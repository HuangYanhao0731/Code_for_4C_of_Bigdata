import numpy as np
from sklearn.ensemble import IsolationForest
import matplotlib.pyplot as plt


## 森林算法
def glslsfs(a):
    data = a
    np.random.seed(1)
    print(data)
    test_is = IsolationForest()
    test_is.fit(data)
    return test_is.predict(data)  # 这里添加返回预测结果

def isolation_forest(a):  # 修改函数名称
    data = a
    np.random.seed(1)
    test_is = IsolationForest()
    test_is.fit(data)
    b = test_is.predict(data)
    return b

def data_processing(zd, n):  ##处理数据zd为字典，n为常数
    m = []
    for i in zd:
        m.append([1, tqsz(i[n])])
    return m

def average_value(zd, n):  ##求平均值
    a = 0
    sum1 = 0
    for i in zd:
        sum1 = sum1+tqsz(i[n])
        a = a+1
    m = sum1/a
    return m

def tqsz(m):
    m = list(m)
    sz = []
    p = 0
    k = 1
    p1 = 1
    hh = 1
    for i in m:
        if '0' <= i <= '9':
            p = p * 10 + int(i)
            if p1 == -1:
                hh = hh*10
        elif i == '.':
            p1 = -1
        elif i == '-':
            k = -1
        else:
            p = k * p/hh
            sz.append(p)
            p = 0
            k = 1
            p1 = 1
            hh = 1
    if '0'<=m[-1]<='9':
        p = k * p / hh
        sz.append(p)
        sz = sz[0]
    return sz

