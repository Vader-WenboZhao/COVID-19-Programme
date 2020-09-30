import socketserver
import threading
from BasicBlockchainProcess import *
from Blockchain import *
from parameters import *
import time

# 实例化Blockchain类
ContactTracingBlockchain = Blockchain()
NotificationBlockchain = Blockchain()
# ContactTracingBlockchain.register_node(node_identifier)

connectedAddrList = []
riskyPseudonymSet = set()


def operation_thread():
    global connectedAddrList
    while True:
        try:
            global ContactTracingBlockchain
            order = input("Input order: ")
            if order == "connect":
                connectedAddrList = connect()
            elif order == "chain":
                print(full_chain(ContactTracingBlockchain))
            elif order == "register node":
                print(register_nodes(ContactTracingBlockchain))
            elif order == "risky names":
                print(riskyPseudonymSet)
            elif order == "current traces":
                print(ContactTracingBlockchain.current_traces)
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


class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        global riskyPseudonymSet
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
                # 操作符为2说明风险名单
                elif self.data['ope'] == 2:
                    # 风险名单集合求6
                    riskyPseudonymSet = self.data['riskyPseudonyms']
                    print(riskyPseudonymSet)
                print('-'*40)

                # print("%s say:%s"%(addr,data))
                # client.sendall(bytes(word, encoding = "utf-8"))


def blockchainMaintain_thread(blockchain):
    while(True):
        try:
            blockchain.deleteOldBlock()
            # 每10分钟维护一次
            time.sleep(600)
        except BaseException as be:
            print(be)
            continue



def udpServer():
    socketToMobileDevice = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    socketToMobileDevice.bind(udpServerAddr)

    while True:
        recvData, (remoteHost, remotePort) = socketToMobileDevice.recvfrom(1024)
        # print("[%s:%s] connect" % (remoteHost, remotePort))     # 接收客户端的ip, port
        recvData = eval(str(recvData, encoding='utf-8'))
        # recvData['traces']是字典结构
        if len(recvData['traces'])!=0:
            new_traces(ContactTracingBlockchain, connectedAddrList, recvData['traces'])
        ACKMessage = {"number":recvData['number'], 'ACK': True, 'riskyPseudonyms': riskyPseudonymSet}
        socketToMobileDevice.sendto(bytes(str(ACKMessage),encoding = "utf-8"), (remoteHost, remotePort))

    socketToMobileDevice.close()



thread_maintain = threading.Thread(target=blockchainMaintain_thread, args=(ContactTracingBlockchain,))
thread_maintain.start()
thread_ope = threading.Thread(target=operation_thread)
thread_ope.start()
udpServer = threading.Thread(target=udpServer)
udpServer.start()
server = socketserver.ThreadingTCPServer(listenAddr, Handler)   # 多线程交互
server.serve_forever()
