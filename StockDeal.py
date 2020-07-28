import pywinauto
import pyautogui
from pywinauto import mouse
from pywinauto import keyboard
import time

import StockMail
from StockConfig import *
"""
国信证券V7.18 自动化交易，为了防止交易时交易软件锁住，建议修改锁时间，或定时调用reinput方法
# gxzq = Trader_gxzq.getInstance(no='75******45',pwd='******',dimpwd='******')
# gxzq.login()
# gxzq.click_tree_item('买入')
# gxzq.click_tree_item('卖出')
# gxzq.click_toolbar('买入')
# gxzq.click_toolbar('卖出')
# gxzq.seal('000001',0,11,1000)
# gxzq.buy('000001',0,11,1000)
# gxzq.reinput()
"""
class Trader_gxzq(object):
    def __init__(self,no=None,pwd=None,dimpwd=None,path=r'C:\zd_gxzq\TdxW.exe'):
        if not all([no, pwd, dimpwd]):
            raise Exception('请输入账号等信息')
        self.path = path
        self.app = pywinauto.Application(backend='uia').start(path)
        # self.app = pywinauto.Application(backend='uia').connect(process=5448)
        self.no = no
        self.pwd = pwd
        self.dimpw = dimpwd


    # 金太阳账号登录
    def login(self):
        try:
            self._login()
        except Exception as e:
            self.destory()
            self.app = pywinauto.Application(backend='uia').start(self.path)
            self._login()
    def _login(self,login_title='国信金太阳网上交易专业版V7.18',deal_title='[国信金太阳网上交易专业版V7.18 - [行情报价-沪深Ａ股]][Desktop]'):
        login_win = self.app[login_title]
        login_win.set_focus()
        # 获取窗口坐标，点击独立交易
        react = login_win.rectangle()
        # 点击独立交易
        mouse.click(coords=(react.left + 330 + 55, react.top + 68 + 13))
        # 输入账号密码
        # login_win.ComboBox.child_window(auto_id="1001", control_type="Edit").set_text(no)
        pyautogui.typewrite(str(self.no))
        keyboard.send_keys('{VK_TAB}')
        pyautogui.typewrite(str(self.pwd))
        keyboard.send_keys('{VK_TAB}')
        pyautogui.typewrite(str(self.dimpw))
        # 点击登录
        mouse.click(coords=(react.left + 90 + 30, react.top + 230 + 11))
        self.deal_win = self.app[deal_title]
    # 点击左侧树
    def click_tree_item(self,path):
        left_tree = self.deal_win['SysTreeView32']
        # 获取买入TreeItem坐标，使用鼠标点击
        buy_node = left_tree.child_window(title="	%s" % path, control_type="TreeItem")
        buy_node_point = buy_node.rectangle().mid_point()
        mouse.click(coords=buy_node_point)
    # 点击toolbar
    def click_toolbar(self,path=None):
        deal_win_toolbar = self.deal_win['MainViewBar']
        deal_win_toolbar.child_window(title=path, control_type="Button").click()
    # 卖出股票
    def seal(self,code=None, type=None, price=None, num=None):
        right_win = self.deal_win.child_window(auto_id="59649", control_type="Pane")
        # 股东代码
        code_type_point = right_win.child_window(auto_id="12015", control_type="ComboBox").rectangle().mid_point()
        mouse.click(coords=code_type_point)
        mouse.click(coords=(code_type_point.x, code_type_point.y + 15 + type * 15))  # 15 深 30 沪
        right_win.child_window(auto_id="12006", control_type="Edit").set_text(str(price))  # 卖出价格
        right_win.child_window(auto_id="12005", control_type="Edit").set_text(str(code))  # 证券代码
        right_win.child_window(auto_id="12007", control_type="Edit").set_text(str(num))  # 数量
        time.sleep(0.3)
        right_win.child_window(title="卖出下单", auto_id="2010", control_type="Button").click()
        time.sleep(0.2)
        keyboard.send_keys('{VK_RETURN}')
        time.sleep(2)
        keyboard.send_keys('{VK_ESCAPE}')
    # 买入股票
    def buy(self,code=None, type=None, price=None, num=None):
        right_win = self.deal_win.child_window(auto_id="59649", control_type="Pane")
        right_win.print_ctrl_ids()
        # 股东代码
        code_type_point = right_win.child_window(auto_id="12015", control_type="ComboBox").rectangle().mid_point()
        mouse.click(coords=code_type_point)
        mouse.click(coords=(code_type_point.x, code_type_point.y + 15 + type * 15))  # 15 深 30 沪
        right_win.child_window(auto_id="12006", control_type="Edit").set_text(str(price))  # 卖出价格
        right_win.child_window(auto_id="12005", control_type="Edit").set_text(str(code))  # 证券代码
        right_win.child_window(auto_id="12007", control_type="Edit").set_text(str(num))  # 数量
        time.sleep(0.3)
        right_win.child_window(title="买入下单", auto_id="2010", control_type="Button").click()
        time.sleep(0.2)
        keyboard.send_keys('{VK_RETURN}')
        time.sleep(2)
        keyboard.send_keys('{VK_ESCAPE}')
    # 查询股票持仓
    def orders(self):
        self.click_toolbar('持仓')
        right_win = self.deal_win.child_window(auto_id="59649", control_type="Pane")
        label = right_win.child_window(auto_id="1576", control_type="Text")
        list = right_win.child_window(title="002279", control_type="ListItem")
        try:
            arr = list.texts()
        except Exception as e:
            arr = []
        return self._get_orders(label.texts(),arr)
    # 查询当日成交
    def day_orders(self):
        self.click_toolbar('成交')
        right_win = self.deal_win.child_window(auto_id="59649", control_type="Pane")
        list = right_win.child_window(auto_id="1567", control_type="List")
        return list.texts()

    def destory(self):
        try:
            self.app.kill()
        except Exception as e:
            pass
        self.app = None
    def reinput(self):
        reinput = self.app['[通达信网上交易][][][][国信金太阳网上交易专业版V7.18 - [行情报价-沪深Ａ股]][Desktop]']
        reinput.set_focus()
        lab_point = reinput.child_window(title="交易密码:", auto_id="610", control_type="Text").rectangle().mid_point()
        mouse.click(coords=(lab_point.x + 100, lab_point.y))
        # 输入账号密码
        pyautogui.typewrite(str(self.pwd))
        reinput.child_window(title="确定", auto_id="442", control_type="Button").click()

    def _get_orders(self,str_result,stocks):
        result = {}
        static_arr = list(filter(None, str_result[0][1:-2].split(' ')))
        orders = []
        for static in static_arr:
            temp = static.split(':')
            result[temp[0]] = temp[1]
        if len(stocks)>0 and int(stocks[4])>0:
            orders.append(stocks)
        return result, orders
    # 获取去除交易费后的金额-10%的价格
    @staticmethod
    def get_money(price,num):
        cje = int(num * price)  # 成交额
        yj = round(cje * STOCK_SXF, 2)  # 手续费
        ghf = round(cje * STOCK_GHF, 2)  # 过户费
        dsxf = round(cje * STOCK_DSXF, 2)  # 代收规费
        yhs = round(cje * STOCK_YHS, 2)  # 印花税
        sxf = yj if (yj + dsxf) > 5 else 5 - dsxf
        kc = round(sxf + ghf + dsxf + yhs, 2)
        return int(cje - kc-price*0.1)
    @classmethod
    def getInstance(cls,no=None,pwd=None,dimpwd=None):
        if not hasattr(Trader_gxzq, "_instance"):
            Trader_gxzq._instance = Trader_gxzq(no=no,pwd=pwd,dimpwd=dimpwd)
        return Trader_gxzq._instance
