#!/usr/bin/env python2.7
# *-* encoding: utf-8 *-*

from random import randrange
import os
os.environ['QT_PREFERRED_BINDING'] = 'PyQt4'
from threading import Lock

from Qt import QtCore, QtGui, QtWidgets
QtCore.pyqtSignal = QtCore.Signal

from bigglesworth.widgets import GraphicsButton, CloseBtn

CursorList = []
MoveCursor, UpCursor, DownCursor, LeftCursor, RightCursor = range(5)

_steps = 'Normal', 'Pause', 'Previous', 'First', 'Last', 'First+Last', 'Chord', 'Random'
_glide = 'No glide', 'Glide'
_accents = 'Silent', '/4', '/3', '/2', '*1', '*2', '*3', '*4'
_lengths = 'Legato', '-3', '-2', '-1', '0', '+1', '+2', '+3'
_timings = 'Random', '-3', '-2', '-1', '0', '+1', '+2', '+3'

STEP, GLIDE, ACCENT, TIMING, LENGTH = range(5)

def _getCssQColorStr(color):
        return 'rgba({},{},{},{:.0f}%)'.format(color.red(), color.green(), color.blue(), color.alphaF() * 100)

def setBold(item, bold=True):
    font = item.font()
    font.setBold(bold)
    item.setFont(font)


class DirCursorClass(QtGui.QCursor):
    limit_pen = QtGui.QPen(QtCore.Qt.black, 2)
    limit_pen.setCapStyle(QtCore.Qt.RoundCap)
    arrow_pen = QtGui.QPen(QtCore.Qt.black, 1)
    arrow_pen.setCapStyle(QtCore.Qt.RoundCap)
    brush = QtGui.QBrush(QtCore.Qt.black)


class UpCursorClass(DirCursorClass):
    def __init__(self):
        pixmap = QtGui.QPixmap(32, 32)
        pixmap.fill(QtCore.Qt.transparent)
        qp = QtGui.QPainter(pixmap)
        qp.setRenderHints(QtGui.QPainter.Antialiasing)
        qp.translate(.5, .5)
        qp.setPen(self.limit_pen)
        qp.drawLine(0, 1, 15, 1)
        qp.setPen(self.arrow_pen)
        qp.setBrush(self.brush)
        path = QtGui.QPainterPath()
        path.moveTo(7.5, 1)
        path.lineTo(12, 8)
        path.lineTo(3, 8)
        path.closeSubpath()
        qp.drawPath(path)
        del qp
        DirCursorClass.__init__(self, pixmap, 8, 1)


class DownCursorClass(DirCursorClass):
    def __init__(self):
        pixmap = QtGui.QPixmap(32, 32)
        pixmap.fill(QtCore.Qt.transparent)
        qp = QtGui.QPainter(pixmap)
        qp.setRenderHints(QtGui.QPainter.Antialiasing)
        qp.translate(.5, .5)
        qp.setPen(self.limit_pen)
        qp.drawLine(0, 8, 15, 8)
        qp.setPen(self.arrow_pen)
        qp.setBrush(self.brush)
        path = QtGui.QPainterPath()
        path.moveTo(3, 1)
        path.lineTo(12, 1)
        path.lineTo(7.5, 7)
        path.closeSubpath()
        qp.drawPath(path)
        del qp
        DirCursorClass.__init__(self, pixmap, 8, 8)


class LeftCursorClass(DirCursorClass):
    def __init__(self):
        pixmap = QtGui.QPixmap(32, 32)
        pixmap.fill(QtCore.Qt.transparent)
        qp = QtGui.QPainter(pixmap)
        qp.setRenderHints(QtGui.QPainter.Antialiasing)
        qp.translate(.5, .5)
        qp.setPen(self.limit_pen)
        qp.drawLine(1, 0, 1, 15)
        qp.setPen(self.arrow_pen)
        qp.setBrush(self.brush)
        path = QtGui.QPainterPath()
        path.moveTo(1, 7.5)
        path.lineTo(8, 12)
        path.lineTo(8, 3)
        path.closeSubpath()
        qp.drawPath(path)
        del qp
        DirCursorClass.__init__(self, pixmap, 1, 8)


class RightCursorClass(DirCursorClass):
    def __init__(self):
        pixmap = QtGui.QPixmap(32, 32)
        pixmap.fill(QtCore.Qt.transparent)
        qp = QtGui.QPainter(pixmap)
        qp.setRenderHints(QtGui.QPainter.Antialiasing)
        qp.translate(.5, .5)
        qp.setPen(self.limit_pen)
        qp.drawLine(8, 0, 8, 15)
        qp.setPen(self.arrow_pen)
        qp.setBrush(self.brush)
        path = QtGui.QPainterPath()
        path.moveTo(1, 3)
        path.lineTo(1, 12)
        path.lineTo(7, 7.5)
        path.closeSubpath()
        qp.drawPath(path)
        del qp
        DirCursorClass.__init__(self, pixmap, 8, 8)


class SpinLineEdit(QtWidgets.QLineEdit):
    def __init__(self):
        QtWidgets.QLineEdit.__init__(self)
        self.setReadOnly(True)
#        self.setStyleSheet('''
#            QLineEdit {
#                color: red;
#                border: 1px solid green;
#                selection-color: red;
#                selection-background-color: transparent;
#            }''')

    def paintEvent(self, event):
        return
        option = QtWidgets.QStyleOptionFrame()
        self.initStyleOption(option)
        qp = QtWidgets.QStylePainter(self)
        qp.drawPrimitive(QtWidgets.QStyle.PE_PanelLineEdit, option)
        qp.drawItemText(self.style().subElementRect(QtWidgets.QStyle.SE_LineEditContents, option, self), 
            QtCore.Qt.AlignCenter, self.palette(), True, 'suca')


class ArpSpinBox(QtWidgets.QSpinBox):
    baseStyleSheet = '''
            ArpSpinBox {{
                border: 1px solid rgba(220, 220, 200, 80);
                color: rgb(30, 50, 40);
                border-radius: 2px;
                /*min-width: 20px;*/
                width: 0px;
                padding-right: {right}px;
                padding-left: {left}px;
                background: transparent;
            }}
            ArpSpinBox:hover {{
                border: 1px solid;
                border-color: rgba(200, 200, 200, 180) rgba(180, 180, 180, 180) rgba(180, 180, 180, 180) rgba(200, 200, 200, 180);
                background: rgba(220, 220, 220, 120);
            }}
            ArpSpinBox::up-button, ArpSpinBox::down-button {{
                border: none;
                background-color: transparent;
                width: 8;
            }}
            ArpSpinBox::up-arrow, ArpSpinBox::down-arrow {{
                width: 0px;
                height: 0px;
                border-right: 4px solid rgba(1, 1, 1, 0);
                border-left: 4px solid rgba(1, 1, 1, 0);
                border-top: 4px solid rgb(30, 50, 40);
                border-bottom: 4px solid rgb(30, 50, 40);
            }}
            ArpSpinBox::down-arrow:disabled, ArpSpinBox::down-arrow:off {{
                border-top: 4px solid gray;
            }}
            ArpSpinBox::up-arrow:disabled, ArpSpinBox::up-arrow:off {{
                border-bottom: 4px solid gray;
            }}
            ArpSpinBox::up-arrow {{
                border-top-width: 0;
            }}
            ArpSpinBox::down-arrow {{
                border-bottom-width: 0;
            }}
            '''
    shown = False

    def __init__(self, step, valueList):
        QtWidgets.QSpinBox.__init__(self)
        self.step = step
        self.valueList = valueList
        self.minWidth = 0
        for item in valueList:
            if isinstance(item, QtGui.QPainterPath):
                self.minWidth = max(self.minWidth, item.boundingRect().width())
            else:
                self.minWidth = max(self.minWidth, self.fontMetrics().width(item))
#        print(self.minWidth)
        self.setRange(0, len(valueList) - 1)
        self.setLineEdit(SpinLineEdit())
        self.setContextMenuPolicy(QtCore.Qt.NoContextMenu)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred))
        self.setButtonSymbols(self.NoButtons)
#        halfWidth = self.minWidth // 2
        self.setStyleSheet(self.baseStyleSheet.format(right=0, left=0))
#        print(8 + self.minWidth)

    def showEvent(self, event):
        if not self.shown:
            self.shown = True
            #avoid tooltip shown while loading
            self.valueChanged.connect(self.resetToolTip)

    def resetToolTip(self, value):
        try:
            QtWidgets.QToolTip.showText(QtGui.QCursor.pos(), self.valueListStr[value])
        except Exception as e:
            print(e)
            self.setToolTip('')

    def event(self, event):
        if event.type() == QtCore.QEvent.ToolTip:
            try:
                self.setToolTip(self.valueListStr[self.value()])
            except:
                self.setToolTip('')
        return QtWidgets.QSpinBox.event(self, event)

    def enterEvent(self, event):
        self.setButtonSymbols(self.UpDownArrows)

    def leaveEvent(self, event):
        self.setButtonSymbols(self.NoButtons)

    def paintEvent(self, event):
#        print(self.sizeHint(), self.width())
        option = QtWidgets.QStyleOptionSpinBox()
        self.initStyleOption(option)
        qp = QtWidgets.QStylePainter(self)
#        qp = QtGui.QPainter(self)
        qp.save()
#        qp.translate(.5, .5)
        qp.setPen(QtCore.Qt.NoPen)
        qp.setBrush(QtGui.QColor(240, 240, 220, 160))
        qp.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 2, 2)
        qp.restore()
        qp.drawComplexControl(QtWidgets.QStyle.CC_SpinBox, option)
        textRect = self.style().subControlRect(QtWidgets.QStyle.CC_SpinBox, option, QtWidgets.QStyle.SC_SpinBoxEditField, self)
        textRect.setWidth(self.minWidth + 2)
#        textRect.setLeft(-self.minWidth * .5)
#        print(self.style().subControlRect(QtWidgets.QStyle.CC_SpinBox))
        value = self.valueList[self.value()]
        if isinstance(value, (str, unicode)):
#            print(textRect, self.width())
            qp.drawItemText(textRect, 
                QtCore.Qt.AlignHCenter|QtCore.Qt.AlignTop, self.palette(), True, unicode(value))
        else:
            qp.translate(.5, .5)
            qp.setRenderHints(qp.Antialiasing)
            qp.setBrush(qp.pen().color())
            qp.translate(textRect.center())
            qp.drawPath(value)

    def resizeEvent(self, event):
        return
        if event.oldSize().isValid() and event.size().width() >= event.oldSize().width():
            right = self.width() - 10
            left = 4
        else:
            right = self.minWidth
            left = 0
        self.setStyleSheet(self.baseStyleSheet.format(
                right=right, 
                left=left, 
                ))
        self.updateGeometry()


class StepSpinBox(ArpSpinBox):
    valueListStr = _steps
    def __init__(self, step):
        valueList = [u'⬤', u'◯', u'◀', u'▼', u'▲']

        firstLastPath = QtGui.QPainterPath()
        firstLastPath.moveTo(4, 0)
        firstLastPath.lineTo(8, 4)
        firstLastPath.lineTo(0, 4)
        firstLastPath.closeSubpath()
        firstLastPath.moveTo(0, 6)
        firstLastPath.lineTo(8, 6)
        firstLastPath.lineTo(4, 10)
        firstLastPath.closeSubpath()
        firstLastPath.translate(-firstLastPath.boundingRect().center())
        valueList.append(firstLastPath)

        chordPath = QtGui.QPainterPath()
        chordPath.moveTo(4, 0)
        chordPath.lineTo(4, 8)
        chordPath.addEllipse(0, 4, 4, 2)
        chordPath.addEllipse(0, 7, 4, 2)
        chordPath.translate(-chordPath.boundingRect().center())
        valueList.append(chordPath)
        valueList.append(u'?')

        ArpSpinBox.__init__(self, step, valueList)


class AccentSpinBox(ArpSpinBox):
    valueListStr = _accents
    def __init__(self, step):
        ArpSpinBox.__init__(self, step, ['sil.', '/4', '/3', '/2', '*1', '*2', '*3', '*4'])
        self.setValue(4)


class TimingSpinBox(ArpSpinBox):
    valueListStr = _timings
    def __init__(self, step):
        ArpSpinBox.__init__(self, step, ['rnd', '-3', '-2', '-1', '+0', '+1', '+2', '+3'])
        self.setValue(4)


class LengthSpinBox(ArpSpinBox):
    valueListStr = _lengths
    def __init__(self, step):
        ArpSpinBox.__init__(self, step, ['leg.', '-3', '-2', '-1', '+0', '+1', '+2', '+3'])
        self.setValue(4)


class SpacerSpinBox(ArpSpinBox):
    def __init__(self, minWidth):
        ArpSpinBox.__init__(self, -1, [''])
        self.setMaximumWidth(minWidth)
        self.setStyleSheet('''
            ArpSpinBox {
                border: none;
                color: transparent;
                background: transparent;
            }
            ''')

    def resizeEvent(self, event):
        pass

    def paintEvent(self, event):
        pass


class SpinBoxProxy(QtWidgets.QGraphicsProxyWidget):
    def __init__(self, parent, widget):
        QtWidgets.QGraphicsProxyWidget.__init__(self, parent)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred))
        self.setWidget(widget)

    def _sizeHint(self, which, constraint):
        #a ugly and hackish way to avoid "focus shade" animated rect while changing values fast,
        #see the resizeEvent of the ArpSpinBox class
        if which == QtCore.Qt.MinimumSize:
            try:
                return self.minimumSizeHint
            except:
                self.minimumSizeHint = QtWidgets.QGraphicsProxyWidget.sizeHint(self, which, constraint)
                return self.minimumSizeHint
        if which == QtCore.Qt.PreferredSize:
            try:
                return self.preferredSizeHint
            except:
                self.preferredSizeHint = QtWidgets.QGraphicsProxyWidget.sizeHint(self, which, constraint)
                return self.preferredSizeHint
        return QtWidgets.QGraphicsProxyWidget.sizeHint(self, which, constraint)


class StepLineItem(QtWidgets.QGraphicsProxyWidget):
    def __init__(self, parent, id):
        QtWidgets.QGraphicsProxyWidget.__init__(self, parent)
        self.lineWidget = QtWidgets.QWidget()
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Expanding))
        if id % 4:
            dot = 1
            margin = 'margin-top: 16px; margin-bottom: 16px;'
        else:
            dot = 2
            margin = ''
        self.lineWidget.setStyleSheet('''
            QWidget {{
                margin-left: .5px;
                border-left: {dot}px dotted rgba(30, 50, 40);
                background: transparent;
                {margin}
            }}
            '''.format(dot=dot, margin=margin))
        self.setWidget(self.lineWidget)
        self.setFlags(self.flags() ^ self.ItemIsFocusable)

    def sizeHint(self, which, constraint):
        if which == QtCore.Qt.MinimumSize:
            return QtCore.QSizeF(5, 60)
        return QtCore.QSizeF(200, 200)


class LabelItem(QtWidgets.QGraphicsProxyWidget):
    def __init__(self, parent, text):
        QtWidgets.QGraphicsProxyWidget.__init__(self, parent)
        self.label = QtWidgets.QLabel(text)
        font = self.font()
        font.setPointSize(font.pointSize() - 1)
        self.label.setFont(font)
        self.label.setStyleSheet('background: transparent;')
        self.setWidget(self.label)

    def setFont(self, font):
        self.label.setFont(font)


class GlideBtn(GraphicsButton):
    valueChanged = QtCore.pyqtSignal(int)
    def __init__(self, id):
        GraphicsButton.__init__(self)
        self.id = id
        self.setMaximumWidth(30)
        self.setCheckable(True)
        self.toggled.connect(lambda state: self.valueChanged.emit(int(state)))

    def paintEvent(self, event):
        QtWidgets.QPushButton.paintEvent(self, event)
        qp = QtWidgets.QStylePainter(self)
        qp.setRenderHints(qp.Antialiasing)
        qp.translate(.5, .5)
        path = QtGui.QPainterPath()
        path.cubicTo(0, 8, 8, 0, 8, 10)
        path.cubicTo(8, 2, 0, 8, 0, 0)
#        path.arcTo(0, -3.5, 9, 7, 180, 90)
#        path.arcTo(1, 3.5, 7, 9, 90, -90)
#        path.arcTo(-1, 4.5, 9, 7, 0, 90)
#        path.arcTo(0, -4.5, 7, 9, 270, -90)
#        qp.drawRect(self.rect().adjusted(0, 0, -2, -2))
        path.translate(-path.boundingRect().center())
        qp.translate(self.rect().center())
        qp.drawPath(path)


class ArpStepWidget(QtWidgets.QGraphicsWidget):
    pen = basePen = defaultPen = QtGui.QColor(10, 30, 20)
    activePen = QtGui.QColor(QtCore.Qt.red)
    silentPen = QtGui.QColor(QtCore.Qt.gray)
    bgdNormal = QtGui.QColor(30, 50, 40, 220)
    bgdSilent = QtGui.QColor(30, 50, 40, 80)
    backgroundBrushes = {False: bgdSilent, True: bgdNormal}

    accentChanged = QtCore.pyqtSignal(int, int)
    lengthChanged = QtCore.pyqtSignal(int, int)
    timingChanged = QtCore.pyqtSignal(int, int)
    changed = QtCore.pyqtSignal(int, int, bool, int, int, int)

    def __init__(self, parent, step, prevSibling=None):
        QtWidgets.QGraphicsWidget.__init__(self, parent)
        self.setAcceptHoverEvents(True)
        self.step = step
        self.geometryChanged.connect(self.updateRect)
        if prevSibling:
            self.prevSibling = prevSibling
            prevSibling.setNextSibling(self)
            self.siblings = [prevSibling]
#            self.timingChanged.connect(lambda timing: prevSibling.computeStep() if not prevSibling.length else None)
        else:
            self.prevSibling = None
            self.siblings = []
        self.nextSibling = None
        self.twin = None
        self.originX = self.bottom = self.hUnit = self.vUnit = self.upperMaxY = self.lowerMinY = 0
        self.stepType = 0
        self.accent = self.timing = self.length = 4
        self.glide = False
        self.stepRect = QtCore.QRectF()
        self.stepShape = QtGui.QPainterPath()
        self.setZValue(100)
        if step < 0:
            self.deltaRef = -1
        elif step > 15:
            self.deltaRef = 2
        else:
            self.deltaRef = 0
            self.setFlags(self.flags() | self.ItemIsSelectable | self.ItemIsFocusable)
#        self.accentChanged.connect(lambda *args: self.changed.emit(self.step, self.stepType, self.glide, self.accent, self.timing, self.length))
#        self.timingChanged.connect(lambda *args: self.changed.emit(self.step, self.stepType, self.glide, self.accent, self.timing, self.length))
#        self.lengthChanged.connect(lambda *args: self.changed.emit(self.step, self.stepType, self.glide, self.accent, self.timing, self.length))

    def values(self):
        return self.stepType, self.glide, self.accent, self.timing, self.length

    def setStepType(self, stepType):
        self.stepType = stepType
        self.changed.emit(self.step, self.stepType, self.glide, self.accent, self.timing, self.length)

    def setGlide(self, glide):
        self.glide = glide
        self.changed.emit(self.step, self.stepType, self.glide, self.accent, self.timing, self.length)

    def setAccent(self, accent, emit=True):
        if accent == self.accent:
            return
        self.accent = accent
        self.basePen = self.defaultPen if accent else self.silentPen
        self.computeStep()
        if emit:
            self.accentChanged.emit(self.step, accent)

    def setTiming(self, timing, emit=True):
        if timing == self.timing:
            return
        self.timing = timing
        self.computeStep()
        if self.prevSibling and not self.prevSibling.length:
            self.prevSibling.computeStep()
        if emit:
            self.timingChanged.emit(self.step, timing)

    def setLength(self, length, emit=True):
        if length == self.length:
            return
        self.length = length
        self.computeStep()
        if emit:
            self.lengthChanged.emit(self.step, length)

    def setNextSibling(self, sibling):
        self.nextSibling = sibling
        self.siblings.append(sibling)

    def connectTo(self, twin):
        twin.twin = self
        twin.accentChanged.connect(lambda step, accent: self.setAccent(accent))
        twin.timingChanged.connect(lambda step, timing: self.setTiming(timing))
        twin.lengthChanged.connect(lambda step, length: self.setLength(length))

    @property
    def referenceItem(self):
        try:
            return self._referenceItem
        except:
            if self.step < 0:
                self._referenceItem = self.parentItem().layout().itemAt(1, 1)
            elif self.step >= 16:
                self._referenceItem = self.parentItem().layout().itemAt(1, 15)
            else:
                self._referenceItem = self.parentItem().layout().itemAt(1, self.step + 1)
            return self._referenceItem

    def boundingRect(self):
        try:
            return self._boundingRect
        except:
            return QtCore.QRectF()

    def shape(self):
        return self.stepShape

    def updateRect(self):
        #TODO: maybe we can do this in the main ArpeggiatorWidget to avoid repeated computations?
        self.prepareGeometryChange()
        self.blockSignals(True)
        self._boundingRect = QtCore.QRectF(QtCore.QPointF(0, 0), self.referenceItem.geometry().size())
        self.hUnit = self._boundingRect.width() / 7.
        self.vUnit = self._boundingRect.height() / 10.
        self.upperMaxY = self.vUnit * 4
        self.lowerMinY = self.vUnit * 5
        self.bottom = self._boundingRect.bottom() - self.vUnit
        increase = self.hUnit * 3
        self.originX = -increase
        self._boundingRect.setLeft(self._boundingRect.left() - increase)
        self._boundingRect.setRight(self._boundingRect.right() + increase)
        self.setPos(self.referenceItem.pos().x() + 7 * self.hUnit * self.deltaRef + self.deltaRef, self.referenceItem.pos().y())
        self.blockSignals(False)
        self.computeStep()

    def computeStep(self):
        bottom = self.bottom - self.accent * self.vUnit
        top = bottom - self.vUnit
        top = min(self.upperMaxY, top)
        bottom = max(self.lowerMinY, bottom) - top
        if self.timing:
            left = self.originX + (self.timing - 1) * self.hUnit
        else:
            left = 0
        if self.length:
            right = self.length * self.hUnit
        elif self.nextSibling:
#            nextTiming = self.nextSibling.timing
#            if not nextTiming:
#                nextTiming = 4
#            right = self.referenceItem.geometry().right() - self.nextSibling.originX + nextTiming * self.hUnit
#            timing = self.timing if self.timing else 4
#            nextTiming = self.nextSibling.timing if self.nextSibling.timing else 4
            right = self.mapFromItem(self.nextSibling, self.nextSibling.stepRect.topLeft()).x() - left
#            right -= left
        else:
            right = 10 * self.hUnit
        self.stepRect = QtCore.QRectF(left, top, right, bottom)
        self.stepShape = QtGui.QPainterPath()
        self.stepShape.addRect(self.stepRect.adjusted(-1, -1, 3, 3))
        self.update()

    def setDragAction(self, pos):
        x = pos.x()
        y = pos.y()
        hRatio = self.hUnit * .5 if self.length <= 4 else self.hUnit * 2
        if self.accent == 4:
            vRatio = self.vUnit * .25
            if x < self.stepRect.left() + hRatio:
                cursor = LeftCursor
            elif x > self.stepRect.right() - hRatio:
                cursor = RightCursor
            elif y < self.stepRect.top() + vRatio:
                cursor = UpCursor
            elif y > self.stepRect.bottom() - vRatio:
                cursor = DownCursor
            else:
                cursor = MoveCursor
        else:
            vRatio = self.vUnit * .5
            if y < self.stepRect.top() + vRatio:
                cursor = UpCursor
            elif y > self.stepRect.bottom() - vRatio:
                cursor = DownCursor
            elif x < self.stepRect.left() + hRatio:
                cursor = LeftCursor
            elif x > self.stepRect.right() - hRatio:
                cursor = RightCursor
            else:
                cursor = MoveCursor
#        print(event.pos() in self.stepRect, event.pos(), self.stepRect)
        self.setCursor(CursorList[cursor])
        self.dragAction = cursor

    def hoverEnterEvent(self, event):
        for sibling in self.siblings:
            sibling.setZValue(99)
        self.setZValue(100)
        self.setDragAction(event.pos())
        self.pen = self.activePen
        self.update()

    def hoverMoveEvent(self, event):
        self.setDragAction(event.pos())

    def hoverLeaveEvent(self, event):
        self.pen = self.basePen
        self.update()

    def mousePressEvent(self, event):
        self.dragDelta = event.pos().x() if self.dragAction == MoveCursor else 0

    def mouseMoveEvent(self, event):
        if event.buttons() == QtCore.Qt.LeftButton:
            x = event.pos().x()
            y = event.pos().y()
            if self.dragAction == LeftCursor or self.dragAction == MoveCursor:
                x -= self.dragDelta
                if x < self.stepRect.left():
                    delta = -1
                elif x > self.stepRect.left() + self.hUnit:
                    delta = 1
                else:
                    delta = 0
                self.setTiming(max(1, min(7, self.timing + delta)))
            elif self.dragAction == RightCursor:
                if x > self.stepRect.right():
                    delta = 1
                elif x < self.stepRect.right() - self.hUnit:
                    delta = -1
                else:
                    delta = 0
                self.setLength(max(1, min(7, self.length + delta)))
            if self.dragAction in (UpCursor, DownCursor, MoveCursor):
                accent = 7
                vPos = self.vUnit * 2
                while y > vPos and accent >= 1:
                    vPos += self.vUnit
                    accent -= 1
#                print(event.pos(), vPos, accent)
                self.setAccent(max(0, min(7, accent)))

    def paint(self, qp, option, widget):
#        qp.drawRect(self.boundingRect())
        qp.save()
        #is this translation really necessary???
        qp.translate(1.5, 1.5)
        qp.setPen(self.activePen if self.isSelected() else self.pen)
        qp.setBrush(self.backgroundBrushes[bool(self.accent)])
        qp.drawRect(self.stepRect)
        qp.restore()


class ArpeggiatorWidget(QtWidgets.QGraphicsWidget):
    def __init__(self, main):
        QtWidgets.QGraphicsWidget.__init__(self)
        layout = QtWidgets.QGraphicsGridLayout()
        layout.setContentsMargins(2, 0, 2, 0)
        layout.setSpacing(2)
        self.setLayout(layout)

        layout.addItem(LabelItem(self, 'Step'), 2, 0, QtCore.Qt.AlignCenter)
        layout.addItem(LabelItem(self, 'Glide'), 3, 0, QtCore.Qt.AlignCenter)
        layout.addItem(LabelItem(self, 'Accent'), 4, 0, QtCore.Qt.AlignCenter)
        layout.addItem(LabelItem(self, 'Timing'), 5, 0, QtCore.Qt.AlignCenter)
        layout.addItem(LabelItem(self, 'Length'), 6, 0, QtCore.Qt.AlignCenter)

        arpStepWidget = ArpStepWidget(self, -1, None)
        arpStepWidget.setAcceptHoverEvents(False)
        arpStepWidget.pen = arpStepWidget.silentPen
        silentBrush = arpStepWidget.backgroundBrushes[False]
        arpStepWidget.backgroundBrushes = {False: silentBrush, True: silentBrush}
        self.geometryChanged.connect(arpStepWidget.updateRect)
        firstStepWidget = arpStepWidget
        self.stepWidgets = []
        self.controlWidgets = []
        for step in range(16):
            layoutStep = step + 1
            stepIdItem = LabelItem(self, str(layoutStep))
            layout.addItem(stepIdItem, 0, layoutStep)
            layout.addItem(StepLineItem(self, step), 1, layoutStep)
#            print(stepIdItem.x())
            font = self.font()
            font.setPointSize(font.pointSize() - 1)
            if not step % 4:
                font.setBold(True)
                stepIdItem.setFont(font)

            arpStepWidget = ArpStepWidget(self, step, arpStepWidget)
            arpStepWidget.accentChanged.connect(main.accentChanged)
            arpStepWidget.timingChanged.connect(main.timingChanged)
            arpStepWidget.lengthChanged.connect(main.lengthChanged)
            self.stepWidgets.append(arpStepWidget)
            self.geometryChanged.connect(arpStepWidget.updateRect)
#            arpStepWidget.setParentItem

            stepSpin = StepSpinBox(step)
            stepSpin.valueChanged.connect(arpStepWidget.setStepType)
            stepSpin.valueChanged.connect(lambda stepType, step=step: main.stepChanged.emit(step, stepType))
            stepSpinItem = SpinBoxProxy(self, stepSpin)
            layout.addItem(stepSpinItem, 2, layoutStep, QtCore.Qt.AlignCenter)
            glideSpinItem = QtWidgets.QGraphicsProxyWidget(self)
            glideBtn = GlideBtn(step)
            glideBtn.setValue = glideBtn.setChecked
            glideBtn.toggled.connect(arpStepWidget.setGlide)
            glideBtn.toggled.connect(lambda glide, step=step: main.glideChanged.emit(step, glide))
            glideSpinItem.setWidget(glideBtn)
            layout.addItem(glideSpinItem, 3, layoutStep, QtCore.Qt.AlignCenter)

            accentSpin = AccentSpinBox(step)
            arpStepWidget.accentChanged.connect(lambda step, accent, spin=accentSpin: spin.setValue(accent))
            accentSpin.valueChanged.connect(lambda accent, widget=arpStepWidget: widget.setAccent(accent))
            layout.addItem(SpinBoxProxy(self, accentSpin), 4, layoutStep, QtCore.Qt.AlignCenter)

            timingSpin = TimingSpinBox(step)
            arpStepWidget.timingChanged.connect(lambda step, timing, spin=timingSpin: spin.setValue(timing))
            timingSpin.valueChanged.connect(lambda timing, widget=arpStepWidget: widget.setTiming(timing))
            layout.addItem(SpinBoxProxy(self, timingSpin), 5, layoutStep, QtCore.Qt.AlignCenter)

            lengthSpin = LengthSpinBox(step)
            arpStepWidget.lengthChanged.connect(lambda step, length, spin=lengthSpin: spin.setValue(length))
            lengthSpin.valueChanged.connect(lambda length, widget=arpStepWidget: widget.setLength(length))
            layout.addItem(SpinBoxProxy(self, lengthSpin), 6, layoutStep, QtCore.Qt.AlignCenter)

            self.controlWidgets.append((
                stepSpin, glideBtn, accentSpin, timingSpin, lengthSpin))

        lastStepLine = StepLineItem(self, 16)
        lastStepLine.setOpacity(.5)
        layout.addItem(lastStepLine, 1, 17)

        lastStepWidget = ArpStepWidget(self, 16, arpStepWidget)
        lastStepWidget.setZValue(-1)
        lastStepWidget.setAcceptHoverEvents(False)
        lastStepWidget.pen = lastStepWidget.silentPen
        silentBrush = lastStepWidget.backgroundBrushes[False]
        lastStepWidget.backgroundBrushes = {False: silentBrush, True: silentBrush}
        self.geometryChanged.connect(lastStepWidget.updateRect)

        firstStepWidget.connectTo(self.stepWidgets[-1])
        lastStepWidget.connectTo(self.stepWidgets[0])

        spacer = SpinBoxProxy(self, SpacerSpinBox(5))
        layout.addItem(spacer, 2, layoutStep + 1)

#    def setAccent(self, step, accent):
#        print(args)

class GraphicsMsgBox(QtWidgets.QGraphicsWidget):
    backgroundBrush = QtGui.QColor(30, 50, 40, 96)
    foregroundBrush = QtGui.QColor(230, 250, 240, 240)
    connected = False
    accepted = QtCore.pyqtSignal()
    rejected = QtCore.pyqtSignal()

    def __init__(self, *args, **kwargs):
        QtWidgets.QGraphicsWidget.__init__(self, *args, **kwargs)
        self.setFlags(self.flags() | self.ItemIsFocusable)
        self.setAcceptHoverEvents(True)
        self.dialog = QtCore.QRectF()
        self.okBtn = QtCore.QRectF()
        self.cancelBtn = QtCore.QRectF()
        self.okBtnHover = self.cancelBtnHover = False
        self.execLock = Lock()
        self.accepted.connect(self.execLock.release)
        self.rejected.connect(self.execLock.release)
        self.shadow = QtWidgets.QGraphicsDropShadowEffect()
        self.shadow.setBlurRadius(4)
        self.shadow.setOffset(3, 3)
        self.shadow.setColor(QtGui.QColor(100, 100, 100, 150))
        self.setGraphicsEffect(self.shadow)

    def hoverMoveEvent(self, event):
        if event.pos() in self.okBtn:
            self.okBtnHover = True
            self.cancelBtnHover = False
        elif event.pos() in self.cancelBtn:
            self.okBtnHover = False
            self.cancelBtnHover = True
        else:
            self.okBtnHover = False
            self.cancelBtnHover = False
        self.update()

    def setBoundingRect(self, *args):
        view = self.scene().views()[0]
        self._boundingRect = view.mapToScene(view.viewport().geometry()).boundingRect().adjusted(-.5, -.5, -1, -1)
        self._shape = QtGui.QPainterPath()
        self._shape.addRect(self._boundingRect)
        if not self.connected:
            self.setFocus()
            self.connected = True
            self.execLock.acquire()
            self.scene().sceneRectChanged.connect(self.setBoundingRect)
        center = self._boundingRect.center()
        self.dialog.setRect(center.x() - 80, center.y() - 40, 160, 80)
        self.okBtn.setRect(center.x() - 60, center.y() + 10, 40, 20)
        self.cancelBtn.setRect(center.x() + 10, center.y() + 10, 60, 20)

    def boundingRect(self):
        try:
            return self._boundingRect
        except:
            return QtCore.QRectF()

    def shape(self):
        return self._shape

    def paint(self, qp, option, widget):
        qp.save()
#        qp.translate(self._boundingRect.center())
        pen = qp.pen()
        brush = qp.brush()
        qp.setBrush(self.backgroundBrush)
        qp.drawRect(self._boundingRect.adjusted(-10, -10, 10, 10))
        qp.setBrush(self.foregroundBrush)
#        winRect = QtCore.QRectF(-80, -40, 160, 80)
        qp.drawRect(self.dialog)
        qp.drawText(self.dialog.adjusted(0, 0, 0, -self.dialog.height() / 2), QtCore.Qt.AlignCenter, 'Reset all steps?')
        if self.okBtnHover:
            qp.setPen(QtGui.QColor(QtCore.Qt.black))
            qp.setBrush(QtGui.QColor(QtCore.Qt.white))
        qp.drawRect(self.okBtn)
        qp.setPen(pen)
        qp.setBrush(brush)
        if self.cancelBtnHover:
            qp.setPen(QtGui.QColor(QtCore.Qt.black))
            qp.setBrush(QtGui.QColor(QtCore.Qt.white))
        qp.drawRect(self.cancelBtn)
        qp.setPen(pen)
        qp.drawText(self.okBtn, QtCore.Qt.AlignCenter, 'Ok')
        qp.drawText(self.cancelBtn, QtCore.Qt.AlignCenter, 'Cancel')
        qp.restore()

    def mousePressEvent(self, event):
        if event.pos() in self.okBtn:
            self.status = True
            self.accepted.emit()
        elif event.pos() in self.cancelBtn or event.pos() not in self.dialog:
            self.status = False
            self.rejected.emit()

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self.status = False
            self.rejected.emit()

    def exec_(self):
        while True:
            if self.execLock.acquire(False):
                break
            QtWidgets.QApplication.processEvents()
        return self.status


class ArpScene(QtWidgets.QGraphicsScene):
    #TODO: subscribe parameters!!!
    stepChanged = QtCore.pyqtSignal(int, int)
    glideChanged = QtCore.pyqtSignal(int, bool)
    accentChanged = QtCore.pyqtSignal(int, int)
    lengthChanged = QtCore.pyqtSignal(int, int)
    timingChanged = QtCore.pyqtSignal(int, int)

    def __init__(self):
        QtWidgets.QGraphicsScene.__init__(self)
        self.arpeggiatorWidget = ArpeggiatorWidget(self)
        self.stepWidgets = self.arpeggiatorWidget.stepWidgets
        for step in range(16):
#            item = self.stepWidgets[step]
#            item.accentChanged.connect(lambda step, accent: self.checkSelectionChange(step, ACCENT, accent))
#            item.lengthChanged.connect(lambda step, accent: self.checkSelectionChange(step, LENGTH, accent))
#            item.timingChanged.connect(lambda step, accent: self.checkSelectionChange(step, TIMING, accent))
            stepSpin, glideBtn, accentSpin, timingSpin, lengthSpin = self.arpeggiatorWidget.controlWidgets[step]
            stepSpin.valueChanged.connect(lambda v, step=step: self.checkSelectionChange(step, STEP, v))
            glideBtn.toggled.connect(lambda v, step=step: self.checkSelectionChange(step, GLIDE, v))
            accentSpin.valueChanged.connect(lambda v, step=step: self.checkSelectionChange(step, ACCENT, v))
            timingSpin.valueChanged.connect(lambda v, step=step: self.checkSelectionChange(step, TIMING, v))
            lengthSpin.valueChanged.connect(lambda v, step=step: self.checkSelectionChange(step, LENGTH, v))
        self.addItem(self.arpeggiatorWidget)
        self.shadow = QtWidgets.QGraphicsDropShadowEffect()
        self.shadow.setBlurRadius(4)
        self.shadow.setOffset(1, 1)
        self.shadow.setColor(QtGui.QColor(100, 100, 100, 150))
        self.arpeggiatorWidget.setGraphicsEffect(self.shadow)
        self.stepRect = QtCore.QRectF(0, 0, 1, 1)

        self.closeBtn = CloseBtn()
        self.closeBtn.setToolTip('Close pattern editor')
        self.closeBtnProxy = QtWidgets.QGraphicsProxyWidget()
        self.closeBtnProxy.setWidget(self.closeBtn)
        self.addItem(self.closeBtnProxy)

    def resizeSceneItems(self, rect):
        self.arpeggiatorWidget.setGeometry(rect)
        self.stepRect.setBottomRight(
            QtCore.QPointF(
                self.arpeggiatorWidget.geometry().right(), 
                self.arpeggiatorWidget.layout().itemAt(1, 1).geometry().bottom()))
        self.closeBtnProxy.setPos(self.stepRect.right() - self.closeBtnProxy.geometry().width(), 0)

    def setSteps(self, stepType):
        for item in self.selectedItems():
            self.arpeggiatorWidget.controlWidgets[item.step][0].setValue(stepType)

    def setGlides(self, glide):
        for item in self.selectedItems():
            self.arpeggiatorWidget.controlWidgets[item.step][1].setChecked(glide)

    def setAccents(self, accent):
        for item in self.selectedItems():
            item.setAccent(accent)

    def setTimings(self, timing):
        for item in self.selectedItems():
            item.setTiming(timing)

    def setLengths(self, length):
        for item in self.selectedItems():
            item.setLength(length)

    def copyStepItem(self, stepItem):
        values = stepItem.values()
        for item in self.selectedItems():
            if item == stepItem:
                continue
            item.blockSignals(True)
            for widget, value in zip(self.arpeggiatorWidget.controlWidgets[item.step], values):
                widget.setValue(value)
            item.blockSignals(False)

    def resetAllRequest(self):
        msg = GraphicsMsgBox()
        self.addItem(msg)
        msg.setBoundingRect()
        self.arpeggiatorWidget.geometryChanged.connect(msg.setBoundingRect)
        res = msg.exec_()
        self.removeItem(msg)
        if not res:
            return
        values = 0, False, 4, 4, 4
        for item in self.stepWidgets:
            item.blockSignals(True)
            for widget, value in zip(self.arpeggiatorWidget.controlWidgets[item.step], values):
                widget.setValue(value)
            item.blockSignals(False)
        self.clearSelection()

    def checkSelectionChange(self, step, valueType, value):
        selectedItems = self.selectedItems()
        if not selectedItems or len(selectedItems) == 1 or self.stepWidgets[step] not in selectedItems:
            self.clearSelection()
            return
        for item in selectedItems:
            if item.step == step:
                continue
            item.blockSignals(True)
            self.arpeggiatorWidget.controlWidgets[item.step][valueType].setValue(value)
            item.blockSignals(False)
        if valueType in (TIMING, LENGTH):
            for item in reversed(self.stepWidgets):
                item.computeStep()

    def mousePressEvent(self, event):
        pos = event.scenePos()
        item = self.itemAt(event.scenePos(), QtGui.QTransform())
        if event.buttons() & QtCore.Qt.LeftButton:
            if not pos in self.stepRect:
                pass
#                if not isinstance(item, QtWidgets.QGraphicsProxyWidget):
#                    self.clearSelection()
            else:
                modifiers = event.modifiers()
                focusItem = self.focusItem()
                if modifiers == QtCore.Qt.ShiftModifier:
                    if focusItem and isinstance(focusItem, ArpStepWidget):
                        first = min(focusItem.step, item.step)
                        last = max(focusItem.step, item.step)
                        for i in self.stepWidgets:
                            if first <= i.step <= last:
                                i.setSelected(True)
                            else:
                                i.setSelected(False)
                    event.accept()
                    return
                elif modifiers == QtCore.Qt.ControlModifier:
                    QtWidgets.QGraphicsScene.mousePressEvent(self, event)
                    if not self.selectedItems() and isinstance(item, ArpStepWidget):
                        self.setFocusItem(item)
                        return
                    elif focusItem and isinstance(focusItem, ArpStepWidget):
                        self.setFocusItem(focusItem)
                    return
                else:
                    if isinstance(item, ArpStepWidget):
                        QtWidgets.QGraphicsScene.mousePressEvent(self, event)
                        if item not in self.selectedItems():
                            self.clearSelection()
                        self.setFocusItem(item)
                        return
        elif event.button() == QtCore.Qt.RightButton:
            if isinstance(item, ArpStepWidget):
                item.setSelected(True)
            event.accept()
            return
        QtWidgets.QGraphicsScene.mousePressEvent(self, event)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_A and event.modifiers() == QtCore.Qt.ControlModifier:
            for item in self.stepWidgets:
                item.setSelected(True)
        elif event.key() == QtCore.Qt.Key_Escape:
            for item in self.stepWidgets:
                item.setSelected(False)
        QtWidgets.QGraphicsScene.keyPressEvent(self, event)

    def contextMenuEvent(self, event):
        item = self.itemAt(event.scenePos(), QtGui.QTransform())
        if isinstance(item, ArpStepWidget):
            selection = self.selectedItems()
        else:
            item = None
        menu = QtWidgets.QMenu()
        if item:
            createSel = selection and len(selection) > 1

            setStepsMenu = menu.addMenu('Set step type{}'.format(' for selection' if createSel else ''))
            for step, txt in reversed(list(enumerate(_steps))):
                action = setStepsMenu.addAction(txt)
                action.triggered.connect(lambda _, s=step: self.setSteps(s))
                if step == item.stepType:
                    setBold(action)

            setGlideMenu = menu.addMenu('Set glide{}'.format(' for selection' if createSel else ''))
            for glide, txt in reversed(list(enumerate(_glide))):
                action = setGlideMenu.addAction(txt)
                action.triggered.connect(lambda _, g=glide: self.setGlides(g))
                if glide == item.glide:
                    setBold(action)

            setAccentMenu = menu.addMenu('Set accent{}'.format(' for selection' if createSel else ''))
            for accent, txt in reversed(list(enumerate(_accents))):
                action = setAccentMenu.addAction(txt)
                action.triggered.connect(lambda _, a=accent: self.setAccents(a))
                if accent == item.accent:
                    setBold(action)

            setTimingMenu = menu.addMenu('Set timing{}'.format(' for selection' if createSel else ''))
            for timing, txt in reversed(list(enumerate(_timings))):
                action = setTimingMenu.addAction(txt)
                action.triggered.connect(lambda _, t=timing: self.setTimings(t))
                if timing == item.timing:
                    setBold(action)

            setLengthMenu = menu.addMenu('Set length{}'.format(' for selection' if createSel else ''))
            for length, txt in reversed(list(enumerate(_lengths))):
                action = setLengthMenu.addAction(txt)
                action.triggered.connect(lambda _, l=length: self.setLengths(l))
                if length == item.length:
                    setBold(action)

            if createSel:
                menu.addSeparator()
                copyAction = menu.addAction('Copy step {} to selection'.format(item.step + 1))
                copyAction.triggered.connect(lambda: self.copyStepItem(item))
            menu.addSeparator()

        resetAction = menu.addAction('Reset all')
        resetAction.triggered.connect(self.resetAllRequest)
        menu.exec_(event.screenPos())


class ArpeggiatorDisplay(QtWidgets.QGraphicsView):
    closeRequest = QtCore.pyqtSignal()

    def __init__(self, *args, **kwargs):
        QtWidgets.QGraphicsView.__init__(self, *args, **kwargs)
        CursorList.extend((QtCore.Qt.SizeAllCursor, UpCursorClass(), DownCursorClass(), LeftCursorClass(), RightCursorClass()))

        self.setRenderHints(QtGui.QPainter.Antialiasing)
        self.setDragMode(self.RubberBandDrag)
        self.arpScene = ArpScene()
        self.controlWidgets = self.arpScene.arpeggiatorWidget.controlWidgets
        self.stepWidgets = self.arpScene.stepWidgets
        #this is for debug only
        try:
            self.main = self.window().main
        except:
            pass
        self.setScene(self.arpScene)

        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
#        self.horizontalScrollBar().setVisible(False)
#        self.verticalScrollBar().setVisible(False)

        self.arpScene.closeBtn.clicked.connect(self.closeRequest)

        self.setPalette(self.palette())
        self.shown = False

    def _showEvent(self, event):
        if not self.shown:
            self.shown = True
            size = self.arpScene.arpeggiatorWidget.minimumSize().toSize()
            self.setMinimumSize(size.width() + 1, size.height() + 1)

    def setPalette(self, palette):
        self.setStyleSheet('''
            ArpeggiatorDisplay {{
                border-top: 1px solid {dark};
                border-right: 1px solid {light};
                border-bottom: 1px solid {light};
                border-left: 1px solid {dark};
                border-radius: 2px;
                background: rgb(230, 240, 230);
            }}
            '''.format(
                dark=_getCssQColorStr(palette.color(palette.Dark)), 
                light=_getCssQColorStr(palette.color(palette.Midlight)), 
                ))

    def resizeEvent(self, event):
        rect = QtCore.QRectF(self.viewport().rect())
        self.setSceneRect(rect)
        self.arpScene.resizeSceneItems(rect.adjusted(0, 0, -2, -2))

    def minimumSizeHint(self):
#        return self.arpScene.arpeggiatorWidget.minimumSize().toSize()
        try:
            return self._minimumSizeHint
        except:
            size = self.arpScene.arpeggiatorWidget.minimumSize().toSize()
            size.setWidth(size.width() + 2)
            size.setHeight(size.height() + 4)
            self._minimumSizeHint = size
            return self._minimumSizeHint

    def sizeHint(self):
        return self.minimumSizeHint()

    def _paintEvent(self, event):
        QtWidgets.QGraphicsView.paintEvent(self, event)
        qp = QtGui.QPainter(self.viewport())
        qp.drawRect(QtCore.QRectF(QtCore.QPointF(0, 0), self.arpScene.arpeggiatorWidget.minimumSize()).adjusted(0, 0, 1, 1))
        qp.drawRect(self.arpScene.arpeggiatorWidget.boundingRect().adjusted(0, 0, -1, -1))


if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)
    w = ArpeggiatorDisplay()
    w.show()
    sys.exit(app.exec_())
