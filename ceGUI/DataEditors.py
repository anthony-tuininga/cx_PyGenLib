"""
Define windows used for editing data.
"""

import ceDatabase
import ceGUI
import cx_Exceptions
import cx_Logging
import functools
import os
import sys
import wx

__all__ = [ "BooleanEditDialogColumn", "ChoiceEditDialogColumn",
            "ColorEditDialogColumn", "DataPanel", "DataEditPanel", "DataGrid",
            "DataGridPanel", "DataList", "DataListPanel", "DataNotebookPanel",
            "DateEditDialogColumn", "DecimalEditDialogColumn",
            "DirNameEditDialogColumn", "EditDialog", "EditDialogColumn",
            "EllipsisEditDialogColumn", "FileNameEditDialogColumn",
            "GridEditWindow", "RadioButtonEditDialogColumn", "SubWindow",
            "TextEditDialogColumn" ]


class EditDialog(ceGUI.StandardDialog):
    dataSetClassName = "DataSet"
    saveWidthOnly = True

    def __init__(self, parent, instanceName = None, parentItem = None,
            clone = False):
        self.parentItem = parentItem
        self.dataSet = self._GetDataSet(parent)
        self.Retrieve(parent)
        if clone:
            self.dataSet.MarkAllRowsAsNew()
            self.OnClone(parent, self.GetRow())
        super(EditDialog, self).__init__(parent, instanceName)
        self.OnPostCreate()

    def _GetDataSet(self, parent):
        cls = self._GetClass(self.dataSetClassName)
        app = ceGUI.GetApp()
        return cls(app.config.dataSource, self.parentItem)

    def GetRow(self):
        return self.dataSet.rows[0]

    def IsUpdatedIndependently(self, parent = None):
        if parent is None:
            parent = self.GetParent()
        return not isinstance(parent, EditDialog)

    def OnCancel(self):
        self.panel.OnCancelEditing()

    def OnClone(self, parent, row):
        pass

    def OnNewRow(self, parent, row):
        pass

    def OnOk(self):
        self.OnPreUpdate()
        if self.IsUpdatedIndependently():
            self.dataSet.Update()
        self.OnPostUpdate()

    def OnPostCreate(self):
        self.panel.OnPostCreate()

    def OnPostUpdate(self):
        self.panel.OnPostUpdate()

    def OnPreUpdate(self):
        self.panel.OnPreUpdate()

    def Retrieve(self, parent):
        if self.parentItem is None:
            handle, row = self.dataSet.InsertRow()
            self.OnNewRow(parent, row)
        elif not self.IsUpdatedIndependently(parent):
            values = [getattr(self.parentItem, n) \
                    for n in self.dataSet.attrNames]
            row = self.dataSet.rowClass(*values)
            self.dataSet.SetRows([row])
        else:
            args = [getattr(self.parentItem, n) \
                    for n in self.parentItem.pkAttrNames]
            self.dataSet.Retrieve(*args)
            if len(self.dataSet.rows) != 1:
                raise cx_Exceptions.NoDataFound()


class DataPanel(ceGUI.Panel):
    updateSubCacheAttrName = None
    dataSetClassName = None

    def _GetDataSet(self):
        editDialog = self._GetEditDialog()
        if self.dataSetClassName is not None:
            cls = self._GetClass(self.dataSetClassName)
            if editDialog is not None:
                dataSet = editDialog.dataSet.AddChildDataSet(cls,
                        editDialog.GetRow())
            else:
                app = ceGUI.GetApp()
                dataSet = cls(app.config.dataSource)
            return dataSet
        if editDialog is not None:
            return editDialog.dataSet

    def _GetEditDialog(self):
        item = self
        while True:
            parent = item.GetParent()
            if parent is None:
                break
            if isinstance(parent, EditDialog):
                return parent
            if isinstance(parent, ceGUI.Dialog):
                break
            item = parent

    def _Initialize(self):
        editDialog = self._GetEditDialog()
        if editDialog is not None:
            self.parentItem = editDialog.parentItem
        self.dataSet = self._GetDataSet()
        super(DataPanel, self)._Initialize()

    def OnCancelEditing(self):
        pass

    def OnPostCreate(self):
        pass

    def OnPostUpdate(self):
        if self.updateSubCacheAttrName is not None:
            subCache = getattr(self.cache, self.updateSubCacheAttrName)
            for row in self.dataSet.GetRows():
                subCache.UpdateRow(self.cache, row, self.dataSet.contextItem)

    def OnPreUpdate(self):
        pass

    def RestoreSettings(self):
        pass

    def SaveSettings(self):
        pass


class DataEditPanel(DataPanel):

    def _Initialize(self):
        self.columns = []
        super(DataEditPanel, self)._Initialize()

    def AddColumn(self, attrName, labelText, field = None, required = False,
            cls = None, constantValue = None, **args):
        if cls is None:
            cls = EditDialogColumn
        if field is None and constantValue is not None:
            field = self.AddTextField(editable = False)
        return cls(self, attrName, labelText, field, required, constantValue,
                **args)

    def GetColumnForAttrName(self, attrName):
        for column in self.columns:
            if column.attrName == attrName:
                return column
        raise MissingColumn(attrName = attrName)

    def GetFieldsSizer(self):
        sizer = wx.FlexGridSizer(rows = len(self.columns), cols = 2, vgap = 5,
                hgap = 5)
        sizer.AddGrowableCol(1)
        return sizer

    def GetRow(self):
        return self.dataSet.rows[0]

    def OnCancelEditing(self):
        for column in self.columns:
            column.OnCancelEditing()

    def OnLayout(self, proportion = 1):
        self.fieldsSizer = self.GetFieldsSizer()
        for column in self.columns:
            column.Layout(self.fieldsSizer)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.fieldsSizer, flag = wx.ALL | wx.EXPAND,
                proportion = proportion, border = 5)
        return sizer

    def OnPostCreate(self):
        focusControl = None
        row = self.GetRow()
        for column in self.columns:
            column.SetValue(row)
            if focusControl is None and column.IsEditable():
                focusControl = column.GetControlForFocus()
        if focusControl is not None:
            focusControl.SetFocus()

    def OnPreUpdate(self):
        for column in self.columns:
            if column.IsEditable():
                column.Verify()
                column.Update(self.dataSet)

    def ReplaceColumn(self, origColumn, newColumn, sizer = None,
            layout = True):
        if sizer is None:
            sizer = self.fieldsSizer
        origIndex = self.columns.index(origColumn)
        self.columns.remove(newColumn)
        newColumn.ReplaceColumn(origColumn, sizer)
        origColumn.Destroy()
        self.columns[origIndex] = newColumn
        if layout:
            sizer.Layout()


class DataMultipleRowPanel(DataPanel):
    createRetrieveButton = False
    filterArgsPerRow = 5

    @property
    def rowControl(self):
        return getattr(self, self.multipleRowControlAttrName)

    def CanDeleteItems(self, items = []):
        return self.rowControl.CanDeleteItems(items)

    def CanInsertItems(self):
        return self.rowControl.CanInsertItems()

    def GetBaseRows(self):
        pass

    def GetFilterArgForName(self, name):
        for filterArg in self.filterArgs:
            if filterArg.name == name:
                return filterArg
        raise MissingFilterArg(name = name)

    def GetRetrievalArgs(self):
        return [a.GetValue() for a in self.filterArgs]

    def IsUpdatedIndependently(self):
        return self._GetEditDialog() is None

    def OnCreate(self):
        self.filterArgs = []
        self.OnCreateFilterArgs()
        if self.createRetrieveButton:
            self.retrieveButton = self.AddButton("Retrieve", self.Retrieve,
                    passEvent = False)
        else:
            wx.CallAfter(self.Retrieve, refresh = True)
        super(DataMultipleRowPanel, self).OnCreate()
        if self.dataSet is None:
            self.dataSet = self.rowControl.dataSet

    def OnCreateFilterArgs(self):
        pass

    def OnLayout(self):
        topSizer = wx.BoxSizer(wx.VERTICAL)
        if self.filterArgs:
            self.OnLayoutFilterArgs(topSizer)
        topSizer.Add(self.rowControl, proportion = 1, flag = wx.EXPAND)
        return topSizer

    def OnLayoutFilterArgs(self, topSizer):
        sizers = []
        argsThisSizer = self.filterArgsPerRow
        for filterArg in self.filterArgs:
            if argsThisSizer == self.filterArgsPerRow:
                sizer = wx.BoxSizer(wx.HORIZONTAL)
                sizers.append(sizer)
                argsThisSizer = 0
            filterArg.Layout(sizer)
            argsThisSizer += 1
        flag = wx.ALL
        for sizer in sizers:
            topSizer.Add(sizer, flag = wx.EXPAND | flag, border = 5)
            flag = wx.LEFT | wx.RIGHT | wx.BOTTOM
        if self.createRetrieveButton:
            sizers[-1].Add(self.retrieveButton,
                    flag = wx.ALIGN_CENTER_VERTICAL | wx.LEFT, border = 10)

    def OnPopulateBaseRows(self, rows):
        pass

    def OnRetrieve(self):
        if self.updateLabelWithCount:
            self._UpdateLabelWithCount()
        else:
            self._DisplayNumItems()

    def Retrieve(self, refresh = False):
        if not self:
            return
        args = self.GetRetrievalArgs()
        if refresh and not self.ContinueQuery():
            return
        if self.createRetrieveButton:
            self.rowControl.Retrieve(*args)
        else:
            if refresh:
                rows = self.GetBaseRows()
                self.OnPopulateBaseRows(rows)
                self.rows = rows
            if self.rows is None \
                    or isinstance(self.dataSet, ceDatabase.FilteredDataSet):
                self.rowControl.Retrieve(*args)
            else:
                self.rowControl.Retrieve(self.rows, *args)
        self.OnRetrieve()

    def RestoreFilterArgs(self):
        for filterArg in self.filterArgs:
            if filterArg.saveValue:
                filterArg.RestoreSetting()

    def SaveFilterArgs(self):
        for filterArg in self.filterArgs:
            if filterArg.saveValue:
                filterArg.SaveSetting()


class DataGridPanel(DataMultipleRowPanel):
    multipleRowControlAttrName = "grid"
    dataSetClassName = "DataSet"
    filteredDataSetClassName = None
    gridClassName = "Grid"
    updateLabelWithCount = False

    def _GetDataSet(self):
        dataSet = super(DataGridPanel, self)._GetDataSet()
        if self.filteredDataSetClassName is None:
            self.primaryDataSet = None
            return dataSet
        self.primaryDataSet = dataSet
        cls = self._GetClass(self.filteredDataSetClassName)
        return cls(self.primaryDataSet)

    def _GetGrid(self):
        cls = self._GetClass(self.gridClassName)
        return cls(self)

    def _GetNumItems(self):
        return self.grid.GetNumberRows()

    def _UpdateLabelWithCount(self):
        numRows = len(self.grid.dataSet.rows)
        parent = self.GetParent().GetParent()
        parent.SetPageText(self, "%s (%s)" % (self.label, numRows))

    def InsertItems(self):
        if self.CanInsertItems():
            self.grid.InsertRows()

    def DeleteSelectedItems(self):
        items = self.grid.GetSelectedRows()
        if not items or not self.CanDeleteItems(items):
            return
        blocks = self.grid._GetSelectionBlocks()
        if not blocks:
            self.grid.DeleteRows()
        for (top, left), (bottom, right) in reversed(blocks):
            self.grid.DeleteRows(top, numRows = bottom - top + 1)
        self.grid.ClearSelection()

    def GetBaseRows(self):
        if self.primaryDataSet is not None:
            self.primaryDataSet.Retrieve()
            return self.primaryDataSet.GetRows()

    def OnCreate(self):
        self.SetWindowStyle(0)
        self.grid = self._GetGrid()
        self.grid.SetFocus()
        super(DataGridPanel, self).OnCreate()

    def OnPostCreate(self):
        if self.updateLabelWithCount:
            self._UpdateLabelWithCount()

    def PendingChanges(self):
        if not self.grid:
            return False
        self.grid.SaveEditControlValue()
        return self.grid.PendingChanges()

    def RestoreSettings(self):
        self.RestoreFilterArgs()
        self.grid.RestoreColumnWidths()

    def SaveSettings(self):
        self.SaveFilterArgs()
        self.grid.SaveColumnWidths()

    def UpdateChanges(self):
        self.OnPreUpdate()
        if self.IsUpdatedIndependently():
            self.grid.Update()
        self.OnPostUpdate()


class DataGrid(ceGUI.Grid):

    def _GetDataSet(self):
        parent = self.GetParent()
        if isinstance(parent, DataGridPanel) and parent.dataSet is not None:
            return parent.dataSet
        return super(DataGrid, self)._GetDataSet()

    def _OnRefresh(self):
        parent = self.GetParent()
        parent.Retrieve(refresh = True)


class DataListPanel(DataMultipleRowPanel):
    multipleRowControlAttrName = "list"
    listClassName = "List"
    editDialogName = None
    updateLabelWithCount = False

    def _GetList(self):
        cls = self._GetClass(self.listClassName)
        return cls(self, wx.SUNKEN_BORDER)

    def _GetNumItems(self):
        return self.list.GetItemCount()

    def _OnEditItem(self, item, itemIndex, dialog):
        row = dialog.GetRow()
        self._UpdateListItem(item, row, itemIndex)
        self._OnListChanged()

    def _OnInsertItems(self, dialog):
        row = dialog.dataSet.rows[0]
        item = self.list.AppendItem(row, refresh = False)
        self._UpdateListItem(item, row)
        self.list.DeselectAll()
        self.list.SelectItem(item, ensureVisible = True)
        self._OnListChanged()
        if self.updateLabelWithCount:
            self._UpdateLabelWithCount()

    def _OnListChanged(self):
        if self.IsUpdatedIndependently():
            self.list.dataSet.ClearChanges()
        self.list.Refresh()

    def _UpdateLabelWithCount(self):
        numRows = len(self.list.dataSet.rows)
        parent = self.GetParent().GetParent()
        parent.SetPageText(self, "%s (%s)" % (self.label, numRows))

    def _UpdateListItem(self, item, row, itemIndex = None):
        for attrName in item.GetAttributeNames():
            if not hasattr(row, attrName):
                continue
            value = getattr(row, attrName)
            if itemIndex is None:
                setattr(item, attrName, value)
            else:
                handle = self.list.rowHandles[itemIndex]
                self.list.dataSet.SetValue(handle, attrName, value)

    def DeleteItems(self, items):
        if self.IsUpdatedIndependently():
            message = "Delete selected items?"
            flag = wx.YES_NO | wx.ICON_EXCLAMATION
            dialog = wx.MessageDialog(self, message, "Confirm Delete", flag)
            response = dialog.ShowModal()
            dialog.Destroy()
            if response != wx.ID_YES:
                return False
        for itemIndex in reversed(list(self.list.GetSelectedItemIndexes())):
            self.list.DeleteItem(itemIndex, refresh = False)
        if self.IsUpdatedIndependently():
            self.list.dataSet.Update()
            if self.updateSubCacheAttrName is not None:
                subCache = getattr(self.cache, self.updateSubCacheAttrName)
                for item in items:
                    subCache.RemoveRow(self.cache, item)
        self._OnListChanged()
        if self.updateLabelWithCount:
            self._UpdateLabelWithCount()
        return True

    def DeleteSelectedItems(self):
        items = self.list.GetSelectedItems()
        if items and self.list.CanDeleteItems(items):
            self.DeleteItems(items)

    def EditItem(self, item, itemIndex):
        dialog = self.GetEditWindow(item)
        if dialog is None:
            return
        if dialog.ShowModal() == wx.ID_OK:
            self._OnEditItem(item, itemIndex, dialog)
        dialog.Destroy()

    def GetEditWindow(self, item = None):
        if self.editDialogName is not None:
            parent = self._GetEditDialog()
            if parent is None:
                parent = self
            return parent.OpenWindow(self.editDialogName, parentItem = item)

    def InsertItems(self):
        if not self.CanInsertItems():
            return
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
        super(DataListPanel, self).OnCreate()

    def OnItemActivated(self, event):
        itemIndex = event.GetIndex()
        handle = self.list.rowHandles[itemIndex]
        item = self.list.dataSet.rows[handle]
        if self.list.CanEditItem(item):
            self.EditItem(item, itemIndex)

    def OnPostCreate(self):
        if self.updateLabelWithCount:
            self._UpdateLabelWithCount()

    def RestoreSettings(self):
        self.RestoreFilterArgs()
        self.list.RestoreColumnWidths()

    def SaveSettings(self):
        self.SaveFilterArgs()
        self.list.SaveColumnWidths()


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

    def _GetDataSet(self):
        parent = self.GetParent()
        if isinstance(parent, DataListPanel) and parent.dataSet is not None:
            return parent.dataSet
        return super(DataList, self)._GetDataSet()

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
        parent = self.GetParent()
        if not isinstance(parent, DataListPanel):
            return True
        if parent.updateSubCacheAttrName is not None:
            return False
        return parent._GetEditDialog() is None

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
        parent = self.GetParent()
        parent.Retrieve(refresh = True)


class DataNotebookPanel(DataPanel):

    def _GetPageIndex(self, pageToFind):
        for pageIndex, page in enumerate(self.notebook.IterPages()):
            if page is pageToFind:
                return pageIndex

    def GetPageByName(self, name):
        for page in self.notebook.IterPages():
            if page.__class__.__name__ == name:
                return page

    def OnCreate(self):
        self.notebook = ceGUI.Notebook(self)
        for className in self.pageClassNames.split():
            cls = self._GetClass(className)
            page = cls(self.notebook)
            self.notebook.AddPage(page, page.label)
        self.notebook.SetSelection(0)

    def OnLayout(self):
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.notebook, border = 5, proportion = 1,
                flag = wx.RIGHT | wx.LEFT | wx.TOP | wx.EXPAND)
        return sizer

    def OnPostCreate(self):
        for page in self.notebook.IterPages():
            page.OnPostCreate()

    def OnPostUpdate(self):
        for page in self.notebook.IterPages():
            page.OnPostUpdate()

    def OnPreUpdate(self):
        for page in self.notebook.IterPages():
            page.OnPreUpdate()

    def RestoreSettings(self):
        for page in self.notebook.IterPages():
            page.RestoreSettings()

    def SaveSettings(self):
        for page in self.notebook.IterPages():
            page.SaveSettings()

    def SetPageText(self, page, text):
        pageIndex = self._GetPageIndex(page)
        self.notebook.SetPageText(pageIndex, text)


class EditDialogColumn(ceGUI.BaseControl):
    expandField = True

    def __init__(self, parent, attrName, labelText, field,
            required = False, constantValue = None):
        self.attrName = attrName
        self.label = parent.AddLabel(labelText, bold = required)
        self.field = field
        self.required = required
        self.constantValue = constantValue
        self._Initialize()
        parent.columns.append(self)

    def GetValue(self):
        return self.field.GetValue()

    def IsEditable(self):
        if self.constantValue is not None:
            return False
        if isinstance(self.field, wx.TextCtrl):
            return self.field.IsEditable()
        return True

    def Destroy(self):
        self.label.Destroy()
        self.field.Destroy()

    def GetControlForFocus(self):
        return self.field

    def Layout(self, sizer):
        sizer.Add(self.label, flag = wx.ALIGN_CENTER_VERTICAL)
        flags = wx.ALIGN_CENTER_VERTICAL
        if isinstance(self.field, wx.CheckBox):
            flags |= wx.TOP | wx.BOTTOM
        elif self.expandField:
            flags |= wx.EXPAND
        sizer.Add(self.field, flag = flags, border = 4)

    def OnCancelEditing(self):
        pass

    def OnRequiredFieldHasNoValue(self):
        self.field.SetFocus()

    def ReplaceColumn(self, origColumn, sizer):
        self.field.MoveAfterInTabOrder(origColumn.field)
        sizer.Replace(origColumn.label, self.label, recursive = True)
        sizer.Replace(origColumn.field, self.field, recursive = True)

    def SetValue(self, row):
        if self.constantValue is not None:
            value = self.constantValue
        else:
            value = getattr(row, self.attrName)
        self.field.SetValue(value)

    def Update(self, dataSet):
        try:
            value = self.GetValue()
        except:
            self.field.SetFocus()
            raise
        dataSet.SetValue(0, self.attrName, value)

    def Verify(self):
        if self.required:
            value = self.field.GetValue()
            if value is None:
                self.OnRequiredFieldHasNoValue()
                raise ceGUI.RequiredFieldHasNoValue()

    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, self.attrName)



class EllipsisEditDialogColumn(EditDialogColumn):

    def __init__(self, parent, attrName, labelText, field = None,
            required = False, constantValue = None, editable = True):
        if field is None:
            field = parent.AddTextField(editable = False)
        super(EllipsisEditDialogColumn, self).__init__(parent, attrName,
                labelText, field, required, constantValue)
        self.button = parent.AddButton("...", size = (25, -1),
                method = self.OnChooseValue, passEvent = False,
                enabled = editable)

    def Destroy(self):
        super(EllipsisEditDialogColumn, self).Destroy()
        self.button.Destroy()

    def IsEditable(self):
        return self.button.IsEnabled()

    def Layout(self, sizer):
        fieldSizer = wx.BoxSizer(wx.HORIZONTAL)
        fieldSizer.Add(self.field, border = 5, proportion = 1,
                flag = wx.ALIGN_CENTER_VERTICAL | wx.EXPAND | wx.RIGHT)
        fieldSizer.Add(self.button, flag = wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(self.label, flag = wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(fieldSizer, flag = wx.ALIGN_CENTER_VERTICAL | wx.EXPAND)

    def OnChooseValue(self):
        pass

    def OnRequiredFieldHasNoValue(self):
        self.button.SetFocus()

    def ReplaceColumn(self, origColumn, sizer):
        super(EllipsisEditDialogColumn, self).ReplaceColumn(origColumn, sizer)
        self.button.MoveAfterInTabOrder(origColumn.button)
        sizer.Replace(origColumn.button, self.button, recursive = True)


class FileNameEditDialogColumn(EllipsisEditDialogColumn):

    def __init__(self, parent, attrName, labelText, field = None,
            required = False, constantValue = None, editable = True,
            extension = None, message = "Choose a file",
            style = wx.FD_DEFAULT_STYLE):
        super(FileNameEditDialogColumn, self).__init__(parent, attrName,
                labelText, field, required, constantValue, editable)
        self.style = style
        self.message = message
        self.extension = extension

    def GetDefaultDirAndFileName(self, currentValue):
        if currentValue is None:
            return "", ""
        return os.path.split(currentValue)

    def OnChooseValue(self):
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

    def __init__(self, parent, attrName, labelText, field = None,
            required = False, constantValue = None, editable = True,
            message = "Choose a directory", style = wx.DD_DEFAULT_STYLE):
        super(DirNameEditDialogColumn, self).__init__(parent, attrName,
                labelText, field, required, constantValue, editable)
        self.style = style
        self.message = message

    def GetDefaultDirName(self, currentValue):
        if currentValue is None:
            return ""
        return currentValue

    def OnChooseValue(self):
        defaultPath = self.GetDefaultDirName(self.field.GetValue())
        parent = self.field.GetParent()
        dialog = wx.DirDialog(parent, self.message, defaultPath = defaultPath,
                style = self.style)
        if dialog.ShowModal() == wx.ID_OK:
            self.field.SetValue(dialog.GetPath())


class BooleanEditDialogColumn(EditDialogColumn):

    def __init__(self, parent, attrName, labelText, editable = True):
        if editable:
            field = parent.AddCheckBox()
        else:
            field = parent.AddTextField(editable = False)
        self.editable = editable
        super(BooleanEditDialogColumn, self).__init__(parent, attrName,
                labelText, field)

    def SetValue(self, row):
        value = getattr(row, self.attrName)
        if not isinstance(value, bool):
            value = False
        if self.editable:
            self.field.SetValue(value)
        else:
            self.field.SetValue(value and "Yes" or "No")


class ChoiceEditDialogColumn(EditDialogColumn):

    def __init__(self, parent, attrName, labelText, choices, required = False,
            editable = True, onChangeMethod = None, passEvent = False):
        self.choices = dict(choices)
        if editable:
            field = parent.AddChoiceField(choices)
            if onChangeMethod is not None:
                parent.BindEvent(field, wx.EVT_CHOICE, onChangeMethod,
                        passEvent = passEvent)
        else:
            field = parent.AddTextField(editable = False)
        self.editable = editable
        super(ChoiceEditDialogColumn, self).__init__(parent, attrName,
                labelText, field, required = required)

    def SetValue(self, row):
        value = getattr(row, self.attrName)
        if self.editable:
            self.field.SetValue(value)
        else:
            displayValue = self.choices[value]
            self.field.SetValue(displayValue)


class RadioButtonEditDialogColumn(EditDialogColumn):

    def __init__(self, parent, attrName, labelText, choices, editable = True,
            horizontal = True, method = None, passEvent = True,
            required = False):
        self.choices = dict(choices)
        self.editable = editable
        self.horizontal = horizontal
        if editable:
            self.radioButtons = []
            self.radioButtonsByValue = {}
            style = wx.RB_GROUP
            for value, description in choices:
                button = wx.RadioButton(parent, label = description,
                        style = style)
                self.radioButtons.append(button)
                self.radioButtonsByValue[value] = button
                style = 0
            field = self.radioButtons[0]
            field.SetValue(True)
            if method is not None:
                for button in self.radioButtons:
                    parent.BindEvent(button, wx.EVT_RADIOBUTTON, method,
                            passEvent = passEvent)
        else:
            field = parent.AddTextField(editable = False)
        super(RadioButtonEditDialogColumn, self).__init__(parent, attrName,
                labelText, field, required = required)

    def GetControlForFocus(self):
        for button in self.radioButtonsByValue.values():
            if button.GetValue():
                return button

    def GetValue(self):
        if not self.editable:
            return self.field.GetValue()
        for value in self.radioButtonsByValue:
            button = self.radioButtonsByValue[value]
            if button.GetValue():
                return value

    def Layout(self, sizer):
        if not self.editable:
            return super(RadioButtonEditDialogColumn, self).Layout(sizer)
        sizer.Add(self.label, flag = wx.ALIGN_CENTER_VERTICAL)
        if self.horizontal:
            orientation = wx.HORIZONTAL
        else:
            orientation = wx.VERTICAL
        buttonSizer = wx.BoxSizer(orientation)
        flags = wx.ALIGN_CENTER_VERTICAL | wx.RIGHT
        for button in self.radioButtons:
            buttonSizer.Add(button, flag = flags, border = 5)
        flags = wx.ALIGN_CENTER_VERTICAL | wx.EXPAND | wx.TOP | wx.BOTTOM
        sizer.Add(buttonSizer, flag = flags, border = 4)

    def SetValue(self, row):
        value = getattr(row, self.attrName)
        if self.editable:
            button = self.radioButtonsByValue[value]
            button.SetValue(True)
        else:
            displayValue = self.choices[value]
            self.field.SetValue(displayValue)


class DateEditDialogColumn(EditDialogColumn):
    expandField = False

    def __init__(self, parent, attrName, labelText, allowNone = False,
            editable = True, showDropDown = False):
        if editable:
            field = parent.AddDateField(allowNone, showDropDown)
        else:
            field = parent.AddTextField(editable = False)
        self.editable = editable
        super(DateEditDialogColumn, self).__init__(parent, attrName, labelText,
                field, required = not allowNone)

    def SetValue(self, row):
        value = getattr(row, self.attrName)
        if self.editable:
            self.field.SetValue(value)
        elif value is None:
            self.field.SetValue("")
        else:
            self.field.SetValue(value.strftime(self.config.dateFormat))


class DecimalEditDialogColumn(EditDialogColumn):

    def __init__(self, parent, attrName, labelText, style = 0,
            digitsBeforeDecimal = 3, digitsAfterDecimal = 3,
            editable = True, required = False):
        field = parent.AddDecimalField(style = style, editable = editable,
                digitsBeforeDecimal = digitsBeforeDecimal,
                digitsAfterDecimal = digitsAfterDecimal)
        super(DecimalEditDialogColumn, self).__init__(parent, attrName,
                labelText, field, required = required)


class TextEditDialogColumn(EditDialogColumn):

    def __init__(self, parent, attrName, labelText, style = 0,
            maxLength = 0, size = (-1, -1), required = False,
            editable = True, cls = ceGUI.TextField, multiLine = False,
            constantValue = None, onChangeMethod = None, passEvent = False):
        field = parent.AddTextField(style, maxLength, size = size, cls = cls,
                editable = editable and constantValue is None,
                multiLine = multiLine)
        if editable and onChangeMethod is not None:
            parent.BindEvent(field, wx.EVT_TEXT, onChangeMethod,
                    passEvent = passEvent)
        super(TextEditDialogColumn, self).__init__(parent, attrName, labelText,
                field, required = required, constantValue = constantValue)


class ColorEditDialogColumn(TextEditDialogColumn):

    def __init__(self, parent, attrName, labelText, style = 0,
            editable = True, size = (-1, -1), buttonSize = (25, -1)):
        super(ColorEditDialogColumn, self).__init__(parent, attrName,
                labelText, maxLength = 8, size = size,
                cls = ceGUI.IntegerField, editable = editable)
        self.color = wx.Colour()
        self.button = parent.AddButton(size = buttonSize,
                method = self.OnChooseColor, enabled = editable,
                passEvent = False)

    def Layout(self, sizer):
        colorSizer = wx.BoxSizer(wx.HORIZONTAL)
        colorSizer.Add(self.field, flag = wx.RIGHT | wx.EXPAND, border = 5)
        colorSizer.Add(self.button)
        sizer.Add(self.label, flag = wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(colorSizer, flag = wx.ALIGN_CENTER_VERTICAL | wx.EXPAND)

    def OnChooseColor(self):
        colorData = wx.ColourData()
        colorData.SetColour(self.color)
        with wx.ColourDialog(self.button.GetParent(), colorData) as dialog:
            if dialog.ShowModal() == wx.ID_OK:
                self.color = dialog.GetColourData().GetColour()
                self.button.SetBackgroundColour(self.color)
                self.button.Refresh()
                self.field.SetValue(self.color.GetRGB())

    def SetValue(self, row):
        color = getattr(row, self.attrName)
        self.field.SetValue(color)
        self.color.SetRGB(color)
        self.button.SetBackgroundColour(self.color)
        self.button.Refresh()


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
        self._DisplayNumItems()

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


class MissingColumn(cx_Exceptions.BaseException):
    message = 'Missing column with attribute named "%(attrName)s".'


class MissingFilterArg(cx_Exceptions.BaseException):
    message = 'Missing filter argument named "%(name)s".'

