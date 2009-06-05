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


class Report(object):
    reportBodyName = "ReportBody"
    paperId = wx.PAPER_LETTER
    orientation = wx.PORTRAIT
    defaultSize = (700, 1000)
    title = ""

    def __init__(self):
        cls = ceGUI.GetModuleItem(self.reportBodyName, associatedObj = self)
        self.body = cls()
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


class ReportBody(object):
    pageWidth = 2160
    pageHeight = 2795

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

