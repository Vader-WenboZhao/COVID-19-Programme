from urllib.parse import urlparse
from hashlib import sha256
from flask import Flask, jsonify, request
from multiprocessing import  Process # 多进程
import getIp

import socketserver
import threading
import requests
import json
import socket
import time
import sys

'''
可以修改的地方:
1.PORT
2.registerAddress
3.listenAddrFromPyGate的port
'''

HOST = str(getIp.get_host_ip())
PORT = 8000
print("IP Address:", HOST)

RISKYADRESS = f'http://121.4.89.43:5000/'
# 默认的注册节点
registerAddress = "http://192.168.1.105:8000"
myAddress = "http://" + HOST + ':' + str(PORT) + '/'

socketPyGate = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
socketPyGate.setblocking(True)
listenAddrFromPyGate = (HOST, 3000)
socketPyGate.bind(listenAddrFromPyGate)

riskyPseudonyms = set()

latestMessage = None

class Block:
    def __init__(self, index, traces, timestamp, previous_hash, nonce=0):
        self.index = index
        self.traces = traces
        self.timestamp = timestamp
        self.previous_hash = previous_hash
        self.nonce = nonce

    def compute_hash(self):
        """
        A function that return the hash of the block contents.
        """
        block_string = json.dumps(self.__dict__, sort_keys=True)
        return sha256(block_string.encode()).hexdigest()


class Blockchain:
    # difficulty of our PoW algorithm
    difficulty = 2

    def __init__(self):
        self.unconfirmed_traces = []
        self.chain = []

    def create_genesis_block(self):
        """
        A function to generate genesis block and appends it to
        the chain. The block has index 0, previous_hash as 0, and
        a valid hash.
        """
        genesis_block = Block(0, [], 0, "0")
        genesis_block.hash = genesis_block.compute_hash()
        self.chain.append(genesis_block)

    @property
    def last_block(self):
        return self.chain[-1]

    def add_block(self, block, proof):
        """
        A function that adds the block to the chain after verification.
        Verification includes:
        * Checking if the proof is valid.
        * The previous_hash referred in the block and the hash of latest block
          in the chain match.
        """
        previous_hash = self.last_block.hash

        if previous_hash != block.previous_hash:
            return False

        if not Blockchain.is_valid_proof(block, proof):
            return False

        block.hash = proof
        self.chain.append(block)
        return True

    @staticmethod
    def proof_of_work(block):
        """
        Function that tries different values of nonce to get a hash
        that satisfies our difficulty criteria.
        """
        block.nonce = 0

        computed_hash = block.compute_hash()
        while not computed_hash.startswith('0' * Blockchain.difficulty):
            block.nonce += 1
            computed_hash = block.compute_hash()

        return computed_hash

    def add_new_trace(self, trace):
        self.unconfirmed_traces.append(trace)

    @classmethod
    def is_valid_proof(cls, block, block_hash):
        """
        Check if block_hash is valid hash of block and satisfies
        the difficulty criteria.
        """
        return (block_hash.startswith('0' * Blockchain.difficulty) and
                block_hash == block.compute_hash())

    @classmethod
    def check_chain_validity(cls, chain):
        result = True
        previous_hash = "0"

        for block in chain:
            block_hash = block.hash
            # remove the hash field to recompute the hash again
            # using `compute_hash` method.
            delattr(block, "hash")

            if not cls.is_valid_proof(block, block_hash) or \
                    previous_hash != block.previous_hash:
                result = False
                break

            block.hash, previous_hash = block_hash, block_hash

        return result

    def mine(self):
        """
        This function serves as an interface to add the pending
        traces to the blockchain by adding them to the block
        and figuring out Proof Of Work.
        """
        if not self.unconfirmed_traces:
            return False

        last_block = self.last_block

        new_block = Block(index=last_block.index + 1,
                          traces=self.unconfirmed_traces,
                          timestamp=time.time(),
                          previous_hash=last_block.hash)

        proof = self.proof_of_work(new_block)
        self.add_block(new_block, proof)

        self.unconfirmed_traces = []

        return True


app = Flask(__name__)

# the node's copy of blockchain
blockchain = Blockchain()
blockchain.create_genesis_block()

'''
# operable
# /new_trace', POST, json, ["pseudonym", "traceTime", "location"]
# /chain, GET
# /mine, GET
# /register_with, POST, json, ["node_address"]

# automatically called
# /register_node, POST, json, ["node_address"]
# /add_block, POST, json, ["index", "traces", "timestamp", "previous_hash", "nonce"]
# /pending_tx
'''




# the address to other participating members of the network
peers = set()


# endpoint to submit a new trace. This will be used by
# our application to add new data (posts) to the blockchain
@app.route('/new_trace', methods=['POST'])
def new_trace():
    tx_data = request.get_json()
    required_fields = ["pseudonym", "traceTime", "location"]

    for field in required_fields:
        if not tx_data.get(field):
            return "Invalid trace data", 404

    # tx_data["timestamp"] = time.time()

    blockchain.add_new_trace(tx_data)
    mine_unconfirmed_traces()

    return "Success", 201


# endpoint to return the node's copy of the chain.
# Our application will be using this endpoint to query
# all the posts to display.
@app.route('/chain', methods=['GET'])
def get_chain():
    chain_data = []
    for block in blockchain.chain:
        chain_data.append(block.__dict__)
    return json.dumps({"length": len(chain_data),
                       "chain": chain_data,
                       "peers": list(peers)})


# endpoint to request the node to mine the unconfirmed
# traces (if any). We'll be using it to initiate
# a command to mine from our application itself.
@app.route('/mine', methods=['GET'])
def mine_unconfirmed_traces():
    result = blockchain.mine()
    if not result:
        return "No traces to mine"
    else:
        # Making sure we have the longest chain before announcing to the network
        chain_length = len(blockchain.chain)
        consensus()
        if chain_length == len(blockchain.chain):
            # announce the recently mined block to the network
            announce_new_block(blockchain.last_block)
        return "Block #{} is mined.".format(blockchain.last_block.index)


# 已存在的节点收到新创建的节点的请求, 并返回区块链、节点链表给该新节点,
# 用来初始化或者(离线后重新上线)同步.
# endpoint to add new peers to the network.
@app.route('/register_node', methods=['POST'])
def register_new_peers():
    # 接收别人的地址
    node_address = request.get_json()["node_address"]
    if not node_address:
        return "Invalid data", 400

    # Add the node to the peer list
    peers.add(node_address)

    # Return the consensus blockchain to the newly registered node
    # so that he can sync
    return get_chain()


# 新创建的/离线后重新上线的节点向已存在的节点发送地址信息
@app.route('/register_with', methods=['POST'])
def register_with_existing_node():
    """
    Internally calls the `register_node` endpoint to
    register current node with the node specified in the
    request, and sync the blockchain as well as peer data.
    """
    # 用户输入
    node_address = request.get_json()["node_address"]
    if not node_address:
        return "Invalid data", 400

    # 将自己的地址信息发给node_address
    data = {"node_address": request.host_url}
    headers = {'Content-Type': "application/json"}

    # Make a request to register with remote node and obtain information
    response = requests.post(node_address + "/register_node",
        data=json.dumps(data), headers=headers)

    # 收到已有节点回复的区块链、peers
    if response.status_code == 200:
        global blockchain
        global peers
        # update chain and the peers
        chain_dump = response.json()['chain']
        blockchain = create_chain_from_dump(chain_dump)
        peers.update(response.json()['peers'])
        return "Registration successful", 200
    else:
        # if something goes wrong, pass it on to the API response
        return response.content, response.status_code


def create_chain_from_dump(chain_dump):
    generated_blockchain = Blockchain()
    generated_blockchain.create_genesis_block()
    for idx, block_data in enumerate(chain_dump):
        if idx == 0:
            continue  # skip genesis block
        block = Block(block_data["index"],
                      block_data["traces"],
                      block_data["timestamp"],
                      block_data["previous_hash"],
                      block_data["nonce"])
        proof = block_data['hash']
        added = generated_blockchain.add_block(block, proof)
        if not added:
            raise Exception("The chain dump is tampered!!")
    return generated_blockchain


# endpoint to add a block mined by someone else to
# the node's chain. The block is first verified by the node
# and then added to the chain.
@app.route('/add_block', methods=['POST'])
def verify_and_add_block():
    block_data = request.get_json()
    block = Block(block_data["index"],
                  block_data["traces"],
                  block_data["timestamp"],
                  block_data["previous_hash"],
                  block_data["nonce"])

    proof = block_data['hash']
    # add_block 里有验证
    added = blockchain.add_block(block, proof)

    if not added:
        return "The block was discarded by the node", 400

    return "Block added to the chain", 201


# endpoint to query unconfirmed traces
@app.route('/pending_tx')
def get_pending_tx():
    return json.dumps(blockchain.unconfirmed_traces)


def consensus():
    """
    Our naive consnsus algorithm. If a longer valid chain is
    found, our chain is replaced with it.
    """
    global blockchain

    longest_chain = None
    current_len = len(blockchain.chain)

    for node in peers:
        response = requests.get('{}chain'.format(node)) # address/chain
        length = response.json()['length']
        chain = response.json()['chain']
        if length > current_len and blockchain.check_chain_validity(chain):
            current_len = length
            longest_chain = chain

    if longest_chain:
        blockchain = longest_chain
        return True

    return False


def announce_new_block(block):
    """
    A function to announce to the network once a block has been mined.
    Other blocks can simply verify the proof of work and add it to their
    respective chains.
    """
    for peer in peers:
        url = "{}add_block".format(peer)
        headers = {'Content-Type': "application/json"}
        requests.post(url,
                      data=json.dumps(block.__dict__, sort_keys=True),
                      headers=headers)





def renewRiskyPseudonymes():
    global RISKYADRESS
    global riskyPseudonyms

    response = requests.get(RISKYADRESS + f'risky/names')

    if response.status_code == 200:
        riskyPseudonymList = response.json()['riskyPseudonyms']
        riskyPseudonyms = set(riskyPseudonymList)
    else:
        return False, "Error in renewRiskyPseudonymes()"

    return True, "Successfully get risky pseudonyms"


def chainData():
    chain_data = []
    for block in blockchain.chain:
        chain_data.append(block.__dict__)
    return chain_data


def newTrace(name, time, loca):
    if not isinstance(name, str) or not isinstance(time, int) or not isinstance(loca, str):
        return False, 'Wrong data type'

    data = {'pseudonym':name, 'traceTime':time, 'location':loca}

    try:
        blockchain.add_new_trace(data)
        mine_unconfirmed_traces()
    except BaseException:
        return False, "newTrace() failed to add new trace"

    return True, "Successfully added new trace"


def register():
    global registerAddress
    global myAddress
    data = {'node_address': registerAddress}
    response = requests.post(myAddress + f'register_with', json=data)
    if response.status_code == 200:
        return True, "Register successfully"
    else:
        return False, "Register failed " + str(response.status_code)



def operation_thread():
    global connectedAddrList
    while True:
        try:
            global ContactTracingBlockchain
            print("Orders: register, peers, chain, trace, risky, quit")
            order = input("Input order: \n")
            if order == "trace":
                values = input("Name, time, location in list:")
                values = eval(values)
                print(newTrace(values[0], values[1], values[2])[1])
            elif order == "chain":
                print(chainData())
            elif order == "risky":
                renewRiskyPseudonymes()
                print(riskyPseudonyms)
            elif order == "register":
                print(register()[1])
            elif order == "peers":
                print(peers)
            elif order == "quit":
                return
            else:
                print("Valid order")
                pass
        except BaseException as be:
            print(be)
            continue


def recvFromPyGatePart():
    global latestMessage
    socketPyGate.listen(5)
    connection, addr = socketPyGate.accept()     # 建立客户端连接
    print("Connected successfully, PyGate part's address:", addr)
    connection.send(bytes(str(list(riskyPseudonyms)), 'utf-8'))
    while True:
        data = connection.recv(1024)
        if data == latestMessage:
            continue
        else:
            latestMessage = data
        # if not self.data:
        #     continue
        data = eval(str(data, encoding='utf-8'))
        print("receive from fixed devices:", data)
        result = newTrace(data['pseudonym'], data['timestamp'], data['location'])
        print(result[0])
        print('-'*40)
        renewRiskyPseudonymes()
        connection.send(bytes(str(list(riskyPseudonyms)), 'utf-8'))
        continue
    connection.close()


def autoSave():
    global blockchain
    workPath = sys.path[0]
    print(workPath)
    while True:
        try:
            f = open(workPath + '/blockchain.txt', 'w')
            f.write(str(chainData()))
            f.close()
            # 每分钟记录一次
            time.sleep(60)
        except BaseException as be:
            print(be, "in autoSave function")






if __name__ == '__main__':

    renewRiskyPseudonymes()

    thread_autosave = threading.Thread(target=autoSave)
    thread_autosave.start()

    thread_pygate = threading.Thread(target=recvFromPyGatePart)
    thread_pygate.start()

    thread_ope = threading.Thread(target=operation_thread)
    thread_ope.start()


    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=PORT, type=int, help='port to listen on')
    args = parser.parse_args()
    port = args.port

    app.run(host=HOST, port=port)

    '''
    server = socketserver.ThreadingTCPServer(listenAddrFromPyGate, HandlerForPyGate)   # 多线程交互
    server.serve_forever()
    '''
