"""
Defines classes used for manipulating tree controls.
"""

import ceGUI
import cx_Exceptions
import datetime
import wx

__all__ = [ "Tree", "TreeItem" ]


class Tree(ceGUI.BaseControl, wx.TreeCtrl):
    rootItemLabel = ""

    def __init__(self, *args, **kwargs):
        wx.TreeCtrl.__init__(self, *args, **kwargs)
        parent = self.GetParent()
        parent.BindEvent(self, wx.EVT_TREE_ITEM_EXPANDING, self.OnExpandItem,
                createBusyCursor = True)
        self._Initialize()
        self._PopulateRootItems()

    def _PopulateBranch(self, parent, items):
        itemsToSort = [(i.GetSortValue(), i) for i in items]
        itemsToSort.sort()
        for sortValue, item in itemsToSort:
            self.AppendItem(parent, item)

    def _PopulateRootItems(self):
        rootItemId = self.AddRoot(self.rootItemLabel)
        self.idsByItem = {}
        self.idsByItem[None] = rootItemId
        self._PopulateBranch(None, self.GetRootItems())

    def AppendItem(self, parent, item):
        parentItemId = self.idsByItem[parent]
        text = item.GetTextValue()
        itemId = wx.TreeCtrl.AppendItem(self, parentItemId, text, item.image)
        self.idsByItem[item.data] = itemId
        self.SetPyData(itemId, item)
        if item.HasChildItems():
            self.SetItemHasChildren(itemId)

    def DeleteItem(self, item):
        itemId = self.idsByItem.pop(item)
        self.Delete(itemId)

    def ExpandItem(self, item):
        itemId = self.idsByItem[item]
        self.Expand(itemId)

    def GetChildItems(self, item = None):
        childItems = []
        itemId = self.idsByItem[item]
        childItemId, cookie = self.GetFirstChild(itemId)
        while childItemId.IsOk():
            childItem = self.GetPyData(childItemId)
            childItems.append(childItem.data)
            childItemId, cookie = self.GetNextChild(itemId, cookie)
        return childItems

    def GetItemParent(self, item):
        itemId = self.idsByItem[item]
        parentItemId = super(Tree, self).GetItemParent(itemId)
        parentItem = self.GetPyData(parentItemId)
        if parentItem is not None:
            return parentItem.data

    def GetItemParents(self, item):
        while True:
            parentItem = self.GetItemParent(item)
            if parentItem is None:
                break
            yield parentItem
            item = parentItem

    def GetRootItems(self):
        return []

    def GetSelectedItem(self):
        itemId = self.GetSelection()
        item = self.GetPyData(itemId)
        return item.data

    def HasItem(self, item):
        return item in self.idsByItem

    def InsertItem(self, parent, item):
        itemIndex = 0
        sortValue = item.GetSortValue()
        parentItemId = self.idsByItem[parent]
        childItemId, cookie = self.GetFirstChild(parentItemId)
        while childItemId.IsOk():
            childItem = self.GetPyData(childItemId)
            if childItem.GetSortValue() > sortValue:
                break
            childItemId, cookie = self.GetNextChild(parentItemId, cookie)
            itemIndex += 1
        text = item.GetTextValue()
        if itemIndex == 0:
            itemId = self.PrependItem(parentItemId, text, item.image)
        else:
            itemId = self.InsertItemBefore(parentItemId, itemIndex, text,
                    item.image)
        self.idsByItem[item.data] = itemId
        self.SetPyData(itemId, item)
        if item.HasChildItems():
            self.SetItemHasChildren(itemId)

    def OnExpandItem(self, event):
        itemId = event.GetItem()
        item = self.GetPyData(itemId)
        if not item.expanded:
            item.expanded = True
            childItems = item.GetChildItems(self)
            if childItems:
                self._PopulateBranch(item.data, childItems)
            else:
                self.SetItemHasChildren(itemId, False)

    def RefreshItem(self, item):
        itemId = self.idsByItem[item]
        treeItem = self.GetPyData(itemId)
        text = treeItem.GetTextValue()
        self.SetItemText(itemId, text)

    def SelectItem(self, item):
        itemId = self.idsByItem[item]
        super(Tree, self).SelectItem(itemId)


class TreeItem(object):
    textAttrName = sortAttrName = "description"

    def __init__(self, data, getChildItemsMethod = None, image = -1):
        self.data = data
        self.image = image
        self.expanded = False
        self.getChildItemsMethod = getChildItemsMethod

    def __repr__(self):
        return "<%s for %s>" % (self.__class__.__name__, self.data)

    def GetChildItems(self, tree):
        return self.getChildItemsMethod(self.data)

    def GetSortValue(self):
        value = getattr(self.data, self.sortAttrName)
        if isinstance(value, basestring):
            return value.upper()
        elif isinstance(value, (datetime.datetime, datetime.date)):
            return str(value)
        return value

    def GetTextValue(self):
        value = getattr(self.data, self.textAttrName)
        if value is None:
            return ""
        return value

    def HasChildItems(self):
        return self.getChildItemsMethod is not None

