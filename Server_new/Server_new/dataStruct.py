# encoding:utf-8
from flask_restful import fields, marshal
import json


class dataStuct(object):
    def __init__(self):
        self._areaData = {
            "titles": [
                "设备ID",
                "状态",
            ],
            "data": []

        }

        self._resultData = {
            "titles": ["序号", "信号类型", "识别结果", "识别时间", "耗时"],
            "data": []
        }

        self._configInfo = {
            "filesList": [],
            "channelsList": [

            ]
        }
        self._deviceInfo ={
            "deviceFixId":"",
            "ip":"",
            "fileInfo":[],
            "pictureSize":{},
            "kind":"",
            "regionProvince":"",
            "regionCity":"合肥",
            "regionArea":"庐阳区"
        }
        self._mapInfo = []

    def getAreaData(self):
        return self._areaData

    def getResultData(self):
        return self._resultData

    def getConfigInfo(self):
        return self._configInfo

    def getDeviceInfo(self):
        return self._deviceInfo
    def getMapInfo(self):
        return self._mapInfo

if __name__ == '__main__':
    data = {"fixedID": "1231", "state": "123"}
    areaData.get('data').append(data)
    areaData.get('data').append(data)
    areaData.get('data').append(data)
    areaData.get('data').append(data)
    areaData.get('data').append(data)
    print(areaData)
