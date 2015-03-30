#------------------------------------------------------------------------------
# srml2pdf
#   Simplified RML to PDF generator which translates RML (Report Markup
# Language) defined by the folks at ReportLab into a PDF document (in memory).
#------------------------------------------------------------------------------

import io

from reportlab.platypus.doctemplate import BaseDocTemplate, NextPageTemplate
from reportlab.platypus.doctemplate import PageTemplate as BasePageTemplate
from reportlab.platypus.doctemplate import FrameBreak
from reportlab.platypus.frames import Frame
from reportlab.platypus.flowables import PageBreak, Image, Spacer
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
            if methodName in ("drawCentredString", "drawRightString",
                    "drawString"):
                x, y, text = args
                text = text.replace("{pageNumber}",
                        str(canvas.getPageNumber()))
                args = (x, y, text)
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
    storyElementTags = """para nextFrame nextPage spacer setNextTemplate
            blockTable""".split()

    def __init__(self, output):
        self.output = output
        self.document = None
        self.pageTemplates = {}
        self.paragraphStyles = {}
        self.tableStyles = {}
        self.story = []
        self.tableRows = []
        self.tableCommands = []
        self.tableRowHeights = []

    def __ConvertNumber(self, value):
        try:
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
        except ValueError:
            raise Exception("Invalid number: '%s'" % value)

    def _ConvertColor(self, element, attrName, defaultColor = None):
        value = element.get(attrName)
        if value is not None:
            parts = [s.strip() for s in value.split(",")]
            if len(parts) == 1 and parts[0].isdigit():
                colorNumber = int(parts[0])
                red = (colorNumber % 256) / 255.0
                colorNumber //= 256
                green = (colorNumber % 256) / 255.0
                colorNumber //= 256
                blue = (colorNumber % 256) / 255.0
                return colors.toColor((red, green, blue))
            elif len(parts) in (3, 4):
                components = [float(s) / 255.0 for s in parts]
                return colors.toColor(components)
            return getattr(colors, value)
        return defaultColor

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
            element.attrib.clear()
            text = cElementTree.tostring(element)
            rotated = self._ConvertNumber(element, "rotate", 0)
            cls = RotatedParagraph if rotated else Paragraph
            para = cls(text, style)
            self.story.append(para)
        elif element.tag == "nextPage":
            self.story.append(PageBreak())
        elif element.tag == "nextFrame":
            self.story.append(FrameBreak())
        elif element.tag == "spacer":
            length = self._ConvertNumber(element, "length", 0)
            self.story.append(Spacer(length, length))
        elif element.tag == "setNextTemplate":
            name = element.attrib["name"]
            self.story.append(NextPageTemplate(name))
        elif element.tag == "blockTable":
            styleName = element.get("style", "default")
            style = self.tableStyles[styleName]
            if self.tableCommands:
                style = TableStyle(self.tableCommands, style)
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
        color = self._ConvertColor(element, "background")
        if color is not None:
            start = (0, len(self.tableRows))
            stop = (-1, len(self.tableRows))
            self.tableCommands.append(("BACKGROUND", start, stop, color))
        for cell in element:
            if cell.tag == "td":
                rowSpan = int(cell.get("rowspan", 1))
                colSpan = int(cell.get("colspan", 1))
                if rowSpan > 1 or colSpan > 1:
                    start = (len(cells), len(self.tableRows))
                    stop = (len(cells) + colSpan - 1,
                            len(self.tableRows) + rowSpan - 1)
                    self.tableCommands.append(("SPAN", start, stop))
                color = self._ConvertColor(cell, "background")
                if color is not None:
                    start = stop = (len(cells), len(self.tableRows))
                    self.tableCommands.append(("BACKGROUND", start, stop,
                            color))
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
                    elif child.tag == "img":
                        fileName = child.get("src", "unknown.png")
                        width = self._ConvertNumber(child, "width")
                        height = self._ConvertNumber(child, "height")
                        img = Image(fileName, width, height)
                        contents.append(img)
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
                color = self._ConvertColor(child, "textColor")
                if color is not None:
                    commands.append(("TEXTCOLOR", start, stop, color))
            elif child.tag == "blockValign":
                alignment = child.get("value", "BOTTOM")
                commands.append(("VALIGN", start, stop, alignment.upper()))
            elif child.tag == "lineStyle":
                kind = child.get("kind", "GRID")
                color = self._ConvertColor(child, "color", colors.black)
                thickness = self._ConvertNumber(child, "thickness", 1)
                cap = self._ConvertNumber(child, "cap", 1)
                dashes = self._ConvertNumberList(child, "dashes")
                commands.append((kind, start, stop, thickness, color, cap,
                        dashes))
            elif child.tag in ("blockLeftPadding", "blockRightPadding",
                    "blockBottomPadding", "blockTopPadding"):
                length = self._ConvertNumber(child, "length", 6)
                commandType = child.tag[5:].upper()
                commands.append((commandType, start, stop, length))
            elif child.tag == "background":
                color = self._ConvertColor(child, "color", colors.white)
                commands.append(("BACKGROUND", start, stop, color))
            elif child.tag == "nosplit":
                commands.append(("NOSPLIT", start, stop))
        style = TableStyle(commands)
        self.tableStyles[ident] = style
        return style

    def CreateDocumentTemplate(self, element):
        rawPageSize = element.get("pageSize", "LETTER")
        if rawPageSize.startswith("(") and rawPageSize.endswith(")"):
            pageSize = self._ConvertNumberList(element, "pageSize", [])
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
            elif child.tag in ("drawCentredString", "drawRightString",
                    "drawString"):
                x = self._ConvertNumber(child, "x", 0)
                y = self._ConvertNumber(child, "y", 0)
                text = child.text and child.text.strip() or ""
                args = (x, y, text)
            elif child.tag == "drawLine":
                x1 = self._ConvertNumber(child, "x1", 0)
                y1 = self._ConvertNumber(child, "y1", 0)
                x2 = self._ConvertNumber(child, "x2", 0)
                y2 = self._ConvertNumber(child, "y2", 0)
                args = (x1, y1, x2, y2)
                methodName = "line"
            elif child.tag == "setStrokeColor":
                color = self._ConvertColor(child, "color", colors.black)
                args = (color,)
            elif child.tag == "setLineWidth":
                width = self._ConvertNumber(child, "width", 1)
                args = (width,)
            elif child.tag == "setFillColor":
                color = self._ConvertColor(child, "color", colors.black)
                args = (color,)
            elif child.tag == "rect":
                x = self._ConvertNumber(child, "x", 0)
                y = self._ConvertNumber(child, "y", 0)
                width = self._ConvertNumber(child, "width", 100)
                height = self._ConvertNumber(child, "height", 10)
                stroke = self._ConvertNumber(child, "stroke", 1)
                fill = self._ConvertNumber(child, "fill", 0)
                args = (x, y, width, height, stroke, fill)
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
        borderColor = self._ConvertColor(element, "borderColor")
        textColor = self._ConvertColor(element, "textColor", colors.black)
        backColor = self._ConvertColor(element, "backColor")
        rawAlignment = element.get("alignment", "left")
        alignment = getattr(enums, "TA_%s" % rawAlignment.upper())
        style = ParagraphStyle(name, fontName = fontName, fontSize = fontSize,
                leading = leading, leftIndent = leftIndent,
                rightIndent = rightIndent, firstLineIndent = firstLineIndent,
                spaceBefore = spaceBefore, spaceAfter = spaceAfter,
                alignment = alignment, borderWidth = borderWidth,
                borderColor = borderColor, textColor = textColor,
                backColor = backColor)
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
        self.tableCommands = []
        self.tableRowHeights = []


def GeneratePDF(rmlInput, pdfOutput = None, inputIsString = True):
    if inputIsString:
        f = io.BytesIO()
        f.write(rmlInput.encode("utf-8"))
        f.seek(0)
        rmlInput = f
    if pdfOutput is None:
        pdfOutput = io.BytesIO()
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
        elif inTable and element.tag != "blockTable" \
                or inStory and element.tag not in context.storyElementTags:
            continue
        elif inStory:
            context.AddStoryElement(element)
            if element.tag == "blockTable":
                inTable = False
            element.clear()
    return context.Build()

