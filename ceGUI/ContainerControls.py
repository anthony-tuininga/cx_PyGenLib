"""
Defines controls that contain other controls with extensions to wx
functionality.
"""

import ceGUI
import os
import wx
import sys

__all__ = ["BaseContainer", "Dialog", "Frame", "Panel", "PreviewFrame",
           "ScrolledPanel", "StandardDialog", "TopLevelFrame"]


class BaseContainer(ceGUI.BaseControl):
    saveSize = savePosition = bindClose = True
    saveWidthOnly = False
    instanceName = None
    defaultSize = None
    defaultWidth = None
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
        if self.saveWidthOnly:
            width = self.ReadSetting("Width", self.defaultWidth,
                    converter = int)
            if width is not None:
                origWidth, height = self.GetSizeTuple()
                self.SetSize((width, height))
        elif self.saveSize:
            size = self.ReadSetting("Size", self.defaultSize or self.minSize,
                    converter = eval)
            if size is not None:
                self.SetSize(size)
        if self.savePosition:
            position = self.ReadSetting("Position", converter = eval)
            if position is not None:
                self.SetPosition(position)
        self.RestoreSettings()

    def _SaveSettings(self):
        if not hasattr(self, "IsIconized") or not self.IsIconized():
            if self.saveWidthOnly:
                width, height = self.GetSizeTuple()
                self.WriteSetting("Width", width)
            elif self.saveSize:
                self.WriteSetting("Size", self.GetSizeTuple())
            if self.savePosition:
                self.WriteSetting("Position", self.GetPositionTuple())
        self.SaveSettings()
        self.settings.Flush()

    def AddButton(self, label = "", method = None, size = (-1, -1),
            passEvent = True, enabled = True):
        button = wx.Button(self, -1, label, size = size)
        if not enabled:
            button.Enable(False)
        if method is not None:
            self.BindEvent(button, wx.EVT_BUTTON, method,
                    passEvent = passEvent)
        return button

    def AddCalendarField(self):
        return ceGUI.CalendarField(self)

    def AddCheckBox(self, label = ""):
        return wx.CheckBox(self, -1, label)

    def AddChoiceField(self, choices = None, size = (-1, -1)):
        if choices is None:
            choices = []
        return ceGUI.Choice(self, choices, size)

    def AddDateField(self, allowNone = False, showDropDown = False):
        return ceGUI.DateField(self, allowNone, showDropDown)

    def AddDecimalField(self, style = 0, digitsBeforeDecimal = 3,
            digitsAfterDecimal = 3, editable = True):
        if not editable:
            style |= wx.TE_READONLY
        return ceGUI.DecimalField(self, style = style,
                digitsBeforeDecimal = digitsBeforeDecimal,
                digitsAfterDecimal = digitsAfterDecimal)

    def AddIntegerField(self, style = 0, editable = True):
        if not editable:
            style |= wx.TE_READONLY
        return ceGUI.IntegerField(self, style)

    def AddLabel(self, label = "", size = (-1, -1)):
        return wx.StaticText(self, -1, label, size = size)

    def AddStaticBox(self, label):
        return wx.StaticBox(self, -1, label)

    def AddTextField(self, style = 0, maxLength = 0, cls = ceGUI.TextField,
            size = (-1, -1), editable = True, multiLine = False):
        if not editable:
            style |= wx.TE_READONLY
        if multiLine:
            style |= wx.TE_MULTILINE
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

    def RunReport(self, className, *args):
        cls = self._GetClass(className)
        report = cls()
        report.Preview(args, parent = self)

    def UpdateChanges(self):
        pass


class Dialog(BaseContainer, wx.Dialog):
    createOkButton = createCancelButton = True
    createCloseButton = False
    style = wx.DEFAULT_DIALOG_STYLE
    title = ""

    def __init__(self, parent = None, instanceName = None):
        wx.Dialog.__init__(self, parent, title = self.title,
                style = self.style)
        self.instanceName = instanceName
        self._Initialize()

    def _OnCreate(self):
        if self.createCloseButton:
            self.closeButton = wx.Button(self, wx.ID_CANCEL, "Close")
            self.BindEvent(self.closeButton, wx.EVT_BUTTON, self._OnCancel)
        else:
            if self.createOkButton:
                self.okButton = wx.Button(self, wx.ID_OK)
                self.BindEvent(self.okButton, wx.EVT_BUTTON, self._OnOk,
                        createBusyCursor = True)
            if self.createCancelButton:
                self.cancelButton = wx.Button(self, wx.ID_CANCEL)
                self.BindEvent(self.cancelButton, wx.EVT_BUTTON,
                        self._OnCancel)
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

    def ShowModalOk(self):
        return self.ShowModal() == wx.ID_OK


class Frame(BaseContainer, wx.Frame):
    style = wx.DEFAULT_FRAME_STYLE
    hasToolbar = hasMenus = True
    hasIcon = False
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
        if self.hasIcon:
            self.OnSetIcon()

    def AddMenu(self, label):
        menu = ceGUI.Menu()
        menu.AddToMenuBar(self.menuBar, label)
        return menu

    def AddMenuItem(self, menu, label, helpString = "", method = None,
            createBusyCursor = False, passEvent = True, radio = False,
            checkable = False, windowName = None, enabled = True):
        return menu.AddEntry(self, label, helpString, method, createBusyCursor,
                passEvent, radio, checkable, windowName, enabled)

    def AddStockMenuItem(self, menu, stockId, method = None,
            createBusyCursor = False, enabled = True):
        return menu.AddStockEntry(self, stockId, method, createBusyCursor,
                enabled)

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

    def OnSetIcon(self):
        iconFile = sys.executable
        name, ext = os.path.splitext(iconFile)
        if ext == ".py":
            iconFile = name + ".ico"
        icon = wx.Icon(iconFile, wx.BITMAP_TYPE_ICO, 16, 16)
        self.SetIcon(icon)

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


class PreviewFrame(BaseContainer, wx.PreviewFrame):

    def __init__(self, preview, parent):
        wx.PreviewFrame.__init__(self, preview, parent, title = self.title)
        self.preview = preview
        self._Initialize()
        self.Initialize()
        self.Show(True)

    def RestoreSettings(self):
        zoom = self.ReadSetting("Zoom", isComplex = True)
        if zoom is not None:
            self.preview.Zoom = zoom

    def SaveSettings(self):
        self.WriteSetting("Zoom", self.preview.Zoom, isComplex = True)


class ScrolledPanel(Panel, wx.ScrolledWindow):

    def __init__(self, parent, style = wx.HSCROLL | wx.VSCROLL,
            instanceName = None):
        wx.ScrolledWindow.__init__(self, parent, style = style)
        self.instanceName = instanceName
        self._Initialize()


class StandardDialog(Dialog):
    style = wx.CAPTION | wx.RESIZE_BORDER
    panelClassName = "Panel"

    def _GetButtons(self):
        buttons = []
        if self.createCloseButton:
            buttons.append(self.closeButton)
        else:
            if self.createOkButton:
                buttons.append(self.okButton)
            if self.createCancelButton:
                buttons.append(self.cancelButton)
        return buttons

    def _LayoutButtons(self, sizer):
        sizer.AddStretchSpacer()
        for button in self._GetButtons():
            sizer.Add(button, flag = wx.ALL | wx.ALIGN_CENTER_VERTICAL,
                    border = 5)
        return sizer

    def _OnLayout(self, topSizer):
        buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
        self._LayoutButtons(buttonSizer)
        topSizer.Add(buttonSizer, flag = wx.EXPAND)
        super(StandardDialog, self)._OnLayout(topSizer)

    def IsEditingCanceled(self):
        return False

    def OnCreate(self):
        cls = self._GetClass(self.panelClassName)
        self.panel = cls(self)

    def OnLayout(self):
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.panel, flag = wx.EXPAND, proportion = 1)
        return sizer

    def RestoreSettings(self):
        self.panel.RestoreSettings()

    def SaveSettings(self):
        self.panel.SaveSettings()


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

