"""
负责：股票数据获取、处理
"""
import datetime

from StockConfig import *
from StockLogger import Logger
import re
import tushare as ts
from pytdx.hq import TdxHq_API
import time
import pandas as pd
import numpy as np
import urllib
import json
import requests
import pymysql
import sqlite3
from sqlalchemy import create_engine
import os
import sys
#根据系统运行位置确认basedir路径
if getattr(sys, 'frozen', None):
    basedir = os.path.dirname(sys.executable)
    DEFAULT_DIR_PATH = basedir
else:
    basedir = os.path.dirname(__file__)

logging = Logger(os.path.join(basedir,'all.log'),level='debug').logger

class StockData:
    def __init__(self):
        # 获取stock接口
        self.pro = ts.pro_api(TUSHARE_TOKEN)
        self.dbUtil = DBUtil.getInstance()
    # 更新股票基本信息
    def updateStocks(self):
        data = self.pro.stock_basic(exchange='', list_status='L',
                                    fields='ts_code,symbol,name,area,industry,fullname,enname,market,exchange,curr_type,list_status,list_date,delist_date')
        self.dbUtil.to_sql(data, 'stock_basic', if_exists='replace', index=False,dtype=STOCK_BASIC_DTYPE)
        logging.info('股票基本信息更新成功，共更新了%s条' % len(data))
    # 判断是否交易日
    def isOpen(self, start, end=None):
        df = self.pro.trade_cal(exchange='', start_date=start, end_date=end if end else start)
        return len(df[df['is_open'] == 1])

    @classmethod
    def getInstance(cls):
        if not hasattr(StockData, "_instance"):
            StockData._instance = StockData()
        return StockData._instance


class LocalData:
    def __init__(self):
        self.dbUtil = DBUtil.getInstance()
        self.tdxData = TdxData.getInstance()
        self.stockData = StockData.getInstance()
    # 获取K线数据
    def data(self,code,type):
        base = self.get_base(code, type)
        zs = True if type == 1 else False
        type = base['type']  # 个股：0深市 ，1 沪市，指数 1tushare
        category = config.getByKey('TDX_CATEGORY')
        if category == 9 and self.dbUtil.is_exist('stock_%s_%s_%s'%(category,type,code)):
            # 获取现有数据
            df = self.dbUtil.read_sql('select * from stock_%s_%s_%s'%(category,type,code))
            start_date = int(df['trade_date'].tail(1))
            end_date = int(time.strftime("%Y%m%d", time.localtime()))
            if end_date - start_date > 1:  # 减少调用接口次数
                days = self.stockData.isOpen(str(start_date), str(end_date))  # 只能算交易日
            else:
                days = end_date - start_date
            if days == 0: # 当天盘中跑实时数据
                if len(df) > 0 :
                    if self.is_deal_time(): # 如果当前时间是交易时间
                        data = self.tdxData.days(code, type, bk=zs, all=False, day=1)
                        return df[0:-1].append(data).reset_index()
                    return df
                return self._init_data(code,zs,type)
            data = self.tdxData.days(code, type, bk=zs, all=False, day=days)
            if not data.empty: # df[0:-1] 过滤掉开始时间对应的旧值
                df = df[0:-1].append(data.sort_values(by="trade_date", ascending=True), sort=False, ignore_index=True)
                data['trade_date'] = data['trade_date'].apply(lambda x: int(x))
                data = data[data['trade_date'] > start_date]
                data = data.sort_values(by="trade_date", ascending=True)
                self.dbUtil.to_sql(data, 'stock_%s_%s_%s' % (category,type,code), if_exists='append', index=False,dtype=STOCK_TRADE_DATA)
            return df.reset_index()#data.sort_values(by="trade_date",ascending=True)
        else: # 获取所有数据
            return self._init_data(code,zs,type)
    # 根据代码获取深沪类型、编号、指数信息
    def get_base(self,code,type):
        if not code:
            return {'code':'','type':'','zs':type}

        stock_list = getattr(self, 'stock_list', None)
        if stock_list is None:
            self.codes()
        base = self.stock_list[self.stock_list['code'].eq(code) & self.stock_list['zs'].eq(type)]
        return {'code':code,'zs':type,'type':base['type'].values[0]}
    # 获取股票代码：type=1 只返回关注股东的股票，type=None 返回所有的股票
    def codes(self,type=None):
        if type is None: # 默认展示所有股票
            sql = 'select symbol code,substr(ts_code ,8)  type, 0 zs from stock_basic sb  union all SELECT code,1 type,1 zs from stock_bk b where b.type=1 '
        elif type == 1: # 展示关注股东为激活的股票（type=1）
            date = self.dbUtil.read_sql('select max(rq) rq from  (select rq,COUNT(1) num from stock_sdgd  group by rq) t where num>3000')
            rq = date['rq'].values[0]
            warns = self.dbUtil.read_sql('select name from stock_gdwarn where type=1')
            if not warns.empty:
                tbsql = ''
                andsql = ''
                orsql = ''
                for index, item in warns.iterrows():
                    name = item['name']
                    tname = 't%s'%index
                    tbsql += " (select code,zj from stock_sdgd  where gdmc  ='%s'  and rq>='%s' ) %s,\n"%(name,rq,tname)
                    andsql+= " and %s.code = c.symbol  \n"%tname
                    orsql += " or %s.zj='新进'   or (%s.zj>0 and %s.zj!='不变')"%(tname,tname,tname)
                sql = "select c.symbol code,substr(c.ts_code ,8)  type, 0 zs from %s stock_basic c ,stock_bk_gn sbg  where  sbg.code  = c.symbol %s and (1=2 %s) " \
                      "GROUP  by c.symbol ORDER by c.symbol"%(tbsql,andsql,orsql)
            else:
                raise Exception('请先配置您关注的股东名称')
        # 将股票代码和类型放入缓存
        data = self.dbUtil.read_sql(sql)
        data['type'] = data['type'].apply(lambda x: 0 if x == 'SZ' else 1)
        if type is None:
            self.stock_list = data
        return data
    # 获取自选股股票池{'code':'000001','state':'1(持仓)/0(空仓)','num':0,'seq':0}
    # return 可买入的股票数量，开买入的股票池，每只股票买入的金额，持有的可操作股票
    def get_buy_stocks(self,money):
        if money<=STOCK_SPLIT and money>5000:
            nums = 1
        else:
            nums = int(money/STOCK_SPLIT) if int(money)%STOCK_SPLIT==0 else int(money/STOCK_SPLIT)+1
            nums = nums-1 if (money-(nums-1)*STOCK_SPLIT)<5000 else nums # 小于5000时不算一个有效操作
        if self.dbUtil.is_exist('stock_buy_pools'):
            data = self.dbUtil.read_sql('select * from stock_buy_pools order by seq desc')
            buy_data = data[data['state']=='0']['code'].values
            seal_data = data[data['state'] == '1']['code'].values
            buy_data = np.append(buy_data , self.codes(type=1)['code'].values)
            if nums>len(data): # 资金过多产生报警发送邮件
                nums = len(buy_data)
                level_money = {buy_data[i]:STOCK_SPLIT for i in range(nums)}
                logging.error('资金分配出现溢出问题请开辟新账号')
                self.mailUtil.sendEmail([MAIL_USER], '资金分配异常', '资金分配出现溢出问题请开辟新账号，现有资金:%s,可买入股票数量:%s'%(money,nums))
            else:
                if nums==1:
                    level_money = {buy_data[0]:money}
                else:
                    level_money = {buy_data[i]:money-(nums-1)*STOCK_SPLIT if (nums-1)==i else STOCK_SPLIT for i in range(nums)}
            return nums,buy_data,level_money,seal_data
        return nums,[],{},[]
    # 回测结果
    def test_result(self,key,*args,**kwargs):
        category = config.getByKey('TDX_CATEGORY')
        if self.dbUtil.is_exist('stock_%s_result'%category):
            if DB_TYPE == 'mysql':
                bkstr = " CONCAT(c.industry ,c.area ,GROUP_CONCAT(sbg.blockname)) "
            else:
                bkstr = " c.industry ||','|| c.area ||'板块,'||GROUP_CONCAT(sbg.blockname)"
            sql = "select * from (select c.name 名称,sr.code 代码,sr.bj 本金,sr.ztsy 总体收益,sr.jycs 交易次数,sr.jf 缴费,sr.cgl 成功率 ,%s 板块 " \
                  "from stock_%s_result sr,stock_basic c ,stock_bk_gn sbg where c.symbol=sr.code and  sbg.code  = c.symbol  and sr.key='%s' " \
                  "group by c.symbol ) t " \
                  "WHERE 代码 like '%%%s%%' and 名称 like '%%%s%%' and 板块 like '%%%s%%'" \
                  "order by 成功率 desc,总体收益 desc"%(bkstr,category,key,kwargs['code'],kwargs['name'],kwargs['bk'])
            return self.dbUtil.read_sql(sql)
        return None
    # 订单信息
    def test_order(self,key,code):
        category = config.getByKey('TDX_CATEGORY')
        if self.dbUtil.is_exist('stock_%s_order'%category):
            return self.dbUtil.read_sql("select trade_date 日期,type 类型, close 价格,ss 手数,cje 成交额,kc 扣除费 from stock_%s_order t where code='%s' and t.key='%s'" %(category,code,key))
        return None
    # 获取当前交易回测结果
    def result_report(self,*args,**kwargs):
        category = config.getByKey('TDX_CATEGORY')
        if self.dbUtil.is_exist('stock_%s_order'%category):
            code = '' if kwargs.get('code') is None else kwargs.get('code')
            name = '' if kwargs.get('name') is None else kwargs.get('name')
            bk = '' if kwargs.get('bk') is None else kwargs.get('bk')
            date = time.strftime("%Y%m", time.localtime())
            if DB_TYPE == 'mysql':
                bkstr = " CONCAT(sb.industry ,sb.area ,GROUP_CONCAT(sbg.blockname)) "
            else:
                bkstr = " sb.industry ||','|| sb.area ||'板块,'||GROUP_CONCAT(sbg.blockname)"
            # 查询出当月处于可操作的个股
            sql = "select * from (SELECT sb.name 名称,so.code 代码,so.close 收盘价,so.type 类型,so.trade_date 日期,%s 板块  from stock_%s_order so,stock_basic sb ,stock_bk_gn sbg " \
                " where so.code =sb.symbol  and so.trade_date  like '%s%%' AND  so.cje>0 and sb.name  not like '%%ST%%'" \
                " and sbg.code  = so.code GROUP  by 代码,日期) t " \
                " WHERE 代码 like '%%%s%%' and 名称 like '%%%s%%' and 板块 like '%%%s%%'" \
                " ORDER by 代码"%(bkstr,category,date,code,name,bk)
            return self.dbUtil.read_sql(sql)
        return None
    # 自选股:国家队参与的新参与的股票即新进或增持的股票
    def self_stock(self,*args,**kwargs):
        if self.dbUtil.is_exist('stock_sdgd'):
            # sql = "select c.name 名称,a.code 代码,a.rq 日期,a.gdmc 股东名称,a.zj 资金,a.bdbl 变动比例,b.gdmc 股东名称,b.zj 资金, b.bdbl 变动比例,GROUP_CONCAT(sbg.blockname) 板块" \
            #     " from " \
            #     " (select code,rq,zj,bdbl from stock_sdgd  where gdmc  ='香港中央结算有限公司'  and rq>='%s' ) a," \
            #     " (select code,rq,zj,bdbl from stock_sdgd where gdmc  ='中央汇金资产管理有限责任公司' and rq>='%s') b," \
            #     " stock_basic c,stock_bk_gn sbg " \
            #     " where a.code = b.code and a.code = c.symbol and sbg.code  = a.code and (a.zj='新进' or b.zj = '新进' or (a.zj>0 and a.zj!='不变') or (b.zj>0 and b.zj!='不变')) " \
            #     " GROUP  by a.code,c.name,a.zj,a.bdbl ORDER by a.code"%(date,date)
            date = self.dbUtil.read_sql('select max(t.rq) rq from  (select rq,COUNT(1) num from stock_sdgd  group by rq)  t where t.num>3000')
            rq = date['rq'].values[0]
            warns = self.dbUtil.read_sql('select name from stock_gdwarn where type=1')
            if not warns.empty:
                columsql = ''
                tbsql = ''
                andsql = ''
                orsql = ''
                if DB_TYPE == 'mysql':
                    bkstr = " CONCAT(c.industry ,c.area ,GROUP_CONCAT(sbg.blockname)) "
                else:
                    bkstr = " c.industry ||','|| c.area ||'板块,'||GROUP_CONCAT(sbg.blockname)"
                for index, item in warns.iterrows():
                    name = item['name']
                    tname = 't%s' % index
                    columsql += ",%s.rq 日期%s,%s.gdmc 股东名称%s,%s.zj 资金%s,%s.bdbl 变动比例%s"%(tname,index,tname,index,tname,index,tname,index)
                    tbsql += " (select code,rq,zj,bdbl,gdmc from stock_sdgd  where gdmc  ='%s'  and rq>='%s' ) %s,\n" % (name, rq, tname)
                    andsql += " and %s.code = c.symbol  \n" % tname
                    orsql += " or %s.zj='新进'   or (%s.zj>0 and %s.zj!='不变')" % (tname, tname, tname)
                sql = "select * from (select c.name 名称,c.symbol 代码 %s ,%s 板块  from %s stock_basic c,stock_bk_gn sbg where sbg.code=c.symbol %s and (1=2 %s) " \
                      "GROUP  by c.symbol,c.name,%s.zj,%s.bdbl,%s.gdmc ) t " \
                      "WHERE 代码 like '%%%s%%' and 名称 like '%%%s%%' and 板块 like '%%%s%%'" \
                      "ORDER by 板块,代码" % (columsql,bkstr,tbsql, andsql, orsql,tname,tname,tname,kwargs['code'],kwargs['name'],kwargs['bk'])
                return self.dbUtil.read_sql(sql)
        return None
    # 保存回测信息
    def saveOrder(self,order,result):
        category = config.getByKey('TDX_CATEGORY')
        code = order[0]['code']
        df = pd.DataFrame(order)
        # df['shift_type'] = df['type'].shift(1).fillna(0).astype('int') #上一个状态
        results = []
        results.append(result)
        dfr = pd.DataFrame(results)
        if self.dbUtil.is_exist('stock_%s_order'%category):
            self.dbUtil.execute_sql('delete from stock_%s_order where code=?'%category,(code))
        if self.dbUtil.is_exist('stock_%s_result'%category):
            self.dbUtil.execute_sql('delete from stock_%s_result where code=?'%category, (code))
        self.dbUtil.to_sql(df,'stock_%s_order'%category,if_exists='append',index=False,dtype=STOCK_ORDER_DTYPE)
        self.dbUtil.to_sql(dfr,'stock_%s_result'%category,if_exists='append',index=False,dtype=STOCK_RESULT_DTYPE)
    # 初始化数据
    def _init_data(self,code,zs,type):
        data = self.tdxData.days(code, type, bk=zs, all=True)
        if not data.empty:
            tmp = data.sort_values(by="trade_date", ascending=True)
            self.dbUtil.to_sql(tmp, 'stock_%s_%s_%s' % (config.getByKey('TDX_CATEGORY'),type,code), if_exists='replace', index=False,dtype=STOCK_TRADE_DATA)
            logging.info('股票%s历史数据更新成功,共%s条' % (code, len(tmp)))
            return tmp
        else:
            logging.info('股票历史数据更新失败,代码%s' % code)
            raise Exception('股票历史数据更新失败,代码%s' % code)
    # 当前时间是否是交易时间，调用前最好调用是否日历isOpen
    def is_deal_time(self):
        time_now = datetime.datetime.now()
        # 范围时间
        start1 = datetime.datetime.strptime(str(datetime.datetime.now().date()) + '9:30', '%Y-%m-%d%H:%M')
        end1 = datetime.datetime.strptime(str(datetime.datetime.now().date()) + '11:30', '%Y-%m-%d%H:%M')
        start2 = datetime.datetime.strptime(str(datetime.datetime.now().date()) + '13:00', '%Y-%m-%d%H:%M')
        end2 = datetime.datetime.strptime(str(datetime.datetime.now().date()) + '15:00', '%Y-%m-%d%H:%M')
        if (time_now > start1 and time_now < end1) or (time_now > start2 and time_now < end2):
            return True
        return False
    # 初始化股东预警表
    def init_gdwarn(self, data=None):
        if data is None:
            gds = []
            gds.append({'name': '中国对外经济贸易信托有限公司 - 淡水泉精选1期', 'type': 0})
            gds.append({'name': '香港中央结算有限公司', 'type': 1})
            gds.append({'name': '中央汇金资产管理有限责任公司', 'type': 1})
            data = pd.DataFrame(gds)
        self.dbUtil.to_sql(data, 'stock_gdwarn', if_exists='replace', index=False,dtype=STOCK_GDWARN_DTYPE)
    # 更新股票池表股票池表:handle=1 添加；handle=-1 删除；
    # param :data:[{code:'',num:'','state':'0/1'}]
    def update_stock_pool(self, datas=None,handle=0):
        if self.dbUtil.is_exist('stock_buy_pools') and datas :
            if datas is None:
                return
            df = self.dbUtil.read_sql('select * from stock_buy_pools')
            temps = []
            if handle==1:# 当日成交时触发
                try:
                    for order in datas:
                        if len(order) == 0:
                            continue
                        if datas[6] not in ('内部撤单', '废单'):
                            temps.append({'code': order[0], 'state': order[2], 'num': order[3], 'seq': '0'})
                except Exception as e:
                    pass
                if len(temps)>0:
                    df = df.append(pd.DataFrame(temps))
            elif handle==-1: # 月线卖出时触发
                for data in datas:
                    code = data['code']
                    df = df[df['code']!=code]
        else:  # 初始化股票池表
            pools = []
            stock = {'code': '002279', 'state': '0', 'num': '0', 'seq': '0'}
            pools.append(stock)
            df = pd.DataFrame(pools)
        self.dbUtil.to_sql(df, 'stock_buy_pools', if_exists='replace', index=False,dtype=STOCK_BUY_POOLS_DTYPE)
    def get_order_msg(self,dayorders):
        orders = [['代码', '名称', '买卖标志', '成交数量', '成交金额', '摘要', '成交时间']]
        try:
            for order in dayorders:
                if len(order) == 0:
                    continue
                if orders[6] not in ('内部撤单', '废单'):
                    orders.append([order[0], order[1], order[2], order[3], order[4], order[5], order[8]])
        except Exception as e:
            pass
        return "\n".join('%s' % id for id in orders)
    @classmethod
    def getInstance(cls):
        if not hasattr(LocalData, "_instance"):
            LocalData._instance = LocalData()
        return LocalData._instance

class TdxData:
    def __init__(self):
        self.api = TdxHq_API(heartbeat=True)
        self.dbUtil = DBUtil.getInstance()
    def get_security_quotes(self,code,type):
        return self.api.get_security_quotes([(type, code)])
    # 支持板块及个股
    def days(self,code,type,bk=False,all=False,day=5):
        category = int(config.getByKey('TDX_CATEGORY'))
        try:
            with self.api.connect(TDX_IP,TDX_PORT):
                data = []
                if all:
                    if bk:
                        for i in range(10):
                            data += self.api.get_index_bars(category, type, code, (9 - i) * 800, 800)
                    else:
                        for i in range(10):
                            data += self.api.get_security_bars(category, type, code, (9 - i) * 800, 800)
                    if len(data)>0:
                        df = self.api.to_df(data).drop(['amount','year','month','day','hour','minute'],axis=1)
                        df['trade_date'] = df['datetime'].apply(lambda x:x[0:10].replace('-',''))
                        df = df.drop(['datetime'], axis=1)
                        df = df.sort_values(by=['trade_date'],axis=0,ascending=False)
                        return df
                    else:
                        return self.api.to_df(data)
                else:
                    if bk:
                        data = self.api.get_index_bars(category,type, code, 0, day)  # 返回DataFrame
                    else:
                        data = self.api.get_security_bars(category, type, code, 0, day)
                    if len(data)>0:
                        df = self.api.to_df(data).drop(['amount','year','month','day','hour','minute'],axis=1)
                        df['trade_date'] = df['datetime'].apply(lambda x:x[0:10].replace('-',''))
                        df = df.drop(['datetime'], axis=1)
                        df = df.sort_values(by=['trade_date'],axis=0,ascending=False)
                        return df
                    else:
                        return self.api.to_df(data)
        except Exception as e:
            logging.info("暂不支持类型,代码：%s:%s"%(code,e))
            return self.api.to_df([])
    # F10 查询公司信息目录
    def get_company_info_category(self,code,type):
        with self.api.connect(TDX_IP, TDX_PORT):
            df = pd.DataFrame(self.api.get_company_info_category(type, code))
            df['txt'] = None
            return df
        return []
    def get_company_info_content(self,code,type,df):
        with self.api.connect(TDX_IP, TDX_PORT):
            return self.api.get_company_info_content(type, code, df['filename'].values[0], df['start'].values[0], df['length'].values[0])
        return ""
    # 查询财务数据
    def get_finance_info(self,code,type):
        with self.api.connect(TDX_IP, TDX_PORT):
            return self.api.get_finance_info(type, code)
        return ''
    # 每年更新一次，板块个股关系
    def updateBk(self):
        with self.api.connect(TDX_IP,TDX_PORT):
            """
            # 获取股票所属板块信息
            # 板块相关参数
            BLOCK_SZ = "block_zs.dat"
            BLOCK_FG = "block_fg.dat"
            BLOCK_GN = "block_gn.dat"
            BLOCK_DEFAULT = "block.dat"
            """
            bk_zs = self.api.to_df(self.api.get_and_parse_block_info("block_zs.dat"))#指数板块
            bk_fg = self.api.to_df(self.api.get_and_parse_block_info("block_fg.dat"))#风格板块
            bk_gn = self.api.to_df(self.api.get_and_parse_block_info("block_gn.dat"))#概念板块
            bk_default = self.api.to_df(self.api.get_and_parse_block_info("block.dat"))  # 默认
            self.dbUtil.to_sql(bk_gn, 'stock_bk_gn', if_exists='replace', index=False,dtype=STOCK_BK_DTYPE)
            self.dbUtil.to_sql(bk_fg, 'stock_bk_fg', if_exists='replace', index=False,dtype=STOCK_BK_DTYPE)
            self.dbUtil.to_sql(bk_zs, 'stock_bk_zs', if_exists='replace', index=False,dtype=STOCK_BK_DTYPE)
            self.dbUtil.to_sql(bk_default, 'stock_bk_default', if_exists='replace', index=False,dtype=STOCK_BK_DTYPE)

            # 获取股票列表
            tmp1 = self.api.to_df(self.api.get_security_list(0, 0))  # 深圳
            tmp1['type'] = 0
            tmp2 = self.api.to_df(self.api.get_security_list(1, 0))  # 上海
            tmp2['type'] = 1
            tmp = tmp1.append(tmp2)
            self.dbUtil.to_sql(tmp, 'stock_bk', if_exists='replace', index=False,dtype=STOCK_BK)
    def updateGD(self,code,type):
        url = 'http://emweb.securities.eastmoney.com/PC_HSF10/ShareholderResearch/ShareholderResearchAjax?code=%s%s'%(type.lower(),code)
        html = urllib.request.urlopen(url).read()
        # 将字符串转换成字典
        data = json.loads(html.decode('utf-8'))
        # gdrs 股东人数,sdgd 十大股东 ，sdltgd 十大流通股东
        df_gdrs = pd.DataFrame(data['gdrs'])
        df_gdrs['code'] = code
        try:
            db_df_gdrs = self.dbUtil.read_sql("select * from stock_gdrs where code ='%s'"%code)
            # 数据合并
            df_gdrs = df_gdrs.append(db_df_gdrs).drop_duplicates(subset=['code','rq','gdmc'],keep='last')
        except Exception as e:
            pass
        self.dbUtil.to_sql(df_gdrs, 'stock_gdrs', if_exists='append', index=False,dtype=STOCK_GDRS_DTYPE)
        sdgd = []
        for i in range(len(data['sdgd'])):
            sdgd += data['sdgd'][i]['sdgd']
        df_sdgd = pd.DataFrame(sdgd)
        df_sdgd['code']= code
        try:
            db_df_sdgd = self.dbUtil.read_sql("select * from stock_sdgd where code ='%s'"%code)
            df_sdgd = df_sdgd.append(db_df_sdgd).drop_duplicates(subset=['code','rq','gdmc'],keep='last')
        except Exception as e:
            pass
        self.dbUtil.to_sql(df_sdgd, 'stock_sdgd', if_exists='append', index=False,dtype=STOCK_SDGD_DTYPE)
        sdltgd = []
        for i in range(len(data['sdltgd'])):
            sdltgd += data['sdltgd'][i]['sdltgd']
        df_sdltgd = pd.DataFrame(sdltgd)
        df_sdltgd['code'] = code

        # 获取后与数据库中的数据进行merge,首次表不存在，会抛异常
        try:
            db_df_sdltgd = self.dbUtil.read_sql("select * from stock_sdltgd where code ='%s'"%code)
            df_sdltgd = df_sdltgd.append(db_df_sdltgd).drop_duplicates(subset=['code','rq','gdmc'],keep='last')
        except Exception as e:
            pass
        self.dbUtil.to_sql(df_sdltgd, 'stock_sdltgd', if_exists='append', index=False,dtype=STOCK_SDGD_DTYPE)
    # 没季度更新一次
    def updateGDs(self):
        codes = self.dbUtil.read_sql("select ts_code from stock_basic")
        tmp = codes['ts_code'].str.split('.', expand=True)
        for index,row in tmp.iterrows():
            try:
                self.updateGD(row[0],row[1])
                logging.info('%s更新结束,当前索引%s'%(row[0],index))
            except Exception as e:
                logging.info('%s更新失败,当前索引%s'%(row[0],index))
    # 分红
    # 分红地址http://data.eastmoney.com/yjfp/201812.html
    def updateFh(self,rq):
        url = 'http://data.eastmoney.com/DataCenter_V3/yjfp/getlist.ashx?filter=(ReportingPeriod=^%s^)'%rq
        html = requests.get(url)
        # 将字符串转换成字典
        data = json.loads(html.text)['data']
        if len(data)==0:
            return 0
        df = pd.DataFrame(data)
        df['ReportingPeriod'] = df['ReportingPeriod'].apply(lambda x:x[0:10])
        # 首次需要将df_fh制空，因为表还不存在
        if self.dbUtil.is_exist("stock_fh"):
            db_fh = self.dbUtil.read_sql("select * from stock_fh where ReportingPeriod = '%s'"%df['ReportingPeriod'][0])
            if db_fh.empty:# 不存在当前日期的分红信息，进行拼接
                self.dbUtil.to_sql(df,'stock_fh',if_exists='append',index=False)
                return 1
            else:
                pass
        else:
            self.dbUtil.to_sql(df, 'stock_fh', if_exists='append', index=False)
            return 1
    # 更新历年分红
    def updateFhYears(self):
        now = int(time.strftime("%Y", time.localtime()))+1
        lastYear = int(self._getFhMaxYear())
        for i in range(lastYear,now):#初始化时开启
            type = self.updateFh('%s-06-30'%i)
            logging.info('%s-06-30%s'%(i,'成功' if type ==1 else '失败'))
            self.updateFh('%s-12-31' % i)
            logging.info('%s-12-31%s'%(i,'成功' if type ==1 else '失败'))
    def _getFhMaxYear(self):
        if self.dbUtil.is_exist('stock_fh'):
            try:
                df = self.dbUtil.read_sql('select substr(max(t.ReportingPeriod ),0,5) year from stock_fh t')
                return df['year'][0].values
            except Exception as e:
                pass
        return 1991
    @classmethod
    def getInstance(cls):
        if not hasattr(TdxData, "_instance"):
            TdxData._instance = TdxData()
        return TdxData._instance
# 回测时查询回测文件目录
class FoldData:
    def __init__(self):
        pass
    @classmethod
    def test_files(cls):
        tests = []
        files = os.listdir(DEFAULT_DIR_PATH)
        for f in files:
            if re.search(r'^Test(.*)\.py$',f):
                tests.append(f)
        return pd.DataFrame(tests,columns=['name'])
"""
数据库工具类
"""
class DBUtil:
    def __init__(self,type):
        super(DBUtil, self).__init__()
        if type =='mysql':
            self.instance = DBUtil_Mysql.getInstance()
        else:
            self.instance = DBUtil_Sqlite.getInstance()
    def read_sql(self,sql):
        return self.instance.read_sql(sql)
    def to_sql(self,df,tablename,if_exists='fail',index=True,dtype=None):
        self.instance.to_sql(df,tablename,if_exists=if_exists,index=index,dtype=dtype)
        return 1
    def execute_sql(self,sql,*args):
        self.instance.execute_sql(sql,args)
        return 1
    def is_exist(self,table_name):
        return self.instance.is_exist(table_name)
    @classmethod
    def getInstance(cls):
        if not hasattr(DBUtil, "_instance"):
            DBUtil._instance = DBUtil(DB_TYPE)
        return DBUtil._instance
class DBUtil_Mysql:
    def __init__(self,url):
        super(DBUtil_Mysql, self).__init__()
        b = url.split(':')
        c = b[2].split('@')
        self.connection = pymysql.connect(c[1], b[1].split('//')[1] , c[0], b[3].split('/')[1])
        self.engine = create_engine(url)
    def read_sql(self,sql):
        return pd.read_sql(sql,self.connection)
    def to_sql(self,df,tablename,if_exists='fail',index=True,dtype=None):
        pd.io.sql.to_sql(df,tablename,self.engine,if_exists=if_exists,index=index,dtype=dtype)
        return 1
    def execute_sql(self,sql,*args):
        cursor = self.connection.cursor()
        sql = sql.replace('?','%s')  # 兼容sqlite
        cursor.execute(sql,*args)
        cursor.execute('SET AUTOCOMMIT=1;')
    def is_exist(self,table_name):
        exist =table_name in self.engine.table_names()
        return exist
    @classmethod
    def getInstance(cls,url=DB_URL):
        if not hasattr(DBUtil_Mysql, "_instance"):
            DBUtil_Mysql._instance = DBUtil_Mysql(url)
        return DBUtil_Mysql._instance
class DBUtil_Sqlite:
    def __init__(self,url):
        super(DBUtil_Sqlite, self).__init__()
        self.connection = sqlite3.connect(url,check_same_thread=False)
    def read_sql(self,sql):
        return pd.read_sql(sql,self.connection)
    def to_sql(self,df,tablename,if_exists='fail',index=True,dtype=None):
        pd.io.sql.to_sql(df,tablename,self.connection,if_exists=if_exists,index=index,dtype=dtype)
        return 1
    def execute_sql(self,sql,*args):
        cursor = self.connection.cursor()
        cursor.execute(sql, *args)
        return 1
    def is_exist(self, table_name):
        num = self.read_sql("SELECT count(1) from sqlite_master where type = 'table' and tbl_name='%s'"%table_name)
        return num.values[0][0]>0
    @classmethod
    def getInstance(cls,url='db.sqlite3'):
        if not hasattr(DBUtil_Sqlite, "_instance"):
            DBUtil_Sqlite._instance = DBUtil_Sqlite(os.path.join(basedir,url))
        return DBUtil_Sqlite._instance