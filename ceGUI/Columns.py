"""
Class definitions for columns used in list controls and grids.
"""

import ceGUI
import datetime
import decimal
import wx
import wx.adv
import wx.grid

__all__ = [ "Column", "ColumnBool", "ColumnDate", "ColumnDecimal", "ColumnInt",
            "ColumnMoney", "ColumnStr", "ColumnTimestamp",
            "InvalidValueEntered" ]

class Column(ceGUI.BaseControl):
    defaultHorizontalAlignment = "left"
    defaultVerticalAlignment = "middle"
    displayNativeValue = True
    defaultNumberFormat = "@"
    defaultSortValue = ""
    defaultHeading = ""
    defaultWidth = None

    def __init__(self, attrName, heading = None, defaultWidth = None,
            horizontalAlignment = None, verticalAlignment = None,
            numberFormat = None, required = False, displayAttrName = None,
            **otherArgs):
        self.attrName = attrName
        self.displayAttrName = displayAttrName
        if displayAttrName is not None:
            self.displayNativeValue = False
        self.required = required
        self.heading = heading or self.defaultHeading
        self.defaultWidth = defaultWidth or self.defaultWidth
        self.horizontalAlignment = \
                horizontalAlignment or self.defaultHorizontalAlignment
        self.verticalAlignment = \
                verticalAlignment or self.defaultVerticalAlignment
        self.numberFormat = numberFormat or self.defaultNumberFormat
        self._Initialize()
        self.ExtendedInitialize(**otherArgs)

    def __repr__(self):
        return "<%s attrName=%r heading=%r>" % \
                (self.__class__.__name__, self.attrName, self.heading)

    def _OnAddToGrid(self, grid, readOnly):
        if self.horizontalAlignment == "center":
            horizontalAlignment = wx.ALIGN_CENTER
        elif self.horizontalAlignment == "right":
            horizontalAlignment = wx.ALIGN_RIGHT
        else:
            horizontalAlignment = wx.ALIGN_LEFT
        if self.verticalAlignment == "middle":
            verticalAlignment = wx.ALIGN_CENTER
        elif self.verticalAlignment == "bottom":
            verticalAlignment = wx.ALIGN_BOTTOM
        else:
            verticalAlignment = wx.ALIGN_TOP
        self.attr = wx.grid.GridCellAttr()
        self.attr.SetAlignment(horizontalAlignment, verticalAlignment)
        if readOnly:
            self.attr.SetReadOnly()
        self.OnAddToGrid(grid)

    def _OnAddToList(self, listControl, columnIndex):
        """Add a column to the control; note that if the column is right
           justified and the first column in the control, a dummy column is
           added and removed because on Windows, the first column is assumed to
           be left justified, no matter what format is specified."""
        if self.horizontalAlignment == "center":
            justification = wx.LIST_FORMAT_CENTER
        elif self.horizontalAlignment == "right":
            justification = wx.LIST_FORMAT_RIGHT
        else:
            justification = wx.LIST_FORMAT_LEFT
        listControl.InsertColumn(columnIndex, self.heading, justification,
                self.defaultWidth or -1)
        if columnIndex == 0 and justification == wx.LIST_FORMAT_RIGHT:
            listControl.InsertColumn(columnIndex + 1, self.heading,
                    justification, self.defaultWidth or -1)
            listControl.DeleteColumn(columnIndex)
        self.OnAddToList(listControl)

    def ExtendedInitialize(self, **args):
        pass

    def GetExportHeading(self):
        if self.heading:
            return '"%s"' % self.heading.replace('"', '""')
        return ""

    def GetExportValue(self, row):
        value = getattr(row, self.attrName)
        if isinstance(value, str):
            return '"%s"' % value.replace('"', '""')
        elif value is not None:
            return str(value)
        return ""

    def GetLabelValue(self):
        return self.heading

    def GetKeyValueForDisplayValue(self, row, displayValue):
        return displayValue

    def GetNativeValue(self, row):
        if self.attrName is None:
            return row
        return getattr(row, self.attrName)

    def GetSortValue(self, row):
        if self.displayNativeValue:
            value = self.GetNativeValue(row)
        else:
            value = self.GetValue(row)
        if value is None:
            return self.defaultSortValue
        elif isinstance(value, str):
            return value.upper()
        return value

    def GetValue(self, row):
        if self.displayAttrName is not None:
            value = getattr(row, self.displayAttrName)
        else:
            value = self.GetNativeValue(row)
        if value is None:
            return ""
        elif isinstance(value, str):
            return value
        return str(value)

    def OnAddToGrid(self, grid):
        pass

    def OnAddToList(self, listControl):
        pass

    def OnEditorCreated(self, control):
        self.editorControl = control

    def OnEditorHidden(self, row):
        pass

    def OnEditorShown(self, row):
        pass

    def SetValue(self, grid, dataSet, rowHandle, row, value):
        if self.displayAttrName is None:
            dataSet.SetValue(rowHandle, self.attrName, value)
        else:
            if value is None:
                keyValue = displayValue = None
            else:
                keyValue, displayValue = value
            dataSet.SetValue(rowHandle, self.attrName, keyValue)
            dataSet.SetValue(rowHandle, self.displayAttrName, displayValue)

    def VerifyValue(self, row):
        if self.required:
            value = getattr(row, self.attrName)
            if value is None:
                return ceGUI.RequiredFieldHasNoValue()

    def VerifyValueOnChange(self, row, rawValue):
        if self.displayAttrName is None:
            return rawValue
        keyValue = self.GetKeyValueForDisplayValue(row, rawValue)
        return (keyValue, rawValue)


class ColumnBool(Column):
    defaultHorizontalAlignment = "center"
    defaultSortValue = False

    def OnAddToGrid(self, grid):
        editor = wx.grid.GridCellBoolEditor()
        editor.UseStringValues("Yes", "No")
        self.attr.SetEditor(editor)
        self.attr.SetRenderer(wx.grid.GridCellBoolRenderer())

    def GetValue(self, row):
        value = self.GetNativeValue(row)
        return "Yes" if value else "No"

    def VerifyValueOnChange(self, row, rawValue):
        return rawValue == "Yes"


class ColumnDate(Column):
    defaultSortValue = datetime.datetime.min
    dateFormatAttrName = "dateFormat"
    dateNumberFormatAttrName = "dateNumberFormat"
    defaultNumberFormat = None

    def ExtendedInitialize(self, dateFormat = None):
        if dateFormat is None:
            dateFormat = getattr(self.config, self.dateFormatAttrName)
        self.dateFormat = dateFormat
        if self.numberFormat is None:
            self.numberFormat = getattr(self.config,
                    self.dateNumberFormatAttrName)

    def OnAddToGrid(self, grid):
        self.attr.SetEditor(GridColumnDateEditor(self.required))

    def GetValue(self, row):
        value = self.GetNativeValue(row)
        if value is not None:
            return value.strftime(self.dateFormat)
        return ""

    def VerifyValueOnChange(self, row, rawValue):
        try:
            return datetime.datetime.strptime(rawValue, self.dateFormat)
        except ValueError:
            message = "'%s' is not a valid date." % rawValue
            raise InvalidValueEntered(message)


class ColumnDecimal(Column):
    defaultHorizontalAlignment = "right"
    defaultNumberFormat = None
    storeAsString = False
    defaultSortValue = 0

    def ExtendedInitialize(self, formatString = None, digitsAfterDecimal = 2,
            prefix = "", suffix = ""):
        self.digitsAfterDecimal = digitsAfterDecimal
        self.prefix = prefix
        self.suffix = suffix
        if formatString is None:
            formatString = "%s{0:,.%sf}%s" % \
                    (prefix, digitsAfterDecimal, suffix)
        self.formatString = formatString
        if self.numberFormat is None:
            if digitsAfterDecimal == 0:
                self.numberFormat = "#,##0"
            else:
                self.numberFormat = "#,##0." + "0" * digitsAfterDecimal
            if prefix is not None:
                self.numberFormat = prefix + self.numberFormat
            if suffix is not None:
                self.numberFormat += suffix

    def GetExportValue(self, row):
        value = self.GetNativeValue(row)
        if value is not None:
            return self.formatString.format(value)
        return ""

    def GetValue(self, row):
        value = self.GetNativeValue(row)
        if value is not None:
            return self.formatString.format(value)
        return ""

    def VerifyValueOnChange(self, row, rawValue):
        try:
            tweakedValue = rawValue.replace(",", "")
            if self.prefix:
                tweakedValue = tweakedValue.replace(self.prefix, "")
            if self.suffix:
                tweakedValue = tweakedValue.replace(self.suffix, "")
            value = decimal.Decimal(tweakedValue)
            if self.storeAsString:
                value = tweakedValue
            return value
        except decimal.InvalidOperation:
            message = "'%s' is not a valid number." % rawValue
            raise InvalidValueEntered(message)


class ColumnInt(Column):
    defaultHorizontalAlignment = "right"
    defaultNumberFormat = "#,##0"
    defaultSortValue = 0

    def OnAddToGrid(self, grid):
        self.attr.SetRenderer(wx.grid.GridCellNumberRenderer())

    def VerifyValueOnChange(self, row, rawValue):
        try:
            return int(rawValue)
        except ValueError:
            message = "'%s' is not a valid integer." % rawValue
            raise InvalidValueEntered(message)


class ColumnMoney(ColumnDecimal):

    def ExtendedInitialize(self):
        super(ColumnMoney, self).ExtendedInitialize(prefix = "$")


class ColumnStr(Column):

    def ExtendedInitialize(self, forceUpper = False, forceLower = False,
            maxLength = None):
        self.forceUpper = forceUpper
        self.forceLower = forceLower
        self.maxLength = maxLength

    def VerifyValueOnChange(self, row, rawValue):
        if rawValue and self.maxLength is not None \
                and len(rawValue) > self.maxLength:
            message = "Value is too large (%s characters and only " \
                    "%s characters are allowed" % \
                    (len(rawValue), self.maxLength)
            raise InvalidValueEntered(message)
        if rawValue and self.forceUpper:
            return rawValue.upper()
        elif rawValue and self.forceLower:
            return rawValue.lower()
        return rawValue


class ColumnTimestamp(ColumnDate):
    dateFormatAttrName = "timestampFormat"
    dateNumberFormatAttrName = "timestampNumberFormat"


class GridColumnDateEditor(wx.grid.GridCellEditor):

    def __init__(self, requiredValue):
        wx.grid.GridCellEditor.__init__(self)
        self.requiredValue = requiredValue

    def ApplyEdit(self, rowIndex, colIndex, grid):
        value = None
        table = grid.GetTable()
        column = table.GetColumn(colIndex)
        wxDate = self.control.GetValue()
        if wxDate.IsValid():
            dateValue = datetime.datetime(wxDate.GetYear(),
                    wxDate.GetMonth() + 1, wxDate.GetDay())
            value = dateValue.strftime(column.dateFormat)
        table.SetValue(rowIndex, colIndex, value)

    def BeginEdit(self, rowIndex, colIndex, grid):
        self.initialValue = None
        table = grid.GetTable()
        column = table.GetColumn(colIndex)
        initialValue = table.GetValue(rowIndex, colIndex)
        if initialValue:
            dateValue = datetime.datetime.strptime(initialValue,
                    column.dateFormat)
            self.initialValue = wx.DateTime.FromDMY(dateValue.day,
                    dateValue.month - 1, dateValue.year)
            self.control.SetValue(self.initialValue)
        self.control.SetFocus()

    def Clone(self):
        return GridColumnDateEditor(self.requiredValue)

    def Create(self, parent, id, evtHandler):
        style = wx.adv.DP_DEFAULT | wx.adv.DP_SHOWCENTURY | wx.adv.DP_DROPDOWN
        if not self.requiredValue:
            style |= wx.adv.DP_ALLOWNONE
        self.control = wx.adv.DatePickerCtrl(parent, id, style = style)
        self.SetControl(self.control)
        self.initialValue = None
        if evtHandler:
            self.control.PushEventHandler(evtHandler)

    def EndEdit(self, rowIndex, colIndex, grid, initialValue):
        changed = False
        wxDate = self.control.GetValue()
        if not wxDate.IsValid():
            return self.initialValue is not None
        elif self.initialValue is None:
            return True
        return wxDate.year != self.initialValue.year \
                or wxDate.month != self.initialValue.month \
                or wxDate.day != self.initialValue.day

    def Reset(self):
        if self.initialValue is not None:
            self.control.SetValue(self.initialValue)

    def SetSize(self, rect):
        self.control.SetSize(rect.x, rect.y, rect.width + 2, rect.height + 2,
                wx.SIZE_ALLOW_MINUS_ONE)


class InvalidValueEntered(Exception):

    def __init__(self, messageToDisplay):
        self.messageToDisplay = messageToDisplay

