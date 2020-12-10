import hashlib
import json
from time import time
from urllib.parse import urlparse

import requests
from flask import Flask, jsonify, request


IPADDRESS = f'http://127.0.0.1:5000/'
HOST = '0.0.0.0'
PORT = 5000


# Instantiate the Node
app = Flask(__name__)

# riskyPseudonyms = set()
# 测试
riskyPseudonyms = set(['HanYe', 'HanBin', 'YuGuangqian'])



# 风险名单操作

@app.route('/risky/names', methods=['GET'])
def get_risky():
    global riskyPseudonyms
    response = {
    # set不能Json化
        'riskyPseudonyms': list(riskyPseudonyms)
    }

    return jsonify(response), 200


@app.route('/risky/add', methods=['POST'])
def add_risky():
    global riskyPseudonyms

    values = request.get_json()

    name = values.get('riskyName')
    if not isinstance(name, str):
        return "Error: Please supply a valid pseudonym", 400

    riskyPseudonyms.add(name)

    return "Added successfully", 201


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
