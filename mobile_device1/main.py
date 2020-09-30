from network import LoRa
import socket
import time
import utime
import pycom
import json
import _thread
import crypto
import myrandom


'''注: lopy4一旦关机时间戳就重置'''


pycom.heartbeat(False)
# pseudonym: {'name':'...', 'timestamp': ...}
riskyNames = set()
# 最新的更新密钥的时间
latestUpdateTime = None
PUBLICKEY = None
H = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
# 现在的假名
presentPseudonym = None
# 重发信息标记
RESENDSYMBOL = True
# 最近发送的消息编号
LATESTMESSAGENUMBER = 0


with open('lib/public.pem') as f:
    PUBLICKEY = f.read()
    f.close()



# LED灯闪烁
def blink(num = 3, period = .5, color = 0):
    """ LED blink """
    for i in range(0, num):
        pycom.rgbled(color)
        time.sleep(period)
        pycom.rgbled(0)


# 删除过期(14days)的假名
def deleteOldNames(nameList):
    if len(nameList) == 0:
        return
    while True:
        if time.time() - nameList[0]['timestamp'] >= 1209600:
            nameList.remove(nameList[0])
        else:
            break


# 保存新的假名、删除过期的假名
def savePseudonym(newName):
    # newName是字符串
    # 如果文件不存在
    try:
        f = open('usedPseudonyms.txt', 'r')
        strPseudonyms = f.read()
        f.close()
        listPseudonyms = eval(strPseudonyms)
    except BaseException as be:
        listPseudonyms = []
        print(be)
    deleteOldNames(listPseudonyms)
    listPseudonyms.append({'name': newName, 'timestamp': time.time()})
    f = open('usedPseudonyms.txt', 'w')
    f.write(str(listPseudonyms))
    f.close()


'''
# 随机数加密
def generatePseudonym():
    return crypto.rsa_encrypt(str(int(myrandom.RandomRange(100000, 999999))), PUBLICKEY)
'''


def ranstr(num):
    salt = ''
    for i in range(num):
        salt += H[myrandom.RandomInt(62)]
    return salt


# 产生假名
def generatePseudonym():
    return ranstr(16)


lora = LoRa(mode=LoRa.LORA, region=LoRa.CN470, sf=7)


# 数据包发送套接字
socketToFixedDevice = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
socketToFixedDevice.setblocking(False)
socketFromFixedDevice = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
socketFromFixedDevice.setblocking(True)


'''
# 真实代码
def updatePseudonym():
    global presentPseudonym
    global latestUpdateTime
    presentPseudonym = generatePseudonym()
    latestUpdateTime = time.time()
    savePseudonym(presentPseudonym)
    while True:
        # 每个小时检查一次
        time.sleep(3600)
        # 每24h更新一次假名
        if time.time() - latestUpdateTime >= 86400:
            presentPseudonym = generatePseudonym()
            latestUpdateTime = time.time()
            savePseudonym(presentPseudonym)
'''


'''测试代码'''
def updatePseudonym():
    global presentPseudonym
    global latestUpdateTime
    presentPseudonym = generatePseudonym()
    latestUpdateTime = time.time()
    savePseudonym(presentPseudonym)
    while True:
        # 每个小时检查一次
        time.sleep(5)
        # 每24h更新一次假名
        if time.time() - latestUpdateTime >= 30:
            presentPseudonym = generatePseudonym()
            latestUpdateTime = time.time()
            savePseudonym(presentPseudonym)

'''
#真实的代码
def sender():
    while True:
        try:
            LATESTMESSAGENUMBER = int(myrandom.RandomRange(100000, 999999))
            print(LATESTMESSAGENUMBER)
            messageToSend = json.dumps({'name': presentPseudonym, 'deviceType': 'mobile', 'messageNumber': LATESTMESSAGENUMBER})
            socketToFixedDevice.send(messageToSend)
            RESENDSYMBOL = True
            # 未收到ACK则每10s重复发信息, 重复5次无果则放弃
            count = 0
            while RESENDSYMBOL == True and count <= 4:
                time.sleep(10)
                socketToFixedDevice.send(messageToSend)
                count += 1
            # 每10分钟向外发射一次信息
            time.sleep(600)
        except BaseException as be:
            print(be)
            sleep(10)
            continue
'''


'''测试代码'''
def sender():
    while True:
        try:
            LATESTMESSAGENUMBER = int(myrandom.RandomRange(100000, 999999))
            messageToSend = json.dumps({'name': presentPseudonym, 'deviceType': 'mobile', 'messageNumber': LATESTMESSAGENUMBER})
            socketToFixedDevice.send(messageToSend)
            RESENDSYMBOL = True
            # 未收到ACK则每10s重复发信息, 重复5次无果则放弃
            count = 0
            while RESENDSYMBOL == True and count <= 4:
                time.sleep(1)
                socketToFixedDevice.send(messageToSend)
                count += 1
            # 每10分钟向外发射一次信息
            time.sleep(10)
        except BaseException as be:
            print(be)
            sleep(10)
            continue




def receiver():
    while True:
        try:
            receivedJson = socketFromFixedDevice.recv(256)
            receivedMessage = json.loads(receivedJson)
            #  收到ACK则停止重复发送信息
            print(receivedMessage)
            if receivedMessage['deviceType'] == 'fixed' and receivedMessage['ACK'] == True and receivedMessage['messageNumber'] == LATESTMESSAGENUMBER:
                RESENDSYMBOL = False
        except BaseException as be:
            print(be)
            time.sleep(10)
            continue


'''调试用代码'''
def cleanPseudonyms():
    f = open('usedPseudonyms.txt', 'w')
    f.write(str([]))
    f.close()
def printPseudonyms():
    f = open('usedPseudonyms.txt', 'r')
    print(f.read())
    f.close()



pseudonymThread = _thread.start_new_thread(updatePseudonym, ())
senderThread = _thread.start_new_thread(sender, ())
receiverThread = _thread.start_new_thread(receiver, ())
