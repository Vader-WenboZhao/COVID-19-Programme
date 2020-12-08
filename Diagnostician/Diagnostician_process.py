from urllib.parse import urlparse

import socketserver
import threading
import requests
from flask import Flask, jsonify, request
import json
import socket
import time

# 连接到地理位置服务器
GEOSERVERADDRESS = ('127.0.0.1', 8081)
BPSCARRESS = f'http://127.0.0.1:5000/'
HOST = '0.0.0.0'
PORT = 5010

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





# 返回多个患者的多个踪迹的(时间-地点)元组
def findPatientTimeLocation(blkchain, patientPseudonymList):
    # patientPseudonymList是字符串列表[n, n, n, ...]
    for name in patientPseudonymList:
        if not isinstance(name, str):
            print("Error: invalid data type!")
            return False
        continue

    result = []
    print("patientPseudonymList:", patientPseudonymList)
    for block in blkchain.chain:
        for trace in block['traces']:
            # trace = eval(trace)
            if trace['pseudonym'] in patientPseudonymList:
                # 元组形式
                result.append((trace['timestamp'], trace['location']))
    # 结果形式: [(t,l), (t,l), (t,l), ...]
    return result


# 将患者踪迹的(时间-地点)元组列表发送给地理位置服务器
def notifyGeoSolver(blkchain, patientPseudonymList):
    # 更新区块链
    blkchain.smart_chain()
    # patientTimeLocationTuples形式: [(t,l), (t,l), (t,l), ...]
    patientTimeLocationTuples = findPatientTimeLocation(blkchain, patientPseudonymList)
    # 添加操作符, 3为上传风险时间地址
    messageToSend = {'ope':3, 'timeLocationList':patientTimeLocationTuples}

    # 连接Geo Server
    GeoSocket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    while True:
        try:
            GeoSocket.connect(GEOSERVERADDRESS)
            break
        except BaseException as be:
            print(be)
            continue

    # 发送失败则重复发送
    retryCount = 0
    while retryCount < 5:
        try:
            GeoSocket.sendall(bytes(str(messageToSend), encoding = "utf-8"))
            GeoSocket.close()
            break
        except BaseException as be:
            print(be)
            retryCount += 1
            time.sleep(1)
            continue
    if retryCount < 5:
        return True
    else:
        GeoSocket.close()
        return False


# 请求地理位置服务器删除名单里的名字
def deleteRiskyPseudonym(riskyPseudonymList):
    # riskyPseudonymList是个字符串列表
    for name in riskyPseudonymList:
        if not isinstance(name, str):
            print("Error: invalid data type!")
            return False
        continue

    # 连接Geo Server
    GeoSocket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)

    while True:
        try:
            GeoSocket.connect(GEOSERVERADDRESS)
            break
        except BaseException as be:
            print(be)
            continue

    # 添加操作符, 4为删除风险假名
    messageToSend = {'ope':4, 'riskyPseudonymList':riskyPseudonymList}

    # 发送失败则重复发送
    retryCount = 0
    while retryCount < 5:
        try:
            GeoSocket.sendall(bytes(str(messageToSend), encoding = "utf-8"))
            GeoSocket.close()
            break
        except BaseException as be:
            print(be)
            retryCount += 1
            time.sleep(1)
            continue
    if retryCount < 5:
        return True
    else:
        GeoSocket.close()
        return False


# register node 和 quit 还没写
def operation_thread():
    while True:
        try:
            global blockchain
            order = input("Input order: ")
            if order == "register":
                pass
            elif order == "add names":
                # 输入list
                patientPseudonymList = input("patient's pseudonyms, in the form of list: ")
                patientPseudonymList = eval(patientPseudonymList)
                notifyGeoSolver(blockchain, patientPseudonymList)
            elif order == "delete names":
                # 输入list
                riskyPseudonymListToDelete = input("risky pseudonyms to delete, in the form of list: ")
                riskyPseudonymListToDelete = eval(riskyPseudonymListToDelete)
                deleteRiskyPseudonym(riskyPseudonymListToDelete)
            elif order == "quit":
                pass
            else:
                print("Invalid order")
        except BaseException as be:
            print(be)
            continue




if __name__ == '__main__':

    thread_ope = threading.Thread(target=operation_thread)
    thread_ope.start()

    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=PORT, type=int, help='port to listen on')
    args = parser.parse_args()
    port = args.port

    app.run(host=HOST, port=port)
