"""
Defines methods used for handling events and other framework items including
such things as exception handling and managing busy cursors.
"""

import cx_Exceptions
import cx_Logging
import wx
import sys

__all__ = ["BusyCursorContext", "EventHandler", "OpenWindow",
           "TransactionContext"]


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
            createBusyCursor = False, skipEvent = True):
        self.parent = parent
        self.method = method
        self.createBusyCursor = createBusyCursor
        self.skipEvent = skipEvent
        if isinstance(control, wx.Window):
            connectControl = control
        else:
            connectControl = parent
        connectControl.Connect(control.GetId(), -1, event.typeId, self)

    def __call__(self, event):
        try:
            if self.createBusyCursor:
                busyCursor = wx.BusyCursor()
            self.method(event)
            if self.skipEvent:
                event.Skip()
        except:
            app = wx.GetApp()
            exc = cx_Exceptions.GetExceptionInfo(*sys.exc_info())
            app.OnException(exc, self.parent)


def OpenWindow(_name, *args, **kwargs):
    moduleName, attrName = _name.split(".")
    module = __import__(moduleName)
    cls = getattr(module, attrName)
    return cls(*args, **kwargs)


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

