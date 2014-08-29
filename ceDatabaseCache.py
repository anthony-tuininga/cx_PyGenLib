"""
Define classes and methods used for caching database results.
"""

import ceDatabase
import cx_Exceptions
import cx_Logging

class PathMetaClass(type):

    def __init__(cls, name, bases, classDict):
        super(PathMetaClass, cls).__init__(name, bases, classDict)
        if isinstance(cls.attrNames, str):
            cls.attrNames = cls.attrNames.split()
        if isinstance(cls.retrievalAttrNames, str):
            cls.retrievalAttrNames = cls.retrievalAttrNames.split()
        if isinstance(cls.stringRetrievalAttrNames, str):
            cls.stringRetrievalAttrNames = cls.stringRetrievalAttrNames.split()
        if "name" not in classDict:
            cls.name = cls.__name__
        if "subCacheAttrName" not in classDict:
            cls.subCacheAttrName = "rowsBy%s" % cls.name


class Path(object, metaclass = PathMetaClass):
    attrNames = []
    retrievalAttrNames = []
    stringRetrievalAttrNames = []
    subCacheAttrName = None
    cacheAttrName = None
    ignoreRowNotCached = False
    name = None

    def __init__(self, cache, subCache):
        self.rows = {}
        self.subCacheName = subCache.name
        self.rowClass = subCache.rowClass
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

    def GetRowsFromDataSource(self, cache, *args):
        conditions = dict(zip(self.retrievalAttrNames, args))
        return self.rowClass.GetRows(cache.dataSource, **conditions)

    def Load(self, cache, subCache, *args):
        rows = self.GetRowsFromDataSource(cache, *args)
        cachedValue = self._OnLoad(rows, *args)
        subCache.OnLoadRows(cache, rows)
        return cachedValue


class SingleRowPath(Path):

    def _OnLoad(self, rows, *args):
        if len(rows) == 0:
            raise cx_Exceptions.NoDataFound()
        elif len(rows) > 1:
            raise cx_Exceptions.TooManyRows(numRows = len(rows))
        return self._CacheValue(args, rows[0])

    def OnRowNotCached(self, args):
        return None


class MultipleRowPath(Path):
    ignoreRowNotCached = True

    def _OnLoad(self, rows, *args):
        return self._CacheValue(args, rows)

    def OnRowNotCached(self, args):
        return list()


class SubCacheMetaClass(type):

    def __init__(cls, name, bases, classDict):
        super(SubCacheMetaClass, cls).__init__(name, bases, classDict)
        if isinstance(cls.onLoadRowExtraDirectives, str):
            directives = cls.onLoadRowExtraDirectives.split()
            cls.onLoadRowExtraDirectives = []
            for i, directive in enumerate(directives):
                attrName = cls.rowClass.extraAttrNames[i]
                cacheMethodName, sourceAttrName = directive.split(":")
                info = (attrName, cacheMethodName, sourceAttrName)
                cls.onLoadRowExtraDirectives.append(info)
        cls.pathClasses = list(cls.pathClasses)
        cls.pathClassesByName = cls.pathClassesByName.copy()
        for value in classDict.values():
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


class SubCache(object, metaclass = SubCacheMetaClass):
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
        exec(code, dict(), temp)
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
        row = None
        for path in self.singleRowPaths:
            if path.ignoreRowNotCached:
                continue
            key = path.GetKeyValue(externalRow)
            row = path.rows.get(key)
            if row is not None:
                break
        if errorIfMissing and row is None:
            raise cx_Exceptions.NoDataFound()
        return row

    def Clear(self):
        self.allRows = []
        self.allRowsLoaded = False
        for path in self.paths:
            path.Clear()

    def GetAllRowsFromDataSource(self, cache):
        return self.rowClass.GetRows(cache.dataSource)

    def Load(self, cache, pathName, *args):
        if self.tracePathLoads:
            cx_Logging.Debug("%s: loading rows by path %s with args %s",
                    self.name, pathName, args)
        path = self.pathsByName[pathName]
        actualArgs = []
        for attrName, value in zip(path.retrievalAttrNames, args):
            if isinstance(value, ceDatabase.Row):
                value = getattr(value, attrName)
            actualArgs.append(value)
        actualArgs = tuple(actualArgs)
        if self.loadAllRowsOnFirstLoad:
            if not self.allRowsLoaded:
                self.LoadAllRows(cache)
            return path.GetCachedValue(actualArgs)
        return path.Load(cache, self, *actualArgs)

    def LoadAllRows(self, cache):
        if self.tracePathLoads:
            cx_Logging.Debug("%s: loading all rows", self.name)
        rows = self.GetAllRowsFromDataSource(cache)
        self.OnLoadRows(cache, rows)
        self.allRows = rows
        self.allRowsLoaded = True
        return self.allRows

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
        for value in classDict.values():
            if isinstance(value, type) and issubclass(value, SubCache):
                cls.subCacheClasses[value.name] = value
                value._GenerateCacheMethods(cls)


class Cache(object, metaclass = CacheMetaClass):
    subCacheClasses = {}

    def __init__(self, dataSource):
        self.dataSource = dataSource
        self.subCaches = []
        for cls in self.subCacheClasses.values():
            subCache = cls(self)
            self.subCaches.append(subCache)
            if cls.cacheAttrName is not None:
                setattr(self, cls.cacheAttrName, subCache)

    def Clear(self):
        for subCache in self.subCaches:
            subCache.Clear()

