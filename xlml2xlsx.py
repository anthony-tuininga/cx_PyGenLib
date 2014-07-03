#------------------------------------------------------------------------------
# xlml2xlsx
#   Translates XLML (Excel Markup Language) defined to mirror the capabilities
# of the xlsxwriter module to an Excel document using the xlsxwriter module.
# This conversion is done in memory to facilitate use by web servers.
#------------------------------------------------------------------------------

import datetime
import decimal
import io
import re
import xlsxwriter

from xml.etree import cElementTree

class Context(object):
    styleBooleanAttrNames = """bold italic underline font_strikeout text_wrap
            shrink""".split()
    styleIntegerAttrNames = """font_size font_script rotation indent pattern
            border bottom top left right""".split()

    def __init__(self, output):
        self.formulaPattern = re.compile("R(\[-?\d+\])?C(\[-?\d+\])?")
        self.workbook = xlsxwriter.Workbook(output, dict(in_memory = True))
        self.sheet = None
        self.styleDict = {}
        self.rowIndex = -1
        self.columnIndex = 0

    def __SubstituteFormula(self, match):
        rowString = match.group(1)
        rowOffset = 0 if rowString is None else int(rowString[1:-1])
        colString = match.group(2)
        colOffset = 0 if colString is None else int(colString[1:-1])
        return xlsxwriter.utility.xl_rowcol_to_cell(self.rowIndex + rowOffset,
                self.columnIndex + colOffset)

    def AddCell(self, element):
        style = None
        styleName = element.get("style")
        if styleName is not None:
            style = self.styleDict[styleName]
        mergeAcross = int(element.get("merge_across", 0))
        mergeDown = int(element.get("merge_down", 0))
        if mergeAcross > 0 or mergeDown > 0:
            self.sheet.merge_range(self.rowIndex, self.columnIndex,
                    self.rowIndex + mergeDown, self.columnIndex + mergeAcross,
                    None, style)
        formula = element.get("formula")
        if formula is not None:
            adjustedFormula = self.formulaPattern.sub(self.__SubstituteFormula,
                    formula)
            self.sheet.write_formula(self.rowIndex, self.columnIndex,
                    adjustedFormula, style)
        else:
            value = element.text
            if value is not None:
                value = value.strip()
            defaultTypeName = "string" if value else "blank"
            typeName = element.get("type", defaultTypeName)
            methodName = "write_%s" % typeName
            method = getattr(self.sheet, methodName)
            if typeName == "number":
                value = decimal.Decimal(value)
            elif typeName == "datetime":
                if len(value) == 10:
                    value = datetime.datetime.strptime(value, "%Y-%m-%d")
                else:
                    value = datetime.datetime.strptime(value,
                            "%Y-%m-%d %H:%M:%S")
            method(self.rowIndex, self.columnIndex, value, style)
        self.columnIndex += mergeAcross + 1

    def AddColumn(self, element):
        width = style = None
        rawWidth = element.get("width")
        if rawWidth is not None:
            width = float(rawWidth)
        styleName = element.get("style")
        if styleName is not None:
            style = self.styleDict[styleName]
        self.sheet.set_column(self.columnIndex, self.columnIndex, width, style)
        self.columnIndex += 1

    def AddRow(self, element):
        self.rowIndex += 1
        self.columnIndex = int(element.get("start_col", 0))
        height = style = None
        rawHeight = element.get("height")
        if rawHeight is not None:
            height = int(rawHeight)
        styleName = element.get("style")
        if styleName is not None:
            style = self.styleDict[styleName]
        self.sheet.set_row(self.rowIndex, height, style)

    def AddStyle(self, element):
        name = "default"
        properties = {}
        for attrName, rawValue in element.items():
            if attrName in self.styleBooleanAttrNames:
                value = True
            elif attrName in self.styleIntegerAttrNames:
                value = int(rawValue)
            else:
                value = rawValue
            if attrName == "name":
                name = value
            else:
                properties[attrName] = value
        self.styleDict[name] = self.workbook.add_format(properties)

    def AddWorksheet(self, element):
        name = element.get("name")
        self.sheet = self.workbook.add_worksheet(name)
        self.rowIndex = -1
        self.columnIndex = 0

    def Complete(self):
        self.workbook.close()


def GenerateXL(xlmlInput, xlOutput = None, inputIsString = True):
    if inputIsString:
        f = io.BytesIO()
        f.write(xlmlInput.encode("utf-8"))
        f.seek(0)
        xlmlInput = f
    if xlOutput is None:
        xlOutput = io.BytesIO()
    context = Context(xlOutput)
    for event, element in cElementTree.iterparse(xlmlInput,
            events = ("start", "end")):
        if event == "start":
            if element.tag == "worksheet":
                context.AddWorksheet(element)
            elif element.tag == "row":
                context.AddRow(element)
        elif element.tag == "style":
            context.AddStyle(element)
        elif element.tag == "column":
            context.AddColumn(element)
        elif element.tag == "cell":
            context.AddCell(element)
    context.Complete()
    return xlOutput

