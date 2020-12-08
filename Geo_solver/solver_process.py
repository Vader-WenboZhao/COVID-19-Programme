from urllib.parse import urlparse

import socketserver
import threading
import requests
from flask import Flask, jsonify, request
import json
import socket

BPSCARRESS = f'http://127.0.0.1:5000/'
HOST = '0.0.0.0'
PORT = 8082

TIMERANGE = 60 # 1 min

LISTENADDRESS = ('127.0.0.1', 8081)


class Smart_Blockchain:
    def __init__(self):
        self.chain = []
        self.nodes = set()


    def register_node(self, address):
        """
        Add a new node to the list of nodes
        :param address: Address of node. Eg. 'http://192.168.0.5:5000'
        """

        parsed_url = urlparse(address)
        if parsed_url.netloc:
            self.nodes.add(parsed_url.netloc)
        elif parsed_url.path:
            # Accepts an URL without scheme like '192.168.0.5:5000'.
            self.nodes.add(parsed_url.path)
        else:
            raise ValueError('Invalid URL')


    def smart_chain(self):
        """
        All nodes can receive the smart_chain
        """

        schain = None
        response = requests.get(BPSCARRESS + f'chain')

        if response.status_code == 200:
            chain = response.json()['chain']
            schain = chain

        # Replace our chain
        if schain:
            self.chain = schain
            return True

        return False



# Instantiate the Node
app = Flask(__name__)

# Instantiate the Smart_Blockchain
blockchain = Smart_Blockchain()


@app.route('/smart/chain', methods=['GET'])
def smart_chain():
    replaced = blockchain.smart_chain()

    if replaced:
        response = {
            'message': 'Smart chain update by bpsc',
            'smart chain': blockchain.chain,
            'length': len(blockchain.chain)
        }
    else:
        response = {
            'message': 'Unsuccessful: Please try again',
            'old chain': blockchain.chain,
            'length': len(blockchain.chain)
        }

    return jsonify(response), 200



@app.route('/addName', methods=['POST'])
def addName():
    values = request.get_json()

    required = ['pseudonyms']
    if not all(k in values for k in required):
        return 'Missing values', 400

    # pseudonyms是字符串列表
    pseudonyms = values.get('pseudonyms')

    if not isinstance(pseudonyms, list):
        return "Wrong data type. Pseudonyms should be a list, now it's a " + str(type(pseudonyms)), 400

    for name in pseudonyms:
        if not isinstance(name, str):
            return 'Wrong data type: ' + str(name) + ". Its type is " + str(type(name)), 400

    for name in pseudonyms:
        data = {'riskyName':name}
        try:
            response = requests.post(BPSCARRESS + f'risky/add', json=data)
            if response.status_code == 201:
                continue
            else:
                return "Failed to add risky pseudonym " + name, 400
        except BaseException as be:
            print(be)
            return "Failed to add risky pseudonym " + name, 400

    return "Successfully add all the risky pseudonyms", 200



@app.route('/removeName', methods=['POST'])
def removeName():
    values = request.get_json()

    required = ['pseudonyms']
    if not all(k in values for k in required):
        return 'Missing values', 400

    # pseudonyms是字符串列表
    pseudonyms = values.get('pseudonyms')

    if not isinstance(pseudonyms, list):
        return "Wrong data type. Pseudonyms should be a list, now it's a " + str(type(pseudonyms)), 400

    for name in pseudonyms:
        if not isinstance(name, str):
            return 'Wrong data type: ' + str(name) + ". Its type is " + str(type(name)), 400

    for name in pseudonyms:
        data = {'riskyName':name}
        try:
            response = requests.post(BPSCARRESS + f'risky/delete', json=data)
            if response.status_code == 201:
                continue
            else:
                return "Failed to add risky pseudonym " + name, 400
        except BaseException as be:
            print(be)
            return "Failed to add risky pseudonym " + name, 400

    return "Successfully remove risky pseudonyms", 200



def renewChain():
    blockchain.smart_chain()
    return True


# 根据时间和地点查找风险匿名
def findRiskyPseudonyms(searchTime, searchLocation):
    renewChain()
    searchTime = int(searchTime)
    searchResult = set()
    for block in blockchain.chain:
        for trace in block['traces']:
            # trace = eval(trace)
            if (searchTime - TIMERANGE) <= int(trace['timestamp']) <= (searchTime + TIMERANGE) and trace['location'] == searchLocation:
                searchResult.add(trace['pseudonym'])
    # searchResult是一个字符串集合
    return searchResult


def addPseudonyms(nameList):
    if not isinstance(nameList, list):
        return "Wrong data type. Pseudonyms should be a list, now it's a " + str(type(nameList)), 400

    for name in nameList:
        if not isinstance(name, str):
            return 'Wrong data type: ' + str(name) + ". Its type is " + str(type(name)), 400

    for name in nameList:
        data = {'riskyName':name}
        try:
            response = requests.post(BPSCARRESS + f'risky/add', json=data)
            if response.status_code == 201:
                continue
            else:
                return False, "Failed to add risky pseudonym " + name
        except BaseException as be:
            print(be)
            return False, "Failed to add risky pseudonym " + name

    return True, "Successfully add all the risky pseudonyms"



def removePseudonyms(nameList):
    if not isinstance(nameList, list):
        return "Wrong data type. Pseudonyms should be a list, now it's a " + str(type(nameList)), 400

    for name in nameList:
        if not isinstance(name, str):
            return 'Wrong data type: ' + str(name) + ". Its type is " + str(type(name)), 400

    for name in nameList:
        data = {'riskyName':name}
        try:
            response = requests.post(BPSCARRESS + f'risky/delete', json=data)
            if response.status_code == 201:
                continue
            else:
                return False, "Failed to add risky pseudonym " + name
        except BaseException as be:
            print(be)
            return False, "Failed to add risky pseudonym " + name

    return True, "Successfully remove risky pseudonyms"



def operation_thread():
    global connectedAddrList
    while True:
        try:
            global ContactTracingBlockchain
            order = input("Input order: ")
            if order == "add names":
                pass
            elif order == "remove names":
                pass
            else:
                print("Invalid order!")
        except BaseException as be:
            print(be)
            continue


class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        while True:
            print('waiting for connect')
            self.data = self.request.recv(1024) # 接收
            print('address:', self.client_address)
            # self.request.send(self.data.upper()) # 发送
            if not self.data:
                break
            if self.data== b'quit':
                print('abort connection....')
                # client.send(b'close')
                break
            # 这里signature还是bytes类型
            self.data = eval(str(self.data, encoding='utf-8'))
            # 操作符为3说明要根据时间地址查询并添加风险用户
            if self.data['ope'] == 3:
                # [(t,l),(t,l),(t,l),...]
                timeLocationList = self.data['timeLocationList']
                if len(timeLocationList) == 0:
                    print("No trace data")
                    break
                for TLtuple in timeLocationList:
                    # riskyPseudonyms是个集合
                    riskyPseudonyms = findRiskyPseudonyms(TLtuple[0], TLtuple[1])
                    riskyPseudonyms = list(riskyPseudonyms)
                result = addPseudonyms(riskyPseudonyms)
                print(result[1])
                break
            # 操作符为4说明要清除风险用户
            elif self.data['ope'] == 4:
                # [(n),(n),(n),...]
                riskyPseudonymListToDelete = self.data['riskyPseudonymList']
                result = removePseudonyms(riskyPseudonymListToDelete)
                print(result[1])
                break
            else:
                break
            print('-'*40)

                # print("%s say:%s"%(addr,data))
                # client.sendall(bytes(word, encoding = "utf-8"))


if __name__ == '__main__':

    server = socketserver.ThreadingTCPServer(LISTENADDRESS, Handler)
    server.serve_forever()

    thread_ope = threading.Thread(target=operation_thread)
    thread_ope.start()

    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=PORT, type=int, help='port to listen on')
    args = parser.parse_args()
    port = args.port

    app.run(host=HOST, port=port)
