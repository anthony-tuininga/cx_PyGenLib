#------------------------------------------------------------------------------
# cx_PrettyPrinter.py
#   Module which provides routines for pretty printing.
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
# PrettyPrinter
#   Class which handles pretty printing.
#------------------------------------------------------------------------------
class PrettyPrinter:

  #----------------------------------------------------------------------------
  # __init__()
  #   Constructor.
  #----------------------------------------------------------------------------
  def __init__(self, a_File, a_SpacesPerIndent = 2, a_MaxLineWidth = 79,
      a_RestIndentSpaces = 4):
    self.i_Line = ""
    self.i_File = a_File
    self.i_SpacesPerIndent = a_SpacesPerIndent
    self.i_MaxLineWidth = a_MaxLineWidth
    self.SetIndentLevels(0, a_RestIndentSpaces)

  #----------------------------------------------------------------------------
  # SetIndentLevels()
  #   Set the indent levels.
  #----------------------------------------------------------------------------
  def SetIndentLevels(self, a_FirstIndentSpaces = -1, a_RestIndentSpaces = -1):
    if a_FirstIndentSpaces >= 0:
      self.i_FirstIndentSpaces = a_FirstIndentSpaces
      self.i_FirstIndentString = " " * self.i_FirstIndentSpaces
    if a_RestIndentSpaces >= 0:
      self.i_RestIndentSpaces = a_RestIndentSpaces
    self.i_RestIndentString = \
        " " * (self.i_FirstIndentSpaces + self.i_RestIndentSpaces)

  #----------------------------------------------------------------------------
  # Indent()
  #   Add one level of indentation to subsequent output
  #----------------------------------------------------------------------------
  def Indent(self):
    self.SetIndentLevels(self.i_FirstIndentSpaces + self.i_SpacesPerIndent)

  #----------------------------------------------------------------------------
  # Unindent()
  #   Remove one level of indentation to subsequent output.
  #----------------------------------------------------------------------------
  def Unindent(self):
    self.SetIndentLevels(self.i_FirstIndentSpaces - self.i_SpacesPerIndent)

  #----------------------------------------------------------------------------
  # OutputLine()
  #   Output the line.
  #----------------------------------------------------------------------------
  def OutputLine(self):
    if self.i_Line:
      self.i_Line = self.i_FirstIndentString + self.i_Line
    while len(self.i_Line) > self.i_MaxLineWidth:
      v_Pos = self.i_Line[:self.i_MaxLineWidth].rfind(" ")
      if v_Pos < 0 or not self.i_Line[:v_Pos].strip():
        v_Pos = self.i_Line[:self.i_MaxLineWidth].rfind("(") + 1
        if v_Pos == 0:
          break
      print >> self.i_File, self.i_Line[:v_Pos].rstrip()
      self.i_Line = self.i_RestIndentString + self.i_Line[v_Pos:].lstrip()
    print >> self.i_File, self.i_Line.rstrip()
    self.i_Line = ""

  #----------------------------------------------------------------------------
  # write()
  #   Handles the writing of strings to the output.
  #----------------------------------------------------------------------------
  def write(self, a_Value):
    v_First = 1
    for v_Line in a_Value.split("\n"):
      if v_First:
        v_First = 0
      else:
        self.OutputLine()
      self.i_Line += v_Line

