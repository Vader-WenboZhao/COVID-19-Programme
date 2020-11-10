import socket
import struct
from network import LoRa
import json
import time

# A basic package header, B: 1 byte for the deviceId, B: 1 byte for the pkg size, %ds: Formatted string for string
_LORA_PKG_FORMAT = "!BB%ds"
# A basic ack package, B: 1 byte for the deviceId, B: 1 byte for the pkg size, B: 1 byte for the Ok (200) or error messages
_LORA_PKG_ACK_FORMAT = "BBB"
_LORA_PKG_TIME_ACK_FORMAT = "!BBL"

# Open a LoRa Socket, use rx_iq to avoid listening to our own messages
# Please pick the region that matches where you are using the device:
# Asia = LoRa.AS923
# Australia = LoRa.AU915
# Europe = LoRa.EU868
# United States = LoRa.US915

# lora = LoRa(mode=LoRa.LORA, rx_iq=True, region=LoRa.EU868)

LoRaBand = LoRa.CN470

lora = LoRa(mode=LoRa.LORA, region=LoRaBand)
lora_sock = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
lora_sock.setblocking(True)

while (True):
    recv_pkg = lora_sock.recv(512)
    try:
        json.loads(recv_pkg)
        continue
    except BaseException:
        try:
            if (len(recv_pkg) > 2):
                recv_pkg_len = recv_pkg[1]

                device_id, pkg_len, msgJson = struct.unpack(_LORA_PKG_FORMAT % recv_pkg_len, recv_pkg)

                # If the uart = machine.UART(0, 115200) and os.dupterm(uart) are set in the boot.py this print should appear in the serial port
                print('Device: %d - Pkg:  %s' % (device_id, msgJson))
                msgJson = json.loads(msgJson)

                if 'timeAsk' in msgJson.keys() and msgJson['timeAsk']==True:
                    ack_pkg = struct.pack(_LORA_PKG_TIME_ACK_FORMAT, device_id, 1, time.time())
                    lora_sock.send(ack_pkg)
                    continue
                else:
                    ack_pkg = struct.pack(_LORA_PKG_ACK_FORMAT, device_id, 1, 200)
                    lora_sock.send(ack_pkg)
        except BaseException as e:
            print(e)
            pass
        continue
