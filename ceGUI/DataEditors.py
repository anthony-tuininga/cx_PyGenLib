"""
Define windows used for editing data.
"""

import ceGUI
import cx_Exceptions
import cx_Logging
import functools
import os
import wx

__all__ = [ "DataList", "DataListPanel", "EditDialog", "GridEditWindow",
            "SubWindow" ]


class DataList(ceGUI.List):
    createContextMenu = True
    singleSelection = True

    def _CreateContextMenu(self):
        self.menu = wx.Menu()
        self.refreshMenuItem = self._AddMenuItem(self.menu,
                "Refresh\tCtrl-R", method = self.OnRefresh, passEvent = False)
        self.menu.AppendSeparator()
        self.insertMenuItem = self._AddMenuItem(self.menu,
                "Insert\tCtrl-I", method = self.OnInsertItems,
                passEvent = False)
        self.editMenuItem = self._AddMenuItem(self.menu,
                "Edit\tCtrl-E", method = self.OnEditItem,
                passEvent = False)
        self.deleteMenuItem = self._AddMenuItem(self.menu,
                "Delete\tCtrl-D", method = self.OnDeleteItems,
                passEvent = False)

    def _GetAccelerators(self):
        return [ ( wx.ACCEL_CTRL, ord('D'), self.deleteMenuItem.GetId() ),
                 ( wx.ACCEL_CTRL, ord('I'), self.insertMenuItem.GetId() ),
                 ( wx.ACCEL_CTRL, ord('E'), self.editMenuItem.GetId() ),
                 ( wx.ACCEL_CTRL, ord('R'), self.refreshMenuItem.GetId() ) ]

    def _OnCreate(self):
        super(DataList, self)._OnCreate()
        self._CreateContextMenu()
        accelerators = self._GetAccelerators()
        self.acceleratorTable = wx.AcceleratorTable(accelerators)
        self.SetAcceleratorTable(self.acceleratorTable)
        self.contextRow = None
        parent = self.GetParent()
        parent.BindEvent(self, wx.EVT_CONTEXT_MENU, self.OnContextMenu)

    def CanDeleteItems(self, items):
        return True

    def CanEditItem(self, item):
        parent = self.GetParent()
        return parent.editDialogName is not None

    def CanInsertItems(self):
        parent = self.GetParent()
        return parent.editDialogName is not None

    def OnContextMenu(self, event):
        x, y = self.ScreenToClient(event.GetPosition())
        row, flags = self.HitTest((x,y))
        if flags & wx.LIST_HITTEST_ONITEM:
            self.contextRow = row
            handle = self.rowHandles[self.contextRow]
            self.contextItem = self.dataSet.rows[handle]
        else:
            self.contextRow = self.contextItem = None
        selectedItems = self.GetSelectedItems()
        deleteEnabled = len(selectedItems) > 0 \
                and self.CanDeleteItems(selectedItems)
        editEnabled = len(selectedItems) == 1 \
                and self.CanEditItem(selectedItems[0])
        self.insertMenuItem.Enable(self.CanInsertItems())
        self.deleteMenuItem.Enable(deleteEnabled)
        self.editMenuItem.Enable(editEnabled)
        self.PopupMenu(self.menu)
        self.contextRow = None

    def OnDeleteItems(self):
        parent = self.GetParent()
        parent.DeleteItems(self.GetSelectedItems())

    def OnEditItem(self):
        parent = self.GetParent()
        parent.EditItem(self.contextItem)

    def OnInsertItems(self):
        parent = self.GetParent()
        parent.InsertItems()

    def OnRefresh(self):
        self.Retrieve()


class DataListPanel(ceGUI.Panel):
    listClassName = "List"
    editDialogName = None

    def _GetList(self):
        cls = ceGUI.GetModuleItem(self.__class__.__module__,
                self.listClassName)
        return cls(self, wx.SUNKEN_BORDER)

    def _UpdateListItem(self, item, row):
        for attrName in item.attrNames:
            if not hasattr(row, attrName):
                continue
            value = getattr(row, attrName)
            setattr(item, attrName, value)

    def EditItem(self, item):
        dialog = self.GetEditWindow(item)
        if dialog is None:
            return
        if dialog.ShowModal() == wx.ID_OK:
            row = dialog.dataSet.rows[0]
            self._UpdateListItem(item, row)
            self.list.Refresh()
        dialog.Destroy()

    def GetEditWindow(self, item = None):
        if self.editDialogName is not None:
            return self.OpenWindow(self.editDialogName, parentItem = item)

    def InsertItems(self):
        dialog = self.GetEditWindow()
        if dialog is None:
            return
        if dialog.ShowModal() == wx.ID_OK:
            row = dialog.dataSet.rows[0]
            item = self.list.AppendItem(row, refresh = False)
            self.list.dataSet.ClearChanges()
            self._UpdateListItem(item, row)
            self.list.Refresh()
        dialog.Destroy()

    def OnCreate(self):
        self.list = self._GetList()
        self.BindEvent(self.list, wx.EVT_LEFT_DCLICK, self.OnDoubleClick)
        self.Retrieve()

    def OnDoubleClick(self, event):
        x, y = event.GetPosition()
        row, flags = self.list.HitTest((x,y))
        if flags & wx.LIST_HITTEST_ONITEM:
            handle = self.list.rowHandles[row]
            contextItem = self.list.dataSet.rows[handle]
            self.EditItem(contextItem)

    def OnLayout(self):
        topSizer = wx.BoxSizer(wx.HORIZONTAL)
        topSizer.Add(self.list, proportion = 1, flag = wx.EXPAND)
        return topSizer

    def RestoreSettings(self):
        self.list.RestoreColumnWidths()

    def Retrieve(self):
        self.list.Retrieve()

    def SaveSettings(self):
        self.list.SaveColumnWidths()


class EditColumn(object):

    def __init__(self, attrName, label, field, required):
        self.attrName = attrName
        self.label = label
        self.field = field
        self.required = required


class EditDialog(ceGUI.StandardDialog):
    dataSetClassName = "DataSet"

    def __init__(self, parent, instanceName = None, parentItem = None):
        self.columns = []
        self.parentItem = parentItem
        cls = ceGUI.GetModuleItem(self.__class__.__module__,
                self.dataSetClassName)
        self.dataSet = cls(parent.config.connection)
        self.Retrieve(parent)
        super(EditDialog, self).__init__(parent, instanceName)
        focusField = None
        row = self.dataSet.rows[0]
        for column in self.columns:
            value = getattr(row, column.attrName)
            column.field.SetValue(value)
            if focusField is None:
                if not isinstance(column.field, wx.TextCtrl) \
                        or column.field.IsEditable():
                    focusField = column.field
        if focusField is not None:
            focusField.SetFocus()

    def AddColumn(self, attrName, labelText, field, required = False):
        label = self.AddLabel(labelText)
        column = EditColumn(attrName, label, field, required)
        self.columns.append(column)

    def OnLayout(self):
        args = []
        for column in self.columns:
            args.append(column.label)
            args.append(column.field)
        fieldsSizer = self.CreateFieldLayout(*args)
        topSizer = wx.BoxSizer(wx.VERTICAL)
        topSizer.Add(fieldsSizer, flag = wx.ALL | wx.EXPAND, border = 5)
        return topSizer

    def OnOk(self):
        for column in self.columns:
            value = column.field.GetValue()
            if column.required and value is None:
                column.field.SetFocus()
                raise RequiredFieldHasNoValue()
            self.dataSet.SetValue(0, column.attrName, value)
        self.OnUpdate()
        self.dataSet.Update()

    def OnNewRow(self, parent, row):
        pass

    def OnUpdate(self):
        pass

    def Retrieve(self, parent):
        if self.parentItem is None:
            handle, row = self.dataSet.InsertRow()
            self.OnNewRow(parent, row)
        else:
            args = [getattr(self.parentItem, n) \
                    for n in self.parentItem.pkAttrNames]
            self.dataSet.Retrieve(*args)
            if len(self.dataSet.rows) != 1:
                raise cx_Exceptions.NoDataFound()


class GridEditWindow(ceGUI.Frame):
    retrievalAttrNames = None
    gridClassName = "Grid"
    hasMenus = False

    def _GetGrid(self):
        gridClass = self._GetClass(self.gridClassName)
        return gridClass(self)

    def _OnCreate(self):
        self.grid = self._GetGrid()
        self.grid.SetFocus()
        self.BindEvent(self.grid, wx.grid.EVT_GRID_SELECT_CELL,
                self.OnCellSelected, skipEvent = False)
        self.subWindows = []
        self.panel = None
        super(GridEditWindow, self)._OnCreate()
        accelerators = [
            ( wx.ACCEL_CTRL, ord('D'), self.deleteToolbarItem.GetId() ),
            ( wx.ACCEL_CTRL, ord('I'), self.insertToolbarItem.GetId() ),
            ( wx.ACCEL_CTRL, ord('R'), self.retrieveToolbarItem.GetId() ),
            ( wx.ACCEL_CTRL, ord('S'), self.saveToolbarItem.GetId() )
        ]
        self.acceleratorTable = wx.AcceleratorTable(accelerators)
        self.SetAcceleratorTable(self.acceleratorTable)
        self.Retrieve()

    def AddSubWindow(self, cls, label = None):
        if self.panel is None:
            self.panel = wx.Panel(self)
        subWindow = cls(self.panel, label)
        self.BindEvent(subWindow.button, wx.EVT_BUTTON,
                functools.partial(self.OnOpenSubWindow, subWindow),
                passEvent = False)
        self.subWindows.append(subWindow)
        return subWindow

    def GetCurrentRow(self):
        return self.grid.GetCurrentRow()

    def GetRetrievalArgs(self):
        if self.retrievalAttrNames is None:
            return ()
        parentRow = self.GetParent().GetCurrentRow()
        args = [getattr(parentRow, n) for n in self.retrievalAttrNames.split()]
        return tuple(args)

    def OnCellSelected(self, event):
        currentRow = self.grid.GetGridCursorRow()
        if event.GetRow() != currentRow and self.subWindows:
            if not self.ContinueQueryChildren():
                event.Veto()
                return
            wx.CallAfter(self.RetrieveSubWindows)
        event.Skip()

    def OnCreateToolbar(self):
        self.retrieveToolbarItem = self.AddToolbarItem("Retrieve",
                wx.ART_FILE_OPEN,
                shortHelp = "Retrieve data",
                longHelp = "Retrieve data from the database",
                method = self.Retrieve, passEvent = False)
        self.saveToolbarItem = self.AddToolbarItem("Save", wx.ART_FILE_SAVE,
                shortHelp = "Save data",
                longHelp = "Save data to the database",
                method = self.OnUpdate)
        self.toolbar.AddSeparator()
        self.insertToolbarItem = self.AddToolbarItem("Insert", wx.ART_NEW,
                shortHelp = "Insert row",
                longHelp = "Insert a new row into the grid",
                method = self.OnInsertRow)
        self.deleteToolbarItem = self.AddToolbarItem("Delete", wx.ART_DELETE,
                shortHelp = "Delete row",
                longHelp = "Delete the current row from the grid",
                method = self.OnDeleteRow)

    def OnDeleteRow(self, event):
        row = self.grid.GetGridCursorRow()
        self.grid.DeleteRows(row)

    def OnInsertRow(self, event):
        row = self.grid.GetGridCursorRow()
        self.grid.InsertRows(row + 1)

    def OnLayout(self):
        topSizer = wx.BoxSizer(wx.HORIZONTAL)
        topSizer.Add(self.grid, proportion = 1, flag = wx.EXPAND)
        if self.subWindows:
            buttonSizer = wx.BoxSizer(wx.VERTICAL)
            for subWindow in self.subWindows:
                buttonSizer.Add(subWindow.button, flag = wx.BOTTOM | wx.EXPAND,
                        border = 5)
            panelSizer = wx.BoxSizer(wx.VERTICAL)
            self.panel.SetSizer(panelSizer)
            panelSizer.Add(buttonSizer, flag = wx.EXPAND | wx.RIGHT | wx.LEFT,
                    border = 5)
            topSizer.Add(self.panel, flag = wx.EXPAND)
        return topSizer

    def OnOpenSubWindow(self, subWindow):
        subWindow.Open(self)

    def OnRetrieve(self):
        pass

    def OnUpdate(self, event):
        self.grid.Update()

    def PendingChanges(self):
        self.grid.SaveEditControlValue()
        return self.grid.PendingChanges()

    def RestoreSettings(self):
        self.grid.RestoreColumnWidths()

    def Retrieve(self, continueQuery = True):
        if continueQuery and not self.ContinueQuery():
            return
        args = self.GetRetrievalArgs()
        self.grid.Retrieve(*args)
        self.RetrieveSubWindows()
        self.OnRetrieve()

    def RetrieveSubWindows(self):
        for subWindow in self.subWindows:
            window = subWindow.window
            if not window:
                continue
            subWindow.window.Retrieve(continueQuery = False)

    def SaveSettings(self):
        self.grid.SaveColumnWidths()

    def UpdateChanges(self):
        self.grid.Update()


class RequiredFieldHasNoValue(cx_Exceptions.BaseException):
    message = "Required field has no value."


class SubWindow(object):
    childWindowName = None
    childWindowInstanceName = None
    childForceNewInstance = False
    isModal = False
    label = ""

    def __init__(self, parent, label):
        if label is None:
            label = self.label
        self.button = wx.Button(parent, -1, label)
        self.window = None

    def Open(self, parent):
        if self.window:
            self.window.SetFocus()
        else:
            self.window = parent.OpenWindow(self.childWindowName,
                    self.childForceNewInstance, self.childWindowInstanceName)
            if self.isModal:
                self.window.ShowModal()
            else:
                self.window.Show()

