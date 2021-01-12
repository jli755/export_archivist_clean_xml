#!/usr/bin/env python3

"""
Python 3
    Web scraping using selenium to get .xml
        - from https://archivist.closer.ac.uk/admin/export  Download latest

    Clean xml 

    grep -rnw 'archivist' -e '&amp;amp;'
    archivist/alspac_91_pq.xml:16376:          <r:Content xml:lang="en-GB">City &amp;amp; Guilds intermediate technical</r:Content>
    archivist/alspac_91_pq.xml:16385:          <r:Content xml:lang="en-GB">City &amp;amp; Guilds final technical</r:Content>
    archivist/alspac_91_pq.xml:16394:          <r:Content xml:lang="en-GB">City &amp;amp; Guilds full technical</r:Content>
    archivist/alspac_91_pq.xml:16412:          <r:Content xml:lang="en-GB">Yes &amp;amp; affected me a lot</r:Content>

"""

import time
import sys
import os
import re
from lxml import etree
import pandas as pd

from mylib import get_driver, url_base, archivist_login_all, get_names


driver = get_driver()


def archivist_download_xml(export_name, output_dir, uname, pw):
    """
    Loop over export_names dictionary, downloading xml
    """

    # Log in to all
    ok = archivist_login_all(driver, export_name.values(), uname, pw)

    def log_to_csv(prefix, xml_date, xml_location):
        """append a line to spreadsheet with three values"""
        with open(os.path.join(os.path.dirname(output_dir), "download_list.csv"), "a") as f:
            f.write( ",".join([prefix, xml_date, xml_location]) + "\n")

    print(export_name.items())
    print(ok)
    for prefix, url in export_name.items():
        if url:
            base = url_base(url)
            print('Working on export item "{}" from "{}" with URL "{}"'.format(prefix, base, url))
            if not ok[base]:
                print("host {} was not available, skipping".format(base))
                with open(os.path.join(os.path.dirname(output_dir), "download_list.csv"), "a") as f:
                    f.write( ",".join([prefix, "skipped"]) + "\n")
                continue
            driver.get(url)
            time.sleep(10)
 
            # find the input box
            inputElement = driver.find_element_by_xpath("//input[@placeholder='Search for...']")
            
            inputElement.send_keys(prefix)   

            # locate id and link
            trs = driver.find_elements_by_xpath("html/body/div/div/div/div/div/div/table/tbody/tr")

            print("This page has {} rows, searching for matching row".format(len(trs)))
            matching_idx = []
            for i in range(1, len(trs)):
                # row 0 is header: tr has "th" instead of "td"
                tr = trs[i]
                if prefix == tr.find_elements_by_xpath("td")[1].text:
                    matching_idx.append(i)
            if len(matching_idx) == 0:
                log_to_csv(prefix, "n/a", "Could not find a row matching the prefix")         
                continue
            elif len(matching_idx) > 1:
                log_to_csv(prefix, "n/a", "There was more than one row matching this prefix: will download first")
                # note, keep going...?

            tr = trs[matching_idx[0]]

            # column 5 is "Export date"           
            xml_date = tr.find_elements_by_xpath("td")[4].text

            # column 6 is "Actions", need to have both "download latest and export"
            xml_location = tr.find_elements_by_xpath("td")[5].find_elements_by_xpath("a")[0].get_attribute("href")

            if xml_location is None:
                log_to_csv(prefix, xml_date, "Skipping because xml_location was none")
                continue
            print("Getting xml for " + prefix) 
            driver.get(xml_location)

            time.sleep(10)
            print("  Downloading xml for " + prefix)
            out_f = os.path.join(output_dir, prefix + ".xml")

            with open(out_f, "wb") as f:
                try:
                    f.write(driver.page_source.encode("utf-8"))
                except UnicodeEncodeError:
                    log_to_csv(prefix, xml_date, "Could not download, Unicode error")
                    continue
                except IOError:
                    log_to_csv(prefix, xml_date, "Could not download, IO error")
                    continue
            time.sleep(5)
            log_to_csv(prefix, xml_date, xml_location)
    driver.quit()

 
def get_xml(df, output_dir, uname, pw):
    """
    Export xml to output dir
    """

    export_names = get_names(df)
    print("Got {} xml names".format(len(export_names)))

    archivist_download_xml(export_names, output_dir, uname, pw)
           

def clean_text(rootdir):
    """
    Go through text files
        - replace &amp;amp;# with &#
        - replace &amp;amp; with &amp;
        - replace &amp;# with &#    
        - replace &#160: with &#160; 
    """

    try:
        files = [f for f in os.listdir(rootdir) if os.path.isfile(os.path.join(rootdir, f))]
    except WindowsError:
        print("something is wrong")
        sys.exit(1)

    for filename in files:
        filename = os.path.join(rootdir, filename)
        print(filename + ": pass 1 fixing '&amp;amp;#'")
        tmpfile1 = filename + ".temp1"
        tmpfile2 = filename + ".temp2"
        tmpfile3 = filename + ".temp3"
        tmpfile4 = filename + ".temp4"

        with open(filename, "r") as fin:
            with open(tmpfile1, "w") as fout:
                for line in fin:
                    fout.write(line.replace("&amp;amp;#", '&#'))

        print(filename + ": pass 2 fixing '&amp;amp;'")
        with open(tmpfile1, "r") as fin:
            # overwrite
            with open(tmpfile2, "w") as fout:
                for line in fin:
                    fout.write(line.replace("&amp;amp;", '&amp;'))

        print(filename + ": pass 3 fixing '&amp;#'")
        with open(tmpfile2, "r") as fin:
            # overwrite
            with open(tmpfile3, "w") as fout:
                for line in fin:
                    fout.write(line.replace("&amp;#", '&#'))

        print(filename + ": pass 4 fixing '&#160: (note colon)'")
        with open(tmpfile3, "r") as fin:
            # overwrite
            with open(tmpfile4, "w") as fout:
                for line in fin:
                    fout.write(re.sub(r"(&#[0-9]+):", r"\1;", line))

        print(filename + ": pass 5 fixing '&#163'")
        with open(tmpfile4, "r") as fin:
            # overwrite
            with open(filename, "w") as fout:
                for line in fin:
                    fout.write(line.replace("&#163<", '&#163;<'))

        # remove tmp
        print(filename + ": deleting tmpfile")
        os.unlink(tmpfile1)
        os.unlink(tmpfile2)
        os.unlink(tmpfile3)
        os.unlink(tmpfile4)


def clean_newline(rootdir):
    """
    Overwrite the original xml file with a middle of context line break replaced by a space.
    Also expand the escaped characters, for example: &#163; becomes £
    Line breaks in text are generally represented as:
        \r\n - on a windows computer
        \r   - on an Apple computer
        \n   - on Linux
    """

    try:
        files = [f for f in os.listdir(rootdir) if os.path.isfile(os.path.join(rootdir, f))]
    except WindowsError:
        print("something is wrong")
        sys.exit(1)

    for filename in files:
        filename = os.path.join(rootdir, filename)
        print(filename)
        p = etree.XMLParser(resolve_entities=True)
        with open(filename, "rt") as f:
            tree = etree.parse(f, p)

        for node in tree.iter():
            if node.text is not None:
                if re.search("\n|\r|\r\n", node.text.rstrip()):
                    node.text = node.text.replace("\r\n", " ")
                    node.text = node.text.replace("\r", " ")
                    node.text = node.text.replace("\n", " ")

        # because encoding="UTF-8" in below options, the output can contain non-ascii characters, e.g. £
        tree.write(filename, encoding="UTF-8", xml_declaration=True)


def main():
    uname = sys.argv[1]
    pw = sys.argv[2]

    main_dir = "export_xml"
    output_dir = os.path.join(main_dir, "archivist_xml")

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # prefixes
    df = pd.read_csv("Prefixes_to_export.txt", sep="\t")

    get_xml(df, output_dir, uname, pw)
    clean_text(output_dir)
    clean_newline(output_dir)


if __name__ == "__main__":
    main()

