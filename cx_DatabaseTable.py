"""Define class that supports executing queries against database tables and
   returning Python objects with attributes corresponding to the names of the
   columns."""

import cx_Exceptions

class Table(object):

    def __init__(self, owner, name, *columnNames, **derivedAttrs):
        self.owner = owner
        self.name = name
        self.columnNames = columnNames
        self.derivedAttrNames = list(derivedAttrs.keys())
        self.derivedDefaults = [derivedAttrs[n] for n in self.derivedAttrNames]
        self.sql = "select\n  %s\nfrom %s.%s" % \
                (",\n  ".join(columnNames), owner, name)
        rowClassName = "%s.%s.Row" % (owner, name)
        slots = [s[0].lower() + s[1:] \
                for s in list(columnNames) + self.derivedAttrNames]
        self.rowClass = type(rowClassName, (Row,),
                dict(__slots__ = slots))

    def _SortRep(self, row, name):
        """Return the representation to use for sorting."""
        value = getattr(row, name)
        if isinstance(value, str):
            return value.lower()
        return value

    def FetchRow(self, cursor, **args):
        """Fetch the row from the database and return it as an instance of
           the requested row. An exception will be raised if no rows are
           returned or more than one row is returned."""
        rows = self.FetchRows(cursor, **args)
        if len(rows) > 1:
            raise cx_Exceptions.TooManyRows(numRows = len(rows))
        if not rows:
            raise cx_Exceptions.NoDataFound()
        return rows[0]

    def FetchRows(self, cursor, **args):
        """Fetch rows from the database and return them as instances of the
           requested row."""
        sql = self.sql
        if args:
            whereClauses = []
            actualArgs = {}
            for name, value in args.items():
                if value is None:
                    whereClauses.append("%s is null" % name)
                elif isinstance(value, str) and "%" in value:
                    whereClauses.append("%s like :%s" % (name, name))
                    actualArgs[name] = value
                elif isinstance(value, (list, tuple)):
                    inClause = ", ".join([str(v) for v in value])
                    whereClauses.append("%s in (%s)" % (name, inClause))
                else:
                    whereClauses.append("%s = :%s" % (name, name))
                    actualArgs[name] = value
            args = actualArgs
            sql += "\nwhere %s" % "\n  and ".join(whereClauses)
        cursor.execute(sql, **args)
        derivedDefaults = tuple(self.derivedDefaults)
        return [self.rowClass(*r + derivedDefaults) for r in cursor]

    def FetchRowsSorted(self, cursor, *sortedBy, **args):
        """Fetch rows from the database and return them as instances of the
           requested row, sorted by the specified set of attributes."""
        sortList = []
        for row in self.FetchRows(cursor, **args):
            sortKey = tuple([self._SortRep(row, n) for n in sortedBy])
            sortList.append((sortKey, row))
        sortList.sort()
        return [r for sk, r in sortList]

    def NewRow(self):
        """Return a row for the table with all values set to null."""
        defaults = [None] * len(self.columnNames) + self.derivedDefaults
        return self.rowClass(*defaults)


class Row(object):

    __slots__ = []
    pkAttrNames = []

    def __init__(self, *args):
        if len(self.__slots__) != len(args):
            raise TypeError("%s() takes exactly %d arguments (%d given)" % \
                    (self.__class__.__name__, len(self.__slots__), len(args)))
        for name, value in zip(self.__slots__, args):
            setattr(self, name, value)

    def __repr__(self):
        attrs = ["%s=%r" % (n, getattr(self, n)) for n in self.__slots__]
        return "<%s: %s>" % (self.__class__.__name__, ", ".join(attrs))

    __str__ = __repr__

    def Copy(self):
        """Create a new row of the specified class as an exact copy."""
        args = [getattr(self, n) for n in self.__slots__]
        return self.__class__(*args)

    def GetDatabaseArgs(self):
        """Return the arguments suitable for accessing or deleting the row
           from the database."""
        return dict([(n, getattr(self, n)) for n in self.pkAttrNames])

    def GetPrimaryKeyTuple(self):
        """Return a tuple consisting of the attributes in the primary key."""
        return tuple([getattr(self, n) for n in self.pkAttrNames])

    def GetIdentifier(self):
        """Return the identifier of the row which is defined as the first
           attribute defined in the slots."""
        return getattr(self, self.__slots__[0])

    def SetIdentifier(self, value):
        """Set the identifier of the row which is defined as the first
           attribute defined in the slots."""
        setattr(self, self.__slots__[0], value)

