from network import LoRa
import socket
import time
import utime
import pycom
import json
import _thread
import crypto
import myrandom


'''
注: lopy4一旦关机时间戳就重置
LoRa的频段都是LoRa.CN470
'''

LoRaBand = LoRa.EU868

pycom.heartbeat(False)
# pseudonym: {'name':'...', 'timestamp': ...}
riskyNames = []
usedNames = []

# 发送一次匿名信息之后的休眠时常
sleepTimeInterval = 10
# 检查当前匿名已使用时长的间隔时间
checkTimeInterval = 10
# 更换匿名的周期
changeNameInterval = 30
# 匿名长度
nameLength = 16
# 健康状态指示灯闪烁间隔时间
displayInterval = 2
# 最新的更新密钥的时间
latestUpdateTime = None
# 匿名信息的存储时长(14天)
outdateTime = 1209600


H = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
# 现在的假名
presentPseudonym = None
riskyLevel = 0 # 0:无风险(绿); 1:有风险(黄); 2:确诊(红);
LEVELCOLOR = {0: 0x000f00, 1: 0x0f0f00, 2: 0x0f0000}


# LED灯闪烁
def blink(num = 3, period = .5, color = 0):
    """ LED blink """
    for i in range(0, num):
        pycom.rgbled(color)
        time.sleep(period)
        pycom.rgbled(0)


def displayriskyLevel():
    global levelColor
    global displayInterval

    while True:
        blink(color = LEVELCOLOR[riskyLevel])
        time.sleep(displayInterval)


# 删除过期(14days)的假名
def deleteOldNames(nameList):
    global outdateTime

    if len(nameList) == 0:
        return
    while True:
        if time.time() - nameList[0]['timestamp'] >= outdateTime:
            nameList.remove(nameList[0])
        else:
            break


# 保存新的假名、删除过期的假名
def savePseudonym(newName):
    global usedNames
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
    # 更新使用过的假名列表(内存中)
    usedNames = listPseudonyms
    listPseudonyms.append({'name': newName, 'timestamp': time.time()})
    f = open('usedPseudonyms.txt', 'w')
    f.write(str(listPseudonyms))
    f.close()



def ranstr(num):
    salt = ''
    for i in range(num):
        salt += H[myrandom.RandomInt(62)]
    return salt


# 产生假名
def generatePseudonym():
    global nameLength

    return ranstr(nameLength)


lora = LoRa(mode=LoRa.LORA, region=LoRaBand, sf=7)


# 数据包发送套接字
socketToFixedDevice = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
socketToFixedDevice.setblocking(False)
socketFromFixedDevice = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
socketFromFixedDevice.setblocking(True)



'''测试代码'''
def updatePseudonym():
    global presentPseudonym
    global latestUpdateTime
    global checkTimeInterval
    global changeNameInterval

    presentPseudonym = generatePseudonym()
    latestUpdateTime = time.time()
    savePseudonym(presentPseudonym)
    while True:
        # 每个小时检查一次
        time.sleep(checkTimeInterval)
        # 每24h更新一次假名
        if time.time() - latestUpdateTime >= changeNameInterval:
            presentPseudonym = generatePseudonym()
            latestUpdateTime = time.time()
            savePseudonym(presentPseudonym)


def matchRiskyNames():
    global riskyNames
    global usedNames
    global riskyLevel

    if len(riskyNames) == 0:
        return
    for rName in riskyNames:
        for uNameDict in usedNames:
            if rName == uNameDict['name']:
                riskyLevel = 1
            else:
                continue


# mobile device 不接收信息
def receiver():
    global socketFromFixedDevice
    global riskyNames
    global sleepTimeInterval
    global presentPseudonym

    while True:
        try:
            receivedJson = socketFromFixedDevice.recv(256)
            receivedMessage = json.loads(receivedJson)
            if receivedMessage['sendDevice'] == 'fixedDevice' and ('wake' in receivedMessage.keys()):
                if receivedMessage['wake']:
                    # print("Waking up ...")
                    riskyNames = receivedMessage['riskyNames'] # 只包含名字的列表
                    print(riskyNames, time.time())
                    messageToSend = {'name': presentPseudonym, 'sendDevice': 'mobileDevice'}
                    messageToSendJson = json.dumps(messageToSend)
                    socketToFixedDevice.send(messageToSendJson)
                    print("sent peudonym:", presentPseudonym)
                    matchRiskyNames()

                    # 测试代码
                    time.sleep(sleepTimeInterval)

        except Exception as e:
            # print("Error in receive")
            # print(e)
            time.sleep(sleepTimeInterval)
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

# 测试, 真正情况下不 启动就清理Pseudonyms
cleanPseudonyms()
pseudonymThread = _thread.start_new_thread(updatePseudonym, ())
receiverThread = _thread.start_new_thread(receiver, ())
displayColorThread = _thread.start_new_thread(displayriskyLevel, ())
