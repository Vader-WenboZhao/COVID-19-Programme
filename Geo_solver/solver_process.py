import socketserver
import threading
from BasicBlockchainProcess import *
from Blockchain import *
from parameters import *

# 实例化Blockchain类
ContactTracingBlockchain = Blockchain()
NotificationBlockchain = Blockchain()
# ContactTracingBlockchain.register_node(node_identifier)

connectedAddrList = []


def notify(addrs, message):
    if len(addrs)!= 0:
        # 添加操作符, 2为发布风险用户集合
        messageToSend = {'riskyPseudonyms': message, 'ope':2}
        for addrTuple in addrs:
            addrTuple[0].sendall(bytes(str(messageToSend), encoding = "utf-8"))


def searchInBlockchain(blockchain, searchTime, searchLocation):
    searchTime = int(searchTime)
    searchResult = set()
    for block in blockchain.chain:
        for trace in block['traces']:
            trace = eval(trace)
            if (searchTime - TIMERANGE) <= int(trace['timestamp']) <= (searchTime + TIMERANGE) and trace['location'] == searchLocation:
                searchResult.add(trace['pseudonym'])
    return searchResult


def findRiskyPseudonyms(blockchain, searchTime, searchLocation):
    # 结果是个集合
    riskyPseudonyms = searchInBlockchain(blockchain, searchTime, searchLocation)
    return riskyPseudonyms




def operation_thread():
    global connectedAddrList
    while True:
        global ContactTracingBlockchain
        order = input("Input order: ")
        if order == "connect":
            connectedAddrList = connect()
        elif order == "chain":
            print(full_chain(ContactTracingBlockchain))
        elif order == "notify":
            searchT = input("Search time: ")
            searchL = input("search location: ")
            print(findRiskyPseudonyms(ContactTracingBlockchain, searchT, searchL))
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


class Handler(socketserver.BaseRequestHandler):
    def handle(self):
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
                        ContactTracingBlockchain.add_trace(newTrace)
                        if self.data['is_current_traces_full'] == True:
                            newBlockTimestamp = self.data['block_timestamp']
                            mine(ContactTracingBlockchain, newBlockTimestamp)
                            if ContactTracingBlockchain.valid_chain(ContactTracingBlockchain.chain) == False:
                                print("Invalid block!")
                                ContactTracingBlockchain.chain.pop()
                    else:
                        print("New trace is invalid!")
                # 操作符为1说明要根据时间地址查询风险用户
                elif self.data['ope'] == 3:
                    # [(t,l),(t,l),(t,l),...]
                    timeLocationList = self.data['timeLocationList']
                    riskyPseudonyms = set()
                    for TLtuple in timeLocationList:
                        riskyPseudonyms = riskyPseudonyms | findRiskyPseudonyms(ContactTracingBlockchain, TLtuple[0], TLtuple[1])
                    notify(connectedAddrList, riskyPseudonyms)
                print('-'*40)

                # print("%s say:%s"%(addr,data))
                # client.sendall(bytes(word, encoding = "utf-8"))


thread_ope = threading.Thread(target=operation_thread)
thread_ope.start()
server = socketserver.ThreadingTCPServer(listenAddr, Handler)   # 多线程交互
server.serve_forever()
