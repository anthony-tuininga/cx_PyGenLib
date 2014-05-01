#------------------------------------------------------------------------------
# srml2pdf
#   Simplified RML to PDF generator which translates RML (Report Markup
# Language) defined by the folks at ReportLab into a PDF document (in memory).
#------------------------------------------------------------------------------

import cStringIO

from reportlab.platypus.doctemplate import BaseDocTemplate, NextPageTemplate
from reportlab.platypus.doctemplate import PageTemplate as BasePageTemplate
from reportlab.platypus.frames import Frame
from reportlab.platypus.flowables import PageBreak
from reportlab.platypus.paragraph import Paragraph
from reportlab.platypus.tables import LongTable, TableStyle
from reportlab.lib import colors, enums, pagesizes, units
from reportlab.lib.styles import ParagraphStyle
from xml.etree import cElementTree

class DocTemplate(BaseDocTemplate):
    pass


class PageTemplate(BasePageTemplate):

    def __init__(self, **args):
        BasePageTemplate.__init__(self, **args)
        self.directives = []

    def beforeDrawPage(self, canvas, document):
        for methodName, args in self.directives:
            method = getattr(canvas, methodName)
            method(*args)


class RotatedParagraph(Paragraph):

    def draw(self):
        self.canv.rotate(90)
        self.canv.translate(1, -self.height)
        Paragraph.draw(self)

    def wrap(self, availableWidth, availableHeight):
        width, height = Paragraph.wrap(self, availableHeight, availableWidth)
        return height, width


class Context(object):

    def __init__(self, output):
        self.output = output
        self.document = None
        self.pageTemplates = {}
        self.paragraphStyles = {}
        self.tableStyles = {}
        self.story = []
        self.tableRows = []
        self.tableRowHeights = []

    def __ConvertNumber(self, value):
        if value.endswith("mm"):
            num = float(value[:-2])
            return num * units.mm
        elif value.endswith("cm"):
            num = float(value[:-2])
            return num * units.cm
        elif value.endswith("in"):
            num = float(value[:-2])
            return num * units.inch
        elif value in ("splitfirst", "splitlast"):
            return value
        elif value.lstrip("-").isdigit():
            return int(value)
        return float(value)

    def _ConvertNumber(self, element, attrName, defaultValue = None):
        value = element.get(attrName)
        if value is None:
            return defaultValue
        return self.__ConvertNumber(value)

    def _ConvertNumberList(self, element, attrName, defaultValue = None):
        value = element.get(attrName)
        if value is None:
            return defaultValue
        if value.startswith("(") and value.endswith(")"):
            value = value[1:-1]
        return [self.__ConvertNumber(p) for p in value.split(",")]

    def AddStoryElement(self, element):
        if element.tag == "para":
            styleName = element.get("style", "default")
            style = self.paragraphStyles[styleName]
            text = element.text.strip()
            rotated = self._ConvertNumber(element, "rotate", 0)
            cls = RotatedParagraph if rotated else Paragraph
            para = cls(text, style)
            self.story.append(para)
        elif element.tag == "nextPage":
            self.story.append(PageBreak())
        elif element.tag == "setNextTemplate":
            name = element.attrib["name"]
            self.story.append(NextPageTemplate(name))
        elif element.tag == "blockTable":
            styleName = element.get("style", "default")
            style = self.tableStyles[styleName]
            repeatRows = self._ConvertNumber(element, "repeatRows", 0)
            hAlign = element.get("hAlign", "CENTER")
            vAlign = element.get("vAlign", "MIDDLE")
            columnWidths = self._ConvertNumberList(element, "colWidths", [])
            pageRows = self._ConvertNumber(element, "pageRows")
            if not pageRows:
                self.story.append(LongTable(self.tableRows, columnWidths,
                        self.tableRowHeights, style = style, hAlign = hAlign,
                        vAlign = vAlign, repeatRows = repeatRows))
            else:
                headerRows = self.tableRows[:repeatRows]
                headerRowHeights = self.tableRowHeights[:repeatRows]
                rows = self.tableRows[repeatRows:]
                rowHeights = self.tableRowHeights[repeatRows:]
                while rows:
                    table = LongTable(headerRows + rows[:pageRows],
                            columnWidths,
                            headerRowHeights + rowHeights[:pageRows],
                            style = style, hAlign = hAlign, vAlign = vAlign)
                    self.story.append(table)
                    rows = rows[pageRows:]
                    rowHeights = rowHeights[pageRows:]

    def AddTableRow(self, element):
        cells = []
        for cell in element:
            if cell.tag == "td":
                contents = []
                for child in cell:
                    if child.tag == "para":
                        styleName = child.get("style", "default")
                        rotated = self._ConvertNumber(child, "rotate")
                        style = self.paragraphStyles[styleName]
                        child.attrib.clear()
                        text = cElementTree.tostring(child)
                        cls = RotatedParagraph if rotated else Paragraph
                        para = cls(text, style)
                        contents.append(para)
                if not contents:
                    contents = cell.text and cell.text.strip()
                cells.append(contents)
        height = self._ConvertNumber(element, "height")
        self.tableRows.append(cells)
        self.tableRowHeights.append(height)

    def Build(self):
        self.document.build(self.story)
        return self.output

    def CreateBlockTableStyle(self, element):
        commands = []
        ident = element.get("id", "default")
        for child in element:
            start = self._ConvertNumberList(child, "start", (0,0))
            stop = self._ConvertNumberList(child, "stop", (-1,-1))
            if child.tag == "blockAlignment":
                alignment = child.get("value", "LEFT")
                commands.append(("ALIGN", start, stop, alignment.upper()))
            elif child.tag == "blockFont":
                fontName = child.get("name", "Helvetica")
                fontSize = self._ConvertNumber(child, "size")
                leading = self._ConvertNumber(child, "leading")
                if leading:
                    args = (fontName, fontSize or 10, leading)
                elif fontSize:
                    args = (fontName, fontSize)
                else:
                    args = (fontName,)
                commands.append(("FONT", start, stop) + args)
            elif child.tag == "blockValign":
                alignment = child.get("value", "BOTTOM")
                commands.append(("VALIGN", start, stop, alignment.upper()))
            elif child.tag == "lineStyle":
                kind = child.get("kind", "GRID")
                colorName = child.get("colorName", "black")
                thickness = self._ConvertNumber(child, "thickness", 1)
                color = getattr(colors, colorName)
                commands.append((kind, start, stop, thickness, color))
            elif child.tag in ("blockLeftPadding", "blockRightPadding",
                    "blockBottomPadding", "blockTopPadding"):
                length = self._ConvertNumber(child, "length", 6)
                commandType = child.tag[5:].upper()
                commands.append((commandType, start, stop, length))
        style = TableStyle(commands)
        self.tableStyles[ident] = style
        return style

    def CreateDocumentTemplate(self, element):
        rawPageSize = element.get("pageSize", "LETTER")
        if rawPageSize.startswith("(") and rawPageSize.endswith(")"):
            pageSize = tuple(float(s.strip()) \
                    for s in rawPageSize[1:-1].split(","))
        else:
            pageSize = getattr(pagesizes, rawPageSize)
        leftMargin = self._ConvertNumber(element, "leftMargin", units.inch)
        rightMargin = self._ConvertNumber(element, "rightMargin", units.inch)
        topMargin = self._ConvertNumber(element, "topMargin", units.inch)
        bottomMargin = self._ConvertNumber(element, "bottomMargin", units.inch)
        showBoundary = self._ConvertNumber(element, "showBoundary", 0)
        allowSplitting = self._ConvertNumber(element, "allowSplitting", 1)
        self.document = DocTemplate(self.output,
                pagesize = pageSize, showBoundary = showBoundary,
                allowSplitting = allowSplitting, leftMargin = leftMargin,
                rightMargin = rightMargin, topMargin = topMargin,
                bottomMargin = bottomMargin)
        for child in element:
            if child.tag == "pageTemplate":
                self.CreatePageTemplate(child)

    def CreateFrame(self, pageTemplate, element):
        ident = element.get("id", "default")
        x1 = self._ConvertNumber(element, "x1", 0)
        y1 = self._ConvertNumber(element, "y1", 0)
        defaultWidth, defaultHeight = self.document.pagesize
        width = self._ConvertNumber(element, "width", defaultWidth)
        height = self._ConvertNumber(element, "height", defaultHeight)
        leftPadding = self._ConvertNumber(element, "leftPadding", 0)
        rightPadding = self._ConvertNumber(element, "rightPadding", 0)
        topPadding = self._ConvertNumber(element, "topPadding", 0)
        bottomPadding = self._ConvertNumber(element, "bottomPadding", 0)
        showBoundary = self._ConvertNumber(element, "showBoundary", 0)
        frame = Frame(x1, y1, width, height, leftPadding = leftPadding,
                rightPadding = rightPadding, topPadding = topPadding,
                bottomPadding = bottomPadding, showBoundary = showBoundary)
        pageTemplate.frames.append(frame)

    def CreatePageGraphics(self, pageTemplate, element):
        for child in element:
            methodName = child.tag
            if child.tag == "setFont":
                name = child.get("name", "Helvetica")
                size = self._ConvertNumber(child, "size", 10)
                args = (name, size)
            elif child.tag in ("drawCentredString", "drawString"):
                x = self._ConvertNumber(child, "x", 0)
                y = self._ConvertNumber(child, "y", 0)
                args = (x, y, child.text.strip())
            elif child.tag == "drawLine":
                x1 = self._ConvertNumber(child, "x1", 0)
                y1 = self._ConvertNumber(child, "y1", 0)
                x2 = self._ConvertNumber(child, "x2", 0)
                y2 = self._ConvertNumber(child, "y2", 0)
                args = (x1, y1, x2, y2)
                methodName = "line"
            elif child.tag == "setStrokeColor":
                colorName = child.get("color", "black")
                color = getattr(colors, colorName)
                args = (color,)
            elif child.tag == "image":
                fileName = child.get("file", "unknown.png")
                x = self._ConvertNumber(child, "x", 0)
                y = self._ConvertNumber(child, "y", 0)
                width = self._ConvertNumber(child, "width")
                height = self._ConvertNumber(child, "height")
                preserveAspectRatio = self._ConvertNumber(child,
                        "preserveAspectRatio", False)
                methodName = "drawImage"
                args = (fileName, x, y, width, height, None,
                        preserveAspectRatio)
            pageTemplate.directives.append((methodName, args))

    def CreatePageTemplate(self, element):
        ident = element.get("id", "default")
        pageTemplate = PageTemplate(id = ident,
                pagesize = self.document.pagesize)
        for child in element:
            if child.tag == "frame":
                self.CreateFrame(pageTemplate, child)
            elif child.tag == "pageGraphics":
                self.CreatePageGraphics(pageTemplate, child)
        self.pageTemplates[ident] = pageTemplate
        self.document.addPageTemplates([pageTemplate])
        return pageTemplate

    def CreateParagraphStyle(self, element):
        name = element.get("name", "default")
        fontName = element.get("fontName", "Helvetica")
        fontSize = self._ConvertNumber(element, "fontSize", 10)
        leading = self._ConvertNumber(element, "leading", 12)
        leftIndent = self._ConvertNumber(element, "leftIndent", 0)
        rightIndent = self._ConvertNumber(element, "rightIndent", 0)
        firstLineIndent = self._ConvertNumber(element, "firstLineIndent", 0)
        spaceBefore = self._ConvertNumber(element, "spaceBefore", 0)
        spaceAfter = self._ConvertNumber(element, "spaceAfter", 0)
        borderWidth = self._ConvertNumber(element, "borderWidth")
        borderColorName = element.get("borderColor")
        borderColor = getattr(colors, borderColorName) \
                if borderColorName is not None else None
        rawAlignment = element.get("alignment", "left")
        alignment = getattr(enums, "TA_%s" % rawAlignment.upper())
        style = ParagraphStyle(name, fontName = fontName, fontSize = fontSize,
                leading = leading, leftIndent = leftIndent,
                rightIndent = rightIndent, firstLineIndent = firstLineIndent,
                spaceBefore = spaceBefore, spaceAfter = spaceAfter,
                alignment = alignment, borderWidth = borderWidth,
                borderColor = borderColor)
        style.keepWithNext = self._ConvertNumber(element, "keepWithNext", 0)
        self.paragraphStyles[name] = style
        return style

    def CreateStylesheet(self, element):
        for child in element:
            if child.tag == "paraStyle":
                self.CreateParagraphStyle(child)
            elif child.tag == "blockTableStyle":
                self.CreateBlockTableStyle(child)

    def StartTable(self):
        self.tableRows = []
        self.tableRowHeights = []


def GeneratePDF(rmlInput, pdfOutput = None, inputIsString = True):
    if inputIsString:
        f = cStringIO.StringIO()
        f.write(rmlInput)
        f.seek(0)
        rmlInput = f
    if pdfOutput is None:
        pdfOutput = cStringIO.StringIO()
    inStory = inTable = False
    context = Context(pdfOutput)
    for event, element in cElementTree.iterparse(rmlInput,
            events = ("start", "end")):
        if event == "start":
            if element.tag == "story":
                inStory = True
            elif element.tag == "blockTable":
                context.StartTable()
                inTable = True
        elif element.tag == "template":
            context.CreateDocumentTemplate(element)
            element.clear()
        elif element.tag == "stylesheet":
            context.CreateStylesheet(element)
            element.clear()
        elif element.tag == "story":
            element.clear()
            inStory = False
        elif element.tag == "tr":
            context.AddTableRow(element)
            element.clear()
        elif inTable and element.tag != "blockTable":
            continue
        elif inStory:
            context.AddStoryElement(element)
            if element.tag == "blockTable":
                inTable = False
            element.clear()
    return context.Build()
