"""
Define windows used for editing data.
"""

import ceGUI
import cx_Exceptions
import cx_Logging
import functools
import os
import wx

__all__ = [ "GridEditWindow", "SubWindow" ]


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

