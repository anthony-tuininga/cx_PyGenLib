"""Defines classes useful for solving general problems."""

import cx_Exceptions
import os

class CaselessDict(dict):
    """Implements a dictionary which ignores case in its keys."""

    def __add__(self, other):
        """Support concatenation of anything decended from a dictionary."""
        if isinstance(other, dict):
            x = CaselessDict(self)
            for key in other:
                x[key] = other[key]
            return x
        message = "unsupported operand type(s) for +: '%s' and '%s'" % \
                (type(self).__name__, type(other).__name__)
        raise TypeError(message)

    def __contains__(self, key):
        return dict.__contains__(self, key.lower())

    def __delitem__(self, key):
        return dict.__delitem__(self, key.lower())

    def __getitem__(self, key):
        return dict.__getitem__(self, key.lower())

    def __iadd__(self, other):
        """Support += of anything decended from a dictionary."""
        if isinstance(other, dict):
            for key in other:
                self[key] = other[key]
            return self
        message = "unsupported operand type(s) for +=: '%s' and '%s'" % \
                (type(self).__name__, type(other).__name__)
        raise TypeError(message)

    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        for key in self:
            if key != key.lower():
               dict.__setitem__(self, key.lower(), dict.__getitem__(self, key))
               dict.__delitem__(self, key)

    def __setitem__(self, key, value):
        dict.__setitem__(self, key.lower(), value)

    def get(self, key, defaultValue = None):
        return dict.get(self, key.lower(), defaultValue)

    def has_key(self, key):
        return dict.has_key(self, key.lower())


class DictArray:
    """Implements a multi-dimensional array which is indexed at each level by
       a dictionary, allowing for quick access at each level."""

    def __init__(self, numLevels):
        self.numLevels = numLevels
        self.topLevel = {}

    def __GetSubDict(self, args):
        """Return dictionary for a particular level in the array."""
        if len(args) >= self.numLevels:
            message = "Expecting less than %d arguments" % self.numLevels
            raise TypeError(message)
        mapping = self.topLevel
        for arg in args:
            if arg not in mapping:
                return {}
            mapping = mapping[arg]
        return mapping

    def __SetValue(self, keys, value):
        """Set a value in the array."""
        if len(keys) != self.numLevels:
            raise TypeError("Can only set a value at the leaf level directly.")
        mapping = self.topLevel
        for key in keys[:-1]:
            if key not in mapping:
                mapping[key] = {}
            mapping = mapping[key]
        mapping[keys[-1]] = value

    def AppendValue(self, *args):
        """Add an element to the list which is the value in the array."""
        keys = args[:-1]
        array = self.GetValue(*keys)
        if array is None:
            array = []
            self.__SetValue(keys, array)
        array.append(args[-1])

    def Exists(self, *args):
        """Return a boolean indicating if the item exists in the array."""
        if len(args) != self.numLevels:
            raise TypeError("Expecting %d arguments" % self.numLevels)
        mapping = self.topLevel
        for arg in args:
            if arg not in mapping:
                return False
            mapping = mapping[arg]
        return True

    def GetValue(self, *args):
        """Return the value at the given level of the tree."""
        if len(args) != self.numLevels:
            raise TypeError("Expecting %d arguments" % self.numLevels)
        value = self.topLevel
        for arg in args:
            if arg not in value:
                return None
            value = value[arg]
        return value

    def HasValues(self):
        """Return a boolean indicating if any values are in the array."""
        return len(self.topLevel) != 0

    def SetValue(self, *args):
        """Sets the value in the array."""
        self.__SetValue(args[:-1], args[-1])

    def SortedKeys(self, *args):
        """Return the keys at the specified level."""
        keys = list(self.__GetSubDict(args).keys())
        keys.sort()
        return keys

    def Split(self, *args):
        """Split the array at the given level and return a new array rooted
           at that level."""
        mapping = self.__GetSubDict(args)
        array = DictArray(self.numLevels - len(args))
        array.topLevel = mapping
        return array


class PythonConfigFile(object):
    """Base class for all configuration files which use Python itself to
       define the configuration."""

    def ReadConfiguration(self, fileName):
        """Read the configuration file by simply executing the script within
           the framework specified by the subclass."""
        if not os.path.exists(fileName):
            raise cx_Exceptions.MissingConfigurationFile(fileName = fileName)
        message = "Reading configuration from %s..." % fileName
        print(message)
        self.__scriptGlobals = self.ScriptGlobals()
        exec(compile(open(fileName).read(), fileName, 'exec'),
                self.__scriptGlobals)

    def ScriptGlobals(self):
        """Intended to be replaced by subclasses as needed."""
        return dict()


class ClassFactory(object):
    """Implements a class factory which builds classes as needed and caches
       them."""

    def __init__(self):
        self.classes = {}

    def _BuildClass(self, key):
        """Build the class for the key and return it. This is intended to be
           implemented in a child class."""
        raise cx_Exceptions.NotImplemented()

    def _GenerateClass(self, className, baseClass, classDict, initArgNames):
        """Generate a class with a generated constructor."""
        if initArgNames:
            initLines = ["    self.%s = %s\n" % (n, n) for n in initArgNames]
            codeString = "def __init__(self, %s):\n%s" % \
                    (", ".join(initArgNames), "".join(initLines))
            code = compile(codeString, "GeneratedClass.py", "exec")
            exec(code, dict(), classDict)
        return type(className, (baseClass,), classDict)

    def GetClass(self, key):
        """Return the class associated with the key or build a new one."""
        try:
            return self.classes[key]
        except KeyError:
            cls = self.classes[key] = self._BuildClass(key)
            return cls

