"""
Handles communication of arbitrary objects across Win32 named pipes.
"""

import pickle
import cx_Exceptions
import cx_Logging
import pywintypes
import win32file
import win32pipe

class NamedPipe(object):

    def __init__(self, name, serverName = None, maxSize = 65536, timeout = 30,
            maxLengthDigits = 6, asServer = True,
            maxInstances = win32pipe.PIPE_UNLIMITED_INSTANCES):
        self.name = name
        self.serverName = serverName
        self.maxSize = maxSize
        self.timeout = timeout
        self.maxLengthDigits = maxLengthDigits
        self.asServer = asServer
        self.maxInstances = maxInstances
        self.handle = None

    def __enter__(self):
        if self.handle is None:
            self.Open()
        return self

    def __exit__(self, excType, excValue, excTraceback):
        if self.handle is not None:
            self.Close()

    def Close(self):
        win32file.CloseHandle(self.handle)
        self.handle = None

    def Open(self):
        pipeName = r"\\%s\pipe\%s" % (self.serverName or ".", self.name)
        if self.asServer:
            cx_Logging.Info("Creating pipe (as server): %s", self.name)
            sa = pywintypes.SECURITY_ATTRIBUTES()
            sa.SetSecurityDescriptorDacl(1, None, 0)
            self.handle = win32pipe.CreateNamedPipe(pipeName,
                    win32pipe.PIPE_ACCESS_DUPLEX,
                    win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_WAIT,
                    self.maxInstances, self.maxSize, self.maxSize,
                    self.timeout, sa)
            win32pipe.ConnectNamedPipe(self.handle)
        else:
            cx_Logging.Info("Connecting to pipe (as client): %s on %s",
                    self.name, self.serverName or ".")
            self.handle = win32file.CreateFile(pipeName,
                    win32file.GENERIC_READ | win32file.GENERIC_WRITE, 0, None,
                    win32file.OPEN_EXISTING, 0, None)

    def Read(self):
        hr, data = win32file.ReadFile(self.handle, self.maxLengthDigits)
        bytesToRead = int(data)
        parts = []
        while bytesToRead:
            hr, data = win32file.ReadFile(self.handle,
                    min(self.maxSize, bytesToRead))
            parts.append(data)
            bytesToRead -= len(data)
        return pickle.loads(b"".join(parts))

    def Write(self, obj):
        data = pickle.dumps(obj, 2)
        length = str(len(data))
        maxSize = self.maxSize - self.maxLengthDigits
        if len(length) > self.maxLengthDigits:
            raise ValueTooLong()
        win32file.WriteFile(self.handle,
                length.rjust(self.maxLengthDigits, "0").encode())
        while data:
            dataToWrite = data[:maxSize]
            data = data[maxSize:]
            win32file.WriteFile(self.handle, dataToWrite)


class ValueTooLong(cx_Exceptions.BaseException):
    message = "Value too long to transport over the named pipe."

