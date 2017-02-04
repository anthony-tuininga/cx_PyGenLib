"""
Defines base configuration class for the application.
"""

import ceDatabase
import cx_Logging
import datetime
import wx

__all__ = ["BaseModel", "Config"]

class BaseModel(ceDatabase.Row):
    cached = False


class Config(object):
    dateFormat = "%Y/%m/%d"
    timestampFormat = "%Y/%m/%d %H:%M"
    dateNumberFormat = "yyyy/mm/dd"
    timestampNumberFormat = "yyyy/mm/dd hh:mm:ss"

    def __init__(self, app, dataSource = None, configId = None):
        self.settings = app.settings
        self.dataSource = dataSource
        self.configId = configId
        if dataSource is None:
            appName = app.GetAppName()
            self.dataSource = self.ConnectToDataSource(app, appName)
        self.ClearRowCache()
        self.OnCreate()

    def __ConvertDateToString(self, value):
        return value.strftime(self.dateFormat)

    def __ConvertStringToDate(self, value):
        return datetime.datetime.strptime(value, self.dateFormat)

    def __ConvertStringToTimestamp(self, value):
        return datetime.datetime.strptime(value, self.timestampFormat)

    def __ConvertTimestampToString(self, value):
        return value.strftime(self.timestampFormat)

    def ClearRowCache(self):
        self.rowsByModel = {}
        self.rowsByPK = {}

    def Clone(self, configId = None):
        app = wx.GetApp()
        newConfig = self.__class__(app, self.dataSource,
                configId or self.configId)
        newConfig.OnClone(self)
        return newConfig

    def ConnectToDataSource(self, app, appName):
        pass

    def GetBaseSettingsName(self):
        return "Database/%s/%s" % (self.dataSource.dsn, self.configId)

    def GetCachedRows(self, model, refresh = False):
        rows = self.rowsByModel.get(model)
        if rows is None or refresh:
            cx_Logging.Info("Getting cached rows for model %s", model.__name__)
            rows = self.rowsByModel[model] = model.GetRows(self.dataSource)
        return rows

    def GetCachedRowByPK(self, model, pkValue):
        rowDict = self.rowsByPK.get(model)
        if rowDict is None:
            cx_Logging.Info("Getting cached rows by PK for model %s",
                    model.__name__)
            rows = self.GetCachedRows(model)
            pkAttrName, = model.pkAttrNames
            rowDict = dict((getattr(r, pkAttrName), r) for r in rows)
            self.rowsByPK[model] = rowDict
        return rowDict.get(pkValue)

    def OnClone(self, otherConfig):
        pass

    def OnCreate(self):
        pass

    def OnRecreate(self):
        pass

    def ReadDatabaseSetting(self, name, defaultValue = None, isComplex = False,
                converter = None, isDate = False, isTimestamp = False):
        settingsName = "%s/%s" % (self.GetBaseSettingsName(), name)
        return self.ReadSetting(settingsName, defaultValue = defaultValue,
                isComplex = isComplex, converter = converter, isDate = isDate,
                isTimestamp = isTimestamp)

    def ReadSetting(self, name, defaultValue = None, isComplex = False,
            converter = None, isDate = False, isTimestamp = False):
        value = self.settings.Read(name, "")
        if not value:
            return defaultValue
        if isComplex:
            converter = eval
        elif isDate:
            converter = self.__ConvertStringToDate
        elif isTimestamp:
            converter = self.__ConvertStringToTimestamp
        if converter is not None:
            try:
                value = converter(value)
            except:
                self.settings.DeleteEntry(name)
                value = defaultValue
        return value

    def RemoveCachedRow(self, model, externalRow):
        pkAttrName, = model.pkAttrNames
        pkValue = getattr(externalRow, pkAttrName)
        row = self.GetCachedRowByPK(model, pkValue)
        if row is None:
            cx_Logging.Info("Ignoring row not cached for model %s (pk = %s)",
                    model.__name__, pkValue)
        else:
            cx_Logging.Info("Removing cached row for model %s (pk = %s)",
                    model.__name__, pkValue)
            del self.rowsByPK[model][pkValue]
            self.rowsByModel[model].remove(row)

    def RestoreConfigId(self):
        settingsName = "Database/%s/ConfigId" % self.dataSource.dsn
        self.configId = self.ReadSetting(settingsName, converter = int)
        return self.configId

    def SaveConfigId(self, configId):
        settingsName = "Database/%s/ConfigId" % self.dataSource.dsn
        self.WriteSetting(settingsName, configId)

    def UpdateCachedRow(self, model, externalRow, contextItem = None):
        pkAttrName, = model.pkAttrNames
        pkValue = getattr(externalRow, pkAttrName)
        row = self.GetCachedRowByPK(model, pkValue)
        if row is not None:
            cx_Logging.Info("Updating cached row for model %s (pk = %s)",
                    model.__name__, pkValue)
        else:
            row = model.New()
            self.rowsByModel[model].append(row)
            self.rowsByPK[model][pkValue] = row
            cx_Logging.Info("Creating cached row for model %s (pk = %s)",
                    model.__name__, pkValue)
        for attrName in row.attrNames + row.extraAttrNames:
            if hasattr(externalRow, attrName):
                value = getattr(externalRow, attrName)
            elif hasattr(contextItem, attrName):
                value = getattr(contextItem, attrName)
            else:
                continue
            setattr(row, attrName, value)

    def WriteDatabaseSetting(self, name, value, isComplex = False,
            converter = None, isDate = False, isTimestamp = False):
        settingsName = "%s/%s" % (self.GetBaseSettingsName(), name)
        self.WriteSetting(settingsName, value, isComplex = isComplex,
                converter = converter, isDate = isDate,
                isTimestamp = isTimestamp)

    def WriteSetting(self, name, value, isComplex = False, converter = None,
            isDate = False, isTimestamp = False):
        if value is None:
            value = ""
        else:
            if isComplex:
                converter = repr
            elif isDate:
                converter = self.__ConvertDateToString
            elif isTimestamp:
                converter = self.__ConvertTimestampToString
            elif converter is None:
                converter = str
            value = converter(value)
        self.settings.Write(name, value)

