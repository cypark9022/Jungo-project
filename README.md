# Jungo-project
개인프로젝트 - 중고거래 웹서버
* 당근마켓, 헬로마켓 중고거래 사이트에있는 상품들을 크롤링
* 필터링을 이용하여 원하는가격, 지역의 데이터를 조회
* 메일예약 기능을 이용하여 필터링조건에 맞을경우 메일전송

## Requirements
* MongoDB
* ChromeDriver

[ Python 패키지 ]
* Flask
* pymongo
* PyJWT
* beautifulsoup4
* selenium
* apscheduler

## Need to change
* (L5) MongoDB에 연결에주는 부분을 본인환경에 맞게 수정
```
default) client = MongoClient('localhost', 27107)
change) client = MongoClient('mongodb://id:password@IP', Port)
ex) client = MongoClient('mongodb://test:test123@192.168.0.100', 27107)
```
* (L114) ChromeDriver 경로 - 본인환경의 드라이버 파일이 있는 경로로 수정
```
ex) chrome_path = '/usr/bin/chromedriver'
```
* (L497~498) SMTP 사용할 메일계정 입력 (메일전송할 본인의 네이버 계정을 입력)

## How To Use
```
nohup python app.py &
```
