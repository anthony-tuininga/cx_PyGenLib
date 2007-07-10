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
        self.SetRowLabelSize(0)
        self.SetMargins(0, 0)
        self.DisableDragRowSize()
        parent.BindEvent(self, wx.grid.EVT_GRID_CELL_RIGHT_CLICK,
                self.OnCellRightClick)
        super(Grid, self)._Initialize()

    def AddColumn(self, label, attrName, dataType = str):
        column = GridColumn(label, attrName, dataType)
        self.table.columns.append(column)
        msg = wx.grid.GridTableMessage(self.table,
                wx.grid.GRIDTABLE_NOTIFY_COLS_APPENDED, 1)
        self.ProcessTableMessage(msg)

    def OnCellRightClick(self, event):
        menu = wx.Menu()
        row = event.GetRow()
        insertMenuItem = self._AddMenuItem(menu, "Insert",
                method = functools.partial(self.OnInsertRow, row + 1))
        if not self.table.CanInsertRow():
            insertMenuItem.Enable(False)
        deleteMenuItem = self._AddMenuItem(menu, "Delete",
                method = functools.partial(self.OnDeleteRow, row))
        if not self.table.CanDeleteRow(row):
            deleteMenuItem.Enable(False)
        self._AddMenuItem(menu, "Update", method = self.Update,
                passEvent = False)
        self.PopupMenu(menu)
        menu.Destroy()

    def OnDeleteRow(self, row, event):
        numRows = self.table.GetNumberRows()
        self.DeleteRows(row)
        msg = wx.grid.GridTableMessage(self.table,
                wx.grid.GRIDTABLE_NOTIFY_ROWS_DELETED, numRows, 1)
        self.ProcessTableMessage(msg)

    def OnInsertRow(self, row, event):
        result = self.InsertRows(row)
        self.SetGridCursor(row, 0)
        msg = wx.grid.GridTableMessage(self.table,
                wx.grid.GRIDTABLE_NOTIFY_ROWS_APPENDED, 1)
        self.ProcessTableMessage(msg)

    def Retrieve(self, *args):
        numRows = self.table.GetNumberRows()
        if numRows > 0:
            msg = wx.grid.GridTableMessage(self.table,
                    wx.grid.GRIDTABLE_NOTIFY_ROWS_DELETED, numRows)
            self.ProcessTableMessage(msg)
        self.table.Retrieve(*args)
        numRows = self.table.GetNumberRows()
        msg = wx.grid.GridTableMessage(self.table,
                wx.grid.GRIDTABLE_NOTIFY_ROWS_APPENDED, numRows)
        self.ProcessTableMessage(msg)

    def Update(self):
        self.table.dataSet.Update()


class GridTable(wx.grid.PyGridTableBase):

    def __init__(self, dataSet):
        super(GridTable, self).__init__()
        self.dataSet = dataSet
        self.columns = []
        self.rowHandles = []

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
        self.rowHandles = self.dataSet.rows.keys()

    def SetValue(self, row, col, value):
        attrName = self.columns[col].attrName
        handle = self.rowHandles[row]
        self.dataSet.SetValue(handle, attrName, value)


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

