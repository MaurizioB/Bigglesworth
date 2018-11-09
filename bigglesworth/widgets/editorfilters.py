#!/usr/bin/env python2.7

import sys, os
from math import log

os.environ['QT_PREFERRED_BINDING'] = 'PyQt4'

from Qt import QtCore, QtGui, QtWidgets
QtCore.pyqtSignal = QtCore.Signal

sys.path.append('../..')
from bigglesworth.utils import sanitize

def _getCssQColorStr(color):
        return 'rgba({},{},{},{:.0f}%)'.format(color.red(), color.green(), color.blue(), color.alphaF() * 100)

filterBrush = QtGui.QBrush(QtGui.QColor(64, 64, 64))

freqMax = 18000
freqLeft = log(10, freqMax)
freqWidth = 1 - freqLeft
freqLines = []
for m in (10, 100, 1000, 10000):
    for f in range(1, 11):
        freq = f * m
        if freq > freqMax:
            break
        freqLines.append((log(freq, freqMax) - freqLeft) / freqWidth)

Bypass, LP24, LP12, BP24, BP12, HP24, HP12, Notch24, Notch12, CombPlus, CombMinus, PPG = range(12)
filterTypes = Bypass, LP24, LP12, BP24, BP12, HP24, HP12, Notch24, Notch12, CombPlus, CombMinus, PPG
filterNames = (
    'Bypass',
    'LP24', 
    'LP12', 
    'BP24', 
    'BP12', 
    'HP24', 
    'HP12', 
    'Notch24', 
    'Notch12', 
    'CombPlus', 
    'CombMinus', 
    'PPG', 
    )

class FilterPath(QtWidgets.QGraphicsPathItem):
    bypassPath = QtGui.QPainterPath()
    bypassPath.moveTo(-1, .5)
    bypassPath.lineTo(2, .5)
    bypassPath.lineTo(2, 2)
    bypassPath.lineTo(-1, 2)
    bypassPath.closeSubpath()

    lp24Path = QtGui.QPainterPath()
    lp24Path.moveTo(-2, .5)
    lp24Path.lineTo(-.02, .5)
    lp24Path.cubicTo(-.01, .5, -.005, .5, 0, .5)
    lp24Path.cubicTo(.01, .5, .04, 1, .06, 1)
    lp24Path.lineTo(2, 1)
    lp24Path.lineTo(2, 2)
    lp24Path.lineTo(-2, 2)
    lp24Path.closeSubpath()

    lp12Path = QtGui.QPainterPath()
    lp12Path.moveTo(-2, .5)
    lp12Path.lineTo(-.03, .5)
    lp12Path.cubicTo(-.02, .5, -.01, .5, 0, .5)
    lp12Path.cubicTo(.02, .5, .08, 1, .12, 1)
    lp12Path.lineTo(2, 1)
    lp12Path.lineTo(2, 2)
    lp12Path.lineTo(-2, 2)
    lp12Path.closeSubpath()

    bp24Path = QtGui.QPainterPath()
    bp24Path.moveTo(-2, 1)
    bp24Path.lineTo(-.06, 1)
    bp24Path.cubicTo(-.04, 1, -.01, .5, 0, .5)
    bp24Path.cubicTo(.01, .5, .04, 1, .06, 1)
    bp24Path.lineTo(2, 1)
    bp24Path.lineTo(2, 2)
    bp24Path.lineTo(-2, 2)
    bp24Path.closeSubpath()

    bp12Path = QtGui.QPainterPath()
    bp12Path.moveTo(-2, 1)
    bp12Path.lineTo(-.12, 1)
    bp12Path.cubicTo(-.08, 1, -.02, .5, 0, .5)
    bp12Path.cubicTo(.02, .5, .08, 1, .12, 1)
    bp12Path.lineTo(2, 1)
    bp12Path.lineTo(2, 2)
    bp12Path.lineTo(-2, 2)
    bp12Path.closeSubpath()

    hp24Path = QtGui.QPainterPath()
    hp24Path.moveTo(-2, 1)
    hp24Path.lineTo(-.06, 1)
    hp24Path.cubicTo(-.04, 1, -.01, .5, 0, .5)
    hp24Path.cubicTo(.005, .5, .01, .5, .02, .5)
    hp24Path.lineTo(2, .5)
    hp24Path.lineTo(2, 2)
    hp24Path.lineTo(-2, 2)
    hp24Path.closeSubpath()

    hp12Path = QtGui.QPainterPath()
    hp12Path.moveTo(-2, 1)
    hp12Path.lineTo(-.12, 1)
    hp12Path.cubicTo(-.08, 1, -.02, .5, 0, .5)
    hp12Path.cubicTo(.01, .5, .02, .5, .03, .5)
    hp12Path.lineTo(2, .5)
    hp12Path.lineTo(2, 2)
    hp12Path.lineTo(-2, 2)
    hp12Path.closeSubpath()

    notch24Path = QtGui.QPainterPath()
    notch24Path.moveTo(-2, .5)
    notch24Path.lineTo(-.06, .5)
    notch24Path.cubicTo(-.05, .5, -.04, 1, -.02, 1)
    notch24Path.lineTo(.02, 1)
    notch24Path.cubicTo(.04, 1, .05, .5, .06, .5)
    notch24Path.lineTo(2, .5)
    notch24Path.lineTo(2, 2)
    notch24Path.lineTo(-2, 2)
    notch24Path.closeSubpath()

    notch12Path = QtGui.QPainterPath()
    notch12Path.moveTo(-2, .5)
    notch12Path.lineTo(-.12, .5)
    notch12Path.cubicTo(-.1, .5, -.08, 1, -.06, 1)
    notch12Path.lineTo(.06, 1)
    notch12Path.cubicTo(.08, 1, .1, .5, .12, .5)
    notch12Path.lineTo(2, .5)
    notch12Path.lineTo(2, 2)
    notch12Path.lineTo(-2, 2)
    notch12Path.closeSubpath()

    combPlusPath = QtGui.QPainterPath()
    combPlusPath.moveTo(-1, .45)
    combPlusPath.lineTo(-.125, .45)

    combMinusPath = QtGui.QPainterPath()
    combMinusPath.moveTo(-1, .55)
    combMinusPath.lineTo(-.125, .55)

    for c in range(-1, 17):
        x0 = c * .0625
        x1 = x0 + .03125
        x2 = x1 + .03125
        combPlusPath.quadTo(x0, .55, x1, .55)
        combPlusPath.quadTo(x2, .55, x2, .45)
        combMinusPath.quadTo(x1, .55, x1, .45)
        combMinusPath.quadTo(x1, .55, x2, .55)

    combPlusPath.lineTo(2, .45)
    combPlusPath.lineTo(2, 2)
    combPlusPath.lineTo(-2, 2)
    combPlusPath.closeSubpath()

    combMinusPath.lineTo(2, .55)
    combMinusPath.lineTo(2, 2)
    combMinusPath.lineTo(-2, 2)
    combMinusPath.closeSubpath()

    filterPaths = (bypassPath, lp24Path, lp12Path, bp24Path, bp12Path, hp24Path, hp12Path, 
        notch24Path, notch12Path, combPlusPath, combMinusPath, QtGui.QPainterPath(lp24Path))

    def __init__(self, filterType):
        self.basePath = self.filterPaths[filterType]
        QtWidgets.QGraphicsPathItem.__init__(self, self.basePath)
        self.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        self.setBrush(filterBrush)
        self.filterType = filterType
        self.cutoff = 0
        self.resonance = 0
        if not filterType: #bypass
            self.setCutoff = lambda *args: None
            self.setResonance = lambda *args: None
        elif filterType in (LP24, LP12, BP24, BP12, HP24, HP12, PPG):
            self.setCutoff = self.setNormalCutoff
            self.setResonance = self.setNormalResonance
        elif filterType in (Notch24, Notch12):
            self.setCutoff = self.setNormalCutoff
            self.setResonance = lambda *args: None
        elif filterType == CombPlus:
            self.setCutoff = self.setCombCutoff
            self.setResonance = self.setCombResonance
            self.rebuildPath = self.rebuildCombPlus
            self.cutoffRatio = .0625
            self.resonanceTop = .45
            self.resonanceBottom = .55
        elif filterType == CombMinus:
            self.setCutoff = self.setCombCutoff
            self.setResonance = self.setCombResonance
            self.rebuildPath = self.rebuildCombMinus
            self.cutoffRatio = .0625
            self.resonanceTop = .45
            self.resonanceBottom = .55
#            if filterType == HP24:
#                for n in range(self.basePath.elementCount()):
#                    e = self.basePath.elementAt(n)
#                    if e.type >= 2:
#                        print(n, e.type, e.x, e.y)

    def setNormalCutoff(self, cutoff):
        self.cutoff = cutoff / 127.
        self.setPath(self.basePath.translated(self.cutoff, 0))

    def setNormalResonance(self, resonance):
        self.resonance = resonance / 127.
        self.basePath.setElementPositionAt(4, 0, .5 - (self.resonance) * .5)
        self.setPath(self.basePath.translated(self.cutoff, 0))

    def setCombCutoff(self, cutoff):
        self.cutoff = cutoff
        self.cutoffRatio = 8. / (128 - cutoff)
        self.rebuildPath()

    def setCombResonance(self, resonance):
        self.resonance = resonance
        delta = .2 * resonance / 127.
        self.resonanceTop = .45 - delta
        self.resonanceBottom = .55 + delta
        self.rebuildPath()

    def rebuildCombPlus(self):
        path = QtGui.QPainterPath()
        path.moveTo(-10, self.resonanceTop)
        path.lineTo(-self.cutoffRatio * 2, self.resonanceTop)

        for c in range(-1, 17):
            x0 = c * self.cutoffRatio
            x1 = x0 + self.cutoffRatio * .5
            x2 = x1 + self.cutoffRatio * .5
            path.quadTo(x0, self.resonanceBottom, x1, self.resonanceBottom)
            path.quadTo(x2, self.resonanceBottom, x2, self.resonanceTop)

        path.lineTo(2, self.resonanceTop)
        path.lineTo(2, 2)
        path.lineTo(-2, 2)
        path.closeSubpath()
        self.setPath(path)

    def rebuildCombMinus(self):
        path = QtGui.QPainterPath()
        path.moveTo(-10, self.resonanceBottom)
        path.lineTo(-self.cutoffRatio * 2, self.resonanceBottom)

        for c in range(-1, 17):
            x0 = c * self.cutoffRatio
            x1 = x0 + self.cutoffRatio * .5
            x2 = x1 + self.cutoffRatio * .5
            path.quadTo(x1, self.resonanceBottom, x1, self.resonanceTop)
            path.quadTo(x1, self.resonanceBottom, x2, self.resonanceBottom)

        path.lineTo(2, self.resonanceBottom)
        path.lineTo(2, 2)
        path.lineTo(-2, 2)
        path.closeSubpath()
        self.setPath(path)


class FilterScene(QtWidgets.QGraphicsScene):
    cutoffChanged = QtCore.pyqtSignal(int)
    resonanceChanged = QtCore.pyqtSignal(int)

    cutoffPen = QtGui.QPen(QtCore.Qt.lightGray, 1, QtCore.Qt.DashLine)
    cutoffPen.setCosmetic(True)
    resonancePen = QtGui.QPen(QtCore.Qt.lightGray, 1, QtCore.Qt.DotLine)
    resonancePen.setCosmetic(True)
    freqLineTen = QtGui.QPen(QtCore.Qt.darkGray, 1)
    freqLineTen.setCosmetic(True)
    freqLineMid = QtGui.QPen(QtCore.Qt.lightGray, .5)
    freqLineMid.setCosmetic(True)

    def __init__(self, view):
        QtWidgets.QGraphicsScene.__init__(self)
        self.setSceneRect(QtCore.QRectF(0, 0, 1, 1))
        self.view = view
        self.currentFilter = Bypass
        self.filterPaths = []
        for filterType in range(12):
            pathItem = FilterPath(filterType)
            self.addItem(pathItem)
            pathItem.setVisible(filterType == self.currentFilter)
            self.filterPaths.append(pathItem)

        self.cutoff = 0
        self.resonance = 0
        self.cutoffLine = self.addLine(0, -1, 0, 2)
        self.cutoffLine.setZValue(10)
        self.cutoffLine.setPen(self.cutoffPen)
        self.resonanceLine = self.addLine(-1, 0, 2, 0)
        self.resonanceLine.setY(.5)
        self.resonanceLine.setZValue(10)
        self.resonanceLine.setPen(self.resonancePen)

        freqTexts = iter((' 100Hz', ' 1kHz', ' 10kHz'))
        self.normalLines = QtWidgets.QGraphicsItemGroup()
        self.normalLines.setZValue(-1)
        self.addItem(self.normalLines)
        for f, x in enumerate(freqLines, 1):
            if x:
                line = self.addLine(x, -1, x, 2)
                self.normalLines.addToGroup(line)
                if f % 10:
                    line.setPen(self.freqLineMid)
                else:
                    line.setPen(self.freqLineTen)
                    freqText = self.addSimpleText(freqTexts.next())
                    freqText.setFlags(freqText.flags() | freqText.ItemIgnoresTransformations)
                    freqText.setBrush(QtGui.QColor(QtCore.Qt.darkGray))
                    freqText.setX(x)
                    self.normalLines.addToGroup(freqText)

        self.combLines = QtWidgets.QGraphicsItemGroup()
        self.combLines.setZValue(-1)
        self.addItem(self.combLines)
        line = self.addLine(.5, -1, .5, 2)
        line.setPen(self.freqLineTen)
        self.combLines.addToGroup(line)
        for x, text in zip((0, .5, freqText.x()), ('0', '10kHz', '20kHz')):
            freqText = self.addSimpleText(text)
            freqText.setFlags(freqText.flags() | freqText.ItemIgnoresTransformations)
            freqText.setBrush(QtGui.QColor(QtCore.Qt.darkGray))
            freqText.setX(x)
            self.combLines.addToGroup(freqText)
        self.combLines.setVisible(False)

    def setFilter(self, filterType):
        for pathItem in self.filterPaths:
            pathItem.setVisible(pathItem.filterType == filterType)
        self.currentFilter = filterType
        if filterType in (CombPlus, CombMinus):
            self.combLines.setVisible(True)
            self.normalLines.setVisible(False)
        else:
            self.combLines.setVisible(False)
            self.normalLines.setVisible(True)

    def setCutoff(self, cutoff):
        if cutoff == self.cutoff:
            return
        self.cutoff = cutoff
        self.cutoffChanged.emit(cutoff)
        self.cutoffLine.setX(cutoff / 127.)
        for pathItem in self.filterPaths:
            pathItem.setCutoff(cutoff)

    def setResonance(self, resonance):
        if resonance == self.resonance:
            return
        self.resonance = resonance
        self.resonanceChanged.emit(resonance)
        self.resonanceLine.setY(.5 - resonance / 127. * .5)
        for pathItem in self.filterPaths:
            pathItem.setResonance(resonance)

    def mouseMoveEvent(self, event):
        cutoff = sanitize(0, int(event.scenePos().x() * 127), 127)
        self.setCutoff(cutoff)
        resonance = sanitize(0, 127 - int(event.scenePos().y() * 255), 127)
        self.setResonance(resonance)


class FilterView(QtWidgets.QGraphicsView):
    def __init__(self, filter=0, parent=None):
        QtWidgets.QGraphicsView.__init__(self, parent)
        scene = FilterScene(self)
        self.setScene(scene)
        self.filter = filter
        self.currentFilter = scene.currentFilter
        self.setPalette(self.palette())
        self.setRenderHints(QtGui.QPainter.Antialiasing)
        self.setFilter = scene.setFilter
        self.setResonance = scene.setResonance
        self.setCutoff = scene.setCutoff
        self.resonanceChanged = scene.resonanceChanged
        self.cutoffChanged = scene.cutoffChanged

#    def setFilter(self, filterType):
#        self.scene().setFilter(filterType)

    def setPalette(self, palette):
        self.setStyleSheet('''
            border-top: 1px solid {dark};
            border-right: 1px solid {light};
            border-bottom: 1px solid {light};
            border-left: 1px solid {dark};
            border-radius: 4px;
            background: rgb(230, 240, 230);
            '''.format(
                dark=_getCssQColorStr(palette.color(palette.Dark)), 
                light=_getCssQColorStr(palette.color(palette.Midlight)), 
                ))

    def resizeEvent(self, event):
        QtWidgets.QGraphicsView.resizeEvent(self, event)
        self.fitInView(self.sceneRect())


if __name__ == '__main__':
#    if 'linux' in sys.platform:
#        from mididings import run, config, Filter, Call, SYSEX as mdSYSEX
#        from mididings.engine import output_event as outputEvent
#        from mididings.event import SysExEvent as mdSysExEvent

    class FilterTest(QtWidgets.QWidget):
        def __init__(self):
            QtWidgets.QWidget.__init__(self)
            layout = QtWidgets.QGridLayout()
            self.setLayout(layout)
            self.filterView = FilterView()
            layout.addWidget(self.filterView, 0, 0, 1, 5)

            filterCombo = QtWidgets.QComboBox()
            layout.addWidget(filterCombo, 1, 0)
            filterCombo.addItems(filterNames)
            filterCombo.currentIndexChanged.connect(self.filterView.setFilter)

            layout.addWidget(QtWidgets.QLabel('Cutoff:'), 1, 1)
            cutoffSpin = QtWidgets.QSpinBox()
            layout.addWidget(cutoffSpin, 1, 2)
            cutoffSpin.setRange(0, 127)
            cutoffSpin.setSingleStep(8)
            cutoffSpin.valueChanged.connect(self.filterView.setCutoff)
            self.filterView.cutoffChanged.connect(cutoffSpin.setValue)

            layout.addWidget(QtWidgets.QLabel('Reso:'), 1, 3)
            resoSpin = QtWidgets.QSpinBox()
            layout.addWidget(resoSpin, 1, 4)
            resoSpin.setRange(0, 127)
            resoSpin.setSingleStep(8)
            resoSpin.valueChanged.connect(self.filterView.setResonance)
            self.filterView.resonanceChanged.connect(resoSpin.setValue)

            self.setMinimumSize(480, 320)

    app = QtWidgets.QApplication(sys.argv)
    filter = FilterTest()
    filter.show()
    sys.exit(app.exec_())
