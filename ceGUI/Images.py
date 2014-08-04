"""
Defines clases for images used within the ceGUI package.
"""

import base64
import io
import wx

__all__ = [ "Image" ]

class Image(object):

    def __init__(self, data):
        self.data = data

    def GetBitmap(self):
        return wx.Bitmap(self.GetImage())

    def GetImage(self):
        data = base64.b64decode(self.data)
        stream = io.BytesIO(data)
        return wx.Image(stream)


# borrowed from the custom tree control in wx.lib
Checked = Image(
        "iVBORw0KGgoAAAANSUhEUgAAAA0AAAANCAYAAABy6+R8AAAABHNCSVQICAgIfAhkiAAA"
        "AKlJREFUKJFjlAls+M9AImBhYGBgODYxFi7AyMjEwMQEwczMzAxMTMxwmomJiUEzrp+B"
        "CdkEQhqYmCDKmYjRYLDBCCrHjNBESAMDAwPcNrgmmAarXXZYNcDUMDIyompiZoZYbbrV"
        "AkPDjYjrDIyMjKg2wUyGAVwaGBlRnAdx0oWAcyjxga4BxXnIwXol5BJODWh+QsQDExMz"
        "Xg0YoQfTjE8DAwMDAyM5aQ8AoE8ebApv5jgAAAAASUVORK5CYII=")

# borrowed from the custom tree control in wx.lib
Unchecked = Image(
        "iVBORw0KGgoAAAANSUhEUgAAAA0AAAANCAYAAABy6+R8AAAABHNCSVQICAgIfAhkiAAA"
        "AG1JREFUKJGd0sENgDAIBdDPhzHcwGk8eXUU757cyM30UKOlF38lIU0ID5IGG6b1RGcE"
        "ABzb/BRI3ulwD7g7IspLOsZlB+sJX4As7ewBpL9IBWmTChqkgYRU0CANmFVIBWaWN6kg"
        "fYQKAMD+3N4FsAcJ4jYyX4sAAAAASUVORK5CYII=")

