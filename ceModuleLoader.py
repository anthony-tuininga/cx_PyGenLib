"""
Module loader which generates a module from a script but only for as long as is
needed by the use of a context variable.
"""

import imp
import sys
import types

class Loader(object):

    def __init__(self, name, scriptText, attrName = None,
            requiredClass = None, **scriptGlobals):
        self.name = name
        self.scriptText = scriptText
        self.scriptGlobals = scriptGlobals
        self.attrName = attrName
        self.requiredClass = requiredClass
        self.module = self.cls = None

    def __enter__(self):
        self.Load()
        return self

    def __exit__(self, excType, excValue, excTraceback):
        self.Unload()

    def Load(self):
        self.module = imp.new_module(self.name)
        sys.modules[self.name] = self.module
        self.module.__dict__.update(self.scriptGlobals)
        code = compile(self.scriptText, "<generated>", "exec")
        exec code in self.module.__dict__
        if self.attrName is not None:
            self.cls = self.module.__dict__.get(self.attrName)
            if self.cls is None:
                raise AttributeNotFound(name = self.attrName)
            if self.requiredClass is not None \
                    and not issubclass(self.cls, self.requiredClass):
                raise AttributeIsOfWrongClass(name = self.attrName,
                        requiredClass = self.requiredClass.__name__)
            return self.cls
        return self.module

    def Unload(self):
        if self.module is not None:
            del sys.modules[self.name]
        self.module = self.cls = None


class NamespaceLoader(object):

    def __init__(self, namespace):
        self.namespace = namespace
        self.cache = {}

    def __enter__(self):
        sys.meta_path.insert(0, self)
        return self

    def __exit__(self, excType, excValue, excTraceback):
        sys.meta_path.remove(self)
        if self.namespace in sys.modules:
            del sys.modules[self.namespace]

    def find_module(self, name, path):
        if name.startswith(self.namespace):
            if name not in self.cache:
                if name == self.namespace:
                    self.cache[name] = module = imp.new_module(self.namespace)
                    module.__path__ = []
                    sys.modules[self.namespace] = module
                else:
                    searchName = name[len(self.namespace) + 1:]
                    scriptText = self.get_script(searchName)
                    self.cache[name] = scriptText
            if self.cache[name] is not None:
                return self

    def load_module(self, name):
        moduleOrScript = self.cache[name]
        if isinstance(moduleOrScript, types.ModuleType):
            return moduleOrScript
        self.cache[name] = module = imp.new_module(name)
        code = compile(moduleOrScript, "<generated>", "exec")
        exec code in module.__dict__
        return module
