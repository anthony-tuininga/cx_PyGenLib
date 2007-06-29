"""Methods for querying CVS for information about revisions of files."""

from __future__ import generators

import os
import socket
import _strptime
import sys
import textwrap
import time

if sys.platform == "win32":
    import win32api
    import win32con

# define some constants
SHORT_DATE_FORMAT = "%Y/%m/%d"
LONG_DATE_FORMAT = SHORT_DATE_FORMAT + " %H:%M:%S"
DASHES = "-" * 28
DOUBLE_DASHES = "=" * 77
DEFAULT_PORT = 2401
MONTHS = [ "Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec" ]

class Connection:
    """Represents a connection to the CVS server."""

    def __init__(self, root = None):
        if root is None:
            root = os.environ.get("CVSROOT")
            if root is None:
                raise "CVS root not specified and environment variable " + \
                        "CVSROOT not set."
        try:
            _, style, userInfo, self.repository = root.split(":")
        except:
            raise "Badly formed CVS root '%s'" % root
        if style != "pserver":
            raise "Don't know how to handle anything except pserver."
        try:
            userName, serverName = userInfo.split("@")
        except:
            raise "Badly formed user information '%s'" % userInfo
        if self.repository[0].isdigit():
            pos = self.repository.index("/")
            port = int(self.repository[:pos])
            self.repository = self.repository[pos:]
        else:
            port = DEFAULT_PORT
        self.__Connect(style, serverName, port, userName)

    def __Connect(self, style, serverName, port, userName):
        """Connect to the CVS server and authenticate."""
        password = self.__GetPassword(style, userName, serverName, port)
        ipAddress = socket.gethostbyname(serverName)
        connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connection.connect((ipAddress, port))
        self.__r = connection.makefile("r")
        self.__w = connection.makefile("w")
        print >> self.__w, "BEGIN AUTH REQUEST"
        print >> self.__w, self.repository
        print >> self.__w, userName
        print >> self.__w, password
        print >> self.__w, "END AUTH REQUEST"
        self.__w.flush()
        result = self.__r.readline().rstrip()
        if result != "I LOVE YOU":
            raise "Authentication with CVS server failed."
        self.__errors = []
        print >> self.__w, "Valid-responses Mod-time Updated M E ok error",
        print >> self.__w, "Valid-requests Checked-in Merged Removed"

    def __GetLine(self):
        """Parse the response from the CVS server."""
        while True:
            line = self.__r.readline().rstrip()
            if line == "ok":
                break
            elif line.startswith("error"):
                message = line[5:].strip()
                if message:
                    self.__errors.append(message)
                raise "CVS server reported error:\n" + "\n".join(self.__errors)
            if line.startswith("E"):
                self.__errors.append(line[2:])
            elif line.startswith("M"):
                return line[2:]
            else:
                raise "Unexpected output from CVS: '%s'" % line

    def __GetFile(self, serverDir, localDir):
        line = self.__r.readline().rstrip()
        while line.startswith("E"):
            self.__errors.append(line[2:])
            line = self.__r.readline().rstrip()
        if line == "ok":
            return False
        if not line.startswith("Mod-time"):
            raise ParseError("Mod-time <time>", line)
        timeInSeconds = self.__ParseModTime(line[9:])
        line = self.__r.readline().rstrip()
        if not line.startswith("Updated"):
            raise ParseError("Updated <directory>", line)
        serverFileName = self.__r.readline().rstrip()
        parts = serverFileName[len(serverDir) + 1:].split("/")
        localFileName = os.path.join(localDir, *parts)
        dir, name = os.path.split(localFileName)
        if not os.path.exists(dir):
            os.makedirs(dir)
        parts = self.__r.readline().split("/")
        fileMode = "w"
        if parts[4].find("-kb") >= 0:
            fileMode = "wb"
        self.__r.readline()
        fileSize = int(self.__r.readline())
        outFile = file(localFileName, fileMode)
        while fileSize > 0:
            bufferSize = min(fileSize, 1048576)
            outFile.write(self.__r.read(bufferSize))
            fileSize -= bufferSize
        outFile.close()
        os.utime(localFileName, (timeInSeconds, timeInSeconds))
        return True

    def __GetPassword(self, style, userName, serverName, port):
        """Retrieve the password for the root from the file $HOME/.cvspass
           on Unix systems and from the registry on Windows systems."""
        password = None
        root = ":%s:%s@%s:%s" % (style, userName, serverName, self.repository)
        altRoot = ":%s:%s@%s:%d%s" % \
                (style, userName, serverName, port, self.repository)
        if sys.platform == "win32":
            try:
                key = win32api.RegOpenKey(win32con.HKEY_CURRENT_USER,
                        os.path.join("Software", "cvsnt", "cvspass"))
            except:
                raise "Cannot locate CVS pass location in registry. " + \
                        "Perhaps CVSNT is not installed?"
            try:
                password, type = win32api.RegQueryValueEx(key, root)
            except:
                try:
                    password, type = win32api.RegQueryValueEx(key, altRoot)
                except KeyError:
                    pass
        else:
            fileName = os.path.join(os.environ["HOME"], ".cvspass")
            if os.path.exists(fileName):
                for line in file(fileName).readlines():
                    _, rootToCheck, passwordForRoot = \
                            line.rstrip().split(" ", 2)
                    if rootToCheck in (root, altRoot):
                        password = passwordForRoot
                        break
        if password is None:
            raise "Cannot locate password for root '%s'." % root + \
                            "Please use the CVS client to login first."
        return password

    def __GetTags(self, module, branch, fileName):
        """Parse a tags file containing the order of the tags that are found in
           the CVS repository since CVS does not keep information about the
           order in which releases are made, nor does it place all branch tags
           on the branch itself."""
        modules = {}
        tags = branches = None
        for line in file(fileName).readlines():
            line = line.strip()
            if line.startswith("Module"):
                moduleName = line.split()[1]
                if module != moduleName and module.startswith(moduleName) \
                        and module[len(moduleName)] == "/":
                    module = moduleName
                branches = modules[moduleName] = {}
                branches["HEAD"] = []
                tags = None
            elif line.startswith("Branch"):
                if branches is None:
                    raise "Specify the module before specifying the branch."
                branchName = line.split()[1]
                tags = branches[branchName] = []
                if branchName != "HEAD":
                    branches["HEAD"].append(branchName)
            elif line:
                if tags is None:
                    raise "Specify the branch before specifying the tag."
                tags.append(line)
        if module in modules:
            branches = modules[module]
            if branch in branches:
                return branches[branch]
        return []

    def __MakeTime(self, year, month, day, hour, minute, second):
        """Make time in local time from the six components."""
        timeTuple = (int(year), int(month), int(day), int(hour), int(minute),
                int(second), 0, 0, -1)
        timeInSeconds = time.mktime(timeTuple)
        timeTuple = time.localtime(timeInSeconds)
        if timeTuple[8] and time.daylight:
            timeInSeconds -= time.altzone
        else:
            timeInSeconds -= time.timezone
        return timeInSeconds

    def __MatchingEntry(self, line, searchString, matchList):
        """Add the matching string to the match list if the search string is
           found in the line and return a boolean indicating if this was
           done."""
        pos = line.find(searchString)
        if pos >= 0:
            matchList.append(line[:pos - 1])
            return True
        return False

    def __ParseField(self, field):
        """Return the field value, stripping out the extra spaces and label."""
        return field[field.index(":") + 1:].strip()

    def __ParseLogOutput(self, allTags, fromTag, toTag, fromDate, toDate):
        """Parse the output from the CVS log command, returning the file name
           and all revisions which match the criteria. Note that the tags are
           filtered in Python, rather than in CVS because if any tag is not
           found in the file, it is not reported at all."""

        # set filter criteria, if necessary
        fromTagIndex = toTagIndex = None
        if fromTag is not None and fromTag in allTags:
            fromTagIndex = allTags.index(fromTag)
        if toTag is not None and toTag in allTags:
            toTagIndex = allTags.index(toTag)

        # continue until end of output
        while self.__GetLine() is not None:

            # determine the name of the file that is being logged
            line = self.__GetLine()
            if not line.startswith("RCS file:"):
                raise ParseError("RCS file: <file>", line)
            fileName = line[10:-2]
            if not fileName.startswith(self.repository):
                raise "File %r not in root %r." % (fileName, self.repository)
            fileName = fileName[len(self.repository) + 1:]

            # skip output until the symbolic names are found
            while self.__GetLine() != "symbolic names:":
                pass

            # read out the list of tags
            indexesByRev = {}
            while True:
                line = self.__GetLine()
                if not line.startswith("\t"):
                    break
                tag, rev = line.strip().split(": ")
                try:
                    tagIndex = allTags.index(tag)
                except ValueError:
                    continue
                parts = [int(s) for s in rev.split(".")]
                if len(parts) > 2 and parts[-2] == 0:
                    rev = ".".join([str(p) for p in parts[:-2]])
                if rev in indexesByRev:
                    lowIndex, highIndex = indexesByRev[rev]
                    lowIndex = min(lowIndex, tagIndex)
                    highIndex = max(highIndex, tagIndex)
                    indexesByRev[rev] = (lowIndex, highIndex)
                else:
                    indexesByRev[rev] = (tagIndex, tagIndex)

            # skip output until the leading dashes are found
            while self.__GetLine() != DASHES:
                pass

            # parse the revisions
            revisions = []
            deadRevisions = []
            lowIndex = highIndex = lowTag = highTag = None
            while True:
                revNum = self.__GetLine().split()[-1]
                date, author, state, changes = self.__GetLine().split(";")
                date = self.__ParseRevisionTime(self.__ParseField(date))
                author = self.__ParseField(author)
                state = self.__ParseField(state)
                textLines = []
                while True:
                    line = self.__GetLine()
                    if line in (DASHES, DOUBLE_DASHES):
                        break
                    if not line.startswith("branches:"):
                        textLines.append(line)
                if revNum in indexesByRev:
                    lowIndex, highIndex = indexesByRev[revNum]
                    if deadRevisions:
                        lowTag = allTags[highIndex]
                        if highIndex + 1 < len(allTags):
                            highTag = allTags[highIndex + 1]
                        else:
                            highTag = None
                        for revision in deadRevisions:
                            if (fromTag is None or highTag is None \
                                            or highIndex >= fromTagIndex) \
                                    and (toTag is None or lowTag is None \
                                            or highIndex < toTagIndex):
                                revision.lowTag = lowTag
                                revision.highTag = highTag
                                revisions.append(revision)
                        deadRevisions = []
                if lowIndex is not None:
                    highTag = allTags[lowIndex]
                    if lowIndex == 0:
                        lowTag = None
                    else:
                        lowTag = allTags[lowIndex - 1]
                elif allTags:
                    lowTag = allTags[-1]
                if (fromDate is None or date > fromDate) \
                        and (toDate is None or date <= toDate):
                    rev = Revision(revNum, lowTag, highTag, date, author,
                            state, "\n".join(textLines))
                    if state == "dead" or deadRevisions:
                        deadRevisions.append(rev)
                    elif (fromTag is None or highTag is None \
                                    or lowIndex is not None \
                                    and lowIndex > fromTagIndex) \
                            and (toTag is None or lowTag is None \
                                    or lowIndex is not None \
                                    and lowIndex <= toTagIndex):
                        revisions.append(rev)
                if line == DOUBLE_DASHES:
                    break

            # add any dead revisions, if applicable
            if deadRevisions and toTag is None:
                for revision in deadRevisions:
                    revision.lowTag = lowTag
                    revision.highTag = highTag
                    revisions.append(revision)

            # return the file name and the revisions
            if revisions:
                yield fileName, revisions

    def __ParseModTime(self, value):
        """Parse the modification time and return the time in local time."""
        try:
            day, monthName, year, timePortion, offset = value.split()
            month = MONTHS.index(monthName) + 1
            hour, minute, second = timePortion.split(":")
            return self.__MakeTime(year, month, day, hour, minute, second)
        except:
            raise "Cannot parse modification time '%s'" % value

    def __ParseRevisionTime(self, value):
        """Parse the revision time and return the time in local time."""
        try:
            datePortion, timePortion = value.split()
            year, month, day = datePortion.split("/")
            hour, minute, second = timePortion.split(":")
            return self.__MakeTime(year, month, day, hour, minute, second)
        except:
            raise "Cannot parse revision time '%s'" % value

    def Diff(self, module, fromTag, toTag = "HEAD"):
        """Return a 3-tuple consisting of a list of new files, modified files
           and removed files from the first tag to the second tag."""
        newFiles = []
        modFiles = []
        remFiles = []
        print >> self.__w, "Global_option", "-q"
        print >> self.__w, "Root", self.repository
        print >> self.__w, "Argument", "-r%s" % fromTag
        print >> self.__w, "Argument", "-r%s" % toTag
        print >> self.__w, "Argument", "-s"
        print >> self.__w, "Argument", module
        print >> self.__w, "rdiff"
        self.__w.flush()
        while True:
            line = self.__GetLine()
            if line is None:
                break
            if not line.startswith("File"):
                raise ParseError("File", line)
            s = line[5:]
            if not self.__MatchingEntry(s, "is new;", newFiles) \
                    and not self.__MatchingEntry(s, "is removed;", remFiles) \
                    and not self.__MatchingEntry(s, "changed from", modFiles):
                raise "Unable to parse output of line '%s'" % line
        return newFiles, modFiles, remFiles

    def Export(self, module, tag, localDir):
        """Export the source for the module at the given tag into the given
           local directory."""
        print >> self.__w, "Root", self.repository
        print >> self.__w, "Global_option", "-Q"
        print >> self.__w, "Argument", "-r%s" % tag
        print >> self.__w, "Argument", module
        print >> self.__w, "export"
        self.__w.flush()
        serverDir = self.repository + "/" + module
        while self.__GetFile(serverDir, localDir):
            pass

    def Log(self, module, branch = "HEAD", tagsFile = None, fromTag = None,
            toTag = None, fromDate = None, toDate = None):
        """Return a list of file names and revisions on the given branch
           matching the given criteria."""
        tags = []
        if tagsFile is not None:
            tags = self.__GetTags(module, branch, tagsFile)
        print >> self.__w, "Global_option", "-q"
        print >> self.__w, "Root", self.repository
        print >> self.__w, "Argument", "-S"
        if branch == "HEAD":
            print >> self.__w, "Argument", "-b"
        else:
            print >> self.__w, "Argument", "-r%s" % branch
        print >> self.__w, "Argument", module
        print >> self.__w, "rlog"
        self.__w.flush()
        return self.__ParseLogOutput(tags, fromTag, toTag, fromDate, toDate)

    def LogAndReport(self, module, branch = None, tagsFile = None,
            filterFromTag = None, filterToTag = None, filterFromDate = None,
            filterToDate = None):
        """Report the revisions sorted by tag, date, and author."""

        # group the revisions by tag, date and author
        tagGroups = {}
        for fileName, revisions in self.Log(module, branch, tagsFile,
                filterFromTag, filterToTag, filterFromDate, filterToDate):
            for revision in revisions:
                date = time.strftime(SHORT_DATE_FORMAT,
                        time.localtime(revision.date))
                key = (revision.lowTag, revision.highTag)
                groupRevs = tagGroups.get(key)
                if groupRevs is None:
                    groupRevs = tagGroups[key] = {}
                revTuple = (date, revision.author, revision.text)
                revFiles = groupRevs.get(revTuple)
                if revFiles is None:
                    revFiles = groupRevs[revTuple] = []
                fileName = fileName.replace("Attic/", "")
                relativeFileName = fileName[len(module) + 1:]
                if not relativeFileName:
                    relativeFileName = "*** ONLY FILE ***"
                if revision.state == "dead":
                    relativeFileName = "%s [REMOVE]" % relativeFileName
                revFiles.append(relativeFileName)

        # Build a list of the results
        result = []
        keys = tagGroups.keys()
        keys.sort()
        outputSeparator = False
        for key in keys:
            fromTag, toTag = key
            if fromTag is None:
                fromTag = "beginning of branch"
            if toTag is None:
                toTag = "end of branch"
            if outputSeparator:
                result.append("")
                result.append("")
            outputSeparator = True
            result.append("=" * 78)
            result.append("Change log from %s to %s" % (fromTag, toTag))
            result.append("  For %s" % module)
            result.append("=" * 78)
            revisions = tagGroups[key]
            revKeys = revisions.keys()
            revKeys.sort()
            for revKey in revKeys:
                date, author, text = revKey
                files = revisions[revKey]
                result.append("")
                result.append("Date: %s Author: %s" % (date, author))
                result += textwrap.wrap(text,78)
                result += [ '  %s' % file for file in files]
                result.append("-" * 78)
        return result


class ParseError(Exception):
    """Exception class raised when a parse error occurs."""

    def __init__(self, expected, found):
        self.expected = expected
        self.found = found.rstrip()

    def __str__(self):
        return "expecting %r\n%r" % (self.expected, self.found)


class Revision:
    """Representation of a revision in CVS."""

    def __init__(self, num, lowTag, highTag, date, author, state, text):
        self.num = num
        self.lowTag = lowTag
        self.highTag = highTag
        self.date = date
        self.author = author
        self.state = state
        self.text = text


def _WorkingFileContents(dir, name):
    """Return the contents of the working file."""
    fileName = os.path.join(dir, "CVS", name)
    if not os.path.exists(fileName):
        raise "Missing CVS working file '%s'." % fileName
    return file(fileName).read().strip()


def DateFromString(value):
    """Return the time value from the string. A short date format (without
       the time) is supported in addition to the long date format."""
    try:
        date = _strptime.strptime(value, SHORT_DATE_FORMAT)
    except ValueError:
        date = _strptime.strptime(value, LONG_DATE_FORMAT)
    return time.mktime(date)


def RootAndModule(workingDir):
    """Return the root and module given a working directory."""
    return _WorkingFileContents(workingDir, "Root"), \
           _WorkingFileContents(workingDir, "Repository")

