"""
Define classes and methods suitable for accessing databases in a generic way.
"""

import cx_Logging
import datetime
import decimal

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
       which can then be used by ceODBC and cx_Oracle as a row factory."""

    def __new__(cls, name, bases, classDict):
        attrNames = _NormalizeValue(bases, classDict, "attrNames")
        extraAttrNames = _NormalizeValue(bases, classDict, "extraAttrNames")
        charBooleanAttrNames = \
                _NormalizeValue(bases, classDict, "charBooleanAttrNames")
        decimalAttrNames = \
                _NormalizeValue(bases, classDict, "decimalAttrNames")
        clobAttrNames = _NormalizeValue(bases, classDict, "clobAttrNames")
        blobAttrNames = _NormalizeValue(bases, classDict, "blobAttrNames")
        pkAttrNames = _NormalizeValue(bases, classDict, "pkAttrNames")
        sortByAttrNames = _NormalizeValue(bases, classDict, "sortByAttrNames")
        reprAttrNames = _NormalizeValue(bases, classDict, "reprAttrNames")
        useSlots = _NormalizeValue(bases, classDict, "useSlots")
        if useSlots:
            classDict["__slots__"] = attrNames + extraAttrNames
        if "reprName" not in classDict:
            classDict["reprName"] = name
        initLines = []
        for attrName in attrNames + extraAttrNames:
            if attrName in charBooleanAttrNames:
                value = '%s in ("Y", "1", True)' % attrName
            elif attrName in decimalAttrNames:
                value = 'decimal.Decimal(%s) if %s is not None else None' % \
                        (attrName, attrName)
            elif attrName in clobAttrNames:
                format = '%s if %s is None or isinstance(%s, basestring) ' \
                         'else %s.read()'
                value = format % (attrName, attrName, attrName, attrName)
            elif attrName in blobAttrNames:
                format = '%s if %s is None or isinstance(%s, basestring) ' \
                         'else %s.read()'
                value = format % (attrName, attrName, attrName, attrName)
            else:
                value = "%s" % attrName
            initLines.append("    self.%s = %s\n" % (attrName, value))
        initArgs = attrNames + ["%s = None" % n for n in extraAttrNames]
        if initArgs:
            codeString = "def __init__(self, %s):\n%s" % \
                    (", ".join(initArgs), "".join(initLines))
            code = compile(codeString, "GeneratedClass.py", "exec")
            exec code in dict(decimal = decimal), classDict
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
    decimalAttrNames = []
    clobAttrNames = []
    blobAttrNames = []
    sortByAttrNames = []
    reprAttrNames = []
    pkAttrNames = []
    useSlots = True
    sortReversed = False
    tableName = None

    def __repr__(self):
        reprAttrNames = self.reprAttrNames or self.attrNames
        if reprAttrNames:
            values = ["%s=%r" % (n, getattr(self, n)) for n in reprAttrNames]
            return "<%s %s>" % (self.__class__.reprName, ", ".join(values))
        return "<%s>" % self.__class__.reprName

    @classmethod
    def GetRow(cls, dataSource, **conditions):
        return dataSource.GetRow(cls.tableName, cls.attrNames, cls,
                **conditions)

    @classmethod
    def GetRows(cls, dataSource, **conditions):
        return dataSource.GetRows(cls.tableName, cls.attrNames, cls,
                **conditions)

    def Copy(self):
        cls = self.__class__
        args = [getattr(self, n) for n in cls.attrNames]
        row = cls(*args)
        for name in cls.extraAttrNames:
            if hasattr(self, name):
                setattr(row, name, getattr(self, name))
        return row

    def GetAttributeNames(self):
        return self.attrNames + self.extraAttrNames

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


class DataSetMetaClass(type):
    """Metaclass for data sets which sets up the class used for retrieval and
       other data manipulation routines."""

    def __init__(cls, name, bases, classDict):
        super(DataSetMetaClass, cls).__init__(name, bases, classDict)
        if "rowClass" not in classDict:
            classDict = dict(attrNames = cls.attrNames,
                    extraAttrNames = cls.extraAttrNames,
                    charBooleanAttrNames = cls.charBooleanAttrNames,
                    decimalAttrNames = cls.decimalAttrNames,
                    clobAttrNames = cls.clobAttrNames,
                    blobAttrNames = cls.blobAttrNames,
                    pkAttrNames = cls.pkAttrNames, useSlots = cls.useSlots,
                    sortByAttrNames = cls.sortByAttrNames,
                    sortReversed = cls.sortReversed)
            cls.rowClass = RowMetaClass("%sRow" % name, (Row,), classDict)
        cls.attrNames = cls.rowClass.attrNames
        cls.pkAttrNames = cls.rowClass.pkAttrNames
        if cls.tableName is None:
            cls.tableName = cls.rowClass.tableName
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
        if not cls.insertAttrNames:
            if cls.pkIsGenerated and cls.pkSequenceName is None:
                names = [n for n in cls.attrNames if n not in cls.pkAttrNames]
            else:
                names = [n for n in cls.retrievalAttrNames \
                        if n not in cls.attrNames] + cls.attrNames
            cls.insertAttrNames = names
        if not cls.updateAttrNames:
            cls.updateAttrNames = [n for n in cls.attrNames \
                    if n not in cls.pkAttrNames]


class DataSet(object):
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
    decimalAttrNames = []
    clobAttrNames = []
    blobAttrNames = []
    retrievalAttrNames = []
    sortByAttrNames = []
    sortReversed = False
    insertAttrNames = []
    updateAttrNames = []
    uniqueAttrNames = []
    pkIsGenerated = False
    pkSequenceName = None
    useSlots = True

    def __init__(self, dataSource, contextItem = None):
        self.dataSource = dataSource
        self.childDataSets = []
        self.contextItem = contextItem
        self.retrievalArgs = [None] * len(self.retrievalAttrNames)
        if self.updateTableName is None:
            self.updateTableName = self.tableName
        self.Clear()

    def _DeleteRowsInDatabase(self, transaction):
        for row in self.deletedRows.itervalues():
            self.DeleteRowInDatabase(transaction, row)

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
        conditions = dict(zip(self.retrievalAttrNames, args))
        self.retrievalArgs = args
        rows = self.dataSource.GetRows(self.tableName, self.attrNames,
                self.rowClass, **conditions)
        if self.rowClass.sortByAttrNames:
            rows.sort(key = self.rowClass.SortValue)
            if self.rowClass.sortReversed:
                rows.reverse()
        return rows

    def _InsertRowsInDatabase(self, transaction):
        for row in self.insertedRows.itervalues():
            self.InsertRowInDatabase(transaction, row)

    def _OnDeleteRow(self, row):
        pass

    def _OnInsertRow(self, row, choice):
        pass

    def _OnSetValue(self, row, attrName, value, origValue):
        pass

    def _GetPrimaryKeyValues(self, transaction):
        if self.pkIsGenerated and self.updatePackageName is None \
                and self.pkSequenceName is None:
            for row in self.insertedRows.itervalues():
                args = self._GetArgsFromNames(self.uniqueAttrNames, row)
                conditions = dict(zip(self.uniqueAttrNames, args))
                pkValues, = self.dataSource.GetRows(self.tableName,
                        self.pkAttrNames, **conditions)
                for attrIndex, value in enumerate(pkValues):
                    setattr(row, self.pkAttrNames[attrIndex], value)
        elif self.pkIsGenerated:
            attrName = self.pkAttrNames[0]
            for row in self.insertedRows.itervalues():
                item = transaction.itemsByRow.get(row)
                setattr(row, attrName, item.generatedKey)
        for dataSet in self.childDataSets:
            dataSet._GetPrimaryKeyValues(transaction)

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

    def _Update(self, transaction):
        if self.deletedRows:
            self._DeleteRowsInDatabase(transaction)
        if self.updatedRows:
            self._UpdateRowsInDatabase(transaction)
        if self.insertedRows:
            self._InsertRowsInDatabase(transaction)
        for dataSet in self.childDataSets:
            dataSet._Update(transaction)

    def _UpdateRowsInDatabase(self, transaction):
        for handle, origRow in self.updatedRows.iteritems():
            row = self.rows[handle]
            self.UpdateRowInDatabase(transaction, row, origRow)

    def AddChildDataSet(self, cls, contextItem = None):
        dataSet = cls(self.dataSource, contextItem)
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

    def DeleteRowInDatabase(self, transaction, row):
        return transaction.RemoveRow(self, row)

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

    def InsertRowInDatabase(self, transaction, row):
        return transaction.CreateRow(self, row)

    def MarkAllRowsAsNew(self):
        for handle, row in self.rows.iteritems():
            self.insertedRows[handle] = row
        for childDataSet in self.childDataSets:
            childDataSet.MarkAllRowsAsNew()

    def MarkAsChanged(self, handle):
        row = self.rows[handle]
        if handle not in self.insertedRows and handle not in self.updatedRows:
            self.updatedRows[handle] = row.Copy()

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
        if self.retrievalAttrNames:
            self.retrievalArgs = args
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
            self.MarkAsChanged(handle)
            cx_Logging.Debug("setting attr %s on row %s to %r (from %r)",
                    attrName, handle, value, origValue)
            self._OnSetValue(row, attrName, value, origValue)
            setattr(row, attrName, value)

    def Update(self):
        if not self.PendingChanges():
            cx_Logging.Debug("no update to perform")
            return
        self._PreUpdate()
        transaction = self.dataSource.BeginTransaction()
        self._Update(transaction)
        self.dataSource.CommitTransaction(transaction)
        self._GetPrimaryKeyValues(transaction)
        self.ClearChanges()
        self._PostUpdate()

    def UpdateSingleRow(self, handle):
        transaction = self.dataSource.BeginTransaction()
        if handle in self.insertedRows:
            row = self.insertedRows[handle]
            self.InsertRowInDatabase(transaction, row)
        elif handle in self.updatedRows:
            origRow = self.updatedRows[handle]
            row = self.rows[handle]
            self.UpdateRowInDatabase(transaction, row, origRow)
        elif handle in self.deletedRows:
            row = self.deletedRows[handle]
            self.DeleteRowInDatabase(transaction, row)
        self.dataSource.CommitTransaction(transaction)
        self._GetPrimaryKeyValues(transaction)
        if handle in self.insertedRows:
            del self.insertedRows[handle]
        elif handle in self.updatedRows:
            del self.updatedRows[handle]
        elif handle in self.deletedRows:
            del self.deletedRows[handle]

    def UpdateRowInDatabase(self, transaction, row, origRow):
        return transaction.ModifyRow(self, row, origRow)


class FilteredDataSet(DataSet):

    def __init__(self, parentDataSet):
        super(FilteredDataSet, self).__init__(parentDataSet.dataSource)
        self.parentDataSet = parentDataSet

    def _SetRows(self, rows):
        handlesByRow = dict((r, h) \
                for h, r in self.parentDataSet.rows.iteritems())
        self.rows = dict((handlesByRow[r], r) for r in rows)

    def DeleteRow(self, handle):
        super(FilteredDataSet, self).DeleteRow(handle)
        self.parentDataSet.DeleteRow(handle)

    def InsertRow(self, choice = None, row = None):
        handle, parentRow = self.parentDataSet.InsertRow(choice, row)
        self.insertedRows[handle] = self.rows[handle] = parentRow
        return handle, parentRow

    def Retrieve(self, *args):
        allRows = self.parentDataSet.GetRows()
        super(FilteredDataSet, self).Retrieve(allRows, *args)

    def SetValue(self, handle, attrName, value):
        self.parentDataSet.SetValue(handle, attrName, value)

    def Update(self):
        self.parentDataSet.Update()
        self.ClearChanges()


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

