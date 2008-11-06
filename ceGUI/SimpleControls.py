"""
Defines simple controls with extensions to wx functionality.
"""

import ceGUI
import cx_Exceptions
import datetime
import wx

__all__ = ["BaseControl", "Choice", "DateField", "IntegerField", "Notebook",
           "TextField", "UpperCaseTextField"]

class BaseControl(object):
    copyAppAttributes = True
    baseSettingsName = None

    def _GetClass(self, name):
        pos = name.rfind(".")
        if pos < 0:
            moduleName = self.__class__.__module__
            attrName = name
        else:
            moduleName = name[:pos]
            attrName = name[pos + 1:]
        return ceGUI.GetModuleItem(moduleName, attrName)

    def _GetSettingsName(self, name):
        baseSettingsName = self.baseSettingsName
        if baseSettingsName is None:
            baseSettingsName = self.__class__.__module__
        return "%s/%s" % (baseSettingsName, name)

    def _Initialize(self):
        if self.copyAppAttributes:
            app = wx.GetApp()
            for name in app.copyAttributes:
                value = getattr(app, name)
                setattr(self, name, value)
        self._OnCreate()

    def _OnCreate(self):
        self.OnCreate()
        self.RestoreSettings()

    def BindEvent(self, control, event, method, createBusyCursor = False,
            skipEvent = True, passEvent = True):
        ceGUI.EventHandler(self, control, event, method,
                createBusyCursor = createBusyCursor, skipEvent = skipEvent,
                passEvent = passEvent)

    def FlushSettings(self):
        self.settings.Flush()

    def OnCreate(self):
        pass

    def OnLayout(self):
        pass

    def ReadSetting(self, name, defaultValue = None, isComplex = False,
            converter = None):
        settingsName = self._GetSettingsName(name)
        value = self.settings.Read(settingsName, "")
        if not value:
            return defaultValue
        if isComplex:
            converter = eval
        if converter is not None:
            try:
                value = converter(value)
            except:
                self.settings.DeleteEntry(fullName)
                value = defaultValue
        return value

    def RestoreSettings(self):
        pass

    def SaveSettings(self):
        pass

    def WriteSetting(self, name, value, isComplex = False, converter = None):
        settingsName = self._GetSettingsName(name)
        if value is None:
            value = ""
        else:
            if isComplex:
                converter = repr
            elif converter is None:
                converter = str
            value = converter(value)
        self.settings.Write(settingsName, value)


class Choice(BaseControl, wx.Choice):

    def __init__(self, parent, choices):
        wx.Choice.__init__(self, parent)
        self.SetChoices(choices)
        self._Initialize()

    def __AddChoice(self, dataValue, choiceIndex):
        self.indexesByDataValue[dataValue] = choiceIndex
        self.dataValuesByIndex[choiceIndex] = dataValue

    def Append(self, dataValue, displayValue = None):
        if displayValue is None:
            displayValue = dataValue
        choiceIndex = super(Choice, self).Append(displayValue)
        self.__AddChoice(dataValue, choiceIndex)
        return choiceIndex

    def GetValue(self):
        choiceIndex = self.GetSelection()
        if choiceIndex != wx.NOT_FOUND:
            return self.dataValuesByIndex[choiceIndex]

    def Insert(self, insertIndex, dataValue, displayValue = None):
        if displayValue is None:
            displayValue = dataValue
        choiceIndex = super(Choice, self).Insert(displayValue, insertIndex)
        self.__AddChoice(dataValue, choiceIndex)
        return choiceIndex

    def SetChoices(self, choices):
        self.Clear()
        displayValues = []
        self.indexesByDataValue = {}
        self.dataValuesByIndex = {}
        for choiceIndex, choice in enumerate(choices):
            if isinstance(choice, (list, tuple)):
                if len(choice) == 1:
                    dataValue = displayValue = choice[0]
                else:
                    dataValue, displayValue = choice
            else:
                dataValue = displayValue = choice
            displayValues.append(displayValue)
            self.__AddChoice(dataValue, choiceIndex)
        self.AppendItems(displayValues)

    def SetValue(self, value):
        choiceIndex = self.indexesByDataValue.get(value, wx.NOT_FOUND)
        self.SetSelection(choiceIndex)


class DateField(BaseControl, wx.DatePickerCtrl):
    copyAppAttributes = False

    def __init__(self, parent):
        wx.DatePickerCtrl.__init__(self, parent)

    def GetValue(self):
        wxDate = wx.DatePickerCtrl.GetValue(self)
        return datetime.date(wxDate.GetYear(), wxDate.GetMonth() + 1,
                wxDate.GetDay())

    def SetValue(self, value):
        wxDate = wx.DateTimeFromDMY(value.day, value.month - 1, value.year)
        wx.DatePickerCtrl.SetValue(self, wxDate)


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


class TextField(BaseControl, wx.TextCtrl):
    copyAppAttributes = False

    def __init__(self, parent, style = 0, maxLength = 0, size = (-1, -1)):
        wx.TextCtrl.__init__(self, parent, style = style, size = size)
        self.maxLength = maxLength
        if style & wx.TE_READONLY:
            self.SetReadOnly()
        if maxLength > 0:
            self.SetMaxLength(maxLength)
        self._Initialize()

    def GetValue(self):
        value = wx.TextCtrl.GetValue(self)
        if value:
            return value

    def SetReadOnly(self):
        color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE)
        self.SetBackgroundColour(color)
        self.SetEditable(False)

    def SetValue(self, value):
        wx.TextCtrl.SetValue(self, value or "")


class UpperCaseTextField(TextField):

    def _Initialize(self):
        super(UpperCaseTextField, self)._Initialize()
        ceGUI.EventHandler(self.GetParent(), self, wx.EVT_CHAR, self.OnChar,
                skipEvent = False)

    def OnChar(self, event):
        key = event.GetKeyCode()
        if key < ord('a') or key > ord('z'):
            event.Skip()
        elif self.maxLength > 0 \
                and len(wx.TextCtrl.GetValue(self)) >= self.maxLength:
            event.Skip()
        else:
            char = chr(key).upper()
            self.WriteText(char)


class IntegerField(TextField):

    def _Initialize(self):
        super(IntegerField, self)._Initialize()
        ceGUI.EventHandler(self.GetParent(), self, wx.EVT_CHAR, self.OnChar,
                skipEvent = False)

    def GetValue(self):
        value = super(IntegerField, self).GetValue()
        if value is not None:
            return int(value)

    def OnChar(self, event):
        key = event.GetKeyCode()
        if key in (wx.WXK_TAB, wx.WXK_BACK, wx.WXK_DELETE) or key > 127:
            event.Skip()
        if key >= ord('0') and key <= ord('9'):
            event.Skip()

    def SetValue(self, value):
        if value is not None:
            value = str(value)
        super(IntegerField, self).SetValue(value)

