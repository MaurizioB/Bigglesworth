# *-* encoding: utf-8 *-*

import sys
from copy import deepcopy
import numpy as np
from Qt import QtCore, QtGui, QtWidgets

from bigglesworth.utils import loadUi, getCardinal, sanitize
from bigglesworth.wavetables.widgets import HarmonicsSlider, CurveIcon, EnvelopeHarmonicsSlider, AddSliderButton
from bigglesworth.wavetables.utils import curves, waveFunction, cubicTranslation, getCurveFunc, Envelope, waveColors, WaveLabelsExt
from bigglesworth.help import HelpDialog

FractRole = QtCore.Qt.UserRole + 1


class StatusBar(QtWidgets.QLabel):
    shown = False

    def __init__(self, *args, **kwargs):
        QtWidgets.QLabel.__init__(self, *args, **kwargs)
        self.timer = QtCore.QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.clear)

    def showEvent(self, event):
        if not self.shown:
            self.shown = True
            if sys.platform == 'darwin':
                self.setMinimumHeight(self.fontMetrics().height() * 2)

    def showMessage(self, message, timeout=0):
        if message == self.text():
            return
        self.setText(message)
        self.timer.stop()
        if timeout:
            self.timer.setInterval(timeout)
            self.timer.start()


class RangeLabel(QtWidgets.QLabel):
    clicked = QtCore.pyqtSignal()
    pen = QtGui.QPen(QtGui.QColor(64, 64, 64), 1.5)

    def mousePressEvent(self, event):
        self.clicked.emit()

    def resizeEvent(self, event):
        vMargin = self.frameWidth()
        margin = vMargin / 2
        rect = self.rect().adjusted(margin, vMargin, - margin, -self.height() / 2 - margin)
        self.rectSize = min(rect.height(), rect.width())
        self.rectCenter = rect.center()

    def paintEvent(self, event):
        QtWidgets.QLabel.paintEvent(self, event)
        qp = QtGui.QPainter(self)
        qp.setRenderHints(qp.Antialiasing)
        qp.setPen(self.pen)
        qp.translate(self.rectCenter + QtCore.QPoint(.5, .5))
        qp.drawPath(self.path)


class StartRangeLabel(RangeLabel):
    def resizeEvent(self, event):
        RangeLabel.resizeEvent(self, event)
        self.path = QtGui.QPainterPath()
        half = self.rectSize * .5
        self.path.moveTo(-half, -half)
        self.path.lineTo(half, 0)
        self.path.lineTo(-half, half)
        self.path.closeSubpath()


class EndRangeLabel(RangeLabel):
    def setNum(self, num):
        if num <= 64:
            self.resizeEvent = self.resizeEventNormal
        else:
            self.setToolTip('This morph ends at the beginning of the wavetable')
            num = 1
            self.resizeEvent = self.resizeEventFinal
        RangeLabel.setNum(self, num)

    def resizeEventFinal(self, event):
        RangeLabel.resizeEvent(self, event)
        half = self.rectSize * .5
        rect = QtCore.QRectF(-half, -half, self.rectSize, self.rectSize)
        self.path = QtGui.QPainterPath()
        self.path.arcMoveTo(rect, 210)
        self.path.arcTo(rect, 210, 300)

    def resizeEventNormal(self, event):
        RangeLabel.resizeEvent(self, event)
        half = self.rectSize * .5
        self.path = QtGui.QPainterPath()
        self.path.moveTo(-half, -half)
        self.path.lineTo(half, -half)
        self.path.lineTo(half, half)
        self.path.lineTo(-half, half)
        self.path.closeSubpath()


class ToolTipSlider(QtWidgets.QSlider):
    shown = False

    def __init__(self, *args, **kwargs):
        QtWidgets.QSlider.__init__(self, *args, **kwargs)
        self.label = QtWidgets.QLabel(self)
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.label.setFrameStyle(self.label.StyledPanel|self.label.Sunken)
        l, t, r, b = self.label.getContentsMargins()
        self.label.setMinimumWidth(self.fontMetrics().width('66') + self.label.frameWidth() * 2 + l + r)

    def setValue(self, value):
        QtWidgets.QSlider.setValue(self, value)
        if value <= 63:
            self.label.setNum(value + 1)
        else:
            self.label.setNum(1)
        option = QtWidgets.QStyleOptionSlider()
        self.initStyleOption(option)
        handleRect = self.style().subControlRect(QtWidgets.QStyle.CC_Slider, option, QtWidgets.QStyle.SC_SliderHandle, self).adjusted(0, 0, -1, -1)
        self.label.move(handleRect.topLeft())

    def showEvent(self, event):
        if not self.shown:
            self.shown = True
            self.setMaximumHeight(self.label.height())

    def resizeEvent(self, event):
        option = QtWidgets.QStyleOptionSlider()
        self.initStyleOption(option)
        self.grooveRect = self.style().subControlRect(QtWidgets.QStyle.CC_Slider, option, QtWidgets.QStyle.SC_SliderGroove, self).adjusted(0, 0, -1, 0)
        fullRange = (self.maximum() - self.minimum() + 1)
        ratio = float(self.grooveRect.width()) / fullRange
        self.points = []
        for p in range(fullRange):
            self.points.append(p * ratio)

    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        qp.setRenderHints(qp.Antialiasing)
        qp.translate(self.grooveRect.left() - .5, self.rect().bottom() - .5)
        for p in self.points:
            qp.drawEllipse(p, 0, 1, 1)
#        qp.translate(.5, .5)
#        qp.drawRect(grooveRect)

#class FakeCombo(QtWidgets.QComboBox):
#    def paintEvent(self, event):
#        pass
#
#class Selector(QtWidgets.QPushButton):
#
#    def __init__(self, main):
#        QtWidgets.QPushButton.__init__(self, QtGui.QIcon.fromTheme('document-edit'), '')
#        self.main = main
#        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum))
#        self.setMaximumHeight(16)
#        self.setCheckable(True)
#        self.setStyleSheet('''
#            Selector {
#                background: darkGray;
#                border: 1px solid palette(dark);
#                border-style: outset;
#                border-radius: 1px;
#            }
#            Selector:on {
#                background: rgb(50, 255, 50);
#                border-style: inset;
#            }
#        ''')
#
#        self.menu = QtWidgets.QMenu()
#        self.copyAction = self.menu.addAction(QtGui.QIcon.fromTheme('edit-copy'), 'Copy envelope')
#        self.pasteAction = self.menu.addAction(QtGui.QIcon.fromTheme('edit-paste'), 'Paste envelope')
#        self.menu.addSeparator()
#        self.removeAction = self.menu.addAction(QtGui.QIcon.fromTheme('edit-delete'), 'Remove')
#
#    def mousePressEvent(self, event):
#        self.click()
#
#    def contextMenuEvent(self, event):
#        self.click()
#        self.pasteAction.setEnabled(QtWidgets.QApplication.clipboard().mimeData().hasFormat('bigglesworth/EnvelopeData'))
#        if len(self.main.envelopes) == 1:
#            self.removeAction.setEnabled(False)
#        self.menu.exec_(QtGui.QCursor.pos())
#
#
#class SliderContainer(QtWidgets.QWidget):
#    triggered = QtCore.pyqtSignal()
#    fractChanged = QtCore.pyqtSignal(int)
#    polarityChanged = QtCore.pyqtSignal(int)
#    valueChanged = QtCore.pyqtSignal(float, float)
#    removeRequested = QtCore.pyqtSignal()
#    copyRequested = QtCore.pyqtSignal()
#    pasteRequested = QtCore.pyqtSignal()
#
#    def __init__(self, main, fract, model):
#        QtWidgets.QWidget.__init__(self)
#        self.main = main
#        layout = QtWidgets.QVBoxLayout()
#        self.setLayout(layout)
#        layout.setContentsMargins(1, 2, 1, 2)
#
#        self.selector = Selector(main)
#        layout.addWidget(self.selector)
#
#        self.slider = HarmonicsSlider(fract, True)
#        self.slider.valueChanged[float, float].connect(self.valueChanged)
#        self.slider.polarityChanged.connect(self.polarityChanged)
#        layout.addWidget(self.slider)
##        self.setValue = self.slider.setValue
#        self.setSliderEnabled = self.slider.setSliderEnabled
#
#        self.selector.setMaximumWidth(self.slider.sizeHint().width())
#        self.selector.copyAction.triggered.connect(self.copyRequested)
#        self.selector.pasteAction.triggered.connect(self.pasteRequested)
#        self.selector.removeAction.triggered.connect(self.removeRequested)
#
#        self.fakeCombo = FakeCombo(self)
#        self.fakeCombo.setModel(model)
#        self.fakeCombo.view().setMinimumWidth(self.fakeCombo.view().sizeHintForColumn(0))
#        self.fakeCombo.setFixedSize(self.slider.labelRect.size())
#        self.fakeCombo.setCurrentIndex(abs(fract) - 1)
#        self.fakeCombo.currentIndexChanged.connect(self.setFractFromCombo)
#
#    def setFractFromCombo(self, index):
#        available = self.fakeCombo.itemData(index, FractRole)
#        if not available:
#            print('errore fract disponibili?!')
#            return
#        newIndex = index + 1
#        if abs(self.fract & 127) == abs(newIndex):
#            return
#        if self.fract > 0:
#            if not available & 1:
#                newIndex *= -1
#        else:
#            if not available & 2:
#                newIndex *= -1
#        self.setFract(newIndex + (self.fract >> 7))
#        QtWidgets.QApplication.sendEvent(self.window(), QtGui.QStatusTipEvent(self.slider.statusTip()))
#
#    def setFract(self, fract):
#        self.fract = fract
#        self.fractChanged.emit(fract)
#
#    def resizeEvent(self, event):
#        self.fakeCombo.move(self.slider.mapTo(self, self.slider.labelRect.topLeft()))
#
##    def setModel(self, model):
##        self.fakeCombo.setModel(model)
##        self.fakeCombo.view().setMinimumWidth(self.fakeCombo.view().sizeHintForColumn(0))
##        self.fakeCombo.setFixedSize(self.slider.labelRect.size())
##        self.fakeCombo.setFixedSize(QtCore.QSize(self.slider.labelRect.width(), 1))
#
#    @property
#    def fract(self):
#        return self.slider.fract
#
#    @fract.setter
#    def fract(self, fract):
#        self.slider.setFract(fract)
#        self.fakeCombo.setStatusTip(self.slider.statusTip())
##        self.setStatusTip(self.slider.statusTip())
#
#    def setValue(self, *args):
#        self.slider.setValue(*args)
#        self.fakeCombo.setStatusTip(self.slider.statusTip())


class NodeItem(QtWidgets.QGraphicsItem):
    _rect = QtCore.QRectF(-3, -3, 6, 6)
    normalPen = QtGui.QPen(QtGui.QColor(237, 255, 120, 201), 1)
    normalPen.setCosmetic(True)
    normalBrush = QtGui.QBrush(QtGui.QColor(237, 255, 120, 64))

    disabledPen = QtGui.QPen(QtGui.QColor(237, 255, 120, 11), 1)
    disabledPen.setCosmetic(True)

    hoverPen = QtGui.QPen(QtGui.QColor(QtCore.Qt.red), 1)
    hoverPen.setCosmetic(True)
    hoverBrush = QtCore.Qt.NoBrush

    invisiblePen = QtCore.Qt.NoPen
    invisibleBrush = QtCore.Qt.NoBrush

    selectPen = QtGui.QPen(QtGui.QColor(255, 116, 255), 1)
    selectPen.setCosmetic(True)
    selectBrush = QtCore.Qt.NoBrush

#    pen = normalPen
    pens = disabledPen, normalPen
    brush = normalBrush

    def __init__(self, path, selectable=False):
        QtWidgets.QGraphicsItem.__init__(self)
        self.path = path
        self.baseFlags = self.flags() | self.ItemIgnoresTransformations | self.ItemSendsGeometryChanges
        self.setFlags(self.baseFlags | (self.ItemIsSelectable | self.ItemIsMovable if selectable else 0))
        self.setAcceptsHoverEvents(True)
        self.setZValue(10)
        self.selectable = selectable
        self.pen = self.pens[selectable]
        self.fract = 0

    @property
    def waveRatio(self):
        try:
            return self._waveRatio
        except:
            try:
                self._waveRatio = self.scene().waveRatio
                self._halfWaveRatio = self._waveRatio * .5
                return self._waveRatio
            except:
                return 0

    @property
    def waveSnap(self):
        try:
            return self.scene().waveSnap
        except:
            return False

    @property
    def valueSnap(self):
        try:
            return self.scene().valueSnap
        except:
            return False

    @property
    def envSnap(self):
        try:
            return self.scene().envSnap
        except:
            return False

    def setFract(self, fract):
        self.fract = fract
        self.setZValue(-abs(fract) * .01 + .01)

    def hoverEnterEvent(self, event):
        QtWidgets.QGraphicsItem.hoverEnterEvent(self, event)
        self.scene().notifyHover(self)

    def hoverLeaveEvent(self, event):
        QtWidgets.QGraphicsItem.hoverLeaveEvent(self, event)
        self.scene().notifyHover()

    def setSelectable(self, selectable):
        if selectable:
            self.setFlags(self.baseFlags | self.ItemIsSelectable | self.ItemIsMovable)
        else:
            self.setFlags(self.baseFlags)
            self.path.slider.setSliderEnabled(False)
        self.selectable = selectable
        self.pen = self.pens[selectable]

    def itemChange(self, change, value):
        if change == self.ItemPositionChange:
            value.setX(sanitize(0, value.x(), 1))
            value.setY(sanitize(-1, value.y(), 0))
            if self.isUnderMouse():
                snapFlag = (QtWidgets.QApplication.mouseButtons() == QtCore.Qt.LeftButton and \
                    QtWidgets.QApplication.keyboardModifiers() == QtCore.Qt.ShiftModifier)
                if self.waveSnap or snapFlag:
                    diff = value.x() % self.waveRatio
                    x = value.x() - diff
                    if diff > self._halfWaveRatio:
                        value.setX(x + self.waveRatio)
                    else:
                        value.setX(x)
                if self.valueSnap or snapFlag:
                    diff = value.y() % .05
                    y = value.y() - diff
                    if diff > .025:
                        value.setY(y + .05)
                    else:
                        value.setY(y)
                if self.envSnap:
                    for item in self.scene().paths.values():
                        if item != self.path and item.near(value):
                            value.setY(item.yAtX(value.x()))
        elif change == self.ItemPositionHasChanged:
            self.path.redraw(emit=value.y() * -1)
        elif change == self.ItemSelectedChange:
            [i.setSelected(False) for i in self.scene().selectedItems() if i != self]
        elif change == self.ItemSelectedHasChanged:
            if self.isSelected():
                self.pen = self.selectPen
                self.path.slider.setSliderEnabled(True)
                self.path.slider.setValue(self.y() * -1, False)
            else:
                self.path.slider.setSliderEnabled(False)
                self.pen = self.pens[self.selectable]
        return QtWidgets.QGraphicsItem.itemChange(self, change, value)

    def boundingRect(self):
        return self._rect

    def contextMenuEvent(self, event):
        if self.selectable:
            self.setSelected(True)
            menu = QtWidgets.QMenu()
            self.path.curveMenu.nodeIndex = self.path.getSortedNodes().index(self)
            self.path.checkCurveMenu()
            menu.addMenu(self.path.curveMenu)
            menu.addSeparator()
            removeAction = menu.addAction(QtGui.QIcon.fromTheme('edit-delete'), 'Remove node')
            removeAction.triggered.connect(lambda: self.path.removeNode(self))
            res = menu.exec_(QtGui.QCursor.pos())
            if res and res.data() is not None:
                self.path.setCurve(res.data())

    def mousePressEvent(self, event):
        if not self.selectable:
            return QtWidgets.QGraphicsItem.mousePressEvent(self, event)
        if event.modifiers() == QtCore.Qt.ShiftModifier:
            self.path.removeNode(self)

    def mouseMoveEvent(self, event):
        self.scene().notifyPosition(self)
        QtWidgets.QGraphicsItem.mouseMoveEvent(self, event)

    def selectionRect(self):
        viewTransform = self.scene().view.viewportTransform()
        inverted, _ = viewTransform.inverted()
        transform = self.deviceTransform(viewTransform)
        return inverted.mapRect(transform.mapRect(self.sceneBoundingRect()))

    def _shape(self):
        transform, _ = self.scene().view.transform().inverted()
        path = QtGui.QPainterPath()
        rect = QtWidgets.QGraphicsItem.sceneBoundingRect(self).adjusted(-5, -5, 5, 5)
        path.addRect(transform.mapRect(rect))
#        print(rect, path.boundingRect())
        return path

    #overriding contains() has problems with isUnderMouse()
    #we use it only for envelope switch detection
    def _contains(self, pos):
        viewTransform = self.scene().view.viewportTransform()
        inverted, _ = viewTransform.inverted()
        transform = self.deviceTransform(viewTransform)
        rect = transform.mapRect(self.sceneBoundingRect())
#        contains = pos in inverted.mapRect(rect)
#        print(contains, pos, inverted.mapRect(rect))
        return pos in inverted.mapRect(rect)
#        path = transform.map(self.path())
#        stroke = self.stroker.createStroke(path)
#        actual = inverted.map(stroke)
#        return actual.contains(pos)

#        shape = QtWidgets.QGraphicsItem.shape(self)

#    def sceneBoundingRect(self):
#        transform, _ = self.scene().view.transform().inverted()
#        return transform.mapRect(QtWidgets.QGraphicsItem.sceneBoundingRect(self))

    def paint(self, qp, option, widget):
        qp.setPen(self.pen)
        qp.setBrush(self.brush)
        qp.drawEllipse(self._rect)


class EnvelopePath(QtWidgets.QGraphicsPathItem):
#    normalPen = QtGui.QPen(QtGui.QColor(169, 214, 255, 125), 1)
#    normalPen = QtGui.QPen(QtGui.QColor(64, 192, 216, 128), 1)
##    normalPen = QtGui.QPen(QtGui.QColor(237, 255, 120, 201), 1)
#    normalPen.setCosmetic(True)
#    selectPen = QtGui.QPen(QtGui.QColor(64, 192, 216), 1.5)
##    selectPen = QtGui.QPen(QtGui.QColor(255, 116, 255), 1)
#    selectPen.setCosmetic(True)
#    pens = normalPen, selectPen

    wavePens = []
    for color in waveColors:
        _normalPen = QtGui.QPen(color.adjusted(a=125), 1)
        _normalPen.setCosmetic(True)
        _selectPen = QtGui.QPen(color, 1.5)
        _selectPen.setCosmetic(True)
        wavePens.append((_normalPen, _selectPen))
    pens = wavePens[0]
    

    stroker = QtGui.QPainterPathStroker()
    stroker.setWidth(4)
    nearStroker = QtGui.QPainterPathStroker()
    nearStroker.setWidth(15)

    def __init__(self, slider, envelope):
        QtWidgets.QGraphicsPathItem.__init__(self)
        self.slider = slider
        self.slider.fractChanged.connect(self.setFract)
        self.envelope = envelope
        self.curves = envelope.curves
#        self.uniqueEnvelope = []
        self.slider.valueChanged[float, float].connect(self.setValue)
        self.nodes = []
        self.closed = False
        self.selectable = False
        self.pens = self.wavePens[abs(slider.fract) >> 7]
        self.setPen(self.pens[self.selectable])

        self.menu = QtWidgets.QMenu()
        self.menu.aboutToShow.connect(self.checkCurveMenu)
        self.curveMenu = self.menu.addMenu('Curve type')
        self.curveMenu.nodeIndex = 0
        self.curveActions = QtWidgets.QActionGroup(self.curveMenu)
        self.linearAction = self.curveMenu.addAction(CurveIcon(0), curves[0])
        self.linearAction.setData(QtCore.QEasingCurve.Linear)
        self.linearAction.setCheckable(True)
        self.curveActions.addAction(self.linearAction)
        self.curveActionDict = {0: self.linearAction}
        for curve in sorted(cubicTranslation):
            action = self.curveMenu.addAction(CurveIcon(curve), curves[curve])
            action.setData(curve)
            action.setCheckable(True)
            self.curveActions.addAction(action)
            self.curveActionDict[curve] = action

    def setup(self):
        for x, y, curve in self.envelope.fullIter():
            node = NodeItem(self)
            node.setPos(x, -y)
            self.scene().addItem(node)
            self.addNode(node)
        self.close()

    def cubicTranslate(self, curve, pos1, pos2):
        return cubicTranslation[curve](pos1.x(), pos1.y(), pos2.x(), pos2.y())

    def applyEnvelope(self):
        self.closed = False
        while len(self.envelope) > len(self.nodes):
            node = NodeItem(self)
            self.scene().addItem(node)
            self.nodes.append(node)
            node.setFract(self.slider.fract)
        while len(self.envelope) < len(self.nodes):
            self.scene().removeItem(self.nodes.pop())
        for (x, y), node in zip(self.envelope, self.nodes):
            node.setPos(x, -y)

        self.closed = True
        self.redraw(True)
        self.nodes[0].setSelected(True)

    def setFract(self, fract):
        [n.setFract(fract) for n in self.nodes]
        QtWidgets.QGraphicsPathItem.setZValue(self, -abs(fract) * .01)
        self.pens = self.wavePens[abs(fract) >> 7]
        self.setPen(self.pens[self.selectable])
#        self.setZValue(-fract * .01)

    def setSelectable(self, selectable):
        [n.setSelectable(selectable) for n in self.nodes]
        self.selectable = selectable
        self.setPen(self.pens[selectable])
        if selectable:
            self.getSortedNodes()[0].setSelected(True)

    def setValue(self, value, oldValue):
        for node in self.nodes:
            if node.isSelected():
                node.setY(value * -1)
                self.envelope[node.x()] = value
                self.scene().notifyPosition(node, True)
                break
#        else:
#            self.slider.setValue(oldValue, False)
#            self.slider.setSliderEnabled(False)
#        self.redraw()

    def setZValue(self, z):
        QtWidgets.QGraphicsPathItem.setZValue(self, z)
        [n.setZValue(z + .01) for n in self.nodes]

    def addNode(self, node):
        self.nodes.append(node)
        node.setFract(self.slider.fract)

    def aboutToInsert(self):
        self.closed = False

    def insertComplete(self, node):
        self.closed = True
        insertIndex = self.getSortedNodes().index(node)
        if not self.curves:
            return
        if insertIndex <= max(self.curves):
            moved = set()
            for index in reversed(self.curves.keys()):
                if index <= insertIndex:
                    break
                moved.add(index)
                newIndex = index + 1
                self.curves[newIndex] = self.curves[index]
                moved.discard(newIndex)
            for index in moved:
                self.curves.pop(index)

    def removeNode(self, node):
        if len(self.nodes) > 1:
            nodeIndex = self.getSortedNodes().index(node)
            self.nodes.remove(node)
            self.scene().removeItem(node)
            self.redraw(True)
            self.nodes[0].setSelected(True)
            self.scene().notifyPosition()
            if nodeIndex in self.curves:
                self.curves.pop(nodeIndex)

    def getSortedNodes(self):
        return sorted(self.nodes, key=lambda n: n.x())

    def redraw(self, rebuild=False, emit=False):
        if not self.closed:
            return
        self.envelope.clear()
        path = self.path()
        if rebuild or self.curves:
            path = QtGui.QPainterPath()
            path.lineTo(0, 0)
            count = -1
        else:
            count = path.elementCount()
        if not self.curves and not rebuild:
            for index, node in enumerate(self.getSortedNodes()):
                if index >= count:
                    path.lineTo(node.pos())
                else:
                    path.setElementPositionAt(index + 1, node.x(), node.y())
                self.envelope[node.x()] = -node.y()
            count = path.elementCount()
            if count == len(self.nodes) + 1:
                path.lineTo(1, node.y())
            else:
                path.setElementPositionAt(count - 1, 1, node.y())
        else:
            prevPos = QtCore.QPoint(0, 0)
            for index, node in enumerate(self.getSortedNodes()):
                curve = self.curves.get(index)
                if not curve:
                    path.lineTo(node.pos())
                else:
                    data = self.cubicTranslate(curve, prevPos, node.pos())
                    path.cubicTo(*data)
                self.envelope[node.x()] = -node.y()
                prevPos = node.pos()
            path.lineTo(1, node.y())
        self.setPath(path)
        if emit:
            self.slider.setValue(emit, False)
        self.scene().pathChanged.emit(self)

    def checkCurveMenu(self):
        if self.curveMenu.nodeIndex < len(self.nodes):
            nodes = self.getSortedNodes()
            prevX = 0
            node = nodes[self.curveMenu.nodeIndex]
            if self.curveMenu.nodeIndex:
                prevX = nodes[self.curveMenu.nodeIndex - 1].x()
#            print(node.x(), prevX)
            if node.x() - prevX < .005:
                self.curveMenu.setEnabled(False)
            else:
                self.curveMenu.setEnabled(True)
                self.curveActionDict[self.curves.get(self.curveMenu.nodeIndex, 0)].setChecked(True)
        else:
            self.linearAction.setChecked(True)

    def contextMenuEvent(self, event):
        if self.selectable and self.contains(event.pos()):
            x = event.scenePos().x()
            self.curveMenu.nodeIndex = 0
            for i, node in enumerate(self.getSortedNodes()):
                self.curveMenu.nodeIndex = i
                if x < node.selectionRect().right():
                    break
            else:
                self.curveMenu.nodeIndex += 1
            res = self.menu.exec_(QtGui.QCursor.pos())
            if res:
                self.setCurve(res.data())
        else:
            QtWidgets.QGraphicsPathItem.contextMenuEvent(self, event)

    def setCurve(self, curve, nodeIndex=None):
        if not nodeIndex:
            nodeIndex = self.curveMenu.nodeIndex
        if not curve:
            try:
                self.curves.pop(self.curveMenu.nodeIndex)
            except:
                pass
        else:
            self.curves[self.curveMenu.nodeIndex] = curve
            if len(self.nodes) == self.curveMenu.nodeIndex:
                self.closed = False
                node = NodeItem(self, True)
                self.scene().addItem(node)
                node.setPos(1, 0)
                self.addNode(node)
                node.setZValue(self.nodes[0].zValue())
                self.closed = True
        self.redraw(True)

    def close(self):
        self.closed = True
        path = QtGui.QPainterPath()
        path.moveTo(0, 0)
        prevPos = QtCore.QPoint(0, 0)
        for index, node in enumerate(self.getSortedNodes()):
            curve = self.curves.get(index)
            if not curve:
                path.lineTo(node.pos())
            else:
                path.cubicTo(*self.cubicTranslate(curve, prevPos, node.pos()))
            prevPos = node.pos()
        path.lineTo(1, node.y())
        self.setPath(path)
#        path = self.path()
#        path.lineTo(1, self.nodes[-1].y())
#        self.setPath(path)

    def yAtX(self, pos):
        prevX = prevY = 0
        if not pos:
            return -self.envelope[0]
        for i, (x, y) in enumerate(self.envelope):
            if x == pos:
                return -y
            elif x < pos:
                prevX = x
                prevY = y
                continue
            else:
                curve = self.curves.get(i)
                diff = y - prevY
                ratio = (pos - prevX) / (x - prevX)
                if not curve:
                    return -(prevY + diff * ratio)
                return -(prevY + diff * getCurveFunc(curve)(ratio))
        return -y

    def near(self, pos):
        viewTransform = self.scene().view.viewportTransform()
        inverted, _ = viewTransform.inverted()
        transform = self.deviceTransform(viewTransform)
        path = transform.map(self.path())
        stroke = self.nearStroker.createStroke(path)
        actual = inverted.map(stroke)
        return actual.contains(pos)

    def contains(self, pos):
        viewTransform = self.scene().view.viewportTransform()
        inverted, _ = viewTransform.inverted()
        transform = self.deviceTransform(viewTransform)
        path = transform.map(self.path())
        stroke = self.stroker.createStroke(path)
        actual = inverted.map(stroke)
        return actual.contains(pos)
#        transform, _ = self.scene().view.transform().inverted()
##        path = QtGui.QPainterPath()
##        path.addRect(transform.mapRect(QtWidgets.QGraphicsItem.sceneBoundingRect(self)))
#        return transform.map(self.path())


class ToolTipItem(QtWidgets.QGraphicsItem):
    background = QtGui.QBrush(QtGui.QColor(128, 128, 128, 96))
    baseRect = _rect = QtCore.QRectF(0, 0, 30, 18)
    fullRect = QtCore.QRectF(0, 0, 30, 36)

    def __init__(self):
        QtWidgets.QGraphicsItem.__init__(self)
        self.title = ''
        self.posText = ''
        self.item = None
        self.setFlags(self.flags() | self.ItemIgnoresTransformations)
        self.fontMetrics = QtGui.QFontMetricsF(QtWidgets.QApplication.fontMetrics())
        self.hBorder = self.fontMetrics.width('8')
        self.vBorder = self.hBorder * .5
        self.margin = self.hBorder * 2
        self.fullRect.setHeight(self.fontMetrics.height() * 3 + self.hBorder)
        self.baseFont = QtWidgets.QApplication.font()
        self.titleFont = QtGui.QFont(self.baseFont)
        self.titleFont.setBold(True)
#        self.fullRect.setWidth(self.fontMetrics.width('value: 0.0000'))

    def setItem(self, item, pos=None):
        if self.item == item:
            return
        self.title = getCardinal(abs(item.fract) & 127)
        if not pos:
            self.posText = ''
            self._rect = self.baseRect
        else:
            if self.scene().waveSnap:
                self.posText = 'Value: {:.02f}%\nWave: {}'.format(max(0, -item.y() * 100), 
                    int(round(self.scene().start + item.x() / self.scene().waveRatio)) + 1)
            else:
                self.posText = 'Value: {:.02f}%\nPos.: {}%'.format(max(0, -item.y()) * 100, int(item.x() * 100))
            self.fullRect.setWidth(self.fontMetrics.boundingRect(self.fullRect, QtCore.Qt.AlignJustify, self.posText).width() + self.margin)
            self.textRect = self.fullRect.adjusted(self.hBorder, self.vBorder, -self.hBorder, -self.vBorder)
            self._rect = self.fullRect
        transform, _ = self.scene().view.transform().inverted()
        rect = transform.mapRect(self.sceneBoundingRect().adjusted(-5, -5, 5, 5))
        pos = item.pos()
        pos.setX(sanitize(0, pos.x() - rect.width(), 1 - rect.width()))
        pos.setY(sanitize(-1, pos.y() - rect.height(), 0 - rect.height()))
        self.setPos(pos)

    def boundingRect(self):
        return self._rect

    def paint(self, qp, option, widget):
        qp.setPen(QtCore.Qt.NoPen)
        qp.setBrush(self.background)
        qp.drawRoundedRect(self._rect, 2, 2)
        qp.setPen(QtCore.Qt.white)
        qp.setFont(self.titleFont)
        if self.posText:
            qp.drawText(self.textRect, QtCore.Qt.AlignHCenter|QtCore.Qt.AlignTop, self.title)
            qp.setFont(self.baseFont)
            qp.drawText(self.textRect, QtCore.Qt.AlignLeft|QtCore.Qt.AlignBottom, self.posText)
        else:
            qp.drawText(self._rect, QtCore.Qt.AlignCenter, self.title)


class IndexItem(QtWidgets.QGraphicsItemGroup):
    linePen = QtGui.QPen(QtGui.QColor(QtCore.Qt.darkGray), .5)
    linePen.setCosmetic(True)
    thinLinePen = QtGui.QPen(QtGui.QColor(250, 250, 250, 64), .5)
    thinLinePen.setCosmetic(True)
    indexBrush = QtGui.QBrush(QtGui.QColor(QtCore.Qt.lightGray))

    def __init__(self, index, showIndex):
        QtWidgets.QGraphicsItemGroup.__init__(self)
        self.index = index
        self.line = QtWidgets.QGraphicsLineItem(QtCore.QLineF(0, -2, 0, 1))
        self.line.setPen(self.linePen if showIndex else self.thinLinePen)
        self.addToGroup(self.line)
        if showIndex:
            self.line.setZValue(-1)

            self.indexItem = QtWidgets.QGraphicsSimpleTextItem(' {}'.format(index + 1))
            self.indexItem.setFlags(self.indexItem.flags() | self.ItemIgnoresTransformations)
            self.indexItem.setBrush(self.indexBrush)
            self.indexItem.setY(-1)
            self.addToGroup(self.indexItem)

            self.indexBgd = QtWidgets.QGraphicsRectItem(self.indexItem.boundingRect().adjusted(0, -5, 2, 1))
            self.indexBgd.setFlags(self.indexItem.flags())
            brush = QtGui.QBrush(QtGui.QColor(64, 64, 64, 192))
            self.indexBgd.setBrush(brush)
            self.indexBgd.setPen(QtGui.QPen(QtCore.Qt.NoPen))
            self.indexBgd.setY(-1)
            self.indexBgd.setZValue(-1)
            self.addToGroup(self.indexBgd)


class EnvelopeScene(QtWidgets.QGraphicsScene):
    playPen = QtGui.QPen(QtGui.QColor('orange'), .5)
    playPen.setCosmetic(True)
    playHeadMoved = QtCore.pyqtSignal(float)
    waveValues = QtCore.pyqtSignal(object)
    pathChanged = QtCore.pyqtSignal(object)

    previewResolution = 64
    silentWave = np.array([0] * previewResolution, dtype='float64')

    def __init__(self, main):
        QtWidgets.QGraphicsScene.__init__(self)
        self.main = main
        self.view = main.envelopeView
        self.setSceneRect(QtCore.QRectF(0, -1, 1., 1.))
        self.waveRatio = .1
        self.waveSnap = False
        self.valueSnap = False
        self.envSnap = False
        self.currentEnvelope = None
        self.pathChanged.connect(self.updateShape)

        self.playHead = self.addLine(QtCore.QLineF(0, -2, 0, 1))
        self.playHead.setPen(self.playPen)
        self.playHead.setZValue(-10)

        self.toolTipItem = ToolTipItem()
        self.addItem(self.toolTipItem)
        self.toolTipItem.setPos(-2, 2)

        self.shapeItem = QtWidgets.QGraphicsPathItem()
        self.addItem(self.shapeItem)
        self.shapeItem.setPen(QtGui.QPen(QtCore.Qt.NoPen))

        envBrush = QtGui.QLinearGradient(0, -1, 0, 1)
        envBrush.setCoordinateMode(envBrush.LogicalMode)
        envBrush.setColorAt(0, QtGui.QColor(0, 128, 192, 64))
        envBrush.setColorAt(.5, QtGui.QColor(200, 128, 192, 64))
        envBrush.setColorAt(1, QtGui.QColor(0, 128, 192, 64))

        self.shapeItem.setBrush(envBrush)

        self.indexItems = []

        self.toolTipTimer = QtCore.QTimer()
        self.toolTipTimer.setInterval(800)
        self.toolTipTimer.setSingleShot(True)
        self.toolTipTimer.timeout.connect(lambda: self.toolTipItem.setVisible(False))

    @property
    def sortedSliders(self):
        return sorted(self.envelopes.keys(), key=lambda s: (abs(s.fract & 127), -(s.fract & 127)))

    def setCurrent(self, envelope):
        self.currentEnvelope = envelope
        self.updateShape(envelope)

    def updateShape(self, envelope):
        if envelope != self.currentEnvelope:
            return
        path = envelope.path()
        path.lineTo(1, 0)
        path.closeSubpath()
        self.shapeItem.setPath(path)

    def notifyHover(self, item=None):
        if not item:
            self.toolTipItem.setVisible(False)
        else:
            self.toolTipItem.setVisible(True)
            self.toolTipItem.setItem(item)

    def notifyPosition(self, item=None, timeout=False):
        if not item:
            self.toolTipItem.setVisible(False)
        else:
            self.toolTipItem.setVisible(True)
            self.toolTipItem.setItem(item, True)
            if timeout:
                self.toolTipTimer.start()

    def setWaveRange(self, start, end):
        self.start = start
        if not end:
            end = 64
        self.end = end
        for item in self.indexItems:
            self.removeItem(item)
        self.waveRatio = 1. / (end - start)
        if self.waveRatio < .025:
            labelMask = 5
        else:
            labelMask = 1
        for i in range(start, end):
            item = IndexItem(i, i in (start, end - 1) or not (i + 1) % labelMask)
            self.addItem(item)
            item.setZValue(-50)
            if i != start:
                item.setX((i - start) * self.waveRatio)
        item = IndexItem(i + 1, False)
        self.addItem(item)
        item.setZValue(-50)
        item.setX((end - start) * self.waveRatio)

    def updateValues(self, pos, ignore=None, update=True):
        self.playHead.setX(pos)
        values = np.copy(self.silentWave)
        for slider, envelope in self.envelopes.items():
            prevX = prevY = 0
            if not pos:
                value = envelope[0]
#                if envelope.get(0) is not None:
#                    value = envelope[0]
#                else:
#                    value = 0
            else:
                for i, (x, y) in enumerate(sorted(envelope)):
                    if not pos:
                        value = 0
                        break
                    elif x == pos:
                        value = envelope[x]
                    elif x < pos:
                        prevX = x
                        prevY = envelope[x]
                        continue
                    else:
                        y = envelope[x]
                        diff = y - prevY
                        ratio = (pos - prevX) / (x - prevX)
                        curve = envelope.curves.get(i)
                        if not curve:
                            value = prevY + diff * ratio
                        else:
                            value = prevY + diff * getCurveFunc(curve)(ratio)
                    break
                else:
#                    print(envelope.data)
                    value = envelope[x]
            if update and slider != ignore:
                slider.setValue(value, False)
#            value /= slider.fract * 2
#            value *= .5
            fract = abs(slider.fract)
            polarity = 1 if slider.fract > 0 else -1
            np.add(values, np.multiply(waveFunction[fract >> 7](fract & 127, self.previewResolution), value * polarity), out=values)
#        self.waveValues.emit(np.clip(values, -1, 1))
        self.waveValues.emit(values)

    def setWaveSnap(self, waveSnap):
        self.waveSnap = waveSnap

    def setValueSnap(self, valueSnap):
        self.valueSnap = valueSnap

    def setEnvSnap(self, envSnap):
        self.envSnap = envSnap

    def getSortedValues(self, slider):
        for x in sorted(self.envelopes[slider]):
            yield x, self.envelopes[slider][x]

    def updatePaths(self):
        existing = [i for i in self.items() if isinstance(i, EnvelopePath)]
        for slider in self.sortedSliders:
            pathItem = self.paths.get(slider)
            if not pathItem:
                pathItem = self.paths[slider] = EnvelopePath(slider, self.envelopes[slider])
                self.addItem(pathItem)
                pathItem.setup()
                pathItem.setPos(0, 0)
#                pathItem.valueChanged.connect(lambda value, slider=slider: slider.setValue(value, False))
            elif pathItem in existing:
                existing.remove(pathItem)
#                pathItem.checkNodes()
#                for x, y, node in izip_longest(self.envelopes[slider], pathItem.nodes, fillvalue=None):
#                    if node is None:
#                        node = NodeItem(pathItem)
#                        node.setPos(x, -y)
#                        self.addItem(node)
#                        pathItem.addNode(node)
#                    else:
#                        node.setPos(x, -y)
            pathItem.setZValue(-abs(slider.fract & 127) * .01)
            pathItem.setSelectable(slider.selector.isChecked())
        for pathItem in existing:
            [self.removeItem(n) for n in pathItem.nodes]
            self.removeItem(pathItem)

    def mousePressEvent(self, event):
        if event.buttons() == QtCore.Qt.MiddleButton:
            pos = event.scenePos()
            for item in self.items(pos):
                if isinstance(item, NodeItem) and item._contains(pos):
                    item.path.slider.selector.click()
        QtWidgets.QGraphicsScene.mousePressEvent(self, event)

    def mouseMoveEvent(self, event):
        x = sanitize(0, event.scenePos().x(), 1)
        self.updateValues(x, self.main.currentSlider if self.selectedItems() else None)
        self.playHeadMoved.emit(x)
#        print(self.main.currentSlider, event.scenePos())
        QtWidgets.QGraphicsScene.mouseMoveEvent(self, event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            node = NodeItem(self.main.currentPath, True)
            self.main.currentPath.aboutToInsert()
            self.main.currentPath.addNode(node)
            pos = event.scenePos()
            if self.waveSnap:
                diff = pos.x() % self.waveRatio
                x = pos.x() - diff
                if diff > self.waveRatio * .5:
                    pos.setX(x + self.waveRatio)
                else:
                    pos.setX(x)
            if self.valueSnap:
                diff = pos.y() % .05
                y = pos.y() - diff
                if diff > .025:
                    pos.setY(y + .05)
                else:
                    pos.setY(y)
            node.setPos(pos)
            self.addItem(node)
            self.main.currentPath.insertComplete(node)
            self.main.currentPath.redraw(True)
            node.setSelected(True)
        QtWidgets.QGraphicsScene.mouseDoubleClickEvent(self, event)


class PreviewScene(QtWidgets.QGraphicsScene):
    def __init__(self):
        QtWidgets.QGraphicsScene.__init__(self)
        self.previewTimer = QtCore.QTimer()
        self.previewTimer.setSingleShot(True)
        self.previewTimer.setInterval(1)
        self.previewTimer.timeout.connect(self.paintPreview)
        self.setSceneRect(QtCore.QRectF(0, -1, 63, 2))

        self.currentValues = np.array([0] * 64)
        self.currentPreviewPath = QtGui.QPainterPath()
        self.currentPreviewPath.moveTo(0, 0)
        for s in range(1, 64):
            self.currentPreviewPath.lineTo(s, 0)
        self.pathItem = self.addPath(self.currentPreviewPath)
        pen = QtGui.QPen(QtGui.QColor(64, 192, 216), 1)
        pen.setCosmetic(True)
        self.pathItem.setPen(pen)

    def queuePreview(self, values):
        if np.array_equal(values, self.currentValues):
            return
        self.currentValues = values
        self.previewTimer.start()

    def paintPreview(self):
        for sample, value in zip(range(64), self.currentValues):
            self.currentPreviewPath.setElementPositionAt(sample, sample, -value)
        self.pathItem.setPath(self.currentPreviewPath)


class SpecHarmonicsScrollArea(QtWidgets.QScrollArea):
    addEnvelopeRequest = QtCore.pyqtSignal()

    def mouseDoubleClickEvent(self, event):
        widget = QtWidgets.QApplication.widgetAt(QtGui.QCursor.pos())
        if widget == self.viewport():
            self.addEnvelopeRequest.emit()


class SpecTransformDialog(QtWidgets.QDialog):
    shown = False

    def __init__(self, parent, transform=None):
        QtWidgets.QDialog.__init__(self, parent)
        loadUi('ui/spectralmorph.ui', self)

        self.envelopeScene = EnvelopeScene(self)
        self.envelopeView.setScene(self.envelopeScene)
        self.envelopeScene.envelopes = self.envelopes = {}
        self.envelopeScene.paths = self.paths = {}
        self.envelopeScene.playHeadMoved.connect(self.moveProgressSlider)

        self.previewScene = PreviewScene()
        self.previewView.setScene(self.previewScene)
        self.envelopeScene.waveValues.connect(self.previewScene.queuePreview)

        self.selectors = QtWidgets.QButtonGroup()

        self.scrollArea.addEnvelopeRequest.connect(self.addEnvelope)
        self.deleteBtn.clicked.connect(self.removeEnvelope)
        self.waveSnapChk.toggled.connect(self.envelopeScene.setWaveSnap)
        self.valueSnapChk.toggled.connect(self.envelopeScene.setValueSnap)
        self.envSnapChk.toggled.connect(self.envelopeScene.setEnvSnap)

        self.sliderModel = QtGui.QStandardItemModel()
        for h, l in enumerate(HarmonicsSlider.names):
            item = QtGui.QStandardItem('{}. {}'.format(h + 1, l))
            item.setData(2, FractRole)
            items = [item]
            for w in range(1, 5):
                item = QtGui.QStandardItem()
                item.setData(2, FractRole)
                items.append(item)
            self.sliderModel.appendRow(items)
        for h in range(h + 1, 50):
            item = QtGui.QStandardItem('{} harmonic'.format(getCardinal(h + 1)))
            item.setData(2, FractRole)
            items = [item]
            for w in range(1, 5):
                item = QtGui.QStandardItem()
                item.setData(2, FractRole)
                items.append(item)
            self.sliderModel.appendRow(items)

        self.updatePaths = self.envelopeScene.updatePaths
        self.selectors.buttonClicked.connect(self.setCurrentEnvelope)
        self.progressSlider.valueChanged.connect(self.movePlayHead)
        self.toolTipSlider.valueChanged.connect(self.progressSlider.setValue)

#        self.startLbl.header = u'▸'
#        self.endLbl.header = u'▮▮'
        self.scrollArea.viewport().setStyleSheet('''
            QScrollArea > QWidget {
                background: rgba(32, 32, 32, 208);
            }
        ''')
        self.harmonicsWidget.setStyleSheet('''
            .QWidget {
                background: transparent;
            }
            HarmonicsSlider {
                color: white;
            }
        ''')
        self.startLbl.setStyleSheet('''
            QLabel {
                padding-left: 5px;
                padding-right: 5px;
            }
        ''')
        self.endLbl.setStyleSheet(self.startLbl.styleSheet())
        self.startLbl.clicked.connect(lambda: self.progressSlider.setValue(self.progressSlider.minimum()))
        self.endLbl.clicked.connect(lambda: self.progressSlider.setValue(self.progressSlider.maximum()))

#        self.statusbar = StatusBar(self)
#        self.statusbar.setSizeGripEnabled(False)
#        self.buttonLayout.insertWidget(0, self.statusbar)

        self.volumeIcon.iconSize = self.playBtn.iconSize()
        self.volumeIcon.setVolume(self.volumeSlider.value())
        self.volumeIcon.step.connect(lambda step: self.volumeSlider.setValue(self.volumeSlider.value() + self.volumeSlider.pageStep() * step))
        self.volumeIcon.reset.connect(self.volumeSlider.reset)
        self.volumeSlider.valueChanged.connect(self.volumeIcon.setVolume)
#        self.setTransform(transform)

#    def setTransform(self, transform):
        self.transform = transform
        self.prevItem = transform.prevItem
        self.nextItem = transform.nextItem

        self.start = self.prevItem.index
        self.end = self.nextItem.index
        if not self.start and not self.end:
            self.applyToNextChk.setEnabled(False)
            self.applyToNextChk.setStatusTip('')
        if not self.end:
            self.end = 64
        self.envelopeScene.setWaveRange(self.start, self.end)
        self.progressSlider.blockSignals(True)
        self.progressSlider.setRange(self.start, self.end)
        self.progressSlider.setValue(self.start)
#        self.progressSlider.setToolTip(str(start))
        self.progressSlider.blockSignals(False)
        self.toolTipSlider.setRange(self.start, self.end)
        self.toolTipSlider.setValue(self.start)
        self.startLbl.setNum(self.start + 1)
        self.endLbl.setNum(self.end + 1)

        self.addBtn = AddSliderButton()
        self.hLayout.addWidget(self.addBtn)
        self.addBtn.clicked.connect(self.addEnvelope)
        self.addBtn.setToolTip('Add envelope')

        self.transformData = transform.data['harmonics']
        self.originalData = deepcopy(self.transformData)
        for h, data in self.transformData.items():
            self.addEnvelope(h, *data)

        self.updatePaths()
        self.addToolBtn.addRequested.connect(self.addMultiEnvelopes)

        self.helpDialog = HelpDialog(self)
        self.buttonBox.button(self.buttonBox.Help).clicked.connect(self.getHelp)

    def getHelp(self):
        self.helpDialog.show()
        self.helpDialog.openUrl('qthelp://jidesk.net.bigglesworth.1.0/html/Wavetable Editor/spectral.html', True)

    @property
    def currentSlider(self):
        return self.selectors.checkedButton().parent()

    @property
    def currentHarmonic(self):
        return self.currentSlider.fract

    @property
    def currentPath(self):
        return self.paths[self.selectors.checkedButton().parent()]

    @property
    def sortedSliders(self):
        #sort by harmonic, negative fractions are after positive
#        return sorted(self.envelopes.keys(), key=lambda s: (abs(s.fract), -s.fract))
#        return sorted(self.envelopes.keys(), key=lambda s: (abs(s.fract) & 127, abs(s.fract) >> 7))
        #changed. sorting by harmonic, ignoring sign or wave
        return sorted(self.envelopes.keys(), key=lambda s: abs(s.fract) & 127)

    def movePlayHead(self, value):
        x = float(value - self.start) / (self.end - self.start)
        self.envelopeScene.updateValues(x)
        self.toolTipSlider.setValue(value)
#        self.progressSlider.setToolTip(str(value))

    def moveProgressSlider(self, x):
        self.progressSlider.blockSignals(True)
        self.progressSlider.setValue(int(x * (self.end - self.start)) + self.start)
        self.toolTipSlider.setValue(self.progressSlider.value())
#        self.progressSlider.setToolTip(str(self.progressSlider.value()))
#        self.progressSlider.setValue(int(x * 1000))
        self.progressSlider.blockSignals(False)

    def setCurrentEnvelope(self, btn):
        for slider, path in self.paths.items():
            if slider.selector == btn:
                path.setSelectable(True)
                path.setZValue(10)
                self.envelopeScene.setCurrent(path)
            else:
                path.setZValue(-abs(slider.fract & 127) * .01)
                path.setSelectable(False)

    def checkPolarities(self, newFract):
        for slider in self.envelopes:
            if slider.fract == newFract and slider != self.sender():
                slider.setFract(-newFract)
                break

    @QtCore.pyqtSlot()
    def resetFractions(self):
        sliders = list(self.sortedSliders)
        fracts = [s.fract for s in sliders]
#        self.sliderModel.blockSignals(True)
        for h in range(1, 51):
            for wave in range(5):
                available = 3
                fract = h + (wave << 7)
                if fract in fracts:
                    available -= 1
                if -fract in fracts:
                    available -= 2
                self.sliderModel.setData(self.sliderModel.index(h - 1, wave), available, FractRole)
#        self.sliderModel.blockSignals(False)
        for newIndex, slider in enumerate(sliders):
            oldIndex = self.hLayout.indexOf(slider)
            if oldIndex != newIndex:
                self.hLayout.takeAt(oldIndex)
                self.hLayout.insertWidget(newIndex, slider)

    def removeEnvelope(self):
        if self.sender() == self.deleteBtn:
            slider = self.currentSlider
            number = getCardinal(abs(slider.fract) & 127)
            wave = WaveLabelsExt[abs(slider.fract) >> 7].lower()
            negative = 'negative ' if slider.fract < 0 else 0
            message = 'Delete envelope for {} harmonic, {}{} wave?'.format(number, negative, wave)
            if QtWidgets.QMessageBox.question(self, 'Delete envelope', message, 
                QtWidgets.QMessageBox.Ok|QtWidgets.QMessageBox.Cancel) != QtWidgets.QMessageBox.Ok:
                    return
        else:
            slider = self.sender()
        self.paths.pop(slider)
        self.envelopes.pop(slider)
        self.selectors.removeButton(slider.selector)
        self.hLayout.removeWidget(slider)
        self.updatePaths()
        if not self.selectors.checkedButton():
            sliders = list(self.sortedSliders)
            try:
                sliders[sliders.index(slider)].selector.click()
            except:
                sliders[-1].selector.click()
        slider.deleteLater()
        self.resetFractions()
        self.addBtn.setEnabled(len(self.envelopes) < 50)
        self.addToolBtn.setEnabled(len(self.envelopes) < 50)
        self.deleteBtn.setEnabled(len(self.envelopes) > 1)
#        print([(s.fract, e) for s, e in self.envelopes.items()])

    def addMultiEnvelopes(self, items, wave):
        [self.addEnvelope(fract=fract, wave=wave) for fract in items]

    @QtCore.pyqtSlot()
    def addEnvelope(self, fract=None, nodes=None, curves=None, update=True, wave=None):
        fracts = [s.fract for s in self.envelopes]
        if len(fracts) >= 50:
            self.addBtn.setEnabled(False)
            self.addToolBtn.setEnabled(False)
            return
        if fract is None:
            if wave is None:
                wave = 0
            for fract in range(1, 51):
                fract = fract + (wave << 7)
                if fract not in fracts:
                    break
            else:
                return
        else:
            if wave is not None:
                fract = fract + (wave << 7)
            if fract in fracts:
                return
#            fract += wave << 7
        slider = EnvelopeHarmonicsSlider(fract, self.sliderModel)
#        slider.triggered.connect(self.changeFract)
#        slider.setModel(self.sliderModel)
        slider.fractChanged.connect(self.checkPolarities)
        slider.fractChanged.connect(self.resetFractions)
#        slider.polarityChanged.connect(self.checkPolarities)
        slider.removeRequested.connect(self.removeEnvelope)
        slider.copyRequested.connect(self.copyEnvelope)
        slider.pasteRequested.connect(self.pasteEnvelope)
        envelope = Envelope(fract, nodes, curves)

#        if not self.envelopes or (fracts and fract > max(fracts)):
#            self.hLayout.addWidget(slider)
#        else:
        self.hLayout.addWidget(slider)

        self.envelopes[slider] = envelope

#        self.sliderModel.item(fract).setEnabled(False)
        self.resetFractions()
        if update:
            self.updatePaths()

        self.selectors.addButton(slider.selector)
        if len(self.envelopes) == 1 or self.sender() in (self.addBtn, self.addToolBtn, self.scrollArea):
            slider.selector.click()
        slider.blockSignals(True)
        slider.setValue(envelope[0])
        slider.blockSignals(False)

        self.deleteBtn.setEnabled(len(self.envelopes) > 1)
        QtWidgets.QApplication.processEvents()
        self.scrollArea.ensureWidgetVisible(self.addBtn)

    def setEnvelope(self, slider, values, curves):
#        print(slider.fract, values)
        self.envelopes[slider][:] = values
        self.envelopes[slider].curves.clear()
        self.envelopes[slider].curves.update(curves)
        self.paths[slider].applyEnvelope()
        self.updatePaths()

    def copyEnvelope(self):
        mimeData = QtCore.QMimeData()
        byteArray = QtCore.QByteArray()
        stream = QtCore.QDataStream(byteArray, QtCore.QIODevice.WriteOnly)
        stream.writeQVariant(self.envelopes[self.sender()])
        stream.writeQVariant(self.envelopes[self.sender()].curves)
        mimeData.setData('bigglesworth/EnvelopeData', byteArray)
        QtWidgets.QApplication.clipboard().setMimeData(mimeData)

    def pasteEnvelope(self):
        mimeData = QtWidgets.QApplication.clipboard().mimeData()
        if mimeData.hasFormat('bigglesworth/EnvelopeData'):
            byteArray = mimeData.data('bigglesworth/EnvelopeData')
            stream = QtCore.QDataStream(byteArray)
            self.setEnvelope(self.sender(), stream.readQVariant(), stream.readQVariant())

    def event(self, event):
        if event.type() == QtCore.QEvent.StatusTip:
            if self.isVisible():
                self.statusBar.showMessage(event.tip())
        return QtWidgets.QDialog.event(self, event)

    def resizeEvent(self, event):
        QtWidgets.QDialog.resizeEvent(self, event)
        QtCore.QTimer.singleShot(0, self.resizeScene)

    def showEvent(self, event):
        if not self.shown:
            self.shown = True
            self.envelopeView.fitInView(self.envelopeScene.sceneRect())
            QtCore.QTimer.singleShot(0, self.resizeScene)

    def resizeScene(self):
        transform, _ = self.envelopeView.viewportTransform().inverted()
        margin = transform.m11() * 5
        self.envelopeView.fitInView(self.envelopeScene.sceneRect().adjusted(-margin, 0, margin, 0))
        self.previewView.fitInView(self.previewScene.sceneRect())

    def getData(self):
        return {slider.fract: (list(envelope.nodes), envelope.curves)[:2 if envelope.curves else 1] for slider, envelope in self.envelopes.items()}

    def reject(self):
        if self.originalData != self.getData() and \
            QtWidgets.QMessageBox.question(self, 'Ignore changes?', 
                'Contents of the transformation has been changed.\nAre you sure you want to cancel?', 
                QtWidgets.QMessageBox.Ok|QtWidgets.QMessageBox.Cancel) != QtWidgets.QMessageBox.Ok:
                    return
        QtWidgets.QDialog.reject(self)

    def exec_(self):
        res = QtWidgets.QDialog.exec_(self)
        if res:
#            data = {slider.fract: (list(envelope.nodes), envelope.curves)[:2 if envelope.curves else 1] for slider, envelope in self.envelopes.items()}
            return self.getData()

#    def changeFract(self):
#        print('agggiornato')
#        fracts = [s.fract for s in self.sliders]
#        for h in range(50):
#            self.sliderModel.item(h).setEnabled(h in fracts)
#        pos = self.sender().mapToGlobal(self.sender().slider.labelRect.bottomLeft())
#        pos.setX(pos.x() - 50)
#        if self.popup.isVisible() and self.popup.pos() == pos:
#            self.popup.hide()
#        else:
#            self.popup.move(pos)
#            self.popup.show()
##        QtCore.QTimer.singleShot(12000, self.popup.hide)
#        print(self.sender())

