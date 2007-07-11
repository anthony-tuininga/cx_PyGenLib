"""
Defines simple controls with extensions to wx functionality.
"""

import ceGUI
import cx_Exceptions
import wx

__all__ = ["BaseControl", "List", "Notebook", "Tree", "TreeItem"]


class BaseControl(object):
    copyAppAttributes = True
    baseSettingsName = None

    def _AddMenuItem(self, menu, label = "", helpString = "",
            kind = wx.ITEM_NORMAL, method = None, createBusyCursor = False,
            id = None, passEvent = True):
        if id is None:
            id = wx.NewId()
        item = wx.MenuItem(menu, id, label, helpString, kind)
        menu.AppendItem(item)
        if method is not None:
            self.BindEvent(item, wx.EVT_MENU, method, passEvent = passEvent,
                    createBusyCursor = createBusyCursor)
        return item

    def _GetSettingsName(self, name):
        baseSettingsName = self.baseSettingsName
        if baseSettingsName is None:
            baseSettingsName = self.__class__.__module__
        return "%s/%s" % (baseSettingsName, name)

    def _Initialize(self):
        if self.copyAppAttributes:
            app = wx.GetApp()
            for name in app.copyAttributes:
                value = getattr(app, name)
                setattr(self, name, value)
        self._OnCreate()

    def _OnCreate(self):
        self.OnCreate()
        self.RestoreSettings()

    def BindEvent(self, control, event, method, createBusyCursor = False,
            skipEvent = True, passEvent = True):
        ceGUI.EventHandler(self, control, event, method,
                createBusyCursor = createBusyCursor, skipEvent = skipEvent,
                passEvent = passEvent)

    def FlushSettings(self):
        self.settings.Flush()

    def OnCreate(self):
        pass

    def OnLayout(self):
        pass

    def ReadSetting(self, name, defaultValue = None, isComplex = False):
        settingsName = self._GetSettingsName(name)
        value = self.settings.Read(settingsName, "")
        if not value:
            return defaultValue
        if isComplex:
            try:
                value = eval(value)
            except:
                self.settings.DeleteEntry(fullName)
                value = defaultValue
        return value

    def RestoreSettings(self):
        pass

    def SaveSettings(self):
        pass

    def WriteSetting(self, name, value, isComplex = False):
        settingsName = self._GetSettingsName(name)
        if isComplex:
            value = repr(value)
        else:
            value = str(value)
        self.settings.Write(settingsName, value)


class List(BaseControl, wx.ListCtrl):
    transformerAcceptsItem = False
    singleSelection = False
    itemIsSequence = False
    attrNames = []

    def __init__(self, parent, style = 0):
        if self.singleSelection:
            style |= wx.LC_SINGLE_SEL
        wx.ListCtrl.__init__(self, parent,
                style = style | wx.LC_REPORT | wx.LC_VIRTUAL)
        parent.BindEvent(self, wx.EVT_LIST_COL_CLICK, self._OnColumnClick,
                createBusyCursor = True)
        parent.BindEvent(self, wx.EVT_SIZE, self._OnResize)
        parent.BindEvent(self, wx.EVT_LIST_COL_END_DRAG, self._OnResize)
        self.items = []
        self.transformers = {}
        self.sortByColumnIndexes = []
        if isinstance(self.attrNames, str):
            self.attrNames = self.attrNames.split()
        self._Initialize()
        self._Resize()

    def _AddColumn(self, heading = "", width = -1, transformer = None,
            format = wx.LIST_FORMAT_LEFT):
        columnIndex = self.GetColumnCount()
        if transformer is not None:
            self.transformers[columnIndex] = transformer
        self.InsertColumn(columnIndex, heading, format, width)

    def _GetSelectedItemIndexes(self):
        pos = -1
        indexes = []
        while True:
            pos = self.GetNextItem(pos, state = wx.LIST_STATE_SELECTED)
            if pos < 0:
                break
            indexes.append(pos)
        return indexes

    def _OnColumnClick(self, event):
        self.SortItems(event.GetColumn())

    def _OnResize(self, event):
        wx.CallAfter(self._Resize)
        event.Skip()

    def _Resize(self):
        """Resize the last column of the control to take up all remaining
           space; note that on Windows this cannot be done during the event
           that caused it as otherwise drawing artifacts remain; on Linux the
           client size of the list control includes the scroll bar but on
           Windows it does not."""
        if not self:
            return
        numColumns = self.GetColumnCount()
        if numColumns:
            width = self.GetClientSize().width
            if wx.Platform == "__WXGTK__":
                x = wx.SystemSettings.GetMetric(wx.SYS_VSCROLL_X)
                if self.GetItemCount() > self.GetCountPerPage():
                    width -= x
            for columnNum in range(numColumns - 1):
                width -= self.GetColumnWidth(columnNum)
            if width > 0:
                self.SetColumnWidth(numColumns - 1, width)
            self.Refresh()

    def AddColumn(self, heading, width = -1, transformer = None):
        self._AddColumn(heading, width, transformer, wx.LIST_FORMAT_LEFT)

    def AddColumnCentered(self, heading, width = -1, transformer = None):
        self._AddColumn(heading, width, transformer, wx.LIST_FORMAT_CENTER)

    def AddColumnRightJustified(self, heading, width = -1, transformer = None):
        """Add a column to the control in which the text is right justified;
           note that a dummy column is added and removed if the column being
           added is the first column because on Windows, the first column is
           assumed to be left justified, no matter what format is specified."""
        if self.GetColumnCount() == 0:
            self._AddColumn(heading, width, transformer, wx.LIST_FORMAT_RIGHT)
            self._AddColumn(heading, width, transformer, wx.LIST_FORMAT_RIGHT)
            self.DeleteColumn(0)
        else:
            self._AddColumn(heading, width, transformer, wx.LIST_FORMAT_RIGHT)

    def ClearAll(self):
        super(List, self).ClearAll()
        self.items = []
        self.transformers = {}
        self.sortByColumnIndexes = []

    def GetSelectedItem(self):
        items = self.GetSelectedItems()
        if len(items) != 1:
            raise WrongNumberOfItemsSelected()
        return items[0]

    def GetSelectedItems(self):
        return [self.items[i] for i in self._GetSelectedItemIndexes()]

    def OnGetItemText(self, itemIndex, columnIndex):
        item = self.items[itemIndex]
        if self.attrNames:
            attrName = self.attrNames[columnIndex]
            if attrName:
                value = getattr(item, attrName)
            else:
                value = None
        elif self.itemIsSequence:
            value = item[columnIndex]
        else:
            value = item
        transformer = self.transformers.get(columnIndex)
        if transformer is not None:
            if self.transformerAcceptsItem:
                transformArg = item
            else:
                transformArg = value
            value = transformer(transformArg)
        if value is None:
            value = ""
        return value

    def RestoreColumnWidths(self):
        widths = self.ReadSetting("ColumnWidths", isComplex = True)
        if widths is not None:
            for columnIndex, width in enumerate(widths):
                self.SetColumnWidth(columnIndex, width)

    def SaveColumnWidths(self):
        numColumns = self.GetColumnCount()
        if numColumns > 1:
            widths = [self.GetColumnWidth(i) for i in range(numColumns - 1)]
            self.WriteSetting("ColumnWidths", tuple(widths), isComplex = True)

    def SetItems(self, items, refresh = True, clearSelection = True):
        if clearSelection:
            self.DeleteAllItems()
        self.items = list(items)
        self.SetItemCount(len(self.items))
        if refresh:
            self.Refresh()

    def SetSelectedItems(self, items):
        itemDict = dict([(item, ix) for ix, item in enumerate(self.items)])
        for item in items:
            itemIndex = itemDict[item]
            self.SetItemState(itemIndex, wx.LIST_STATE_SELECTED,
                    wx.LIST_STATE_SELECTED)

    def SortItems(self, columnIndex = None, refresh = True):
        if columnIndex is not None:
            if columnIndex in self.sortByColumnIndexes:
                self.sortByColumnIndexes.remove(columnIndex)
            self.sortByColumnIndexes.insert(0, columnIndex)
        method = ceGUI.SortRep
        selectedItemIndexes = self._GetSelectedItemIndexes()
        if self.attrNames:
            attrNames = [self.attrNames[i] for i in self.sortByColumnIndexes]
            attrNames.extend([n for n in self.attrNames if n not in attrNames])
            itemsToSort = [[[method(getattr(i, n)) for n in attrNames], i, 0] \
                    for i in self.items]
        elif self.itemIsSequence:
            numColumns = self.GetColumnCount()
            indexes = self.sortByColumnIndexes
            if len(indexes) != numColumns:
                newIndexes = [i for i in range(numColumns) if i not in indexes]
                self.sortByColumnIndexes.extend(newIndexes)
            itemsToSort = [[[method(i[x]) for x in indexes], i, 0] \
                    for i in self.items]
        else:
            itemsToSort = [[i, i, 0] for i in self.items]
        for itemIndex in selectedItemIndexes:
            self.SetItemState(itemIndex, 0, wx.LIST_STATE_SELECTED)
            itemsToSort[itemIndex][2] = 1
        itemsToSort.sort()
        self.items = [i[1] for i in itemsToSort]
        indexesToSelect = [i for i, info in enumerate(itemsToSort) if info[2]]
        for itemIndex in indexesToSelect:
            self.SetItemState(itemIndex, wx.LIST_STATE_SELECTED,
                    wx.LIST_STATE_SELECTED)
        if refresh:
            self.Refresh()


class Notebook(BaseControl, wx.Notebook):

    def __init__(self, *args, **kwargs):
        wx.Notebook.__init__(self, *args, **kwargs)
        self._Initialize()

    def IterPages(self):
        for pageIndex in range(self.GetPageCount()):
            yield self.GetPage(pageIndex)

    def RestoreSettings(self):
        for page in self.IterPages():
            page.RestoreSettings()

    def SaveSettings(self):
        for page in self.IterPages():
            page.SaveSettings()


class Tree(BaseControl, wx.TreeCtrl):
    rootItemLabel = ""

    def __init__(self, *args, **kwargs):
        wx.TreeCtrl.__init__(self, *args, **kwargs)
        parent = self.GetParent()
        parent.BindEvent(self, wx.EVT_TREE_ITEM_EXPANDING, self.OnExpandItem,
                createBusyCursor = True)
        self._Initialize()
        self._PopulateRootItems()

    def _PopulateBranch(self, parentItemId, items):
        for item in items:
            text = getattr(item.data, item.textAttrName)
            itemId = self.AppendItem(parentItemId, text)
            self.idsByItem[item.data] = itemId
            self.SetPyData(itemId, item)
            if item.getChildItemsMethod is not None:
                self.SetItemHasChildren(itemId)

    def _PopulateRootItems(self):
        rootItemId = self.AddRoot(self.rootItemLabel)
        self.idsByItem = {}
        self.idsByItem[None] = rootItemId
        self._PopulateBranch(rootItemId, self.GetRootItems())

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
            self._PopulateBranch(itemId, childItems)

    def GetRootItems(self):
        return []


class TreeItem(object):
    textAttrName = "description"

    def __init__(self, data, getChildItemsMethod = None):
        self.data = data
        self.expanded = False
        self.getChildItemsMethod = getChildItemsMethod

    def __repr__(self):
        return "<%s for %s>" % (self.__class__.__name__, self.data)


class WrongNumberOfItemsSelected(cx_Exceptions.BaseException):
    message = "One and only one item should be selected."

