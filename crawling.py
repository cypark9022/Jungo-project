import requests
from bs4 import BeautifulSoup
from selenium import webdriver


## 프론트와 연결할때는 화면에서의 입력값(keyword)으로 수정해야함!!
keyword = str(input('품목명을 입력하시오 : '))
url = 'https://www.daangn.com/search/' + keyword

chrome_path = 'C:/Users/LGPC/Desktop/sparta/Jungo-project/driver/chromedriver_v81/chromedriver_win32/chromedriver'
driver = webdriver.Chrome(chrome_path)

driver.implicitly_wait(3)
driver.get(url)

# 크롬에서 특정tag영역(더보기) 클릭 -> 5회 반복
for i in range(5):
    driver.find_element_by_xpath('//*[@id="result"]/div[1]/div[2]').click()

# 더보기 5번 클릭 후 url 페이지의 html data 크롤링
driver.implicitly_wait(1)
html = driver.page_source
soup = BeautifulSoup(html, 'html.parser')

item_img = soup.select('#flea-market-wrap > article > a > div.card-photo')
item_title = soup.select('#flea-market-wrap > article > a > div.article-info > div > span.article-title')
item_position = soup.select('#flea-market-wrap > article > a > div.article-info > p.article-region-name')
item_price = soup.select('#flea-market-wrap > article > a > div.article-info > p.article-price')

# items 리스트에 img, title, position, price 데이터를 key&value 형태로 저장
items = []
for item in zip(item_img, item_title, item_position, item_price):
    items.append(
        {
            'img': item[0],
            'title': item[1].text,
            'position': item[2].text,
            'price': item[3].text
        }
    )

print(items)

# Chrome 브라우저 종료
driver.close()