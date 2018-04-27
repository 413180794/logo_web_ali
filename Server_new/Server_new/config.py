#coding:utf-8
DIALECT='mysql'
DRIVER='mysqlconnector'
USERNAME='root'
PASSWORD='123456'
HOST='127.0.0.1'
PORT='3306'
DATABASE='new_logo_result'
SQLALCHEMY_TRACK_MODIFICATIONS = True
#这个连接字符串变量名是固定的具体 参考 flask_sqlalchemy  文档 sqlalchemy会自动找到flask配置中的 这个变量
SQLALCHEMY_DATABASE_URI='{}+{}://{}:{}@{}:{}/{}?charset=utf8'.format(DIALECT,DRIVER,USERNAME,PASSWORD,HOST,PORT,DATABASE)
SQLALCHEMY_ECHO=False
