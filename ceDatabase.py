"""
Define classes and methods suitable for accessing databases in a generic way.
"""

def _NormalizeValue(bases, classDict, name):
    """Helper routine for row metaclass."""
    value = classDict.get(name)
    if value is None:
        for base in bases:
            value = getattr(base, name, None)
            if value is not None:
                break
    if isinstance(value, basestring):
        value = value.split()
    classDict[name] = value
    return value


class RowMetaClass(type):
    """Metaclass for rows which automatically builds a constructor function
       which can then be used by ceODBC and cx_Oracle as a cursor row
       factory."""

    def __new__(cls, name, bases, classDict):
        attrNames = _NormalizeValue(bases, classDict, "attrNames")
        extraAttrNames = _NormalizeValue(bases, classDict, "extraAttrNames")
        useSlots = _NormalizeValue(bases, classDict, "useSlots")
        if useSlots:
            classDict["__slots__"] = attrNames + extraAttrNames
        if attrNames:
            initLines = ["    self.%s = %s\n" % (n, n) for n in attrNames]
            codeString = "def __init__(self, %s):\n%s" % \
                    (", ".join(attrNames), "".join(initLines))
            code = compile(codeString, "GeneratedClass.py", "exec")
            exec code in dict(), classDict
        return type.__new__(cls, name, bases, classDict)

    def New(cls):
        args = [None] * len(cls.attrNames)
        return cls(*args)


class Row(object):
    __metaclass__ = RowMetaClass
    __slots__ = []
    attrNames = []
    extraAttrNames = []
    useSlots = True

    def __repr__(self):
        if self.__slots__:
            values = ["%s=%r" % (n, getattr(self, n)) for n in self.__slots__]
            return "<%s %s>" % (self.__class__.__name__, ", ".join(values))
        return "<%s>" % self.__class__.__name__

    def Copy(self):
        cls = self.__class__
        args = [getattr(self, n) for n in cls.attrNames]
        return cls(*args)

