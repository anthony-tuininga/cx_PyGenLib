"""
Defines simple controls with extensions to wx functionality.
"""

import wx

__all__ = ["BaseControl", "Notebook"]


class BaseControl(object):
    saveSize = savePosition = False
    baseSettingsName = None
    minSize = None

    def _GetSettingsName(self, name):
        baseSettingsName = self.baseSettingsName
        if baseSettingsName is None:
            baseSettingsName = self.__class__.__module__
        return "%s/%s" % (baseSettingsName, name)

    def _Initialize(self):
        app = wx.GetApp()
        for name in app.copyAttributes:
            value = getattr(app, name)
            setattr(self, name, value)
        if self.minSize is not None:
            self.SetMinSize(self.minSize)
        self._OnCreate()

    def _OnCreate(self):
        self.OnCreate()
        self._RestoreSettings()

    def _RestoreSettings(self):
        if self.saveSize:
            size = self.ReadSetting("Size", isComplex = True)
            if size is not None:
                self.SetSize(size)
        if self.savePosition:
            position = self.ReadSetting("Position", isComplex = True)
            if position is not None:
                self.SetPosition(position)
        self.RestoreSettings()

    def _SaveSettings(self):
        if self.saveSize:
            self.WriteSetting("Size", self.GetSizeTuple(), isComplex = True)
        if self.savePosition:
            self.WriteSetting("Position", self.GetPositionTuple(),
                    isComplex = True)
        self.SaveSettings()
        self.settings.Flush()

    def FlushSettings(self):
        self.settings.Flush()

    def OnCreate(self):
        pass

    def OnLayout(self):
        pass

    def ReadSetting(self, name, defaultValue = None, isComplex = False):
        settingsName = self._GetSettingsName(name)
        value = self.settings.Read(settingsName, "")
        if not value:
            return defaultValue
        if isComplex:
            try:
                value = eval(value)
            except:
                self.settings.DeleteEntry(fullName)
                value = defaultValue
        return value

    def RestoreSettings(self):
        pass

    def SaveSettings(self):
        pass

    def WriteSetting(self, name, value, isComplex = False):
        settingsName = self._GetSettingsName(name)
        if isComplex:
            value = repr(value)
        else:
            value = str(value)
        self.settings.Write(settingsName, value)


class Notebook(BaseControl, wx.Notebook):

    def __init__(self, *args, **kwargs):
        wx.Notebook.__init__(self, *args, **kwargs)
        self._Initialize()

    def IterPages(self):
        for pageIndex in range(self.GetPageCount()):
            yield self.GetPage(pageIndex)

    def RestoreSettings(self):
        for page in self.IterPages():
            page.RestoreSettings()

    def SaveSettings(self):
        for page in self.IterPages():
            page.SaveSettings()

