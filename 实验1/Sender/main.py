from network import LoRa
import socket
import time
import pycom
import myrandom

LoRaBand = LoRa.EU868

pycom.heartbeat(False)



# LED灯闪烁
def blink(num = 3, period = .5, color = 0):
    """ LED blink """
    for i in range(0, num):
        pycom.rgbled(color)
        time.sleep(period)
        pycom.rgbled(0)


# 似乎tx_power越低RSSI降得越明显
# lora = LoRa(mode=LoRa.LORA, region=LoRaBand, tx_power=2, sf=7)
lora = LoRa(mode=LoRa.LORA, region=LoRaBand, bandwidth=LoRa.BW_500KHZ, coding_rate=LoRa.CODING_4_5, sf=7, tx_power=8)

mySocket = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
mySocket.setblocking(False)

while True:
    message = str(myrandom.RandomInt(999))
    mySocket.send(message)
    blink(num=1, period=0.5, color = 0x0F000F)
    time.sleep(1)
