"""
全局配置类,读取g57.ini
"""
import configparser
import os
import sys
#根据系统运行位置确认basedir路径
if getattr(sys, 'frozen', None):
    basedir = os.path.dirname(sys.executable)
    DEFAULT_DIR_PATH = basedir
else:
    basedir = os.path.dirname(__file__)
# 优化配置，将内存配置转为配置文件
class StockConfig:
    def __init__(self):
        self.config = configparser.ConfigParser()  # 类实例化
        self.path = os.path.join(basedir, 'g57.ini')
        self.config.read(self.path, encoding='utf-8')
    def get(self,sections=None,key=None):
        if not all([sections,key]):
            return None
        try:
            return self.config.get(sections, key.lower())
        except Exception as e:
            return None
    def put(self,sections=None,key=None,value=None):
        if not all([sections, key,value]):
            return None
        try:
            self.config.set(sections, key.lower(), value)  # 写入数据
        except Exception as e:
            return None
    def getByKey(self,key):
        sels = self.sections()
        for sel in sels:
            val = self.config.items(sel)
            for k,v in val:
                if k ==key.lower():
                    return v
        return None
    def putByKey(self,key,value):
        sels = self.sections()
        for sel in sels:
            val = self.config.items(sel)
            for k, v in val:
                if k == key.lower():
                    self.config.set(sel, k, value)  # 写入数据
    def sections(self):
        return self.config.sections()
    def save(self):
        self.config.write(open(self.path, 'a'))

    @classmethod
    def getInstance(cls):
        if not hasattr(StockConfig, "_instance"):
            StockConfig._instance = StockConfig()
        return StockConfig._instance
config = StockConfig.getInstance()
DEFAULT_WINDOW_LOCATION = config.get(sections='window',key='default_window_location')
DEFAULT_DIR_PATH = config.get(sections='window',key='default_dir_path')
STOCK_BJ = float(config.get(sections='test',key='stock_bj'))
STOCK_BUY_INDEX = config.get(sections='test',key='stock_buy_index')
STOCK_GHF = float(config.get(sections='test',key='stock_ghf'))
STOCK_DSXF  = float(config.get(sections='test',key='stock_dsxf'))
STOCK_SXF = float(config.get(sections='test',key='stock_sxf'))
STOCK_SEAL_INDEX = config.get(sections='test',key='stock_seal_index')
STOCK_YHS = float(config.get(sections='test',key='stock_yhs'))
STOCK_SPLIT = int(config.get(sections='test',key='stock_split'))
TUSHARE_TOKEN = config.get(sections='data',key='tushare_token')
TDX_IP = config.get(sections='data',key='tdx_ip')
TDX_PORT = int(config.get(sections='data',key='tdx_port'))
TDX_USER = config.get(sections='data',key='tdx_user')
TDX_PWD = config.get(sections='data',key='tdx_pwd')
TDX_DIMPWD = config.get(sections='data',key='tdx_dimpwd')
MAIL_HOST = config.get(sections='mail',key='mail_host')
MAIL_USER = config.get(sections='mail',key='mail_user')
MAIL_PASS = config.get(sections='mail',key='mail_pass')
MAIL_TO = config.get(sections='mail',key='mail_to')

DB_URL = config.get(sections='db',key='db_url')
DB_TYPE = config.get(sections='db',key='db_type')

DEBUG = False

# 数据库配置
from sqlalchemy.types import NVARCHAR, Float, Integer,Numeric,BigInteger
STOCK_BASIC_DTYPE ={
'ts_code':NVARCHAR(10),
'symbol': NVARCHAR(6),
'name': NVARCHAR(50),
'area': NVARCHAR(50),
'industry': NVARCHAR(50),
'fullname': NVARCHAR(100),
'enname': NVARCHAR(100),
'market': NVARCHAR(10),
'exchange': NVARCHAR(10),
'curr_type': NVARCHAR(10),
'list_status': NVARCHAR(10),
'list_date': NVARCHAR(10),
'delist_date': NVARCHAR(10),
}
STOCK_TRADE_DATA = {
'open':Numeric(10,2),
'close':Numeric(10,2),
'high':Numeric(10,2),
'low':Numeric(10,2),
'vol':Numeric(10,2),
'trade_date':NVARCHAR(10),
}
STOCK_GDWARN_DTYPE = {
'name': NVARCHAR(50),
'type': Integer
}
STOCK_BUY_POOLS_DTYPE = {
'code':NVARCHAR(6),
'num':Integer,
'seq':Integer,
'state':Integer,
}
STOCK_BK_DTYPE = {
'blockname':NVARCHAR(50),
'block_type':Integer,
'code_index':Integer,
'code':NVARCHAR(10),
}
STOCK_BK = {
'code':NVARCHAR(6),
'volunit':Integer,
'decimal_point':Integer,
'name':NVARCHAR(50),
'pre_close':NVARCHAR(20),
'type':Integer,
}
STOCK_ORDER_DTYPE = {
'cje': BigInteger,
'close':Numeric(10,2),
'code': NVARCHAR(6),
'kc':Numeric(10,2),
'key':NVARCHAR(10),
'ss':Integer,
'type':Integer,
'trade_date':NVARCHAR(10),
'shift_type':Integer,
}
STOCK_RESULT_DTYPE = {
'bj':Integer,
'cgl':Integer,
'code':NVARCHAR(6),
'jf':Numeric(10,2),
'jycs':Integer,
'key':NVARCHAR(10),
'ztsy':Integer,
}
STOCK_GDRS_DTYPE = {
'cmjzd':NVARCHAR(20),
'gdrs':NVARCHAR(20),
'gdrs_jsqbh':NVARCHAR(20),
'gj':NVARCHAR(20),
'qsdgdcghj':NVARCHAR(20),
'qsdltgdcghj':NVARCHAR(20),
'rjcgje':NVARCHAR(20),
'rjltg':NVARCHAR(20),
'rjltg_jsqbh':NVARCHAR(20),
'rq':NVARCHAR(10),
'code':NVARCHAR(6),
}
STOCK_SDGD_DTYPE = {
'bdbl':NVARCHAR(20),
'cgs':NVARCHAR(20),
'gdmc':NVARCHAR(255),
'gflx':NVARCHAR(50),
'mc':Integer,
'rq':NVARCHAR(10),
'zj':NVARCHAR(20),
'zltgbcgbl':NVARCHAR(10),
'code':NVARCHAR(6),
}
