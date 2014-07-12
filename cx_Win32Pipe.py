"""There are a number of serious restrictions on Windows to using popen but the
   one that really troubles us is the fact that if popen is called with a mode
   of "w" then stdout for the child process is closed. If popen4 is used, then
   it is imperative that stdout be read in a different thread in order to avoid
   flow control issues."""

import os
import sys
import _thread

class Popen4:
    """Replacement for popen4 which works when writing to stdin."""

    def __init__(self, command):
        self.__childStdin, self.__childStdout = os.popen4(command)
        self.__lock = _thread.allocate_lock()
        self.__lock.acquire()
        _thread.start_new_thread(self.__DuplicateStdout, ())
        self.write = self.__childStdin.write

    def __DuplicateStdout(self):
        """Duplicate stdout from the child process to stdout."""
        while True:
            line = self.__childStdout.readline()
            if not line:
                break
            sys.stdout.write(line)
        self.__result = self.__childStdout.close()
        self.__lock.release()

    def close(self):
        """Close the pipe and return the exit code of the process."""
        self.__result = self.__childStdin.close()
        self.__lock.acquire()
        return self.__result


def popen(command, mode = "r"):
    """Win32 replacement for popen that avoids the problems noted above."""
    if mode == "w":
        return Popen4(command)
    return os.popen(command, mode)

