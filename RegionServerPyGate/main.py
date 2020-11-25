from network import WLAN
from network import LoRa
import time
import machine
from machine import RTC
import pycom
import socket
import json
import os
import struct
import _thread


'''
LoRa part
'''
LoRaBand = LoRa.EU868

# lora = LoRa(mode=LoRa.LORA, tx_iq=True, region=LoRaBand)
lora = LoRa(mode=LoRa.LORA, region=LoRa.EU868)
lora_sock = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
lora_sock.setblocking(False)

localTraces = []

'''
wifi part
'''
# outdoor hotspot
# PCAddr = ('172.20.10.3', 8081)
# indoor Wi-Fi
PCAddr = ('192.168.1.100', 8090)
print('\nConnecting to WiFi...',  end='')
# Connect to a Wifi Network
wlan = WLAN(mode=WLAN.STA)

# 室外用热点
# wlan.connect(ssid='zwbHotspot', auth=(WLAN.WPA2, "zhaowenbo"))
# 室内用Wi-Fi
wlan.connect(ssid='WiLNA305', auth=(WLAN.WPA2, "305netlab"))

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

# 室外
# rtc.ntp_sync(server="ntp.aliyun.com")
# 室内
rtc.ntp_sync(server="time.dlut.edu.cn")

while not rtc.synced():
    print('.', end='')
    time.sleep(.5)
print(" OK\n")

'''
# Read the GW config file from Filesystem
fp = open('/flash/config.json','r')
buf = fp.read()

# Start the Pygate
machine.pygate_init(buf)
# disable degub messages
# machine.pygate_debug_level(1)
'''


socketToPC = socket.socket(socket.AF_INET,socket.SOCK_STREAM)

while True:
    try:
        time.sleep(3)
        socketToPC.connect(PCAddr)
        break
    except BaseException as be:
        print(be)
        continue

def sendToPCPart():
    global localTraces

    while True:
        if len(localTraces) == 0:
            time.sleep(1)
            continue
        try:
            messageToSend = bytes(str(localTraces[0]), 'utf-8')
            socketToPC.send(messageToSend)
            localTraces.remove(localTraces[0])
            time.sleep(1)
        except BaseException as be:
            print("PCPart", be)
            continue


_LORA_PKG_FORMAT = "BB%ds"
_LORA_PKG_ACK_FORMAT = "BBB"
_LORA_PKG_TIME_ACK_FORMAT = "!BBL"

def recvFromFixedDevice():
    global localTraces

    while True:
        recv_pkg = lora_sock.recv(512)
        if (len(recv_pkg) > 2):
            recv_pkg_len = recv_pkg[1]

            device_id, pkg_len, msgJson = struct.unpack(_LORA_PKG_FORMAT % recv_pkg_len, recv_pkg)
            msgStr = msgJson.decode()
            try:
                msg = eval(msgStr)
            except BaseException:
                continue

            if 'timeAsk' in msg.keys() and msg['timeAsk']==True:
                ack_pkg = struct.pack(_LORA_PKG_TIME_ACK_FORMAT, device_id, 1, time.mktime(rtc.now()))
                lora_sock.send(ack_pkg)
                continue
            else:
                # sendMessage = {'traces': localTraces[0], 'sendDevice': 'fixedDevice', 'aim': regionServerNum}
                if msg['sendDevice'] == 'fixedDevice':
                    localTraces.append(msg['traces'])
                ack_pkg = struct.pack(_LORA_PKG_ACK_FORMAT, device_id, 1, 200)
                lora_sock.send(ack_pkg)

            '''
            ack_pkg = struct.pack(_LORA_PKG_ACK_FORMAT, device_id, 1, 200)
            lora_sock.send(ack_pkg)
            '''


threadRecvFromFixedDevice = _thread.start_new_thread(recvFromFixedDevice,())
threadSendToPCPart = _thread.start_new_thread(sendToPCPart,())
