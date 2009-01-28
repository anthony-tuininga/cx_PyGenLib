"""
Define classes and methods used for caching database results.
"""

import ceDatabase
import cx_Exceptions
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

    def _GetRows(self, subCache, args):
        dbArgs = []
        for attrName, arg in zip(self.retrievalAttrNames, args):
            if not isinstance(arg, ceDatabase.Row):
                dbArgs.append(arg)
            else:
                dbArgs.append(getattr(arg, attrName))
        cursor = subCache.connection.cursor()
        cursor.execute(self.sql, dbArgs)
        if self.loadViaPathName is None:
            if not self.retrievalAttrCacheMethodNames:
                method = subCache.rowClass
            else:
                numArgs = len(self.retrievalAttrCacheMethodNames)
                partialArgs = args[:numArgs]
                method = functools.partial(subCache.rowClass, *partialArgs)
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

    def _OnLoad(self, rows, args):
        return self._CacheValue(args, rows)

    def OnRowNotCached(self, args):
        return list()


class SubCacheMetaClass(type):

    def __init__(cls, name, bases, classDict):
        super(SubCacheMetaClass, cls).__init__(name, bases, classDict)
        cls.pathClasses = []
        cls.pathClassesByName = {}
        for value in classDict.itervalues():
            if isinstance(value, type) and issubclass(value, Path):
                cls.pathClasses.append(value)
                cls.pathClassesByName[value.name] = value
        if "name" not in classDict:
            cls.name = cls.__name__
        loadRowMethodName = "OnLoadRow"
        if loadRowMethodName not in classDict:
            methodLines = []
            for pathClass in cls.pathClasses:
                if not issubclass(pathClass, SingleRowPath):
                    continue
                rawArgs = ["row.%s" % n for n in pathClass.retrievalAttrNames]
                if len(rawArgs) == 1:
                    args, = rawArgs
                else:
                    args = "(%s)" % ",".join(rawArgs)
                line = "self.%s[%s] = row" % (pathClass.subCacheAttrName, args)
                methodLines.append(line)
            if methodLines:
                cls._GenerateMethod(cls, loadRowMethodName, methodLines,
                        "cache", "row")


class SubCache(object):
    __metaclass__ = SubCacheMetaClass
    loadAllRowsOnFirstLoad = False
    allRowsMethodCacheAttrName = None
    cacheAttrName = None
    name = None

    def __init__(self, cache):
        self.connection = cache.connection
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
            processedArgs = []
            for attrName in pathClass.retrievalAttrNames:
                if attrName in pathClass.stringRetrievalAttrNames:
                    processedArgs.append("%s.upper()" % attrName)
                else:
                    processedArgs.append(attrName)
            if len(processedArgs) == 1:
                keyArgs = processedArgs[0]
            else:
                keyArgs = "(%s)" % ", ".join(processedArgs)
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

    def Clear(self):
        self.allRows = []
        self.allRowsLoaded = False
        for path in self.paths:
            path.Clear()

    def Load(self, cache, pathName, *args):
        path = self.pathsByName[pathName]
        if self.loadAllRowsOnFirstLoad:
            self.LoadAllRows(cache)
            return path.GetCachedValue(args)
        rows = path._GetRows(self, args)
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
        self.allRows = path._GetRows(self, ())
        self.OnLoadRows(cache, self.allRows)
        self.allRowsLoaded = True
        return self.allRows

    def OnLoadRows(self, cache, rows):
        if self.singleRowPaths:
            for row in rows:
                self.OnLoadRow(cache, row)


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

