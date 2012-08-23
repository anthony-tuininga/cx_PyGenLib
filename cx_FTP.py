#------------------------------------------------------------------------------
# cx_FTP.py
#   Module which permits transfer of files via FTP.
#------------------------------------------------------------------------------

import ftplib, os, string, time

#------------------------------------------------------------------------------
# Connection
#   Handles FTP connections.
#------------------------------------------------------------------------------
class Connection:

  #----------------------------------------------------------------------------
  # __init__()
  #   Constructor.
  #----------------------------------------------------------------------------
  def __init__(self, a_Host, a_User, a_Password):
    self.i_Host = a_Host
    self.i_User = a_User
    self.i_Password = a_Password
    self.i_Connection = None

  #----------------------------------------------------------------------------
  # Connect()
  #   Connect to the FTP server.
  #----------------------------------------------------------------------------
  def Connect(self):
    self.i_Connection = ftplib.FTP(self.i_Host, self.i_User, self.i_Password)

  #----------------------------------------------------------------------------
  # Disconnect()
  #   Disconnect from the FTP server.
  #----------------------------------------------------------------------------
  def Disconnect(self):
    if self.i_Connection:
      self.i_Connection.close()
      self.i_Connection = None

  #----------------------------------------------------------------------------
  # AppendFile()
  #   Callback which parses an FTP listing line and appends the name of a file
  # to the list of files kept on the instance of the class. Note that the
  # special entries "." and ".." are ignored as well.
  #----------------------------------------------------------------------------
  def AppendFile(self, a_Line):
    if a_Line[:5] == "total":
      return
    v_File, = string.split(a_Line)[-1:]
    if v_File in (".", ".."):
      return
    self.i_Files.append(v_File)

  #----------------------------------------------------------------------------
  # TransferData()
  #   Callback which writes a block of data to the file currently open.
  #----------------------------------------------------------------------------
  def TransferData(self, a_Data):
    self.i_File.write(a_Data)

  #----------------------------------------------------------------------------
  # DownloadFile()
  #   Download a file from the FTP server. Once the download is complete, the
  # file is moved to the processed directory (if it exists) or deleted.
  #----------------------------------------------------------------------------
  def DownloadFile(self, a_FileName, a_ProcessedDir):
    print "  Downloading", a_FileName
    self.i_File = open(a_FileName, "w+b")
    self.i_Connection.retrbinary("RETR " + a_FileName, self.TransferData)
    self.i_File.close()
    if a_ProcessedDir:
      self.i_Connection.rename(a_FileName, a_ProcessedDir + "/" + a_FileName)
    else:
      self.i_Connection.delete(a_FileName)

  #----------------------------------------------------------------------------
  # UploadFile()
  #   Upload a file to the FTP server. Once the upload is complete, the file is
  # moved to the processed directory (if it exists) or deleted.
  #----------------------------------------------------------------------------
  def UploadFile(self, a_FileName, a_ProcessedDir):
    print "  Uploading", a_FileName
    v_File = open(a_FileName, "rb")
    self.i_Connection.storbinary("STOR " + a_FileName, v_File, 8192)
    v_File.close()
    if a_ProcessedDir:
      os.rename(a_FileName, os.path.join(a_ProcessedDir, a_FileName))
    else:
      os.remove(a_FileName)

  #----------------------------------------------------------------------------
  # Download()
  #   Download all of the files in the remote directory to the local directory.
  #----------------------------------------------------------------------------
  def Download(self, a_LocalDir, a_RemoteDir, a_ProcessedDir):
    os.chdir(a_LocalDir)
    self.i_Connection.cwd(a_RemoteDir)
    self.i_Files = []
    self.i_Connection.retrlines("LIST", self.AppendFile)
    for v_File in self.i_Files:
      try:
        self.DownloadFile(v_File, a_ProcessedDir)
      except:
        pass
    return (len(self.i_Files) > 0)

  #----------------------------------------------------------------------------
  # Upload()
  #   Upload all of the files in the local directory to the remote directory.
  #----------------------------------------------------------------------------
  def Upload(self, a_LocalDir, a_RemoteDir, a_ProcessedDir):
    os.chdir(a_LocalDir)
    self.i_Connection.cwd(a_RemoteDir)
    v_Files = os.listdir(a_LocalDir)
    for v_File in v_Files:
      try:
        self.UploadFile(v_File, a_ProcessedDir)
      except:
        pass
    return (len(v_Files) > 0)

#------------------------------------------------------------------------------
# Control
#   Handles controlling an FTP connection.
#------------------------------------------------------------------------------
class Control:

  #----------------------------------------------------------------------------
  # __init__()
  #   Constructor.
  #----------------------------------------------------------------------------
  def __init__(self, a_Connection, a_IniFile, a_Name):
    self.i_Name = a_Name
    v_Operation = a_IniFile.Value(a_Name, "Operation")
    if v_Operation == "Download":
      self.i_Function = a_Connection.Download
    elif v_Operation == "Upload":
      self.i_Function = a_Connection.Upload
    else:
      raise 'Operation must be one of "Download" or "Upload"'
    self.i_RemoteDir = a_IniFile.Value(a_Name, "RemoteDir")
    self.i_LocalDir = a_IniFile.Value(a_Name, "LocalDir")
    self.i_ProcessedDir = a_IniFile.Value(a_Name, "ProcessedDir")
    self.i_LastProcessed = None

  #----------------------------------------------------------------------------
  # Process()
  #   Perform the upload or the download as appropriate.
  #----------------------------------------------------------------------------
  def Process(self, a_TimeFormat):
    v_Desc = self.i_Name
    if self.i_LastProcessed:
      v_Desc += " (" + \
          time.strftime(a_TimeFormat, self.i_LastProcessed) + ")"
    print "Processing", v_Desc
    v_DidSomething = apply(self.i_Function,
        (self.i_LocalDir, self.i_RemoteDir, self.i_ProcessedDir))
    if v_DidSomething:
      self.i_LastProcessed = time.localtime(time.time())

