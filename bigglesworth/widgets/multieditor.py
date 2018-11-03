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
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Maximum)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        self.handleRect = QtCore.QRect()
        self.valueChanged.connect(self.computeHandleRect)

        palette = self.palette()
        handleLight = palette.color(palette.Midlight)
        handleDark = palette.color(palette.Dark)
        self.setStyleSheet('''
            QSlider::groove:horizontal {{
                margin-top: 0px;
                margin-bottom: -1px;
                background: transparent;
                height: 10px;
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

    def computeHandleRect(self):
        option = QtWidgets.QStyleOptionSlider()
        self.initStyleOption(option)
        self.handleRect = self.style().subControlRect(QtWidgets.QStyle.CC_Slider, option, QtWidgets.QStyle.SC_SliderHandle, self)
#        print(self.handleRect)

#    def mousePressEvent(self, event):
#        if event.pos() not in self.handleRect:
#            self.setValue(QtWidgets.QStyle.sliderValueFromPosition(0, 127, event.x(), self.width()))
#        QtWidgets.QSlider.mousePressEvent(self, event)

    def showEvent(self, event):
        if not event.spontaneous():
            self.computeHandleRect()


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
        self.values = [str(v) for v in range(minimum, maximum + 1)]

        self.startHandle = RangeSliderHandle(minimum, maximum)
        layout.addWidget(self.startHandle, 0, QtCore.Qt.AlignTop)
        self.startHandle.valueChanged.connect(self.computeHandleRect)
        self.startHandle.valueChanged.connect(self.emitRangeChanged)

        self.endHandle = RangeSliderHandle(minimum, maximum)
        layout.addWidget(self.endHandle, 0, QtCore.Qt.AlignBottom)
        self.endHandle.setValue(127)
        self.endHandle.valueChanged.connect(self.computeHandleRect)
        self.endHandle.valueChanged.connect(self.emitRangeChanged)

        self.handleRect = QtCore.QRect()
        self.currentHandle = None
        self.deltaPos = None

    def virtualRange(self):
        values = (self.startHandle.value(),  self.endHandle.value())
        return min(values), max(values)

    def stepWidth(self):
        return QtWidgets.QStyle.sliderPositionFromValue(self.minimum, self.maximum, self.maximum, self.startHandle.width()) / float(self.maximum)

    def grooveCoordinates(self):
        left = self.startHandle.mapTo(self, self.startHandle.handleRect.bottomLeft())
        right = self.endHandle.mapTo(self, self.endHandle.handleRect.topRight())
#        print(left, right)

    def emitRangeChanged(self):
        self.rangeChanged.emit(self.startHandle.value(), self.endHandle.value())

    def computeHandleRect(self):
        top = self.startHandle.geometry().bottom() + 1
        height = self.endHandle.geometry().top() - top + 1
        left = min(self.startHandle.handleRect.left(), self.endHandle.handleRect.left()) + self.hMargin
        right = max(self.startHandle.handleRect.right(), self.endHandle.handleRect.right()) + self.hMargin
        width = right - left
        self.handleRect = QtCore.QRect(left, top, width, height)
        self.update()

    def enterEvent(self, event):
        self.hoverEnter.emit()

    def leaveEvent(self, event):
        self.hoverLeave.emit()

    def resizeEvent(self, event):
        QtWidgets.QWidget.resizeEvent(self, event)
        self.startHandle.computeHandleRect()
        self.endHandle.computeHandleRect()
        self.computeHandleRect()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            pos = event.pos()
            x = pos.x()
            y = pos.y()
            if self.startHandle.handleRect.left() <= x <= self.startHandle.handleRect.right() or \
                y < self.startHandle.geometry().bottom() * .8:
                    self.currentHandle = self.startHandle
    #                QtWidgets.QApplication.sendEvent(self.startHandle, event)
            elif self.endHandle.handleRect.left() <= x <= self.endHandle.handleRect.right() or \
                y > self.endHandle.geometry().top() + self.endHandle.height() * .2:
                    self.currentHandle = self.endHandle
            if self.currentHandle:
                x = self.currentHandle.mapFromParent(pos).x()
                self.currentHandle.setValue(QtWidgets.QStyle.sliderValueFromPosition(self.minimum, self.maximum, x, self.currentHandle.width()))
            elif self.virtualRange() != self.range:
                self.deltaPos = pos
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

    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        qp.setRenderHints(qp.Antialiasing)
        qp.translate(.5, .5)
#        qp.drawRect(self.rect().adjusted(0, 0, -1, -1))
        qp.drawRoundedRect(self.handleRect, 2, 2)


class Mixer(QtWidgets.QWidget):
    def __init__(self):
        QtWidgets.QWidget.__init__(self)
        self.setMouseTracking(True)
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        self.sliders = []
        noteNames = ['{} ({})'.format(_noteNumberToName[v].upper(), v) for v in range(128)]
        for s in range(16):
            slider = RangeSlider()
            self.sliders.append(slider)
            layout.addWidget(slider)
            slider.hoverEnter.connect(self.sliderEnter)
            slider.hoverLeave.connect(self.sliderLeave)
            slider.rangeChanged.connect(self.checkSelection)
            slider.values = noteNames

        self.currentSlider = None

        self.piano = PianoKeyboard()
        layout.addWidget(self.piano)
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

    def sliderEnter(self, slider=None):
        if slider is None:
            slider = self.sender()
        self.currentSlider = slider
        self.checkSelection(*slider.virtualRange())

    def checkSelection(self, start, end):
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
#            if _isWhiteKey(last):
#                lastWhite = lastKey
#            else:
#                lastWhite = self.piano.keys[last - 1]
#            rect.setLeft(firstWhite.sceneBoundingRect().left() + 2)
#            rect.setRight(lastWhite.sceneBoundingRect().right() - 2)
#            rect.setHeight(self.piano.sceneRect().height())
#            path.addRect(rect)
#            if firstKey != firstWhite:
#                path.addRect(firstKey.sceneBoundingRect())
#            if lastKey != lastWhite:
#                path.addRect(lastKey.sceneBoundingRect())
            self.background.setVisible(True)
        else:
            self.background.setVisible(False)
        self.selection.setPath(path)

    def sliderLeave(self):
        pass
#        self.currentSlider = None
#        self.selection.setPath(QtGui.QPainterPath())
#        self.background.setVisible(False)

    def deselect(self):
        self.currentSlider = None
        self.selection.setPath(QtGui.QPainterPath())
        self.background.setVisible(False)

    def mouseMoveEvent(self, event):
        if event.pos() not in self.sliders[0].geometry() | self.sliders[-1].geometry():
            self.deselect()

    def leaveEvent(self, event):
        self.deselect()


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    mixer = Mixer()
    mixer.show()
    sys.exit(app.exec_())
