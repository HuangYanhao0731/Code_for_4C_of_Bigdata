import codecs
import jieba
import numpy as np
from algorithm import glslsfs
from algorithm  import clsj
from algorithm import pjz
import torch
import time
import pandas as pd


def analyze_abnormal_products(input_file):
    global progress
    PPP = []
    startTime = time.time()
    np.seterr(divide='ignore', invalid='ignore')
    result6 = []
    with codecs.open(input_file, 'rb', 'gb18030', errors='ignore') as csvfile:
        for line in csvfile:
            temp1 = line.split('\t')
            result6.append(temp1)
    jieba.add_word("天猫")
    jieba.add_word("天天特买工厂店")
    jieba.add_word("天猫")
    jieba.add_word("自营店")
    jieba.add_word("奢侈品")
    jieba.add_word("正品代购")

    qwsp = ["旗舰店",  "天天特卖工厂店","天猫","自营店"]
    spmsb = ["正品代购","奢侈品","闲鱼",]
    r = 0
    zspz = {}  ##  储存各个类别的字典
    zspl = []  ##  列表用于存储各个类别商品
    for i in result6:
        r = r + 1
        if r > 1:
            Q = jieba.lcut(i[-1])
            P = jieba.lcut(i[2])
            k = -1
            for j in qwsp:
                if j in Q :
                    k = 1
            for j in spmsb:
                if j in P:
                    k = 1
            if k == -1:

                ## 补充库存缺失
                if i[15] == '':
                    i[15] = i[6]
                ## 商品类别选择最高级，存在多类别取最后一个
                if i[12] != '':
                    lb = 12
                elif i[11] != '':
                    lb = 11
                elif i[10] != '':
                    lb = 10
                elif i[9] != '':
                    lb = 9
                else:
                    lb = 8
                Q = jieba.lcut(i[lb])
                if '/' in Q:
                    i[12] = Q[0]
                else:
                    i[12] = i[lb]
                lb = 12
                if i[lb] not in zspz:  ##判断字典中有无该键，没有就添加
                    zspz[i[lb]] = k  ## K为该类别在zspl列表的第几个元素
                    k = k + 1
                    zspl.append([])  ##  添加一个存储该商品的列表
                zspl[zspz[i[lb]]].append(i)  ##把该商品信息添加入列表
            else:
                continue

    fl = {}
    n = 0
    for i in zspz.keys():
        fl[i] = zspl[n]  ##把zspl列表中信息加到字典fl对应键下
        n = n + 1  ##统计一共有多少个类别
    input_file = 0
    ds = 1
    L = 0
    glpd = []  # 森林算法判断价格结果
    xbk = []  # 销量比库存判断
    glpdxl = []  # 森林算法判断销量
    sj = []  # 按顺序储存各个类别商品信息
    djyc = []  # 统计低价异常数据
    max_lb = []
    for key, value in fl.items():

        c = value
        a = key
        max_lb.append(a)
        sj.append(c)

        if ds >= 1:
            m = clsj(c, 5)
            d1 = glslsfs(m)  ##孤立森林算法判断价格
            glpd.append(d1)

            m = clsj(c, 6)
            d1 = glslsfs(m)  # 孤立森林算法判断销量
            glpdxl.append(d1)

        ## 比较月销量与商品库存, 若销量大于库存为销量异常
        d2 = []  # 库存与销量对比结果
        d3 = []  # 低于平均值检测结果
        for i in c:
            m = pjz(c, 5)
            if m > float(i[5]):
                d3.append(1)
            else:
                d3.append(-1)
            try:
                if float(i[6]) > float(i[15]):
                    d2.append(-1)
                else:
                    d2.append(1)
            except:
                d2.append(-1)
        xbk.append(d2)
        djyc.append(d3)

    yc = 0
    max = []
    A=[]

    for i in range(len(glpd)):
        for j in range(len(glpd[i])):
            if glpd[i][j] == -1 and djyc[i][j] == -1 and xbk[i][j] == -1 or glpdxl[i][j] == -1:
                ycy = sj[i][j]
                A.append(ycy)
                PPP.append(f"{ycy[1]} 价格异常+销量异常")
                yc = yc + 1
            elif xbk[i][j] == -1 or glpdxl[i][j] == -1:
                ycy = sj[i][j]
                A.append(ycy)
                PPP.append(f"{ycy[1]} 价格异常+销量异常")
                yc = yc + 1
            elif glpd[i][j] == -1 and djyc[i][j] == -1:
                ycy = sj[i][j]
                A.append(ycy)
                PPP.append(f"{ycy[1]} 价格异常+销量异常")
                yc = yc + 1
            else:
                pass

    duration = time.time()-startTime
    print(f"运行时间：{duration}")
    torch.save(A, '007jg')
    print("ok")
    print(yc)
    return None


def jc1(o):
    PPP = []
    print(time.ctime())
    np.seterr(divide='ignore', invalid='ignore')
    result6 = torch.load('007jg')
    r = 0
    zspz = {}  ##  储存各个类别的字典
    zspl = []  ##  列表用于存储各个类别商品
    for i in result6:
        r = r + 1
        if r > 1:
            k = -1
            if k == -1:

                ## 补充库存缺失
                if i[15] == '':
                    i[15] = i[6]
                ## 商品类别选择最高级，存在多类别取最后一个
                if i[12] != '':
                    lb = 12
                elif i[11] != '':
                    lb = 11
                elif i[10] != '':
                    lb = 10
                elif i[9] != '':
                    lb = 9
                else:
                    lb = 8
                Q = jieba.lcut(i[lb])
                if '/' in Q:
                    i[12] = Q[0]
                else:
                    i[12] = i[lb]
                lb = 12
                if i[lb] not in zspz:  ##判断字典中有无该键，没有就添加
                    zspz[i[lb]] = k  ## K为该类别在zspl列表的第几个元素
                    k = k + 1
                    zspl.append([])  ##  添加一个存储该商品的列表
                zspl[zspz[i[lb]]].append(i)  ##把该商品信息添加入列表
            else:
                continue

    fl = {}
    n = 0
    for i in zspz.keys():
        fl[i] = zspl[n]  ##把zspl列表中信息加到字典fl对应键下
        n = n + 1  ##统计一共有多少个类别
    o = 0
    ds = 1
    L = 0
    glpd = []  # 森林算法判断价格结果
    xbk = []  # 销量比库存判断
    glpdxl = []  # 森林算法判断销量
    sj = []  # 按顺序储存各个类别商品信息
    djyc = []  # 统计低价异常数据
    max_lb = []
    for key, value in fl.items():

        c = value
        a = key
        max_lb.append(a)
        sj.append(c)

        m = []
        djw = 0
        if ds >= 1:
            m = clsj(c, 5)
            d1 = glslsfs(m)  ##孤立森林算法判断价格
            glpd.append(d1)

            m = clsj(c, 6)
            d1 = glslsfs(m)  # 孤立森林算法判断销量
            glpdxl.append(d1)

        ## 比较月销量与商品库存, 若销量大于库存为销量异常
        d2 = []  # 库存与销量对比结果
        d3 = []  # 低于平均值检测结果
        max = [] #各类商品最大值
        sl = 0  # 统计一个类别的数量
        for i in c:
            m = pjz(c, 5)
            if m > float(i[5]):
                d3.append(1)
            else:
                d3.append(-1)
            try:
                if float(i[6]) > float(i[15]):
                    d2.append(-1)
                else:
                    d2.append(1)
            except:
                d2.append(-1)
        xbk.append(d2)
        djyc.append(d3)

    yc = 0

    for i in range(len(glpd)):
        for j in range(len(glpd[i])):
            if glpd[i][j] == -1 and djyc[i][j] == -1 and xbk[i][j] == -1 or glpdxl[i][j] == -1:
                ycy = sj[i][j]
                PPP.append(f"{str(ycy[1])} 价格异常+销量异常")
                yc = yc + 1
            elif xbk[i][j] == -1 or glpdxl[i][j] == -1:
                ycy = sj[i][j]
                PPP.append(f"{str(ycy[1])} 销量异常")
                yc = yc + 1
            elif glpd[i][j] == -1 and djyc[i][j] == -1:
                ycy = sj[i][j]
                PPP.append(f"{str(ycy[1])} 价格异常")
                yc = yc + 1


    print("ok")
    print(yc)
    with open("test7.txt","r+") as f:
        f.truncate(0)
    with open("test7.txt","w") as f: #-6
        for i in PPP:
            f.write(i+"\n")
        f.write(str(len(PPP)))
    # print(TIME )
    # print(time.ctime())

    return None

t = time.ctime()
o = "D:/asus/十三届大学生服务创新赛/数据/data_202107.tsv"
analyze_abnormal_products(o)
print("OK")
o = '007jg'
jc1(o)
print(t)
print(time.ctime())
