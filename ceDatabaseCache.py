"""
Define classes and methods used for caching database results.
"""

import ceDatabase
import cx_Exceptions
import cx_Logging
import functools

class PathMetaClass(type):

    def __init__(cls, name, bases, classDict):
        super(PathMetaClass, cls).__init__(name, bases, classDict)
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


class Path(object):
    __metaclass__ = PathMetaClass
    retrievalAttrNames = []
    retrievalAttrCacheMethodNames = []
    stringRetrievalAttrNames = []
    loadViaPathName = None
    subCacheAttrName = None
    cacheAttrName = None
    ignoreRowNotCached = False
    name = None

    def __init__(self, cache, subCache):
        self.rows = {}
        rowClass = subCache.rowClass
        if self.loadViaPathName is None:
            pos = len(self.retrievalAttrCacheMethodNames)
            attrNames = rowClass.attrNames[pos:]
        else:
            cls = subCache.pathClassesByName[self.loadViaPathName]
            attrNames = cls.retrievalAttrNames
        self.sql = "select %s from %s" % \
                (",".join(attrNames), rowClass.tableName)
        if self.retrievalAttrNames:
            whereClauses = cache._GetWhereClauses(self.retrievalAttrNames)
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
        for attrName, arg in zip(self.retrievalAttrNames, args):
            if not isinstance(arg, ceDatabase.Row):
                dbArgs.append(arg)
            else:
                dbArgs.append(getattr(arg, attrName))
        cursor = cache.connection.cursor()
        cursor.execute(self.sql, dbArgs)
        if self.loadViaPathName is None:
            if not self.retrievalAttrCacheMethodNames:
                method = rowFactory
            else:
                numArgs = len(self.retrievalAttrCacheMethodNames)
                partialArgs = args[:numArgs]
                method = functools.partial(rowFactory, *partialArgs)
            cursor.rowfactory = method
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
        cls.pathClasses = []
        cls.pathClassesByName = {}
        for value in classDict.itervalues():
            if isinstance(value, type) and issubclass(value, Path):
                cls.pathClasses.append(value)
                cls.pathClassesByName[value.name] = value
        if "name" not in classDict:
            cls.name = cls.__name__
        if cls.onLoadRowMethodName not in classDict \
                or cls.onRemoveRowMethodName not in classDict:
            onLoadRowMethodLines = []
            onRemoveRowMethodLines = []
            for directive in cls.onLoadRowExtraDirectives:
                line = "row.%s = cache.%s(row.%s)" % directive
                onLoadRowMethodLines.append(line)
            if cls.setExtraAttrValuesMethodName in classDict:
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
            if onLoadRowMethodLines \
                    and cls.onLoadRowMethodName not in classDict:
                cls._GenerateMethod(cls, cls.onLoadRowMethodName,
                        onLoadRowMethodLines, "cache", "row")
            if onRemoveRowMethodLines \
                    and cls.onRemoveRowMethodName not in classDict:
                cls._GenerateMethod(cls, cls.onRemoveRowMethodName,
                        onRemoveRowMethodLines, "cache", "row")


class SubCache(object):
    __metaclass__ = SubCacheMetaClass
    setExtraAttrValuesMethodName = "SetExtraAttrValues"
    onRemoveRowMethodName = "OnRemoveRow"
    onLoadRowMethodName = "OnLoadRow"
    onLoadRowExtraDirectives = []
    loadAllRowsOnFirstLoad = False
    allRowsMethodCacheAttrName = None
    cacheAttrName = None
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
        cx_Logging.Debug("GENERATED CODE:\n%s", codeString)
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

    def _FindRow(self, externalRow):
        path = self.singleRowPaths[0]
        key = path.GetKeyValue(externalRow)
        return path.rows.get(key)

    def Clear(self):
        self.allRows = []
        self.allRowsLoaded = False
        for path in self.paths:
            path.Clear()

    def Load(self, cache, pathName, *args):
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
        return path._OnLoad(rows, args)

    def LoadAllRows(self, cache):
        path = Path(cache, self)
        self.allRows = path._GetRows(cache, self.rowClass, ())
        self.OnLoadRows(cache, self.allRows)
        self.allRowsLoaded = True
        return self.allRows

    def OnLoadRows(self, cache, rows):
        if self.singleRowPaths or self.loadAllRowsOnFirstLoad:
            for row in rows:
                self.OnLoadRow(cache, row)

    def RemoveRow(self, cache, externalRow):
        row = self._FindRow(externalRow)
        self.OnRemoveRow(cache, row)
        if self.allRowsLoaded:
            self.allRows.remove(row)

    def UpdateRow(self, cache, externalRow, contextItem = None):
        row = self._FindRow(externalRow)
        if row is None:
            args = []
            for attrName in self.rowClass.attrNames:
                if hasattr(externalRow, attrName):
                    value = getattr(externalRow, attrName)
                else:
                    value = getattr(contextItem, attrName, None)
                args.append(value)
            row = self.rowClass(*args)
            self.OnLoadRow(cache, row)
            if self.allRowsLoaded:
                self.allRows.append(row)
        else:
            beforeKeyValues = []
            for path in self.singleRowPaths:
                beforeKeyValues.append((path, path.GetKeyValue(row)))
            for attrName in row.attrNames:
                if hasattr(externalRow, attrName):
                    value = getattr(externalRow, attrName)
                elif hasattr(contextItem, attrName):
                    value = getattr(contextItem, attrName)
                else:
                    continue
                setattr(row, attrName, value)
            for path, beforeKeyValue in beforeKeyValues:
                afterKeyValue = path.GetKeyValue(row)
                if afterKeyValue != beforeKeyValue:
                    del path.rows[beforeKeyValue]
                    path.rows[afterKeyValue] = row
            method = getattr(self, self.setExtraAttrValuesMethodName, None)
            if method is not None:
                method(cache, row)


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

