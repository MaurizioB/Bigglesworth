#!/usr/bin/env python3

from __future__ import division
import os
import json

os.environ['QT_PREFERRED_BINDING'] = 'PyQt4'
from Qt import QtCore, QtGui, QtWidgets
import metawidget

#from metawidget import BaseWidget, _getCssQColorStr, _getCssQFontStr, makeQtChildProperty

try:
    range = xrange
except:
    pass

with open(os.path.join(os.path.dirname(__file__), 'pianokbmap.json'), 'r') as jsf:
    _localeData = json.loads(jsf.read())

_layoutCountries = {}

emptyKeys = {0: {}, 1: {}, 2: {}, 3: {}}

for _country, _mappings in _localeData.items():
    for _symbolName, _layout in _mappings.items():
        mapping = {'include': _layout.get('include', []), 'keys': _layout.get('keys', emptyKeys.copy()), 'symbolName': _layout.get('symbolName', _symbolName)}
        name = _layout.get('name', _symbolName)
        mapping['name'] = name
        if _symbolName == 'basic':
            try:
                _layoutCountries[_country][0] = _symbolName
                _layoutCountries[_country][1][_symbolName] = mapping
            except:
                _layoutCountries[_country] = [_symbolName, {_symbolName: mapping}]
        else:
            try:
                _layoutCountries[_country][1][_symbolName] = mapping
            except:
                _layoutCountries[_country] = [_symbolName, {_symbolName: mapping}]


_layouts = {
    'it': (
        u'z', u's', u'x', u'd', u'c', u'v', u'g', u'b', u'h', u'n', u'j', u'm', 
        u',', u'l', u'.', u'\xf2', u'-', u'q', u'2', u'w', u'3', u'e', u'4', u'r', 
        u't', u'6', u'y', u'7', u'u', u'i', u'9', u'o', u'0', u'p', u"'", u'\xe8', 
        )
    }

_layout1 = [
    (0, 0), (1, 1), (0, 1), (1, 2), (0, 2), (0, 3), (1, 4), (0, 4), (1, 5), (0, 5), (1, 6), (0, 6)
    ]

_layout2 = _layout1 + [
    (2, 0), (3, 1), (2, 1), (3, 2), (2, 2), (2, 3), (3, 4), (2, 4), (3, 5), (2, 5), (3, 6), (2, 6)
    ]

_layout3 = _layout1 + [
    (0, 7), (1, 8), (0, 8), (1, 9), (0, 9), (2, 0), (3, 1), (2, 1), (3, 2), (2, 2), (3, 3), (2, 3), 
    (2, 4), (3, 5), (2, 5), (3, 6), (2, 6), (2, 7), (3, 8), (2, 8), (3, 9), (2, 9), (3, 10), (2, 10), 
    ]

_noteNames = ['c', 'c#', 'd', 'd#', 'e', 'f', 'f#', 'g', 'g#', 'a', 'a#', 'b']
_noteAliases = {
    'c': ('b#', -1),
    'c#': ('db', 0),
    'd#': ('eb', 0),
    'e': ('fb', 0), 
    'f': ('e#', 0),
    'f#': ('gb', 0),
    'g#': ('ab', 0),
    'a#': ('bb', 0),
    'b': ('cb', 1), 
    }
_whiteKeys = (0, 2, 4, 5, 7, 9, 11)
_noteNumberToName = {}
_noteNameToNumber = {}

for _noteId in range(128):
    _octave, _note = divmod(_noteId, 12)
    _noteName = _noteNames[_note]
    _fullNoteName = '{}{}'.format(_noteName, -2 + _octave)
    _noteNumberToName[_noteId] = _fullNoteName
    _noteNameToNumber[_fullNoteName] = _noteId
    try:
        _alias, _offset = _noteAliases[_noteName]
        _noteNameToNumber['{}{}'.format(_alias, -2 + _octave + _offset)] = _noteId
    except:
        pass

def _isWhiteKey(noteId):
    return True if noteId % 12 in _whiteKeys else False


class MetaKey(QtWidgets.QGraphicsItem):
    x = 0
    width = 18
    height = 100
    pressed = 0
    keyBrush = QtCore.Qt.white

    def __init__(self, note):
        QtWidgets.QGraphicsItem.__init__(self, parent=None)
        self.note = note
        self.noteName = _noteNumberToName[note]
        self.setToolTip(self.noteName.upper())
        self._shortcut = ''
        self.shortcutPaintFunc = lambda *args: None

    @property
    def shortcut(self):
        return self._shortcut

    @shortcut.setter
    def shortcut(self, shortcut):
        self._shortcut = shortcut
        self.shortcutPaintFunc = self.shortcutPaint if shortcut else lambda *args: None

    def emitNoteEvent(self, velocity, state):
        if velocity < 0:
            velocity = 0
        elif velocity > 127:
            velocity = 127
        self.scene().noteEvent.emit(state, self.note, velocity)

    def mousePressEvent(self, event):
        self.emitNoteEvent(int(round(event.pos().y() * 127 / self.height, 0)), True)
        self.pressed = 1
        self.update()

    def mouseReleaseEvent(self, event):
        self.emitNoteEvent(int(round(event.pos().y() * 127 / self.height, 0)), False)
        self.pressed = 0
        try:
            self.ungrabMouse()
        except:
            pass
        self.update()

    def mouseMoveEvent(self, event):
        item = self.scene().itemAt(self.mapToScene(event.pos()))
        if item == self:
            if not self.pressed:
                self.mousePressEvent(event)
        elif item is None:
            if self.pressed:
                self.mouseReleaseEvent(event)
                self.grabMouse()
        else:
            self.mouseReleaseEvent(event)
            if isinstance(item, QtWidgets.QGraphicsItem):
                item.mousePressEvent(event)
                item.grabMouse()

    def boundingRect(self):
        return QtCore.QRectF(0, 0, self.x + self.width, self.height)


class WhiteKey(MetaKey):
    pressedShadow = QtGui.QPolygon([
        QtCore.QPoint(.5, 2), 
        QtCore.QPoint(.5, 98), 
        QtCore.QPoint(5, 98), 
        QtCore.QPoint(1.5, 2), 
        ])
    pressedShadowGradient = QtGui.QLinearGradient(0, 0, 1, 0)
    pressedShadowGradient.setCoordinateMode(pressedShadowGradient.ObjectBoundingMode)
    pressedShadowGradient.setColorAt(0, QtGui.QColor(64, 64, 64, 192))
    pressedShadowGradient.setColorAt(.8, QtGui.QColor(192, 192, 192, 192))
    pressedShadowGradient.setColorAt(1, QtGui.QColor(255, 255, 255, 192))
    pressedShadowPen = QtGui.QPen(QtGui.QColor(192, 192, 192, 128), 4)
#    pressedShadowBrush = QtGui.QColor(192, 192, 192, 192)
    pressedShadowBrush = pressedShadowGradient

    def __init__(self, *args, **kwargs):
        MetaKey.__init__(self, *args, **kwargs)
        self.pressedPaintFunction = lambda qp: None
        if not self.note % 12:
            self.paintCFunc = lambda qp: self.paintC(qp, 'C{}'.format(self.note // 12 - 2))
        else:
            self.paintCFunc = lambda *args: None
        self._prevBlack = None
        self.prevWhite = None
#        self.prevBlackShadow = lambda: None

    @property
    def prevBlack(self):
        return self._prevBlack

    @prevBlack.setter
    def prevBlack(self, key):
        self._prevBlack = key
#        self.prevBlackShadow = key.update

    def mousePressEvent(self, event):
        self.pressedPaintFunction = self.pressedPaint
        if self._prevBlack:
            self.prevBlack.setWhiteShadow(True)
        MetaKey.mousePressEvent(self, event)

    def mouseReleaseEvent(self, event):
        self.pressedPaintFunction = lambda qp: None
        if self._prevBlack:
            self.prevBlack.setWhiteShadow(False)
        MetaKey.mouseReleaseEvent(self, event)

    def triggerNoteEvent(self, eventType, velocity):
        if eventType and velocity == 0:
            eventType = False
        if eventType:
            self.pressedPaintFunction = self.pressedPaint
            if self._prevBlack:
                self.prevBlack.setWhiteShadow(True)
            self.pressed = 1
            self.emitNoteEvent(velocity, True)
            self.update()
        else:
            self.pressedPaintFunction = lambda qp: None
            self.pressed = 0
            if self._prevBlack:
                self.prevBlack.setWhiteShadow(False)
            self.emitNoteEvent(velocity, False)
            self.update()
            if self.scene().mouseGrabberItem() == self:
                self.ungrabMouse()

    def paint(self, qp, *args, **kwargs):
#        self.prevBlackShadow()
        qp.translate(.5, .5)
        qp.setRenderHints(QtGui.QPainter.Antialiasing)
        qp.setPen(QtCore.Qt.darkGray)
        qp.setBrush(self.keyBrush)
        qp.drawRoundedRect(self.x, 0, self.width, self.height - 1.1 + self.pressed, 1, 1)
        self.pressedPaintFunction(qp)
        self.paintCFunc(qp)
        self.shortcutPaintFunc(qp)

    def shortcutPaint(self, qp):
        qp.setPen(QtCore.Qt.black)
        xScale = 1 / qp.transform().m11()
        yScale = 1 / qp.transform().m22()
        qp.save()
        font = qp.font()
        font.setPointSize(int(font.pointSize() / max(xScale, yScale)) + 2)
        font.setBold(True)
        qp.setFont(font)
        qp.scale(xScale, yScale)
        qp.drawText(self.x, 0, self.width / xScale, (self.height - 1) / yScale - 20 / yScale, QtCore.Qt.AlignHCenter|QtCore.Qt.AlignBottom, self.shortcut)
        qp.restore()

    def pressedPaint(self, qp):
        if not self.prevWhite or self.prevWhite.pressed:
            return
        qp.setPen(self.pressedShadowPen)
        qp.setBrush(self.pressedShadowBrush)
        qp.drawPolygon(self.pressedShadow)

    def paintC(self, qp, label):
        qp.setPen(QtCore.Qt.darkGray)
        xScale = 1 / qp.transform().m11()
        yScale = 1 / qp.transform().m22()
        qp.save()
        font = qp.font()
        font.setPointSize(int(font.pointSize() / max(xScale, yScale)) + 2)
        qp.setFont(font)
        qp.scale(xScale, yScale)
        qp.drawText(self.x, self.y(), self.width / xScale, (self.height - 1) / yScale - 1 / yScale, QtCore.Qt.AlignHCenter|QtCore.Qt.AlignBottom, label)
        qp.restore()


class BlackKey(MetaKey):
    height = int(MetaKey.height * .6)
    bottomHeight = 8
    topHeight = height - bottomHeight
    width = int(MetaKey.width * .75)
    keyBodyNormal = QtGui.QLinearGradient(0, 0, 0, 1)
    keyBodyNormal.setCoordinateMode(keyBodyNormal.ObjectBoundingMode)
    keyBodyNormal.setColorAt(0, QtGui.QColor(24, 24, 24))
    keyBodyNormal.setColorAt(.4, QtGui.QColor(48, 40, 40))
    keyBodyNormal.setColorAt(.5, QtGui.QColor(48, 40, 40))
    keyBodyNormal.setColorAt(1, QtGui.QColor(24, 24, 24))
    keyBodyPressed = QtGui.QLinearGradient(0, 0, 0, 1)
    keyBodyPressed.setCoordinateMode(keyBodyPressed.ObjectBoundingMode)
    keyBodyPressed.setColorAt(0, QtGui.QColor(48, 48, 48))
    keyBodyPressed.setColorAt(.4, QtGui.QColor(72, 64, 64))
    keyBodyPressed.setColorAt(.5, QtGui.QColor(72, 64, 64))
    keyBodyPressed.setColorAt(1, QtGui.QColor(48, 48, 48))

    leftBorder = QtGui.QPolygon([
        QtCore.QPoint(.5, .5), 
        QtCore.QPoint(.5, height), 
        QtCore.QPoint(1, height), 
        QtCore.QPoint(1, .5), 
        ])

    rightBorderLeft = width - 1
    rightBorderRight = width - .5
    rightBorder = QtGui.QPolygon([
        QtCore.QPoint(rightBorderLeft, .5), 
        QtCore.QPoint(rightBorderLeft, height), 
        QtCore.QPoint(rightBorderRight, height), 
        QtCore.QPoint(rightBorderRight, .5), 
        ])

    shadowPen = QtGui.QColor(200, 200, 200, 160)
    shadowWhiteNormalBrush = QtGui.QLinearGradient(0, 0, 0, 1)
    shadowWhiteNormalBrush.setCoordinateMode(shadowWhiteNormalBrush.ObjectBoundingMode)
    shadowWhiteNormalBrush.setColorAt(0, QtGui.QColor(48, 48, 48, 92))
    shadowWhiteNormalBrush.setColorAt(.2, QtGui.QColor(64, 64, 64, 128))
    shadowWhiteNormalBrush.setColorAt(1, QtGui.QColor(128, 128, 128, 128))
    shadowWhitePressedBrush = QtGui.QLinearGradient(0, 0, 0, 1)
    shadowWhitePressedBrush.setCoordinateMode(shadowWhitePressedBrush.ObjectBoundingMode)
    shadowWhitePressedBrush.setColorAt(0, QtGui.QColor(32, 32, 32, 92))
    shadowWhitePressedBrush.setColorAt(.2, QtGui.QColor(32, 32, 32, 128))
    shadowWhitePressedBrush.setColorAt(1, QtGui.QColor(96, 96, 96, 128))
    shadowBrushes = shadowWhiteNormalBrush, shadowWhitePressedBrush
    shadowBrush = shadowWhiteNormalBrush

    @classmethod
    def setRatio(cls, ratio):
        cls.height = int(MetaKey.height * ratio)
        cls.topHeight = cls.height - cls.bottomHeight

    def __init__(self, *args, **kwargs):
        MetaKey.__init__(self, *args, **kwargs)
        self.keyBody = self.keyBodyNormal
        self.shadowPaint = self.normalWhiteNormalShadowPaint
        self.bottomPaint = self.normalBottomPaint

    def setWhiteShadow(self, state):
        self.shadowBrush = self.shadowBrushes[state]
        self.shadowPaint = self.normalWhitePressedShadowPaint if state else self.normalWhiteNormalShadowPaint

    def mousePressEvent(self, event):
        self.keyBody = self.keyBodyPressed
        self.shadowPaint = self.pressedShadowPaint
        self.bottomPaint = self.pressedBottomPaint
        MetaKey.mousePressEvent(self, event)

    def mouseReleaseEvent(self, event):
        self.keyBody = self.keyBodyNormal
        self.shadowPaint = self.normalWhiteNormalShadowPaint
        self.bottomPaint = self.normalBottomPaint
        MetaKey.mouseReleaseEvent(self, event)

    def triggerNoteEvent(self, eventType, velocity):
        if eventType and velocity == 0:
            eventType = False
        if eventType:
            self.keyBody = self.keyBodyPressed
            self.shadowPaint = self.pressedShadowPaint
            self.bottomPaint = self.pressedBottomPaint
            self.pressed = 1
            self.emitNoteEvent(velocity, True)
            self.update()
        else:
            self.keyBody = self.keyBodyNormal
            self.shadowPaint = self.normalWhiteNormalShadowPaint
            self.bottomPaint = self.normalBottomPaint
            self.pressed = 0
            self.emitNoteEvent(velocity, False)
            self.update()
            if self.scene().mouseGrabberItem() == self:
                self.ungrabMouse()

    def paint(self, qp, *args, **kwargs):
        qp.translate(.5, .5)
        qp.setRenderHints(QtGui.QPainter.Antialiasing)
        qp.setPen(self.shadowPen)
        qp.setBrush(self.shadowBrush)
        self.shadowPaint(qp)
        qp.setPen(QtCore.Qt.NoPen)
        qp.setBrush(self.keyBody)
        qp.drawRoundedRect(self.x, 0, self.width, self.height, 1, 1)
        qp.setBrush(QtCore.Qt.darkGray)
        qp.drawPolygon(self.leftBorder)
        qp.setPen(QtCore.Qt.black)
        qp.drawPolygon(self.rightBorder)
        self.bottomPaint(qp)
        self.shortcutPaintFunc(qp)

    def shortcutPaint(self, qp):
        qp.setPen(QtCore.Qt.white)
        xScale = 1 / qp.transform().m11()
        yScale = 1 / qp.transform().m22()
        qp.save()
        font = qp.font()
        font.setPointSize(int(font.pointSize() / max(xScale, yScale)) + 2)
        font.setBold(True)
        qp.setFont(font)
        qp.scale(xScale, yScale)
        qp.drawText(self.x, 0, self.width / xScale, (self.height - 1) / yScale - 20 / yScale, QtCore.Qt.AlignHCenter|QtCore.Qt.AlignBottom, self.shortcut)
        qp.restore()

    def normalWhiteNormalShadowPaint(self, qp):
        qp.drawRoundedRect(self.x + 1, 0, self.width + 2, self.height + 1, 2, 2)

    def normalWhitePressedShadowPaint(self, qp):
        qp.save()
        qp.translate(.5, .2)
        qp.drawRoundedRect(self.x + 1, 0, self.width + 2, self.height + 1, 2, 2)
        qp.restore()

    def pressedShadowPaint(self, qp):
        qp.drawRoundedRect(self.x + 1, 0, self.width + 1, self.height + 1, 2, 2)
        self.nextWhite.update()

    def pressedBottomPaint(self, qp):
        qp.setPen(QtCore.Qt.NoPen)
        qp.setBrush(QtCore.Qt.black)
        qp.drawRoundedRect(self.x + 1, self.topHeight + 2, self.width - 2, self.bottomHeight - 2, 1, 1)

    def normalBottomPaint(self, qp):
        qp.setPen(QtCore.Qt.NoPen)
        qp.setBrush(QtCore.Qt.black)
        qp.drawRoundedRect(self.x + 1, self.topHeight, self.width - 2, self.bottomHeight, 1, 1)


class TopShadow(QtWidgets.QGraphicsItem):
    width = 1
    height = 10
    gradient = QtGui.QLinearGradient(0, 0, 0, 1)
    gradient.setCoordinateMode(gradient.ObjectBoundingMode)
    gradient.setColorAt(0, QtGui.QColor(92, 92, 92, 192))
    gradient.setColorAt(1, QtGui.QColor(255, 255, 255, 0))
    def __init__(self, *args, **kwargs):
        QtWidgets.QGraphicsItem.__init__(self, *args, **kwargs)
        self.setAcceptedMouseButtons(QtCore.Qt.NoButton)

    def boundingRect(self):
        return QtCore.QRectF(0, 0, self.width, self.height)

    def paint(self, qp, *args, **kwargs):
        qp.translate(.5, .5)
        qp.setPen(QtCore.Qt.NoPen)
        qp.setBrush(self.gradient)
        qp.drawRect(self.boundingRect())


class PianoScene(QtWidgets.QGraphicsScene):
    noteEvent = QtCore.pyqtSignal(bool, int, int)


class PianoKeyboard(QtWidgets.QGraphicsView):
    noteEvent = QtCore.pyqtSignal(bool, int, int)
    def __init__(self, parent=None):
        QtWidgets.QGraphicsView.__init__(self, parent)
        self.setBackgroundBrush(QtGui.QBrush(QtCore.Qt.NoBrush))
        palette = self.palette()
        palette.setColor(palette.Base, QtGui.QColor(QtCore.Qt.transparent))
        self.setPalette(palette)
        sizePolicy = self.sizePolicy()
        sizePolicy.setHeightForWidth(True)
        self.setSizePolicy(sizePolicy)
        self.pianoScene = PianoScene(self)
        self.pianoScene.noteEvent.connect(self.noteEvent)
        self.setScene(self.pianoScene)
        self.setFrameStyle(0)
        self._aspectRatio = QtCore.Qt.KeepAspectRatio
        self._blackKeyRatio = int(BlackKey.height / WhiteKey.height * 100)
        self._firstNote = 36
        self._lastNote = 96
        self._octaves = 5
        self._noteOffset = 1
        self._showShortcuts = True
        self._defaultVelocity = 127
        self.setKeyboard()
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
#        self.aspectRatio = QtCore.Qt.KeepAspectRatioByExpanding

    def heightForWidth(self, width):
        keyWidth = width / self._whiteKeysWidth
#        print(width, self._whiteKeysWidth, keyWidth, keyWidth * 5.55555555)
        return int(keyWidth * 5.55555555)
#        return QtWidgets.QGraphicsView.heightForWidth(self, width)

    def sizeHint(self):
        return QtCore.QSize(self.width(), self.heightForWidth(self.width()))


#    @QtCore.pyqtProperty(int)
#    def keyWidth(self):
#        return MetaKey.width
#
#    @keyWidth.setter
#    def keyWidth(self, width):
#        if width < 10:
#            width = 10
#        elif width > 50:
#            width = 50
#        MetaKey.width = width
#        self.update()

    @QtCore.pyqtProperty(QtCore.Qt.AspectRatioMode, doc='aoaoa')
    def aspectRatio(self):
        return self._aspectRatio

    @aspectRatio.setter
    def aspectRatio(self, aspectRatio):
        sizePolicy = self.sizePolicy()
        if aspectRatio == QtCore.Qt.KeepAspectRatioByExpanding:
            aspectRatio = QtCore.Qt.KeepAspectRatio
            sizePolicy.setHeightForWidth(True)
        elif aspectRatio == QtCore.Qt.KeepAspectRatio:
            sizePolicy.setHeightForWidth(True)
        else:
            sizePolicy.setHeightForWidth(False)
        self.setSizePolicy(sizePolicy)
        self._aspectRatio = aspectRatio
        QtWidgets.QApplication.postEvent(self, QtCore.QEvent(QtCore.QEvent.UpdateRequest))
        self.fitInView(1, 1, self._whiteKeysWidth * MetaKey.width - 1, 99, QtCore.Qt.IgnoreAspectRatio)

    @QtCore.pyqtProperty(int)
    def blackKeyRatio(self):
        return self._blackKeyRatio

    @blackKeyRatio.setter
    def blackKeyRatio(self, ratio):
        if ratio < 30:
            ratio = 30
        elif ratio > 100:
            ratio = 100
        self._blackKeyRatio = ratio
        BlackKey.setRatio(ratio / 100)
#        BlackKey.height = WhiteKey.height * ratio
        self.updateScene(self.pianoScene.sceneRect())

    @QtCore.pyqtProperty(int)
    def firstNote(self):
        return self._firstNote

    @firstNote.setter
    def firstNote(self, firstNote):
        if not _isWhiteKey(firstNote):
            firstNote -= 1
        if firstNote < 0:
            firstNote = 0
        elif firstNote > 127:
            firstNote = 127
        #TODO: check consistency!
        while firstNote + self._octaves * 12 + self._noteOffset > 127:
            if self._octaves > 0:
                self._octaves -= 1
            else:
                firstNote -= 1
        self._firstNote = firstNote
        self.noteOffset = self.noteOffset
        lastNote = firstNote + self._octaves * 12 + self._noteOffset
        if not _isWhiteKey(lastNote):
            self._noteOffset += -1 if not self._noteOffset <= 10 else 1
        self._lastNote = firstNote + self._octaves * 12 + self._noteOffset
        self.setKeyboard()

    @QtCore.pyqtProperty(int)
    def octaves(self):
        return self._octaves

    @octaves.setter
    def octaves(self, octaves):
        if octaves < 0:
            octaves = 0
        elif octaves > 10:
            octaves = 10
        lastNote = self._firstNote + octaves * 12 + self._noteOffset
        noteOffset = self._noteOffset
        while lastNote > 127:
            noteOffset = self._noteOffset - 1
            lastNote = self._firstNote + octaves * 12 + noteOffset
        if not _isWhiteKey(lastNote):
            noteOffset -= 1
        self._octaves = octaves
        self._noteOffset = noteOffset
        self._lastNote = self._firstNote + self._octaves * 12 + self._noteOffset
        self.setKeyboard()

    @QtCore.pyqtProperty(int)
    def noteOffset(self):
        return self._noteOffset

    @noteOffset.setter
    def noteOffset(self, noteOffset):
        if noteOffset > 11:
            noteOffset = 11
        elif noteOffset < -10:
            noteOffset = -10
        lastNote = self._firstNote + self._octaves * 12 - 1 + noteOffset
        if not _isWhiteKey(lastNote):
            #TODO: valuta un baseOffset?
            noteOffset += 1
        self._noteOffset = noteOffset
        self._lastNote = self._firstNote + self._octaves * 12 - 1 + noteOffset
        self.setKeyboard()

    @QtCore.pyqtProperty(bool)
    def showShortcuts(self):
        return self._showShortcuts

    @showShortcuts.setter
    def showShortcuts(self, show):
        self._showShortcuts = show
        self.setShortcuts()

    @QtCore.pyqtProperty(int)
    def defaultVelocity(self):
        return self._defaultVelocity

    @defaultVelocity.setter
    def defaultVelocity(self, velocity):
        if velocity < 0:
            velocity = 0
        elif velocity > 127:
            velocity = 127
        self._defaultVelocity = velocity

    def setKeyboard(self):
        self.keys = {}
        self.shortcuts = {}
        self.pianoScene.clear()
        whiteKeysWidth = 0
        self._keyRange = range(self._firstNote, self._lastNote + 1)
        for k in self._keyRange:
            if _isWhiteKey(k):
                key = WhiteKey(k)
                self.pianoScene.addItem(key)
                key.setPos(whiteKeysWidth * MetaKey.width, 0)
                whiteKeysWidth += 1
                try:
                    if not _isWhiteKey(k - 1):
                        prevBlack = self.keys[k - 1]
                        prevBlack.nextWhite = key
                        key.prevBlack = prevBlack
                        prevWhite = self.keys[k - 2]
                        key.prevWhite = prevWhite
                    elif k > 0:
                        prevWhite = self.keys[k - 1]
                        key.prevWhite = prevWhite
                except:
                    pass
            else:
                keyDelta = k % 12
                shift = 0
                if keyDelta in (1, 6):
                    shift = -2
                elif keyDelta in (3, 10):
                    shift = +2
                key = BlackKey(k)
                self.pianoScene.addItem(key)
                key.setZValue(2)
                key.setPos(whiteKeysWidth * MetaKey.width - BlackKey.width * .5 + shift, 0)
            self.keys[k] = key
        topShadow = TopShadow()
        topShadow.width = whiteKeysWidth * MetaKey.width
        self.pianoScene.addItem(topShadow)
        self._whiteKeysWidth = whiteKeysWidth
        self.setShortcuts()
        self.resizeEvent()

    def getMapping(self, country, symbolName=None):
        countryLayout = _layoutCountries.get(country, _layoutCountries['latin'])
        if symbolName is None or symbolName == country:
            symbolName = countryLayout[0]
        layouts = countryLayout[1]
        base = {0: {}, 1: {}, 2: {}, 3: {}}
        try:
            layout = layouts[symbolName]
            base['name'] = layouts[symbolName]['name']
        except Exception as e:
            layout = layouts['basic']
#            print(e, country, symbolName)
#            print(layoutCountries[country])
        for include in layout.get('include', []):
            includeSplit = include.split('.')
            includeCountry = includeSplit[0]
            try:
                includeLayout = includeSplit[1]
            except:
                includeLayout = 'basic'
            try:
                includeMap = self.getMapping(includeCountry, includeLayout)
                for row in range(4):
                    base[row].update({int(k):v for k, v in includeMap[row].items()})
            except:
                continue
        for row in range(4):
            try:
                base[row].update({int(k):v for k, v in layout['keys'][str(row)].items()})
            except:
                pass
        return base

    def setShortcuts(self):
        if self._showShortcuts:
            lang, country = QtWidgets.QApplication.keyboardInputLocale().name().split('_')
            country = country.lower()
            keyboardMapping = self.getMapping(country, lang)

            note = self._firstNote
            if self._octaves > 4:
                note += (self._octaves - 3) * 6
            while note % 12:
                note += 1

            #determine the first C and actual octave extension
            extension = self._lastNote - note + 1
            if extension >= 36:
                layout = _layout3
            elif extension >= 24:
                layout = _layout2
            else:
                layout = _layout1
            pianoMapping = [keyboardMapping[k[0]][k[1]] for k in layout]

            for shortcut in pianoMapping:
                try:
                    key = self.keys[note]
                    key.shortcut = shortcut.upper()
                    self.shortcuts[shortcut] = key
                    note += 1
                except:
                    break
        else:
            for key in self.keys.values():
                key.shortcut = ''
        self.pianoScene.update(self.pianoScene.sceneRect())

    @QtCore.pyqtSlot(bool, int)
    @QtCore.pyqtSlot(bool, int, int)
    def triggerNoteEvent(self, eventType, note, velocity=None):
        self.keys[note].triggerNoteEvent(eventType, velocity if velocity is not None else self._defaultVelocity)

    def resizeEvent(self, event=None):
        sceneRect = QtCore.QRectF(0, 0, self._whiteKeysWidth * MetaKey.width, 100)
        self.pianoScene.setSceneRect(sceneRect)
        self.fitInView(sceneRect.adjusted(1, 1, -1, -1), QtCore.Qt.IgnoreAspectRatio)

    def keyPressEvent(self, event):
        if event.isAutoRepeat():
            return
        try:
            self.shortcuts[event.text()].triggerNoteEvent(True, self._defaultVelocity)
        except:
            pass

    def keyReleaseEvent(self, event):
        if event.isAutoRepeat():
            return
        try:
            self.shortcuts[event.text()].triggerNoteEvent(False, 0)
        except:
            pass

def printEvent(eventType, note, velocity):
    print('Note{eventType} {note} {noteName} {velocity}'.format(
        eventType = 'On' if eventType else 'Off', 
        note = note, 
        noteName = _noteNumberToName[note], 
        velocity = velocity
        ))

if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)
    piano = PianoKeyboard()
    piano.noteEvent.connect(printEvent)
#    piano.aspectRatio = QtCore.Qt.KeepAspectRatio
    piano.show()
    sys.exit(app.exec_())
