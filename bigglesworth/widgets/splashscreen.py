from Qt import QtCore, QtGui, QtWidgets

from bigglesworth.version import __version__

#class SplashPixmap(QtGui.QPixmap):
#    def __init__(self):
#        QtGui.QPixmap.__init__(self, 480, 320)
#        self.fill(QtCore.Qt.white)
#        qp = QtGui.QPainter(self)
#        qp.setRenderHints(qp.Antialiasing)
#        font = QtGui.QFont('OPTIAlpine-Bold')
#        font.setPointSize(44)
#        font.setBold(True)
#        font.setStretch(130)
#
#        qp.setPen(QtCore.Qt.darkGray)
#        fm = QtGui.QFontMetrics(font)
#        qp.drawRoundedRect(480 - fm.width('bigglesworth') - 10, 110, 600, fm.height() - 10, 6, 6)
#
#        qp.setPen(QtCore.Qt.black)
#        qp.setFont(font)
#        qp.drawText(QtCore.QRect(0, 100, 476, 100), QtCore.Qt.AlignRight|QtCore.Qt.AlignTop, 'bigglesworth')
#        font.setPointSize(8)
#        font.setBold(False)
#        font.setStretch(110)
#
#        qp.setPen(QtCore.Qt.NoPen)
#        qp.setBrush(QtCore.Qt.white)
#        qp.drawRect(480 - QtGui.QFontMetrics(font).width('a free editor for your Waldorf Blofeld') - 5, 154, 600, 20)
#
#        qp.setFont(font)
#        qp.setPen(QtCore.Qt.darkGray)
#        qp.drawText(QtCore.QRect(0, 156, 476, 20), QtCore.Qt.AlignRight|QtCore.Qt.AlignTop, 'a free editor for your Waldorf Blofeld')
#
#        qp.setPen(QtCore.Qt.black)
#        qp.setFont(QtWidgets.QApplication.font())
#        qp.drawText(QtCore.QRect(0, 156, 476, 40), QtCore.Qt.AlignRight|QtCore.Qt.AlignBottom, 'version ' + __version__)
#        qp.end()


class SplashScreen(QtWidgets.QSplashScreen):
    finished = QtCore.pyqtSignal()

    def __init__(self):
        self.sourcePixmap = QtGui.QPixmap(':/images/bigglesworth_splash.svg')
        desktop = QtWidgets.QApplication.desktop()
        size = min(desktop.availableGeometry().width() / 3., 480)
        pixmap = self.sourcePixmap.scaledToWidth(size, QtCore.Qt.SmoothTransformation)

        QtWidgets.QSplashScreen.__init__(self, pixmap, QtCore.Qt.WindowStaysOnTopHint)
        self.progress = 0
        self.next = 0
        self.delta = 0
        self.pen = QtGui.QPen(QtCore.Qt.darkGray, 2)
        self.timer = QtCore.QTimer()
        self.timer.setInterval(25)
        self.timer.timeout.connect(self.refresh)
        self.timerThread = QtCore.QThread()
        self.timer.moveToThread(self.timerThread)
        self.timerThread.started.connect(self.timer.start)
        self.finished.connect(self.timerThread.quit)

    def hideEvent(self, event):
        self.finished.emit()

    def refresh(self):
        if self.next - self.progress:
            self.delta = (self.next - self.progress) * .5
            self.progress += self.delta
        else:
            self.timer.stop()
        self.repaint()
        if self.next < 1:
            QtWidgets.QApplication.processEvents()

    def start(self):
        self.timerThread.start()
        self.show()

    def showMessage(self, message, alignment, next=None):
        if next is not None:
            self.progress = self.next
            self.next = next
            self.refresh()
        else:
            self.timer.stop()
        QtWidgets.QSplashScreen.showMessage(self, message, alignment)

    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        qp.setPen(self.pen)
        qp.drawLine(-10, 220, self.width() * self.progress, 220)

