"""Classes for handling .ini files.

You can use this module to read, manipulate, or create .ini-style files.
Typically, you would instantiate an IniFile object based on an existing .ini
file.  Then you could query and change items, and eventually write the changes
to disk.  For example:

  import cx_IniFile

  ini = cx_IniFile.IniFile(r"C:\MyApp\MyApp.ini")
  try:
    curDB = ini.GetValue("Settings", "CurrentDB")
  except ValueError:
    curDB = "dev"
    ini.SetValue("Settings", "CurrentDB", curDB)
  #
  # more code, presumably using curDB
  #
  ini.SetValue("Settings", "PreviousDB", curDB)
  if ini.isModified:
      ini.Write()

The file you specify does not have to exist, but note that the internal data
structures will initially be empty in this case.  You can also instantiate an
object with no file name at all, but you will have to specify a name of some
sort (by assigning a value to the File object's .fileName property) before you
can Write() it to disk.

When you call SetValue() passing in a non-existent key, the key will be
created in the specified section.  If the section you specify does not exist
then it will be created too, and the new key will be placed inside it.

If you try to perform a GetValue() on a key that does not exist in the given
section, a ValueError exception is raised.  You can use the HasValue()
function to check for the existence of a key in a section, or catch the
exception as demonstrated in the example above.  Note that both the section
and key name are not case sensitive in calls to GetValue() or HasValue().
Although the original case of these two items specified in SetValue() is
preserved internally, when searching for them case is not respected.

A section can have a header comment.  This comment can be changed with the
SetSection() function.

You can check whether or not the internal data structures have been changed
since the file was loaded by looking at the isModified property.  Note that
isModified is a read-only property, and cannot be set directly.

If you need to find out more about the internal data structures you can use
the following properties:

IniFile object
  comments - a list of all comments that appear before the first section.
  fileName - the fully qualified path name of the .ini file.
  isModified - whether anything anywhere has changed (read-only).
  sections - a list of all the Section objects in this file.

Section objects
  comment - the optional comment for this section.
  isModified - if this section or any key in it has changed (read-only).
  keys - a list of all the Key objects in this section.
  name - the name of this section.

Key objects
  comment - the optional comment for this key*.
  isModified - if this key's value or comment has changed (read-only).
  name - the name of this key (can be empty*).
  value - the value of this key (can be empty*)

* Note that Key objects come in two varieties: the standard key/value pair
with optional comment, or a "comments-only" version whose key and value are
blank.  This latter type is used to store line comments within the section,
and can be added to a section with either SetValue() or AddComment().

"""


import os
import cx_Utils


COMMENT_CHARS = ";#"

class IniFile(object):
    """Class that represents a .ini file."""

    def __init__(self, fileName=None):
        self.__comments = []
        self.__fileName = ""
        self.__sections = []
        self.commentChars = COMMENT_CHARS
        self.fileName = fileName

    def __str__(self):
        contents = ""
        for line in self.comments:
            if line[0] not in COMMENT_CHARS:
                line = COMMENT_CHARS[0] + line
            contents += line + "\n"
        for section in self.sections:
            if contents:
                contents += "\n"
            contents += str(section)
        return contents

    def __GetCommentChars(self):
        return self.__commentChars

    def __GetComments(self):
        return self.__comments

    def __GetFileName(self):
        return self.__fileName

    def __GetIsModified(self):
        isModified = self.__isModified
        if not isModified:
            for section in self.sections:
                isModified = section.isModified
                if isModified:
                    break
        return isModified

    def __GetSections(self):
        return self.__sections

    def __Parse(self):
        """Load the file into the internal data structures.
        
           Note that key/value lines are allowed to have a comment, as in:
                SomeKey=SomeValue   ; Here is a comment
           However, ambiguity is introduced when the value itself contains
           a comment character, as in:
                LastDB=dsn=prod;uid=admin;pwd=topsekrit   ; Another comment
           This ambiguity is resolved by examining the character just
           before the comment character.  If it is whitespace then we
           assume that the comment character indicates an actual comment."""
        self.sections = []
        self.comments = []
        lines = [line.strip() for line in open(self.fileName).readlines() \
                if line.strip()]
        section = ""
        for line in lines:
            key = None
            value = None
            comment = None
            if line.startswith("["):
                pos = line.find("]")
                if pos > 0:
                    # This is the start of a new section.
                    section = line[1:pos]
                    comment = line[pos + 1:].strip()
                    self._AddSection(section, comment)
                    continue
            if section:
                if line[0:1] in COMMENT_CHARS:
                    pos = -1
                else:
                    # The existence of "=" indicates a key/value pair.
                    pos = line.find("=")
                if pos >= 0:
                    # The key is everything up to the equals sign.
                    key = line[:pos].strip()
                    line = line[pos + 1:].strip()
                    # Extract any comment that might exist.
                    for char in COMMENT_CHARS:
                        pos = line.find(char)
                        if pos == 0 or pos > 0 and line[pos - 1].isspace():
                            comment = line[pos:]
                            line = line[:pos].strip()
                            break
                    # The value is whatever is left over.
                    value = line
                else:
                    comment = line
                self.SetValue(section, key, value, comment)
            else:
                # No sections defined yet, treat the line as a file comment.
                self.comments.append(line)
        self.__SetIsModified(False)

    def __SetCommentChars(self, string):
        global COMMENT_CHARS
        if string is not None and self.__commentChars != string:
            self.__commentChars = string
            COMMENT_CHARS = string
            self.__SetIsModified(True)

    def __SetComments(self, commentList):
        if type(commentList) != type([]):
            commentList = [commentList]
        if self.__comments != commentList:
            self.__comments = commentList
            self.__SetIsModified(True)

    def __SetFileName(self, fileName):
        if self.__fileName != fileName:
            self.__fileName = fileName
            self.__SetIsModified(True)
        # If an existing file is assigned, it is parsed even if it is the same
        # file as what was there before.  This resets all the internal data
        # structures, silently overwriting any changes that were made.
        if fileName:
            if os.path.isfile(fileName):
                self.__Parse()

    def __SetIsModified(self, isModified):
        self.__isModified = isModified
        for section in self.sections:
            section.isModified = isModified

    def __SetSections(self, sectionList):
        if type(sectionList) != type([]):
            sectionList = [sectionList]
        if sectionList != self.__sections:
            for section in sectionList:
                if not isinstance(section, Section):
                    message = "%s must be a Section object." % section
                    raise ValueError(message)
            self.__sections = sectionList
            self.__SetIsModified(True)

    comments = property(__GetComments, __SetComments, None,
            "List of comments not associated with any section.")

    fileName = property(__GetFileName, __SetFileName, None,
            "The fully qualified name of the .ini file")

    # Note: although __SetIsModified() has been declared, it is used
    # internally only and thus isn't mentioned on the following line.
    isModified = property(__GetIsModified, None, None,
            "Whether or not any changes have occurred.")

    sections = property(__GetSections, __SetSections, None,
            "List of Section objects.")

    def _AddSection(self, name, comment=None):
        """Add a new section."""
        section = Section(name, comment)
        self.sections.append(section)
        self.__isModified = True

    def AddComment(self, section, comment):
        """Adds the given line comment to the section."""
        self.SetValue(section, comment=comment)

    def GetSection(self, name):
        """Return the given section object or raise an exception."""
        lowercaseName = name.lower()
        found = False
        for section in self.sections:
            if section.name.lower() == lowercaseName:
                found = True
                break
        if not found:
            raise ValueError("Unknown section: %s" % name)
        return section

    def GetValue(self, section, key):
        """Return the given section/key's value.

        If the given section or key doesn't exist a ValueError exception is
        raised.  You can use HasValue() to determine if a given key exists
        in a section before calling this function.

        """
        return self.GetSection(section)._GetValue(key)

    def GetValueWithDefault(self, section, key, defaultValue = None):
        """Return the given section/key's value if found or the default value
           if not found."""
        try:
            return self.GetValue(section, key)
        except ValueError:
            return defaultValue

    def HasSection(self, name):
        """Return whether or not the given section exists."""
        lowercaseName = name.lower()
        found = False
        for section in self.sections:
            if section.name.lower() == lowercaseName:
                found = True
                break
        return found

    def HasValue(self, section, key):
        """Return whether or not the given section has the given key."""
        exists = self.HasSection(section)
        if exists:
            exists = self.GetSection(section)._HasKey(key)
        return exists

    def Read(self, fileName=None):
        """Load the given file.

        Unlike simply assigning the .fileName property, this method insists
        that the file must actually exist, or an error is raised.
        """
        if fileName is None:
            raise ValueError("No file name specified, try Read(<FILENAME>)")
        if not os.path.isfile(fileName):
            raise ValueError("Invalid file name: %s" % fileName)
        self.fileName = fileName

    def SetSection(self, section, comment=None):
        """Change a section's header comment, or create it if necessary."""
        if self.HasSection(section):
            if comment is not None:
                self.GetSection(section).comment = comment
        else:
            self._AddSection(section, comment)

    def SetValue(self, section, key=None, value=None, comment=None):
        """Set the given section/key's value and comment (if any).

        An empty section results in comment being applied as a file-wide
        comment before the first section.
        A non-empty section and an empty key results in comment being inserted
        as a section comment.

        """
        if section:
            if not self.HasSection(section):
                self._AddSection(section)
            if key or comment:
                self.GetSection(section)._SetValue(key, value, comment)
        else:
            # Ignore key and value, this is a file-wide comment.
            if comment is not None:
                self.comments.append(comment)
                self.__isModified = True

    def Write(self, fileName=None):
        """Overwrite the file with the current data structures."""
        f = fileName or self.fileName
        if f is None:
            raise ValueError("No file name specified, try Write(<FILENAME>)")
        cx_Utils.WriteFile(f, str(self))
        if fileName:
            self.fileName = fileName


class Key(object):
    """Class that represents a key/value item within a section."""

    def __init__(self, name=None, value=None, comment=None):
        self.__comment = comment
        self.__name = name
        self.__value = value
        self.isModified = False

    def __str__(self):
        if self.name:
            if self.comment:
                comment = self.comment
                if comment[0] not in COMMENT_CHARS:
                    comment = COMMENT_CHARS[0] + comment
                contents = "%s=%s   %s" % (self.name, self.value, comment)
            else:
                contents = "%s=%s" % (self.name, self.value)
        elif self.comment:
            contents = self.comment
        else:
            # This should never happen.
            contents = ""
        return contents

    def __GetComment(self):
        return self.__comment

    def __GetIsModified(self):
        return self.__isModified

    def __GetName(self):
        return self.__name

    def __GetValue(self):
        return self.__value

    def __SetComment(self, comment):
        if comment is not None and self.__comment != comment:
            self.__comment = comment
            self.isModified = True

    def __SetIsModified(self, isModified):
        self.__isModified = isModified

    def __SetName(self, name):
        if name is not None and self.__name != name:
            self.__name = name
            self.isModified = True

    def __SetValue(self, value):
        if value is not None and self.__value != value:
            self.__value = value
            self.isModified = True

    comment = property(__GetComment, __SetComment, None,
            "Optional comment for this key.")

    isModified = property(__GetIsModified, __SetIsModified, None,
            "Whether or not this section has changed.")

    name = property(__GetName, __SetName, None,
            "The name of this key.")

    value = property(__GetValue, __SetValue, None,
            "The value of this key.")


class Section(object):
    """Class that represents a section of a .ini file."""

    def __init__(self, name, comment=None):
        self.__comment = comment
        self.__allkeys = []
        self.__keys = []
        self.__name = name
        self.isModified = False

    def __str__(self):
        comment = self.comment
        if comment:
            if comment[0] not in COMMENT_CHARS:
                comment = COMMENT_CHARS[0] + comment
            contents = "[%s]   %s\n" % (self.name, comment)
        else:
            contents = "[%s]\n" % self.name
        for key in self.allkeys:
            contents += str(key) + "\n"
        return contents

    def __GetAllKeys(self):
        return self.__allkeys

    def __GetComment(self):
        return self.__comment

    def __GetIsModified(self):
        isModified = self.__isModified
        if not isModified:
            for key in self.allkeys:
                isModified = key.isModified
                if isModified:
                    break
        return isModified

    def __GetKeys(self):
        return [key for key in self.allkeys if key.name]

    def __GetName(self):
        return self.__name

    def __SetAllKeys(self, keyList):
        if type(keyList) != type([]):
            keyList = [keyList]
        if self.__allkeys != keyList:
            for key in keyList:
                if not isinstance(key, Key):
                    raise ValueError("%s must be a Key object." % key)
            self.__allkeys = keyList
            self.isModified = True

    def __SetComment(self, comment):
        if comment is not None and self.__comment != comment:
            self.__comment = comment
            self.isModified = True

    def __SetIsModified(self, isModified):
        self.__isModified = isModified
        for key in self.keys:
            key.isModified = isModified

    def __SetKeys(self, keyList):
        self.allkeys = keyList

    def __SetName(self, name):
        if name is not None and self.__name != name:
            self.__name = name
            self.isModified = True

    allkeys = property(__GetAllKeys, __SetAllKeys, None,
            "List of all Key objects in this section.")

    comment = property(__GetComment, __SetComment, None,
            "Section header comment.")

    isModified = property(__GetIsModified, __SetIsModified, None,
            "Whether or not this section or any of its keys has changed.")

    keys = property(__GetKeys, __SetKeys, None,
            "List of all non-comment Key objects in this section.")

    name = property(__GetName, __SetName, None,
            "The name of this section.")

    def _AddKey(self, name, value, comment=None):
        """Add the given key/value with optional comment to this section."""
        key = Key(name, value, comment)
        self.allkeys.append(key)
        self.isModified = True

    def _GetKey(self, name):
        """Return a Key object or raise an exception if it does not exist."""
        lowercaseName = name.lower()
        found = False
        for key in self.allkeys:
            if key.name.lower() == lowercaseName:
                found = True
                break
        if not found:
            message = "Key %s not found in section %s" % (name, self.name)
            raise ValueError(message)
        return key

    def _GetValue(self, name):
        """Return the given key's value."""
        return self._GetKey(name).value

    def _HasKey(self, name):
        """Return whether or not the given key exists in this section."""
        lowercaseName = name.lower()
        found = False
        for key in self.allkeys:
            if key.name.lower() == lowercaseName:
                found = True
                break
        return found

    def _SetValue(self, name, value, comment=None):
        """Set key's value and comment, creating it if necessary."""
        if name:
            if self._HasKey(name):
                key = self._GetKey(name)
                if key.value != value:
                    key.value = value
                    self.isModified = True
                if key.comment != comment:
                    key.comment = comment
                    self.isModified = True
            else:
                self._AddKey(name, value, comment)
                self.isModified = True
        else:
            # No key specified, assume it's a section comment.
            self._AddKey("", "", comment)
            self.isModified = True

