from Qt import QtCore

class Logger(QtCore.QObject):
    updated = QtCore.pyqtSignal(int, int, object, object)

    def __init__(self, main):
        QtCore.QObject.__init__(self)
        self.main = main
        self.log = []
        self.timer = QtCore.QElapsedTimer()
        self.timer.start()
        self.startTime = QtCore.QDateTime.currentDateTime()
        self.append(0, 'Started')

    def append(self, logLevel, message, extMessage=''):
        elapsed = self.timer.elapsed()
        if extMessage is None:
            extMessage = ''
        elif isinstance(extMessage, (tuple, list)):
            extMessage = ', '.join(str(m) for m in extMessage)
        self.log.append((elapsed, logLevel, message, extMessage))
        self.updated.emit(elapsed, logLevel, message, extMessage)

