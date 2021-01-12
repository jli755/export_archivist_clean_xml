"""
Python 3
    Web scraping using selenium to click the "Export" button
        - from https://archivist.closer.ac.uk/admin/export 
"""

import pandas as pd
import time
import sys
import os
from urllib.parse import urlparse

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities 

def get_driver():
    # driver = webdriver.Remote( 
        # command_executor='http://selenium-standalone-firefox:4444/wd/hub',
        # desired_capabilities=DesiredCapabilities.FIREFOX)
    driver = webdriver.Firefox(executable_path="/home/jenny/Documents/python_scripts.git/geckodriver")
    return driver


def archivist_login(driver, url, uname, pw, sleep_time=3):
    """
    Log in to archivist

    Returns:
        bool: True if the login seemed to work, else False.
    """
    driver.get(url)
    time.sleep(sleep_time)
    # 
    try:
        driver.find_element_by_id("login-email").send_keys(uname)
        driver.find_element_by_id("login-password").send_keys(pw)
        driver.find_element_by_class_name("btn-default").click()
    except NoSuchElementException as e:
        print(e)
        print("So we give up on this host")
        return False
    time.sleep(sleep_time)
    # check next page's title to make sure one is logged in
    if not driver.title.startswith("Instruments"):
        print("failed to login to this host, check your credentials?")
        return False
    return True


def url_base(s):
    """Extract the "base" of a url.

    For example, from "https://example.com/something/somewhere.html" returns
    "https://example.com"
    """
    o = urlparse(s)
    return "{}://{}".format(o.scheme, o.netloc)


def archivist_login_all(driver, urls, uname, pw):
    """Log in to archivist for a bunch of different URLs

    If URLs share common bases (scheme+host) then each one is logged into
    only once.

    Returns:
        dict: keyed by the base (scheme+host) with value True/False where
            True means we could login and False means we could not.
    """
    print("Log in to all hosts")
    unique_instance = set([url_base(l) for l in urls])
    print("Unique hosts are: {}".format(unique_instance))
    ok = {}
    for i in unique_instance:
        print("Logging into host {}".format(i))
        if archivist_login(driver, i, uname, pw):
            ok[i] = True
        else:
            ok[i] = False
 
    print("Host online/available mapping: {}".format(ok))
    return ok


def get_names(df):
    """Return a dictionary of files

    PLAN DEPRECATED: reuse get_base_url below instead?
    """

    df["url"] = df.apply(lambda row: "https://archivist.closer.ac.uk/admin/export" if row["Archivist"].lower() == "main"
                                else "https://closer-archivist-alspac.herokuapp.com/admin/export" if row["Archivist"].lower() == "alspac"
                                else "https://closer-archivist-us.herokuapp.com/admin/export" if row["Archivist"].lower() == "us"
                                else "https://closer-archivist-wirral.herokuapp.com/admin/export" if row["Archivist"].lower() == "wirral"
                                else None, axis=1)
    names_dict = pd.Series(df.url.values, index=df.Instrument).to_dict()
    return names_dict


def get_base_url(df):
    """
    Return a dataframe of files that need to be downloaded
    """

    df["base_url"] = df.apply(lambda row: "https://archivist.closer.ac.uk/" if row["Archivist"].lower() == "main"
                                     else "https://closer-archivist-alspac.herokuapp.com/" if row["Archivist"].lower() == "alspac"
                                     else "https://closer-archivist-us.herokuapp.com/" if row["Archivist"].lower() == "us"
                                     else "https://closer-archivist-wirral.herokuapp.com/" if row["Archivist"].lower() == "wirral"
                                     else None, axis=1)

    return df


if __name__ == "__main__":
    raise RuntimeError("don't run this directly")

