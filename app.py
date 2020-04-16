from flask import Flask, render_template, jsonify, request, redirect, url_for
app = Flask(__name__)

from pymongo import MongoClient
client = MongoClient('localhost', 27017)
db = client.jungo

import hashlib          # 비밀번호 SHA256 암호화
import jwt              # 로그인 기능을위한 토큰
import datetime, time   # 토큰 만료시간 설정 

SECRET_KEY = 'cypark'   # jwt 토큰 생성을위한 고유키(비밀키)

import requests
from bs4 import BeautifulSoup   # html 파싱
from selenium import webdriver  # 동적인 페이지 크롤링

###################################
##       HTML을 주는 부분        ##
###################################
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login')
def member_page():
    return render_template('login.html')

@app.route('/register')
def main_page():
    return render_template('register.html')


#####################################
##     로그인기능을 위한 API       ##
#####################################

# [회원가입 API]
# 입력받은 id, pw, name을 DB에 저장 (pw는 sha256 암호화)
@app.route('/api/register', methods=['POST'])
def api_register():
    uid_receive = request.form['uid_give']
    upw_receive = request.form['upw_give']
    uname_receive = request.form['uname_give']

    # 아이디 중복체크
    result = db.user.find_one({'uid': uid_receive})
    if result is not None:
        return jsonify({'result': 'fail', 'msg': '이미 사용중인 아이디 입니다.'})
    
    # 비밀번호는 암호화하여 DB에 저장
    upw_hash = hashlib.sha256(upw_receive.encode('utf-8')).hexdigest()

    user_info = {'uid': uid_receive, 'upw': upw_hash, 'uname': uname_receive}
    db.user.insert_one(user_info)

    return jsonify({'result': 'success'})


# [로그인 API]
# 입력받은 id, pw가 DB에 있을경우 토큰 발급
@app.route('/api/login', methods=['POST'])
def login():
    uid_receive = request.form['uid_give']
    upw_receive = request.form['upw_give']

    # 아이디와 암호화된 비밀번호로 DB에 있는지 확인
    upw_hash = hashlib.sha256(upw_receive.encode()).hexdigest()
    
    user_info = {'uid': uid_receive, 'upw': upw_hash}
    result = db.user.find_one(user_info)

    if result is not None:
        # payload에 아이디와 만료기간 정보 담기
        payload = {
            'uid': uid_receive,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(seconds=60)
        }
        # 시크릿키를 알아야 payload 정보를 볼 수 있는 jwt 토큰 생성
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256').decode('utf-8')
        
        return jsonify({'result': 'success', 'token': token})
    else:
        return jsonify({'result': 'fail', 'msg': '아이디/비밀번호가 일치하지 않습니다'})


# [유저 정보 확인 API]
# 로그인에 성공하여 토큰이 있는 유저만 호출할 수 있는 API
@app.route('/api/uname', methods=['GET'])
def api_valid():
    token_receive = request.headers['token_give']

    # token을 시크릿키로 디코딩
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        print(payload)

        user_info = db.user.find_one({'uid': payload['uid']}, {'_id': False})
        return jsonify({'result': 'success', 'uname': user_info['uname']})
    except jwt.ExpiredSignature:
        # jwt 토큰의 만료시간이 지났으면 에러발생
        return jsonify({'result': 'fail', 'msg': '로그인 시간이 만료되었습니다.'})


##################################
##     당근마켓 크롤링 API      ##
##################################

# 입력받은 키워드로 당근마켓 크롤링
@app.route('/dgmk', methods=['POST'])
def dgmk():
    keyword_receive = request.form['keyword_give']
    url = 'https://www.daangn.com/search/' + str(keyword_receive)

    chrome_path = 'C:/Users/LGPC/Desktop/sparta/Jungo-project/driver/chromedriver_v81/chromedriver_win32/chromedriver'
    driver = webdriver.Chrome(chrome_path)

    driver.implicitly_wait(3)
    driver.get(url)

    # 크롬 웹브라우저 화면에서 [더보기] 클릭 -> 12회 반복 (150개)
    for i in range(12):
        driver.find_element_by_xpath('//*[@id="result"]/div[1]/div[2]').click()
    time.sleep(5)

    # url 페이지의 html data 크롤링
    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')

    # 새로운 데이터를 저장하기위해 DB 테이블 초기화
    db.items_dangn.remove({})

    # 입력받은 상한가, 하한가를 int형으로 변환
    max_price_receive = request.form['max_price_give']
    min_price_receive = request.form['min_price_give']
    price_max = int("".join(filter(str.isdigit, max_price_receive)))
    price_min = int("".join(filter(str.isdigit, min_price_receive)))

    # 크롤링된 데이터를 DB에 저장
    items = soup.select('div > article.flea-market-article')

    for item in items:
        item_img = item.select_one('div.card-photo > img')['src']
        item_title = item.select_one('span.article-title').text
        item_position = item.select_one('p.article-region-name').text
        item_price = item.select_one('p.article-price').text
        item_link = item.select_one('article.flea-market-article > a')['href']

        # 물품의 가격을 int형으로 변환
        price_int = int("".join(filter(str.isdigit, item_price)))

        if price_min <= price_int and price_int <= price_max:
            doc = {
                'img': item_img,
                'title': item_title,
                'position': item_position,
                'price': item_price,
                'link': 'daangn.com' + item_link
                }
            db.items_dangn.insert_one(doc)

    # Chrome 브라우저 종료
    driver.close()

    # DB에 데이터 저장이 될 경우, 크롤링성공 메시지출력
    result = db.items_dangn.find({})

    if result is not None:
        return jsonify({'result': 'success', 'msg': '검색결과를 DB에 저장하였습니다'})
    else:
        return jsonify({'result': 'fail'})


##################################
##     헬로마켓 크롤링 API      ##
##################################

# 입력받은 키워드로 헬로마켓 크롤링
@app.route('/hlmk', methods=['POST'])
def hlmk():
    keyword_receive = request.form['keyword_give']

    # 입력받은 키워드로 최신(1~5page) html 가져오기
    headers = {'User-Agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36'}
    
    # 새로운 데이터를 저장하기위해 DB 테이블 초기화
    db.items_hello.remove({})

    # 입력받은 상한가, 하한가를 int형으로 변환
    max_price_receive = request.form['max_price_give']
    min_price_receive = request.form['min_price_give']
    price_max = int("".join(filter(str.isdigit, max_price_receive)))
    price_min = int("".join(filter(str.isdigit, min_price_receive)))

    for i in range(1, 6):
        url = 'https://www.hellomarket.com/search?q=' + keyword_receive + '&page=' + str(i)
        data = requests.get(url, headers=headers)

        # 검색키워드로 크롤링하여 DB에 저장
        soup = BeautifulSoup(data.text, 'html.parser')
        items = soup.select('ul > li.main_col_3')

        for item in items:
            item_img = item.select_one('div.image_centerbox > img')['src']
            item_title = item.select_one('div.item_title').text
            item_price = item.select_one('div.item_price').text
            item_link = item.select_one('li.main_col_3 > a')['href']

            # 물품의 가격을 int형으로 변환
            price_int = int("".join(filter(str.isdigit, item_price)))

            if price_min <= price_int and price_int <= price_max:
                doc = {
                    'img': item_img,
                    'title': item_title,
                    'price': item_price,
                    'link': 'hellomarket.com' + item_link
                    }

                db.items_hello.insert_one(doc)

    # DB에 데이터 저장이 될 경우, 크롤링성공 메시지출력
    result = db.items_hello.find({})

    if result is not None:
        return jsonify({'result': 'success', 'msg': '검색결과를 DB에 저장하였습니다'})
    else:
        return jsonify({'result': 'fail'})

# API 서버 실행 (url, Port)
if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)