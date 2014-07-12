"""Defines methods for managing tracing."""

import cx_Logging
import os
import sys
import time

STATIC_DOMAIN_ATTR = "CX_TRACING_DOMAIN"
DYNAMIC_DOMAIN_ATTR = "CX_TRACING_DYNAMIC_DOMAINS"


class TraceManager(object):
    """Manages tracing within domains."""

    def __init__(self):
        self.dynamicDomains = {}
        self.modules = {}

    def AddModule(self, module, domain = None):
        """Add a module to the list of modules to trace. If the domain is
           specified, then it will be added to the domain regardless of
           whether or not a domain is specified in the module itself; otherwise
           the module will be searched for the above domains and only added to
           the list if the correct attribute is specified."""
        if domain is None:
            domain = getattr(module, STATIC_DOMAIN_ATTR, None)
        if domain is not None:
            origDomain = self.modules.get(module.__name__)
            self.modules[module.__name__] = domain
            if origDomain is not None and domain != origDomain:
                cx_Logging.Warning("swapping domain for %s from %s to %s",
                        module.__name__, origDomain, domain)
            else:
                cx_Logging.Debug("adding %s to domain %s",
                        module.__name__, domain)
            dynamicDomains = getattr(module, DYNAMIC_DOMAIN_ATTR, [])
            for domain in dynamicDomains:
                self.dynamicDomains[domain] = None

    def GetDomains(self):
        """Return the distinct list of domain names for the modules currently
           managed."""
        domains = list(self.modules.values()) + list(self.dynamicDomains.keys())
        domains = list(dict.fromkeys(domains).keys())
        domains.sort()
        return domains

    def ScanImportedModules(self):
        """Scan all of the imported modules looking for tracing domains."""
        for module in sys.modules.values():
            self.AddModule(module)

    def StartTracing(self, domains, maxLength = 1000, traceLines = False):
        tracer = Tracer(self, domains, maxLength, traceLines)
        cx_Logging.Trace("starting tracing (traceLines=%r) of domains %r",
                traceLines, domains)
        if traceLines:
            sys.settrace(tracer)
        else:
            sys.setprofile(tracer)

    def StopTracing(self):
        cx_Logging.Trace("stopping tracing")
        sys.setprofile(None)
        sys.settrace(None)


class Tracer(object):
    """Class which actually performs the tracing."""

    def __init__(self, traceManager, domains, maxLength, traceLines):
        self.traceManager = traceManager
        self.domains = dict.fromkeys(domains)
        self.maxLength = maxLength
        self.traceLines = traceLines
        self.files = {}
        self.traceTimeStack = []
        self.localVarsStack = []
        self.prefix = ""

    def __call__(self, frame, event, arg):
        """Write a trace message for all events."""
        fileName = frame.f_code.co_filename
        trace = self.files.get(fileName)
        if trace is None:
            trace = self.files[fileName] = self.__ShouldTrace(fileName)
        if trace:
            self.dispatch[event](self, frame, arg)
            return self

    def __FormatValue(self, frame, name, prefix = ""):
        """Return the formatted value of the value. Names starting with an
           underscore that are not Python "magic" attributes are shown as
           <hidden>."""
        if name.startswith("_") and not name.startswith("__"):
            value = "<hidden>"
        else:
            value = self.__ValueForOutput(frame.f_locals[name])
        return "%s%s = %s" % (prefix, name, value)

    def __ShouldTrace(self, fileName):
        cx_Logging.Debug("should trace code from file %s?", fileName)
        fileName, ext = os.path.splitext(fileName)
        if os.path.isabs(fileName):
            for path in sys.path:
                if fileName.startswith(path + os.sep):
                    fileName = fileName[len(path) + 1:]
        moduleName = fileName.split(os.sep)[0]
        domain = self.traceManager.modules.get(moduleName)
        trace = (domain in self.domains)
        cx_Logging.Debug("  tracing for module %s is %s", moduleName, trace)
        return trace

    def __TraceCall(self, frame, unusedArg):
        code = frame.f_code
        cx_Logging.Trace('%sFile "%s", line %d', self.prefix, code.co_filename,
                frame.f_lineno)
        args = [self.__FormatValue(frame, n) \
                for n in code.co_varnames[:code.co_argcount]]
        if code.co_flags & 4:
            args.append(self.__FormatValue(frame,
                    code.co_varnames[len(args)], "*"))
        if code.co_flags & 8:
            args.append(self.__FormatValue(frame,
                    code.co_varnames[len(args)], "**"))
        cx_Logging.Trace("%s%s(%s)", self.prefix, code.co_name,
                ", ".join(args))
        self.traceTimeStack.append(time.time())
        self.prefix = "    " * len(self.traceTimeStack)

    def __TraceCException(self, frame, exceptionInfo):
        self.__TraceReturn(frame, "exception")

    def __TraceException(self, frame, exceptionInfo):
        returnValue = "exception %s: %r" % (exceptionInfo[:2])
        self.__TraceReturn(frame, returnValue)

    def __TraceLine(self, frame, unusedArg):
        code = frame.f_code
        cx_Logging.Trace('%sFile "%s", line %d', self.prefix, code.co_filename,
                frame.f_lineno)

    def __TraceReturn(self, frame, returnValue):
        if self.traceTimeStack:
            elapsedTime = time.time() - self.traceTimeStack.pop()
        else:
            elapsedTime = 0
        self.prefix = "    " * len(self.traceTimeStack)
        code = frame.f_code
        cx_Logging.Trace('%sFile "%s", line %d', self.prefix, code.co_filename,
                frame.f_lineno)
        returnValue = self.__ValueForOutput(returnValue)
        cx_Logging.Trace("%s%s() returning %s in %.3f seconds", self.prefix,
                code.co_name, returnValue, elapsedTime)

    def __ValueForOutput(self, value):
        try:
            value = repr(value)
        except:
            value = "cannot repr object of type %s" % type(value)
        if len(value) > self.maxLength:
            value = value[:self.maxLength] + "..."
        return value

    dispatch = {
            "c_call" : __TraceCall,
            "call" : __TraceCall,
            "c_exception" : __TraceCException,
            "exception" : __TraceException,
            "line" : __TraceLine,
            "c_return" : __TraceReturn,
            "return" : __TraceReturn
    }

