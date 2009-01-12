"""
Define windows used for editing data.
"""

import ceGUI
import cx_Exceptions
import cx_Logging
import functools
import os
import sys
import wx

__all__ = [ "DataList", "DataListPanel", "DirNameEditDialogColumn",
            "EditDialog", "EditDialogColumn", "FileNameEditDialogColumn",
            "GridEditWindow", "SubWindow" ]


class DataList(ceGUI.List):
    createContextMenu = True
    singleSelection = True

    def _CreateContextMenu(self):
        self.menu = ceGUI.Menu()
        self.refreshMenuItem = self.menu.AddEntry(self, "Refresh\tCtrl-R",
                method = self._OnRefresh, passEvent = False)
        self.menu.AddSeparator()
        self.insertMenuItem = self.menu.AddEntry(self, "Insert\tCtrl-I",
                method = self._OnInsertItems, passEvent = False)
        self.editMenuItem = self.menu._AddEntry(self, "Edit\tCtrl-E",
                method = self._OnEditItem, passEvent = False)
        self.deleteMenuItem = self.menu.AddEntry(self, "Delete\tCtrl-D",
                method = self._OnDeleteItems, passEvent = False)

    def _GetAccelerators(self):
        return [ ( wx.ACCEL_CTRL, ord('D'), self.deleteMenuItem.GetId() ),
                 ( wx.ACCEL_CTRL, ord('I'), self.insertMenuItem.GetId() ),
                 ( wx.ACCEL_CTRL, ord('E'), self.editMenuItem.GetId() ),
                 ( wx.ACCEL_CTRL, ord('R'), self.refreshMenuItem.GetId() ) ]

    def _OnContextMenu(self, event):
        self.OnContextMenu()

    def _OnRightClick(self, event):
        self.OnContextMenu()

    def _OnCreate(self):
        super(DataList, self)._OnCreate()
        self._CreateContextMenu()
        accelerators = self._GetAccelerators()
        self.acceleratorTable = wx.AcceleratorTable(accelerators)
        self.SetAcceleratorTable(self.acceleratorTable)
        parent = self.GetParent()
        if sys.platform == "win32":
            parent.BindEvent(self, wx.EVT_CONTEXT_MENU,
                    self._OnContextMenu)
        else:
            parent.BindEvent(self, wx.EVT_LIST_ITEM_RIGHT_CLICK,
                    self._OnRightClick)

    def _OnDeleteItems(self):
        items = self.GetSelectedItems()
        if self.CanDeleteItems(items):
            self.OnDeleteItems(items)

    def _OnEditItem(self):
        itemIndexes = list(self.GetSelectedItemIndexes())
        if len(itemIndexes) == 1:
            itemIndex = itemIndexes[0]
            item = self.GetItem(itemIndex)
            if self.CanEditItem(item):
                self.OnEditItem(item, itemIndex)

    def _OnInsertItems(self):
        if self.CanInsertItems():
            self.OnInsertItems()

    def _OnRefresh(self):
        if self.CanRefreshItems():
            self.OnRefresh()

    def CanDeleteItems(self, items):
        return True

    def CanEditItem(self, item):
        parent = self.GetParent()
        return parent.editDialogName is not None

    def CanInsertItems(self):
        parent = self.GetParent()
        return parent.editDialogName is not None

    def CanRefreshItems(self):
        return True

    def OnContextMenu(self):
        items = self.GetSelectedItems()
        deleteEnabled = len(items) > 0 and self.CanDeleteItems(items)
        editEnabled = len(items) == 1 and self.CanEditItem(items[0])
        self.refreshMenuItem.Enable(self.CanRefreshItems())
        self.insertMenuItem.Enable(self.CanInsertItems())
        self.deleteMenuItem.Enable(deleteEnabled)
        self.editMenuItem.Enable(editEnabled)
        self.menu.Popup(self)

    def OnDeleteItems(self, items):
        parent = self.GetParent()
        parent.DeleteItems(items)

    def OnEditItem(self, item, itemIndex):
        parent = self.GetParent()
        parent.EditItem(item, itemIndex)

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

    def _OnEditItem(self, item, itemIndex, dialog):
        row = dialog.dataSet.rows[0]
        self._UpdateListItem(item, row)
        self.list.Refresh()

    def _OnInsertItems(self, dialog):
        row = dialog.dataSet.rows[0]
        item = self.list.AppendItem(row, refresh = False)
        self.list.dataSet.ClearChanges()
        self._UpdateListItem(item, row)
        self.list.Refresh()

    def _UpdateListItem(self, item, row):
        for attrName in item.attrNames:
            if not hasattr(row, attrName):
                continue
            value = getattr(row, attrName)
            setattr(item, attrName, value)

    def DeleteItems(self, items):
        message = "Delete selected items?"
        flag = wx.YES_NO | wx.ICON_EXCLAMATION
        dialog = wx.MessageDialog(self, message, "Confirm Delete", flag)
        response = dialog.ShowModal()
        dialog.Destroy()
        if response != wx.ID_YES:
            return
        for itemIndex in reversed(list(self.list.GetSelectedItemIndexes())):
            self.list.DeleteItem(itemIndex, refresh = False)
        self.list.dataSet.Update()
        self.list.Refresh()

    def EditItem(self, item, itemIndex):
        dialog = self.GetEditWindow(item)
        if dialog is None:
            return
        if dialog.ShowModal() == wx.ID_OK:
            self._OnEditItem(item, itemIndex, dialog)
        dialog.Destroy()

    def GetEditWindow(self, item = None):
        if self.editDialogName is not None:
            return self.OpenWindow(self.editDialogName, parentItem = item)

    def InsertItems(self):
        dialog = self.GetEditWindow()
        if dialog is None:
            return
        method = getattr(dialog, "IsEditingCanceled", None)
        if method is None or not method():
            if dialog.ShowModal() == wx.ID_OK:
                self._OnInsertItems(dialog)
        dialog.Destroy()

    def OnCreate(self):
        self.list = self._GetList()
        self.BindEvent(self.list, wx.EVT_LIST_ITEM_ACTIVATED,
                self.OnItemActivated)
        wx.CallAfter(self.Retrieve)

    def OnItemActivated(self, event):
        itemIndex = event.GetIndex()
        handle = self.list.rowHandles[itemIndex]
        item = self.list.dataSet.rows[handle]
        self.EditItem(item, itemIndex)

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


class EditDialogColumn(ceGUI.BaseControl):

    def __init__(self, parent, attrName, labelText, field, required = False):
        self.attrName = attrName
        self.label = parent.AddLabel(labelText)
        self.field = field
        self.required = required
        self._Initialize()
        parent.columns.append(self)

    def GetValue(self):
        return self.field.GetValue()

    def IsEditable(self):
        if isinstance(self.field, wx.TextCtrl):
            return self.field.IsEditable()
        return True

    def Layout(self, sizer):
        sizer.Add(self.label, flag = wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(self.field, flag = wx.ALIGN_CENTER_VERTICAL | wx.EXPAND)

    def SetValue(self, row):
        value = getattr(row, self.attrName)
        self.field.SetValue(value)

    def Update(self, dataSet):
        value = self.GetValue()
        dataSet.SetValue(0, self.attrName, value)

    def Verify(self):
        if self.required:
            value = self.field.GetValue()
            if value is None:
                self.field.SetFocus()
                raise ceGUI.RequiredFieldHasNoValue()

    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, self.attrName)


class FileNameEditDialogColumn(EditDialogColumn):
    style = wx.FD_DEFAULT_STYLE
    message = "Choose a file"
    extension = None

    def __init__(self, parent, attrName, labelText, field, required = False):
        super(FileNameEditDialogColumn, self).__init__(parent, attrName,
                labelText, field, required)
        self.button = parent.AddButton("...", size = (25, -1),
                method = self.OnSelectFileName, passEvent = False)

    def GetDefaultDirAndFileName(self, currentValue):
        if currentValue is None:
            return "", ""
        return os.path.split(currentValue)

    def Layout(self, sizer):
        fileNameSizer = wx.BoxSizer(wx.HORIZONTAL)
        fileNameSizer.Add(self.field, border = 5, proportion = 1,
                flag = wx.ALIGN_CENTER_VERTICAL | wx.EXPAND | wx.RIGHT)
        fileNameSizer.Add(self.button, flag = wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(self.label, flag = wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(fileNameSizer, flag = wx.ALIGN_CENTER_VERTICAL | wx.EXPAND)

    def OnSelectFileName(self):
        dir, fileName = self.GetDefaultDirAndFileName(self.field.GetValue())
        if self.extension is not None:
            wildcard = "*" + self.extension
        else:
            wildcard = "*.*"
        parent = self.field.GetParent()
        dialog = wx.FileDialog(parent, self.message, wildcard = wildcard,
                defaultDir = dir, defaultFile = fileName, style = self.style)
        if dialog.ShowModal() == wx.ID_OK:
            fileName = dialog.GetPath()
            if self.extension is not None:
                normalizedFileName = os.path.normcase(fileName)
                if not normalizedFileName.endswith(self.extension):
                    fileName += self.extension
            self.field.SetValue(fileName)


class DirNameEditDialogColumn(FileNameEditDialogColumn):
    style = wx.DD_DEFAULT_STYLE
    message = "Choose a directory"

    def GetDefaultDirName(self, currentValue):
        if currentValue is None:
            return ""
        return currentValue

    def OnSelectFileName(self):
        defaultPath = self.GetDefaultDirName(self.field.GetValue())
        parent = self.field.GetParent()
        dialog = wx.DirDialog(parent, self.message, defaultPath = defaultPath,
                style = self.style)
        if dialog.ShowModal() == wx.ID_OK:
            self.field.SetValue(dialog.GetPath())


class EditDialog(ceGUI.StandardDialog):
    dataSetClassName = "DataSet"
    updateCacheMethodName = None

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
            column.SetValue(row)
            if focusField is None and column.IsEditable():
                focusField = column.field
        if focusField is not None:
            focusField.SetFocus()

    def AddColumn(self, attrName, labelText, field, required = False,
            cls = EditDialogColumn):
        return cls(self, attrName, labelText, field, required)

    def GetFieldsSizer(self):
        sizer = wx.FlexGridSizer(rows = len(self.columns), cols = 2, vgap = 5,
                hgap = 5)
        sizer.AddGrowableCol(1)
        return sizer

    def OnLayout(self):
        fieldsSizer = self.GetFieldsSizer()
        for column in self.columns:
            column.Layout(fieldsSizer)
        topSizer = wx.BoxSizer(wx.VERTICAL)
        topSizer.Add(fieldsSizer, flag = wx.ALL | wx.EXPAND, border = 5)
        return topSizer

    def OnOk(self):
        for column in self.columns:
            if column.IsEditable():
                column.Verify()
                column.Update(self.dataSet)
        self.OnPreUpdate()
        self.dataSet.Update()
        self.OnPostUpdate()

    def OnNewRow(self, parent, row):
        pass

    def OnPostUpdate(self):
        if self.updateCacheMethodName is not None:
            method = getattr(self.cache, self.updateCacheMethodName)
            for row in self.dataSet.rows.itervalues():
                method(row)

    def OnPreUpdate(self):
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

