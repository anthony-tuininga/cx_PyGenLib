"""
Defines class for the application. This handles starting logging using
cx_Logging and saving/restoring settings in a standard way. It also sets up a
set of attributes that are copied to all controls, in particular the
application configuration and settings objects.
"""

import ceGUI
import cx_Exceptions
import cx_Logging
import os
import wx
import sys

__all__ = ["Application"]


class Application(wx.App):
    copyAttributes = ""
    copyrightOwner = None
    copyrightStartYear = None
    copyrightEndYear = None
    description = None
    vendorName = None
    version = None

    def _ExceptionHandler(self, excType, excValue, excTraceback):
        exc = cx_Exceptions.GetExceptionInfo(excType, excValue, excTraceback)
        self.OnException(exc)

    def GetDefaultLoggingFileName(self):
        baseName = "%s.log" % self.GetAppName()
        standardPaths = wx.StandardPaths.Get()
        return os.path.join(standardPaths.GetUserDataDir(), baseName)

    def GetTopWindow(self):
        return ceGUI.OpenWindow("w_TopLevelFrame.Frame")

    def OnException(self, exc, parent = None):
        cx_Logging.LogException(exc)
        wx.MessageBox(exc.message, "Error", wx.OK | wx.ICON_EXCLAMATION,
                parent)

    def OnInit(self):
        self.topWindow = None
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
        self.copyAttributes = self.copyAttributes.split()
        self.copyAttributes.append("settings")
        cls = ceGUI.GetModuleItem(self.__class__.__module__, "Config")
        self.config = cls(self)
        self.copyAttributes.append("config")
        self.OnStartup()
        self.topWindow = self.GetTopWindow()
        if self.topWindow is not None:
            self.SetTopWindow(self.topWindow)
            self.topWindow.Show()
        return True

    def OnStartup(self):
        pass

    def StartLogging(self):
        defaultFileName = self.GetDefaultLoggingFileName()
        fileName = self.settings.Read("LogFileName", defaultFileName)
        levelName = self.settings.Read("LogLevel", "ERROR")
        level = getattr(cx_Logging, levelName)
        cx_Logging.StartLogging(fileName, level)

