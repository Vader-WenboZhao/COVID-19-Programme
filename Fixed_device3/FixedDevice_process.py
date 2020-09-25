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
riskyPseudonymList = set()


def operation_thread():
    global connectedAddrList
    while True:
        global ContactTracingBlockchain
        order = input("Input order: ")
        if order == "connect":
            connectedAddrList = connect()
        elif order == "add trace":
            print(new_traces(ContactTracingBlockchain, connectedAddrList))
        elif order == "chain":
            print(full_chain(ContactTracingBlockchain))
        elif order == "register node":
            print(register_nodes(ContactTracingBlockchain))
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


class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        global riskyPseudonymList
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
                    # 风险名单集合求并集
                    riskyPseudonymList = riskyPseudonymList | self.data['riskyPseudonyms']
                    print(riskyPseudonymList)
                print('-'*40)

                # print("%s say:%s"%(addr,data))
                # client.sendall(bytes(word, encoding = "utf-8"))


thread_ope = threading.Thread(target=operation_thread)
thread_ope.start()
server = socketserver.ThreadingTCPServer(listenAddr, Handler)   # 多线程交互
server.serve_forever()
