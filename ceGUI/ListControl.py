"""
Defines classes used for manipulating lists.
"""

import ceGUI
import cx_Exceptions
import datetime
import wx

__all__ = [ "CheckList", "List", "ListBooleanColumn", "ListColumn",
            "ListDateColumn", "ListDecimalColumn", "ListMoneyColumn",
            "ListTimestampColumn", "OrderedList" ]


class List(ceGUI.BaseControl, wx.ListCtrl):
    settingsName = "ColumnWidths"
    dataSetClassName = "DataSet"
    singleSelection = False
    sortByAttrNames = None
    sortOnRetrieve = True
    enableColumnSorting = True

    def __init__(self, parent, style = 0):
        if self.singleSelection:
            style |= wx.LC_SINGLE_SEL
        wx.ListCtrl.__init__(self, parent,
                style = style | wx.LC_REPORT | wx.LC_VIRTUAL)
        parent.BindEvent(self, wx.EVT_LIST_COL_CLICK, self._OnColumnClick,
                createBusyCursor = True)
        parent.BindEvent(self, wx.EVT_SIZE, self._OnResize)
        parent.BindEvent(self, wx.EVT_LIST_COL_END_DRAG, self._OnResize)
        self.ClearAll()
        self._Initialize()
        self._Resize()

    def _AddColumn(self, column):
        """Add a column to the control; note that if the column is right
           justified and the first column in the control, a dummy column is
           added and removed because on Windows, the first column is assumed to
           be left justified, no matter what format is specified."""
        columnIndex = len(self.columns)
        self.columns.append(column)
        self.columnsByAttrName[column.attrName] = column
        self.InsertColumn(columnIndex, column.heading, column.justification,
                column.defaultWidth)
        if columnIndex == 0 and column.justification == wx.LIST_FORMAT_RIGHT:
            self.InsertColumn(columnIndex + 1, column.heading,
                    column.justification, column.defaultWidth)
            self.DeleteColumn(columnIndex)

    def _GetDataSet(self):
        if self.dataSetClassName is not None:
            cls = self._GetClass(self.dataSetClassName)
            return cls(self.config.connection)

    def _GetItemIndexesWithState(self, state):
        itemIndex = -1
        while True:
            itemIndex = self.GetNextItem(itemIndex, state = state)
            if itemIndex < 0:
                break
            yield itemIndex

    def _GetSortKey(self, item, sortColumns):
        return [c.GetSortValue(item) for c in sortColumns]

    def _OnColumnClick(self, event):
        if self.enableColumnSorting:
            column = self.columns[event.GetColumn()]
            self.SortItems(column.attrName)

    def _OnCreate(self):
        self.dataSet = self._GetDataSet()
        super(List, self)._OnCreate()

    def _OnResize(self, event):
        wx.CallAfter(self._Resize)
        event.Skip()

    def _Resize(self):
        """Resize the last column of the control to take up all remaining
           space; note that on Windows this cannot be done during the event
           that caused it as otherwise drawing artifacts remain; on Linux the
           client size of the list control includes the scroll bar but on
           Windows it does not."""
        if not self:
            return
        numColumns = self.GetColumnCount()
        if numColumns:
            width = self.GetClientSize().width
            if wx.Platform == "__WXGTK__":
                x = wx.SystemSettings.GetMetric(wx.SYS_VSCROLL_X)
                if self.GetItemCount() > self.GetCountPerPage():
                    width -= x
            for columnNum in range(numColumns - 1):
                width -= self.GetColumnWidth(columnNum)
            if width > 0:
                self.SetColumnWidth(numColumns - 1, width)
            self.Refresh()

    def _RestoreItemState(self, itemIndexDict, rowHandles, state):
        for handle in rowHandles:
            itemIndex = itemIndexDict[handle]
            self.SetItemState(itemIndex, state, state)

    def _SaveItemState(self, state):
        rowHandles = []
        for itemIndex in self._GetItemIndexesWithState(state):
            self.SetItemState(itemIndex, 0, state)
            rowHandles.append(self.rowHandles[itemIndex])
        return rowHandles

    def AddColumn(self, attrName, heading = "", defaultWidth = -1,
            justification = wx.LIST_FORMAT_LEFT, cls = None):
        if cls is None:
            cls = ListColumn
        column = cls(attrName, heading, defaultWidth, justification)
        self._AddColumn(column)
        return column

    def AppendItem(self, choice = None, refresh = True, item = None):
        return self.InsertItem(len(self.rowHandles), choice, refresh, item)

    def Clear(self):
        self.DeleteAllItems()
        self.rowHandles = []

    def ClearAll(self):
        super(List, self).ClearAll()
        self.Clear()
        self.columns = []
        self.columnsByAttrName = {}
        self.sortByAttrNames = []
        if self.__class__.sortByAttrNames:
            self.sortByAttrNames.extend(self.__class__.sortByAttrNames.split())

    def DeleteItem(self, itemIndex, refresh = True):
        self.SetItemState(itemIndex, 0, wx.LIST_STATE_SELECTED)
        handle = self.rowHandles.pop(itemIndex)
        self.dataSet.DeleteRow(handle)
        self.SetItemCount(len(self.rowHandles))
        if refresh:
            self.Refresh()

    def DeselectAll(self):
        for itemIndex in range(len(self.rowHandles)):
            self.SetItemState(itemIndex, 0, wx.LIST_STATE_SELECTED)

    def ExportItems(self, outputFile, exportHeaders = False):
        if exportHeaders:
            exportValues = self.GetItemExportHeadings()
            print >> outputFile, ",".join(exportValues)
        for item in self.GetItems():
            exportValues = self.GetItemExportValues(item)
            print >> outputFile, ",".join(exportValues)

    def GetInsertChoicesDialog(self, parent):
        pass

    def GetItem(self, itemIndex):
        handle = self.rowHandles[itemIndex]
        return self.dataSet.rows[handle]

    def GetItemExportHeadings(self):
        return [c.GetExportHeading() for c in self.columns]

    def GetItemExportValues(self, item):
        return [c.GetExportValue(item) for c in self.columns]

    def GetItems(self):
        for handle in self.rowHandles:
            yield self.dataSet.rows[handle]

    def GetSelectedItem(self):
        rows = self.GetSelectedItems()
        if len(rows) != 1:
            raise WrongNumberOfRowsSelected()
        return rows[0]

    def GetSelectedItems(self):
        return [self.dataSet.rows[self.rowHandles[i]] \
                for i in self.GetSelectedItemIndexes()]

    def GetSelectedItemIndexes(self):
        return self._GetItemIndexesWithState(wx.LIST_STATE_SELECTED)

    def InsertItem(self, pos = 0, choice = None, refresh = True, item = None):
        handle, row = self.dataSet.InsertRow(choice, item)
        self.rowHandles.insert(pos, handle)
        self.SetItemCount(len(self.rowHandles))
        if refresh:
            self.Refresh()
        return row

    def OnDeleteItems(self):
        for pos, itemIndex in enumerate(self.GetSelectedItemIndexes()):
            self.DeleteItem(itemIndex - pos, refresh = False)
        self.Refresh()

    def OnGetItemText(self, itemIndex, columnIndex):
        handle = self.rowHandles[itemIndex]
        row = self.dataSet.rows[handle]
        column = self.columns[columnIndex]
        value = column.GetValue(row)
        if value is None:
            value = ""
        return value

    def OnInsertItems(self):
        pass

    def PendingChanges(self):
        return self.dataSet.PendingChanges()

    def RefreshFromDataSet(self):
        self.rowHandles = self.dataSet.rows.keys()
        self.SetItemCount(len(self.rowHandles))
        self.Refresh()

    def RestoreColumnWidths(self, settingsName = None):
        if settingsName is None:
            settingsName = self.settingsName
        widths = self.ReadSetting(settingsName, converter = eval)
        if widths is not None and len(widths) == len(self.columns) - 1:
            for columnIndex, width in enumerate(widths):
                self.SetColumnWidth(columnIndex, width)

    def Retrieve(self, *args):
        self.DeleteAllItems()
        self.dataSet.Retrieve(*args)
        self.rowHandles = self.dataSet.rows.keys()
        self.SetItemCount(len(self.rowHandles))
        if self.sortOnRetrieve:
            self.SortItems()

    def SaveColumnWidths(self, settingsName = None):
        if settingsName is None:
            settingsName = self.settingsName
        numColumns = self.GetColumnCount()
        if numColumns > 1:
            widths = [self.GetColumnWidth(i) for i in range(numColumns - 1)]
            self.WriteSetting(settingsName, tuple(widths))

    def SelectAll(self):
        for itemIndex in range(len(self.rowHandles)):
            self.SetItemState(itemIndex, wx.LIST_STATE_SELECTED,
                    wx.LIST_STATE_SELECTED)

    def SelectItems(self, items):
        itemDict = dict([(self.dataSet.rows[h], ix) \
                for ix, h in enumerate(self.rowHandles)])
        for item in items:
            itemIndex = itemDict[item]
            self.SetItemState(itemIndex, wx.LIST_STATE_SELECTED,
                    wx.LIST_STATE_SELECTED)

    def SelectItemsByValue(self, **values):
        for itemIndex, handle in enumerate(self.rowHandles):
            item = self.dataSet.rows[handle]
            itemMatches = True
            for name, value in values.iteritems():
                itemValue = getattr(item, name)
                if itemValue != value:
                    itemMatches = False
                    break
            if itemMatches:
                self.SetItemState(itemIndex, wx.LIST_STATE_SELECTED,
                        wx.LIST_STATE_SELECTED)

    def SetItemValue(self, itemIndex, attrName, value, refresh = True):
        handle = self.rowHandles[itemIndex]
        self.dataSet.SetValue(handle, attrName, value)
        if refresh:
            self.Refresh()

    def SortItems(self, attrName = None, refresh = True):
        if attrName is not None:
            if attrName in self.sortByAttrNames:
                self.sortByAttrNames.remove(attrName)
            self.sortByAttrNames.insert(0, attrName)
        sortColumns = [self.columnsByAttrName[n] for n in self.sortByAttrNames]
        sortColumns.extend([c for c in self.columns if c not in sortColumns])
        focusedState = self._SaveItemState(wx.LIST_STATE_FOCUSED)
        selectedState = self._SaveItemState(wx.LIST_STATE_SELECTED)
        rowDict = self.dataSet.rows
        itemsToSort = [(self._GetSortKey(rowDict[h], sortColumns), h) \
                for h in self.rowHandles]
        itemsToSort.sort()
        self.rowHandles = [i[1] for i in itemsToSort]
        itemIndexDict = dict([(h, i) for i, h in enumerate(self.rowHandles)])
        self._RestoreItemState(itemIndexDict, focusedState,
                wx.LIST_STATE_FOCUSED)
        self._RestoreItemState(itemIndexDict, selectedState,
                wx.LIST_STATE_SELECTED)
        if refresh:
            self.Refresh()

    def Update(self):
        self.dataSet.Update()


class CheckList(List):
    checkedAttrName = "checked"

    def _AddImage(self, flag = 0):
        bitmap = wx.EmptyBitmap(16, 16)
        dc = wx.MemoryDC(bitmap)
        dc.Clear()
        wx.RendererNative.Get().DrawCheckBox(self, dc, (0, 0, 16, 16), flag)
        dc.SelectObject(wx.NullBitmap)
        return self.imageList.Add(bitmap)

    def _OnCreate(self):
        parent = self.GetParent()
        parent.BindEvent(self, wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.imageList = wx.ImageList(16, 16)
        self.uncheckedImageIndex = self._AddImage()
        self.checkedImageIndex = self._AddImage(wx.CONTROL_CHECKED)
        self.SetImageList(self.imageList, wx.IMAGE_LIST_SMALL)
        super(CheckList, self)._OnCreate()

    def _SetAllChecked(self, value):
        for item in self.GetItems():
            setattr(item, self.checkedAttrName, value)

    def CheckAllItems(self):
        self._SetAllChecked(value = True)

    def GetCheckedItems(self):
        for item in self.GetItems():
            checked = getattr(item, self.checkedAttrName)
            if checked:
                yield item

    def OnGetItemImage(self, itemIndex):
        handle = self.rowHandles[itemIndex]
        item = self.dataSet.rows[handle]
        checked = getattr(item, self.checkedAttrName)
        if checked:
            return self.checkedImageIndex
        return self.uncheckedImageIndex

    def OnLeftDown(self, event):
        itemIndex, flags = self.HitTest(event.GetPosition())
        if flags == wx.LIST_HITTEST_ONITEMICON:
            handle = self.rowHandles[itemIndex]
            item = self.dataSet.rows[handle]
            value = getattr(item, self.checkedAttrName)
            setattr(item, self.checkedAttrName, not value)

    def UncheckAllItems(self):
        self._SetAllChecked(value = False)


class OrderedList(List):
    sortOnRetrieve = False
    enableColumnSorting = False

    def MoveItem(self, indexOffset):
        itemIndex, = self.GetSelectedItemIndexes()
        newItemIndex = itemIndex + indexOffset
        handle = self.rowHandles.pop(itemIndex)
        self.rowHandles.insert(newItemIndex, handle)
        self.SetItemState(itemIndex, 0, wx.LIST_STATE_SELECTED)
        self.SetItemState(itemIndex, 0, wx.LIST_STATE_FOCUSED)
        self.SetItemState(newItemIndex, wx.LIST_STATE_SELECTED,
                wx.LIST_STATE_SELECTED)
        self.SetItemState(newItemIndex, wx.LIST_STATE_FOCUSED,
                wx.LIST_STATE_FOCUSED)
        self.Refresh()


class ListColumn(ceGUI.BaseControl):
    defaultJustification = wx.LIST_FORMAT_LEFT
    defaultHeading = ""
    defaultWidth = -1

    def __init__(self, attrName, heading = None, defaultWidth = None,
            justification = None):
        self.attrName = attrName
        self.heading = heading or self.defaultHeading
        self.defaultWidth = defaultWidth or self.defaultWidth
        self.justification = justification or self.defaultJustification
        self._Initialize()

    def __repr__(self):
        return "<%s attrName=%r heading=%r>" % \
                (self.__class__.__name__, self.attrName, self.heading)

    def GetExportHeading(self):
        if self.heading:
            return '"%s"' % self.heading.replace('"', '""')
        return ""

    def GetExportValue(self, row):
        value = getattr(row, self.attrName)
        if isinstance(value, basestring):
            return '"%s"' % value.replace('"', '""')
        elif value is not None:
            return str(value)
        return ""

    def GetSortValue(self, row):
        if self.attrName is None:
            return row
        value = getattr(row, self.attrName)
        if isinstance(value, basestring):
            return value.upper()
        elif isinstance(value, (datetime.datetime, datetime.date)):
            return str(value)
        return value

    def GetValue(self, row):
        if self.attrName is not None:
            value = getattr(row, self.attrName)
            if value is not None and not isinstance(value, basestring):
                return str(value)
            return value
        return row


class ListBooleanColumn(ListColumn):
    defaultJustification = wx.LIST_FORMAT_CENTER

    def GetValue(self, row):
        value = getattr(row, self.attrName)
        if value:
            return "Yes"
        return "No"


class ListDateColumn(ListColumn):
    dateFormatAttrName = "dateFormat"
    dateFormat = None

    def GetValue(self, row):
        value = getattr(row, self.attrName)
        if value is not None:
            dateFormat = self.dateFormat
            if dateFormat is None:
                dateFormat = getattr(self.config, self.dateFormatAttrName)
            return value.strftime(dateFormat)


class ListDecimalColumn(ListColumn):
    defaultJustification = wx.LIST_FORMAT_RIGHT
    digitsAfterDecimal = 2

    def GetValue(self, row):
        value = getattr(row, self.attrName)
        if value is not None:
            format = "%%.%df" % self.digitsAfterDecimal
            return format % value


class ListMoneyColumn(ListDecimalColumn):

    def GetValue(self, row):
        value = getattr(row, self.attrName)
        if value is not None:
            return "$%.2f" % value


class ListTimestampColumn(ListDateColumn):
    dateFormatAttrName = "timestampFormat"


class WrongNumberOfRowsSelected(cx_Exceptions.BaseException):
    message = "Wrong number of rows selected."

