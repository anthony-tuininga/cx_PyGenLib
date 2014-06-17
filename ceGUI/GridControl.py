"""
Defines classes used for manipulating grids.
"""

import ceGUI
import cx_Exceptions
import datetime
import decimal
import wx
import wx.grid

__all__ = [ "Grid", "GridColumn", "GridColumnBool", "GridColumnChoice",
            "GridColumnDate", "GridColumnDecimal", "GridColumnInt",
            "GridColumnStr", "GridTable", "InvalidValueEntered" ]


class Grid(ceGUI.BaseControl, wx.grid.Grid):
    settingsName = "ColumnWidths"
    dataSetClassName = "DataSet"
    enableInsertFromClipboard = True
    customCellAttributes = False
    stripSpacesOnPaste = True
    highlightRowColor = None
    sortOnRetrieve = True
    hideRowLabels = True

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
        self.OnContextMenu()
        self.contextPos = self.contextItem = None

    def _OnCreate(self):
        self.table = self._GetTable()
        self.SetTable(self.table)
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
            readOnly = False, cls = None, required = False,
            contextItem = None, **args):
        if cls is None:
            cls = GridColumn
        if horizontalAlignment is None:
            horizontalAlignment = cls.defaultHorizontalAlignment
        if verticalAlignment is None:
            verticalAlignment = cls.defaultVerticalAlignment
        if contextItem is None:
            contextItem = self.table.dataSet.contextItem
        column = cls(attrName, heading, horizontalAlignment, verticalAlignment,
                readOnly, required, contextItem, **args)
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
        self.ClearGrid()
        self.table.Clear()

    def ClearAll(self):
        self.ClearGrid()
        numCols = self.table.GetNumberCols()
        if numCols > 0:
            msg = wx.grid.GridTableMessage(self.table,
                    wx.grid.GRIDTABLE_NOTIFY_COLS_DELETED, 0, numCols)
            self.ProcessTableMessage(msg)
        self.table.ClearAll()

    def ClearRows(self):
        numRows = self.table.GetNumberRows()
        if numRows > 0:
            msg = wx.grid.GridTableMessage(self.table,
                    wx.grid.GRIDTABLE_NOTIFY_ROWS_DELETED, numRows, numRows)
            self.ProcessTableMessage(msg)

    def CopyToClipboard(self):
        topLeft = self.GetSelectionBlockTopLeft()
        bottomRight = self.GetSelectionBlockBottomRight()
        if topLeft and bottomRight:
            top, left = topLeft[0]
            bottom, right = bottomRight[0]
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
        topLeft = self.GetSelectionBlockTopLeft()
        bottomRight = self.GetSelectionBlockBottomRight()
        if not topLeft:
            row = self.GetRow()
            if row is not None:
                return [row]
            return []
        rows = []
        topLeft.sort()
        bottomRight.sort()
        blockIndex = 0
        for top, left in topLeft:
            bottom, right = bottomRight[blockIndex]
            blockIndex += 1
            rows.extend(self.table.GetRows(top, bottom - top + 1))
        return rows

    def InsertRows(self, pos = None, numRows = 1, choices = None):
        if pos is None:
            if len(self.table.rowHandles) == 0:
                pos = 0
            elif self.contextPos is None:
                pos = self.GetGridCursorRow() + 1
            elif self.contextPos == wx.NOT_FOUND:
                pos = len(self.table.rowHandles)
            else:
                pos = self.contextPos + 1
        if choices is None:
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
        for choiceNum, choice in enumerate(choices):
            row = self.table.InsertRow(pos + choiceNum, choice)
            self.OnInsertRow(row, choice)
        msg = wx.grid.GridTableMessage(self.table,
                wx.grid.GRIDTABLE_NOTIFY_ROWS_APPENDED, len(choices))
        self.ProcessTableMessage(msg)
        self.SetGridCursor(pos, 0)
        self.MakeCellVisible(pos, 0)
        if choices is None and dialog is None:
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
        topLeft = self.GetSelectionBlockTopLeft()
        bottomRight = self.GetSelectionBlockBottomRight()
        selection = bool(topLeft and bottomRight)
        if insert:
            self.InsertRows(numRows = len(data))
            selection = False
        if selection:
            top, left = topLeft[0]
            bottom, right = bottomRight[0]
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
                                and isinstance(value, basestring):
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
        self.ClearRows()
        self.table.RefreshFromDataSet()
        self.OnRetrieve()

    def RestoreColumnWidths(self):
        widths = self.ReadSetting(self.settingsName, converter = eval)
        if widths is not None and len(widths) <= len(self.table.columns):
            for columnIndex, width in enumerate(widths):
                self.SetColSize(columnIndex, width)
            self._Resize()

    def Retrieve(self, *args):
        self.ClearRows()
        self.table.Retrieve(*args)
        self.OnRetrieve()

    def SaveColumnWidths(self):
        numColumns = self.GetNumberCols()
        if numColumns > 1:
            widths = [self.GetColSize(i) for i in range(numColumns - 1)]
            self.WriteSetting(self.settingsName, tuple(widths))

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
                    exc.method = self.EnableCellEditControl
                    colIndex = self.table.columns.index(column)
                    self.SetGridCursor(rowIndex, colIndex)
                    self.MakeCellVisible(rowIndex, colIndex)
                    raise exc

    @property
    def columns(self):
        return self.table.columns


if "phoenix" in wx.version():
    GridTableBase = wx.grid.GridTableBase
else:
    GridTableBase = wx.grid.PyGridTableBase

class GridTable(GridTableBase):

    def __init__(self, dataSet):
        super(GridTable, self).__init__()
        self.dataSet = dataSet
        self.ClearAll()

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

    def ClearAll(self):
        self.columns = []
        self.rowHandles = []
        self.sortByColumnIndexes = []

    def DeleteRows(self, pos = 0, numRows = 1):
        while numRows > 0:
            handle = self.rowHandles[pos]
            self.dataSet.DeleteRow(handle)
            self.rowHandles.pop(pos)
            numRows -= 1

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

    def InsertRow(self, pos, choice):
        handle, row = self.dataSet.InsertRow(choice)
        self.rowHandles.insert(pos, handle)
        return row

    def PendingChanges(self):
        return self.dataSet.PendingChanges()

    def RefreshFromDataSet(self):
        self.rowHandles = self.dataSet.rows.keys()

    def Retrieve(self, *args):
        self.dataSet.Retrieve(*args)
        self.rowHandles = self.dataSet.rows.keys()

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
        except InvalidValueEntered as e:
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
    defaultNumberFormat = "@"

    def __init__(self, attrName, heading, horizontalAlignment,
            verticalAlignment, readOnly, required, contextItem,
            numberFormat = None, **args):
        self.attrName = attrName
        self.heading = heading
        self.required = required
        self.attr = wx.grid.GridCellAttr()
        self.attr.SetAlignment(horizontalAlignment, verticalAlignment)
        self.contextItem = contextItem
        self.numberFormat = numberFormat or self.defaultNumberFormat
        if readOnly:
            self.attr.SetReadOnly()
        self._Initialize()
        self.ExtendedInitialize(**args)

    def ExtendedInitialize(self, **args):
        pass

    def GetLabelValue(self):
        return self.heading

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

    def SetValue(self, grid, dataSet, rowHandle, row, value):
        dataSet.SetValue(rowHandle, self.attrName, value)

    def VerifyValue(self, row):
        if self.required:
            value = getattr(row, self.attrName)
            if value is None:
                return ceGUI.RequiredFieldHasNoValue()

    def VerifyValueOnChange(self, row, rawValue):
        return rawValue


class GridColumnBool(GridColumn):
    defaultHorizontalAlignment = wx.ALIGN_CENTRE

    def OnCreate(self):
        editor = wx.grid.GridCellBoolEditor()
        editor.UseStringValues("1", "0")
        self.attr.SetEditor(editor)
        self.attr.SetRenderer(wx.grid.GridCellBoolRenderer())

    def GetValue(self, row):
        value = getattr(row, self.attrName)
        return str(int(bool(value)))

    def VerifyValueOnChange(self, row, rawValue):
        return bool(int(rawValue))


class GridColumnChoice(GridColumn):
    allowOthers = False

    def OnCreate(self):
        self.RefreshChoices()

    def GetSortValue(self, row):
        value = getattr(row, self.attrName)
        return self.displayValuesByDataValue.get(value, value)

    def GetValue(self, row):
        value = getattr(row, self.attrName)
        displayValue = self.displayValuesByDataValue.get(value, value)
        if displayValue is None:
            return ""
        return displayValue

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
        return self.dataValuesByDisplayValue.get(rawValue, rawValue)


class GridColumnInt(GridColumn):
    defaultHorizontalAlignment = wx.ALIGN_RIGHT

    def OnCreate(self):
        self.attr.SetRenderer(wx.grid.GridCellNumberRenderer())

    def VerifyValueOnChange(self, row, rawValue):
        try:
            return int(rawValue)
        except ValueError:
            message = "'%s' is not a valid integer." % rawValue
            raise InvalidValueEntered(message)


class GridColumnDate(GridColumn):
    defaultHorizontalAlignment = wx.ALIGN_RIGHT
    storeAsString = False

    def ExtendedInitialize(self, dateFormat = None):
        if dateFormat is None:
            dateFormat = self.config.dateFormat
        self.dateFormat = dateFormat
        self.attr.SetEditor(GridColumnDateEditor(self.required))

    def GetValue(self, row):
        value = getattr(row, self.attrName)
        if value is None:
            return ""
        return value.strftime(self.dateFormat)

    def VerifyValueOnChange(self, row, rawValue):
        try:
            return datetime.datetime.strptime(rawValue, self.dateFormat)
        except ValueError:
            message = "'%s' is not a valid date." % rawValue
            raise InvalidValueEntered(message)


class GridColumnDecimal(GridColumn):
    defaultHorizontalAlignment = wx.ALIGN_RIGHT
    storeAsString = False

    def ExtendedInitialize(self, formatString = None, digitsAfterDecimal = 2):
        self.digitsAfterDecimal = digitsAfterDecimal
        if formatString is None:
            formatString = "{0:,.%sf}" % digitsAfterDecimal
        self.formatString = formatString

    def GetValue(self, row):
        value = getattr(row, self.attrName)
        if value is None:
            return ""
        return self.formatString.format(value)

    def VerifyValueOnChange(self, row, rawValue):
        try:
            tweakedValue = rawValue.replace(",", "")
            value = decimal.Decimal(tweakedValue)
            if self.storeAsString:
                value = tweakedValue
            return value
        except decimal.InvalidOperation:
            message = "'%s' is not a valid number." % rawValue
            raise InvalidValueEntered(message)


class GridColumnStr(GridColumn):

    def ExtendedInitialize(self, forceUpper = False, forceLower = False):
        self.forceUpper = forceUpper
        self.forceLower = forceLower

    def VerifyValueOnChange(self, row, rawValue):
        if rawValue and self.forceUpper:
            return rawValue.upper()
        elif rawValue and self.forceLower:
            return rawValue.lower()
        return rawValue


class GridColumnDateEditor(wx.grid.PyGridCellEditor):

    def __init__(self, requiredValue):
        super(GridColumnDateEditor, self).__init__()
        self.requiredValue = requiredValue

    def Create(self, parent, id, evtHandler):
        style = wx.DP_DEFAULT | wx.DP_SHOWCENTURY | wx.DP_DROPDOWN
        if not self.requiredValue:
            style |= wx.DP_ALLOWNONE
        self.control = wx.DatePickerCtrl(parent, id, style = style)
        self.SetControl(self.control)
        self.initialValue = None
 
    def SetSize(self, rect):
        self.control.SetDimensions(rect.x, rect.y, rect.width + 2,
                rect.height + 2, wx.SIZE_ALLOW_MINUS_ONE)
 
    def BeginEdit(self, rowIndex, colIndex, grid):
        self.initialValue = None
        table = grid.GetTable()
        column = table.GetColumn(colIndex)
        initialValue = table.GetValue(rowIndex, colIndex)
        if initialValue:
            dateValue = datetime.datetime.strptime(initialValue,
                    column.dateFormat)
            self.initialValue = wx.DateTimeFromDMY(dateValue.day,
                    dateValue.month - 1, dateValue.year)
            self.control.SetValue(self.initialValue)
        self.control.SetFocus()
 
    def EndEdit(self, rowIndex, colIndex, grid):
        changed = False
        wxDate = self.control.GetValue()
        if wxDate != self.initialValue:
            changed = True
            value = None
            table = grid.GetTable()
            column = table.GetColumn(colIndex)
            if wxDate.IsValid():
                dateValue = datetime.datetime(wxDate.GetYear(),
                        wxDate.GetMonth() + 1, wxDate.GetDay())
                value = dateValue.strftime(column.dateFormat)
            table.SetValue(rowIndex, colIndex, value)
        return changed
 
    def Reset(self):
        if self.initialValue is not None:
            self.control.SetValue(self.initialValue)
 
    def Clone(self):
        return GridColumnDateEditor(self.requiredValue)


class InvalidValueEntered(Exception):

    def __init__(self, messageToDisplay):
        self.messageToDisplay = messageToDisplay


class ReadOnlyCells(cx_Exceptions.BaseException):
    message = "At least some of the cells are read only and cannot be " \
            "modified at this time."

