"""
Defines classes used for manipulating lists.
"""

import ceGUI
import cx_Exceptions
import wx

__all__ = [ "CheckList", "List", "ListColumn", "ListBooleanColumn",
            "ListDateColumn", "ListDecimalColumn", "ListMoneyColumn",
            "ListTimestampColumn", "OrderedList" ]

# keep old names for classes for backwards compatibility
ListColumn = ceGUI.Column
ListBooleanColumn = ceGUI.ColumnBool
ListDateColumn = ceGUI.ColumnDate
ListDecimalColumn = ceGUI.ColumnDecimal
ListMoneyColumn = ceGUI.ColumnMoney
ListTimestampColumn = ceGUI.ColumnTimestamp

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

    def _GetDataSet(self):
        if self.dataSetClassName is not None:
            cls = self._GetClass(self.dataSetClassName)
            return cls(self.config.dataSource)

    def _GetItemIndexesWithState(self, state):
        itemIndex = -1
        while True:
            itemIndex = self.GetNextItem(itemIndex, state = state)
            if itemIndex < 0:
                break
            yield itemIndex

    def _GetSortKey(self, item, sortColumns):
        return [c.GetSortValue(item) for c in sortColumns]

    def _InsertItem(self, pos, choice, item, refresh, ensureVisible):
        handle, row = self.dataSet.InsertRow(choice, item)
        self.rowHandles.insert(pos, handle)
        self.SetItemCount(len(self.rowHandles))
        if ensureVisible:
            self.EnsureVisible(pos)
        if refresh:
            self.Refresh()
        return row

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

    def AddColumn(self, attrName, heading = None, defaultWidth = None,
            cls = ceGUI.Column, rightJustified = False, centered = False,
            numberFormat = None, **args):
        horizontalAlignment = None
        if rightJustified:
            horizontalAlignment = "right"
        elif centered:
            horizontalAlignment = "center"
        column = cls(attrName, heading, defaultWidth, horizontalAlignment,
                numberFormat = numberFormat, **args)
        columnIndex = len(self.columns)
        self.columns.append(column)
        self.columnsByAttrName[column.attrName] = column
        column._OnAddToList(self, columnIndex)
        return column

    def AppendItem(self, choice = None, refresh = True, item = None,
            ensureVisible = False):
        return self._InsertItem(len(self.rowHandles), choice, item, refresh,
                ensureVisible)

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
            print(",".join(exportValues), file = outputFile)
        for item in self.GetItems():
            exportValues = self.GetItemExportValues(item)
            print(",".join(exportValues), file = outputFile)

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

    def InsertItem(self, pos = 0, choice = None, refresh = True, item = None,
            ensureVisible = False):
        return self._InsertItem(pos, choice, item, refresh, ensureVisible)

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
        self.rowHandles = list(self.dataSet.rows.keys())
        self.SetItemCount(len(self.rowHandles))
        self.Refresh()
        if self.sortOnRetrieve:
            self.SortItems()

    def RestoreColumnWidths(self, settingsName = None):
        if settingsName is None:
            settingsName = self.settingsName
        widths = self.ReadSetting(settingsName, converter = eval)
        if widths is not None and len(widths) == len(self.columns) - 1:
            for columnIndex, width in enumerate(widths):
                self.SetColumnWidth(columnIndex, width)

    def Retrieve(self, *args):
        with ceGUI.BusyCursorContext(parent = self.GetParent()):
            self.DeleteAllItems()
            self.dataSet.Retrieve(*args)
            self.rowHandles = list(self.dataSet.rows.keys())
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

    def SelectItem(self, item, ensureVisible = False):
        self.SelectItems([item], ensureVisible = ensureVisible)

    def SelectItems(self, items, ensureVisible = False):
        itemDict = dict([(self.dataSet.rows[h], ix) \
                for ix, h in enumerate(self.rowHandles)])
        for item in items:
            itemIndex = itemDict[item]
            self.SetItemState(itemIndex, wx.LIST_STATE_SELECTED,
                    wx.LIST_STATE_SELECTED)
        if ensureVisible and items:
            itemIndex = itemDict[items[-1]]
            self.EnsureVisible(itemIndex)

    def SelectItemsByValue(self, **values):
        for itemIndex, handle in enumerate(self.rowHandles):
            item = self.dataSet.rows[handle]
            itemMatches = True
            for name, value in values.items():
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

    def SetSingleSelection(self, singleSelection = True):
        self.SetSingleStyle(wx.LC_SINGLE_SEL, add = singleSelection)

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
        self.rowHandles.sort(key = lambda h: \
                self._GetSortKey(rowDict[h], sortColumns))
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
    seqNumAttrName = "seqNum"

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

    def SetSeqNumValues(self):
        for seqNum, handle in enumerate(self.rowHandles):
            self.dataSet.SetValue(handle, self.seqNumAttrName, seqNum + 1)

    def Update(self):
        self.SetSeqNumValues()
        super(OrderedList, self).Update()


class WrongNumberOfRowsSelected(cx_Exceptions.BaseException):
    message = "Wrong number of rows selected."

