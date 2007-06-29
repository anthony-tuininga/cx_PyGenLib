"""Module which provides routines for parsing using SimpleParse."""

import simpleparse.parser

class DispatchProcessor:
    """Handles the processing of parse trees. Each item in the tree consists
       of the tag, the start and ending position and a list of any child
       productions."""

    def DefaultDispatch(self, buffer, tag, start, end, childProductions):
        """Default method if no method is associated with the tag."""
        return tag, self.DispatchList(buffer, childProductions)

    def Dispatch(self, buffer, value):
        """Call the method associated with the tag."""
        tag, start, end, childProductions = value
        try:
            function = getattr(self, tag)
        except AttributeError:
            function = self.DefaultDispatch
        return function(buffer, tag, start, end, childProductions)

    def DispatchList(self, buffer, productions):
        """Call the method associated with the tag for each production in the
           list."""
        return [self.Dispatch(buffer, p) for p in productions]


class Parser:
    """Generates a parse tree from a grammar."""

    def __init__(self, grammar, processor = None):
        self.parser = simpleparse.parser.Parser(grammar)
        self.processor = processor

    def Parse(self, string, productionName):
        """Parse a string and return the unparsed string and the results tree
           of the successful parse. If the parse was unsuccessful, None is
           returned for the parse tree."""
        success, results, nextChar = self.parser.parse(string, productionName)
        if not success:
            results = None
        elif self.processor is not None:
            results = self.processor.DispatchList(string, results)
        return string[nextChar:], results

