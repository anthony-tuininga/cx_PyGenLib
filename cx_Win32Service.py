"""Defines constants and methods for controlling services on Windows."""

import cx_Logging
import winerror
import win32con
import win32service
import pywintypes
import time

class ServiceManager(object):

    def __init__(self):
        self.handle = win32service.OpenSCManager(None, None,
                win32con.GENERIC_READ)

    def Exists(self, serviceName):
        service = self.GetService(serviceName, ignoreError = True)
        return service is not None

    def GetService(self, serviceName, ignoreError = False):
        try:
            return Service(self, serviceName)
        except pywintypes.error as e:
            if ignoreError \
                    and e.args[0] == winerror.ERROR_SERVICE_DOES_NOT_EXIST:
                return None
            raise

    def GetServiceNames(self, startsWith = ""):
        startsWith = startsWith.lower()
        services = win32service.EnumServicesStatus(self.handle)
        return [str(n) for n, d, i in services \
                if n.lower().startswith(startsWith)]

    def Start(self, serviceName):
        service = self.GetService(serviceName)
        service.Start()

    def State(self, serviceName):
        service = self.GetService(serviceName)
        return service.state

    def Stop(self, serviceName):
        service = self.GetService(serviceName)
        service.Stop()


class ConfigDescriptor(object):


    def __init__(self, attrName):
        self.attrName = attrName

    def __get__(self, service, serviceType):
        info = win32service.QueryServiceConfig(service.handle)
        serviceType, startType, errorControl, binaryPathName, loadOrderGroup, \
                tagId, dependencies, name, displayName = info
        service.binaryPathName = str(binaryPathName)
        service.disabled = (startType == win32service.SERVICE_DISABLED)
        service.automatic = (startType == win32service.SERVICE_AUTO_START)
        service.manual = (startType == win32service.SERVICE_DEMAND_START)
        return getattr(service, self.attrName)


class InStateDescriptor(object):

    def __init__(self, desiredState):
        self.desiredState = desiredState

    def __get__(self, service, serviceType):
        return service.state == self.desiredState


class StateDescriptor(object):

    def __get__(self, service, serviceType):
        statusInfo = win32service.QueryServiceStatus(service.handle)
        return statusInfo[1]


class Service(object):
    state = StateDescriptor()
    automatic = ConfigDescriptor("automatic")
    manual = ConfigDescriptor("manual")
    disabled = ConfigDescriptor("disabled")
    binaryPathName = ConfigDescriptor("binaryPathName")
    started = InStateDescriptor(win32service.SERVICE_RUNNING)
    stopped = InStateDescriptor(win32service.SERVICE_STOPPED)
    handle = None

    def __init__(self, manager, name):
        cx_Logging.Debug("opening service %s", name)
        self.name = name
        self.handle = win32service.OpenService(manager.handle, name,
                win32service.SC_MANAGER_ALL_ACCESS)

    def __del__(self):
        if self.handle is not None:
            cx_Logging.Debug("closing service %s", self.name)
            win32service.CloseServiceHandle(self.handle)

    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, self.name)

    def Start(self):
        if self.started:
            cx_Logging.Info("Service %s already started.", self.name)
        else:
            cx_Logging.Info("Starting service %s", self.name)
            win32service.StartService(self.handle, None)
            while True:
                if self.state != win32service.SERVICE_START_PENDING:
                    break
                cx_Logging.Info("    waiting for service to start....")
                time.sleep(2)

    def Stop(self):
        if self.stopped:
            cx_Logging.Info("Service %s already stopped.", self.name)
        else:
            cx_Logging.Info("Stopping service %s", self.name)
            win32service.ControlService(self.handle,
                    win32service.SERVICE_CONTROL_STOP)
            while True:
                if self.state != win32service.SERVICE_STOP_PENDING:
                    break
                cx_Logging.Info("    waiting for service to stop....")
                time.sleep(2)

