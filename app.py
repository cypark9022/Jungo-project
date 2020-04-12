from pymongo import MongoClient

from flask import Flask, render_template, jsonify, request, redirect

import requests
from bs4 import BeautifulSoup
from selenium import webdriver

app = Flask(__name__)

client = MongoClient('localhost', 27017)
db = client.jungo


@app.route('/')
def home():
    return render_template('login_index.html')


# @app.route('/member', methods=['GET'])
# def member_page():
#     return render_template('member_index.html')


# 회원정보에 동일한 아이디가 있는지 확인
@app.route('/member/check', methods=['POST'])
def member_check():
    uid_receive = request.form['uid_give']
    member = db.member.find_one({'uid': uid_receive})
    if member == None:
        return jsonify({'result': 'new'})
    else:
        return jsonify({'result': 'old'})
## 동시에 같은아이디로 회원가입할 경우, 에러발생가능!!(mongoDB의 _id 로 확인 필요)


# 입력받은 회원정보를 DB에 저장
@app.route('/member/save', methods=['POST'])
def member_save():
    uid_receive = request.form['uid_give']
    upw_receive = request.form['upw_give']
    uname_receive = request.form['uname_give']

    member = {'uid': uid_receive, 'upw': upw_receive, 'uname': uname_receive}
    db.member.insert_one(member)

    return jsonify({'result': 'success'})


# API 서버 실행 (url, Port)
if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)