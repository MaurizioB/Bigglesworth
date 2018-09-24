from itertools import chain
from copy import deepcopy
from collections import namedtuple
from random import randrange
from math import log10
from uuid import uuid4

from Qt import QtCore, QtGui, QtWidgets

import numpy as np

from bigglesworth.utils import setBold, sanitize
from bigglesworth.wavetables.keyframes import KeyFrames
from bigglesworth.wavetables.utils import (pow16, pow19, pow20, pow21, pow22, 
    sineValues, baseSineValues, waveFunction, 
    getCurvePath, getCurveFunc, Envelope)

polyPoints = namedtuple('polyPoints', 'topLeft topRight bottomRight bottomLeft')

class HoverCursor(QtWidgets.QWidget):
    def __init__(self, *args):
        QtWidgets.QWidget.__init__(self)
        self.setWindowFlags(QtCore.Qt.Widget|QtCore.Qt.Tool|QtCore.Qt.FramelessWindowHint|QtCore.Qt.X11BypassWindowManagerHint)
        self.iconCache = {}
        self.stroker = QtGui.QPainterPathStroker()
        self.stroker.setWidth(1.5)
        self.timer = QtCore.QTimer()
        self.timer.setInterval(25)
        self.timer.timeout.connect(self.setPos)
        self.delta = QtCore.QPoint(16, 16)
        self.pixmap = None

    def setCursor(self, iconName=None):
        if iconName is None:
            self.pixmap = None
            return
        data = self.iconCache.get(iconName)
        if data:
            mask, self.pixmap = data
            self.setMask(mask)
        if not data:
            icon = QtGui.QIcon.fromTheme(iconName)
            iconPixmap = icon.pixmap(16)
            region = QtGui.QRegion(iconPixmap.mask())
            path = QtGui.QPainterPath()
            path.addRegion(region)
            strokePath = self.stroker.createStroke(path)
            self.pixmap = QtGui.QPixmap(18, 18)
            self.pixmap.fill(QtCore.Qt.transparent)
            qp = QtGui.QPainter(self.pixmap)
            qp.setPen(QtCore.Qt.NoPen)
            qp.setBrush(QtGui.QColor(QtCore.Qt.white))
            qp.translate(.5, .5)
            qp.drawPath(strokePath)
            qp.drawPixmap(0, 0, iconPixmap)
            qp.end()
            mask = self.pixmap.mask()
            self.setMask(mask)
            self.iconCache[iconName] = mask, self.pixmap

    def setPos(self):
        self.move(QtGui.QCursor.pos() + self.delta)

    def show(self):
        if self.pixmap:
            QtWidgets.QWidget.show(self)
            self.timer.start()

    def hide(self):
        QtWidgets.QWidget.hide(self)
        self.timer.stop()

    def sizeHint(self):
        return QtCore.QSize(32, 32)

    def paintEvent(self, event):
        if self.pixmap:
            qp = QtGui.QPainter(self)
            qp.drawPixmap(0, 0, self.pixmap)


class ChunkItem(QtWidgets.QGraphicsRectItem):
    _rect = QtCore.QRectF(0, 0, 64, 0)

    noPen = QtGui.QPen(QtCore.Qt.NoPen)

    waveBackground = QtGui.QLinearGradient(0, -1, 0, 1)
    waveBackground.setColorAt(0, QtGui.QColor(0, 128, 192, 64))
    waveBackground.setColorAt(.5, QtGui.QColor(0, 128, 192, 192))
    waveBackground.setColorAt(1, QtGui.QColor(0, 128, 192, 64))

    paint = normalPaint = lambda *args: QtWidgets.QGraphicsRectItem.paint(*args)

    def __init__(self, data, index):
        QtWidgets.QGraphicsRectItem.__init__(self)
#        self.setFlags(self.ItemIsSelectable)
        self.data = data
        self.index = index
        self.offset = 0
        self.chunkData = data[index * 128:(index + 1) * 128]
        try:
            self.last = data[(index + 1) * 128]
        except:
            self.last = self.chunkData[-1]
        self.size = len(self.chunkData)
        y = min(0, -max(self.chunkData))
        height = -y - min(0, min(self.chunkData))
        self.setRect(0, y, self.size, height)
#        self.setPen(QtGui.QPen(QtCore.Qt.white))
        self.setPen(self.noPen)
        self.setBrush(self.waveBackground)
        self.setVisible(False)

    def invalidate(self):
        try:
            del self.wavePath
        except:
            pass
        self.chunkData = self.data[self.index * 128 + self.offset:(self.index + 1) * 128 + self.offset]
        try:
            self.last = self.data[(self.index + 1) * 128 + self.offset]
        except:
            self.last = self.chunkData[-1]
        self.size = len(self.chunkData)
        y = min(0, -max(self.chunkData))
        height = -y - min(0, min(self.chunkData))
        self.setRect(0, y, self.size, height)

    def setOffset(self, offset):
        self.offset = offset % 128
        #TODO: non serve?!?
        return
        self.chunkData = self.data[self.index * 128 + self.offset:(self.index + 1) * 128 + self.offset]
        try:
            self.last = self.data[(self.index + 1) * 128 + self.offset]
        except:
            self.last = self.chunkData[-1]
        self.size = len(self.chunkData)
        y = min(0, -max(self.chunkData))
        height = -y - min(0, min(self.chunkData))
        self.setRect(0, y, self.size, height)

    def wavePaint(self, qp, option, widget):
        qp.setPen(self.noPen)
        qp.setBrush(self.waveBackground)
        try:
            qp.drawPath(self.wavePath)
        except:
            self.wavePath = QtGui.QPainterPath()
            for sample, value in enumerate(self.chunkData):
                self.wavePath.lineTo(sample, -value)
            self.wavePath.lineTo(self.size, -self.last)
            self.wavePath.lineTo(self.size, 0)
            self.wavePath.lineTo(0, 0)
            qp.drawPath(self.wavePath)
#        qp.setPen(QtCore.Qt.white)
#        qp.drawRect(self.rect())


class LoadItem(QtWidgets.QGraphicsItem):
    pen = QtGui.QPen(QtCore.Qt.white)
    _rect = QtCore.QRectF()
    text = 'File too big, click here to show preview'

    def __init__(self):
        QtWidgets.QGraphicsItem.__init__(self)
        self.setFlags(self.flags() ^ self.ItemIgnoresTransformations)
        self.font = QtWidgets.QApplication.font()
        self.font.setPointSizeF(22.)
        self.fontMetrics = QtGui.QFontMetricsF(self.font)
#        self._rect = self.fontMetrics.boundingRect(self.text).adjusted(-20, -20, 20, 20)
        self._rect = self.fontMetrics.boundingRect(self.text)
        self._rect.moveCenter(QtCore.QPointF(0, 0))

    def boundingRect(self):
        return self._rect

    def paint(self, qp, option, widget):
        qp.setPen(self.pen)
        qp.drawText(self._rect, QtCore.Qt.AlignCenter, self.text)


class SilentItem(LoadItem):
    text = 'This file is silent'

class InvalidItem(LoadItem):
    text = 'Invalid file'


class NodeItem(QtWidgets.QGraphicsItem):
    _rect = QtCore.QRectF(-3, -3, 6, 6)
    normalPen = QtGui.QPen(QtGui.QColor(237, 255, 120, 201), 1)
    normalPen.setCosmetic(True)
    normalBrush = QtGui.QBrush(QtGui.QColor(237, 255, 120, 64))

    hoverPen = QtGui.QPen(QtGui.QColor(QtCore.Qt.red), 1)
    hoverPen.setCosmetic(True)
    hoverBrush = QtCore.Qt.NoBrush

    invisiblePen = QtCore.Qt.NoPen
    invisibleBrush = QtCore.Qt.NoBrush

    selectPen = QtGui.QPen(QtGui.QColor(255, 116, 255), 1)
    selectPen.setCosmetic(True)
    selectBrush = QtCore.Qt.NoBrush

    pen = invisiblePen
    brush = invisibleBrush

    def __init__(self, sample):
        QtWidgets.QGraphicsItem.__init__(self)
        self.sample = sample
        self.setFlags(self.flags() | self.ItemIgnoresTransformations | self.ItemIsSelectable)
        self.setAcceptsHoverEvents(True)
        self.setZValue(10)

    def boundingRect(self):
        return self._rect

    def hoverEnterEvent(self, event):
        self.pen = self.hoverPen
        self.brush = self.hoverBrush
        self.update()

    def hoverLeaveEvent(self, event):
        if self.isSelected():
            self.pen = self.selectPen
            self.brush = self.selectBrush
        else:
            if self.scene().showNodes:
                self.pen = self.normalPen
                self.brush = self.normalBrush
            else:
                self.pen = self.invisiblePen
                self.brush = self.invisibleBrush
        self.update()

    def mousePressEvent(self, event):
        QtWidgets.QGraphicsItem.mousePressEvent(self, event)

    def mouseMoveEvent(self, event):
        if not self.isUnderMouse():
            self.pen = self.normalPen
            self.brush = self.normalBrush
            self.update()

#    def setInvisible(self, invisible):
#        if invisible:
#            self.pen = self.invisiblePen
#            self.brush = self.invisibleBrush
#            self.setVisible(True)
#            print('invisible (setVisible True)')
#        else:
#            if self.isSelected():
#                self.pen = self.selectPen
#                self.brush = self.selectBrush
#                self.setVisible(True)
#            else:
#                self.pen = self.normalPen
#                self.brush = self.normalBrush
#                self.setVisible(self.scene().showNodes)

    def setVisible(self, visible):
        if self.isSelected():
            self.pen = self.selectPen
            self.brush = self.selectBrush
        elif self.scene().showNodes:
            if self.isUnderMouse():
                self.pen = self.hoverPen
                self.brush = self.hoverBrush
            else:
                self.pen = self.normalPen
                self.brush = self.normalBrush
        else:
            self.pen = self.invisiblePen
            self.brush = self.invisibleBrush
        self.update()

    def itemChange(self, change, value):
        if change == self.ItemSelectedChange:
            if value:
#                print('select')
                self.pen = self.selectPen
                self.brush = self.selectBrush
#                self.setVisible(True)
            else:
                if self.scene().showNodes:
                    self.pen = self.normalPen
                    self.brush = self.normalBrush
                else:
                    self.pen = self.invisiblePen
                    self.brush = self.invisibleBrush
        return QtWidgets.QGraphicsItem.itemChange(self, change, value)

    def paint(self, qp, option, widget):
        qp.setPen(self.pen)
        qp.setBrush(self.brush)
        qp.drawEllipse(self._rect)


class SampleItem(QtWidgets.QGraphicsWidget):
    setIndexRequested = QtCore.pyqtSignal()
    deleteRequested = QtCore.pyqtSignal()
    copyWave = QtCore.pyqtSignal()
    pasteWave = QtCore.pyqtSignal()
    pressed = QtCore.pyqtSignal(bool)
    changed = QtCore.pyqtSignal()
    indexChanged = QtCore.pyqtSignal(int)

#    normalPen = QtGui.QColor(174, 181, 193, 106)
    borderNormalPen = QtGui.QPen(QtGui.QColor(64, 192, 216))
    borderHighlightPen = QtGui.QColor(114, 222, 246)
    borderSelectedPen = QtGui.QColor(134, 242, 255)
    normalBrush = QtGui.QColor(58, 60, 64)
    sampleBackground = QtGui.QColor(32, 32, 32, 120)
    selectedBrush = QtGui.QColor(99, 104, 110)
    wavePen = QtGui.QPen(QtGui.QColor(64, 192, 216))

#    prevTransform = nextTransform = None
    final = False
    minimizedRect = QtCore.QRectF(0, 0, 20, 60)
    minimizedShape = QtGui.QPainterPath()
    minimizedShape.addRect(minimizedRect.adjusted(-2, 0, 2, 0))
    minimizedSize = minimizedRect.size()
    hoverRect = QtCore.QRectF(-20, 0, 60, 60)
    normalRect = QtCore.QRectF(0, 0, 80, 60)
    normalShape = QtGui.QPainterPath()
    normalShape.addRect(normalRect.adjusted(-2, 0, 2, 0))
    normalSize = normalRect.size()

#    baseSineValues = []
    sinePreviewWavePath = QtGui.QPainterPath()
    sineWavePath = QtGui.QPainterPath()
    for p, sine in enumerate(sineValues(1)):
        sinePreviewWavePath.lineTo(p, -sine*16)
        _value = int(sine*pow19)
#        baseSineValues.append(_value)
        sineWavePath.lineTo(p*16384, -_value)
#    sinePreviewWavePath.translate(0, 32)
    sineWavePath.translate(0, pow20)
#    previewPath = sinePreviewWavePath

    previewPathMaxWidth = sinePreviewWavePath.boundingRect().width()
    previewPathMaxHeight = sinePreviewWavePath.boundingRect().height() * 2
    wavePathMaxHeight = sineWavePath.boundingRect().height() * 2
    wavePathMaxWidth = sineWavePath.boundingRect().width()

    def __init__(self, keyFrames, uuid=None):
        QtWidgets.QGraphicsWidget.__init__(self)
        self.keyFrames = keyFrames
        self.uuid = uuid if uuid is not None else uuid4()
        self.setAcceptsHoverEvents(True)
        self.setFlags(self.flags() | self.ItemIsSelectable)

        self.wavePath = QtGui.QPainterPath(self.sineWavePath)
        self.previewPath = QtGui.QPainterPath(self.sinePreviewWavePath)
#        if self.values != baseSineValues:
#            for sample, value in enumerate(self.values):
#                self.previewPath.setElementPositionAt(sample, sample, -value/32768)
#                self.wavePath.setElementPositionAt(sample, self.wavePath.elementAt(sample).x, pow20 - value)
        self._rect = self.minimizedRect
        self._shape = self.minimizedShape
        self._size = self.minimizedSize
        font = QtWidgets.QApplication.font()
        font.setPointSizeF(font.pointSizeF() * .88)
        self.setFont(font)
        self.fontMetrics = QtGui.QFontMetrics(font)
        self.fontHeight = self.fontMetrics.height()
        self.keepMaximized = False
        self.highlighted = False

        self.changed.connect(self.update)

        setIndexAction = QtWidgets.QAction(QtGui.QIcon.fromTheme('document-swap'), 'Change position', self)
        setIndexAction.triggered.connect(self.setIndexRequested)
        copyAction = QtWidgets.QAction(QtGui.QIcon.fromTheme('edit-copy'), 'Copy wave values', self)
        copyAction.triggered.connect(self.copyWave)
        self.pasteAction = QtWidgets.QAction(QtGui.QIcon.fromTheme('edit-paste'), 'Paste wave values', self)
        self.pasteAction.triggered.connect(self.pasteWave)
        removeAction = QtWidgets.QAction(QtGui.QIcon.fromTheme('edit-delete'), 'Remove wave', self)
        removeAction.triggered.connect(self.deleteRequested)

        self.addActions([setIndexAction, copyAction, self.pasteAction, removeAction])

    @property
    def index(self):
        return self.keyFrames.index(self)

    @property
    def values(self):
        return self.keyFrames.values(self)

    @property
    def external(self):
        return self.keyFrames.isExternal(self)

    @property
    def prevTransform(self):
        return self.keyFrames.prevTransform(self)

    @property
    def nextTransform(self):
        return self.keyFrames.nextTransform(self)

    def setFirst(self, isFirst):
        if isFirst:
            self._rect = self.normalRect
            self._shape = self.normalShape
            self._size = self.normalSize
        else:
            self._rect = self.minimizedRect
            self._shape = self.minimizedShape
            self._size = self.minimizedSize
        self.updateGeometry()

    def actions(self):
        self.pasteAction.setEnabled(QtWidgets.QApplication.clipboard().mimeData().hasFormat('bigglesworth/WaveValues'))
        return QtWidgets.QGraphicsWidget.actions(self)

    def setHighlighted(self, highlighted):
        self.highlighted = highlighted
        self.update()

    def setMaximized(self, maximized):
        if self.index:
            self.prepareGeometryChange()
            if maximized:
                self.maximize()
            else:
                self.minimize()
#        if self.index in (0, 63):
#            return
#        self.keepMaximized = maximized
#        self._rect = self.normalRect if maximized else self.minimizedRect
#        self._shape = self.normalShape if maximized else self.minimizedShape
        self.updateGeometry()

    def setValue(self, sample, value):
        self.keyFrames.setValue(self.index, sample, value)

    def setWaveValue(self, sample, value):
        self.previewPath.setElementPositionAt(sample, sample, -value/32768)
        self.wavePath.setElementPositionAt(sample, self.wavePath.elementAt(sample).x, pow20 - value)
        self.changed.emit()

    def setValues(self, data):
        self.keyFrames.setValues(self.index, data)

    def setWaveValues(self, data):
        for sample, value in data:
            self.previewPath.setElementPositionAt(sample, sample, -value/32768)
            self.wavePath.setElementPositionAt(sample, self.wavePath.elementAt(sample).x, pow20 - value)
        self.changed.emit()

    def itemChange(self, change, value):
        if change == self.ItemSceneChange:
            if value:
                value.keyFrameAdded(self)
        return QtWidgets.QGraphicsWidget.itemChange(self, change, value)

    def mousePressEvent(self, event):
        self.pressed.emit(False)
        QtWidgets.QGraphicsWidget.mousePressEvent(self, event)

    def mouseDoubleClickEvent(self, event):
        self.pressed.emit(True)
        QtWidgets.QGraphicsWidget.mouseDoubleClickEvent(self, event)

    def setFinal(self, final):
        self.final = final
        if final:
            self._rect = self.normalRect
            self._shape = self.normalShape
##        elif not self.scene().maximized:
###            self.keepMaximized = False
##            self._rect = self.minimizedRect
##            self._shape = self.minimizedShape
##            self.updateGeometry()

    def hoverEnterEvent(self, event):
        if self.index and not self.scene().maximized and not self.scene().hoverMode:
            self._rect = self.hoverRect
            self.prepareGeometryChange()
            self.setZValue(1)

    def hoverLeaveEvent(self, event):
        if self.index and not self.scene().maximized and not self.scene().hoverMode:
            self.prepareGeometryChange()
            self.minimize()
        self.setZValue(0)

    def maximize(self):
        if self.index:
            self._rect = self.normalRect
            self._shape = self.normalShape
            self._size = self.normalSize
            self.updateGeometry()

    def minimize(self):
        if self.index:
            self._rect = self.minimizedRect
            self._shape = self.minimizedShape
            self._size = self.minimizedSize
            self.updateGeometry()

    def sizeHint(self, *args):
#        return self._rect.size() if self.index else self.normalRect.size()
        return self._size

    def boundingRect(self):
        return self._rect.adjusted(-2, 0, 2, 0) if self.index and not self.scene().maximized and not self.scene().hoverMode else self.normalRect

    def shape(self):
        return self._shape

    def paint(self, qp, option=None, widget=None, hoverRect=False):
#        qp.setPen(QtGui.QPen(QtCore.Qt.red, 2, QtCore.Qt.DotLine))
        rect = hoverRect if hoverRect else self._rect
        qp.save()
        qp.save()
        if self.highlighted:
            qp.setPen(self.borderHighlightPen)
            qp.setBrush(self.selectedBrush)
        elif self.isSelected():
            qp.setPen(self.borderSelectedPen)
            qp.setBrush(self.selectedBrush)
        else:
            qp.setPen(self.borderNormalPen)
            qp.setBrush(self.normalBrush)
        qp.drawRect(rect)
        qp.restore()
        sampleRect = rect.adjusted(1, 1, -1, - self.fontHeight - 2)
        qp.setBrush(self.sampleBackground)
        qp.drawRect(sampleRect)
        qp.setBrush(QtCore.Qt.NoBrush)
        indexRect = rect.adjusted(1, sampleRect.height() + 1, -1, -1)
        qp.setFont(self.font())
        qp.setPen(QtCore.Qt.white)
        index = self.index
        if index:
            if index == 63:
                text = 'END'
            else:
                text = str(index + 1)
        else:
            text = 'START'
        qp.drawText(indexRect, QtCore.Qt.AlignCenter, text)
        hRatio = (rect.width() - 2) / self.previewPath.boundingRect().width()
        vRatio = (sampleRect.height() - 2) / self.previewPathMaxHeight
        qp.translate(1, sampleRect.center().y())
        qp.scale(hRatio, vRatio)
        qp.save()
        try:
            qp.translate(rect.left() / hRatio, 0)
        except:
            pass
        qp.setPen(self.wavePen)
        qp.drawPath(self.previewPath)
        qp.restore()
        qp.restore()




class WaveTransformItem(QtWidgets.QGraphicsWidget):
    deleteRequested = QtCore.pyqtSignal()
    copyTransform = QtCore.pyqtSignal()
    pasteTransform = QtCore.pyqtSignal()
    bounceRequested = QtCore.pyqtSignal(object)
    changed = QtCore.pyqtSignal()
    pressed = QtCore.pyqtSignal(bool)

#    noneRect = QtCore.QRectF(0, 0, 5, 60)
    noneRect = QtCore.QRectF(0, 0, 0, 60)
    _rect = minimizedRect = QtCore.QRectF(0, 0, 20, 60)
    hoverRect = QtCore.QRectF(-20, 0, 60, 60)
    normalRect = QtCore.QRectF(0, 0, 80, 60)
    _size = minimizedSize = minimizedRect.size()
    normalSize = normalRect.size()

    borderNormalPen = QtGui.QPen(QtGui.QColor(77, 96, 108), .5)
    pathPen = QtGui.QPen(QtGui.QColor(200, 212, 200))
    normalBrush = QtGui.QColor(58, 60, 64)
    invalidPen = QtGui.QColor(QtCore.Qt.red)
    invalidBrush = QtGui.QColor(96, 0, 0)

    Const, CurveMorph, TransMorph, SpecMorph = range(4)

    modeNames = {
        Const: 'Constant', 
        CurveMorph: 'Curve', 
        TransMorph: 'Translate', 
        SpecMorph: 'Spectral', 
    }

    modeLabels = {
        Const: 'CONST', 
        CurveMorph: 'CURVE\nMORPH', 
        TransMorph: 'TRANSL\nMORPH', 
        SpecMorph: 'SPECTRAL\nMORPH'
    }

    modeIcons = {
        Const: 'arrow-right-double', 
        CurveMorph: 'labplot-xy-curve-segments', 
        TransMorph: 'kdenlive-object-width', 
        SpecMorph: 'pathshape', 
    }

    normalTransformPath = QtGui.QPainterPath()
    minimizedTransformPath = QtGui.QPainterPath()
    silentWave = np.array([0] * 128, dtype='float64')

    def __init__(self, keyFrames, mode=0, prevItem=None, nextItem=None, data=None):
        QtWidgets.QGraphicsWidget.__init__(self)
        self.keyFrames = keyFrames
        self.keyFrames.changed.connect(self.setDirty)
        self.setAcceptsHoverEvents(True)
        font = QtWidgets.QApplication.font()
        font.setPointSizeF(font.pointSizeF() * .88)
        self.setFont(font)
        self.fontMetrics = QtGui.QFontMetrics(font)
        self.fontHeight = self.fontMetrics.height()
        self.deltaY = self.fontHeight * .5
        self.keepMaximized = False
        self.minimized = True

        self.prevItem = prevItem
        if prevItem is not None:
            prevItem.changed.connect(self.targetChanged)
            prevItem.indexChanged.connect(self.indexChanged)
            try:
                self.prevWaveIndex = prevItem.index
            except:
                self.prevWaveIndex = None
        else:
            self.prevWaveIndex = None

        if nextItem is not None and nextItem != prevItem:
#            nextItem.prevTransform = self
            nextItem.changed.connect(self.targetChanged)
            nextItem.indexChanged.connect(self.indexChanged)
        else:
            nextItem = prevItem
        self._rect = self.minimizedRect
        self.nextItem = nextItem

        self.mode = mode
        self.data = {}
        if data:
            self.setData(data)

        self.computePaths()

        constAction = QtWidgets.QAction(QtGui.QIcon.fromTheme(self.modeIcons[self.Const]), 'Constant', self)
        constAction.setData(self.Const)
        constAction.triggered.connect(lambda: self.setMode(self.Const))
        curveMorphAction = QtWidgets.QAction(QtGui.QIcon.fromTheme(self.modeIcons[self.CurveMorph]), 'Curve morph', self)
        curveMorphAction.setData(self.CurveMorph)
        curveMorphAction.triggered.connect(lambda: self.setMode(self.CurveMorph))
        transMorphAction = QtWidgets.QAction(QtGui.QIcon.fromTheme(self.modeIcons[self.TransMorph]), 'Translate morph', self)
        transMorphAction.setData(self.TransMorph)
        transMorphAction.triggered.connect(lambda: self.setMode(self.TransMorph))
        specMorphAction = QtWidgets.QAction(QtGui.QIcon.fromTheme(self.modeIcons[self.SpecMorph]), 'Spectral morph', self)
        specMorphAction.setData(self.SpecMorph)
        specMorphAction.triggered.connect(lambda: self.setMode(self.SpecMorph))
        self.morphActions = [constAction, curveMorphAction, transMorphAction, specMorphAction]

        sep = QtWidgets.QAction(self)
        sep.setSeparator(True)
        copyAction = QtWidgets.QAction(QtGui.QIcon.fromTheme('edit-copy'), 'Copy transformation', self)
        copyAction.triggered.connect(self.copyTransform)
        self.pasteAction = QtWidgets.QAction(QtGui.QIcon.fromTheme('edit-paste'), 'Paste transformation', self)
        self.pasteAction.triggered.connect(self.pasteTransform)
        self.bounceAction = QtWidgets.QAction(QtGui.QIcon.fromTheme('timeline-insert'), 'Create intermediate waves', self)
        self.bounceAction.triggered.connect(lambda: self.bounceRequested.emit(self))
        self.allActions = self.morphActions + [sep, copyAction, self.pasteAction, self.bounceAction]

        self.deleteAction = QtWidgets.QAction(QtGui.QIcon.fromTheme('edit-delete'), 'Remove', self)
        self.deleteAction.triggered.connect(self.deleteRequested)

        self.setDirty()

    def setDirty(self):
        self.cache = None
        self.pathCache = {}

    def isLinear(self):
        if not self.mode:
            return True
        elif self.mode == self.CurveMorph and not self.curve:
            return True
        elif self.mode == self.TransMorph and not self.translate:
            return True
        elif self.mode == self.SpecMorph:
            for data in self.harmonics.values():
                for pos, value in data[0]:
                    if value > 0:
                        return False
            return True
        return False

    @property
    def curve(self):
        if not self.mode:
            return 0
        try:
            return self.data['curve']
        except:
            self.data['curve'] = QtCore.QEasingCurve.Linear
            return QtCore.QEasingCurve.Linear

    @property
    def translate(self):
        if not self.mode:
            return 0
        try:
            return self.data['translate']
        except:
            self.data['translate'] = 0
            return 0

    @property
    def harmonics(self):
        if not self.mode:
            return {1: ([(0, 0)], )}
        try:
            return self.data['harmonics']
        except:
            #data format is ([(x, y), ], {node:curve}])
            self.data['harmonics'] = {1: ([(0, 0)], )}
            return self.data['harmonics']

    @property
    def harmonicsOverride(self):
        if not self.mode:
            return False
        return self.data.get('harmonicsOverride', False)

    def clone(self, prevItem, nextItem=None):
        return WaveTransformItem(self.keyFrames, self.mode, prevItem, nextItem)

    def setData(self, data):
        self.data.update(deepcopy(data))
        self.computePaths()
        self.setDirty()
        if data:
            self.changed.emit()
        try:
            self.update()
        except:
            pass

    def isValid(self):
        try:
            return isinstance(self.prevItem, SampleItem) and isinstance(self.nextItem, SampleItem)
        except Exception as e:
            print(self, 'isValid exception', e)
            return False

    def isContiguous(self):
        try:
            return self.prevItem.index == 63 or self.nextItem.index == self.prevItem.index + 1
        except:
            print('isContiguous exception?')
            return False

    def setPrevItem(self, prevItem):
        self.setDirty()
        if isinstance(self.prevItem, SampleItem) and self.prevItem != self.nextItem:
            try:
                self.prevItem.changed.disconnect(self.targetChanged)
                self.prevItem.indexChanged.disconnect(self.indexChanged)
            except:
                print('setPrev disconnect ignored')
        if isinstance(prevItem, SampleItem):
            prevItem.changed.connect(self.targetChanged)
            prevItem.indexChanged.connect(self.indexChanged)
            self.prevWaveIndex = prevItem.index
#            prevItem.nextTransform = self
        self.prevItem = prevItem
        if self.prevItem and self.nextItem:
            self.updateGeometry()
        self.computePaths()

    def setNextItem(self, nextItem):
        self.setDirty()
        if isinstance(self.nextItem, SampleItem) and self.nextItem != self.prevItem:
            try:
                self.nextItem.changed.disconnect(self.targetChanged)
                self.nextItem.indexChanged.disconnect(self.indexChanged)
            except:
                print('setNext disconnect ignored')
        if isinstance(nextItem, SampleItem) and nextItem != self.prevItem:
            nextItem.changed.connect(self.targetChanged)
            nextItem.indexChanged.connect(self.indexChanged)
        self.nextItem = nextItem
        if self.prevItem and self.nextItem:
            self.updateGeometry()
        self.computePaths()

    def setTargets(self, prevItem, nextItem):
        if isinstance(self.prevItem, SampleItem):
            self.prevItem.changed.disconnect(self.targetChanged)
            self.prevItem.indexChanged.disconnect(self.indexChanged)
        if isinstance(self.nextItem, SampleItem) and self.nextItem != self.prevItem:
            self.nextItem.changed.disconnect(self.targetChanged)
            self.nextItem.indexChanged.disconnect(self.indexChanged)

        self.prevItem = prevItem
        if isinstance(prevItem, SampleItem):
            prevItem.changed.connect(self.targetChanged)
            prevItem.indexChanged.connect(self.indexChanged)
            self.prevWaveIndex = nextItem.index

        self.nextItem = nextItem
        if isinstance(nextItem, SampleItem) and nextItem != prevItem:
            nextItem.changed.connect(self.targetChanged)
            nextItem.indexChanged.connect(self.indexChanged)

        if self.prevItem and self.nextItem:
            self.updateGeometry()
        self.computePaths()
        self.updateGeometry()
        self.setDirty()

    def indexChanged(self):
#        if self.isContiguous():
#            self.setAcceptsHoverEvents(False)
#            self._rect = self.noneRect
#        else:
#            self.setAcceptsHoverEvents(True)
#            self._rect = self.minimizedRect if self.minimized else self.normalRect
        self.updateGeometry()
        self.setDirty()

    def targetChanged(self):
        self.setDirty()
        self.computePaths()
        self.changed.emit()
        self.update()

    def getParameters(self):
        values = [self.mode]
        if not self.mode:
            pass
        return values

    def setParameters(self, values):
        self.mode = values[0]
        self.setMode(self.mode)

    def actions(self):
        if not self.isValid():
            return [self.deleteAction]
        for action in self.morphActions:
            setBold(action, action.data() == self.mode)
        self.pasteAction.setEnabled(QtWidgets.QApplication.clipboard().mimeData().hasFormat('bigglesworth/TransformParameters'))
        return self.allActions

    def setMaximized(self, maximized):
#        self.keepMaximized = maximized
#        self._rect = self.normalRect if maximized else self.minimizedRect
        self.minimized = not maximized
        if maximized:
            self.maximize()
        else:
            self.minimize()
        self.updateGeometry()

    def getIntermediatePaths(self, index):
        if self.cache:
            try:
                return self.pathCache[index]
            except:
                pass
#        harmonicArray = self.getHarmonicsArray()[index]
        start = self.prevItem.index
        end = self.nextItem.index
        if not end:
            end = 64
        if self.mode == self.CurveMorph:
            firstValues = np.array(self.prevItem.values)
            lastValues = np.array(self.nextItem.values)
            ratio = 1. / (end - start)
            percent = self.curveFunction((index - start) * ratio)
            values = (1 - percent) * firstValues + percent * lastValues
        elif self.mode == self.TransMorph:
            firstValues = np.array(self.prevItem.values)
            lastValues = np.roll(np.array(self.nextItem.values), -self.translate)
            ratio = 1. / (end - start)
            percent = (index - start) * ratio
            values = np.roll((1 - percent) * firstValues + percent * lastValues, int(self.translate * percent))
        elif self.mode == self.SpecMorph:
            firstValues = np.array(self.prevItem.values)
            lastValues = np.array(self.nextItem.values)
            ratio = 1. / (end - start)
            percent = (index - start) * ratio
            values = (1 - percent) * firstValues + percent * lastValues
            np.clip(np.add(values, self.getHarmonicsArray()[index - start]), -pow20, pow20, out=values)
        path = QtGui.QPainterPath()
        path.moveTo(0, pow20 - values[0])
        for x, value in zip(range(0, pow21, 16384), values):
            path.lineTo(x, pow20 - value)
        self.pathCache[index] = path
        return path

    def computePaths(self):
        if not self.isValid():
            return
        if self.mode:
            self.normalTransformPath = QtGui.QPainterPath()
            self.minimizedTransformPath = QtGui.QPainterPath()
#            x = self.prevItem.previewPath.boundingRect().width() * .5
#            y = self.prevItem.previewPath.boundingRect().height()
            x = self.prevItem.previewPathMaxWidth * .5
            y = self.prevItem.previewPathMaxHeight
            self.normalTransformPath.addPath(self.prevItem.previewPath.translated(-x, -y * .4))
            self.normalTransformPath.addPath(self.nextItem.previewPath.translated(-x, y * .6))
            self.minimizedTransformPath.addPath(self.prevItem.previewPath.translated(-x, -y * 2))
            self.minimizedTransformPath.addPath(self.nextItem.previewPath.translated(-x, y * 2))
            if self.mode == self.CurveMorph:
                if self.curve:
                    self.minimizedTransformPath.addPath(getCurvePath(self.curve, int(y)).translated(-x * .5, -y * .5))
                else:
                    self.minimizedTransformPath.moveTo(0, -y)
                    self.minimizedTransformPath.lineTo(0, y)
            elif self.mode == self.SpecMorph:
                self.minimizedTransformPath.moveTo(-x * .7, y * .5)
                self.minimizedTransformPath.lineTo(-x * .3, -y * .5)
                self.minimizedTransformPath.lineTo(0, -y * .1)
                self.minimizedTransformPath.lineTo(x * .5, -y * .1)
                self.minimizedTransformPath.lineTo(x * .7, y * .5)
            else:
                self.minimizedTransformPath.moveTo(-x * .3, -y)
                self.minimizedTransformPath.lineTo(-x * .7, y)
                self.minimizedTransformPath.moveTo(x * .7, -y)
                self.minimizedTransformPath.lineTo(x * .3, y)

    def setMode(self, mode):
        if mode is None:
            return
        self.mode = mode
        if self.mode == self.CurveMorph and self.data.get('curve') is None:
            self.data['curve'] = QtCore.QEasingCurve.Linear
        if self.mode == self.TransMorph and self.data.get('translate') is None:
            self.data['translate'] = 0
        if self.mode == self.SpecMorph and not self.data.get('harmonics'):
            self.data['harmonics'] = {1: ([(0, 0)], )}
        self.setDirty()
        self.computePaths()
        self.update()
        self.changed.emit()

    @property
    def curveFunction(self):
        return QtCore.QEasingCurve(self.curve).valueForProgress

    def getHarmonicsArray(self):
        start = self.prevItem.index
        end = self.nextItem.index
        if end == 0:
            end = 64
        arrays = []
        indexRange = end - start
        if self.cache and len(self.cache) == indexRange:
            return self.cache
        posRatio = 1. / indexRange
        for index in range(indexRange):
            pos = index * posRatio
            values = np.copy(self.silentWave)
            for harmonic, envData in self.harmonics.items():
                envelope = Envelope(*envData)
                prevX = prevY = 0
                if not pos:
                    value = envelope[0]
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
                        value = envelope[x]
                np.add(values, np.multiply(waveFunction[abs(harmonic) >> 7](abs(harmonic & 127), 128), value * pow20), out=values)
            arrays.append(values)
        self.cache = arrays
        return arrays

#    def valuesAt(self, index):
#        if not self.isValid():
#            return baseSineValues
#        if self.mode == self.Const:
#            return self.prevItem.values
#        elif self.mode == self.CurveMorph:
#            pos = (index - self.prevItem.index) / float(self.nextItem.index - self.prevItem.index)
#            values = []
#            for sample in range(128):
#                start = self.prevItem.values[sample]
#                end = self.nextItem.values[sample]
#                res = start + (end - start) * pos
#                values.append(res)
##                print(start, end, res)
#            print(self.prevItem.index, index, self.nextItem.index, pos, values[-1])
#            return values
#        elif self.mode == self.TransMorph:
#            return self.nextItem.values

    @property
    def modeLabel(self):
        return self.modeLabels[self.mode]

    def hoverEnterEvent(self, event):
        if not self.scene().maximized and not self.scene().hoverMode:
            self._rect = self.hoverRect
            self.prepareGeometryChange()
            self.setZValue(1)

    def hoverLeaveEvent(self, event):
        if not self.scene().maximized and not self.scene().hoverMode:
            self.prepareGeometryChange()
            self.minimize()
        self.setZValue(0)

    def maximize(self):
        self._rect = self.normalRect
        self._size = self.normalSize
        self.updateGeometry()

    def minimize(self):
        self._rect = self.minimizedRect
        self._size = self.minimizedSize
        self.updateGeometry()

    def sizeHint(self, *args):
#        if self.prevItem:
#            print(self.prevItem.index, self.isValid(), self.isContiguous())
        return self.noneRect.size() if self.isValid() and self.isContiguous() else self._size

    def boundingRect(self):
        return self.noneRect if self.isValid() and self.isContiguous() else self._rect

    def itemChange(self, change, value):
        if change == self.ItemSceneChange:
            if value:
                value.transformAdded(self)
        return QtWidgets.QGraphicsWidget.itemChange(self, change, value)

    def mouseDoubleClickEvent(self, event):
        self.pressed.emit(True)
        QtWidgets.QGraphicsWidget.mouseDoubleClickEvent(self, event)

    def paint(self, qp, option, widget, hoverRect=False):
        if self.isValid() and self.isContiguous():
            return

        rect = hoverRect if hoverRect else self._rect

        if not self.isValid() and self.nextItem is not None:
            qp.setPen(self.invalidPen)
            qp.setBrush(self.invalidBrush)
            qp.drawRect(rect)
        else:
            #TODO: full paint necessario post rimozione di SampleItem, quindi disegna comunque
            qp.setPen(self.borderNormalPen)
            qp.setBrush(self.normalBrush)
            qp.drawRect(rect.adjusted(0, -1, 0, 1))
            qp.setPen(QtCore.Qt.white)
        y = rect.center().y() - self.deltaY
        right = rect.width() - 2
#        qp.translate(rect.left(), 0)
        qp.save()
        if not self.mode:
            qp.translate(rect.left(), 0)
            qp.drawLine(1, y, right, y)
            normY = rect.height() * .2
            qp.drawLine(right, y - normY, right, y + normY)
        else:
#            qp.save()
            qp.setPen(self.pathPen)
            qp.setBrush(QtCore.Qt.NoBrush)
            if rect == self.minimizedRect:
                qp.translate(rect.center().x(), rect.center().y() - self.deltaY)
                ratio = (right / self.normalTransformPath.boundingRect().width())
                qp.scale(ratio, ratio)
                qp.drawPath(self.minimizedTransformPath)
            else:
                qp.translate(rect.center().x(), rect.center().y() * .5)
#                ratio = (y - self.deltaY) / self.normalTransformPath.boundingRect().height()
                ratio = (y - self.deltaY) / SampleItem.previewPathMaxHeight * .8
                qp.scale(ratio, ratio)
#                qp.translate(rect.left() * ratio, 0)
                qp.drawPath(self.normalTransformPath)
        qp.restore()
        if rect != self.minimizedRect:
            qp.drawText(rect.adjusted(1, 0, -1, 0), QtCore.Qt.AlignHCenter|QtCore.Qt.AlignBottom, self.modeLabel)
        elif self.mode:
            qp.drawText(rect.adjusted(1, 0, -1, 0), QtCore.Qt.AlignHCenter|QtCore.Qt.AlignBottom, self.modeLabel[0])


class KeyFrameContainer(QtWidgets.QGraphicsWidget):
    placeHolderBrush = QtGui.QColor(220, 220, 220, 192)

    def __init__(self):
        QtWidgets.QGraphicsWidget.__init__(self)
        layout = QtWidgets.QGraphicsLinearLayout()
        self.setLayout(layout)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(0)
        self.keyFrames = KeyFrames(self)
        self.placeHolder = None

    @property
    def allVisibleItems(self):
        items = []
        try:
            for i in range(self.layout().count()):
                item = self.layout().itemAt(i)
                if isinstance(item, WaveTransformItem) and item.isValid() and item.isContiguous():
                    continue
                items.append(item)
        except Exception as e:
            print(e)
        return items

    def itemAt(self, pos):
        for i in range(self.layout().count()):
            item = self.layout().itemAt(i)
            if pos in item.geometry():
                return item
        return None

    def insertPlaceHolder(self, index):
        index -= 1
        for i in range(self.layout().count()):
            self.layout().setItemSpacing(i, 6 if index == i else 0)
        self.placeHolder = index

    def setPlaceHolder(self, index):
        self.placeHolder = index
        for i in range(self.layout().count()):
            self.layout().setItemSpacing(i, 0)

    def removePlaceHolders(self):
        for i in range(self.layout().count()):
            self.layout().setItemSpacing(i, 0)
        self.placeHolder = None

    def moveKeyFrames(self, items, targetPos, dropPos):
        print('move', items)
#        if len(indexes) == 1:
#            self.layout().removeItem()
#        taken = []
#        
#        layoutIndexes = iter(reversed(range(self.layout().count())))
#        while True:
#            try:
#                index = layoutIndexes.next()
#                item = self.layout().itemAt(index)
#                if isinstance(item, SampleItem):
#                    if item.index in indexes:
#                        taken.append(item)
#                        self.layout().removeItem(item)
#                        transformItem = self.layout().itemAt(layoutIndexes.next())
#                        if transformItem.mode:
#                            taken.append(transformItem)
#                        self.layout().removeItem(transformItem)
#                        self.scene().removeItem(transformItem)
#            except:
#                break
#        if min(indexes) < targetPos:
##            targetPos += 1 - len(indexes) * 2
##        else:
##            print('targetPos', targetPos, len(indexes))
#            targetPos += 1 - len(indexes) * 2
#        for item in taken:
#            self.layout().insertItem(targetPos, item)
#        self.checkIndexes()
#
#    def copyKeyFrames(self, indexes, targetPos, dropPos):
#        print('copying', indexes, 'to', targetPos, dropPos)
#
#    def checkIndexes(self):
#        keyIndex = 0
#        self.keyFrames = []
#        for index in range(self.layout().count()):
#            item = self.layout().itemAt(index)
#            if not isinstance(item, SampleItem):
#                continue
#            self.keyFrames.append(item)
#            item.setFinal(False)
#            if keyIndex == 0 and item.index > 0:
#                item.setIndex(keyIndex)
#            elif item.index > keyIndex:
#                keyIndex = item.index
#            elif item.index < keyIndex:
#                item.setIndex(keyIndex)
#            keyIndex += 1
#        self.keyFrames[-1].setFinal(True)

    def setMaximized(self, maximized):
        for item in self.allVisibleItems:
            item.setMaximized(maximized)
        self.scene().update(self.scene().sceneRect())

    def paint(self, qp, option, widget):
        if self.placeHolder is not None:
            qp.setBrush(self.placeHolderBrush)
            qp.setPen(QtCore.Qt.NoPen)
            for i in range(self.layout().count()):
                spacing = self.layout().itemSpacing(i)
                if spacing:
                    rect = self.layout().itemAt(i + 1).geometry()
                    rect.setWidth(spacing)
                    rect.moveLeft(rect.left() - spacing)
                    qp.drawRect(rect)
                    break
            else:
                try:
                    qp.drawRect(self.layout().itemAt(self.placeHolder).geometry())
                except:
                    print('wrong placeHolder?', self.placeHolder)


class KeyFrameScene(QtWidgets.QGraphicsScene):
    deleteRequested = QtCore.pyqtSignal(object)
    mergeRequested = QtCore.pyqtSignal(object)
    bounceRequested = QtCore.pyqtSignal(object)
    pasteTransformRequested = QtCore.pyqtSignal(object, object)
    createKeyFrameRequested = QtCore.pyqtSignal(int, object, bool)
    externalDrop = QtCore.pyqtSignal(object, object, object)
    waveDrop = QtCore.pyqtSignal(object, object, object)
    setIndexRequested = QtCore.pyqtSignal(object)
    highlight = QtCore.pyqtSignal(object, bool)
    transformSelected = QtCore.pyqtSignal(object, bool)
    changed = QtCore.pyqtSignal()

    BeforeItem, OnItem, AfterItem = -1, 0, 1

    def __init__(self, view):
        QtWidgets.QGraphicsScene.__init__(self)
        self.keyFrameContainer = KeyFrameContainer()
        self.keyFrames = self.keyFrameContainer.keyFrames
        self.keyFrames.changed.connect(self.clearSelection)
        self.view = view
        self.changed.connect(lambda: self.view.viewport().update())
        self.addItem(self.keyFrameContainer)
        self.currentDropIndex = None
        self.currentDropPos = self.OnItem
        self.currentSelection = None
        self.maximized = False
        self.hoverMode = True

    def keyFrameAdded(self, keyFrame):
        keyFrame.deleteRequested.connect(lambda: self.deleteRequested.emit(keyFrame))
        keyFrame.setIndexRequested.connect(lambda: self.setIndexRequested.emit(keyFrame))
        keyFrame.pressed.connect(lambda doubleClicked: self.highlight.emit(keyFrame, doubleClicked))
        keyFrame.copyWave.connect(self.copyWave)
        keyFrame.pasteWave.connect(self.pasteWave)
#        self.changed.emit()

    def copyWave(self):
        mimeData = QtCore.QMimeData()
        byteArray = QtCore.QByteArray()
        stream = QtCore.QDataStream(byteArray, QtCore.QIODevice.WriteOnly)
        stream.writeQVariant(self.sender().values)
        mimeData.setData('bigglesworth/WaveValues', byteArray)
        QtWidgets.QApplication.clipboard().setMimeData(mimeData)

    def pasteWave(self):
        mimeData = QtWidgets.QApplication.clipboard().mimeData()
        if mimeData.hasFormat('bigglesworth/WaveValues'):
            byteArray = mimeData.data('bigglesworth/WaveValues')
            stream = QtCore.QDataStream(byteArray)
            self.sender().setValues(stream.readQVariant())
#        self.changed.emit()

    def transformAdded(self, transform):
        transform.deleteRequested.connect(lambda t=transform: self.deleteRequested.emit(transform))
        transform.copyTransform.connect(self.copyTransform)
        transform.pasteTransform.connect(self.pasteTransform)
        transform.bounceRequested.connect(self.bounceRequested)
        transform.pressed.connect(lambda doubleClicked: self.transformSelected.emit(transform, doubleClicked))
        transform.geometryChanged.connect(lambda: self.keyFrameContainer.layout().invalidate())
#        self.changed.emit()

#    def deleteKeyFrame(self, keyFrame):
#        self.keyFrameContainer.layout().removeItem(keyFrame)
#        self.removeItem(keyFrame)
#        self.keyFrames.pop(self.keyFrames.index(keyFrame))
#        self.checkIndexes()
#
#    def deleteKeyFrames(self, keyFrameList):
#        for keyFrame in keyFrameList:
#            self.keyFrameContainer.layout().removeItem(keyFrame)
#            self.removeItem(keyFrame)
#            self.keyFrames.pop(self.keyFrames.index(keyFrame))
#        self.checkIndexes()

#    def _deleteTransform(self):
#        transform = self.sender()
#        self.keyFrameContainer.layout().removeItem(transform)
#        self.removeItem(transform)
#        self.checkIndexes()

    def clearSelection(self):
        QtWidgets.QGraphicsScene.clearSelection(self)
        self.currentSelection = []

    def copyTransform(self):
        mimeData = QtCore.QMimeData()
        byteArray = QtCore.QByteArray()
        stream = QtCore.QDataStream(byteArray, QtCore.QIODevice.WriteOnly)
        for value in self.sender().getParameters():
            stream.writeInt(value)
        mimeData.setData('bigglesworth/TransformParameters', byteArray)
        QtWidgets.QApplication.clipboard().setMimeData(mimeData)

    def pasteTransform(self):
        mimeData = QtWidgets.QApplication.clipboard().mimeData()
        if mimeData.hasFormat('bigglesworth/TransformParameters'):
            byteArray = mimeData.data('bigglesworth/TransformParameters')
            stream = QtCore.QDataStream(byteArray)
            values = []
            while not stream.atEnd():
                values.append(stream.readInt())
#            self.sender().setParameters(values)
            self.pasteTransformRequested.emit(self.sender(), values)
#        self.changed.emit()

    def mousePressEvent(self, event):
        self.oldSelection = self.selectedItems()
        underMouse = None
        for underMouse in self.items(event.scenePos()):
            if isinstance(underMouse, (SampleItem, WaveTransformItem)):
                break
        if not event.modifiers():
            if event.buttons() == QtCore.Qt.LeftButton:
                if isinstance(underMouse, SampleItem):
                    if underMouse not in self.selectedItems():
                        self.clearSelection()
                    underMouse.setSelected(True)
                else:
                    self.clearSelection()
                    if isinstance(underMouse, WaveTransformItem):
                        self.transformSelected.emit(underMouse, False)
            elif isinstance(underMouse, SampleItem):
                if underMouse not in self.selectedItems():
                    self.clearSelection()
                underMouse.setSelected(True)
            elif isinstance(underMouse, WaveTransformItem):
                self.clearSelection()
        elif event.modifiers() == QtCore.Qt.ShiftModifier:
            if isinstance(underMouse, WaveTransformItem):
                self.clearSelection()
            else:
                selectedIndexes = [item.index for item in self.selectedItems() + ([underMouse] if isinstance(underMouse, SampleItem) else [])]
                if selectedIndexes:
                    selectionRange = range(min(selectedIndexes), max(selectedIndexes) + 1)
                    for item in self.keyFrames:
                        item.setSelected(item.index in selectionRange)
#        if isinstance(underMouse, SampleItem):
#            underMouse.pressed.emit(False)
        if event.buttons() == QtCore.Qt.RightButton:
            event.accept()
            return

    def mouseReleaseEvent(self, event):
        QtWidgets.QGraphicsScene.mouseReleaseEvent(self, event)
        newSelection = self.selectedItems()
        if newSelection and newSelection != self.oldSelection:
            for item in self.items(event.scenePos()):
                if isinstance(item, SampleItem):
                    item.pressed.emit(False)
                    break

    def contextMenuEvent(self, event):
        yMargin = self.view.mapFromScene(self.keyFrameContainer.geometry().topLeft()).y()

        underMouse = None
        for underMouse in self.items(event.scenePos()):
            if isinstance(underMouse, (SampleItem, WaveTransformItem)):
#                underMouse.maximize()
                break

        menu = QtWidgets.QMenu()

        selected = self.selectedItems()

        insertBeforeAction = False
        insertAfterAction = False
        if (selected and len(selected) == 1) or isinstance(underMouse, WaveTransformItem):
            if underMouse is None:
                underMouse = selected[0]
            if len(self.keyFrames) < 64 and isinstance(underMouse, SampleItem):
                before = underMouse.index - 1
#                before = self.getLayoutIndex(underMouse)
                after = underMouse.index + 1
                insertBeforeAction = menu.addAction(QtGui.QIcon.fromTheme('arrow-left'), 'Insert wave before')
                insertBeforeAction.setData(before)
                insertAfterAction = menu.addAction(QtGui.QIcon.fromTheme('arrow-right'), 'Insert wave after')
                insertAfterAction.setData(after)
                menu.addSeparator()
#            elif isinstance(underMouse, WaveTransformItem) and underMouse.isValid():
#                bounceAction = menu.addAction(QtGui.QIcon.fromTheme('timeline-insert'), 'Create intermediate waves')
#                bounceAction.setData(underMouse)
            menu.addActions(underMouse.actions())
#            underMouse.setMaximized(True)
            menu.addSeparator()
        elif selected:
            bounceAction = menu.addAction(QtGui.QIcon.fromTheme('timeline-insert'), 'Create intermediate waves')
            indexes = [i.index for i in selected]
            if len(indexes) != 2 or max(indexes) - min(indexes) < 2:
                bounceAction.setEnabled(False)
            else:
                bounceAction.setData(self.keyFrames[min(indexes)].nextTransform)
            joinMorphAction = menu.addAction(QtGui.QIcon.fromTheme('curve-connector'), 'Join and morph')
            if len(selected) <= 2:
                joinMorphAction.setEnabled(False)
            deleteSelectedAction = menu.addAction(QtGui.QIcon.fromTheme('edit-delete'), 'Remove selected items')
            if set(selected) == set(self.keyFrames):
                deleteSelectedAction.setEnabled(False)
        if menu.actions() and not menu.actions()[-1].isSeparator():
            menu.addSeparator()
        if self.maximized:
            minimizeAction = menu.addAction(QtGui.QIcon.fromTheme('zoom-out'), 'Minimize all items')
        else:
            minimizeAction = menu.addAction(QtGui.QIcon.fromTheme('zoom-in'), 'Maximize all items')
        disableHoverMode = menu.addAction(QtGui.QIcon.fromTheme('input-mouse'), '{}able hover mode'.format('Dis' if self.hoverMode else 'En'))
        if self.maximized:
            disableHoverMode.setEnabled(False)

        res = menu.exec_(QtGui.QCursor.pos())
        if res == disableHoverMode:
            self.setHoverMode(not self.hoverMode)
        elif res == minimizeAction:
            self.maximized = not self.maximized
            self.keyFrameContainer.setMaximized(self.maximized)
            if not self.maximized:
                self.view.ensureVisible(self.keyFrames[0], yMargin=yMargin)
            self.view.viewport().update()
            QtCore.QTimer.singleShot(1, lambda: self.view.setSceneRect(self.keyFrameContainer.geometry()))
        elif res in (insertBeforeAction, insertAfterAction):
#            self.createKeyFrameAtLayoutIndex(res.data())
            self.createKeyFrameRequested.emit(res.data(), None, res == insertAfterAction)
        elif len(selected) > 1:
            if res == deleteSelectedAction:
                self.deleteRequested.emit(selected)
            elif res == joinMorphAction:
                self.mergeRequested.emit(selected)
            elif res == bounceAction:
                self.bounceRequested.emit(bounceAction.data())
        if isinstance(underMouse, (SampleItem, WaveTransformItem)):
            if not self.maximized and \
                (isinstance(underMouse, WaveTransformItem) or (underMouse.index and not underMouse.final)):
                    QtCore.QTimer.singleShot(500, underMouse.minimize)

    def setHoverMode(self, mode):
        self.hoverMode = mode
        self.view.viewport().update()

#    def getTransformValues(self, index, keyFrameIndex):
#        layout = self.keyFrameContainer.layout()
#        prevItem = layout.itemAt(index - 1)
#        nextItem = layout.itemAt(index)
#        if isinstance(prevItem, SampleItem):
#            if isinstance(nextItem, SampleItem):
#                return prevItem.values, None
#            #TODO: check this!
#            return prevItem.values, None
#        elif isinstance(prevItem, WaveTransformItem) and isinstance(nextItem, WaveTransformItem):
#            while isinstance(prevItem, WaveTransformItem):
#                index -= 1
#                prevItem = layout.itemAt(index)
#            return prevItem.values, None
#        transform = prevItem
#        while isinstance(prevItem, WaveTransformItem):
#            index -= 1
#            prevItem = layout.itemAt(index)
#        return transform.valuesAt(keyFrameIndex), transform

    def dragEnterEvent(self, event):
        mimeData = event.mimeData()
        if mimeData.hasFormat('bigglesworth/SampleItemSelection'):
            self.view.window().statusBar().showMessage('Keep SHIFT pressed to duplicate waves')
            event.accept()
        elif mimeData.hasFormat('bigglesworth/WaveFileData'):
            event.accept()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.currentDropIndex = None
        self.keyFrameContainer.removePlaceHolders()
        self.view.window().statusBar().clearMessage()
        self.clearSelection()

    def getPos(self, x, item):
        if x <= item.geometry().left() + item.geometry().width() * .3:
            return self.BeforeItem
        elif x >= item.geometry().right() - item.geometry().width() * .3:
            return self.AfterItem
        return self.OnItem

    def getDropTargets(self, count):
        if self.currentDropIndex is None:
            return
        item = self.keyFrameContainer.layout().itemAt(self.currentDropIndex)
#        over = self.currentDropPos == 0
        index = None
        if item is None:
            return
        if isinstance(item, SampleItem):
            index = item.index
        elif isinstance(item, WaveTransformItem):
#            print(self.currentDropPos, item.prevItem.index, item.nextItem.index)
            if self.currentDropPos < 0 and item.prevItem:
                if isinstance(item.prevItem, SampleItem):
                    index = item.prevItem.index
                else:
                    index = item.prevItem.prevWaveIndex
            elif self.currentDropPos >= 0 and item.nextItem:
                if item.nextItem == self.keyFrames[0]:
                    #yes, this is right! but might want to check it out in future...
                    index = 64
                elif isinstance(item.nextItem, SampleItem):
                    index = item.nextItem.index
                else:
                    index = item.nextItem.prevWaveIndex
        if index is None:
            return
        overwrite = []
        targets = []
        movedBefore = movedAfter = 0
        existing = [i for i, k in enumerate(self.keyFrames.fullList) if k]
        if not self.currentDropPos:
            if index == 64 and isinstance(item, WaveTransformItem):
                if not None in self.keyFrames.fullList:
                    overwrite.append(63)
                elif self.keyFrames.fullList[63]:
                    movedBefore += 1
            else:
                overwrite.append(index)
            targets.append(min(63, index))
            count -= 1
            if not count:
                return targets, overwrite, movedBefore, movedAfter
        freeBefore = freeAfter = 0
        for i, item in enumerate(self.keyFrames.fullList):
            if i < index and item is None:
                freeBefore += 1
            elif i > index and item is None:
                freeAfter += 1
        if freeAfter > freeBefore or self.currentDropPos > 0:
            delta = 1
        else:
            delta = -1
        multiplier = 1
        #index is sanitized now, because of special case of index 64 (see above)
#        index = sanitize(0, index, 63)
        minIndex = 1
        current = sanitize(1, index + multiplier * delta, 63)
        while count and (freeBefore or freeAfter) and self.currentDropPos:
            print('insert')
            if current < index and freeBefore and current not in targets:
                freeBefore -= 1
                count -= 1
                targets.append(current)
                if current in existing:
                    movedBefore += 1
            elif current > index and freeAfter and current not in targets:
                freeAfter -= 1
                count -= 1
                targets.append(current)
                if current in existing:
                    movedAfter += 1
            if freeBefore and freeAfter:
                delta *= -1
                multiplier += .5
            elif freeBefore:
                delta = -1
                minIndex = 0
                multiplier += 1
            elif freeAfter:
                delta = 1
                multiplier += 1
            current = sanitize(minIndex, index + int(multiplier) * delta, 63)
        delta = 1 if self.currentDropPos >= 0 else -1
        current = sanitize(0, index, 63)
        multiplier = 0
        done = 0
        while count:
            if current not in targets:
                targets.append(current)
                while targets[done] in overwrite:
                    done += 1
                overwrite.append(targets[done])
                count -= 1
                done += 1
            delta *= -1
            multiplier += .5
            current = sanitize(0, index + int(multiplier) * delta, 63)
        return sorted(targets), sorted(overwrite), movedBefore, movedAfter

    def dragMoveEvent(self, event):
        mimeData = event.mimeData()
        if mimeData.hasFormat('bigglesworth/SampleItemSelection'):
            item = self.itemAt(event.scenePos())
            if not item:
                event.ignore()
                self.keyFrameContainer.removePlaceHolders()
                return
            currentDropIndex = self.currentDropIndex
            pos = self.currentDropPos
            for index in range(self.keyFrameContainer.layout().count()):
                _item = self.keyFrameContainer.layout().itemAt(index)
                if _item == item:
                    currentDropIndex = index
                    pos = self.getPos(event.scenePos().x(), _item)
                    delta = 2 if isinstance(item, WaveTransformItem) and (item.isValid() and item.isContiguous()) else 1
                    break
            if self.currentDropIndex == currentDropIndex or self.currentDropIndex is None:
                if self.currentDropPos != pos:
                    if not pos:
                        self.keyFrameContainer.setPlaceHolder(currentDropIndex)
                    else:
                        if pos > 0:
                            self.keyFrameContainer.insertPlaceHolder(currentDropIndex + delta)
                        else:
                            self.keyFrameContainer.insertPlaceHolder(currentDropIndex)
            elif self.currentDropIndex is not None:
                if pos > 0:
                    self.keyFrameContainer.insertPlaceHolder(currentDropIndex + delta)
                else:
                    self.keyFrameContainer.insertPlaceHolder(currentDropIndex)

            self.currentDropIndex = currentDropIndex
            self.currentDropPos = pos

            if self.currentDropIndex is None:
                return event.ignore()
            stream = QtCore.QDataStream(mimeData.data('bigglesworth/SampleItemSelection'))
            indexes = []
            while not stream.atEnd():
                indexes.append(stream.readInt())
            count = len(indexes)
            if event.modifiers() == QtCore.Qt.ShiftModifier or event.source() != self.view:
                event.setDropAction(QtCore.Qt.CopyAction)
                target = self.keyFrameContainer.layout().itemAt(self.currentDropIndex)
                if isinstance(target, WaveTransformItem) and not self.currentDropPos:
                    return event.ignore()
                if len(self.keyFrames) + count - (0 if self.currentDropPos else 1) > 64:
                    if event.source() == self.view or event.modifiers() != QtCore.Qt.ControlModifier:
                        return event.ignore()
                data = self.getDropTargets(count)
                if not data:
                    return event.ignore()
                targets, overwrite, movedBefore, movedAfter = data
                [k.setSelected(k.index in overwrite) for k in self.keyFrames]

            else:
                event.setDropAction(QtCore.Qt.MoveAction)
            event.accept()

        elif mimeData.hasFormat('bigglesworth/WaveFileData'):
            item = self.itemAt(event.scenePos())
            if not item:
                event.ignore()
                self.keyFrameContainer.removePlaceHolders()
                return
            byteArray = mimeData.data('bigglesworth/WaveFileData')
            stream = QtCore.QDataStream(byteArray)
            #read window uuid and tab
            [stream.readQVariant(), stream.readInt()]
            count = stream.readInt()
            currentDropIndex = self.currentDropIndex
            pos = self.currentDropPos
            for index in range(self.keyFrameContainer.layout().count()):
                _item = self.keyFrameContainer.layout().itemAt(index)
                if _item == item:
                    currentDropIndex = index
                    pos = self.getPos(event.scenePos().x(), _item)
                    delta = 2 if isinstance(item, WaveTransformItem) and not item.mode else 1
                    break
            if self.currentDropIndex == currentDropIndex or self.currentDropIndex is None:
                if self.currentDropPos != pos:
                    if not pos:
                        self.keyFrameContainer.setPlaceHolder(currentDropIndex)
                    else:
                        if pos > 0:
                            self.keyFrameContainer.insertPlaceHolder(currentDropIndex + delta)
                        else:
                            self.keyFrameContainer.insertPlaceHolder(currentDropIndex)
            elif self.currentDropIndex is not None:
                if pos > 0:
                    self.keyFrameContainer.insertPlaceHolder(currentDropIndex + delta)
                else:
                    self.keyFrameContainer.insertPlaceHolder(currentDropIndex)
            self.currentDropIndex = currentDropIndex
            self.currentDropPos = pos
            data = self.getDropTargets(count)
            if not data:
                return event.ignore()
            targets, overwrite, movedBefore, movedAfter = data
            [k.setSelected(k.index in overwrite) for k in self.keyFrames]

    def dropEvent(self, event):
        self.view.window().statusBar().clearMessage()
        self.keyFrameContainer.removePlaceHolders()
        mimeData = event.mimeData()
        if mimeData.hasFormat('bigglesworth/SampleItemSelection'):
            byteArray = mimeData.data('bigglesworth/SampleItemSelection')
            stream = QtCore.QDataStream(byteArray)
            indexes = []
            while not stream.atEnd():
                indexes.append(stream.readInt())
            if event.source().window() == self.view.window():
                items = []
                total = len(indexes)
                if total == 1:
                    for keyFrame in self.keyFrames:
                        if keyFrame.index in indexes:
                            items.append(keyFrame)
                            break
                else:
                    done = 0
                    for keyFrame in self.keyFrames:
                        if keyFrame.index in indexes:
                            items.append(keyFrame)
                            done += 1
                            if done < total:
                                items.append(keyFrame.nextTransform)
                if event.modifiers() == QtCore.Qt.ShiftModifier:
                    print('copio')
                    self.copyKeyFrames(items, self.currentDropIndex, self.currentDropPos)
                else:
                    print('mouvo')
                    self.moveKeyFrames(items, self.currentDropIndex, self.currentDropPos)
            else:
                dropData = self.getDropTargets(len(indexes))
                if not dropData:
                    event.ignore()
                    return
                data = []
                sourceKeyFrames = event.source().window().keyFrames
                for index in range(min(indexes), max(indexes)):
                    keyFrame = sourceKeyFrames.fullList[index]
                    if keyFrame:
                        data.append((SampleItem, sourceKeyFrames.fullValues[index][:]))
                        transform = keyFrame.nextTransform
                        data.append((WaveTransformItem, transform.mode, transform.data))
                if sourceKeyFrames.fullList[max(indexes)]:
                    data.append((SampleItem, sourceKeyFrames.fullValues[max(indexes)][:]))
                self.externalDrop.emit(dropData, data, event.source().window().currentWaveTableName)

        elif mimeData.hasFormat('bigglesworth/WaveFileData'):
            byteArray = mimeData.data('bigglesworth/WaveFileData')
            stream = QtCore.QDataStream(byteArray)
            #read window uuid and tab
            [stream.readQVariant(), stream.readInt()]
            count = stream.readInt()
            dropData = self.getDropTargets(count)
            if not dropData:
                event.ignore()
                return
#            targets, overwrite, movedBefore, movedAfter = dropData
#            values = [map(lambda v: sanitize(-pow20, v, pow20), stream.readQVariant() * pow20) for _ in range(count)]
            values = [stream.readQVariant() for _ in range(count)]
            filePath = stream.readQVariant()
            self.waveDrop.emit(dropData, values, filePath)

    def copyKeyFrames(self, items, dropIndex, dropPos):
        print(dropIndex, dropPos)
#        values = {}
#        print([k.index for k in items if isinstance(k, SampleItem)])

    def moveKeyFrames(self, items, dropIndex, dropPos):
        print(dropIndex, dropPos)

#    def _moveKeyFrames(self, items, dropIndex, dropPos):
##        print(dropIndex, dropPos)
#        layout = self.keyFrameContainer.layout()
#        firstIndex = self.getLayoutIndex(items[0])
#        if len(items) > 1:
#            lastIndex = self.getLayoutIndex(items[-1])
#            indexRange = range(firstIndex, lastIndex + 1)
#        else:
#            lastIndex = firstIndex
#            indexRange = [firstIndex]
#        if dropIndex in indexRange or (dropPos == self.AfterItem and dropIndex + 2 == firstIndex) or \
#            (dropPos == self.BeforeItem and dropIndex -2 == lastIndex):
#                print('ignoro')
#                return
#        print('procedo')
#        for item in items:
#            layout.removeItem(item)
#        wasAfter = True
#        if firstIndex < dropIndex:
#            wasAfter = False
#            dropIndex -= len(items) - (1 if dropPos > 0 else 0)
#        elif dropPos == self.AfterItem:
#            dropIndex += 1
#        for item in reversed(items):
#            layout.insertItem(dropIndex, item)
#        self.checkIndexes(wasAfter)

    def checkIndexes(self, wasAfter=False):
        self.blockSignals(True)
        keyIndex = 0
#        self.keyFrames = []
        layout = self.keyFrameContainer.layout()
        prevItem = None
        changed = []
        emptyTransforms = []
        newTransformReferences = []

        for index in range(layout.count()):
            item = layout.itemAt(index)

            if isinstance(item, WaveTransformItem):
                if isinstance(prevItem, WaveTransformItem):
                    if (not item.mode and prevItem.mode) or item.isContiguous():
                        emptyTransforms.append(item)
                    elif (item.mode and not prevItem.mode) or prevItem.isContiguous():
                        emptyTransforms.append(prevItem)
                prevItem = item
                continue

            elif isinstance(prevItem, SampleItem):
                newTransformReferences.append((prevItem, item))

            if item not in self.keyFrames:
                self.keyFrames.append(item)

            if keyIndex:
                changed.append(item)
                item.blockSignals(True)
                item.setFinal(False)
                item.blockSignals(False)
            if keyIndex == 0 and item.index > 0:
                changed.append(item)
                item.blockSignals(True)
                item.setIndex(keyIndex)
                item.blockSignals(False)
            elif item.index > keyIndex:
                if wasAfter:
                    changed.append(item)
                    item.blockSignals(True)
                    item.setIndex(keyIndex)
                    item.blockSignals(False)
                else:
                    keyIndex = item.index
            elif item.index < keyIndex:
                changed.append(item)
                item.blockSignals(True)
                item.setIndex(keyIndex)
                item.blockSignals(False)
            keyIndex += 1
            prevItem = item

        #sort *before* adding or removing new transformations
#        self.keyFrames.sort(key=lambda k: k.index)
        last = self.keyFrames[-1]
        last.blockSignals(True)
        last.setFinal(True)
        last.blockSignals(False)

        for empty in emptyTransforms:
            layout.removeItem(empty)
            self.removeItem(empty)
        for newPrev, newNext in newTransformReferences:
            transform = WaveTransformItem(self.keyFrames, newPrev, newNext)
            layout.insertItem(self.getLayoutIndex(newNext), transform)

        #reset transformations targets
        count = layout.count()
        for index in range(count):
            item = layout.itemAt(index)
            if isinstance(item, WaveTransformItem):
                prevItem = layout.itemAt(index - 1) if index else None
                nextItem = layout.itemAt(index + 1) if index < count else None
                item.setTargets(prevItem, nextItem)

        self.keyFrames.rebuild()
        self.blockSignals(False)
        self.changed.emit()

    def getLayoutIndex(self, item):
        for index in range(self.keyFrameContainer.layout().count()):
            _item = self.keyFrameContainer.layout().itemAt(index)
            if _item == item:
                break
        return index


class Grid(QtWidgets.QGraphicsWidget):
    _rect = QtCore.QRectF(0, 0, pow21, pow16)
    boundingRect = lambda cls: cls._rect

    basePen = QtGui.QPen(QtGui.QColor(200, 0, 200), .8)
    basePen.setCosmetic(True)
    smallPen = QtGui.QPen(QtGui.QColor(220, 220, 210, 200), .25)
    smallPen.setCosmetic(True)
    baseLinePen = QtGui.QPen(QtGui.QColor(QtCore.Qt.red), 1.)
    baseLinePen.setCosmetic(True)

    def __init__(self):
        QtWidgets.QGraphicsWidget.__init__(self)
        self.mainGridLines = []
        self.smallGridLines = []
        
        h_length = pow21 - 16384
        for group in xrange(0, pow21, 65536):
            hLine = QtWidgets.QGraphicsLineItem(QtCore.QLineF(0, group, h_length, group), self)
            hLine.setPen(self.basePen)
            self.mainGridLines.append(hLine)
            vLine = QtWidgets.QGraphicsLineItem(QtCore.QLineF(group, 0, group, pow21), self)
            vLine.setPen(self.basePen)
            self.mainGridLines.append(vLine)
            for line in xrange(1, 4):
                pos = group + line * 16384
                hLine = QtWidgets.QGraphicsLineItem(QtCore.QLineF(0, pos, h_length, pos), self)
                hLine.setPen(self.smallPen)
                self.smallGridLines.append(hLine)
                vLine = QtWidgets.QGraphicsLineItem(QtCore.QLineF(pos, 0, pos, pow21), self)
                vLine.setPen(self.smallPen)
                self.smallGridLines.append(vLine)
#        hLine = QtWidgets.QGraphicsLineItem(QtCore.QLineF(0, pow21, h_length, pow21), self)
#        hLine.setPen(self.basePen)
#        self.mainGridLines.append(hLine)
        self.baseLine = self.mainGridLines.pop(32)
        self.baseLine.setPen(self.baseLinePen)
        self.baseLine.setZValue(10)
        self.shown = False

    def showEvent(self, event):
        if not self.shown:
            self.shown = True
            self.scene().removeItem(self.mainGridLines.pop(0))
            self.scene().removeItem(self.mainGridLines.pop(0))

    def setGridMode(self, mode):
        if not mode:
            for line in self.mainGridLines + self.smallGridLines:
                line.setVisible(False)
        elif mode == 1:
            for line in self.mainGridLines:
                line.setVisible(True)
            for line in self.smallGridLines:
                line.setVisible(False)
        else:
            for line in self.mainGridLines + self.smallGridLines:
                line.setVisible(True)


class WaveIndexItem(QtWidgets.QGraphicsObject):
    basePen = QtGui.QColor(QtCore.Qt.lightGray)
    hoverPen = QtGui.QColor(basePen)
    hoverPen.setAlpha(128)
    _rect = QtCore.QRectF()

    def __init__(self, parent):
        QtWidgets.QGraphicsObject.__init__(self)
        self.setFlags(self.flags() ^ self.ItemIgnoresTransformations)
        self.setAcceptsHoverEvents(True)
        self.text = '1'
        self.font = QtWidgets.QApplication.font()
        self.setPointSize(32)
        self._pen = QtGui.QColor(self.basePen)
        self.penAnimation = QtCore.QPropertyAnimation(self, b'pen')
        self.penAnimation.setDuration(150)
        self.penAnimation.setStartValue(self._pen)
        self.penAnimation.setEndValue(self.hoverPen)

    def setPointSize(self, size):
        self.font.setPointSizeF(size)
        self.fontMetrics = QtGui.QFontMetricsF(self.font)
        self._rect = self.fontMetrics.boundingRect('WWW')
        self._rect.moveTop(0)
        self._rect.moveLeft(self.fontMetrics.width('.') * .5)

    @QtCore.pyqtProperty(QtGui.QColor)
    def pen(self):
        return self._pen

    @pen.setter
    def pen(self, color):
        self._pen = color
        self.update()

    def hoverEnterEvent(self, event):
        self.penAnimation.setDirection(self.penAnimation.Forward)
        self.penAnimation.start()

    def hoverLeaveEvent(self, event):
        self.penAnimation.setDirection(self.penAnimation.Backward)
        self.penAnimation.start()

    def boundingRect(self):
        return self._rect

    def setText(self, text):
        self.text = text
        self.update()

    def paint(self, qp, option, widget):
        qp.setPen(self.pen)
        qp.setFont(self.font)
        qp.drawText(self._rect, QtCore.Qt.AlignVCenter|QtCore.Qt.AlignLeft, self.text)


class CursorPositionItem(QtWidgets.QGraphicsItem):
    pen = QtGui.QColor(220, 220, 200)
    brush = QtGui.QColor(192, 192, 192, 128)
    _rect = textRect = QtCore.QRectF()

    def __init__(self, parent):
        QtWidgets.QGraphicsItem.__init__(self)
        self.setFlags(self.flags() ^ self.ItemIgnoresTransformations)
        self.font = QtWidgets.QApplication.font()
        self.font.setPointSizeF(9.)
        self.text = 'Sample 128\nValue {} '.format(pow22)
        self.fontMetrics = QtGui.QFontMetricsF(self.font)
        self.alignment = QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter
        self.textRect = self.fontMetrics.boundingRect(QtCore.QRectF(), self.alignment, self.text)
        self.textRect.moveTop(0)
        self.textRect.moveLeft(self.fontMetrics.width('.') * .5)
        self._rect = self.textRect.adjusted(-1, -1, 1, 1)
        self.textRect.moveLeft(2)

    def boundingRect(self):
        return self._rect

    def setCoordinates(self, sample, value):
        self.text = 'Sample {}\nValue {}'.format(sample + 1, value)

    def setShift(self, shift):
        self.text = 'Shift:\n{:+} samples'.format(-shift)

    def paint(self, qp, option, widget):
        qp.setPen(QtCore.Qt.NoPen)
        qp.setBrush(self.brush)
        qp.drawRoundedRect(self._rect, 2, 2)
        qp.setPen(self.pen)
        qp.setFont(self.font)
        qp.drawText(self.textRect, self.alignment, self.text)


class CurvePath(QtWidgets.QGraphicsItem):
    nodePen = QtGui.QPen(QtGui.QColor(QtCore.Qt.red), 1)
    nodePen.setCosmetic(True)
    _rect = QtCore.QRectF()

    def __init__(self, *args):
        QtWidgets.QGraphicsItem.__init__(self)
        self.setFlags(self.flags() | self.ItemHasNoContents)
        self.x1, self.y1, self.x2, self.y2, self.cubic = args
        self.node1 = QtWidgets.QGraphicsEllipseItem(-3, -3, 6, 6, self)
        self.node1.setFlags(self.node1.flags() | self.ItemIgnoresTransformations)
        self.node1.setPos(self.x1, self.y1)
        self.node1.setPen(self.nodePen)
        self.node2 = QtWidgets.QGraphicsEllipseItem(-3, -3, 6, 6, self)
        self.node2.setFlags(self.node1.flags())
        self.node2.setPos(self.x2, self.y2)
        self.node2.setPen(self.nodePen)
        self.line = QtCore.QLineF(self.x1, self.y1, self.x2, self.y2)
        self.path = QtGui.QPainterPath()
        self.path.moveTo(self.line.p1())
        self.path.lineTo(self.line.p2())
        self.pathItem = QtWidgets.QGraphicsPathItem(self.path, self)
        self.pathItem.setPen(self.nodePen)
        self.focusNode1 = QtWidgets.QGraphicsEllipseItem(-3, -3, 6, 6, self)
        self.focusNode1.setPen(self.nodePen)
        self.focusNode1.setFlags(self.node1.flags())
        if self.cubic:
            self.focusNode1.setPos(self.line.pointAt(.33))
            self.focusNode2 = QtWidgets.QGraphicsEllipseItem(-3, -3, 6, 6, self)
            self.focusNode2.setPen(self.nodePen)
            self.focusNode2.setPos(self.line.pointAt(.66))
            self.focusNode2.setFlags(self.node1.flags())
        else:
            self.focusNode1.setPos(self.line.pointAt(.5))
        self.initialized = False
        self.stroker = QtGui.QPainterPathStroker()
        self.stroker.setWidth(1)

    def setTarget(self, x2, y2):
        self.x2 = x2
        self.y2 = y2
        self.node2.setPos(x2, y2)
        self.line.setP2(QtCore.QPointF(x2, y2))
        if self.cubic:
            self.focusNode1.setPos(self.line.pointAt(.33))
            self.focusNode2.setPos(self.line.pointAt(.66))
        else:
            self.focusNode1.setPos(self.line.pointAt(.5))
        self.path.setElementPositionAt(1, x2, y2)
        self.pathItem.setPath(self.path)
        self._rect = self.node1.boundingRect() | self.pathItem.boundingRect() | self.node2.boundingRect()

    def setFocusPoint(self, x, y):
        x = max(self.x1, min(self.x2, x))
        self.path.setElementPositionAt(1, x, y)
        if not self.cubic:
            self.path.setElementPositionAt(2, x, y)
        if self.path.boundingRect().top() > 0 and self.path.boundingRect().bottom() < pow21:
            self.focusNode1.setPos(x, y)
#            self.pathItem.setPath(self.path)
            stroke = self.stroker.createStroke(self.path)
            valueMap = []
            for sample, controlPath in self.controlPaths:
                intersection = controlPath.intersected(stroke)
                valueMap.append((sample, intersection.boundingRect().bottom()))
            return valueMap

    def setFocusPoint2(self, x, y):
        x = max(self.x1, min(self.x2, x))
        self.path.setElementPositionAt(2, x, y)
        if self.path.boundingRect().top() > 0 and self.path.boundingRect().bottom() < pow21:
            self.focusNode2.setPos(x, y)
            stroke = self.stroker.createStroke(self.path)
            valueMap = []
            for sample, controlPath in self.controlPaths:
                intersection = controlPath.intersected(stroke)
                valueMap.append((sample, intersection.boundingRect().bottom()))
            return valueMap

    def initialize(self):
        self.path = QtGui.QPainterPath()
        self.path.moveTo(self.node1.pos())
        if self.cubic:
            self.path.cubicTo(self.focusNode1.pos(), self.focusNode2.pos(), self.node2.pos())
        else:
            self.path.quadTo(self.focusNode1.pos(), self.node2.pos())
        if self.x1 > self.x2:
            self.x2, self.x1 = self.x1, self.x2
            self.y2, self.y1 = self.y1, self.y2
        self.x1 += 16384
        self.controlPaths = []
        for sample, x in enumerate(range(self.x1, self.x2, 16384), self.x1 / 16384):
            p = QtGui.QPainterPath()
            p.addRect(x, 0, 1, pow21)
#            i = QtWidgets.QGraphicsPathItem(p, self)
#            i.setPen(self.nodePen)
            self.controlPaths.append((sample, p))
            sample += 1
        self.x2 -= 16384
        self.scene().removeItem(self.pathItem)
        self.initialized = True
        if self.cubic:
            self.setFocusPoint(self.focusNode1.x(), self.focusNode1.y())
            return self.setFocusPoint2(self.focusNode2.x(), self.focusNode2.y())
        return self.setFocusPoint(self.focusNode1.x(), self.focusNode1.y())

    def boundingRect(self):
        return self._rect


class WaveScene(QtWidgets.QGraphicsScene):
    deltaPos = QtCore.QPoint(5, 5)

    waveBackground = QtGui.QLinearGradient(0, 0, 0, pow21)
    waveBackground.setColorAt(0, QtGui.QColor(0, 128, 192, 64))
    waveBackground.setColorAt(.5, QtGui.QColor(0, 128, 192, 192))
    waveBackground.setColorAt(1, QtGui.QColor(0, 128, 192, 64))

    wavePen = QtGui.QPen(QtGui.QColor(64, 192, 216), 1.2, cap=QtCore.Qt.RoundCap)
    wavePen.setCosmetic(True)

    mouseVGrad = QtGui.QLinearGradient(0, 0, 1, 0)
    mouseVGrad.setCoordinateMode(mouseVGrad.ObjectBoundingMode)
    mouseVGrad.setSpread(mouseVGrad.PadSpread)
    mouseHGrad = QtGui.QLinearGradient(0, 0, 0, 1)
    mouseHGrad.setCoordinateMode(mouseVGrad.ObjectBoundingMode)
    mouseHGrad.setSpread(mouseVGrad.PadSpread)
    for grad in mouseVGrad, mouseHGrad:
        grad.setColorAt(0, QtCore.Qt.transparent)
        grad.setColorAt(1, QtCore.Qt.transparent)
        grad.setColorAt(.3, QtGui.QColor(255, 255, 255, 100))
        grad.setColorAt(.45, QtCore.Qt.white)
        grad.setColorAt(.55, QtCore.Qt.white)
        grad.setColorAt(.7, QtGui.QColor(255, 255, 255, 100))

    snapNone, snapFull, snapMain = 0, 16384., 65536.
    snapModes = (
        (snapNone, snapFull), 
        (snapFull, snapFull), 
        (snapMain, snapMain)
    )

    FreeDraw, LineDraw = 1, 2
    QuadCurveDraw, CubicCurveDraw = 4, 8
    CurveDraw = QuadCurveDraw | CubicCurveDraw
    Shift, Gain = 64, 128
    Select, HLock, VLock, Drag = 512, 1024, 2048, 4096
    Harmonics = 8192
    Paste = 16384
    Drop = 32768
    Drawing = FreeDraw | LineDraw | CurveDraw
    Moving = Gain | HLock | VLock | Drag

    WaveTransformEnum = 524288
    Randomize, Smoothen, Quantize, HorizontalReverse, VerticalReverse = [WaveTransformEnum + 2 ** e for e in range(5)]

    cursors = {
        FreeDraw: 'draw-freehand', 
        LineDraw: 'draw-line', 
        QuadCurveDraw: 'node-segment-curve', 
        CubicCurveDraw: 'curve-connector', 
        Select: 'tool_rect_selection', 
        Drag: 'transform-move', 
        HLock: 'transform-move-vertical', 
        VLock: 'transform-move-horizontal', 
        Gain: 'audio-volume-high', 
        Shift: 'resizecol', 
    }

    statusMessages = {
        QuadCurveDraw: 'Draw a simple curve, press SHIFT to snap to the existing wave', 
        CubicCurveDraw: 'Draw a cubic curve, press SHIFT to snap to the existing wave', 
        LineDraw: 'Draw straight lines, press SHIFT to snap to the existing wave, CTRL for horizontal lines', 
        Drag: 'Move wave nodes. If no node is selected, the full wave will be moved only vertically', 
        HLock: 'Horizontal lock: the wave nodes will be moved only vertically', 
        VLock: 'Vertical lock: the selected wave nodes will be moved only horizontally', 
        Shift: 'Shift the whole wave horizontally', 
        Gain: 'Change the gain of the (selected) wave nodes', 
        Harmonics: 'Edit wave harmonics', 
    }


    freeDraw = QtCore.pyqtSignal(object, int, int, object)
    freeDrawInterpolate = QtCore.pyqtSignal(object, int, int, object, int)
    genericDraw = QtCore.pyqtSignal([int, object, object], [int, object, object, object])
    waveTransform = QtCore.pyqtSignal(int, object, object)

    def __init__(self, waveTableWindow):
        QtWidgets.QGraphicsScene.__init__(self)
        self.waveTableWindow = waveTableWindow
        self.view = waveTableWindow.waveView
        self.keyFrameScene = waveTableWindow.keyFrameScene
        self.keyFrames = self.keyFrameScene.keyFrames
        self.waveTableScene = waveTableWindow.waveTableScene
        self.hoverCursor = HoverCursor()

        self.grid = Grid()
        self.addItem(self.grid)
        self.grid.setZValue(-10)
        self.setGridMode = self.grid.setGridMode

        self.waveIndexItem = WaveIndexItem(self)
        self.addItem(self.waveIndexItem)
        self.waveIndexItem.setZValue(-5)

        self.extData = None
        self.buttonTimer = None
        self.statusMessage = None
        self.selectedNodes = None
        self.hSnap = self.snapFull
        self.vSnap = self.snapNone
        self.lastSampleSet = None
        self.curvePath = None
        self.showCrosshair = True
        self.showNodes = False
        self.mouseMode = 0
        self.previousIndex = self.currentIndex = 0

        self.nodes = []
        for sample in range(128):
            node = NodeItem(sample)
#            node.setVisible(False)
            self.nodes.append(node)
            self.addItem(node)

        self.backgroundPath = self.addPath(QtGui.QPainterPath())
        self.backgroundPath.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        self.backgroundPath.setBrush(self.waveBackground)

        self.currentWavePath = self.addPath(QtGui.QPainterPath())
        self.currentWavePath.setPen(self.wavePen)

        self._currentKeyFrame = self.currentUuid = None
        self.setKeyFrame(self.keyFrames[0])

        self.xLine = self.addRect(-2, 0, 4, pow21)
        self.xLine.setFlags(self.xLine.flags() ^ self.xLine.ItemIgnoresTransformations)
        self.xLine.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        self.xLine.setBrush(self.mouseVGrad)
        self.xLine.setVisible(False)

        self.yLine = self.addRect(0, -2, pow21, 4)
        self.yLine.setFlags(self.yLine.flags() ^ self.yLine.ItemIgnoresTransformations)
        self.yLine.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        self.yLine.setBrush(self.mouseHGrad)
        self.yLine.setVisible(False)

        self.cursorPosition = CursorPositionItem(self)
        self.addItem(self.cursorPosition)
        self.cursorPosition.setVisible(False)

    @property
    def currentKeyFrame(self):
        return self._currentKeyFrame

    @currentKeyFrame.setter
    def currentKeyFrame(self, keyFrame):
        self._currentKeyFrame = keyFrame
        self.currentUuid = keyFrame.uuid
        self.previousIndex = self.currentIndex
        self.currentIndex = keyFrame.index

    def indexesChanged(self, changed):
#        print('changed', changed)
        if not self.currentUuid in changed:
            return
        newIndex = changed[self.currentUuid]
        if newIndex is not None:
#            print('qui')
            self.setKeyFrame(self.keyFrames.get(newIndex))
        else:
#            print('quo')
            self.setKeyFrame(self.keyFrames.getClosestValidKeyFrame(self.currentIndex))
#        print('fatto')

    def setCrosshair(self, show):
        self.showCrosshair = show
        if not show:
            self.xLine.setVisible(show)
            self.yLine.setVisible(show)

    def setNodes(self, show):
        self.showNodes = show
        if show:
            for sample, (value, node) in enumerate(zip(self.currentKeyFrame.values, self.nodes)):
                element = self.currentKeyFrame.wavePath.elementAt(sample)
                node.setPos(element.x, element.y)
                node.setVisible(True)
        else:
            [node.setVisible(False) for node in self.nodes]

    def randomize(self):
        selected = self.selectedItems()
        if not selected:
            selected = self.nodes
        samples = [node.sample for node in selected]
        values = {sample:randrange(-pow20, pow20) for sample in samples}
#        values = [randrange(-pow20, pow20) for _ in range(128)]
#        self.currentKeyFrame.setValues(values)
        self.waveTransform.emit(self.Randomize, self.currentKeyFrame, values)

    def smoothen(self, edges=False):
        selected = self.selectedItems()
        if not selected:
            selected = self.nodes
            [n.setSelected(True) for n in selected]
        elif len(selected) < 3:
            return
        selected.sort(key=lambda n: n.sample)
        basePath = self.currentWavePath.path()
        newPath = QtGui.QPainterPath()
        first = basePath.elementAt(0)
        newPath.moveTo(first.x, first.y)
        for p in range(126):
            tempPath = QtGui.QPainterPath()
            first = basePath.elementAt(p)
            tempPath.moveTo(first.x, first.y)
            ref = basePath.elementAt(p + 1)
            last = basePath.elementAt(p + 2)
            if not self.nodes[p] in selected:
                newPath.lineTo((p + 1) * 16384, ref.y)
                continue
            tempPath.quadTo(ref.x, ref.y, last.x, last.y)
            newPath.lineTo((p + 1) * 16384, tempPath.pointAtPercent(.5).y())
        if selected[0] != self.nodes[0]:
            tempPath = QtGui.QPainterPath()
            first = basePath.elementAt(self.nodes[selected[0].sample - 1].sample)
            tempPath.moveTo(first.x, first.y)
            ref = basePath.elementAt(selected[0].sample)
            last = basePath.elementAt(selected[0].sample + 1)
            tempPath.quadTo(ref.x, ref.y, last.x, last.y)
            newPath.setElementPositionAt(selected[0].sample, selected[0].sample, tempPath.pointAtPercent(.5).y())
        if edges:
            if self.nodes[0] in selected:
                tempPath = QtGui.QPainterPath()
                tempPath.moveTo(-16384, basePath.elementAt(127).y)
                ref = basePath.elementAt(0)
                last = basePath.elementAt(1)
                tempPath.quadTo(ref.x, ref.y, last.x, last.y)
                newPath.setElementPositionAt(0, 0, tempPath.pointAtPercent(.5).y())
            if self.nodes[-1] in selected:
                tempPath = QtGui.QPainterPath()
                first = basePath.elementAt(126)
                tempPath.moveTo(first.x, first.y)
                ref = basePath.elementAt(127)
                last = basePath.elementAt(0)
                tempPath.quadTo(ref.x, ref.y, ref.x + 16384, last.y)
                newPath.lineTo(127 * 16384, tempPath.pointAtPercent(.5).y())

        values = []
        for sample in range(127):
            values.append(pow20 - newPath.elementAt(sample).y)
        if edges and self.nodes[-1] in selected:
            values.append(pow20 - newPath.elementAt(127).y)
        else:
            values.append(self.currentKeyFrame.values[-1])
#        self.currentKeyFrame.setValues(values)
        self.waveTransform.emit(self.Smoothen, self.currentKeyFrame, values)

    def quantize(self, resolution):
        if len(self.selectedItems()) > 4:
            indexes = [i for i in range(128) if self.nodes[i].isSelected()]
        else:
            indexes = range(128)
            [n.setSelected(True) for n in self.nodes]
        start = min(indexes)
#        end = max(indexes) + 1
        count = len(indexes)
        ratio = float(count) / resolution
        slices = []
        sample = step = 0
        for s in range(resolution):
            slice = []
            step += ratio
            while sample < step:
                slice.append(start + sample)
                sample += 1
            slices.append(slice)
        values = {}
        fullValues = self._currentKeyFrame.values
        for slice in slices:
            value = sum(fullValues[min(slice):max(slice) + 1]) / len(slice)
            for sample in slice:
                values[sample] = value
        self.waveTransform.emit(self.Quantize, self.currentKeyFrame, values)

    def reverseHorizontal(self):
#        self.currentKeyFrame.setValues(list(reversed(self.currentKeyFrame.values)))
        self.waveTransform.emit(self.HorizontalReverse, self.currentKeyFrame, list(reversed(self.currentKeyFrame.values)))

    def reverseVertical(self):
#        self.currentKeyFrame.setValues([v * -1 for v in self.currentKeyFrame.values])
        self.waveTransform.emit(self.VerticalReverse, self.currentKeyFrame, [v * -1 for v in self.currentKeyFrame.values])

    def setSnapMode(self, snap):
        self.vSnap, self.hSnap = self.snapModes[snap]

    def setMouseMode(self, mode):
        if mode == self.Select:
            self.view.setDragMode(self.view.RubberBandDrag)
        else:
            self.view.setDragMode(self.view.NoDrag)
        if mode != self.mouseMode and self.mouseMode & (self.CurveDraw | self.Harmonics):
            path = self.currentWavePath.path()
            for sample in range(128):
                path.setElementPositionAt(sample, path.elementAt(sample).x, pow20 - self.currentKeyFrame.values[sample])
            self.currentWavePath.setPath(path)
            if self.curvePath:
                self.removeItem(self.curvePath)
                self.curvePath = None
        if not self.showNodes:
            for sample, (value, node) in enumerate(zip(self.currentKeyFrame.values, self.nodes)):
                element = self.currentKeyFrame.wavePath.elementAt(sample)
                node.setPos(element.x, element.y)
        self.statusMessage = self.statusMessages.get(mode), 0
        self.hoverCursor.setCursor(self.cursors.get(mode))
        self.mouseMode = mode

    def getSampleCoordinates(self, pos):
        x = min(int(round(pos.x() / self.hSnap) * self.hSnap), 2080768)
        if self.vSnap:
            y = int(round(pos.y() / self.vSnap) * self.vSnap)
        else:
            y = int(pos.y())
        sample = (x / 16384)
        value = pow20 - y
        return x, y, sample, value

    def mousePressEvent(self, event):
        self.mousePos = event.scenePos()
        if event.buttons() == QtCore.Qt.LeftButton:
            self.buttonTimer = QtCore.QElapsedTimer()
            self.buttonTimer.start()
            if self.mouseMode & self.Drawing:
                x, y, sample, value = self.getSampleCoordinates(self.mousePos)
                if self.mouseMode == self.FreeDraw:
                    self.freeDraw.emit(self.currentKeyFrame, sample, value, self.buttonTimer)
                elif self.mouseMode == self.LineDraw:
                    self.oldPositions = [node.y() for node in self.nodes]
                    if event.modifiers() == QtCore.Qt.ShiftModifier:
                        y = self.nodes[sample].y()
                    self.lineStart = x, y, sample, value
                elif self.mouseMode & self.CurveDraw:
                    if not self.curvePath:
                        if event.modifiers() == QtCore.Qt.ShiftModifier:
                            y = self.nodes[sample].y()
                        self.curveStart = x, y, sample, value
                    else:
                        QtWidgets.QGraphicsScene.mousePressEvent(self, event)
            elif self.mouseMode == self.Shift:
                self.clearSelection()
                self.oldPositions = [node.y() for node in self.nodes]

    def mouseMoveEvent(self, event):
        pos = event.scenePos()
        if self.mouseMode & self.Moving:
            if event.buttons() == QtCore.Qt.LeftButton:

                if not self.selectedNodes:
                    self.oldPositions = [node.y() for node in self.nodes]
                    self.selectedSamples = []
                    self.selectedNodes = []
                    valueRange = set()
                    if not self.selectedItems():
                        for node in self.nodes:
                            node.setSelected(True)
                    for node in self.selectedItems():
                        self.selectedNodes.append((node, node.x(), node.y()))
                        self.selectedSamples.append(node.sample)
                        valueRange.add(node.y())
                    self.selectedNodes.sort(key=lambda t: t[0].sample)
                    self.dragVRangeMin = -min(valueRange)
                    self.dragVRangeMax = pow21 - max(valueRange)
                    self.dragHRangeMin = -self.selectedNodes[0][0].x()
                    self.dragHRangeMax = pow21 - 16384 - self.selectedNodes[-1][0].x()

                dragHRange = max(self.dragHRangeMin, min(pos.x() - self.mousePos.x(), self.dragHRangeMax))
                shift = int(round(dragHRange / 16384.))
                dragDeltaX = shift * 16384
                dragDeltaY = max(self.dragVRangeMin, min(pos.y() - self.mousePos.y(), self.dragVRangeMax))
                path = self.currentWavePath.path()

                if self.mouseMode == self.HLock:
                    for node, originX, originY in self.selectedNodes:
                        y = originY + dragDeltaY
                        node.setY(y)
                        path.setElementPositionAt(node.sample, node.x(), y)
                elif self.mouseMode == self.VLock:
                    values = []
                    for node, originX, originY in self.selectedNodes:
                        node.setX(originX + dragDeltaX)
                        values.append(node.y())
                    deltaSamples = map(lambda s: s + shift, self.selectedSamples)
                    values = iter(values)
                    for sample in range(128):
                        y = self.oldPositions[sample] if sample not in deltaSamples else values.next()
                        path.setElementPositionAt(sample, path.elementAt(sample).x, y)
                elif self.mouseMode == self.Drag:
                    values = []
                    for node, originX, originY in self.selectedNodes:
                        node.setPos(originX + dragDeltaX, originY + dragDeltaY)
                        values.append(node.y())
                    deltaSamples = map(lambda s: s + shift, self.selectedSamples)
                    values = iter(values)
                    for sample in range(128):
                        y = self.oldPositions[sample] if sample not in deltaSamples else values.next()
                        path.setElementPositionAt(sample, path.elementAt(sample).x, y)
                elif self.mouseMode == self.Gain:
                    deltaY = self.mousePos.y() - pos.y()
                    ratio = (pow20 + deltaY) / pow20
                    if ratio >= 1:
                        gain = log10(deltaY / pow20 * 9 + 1)
                    elif ratio > 0:
                        gain = max(-1, log10(ratio))
                    else:
                        gain = -1
                    for node, originX, originY in self.selectedNodes:
                        if originY == pow20:
                            continue
                        y = max(0, originY - (pow20 - originY) * gain)
                        if originY > pow20:
                            y = min(pow21, y)
                        node.setY(y)
                        path.setElementPositionAt(node.sample, node.x(), y)
                self.currentWavePath.setPath(path)

        elif self.mouseMode == self.Shift:
            if event.buttons() == QtCore.Qt.LeftButton:
                shift = -int(round((pos.x() - self.mousePos.x()) / 16384.))
                path = self.currentWavePath.path()
                for sample in range(128):
                    index = (sample + shift) % 128
                    path.setElementPositionAt(sample, path.elementAt(sample).x, self.oldPositions[index])
                self.currentWavePath.setPath(path)

                self.cursorPosition.setShift(shift)
                self.extData = -shift
                self.cursorPosition.setVisible(True)
                x, y, sample, value = self.getSampleCoordinates(pos)
                if event.buttons() == QtCore.Qt.LeftButton:
                    rect = self.view.mapToScene(self.cursorPosition.boundingRect().toRect()).boundingRect()
                    delta = self.view.mapToScene(self.deltaPos)
                    deltaX = delta.x()
                    deltaY = delta.y()
                    sceneRect = self.sceneRect()
                    x = max(deltaX, min(x, sceneRect.width() - rect.width() - deltaX))
                    y = max(deltaY, min(y - rect.height(), sceneRect.height() - rect.height() - deltaY))
                    self.cursorPosition.setPos(x, y)
                    self.cursorPosition.update()

        elif pos not in self.sceneRect() and not (self.curvePath and self.curvePath.initialized):
            self.xLine.setVisible(False)
            self.yLine.setVisible(False)
            self.cursorPosition.setVisible(False)
        else:
            if self.showCrosshair:
                self.xLine.setVisible(True)
                self.yLine.setVisible(True)
            self.cursorPosition.setVisible(True)
            x, y, sample, value = self.getSampleCoordinates(pos)

            if event.buttons() == QtCore.Qt.LeftButton:
                if self.mouseMode == self.FreeDraw:
                    if self.lastSampleSet is not None and sample != self.lastSampleSet:
#                        self.currentKeyFrame.interpolate(sample, value, self.lastSampleSet)
                        self.freeDrawInterpolate.emit(self.currentKeyFrame, sample, value, self.buttonTimer, self.lastSampleSet)
                    else:
#                        self.currentKeyFrame.setValue(sample, value)
                        self.freeDraw.emit(self.currentKeyFrame, sample, value, self.buttonTimer)
                    self.lastSampleSet = sample
                elif self.mouseMode == self.LineDraw:
                    startX, startY, startSample, startValue = self.lineStart
                    if event.modifiers() == QtCore.Qt.ShiftModifier:
                        y = self.nodes[sample].y()
                    elif event.modifiers() == QtCore.Qt.ControlModifier:
                        y = startY
                    path = self.currentWavePath.path()
                    if sample == startSample:
                        for s in range(128):
                            path.setElementPositionAt(s, path.elementAt(s).x, self.oldPositions[s])
                    else:
                        if sample > startSample:
                            lineRange = range(startSample, sample + 1)
                            ratio = 1. / len(lineRange)
                            done = iter(range(len(lineRange)))
                        else:
                            lineRange = range(startSample, sample - 1, -1)
                            ratio = 1. / len(lineRange)
                            done = iter(reversed(range(len(lineRange))))
                        line = QtCore.QLineF(startX, startY, x, y)
                        for s in range(128):
                            if s in lineRange:
                                pathY = line.pointAt(ratio * done.next()).y()
                            else:
                                pathY = self.oldPositions[s]
                            path.setElementPositionAt(s, path.elementAt(s).x, pathY)
                    self.currentWavePath.setPath(path)
                elif self.mouseMode & self.CurveDraw:
                    startX, startY, startSample, startValue = self.curveStart
                    if event.modifiers() == QtCore.Qt.ShiftModifier:
                        y = self.nodes[sample].y()
                    if self.curvePath and self.curvePath.initialized:
                        if self.mouseMode == self.CubicCurveDraw and event.modifiers() == QtCore.Qt.ControlModifier:
                            valueMap = self.curvePath.setFocusPoint2(x, event.scenePos().y())
                        else:
                            valueMap = self.curvePath.setFocusPoint(x, event.scenePos().y())
                        if valueMap:
                            path = self.currentWavePath.path()
                            for sample, y in valueMap:
                                path.setElementPositionAt(sample, path.elementAt(sample).x, y)
                            self.currentWavePath.setPath(path)
                        return
                    if abs(sample - startSample) < 3:
                        if self.curvePath:
                            self.removeItem(self.curvePath)
                            self.curvePath = None
                        return
                    if not self.curvePath:
                        self.curvePath = CurvePath(startX, startY, x, y, self.mouseMode == self.CubicCurveDraw)
                        self.addItem(self.curvePath)
                    else:
                        self.curvePath.setTarget(x, y)

            elif self.mouseMode & (self.LineDraw | self.CurveDraw):
                if event.modifiers() == QtCore.Qt.ShiftModifier:
                    y = self.nodes[sample].y()

            self.xLine.setX(x)
            self.yLine.setY(y)
            self.cursorPosition.setCoordinates(sample, value)
            rect = self.view.mapToScene(self.cursorPosition.boundingRect().toRect()).boundingRect()
            delta = self.view.mapToScene(self.deltaPos)
            deltaX = delta.x()
            deltaY = delta.y()
            sceneRect = self.sceneRect()
            if x + deltaX + rect.width() > sceneRect.width():
                x -= deltaX + rect.width()
            else:
                x += deltaX
            if y - deltaY - rect.height() < 0:
                y += deltaY
            else:
                y -= deltaY + rect.height()
            self.cursorPosition.setPos(x, y)
            self.cursorPosition.update()
        QtWidgets.QGraphicsScene.mouseMoveEvent(self, event)

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            values = oldValues = self.currentKeyFrame.values[:]
            if self.mouseMode & (self.Shift | self.LineDraw | self.Gain):
                values = []
                path = self.currentWavePath.path()
                for sample in range(128):
                    values.append(pow20 - path.elementAt(sample).y)
#                self.currentKeyFrame.setValues(values)
                
            elif self.selectedNodes:
                firstNode, firstX, firstY = self.selectedNodes[0]
                lastNode, lastX, lastY = self.selectedNodes[-1]
                deltaX = firstNode.x() - firstX
                sampleShift = deltaX / 16384
                deltaY = - firstNode.y() + firstY
                values = self.currentKeyFrame.values[:]
                indexes = []
                for node, originX, originY in self.selectedNodes:
                    index = int(node.sample + sampleShift)
                    indexes.append(index)
                    values[index] = pow20 - originY + deltaY
#                self.currentKeyFrame.setValues(values)
                for node in self.nodes:
                    node.setSelected(node.sample in indexes)
            if not self.mouseMode & self.CurveDraw and oldValues != values:
                if self.mouseMode == self.Shift:
                    self.genericDraw[int, object, object, object].emit(self.mouseMode, self.currentKeyFrame, values, self.extData)
                else:
                    self.genericDraw.emit(self.mouseMode, self.currentKeyFrame, values)
        self.lastSampleSet = None
        self.selectedNodes = None
        if self.curvePath and not self.curvePath.initialized:
            valueMap = self.curvePath.initialize()
            path = self.currentWavePath.path()
            for sample, y in valueMap:
                path.setElementPositionAt(sample, path.elementAt(sample).x, y)
            self.currentWavePath.setPath(path)
            if self.mouseMode == self.CubicCurveDraw:
                self.setStatusMessage('Keep CTRL pressed to edit alternate focus point, press ENTER to finalize the curve, ESC to ignore.')
            else:
                self.setStatusMessage('Press ENTER to finalize the curve, ESC to ignore.')
        self.buttonTimer = None
        QtWidgets.QGraphicsScene.mouseReleaseEvent(self, event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat('bigglesworth/SampleItemSelection'):
            byteArray = event.mimeData().data('bigglesworth/SampleItemSelection')
            stream = QtCore.QDataStream(byteArray)
            indexes = []
            while not stream.atEnd():
                indexes.append(stream.readInt())
            if len(indexes) == 1:
                event.accept()
                return
        elif event.mimeData().hasFormat('bigglesworth/WaveFileData'):
            byteArray = QtCore.QByteArray(event.mimeData().data('bigglesworth/WaveFileData'))
            stream = QtCore.QDataStream(byteArray)
            #read window uuid and tab
            [stream.readQVariant(), stream.readInt()]
            count = stream.readInt()
            if count == 1:
                event.accept()
                return
        QtWidgets.QGraphicsScene.dragEnterEvent(self, event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat('bigglesworth/SampleItemSelection'):
            byteArray = event.mimeData().data('bigglesworth/SampleItemSelection')
            stream = QtCore.QDataStream(byteArray)
            indexes = []
            while not stream.atEnd():
                indexes.append(stream.readInt())
            if len(indexes) == 1:
                event.accept()
                return
        elif event.mimeData().hasFormat('bigglesworth/WaveFileData'):
            byteArray = QtCore.QByteArray(event.mimeData().data('bigglesworth/WaveFileData'))
            stream = QtCore.QDataStream(byteArray)
            #read window uuid and tab
            [stream.readQVariant(), stream.readInt()]
            count = stream.readInt()
            if count == 1:
                event.accept()
                return
        QtWidgets.QGraphicsScene.dragMoveEvent(self, event)

    def dropEvent(self, event):
        if event.mimeData().hasFormat('bigglesworth/SampleItemSelection'):
            byteArray = event.mimeData().data('bigglesworth/SampleItemSelection')
            stream = QtCore.QDataStream(byteArray)
            indexes = []
            while not stream.atEnd():
                indexes.append(stream.readInt())
            if len(indexes) != 1 or indexes[0] == self.currentIndex:
                event.ignore()
                return
            values = event.source().window().keyFrames.get(indexes[0]).values[:]
            self.genericDraw.emit(self.Drop, self.currentKeyFrame, values)
        elif event.mimeData().hasFormat('bigglesworth/WaveFileData'):
            byteArray = QtCore.QByteArray(event.mimeData().data('bigglesworth/WaveFileData'))
            stream = QtCore.QDataStream(byteArray)
            #read window uuid and tab
            [stream.readQVariant(), stream.readInt()]
            count = stream.readInt()
            if count != 1:
                #this does never happen, right?
                print('what?!?')
                event.ignore()
                return
            self.genericDraw.emit(self.Drop, self.currentKeyFrame, map(lambda v: sanitize(-pow20, v, pow20), stream.readQVariant() * pow20))

    def setStatusMessage(self, message='', timeout=0):
        self.statusMessage = message, timeout
        self.view.window().statusBar().showMessage(message, timeout)

    def restoreStatusMessage(self):
        if self.statusMessage:
            self.setStatusMessage(*self.statusMessage)

    def clearStatusMessage(self):
        self.view.window().statusBar().clearMessage()

    def keyPressEvent(self, event):
        if self.mouseMode & self.CurveDraw and self.curvePath:
            if event.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
                values = []
                path = self.currentWavePath.path()
                for sample in range(128):
                    values.append(pow20 - path.elementAt(sample).y)
#                self.currentKeyFrame.setValues(values)
                self.genericDraw.emit(self.mouseMode, self.currentKeyFrame, values)
                self.removeItem(self.curvePath)
                self.curvePath = None
            elif event.key() == QtCore.Qt.Key_Escape:
                path = self.currentWavePath.path()
                for sample in range(128):
                    path.setElementPositionAt(sample, path.elementAt(sample).x, pow20 - self.currentKeyFrame.values[sample])
                self.currentWavePath.setPath(path)
                self.removeItem(self.curvePath)
                self.curvePath = None
        QtWidgets.QGraphicsScene.keyPressEvent(self, event)

    def harmonicsChanged(self, harmonics, waveType, add):
        if add:
            array = np.array((self.currentKeyFrame.values))
        else:
            array = np.array((0, ) * 128)
        for id, ratio in enumerate(harmonics, 1):
            if ratio:
#                array += np.array(waveFunction[waveType](id)) * pow19 * ratio * .5 / id
                np.add(array, np.array(waveFunction[waveType](id)) * pow19 * ratio / id, out=array, casting='unsafe')
        path = self.currentWavePath.path()
        for sample in range(128):
            value = sanitize(0, pow20 - array[sample], pow21)
            path.setElementPositionAt(sample, path.elementAt(sample).x, value)
        self.currentWavePath.setPath(path)

    def applyHarmonics(self):
        path = self.currentWavePath.path()
        values = []
        for sample in range(128):
            values.append(pow20 - path.elementAt(sample).y)
        self.genericDraw.emit(self.mouseMode, self.currentKeyFrame, values)

    def enter(self):
        self.restoreStatusMessage()
        self.hoverCursor.show()
        if not self.mouseMode & self.Drawing:
            return
        if self.showCrosshair:
            self.xLine.setVisible(True)
            self.yLine.setVisible(True)
        self.cursorPosition.setVisible(True)

    def leave(self):
        self.hoverCursor.hide()
        self.xLine.setVisible(False)
        self.yLine.setVisible(False)
        self.cursorPosition.setVisible(False)
        self.clearStatusMessage()

    def setKeyFrame(self, keyFrame=None):
        try:
            self.currentKeyFrame.changed.disconnect(self.setKeyFrame)
#            self.currentKeyFrame.valueChanged.disconnect(self.updateNode)
        except:
            pass
        if keyFrame is None:
            keyFrame = self.sender()
        self.currentKeyFrame = keyFrame
        self.currentKeyFrame.changed.connect(self.setKeyFrame)
#        self.currentKeyFrame.valueChanged.connect(self.updateNode)

        bgdPath = QtGui.QPainterPath(keyFrame.wavePath)
        bgdPath.lineTo(self.grid.baseLine.line().p2())
        bgdPath.lineTo(self.grid.baseLine.line().p1())
        self.backgroundPath.setPath(bgdPath)

        self.currentWavePath.setPath(keyFrame.wavePath)
        self.waveIndexItem.setText(str(keyFrame.index + 1))
        self.waveTableScene.updateSlice(keyFrame)

        for sample in range(128):
            element = self.currentKeyFrame.wavePath.elementAt(sample)
            self.nodes[sample].setPos(element.x, element.y)


class NextWaveScene(WaveScene):
    baseLinePen = QtGui.QPen(QtGui.QColor(QtCore.Qt.red), .5)
    baseLinePen.setCosmetic(True)
    currentKeyFrame = None

    def __init__(self):
        QtWidgets.QGraphicsScene.__init__(self)
        self.setSceneRect(QtCore.QRectF(0, 0, pow21, pow21))
        self.backgroundPath = self.addPath(QtGui.QPainterPath())
        self.backgroundPath.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        self.backgroundPath.setBrush(self.waveBackground)
        self.currentWavePath = self.addPath(QtGui.QPainterPath())
        self.currentWavePath.setPen(self.wavePen)
        self.baseLine = self.addLine(0, pow20, pow21, pow20)
        self.baseLine.setPen(self.baseLinePen)
        self.baseLine.setZValue(10)

        self.waveIndexItem = WaveIndexItem(self)
        self.addItem(self.waveIndexItem)
        self.waveIndexItem.setZValue(-5)
        self.waveIndexItem.setPointSize(8)

    def setWave(self, keyFrame):
        if self.currentKeyFrame:
            self.currentKeyFrame.changed.disconnect(self.updateWave)
        self.currentKeyFrame = keyFrame
        self.currentKeyFrame.changed.connect(self.updateWave)
        self.updateWave()

    def updateWave(self):
        self.waveIndexItem.setText(str(self.currentKeyFrame.index + 1))
        bgdPath = QtGui.QPainterPath(self.currentKeyFrame.wavePath)
        bgdPath.lineTo(self.baseLine.line().p2())
        bgdPath.lineTo(self.baseLine.line().p1())
        self.backgroundPath.setPath(bgdPath)
        self.currentWavePath.setPath(self.currentKeyFrame.wavePath)
        self.waveIndexItem.setText(str(self.currentKeyFrame.index + 1))


class PreviewWaveItem(QtWidgets.QGraphicsPathItem):
#    highlight = QtCore.pyqtSignal(object)
#    clicked = QtCore.pyqtSignal(object)

    normalPen = QtGui.QPen(QtGui.QColor(64, 192, 216, 185), 1)
    normalPen.setCosmetic(True)
    hoverPen = QtGui.QPen(QtGui.QColor(169, 214, 255), 1.5)
    hoverPen.setCosmetic(True)
    writingPen = QtGui.QPen(QtGui.QColor(255, 123, 57), 1.5)
    writingPen.setCosmetic(True)

    def __init__(self, keyFrame):
        QtWidgets.QGraphicsPathItem.__init__(self)
        self.index = keyFrame.index
        self.keyFrame = keyFrame
        keyFrame.changed.connect(self.updatePath)
#        path = QtGui.QPainterPath()
#        path.lineTo(50, 50)
#        path.quadTo(50, 100, 100, 100)
#        path.lineTo(100, 0)
        self.setAcceptsHoverEvents(True)
        self.stroker = QtGui.QPainterPathStroker()
        self.stroker.setWidth(4)
        self.setPath(keyFrame.wavePath)
        self.setPen(self.normalPen)
        self.highlighted = False

    def updatePath(self):
        self.setPath(self.keyFrame.wavePath)

    def setPath(self, path):
        QtWidgets.QGraphicsPathItem.setPath(self, path)
        self.strokerPath = self.stroker.createStroke(self.path())

#    def mouseDoubleClickEvent(self, event):
#        self.scene().waveDoubleClicked.emit(self.keyFrame)
#        self.clicked.emit(self.keyFrame)

    def hoverEnterEvent(self, event):
        self.setPen(self.hoverPen)
#        self.scene().highlight.emit(self.keyFrame)
        self.keyFrame.setHighlighted(True)

    def hoverLeaveEvent(self, event):
        if not self.highlighted:
            self.setPen(self.normalPen)
            self.keyFrame.setHighlighted(False)
        
#        self.setPen(self.hoverPen if self.highlighted else self.normalPen)

    def setHighlighted(self, highlighted):
        self.highlighted = highlighted
        if highlighted:
            self.setPen(self.hoverPen)
        else:
            self.setPen(self.normalPen)
            self.keyFrame.setHighlighted(False)
        self.update()

    def setWriting(self, writing):
        self.setPen(self.writingPen if writing else self.normalPen)
        self.update()

    def _shape(self):
        return self.strokerPath


class VirtualSlice(QtWidgets.QGraphicsPolygonItem):
    def __init__(self, index, polygon):
        QtWidgets.QGraphicsPolygonItem.__init__(self, polygon)
        self.index = index
        self.setFlags(self.flags() ^ self.ItemHasNoContents)


class EdgeVirtualSlice(QtWidgets.QGraphicsPolygonItem):
    def __init__(self, index, polygon):
        QtWidgets.QGraphicsPolygonItem.__init__(self, polygon)
        self.index = index
        self.setFlags(self.flags() ^ self.ItemHasNoContents)


class MaybeVisibleEditItem(QtWidgets.QGraphicsObject):
    _rectF = QtCore.QRectF()
    _rect = QtCore.QRect()
    pen = normalPen = QtGui.QPen(QtGui.QColor(QtCore.Qt.darkGray), 1)
    normalPen.setCosmetic(True)
    hoverPen = QtGui.QPen(QtGui.QColor(QtCore.Qt.lightGray), 1)
    hoverPen.setCosmetic(True)
    plusPen = plusPenNormal = QtGui.QPen(QtGui.QColor(QtCore.Qt.darkGray), 2)
    plusPenNormal.setCosmetic(True)
    plusPenHover = QtGui.QPen(QtGui.QColor(QtCore.Qt.white), 2)
    plusPenHover.setCosmetic(True)

    clicked = QtCore.pyqtSignal()

    def __init__(self, parent, size, view):
        QtWidgets.QGraphicsObject.__init__(self, parent)
        self.setFlags(self.flags() ^ self.ItemIgnoresTransformations)
        self.viewport = view.viewport()
        self.view = view
        self.setAcceptsHoverEvents(True)
        self._rectF.setSize(QtCore.QSizeF(size, size))
        self._rect.setSize(QtCore.QSize(size, size))
        self._rect.moveBottom(-size)
        self._rectF.moveBottom(-size)
        self.size = size
        self.edit = True
        self.editIconNormal = QtGui.QIcon.fromTheme('document-edit')
        self.editIconHover = QtGui.QIcon.fromTheme('document-edit-bright')
        self.editIcon = self.editIconNormal

        self.plusPath = QtGui.QPainterPath()
        half = size * .5
        self.plusPath.moveTo(2, half)
        self.plusPath.lineTo(size - 2, half)
        self.plusPath.moveTo(half, 2)
        self.plusPath.lineTo(half, size - 2)
        self.setEdit(False)

    def mousePressEvent(self, event):
        self.clicked.emit()
        QtWidgets.QGraphicsObject.mousePressEvent(self, event)

    def hoverEnterEvent(self, event):
        self.pen = self.hoverPen
        self.plusPen = self.plusPenHover
        self.editIcon = self.editIconHover
        QtWidgets.QGraphicsObject.hoverEnterEvent(self, event)

#    def hoverMoveEvent(self, event):
#        print(event.scenePos() in self.sceneBoundingRect(), self.contains(event.scenePos()))
#        QtWidgets.QGraphicsObject.hoverMoveEvent(self, event)

    def hoverLeaveEvent(self, event):
        self.pen = self.normalPen
        self.plusPen = self.plusPenNormal
        self.editIcon = self.editIconNormal
        QtWidgets.QGraphicsObject.hoverLeaveEvent(self, event)

    def boundingRect(self):
        return self._rectF

    def setEdit(self, edit=True):
        if edit == self.edit:
            return
        self.edit = edit

    def paint(self, qp, option, widget):
        if widget != self.viewport:
            return
        qp.setPen(self.pen)
        qp.drawRect(self._rect)
        if self.edit:
            qp.drawPixmap(self._rect, self.editIcon.pixmap(self.size))
        else:
            qp.translate(0, self._rectF.y() + 1)
            qp.setPen(self.plusPen)
            qp.drawPath(self.plusPath)

    def contains(self, pos):
        viewTransform = self.scene().view.viewportTransform()
        inverted, _ = viewTransform.inverted()
        transform = self.deviceTransform(viewTransform)
        rect = transform.mapRect(self.boundingRect())
        return pos in inverted.mapRect(rect)

class MaybeVisibleSimpleTextItem(QtWidgets.QGraphicsSimpleTextItem):
    def __init__(self, text, font, view):
        QtWidgets.QGraphicsSimpleTextItem.__init__(self, text)
        self.setFont(font)
        self.setFlags(self.flags() ^ self.ItemIgnoresTransformations)
        self.setBrush(QtCore.Qt.lightGray)
        self.viewport = view.viewport()
        self.editItem = MaybeVisibleEditItem(self, self.font().pointSizeF(), view)
        self.setVisible(False)
        self.index = 0

    def _setVisible(self, visible):
        QtWidgets.QGraphicsSimpleTextItem.setVisible(self, visible)
        self.editItem.setVisible(visible)

    def _setPos(self, pos):
        QtWidgets.QGraphicsSimpleTextItem.setPos(self, pos)
        self.editItem.setPos(pos)

    def _setY(self, y):
        QtWidgets.QGraphicsSimpleTextItem.setY(self, y)
        self.editItem.setY(y)

    def setIndex(self, index, other=None):
        self.index = index
        if other is None:
            self.setText(str(index + 1))
        else:
            self.setText('{}-{}'.format(index, other))

    def paint(self, qp, option, widget):
        if widget == self.viewport:
            QtWidgets.QGraphicsSimpleTextItem.paint(self, qp, option, widget)


class WaveTableScene(QtWidgets.QGraphicsScene):
    highlight = QtCore.pyqtSignal(object)
    waveDoubleClicked = QtCore.pyqtSignal(object)
    createKeyFrameRequested = QtCore.pyqtSignal(int, object, bool)
#    moveKeyFrameRequested = QtCore.pyqtSignal(object, int)
    moveKeyFramesRequested = QtCore.pyqtSignal(object, int)
    copyVirtualRequested = QtCore.pyqtSignal(int)
    deleteRequested = QtCore.pyqtSignal(object)
    waveDrop = QtCore.pyqtSignal(int, object, object)

    cubePen = QtGui.QPen(QtGui.QColor(169, 214, 255, 185), .5)
    cubePen.setCosmetic(True)
    cubeSelectPen = QtGui.QPen(QtGui.QColor(255, 240, 123, 185), .5)
    cubeSelectPen.setCosmetic(True)
    cubeSelectFrontBrush = QtGui.QColor(255, 240, 123, 109)
    cubeSelectBackBrush = QtGui.QColor(255, 240, 123, 64)
    cubeSelectNoBrush = QtGui.QBrush(QtCore.Qt.NoBrush)
    cubeBrush = QtGui.QBrush(QtGui.QColor(139, 163, 193, 106))
    transformPen = QtGui.QPen(QtGui.QColor(QtCore.Qt.white), .2)
    transformPen.setCosmetic(True)

    def __init__(self, waveTableWindow):
        QtWidgets.QGraphicsScene.__init__(self)
        self.waveTableWindow = waveTableWindow
        self.view = waveTableWindow.waveTableView
        self.keyFrameScene = waveTableWindow.keyFrameScene
        self.keyFrameScene.changed.connect(self.updateKeyFrames)
        self.keyFrameScene.selectionChanged.connect(self.keyFrameSceneSelectionChanged)
        self.keyFrames = self.keyFrameScene.keyFrames

        self.scaleTransform = QtGui.QTransform().scale(2, .55)
        self.xRatio = SampleItem.wavePathMaxWidth * .02
        self.yRatio = SampleItem.wavePathMaxHeight * .02

        self.back = QtWidgets.QGraphicsRectItem(0, 0, SampleItem.wavePathMaxWidth, SampleItem.wavePathMaxHeight)
        self.back.setZValue(-128)
        self.back.setX(SampleItem.wavePathMaxWidth * 1.26)
        self.back.setY(-SampleItem.wavePathMaxHeight * 1.26)
        self.back.setPen(self.cubePen)
        self.back.setTransform(self.scaleTransform)
        self.addItem(self.back)

        self.front = QtWidgets.QGraphicsRectItem(0, 0, SampleItem.wavePathMaxWidth, SampleItem.wavePathMaxHeight)
        self.front.setPen(self.cubePen)
        self.front.setTransform(self.scaleTransform)
        self.addItem(self.front)

        self.selectReference = QtGui.QPolygonF(self.scaleTransform.mapToPolygon(self.front.rect().toRect()))
        self.selectStart = QtWidgets.QGraphicsPolygonItem(self.selectReference)
        self.selectStart.setPen(self.cubeSelectPen)
        self.addItem(self.selectStart)
        self.selectStart.setVisible(False)

        self.selectEnd = QtWidgets.QGraphicsPolygonItem(self.selectReference)
        self.selectEnd.setPen(self.cubeSelectPen)
        self.addItem(self.selectEnd)
        self.selectEnd.setVisible(False)

        self.selectTop = QtWidgets.QGraphicsPolygonItem()
        self.selectTop.setBrush(self.cubeSelectFrontBrush)
        self.selectRight = QtWidgets.QGraphicsPolygonItem()
        self.selectRight.setBrush(self.cubeSelectFrontBrush)
        self.selectBottom = QtWidgets.QGraphicsPolygonItem()
        self.selectBottom.setBrush(self.cubeSelectBackBrush)
        self.selectLeft = QtWidgets.QGraphicsPolygonItem()
        self.selectLeft.setBrush(self.cubeSelectBackBrush)
        for p in (self.selectTop, self.selectRight, self.selectBottom, self.selectLeft):
            p.setPen(QtGui.QPen(QtCore.Qt.NoPen))
            p.setVisible(False)
            self.addItem(p)
        self.selectBottom.setZValue(-10)
        self.selectLeft.setZValue(-10)
        self.selectionItems = (self.selectStart, self.selectLeft, self.selectTop, self.selectRight, self.selectBottom, self.selectEnd)

        self.invertedScale, valid = self.scaleTransform.inverted()
        
        self.bottomBackLine = QtWidgets.QGraphicsLineItem(
            QtCore.QLineF(self.back.sceneBoundingRect().bottomLeft(), self.front.sceneBoundingRect().bottomLeft()))
        self.bottomBackLine.setPen(self.cubePen)
        self.bottomBackLine.setZValue(-128)
        self.addItem(self.bottomBackLine)

        self.bottomFrontLine = QtWidgets.QGraphicsLineItem(
            QtCore.QLineF(self.back.sceneBoundingRect().bottomRight(), self.front.sceneBoundingRect().bottomRight()))
        self.bottomFrontLine.setPen(self.cubePen)
        self.bottomFrontLine.setZValue(-128)
        self.addItem(self.bottomFrontLine)

        self.TopBackLine = QtWidgets.QGraphicsLineItem(
            QtCore.QLineF(self.back.sceneBoundingRect().topLeft(), self.front.sceneBoundingRect().topLeft()))
        self.TopBackLine.setPen(self.cubePen)
        self.addItem(self.TopBackLine)

        self.TopFrontLine = QtWidgets.QGraphicsLineItem(
            QtCore.QLineF(self.back.sceneBoundingRect().topRight(), self.front.sceneBoundingRect().topRight()))
        self.TopFrontLine.setPen(self.cubePen)
        self.addItem(self.TopFrontLine)

        self.sliceItem = self.addRect(self.front.rect())
        self.sliceItem.setTransform(self.scaleTransform)
        self.sliceItem.setPen(self.cubePen)
        self.sliceItem.setBrush(self.cubeBrush)
        self.sliceItem.setVisible(False)

        font = self.font()
        font.setPointSizeF(16)
#        self.sliceIdItem = self.addSimpleText('1', font)
#        self.sliceEditItem = $(16, self.view)
#        self.addItem(self.sliceEditItem)
        self.sliceIdItem = MaybeVisibleSimpleTextItem('1', font, self.view)
        self.sliceEditItem = self.sliceIdItem.editItem
        self.sliceEditItem.clicked.connect(self.sliceEditClicked)
        self.addItem(self.sliceIdItem)

        sliceX = self.front.x()
        sliceY = self.front.y() + self.front.rect().height() * .5
        sliceWidth = self.front.rect().width()
        sliceBottomLeft = QtCore.QPointF(sliceX, sliceY)
        sliceBottomRight = QtCore.QPointF(sliceX + sliceWidth, sliceY)
        sliceTopRight = QtCore.QPointF(sliceX + sliceWidth + self.xRatio * .5, sliceY - self.yRatio * 2)
        sliceTopLeft = QtCore.QPointF(sliceX + self.xRatio * .5, sliceY - self.yRatio * 2)
        slicePolygon = QtGui.QPolygonF([sliceBottomLeft, sliceBottomRight, sliceTopRight, sliceTopLeft])
        self.slices = []
        self.frontSlice = EdgeVirtualSlice(0, slicePolygon)
        self.addItem(self.frontSlice)
        self.slices.append(self.frontSlice)
        self.frontSlice.setTransform(self.scaleTransform)
        self.frontSlice.setPos(self.front.x() - self.xRatio * .5, 
            self.front.y() + self.xRatio * .5)
        clipSliceTopLeft = QtCore.QLineF(sliceTopLeft, sliceTopRight).pointAt(.15)
        clipSliceBottomLeft = QtCore.QLineF(sliceBottomLeft, sliceBottomRight).pointAt(.15)
        clipSlice = QtGui.QPolygonF([clipSliceBottomLeft, sliceBottomRight, sliceTopRight, clipSliceTopLeft])
        for i in range(1, 63):
            slice = VirtualSlice(i, clipSlice)
#            slice.setPen(QtGui.QPen(QtCore.Qt.white))
            self.addItem(slice)
            self.slices.append(slice)
            slice.setTransform(self.scaleTransform)
            slice.setPos(self.front.x() + i * self.xRatio - self.xRatio * .5, 
                self.front.y() - i * self.yRatio + self.xRatio * .5)
        self.backSlice = EdgeVirtualSlice(63, slicePolygon)
        self.addItem(self.backSlice)
        self.slices.append(self.backSlice)
        self.backSlice.setTransform(self.scaleTransform)
        self.backSlice.setPos(self.front.x() + 63 * self.xRatio - self.xRatio * .5, 
            self.front.y() - 63 * self.yRatio + self.xRatio * .5)

        self.highlight.connect(self.updateSlice)
        self.highlightedItem = None
        self.newIndex = None
        self.currentSelection = []
        self.moveRangePrev = self.moveRangeNext = 0

        self.keyFrameItems = {}
        self.motionLines = {}
        self.updateKeyFrames()
        self.setSceneRect(self.sceneRect().adjusted(-65536, 0, 65536, 0))

        self.updateQueue = set()
        self.queueTimer = QtCore.QTimer()
        self.queueTimer.setInterval(25)
        self.queueTimer.setSingleShot(True)
        self.queueTimer.timeout.connect(self.consumeQueue)

    def getPreview(self, qp, targetRect, sourceRect):
        if self.highlightedItem:
            self.highlightedItem.setHighlighted(False)
            self.highlightedItem = None
        self.sliceItem.setVisible(False)
        self.sliceIdItem.setVisible(False)
        self.clearSliceSelection()
        self.currentSelection = []
        self.render(qp, targetRect, sourceRect, mode=QtCore.Qt.IgnoreAspectRatio)

    def sliceEditClicked(self):
        keyFrame = (self.keyFrames.fullList[self.sliceIdItem.index])
        if keyFrame:
            self.waveDoubleClicked.emit(keyFrame)
        else:
            self.createKeyFrameRequested.emit(self.sliceIdItem.index, None, False)
#        self.sliceEditRequested.emit(self.sliceIdItem.index)

    def updateSlice(self, keyFrame):
        #emitted by PreviewWaveItem.hoverEnterEvent
        if self.highlightedItem and self.highlightedItem != keyFrame:
            self.highlightedItem.setHighlighted(False)
        waveItem = self.keyFrameItems.get(keyFrame)
        if waveItem:
            self.highlightedItem = waveItem
            waveItem.setHighlighted(True)
            self.sliceItem.setPos(waveItem.pos())
            self.sliceItem.setZValue(waveItem.zValue() - 1)
            self.sliceItem.setVisible(True)
            self.sliceIdItem.setIndex(keyFrame.index)
            self.sliceIdItem.setPos(self.sliceItem.pos())
            self.sliceIdItem.setY(
                self.sliceIdItem.y() - self.view.mapToScene(self.sliceIdItem.boundingRect().toRect()).boundingRect().height() * 1.25)
            self.sliceIdItem.setVisible(True)
            self.sliceEditItem.setEdit(True)
        else:
#            print('keyFrame not in previews?!')
            self.highlightedItem = None
            self.sliceItem.setPos(self.front.x() + keyFrame * self.xRatio, 
                self.front.y() - keyFrame * self.yRatio)
            self.sliceIdItem.setIndex(keyFrame)
            self.sliceIdItem.setPos(self.sliceItem.pos())
            self.sliceIdItem.setY(
                self.sliceIdItem.y() - self.view.mapToScene(self.sliceIdItem.boundingRect().toRect()).boundingRect().height() * 1.25)
            self.sliceItem.setVisible(True)
            self.sliceIdItem.setVisible(True)
            self.sliceEditItem.setEdit(False)

    def updateKeyFrames(self):
        for item in self.keyFrameItems.values() + list(chain(*self.motionLines.values())):
            self.removeItem(item)
        self.motionLines.clear()
        self.keyFrameItems.clear()
        if self.highlightedItem:
            self.highlightedItem.setHighlighted(False)
            self.highlightedItem = None
        for keyFrame in self.keyFrames:
            item = PreviewWaveItem(keyFrame)
#            item.highlight.connect(self.highlight)
#            item.clicked.connect(self.waveDoubleClicked)
            try:
                item.setX(self.front.x() + keyFrame.index * self.xRatio)
            except:
                print(self.keyFrames[:], self.keyFrames.fullList)
                raise
            item.setY(self.front.y() - keyFrame.index * self.yRatio)
            item.setTransform(self.scaleTransform)
            self.addItem(item)
            self.keyFrameItems[keyFrame] = item
            try:
                keyFrame.indexChanged.disconnect(self.updateKeyFrames)
            except:
                pass
            keyFrame.indexChanged.connect(self.updateKeyFrames)

        for item in self.keyFrames.allItems:
            if isinstance(item, WaveTransformItem):
                self.updateTransform(item)
#        return
#        #for "cycling" (last keyFrame has to know the first keyframe if it's not final)
#        first = self.keyFrames[0]
#        last = self.keyFrames[-1]
#        scaleX = self.invertedScale.m11()
#        scaleY = self.invertedScale.m22()
#        for keyFrame in self.keyFrames:
#            transform = keyFrame.nextTransform
#            if transform and transform.isValid() and not transform.isContiguous():
#                keyFrameX = keyFrame.index * scaleX
#                keyFrameY = -keyFrame.index * scaleY
#                if keyFrame == last:
#                    nextItem = first
#                    nextItemY = -63 * scaleY
#                    deltaX = (63 - keyFrame.index) * scaleX
##                    deltaY = -(63 - keyFrame.index) * scaleY
#                else:
#                    nextItem = transform.nextItem
#                    nextItemY = -(nextItem.index) * scaleY
#                    deltaX = (nextItem.index - keyFrame.index) * scaleX
##                    deltaY = -(nextItem.index - keyFrame.index) * scaleY
#                lines = []
#                self.motionLines[transform] = lines
#                if transform.mode:
#                    print('mode')
#                    for sample in range(128):
#                        p0 = keyFrame.wavePath.elementAt(sample)
#                        p1 = nextItem.wavePath.elementAt(sample)
#                        line = QtCore.QLineF(keyFrameX + p0.x, p0.y + keyFrameY, 
#                            keyFrameX + p0.x + deltaX, nextItemY - keyFrameY + p1.y)
#                        lineItem = self.addLine(line)
#                        lineItem.setPen(self.transformPen)
#                        lineItem.setTransform(self.scaleTransform)
#                        lines.append(lineItem)
#                else:
#                    print('constant', keyFrame.y())
#                    for sample in range(128):
#                        p0 = keyFrame.wavePath.elementAt(sample)
#                        p1 = nextItem.wavePath.elementAt(sample)
#                        line = QtCore.QLineF(keyFrameX + p0.x, p0.y + keyFrameY, 
#                            keyFrameX + p0.x + deltaX, nextItemY + p0.y)
#                        lineItem = self.addLine(line)
#                        lineItem.setPen(self.transformPen)
#                        lineItem.setTransform(self.scaleTransform)
#                        lines.append(lineItem)
#                transform.changed.connect(self.updateTransform)
#            else:
#                pass
##                print('habeoje', keyFrame, keyFrame.index, transform)
#            print(self.motionLines.keys())

    def queueTransformUpdate(self):
        self.updateQueue.add(self.sender())
        self.queueTimer.start()

    def consumeQueue(self):
        while self.updateQueue:
            self.updateTransform(self.updateQueue.pop())

    def updateTransform(self, transform=None):
        if transform is None:
            transform = self.sender()
        if not transform.isValid() or transform.isContiguous():
            return
        scaleX = self.invertedScale.m11() * self.xRatio
        scaleY = self.invertedScale.m22() * self.yRatio
        print(transform.prevItem, transform.nextItem)
        print('indexes: {} {}'.format(transform.prevItem.index, transform.nextItem.index))
        prevItem = transform.prevItem
        nextItem = transform.nextItem
#        prevPreview = self.keyFrameItems[prevItem]
        prevX = prevItem.index * scaleX
        prevY = -prevItem.index * scaleY
        if nextItem != self.keyFrames[0]:
            nextX = nextItem.index * scaleX
            nextY = -(nextItem.index) * scaleY
            diff = nextItem.index - prevItem.index
        else:
            nextX = 63 * scaleX
            nextY = -63 * scaleY
            diff = 63 - prevItem.index
#        print(prevX, prevY, nextX, nextY)
        lines = []
        if not transform.mode:
            for sample in range(128):
                p0 = prevItem.wavePath.elementAt(sample)
#                p1 = nextItem.wavePath.elementAt(sample)
                lines.append(QtCore.QLineF(p0.x + prevX, p0.y + prevY, p0.x + nextX, p0.y + nextY))
        elif transform.isLinear() or not transform.isValid():
            for sample in range(128):
                p0 = prevItem.wavePath.elementAt(sample)
                p1 = nextItem.wavePath.elementAt(sample)
                lines.append(QtCore.QLineF(p0.x + prevX, p0.y + prevY, p0.x + nextX, p1.y + nextY))
        elif transform.mode == WaveTransformItem.CurveMorph:
            if diff < 3:
                for sample in range(128):
                    p0 = prevItem.wavePath.elementAt(sample)
                    p1 = nextItem.wavePath.elementAt(sample)
                    lines.append(QtCore.QLineF(p0.x + prevX, p0.y + prevY, p0.x + nextX, p1.y + nextY))
            else:
                curveFunction = transform.curveFunction
                for sample in range(128):
                    p0 = prevItem.wavePath.elementAt(sample)
                    p1 = nextItem.wavePath.elementAt(sample)
                    path = QtGui.QPainterPath()
                    path.moveTo(p0.x, p0.y)
                    ratio = 1. / diff
                    yDiff = p1.y - p0.y
                    for p in range(1, diff + 1):
                        path.lineTo(p0.x + p * scaleX, p0.y - p * scaleY + yDiff * curveFunction(p * ratio))
                    path.translate(prevX, prevY)
                    lines.append(path)
#                    lines.append(QtCore.QLineF(p0.x + prevX, p0.y + prevY, p0.x + nextX, p1.y + nextY))
        elif transform.mode == WaveTransformItem.TransMorph:
#            if not transform.translate:
#                for sample in range(128):
#                    p0 = prevItem.wavePath.elementAt(sample)
#                    p1 = nextItem.wavePath.elementAt(sample)
#                    lines.append(QtCore.QLineF(p0.x + prevX, p0.y + prevY, p0.x + nextX, p1.y + nextY))
#            else:
                offset = transform.translate
                lineRatio = 1. / offset
                if offset < 0:
#                    lineRatio = 1 + lineRatio
                    offsetFunc = lambda s: lineRatio * (-s)
                    translateX = 101 * scaleX
                else:
                    offsetFunc = lambda s: lineRatio * (128 - s)
                    translateX = -101 * scaleX
                for sample in range(128):
                    p0 = prevItem.wavePath.elementAt(sample)
                    p1 = nextItem.wavePath.elementAt((sample + transform.translate) % 128)
#                    p1 = nextItem.wavePath.elementAt(sample)
                    xOffset = offset * scaleX * .78125
                    line = QtCore.QLineF(p0.x + prevX, p0.y + prevY, p0.x + nextX + xOffset, p1.y + nextY)
                    if 0 <= sample + offset <= 127:
                        lines.append(line)
                    else:
                        offsetPoint = offsetFunc(sample)
                        lines.append(QtCore.QLineF(line.p1(), line.pointAt(offsetPoint)))
                        line.translate(translateX, 0)
                        lines.append(QtCore.QLineF(line.pointAt(offsetPoint), line.p2()))
#                        otherLine = QtCore.QLineF()
#                        line.setLength(line.length() * lineRatio * (127 - sample))
#                        lines.append(line)
#                    path = QtGui.QPainterPath()
#                    path.moveTo(p0.x, p0.y)
#                    ratio = 1. / diff
#                    yDiff = p1.y - p0.y
#                    for p in range(1, diff + 1):
#                        path.lineTo(p0.x + p * scaleX, p0.y - p * scaleY + yDiff * p * ratio)
#                    path.translate(prevX, prevY)
#                    lines.append(path)
        elif transform.mode == WaveTransformItem.SpecMorph:
#            if diff < 3:
#                for sample in range(128):
#                    p0 = prevItem.wavePath.elementAt(sample)
#                    p1 = nextItem.wavePath.elementAt(sample)
#                    lines.append(QtCore.QLineF(p0.x + prevX, p0.y + prevY, p0.x + nextX, p1.y + nextY))
#            else:
                harmonicsArrays = np.swapaxes(transform.getHarmonicsArray(), 0, 1)
                curveFunction = transform.curveFunction
                for sample in range(128):
                    p0 = prevItem.wavePath.elementAt(sample)
                    p1 = nextItem.wavePath.elementAt(sample)
                    harmonicArray = harmonicsArrays[sample]
                    path = QtGui.QPainterPath()
#                    path.moveTo(p0.x, p0.y)
                    path.moveTo(p0.x, p0.y - harmonicArray[0])
                    ratio = 1. / diff
                    yDiff = p1.y - p0.y
                    for p in range(1, diff):
#                        value = p0.y - p * scaleY + yDiff * p * ratio
#                        path.lineTo(p0.x + p * scaleX, sanitize(0, p0.y - harmonicArray[p], pow21) - p * scaleY)
                        value = p0.y + yDiff * p * ratio - harmonicArray[p]
                        path.lineTo(p0.x + p * scaleX, sanitize(0, value, pow21) - p * scaleY)
                    path.translate(prevX, prevY)
                    lines.append(path)

        motionLines = self.motionLines.get(transform)
        if motionLines:
#            [lineItem.setLine(line) for lineItem, line in zip(motionLines, lines)]
            try:
                assert len(motionLines) == len(lines)
                for lineItem, line in zip(motionLines, lines):
                    try:
                        lineItem.setLine(line)
                    except:
                        lineItem.setPath(line)
            except:
                [self.removeItem(l) for l in motionLines]
                motionLines[:] = []
                for line in lines:
                    try:
                        lineItem = self.addLine(line)
                    except:
                        lineItem = self.addPath(line)
                    lineItem.setPen(self.transformPen)
                    lineItem.setTransform(self.scaleTransform)
                    motionLines.append(lineItem)
        else:
            transform.changed.connect(self.queueTransformUpdate)
            motionLines = self.motionLines.setdefault(transform, [])
            for line in lines:
                try:
                    lineItem = self.addLine(line)
                except:
                    lineItem = self.addPath(line)
                lineItem.setPen(self.transformPen)
                lineItem.setTransform(self.scaleTransform)
                motionLines.append(lineItem)


        return
#        keyFrame = transform.nextItem
#        item = self.keyFrameItems[keyFrame]
#        if transform.mode:
#            for sample, lineItem in enumerate(self.motionLines[transform]):
#                prevItem = self.keyFrameItems[transform.prevItem]
#                p0 = transform.prevItem.wavePath.elementAt(sample)
#                p1 = keyFrame.wavePath.elementAt(sample)
#                line = QtCore.QLineF(p0.x, p0.y, p0.x + delta * self.xRatio * self.invertedScale.m11(), 
#                    (item.y() - prevItem.y()) * self.invertedScale.m22() + p1.y)
#                lineItem.setLine(line)
#        else:
#            for sample, lineItem in enumerate(self.motionLines[transform]):
#                prevItem = self.keyFrameItems[transform.prevItem]
#                p0 = transform.prevItem.wavePath.elementAt(sample)
#                p1 = keyFrame.wavePath.elementAt(sample)
#                line = QtCore.QLineF(p0.x, p0.y, p0.x + delta * self.xRatio * self.invertedScale.m11(), 
#                    (item.y() - prevItem.y()) * self.invertedScale.m22() + p0.y)
#                lineItem.setLine(line)

    def isOverSelection(self):
        if not self.currentSelection:
            return
        return True if set(self.items(self.mousePos)) & set(self.selectionItems) else False

    def mousePressEvent(self, event):
        self.mousePos = event.scenePos()
        if event.buttons() == QtCore.Qt.LeftButton:
            if self.isOverSelection():
                self.moveRangePrev = 0
                start = self.currentSelection[0].index
                self.moveRangeNext = end = self.currentSelection[-1].index
                for keyFrame in self.keyFrames:
                    if keyFrame.index < start:
                        self.moveRangePrev = keyFrame.index
                    elif keyFrame.index > end:
                        self.moveRangeNext = keyFrame.index
                        break
                    else:
                        self.moveRangeNext = 64
            else:
                item = self.itemAt(self.mousePos)
                if not self.highlightedItem:
                    if isinstance(item, PreviewWaveItem):
                        self.highlightedItem = item
                        item.setHighlighted(True)
                    elif isinstance(item, VirtualSlice):
#                        keyFrame = self.keyFrames.get(item.index)
                        waveItem = self.keyFrameItems.get(self.keyFrames.get(item.index))
                        if waveItem:
                            self.highlightedItem = waveItem
                            waveItem.setHighlighted(True)
#                    elif item == self.front:
#                        self.highlightedItem = self.keyFrameItems.get(self.keyFrames[0])
#                        self.highlightedItem.setHighlighted(True)
                print(item, self.highlightedItem)
                if self.highlightedItem:
                    if self.currentSelection:
                        self.clearSelection()
                        self.currentSelection = []
                    if self.highlightedItem.keyFrame.index:
                        self.moveRangePrev = 0
                        self.moveRangeNext = current = self.highlightedItem.keyFrame.index
                        for keyFrame in self.keyFrames:
                            if keyFrame.index < current:
                                self.moveRangePrev = keyFrame.index
                            elif keyFrame.index > current:
                                self.moveRangeNext = keyFrame.index
                                break
                        else:
                            self.moveRangeNext = 64
                    else:
                        self.moveRangePrev = self.moveRangeNext = 0
                    if self.moveRangeNext - self.moveRangePrev > 2:
                        self.view.setCursor(QtCore.Qt.SizeBDiagCursor)
                elif event.modifiers() == QtCore.Qt.ShiftModifier:
                    self.view.setDragMode(self.view.RubberBandDrag)
                elif self.sliceEditItem.contains(self.mousePos):
                    pass
                else:
                    self.clearSliceSelection()
                    self.currentSelection = []
        QtWidgets.QGraphicsScene.mousePressEvent(self, event)

    def mouseDoubleClickEvent(self, event):
        if self.highlightedItem:
            self.waveDoubleClicked.emit(self.highlightedItem.keyFrame)

    def mouseMoveEvent(self, event):
        if event.buttons() == QtCore.Qt.LeftButton:
            if self.currentSelection:
                prevValidIndex = self.moveRangePrev + 1
                nextValidIndex = self.moveRangeNext - 1
                firstIndex = self.currentSelection[0].index
                lastIndex = self.currentSelection[-1].index
                if prevValidIndex < firstIndex or nextValidIndex > lastIndex and not self.keyFrames[0] in self.currentSelection:
                    newPos = event.scenePos() - self.mousePos
                    median = firstIndex + (lastIndex - firstIndex) * .5
                    avg = int(median + (newPos.x() / self.xRatio - newPos.y() / self.yRatio) * .5)
                    count = lastIndex - firstIndex + 1
                    self.newIndex = newStartIndex = sanitize(prevValidIndex, int(avg - count * .5), nextValidIndex - count + 1)
                    self.setSliceSelection(newStartIndex, newStartIndex + count - 1)
                    delta = newStartIndex - firstIndex
                    for keyFrame in self.currentSelection:
                        item = self.keyFrameItems[keyFrame]
                        item.setPos(self.front.x() + (item.index + delta) * self.xRatio, 
                            self.front.y() - (item.index + delta) * self.yRatio)
            elif self.highlightedItem:
                if self.moveRangeNext - self.moveRangePrev > 2:
                    newPos = event.scenePos() - self.mousePos
                    avg = self.highlightedItem.keyFrame.index + (newPos.x() / self.xRatio - newPos.y() / self.yRatio) * .5
                    self.newIndex = newIndex = max(self.moveRangePrev + 1, min(int(avg), self.moveRangeNext - 1))
                    self.highlightedItem.setPos(self.front.x() + newIndex * self.xRatio, 
                        self.front.y() - newIndex * self.yRatio)
                    self.sliceItem.setPos(self.highlightedItem.pos())
                    self.sliceIdItem.setIndex(newIndex)
                    self.sliceIdItem.setPos(self.highlightedItem.pos())
                    self.sliceIdItem.setY(
                        self.sliceIdItem.y() - self.view.mapToScene(self.sliceIdItem.boundingRect().toRect()).boundingRect().height() * 1.25)
        else:
            item = self.itemAt(event.scenePos())
            if not isinstance(item, PreviewWaveItem):
                if self.highlightedItem and event.scenePos() not in self.sliceItem.sceneBoundingRect():
                    self.highlightedItem.setHighlighted(False)
                    self.highlightedItem = None
                if not self.highlightedItem and isinstance(item, VirtualSlice):
                    keyFrame = self.keyFrames.get(item.index)
                    self.highlight.emit(keyFrame if keyFrame else item.index)
                elif event.scenePos() in self.back.sceneBoundingRect():
                    self.highlight.emit(63)
                else:
                    for item in self.items(event.scenePos()):
                        if isinstance(item, VirtualSlice):
                            self.highlight.emit(item.index)
                            break
                    else:
                        if event.scenePos() in self.front.sceneBoundingRect():
                            self.highlight.emit(0)
            else:
                if self.highlightedItem != item:
                    self.highlight.emit(item.keyFrame)
        QtWidgets.QGraphicsScene.mouseMoveEvent(self, event)

    def mouseReleaseEvent(self, event):
        if self.newIndex is not None:
            if self.currentSelection:
                self.moveKeyFramesRequested.emit(self.currentSelection, self.newIndex)
            else:
                self.moveKeyFramesRequested.emit([self.highlightedItem.keyFrame], self.newIndex)
    #            self.highlightedItem.keyFrame.setIndex(self.newIndex)
                self.highlight.emit(self.newIndex)
            self.newIndex = None
        elif self.view.dragMode() == self.view.NoDrag:
            self.clearSelection()
            self.currentSelection = []
        self.view.unsetCursor()
        self.view.setDragMode(self.view.NoDrag)
        QtWidgets.QGraphicsScene.mouseReleaseEvent(self, event)

    def keyFrameSceneSelectionChanged(self):
        self.currentSelection = sorted(self.keyFrameScene.selectedItems(), key=lambda k: k.index)
        if self.currentSelection:
            indexes = [k.index for k in self.currentSelection]
            self.setSliceSelection(min(indexes), max(indexes))
        else:
            self.clearSliceSelection()

    def clearSliceSelection(self):
        self.selectStart.setVisible(False)
        self.selectEnd.setVisible(False)
        self.selectTop.setVisible(False)
        self.selectRight.setVisible(False)
        self.selectBottom.setVisible(False)
        self.selectLeft.setVisible(False)
        self.sliceIdItem.setVisible(False)

    def setSliceSelection(self, start, end):
        if None in (start, end):
            self.clearSliceSelection()
            return
        topLeftStart = QtCore.QPointF(self.front.x() + start * self.xRatio, self.front.y() - start * self.yRatio)
        self.selectStart.setPos(topLeftStart)
        self.selectStart.setVisible(True)
        if start == end:
            self.selectStart.setBrush(self.cubeSelectFrontBrush)
            self.selectEnd.setVisible(False)
            self.selectTop.setVisible(False)
            self.selectRight.setVisible(False)
            self.selectBottom.setVisible(False)
            self.selectLeft.setVisible(False)
            self.sliceIdItem.setIndex(start)
            self.sliceIdItem.setPos(self.selectStart.pos())
            self.sliceIdItem.setY(
                self.sliceIdItem.y() - self.view.mapToScene(self.sliceIdItem.boundingRect().toRect()).boundingRect().height() * 1.25)
        else:
            self.selectStart.setBrush(self.cubeSelectNoBrush)
            topLeftEnd = QtCore.QPointF(self.front.x() + end * self.xRatio, self.front.y() - end * self.yRatio)
            self.selectEnd.setPos(topLeftEnd)
            self.selectEnd.setVisible(True)
            startPoly = self.selectReference.translated(start * self.xRatio, -start * self.yRatio)
            startPoints = polyPoints(*[startPoly.at(p) for p in range(4)])
            endPoly = self.selectReference.translated(end * self.xRatio, -end * self.yRatio)
            endPoints = polyPoints(*[endPoly.at(p) for p in range(4)])
            self.selectTop.setPolygon(QtGui.QPolygonF([startPoints.topLeft, endPoints.topLeft, endPoints.topRight, startPoints.topRight]))
            self.selectTop.setVisible(True)
            self.selectRight.setPolygon(QtGui.QPolygonF([startPoints.topRight, endPoints.topRight, endPoints.bottomRight, startPoints.bottomRight]))
            self.selectRight.setVisible(True)
            self.selectBottom.setPolygon(QtGui.QPolygonF([startPoints.bottomLeft, endPoints.bottomLeft, endPoints.bottomRight, startPoints.bottomRight]))
            self.selectBottom.setVisible(True)
            self.selectLeft.setPolygon(QtGui.QPolygonF([startPoints.topLeft, endPoints.topLeft, endPoints.bottomLeft, startPoints.bottomLeft]))
            self.selectLeft.setVisible(True)
            self.sliceIdItem.setIndex(start, end)
            self.sliceIdItem.setPos(self.selectEnd.pos())
            refRect = self.view.mapToScene(self.sliceIdItem.boundingRect().toRect()).boundingRect()
            self.sliceIdItem.setX(
                self.sliceIdItem.x() - refRect.width() * 1.25)

        self.sliceIdItem.setVisible(True)
        self.view.viewport().update()

    def checkSelection(self):
        selectedIndexes = []
        self.currentSelection = []
        selectionArea = self.selectionArea()
        for item in self.items(selectionArea):
            if isinstance(item, (VirtualSlice, EdgeVirtualSlice)) and self.keyFrames.fullList[item.index]:
                selectedIndexes.append(item.index)
                self.currentSelection.append(self.keyFrames.fullList[item.index])
        if not selectedIndexes:
            self.clearSliceSelection()
            return
        self.keyFrameScene.selectionChanged.disconnect(self.keyFrameSceneSelectionChanged)
        [w.setSelected(w in self.currentSelection) for w in self.keyFrames]
        self.keyFrameScene.selectionChanged.connect(self.keyFrameSceneSelectionChanged)
        self.currentSelection.sort(key=lambda item: item.index)
        self.setSliceSelection(min(selectedIndexes), max(selectedIndexes))

    def contextMenuEvent(self, event):
        keyFrame = index = None
        if self.highlightedItem:
            keyFrame = self.highlightedItem.keyFrame
            index = keyFrame.index
        elif isinstance(self.itemAt(event.scenePos()), VirtualSlice):
            index = self.itemAt(event.scenePos()).index
        else:
            for item in self.items(event.scenePos()):
                if isinstance(item, VirtualSlice):
                    index = item.index
                    break
            else:
                if event.scenePos() in self.back.sceneBoundingRect():
                    index = 63
                else:
                    return
        if not keyFrame:
            keyFrame = self.keyFrames.get(index)
        menu = QtWidgets.QMenu()
        clipboardValid = QtWidgets.QApplication.clipboard().mimeData().hasFormat('bigglesworth/WaveValues')
        editAction = newAction = insertBeforeAction = insertAfterAction = pasteAction = deleteSelectedAction = copyVirtualAction = False
        if keyFrame:
            editAction = menu.addAction(QtGui.QIcon.fromTheme('document-edit'), 'Edit wave {}'.format(keyFrame.index + 1))
            menu.addSeparator()
            if len(self.keyFrames) < 64:
                newAction = menu.addAction(QtGui.QIcon.fromTheme('arrow-left'), 'Insert wave before')
                newAction.setData((index - 1, False))
                if clipboardValid:
                    insertBeforeAction = menu.addAction(QtGui.QIcon.fromTheme('edit-paste'), 'Paste wave before')
                    insertBeforeAction.setData((index - 1, True))
            if not keyFrame.final and not self.keyFrames.get(index + 1):
                insertAfterAction = menu.addAction(QtGui.QIcon.fromTheme('arrow-right'), 'Insert wave after')
                insertAfterAction.setData((index + 1, False))
                if clipboardValid:
                    pasteAction = menu.addAction(QtGui.QIcon.fromTheme('edit-paste'), 'Paste wave after')
                    pasteAction.setData((index + 1, True))
            if not menu.actions()[-1].isSeparator():
                menu.addSeparator()
            menu.addActions(keyFrame.actions())
        else:
            newAction = menu.addAction(QtGui.QIcon.fromTheme('document-new'), 'Create wave at index {}'.format(index + 1))
            if clipboardValid:
                pasteAction = menu.addAction(QtGui.QIcon.fromTheme('edit-paste'), 'Paste wave values at index {}'.format(index + 1))
                pasteAction.setData((index, True))
            if self.keyFrames.previous(index).nextTransform:
                transform = self.keyFrames.previous(index).nextTransform
                if transform.isValid():
                    text = 'Morph from {} to '.format(transform.prevItem.index + 1)
                    if transform.nextItem != self.keyFrames[0]:
                        text += '{}'.format(transform.nextItem.index + 1)
                    else:
                        text += 'table beginning'
                    menu.addSection(text)
                else:
                    menu.addSeparator()
                menu.addActions(self.keyFrames.previous(index).nextTransform.actions())
                copyVirtualAction = menu.addAction(QtGui.QIcon.fromTheme('edit-copy'), 'Copy computed values at index {}'.format(index + 1))
        if self.isOverSelection() and len(self.currentSelection) > 1:
            if not menu.actions()[-1].isSeparator():
                menu.addSeparator()
            deleteSelectedAction = menu.addAction(QtGui.QIcon.fromTheme('edit-delete'), 'Remove {} selected waves'.format(len(self.currentSelection)))

        res = menu.exec_(QtGui.QCursor.pos())
        if not res:
            return
        elif res == editAction:
            self.waveDoubleClicked.emit(keyFrame)
        elif res == newAction:
            self.createKeyFrameRequested.emit(index, None, False)
        elif res == deleteSelectedAction:
            self.deleteRequested.emit(self.currentSelection)
        elif res == copyVirtualAction:
            self.copyVirtualRequested.emit(index)
        elif res.data():
            if res.parent() == menu:
                index, useClipboard = res.data()
                if useClipboard:
                    byteArray = QtWidgets.QApplication.clipboard().mimeData().data('bigglesworth/WaveValues')
                    stream = QtCore.QDataStream(byteArray)
                    values = stream.readQVariant()
                else:
                    values = None
                self.createKeyFrameRequested.emit(index, values, False)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat('bigglesworth/WaveFileData'):
            event.accept()
            return
        QtWidgets.QGraphicsScene.dragEnterEvent(self, event)

    def dragLeaveEvent(self, event):
        self.selectStart.setVisible(False)
        self.selectEnd.setVisible(False)
        self.selectTop.setVisible(False)
        self.selectRight.setVisible(False)
        self.selectBottom.setVisible(False)
        self.selectLeft.setVisible(False)
        self.sliceIdItem.setVisible(False)
        return QtWidgets.QGraphicsScene.dragLeaveEvent(self, event)

    def dragMoveEvent(self, event):
        if not event.mimeData().hasFormat('bigglesworth/WaveFileData'):
            self.clearSliceSelection()
            [i.setWriting(False) for i in self.keyFrameItems.values()]
            return QtWidgets.QGraphicsScene.dragMoveEvent(self, event)
        item = self.itemAt(event.scenePos())
        index = None
        if isinstance(item, VirtualSlice):
            index = item.index
        elif item == self.front:
            index = 0
        elif item == self.back:
            index = 63
        if index is None:
            self.clearSliceSelection()
            [i.setWriting(False) for i in self.keyFrameItems.values()]
            return QtWidgets.QGraphicsScene.dragMoveEvent(self, event)
        byteArray = QtCore.QByteArray(event.mimeData().data('bigglesworth/WaveFileData'))
        stream = QtCore.QDataStream(byteArray)
        #read window uuid and tab
        [stream.readQVariant(), stream.readInt()]
        count = stream.readInt()
        start = sanitize(0, index - (count - 1) / 2, 64 - count)
        end = min(63, start + count - 1)
        self.setSliceSelection(start, end)
#        topLeftStart = QtCore.QPointF(self.front.x() + start * self.xRatio, self.front.y() - start * self.yRatio)
#        self.selectStart.setPos(topLeftStart)
#        self.selectStart.setVisible(True)
#        if count == 1:
#            self.selectStart.setBrush(self.cubeSelectFrontBrush)
#            self.selectEnd.setVisible(False)
#            self.selectTop.setVisible(False)
#            self.selectRight.setVisible(False)
#            self.selectBottom.setVisible(False)
#            self.selectLeft.setVisible(False)
#
#            self.sliceIdItem.setText(str(start + 1))
#            self.sliceIdItem.setPos(self.selectStart.pos())
#            self.sliceIdItem.setY(
#                self.sliceIdItem.y() - self.view.mapToScene(self.sliceIdItem.boundingRect().toRect()).boundingRect().height() * 1.25)
#        else:
#            self.selectStart.setBrush(self.cubeSelectNoBrush)
#            topLeftEnd = QtCore.QPointF(self.front.x() + end * self.xRatio, self.front.y() - end * self.yRatio)
#            self.selectEnd.setPos(topLeftEnd)
#            self.selectEnd.setVisible(True)
#            startPoly = self.selectReference.translated(start * self.xRatio, -start * self.yRatio)
#            startPoints = polyPoints(*[startPoly.at(p) for p in range(4)])
#            endPoly = self.selectReference.translated(end * self.xRatio, -end * self.yRatio)
#            endPoints = polyPoints(*[endPoly.at(p) for p in range(4)])
#            self.selectTop.setPolygon(QtGui.QPolygonF([startPoints.topLeft, endPoints.topLeft, endPoints.topRight, startPoints.topRight]))
#            self.selectTop.setVisible(True)
#            self.selectRight.setPolygon(QtGui.QPolygonF([startPoints.topRight, endPoints.topRight, endPoints.bottomRight, startPoints.bottomRight]))
#            self.selectRight.setVisible(True)
#            self.selectBottom.setPolygon(QtGui.QPolygonF([startPoints.bottomLeft, endPoints.bottomLeft, endPoints.bottomRight, startPoints.bottomRight]))
#            self.selectBottom.setVisible(True)
#            self.selectLeft.setPolygon(QtGui.QPolygonF([startPoints.topLeft, endPoints.topLeft, endPoints.bottomLeft, startPoints.bottomLeft]))
#            self.selectLeft.setVisible(True)
#
#            self.sliceIdItem.setText('{}-{}'.format(start + 1, end + 1))
#            self.sliceIdItem.setPos(self.selectEnd.pos())
#            refRect = self.view.mapToScene(self.sliceIdItem.boundingRect().toRect()).boundingRect()
#            self.sliceIdItem.setX(
#                self.sliceIdItem.x() - refRect.width() * 1.25)

        indexRange = range(start, end)
        for keyFrame, keyFrameItem in self.keyFrameItems.items():
            keyFrameItem.setWriting(keyFrame.index in indexRange)
#        self.sliceIdItem.setVisible(True)

        self.pasteStart = start
        event.accept()

    def dropEvent(self, event):
        if event.mimeData().hasFormat('bigglesworth/WaveFileData'):
            byteArray = QtCore.QByteArray(event.mimeData().data('bigglesworth/WaveFileData'))
            stream = QtCore.QDataStream(byteArray)
            #read window uuid and tab
            [stream.readQVariant(), stream.readInt()]
            count = stream.readInt()
            self.waveDrop.emit(self.pasteStart, [stream.readQVariant() for _ in range(count)], stream.readQVariant())
#            self.genericDraw.emit(self.Drop, self.currentKeyFrame, map(lambda v: sanitize(-pow20, v, pow20), stream.readQVariant() * pow20))
            self.selectStart.setVisible(False)
            self.selectEnd.setVisible(False)
            self.selectTop.setVisible(False)
            self.selectRight.setVisible(False)
            self.selectBottom.setVisible(False)
            self.selectLeft.setVisible(False)


