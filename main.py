import json
from selenium import webdriver
from selenium.common import TimeoutException, NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from geopy.geocoders import Nominatim
from rosreestr_api.clients.rosreestr import PKKRosreestrAPIClient
import undetected_chromedriver as uc

driver = webdriver.Firefox()

data = []

geolocator = Nominatim(user_agent="GetLoc")

rosreestr_api_client = PKKRosreestrAPIClient()


def process_address(address):
    if "мкр-н" in address:
        address = ', '.join(part for part in address.split(', ') if "мкр-н" not in part)

    if "пр-т" in address:
        address = address.replace("пр-т", "проспект")

    if "тракт." in address:
        address = address.replace("тракт.", "").strip()
        parts = address.split(',')
        if len(parts) >= 2:
            address = f"{parts[0].strip()} тракт, {parts[1].strip()}"
        if len(parts) == 3:
            address = f"{address.split(',')[0].strip()} {parts[1].strip()} к{parts[2].strip()}"

    address = address.replace("д.", "").replace(" корп.", " к").strip()

    return address


for i in range(1, 6):
    driver.get(f"https://www.avito.ru/altayskiy_kray/kvartiry/prodam-ASgBAgICAUSSA8YQ?cd=1&context=H4sIAAAAAAAA_0q0MrSqLraysFJKK8rPDUhMT1WyLrYyt1JKTixJzMlPV7KuBQQAAP__dhSE3CMAAAA&p={i}")

    try:
        WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.XPATH, "//div[@data-marker='item']")))

        ads = driver.find_elements(By.XPATH, "//div[@data-marker='item']")

        if not ads:
            print("Нет доступных объявлений на странице.")
            break

        for j in range(len(ads)):
            try:
                ads = driver.find_elements(By.XPATH, "//div[@data-marker='item']")
                if j >= len(ads):
                    print(f"Объявление {j} больше не доступно.")
                    continue

                url_element = ads[j].find_element(By.XPATH, ".//a[@itemprop='url']")
                url = url_element.get_attribute("href")

                driver.get(url)
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "h1[itemprop='name']")))
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "span.styles-module-size_xxxl-GRUMY")))
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "span.style-item-address__string-wt61A")))

                title = driver.find_element(By.CSS_SELECTOR, "h1[itemprop='name']").text
                price = driver.find_element(By.CSS_SELECTOR, "span.styles-module-size_xxxl-GRUMY").text
                address = driver.find_element(By.CSS_SELECTOR, "span.style-item-address__string-wt61A").text

                processed_address = process_address(address)

                location = geolocator.geocode(processed_address, timeout=10)

                temp_data = {}

                if location:
                    parcel = rosreestr_api_client.get_parcel_by_coordinates(lat=location.latitude,
                                                                            long=location.longitude)
                    if parcel["features"]:
                        cadastral_id = parcel["features"][0]["attrs"]["cn"]
                        temp_data = {
                            "Название": title,
                            "Цена": price,
                            "Ссылка": url,
                            "Адрес": processed_address,
                            "Кадастровый номер": cadastral_id,
                        }
                    else:
                        temp_data = {
                            "Название": title,
                            "Цена": price,
                            "Ссылка": url,
                            "Адрес": processed_address,
                        }
                else:
                    temp_data = {
                        "Название": title,
                        "Цена": price,
                        "Ссылка": url,
                        "Адрес": processed_address,
                    }

                parameters = driver.find_elements(By.CLASS_NAME, "params-paramsList__item-_2Y2O")
                for parameter in parameters:
                    try:
                        key_element = parameter.find_element(By.CLASS_NAME, "styles-module-noAccent-LowZ8")
                        key = key_element.text.split(':')[0].strip()
                        value = parameter.text.split(':')[1].strip()
                        temp_data[key] = value
                    except (NoSuchElementException, StaleElementReferenceException):
                        continue

                data.append(temp_data)

                driver.back()
                WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.XPATH, "//div[@data-marker='item']")))

            except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
                print(f"Ошибка при обработке объявления: {e}")

    except TimeoutException as e:
        print(f"Ошибка загрузки страницы: {e}")

driver.close()
driver.quit()

with open("data.json", "w", encoding="utf-8") as json_file:
    json.dump(data, json_file, ensure_ascii=False, indent=4)
