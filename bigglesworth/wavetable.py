#!/usr/bin/env python2.7
# *-* coding: utf-8 *-*

import struct
import wave, audioop
from uuid import uuid4
from random import shuffle
from math import sqrt, pow, sin, pi
from PyQt4 import QtCore, QtGui
try:
    from PyQt4 import QtMultimedia
    QTMULTIMEDIA = True
except:
    QTMULTIMEDIA = False

from bigglesworth.utils import load_ui, setBoldItalic
from bigglesworth.const import *
from bigglesworth.dialogs import WaveLoad
from bigglesworth.widgets import MagnifyingCursor, LineCursor, CurveCursor, FreeDrawIcon, LineDrawIcon, CurveDrawIcon
from bigglesworth.libs import midifile

sqrt_center = 4*(sqrt(2)-1)/3
_x0 = _y3 = 0
_y0 = _y1 = _x2 = _x3 = 1
_x1 = _y2 = sqrt_center

undoRole = QtCore.Qt.UserRole + 1
pathRole = QtCore.Qt.UserRole + 1
streamRole = pathRole + 1
gainRole = streamRole + 1
balanceActiveRole = gainRole + 1
balanceValueRole = balanceActiveRole + 1
balanceModeRole = balanceValueRole + 1
balanceLeftRole = balanceModeRole + 1
balanceRightRole = balanceLeftRole + 1

pow22 = 2**22
pow21 = 2**21
pow20 = 2**20
pow19 = 2**19
pow18 = 2**18
pow16 = 2**16
pow14 = 2**14
pow12 = 2**12

DRAW_FREE, DRAW_LINE, DRAW_CURVE = range(3)
REVERSE_WAVES, REVERSE_VALUES, REVERSE_FULL, INVERT_VALUES, SHUFFLE_WAVES, SINE_WAVES, CLEAR_WAVES, INTERPOLATE_VALUES, MORPH_WAVES, DROP_WAVE, DROP_WAVE_SOURCE, WAVETABLE_IMPORT, SLOT_CHANGE, NAME_CHANGE = (16 + i for i in xrange(14))

sine128 = tuple(sin(2 * pi * r * (0.0078125)) for r in xrange(128))

def compute_sqrt_curve(t):
#   original function:
#   X0*(1−t)^3 + 3*X1*(1−t)^2*t + 3*X2*(1−t)*t**2 + X3*t**3
#    x = p0.x*pow((1-t),3) + 3*p1.x*pow((1-t),2)*t + 3*p2.x*(1-t)*pow(t,2) + p3.x*pow(t,3)
#    y = p0.y*pow((1-t),3) + 3*p1.y*pow((1-t),2)*t + 3*p2.y*(1-t)*pow(t,2) + p3.y*pow(t,3)
    x = (3 * _x1 * pow ((1 - t), 2) * t) + (3 * _x2 * (1 - t) * pow(t, 2)) + (_x3 * pow(t, 3))
    y = (_y0 * pow((1 - t), 3)) + (3 * _y1 * pow((1 - t), 2) * t) + (3 * _y2 * (1 - t) * pow(t, 2))
    return x, y

def compute_linear_curve(t):
    return t, 1 - t

compute_fn = compute_linear_curve, compute_sqrt_curve

invalid_msgbox = lambda parent, msg=None: QtGui.QMessageBox.warning(
                                                          parent, 'Wavetable import error', 
                                                          'The selected file does not seem to be a Blofeld Wavetable.{}'.format('\n{}'.format(msg) if msg else '')
                                                          )

class UndoDialog(QtGui.QDialog):
    def __init__(self, main, *args, **kwargs):
        QtGui.QDialog.__init__(self, main, *args, **kwargs)
        load_ui(self, 'dialogs/wavetable_undo.ui')
        self.main = main
        self.undo = self.main.undo
        self.undo_model = QtGui.QStandardItemModel()
        self.undo_list.setModel(self.undo_model)

        original = QtGui.QStandardItem('Initial state')
        setBoldItalic(original, True, False)
        self.undo_model.appendRow(original)

        self.undo.updated.connect(self.update)
        self.undo.indexChanged.connect(self.indexChanged)
        self.undo_list.doubleClicked.connect(self.do_action)
        self.undo_btn.clicked.connect(lambda: self.undo.setIndex(0))
        self.redo_btn.clicked.connect(lambda: self.undo.setIndex(self.undo.count()))

    def update(self):
        self.undo_model.clear()
        index = self.undo.index()
        original = QtGui.QStandardItem('Initial state')
        setBoldItalic(original, True, False)
        self.undo_model.appendRow(original)
        for u in xrange(self.undo.count()):
            cmd = self.undo.command(u)
            item = QtGui.QStandardItem(cmd.text())
#            item.setData(cmd, undoRole)
            if u > index:
                setBoldItalic(item, False, True)
            else:
                setBoldItalic(item, True, False)
            self.undo_model.appendRow(item)

    def indexChanged(self, index):
        for i in xrange(self.undo_model.rowCount()):
            item = self.undo_model.item(i, 0)
            if i > index:
                setBoldItalic(item, False, True)
            else:
                setBoldItalic(item, True, False)

    def do_action(self, index):
        self.undo.setIndex(index.row())


class UndoStack(QtGui.QUndoStack):
    updated = QtCore.pyqtSignal()

    def push(self, cmd):
        QtGui.QUndoStack.push(self, cmd)
        self.updated.emit()


class SingleWaveUndo(QtGui.QUndoCommand):
    def __init__(self, mode, wave_obj):
        QtGui.QUndoCommand.__init__(self)
        self.wave_obj = wave_obj
        self.index = wave_obj.index
        self.previous = wave_obj.values[:]
        if mode == DRAW_FREE:
            self.setText('Freehand draw on wave {}'.format(self.index + 1))
        elif mode == DRAW_LINE:
            self.setText('Line draw on wave {}'.format(self.index + 1))
        else:
            self.setText('Curve draw on wave {}'.format(self.index + 1))

    def finalize(self, values):
        self.values = values[:]

    def undo(self):
        self.wave_obj.setValues(self.previous)

    def redo(self):
        self.wave_obj.setValues(self.values)


class MultiWaveUndo(QtGui.QUndoCommand):
    def __init__(self, mode, waveobj_list, source=None):
        QtGui.QUndoCommand.__init__(self)
        self.values_dict = {}
        selection = []
        for wave_obj in waveobj_list:
            self.values_dict[wave_obj] = [wave_obj.values[:]]
            selection.append(wave_obj.index)
        if len(selection) == 1:
            sel_text = '{}'.format(selection[0] + 1)
            plural = ''
        else:
            sel_text = '{} to {}'.format(selection[0] + 1, selection[-1] + 1)
            plural = 's'
        if mode == REVERSE_WAVES:
            self.setText('Reverse wave{} {}'.format(plural, sel_text))
        elif mode == REVERSE_VALUES:
            self.setText('Reverse values for wave{} {}'.format(plural, sel_text))
        elif mode == REVERSE_FULL:
            self.setText('Reverse values and wave order from {}'.format(sel_text))
        elif mode == INVERT_VALUES:
            self.setText('Invert values for wave{} {}'.format(plural, sel_text))
        elif mode == SHUFFLE_WAVES:
            self.setText('Shuffle wave order from {}'.format(sel_text))
        elif mode == SINE_WAVES:
            self.setText('Reset to sine waveform wave{} {}'.format(plural, sel_text))
        elif mode == CLEAR_WAVES:
            self.setText('Clear values to 0 for wave{} {}'.format(plural, sel_text))
        elif mode == INTERPOLATE_VALUES:
            self.setText('Smooth wawe{} {}'.format(plural, sel_text))
        elif mode == MORPH_WAVES:
            self.setText('Morph wave{} {}'.format(plural, sel_text))
        elif mode == DROP_WAVE:
            self.setText('Drag and drop to wave{} {} from {}'.format(plural, sel_text, source))
        elif mode == WAVETABLE_IMPORT:
            self.setText('Import wavetable from "{}"'.format(source))

    def finalize(self, waveobj_list):
        for wave_obj in waveobj_list:
            self.values_dict[wave_obj].append(wave_obj.values[:])

    def undo(self):
        for wave_obj, values in self.values_dict.items():
            wave_obj.setValues(values[0])

    def redo(self):
        for wave_obj, values in self.values_dict.items():
            wave_obj.setValues(values[1])


class SlotChangeUndo(QtGui.QUndoCommand):
    def __init__(self, spin, original, new=None):
        QtGui.QUndoCommand.__init__(self)
        self.spin = spin
        self.original = int(original)
        self.new = new if new is not None else original
        self.setText('Change slot to {}'.format(new))

    def isChanged(self):
        if self.original != self.new:
            return True
        return False

    def finalize(self, value):
#        self.new = int(value)
        self.new = value
        self.setText('Change slot to {}'.format(value))

    def undo(self):
        self.spin.blockSignals(True)
        self.spin.setValue(self.original)
        self.spin.blockSignals(False)

    def redo(self):
        self.spin.blockSignals(True)
        self.spin.setValue(self.new)
        self.spin.blockSignals(False)

class NameChangeUndo(QtGui.QUndoCommand):
    def __init__(self, edit, original, new):
        QtGui.QUndoCommand.__init__(self)
        self.edit = edit
        self.original = str(original).rstrip()
        self.new = str(new).rstrip()
        self.setText('Change name to "{}"'.format(new))

    def finalize(self, value):
        if str(value).rstrip() != self.original:
            self.new = value
            self.setText('Change slot to {}'.format(value))

    def undo(self):
        self.edit.blockSignals(True)
        self.edit.setText(self.original)
        self.edit.blockSignals(False)

    def redo(self):
        self.edit.blockSignals(True)
        self.edit.setText(self.new)
        self.edit.blockSignals(False)

class DumpDialog(QtGui.QDialog):
    def __init__(self, main):
        QtGui.QDialog.__init__(self, main)
        self.setModal(True)
        layout = QtGui.QGridLayout()
        self.setLayout(layout)

        icon = self.style().standardIcon(QtGui.QStyle.SP_MessageBoxWarning)
        icon_label = QtGui.QLabel(self)
        icon_label.setPixmap(icon.pixmap(32, 32))
        layout.addWidget(icon_label, 0, 0, 2, 1)

        self.label = QtGui.QLabel()
        layout.addWidget(self.label, 0, 1, 1, 1)
        self.setWindowTitle('Wavetable dump')

        layout.addWidget(QtGui.QLabel('Please wait, and do not touch the Blofeld!'), 1, 1, 1, 1)

        self.slot = 80
        self.name = 'MyWavetable001'

    def setData(self, slot, name):
        self.slot = slot
        self.name = name

    def setIndex(self, index):
        self.label.setText(QtCore.QString.fromUtf8('Dumping wavetable "{}" to Blofeld slot {}, current wave: {}'.format(str(self.name.toUtf8()), self.slot, index)))

    def closeEvent(self, event):
        event.ignore()

class Margin(QtGui.QGraphicsItem):
    rect = QtCore.QRectF(0, -100, 5000, 1)
    def __init__(self, height, color=QtGui.QColor(200, 200, 200)):
        QtGui.QGraphicsItem.__init__(self)
        self.rect.setHeight(height)
        self.pen = QtGui.QPen(QtCore.Qt.NoPen)
        self.brush = QtGui.QBrush(color)

    def boundingRect(self):
        return self.rect

    def paint(self, painter, *args, **kwargs):
        painter.setPen(self.pen)
        painter.setBrush(self.brush)
        painter.drawRect(self.rect)


class StartSelectionMargin(Margin):
    rect = QtCore.QRectF(0, -100, -5000, 1)
    def __init__(self, height):
        Margin.__init__(self, height, QtGui.QColor(255, 128, 0, 128))


class EndSelectionMargin(Margin):
    def __init__(self, height):
        Margin.__init__(self, height, QtGui.QColor(255, 128, 0, 128))


class VerticalToggleButton(QtGui.QPushButton):
    def __init__(self, *args, **kwargs):
        QtGui.QPushButton.__init__(self, *args, **kwargs)
        width = self.fontMetrics().lineSpacing() + self.getContentsMargins()[0] + 4
        
        self.setMinimumWidth(width)
        self.setMaximumWidth(width)
        disabled = QtGui.QPen(self.palette().color(QtGui.QPalette.Disabled, QtGui.QPalette.WindowText))
        enabled = QtGui.QPen(self.palette().color(QtGui.QPalette.Active, QtGui.QPalette.WindowText))
        self.text_colors = disabled, enabled
        self.text = ''

    def paintEvent(self, event):
        QtGui.QPushButton.paintEvent(self, event)
        qp = QtGui.QPainter()
        qp.begin(self)
        qp.translate(.5, .5)
        qp.setPen(self.text_colors[self.isEnabled()])
        qp.rotate(270)
        qp.drawText(0, 0, -self.height()-1, self.width()-1, QtCore.Qt.AlignCenter, self.text)
        qp.end()

    def setText(self, text):
        self.text = text


class Wave3DPathItem(QtGui.QGraphicsPathItem):
    wavegrad = QtGui.QLinearGradient()
#    wavegrad.setStart(0, pow19 * .707)
#    wavegrad.setFinalStop(0, pow21 * 1.414)
#    wavegrad.setColorAt(0, QtGui.QColor(128, 128, 128, 255))
#    wavegrad.setColorAt(1, QtGui.QColor(0, 0, 0, 128))
    wavegrad.setStart(0, 0)
    wavegrad.setFinalStop(0, pow21)
    wavegrad.setColorAt(.15, QtGui.QColor(255, 0, 0, 192))
    wavegrad.setColorAt(.35, QtGui.QColor(0, 255, 0, 192))
    wavegrad.setColorAt(.5, QtGui.QColor(128, 255, 192, 255))
    wavegrad.setColorAt(.65, QtGui.QColor(0, 255, 0, 192))
    wavegrad.setColorAt(.85, QtGui.QColor(255, 0, 0, 192))
    wave_pen = QtGui.QPen(wavegrad, 16384)
    selected_pen = QtGui.QPen(QtCore.Qt.red, 16384)
    highlight_pen = QtGui.QPen(QtCore.Qt.blue, 16384)
    wavegrad = QtGui.QBrush(QtGui.QColor(128, 128, 128, 16))

    def __init__(self, path, *args, **kwargs):
        QtGui.QGraphicsPathItem.__init__(self, path, *args, **kwargs)
#        self.setAcceptHoverEvents(True)
        self.setPen(self.wave_pen)
        self.default_pen = self.wave_pen
        self.selected = False

    def select(self, state):
        if state:
            self.setPen(self.selected_pen)
        else:
            self.setPen(self.wave_pen)
        self.selected = state

    def highlight(self, state):
        if self.selected: return
        if not state:
            self.setPen(self.wave_pen)
        else:
            self.setPen(self.highlight_pen)

#    def hoverEnterEvent(self, event):
#        self.setPen(QtCore.Qt.red)
#        self.colliding = [i for i in self.collidingItems() if i.zValue() > self.zValue()]
#        for i in self.colliding:
#            i.setOpacity(.2)
#
#    def hoverLeaveEvent(self, event):
#        self.setPen(self.default_pen)
#        for i in self.colliding:
#            i.setOpacity(1)


class WaveTable3DView(QtGui.QGraphicsView):
    cube_pen = QtGui.QPen(QtGui.QColor(64, 64, 64, 192))

    def __init__(self, *args, **kwargs):
        QtGui.QGraphicsView.__init__(self, *args, **kwargs)
        self.setScene(QtGui.QGraphicsScene())
        self.setRenderHints(QtGui.QPainter.Antialiasing)
        self.setBackgroundBrush(QtGui.QColor(32, 32, 32))
        self.boundingRect = QtCore.QRectF()
        self.slice_transform = QtGui.QTransform().shear(0, 1)
        self.delta_x = 8192
        self.delta_y = 12288
        slice0 = QtGui.QGraphicsRectItem(0, 0, 128 * self.delta_x, pow21)
        slice0.setPen(self.cube_pen)
        slice0.setTransform(self.slice_transform)
        slice1 = QtGui.QGraphicsRectItem(0, 0, 128 * self.delta_x, pow21)
        slice1.setPen(self.cube_pen)
        slice1.setZValue(-200)
        slice1.setTransform(self.slice_transform)
        slice1.setPos(63 * self.delta_x, -63 * self.delta_y)
        self.boundingRect = slice0.sceneBoundingRect().united(slice1.sceneBoundingRect())
        height = self.boundingRect.height()
        self.boundingRect.setTop(-height * .25)
        self.boundingRect.setBottom(height * .85)
        self.scene().setSceneRect(self.boundingRect)

        #add nice 3D cube
        self.scene().addItem(slice0)
        self.scene().addItem(slice1)
        l = self.scene().addLine(slice0.sceneBoundingRect().x(), slice0.sceneBoundingRect().y(), slice1.sceneBoundingRect().x(), slice1.sceneBoundingRect().y())
        l.setPen(self.cube_pen)
        l = self.scene().addLine(QtCore.QLineF(slice0.mapToScene(slice0.boundingRect().topRight()), slice1.mapToScene(slice1.boundingRect().topRight())))
        l.setPen(self.cube_pen)
        l = self.scene().addLine(QtCore.QLineF(slice0.mapToScene(slice0.boundingRect().bottomRight()), slice1.mapToScene(slice1.boundingRect().bottomRight())))
        l.setPen(self.cube_pen)
        l = self.scene().addLine(QtCore.QLineF(slice0.mapToScene(slice0.boundingRect().bottomLeft()), slice1.mapToScene(slice1.boundingRect().bottomLeft())))
        l.setZValue(-200)
        l.setPen(self.cube_pen)

        self.currentWave = None

    def setWaveTable(self, waveobj_list):
#        self.waveobj_list = waveobj_list
        self.wave_list = []
        for w, wave_obj in enumerate(waveobj_list):
            wave_obj.changed.connect(self.updateWave)
            values = wave_obj.values
            wavepath = QtGui.QPainterPath()
            wavepath.moveTo(0, pow20 - values[0])
            for sid, value in enumerate(values[1:], 1):
                wavepath.lineTo(sid * self.delta_x, pow20 - value)
#            wavepath.lineTo(128 * 1024, pow21 * 1.414)
#            wavepath.lineTo(0, pow21 * 1.414)
#            wavepath.lineTo(0, pow21 - values[0])
            slice = Wave3DPathItem(wavepath)
            self.scene().addItem(slice)
            self.wave_list.append(slice)
#            slice.setBrush(self.wavegrad)
            slice.setTransform(self.slice_transform)
            slice.setPos(w * self.delta_x, -w * self.delta_y)
            slice.setZValue(-w)
        self.selectWave(0)

    def updateWaveValue(self, index, sample, value):
        item = self.wave_list[index]
        wavepath = item.path()
        wavepath.setElementPositionAt(sample, wavepath.elementAt(sample).x, pow20 - value)
        item.setPath(wavepath)

    def updateWave(self, wave_obj):
        index = wave_obj.index
        slice = self.wave_list[index]
        values = wave_obj.values
        wavepath = QtGui.QPainterPath()
        wavepath.moveTo(0, pow20 - values[0])
        for sid, value in enumerate(values[1:], 1):
            wavepath.lineTo(sid * self.delta_x, pow20 - value)
        slice.setPath(wavepath)

    def selectWave(self, index):
        if self.currentWave is not None: 
            self.wave_list[self.currentWave].select(False)
        self.wave_list[index].select(True)
        self.currentWave = index

    def resizeEvent(self, event):
#        print self.wave_list
#        self.fitInView(0, 0, self.boundingRect.width(), pow22)
        self.fitInView(self.boundingRect)


class WaveSourceView(QtGui.QGraphicsView):
    sampleSelectionChanged = QtCore.pyqtSignal(int, int)
    statusTip = QtCore.pyqtSignal(str)

    def __init__(self, main, *args, **kwargs):
        QtGui.QGraphicsView.__init__(self, main, *args, **kwargs)
        self.main = main
#        self.setToolTip('Shift+click to select a wave range, then drag the selection to the wave table list.')
        self.setScene(QtGui.QGraphicsScene())
        self.setRenderHints(QtGui.QPainter.Antialiasing)
        self.setBackgroundBrush(QtCore.Qt.white)
        self.setMouseTracking(True)
        self.viewport().installEventFilter(self)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.wave_pen = QtGui.QPen(QtGui.QColor(QtCore.Qt.darkGray), 2)
        self.wave_pen_ghost = QtGui.QPen(QtGui.QColor(QtCore.Qt.lightGray), 2)

        self.magnifying_cursor = MagnifyingCursor()

        self.wavepath = self.scene().addPath(QtGui.QPainterPath())
        self.samplepath = self.scene().addPath(QtGui.QPainterPath())
        self.current_samplepath = self.scene().addPath(QtGui.QPainterPath())
        self.current_sampwidth_int = 2**16
        self.current_sampwidth = 2
        self.current_data = None
        self.current_items = None
        self.current_index = None
        self.current_source = ''
        self.cache = {}
        self.offset = self.offset_pos = 0

        self.zoom_values = tuple(2**e for e in xrange(2, 10))
        self.zoom = self.zoom_values.index(256)

        self.split_waves = []
        split_pen = QtGui.QPen(QtGui.QColor(QtGui.QColor(88, 88, 250, 120)), .0625)
        split_height = self.current_sampwidth_int*1.2
        self.left_margin = self.wave_pen.width()*.25
        self.grid = QtGui.QGraphicsItemGroup()
        self.grid.setZValue(2)
        for i in xrange(4096):
            wave = self.scene().addRect(i*2, 0, 2, split_height)
            self.grid.addToGroup(wave)
            wave.setFlags(QtGui.QGraphicsItem.ItemIsSelectable)
            wave.setPen(split_pen)
            wave.setData(0, i)
            self.split_waves.append(wave)
        self.scene().addItem(self.grid)

        self.right_margin_item = Margin(split_height)
        self.scene().addItem(self.right_margin_item)
        self.right_margin_item.setZValue(10)
        self.right_margin_item.setX(500)

        self.start_selection_margin = StartSelectionMargin(split_height)
        self.scene().addItem(self.start_selection_margin)
        self.start_selection_margin.setZValue(10)
        self.start_selection_margin.setVisible(False)
        self.end_selection_margin = EndSelectionMargin(split_height)
        self.scene().addItem(self.end_selection_margin)
        self.end_selection_margin.setZValue(10)
        self.end_selection_margin.setVisible(False)

#        self.setDragMode(self.RubberBandDrag)
        self.scene().selectionChanged.connect(self.selection_update)

        self.selection = None

        self.shown = False

    def selection_update(self):
        select_path = self.scene().selectionArea()
        self.start_selection_margin.setVisible(True)
        self.end_selection_margin.setVisible(True)
        items = [i for i in self.scene().items(select_path, QtCore.Qt.IntersectsItemBoundingRect, QtCore.Qt.AscendingOrder) if isinstance(i, QtGui.QGraphicsRectItem)]
#        self.start_selection_margin.setX(items[0].boundingRect().x())
#        print select_path.boundingRect(), self.mouse_x
#        print ', '.join(str(i.data(0).toPyObject()) for i in items)
        if len(items) <= 128:
            first = items[0]
            last = items[-1]
            first_id = first.data(0).toPyObject()
            last_id = last.data(0).toPyObject()
            self.start_selection_margin.setX(first.boundingRect().x())
            self.end_selection_margin.setX(last.boundingRect().right())
            self.sampleSelectionChanged.emit(first_id, last_id)
            self.selection = first_id, last_id
        QtCore.QTimer.singleShot(0, lambda: self.scene().update(self.mapToScene(self.viewport().rect()).boundingRect()))
#        else:
#            if select_path.boundingRect().x() > self.mouse_x:
#                first = items[0]
#                last = items[127]
#                self.start_selection_margin.setX(first.boundingRect().x())
#                self.end_selection_margin.setX(last.boundingRect().x())
                
#        self.start_selection_margin.update()

    def showEvent(self, event):
        if not self.shown:
            self.shown = True
            width = self.mapToScene(self.viewport().rect()).boundingRect().width()
            QtCore.QTimer.singleShot(0, lambda: self.scene().setSceneRect(-self.left_margin, 0, width, self.current_sampwidth_int))

    def eventFilter(self, source, event):
        if source == self.viewport() and event.type() == QtCore.QEvent.Leave:
            self.leaveEvent(event)
        return QtGui.QGraphicsView.eventFilter(self, source, event)

    def setMain(self, main):
        self.main = main

    def clear(self):
        self.scene().removeItem(self.wavepath)
        self.fitInView(0, 0, 1, 1)
        self.wavepath = self.scene().addPath(QtGui.QPainterPath())

    def set_offset(self, offset):
        self.offset = offset
        self.offset_pos = offset/64.
        self.grid.setX(self.offset_pos)

    def draw_wave(self, stream, force=False):
#        print stream.getnframes()
        if self.wavepath:
            self.scene().removeItem(self.wavepath)
            self.fitInView(0, 0, 1, 1)
        self.current_sampwidth = sampwidth = stream.getsampwidth()
        self.current_sampwidth_int = delta = 2**(8*sampwidth)
        if stream in self.cache and not force:
            self.current_data, wavepath = self.cache[stream]
        else:
            stream.rewind()
            frames = stream.getnframes()
            ratio = frames / 64
            if stream.getnchannels() == 2:
                data = audioop.tomono(stream.readframes(float('inf')), sampwidth, self.main.left_spin.value(), self.main.right_spin.value())
            else:
                data = stream.readframes(float('inf'))
            data = audioop.mul(data, sampwidth, self.main.gain)
            self.current_data = data
            wavepath = QtGui.QPainterPath()
            try:
                for frame_set in xrange(ratio):
                    frame_min = frame_max = 0
                    for frame in xrange(64):
                        try:
                            value = audioop.getsample(data, sampwidth, frame + frame_set * 64)
                            frame_min = min(frame_min, value)
                            frame_max = max(frame_max, value)
                        except:
                            break
                    if frame == 0:
                        break
                    wavepath.moveTo(frame_set, delta - frame_min)
                    wavepath.lineTo(frame_set, delta - frame_max)
            except:
                pass
            self.cache[stream] = data, wavepath
        self.wavepath = self.scene().addPath(wavepath)
        self.wavepath.setPen(self.wave_pen)
        self.wavepath.setY(-delta * .5)
        self.wavepath.setX(self.left_margin*2)
        self.fitInView(0, 0, self.zoom_values[self.zoom], delta)
        if not force:
            self.centerOn(self.wavepath)
        self.right_margin_item.setX(len(self.current_data)/self.current_sampwidth/64)

        visible = self.mapToScene(self.viewport().rect()).boundingRect()
        if visible.width() > self.wavepath.boundingRect().width():
            self.scene().setSceneRect(-self.left_margin, 0, visible.width(), delta)
        else:
            self.scene().setSceneRect(-self.left_margin, 0, self.wavepath.boundingRect().width(), delta)

    def createDragData(self):
        self.drag = QtGui.QDrag(self)
        data = QtCore.QMimeData()
        wave_len = self.selection[1] + 1 - self.selection[0]
        samples = self.current_data[self.selection[0] * 256 + self.offset:(self.selection[1] + 1) * 256 + self.offset]
        data.setData('audio/wavesamples', samples)
        data.setText(self.current_source)
        path = QtGui.QPainterPath()
        sampwidth_int = self.current_sampwidth_int / 2
        path.moveTo(0, sampwidth_int - audioop.getsample(samples, self.current_sampwidth, 0))
        for s in xrange(1, len(samples)/2):
            path.lineTo(s, sampwidth_int - audioop.getsample(samples, self.current_sampwidth, s))
        wave_size = self.main.wavetable_view.width() / 64
        pixmap = QtGui.QPixmap(wave_size * wave_len, 48)
        pixmap.fill(QtCore.Qt.transparent)
        qp = QtGui.QPainter(pixmap)
        qp.setRenderHints(qp.Antialiasing)
        qp.scale((wave_size * wave_len / path.boundingRect().width()), 48. / self.current_sampwidth_int)
        qp.drawPath(path)
        qp.end()
        self.drag.setPixmap(pixmap)
        self.drag.setMimeData(data)
        self.drag.exec_()

    def mousePressEvent(self, event):
        if event.modifiers() == QtCore.Qt.ShiftModifier:
            self.setDragMode(self.RubberBandDrag)
        else:
            if not (self.current_data and self.selection): return
#            self.setDragMode(self.ScrollHandDrag)
            self.setDragMode(self.NoDrag)
            self.createDragData()
            return
        QtGui.QGraphicsView.mousePressEvent(self, event)
        self.mouse_x = self.mapToScene(event.pos())

    def mouseMoveEvent(self, event):
        if isinstance(event, QtGui.QMouseEvent):
            QtGui.QGraphicsView.mouseMoveEvent(self, event)
        if not self.current_data or self.zoom >= 5: return
        items = [i for i in self.items(self.viewport().rect()) if isinstance(i, QtGui.QGraphicsRectItem)]
        if not items: return
        current = [i for i in self.items(event.pos()) if isinstance(i, QtGui.QGraphicsRectItem)]
        try:
            current_index = current[0].data(0).toPyObject()
        except:
            current_index = None
        items = sorted(items, key=lambda i: i.data(0).toPyObject())
        if items == self.current_items and current_index == self.current_index:
            return
        else:
            self.current_items = items
            self.current_index = current_index
        self.scene().removeItem(self.samplepath)
        current_path = QtGui.QPainterPath()
        samplepath = QtGui.QPainterPath()
        max_len = len(self.current_data)/self.current_sampwidth/128
        sample0 = audioop.getsample(self.current_data, self.current_sampwidth, items[0].data(0).toPyObject() * 128)
        samplepath.moveTo(0, self.current_sampwidth_int - sample0)
        for item in items:
            index = item.data(0).toPyObject()
            index_delta = index * 128
            index_pos = index * 2
            if index >= max_len:
                break
            elif index == current_index:
                self.scene().removeItem(self.current_samplepath)
                current_sample = audioop.getsample(self.current_data, self.current_sampwidth, index_delta + self.offset)
                current_path.moveTo(index_pos, self.current_sampwidth_int - current_sample)
                for sample in xrange(128):
                    try:
                        value = audioop.getsample(self.current_data, self.current_sampwidth, index_delta + sample + self.offset)
                        current_path.lineTo(index_pos + sample/64., self.current_sampwidth_int - value)
                    except:
                        break
                current_item = self.scene().addPath(current_path)
                current_item.setPen(QtCore.Qt.darkGreen)
                current_item.setY(self.wavepath.y())
                current_item.setX(self.offset_pos)
                current_item.setZValue(1)
                self.current_samplepath = current_item
                try:
                    next_value = audioop.getsample(self.current_data, self.current_sampwidth, (index + 1) * 128 + self.offset)
                    samplepath.moveTo((index + 1) * 2, self.current_sampwidth_int - next_value)
                except Exception as e:
                    print type(e), e
                    pass
                continue
            for sample in xrange(128):
                try:
                    value = audioop.getsample(self.current_data, self.current_sampwidth, index_delta + sample + self.offset)
                    samplepath.lineTo(index_pos + sample/64., self.current_sampwidth_int - value)
                except:
                    break
        path_item = self.scene().addPath(samplepath)
        path_item.setPen(QtCore.Qt.darkRed)
        path_item.setY(self.wavepath.y())
        path_item.setX(self.offset_pos)
        path_item.setZValue(1)
        self.wavepath.setPen(self.wave_pen_ghost)
        self.samplepath = path_item

    def enterEvent(self, event):
        QtGui.QGraphicsView.enterEvent(self, event)
        self.statusTip.emit('Ctrl+MouseWheel for zoom, Shift to select a sample range.')

    def leaveEvent(self, event):
        self.statusTip.emit('')
        self.wavepath.setPen(self.wave_pen)
        self.scene().removeItem(self.samplepath)
        self.scene().removeItem(self.current_samplepath)
        self.samplepath = self.scene().addPath(QtGui.QPainterPath())
        self.current_samplepath = self.scene().addPath(QtGui.QPainterPath())
        self.current_index = self.current_items = None

    def keyPressEvent(self, event):
        if event.modifiers() & QtCore.Qt.ControlModifier:
            self.setCursor(self.magnifying_cursor)
#            QtGui.QApplication.setOverrideCursor(QtGui.QCursor(QtCore.Qt.SizeAllCursor))

    def keyReleaseEvent(self, event):
        if not event.modifiers() & QtCore.Qt.ControlModifier:
            self.unsetCursor()

    def wheelEvent(self, event):
        if event.modifiers() & QtCore.Qt.ControlModifier:
#            center = QtCore.QPointF(self.mapToScene(event.pos()).x(), self.wavepath.boundingRect().center().y())
            center = QtCore.QPointF(self.mapToScene(event.pos()).x(), self.mapToScene(self.viewport().rect().center()).y())
            if event.delta() > 0:
                self.zoom = self.zoom - 1 if self.zoom > 0 else 0
            else:
                self.zoom = self.zoom + 1 if self.zoom < len(self.zoom_values) - 1 else self.zoom
            self.fitInView(0, 0, self.zoom_values[self.zoom], self.current_sampwidth_int)
            visible = self.mapToScene(self.viewport().rect()).boundingRect()
            if visible.width() > self.wavepath.boundingRect().width():
                self.scene().setSceneRect(-self.left_margin, 0, visible.width(), self.current_sampwidth_int)
            else:
                self.scene().setSceneRect(-self.left_margin, 0, self.wavepath.boundingRect().width(), self.current_sampwidth_int)
            self.centerOn(center)
        elif event.modifiers() & QtCore.Qt.ShiftModifier:
            event = QtGui.QWheelEvent(event.pos(), event.delta()*5, event.buttons(), event.modifiers(), QtCore.Qt.Horizontal)
            QtGui.QGraphicsView.wheelEvent(self, event)
            self.mouseMoveEvent(event)
        else:
            event = QtGui.QWheelEvent(event.pos(), event.delta(), event.buttons(), event.modifiers(), QtCore.Qt.Horizontal)
            QtGui.QGraphicsView.wheelEvent(self, event)
            self.mouseMoveEvent(event)

    def resizeEvent(self, event):
        if not self.shown: return
        self.fitInView(0, 0, 256, self.current_sampwidth_int)
        self.centerOn(self.wavepath)


class WavePlaceHolderItem(QtGui.QGraphicsWidget):
    bgd_normal_brush = QtGui.QBrush(QtCore.Qt.NoBrush)
    bgd_highlight_brush = QtGui.QBrush(QtGui.QColor(128, 192, 192, 128))
    bgd_selected_brush = QtGui.QBrush(QtGui.QColor(192, 192, 192, 128))
    bgd_selected_highlight_brush = QtGui.QBrush(QtGui.QColor(96, 128, 128, 128))
    bgd_brushes = bgd_normal_brush, bgd_highlight_brush, bgd_selected_brush, bgd_selected_highlight_brush

    def __init__(self, main, index, rect, *args, **kwargs):
        QtGui.QGraphicsWidget.__init__(self, *args, **kwargs)
        self.main = main
        self.index = index
        rect.setTop(-100)
        rect.setBottom(rect.bottom()+100)
        self.setGeometry(rect)
        self.setAcceptHoverEvents(True)
        self.pen = QtGui.QPen(QtGui.QColor(QtCore.Qt.lightGray))
        self.brush = self.bgd_brushes[0]
        self.index_item = QtGui.QGraphicsTextItem(str(index+1), self)
        self.index_item.setFlags(self.index_item.ItemIgnoresTransformations)
        font = self.index_item.font()
        font.setPointSize(7)
        self.index_item.setFont(font)
        self.index_item.setY(90)
        self.index_item.setTextWidth(20)
        if (self.index+1) % 8:
            self.index_item.setVisible(False)
        else:
            self.index_item.setX(-16)
        self.selected = False
        self.highlight = False

    def hoverEnterEvent(self, event):
        self.main.hover.emit(True)
        if not (self.index+1) % 8: return
        real_width = self.deviceTransform(self.scene().views()[0].viewportTransform()).mapRect(self.boundingRect()).width()
        if real_width < 12:
            self.index_item.setX(-real_width*2)
        else:
            self.index_item.setX(0)
        self.index_item.setVisible(True)

    def hoverLeaveEvent(self, event):
        self.main.hover.emit(False)
        if not (self.index+1) % 8: return
        self.index_item.setVisible(False)

    def mousePressEvent(self, event):
        self.main.selected.emit(self.main)
        QtGui.QGraphicsWidget.mousePressEvent(self, event)

    def setSelected(self, state):
        self.brush = self.bgd_brushes[self.highlight + state * 2]
        self.selected = state
        self.update()

    def setHighlight(self, state):
        self.brush = self.bgd_brushes[state + self.selected * 2]
        self.highlight = state
        self.update()

    def paint(self, painter, *args, **kwargs):
        painter.setPen(self.pen)
        painter.setBrush(self.brush)
        painter.drawRect(0, 0, self.size().width(), self.size().height())


class WaveObject(QtCore.QObject):
    hover = QtCore.pyqtSignal(bool)
    selected = QtCore.pyqtSignal(object)
    valueChanged = QtCore.pyqtSignal(object)
    changed = QtCore.pyqtSignal(object)

    sine_values = []
    sine_preview_wavepath = QtGui.QPainterPath()
    sine_wavepath = QtGui.QPainterPath()
    for p, sine in enumerate(sine128):
        sine_preview_wavepath.lineTo(p, -sine*16)
        _value = int(sine*pow19)
        sine_values.append(_value)
        sine_wavepath.lineTo(p*16384, -_value)
    sine_preview_wavepath.translate(0, 32)
    sine_wavepath.translate(0, pow20)
    normal_pen = QtGui.QPen(QtCore.Qt.black)
    hover_pen = QtGui.QPen(QtCore.Qt.darkGreen)
    selected_pen = QtGui.QPen(QtCore.Qt.red)
    preview_pens = normal_pen, hover_pen, selected_pen

    def __init__(self, index, values=None):
        QtCore.QObject.__init__(self)
        self.index = index
        self.values = self.sine_values
        #do we really need to create a self.preview_path?
        self.preview_path = QtGui.QPainterPath(self.sine_preview_wavepath)
        self.preview_path_item = QtGui.QGraphicsPathItem(self.preview_path)
        self.preview_path_item.setFlag(QtGui.QGraphicsPathItem.ItemIsSelectable)
        self.preview_rect = WavePlaceHolderItem(self, index, self.preview_path_item.boundingRect())
        self.path = QtGui.QPainterPath(self.sine_wavepath)
        self.hover.connect(self.preview_highlight)
        self._selected_state = False
        #this is a *BAD* workaround for setting values (vertical alignment problem) fix it!
        if values is not None:
            QtCore.QTimer.singleShot(0, lambda: self.setValues(values))

    @property
    def selected_state(self):
        return self._selected_state

    @selected_state.setter
    def selected_state(self, select):
        self._selected_state = select
        if not select:
            self.preview_path_item.setPen(self.preview_pens[0])
        else:
            self.preview_path_item.setPen(self.preview_pens[2])

    def setValues(self, values):
        self.values = list(values)
        for index, value in enumerate(values):
            self.preview_path.setElementPositionAt(index, index, 32 - value/32768)
            self.path.setElementPositionAt(index, index*16384, pow20 - value)
        self.preview_path_item.setPath(self.preview_path)
        self.changed.emit(self)
        #dirty. check it!
#        self.valueChanged.emit(self)

    def setValue(self, index, value):
        self.values[index] = value
        self.changed.emit(self)
        self.preview_path.setElementPositionAt(index, index, 32 - value/32768)
        self.preview_path_item.setPath(self.preview_path)
        self.path.setElementPositionAt(index, index*16384, pow20 - value)

    def reset(self, ratio=1.):
        if ratio == 1:
            self.values = self.sine_values[:]
            self.preview_path = QtGui.QPainterPath(self.sine_preview_wavepath)
            self.preview_path_item.setPath(self.preview_path)
            self.path = QtGui.QPainterPath(self.sine_wavepath)
        self.changed.emit(self)
#        self.valueChanged.emit(self)

    def clear(self):
        self.values = []
        self.preview_path = QtGui.QPainterPath()
        self.path = QtGui.QPainterPath()
        for p in xrange(128):
            self.values.append(0)
            self.preview_path.lineTo(p, 0)
            self.path.lineTo(p*16384, 0)
        self.preview_path.translate(0, 32)
        self.path.translate(0, pow20)
        self.preview_path_item.setPath(self.preview_path)
        self.changed.emit(self)
#        self.valueChanged.emit(self)

    def interpolate(self, stat_range=3):
        values = []
        delta = (stat_range - 1) / 2
        for c in xrange(128):
            stats = []
            if c - delta < 0:
                for i in xrange(delta):
                    stats.append(self.values[127 - delta + i])
            else:
                for i in xrange(delta):
                    stats.append(self.values[c - delta + i])
            stats.append(self.values[c])
            if c + delta > 127:
                for i in xrange(delta):
                    stats.append(self.values[i])
            else:
                for i in xrange(delta):
                    stats.append(self.values[c + delta + i])
            values.append(int(float(sum(stats)) / stat_range))
        self.setValues(values)

    def preview_highlight(self, state):
        if not self.selected_state:
            self.preview_path_item.setPen(self.preview_pens[state])

class MimeData(QtCore.QMimeData):
    def __init__(self):
        QtCore.QMimeData.__init__(self)
        self.referenceDataObject = None

    def hasFormat(self, mime):
        if mime == 'data/reference' and self.referenceDataObject:
            return True
        return QtCore.QMimeData.hasFormat(self, mime)

    def setReferenceData(self, obj):
        self.referenceDataObject = obj

    def referenceData(self):
        return self.referenceDataObject


class WaveTableView(QtGui.QGraphicsView):
    editAction = QtCore.pyqtSignal(int, bool, object)
    dropAction = QtCore.pyqtSignal(int, bool, object, str)

    def __init__(self, *args, **kwargs):
        QtGui.QGraphicsView.__init__(self, *args, **kwargs)
        self.setScene(QtGui.QGraphicsScene())
        self.setRenderHints(QtGui.QPainter.Antialiasing)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.customContextMenuRequested.connect(self.show_menu)
        self.clipboard = None
        self.selection = None
        self.currentWave = 0
        self.scene().selectionChanged.connect(self.selection_update)
        self.setDragMode(self.RubberBandDrag)

    def setMain(self, main):
        self.main = main

    def createDragData(self):
        if not self.selection: return
        start = self.selection[0]
        end = self.selection[-1]
        if start == end:
            self.waveobj_list[start].preview_rect.setSelected(True)
        self.drag = QtGui.QDrag(self)
        data = MimeData()
        data.setData('audio/waves', QtCore.QByteArray('{}:{}'.format(start, end)))
        data.setReferenceData(self.main)
        pixmap = QtGui.QPixmap(int(self.viewport().rect().width() / 64. * (end - start + 1)), self.height())
        pixmap.fill(QtGui.QColor(192, 192, 192, 128))
        qp = QtGui.QPainter(pixmap)
        qp.setRenderHints(qp.Antialiasing)
        x = self.mapFromScene(self.waveobj_list[start].preview_rect.pos()).x()
        width = self.mapFromScene(self.waveobj_list[end].preview_rect.pos()).x() + self.mapFromScene(self.waveobj_list[end].preview_rect.boundingRect().topRight()).x() - x
        self.render(qp, source=QtCore.QRect(x, self.wavegroup.boundingRect().y(), width, self.mapToScene(self.viewport().rect()).boundingRect().height()), mode=QtCore.Qt.IgnoreAspectRatio)
        qp.end()
        self.drag.setPixmap(pixmap)
        self.drag.setMimeData(data)
        self.drag.exec_()

    def selection_update(self):
        select_path = self.scene().selectionArea()
        items = [i for i in self.scene().items(select_path) if isinstance(i, WavePlaceHolderItem)]
        if not items: return
        selection = [item.index for item in items]
        for i, r in enumerate(self.waveobj_list):
            r.preview_rect.setSelected(True if i in selection else False)
        self.selection = sorted(selection)

    def keyPressEvent(self, event):
        if event.key() in (QtCore.Qt.Key_Right, QtCore.Qt.Key_Down):
            if self.currentWave < 63:
                wave_obj = self.waveobj_list[self.currentWave + 1]
                wave_obj.selected.emit(wave_obj)
        elif event.key() in (QtCore.Qt.Key_Left, QtCore.Qt.Key_Up):
            if self.currentWave > 0:
                wave_obj = self.waveobj_list[self.currentWave - 1]
                wave_obj.selected.emit(wave_obj)
        elif event.key() == QtCore.Qt.Key_Home:
            wave_obj = self.waveobj_list[0]
            wave_obj.selected.emit(wave_obj)
        elif event.key() == QtCore.Qt.Key_End:
            wave_obj = self.waveobj_list[-1]
            wave_obj.selected.emit(wave_obj)
        elif event.key() == QtCore.Qt.Key_PageUp:
            index = self.currentWave - 8
            if index < 0:
                index = 0
            wave_obj = self.waveobj_list[index]
            wave_obj.selected.emit(wave_obj)
        elif event.key() == QtCore.Qt.Key_PageDown:
            index = self.currentWave + 8
            if index > 63:
                index = 63
            wave_obj = self.waveobj_list[index]
            wave_obj.selected.emit(wave_obj)

    def mousePressEvent(self, event):
        QtGui.QGraphicsView.mousePressEvent(self, event)
        if event.modifiers() == QtCore.Qt.ShiftModifier:
            self.setDragMode(self.RubberBandDrag)
        else:
            self.setDragMode(self.NoDrag)
            items = [i.index for i in self.items(event.pos()) if isinstance(i, WavePlaceHolderItem)]
            if not items: return
            if self.selection:
                if items[0] not in self.selection:
                    self.selection = [items[0]]
                    [r.preview_rect.setSelected(False) for r in self.waveobj_list]
            else:
                self.selection = [items[0]]

    def mouseMoveEvent(self, event):
        QtGui.QGraphicsView.mouseMoveEvent(self, event)
        if event.buttons() == QtCore.Qt.LeftButton and not event.modifiers() == QtCore.Qt.ShiftModifier:
            self.createDragData()

    def focusOutEvent(self, event):
        if event.reason() != QtCore.Qt.PopupFocusReason:
            self.selection = None
            [r.preview_rect.setSelected(False) for r in self.waveobj_list]

    def show_menu(self, pos):
        items = [i for i in self.items(pos) if isinstance(i, WavePlaceHolderItem)]
        if not items: return
        index = items[0].index
        wave_obj = self.waveobj_list[index]
        menu = QtGui.QMenu()
        menu.setSeparatorsCollapsible(False)
        if len(self.selection) > 1 and index in self.selection:
            title = QtGui.QAction('Selection', menu)
            title.setSeparator(True)
            reverse = QtGui.QAction('Reverse wave order', menu)
            reverse_values = QtGui.QAction('Reverse wave values', menu)
            reverse_full = QtGui.QAction('Reverse wave values and order', menu)
            invert = QtGui.QAction('Invert waves', menu)
            morph = QtGui.QAction('Morph waves', menu)
            if len(self.selection) < 3:
                morph.setEnabled(False)
            sep0 = QtGui.QAction(menu)
            sep0.setSeparator(True)
            shuffle_ = QtGui.QAction('Randomize wave order', menu)
            sep1 = QtGui.QAction(menu)
            sep1.setSeparator(True)
            sine = QtGui.QAction('Reset waves to sine', menu)
            clear = QtGui.QAction('Clear waves', menu)
            menu.addActions([title, reverse, reverse_values, reverse_full, invert, morph, sep0, shuffle_, sep1, sine, clear])
            res = menu.exec_(self.mapToGlobal(pos))
            if not res: return
            if res == reverse:
                self.reverse_waves(self.selection)
            elif res == reverse_values:
                self.reverse_wave_values(self.selection)
            elif res == reverse_full:
                self.reverse_full(self.selection)
            elif res == invert:
                self.invert_waves(self.selection)
            elif res == morph:
                self.morph_waves(self.selection)
            elif res == shuffle_:
                self.shuffle_waves(self.selection)
            elif res == sine:
                self.sine_waves(self.selection)
            elif res == clear:
                self.clear_waves(self.selection)
            wave_obj.selected.emit(wave_obj)
        else:
            title = QtGui.QAction('Wave {}'.format(index + 1), menu)
            title.setSeparator(True)
            reverse = QtGui.QAction('Reverse wave', menu)
            invert = QtGui.QAction('Invert wave', menu)
            sine = QtGui.QAction('Reset wave to sine', menu)
            clear = QtGui.QAction('Clear wave', menu)
            sep0 = QtGui.QAction(menu)
            sep0.setSeparator(True)
            copy = QtGui.QAction('Copy', menu)
            duplicate = QtGui.QAction('Duplicate to all wavetable', menu)
            if self.clipboard is not None:
                paste = QtGui.QAction('Paste wave {} here'.format(self.clipboard + 1), menu)
                if index == self.clipboard:
                    paste.setEnabled(False)
            else:
                paste = QtGui.QAction('Paste', menu)
                paste.setEnabled(False)
            sep1 = QtGui.QAction(menu)
            sep1.setSeparator(True)
            selectall = QtGui.QAction('Select all', menu)
            menu.addActions([title, reverse, invert, sine, clear, sep0, copy, duplicate, paste, sep1, selectall])
            res = menu.exec_(self.mapToGlobal(pos))
            if not res: return
            if res == reverse:
                self.reverse_wave_values([index])
                wave_obj.selected.emit(wave_obj)
            elif res == invert:
                self.invert_waves([index])
                wave_obj.selected.emit(wave_obj)
            elif res == sine:
                self.sine_waves([index])
                wave_obj.selected.emit(wave_obj)
            elif res == clear:
                self.clear_waves([index])
                wave_obj.selected.emit(wave_obj)
            elif res == copy:
                self.clipboard = index
            elif res == duplicate:
                for w in self.waveobj_list:
                    if w == wave_obj: continue
                    w.setValues(wave_obj.values)
            elif res == paste:
                wave_obj.setValues(self.waveobj_list[self.clipboard].values)
                wave_obj.selected.emit(wave_obj)
            elif res == selectall:
                for r in self.waveobj_list:
                    r.preview_rect.setSelected(True)
                self.selection = list(xrange(64))

#    Hey, what about decorators?!
    def reverse_waves(self, selection=None):
        if not selection:
            selection = tuple(xrange(64))
        waveobj_list = self.waveobj_list[selection[0]:selection[-1] + 1]
        self.editAction.emit(REVERSE_WAVES, True, waveobj_list)
        values_list = [wave_obj.values for wave_obj in reversed(waveobj_list)]
        for i, wave_obj in enumerate(waveobj_list):
            wave_obj.setValues(values_list[i])
        self.editAction.emit(REVERSE_WAVES, False, waveobj_list)

    def reverse_wave_values(self, selection=None):
        if not selection:
            selection = tuple(xrange(64))
        waveobj_list = self.waveobj_list[selection[0]:selection[-1] + 1]
        self.editAction.emit(REVERSE_VALUES, True, waveobj_list)
        for wave_obj in waveobj_list:
            wave_obj.setValues(tuple(reversed(wave_obj.values)))
        self.editAction.emit(REVERSE_VALUES, False, waveobj_list)

    def reverse_full(self, selection=None):
        if not selection:
            selection = tuple(xrange(64))
        waveobj_list = self.waveobj_list[selection[0]:selection[-1] + 1]
        self.editAction.emit(REVERSE_FULL, True, waveobj_list)
        self.blockSignals(True)
        self.reverse_waves(selection)
        self.reverse_wave_values(selection)
        self.blockSignals(False)
        self.editAction.emit(REVERSE_FULL, False, waveobj_list)

    def invert_waves(self, selection=None):
        if not selection:
            selection = tuple(xrange(64))
        waveobj_list = self.waveobj_list[selection[0]:selection[-1] + 1]
        self.editAction.emit(INVERT_VALUES, True, waveobj_list)
        for wave_obj in waveobj_list:
            wave_obj.setValues(tuple(v * -1 for v in wave_obj.values))
        self.editAction.emit(INVERT_VALUES, False, waveobj_list)

    def morph_waves(self, selection=None):
        if not selection:
            selection = tuple(xrange(64))
        waveobj_list = self.waveobj_list[selection[1]:selection[-1]]
        self.editAction.emit(MORPH_WAVES, True, waveobj_list)
        interpolation = [[] for i in xrange(len(waveobj_list))]
        div = selection[-1] - selection[0] + 1
        values_first = iter(self.waveobj_list[selection[0]].values)
        values_last = iter(self.waveobj_list[selection[-1]].values)
        for s in xrange(128):
            first = values_first.next()
            ratio = (values_last.next() - first) / div
            for w in xrange(div - 2):
                interpolation[w].append(first + (w + 1) * ratio)
        for w, wave_obj in enumerate(waveobj_list):
            wave_obj.setValues(interpolation[w])
        self.editAction.emit(INVERT_VALUES, False, waveobj_list)

    def shuffle_waves(self, selection=None):
        if not selection:
            selection = tuple(xrange(64))
            shuffled = tuple(xrange(64))
        else:
            shuffled = selection[:]
        shuffle(shuffled)
        waveobj_list = self.waveobj_list[selection[0]:selection[-1] + 1]
        self.editAction.emit(SHUFFLE_WAVES, True, waveobj_list)
        values_list = [self.waveobj_list[i].values for i in shuffled]
        for i, wave_obj in enumerate(waveobj_list):
            wave_obj.setValues(values_list[i])
        self.editAction.emit(SHUFFLE_WAVES, False, waveobj_list)

    def sine_waves(self, selection=None):
        if not selection:
            selection = tuple(xrange(64))
        waveobj_list = self.waveobj_list[selection[0]:selection[-1] + 1]
        self.editAction.emit(SINE_WAVES, True, waveobj_list)
        for wave_obj in waveobj_list:
            wave_obj.reset()
        self.editAction.emit(SINE_WAVES, False, waveobj_list)

    def clear_waves(self, selection=None):
        if not selection:
            selection = tuple(xrange(64))
        waveobj_list = self.waveobj_list[selection[0]:selection[-1] + 1]
        self.editAction.emit(CLEAR_WAVES, True, waveobj_list)
        for wave_obj in waveobj_list:
            wave_obj.clear()
        self.editAction.emit(CLEAR_WAVES, False, waveobj_list)

    def interpolate_values(self, selection=None, stat_range=3):
        if not selection:
            selection = tuple(xrange(64))
        waveobj_list = self.waveobj_list[selection[0]:selection[-1] + 1]
        self.editAction.emit(INTERPOLATE_VALUES, True, waveobj_list)
        for wave_obj in waveobj_list:
            wave_obj.interpolate(stat_range)
        self.editAction.emit(INTERPOLATE_VALUES, False, waveobj_list)

    def setWaveTable(self, waveobj_list):
        self.waveobj_list = waveobj_list
        self.wavegroup = QtGui.QGraphicsItemGroup()
        for i, wave_obj in enumerate(waveobj_list):
#            wave_obj.selected.connect(self.select)
            wave_obj.preview_path_item.setX(i*128)
            wave_obj.selected.connect(lambda o, index=i: setattr(self, 'currentWave', index))
            self.wavegroup.addToGroup(wave_obj.preview_path_item)
            rect = wave_obj.preview_rect
            self.scene().addItem(rect)
            rect.setX(i*128)
            rect.setZValue(-10)
        bounding = self.wavegroup.boundingRect()
        bounding.setTop(-5)
        bounding.setBottom(bounding.bottom()+15)
        bounding_item = QtGui.QGraphicsRectItem(bounding)
        bounding_item.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        self.wavegroup.addToGroup(bounding_item)
        self.scene().addItem(self.wavegroup)
        self.setSceneRect(self.wavegroup.boundingRect())

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat('audio/wavesamples') or event.mimeData().hasFormat('audio/waves'):
            event.accept()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        for r in self.waveobj_list:
            r.preview_rect.setHighlight(False)

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat('audio/wavesamples'):
            data = event.mimeData().data('audio/wavesamples')
            wave_len = int(len(data) * 0.00390625)
        elif event.mimeData().hasFormat('audio/waves'):
            data = event.mimeData().data('audio/waves')
            start, end = map(int, str(data).split(':'))
            wave_len = end - start + 1
        else:
            event.ignore()
            return
        items = [i for i in self.items(event.pos()) if isinstance(i, WavePlaceHolderItem)]
        if not items: return
        index = items[0].index
        for r in self.waveobj_list[:index]:
            r.preview_rect.setHighlight(False)
        if index + wave_len > 64:
            event.ignore()
            for r in self.waveobj_list[index:-1]:
                r.preview_rect.setHighlight(True)
        else:
            event.accept()
            for r in self.waveobj_list[index:index + wave_len + 1]:
                r.preview_rect.setHighlight(True)
            for r in self.waveobj_list[index + wave_len:]:
                r.preview_rect.setHighlight(False)

    def dropEvent(self, event):
        items = [i for i in self.items(event.pos()) if isinstance(i, WavePlaceHolderItem)]
        if not items: return
        index = items[0].index
        mimedata = event.mimeData()
        if mimedata.hasFormat('audio/wavesamples'):
            data = mimedata.data('audio/wavesamples')
            slice_range = len(data) / 256
            self.dropAction.emit(DROP_WAVE, True, self.waveobj_list[index:index + slice_range], '"{}"'.format(mimedata.text()))
            for w in xrange(slice_range):
                values = []
                for s in xrange(128):
                    values.append(audioop.getsample(data, 2, w * 128 + s) * 31)
                self.waveobj_list[index + w].setValues(values)
            for r in self.waveobj_list:
                r.preview_rect.setHighlight(False)
            self.dropAction.emit(DROP_WAVE, False, self.waveobj_list[index:index + slice_range], '')
            event.accept()
        elif mimedata.hasFormat('audio/waves'):
            start, end = map(int, str(mimedata.data('audio/waves')).split(':'))
            if start == index:
                event.ignore()
                return
            wave_len = end - start + 1
            if start == end:
                drop_text = 'wave {}'.format(start + 1)
            else:
                drop_text = 'wave {} to {}'.format(start + 1, end + 1)

            if mimedata.hasFormat('data/reference'):
                ref = mimedata.referenceData()
                if ref == self.main:
                    source = self.waveobj_list
                else:
                    source = ref.waveobj_list
                    drop_text = 'from "{}" {}'.format(ref.wavetable_name, drop_text)
            else:
                source = self.waveobj_list
            data_list = []
            self.dropAction.emit(DROP_WAVE, True, self.waveobj_list[index:index + wave_len], drop_text)
            for wave_obj in source[start:end + 1]:
                data_list.append(wave_obj.values)
            for i, wave_obj in enumerate(self.waveobj_list[index:index + wave_len]):
                wave_obj.setValues(data_list[i])
            for r in self.waveobj_list:
                r.preview_rect.setHighlight(False)
            selection = tuple(xrange(index, index + wave_len))
            for i, r in enumerate(self.waveobj_list):
                r.preview_rect.setSelected(True if i in selection else False)
            self.selection = selection
            self.dropAction.emit(DROP_WAVE, False, self.waveobj_list[index:index + wave_len], '')
            event.accept()
        else:
            event.ignore()

    def resizeEvent(self, event):
        self.fitInView(self.wavegroup)


class SpacerWidget(QtGui.QWidget):
    def __init__(self):
        QtGui.QWidget.__init__(self)
        self.setSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Minimum)


class ControlPoint(QtGui.QGraphicsWidget):
    pen = QtGui.QPen(QtCore.Qt.blue)
    brush = QtGui.QBrush(QtGui.QColor(255, 88, 88, 150))
    moved = QtCore.pyqtSignal(float, float)

    def __init__(self, wave_path):
        QtGui.QGraphicsWidget.__init__(self, parent=None)
        self.setFlags(self.ItemIsMovable|self.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        self.shape_path = QtGui.QPainterPath()
        self.shape_path.addRect(-15000, -15000, 30000, 30000)
        self.wave_path = wave_path

    def setMoveFunction(self, fn):
        self.move = fn

    def itemChange(self, change, value):
        if change == self.ItemPositionChange:
            pos = value.toPyObject()
            if self.isVisible():
                if QtGui.QApplication.keyboardModifiers() == QtCore.Qt.ShiftModifier:
                    colliding = [i for i in self.collidingItems() if isinstance(i, ControlPoint)]
                    if colliding:
                        if colliding[0].contains(self.mapFromScene(pos)):
                            pos = colliding[0].pos()
                            self.moved.emit(pos.x(), pos.y())
                            return pos
                elif QtGui.QApplication.keyboardModifiers() == QtCore.Qt.ControlModifier:
                    if self.wave_path in self.collidingItems():
                        sample = int(pos.x() / 16384)
                        pos = self.wave_path.path().elementAt(sample)
                        self.moved.emit(pos.x, pos.y)
                        return QtCore.QPointF(pos.x, pos.y)
#            if not self.move(self, pos.x(), pos.y()):
#                return self.pos()
            self.moved.emit(pos.x(), pos.y())
        return QtGui.QGraphicsWidget.itemChange(self, change, value)

    def hoverEnterEvent(self, event):
        self.pen = QtGui.QPen(QtCore.Qt.red)
        self.brush = QtGui.QBrush(QtGui.QColor(255, 88, 88))
        self.update()

    def hoverLeaveEvent(self, event):
        self.pen = QtGui.QPen(QtCore.Qt.blue)
        self.brush = QtGui.QBrush(QtGui.QColor(255, 88, 88, 150))
        self.update()

    def shape(self):
        return self.shape_path

    def boundingRect(self):
        return QtCore.QRectF(-15000, -15000, 30000, 30000)

    def paint(self, painter, *args, **kwargs):
        painter.setPen(self.pen)
        painter.setBrush(self.brush)
        painter.drawEllipse(-10000, -10000, 20000, 20000)


class WavePath(QtGui.QGraphicsPathItem):
    def __init__(self, *args, **kwargs):
        QtGui.QGraphicsPathItem.__init__(self, *args, **kwargs)
        self.stroker = QtGui.QPainterPathStroker()
        self.shape_path = self.stroker.createStroke(self.path())

    def setPath(self, path):
        self.shape_path = self.stroker.createStroke(path)
        QtGui.QGraphicsPathItem.setPath(self, path)

    def shape(self):
        return self.shape_path

class WaveScene(QtGui.QGraphicsScene):
    curve_valid_pen = QtGui.QPen(QtCore.Qt.darkGreen)
    curve_invalid_pen = QtGui.QPen(QtCore.Qt.red)
    curve_pens = curve_invalid_pen, curve_valid_pen

    def __init__(self, main, *args, **kwargs):
        QtGui.QGraphicsScene.__init__(self, *args, **kwargs)
        self.main = main

        pen = QtGui.QPen(QtGui.QColor(200, 0, 200), 2048)
        smallpen = QtGui.QPen(QtCore.Qt.black, 1024)
        self.main_lines = []
        self.small_lines = []
        main_h_lines = []
        h_length = pow21 - 16384
        for group in xrange(0, pow21, 65536):
            hor = self.addLine(0, group, h_length, group)
            hor.setPen(pen)
            main_h_lines.append(hor)
            ver = self.addLine(group, 0, group, pow21)
            ver.setPen(pen)
            for line in xrange(1, 4):
                pos = group + line * 16384
                hor = self.addLine(0, pos, h_length, pos)
                hor.setPen(smallpen)
                ver = self.addLine(pos, 0, pos, pow21)
                ver.setPen(smallpen)
        hor = self.addLine(0, pow21, h_length, pow21)
        hor.setPen(pen)
        main_h_lines[16].setPen(QtGui.QPen(QtGui.QColor(200, 0, 100), 4096))

        self.wave_path = WavePath(QtGui.QPainterPath())
        self.addItem(self.wave_path)

        self.cursor = QtGui.QGraphicsItemGroup()
        rule_pen = QtGui.QPen(QtCore.Qt.blue, 2048)

        self.h_line = self.addLine(-pow21, 0, pow22, 0)
        self.h_line.setPen(rule_pen)
        self.cursor.addToGroup(self.h_line)

        self.v_line = self.addLine(0, -pow22, 0, pow21)
        self.v_line.setPen(rule_pen)
        self.cursor.addToGroup(self.v_line)

        self.cursor_text = self.addText('')
        self.cursor_text.setFlags(self.cursor_text.ItemIgnoresTransformations)
        self.cursor_text.setTextWidth(16384)
        self.cursor_text.setY(-98304)
        self.cursor.addToGroup(self.cursor_text)

        self.addItem(self.cursor)
        self.cursor.setVisible(False)
#        self.cursor.setPos(-16384, -16384)

        self.index_item = self.addText('1', QtGui.QFont('Helvetica'))
        index_transform = QtGui.QTransform().scale(16384, 16384)
        self.index_item.setTransform(index_transform)
        self.index_item.setDefaultTextColor(QtGui.QColor(96, 96, 96, 128))
        self.index_item.setPos(-32768, -65536)
        self.index_item.setZValue(-100)

        line_pen = QtGui.QPen(QtCore.Qt.red, 4096)
        self.linedraw = self.addLine(-16384, -16384, -16384, -16384)
        self.linedraw.setPen(line_pen)
        self.linedraw.setVisible(False)

        self.curvepath = QtGui.QGraphicsPathItem(QtGui.QPainterPath())
        self.curvepath.setPen(self.curve_valid_pen)
        self.curve_valid = True
        self.addItem(self.curvepath)

        self.curve_cp1 = ControlPoint(self.wave_path)
        self.curve_cp1.setVisible(False)
#        self.curve_cp1.setMoveFunction(self.curve_cp_move)
        self.curve_cp1.moved.connect(self.curve_cp_move)
        self.addItem(self.curve_cp1)

        self.curve_cp2 = ControlPoint(self.wave_path)
        self.curve_cp2.setVisible(False)
#        self.curve_cp2.setMoveFunction(self.curve_cp_move)
        self.curve_cp2.moved.connect(self.curve_cp_move)
        self.addItem(self.curve_cp2)

        self.curve_linecp1 = QtGui.QGraphicsLineItem()
        self.curve_linecp1.setPen(QtGui.QPen(QtCore.Qt.blue))
        self.curve_linecp1.setVisible(False)
        self.addItem(self.curve_linecp1)

        self.curve_linecp2 = QtGui.QGraphicsLineItem()
        self.curve_linecp2.setPen(QtGui.QPen(QtCore.Qt.blue))
        self.curve_linecp2.setVisible(False)
        self.addItem(self.curve_linecp2)

        self.curve_start = 0, 0
        self.curve_complete = False


        self.setSceneRect(0, 0, pow21, pow21)

    def setIndex(self, index):
        self.index_item.setPlainText(str(index + 1))

    def curve_cp_move(self, x, y):
        if not self.curve_complete: 
            return True
        if self.sender() == self.curve_cp1:
#            start_pos = self.curve_linecp1.line().p1()
            cp1_x = x
            cp1_y = y
            cp2_pos = self.curve_linecp2.line().p2()
            cp2_x = cp2_pos.x()
            cp2_y = cp2_pos.y()
        else:
#            start_pos = self.curve_linecp2.line().p1()
            cp2_x = x
            cp2_y = y
            cp1_pos = self.curve_linecp1.line().p2()
            cp1_x = cp1_pos.x()
            cp1_y = cp1_pos.y()
        path = self.curvepath.path()
        start = path.elementAt(0)
        end = path.currentPosition()
        new = QtGui.QPainterPath()
        new.moveTo(start.x, start.y)
        new.cubicTo(cp1_x, cp1_y, cp2_x, cp2_y, end.x(), end.y())
        br = new.boundingRect()
#        if (br.x() < start.x or br.x()+br.width() > end.x()) and self.curve_complete:
#            print 'Curve error! {}, {}'.format(br.x()-start.x, end.x()-br.x()+br.width())
#            return False
        end_limit = br.x() + br.width()
        start_limit = start.x
        for p in xrange(128):
            delta_x = new.pointAtPercent(p*.0078125).x()
            if not start_limit <= delta_x <= end_limit:
                valid = False
                break
            start_limit = delta_x
        else:
            valid = True
        self.curve_linecp1.setLine(start.x, start.y, cp1_x, cp1_y)
        self.curve_linecp2.setLine(end.x(), end.y(), cp2_x, cp2_y)
        self.curvepath.setPath(new)
        self.curvepath.setPen(self.curve_pens[valid])
        self.curve_valid = valid

    def setCurveStart(self, x, y, sample):
        self.curve_valid = True
        self.curvepath.setPen(self.curve_valid_pen)
        self.curve_sample_start = sample
        self.curve_complete = False
        self.curve_start = x, y

    def setCurveEnd(self, x2, y2, sample):
        self.curve_sample_end = sample
        self.curve_end = x2, y2
        path = QtGui.QPainterPath()
        x1, y1 = self.curve_start
        if x2 > x1:
            path.moveTo(x1, y1)
            path.cubicTo(x2, y1, x2, y1, x2, y2)
        else:
            path.moveTo(x2, y2)
            path.cubicTo(x2, y1, x2, y1, x1, y1)

        self.curvepath.setPath(path)

        self.curve_cp1.setPos(x2, y1)
        self.curve_cp2.setPos(x2, y1)

        self.curve_linecp1.setLine(x1, y1, x2, y1)
        self.curve_linecp2.setLine(x2, y2, x2, y1)

        self.curve_cp1.setVisible(True)
        self.curve_cp2.setVisible(True)
        self.curve_linecp1.setVisible(True)
        self.curve_linecp2.setVisible(True)

        self.curve_complete = True

    def clear_curve(self):
        self.curve_complete = False
        self.curvepath.setVisible(False)
        self.curve_cp1.setVisible(False)
        self.curve_cp2.setVisible(False)
        self.curve_linecp1.setVisible(False)
        self.curve_linecp2.setVisible(False)


class WaveView(QtGui.QWidget):
    valueChanged = QtCore.pyqtSignal(int, int)
    statusTip = QtCore.pyqtSignal(str)

    drawAction = QtCore.pyqtSignal(int, bool)

    def __init__(self, *args, **kwargs):
        QtGui.QWidget.__init__(self, *args, **kwargs)
        self.setContentsMargins(0, 0, 0, 0)
        self.setLayout(QtGui.QBoxLayout(QtGui.QBoxLayout.LeftToRight))
#        self.layout().addWidget(SpacerWidget())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.view = QtGui.QGraphicsView()
        self.view.setMouseTracking(True)
        self.view.setRenderHints(QtGui.QPainter.Antialiasing)
        self.layout().addWidget(self.view)
        self.layout().addWidget(SpacerWidget())
        self.scene = WaveScene(self)
        self.view.setScene(self.scene)
        self.view.keyPressEvent = self.viewKeyPressEvent
        self.view.enterEvent = self.viewEnterEvent
        self.view.leaveEvent = self.viewLeaveEvent
        self.view.mousePressEvent = self.viewMousePressEvent
        self.view.mouseMoveEvent = self.viewMouseMoveEvent
        self.view.mouseReleaseEvent = self.viewMouseReleaseEvent
        self.view.focusOutEvent = self.viewFocusOutEvent
        self.view.fitInView(0, 0, pow21, pow21)
        self.wave_path = self.scene.wave_path
        self.mouse_prev = None
        self.cursors = {
                        DRAW_FREE: self.cursor(), 
                        DRAW_LINE: LineCursor(), 
                        DRAW_CURVE: CurveCursor(), 
                        }
        self.draw_mode = DRAW_FREE

#    @property
#    def draw_mode(self):
#        return self._draw_mode
#
#    @draw_mode.setter
#    def draw_mode(self, mode):
#        self._draw_mode = mode
#        self.setCursor(self.cursors[mode])

    def setDrawMode(self, mode):
        self.draw_mode = mode
        self.view.setCursor(self.cursors[mode])

    def computePos(self, x):
        sample, rem = divmod(x, 16384)
        sample = int(sample)
        if sample < 0:
            sample = 0
        elif sample < 127:
            if rem > 12288:
                sample += 1
        else:
            sample = 127
        return sample

    def computeValue(self, y):
        value = int(pow20 - y)
        if QtGui.QApplication.keyboardModifiers() == QtCore.Qt.ControlModifier|QtCore.Qt.ShiftModifier:
            d, r = divmod(value, 16384)
            if r < 8192:
                value = d * 16384
            else:
                value = d * 16384 + 16384
        if value < -1048576:
            value = -1048576
        elif value > 1048575:
            value = 1048575
        return value

    def computePosValue(self, pos):
        return self.computePos(pos.x()), self.computeValue(pos.y())

    def viewFocusOutEvent(self, event):
        if self.draw_mode == DRAW_LINE:
            self.scene.linedraw.setVisible(False)
        elif self.draw_mode == DRAW_CURVE:
            self.scene.clear_curve()

    def viewKeyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            if self.draw_mode == DRAW_LINE:
                self.scene.linedraw.setVisible(False)
            elif self.draw_mode == DRAW_CURVE:
                self.scene.clear_curve()
        elif event.key() == QtCore.Qt.Key_Return:
            if self.draw_mode == DRAW_CURVE:
                if self.scene.curve_valid:
                    self.drawAction.emit(DRAW_CURVE, True)
                    #create a fake fill area by duplicating the curve
                    orig = self.scene.curvepath.path()
                    start_pos = orig.elementAt(0)
                    orig.lineTo(self.scene.curve_end[0], self.scene.curve_end[1])
                    cp1 = self.scene.curve_cp1.pos()
                    cp2 = self.scene.curve_cp2.pos()
                    orig.cubicTo(cp2.x(), cp2.y(), cp1.x(), cp1.y(), start_pos.x, start_pos.y)
                    orig.closeSubpath()
    #                test = QtGui.QPainterPath()
    #                test.addRect(1048576, 0, 1, 2097152)
    #                inters = test.intersected(orig)
    #                print inters.boundingRect()#, inters.elementAt(0).pos()
                    start = self.scene.curve_sample_start
                    end = self.scene.curve_sample_end
                    if start > end:
                        range_t = start - 1, end, -1
                    else:
                        range_t = start + 1, end
                    for sample in xrange(*range_t):
                        base = QtGui.QPainterPath()
                        base.addRect(sample * 16384, 0, 1, 2097152)
                        inters = base.intersected(orig)
                        self.valueChanged.emit(sample, pow20 - inters.boundingRect().y())
                    self.drawAction.emit(DRAW_CURVE, False)
                self.scene.clear_curve()

    def viewEnterEvent(self, event):
        self.scene.cursor.setVisible(True)
        text = 'Ctrl+Shift to snap to horizontal grid.'
        if self.draw_mode == DRAW_FREE:
            text += ' Ctrl to draw horizontal lines.'
        elif self.draw_mode == DRAW_CURVE:
            text += ' Ctrl to snap to existing wave. Press Enter to finalize the curve, Esc to ignore it.'
        self.statusTip.emit(text)

    def viewLeaveEvent(self, event):
        self.scene.cursor.setVisible(False)
        self.statusTip.emit('')

    def viewMousePressEvent(self, event):
#        QtGui.QGraphicsView.mousePressEvent(self.view, event)
        pos = self.view.mapToScene(event.pos())
        sample, value = self.computePosValue(pos)
        if self.draw_mode == DRAW_LINE:
            source = self.wave_path.path().elementAt(sample)
            x2 = sample * 16384
            y2 = pow20 - value
            self.scene.linedraw.setLine(source.x, source.y, x2, y2)
            self.scene.linedraw.setVisible(True)
            self.mouse_prev = sample, pow20 - source.y
        elif self.draw_mode == DRAW_CURVE:
            if self.scene.curvepath.isVisible() and self.scene.curve_complete:
                return QtGui.QGraphicsView.mousePressEvent(self.view, event)
            source = self.wave_path.path().elementAt(sample)
            self.scene.setCurveStart(source.x, source.y, sample)
            self.scene.curvepath.setVisible(True)
#            self.mouse_prev = sample, value
        else:
            self.drawAction.emit(DRAW_FREE, True)
            self.valueChanged.emit(sample, value)
            self.mouse_prev = sample, value

    def viewMouseMoveEvent(self, event):
        if self.draw_mode == DRAW_CURVE and self.scene.curvepath.isVisible() and self.scene.curve_complete:
            QtGui.QGraphicsView.mouseMoveEvent(self.view, event)
            self.scene.update()

#        QtGui.QGraphicsView.mouseMoveEvent(self.view, event)
        pos = self.view.mapToScene(event.pos())
        sample, value = self.computePosValue(pos)
        self.scene.cursor.setPos(sample * 16384, pow20 - value)
        self.scene.cursor_text.setPlainText('Sample: {}\nValue: {}'.format(sample + 1, value))
        if event.buttons():
            if self.draw_mode == DRAW_LINE:
                if not self.scene.linedraw.isVisible(): return
                self.scene.linedraw.setLine(self.scene.linedraw.line().x1(), self.scene.linedraw.line().y1(), sample * 16384, pow20 - value)
                return
            elif self.draw_mode == DRAW_CURVE:
                if not self.scene.curvepath.isVisible(): return
                if self.scene.curve_complete:
#                    QtGui.QGraphicsView.mouseMoveEvent(self.view, event)
                    return
                path = QtGui.QPainterPath()
                x1, y1 = self.scene.curve_start
                x2 = sample * 16384
                if event.modifiers() & QtCore.Qt.ControlModifier:
                    y2 = self.wave_path.path().elementAt(sample).y
                else:
                    y2 = pow20 - value
#                print self.wave_path.path().elementAt(sample).y, y2
                path.moveTo(x1, y1)
                path.cubicTo(x2, y1, x2, y1, x2, y2)
                self.scene.curvepath.setPath(path)
                return
            prev_sample, prev_value = self.mouse_prev
            delta_sample = abs(sample - prev_sample)
            if event.modifiers() == QtCore.Qt.ControlModifier:
                value = prev_value
            if delta_sample <= 1:
                self.valueChanged.emit(sample, value)
                self.mouse_prev = sample, value
                return
            diff = value - prev_value
            ratio = float(diff)/delta_sample
            if sample > prev_sample:
                for i, s in enumerate(xrange(prev_sample + 1, sample)):
                    self.valueChanged.emit(s, int(prev_value + (i + 1) * ratio))
            else:
                for i, s in enumerate(xrange(prev_sample - 1, sample, -1)):
                    self.valueChanged.emit(s, int(prev_value + (i + 1) * ratio))
            self.valueChanged.emit(sample, value)
            self.mouse_prev = sample, value

    def viewMouseReleaseEvent(self, event):
#        QtGui.QGraphicsView.mouseReleaseEvent(self.view, event)
        if self.draw_mode == DRAW_LINE and self.scene.linedraw.isVisible():
            self.drawAction.emit(DRAW_LINE, True)
            self.scene.linedraw.setVisible(False)
            sample, value = self.computePosValue(self.view.mapToScene(event.pos()))
            prev_sample, prev_value = self.mouse_prev
            delta_sample = abs(sample - prev_sample)
            if delta_sample <= 1:
                self.valueChanged.emit(sample, value)
                self.mouse_prev = None
                self.drawAction.emit(DRAW_LINE, False)
                return
            diff = value - prev_value
            ratio = float(diff)/delta_sample
            if sample > prev_sample:
                for i, s in enumerate(xrange(prev_sample + 1, sample)):
                    self.valueChanged.emit(s, int(prev_value + (i + 1) * ratio))
            else:
                for i, s in enumerate(xrange(prev_sample - 1, sample, -1)):
                    self.valueChanged.emit(s, int(prev_value + (i + 1) * ratio))
            self.valueChanged.emit(sample, value)
            self.drawAction.emit(DRAW_LINE, False)
        elif self.draw_mode == DRAW_CURVE and self.scene.curvepath.isVisible():
            if self.scene.curve_complete:
                return QtGui.QGraphicsView.mouseReleaseEvent(self.view, event)
            sample, value = self.computePosValue(self.view.mapToScene(event.pos()))
            x2 = sample * 16384
            if event.modifiers() & QtCore.Qt.ControlModifier:
                y2 = self.wave_path.path().elementAt(sample).y
            else:
                y2 = pow20 - value
            self.scene.setCurveEnd(x2, y2, sample)
        else:
            self.drawAction.emit(DRAW_FREE, False)
        self.mouse_prev = None

    def setWavePath(self, wave_obj):
        self.wave_path.setPath(wave_obj.path)
        self.scene.setIndex(wave_obj.index)

    def resizeEvent(self, event):
        width = event.size().width()
        height = event.size().height()
        if width == height:
            return
        layout = self.layout()
        if width > height:
            layout.setDirection(QtGui.QBoxLayout.LeftToRight)
            w_stretch = height
            stretch = (width - height) + .5
        else:
            layout.setDirection(QtGui.QBoxLayout.TopToBottom)
            w_stretch = width
            stretch = (height - width) + .5
#        layout.setStretch(0, stretch)
        layout.setStretch(0, w_stretch)
        layout.setStretch(1, stretch)
        QtCore.QTimer.singleShot(0, lambda: self.view.fitInView(0, 0, pow21, pow21))


class AudioBuffer(QtCore.QBuffer):
    sweep = QtCore.pyqtSignal(int)

    def __init__(self, waveobj_list, *args, **kwargs):
        QtCore.QBuffer.__init__(self, *args, **kwargs)
        self.waveobj_list = waveobj_list

        self.single_data_list = [QtCore.QByteArray() for b in xrange(64)]
        self.multi_data = QtCore.QByteArray()
        self.multiplier = 6
        self.ratio = 1. / 44100 * 128 * self.multiplier * 1000000

        for wave_obj in waveobj_list:
            wave_obj.changed.connect(self.update)
            wave_obj.selected.connect(self.setCurrentWave)
            self.update(wave_obj)

        self.currentWave = 0
        self.current_data = self.single_data_list[0]
        self.start = 0
        self.delta = 256
        self.full_mode = False
        self.open(QtCore.QIODevice.ReadOnly)

    def set_full_mode(self, mode):
        self.full_mode = mode
        if mode:
            self.current_data = self.multi_data
#            self.delta = 256 * self.multiplier * (64 * self.multiplier - self.multiplier) / 2
            self.delta = len(self.current_data) / 2
            self.start = self.start + self.currentWave * 256 * self.multiplier
        else:
            self.current_data = self.single_data_list[self.currentWave]
            self.delta = 256
            self.start = self.start % 256

    def reset(self):
        self.start = 0

    def setCurrentWave(self, wave_obj):
        index = wave_obj.index
        self.currentWave = index
        if not self.full_mode:
            self.current_data = self.single_data_list[index]

    def update(self, wave_obj):
        data = QtCore.QByteArray()
        for s in range(128):
            data.append(struct.pack('<h', int(wave_obj.values[s] * .03125)))
        index = wave_obj.index
        self.single_data_list[index].replace(0, 65536, data * 256)
        self.multi_data.replace(index * 256 * self.multiplier, 256 * self.multiplier, str(data) * self.multiplier)
#        self.multi_data.replace((126 + index) * 256 * self.multiplier, 256 * self.multiplier, str(data) * self.multiplier)
#        if index not in (0, 63):
#            self.multi_data.replace((126 - index) * 256 * self.multiplier, 256 * self.multiplier, str(data) * self.multiplier)
#            self.multi_data.replace((252 - index) * 256 * self.multiplier, 256 * self.multiplier, str(data) * self.multiplier)
        self.multi_data.replace((127 - index) * 256 * self.multiplier, 256 * self.multiplier, str(data) * self.multiplier)
        self.multi_data.replace((128 + index) * 256 * self.multiplier, 256 * self.multiplier, str(data) * self.multiplier)
        self.multi_data.replace((255 - index) * 256 * self.multiplier, 256 * self.multiplier, str(data) * self.multiplier)

    def size(self):
        return len(self.current_data)

    def readData(self, size):
        slice = str(self.current_data.mid(self.start, size))
        self.start = (self.start + size) % self.delta
        return slice


class WaveTableEditor(QtGui.QMainWindow):
    wavetable_send = QtCore.pyqtSignal(object)
    closed = QtCore.pyqtSignal(object)

    def __init__(self, main, uid=None, wavetable_data=None):
        QtGui.QMainWindow.__init__(self)
        self.main = main
        self.wavetable_library = self.main.wavetable_library
        load_ui(self, 'wavetable.ui')
        self.currentStream = None
        self.undo = UndoStack(self)
        self.undo.canUndoChanged.connect(self.undo_btn.setEnabled)
        self.undo.canRedoChanged.connect(self.redo_btn.setEnabled)
        self.save_state = True
        self.undo.indexChanged.connect(self.undo_update)
        self.undo_dialog = UndoDialog(self)
        self.currentUndo = None

        self.saveAction.triggered.connect(self.wavetable_save)
        self.showLibraryAction.triggered.connect(lambda: [self.main.wavetable_list_window.show(), self.main.wavetable_list_window.activateWindow()])
        self.undoAction.triggered.connect(self.undo.undo)
        self.redoAction.triggered.connect(self.undo.redo)
        self.undoHistoryAction.triggered.connect(self.undo_dialog.show)
        self.undo_btn.setIcon(QtGui.QIcon.fromTheme('edit-undo'))
        self.redo_btn.setIcon(QtGui.QIcon.fromTheme('edit-redo'))
        self.undo_history_btn.setIcon(QtGui.QIcon.fromTheme('document-properties'))
        self.undo_history_btn.clicked.connect(self.undo_dialog.show)

        self.wavImportAction.triggered.connect(lambda: self.load_wave())
        self.wavetableImportAction.triggered.connect(self.load_wavetable)

        self.wave_source_view = WaveSourceView(self)
        self.wave_source_view.setMinimumHeight(100)
        self.wave_source_view.installEventFilter(self)
        self.wave_source_view.statusTip.connect(self.setStatusTip)
        self.wave_layout.insertWidget(0, self.wave_source_view)
        self.wavetable_view.setMain(self)
        self.wave_source_view.setMain(self)
        self.wave_source_view.sampleSelectionChanged.connect(self.setSampleSelection)
        self.sel_start = 0
        self.sel_end = 127
        self.splitter.splitterMoved.connect(self.splitterMoved)
        self.splitter_pos = 120
        self.wavesource_toggle.setVisible(False)
        self.wavesource_toggle.clicked.connect(lambda: (self.wavesource_toggle.setVisible(False), self.splitter.moveSplitter(20, 0)))

        self.wave_model = QtGui.QStandardItemModel()
        self.wave_list.setModel(self.wave_model)

        self.draw_timer = QtCore.QTimer()
        self.draw_timer.setSingleShot(True)
        self.draw_timer.setInterval(250)
        self.draw_timer.timeout.connect(self.resetWave)

        self.wave_list.currentChanged = self.setWaveSource
        self.wave_list.dragEnterEvent = self.wavelistDragEnterEvent
        self.wave_list.dragMoveEvent = self.wavelistDragMoveEvent
        self.wave_list.dragLeaveEvent = self.wavelistDragLeaveEvent
        self.wave_list.dropEvent = self.wavelistDropEvent
        self.add_wave_btn.clicked.connect(lambda: self.load_wave())
        self.del_wave_btn.clicked.connect(self.unload_wave)

        self.bal_toggle.clicked.connect(lambda: self.bal_panel.setVisible(True if not self.bal_panel.isVisible() else False))
        self.bal_toggle.clicked.connect(lambda: setattr(self, 'bal_panel_visible', not self.bal_panel_visible))
        self.left_slider.valueChanged.connect(lambda value: self.left_spin.setValue(float(value)/100.))
        self.left_slider.valueChanged.connect(lambda value: self.draw_timer.start())
        self.right_slider.valueChanged.connect(lambda value: self.right_spin.setValue(float(value)/100.))
        self.right_slider.valueChanged.connect(lambda value: self.draw_timer.start())
        self.left_spin.valueChanged.connect(lambda value: self.left_slider.setValue(int(value*100)))
        self.left_spin.valueChanged.connect(lambda value: self.currentStream.setData(value, balanceLeftRole))
        self.right_spin.valueChanged.connect(lambda value: self.right_slider.setValue(int(value*100)))
        self.right_spin.valueChanged.connect(lambda value: self.currentStream.setData(value, balanceRightRole))
        self.gain_dial.valueChanged.connect(lambda value, src=self.gain_dial: self.setGain(value, src))
        self.gain_spin.valueChanged.connect(lambda value, src=self.gain_spin: self.setGain(value, src))
        self.gain_spin.valueChanged.connect(lambda value: self.currentStream.setData(value, gainRole))
        self.bal_chk.toggled.connect(self.set_balance_active)
        self.bal_chk.toggled.connect(lambda state: self.currentStream.setData(state, balanceActiveRole))
        self.bal_slider.valueChanged.connect(self.set_balance)
        self.bal_slider.mouseDoubleClickEvent = lambda ev: self.bal_slider.setValue(50)
        self.bal_slider.mousePressEvent = lambda ev: self.bal_slider.setValue(50) if ev.buttons() == QtCore.Qt.MidButton else QtGui.QSlider.mousePressEvent(self.bal_slider, ev)
        self.bal_combo.currentIndexChanged.connect(self.set_balance_mode)
        self.balance_fn = compute_fn[0]
        self.gain_spin.installEventFilter(self)
        self.gain = 1.

        self.bal_panel.setVisible(False)
        self.bal_widget.setEnabled(False)
        self.bal_panel_visible = 0

        self.offset_spin.valueChanged.connect(self.wave_source_view.set_offset)
        self.sel_start_spin.valueChanged.connect(self.setSampleSelection)
        self.sel_end_spin.valueChanged.connect(self.setSampleSelection)

        self.currentWave = 0
        self.waveobj_list = []
        if uid is None:
            self.wavetable_uid = str(uuid4())
            if wavetable_data is None:
                values = [None for w in xrange(64)]
                self.wavetable_name = self.name_edit.text()
            else:
                values, slot, name = wavetable_data
            self.save_index = -1
        else:
            self.wavetable_uid = uid
            values, slot, name = self.wavetable_library[uid]
            self.wavetable_name = name
            self.name_edit.setText(name)
            self.slot_spin.setValue(slot)
            self.save_index = 0
        for w in xrange(64):
            wave_obj = WaveObject(w, values[w])
            wave_obj.selected.connect(self.setWave)
            wave_obj.changed.connect(lambda o: self.setWave(o) if o.index == self.currentWave else None)
            self.waveobj_list.append(wave_obj)
        self.wavetable_view.setWaveTable(self.waveobj_list)
        self.wavetable3d_view.setWaveTable(self.waveobj_list)
        self.setWave(self.waveobj_list[0])

        self.wave_view.valueChanged.connect(self.setWaveValue)
        self.wave_view.drawAction.connect(self.undo_push)
        self.wavetable_view.editAction.connect(self.undo_push)
        self.wavetable_view.dropAction.connect(self.undo_push)
        self.wave_view.statusTip.connect(self.setStatusTip)

        self.freedraw_btn.setIcon(FreeDrawIcon())
        self.drawmode_group.setId(self.freedraw_btn, 0)
        self.linedraw_btn.setIcon(LineDrawIcon())
        self.drawmode_group.setId(self.linedraw_btn, 1)
        self.curvedraw_btn.setIcon(CurveDrawIcon())
        self.drawmode_group.setId(self.curvedraw_btn, 2)
        self.drawmode_group.buttonClicked[int].connect(self.wave_view.setDrawMode)

        self.play_btn.setIcon(self.style().standardIcon(QtGui.QStyle.SP_FileDialogStart))
        p_fm = self.play_btn.fontMetrics()
        p_width = p_fm.width(self.play_btn.text())
        self.play_btn.setMinimumWidth(self.play_btn.width() - p_width + max(p_fm.width('Stop'), p_width))
        self.play_btn.toggled.connect(self.play)
        self.full_sweep_chk.toggled.connect(self.full_mode)

        self.dump_btn.setIcon(self.style().standardIcon(QtGui.QStyle.SP_ArrowRight))
        self.dump_btn.clicked.connect(self.dump)
        self.export_btn.setIcon(self.style().standardIcon(QtGui.QStyle.SP_DialogSaveButton))
        self.export_btn.clicked.connect(self.export)

        self.audio_buffer = AudioBuffer(self.waveobj_list)

        self.qtmultimedia = QTMULTIMEDIA
        if QTMULTIMEDIA:
            format = QtMultimedia.QAudioFormat()
            format.setChannels(1)
            format.setFrequency(44100)
            format.setSampleSize(16)
            format.setCodec("audio/pcm")
            format.setByteOrder(QtMultimedia.QAudioFormat.LittleEndian)
            format.setSampleType(QtMultimedia.QAudioFormat.SignedInt)
            self.output = QtMultimedia.QAudioOutput(format, self)
            self.audio_timer = QtCore.QTimer()
            self.audio_timer.setInterval(8)
            self.audio_timer.timeout.connect(self.play_pos)
        else:
            self.play_btn.setEnabled(False)
            self.full_sweep_chk.setEnabled(False)

        self.dump_dialog = DumpDialog(self)

        self.name_edit.setValidator(QtGui.QRegExpValidator(QtCore.QRegExp('[\x20-\x7f°]*')))
#        self.name_edit.editingFinished.connect(lambda: (self.name_edit.setText(self.name_edit.text().leftJustified(14)), self.setFocus(QtCore.Qt.OtherFocusReason)))
        self.name_edit.editingFinished.connect(self.wavetable_name_set)
        self.name_edit.textEdited.connect(self.wavetable_name_change)
        self.setWindowTitle()
        self.slot_spin.valueChanged.connect(self.wavetable_slot_set)
        self.slot_spin.editingFinished.connect(self.wavetable_slot_set_finish)

        if QTMULTIMEDIA:
            self.addAction(self.wavetablePlayAction)
            self.wavetablePlayAction.triggered.connect(lambda: self.play_btn.setChecked(not self.play_btn.isChecked()))

        #wave editing
        self.reverse_btn.clicked.connect(lambda: self.wavetable_view.reverse_wave_values([self.currentWave]))
        self.invert_btn.clicked.connect(lambda: self.wavetable_view.invert_waves([self.currentWave]))
        self.smooth_btn.clicked.connect(lambda: self.wavetable_view.interpolate_values([self.currentWave]))

        self.menuWindows.aboutToShow.connect(self.populate_wavetable_window_menu)
        win_sep = QtGui.QAction('Open wavetables:', self.menuWindows)
        win_sep.setSeparator(True)
        self.menuWindows.addAction(win_sep)
        self.wavetable_windows_list = self.main.wavetable_windows_list
        self.wavetable_window_actions = []

        self.installEventFilter(self)

    def undo_update(self, index):
        self.save_state = True if index == self.save_index else False
        self.setWindowTitle()

    def wavetable_name_change(self, text):
        self.undo_push(NAME_CHANGE, True, self.wavetable_name, text)

    def setWindowTitle(self, name=None):
        if name is None:
            name = self.name_edit.text()
        saved = '' if self.save_state else ' (edited)'
        QtGui.QMainWindow.setWindowTitle(self, 'Wavetable editor - {}{}'.format(name, saved))

    def wavetable_name_set(self):
        self.name_edit.setText(self.name_edit.text().leftJustified(14))
        name = str(self.name_edit.text()).rstrip()
        self.undo_push(NAME_CHANGE, False, name)
        self.wavetable_name = name
        self.setWindowTitle(name)
        self.setFocus(QtCore.Qt.OtherFocusReason)

    def wavetable_slot_set(self, slot):
        self.undo_push(SLOT_CHANGE, True, self.slot, slot)
#        self.slot = slot

    @property
    def slot(self):
        return self.slot_spin.value()

    def wavetable_slot_set_finish(self):
        self.undo_push(SLOT_CHANGE, False, self.slot_spin.value())

    def wavetable_save(self):
        for item in self.wavetable_library.model.findItems(self.name_edit.text().leftJustified(14)):
            if self.wavetable_uid == self.wavetable_library.model.item(item.row(), 4).text():
                continue
            else:
                QtGui.QMessageBox.warning(self, 'Wavetable name conflict', 'The Library already contains a Wavetable named "{}"'.format(self.name_edit.text()))
                return
        wavetable_values = []
        for wave_obj in self.waveobj_list:
            wavetable_values.extend(wave_obj.values)
        self.wavetable_library[self.wavetable_uid] = wavetable_values, self.slot, self.name_edit.text()
        self.save_index = self.undo.index()
        self.save_state = True
        self.setWindowTitle()

    def populate_wavetable_window_menu(self):
        window_list = set([w for w in self.wavetable_windows_list if w is not self])
        window_actions = {action.data().toPyObject():action for action in self.wavetable_window_actions}
        for window in window_list:
            if window not in window_actions:
                action = QtGui.QAction(window.name_edit.text(), self)
                self.menuWindows.addAction(action)
                self.wavetable_window_actions.append(action)
        for window, action in window_actions.items():
            if window not in window_list:
                self.menuWindows.removeAction(action)

    def midi_output_state(self, conn):
        state = True if conn else False
        self.dump_btn.setEnabled(state)

    def closeEvent(self, event):
        if not self.save_state:
            res = QtGui.QMessageBox.question(self, 'Wavetable not saved',
                                       'The wavetable has been modified, how do you want to proceed?', 
                                       QtGui.QMessageBox.Save|QtGui.QMessageBox.Discard|QtGui.QMessageBox.Cancel
                                       )
            if res == QtGui.QMessageBox.Save:
                self.wavetable_save()
            elif res == QtGui.QMessageBox.Cancel:
                event.ignore()
                return
        self.closed.emit(self)
        self.wavetable_windows_list.pop(self.wavetable_windows_list.index(self))
        if not any([self.main.librarian.isVisible(), self.main.editor.isVisible(), len(self.wavetable_windows_list)]):
            self.main.librarian.show()
        

    def undo_push(self, action, state, *data):
        if isinstance(self.currentUndo, SlotChangeUndo) and action != SLOT_CHANGE:
            self.currentUndo.finalize(self.slot_spin.value())
            if self.currentUndo.isChanged():
                self.undo.push(self.currentUndo)
            self.currentUndo = None
        if action in (DRAW_FREE, DRAW_CURVE, DRAW_LINE):
            if state:
                self.currentUndo = SingleWaveUndo(action, self.waveobj_list[self.currentWave])
            else:
                self.currentUndo.finalize(self.waveobj_list[self.currentWave].values)
                self.undo.push(self.currentUndo)
                self.currentUndo = None
        elif action == NAME_CHANGE:
            if state:
                self.currentUndo = NameChangeUndo(self.name_edit, *data)
            elif self.currentUndo is not None:
                self.currentUndo.finalize(data[0])
                self.undo.push(self.currentUndo)
                self.currentUndo = None
        elif action == SLOT_CHANGE:
            if self.currentUndo is None:
                self.currentUndo = SlotChangeUndo(self.slot_spin, *data)
            elif state:
                self.currentUndo.finalize(data[1])
            else:
                self.currentUndo.finalize(data[0])
                if self.currentUndo.isChanged():
                    self.undo.push(self.currentUndo)
                self.currentUndo = None
        else:
            if state:
                self.currentUndo = MultiWaveUndo(action, *data)
            else:
                self.currentUndo.finalize(data[0])
                self.undo.push(self.currentUndo)
                self.currentUndo = None

    def setStatusTip(self, text):
        if not text:
            self.statusbar.clearMessage()
        else:
            self.statusbar.showMessage(text)

    def wavelistDragEnterEvent(self, event):
        for fmt in event.mimeData().formats():
            if fmt.toLower().contains('text') or fmt.toLower().contains('string'):
                s = QtCore.QString(event.mimeData().data(fmt))
                if s.startsWith('file://'):
                    try:
                        path = str(QtCore.QUrl(s).toLocalFile())
                        source = wave.open(path)
                        if source.getnchannels() > 2 or source.getsampwidth() > 2:
                            raise
                        framerate = source.getframerate()
                        frames = source.getnframes()
                        if frames/float(framerate) > 60:
                            raise
                        break
                    except:
                        continue
        else:
            event.ignore()
            return
        event.accept()
        self.wave_accepted_fmt = fmt

    def wavelistDragMoveEvent(self, event):
        event.accept()

    def wavelistDragLeaveEvent(self, event):
        self.wave_accepted_fmt = None

    def wavelistDropEvent(self, event):
        self.load_wave(QtCore.QUrl(QtCore.QString(event.mimeData().data(self.wave_accepted_fmt))).toLocalFile())

    def setSampleSelection(self, *args):
        sender = self.sender()
        if sender == self.wave_source_view:
            start, end = args
            self.sel_start_spin.blockSignals(True)
            self.sel_end_spin.blockSignals(True)
            self.sel_start_spin.setValue(start)
            self.sel_end_spin.setValue(end)
            self.sel_start_spin.blockSignals(False)
            self.sel_end_spin.blockSignals(False)
            return
        value = args[0]
        if sender == self.sel_start_spin:
            self.sel_end_spin.setMinimum(value + 1)
            if self.sel_link_chk.isChecked():
                self.sel_end_spin.setValue(self.sel_end + value - self.sel_start)
                self.sel_end_spin.setMaximum(4096)
            else:
                self.sel_end_spin.setMaximum(value + 127)
            self.sel_start = value
            self.sel_end = self.sel_end_spin.value()
        else:
            if self.sel_link_chk.isChecked() and value > 128:
                self.sel_start_spin.blockSignals(True)
                self.sel_start_spin.setValue(self.sel_start + value - self.sel_end)
                self.sel_start_spin.blockSignals(False)
                #current wave maximum
                self.sel_end_spin.setMaximum(4096)
            self.sel_start = self.sel_start_spin.value()
            self.sel_end = value

    def play_pos(self):
        buff = (self.output.bufferSize() - self.output.bytesFree()) * 11.337868480725623
        diff = self.output.processedUSecs() - self.sweep_pos - buff
        index = int(round(diff / self.audio_buffer.ratio, 0) % 128)
        if index > 63:
            index = 127 - index
        if index != self.sweep_index:
            self.waveobj_list[self.sweep_index].preview_rect.setHighlight(False)
            self.waveobj_list[index].preview_rect.setHighlight(True)
            self.wavetable3d_view.wave_list[self.sweep_index].highlight(False)
            self.wavetable3d_view.wave_list[index].highlight(True)
            self.sweep_index = index

    def play(self, state):
        if state:
            self.play_btn.setIcon(self.style().standardIcon(QtGui.QStyle.SP_MediaStop))
            self.play_btn.setText('Stop')
            self.output.start(self.audio_buffer)
            if self.audio_buffer.full_mode:
                self.audio_timer.start()
        else:
            self.play_btn.setIcon(self.style().standardIcon(QtGui.QStyle.SP_FileDialogStart))
            self.play_btn.setText('Play')
            self.audio_timer.stop()
            self.output.stop()
            self.output.reset()
            self.audio_buffer.reset()
            if self.audio_buffer.full_mode:
                self.waveobj_list[self.sweep_index].preview_rect.setHighlight(False)
                self.wavetable3d_view.wave_list[self.sweep_index].highlight(False)

    def full_mode(self, state):
        self.audio_buffer.set_full_mode(state)
        if state:
            self.sweep_index = 0
            self.sweep_pos = self.output.processedUSecs()
        if self.output.state() == QtMultimedia.QAudio.ActiveState:
            if state:
                QtCore.QTimer.singleShot(0, lambda: self.audio_timer.start())
            else:
                self.audio_timer.stop()
                self.waveobj_list[self.sweep_index].preview_rect.setHighlight(False)
                self.wavetable3d_view.wave_list[self.sweep_index].highlight(False)

    def showEvent(self, event):
        sizes = self.splitter.sizes()
        sizes[0] = 0
        self.splitter.setSizes(sizes)
        self.wavesource_toggle.setVisible(True)

    def splitterMoved(self, pos, index):
        self.wavesource_toggle.setVisible(not pos)
        if pos and pos != self.splitter_pos:
            self.splitter_pos = pos

    def dump(self):
        def send(index):
            self.dump_dialog.setIndex(index)
            sysex_data = sysex_list.next()
            self.wavetable_send.emit(sysex_data)
            if index == 63:
                self.dump_dialog.hide()
                return
            QtCore.QTimer.singleShot(200, lambda i=index: send(i + 1))
        sysex_list = iter(self.createSysExData())
        self.dump_dialog.setData(self.slot_spin.value(), self.name_edit.text())
        self.dump_dialog.show()
        send(0)

    def export(self):
        name = QtCore.QDir.homePath() + '/' + self.name_edit.text() + '.syx'
        path = QtGui.QFileDialog.getSaveFileName(self, 'Export wavetable', name, 'SysEx files (*.syx)')
        if not path: return
        data_list = self.createSysExData()
        data = []
        for w_data in data_list:
            data.extend(w_data)
        with open(str(path.toUtf8()), 'wb') as sf:
            sf.write(bytearray(data))

    def createSysExData(self):
        sysex_list = []
        slot = self.slot_spin.value()
        name = tuple(ord(l) if l != '°' else 127 for l in str(self.name_edit.text().toUtf8()).replace('\xc2\xb0', '\x7f').ljust(14, ' '))
        for n, wave_obj in enumerate(self.waveobj_list):
            sysex_data = [INIT, IDW, IDE, self.main.blofeld_id, WTBD, slot, n, 0]
            for value in wave_obj.values:
                if value < 0:
                    value = pow21 + value
                sysex_data.extend((value >> 14, (value >> 7) & 127,  value & 127))
            sysex_data.extend(name)
            sysex_data.extend((0, 0, CHK))
            sysex_data.append(END)

            sysex_list.append(sysex_data)
        return sysex_list

    def setWave(self, wave_obj=None):
        self.waveobj_list[self.currentWave].selected_state = False
        if wave_obj is None:
            wave_obj = self.sender()
        index = wave_obj.index
        self.currentWave = wave_obj.index
        wave_obj.selected_state = True
        self.wave_view.setWavePath(wave_obj)
        self.wavetable3d_view.selectWave(index)

    def setWaveValue(self, sample_id, value):
        wave_obj = self.waveobj_list[self.currentWave]
        wave_obj.setValue(sample_id, value)
        self.wave_view.setWavePath(wave_obj)
        self.wavetable3d_view.updateWaveValue(self.currentWave, sample_id, value)

    def eventFilter(self, source, event):
        if source == self.gain_spin and event.type() == QtCore.QEvent.Wheel:
            if QtGui.QApplication.keyboardModifiers() == QtCore.Qt.ShiftModifier:
                self.gain_spin.setSingleStep(.01)
            else:
                self.gain_spin.setSingleStep(.1)
        elif ((event.type() == QtCore.QEvent.KeyPress and event.modifiers() & (QtCore.Qt.ShiftModifier|QtCore.Qt.ControlModifier)) or event.type() == QtCore.QEvent.KeyRelease) and self.wave_source_view.rect().contains(self.wave_source_view.mapFromGlobal(QtGui.QCursor().pos())):
            self.wave_source_view.event(event)
            return True
        return QtGui.QMainWindow.eventFilter(self, source, event)

    def set_balance_active(self, state):
        self.left_slider.setDisabled(state)
        self.left_spin.setDisabled(state)
        self.right_slider.setDisabled(state)
        self.right_spin.setDisabled(state)
        self.bal_slider.setEnabled(state)
        self.bal_combo.setEnabled(state)

        self.left_slider.blockSignals(state)
        self.right_slider.blockSignals(state)

        if state:
            self.set_balance(self.bal_slider.value())

    def set_balance_mode(self, mode):
        self.balance_fn = compute_fn[mode]
        self.set_balance(self.bal_slider.value())

    def set_balance(self, value):
        right, left = self.balance_fn(value*.01)
        self.left_spin.setValue(left)
        self.right_spin.setValue(right)
        self.draw_timer.start()
        self.currentStream.setData(value, balanceValueRole)

    def setGain(self, value, source):
        if source == self.gain_dial:
            self.gain_spin.blockSignals(True)
            self.gain = float(value)/100
            self.gain_spin.setValue(self.gain)
            self.gain_spin.blockSignals(False)
        else:
            self.gain_dial.blockSignals(True)
            self.gain_dial.setValue(int(value*100))
            self.gain = value
            self.gain_dial.blockSignals(False)
        self.draw_timer.start()

    def load_wave(self, path=None):
        if path is None:
            path = WaveLoad(self.main).exec_()
            if not path: return
        if self.wave_model.findItems(path, column=1):
            QtGui.QMessageBox.information(self, 'File already imported', 'The selected file is already in the wave list.')
            return
        stream = wave.open(str(path.toUtf8()))
        info = QtCore.QFileInfo(path)
        item = QtGui.QStandardItem(info.fileName())
        item.setData(path, pathRole)
        item.setData(stream, streamRole)
        item.setData(1., gainRole)
        if stream.getnchannels() > 1:
            item.setData(True, balanceActiveRole)
            item.setData(0, balanceModeRole)
            item.setData(50, balanceValueRole)
            item.setData(.5, balanceLeftRole)
            item.setData(.5, balanceRightRole)
        path_item = QtGui.QStandardItem(path)
        self.wave_model.appendRow([item, path_item])
        self.setWaveSource(item, force=True)
        self.wave_list.selectionModel().select(self.wave_model.index(self.wave_model.rowCount()-1, 0), QtGui.QItemSelectionModel.ClearAndSelect)
        self.wave_panel.setEnabled(True)
        self.del_wave_btn.setEnabled(True)
        if self.wavesource_toggle.isVisible():
            self.splitter.moveSplitter(60, 0)

    def load_wavetable(self, as_new=False):
        path = QtGui.QFileDialog.getOpenFileName(self, 'Import Wavetable', filter = 'Wavetable files (*.mid, *.syx)(*.mid *.syx);;SysEx files (*.syx);;MIDI files (*.mid);;All files (*)')
        if not path: return
        try:
            pattern = midifile.read_midifile(str(path.toUtf8()))
            if len(pattern) < 1:
                raise InvalidException('Empty MIDI file')
            track = pattern[0]
            if len(track) < 64:
                raise InvalidException('MIDI file too small')
            wt_list = []
            #todo: check for actual wave number order?
            for event in track:
                if isinstance(event, midifile.SysexEvent) and len(event.data) == 410:
                    data = event.data[2:-1]
                    if data[:2] != [IDW, IDE] and data[3] != WTBD and data[6] != 0:
                        raise InvalidException
                    wt_list.append(data[7:391])
            if len(wt_list) != 64:
                raise InvalidException('Wrong number of SysEx events')
        except InvalidException as error:
            invalid_msgbox(self, error)
            return
        except Exception:
            try:
                with open(str(path.toUtf8()), 'rb') as sf:
                    sysex_list = list(ord(i) for i in sf.read())
                if len(sysex_list) != 26240:
                    raise
                wt_list = []
                for w in xrange(64):
                    data = sysex_list[w * 410 + 1:w * 410 + 408]
                    if data[:3] != [IDW, IDE] and data[3] != WTBD and data[6] != 0:
                        raise
                    wt_list.append(data[7:391])
            except:
                invalid_msgbox(self)
                return
        wt_slot = data[4]
        wt_name = ''.join([str(unichr(l)) for l in data[391:405]])
        self.slot_spin.setValue(wt_slot)
        self.name_edit.setText(wt_name)

        if not as_new:
            self.undo_push(WAVETABLE_IMPORT, True, self.waveobj_list, QtCore.QFileInfo(path).fileName())
        for w, wave_obj in enumerate(self.waveobj_list):
            values_iter = iter(wt_list[w])
            values = []
            for s in xrange(128):
                value = (values_iter.next() << 14) + (values_iter.next() << 7) + values_iter.next()
                if value >= 1048576:
                    value -= 2097152
                values.append(value)
            wave_obj.setValues(values)
        if not as_new:
            self.undo_push(WAVETABLE_IMPORT, False, self.waveobj_list, '')
        self.setWave(self.waveobj_list[self.currentWave])

    def unload_wave(self):
        row = self.currentStream.row()
        if row < 0: return
        res = QtGui.QMessageBox.question(
                                         self, 'Remove wave file', 
                                         'Do you want to remove this file?\n{}'.format(self.currentStream.data(0).toPyObject()), 
                                         QtGui.QMessageBox.Yes|QtGui.QMessageBox.No
                                         )
        if res != QtGui.QMessageBox.Yes: return
        self.wave_model.takeRow(row)
        new_row = row - 1
        if new_row < 0:
            new_row = 0
        elif new_row == self.wave_model.rowCount():
            new_row = self.wave_model.rowCount() - 1
        index = self.wave_model.index(new_row, 0)
        self.wave_list.selectionModel().select(index, QtGui.QItemSelectionModel.ClearAndSelect)
        self.setWaveSource(index)

    def resetWave(self):
        self.wave_source_view.draw_wave(self.currentStream.data(streamRole).toPyObject(), force=True)

    def setWaveSource(self, item, force=False):
        if item.row() == -1 or item.column() == -1:
            self.wave_source_view.clear()
            self.wave_panel.setEnabled(False)
            self.bal_panel.setVisible(False)
            return
        stream = item.data(streamRole).toPyObject()
        if isinstance(item, QtCore.QModelIndex):
            self.currentStream = self.wave_model.itemFromIndex(item)
        else:
            self.currentStream = item
        self.gain_spin.setValue(item.data(gainRole).toPyObject())
        if stream.getnchannels() == 1:
            self.bal_widget.setEnabled(False)
            self.bal_panel.setVisible(False)
        else:
            self.bal_widget.setEnabled(True)
            self.bal_panel.setVisible(self.bal_panel_visible)
            balance_active = item.data(balanceActiveRole).toPyObject()
            if balance_active:
                self.bal_chk.setChecked(True)
                self.bal_combo.setCurrentIndex(item.data(balanceModeRole).toPyObject())
                self.bal_slider.setValue(item.data(balanceValueRole).toPyObject())
            else:
                self.bal_chk.setChecked(False)
                self.left_spin.setValue(item.data(balanceLeftRole).toPyObject())
                self.right_spin.setValue(item.data(balanceRightRole).toPyObject())
        self.wave_source_view.draw_wave(stream, force)
        self.wave_source_view.current_source = item.data(QtCore.Qt.DisplayRole).toPyObject()










