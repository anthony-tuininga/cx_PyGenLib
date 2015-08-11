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

    def _GetBlobType(self):
        raise NotImplementedError

    def _GetClobType(self):
        raise NotImplementedError

    def _GetEmptyArgs(self):
        raise NotImplementedError

    def _TransactionCallProcedure(self, cursor, item):
        args = self._TransactionSetupPositionalArgs(cursor, item.args,
                item.clobArgs, item.blobArgs, item.fkArgs,
                item.referencedItems)
        if item.returnType is not None:
            item.generatedKey = cursor.callfunc(item.procedureName,
                    item.returnType, args)
        else:
            cursor.callproc(item.procedureName, args)

    def _TransactionDeleteRow(self, cursor, item):
        whereClause, args = self.GetWhereClauseAndArgs(**item.conditions)
        sql = "delete from %s" % item.tableName
        if whereClause is not None:
            sql += " where " + whereClause
        cursor.execute(sql, args)

    def _TransactionInsertRow(self, cursor, item):
        raise NotImplementedError

    def _TransactionSetupKeywordArgs(self, cursor, args, clobArgs, blobArgs,
            fkArgs = [], referencedItems = []):
        inputSizes = {}
        for attrName in clobArgs:
            inputSizes[attrName] = self._GetClobType()
        for attrName in blobArgs:
            inputSizes[attrName] = self._GetBlobType()
        if inputSizes:
            cursor.setinputsizes(**inputSizes)
        args = args.copy()
        for attrName, referencedItem in zip(fkArgs, referencedItems):
            args[attrName] = referencedItem.generatedKey
        return args

    def _TransactionSetupPositionalArgs(self, cursor, args, clobArgs, blobArgs,
            fkArgs = [], referencedItems = []):
        inputSizes = []
        for attrIndex in clobArgs:
            while len(inputSizes) <= attrIndex:
                inputSizes.append(None)
            inputSizes[attrIndex] = self._GetClobType()
        for attrIndex in blobArgs:
            while len(inputSizes) <= attrIndex:
                inputSizes.append(None)
            inputSizes[attrIndex] = self._GetBlobType()
        if inputSizes:
            cursor.setinputsizes(*inputSizes)
        args = list(args)
        for attrIndex, referencedItem in zip(fkArgs, referencedItems):
            args[attrIndex] = referencedItem.generatedKey
        return args

    def CallFunction(self, functionName, returnType, *args):
        return self.cursor.callfunc(functionName, returnType, args)

    def CallProcedure(self, procedureName, *args):
        return self.cursor.callproc(procedureName, args)

    def CommitTransaction(self, transaction):
        with self.connection:
            cursor = self.connection.cursor()
            for item in transaction.items:
                if item.procedureName is not None:
                    self._TransactionCallProcedure(cursor, item)
                elif item.setValues is not None and item.conditions is None:
                    self._TransactionInsertRow(cursor, item)
                elif item.setValues is not None:
                    self._TransactionUpdateRow(cursor, item)
                else:
                    self._TransactionDeleteRow(cursor, item)

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
            for name, value in conditions.items():
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
        shortColumnName = columnName if "." not in columnName \
                else columnName.split(".")[1]
        if rawOperator is None:
            if value is None:
                whereClauses.append("%s is null" % columnName)
                return
            clauseFormat = "%s = :%s"
            argName = shortColumnName
        else:
            seqNum = 1
            argName = shortColumnName
            while argName in args:
                seqNum += 1
                strSeqNum = str(seqNum)
                argName = shortColumnName[:30 - len(strSeqNum)] + strSeqNum
            operator = self.operators.get(rawOperator, "?")
            if rawOperator == "contains":
                clauseFormat = "regexp_like(%s, :%s, 'i')"
            elif rawOperator == "startswith":
                clauseFormat = "regexp_like(%s, '^' || :%s, 'i')"
            elif rawOperator == "endswith":
                clauseFormat = "regexp_like(%s, :%s || '$', 'i')"
            elif rawOperator == "in":
                inClauseParts = []
                for i, inValue in enumerate(value):
                    strSeqNum = str(seqNum + i)
                    argName = shortColumnName[:30 - len(strSeqNum)] + strSeqNum
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

    def _GetBlobType(self):
        return self.connection.BLOB

    def _GetClobType(self):
        return self.connection.NCLOB

    def _GetEmptyArgs(self):
        return {}

    def _TransactionInsertRow(self, cursor, item):
        if item.pkSequenceName is not None:
            sql = "select %s.nextval from dual" % item.pkSequenceName
            cursor.execute(sql)
            item.generatedKey, = cursor.fetchone()
        values = self._TransactionSetupKeywordArgs(cursor, item.setValues,
                item.clobArgs, item.blobArgs, item.fkArgs,
                item.referencedItems)
        if item.pkSequenceName is not None:
            values[item.pkAttrName] = item.generatedKey
        insertNames = list(values.keys())
        insertValues = [":%s" % n for n in insertNames]
        sql = "insert into %s (%s) values (%s)" % \
                (item.tableName, ",".join(insertNames), ",".join(insertValues))
        cursor.execute(sql, values)

    def _TransactionUpdateRow(self, cursor, item):
        args = self._TransactionSetupKeywordArgs(cursor, item.setValues,
                item.clobArgs, item.blobArgs)
        args.update(item.conditions)
        conditionNames = list(item.conditions.keys())
        setClauses = ["%s = :%s" % (n, n) for n in args \
                if n not in conditionNames]
        whereClauses = ["%s = :%s" % (n, n) for n in conditionNames]
        sql = "update %s set %s where %s" % \
                (item.tableName, ",".join(setClauses),
                        " and ".join(whereClauses))
        cursor.execute(sql, args)


class ODBCDataSource(DatabaseDataSource):
    operators = {
            "contains" : "like",
            "icontains" : "ilike",
            "endswith" : "like",
            "iendswith" : "ilike",
            "lt" : "<",
            "lte" : "<=",
            "ne" : "!=",
            "gt" : ">",
            "gte" : ">=",
            "startswith" : "like",
            "istartswith" : "ilike"
    }

    def _AddWhereClauseAndArg(self, columnName, rawOperator, value,
            whereClauses, args):
        if rawOperator is None:
            if value is None:
                whereClauses.append("%s is null" % columnName)
                return
            clauseFormat = "%s = ?"
        else:
            operator = self.operators.get(rawOperator, "?")
            if rawOperator in ("contains", "icontains"):
                clauseFormat = "%s {0} '%%' || ? || '%%'".format(operator)
            elif rawOperator in ("startswith", "istartswith"):
                clauseFormat = "%s {0} ? || '%%'".format(operator)
            elif rawOperator in ("endswith", "iendswith"):
                clauseFormat = "%s {0} '%%' || ?".format(operator)
            elif rawOperator == "ne" and value is None:
                whereClauses.append("%s is not null" % columnName)
                return
            else:
                clauseFormat = "%%s %s ?" % operator
        args.append(value)
        whereClauses.append(clauseFormat % columnName)

    def _GetEmptyArgs(self):
        return []

    def _TransactionInsertRow(self, cursor, item):
        if item.pkSequenceName is not None:
            sql = "select nextval('%s')::integer" % item.pkSequenceName
            cursor.execute(sql)
            item.generatedKey, = cursor.fetchone()
            item.setValues[item.pkAttrName] = item.generatedKey
        insertNames = list(item.setValues.keys())
        args = self._TransactionSetupArgs(cursor, item, insertNames)
        insertValues = ["?" for n in insertNames]
        sql = "insert into %s (%s) values (%s)" % \
                (item.tableName, ",".join(insertNames), ",".join(insertValues))
        cursor.execute(sql, args)
        if hasattr(cursor, "lastrowid") and item.pkAttrName is not None:
            item.generatedKey = cursor.lastrowid

    def _TransactionSetupArgs(self, cursor, item, setValueNames):
        clobArgs = []
        blobArgs = []
        fkArgs = [None] * len(item.fkArgs)
        args = []
        for attrIndex, name in enumerate(setValueNames):
            if name in item.clobArgs:
                clobArgs.append(attrIndex)
            elif name in item.blobArgs:
                blobArgs.append(attrIndex)
            elif name in item.fkArgs:
                fkArgs[item.fkArgs.index(name)] = attrIndex
            args.append(item.setValues[name])
        return self._TransactionSetupPositionalArgs(cursor, args, clobArgs,
                blobArgs, fkArgs, item.referencedItems)

    def _TransactionUpdateRow(self, cursor, item):
        setNames = list(item.setValues.keys())
        conditionNames = list(item.conditions.keys())
        args = self._TransactionSetupArgs(cursor, item, setNames)
        for name in conditionNames:
            args.append(item.conditions[name])
        setClauses = ["%s = ?" % n for n in setNames]
        whereClauses = ["%s = ?" % n for n in conditionNames]
        sql = "update %s set %s where %s" % \
                (item.tableName, ",".join(setClauses),
                        " and ".join(whereClauses))
        cursor.execute(sql, args)


class Transaction(object):

    def __init__(self):
        self.items = []
        self.itemsByRow = {}

    def AddItem(self, **args):
        item = self.itemClass(**args)
        self.items.append(item)
        item.position = len(self.items)
        return item

    def CreateRow(self, dataSet, row):
        referencedItems = []
        referencedItem = self.itemsByRow.get(dataSet.contextItem)
        if referencedItem is not None \
                and (referencedItem.returnType is not None \
                        or referencedItem.pkSequenceName is not None):
            referencedItems.append(referencedItem)
        args = dataSet._GetArgsFromNames(dataSet.insertAttrNames, row)
        if dataSet.updatePackageName is not None:
            procedureName = "%s.%s" % \
                    (dataSet.updatePackageName, dataSet.insertProcedureName)
            returnType = int if dataSet.pkIsGenerated else None
            item = self.AddItem(procedureName = procedureName, args = args,
                    returnType = returnType, referencedItems = referencedItems)
        else:
            setValues = dict(zip(dataSet.insertAttrNames, args))
            pkSequenceName = dataSet.pkSequenceName if dataSet.pkIsGenerated \
                    else None
            pkAttrName = row.pkAttrNames[0] if dataSet.pkIsGenerated \
                    else None
            item = self.AddItem(tableName = dataSet.updateTableName,
                    setValues = setValues, pkSequenceName = pkSequenceName,
                    pkAttrName = pkAttrName, referencedItems = referencedItems)
        self.itemsByRow[row] = item
        item._SetArgTypes(dataSet, row, dataSet.insertAttrNames)
        return item

    def ModifyRow(self, dataSet, row, origRow):
        if dataSet.updatePackageName is not None:
            args = dataSet._GetArgsFromNames(row.pkAttrNames, origRow) + \
                    dataSet._GetArgsFromNames(dataSet.updateAttrNames, row)
            procedureName = "%s.%s" % \
                    (dataSet.updatePackageName, dataSet.updateProcedureName)
            item = self.AddItem(procedureName = procedureName, args = args)
        else:
            args = dataSet._GetArgsFromNames(dataSet.updateAttrNames, row)
            setValues = dict(zip(dataSet.updateAttrNames, args))
            args = dataSet._GetArgsFromNames(row.pkAttrNames, origRow)
            conditions = dict(zip(row.pkAttrNames, args))
            item = self.AddItem(tableName = dataSet.updateTableName,
                    setValues = setValues, conditions = conditions)
        item._SetArgTypes(dataSet, row,
                row.pkAttrNames + dataSet.updateAttrNames)
        return item

    def RemoveRow(self, dataSet, row):
        args = dataSet._GetArgsFromNames(row.pkAttrNames, row)
        if dataSet.updatePackageName is not None:
            procedureName = "%s.%s" % \
                    (dataSet.updatePackageName, dataSet.deleteProcedureName)
            item = self.AddItem(procedureName = procedureName, args = args)
        else:
            conditions = dict(zip(row.pkAttrNames, args))
            item = self.AddItem(tableName = dataSet.updateTableName,
                    conditions = conditions)
        return item

    class itemClass(object):
        position = None

        def __init__(self, procedureName = None, args = None,
                returnType = None, tableName = None, setValues = None,
                conditions = None, referencedItems = None,
                pkSequenceName = None, pkAttrName = None, clobArgs = None,
                blobArgs = None, fkArgs = None, methodName = None):
            self.procedureName = procedureName
            self.methodName = methodName
            self.args = args
            self.returnType = returnType
            self.tableName = tableName
            self.setValues = setValues
            self.conditions = conditions
            self.referencedItems = referencedItems or []
            self.pkSequenceName = pkSequenceName
            self.pkAttrName = pkAttrName
            self.generatedKey = None
            self.clobArgs = clobArgs or []
            self.blobArgs = blobArgs or []
            self.fkArgs = fkArgs or []

        def __repr__(self):
            return "<TransactionItem: position=%s>" % self.position

        def _SetArgType(self, dataSet, row, attrIndex, attrName, offset):
            if attrName in row.clobAttrNames:
                if self.procedureName is not None:
                    self.clobArgs.append(attrIndex + offset)
                else:
                    self.clobArgs.append(attrName)
            elif attrName in row.blobAttrNames:
                if self.procedureName is not None:
                    self.blobArgs.append(attrIndex + offset)
                else:
                    self.blobArgs.append(attrName)
            elif self.referencedItems and not hasattr(row, attrName) \
                    and hasattr(dataSet.contextItem, attrName):
                if self.procedureName is not None:
                    self.fkArgs.append(attrIndex)
                else:
                    self.fkArgs.append(attrName)

        def _SetArgTypes(self, dataSet, row, attrNames):
            offset = 1 if self.returnType is not None else 0
            for attrIndex, attrName in enumerate(attrNames):
                self._SetArgType(dataSet, row, attrIndex, attrName, offset)

