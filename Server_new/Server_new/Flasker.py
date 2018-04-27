# -*-coding:utf-8 -*-
from datetime import datetime
import hashlib
import socket
import sys
import threading
import logging
import os
import cv2
import numpy as np
import pypinyin
from flask import Flask, request, Response, send_from_directory, make_response, jsonify, redirect, abort
from flask_cors import CORS

import pushToSql
import pickle
import sys
from time import sleep
import time
from PyQt5.QtCore import QThread, QReadWriteLock, pyqtSignal, QByteArray, QDataStream, QFile, QIODevice, QObject, \
    QCoreApplication
from PyQt5.QtNetwork import QTcpSocket, QHostAddress, QTcpServer, QAbstractSocket
from PyQt5.QtWidgets import QWidget, QApplication, QPushButton
from resultInfo import resultInfo
from deviceInfo import deviceInfo
import flask_restful
import config
from pushToSql import api, app as app1, db
from pushToSql import DeviceInfo, ResultInfo, FileInfo, PictureSize,ErrorInfo
from dataStruct import dataStuct

PORT = 31200
SIZEOF_UINT16 = 2
SIZEOF_UINT64 = 8

sockeIdToSocketDict = {}  # 保存 socketId 与 socket 的字典
fixIdToSocketIdDict = {}  # 保存设备id与socketID的字典
threadDict = {}


def sendBackOrder(deviceFixId, order):
    '''
    :param deviceFixId:
    :param order:
    UpdateInfo
    UpdateModelFile,cetv_tf
    ---先不管下面的---
    RollbackInfo
    RollbackModelFile,cetv_tf
    :return:
    '''
    print('询问客户端是否准备好接受文件')
    try:
        socketID = fixIdToSocketIdDict[deviceFixId]
        socket = sockeIdToSocketDict[socketID]
        thread = threadDict[socketID]
        print(socketID)
        print(socket)
        thread.sendBackOrder(socket, order)
    except Exception as e:
        print("该设备不在线，该设备名称不存在")
        return "该设备不在线，该设备名称不存在"


def sendBackImageStatus(deviceFixId, order):
    '''
    :param deviceFixId:
    :param order:
    UpdateInfo
    UpdateModelFile,cetv_tf
    ---先不管下面的---
    RollbackInfo
    RollbackModelFile,cetv_tf
    :return:
    '''
    print('询问客户端是否准备好接受文件')
    try:
        socketID = fixIdToSocketIdDict[deviceFixId]
        socket = sockeIdToSocketDict[socketID]
        thread = threadDict[socketID]
        print(socketID)
        thread.sendBackImageStatus(socket, order)
    except Exception as e:
        print("该设备不在线，该设备名称不存在")
        return "该设备不在线，该设备名称不存在"


class AreaData(flask_restful.Resource):
    def get(self):
        areaData = dataStuct().getAreaData()
        region = eval(request.args.get('data'))
        selectDevice = None
        if len(region) == 1:
            print(region[0])
            selectDevice = DeviceInfo.query.filter_by(regionProvince=region[0]).all()
        elif len(region) == 2:
            selectDevice = DeviceInfo.query.filter_by(regionProvince=region[0], regionCity=region[1]).all()
        elif len(region) == 3:
            selectDevice = DeviceInfo.query.filter_by(regionProvince=region[0], regionCity=region[1],
                                                      regionArea=region[2]).all()
        if selectDevice:
            for x in selectDevice:
                print(x)
                areaData.get('data').append({"fixedID": x.deviceFixId, "state": x.status})
        return areaData


class DetailData(flask_restful.Resource):
    def get(self):

        resultData = dataStuct().getResultData()
        nameAndDate = eval(request.args.get('data'))
        deviceName = nameAndDate.get('name')  # xxx_HDMI
        selectDate = nameAndDate.get('date')  # xxxx-xx-xx
        print(selectDate)
        ResultInfo.changeName(selectDate)
        result = ResultInfo.query.filter(ResultInfo.deviceFixId == deviceName).order_by(ResultInfo.startTime.desc()).all()
        print(ResultInfo.__table__.name)
        print('result', result)
        print(type(result))
        if result:
            
            count = 1
            for x in result:
                resultData.get('data').append(
                    {
                        "id": count,
                        "kind": x.kind,
                        "result": x.result,
                        "date": x.startTime.strftime("%Y-%m-%d %H:%M:%S"),
                        "usedTime": str(int(x.usedTime) * 1.0 / 1000)
                    }
                )
                count+=1
        return resultData


class configData(flask_restful.Resource):
    def get(self):
        deviceFixIds = eval(request.args.get('data'))
        configInfo = dataStuct().getConfigInfo()
        if deviceFixIds:
            deviceFixId = deviceFixIds[0]
            fileInfo = FileInfo.query.filter_by(deviceFixId=deviceFixId)
            pictureInfo = PictureSize.query.filter_by(deviceFixId=deviceFixId)
        else:
            return configInfo

        if fileInfo:
            for x in fileInfo:
                configInfo.get('filesList').append(x.fileAbsolutePath)
        if pictureInfo:
            havePustList = []
            for x in pictureInfo:
                channelName = x.channel
                kind = x.kind
                leftTopX = x.leftTopX
                leftTopY = x.leftTopY
                rightBottomX = x.rightBottomX
                rightBottomY = x.rightBottomY
                if channelName in havePustList:
                    channelIndex = havePustList.index(channelName)
                    # print(channelIndex)
                    configInfo['channelsList'][channelIndex][kind] = {
                        "lt": [leftTopX, leftTopY],
                        "rb": [rightBottomX, rightBottomY]
                    }
                else:
                    configInfo["channelsList"].append(
                        {
                            "name": channelName,
                            kind:
                                {
                                    "lt": [leftTopX, leftTopY],
                                    "rb": [rightBottomX, rightBottomY]
                                }
                        }
                    )
                    havePustList.append(channelName)
        return configInfo


class resetConfigInfo(flask_restful.Resource):
    def post(self):
        configInfo = eval(str(request.get_data(), encoding='utf-8'))
        for deviceFixId in configInfo.get('deviceList'):
            for channel in configInfo.get('channelsList'):
                try:
                    kind = deviceFixId.split('_')[1]
                    print(kind)
                    leftTopX1 = channel[kind]['lt'][0]
                    leftTopY1 = channel[kind]['lt'][1]
                    rightBottomX1 = channel[kind]['rb'][0]
                    rightBottomY1 = channel[kind]['rb'][1]
                    pictureSize = PictureSize.query.filter_by(deviceFixId=deviceFixId, channel=channel.get('name'),
                                                              kind=kind).first()
                    print(pictureSize.leftTopX, pictureSize.leftTopY, pictureSize.rightBottomX,
                          pictureSize.rightBottomY)
                    if pictureSize:
                        pictureSize.leftTopX = leftTopX1
                        pictureSize.leftTopY = leftTopY1
                        pictureSize.rightBottomX = rightBottomX1
                        pictureSize.rightBottomY = rightBottomY1

                    pictureSize.update()
                except Exception as e:
                    print(e)
                    print("设备名称格式不正确")

        for deviceFixId in configInfo.get('deviceList'):
            print(deviceFixId)
            sendBackOrder(deviceFixId, "UpdateInfo," + str(deviceFixId).split("_")[1])
            if configInfo.get('filesList'):
                for file in configInfo.get('filesList'):
                    sendBackOrder(deviceFixId, 'UpdateModelFile,' + file)


class ReturnDeviceInfo(flask_restful.Resource):
    def get(self, model_type):
        deviceInfo = dataStuct().getDeviceInfo()
        deviceFixId = request.args.get("deviceFixId")
        selectDeviceInfo = DeviceInfo.query.filter_by(deviceFixId=deviceFixId).first_or_404()

        deviceInfo.update(
            deviceFixId=deviceFixId,
            ip=self.get_host_ip(),
            kind=model_type,
            regionProvince=selectDeviceInfo.regionProvince,
            regionCity=selectDeviceInfo.regionCity,
            regionArea=selectDeviceInfo.regionArea
        )
        for fileInfo in selectDeviceInfo.fileInfo:
            deviceInfo.get('fileInfo').append(
                {
                    "fileAbsolutePath": fileInfo.fileAbsolutePath,
                    "fileSize": fileInfo.fileSize,
                    "lastUpdatedDate": datetime.strftime(fileInfo.lastUpdatedDate, '%Y-%m-%d %H:%M:%S')
                }
            )
        for pictureSize in selectDeviceInfo.pictureSize:
            if pictureSize.kind == model_type:
                deviceInfo.get('pictureSize')[pictureSize.channel] = [
                    pictureSize.leftTopX,
                    pictureSize.leftTopY,
                    pictureSize.rightBottomX,
                    pictureSize.rightBottomY
                ]
        return deviceInfo

    def get_host_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
        finally:
            s.close()
        return ip


class DownloadFile(flask_restful.Resource):
    def get(self, kindname, filename):
        deviceFixId = request.args.get("deviceFixId")
        deviceProvince = pypinyin.slug(DeviceInfo.query.filter_by(deviceFixId=deviceFixId).first().regionProvince,
                                       separator="")
        directory = os.getcwd()
        response = make_response(send_from_directory(
            os.path.join(directory, "download", deviceProvince, kindname + "_" + deviceFixId.split("_")[1]), filename))
        response.headers['md5'] = hashlib.md5(
            open(os.path.join(directory, "download", deviceProvince, kindname + "_" + deviceFixId.split("_")[1],
                              filename),
                 'rb').read()).hexdigest()
        return response


class SendMapInfo(flask_restful.Resource):
    def get(self):
        mapInfo = dataStuct().getMapInfo()
        mapName = eval(request.args.get('data'))
        print(mapName)
        for name in mapName:
            mapInfo.append({
                'name': name,
                'value': len(DeviceInfo.query.filter_by(regionProvince=name).all())
            })
        return mapInfo


class ReceiveOffLineResult(flask_restful.Resource):
    def post(self):
        resultInfoAll = request.get_json()
        if resultInfoAll:
            oldResult = ""
            for resultInfo in resultInfoAll:
                if oldResult != resultInfo['result']:
                    x = ResultInfo(
                        resultInfo.get('deviceFixId'),
                        resultInfo.get('kind'),
                        resultInfo.get('result'),
                        resultInfo.get('startTime'),
                        resultInfo.get('usedTime')
                    )
                    db.session.add(x)
        db.session.commit()


class ScreenShotStatus(flask_restful.Resource):
    def get(self):
        data = eval(request.args.get('data'))
        deviceList = data.get('deviceList')
        status = data.get('status')
        if deviceList:
            for deviceFixId in deviceList:
                sendBackImageStatus(deviceFixId, status)


class ReceiveImage(flask_restful.Resource):
    def post(self, deviceFixId, result):
        image = pickle.loads(request.files['img'].read())
        if not os.path.exists(os.path.join("picture", deviceFixId, result)):
            os.makedirs(os.path.join("picture", deviceFixId, result));
        count = 0
        while (os.path.exists(os.path.join("picture", deviceFixId, result, "{}.jpg".format(count)))):
            count += 1
        print(count)
        print(os.path.join("picture", deviceFixId, result, "{}.jpg".format(count)))
        # with open(os.path.join("picture",deviceFixId,result,"{}.jpg".format(count)),'wb') as f:
        # f.write(file)
        cv2.imwrite(os.path.join("picture", deviceFixId, result, "{}.jpg".format(count)), image)


api.add_resource(ReceiveImage, '/send_image/<deviceFixId>/<result>')
api.add_resource(ScreenShotStatus, '/exampleData/screenShotStatus')
api.add_resource(ReceiveOffLineResult, '/send_offline_result')
api.add_resource(AreaData, '/exampleData/areaData')
api.add_resource(DetailData, '/exampleData/detailData')
api.add_resource(configData, '/exampleData/configData')
api.add_resource(resetConfigInfo, '/exampleData/sendConfigData')
api.add_resource(ReturnDeviceInfo, '/download_deviceInfo/<model_type>')
api.add_resource(DownloadFile, "/download_file/<kindname>/<filename>")
api.add_resource(SendMapInfo, '/exampleData/mapData')


class Thread(QThread, QWidget):  # 这个线程为自动采集所用的。运行这个线程就会启动tcp 允许别人连上
    lock = QReadWriteLock()
    # 该线程内部定义的信号，携带了三个字 用于解决数据库问题
    pushDeviceInfoSignal = pyqtSignal(str, str, str, str)
    popDeviceSignal = pyqtSignal(str)
    pushPictureSizeSignal = pyqtSignal(str, str, str)
    pushFileInfoSignal = pyqtSignal(str, str)
    pushResultInfoSignal = pyqtSignal(str, str, str, str, int)
    sendFileSignal = pyqtSignal(str)
    pushDeviceSignal = pyqtSignal(str)
    pushErrorSignal = pyqtSignal(str,str,str,str)

    def __init__(self, socketId, parent):
        super(Thread, self).__init__(parent)
        self.myParent = parent
        self.socketId = socketId  # socketID 可能是为socket编号
        self.hdmi_old_result = ""  # 为自动识别提供的 变量，可防止重复数据不停地输出
        self.av_old_result = ""  # 不共享变量
        self.pushDeviceInfoSignal.connect(self.pushDeviceInfo)
        self.pushResultInfoSignal.connect(self.pushResultInfo)
        self.pushPictureSizeSignal.connect(self.pushPictureSize)
        self.pushFileInfoSignal.connect(self.pushFileInfo)
        self.popDeviceSignal.connect(self.popDevice)
        self.pushDeviceSignal.connect(self.pushDevice)
        self.pushErrorSignal.connect(self.pushError)

    
    def pushError(self,deviceFixId,errorName,fileName,dateTime):
        errorInfo = ErrorInfo(deviceFixId,errorName,fileName,dateTime)
        db.session.add(errorInfo)
        db.session.commit()

    def pushDeviceInfo(self, deviceFixId, regionProvince, regionCity, regionArea):
        deviceInfo = DeviceInfo.query.filter_by(deviceFixId=deviceFixId).first()
        if not deviceInfo:
            newDevice = DeviceInfo(
                deviceFIxId=deviceFixId,
                regionProvince=regionProvince,
                regionCity=regionCity,
                regionArea=regionArea,
                status=1
            )
            db.session.add(newDevice)
        else:
            deviceInfo.status = 1
        db.session.commit()

    def pushResultInfo(self, deviceFixId, kind, result, startTime,
                       usedTime):  # (self, deviceFixId, kind, result, startTime, usedTime
        print("-----收到结果-------")
        print(startTime.split(' ')[0].replace("-","_"))
        print('usedTime',usedTime)
        if int(usedTime) > 20000:
            usedTime = str(int(int(usedTime)/2))
        #resultInfo = ResultInfo(deviceFixId, kind, result, startTime, usedTime)
        ResultInfo.changeName(startTime.split(' ')[0].replace("-", "_"))
        print(deviceFixId,kind,result,startTime,usedTime)
        print("-----收到结果-------")       

        db.session.execute('Insert into {} (`deviceFixId`, `kind`, `result`, `startTime`, usedTime) VALUES ("{}","{}","{}","{}",{})'.format('ResultInfo_' + startTime.split(' ')[0].replace("-", "_"), deviceFixId, kind, result,startTime, usedTime))
        db.session.commit()

    def pushPictureSize(self, pictureSize, deviceFixId, kind):  # 将图片信息转入数据库
        pictureSizeDict = eval(pictureSize)
        # print(type(pictureSizeDict), pictureSizeDict)
        # print(pictureSizeDict)
        for key, value in pictureSizeDict.items():
            pictureInfo = PictureSize.query.filter_by(deviceFixId=deviceFixId, channel=key, kind=kind).first()
            if pictureInfo:  # 如果不是空，则需要更新
                pictureInfo.leftTopX = value[0]
                pictureInfo.leftTopY = value[1]
                pictureInfo.rightBottomX = value[2]
                pictureInfo.rightBottomY = value[3]

            # ---------# 此处可能有bug
            else:  # 如果是空
                x = PictureSize(deviceFixId, key, kind, value[0], value[1], value[2], value[3])
                db.session.add(x)
        db.session.commit()

    def pushFileInfo(self, fileInfo, deviceFixId):
        fileInfo = eval(fileInfo)
        for fileInfoItem in fileInfo:
            fileAbsolutePath = fileInfoItem['fileAbsolutePath']
            fileSize = fileInfoItem['fileSize']
            lastUpdatedDate = fileInfoItem['lastUpdatedDate']
            tempFileInfo = FileInfo.query.filter_by(deviceFixId=deviceFixId, fileAbsolutePath=fileAbsolutePath).first()
            if tempFileInfo:  # 非空
                tempFileInfo.fileSize = fileSize
                tempFileInfo.lastUpdatedDate = lastUpdatedDate

            else:
                x = FileInfo(deviceFixId, fileAbsolutePath, fileSize, lastUpdatedDate)
                db.session.add(x)

        db.session.commit()

    def popDevice(self, deviceId):
        x = DeviceInfo.query.filter_by(deviceFixId=deviceId).first()
        if x:
            x.status = 0
        db.session.add(x)
        db.session.commit()
    
    def pushDevice(self,deviceId):
        x = DeviceInfo.query.filter_by(deviceFixId=deviceId).first()
        if x and x.status==0:
            x.status = 1
        db.session.add(x)
        db.session.commit()

    def run(self):
        print('-----------------------')
        socket = QTcpSocket()
        fixID = "None"
        count = 0

        if not socket.setSocketDescriptor(self.socketId):  # 可能是分配的东西，具体作用不知道
            # self.emit(SIGNAL("error(int)"), socket.error())
            self.error.connect(socket.error)

            return

        while socket.state() == QAbstractSocket.ConnectedState:
            nextBlockSize = 0
            stream = QDataStream(socket)
            stream.setVersion(QDataStream.Qt_4_0)
            sockeIdToSocketDict[self.socketId] = socket
            # print(sockeIdToSocketDict)  # 将所有连接上来的socket保存起来
            # print(fixIdToSocketIdDict)
            aim_ip = socket.peerAddress().toString()  # 获得连上来的IP地址
            # print(aim_ip)

            if (socket.waitForReadyRead(60000) and
                    socket.bytesAvailable() >= SIZEOF_UINT16):
                print('wait')
                nextBlockSize = stream.readUInt16()

            else:
                print('错误')  # 客户端主动断开时，去掉字典中的对应，在这里做一部分操作。
                # 客户端主动断开的时候，要将其从self.myParent.sockeIdToSocketDict   self.myParent.fixIdToSocketIdDict 中删掉
                try:
                    sockeIdToSocketDict.pop(self.socketId)  # 客户端主动断开的时候删掉。
                    fixIdToSocketIdDict.pop(fixID)
                    threadDict.pop(self.socketId)
                except:
                    print("不存在该设备")
                self.popDeviceSignal.emit(fixID)
                return
            if socket.bytesAvailable() < nextBlockSize:
                print("错误2")
                if (not socket.waitForReadyRead(60000) or
                        socket.bytesAvailable() < nextBlockSize):
                    print("错误3")
                    return

            # 这段数据流上 第一个是state 根据state判断接下来的状态，
            # 发送成功的状态，发送来 success    日期  信号类型 识别结果 识别开始时间 识别时间

            state = stream.readQString()  # 读状态

            print('#61    ' + state)
            if state == 'successResult':  # 如果状态是success，说明下一个发来的是识别的结果
                resultBytes = stream.readBytes()
                try:
                    Thread.lock.lockForRead()
                finally:
                    Thread.lock.unlock()
                resultObject = pickle.loads(resultBytes)
                # print(fixID)
                # print(resultObject.dateNow)
                # print(resultObject.kind)
                # print(resultObject.result)
                # print(resultObject.startTime)
                # print(resultObject.usedTime)

                if resultObject.kind == "HDMI" and self.hdmi_old_result != resultObject.result:

                    # 自动采集的不需要时间，他需要 日期 时间识别结果 发走的信息只有 类型 识别结果 ip地址 全是strhandleSql.pushResultInfo('123425','HDMI','北京卫视','2018-12-23 12:23:21',12)
                    self.pushResultInfoSignal.emit(fixID, resultObject.kind, resultObject.result,
                                                   resultObject.startTime,
                                                   int(
                                                       resultObject.usedTime))  # 发射信号，携带了信号类型，识别结果，aim_ip（当做区分控件的id）结果从这里发出去
                    self.hdmi_old_result = resultObject.result

                elif resultObject.kind == 'AV' and self.av_old_result != resultObject.result:
                    self.pushResultInfoSignal.emit(fixID, resultObject.kind, resultObject.result,
                                                   resultObject.startTime,
                                                   int(
                                                       resultObject.usedTime))  # 发射信号，携带了信号类型，识别结果，aim_ip(当做区分空间的id） getMessgetMessageAllTcpageAllTcp
                    self.av_old_result = resultObject.result
            elif state == 'deviceInfo':  # 收到deviceInfo对象
                deviceInfoByte = stream.readBytes()
                try:
                    Thread.lock.lockForRead()
                finally:
                    Thread.lock.unlock()
                # pictureSizeByte = stream.readBytes()
                deviceInfo = pickle.loads(deviceInfoByte)
                # pictureSize = pickle.loads(pictureSizeByte)

                fixID = deviceInfo['deviceFixId']
                fixIdToSocketIdDict[fixID] = self.socketId
                print(deviceInfo['pictureSize'])
                self.pushDeviceInfoSignal.emit(deviceInfo['deviceFixId'], deviceInfo['regionProvince'],
                                               deviceInfo['regionCity'],
                                               deviceInfo['regionArea'])
                print("___________________________")
                print(deviceInfo['fileInfo'])
                self.pushPictureSizeSignal.emit(str(deviceInfo['pictureSize']), deviceInfo['deviceFixId'],
                                                deviceInfo['kind'])
                self.pushFileInfoSignal.emit(str(deviceInfo['fileInfo']), deviceInfo['deviceFixId'])



            elif state == 'sendHeartBeat':  # 准备接受 文件
                print("heartBeat")
            elif state == 'sendError':
                errorName = stream.readQString()
                fileName = stream.readQString()
                now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
                self.pushErrorSignal.emit(deviceInfo['deviceFixId'],errorName,fileName,now)


    def sendBackOrder(self, socket, order):  # 回传一条命令
        reply = QByteArray()
        stream = QDataStream(reply, QIODevice.WriteOnly)
        stream.setVersion(QDataStream.Qt_4_0)
        stream.writeUInt16(0)
        stream.writeQString("ORDER")  # 回传一条命令,命令自己定义。
        stream.writeQString(order)
        stream.device().seek(0)
        stream.writeUInt16(reply.size() - SIZEOF_UINT16)
        socket.write(reply)
        socket.waitForBytesWritten()

    def sendBackImageStatus(self, socket, order):  # 回传一条命令
        reply = QByteArray()
        stream = QDataStream(reply, QIODevice.WriteOnly)
        stream.setVersion(QDataStream.Qt_4_0)
        stream.writeUInt16(0)
        stream.writeQString("changeImageStatus")  # 回传一条命令,命令自己定义。
        stream.writeQString(order)
        stream.device().seek(0)
        stream.writeUInt16(reply.size() - SIZEOF_UINT16)
        socket.write(reply)
        socket.waitForBytesWritten()

    def sendBackFile(self, socket, filePath):  #
        file = QFile(filePath)
        print(file.size())
        count = 0
        with open(filePath, 'rb') as f:
            while 1:
                sleep(0.1)
                filedata = f.read(20480)
                if not filedata:
                    break
                reply = QByteArray()
                stream = QDataStream(reply, QIODevice.WriteOnly)
                stream.setVersion(QDataStream.Qt_4_0)
                stream.writeUInt16(0)

                stream.writeQString('SENDFILE')
                stream.writeQString(file.fileName())
                stream.writeInt(file.size())
                stream.writeBytes(filedata)

                stream.device().seek(0)
                stream.writeUInt16(reply.size() - SIZEOF_UINT16)
                socket.write(reply)
                socket.waitForBytesWritten()
                count = count + filedata.__len__()
                print(count)

    def fileToBytes(self, fileName):  # 将文件转换成二进制
        with open(fileName, 'rb') as f:
            return f.read()


class TcpServer(QTcpServer):

    def __init__(self, parent=None):
        super(TcpServer, self).__init__(parent)
        self.myParent = parent

    def incomingConnection(self, socketId):
        thread = Thread(socketId, self)
        threadDict[socketId] = thread  # 保存此线程对象可以解决回传的问题，
        print(threadDict)
        # thread.havegotmessageall.connect(self.myParent.getMessageAllTcp)  # 因为thread这个对象是内部创建的，只能通过parent得到他内部的信号  绑定
        print('# 151 连接一次')

        thread.finished.connect(thread.deleteLater)
        thread.start()


class BuildingServicesDlg(QObject):
    dosomething = pyqtSignal()

    def __init__(self):
        super(BuildingServicesDlg, self).__init__()
        self.tcpServer = TcpServer(self)

        if not self.tcpServer.listen(QHostAddress("0.0.0.0"), PORT):
            # QMessageBox.critical(self, "Building Services Server",
            #                      "Failed to start server: {0}".format(self.tcpServer.errorString()))

            self.close()
            return


if __name__ == '__main__':
    try:
        t = threading.Thread(target=app1.run, args=('127.0.0.1', 5000))
        t.start()
    except Exception as e:
        print(e)

    app = QCoreApplication(sys.argv)
    dig = BuildingServicesDlg()
    sys.exit(app.exec_())
