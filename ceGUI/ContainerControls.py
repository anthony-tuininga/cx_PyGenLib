"""
Defines controls that contain other controls with extensions to wx
functionality.
"""

import ceGUI
import functools
import wx

__all__ = ["BaseContainer", "Dialog", "Frame", "Panel", "ScrolledPanel",
           "StandardDialog", "TopLevelFrame" ]


class BaseContainer(ceGUI.BaseControl):
    saveSize = savePosition = bindClose = True
    instanceName = None
    minSize = None
    closing = False

    def _Initialize(self):
        if self.minSize is not None:
            self.SetMinSize(self.minSize)
        super(BaseContainer, self)._Initialize()

    def _OnClose(self, event):
        self.closing = True
        self._SaveSettings()
        self.OnClose(event)

    def _OnCreate(self):
        if self.bindClose:
            self.Bind(wx.EVT_CLOSE, self._OnClose)
        self.OnCreate()
        topSizer = self.OnLayout()
        if topSizer is not None:
            self._OnLayout(topSizer)
        self._RestoreSettings()

    def _OnLayout(self, topSizer):
        self.SetSizer(topSizer)
        if self.minSize is None:
            topSizer.Fit(self)

    def _RestoreSettings(self):
        if self.saveSize:
            size = self.ReadSetting("Size", self.minSize, isComplex = True)
            if size is not None:
                self.SetSize(size)
        if self.savePosition:
            position = self.ReadSetting("Position", isComplex = True)
            if position is not None:
                self.SetPosition(position)
        self.RestoreSettings()

    def _SaveSettings(self):
        if self.saveSize:
            self.WriteSetting("Size", self.GetSizeTuple(), isComplex = True)
        if self.savePosition:
            self.WriteSetting("Position", self.GetPositionTuple(),
                    isComplex = True)
        self.SaveSettings()
        self.settings.Flush()

    def AddButton(self, label = "", method = None, size = (-1, -1)):
        button = wx.Button(self, -1, label, size = size)
        if method is not None:
            self.BindEvent(button, wx.EVT_BUTTON, method)
        return button

    def AddCheckBox(self, label = ""):
        return wx.CheckBox(self, -1, label)

    def AddChoiceField(self, *choices):
        return ceGUI.Choice(self, choices)

    def AddIntegerField(self, style = 0):
        return ceGUI.IntegerField(self, style)

    def AddLabel(self, label = "", size = (-1, -1)):
        return wx.StaticText(self, -1, label, size = size)

    def AddTextField(self, style = 0, maxLength = 0, cls = ceGUI.TextField,
            size = (-1, -1)):
        return cls(self, style, maxLength, size)

    def ContinueQuery(self, allowCancel = True):
        if self.PendingChanges():
            message = "Do you want to save your changes?"
            flag = wx.YES_NO | wx.ICON_EXCLAMATION
            if allowCancel:
                flag |= wx.CANCEL
            dialog = wx.MessageDialog(self, message, self.GetTitle(), flag)
            response = dialog.ShowModal()
            if response == wx.ID_YES:
                self.UpdateChanges()
            elif response == wx.ID_CANCEL:
                return False
        return self.ContinueQueryChildren(allowCancel)

    def ContinueQueryChildren(self, allowCancel = True):
        for window in self.GetChildren():
            if not isinstance(window, BaseContainer):
                continue
            if not window.ContinueQuery(allowCancel):
                return False
        return True

    def CreateFieldLayout(self, *controls):
        numRows = len(controls) / 2
        sizer = wx.FlexGridSizer(rows = numRows, cols = 2, vgap = 5, hgap = 5)
        sizer.AddGrowableCol(1)
        for index, control in enumerate(controls):
            flag = wx.ALIGN_CENTER_VERTICAL
            if index % 2 == 1:
                flag |= wx.EXPAND
            sizer.Add(control, flag = flag)
        return sizer

    def OnClose(self, event):
        if self.ContinueQuery():
            event.Skip()
        else:
            event.Veto()

    def OpenWindow(self, name, forceNewInstance = False, instanceName = None,
            **kwargs):
        return ceGUI.OpenWindow(name, self, forceNewInstance, instanceName,
                **kwargs)

    def PendingChanges(self):
        return False

    def UpdateChanges(self):
        pass


class Dialog(BaseContainer, wx.Dialog):
    createOkButton = createCancelButton = True
    style = wx.DEFAULT_DIALOG_STYLE
    title = ""

    def __init__(self, parent = None, instanceName = None):
        wx.Dialog.__init__(self, parent, title = self.title,
                style = self.style)
        self.instanceName = instanceName
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
    style = wx.DEFAULT_FRAME_STYLE
    hasToolbar = hasMenus = True
    title = ""

    def __init__(self, parent = None, instanceName = None):
        wx.Frame.__init__(self, parent, title = self.title, style = self.style)
        self.instanceName = instanceName
        self._Initialize()

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
            createBusyCursor = False, passEvent = True, radio = False,
            checkable = False, windowName = None, enabled = True):
        if radio:
            kind = wx.ITEM_RADIO
        elif checkable:
            kind = wx.ITEM_CHECK
        else:
            kind = wx.ITEM_NORMAL
        if windowName is not None:
            method = functools.partial(self.SimpleOpenWindow, windowName)
            passEvent = False
        return self._AddMenuItem(menu, label, helpString, kind, method,
                createBusyCursor, passEvent = passEvent, enabled = enabled)

    def AddStockMenuItem(self, menu, stockId, method = None,
            createBusyCursor = False, enabled = True):
        return self._AddMenuItem(menu, id = stockId, method = method,
                createBusyCursor = createBusyCursor, enabled = enabled)

    def AddToolbarItem(self, label, bitmapId, shortHelp = "", longHelp = "",
            method = None, createBusyCursor = False, passEvent = True,
            enabled = True):
        bitmap = wx.ArtProvider.GetBitmap(bitmapId, wx.ART_TOOLBAR,
                self.toolbar.GetToolBitmapSize())
        item = self.toolbar.AddLabelTool(-1, label, bitmap,
                shortHelp = shortHelp, longHelp = longHelp)
        if not enabled:
            item.Enable(False)
        if method is not None:
            self.BindEvent(item, wx.EVT_TOOL, method,
                    createBusyCursor = createBusyCursor, passEvent = passEvent)
        return item

    def OnCreateToolbar(self):
        pass

    def SimpleOpenWindow(self, windowName):
        window = self.OpenWindow(windowName)
        window.Show()


class Panel(BaseContainer, wx.Panel):
    saveSize = savePosition = bindClose = False

    def __init__(self, parent, style = wx.TAB_TRAVERSAL,
            instanceName = None):
        wx.Panel.__init__(self, parent, style = style)
        self.instanceName = instanceName
        self._Initialize()


class ScrolledPanel(Panel, wx.ScrolledWindow):

    def __init__(self, parent, style = wx.HSCROLL | wx.VSCROLL,
            instanceName = None):
        wx.ScrolledWindow.__init__(self, parent, style = style)
        self.instanceName = instanceName
        self._Initialize()


class StandardDialog(Dialog):
    style = wx.CAPTION | wx.RESIZE_BORDER

    def _GetButtons(self):
        buttons = []
        if self.createOkButton:
            buttons.append(self.okButton)
        if self.createCancelButton:
            buttons.append(self.cancelButton)
        return buttons

    def _OnLayout(self, topSizer):
        buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
        buttonSizer.AddStretchSpacer()
        for button in self._GetButtons():
            buttonSizer.Add(button, flag = wx.ALL | wx.ALIGN_CENTER_VERTICAL,
                    border = 5)
        topSizer.Add(buttonSizer, flag = wx.EXPAND)
        super(StandardDialog, self)._OnLayout(topSizer)


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

