"""
Defines simple controls with extensions to wx functionality.
"""

import ceGUI
import cx_Exceptions
import datetime
import decimal
import wx
try:
    import wx.adv as DatePickerLib
except ImportError:
    DatePickerLib = wx

__all__ = ["BaseControl", "Choice", "DateField",
           "DecimalField", "IntegerField", "Notebook", "TextField",
           "UpperCaseTextField"]

class BaseControl(object):
    createdSuccessfully = False
    copyAppAttributes = True
    baseSettingsName = None

    def _GetClass(self, name):
        return ceGUI.GetModuleItem(name, associatedObj = self)

    def _GetSettingsName(self, name):
        baseSettingsName = self.baseSettingsName
        if baseSettingsName is None:
            baseSettingsName = "/".join(self.__class__.__module__.split("."))
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

    def ContinueQuery(self, allowCancel = True, parent = None):
        return True

    def FlushSettings(self):
        self.settings.Flush()

    def OnCreate(self):
        pass

    def OnLayout(self):
        pass

    def ReadSetting(self, name, defaultValue = None, isComplex = False,
            converter = None):
        settingsName = self._GetSettingsName(name)
        return self.config.ReadSetting(settingsName, defaultValue, isComplex,
                converter)

    def RestoreSettings(self):
        pass

    def SaveSettings(self):
        pass

    def WriteSetting(self, name, value, isComplex = False, converter = None):
        settingsName = self._GetSettingsName(name)
        self.config.WriteSetting(settingsName, value, isComplex, converter)


class Choice(BaseControl, wx.Choice):

    def __init__(self, parent, choices, size = (-1, -1)):
        wx.Choice.__init__(self, parent, size = size)
        self.SetChoices(choices)
        self._Initialize()

    def GetValue(self):
        choiceIndex = self.GetSelection()
        if choiceIndex != wx.NOT_FOUND:
            return self.dataValuesByIndex[choiceIndex]

    def SetChoices(self, choices):
        origValue = self.GetValue()
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
            self.indexesByDataValue[dataValue] = choiceIndex
            self.dataValuesByIndex[choiceIndex] = dataValue
        self.AppendItems(displayValues)
        self.SetValue(origValue)

    def SetValue(self, value):
        choiceIndex = self.indexesByDataValue.get(value, wx.NOT_FOUND)
        self.SetSelection(choiceIndex)


class DateField(BaseControl, DatePickerLib.DatePickerCtrl):
    copyAppAttributes = False

    def __init__(self, parent, allowNone = False, showDropDown = False):
        self.allowNone = allowNone
        self.showDropDown = showDropDown
        style = DatePickerLib.DP_DEFAULT | DatePickerLib.DP_SHOWCENTURY
        if allowNone:
            style |= DatePickerLib.DP_ALLOWNONE
        if showDropDown:
            style |= DatePickerLib.DP_DROPDOWN
        DatePickerLib.DatePickerCtrl.__init__(self, parent, style = style,
                size = (120, -1))

    def GetValue(self):
        wxDate = DatePickerLib.DatePickerCtrl.GetValue(self)
        if wxDate.IsValid():
            return datetime.datetime(wxDate.GetYear(), wxDate.GetMonth() + 1,
                    wxDate.GetDay())

    def SetValue(self, value):
        if value is not None:
            wxDate = wx.DateTime.FromDMY(value.day, value.month - 1,
                    value.year)
            DatePickerLib.DatePickerCtrl.SetValue(self, wxDate)
        elif self.allowNone:
            wxDate = wx.DateTime()
            DatePickerLib.DatePickerCtrl.SetValue(self, wxDate)


class Notebook(BaseControl, wx.Notebook):

    def __init__(self, *args, **kwargs):
        wx.Notebook.__init__(self, *args, **kwargs)
        self._Initialize()

    def AddPage(self, nameOrPage, text):
        if isinstance(nameOrPage, str):
            nameOrPage = ceGUI.OpenWindow(nameOrPage, self)
        wx.Notebook.AddPage(self, nameOrPage, text)

    def AddPageWithCheck(self, name, text):
        currentPage = self.GetCurrentPage()
        newPage = ceGUI.OpenWindow(name, self, instanceName = text)
        if newPage is currentPage:
            return newPage
        for pageIndex in range(self.GetPageCount()):
            page = self.GetPage(pageIndex)
            if newPage is page:
                self.SetSelection(pageIndex)
                return newPage
        wx.Notebook.AddPage(self, newPage, text)
        newPage.RestoreSettings()
        return newPage

    def ContinueQuery(self, allowCancel = True, parent = None):
        pageIndex = 0
        for page in self.IterPages():
            if page.PendingChanges():
                self.SetSelection(pageIndex)
                if not page.ContinueQuery(allowCancel, parent):
                    return False
            pageIndex += 1
        return True

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
        if value is None:
            value = ""
        elif not isinstance(value, str):
            value = str(value)
        wx.TextCtrl.SetValue(self, value)


class UpperCaseTextField(TextField):

    def _Initialize(self):
        super(UpperCaseTextField, self)._Initialize()
        ceGUI.EventHandler(self.GetParent(), self, wx.EVT_CHAR, self.OnChar,
                skipEvent = False)

    def GetValue(self):
        value = super(UpperCaseTextField, self).GetValue()
        if value is not None:
            return value.upper()

    def OnChar(self, event):
        if not self.IsEditable():
            event.Skip()
            return
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


class DecimalField(IntegerField):

    def __init__(self, parent, style = 0, digitsBeforeDecimal = 3,
            digitsAfterDecimal = 2):
        self.digitsBeforeDecimal = digitsBeforeDecimal
        self.digitsAfterDecimal = digitsAfterDecimal
        self.format = "%%.%df" % digitsAfterDecimal
        super(DecimalField, self).__init__(parent, style = style)

    def GetValue(self):
        textValue = wx.TextCtrl.GetValue(self)
        if textValue:
            if textValue == ".":
                return decimal.Decimal(0)
            pos = textValue.find(".")
            if pos < 0:
                digitsBeforeDecimal = len(textValue)
                digitsAfterDecimal = 0
            else:
                digitsBeforeDecimal = pos
                digitsAfterDecimal = len(textValue) - pos - 1
            if digitsBeforeDecimal > self.digitsBeforeDecimal:
                raise TooManyDigitsBeforeDecimal(digitsAllowed = \
                        self.digitsBeforeDecimal)
            if digitsAfterDecimal > self.digitsAfterDecimal:
                raise TooManyDigitsAfterDecimal(digitsAllowed = \
                        self.digitsAfterDecimal)
            return decimal.Decimal(textValue)

    def OnChar(self, event):
        super(DecimalField, self).OnChar(event)
        key = event.GetKeyCode()
        if key in (ord("."), ord("-")):
            event.Skip()

    def SetValue(self, value):
        if value is None:
            textValue = ""
        else:
            textValue = self.format % value
        wx.TextCtrl.SetValue(self, textValue)


class TooManyDigitsAfterDecimal(cx_Exceptions.BaseException):
    message = "Value has too many digits after the decimal point " \
              "(%(digitsAllowed)s allowed)."


class TooManyDigitsBeforeDecimal(cx_Exceptions.BaseException):
    message = "Value has too many digits before the decimal point " \
              "(%(digitsAllowed)s allowed)."

