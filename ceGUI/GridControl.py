"""
Defines classes used for manipulating grids.
"""

import ceGUI
import datetime
import wx
import wx.grid

__all__ = [ "Grid", "GridColumn", "GridColumnBool", "GridColumnChoice",
            "GridColumnDecimal", "GridColumnInt", "GridColumnStr", "GridTable",
            "InvalidValueEntered" ]


class Grid(ceGUI.BaseControl, wx.grid.Grid):
    dataSetClassName = "DataSet"
    sortOnRetrieve = True

    def __init__(self, parent):
        wx.grid.Grid.__init__(self, parent)
        self._Initialize(parent)

    def _CreateContextMenu(self):
        self.menu = ceGUI.Menu()
        self.refreshMenuItem = self.menu.AddEntry(self, "Refresh\tCtrl-R",
                method = self.Retrieve, passEvent = False)
        self.updateMenuItem = self.menu.AddEntry(self, "Save\tCtrl-S",
                method = self.Update, passEvent = False)
        self.menu.AddSeparator()
        self.insertMenuItem = self.menu.AddEntry(self, "Insert\tCtrl-I",
                method = self._OnInsert, passEvent = False)
        self.deleteMenuItem = self.menu.AddEntry(self, "Delete\tCtrl-D",
                method = self._OnDelete, passEvent = False)

    def _GetAccelerators(self):
        return [ ( wx.ACCEL_CTRL, ord('D'), self.deleteMenuItem.GetId() ),
                 ( wx.ACCEL_CTRL, ord('I'), self.insertMenuItem.GetId() ),
                 ( wx.ACCEL_CTRL, ord('R'), self.refreshMenuItem.GetId() ),
                 ( wx.ACCEL_CTRL, ord('S'), self.updateMenuItem.GetId() ) ]

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
                self._OnContextMenu)
        parent.BindEvent(self, wx.EVT_SIZE, self._Resize)
        parent.BindEvent(self, wx.grid.EVT_GRID_COL_SIZE, self._Resize)
        parent.BindEvent(self, wx.grid.EVT_GRID_LABEL_LEFT_CLICK,
                self.OnLabelClicked, skipEvent = False)
        super(Grid, self)._Initialize()

    def _OnContextMenu(self, event):
        x, y = self.CalcUnscrolledPosition(event.GetPosition())
        self.contextRow = self.YToRow(y)
        self.insertMenuItem.Enable(self.table.CanInsertRow())
        deleteEnabled = self.contextRow != wx.NOT_FOUND \
                and self.table.CanDeleteRow(self.contextRow)
        self.deleteMenuItem.Enable(deleteEnabled)
        self.OnContextMenu()
        self.contextRow = None

    def _OnCreate(self):
        self.table = self._GetTable()
        self.SetTable(self.table)
        self._CreateContextMenu()
        accelerators = self._GetAccelerators()
        self.acceleratorTable = wx.AcceleratorTable(accelerators)
        self.SetAcceleratorTable(self.acceleratorTable)
        self.contextRow = None
        super(Grid, self)._OnCreate()

    def _OnDelete(self):
        if self.contextRow is None:
            row = self.GetGridCursorRow()
        else:
            row = self.contextRow
        if not self.table.CanDeleteRow(row):
            return
        self.DeleteRows(row)

    def _OnInsert(self):
        if not self.table.CanInsertRow():
            return
        if self.contextRow is None:
            row = self.GetGridCursorRow() + 1
        elif self.contextRow == wx.NOT_FOUND:
            row = len(self.table.rowHandles) + 1
        else:
            row = self.contextRow + 1
        if len(self.table.rowHandles) == 0:
            row = 0
        self.InsertRows(row)

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

    def AddColumn(self, attrName, label, defaultWidth = None,
            horizontalAlignment = None, verticalAlignment = None,
            readOnly = False, cls = None, required = False,
            contextItem = None):
        if cls is None:
            cls = GridColumn
        if horizontalAlignment is None:
            horizontalAlignment = cls.defaultHorizontalAlignment
        if verticalAlignment is None:
            verticalAlignment = cls.defaultVerticalAlignment
        if contextItem is None:
            contextItem = self.table.dataSet.contextItem
        column = cls(attrName, label, horizontalAlignment, verticalAlignment,
                readOnly, required, contextItem)
        columnIndex = self.table.GetNumberCols()
        self.table.AddColumn(column)
        self.SetColAttr(columnIndex, column.attr)
        msg = wx.grid.GridTableMessage(self.table,
                wx.grid.GRIDTABLE_NOTIFY_COLS_APPENDED, 1)
        self.ProcessTableMessage(msg)
        if defaultWidth is not None:
            self.SetColSize(columnIndex, defaultWidth)
        return column

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
        if row >= 0:
            return self.table.GetRow(row)

    def GetInsertChoicesDialog(self, parent):
        pass

    def InsertRows(self, row, numRows = 1):
        dialog = self.GetInsertChoicesDialog(self.GetParent())
        if dialog is None:
            choices = [None] * numRows
        else:
            if dialog.ShowModal() == wx.ID_OK:
                choices = dialog.GetSelectedItems()
            else:
                choices = []
            dialog.Destroy()
            if not choices:
                return
        self.table.InsertRows(row, choices)
        msg = wx.grid.GridTableMessage(self.table,
                wx.grid.GRIDTABLE_NOTIFY_ROWS_APPENDED, len(choices))
        self.ProcessTableMessage(msg)
        self.SetGridCursor(row, 0)
        self.MakeCellVisible(row, 0)
        if dialog is None:
            self.EnableCellEditControl(True)

    def OnContextMenu(self):
        self.menu.Popup(self)

    def OnInvalidValueEntered(self, rowIndex, colIndex, rawValue):
        self.SetGridCursor(rowIndex, colIndex)
        self.EnableCellEditControl(True)

    def OnLabelClicked(self, event):
        self.SortItems(event.GetCol())

    def PendingChanges(self):
        return self.table.PendingChanges()

    def RestoreColumnWidths(self):
        widths = self.ReadSetting("ColumnWidths", converter = eval)
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
        if self.sortOnRetrieve:
            self.table.SortItems()
        numRows = self.table.GetNumberRows()
        msg = wx.grid.GridTableMessage(self.table,
                wx.grid.GRIDTABLE_NOTIFY_ROWS_APPENDED, numRows)
        self.ProcessTableMessage(msg)

    def SaveColumnWidths(self):
        numColumns = self.GetNumberCols()
        if numColumns > 1:
            widths = [self.GetColSize(i) for i in range(numColumns - 1)]
            self.WriteSetting("ColumnWidths", tuple(widths))

    def SortItems(self, columnIndex = None):
        col = self.GetGridCursorCol()
        row = self.table.SortItems(columnIndex, self.GetGridCursorRow())
        msg = wx.grid.GridTableMessage(self.table,
                wx.grid.GRIDTABLE_REQUEST_VIEW_GET_VALUES)
        self.ProcessTableMessage(msg)
        self.SetGridCursor(row, col)

    def Update(self):
        self.SaveEditControlValue()
        self.VerifyData()
        self.table.dataSet.Update()
        self.Refresh()

    def VerifyData(self):
        dataSet = self.table.dataSet
        for rowIndex, handle in enumerate(self.table.rowHandles):
            row = dataSet.rows[handle]
            for column in self.table.columns:
                exc = column.VerifyValue(row)
                if exc is not None:
                    colIndex = self.table.columns.index(column)
                    self.SetGridCursor(rowIndex, colIndex)
                    self.MakeCellVisible(rowIndex, colIndex)
                    self.EnableCellEditControl()
                    raise exc


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

    def SetValue(self, rowIndex, colIndex, rawValue):
        column = self.columns[colIndex]
        handle = self.rowHandles[rowIndex]
        row = self.dataSet.rows[handle]
        grid = self.GetView()
        try:
            validValue = column.SetValue(grid, self.dataSet, handle, row,
                    rawValue)
        except InvalidValueEntered, e:
            validValue = False
            dialog = wx.MessageDialog(grid.GetParent(), e.messageToDisplay,
                    "Invalid Value", style = wx.OK | wx.ICON_ERROR)
            dialog.ShowModal()
            dialog.Destroy()
        if not validValue:
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
    defaultHorizontalAlignment = wx.ALIGN_LEFT
    defaultVerticalAlignment = wx.ALIGN_CENTRE

    def __init__(self, attrName, label, horizontalAlignment,
            verticalAlignment, readOnly, required, contextItem):
        self.attrName = attrName
        self.label = label
        self.required = required
        self.attr = wx.grid.GridCellAttr()
        self.attr.SetAlignment(horizontalAlignment, verticalAlignment)
        self.contextItem = contextItem
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
        elif isinstance(value, basestring):
            return value
        return str(value)

    def SetValue(self, grid, dataSet, rowHandle, row, rawValue):
        if rawValue:
            value = rawValue
        else:
            value = None
        dataSet.SetValue(rowHandle, self.attrName, value)
        return True

    def VerifyValue(self, row):
        if self.required:
            value = getattr(row, self.attrName)
            if value is None:
                return ceGUI.RequiredFieldHasNoValue()


class GridColumnBool(GridColumn):
    defaultHorizontalAlignment = wx.ALIGN_CENTRE

    def OnCreate(self):
        editor = wx.grid.GridCellBoolEditor()
        editor.UseStringValues("1", "0")
        self.attr.SetEditor(editor)
        self.attr.SetRenderer(wx.grid.GridCellBoolRenderer())

    def GetValue(self, row):
        value = getattr(row, self.attrName)
        return str(int(value))

    def SetValue(self, grid, dataSet, rowHandle, row, rawValue):
        value = bool(int(rawValue))
        dataSet.SetValue(rowHandle, self.attrName, value)
        return True


class GridColumnChoice(GridColumn):
    allowOthers = False

    def OnCreate(self):
        displayValues = []
        self.dataValuesByDisplayValue = {}
        self.displayValuesByDataValue = {}
        for choice in self.GetChoices():
            if isinstance(choice, tuple):
                dataValue, displayValue = choice
            else:
                dataValue = displayValue = choice
            displayValues.append(displayValue)
            self.dataValuesByDisplayValue[displayValue] = dataValue
            self.displayValuesByDataValue[dataValue] = displayValue
        editor = wx.grid.GridCellChoiceEditor(displayValues,
                allowOthers = self.allowOthers)
        self.attr.SetEditor(editor)

    def GetSortValue(self, row):
        value = getattr(row, self.attrName)
        return self.displayValuesByDataValue.get(value, value)

    def GetValue(self, row):
        value = getattr(row, self.attrName)
        return self.displayValuesByDataValue.get(value, value)

    def SetValue(self, grid, dataSet, rowHandle, row, rawValue):
        value = self.dataValuesByDisplayValue.get(rawValue, rawValue)
        dataSet.SetValue(rowHandle, self.attrName, value)
        return True


class GridColumnInt(GridColumn):
    defaultHorizontalAlignment = wx.ALIGN_RIGHT

    def OnCreate(self):
        self.attr.SetRenderer(wx.grid.GridCellNumberRenderer())

    def SetValue(self, grid, dataSet, rowHandle, row, rawValue):
        if rawValue:
            try:
                value = int(rawValue)
            except ValueError:
                message = "'%s' is not a valid integer." % rawValue
                raise InvalidValueEntered(message)
        else:
            value = None
        dataSet.SetValue(rowHandle, self.attrName, value)
        return True


class GridColumnDecimal(GridColumn):
    defaultHorizontalAlignment = wx.ALIGN_RIGHT
    storeAsString = False

    def SetValue(self, grid, dataSet, rowHandle, row, rawValue):
        import decimal
        if rawValue:
            try:
                value = decimal.Decimal(rawValue)
            except decimal.InvalidOperation:
                message = "'%s' is not a valid number." % rawValue
                raise InvalidValueEntered(message)
            if self.storeAsString:
                value = rawValue
        else:
            value = None
        dataSet.SetValue(rowHandle, self.attrName, value)
        return True


class GridColumnStr(GridColumn):
    pass


class InvalidValueEntered(Exception):

    def __init__(self, messageToDisplay):
        self.messageToDisplay = messageToDisplay

