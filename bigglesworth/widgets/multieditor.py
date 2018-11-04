#!/usr/bin/env python2.7

import sys, os

os.environ['QT_PREFERRED_BINDING'] = 'PyQt4'

from Qt import QtCore, QtGui, QtWidgets
QtCore.pyqtSignal = QtCore.Signal

from pianokeyboard import PianoKeyboard, _isWhiteKey, _noteNumberToName

def _getCssQColorStr(color):
    return 'rgba({},{},{},{:.0f}%)'.format(color.red(), color.green(), color.blue(), color.alphaF() * 100)

def avg(v0, v1):
    return (v0 + v1) / 2

class RangeSliderHandle(QtWidgets.QSlider):
    valueRequested = QtCore.pyqtSignal(int)

    def __init__(self, minimum=0, maximum=127):
        QtWidgets.QSlider.__init__(self, QtCore.Qt.Horizontal)
        self.setRange(minimum, maximum)
        self._values = [str(v) for v in range(minimum, maximum + 1)]
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Maximum)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        self.handleRect = QtCore.QRect()
        self.valueChanged.connect(self.computeHandleSizes)
        self.valueDoc = QtGui.QTextDocument()

        palette = self.palette()
        handleLight = palette.color(palette.Midlight)
        handleDark = palette.color(palette.Dark)
        self.setStyleSheet('''
            QSlider::groove:horizontal {{
                margin-top: 0px;
                margin-bottom: 0px;
                background: transparent;
            }}
            QSlider::handle {{
                height: 4px;
                width: 10px;
                background: {handleColor};
                border-top: 1px solid {handleLight};
                border-right: 1px solid {handleDark};
                border-bottom: 1px solid {handleDark};
                border-left: 1px solid {handleLight};
                border-radius: 2px;
            }}
        '''.format(
            handleLight=_getCssQColorStr(handleLight), 
            handleDark=_getCssQColorStr(handleDark), 
            handleColor=_getCssQColorStr(QtGui.QColor.fromRgb(*map(lambda c: avg(*c), zip(handleLight.getRgb(), handleDark.getRgb()))))
            ))

    @property
    def values(self):
        return self._values

    @values.setter
    def values(self, values):
        self._values = values
        self.computeHandleText()

    def computeHandleSizes(self):
        option = QtWidgets.QStyleOptionSlider()
        self.initStyleOption(option)
        self.handleRect = self.style().subControlRect(QtWidgets.QStyle.CC_Slider, option, QtWidgets.QStyle.SC_SliderHandle, self)
        self.computeHandleText()

    def computeHandleText(self):
        font = self.font()
        font.setPointSizeF(self.height() * .8)
        self.valueDoc.setDefaultFont(font)
        self.valueDoc.setPlainText(self._values[self.value()])

    def showEvent(self, event):
        if not event.spontaneous():
            self.computeHandleSizes()

    def paintEvent(self, event):
        QtWidgets.QSlider.paintEvent(self, event)
        qp = QtGui.QPainter(self)
        qp.translate(.5, 1.5)
        font = self.font()
        font.setPointSizeF(self.height() * .8)
        qp.setFont(font)
        if self.handleRect.right() + self.handleRect.width() * .5 + self.valueDoc.idealWidth() > self.width():
            rect = QtCore.QRect(0, 0, self.handleRect.left() - self.handleRect.width() * .5, self.height())
            qp.drawText(rect, QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter, self.values[self.value()])
        elif self.value() < self.maximum() - 4:
            rect = self.rect().adjusted(self.handleRect.right() + self.handleRect.width() * .5, 0, 0, 0)
            qp.drawText(rect, QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter, self.values[self.value()])


class RangeHandle(QtWidgets.QWidget):

    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent)
        self.handleGrad = QtGui.QLinearGradient(0, 0, 0, 1)
        self.handleGrad.setCoordinateMode(self.handleGrad.ObjectBoundingMode)
        self.updateColors()
        self.updateShape()

    def updateColors(self):
        palette = self.palette()
        ref = palette.color(palette.Mid)
        self.handleGrad.setColorAt(0, ref.lighter(125))
        self.handleGrad.setColorAt(.4, ref)
        self.handleGrad.setColorAt(.6, ref)
        self.handleGrad.setColorAt(1, ref.darker(150))

    def updateShape(self):
        height = self.height() - 1
        radius = height / 2.
        width = self.width() - radius * 2 - 1
        self.path = QtGui.QPainterPath()
        self.path.moveTo(radius, 0)
        self.path.arcTo(width, 0, height, height, 90, -180)
        self.path.arcTo(0, 0, height, height, -90, -180)

    def changeEvent(self, event):
        if event.type() == QtCore.QEvent.PaletteChange:
            self.updateColors()

    def resizeEvent(self, event):
        self.updateShape()

    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        qp.setRenderHints(qp.Antialiasing)
        qp.setPen(QtCore.Qt.NoPen)
        qp.setBrush(self.handleGrad)
        qp.drawPath(self.path)


class RangeSlider(QtWidgets.QWidget):
    hoverEnter = QtCore.pyqtSignal()
    hoverLeave = QtCore.pyqtSignal()
    rangeChanged = QtCore.pyqtSignal(int, int)

    def __init__(self, minimum=0, maximum=127):
        QtWidgets.QWidget.__init__(self)
        self.setMouseTracking(True)
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        self.hMargin = 2
        self.vMargin = 1
        layout.setContentsMargins(0, 0, 0, 0)
        self.setContentsMargins(self.hMargin, self.vMargin, self.hMargin, self.vMargin)
        self.setMaximumHeight(self.fontMetrics().height() * 2)

        self.minimum = minimum
        self.maximum = maximum
        self.range = minimum, maximum

        self.startHandle = RangeSliderHandle(minimum, maximum)
        layout.addWidget(self.startHandle, 0, QtCore.Qt.AlignTop)
        self.startHandle.valueChanged.connect(self.computeHandleRect)
        self.startHandle.valueChanged.connect(self.emitRangeChanged)

        self.endHandle = RangeSliderHandle(minimum, maximum)
        layout.addWidget(self.endHandle, 0, QtCore.Qt.AlignBottom)
        self.endHandle.setValue(127)
        self.endHandle.valueChanged.connect(self.computeHandleRect)
        self.endHandle.valueChanged.connect(self.emitRangeChanged)

        self.values = [str(v) for v in range(minimum, maximum + 1)]
        self.handle = RangeHandle(self)
        self.currentHandle = None
        self.deltaPos = None
        self.cachedValid = True

    @property
    def values(self):
        return self._values

    @values.setter
    def values(self, values):
        self._values = values
        self.startHandle.values = values
        self.endHandle.values = values

    def currentRange(self):
        return self.startHandle.value(),  self.endHandle.value()

    def virtualRange(self):
        values = (self.currentRange())
        return min(values), max(values)

    def stepWidth(self):
        return QtWidgets.QStyle.sliderPositionFromValue(self.minimum, self.maximum, self.maximum, self.startHandle.width()) / float(self.maximum)

#    def grooveCoordinates(self):
#        left = self.startHandle.mapTo(self, self.startHandle.handleRect.bottomLeft())
#        right = self.endHandle.mapTo(self, self.endHandle.handleRect.topRight())
#        print(left, right)

    def emitRangeChanged(self):
        self.rangeChanged.emit(*self.currentRange())
        if self.startHandle.value() > self.endHandle.value():
            if self.cachedValid:
                palette = self.palette()
                palette.setColor(palette.Mid, QtGui.QColor(QtCore.Qt.red))
                self.handle.setPalette(palette)
                self.cachedValid = False
        elif not self.cachedValid:
            self.handle.setPalette(self.palette())
            self.cachedValid = True

    def computeHandleRect(self):
        top = self.startHandle.geometry().bottom() + 1
        height = self.endHandle.geometry().top() - top + 1
        left = min(self.startHandle.handleRect.left(), self.endHandle.handleRect.left()) + self.hMargin
        right = max(self.startHandle.handleRect.right(), self.endHandle.handleRect.right()) + self.hMargin
        width = right - left
#        self.handleRect = QtCore.QRect(left, top, width, height)
        self.handle.setGeometry(left, top, width, height)
        self.update()

    def enterEvent(self, event):
        self.hoverEnter.emit()

    def leaveEvent(self, event):
        self.hoverLeave.emit()

    def resizeEvent(self, event):
        QtWidgets.QWidget.resizeEvent(self, event)
        self.startHandle.computeHandleSizes()
        self.endHandle.computeHandleSizes()
        self.computeHandleRect()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            pos = event.pos()
            x = pos.x()
            y = pos.y()
            #y detection is splitted to avoid startHandle stealing focus
            if self.startHandle.handleRect.left() <= x <= self.startHandle.handleRect.right():
                self.currentHandle = self.startHandle
            elif self.endHandle.handleRect.left() <= x <= self.endHandle.handleRect.right() or \
                y > self.endHandle.geometry().top() + self.endHandle.height() * .2:
                    self.currentHandle = self.endHandle
            elif y < self.startHandle.geometry().bottom() * .8:
                    self.currentHandle = self.startHandle
            if self.currentHandle:
                x = self.currentHandle.mapFromParent(pos).x()
                self.currentHandle.setValue(QtWidgets.QStyle.sliderValueFromPosition(self.minimum, self.maximum, x, self.currentHandle.width()))
            elif self.currentRange() != self.range:
                self.deltaPos = pos
                if self.startHandle.value() > self.endHandle.value():
                    end, start = self.currentRange()
                    self.startHandle.blockSignals(True)
                    self.startHandle.setValue(start)
                    self.startHandle.blockSignals(False)
                    self.endHandle.blockSignals(True)
                    self.endHandle.setValue(end)
                    self.endHandle.blockSignals(False)
                self.refValue = self.startHandle.value()

    def mouseDoubleClickEvent(self, event):
        if self.virtualRange() != self.range:
            self.startHandle.setValue(self.minimum)
            self.endHandle.setValue(self.maximum)

    def mouseMoveEvent(self, event):
        if self.currentHandle:
            x = self.currentHandle.mapFromParent(event.pos()).x()
            value = QtWidgets.QStyle.sliderValueFromPosition(self.minimum, self.maximum, x, self.currentHandle.width())
            self.currentHandle.setValue(value)
            pos = QtCore.QPoint(QtGui.QCursor.pos().x(), self.mapToGlobal(self.rect().bottomLeft()).y())
            self.setToolTip('{} - {}'.format(self.values[self.startHandle.value()], self.values[self.endHandle.value()]))
            QtWidgets.QToolTip.showText(pos, self.values[value])
        elif self.deltaPos is not None:
            delta = float(event.x() - self.deltaPos.x()) / self.stepWidth()
            vRange = self.virtualRange()
            diff = max(vRange) - min(vRange)
            start = max(self.minimum, min(self.maximum - diff, self.refValue + delta))
            self.startHandle.setValue(start)
            self.endHandle.setValue(start + diff)
            pos = QtCore.QPoint(QtGui.QCursor.pos().x(), self.mapToGlobal(self.rect().bottomLeft()).y())
            tooltip = '{} - {}'.format(self.values[self.startHandle.value()], self.values[self.endHandle.value()])
            self.setToolTip(tooltip)
            QtWidgets.QToolTip.showText(pos, tooltip)

    def mouseReleaseEvent(self, event):
        self.currentHandle = self.deltaPos = None

    def showEvent(self, event):
        if not event.spontaneous():
            self.computeHandleRect()
            if not self.toolTip():
                self.setToolTip('{} - {}'.format(self.values[self.startHandle.value()], self.values[self.endHandle.value()]))


class VelocityScene(QtWidgets.QGraphicsScene):
    def __init__(self, view):
        QtWidgets.QGraphicsScene.__init__(self)
        self.view = view
        self.setSceneRect(0, 0, 128, 127)

        noPen = QtGui.QPen(QtCore.Qt.NoPen)
        noBrush = QtGui.QBrush(QtCore.Qt.NoBrush)
        black = QtGui.QColor(QtCore.Qt.black)

        triangle = QtGui.QPolygonF([
            QtCore.QPoint(0, 127), 
            QtCore.QPoint(128, 0), 
            QtCore.QPoint(128, 127)
        ])
        self.addPolygon(triangle, noPen, QtGui.QBrush(QtCore.Qt.lightGray))

        self.selection = self.addPolygon(QtGui.QPolygonF(), noPen, QtGui.QBrush(QtCore.Qt.darkGray))

        linePen = QtGui.QPen(QtCore.Qt.black, 1.)
        linePen.setCosmetic(True)

        invalidPen = QtGui.QPen(QtCore.Qt.black, 2)
        invalidPen.setCosmetic(True)
        invalidPath = QtGui.QPainterPath()
        invalidPath.lineTo(4, 4)
        invalidPath.moveTo(4, 0)
        invalidPath.lineTo(0, 4)

        self.startLine = self.addLine(QtCore.QLineF(0, -10, 0, 150), linePen)
        startArrowPath = QtGui.QPainterPath()
        startArrowPath.moveTo(-5, 2)
        startArrowPath.lineTo(-2, 5)
        startArrowPath.lineTo(-5, 7)
        startArrowPath.closeSubpath()
        self.startArrow = QtWidgets.QGraphicsPathItem(startArrowPath, self.startLine)
        self.startArrow.setFlags(self.startArrow.flags() ^ self.startArrow.ItemIgnoresTransformations)
        self.startArrow.setPen(noPen)
        self.startArrow.setBrush(black)
        self.invalidStart = QtWidgets.QGraphicsPathItem(invalidPath.translated(-7, 2), self.startLine)
        self.invalidStart.setFlags(self.startArrow.flags())
        self.invalidStart.setPen(invalidPen)
        self.invalidStart.setBrush(noBrush)
        self.invalidStart.setVisible(False)
        
        self.endLine = self.addLine(QtCore.QLineF(0, -10, 0, 150), linePen)
        self.endLine.setX(128)
        endArrowPath = QtGui.QPainterPath()
        endArrowPath.moveTo(5, 2)
        endArrowPath.lineTo(2, 5)
        endArrowPath.lineTo(5, 7)
        endArrowPath.closeSubpath()
        self.endArrow = QtWidgets.QGraphicsPathItem(endArrowPath, self.endLine)
        self.endArrow.setFlags(self.startArrow.flags())
        self.endArrow.setPen(noPen)
        self.endArrow.setBrush(black)
        self.invalidEnd = QtWidgets.QGraphicsPathItem(invalidPath.translated(3, 2), self.endLine)
        self.invalidEnd.setFlags(self.startArrow.flags())
        self.invalidEnd.setPen(invalidPen)
        self.invalidEnd.setBrush(noBrush)
        self.invalidEnd.setVisible(False)

        self.hideRange()

    def hideRange(self):
        self.startLine.setVisible(False)
        self.endLine.setVisible(False)
        self.selection.setVisible(False)

    def setRange(self, minimum, maximum):
        self.startLine.setX(minimum)
        self.startLine.setVisible(True)
        self.endLine.setX(maximum + 1)
        self.endLine.setVisible(True)
        if minimum > maximum:
            self.invalidStart.setVisible(True)
            self.invalidEnd.setVisible(True)
            self.startArrow.setVisible(False)
            self.selection.setVisible(False)
        else:
            self.invalidStart.setVisible(False)
            self.invalidEnd.setVisible(False)
            self.startArrow.setVisible(True)
            minTop = 127 - minimum
            maxTop = 127 - maximum
            poly = QtGui.QPolygonF([
                QtCore.QPoint(minimum, 127), 
                QtCore.QPoint(minimum, minTop), 
                QtCore.QPoint(maximum + 1, maxTop), 
                QtCore.QPoint(maximum + 1, 127)
                ])
            self.selection.setPolygon(poly)
            self.selection.setVisible(True)


class VelocityView(QtWidgets.QGraphicsView):
    def __init__(self, *args, **kwargs):
        QtWidgets.QWidget.__init__(self, *args, **kwargs)
        self.setRenderHints(QtGui.QPainter.Antialiasing)
        self.setBackgroundBrush(QtGui.QBrush(QtGui.QColor(230, 240, 230)))
        scene = VelocityScene(self)
        self.setScene(scene)
        self.setRange = scene.setRange
        self.hideRange = scene.hideRange
    
    def sizeHint(self):
        return QtCore.QSize(25, 25)

    def resizeEvent(self, event):
        self.fitInView(self.sceneRect())


class Mixer(QtWidgets.QWidget):
    def __init__(self):
        QtWidgets.QWidget.__init__(self)
        self.setMouseTracking(True)
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        self.tabBar = QtWidgets.QTabBar()
        layout.addWidget(self.tabBar)
        self.tabBar.addTab('Key range')
        self.tabBar.addTab('Velocity range')

        self.sliders = []
        noteNames = ['{} ({})'.format(_noteNumberToName[v].upper(), v) for v in range(128)]
        for s in range(16):
            slider = RangeSlider()
            self.sliders.append(slider)
            layout.addWidget(slider)
            slider.hoverEnter.connect(self.sliderEnter)
            slider.rangeChanged.connect(self.checkSelection)
            slider.values = noteNames

        self.currentSlider = None

        self.stacked = QtWidgets.QStackedWidget()
        layout.addWidget(self.stacked)
        self.tabBar.currentChanged.connect(self.stacked.setCurrentIndex)
        self.stacked.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum)

        self.piano = PianoKeyboard()
        self.stacked.addWidget(self.piano)
        self.piano.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Maximum)
        self.piano.setInteractive(False)
        self.piano.firstNote = 0
        self.piano.octaves = 10
        self.piano.noteOffset = 8
        self.piano.showShortcuts = False
        self.selectionColors = QtGui.QColor(255, 0, 0, 128), QtGui.QColor(0, 255, 0, 128)
        self.selection = self.piano.scene().addPath(QtGui.QPainterPath(), pen=QtGui.QPen(QtCore.Qt.NoPen), brush=self.selectionColors[1])
        self.selection.setZValue(100)
        self.background = self.piano.scene().addRect(self.piano.sceneRect(), pen=QtGui.QPen(QtCore.Qt.NoPen), brush=QtGui.QColor(128, 128, 128, 128))
        self.background.setZValue(99)
        self.background.setVisible(False)

        self.velocity = VelocityView()
        self.stacked.addWidget(self.velocity)
#        self.stacked.setCurrentIndex(1)

    def sliderEnter(self, slider=None):
        if slider is None:
            slider = self.sender()
        self.currentSlider = slider
        self.checkSelection(*slider.currentRange())

    def checkSelection(self, start, end):
        self.velocity.setRange(start, end)
        path = QtGui.QPainterPath()
        if self.currentSlider:
            first = min(start, end)
            last = max(start, end)
            self.selection.setBrush(self.selectionColors[first == start])
            path.setFillRule(QtCore.Qt.WindingFill)

            firstKey = self.piano.keys[first]
            whiteRect = blackRect = preClear = postClear = False
            if first == last and not _isWhiteKey(first):
                blackRect = firstKey.sceneBoundingRect()
            else:
                absFirst = first % 12
                if absFirst in (0, 5):
                    whiteRect = firstKey.sceneBoundingRect()
                elif absFirst in (2, 4, 7, 9, 11):
                    whiteRect = firstKey.sceneBoundingRect()
                    preClear = self.piano.keys[first - 1].sceneBoundingRect()
                else:
                    whiteRect = self.piano.keys[first + 1].sceneBoundingRect()
                    blackRect = firstKey.sceneBoundingRect()
                lastKey = self.piano.keys[last]
                absLast = last % 12
                if absLast in (4, 11):
                    if whiteRect:
                        whiteRect.setRight(lastKey.sceneBoundingRect().right())
                    else:
                        whiteRect = lastKey.sceneBoundingRect().right()
                elif absLast in (0, 2, 5, 7, 9):
                    if whiteRect:
                        whiteRect.setRight(lastKey.sceneBoundingRect().right())
                    else:
                        whiteRect = lastKey.sceneBoundingRect().right()
                    if last < 127:
                        postClear = self.piano.keys[last + 1].sceneBoundingRect()
                else:
                    if whiteRect:
                        whiteRect.setRight(self.piano.keys[last - 1].sceneBoundingRect().right())
                    else:
                        whiteRect = self.piano.keys[last - 1].sceneBoundingRect()
                    if blackRect:
                        blackRect.setRight(lastKey.sceneBoundingRect().right())
                    else:
                        blackRect = lastKey.sceneBoundingRect()
            region = QtGui.QRegion()
            if whiteRect:
                region += QtGui.QRegion(whiteRect.toRect().adjusted(-1, 0, 1, 0))
            if blackRect:
                region += QtGui.QRegion(blackRect.toRect().adjusted(-2, 0, 1, 0))
            if preClear:
                region -= QtGui.QRegion(preClear.toRect())
            if postClear:
                region -= QtGui.QRegion(postClear.toRect())
            path.addRegion(region)
            self.background.setVisible(True)
        else:
            self.background.setVisible(False)
        self.selection.setPath(path)

    def deselect(self):
        self.currentSlider = None
        self.selection.setPath(QtGui.QPainterPath())
        self.background.setVisible(False)

    def mouseMoveEvent(self, event):
        if event.pos() not in self.sliders[0].geometry() | self.sliders[-1].geometry():
            self.deselect()

    def leaveEvent(self, event):
        self.deselect()
        self.velocity.hideRange()


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    mixer = Mixer()
    mixer.show()
    sys.exit(app.exec_())
