"""Defines a number of utility functions."""

import glob
import os
import sys

if sys.platform == "win32":
    import _winreg

def ExecuteOSCommands(*commands):
    """Execute OS commands, raising an error if any return errors."""
    for command in commands:
        if os.system(command) != 0:
            raise "Execution of command %s failed." % command

def FilesInDirectory(*entries):
    """Return a list of all of the files found in the directory. If the entry
       is actually a file, it is returned instead."""
    files = []
    while entries:
        newEntries = []
        for entry in entries:
            if os.path.isdir(entry):
                newEntries += [os.path.join(entry, f) \
                        for f in os.listdir(entry)]
            else:
                files.append(entry)
        entries = newEntries
    return files

def FilesHierarchy(rootDir, namesToIgnore=[]):
    """Return a list of relative file names starting at rootDir.

    The returned list of file names will contain relative path
    information; that is, the portion of their full path less rootDir.

    Files or directories that appear in namesToIgnore are ignored.
    Note that this comparison is not case sensitive: if "foo.txt" is
    specified then "FOO.TXT" will not appear in the final result.  As
    well, if "bar" is specified then any files in the directory "Bar"
    will not appear in the final result.

    """
    def Visit(args, dirname, names):
        """Append all legitimate files in dirname to the files list."""
        rootDir, files, ignored = args
        for name in names[:]:
            if name.lower() in ignored:
                names.remove(name)
            else:
                file = os.path.join(dirname, name)
                if os.path.isfile(file):
                    files.append(PathRemainder(rootDir, file))

    rootDir = os.path.normpath(rootDir)
    files = []
    ignored = [name.lower() for name in namesToIgnore]
    os.path.walk(rootDir, Visit, (rootDir, files, ignored))

    return files

def GetRegistryAppPath(key):
    """Return the given key's app path, or None.

    Scan the registry to figure out exactly where on the hard drive the given
    executable is located, and return the fully qualified path to that file.

    By default the executable's "Default" key value is returned, but it is
    possible to get a value other than the default one by appending it to the
    end of key separated by a backslash character.  For example:
      GetRegistryAppPath("MyApp.exe") returns the default value
      GetRegistryAppPath(r"MyApp.exe\Path") returns the value for subkey Path

    Note that the registry is not case sensitive; the following two examples
    return the same result:
        GetRegistryAppPath("MyApp.EXE")
        GetRegistryAppPath("myapp.exe")

    Note also that although registry entries are stored in Unicode form, this
    function returns a standard Python string.

    """

    result = None
    valueName = None

    if not key: return result

    tuple = key.split("\\", 1)
    exeName = tuple[0]
    if len(tuple) > 1:
        valueName = tuple[1]

    subKey = r"Software\Microsoft\Windows\CurrentVersion\App Paths\%s" % \
            exeName

    try:
        hkey = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, subKey)
    except WindowsError, (errno, strerr):
        if errno == 2:    # Unable to find file
            print r"Registry key not found: HKLM\%s" % subKey
            result = ""
        else:
            raise
    else:
        # Note: Registry strings are stored in Unicode format, so they must be
        # converted to regular strings for use in Python.
        result = str(_winreg.QueryValueEx(hkey, valueName)[0])

    return result

def InlineIf(expr, trueValue, falseValue = None):
    """Method used for performing a simple if clause in an expression."""
    if expr:
        return trueValue
    else:
        return falseValue

def PathRemainder(path1, path2, caseSensitive=False, ignoreDriveLetters=True):
    """Return the right-hand part of path2 that is not in path1.

    The matching directories are removed, one by one, starting from the left
    side of the two paths.  Once a mismatch is encountered, or either path
    runs out, the remainder of path2 is returned.  It is possible for an empty
    string to be returned if path2 is equal to path1, or if path2 is shorter
    than path1.

    """
    if ignoreDriveLetters:
        p1 = os.path.splitdrive(path1)[1]
        p2 = os.path.splitdrive(path2)[1]
    else:
        p1 = path1
        p2 = path2

    while p1 and p2:
        head1, tail1 = SplitFirst(p1)
        head2, tail2 = SplitFirst(p2)
        if not caseSensitive:
            head1 = head1.lower()
            head2 = head2.lower()
        if head1 == head2:
            p1 = tail1
            p2 = tail2
        else:
            break
    return p2

def PerformDiff(sourceDir, targetDir):
    """Perform a diff between two directories and return the results as a set
       of three lists: new, modified and removed."""
    newFiles = []
    modifiedFiles = []
    removedFiles = []
    command = 'diff --recursive --brief "%s" "%s"' % (sourceDir, targetDir)
    pipe = os.popen(command)
    for line in pipe.readlines():
        if line.startswith("Only"):
            fileOrDir = os.path.join(*line[8:-1].split(": "))
            if fileOrDir.startswith(sourceDir):
                removedFiles += FilesInDirectory(fileOrDir)
            else:
                newFiles += FilesInDirectory(fileOrDir)
        else:
            modifiedFiles.append(line[line.find(" and "):][5:-8])
    status = pipe.close()
    if status is not None:
        if not newFiles and not removedFiles and not modifiedFiles:
            raise "Command %s failed." % command
    return (newFiles, modifiedFiles, removedFiles)

def SplitFirst(path):
    """Return a tuple containing the first directory and the rest of path.

    This is similar to os.path.split(), except that in this function the
    (head, tail) tuple has the first directory in head, while the remainder of
    path is in tail.  As with os.path.split(), os.path.join(head, tail) will
    produce path.

    """
    pos = path.find(os.sep)
    if pos == -1:
        # No separator found, assume path is a directory.
        head = path
        tail = ""
    else:
        head = path[:pos]
        tail = path[pos + len(os.sep):]
    return (head, tail)

def Touch(fileName):
    """Update the modification date of the file, or create it if necessary."""
    if os.path.exists(fileName):
        os.utime(fileName, None)
    else:
        file(fileName, "w")

def TransformText(text, method, openDelim = "{", closeDelim = "}"):
    """Transform the text containing the given delimiters and return the
       transformed value. The method will be called whenever text is found
       between the given delimiters but not if the text contains another
       opening delimiter. Whatever is returned by the method will replace the
       text between the delimiters and the delimiters as well."""
    lastPos = 0
    results = []
    while True:
        startPos = text.find(openDelim, lastPos)
        if startPos < 0:
            break
        endPos = text.find(closeDelim, startPos)
        if endPos < 0:
            break
        textToReplace = text[startPos:endPos + 1]
        textInDelimiters = textToReplace[1:-1]
        if openDelim in textInDelimiters:
            results.append(text[lastPos:startPos + 1])
            lastPos = startPos + 1
            continue
        results.append(text[lastPos:startPos])
        results.append(method(textToReplace, textInDelimiters))
        lastPos = endPos + 1
    results.append(text[lastPos:])
    return "".join(results)

def WriteFile(fileName, contents=""):
    """Create or replace a file with the given contents.

    If the file already exists then it is replaced.  If the file has been set
    Read-only, its permissions are changed first and then changed back after
    the file has been written.

    """
    writeable = True
    if os.path.exists(fileName):
        writeable = os.access(fileName, os.W_OK)
    if not writeable:
        permissions = os.stat(fileName).st_mode
        os.chmod(fileName, permissions | os.W_OK << 6)
    if type(contents) == type([]):
        contents = reduce(lambda x, y: x + y, contents)
    open(fileName, "w+").write(contents)
    if not writeable:
        os.chmod(fileName, permissions)

