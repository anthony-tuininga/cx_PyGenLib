"""
Define commonly used dialogs.
"""

import ceGUI
import cx_Logging
import os
import wx

__all__ = [ "AboutDialog", "PreferencesDialog" ]


class AboutDialog(ceGUI.Dialog):
    baseSettingsName = "w_About"
    createCancelButton = False
    saveSize = False

    def __init__(self, parent):
        app = wx.GetApp()
        title = "About %s" % app.description
        wx.Dialog.__init__(self, parent, -1, title, style = wx.CAPTION)
        self._Initialize()

    def OnCreate(self):
        app = wx.GetApp()
        self.panel = Panel(self, -1, style = wx.SUNKEN_BORDER)
        aboutText = app.description
        if app.version is not None:
            aboutText = "%s\n\nVersion %s" % (aboutText, app.version)
        if app.copyrightOwner is not None:
            if app.copyrightStartYear == app.copyrightEndYear:
                copyrightYears = app.copyrightEndYear
            else:
                copyrightYears = "%s-%s" % \
                        (app.copyrightStartYear, app.copyrightEndYear)
            aboutText = "%s\n\nCopyright %s\n%s" % \
                    (aboutText, copyrightYears, app.copyrightOwner)
        self.aboutLabel = wx.StaticText(self.panel, -1, aboutText,
                style = wx.ALIGN_CENTRE)

    def OnLayout(self):
        panelSizer = wx.BoxSizer(wx.VERTICAL)
        panelSizer.Add(self.aboutLabel, flag = wx.ALL | wx.EXPAND, border = 5)
        self.panel.SetSizer(panelSizer)
        topSizer = wx.BoxSizer(wx.VERTICAL)
        topSizer.Add(self.panel, flag = wx.ALL | wx.EXPAND, border = 5)
        topSizer.Add(self.okButton,
                flag = wx.ALL | wx.ALIGN_CENTER_HORIZONTAL | \
                        wx.ALIGN_CENTER_VERTICAL, border = 5)
        return topSizer


class LoggingPreferencesPane(ceGUI.Panel):
    loggingLevels = "DEBUG INFO WARNING ERROR CRITICAL".split()

    def OnCreate(self):
        self.fileNameLabel = wx.StaticText(self, -1, "File Name:")
        self.fileNameField = wx.TextCtrl(self, -1)
        self.selectFileNameButton = wx.Button(self, -1, "...",
                size = (25, -1))
        self.BindEvent(self.selectFileNameButton, wx.EVT_BUTTON,
                self.OnSelectFileName)
        self.levelLabel = wx.StaticText(self, -1, "Level:")
        self.levelField = wx.Choice(self, -1, choices = self.loggingLevels)

    def OnLayout(self):
        fileNameSizer = wx.BoxSizer(wx.HORIZONTAL)
        fileNameSizer.Add(self.fileNameLabel,
                flag = wx.LEFT | wx.RIGHT | wx.TOP | wx.ALIGN_CENTER_VERTICAL,
                border = 5)
        fileNameSizer.Add(self.fileNameField, proportion = 1,
                flag = wx.LEFT | wx.RIGHT | wx.TOP | wx.ALIGN_CENTER_VERTICAL,
                border = 5)
        fileNameSizer.Add(self.selectFileNameButton,
                flag = wx.LEFT | wx.RIGHT | wx.TOP | wx.ALIGN_CENTER_VERTICAL,
                border = 5)
        levelSizer = wx.BoxSizer(wx.HORIZONTAL)
        levelSizer.Add(self.levelLabel,
                flag = wx.ALL | wx.ALIGN_CENTER_VERTICAL, border = 5)
        levelSizer.Add(self.levelField,
                flag = wx.ALL | wx.ALIGN_CENTER_VERTICAL, border = 5)
        topSizer = wx.BoxSizer(wx.VERTICAL)
        topSizer.Add(fileNameSizer, flag = wx.EXPAND)
        topSizer.Add(levelSizer)
        return topSizer

    def OnSelectFileName(self, event):
        currentFileName = self.fileNameField.GetValue()
        dir, fileName = os.path.split(currentFileName)
        dialog = wx.FileDialog(self, "Select log file", wildcard = "*.log",
                defaultDir = dir, defaultFile = fileName,
                style = wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
        if dialog.ShowModal() == wx.ID_OK:
            fileName = dialog.GetPath()
            if not fileName.lower().endswith(".log"):
                fileName += ".log"
            self.fileNameField.SetValue(fileName)

    def RestoreSettings(self):
        defaultFileName = wx.GetApp().GetDefaultLoggingFileName()
        fileName = self.settings.Read("LogFileName", defaultFileName)
        self.fileNameField.SetValue(fileName)
        levelName = self.settings.Read("LogLevel", "ERROR")
        self.levelField.SetStringSelection(levelName)

    def SaveSettings(self):
        fileName = self.fileNameField.GetValue()
        if not fileName:
            self.fileNameField.SetFocus()
            raise LoggingFileNameNotSpecified()
        levelName = self.levelField.GetStringSelection()
        level = getattr(cx_Logging, levelName)
        if fileName != cx_Logging.GetLoggingFileName():
            cx_Logging.StartLogging(fileName, level)
        elif level != cx_Logging.GetLoggingLevel():
            cx_Logging.SetLoggingLevel(level)
        self.settings.Write("LogFileName", fileName)
        self.settings.Write("LogLevel", levelName)


class PreferencesDialog(ceGUI.Dialog):
    baseSettingsName = "w_Preferences"
    minSize = (450, 145)

    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, "Edit Preferences",
                style = wx.CAPTION | wx.RESIZE_BORDER)
        self._Initialize()

    def OnCreate(self):
        self.notebook = ceGUI.Notebook(self, -1)
        self.OnCreateNotebook()
        pane = LoggingPreferencesPane(self.notebook)
        self.notebook.AddPage(pane, "Logging")
        self.notebook.RestoreSettings()

    def OnCreateNotebook(self):
        pass

    def OnOk(self):
        self.notebook.SaveSettings()
        self.settings.Flush()

    def OnLayout(self):
        buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
        buttonSizer.AddStretchSpacer()
        buttonSizer.Add(self.okButton,
                flag = wx.ALL | wx.ALIGN_CENTER_VERTICAL, border = 5)
        buttonSizer.Add(self.cancelButton,
                flag = wx.ALL | wx.ALIGN_CENTER_VERTICAL, border = 5)
        topSizer = wx.BoxSizer(wx.VERTICAL)
        topSizer.Add(self.notebook, proportion = 1, flag = wx.EXPAND)
        topSizer.Add(buttonSizer, flag = wx.EXPAND)
        return topSizer

