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

# 自己的编号大小为 1 byte
DEVICE_ID = 0x01


riskyPseudonymSet = set()
localTraces = []

# 未收到ACK重复发送trace时间间隔
resendTraceInterval = 1
# 发送唤醒信息的时间间隔, 应小于移动设备的休眠时长
wakeUpTimeInterval = 4
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


def sendToRegionServer():
    global waiting_ack
    global localTraces
    global riskyPseudonymSet
    global socketToRegionServer
    global socketReceive
    global HasReceived
    global timeHasReceived
    global case
    global timeDifference
    global resendTraceInterval

    # 时间校对, 误差为秒级
    # timeMessage = {'sendDevice': 'fixedDevice', 'aim': regionServerNum, 'timeAsk': True}
    timeMessage = {'sendDevice': 'fixedDevice', 'timeAsk': True}
    timeMessage = str(timeMessage)
    '''timeMessageJson = json.dumps(timeMessage)
    pkgTime = struct.pack("BB%ds" % len(timeMessageJson), DEVICE_ID, len(timeMessageJson), timeMessageJson)'''
    pkgTime = struct.pack("BB%ds" % len(timeMessage), DEVICE_ID, len(timeMessage), timeMessage)
    socketToRegionServer.send(pkgTime)

    waiting_ack = True

    while not timeHasReceived:
        socketToRegionServer.send(pkgTime)
        time.sleep(1)
        continue

    while True:
        if len(localTraces)>=1:
            case = 1
            sendMessage = {'traces': localTraces[0], 'sendDevice': 'fixedDevice'}
            sendMessage = str(sendMessage)
        else:
            continue

        '''sendJson = json.dumps(sendMessage)
        pkgTrace = struct.pack("BB%ds" % len(sendJson), DEVICE_ID, len(sendJson), sendJson)'''
        pkgTrace = struct.pack("BB%ds" % len(sendMessage), DEVICE_ID, len(sendMessage), sendMessage)
        socketToRegionServer.send(pkgTrace)
        # print(pkgTrace)

        waiting_ack = True
        while True:
            time.sleep(resendTraceInterval)
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
    global timeDifference
    global riskyPseudonymSet


    while True:
        recvMessage = socketReceive.recv(256)

        while not timeHasReceived:
            if (len(recvMessage) > 0):
                device_id, pkg_len, timeGet = struct.unpack("!BBL", recvMessage)
                # if type(timeGet) != type(1605003234):
                if not isinstance(timeGet, int):
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
                print(message, str(time.time()+timeDifference))
                if message['sendDevice'] == "mobileDevice":
                    newTrace = createTrace(message['name'])
                    continue
            except BaseException:
                # 先读出串的长度，然后按这个长度读出串
                strLength, device_id, ack = struct.unpack("iBB", recvMessage[0:6])
                # print(strLength, device_id, ack)
                try:
                    riskyNamesStr = struct.unpack(str(strLength) + "s", recvMessage[6:6+strLength])
                except ValueError:
                    continue
                # 是个元组
                riskyPseudonymSet = eval(riskyNamesStr[0])
                # recv_str_len, device_id, pkg_len, ack, riskyNamesStr = struct.unpack("iBBB" + str(recv_str_len) + "s", recvMessage)
            if (device_id == DEVICE_ID):
                if (ack == 200):
                    waiting_ack = False
                    print("ACK", riskyPseudonymSet, str(time.time()+timeDifference))
                else:
                    waiting_ack = False
                    print("Message Failed")



def wakeup():
    global wakeUpTimeInterval

    while True:
        # 集合类型放进JSON报错, riskyPseudonymSet转化为list类型
        wakeMessage = {'wake': True, 'riskyNames': list(riskyPseudonymSet), 'sendDevice': 'fixedDevice'}
        wakeMessageJson = json.dumps(wakeMessage)
        socketToMobileDevice.send(wakeMessageJson)
        # 测试代码
        time.sleep(wakeUpTimeInterval)


# 调试用函数
def printLocalTraces():
    print(localTraces)

sendToRegionServer = _thread.start_new_thread(sendToRegionServer,())
thread_receive = _thread.start_new_thread(receive,())
wakeupThread = _thread.start_new_thread(wakeup,())
