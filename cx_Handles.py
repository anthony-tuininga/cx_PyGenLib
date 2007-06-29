"""Defines class that manages handles."""

import cx_Exceptions
import thread

class HandleManager(object):
    """Manages handles which are simple integers associated with objects; a
       hierarchal relationship between handles is also managed."""

    __handle = 0
    __handleLock = thread.allocate_lock()

    def __GetHandle(cls):
        cls.__handleLock.acquire()
        try:
            cls.__handle += 1
            return cls.__handle
        finally:
            cls.__handleLock.release()

    __GetHandle = classmethod(__GetHandle)

    def __init__(self):
        self.Clear()

    def __RemoveObjectAndHandle(self, obj, handle):
        """Remove an object and its handle from the manager."""
        del self.__handlesByObject[obj]
        del self.__objectsByHandle[handle]
        method = getattr(obj, "OnRemoveFromHandleManager", None)
        if method is not None:
            method(handle)

    def Clear(self):
        self.__objectsByHandle = {}
        self.__handlesByObject = {}

    def HandleForObject(self, obj):
        """Return the handle for an object; if the object is not already
           managed, allocate a new handle and return it."""
        handle = self.__handlesByObject.get(obj)
        if handle is None:
            handle = self.__GetHandle()
            self.__objectsByHandle[handle] = obj
            self.__handlesByObject[obj] = handle
            method = getattr(obj, "OnAddToHandleManager", None)
            if method is not None:
                method(handle)
        return handle

    def ObjectForHandle(self, handle):
        """Return the object registered for the handle."""
        try:
            return self.__objectsByHandle[handle]
        except KeyError:
            raise cx_Exceptions.InvalidHandle(handle = handle)

    def RemoveHandle(self, handle):
        """Remove the object from the handle manager if it is present."""
        obj = self.__objectsByHandle.get(handle)
        if obj is not None:
            self.__RemoveObjectAndHandle(obj, handle)

    def RemoveObject(self, obj):
        """Remove the object from the handle manager if it is present."""
        handle = self.__handlesByObject.get(obj)
        if handle is not None:
            self.__RemoveObjectAndHandle(obj, handle)

