import socketserver
import threading
from BasicBlockchainProcess import *
from Blockchain import *
from parameters import *
import time

# outdoor
# listenAddrFromPyGate = ('172.20.10.3', 8081)
# indoor
listenAddrFromPyGate = ('192.168.1.100', 8091)
listenAddrFromNodes = ('192.168.1.100', 8093)

# 实例化Blockchain类
ContactTracingBlockchain = Blockchain()
NotificationBlockchain = Blockchain()
# ContactTracingBlockchain.register_node(node_identifier)

connectedAddrList = []
riskyPseudonymList = set()


def operation_thread():
    global connectedAddrList
    while True:
        try:
            global ContactTracingBlockchain
            order = input("Input order: ")
            if order == "connect":
                connectedAddrList = connect()

            # 改成自动的
            # elif order == "add trace":
            #     pseudonymList = input("pseudonym list: ")
            #     print(new_traces(ContactTracingBlockchain, connectedAddrList, pseudonymList))
            elif order == "chain":
                print(full_chain(ContactTracingBlockchain))
            # 不知道啥意思
            # elif order == "register node":
            #     print(register_nodes(ContactTracingBlockchain))
            elif order == "risky list":
                print(riskyPseudonymList)
            # elif order == "resolve conflicts":
            #     print(consensus(ContactTracingBlockchain))
            elif order == "quit":
                quit(connectedAddrList)
                if len(connectedAddrList) != 0:
                    for addrTuple in connectedAddrList:
                        addrTuple[0].close()
                print("Connection breaks")
                return
            else:
                print("Valid order")
                pass
        except BaseException as be:
            print(be)
            continue


# 处理其他地区服务器发来的数据
class HandlerForNodes(socketserver.BaseRequestHandler):
    def handle(self):
        global riskyPseudonymList
        while True:
            print('Connected')
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
                print(self.data)
                # 操作符为1说明新的trace
                if self.data['ope'] == 1:
                    newTrace = Trace(self.data['pseudonym'], self.data['location'], self.data['timestamp'], self.data['signature'])
                    if newTrace.verify(PUB_KEY_PATH):
                        ContactTracingBlockchain.add_trace(newTrace)
                        if self.data['is_current_traces_full'] == True:
                            newBlockTimestamp = self.data['block_timestamp']
                            mine(ContactTracingBlockchain, newBlockTimestamp)
                            if ContactTracingBlockchain.valid_chain(ContactTracingBlockchain.chain) == False:
                                print("Invalid block!")
                                ContactTracingBlockchain.chain.pop()
                    else:
                        print("New trace is invalid!")
                # 操作符为2说明风险名单
                elif self.data['ope'] == 2:
                    # 风险名单集合求并集
                    riskyPseudonymList = self.data['riskyPseudonyms']
                    print(riskyPseudonymList)
                print('-'*40)

                # print("%s say:%s"%(addr,data))
                # client.sendall(bytes(word, encoding = "utf-8"))

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
                result = new_traces(ContactTracingBlockchain, connectedAddrList, self.data['pseudonym'], self.data['location'], self.data['timestamp'])
                print(result)
                print('-'*40)

                continue


def blockchainMaintain_thread(blockchain):
    while(True):
        try:
            blockchain.deleteOldBlock()
            # 每10分钟维护一次
            time.sleep(600)
        except BaseException as be:
            print(be)
            continue


thread_ope = threading.Thread(target=operation_thread)
thread_ope.start()

server = socketserver.ThreadingTCPServer(listenAddrFromPyGate, HandlerForPyGate)   # 多线程交互
server.serve_forever()

# server = socketserver.ThreadingTCPServer(listenAddrFromNodes, HandlerForNodes)   # 多线程交互
# server.serve_forever()

thread_maintain = threading.Thread(target=blockchainMaintain_thread, args=(ContactTracingBlockchain,))
thread_maintain.start()
