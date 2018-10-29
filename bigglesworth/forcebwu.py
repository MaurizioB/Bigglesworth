#!/usr/bin/env python2.7
# *-* encoding: utf-8 *-*

import os, sys
from random import randrange

os.environ['QT_PREFERRED_BINDING'] = 'PyQt4'

from Qt import QtCore, QtGui, QtWidgets

try:
    from bigglesworth.version import __version__
    from bigglesworth.dialogs.about import thanksto
except:
    __version__ == '0.1.2'
    thanksto = 'Fabio "Faber" Vescarelli', 'Benedetto Schiavone', 'Nick Sherman', 'Piet Wagner'

#SWColor = lambda: QtGui.QColor(229, 177, 58)
SWColor = lambda: QtGui.QColor(255, 195, 12)

Romans = [
    (1000, 'M'),
    ( 900, 'CM'),
    ( 500, 'D'),
    ( 400, 'CD'),
    ( 100, 'C'),
    (  90, 'XC'),
    (  50, 'L'),
    (  40, 'XL'),
    (  10, 'X'),
    (   9, 'IX'),
    (   5, 'V'),
    (   4, 'IV'),
    (   1, 'I'),
]

def getRoman(value):
    if not value:
        return '0'
    roman = ''
    for n, r in Romans:
        fact, value = divmod(value, n)
        roman += r * fact
        if not value:
            break
    return roman

class BgPixmap(QtGui.QPixmap):
    def __init__(self, size):
        QtGui.QPixmap.__init__(self, size)
        self.fill(QtCore.Qt.black)
        stars = (
            (2, randrange(2000, 3000), 128, 32), 
            (2, randrange(1500, 2500), 128, 64), 
            (2, randrange(1000, 1500), 144, 96), 
            (4, randrange(100, 200), 152, 128), 
            )
        starGrad = QtGui.QRadialGradient(.5, .5, .5)
        starGrad.setCoordinateMode(starGrad.ObjectBoundingMode)
        starGrad.setColorAt(1, QtCore.Qt.black)
        qp = QtGui.QPainter(self)
        qp.translate(.5, .5)
        qp.setRenderHints(qp.Antialiasing)
        width = size.width()
        height = size.height()
        tot = 0
        for size, count, blue, alpha in stars:
            starGrad.setColorAt(0, QtGui.QColor(128, blue, blue, alpha))
            qp.setBrush(starGrad)
            for n in range(count):
                qp.drawEllipse(randrange(width), randrange(height), size, size)
                tot += 1
        qp.end()


class MayTheForce(QtWidgets.QDialog):
    def __init__(self, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        layout = QtWidgets.QHBoxLayout()
        self.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setMinimumWidth(720)
        self.setMinimumHeight(306)
        desktop = QtWidgets.QApplication.desktop()
        geo = desktop.availableGeometry()
        width = int(geo.width() * .8)
        height = int(width / 2.4)
        self.resize(width, height)
        self.move(geo.left() + (geo.width() - width) / 2, geo.top() + (geo.height() - height) / 2)
        self.starField = BgPixmap(self.size())
        
        self.ratio = 1.
        self.topXRatio = .18
        self.topYRatio = .50
        self.bottomXRatio = .18
        self.bottomYRatio = 1.35

        palette = self.palette()
        palette.setBrush(self.backgroundRole(), QtGui.QBrush(self.starField))
        self.setPalette(palette)
        self.transform = QtGui.QTransform()

        self._crawlColor = SWColor()
        #TODO: aggiorna la Y del gradiente al resize?
#        self.crawlGrad = QtGui.QLinearGradient(0, 1, 0, 0)
#        self.crawlGrad.setCoordinateMode(self.crawlGrad.StretchToDeviceMode)
        self.crawlGrad = QtGui.QLinearGradient(0, 1800, 0, 0)
#        self.crawlGrad.setSpread(self.crawlGrad.RepeatSpread)
        self.crawlGrad.setColorAt(1, QtCore.Qt.transparent)
#        self.crawlGrad.setColorAt(1, QtCore.Qt.green)
        self.crawlGrad.setColorAt(.5, self._crawlColor)
#        self.crawlGrad.setColorAt(.2, QtGui.QColor(QtCore.Qt.red))
        self.crawlGrad.setColorAt(0, self._crawlColor)
        self.brush = QtGui.QBrush(self.crawlGrad)
        self.pen = QtGui.QPen(self.brush, 2)
        self._headerColor = SWColor()
        self.headerPen = QtGui.QPen(self.headerColor, 4, join=QtCore.Qt.MiterJoin)

        QtGui.QFontDatabase.addApplicationFont(':/fonts/Starjedi.ttf')
        self.headerFont = QtGui.QFont('Star Jedi')
        self.headerFont.setPointSize(96)
        headerFM = QtGui.QFontMetrics(self.headerFont)
        header = QtGui.QPainterPath()
        header.addText(16, 80, self.headerFont, 'biggle')
        header.addText(headerFM.width('SW'), 164, self.headerFont, 'oRth')
        self.header = QtGui.QPainterPath()
        for p in header.toSubpathPolygons():
            self.header.addPolygon(p)

        sPath = QtGui.QPainterPath()
        sPath.addText(0, 164, self.headerFont, 'S')

        wPath = QtGui.QPainterPath()
        wPath.addText(headerFM.width('S'), 164, self.headerFont, 'W')

        sb = sPath.united(wPath)
        self.header = self.header.united(sb)
        self.header = self.header.translated(
            -self.header.boundingRect().center().x(), -self.header.boundingRect().center().y())

        QtGui.QFontDatabase.addApplicationFont(':/fonts/SWCrawlTitle.ttf')
        self.titleFont = QtGui.QFont('SW Crawl Title')
        self.titleFont.setPointSize(80)
        QtGui.QFontDatabase.addApplicationFont(':/fonts/SWCrawlBody.ttf')
        self.bodyFont = QtGui.QFont('SW Crawl Body')
        self.bodyFont.setBold(True)
        self.bodyFont.setPointSize(42)
        if sys.platform != 'win32':
            self.bodyFont.setStretch(140)
            self.bodyFont.setLetterSpacing(self.bodyFont.PercentageSpacing, 85)
            self.bodyFont.setWordSpacing(-4)
        else:
            self.titleFont.setBold(True)
        self.versionFont = QtGui.QFont(self.bodyFont)
        self.versionFont.setPointSize(16)
#        self.bodyFont.setWeight(99)

        QtGui.QFontDatabase.addApplicationFont(':/fonts/onesizerev.ttf')
        QtGui.QFontDatabase.addApplicationFont(':/fonts/onesize.ttf')

        #The following is a unicode thin space (U+2009): " "
        #The following is a unicode hair space (U+200A): " "
#        text = u'''
#        A  year  has  passed since  the  previous 
#        version was released, and lots of users 
#        lost their hope, but here we are.
#
#        Created by Maurizio Berti.
#
#        Thanks to:
#        Fabio "Faber" Vescarelli
#        Benedetto Schiavone
#        Nick Sherman
#
#        The people at Synth Cafe and all the 
#        users around the galaxy!
#
#        May the patch be with us....
#        '''
#
#        self.text = [l.strip() for l in text.split('\n')]
        self.fullText = u'It is a dark time for the Blofeld editors. ' \
            'A year has passed since the previous version of BIGGLESWORTH was released, ' \
            'and lots of users lost their hope.\n\n' \
            'Evading the dreaded competition, a group of freedom fighters has ' \
            'established their confidence, sure that the beloved program was still alive.\n\n' \
            'Created by Maurizio Berti.\n\n' \
            'Thanks to:\n{}, ' \
            'the people at Synth Cafe, and all the users around the galaxy!\n\n' \
            'May the patch be with us__dots__'.format(', '.join(thanksto))

#        self.fullText = 'It is a dark time for the Rebellion. ' \
#        'Although the Death Star has been destroyed, Imperial troops have driven the ' \
#        'Rebel forces from their hidden base and pursued them across the galaxy.\n\n' \
#        'Evading the dreaded Imperial Starfleet, a group of freedom fighters led by ' \
#        'Luke Skywalker has established a new secret base on the remote ice world of Hoth.\n\n' \
#        'The evil lord Darth Vader, obsessed with finding young Skywalker, ' \
#        'has dispatched thousands of remote probes into the far reaches of space....'

        self.buildText()

        self.midiMoon = QtGui.QPixmap(':/images/midimoon.svg')

        self._headerScale = 1
        self.headerScaleAnimation = QtCore.QPropertyAnimation(self, b'headerScale')
        self.headerScaleAnimation.valueChanged.connect(self.update)
#        self.headerScaleAnimation.setEasingCurve(QtCore.QEasingCurve(QtCore.QEasingCurve.OutQuint))
        self.headerScaleAnimation.setEasingCurve(QtCore.QEasingCurve(QtCore.QEasingCurve.OutExpo))
        self.headerScaleAnimation.setDuration(24000)
        self.headerScaleAnimation.setEndValue(0)
        self.headerScaleAnimation.setLoopCount(1)

        self.headerColorAnimation = QtCore.QPropertyAnimation(self, b'headerColor')
        self.headerColorAnimation.setDuration(4000)
        self.headerColorAnimation.setEasingCurve(QtCore.QEasingCurve(QtCore.QEasingCurve.OutQuart))
        self.headerColorAnimation.setStartValue(self._headerColor)
        self.headerColorAnimation.setEndValue(QtGui.QColor(229, 177, 58, 0))
        self.headerColorAnimation.setLoopCount(1)
        self.headerColorAnimation.finished.connect(lambda: [self.headerScaleAnimation.stop(), self.setTitleShown(False)])

        self._crawlPos = self.height()
        self.crawlAnimation = QtCore.QPropertyAnimation(self, b'crawlPos')
        self.crawlAnimation.setDuration(77000)
        self.crawlAnimation.setLoopCount(1)
        self.crawlAnimation.valueChanged.connect(self.update)
        self.crawlAnimation.setEndValue(self.crawlText.boundingRect().height() * -2)
#        self.crawlAnimation.finished.connect(lambda: [self.startPan(), self.setCrawlShown(False)])
        self.crawlFadeTimer = QtCore.QTimer()
        self.crawlFadeTimer.setInterval(74000)
        self.crawlFadeTimer.setSingleShot(True)

        self.showCrawl = False
        self.crawlFadeAnimation = QtCore.QPropertyAnimation(self, b'crawlColor')
        self.crawlFadeAnimation.setStartValue(self._crawlColor)
        crawlTransparent = SWColor()
        crawlTransparent.setAlpha(0)
        self.crawlFadeAnimation.setEndValue(crawlTransparent)
        self.crawlFadeAnimation.setDuration(3000)
        self.crawlFadeAnimation.setLoopCount(1)
        self.crawlFadeAnimation.finished.connect(lambda: [self.startPan(), self.setCrawlShown(False), self.crawlAnimation.stop()])
        self.crawlFadeTimer.timeout.connect(self.crawlFadeAnimation.start)

#        self.crawlTimer = QtCore.QTimer()
#        self.crawlTimer.setInterval(25)
#        self.crawlTimer.timeout.connect(self.updateCrawl)
        self._moveY = 0
        self.cameraAnimation = QtCore.QPropertyAnimation(self, b'moveY')
        self.cameraAnimation.valueChanged.connect(self.moveBgd)
        self.cameraAnimation.setStartValue(0)
        self.cameraAnimation.setEasingCurve(QtCore.QEasingCurve(QtCore.QEasingCurve.InOutSine))
        self.cameraAnimation.setDuration(8000)
        self.cameraAnimation.setLoopCount(1)

        self._moonScale = .01
        self.moonAnimation = QtCore.QPropertyAnimation(self, b'moonScale')
        self.moonAnimation.valueChanged.connect(self.update)
#        self.moonAnimation.setEasingCurve(QtCore.QEasingCurve(QtCore.QEasingCurve.InOutQuint))
#        self.moonAnimation.setDuration(32000)
        self.moonAnimation.setEasingCurve(QtCore.QEasingCurve(QtCore.QEasingCurve.InQuint))
        self.moonAnimation.setDuration(20000)
        self.moonAnimation.setLoopCount(1)

        self._moonDelta = 0
        self.moonDeltaAnimation = QtCore.QPropertyAnimation(self, b'moonDelta')
        self.moonDeltaAnimation.setEasingCurve(QtCore.QEasingCurve(QtCore.QEasingCurve.InSine))
        self.moonDeltaAnimation.setEndValue(0)
        self.moonDeltaAnimation.setDuration(self.moonAnimation.duration())
        self.moonDeltaAnimation.setLoopCount(1)

        self.sub = [
            ('We\'re heading for that small moon.', 2500), 
            ('', 500), 
            ('That\'s no moon...', 2000), 
            ('', 500), 
            ('It\'s a MIDI connection!', 3500), 
            ('', 40000), 
            ('You\'re still there?', 5000), 
            ('', 2000), 
            ('...', 2000), 
            ('', 2000), 
            ('Mmmh...', 2000), 
            ('', 4000), 
            ('Seriously, don\'t you have anything\nbetter to do?', 3500), 
            ('', 1500), 
            ('Well, the show is over. It took me a lot of CPU,\nI\'m not gonna play it again, ok?', 5000), 
            ('', 5500), 
            ('Ah, while you\'re still there having fun...\nThink about donating something to the project :-)', 3500), 
            ('', 2500), 
            ('Ok, bye! Have fun staring at this\n(wonderfully created) star field...', 5000), 
            ('', 6500), 
            ('(I\'m serious, isn\'t it beautiful?)', 2500), 
            ('', 30000), 
            ('Well... I\'m gonna have a cup of coffee, see you!', 500), 
            ('', 60000), 
            ('Please, close me!', 1)
            ]
        self.subTimer = QtCore.QTimer()
        self.subTimer.setInterval(1000)
        self.subTimer.setSingleShot(True)
        self.subTimer.timeout.connect(self.nextSub)
        self.subText = ''

#        self.moveTimer = QtCore.QTimer()
#        self.moveTimer.setInterval(50)
#        self.moveTimer.timeout.connect(self.moveBgd)
        self.start()

        self._boomColor = QtGui.QColor(0, 0, 0)
        self.boomAnimation = QtCore.QPropertyAnimation(self, b'boomColor')
        self.boomAnimation.setDuration(8000)
        self.boomAnimation.setStartValue(self._boomColor)
        self.boomAnimation.setKeyValueAt(.0125, QtGui.QColor(QtCore.Qt.white))
        self.boomAnimation.setEndValue(QtGui.QColor(QtCore.Qt.transparent))
        self.boomAnimation.valueChanged.connect(self.update)
        self.moonAnimation.finished.connect(lambda: [
            setattr(self, 'showMoon', False), 
            setattr(self, 'showBoom', True), 
            self.boomAnimation.start()])
        self.showBoom = False

        self.animations = [obj for obj in self.__dict__.values() if isinstance(obj, QtCore.QPropertyAnimation)]
        self.elapsedTimer = QtCore.QElapsedTimer()
        self.elapsedTimer.start()
        self.lastFrame = 0
        self.showOsd = False
        self.osdTimer = QtCore.QTimer()
        self.osdTimer.setInterval(0)
        self.osdTimer.timeout.connect(self.updateOsd)
        self.shown = False
#        self.startPan()

    @QtCore.Property(QtGui.QColor)
    def crawlColor(self):
        return self._crawlColor

    @crawlColor.setter
    def crawlColor(self, color):
        self._crawlColor = color
        self.crawlGrad.setColorAt(.5, color)
        self.crawlGrad.setColorAt(0, color)
        self.brush = QtGui.QBrush(self.crawlGrad)
#        self.brush = QtGui.QBrush(self._crawlColor)

    @QtCore.Property(int)
    def moveY(self):
        return self._moveY

    @moveY.setter
    def moveY(self, y):
        self._moveY = y
#        self.moveBgd()

    @QtCore.Property(float)
    def headerScale(self):
        return self._headerScale

    @headerScale.setter
    def headerScale(self, scale):
        self._headerScale = scale
        if self.headerScale < .1:
            if not self.showCrawl:
                self.setCrawlShown(True)
                self.crawlAnimation.start()
                self.crawlFadeTimer.start()
                self.crawlStart = self.elapsedTimer.elapsed()
            if self.headerScale < .05 and not self.headerColorAnimation.state():
                self.headerColorAnimation.start()
#                alpha = self.headerColor.alphaF()
#                self.headerColor.setAlphaF(alpha - alpha * .045)
#                self.headerPen.setColor(self.headerColor)

    @QtCore.Property(QtGui.QColor)
    def headerColor(self):
        return self._headerColor

    @headerColor.setter
    def headerColor(self, color):
#        print(color.alpha())
        self._headerColor = color
        self.headerPen.setColor(self._headerColor)

    @QtCore.Property(float)
    def crawlPos(self):
        return self._crawlPos

    @crawlPos.setter
    def crawlPos(self, pos):
        self._crawlPos = pos

    @QtCore.Property(float)
    def moonScale(self):
        return self._moonScale

    @moonScale.setter
    def moonScale(self, scale):
        self._moonScale = scale

    @QtCore.Property(float)
    def moonDelta(self):
        return self._moonDelta

    @moonDelta.setter
    def moonDelta(self, delta):
        self._moonDelta = delta

    @QtCore.Property(QtGui.QColor)
    def boomColor(self):
        return self._boomColor

    @boomColor.setter
    def boomColor(self, color):
        self._boomColor = color

    def setTitleShown(self, show):
        self.showTitle = show

    def setCrawlShown(self, show):
        self.showCrawl = show

    def buildText(self):
        self.crawlText = QtGui.QPainterPath()
        bodyMetrics = QtGui.QFontMetrics(self.bodyFont)
        space = bodyMetrics.width(' ')
        width = float(self.width())
        height = bodyMetrics.height()
        splitted = []
        lineCount = 0
        for line in self.fullText.split('\n'):
            lineWidth = 0
            lineWords = []
            splitted = line.split()
            while splitted:
                word = splitted.pop(0)
                if word.endswith('__dots__'):
                    word = word.replace('__dots__', ' . . . .')
                wordWidth = bodyMetrics.width(word)
#                lineWords.append(word)
                if lineWidth + len(lineWords) * space + wordWidth > width:
                    justSpace = (width - lineWidth) / max(1, len(lineWords) - 1)
                    deltaX = 0
                    for w in lineWords:
                        self.crawlText.addText(deltaX, height * lineCount, self.bodyFont, w)
                        deltaX += bodyMetrics.width(w) + justSpace
                    lineWords = [word]
                    lineCount += 1
                    lineWidth = wordWidth
                else:
                    lineWords.append(word)
                    if not splitted:
                        self.crawlText.addText(0, height * lineCount, self.bodyFont, ' '.join(lineWords))
                        lineCount += 2
                        lineWords = []
                    else:
                        lineWidth += wordWidth
            if lineWords:
                self.crawlText.addText(0, height * lineCount, self.bodyFont, ' '.join(lineWords))
                lineCount += 2

        width = self.crawlText.boundingRect().width()
        titleMetrics = QtGui.QFontMetrics(self.titleFont)
        self.crawlText.translate(0, height * 2 + titleMetrics.height())

        versionText = 'Version {}'.format('.'.join(getRoman(int(v)) for v in __version__.split('.')))
        self.crawlText.addText((width - bodyMetrics.width(versionText)) / 2., 0, self.bodyFont, versionText)
        subtitleText = 'revenge of the synth editor'
        self.crawlText.addText((width - titleMetrics.width(subtitleText)) / 2., bodyMetrics.height() * 2, self.titleFont, subtitleText)


    def _buildText(self):
        versionFM = QtGui.QFontMetrics(self.versionFont)
        crawlFM = QtGui.QFontMetrics(self.bodyFont)
        width = max(crawlFM.width(l) for l in self.text)

        self.versionText = 'Episode {}'.format('.'.join(getRoman(int(v)) for v in '0.10.56'.split('.')))
        self.subtitleText = 'revenge of the synth editor'
        titleFM = QtGui.QFontMetrics(self.titleFont)

        self.crawlText = QtGui.QPainterPath()
        self.crawlText.addText(width * .5 - versionFM.width(self.versionText) * .5, 0, self.versionFont, self.versionText)
        self.crawlText.addText(width * .5 - titleFM.width(self.subtitleText) * .5, 
            self.crawlText.boundingRect().height() + titleFM.height() * .8, self.titleFont, self.subtitleText)

        y = self.crawlText.boundingRect().height() - titleFM.height() * .2
        for line in self.text:
            y += self.bodyFont.pointSize()
            self.crawlText.addText(0, y, self.bodyFont, line.strip())

#        self.crawlText = self.crawlText.translated(self.crawlText.boundingRect().width())
        self.crawlText.translate(-self.crawlText.boundingRect().width() * .5, 0)

    def start(self):
#        self._headerScale = self.width() / self.header.boundingRect().width() * 1.05
        self._headerScale = 1.6
#        self.resize(1280, 720)
#        self._crawlPos = self.height() * 1.1
#        self.crawlAnimation.setStartValue(0)
#        self.crawlAnimation.setEndValue(-self.crawlText.boundingRect().height())
#        self._crawlPos = self.height()
#        self.crawlAnimation.setStartValue(self.height())
        self.resetData()
        self.showTitle = True
        self.showCrawl = False
        self.showMoon = False
#        self.headerColor.setAlphaF(1)
#        self.headerPen.setColor(self.headerColor)
        self.headerScaleAnimation.setStartValue(self.ratio)
        self.headerScaleAnimation.start()
#        self.crawlTimer.start()

#        self.startPan()

    def startPan(self):
#        self.setMaximumWidth(self.width())
#        self.setMaximumHeight(self.height())
        self.cameraAnimation.setEndValue(self.height() * 1.6)
#        self.midiMoon = self.midiMoon.scaledToWidth(self.width() * 10, QtCore.Qt.SmoothTransformation)
        self.moonAnimation.setStartValue(.01)
        self.moonAnimation.setEndValue(4)
#        self.moonAnimation.setStartValue(self.width() / self.midiMoon.width() * 2.1)
#        print(self.width() / self.midiMoon.width() * .1)
#        self.moonAnimation.setEndValue(self.width() / self.midiMoon.width() * 10)
        self.moonStart = int(self.cameraAnimation.endValue() * .5)
#        self.subFont = self.font()
#        self.subFont.setPointSize(self.height() * .05)
        self.subFontBgd = QtGui.QFont('Onesize')
        self.subFont = QtGui.QFont('Onesize Reverse')
        self.subFontBgd.setPointSize(self.height() * .06)
        self.subFont.setPointSize(self.height() * .06)
        self.cameraAnimation.start()

    def resetData(self):
        self.crawlGrad.setStart(0, self.height())
        self.crawlGrad.setFinalStop(0, -self.height() * 8)
        self.brush = QtGui.QBrush(self.crawlGrad)
        self.center = self.rect().center()
        self.ratio = self.width() / 720.

        self.titleFont.setPointSize(80 * self.ratio)
        self.bodyFont.setPointSize(42 * self.ratio)
        width = self.width()
        height = self.height()
        srcBottom = height * 1
        poly = QtGui.QPolygonF([
            QtCore.QPointF(0, 0), 
            QtCore.QPointF(width, 0), 
            QtCore.QPointF(width, srcBottom), 
            QtCore.QPointF(0, srcBottom), 
            ])
#        topDelta = width * .375
        topDelta = width * self.topXRatio
#        bottomDelta = width * .03125
        bottomDelta = width * self.bottomXRatio
        top = height * self.topYRatio
        bottom = height * self.bottomYRatio
        poly2 = QtGui.QPolygonF([
            QtCore.QPointF(topDelta, top), 
            QtCore.QPointF(width - topDelta, top), 
            QtCore.QPointF(width + bottomDelta, bottom), 
            QtCore.QPointF(-bottomDelta, bottom), 
            ])
        assert QtGui.QTransform.quadToQuad(poly, poly2, self.transform)
        self.buildText()
#        self.crawlAnimation.setStartValue(self.height())
        if not self.showCrawl:
            inverted = self.transform.inverted()[0]
            self.crawlAnimation.setStartValue(inverted.map(0, self.height())[1])
            self.crawlAnimation.setEndValue(inverted.map(0, -45)[1])
#            print(inverted.map(0, self.crawlText.boundingRect().height() * -.125)[1])
#            print(self.crawlAnimation.startValue(), self.crawlAnimation.endValue())

#            self.crawlAnimation.setStartValue(self.height())
##            self.crawlPos = self.height() * 1.1

    def moveBgd(self, y):
        palette = self.palette()
        bgd = QtGui.QPixmap(self.size())
        qp = QtGui.QPainter(bgd)
        width = self.width()
        height = self.height()
        baseY, deltaY = divmod(y, height)
        qp.drawPixmap(0, 0, self.starField, 0, deltaY, width, height - deltaY)
        qp.setPen(QtCore.Qt.white)
#        qp.drawLine(0, height - deltaY -1, width, height - deltaY - 1)
        qp.drawPixmap(0, height - deltaY, self.starField, 0, 0, width, deltaY)
        qp.end()
        if y > self.moonStart:
            if not self.moonAnimation.state():
                self.moonAnimation.start()
                self.moonPos = height * 2.3
                self.moonDeltaAnimation.setStartValue(-width * .2)
                self.moonDeltaAnimation.start()
                self.subTimer.start()
                self.boomAnimation.finished.connect(lambda: self.osdTimer.start() if self.showOsd else None)
                self.showMoon = True
            self.moonPos -= 2
#            print(self.moonPos)
        palette.setBrush(self.backgroundRole(), QtGui.QBrush(bgd))
        self.setPalette(palette)

    def nextSub(self):
        if self.sub:
            self.subText, timeout = self.sub.pop(0)
            self.subTimer.setInterval(timeout)
            self.subTimer.start()
            self.update()

    def _mousePressEvent(self, event):
        self.headerScaleAnimation.start() if not self.headerScaleAnimation.state() else None
        self.crawlAnimation.start() if not self.crawlAnimation.state() else self.crawlAnimation.stop()

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_O:
            self.showOsd = not self.showOsd
            self.update()
            if self.showOsd:
                if not any(True for a in self.animations if a.state()):
                    self.osdTimer.start()
            elif self.osdTimer.isActive():
                self.osdTimer.stop()
        else:
            QtWidgets.QDialog.keyPressEvent(self, event)

    def updateOsd(self):
        if any(True for a in self.animations if a.state()):
            self.osdTimer.stop()
        else:
            self.osdTimer.timeout.disconnect()
            self.osdTimer.setInterval(33)
            self.osdTimer.timeout.connect(self.update)

    def showEvent(self, event):
        self.resetData()
        if not self.shown:
            self.shown = True
            self.setMinimumSize(self.size())
            self.setMaximumSize(self.size())

    def resizeEvent(self, event):
        if event.oldSize().width() != self.width():
            self.resize(self.width(), int(self.width() / 2.4))
#            print('resetto', self.width(), self.height(), int(self.width() / 2.4))
        self.resetData()

    def paintEvent(self, event):
        QtWidgets.QDialog.paintEvent(self, event)
        qp = QtGui.QPainter(self)
        qp.setRenderHints(qp.Antialiasing)

#        qp.drawLine(self.center.x(), 0, self.center.x(), self.height())
#        qp.drawLine(0, self.center.y(), self.width(), self.center.y())
        if self.showTitle:
            qp.save()
            qp.translate(self.center)
            qp.scale(self._headerScale * self.ratio, self._headerScale * self.ratio)
            qp.setPen(self.headerPen)
            qp.setFont(self.headerFont)
            qp.drawPath(self.header)
            qp.restore()

        if self.showCrawl:
#            o = QtGui.QTextOption()
#            o.setAlignment(QtCore.Qt.AlignTop|QtCore.Qt.AlignJustify)

            qp.setBrush(self.brush)
            qp.translate(0, 50 * self.ratio)
#            qp.scale(1, .8)
            qp.setTransform(self.transform, True)
#            qp.translate(0, self._crawlPos)
#            qp.translate(0, self._crawlPos * 1.2)
#            qp.setPen(QtCore.Qt.NoPen)

#            qp.setPen(self.pen)
#            qp.setFont(self.bodyFont)
#            qp.drawText(self.rect(), QtCore.Qt.AlignTop|QtCore.Qt.AlignHCenter, self.versionText)
#            qp.setFont(self.titleFont)
#            qp.translate(0, QtGui.QFontMetrics(self.bodyFont).height() * 1.5)
#            qp.drawText(self.rect(), QtCore.Qt.AlignTop|QtCore.Qt.AlignHCenter, self.subtitleText)
#            qp.translate(0, QtGui.QFontMetrics(self.titleFont).height() * 1.5)
#            qp.setFont(self.bodyFont)
#            qp.drawText(QtCore.QRectF(self.rect().adjusted(0, 0, 0, self.rect().height() * 4)), self.fullText, o)
            
#            qp.setPen(QtGui.QPen(SWColor(), 2))
#            r = QtCore.QRectF(self.rect().adjusted(self.rect().width() * .2, 0, -self.rect().width() * .2, self.rect().height()))
#            qp.drawRect(self.crawlText.boundingRect())

            qp.setPen(QtCore.Qt.NoPen)
#            qp.setBrush(self.brush)
#            qp.drawPath(self.crawlText)
            qp.drawPath(self.crawlText.translated(0, self._crawlPos))

        if self.showMoon:
#            qp.translate(self.center.x() - (self.midiMoon.width() * .6) * self._moonScale, 
##                (self.center.y() - self.midiMoon.height() * self._moonScale))
#                -self.midiMoon.height() * self._moonScale)
            qp.save()
            qp.scale(self._moonScale, self._moonScale)
            qp.drawPixmap(
#                (self.width() - self.midiMoon.width() * self._moonScale) / self._moonScale * .5, 
#                (self.moonPos - self.midiMoon.height() * self._moonScale) / self._moonScale * .5, 
                ((self.width() + self._moonDelta) / self._moonScale - self.midiMoon.width()) * .5, 
                (self.moonPos / self._moonScale - self.midiMoon.height()) * .45, 
                self.midiMoon)
#            print(self.midiMoon.height() / self._moonScale, self._moonScale)
            qp.restore()

        if self.subText:
            subRect = self.rect().adjusted(0, 0, 0, -self.height() * .02)
            qp.setPen(QtCore.Qt.black)
            qp.setFont(self.subFontBgd)
            qp.drawText(subRect, QtCore.Qt.AlignBottom|QtCore.Qt.AlignHCenter, self.subText)
            qp.setPen(QtCore.Qt.white)
            qp.setFont(self.subFont)
            qp.drawText(subRect, QtCore.Qt.AlignBottom|QtCore.Qt.AlignHCenter, self.subText)

        if self.showBoom:
            qp.fillRect(self.rect(), self._boomColor)

        if self.showOsd:
            qp.setPen(QtCore.Qt.white)
            qp.setFont(self.font())
            qp.setTransform(QtGui.QTransform())
            elapsed = self.elapsedTimer.elapsed()
            text = '{:05.2f}, {}fps'.format(elapsed * .001, int(1000. / (elapsed - self.lastFrame)))
            self.lastFrame = elapsed
            if not self.crawlFadeTimer.isActive():
                self.crawlStart = elapsed
            else:
                fromStart = elapsed - self.crawlStart
                text += '\ncrawlFadeTimer: {:.2f}s ({:.2f})'.format(fromStart * .001, (self.crawlFadeTimer.interval() - fromStart) * .001)
            for ani in self.animations:
                if ani.state():
                    text += '\n{}: {:.2f}s '.format(ani.propertyName(), ani.currentTime() * .001)
                    try:
                        text += '{:.2f}'.format(ani.currentValue())
                    except Exception as e:
#                        print(e, ani.propertyName(), ani.currentValue())
                        text += '{}, {}, {}, {}'.format(*ani.currentValue().getRgb())
            qp.drawText(self.rect(), QtCore.Qt.AlignTop|QtCore.Qt.AlignLeft, text)


class Ctrl(QtWidgets.QWidget):
    def __init__(self, w):
        QtWidgets.QWidget.__init__(self)
        self.w = w
        l = QtWidgets.QGridLayout()
        self.setLayout(l)
        self.topXRatio = QtWidgets.QDoubleSpinBox()
        self.topXRatio.setSingleStep(.01)
        self.topXRatio.setValue(w.topXRatio)
        self.topXRatio.valueChanged.connect(lambda v: [setattr(w, 'topXRatio', v), w.resetData(), w.update()])
        l.addWidget(self.topXRatio)
        self.topYRatio = QtWidgets.QDoubleSpinBox()
        self.topYRatio.setSingleStep(.01)
        self.topYRatio.setValue(w.topYRatio)
        self.topYRatio.valueChanged.connect(lambda v: [setattr(w, 'topYRatio', v), w.resetData(), w.update()])
        l.addWidget(self.topYRatio, 0, 1)
        self.bottomXRatio = QtWidgets.QDoubleSpinBox()
        self.bottomXRatio.setSingleStep(.01)
        self.bottomXRatio.setValue(w.bottomXRatio)
        self.bottomXRatio.valueChanged.connect(lambda v: [setattr(w, 'bottomXRatio', v), w.resetData(), w.update()])
        l.addWidget(self.bottomXRatio)
        self.bottomYRatio = QtWidgets.QDoubleSpinBox()
        self.bottomYRatio.setSingleStep(.01)
        self.bottomYRatio.setValue(w.bottomYRatio)
        self.bottomYRatio.valueChanged.connect(lambda v: [setattr(w, 'bottomYRatio', v), w.resetData(), w.update()])
        l.addWidget(self.bottomYRatio)

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    w = MayTheForce()
    w.show()
#    ctrl = Ctrl(w)
#    ctrl.show()
    sys.exit(app.exec_())
