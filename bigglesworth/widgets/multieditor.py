#!/usr/bin/env python2.7
# *-* encoding: utf-8 *-*

import sys, os

os.environ['QT_PREFERRED_BINDING'] = 'PyQt4'

from Qt import QtCore, QtGui, QtWidgets
QtCore.pyqtSignal = QtCore.Signal

from frame import Frame
from combo import Combo
#Combo.value = lambda: Combo.combo.currentIndex()
from squarebutton import SquareButton
#SquareButton.value = lambda: SquareButton.switched

from pianokeyboard import PianoKeyboard, _isWhiteKey, _noteNumberToName

sys.path.append('../..')

from bigglesworth.widgets import NameEdit
from bigglesworth.dialogs import QuestionMessageBox
from bigglesworth.utils import loadUi, getName
from bigglesworth.parameters import panRange, arpTempo, fullRangeCenterZero
from bigglesworth.midiutils import SysExEvent, SYSEX
from bigglesworth.const import INIT, END, IDW, IDE, MULR, MULD, NameColumn

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


class PartObject(QtCore.QObject):
    def __init__(self, part=0):
        QtCore.QObject.__init__(self)
        self.part = part
        self.label = 'Part {}'.format(part)
        self.labelColor = self.borderColor = None
        self.bank = self.prog = 0
        self.volume = 100
        self.pan = self.transpose = self.detune = 64
        self.channel = part + 2
        self.lowVel = self.lowKey = 0
        self.highVel = self.highKey = 127
        self.midi = self.usb = self.local = self.play = True
        self.pitch = self.mod = self.pressure = self.sustain = self.edits = self.progChange = True
        self.ctrlBit = 63
        self.unknonwnParameter = 0
        self.tailData = [1, 63, 0, 0, 0, 0, 0, 0, 0, 0]

    @property
    def index(self):
        return (self.bank << 7) + self.prog

    @index.setter
    def index(self, index):
        self.bank = index >> 7
        self.prog = index & 127

    @property
    def velocityRange(self):
        return self.lowVel, self.highVel

    @velocityRange.setter
    def velocityRange(self, velRange):
        self.lowVel, self.highVel = velRange

    @property
    def keyRange(self):
        return self.lowKey, self.highKey

    @keyRange.setter
    def keyRange(self, keyRange):
        self.lowKey, self.highKey = keyRange

    @property
    def mute(self):
        return not self.play

    @mute.setter
    def mute(self, mute):
        self.play = not mute

    @property
    def receive(self):
        return (self.mute << 6) + (self.local << 2) + (self.usb << 1) + self.midi

    @receive.setter
    def receive(self, bitMask):
        self.mute = bool(bitMask & 64)
        self.local = bool(bitMask & 4)
        self.usb = bool(bitMask & 2)
        self.midi = bool(bitMask & 1)

    @property
    def ctrl(self):
        return (self.progChange << 5) + (self.edits << 4) + (self.sustain << 3) + (self.pressure << 2) + (self.mod << 1) + int(bool(self.pitch))

    @ctrl.setter
    def ctrl(self, bitMask):
        self.progChange = bool(bitMask & 32)
        self.edits = bool(bitMask & 16)
        self.sustain = bool(bitMask & 8)
        self.pressure = bool(bitMask & 4)
        self.mod = bool(bitMask & 2)
        self.pitch = bool(bitMask & 1)

    def getSerializedData(self):
        pass

    def setSerializedData(self, data):
        pass

    def getMidiData(self):
        return [self.bank, self.prog, self.volume, self.pan, self.unknonwnParameter, self.transpose, self.detune, self.channel, 
            self.lowKey, self.highKey, self.lowVel, self.highVel, self.receive, self.ctrl] + self.tailData

    def setMidiData(self, data):
        self.bank, self.prog, self.volume, self.pan, self.unknonwnParameter, self.transpose, self.detune, self.channel, \
            self.lowKey, self.highKey, self.lowVel, self.highVel, self.receive, self.ctrl = data[:14]
        self.tailData = data[14:]

    def getData(self):
        return [self.bank, self.prog, self.volume, self.pan, self.transpose, self.detune, self.channel, 
            self.lowKey, self.highKey, self.lowVel, self.highVel, 
            self.midi, self.usb, self.local, self.mute, 
            self.pitch, self.mod, self.pressure, self.sustain, self.edits, self.progChange]

    def getInfo(self):
        return self.label, self.labelColor, self.borderColor

    def setLabelData(self, *data):
        self.label, self.labelColor, self.borderColor = data

    @classmethod
    def fromMidi(cls, part, data):
        obj = cls(part)
        obj.setMidiData(data)
        return obj


class MultiObject(QtCore.QObject):
    def __init__(self, data=None):
        QtCore.QObject.__init__(self)
        self.unknonwnParameter = 0
        self.unknonwnData = [1, 0, 2, 4, 11, 12, 0, 0, 0, 0, 0, 0, 0]
        self.buffer = False
        if data is None:
            self.index = 0
            self._nameChars = [73, 110, 105, 116, 32, 77, 117, 108, 116, 105, 32, 32, 32, 32, 32, 32]
            self.volume = 127
            self.tempo = 55
            self.parts = [PartObject(part) for part in range(16)]
        else:
            self.parts = []
            if isinstance(data, (list, tuple)) and len(data) == 418 and isinstance(data[0], int):
                self.parseMidiData(data)
            else:
                self.parseSerializedData(data)

    @property
    def name(self):
        return ''.join(map(chr, self._nameChars))

    @name.setter
    def name(self, name=''):
        self._nameChars = map(ord, name.ljust(16))

    def parseMidiData(self, data):
        self.buffer = bool(data[0])
        self.index = data[1]
        self._nameChars = data[2:18]
        self.unknonwnParameter, self.volume, self.tempo = data[18:21]
        self.unknonwnData = data[21:34]
        partData = data[34:]
        if not self.parts:
            for part in range(16):
                self.parts.append(PartObject.fromMidi(part, partData[part * 24: (part + 1) * 24]))
        else:
            for part in self.parts:
                part.setMidiData(partData[part * 24: (part + 1) * 24])


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
            newEvent = SysExEvent(event.port, map(int, event.sysex))
        else:
            return
        self.midiEvent.emit(newEvent)

    def outputEvent(self, event):
        if self.isValid:
            outputEvent(mdSysExEvent(1, event.sysex))


class ProgProxyModel(QtCore.QSortFilterProxyModel):
    DefaultItemFlags = QtCore.Qt.ItemIsSelectable|QtCore.Qt.ItemIsEnabled
    bank = 0

    def rowCount(self, parent=None):
        return 128

    def setBank(self, bank):
        self.bank = bank
        self.invalidateFilter()
        self.modelReset.emit()

    def data(self, index, role=QtCore.Qt.DisplayRole):
        row = (self.bank << 7) + index.row()
        index = self.sourceModel().index(row, NameColumn) 
        data = index.data(role)
        if role == QtCore.Qt.DisplayRole:
            data = '{} {}'.format(index.row() + 1, data) if index.flags() & QtCore.Qt.ItemIsEnabled else str(index.row() + 1)
#        elif role == QtCore.Qt.ForegroundRole:
#            print('trattoria')
#            return QtGui.QBrush(QtGui.QColor(QtCore.Qt.green))
#            if not index.flags() & QtCore.Qt.ItemIsEnabled:
#                return QtWidgets.QApplication.palette().color(QtGui.QPalette.Disabled, QtGui.QPalette.Text)
        return data

    def flags(self, index):
        return self.DefaultItemFlags
#        row = (self.bank << 7) + index.row()
#        return self.sourceModel().index(row, NameColumn).flags()


class ColorLineEdit(QtWidgets.QLineEdit):
    editBtnClicked = QtCore.pyqtSignal()
    def __init__(self, *args, **kwargs):
        QtWidgets.QLineEdit.__init__(self, *args, **kwargs)
        self.editBtn = QtWidgets.QPushButton(u'…', self)
        self.editBtn.setCursor(QtCore.Qt.ArrowCursor)
        self.editBtn.clicked.connect(self.editBtnClicked.emit)

    def resizeEvent(self, event):
        size = self.height() - 8
        self.editBtn.resize(size, size)
        self.editBtn.move(self.width() - size - 4, (self.height() - size) / 2)


class PartLabelEditDialog(QtWidgets.QDialog):
#    defaultForeground = QtGui.QColor(QtCore.Qt.white)
#    defaultBackground = QtGui.QColor(QtCore.Qt.darkGray)
#    colorValidator = QtGui.QRegExpValidator(QtCore.QRegExp(r'^[#](?:[a-fA-F0-9]{3}|[a-fA-F0-9]{6})$'))

    def __init__(self, parent, label, fgd, bgd):
        QtWidgets.QDialog.__init__(self, parent)
        layout = QtWidgets.QGridLayout()
        self.setLayout(layout)

        layout.addWidget(QtWidgets.QLabel('Part name:'))
        self.labelEdit = QtWidgets.QLineEdit(label)
        layout.addWidget(self.labelEdit, 0, 1)
        self.labelEdit.setMaxLength(8)

        palette = self.palette()
        self.defaultForeground = QtGui.QColor(palette.color(palette.Text))
        self.defaultBackground = QtGui.QColor(palette.color(palette.Midlight))

        self.foregroundColor = fgd
        self.backgroundColor = bgd
        self.foregroundEdit = ColorLineEdit()
        basePalette = self.foregroundEdit.palette()
        basePalette.setColor(basePalette.Active, basePalette.Text, self.foregroundColor)
        basePalette.setColor(basePalette.Inactive, basePalette.Text, self.foregroundColor)
        basePalette.setColor(basePalette.Active, basePalette.Base, self.backgroundColor)
        basePalette.setColor(basePalette.Inactive, basePalette.Base, self.backgroundColor)
        layout.addWidget(QtWidgets.QLabel('Label color:'))
        self.foregroundEdit.setText(self.foregroundColor.name())
        self.foregroundEdit.textChanged.connect(self.validateColor)
        self.foregroundEdit.editBtnClicked.connect(self.foregroundSelect)
        self.foregroundEdit.setPalette(basePalette)
        layout.addWidget(self.foregroundEdit, 1, 1)
        autoFgBtn = QtWidgets.QPushButton('Base on background')
        layout.addWidget(autoFgBtn, 1, 2)
        autoFgBtn.clicked.connect(lambda: self.setForegroundColor(self.reverseColor(self.backgroundColor)))

        layout.addWidget(QtWidgets.QLabel('Background:'), 2, 0)
        self.backgroundEdit = ColorLineEdit()
        self.backgroundEdit.setText(self.backgroundColor.name())
        self.backgroundEdit.textChanged.connect(self.validateColor)
        self.backgroundEdit.editBtnClicked.connect(self.backgroundSelect)
        self.backgroundEdit.setPalette(basePalette)
        layout.addWidget(self.backgroundEdit, 2, 1)
        autoBgBtn = QtWidgets.QPushButton('Base on label')
        layout.addWidget(autoBgBtn, 2, 2)
        autoBgBtn.clicked.connect(lambda: self.setBackgroundColor(self.reverseColor(self.foregroundColor)))

        swapBtn = QtWidgets.QPushButton()
        layout.addWidget(swapBtn, 1, 3, 2, 1)
        swapBtn.setIcon(QtGui.QIcon.fromTheme('transform-move-vertical'))
        swapBtn.setToolTip('Invert colors')
        swapBtn.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Expanding)
        swapBtn.clicked.connect(self.swapColors)

        self.buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok|QtWidgets.QDialogButtonBox.Cancel)
        layout.addWidget(self.buttonBox, layout.rowCount(), 0, 1, layout.columnCount())
        self.okBtn = self.buttonBox.button(self.buttonBox.Ok)
        self.okBtn.clicked.connect(self.accept)
        self.buttonBox.button(self.buttonBox.Cancel).clicked.connect(self.reject)

        self.restoreBtn = self.buttonBox.addButton('Default colors', self.buttonBox.ResetRole)
        self.restoreBtn.setIcon(QtGui.QIcon.fromTheme('edit-undo'))
        self.restoreBtn.clicked.connect(lambda: [self.setBackgroundColor(), self.setForegroundColor()])

        self.setWindowTitle('Edit part label and colors')
        self.labelEdit.selectAll()

    def reverseColor(self, color):
        def isDifferent(lightDelta):
            return (abs(r - _r) + abs(g - _g) + abs(b - _b)) > 64 and abs(color.lightness() - newColor.lightness()) > lightDelta
        _r, _g, _b = color.getRgb()[:3]
        r = _r^255
        g = _g^255
        b = _b^255
        newColor = QtGui.QColor(r, g, b)
        if not isDifferent(96):
            newColor = QtGui.QColor(r, g, b).lighter()
            r, g, b = newColor.getRgb()[:3]
        if not isDifferent(48):
            newColor = QtGui.QColor(r, g, b).darker()
            r, g, b = newColor.getRgb()[:3]
        return QtGui.QColor(r, g, b)

    def validateColor(self, text):
        edit = self.sender()
        color = QtGui.QColor(edit.text())
        if color.isValid():
            if edit == self.foregroundEdit:
                self.setForegroundColor(color)
            else:
                self.setBackgroundColor(color)
#        print(self.colorValidator.validate(text, edit.cursorPosition())[0])

    def foregroundSelect(self):
        color = QtWidgets.QColorDialog.getColor(self.foregroundColor, self, 'Select text color')
        if color.isValid():
            self.foregroundEdit.setText(color.name())
            self.setForegroundColor(color)

    def setForegroundColor(self, color=None):
        if not color:
            color = self.defaultForeground
        elif isinstance(color, (str, unicode)):
            color = QtGui.QColor(color)
        self.foregroundColor = color
        palette = self.foregroundEdit.palette()
        palette.setColor(palette.Active, palette.Text, self.foregroundColor)
        palette.setColor(palette.Inactive, palette.Text, self.foregroundColor)
        self.foregroundEdit.setPalette(palette)
        self.backgroundEdit.setPalette(palette)
        self.foregroundEdit.setText(color.name())

    def backgroundSelect(self):
        color = QtWidgets.QColorDialog.getColor(self.backgroundColor, self, 'Select background color')
        if color.isValid():
            self.backgroundEdit.setText(color.name())
            self.setBackgroundColor(color)

    def setBackgroundColor(self, color=None):
        if not color:
            color = self.defaultBackground
        elif isinstance(color, (str, unicode)):
            color = QtGui.QColor(color)
        self.backgroundColor = color
        palette = self.backgroundEdit.palette()
        palette.setColor(palette.Active, palette.Base, self.backgroundColor)
        palette.setColor(palette.Inactive, palette.Base, self.backgroundColor)
        self.foregroundEdit.setPalette(palette)
        self.backgroundEdit.setPalette(palette)
        self.backgroundEdit.setText(color.name())

    def swapColors(self):
        fgd = self.foregroundColor
        bgd = self.backgroundColor
        self.setForegroundColor(bgd)
        self.setBackgroundColor(fgd)

    def exec_(self):
        res = QtWidgets.QDialog.exec_(self)
#        if self.foregroundColor == self.defaultForeground and self.backgroundColor == self.defaultBackground:
#            self.foregroundColor = None
#            self.backgroundColor = None
        return res


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
#        self.square.moveRight(self.width() - 1)
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
        self.shadow = Shadow(self)
        self.shadow.setVisible(False)

    @property
    def values(self):
        return self._values

    @values.setter
    def values(self, values):
        self._values = values
        self.startHandle.values = values
        self.endHandle.values = values

    def setEnabled(self, enabled):
        QtWidgets.QWidget.setEnabled(self, enabled)
        if not enabled:
            self.shadow.setGeometry(self.rect())
        self.shadow.setVisible(not enabled)

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
        if not self.isEnabled():
            self.shadow.setGeometry(self.rect())

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


class MultiNameEdit(NameEdit):
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

        self.nameEdit = MultiNameEdit()
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

#        self.setMaximumHeight((self.font().pointSize() * 2 + self.frameWidth()) * 2)
        hint = self.displayWidget.sizeHint()
        hint += QtCore.QSize(self.frameWidth() * 2, self.frameWidth() * 2)
        self.setMinimumSize(hint)

    def setCurrent(self, index, name):
        self.slotSpin.setValue(index)
        self.nameEdit.setText(name)

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
    labelEditRequested = QtCore.pyqtSignal(int)
    dragRequested = QtCore.pyqtSignal()
    clicked = QtCore.pyqtSignal()

    def __init__(self, part):
        QtWidgets.QWidget.__init__(self)
        self.part = part
        self.realLabel = str(part + 1)
        self._label = ' {} '.format(self.realLabel)
        palette = self.palette()
        self.brush = palette.color(palette.Midlight)
        self.pen = palette.color(palette.Text)
        self.updateSize()

    @property
    def label(self):
        return self._label

    @label.setter
    def label(self, label):
        self.realLabel = label
        label = ' '.join(label.split())
        if label == self._label:
            return
        if label.lower().startswith('part ') and len(label.split()) == 2 and label.split()[1].isdigit():
            label = label.split()[1]
        self._label = (' {} ').format(label)
        self.updateSize()

    def updateSize(self):
        self._font = self.font()
        self._font.setPointSize(max(8, self._font.pointSize()) * 2)
        self._font.setBold(True)
        self.updateGeometry()

    def sizeHint(self):
        return QtGui.QFontMetrics(self._font).boundingRect(self._label + ' ').size()

    def changeEvent(self, event):
        if event.type() == QtCore.QEvent.FontChange:
            self.updateSize()

    def mousePressEvent(self, event):
        if not self.parent().selectable:
            self.startPos = event.pos()
        else:
            self.clicked.emit()
            self.startPos = None

    def mouseMoveEvent(self, event):
        if self.startPos is not None and event.pos() - self.startPos >= QtWidgets.QApplication.startDragDistance():
            self.dragRequested.emit()

    def mouseDoubleClickEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.labelEditRequested.emit(self.part)

    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        qp.setRenderHints(qp.Antialiasing)
        qp.translate(.5, .5)
        qp.setPen(QtCore.Qt.NoPen)
        qp.setBrush(self.brush)
        qp.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 2, 2)
        qp.setPen(self.pen)
        qp.setFont(self._font)
        qp.drawText(self.rect(), QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter, self._label)


class RangeEditor(QtWidgets.QWidget):
    rangeChanged = QtCore.pyqtSignal(int, int, int)
    selected = QtCore.pyqtSignal(int, bool)
    labelEditRequested = QtCore.pyqtSignal(int)
    dragRequested = QtCore.pyqtSignal(int)
    dropRequested = QtCore.pyqtSignal(int, int, bool)

    def __init__(self):
        QtWidgets.QWidget.__init__(self)
        self.setMouseTracking(True)
        self.setAcceptDrops(True)
        self.dropTargetWidget = DropTargetWidget(self)
        self.highlightWidget = HighlightWidget(self)

        layout = QtWidgets.QGridLayout()
        layout.setHorizontalSpacing(2)
        layout.setVerticalSpacing(2)
        self.setLayout(layout)

        self.sliders = []
        self.selectors = []
        self.labels = []
        selectorSizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Maximum)
        for part in range(16):
            selector = PartCheckBox()
            selector.part = part
            layout.addWidget(selector, part, 0)
            selector.setSizePolicy(selectorSizePolicy)
            selector.setReallyVisible(False)
            selector.toggled.connect(lambda state, part=part: self.setSelected(part, state))
            self.selectors.append(selector)
            label = PartLabel(part)
            label.labelEditRequested.connect(self.labelEditRequested)
            label.dragRequested.connect(lambda part=part: self.dragRequested.emit(part))
            label.clicked.connect(lambda selector=selector, part=part: self.setSelected(part, not selector.isChecked()))
            layout.addWidget(label, part, 1)
            self.labels.append(label)
            slider = RangeSlider()
            slider.index = part
            self.sliders.append(slider)
            layout.addWidget(slider, part, 2)
            slider.hoverEnter.connect(self.sliderEnter)
            slider.rangeChanged.connect(self.checkSelection)
            slider.rangeChanged.connect(self.emitRangeChanged)

        self.currentSlider = None
        self.selectable = False

    def getStripRect(self, part):
        return self.labels[part].geometry() | self.sliders[part].geometry()

    def setSelectable(self, selectable):
        self.selectable = selectable
        for selector in self.selectors:
            selector.setReallyVisible(selectable)
            if not selectable:
                selector.blockSignals(True)
                selector.setChecked(False)
                selector.blockSignals(False)
        for widget in self.sliders:
            widget.setEnabled(not selectable)

    def setSelected(self, part, selected):
        if not self.selectable:
            return
        self.sliders[part].setEnabled(selected)
#        self.labels[part].setEnabled(selected)
        if isinstance(self.sender(), (PartCheckBox, PartLabel)):
            self.selected.emit(part, selected)
        else:
            selector = self.selectors[part]
            selector.blockSignals(True)
            selector.setChecked(selected)
            selector.blockSignals(False)

    def highlight(self, part):
        self.highlightWidget.activate(self.labels[part].geometry() | self.sliders[part].geometry())

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

    def showEvent(self, event):
        if not event.spontaneous():
            self.dropTargetWidget.raise_()
            self.highlightWidget.raise_()

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat('bigglesworth/MultiStrip'):
            event.accept()
            self.update()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat('bigglesworth/MultiStrip'):
            widget = QtWidgets.QApplication.widgetAt(QtGui.QCursor.pos())
            if not widget:
                self.dropTargetWidget.setVisible(False)
                return event.ignore()
            event.accept()
            spacing = self.layout().spacing()
            dropTarget = QtCore.QRect()
            isOver = False
            stripWidth = self.sliders[0].geometry().right() - self.labels[0].x()
            bottom = self.sliders[-1].geometry().bottom() - spacing
            if widget == self:
                y = event.pos().y()
                for index, label in enumerate(self.labels):
                    if y > label.geometry().y():
                        continue
                    dropTarget = QtCore.QRect(0, max(0, label.y() - spacing / 2), stripWidth, spacing)
                    index -= 1
                    break
                else:
                    dropTarget = QtCore.QRect(0, bottom, 0, stripWidth, spacing)
                    index = 16
            else:
                pos = event.pos()
                for index, label in enumerate(self.labels):
                    if pos in label.geometry().adjusted(0, -spacing, stripWidth, spacing):
                        break
                if pos in label.geometry().adjusted(0, 5, stripWidth, -5):
                    dropTarget = label.geometry()
                    dropTarget.setWidth(stripWidth)
                    isOver = True
                elif pos.y() > label.geometry().bottom() - 5:
                    dropTarget = QtCore.QRect(0, label.geometry().top(), stripWidth, spacing)
                    if index == 15:
                        dropTarget.moveBottom(bottom - 1)
                    else:
                        dropTarget.moveTop(self.labels[index + 1].y() - spacing / 2)
                else:
                    index -= 1
                    dropTarget = QtCore.QRect(0, max(0, label.y() - spacing / 2), stripWidth, spacing)

            self.dropTargetWidget.setGeometry(dropTarget)
            self.dropTargetWidget.setVisible(True)

            self.dropTarget = index, isOver
            if isOver:
                byteArray = QtCore.QByteArray(event.mimeData().data('bigglesworth/MultiStrip'))
                stream = QtCore.QDataStream(byteArray)
                if stream.readInt() == index:
                    return event.ignore()
                event.setDropAction(QtCore.Qt.CopyAction)
            else:
                event.setDropAction(QtCore.Qt.MoveAction)

    def dragLeaveEvent(self, event):
        self.dropTargetWidget.setVisible(False)

    def dropEvent(self, event):
        byteArray = QtCore.QByteArray(event.mimeData().data('bigglesworth/MultiStrip'))
        stream = QtCore.QDataStream(byteArray)
        source = stream.readInt()
        self.dropTargetWidget.setVisible(False)
        QtCore.QTimer.singleShot(0, lambda: self.dropRequested.emit(source, *self.dropTarget))


class VelocityRangeEditor(RangeEditor):
    velocityChanged = RangeEditor.rangeChanged

    def __init__(self, *args, **kwargs):
        RangeEditor.__init__(self, *args, **kwargs)
        self.velocity = VelocityView()
        self.layout().addWidget(self.velocity, self.layout().rowCount(), 2, 1, 1)
        self.currentPartLbl = QtWidgets.QLabel('')
        self.currentPartLbl.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum)
        self.layout().addWidget(self.currentPartLbl, self.layout().rowCount(), 2, 1, 1)

    def checkSelection(self, start, end):
        self.velocity.setRange(start, end)
        label = self.labels[self.currentSlider.index].realLabel
        velRange = end - start + 1
        if velRange == 128:
            velRange = 'full range'
        elif velRange > 0:
            velRange = '{} level{}'.format(velRange, 's' if velRange > 1 else '')
        else:
            velRange = 'invalid range'
        text = '{}: {}, from {} to {}'.format(label, velRange, start, end)
        self.currentPartLbl.setText(text)

    def deselect(self):
        self.currentSlider = None
        self.velocity.hideRange()
        self.currentPartLbl.setText('')


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

        self.currentPartLbl = QtWidgets.QLabel('')
        self.currentPartLbl.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum)
        self.layout().addWidget(self.currentPartLbl, self.layout().rowCount(), 2, 1, 1)

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
            label = self.labels[self.currentSlider.index].realLabel
            keyRange = end - start + 1
            if keyRange == 128:
                keyRange = 'full keyboard'
            elif keyRange > 0:
                keyRange = '{} key{}'.format(keyRange, 's' if keyRange > 1 else '')
            else:
                keyRange = 'invalid range'
            text = '{}: {}, from {} to {}'.format(label, keyRange, noteNames[start], noteNames[end])
            self.currentPartLbl.setText(text)
        else:
            self.pianoBackground.setVisible(False)
            self.currentPartLbl.setText('')
        self.pianoSelection.setPath(path)

    def deselect(self):
        self.currentSlider = None
        self.pianoSelection.setPath(QtGui.QPainterPath())
        self.pianoBackground.setVisible(False)
        self.currentPartLbl.setText('')


class Shadow(QtWidgets.QWidget):
    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
#        qp.fillRect(self.rect(), shadowBrush)
        qp.setRenderHints(qp.Antialiasing)
        qp.setPen(QtCore.Qt.NoPen)
        qp.setBrush(shadowBrush)
        qp.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 2, 2)


#class LabelEdit(QtWidgets.QLineEdit):
#    def __init__(self, parent):
#        QtWidgets.QLineEdit.__init__(self, parent)
#
#    def keyPressEvent(self, event):
#        if event.key() == QtCore.Qt.Key_Escape:
#            self.setVisible(False)
#        else:
#            QtWidgets.QLineEdit.keyPressEvent(self, event)
#
#    def focusOutEvent(self, event):
#        QtWidgets.QLineEdit.focusOutEvent(self, event)
#        self.setVisible(False)
#
#    def setPalette(self, palette):
#        self.setStyleSheet('''
#            border: 1px solid palette(dark);
#            border-style: inset;
#        ''')
#        self.setMaximumHeight(self.fontMetrics().height() * 2)


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
#    valueSignals = [
#        ('volumeChanged', 'volumeSlider', 'setVolume'), 
#        ('panChanged', 'panSlider', 'setPan'), 
#        ('transposeChanged', 'transposeDial', 'setTranspose'), 
#        ('detuneChanged', 'detuneDial', 'setDetune'), 
#        ('channelChanged', 'channelCombo', 'setChannel'), 
#        ('lowKeyChanged', 'lowKeyDial', 'setLowKey'), 
#        ('highKeyChanged', 'highKeyDial', 'setHighKey'), 
#        ('lowVelChanged', 'lowVelDial', 'setLowVel'), 
#        ('highVelChanged', 'highVelDial', 'setHighVel'), 
#        ]

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

#    dials = 'transpose', 'detune', 'lowKey', 'highKey', 'highVel', 'lowVel'
#    sliders = 'volume', 'pan'
    valueProps = ['volume', 'pan', 'transpose', 'detune', 'channel', 'lowKey', 'highKey', 'lowVel', 'highVel']
    bottomProps = ['pitch', 'mod', 'pressure', 'sustain', 'edits', 'progChange']
    toggleProps = ['midi', 'usb', 'local', 'play'] + bottomProps
    allProps = valueProps + toggleProps

    PasteMidi, PasteValues, PasteParams, PasteAll = 1, 2, 3, 7

    selected = QtCore.pyqtSignal(int, bool)
    dragRequested = QtCore.pyqtSignal()
    labelEditRequested = QtCore.pyqtSignal(int)
    pasteRequested = QtCore.pyqtSignal(int)
    labelReset = QtCore.pyqtSignal()
    beginChanReset = QtCore.pyqtSignal()
    endChanReset = QtCore.pyqtSignal()

    def __init__(self, part):
        Frame.__init__(self)
        loadUi('ui/multistrip.ui', self)
        self.part = part

        self.bankCombo.currentIndexChanged.connect(self.setBank)
        self.progCombo.setExpanding(True)
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
        self.bottomButtons = self.modBtn, self.pitchBtn, self.sustainBtn, self.pressureBtn, self.editsBtn, self.progChangeBtn

        self.allWidgets = []
        self.valueWidgets = []
        self.signalSlotNames = []
        self.slots = []

        self.transposeDial.setValueList(fullRangeCenterZero)
        self.detuneDial.setValueList(fullRangeCenterZero)

        for attr in self.valueProps:
            signal = getattr(self, '{}Changed'.format(attr))
            if attr == 'channel':
                widget = self.channelCombo
            elif attr in ('volume', 'pan'):
                widget = getattr(self, '{}Slider'.format(attr))
            else:
                widget = getattr(self, '{}Dial'.format(attr))
            slotName = 'set{}{}'.format(attr[0].upper(), attr[1:])
            setattr(self, slotName, widget.setValue)
            self.signalSlotNames.append((signal, slotName))
            self.slots.append(getattr(self, slotName))
            self.allWidgets.append(widget)
            self.valueWidgets.append(widget)
            widget.valueChanged.connect(lambda value, signal=signal, part=part: signal.emit(part, value))
            widget.valueChanged.connect(lambda value, attr=attr: self.updateProperty(attr, value))
        for attr in self.toggleProps:
            signal = getattr(self, '{}Toggled'.format(attr))
            widget = getattr(self, '{}Btn'.format(attr))
            slotName = 'set{}{}'.format(attr[0].upper(), attr[1:])
            setattr(self, slotName, widget.setSwitched)
            self.signalSlotNames.append((signal, slotName))
            self.slots.append(getattr(self, slotName))
            self.allWidgets.append(widget)
            widget.switchToggled.connect(lambda state, signal=signal,part=part: signal.emit(part, state))
            widget.switchToggled.connect(lambda value, attr=attr: self.updateProperty(attr, value))

        self.bankCombo.valueChanged.connect(lambda value: self.updateProperty('bank', value))
        self.setBank = self.bankCombo.setValue
        self.progCombo.valueChanged.connect(lambda value: self.updateProperty('prog', value))
        self.setProg = self.progCombo.setValue

        self.checkSizes()
        self.isSelected = self.selectChk.isChecked
        self.shadow = Shadow(self)
        self.shadow.setVisible(False)
        self.partObject = None
        self.startPos = None
        self.model = None

    def setPartObject(self, partObject):
        self.partObject = partObject
        self.bankCombo.blockSignals(True)
        self.bankCombo.setValue(partObject.bank)
        self.bankCombo.blockSignals(False)
        self.progCombo.blockSignals(True)
        self.progCombo.setValue(partObject.prog)
        self.progCombo.blockSignals(False)
        for widget, slot, attr in zip(self.allWidgets, self.slots, self.allProps):
            widget.blockSignals(True)
            slot(getattr(partObject, attr))
            widget.blockSignals(False)

    def setLabelData(self, *data, **kwargs):
        self.label, labelColor, borderColor = data
        #questo è sbagliato.
        if kwargs.get('override', False):
            palette = self.palette()
            self.labelColor = labelColor if labelColor else palette.color(palette.Text)
            self.borderColor = borderColor if borderColor else palette.color(palette.Base)
            if self.labelColor == palette.color(palette.Text):
                labelColor = None
            else:
                labelColor = self.labelColor
            if self.borderColor == palette.color(palette.Base):
                borderColor = None
            else:
                borderColor = self.borderColor
        self.partObject.setLabelData(self.label, labelColor, borderColor)

    def updateProperty(self, attr, value):
        if not self.partObject:
            return
        setattr(self.partObject, attr, value)

    def setModel(self, model):
        self.model = model
        self.progCombo.combo.setModel(model)

    def setCollectionModel(self, model):
        self.collectionModel = model
        self.model.setSourceModel(model)

    def setBank(self, bank):
        if not self.model:
            return
        self.model.setBank(bank)

    def playSwitched(self, state):
        if not state:
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
        self.channelCombo.setValue(channel)

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
        self.labelReset.emit()
        self.volumeSlider.setValue(self.volumeSlider.defaultValue)
        self.panSlider.setValue(self.panSlider.defaultValue)
        self.transposeDial.setValue(self.transposeDial.defaultValue)
        self.detuneDial.setValue(self.detuneDial.defaultValue)
        self.lowKeyDial.setValue(0)
        self.highKeyDial.setValue(127)
        self.lowVelDial.setValue(0)
        self.highKeyDial.setValue(127)

    def resetMidi(self):
        self.beginChanReset.emit()
        self.channelCombo.setValue(self.part + 2)
        self.playBtn.setSwitched(True)
        for btn in self.midiButtons + self.bottomButtons:
            btn.setSwitched(True)
            #force emit to restore defaults value even if the current state is already True
            btn.switchToggled.emit(True)
        QtCore.QTimer.singleShot(0, self.endChanReset.emit)

    def resetAll(self):
        self.resetValues()
        self.resetMidi()

    def getData(self):
        values = [self.bankCombo.combo.currentIndex(), self.progCombo.combo.currentIndex()]
        for w in self.allWidgets:
            if isinstance(w, Combo):
                values.append(w.combo.currentIndex())
            elif isinstance(w, SquareButton):
                values.append(w.switched)
            else:
                values.append(w.value)
        return self.label, self.labelColor, self.borderColor, values

    def setData(self, data, mode=None):
        if mode is None:
            mode = self.PasteParams
        if mode == self.PasteAll:
            self.bankCombo.setValue(data[0])
            self.progCombo.setValue(data[1])
        for value, widget in zip(data[2:], self.allWidgets):
            if (mode & self.PasteParams) == self.PasteParams:
                widget.setValue(value)
            else:
                if mode & self.PasteMidi and widget in self.midiButtons + self.bottomButtons:
                    widget.setValue(value)
                if mode & self.PasteValues and widget in self.valueWidgets:
                    widget.setValue(value)

    def contextMenuEvent(self, event):
        menu = QtWidgets.QMenu()
        menu.setSeparatorsCollapsible(False)
        menu.addSection(self.label)
        if self.selectable:
            selectAction = menu.addAction('Group edit')
            selectAction.setCheckable(True)
            selectAction.setChecked(self.selectChk.isChecked())
            selectAction.triggered.connect(self.selectChk.setChecked)
        else:
            editAction = menu.addAction(QtGui.QIcon.fromTheme('document-edit'), 'Edit label...')
            editAction.triggered.connect(lambda: self.labelEditRequested.emit(self.part))
        menu.addSeparator()
        copyAction = menu.addAction(QtGui.QIcon.fromTheme('edit-copy'), 'Copy Data')
        pasteMenu = menu.addMenu('Paste Data')
        if QtWidgets.QApplication.clipboard().mimeData().hasFormat('bigglesworth/MultiStrip'):
            pasteAllAction = pasteMenu.addAction(QtGui.QIcon.fromTheme('edit-paste'), 'Paste everything (including sounds)')
            pasteAllAction.setData(self.PasteAll)
            pasteMenu.addSeparator()
            pasteParamsAction = pasteMenu.addAction(QtGui.QIcon.fromTheme('edit-paste'), 'Paste all parameters')
            pasteParamsAction.setData(self.PasteParams)
            pasteValuesAction = pasteMenu.addAction(QtGui.QIcon.fromTheme('dial'), 'Paste values')
            pasteValuesAction.setData(self.PasteValues)
            pasteMidiAction = pasteMenu.addAction(QtGui.QIcon.fromTheme('midi'), 'Paste MIDI parameters')
            pasteMidiAction.setData(self.PasteMidi)
            pasteActions = [pasteAllAction, pasteParamsAction, pasteValuesAction, pasteMidiAction]
        else:
            pasteActions = []
            pasteMenu.setEnabled(False)
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

        res = menu.exec_(QtGui.QCursor.pos())
        if res == copyAction:
            mimeData = QtCore.QMimeData()
            byteArray = QtCore.QByteArray()
            stream = QtCore.QDataStream(byteArray, QtCore.QIODevice.WriteOnly)
            stream.writeInt(self.part)
            stream.writeQVariant(self.getData())
            mimeData.setData('bigglesworth/MultiStrip', byteArray)
            QtWidgets.QApplication.clipboard().setMimeData(mimeData)
        elif res in pasteActions:
            self.pasteRequested.emit(res.data())

    def changeEvent(self, event):
        if event.type() in (QtCore.QEvent.PaletteChange, QtCore.QEvent.FontChange):
            self.checkSizes()

    def resizeEvent(self, event):
        if self.shadow.isVisible():
            self.shadow.setGeometry(self.rect().adjusted(0, self.playBtn.geometry().top(), 0, 0))

    def mousePressEvent(self, event):
        if not self.selectable and event.y() <= self._labelRect.bottom():
            self.startPos = event.pos()
        else:
            self.startPos = None

    def mouseDoubleClickEvent(self, event):
        if not self.selectable and event.y() <= self._labelRect.bottom():
            self.labelEditRequested.emit(self.part)

    def mouseMoveEvent(self, event):
        if self.startPos is not None and event.pos() - self.startPos >= QtWidgets.QApplication.startDragDistance():
            self.dragRequested.emit()

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


class DropTargetWidget(QtWidgets.QWidget):
    def __init__(self, parent):
        QtWidgets.QWidget.__init__(self, parent)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        self.setVisible(False)
        self.setAutoFillBackground(True)
        self.setStyleSheet('''
            background: rgba(128, 192, 192, 128);
            border: 1px solid blue;
            border-radius: 2px;
            border-style: outset;
            ''')

    def paintEvent(self, event):
        option = QtWidgets.QStyleOption()
        option.init(self)
        qp = QtWidgets.QStylePainter(self)
        qp.drawPrimitive(QtWidgets.QStyle.PE_Widget, option)



class HighlightWidget(QtWidgets.QWidget):
    def __init__(self, parent):
        QtWidgets.QWidget.__init__(self, parent)
        self.setVisible(False)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        self.pen = QtGui.QColor(QtCore.Qt.black)
        self.brush = QtGui.QColor(QtCore.Qt.white)
        self.fadeAnimation = QtCore.QPropertyAnimation(self, b'alpha')
        self.fadeAnimation.setDuration(1500)
        self.fadeAnimation.setStartValue(1)
        self.fadeAnimation.setEndValue(0)
        self.fadeAnimation.setEasingCurve(QtCore.QEasingCurve(QtCore.QEasingCurve.InSine))
        self.fadeAnimation.finished.connect(lambda: self.setVisible(False))

    @QtCore.pyqtProperty(float)
    def alpha(self):
        return self.pen.alphaF()

    @alpha.setter
    def alpha(self, alpha):
        self.pen.setAlphaF(alpha)
        self.brush.setAlphaF(alpha * .6)
        self.update()

    def activate(self, geometry):
        self.setGeometry(geometry)
        palette = self.palette()
        self.pen = palette.color(palette.Text).adjusted(a=255)
        self.brush = palette.color(palette.Base).adjusted(a=170)
        self.setVisible(True)
        self.fadeAnimation.start()

    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        qp.setRenderHints(qp.Antialiasing)
        qp.setPen(self.pen)
        qp.setBrush(self.brush)
        qp.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 2, 2)


class ChannelPageWidget(QtWidgets.QWidget):
    dropRequested = QtCore.pyqtSignal(int, int, bool)

    def __init__(self, *args, **kwargs):
        QtWidgets.QWidget.__init__(self, *args, **kwargs)
        self.dropTargetWidget = DropTargetWidget(self)

    def showEvent(self, event):
        if not event.spontaneous():
            self.dropTargetWidget.raise_()

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat('bigglesworth/MultiStrip'):
            event.accept()
            self.update()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat('bigglesworth/MultiStrip'):
            widget = QtWidgets.QApplication.widgetAt(QtGui.QCursor.pos())
            if not widget:
                self.dropTargetWidget.setVisible(False)
                return event.ignore()
            event.accept()
            spacing = self.layout().spacing()
            dropTarget = QtCore.QRect()
            isOver = False
            if widget == self:
                x = event.pos().x()
                for index, strip in enumerate(self.strips):
                    if x > strip.geometry().x():
                        continue
                    dropTarget = QtCore.QRect(max(0, strip.x() - spacing / 2), 0, spacing, strip.height())
                    index -= 1
                    break
                else:
                    dropTarget = QtCore.QRect(self.width() - spacing, 0, spacing, strip.height())
                    index = 16
            else:
                pos = event.pos()
                for index, strip in enumerate(self.strips):
                    if pos in strip.geometry().adjusted(-spacing, 0, spacing, 0):
                        break
                if pos in strip.geometry().adjusted(10, 0, -10, 0):
                    dropTarget = strip.geometry()
                    isOver = True
                elif pos.x() > strip.geometry().right() - 10:
                    dropTarget = QtCore.QRect(strip.geometry().left(), 0, self.layout().spacing(), strip.height())
                    if index == 15:
                        dropTarget.moveRight(self.width() - 1)
                    else:
                        dropTarget.moveLeft(self.strips[index + 1].x() - spacing / 2)
                else:
                    index -= 1
                    dropTarget = QtCore.QRect(max(0, strip.x() - spacing / 2), 0, self.layout().spacing(), strip.height())

            self.dropTargetWidget.setGeometry(dropTarget)
            self.dropTargetWidget.setVisible(True)

            self.dropTarget = index, isOver
            if isOver:
                byteArray = QtCore.QByteArray(event.mimeData().data('bigglesworth/MultiStrip'))
                stream = QtCore.QDataStream(byteArray)
                if stream.readInt() == index:
                    return event.ignore()
                event.setDropAction(QtCore.Qt.CopyAction)
            else:
                event.setDropAction(QtCore.Qt.MoveAction)

    def dragLeaveEvent(self, event):
        self.dropTargetWidget.setVisible(False)

    def dropEvent(self, event):
        byteArray = QtCore.QByteArray(event.mimeData().data('bigglesworth/MultiStrip'))
        stream = QtCore.QDataStream(byteArray)
        source = stream.readInt()
        self.dropTargetWidget.setVisible(False)
        QtCore.QTimer.singleShot(0, lambda: self.dropRequested.emit(source, *self.dropTarget))


class MultiEditor(QtWidgets.QWidget):
    midiEvent = QtCore.pyqtSignal(object)
    closeRequested = QtCore.pyqtSignal()
    detachRequested = QtCore.pyqtSignal()

    def __init__(self, *args, **kwargs):
        QtWidgets.QWidget.__init__(self, *args, **kwargs)
        loadUi('ui/multieditor.ui', self)
        self.setAutoFillBackground(True)
        self.main = QtWidgets.QApplication.instance()

        if __name__ == '__main__':
            self.database = None
            self.midiDevice = TestMidiDevice(self)
            self.midiThread = QtCore.QThread()
            self.midiDevice.moveToThread(self.midiThread)
            self.midiThread.started.connect(self.midiDevice.start)
            self.midiThread.start()
            self.midiDevice.midiEvent.connect(self.midiEventReceived)
            palette = self.palette()
            palette.setColor(palette.Active, palette.Button, QtGui.QColor(124, 240, 110))
            self.setPalette(palette)
        else:
            self.database = self.main.database
            self.referenceModel = self.database.referenceModel

        self.tempoDial.setValueList(arpTempo)
        self.requestBtn.clicked.connect(self.sendRequest)
        self.groupEditBtn.switchToggled.connect(self.setGroupEdit)

        self.closeBtn.clicked.connect(self.closeRequested)
        self.detachBtn.clicked.connect(self.detachRequested)
        cornerBtnSize = min(self.closeBtn.button.width(), self.detachBtn.button.width())
        self.closeBtn.button.setMaximumWidth(cornerBtnSize)
        self.detachBtn.button.setMaximumWidth(cornerBtnSize)

        self.velocityRangeEditor = VelocityRangeEditor()
        self.stackedWidget.addWidget(self.velocityRangeEditor)
        self.velocityRangeEditor.velocityChanged.connect(self.setVelocities)
        self.velocityRangeEditor.labelEditRequested.connect(self.showEditDialog)
        self.velocityRangeEditor.dragRequested.connect(self.dragStrip)
        self.velocityRangeEditor.dropRequested.connect(self.dropRequested)

        self.keyRangeEditor = KeyRangeEditor()
        self.stackedWidget.addWidget(self.keyRangeEditor)
        self.keyRangeEditor.keyChanged.connect(self.setKeys)
        self.keyRangeEditor.labelEditRequested.connect(self.showEditDialog)
        self.keyRangeEditor.dragRequested.connect(self.dragStrip)
        self.keyRangeEditor.dropRequested.connect(self.dropRequested)

        #little hack to (theoretically) ensure that both piano and velocity 
        #QGraphicsViews have the same height
        self.velocityRangeEditor.velocity.setSizePolicy(self.keyRangeEditor.piano.sizePolicy())
        self.velocityRangeEditor.velocity.sizeHint = lambda: self.keyRangeEditor.piano.sizeHint()

        self.strips = self.channelPage.strips = []
        for part in range(16):
            strip = MultiStrip(part)
            self.strips.append(strip)
#            strip.label = 'Part {}'.format(part + 1)
            strip.dragRequested.connect(self.dragStrip)
            strip.pasteRequested.connect(lambda data, strip=strip: self.pasteData(strip, data))
            strip.labelReset.connect(self.setPartLabels)
            if self.database:
                strip.setModel(ProgProxyModel())

            strip.beginChanReset.connect(self.beginChanReset)
            strip.endChanReset.connect(self.endChanReset)
            strip.labelEditRequested.connect(self.showEditDialog)
            strip.lowKeyChanged.connect(self.keyRangeEditor.setLowValue)
            strip.highKeyChanged.connect(self.keyRangeEditor.setHighValue)
            strip.lowVelChanged.connect(self.velocityRangeEditor.setLowValue)
            strip.highVelChanged.connect(self.velocityRangeEditor.setHighValue)
            strip.velocityBtn.clicked.connect(lambda part=part: self.showVelocities(part))
            strip.keyBtn.clicked.connect(lambda part=part: self.showKeys(part))
            strip.setChannel(part + 2)
            self.stripLayout.addWidget(strip)

            for signal, slotName in strip.signalSlotNames:
                signal.connect(lambda part, value, slotName=slotName: self.updateGroup(part, slotName, value))

        self.velocityBtn.clicked.connect(self.showVelocities)
        self.keyBtn.clicked.connect(self.showKeys)
        self.mainBtn.clicked.connect(self.showMixer)
        self.channelPage.dropRequested.connect(self.dropRequested)
        self.groupEdit = False
        self.currentMulti = None
        self.currentCollection = None
        self.currentCollectionModel = None
        self.isResettingChannels = False
        self.setCurrentMulti(MultiObject())

    def beginChanReset(self):
        self.isResettingChannels = True

    def endChanReset(self):
        self.isResettingChannels = False

    def setCollection(self, collection=None):
        if self.currentCollection == collection:
            return
        self.currentCollection = collection
        if collection is not None:
            model = self.database.openCollection(collection)
            for strip in self.strips:
                strip.setCollectionModel(model)

    def showEditDialog(self, part):
        if self.groupEdit:
            return
        strip = self.strips[part]
        dialog = PartLabelEditDialog(self, strip.label, strip.labelColor, strip.borderColor)
        if dialog.exec_():
            self.setPartLabels(part, (dialog.labelEdit.text(), dialog.foregroundColor, dialog.backgroundColor), override=True)
#            label = dialog.labelEdit.text()
#            velocityLabel = self.velocityRangeEditor.labels[part]
#            keyLabel = self.keyRangeEditor.labels[part]
#
#            strip.setLabelData(label, dialog.foregroundColor, dialog.backgroundColor)
#            velocityLabel.label = keyLabel.label = label
#            velocityLabel.pen = keyLabel.pen = dialog.foregroundColor
#            velocityLabel.brush = keyLabel.brush = dialog.backgroundColor
#
#            velocityLabel.update()
#            keyLabel.update()

    def setGroupEdit(self, active):
        self.groupEdit = active
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

    def updateGroup(self, part, slotName, value):
        if self.groupEditBtn.switched:
            for strip in self.strips:
                if strip.part == part or not strip.isSelected():
                    continue
                if self.isResettingChannels and slotName == 'setChannel':
                    value = strip.part + 2
                getattr(strip, slotName)(value)

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

    @QtCore.pyqtSlot(int)
    def showVelocities(self, part=None):
        self.stackedWidget.setCurrentWidget(self.velocityRangeEditor)
        self.mainBtn.setSwitched(False)
        self.velocityBtn.setSwitched(True)
        self.keyBtn.setSwitched(False)
        if part is not None:
            self.velocityRangeEditor.highlight(part)

    @QtCore.pyqtSlot(int)
    def showKeys(self, part=None):
        self.stackedWidget.setCurrentWidget(self.keyRangeEditor)
        self.mainBtn.setSwitched(False)
        self.velocityBtn.setSwitched(False)
        self.keyBtn.setSwitched(True)
        if part is not None:
            self.keyRangeEditor.highlight(part)

    def setPartLabels(self, part=None, data=None, override=True):
        palette = self.palette()
        if part is None:
            strip = self.sender()
            part = strip.part
            label = 'Part {}'.format(part + 1)
            foregroundColor = QtGui.QColor(palette.color(palette.Text))
            backgroundColor = QtGui.QColor(palette.color(palette.Midlight))
        else:
            strip = self.strips[part]
            label, foregroundColor, backgroundColor = data
#            if not override or foregroundColor is None:
#                foregroundColor = QtGui.QColor(palette.color(palette.Text))
#            if not override or backgroundColor is None:
#                backgroundColor = QtGui.QColor(palette.color(palette.Midlight))
            #change label only if any of the labels are not "Part X"
            if label.lower().startswith('part ') and len(label.split()) == 2 and label.split()[1].isdigit():
                label = 'Part {}'.format(part + 1)
        strip.setLabelData(label, foregroundColor, backgroundColor, override=override)
#        strip.foregroundColor = foregroundColor
#        strip.backgroundColor = backgroundColor

        velocityLabel = self.velocityRangeEditor.labels[part]
        keyLabel = self.keyRangeEditor.labels[part]

        velocityLabel.label = keyLabel.label = label
        velocityLabel.pen = keyLabel.pen = foregroundColor
        velocityLabel.brush = keyLabel.brush = backgroundColor

        velocityLabel.update()
        keyLabel.update()

    def pasteData(self, target, pasteMask):
#        print('paste to: {}, mask {}'.format(target, pasteMask))
#        return
        byteArray = QtWidgets.QApplication.clipboard().mimeData().data('bigglesworth/MultiStrip')
        stream = QtCore.QDataStream(byteArray)
        #ignore part index
        stream.readInt()
        data = stream.readQVariant()
        if not self.groupEdit:
            self.setPartData(target.part, data, pasteMask)
        else:
            for strip in self.strips:
                if strip.isSelected():
                    self.setPartData(strip.part, data, pasteMask)

    def setCurrentMulti(self, multi):
        self.groupEditBtn.setSwitched(False)
        if not self.currentMulti:
            override = True
        else:
            override = self.currentMulti.index != multi.index
        self.currentMulti = multi
        self.volumeDial.setValue(multi.volume)
        self.tempoDial.setValue(multi.tempo)
        self.display.setCurrent(multi.index, multi.name)

        for part in multi.parts:
            self.strips[part.part].setPartObject(part)
            self.setPartLabels(part.part, part.getInfo(), override)

    def setPartData(self, part, data, pasteMask=MultiStrip.PasteAll):
        self.strips[part].setData(data[3], pasteMask)
        self.setPartLabels(part, data[:3])

    def dragStrip(self, part=None):
        if part is None:
            strip = self.sender()
            widget = strip
            rect = strip.rect()
        else:
            strip = self.strips[part]
            widget = self.sender()
            rect = widget.getStripRect(part)
        dragObject = QtGui.QDrag(strip)

        mimeData = QtCore.QMimeData()
        byteArray = QtCore.QByteArray()
        stream = QtCore.QDataStream(byteArray, QtCore.QIODevice.WriteOnly)
        stream.writeInt(strip.part)
        stream.writeQVariant(strip.getData())
        mimeData.setData('bigglesworth/MultiStrip', byteArray)
        dragObject.setMimeData(mimeData)

        palette = self.palette()
        pm = QtGui.QPixmap(rect.size())
        pm.fill(palette.color(palette.Window))
        qp = QtGui.QPainter(pm)
        widget.render(qp, sourceRegion=QtGui.QRegion(rect))
        qp.end()

        dragObject.setPixmap(pm)
        dragObject.exec_(QtCore.Qt.CopyAction|QtCore.Qt.MoveAction, QtCore.Qt.MoveAction)

    def dropRequested(self, source, target, isOver):
        if isOver:
            res = QuestionMessageBox(self, 'Drop multi part', 
                'You have dropped part {s} on part {t}<br/>Do you want to swap them or overwrite part {t}?'.format(
                    s=source + 1, t=target + 1), 
                buttons={
                    QuestionMessageBox.Ok: ('Swap', QtGui.QIcon.fromTheme('document-swap')), 
                    QuestionMessageBox.Save: ('Overwrite', QtGui.QIcon.fromTheme('edit-copy')), 
                    QuestionMessageBox.Cancel: None
                    }).exec_()
            if res == QuestionMessageBox.Ok:
                self.swapParts(source, target)
            elif res == QuestionMessageBox.Save:
                self.copyPartTo(source, target)
            else:
                return
        else:
            self.movePart(source, target)

    def swapParts(self, source, target):
        sourceData = self.strips[source].getData()
        targetData = self.strips[target].getData()
        self.setPartData(source, targetData)
        self.setPartData(target, sourceData)
#        self.strips[source].setData(targetData, mode=MultiStrip.PasteAll)
#        self.setPartLabels(source, targetData[:3])
#        self.strips[target].setData(sourceData)
#        self.setPartLabels(target, sourceData[:3])

    def copyPartTo(self, source, target):
        targetData = self.strips[source].getData()
        self.setPartData(target, targetData)
#        self.strips[target].setData(targetData, mode=MultiStrip.PasteAll)
#        self.setPartLabels(target, targetData[:3])

    def movePart(self, source, target):
        if source == target + 1 or source == target:
            return
        targetData = self.strips[source].getData()
        sourceData = []
        if source < target:
            for strip in range(source + 1, target + 1):
                sourceData.append(self.strips[strip].getData())
            for strip, data in zip(range(source, target), sourceData):
                self.setPartData(strip, data)
            self.setPartData(target, targetData)
        else:
            for strip in range(target + 1, source):
                sourceData.append(self.strips[strip].getData())
            for strip, data in zip(range(target + 2, source + 1), sourceData):
                self.setPartData(strip, data)
            self.setPartData(target + 1, targetData)

    def sendRequest(self):
        self.groupEditBtn.setSwitched(False)
        deviceId = 0
        bank = self.bankSpin.value()
        prog = self.progSpin.value()
        self.midiEvent.emit(SysExEvent(1, [INIT, IDW, IDE, deviceId, MULR, bank, prog, END]))

    def midiEventReceived(self, event):
        if event.type != SYSEX:
            return
        if not (event.sysex[:3] == [INIT, IDW, IDE] and event.sysex[4] == MULD):
            return
        self.multiReceived(event.sysex)

    def multiReceived(self, sysex):
        #ignore checksum (last value)
        if sysex[-1] == 0xf7:
            multiData = sysex[5:-2]
        else:
            multiData = sysex[5:-1]
        self.setCurrentMulti(MultiObject(multiData))
#        index = multiData[:2]
#        name = multiData[2:18]
#        volume = multiData[19]
#        tempo = multiData[20]
#        boh = multiData[21:34]
#        self.volumeDial.setValue(volume)
#        self.tempoDial.setValue(tempo)
##        print('{1}:{2} {0}'.format(getName(name), *index))
#        self.display.setCurrent(index, getName(name))
#        if boh != [1, 0, 2, 4, 11, 12, 0, 0, 0, 0, 0, 0, 0]:
#            print('other data differs: {}'.format(boh))
#        for part in range(16):
#            data = multiData[34 + part * 24: 34 + (part + 1) * 24]
#            strip = self.strips[part]
#
#            strip.setChannel(data[7])
#            strip.setBank(data[0])
#            strip.setProg(data[1])
#
#            strip.setVolume(data[2])
#            strip.setPan(data[3])
#            #field 4 is probably ignored?
#            if data[4] != 0:
#                print('field 4 is not 0: {}'.format(data[0]))
#            strip.setTranspose(data[5])
#            strip.setDetune(data[6])
#
#            strip.setLowKey(data[8])
#            strip.setHighKey(data[9])
#            strip.setLowVel(data[10])
#            strip.setHighVel(data[11])
#
#            midiByte = data[12]
#            strip.setMidi(midiByte & 1)
#            strip.setUsb(midiByte & 2)
#            strip.setLocal(midiByte & 4)
#            strip.setPlay(midiByte & 64)
#
#            ctrlByte = data[13]
#            strip.setPitch(ctrlByte & 1)
#            strip.setMod(ctrlByte & 2)
#            strip.setPressure(ctrlByte & 4)
#            strip.setSustain(ctrlByte & 8)
#            strip.setEdits(ctrlByte & 16)
#            strip.setProgChange(ctrlByte & 32)
#
#            if data[14:] != [1, 63, 0, 0, 0, 0, 0, 0, 0, 0]:
#                print('final part {} is different! {}'.format(part, data[14:]))

#    def dragEnterEvent(self, event):
#        if event.mimeData().hasFormat('bigglesworth/MultiStrip'):
#            event.accept()
#        else:
#            event.ignore()
#
#    def dragMoveEvent(self, event):
#        if event.mimeData().hasFormat('bigglesworth/MultiStrip') and event.pos() in self.stackedWidget.geometry():
#            widget = QtWidgets.QApplication.widgetAt(QtGui.QCursor.pos())
#            if not widget:
#                return event.ignore()
#            event.accept()
#            self.paintEvent = self.dragPaintEvent
##            if isinstance(widget, MultiStrip):
##                self.dragPaint = 
#        else:
#            event.ignore()

    def changeEvent(self, event):
        if event.type() == QtCore.QEvent.PaletteChange:
            self.display.displayWidget.setPalette(self.palette())

    def resizeEvent(self, event):
        QtWidgets.QWidget.resizeEvent(self, event)
#        self.velocityRangeEditor.velocity.setMaximumHeight(self.keyRangeEditor.piano.sizeHint().height())

#    paintEvent = defaultPaintEvent = lambda *args: QtWidgets.QWidget.paintEvent(*args)
#
#    def dragPaintEvent(self, event):
#        print('aghaaa')
#        QtWidgets.QWidget.paintEvent(self, event)


if __name__ == '__main__':
    if 'linux' in sys.platform:
        from mididings import run, config, Filter, Call, SYSEX as mdSYSEX
        from mididings.engine import output_event as outputEvent
        from mididings.event import SysExEvent as mdSysExEvent

    app = QtWidgets.QApplication(sys.argv)
    multi = MultiEditor()
    multi.show()
    sys.exit(app.exec_())
