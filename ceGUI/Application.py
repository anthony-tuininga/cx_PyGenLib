"""
Defines class for the application. This handles starting logging using
cx_Logging and saving/restoring settings in a standard way. It also sets up a
set of attributes that are copied to all controls, in particular the
application configuration and settings objects.
"""

import ceGUI
import cx_Exceptions
import cx_Logging
import datetime
import os
import wx
import sys

__all__ = ["Application"]

# grab the build release string from the build constants module generated by
# cx_Freeze, if possible
try:
    from BUILD_CONSTANTS import BUILD_RELEASE_STRING
except ImportError:
    BUILD_RELEASE_STRING = "Source"


class Application(wx.App):
    copyAttributes = ""
    copyrightOwner = None
    copyrightStartYear = None
    copyrightEndYear = None
    description = None
    vendorName = None
    configClassName = "ceGUI.Config"
    topLevelClassName = "w_TopLevelFrame.Frame"
    version = BUILD_RELEASE_STRING
    logMaxFilesDefault = 1
    showTopWindowOnInit = True
    busyInfo = None

    def _ExceptionHandler(self, excType, excValue, excTraceback):
        exc = cx_Exceptions.GetExceptionInfo(excType, excValue, excTraceback)
        self.OnException(exc)

    def GetConfig(self, dataSource = None):
        cls = ceGUI.GetModuleItem(self.configClassName, associatedObj = self)
        return cls(self, dataSource)

    def GetDefaultLoggingFileName(self):
        baseName = "%s.log" % self.GetAppName()
        standardPaths = wx.StandardPaths.Get()
        return os.path.join(standardPaths.GetUserDataDir(), baseName)

    def GetTopWindow(self):
        return ceGUI.OpenWindow(self.topLevelClassName)

    def OnException(self, exc, parent = None, logException = True):
        if logException:
            cx_Logging.LogException(exc)
        if self.busyInfo is not None:
            self.busyInfo.Destroy()
            self.busyInfo = None
        wx.MessageBox(exc.message, "Error", wx.OK | wx.ICON_EXCLAMATION,
                parent)
        method = getattr(exc, "method", None)
        if method is not None:
            method()

    def OnStartup(self):
        return True

    def Run(self):
        self.topWindow = None
        self.SetAppName(self.__class__.__name__)
        if self.vendorName is not None:
            self.SetVendorName(self.vendorName)
        if sys.platform == "win32":
            self.settings = wx.ConfigBase.Get()
        else:
            standardPaths = wx.StandardPaths.Get()
            dir = standardPaths.GetUserDataDir()
            fileName = os.path.join(dir, "settings.cfg")
            self.settings = wx.FileConfig(localFilename = fileName)
            wx.ConfigBase.Set(self.settings)
        self.StartLogging()
        sys.excepthook = self._ExceptionHandler
        self.copyAttributes = set(self.copyAttributes.split())
        self.config = self.GetConfig()
        self.copyAttributes.add("settings")
        self.copyAttributes.add("config")
        if self.OnStartup():
            self.topWindow = self.GetTopWindow()
            if self.topWindow is not None:
                self.SetTopWindow(self.topWindow)
                if self.showTopWindowOnInit:
                    self.topWindow.Show()
        self.MainLoop()

    def StartLogging(self):
        defaultFileName = self.GetDefaultLoggingFileName()
        fileName = self.settings.Read("LogFileName", defaultFileName)
        dirName = os.path.dirname(fileName)
        if not os.path.isdir(dirName):
            os.makedirs(dirName)
        levelName = self.settings.Read("LogLevel", "ERROR")
        level = getattr(cx_Logging, levelName)
        maxFilesRaw = self.settings.Read("LogMaxFiles",
                str(self.logMaxFilesDefault))
        try:
            maxFiles = int(maxFilesRaw)
        except:
            self.settings.DeleteEntry("LogMaxFiles")
            maxFiles = self.logMaxFilesDefault
        cx_Logging.StartLogging(fileName, level, maxFiles)

