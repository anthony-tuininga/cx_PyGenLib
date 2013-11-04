"""Defines a framework for managing services."""

import cx_Threads

class Server(object):
    """Framework for managing services."""

    def __init__(self):
        self.event = cx_Threads.Event()
        self.stopEvent = cx_Threads.Event()
        self.stopRequested = False

    def Initialize(self):
        """Initialize the service in preparation for running. Override this
           method in subclasses as needed."""
        pass

    def Run(self):
        """Run the service. This method should be overridden in subclasses."""
        while not self.stopRequested:
            self.event.Wait()
        self.stopEvent.Set()

    def Stop(self):
        """Stop the service. This method can be overridden in subclasses."""
        self.stopRequested = True
        self.event.Set()
        self.stopEvent.Wait()

