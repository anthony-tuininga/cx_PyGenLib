"""
Defines clases for images used within the ceGUI package.
"""

import base64
import cStringIO
import wx
import zlib

__all__ = [ "Image" ]

class Image(object):

    def GetBitmap(cls):
        return wx.BitmapFromImage(cls.GetImage())

    GetBitmap = classmethod(GetBitmap)

    def GetImage(cls):
        data = zlib.decompress(base64.b64decode(cls.data))
        stream = cStringIO.StringIO(data)
        return wx.ImageFromStream(stream)

    GetImage = classmethod(GetImage)


# borrowed from the custom tree control in wx.lib
class Checked(Image):
    data = \
            "eNrrDPBz5+WS4mJgYOD19HAJAtEgzMEGJIteP6kBUizFTp4hHEBQw5HSAeSv9H" \
            "RxDNGYmDyFM+fHeQelhMSEhAQLM0MxvQMnThw5cITl4JkzZ3h8fM4UzOrs7HQ0" \
            "Xje/kfMmi5PUjBkKp2Z2XEzYcJBD63jPBRcPZiC4Y7ZDbQbb6tiyCNMDVwyMjB" \
            "ZlJaW1ReTuusrkfLi34zVPT0/PCrODPm2MMVISkoFz2AsvtTYUa3xsXMd4tPLE" \
            "wSrVJ0J+vBl1TkeYhYWN43glFrJf7vEHmcusbJnJz7DAXy6HK/+ZBdDRDJ6ufi" \
            "7rnBKaAJLMU58="


# borrowed from the custom tree control in wx.lib
class Unchecked(Image):
    data = \
            "eNrrDPBz5+WS4mJgYOD19HAJAtEgzMEGJIteP6kBUizFTp4hHEBQw5HSAeTner" \
            "o4hmhMnHvpIG+DAQfrhfPthncOZNpUloq8n3fnxNkvAYuXiterKvpy8E9ik172" \
            "1SWdhUHm9h8Rj3svC/h3WCud8rY6lsr+mjO+QeftG8Yl+z1YMydzSS1pbAm5oM" \
            "A7I9SDNW2a+UqF2hYuhgP/7txj3cDO+cjMKL4baDGDp6ufyzqnhCYAh1M9vg=="

