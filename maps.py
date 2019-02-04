from selenium.webdriver import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
import time
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
import queue

driver = webdriver.Chrome()

driver.get(
    'https://www.google.com/maps/search/H%C3%B4tels/@14.4964286,-61.0759903,13z')

# Wait and click the menu button
wait = WebDriverWait(driver, 10)

# Change the option

results = []
for x in driver.find_elements_by_xpath('//*[contains(concat( " ", @class, " " ), concat( " ", "section-result", " " ))]'):
    results.append(x.get_attribute('data-result-index'))

for r in results:
    print(r)

r = "1"
page = wait.until(EC.element_to_be_clickable(
    (By.XPATH, '//*[contains(concat( " ", @class, " " ), concat( " ", "section-result", " " )) and (((count(preceding-sibling::*) + 1) = '+r+') and parent::*)]')))  # result detail page
page.click()
phone_number_xpath = '//*[@id="pane"]/div/div[1]/div/div/div[18]/div/div[1]/span[3]/span[3]'
phone_number = wait.until(EC.visibility_of_element_located(
    (By.XPATH, phone_number_xpath))).find_element_by_xpath(phone_number_xpath)
print(phone_number.text)

hotel_name_xpath = '//*[@id="pane"]/div/div[1]/div/div/div[1]/div[3]/div[1]/h1'
hotel_name = wait.until(EC.visibility_of_element_located(
    (By.XPATH, hotel_name_xpath))).find_element_by_xpath(hotel_name_xpath)
print(hotel_name.text)
driver.back()
driver.forward()
