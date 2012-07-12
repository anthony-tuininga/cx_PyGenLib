"""
Define classes for accessing data sources in a generic fashion (and may not be
connected directly but indirectly through a web service, for example).
"""

import cx_Exceptions

class DataSource(object):

    def BeginTransaction(self):
        return Transaction()

    def CallFunction(self, functionName, returnType, *args):
        raise NotImplementedError

    def CallProcedure(self, procedureName, *args):
        raise NotImplementedError

    def CommitTransaction(self, transaction):
        raise NotImplementedError

    def DeleteRows(self, tableName, **conditions):
        raise NotImplementedError

    def GetSequenceValue(self, sequenceName):
        raise NotImplementedError

    def GetSqlAndArgs(self, tableName, columnNames, **conditions):
        raise NotImplementedError

    def GetWhereClauseAndArgs(self, **conditions):
        raise NotImplementedError

    def GetRow(self, _tableName, _columnNames, _rowFactory = None,
            **_conditions):
        rows = self.GetRows(_tableName, _columnNames, _rowFactory,
                **_conditions)
        if len(rows) == 0:
            raise cx_Exceptions.NoDataFound()
        elif len(rows) > 1:
            raise cx_Exceptions.TooManyRows(numRows = len(rows))
        return rows[0]

    def GetRows(self, _tableName, _columnNames, _rowFactory = None,
            **_conditions):
        sql, args = self.GetSqlAndArgs(_tableName, _columnNames, **_conditions)
        return self.GetRowsDirect(sql, args, _rowFactory)

    def GetRowsDirect(self, sql, args, rowFactory = None):
        raise NotImplementedError

    def InsertRow(self, tableName, **values):
        raise NotImplementedError

    def UpdateRows(self, tableName, *whereNames, **values):
        raise NotImplementedError


class DatabaseDataSource(DataSource):

    def __init__(self, connection):
        self.connection = connection
        self.cursor = connection.cursor()

    def __enter__(self):
        return self.cursor

    def __exit__(self, excType, excValue, tb):
        if excType is None and excValue is None and tb is None:
            self.connection.commit()
        else:
            self.connection.rollback()

    def _AddWhereClauseAndArg(self, columnName, rawOperator, value,
            whereClauses, args):
        raise NotImplementedError

    def _GetEmptyArgs(self):
        raise NotImplementedError

    def _SetupArgs(self, cursor, transactionItem):
        if transactionItem.procedureName is not None:
            inputSizes = []
            for attrIndex in transactionItem.clobArgs:
                while len(inputSizes) <= attrIndex:
                    inputSizes.append(None)
                inputSizes[attrIndex] = cursor.connection.NCLOB
            for attrIndex in transactionItem.blobArgs:
                while len(inputSizes) <= attrIndex:
                    inputSizes.append(None)
                inputSizes[attrIndex] = cursor.connection.BLOB
            if inputSizes:
                cursor.setinputsizes(*inputSizes)
        else:
            inputSizes = {}
            for attrName in transactionItem.clobArgs:
                inputSizes[attrName] = cursor.connection.NCLOB
            for attrName in transactionItem.blobArgs:
                inputSizes[attrName] = cursor.connection.BLOB
            if inputSizes:
                cursor.setinputsizes(**inputSizes)

    def CallFunction(self, functionName, returnType, *args):
        return self.cursor.callfunc(functionName, returnType, args)

    def CallProcedure(self, procedureName, *args):
        return self.cursor.callproc(procedureName, args)

    def CommitTransaction(self, transaction):
        with self.connection:
            cursor = self.connection.cursor()
            for item in transaction.items:
                self._SetupArgs(cursor, item)
                if item.procedureName is not None:
                    args = list(item.args)
                    for attrIndex in item.fkArgs:
                        args[attrIndex] = item.referencedItem.generatedKey
                    if item.returnType is not None:
                        item.generatedKey = cursor.callfunc(item.procedureName,
                                item.returnType, args)
                    else:
                        cursor.callproc(item.procedureName, args)
                elif item.setValues is not None and item.conditions is None:
                    args = item.setValues.copy()
                    for attrName in item.fkArgs:
                        args[attrName] = item.referencedItem.generatedKey
                    if item.pkIsGenerated:
                        item.generatedKey = \
                                self.GetSequenceValue(item.pkSequenceName)
                        args[item.pkAttrName] = item.generatedKey
                    self.InsertRow(item.tableName, **args)
                elif item.setValues is not None:
                    args = item.setValues.copy()
                    args.update(item.conditions)
                    pkAttrNames = item.conditions.keys()
                    self.UpdateRows(item.tableName, *pkAttrNames, **args)
                else:
                    self.DeleteRows(item.tableName, **item.conditions)

    def DeleteRows(self, tableName, **conditions):
        whereClause, args = self.GetWhereClauseAndArgs(**conditions)
        sql = "delete from %s" % tableName
        if whereClause is not None:
            sql += " where " + whereClause
        self.cursor.execute(sql, args)

    def GetSqlAndArgs(self, tableName, columnNames, **conditions):
        sql = "select %s from %s" % (", ".join(columnNames), tableName)
        if conditions:
            whereClause, args = self.GetWhereClauseAndArgs(**conditions)
            sql += " where " + whereClause
        else:
            args = self._GetEmptyArgs()
        return sql, args

    def GetWhereClauseAndArgs(self, **conditions):
        args = self._GetEmptyArgs()
        whereClause = None
        if conditions:
            whereClauses = []
            for name, value in conditions.iteritems():
                pos = name.find("__")
                if pos < 0:
                    columnName = name
                    rawOperator = None
                else:
                    columnName = name[:pos]
                    rawOperator = name[pos + 2:]
                self._AddWhereClauseAndArg(columnName, rawOperator, value,
                        whereClauses, args)
            whereClause = " and ".join(whereClauses)
        return whereClause, args

    def GetRowsDirect(self, sql, args, rowFactory = None):
        cursor = self.connection.cursor()
        cursor.execute(sql, args)
        if rowFactory is not None:
            cursor.rowfactory = rowFactory
        return cursor.fetchall()


class OracleDataSource(DatabaseDataSource):
    operators = {
            "contains" : "like",
            "endswith" : "like",
            "lt" : "<",
            "lte" : "<=",
            "ne" : "!=",
            "gt" : ">",
            "gte" : ">=",
            "startswith" : "like"
    }

    def _AddWhereClauseAndArg(self, columnName, rawOperator, value,
            whereClauses, args):
        if rawOperator is None:
            if value is None:
                whereClauses.append("%s is null" % columnName)
                return
            clauseFormat = "%s = :%s"
            argName = columnName
        else:
            seqNum = 1
            argName = columnName
            while argName in args:
                seqNum += 1
                strSeqNum = str(seqNum)
                argName = columnName[:30 - len(strSeqNum)] + strSeqNum
            operator = self.operators.get(rawOperator, "?")
            if rawOperator == "contains":
                clauseFormat = "%s like '%%' || :%s || '%%'"
            elif rawOperator == "startswith":
                clauseFormat = "%s like :%s || '%%'"
            elif rawOperator == "endswith":
                clauseFormat = "%s like '%%' || :%s"
            elif rawOperator == "in":
                inClauseParts = []
                for i, inValue in enumerate(value):
                    strSeqNum = str(seqNum + i)
                    argName = columnName[:30 - len(strSeqNum)] + strSeqNum
                    inClauseParts.append(":" + argName)
                    args[argName] = inValue
                clause = "%s in (%s)" % (columnName, ",".join(inClauseParts))
                whereClauses.append(clause)
                return
            else:
                if rawOperator == "ne" and value is None:
                    whereClauses.append("%s is not null" % columnName)
                    return
                clauseFormat = "%%s %s :%%s" % operator
        args[argName] = value
        whereClauses.append(clauseFormat % (columnName, argName))

    def _GetEmptyArgs(self):
        return {}

    def GetSequenceValue(self, sequenceName):
        self.cursor.execute("select %s.nextval from dual" % sequenceName)
        value, = self.cursor.fetchone()
        return value

    def InsertRow(self, tableName, **values):
        insertNames = values.keys()
        insertValues = [":%s" % n for n in insertNames]
        sql = "insert into %s (%s) values (%s)" % \
                (tableName, ",".join(insertNames), ",".join(insertValues))
        self.cursor.execute(sql, values)

    def UpdateRows(self, tableName, *whereNames, **values):
        setClauses = ["%s = :%s" % (n, n) for n in values \
                if n not in whereNames]
        whereClauses = ["%s = :%s" % (n, n) for n in whereNames]
        statement = "update %s set %s where %s" % \
                (tableName, ",".join(setClauses), " and ".join(whereClauses))
        self.cursor.execute(statement, args)


class SqlServerDataSource(DatabaseDataSource):

    def _AddWhereClauseAndArg(self, columnName, rawOperator, value,
            whereClauses, args):
        if rawOperator is None:
            if value is None:
                whereClauses.append("%s is null" % columnName)
                return
            clauseFormat = "%s = ?"
        else:
            operator = self.operators.get(rawOperator, "?")
            if rawOperator == "ne" and value is None:
                whereClauses.append("%s is not null" % columnName)
                return
            clauseFormat = "%%s %s ?" % operator
        args.append(value)
        whereClauses.append(clauseFormat % columnName)

    def _GetEmptyArgs(self):
        return []

    def GetSequenceValue(self, sequenceName):
        self.cursor.execute("select nextval('%s')::integer" % sequenceName)
        value, = self.cursor.fetchone()
        return value

    def InsertRow(self, tableName, **values):
        insertNames = values.keys()
        args = [values[n] for n in insertNames]
        insertValues = ["?" for n in insertNames]
        sql = "insert into %s (%s) values (%s)" % \
                (tableName, ",".join(insertNames), ",".join(insertValues))
        self.cursor.execute(sql, args)

    def UpdateRows(self, tableName, *whereNames, **values):
        args = [values[n] for n in values if n not in whereNames] + \
               [values[n] for n in whereNames]
        setClauses = ["%s = ?" % n for n in values if n not in whereNames]
        whereClauses = ["%s = ?" % n for n in whereNames]
        statement = "update %s set %s where %s" % \
                (tableName, ",".join(setClauses), " and ".join(whereClauses))
        self.cursor.execute(statement, args)


class Transaction(object):

    def __init__(self):
        self.items = []
        self.itemsByRow = {}

    def CreateRow(self, dataSet, row):
        referencedItem = self.itemsByRow.get(dataSet.contextItem)
        args = dataSet._GetArgsFromNames(dataSet.insertAttrNames, row)
        if dataSet.updatePackageName is not None:
            procedureName = "%s.%s" % \
                    (dataSet.updatePackageName, dataSet.insertProcedureName)
            returnType = int if dataSet.pkIsGenerated else None
            item = TransactionItem(procedureName = procedureName, args = args,
                    returnType = returnType, referencedItem = referencedItem)
        else:
            setValues = dict(zip(dataSet.insertAttrNames, args))
            pkSequenceName = dataSet.pkSequenceName if dataSet.pkIsGenerated \
                    else None
            pkAttrName = dataSet.pkAttrNames[0] if dataSet.pkIsGenerated \
                    else None
            item = TransactionItem(tableName = dataSet.updateTableName,
                    setValues = setValues, pkSequenceName = pkSequenceName,
                    pkAttrName = pkAttrName, referencedItem = referencedItem)
        self.items.append(item)
        self.itemsByRow[row] = item
        item._SetArgTypes(dataSet, row, dataSet.insertAttrNames)

    def ModifyRow(self, dataSet, row, origRow):
        if dataSet.updatePackageName is not None:
            args = dataSet._GetArgsFromNames(dataSet.pkAttrNames, origRow) + \
                    dataSet._GetArgsFromNames(dataSet.updateAttrNames, row)
            procedureName = "%s.%s" % \
                    (dataSet.updatePackageName, dataSet.updateProcedureName)
            item = TransactionItem(procedureName = procedureName, args = args)
        else:
            args = dataSet._GetArgsFromNames(dataSet.updateAttrNames, row)
            setValues = dict(zip(dataSet.updateAttrNames, args))
            args = dataSet._GetArgsFromNames(dataSet.pkAttrNames, origRow)
            conditions = dict(zip(dataSet.pkAttrNames, args))
            item = TransactionItem(tableName = dataSet.updateTableName,
                    setValues = setValues, conditions = conditions)
        self.items.append(item)
        item._SetArgTypes(dataSet, row,
                dataSet.pkAttrNames + dataSet.updateAttrNames)

    def RemoveRow(self, dataSet, row):
        args = dataSet._GetArgsFromNames(dataSet.pkAttrNames, row)
        if dataSet.updatePackageName is not None:
            procedureName = "%s.%s" % \
                    (dataSet.updatePackageName, dataSet.deleteProcedureName)
            item = TransactionItem(procedureName = procedureName, args = args)
        else:
            conditions = dict(zip(dataSet.pkAttrNames, args))
            item = TransactionItem(tableName = dataSet.updateTableName,
                    conditions = conditions)
        self.items.append(item)


class TransactionItem(object):

    def __init__(self, procedureName = None, args = None, returnType = None,
            tableName = None, setValues = None, conditions = None,
            referencedItem = None, pkSequenceName = None, pkAttrName = None):
        self.procedureName = procedureName
        self.args = args
        self.returnType = returnType
        self.tableName = tableName
        self.setValues = setValues
        self.conditions = conditions
        self.referencedItem = referencedItem
        self.pkSequenceName = pkSequenceName
        self.pkAttrName = pkAttrName
        self.generatedKey = None
        self.clobArgs = []
        self.blobArgs = []
        self.fkArgs = []

    def _SetArgTypes(self, dataSet, row, attrNames):
        offset = 1 if self.returnType is not None else 0
        for attrIndex, attrName in enumerate(attrNames):
            if attrName in dataSet.clobAttrNames:
                if self.procedureName is not None:
                    self.clobArgs.append(attrIndex + offset)
                else:
                    self.clobArgs.append(attrName)
            elif attrName in dataSet.blobAttrNames:
                if self.procedureName is not None:
                    self.blobArgs.append(attrIndex + offset)
                else:
                    self.blobArgs.append(attrName)
            elif self.referencedItem is not None \
                    and not hasattr(row, attrName) \
                    and hasattr(dataSet.contextItem, attrName):
                if self.procedureName is not None:
                    self.fkArgs.append(attrIndex)
                else:
                    self.fkArgs.append(attrName)

