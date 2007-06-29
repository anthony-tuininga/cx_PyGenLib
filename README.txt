cx_PyGenLib
-----------
This project contains a number of generic Python modules that are used by
Computronix for a number of projects (cx_Freeze, cx_OracleTools,
cx_OracleDBATools, etc.) and as such they are handled independently, rather
than bundled with the distribution of the dependent project.

It is released under a free software license, see LICENSE.txt for more
details.

Note that six modules (logging, optparse, textwrap, _strptime, tarfile and
modulefinder) are modules that are part of the upcoming Python 2.3
distribution; they are included here so that I can make use of the advanced
functionality. They operate just fine with a Python 2.2 distribution (and
perhaps earlier).

