"""Defines functions for standard shell operations that are common on Unix but
   are not readily available on Windows in a cross platform way; this is
   intended to replace shutil which is less usable for copying and removing
   trees."""

import os
import stat
import sys

def CopyFile(source, target, bufferSize = 16 * 1024):
    """Copy the source to the target."""
    sourceFile = file(source, "rb")
    if os.path.exists(target):
        Remove(target)
    targetFile = file(target, "wb")
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

def CopyTree(source, target, includeTimes = False):
    """Recursively copy a directory tree."""
    for name in os.listdir(source):
        sourceName = os.path.join(source, name)
        targetName = os.path.join(target, name)
        if os.path.isdir(sourceName):
            if os.path.exists(targetName):
                RemoveTree(targetName)
            os.mkdir(targetName)
            CopyTree(sourceName, targetName, includeTimes)
        else:
            CopyFile(sourceName, targetName)
            CopyStat(sourceName, targetName, includeTimes)

def Remove(path):
    """Remove a file or a directory tree recursively."""
    if os.path.isdir(path):
        RemoveTree(path)
    else:
        if sys.platform == "win32":
            os.chmod(path, 0777)
        os.remove(path)

def RemoveTree(path):
    """Recursively remove a directory tree."""
    try:
        currentDir = os.getcwd()
    except OSError:
        currentDir = None
    if currentDir is None or currentDir.startswith(path):
        os.chdir("/")
    for name in os.listdir(path):
        fullName = os.path.join(path, name)
        Remove(fullName)
    os.rmdir(path)

