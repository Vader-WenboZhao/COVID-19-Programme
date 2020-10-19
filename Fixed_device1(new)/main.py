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
模式切换后第一件事就是时间校对, 其他什么都不做
'''

riskyPseudonymSet = set()
localTraces = []
# alarm计时
seconds = 0
# 等待时间(s)
WAITINGTIME = 5
# 正在等待的来自地区服务器的ACK的号
WaitingNum = 0
# 是否收到地区服务器的ACK
HasReceived = False
# 发送给地区服务器的两种情况
case = 2
# 时间校对成功标志
timeHasReceived = False
# 时间差, 用于时间校对
timeDifference = 0

# Fixed_device产生的Trace不带有time
def createTrace(pseudonym):
    global timeDifference
    newTrace = Trace(pseudonym, LOCATION, time.time()+timeDifference)
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


def sendToRegionServer():
    global localTraces
    global riskyPseudonymSet
    global socketToRegionServer
    global socketReceive
    global WaitingNum
    global HasReceived
    global timeHasReceived
    global case

    '''
    # 时间校对, 误差为秒级
    sendMessage = {'number': int(myrandom.RandomRange(1000000000,9999999999)), 'sendDevice': 'fixedDevice', 'aim': regionServerNum, 'timeAsk': True}
    sendJson = json.dumps(sendMessage)
    socketToRegionServer.send(sendJson)
    WaitingNum = sendMessage['number']
    timeHasReceived = False
    while True:
        time.sleep(2)
        # 校对成功
        if timeHasReceived:
            break
        else:
            socketToRegionServer.send(sendJson)
            continue
    '''

    case = 1
    while True:
        # 六位随机数作为序列号
        # UDP长度有限, 最多一次传1条trace!
        if len(localTraces)>1:
            case = 1
            sendMessage = {'number': int(myrandom.RandomRange(1000000000,9999999999)), 'traces': localTraces[0], 'sendDevice': 'fixedDevice', 'aim': regionServerNum}
        elif len(localTraces)==1:
            case = 2
            sendMessage = {'number': int(myrandom.RandomRange(1000000000,9999999999)), 'traces': localTraces, 'sendDevice': 'fixedDevice', 'aim': regionServerNum}
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
    global timeHasReceived
    global timeDifference

    '''
    # 时间校对
    if timeHasReceived == False:
        while True:
            try:
                recvJsonData = socketReceive.recv(256)
                recvData = json.loads(recvJsonData)
                if recvData['sendDevice'] == "regionServer" and ('timestamp' in recvData.keys()) and recvData['number'] == WaitingNum:
                    timeDifference = int(recvData['timestamp'] - time.time())
                    # 校对成功
                    timeHasReceived = True
            except Exception as e:
                print("Error in receive thread!")
                print(e)
                continue
    '''

    while True:
        try:
            recvJsonData = socketReceive.recv(256)
            recvData = json.loads(recvJsonData)
            # print(recvData)
            # 从 region server 收到 ACK 和风险名单数据
            if recvData['sendDevice'] == "regionServer" and ('ACK' in recvData.keys()):
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
