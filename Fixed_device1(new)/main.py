from network import LoRa
import socket
import _thread
import time
import utime
import pycom
import json
from parameters import *
import sys
import myrandom
from Trace import Trace
from machine import Timer

pycom.heartbeat(False)

'''
fixed device 从 mobile device 接收到只包含假名的记录, 向 region server 发出只包含假名、地点的记录
'''

riskyPseudonymSet = set()
localTraces = []
seconds = 0
WAITINGTIME = 5
WaitingNum = 0
HasReceived = False
case = 2

'''
# 等待ACK超时错误
class ACKTimeoutError(Exception):
    pass
'''

'''
# 类的方法
class Clock:
    def __init__(self, time):
        self.seconds = 0
        self.time = time
        self.__alarm = Timer.Alarm(self._seconds_handler, 1, periodic=True)

    def _seconds_handler(self, alarm):
        self.seconds += 1
        print("%02d seconds have passed" % self.seconds)
        if self.seconds == self.time:
            alarm.cancel() # stop counting after 'time' seconds
            raise ACKTimeoutError
'''


# Fixed_device产生的Trace不带有time
def createTrace(pseudonym):
    newTrace = Trace(pseudonym, LOCATION, time.time())
    '''签名就会超出lora可传送的包大小'''
    # newTrace.sign(PRI_KEY_PATH)
    localTraces.append(newTrace.dictForm())
    return newTrace.dictForm()


# lora = LoRa(mode=LoRa.LORA, region=LoRa.EU868)
lora = LoRa(mode=LoRa.LORA, region=LoRa.CN470, sf=7)

socketToMobileDevice = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
socketToMobileDevice.setblocking(False)
socketToRegionServer = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
socketToRegionServer.setblocking(False)
socketReceive = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
socketReceive.setblocking(True)


'''
def clientSend():
    global localTraces
    global riskyPseudonymSet
    global socketToRegionServer
    global socketReceive

    # 等待ACK超时错误
    class ACKTimeoutError(Exception):
        pass

    def clockHandler(alarm):
        global seconds
        seconds += 1
        print("%02d seconds have passed" % seconds)
        if seconds == WAITINGTIME:
            alarm.cancel() # stop counting after 'time' seconds
            seconds = 0
            raise ACKTimeoutError

    def clock():
        alarm = Timer.Alarm(clockHandler, 1, periodic=True)


    # 两种情况
    case = 1
    while True:
        # socketToReigionServer = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 六位随机数作为序列号
        # UDP长度有限, 最多一次传2条trace!
        if len(localTraces)>2:
            case = 1
            sendMessage = {'number': myrandom.RandomRange(100000,999999), 'traces': localTraces[0:2], 'aim': regionServerShenzhen}
        elif 0<len(localTraces)<=2:
            case = 2
            sendMessage = {'number': myrandom.RandomRange(100000,999999), 'traces': localTraces, 'aim': regionServerShenzhen}
        else:
            time.sleep(10)
            continue
        # socketToReigionServer.sendto(bytes(str(sendMessage),encoding = "utf-8"), regionServerShenzhen)
        sendJson = json.dumps(sendMessage)
        socketToRegionServer.send(sendJson)
        print(sendJson)

        while True:
            # 每次等待ACK最长5s
            # signal.alarm(5)
            try:
                clock()
                recvJsonData = socketReceive.recvfrom(1024)
                recvData = json.loads(recvJsonData)
                # recvData = eval(str(recvData[0], encoding='utf-8'))
                if(recvData['ACK'] and recvData['number'] == sendMessage['number']):
                    # signal.alarm(0)
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
                socketToRegionServer.send(sendJson)
                continue

        socketToReigionServer.close()
        # 每30s发送一次traces
        time.sleep(10)
'''


def sendToRegionServer():
    global localTraces
    global riskyPseudonymSet
    global socketToRegionServer
    global socketReceive
    global WaitingNum
    global HasReceived
    global case

    case = 1
    while True:
        # 六位随机数作为序列号
        # UDP长度有限, 最多一次传1条trace!
        if len(localTraces)>1:
            case = 1
            sendMessage = {'number': int(myrandom.RandomRange(100000,999999)), 'traces': localTraces[0], 'sendDevice': 'fixedDevice', 'aim': regionServerShenzhen}
        elif len(localTraces)==1:
            case = 2
            sendMessage = {'number': int(myrandom.RandomRange(100000,999999)), 'traces': localTraces, 'sendDevice': 'fixedDevice', 'aim': regionServerShenzhen}
        else:
            time.sleep(10)
            continue

        sendJson = json.dumps(sendMessage)
        # print(sendJson)
        socketToRegionServer.send(sendJson)
        WaitingNum = sendMessage['number']
        HasReceived = False

        while True:
            time.sleep(WAITINGTIME)
            if HasReceived:
                break
            else:
                # print("Waiting for ACK timeout, resend ...")
                socketToRegionServer.send(sendJson)
                # print(sendJson)
                continue

        continue


def receive():
    global HasReceived
    global case
    global riskyPseudonymSet

    while True:
        try:
            recvJsonData = socketReceive.recv(256)
            recvData = json.loads(recvJsonData)
            # print(recvData)
            # 从 region server 收到 ACK 和风险名单数据
            if recvData['sendDevice'] == "regionServer":
                if(recvData['ACK'] and recvData['number'] == WaitingNum):
                    # signal.alarm(0)
                    HasReceived = True
                    print("Receive ACK")
                    if case == 1:
                        localTraces.remove(localTraces[0])
                    else:
                        localTraces = []
                riskyPseudonymSet = recvData['riskyPseudonyms']
            # 从 mobile device 收到 trace 数据
            elif recvData['sendDevice'] == "mobileDevice":
                newTrace = createTrace(recvData['name'])
                # 集合类型放进JSON报错, riskyPseudonymSet转化为list类型
                ACKToMobile = {'sendDevice': 'fixedDevice', 'ACK': True, 'messageNumber': recvData['messageNumber'], 'riskyNames': list(riskyPseudonymSet)}
                ACKToMobileJson = json.dumps(ACKToMobile)
                socketToMobileDevice.send(ACKToMobileJson)
                print(ACKToMobileJson)
        except Exception as e:
            print("Error in receive thread!")
            print(e)
            continue

# 调试用函数
def printLocalTraces():
    print(localTraces)

sendToRegionServer = _thread.start_new_thread(sendToRegionServer,())
thread_receive = _thread.start_new_thread(receive,())
