"""
Define commonly used panels.
"""

import ceGUI
import wx

__all__ = [ "ListPanel", "OrderedListPanel" ]

class ListPanel(ceGUI.Panel):
    listClassName = "List"

    def OnCreate(self):
        cls = self._GetClass(self.listClassName)
        self.list = cls(self)

    def OnLayout(self):
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.list, proportion = 1, flag = wx.EXPAND)
        return sizer

    def RestoreSettings(self):
        self.list.RestoreColumnWidths()

    def SaveSettings(self):
        self.list.SaveColumnWidths()


class OrderedListPanel(ListPanel):

    def _CanMoveDown(self, itemIndex):
        return itemIndex < len(self.list.rowHandles) - 1

    def _CanMoveUp(self, itemIndex):
        return itemIndex > 0

    def _SetMoveButtonStatus(self):
        if self.list.GetSelectedItemCount() != 1:
            canMoveUp = canMoveDown = False
        else:
            itemIndex, = self.list.GetSelectedItemIndexes()
            canMoveUp = self._CanMoveUp(itemIndex)
            canMoveDown = self._CanMoveDown(itemIndex)
        self.moveUpButton.Enable(canMoveUp)
        self.moveDownButton.Enable(canMoveDown)

    def OnCreate(self):
        super(OrderedListPanel, self).OnCreate()
        self.BindEvent(self.list, wx.EVT_LIST_ITEM_SELECTED,
                self.OnItemSelected, passEvent = False)
        self.BindEvent(self.list, wx.EVT_LIST_ITEM_DESELECTED,
                self.OnItemDeselected, passEvent = False)
        self.moveUpButton = self.AddButton("Move Up", enabled = False,
                method = self.OnMoveUp, passEvent = False)
        self.moveDownButton = self.AddButton("Move Down", enabled = False,
                method = self.OnMoveDown, passEvent = False)

    def OnItemDeselected(self):
        self._SetMoveButtonStatus()
        
    def OnItemSelected(self):
        self._SetMoveButtonStatus()
        
    def OnLayout(self):
        moveButtonSizer = wx.BoxSizer(wx.VERTICAL)
        moveButtonSizer.AddStretchSpacer()
        moveButtonSizer.Add(self.moveUpButton,
                flag = wx.BOTTOM | wx.ALIGN_CENTER_VERTICAL, border = 5)
        moveButtonSizer.Add(self.moveDownButton,
                flag = wx.ALIGN_CENTER_VERTICAL)
        moveButtonSizer.AddStretchSpacer()
        mainSizer = wx.BoxSizer(wx.HORIZONTAL)
        mainSizer.Add(self.list, flag = wx.EXPAND, proportion = 1)
        mainSizer.Add(moveButtonSizer, flag = wx.LEFT | wx.EXPAND, border = 5)
        topSizer = wx.BoxSizer(wx.VERTICAL)
        topSizer.Add(mainSizer, flag = wx.ALL | wx.EXPAND, border = 5,
                proportion = 1)
        return topSizer

    def OnMoveDown(self):
        self.list.MoveItem(1)
        
    def OnMoveUp(self):
        self.list.MoveItem(-1)

