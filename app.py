from flask import Flask, render_template, jsonify, request, redirect, url_for
app = Flask(__name__)

from pymongo import MongoClient
client = MongoClient('localhost', 27017)
db = client.jungo

# 로그인기능(JWT)을 위한 패키지
import hashlib
import jwt
import datetime, time  

# 크롤링을 위한 패키지
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options

# 메일전송을 위한 패키지
import smtplib      
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# 스케쥴링을 위한 패키지
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.base import JobLookupError

# 토큰에 사용할 고유키(비밀키)
SECRET_KEY = 'cypark' 

###################################
##       HTML을 주는 부분        ##
###################################
@app.route('/')
def home():
    return render_template('main.html')

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
            'exp': datetime.datetime.utcnow() + datetime.timedelta(seconds=180)
        }
        # 시크릿키를 알아야 payload 정보를 볼 수 있는 토큰 생성
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256').decode('utf-8')
        
        return jsonify({'result': 'success', 'token': token})
    else:
        return jsonify({'result': 'fail', 'msg': '아이디/비밀번호가 일치하지 않습니다'})


# [유저 정보 확인 API]
@app.route('/api/uname', methods=['GET'])
def api_valid():
    token_receive = request.headers['token_give']
    # 로그인에 성공하여 토큰이 있는 유저만 호출할 수 있는 API
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        print('payload : ' + payload)
        user_info = db.user.find_one({'uid': payload['uid']}, {'_id': False})
        print('login success ID : ' + user_info['uname'])
        return jsonify({'result': 'success', 'uname': user_info['uname']})
    except jwt.ExpiredSignature:
        return jsonify({'result': 'fail', 'msg': '로그인 시간이 만료되었습니다.'})


##################################
##     당근마켓 크롤링 API      ##
##################################

# 입력받은 키워드로 당근마켓 크롤링
def dgmk(keyword, uname):
    chrome_path = 'C:/Users/LGPC/Desktop/sparta/Jungo-project/driver/chromedriver_v81/chromedriver_win32/chromedriver'

    # chrome 브라우저를 headless(non-gui)로 사용하기위한 옵션설정
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    driver = webdriver.Chrome(options=options, executable_path=chrome_path)
    driver.implicitly_wait(3)

    url = 'https://www.daangn.com/search/' + keyword
    driver.get(url)
    driver.implicitly_wait(1)

    # 크롬 웹브라우저 화면에서 [더보기] 클릭 -> 12회 반복 (150개)
    for i in range(12):
        try:
            driver.find_element_by_xpath('//*[@id="result"]/div[1]/div[2]').click()
            driver.implicitly_wait(1)
            driver.find_element_by_tag_name('body').send_keys(Keys.PAGE_DOWN)
            time.sleep(0.5)
        # [더보기] 버튼이 없을경우, 현재페이지를 크롤링
        except:
            print('Dangn-market more-button end')
            time.sleep(1)
            break

    # url 페이지의 html data 크롤링
    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')

    # 크롤링된 데이터를 DB에 저장
    items_uname = 'items_' + uname
    items = soup.select('div > article.flea-market-article')

    for item in items:
        item_img = item.select_one('div.card-photo > img')['src']
        item_title = item.select_one('span.article-title').text
        item_position = item.select_one('p.article-region-name').text
        item_price = item.select_one('p.article-price').text
        item_link = item.select_one('article.flea-market-article > a')['href']

        doc = {
                'keyword': keyword,
                'img': item_img,
                'title': item_title,
                'position': item_position,
                'price': item_price,
                'link': 'daangn.com' + item_link
        }
        db[items_uname].insert_one(doc)

    # Chrome 브라우저 종료
    driver.close()

    result = db[items_uname].find({'keyword': keyword})
    if result is not None:
        print('Dangn-market crawling success!! (save to DB)')
    else:
        print('ERROR!! Dangn-market crawling Fail...')


##################################
##     헬로마켓 크롤링 API      ##
##################################

# 입력받은 키워드로 헬로마켓 크롤링
def hlmk(keyword, uname):
    headers = {'User-Agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36'}
    items_uname = 'items_' + uname

    # 입력받은 키워드로 최신(1~5page) html 가져오기
    for i in range(1, 6):
        url = 'https://www.hellomarket.com/search?q=' + keyword + '&page=' + str(i)
        data = requests.get(url, headers=headers)

        # 검색키워드로 크롤링하여 DB에 저장
        soup = BeautifulSoup(data.text, 'html.parser')
        items = soup.select('ul > li.main_col_3')

        for item in items:
            item_img = item.select_one('div.image_centerbox > img')['data-src']
            item_title = item.select_one('div.item_title').text
            item_price = item.select_one('div.item_price').text
            item_link = item.select_one('li.main_col_3 > div > a')['href']

            doc = {
                'keyword': keyword,
                'img': item_img,
                'title': item_title,
                'position': ' ',
                'price': item_price,
                'link': 'hellomarket.com' + item_link
            }
            db[items_uname].insert_one(doc)

    result = db[items_uname].find({'keyword': keyword})
    if result is not None:
        print('Hello-market crawling success!! (save to DB)')
    else:
        print('ERROR!! Hello-market crawling fail...')


####################################
##      DB데이터 화면에 출력      ##
####################################

@app.route('/searching', methods=['POST'])
def make_card():
    keyword = request.form['keyword_give']
    uname = request.form['uname']

    # 로그인ID 각각의 컬렉션을 사용 (기존 DB데이터 삭제)
    items_uname = 'items_' + uname
    db[items_uname].remove({'keyword': keyword})

    # 키워드로 당근마켓, 헬로마켓 크롤링
    dgmk(keyword, uname)
    hlmk(keyword, uname)

    # 로그인ID의 keyword 검색데이터를 가져온 후 list로 변환
    items = list(db[items_uname].find({'keyword': keyword},{'_id': 0}))

    # 유저마다 마지막으로 검색한 keyword를 저장
    db.fs_keyword.remove({'uname': uname})
    db.fs_keyword.insert_one({'uname': uname, 'fs_keyword': keyword})

    return jsonify({'result': 'success', 'items': items})

################################
##        필터링 API        ##
################################

@app.route('/api/filter', methods=['POST'])
def api_filter():
    keyword = request.form['keyword_give']
    max_price_receive = request.form['max_price_give']
    min_price_receive = request.form['min_price_give']
    position_receive = request.form['position_give']
    uname = request.form['uname']
    items_uname = 'items_' + uname
    filter_uname = 'filter_' + uname

    # 최대/최소가격 입력이 없을경우 -1 / 0 저장 (int형 변환)
    temp_max = "".join(filter(str.isdigit, max_price_receive))
    temp_min = "".join(filter(str.isdigit, min_price_receive))

    if temp_max == '':
        max_price = -1
        min_price = int(temp_min)
    elif temp_min == '':
        min_price = 0
        max_price = int(temp_max)
    else:
        max_price = int(temp_max)
        min_price = int(temp_min)

    # 필터링된 데이터를 DB에 저장
    db[filter_uname].remove({'keyword': keyword})
    items = list(db[items_uname].find({'keyword': keyword},{'_id': 0}))

    for item in items:
        keyword = item['keyword']
        title = item['title']
        position = item['position']
        price = item['price']
        img = item['img']
        link = item['link']
        
        # 물품의 가격을 int형으로 변환 (가격정보 없으면 pass)
        price_int = "".join(filter(str.isdigit, price))
        if price_int == '':
            continue

        # 최대가격 입력 안했을 경우, 최소가격만 비교하여 저장
        if min_price <= int(price_int) and max_price == -1:
            doc = {
                'keyword': keyword,
                'img': img,
                'title': title,
                'position': position,
                'price': price,
                'link': link
            }
            db[filter_uname].insert_one(doc)

        elif min_price <= int(price_int) and int(price_int) <= max_price:
            doc = {
                'keyword': keyword,
                'img': img,
                'title': title,
                'position': position,
                'price': price,
                'link': link
            }
            db[filter_uname].insert_one(doc)

    filter_items = list(db[filter_uname].find({'keyword': keyword},{'_id': 0}))
 
    return jsonify({'result': 'success', 'items': filter_items})


################################
##        메일전송 API        ##
################################

# 스케쥴링 종료시점을 정하기위한 전역변수 설정
found_item = False

@app.route('/api/mail', methods=['POST'])
def api_mail():
    keyword = request.form['keyword_give']
    max_price_receive = request.form['max_price_give']
    min_price_receive = request.form['min_price_give']
    you = request.form['you_give']
    uname = request.form['uname']

    # 최대/최소가격 입력이 없을경우 -1 / 0 저장 (int형 변환)
    temp_max = "".join(filter(str.isdigit, max_price_receive))
    temp_min = "".join(filter(str.isdigit, min_price_receive))
    
    if temp_max == '':
        max_price = -1
        min_price = int(temp_min)
    elif temp_min == '':
        min_price = 0
        max_price = int(temp_max)
    else:
        max_price = int(temp_max)
        min_price = int(temp_min)

    global found_item
    found_item = False
    
    run(keyword, max_price, min_price, you, uname)

# 스케쥴링 실행 (run)
def run(keyword, max_price, min_price, you, uname):
    sched = BackgroundScheduler()
    sched.start()

    sched.add_job(job, 'interval', seconds=30, id="test1", args=[keyword, max_price, min_price, you, uname])
    global found_item

    while True:
        print('Running schedule process!!')
        time.sleep(10)
        if found_item == True:
            sched.remove_job("test1")
            print('스케쥴링을 종료합니다.')
            return False

# 스케쥴링되어 동작 (job)
def job(keyword, max_price, min_price, you, uname):
    # 로그인ID 각각의 컬렉션을 사용 (기존에 검색한 DB데이터 삭제)
    items_uname = 'items_' + uname
    db[items_uname].remove({'keyword': keyword})
    
    # 당근마켓, 헬로마켓 크롤링
    dgmk(keyword, uname)
    hlmk(keyword, uname)

    items = list(db[items_uname].find({'keyword': keyword},{'_id': 0}))
    global found_item

    if not items:
        print('데이터가 없어 스케쥴링이 계속 실행됩니다.')
    else:
        print('데이터가 있어 메일을 전송하고 스케쥴링을 멈춥니다.')
        mailsent(you)
        found_item = True

# you에 보낼메일주소를 넘겨주면 SMTP를 이용하여 메일전송
def mailsent(you):
    me = 'cyparkdev@naver.com'
    # my_password = '메일계정 패스워드'
    msg = MIMEMultipart('alternative')

    # 메일의 header영역에 들어갈 내용 추가
    msg['Subject'] = 'Success!! jungo searching'
    msg['From'] = me
    msg['To'] = you

    # 메일의 text영역에 들어갈 내용 추가
    html = '<html><body>\
            <p>Hi, I have the following alerts for you!</p>\
            <a href="">url</a>\
            </body></html>'
    part2 = MIMEText(html, 'html')
    msg.attach(part2)

    # 네이버 메일서버에 로그인하여 메일전송
    try:
        server = smtplib.SMTP_SSL('smtp.naver.com')
        server.ehlo()
        server.login(me, my_password)
        server.sendmail(me, you, msg.as_string())
        print('Success!! Email sent')
    except:
        print('Error!! Email not sent')


#################################
##       유저별 최근검색       ##
#################################

@app.route('/final/search', methods=['POST'])
def final_search():
    uname = request.form['uname']
    items_uname = 'items_' + uname

    # 로그인중인 ID가 마지막으로 검색한 keyword로 DB데이터를 화면에 출력
    try:
        keyword_db = db.fs_keyword.find_one({'uname': uname})
        final_keyword = keyword_db['fs_keyword']
        print('final_keyword : ' + str(final_keyword))
        items = list(db[items_uname].find({'keyword': final_keyword}, {'_id': 0}))
        return jsonify({'result': 'success', 'items': items})
    except:
        print('검색기록이 없습니다.')
        return jsonify({'result': 'fail'})

# API 서버 실행 (url, Port)
if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)