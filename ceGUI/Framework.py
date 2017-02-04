"""
Defines methods used for handling events and other framework items including
such things as exception handling and managing busy cursors.
"""

import ceDatabase
import cx_Exceptions
import cx_Logging
import cx_Threads
import wx
import sys

import wx.lib.pubsub.setupkwargs

from wx.lib.pubsub import pub

__all__ = [ "AppExit", "AppTopWindow", "BusyCursorContext", "DataSet",
            "DataSetRow", "EventHandler", "EVT_THREAD_TERMINATED",
            "FilteredDataSet", "FrozenContext", "GetApp", "GetModuleItem",
            "OpenWindow", "RequiredFieldHasNoValue", "SendMessage",
            "Subscribe", "Thread", "TransactionContext", "UnsubscribeAll" ]

EVT_THREAD_TERMINATED = wx.NewEventType()

class ThreadTerminatedEvent(wx.PyEvent):

    def __init__(self, thread):
        wx.PyEvent.__init__(self)
        self.SetEventType(EVT_THREAD_TERMINATED)
        self.thread = thread


class BusyCursorContext(object):

    def __init__(self, parent = None, raiseException = False):
        self.parent = parent
        self.raiseException = raiseException

    def __enter__(self):
        self.busyCursor = wx.BusyCursor()

    def __exit__(self, excType, excValue, excTraceback):
        if self.raiseException and excValue is not None:
            app = wx.GetApp()
            exc = cx_Exceptions.GetExceptionInfo(excType, excValue,
                    excTraceback)
            app.OnException(exc, self.parent)
            return True


class DataSet(ceDatabase.DataSet):
    updateSubCacheAttrName = None
    selectCacheAttrName = None

    @property
    def cache(self):
        app = wx.GetApp()
        return app.cache

    @property
    def config(self):
        app = wx.GetApp()
        return app.config

    def _GetRows(self, *args):
        if self.selectCacheAttrName is not None:
            method = getattr(self.cache, self.selectCacheAttrName)
            return method(*args)
        elif self.rowClass.cached:
            if not args:
                return self.config.GetCachedRows(self.rowClass)
            pkValue, = args
            row = self.config.GetCachedRowByPK(self.rowClass, pkValue)
            if row is not None:
                return [row]
        return super(DataSet, self)._GetRows(*args)

    def Update(self):
        if self.updateSubCacheAttrName is not None or self.rowClass.cached:
            rowsToUpdate = [self.rows[h] for h in self.insertedRows] + \
                    [self.rows[h] for h in self.updatedRows]
            rowsToDelete = list(self.deletedRows.values())
        super(DataSet, self).Update()
        if self.updateSubCacheAttrName is not None:
            cache = self.cache
            subCache = getattr(cache, self.updateSubCacheAttrName)
            for row in rowsToDelete:
                subCache.RemoveRow(cache, row)
            for row in rowsToUpdate:
                subCache.UpdateRow(cache, row, self.contextItem)
        elif self.rowClass.cached:
            config = self.config
            for row in rowsToDelete:
                config.RemoveCachedRow(self.rowClass, row)
            for row in rowsToUpdate:
                config.UpdateCachedRow(self.rowClass, row, self.contextItem)


class FilteredDataSet(ceDatabase.FilteredDataSet, DataSet):
    pass


class DataSetRow(ceDatabase.Row):
    pass


class EventHandler(object):

    def __init__(self, parent, control, event, method,
            createBusyCursor = False, skipEvent = True, passEvent = True):
        self.parent = parent
        self.method = method
        self.createBusyCursor = createBusyCursor
        self.skipEvent = skipEvent
        self.passEvent = passEvent
        if isinstance(control, wx.Window):
            connectControl = control
        else:
            connectControl = parent
        connectControl.Connect(control.GetId(), -1, event.typeId, self)

    def __call__(self, event):
        try:
            if self.createBusyCursor:
                busyCursor = wx.BusyCursor()
            if self.passEvent:
                self.method(event)
            else:
                self.method()
            if self.skipEvent:
                event.Skip()
        except:
            app = wx.GetApp()
            exc = cx_Exceptions.GetExceptionInfo(*sys.exc_info())
            app.OnException(exc, self.parent)


class FrozenContext(object):

    def __init__(self, window):
        self.window = window

    def __enter__(self):
        self.window.Freeze()

    def __exit__(self, excType, excValue, excTraceback):
        self.window.Thaw()


class AppExit(SystemExit):
    """Terminate the application and display an error dialog when frozen."""
    caption = "Error"

    def __init__(self, **kwargs):
        SystemExit.__init__(self, self.message % kwargs)


def AppTopWindow():
    """Return the application top window."""
    app = wx.GetApp()
    return app.topWindow


def GetApp():
    """Return the application object. Created simply for convenience of not
       having to import the wx module for this simple task."""
    return wx.GetApp()


def GetModuleItem(moduleName, attrName = None, associatedObj = None):
    """Return the item from the module. Note that the __import__() method has a
       quirk in that if the last parameter to the method is empty it only loads
       the top level package instead of the submodule."""
    if attrName is None:
        pos = moduleName.rfind(".")
        if pos < 0:
            attrName = moduleName
            moduleName = type(associatedObj).__module__
        else:
            attrName = moduleName[pos + 1:]
            moduleName = moduleName[:pos]
    module = __import__(moduleName, globals(), locals(), [""])
    return getattr(module, attrName)


def OpenWindow(name, parent = None, forceNewInstance = False,
        instanceName = None, **kwargs):
    with BusyCursorContext(parent):
        cls = GetModuleItem(name)
        if parent is not None and not forceNewInstance:
            for child in parent.GetChildren():
                if isinstance(child, cls) \
                        and child.instanceName == instanceName:
                    if not child.createdSuccessfully:
                        child.Destroy()
                        continue
                    child.SetFocus()
                    return child
        window = cls(parent, instanceName = instanceName, **kwargs)
        return window


class RequiredFieldHasNoValue(cx_Exceptions.BaseException):
    message = "Required field has no value."


def SendMessage(topic, **args):
    pub.sendMessage(topic, **args)


def Subscribe(listener, topic):
    pub.subscribe(listener, topic)


def UnsubscribeAll(topics = None):
    pub.unsubAll(topics)


class TransactionContext(BusyCursorContext):
    
    def __init__(self, dataSource, parent = None, raiseException = False):
        super(TransactionContext, self).__init__(parent, raiseException)
        self.dataSource = dataSource

    def __exit__(self, excType, excValue, excTraceback):
        if excValue is None:
            cx_Logging.Debug("transaction succeeded, committing")
            self.dataSource.commit()
        else:
            cx_Logging.Debug("transaction failed, rolling back")
            self.dataSource.rollback()
            return super(TransactionContext, self).__exit__(excType, excValue,
                    excTraceback)


class Thread(cx_Threads.Thread):

    def __init__(self, window, method, *args, **kwargs):
        super(Thread, self).__init__(method, *args, **kwargs)
        self.window = window

    def OnThreadEnd(self):
        super(Thread, self).OnThreadEnd()
        wx.PostEvent(self.window, ThreadTerminatedEvent(self))

