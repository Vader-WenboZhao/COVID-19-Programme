from network import WLAN
import time
import machine
from machine import RTC
import pycom
import socket

print('\nStarting LoRaWAN concentrator')
# Disable Hearbeat
pycom.heartbeat(False)

# Define callback function for Pygate events
def machine_cb (arg):
    evt = machine.events()
    if (evt & machine.PYGATE_START_EVT):
        # Green
        pycom.rgbled(0x103300)
    elif (evt & machine.PYGATE_ERROR_EVT):
        # Red
        pycom.rgbled(0x331000)
    elif (evt & machine.PYGATE_STOP_EVT):
        # RGB off
        pycom.rgbled(0x000000)

# register callback function
machine.callback(trigger = (machine.PYGATE_START_EVT | machine.PYGATE_STOP_EVT | machine.PYGATE_ERROR_EVT), handler=machine_cb)

print('Connecting to WiFi...',  end='')
# Connect to a Wifi Network
wlan = WLAN(mode=WLAN.STA)
wlan.connect(ssid='zwbHotspot', auth=(WLAN.WPA2, "zhaowenbo"))

while not wlan.isconnected():
    print('.', end='')
    time.sleep(1)
print(" OK")

# Sync time via NTP server for GW timestamps on Events
print('Syncing RTC via ntp...', end='')
rtc = RTC()
rtc.ntp_sync(server="time1.aliyun.com")

while not rtc.synced():
    print('.', end='')
    time.sleep(.5)
print(" OK\n")

# Read the GW config file from Filesystem
fp = open('/flash/config.json','r')
buf = fp.read()

# Start the Pygate
machine.pygate_init(buf)
# disable degub messages
# machine.pygate_debug_level(1)

messageToSend = 'This message is from PyGate'

mySocket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
PCAddr = ('172.20.10.3', 8081)
mySocket.connect(PCAddr)
while True:
    mySocket.send(b'123')
    time.sleep(3)

'''
eth = ETH()

eth.init()
eth.hostname('gate1')

messageToSend = 'This message is from PyGate'

mySocket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
PCAddr = ('127.0.0.1', 8082)
mySocket.connect(PCAddr)
mySocket.sendall(bytes(str(messageToSend), encoding = "utf-8"))

print("connecting...")
while not eth.isconnected():
    time.sleep(1)
    print(".", end='')

print(eth.ifconfig())
print(socket.getaddrinfo("pycom.io", 80))
'''
