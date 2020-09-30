import socketserver
import socket
import threading
from BasicBlockchainProcess import *
from Blockchain import *
from parameters import *
import time
import sys
import random
import signal
from Trace import Trace


riskyPseudonymSet = set()


'''
测试
'''
localTraces = []


# 等待ACK超时错误
class ACKTimeoutError(Exception):
  pass

def interrupted(signum, frame):
  raise ACKTimeoutError

signal.signal(signal.SIGALRM, interrupted)


def createTrace(pseudonym):
    newTrace = Trace(pseudonym, LOCATION, int(time.time()))
    newTrace.sign(PRI_KEY_PATH)
    localTraces.append(newTrace.dictForm())
    return newTrace.dictForm()


def server():
    global localTraces
    socketToMobileDevice = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    socketToMobileDevice.bind(myAddr)

    while True:
        recvData, (remoteHost, remotePort) = socketToMobileDevice.recvfrom(1024)
        # print("[%s:%s] connect" % (remoteHost, remotePort))     # 接收客户端的ip, port
        recvData = eval(str(recvData, encoding='utf-8'))
        newTrace = recvData['trace']
        localTraces.append(newTrace)
        ACKMessage = {"number":recvData['number'], 'ACK': True}
        socketToMobileDevice.sendto(bytes(str(ACKMessage),encoding = "utf-8"), (remoteHost, remotePort))
        print("recvData: ", recvData)
        print("sendData: ", ACKMessage)

    socketToMobileDevice.close()


def client():
    global localTraces
    global riskyPseudonymSet
    # 两种情况
    case = 1
    while True:
        socketToReigionServer = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 六位随机数作为序列号
        # UDP长度有限, 最多一次传2条trace!
        if len(localTraces)>2:
            case = 1
            sendMessage = {'number': random.randint(100000,999999), 'traces': localTraces[0:2]}
        else:
            case = 2
            sendMessage = {'number': random.randint(100000,999999), 'traces': localTraces}
        socketToReigionServer.sendto(bytes(str(sendMessage),encoding = "utf-8"), regionServerShenzhen)

        while True:
            # 每次等待ACK最长5s
            signal.alarm(5)
            try:
                recvData = socketToReigionServer.recvfrom(1024)
                recvData = eval(str(recvData[0], encoding='utf-8'))
                if(recvData['ACK'] and recvData['number'] == sendMessage['number']):
                    signal.alarm(0)
                    print("Receive ACK")
                    if case == 1:
                        localTraces.remove(localTraces[0])
                        localTraces.remove(localTraces[0])
                    else:
                        localTraces = []
                riskyPseudonymSet = recvData['riskyPseudonyms']
                break
            except ACKTimeoutError:
                print("Waiting ACK timeout! Resend traces...")
                socketToReigionServer.sendto(bytes(str(sendMessage),encoding = "utf-8"), regionServerShenzhen)
                continue

        socketToReigionServer.close()
        # 每30s发送一次traces
        time.sleep(10)


def operation_thread():
    global riskyPseudonymSet
    while True:
        try:
            order = input("Input order: ")
            if order == "add trace":
                pseudonym = input("pseudonym: ")
                print(createTrace(pseudonym))
            elif order == "risky names":
                print(riskyPseudonymSet)
        except BaseException as be:
            print(be)
            continue


thread_ope = threading.Thread(target=operation_thread)
thread_ope.start()
receiveTraceFromMobileDevice = threading.Thread(target=server)
receiveTraceFromMobileDevice.start()
client() # signal只在主线程工作
