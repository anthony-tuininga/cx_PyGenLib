"""
Converts an image to a Python script similar in nature to the wxPython script
of the same name but this script only accepts PNG files and generates output
useful for using ceGUI.Image classes. Use the img2img.py wxPython script if you
need to deal with a different type of image.
"""

import base64
import sys
import wx
import zlib

for argIndex, inputFileName in enumerate(sys.argv[1:]):
    data = base64.b64encode(zlib.compress(file(inputFileName, "rb").read()))
    print "# image from %s" % inputFileName
    print "class Image%s(ceGUI.Image):" % (argIndex + 1)
    print "    data = \\"
    while data:
        part = data[:62]
        data = data[62:]
        output = '            "%s"' % part
        if data:
            output += " \\"
        print output
    print

