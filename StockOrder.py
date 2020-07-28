from StockData import DBUtil, TdxData
import  pandas as pd

db = DBUtil.getInstance()
if db.is_exist('stock_%s_%s_%s'%(9,0,'000001')):
    # 获取现有数据
    df = db.read_sql('select * from stock_%s_%s_%s'%(9,0,'000001'))
    print(df)
    data = TdxData.getInstance().days('000001', 0, bk=0, all=False, day=1)
    print(data)
    dd = df[0:-1].append(data)
    print(dd)