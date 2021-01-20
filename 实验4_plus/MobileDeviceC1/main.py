from network import LoRa
import socket
import time
import pycom
import json
import _thread
import myrandom


'''
注: lopy4一旦关机时间戳就重置
LoRa的频段都是LoRa.CN470
'''

LoRaBand = LoRa.EU868

pycom.heartbeat(False)# 1
# pseudonym: {'name':'...', 'timestamp': ...}
riskyNames = []
usedNames = []

# 移动设备编号
DEVICE_ID = 'C1'


# 实验3发包计数
packageCount = 0
# 实验3 最大发包数
maxPackageNum = 99999

# 发送一次匿名信息之后的休眠时常 (s)
sleepTimeInterval = 20
# 检查当前匿名已使用时长的间隔时间 (s)
checkTimeInterval = 10
# 更换匿名的周期 (s)
changeNameInterval = 2 * 60
# 匿名长度
nameLength = 16
# 健康状态指示灯闪烁间隔时间 (s)
displayInterval = 2
# 最新的更新密钥的时间 (s)
latestUpdateTime = None
# 匿名信息的存储时长(14天)
outdateTime = 1209600

'''实验记录路径1'''
dataFileFixedDevice = 'dataWithFixedDevice.txt'


H = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
# 当前使用的假名
presentPseudonym = None
# 风险等级, 0:无风险(绿); 1:有风险(黄); 2:确诊(红);
riskyLevel = 0
# 风险等级和指示灯颜色对照
LEVELCOLOR = {0: 0x000f00, 1: 0x0f0f00, 2: 0x0f0000}


# LED灯闪烁
def blink(num = 3, period = .5, color = 0):
    """ LED blink """
    for i in range(0, num):
        pycom.rgbled(color)
        time.sleep(period)
        pycom.rgbled(0)


'''
record和deleteFile用于做实验记录
'''

def record(strList, filePath):
    global timeDifference

    try:
        f = open(filePath, 'a')
        f.write(str(time.time())+"   ")
        for string in strList:
            f.write(string+"  ")
        f.write("\n")
        f.close()
        return True
    except BaseException as be:
        print(be, 'in record()')
        return False


def deleteFile(fileName):
    try:
        os.remove(fileName)
        return True
    except BaseException:
        return False


# 根据风险等级展现指示灯颜色
def displayriskyLevel():
    global levelColor
    global displayInterval

    while True:
        blink(color = LEVELCOLOR[riskyLevel])
        time.sleep(displayInterval)


# 删除过期(outdateTime,默认14天)的假名
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



# 产生num位的随机字符串
def ranstr(num):
    salt = ''
    for i in range(num):
        salt += H[myrandom.RandomInt(62)]
    return salt


# 产生假名(随机字符串)
def generatePseudonym():
    global nameLength

    return ranstr(nameLength)


lora = LoRa(mode=LoRa.LORA, region=LoRaBand, bandwidth=LoRa.BW_500KHZ, coding_rate=LoRa.CODING_4_5, sf=7, tx_power=8)


# 数据包发送套接字
socketToFixedDevice = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
socketToFixedDevice.setblocking(False)
# 数据包接收套接字, 阻塞
socketFromFixedDevice = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
socketFromFixedDevice.setblocking(True)



# 定期更新假名线程
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


# 匹配自己的假名使用记录和风险匿名名单, 线程
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


# 信息接收线程
def receiver():
    global socketFromFixedDevice
    global riskyNames
    global sleepTimeInterval
    global presentPseudonym
    global dataFileFixedDevice
    global packageCount
    global maxPackageNum

    while True:
        try:
            receivedJson = socketFromFixedDevice.recv(256)
            receivedMessage = json.loads(receivedJson)
            # 收到唤醒信息
            if receivedMessage['sendDevice'] == 'fixedDevice' and ('wake' in receivedMessage.keys()):
                if receivedMessage['wake'] == 'C':

                    # 已发送最大数量的包
                    if packageCount == maxPackageNum:
                        blink(num=1, period=.5, color=0x1F1F1F)
                        time.sleep(1)
                        continue

                    '''记录被唤醒'''
                    record(['recv_wake', ''], dataFileFixedDevice)

                    # 风险匿名名单, [str, str, str, ...]
                    riskyNames = receivedMessage['riskyNames']
                    print(riskyNames, time.time())
                    # 被唤醒后发送自己的信息
                    messageToSend = {'name': DEVICE_ID + ('%03d'%packageCount) + presentPseudonym, 'sendDevice': 'mobileDevice'}
                    messageToSendJson = json.dumps(messageToSend)
                    socketToFixedDevice.send(messageToSendJson)

                    # 发包计数+1
                    packageCount += 1

                    '''记录发出匿名信息'''
                    record(['send_pseudonym', ''], dataFileFixedDevice)

                    print("sent peudonym:", presentPseudonym)
                    matchRiskyNames()

                    # 每发送一次匿名信息后就休眠一段时间
                    time.sleep(sleepTimeInterval)

        except Exception as e:
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

# 清空存储
def cleanFlash():
    deleteFile(dataFileFixedDevice)


if __name__ == '__main__':
    cleanFlash()
    # 测试, 真正情况下不 启动就清理Pseudonyms
    cleanPseudonyms()
    pseudonymThread = _thread.start_new_thread(updatePseudonym, ())
    receiverThread = _thread.start_new_thread(receiver, ())
    displayColorThread = _thread.start_new_thread(displayriskyLevel, ())
