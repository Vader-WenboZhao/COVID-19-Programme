# from urllib.parse import urlparse
from hashlib import sha256
from flask import Flask, jsonify, request

import threading
import requests
import json
import time
import getIp

'''
可以修改的地方:
1.PORT
2.registerAddress
'''

MyIP = getIp.get_host_ip()
# 本机IP地址
HOST = str(MyIP)
# 区块链相关端口
PORT = 5010

# 修改风险名单的网站, 腾讯云服务器
RISKYADRESS = f'http://121.4.89.43:5000/'
# 风险时间范围, 默认为2h, 前后TIMERANGE时间范围内算作有风险
TIMERANGE = 7200

# 默认的注册节点, 可修改为区块链里任意的某个节点
registerAddress = "http://192.168.1.101:8000"
# 本机的地址
myAddress = "http://" + HOST + ':' + str(PORT) + '/'


riskyPseudonyms = set()

'''
区块链部分代码的注释见RegionServerPC的代码
'''

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



# 向服务器添加风险匿名, 通过命令行操作
def addPseudonyms(nameList):
    if not isinstance(nameList, list):
        return False, "Wrong data type. Pseudonyms should be a list, now it's a " + str(type(nameList))

    for name in nameList:
        if not isinstance(name, str):
            return False, 'Wrong data type: ' + str(name) + ". Its type is " + str(type(name))

    # 函数内部是一个一个添加
    for name in nameList:
        data = {'riskyName':name}
        try:
            # 通过HTTP添加
            response = requests.post(RISKYADRESS + f'risky/add', json=data)
            # 成功
            if response.status_code == 201:
                continue
            else:
                return False, "Failed to add risky pseudonym " + name
        except BaseException as be:
            print(be)
            return False, "Failed to add risky pseudonym " + name

    return True, "Successfully add all the risky pseudonyms"



# 从服务器删除风险匿名, 通过命令行操作
def removePseudonyms(nameList):
    if not isinstance(nameList, list):
        return False, "Wrong data type. Pseudonyms should be a list, now it's a " + str(type(nameList))

    for name in nameList:
        if not isinstance(name, str):
            return False, 'Wrong data type: ' + str(name) + ". Its type is " + str(type(name))

    for name in nameList:
        data = {'riskyName':name}
        try:
            # 通过HTTP删除
            response = requests.post(RISKYADRESS + f'risky/delete', json=data)
            # 成功
            if response.status_code == 201:
                continue
            else:
                return False, "Failed to add risky pseudonym " + name
        except BaseException as be:
            print(be)
            return False, "Failed to add risky pseudonym " + name

    return True, "Successfully remove risky pseudonyms"



# 返回多个患者的多个踪迹的(时间-地点)元组
def findPatientTimeLocation(patientPseudonymList):
    global blockchain
    # patientPseudonymList是字符串列表[n, n, n, ...]
    for name in patientPseudonymList:
        if not isinstance(name, str):
            print("Error: invalid data type!")
            return False
        continue
    result = []
    for blk in blockchain.chain:
        # 没有任何trace
        if len(blockchain.chain) == 1:
            return []
        for trace in blk.traces:
            # trace = eval(trace)
            if trace['pseudonym'] in patientPseudonymList:
                # 元组形式
                result.append((trace['traceTime'], trace['location']))
    # 结果形式: [(t,l), (t,l), (t,l), ...]
    return result



# 根据时间和地点查找风险匿名
def findRiskyPseudonyms(searchTime, searchLocation):
    global blockchain

    searchTime = int(searchTime)
    searchResult = set()
    for block in blockchain.chain:
        for trace in block.traces:
            # trace = eval(trace)
            if (searchTime - TIMERANGE) <= int(trace['traceTime']) <= (searchTime + TIMERANGE) and trace['location'] == searchLocation:
                searchResult.add(trace['pseudonym'])
    # searchResult是一个字符串集合
    return searchResult


# 操作 findPatientTimeLocation, findRiskyPseudonyms, addPseudonyms
def addRiskyPseudonyms(patientPseudonymList):
    global blockchain
    # patientTimeLocationTuples形式: [(t,l), (t,l), (t,l), ...]
    patientTimeLocationTuples = findPatientTimeLocation(patientPseudonymList)

    # 这些患者没有轨迹
    if len(patientTimeLocationTuples) == 0:
        return addPseudonyms(patientPseudonymList)

    for TLtuple in patientTimeLocationTuples:
        # riskyPseudonyms是个集合
        riskyPseudonyms = findRiskyPseudonyms(TLtuple[0], TLtuple[1])
        riskyPseudonyms = list(riskyPseudonyms)
    # 返回类型是 (Bool, str)
    return addPseudonyms(riskyPseudonyms)



# 操作 removePseudonyms
def deleteRiskyPseudonym(riskyPseudonymList):
    # riskyPseudonymList是个字符串列表
    for name in riskyPseudonymList:
        if not isinstance(name, str):
            print("Error: invalid data type!")
            return False
        continue
    # return (Bool, str)
    return removePseudonyms(riskyPseudonymList)


# 打印区块链,先将区块链转化为字典组成的列表
def printChain():
    chain_data = []
    for block in blockchain.chain:
        chain_data.append(block.__dict__)
    print(chain_data)
    return


# 在区块链里注册节点
def register():
    global registerAddress
    global myAddress
    data = {'node_address': registerAddress}
    response = requests.post(myAddress + f'register_with', json=data)
    if response.status_code == 200:
        return True, "Register successfully"
    else:
        return False, "Register failed " + str(response.status_code)



#
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


# 操作进程, 命令行
def operation_thread():
    while True:
        try:
            global blockchain
            renewRiskyPseudonymes()
            print("Orders: register, peers, risky, add, delete, chain, quit")
            order = input("Input order: ")
            if order == "register":
                print(register()[1])
            elif order == "peers":
                print(peers)
            elif order == "add":
                # 输入list
                patientPseudonymList = input("patient's pseudonyms, in the form of list: ")
                patientPseudonymList = eval(patientPseudonymList)
                print(addRiskyPseudonyms(patientPseudonymList)[1])
            elif order == "delete":
                # 输入list
                riskyPseudonymListToDelete = input("risky pseudonyms to delete, in the form of list: ")
                riskyPseudonymListToDelete = eval(riskyPseudonymListToDelete)
                print(deleteRiskyPseudonym(riskyPseudonymListToDelete)[1])
            elif order == "chain":
                printChain()
            elif order == "risky":
                print(riskyPseudonyms)
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
