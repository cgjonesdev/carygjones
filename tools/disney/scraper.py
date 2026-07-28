import sys
import re
import time
import requests
import selenium
from selenium import webdriver as driver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options
from bs4 import BeautifulSoup as bs

options = Options()

def wait(driver, by, elem_str):
    for i in range(100):
        try: return driver.find_element(by, elem_str)
        except Exception as e: time.sleep(.25)

def retry(elem, action, *args, **kwargs):
    for i in range(10):
        try: return getattr(elem, action)(*args, **kwargs)
        except Exception as e: time.sleep(.25)
