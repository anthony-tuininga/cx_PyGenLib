"""
Module which defines classes used in creating reports with print preview
capability.
"""

import ceGUI
import wx

class Printout(wx.Printout):

    def __init__(self, body, title):
        wx.Printout.__init__(self, title)
        self.body = body

    def GetPageInfo(self):
        dc = self.GetDC()
        self.maxPage = self.body.GetNumberOfPages(dc)
        return (1, self.maxPage, 1, self.maxPage)

    def HasPage(self, pageNum):
        return (pageNum <= self.maxPage)

    def OnBeginPrinting(self):
        self.FitThisSizeToPage((self.body.pageWidth, self.body.pageHeight))

    def OnPrintPage(self, pageNum):
        dc = self.GetDC()
        self.body.OnPrintPage(dc, pageNum)
        return True


class Report(object):
    reportBodyName = "ReportBody"
    paperId = wx.PAPER_LETTER
    orientation = wx.PORTRAIT
    defaultSize = (700, 1000)
    title = ""

    def __init__(self, title = None, **bodyArgs):
        if title is not None:
            self.title = title
        cls = ceGUI.GetModuleItem(self.reportBodyName, associatedObj = self)
        self.body = cls(self.title, **bodyArgs)
        self.printout = Printout(self.body, self.title)
        self.printoutForPrinting = Printout(self.body, self.title)
        self.printData = wx.PrintData()
        self.printData.SetPaperId(self.paperId)
        self.printData.SetOrientation(self.orientation)

    def Preview(self, args, parent = None):
        self.body.Retrieve(*args)
        printData = wx.PrintDialogData(self.printData)
        preview = wx.PrintPreview(self.printout, self.printoutForPrinting,
                printData)
        frame = wx.PreviewFrame(preview, parent, self.title,
                size = self.defaultSize)
        frame.Initialize()
        frame.Show(True)


class ReportColumn(ceGUI.BaseControl):
    defaultWidth = 200

    def __init__(self, attrName, heading, startX = None, width = None,
            centered = False, rightJustified = False):
        self.attrName = attrName
        self.heading = heading
        self.startX = startX
        self.width = width or self.defaultWidth
        self.centered = centered
        self.rightJustified = rightJustified
        self._Initialize()

    def GetValue(self, row):
        value = getattr(row, self.attrName)
        if value is not None:
            if isinstance(value, str):
                return value
            return str(value)

    def PrintValue(self, dc, value, y):
        if self.centered:
            textWidth, textHeight = dc.GetTextExtent(value)
            dc.DrawText(value, self.startX + self.width / 2 - textWidth / 2, y)
        elif self.rightJustified:
            textWidth, textHeight = dc.GetTextExtent(value)
            dc.DrawText(value, self.startX + self.width - textWidth, y)
        else:
            dc.DrawText(value, self.startX, y)


class ReportDateColumn(ReportColumn):
    dateFormatAttrName = "dateFormat"
    dateFormat = None

    def GetValue(self, row):
        value = getattr(row, self.attrName)
        if value is not None:
            dateFormat = self.dateFormat
            if dateFormat is None:
                dateFormat = getattr(self.config, self.dateFormatAttrName)
            return value.strftime(dateFormat)
        

class ReportTimestampColumn(ReportDateColumn):
    dateFormatAttrName = "timestampFormat"


class ReportBody(object):
    columnSeparation = 20
    pageWidth = 2160
    pageHeight = 2795
    topMargin = 87
    leftMargin = 87

    def __init__(self, title = None):
        app = wx.GetApp()
        for name in app.copyAttributes:
            value = getattr(app, name)
            setattr(self, name, value)
        self.columns = []
        self.title = title
        self.OnCreate()

    def AddColumn(self, attrName, heading, startX = None, width = None,
            centered = False, rightJustified = False, cls = ReportColumn):
        if startX is None:
            if not self.columns:
                startX = self.leftMargin
            else:
                lastColumn = self.columns[-1]
                startX = lastColumn.startX + lastColumn.width + \
                        self.columnSeparation
        column = cls(attrName, heading, startX, width, centered,
                rightJustified)
        self.columns.append(column)

    def CenterColumnsOnPage(self):
        minX = self.columns[0].startX
        maxX = self.columns[-1].startX + self.columns[-1].width
        newMinX = (self.pageWidth - (maxX - minX)) / 2
        delta = newMinX - minX
        for column in self.columns:
            column.startX += delta

    def DrawTextCentered(self, dc, text, x, y):
        width, height = dc.GetTextExtent(text)
        dc.DrawText(text, x - width / 2, y)

    def DrawTextCenteredOnPage(self, dc, text, y):
        width, height = dc.GetTextExtent(text)
        x = (self.pageWidth - width) / 2
        dc.DrawText(text, x, y)

    def DrawTextRightJustified(self, dc, text, x, y):
        width, height = dc.GetTextExtent(text)
        dc.DrawText(text, x - width, y)

    def GetNumberOfPages(self, dc):
        return 1

    def OnCreate(self):
        pass

    def PrintColumns(self, dc, row, y):
        for column in self.columns:
            value = column.GetValue(row)
            if value:
                column.PrintValue(dc, value, y)

    def PrintColumnHeadings(self, dc, y):
        for column in self.columns:
            column.PrintValue(dc, column.heading, y)

    def WrapText(self, dc, text, width):
        if text is None or not text.rstrip():
            return []
        lines = []
        for line in text.splitlines():
            line = line.rstrip()
            if not line:
                lines.append(line)
                continue
            while line:
                extents = dc.GetPartialTextExtents(line)
                if extents[-1] < width:
                    lines.append(line)
                    break
                lastWordPos = -1
                for charIndex, char in enumerate(line):
                    charWidth = extents[charIndex]
                    if charWidth > width:
                        if lastWordPos < 0:
                            lastWordPos = charIndex - 1
                        lines.append(line[:lastWordPos].rstrip())
                        line = line[lastWordPos:].strip()
                        break
                    if char.isspace():
                        lastWordPos = charIndex
        return lines

