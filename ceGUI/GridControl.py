"""
Defines classes used for manipulating grids.
"""

import ceGUI
import cx_Exceptions
import cx_Logging
import datetime
import decimal
import wx
import wx.adv
import wx.grid

__all__ = [ "Grid", "GridColumn", "GridColumnBool", "GridColumnChoice",
            "GridColumnDate", "GridColumnDecimal", "GridColumnInt",
            "GridColumnStr", "GridTable" ]

# keep old names for classes for backwards compatibility
GridColumn = ceGUI.Column
GridColumnBool = ceGUI.ColumnBool
GridColumnDate = ceGUI.ColumnDate
GridColumnDecimal = ceGUI.ColumnDecimal
GridColumnInt = ceGUI.ColumnInt
GridColumnStr = ceGUI.ColumnStr

class Grid(ceGUI.BaseControl, wx.grid.Grid):
    settingsName = "ColumnWidths"
    dataSetClassName = "DataSet"
    enableInsertFromClipboard = True
    customCellAttributes = False
    stripSpacesOnPaste = True
    highlightRowColor = None
    sortOnRetrieve = True
    hideRowLabels = True
    enablePaste = True
    enableCopy = True

    def __init__(self, parent):
        wx.grid.Grid.__init__(self, parent)
        self._Initialize(parent)

    def _CreateContextMenu(self):
        self.menu = ceGUI.Menu()
        self.refreshMenuItem = self.menu.AddEntry(self, "Refresh\tCtrl-R",
                method = self._OnRefresh, passEvent = False)
        self.updateMenuItem = self.menu.AddEntry(self, "Save\tCtrl-S",
                method = self.Update, passEvent = False)
        self.menu.AddSeparator()
        self.insertMenuItem = self.menu.AddEntry(self, "Insert\tCtrl-I",
                method = self._OnInsert, passEvent = False)
        if self.enableInsertFromClipboard:
            self.insertFromClipboardMenuItem = self.menu.AddEntry(self,
                    "Insert from clipboard",
                    method = self._OnInsertFromClipboard, passEvent = False)
        self.deleteMenuItem = self.menu.AddEntry(self, "Delete\tCtrl-D",
                method = self._OnDelete, passEvent = False)
        self.menu.AddSeparator()
        self.copyMenuItem = self.menu.AddEntry(self, "Copy\tCtrl-C",
                method = self.CopyToClipboard, passEvent = False)
        self.pasteMenuItem = self.menu.AddEntry(self, "Paste\tCtrl-V",
                method = self.PasteFromClipboard, passEvent = False)

    def _GetAccelerators(self):
        return [ ( wx.ACCEL_CTRL, ord('D'), self.deleteMenuItem.GetId() ),
                 ( wx.ACCEL_CTRL, ord('I'), self.insertMenuItem.GetId() ),
                 ( wx.ACCEL_CTRL, ord('R'), self.refreshMenuItem.GetId() ),
                 ( wx.ACCEL_CTRL, ord('S'), self.updateMenuItem.GetId() ),
                 ( wx.ACCEL_CTRL, ord('C'), self.copyMenuItem.GetId() ),
                 ( wx.ACCEL_CTRL, ord('V'), self.pasteMenuItem.GetId() )]

    def _GetDataSet(self):
        cls = self._GetClass(self.dataSetClassName)
        return cls(self.config.dataSource)

    def _GetSelectionBlocks(self):
        topLeft = [(c.GetRow(), c.GetCol()) 
                for c in self.GetSelectionBlockTopLeft()]
        bottomRight = [(c.GetRow(), c.GetCol()) \
                for c in self.GetSelectionBlockBottomRight()]
        blocks = list(zip(topLeft, bottomRight))
        blocks.sort()
        return blocks

    def _GetTable(self):
        dataSet = self._GetDataSet()
        return GridTable(dataSet)

    def _Initialize(self, parent):
        """Note that the margins have to be set to negative pixels in order to
           eliminate the implicit margin that appears to be there otherwise."""
        if self.hideRowLabels:
            self.SetRowLabelSize(0)
            self.SetMargins(-10, 0)
        self.DisableDragRowSize()
        self.BindEvent(self.GetGridWindow(), wx.EVT_RIGHT_DOWN,
                self._OnContextMenu)
        parent.BindEvent(self, wx.EVT_SIZE, self._Resize,
                passEvent = False)
        parent.BindEvent(self, wx.grid.EVT_GRID_COL_SIZE, self._Resize,
                passEvent = False)
        parent.BindEvent(self, wx.grid.EVT_GRID_LABEL_LEFT_CLICK,
                self.OnLabelClicked, skipEvent = False)
        parent.BindEvent(self, wx.grid.EVT_GRID_EDITOR_CREATED,
                self._OnEditorCreated)
        parent.BindEvent(self, wx.grid.EVT_GRID_EDITOR_SHOWN,
                self._OnEditorShown)
        parent.BindEvent(self, wx.grid.EVT_GRID_EDITOR_HIDDEN,
                self._OnEditorHidden)
        super(Grid, self)._Initialize()

    def _OnContextMenu(self, event):
        x, y = self.CalcUnscrolledPosition(event.GetPosition())
        self.contextPos = self.YToRow(y)
        self.contextItem = self.GetRow(self.contextPos)
        insertEnabled = self.CanInsertItems()
        self.insertMenuItem.Enable(insertEnabled)
        if self.enableInsertFromClipboard:
            self.insertFromClipboardMenuItem.Enable(insertEnabled)
        deleteEnabled = self.contextItem is not None \
                and self.CanDeleteItems([self.contextItem])
        self.deleteMenuItem.Enable(deleteEnabled)
        self.copyMenuItem.Enable(self.enableCopy)
        self.pasteMenuItem.Enable(self.enablePaste)
        self.OnContextMenu()
        self.contextPos = self.contextItem = None

    def _OnCreate(self):
        self.table = self._GetTable()
        self.SetTable(self.table, True)
        self._CreateContextMenu()
        accelerators = self._GetAccelerators()
        self.acceleratorTable = wx.AcceleratorTable(accelerators)
        self.SetAcceleratorTable(self.acceleratorTable)
        self.contextPos = self.contextItem = None
        super(Grid, self)._OnCreate()

    def _OnDelete(self):
        if self.contextItem is None:
            pos = self.GetGridCursorRow()
            item = self.GetRow(pos)
        else:
            pos = self.contextPos
            item = self.contextItem
        if not self.CanDeleteItems([item]):
            return
        self.DeleteRows(pos)

    def _OnInsert(self):
        if not self.CanInsertItems():
            return
        self.InsertRows()

    def _OnInsertFromClipboard(self):
        if not self.CanInsertItems():
            return
        self.PasteFromClipboard(insert = True)

    def _OnEditorCreated(self, event):
        column = self.table.GetColumn(event.GetCol())
        if column is not None:
            column.OnEditorCreated(event.GetControl())

    def _OnEditorHidden(self, event):
        column = self.table.GetColumn(event.GetCol())
        row = self.table.GetRow(event.GetRow())
        if column is not None and row is not None:
            column.OnEditorHidden(row)

    def _OnEditorShown(self, event):
        column = self.table.GetColumn(event.GetCol())
        row = self.table.GetRow(event.GetRow())
        if column is not None and row is not None:
            wx.CallAfter(column.OnEditorShown, row)

    def _OnRefresh(self):
        self.Retrieve()

    def _Resize(self):
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

    def AddColumn(self, attrName, heading, defaultWidth = None,
            horizontalAlignment = None, verticalAlignment = None,
            readOnly = False, cls = ceGUI.Column, required = False,
            numberFormat = None, **args):
        column = cls(attrName, heading, defaultWidth, horizontalAlignment,
                verticalAlignment, numberFormat, required, **args)
        column._OnAddToGrid(self, readOnly)
        columnIndex = self.table.GetNumberCols()
        self.table.AddColumn(column)
        self.SetColAttr(columnIndex, column.attr)
        msg = wx.grid.GridTableMessage(self.table,
                wx.grid.GRIDTABLE_NOTIFY_COLS_APPENDED, 1)
        self.ProcessTableMessage(msg)
        if defaultWidth is not None:
            self.SetColSize(columnIndex, defaultWidth)
        return column

    def CanDeleteItems(self, items):
        return True

    def CanInsertItems(self):
        return True

    def Clear(self):
        numRows = self.table.GetNumberRows()
        if numRows > 0:
            msg = wx.grid.GridTableMessage(self.table,
                    wx.grid.GRIDTABLE_NOTIFY_ROWS_DELETED, 0, numRows)
            self.ProcessTableMessage(msg)
            self.table.Clear()

    def ClearAll(self):
        self.Clear()
        numCols = self.table.GetNumberCols()
        if numCols > 0:
            msg = wx.grid.GridTableMessage(self.table,
                    wx.grid.GRIDTABLE_NOTIFY_COLS_DELETED, 0, numCols)
            self.ProcessTableMessage(msg)
            self.table.ClearColumns()

    def CopyToClipboard(self):
        if not self.enableCopy:
            return
        blocks = self._GetSelectionBlocks()
        if blocks:
            (top, left), (bottom, right) = blocks[0]
        else:
            top = bottom = self.GetGridCursorRow()
            left = right = self.GetGridCursorCol()
        columns = list(range(left, right + 1))
        lines = []
        for rowIndex in range(top, bottom + 1):
            line = "\t".join(self.GetCellValue(rowIndex, c) for c in columns)
            lines.append(line)
        dataObject = wx.TextDataObject()
        dataObject.SetText("\n".join(lines))
        wx.TheClipboard.Open()
        wx.TheClipboard.SetData(dataObject)
        wx.TheClipboard.Close()

    def DeleteRows(self, pos = None, numRows = 1):
        if pos is None:
            pos = self.GetGridCursorRow()
        currentNumRows = self.table.GetNumberRows()
        wx.grid.Grid.DeleteRows(self, pos, numRows)
        msg = wx.grid.GridTableMessage(self.table,
                wx.grid.GRIDTABLE_NOTIFY_ROWS_DELETED, currentNumRows, numRows)
        self.ProcessTableMessage(msg)
        return True

    def GetAllRows(self):
        return self.table.GetAllRows()

    def GetInsertChoicesDialog(self, parent):
        pass

    def GetRow(self, pos = None):
        if pos is None:
            pos = self.GetGridCursorRow()
        if pos != wx.NOT_FOUND:
            return self.table.GetRow(pos)

    def GetSelectedRows(self):
        blocks = self._GetSelectionBlocks()
        if not blocks:
            row = self.GetRow()
            if row is not None:
                return [row]
            return []
        rows = []
        for (top, left), (bottom, right) in blocks:
            rows.extend(self.table.GetRows(top, bottom - top + 1))
        return rows

    def AppendRows(self, numRows = 1, choices = None, rows = None):
        pos = len(self.table.rowHandles)
        self.InsertRows(pos, numRows, choices, rows)

    def InsertRows(self, pos = None, numRows = 1, choices = None, rows = None):
        if pos is None:
            if len(self.table.rowHandles) == 0:
                pos = 0
            elif self.contextPos is None:
                pos = self.GetGridCursorRow() + 1
            elif self.contextPos == wx.NOT_FOUND:
                pos = len(self.table.rowHandles)
            else:
                pos = self.contextPos + 1
        if choices is None and rows is None:
            dialog = self.GetInsertChoicesDialog(self.GetParent())
            if dialog is None:
                choices = [None] * numRows
            else:
                if dialog.ShowModalOk():
                    choices = dialog.GetSelectedItems()
                else:
                    choices = []
                dialog.Destroy()
                if not choices:
                    return
        if rows is not None:
            numRows = len(rows)
            for rowNum, row in enumerate(rows):
                self.table.InsertRow(pos + rowNum, row, row)
        else:
            numRows = len(choices)
            for choiceNum, choice in enumerate(choices):
                row = self.table.InsertRow(pos + choiceNum, choice)
                self.OnInsertRow(row, choice)
        msg = wx.grid.GridTableMessage(self.table,
                wx.grid.GRIDTABLE_NOTIFY_ROWS_APPENDED, numRows)
        self.ProcessTableMessage(msg)
        self.SetGridCursor(pos, 0)
        self.MakeCellVisible(pos, 0)
        if choices is None and rows is None and dialog is None:
            self.EnableCellEditControl(True)

    def OnContextMenu(self):
        self.menu.Popup(self)

    def OnGetCustomCellAttributes(self, row, column, attr):
        pass

    def OnInsertRow(self, row, choice):
        pass

    def OnInvalidValueEntered(self, rowIndex, colIndex, rawValue):
        self.SetGridCursor(rowIndex, colIndex)
        self.EnableCellEditControl(True)

    def OnLabelClicked(self, event):
        self.SortItems(event.GetCol())

    def OnRetrieve(self):
        if self.sortOnRetrieve:
            self.table.SortItems()
        numRows = self.table.GetNumberRows()
        msg = wx.grid.GridTableMessage(self.table,
                wx.grid.GRIDTABLE_NOTIFY_ROWS_APPENDED, numRows)
        self.ProcessTableMessage(msg)

    def PasteFromClipboard(self, insert = False):
        if not self.enablePaste:
            return
        dataObject = wx.TextDataObject()
        clipboard = wx.Clipboard()
        clipboard.Open()
        success = clipboard.GetData(dataObject)
        clipboard.Close()
        if not success:
            return
        data = [line.split("\t") for line in dataObject.GetText().splitlines()]
        if not data:
            data = [[""]]
        blocks = self._GetSelectionBlocks()
        selection = bool(blocks)
        if insert:
            self.InsertRows(numRows = len(data))
            selection = False
        if selection:
            (top, left), (bottom, right) = blocks[0]
        else:
            left = self.GetGridCursorCol()
            top = self.GetGridCursorRow()
            bottom = self.GetNumberRows() - 1
            right = self.GetNumberCols() - 1
        rowIndex = top
        while rowIndex <= bottom:
            for row in data:
                colIndex = left
                while colIndex <= right:
                    for value in row:
                        attr = self.table.GetAttr(rowIndex, colIndex)
                        if attr.IsReadOnly():
                            raise ReadOnlyCells()
                        if self.stripSpacesOnPaste \
                                and isinstance(value, str):
                            value = value.strip()
                        self.SetCellValue(rowIndex, colIndex, value)
                        colIndex += 1
                        if colIndex > right:
                            break
                    if not selection:
                        break
                rowIndex += 1
                if rowIndex > bottom:
                    break
            if not selection:
                break

    def PendingChanges(self):
        return self.table.PendingChanges()

    def RefreshEditors(self):
        for column in self.table.columns:
            if isinstance(column, ceGUI.GridColumnChoice):
                column.RefreshChoices()

    def RefreshFromDataSet(self):
        self.Clear()
        self.table.RefreshFromDataSet()
        self.OnRetrieve()

    def RestoreColumnWidths(self, settingsName = None):
        if settingsName is None:
            settingsName = self.settingsName
        widths = self.ReadSetting(settingsName, converter = eval)
        if widths is not None and len(widths) <= len(self.table.columns):
            for columnIndex, width in enumerate(widths):
                self.SetColSize(columnIndex, width)
            self._Resize()

    def Retrieve(self, *args):
        self.Clear()
        self.table.Retrieve(*args)
        self.OnRetrieve()

    def SaveColumnWidths(self, settingsName = None):
        if settingsName is None:
            settingsName = self.settingsName
        numColumns = self.GetNumberCols()
        if numColumns > 1:
            widths = [self.GetColSize(i) for i in range(numColumns - 1)]
            self.WriteSetting(settingsName, tuple(widths))

    def SortItems(self, columnIndex = None):
        col = self.GetGridCursorCol()
        row = self.table.SortItems(columnIndex, self.GetGridCursorRow())
        msg = wx.grid.GridTableMessage(self.table,
                wx.grid.GRIDTABLE_REQUEST_VIEW_GET_VALUES)
        self.ProcessTableMessage(msg)
        self.SetGridCursor(row, col)

    def Update(self):
        self.SaveEditControlValue()
        self.EnableCellEditControl(False)
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
                    exc.method = self.EnableCellEditControl
                    colIndex = self.table.columns.index(column)
                    self.SetGridCursor(rowIndex, colIndex)
                    self.MakeCellVisible(rowIndex, colIndex)
                    raise exc

    @property
    def columns(self):
        return self.table.columns

    @property
    def dataSet(self):
        return self.table.dataSet

    GetItems = GetAllRows
    GetSelectedItems = GetSelectedRows


class GridTable(wx.grid.GridTableBase):

    def __init__(self, dataSet):
        super(GridTable, self).__init__()
        self.dataSet = dataSet
        self.Clear()
        self.ClearColumns()

    def _GetSortKey(self, item, sortByColumns):
        return [c.GetSortValue(item) for c in sortByColumns]

    def AddColumn(self, column):
        self.columns.append(column)

    def AppendRows(self, numRows = 1):
        for rowNum in range(numRows):
            handle, row = self.dataSet.InsertRow()
            self.rowHandles.append(handle)

    def Clear(self):
        self.rowHandles = []

    def ClearColumns(self):
        self.columns = []
        self.sortByColumnIndexes = []

    def DeleteRows(self, pos = 0, numRows = 1):
        while numRows > 0 and pos < len(self.rowHandles):
            handle = self.rowHandles[pos]
            self.dataSet.DeleteRow(handle)
            self.rowHandles.pop(pos)
            numRows -= 1
        return True

    def GetAllRows(self):
        return [self.dataSet.rows[h] for h in self.rowHandles]

    def GetAttr(self, rowIndex, columnIndex, kind = 0):
        grid = self.GetView()
        if grid is None or not grid.customCellAttributes \
                or rowIndex >= len(self.rowHandles) \
                or columnIndex >= len(self.columns):
            return super(GridTable, self).GetAttr(rowIndex, columnIndex, kind)
        column = self.columns[columnIndex]
        attr = column.attr.Clone()
        if grid.highlightRowColor is not None \
                and rowIndex == grid.GetGridCursorRow():
            attr.SetBackgroundColour(grid.highlightRowColor)
        handle = self.rowHandles[rowIndex]
        row = self.dataSet.rows[handle]
        grid.OnGetCustomCellAttributes(row, column, attr)
        return attr

    def GetColLabelValue(self, col):
        if col < len(self.columns):
            column = self.columns[col]
            return column.GetLabelValue()
        return ""

    def GetColumn(self, colIndex):
        if colIndex >= 0 and colIndex < len(self.columns):
            return self.columns[colIndex]

    def GetNumberCols(self):
        return len(self.columns)

    def GetNumberRows(self):
        return len(self.rowHandles)

    def GetRow(self, row):
        if row < len(self.rowHandles):
            handle = self.rowHandles[row]
            return self.dataSet.rows[handle]

    def GetRows(self, startingRow, numRows):
        return [self.dataSet.rows[h] \
                for h in self.rowHandles[startingRow:startingRow + numRows]]

    def GetValue(self, rowIndex, colIndex):
        column = self.columns[colIndex]
        handle = self.rowHandles[rowIndex]
        row = self.dataSet.rows[handle]
        return column.GetValue(row)

    def InsertRow(self, pos, choice, row = None):
        handle, row = self.dataSet.InsertRow(choice, row)
        self.rowHandles.insert(pos, handle)
        return row

    def PendingChanges(self):
        return self.dataSet.PendingChanges()

    def RefreshFromDataSet(self):
        self.rowHandles = list(self.dataSet.rows.keys())

    def Retrieve(self, *args):
        self.dataSet.Retrieve(*args)
        self.rowHandles = list(self.dataSet.rows.keys())

    def SetValue(self, rowIndex, colIndex, rawValue):
        column = self.columns[colIndex]
        handle = self.rowHandles[rowIndex]
        row = self.dataSet.rows[handle]
        grid = self.GetView()
        try:
            if not rawValue:
                value = None
            else:
                value = column.VerifyValueOnChange(row, rawValue)
            column.SetValue(grid, self.dataSet, handle, row, value)
        except ceGUI.InvalidValueEntered as e:
            dialog = wx.MessageDialog(grid.GetParent(), e.messageToDisplay,
                    "Invalid Value", style = wx.OK | wx.ICON_ERROR)
            dialog.ShowModal()
            dialog.Destroy()
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
        self.rowHandles.sort(key = \
                lambda h: self._GetSortKey(rowDict[h], sortByColumns))
        if rowIndex is not None and rowIndex < len(self.rowHandles):
            rowIndex = self.rowHandles.index(handle)
        return rowIndex


class GridColumnChoice(ceGUI.Column):
    displayNativeValue = False
    allowOthers = False

    def GetSortValue(self, row):
        value = self.GetNativeValue(row)
        return self.displayValuesByDataValue.get(value, self.defaultSortValue)

    def GetValue(self, row):
        value = self.GetNativeValue(row)
        try:
            return self.displayValuesByDataValue[value]
        except KeyError:
            if value is None:
                return ""
            elif not isinstance(value, str):
                return str(value)
            return value

    def OnAddToGrid(self, grid):
        self.RefreshChoices()

    def RefreshChoices(self):
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

    def VerifyValueOnChange(self, row, rawValue):
        try:
            return self.dataValuesByDisplayValue[rawValue]
        except KeyError:
            message = "'%s' is not a valid option." % rawValue
            raise ceGUI.InvalidValueEntered(message)


class ReadOnlyCells(cx_Exceptions.BaseException):
    message = "At least some of the cells are read only and cannot be " \
            "modified at this time."

