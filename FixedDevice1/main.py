from network import LoRa
import socket
import _thread
import time
import pycom
import json
from Trace import Trace
import os
import struct


# 该场所设备代表的地点(推荐编号表示)
LOCATION = 'ABC12345'

pycom.heartbeat(False)

LoRaBand = LoRa.EU868

# 自己的编号大小为 1 byte
DEVICE_ID = 0x01


riskyPseudonymSet = set()
localTraces = []

# 未收到ACK重复发送trace时间间隔, 因为硬件限制必须大于 2, 否则接收不到ACK (s)
resendTraceInterval = 3
# 发送唤醒信息的时间间隔, 应小于移动设备的休眠时长 (s)
wakeUpTimeInterval = 4
# 是否收到地区服务器的ACK
HasReceived = False
# 时间校对成功标志
timeHasReceived = False
# 时间差, 用于时间校对, 也是设备工作起始时间 (s)
timeDifference = 0
# 是否收需要等待ACK
waiting_ack = True
# 模式, True代表和网关通信, False代表和移动设备通信
communicateWithGateway = True
# 模式变化标志位, 针对接收线程
modeChange = False
# 和移动设备通信的时长 (s)
TIMELENGTHMOBILE = 4 * 60
# 和网关通信的时长 (s)
TIMELENGTHGATEWAY = 1 * 60
# 模式检查的时间间隔 (s)
modeRenewInterval = 1
# 灯光 pkgGateway:亮紫色, pkgMobile:亮黄色, modeGateway:暗紫色, modeMobile:暗黄色
lightColor = {'pkgGateway':0x00FFFF, 'pkgMobile':0xFFFF00, 'modeGateway':0x001010, 'modeMobile':0x101000}



# Fixed_device产生的Trace不带有time
def createTrace(pseudonym):
    global timeDifference
    global LOCATION

    newTrace = Trace(pseudonym, LOCATION, time.time()+timeDifference)
    '''签名就会超出lora可传送的包大小'''
    # newTrace.sign(PRI_KEY_PATH)
    localTraces.append(newTrace.dictForm())
    return newTrace.dictForm()


# use tx_iq to avoid listening to our own messages
# lora = LoRa(mode=LoRa.LORA, tx_iq=True, region=LoRaBand, sf=7)
lora = LoRa(mode=LoRa.LORA, region=LoRaBand, bandwidth=LoRa.BW_125KHZ, coding_rate=LoRa.CODING_4_8, sf=9, tx_power=14)
# 和移动设备通信的socket
socketToMobileDevice = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
socketToMobileDevice.setblocking(False)
# 和地区服务器通信的socket
socketToRegionServer = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
socketToRegionServer.setblocking(False)
# 接收socket, 阻塞
socketReceive = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
socketReceive.setblocking(True)


# LED灯闪烁
def blink(num = 3, period = .5, color = 0):
    """ LED blink """
    for i in range(0, num):
        pycom.rgbled(color)
        time.sleep(period)
        pycom.rgbled(0)


# 控制通信模式的线程
def modeControl():
    global communicateWithGateway
    global TIMELENGTHGATEWAY
    global TIMELENGTHMOBILE
    global timeDifference
    global modeRenewInterval
    global modeChange
    global lightColor

    # 每 modeRenewInterval 秒检查一次
    while True:
        if (time.time() - timeDifference) % (TIMELENGTHGATEWAY+TIMELENGTHMOBILE) <= TIMELENGTHMOBILE:
            if communicateWithGateway == True:
                modeChange = True
            communicateWithGateway = False
            pycom.rgbled(lightColor['modeMobile'])
            time.sleep(modeRenewInterval)
        else:
            if communicateWithGateway == False:
                modeChange = True
            communicateWithGateway = True
            pycom.rgbled(lightColor['modeGateway'])
            time.sleep(modeRenewInterval)



# 和地区服务器通信的线程
def sendToRegionServer():
    global waiting_ack
    global localTraces
    global riskyPseudonymSet
    global socketToRegionServer
    global socketReceive
    global HasReceived
    global timeHasReceived
    global timeDifference
    global resendTraceInterval
    global communicateWithGateway
    global modeRenewInterval
    global modeChange

    '''
    时间校对, 误差为秒级
    '''
    # 时间校对请求信息
    timeMessage = {'sendDevice': 'fixedDevice', 'timeAsk': True}
    timeMessage = str(timeMessage)
    # 通过struct库发送
    pkgTime = struct.pack("BB%ds" % len(timeMessage), DEVICE_ID, len(timeMessage), timeMessage)
    socketToRegionServer.send(pkgTime)

    # 没有收到时间校对回复则重复请求
    while not timeHasReceived:
        socketToRegionServer.send(pkgTime)
        time.sleep(1)
        continue

    # 时间校对成功, 首先收集traces
    lora = LoRa(mode=LoRa.LORA, region=LoRaBand, bandwidth=LoRa.BW_500KHZ, coding_rate=LoRa.CODING_4_5, sf=7, tx_power=8)

    # waiting_ack标志位设为True,表示未收到ACK,需要等待ACK
    waiting_ack = True

    while True:
        # 检查通信模式
        if communicateWithGateway == False:
            time.sleep(modeRenewInterval)
            continue

        # 换成远程通信的LoRa参数
        if modeChange == True:
            lora = LoRa(mode=LoRa.LORA, region=LoRaBand, bandwidth=LoRa.BW_125KHZ, coding_rate=LoRa.CODING_4_8, sf=9, tx_power=14)
            modeChange = False

        # # 发送trace, 因为LoRa包的大小限制, 一次发送一条trace
        if len(localTraces) > 0:
            sendMessage = {'traces': localTraces[0], 'sendDevice': 'fixedDevice'}
            sendMessage = str(sendMessage)
        # 没有任何新的trace存在本地, 就一直等待到 communicateWithGateway==False
        else:
            while communicateWithGateway == True:
                time.sleep(1)
            continue


        # 第二个B存sendMessage的大小, 和%d是同一个数, 便于接收端解析后面的%ds
        pkgTrace = struct.pack("BB%ds" % len(sendMessage), DEVICE_ID, len(sendMessage), sendMessage)
        socketToRegionServer.send(pkgTrace)

        # 发送之后等待ACK
        waiting_ack = True
        # 等待一段时间, 等待地区服务器的回复
        time.sleep(resendTraceInterval)
        while True:
            # 收到ACK就继续下一次大循环; 未收到ACK就再次发送;
            if waiting_ack == False:
                localTraces.remove(localTraces[0])
                break
            socketToRegionServer.send(pkgTrace)
            # 重复发送后等待一段时间
            time.sleep(resendTraceInterval)
        continue


# 接收线程
def receive():
    global waiting_ack
    global socketReceive
    global timeHasReceived
    global timeDifference
    global riskyPseudonymSet
    global modeChange
    global communicateWithGateway
    global lightColor


    while True:

        recvMessage = socketReceive.recv(256)
        # print("received new message:", recvMessage)

        # 时间还未校对成功,则只处理时间校对回复 (时间未校对,场所设备节点就不正式工作)
        while not timeHasReceived:
            if (len(recvMessage) > 0):
                # 时间校对信息
                # 第一个B保存device_id, 第二个B保存pkg_len, L保存时间戳
                try:
                    device_id, pkg_len, timeGet = struct.unpack("!BBL", recvMessage)
                    # 时间戳类型错误
                    if not isinstance(timeGet, int):
                        recvMessage = socketReceive.recv(256)
                        continue
                    # 设备号是否相同, 是否是自己的请求
                    if (device_id == DEVICE_ID):
                        timeDifference = timeGet
                        print("Time difference is", timeDifference)
                        # 时间校对成功
                        timeHasReceived = True
                        break
                except BaseException as be:
                    continue


        # 接收有关trace的数据
        # 和移动设备通信用json形式,和地区服务器通信用struct库
        if (len(recvMessage) > 0):
            try:
                # json.loads成功则说明是来自移动设备的数据,报错就是来自地区服务器
                message = json.loads(recvMessage)

                blink(num=1, color=lightColor['pkgMobile'])

                print(message, str(time.time()+timeDifference))
                if message['sendDevice'] == "mobileDevice":
                    newTrace = createTrace(message['name'])
                    continue
            # json.loads报错就是来自地区服务器
            except BaseException as be1:
                # 先读出串的长度，然后按这个长度读出串
                # 先读出strLength, device_id, ack, 在recvMessage的前6字节
                strLength, device_id, ack = struct.unpack("iBB", recvMessage[0:6])

                blink(num=1, color=lightColor['pkgGateway'])

                try:
                    # 根据strLength来读取风险匿名名单
                    riskyNamesStr = struct.unpack(str(strLength) + "s", recvMessage[6:6+strLength])
                except ValueError:
                    continue
                # 是个元组
                riskyPseudonymSet = eval(riskyNamesStr[0])
            # # 设备号是否相同, 是否是自己的请求
            if (device_id == DEVICE_ID):
                if (ack == 200):
                    waiting_ack = False
                    print("ACK", riskyPseudonymSet, str(time.time()+timeDifference))
                else:
                    waiting_ack = False
                    print("Message Failed")



# 唤醒移动设备的进程, 和移动设备通信的进程
def wakeup():
    global wakeUpTimeInterval
    global timeHasReceived
    global communicateWithGateway
    global modeRenewInterval
    global modeChange

    while not timeHasReceived:
        time.sleep(2)

    while True:
        # 检查通信模式
        if communicateWithGateway == True:
            time.sleep(modeRenewInterval)
            continue

        # 换成近程通信的LoRa模式
        if modeChange == True:
            lora = LoRa(mode=LoRa.LORA, region=LoRaBand, bandwidth=LoRa.BW_500KHZ, coding_rate=LoRa.CODING_4_5, sf=7, tx_power=8)
            modeChange = False

        # 集合类型放进JSON报错, riskyPseudonymSet转化为list类型
        wakeMessage = {'wake': True, 'riskyNames': list(riskyPseudonymSet), 'sendDevice': 'fixedDevice'}
        wakeMessageJson = json.dumps(wakeMessage)
        socketToMobileDevice.send(wakeMessageJson)
        # 测试代码
        time.sleep(wakeUpTimeInterval)


# 调试用函数, 输出本地traces
def printLocalTraces():
    print(localTraces)

# 调试函数, 输出目前模式
def printMode():
    global communicateWithGateway
    print(communicateWithGateway)


if __name__ == '__main__':

    sendToRegionServer = _thread.start_new_thread(sendToRegionServer,())
    thread_receive = _thread.start_new_thread(receive,())
    wakeupThread = _thread.start_new_thread(wakeup,())
    modeControlThread = _thread.start_new_thread(modeControl,())
