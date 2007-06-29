"""Defines constants and methods for controlling services on Windows."""

import win32con
import winerror
import win32service
import pywintypes
import time

# constants for ControlService [dwControl]
SERVICE_CONTROL_CONTINUE = win32service.SERVICE_CONTROL_CONTINUE
SERVICE_CONTROL_INTERROGATE = win32service.SERVICE_CONTROL_INTERROGATE
SERVICE_CONTROL_PAUSE = win32service.SERVICE_CONTROL_PAUSE
SERVICE_CONTROL_STOP = win32service.SERVICE_CONTROL_STOP
# the following is defined, but not supported.
SERVICE_CONTROL_SHUTDOWN = win32service.SERVICE_CONTROL_SHUTDOWN
# the following are supported by Win2000 and up, but not in win32service :-(
SERVICE_CONTROL_NETBINDADD = 7           # 0x000000007
SERVICE_CONTROL_NETBINDDISABLE = 10      # 0x00000000A
SERVICE_CONTROL_NETBINDENABLE = 9        # 0x000000009
SERVICE_CONTROL_NETBINDREMOVE = 8        # 0x000000008
SERVICE_CONTROL_PARAMCHANGE = 6          # 0x000000006

# constants for ChangeServiceConfig [dwStartType]
SERVICE_AUTO_START = win32service.SERVICE_AUTO_START
SERVICE_BOOT_START = win32service.SERVICE_BOOT_START
SERVICE_DEMAND_START = win32service.SERVICE_DEMAND_START
SERVICE_DISABLED = win32service.SERVICE_DISABLED
SERVICE_SYSTEM_START = win32service.SERVICE_SYSTEM_START
SERVICE_NO_CHANGE = win32service.SERVICE_NO_CHANGE

# constants for ChangeServiceConfig [dwErrorControl]
SERVICE_ERROR_IGNORE = win32service.SERVICE_ERROR_IGNORE
SERVICE_ERROR_NORMAL = win32service.SERVICE_ERROR_NORMAL
SERVICE_ERROR_SEVERE = win32service.SERVICE_ERROR_SEVERE
SERVICE_ERROR_CRITICAL = win32service.SERVICE_ERROR_CRITICAL

# constants for CreateService/OpenService [dwDesiredAccess]
STANDARD_RIGHTS_REQUIRED = win32con.STANDARD_RIGHTS_REQUIRED
ACCESS_SYSTEM_SECURITY = win32con.ACCESS_SYSTEM_SECURITY
DELETE = win32con.DELETE
READ_CONTROL = win32con.READ_CONTROL
WRITE_DAC = win32con.WRITE_DAC
WRITE_OWNER = win32con.WRITE_OWNER
SERVICE_ALL_ACCESS = win32service.SERVICE_ALL_ACCESS
SERVICE_CHANGE_CONFIG = win32service.SERVICE_CHANGE_CONFIG
SERVICE_ENUMERATE_DEPENDENTS = win32service.SERVICE_ENUMERATE_DEPENDENTS
SERVICE_INTERROGATE = win32service.SERVICE_INTERROGATE
SERVICE_PAUSE_CONTINUE = win32service.SERVICE_PAUSE_CONTINUE
SERVICE_QUERY_CONFIG = win32service.SERVICE_QUERY_CONFIG
SERVICE_QUERY_STATUS = win32service.SERVICE_QUERY_STATUS
SERVICE_START = win32service.SERVICE_START
SERVICE_STOP = win32service.SERVICE_STOP
SERVICE_USER_DEFINED_CONTROL = win32service.SERVICE_USER_DEFINED_CONTROL
GENERIC_READ = win32con.GENERIC_READ
GENERIC_WRITE = win32con.GENERIC_WRITE
GENERIC_EXECUTE = win32con.GENERIC_EXECUTE

# constants for EnumDependentServices [dwServiceState]
SERVICE_ACTIVE = win32service.SERVICE_ACTIVE
SERVICE_INACTIVE = win32service.SERVICE_INACTIVE
SERVICE_STATE_ALL = win32service.SERVICE_STATE_ALL

# constants for EnumServicesStatus [dwServiceType]
SERVICE_DRIVER = win32service.SERVICE_DRIVER
SERVICE_WIN32 = win32service.SERVICE_WIN32

# constants for OpenSCMananger [dwDesiredAccess]
SC_MANAGER_ALL_ACCESS = win32service.SC_MANAGER_ALL_ACCESS
SC_MANAGER_CREATE_SERVICE = win32service.SC_MANAGER_CREATE_SERVICE
SC_MANAGER_CONNECT = win32service.SC_MANAGER_CONNECT
SC_MANAGER_ENUMERATE_SERVICE = win32service.SC_MANAGER_ENUMERATE_SERVICE
SC_MANAGER_LOCK = win32service.SC_MANAGER_LOCK
SC_MANAGER_QUERY_LOCK_STATUS = win32service.SC_MANAGER_QUERY_LOCK_STATUS
SC_MANAGER_MODIFY_BOOT_CONFIG = win32service.SC_MANAGER_MODIFY_BOOT_CONFIG

# constants for error codes
ERROR_ACCESS_DENIED = winerror.ERROR_ACCESS_DENIED
ERROR_CIRCULAR_DEPENDENCY = winerror.ERROR_CIRCULAR_DEPENDENCY
ERROR_DATABASE_DOES_NOT_EXIST = winerror.ERROR_DATABASE_DOES_NOT_EXIST
ERROR_DEPENDENT_SERVICES_RUNNING = winerror.ERROR_DEPENDENT_SERVICES_RUNNING
ERROR_DUPLICATE_SERVICE_NAME = winerror.ERROR_DUPLICATE_SERVICE_NAME
ERROR_INSUFFICIENT_BUFFER = winerror.ERROR_INSUFFICIENT_BUFFER
ERROR_INVALID_DATA = winerror.ERROR_INVALID_DATA
ERROR_INVALID_HANDLE = winerror.ERROR_INVALID_HANDLE
ERROR_INVALID_NAME = winerror.ERROR_INVALID_NAME
ERROR_INVALID_PARAMETER = winerror.ERROR_INVALID_PARAMETER
ERROR_INVALID_SERVICE_ACCOUNT = winerror.ERROR_INVALID_SERVICE_ACCOUNT
ERROR_INVALID_SERVICE_CONTROL = winerror.ERROR_INVALID_SERVICE_CONTROL
ERROR_INVALID_SERVICE_LOCK = winerror.ERROR_INVALID_SERVICE_LOCK
ERROR_MORE_DATA = winerror.ERROR_MORE_DATA
ERROR_PATH_NOT_FOUND = winerror.ERROR_PATH_NOT_FOUND
ERROR_SERVICE_ALREADY_RUNNING = winerror.ERROR_SERVICE_ALREADY_RUNNING
ERROR_SERVICE_CANNOT_ACCEPT_CTRL = winerror.ERROR_SERVICE_CANNOT_ACCEPT_CTRL
ERROR_SERVICE_DATABASE_LOCKED = winerror.ERROR_SERVICE_DATABASE_LOCKED
ERROR_SERVICE_DEPENDENCY_DELETED = winerror.ERROR_SERVICE_DEPENDENCY_DELETED
ERROR_SERVICE_DEPENDENCY_FAIL = winerror.ERROR_SERVICE_DEPENDENCY_FAIL
ERROR_SERVICE_DISABLED = winerror.ERROR_SERVICE_DISABLED
ERROR_SERVICE_DOES_NOT_EXIST = winerror.ERROR_SERVICE_DOES_NOT_EXIST
ERROR_SERVICE_EXISTS = winerror.ERROR_SERVICE_EXISTS
ERROR_SERVICE_LOGON_FAILED = winerror.ERROR_SERVICE_LOGON_FAILED
ERROR_SERVICE_MARKED_FOR_DELETE = winerror.ERROR_SERVICE_MARKED_FOR_DELETE
ERROR_SERVICE_NO_THREAD = winerror.ERROR_SERVICE_NO_THREAD
ERROR_SERVICE_NOT_ACTIVE = winerror.ERROR_SERVICE_NOT_ACTIVE
ERROR_SERVICE_REQUEST_TIMEOUT = winerror.ERROR_SERVICE_REQUEST_TIMEOUT
ERROR_SERVICE_SPECIFIC_ERROR = win32service.SERVICE_SPECIFIC_ERROR
ERROR_SHUTDOWN_IN_PROGRESS = winerror.ERROR_SHUTDOWN_IN_PROGRESS

# service type constants (service_status[0]) [dwServiceType]
SERVICE_FILE_SYSTEM_DRIVER = win32service.SERVICE_FILE_SYSTEM_DRIVER
SERVICE_KERNEL_DRIVER = win32service.SERVICE_KERNEL_DRIVER
SERVICE_WIN32_OWN_PROCESS = win32service.SERVICE_WIN32_OWN_PROCESS
SERVICE_WIN32_SHARE_PROCESS = win32service.SERVICE_WIN32_SHARE_PROCESS
SERVICE_INTERACTIVE_PROCESS = win32service.SERVICE_INTERACTIVE_PROCESS

# service state constants (service_status[1]) [dwStartType]
SERVICE_CONTINUE_PENDING = win32service.SERVICE_CONTINUE_PENDING
SERVICE_PAUSE_PENDING = win32service.SERVICE_PAUSE_PENDING
SERVICE_PAUSED = win32service.SERVICE_PAUSED
SERVICE_RUNNING = win32service.SERVICE_RUNNING
SERVICE_START_PENDING = win32service.SERVICE_START_PENDING
SERVICE_STOP_PENDING = win32service.SERVICE_STOP_PENDING
SERVICE_STOPPED = win32service.SERVICE_STOPPED

# service controls accepted (service_status[2]) [dwControl]
SERVICE_ACCEPT_PAUSE_CONTINUE = win32service.SERVICE_ACCEPT_PAUSE_CONTINUE
SERVICE_ACCEPT_INTERROGATE = win32service.SERVICE_INTERROGATE
SERVICE_ACCEPT_SHUTDOWN = win32service.SERVICE_ACCEPT_SHUTDOWN
SERVICE_ACCEPT_STOP = win32service.SERVICE_ACCEPT_STOP
# the following are supported by Win2000 and up, but not in win32service :-(
SERVICE_ACCEPT_NETBINDCHANGE =  16  #0x00000010
SERVICE_ACCEPT_PARAMCHANGE = 8      #0x00000008


class ServiceManager:
    """Wrapper class for handling services on Windows."""

    def __init__(self):
        self.__handle = win32service.OpenSCManager(None, None, GENERIC_READ)

    def __GetState(self, handle):
        """Return the state of the service given its handle."""
        status = win32service.QueryServiceStatus(handle)
        return status[1]

    def Exists(self, serviceName):
        """Return True if the service exists."""
        try:
            handle = win32service.OpenService(self.__handle, serviceName,
                    SC_MANAGER_ALL_ACCESS)
            win32service.CloseServiceHandle(handle)
            return True
        except pywintypes.error, e:
            if e[0] == ERROR_SERVICE_DOES_NOT_EXIST:
                return False
            raise

    def Start(self, serviceName):
        """Start the service."""
        print "Starting service", serviceName
        handle = win32service.OpenService(self.__handle, serviceName,
              SC_MANAGER_ALL_ACCESS)
        win32service.StartService(handle, None)
        while True:
            state = self.__GetState(handle)
            if state != SERVICE_START_PENDING:
                break
            print "    waiting for service to start...."
            time.sleep(2)
        win32service.CloseServiceHandle(handle)

    def State(self, serviceName):
        """Return the state of the service."""
        handle = win32service.OpenService(self.__handle, serviceName,
                SC_MANAGER_ALL_ACCESS)
        state = self.__GetState(handle)
        win32service.CloseServiceHandle(handle)
        return state

    def Stop(self, serviceName):
        """Stop the service."""
        print "Stopping service", serviceName
        handle = win32service.OpenService(self.__handle, serviceName,
                SC_MANAGER_ALL_ACCESS)
        win32service.ControlService(handle, SERVICE_CONTROL_STOP)
        while True:
            state = self.__GetState(handle)
            if state != SERVICE_STOP_PENDING:
                break
            print "    waiting for service to stop...."
            time.sleep(2)
        win32service.CloseServiceHandle(handle)

