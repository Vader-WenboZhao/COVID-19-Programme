import socket
import json
import threading
import socketserver
from Blockchain import *
from Trace import Trace


PRI_KEY_PATH = '/Users/zhaowenbo/wilna305/Fang3/项目/Geo_solver/Signature_Functions/private_Geo_solver.rsa'
PUB_KEY_PATH = '/Users/zhaowenbo/wilna305/Fang3/项目/Geo_solver/Signature_Functions/public_Geo_solver.rsa'
LOCATION = 'Shenzhen'

sendSocket1 = socket.socket(socket.AF_INET,socket.SOCK_STREAM)

# sendAddr = ('127.0.0.1', 8081)
listenAddr = ('127.0.0.1', 8082)

addr_Dalian = ('127.0.0.1', 8081)

addrList = [(sendSocket1, addr_Dalian)]


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
    if len(addrList)!=0:
        for addrTuple in addrList:
            addrTuple[0].connect(addrTuple[1])
    print("Connected successfully")

# 创建交trace请求
def new_traces(blockchain):
    pseudonym = input("Pseudonym: ")

    #创建一个新的交易, 每满BLOCKLENGTH个traces就产生一个块
    returnResult = blockchain.new_trace(pseudonym, False, LOCATION, PRI_KEY_PATH)
    index = returnResult[0]
    newTrace = returnResult[1]
    if len(addrList)!= 0:
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
        for addrTuple in addrList:
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


def quit():
    if len(addrList)!= 0:
        '''这里可以使用多线程来发送'''
        for addrTuple in addrList:
            addrTuple[0].sendall(bytes("quit", encoding = "utf-8"))


'''
# 解决冲突
def consensus(blockchain):
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': blockchain.chain
        }

    return response
'''

# 实例化Blockchain类
blkchn = Blockchain()
# blkchn.register_node(node_identifier)

def operation_thread():
    while True:
        order = input("Input order: ")
        if order == "connect":
            connect()
        elif order == "add trace":
            print(new_traces(blkchn))
        elif order == "chain":
            print(full_chain(blkchn))
        elif order == "register node":
            print(register_nodes(blkchn))
        # elif order == "resolve conflicts":
        #     print(consensus(blkchn))
        elif order == "quit":
            quit()
            if len(addrList) != 0:
                for addrTuple in addrList:
                    addrTuple[0].close()
            print("Connection breaks")
            return
        else:
            print("Valid order")
            pass


class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        global blkchn
        while True:
            print('waiting for connect')
            while True:
                self.data = self.request.recv(1024) # 接收
                print('address:', self.client_address)
                # self.request.send(self.data.upper()) # 发送
                if not self.data:
                    continue
                if self.data== b'quit':
                    print('abort connection....')
                    # client.send(b'close')
                    client.close()
                    break
                # 这里signature还是bytes类型
                self.data = eval(str(self.data, encoding='utf-8'))
                # 操作符为1说明新的trace
                if self.data['ope'] == 1:
                    newTrace = Trace(self.data['pseudonym'], self.data['location'], self.data['timestamp'], self.data['signature'])
                    if newTrace.verify(PUB_KEY_PATH):
                        blkchn.add_trace(newTrace)
                        if self.data['is_current_traces_full'] == True:
                            newBlockTimestamp = self.data['block_timestamp']
                            mine(blkchn, newBlockTimestamp)
                            if blkchn.valid_chain(blkchn.chain) == False:
                                print("Valid block!")
                                blkchn.chain.pop()
                    else:
                        print("New trace is invalid!")
                elif self.data['ope'] == 2:
                    print(self.data)
                print('-'*40)

                # print("%s say:%s"%(addr,data))
                # client.sendall(bytes(word, encoding = "utf-8"))


thread_ope = threading.Thread(target=operation_thread)
thread_ope.start()
server = socketserver.ThreadingTCPServer(listenAddr, Handler)   # 多线程交互
server.serve_forever()
