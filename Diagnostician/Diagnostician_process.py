import socketserver
import threading
from BasicBlockchainProcess import *
from Blockchain import *
from parameters import *
import time

# 实例化Blockchain类
ContactTracingBlockchain = Blockchain()
NotificationBlockchain = Blockchain()

connectedAddrList = []


def findPatientTimeLocation(blockchain, patientPseudonymList):
    result = []
    print("patientPseudonymList:", patientPseudonymList)
    for block in blockchain.chain:
        for trace in block['traces']:
            trace = eval(trace)
            # print("trace's pseudonym is:", trace['pseudonym'])
            if trace['pseudonym'] in patientPseudonymList:
                # 元组形式
                result.append((trace['timestamp'], trace['location']))
    return result

def notifyGeoSolver(blockchain, patientPseudonymList):
    global connectedAddrList
    # 结果形式: [(t,l),(t,l),(t,l)...]
    patientTimeLocation = findPatientTimeLocation(blockchain, patientPseudonymList)
    # 添加操作符, 3为查询风险时间地址
    messageToSend = {'ope':3, 'timeLocationList':patientTimeLocation}
    # connectedAddrList[0]是Geo Solver的元组
    connectedAddrList[0][0].sendall(bytes(str(messageToSend), encoding = "utf-8"))


def deleteRiskyPseudonym(riskyPseudonymList):
    global connectedAddrList
    # 添加操作符, 4为删除风险假名
    messageToSend = {'ope':4, 'riskyPseudonymList':riskyPseudonymList}
    # connectedAddrList[0]是Geo Solver的元组
    connectedAddrList[0][0].sendall(bytes(str(messageToSend), encoding = "utf-8"))


def operation_thread():
    global connectedAddrList
    while True:
        try:
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
            elif order == "upload patient":
                patientPseudonymList = input("patient's pseudonym list: ")
                # 传list
                patientPseudonymList = eval(patientPseudonymList)
                notifyGeoSolver(ContactTracingBlockchain, patientPseudonymList)
            elif order == "delete risk":
                riskyPseudonymListToDelete = input("risky pseudonyms to delete: ")
                # 传list
                riskyPseudonymListToDelete = eval(riskyPseudonymListToDelete)
                deleteRiskyPseudonym(riskyPseudonymListToDelete)
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
                    pass
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


thread_maintain = threading.Thread(target=blockchainMaintain_thread, args=(ContactTracingBlockchain,))
thread_maintain.start()
thread_ope = threading.Thread(target=operation_thread)
thread_ope.start()
server = socketserver.ThreadingTCPServer(listenAddr, Handler)   # 多线程交互
server.serve_forever()
