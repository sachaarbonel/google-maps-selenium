from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
import time
from selenium import webdriver
import csv
import re


def wait_and_find(waitDriver: WebDriverWait, xpath: str)->str:

    element = waitDriver.until(EC.visibility_of_element_located(
        (By.XPATH, xpath))).find_element_by_xpath(xpath)
    return element.text


def wait_and_find_elements(waitDriver: WebDriverWait, xpath: str)->list:

    elements = waitDriver.until(EC.visibility_of_element_located(
        (By.XPATH, xpath))).find_elements_by_xpath(xpath)
    return [element for element in elements]


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
    phone_number_xpath = '//*[@id="pane"]/div/div[1]/div/div/div[18]/div/div[1]/span[3]/span[3]'
    phone = wait_and_find(wait, phone_number_xpath)
    if get_phone_number(phone) is None:
        phone_number_xpath = '//*[@id="pane"]/div/div[1]/div/div/div[15]/div/div[1]/span[3]/span[3]'
        phone = wait_and_find(wait, phone_number_xpath)
    print(phone)
    hotel_name_xpath = '//*[@id="pane"]/div/div[1]/div/div/div[1]/div[3]/div[1]/h1'
    hotel = wait_and_find(wait, hotel_name_xpath)
    print(hotel)
    time.sleep(2)
    #current_url = driver.current_url
    # print(current_url)
    print("please skip manually if no response")
    return hotel, phone


def exists(name: str)->bool:
    with open('results.csv') as csvfile:

        reader = csv.DictReader(csvfile)

        for row in reader:
            return row["name"] == name


def writeToCsv(name: str, phone: str):
    with open('results.csv', 'a', newline='') as csvfile:
        fieldnames = ['name', 'phone']

        #reader = csv.DictReader(csvfile)
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writerow({'name': name, 'phone': phone})


def get_phone_number(scraped_items: str)->str:
    regex = r"""
        ^
            (?:(?:\+|00)33|0|\+596|\+696)     # Dialing code
            \s*[1-9]              # First number (from 1 to 9)
            (?:[\s.-]*\d{2}){4}   # End of the phone number
        $
        """

    matches = re.finditer(regex, scraped_items, re.MULTILINE |
                          re.IGNORECASE | re.VERBOSE)

    return [match.group() for matchNum, match in enumerate(matches, start=1)]


if __name__ == "__main__":

    driver = webdriver.Chrome()
    url = 'https://www.google.com/maps/search/H%C3%B4tels/@14.4964286,-61.0759903,13z'
    driver.get(url)  # lat, long, zoom level
    driver.set_page_load_timeout(30)
    driver.set_script_timeout(30)
    wait = WebDriverWait(driver, 10)

    for i in range(1, 20):
        name, phone = extract_hotel_info(i)
        writeToCsv(name, phone)
        driver.execute_script(script="window.history.back(-1);")

    driver.quit()

    # test_str = ("06 01 02 03 04\n"
    #             "+33 6 01 02 03 04\n"
    #             "+596 7 01 02 03 04\n"
    #             "+696 7 01 02 03 04\n")
    # result = get_phone_number(test_str)
