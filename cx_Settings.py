"""Classes for handling the saving and restoring of settings."""

import cx_Logging
import os
import sys

if sys.platform == "win32":

    import win32api
    import win32con
    import pywintypes

    class Session:
        """Handles saving and restoring settings from the registry."""

        def __init__(self, registryLoc, baseName):
            self.baseName = baseName
            self.key = win32api.RegCreateKey(win32con.HKEY_CURRENT_USER,
                    os.path.join(registryLoc, baseName))

        def GetValue(self, key, defaultValue = None):
            """Return a value from the registry, returning the default value
               if a value cannot be found and destroying invalid values if
               any are found."""
            try:
                value, type = win32api.RegQueryValueEx(self.key, key)
            except:
                cx_Logging.Debug(
                        "Getting default for session key %s\\%s. Value=\"%s\"",
                        self.baseName, key, defaultValue)
                return defaultValue
            try:
                returnValue = eval(str(value))
                cx_Logging.Debug("Getting session key %s\\%s. Value=\"%s\"",
                        self.baseName, key, returnValue)
                return returnValue
            except:
                win32api.RegDeleteValue(self.key, key)
                cx_Logging.Debug(
                        "Getting default for session key %s\\%s. Value=\"%s\"",
                        self.baseName, key, defaultValue)
                return defaultValue

        def SetValue(self, key, value):
            """Set the value in the registry."""
            cx_Logging.Debug("Setting Session key %s\\%s=\"%s\"",
                    self.baseName, key, repr(value))
            win32api.RegSetValueEx(self.key, key, 0, win32con.REG_SZ,
                    repr(value))


    class Handler:
        """Handles saving and restoring settings in the registry."""

        def __init__(self, vendorName, applicationName):
            self.registryLoc = os.path.join("SOFTWARE", vendorName,
                    applicationName)
            baseKey = win32api.RegCreateKey(win32con.HKEY_CURRENT_USER,
                    "SOFTWARE")
            vendorKey = win32api.RegCreateKey(baseKey, vendorName)
            win32api.RegCreateKey(vendorKey, applicationName)

        def GetSession(self, baseName):
            """Return a session which can be used for saving and restoring
               values from the registry. This means that the registry is not
               constantly being opened and closed during a series of getting
               and setting values."""
            return Session(self.registryLoc, baseName)


else:

    import dbm.gnu

    class Session:
        """Handles saving and restoring settings from a GDBM database."""

        def __init__(self, fileName, baseName):
            self.database = dbm.gnu.open(fileName, "cf")
            self.baseName = baseName

        def GetValue(self, key, defaultValue = None):
            """Return a value from the database, returning the default value
               if a value cannot be found and destroying invalid values if
               any are found."""
            key = "%s.%s" % (self.baseName, key)
            try:
                value = self.database[key]
            except KeyError:
                cx_Logging.Debug("no value for key %s, default value is %s",
                        key, defaultValue)
                return defaultValue
            try:
                value = eval(value)
            except:
                del self.database[key]
                cx_Logging.Debug("bad value for key %s, default value is %s",
                        key, defaultValue)
                return defaultValue
            cx_Logging.Debug("value for key %s is %r", key, value)
            return value

        def SetValue(self, key, value):
            """Set the value in the database."""
            key = "%s.%s" % (self.baseName, key)
            self.database[key] = repr(value)
            cx_Logging.Debug("setting value for key %s to %r", key, value)

    class Handler:
        """Handles saving and restoring settings in a GDBM database."""

        def __init__(self, vendorName, applicationName):
            baseDirName = ".%s" % vendorName.lower()
            baseFileName = "%s.db" % applicationName
            self.fileName = os.path.join(os.environ["HOME"], baseDirName,
                    baseFileName)
            dirName = os.path.dirname(self.fileName)
            if not os.path.isdir(dirName):
                os.makedirs(dirName)

        def GetSession(self, baseName):
            """Return a session which can be used for saving and restoring
               values from the database. This means that the file is not
               constantly being opened and closed during a series of getting
               and setting values."""
            return Session(self.fileName, baseName)

