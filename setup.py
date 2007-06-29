"""Distutils script for cx_PyGenLib.

To install:
    python setup.py install

"""

import sys

from distutils.core import setup

modules = [
        "cx_ClassLibrary",
        "cx_CVS",
        "cx_DatabaseTable",
        "cx_Exceptions",
        "cx_FTP",
        "cx_Handles",
        "cx_IniFile",
        "cx_LoggingOptions",
        "cx_OptionParser",
        "cx_Parser",
        "cx_PrettyPrinter",
        "cx_ReadLine",
        "cx_ServerFramework",
        "cx_Settings",
        "cx_ShellUtils",
        "cx_Threads",
        "cx_Tracing",
        "cx_Utils",
        "cx_Win32Pipe",
        "cx_Win32Service",
        "cx_XML"
]

setup(
        name = "cx_PyGenLib",
        version = "2.4",
        description = "Set of general Python modules",
        license = "See LICENSE.txt",
        long_description = "Set of general Python modules used by a " + \
                "number of Computronix projects (cx_OracleTools, " + \
                "cx_OracleDBATools, etc.)",
        author = "Anthony Tuininga",
        author_email = "anthony.tuininga@gmail.com",
        url = "http://starship.python.net/crew/atuining",
        py_modules = modules)

