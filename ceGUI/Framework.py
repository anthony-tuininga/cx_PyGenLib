"""
Defines methods used for handling events and other framework items including
such things as exception handling and managing busy cursors.
"""

import cx_Exceptions
import cx_Logging
import cx_Threads
import wx
import sys

__all__ = [ "BusyCursorContext", "EventHandler", "EVT_THREAD_TERMINATED",
            "GetModuleItem", "OpenWindow", "Thread", "TransactionContext" ]

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


def GetModuleItem(moduleName, attrName = None):
    """Return the item from the module. Note that the __import__() method has a
       quirk in that if the last parameter to the method is empty it only loads
       the top level package instead of the submodule."""
    if attrName is None:
        pos = moduleName.rfind(".")
        attrName = moduleName[pos + 1:]
        moduleName = moduleName[:pos]
    module = __import__(moduleName, globals(), locals(), [""])
    return getattr(module, attrName)


def OpenWindow(name, parent = None, forceNewInstance = False,
        instanceName = None):
    cls = GetModuleItem(name)
    if parent is not None and not forceNewInstance:
        for child in parent.GetChildren():
            if isinstance(child, cls) and child.instanceName == instanceName:
                child.SetFocus()
                return child
    window = cls(parent, instanceName = instanceName)
    return window


class TransactionContext(BusyCursorContext):
    
    def __init__(self, connection, parent = None, raiseException = False):
        super(TransactionContext, self).__init__(parent, raiseException)
        self.connection = connection

    def __exit__(self, excType, excValue, excTraceback):
        if excValue is None:
            cx_Logging.Debug("transaction succeeded, committing")
            self.connection.commit()
        else:
            cx_Logging.Debug("transaction failed, rolling back")
            self.connection.rollback()
            return super(TransactionContext, self).__exit__(excType, excValue,
                    excTraceback)


class Thread(cx_Threads.Thread):

    def __init__(self, window, method, *args, **kwargs):
        super(Thread, self).__init__(method, *args, **kwargs)
        self.window = window

    def OnThreadEnd(self):
        super(Thread, self).OnThreadEnd()
        wx.PostEvent(self.window, ThreadTerminatedEvent(self))

