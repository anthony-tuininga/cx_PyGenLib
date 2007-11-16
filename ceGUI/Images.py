"""
Defines clases for images used within the ceGUI package.
"""

import base64
import cStringIO
import wx

__all__ = [ "Image" ]

class Image(object):

    def GetBitmap(cls):
        return wx.BitmapFromImage(cls.GetImage())

    GetBitmap = classmethod(GetBitmap)

    def GetImage(cls):
        data = base64.b64decode(cls.data)
        stream = cStringIO.StringIO(data)
        return wx.ImageFromStream(stream)

    GetImage = classmethod(GetImage)


# borrowed from the custom tree control in wx.lib
class Checked(Image):
    data = \
            "iVBORw0KGgoAAAANSUhEUgAAAA0AAAANCAYAAABy6+R8AAAABHNCSVQICAgIfA" \
            "hkiAAAAKlJREFUKJFjlAls+M9AImBhYGBgODYxFi7AyMjEwMQEwczMzAxMTMxw" \
            "momJiUEzrp+BCdkEQhqYmCDKmYjRYLDBCCrHjNBESAMDAwPcNrgmmAarXXZYNc" \
            "DUMDIyompiZoZYbbrVAkPDjYjrDIyMjKg2wUyGAVwaGBlRnAdx0oWAcyjxga4B" \
            "xXnIwXol5BJODWh+QsQDExMzXg0YoQfTjE8DAwMDAyM5aQ8AoE8ebApv5jgAAA" \
            "AASUVORK5CYII="


# borrowed from the custom tree control in wx.lib
class Unchecked(Image):
    data = \
            "iVBORw0KGgoAAAANSUhEUgAAAA0AAAANCAYAAABy6+R8AAAABHNCSVQICAgIfA" \
            "hkiAAAAG1JREFUKJGd0sENgDAIBdDPhzHcwGk8eXUU757cyM30UKOlF38lIU0I" \
            "D5IGG6b1RGcEABzb/BRI3ulwD7g7IspLOsZlB+sJX4As7ewBpL9IBWmTChqkgY" \
            "RU0CANmFVIBWaWN6kgfYQKAMD+3N4FsAcJ4jYyX4sAAAAASUVORK5CYII="

