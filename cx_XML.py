"""Define classes which make parsing and writing of XML files a little
   simpler."""

import cx_Exceptions
from xml.sax import saxutils

# make freeze work properly
from xml.sax.drivers2 import drv_pyexpat
from xml.parsers import expat


class Parser(saxutils.DefaultHandler):
    """Parser for an XML file, based on the SAX model."""

    def __Handlers(self, prefix):
        """Return a dictionary of handlers for the given prefix."""
        handlers = {}
        for name in self.__class__.__dict__:
          if name.startswith(prefix):
            handlers[name[len(prefix):]] = getattr(self, name)
        return handlers

    def endElement(self, name):
        """Called when an element has been completely parsed."""
        handler = self.__endElementHandlers.get(name)
        if handler is not None:
            handler()

    def startDocument(self):
        """Called when the document is first being processed."""
        self.__startElementHandlers = self.__Handlers("start_")
        self.__endElementHandlers = self.__Handlers("end_")
        self.__charactersHandlers = self.__Handlers("characters_")

    def startElement(self, name, attrs):
        """Called when an element is beginning to be parsed; note that the
           attributes are passed as a thin wrapper for a dictionary which
           contains unicode strings which cannot be used with keyword
           parameters."""
        handler = self.__startElementHandlers.get(name)
        if handler is None:
            raise cx_Exceptions.NoHandlerForStartTag(name = name)
        attrs = dict([(str(k), str(v)) for k, v in attrs.items()])
        handler(**attrs)
        self.__elementName = name

    def characters(self, data):
        """Called when element values are encountered."""
        handler = self.__charactersHandlers.get(self.__elementName)
        if handler is not None:
            handler(data)


class Writer(object):
    """Class which handles writing XML as output to a file."""

    def __init__(self, f, numSpaces = 2, encoding = None):
        self.__f = f
        self.__tags = []
        self.__numSpaces = numSpaces
        self.__SetIndentString()
        if encoding is not None:
            print >> self.__f, '<?xml version="1.0" encoding="%s"?>' % encoding
        else:
            print >> self.__f, '<?xml version="1.0"?>'

    def __SetIndentString(self):
        """Set the indent string for pretty printing the XML."""
        numSpaces = len(self.__tags) * self.__numSpaces
        self.__indentString = " " * numSpaces

    def _WriteTag(self, name, attrs, multiLineAttrs = False):
        """Write the tag with the given attributes."""
        self.__f.write(self.__indentString)
        self.__f.write("<%s" % name)
        for key, value in attrs.iteritems():
            if value is None:
                value = ""
            value = saxutils.quoteattr(str(value))
            if multiLineAttrs:
                self.__f.write("\n        %s=%s" % (key, value))
            else:
                self.__f.write(" %s=%s" % (key, value))

    def EndTag(self):
        """End the tag."""
        name = self.__tags.pop()
        self.__SetIndentString()
        self.__f.write(self.__indentString)
        print >> self.__f, "</%s>" % name

    def StartTag(self, _name, _multiLineAttrs = False, **_attrs):
        """Start the tag with any number of attributes."""
        self._WriteTag(_name, _attrs, _multiLineAttrs)
        print >> self.__f, ">"
        self.__tags.append(_name)
        self.__SetIndentString()

    def WriteTagNoValue(self, _name, **_attrs):
        """Write a tag which has no value (or any children)."""
        self._WriteTag(_name, _attrs)
        print >> self.__f, "/>"

    def WriteTagWithValue(self, _name, _value, **_attrs):
        """Write a tag which has a value (but no children)."""
        self._WriteTag(_name, _attrs)
        _value = saxutils.escape(str(_value)).replace("\r", "&#xD;")
        print >> self.__f, ">%s</%s>" % (_value, _name)

    def WriteTagWithValueRaw(self, _name, _value, **_attrs):
        """Write a tag which has a value (but no children)."""
        self._WriteTag(_name, _attrs)
        self.__f.write("><![CDATA[%s]]></%s>\n" % (_value, _name))

