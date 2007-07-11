"""
Defines classes used for manipulating grids.
"""

import ceGUI
import functools
import wx
import wx.grid

__all__ = ["Grid"]


class Grid(ceGUI.BaseControl, wx.grid.Grid):

    def __init__(self, parent, dataSet):
        wx.grid.Grid.__init__(self, parent)
        self.table = GridTable(dataSet)
        self.SetTable(self.table)
        self._Initialize(parent)

    def _Initialize(self, parent):
        """Note that the margins have to be set to negative pixels in order to
           eliminate the implicit margin that appears to be there otherwise."""
        self.SetRowLabelSize(0)
        self.SetMargins(-10, 0)
        self.DisableDragRowSize()
        parent.BindEvent(self, wx.grid.EVT_GRID_CELL_RIGHT_CLICK,
                self.OnCellRightClick)
        parent.BindEvent(self, wx.EVT_SIZE, self._Resize)
        parent.BindEvent(self, wx.grid.EVT_GRID_COL_SIZE, self._Resize)
        parent.BindEvent(self, wx.grid.EVT_GRID_LABEL_LEFT_CLICK,
                self.OnLabelClicked, skipEvent = False)
        super(Grid, self)._Initialize()

    def _Resize(self, event):
        """Resize the last column of the control to take up all remaining
           space."""
        if not self:
            return
        numColumns = self.GetNumberCols()
        if numColumns:
            width = self.GetClientSize().width
            for columnNum in range(numColumns - 1):
                width -= self.GetColSize(columnNum)
            if width > 0:
                self.SetColSize(numColumns - 1, width)

    def AddColumn(self, label, attrName, dataType = str):
        column = GridColumn(label, attrName, dataType)
        self.table.columns.append(column)
        self.SetColAttr(len(self.table.columns) - 1, column.attr)
        msg = wx.grid.GridTableMessage(self.table,
                wx.grid.GRIDTABLE_NOTIFY_COLS_APPENDED, 1)
        self.ProcessTableMessage(msg)

    def DeleteRows(self, row, numRows = 1):
        currentNumRows = self.table.GetNumberRows()
        wx.grid.Grid.DeleteRows(self, row, numRows)
        msg = wx.grid.GridTableMessage(self.table,
                wx.grid.GRIDTABLE_NOTIFY_ROWS_DELETED, currentNumRows, numRows)
        self.ProcessTableMessage(msg)

    def InsertRows(self, row, numRows = 1):
        wx.grid.Grid.InsertRows(self, row, numRows)
        self.SetGridCursor(row, 0)
        msg = wx.grid.GridTableMessage(self.table,
                wx.grid.GRIDTABLE_NOTIFY_ROWS_APPENDED, numRows)
        self.ProcessTableMessage(msg)

    def OnCellRightClick(self, event):
        menu = wx.Menu()
        row = event.GetRow()
        self._AddMenuItem(menu, "Retrieve", method = self.Retrieve,
                passEvent = False)
        self._AddMenuItem(menu, "Update", method = self.Update,
                passEvent = False)
        menu.AppendSeparator()
        insertMenuItem = self._AddMenuItem(menu, "Insert",
                method = functools.partial(self.InsertRows, row + 1),
                passEvent = False)
        if not self.table.CanInsertRow():
            insertMenuItem.Enable(False)
        deleteMenuItem = self._AddMenuItem(menu, "Delete",
                method = functools.partial(self.DeleteRows, row),
                passEvent = False)
        if not self.table.CanDeleteRow(row):
            deleteMenuItem.Enable(False)
        self.PopupMenu(menu)
        menu.Destroy()

    def OnLabelClicked(self, event):
        self.SortItems(event.GetCol())

    def PendingChanges(self):
        return self.table.dataSet.PendingChanges()

    def RestoreColumnWidths(self):
        widths = self.ReadSetting("ColumnWidths", isComplex = True)
        if widths is not None:
            for columnIndex, width in enumerate(widths):
                self.SetColSize(columnIndex, width)

    def Retrieve(self, *args):
        numRows = self.table.GetNumberRows()
        if numRows > 0:
            msg = wx.grid.GridTableMessage(self.table,
                    wx.grid.GRIDTABLE_NOTIFY_ROWS_DELETED, numRows, numRows)
            self.ProcessTableMessage(msg)
        self.table.Retrieve(*args)
        numRows = self.table.GetNumberRows()
        msg = wx.grid.GridTableMessage(self.table,
                wx.grid.GRIDTABLE_NOTIFY_ROWS_APPENDED, numRows)
        self.ProcessTableMessage(msg)

    def SaveColumnWidths(self):
        numColumns = self.GetNumberCols()
        if numColumns > 1:
            widths = [self.GetColSize(i) for i in range(numColumns - 1)]
            self.WriteSetting("ColumnWidths", tuple(widths), isComplex = True)

    def SortItems(self, columnIndex = None):
        row = self.GetGridCursorRow()
        numRows = self.table.GetNumberRows()
        if row < numRows:
            handle = self.table.rowHandles[row]
            col = self.GetGridCursorCol()
        self.table.SortItems(columnIndex)
        msg = wx.grid.GridTableMessage(self.table,
                wx.grid.GRIDTABLE_REQUEST_VIEW_GET_VALUES)
        self.ProcessTableMessage(msg)
        if row < numRows:
            row = self.table.rowHandles.index(handle)
            self.SetGridCursor(row, col)

    def Update(self):
        self.table.dataSet.Update()


class GridTable(wx.grid.PyGridTableBase):

    def __init__(self, dataSet):
        super(GridTable, self).__init__()
        self.dataSet = dataSet
        self.columns = []
        self.rowHandles = []
        self.sortByColumnIndexes = []

    def AppendRows(self, numRows = 1):
        for rowNum in range(numRows):
            handle, row = self.dataSet.InsertRow()
            self.rowHandles.append(handle)

    def CanDeleteRow(self, row):
        handle = self.rowHandles[row]
        return self.dataSet.CanDeleteRow(handle)

    def CanGetValueAs(self, row, col, typeName):
        return self.columns[col].typeName == typeName

    def CanInsertRow(self):
        return self.dataSet.CanInsertRow()

    def CanSetValueAs(self, row, col, typeName):
        return self.columns[col].typeName == typeName

    def DeleteRows(self, pos = 0, numRows = 1):
        while numRows > 0:
            handle = self.rowHandles[pos]
            self.dataSet.DeleteRow(handle)
            self.rowHandles.pop(pos)
            numRows -= 1

    def GetColLabelValue(self, col):
        return self.columns[col].label

    def GetNumberCols(self):
        return len(self.columns)

    def GetNumberRows(self):
        return len(self.rowHandles)

    def GetTypeName(self, row, col):
        return self.columns[col].typeName

    def GetValue(self, row, col):
        attrName = self.columns[col].attrName
        handle = self.rowHandles[row]
        value = getattr(self.dataSet.rows[handle], attrName)
        if value is None:
            return ""
        return value

    def InsertRows(self, pos = 0, numRows = 1):
        for rowNum in range(numRows):
            handle, row = self.dataSet.InsertRow()
            self.rowHandles.insert(pos + rowNum, handle)

    def Retrieve(self, *args):
        self.dataSet.Retrieve(*args)
        self.SortItems()

    def SetValue(self, row, col, value):
        attrName = self.columns[col].attrName
        handle = self.rowHandles[row]
        self.dataSet.SetValue(handle, attrName, value)

    def SortItems(self, columnIndex = None):
        if columnIndex is not None:
            if columnIndex in self.sortByColumnIndexes:
                self.sortByColumnIndexes.remove(columnIndex)
            self.sortByColumnIndexes.insert(0, columnIndex)
        method = ceGUI.SortRep
        attrNames = [self.columns[i].attrName \
                for i in self.sortByColumnIndexes]
        attrNames.extend([c.attrName for c in self.columns \
                if c.attrName not in attrNames])
        itemsToSort = [([method(getattr(i, n)) for n in attrNames], h) \
                for h, i in self.dataSet.rows.iteritems()]
        itemsToSort.sort()
        self.rowHandles = [i[1] for i in itemsToSort]


class GridColumn(object):
    typeNames = {
            str : wx.grid.GRID_VALUE_STRING,
            bool : wx.grid.GRID_VALUE_BOOL
    }

    def __init__(self, label, attrName, dataType):
        self.label = label
        self.attrName = attrName
        self.dataType = dataType
        self.typeName = self.typeNames[dataType]
        self.attr = wx.grid.GridCellAttr()
        if dataType is bool:
            self.attr.SetAlignment(wx.ALIGN_CENTRE, wx.ALIGN_CENTRE)

