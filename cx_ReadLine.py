"""Extends readline capability on those platforms that support it."""

import getpass
import os
import sys

def AskBooleanQuestion(label):
    """Ask a boolean question repeatedly until one of Y or N is returned."""
    result = AskQuestion(label, ["Y", "N"])
    return result == "Y"

def AskQuestion(label, values):
    """Ask question repeatedly until one of the right answers is given. The
       first possible value is considered the default."""
    validValues = [s.upper() for s in values]
    defaultValue = validValues[0]
    stringValues = ['"%s"' % v for v in values]
    errorMessage = "Expecting one of %s\n" % " or ".join(stringValues)
    while True:
        value = ReadLine(label, defaultValue).upper()
        if value in validValues:
            break
        sys.stderr.write(errorMessage)
    return value

def GetChoices(header, label, valueTuples):
    """Ask questions repeatedly until one of the right answers is given. The
       values are expected as a list of tuples consisting of the description
       and the value. The list of values selected is returned."""
    values = []
    optionStrings = []
    for i, (description, value) in enumerate(valueTuples):
        values.append(value)
        optionStrings.append("%d) %s" % (i + 1, description))
    optionStrings.append("")
    optionStrings.append("Use hyphen for ranges and comma for multiple " \
            "(for example, 1-4,5,7-8)")
    options = "\n".join(optionStrings)
    while True:
        print("")
        print(header)
        print("")
        print(options)
        print("")
        result = ParseChoices(ReadLine(label), len(valueTuples))
        if isinstance(result, list):
            return [values[i] for i in result]
        result = "*** " + result
        print(result)

def ParseChoices(string, numValid):
    """Parse the choices selected and return a list of numbers if valid or a
       string indicating the problem if invalid."""
    if not string:
        return []
    choices = {}
    for part in string.split(","):
        try:
            rangeParts = [int(s) for s in part.split("-")]
        except ValueError as error:
            badValue = str(error).split(":", 2)[1].strip()
            if badValue:
                return "invalid number: %s" % badValue
            return "missing value in range or list"
        if len(rangeParts) > 2:
            return "ranges should be of the form min-max"
        elif len(rangeParts) == 2:
            minValue, maxValue = rangeParts
            if minValue > maxValue:
                return "min value of range is greater than max value of range"
            for i in range(minValue, maxValue + 1):
                choices[i] = None
        else:
            choices[rangeParts[0]] = None
    badChoices = [i for i in choices if i > numValid or i < 1]
    if badChoices:
        return "%d is an invalid choice" % badChoices[0]
    choices = [i - 1 for i in choices.keys()]
    choices.sort()
    return choices

def ReadLine(label, defaultValue = "", password = False):
    """Read a line of input from stdin and return it. If nothing is read, the
       default value is returned. Note that if stdin in not a TTY, the label
       will not be displayed."""
    if sys.stdin.isatty():
        if defaultValue:
            label += " [%s]" % defaultValue
        label += ": "
        if password:
            result = getpass.getpass(label)
        else:
            if sys.platform == "win32":
                import msvcrt
                for c in label:
                    msvcrt.putch(c.encode())
                result = sys.stdin.readline().strip()
            else:
                result = input(label).strip()
    else:
        result = input().strip()
    if not result:
        return defaultValue
    return result

# set up readline capability, if applicable
try:
    import readline
    readline.read_init_file()
except:
    pass

