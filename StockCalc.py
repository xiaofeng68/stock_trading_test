from sys import platform

import pandas as pd
import numpy as np
from numpy import NaN

"""基础指标"""
def EMA(Series, N):
    return pd.Series.ewm(Series, span=N, min_periods=N - 1, adjust=True, ignore_na=True).mean()

def MA(Series, N):
    return pd.Series.rolling(Series, N).mean()

def DIFF(Series, N=1):
    return pd.Series(Series).diff(N)

def SUMX(Series, N):
    if N<=0:
        N=len(Series)
    sum=pd.Series.rolling(Series, N).sum()
    return pd.Series(sum,name='sums')

def ABS(Series):
    return abs(Series)

def MAX(A, B):
    var = IF(A > B, A, B)
    return pd.Series( var,name='maxs')

def MIN(A, B):
    var = IF(A < B, A, B)
    return var

def SINGLE_CROSS(A, B):
    if A.iloc[-2] < B.iloc[-2] and A.iloc[-1] > B.iloc[-1]:
        return True
    else:
        return False
# 布林指标中 STD 标准差
def STD(Series, n):
    G_pyver = int(platform.python_version()[0:1])
    G_ma = None
    if G_pyver == 2:
        G_MAstr = 'pd.rolling_std(Series,n)'
        G_ma = eval(G_MAstr)
    else:
        G_MAstr = 'Series.rolling(window=n,center=False).std()'
        G_ma = eval(G_MAstr)
    return G_ma
"""
上穿函数
"""
def CROSS(df, tp1, tp2, index):
    i = 1
    CR_l = [0]
    y = 0
    while i < len(df):
        if ((tp1[i - 1] < tp2[i - 1]) and (tp1[i] >= tp2[i])):
            y = 1
        else:
            y = 0
        CR_l.append(y)
        i = i + 1
    CR_s = pd.Series(CR_l)
    CR = pd.Series(CR_s, name=index)
    df = df.join(CR)
    return df
def IF(COND, V1, V2):
    var = np.where(COND, V1, V2)
    return pd.Series(var, index=V1.index)
"""
取前n周期数值函数
"""
def REF(tp1, n):
    i = 0
    ZB_l = []
    y = 0
    while i < n:
        y = tp1[i]
        ZB_l.append(y)
        i = i + 1
    while i < len(tp1):
        y = tp1[i - n]
        ZB_l.append(y)
        i = i + 1
    ZB_s = pd.Series(ZB_l)
    return ZB_s
"""
TA-Lib的SMA同国内量化交易普遍使用的SMA是不同的，不能照搬使用，不然结果会有误差。
"""
def SMA(tp1, n, m):
    i = 0
    ZB_l = []
    y = 1
    while i < len(tp1):
        y = 1 if str(y) == 'nan' else y
        y = (tp1[i] * m + (n - m) * y) / n
        ZB_l.append(y)
        i = i + 1
    ZB_s = pd.Series(ZB_l)
    return ZB_s

def COUNT(COND, N):
    return pd.Series(np.where(COND, 1, 0), index=COND.index).rolling(N).sum().fillna(0).astype('int')
def HHV(Series, N):
    return pd.Series(Series).rolling(N).max()
def LLV(Series, N):
    return pd.Series(Series).rolling(N).min()
# """
# tablib 安装比较复杂兼容存在问题更换引用
# talib官方默认参数 fastperiod=12, slowperiod=26,signalperiod=9
# 参数:
#     fastperiod:快线【短周期均线】
#     slowperiod:慢线【长周期均线】
#     signalperiod:计算signalperiod天的macd的EMA均线【默认是9,无需更改】
# 返回参数：
#     macd【DIF】 = 12【fastperiod】天EMA - 26【slowperiod】天EMA
#     macdsignal【DEA或DEM】 = 计算macd的signalperiod天的EMA
#     macdhist【MACD柱状线】 = macd - macdsignal
# """
# def MACD(data,fastperiod=12,slowperiod=26,m=9):
#     close = [float(x) for x in data['close']]
#     # 调用talib计算指数移动平均线的值
#     data['EMA12'] = talib.EMA(np.array(close), timeperiod=fastperiod)
#     data['EMA26'] = talib.EMA(np.array(close), timeperiod=slowperiod)
#     # 调用talib计算MACD指标
#     # data['DIF'],data['DEA'],data['MACD'] = talib.MACD(np.array(close),fastperiod=fastperiod, slowperiod=slowperiod, signalperiod=m)
#     # data['DIF'] = round(data['DIF'],2)
#     # data['DEA'] = round(data['DEA'],2)
#     # data['MACD'] = round(data['MACD']*2,2)
#
#     data['DIF'] = round(EMA(data['close'], fastperiod) - EMA(data['close'], slowperiod),2);
#     data['DEA'] = round(EMA(data['DIF'], m),2);
#     data['MACD'] = round((data['DIF'] - data['DEA']) * 2,2)
#     # MA
#     data['MA5'] = talib.MA(np.array(close), timeperiod=5)
#     data['MA10'] = talib.MA(np.array(close), timeperiod=10)
#     data['MA20'] = talib.MA(np.array(close), timeperiod=20)
#     data['MA5'] = round(data['MA5'],2)
#     data['MA10'] = round(data['MA10'],2)
#     data['MA20'] = round(data['MA20'],2)
#     return data

# MACD 指数平滑移动平均线
def MACD(data,SHORT=12, LONG=26, M=9):
    CLOSE = data['close']
    DIFF = EMA(CLOSE, SHORT) - EMA(CLOSE, LONG)
    DEA = EMA(DIFF, M)
    MACD = (DIFF - DEA) * 2
    return DIFF,DEA,MACD

def KDJ(data,N=9,M1=3,M2=3):
    data['RSV'] = (data['close'] - LLV(data['low'], N)) / (HHV(data['high'], N) - LLV(data['low'], N)) * 100
    data['K'] = SMA(data['RSV'], M1, 1)
    data['D'] = SMA(data['K'], M2, 1)
    data['J']= 3 * data['K'] - 2 * data['D']
    return data

