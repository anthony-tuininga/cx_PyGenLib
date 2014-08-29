"""
Converts an image to a Python script similar in nature to the wxPython script
of the same name but this script only accepts PNG files and generates output
useful for using ceGUI.Image classes. Use the img2img.py wxPython script if you
need to deal with a different type of image.
"""

import base64
import sys
import wx

for argIndex, inputFileName in enumerate(sys.argv[1:]):
    data = base64.b64encode(file(inputFileName, "rb").read())
    print("# image from %s" % inputFileName)
    print("image%s = ceGUI.Image(" % (argIndex + 1))
    while data:
        part = data[:68]
        data = data[68:]
        output = '        "%s"' % part
        if not data:
            output += ")"
        print(output)
    print()

