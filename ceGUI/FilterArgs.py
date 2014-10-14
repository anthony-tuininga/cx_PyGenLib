"""
Handle the addition of filter arguments.
"""

import ceGUI
import wx
import wx.adv

class FilterArg(object):
    changeEvent = None

    def __init__(self, parent, name, label, fieldControl,
            onChangeMethod = None, passEvent = False, labelBorder = 10,
            **args):
        self.name = name
        parent.filterArgs.append(self)
        self.labelControl = parent.AddLabel(label)
        self.fieldControl = fieldControl
        self.labelBorder = labelBorder
        if onChangeMethod is None and not parent.createRetrieveButton:
            onChangeMethod = parent.Retrieve
        if onChangeMethod is not None:
            parent.BindEvent(fieldControl, self.changeEvent, onChangeMethod,
                    passEvent = passEvent)
        self.ExtendedInitialize(**args)

    def ExtendedInitialize(self, **args):
        pass

    def GetValue(self):
        return self.fieldControl.GetValue()

    def Layout(self, sizer):
        baseFlag = flag = wx.ALIGN_CENTER_VERTICAL
        for child in sizer.GetChildren():
            flag |= wx.LEFT
            break
        sizer.Add(self.labelControl, flag = flag, border = self.labelBorder)
        sizer.Add(self.fieldControl, flag = baseFlag | wx.LEFT, border = 5)

    def SetValue(self, value):
        self.fieldControl.SetValue(value)


class FilterArgBool(FilterArg):

    def __init__(self, parent, name, label, labelBorder = 10,
            onChangeMethod = None, passEvent = False, **args):
        fieldControl = parent.AddCheckBox()
        super(FilterArgBool, self).__init__(parent, name, label, fieldControl,
                onChangeMethod = onChangeMethod, passEvent = passEvent,
                labelBorder = labelBorder, **args)


class FilterArgChoice(FilterArg):
    changeEvent = wx.EVT_CHOICE

    def __init__(self, parent, name, label, labelBorder = 10,
            choices = [], size = (-1, -1), onChangeMethod = None,
            passEvent = False, **args):
        self.choices = choices
        fieldControl = parent.AddChoiceField(choices, size = size)
        super(FilterArgChoice, self).__init__(parent, name, label,
                fieldControl, onChangeMethod = onChangeMethod,
                passEvent = passEvent, labelBorder = labelBorder, **args)

    def SetChoices(self, choices):
        self.fieldControl.SetChoices(choices)


class FilterArgDate(FilterArg):
    changeEvent = wx.adv.EVT_DATE_CHANGED

    def __init__(self, parent, name, label, labelBorder = 10,
            allowNone = True, showDropDown = True, onChangeMethod = None,
            passEvent = False, **args):
        fieldControl = parent.AddDateField(allowNone = allowNone,
                showDropDown = showDropDown)
        super(FilterArgDate, self).__init__(parent, name, label, fieldControl,
                onChangeMethod = onChangeMethod, passEvent = passEvent,
                labelBorder = labelBorder, **args)


class FilterArgInt(FilterArg):
    changeEvent = wx.EVT_TEXT

    def __init__(self, parent, name, label, labelBorder = 10,
            size = (-1, -1), onChangeMethod = None, passEvent = False, **args):
        fieldControl = parent.AddTextField(cls = ceGUI.IntegerField,
                size = size)
        super(FilterArgInt, self).__init__(parent, name, label, fieldControl,
                onChangeMethod = onChangeMethod, passEvent = passEvent,
                labelBorder = labelBorder, **args)


class FilterArgStr(FilterArg):
    changeEvent = wx.EVT_TEXT

    def __init__(self, parent, name, label, labelBorder = 10,
            size = (-1, -1), forceUppercase = True, onChangeMethod = None,
            passEvent = False, **args):
        self.forceUppercase = forceUppercase
        fieldControl = parent.AddTextField(size = size)
        super(FilterArgStr, self).__init__(parent, name, label, fieldControl,
                onChangeMethod = onChangeMethod, passEvent = False,
                labelBorder = labelBorder, **args)

    def GetValue(self):
        value = self.fieldControl.GetValue()
        if value is not None and self.forceUppercase:
            value = value.upper()
        return value

