from urllib.parse import urlparse

import socketserver
import threading
import requests
from flask import Flask, jsonify, request
import json

BPSCARRESS = f'http://127.0.0.1:5000/'
HOST = '0.0.0.0'
PORT = 5001

listenAddrFromPyGate = ('127.0.0.1', 8091)

riskyPseudonyms = set()


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


@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200


@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()

    nodes = values.get('nodes')
    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(blockchain.nodes),
    }
    return jsonify(response), 201


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


@app.route('/newtrace', methods=['POST'])
def add_new_trace():
    values = request.get_json()

    required = ['pseudonym', 'timestamp', 'location']
    if not all(k in values for k in required):
        return 'Missing values', 400

    pseudonym = values.get('pseudonym')
    timestamp = values.get('timestamp')
    location = values.get('location')

    if not isinstance(pseudonym, str) or not isinstance(timestamp, int) or not isinstance(location, str):
        return 'Wrong data type', 400

    data = {'pseudonym':pseudonym, 'timestamp':timestamp, 'location':location}

    try:
        requests.post(BPSCARRESS + f'traces/new', json=data)
    except BaseException:
        return "Failed to add new trace", 400

    return "Successfully added new trace", 201


@app.route('/riskyNames', methods=['GET'])
def get_risky_Pseudonymes():
    global riskyPseudonyms

    response = requests.get(BPSCARRESS + f'risky/names')

    if response.status_code == 200:
        riskyPseudonymList = response.json()['riskyPseudonyms']
        riskyPseudonyms = set(riskyPseudonymList)
    else:
        return "Error", 400

    return jsonify(list(riskyPseudonyms)), 200



def newTrace(name, time, loca):
    if not isinstance(name, str) or not isinstance(time, int) or not isinstance(loca, str):
        return 'Wrong data type', 400

    data = {'pseudonym':name, 'timestamp':time, 'location':loca}

    try:
        requests.post(BPSCARRESS + f'traces/new', json=data)
    except BaseException:
        return "Failed to add new trace"

    return "Successfully added new trace"


def renewRiskyPseudonymes():
    global riskyPseudonyms

    response = requests.get(BPSCARRESS + f'risky/names')

    if response.status_code == 200:
        riskyPseudonymList = response.json()['riskyPseudonyms']
        riskyPseudonyms = set(riskyPseudonymList)
    else:
        return "Error"

    return "Successfully got risky pseudonyms"


def operation_thread():
    global connectedAddrList
    while True:
        try:
            global ContactTracingBlockchain
            order = input("Input order: ")
            if order == "add trace":
                values = input("Name, time, location in list:")
                values = eval(values)
                print(newTrace(values[0], values[1], values[2]))
            elif order == "chain":
                blockchain.smart_chain()
                print(blockchain.chain)
            elif order == "risky names":
                renewRiskyPseudonymes()
                print(riskyPseudonyms)
            elif order == "quit":
                return
            else:
                print("Valid order")
                pass
        except BaseException as be:
            print(be)
            continue


# 处理PyGate部分发来的数据
class HandlerForPyGate(socketserver.BaseRequestHandler):
    def handle(self):
        while True:
            print('Connected')
            while True:
                self.data = self.request.recv(1024)
                print('address:', self.client_address)
                if not self.data:
                    continue

                self.data = eval(str(self.data, encoding='utf-8'))
                print(self.data)
                result = newTrace(self.data['pseudonym'], self.data['timestamp'], self.data['location'])
                print(result[0])
                print('-'*40)

                continue


if __name__ == '__main__':

    # server = socketserver.ThreadingTCPServer(listenAddrFromPyGate, HandlerForPyGate)   # 多线程交互
    # server.serve_forever()

    thread_ope = threading.Thread(target=operation_thread)
    thread_ope.start()

    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=PORT, type=int, help='port to listen on')
    args = parser.parse_args()
    port = args.port

    app.run(host=HOST, port=port)
