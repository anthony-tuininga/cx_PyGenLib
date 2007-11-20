"""
Defines classes used for manipulating grids.
"""

import ceGUI
import datetime
import wx
import wx.grid

__all__ = [ "Grid", "GridColumn", "GridColumnBool", "GridColumnChoice",
            "GridColumnInt", "GridColumnStr", "GridTable" ]


class Grid(ceGUI.BaseControl, wx.grid.Grid):
    dataSetClassName = "DataSet"

    def __init__(self, parent):
        wx.grid.Grid.__init__(self, parent)
        self._Initialize(parent)

    def _GetDataSet(self):
        cls = self._GetClass(self.dataSetClassName)
        return cls(self.config.connection)

    def _GetTable(self):
        dataSet = self._GetDataSet()
        return GridTable(dataSet)

    def _Initialize(self, parent):
        """Note that the margins have to be set to negative pixels in order to
           eliminate the implicit margin that appears to be there otherwise."""
        self.SetRowLabelSize(0)
        self.SetMargins(-10, 0)
        self.DisableDragRowSize()
        self.BindEvent(self.GetGridWindow(), wx.EVT_RIGHT_DOWN,
                self.OnContextMenu)
        parent.BindEvent(self, wx.EVT_SIZE, self._Resize)
        parent.BindEvent(self, wx.grid.EVT_GRID_COL_SIZE, self._Resize)
        parent.BindEvent(self, wx.grid.EVT_GRID_LABEL_LEFT_CLICK,
                self.OnLabelClicked, skipEvent = False)
        super(Grid, self)._Initialize()

    def _OnCreate(self):
        self.table = self._GetTable()
        self.SetTable(self.table)
        self.menu = wx.Menu()
        self.retrieveMenuItem = self._AddMenuItem(self.menu, "Retrieve",
                method = self.Retrieve, passEvent = False)
        self.updateMenuItem = self._AddMenuItem(self.menu, "Update",
                method = self.Update, passEvent = False)
        self.menu.AppendSeparator()
        self.insertMenuItem = self._AddMenuItem(self.menu, "Insert",
                method = self._OnInsert)
        self.deleteMenuItem = self._AddMenuItem(self.menu, "Delete",
                method = self._OnDelete)
        accelerators = [
                ( wx.ACCEL_CTRL, ord('D'), self.deleteMenuItem.GetId() ),
                ( wx.ACCEL_CTRL, ord('I'), self.insertMenuItem.GetId() ),
                ( wx.ACCEL_CTRL, ord('R'), self.retrieveMenuItem.GetId() ),
                ( wx.ACCEL_CTRL, ord('S'), self.updateMenuItem.GetId() )
        ]
        self.acceleratorTable = wx.AcceleratorTable(accelerators)
        self.SetAcceleratorTable(self.acceleratorTable)
        self.contextRow = None
        super(Grid, self)._OnCreate()

    def _OnDelete(self, event):
        if self.contextRow is None:
            row = self.GetGridCursorRow()
        else:
            row = self.contextRow
        self.DeleteRows(row)

    def _OnInsert(self, event):
        if self.contextRow is None:
            row = self.GetGridCursorRow()
        elif self.contextRow == wx.NOT_FOUND:
            row = len(self.table.rowHandles)
        else:
            row = self.contextRow
        self.InsertRows(row + 1)

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

    def AddColumn(self, cls, *args, **kwargs):
        column = cls(*args, **kwargs)
        self.table.AddColumn(column)
        columnIndex = self.table.GetNumberCols() - 1
        self.SetColAttr(columnIndex, column.attr)
        msg = wx.grid.GridTableMessage(self.table,
                wx.grid.GRIDTABLE_NOTIFY_COLS_APPENDED, 1)
        self.ProcessTableMessage(msg)

    def DeleteRows(self, row, numRows = 1):
        currentNumRows = self.table.GetNumberRows()
        wx.grid.Grid.DeleteRows(self, row, numRows)
        msg = wx.grid.GridTableMessage(self.table,
                wx.grid.GRIDTABLE_NOTIFY_ROWS_DELETED, currentNumRows, numRows)
        self.ProcessTableMessage(msg)

    def GetAllRows(self):
        return self.table.GetAllRows()

    def GetCurrentRow(self):
        row = self.GetGridCursorRow()
        return self.table.GetRow(row)

    def GetInsertChoicesDialog(self, parent):
        pass

    def InsertRows(self, row, numRows = 1):
        dialog = self.GetInsertChoicesDialog(self.GetParent())
        if dialog is None:
            choices = [None] * numRows
        elif dialog.ShowModal() != wx.ID_OK:
            return
        else:
            choices = dialog.GetSelectedItems()
        self.table.InsertRows(row, choices)
        msg = wx.grid.GridTableMessage(self.table,
                wx.grid.GRIDTABLE_NOTIFY_ROWS_APPENDED, len(choices))
        self.ProcessTableMessage(msg)
        self.SetGridCursor(row, 0)
        self.MakeCellVisible(row, 0)

    def OnContextMenu(self, event):
        x, y = self.CalcUnscrolledPosition(event.GetPosition())
        self.contextRow = self.YToRow(y)
        self.insertMenuItem.Enable(self.table.CanInsertRow())
        deleteEnabled = self.contextRow != wx.NOT_FOUND \
                and self.table.CanDeleteRow(self.contextRow)
        self.deleteMenuItem.Enable(deleteEnabled)
        self.PopupMenu(self.menu)
        self.contextRow = None

    def OnInvalidValueEntered(self, rowIndex, colIndex, rawValue):
        self.SetGridCursor(rowIndex, colIndex)
        self.EnableCellEditControl(True)

    def OnLabelClicked(self, event):
        self.SortItems(event.GetCol())

    def PendingChanges(self):
        return self.table.PendingChanges()

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
        col = self.GetGridCursorCol()
        row = self.table.SortItems(columnIndex, self.GetGridCursorRow())
        msg = wx.grid.GridTableMessage(self.table,
                wx.grid.GRIDTABLE_REQUEST_VIEW_GET_VALUES)
        self.ProcessTableMessage(msg)
        self.SetGridCursor(row, col)

    def Update(self):
        self.SaveEditControlValue()
        self.table.dataSet.Update()
        self.Refresh()


class GridTable(wx.grid.PyGridTableBase):

    def __init__(self, dataSet):
        super(GridTable, self).__init__()
        self.dataSet = dataSet
        self.columns = []
        self.rowHandles = []
        self.sortByColumnIndexes = []

    def _GetSortKey(self, item, sortByColumns):
        return [c.GetSortValue(item) for c in sortByColumns]

    def AddColumn(self, column):
        self.columns.append(column)

    def AppendRows(self, numRows = 1):
        for rowNum in range(numRows):
            handle, row = self.dataSet.InsertRow()
            self.rowHandles.append(handle)

    def CanDeleteRow(self, row):
        handle = self.rowHandles[row]
        return self.dataSet.CanDeleteRow(handle)

    def CanInsertRow(self):
        return self.dataSet.CanInsertRow()

    def DeleteRows(self, pos = 0, numRows = 1):
        while numRows > 0:
            handle = self.rowHandles[pos]
            self.dataSet.DeleteRow(handle)
            self.rowHandles.pop(pos)
            numRows -= 1

    def GetAllRows(self):
        return [self.dataSet.rows[h] for h in self.rowHandles]

    def GetColLabelValue(self, col):
        return self.columns[col].label

    def GetNumberCols(self):
        return len(self.columns)

    def GetNumberRows(self):
        return len(self.rowHandles)

    def GetRow(self, row):
        if row < len(self.rowHandles):
            handle = self.rowHandles[row]
            return self.dataSet.rows[handle]

    def GetValue(self, row, col):
        column = self.columns[col]
        handle = self.rowHandles[row]
        row = self.dataSet.rows[handle]
        return column.GetValue(row)

    def InsertRows(self, pos = 0, choices = [None]):
        for rowNum, choice in enumerate(choices):
            handle, row = self.dataSet.InsertRow(choice)
            self.rowHandles.insert(pos + rowNum, handle)

    def PendingChanges(self):
        return self.dataSet.PendingChanges()

    def Retrieve(self, *args):
        self.dataSet.Retrieve(*args)
        self.rowHandles = self.dataSet.rows.keys()
        self.SortItems()

    def SetValue(self, rowIndex, colIndex, rawValue):
        column = self.columns[colIndex]
        handle = self.rowHandles[rowIndex]
        row = self.dataSet.rows[handle]
        grid = self.GetView()
        if not column.SetValue(grid, self.dataSet, handle, row, rawValue):
            wx.CallAfter(grid.OnInvalidValueEntered, rowIndex, colIndex,
                    rawValue)

    def SortItems(self, columnIndex = None, rowIndex = None):
        if rowIndex is not None and rowIndex < len(self.rowHandles):
            handle = self.rowHandles[rowIndex]
        if columnIndex is not None:
            if columnIndex in self.sortByColumnIndexes:
                self.sortByColumnIndexes.remove(columnIndex)
            self.sortByColumnIndexes.insert(0, columnIndex)
        sortByColumns = [self.columns[i] for i in self.sortByColumnIndexes]
        sortByColumns.extend([c for c in self.columns \
                if c not in sortByColumns])
        rowDict = self.dataSet.rows
        itemsToSort = [(self._GetSortKey(rowDict[h], sortByColumns), h) \
                for h in self.rowHandles]
        itemsToSort.sort()
        self.rowHandles = [i[1] for i in itemsToSort]
        if rowIndex is not None and rowIndex < len(self.rowHandles):
            rowIndex = self.rowHandles.index(handle)
        return rowIndex


class GridColumn(ceGUI.BaseControl):

    def __init__(self, label, attrName, readOnly = False):
        self.label = label
        self.attrName = attrName
        self.attr = wx.grid.GridCellAttr()
        if readOnly:
            self.attr.SetReadOnly()
        self._Initialize()

    def GetSortValue(self, row):
        value = getattr(row, self.attrName)
        if isinstance(value, basestring):
            return value.upper()
        elif isinstance(value, (datetime.datetime, datetime.date)):
            return str(value)
        return value

    def GetValue(self, row):
        value = getattr(row, self.attrName)
        if value is None:
            return ""
        return str(value)

    def SetValue(self, grid, dataSet, rowHandle, row, rawValue):
        if rawValue:
            value = rawValue
        else:
            value = None
        dataSet.SetValue(rowHandle, self.attrName, value)
        return True


class GridColumnBool(GridColumn):

    def __init__(self, label, attrName, readOnly = False):
        super(GridColumnBool, self).__init__(label, attrName, readOnly)
        editor = wx.grid.GridCellBoolEditor()
        editor.UseStringValues("1", "0")
        self.attr.SetEditor(editor)
        self.attr.SetAlignment(wx.ALIGN_CENTRE, wx.ALIGN_CENTRE)
        self.attr.SetRenderer(wx.grid.GridCellBoolRenderer())

    def GetValue(self, row):
        value = getattr(row, self.attrName)
        return str(int(value))

    def SetValue(self, grid, dataSet, rowHandle, row, rawValue):
        value = bool(int(rawValue))
        dataSet.SetValue(rowHandle, self.attrName, value)
        return True


class GridColumnChoice(GridColumn):

    def __init__(self, label, attrName, choices, readOnly = False):
        super(GridColumnChoice, self).__init__(label, attrName, readOnly)
        displayValues = []
        self.dataValuesByDisplayValue = {}
        self.displayValuesByDataValue = {}
        for choice in choices:
            if isinstance(choice, tuple):
                dataValue, displayValue = choice
            else:
                dataValue = displayValue = choice
            displayValues.append(displayValue)
            self.dataValuesByDisplayValue[displayValue] = dataValue
            self.displayValuesByDataValue[dataValue] = displayValue
        editor = wx.grid.GridCellChoiceEditor(displayValues)
        self.attr.SetEditor(editor)

    def GetSortValue(self, row):
        value = getattr(row, self.attrName)
        return self.displayValuesByDataValue[value]

    def GetValue(self, row):
        value = getattr(row, self.attrName)
        return self.displayValuesByDataValue[value]

    def SetValue(self, grid, dataSet, rowHandle, row, rawValue):
        value = self.dataValuesByDisplayValue[rawValue]
        dataSet.SetValue(rowHandle, self.attrName, value)
        return True


class GridColumnInt(GridColumn):

    def __init__(self, label, attrName, readOnly = False, min = -1, max = -1):
        super(GridColumnInt, self).__init__(label, attrName, readOnly)
        editor = wx.grid.GridCellNumberEditor(min, max)
        self.attr.SetEditor(editor)
        self.attr.SetRenderer(wx.grid.GridCellNumberRenderer())

    def SetValue(self, grid, dataSet, rowHandle, row, rawValue):
        if rawValue:
            value = int(rawValue)
        else:
            value = None
        dataSet.SetValue(rowHandle, self.attrName, value)
        return True


class GridColumnStr(GridColumn):
    pass

