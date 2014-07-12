"""Defines methods for managing threads and queues."""

import cx_Exceptions
import cx_Logging
import threading

class Thread(threading.Thread):
    """Base class for threads which extends the threading module to include
       logging as well as tracebacks and notifications of thread
       termination."""

    def __init__(self, function, *args, **keywordArgs):
        super(Thread, self).__init__(target = function,
                args = args, kwargs = keywordArgs)
        self.errorObj = None
        self.event = None

    def OnThreadEnd(self):
        """Called when the thread is ended. Override in child classes."""
        cx_Logging.Info("thread %r ending", self.name)

    def OnThreadStart(self):
        """Called when the thread is started. Override in child classes."""
        cx_Logging.Info("thread %r starting", self.name)

    def run(self):
        """Execute the function associated with the thread."""
        cx_Logging.SetExceptionInfo(cx_Exceptions.BaseException,
                cx_Exceptions.GetExceptionInfo)
        try:
            self.OnThreadStart()
            try:
                super(Thread, self).run()
            except:
                self.errorObj = cx_Logging.LogException()
                cx_Logging.Error("Thread %r terminating", self.name)
        finally:
            self.OnThreadEnd()
            if self.event:
                self.event.set()


class Queue(object):
    """Light weight implementation of stacks and queues."""

    def __init__(self):
        self.lock = threading.Lock()
        self.queueEvent = threading.Event()
        self.items = []

    def Clear(self):
        """Clear the queue of all items."""
        self.lock.acquire()
        self.items = []
        self.lock.release()

    def QueueItem(self, item):
        """Add an item to end of the list of items (for queues)."""
        self.lock.acquire()
        self.items.append(item)
        self.lock.release()
        self.queueEvent.set()

    def PopItem(self, returnNoneIfEmpty=False):
        """Get the next item from the beginning of the list of items,
           optionally returning None if nothing is found."""
        self.lock.acquire()
        while not self.items:
            self.lock.release()
            if returnNoneIfEmpty:
                return None
            self.queueEvent.wait()
            self.queueEvent.clear()
            self.lock.acquire()
        item = self.items.pop(0)
        self.lock.release()
        return item

    def PushItem(self, item):
        """Add an item to the beginning of the list of items (for stacks)."""
        self.lock.acquire()
        self.items.insert(0, item)
        self.lock.release()
        self.queueEvent.set()


class ResourcePool(object):
    """Implements a pool of resources."""

    def __init__(self, maxResources, newResourceFunc):
        self.lock = threading.Lock()
        self.poolEvent = threading.Event()
        self.freeResources = []
        self.busyResources = []
        self.maxResources = maxResources
        self.newResourceFunc = newResourceFunc

    def Destroy(self):
        """Destroy the resource pool, this blocks until all resources are
           returned to the pool for destruction."""
        self.lock.acquire()
        self.freeResources = []
        self.maxResources = 0
        self.lock.release()
        while self.busyResources:
            self.poolEvent.wait()

    def Get(self):
        """Gets a resource form the pool, creating new resources as necessary.
           The calling thread will block until a resource is available, if
           necessary."""
        resource = None
        self.lock.acquire()
        while resource is None:
            try:
                if self.freeResources:
                    resource = self.freeResources.pop()
                elif len(self.busyResources) < self.maxResources:
                    resource = self.newResourceFunc()
                elif not self.maxResources:
                    raise Exception("No resources not available.")
                else:
                    self.lock.release()
                    self.poolEvent.wait()
                    self.lock.acquire()
            except:
                if self.lock.locked():
                    self.lock.release()
                raise
        self.busyResources.append(resource)
        self.lock.release()
        return resource

    def Put(self, resource, addToFreeList = True):
        """Put a resource back into the pool."""
        self.lock.acquire()
        try:
            index = self.busyResources.index(resource)
            del self.busyResources[index]
            if self.maxResources and addToFreeList:
                self.freeResources.append(resource)
        finally:
            self.lock.release()
        self.poolEvent.set()

