"""
Defines controls that contain other controls with extensions to wx
functionality.
"""

import ceGUI
import wx

__all__ = ["BaseContainer", "Dialog", "Frame", "Panel", "TopLevelFrame" ]


class BaseContainer(ceGUI.BaseControl):
    saveSize = savePosition = bindClose = True

    def _OnClose(self, event):
        self._SaveSettings()
        self.OnClose()
        event.Skip()

    def _OnCreate(self):
        if self.bindClose:
            self.Bind(wx.EVT_CLOSE, self._OnClose)
        self.OnCreate()
        topSizer = self.OnLayout()
        if topSizer is not None:
            self.SetSizer(topSizer)
            if self.minSize is None:
                topSizer.Fit(self)
        self._RestoreSettings()

    def BindEvent(self, control, event, method, createBusyCursor = False,
            skipEvent = True):
        ceGUI.EventHandler(self, control, event, method,
                createBusyCursor = createBusyCursor, skipEvent = skipEvent)

    def OnClose(self):
        pass


class Dialog(BaseContainer, wx.Dialog):
    createOkButton = createCancelButton = True

    def __init__(self, *args, **kwargs):
        wx.Dialog.__init__(self, *args, **kwargs)
        self._Initialize()

    def _OnCreate(self):
        if self.createOkButton:
            self.okButton = wx.Button(self, wx.ID_OK)
            self.BindEvent(self.okButton, wx.EVT_BUTTON, self._OnOk,
                    createBusyCursor = True)
        if self.createCancelButton:
            self.cancelButton = wx.Button(self, wx.ID_CANCEL)
            self.BindEvent(self.cancelButton, wx.EVT_BUTTON, self._OnCancel)
        super(Dialog, self)._OnCreate()

    def _OnOk(self, event):
        self.OnOk()
        self._SaveSettings()

    def _OnCancel(self, event):
        self.OnCancel()
        self._SaveSettings()

    def OnCancel(self):
        pass

    def OnOk(self):
        pass


class Frame(BaseContainer, wx.Frame):
    hasToolbar = hasMenus = True

    def __init__(self, *args, **kwargs):
        wx.Frame.__init__(self, *args, **kwargs)
        self._Initialize()

    def _AddMenuItem(self, menu, label = "", helpString = "",
            kind = wx.ITEM_NORMAL, method = None, createBusyCursor = False,
            id = None):
        if id is None:
            id = wx.NewId()
        item = wx.MenuItem(menu, id, label, helpString, kind)
        menu.AppendItem(item)
        if method is not None:
            self.BindEvent(item, wx.EVT_MENU, method,
                    createBusyCursor = createBusyCursor)
        return item

    def _OnCreate(self):
        if self.hasToolbar:
            self.toolbar = wx.ToolBar(self)
            self.SetToolBar(self.toolbar)
            self.OnCreateToolbar()
            self.toolbar.Realize()
        if self.hasMenus:
            self.menuBar = wx.MenuBar()
            self.SetMenuBar(self.menuBar)
            self.OnCreateMenus()
        super(Frame, self)._OnCreate()

    def AddMenu(self, label):
        menu = wx.Menu()
        self.menuBar.Append(menu, label)
        return menu

    def AddMenuItem(self, menu, label, helpString = "", method = None,
            createBusyCursor = False):
        return self._AddMenuItem(menu, label, helpString,
                method = method, createBusyCursor = createBusyCursor)

    def AddStockMenuItem(self, menu, stockId, method = None,
            createBusyCursor = False):
        return self._AddMenuItem(menu, id = stockId, method = method,
                createBusyCursor = createBusyCursor)

    def AddToolbarItem(self, label, bitmapId, shortHelp = "", longHelp = "",
            method = None, createBusyCursor = False):
        bitmap = wx.ArtProvider.GetBitmap(bitmapId, wx.ART_TOOLBAR,
                self.toolbar.GetToolBitmapSize())
        item = self.toolbar.AddLabelTool(-1, label, bitmap,
                shortHelp = shortHelp, longHelp = longHelp)
        if method is not None:
            self.BindEvent(item, wx.EVT_TOOL, method,
                    createBusyCursor = createBusyCursor)
        return item

    def OnCreateToolbar(self):
        pass


class Panel(BaseContainer, wx.Panel):
    saveSize = savePosition = bindClose = False

    def __init__(self, *args, **kwargs):
        wx.Panel.__init__(self, *args, **kwargs)
        self._Initialize()


class TopLevelFrame(Frame):
    baseSettingsName = ""

    def OnAbout(self, event):
        dialog = ceGUI.AboutDialog(self)
        dialog.ShowModal()

    def OnEditPreferences(self, event):
        dialog = ceGUI.PreferencesDialog(self)
        dialog.ShowModal()

    def OnExit(self, event):
        self.Close()

