"""
Define classes and methods suitable for accessing databases in a generic way.
"""

import cx_Logging

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
        _NormalizeValue(bases, classDict, "pkAttrNames")
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
    """Base class for use with the row meta class (see above)."""
    __metaclass__ = RowMetaClass
    __slots__ = []
    attrNames = []
    extraAttrNames = []
    pkAttrNames = []
    useSlots = True

    def __repr__(self):
        if self.attrNames:
            values = ["%s=%r" % (n, getattr(self, n)) for n in self.attrNames]
            return "<%s %s>" % (self.__class__.__name__, ", ".join(values))
        return "<%s>" % self.__class__.__name__

    def Copy(self):
        cls = self.__class__
        args = [getattr(self, n) for n in cls.attrNames]
        return cls(*args)


class DataSetMetaClass(type):
    """Metaclass for data sets which sets up the class used for retrieval and
       other data manipulation routines."""

    def __init__(cls, name, bases, classDict):
        super(DataSetMetaClass, cls).__init__(name, bases, classDict)
        cls.rowClass = RowMetaClass("%sRow" % name, (Row,),
                dict(attrNames = cls.attrNames))
        cls.attrNames = cls.rowClass.attrNames
        if isinstance(cls.pkAttrNames, basestring):
            cls.pkAttrNames = cls.pkAttrNames.split()
        if isinstance(cls.retrievalAttrNames, basestring):
            cls.retrievalAttrNames = cls.retrievalAttrNames.split()


class DataSet(object):
    """Base class for data sets which allows for retrieval, insert, update and
       deletion of rows in a database."""
    __metaclass__ = DataSetMetaClass
    tableName = None
    attrNames = []
    pkAttrNames = []
    retrievalAttrNames = []

    def __init__(self, connection):
        self.connection = connection
        self.Clear()

    def _DeleteRowsInDatabase(self, cursor):
        cx_Logging.Debug("deleting rows in database....")
        for row in self.deletedRows.itervalues():
            self.DeleteRowInDatabase(cursor, row)

    def _GetNewRowHandle(self):
        if self.rows:
            handle = max(self.rows) + 1
        else:
            handle = 0
        if self.deletedRows:
            existingHandle = max(self.deletedRows)
            if existingHandle >= handle:
                handle = existingHandle + 1
        return handle

    def _InsertRowsInDatabase(self, cursor):
        for row in self.insertedRows.itervalues():
            self.InsertRowInDatabase(cursor, row)

    def _OnDeleteRow(self, row):
        pass

    def _OnInsertRow(self, row, choice):
        pass

    def _OnSetValue(self, row, attrName, value, origValue):
        pass

    def _PostUpdate(self):
        pass

    def _PreUpdate(self):
        pass

    def _UpdateRowsInDatabase(self, cursor):
        for handle, origRow in self.updatedRows.iteritems():
            row = self.rows[handle]
            self.UpdateRowInDatabase(cursor, row, origRow)

    def CanDeleteRow(self, rowHandle):
        return True

    def CanInsertRow(self):
        return True

    def Clear(self):
        self.rows = {}
        self.ClearChanges()

    def ClearChanges(self):
        self.insertedRows = {}
        self.updatedRows = {}
        self.deletedRows = {}

    def DeleteRow(self, handle):
        row = self.rows[handle]
        self._OnDeleteRow(row)
        self.rows.pop(handle)
        if handle in self.insertedRows:
            self.insertedRows.pop(handle)
        else:
            self.deletedRows[handle] = row

    def DeleteRowInDatabase(self, cursor, row):
        args = [getattr(row, n) for n in self.pkAttrNames]
        clauses = ["%s = ?" % n for n in self.pkAttrNames]
        sql = "delete from %s where %s" % \
                (self.tableName, " and ".join(clauses))
        cursor.execute(sql, args)

    def InsertRow(self, choice = None):
        handle = self._GetNewRowHandle()
        row = self.rowClass.New()
        self._OnInsertRow(row, choice)
        self.insertedRows[handle] = self.rows[handle] = row
        return handle, row

    def InsertRowInDatabase(self, cursor, row):
        args = [getattr(row, n) for n in self.attrNames]
        names = [n for n in self.attrNames]
        values = ["?"] * len(self.attrNames)
        sql = "insert into %s (%s) values (%s)" % \
                (self.tableName, ",".join(names), ",".join(values))
        cursor.execute(sql, args)

    def PendingChanges(self):
        return bool(self.insertedRows or self.updatedRows or self.deletedRows)

    def Retrieve(self, *args):
        self.Clear()
        sql = "select %s from %s" % (", ".join(self.attrNames), self.tableName)
        if self.retrievalAttrNames:
            whereClauses = ["%s = ?" % n for n in self.retrievalAttrNames]
            sql += " where %s" % " and ".join(whereClauses)
        cursor = self.connection.cursor()
        cursor.execute(sql, args)
        cursor.rowfactory = self.rowClass
        self.retrievalArgs = args
        self.rows = dict(enumerate(cursor))

    def SetValue(self, handle, attrName, value):
        row = self.rows[handle]
        origValue = getattr(row, attrName)
        if value != origValue:
            if handle not in self.insertedRows \
                    and handle not in self.updatedRows:
                self.updatedRows[handle] = row.Copy()
            cx_Logging.Debug("setting attr %s on row %s to %r", attrName,
                    handle, value)
            self._OnSetValue(row, attrName, value, origValue)
            setattr(row, attrName, value)

    def Update(self):
        if not self.PendingChanges():
            cx_Logging.Debug("no update to perform")
            return
        self._PreUpdate()
        cursor = self.connection.cursor()
        try:
            if self.deletedRows:
                self._DeleteRowsInDatabase(cursor)
            if self.updatedRows:
                self._UpdateRowsInDatabase(cursor)
            if self.insertedRows:
                self._InsertRowsInDatabase(cursor)
            self.connection.commit()
        except:
            self.connection.rollback()
            raise
        self.ClearChanges()
        self._PostUpdate()

    def UpdateRowInDatabase(self, cursor, row, origRow):
        dataAttrNames = [n for n in self.attrNames if n not in self.pkAttrNames]
        args = [getattr(row, n) for n in dataAttrNames + self.pkAttrNames]
        setClauses = ["%s = ?" % n for n in dataAttrNames]
        whereClauses = ["%s = ?" % n for n in self.pkAttrNames]
        sql = "update %s set %s where %s" % \
                (self.tableName, ", ".join(setClauses),
                " and ".join(whereClauses))
        cursor.execute(sql, args)

