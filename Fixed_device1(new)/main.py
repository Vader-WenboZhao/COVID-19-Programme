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
import os
import struct

pycom.heartbeat(False)

LoRaBand = LoRa.EU868

# A basic package header, B: 1 byte for the deviceId, B: 1 byte for the pkg size
_LORA_PKG_FORMAT = "BB%ds"
_LORA_PKG_ACK_FORMAT = "BBB"
_LORA_PKG_TIME_ACK_FORMAT = "!BBL"

# 自己的编号大小为 1 byte
DEVICE_ID = 0x01

'''
fixed device 从 mobile device 接收到只包含假名的记录, 向 region server 发出只包含假名、地点的记录
模式切换后第一件事就是时间校对, 其他什么都不做
'''

riskyPseudonymSet = set({'8iw3bNKJj0eu6dxc', 't5ctaNlWPq4BEGDF', 'jwYQInToUKFCFGmy'})
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
# 是否收需要等待ACK
waiting_ack = True

# Fixed_device产生的Trace不带有time
def createTrace(pseudonym):
    global timeDifference
    newTrace = Trace(pseudonym, LOCATION, time.time()+timeDifference)
    '''签名就会超出lora可传送的包大小'''
    # newTrace.sign(PRI_KEY_PATH)
    localTraces.append(newTrace.dictForm())
    return newTrace.dictForm()


# use tx_iq to avoid listening to our own messages
# lora = LoRa(mode=LoRa.LORA, tx_iq=True, region=LoRaBand, sf=7)
lora = LoRa(mode=LoRa.LORA, region=LoRaBand, sf=7)


socketToMobileDevice = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
socketToMobileDevice.setblocking(False)
socketToRegionServer = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
socketToRegionServer.setblocking(False)
socketReceive = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
socketReceive.setblocking(True)



''' # 旧版
def sendToRegionServer():
    global localTraces
    global riskyPseudonymSet
    global socketToRegionServer
    global socketReceive
    global WaitingNum
    global HasReceived
    global timeHasReceived
    global case

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
'''


def sendToRegionServer():
    global waiting_ack
    global localTraces
    global riskyPseudonymSet
    global socketToRegionServer
    global socketReceive
    global WaitingNum
    global HasReceived
    global timeHasReceived
    global case
    global timeDifference

    # 时间校对, 误差为秒级
    # timeMessage = {'sendDevice': 'fixedDevice', 'aim': regionServerNum, 'timeAsk': True}
    timeMessage = {'sendDevice': 'fixedDevice', 'timeAsk': True}
    timeMessageJson = json.dumps(timeMessage)
    pkgTime = struct.pack(_LORA_PKG_FORMAT % len(timeMessageJson), DEVICE_ID, len(timeMessageJson), timeMessageJson)
    socketToRegionServer.send(pkgTime)

    waiting_ack = True
    while True:
        time.sleep(1)
        if timeHasReceived == True:
            break
        socketToRegionServer.send(pkgTime)
        continue

        '''
        if (len(recv_ack) > 0):
            device_id, pkg_len, timeGet = struct.unpack(_LORA_PKG_TIME_ACK_FORMAT, recv_ack)
            if (device_id == DEVICE_ID):
                timeDifference = timeGet
                print("Time difference is", timeDifference)
                break
        '''


    while True:
        if len(localTraces)>=1:
            case = 1
            sendMessage = {'traces': localTraces[0], 'sendDevice': 'fixedDevice', 'aim': regionServerNum}
        else:
            continue

        sendJson = json.dumps(sendMessage)
        pkgTrace = struct.pack(_LORA_PKG_FORMAT % len(sendJson), DEVICE_ID, len(sendJson), sendJson)
        socketToRegionServer.send(pkgTrace)
        # print(pkgTrace)

        waiting_ack = True
        while True:
            time.sleep(1)
            if waiting_ack == False:
                localTraces.remove(localTraces[0])
                break
            socketToRegionServer.send(pkgTrace)
            continue
        continue


def receive():
    global waiting_ack
    global socketReceive
    global timeHasReceived


    while True:
        recvMessage = socketReceive.recv(256)

        while not timeHasReceived:
            if (len(recvMessage) > 0):
                device_id, pkg_len, timeGet = struct.unpack(_LORA_PKG_TIME_ACK_FORMAT, recvMessage)
                if type(timeGet) != type(1605003234):
                    recvMessage = socketReceive.recv(256)
                    continue
                if (device_id == DEVICE_ID):
                    timeDifference = timeGet
                    print("Time difference is", timeDifference)
                    timeHasReceived = True
                continue

        if (len(recvMessage) > 0):
            try:
                message = json.loads(recvMessage)
                if message['sendDevice'] == "mobileDevice":
                    newTrace = createTrace(message['name'])
                    continue
            except BaseException:
                device_id, pkg_len, ack = struct.unpack(_LORA_PKG_ACK_FORMAT, recvMessage)
            if (device_id == DEVICE_ID):
                if (ack == 200):
                    waiting_ack = False
                    print("ACK")
                else:
                    waiting_ack = False
                    print("Message Failed")


''' # 旧代码
def receive():
    global HasReceived
    global case
    global riskyPseudonymSet
    global timeHasReceived
    global timeDifference

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
        except Exception as e:
            print("Error in receive thread!")
            print(e)
            continue
'''





def wakeup():
    while True:
        # 集合类型放进JSON报错, riskyPseudonymSet转化为list类型
        wakeMessage = {'wake': True, 'riskyNames': list(riskyPseudonymSet), 'sendDevice': 'fixedDevice'}
        wakeMessageJson = json.dumps(wakeMessage)
        socketToMobileDevice.send(wakeMessageJson)
        '''# 正确代码, 每5分钟广播一次唤醒信息
        time.sleep(300)'''
        # 测试代码
        time.sleep(10)


# 调试用函数
def printLocalTraces():
    print(localTraces)

sendToRegionServer = _thread.start_new_thread(sendToRegionServer,())
thread_receive = _thread.start_new_thread(receive,())
wakeupThread = _thread.start_new_thread(wakeup,())
