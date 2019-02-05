from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
import time
from selenium import webdriver
import csv
import re

from processing import exists


def wait_and_find(waitDriver: WebDriverWait, xpath: str)->str:

    element = waitDriver.until(EC.visibility_of_element_located(
        (By.XPATH, xpath))).find_element_by_xpath(xpath)
    return element.text


def wait_and_click(waitDriver: WebDriverWait, xpath: str):
    page = waitDriver.until(EC.element_to_be_clickable(
        (By.XPATH, xpath)))  # result detail page
    page.click()


def hotel_xpath(id: int):
    index = 1
    newindex = id*2-index
    div_id = str(newindex)
    section_result_xpath = '//*[@id="pane"]/div/div[1]/div/div/div[4]/div['+div_id+']'
    return section_result_xpath


def extract_hotel_info(id: int)->(str, str):
    section_result_xpath = hotel_xpath(id)
    wait_and_click(wait, section_result_xpath)
    xpath = '//*[contains(concat( " ", @class, " " ), concat( " ", "section-info-line", " " ))]'
    info_sections = wait_and_find_elements(wait, xpath)
    phone = get_phone_number(info_sections)
    print(phone)
    hotel_name_xpath = '//*[@id="pane"]/div/div[1]/div/div/div[1]/div[3]/div[1]/h1'
    hotel = wait_and_find(wait, hotel_name_xpath)
    print(hotel)
    time.sleep(2)
    #current_url = driver.current_url
    # print(current_url)
    print("please skip manually if no response")
    return hotel, phone


def writeToCsv(name: str, phone: str):
    with open('results.csv', 'a', newline='') as csvfile:
        fieldnames = ['name', 'phone']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not exists(name):
            writer.writerow({'name': name, 'phone': phone})


def get_phone_number(elements: object)->str:
    result = ""
    for elts in elements:
        phone_number = match_phone_number(elts.text)
        if phone_number:
            result = phone_number[0]
    return result


def match_phone_number(item: str)->list:
    regex = r"""
        ^
            (?:(?:\+|00)33|0|\+596|\+696)     # Dialing code
            \s*[1-9]              # First number (from 1 to 9)
            (?:[\s.-]*\d{2}){4}   # End of the phone number
        $
        """

    matches = re.finditer(regex, item, re.MULTILINE |
                          re.IGNORECASE | re.VERBOSE)

    return [match.group() for matchNum, match in enumerate(matches, start=1)]


def wait_and_find_elements(waitDriver: WebDriverWait, xpath: str)->object:
    elements = wait.until(
        EC.visibility_of_element_located((By.XPATH, xpath))).find_elements_by_xpath(xpath)
    return elements


if __name__ == "__main__":

    driver = webdriver.Chrome()
    # lat, long, zoom level
    url = 'https://www.google.com/maps/search/H%C3%B4tels/@14.4964286,-61.0759903,13z'
    driver.get(url)
    driver.set_page_load_timeout(30)
    driver.set_script_timeout(30)
    wait = WebDriverWait(driver, 10)

    for i in range(1, 20):
        name, phone = extract_hotel_info(i)
        writeToCsv(name, phone)
        driver.execute_script(script="window.history.back(-1);")

    driver.quit()
