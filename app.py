from pymongo import MongoClient

from flask import Flask, render_template, jsonify, request, redirect

import hashlib
import requests
from bs4 import BeautifulSoup
from selenium import webdriver

app = Flask(__name__)

client = MongoClient('localhost', 27017)
db = client.jungo

# 페이지 이동 (로그인, 회원가입, 메인)
@app.route('/')
def home():
    return render_template('login_index.html')

@app.route('/member')
def member_page():
    return render_template('member_index.html')

@app.route('/main')
def main_page():
    return render_template('main_index.html')


# 입력받은 회원정보를 DB에 저장
@app.route('/member/save', methods=['POST'])
def member_save():
    uid_receive = request.form['uid_give']
    upw_receive = request.form['upw_give']
    uname_receive = request.form['uname_give']

    ## 동시에 같은아이디로 회원가입할 경우, 에러발생가능!!(mongoDB의 _id 확인으로 변경필요!!)
    if db.member.find_one({'uid': uid_receive}):
        return jsonify({'result': 'duplication'})

    # 비밀번호 sha256으로 암호화한 hash값 저장
    upw_receive = hashlib.sha256(upw_receive.encode()).hexdigest()

    member = {'uid': uid_receive, 'upw': upw_receive, 'uname': uname_receive}
    db.member.insert_one(member)

    return jsonify({'result': 'success'})


# 입력받은 회원정보로 로그인
@app.route('/login', methods=['POST'])
def login():
    uid_receive = request.form['uid_give']
    upw_receive = request.form['upw_give']

    # 비밀번호 sha256으로 암호화한 hash값 저장
    upw_receive = hashlib.sha256(upw_receive.encode()).hexdigest()
    
    if db.member.find_one({'uid': uid_receive, 'upw': upw_receive}):
        return jsonify({'result': 'success'})
        # return render_template('main_index.html')


# 입력받은 키워드로 당근마켓 크롤링
@app.route('/main', methods=['POST'])
def main():
    ## 프론트와 연결할때는 화면에서의 입력값(keyword)으로 수정해야함!!
    keyword = '지갑'
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
    # items = []
    # for item in zip(item_img, item_title, item_position, item_price):
    #     items.append(
    #         {
    #             'img': item[0].select_one('img')['src'],
    #             'title': item[1].text,
    #             'position': item[2].text,
    #             'price': item[3].text
    #         }
    #     )

    items_all = []
    for item in zip(item_img, item_title, item_position, item_price):
        items = {}
        items.update({'img': item[0].select_one('img')['src']})
        items.update({'title': item[1].text})
        items.update({'position': item[2].text})
        items.update({'price': item[3].text})

        items_all.append(items)

    # 크롤링한 데이터 DB에 저장
    db.items.insert(items_all)

    # Chrome 브라우저 종료
    driver.implicitly_wait(1)
    driver.close()

    # DB에 데이터 저장이 될 경우, 크롤링성공 메시지출력
    if db.items.find({}):
        return jsonify({'result': 'success'})
    else:
        return jsonify({'result': 'fail'})

# API 서버 실행 (url, Port)
if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)