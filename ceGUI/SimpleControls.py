"""
Defines simple controls with extensions to wx functionality.
"""

import ceGUI
import cx_Exceptions
import wx

__all__ = ["BaseControl", "Choice", "IntegerField", "Notebook", "TextField",
           "Tree", "TreeItem"]


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

    def _GetClass(self, name):
        parts = name.split(".")
        if len(parts) == 2:
            moduleName, attrName = parts
        else:
            moduleName = self.__class__.__module__
            attrName = name
        module = __import__(moduleName)
        return getattr(module, attrName)

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


class Choice(BaseControl, wx.Choice):

    def __init__(self, parent, choices):
        wx.Choice.__init__(self, parent)
        self.SetChoices(choices)
        self._Initialize()

    def __AddChoice(self, dataValue, choiceIndex):
        self.indexesByDataValue[dataValue] = choiceIndex
        self.dataValuesByIndex[choiceIndex] = dataValue

    def Append(self, dataValue, displayValue = None):
        if displayValue is None:
            displayValue = dataValue
        choiceIndex = super(Choice, self).Append(displayValue)
        self.__AddChoice(dataValue, choiceIndex)
        return choiceIndex

    def GetValue(self):
        choiceIndex = self.GetSelection()
        if choiceIndex != wx.NOT_FOUND:
            return self.dataValuesByIndex[choiceIndex]

    def Insert(self, insertIndex, dataValue, displayValue = None):
        if displayValue is None:
            displayValue = dataValue
        choiceIndex = super(Choice, self).Insert(displayValue, insertIndex)
        self.__AddChoice(dataValue, choiceIndex)
        return choiceIndex

    def SetChoices(self, choices):
        self.Clear()
        displayValues = []
        self.indexesByDataValue = {}
        self.dataValuesByIndex = {}
        for choiceIndex, choice in enumerate(choices):
            if isinstance(choice, (list, tuple)):
                if len(choice) == 1:
                    dataValue = displayValue = choice[0]
                else:
                    dataValue, displayValue = choice
            else:
                dataValue = displayValue = choice
            displayValues.append(displayValue)
            self.__AddChoice(dataValue, choiceIndex)
        self.AppendItems(displayValues)

    def SetValue(self, value):
        choiceIndex = self.indexesByDataValue.get(value, wx.NOT_FOUND)
        self.SetSelection(choiceIndex)


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


class TextField(BaseControl, wx.TextCtrl):
    copyAppAttributes = False

    def __init__(self, parent, style = 0):
        wx.TextCtrl.__init__(self, parent, style = style)
        self._Initialize()

    def GetValue(self):
        value = wx.TextCtrl.GetValue(self)
        if value:
            return value

    def SetValue(self, value):
        wx.TextCtrl.SetValue(self, value or "")


class IntegerField(TextField):

    def _Initialize(self):
        super(IntegerField, self)._Initialize()
        self.GetParent().BindEvent(self, wx.EVT_CHAR, self.OnChar,
                skipEvent = False)

    def GetValue(self):
        value = super(IntegerField, self).GetValue()
        if value is not None:
            return int(value)

    def OnChar(self, event):
        key = event.GetKeyCode()
        if key in (wx.WXK_BACK, wx.WXK_DELETE) or key > 127:
            event.Skip()
        if key >= ord('0') and key <= ord('9'):
            event.Skip()

    def SetValue(self, value):
        if value is not None:
            value = str(value)
        super(IntegerField, self).SetValue(value)


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

