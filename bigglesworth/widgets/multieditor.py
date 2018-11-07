#!/usr/bin/env python2.7

import sys, os

os.environ['QT_PREFERRED_BINDING'] = 'PyQt4'

from Qt import QtCore, QtGui, QtWidgets
QtCore.pyqtSignal = QtCore.Signal

from frame import Frame

from pianokeyboard import PianoKeyboard, _isWhiteKey, _noteNumberToName

sys.path.append('../..')

from bigglesworth.widgets import NameEdit
from bigglesworth.utils import loadUi, getName
from bigglesworth.parameters import panRange, arpTempo
from bigglesworth.midiutils import SysExEvent, SYSEX
from bigglesworth.const import INIT, END, IDW, IDE, MULR, MULD

def _getCssQColorStr(color):
    return 'rgba({},{},{},{:.0f}%)'.format(color.red(), color.green(), color.blue(), color.alphaF() * 100)

def avg(v0, v1):
    return (v0 + v1) / 2

shadowBrush = QtGui.QColor(128, 128, 128, 128)
displayBackground = QtGui.QBrush(QtGui.QColor(230, 240, 230))
noteNames = ['{} ({})'.format(_noteNumberToName[v].upper(), v) for v in range(128)]

leftArrowPath = QtGui.QPainterPath()
leftArrowPath.moveTo(0, 14)
leftArrowPath.lineTo(11, 14)
leftArrowPath.lineTo(11, 10)
leftArrowPath.lineTo(15, 15)
leftArrowPath.lineTo(11, 20)
leftArrowPath.lineTo(11, 16)
leftArrowPath.lineTo(0, 16)
leftArrowPath.closeSubpath()

rightArrowPath = QtGui.QPainterPath()
rightArrowPath.moveTo(0, 15)
rightArrowPath.lineTo(4, 10)
rightArrowPath.lineTo(4, 14)
rightArrowPath.lineTo(15, 14)
rightArrowPath.lineTo(15, 16)
rightArrowPath.lineTo(4, 16)
rightArrowPath.lineTo(4, 20)
rightArrowPath.closeSubpath()


class TestMidiDevice(QtCore.QObject):
    midiEvent = QtCore.pyqtSignal(object)
    def __init__(self, main):
        QtCore.QObject.__init__(self)
        self.main = main
        self.backend = -1
        self.main.midiEvent.connect(self.outputEvent)
        try:
            config(
                client_name='Bigglesworth', 
                in_ports=[('Input', 'Virtual.*',  'Blofeld.*')], 
                out_ports=[('Output', 'Blofeld.*', 'aseqdump.*')])
            self.isValid = True
        except:
            self.isValid = False

    def start(self):
        run(Filter(mdSYSEX) >> Call(self.inputEvent))

    def inputEvent(self, event):
        if event.type == mdSYSEX:
            newEvent = SysExEvent(event.port, map(int, event.sysex[1:-1]))
        else:
            return
        self.midiEvent.emit(newEvent)

    def outputEvent(self, event):
        if self.isValid:
            outputEvent(mdSysExEvent(1, event.sysex))


class PartCheckBox(QtWidgets.QCheckBox):
    _path = QtGui.QPainterPath()
    _path.moveTo(-3, 0)
    _path.lineTo(-1, 3)
    _path.lineTo(3, -3)
    _path.lineTo(-1, 1)
    _path.closeSubpath()
    paint = True

    def setReallyVisible(self, paint):
#        self.setEnabled(paint)
        if paint == self.paint:
            return
        self.paint = paint
        self.update()

    def sizeHint(self):
        size = QtGui.QFontMetrics(self.window().font()).height() + 1
        return QtCore.QSize(size, size)

    #override default QCheckBox behavior, which only accounts for the 
    #checkbox and its label
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton and self.paint:
            self.click()
        else:
            event.ignore()

    def resizeEvent(self, event):
        self.squareSize = QtGui.QFontMetrics(self.window().font()).height()
        self.square = QtCore.QRectF(0, 0, self.squareSize, self.squareSize)
        self.square.moveRight(self.width() - 1)
        scale = self.squareSize / 7.
        self.path = self._path.toFillPolygon(QtGui.QTransform().scale(scale, scale))

    def paintEvent(self, event):
        if not self.paint:
            return
        qp = QtGui.QPainter(self)
        qp.setRenderHints(qp.Antialiasing)
        palette = self.palette()
        qp.setPen(palette.color(palette.Mid))
        qp.setBrush(palette.color(palette.Base))
        qp.drawRoundedRect(self.square, 2, 2)
        if self.isChecked():
            qp.setPen(QtCore.Qt.NoPen)
            qp.setBrush(palette.color(palette.Text))
            qp.translate(self.square.center())
            qp.drawPolygon(self.path)


class PathCursor(QtGui.QCursor):
    def __init__(self, path):
        pixmap = QtGui.QPixmap(32, 32)
        pixmap.fill(QtCore.Qt.transparent)
        qp = QtGui.QPainter(pixmap)
        qp.setRenderHints(qp.Antialiasing)
        qp.setPen(QtCore.Qt.white)
        qp.setBrush(QtCore.Qt.black)
        qp.drawPath(path)
        qp.end()
        QtGui.QCursor.__init__(self, pixmap)


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
        self.checkFontColor()

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

    def checkFontColor(self):
        color = self.window().palette().color(QtGui.QPalette.WindowText)
        if color.lightness() >= 127:
            self.fontColor = color.lighter()
        else:
            self.fontColor = color.darker()

    def changeEvent(self, event):
        if event.type() == QtCore.QEvent.FontChange:
            self.computeHandleText()
        elif event.type() == QtCore.QEvent.PaletteChange:
            self.checkFontColor()

    def showEvent(self, event):
        if not event.spontaneous():
            self.computeHandleSizes()

    def paintEvent(self, event):
        QtWidgets.QSlider.paintEvent(self, event)
        qp = QtGui.QPainter(self)
        qp.translate(.5, 1.5)
        font = self.font()
        font.setPointSizeF(self.height() * .8)
        font.setBold(True)
        qp.setFont(font)
        qp.setPen(self.fontColor)
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
        if not self.isEnabled():
            ref.setAlpha(ref.alpha() * .5)
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
        if event.type() in (QtCore.QEvent.PaletteChange, QtCore.QEvent.EnabledChange):
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
        self.leftArrowCursor = PathCursor(leftArrowPath)
        self.rightArrowCursor = PathCursor(rightArrowPath)

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

    def setCurrentRange(self, start, end):
        self.startHandle.setValue(start)
        self.endHandle.setValue(end)

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
        self.unsetCursor()

    def resizeEvent(self, event):
        QtWidgets.QWidget.resizeEvent(self, event)
        self.startHandle.computeHandleSizes()
        self.endHandle.computeHandleSizes()
        self.computeHandleRect()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            pos = event.pos()
            x = event.x()
            y = event.y()
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
                self.setCursor(QtCore.Qt.ClosedHandCursor)

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
        else:
            pos = event.pos()
            x = event.x()
            y = event.y()
            handleTolerance = self.startHandle.height()
            if self.startHandle.handleRect.left() <= x <= self.startHandle.handleRect.right():
                self.setCursor(self.leftArrowCursor)
            elif self.endHandle.handleRect.left() <= x <= self.endHandle.handleRect.right() or \
                y > self.endHandle.geometry().top() + handleTolerance:
                    self.setCursor(self.rightArrowCursor)
            elif y < self.startHandle.geometry().bottom() * .8:
                    self.setCursor(self.leftArrowCursor)
            elif self.currentRange() != self.range and pos in self.handle.geometry().adjusted(0, -handleTolerance, 0, handleTolerance):
                self.setCursor(QtCore.Qt.OpenHandCursor)
            else:
                self.unsetCursor()

    def mouseReleaseEvent(self, event):
        self.currentHandle = self.deltaPos = None
        self.unsetCursor()

    def changeEvent(self, event):
        if event.type() == QtCore.QEvent.PaletteChange:
            self.startHandle.checkFontColor()
            self.endHandle.checkFontColor()

    def showEvent(self, event):
        if not event.spontaneous():
            self.computeHandleRect()
            if not self.toolTip():
                self.setToolTip('{} - {}'.format(self.values[self.startHandle.value()], self.values[self.endHandle.value()]))


class MultiEdit(NameEdit):
    focusChanged = QtCore.pyqtSignal(bool)

    def focusInEvent(self, event):
        self.focusChanged.emit(True)
        NameEdit.focusInEvent(self, event)

    def focusOutEvent(self, event):
        self.focusChanged.emit(False)
        NameEdit.focusOutEvent(self, event)

    def clearFocus(self):
        NameEdit.clearFocus(self)
        self.focusChanged.emit(False)


class DisplaySpinBox(QtWidgets.QSpinBox):
    focusChanged = QtCore.pyqtSignal(bool)

    def focusInEvent(self, event):
        self.focusChanged.emit(True)
        QtWidgets.QSpinBox.focusInEvent(self, event)

    def focusOutEvent(self, event):
        self.focusChanged.emit(False)
        QtWidgets.QSpinBox.focusOutEvent(self, event)

    def clearFocus(self):
        QtWidgets.QSpinBox.clearFocus(self)
        self.focusChanged.emit(False)


class DisplayWidget(QtWidgets.QWidget):
    def __init__(self):
        QtWidgets.QWidget.__init__(self)
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum)
        layout = QtWidgets.QHBoxLayout()
        self.setLayout(layout)
        self.setContentsMargins(0, 0, 0, 0)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(4)

        self.slotSpin = DisplaySpinBox()
        self.slotSpin.setRange(1, 128)
        layout.addWidget(self.slotSpin)
        self.slotSpin.setObjectName('slotSpin')
        self.slotSpin.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum)

        self.nameEdit = MultiEdit()
        layout.addWidget(self.nameEdit)
        self.nameEdit.setWindowFlags(QtCore.Qt.BypassGraphicsProxyWidget)
        self.nameEdit.setText('Init Multi')
        self.nameEdit.setFrame(False)
        self.nameEdit.setObjectName('nameEdit')
        self.nameEdit.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum)

        self.setPalette(self.palette())

    def setPalette(self, palette):
        self.setStyleSheet('''
            QWidget {{
                border-top: 1px solid {dark};
                border-right: 1px solid {light};
                border-bottom: 1px solid {light};
                border-left: 1px solid {dark};
                border-radius: 4px;
                background: rgb(230, 240, 230);
            }}
            DisplayWidget, NameEdit {{
                background: transparent;
                font-family: "Fira Sans";
            }}
            QLabel#nameEdit, NameEdit {{
                font-size: 24px;
                padding-left: 5px;
                margin-right: 4px;
                border-top: .5px solid rgba(240, 240, 220, 128);
                border-left: .5px solid rgba(240, 240, 220, 128);
                border-bottom: .5px solid rgba(220, 220, 200, 64);
                border-right: .5px solid rgba(220, 220, 200, 64);
                border-radius: 4px;
            }}
            #slotSpin {{
                font-size: 12px;
            }}
            '''.format(
                dark=_getCssQColorStr(palette.color(palette.Dark)), 
                light=_getCssQColorStr(palette.color(palette.Midlight)), 
                ))


class DisplayScene(QtWidgets.QGraphicsScene):
    def __init__(self, view):
        QtWidgets.QGraphicsScene.__init__(self)
        self.displayWidget = DisplayWidget()
        self.displayProxy = QtWidgets.QGraphicsProxyWidget()
        self.displayProxy.setWidget(self.displayWidget)

        self.nameEdit = self.displayWidget.nameEdit
        self.slotSpin = self.displayWidget.slotSpin

        self.addItem(self.displayProxy)

    def resizeSceneItems(self, rect):
        self.displayProxy.setGeometry(rect)


class MultiDisplayView(QtWidgets.QGraphicsView):
    def __init__(self, *args, **kwargs):
        QtWidgets.QGraphicsView.__init__(self, *args, **kwargs)
        scene = DisplayScene(self)
        self.setScene(scene)
        self.setBackgroundBrush(displayBackground)
        self.displayWidget = scene.displayWidget
        self.nameEdit = scene.nameEdit
        self.nameEdit.focusChanged.connect(self.updateFocus)
        self.nameEdit.returnPressed.connect(self.nameEdit.clearFocus)
        self.slotSpin = scene.slotSpin
        self.slotSpin.focusChanged.connect(self.updateFocus)
        self.slotSpin.lineEdit().returnPressed.connect(self.slotSpin.clearFocus)
        self.slotSpin = scene.slotSpin

        self.setMaximumHeight((self.font().pointSize() * 2 + self.frameWidth()) * 2)

    def setCurrent(self, index, name):
        self.nameEdit.setText(name)
        self.slotSpin.setValue(index[1] + 1)

    def updateFocus(self, focus=False):
        if focus:
            self.setFocusPolicy(QtCore.Qt.StrongFocus)
            self.setFocus()
        else:
            self.setFocusPolicy(QtCore.Qt.NoFocus)

    def focusOutEvent(self, event):
        QtWidgets.QGraphicsView.focusOutEvent(self, event)
        self.setFocusPolicy(QtCore.Qt.NoFocus)

    def resizeEvent(self, event):
        QtWidgets.QGraphicsView.resizeEvent(self, event)
        rect = QtCore.QRectF(self.viewport().rect())
        self.setSceneRect(rect)
        self.scene().resizeSceneItems(rect)


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

        self.startValueText = QtWidgets.QGraphicsSimpleTextItem(self.startArrow)
        self.startValueText.setPos(-10, 8)
        
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

        self.endValueText = QtWidgets.QGraphicsSimpleTextItem(self.endArrow)
        self.endValueText.setPos(self.view.fontMetrics().width(' '), 8)

        self.hideRange()

    def hideRange(self):
        self.startLine.setVisible(False)
        self.endLine.setVisible(False)
        self.selection.setVisible(False)

    def setRange(self, start, end):
        self.startLine.setX(start)
        self.startLine.setVisible(True)
        self.endLine.setX(end + 1)
        self.endLine.setVisible(True)

        startText = str(start)
        self.startValueText.setText(startText)
        self.startValueText.setX(-self.view.fontMetrics().width(startText + ' '))
        self.endValueText.setText(str(end))

        if start > end:
            self.invalidStart.setVisible(True)
            self.invalidEnd.setVisible(True)
            self.startArrow.setVisible(False)
            self.selection.setVisible(False)
        else:
            self.invalidStart.setVisible(False)
            self.invalidEnd.setVisible(False)
            self.startArrow.setVisible(True)
            minTop = 127 - start
            maxTop = 127 - end
            poly = QtGui.QPolygonF([
                QtCore.QPoint(start, 127), 
                QtCore.QPoint(start, minTop), 
                QtCore.QPoint(end + 1, maxTop), 
                QtCore.QPoint(end + 1, 127)
                ])
            self.selection.setPolygon(poly)
            self.selection.setVisible(True)


class VelocityView(QtWidgets.QGraphicsView):
    def __init__(self, *args, **kwargs):
        QtWidgets.QWidget.__init__(self, *args, **kwargs)
        self.setRenderHints(QtGui.QPainter.Antialiasing)
        self.setBackgroundBrush(displayBackground)
        scene = VelocityScene(self)
        self.setScene(scene)
        self.setRange = scene.setRange
        self.hideRange = scene.hideRange
    
    def sizeHint(self):
        return QtCore.QSize(25, 25)

    def resizeEvent(self, event):
        QtWidgets.QGraphicsView.resizeEvent(self, event)
        self.fitInView(self.sceneRect())


class PartLabel(QtWidgets.QWidget):
    def __init__(self, part):
        QtWidgets.QWidget.__init__(self)
        self.part = str(part + 1)

    def sizeHint(self):
        font = self.font()
        size = font.pointSize() * 2
        return QtCore.QSize(size * 1.5, size)

    def paintEvent(self, event):
        font = self.font()
        font.setPointSizeF(font.pointSize() * 2)
        font.setBold(True)
        qp = QtGui.QPainter(self)
        qp.setFont(font)
        qp.drawText(self.rect(), QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter, self.part)


class RangeEditor(QtWidgets.QWidget):
    rangeChanged = QtCore.pyqtSignal(int, int, int)
    selected = QtCore.pyqtSignal(int, bool)

    def __init__(self):
        QtWidgets.QWidget.__init__(self)
        self.setMouseTracking(True)
        layout = QtWidgets.QGridLayout()
        layout.setHorizontalSpacing(2)
        layout.setVerticalSpacing(2)
        self.setLayout(layout)

        self.sliders = []
        self.selectors = []
        self.labels = []
        selectorSizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Maximum)
        for s in range(16):
            selector = PartCheckBox()
            selector.part = s
            layout.addWidget(selector, s, 0)
            selector.setSizePolicy(selectorSizePolicy)
            selector.setReallyVisible(False)
            selector.toggled.connect(lambda state, part=s: self.setSelected(part, state))
            self.selectors.append(selector)
            label = PartLabel(s)
            layout.addWidget(label, s, 1)
            self.labels.append(label)
            slider = RangeSlider()
            slider.index = s
            self.sliders.append(slider)
            layout.addWidget(slider, s, 2)
            slider.hoverEnter.connect(self.sliderEnter)
            slider.rangeChanged.connect(self.checkSelection)
            slider.rangeChanged.connect(self.emitRangeChanged)

        self.currentSlider = None

    def setSelectable(self, selectable):
        for selector in self.selectors:
            selector.setReallyVisible(selectable)
            if not selectable:
                selector.blockSignals(True)
                selector.setChecked(False)
                selector.blockSignals(False)
        for widget in self.sliders + self.labels:
            widget.setEnabled(not selectable)

    def setSelected(self, part, selected):
        self.sliders[part].setEnabled(selected)
        self.labels[part].setEnabled(selected)
        if isinstance(self.sender(), PartCheckBox):
            self.selected.emit(part, selected)
        else:
            selector = self.selectors[part]
            selector.blockSignals(True)
            selector.setChecked(selected)
            selector.blockSignals(False)

    def setLowValue(self, part, value):
        self.sliders[part].startHandle.setValue(value)

    def setHighValue(self, part, value):
        self.sliders[part].endHandle.setValue(value)

    def sliderEnter(self, slider=None):
        if slider is None:
            slider = self.sender()
        self.currentSlider = slider
        self.checkSelection(*slider.currentRange())

    def emitRangeChanged(self, start, end):
        self.rangeChanged.emit(self.sender().index, start, end)

    def mouseMoveEvent(self, event):
        if event.pos() not in self.sliders[0].geometry() | self.sliders[-1].geometry():
            self.deselect()

    def leaveEvent(self, event):
        self.deselect()


class VelocityRangeEditor(RangeEditor):
    velocityChanged = RangeEditor.rangeChanged

    def __init__(self, *args, **kwargs):
        RangeEditor.__init__(self, *args, **kwargs)
        self.velocity = VelocityView()
        self.layout().addWidget(self.velocity, self.layout().rowCount(), 2, 1, 1)

    def checkSelection(self, start, end):
        self.velocity.setRange(start, end)

    def deselect(self):
        self.currentSlider = None
        self.velocity.hideRange()


class KeyRangeEditor(RangeEditor):
    keyChanged = RangeEditor.rangeChanged

    def __init__(self, *args, **kwargs):
        RangeEditor.__init__(self, *args, **kwargs)
        for slider in self.sliders:
            slider.values = noteNames

        self.piano = PianoKeyboard()
        self.layout().addWidget(self.piano, self.layout().rowCount(), 2, 1, 1)
        self.piano.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Maximum)
        self.piano.setInteractive(False)
        self.piano.firstNote = 0
        self.piano.octaves = 10
        self.piano.noteOffset = 8
        self.piano.showShortcuts = False
        self.selectionColors = QtGui.QColor(255, 0, 0, 128), QtGui.QColor(0, 255, 0, 128)
        self.pianoSelection = self.piano.scene().addPath(QtGui.QPainterPath(), pen=QtGui.QPen(QtCore.Qt.NoPen), brush=self.selectionColors[1])
        self.pianoSelection.setZValue(100)
        self.pianoBackground = self.piano.scene().addRect(self.piano.sceneRect(), pen=QtGui.QPen(QtCore.Qt.NoPen), brush=shadowBrush)
        self.pianoBackground.setZValue(99)
        self.pianoBackground.setVisible(False)

    def checkSelection(self, start, end):
        path = QtGui.QPainterPath()
        if self.currentSlider:
            first = min(start, end)
            last = max(start, end)
            self.pianoSelection.setBrush(self.selectionColors[first == start])
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
            self.pianoBackground.setVisible(True)
        else:
            self.pianoBackground.setVisible(False)
        self.pianoSelection.setPath(path)

    def deselect(self):
        self.currentSlider = None
        self.pianoSelection.setPath(QtGui.QPainterPath())
        self.pianoBackground.setVisible(False)


class Shadow(QtWidgets.QWidget):
    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        qp.fillRect(self.rect(), shadowBrush)


class MultiStrip(Frame):
    invalidBrush = QtGui.QColor('red')
    emptyProgNames = [str(p) for p in range(1, 129)]

    channelChanged = QtCore.pyqtSignal(int, int)
    volumeChanged = QtCore.pyqtSignal(int, int)
    panChanged = QtCore.pyqtSignal(int, int)
    transposeChanged = QtCore.pyqtSignal(int, int)
    detuneChanged = QtCore.pyqtSignal(int, int)
    lowVelChanged = QtCore.pyqtSignal(int, int)
    highVelChanged = QtCore.pyqtSignal(int, int)
    lowKeyChanged = QtCore.pyqtSignal(int, int)
    highKeyChanged = QtCore.pyqtSignal(int, int)
    valueSignals = {
        'channelChanged': ('chanCombo', 'setChannel'), 
        'volumeChanged': ('volumeSlider', 'setVolume'), 
        'panChanged': ('panSlider', 'setPan'), 
        'transposeChanged': ('transDial', 'setTranspose'), 
        'detuneChanged': ('detuneDial', 'setDetune'), 
        'lowVelChanged': ('lowVelDial', 'setLowVel'), 
        'highVelChanged': ('highVelDial', 'setHighVel'), 
        'lowKeyChanged': ('lowKeyDial', 'setLowKey'), 
        'highKeyChanged': ('highKeyDial', 'setHighKey'), 
        }

    playToggled = QtCore.pyqtSignal(int, bool)
    midiToggled = QtCore.pyqtSignal(int, bool)
    usbToggled = QtCore.pyqtSignal(int, bool)
    localToggled = QtCore.pyqtSignal(int, bool)
    modToggled = QtCore.pyqtSignal(int, bool)
    pitchToggled = QtCore.pyqtSignal(int, bool)
    sustainToggled = QtCore.pyqtSignal(int, bool)
    pressureToggled = QtCore.pyqtSignal(int, bool)
    editsToggled = QtCore.pyqtSignal(int, bool)
    progChangeToggled = QtCore.pyqtSignal(int, bool)
    toggleSignals = {
        'playToggled': ('playBtn', 'setPlay'), 
        'midiToggled': ('midiBtn', 'setMidi'), 
        'usbToggled': ('usbBtn', 'setUsb'), 
        'localToggled': ('localBtn', 'setLocal'), 
        'modToggled': ('modBtn', 'setMod'), 
        'pitchToggled': ('pitchBtn', 'setPitch'), 
        'sustainToggled': ('susBtn', 'setSustain'), 
        'pressureToggled': ('pressBtn', 'setPressure'), 
        'editsToggled': ('editsBtn', 'setEdits'), 
        'progChangeToggled': ('progBtn', 'setProgChange'), 
        }

    selected = QtCore.pyqtSignal(int, bool)

    def __init__(self, part):
        Frame.__init__(self)
        loadUi('ui/multistrip.ui', self)
        self.part = part

        self.progCombo.setValueList(self.emptyProgNames)
        self.selectChk.setReallyVisible(False)
        self.selectChk.toggled.connect(self.setSelected)
        self.selectable = False

        self.panSlider.setValueList(panRange)

        self.lowKeyDial.setValueList(noteNames)
        self.highKeyDial.setValueList(noteNames)

        self.lowVelDial.valueChanged.connect(self.checkVelocity)
        self.highVelDial.valueChanged.connect(self.checkVelocity)
        self.lowKeyDial.valueChanged.connect(self.checkKeys)
        self.highKeyDial.valueChanged.connect(self.checkKeys)

        self.velocityValid = True
        self.keyValid = True

        self.playBtn.switchToggled.connect(self.playSwitched)
        self.midiButtons = self.midiBtn, self.usbBtn, self.localBtn
        self.bottomButtons = self.modBtn, self.pitchBtn, self.susBtn, self.pressBtn, self.editsBtn, self.progBtn

        for signalName, (widgetName, slot) in self.valueSignals.items():
            signal = getattr(self, signalName)
            widget = getattr(self, widgetName)
            slot = setattr(self, slot, widget.setValue)
            widget.valueChanged.connect(lambda value, signal=signal, part=part: signal.emit(part, value))
        for signalName, (widgetName, slot) in self.toggleSignals.items():
            signal = getattr(self, signalName)
            widget = getattr(self, widgetName)
            slot = setattr(self, slot, widget.setSwitched)
            widget.switchToggled.connect(lambda state, signal=signal,part=part: signal.emit(part, state))

        self.checkSizes()
        self.isSelected = self.selectChk.isChecked
        self.shadow = Shadow(self)
        self.shadow.setVisible(False)

    def playSwitched(self, state):
        if state:
            self.playBtn.icon = QtGui.QIcon.fromTheme('audio-volume-muted')
            self.playBtn.label = 'MUTE'
        else:
            self.playBtn.icon = QtGui.QIcon.fromTheme('media-playback-start')
            self.playBtn.label = 'PLAY'

    def setSelectable(self, selectable):
        self.selectChk.setReallyVisible(selectable)
        self.selectable = selectable
        if not selectable:
            self.selectChk.blockSignals(True)
            self.selectChk.setChecked(False)
            self.selectChk.blockSignals(False)
            self.setSelected(True)
            self.bankCombo.setEnabled(True)
            self.progCombo.setEnabled(True)
        else:
            self.setSelected(False)

    def setSelected(self, selected):
        self.shadow.setVisible(not selected)
        if not selected:
            self.shadow.setGeometry(self.rect().adjusted(0, self.playBtn.geometry().top(), 0, 0))
        if self.sender() == self.selectChk:
            self.selected.emit(self.part, selected)
        for index in range(self.layout().indexOf(self.playBtn), self.layout().count()):
            item = self.layout().itemAt(index)
            if item:
                if item.widget():
                    widget = item.widget()
                    if widget in (self.bankCombo, self.progCombo):
                        widget.setEnabled(False)
                    else:
                        widget.setEnabled(selected)
                elif item.layout():
                    subLayout = item.layout()
                    for subIndex in range(subLayout.count()):
                        item = subLayout.itemAt(subIndex)
                        if item and item.widget():
                            item.widget().setEnabled(selected)

    def setChannel(self, channel):
        self.chanCombo.setValue(channel)

    def checkVelocity(self):
        self.setVelocityValid(self.lowVelDial.value <= self.highVelDial.value)

    def checkKeys(self):
        self.setKeyValid(self.lowKeyDial.value <= self.highKeyDial.value)

    def setVelocityValid(self, valid):
        if self.velocityValid != valid:
            self.update()
        self.velocityValid = valid

    def setKeyValid(self, valid):
        if self.keyValid != valid:
            self.update()
        self.keyValid = valid

    def checkSizes(self):
        fm = self.fontMetrics()
        width = max(fm.width('Low'), fm.width('High'))
        for dial in (self.lowVelDial, self.highVelDial, self.lowKeyDial, self.highKeyDial):
            dial.setMinimumWidth(width)
        font = self.font()
        font.setPointSizeF(font.pointSize() * .8)
        width = max(fm.width(b.insideText) for b in self.bottomButtons)
        for btn in self.bottomButtons:
            btn.setFont(font)
            btn.setMinimumWidth(width)

    def resetValues(self):
        self.volumeSlider.setValue(self.volumeSlider.defaultValue)
        self.panSlider.setValue(self.panSlider.defaultValue)
        self.transDial.setValue(self.transDial.defaultValue)
        self.detuneDial.setValue(self.detuneDial.defaultValue)
        self.lowKeyDial.setValue(0)
        self.highKeyDial.setValue(127)
        self.lowVelDial.setValue(0)
        self.highKeyDial.setValue(127)

    def resetMidi(self):
        self.chanCombo.setValue(2 + self.part)
        self.playBtn.setSwitched(False)
        for btn in self.midiButtons + self.bottomButtons:
            btn.setSwitched(True)
            #force emit to restore defaults value even if the current state is already True
            btn.switchToggled.emit(True)

    def resetAll(self):
        self.resetValues()
        self.resetMidi()

    def contextMenuEvent(self, event):
        menu = QtWidgets.QMenu()
        menu.setSeparatorsCollapsible(False)
        menu.addSection('Part {}'.format(self.part + 1))
        if self.selectable:
            selectAction = menu.addAction('Group edit')
            selectAction.setCheckable(True)
            selectAction.setChecked(self.selectChk.isChecked())
            selectAction.triggered.connect(self.selectChk.setChecked)
            menu.addSeparator()

        setDefaultsAction = menu.addAction(QtGui.QIcon.fromTheme('edit-undo'), 'Restore all to default')
        setDefaultsAction.triggered.connect(self.resetAll)
        menu.addSeparator()
        setDefaultValuesAction = menu.addAction(QtGui.QIcon.fromTheme('dial'), 'Restore default values')
        setDefaultValuesAction.triggered.connect(self.resetValues)
        setDefaultMidiAction = menu.addAction(QtGui.QIcon.fromTheme('midi'), 'Restore MIDI parameters')
        setDefaultMidiAction.triggered.connect(self.resetMidi)
        if self.selectable and not self.selectChk.isChecked():
            setDefaultsAction.setEnabled(False)
            setDefaultValuesAction.setEnabled(False)
            setDefaultMidiAction.setEnabled(False)

        menu.exec_(QtGui.QCursor.pos())

    def changeEvent(self, event):
        if event.type() in (QtCore.QEvent.PaletteChange, QtCore.QEvent.FontChange):
            self.checkSizes()

    def resizeEvent(self, event):
        if self.shadow.isVisible():
            self.shadow.setGeometry(self.rect().adjusted(0, self.playBtn.geometry().top(), 0, 0))

    def paintEvent(self, event):
        Frame.paintEvent(self, event)
        if self.keyValid and self.velocityValid:
            return
        qp = QtGui.QPainter(self)
        qp.setRenderHints(qp.Antialiasing)
        qp.setPen(QtCore.Qt.NoPen)
        qp.setBrush(self.invalidBrush)
        qp.translate(self.rangeSection.pos())
        if not self.velocityValid:
            qp.drawRoundedRect(self.lowVelDial.geometry() | self.highVelDial.geometry(), 2, 2)
        if not self.keyValid:
            qp.drawRoundedRect(self.lowKeyDial.geometry() | self.highKeyDial.geometry(), 2, 2)


class MultiEditor(QtWidgets.QWidget):
    midiEvent = QtCore.pyqtSignal(object)

    def __init__(self, *args, **kwargs):
        QtWidgets.QWidget.__init__(self, *args, **kwargs)
        loadUi('ui/multieditor.ui', self)
        self.setAutoFillBackground(True)

        if __name__ == '__main__':
            self.midiDevice = TestMidiDevice(self)
            self.midiThread = QtCore.QThread()
            self.midiDevice.moveToThread(self.midiThread)
            self.midiThread.started.connect(self.midiDevice.start)
            self.midiThread.start()
            self.midiDevice.midiEvent.connect(self.midiEventReceived)
            palette = self.palette()
            palette.setColor(palette.Active, palette.Button, QtGui.QColor(124, 240, 110))
            self.setPalette(palette)

        self.tempoDial.setValueList(arpTempo)
        self.requestBtn.clicked.connect(self.sendRequest)
        self.groupEditBtn.switchToggled.connect(self.setGroupEdit)

        self.velocityRangeEditor = VelocityRangeEditor()
        self.stackedWidget.addWidget(self.velocityRangeEditor)
        self.velocityRangeEditor.velocityChanged.connect(self.setVelocities)

        self.keyRangeEditor = KeyRangeEditor()
        self.stackedWidget.addWidget(self.keyRangeEditor)
        self.keyRangeEditor.keyChanged.connect(self.setKeys)

        self.strips = []
        for p in range(16):
            strip = MultiStrip(p)
            self.strips.append(strip)
            strip.label = 'Part {}'.format(p + 1)
            strip.lowKeyChanged.connect(self.keyRangeEditor.setLowValue)
            strip.highKeyChanged.connect(self.keyRangeEditor.setHighValue)
            strip.lowVelChanged.connect(self.velocityRangeEditor.setLowValue)
            strip.highVelChanged.connect(self.velocityRangeEditor.setHighValue)
            strip.velocityBtn.clicked.connect(self.velocityBtn.clicked)
            strip.keyBtn.clicked.connect(self.keyBtn.clicked)
            strip.setChannel(p + 2)
            self.stripLayout.addWidget(strip)

            for signalName, (widgetName, slot) in strip.valueSignals.items() + strip.toggleSignals.items():
                signal = getattr(strip, signalName)
                signal.connect(lambda part, value, slot=slot: self.updateGroup(part, slot, value))

        self.velocityBtn.clicked.connect(self.showVelocities)
        self.keyBtn.clicked.connect(self.showKeys)
        self.mainBtn.clicked.connect(self.showMixer)

    def setGroupEdit(self, active):
        for strip in self.strips:
            strip.setSelectable(active)
            if active:
                strip.selected.connect(self.velocityRangeEditor.setSelected)
                strip.selected.connect(self.keyRangeEditor.setSelected)
            else:
                strip.selected.disconnect(self.velocityRangeEditor.setSelected)
                strip.selected.disconnect(self.keyRangeEditor.setSelected)
        self.velocityRangeEditor.setSelectable(active)
        self.keyRangeEditor.setSelectable(active)
        if active:
            self.velocityRangeEditor.selected.connect(self.setStripSelected)
            self.keyRangeEditor.selected.connect(self.setStripSelected)
        else:
            self.velocityRangeEditor.selected.disconnect(self.setStripSelected)
            self.keyRangeEditor.selected.disconnect(self.setStripSelected)

    def setStripSelected(self, part, selected):
        self.keyRangeEditor.setSelected(part, selected)
        self.velocityRangeEditor.setSelected(part, selected)
        self.strips[part].selectChk.setChecked(selected)

    def updateGroup(self, part, slot, value):
        if self.groupEditBtn.switched:
            for strip in self.strips:
                if strip.part == part or not strip.isSelected():
                    continue
                getattr(strip, slot)(value)

    def setKeys(self, part, low, high):
        self.strips[part].setLowKey(low)
        self.strips[part].setHighKey(high)

    def setVelocities(self, part, low, high):
        self.strips[part].setLowVel(low)
        self.strips[part].setHighVel(high)

    def showMixer(self):
        self.stackedWidget.setCurrentWidget(self.channelPage)
        self.mainBtn.setSwitched(True)
        self.velocityBtn.setSwitched(False)
        self.keyBtn.setSwitched(False)

    def showVelocities(self):
        self.stackedWidget.setCurrentWidget(self.velocityRangeEditor)
        self.mainBtn.setSwitched(False)
        self.velocityBtn.setSwitched(True)
        self.keyBtn.setSwitched(False)

    def showKeys(self):
        self.stackedWidget.setCurrentWidget(self.keyRangeEditor)
        self.mainBtn.setSwitched(False)
        self.velocityBtn.setSwitched(False)
        self.keyBtn.setSwitched(True)

    def sendRequest(self):
        self.groupEditBtn.setSwitched(False)
        deviceId = 0
        bank = self.bankSpin.value()
        prog = self.progSpin.value()
        self.midiEvent.emit(SysExEvent(1, [INIT, IDW, IDE, deviceId, MULR, bank, prog, END]))

    def midiEventReceived(self, event):
        if event.type != SYSEX:
            return
        if not (event.sysex[:2] == [IDW, IDE] and event.sysex[3] == MULD):
            return
        self.multiReceived(event.sysex)

    def multiReceived(self, sysex):
        #ignore checksum (last value)
        multiData = sysex[4:-1]
        index = multiData[:2]
        name = multiData[2:18]
        volume = multiData[19]
        tempo = multiData[20]
        boh = multiData[21:34]
        self.volumeDial.setValue(volume)
        self.tempoDial.setValue(tempo)
#        print('{1}:{2} {0}'.format(getName(name), *index))
        self.display.setCurrent(index, getName(name))
        if boh != [1, 0, 2, 4, 11, 12, 0, 0, 0, 0, 0, 0, 0]:
            print('other data differs: {}'.format(boh))
        for part in range(16):
            data = multiData[34 + part * 24: 34 + (part + 1) * 24]
            strip = self.strips[part]
            strip.setChannel(data[7])
            strip.bankCombo.setValue(data[0])
            strip.progCombo.setValue(data[1])

            strip.setVolume(data[2])
            strip.setPan(data[3])
            #field 4 is probably ignored?
            if data[4] != 0:
                print('field 4 is not 0: {}'.format(data[0]))
            strip.setTranspose(data[5])
            strip.setDetune(data[6])

            strip.setLowKey(data[8])
            strip.setHighKey(data[9])
            strip.setLowVel(data[10])
            strip.setHighVel(data[11])

            midiByte = data[12]
            strip.setMidi(midiByte & 1)
            strip.setUsb(midiByte & 2)
            strip.setLocal(midiByte & 4)
            strip.setPlay(midiByte & 64)

            ctrlByte = data[13]
            strip.setPitch(ctrlByte & 1)
            strip.setMod(ctrlByte & 2)
            strip.setPressure(ctrlByte & 4)
            strip.setSustain(ctrlByte & 8)
            strip.setEdits(ctrlByte & 16)
            strip.setProgChange(ctrlByte & 32)

            if data[14:] != [1, 63, 0, 0, 0, 0, 0, 0, 0, 0]:
                print('final part {} is different! {}'.format(part, data[14:]))


    def changeEvent(self, event):
        if event.type() == QtCore.QEvent.PaletteChange:
            self.display.displayWidget.setPalette(self.palette())

    def resizeEvent(self, event):
        QtWidgets.QWidget.resizeEvent(self, event)
        self.velocityRangeEditor.velocity.setMaximumHeight(self.keyRangeEditor.piano.sizeHint().height())


if __name__ == '__main__':
    if 'linux' in sys.platform:
        from mididings import run, config, Filter, Call, SYSEX as mdSYSEX
        from mididings.engine import output_event as outputEvent
        from mididings.event import SysExEvent as mdSysExEvent

    app = QtWidgets.QApplication(sys.argv)
    multi = MultiEditor()
    multi.show()
    sys.exit(app.exec_())
