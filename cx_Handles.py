"""Defines class that manages handles."""

import cx_Exceptions
import _thread

class HandleManager(object):
    """Manages handles which are simple integers associated with objects; a
       hierarchal relationship between handles is also managed."""

    __handle = 0
    __handleLock = _thread.allocate_lock()

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
        if handle in self.__handleDescriptors:
            del self.__handleDescriptors[handle]
        method = getattr(obj, "OnRemoveFromHandleManager", None)
        if method is not None:
            method(handle)

    def Clear(self):
        self.__objectsByHandle = {}
        self.__handlesByObject = {}
        self.__handleDescriptors = {}

    def DescriptorForHandle(self, handle):
        return self.__handleDescriptors.get(handle)

    def DumpState(self):
        """Return the internal state of the manager, for debugging."""
        lines = []
        for handle, obj in self.__objectsByHandle.items():
            descriptor = self.__handleDescriptors.get(handle)
            if descriptor:
                lines.append("%i [%s]: %s" % (handle, descriptor, obj))
            else:
                lines.append("%i: %s" % (handle, obj))
        return "\n".join(lines)

    def HandleForObject(self, obj, handleDescriptor = None):
        """Return the handle for an object; if the object is not already
           managed, allocate a new handle and return it.

           An optional handleDescriptor is passed in, which is simply a
           piece of text that describes the handle.  This is done solely
           to allow for debugging."""
        handle = self.__handlesByObject.get(obj)
        if handle is None:
            handle = self.__GetHandle()
            self.__objectsByHandle[handle] = obj
            self.__handlesByObject[obj] = handle
            if handleDescriptor is not None:
                self.__handleDescriptors[handle] = handleDescriptor
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

