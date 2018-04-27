# -*-coding:utf-8 -*-
from flask import Flask
import flask_sqlalchemy
import config
from flask_sqlalchemy import SQLAlchemy
import flask_restful

app = Flask(__name__)
app.config.from_object(config)
api = flask_restful.Api(app)
db = SQLAlchemy(app)

from datetime import datetime


class DeviceInfo(db.Model):
    __tablename__ = 'DeviceInfo'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    deviceFixId = db.Column(db.String(64), nullable=False, unique=True,primary_key=True)
    regionProvince = db.Column(db.String(64), nullable=False)
    regionCity = db.Column(db.String(64), nullable=False)
    regionArea = db.Column(db.String(64), nullable=False)
    status = db.Column(db.Integer, nullable=False)  # 判断是否在线

    resultInfo = db.relationship('ResultInfo', backref='deviceinfo', lazy='dynamic')
    pictureSize = db.relationship('PictureSize', backref='deviceinfo', lazy='dynamic')
    fileInfo = db.relationship('FileInfo', backref='deviceinfo', lazy='dynamic')

    def __init__(self, deviceFIxId, regionProvince, regionCity, regionArea, status):
        self.deviceFixId = deviceFIxId
        self.regionProvince = regionProvince
        self.regionCity = regionCity
        self.regionArea = regionArea
        self.status = status




class FileInfo(db.Model):
    __tablename__ = 'FileInfo'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    deviceFixId = db.Column(db.String(64), db.ForeignKey('DeviceInfo.deviceFixId'), nullable=False)
    fileAbsolutePath = db.Column(db.String(64), nullable=False)
    fileSize = db.Column(db.String(64), nullable=False)
    lastUpdatedDate = db.Column(db.DateTime(64), nullable=False)

    def __init__(self, deviceFixId, fileAbsolutePath, fileSize, lastUpdatedDate):
        self.deviceFixId = deviceFixId
        self.fileAbsolutePath = fileAbsolutePath
        self.fileSize = fileSize
        self.lastUpdatedDate = lastUpdatedDate

    def save(self):
        db.session.add(self)
        db.session.commit()
        return self

    def update(self):
        db.session.commit()
        return self


class ResultInfo(db.Model):
    __tablename__ = 'ResultInfo'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    deviceFixId = db.Column(db.String(64), db.ForeignKey('DeviceInfo.deviceFixId'), nullable=False)  # 外键
    kind = db.Column(db.String(64), nullable=False)
    result = db.Column(db.String(64), nullable=False)
    startTime = db.Column(db.DateTime(64), nullable=False, index=True)
    usedTime = db.Column(db.Integer, nullable=False)

    def __init__(self, deviceFixId, kind, result, startTime, usedTime):
        self.deviceFixId = deviceFixId
        self.kind = kind
        self.result = result
        self.startTime = startTime
        self.usedTime = usedTime

    def save(self):
        db.session.add(self)
        db.session.commit()
        return self

    def update(self):
        db.session.commit()
        return self

    @staticmethod
    def changeName(dateTime):
        ResultInfo.__table__.name = 'ResultInfo_' +dateTime.replace("-",'_')
        ResultInfo.__tablename__ = 'ResultInfo_' +dateTime.replace("-",'_') # 数据库中不支持'-'
        db.create_all()



class PictureSize(db.Model):
    __tablename__ = 'PictureSize'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    deviceFixId = db.Column(db.String(64), db.ForeignKey('DeviceInfo.deviceFixId'), nullable=False)
    channel = db.Column(db.String(64), nullable=False)
    kind = db.Column(db.String(64), nullable=False)
    leftTopX = db.Column(db.Integer, nullable=False)
    leftTopY = db.Column(db.Integer, nullable=False)
    rightBottomX = db.Column(db.Integer, nullable=False)
    rightBottomY = db.Column(db.Integer, nullable=False)

    def __init__(self, deviceFixId, channel, kind, leftTopX, leftTopY, rightBottomX, rightBottomY):
        self.deviceFixId = deviceFixId
        self.channel = channel
        self.kind = kind
        self.leftTopX = leftTopX
        self.leftTopY = leftTopY
        self.rightBottomX = rightBottomX
        self.rightBottomY = rightBottomY

    def save(self):
        db.session.add(self)
        db.session.commit()
        return self

    def update(self):
        db.session.commit()
        return self


class ErrorInfo(db.Model):
    __tablename__ = 'ErrorInfo'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    deviceFixId = db.Column(db.String(64), db.ForeignKey("DeviceInfo.deviceFixId"), nullable=False)
    errorName = db.Column(db.String(64), nullable=False)
    fileName = db.Column(db.String(64), nullable=False)
    dateTime = db.Column(db.DateTime(64), nullable=False)

    def __init__(self, deviceFixId, errorName, fileName, dateTime):
        self.deviceFixId = deviceFixId
        self.errorName = errorName
        self.fileName = fileName
        self.dateTime = dateTime

    def save(self):
        db.session.add(self)
        db.session.commit()
        return self

    def update(self):
        db.session.commit()
        return self


if __name__ == '__main__':
    db.create_all()
    m = DeviceInfo('1231223_HDMI','北京','北京','朝阳区','1')
    x = ResultInfo('1231223_HDMI','HDMI','北京卫视','2018-2-23 20:23:23','1234')
    y = PictureSize('1231223_HDMI','北京卫视','HDMI','12','123','241','231')
    z = FileInfo('1231223_HDMI','asdfa3sdf','asdfafsd','asdfasdf')
    x.changeName('2018-02-23')
    # db.session.add(m)
    db.session.add(x)
    # db.session.add(y)
    # db.session.add(z)
    db.session.commit()

