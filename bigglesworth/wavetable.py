#!/usr/bin/env python2.7
# *-* coding: utf-8 *-*

import struct
import wave, audioop
from math import sqrt, pow, sin, pi
from PyQt4 import QtCore, QtGui, QtMultimedia

from bigglesworth.utils import load_ui
from bigglesworth.const import *
from bigglesworth.dialogs import WaveLoad
from bigglesworth.widgets import MagnifyingCursor, LineCursor, FreeDrawIcon, LineDrawIcon, CurveDrawIcon

sqrt_center = 4*(sqrt(2)-1)/3
_x0 = _y3 = 0
_y0 = _y1 = _x2 = _x3 = 1
_x1 = _y2 = sqrt_center

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

_NORMAL, _LINE = xrange(2)

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
        self.name = 'MyNewWavetable'

    def setData(self, slot, name):
        self.slot = slot
        self.name = name

    def setIndex(self, index):
        self.label.setText('Dumping wavetable "{}" to Blofeld slot {}, current wave: {}'.format(self.name, self.slot, index))

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

    def __init__(self, main, *args, **kwargs):
        QtGui.QGraphicsView.__init__(self, main, *args, **kwargs)
        self.main = main
        self.setToolTip('Shift+click to select a wave range, then drag the selection to the wave table list.')
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
        data.setData('audio/samples', samples)
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

    def leaveEvent(self, event):
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
    bgd_sweep_brush = QtGui.QBrush(QtGui.QColor(128, 128, 128, 128))
    bgd_brushes = bgd_normal_brush, bgd_sweep_brush

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

    def sweepHighlight(self, state):
        self.brush = self.bgd_brushes[state]
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
        _value = sine*pow19
        sine_values.append(_value)
        sine_wavepath.lineTo(p*16384, -_value)
    sine_preview_wavepath.translate(0, 32)
    sine_wavepath.translate(0, pow20)
    normal_pen = QtGui.QPen(QtCore.Qt.black)
    hover_pen = QtGui.QPen(QtCore.Qt.darkGreen)
    selected_pen = QtGui.QPen(QtCore.Qt.red)
    preview_pens = normal_pen, hover_pen, selected_pen

    def __init__(self, index):
        QtCore.QObject.__init__(self)
        self.index = index
        self.values = self.sine_values[:]
        #do we really need to create a self.preview_path?
        self.preview_path = QtGui.QPainterPath(self.sine_preview_wavepath)
        self.preview_path_item = QtGui.QGraphicsPathItem(self.preview_path)
        self.preview_rect = WavePlaceHolderItem(self, index, self.preview_path_item.boundingRect())
        self.path = QtGui.QPainterPath(self.sine_wavepath)
        self.hover.connect(self.preview_highlight)
        self._selected_state = False

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
        self.values = values
        for index, value in enumerate(values):
            self.preview_path.setElementPositionAt(index, index, 32 - value/32768)
            self.preview_path_item.setPath(self.preview_path)
            self.path.setElementPositionAt(index, index*16384, pow20 - value)
        self.changed.emit(self)
        #dirty. check it!
        self.valueChanged.emit(self)

    def setValue(self, index, value):
        self.values[index] = value
        self.valueChanged.emit(self)
#        return
        self.preview_path.setElementPositionAt(index, index, 32 - value/32768)
        self.preview_path_item.setPath(self.preview_path)
        self.path.setElementPositionAt(index, index*16384, pow20 - value)

    def preview_highlight(self, state):
        if not self.selected_state:
            self.preview_path_item.setPen(self.preview_pens[state])


class WaveTableView(QtGui.QGraphicsView):
    def __init__(self, *args, **kwargs):
        QtGui.QGraphicsView.__init__(self, *args, **kwargs)
        self.setScene(QtGui.QGraphicsScene())
        self.setRenderHints(QtGui.QPainter.Antialiasing)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

    def setWaveTable(self, waveobj_list):
        self.waveobj_list = waveobj_list
        self.wavegroup = QtGui.QGraphicsItemGroup()
        for i, wave_obj in enumerate(waveobj_list):
#            wave_obj.selected.connect(self.select)
            wave_obj.preview_path_item.setX(i*128)
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

#    def select(self, *args):
#        pass

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat('audio/samples'):
            event.accept()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        pass

    def dragMoveEvent(self, event):
        if not event.mimeData().hasFormat('audio/samples'):
            event.ignore()
            return
        data = event.mimeData().data('audio/samples')
        wave_len = int(len(data) * 0.00390625)
        items = [i for i in self.items(event.pos()) if isinstance(i, WavePlaceHolderItem)]
        if not items: return
        index = items[0].index
        for r in self.waveobj_list[:index]:
            r.preview_rect.sweepHighlight(False)
        if index + wave_len > 64:
            event.ignore()
            for r in self.waveobj_list[index:-1]:
                r.preview_rect.sweepHighlight(True)
        else:
            event.accept()
            for r in self.waveobj_list[index:index + wave_len + 1]:
                r.preview_rect.sweepHighlight(True)
            for r in self.waveobj_list[index + wave_len:]:
                r.preview_rect.sweepHighlight(False)

    def dropEvent(self, event):
        items = [i for i in self.items(event.pos()) if isinstance(i, WavePlaceHolderItem)]
        if not items: return
        index = items[0].index
        data = event.mimeData().data('audio/samples')
        for w in xrange(len(data) / 256):
            values = []
            for s in xrange(128):
                values.append(audioop.getsample(data, 2, w * 128 + s) * 31)
            self.waveobj_list[index + w].setValues(values)
        for r in self.waveobj_list:
            r.preview_rect.sweepHighlight(False)
        event.accept()

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

    def __init__(self, parent=None):
        QtGui.QGraphicsWidget.__init__(self, parent)
        self.setFlags(self.ItemIsMovable|self.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        self.shape_path = QtGui.QPainterPath()
        self.shape_path.addRect(-15000, -15000, 30000, 30000)

    def setMoveFunction(self, fn):
        self.move = fn

    def itemChange(self, change, value):
        if change == self.ItemPositionChange:
            pos = value.toPyObject()
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
        hor = self.addLine(0, pow21, pow21, pow21)
        hor.setPen(pen)
        main_h_lines[16].setPen(QtGui.QPen(QtGui.QColor(200, 0, 100), 4096))

        self.cursor = QtGui.QGraphicsItemGroup()
        rule_pen = QtGui.QPen(QtCore.Qt.blue, 2048)
#        rule_pen.setStyle(QtCore.Qt.DotLine)

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
        self.cursor.setPos(-16384, -16384)

        line_pen = QtGui.QPen(QtCore.Qt.red, 4096)
        self.linedraw = self.addLine(-16384, -16384, -16384, -16384)
        self.linedraw.setPen(line_pen)
        self.linedraw.setVisible(False)

        self.curvepath = QtGui.QGraphicsPathItem(QtGui.QPainterPath())
        self.curvepath.setPen(self.curve_valid_pen)
        self.curve_valid = True
        self.addItem(self.curvepath)

        self.curve_cp1 = ControlPoint()
        self.curve_cp1.setVisible(False)
#        self.curve_cp1.setMoveFunction(self.curve_cp_move)
        self.curve_cp1.moved.connect(self.curve_cp_move)
        self.addItem(self.curve_cp1)

        self.curve_cp2 = ControlPoint()
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
        self.wave_path = self.scene.addPath(QtGui.QPainterPath())
        self.mouse_prev = None
        self.cursors = {
                        CURSOR_NORMAL: self.cursor(), 
                        CURSOR_LINE: LineCursor(), 
                        CURSOR_CURVE: LineCursor(), 
                        }
        self.draw_mode = _NORMAL

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
        self.setCursor(self.cursors[mode])

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
        if self.draw_mode == CURSOR_LINE:
            self.scene.linedraw.setVisible(False)
        elif self.draw_mode == CURSOR_CURVE:
            self.scene.clear_curve()

    def viewKeyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            if self.draw_mode == CURSOR_LINE:
                self.scene.linedraw.setVisible(False)
            elif self.draw_mode == CURSOR_CURVE:
                self.scene.clear_curve()
        elif event.key() == QtCore.Qt.Key_Return:
            if self.draw_mode == CURSOR_CURVE:
                if self.scene.curve_valid:
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
                self.scene.clear_curve()

    def viewEnterEvent(self, event):
        self.scene.cursor.setVisible(True)

    def viewLeaveEvent(self, event):
        self.scene.cursor.setVisible(False)

    def viewMousePressEvent(self, event):
#        QtGui.QGraphicsView.mousePressEvent(self.view, event)
        pos = self.view.mapToScene(event.pos())
        sample, value = self.computePosValue(pos)
        if self.draw_mode == CURSOR_LINE:
            source = self.wave_path.path().elementAt(sample)
            x2 = sample * 16384
            y2 = pow20 - value
            self.scene.linedraw.setLine(source.x, source.y, x2, y2)
            self.scene.linedraw.setVisible(True)
            self.mouse_prev = sample, pow20 - source.y
        elif self.draw_mode == CURSOR_CURVE:
            if self.scene.curvepath.isVisible() and self.scene.curve_complete:
                return QtGui.QGraphicsView.mousePressEvent(self.view, event)
            source = self.wave_path.path().elementAt(sample)
            self.scene.setCurveStart(source.x, source.y, sample)
            self.scene.curvepath.setVisible(True)
#            self.mouse_prev = sample, value
        else:
            self.valueChanged.emit(sample, value)
            self.mouse_prev = sample, value

    def viewMouseMoveEvent(self, event):
        if self.draw_mode == CURSOR_CURVE and self.scene.curvepath.isVisible() and self.scene.curve_complete:
            QtGui.QGraphicsView.mouseMoveEvent(self.view, event)
            self.scene.update()

#        QtGui.QGraphicsView.mouseMoveEvent(self.view, event)
        pos = self.view.mapToScene(event.pos())
#        item = self.scene.itemAt(pos, self.view.transform())
#        if isinstance(item, ControlPoint):
##            item.mouseMoveEvent(event)
#            return
        sample, value = self.computePosValue(pos)
        self.scene.cursor.setPos(sample * 16384, pow20 - value)
        self.scene.cursor_text.setPlainText('Sample: {}\nValue: {}'.format(sample + 1, value))
        if event.buttons():
            if self.draw_mode == CURSOR_LINE:
                if not self.scene.linedraw.isVisible(): return
                self.scene.linedraw.setLine(self.scene.linedraw.line().x1(), self.scene.linedraw.line().y1(), sample * 16384, pow20 - value)
                return
            elif self.draw_mode == CURSOR_CURVE:
                if not self.scene.curvepath.isVisible(): return
                if self.scene.curve_complete:
#                    QtGui.QGraphicsView.mouseMoveEvent(self.view, event)
                    return
                path = QtGui.QPainterPath()
                x1, y1 = self.scene.curve_start
                x2 = sample * 16384
                y2 = pow20 - value
                path.moveTo(x1, y1)
                path.cubicTo(x2, y1, x2, y1, x2, y2)
                self.scene.curvepath.setPath(path)
                return
            prev_sample, prev_value = self.mouse_prev
            delta_sample = abs(sample - prev_sample)
            if delta_sample <= 1:
                if event.modifiers() == QtCore.Qt.ControlModifier:
                    value = prev_value
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
        if self.draw_mode == CURSOR_LINE and self.scene.linedraw.isVisible():
            self.scene.linedraw.setVisible(False)
            sample, value = self.computePosValue(self.view.mapToScene(event.pos()))
            prev_sample, prev_value = self.mouse_prev
            delta_sample = abs(sample - prev_sample)
            if delta_sample <= 1:
                self.valueChanged.emit(sample, value)
                self.mouse_prev = None
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
        elif self.draw_mode == CURSOR_CURVE and self.scene.curvepath.isVisible():
            if self.scene.curve_complete:
                return QtGui.QGraphicsView.mouseReleaseEvent(self.view, event)
            sample, value = self.computePosValue(self.view.mapToScene(event.pos()))
            x2 = sample * 16384
            y2 = pow20 - value
            self.scene.setCurveEnd(x2, y2, sample)
        self.mouse_prev = None

    def setWavePath(self, wave_obj):
        self.wave_path.setPath(wave_obj.path)

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
            wave_obj.valueChanged.connect(self.update)
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
#        rest = (self.start + size) % self.delta
        slice = str(self.current_data.mid(self.start, size))
        self.start = (self.start + size) % self.delta
#        if rest:
#            self.start = rest
#        else:
#            self.start = 0
#        try:
        return slice
#        finally:
#            if self.full_mode:
#                pos = self.start / 1024
#                if pos < 64:
#                    index = pos
#                elif pos < 126:
#                    index = 126 - pos
#                elif pos < 190:
#                    index = 126 + pos
#                else:
#                    index = 252 - pos
#                print index/4
##                self.sweep.emit(self.start % self.delta)


class WaveTableEditor(QtGui.QMainWindow):
    wavetable_send = QtCore.pyqtSignal(object)

    def __init__(self, main):
        QtGui.QMainWindow.__init__(self)
        self.main = main
        load_ui(self, 'wavetable.ui')
        self.currentStream = None
        self.wave_source_view = WaveSourceView(self)
        self.wave_source_view.setMinimumHeight(100)
        self.wave_source_view.installEventFilter(self)
        self.wave_layout.insertWidget(0, self.wave_source_view)
        self.wave_source_view.setMain(self)
        self.wave_source_view.sampleSelectionChanged.connect(self.setSampleSelection)
        self.sel_start = 0
        self.sel_end = 127

        self.wave_model = QtGui.QStandardItemModel()
        self.wave_list.setModel(self.wave_model)

        self.draw_timer = QtCore.QTimer()
        self.draw_timer.setSingleShot(True)
        self.draw_timer.setInterval(250)
        self.draw_timer.timeout.connect(self.resetWave)

        self.wave_list.currentChanged = self.setWaveSource
        self.add_wave_btn.clicked.connect(self.load_wave)
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

        self.waveobj_list = []
        for w in xrange(64):
            wave_obj = WaveObject(w)
            wave_obj.selected.connect(self.setWave)
            self.waveobj_list.append(wave_obj)
        self.wavetable_view.setWaveTable(self.waveobj_list)
        self.wavetable3d_view.setWaveTable(self.waveobj_list)
        self.currentWave = 0
        self.setWave(self.waveobj_list[0])

        self.wave_view.valueChanged.connect(self.setWaveValue)

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

        self.audio_buffer = AudioBuffer(self.waveobj_list)

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

        self.dump_dialog = DumpDialog(self)

        self.installEventFilter(self)

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
            self.waveobj_list[self.sweep_index].preview_rect.sweepHighlight(False)
            self.waveobj_list[index].preview_rect.sweepHighlight(True)
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
                self.waveobj_list[self.sweep_index].preview_rect.sweepHighlight(False)
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
                self.waveobj_list[self.sweep_index].preview_rect.sweepHighlight(False)
                self.wavetable3d_view.wave_list[self.sweep_index].highlight(False)

#    def showEvent(self, event):
#        sizes = self.splitter.sizes()
#        sizes[0] = 0
#        self.splitter.setSizes(sizes)

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
        data = self.createSysExData(False)
        print len(data[0])

    def createSysExData(self, midi=True):
        #to do: text check (and remove int from for cycle)
        sysex_list = []
        slot = self.slot_spin.value()
        name = (ord(l) for l in str(self.name_edit.text().toUtf8()).ljust(14, ' '))
        for n, wave_obj in enumerate(self.waveobj_list):
            sysex_data = [IDW, IDE, self.main.blofeld_id, WTBD, slot, n, 0]
            for value in wave_obj.values:
                value = int(value)
                if value < 0:
                    value = pow21 + value
                sysex_data.extend((value >> 14, (value >> 7) & 127,  value & 127))
            sysex_data.extend(name)
            sysex_data.extend((0, 0, CHK))
            if midi:
                sysex_data.insert(0, INIT)
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

    def load_wave(self):
        res = WaveLoad(self.main).exec_()
        if not res: return
        if self.wave_model.findItems(res, column=1):
            QtGui.QMessageBox.information(self, 'File already imported', 'The selected file is already in the wave list.')
            return
        stream = wave.open(str(res.toUtf8()))
        info = QtCore.QFileInfo(res)
        item = QtGui.QStandardItem(info.fileName())
        item.setData(res, pathRole)
        item.setData(stream, streamRole)
        item.setData(1., gainRole)
        if stream.getnchannels() > 1:
            item.setData(True, balanceActiveRole)
            item.setData(0, balanceModeRole)
            item.setData(50, balanceValueRole)
            item.setData(.5, balanceLeftRole)
            item.setData(.5, balanceRightRole)
        path_item = QtGui.QStandardItem(res)
        self.wave_model.appendRow([item, path_item])
        self.setWaveSource(item, force=True)
        self.wave_list.selectionModel().select(self.wave_model.index(self.wave_model.rowCount()-1, 0), QtGui.QItemSelectionModel.ClearAndSelect)
        self.wave_panel.setEnabled(True)
        self.del_wave_btn.setEnabled(True)

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










