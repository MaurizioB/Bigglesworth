import os, sys, ctypes
from Queue import Queue
from ctypes.util import find_library

from Qt import QtCore

from bigglesworth.const import LogDebug, LogCritical

SQLITE_OK = 0
SQLITE_ERROR = 1
SQLITE_BUSY = 5
SQLITE_LOCKED = 6

SQLITE_OPEN_READONLY = 1
SQLITE_OPEN_READWRITE = 2
SQLITE_OPEN_CREATE = 4

if sys.platform == 'win32':
#    print(sys.path)
    for p in sys.path:
        try:
            sqlite = ctypes.CDLL(os.path.join(p, 'sqlite3.dll'))
            break
        except:
            pass
    else:
        raise('sqlite not found?!')
else:
    sqlite = ctypes.CDLL(find_library('sqlite3'))

sqlite.sqlite3_backup_init.restype = ctypes.c_void_p

srcDbPointer = ctypes.c_void_p(None)
destDbPointer = ctypes.c_void_p(None)
nullPointer = ctypes.c_void_p(None)

class BackUp(QtCore.QObject):
    backupStarted = QtCore.pyqtSignal()
    backupStatusChanged = QtCore.pyqtSignal(int)
    backupFinished = QtCore.pyqtSignal()
    backupError = QtCore.pyqtSignal(str)

    def __init__(self, parent):
        QtCore.QObject.__init__(self)
        self.main = parent
        self.basePath = self.bkpPath = None
        self.queue = Queue()
        self.success = True

    def setPath(self, path):
        self.basePath = path
        self.bkpPath = path + '.bkp'

    def queueBackup(self):
        self.backupStarted.emit()
#        print('metto in coda')
        self.queue.put(True)

    def run(self):
        while True:
            res = self.queue.get()
            if res:
                self.doBackup()
            else:
                print('esco!')
                break

    def doBackup(self):
        self.main.logger.append(LogDebug, 'Starting backup')
#        print('lancio backup')
        res = sqlite.sqlite3_open_v2(self.basePath, ctypes.byref(srcDbPointer), SQLITE_OPEN_READONLY, nullPointer)
        if res != SQLITE_OK or srcDbPointer.value is None:
            self.main.logger.append(LogCritical, 'Error opening database for backup')
            self.success = False
            self.backupError.emit('Error opening the database for backup')
            return
        res = sqlite.sqlite3_open_v2(self.bkpPath, ctypes.byref(destDbPointer), SQLITE_OPEN_READWRITE|SQLITE_OPEN_CREATE, nullPointer)
        if res != SQLITE_OK or destDbPointer.value is None:
            self.main.logger.append(LogCritical, 'Error opening or creating backup database')
            self.success = False
            self.backupError.emit('Error opening or creating the backup database')
            return

        self.backupStarted.emit()
        backupPointer = sqlite.sqlite3_backup_init(destDbPointer, 'main', srcDbPointer, 'main')
        self.main.logger.append(LogDebug, 'Backup handler', '{0:#08x}'.format(backupPointer))
        print('backup handler: {0:#08x}'.format(backupPointer))
        if backupPointer is None:
            self.main.logger.append(LogCritical, 'Error obtaining pointer for backup')
            self.success = False
            self.backupError.emit('Error obtaining pointer to database backup')
        self.backupStatusChanged.emit(0)

        while True:
            res = sqlite.sqlite3_backup_step(backupPointer, 20)
            remaining = sqlite.sqlite3_backup_remaining(backupPointer)
            count = sqlite.sqlite3_backup_pagecount(backupPointer)
            current = (count - remaining) / float(count) * 100
            self.backupStatusChanged.emit(current)
            if remaining == 0:
                break
            if res in (SQLITE_OK, SQLITE_BUSY, SQLITE_LOCKED):
                sqlite.sqlite3_sleep(100)

        self.success = True
        self.backupFinished.emit()
        self.main.logger.append(LogDebug, 'Backup completed')
        sqlite.sqlite3_backup_finish(backupPointer)
        sqlite.sqlite3_close(srcDbPointer)
        sqlite.sqlite3_close(destDbPointer)


