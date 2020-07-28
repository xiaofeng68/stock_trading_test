import os
import subprocess
import threading
import tkinter as tk
import tkinter.ttk as ttk   #导入Tkinter.ttk
from tkinter import messagebox
from tkinter.filedialog import askopenfilename, asksaveasfilename, re
from tkinter.messagebox import showinfo
from tkinter.scrolledtext import ScrolledText
from StockConfig import *
from StockData import LocalData, TdxData, FoldData,logging
from PIL import Image, ImageTk
from StockCalc import *
from StockJob import StockJob
import sys

#根据系统运行位置确认basedir路径
if getattr(sys, 'frozen', None):
    basedir = sys._MEIPASS
    DEFAULT_DIR_PATH = os.path.dirname(sys.executable)
else:
    basedir = os.path.dirname(__file__)

"""
使用窗口应用实现量化交易，是本系统入口
"""
class StockWindow(tk.Tk):
    # 自定义窗口类，扩展常用功能
    """接收主题、坐标、长宽信息"""
    def __init__(self,title='窗口',x=0,y=0,w=800,h=600,**kwargs):
        super().__init__()
        self.title(title)
        self.x = x
        self.y = y
        self.width = w
        self.height = h
        self.options = kwargs
        self.location() # 窗口所在位置，默认在左上角
        self.protocol("WM_DELETE_WINDOW", self.callback_quit)

    """设置窗口位置,支持四角+居中+自定义位置"""
    def location(self):
        ws = self.winfo_screenwidth()  # 获取屏幕宽度
        hs = self.winfo_screenheight()  # 获取屏幕高度
        loc = getattr(self.options,'location',None)
        if loc is not None:
            location = self.options['location']
            if 1 == location:
                self.x = 0
                self.y = 0
            elif 2==location:
                self.x=ws-self.width
                self.y=0
            elif 3==location:
                self.x = ws-self.width
                self.y = hs-self.height
            elif 4==location:
                self.x =0
                self.y = hs-self.height
            else:
                self.x = int((ws / 2) - (self.width / 2))
                self.y = int((hs / 2) - (self.height / 2))
        elif self.x ==0 and self.y ==0 :
            self.x = int((ws / 2) - (self.width / 2))
            self.y = int((hs / 2) - (self.height / 2))
        self.geometry('{}x{}+{}+{}'.format(self.width, self.height, self.x, self.y))
    """显示窗口"""
    def show(self):
        self.mainloop() # 显示窗口
    """# messagebox.showwarning('提示','程序结束')"""
    def callback_quit(self):
        ans = messagebox.askokcancel('提示', '要程序结束吗?')  # 确定/取消，返回值True/False
        if ans == True:
            self.destroy()
# 菜单栏
class MenuBar:
    def __init__(self, root, menus=['文件', '编辑', '工具', '帮助'], items=[['文件'], ['编辑'], ['工具'], ['帮助']],fun=None):
        self.root = root
        self.menus = menus
        self.items = items
        self.menubar = tk.Menu(self.root)
        var = tk.StringVar()
        for i, x in enumerate(self.menus):
            m = tk.Menu(self.menubar, tearoff=0)
            for item in zip(self.items[i]):
                if isinstance(item, list):
                    sm = tk.Menu(self.menubar, tearoff=0)
                    for subitem in zip(item[1:]):
                        if subitem == '-':
                            sm.add_separator()
                        else:
                            sm.add_radiobutton(label=subitem, command=lambda: fun(var=var), image=None, compound='left',variable=var,value=subitem)
                    m.add_cascade(label=item[0], menu=sm)
                elif item == '-':
                    m.add_separator()
                else:
                    m.add_radiobutton(label=item, command=lambda: fun(var=var), image=None, compound='left',variable=var,value=item)
            self.menubar.add_cascade(label=x, menu=m)
        self.root.config(menu=self.menubar)
# 工具栏（横向）
class ToolsBar(tk.Frame):
    def __init__(self, root, n=3, **kw):
        tk.Frame.__init__(self, root, **kw)
        self.png = ImageTk.PhotoImage(Image.open(os.path.join(basedir, 'ico/ico.ico')))
        self.m = n  # 有10个子栏
        if self.m > 8:
            self.m = 8
        if self.m < 0:
            self.m = 1

        self.t = []
        # 添加快捷按钮
        for i in range(1,self.m+1):
            ti= ttk.Button(self, width=20, image=self.png, command=None, cursor='hand2')
            self.t.append(ti)
        # 添加搜索框
        self.type = tk.IntVar()
        self.t9 = tk.Checkbutton(self, text='个股', variable=self.type, onvalue=0, offvalue=1)
        self.t9.select()
        self.t10 = tk.Label(self, text='代码')
        self.code = tk.StringVar(value='000001')
        self.t11 = tk.Entry(self, textvariable=self.code)  # highlightcolor:颜色
        self.t12 = ttk.Button(self, command=None, text='查询')
        self.t.append(self.t9)
        self.t.append(self.t10)
        self.t.append(self.t11)
        self.t.append(self.t12)

        for i in range(self.m+4):
            self.t[i].grid(row=0, column=i, padx=1, pady=1, sticky=tk.E)

    def config(self, i, **kargs):  # 配置长度 和 颜色
        for x, y in kargs.items():
            if x == 'image':
                self.t[i].config(image=y)
            if x == 'command':
                self.t[i].config(command=y)
            if x == 'color':
                self.t[i].config(fg=y)
            if x == 'width':
                self.t[i].config(width=y)
    def get(self):
        return LocalData.getInstance().get_base(self.code.get(),self.type.get())
# 状态栏
class StatusBar(tk.Frame):
    def __init__(self, root):
        tk.Frame.__init__(self, root)
        tk.Label(self, bd=1, relief=tk.SUNKEN, anchor=tk.W, text='0000').place(x=0, y=0, relwidth=1,
                                                                               bordermode=tk.OUTSIDE)
        self.m = 5  # 有5个子栏
        self.l = []
        self.l1 = tk.Label(self, bd=1, relief=tk.SUNKEN, anchor=tk.CENTER, width=7, text='状态栏', justify=tk.CENTER)
        self.l1.pack(side=tk.LEFT, padx=1, pady=1)
        self.l.append(self.l1)
        self.l2 = tk.Label(self, bd=1, relief=tk.SUNKEN, anchor=tk.W, width=20, text='2')
        self.l2.pack(side=tk.LEFT, padx=1, pady=1)
        self.l.append(self.l2)
        self.l3 = tk.Label(self, bd=1, anchor=tk.W, relief=tk.SUNKEN, text='3')
        self.l3.pack(side=tk.LEFT, fill=tk.X)
        self.l.append(self.l3)
        self.l4 = tk.Label(self, bd=1, relief=tk.SUNKEN, anchor=tk.W, width=10, text='6')
        self.l4.pack(side=tk.RIGHT, padx=1, pady=1)

        self.l5 = tk.Label(self, bd=1, relief=tk.SUNKEN, anchor=tk.W, width=10, text='5')
        self.l5.pack(side=tk.RIGHT, padx=1, pady=1)
        self.l.append(self.l5)
        self.l.append(self.l4)

    def text(self, i, t):  # 输出文字信息
        self.l[i].config(text=t)
        self.l[i].update_idletasks()

    def config(self, i, **kargs):  # 配置长度 和 颜色
        for x, y in kargs.items():
            if x == 'text':
                self.l[i].config(text=y)
            if x == 'color':
                self.l[i].config(fg=y)
            if x == 'width':
                self.l[i].config(width=y)

    def clear(self):  # 清除所有信息
        for i in range(0, self.m):
            self.l[i].config(text='')
            self.l[i].update_idletasks()

    def set(self, i, format, *args):  # 输出格式信息
        self.l[i].config(text=format % args)
        self.l[i].update_idletasks()
# 用户代码编辑类
class EditorArea(tk.Frame):  # 继承Frame类
    def __init__(self, root=None):
        tk.Frame.__init__(self, root)
        self.root = root  # 定义内部变量root
        self.filename = ''
        self.Init()

    def openfile(self):
        # global filename
        self.filename = askopenfilename(defaultextension='.py')
        if self.filename == '':
            self.filename = None
        else:
            self.textPad.delete(1.0, tk.END)  # delete all
            f = open(self.filename, 'r', encoding='utf-8', errors='ignore')
            self.textPad.insert(1.0, f.read())
            f.close()
    def newfile(self):
        self.filename = None
        self.textPad.delete(1.0, tk.END)

    def savefile(self):
        try:
            f = open(self.filename, 'w', encoding='utf-8', errors='ignore')
            msg = self.textPad.get(1.0, tk.END)
            f.write(msg)
            f.close()
        except:
            self.saveas()
    def set_log(self,log):
        self.log = log
    def show_log(self,msg):
        self.log.insert(tk.END,msg)
    def refash(self,base):
        self.base = base
        self.log.delete(1.0,tk.END)
    def runuc(self):
        self.log.delete(1.0, tk.END)
        base = getattr(self, "base", {'code': '000001', 'type': 0})
        code = base['code']
        type = base['type']
        try:
            msg = self.textPad.get(1.0, tk.END)
            cls = re.findall('class (.*?)\(BaseTest',msg)[0]
            name = self.filename.rsplit('/',1)[1].replace('.py','')
            msg += "\nself.show_log(%s('%s',%s,'%s').run()[2])"%(cls,code,type,name)
            self.show_log('开始运行您的回测交易\n')
            exec(msg)
        except Exception as e:
            logging.error(str(e))
            showinfo(title='用户代码出错', message=str(e))

    def saveas(self):
        try:
            # global filename
            f = asksaveasfilename(initialfile='newfile', defaultextension='.py')
            self.filename = f
            fh = open(f, 'w', encoding='utf-8', errors='ignore')
            msg = self.textPad.get(1.0, tk.END)
            fh.write(msg)
            fh.close()
            # root.title('FileName:'+os.path.basename(f))
        except:
            pass

    def cut(self):
        self.textPad.event_generate('<<Cut>>')

    def copy(self):
        self.textPad.event_generate('<<Copy>>')

    def paste(self):
        self.textPad.event_generate('<<Paste>>')

    def redo(self):
        self.textPad.event_generate('<<Redo>>')

    def undo(self):
        self.textPad.event_generate('<<Undo>>')

    def search(self):
        topsearch = tk.Toplevel(self)
        topsearch.geometry('300x30+200+250')
        labell = tk.Label(topsearch, text='find')
        labell.grid(row=0, column=0, padx=5)
        entry1 = tk.Entry(topsearch, width=28)
        entry1.grid(row=0, column=1, padx=5)
        button1 = tk.Button(topsearch, text='find')
        button1.grid(row=0, column=2)

    # 用户类初始化
    def Init(self):
        # 按钮
        self.toolbar = tk.Frame(self.root, height=20)
        self.toolbarName = ('新文件', '打开', '保存', '另存',   '运行程序')#'Undo', 'Redo', 'Cut', 'Copy', 'Paste',
        self.toolbarCommand = (
        self.newfile, self.openfile, self.savefile, self.saveas,  self.runuc)#self.undo, self.redo, self.cut, self.copy, self.paste,

        def addButton(name, command):
            for (toolname, toolcom) in zip(name, command):
                shortButton = tk.Button(self.toolbar, text=toolname, relief='groove', command=toolcom)
                shortButton.pack(side=tk.LEFT, padx=2, pady=5)

        addButton(self.toolbarName, self.toolbarCommand)  # 调用添加按钮的函数
        label = tk.Label(self.toolbar, anchor=tk.E, height=1, text='文件必须以Test开头', relief=tk.FLAT, takefocus=False,fg='red')
        label.pack(side=tk.LEFT, padx=2, pady=5)
        self.toolbar.pack(side=tk.TOP, fill=tk.X)
        # 去掉右键菜单
        # # 创建弹出菜单
        # self.menubar = tk.Menu(self)
        # self.toolbarName2 = ('新文件', '打开', '保存', '另存', '运行程序')#'Undo', 'Redo', 'Cut', 'Copy', 'Paste',
        # self.toolbarCommand2 = (
        # self.newfile, self.openfile, self.savefile, self.saveas,  self.runuc) #self.undo, self.redo, self.cut, self.copy, self.paste,
        #
        # def addPopButton(name, command):
        #     for (toolname, toolcom) in zip(name, command):
        #         self.menubar.add_command(label=toolname, command=toolcom)
        #
        # def pop(event):
        #     # Menu 类里面有一个 post 方法，它接收两个参数，即 x 和y 坐标，它会在相应的位置弹出菜单。
        #     self.menubar.post(event.x_root, event.y_root)
        #
        # addPopButton(self.toolbarName2, self.toolbarCommand2)  # 创建弹出菜单
        self.textPad = tk.Text(self.root, undo=True, bg='#FFF8DC')
        self.textPad.insert(1.0, ' \n')
        self.textPad.pack(expand=tk.YES, fill=tk.BOTH)
        self.textPad.focus_set()
        # self.textPad.bind("<Button-3>", pop)
        self.scroll = tk.Scrollbar(self.textPad)
        self.textPad.config(yscrollcommand=self.scroll.set)
        self.scroll.config(command=self.textPad.yview)
        self.scroll.pack(side=tk.RIGHT, fill=tk.Y)
        var = tk.StringVar()
        self.status = tk.Label(self.root, anchor=tk.E, height=1, text='Ln', relief=tk.FLAT, takefocus=False,
                               textvariable=var, padx=2)
        self.status.pack(fill=tk.X)
# 定义我的窗口基类
class BaseWindow(tk.Toplevel):
    def __init__(self, root, title, w=600, h=500):
        super().__init__(root)
        self.width = w
        self.height = h
        self.title(title)
        self.flag = True
        self.transparent = False
        self.wm_attributes('-topmost', 1)  # 窗口置顶
        self.wm_attributes("-alpha", 0.8)  # 设置窗口透明度从0-1，1是不透明，0是全透明
        self.setCenter()

    # 移动窗口到屏幕中央
    def setCenter(self):
        ws = self.winfo_screenwidth()  # 获取屏幕宽度
        hs = self.winfo_screenheight()  # 获取屏幕高度
        x = int((ws / 2) - (self.width / 2))
        y = int((hs / 2) - (self.height / 2))
        self.geometry('{}x{}+{}+{}'.format(self.width, self.height, x, y))

    # 移动窗口到屏幕坐标x,y
    def setPlace(self, x, y, w, h):
        self.geometry('{}x{}+{}+{}'.format(w, h, x, y))

    # 显示窗口ico图标
    def showIco(self, Ico):
        self.iconbitmap(Ico)

        # 是否禁止修改窗口大小

    def reSizable(self, x, y):
        self.resizable(x, y)  # 是否禁止修改窗口大小
# 表格
# Table表格类
class Table(tk.Frame):  # 继承Frame类的ttk.Treeview类
    def __init__(self, master=None, **kw):
        tk.Frame.__init__(self, master, **kw)
        self.root = master  # 定义内部变量root
        self.col = [1, 2]
        self.table = ttk.Treeview(self, show="headings")
        self.table_root = None
        self.table.pack(fill=tk.BOTH, expand=tk.YES, side=tk.LEFT)
        # x滚动条
        self.xscroll = tk.Scrollbar(self.table, orient=tk.HORIZONTAL, command=self.table.xview)
        self.table.configure(xscrollcommand=self.xscroll.set)
        self.xscroll.pack(side=tk.BOTTOM, fill=tk.X)
        # y滚动条
        self.yscrollbar = tk.Scrollbar(self.table, orient=tk.VERTICAL, command=self.table.yview)
        self.table.configure(yscrollcommand=self.yscrollbar.set)
        self.yscrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def load_df(self, df):
        grid_df = df
        grid_ss = grid_df.columns
        grid_colimns = []
        for s in grid_ss:
            grid_colimns.append(s)

        # Treeview组件，6列，显示表头，带垂直滚动条
        self.table.configure(columns=(grid_colimns), show="headings")

        for s in grid_colimns:
            # 设置每列宽度和对齐方式
            # tree.column(s, anchor='center')
            self.table.column(s, width=100, anchor='w')
            # 设置每列表头标题文本
            self.table.heading(s, text=s)

        # 插入演示数据
        for i in range(len(grid_df)):
            v = []
            for s in grid_ss:
                # v.append(grid_df.get_value(i, s))
                v.append(grid_df.at[i, s])
            self.table.insert('', i, values=v)

    def delete_table(self):
        items = self.table.get_children()
        [self.table.delete(item) for item in items]

    def brush(self, c1='#FAFAFA', c2='#eeeeff'):

        items = self.table.get_children()

        for i in range(len(items)):

            if i % 2 == 1:
                self.table.item(items[i], tags=('row1'))
            else:
                self.table.item(items[i], tags=('row2'))

        self.table.tag_configure('row1', background=c1)
        self.table.tag_configure('row2', background=c2)
# K线
class F9(tk.Frame):
    def __init__(self,root,num=1):
        tk.Frame.__init__(self, root)
        self.root = root
        self.num = num
        self.v = []
        self.init()
    def init(self):
        center = tk.Frame(self,bg='blue')
        center.pack(expand='yes', fill='both')
        self.v.append(center)
    def refash(self,base):
        import StockView as sv
        if not base['code']:
            messagebox.showerror('错误','请输入代码')
            return
        canvas = getattr(self,'canvas',None)
        if canvas:
            canvas.get_tk_widget().pack_forget()
        pre_base = getattr(self,'base',None)
        if pre_base and pre_base==base: # 相等使用当前数据
            data = self.data
        else:
            self.base = base
            data = LocalData.getInstance().data(base['code'],type=base['zs'])
            self.data = data
        self.canvas = sv.view3(self.root,data,'K线')
        self.root.update()
# F0面板
class F10(tk.Frame):
    def __init__(self, master=None, **kw):
        tk.Frame.__init__(self, master, **kw)
        # 把window划分为左右2个子容器,左为v1,右为v2
        v1 = tk.Frame(self, width=200)
        v1.pack(side=tk.LEFT, fill=tk.Y)
        v2 = tk.Frame(self)
        v2.pack(side=tk.RIGHT, fill=tk.BOTH, expand=1)
        f10 = ScrolledText(v2, wrap=tk.WORD, height=29)
        f10.pack(side=tk.RIGHT, fill=tk.BOTH, expand=1)
        self.f10 = f10
        tree = ttk.Treeview(v1)
        tree.pack(side=tk.TOP, fill=tk.BOTH, expand=1)
        self.tree = tree
        def treeviewClick(event):  # 单击
            for item in tree.selection():
                if 'F10' == item:
                    return
                index = int(tree.item(item, "values")[0])
                f10.delete(1.0, tk.END)  # 清空数据
                df = self.treedata[self.treedata['name'].eq(item)]
                txt = df['txt'].values[0]
                if txt is None:
                    base = toolsbar.get()
                    txt = TdxData.getInstance().get_company_info_content(base['code'], base['type'], df)
                    self.treedata.loc[index, 'txt'] = txt
                f10.insert(tk.END, txt)
        tree.bind('<ButtonRelease-1>', treeviewClick)
    def refash(self,base):
        self.clear()
        if not base['code']:
            messagebox.showerror('错误','请输入代码')
            return
        self.base = base
        tdx_node = self.tree.insert("", 0, "F10", text="F10", values=("-1"), open=True)
        treedata = TdxData.getInstance().get_company_info_category(self.base['code'],self.base['type'])
        for i, td in treedata.iterrows():
            self.tree.insert(tdx_node, i, td['name'], text=td['name'], values=(i))
        self.treedata = treedata
        self.tree.selection_set("F10")
    def clear(self):
        self.f10.delete(1.0,tk.END) # 清空文本框
        for item in self.tree.get_children():
            self.tree.delete(item)
# 回测
class F11(tk.PanedWindow):
    def __init__(self, master=None, cnf={}, **kw):
        tk.PanedWindow.__init__(self, master, cnf,**kw)
        f1 = tk.Frame(self, bg='blue', height=300)
        self.add(f1)
        self.paneconfig(f1, height=300)
        f2 = tk.LabelFrame(self, text='信息输出框', height=300)
        self.add(f2)
        myedit = EditorArea(f1)
        myedit.pack()
        log = ScrolledText(f2, wrap=tk.WORD, height=12)
        log.pack(fill=tk.BOTH)
        myedit.set_log(log)
        self.myedit = myedit
    def refash(self,base):
        self.myedit.refash(base)
        # 清空回测文本框，并初始化默认Test2.py
        self.myedit.textPad.delete(1.0, tk.END)
        with open(os.path.join(DEFAULT_DIR_PATH, 'Test2.py'), 'r', encoding='utf-8', errors='ignore') as f:
            self.myedit.textPad.insert(1.0, f.read())

# F12统计面板
class F12(tk.Frame):
    def __init__(self, master=None, **kw):
        tk.Frame.__init__(self, master, **kw)
        # 把window划分为左右2个子容器,左为v1,右为v2
        v1 = tk.Frame(self, width=200)
        v1.pack(side=tk.LEFT, fill=tk.Y)
        v2 = tk.Frame(self)
        v2.pack(side=tk.RIGHT, fill=tk.BOTH, expand=1)
        self.init_tools(v2)
        tb = Table(v2)  # 创建表格控件
        tb.pack(expand=1, fill=tk.BOTH)

        def onDBClick(event):
            if getattr(self,'test_name',None):
                item = tb.table.selection()[0]
                aa = tb.table.item(item, "values")
                popWindow = BaseWindow(stock,'%s-回测详情'%self.test_name)  # 建立新窗口
                # 加载订单数据
                stb = Table(popWindow)  # 创建表格控件
                stb.pack(expand=1, fill=tk.BOTH)
                df = LocalData.getInstance().test_order(self.test_name, aa[1]) # 展示默认
                stb.load_df(df)
                stb.brush()  # 用2种底色交替显示表格
                # stock.wait_window(popWindow)
        tb.table.bind("<Double-1>", onDBClick)

        tree = ttk.Treeview(v1)
        tree.pack(side=tk.TOP, fill=tk.BOTH, expand=1)
        test_node = tree.insert("", 0, "交易策略", text="交易策略", values=(-1), open=True)
        pool_node = tree.insert("", 1, "股票池", text="股票池", values=(-1),open=True)
        tree.insert(pool_node, 0, "自选股", text="自选股", values=(0))
        tree.insert(pool_node, 1, "月操作", text="月操作", values=(1))
        tree.insert(pool_node, 2, "日操作", text="日操作", values=(2))
        treedata = FoldData.test_files()
        for i, td in treedata.iterrows():
            tree.insert(test_node, i, td['name'], text=td['name'], values=(i))
        tree.selection_set("交易策略")
        def treeviewClick(event):  # 单击
            for item in tree.selection():
                index = int(tree.item(item, "values")[0])
                if index == -1:
                    break
                self.name = os.path.splitext(item)[0]
                self.search_data()
        tree.bind('<ButtonRelease-1>', treeviewClick)
        self.tb = tb
    def search_data(self):
        self.tb.delete_table()
        code = self.stock_code.get()
        name = self.stock_name.get()
        bk = self.stock_bk.get()
        if self.name == '自选股':
            self.table_data = LocalData.getInstance().self_stock(code=code,name=name,bk=bk)  # 自选股
        elif self.name == '月操作':
            config.put('test','TDX_CATEGORY','6')
            self.table_data = LocalData.getInstance().result_report(code=code,name=name,bk=bk)  # 当月可操作个股
        elif self.name == '日操作':
            config.put('test', 'TDX_CATEGORY', '9')
            self.table_data = LocalData.getInstance().result_report(code=code, name=name, bk=bk)  # 当日可操作个股
        else:
            self.test_name = self.name
            self.table_data = LocalData.getInstance().test_result(self.name, code=code,name=name,bk=bk)  # 回测文件名，代码
        self.tb.load_df(self.table_data)  # 自选股
        self.tb.brush()  # 用2种底色交替显示表格
    def export_data(self):
        self.table_data.to_csv(os.path.join(DEFAULT_DIR_PATH,'temp/%s.csv'%self.name), index=False)
        tk.messagebox.showinfo('提示','导出成功！')
    def clear_txt(self):
        self.stock_code.set('')
        self.stock_name.set('')
        self.stock_bk.set('')
    def init_tools(self,root):
        self.toolbar = tk.Frame(root, height=20)
        self.toolbarName = ('查询','重置','导出')
        self.toolbarCommand = (self.search_data,self.clear_txt,self.export_data)
        def addButton(name, command):
            for (toolname, toolcom) in zip(name, command):
                shortButton = tk.Button(self.toolbar, text=toolname, relief='groove', command=toolcom)
                shortButton.pack(side=tk.LEFT, padx=2, pady=5)
        self.t = []
        label = tk.Label(self.toolbar, text='代码:')
        self.t.append(label)
        self.stock_code = tk.StringVar(value='')
        text = tk.Entry(self.toolbar, width=12,textvariable=self.stock_code)
        self.t.append(text)
        label = tk.Label(self.toolbar, text='名称:')
        self.t.append(label)
        self.stock_name = tk.StringVar(value='')
        text = tk.Entry(self.toolbar, width=12,textvariable=self.stock_name)
        self.t.append(text)
        label = tk.Label(self.toolbar, text='板块:')
        self.t.append(label)
        self.stock_bk = tk.StringVar(value='')
        text = tk.Entry(self.toolbar, width=12,textvariable=self.stock_bk)
        self.t.append(text)
        for i in range(len(self.t)):
            self.t[i].pack(side=tk.LEFT, padx=2, pady=5)

        addButton(self.toolbarName, self.toolbarCommand)  # 调用添加按钮的函数
        self.toolbar.pack(side=tk.TOP, fill=tk.X)
    def refash(self,base):
        self.base = base
        self.stock_code.set(base['code'])
# 数据管理
class F13(tk.PanedWindow):
    def __init__(self, master=None, cnf={}, **kw):
        tk.PanedWindow.__init__(self, master, cnf,**kw)
        f1 = tk.Frame(self, bg='blue', height=400)
        self.add(f1)
        self.paneconfig(f1, height=400)
        self.init_tools(f1)
        log = ScrolledText(f1, wrap=tk.WORD, height=380)
        log.pack(fill=tk.BOTH)
        self.log = log
        self.p = subprocess.Popen('tail -F %s'%os.path.join(DEFAULT_DIR_PATH,'all.log'), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        threading.Thread(target=self.read_log, daemon=True).start()
        self.job_status = False
    def read_log(self):
        while True:
            try:
                line = self.p.stdout.readline().decode('utf-8')
                self.log.insert(tk.END, line)
                self.log.update()
                self.log.see(tk.END)
            except Exception as e:
                pass

    def update_codes(self):
        self.clear_log()
        threading.Thread(target=StockJob.getInstance().update_codes,daemon=True).start()
    def update_bks(self):
        self.clear_log()
        threading.Thread(target=StockJob.getInstance().update_bks,daemon=True).start()

    def update_gds(self):
        self.clear_log()
        threading.Thread(target=StockJob.getInstance().update_gds,daemon=True).start()

    def update_fhs(self):
        self.clear_log()
        threading.Thread(target=StockJob.getInstance().update_fhs, daemon=True).start()

    def update_test(self):
        self.clear_log()
        threading.Thread(target=StockJob.getInstance().test,args=(False,), daemon=True).start()
    def start_job(self):
        stockJob = StockJob.getInstance()
        if self.job_status:
            # 1.每年一月一号8:00，更新股票代码、更新板块
            stockJob.add_cron_job(stockJob.update_codes, month='1', day='1', hour='8', minute='0')
            # 2.每星期六20:00更新股东人数
            stockJob.add_cron_job(stockJob.update_gds, day_of_week='sat', hour='18', minute='0')
            # 3.每周六16:00以后更新分红数据
            stockJob.add_cron_job(stockJob.update_fhs, day_of_week='sat', hour='16', minute='0')
            # 4.每天20点更新股票池的月线预警值
            stockJob.add_cron_job(stockJob.test, hour='20', minute='0')
            # 5.每天9:30,到15:00，没5分钟 进行下载数据并回测
            stockJob.add_cron_job(stockJob.update_datas, hour='9-16', minute='*/5')
            # 6.每周1-5  9:00打开交易软件
            stockJob.add_cron_job(stockJob.open_tdx, hour='9', minute='18')
            # 6.每周1-7  15:00 关闭交易软件，并发送当天交易流水
            stockJob.add_cron_job(stockJob.close_tdx, hour='15', minute='0')
            stockJob.start()
        else:
            for job in stockJob.scheduler.get_jobs():
                job.remove()
            stockJob.stop()
        self.job_status = not self.job_status
    def init_tools(self,root):
        self.toolbar = tk.Frame(root, height=20)
        self.toolbarName = ('股票代码', '所属板块', '十大股东', '历年分红','历史回测','启动/停止')
        self.toolbarCommand = (
            self.update_codes, self.update_bks, self.update_gds, self.update_fhs,self.update_test,self.start_job)

        def addButton(name, command):
            for (toolname, toolcom) in zip(name, command):
                shortButton = tk.Button(self.toolbar, text=toolname, relief='groove', command=toolcom)
                shortButton.pack(side=tk.LEFT, padx=2, pady=5)

        addButton(self.toolbarName, self.toolbarCommand)  # 调用添加按钮的函数
        label = tk.Label(self.toolbar, anchor=tk.E, height=1, text='用于股票数据手动更新', relief=tk.FLAT, takefocus=False,
                         fg='red')
        label.pack(side=tk.LEFT, padx=2, pady=5)
        self.toolbar.pack(side=tk.TOP, fill=tk.X)
    def clear_log(self):
        self.log.delete(1.0,tk.END) # 清空文本框
    def refash(self,base):
        self.clear_log()
if __name__ =='__main__':
    stock = StockWindow(location=DEFAULT_WINDOW_LOCATION,title='量化交易系统(V1.0)')
    # 设置菜单
    menus = ['用户功能', '系统设置', '帮助']
    items = [[],
             [],
             ['关于软件', '退出']]
    def popwindow(*args,**kwargs):
        menu = kwargs['var'].get()
        if menu == '关于软件':
            popWindow = BaseWindow(stock,'关于软件',w=300,h=200)  # 设置窗口标题
            image = Image.open(os.path.join(basedir, 'ico/about.ico'))
            tk_image = ImageTk.PhotoImage(image)
            tk.Label(popWindow, image=tk_image).pack()
            popWindow.wm_resizable(False, False)  # 允许调整窗口大小
            stock.wait_window(popWindow)
        elif menu=='退出':
            if tk.messagebox.askyesno("提示", "确定直接退出吗？"):
                stock.quit()
    menu = MenuBar(stock, menus, items,popwindow)
    # # 设置工具栏
    toolsbar = ToolsBar(stock, 4)  # 创建工具栏
    toolsbar.pack(side=tk.TOP, fill=tk.X)  # 把工具栏放到窗口顶部
    png1 = ImageTk.PhotoImage(Image.open(os.path.join(basedir, 'ico/f10.ico')))
    png2 = ImageTk.PhotoImage(Image.open(os.path.join(basedir,'ico/f9.ico')))
    png3 = ImageTk.PhotoImage(Image.open(os.path.join(basedir,'ico/f11.ico')))
    png4 = ImageTk.PhotoImage(Image.open(os.path.join(basedir,'ico/f12.ico')))
    # Tab页
    tab_index = []
    tabControl = ttk.Notebook(stock)  # 创建Notebook
    tab1 = tk.Frame(tabControl)  # 增加新选项卡tab1
    tabControl.add(tab1, text='综合信息')  # 把新选项卡增加到Notebook
    tab2 = tk.Frame(tabControl)  # 增加新选项卡tab3
    tabControl.add(tab2, text='技术分析')  # 把新选项卡增加到Notebook
    tab3 = tk.Frame(tabControl)
    tabControl.add(tab3, text='我的回测')
    tab4 = tk.Frame(tabControl)
    tabControl.add(tab4, text='交易统计')
    tab5 = tk.Frame(tabControl)
    tabControl.add(tab5, text='数据管理')

    tabControl.pack(expand=1, fill="both")  # 使用pack方法显示
    tabControl.select(tab3)  # 选择tab1
    # F10
    f10 = F10(tab1)
    f10.pack(expand=1, fill=tk.BOTH)
    tab_index.append(f10)
    # k线
    f9 = F9(tab2)
    tab_index.append(f9)
    # F11 自定义回测
    f11 = F11(tab3, orient=tk.VERTICAL, showhandle=True, sashrelief=tk.SUNKEN, sashwidth=1)  # 默认是左右分布的,现改为上下布局
    f11.pack(fill=tk.BOTH, expand=1)
    tab_index.append(f11)
    f12 = F12(tab4)
    f12.pack(expand=1, fill=tk.BOTH)
    tab_index.append(f12)
    f13 = F13(tab5, orient=tk.VERTICAL, showhandle=True, sashrelief=tk.SUNKEN, sashwidth=1)
    f13.pack(fill=tk.BOTH, expand=1)
    tab_index.append(f13)


    # 绑定相关事件
    def tab_change(*args):
        index = tabControl.index(tabControl.select())
        tab_index[index].refash(toolsbar.get())
    tabControl.bind('<<NotebookTabChanged>>', tab_change)
    def showTab(index=None):
        if index is None:
            index = tabControl.index(tabControl.select())
        tabControl.select(index)
        tab_index[index].refash(toolsbar.get())
    # 改变工具栏的图标
    toolsbar.config(0, image=png1,command=lambda: showTab(0))
    toolsbar.config(1, image=png2,command=lambda: showTab(1))
    toolsbar.config(2, image=png3,command=lambda: showTab(2))
    toolsbar.config(3, image=png4,command=lambda: showTab(3))
    toolsbar.config(7, command=showTab)
    # 建立状态栏
    status = StatusBar(stock)  # 建立状态栏
    status.pack(side=tk.BOTTOM, fill=tk.X)  # 把状态栏放到窗口底部
    status.clear()
    status.text(0, '状态栏')  # 在状态栏1输出信息
    status.text(1, '不断学习，不断超越自我！')  # 在状态栏2输出信息
    status.text(2, '实现自己的翻倍目标！')
    status.text(3, '版权所有')
    status.text(4, '作者:小风')
    status.config(1, color='red')  # 改变状态栏2信息颜色
    status.config(3, color='green')  # 改变状态栏2信息颜色
    stock.show()
