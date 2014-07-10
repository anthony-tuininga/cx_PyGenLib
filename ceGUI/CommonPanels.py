"""
Define commonly used panels.
"""

import ceGUI
import wx

__all__ = [ "ListPanel", "OrderedListPanel", "SelectListPanel" ]

class ListPanel(ceGUI.Panel):
    listClassName = "List"

    def _GetNumItems(self):
        return self.list.GetItemCount()

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


class SelectListPanel(ceGUI.Panel):
    availableListClassName = "AvailableList"
    selectedListClassName = "SelectedList"
    selectedListIsOrdered = True
    layoutHorizontally = True

    def __MoveItems(self, fromList, itemIndexes, toList, button):
        for itemIndex in itemIndexes:
            item = fromList.GetItem(itemIndex)
            fromList.DeleteItem(itemIndex)
            toList.AppendItem(item = item)
        if fromList.GetSelectedItemCount() == 0:
            button.Enable(False)

    def _GetAvailableList(self):
        cls = self._GetClass(self.availableListClassName)
        return cls(self)

    def _GetSelectedList(self):
        cls = self._GetClass(self.selectedListClassName)
        return cls(self)

    def _LayoutAvailableList(self, mainSizer):
        mainSizer.Add(self.availableList, flag = wx.EXPAND, proportion = 1)

    def _LayoutSelectedList(self, mainSizer):
        mainSizer.Add(self.selectedList, flag = wx.EXPAND, proportion = 1)

    def _MoveItems(self, fromList, toList, button):
        itemIndexes = list(fromList.GetSelectedItemIndexes())
        self.__MoveItems(fromList, reversed(itemIndexes), toList, button)

    def _OnListItemDoubleClicked(self, event, fromList, toList, button):
        itemIndex, flags = fromList.HitTest(event.GetPosition())
        if flags & wx.LIST_HITTEST_ONITEM:
            self.__MoveItems(fromList, [itemIndex], toList, button)

    def _SetMoveButtonStatus(self):
        enabled = (self.selectedList.GetSelectedItemCount() == 1)
        if enabled:
            itemIndex, = self.selectedList.GetSelectedItemIndexes()
            maxIndex = len(self.selectedList.rowHandles) - 1
        self.moveUpButton.Enable(enabled and itemIndex > 0)
        self.moveDownButton.Enable(enabled and itemIndex < maxIndex)

    def OnCreate(self):
        self.availableList = self._GetAvailableList()
        self.BindEvent(self.availableList, wx.EVT_LIST_ITEM_SELECTED,
                self.OnAvailableListItemSelected, passEvent = False)
        self.BindEvent(self.availableList, wx.EVT_LIST_ITEM_DESELECTED,
                self.OnAvailableListItemDeselected, passEvent = False)
        self.BindEvent(self.availableList, wx.EVT_LEFT_DCLICK,
                self.OnAvailableListItemDoubleClicked)
        self.selectedList = self._GetSelectedList()
        self.BindEvent(self.selectedList, wx.EVT_LIST_ITEM_SELECTED,
                self.OnSelectedListItemSelected, passEvent = False)
        self.BindEvent(self.selectedList, wx.EVT_LIST_ITEM_DESELECTED,
                self.OnSelectedListItemDeselected, passEvent = False)
        self.BindEvent(self.selectedList, wx.EVT_LEFT_DCLICK,
                self.OnSelectedListItemDoubleClicked)
        self.addToSelectedButton = self.AddButton(">>", enabled = False,
                method = self.OnAddToSelected, passEvent = False)
        self.removeFromSelectedButton = self.AddButton("<<", enabled = False,
                method = self.OnRemoveFromSelected, passEvent = False)
        if self.selectedListIsOrdered:
            self.moveUpButton = self.AddButton("Move Up", enabled = False,
                    method = self.OnMoveUp, passEvent = False)
            self.moveDownButton = self.AddButton("Move Down", enabled = False,
                    method = self.OnMoveDown, passEvent = False)

    def OnAddToSelected(self):
        self._MoveItems(self.availableList, self.selectedList,
                self.addToSelectedButton)

    def OnAvailableListItemDeselected(self):
        if self.availableList.GetSelectedItemCount() == 0:
            self.addToSelectedButton.Enable(False)

    def OnAvailableListItemDoubleClicked(self, event):
        self._OnListItemDoubleClicked(event, self.availableList,
                self.selectedList, self.addToSelectedButton)

    def OnAvailableListItemSelected(self):
        self.addToSelectedButton.Enable(True)

    def OnLayout(self):
        selectButtonSizer = wx.BoxSizer(wx.VERTICAL)
        selectButtonSizer.AddStretchSpacer()
        selectButtonSizer.Add(self.addToSelectedButton,
                flag = wx.BOTTOM | wx.ALIGN_CENTER_VERTICAL, border = 5)
        selectButtonSizer.Add(self.removeFromSelectedButton,
                flag = wx.ALIGN_CENTER_VERTICAL)
        selectButtonSizer.AddStretchSpacer()
        if self.selectedListIsOrdered:
            moveButtonSizer = wx.BoxSizer(wx.VERTICAL)
            moveButtonSizer.AddStretchSpacer()
            moveButtonSizer.Add(self.moveUpButton,
                    flag = wx.BOTTOM | wx.ALIGN_CENTER_VERTICAL, border = 5)
            moveButtonSizer.Add(self.moveDownButton,
                    flag = wx.ALIGN_CENTER_VERTICAL)
            moveButtonSizer.AddStretchSpacer()
        if self.layoutHorizontally:
            orientation = wx.HORIZONTAL
        else:
            orientation = wx.VERTICAL
        mainSizer = wx.BoxSizer(orientation)
        self._LayoutAvailableList(mainSizer)
        mainSizer.Add(selectButtonSizer, flag = wx.ALL | wx.EXPAND,
                border = 5)
        self._LayoutSelectedList(mainSizer)
        if self.selectedListIsOrdered:
            mainSizer.Add(moveButtonSizer,
                    flag = wx.LEFT | wx.EXPAND, border = 5)
        topSizer = wx.BoxSizer(wx.VERTICAL)
        topSizer.Add(mainSizer, flag = wx.ALL | wx.EXPAND, border = 5,
                proportion = 1)
        return topSizer

    def OnMoveDown(self):
        self.selectedList.MoveItem(1)

    def OnMoveUp(self):
        self.selectedList.MoveItem(-1)

    def OnRemoveFromSelected(self):
        self._MoveItems(self.selectedList, self.availableList,
                self.removeFromSelectedButton)
        self.availableList.SortItems()

    def OnSelectedListItemDeselected(self):
        numSelected = self.selectedList.GetSelectedItemCount()
        if self.selectedList.GetSelectedItemCount() == 0:
            self.removeFromSelectedButton.Enable(False)
        if self.selectedListIsOrdered:
            self._SetMoveButtonStatus()

    def OnSelectedListItemDoubleClicked(self, event):
        self._OnListItemDoubleClicked(event, self.selectedList,
                self.availableList, self.removeFromSelectedButton)
        self.availableList.SortItems()

    def OnSelectedListItemSelected(self):
        if self.selectedListIsOrdered:
            self._SetMoveButtonStatus()
        self.removeFromSelectedButton.Enable(True)

    def RestoreSettings(self):
        self.availableList.RestoreColumnWidths("AvailableColumnWidths")
        self.selectedList.RestoreColumnWidths("SelectedColumnWidths")

    def SaveSettings(self):
        self.availableList.SaveColumnWidths("AvailableColumnWidths")
        self.selectedList.SaveColumnWidths("SelectedColumnWidths")

