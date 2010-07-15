"""
Define classes and methods used for caching database results.
"""

import ceDatabase
import cx_Exceptions
import cx_Logging

class PathMetaClass(type):

    def __init__(cls, name, bases, classDict):
        super(PathMetaClass, cls).__init__(name, bases, classDict)
        if isinstance(cls.attrNames, basestring):
            cls.attrNames = cls.attrNames.split()
        if isinstance(cls.retrievalAttrNames, basestring):
            cls.retrievalAttrNames = cls.retrievalAttrNames.split()
        if isinstance(cls.retrievalAttrCacheMethodNames, basestring):
            cls.retrievalAttrCacheMethodNames = \
                    cls.retrievalAttrCacheMethodNames.split()
        if isinstance(cls.stringRetrievalAttrNames, basestring):
            cls.stringRetrievalAttrNames = cls.stringRetrievalAttrNames.split()
        if "name" not in classDict:
            cls.name = cls.__name__
        if "subCacheAttrName" not in classDict:
            cls.subCacheAttrName = "rowsBy%s" % cls.name
        if "dbRetrievalAttrNames" in classDict:
            cls.dbRetrievalAttrNames = cls.dbRetrievalAttrNames.split()
        else:
            cls.dbRetrievalAttrNames = cls.retrievalAttrNames


class Path(object):
    __metaclass__ = PathMetaClass
    attrNames = []
    retrievalAttrNames = []
    retrievalAttrCacheMethodNames = []
    stringRetrievalAttrNames = []
    loadViaPathName = None
    subCacheAttrName = None
    cacheAttrName = None
    rowFactoryCacheMethodName = None
    ignoreRowNotCached = False
    name = None

    def __init__(self, cache, subCache):
        self.rows = {}
        rowClass = subCache.rowClass
        if self.loadViaPathName is None:
            attrNames = self.attrNames or rowClass.attrNames
        else:
            cls = subCache.pathClassesByName[self.loadViaPathName]
            attrNames = cls.dbRetrievalAttrNames
        self.sql = "select %s from %s" % \
                (",".join(attrNames), rowClass.tableName)
        if self.dbRetrievalAttrNames:
            whereClauses = cache._GetWhereClauses(self.dbRetrievalAttrNames)
            self.sql += " where %s" % " and ".join(whereClauses)
        self.Clear()

    @classmethod
    def _GetProcessedAndKeyArgs(cls, prefix = ""):
        processedArgs = []
        for attrName in cls.retrievalAttrNames:
            if attrName in cls.stringRetrievalAttrNames:
                processedArgs.append("%s%s.upper()" % (prefix, attrName))
            else:
                processedArgs.append(prefix + attrName)
        if len(processedArgs) == 1:
            return processedArgs, processedArgs[0]
        return processedArgs, "(%s)" % ", ".join(processedArgs)

    def _CacheValue(self, args, value):
        if len(args) == 1:
            self.rows[args[0]] = value
        elif len(args) > 1:
            self.rows[args] = value
        return value

    def _DatabaseArgsToCacheArgs(self, cache, dbArgs):
        cacheArgs = []
        for i, value in enumerate(dbArgs):
            if i < len(self.retrievalAttrCacheMethodNames):
                method = getattr(cache, self.retrievalAttrCacheMethodNames[i])
                value = method(value)
            cacheArgs.append(value)
        return cacheArgs

    def _GetRows(self, cache, rowFactory, args):
        dbArgs = []
        for attrName, arg in zip(self.dbRetrievalAttrNames, args):
            if not isinstance(arg, ceDatabase.Row):
                dbArgs.append(arg)
            else:
                dbArgs.append(getattr(arg, attrName))
        cursor = cache.connection.cursor()
        cursor.execute(self.sql, dbArgs)
        if self.rowFactoryCacheMethodName is not None:
            cursor.rowfactory = getattr(cache, self.rowFactoryCacheMethodName)
        elif self.loadViaPathName is None:
            cursor.rowfactory = rowFactory
        return cursor.fetchall()

    def Clear(self):
        self.rows.clear()

    def GetCachedValue(self, args):
        if len(args) == 1:
            key, = args
        else:
            key = args
        try:
            return self.rows[key]
        except KeyError:
            if self.ignoreRowNotCached:
                return self.OnRowNotCached(args)
            raise cx_Exceptions.NoDataFound()

    def GetKeyValue(self, row):
        args = [getattr(row, n) for n in self.retrievalAttrNames]
        if len(args) == 1:
            return args[0]
        return tuple(args)


class SingleRowPath(Path):

    def _OnLoad(self, rows, args):
        if len(rows) == 0:
            raise cx_Exceptions.NoDataFound()
        elif len(rows) > 1:
            raise cx_Exceptions.TooManyRows(numRows = len(rows))
        return self._CacheValue(args, rows[0])

    def OnRowNotCached(self, args):
        return None


class MultipleRowPath(Path):
    ignoreRowNotCached = True

    def _OnLoad(self, rows, args):
        return self._CacheValue(args, rows)

    def OnRowNotCached(self, args):
        return list()


class SubCacheMetaClass(type):

    def __init__(cls, name, bases, classDict):
        super(SubCacheMetaClass, cls).__init__(name, bases, classDict)
        if isinstance(cls.onLoadRowExtraDirectives, basestring):
            directives = cls.onLoadRowExtraDirectives.split()
            cls.onLoadRowExtraDirectives = []
            for i, directive in enumerate(directives):
                attrName = cls.rowClass.extraAttrNames[i]
                cacheMethodName, sourceAttrName = directive.split(":")
                info = (attrName, cacheMethodName, sourceAttrName)
                cls.onLoadRowExtraDirectives.append(info)
        cls.pathClasses = list(cls.pathClasses)
        cls.pathClassesByName = cls.pathClassesByName.copy()
        for value in classDict.itervalues():
            if isinstance(value, type) and issubclass(value, Path):
                origValue = cls.pathClassesByName.get(value.name)
                cls.pathClassesByName[value.name] = value
                if origValue is not None:
                    cls.pathClasses.remove(origValue)
                cls.pathClasses.append(value)
        if "name" not in classDict:
            cls.name = cls.__name__
        if cls.regenerateMethods \
                or not hasattr(cls, cls.onLoadRowMethodName) \
                or not hasattr(cls, cls.onRemoveRowMethodName):
            onLoadRowMethodLines = []
            onRemoveRowMethodLines = []
            for directive in cls.onLoadRowExtraDirectives:
                line = "row.%s = cache.%s(row.%s)" % directive
                onLoadRowMethodLines.append(line)
            if hasattr(cls, cls.setExtraAttrValuesMethodName):
                line = "self.%s(cache, row)" % cls.setExtraAttrValuesMethodName
                onLoadRowMethodLines.append(line)
            for pathClass in cls.pathClasses:
                processedArgs, keyArgs = \
                        pathClass._GetProcessedAndKeyArgs("row.")
                if issubclass(pathClass, SingleRowPath):
                    line = "self.%s[%s] = row" % \
                            (pathClass.subCacheAttrName, keyArgs)
                    onLoadRowMethodLines.append(line)
                    line = "del self.%s[%s]" % \
                            (pathClass.subCacheAttrName, keyArgs)
                    onRemoveRowMethodLines.append(line)
                else:
                    if cls.loadAllRowsOnFirstLoad:
                        line = "self.%s.setdefault(%s, []).append(row)" % \
                                (pathClass.subCacheAttrName, keyArgs)
                        onLoadRowMethodLines.append(line)
                    line = "self.%s[%s].remove(row)" % \
                            (pathClass.subCacheAttrName, keyArgs)
                    onRemoveRowMethodLines.append(line)
            if onLoadRowMethodLines:
                if cls.regenerateMethods \
                        or not hasattr(cls, cls.onLoadRowMethodName):
                    cls._GenerateMethod(cls, cls.onLoadRowMethodName,
                            onLoadRowMethodLines, "cache", "row")
            if onRemoveRowMethodLines:
                if cls.regenerateMethods \
                        or not hasattr(cls, cls.onRemoveRowMethodName):
                    cls._GenerateMethod(cls, cls.onRemoveRowMethodName,
                            onRemoveRowMethodLines, "cache", "row")


class SubCache(object):
    __metaclass__ = SubCacheMetaClass
    setExtraAttrValuesMethodName = "SetExtraAttrValues"
    onRemoveRowMethodName = "OnRemoveRow"
    onLoadRowMethodName = "OnLoadRow"
    regenerateMethods = False
    onLoadRowExtraDirectives = []
    loadAllRowsOnFirstLoad = False
    allRowsMethodCacheAttrName = None
    pathClasses = []
    pathClassesByName = {}
    cacheAttrName = None
    tracePathLoads = True
    name = None

    def __init__(self, cache):
        self.paths = []
        self.singleRowPaths = []
        self.pathsByName = {}
        self.allRowsLoaded = False
        self.allRows = []
        for cls in self.pathClasses:
            path = cls(cache, self)
            self.paths.append(path)
            self.pathsByName[path.name] = path
            setattr(self, cls.subCacheAttrName, path.rows)
            if issubclass(cls, SingleRowPath):
                self.singleRowPaths.append(path)

    @classmethod
    def _GenerateMethod(cls, targetClass, methodName, methodLines, *args):
        actualArgs = ("self",) + args
        codeString = "def %s(%s):\n    %s" % \
                (methodName, ", ".join(actualArgs), "\n    ".join(methodLines))
        cx_Logging.Debug("%s: GENERATED CODE\n%s", cls.name, codeString)
        code = compile(codeString, "SubCacheGeneratedCode.py", "exec")
        temp = {}
        exec code in dict(), temp
        setattr(targetClass, methodName, temp[methodName])

    @classmethod
    def _GenerateCacheMethods(cls, cacheClass):
        if cls.allRowsMethodCacheAttrName is not None:
            methodLines = [
                    "if self.%s.allRowsLoaded:" % cls.cacheAttrName,
                    "    return self.%s.allRows" % cls.cacheAttrName,
                    "return self.%s.LoadAllRows(self)" % cls.cacheAttrName
            ]
            cls._GenerateMethod(cacheClass, cls.allRowsMethodCacheAttrName,
                    methodLines)
        for pathClass in cls.pathClasses:
            if pathClass.cacheAttrName is None:
                continue
            processedArgs, keyArgs = pathClass._GetProcessedAndKeyArgs()
            ref = "self.%s" % cls.cacheAttrName
            methodLines = [
                    "try:",
                    "    return %s.%s[%s]" % \
                            (ref, pathClass.subCacheAttrName, keyArgs),
                    "except KeyError:",
                    "    return %s.Load(self, %r, %s)" % \
                            (ref, pathClass.name, ", ".join(processedArgs))
            ]
            cls._GenerateMethod(cacheClass, pathClass.cacheAttrName,
                    methodLines, *pathClass.retrievalAttrNames)

    def _CopyAttrs(self, row, externalRow, contextItem):
        for attrName in row.attrNames + row.extraAttrNames:
            if hasattr(externalRow, attrName):
                value = getattr(externalRow, attrName)
            elif hasattr(contextItem, attrName):
                value = getattr(contextItem, attrName)
            else:
                continue
            setattr(row, attrName, value)

    def _FindRow(self, externalRow, errorIfMissing = False):
        path = self.singleRowPaths[0]
        key = path.GetKeyValue(externalRow)
        row = path.rows.get(key)
        if errorIfMissing and row is None:
            raise cx_Exceptions.NoDataFound()
        return row

    def Clear(self):
        self.allRows = []
        self.allRowsLoaded = False
        for path in self.paths:
            path.Clear()

    def Load(self, cache, pathName, *args):
        if self.tracePathLoads:
            cx_Logging.Debug("%s: loading rows by path %s with args %s",
                    self.name, pathName, args)
        path = self.pathsByName[pathName]
        if self.loadAllRowsOnFirstLoad:
            if not self.allRowsLoaded:
                self.LoadAllRows(cache)
            return path.GetCachedValue(args)
        rows = path._GetRows(cache, self.rowClass, args)
        if path.loadViaPathName is not None:
            loadViaPath = self.pathsByName[path.loadViaPathName]
            for row in rows:
                loadViaArgs = loadViaPath._DatabaseArgsToCacheArgs(cache, row)
                self.Load(cache, path.loadViaPathName, *loadViaArgs)
            return path.GetCachedValue(args)
        self.OnLoadRows(cache, rows)
        loadedRows = path._OnLoad(rows, args)
        if self.rowClass.sortByAttrNames \
                and isinstance(path, MultipleRowPath):
            cx_Logging.Debug("%s: sorting rows for path %s", self.name,
                    pathName)
            loadedRows.sort(key = self.rowClass.SortValue)
            if self.rowClass.sortReversed:
                loadedRows.reverse()
        return loadedRows

    def LoadAllRows(self, cache):
        cx_Logging.Debug("%s: loading all rows", self.name)
        path = Path(cache, self)
        rows = path._GetRows(cache, self.rowClass, ())
        if self.rowClass.sortByAttrNames:
            rows.sort(key = self.rowClass.SortValue)
            if self.rowClass.sortReversed:
                rows.reverse()
        self.OnLoadRows(cache, rows)
        self.allRows = rows
        self.allRowsLoaded = True
        return rows

    def OnLoadRows(self, cache, rows):
        method = getattr(self, self.onLoadRowMethodName, None)
        if method is not None:
            for row in rows:
                method(cache, row)

    def RemoveRow(self, cache, externalRow):
        row = self._FindRow(externalRow, errorIfMissing = True)
        cx_Logging.Debug("%s: removing row %s", self.name, row)
        self.OnRemoveRow(cache, row)
        if self.allRowsLoaded:
            self.allRows.remove(row)

    def UpdateRow(self, cache, externalRow, contextItem = None):
        row = self._FindRow(externalRow)
        if row is None:
            cx_Logging.Debug("%s: creating new row with source as %s",
                    self.name, externalRow)
            row = self.rowClass.New()
            self._CopyAttrs(row, externalRow, contextItem)
            self.OnLoadRow(cache, row)
            if not self.loadAllRowsOnFirstLoad:
                for path in self.paths:
                    if isinstance(path, MultipleRowPath):
                        key = path.GetKeyValue(row)
                        path.rows.setdefault(key, []).append(row)
            if self.allRowsLoaded:
                self.allRows.append(row)
        else:
            cx_Logging.Debug("%s: modifying row %s", self.name, row)
            beforeKeyValues = []
            for path in self.singleRowPaths:
                beforeKeyValues.append((path, path.GetKeyValue(row)))
            self._CopyAttrs(row, externalRow, contextItem)
            for path, beforeKeyValue in beforeKeyValues:
                afterKeyValue = path.GetKeyValue(row)
                if afterKeyValue != beforeKeyValue:
                    del path.rows[beforeKeyValue]
                    path.rows[afterKeyValue] = row
            method = getattr(self, self.setExtraAttrValuesMethodName, None)
            if method is not None:
                method(cache, row)


class XrefSubCache(SubCache):

    def AddRow(self, cache, key1, key2):
        cx_Logging.Debug("%s: adding xref between %s and %s", self.name, key1,
                key2)
        path1, path2 = self.paths
        if key1 in path1.rows:
            path1.rows[key1].append(key2)
        if key2 in path2.rows:
            path2.rows[key2].append(key1)

    def RemoveRow(self, cache, key1, key2):
        cx_Logging.Debug("%s: removing xref between %s and %s", self.name,
                key1, key2)
        path1, path2 = self.paths
        if key1 in path1.rows:
            path1.rows[key1].remove(key2)
        if key2 in path2.rows:
            path2.rows[key2].remove(key1)


class CacheMetaClass(type):

    def __init__(cls, name, bases, classDict):
        super(CacheMetaClass, cls).__init__(name, bases, classDict)
        cls.subCacheClasses = cls.subCacheClasses.copy()
        for value in classDict.itervalues():
            if isinstance(value, type) and issubclass(value, SubCache):
                cls.subCacheClasses[value.name] = value
                value._GenerateCacheMethods(cls)


class Cache(ceDatabase.WrappedConnection):
    __metaclass__ = CacheMetaClass
    subCacheClasses = {}

    def __init__(self, connection):
        super(Cache, self).__init__(connection)
        self.subCaches = []
        for cls in self.subCacheClasses.itervalues():
            subCache = cls(self)
            self.subCaches.append(subCache)
            if cls.cacheAttrName is not None:
                setattr(self, cls.cacheAttrName, subCache)

    def Clear(self):
        for subCache in self.subCaches:
            subCache.Clear()

