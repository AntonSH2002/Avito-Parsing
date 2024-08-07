import json
from selenium import webdriver
from selenium.common import TimeoutException, NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from geopy.geocoders import Nominatim
from rosreestr_api.clients.rosreestr import PKKRosreestrAPIClient

driver = webdriver.Firefox()

data = []

geolocator = Nominatim(user_agent="GetLoc")

rosreestr_api_client = PKKRosreestrAPIClient()


def correct_address(address):
    if "мкр-н" in address or "пр-т" in address:
        return None

    if "тракт." in address:
        address = address.replace("тракт.", "тракт ")

    if "тракт" in address:
        parts = address.split(", ")
        for i, part in enumerate(parts):
            if "тракт" in part:
                parts[i] = part.replace("тракт ", "") + " тракт"
        address = ", ".join(parts)

    if "пр-т" in address:
        address = address.replace("пр-т", "проспект")

    if "д." in address:
        address = address.replace("д.", "")
    if "корп." in address:
        address = address.replace("корп.", "к")
    return address


for i in range(1):
    driver.get(
        f"https://www.avito.ru/barnaul/kvartiry/prodam-ASgBAgICAUSSA8YQ?cd=1&context=H4sIAAAAAAAA_0q0MrSqLraysFJKK8rPDUhMT1WyLrYysVLKTczMU7KuBQQAAP__w5qblCAAAAA&p={i}")

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

                corrected_address = correct_address(address)
                if not corrected_address:
                    print(f"Объявление {j} с адресом {address} было удалено.")
                    driver.back()
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_all_elements_located((By.XPATH, "//div[@data-marker='item']")))
                    continue

                location = geolocator.geocode(corrected_address, timeout=10)

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
                            "Адрес": corrected_address,
                            "Кадастровый номер": cadastral_id
                        }
                    else:
                        temp_data = {
                            "Название": title,
                            "Цена": price,
                            "Ссылка": url,
                            "Адрес": corrected_address,
                        }
                else:
                    temp_data = {
                        "Название": title,
                        "Цена": price,
                        "Ссылка": url,
                        "Адрес": corrected_address,
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
