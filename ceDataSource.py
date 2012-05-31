"""
Define classes for accessing data sources in a generic fashion (and may not be
connected directly but indirectly through a web service, for example).
"""

class DataSource(object):

    def CallFunction(self, functionName, returnType, *args):
        raise NotImplementedError

    def CallProcedure(self, procedureName, *args):
        raise NotImplementedError

    def DeleteRows(self, tableName, **conditions):
        raise NotImplementedError

    def GetSequenceValue(self, sequenceName):
        raise NotImplementedError

    def GetSqlAndArgs(self, tableName, columnNames, **conditions):
        raise NotImplementedError

    def GetWhereClauseAndArgs(self, **conditions):
        raise NotImplementedError

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

    def CallFunction(self, functionName, returnType, *args):
        return self.cursor.callfunc(functionName, returnType, args)

    def CallProcedure(self, procedureName, *args):
        return self.cursor.callproc(procedureName, args)

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
        self.cursor.execute(sql, args)
        if rowFactory is not None:
            self.cursor.rowfactory = rowFactory
        return self.cursor.fetchall()


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
            while argName in existingArgs:
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

