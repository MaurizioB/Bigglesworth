# *-* encoding: utf-8 *-*

import sys
from Qt import QtCore, QtGui, QtWidgets

from bigglesworth.utils import loadUi, getCardinal, getQtFlags, sanitize
from bigglesworth.wavetables.widgets import HarmonicsSlider, CurveIcon
from bigglesworth.wavetables.utils import curves


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
    def resizeEvent(self, event):
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
        self.label.setFrameStyle(self.label.StyledPanel|self.label.Sunken)

    def setValue(self, value):
        QtWidgets.QSlider.setValue(self, value)
        self.label.setNum(value + 1)
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

class FakeCombo(QtWidgets.QComboBox):
    def paintEvent(self, event):
        pass

class Selector(QtWidgets.QPushButton):
    removeRequested = QtCore.pyqtSignal()

    def __init__(self, main):
        QtWidgets.QPushButton.__init__(self, QtGui.QIcon.fromTheme('document-edit'), '')
        self.main = main
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum))
        self.setMaximumHeight(16)
        self.setCheckable(True)
        self.setStyleSheet('''
            Selector {
                background: darkGray;
                border: 1px solid palette(dark);
                border-style: outset;
                border-radius: 1px;
            }
            Selector:on {
                background: rgb(50, 255, 50);
                border-style: inset;
            }
        ''')

    def mousePressEvent(self, event):
        self.click()

    def contextMenuEvent(self, event):
        self.click()
#        self.clicked.emit(True)
#        self.setChecked(True)
        menu = QtWidgets.QMenu()
        removeAction = menu.addAction(QtGui.QIcon.fromTheme('edit-delete'), 'Remove')
        removeAction.triggered.connect(self.removeRequested.emit)
        if len(self.main.envelopes) == 1:
            removeAction.setEnabled(False)
        menu.exec_(QtGui.QCursor.pos())


class SliderContainer(QtWidgets.QWidget):
    triggered = QtCore.pyqtSignal()
    fractChanged = QtCore.pyqtSignal(int)
    valueChanged = QtCore.pyqtSignal(float, float)
    removeRequested = QtCore.pyqtSignal()

    def __init__(self, main, fract=None, polarity=1):
        QtWidgets.QWidget.__init__(self)
        self.main = main
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        layout.setContentsMargins(1, 2, 1, 2)

        self.selector = Selector(main)
        layout.addWidget(self.selector)

        self.slider = HarmonicsSlider(fract, True, polarity)
        self.slider.valueChanged[float, float].connect(self.valueChanged)
        layout.addWidget(self.slider)
#        self.setValue = self.slider.setValue
        self.setSliderEnabled = self.slider.setSliderEnabled

        self.selector.setMaximumWidth(self.slider.sizeHint().width())
        self.selector.removeRequested.connect(self.removeRequested)

        self.fakeCombo = FakeCombo(self)
        self.fakeCombo.currentIndexChanged.connect(self.setFract)

    def setFract(self, fract):
        self.fract = fract
        self.fractChanged.emit(fract)

    def resizeEvent(self, event):
        self.fakeCombo.move(self.slider.mapTo(self, self.slider.labelRect.topLeft()))

    def setModel(self, model):
        self.fakeCombo.setModel(model)
        self.fakeCombo.view().setMinimumWidth(self.fakeCombo.view().sizeHintForColumn(0))
        self.fakeCombo.setFixedSize(self.slider.labelRect.size())
#        self.fakeCombo.setFixedSize(QtCore.QSize(self.slider.labelRect.width(), 1))

    @property
    def fract(self):
        return self.slider.fract

    @fract.setter
    def fract(self, fract):
        self.slider.setFract(fract)
        self.fakeCombo.setStatusTip(self.slider.statusTip())
#        self.setStatusTip(self.slider.statusTip())

    def setValue(self, *args):
        self.slider.setValue(*args)
        self.fakeCombo.setStatusTip(self.slider.statusTip())


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

    def setFract(self, fract):
        self.fract = fract
        self.setZValue(-fract * .01)

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

    def mousePressEvent(self, event):
        if not self.selectable:
            return QtWidgets.QGraphicsItem.mousePressEvent(self, event)
        if event.buttons() == QtCore.Qt.RightButton:
            self.path.removeNode(self)

    def mouseMoveEvent(self, event):
        self.scene().notifyPosition(self)
        QtWidgets.QGraphicsItem.mouseMoveEvent(self, event)

    def _shape(self):
        transform, _ = self.scene().view.transform().inverted()
        path = QtGui.QPainterPath()
        rect = QtWidgets.QGraphicsItem.sceneBoundingRect(self).adjusted(-5, -5, 5, 5)
        path.addRect(transform.mapRect(rect))
#        print(rect, path.boundingRect())
        return path

    def contains(self, pos):
        viewTransform = self.scene().view.viewportTransform()
        inverted, _ = viewTransform.inverted()
        transform = self.deviceTransform(viewTransform)
        rect = transform.mapRect(self.sceneBoundingRect())
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
    normalPen = QtGui.QPen(QtGui.QColor(169, 214, 255, 125), 1)
#    normalPen = QtGui.QPen(QtGui.QColor(237, 255, 120, 201), 1)
    normalPen.setCosmetic(True)
    selectPen = QtGui.QPen(QtGui.QColor(64, 192, 216), 1.5)
#    selectPen = QtGui.QPen(QtGui.QColor(255, 116, 255), 1)
    selectPen.setCosmetic(True)
    pens = normalPen, selectPen
    stroker = QtGui.QPainterPathStroker()
    stroker.setWidth(4)

    def __init__(self, slider, envelope):
        QtWidgets.QGraphicsPathItem.__init__(self)
        self.slider = slider
        self.slider.fractChanged.connect(self.setFract)
        self.envelope = envelope
        self.uniqueEnvelope = []
        self.slider.valueChanged[float, float].connect(self.setValue)
        self.nodes = []
        self.closed = False
        self.selectable = False
        self.setPen(self.normalPen)

        self.menu = QtWidgets.QMenu()
        for curve in sorted(curves):
            action = self.menu.addAction(CurveIcon(curve), curves[curve])
            action.setData(curve)

    def setFract(self, fract):
        [n.setFract(fract) for n in self.nodes]
        QtWidgets.QGraphicsPathItem.setZValue(self, -fract * .01)
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
        [n.setZValue(z) for n in self.nodes]

    def addNode(self, node):
        self.nodes.append(node)
        node.setFract(self.slider.fract)

    def removeNode(self, node):
        if len(self.nodes) > 1:
            self.nodes.remove(node)
            self.scene().removeItem(node)
            self.redraw(True)
            self.nodes[0].setSelected(True)

    def getSortedNodes(self):
        return sorted(self.nodes, key=lambda n: n.x())

    def redraw(self, rebuild=False, emit=False):
        if not self.closed:
            return
        self.envelope.clear()
        self.uniqueEnvelope[:] = []
        path = self.path()
        if rebuild:
            path = QtGui.QPainterPath()
            path.lineTo(0, 0)
            count = -1
        else:
            count = path.elementCount()
        for index, node in enumerate(self.getSortedNodes()):
            if index >= count:
                path.lineTo(node.pos())
            else:
                path.setElementPositionAt(index + 1, node.x(), node.y())
            self.envelope[node.x()] = -node.y()
            self.uniqueEnvelope.append((node.x(), -node.y()))
        count = path.elementCount()
        if count == len(self.nodes) + 1:
#            print('chiudo', count, len(self.nodes), node.y())
            path.lineTo(1, node.y())
        else:
            path.setElementPositionAt(count - 1, 1, node.y())
        self.setPath(path)
        if emit:
            self.slider.setValue(emit, False)

    def _contextMenuEvent(self, event):
        if self.selectable and self.contains(event.pos()):
            self.menu.exec_(QtGui.QCursor.pos())
        else:
            QtWidgets.QGraphicsPathItem.contextMenuEvent(self, event)

    def close(self):
        self.closed = True
        path = QtGui.QPainterPath()
        path.moveTo(0, 0)
        for index, node in enumerate(self.getSortedNodes()):
            path.lineTo(node.pos())
        path.lineTo(1, node.y())
        self.setPath(path)
#        path = self.path()
#        path.lineTo(1, self.nodes[-1].y())
#        self.setPath(path)

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
        if not pos:
            self.title = getCardinal(item.fract + 1)
            self.posText = ''
            self._rect = self.baseRect
        else:
            self.title = getCardinal(item.fract + 1)
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
    indexBrush = QtGui.QBrush(QtGui.QColor(QtCore.Qt.lightGray))

    def __init__(self, index, showIndex):
        QtWidgets.QGraphicsItemGroup.__init__(self)
        self.index = index
        self.line = QtWidgets.QGraphicsLineItem(QtCore.QLineF(0, -2, 0, 1))
        self.line.setPen(self.linePen)
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

    def __init__(self, main):
        QtWidgets.QGraphicsScene.__init__(self)
        self.main = main
        self.view = main.envelopeView
        self.setSceneRect(QtCore.QRectF(0, -1, 1., 1.))
        self.waveRatio = .1
        self.waveSnap = False
        self.valueSnap = False

        self.playHead = self.addLine(QtCore.QLineF(0, -2, 0, 1))
        self.playHead.setPen(self.playPen)
        self.playHead.setZValue(-10)

        self.toolTipItem = ToolTipItem()
        self.addItem(self.toolTipItem)
        self.toolTipItem.setPos(-2, 2)

        self.indexItems = []

        self.toolTipTimer = QtCore.QTimer()
        self.toolTipTimer.setInterval(800)
        self.toolTipTimer.setSingleShot(True)
        self.toolTipTimer.timeout.connect(lambda: self.toolTipItem.setVisible(False))

    @property
    def sortedSliders(self):
        return sorted(self.envelopes.keys(), key=lambda s: s.fract)

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

    def movePlayHead(self, pos, ignore=None):
        self.playHead.setX(pos)
        for slider, envelope in self.envelopes.items():
            if slider == ignore:
                continue
            prevX = prevY = 0
            if not pos:
                if envelope.get(0) is not None:
                    slider.setValue(envelope[0], False)
                else:
                    slider.setValue(0, False)
                continue
            for x in sorted(envelope):
                if not pos:
                    slider.setValue(0, False)
                    break
                elif x == pos:
                    slider.setValue(envelope[x], False)
                    break
                elif x < pos:
                    prevX = x
                    prevY = envelope[x]
                else:
                    y = envelope[x]
                    diff = y - prevY
                    ratio = (pos - prevX) / (x - prevX)
                    slider.setValue(prevY + diff * ratio, False)
                    break
            else:
                slider.setValue(envelope[x], False)
#        print(envelope, self.paths[slider].uniqueEnvelope)

    def setWaveSnap(self, waveSnap):
        self.waveSnap = waveSnap

    def setValueSnap(self, valueSnap):
        self.valueSnap = valueSnap

    def getSortedValues(self, slider):
        for x in sorted(self.envelopes[slider]):
            yield x, self.envelopes[slider][x]

    def updatePaths(self):
        existing = [i for i in self.items() if isinstance(i, EnvelopePath)]
        for slider in self.sortedSliders:
            pathItem = self.paths.get(slider)
            if not pathItem:
                pathItem = self.paths[slider] = EnvelopePath(slider, self.envelopes[slider])
                for x, y in self.getSortedValues(slider):
                    node = NodeItem(pathItem)
                    node.setPos(x, -y)
                    self.addItem(node)
                    pathItem.addNode(node)
                pathItem.close()
                self.addItem(pathItem)
                pathItem.setPos(0, 0)
#                pathItem.valueChanged.connect(lambda value, slider=slider: slider.setValue(value, False))
            else:
                if pathItem in existing:
                    existing.remove(pathItem)
            pathItem.setZValue(-slider.fract * .01)
            pathItem.setSelectable(slider.selector.isChecked())
        for pathItem in existing:
            [self.removeItem(n) for n in pathItem.nodes]
            self.removeItem(pathItem)

    def mousePressEvent(self, event):
        if event.buttons() == QtCore.Qt.MiddleButton:
            pos = event.scenePos()
            for item in self.items(pos):
                if isinstance(item, NodeItem) and item.contains(pos):
                    item.path.slider.selector.click()
        QtWidgets.QGraphicsScene.mousePressEvent(self, event)

    def mouseMoveEvent(self, event):
        x = sanitize(0, event.scenePos().x(), 1)
        self.movePlayHead(x, self.main.currentSlider if self.selectedItems() else None)
        self.playHeadMoved.emit(x)
#        print(self.main.currentSlider, event.scenePos())
        QtWidgets.QGraphicsScene.mouseMoveEvent(self, event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            node = NodeItem(self.main.currentPath, True)
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
            self.main.currentPath.redraw()
            node.setSelected(True)
        QtWidgets.QGraphicsScene.mouseDoubleClickEvent(self, event)


class SpecTransformDialog(QtWidgets.QDialog):
    shown = False

    def __init__(self, parent, transform=None):
        QtWidgets.QDialog.__init__(self, parent)
        loadUi('ui/spectralmorph.ui', self)
        self.transform = transform

        self.envelopeScene = EnvelopeScene(self)
        self.envelopeView.setScene(self.envelopeScene)
        self.envelopeScene.envelopes = self.envelopes = {}
        self.envelopeScene.paths = self.paths = {}
        self.envelopeScene.playHeadMoved.connect(self.moveProgressSlider)

        self.selectors = QtWidgets.QButtonGroup()

        self.addBtn.clicked.connect(self.addEnvelope)
        self.deleteBtn.clicked.connect(self.removeEnvelope)
        self.waveSnapChk.toggled.connect(self.envelopeScene.setWaveSnap)
        self.valueSnapChk.toggled.connect(self.envelopeScene.setValueSnap)

        self.sliderModel = QtGui.QStandardItemModel()
        for h, l in enumerate(HarmonicsSlider.names):
            item = QtGui.QStandardItem('{}. {}'.format(h + 1, l))
            item.setData(h)
            self.sliderModel.appendRow(item)
        for h in range(h + 1, 50):
            item = QtGui.QStandardItem('{} harmonic'.format(getCardinal(h + 1)))
            item.setData(h)
            self.sliderModel.appendRow(item)

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

        self.statusbar = QtWidgets.QStatusBar(self)
        self.buttonLayout.insertWidget(0, self.statusbar)

        self.volumeIcon.iconSize = self.playBtn.iconSize()
        self.volumeIcon.setVolume(self.volumeSlider.value())
        self.volumeIcon.step.connect(lambda step: self.volumeSlider.setValue(self.volumeSlider.value() + self.volumeSlider.pageStep() * step))
        self.volumeIcon.reset.connect(self.volumeSlider.reset)
        self.volumeSlider.valueChanged.connect(self.volumeIcon.setVolume)


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
        return sorted(self.envelopes.keys(), key=lambda s: s.fract)

    def movePlayHead(self, value):
        self.envelopeScene.movePlayHead(float(value - self.start) / (self.end - self.start))
        self.toolTipSlider.setValue(value)
#        self.progressSlider.setToolTip(str(value))

    def moveProgressSlider(self, x):
        self.progressSlider.blockSignals(True)
        self.progressSlider.setValue(int(x * (self.end - self.start)) + self.start)
        self.toolTipSlider.setValue(self.progressSlider.value())
#        self.progressSlider.setToolTip(str(self.progressSlider.value()))
#        self.progressSlider.setValue(int(x * 1000))
        self.progressSlider.blockSignals(False)

    def setWaveRange(self, start, end):
        self.start = start
        self.end = end
        self.envelopeScene.setWaveRange(start, end)
        self.progressSlider.blockSignals(True)
        self.progressSlider.setRange(start, end)
        self.progressSlider.setValue(start)
#        self.progressSlider.setToolTip(str(start))
        self.progressSlider.blockSignals(False)
        self.toolTipSlider.setRange(start, end)
        self.toolTipSlider.setValue(start)
        self.startLbl.setNum(start + 1)
        self.endLbl.setNum(end + 1)

    def setCurrentEnvelope(self, btn):
        for slider, path in self.paths.items():
            if slider.selector == btn:
                path.setSelectable(True)
                path.setZValue(10)
            else:
                path.setZValue(-slider.fract * .01)
                path.setSelectable(False)
#            path.setSelectable(slider.selector == btn)

    def removeEnvelope(self):
        if self.sender() == self.deleteBtn:
            slider = self.currentSlider
            if QtWidgets.QMessageBox.question(self, 'Delete envelope', 
                'Delete envelope for {} harmonic?'.format(getCardinal(slider.fract + 1)), 
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
            try:
                self.sortedSliders[slider.fract].selector.click()
            except:
                self.sortedSliders[-1].selector.click()
        slider.deleteLater()
        self.resetFractions()
        self.addBtn.setEnabled(len(self.envelopes) < 50)
        self.deleteBtn.setEnabled(len(self.envelopes) > 1)
#        print([(s.fract, e) for s, e in self.envelopes.items()])

    def resetFractions(self):
        sliders = list(self.sortedSliders)
        fracts = [s.fract for s in sliders]
        for h in range(50):
            self.sliderModel.item(h).setEnabled(h not in fracts)
        for newIndex, slider in enumerate(sliders):
            oldIndex = self.hLayout.indexOf(slider)
            if oldIndex != newIndex:
                self.hLayout.takeAt(oldIndex)
                self.hLayout.insertWidget(newIndex, slider)

    @QtCore.pyqtSlot()
    def addEnvelope(self, fract=None, polarity=1, values=None, update=True):
        fracts = [s.fract for s in self.envelopes]
        if len(fracts) == 50:
            self.addBtn.setEnabled(False)
            return
        if fract is None:
            for fract in range(50):
                if fract not in fracts:
                    break
        slider = SliderContainer(self, fract, polarity)
        self.selectors.addButton(slider.selector)
#        slider.triggered.connect(self.changeFract)
        slider.setModel(self.sliderModel)
        slider.fractChanged.connect(self.resetFractions)
        slider.removeRequested.connect(self.removeEnvelope)
        values = values if values else {0: .5}

#        if not self.envelopes or (fracts and fract > max(fracts)):
#            self.hLayout.addWidget(slider)
#        else:
        self.hLayout.addWidget(slider)

        self.envelopes[slider] = values
        if len(self.envelopes) == 1 or self.sender() == self.addBtn:
            slider.selector.click()
        if values.get(0) is not None:
            slider.setValue(values[0])

        self.sliderModel.item(fract).setEnabled(False)
        self.resetFractions()
        if update:
            self.updatePaths()
        self.deleteBtn.setEnabled(True)

    def event(self, event):
        if event.type() == QtCore.QEvent.StatusTip:
            if self.isVisible():
                self.statusbar.showMessage(event.tip())
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

    def exec_(self, transform=None):
        for i in range(4):
            self.addEnvelope(i, update=False)
        self.setWaveRange(12, 54)
        self.updatePaths()

        self.show()

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

