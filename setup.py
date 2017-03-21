"""Distutils script for cx_PyGenLib.

To install:
    python setup.py install

"""

import sys

from distutils.core import setup

modules = [
        "ceDatabase",
        "ceDatabaseCache",
        "ceDataSource",
        "ceModuleLoader",
        "ceWin32NamedPipes",
        "cx_ClassLibrary",
        "cx_DatabaseTable",
        "cx_Exceptions",
        "cx_Handles",
        "cx_IniFile",
        "cx_LoggingOptions",
        "cx_OptionParser",
        "cx_Parser",
        "cx_ReadLine",
        "cx_Settings",
        "cx_ShellUtils",
        "cx_Threads",
        "cx_Tracing",
        "cx_Utils",
        "cx_Win32Pipe",
        "cx_Win32Service",
        "cx_XML",
        "srml2pdf",
        "xlml2xlsx"
]

setup(
        name = "cx_PyGenLib",
        version = "3.1",
        description = "Set of general Python modules",
        license = "Python Software Foundation License",
        long_description = "Set of general Python modules used by a " \
                "number of projects (cx_OracleTools, cx_OracleDBATools, etc.)",
        author = "Anthony Tuininga",
        author_email = "anthony.tuininga@gmail.com",
        maintainer = "Anthony Tuininga",
        maintainer_email = "anthony.tuininga@gmail.com",
        url = "http://cx-pygenlib.sourceforge.net",
        py_modules = modules,
        packages = ["ceGUI"],
        scripts = ["img2py.py"])

