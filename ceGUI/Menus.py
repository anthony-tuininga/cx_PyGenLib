"""
Defines menu functionality.
"""

import ceGUI
import functools
import wx

__all__ = ["Menu"]

class Menu(object):

    def __init__(self):
        self.menu = wx.Menu()

    def _AddEntry(self, parent, label = "", helpString = "",
            kind = wx.ITEM_NORMAL, method = None, createBusyCursor = False,
            id = None, skipEvent = False, passEvent = True, enabled = True,
            pos = None):
        if id is None:
            id = wx.NewId()
        item = wx.MenuItem(self.menu, id, label, helpString, kind)
        if pos is None:
            self.menu.Append(item)
        else:
            self.menu.Insert(pos, item)
        if not enabled:
            item.Enable(False)
        if method is not None:
            parent.BindEvent(item, wx.EVT_MENU, method, passEvent = passEvent,
                    skipEvent = skipEvent, createBusyCursor = createBusyCursor)
        return item

    def AddEntry(self, parent, label, helpString = "", method = None,
            createBusyCursor = False, passEvent = True, radio = False,
            checkable = False, windowName = None, enabled = True, pos = None):
        if radio:
            kind = wx.ITEM_RADIO
        elif checkable:
            kind = wx.ITEM_CHECK
        else:
            kind = wx.ITEM_NORMAL
        if windowName is not None:
            method = functools.partial(parent.SimpleOpenWindow, windowName)
            passEvent = False
        return self._AddEntry(parent, label, helpString, kind, method,
                createBusyCursor, passEvent = passEvent, enabled = enabled,
                pos = pos)

    def AddSeparator(self):
        self.menu.AppendSeparator()

    def AddStockEntry(self, parent, stockId, method = None,
            createBusyCursor = False, enabled = True, passEvent = True):
        return self._AddEntry(parent, id = stockId, method = method,
                createBusyCursor = createBusyCursor, enabled = enabled,
                passEvent = passEvent)

    def AddToMenuBar(self, menuBar, label):
        menuBar.Append(self.menu, label)

    def Destroy(self):
        self.menu.Destroy()

    def Popup(self, parent):
        parent.PopupMenu(self.menu)

