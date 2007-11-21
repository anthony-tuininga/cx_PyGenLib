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
        if item.getChildItemsMethod is not None:
            self.SetItemHasChildren(itemId)

    def DeleteItem(self, item):
        itemId = self.idsByItem[item]
        self.Delete(itemId)

    def GetItemParents(self, item):
        while True:
            itemId = self.idsByItem[item]
            parentItemId = self.GetItemParent(itemId)
            parentItem = self.GetPyData(parentItemId)
            if parentItem is None:
                break
            yield parentItem.data
            item = parentItem.data

    def GetSelectedItem(self):
        itemId = self.GetSelection()
        item = self.GetPyData(itemId)
        return item.data

    def OnExpandItem(self, event):
        itemId = event.GetItem()
        item = self.GetPyData(itemId)
        if not item.expanded:
            item.expanded = True
            childItems = item.getChildItemsMethod(item.data)
            self._PopulateBranch(item.data, childItems)

    def GetRootItems(self):
        return []


class TreeItem(object):
    textAttrName = sortAttrName = "description"

    def __init__(self, data, getChildItemsMethod = None, image = -1):
        self.data = data
        self.image = image
        self.expanded = False
        self.getChildItemsMethod = getChildItemsMethod

    def __repr__(self):
        return "<%s for %s>" % (self.__class__.__name__, self.data)

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

