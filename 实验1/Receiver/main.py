from network import LoRa
import socket
import time
import pycom
import _thread
import os

LoRaBand = LoRa.EU868

pycom.heartbeat(False)

savePath = input("Input file name: ")
savePath += ".txt"

# LED灯闪烁
def blink(num = 3, period = .5, color = 0):
    """ LED blink """
    for i in range(0, num):
        pycom.rgbled(color)
        time.sleep(period)
        pycom.rgbled(0)


lora = LoRa(mode=LoRa.LORA, region=LoRaBand, bandwidth=LoRa.BW_500KHZ, coding_rate=LoRa.CODING_4_5, sf=7, tx_power=8)

mySocket = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
mySocket.setblocking(True)

def printRecords():
    f = open(savePath, 'r')
    print(f.read())
    f.close()

def clean():
    f = open(savePath, 'w')
    f.write("")
    f.close()

def mainThread():
    while True:
        recvMessage = mySocket.recv(64)
        blink(num=1, period=0.5, color=0x0F0F00)
        tupleRecord = lora.stats()
        # rssi, snr, sfrx, tx_power,
        record = (tupleRecord[1],tupleRecord[2],tupleRecord[3],tupleRecord[6])
        print(record, recvMessage)
        f = open(savePath, 'a')
        f.write(str(record) + "\n")
        f.close()

def deleteFile(fileName):
    try:
        os.remove(fileName)
    except BaseException:
        pass

threadMain = _thread.start_new_thread(mainThread, ())
