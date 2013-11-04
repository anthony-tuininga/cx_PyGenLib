"""Define options and methods used for handling logging."""

import cx_Exceptions
import cx_Logging
import cx_OptionParser
import locale
import os
import sys

LOG_ENCODING = cx_OptionParser.Option("--log-encoding",
        default = locale.getpreferredencoding(),
        metavar = "ENCODING", help = "the encoding to use for logging instead")

LOG_FILE = cx_OptionParser.Option("--log-file",
        metavar = "FILE",
        default = os.environ.get(cx_Logging.ENV_NAME_FILE_NAME, "stderr"),
        help = "the name of the file to log messages to or the words stdout "
               "or stderr")

LOG_LEVEL = cx_OptionParser.Option("--log-level",
        metavar = "LEVEL",
        default = os.environ.get(cx_Logging.ENV_NAME_LEVEL, "error"),
        help = "the level at which to log messages; one of debug (10), "
               "info (20), warning (30), error (40) or critical (50)")

LOG_PREFIX = cx_OptionParser.Option("--log-prefix",
        metavar = "STR",
        default = os.environ.get(cx_Logging.ENV_NAME_PREFIX, "%t"),
        help = "the prefix to use for log messages which is a mask containing "
               "%i (id of the thread logging the message), %d (date at which "
               "the message was logged), %t (time at which the message was "
               "logged) or %l (level at which message was logged)")

MAX_FILES = cx_OptionParser.Option("--max-files",
        type = "int",
        metavar = "N",
        default = 10,
        help = "the maximum number of files to keep before overwriting")

MAX_FILE_SIZE = cx_OptionParser.Option("--max-file-size",
        type = "int",
        metavar = "N",
        default = 5242880,
        help = "the maximum size of the file before rotating to the next file")

LOG_LEVEL_NAMES = {
        "debug" : cx_Logging.DEBUG,
        "info" : cx_Logging.INFO,
        "warning" : cx_Logging.WARNING,
        "error" : cx_Logging.ERROR,
        "critical" : cx_Logging.CRITICAL
}


def AddOptions(parser, includeServerOptions = False):
    parser.AddOption(LOG_FILE)
    parser.AddOption(LOG_LEVEL)
    parser.AddOption(LOG_PREFIX)
    parser.AddOption(LOG_ENCODING)
    if includeServerOptions:
        parser.AddOption(MAX_FILES)
        parser.AddOption(MAX_FILE_SIZE)


def ExceptionHandler(excType, excValue, traceback):
    """Exception handler suitable for placing in sys.excepthook."""
    error = cx_Exceptions.GetExceptionInfo(excType, excValue, traceback)
    fullTraceback = not hasattr(sys, "tracebacklimit")
    if fullTraceback:
        cx_Logging.LogException(error)
    else:
        cx_Logging.Error("%s", error.message)
    if sys.stdout.isatty() and not sys.stderr.isatty():
        print(error.message)
        if fullTraceback:
            print("See log file for more details.")


def ProcessOptions(options):
    """Process the options and start logging."""
    logLevel = LOG_LEVEL_NAMES.get(options.logLevel.lower())
    if logLevel is None:
        logLevel = int(options.logLevel)
    logPrefix = options.logPrefix
    if options.logFile.lower() == "stderr":
        cx_Logging.StartLoggingStderr(logLevel, logPrefix, options.logEncoding)
    elif options.logFile.lower() == "stdout":
        cx_Logging.StartLoggingStdout(logLevel, logPrefix, options.logEncoding)
    else:
        maxFiles = getattr(options, "maxFiles", 1)
        maxFileSize = getattr(options, "maxFileSize", 0)
        cx_Logging.StartLogging(options.logFile, logLevel, maxFiles,
                maxFileSize, logPrefix, options.logEncoding)
        f = cx_Logging.GetLoggingFile()
        os.dup2(f.fileno(), 2)
    cx_Logging.SetExceptionInfo(cx_Exceptions.BaseException,
            cx_Exceptions.GetExceptionInfo)
    sys.excepthook = ExceptionHandler

