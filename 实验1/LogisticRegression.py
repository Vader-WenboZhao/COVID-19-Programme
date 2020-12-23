'''
logistic regression
'''

#导入需要的包
import pandas as pd
#建立数据集
from collections import OrderedDict


def readFile(path):
    data = []
    f = open(path)             # 返回一个文件对象
    line = f.readline()             # 调用文件的 readline()方法
    while line:
        data.append(eval(line)[0])
        line = f.readline()
    f.close()
    return data, len(data)

outdoorData = readFile('/Users/zhaowenbo/wilna305/Fang2/项目/实验1/KNN/data/outdoor_sf12_txpower2_tcenter.txt')
indoorData = readFile('/Users/zhaowenbo/wilna305/Fang2/项目/实验1/KNN/data/indoor_sf12_txpower2_tcenter.txt')
RSSIdata = outdoorData[0] + indoorData[0]
labels = ([0]*outdoorData[1]) + ([1]*indoorData[1])

#是否InOut用0和1表示，0表示未通过，1表示通过。
examDict={'RSSI':RSSIdata, 'InOut':labels}



# 使用OrderedDict会根据放入元素的先后顺序进行排序。所以输出的值是排好序的
examOrderDict=OrderedDict(examDict)
examDf=pd.DataFrame(examOrderDict)
# examDf.head()
#在机器学习编码中变量命名在变量后面加一个大写的X表示特征，y表示标签，通过后缀就可以看出哪些是特征和标签。
#获取特征
'''
loc——通过行标签索引行数据
iloc——通过行号索引行数据
ix——通过行标签或者行号索引行数据（基于loc和iloc 的混合）
'''
exam_X=examDf.loc[:,'RSSI']
#获取标签
exam_y=examDf.loc[:,'InOut']
#建立训练数据和测试数据
from sklearn.model_selection import train_test_split
X_train,X_test,y_train,y_test=train_test_split(exam_X,exam_y,test_size=.2)
#导入sklearn包逻辑回归函数
from sklearn.linear_model import LogisticRegression
#创建逻辑回归模型
model=LogisticRegression(solver='liblinear')
#训练模型
'''
机器学习包sklearn要求输入的特征必须是一个二维数组的类型，这里只有一个特征，
需要进行重塑，否则会报错，因此对训练数据和测试数据的特征进行重塑。
'''
X_train=X_train.values.reshape(-1,1)
X_test=X_test.values.reshape(-1,1)
model.fit(X_train,y_train)

#可以用model的predict_proba方法预测给定RSSI是否InOut的概率
# model.predict_proba(3)

leastDifference = 100
result = None

for x in range(-150,0,1):
    temp = model.predict_proba([[x]])[0]
    if abs(temp[0]-temp[1]) < leastDifference:
        leastDifference = abs(temp[0]-temp[1])
        result = x

print(result)
print(model.predict_proba([[result]])[0])
