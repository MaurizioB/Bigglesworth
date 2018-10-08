# *-* encoding: utf-8 *-*

from Qt import QtCore, QtGui, QtWidgets

from bigglesworth.version import __version__

QtCore.pyqtProperty = QtCore.Property

helpers = 'Fabio "Faber" Vescarelli', 'Benedetto Schiavone', 
contributors = 'Thibault Appourchaux', 
testers = 'Don Petersen', 
donors = 'Nick Sherman', 'Piet Wagner'

thanksto = helpers + contributors + testers + donors

def makeCoordProp(gradName):
    def getterX(self):
        return getattr(self, gradName).center().x()
    def setterX(self, x):
        grad = getattr(self, gradName)
        grad.setCenter(x, grad.center().y())
        grad.setFocalPoint(x, grad.focalPoint().y())

    def getterY(self):
        return getattr(self, gradName).center().y()
    def setterY(self, y):
        grad = getattr(self, gradName)
        grad.setCenter(grad.center().x(), y)
        grad.setFocalPoint(grad.focalPoint().x(), y)

    def getterCenterRadius(self):
        return getattr(self, gradName).centerRadius()
    def setterCenterRadius(self, radius):
        getattr(self, gradName).setCenterRadius(radius)

    return (QtCore.pyqtProperty(float, getterX, setterX), 
        QtCore.pyqtProperty(float, getterY, setterY), 
        QtCore.pyqtProperty(float, getterCenterRadius, setterCenterRadius))


def makeGradProp(colName, gradName, pos):
    def getterRed(self):
        return getattr(self, colName).red()
    def setterRed(self, red):
        col = getattr(self, colName)
        col.setRed(int(red))
        getattr(self, gradName).setColorAt(pos, col)

    def getterGreen(self):
        return getattr(self, colName).green()
    def setterGreen(self, red):
        col = getattr(self, colName)
        col.setGreen(int(red))
        getattr(self, gradName).setColorAt(pos, col)

    def getterBlue(self):
        return getattr(self, colName).blue()
    def setterBlue(self, red):
        col = getattr(self, colName)
        col.setBlue(int(red))
        getattr(self, gradName).setColorAt(pos, col)

    return QtCore.pyqtProperty(float, getterRed, setterRed), QtCore.pyqtProperty(float, getterGreen, setterGreen), QtCore.pyqtProperty(float, getterBlue, setterBlue)


class AboutDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        self.setWindowTitle('About Bigglesworth...')
        self.pixmap = QtGui.QPixmap(':/images/bigglesworth_splash_transparent.svg').scaledToWidth(480, QtCore.Qt.SmoothTransformation)
        self.resize(480, 320)
        self.setFixedSize(self.size())

        self._scrollY = self.height()
        self.anim = QtCore.QPropertyAnimation(self, b'scrollY')
        self.anim.setLoopCount(-1)
        self.anim.setDuration(15000)
        self.anim.setStartValue(self.height())

        text = u'''
            The open and multi-platform editor
            for the Waldorf Blofeld Synthesizer
            
            Version {version}

            written by Maurizio Berti

            Thanks to:

            {thanksto}

            The people at Synth Cafè
            and all the users!
            '''.format(version=__version__, thanksto='\n'.join(thanksto))
        self.text = '\n'.join(map(unicode.strip, text.strip().split('\n')))

        rect = QtCore.QRect(0, 0, self.width(), 10000)
        self.textRect = self.fontMetrics().boundingRect(rect, 0x1000, self.text)
        self.anim.setEndValue(-self.textRect.height() + 100)
        self.shown = False
        self.scrollGrad = QtGui.QLinearGradient(0, 178, 0, 320)
        self.scrollGrad.setColorAt(0, QtGui.QColor(QtCore.Qt.transparent))
        self.scrollGrad.setColorAt(.01, QtGui.QColor(QtCore.Qt.transparent))
        self.scrollGrad.setColorAt(.2, QtGui.QColor(30, 30, 30))
        self.scrollPen = QtGui.QPen(self.scrollGrad, 1)

        self.grad0 = QtGui.QRadialGradient(10, 160, 240, 10, 160, 80)
        self.col0 = QtGui.QColor(100, 200, 200, 64)
        self.grad0.setColorAt(0, self.col0)
        self.grad0.setColorAt(1, QtGui.QColor(190, 200, 200, 64))
        self.grad1 = QtGui.QRadialGradient(10, 160, 240, 10, 160, 80)
        self.col1 = QtGui.QColor(190, 200, 200, 64)
        self.grad1.setColorAt(0, self.col1)
        self.grad0.setColorAt(1, QtGui.QColor(190, 200, 200, 64))

        self.animations = []

        self.createAnimation(b'center0X', 3300, -10, 490)
        self.createAnimation(b'center0Y', 2000, -10, 330)
        self.createAnimation(b'radius0', 2000, 160, 400)
        self.createAnimation(b'grad0R', 1500, 0, 255)
        self.createAnimation(b'grad0G', 1200, 0, 255)
        self.createAnimation(b'grad0B', 800, 0, 255)

        self.createAnimation(b'center1X', 2000, 490, -10)
        self.createAnimation(b'center1Y', 1900, 330, -10)
        self.createAnimation(b'grad1R', 3000, 255, 0)
        self.createAnimation(b'grad1G', 2400, 255, 0)
        self.createAnimation(b'grad1B', 2600, 255, 0)

    def createAnimation(self, prop, time, start, end):
        anim = QtCore.QPropertyAnimation(self, prop)
        anim.setEasingCurve(QtCore.QEasingCurve.InOutQuad)
        anim.setDuration(time)
        anim.setStartValue(start)
        anim.setEndValue(end)
        anim.finished.connect(lambda a=anim: [a.setDirection(not a.direction()), a.start()])
        self.animations.append(anim)

    def showEvent(self, event):
        if not self.shown:
            self.textRect.setRight(self.width() - 10)
            self.anim.start()
            self.shown = True
            [a.start() for a in self.animations]
#            self.gradAniCY.start()

    def closeEvent(self, event):
        [a.stop() for a in self.animations]

    @QtCore.pyqtProperty(float)
    def scrollY(self):
        return self._scrollY

    @scrollY.setter
    def scrollY(self, value):
        self._scrollY = value
        self.update()

    center0X, center0Y, radius0 = makeCoordProp('grad0')
    center1X, center1Y, radius1 = makeCoordProp('grad1')

#    @QtCore.pyqtProperty(float)
#    def center0X(self):
#        return self.grad0.center().x()
#
#    @center0X.setter
#    def center0X(self, x):
#        self.grad0.setCenter(x, self.grad0.center().y())
#        self.grad0.setFocalPoint(x, self.grad0.focalPoint().y())
#
#    @QtCore.pyqtProperty(float)
#    def center0Y(self):
#        return self.grad0.center().y()
#
#    @center0Y.setter
#    def center0Y(self, y):
#        self.grad0.setCenter(self.grad0.center().x(), y)
#        self.grad0.setFocalPoint(self.grad0.focalPoint().x(), y)

    grad0R, grad0G, grad0B = makeGradProp('col0', 'grad0', 0)
    grad1R, grad1G, grad1B = makeGradProp('col1', 'grad1', 1)

    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        qp.translate(.5, .5)
        qp.setRenderHints(qp.Antialiasing)
        qp.fillRect(self.rect(), QtCore.Qt.white)
        qp.fillRect(self.rect(), self.grad0)
        qp.fillRect(self.rect(), self.grad1)
#
#        font = QtGui.QFont('OPTIAlpine-Bold')
#        font.setPointSize(44)
#        font.setBold(True)
#        font.setStretch(130)
#
#        qp.save()
#        rect0 = QtCore.QRect(0, 0, 480, 160)
#        font2 = QtGui.QFont(font)
#        font2.setPointSize(8)
#        font2.setBold(False)
#        font2.setStretch(110)
#        rect1 = QtCore.QRect(0, 0, 480 - QtGui.QFontMetrics(font2).width('The editor for your Waldorf Blofeld') - 10, 180)
#        region = QtGui.QRegion(rect0)
#        region = region.united(rect1)
#        qp.setClipRegion(region)
#        qp.setPen(QtCore.Qt.darkGray)
#        fm = QtGui.QFontMetrics(font)
#        qp.drawRoundedRect(480 - fm.width('bigglesworth') - 10, 110, 600, fm.height() - 10, 6, 6)
#        qp.restore()
#
#        qp.setPen(QtCore.Qt.black)
#        qp.setFont(font)
#        qp.drawText(QtCore.QRect(0, 100, 476, 100), QtCore.Qt.AlignRight|QtCore.Qt.AlignTop, 'bigglesworth')
#        font.setPointSize(8)
#        font.setBold(False)
#        font.setStretch(110)
#
##        qp.setPen(QtCore.Qt.NoPen)
##        qp.setBrush(QtCore.Qt.white)
##        qp.drawRect(480 - QtGui.QFontMetrics(font).width('a free editor for your Waldorf Blofeld') - 5, 154, 600, 20)
#
#        qp.setFont(font)
#        qp.setPen(QtGui.QColor(50, 50, 50))
#        qp.drawText(QtCore.QRect(0, 156, 476, 20), QtCore.Qt.AlignRight|QtCore.Qt.AlignTop, 'The editor for your Waldorf Blofeld')

        qp.drawPixmap(self.rect(), self.pixmap)

        qp.setPen(self.scrollPen)
        qp.setFont(self.font())
        qp.setClipRect(self.rect().adjusted(0, 146, 0, 0))
        qp.drawText(self.textRect.translated(0, self.scrollY), QtCore.Qt.AlignTop|QtCore.Qt.AlignRight, self.text)
        qp.setPen(QtCore.Qt.NoPen)
#        qp.setBrush(self.grad)
#        qp.drawRect(0, 170, self.width(), 10)


if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)
    w = AboutDialog()
    w.show()
    sys.exit(app.exec_())
