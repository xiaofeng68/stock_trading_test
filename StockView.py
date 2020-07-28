"""
用于图形展示
"""
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker  # 用于日期刻度定制
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import sys
Major_Version_Number = int(sys.version[0:1])
Minor_Version_Number = int(sys.version[2:3])
if Minor_Version_Number>5:
    from mplfinance import original_flavor as mpf  # 用新版库里面的旧版实现(跟mpl_finance一模一样)
else:
    import mpl_finance as mpf
from matplotlib import colors as mcolors  # 用于颜色转换成渲染时顶点需要的颜色格式
from matplotlib.collections import LineCollection, PolyCollection  # 用于绘制直线集合和多边形集合
import tkinter as tk
import matplotlib.dates as mdates
import matplotlib as mpl# 用于设置曲线参数
from cycler import cycler# 用于定制线条颜色

from StockCalc import *
from StockData import LocalData

#  显示K线
def view2(master,data,title='',xlabel='',ylabel='价格'):
    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    arr = data.copy()
    dates = pd.to_datetime(arr['trade_date'])
    plt.plot(dates, arr['MA5'])
    plt.plot(dates, arr['MA10'])
    plt.plot(dates, arr['MA20'])
    plt.legend(('MA5', 'MA10', 'MA20'))
    plt.grid(True)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    canvas = FigureCanvasTkAgg(fig, master=master)
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=1)
    return canvas
def view3(master,data,title=''):
    # 获取数据
    # calc_kdj(data)  # 计算KDJ值，数据存于DataFrame中
    # 数据
    # daily = LocalData.getInstance().data('000001', 0)
    daily = data.copy()
    daily = KDJ(daily)
    daily.rename(
        columns={
            'trade_date': 'date', 'vol': 'volume','macd':'bar','DIF':'dif','DEA':'dea','MACD':'bar','K':'k','D':'d','J':'j'},
        inplace=True)
    df = daily[-150:]  # 取最近的N天测试，列顺序为 date,open,close,high,low,volume,dif,dea,bar,k,d,j
    df = df[['date', 'open', 'close', 'high', 'low', 'volume', 'dif', 'dea', 'bar','k','d','j']]
    # 日期转换成整数序列
    date_tickers = df.date.values
    df.date = range(0, len(df))  # 日期改变成序号
    matix = df.values  # 转换成绘制蜡烛图需要的数据格式(date, open, close, high, low, volume)
    xdates = matix[:, 0]  # X轴数据(这里用的天数索引)

    # 设置外观效果
    plt.rc('font', family='Microsoft YaHei')  # 用中文字体，防止中文显示不出来
    plt.rc('figure', fc='k')  # 绘图对象背景图
    plt.rc('text', c='#800000')  # 文本颜色
    plt.rc('axes', axisbelow=True, xmargin=0, fc='k', ec='#800000', lw=1.5, labelcolor='#800000',
           unicode_minus=False)  # 坐标轴属性(置底，左边无空隙，背景色，边框色，线宽，文本颜色，中文负号修正)
    plt.rc('xtick', c='#d43221')  # x轴刻度文字颜色
    plt.rc('ytick', c='#d43221')  # y轴刻度文字颜色
    plt.rc('grid', c='#800000', alpha=0.9, ls=':', lw=0.8)  # 网格属性(颜色，透明值，线条样式，线宽)
    plt.rc('lines', lw=0.8)  # 全局线宽

    # 创建绘图对象和4个坐标轴
    fig = plt.figure(figsize=(16, 8))
    left, width = 0.05, 0.9
    ax1 = fig.add_axes([left, 0.6, width, 0.35])  # left, bottom, width, height
    ax2 = fig.add_axes([left, 0.45, width, 0.15], sharex=ax1)  # 共享ax1轴
    ax3 = fig.add_axes([left, 0.25, width, 0.2], sharex=ax1)  # 共享ax1轴
    ax4 = fig.add_axes([left, 0.05, width, 0.2], sharex=ax1)  # 共享ax1轴
    plt.setp(ax1.get_xticklabels(), visible=False)  # 使x轴刻度文本不可见，因为共享，不需要显示
    plt.setp(ax2.get_xticklabels(), visible=False)  # 使x轴刻度文本不可见，因为共享，不需要显示
    plt.setp(ax3.get_xticklabels(), visible=False)  # 使x轴刻度文本不可见，因为共享，不需要显示
    # 绘制蜡烛图
    def format_date(x, pos=None):
        return '' if x < 0 or x > len(date_tickers) - 1 else date_tickers[
            int(x)]  # 日期格式化函数，根据天数索引取出日期值
    ax1.xaxis.set_major_formatter(ticker.FuncFormatter(format_date))  # 设置自定义x轴格式化日期函数
    ax1.xaxis.set_major_locator(ticker.MultipleLocator(max(int(len(df) / 15), 5)))  # 横向最多排15个左右的日期，最少5个，防止日期太拥挤
    # mpf.candlestick_ochl(ax1, matix, width=0.5, colorup='#ff3232', colordown='#54fcfc')
    # # 下面这一段代码，替换了上面注释的这个函数，因为上面的这个函数达不到同花顺的效果
    opens, closes, highs, lows = matix[:, 1], matix[:, 2], matix[:, 3], matix[:, 4]  # 取出ochl值
    avg_dist_between_points = (xdates[-1] - xdates[0]) / float(len(xdates))  # 计算每个日期之间的距离
    delta = avg_dist_between_points / 4.0  # 用于K线实体(矩形)的偏移坐标计算
    barVerts = [((date - delta, open), (date - delta, close), (date + delta, close), (date + delta, open)) for
                date, open, close in zip(xdates, opens, closes)]  # 生成K线实体(矩形)的4个顶点坐标
    rangeSegLow = [((date, low), (date, min(open, close))) for date, low, open, close in
                   zip(xdates, lows, opens, closes)]  # 生成下影线顶点列表
    rangeSegHigh = [((date, high), (date, max(open, close))) for date, high, open, close in
                    zip(xdates, highs, opens, closes)]  # 生成上影线顶点列表
    rangeSegments = rangeSegLow + rangeSegHigh  # 上下影线顶点列表
    cmap = {True: mcolors.to_rgba('#000000', 1.0),
            False: mcolors.to_rgba('#54fcfc', 1.0)}  # K线实体(矩形)中间的背景色(True是上涨颜色，False是下跌颜色)
    inner_colors = [cmap[opn < cls] for opn, cls in zip(opens, closes)]  # K线实体(矩形)中间的背景色列表
    cmap = {True: mcolors.to_rgba('#ff3232', 1.0),
            False: mcolors.to_rgba('#54fcfc', 1.0)}  # K线实体(矩形)边框线颜色(上下影线和后面的成交量颜色也共用)
    updown_colors = [cmap[opn < cls] for opn, cls in zip(opens, closes)]  # K线实体(矩形)边框线颜色(上下影线和后面的成交量颜色也共用)列表
    ax1.add_collection(LineCollection(rangeSegments, colors=updown_colors, linewidths=0.5,
                                      antialiaseds=False))  # 生成上下影线的顶点数据(颜色，线宽，反锯齿，反锯齿关闭好像没效果)
    ax1.add_collection(PolyCollection(barVerts, facecolors=inner_colors, edgecolors=updown_colors, antialiaseds=False,
                                      linewidths=0.5))  # 生成多边形(矩形)顶点数据(背景填充色，边框色，反锯齿，线宽)

    # 绘制均线
    mav_colors = ['#ffffff', '#d4ff07', '#ff80ff']  # 均线循环颜色, '#00e600', '#02e2f4', '#ffffb9', '#2a6848'
    mav_period = [5, 10, 20]  # 定义要绘制的均线周期，可增减, 30, 60, 120, 180
    n = len(df)
    for i in range(len(mav_period)):
        if n >= mav_period[i]:
            mav_vals = df['close'].rolling(mav_period[i]).mean().values
            ax1.plot(xdates, mav_vals, c=mav_colors[i % len(mav_colors)], label='MA' + str(mav_period[i]))
    # ax1.set_title(title)  # 标题
    ax1.yaxis.set_ticks_position('right')  # y轴显示在右边
    ax1.grid(True)  # 画网格
    ax1.legend(loc='upper left')  # 图例放置于右上角
    # ax1.xaxis_date()  # 好像要不要效果一样？

    # 绘制成交量和成交量均线（5日，10日）
    # ax2.bar(xdates, matix[:, 5], width= 0.5, color=updown_colors) # 绘制成交量柱状图
    barVerts = [((date - delta, 0), (date - delta, vol), (date + delta, vol), (date + delta, 0)) for date, vol in
                zip(xdates, matix[:, 5])]  # 生成K线实体(矩形)的4个顶点坐标
    ax2.add_collection(PolyCollection(barVerts, facecolors=inner_colors, edgecolors=updown_colors, antialiaseds=False,
                                      linewidths=0.5))  # 生成多边形(矩形)顶点数据(背景填充色，边框色，反锯齿，线宽)
    if n >= 5:  # 5日均线，作法类似前面的均线
        vol5 = df['volume'].rolling(5).mean().values
        ax2.plot(xdates, vol5, c='y', label='VOL5')
    if n >= 10:  # 10日均线，作法类似前面的均线
        vol10 = df['volume'].rolling(10).mean().values
        ax2.plot(xdates, vol10, c='w', label='VOL10')
    ax2.yaxis.set_ticks_position('right')  # y轴显示在右边
    ax2.legend(loc='upper left')  # 图例放置于右上角
    ax2.grid(True)  # 画网格
    # ax2.set_ylabel('成交量') # y轴名称

    # 绘制MACD
    difs, deas, bars = matix[:, 6], matix[:, 7], matix[:, 8]  # 取出MACD值
    ax3.axhline(0, ls='-', c='g', lw=0.5)  # 水平线
    ax3.plot(xdates, difs, c='w', label='DIFF')  # 绘制DIFF线
    ax3.plot(xdates, deas, c='y', label='DEA')  # 绘制DEA线
    # ax3.bar(xdates, df['bar'], width= 0.05, color=bar_colors) # 绘制成交量柱状图(发现用bar绘制，线的粗细不一致，故使用下面的直线列表)
    cmap = {True: mcolors.to_rgba('r', 1.0), False: mcolors.to_rgba('g', 1.0)}  # MACD线颜色，大于0为红色，小于0为绿色
    bar_colors = [cmap[bar > 0] for bar in bars]  # MACD线颜色列表
    vlines = [((date, 0), (date, bars[date])) for date in range(len(bars))]  # 生成MACD线顶点列表
    ax3.add_collection(
        LineCollection(vlines, colors=bar_colors, linewidths=0.5, antialiaseds=False))  # 生成MACD线的顶点数据(颜色，线宽，反锯齿)
    ax3.legend(loc='upper left')  # 图例放置于右上角
    ax3.yaxis.set_ticks_position('right')  # y轴显示在右边
    ax3.grid(True)  # 画网格

    # # 绘制KDJ
    K, D, J = matix[:, 9], matix[:, 10], matix[:, 11]  # 取出KDJ值
    ax4.axhline(0, ls='-', c='g', lw=0.5)  # 水平线
    ax4.yaxis.set_ticks_position('right')  # y轴显示在右边
    ax4.plot(xdates, K, c='y', label='K')  # 绘制K线
    ax4.plot(xdates, D, c='c', label='D')  # 绘制D线
    ax4.plot(xdates, J, c='m', label='J')  # 绘制J线
    ax4.legend(loc='upper left')  # 图例放置于右上角
    ax4.grid(True)  # 画网格

    # set useblit = True on gtkagg for enhanced performance
    # from matplotlib.widgets import Cursor  # 处理鼠标
    # cursor = Cursor(ax1, useblit=True, color='red', linewidth=2)

    canvas = FigureCanvasTkAgg(fig, master=master)
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=1)
    return canvas


def view3_new(master,data,title='',xlabel='',ylabel='价格'):
    # 数据
    daily = LocalData.getInstance().data('000001',0).tail(150)
    daily.rename(
        columns={
            'trade_date': 'Date', 'open': 'Open',
            'high': 'High', 'low': 'Low',
            'close': 'Close', 'vol': 'Volume'},
        inplace=True)
    # 转换为日期格式
    daily['Date'] = pd.to_datetime(daily['Date'])
    # 将日期列作为行索引
    daily.set_index(['Date'], inplace=True)
    # 样式
    # 设置基本参数
    # type:绘制图形的类型，有candle, renko, ohlc, line等
    # 此处选择candle,即K线图
    # mav(moving average):均线类型,此处设置7,30,60日线
    # volume:布尔类型，设置是否显示成交量，默认False
    # title:设置标题
    # y_label:设置纵轴主标题
    # y_label_lower:设置成交量图一栏的标题
    # figratio:设置图形纵横比
    # figscale:设置图形尺寸(数值越大图像质量越高)
    kwargs = dict(
        type='candle',
        mav=(5, 10, 20),
        volume=True,
        title='',
        ylabel='',
        datetime_format='%Y-%m-%d',
        ylabel_lower='',
        figratio=(15, 10),
        figscale=5)
    # 设置marketcolors
    # up:设置K线线柱颜色，up意为收盘价大于等于开盘价
    # down:与up相反，这样设置与国内K线颜色标准相符
    # edge:K线线柱边缘颜色(i代表继承自up和down的颜色)，下同。详见官方文档)
    # wick:灯芯(上下影线)颜色
    # volume:成交量直方图的颜色
    # inherit:是否继承，选填
    mc = mpf.make_marketcolors(
        up='red',
        down='green',
        edge='i',
        wick='i',
        volume='in',
        inherit=True)
    # 设置图形风格
    # gridaxis:设置网格线位置
    # gridstyle:设置网格线线型
    # y_on_right:设置y轴位置是否在右
    s = mpf.make_mpf_style(
        gridaxis='both',
        gridstyle='-.',
        y_on_right=False,
        marketcolors=mc)
    # 设置均线颜色，配色表可见下图
    # 建议设置较深的颜色且与红色、绿色形成对比
    # 此处设置七条均线的颜色，也可应用默认设置
    mpl.rcParams['axes.prop_cycle'] = cycler(
        color=['dodgerblue', 'deeppink',
               'navy', 'teal', 'maroon', 'darkorange',
               'indigo'])
    # 设置线宽
    mpl.rcParams['lines.linewidth'] = .5

    # 图形绘制
    # show_nontrading:是否显示非交易日，默认False
    # savefig:导出图片，填写文件名及后缀
    fig,axes = mpf.plot(daily,
             **kwargs,
             style=s,
             returnfig=True,
             show_nontrading=False)#,savefig='1.png'


    canvas = FigureCanvasTkAgg(fig, master=master)
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=1)

# if __name__=='__main__':
#     # view3(None,None)
#     print(plt.matplotlib_fname())  # 将会获得matplotlib配置文件
#     from matplotlib.font_manager import _rebuild
#
#     print(plt.rcParams['font.serif'] )