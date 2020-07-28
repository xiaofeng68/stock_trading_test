"""更新数据，并且进行回测获取对应订单"""
import platform
import time
from apscheduler.schedulers.blocking import BlockingScheduler
from StockConfig import *
from StockData import LocalData, TdxData, StockData,logging
from StockTest import StockTest2, StockTest3
from StockMail import MailUtil

if(platform.system()=='Windows'):
    from StockDeal import Trader_gxzq

"""
scheduler.add_job(job, 'cron', hour=1, minute=5)
hour =19 , minute =23  这里表示每天的19：23 分执行任务
hour ='19', minute ='23'  这里可以填写数字，也可以填写字符串
hour ='19-21', minute= '23'  表示 19:23、 20:23、 21:23 各执行一次任务
#每300秒执行一次
scheduler .add_job(job, 'interval', seconds=300)
#在1月,3月,5月,7-9月，每天的下午2点，每一分钟执行一次任务
scheduler .add_job(func=job, trigger='cron', month='1,3,5,7-9', day='*', hour='14', minute='*')
# 当前任务会在 6、7、8、11、12 月的第三个周五的 0、1、2、3 点执行
scheduler .add_job(job, 'cron', month='6-8,11-12', day='3rd fri', hour='0-3')
#从开始时间到结束时间，每隔俩小时运行一次
scheduler .add_job(job, 'interval', hours=2, start_date='2018-01-10 09:30:00', end_date='2018-06-15 11:00:00')
"""
class StockJob:
    def __init__(self):
        self.scheduler = BlockingScheduler()
        self.pool = None
        if (platform.system() == 'Windows'):
            self.stockDeal = Trader_gxzq(no=TDX_USER,pwd=TDX_PWD,dimpwd=TDX_DIMPWD)
        self.isopen = False
        self.localData = LocalData.getInstance()
        self.stockData = StockData.getInstance()
        self.tdxData = TdxData.getInstance()
        self.mailUtil = MailUtil.getInstance()


    def add_interval_job(self,fun,days=1,start='2020-05-07 20:56:00'):
        # 在 2020-05-07 20:00:00，每隔1天执行一次
        self.scheduler.add_job(fun, 'interval', days=days, start_date=start)
    '''
    cron: 在特定时间周期性地触发：
        year: 4位数字
        month: 月 (1-12)
        day: 天 (1-31)
        week: 标准周 (1-53)
        day_of_week: 周中某天 (0-6 or mon,tue,wed,thu,fri,sat,sun)
        hour: 小时 (0-23)
        minute:分钟 (0-59)
        second: 秒 (0-59)
        start_date: 最早执行时间
        end_date: 最晚执行时间
        timezone: 执行时间区间
    '''
    def add_cron_job(self,fun,month='*',day='*',day_of_week='*',hour='*',minute='*'):
        self.scheduler.add_job(func=fun, trigger='cron', month=month, day=day,day_of_week=day_of_week, hour=hour, minute=minute)
    def add_date_job(self,fun,date):
        self.scheduler.add_job(fun, 'date', run_date=date)
    def start(self):
        self.scheduler.start()
    def stop(self):
        self.scheduler.shutdown()

    # 回测
    def test(self,default=True):
        config.putByKey('TDX_CATEGORY','6')
        if default:# 默认情况只有交易日可回测
            now = time.strftime("%Y%m%d", time.localtime())
            if not DEBUG and self.stockData.isOpen(now) <= 0:
                return
        # 判断是否交易日，才回测否则不做操作
        codes = self.localData.codes(type=1)
        codes = codes[codes['zs'].eq(0)] #只回测个股
        for index, code in codes.iterrows():
            logging.debug('%s开始更新，当前索引%s,剩余%s'%(code['code'],index,len(codes)-index-1))
            try:
                g57 = StockTest2(code['code'], 0, 'Test2')
                g57.run()
            except Exception as e:
                print(e)
        # 回测完成后设置股票池
        self.pool = self.localData.result_report()

    # 下载数据
    def download(self):
        config.putByKey('TDX_CATEGORY', '6')
        codes = self.localData.codes()
        codes = codes[codes['zs'].eq(0)]
        for index,code in codes.iterrows():
            try:
                self.localData.data(code['code'],code['zs'])
                time.sleep(0.2) # 每分钟60次限制
            except Exception as e:
                print(e)
    # 更新股票代码、板块、关注股东初始化
    def update_codes(self):
        self.stockData.updateStocks()
        # self.tdxData.updateBk()
        self.localData.init_gdwarn()
        # self.localData.update_stock_pool()
    # 更新板块
    def update_bks(self):
        self.tdxData.updateBk()
    # 更新股东
    def update_gds(self):
        self.tdxData.updateGDs()
    # 更新分红
    def update_fhs(self):
        self.tdxData.updateFhYears()
    # 打开交易软件
    def open_tdx(self):
        now = time.strftime("%Y%m%d", time.localtime())
        if not DEBUG and  self.stockData.isOpen(now) <= 0:
            return
        logging.debug('软件开始登陆。。。。')
        self.stockDeal.login()
        time.sleep(10)
        self.stockDeal.click_tree_item('买入')
        # 登录成功后，休眠5秒获取持仓信息
        time.sleep(3)
        results, orders = self.stockDeal.orders()
        self.les_money = float(results['可用'])
        # 可买入的股票，保存在数据库表中(月线为卖出时删除该自选，在关闭时合并股票到表中，如果表中没有股票从当月可操作股票中随机获取)
        # 获取可买入数量，可买入的股票池，每只买入金额，可卖出的股票池
        nums,buy_data,level_money,seal_data = self.localData.get_buy_stocks(self.les_money)
        self.level_money = level_money
        self.seal_data = seal_data
        self.buy_pools = {} # 讲买卖股票池改为{code:'',num:''}形式
        if len(buy_data)>0:
            for i in range(nums):
                self.buy_pools[buy_data[i]]=0
        # 根据持仓查询对应的月回测记录，讲交易状态放入缓存
        self.seal_pools = {}  # 可卖出的股票
        try:
            for i in range(len(orders)):
                self.seal_pools[orders[i][0]]=orders[i][4]
            self.isopen = True
            logging.debug('软件开始登陆成功。\n可用资金%s,买入股票池%s,持仓%s'%(self.les_money,str(self.buy_pools),str(self.seal_pools)))
        except Exception as e:
            logging.debug('获取持仓失败%s'%e)
    # 关闭交易软件
    def close_tdx(self):
        now = time.strftime("%Y%m%d", time.localtime())
        if not DEBUG and  self.stockData.isOpen(now) <= 0:
            return
        logging.debug('软件即将关闭。。。。')
        try:
            # 当日成交,如果有成交记录发送邮件通知
            dayorders = self.stockDeal.day_orders()
            # 关闭交易软件
            self.stockDeal.destory()
            # 根据当日成交更新表成交
            self.localData.update_stock_pool(dayorders,handle=1)
            self.mailUtil.sendEmail([MAIL_USER], '当日成交', self.localData.get_order_msg(dayorders))
            logging.debug('软件已关闭.当日成交明细：\n%s'%("\n".join('%s' % id for id in dayorders)))
        except Exception as e:
            pass
        self.isopen = False
    # 个股预警交易
    def update_datas(self):
        now = time.strftime("%Y%m%d", time.localtime())
        if not DEBUG and self.stockData.isOpen(now) <= 0:
            return
        if not DEBUG and not self.localData.is_deal_time():
            return
        if not self.isopen:
            self.close_tdx()
            self.open_tdx()
        # 设置初始数据
        config.putByKey('TDX_CATEGORY','9')
        pools = {}
        pools.update(self.buy_pools)
        pools.update(self.seal_pools)
        pools_data = []
        for code,num in pools.items():
            # 更新数据
            df = self.localData.data(code,0)
            current_price = df.tail(1)['close'].values[0]
            # 回测
            g57 = StockTest3(code, 0, 'Test3',data=df)
            order,result,msgs = g57.run()
            # 解析回测结果:日期','类型','价格','手数','成交额','扣除费
            # base = self.localData.get_base(code, 0)
            arr = order.split('\t')
            if arr[0] != now: # 当天买组交易
                continue
            # 手数需要重新计算
            if arr[1]=='1' :# 买入
                self.stockDeal.click_toolbar('买入')
                logging.debug('买入：%s'%order)
                if len(self.buy_pools)>0:# 当月线为买入状态方可交易
                    num = int(self.level_money[code] / current_price / 100) * 100
                    # 根据编号
                    # self.stockDeal.buy(code=code,type=base['type'],price=current_price,num=num)
                    self.buy_pools.pop(code,'404') # 买入后移出股票池
                    pools_data.append({'code': code, 'state': 1, 'num': num})
                    logging.info('买入成功：代码：%s，价格：%s，数量：%s' % (code,current_price,num))
                else:
                    logging.error('买入失败，买入股票池%s,待买入%s,价格%s'%(self.buy_pools,code,current_price))
                    self.mailUtil.sendEmail([MAIL_USER], '交易失败，请及时关注', '买入失败%s'%order)
            elif arr[1]=='0':# 卖出
                self.stockDeal.click_toolbar('卖出')
                logging.debug('卖出：%s' % order)
                num = self.seal_pools.get(code,0)
                if self.seal_pools.get(code,0) ==0:
                    err_msg  =  '卖出失败，代码：%s，当前价格：%s，数量：%s' % (code,current_price,num)
                    logging.error(err_msg)
                    self.mailUtil.sendEmail([MAIL_USER], '交易失败，请及时关注', err_msg)
                    continue
                # self.stockDeal.seal(code=code,type=base['type'],price=current_price,num=num)
                pools_data.append({'code': code, 'state': 0, 'num': 0})
                self.seal_pools.pop(code,'404')
                logging.info('卖出成功：代码：%s，价格：%s，数量：%s' % (code, current_price, num))
                # 如果月线为买入状态，需加入到self.pools第一个位置
                if self.seal_data.get(code,0)>0:
                    self.buy_pools[code] = self.stockDeal.get_money(current_price,num)
                else:
                    logging.error('卖出池%s未找到%s'%(str(self.seal_data,code)))

    @classmethod
    def getInstance(cls):
        if not hasattr(StockJob, "_instance"):
            StockJob._instance = StockJob()
        return StockJob._instance
if __name__ == '__main__':
    # 每天7点下载数据//,start='2020-05-07 19:00:00'
    # StockJob.getInstance().add_interval_job(StockJob.download).start()
    # 每天8点进行回测系统数据
    # StockJob.getInstance().add_interval_job(StockJob.test).start()
    # StockJob.update_codes()
    # StockJob.update_gds()
    # StockJob.update_fhs()
    # StockJob.getInstance().test()
    # df = LocalData.getInstance().data('002279', 0)
    # g57 = StockTest2('002279', 0, 'Test2', data=df)
    # order,result,msgs = g57.run()
        # 初始化股票月回测
    # config.putByKey('TDX_CATEGORY', '6')
    # 回测
    # df = LocalData.getInstance().data('002279', 0)
    # g57 = StockTest3('002279', 0, 'Test3', data=df)
    # order, result, msgs = g57.run()
    # arr = order.split('\t')
    # print(arr[0] == time.strftime("%Y%m%d", time.localtime()))

    stockJob = StockJob.getInstance()
    # 1.每年一月一号8:00，更新股票代码、更新板块
    stockJob.add_cron_job(stockJob.update_codes,month='1',day='1',hour='8',minute='0')
    #2.每星期六20:00更新股东人数
    stockJob.add_cron_job(stockJob.update_gds, day_of_week='sat', hour='18', minute='0')
    #3.每周六16:00以后更新分红数据
    stockJob.add_cron_job(stockJob.update_fhs, day_of_week='sat', hour='16', minute='0')
    #4.每天17点下载数据，20点更新股票池的月线预警值
    stockJob.add_cron_job(stockJob.test, hour='20', minute='0')
    #5.每天9:30,到15:00，没5分钟 进行下载数据并回测
    stockJob.add_cron_job(stockJob.update_datas, hour='9-14', minute='*/5')
    #6.每周1-5  9:00打开交易软件
    stockJob.add_cron_job(stockJob.open_tdx, hour='9', minute='18')
    #6.每周1-7  15:00 关闭交易软件，并发送当天交易流水
    stockJob.add_cron_job(stockJob.close_tdx, hour='15', minute='30')
    stockJob.start()

    # 更新数据库字段测试
    # StockData.getInstance().updateStocks()
    # LocalData.getInstance().data('002279',0)
    # LocalData.getInstance().update_stock_pool()