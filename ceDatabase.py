"""
Define classes and methods suitable for accessing databases in a generic way.
"""

import cx_Logging
import datetime

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
        charBooleanAttrNames = \
                _NormalizeValue(bases, classDict, "charBooleanAttrNames")
        pkAttrNames = _NormalizeValue(bases, classDict, "pkAttrNames")
        sortByAttrNames = _NormalizeValue(bases, classDict, "sortByAttrNames")
        reprAttrNames = _NormalizeValue(bases, classDict, "reprAttrNames")
        useSlots = _NormalizeValue(bases, classDict, "useSlots")
        if useSlots:
            classDict["__slots__"] = attrNames + extraAttrNames
        if "reprName" not in classDict:
            classDict["reprName"] = name
        if attrNames:
            initLines = []
            for attrName in attrNames:
                if attrName in charBooleanAttrNames:
                    value = '%s in ("Y", "1", True)' % attrName
                else:
                    value = "%s" % attrName
                initLines.append("    self.%s = %s\n" % (attrName, value))
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
    charBooleanAttrNames = []
    sortByAttrNames = []
    reprAttrNames = []
    pkAttrNames = []
    useSlots = True

    def __repr__(self):
        reprAttrNames = self.reprAttrNames or self.attrNames
        if reprAttrNames:
            values = ["%s=%r" % (n, getattr(self, n)) for n in reprAttrNames]
            return "<%s %s>" % (self.__class__.reprName, ", ".join(values))
        return "<%s>" % self.__class__.reprName

    def Copy(self):
        cls = self.__class__
        args = [getattr(self, n) for n in cls.attrNames]
        row = cls(*args)
        for name in cls.extraAttrNames:
            if hasattr(self, name):
                setattr(row, name, getattr(self, name))
        return row

    def GetPrimaryKeyTuple(self):
        return tuple([getattr(self, n) for n in self.pkAttrNames])

    def SortValue(self):
        if len(self.sortByAttrNames) == 1:
            value = getattr(self, self.sortByAttrNames[0])
            if isinstance(value, basestring):
                return value.upper()
            elif isinstance(value, (datetime.datetime, datetime.date)):
                return str(value)
            return value
        values = []
        for attrName in self.sortByAttrNames:
            value = getattr(self, attrName)
            if isinstance(value, basestring):
                value = value.upper()
            elif isinstance(value, (datetime.datetime, datetime.date)):
                value = str(value)
            values.append(value)
        return tuple(values)


class WrappedConnection(object):

    def __init__(self, connection):
        self.connection = connection
        self.isOracle = self._IsOracle(type(connection))

    def _GetWhereClauses(self, names, paramsUsed = 0):
        if self.isOracle:
            return ["%s = :%s" % (n, paramsUsed + i + 1) \
                    for i, n in enumerate(names)]
        else:
            return ["%s = ?" % n for n in names]

    def _IsOracle(self, cls):
        if cls.__module__ == "cx_Oracle":
            return True
        for base in cls.__bases__:
            if self._IsOracle(base):
                return True
        return False


class DataSetMetaClass(type):
    """Metaclass for data sets which sets up the class used for retrieval and
       other data manipulation routines."""

    def __init__(cls, name, bases, classDict):
        super(DataSetMetaClass, cls).__init__(name, bases, classDict)
        if "rowClass" not in classDict:
            classDict = dict(attrNames = cls.attrNames,
                    extraAttrNames = cls.extraAttrNames,
                    charBooleanAttrNames = cls.charBooleanAttrNames,
                    pkAttrNames = cls.pkAttrNames, useSlots = cls.useSlots,
                    sortByAttrNames = cls.sortByAttrNames)
            cls.rowClass = RowMetaClass("%sRow" % name, (Row,), classDict)
        cls.attrNames = cls.rowClass.attrNames
        cls.pkAttrNames = cls.rowClass.pkAttrNames
        if isinstance(cls.uniqueAttrNames, basestring):
            cls.uniqueAttrNames = cls.uniqueAttrNames.split()
        if isinstance(cls.insertAttrNames, basestring):
            cls.insertAttrNames = cls.insertAttrNames.split()
        if isinstance(cls.updateAttrNames, basestring):
            cls.updateAttrNames = cls.updateAttrNames.split()
        if isinstance(cls.retrievalAttrNames, basestring):
            cls.retrievalAttrNames = cls.retrievalAttrNames.split()
        cls.retrievalAttrIndexes = \
                dict([(n, i) for i, n in enumerate(cls.retrievalAttrNames)])


class DataSet(WrappedConnection):
    """Base class for data sets which allows for retrieval, insert, update and
       deletion of rows in a database."""
    __metaclass__ = DataSetMetaClass
    updatePackageName = None
    insertProcedureName = "New"
    updateProcedureName = "Modify"
    deleteProcedureName = "Remove"
    tableName = None
    updateTableName = None
    attrNames = []
    extraAttrNames = []
    pkAttrNames = []
    charBooleanAttrNames = []
    retrievalAttrNames = []
    sortByAttrNames = []
    sortReversed = False
    insertAttrNames = []
    updateAttrNames = []
    uniqueAttrNames = []
    pkIsGenerated = False
    pkSequenceName = None
    useSlots = True

    def __init__(self, connection, contextItem = None):
        super(DataSet, self).__init__(connection)
        self.childDataSets = []
        self.contextItem = contextItem
        self.retrievalArgs = [None] * len(self.retrievalAttrNames)
        if self.updateTableName is None:
            self.updateTableName = self.tableName
        self.Clear()

    def _DeleteRowsInDatabase(self, cursor):
        for row in self.deletedRows.itervalues():
            self.DeleteRowInDatabase(cursor, row)

    def _GetArgsFromNames(self, names, row = None):
        args = []
        contextItem = self.contextItem
        for name in names:
            if row is not None and hasattr(row, name):
                value = getattr(row, name)
            elif contextItem is not None and hasattr(contextItem, name):
                value = getattr(contextItem, name)
            else:
                argIndex = self.retrievalAttrIndexes[name]
                value = self.retrievalArgs[argIndex]
            if name in self.rowClass.charBooleanAttrNames:
                value = value and "Y" or "N"
            args.append(value)
        return args

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

    def _GetRows(self, *args):
        sql = self._GetSqlForRetrieve()
        cursor = self.connection.cursor()
        cursor.execute(sql, args)
        cursor.rowfactory = self.rowClass
        self.retrievalArgs = args
        rows = cursor.fetchall()
        if self.rowClass.sortByAttrNames:
            rows.sort(key = self.rowClass.SortValue)
            if self.sortReversed:
                rows.reverse()
        return rows

    def _GetSqlForRetrieve(self):
        sql = "select %s from %s" % (", ".join(self.attrNames), self.tableName)
        if self.retrievalAttrNames:
            whereClauses = self._GetWhereClauses(self.retrievalAttrNames)
            sql += " where %s" % " and ".join(whereClauses)
        return sql

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

    def _SetRows(self, rows):
        self.rows = dict(enumerate(rows))

    def _SortRep(self, value):
        if isinstance(value, basestring):
            return value.upper()
        elif isinstance(value, (datetime.datetime, datetime.date)):
            return str(value)
        return value

    def _Update(self, cursor):
        if self.deletedRows:
            self._DeleteRowsInDatabase(cursor)
        if self.updatedRows:
            self._UpdateRowsInDatabase(cursor)
        if self.insertedRows:
            self._InsertRowsInDatabase(cursor)
        for dataSet in self.childDataSets:
            dataSet._Update(cursor)

    def _UpdateRowsInDatabase(self, cursor):
        for handle, origRow in self.updatedRows.iteritems():
            row = self.rows[handle]
            self.UpdateRowInDatabase(cursor, row, origRow)

    def AddChildDataSet(self, cls, contextItem = None):
        dataSet = cls(self.connection, contextItem)
        self.childDataSets.append(dataSet)
        return dataSet

    def CanDeleteRow(self, rowHandle):
        return True

    def CanInsertRow(self):
        return True

    def Clear(self, includeChildren = True):
        self.rows = {}
        if includeChildren:
            for dataSet in self.childDataSets:
                dataSet.Clear()
        self.ClearChanges(includeChildren = False)

    def ClearChanges(self, includeChildren = True):
        self.insertedRows = {}
        self.updatedRows = {}
        self.deletedRows = {}
        if includeChildren:
            for dataSet in self.childDataSets:
                dataSet.ClearChanges()

    def DeleteRow(self, handle):
        row = self.rows[handle]
        self._OnDeleteRow(row)
        self.rows.pop(handle)
        if handle in self.insertedRows:
            self.insertedRows.pop(handle)
        else:
            if handle in self.updatedRows:
                self.updatedRows.pop(handle)
            self.deletedRows[handle] = row

    def DeleteRowInDatabase(self, cursor, row):
        args = self._GetArgsFromNames(self.pkAttrNames, row)
        if self.updatePackageName is not None:
            fullProcedureName = "%s.%s" % \
                    (self.updatePackageName, self.deleteProcedureName)
            cursor.callproc(fullProcedureName, args)
        else:
            clauses = self._GetWhereClauses(self.pkAttrNames)
            sql = "delete from %s where %s" % \
                    (self.updateTableName, " and ".join(clauses))
            cursor.execute(sql, args)

    def GetGeneratedPrimaryKey(self, cursor):
        if self.isOracle:
            sql = "select %s.nextval from dual" % self.pkSequenceName
        else:
            sql = "select nextval('%s')::integer" % self.pkSequenceName
        cursor.execute(sql)
        value, = cursor.fetchone()
        return value

    def GetKeyedDataSet(self, *attrNames):
        return KeyedDataSet(self, *attrNames)

    def GetRows(self):
        return self.rows.values()

    def GetSortedRows(self, *attrNames):
        handles = self.GetSortedRowHandles(*attrNames)
        return [self.rows[h] for h in handles]

    def GetSortedRowHandles(self, *attrNames):
        itemsToSort = [([self._SortRep(getattr(i, n)) for n in attrNames], h) \
                for h, i in self.rows.iteritems()]
        itemsToSort.sort()
        return [i[1] for i in itemsToSort]

    def InsertRow(self, choice = None, row = None):
        handle = self._GetNewRowHandle()
        if row is None:
            row = self.rowClass.New()
        self._OnInsertRow(row, choice)
        self.insertedRows[handle] = self.rows[handle] = row
        return handle, row

    def InsertRowInDatabase(self, cursor, row):
        if self.pkIsGenerated and self.pkSequenceName is not None:
            attrName, = self.pkAttrNames
            value = self.GetGeneratedPrimaryKey(cursor)
            setattr(row, attrName, value)
        if self.insertAttrNames:
            names = self.insertAttrNames
        elif self.pkIsGenerated and self.pkSequenceName is None:
            names = [n for n in self.attrNames if n not in self.pkAttrNames]
        else:
            names = [n for n in self.retrievalAttrNames \
                    if n not in self.attrNames] + self.attrNames
        args = self._GetArgsFromNames(names, row)
        if self.updatePackageName is not None:
            fullProcedureName = "%s.%s" % \
                    (self.updatePackageName, self.insertProcedureName)
            if self.pkIsGenerated:
                attrName, = self.pkAttrNames
                value = cursor.callfunc(fullProcedureName, int, args)
                setattr(row, attrName, value)
            else:
                cursor.callproc(fullProcedureName, args)
        else:
            if self.isOracle:
                values = [":%s" % i for i in range(len(names))]
            else:
                values = ["?"] * len(names)
            sql = "insert into %s (%s) values (%s)" % \
                    (self.updateTableName, ",".join(names), ",".join(values))
            cursor.execute(sql, args)
            if self.pkIsGenerated and self.pkSequenceName is None:
                selectItems = ",".join(self.pkAttrNames)
                whereClauses = ["%s = ?" % n for n in self.uniqueAttrNames]
                sql = "select %s from %s where %s" % \
                        (",".join(self.pkAttrNames), self.tableName,
                        " and ".join(whereClauses))
                args = self._GetArgsFromNames(self.uniqueAttrNames, row)
                cursor.execute(sql, args)
                pkValues, = cursor.fetchall()
                for attrIndex, value in enumerate(pkValues):
                    setattr(row, self.pkAttrNames[attrIndex], value)

    def MarkAllRowsAsNew(self):
        for handle, row in self.rows.iteritems():
            self.insertedRows[handle] = row
        for childDataSet in self.childDataSets:
            childDataSet.MarkAllRowsAsNew()

    def PendingChanges(self):
        if self.insertedRows or self.updatedRows or self.deletedRows:
            return True
        for dataSet in self.childDataSets:
            if dataSet.PendingChanges():
                return True
        return False

    def RevertChanges(self, includeChildren = True):
        while self.insertedRows:
            handle, row = self.insertedRows.popitem()
            del self.rows[handle]
        while self.deletedRows:
            handle, row = self.deletedRows.popitem()
            self.rows[handle] = row
        while self.updatedRows:
            handle, row = self.updatedRows.popitem()
            self.rows[handle] = row
        if includeChildren:
            for dataSet in self.childDataSets:
                dataSet.RevertChanges()

    def Retrieve(self, *args):
        self.Clear()
        if not args and self.retrievalAttrNames:
            args = self._GetArgsFromNames(self.retrievalAttrNames)
        self.retrievalArgs = args
        self._SetRows(self._GetRows(*args))

    def SetRows(self, rows):
        self._SetRows(rows)
        self.ClearChanges()

    def SetValue(self, handle, attrName, value):
        row = self.rows[handle]
        origValue = getattr(row, attrName)
        if value != origValue:
            if handle not in self.insertedRows \
                    and handle not in self.updatedRows:
                self.updatedRows[handle] = row.Copy()
            cx_Logging.Debug("setting attr %s on row %s to %r (from %r)",
                    attrName, handle, value, origValue)
            self._OnSetValue(row, attrName, value, origValue)
            setattr(row, attrName, value)

    def Update(self):
        if not self.PendingChanges():
            cx_Logging.Debug("no update to perform")
            return
        self._PreUpdate()
        cursor = self.connection.cursor()
        try:
            self._Update(cursor)
            self.connection.commit()
        except:
            self.connection.rollback()
            raise
        self.ClearChanges()
        self._PostUpdate()

    def UpdateSingleRow(self, handle):
        cursor = self.connection.cursor()
        try:
            if handle in self.insertedRows:
                row = self.insertedRows[handle]
                self.InsertRowInDatabase(cursor, row)
            elif handle in self.updatedRows:
                origRow = self.updatedRows[handle]
                row = self.rows[handle]
                self.UpdateRowInDatabase(cursor, row, origRow)
            elif handle in self.deletedRows:
                row = self.deletedRows[handle]
                self.DeleteRowInDatabase(cursor, row)
            self.connection.commit()
        except:
            self.connection.rollback()
            raise
        if handle in self.insertedRows:
            del self.insertedRows[handle]
        elif handle in self.updatedRows:
            del self.updatedRows[handle]
        elif handle in self.deletedRows:
            del self.deletedRows[handle]

    def UpdateRowInDatabase(self, cursor, row, origRow):
        if self.updateAttrNames:
            dataAttrNames = self.updateAttrNames
        else:
            dataAttrNames = [n for n in self.attrNames \
                    if n not in self.pkAttrNames]
        if self.updatePackageName is not None:
            args = self._GetArgsFromNames(self.pkAttrNames, origRow) + \
                    self._GetArgsFromNames(dataAttrNames, row)
            fullProcedureName = "%s.%s" % \
                    (self.updatePackageName, self.updateProcedureName)
            cursor.callproc(fullProcedureName, args)
        else:
            args = self._GetArgsFromNames(dataAttrNames, row) + \
                    self._GetArgsFromNames(self.pkAttrNames, origRow)
            if self.isOracle:
                setClauses = ["%s = :%s" % (n, i + 1) \
                        for i, n in enumerate(dataAttrNames)]
            else:
                setClauses = ["%s = ?" % n for n in dataAttrNames]
            whereClauses = self._GetWhereClauses(self.pkAttrNames,
                    len(setClauses))
            sql = "update %s set %s where %s" % \
                    (self.updateTableName, ", ".join(setClauses),
                    " and ".join(whereClauses))
            cursor.execute(sql, args)


class KeyedDataSet(object):

    def __init__(self, dataSet, *attrNames):
        self.dataSet = dataSet
        self.rows = {}
        for handle, row in dataSet.rows.iteritems():
            key = tuple([getattr(row, n) for n in attrNames])
            self.rows[key] = handle

    def DeleteRow(self, *key):
        try:
            handle = self.rows.pop(key)
        except KeyError:
            return
        self.dataSet.DeleteRow(handle)

    def FindRow(self, *key):
        handle = self.rows.get(key)
        if handle is not None:
            return RowForUpdate(self.dataSet, handle)

    def InsertRow(self, choice = None):
        handle, row = self.dataSet.InsertRow(choice)
        return RowForUpdate(self.dataSet, handle)


class RowForUpdate(object):

    def __init__(self, dataSet, handle):
        self._dataSet = dataSet
        self._handle = handle
        self._row = dataSet.rows[handle]

    def __getattr__(self, attrName):
        if attrName.startswith("_"):
            return object.__getattr__(self, attrName)
        return getattr(self._row, attrName)

    def __setattr__(self, attrName, value):
        if attrName.startswith("_"):
            object.__setattr__(self, attrName, value)
        else:
            self._dataSet.SetValue(self._handle, attrName, value)

    def Delete(self):
        self._dataSet.DeleteRow(self._handle)

