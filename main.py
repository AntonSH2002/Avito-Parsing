import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import json
from geopy.geocoders import Nominatim
from rosreestr_api.clients.rosreestr import PKKRosreestrAPIClient

driver = uc.Chrome(headless=True)

data = []

geolocator = Nominatim(user_agent="GetLoc")

rosreestr_api_client = PKKRosreestrAPIClient()

for i in range(1, 2):
    driver.get(f"https://www.avito.ru/barnaul/kvartiry/prodam-ASgBAgICAUSSA8YQ?cd=1&context=H4sIAAAAAAAA_0q0MrSqLraysFJKK8rPDUhMT1WyLrYysVLKTczMU7KuBQQAAP__w5qblCAAAAA&p={i}")
    elements = driver.find_elements(By.CLASS_NAME, "iva-item-root-_lk9K")

    for element in elements:
        name = element.find_element(By.CLASS_NAME, "styles-module-root-iSkj3")
        price = element.find_element(By.CLASS_NAME, "styles-module-root-bLKnd")
        address_div = element.find_element(By.CLASS_NAME, "geo-root-zPwRk")
        address = ("Алтайский край, Барнаул, " + address_div.text).replace("р-н", "").replace("\n", "")
        link = name.get_attribute("href")

        location = geolocator.geocode(address)

        if location:
            parcel = rosreestr_api_client.get_parcel_by_coordinates(lat=location.latitude, long=location.longitude)
            if parcel["features"]:
                cadastral_id = parcel["features"][0]["attrs"]["cn"]
                data.append({
                    "Название объявления": name.text,
                    "Цена": price.text,
                    "Адрес": address,
                    "Долгота": location.latitude,
                    "Широта": location.longitude,
                    "Кадастровый номер": cadastral_id,
                    "Ссылка": link
                })
            else:
                data.append({
                    "Название объявления": name.text,
                    "Цена": price.text,
                    "Адрес": address,
                    "Ссылка": link
                })
        else:
            data.append({
                "Название объявления": name.text,
                "Цена": price.text,
                "Адрес": address,
                "Ссылка": link
            })

with open("data.json", "w", encoding="utf-8") as json_file:
    json.dump(data, json_file, ensure_ascii=False, indent=4)

driver.close()
