import hashlib
import json
from time import time
from urllib.parse import urlparse

import requests
from flask import Flask, jsonify, request


# 云服务器的公网IPv4地址是121.4.89.43
HOST = '0.0.0.0'
PORT = 5000


# Instantiate the Node
app = Flask(__name__)

riskyPseudonyms = set()


'''
都是基于Flask框架
'''

# 获取风险名单
@app.route('/risky/names', methods=['GET'])
def get_risky():
    global riskyPseudonyms
    response = {
    # set不能Json化
        'riskyPseudonyms': list(riskyPseudonyms)
    }

    return jsonify(response), 200


# 添加风险匿名信息, 只能一次添加一个
@app.route('/risky/add', methods=['POST'])
def add_risky():
    global riskyPseudonyms

    values = request.get_json()

    name = values.get('riskyName')
    if not isinstance(name, str):
        return "Error: Please supply a valid pseudonym", 400

    riskyPseudonyms.add(name)

    return "Added successfully", 201


# 删除风险匿名信息, 只能一次删除一个
@app.route('/risky/delete', methods=['POST'])
def delete_risky():
    global riskyPseudonyms

    values = request.get_json()

    name = values.get('riskyName')
    if not isinstance(name, str):
        return "Error: Please supply a valid pseudonym", 400

    if riskyPseudonyms.__contains__(name):
        riskyPseudonyms.remove(name)
        return "Deleted successfully", 201
    else:
        return "Deleted successfully", 201



if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=PORT, type=int, help='port to listen on')
    args = parser.parse_args()
    port = args.port

    app.run(host=HOST, port=port)
