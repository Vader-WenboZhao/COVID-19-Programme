from network import WLAN
from network import LoRa
import time
from machine import RTC
import pycom
import socket
import json
import os
import struct
import _thread




# PC部分的IP地址和端口号
PCAddr = ('172.19.157.52', 3000)
# Wi-Fi ssid
wifissid = 'wenbo_TP-LINK'
# Wi-Fi Passcode
wifiPasscode = "13860666"
# NTP 服务器地址, 连接校园网的情况下只能访问 time.dlut.edu.cn, 其他情况可以 ntp.aliyun.com
NTPServer = "time.dlut.edu.cn"
# 发送trace信息给PC端的时间间隔
sendTraceInterval = 1


'''
LoRa part
'''
LoRaBand = LoRa.EU868

# lora = LoRa(mode=LoRa.LORA, tx_iq=True, region=LoRaBand)
lora = LoRa(mode=LoRa.LORA, region=LoRaBand, bandwidth=LoRa.BW_125KHZ, coding_rate=LoRa.CODING_4_8, sf=9, tx_power=14)
# 接收LoRa信号的套接字
lora_sock = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
lora_sock.setblocking(False)

localTraces = []
riskyNames = set()

print('\nConnecting to WiFi...',  end='')
# Connect to a Wifi Network
wlan = WLAN(mode=WLAN.STA)

# 连接 Wi-Fi
wlan.connect(ssid = wifissid, auth=(WLAN.WPA2, wifiPasscode))
while not wlan.isconnected():
    print('.', end='')
    time.sleep(1)
print(" OK")


'''
Sync time
'''
# Sync time via NTP server for GW timestamps on Events
print('Syncing RTC via ntp...', end='')
rtc = RTC()


# 连接NTP server
rtc.ntp_sync(server= NTPServer)
while not rtc.synced():
    print('.', end='')
    time.sleep(.5)
print(" OK\n")


# 和 PC 端通信的socket
socketToPC = socket.socket(socket.AF_INET,socket.SOCK_STREAM)

# TCP连接PC端
while True:
    try:
        time.sleep(3)
        socketToPC.connect(PCAddr)
        print("Connect PC successfully")
        break
    except BaseException as be:
        print(be)
        time.sleep(3)
        continue


# LED灯闪烁
def blink(num = 3, period = .5, color = 0):
    """ LED blink """
    for i in range(0, num):
        pycom.rgbled(color)
        time.sleep(period)
        pycom.rgbled(0)


# 和PC端通信的线程: 发送数据(trace数据)
def sendToPCPart():
    global localTraces
    global sendTraceInterval

    while True:
        # 内存中没有暂存的trace数据
        if len(localTraces) == 0:
            time.sleep(1)
            continue
        try:
            # 把本地暂存的trace数据发送给PC端
            messageToSend = bytes(str(localTraces[0]), 'utf-8')
            socketToPC.send(messageToSend)
            localTraces.remove(localTraces[0])
            time.sleep(sendTraceInterval)
        except BaseException as be:
            print(be, "at sendToPCPart")
            time.sleep(5)
            continue


# 和PC端通信的线程: 接收数据(风险名单)
def recvFromPCPart():
    global riskyNames

    while True:
        recvTCPData = socketToPC.recv(512)

        blink(num=1, period=.5, color=0x1F1F1F)

        # 风险名单为空
        if recvTCPData == b'[]' or b'':
            continue
        # bytes数据转str
        msg = recvTCPData.decode('utf-8')
        print("recv from PC part:", msg)
        # str数据转list
        msg = eval(msg)
        if isinstance(msg, list):
            # list数据转set, 因为set不能用于网络传输
            msg = set(msg)
            riskyNames = msg


# 接收来自场所设备的信息, 使用struct库
def recvFromFixedDevice():
    global localTraces
    global riskyNames

    while True:
        try:
            recv_pkg = lora_sock.recv(512)

            if (len(recv_pkg) > 2):
                # recv_pkg的第2个字节记录的是数据长度,即"BB%ds"里第二个B
                recv_pkg_len = recv_pkg[1]
                # 按B、B、%ds读取数据分别赋值给device_id、pkg_len、msgJson
                # unpack内的语句是, recv_pkg_len格式化赋值%d, 按"BB%d"解析recv_pkg
                device_id, pkg_len, msgJson = struct.unpack("BB%ds" % recv_pkg_len, recv_pkg)
                msgStr = msgJson.decode()
                try:
                    msg = eval(msgStr)
                except BaseException:
                    continue

                blink(num=1, period=.5, color=0x00003F)

                # 是否是时间校对请求, 是的话就回复当前时间戳, 根据NTP服务器的信息回复
                if 'timeAsk' in msg.keys() and msg['timeAsk']==True:
                    # BBL: 第一个字节存device_id, 第二个字节存1, 最后的长整数存时间戳
                    ack_pkg = struct.pack("!BBL", device_id, 1, time.mktime(rtc.now()))
                    lora_sock.send(ack_pkg)
                    print(msg, "Time ACK sent")
                    continue
                # 接收到trace数据
                else:
                    if msg['sendDevice'] == 'fixedDevice':
                        localTraces.append(msg['traces'])
                    # 将风险匿名名单发送给场所设备
                    riskNamesStr = str(riskyNames)
                    # !!! 在串的前面写入串的长度然后写入串本身, 便于接收端解析
                    # 格式相当于"iBB%ds", i保存riskNamesStr的长度, B保存device_id, B保存200, %ds保存riskNamesStr
                    ack_pkg = struct.pack("iBB" + str(len(riskNamesStr)) + "s", len(riskNamesStr), device_id, 200, riskNamesStr)
                    lora_sock.send(ack_pkg)
                    print(msg, "ACK sent")

        except BaseException as be:
            continue



if __name__ == '__main__':

    threadRecvFromFixedDevice = _thread.start_new_thread(recvFromFixedDevice,())
    threadSendToPC = _thread.start_new_thread(sendToPCPart,())
    threadRecvFromPC = _thread.start_new_thread(recvFromPCPart,())
