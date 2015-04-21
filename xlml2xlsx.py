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
import xlsxwriter.utility

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
        self.columnIndex = int(element.get("column_index", self.columnIndex))
        mergeAcross = int(element.get("merge_across", 0))
        mergeDown = int(element.get("merge_down", 0))
        if mergeAcross > 0 or mergeDown > 0:
            self.sheet.merge_range(self.rowIndex, self.columnIndex,
                    self.rowIndex + mergeDown, self.columnIndex + mergeAcross,
                    None, style)
        name = element.get("name")
        if name is not None:
            ref = xlsxwriter.utility.xl_rowcol_to_cell(self.rowIndex,
                    self.columnIndex, row_abs = True, col_abs = True)
            if element.get("start_range"):
                self.rangeNames[name] = ref
            else:
                startRef = self.rangeNames.get(name)
                if startRef is not None:
                    endRef = xlsxwriter.utility.xl_rowcol_to_cell( \
                            self.rowIndex + mergeDown,
                            self.columnIndex + mergeAcross, row_abs = True,
                            col_abs = True)
                    ref = "%s:%s" % (startRef, endRef)
                fullRef = "'%s'!%s" % (self.sheet.name, ref)
                if not element.get("global_name"):
                    name = "'%s'!%s" % (self.sheet.name, name)
                self.workbook.define_name(name, '=%s' % fullRef)
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
            if value is None:
                typeName = "blank"
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
        conditionalFormatNames = element.get("conditional_formats")
        if conditionalFormatNames is not None:
            for name in conditionalFormatNames.split(","):
                conditionalFormat = self.conditionalFormatDict[name]
                conditionalFormat.AddCell(self.rowIndex, self.columnIndex)
        self.columnIndex += mergeAcross + 1

    def AddChart(self, element):
        chart = Chart(self.sheet, element)
        self.charts.append(chart)

    def AddColumn(self, element):
        width = style = None
        rawWidth = element.get("width")
        if rawWidth is not None:
            width = float(rawWidth)
        styleName = element.get("style")
        if styleName is not None:
            style = self.styleDict[styleName]
        options = {}
        hidden = int(element.get("hidden", 0))
        if hidden:
            options["hidden"] = hidden
        self.sheet.set_column(self.columnIndex, self.columnIndex, width, style,
                options)
        self.columnIndex += 1

    def AddConditionalFormat(self, element):
        properties = {}
        name = "default"
        for attrName, value in element.items():
            if attrName == "name":
                name = value
            elif attrName == "style":
                properties["format"] = self.styleDict[value]
            else:
                properties[attrName] = value
        conditionalFormat = ConditionalFormat(name, properties)
        self.conditionalFormats.append(conditionalFormat)
        self.conditionalFormatDict[name] = conditionalFormat

    def AddRow(self, element):
        self.columnIndex = int(element.get("start_col", 0))
        self.rowIndex = int(element.get("row_index", self.rowIndex + 1))
        freeze = int(element.get("freeze", 0))
        height = style = None
        rawHeight = element.get("height")
        if rawHeight is not None:
            height = float(rawHeight)
        styleName = element.get("style")
        if styleName is not None:
            style = self.styleDict[styleName]
        if height is not None or style is not None:
            self.sheet.set_row(self.rowIndex, height, style)
        if freeze:
            self.sheet.freeze_panes(self.rowIndex + 1, 0)

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

    def BeginWorksheet(self, element):
        name = element.get("name")
        self.sheet = self.workbook.add_worksheet(name)
        self.rowIndex = -1
        self.columnIndex = 0
        self.conditionalFormats = []
        self.conditionalFormatDict = {}
        self.rangeNames = {}
        self.charts = []

    def Complete(self):
        self.workbook.close()

    def EndWorksheet(self):
        for conditionalFormat in self.conditionalFormats:
            conditionalFormat.AddToSheet(self.sheet)
        for chart in self.charts:
            chart.AddToSheet(self.workbook, self.sheet)


class ConditionalFormat(object):

    def __init__(self, name, properties):
        self.name = name
        self.properties = properties
        self.rowDict = {}

    def AddCell(self, rowIndex, colIndex):
        columns = self.rowDict.setdefault(rowIndex, [])
        if not columns:
            columns.append((colIndex, colIndex))
        else:
            startColIndex, endColIndex = columns[-1]
            if colIndex == endColIndex + 1:
                columns[-1] = (startColIndex, colIndex)
            else:
                columns.append((colIndex, colIndex))

    def AddToSheet(self, sheet):
        rowRanges = []
        for rowIndex in sorted(self.rowDict):
            columnRanges = self.rowDict[rowIndex]
            if not rowRanges:
                rowRanges.append((rowIndex, rowIndex, columnRanges))
                continue
            startRowIndex, endRowIndex, ranges = rowRanges[-1]
            if ranges == columnRanges and rowIndex == endRowIndex + 1:
                rowRanges[-1] = (startRowIndex, rowIndex, columnRanges)
            else:
                rowRanges.append((rowIndex, rowIndex, columnRanges))
        for startRowIndex, endRowIndex, columnRanges in rowRanges:
            for startColIndex, endColIndex in columnRanges:
                sheet.conditional_format(startRowIndex, startColIndex,
                        endRowIndex, endColIndex, self.properties)


class OptionsMetaClass(type):

    def __new__(cls, name, bases, classDict):
        for name in classDict:
            if name == "subOptionTags":
                value = classDict[name]
                classDict[name] = dict(value)
            elif name.endswith("OptionNames"):
                value = classDict[name]
                if isinstance(value, str):
                    classDict[name] = value.split()
        return type.__new__(cls, name, bases, classDict)


class Options(metaclass = OptionsMetaClass):
    stringOptionNames = ""
    floatOptionNames = ""
    intOptionNames = ""
    boolOptionNames = ""
    subOptionTags = []

    @classmethod
    def Get(cls, sheet, element):
        options = {}
        for name in cls.stringOptionNames:
            value = element.get(name)
            if value is not None:
                options[name] = value
        for name in cls.floatOptionNames:
            value = element.get(name)
            if value is not None:
                options[name] = float(value)
        for name in cls.intOptionNames:
            value = element.get(name)
            if value is not None:
                options[name] = int(value)
        for name in cls.boolOptionNames:
            value = element.get(name)
            if value is not None:
                options[name] = value.lower() in ("1", "true", "y")
        if cls.subOptionTags:
            for childElement in element:
                subOptionsClass = cls.subOptionTags.get(childElement.tag)
                if subOptionsClass is not None:
                    subOptions = subOptionsClass.Get(sheet, childElement)
                    options[childElement.tag] = subOptions
        return options


class RangeReference(object):

    @classmethod
    def Get(cls, sheet, element):
        sheetName = element.get("sheet_name", sheet.name)
        firstRow = int(element.get("first_row", 0))
        firstCol = int(element.get("first_col", 0))
        lastRow = int(element.get("last_row", 0))
        lastCol = int(element.get("last_col", 0))
        return [sheetName, firstRow, firstCol, lastRow, lastCol]


class FontOptions(Options):
    stringOptionNames = "name color"
    intOptionNames = "size rotation"
    boolOptionNames = "bold italic underline"


class AxisOptions(Options):
    floatOptionNames = "min max major_unit minor_unit"
    stringOptionNames = "num_format"
    subOptionTags = [
            ("name_font", FontOptions),
            ("num_font", FontOptions)
    ]


class DataLabelsOptions(Options):
    boolOptionNames = "series_name"
    stringOptionNames = "position"


class FillOptions(Options):
    stringOptionNames = "color"


class LayoutOptions(Options):
    floatOptionNames = "x y width height"


class LegendOptions(Options):
    stringOptionNames = "position"
    boolOptionNames = "none"
    subOptionTags = [
            ("font", FontOptions),
            ("layout", LayoutOptions)
    ]


class LineOptions(Options):
    stringOptionNames = "color dash_type"
    floatOptionNames = "width"
    boolOptionNames = "none"


class MarkerOptions(Options):
    stringOptionNames = "type"
    intOptionNames = "size"
    subOptionTags = [
            ("border", LineOptions),
            ("fill", FillOptions)
    ]


class PlotAreaOptions(Options):
    subOptionTags = [
            ("fill", FillOptions),
            ("layout", LayoutOptions)
    ]


class SeriesOptions(Options):
    stringOptionNames = "name values categories"
    subOptionTags = [
            ("values", RangeReference),
            ("categories", RangeReference),
            ("data_labels", DataLabelsOptions),
            ("fill", FillOptions),
            ("line", LineOptions),
            ("marker", MarkerOptions)
    ]


class SizeOptions(Options):
    floatOptionNames = "x_offset y_offset x_scale y_scale width height"


class TitleOptions(Options):
    stringOptionNames = "name"
    subOptionTags = [("name_font", FontOptions)]


class TypeOptions(Options):
    stringOptionNames = "type subtype"


class Chart(object):

    def __init__(self, sheet, element):
        self.row = int(element.get("row", 0))
        self.col = int(element.get("col", 0))
        self.typeOptions = TypeOptions.Get(sheet, element)
        self.sizeOptions = self.legendOptions = self.titleOptions = None
        self.plotAreaOptions = self.xAxisOptions = self.yAxisOptions = None
        self.x2AxisOptions = self.y2AxisOptions = None
        self.series = []
        for childElement in element:
            if childElement.tag == "series":
                self.series.append(SeriesOptions.Get(sheet, childElement))
            elif childElement.tag == "legend":
                self.legendOptions = LegendOptions.Get(sheet, childElement)
            elif childElement.tag == "plotarea":
                self.plotAreaOptions = PlotAreaOptions.Get(sheet, childElement)
            elif childElement.tag == "title":
                self.titleOptions = TitleOptions.Get(sheet, childElement)
            elif childElement.tag == "size":
                self.sizeOptions = SizeOptions.Get(sheet, childElement)
            elif childElement.tag == "x_axis":
                self.xAxisOptions = AxisOptions.Get(sheet, childElement)
            elif childElement.tag == "x2_axis":
                self.x2AxisOptions = AxisOptions.Get(sheet, childElement)
            elif childElement.tag == "y_axis":
                self.yAxisOptions = AxisOptions.Get(sheet, childElement)
            elif childElement.tag == "y2_axis":
                self.y2AxisOptions = AxisOptions.Get(sheet, childElement)

    def AddToSheet(self, workbook, sheet):
        chart = workbook.add_chart(self.typeOptions)
        for seriesOptions in self.series:
            chart.add_series(seriesOptions)
        if self.sizeOptions:
            chart.set_size(self.sizeOptions)
        if self.titleOptions:
            chart.set_title(self.titleOptions)
        if self.legendOptions:
            chart.set_legend(self.legendOptions)
        if self.plotAreaOptions:
            chart.set_plotarea(self.plotAreaOptions)
        if self.xAxisOptions:
            chart.set_x_axis(self.xAxisOptions)
        if self.x2AxisOptions:
            chart.set_x2_axis(self.x2AxisOptions)
        if self.yAxisOptions:
            chart.set_y_axis(self.yAxisOptions)
        if self.y2AxisOptions:
            chart.set_y2_axis(self.y2AxisOptions)
        sheet.insert_chart(self.row, self.col, chart)


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
                context.BeginWorksheet(element)
            elif element.tag == "row":
                context.AddRow(element)
            elif element.tag == "chart":
                context.AddChart(element)
        elif element.tag == "style":
            context.AddStyle(element)
        elif element.tag == "conditional_format":
            context.AddConditionalFormat(element)
        elif element.tag == "column":
            context.AddColumn(element)
        elif element.tag == "cell":
            context.AddCell(element)
        elif element.tag == "worksheet":
            context.EndWorksheet()
    context.Complete()
    return xlOutput

