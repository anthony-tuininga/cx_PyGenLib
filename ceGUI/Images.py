"""
Defines clases for images used within the ceGUI package.
"""

import base64
import cStringIO
import wx

__all__ = [ "Image" ]

class Image(object):

    def __init__(self, data):
        self.data = data

    def GetBitmap(self):
        return wx.BitmapFromImage(self.GetImage())

    def GetImage(self):
        data = base64.b64decode(self.data)
        stream = cStringIO.StringIO(data)
        return wx.ImageFromStream(stream)

# borrowed from the custom tree control in wx.lib
Checked = Image( \
        "iVBORw0KGgoAAAANSUhEUgAAAA0AAAANCAYAAABy6+R8AAAABHNCSVQICAgIfAhkiA" \
        "AAAKlJREFUKJFjlAls+M9AImBhYGBgODYxFi7AyMjEwMQEwczMzAxMTMxwmomJiUEz" \
        "rp+BCdkEQhqYmCDKmYjRYLDBCCrHjNBESAMDAwPcNrgmmAarXXZYNcDUMDIyompiZo" \
        "ZYbbrVAkPDjYjrDIyMjKg2wUyGAVwaGBlRnAdx0oWAcyjxga4BxXnIwXol5BJODWh+" \
        "QsQDExMzXg0YoQfTjE8DAwMDAyM5aQ8AoE8ebApv5jgAAAAASUVORK5CYII=")

# borrowed from the custom tree control in wx.lib
Unchecked = Image( \
        "iVBORw0KGgoAAAANSUhEUgAAAA0AAAANCAYAAABy6+R8AAAABHNCSVQICAgIfAhkiA" \
        "AAAG1JREFUKJGd0sENgDAIBdDPhzHcwGk8eXUU757cyM30UKOlF38lIU0ID5IGG6b1" \
        "RGcEABzb/BRI3ulwD7g7IspLOsZlB+sJX4As7ewBpL9IBWmTChqkgYRU0CANmFVIBW" \
        "aWN6kgfYQKAMD+3N4FsAcJ4jYyX4sAAAAASUVORK5CYII=")

