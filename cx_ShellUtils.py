"""Defines functions for standard shell operations that are common on Unix but
   are not readily available on Windows in a cross platform way; this is
   intended to replace shutil which is less usable for copying and removing
   trees."""

import cx_Logging
import os
import stat
import sys

def CopyFile(source, target, bufferSize = 16 * 1024, log = True):
    """Copy the source to the target."""
    if log:
        cx_Logging.Info("copying %s to %s...", source, target)
    sourceFile = open(source, "rb")
    if os.path.exists(target):
        Remove(target, log = log)
    targetFile = open(target, "wb")
    while True:
        buffer = sourceFile.read(bufferSize)
        if not buffer:
            break
        targetFile.write(buffer)

def CopyStat(source, target, includeTimes = False):
    """Copy the stat information from the source to the target."""
    sourceStat = os.stat(source)
    mode = stat.S_IMODE(sourceStat.st_mode)
    os.chmod(target, mode)
    if includeTimes:
        os.utime(target, (sourceStat.st_atime, sourceStat.st_mtime))

def Copy(source, target, includeTimes = False):
    """Copy the source to the target."""
    if os.path.isdir(target):
        target = os.path.join(target, os.path.basename(source))
    CopyFile(source, target)
    CopyStat(source, target, includeTimes)

def CopyTree(source, target, includeTimes = False, log = True):
    """Recursively copy a directory tree."""
    for name in os.listdir(source):
        sourceName = os.path.join(source, name)
        targetName = os.path.join(target, name)
        if os.path.isdir(sourceName):
            if os.path.exists(targetName):
                RemoveTree(targetName, log)
            os.mkdir(targetName)
            CopyTree(sourceName, targetName, includeTimes)
        else:
            CopyFile(sourceName, targetName)
            CopyStat(sourceName, targetName, includeTimes)

def Remove(path, log = True):
    """Remove a file or a directory tree recursively."""
    if os.path.isdir(path):
        RemoveTree(path, log)
    else:
        if log:
            cx_Logging.Info("removing file %s...", path)
        if sys.platform == "win32":
            os.chmod(path, 0x1ff)
        os.remove(path)

def RemoveTree(path, log = True):
    """Recursively remove a directory tree."""
    try:
        currentDir = os.getcwd()
    except OSError:
        currentDir = None
    if currentDir is None or currentDir.startswith(path):
        os.chdir("/")
    if log:
        cx_Logging.Info("removing directory %s...", path)
    for name in os.listdir(path):
        fullName = os.path.join(path, name)
        Remove(fullName, log = log)
    if sys.platform == "win32":
        os.chmod(path, 0x1ff)
    os.rmdir(path)

