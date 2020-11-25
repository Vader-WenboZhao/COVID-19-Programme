import socket
import json
import threading
import socketserver
from Blockchain import *
from Trace import Trace
from parameters import *


# 为该节点生成一个全局惟一的地址
node_identifier = str(uuid4()).replace('-','')





# 挖矿(无奖赏)
def mine(blockchain, timestamp=None):
    # 运行工作算法的证明来获得下一个证明。
    if timestamp == None:
        last_block = blockchain.last_block
        last_proof = last_block['proof']
        proof = blockchain.proof_of_work(last_proof)

        # 通过将其添加到链中来构建新的块
        previous_hash = blockchain.hash(last_block)
        block = blockchain.new_block(proof,previous_hash)
    else:
        last_block = blockchain.last_block
        last_proof = last_block['proof']
        proof = blockchain.proof_of_work(last_proof)

        # 通过将其添加到链中来构建新的块
        previous_hash = blockchain.hash(last_block)
        block = blockchain.new_block(proof,previous_hash, timestamp)

def connect():
    global addrList
    connectedAddrList = []
    if len(addrList)!=0:
        for addrTuple in addrList:
            try:
                addrTuple[0].connect(addrTuple[1])
            except BaseException as e:
                print(e)
                continue
            connectedAddrList.append(addrTuple)

    print("Connected successfully")
    return connectedAddrList

# 创建交trace请求
def new_traces(blockchain, connectedAddrList, nameList):
    pseudonymList = eval(nameList)

    #创建一个新的交易, 每满BLOCKLENGTH个traces就产生一个块
    for pseudonym in pseudonymList:
        returnResult = blockchain.new_trace(pseudonym, False, LOCATION, PRI_KEY_PATH)
        index = returnResult[0]
        newTrace = returnResult[1]
        if len(connectedAddrList)!= 0:
            messageToSend = newTrace.dictForm()
            # 添加操作符, 1为新增trace
            messageToSend['ope'] = 1
            # 通过确定块内最后一条trace来统一新的区块的timestamp
            if len(blockchain.current_traces) == BLOCKLENGTH:
                messageToSend['is_current_traces_full'] = True
                mine(blockchain)
                blockTimestamp = blockchain.chain[-1]['timestamp']
                messageToSend['block_timestamp'] = blockTimestamp
            else:
                messageToSend['is_current_traces_full'] = False
            for addrTuple in connectedAddrList:
                addrTuple[0].sendall(bytes(str(messageToSend), encoding = "utf-8"))
        response = {'message': f'trace will be added to Block {index}'}
    return response


# 获取所有块的信息
def full_chain(blockchain):
    response = {'chain': blockchain.chain, 'length':len(blockchain.chain)}
    if blockchain.valid_chain(blockchain.chain):
        print("Chain is valid")
    else:
        print("Chain is invalid!")
    return response


# 添加节点
def  register_nodes(blockchain):
    newNode = input("Input your new node address: ")
    if newNode is None:
        return "Error: Please supply a valid node address", 400

    blockchain.register_node(newNode)

    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(blockchain.nodes),
    }
    return response


def quit(connectedAddrList):
    if len(connectedAddrList)!= 0:
        '''这里可以使用多线程来发送'''
        for addrTuple in connectedAddrList:
            addrTuple[0].sendall(bytes("quit", encoding = "utf-8"))
