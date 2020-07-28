#!/usr/bin/python3
import smtplib
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication 
from StockConfig import *

class MailUtil(object):
	@classmethod
	def __init__(self,args=None):
		self.args = args
	def sendEmail(self,receivers,content,title):
		message = MIMEText(content, 'html', 'utf-8') # 内容, 格式, 编码
		message['From'] = "{}".format(MAIL_USER)
		message['To'] = ",".join(receivers)
		message['Subject'] = title
		threading.Thread(target=self.__send,args=(receivers,message,) ,daemon=True).start()

	def sendEmailAttach(self,receivers,content,title):
		message = MIMEMultipart()
		message['Subject'] = title
		if self.args and self.args['fileName']:
			# 添加附件
			fileName = self.args['fileName']
			sqlApart = MIMEApplication(open(fileName, 'rb').read())
			sqlApart.add_header('Content-Disposition', 'attachment', filename=fileName)
			message.attach(sqlApart)
		textApart = MIMEText(content)
		message.attach(textApart)
        # 发送邮件
		threading.Thread(target=self.__send, args=(receivers, message,), daemon=True).start()
		# self.__send(receivers,message)
        
	def __send(self,receivers,message):
		smtpObj = None
		try:
			smtpObj = smtplib.SMTP_SSL(MAIL_HOST, 465) # 启用SSL发信, 端口一般是465
			smtpObj.login(MAIL_USER, MAIL_PASS) # 登录验证
			smtpObj.sendmail(MAIL_USER, receivers, message.as_string()) # 发送
			print("mail has been send successfully.")
		except smtplib.SMTPException as e:
			print('mail send faild,error:%s'%e)
		finally:
			if smtpObj:
				smtpObj.quit()
	@classmethod
	def getInstance(cls):
		if not hasattr(MailUtil, "_instance"):
			MailUtil._instance = MailUtil()
		return MailUtil._instance
if __name__ == '__main__':
	mailUtil = MailUtil({'fileName':'2020.sql'})
	mailUtil.sendEmail(['ls_yuqinghai@163.com'],'请根据附件更新节假日','运维工作-更新节假日')
