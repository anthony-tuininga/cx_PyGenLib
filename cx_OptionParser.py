"""Provides routines for standardized command line argument and option
   parsing.  It is based on the standard library optparse with some
   extensions."""

import optparse
import os
import sys
import textwrap
import warnings

import cx_Exceptions
import cx_ReadLine

# commonly used attributes
PROMPT_ATTR = "prompt"
REQUIRED_ATTR = "required"
VARIABLE_ATTR = "variable"
KEYWORDS_ATTR = "keywords"
DEFAULT_ATTR = "default"
ACTION_ATTR = "action"
HELP_ATTR = "help"
DEST_ATTR = "dest"

# build constants
try:
    from BUILD_CONSTANTS import *
except ImportError:
    BUILD_TIMESTAMP = None
    BUILD_RELEASE_STRING = None
    BUILD_COPYRIGHT = None
    BUILD_HOST = None
    if cx_Exceptions.__file__ == "<frozen>":
        SOURCE_TIMESTAMP = "Frozen"
    else:
        SOURCE_TIMESTAMP = "Source"

class ArgumentValueError(cx_Exceptions.BaseException):
    MESSAGE = "argument %(name)s: invalid %(type)s value: %(value)r"


def AddDefaultsToHelp(attributes):
    """Add the default value to the help string."""
    if HELP_ATTR in attributes and DEFAULT_ATTR in attributes:
        defaultValue = attributes[DEFAULT_ATTR]
        action = attributes.get(ACTION_ATTR)
        if defaultValue and action not in ("store_true", "store_false"):
            attributes[HELP_ATTR] += " [default: %r]" % defaultValue

class Option(optparse.Option):
    """Defines an option on the command line, optionally allowing for
    prompting for the value if one is not specified or requiring that a
    value be specified on the command line"""

    def __init__(self, *options, **attributes):
        """Constructor. Handles optional keyword arguments "prompt" and
        "required". Extends base constructor."""
        AddDefaultsToHelp(attributes)
        for attr in [PROMPT_ATTR, REQUIRED_ATTR]:
            if attr in attributes:
                setattr(self, attr, attributes[attr])
                del attributes[attr]
        if DEST_ATTR not in attributes:
            for option in options:
                if option.startswith("--"):
                    parts = option[2:].split("-")
                    parts = [parts[0]] + [s.capitalize() for s in parts[1:]]
                    attributes[DEST_ATTR] = "".join(parts)
        optparse.Option.__init__(self, *options, **attributes)

    def __repr__(self):
        return str(self)

    def __str__(self):
        return optparse.Option.__str__(self) + " option"


class Argument:
    """Defines an argument on the command line."""

    def __init__(self, name, **attributes):
        self.type = None
        self.dest = name
        self.metavar = name.upper()
        for attr in attributes:
            setattr(self, attr, attributes[attr])
        if VARIABLE_ATTR in attributes:
            setattr(self, KEYWORDS_ATTR, False)

    def __repr__(self):
        return str(self)

    def __str__(self):
        return "%s argument" % self.metavar


# common options
TRACEBACK_OPTION = Option("-t", "--traceback", action = "store_true",
    help = "display traceback on error", default = False)
SHOW_BANNER_OPTION = Option("--show-banner", action = "store_true",
    help = "display banner on execution")
PROMPT_OPTION = Option("-p", "--prompt", action = "store_true",
    help = "prompt for options and arguments")


class OptionParser(optparse.OptionParser):
    """Class which parses the arguments and options on the command line."""

    # define standard options
    standard_option_list = optparse.OptionParser.standard_option_list + \
            [TRACEBACK_OPTION, SHOW_BANNER_OPTION]

    def __init__(self, name = None, version = None, docString = None,
            copyright = None, extendedVersion = None):
        self.__args = []
        self.__varArg = None
        if name is None:
            name, ext = os.path.splitext(os.path.basename(sys.argv[0]))
        if docString is None:
            docString = sys.modules["__main__"].__doc__
        self.__docString = docString
        if version is None:
            version = BUILD_RELEASE_STRING
        if version is not None:
            self.__banner = "%s %s" % (name, version)
        else:
            self.__banner = name
        if extendedVersion is None and BUILD_TIMESTAMP is not None:
            extendedVersion = "Build: %s on %s" % (BUILD_TIMESTAMP, BUILD_HOST)
        if copyright is None:
            copyright = BUILD_COPYRIGHT
        version = "%s (%s)" % (self.__banner, SOURCE_TIMESTAMP)
        if extendedVersion is not None:
            version += "\n%s" % extendedVersion
        if copyright is not None:
            version += "\n%s" % copyright
        usage = "%s\n\nUsage: %s [options]" % (version, name)
        optparse.OptionParser.__init__(self, option_class = Option,
            usage = usage, version = version)
        warnings.filterwarnings("ignore", category = FutureWarning)
        warnings.filterwarnings("ignore", category = DeprecationWarning)

    def __PrintHelpSection(self, heading, helpTuples):
        if not helpTuples:
            return
        maxLength = 20
        indentString = " " * (maxLength + 4)
        sys.stderr.write("%s:\n" % heading)
        for name, helpString in helpTuples:
            if len(name) > maxLength:
                sys.stderr.write("  %s\n" % name)
                output = textwrap.fill(helpString, width = 79,
                        initial_indent = indentString,
                        subsequent_indent = indentString)
            else:
                text = "  %s  %s" % (name.ljust(maxLength), helpString)
                output = textwrap.fill(text, width = 79,
                        subsequent_indent = indentString)
            sys.stderr.write(output + "\n")
        sys.stderr.write("\n")

    def __PromptForValue(self, option, values):
        """Prompt for the value of an option."""
        defaultValue = ""
        if getattr(values, option.dest):
            defaultValue = str(getattr(values, option.dest))
        value = cx_ReadLine.ReadLine(option.prompt, defaultValue)
        if value:
            setattr(values, option.dest, value)

    def _ProcessArgs(self, values):
        # display version, if not in quiet mode
        if values.showBanner:
            sys.stderr.write(self.__banner + "\n")

        # turn off traceback if not desired
        if not values.traceback:
            sys.tracebacklimit = 0

    def AddArgument(self, nameOrArg, **attributes):
        """Add an argument to the list of supported arguments."""
        if isinstance(nameOrArg, Argument):
            arg = nameOrArg
        else:
            arg = Argument(nameOrArg, **attributes)
        AddDefaultsToHelp(arg.__dict__)
        self.defaults[arg.dest] = getattr(arg, DEFAULT_ATTR, None)
        if hasattr(arg, VARIABLE_ATTR) or hasattr(arg, KEYWORDS_ATTR):
            self.__varArg = arg
        else:
            self.__args.append(arg)

    def AddOption(self, *args, **keywordArgs):
        """Add an option to the list of supported options."""
        optparse.OptionParser.add_option(self, *args, **keywordArgs)

    def AllowVarArgs(self, name, help=None):
        self.AddArgument(name, variable = True, help = help)

    def error(self, message):
        """Print an error message and exit.  Overrides base method."""
        self.print_help(sys.stderr)
        sys.exit("\nerror: %s" % message)

    def Parse(self):
        """Parse the command line returning an object containing the values."""

        # modify the usage if any arguments were added
        if self.__args or self.__varArg:
            args = []
            numClosingBrackets = 0
            for arg in self.__args:
                if hasattr(arg, REQUIRED_ATTR) and arg.required:
                    args.append(arg.metavar)
                else:
                    args.append("[" + arg.metavar)
                    numClosingBrackets += 1
            self.usage += " " + " ".join(args) + "]" * numClosingBrackets
            if self.__varArg:
                self.usage += " [%s, ...]" % self.__varArg.metavar

        # add a prompt option, if any options or arguments are promptable
        promptArgs = [a for a in self.option_list + self.__args \
            if hasattr(a, PROMPT_ATTR)]
        if promptArgs:
            self.defaults[PROMPT_ATTR] = 0
            self.add_option(PROMPT_OPTION)
            option = self.option_list.pop()
            self.option_list.insert(len(self.standard_option_list), option)

        # perform the real parsing of the arguments
        values, argValues = optparse.OptionParser.parse_args(self)

        # set the values of any arguments
        if len(argValues) > len(self.__args) and self.__varArg is None:
            self.error("too many arguments")
        for arg, argValue in zip(self.__args, argValues):
            if arg.type == "int":
                try:
                    argValue = int(argValue)
                except ValueError:
                    raise ArgumentValueError(name = arg.dest, type = "integer",
                            value = argValue)
            setattr(values, arg.dest, argValue)
        if self.__varArg is not None:
            value = argValues[len(self.__args):]
            if self.__varArg.keywords:
                rawValues = [s.split("=") for s in value]
                if [x for x in rawValues if len(x) != 2]:
                    self.error("keyword arguments must be of form name=value.")
                value = dict(rawValues)
            setattr(values, self.__varArg.dest, value)

        # prompt for any arguments that are missing
        if promptArgs and values.prompt:
            for arg in promptArgs:
                self.__PromptForValue(arg, values)

        # verify that all required options and arguments have a value
        requiredArgs = [a for a in self.option_list + self.__args \
            if hasattr(a, REQUIRED_ATTR) and a.required]
        for arg in requiredArgs:
            if getattr(values, arg.dest) is None:
                self.error("%s not supplied" % arg)

        self._ProcessArgs(values)

        return values

    def print_help(self, outFile = None):
        """Print help message in response to the -h option.

           Override the base method to avoid inclusion of the distutils module
           which adds a fair amount of code.  In addition this method provides
           help for the arguments and a brief synopsis of the program in
           general.

        """

        # print the main usage message
        sys.stderr.write(self.usage + "\n\n")

        # print the doc string for the program
        if self.__docString:
            sys.stderr.write(textwrap.fill(self.__docString.strip(),
                    width = 79))
            sys.stderr.write("\n\n")

        # print the usage message for the arguments
        helpStrings = []
        for arg in self.__args + [self.__varArg]:
            if arg is None:
                continue
            if hasattr(arg, HELP_ATTR):
                helpStrings.append((arg.metavar, arg.help))
            else:
                helpStrings.append((arg.metavar, ""))
        self.__PrintHelpSection("arguments", helpStrings)

        # print the usage message for the options
        helpStrings = []
        for option in self.option_list:
            if option.help is optparse.SUPPRESS_HELP:
                continue
            optionStrings = []
            if option.takes_value():
                metavar = option.metavar or option.dest.upper()
                for shortOption in option._short_opts:
                    optionStrings.append(shortOption + metavar)
                for longOption in option._long_opts:
                    optionStrings.append(longOption + "=" + metavar)
            else:
                optionStrings = option._short_opts + option._long_opts
            helpStrings.append((", ".join(optionStrings), option.help))
        self.__PrintHelpSection("options", helpStrings)

