#coding:utf-8

from numpy import *
import operator

SF_TXP_LIST = [[7,2],[7,14],[12,2],[12,14]]

ROOTPATH = '/Users/zhaowenbo/wilna305/Fang2/实验1/records_A/'
TESTROOTPATH = '/Users/zhaowenbo/wilna305/Fang2/实验1/records_A/test/'
K = 5

def readFile(path):
    data = []
    f = open(path)             # 返回一个文件对象
    line = f.readline()             # 调用文件的 readline()方法
    while line:
        data.append(list(eval(line)))
        line = f.readline()
    f.close()
    return data, len(data)

##给出训练数据以及对应的类别
def createDataSet(data, labels):
    group = array(data)
    labels = labels
    return group,labels

###通过KNN进行分类
def classify(input,dataSet,label,k):
    dataSize = dataSet.shape[0]
    ####计算欧式距离
    diff = tile(input,(dataSize,1)) - dataSet
    sqdiff = diff ** 2
    squareDist = sum(sqdiff,axis = 1) # 行向量分别相加，从而得到新的一个行向量
    dist = squareDist ** 0.5

    ##对距离进行排序
    sortedDistIndex = argsort(dist) # argsort()根据元素的值从大到小对元素进行排序，返回下标

    classCount={}
    for i in range(k):
        voteLabel = label[sortedDistIndex[i]]
        ###对选取的K个样本所属的类别个数进行统计
        classCount[voteLabel] = classCount.get(voteLabel,0) + 1
    ###选取出现的类别次数最多的类别
    maxCount = 0
    for key,value in classCount.items():
        if value > maxCount:
            maxCount = value
            classes = key

    return classes

def main():
    for sftxp in SF_TXP_LIST:
        indoorDataPath = ROOTPATH + 'indoor_sf'+str(sftxp[0])+'_txpower'+str(sftxp[1])+'_tcenter.txt'
        outdoorDataPath = ROOTPATH + 'outdoor_sf'+str(sftxp[0])+'_txpower'+str(sftxp[1])+'_tcenter.txt'
        data = []
        labels = []
        data += readFile(indoorDataPath)[0]
        labels1 = readFile(indoorDataPath)[1] * [True]
        data += readFile(outdoorDataPath)[0]
        labels2 = readFile(outdoorDataPath)[1] * [False]
        labels = labels1 + labels2
        dataSet, labelsSet = createDataSet(data, labels)

        indoorTestDataPath = TESTROOTPATH + 'Indoor_sf'+str(sftxp[0])+'_txp'+str(sftxp[1])+'_test.txt'
        outdoorTestDataPath = TESTROOTPATH + 'Outdoor_sf'+str(sftxp[0])+'_txp'+str(sftxp[1])+'_test.txt'
        inputIndoorData = readFile(indoorTestDataPath)[0]
        inputOutdoorData = readFile(outdoorTestDataPath)[0]
        denominator = readFile(indoorTestDataPath)[1] + readFile(outdoorTestDataPath)[1]

        count = 0
        accuracy = 0

        for data in inputIndoorData:
            if classify(data, dataSet, labels, K) == True:
                count += 1

        for data in inputOutdoorData:
            if classify(data, dataSet, labels, K) == False:
                count += 1

        accuracy = count/denominator

        print('sf=' + str(sftxp[0]) + ', tx_power=' + str(sftxp[1]) + ': ' + '%.2f' % (100 *accuracy))

main()
