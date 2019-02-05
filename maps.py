from selenium.webdriver import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
import time
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
import queue


def wait_and_find(waitDriver: WebDriverWait, xpath: str)->str:

    element = waitDriver.until(EC.visibility_of_element_located(
        (By.XPATH, xpath))).find_element_by_xpath(xpath)
    return element.text


def wait_and_click(waitDriver: WebDriverWait, xpath: str):
    page = waitDriver.until(EC.element_to_be_clickable(
        (By.XPATH, xpath)))  # result detail page
    page.click()


def hotel_xpath(r):
    index = 1
    newindex = r*2-index
    div_id = str(newindex)
    section_result_xpath = '//*[@id="pane"]/div/div[1]/div/div/div[4]/div['+div_id+']'
    return section_result_xpath


if __name__ == "__main__":

    driver = webdriver.Chrome()
    url = 'https://www.google.com/maps/search/H%C3%B4tels/@14.4964286,-61.0759903,13z'
    driver.get(
        url)  # lat, long, zoom level

    wait = WebDriverWait(driver, 10)

    results = []
    for elt in driver.find_elements_by_xpath('//*[contains(concat( " ", @class, " " ), concat( " ", "section-result", " " ))]'):
        results.append(elt.get_attribute('data-result-index'))

    for r in results:
        print(r)

    r = 1
    section_result_xpath = hotel_xpath(r)
    wait_and_click(wait, section_result_xpath)
    phone_number_xpath = '//*[@id="pane"]/div/div[1]/div/div/div[18]/div/div[1]/span[3]/span[3]'
    phone = wait_and_find(wait, phone_number_xpath)
    print(phone)
    hotel_name_xpath = '//*[@id="pane"]/div/div[1]/div/div/div[1]/div[3]/div[1]/h1'
    hotel = wait_and_find(wait, hotel_name_xpath)
    print(hotel)
    time.sleep(2)
    driver.back()
    # driver.forward()
    current_url = driver.current_url
    print(current_url)

    # driver.refresh()
    # print("driver refreshed")
    r = 2
    s = hotel_xpath(r)
    wait_and_click(wait, s)
    print("clicked")
    time.sleep(2)
    phone2 = wait_and_find(wait, phone_number_xpath)
    print(phone2)
    print(driver.current_url)
    driver.quit()
