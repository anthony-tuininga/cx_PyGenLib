"""
Define commonly used dialogs.
"""

import ceGUI
import cx_Exceptions
import cx_Logging
import os
import wx

__all__ = [ "AboutDialog", "PreferencesDialog", "SelectionListDialog",
            "SelectionCheckListDialog", "SelectionTreeDialog" ]


class AboutDialog(ceGUI.Dialog):
    baseSettingsName = "w_About"
    createCancelButton = False
    saveSize = False

    def __init__(self, parent):
        super(AboutDialog, self).__init__(parent, wx.CAPTION)

    def OnCreate(self):
        app = wx.GetApp()
        self.SetTitle("About %s" % app.description)
        self.panel = ceGUI.Panel(self, wx.SUNKEN_BORDER)
        aboutText = app.description
        if app.version is not None:
            aboutText = "%s\n\nVersion %s" % (aboutText, app.version)
        if app.copyrightOwner is not None:
            if app.copyrightStartYear == app.copyrightEndYear:
                copyrightYears = app.copyrightEndYear
            else:
                copyrightYears = "%s-%s" % \
                        (app.copyrightStartYear, app.copyrightEndYear)
            aboutText = "%s\n\nCopyright %s\n%s" % \
                    (aboutText, copyrightYears, app.copyrightOwner)
        self.aboutLabel = wx.StaticText(self.panel, -1, aboutText,
                style = wx.ALIGN_CENTRE)

    def OnLayout(self):
        panelSizer = wx.BoxSizer(wx.VERTICAL)
        panelSizer.Add(self.aboutLabel, flag = wx.ALL | wx.EXPAND, border = 5)
        self.panel.SetSizer(panelSizer)
        topSizer = wx.BoxSizer(wx.VERTICAL)
        topSizer.Add(self.panel, flag = wx.ALL | wx.EXPAND, border = 5)
        topSizer.Add(self.okButton,
                flag = wx.ALL | wx.ALIGN_CENTER_HORIZONTAL | \
                        wx.ALIGN_CENTER_VERTICAL, border = 5)
        return topSizer


class LoggingPreferencesPane(ceGUI.Panel):
    loggingLevels = "DEBUG INFO WARNING ERROR CRITICAL".split()

    def OnCreate(self):
        self.fileNameLabel = wx.StaticText(self, -1, "File Name:")
        self.fileNameField = wx.TextCtrl(self, -1)
        self.selectFileNameButton = wx.Button(self, -1, "...",
                size = (25, -1))
        self.BindEvent(self.selectFileNameButton, wx.EVT_BUTTON,
                self.OnSelectFileName)
        self.levelLabel = wx.StaticText(self, -1, "Level:")
        self.levelField = wx.Choice(self, -1, choices = self.loggingLevels)

    def OnLayout(self):
        fileNameSizer = wx.BoxSizer(wx.HORIZONTAL)
        fileNameSizer.Add(self.fileNameField, proportion = 1, flag = wx.RIGHT,
                border = 5)
        fileNameSizer.Add(self.selectFileNameButton)
        fieldLayout = self.CreateFieldLayout(self.fileNameLabel, fileNameSizer,
                self.levelLabel, self.levelField)
        topSizer = wx.BoxSizer(wx.VERTICAL)
        topSizer.Add(fieldLayout, flag = wx.ALL | wx.EXPAND, border = 5,
                proportion = 1)
        return topSizer

    def OnSelectFileName(self, event):
        currentFileName = self.fileNameField.GetValue()
        dir, fileName = os.path.split(currentFileName)
        dialog = wx.FileDialog(self, "Select log file", wildcard = "*.log",
                defaultDir = dir, defaultFile = fileName,
                style = wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
        if dialog.ShowModal() == wx.ID_OK:
            fileName = dialog.GetPath()
            if not fileName.lower().endswith(".log"):
                fileName += ".log"
            self.fileNameField.SetValue(fileName)

    def RestoreSettings(self):
        defaultFileName = wx.GetApp().GetDefaultLoggingFileName()
        fileName = self.settings.Read("LogFileName", defaultFileName)
        self.fileNameField.SetValue(fileName)
        levelName = self.settings.Read("LogLevel", "ERROR")
        self.levelField.SetStringSelection(levelName)

    def SaveSettings(self):
        fileName = self.fileNameField.GetValue()
        if not fileName:
            self.fileNameField.SetFocus()
            raise LoggingFileNameNotSpecified()
        levelName = self.levelField.GetStringSelection()
        level = getattr(cx_Logging, levelName)
        if fileName != cx_Logging.GetLoggingFileName():
            cx_Logging.StartLogging(fileName, level)
        elif level != cx_Logging.GetLoggingLevel():
            cx_Logging.SetLoggingLevel(level)
        self.settings.Write("LogFileName", fileName)
        self.settings.Write("LogLevel", levelName)


class PreferencesDialog(ceGUI.StandardDialog):
    baseSettingsName = "w_Preferences"
    defaultSize = (450, 157)

    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, "Edit Preferences",
                style = wx.CAPTION | wx.RESIZE_BORDER)
        self._Initialize()

    def OnCreate(self):
        self.notebook = ceGUI.Notebook(self, -1)
        self.OnCreateNotebook()
        pane = LoggingPreferencesPane(self.notebook)
        self.notebook.AddPage(pane, "Logging")
        self.notebook.RestoreSettings()

    def OnCreateNotebook(self):
        pass

    def OnOk(self):
        self.notebook.SaveSettings()
        self.settings.Flush()

    def OnLayout(self):
        topSizer = wx.BoxSizer(wx.VERTICAL)
        topSizer.Add(self.notebook, proportion = 1,
                flag = wx.EXPAND | wx.RIGHT | wx.LEFT | wx.TOP, border = 5)
        return topSizer

    def RestoreSettings(self):
        pass

    def SaveSettings(self):
        pass


class SelectionListDialog(ceGUI.StandardDialog):
    listClassName = "List"
    selectFirstItem = True

    def _GetList(self):
        cls = self._GetClass(self.listClassName)
        return cls(self, wx.SUNKEN_BORDER)

    def GetSelectedItem(self):
        return self.selectionList.GetSelectedItem()

    def GetSelectedItems(self):
        return self.selectionList.GetSelectedItems()

    def OnCreate(self):
        self.okButton.Enable(False)
        self.selectionList = self._GetList()
        self.selectionList.SetFocus()
        self.BindEvent(self.selectionList, wx.EVT_LIST_ITEM_SELECTED,
                self.OnItemSelected)
        self.BindEvent(self.selectionList, wx.EVT_LIST_ITEM_DESELECTED,
                self.OnItemDeselected)
        self.BindEvent(self.selectionList, wx.EVT_LIST_ITEM_ACTIVATED,
                self.OnItemActivated)
        self.BindEvent(self.selectionList, wx.EVT_CHAR,
                self.OnCharPressed)

    def OnCharPressed(self, event):
        key = event.GetKeyCode()
        if key == 1 and not self.selectionList.singleSelection: # Ctrl-A
            self.selectionList.SelectAll()
        elif key == wx.WXK_RETURN and self.GetSelectedItems():
            self._OnOk(event)
            self.EndModal(wx.ID_OK)
        event.Skip()

    def OnItemActivated(self, event):
        self._OnOk(event)
        self.EndModal(wx.ID_OK)

    def OnItemDeselected(self, event):
        if self.selectionList.GetSelectedItemCount() == 0:
            self.okButton.Enable(False)

    def OnItemSelected(self, event):
        self.okButton.Enable()

    def OnLayout(self):
        topSizer = wx.BoxSizer(wx.VERTICAL)
        topSizer.Add(self.selectionList, proportion = 1, flag = wx.EXPAND)
        return topSizer

    def RestoreSettings(self):
        self.selectionList.RestoreColumnWidths()

    def Retrieve(self, *args):
        self.selectionList.Retrieve(*args)
        if self.selectFirstItem and len(self.selectionList.rowHandles) > 0:
            handle = self.selectionList.rowHandles[0]
            item = self.selectionList.dataSet.rows[handle]
            self.selectionList.SelectItems([item])

    def SaveSettings(self):
        self.selectionList.SaveColumnWidths()

    def SelectItems(self, items):
        self.selectionList.SelectItems(items)


class SelectionCheckListDialog(ceGUI.StandardDialog):
    listClassName = "List"
    checkedAttrName = "checked"

    def _GetList(self):
        cls = self._GetClass(self.listClassName)
        return cls(self, wx.SUNKEN_BORDER)

    def CheckAllItems(self):
        self.list.CheckAllItems()

    def GetCheckedItems(self):
        return self.list.GetCheckedItems()

    def OnCreate(self):
        self.list = self._GetList()

    def OnLayout(self):
        topSizer = wx.BoxSizer(wx.VERTICAL)
        topSizer.Add(self.list, proportion = 1, flag = wx.EXPAND)
        return topSizer

    def RestoreSettings(self):
        self.list.RestoreColumnWidths()

    def Retrieve(self, *args):
        self.list.Retrieve(*args)

    def SaveSettings(self):
        self.list.SaveColumnWidths()

    def UncheckAllItems(self):
        self.list.UncheckAllItems()


class SelectionTreeDialog(ceGUI.StandardDialog):
    treeClassName = "Tree"

    def _GetTree(self):
        cls = self._GetClass(self.treeClassName)
        return cls(self, -1, style = wx.TR_HAS_BUTTONS | wx.TR_HIDE_ROOT | \
                wx.TR_LINES_AT_ROOT)

    def _OnItemActivated(self, event):
        itemId = event.GetItem()
        item = self.selectionTree.GetItemData(itemId)
        if self.CanSelectItem(item.data):
            self.EndModal(wx.ID_OK)

    def _OnSelectionChanged(self, event):
        if self.okButton and self.selectionTree:
            itemId = event.GetItem()
            item = self.selectionTree.GetItemData(itemId)
            self.okButton.Enable(self.CanSelectItem(item.data))

    def CanSelectItem(self, item):
        return True

    def GetSelectedItem(self):
        return self.selectionTree.GetSelectedItem()

    def GetSelectedItemParents(self):
        item = self.selectionTree.GetSelectedItem()
        return self.selectionTree.GetItemParents(item)

    def OnCreate(self):
        self.okButton.Enable(False)
        self.selectionTree = self._GetTree()
        self.BindEvent(self.selectionTree, wx.EVT_TREE_SEL_CHANGED,
                self._OnSelectionChanged)
        self.BindEvent(self.selectionTree, wx.EVT_TREE_ITEM_ACTIVATED,
                self._OnItemActivated)

    def OnLayout(self):
        topSizer = wx.BoxSizer(wx.VERTICAL)
        topSizer.Add(self.selectionTree, proportion = 1, flag = wx.EXPAND)
        return topSizer

    def RestoreSettings(self):
        pass

    def SaveSettings(self):
        pass


class LoggingFileNameNotSpecified(cx_Exceptions.BaseException):
    message = "Logging file name must be specified."

