"""Define classes which make parsing and writing of XML files a little
   simpler."""

from xml.sax import saxutils

class Writer(object):
    """Class which handles writing XML as output to a file."""

    def __init__(self, f, numSpaces = 2, encoding = None):
        self.__f = f
        self.__tags = []
        self.__numSpaces = numSpaces
        self.__SetIndentString()
        if encoding is not None:
            print('<?xml version="1.0" encoding="%s"?>' % encoding,
                    file = self.__f)
        else:
            print('<?xml version="1.0"?>', file = self.__f)

    def __SetIndentString(self):
        """Set the indent string for pretty printing the XML."""
        numSpaces = len(self.__tags) * self.__numSpaces
        self.__indentString = " " * numSpaces

    def _WriteTag(self, name, attrs, multiLineAttrs = False):
        """Write the tag with the given attributes."""
        self.__f.write(self.__indentString)
        self.__f.write("<%s" % name)
        for key, value in attrs.items():
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
        print("</%s>" % name, file = self.__f)

    def StartTag(self, _name, _multiLineAttrs = False, **_attrs):
        """Start the tag with any number of attributes."""
        self._WriteTag(_name, _attrs, _multiLineAttrs)
        print(">", file = self.__f)
        self.__tags.append(_name)
        self.__SetIndentString()

    def WriteTagNoValue(self, _name, **_attrs):
        """Write a tag which has no value (or any children)."""
        self._WriteTag(_name, _attrs)
        print("/>", file = self.__f)

    def WriteTagWithValue(self, _name, _value, **_attrs):
        """Write a tag which has a value (but no children)."""
        self._WriteTag(_name, _attrs)
        _value = saxutils.escape(str(_value)).replace("\r", "&#xD;")
        print(">%s</%s>" % (_value, _name), file = self.__f)

    def WriteTagWithValueRaw(self, _name, _value, **_attrs):
        """Write a tag which has a value (but no children)."""
        self._WriteTag(_name, _attrs)
        self.__f.write("><![CDATA[%s]]></%s>\n" % (_value, _name))

