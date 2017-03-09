#!/usr/bin/env python2.7
# *-* coding: utf-8 *-*

from math import pi, sin, cos, acos, hypot, radians, degrees
from bisect import bisect_left
from PyQt4 import QtCore, QtGui

from midiutils import NoteIds, NoteNames
from utils import getAlignMask

ADSR, ADS1DS2R, ONESHOT, LOOPS1S2, LOOPALL = range(5)
VERTICAL = QtCore.Qt.Vertical
HORIZONTAL = QtCore.Qt.Horizontal
TOP = QtCore.Qt.TopSection
BOTTOM = QtCore.Qt.BottomSection
LEFT = QtCore.Qt.LeftSection
RIGHT = QtCore.Qt.RightSection
FROM, TO, EXT, INT = range(4)

class Key(QtGui.QGraphicsWidget):
    def __init__(self, parent):
        QtGui.QGraphicsWidget.__init__(self, parent)

    def paint(self, painter, *args, **kwargs):
        painter.drawRect(0, 0, 40, 40)

class KeyItem(QtGui.QGraphicsItem):
    noteEvent = QtCore.pyqtSignal(int, int)
    key_name_font = QtGui.QFont()
    def __init__(self, note, text=False):
        QtGui.QGraphicsItem.__init__(self, parent=None)
        self.note = note
        self.note_name = NoteNames[note]
        self.note_short = self.note_name[0].upper()
        if isinstance(text, bool):
            self.note_label = self.note_short if text else ''
        else:
            self.note_label = text
        self.setAcceptHoverEvents(True)
        self.base_height = 100
        self.base_x = 0
        self.base_width = 20
        self.border_pen = QtGui.QPen(QtCore.Qt.darkGray, 1)
        self.pressed = 2
        self.shadow = 5
        self.current = self

    def boundingRect(self):
        return QtCore.QRectF(0, 0, self.base_x+self.base_width+1, self.base_height)

    def mouseMoveEvent(self, event):
        if not self.boundingRect().contains(event.pos()):
            item = self.scene().itemAt(self.mapToScene(event.pos()))
            if isinstance(item, QtGui.QGraphicsItem):
                if item != self.current:
                    try:
                        self.current.release()
                    except:
                        pass
                    item.push(int(round(1+event.pos().y()*126/item.boundingRect().height(), 0)))
                    self.current = item
            else:
                try:
                    self.current.release()
                    self.current = None
                except:
                    pass
        else:
            if self.current != self:
                try:
                    self.current.release()
                except:
                    pass
                self.push(int(round(1+event.pos().y()*126/self.boundingRect().height(), 0)))
                self.current = self

    def mousePressEvent(self, event):
        self.current = self
        self.push(int(round(1+event.pos().y()*126/self.boundingRect().height(), 0)))

    def push(self, vel=127):
        self.scene().views()[0].noteEvent.emit(self.note, vel)
        self.key_color = self.key_color_dn
        self.pressed = 0
        self.shadow = 2
        self.update()

    def mouseReleaseEvent(self, event):
        try:
            self.current.release()
        except:
            pass

    def release(self):
        self.scene().views()[0].noteEvent.emit(self.note, 0)
        self.key_color = self.key_color_up
        self.pressed = 2
        self.shadow = 5
        self.update()

    def paint_white(self, painter, *args, **kwargs):
        painter.translate(.5, .5)
        painter.setRenderHints(QtGui.QPainter.Antialiasing)
        painter.setPen(QtCore.Qt.lightGray)
        painter.setBrush(self.key_color)
        painter.drawRect(self.base_x, 0, self.base_width, self.base_height-self.pressed)
        painter.setPen(self.key_name_color)
        painter.drawText(self.base_x, 0, self.base_width, self.base_height-5, QtCore.Qt.AlignHCenter|QtCore.Qt.AlignBottom, self.note_label)

    def paint_black(self, painter, *args, **kwargs):
        painter.translate(.5, .5)
        painter.setRenderHints(QtGui.QPainter.Antialiasing)
        painter.setPen(self.border_pen)
        painter.drawRect(self.base_x, 0, self.base_width, self.base_height)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(self.key_shadow)
        painter.drawRect(self.base_x+self.base_width, 0, self.shadow, self.base_height)
        painter.setBrush(self.key_color)
        painter.drawRect(self.base_x, 0, self.base_width, self.base_height-4-self.pressed)
        painter.setBrush(self.key_angle)
        painter.drawRect(self.base_x, self.base_height-5-self.pressed, self.base_width, 5+self.pressed)
        painter.setPen(self.key_name_color)
        painter.drawText(self.base_x, 0, self.base_width, self.base_height-5, QtCore.Qt.AlignHCenter|QtCore.Qt.AlignBottom, self.note_label)

class WhiteKey(KeyItem):
    key_color_up = QtCore.Qt.white
    key_color_dn = QtGui.QRadialGradient(0, .75, .5)
    key_color_dn.setColorAt(0, QtGui.QColor(180, 180, 180))
    key_color_dn.setColorAt(1, key_color_up)
    key_color_dn.setCoordinateMode(QtGui.QRadialGradient.ObjectBoundingMode)
    key_name_color = QtCore.Qt.black
    def __init__(self, note, text):
        KeyItem.__init__(self, note, text)
        self.font_pen = QtGui.QPen()
        self.paint = self.paint_white
        self.key_color = self.key_color_up

class BlackKey(KeyItem):
    key_color_up = QtGui.QColor(30, 30, 30)
    key_color_dn = QtGui.QColor(18, 18, 18)
    key_shadow = QtGui.QColor(180, 180, 180, 200)
    key_angle = QtCore.Qt.black
    key_name_color = QtCore.Qt.white
    def __init__(self, note, text):
        KeyItem.__init__(self, note, text)
        self.base_x = 2.5
        self.base_width = 14
        self.base_height = self.base_height*.625
        self.paint = self.paint_black
        self.key_color = self.key_color_up

class Piano(QtGui.QGraphicsView):
    noteEvent = QtCore.pyqtSignal(int, int)
    def __init__(self, parent=None, lower='c2', higher='c7', key_list=None, key_list_start=12):
        QtGui.QGraphicsView.__init__(self, parent)
        self.scene = QtGui.QGraphicsScene(self)
        self.main = parent
        self.keys = {}
        self.setFrameStyle(0)
        self.scene = QtGui.QGraphicsScene(self)
        self.setScene(self.scene)
        self.draw_keyboard(lower, higher, key_list, key_list_start)

    def draw_keyboard(self, lower, higher, key_list, key_list_start):
        if isinstance(lower, str):
            lower = NoteIds[lower]
        if isinstance(higher, str):
            higher = NoteIds[higher]
        white = 0
        for k, n in enumerate(range(lower, higher+1)):
            if key_list and k >= key_list_start and k < (len(key_list)+key_list_start):
                text = key_list[k-key_list_start]
            else:
                text = ''
            if '#' not in NoteNames[n]:
                key = WhiteKey(n, text)
                self.scene.addItem(key)
                key.setPos(20*white, 0)
                key.setZValue(0)
                white += 1
            else:
                key = BlackKey(n, text)
                d = 0
                if key.note_short in ['C', 'F']:
                    d = -1
                elif key.note_short in ['D', 'A']:
                    d = 1
                self.scene.addItem(key)
                key.setPos(20*white-10+d, 0)
                key.setZValue(1)
            self.keys[n] = key
        self.key_range = white

    def resizeEvent(self, event):
        self.fitInView(0, 0, self.key_range*20, 100, QtCore.Qt.IgnoreAspectRatio)

class Label(QtGui.QWidget):
    _pen_enabled = QtGui.QPen(QtCore.Qt.white)
    _pen_disabled = QtGui.QPen(QtCore.Qt.darkGray)
    _pen_colors = _pen_disabled, _pen_enabled
    pen = _pen_colors[1]
    path = QtGui.QPainterPath()
    path_rect = QtCore.QRectF()
#    label_pos = RIGHT
    base_translate = QtCore.QPointF(0, 0)
    def __init__(self, parent=None, text='', text_align=QtCore.Qt.AlignHCenter|QtCore.Qt.AlignVCenter, label_pos=RIGHT, path=None):
        QtGui.QWidget.__init__(self, parent)
        self.text = text
        self.text_align = text_align
        self.font = QtGui.QFont('Decorative', 9, QtGui.QFont.Bold)
        self.font_metrics = QtGui.QFontMetrics(self.font)
        text_split = text.split('\n')
        text_height = self.font_metrics.height()*len(text_split)
        text_width = max([self.font_metrics.width(t) for t in text_split])
        self.label_rect = QtCore.QRectF(0, 0, text_width, text_height)
#        self.setSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Preferred)
        if path:
            self.path = path
            self.path_rect = self.path.boundingRect()
        if not self.path_rect:
            self.setMinimumSize(self.label_rect.width(), self.label_rect.height())
        else:
            self.label_pos = label_pos
            if label_pos in (TOP, BOTTOM):
                self.setMinimumSize(max(self.label_rect.width(), self.path_rect.width()), self.label_rect.height()+self.path_rect.height()+2)
                self.label_rect.setWidth(max(self.label_rect.width(), self.path_rect.width()))
            else:
                self.setMinimumSize(self.label_rect.width()+self.path_rect.width()+2, max(self.label_rect.height(), self.path_rect.height()))
                self.label_rect.setHeight(max(self.label_rect.height(), self.path_rect.height()))
            if label_pos == TOP:
                self.path_rect.moveTop(self.label_rect.bottom()+2)
                if self.path_rect.width() < self.label_rect.width():
                    self.path_rect.moveLeft((self.label_rect.width()-self.path_rect.width())/2)
            elif label_pos == BOTTOM:
                self.label_rect.moveTop(self.path_rect.bottom()+2)
                if self.path_rect.width() < self.label_rect.width():
                    self.path_rect.moveLeft((self.label_rect.width()-self.path_rect.width())/2)
            elif label_pos == LEFT:
                self.path_rect.moveLeft(self.label_rect.right()+2)
                if self.path_rect.height() < self.label_rect.height():
                    self.path_rect.moveTop((self.label_rect.height()-self.path_rect.height())/2)
            else:
                self.label_rect.moveLeft(self.path_rect.right()+2)
                if self.path_rect.height() < self.label_rect.height():
                    self.path_rect.moveTop((self.label_rect.height()-self.path_rect.height())/2)

    def changeEvent(self, event):
        if not event.type() == QtCore.QEvent.EnabledChange: return
        state = self.isEnabled()
        self.pen = self._pen_colors[state]
        self.update()

    def setText(self, text):
        self.text = text
        self.update()

    def paintEvent(self, event):
        qp = QtGui.QPainter()
        qp.begin(self)
        qp.setRenderHints(QtGui.QPainter.Antialiasing)
        qp.translate(self.base_translate)
        qp.setPen(self.pen)
#        qp.drawRect(0, 0, self.width()-1, self.height()-1)

        qp.setFont(self.font)
        qp.drawText(self.label_rect, self.text_align, self.text)
        if self.path:
            qp.translate(self.path_rect.x(), self.path_rect.y())
            qp.drawPath(self.path)

        qp.end()

    def resizeEvent(self, event):
        full_rect = self.label_rect.united(self.path_rect)
        diff = QtCore.QRectF(0, 0, self.width(), self.height()).center()-full_rect.center()
        self.base_translate = QtCore.QPointF(diff.x(), diff.y())

class Section(QtGui.QWidget):
    def __init__(self, parent=None, color=None, alpha=None, width=0, height=0, border=False, border_color=None, label='', label_pos=TOP):
        QtGui.QWidget.__init__(self, parent)
        if color is None:
            self.brush = QtGui.QColor(30, 35, 35, 200 if alpha is None else alpha)
        else:
            if len(color) == 4:
                self.brush = QtGui.QColor(*color)
            else:
                self.brush = QtGui.QColor(*color, a=200 if alpha is None else alpha)
        if not border:
            self.pen = QtCore.Qt.NoPen
        elif border_color is None:
            self.pen = QtGui.QPen(QtGui.QColor(40, 45, 45, 255), 1)
        else:
            self.pen = QtGui.QPen(QtGui.QColor(*border_color))
        if label:
            self.label = Label(self, label)
            self.label.setSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Minimum)
            self.label.move(0, 0)
        else:
            self.label = None
        if width > 0:
            self.max_width = width
        else:
            self.max_width = None
        if height > 0:
            self.max_height = height
        else:
            self.max_height = None

    def paintEvent(self, event):
        qp = QtGui.QPainter()
        qp.begin(self)
        qp.setRenderHints(QtGui.QPainter.Antialiasing)
        qp.translate(.5, .5)
        qp.setPen(self.pen)
        qp.setBrush(self.brush)
        qp.drawRoundedRect(self.rect, 2, 2)
        qp.end()

    def resizeEvent(self, event):
        if self.max_width:
            x = (self.width()-1-self.max_width)/2.
            width = self.max_width
        else:
            x = 0
            width = self.width()-1
        if self.max_height:
            y = (self.height()-1-self.max_height)/2.
            height = self.max_height
        else:
            y = 0
            height = self.height()-1
        self.rect = QtCore.QRectF(x, y, width, height)

class Routing(QtGui.QWidget):
    base_size = 12
    base_rect = QtCore.QRect(-4, -4, 4, 4)
    top_triangle = QtGui.QPainterPath(QtCore.QPoint(0, -4))
    top_triangle.lineTo(-4, 4)
    top_triangle.lineTo(0, 0)
    top_triangle.lineTo(4, 4)
    top_triangle.closeSubpath()
    bottom_triangle = QtGui.QPainterPath(QtCore.QPoint(0, 4))
    bottom_triangle.lineTo(-4, -4)
    bottom_triangle.lineTo(0, 0)
    bottom_triangle.lineTo(4, -4)
    bottom_triangle.closeSubpath()
    left_triangle = QtGui.QPainterPath(QtCore.QPoint(-4, 0))
    left_triangle.lineTo(4, -4)
    left_triangle.lineTo(0, 0)
    left_triangle.lineTo(4, 4)
    left_triangle.closeSubpath()
    right_triangle = QtGui.QPainterPath(QtCore.QPoint(4, 0))
    right_triangle.lineTo(-4, -4)
    right_triangle.lineTo(0, 0)
    right_triangle.lineTo(-4, 4)
    right_triangle.closeSubpath()

    def __init__(self, parent=None, start=BOTTOM, end=BOTTOM, direction=FROM, orientation=HORIZONTAL, padding=4):
        QtGui.QWidget.__init__(self, parent)
        self.direction = direction
        self.orientation = orientation
        self.invert = False
        self.internals = []
        if isinstance(padding, int):
            self.horizontal_padding = self.vertical_padding = padding
        else:
            self.horizontal_padding, self.vertical_padding = padding
        self.conn_end = QtCore.QPoint(0, 0)
        if orientation == HORIZONTAL:
            self.setSizePolicy(QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.Fixed)
            if start == BOTTOM and end in [TOP, RIGHT]:
                start = end
                end = BOTTOM
                self.invert = True
            elif (start, end) == (RIGHT, LEFT):
                start, end = LEFT, RIGHT
                self.invert = True
            self.start_arrow_pos = start
            self.end_arrow_pos = end
            if start == end:
                self.setMinimumHeight(24+self.vertical_padding*2)
                if start == BOTTOM:
                    self.start = self.end_point = 4, 19
                    self.conn_start = self.conn_end_point = 4, 16
                    self.line_start = self.line_end_point = 12, 4
                else:
                    self.start = self.end_point = 4, 4
                    self.conn_start = self.conn_end_point = 4, 8
                    self.line_start = self.line_end_point = 12, 12
            elif set((start, end)) == set((LEFT, RIGHT)):
                self.setMinimumHeight(12+self.vertical_padding*2)
                self.start = self.end_point = 4, 6
                self.conn_start = self.conn_end_point = 6, 6
                self.line_start = self.line_end_point = 6, 6
            elif set((start, end)) == set((TOP, BOTTOM)):
                self.setMinimumHeight(32+self.vertical_padding*2)
                self.start = 4, 4
                self.end_point = 4, 28
                self.conn_start = 4, 10
                self.line_start = 10, 16
                self.line_end_point = 10, 16
                self.conn_end_point = 4, 22
            else:
                self.setMinimumHeight(24)
                self.start = 4, 4
                if start == TOP:
                    self.conn_start = 4, 10
                    self.line_start = 10, 16
                else:
                    self.conn_start = 6, 4
                    self.line_start = 6, 4
                if end == RIGHT:
                    self.end_point = 4, 4
                    self.conn_end_point = 6, 4
                    self.line_end_point = 6, 4
                else:
                    self.end_point = 4, 19
                    self.conn_end_point = 4, 10
                    self.line_end_point = 10, 4

            self.start = QtCore.QPoint(self.start[0]+self.horizontal_padding, self.start[1]+self.vertical_padding)
            self.end_point = QtCore.QPoint(self.end_point[0]+self.horizontal_padding, self.end_point[1]+self.vertical_padding)
            self.conn_start = QtCore.QPoint(self.conn_start[0]+self.horizontal_padding, self.conn_start[1]+self.vertical_padding)
            self.line_start = QtCore.QPoint(self.line_start[0]+self.horizontal_padding, self.line_start[1]+self.vertical_padding)
            self.line_end_point = QtCore.QPoint(self.line_end_point[0]+self.horizontal_padding, self.line_end_point[1]+self.vertical_padding)
            self.conn_end_point = QtCore.QPoint(self.conn_end_point[0]+self.horizontal_padding, self.conn_end_point[1]+self.vertical_padding)

            self.set_arrow(self.direction)

            self.paintEvent = self.linearHorizontalPaintEvent

    def set_arrow(self, direction):
        if self.start_arrow_pos == LEFT:
            start_dir = self.right_triangle, self.left_triangle
        elif self.start_arrow_pos == TOP:
            start_dir = self.bottom_triangle, self.top_triangle
        else:
            start_dir = self.top_triangle, self.bottom_triangle
        if self.end_arrow_pos == RIGHT:
            end_dir = self.right_triangle, self.left_triangle
        elif self.end_arrow_pos == TOP:
            end_dir = self.top_triangle, self.bottom_triangle
        else:
            end_dir = self.bottom_triangle, self.top_triangle
        if direction == FROM:
            start = end = 0 if not self.invert else 1
        elif direction == TO:
            start = end = 1 if not self.invert else 0
        elif direction == INT:
            start = 0
            end = 1
        else:
            start = 1
            end = 0
        self.start_arrow = start_dir[start]
        self.end_arrow = end_dir[end]
        self.direction = direction
        self.draw_horizontal_internals()

    def linearHorizontalPaintEvent(self, event):
        qp = QtGui.QPainter()
        qp.begin(self)
        qp.setRenderHints(QtGui.QPainter.Antialiasing)
        qp.translate(.5, .5)

        qp.setPen(QtCore.Qt.white)
#        qp.drawRect(0, 0, self.width()-1, self.height()-1)

        line = QtGui.QPainterPath(self.start)
        line.lineTo(self.conn_start)
        line.quadTo(self.conn_start.x(), self.line_start.y(), self.line_start.x(), self.line_start.y())
        line.lineTo(self.line_end)
        line.quadTo(self.conn_end.x(), self.line_end.y(), self.conn_end.x(), self.conn_end.y())
        line.lineTo(self.end)
#        line.lineTo(self.width()-self.end.x(), self.end.y())
        qp.drawPath(line)
#        qp.drawLine(self.start.x(), self.start.y(), self.width()-self.end.x(), self.height()-self.end.y())

        qp.setBrush(QtCore.Qt.white)

        if self.internals:
            qp.save()
            qp.translate(self.conn_start.x(), self.line_start.y())
            for x in self.internals:
                qp.translate(self.internals_div, 0)
                qp.drawPath(x)
            qp.restore()
        qp.save()
        qp.translate(self.start)
        qp.drawPath(self.start_arrow)
        qp.restore()
        qp.translate(self.end)
        qp.drawPath(self.end_arrow)

        qp.end()

    def draw_horizontal_internals(self):
        diff = self.conn_end.x() - self.conn_start.x()
        if diff < 120:
            self.internals = []
            return
        fact = 35.
        self.internals = []
        if self.direction in [EXT, INT]:
            res = int(round(diff/float(fact), 0))
            if not res&1:
                res -= 1
            if self.direction == EXT:
                start = self.left_triangle
                end = self.right_triangle
            else:
                start = self.right_triangle
                end = self.left_triangle
            for f in range(0, res/2):
                self.internals.append(start)
            for f in range(res/2, res-1):
                self.internals.append(end)
        else:
            res = int(round(diff/float(fact), 0))
            arrow = self.right_triangle if self.direction==FROM else self.left_triangle
            for f in range(int(diff/float(fact))):
                self.internals.append(arrow)
        self.internals_div = int(diff/float(res))

    def resizeEvent(self, event):
        width = self.width()
        self.end = QtCore.QPoint(width-self.end_point.x()-1, self.end_point.y())
        self.conn_end = QtCore.QPoint(width-self.conn_end_point.x()-1, self.conn_end_point.y())
        self.line_end = QtCore.QPoint(width-self.line_end_point.x()-1, self.line_end_point.y())
        self.draw_horizontal_internals()



class OSpacer(QtGui.QWidget):
    def __init__(self, parent=None, min_size=2, min_width=None, min_height=None, max_size=None, max_width=None, max_height=None):
        QtGui.QWidget.__init__(self, parent)
        self.setSizePolicy(QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.MinimumExpanding)
        if not any((min_width, min_height)):
            if isinstance(min_size, tuple):
                self.setMinimumSize(*min_size)
            elif min_size is None:
                self.setMinimumSize(0, 0)
            else:
                self.setMinimumSize(min_size, min_size)
        else:
            if min_width is not None:
                self.setMinimumWidth(min_width)
            if min_height is not None:
                self.setMinimumHeight(min_height)
        if max_size is not None:
            if isinstance(max_size, tuple):
                self.setMinimumSize(*max_size)
            else:
                self.setMinimumSize(max_size, max_size)
        else:
            if max_width is not None:
                self.setMaximumWidth(max_width)
            if max_height is not None:
                self.setMaximumHeight(max_height)

class HSpacer(OSpacer):
    def __init__(self, parent=None, min_width=None, max_width=None):
        OSpacer.__init__(self, parent, min_width, max_width, max_height=0)
        self.setSizePolicy(QtGui.QSizePolicy.MinimumExpanding if max_width is None else QtGui.QSizePolicy.Maximum, QtGui.QSizePolicy.Fixed)
        self.setMinimumHeight(0)

class VSpacer(OSpacer):
    def __init__(self, parent=None, min_height=None, max_height=None):
        OSpacer.__init__(self, parent, min_height, max_height, max_width=0)
        self.setSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.MinimumExpanding)
        self.setMinimumWidth(0)

class Slider(QtGui.QAbstractSlider):
    border_grad = QtGui.QConicalGradient(QtCore.QPointF(.5, .5), 45)
    border_grad.setCoordinateMode(QtGui.QConicalGradient.ObjectBoundingMode)
    _top = QtGui.QColor(30, 30, 30)
    _left = QtGui.QColor(40, 40, 40)
    _bottom = QtGui.QColor(100, 100, 100)
    _right = QtGui.QColor(60, 60, 60)
    border_grad.setColorAt(0, _top)
    border_grad.setColorAt(.25, _top)
    border_grad.setColorAt(.251, _left)
    border_grad.setColorAt(.5, _left)
    border_grad.setColorAt(.501, _bottom)
    border_grad.setColorAt(.75, _bottom)
    border_grad.setColorAt(.751, _right)
    border_grad.setColorAt(.998, _right)
    border_grad.setColorAt(1, _top)
    border_pen = QtGui.QPen(border_grad, 1)
    range_color = QtGui.QBrush(QtGui.QColor(20, 20, 20))
    value_grad = QtGui.QLinearGradient(0, 0, 1, 1)
    value_grad.setColorAt(0, QtGui.QColor(0, 0, 0, 0))
#    value_grad.setColorAt(0.001, QtCore.Qt.green)
#    value_grad.setColorAt(.7, QtCore.Qt.red)
#    value_grad.setColorAt(.9, QtCore.Qt.darkRed)
    value_grad.setColorAt(1, QtCore.Qt.black)
    value_color = QtGui.QBrush(value_grad)

    slider_color= QtGui.QColor(QtCore.Qt.gray)
    slider_rgb = slider_color.getRgb()[:3]

    slider_border = QtGui.QConicalGradient(QtCore.QPointF(.5, .5), 45)
    slider_border.setCoordinateMode(QtGui.QConicalGradient.ObjectBoundingMode)
    slider_up = QtGui.QColor(*(c+(255-c)*.4 for c in slider_rgb))
    slider_left = QtGui.QColor(*(c+(255-c)*.2 for c in slider_rgb))
    slider_down = QtGui.QColor(*(c*.5 for c in slider_rgb))
    slider_right = QtGui.QColor(*(c*.3 for c in slider_rgb))
    slider_border.setColorAt(0, slider_up)
    slider_border.setColorAt(.25, slider_up)
    slider_border.setColorAt(.251, slider_left)
    slider_border.setColorAt(.5, slider_left)
    slider_border.setColorAt(.501, slider_down)
    slider_border.setColorAt(.75, slider_down)
    slider_border.setColorAt(.751, slider_right)
    slider_border.setColorAt(.99, slider_right)
    slider_border.setColorAt(1, slider_up)
    slider_border = QtGui.QPen(slider_border, 1)

    def __init__(self, parent, orientation=VERTICAL, inverted=True, min_value=0, max_value=127, step=1, value=None, default=None, name='', label_pos=BOTTOM, center=False, show_bar=True, scale=False, gradient=False, size=None, min_size=None, max_size=None):
        QtGui.QAbstractSlider.__init__(self, parent)
        self.label_font = QtGui.QFont('Decorative', 9, QtGui.QFont.Bold)
        self.label_font_metrics = QtGui.QFontMetrics(self.label_font)
        self.setRange(min_value, max_value)
        self.setOrientation(orientation)
        self.setMouseTracking(True)

        if orientation == HORIZONTAL:
            inverted = not inverted
        self.inverted = -1 if inverted else 1
        if inverted:
            self.get_pos = self._get_pos_negative
        else:
            self.get_pos = self._get_pos_positive
        if value is not None:
            if value < min_value:
                self.value = min_value
            elif value > max_value:
                self.value = max_value
            else:
                self.value = value
        elif default:
            self.default_value = default
            self.value = default
        else:
            self.value = min_value
        self.range = max_value - min_value
        self.range_size = 8
        if orientation == VERTICAL:
            min_width = 20
            min_height = 24
            self.setSizePolicy(QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.Expanding)
            self.slider_rect = QtCore.QRectF(0, 0, 16, 4)
            self.resizeEvent = self.resizeEventVertical
            self.mouseMoveEvent = self.mouseMoveEventVertical
            self._setValue = self._setValueVertical
        else:
            min_width = 24
            min_height = 20
            self.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.MinimumExpanding)
            self.slider_rect = QtCore.QRectF(0, 0, 4, 16)
            self.resizeEvent = self.resizeEventHorizontal
            self.mouseMoveEvent = self.mouseMoveEventHorizontal
            self._setValue = self._setValueHorizontal
        self.name = name
        if name:
            self.label_pos = label_pos
            if label_pos in [TOP, BOTTOM]:
                self.setMinimumSize(max((min_width, self.label_font_metrics.width(self.name))), min_height)
            else:
                self.setMinimumSize(min_width, max((min_height, self.label_font_metrics.height())))
            self.spacing = 4
        else:
            self.label_pos = None
            self.spacing = 0
        self.cursor = GhostCursor(self, self.slider_rect.width()+4, self.slider_rect.height()+4)
        self.cursor.installEventFilter(self)
        self.cursor_mode = False
        self.current_delta = None

    @property
    def abs_value(self):
        return 1./(self.maximum()-self.minimum())*(self.value-self.minimum())

    def eventFilter(self, source, event):
        if source == self.cursor:
            if event.type() == QtCore.QEvent.MouseButtonPress and event.button() == QtCore.Qt.LeftButton:
                self.cursor_mode = True
                self.current_delta = event.pos().x() if self.orientation() == HORIZONTAL else event.pos().y()
                return True
            elif event.type() == QtCore.QEvent.MouseButtonRelease and event.button() == QtCore.Qt.LeftButton:
                self.cursor_mode = False
                self.current_delta = None
                return True
        return QtGui.QAbstractSlider.eventFilter(self, source, event)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            value= int(round((event.pos().y()-self.range_size/2)*self.range/self.range_range[1], 0))
            if self.inverted < 1:
                value = self.maximum()-value
            if value < self.value:
                value = self.value-self.pageStep()
            else:
                value = self.value+self.pageStep()
            if value < self.minimum():
                value = self.minimum()
            elif value > self.maximum():
                value = self.maximum()
            self._setValue(value)
            self.update()

    def mouseMoveEventVertical(self, event):
        if not event.buttons() == QtCore.Qt.LeftButton: return
        if not self.cursor_mode:
            return
        value = int(round((event.pos().y()-self.current_delta-self.range_size/2)*self.range/self.range_range[1], 0))
        if self.inverted < 1:
            value = self.maximum()-value
        if value < self.minimum():
            value = self.minimum()
        elif value > self.maximum():
            value = self.maximum()
        self.setValue(value)
        self.update()

    def mouseMoveEventHorizontal(self, event):
        if not event.buttons() == QtCore.Qt.LeftButton: return
        if not self.cursor_mode:
            return
        value = int(round((event.pos().x()-self.current_delta-self.range_size/2)*self.range/self.range_range[1], 0))
        if self.inverted < 1:
            value = self.maximum()-value
        if value < self.minimum():
            value = self.minimum()
        elif value > self.maximum():
            value = self.maximum()
        self.setValue(value)
        self.update()

    def wheelEvent(self, event):
        if event.modifiers() == QtCore.Qt.ShiftModifier:
            delta = self.singleStep()*5*-self.inverted
        else:
            delta = self.singleStep()*-self.inverted
        self.setValue(self.value+delta if event.delta() > 1 else self.value-delta)
        self.update()

    def _setValueVertical(self, value):
        if not self.minimum() <= value <= self.maximum(): return
        self.value = value
        pos = QtCore.QPointF(self.range_rect.center().x(), self.get_pos())
        self.slider_rect.moveCenter(pos)
        self.cursor.move(pos.x(), pos.y())
        self.update()

    def _setValueHorizontal(self, value):
        if not self.minimum() <= value <= self.maximum(): return
        self.value = value
        pos = QtCore.QPointF(self.get_pos(), self.range_rect.center().y())
        self.slider_rect.moveCenter(pos)
        self.cursor.move(pos.x(), pos.y())
        self.update()

    def setValue(self, value):
        if value < self.minimum():
            value = self.minimum()
        elif value > self.maximum():
            value = self.maximum()
        self._setValue(value)
        self.valueChanged.emit(self.value)
#        print self.value

    def paintEvent(self, event):
        qp = QtGui.QPainter()
        qp.begin(self)
        qp.translate(.5, .5)
        qp.setRenderHints(QtGui.QPainter.Antialiasing)

        #debug rect
#        qp.setPen(QtCore.Qt.black)
#        qp.drawRect(0, 0, self.width()-1, self.height()-1)

        #range
        qp.setPen(self.border_pen)
        qp.setBrush(self.range_color)
        qp.drawRoundedRect(self.range_rect, 2, 2)

        #value shade
        qp.setPen(QtCore.Qt.NoPen)
        value_color = QtGui.QColor(self.abs_value*180, 100-self.abs_value*100, 0)
        if self.orientation() == VERTICAL:
            self.value_grad.setStart(0, self.get_pos())
            self.value_grad.setFinalStop(0, self.range_rect.height()+self.range_rect.x())
            self.value_grad.setColorAt(.1, value_color)
            self.value_grad.setColorAt(.9, value_color.darker(300))
        else:
            self.value_grad.setStart(self.get_pos(), 0)
            self.value_grad.setFinalStop(0, 0)
            self.value_grad.setColorAt(.9, value_color)
            self.value_grad.setColorAt(.1, value_color.darker(300))

        qp.setBrush(self.value_grad)
        qp.drawRoundedRect(self.range_rect, 2, 2)

        #slider
        qp.setPen(self.slider_border)
        qp.setBrush(self.slider_color)
        qp.drawRoundedRect(self.slider_rect, 1., 1.)

        #label
        if self.name:
            qp.setFont(self.label_font)
            qp.setPen(QtCore.Qt.white)
            qp.drawText(self.label_rect, QtCore.Qt.AlignHCenter|QtCore.Qt.AlignVCenter, self.name)

        qp.end()


    def _get_pos_positive(self):
        return self.range_range[0]+self.range_range[1]*self.abs_value

    def _get_pos_negative(self):
        return self.range_range[1]-self.range_range[1]*self.abs_value+8

    def resizeEventVertical(self, event):
        if self.label_pos == TOP:
            y = self.label_font_metrics.height()+self.spacing
            height = y
            self.label_rect = QtCore.QRect(0, 0, self.width(), height)
        elif self.label_pos == BOTTOM:
            y = 0
            height = self.label_font_metrics.height()+self.spacing
            self.label_rect = QtCore.QRect(0, self.height()-height, self.width(), height)
        else:
            y = height = 0
        self.range_rect = QtCore.QRectF((self.width()-self.range_size)/2., self.range_size/2.+y, self.range_size, self.height()-self.range_size-height)
        self.range_range = self.range_rect.y()+4, self.range_rect.height()-8
        pos = QtCore.QPointF(self.range_rect.center().x(), self.get_pos())
        self.slider_rect.moveCenter(pos)
        self.cursor.move(pos.x(), pos.y())

    def resizeEventHorizontal(self, event):
        if self.label_pos == TOP:
            y = self.label_font_metrics.height()+self.spacing
            height = y
            self.label_rect = QtCore.QRect(0, 0, self.width(), height)
        elif self.label_pos == BOTTOM:
            y = 0
            height = self.label_font_metrics.height()+self.spacing
            self.label_rect = QtCore.QRect(0, self.height()-height, self.width(), height)
        else:
            y = height = 0
            x = width = 0
        self.range_rect = QtCore.QRectF(self.range_size/2.+x, (self.height()-self.range_size)/2., self.width()-self.range_size-width, self.range_size)
        self.range_range = self.range_rect.x()+4, self.range_rect.width()-8
        pos = QtCore.QPointF(self.get_pos(), self.range_rect.center().y())
        self.slider_rect.moveCenter(pos)
        self.cursor.move(pos.x(), pos.y())


class SquareButton(QtGui.QAbstractButton):
    @staticmethod
    def get_btn_colors(color):
        if isinstance(color, QtGui.QColor):
            up_color = color
        elif isinstance(color, tuple):
            up_color = QtGui.QColor(*color)
        else:
            up_color= QtGui.QColor(color)
#        print up_color, up_color.green()
        up_base = up_color.getRgb()[:3]
        down_color = up_color.darker(150)
        down_base = down_color.getRgb()[:3]

        up_border = QtGui.QConicalGradient(QtCore.QPointF(.5, .5), 45)
        up_border.setCoordinateMode(QtGui.QConicalGradient.ObjectBoundingMode)
        up_up = QtGui.QColor(*(c+(255-c)*.4 for c in up_base))
        up_left = QtGui.QColor(*(c+(255-c)*.2 for c in up_base))
        up_down = QtGui.QColor(*(c*.5 for c in up_base))
        up_right = QtGui.QColor(*(c*.3 for c in up_base))
        up_border.setColorAt(0, up_up)
        up_border.setColorAt(.25, up_up)
        up_border.setColorAt(.251, up_left)
        up_border.setColorAt(.5, up_left)
        up_border.setColorAt(.501, up_down)
        up_border.setColorAt(.75, up_down)
        up_border.setColorAt(.751, up_right)
        up_border.setColorAt(.99, up_right)
        up_border.setColorAt(1, up_up)

        up_grad = QtGui.QRadialGradient(15, 15, 30)
        up_grad.setColorAt(0, up_color)
        up_grad.setColorAt(1, up_color.darker(150))

        down_border = QtGui.QConicalGradient(QtCore.QPointF(.5, .5), 45)
        down_border.setCoordinateMode(QtGui.QConicalGradient.ObjectBoundingMode)
        down_up = QtGui.QColor(*(c*.5 for c in down_base))
        down_left = QtGui.QColor(*(c*.3 for c in down_base))
        down_down = QtGui.QColor(*(c+(255-c)*.3 for c in down_base))
        down_right = QtGui.QColor(*(c+(255-c)*.05 for c in down_base))
        down_border.setColorAt(0, down_up)
        down_border.setColorAt(.25, down_up)
        down_border.setColorAt(.251, down_left)
        down_border.setColorAt(.5, down_left)
        down_border.setColorAt(.501, down_down)
        down_border.setColorAt(.75, down_down)
        down_border.setColorAt(.751, down_right)
        down_border.setColorAt(.99, down_right)
        down_border.setColorAt(1, down_up)
        down_grad = QtGui.QRadialGradient(15, 15, 30)
        down_grad.setColorAt(0, down_color)
        down_grad.setColorAt(1, down_color.darker(150))
        return up_border, up_grad, down_border, down_grad
#        return QtGui.QPen(up_border, 1), QtGui.QBrush(up_grad), QtGui.QPen(down_border, 1), QtGui.QBrush(down_grad)

    unactive_border, unactive_grad, unactive_pressed_border, unactive_pressed_grad = get_btn_colors.__func__((150, 150, 150))
    unactive_pen = QtGui.QPen(unactive_border, 1)
    unactive_color = QtGui.QBrush(unactive_grad)
    unactive_pressed_pen = QtGui.QPen(unactive_pressed_border, 1)
    unactive_pressed_color = QtGui.QBrush(unactive_pressed_grad)
    enabled_text_pen = QtGui.QPen(QtCore.Qt.white)
    disabled_text_pen = QtGui.QPen(QtCore.Qt.gray)
    text_pen = enabled_text_pen
#    unactive_pen, unactive_color, unactive_pressed_pen, unactive_pressed_color = get_btn_colors.__func__((150, 150, 150))

    base_width = 40
    base_height = 20
    color = QtCore.Qt.green
    _text_align = QtCore.Qt.AlignHCenter|QtCore.Qt.AlignVCenter
    label_pos = BOTTOM

    def __init__(self, parent=None, name='', inverted=False, color=color, checkable=False, checked=False, size=None, text_align=None, label_pos=label_pos):
        QtGui.QAbstractButton.__init__(self, parent=parent)
        self.label_font = QtGui.QFont('Decorative', 9, QtGui.QFont.Bold)
        self.label_font_metrics = QtGui.QFontMetrics(self.label_font)
        self.setMinimumSize(self.base_width, self.base_height)
        self.setSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        self.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.toggled.connect(self.toggle_states)
        self.active_border, self.active_grad, self.active_pressed_border, self.active_pressed_grad = self.get_btn_colors(color)
        self.active_pen = QtGui.QPen(self.active_border, 1)
        self.active_color = QtGui.QBrush(self.active_grad)
        self.active_pressed_pen = QtGui.QPen(self.active_pressed_border, 1)
        self.active_pressed_color = QtGui.QBrush(self.active_pressed_grad)
        self.isPressed = False
        self.inverted = inverted
#        self.active_pen, self.active_color, self.active_pressed_pen, self.active_pressed_color = self.get_btn_colors(color)
        if not checkable:
            self.current_pen = self.active_pen
            self.current_color = self.active_color
        else:
            self.setCheckable(True)
            self.setChecked(checked)
            self.toggle_states(checked^inverted)
#            checked ^= inverted
#            self.current_pen = self.active_pen if checked else self.unactive_pen
#            self.current_color = self.active_color if checked else self.unactive_color
        if size:
            if isinstance(size, tuple):
                w, h = size
            else:
                w = h = size
        else:
            w = self.base_width
            h = self.base_height
        self.button_rect = QtCore.QRect(0, 0, w, h)
        self.name = name
        if not text_align:
            self.text_align = self._text_align
        else:
            self.text_align = getAlignMask(text_align, self._text_align)
        if name:
            spacing = 4
            txt_split = name.split('\n')
            txt_height = self.label_font_metrics.height()*len(txt_split)
            txt_width = max([self.label_font_metrics.width(txt) for txt in txt_split])
            self.label_rect = QtCore.QRect(0, 0, txt_width, txt_height)
            if label_pos == BOTTOM:
                self.label_rect.moveTop(self.button_rect.bottom()+spacing)
                if self.label_rect.width() > self.button_rect.width():
                    self.button_rect.moveLeft((self.label_rect.width()-self.button_rect.width())/2)
                elif self.label_rect.width() < self.button_rect.width():
                    self.label_rect.moveLeft((self.button_rect.width()-self.label_rect.width())/2)
            elif label_pos == TOP:
                self.button_rect.moveTop(self.label_rect.bottom()+spacing)
                if self.label_rect.width() > self.button_rect.width():
                    self.button_rect.moveLeft((self.label_rect.width()-self.button_rect.width())/2)
                elif self.label_rect.width() < self.button_rect.width():
                    self.label_rect.moveLeft((self.button_rect.width()-self.label_rect.width())/2)
            elif label_pos == RIGHT:
                self.label_rect.moveLeft(self.button_rect.right()+spacing)
                if self.label_rect.height() < self.button_rect.height():
                    self.label_rect.setHeight(self.button_rect.height())
                elif self.label_rect.height() > self.button_rect.height():
                    self.button_rect.moveTop((self.label_rect.height()-self.button_rect.height())/2)
            else:
                self.button_rect.moveLeft(self.label_rect.right()+spacing)
                if self.label_rect.height() < self.button_rect.height():
                    self.label_rect.setHeight(self.button_rect.height())
                elif self.label_rect.height() > self.button_rect.height():
                    self.button_rect.moveTop((self.label_rect.height()-self.button_rect.height())/2)
        else:
            self.label_rect = QtCore.QRect(0, 0, 0, 0)
        intersect = self.label_rect.united(self.button_rect)
        self.setMinimumSize(intersect.width(), intersect.height())
        self.setMaximumSize(intersect.width(), intersect.height())
        self.button_rect.setRight(self.button_rect.right()-1)
        self.button_rect.setBottom(self.button_rect.bottom()-1)
#        if name:
#            self.spacing = 4
#            self.label_rect = QtCore.QRect(0, 0, self.label_font_metrics.width(name), self.label_font_metrics.height())
#        else:
#            self.spacing = 0
#            self.label_rect = QtCore.QRect(0, 0, 0, 0)
#        if size:
#            max_width = max((size[0], self.label_rect.width()))
#            self.setMinimumSize(max_width, size[1]+self.spacing+self.label_rect.height())
#            self.button_rect = QtCore.QRectF((max_width-max_width)/2., 0, size[0], size[1])
#        elif min_size:
#            if isinstance(min_size, tuple):
#                w, h = min_size
#            else:
#                w = h = min_size
#            max_width = max((w, self.label_rect.width()))
#            self.setMinimumSize(max_width, h+self.spacing+self.label_rect.height())
#            self.button_rect = QtCore.QRectF((max_width-max_width)/2., 0, w, h)
#            self.setSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Fixed)
#        elif max_size:
#            if isinstance(max_size, tuple):
#                w, h = max_size
#            else:
#                w = h = max_size
#            max_width = max((w, self.label_rect.width()))
#            self.setMinimumSize(max_width, h+self.spacing+self.label_rect.height())
#            self.setMaximumSize(max_width, h+self.spacing+self.label_rect.height())
#            self.button_rect = QtCore.QRectF((max_width-w)/2., 0, w, h)
##            self.setSizePolicy(QtGui.QSizePolicy.Maximum, QtGui.QSizePolicy.Fixed)
#        else:
#            max_width = max((self.base_width, self.label_rect.width()))
#            self.setMinimumSize(max_width, self.base_height+self.spacing+self.label_rect.height())
#            self.button_rect = QtCore.QRectF((max_width-self.base_width)/2., 0, self.base_width, self.base_height)

#    def setChecked(self, state):
#        if self.inverted:
#            state = not state
#        QtGui.QAbstractButton.setChecked(self,state)

    def setText(self, text):
        self.name = text
        self.update()

    def changeEvent(self, event):
        if not event.type() == QtCore.QEvent.EnabledChange: return
#        QtGui.QAbstractButton.changeEvent(self, event)
        state = self.isEnabled()
        if not state:
            self.current_color = self.unactive_color
            self.current_pen = self.unactive_pen
            self.text_pen = self.disabled_text_pen
            self.repaint()
        else:
            self.text_pen = self.enabled_text_pen
            self.toggle_states(self.isChecked())

    def toggle_states(self, state):
        state ^= self.inverted
        if state:
            self.current_color = self.active_color
            self.current_pen = self.active_pen
        else:
            self.current_color = self.unactive_color
            self.current_pen = self.unactive_pen
        self.update()

    def set_pressed_colors(self):
        if self.isCheckable():
            self.current_color = self.active_pressed_color if self.isChecked() else self.unactive_pressed_color
            self.current_pen = self.active_pressed_pen if self.isChecked() else self.unactive_pressed_pen
        else:
            self.current_color = self.active_pressed_color
            self.current_pen = self.active_pressed_pen

    def mousePressEvent(self, event):
        self.set_pressed_colors()
        self.repaint()
        QtGui.QAbstractButton.mousePressEvent(self, event)

    def set_released_colors(self):
        if not self.isEnabled():
            self.current_color = self.unactive_color
            self.current_pen = self.unactive_pen
        elif self.isCheckable():
            self.current_color = self.active_color if self.isChecked() else self.unactive_color
            self.current_pen = self.active_pen if self.isChecked() else self.unactive_pen
        else:
            self.current_color = self.active_color
            self.current_pen = self.active_pen
        self.update()

    def mouseReleaseEvent(self, event):
        self.set_released_colors()
        self.repaint()
        QtGui.QAbstractButton.mouseReleaseEvent(self, event)

    def mouseMoveEvent(self, event):
        pressed = self.hitButton(event.pos())
        if pressed == self.isPressed: return
        self.isPressed = pressed
        if pressed:
            self.set_pressed_colors()
        else:
            self.set_released_colors()
        self.repaint()

    def keyPressEvent(self, event):
        event.ignore()

    def keyReleaseEvent(self, event):
        event.ignore()

    def paintEvent(self, event):
        qp = QtGui.QPainter()
        qp.begin(self)
        qp.translate(.5, .5)
        qp.setRenderHints(QtGui.QPainter.Antialiasing)
        qp.setPen(self.current_pen)
        qp.setBrush(self.current_color)
        qp.drawRoundedRect(self.button_rect, 2, 2)
        if self.name:
            qp.setPen(self.text_pen)
            qp.setFont(self.label_font)
            qp.drawText(self.label_rect, self.text_align, self.name)
        qp.end()

    def resizeEvent(self, event):
        width = self.width()
        height = self.height()
        x = width/2
        y = height/2
        radius = max(width, height)/2
        for c in ('active', 'active_pressed', 'unactive', 'unactive_pressed'):
            grad = getattr(self, '{}_grad'.format(c))
            grad.setCenter(x, y)
            grad.setRadius(radius)
            grad.setFocalPoint(x, y)
            setattr(self, '{}_color'.format(c), QtGui.QBrush(grad))
        self.set_released_colors()
#        if self.isCheckable():
#            self.current_color = self.active_color if self.isChecked() else self.unactive_color
#            self.current_pen = self.active_pen if self.isChecked() else self.unactive_pen
#        else:
#            self.current_color = self.active_color
#            self.current_pen = self.active_pen

class Frame(QtGui.QWidget):
    _fgd_line_normal = QtGui.QColor(QtCore.Qt.black)
    _fgd_line_highlight = QtGui.QColor(QtCore.Qt.gray)
    fgd_lines = _fgd_line_normal, _fgd_line_highlight
    _up = QtGui.QColor(180, 180, 180)
    _left = QtGui.QColor(80, 80, 80)
    _right = QtGui.QColor(120, 120, 120)
    _down = QtGui.QColor(200, 200, 200)
    border_grad = QtGui.QConicalGradient(QtCore.QPointF(.5, .5), 45)
    border_grad.setCoordinateMode(QtGui.QConicalGradient.ObjectBoundingMode)
    border_grad.setColorAt(0, _up)
    border_grad.setColorAt(.249, _up)
    border_grad.setColorAt(.25, _left)
    border_grad.setColorAt(.5, _left)
    border_grad.setColorAt(.501, _down)
    border_grad.setColorAt(.749, _down)
    border_grad.setColorAt(.75, _right)
    border_grad.setColorAt(.99, _right)
    border_grad.setColorAt(1, _up)
    border_pen = QtGui.QPen(border_grad, 1)
    def __init__(self, parent, title='', padding=1, ratio=1., ani_range=5):
        QtGui.QWidget.__init__(self, parent)
        self.font = QtGui.QFont('Decorative', 14, QtGui.QFont.Bold)
        self.font_metrics = QtGui.QFontMetrics(self.font)
        self.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.setSizePolicy(QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.Preferred)
        self.padding = padding
        if title:
            self.title = title
            top_margin = self.font_metrics.height()+self.padding+4
        else:
            self.title = None
            top_margin = 0
        self.setContentsMargins(2, 2+top_margin, 2, 2)

        self._fgd_line = self.fgd_lines[0]
        self.border_anim = QtCore.QPropertyAnimation(self, 'fgd_line')
        self.border_anim.setStartValue(self.fgd_lines[0])
        self.border_anim.setEndValue(self.fgd_lines[1])
        self.border_anim.valueChanged.connect(lambda value: self.update())
        

    @QtCore.pyqtProperty('QColor')
    def fgd_line(self):
        return self._fgd_line

    @fgd_line.setter
    def fgd_line(self, value):
        self._fgd_line = value

    def enterEvent(self, event):
        self.border_anim.setDirection(QtCore.QPropertyAnimation.Forward)
        self.border_anim.start()

    def leaveEvent(self, event):
        self.border_anim.setDirection(QtCore.QPropertyAnimation.Backward)
        self.border_anim.start()


    def paintEvent(self, e):
        qp = QtGui.QPainter()
        qp.begin(self)
        qp.translate(.5, .5)
        qp.setRenderHints(QtGui.QPainter.Antialiasing)

        #debug rect
#        qp.setPen(QtCore.Qt.green)
#        qp.drawRect(0, 0, self.width()-1, self.height()-1)

        qp.setPen(self.border_pen)
        qp.drawRoundedRect(0, 0, self.width()-1, self.height()-1, 2, 2)
        qp.setPen(self.fgd_line)
        qp.drawRoundedRect(self.fgd_rect, 1, 1)

        if self.title:
            qp.setPen(QtCore.Qt.NoPen)
            qp.setBrush(QtGui.QColor(240, 240, 240))
            rect = QtCore.QRectF(0, 0, self.font_metrics.width(self.title)+8, self.font_metrics.height()+4)
            qp.setPen(QtCore.Qt.NoPen)
            path = QtGui.QPainterPath()
            path.moveTo(rect.x()+rect.width()+rect.height()*2, rect.y())
            path.arcTo(rect.x(), rect.y(), 4, 4, 90, 90)
            path.lineTo(rect.x(), rect.height()-2)
            path.arcTo(rect.x(), rect.y()+rect.height()-4, 4, 4, 180, 90)
            path.lineTo(rect.width(), rect.y()+rect.height())
            path.arcTo(rect.width()-rect.height()/2-8, rect.y(), rect.height(), rect.height(), 270, 90)
            path.arcTo(rect.width()+rect.height()/2-8, rect.y(), rect.height(), rect.height(), 180, -90)
            qp.drawPath(path)

            qp.setFont(self.font)
            qp.setPen(QtCore.Qt.black)
            qp.drawText(rect, QtCore.Qt.AlignHCenter|QtCore.Qt.AlignVCenter, self.title)
        qp.end()

    def resizeEvent(self, event):
        self.fgd_rect = QtCore.QRectF(1, 1, self.width()-self.padding*2-1, self.height()-self.padding*2-1)

class EnvelopeObject(QtGui.QWidget):
    def __init__(self, parent, name='', cursor=QtCore.Qt.SizeAllCursor, *args, **kwargs):
        self.name = name
        self.cursor = QtGui.QCursor(cursor)
        QtGui.QWidget.__init__(self, parent)

class EnvelopePoint(EnvelopeObject):
    def __init__(self, parent=None, *args):
        EnvelopeObject.__init__(self, parent, *args)
        self.setFixedSize(12, 12)
        self.pen_normal = QtGui.QPen(parent.env_line)
        self.pen_normal.setWidth(2)
        self.pen_highlight = QtGui.QPen(QtGui.QColor(QtCore.Qt.red), 2)
        self.pen = self.pen_normal
        self.brush = parent.fgd_brush

    def enterEvent(self, event):
        self.pen = self.pen_highlight
        self.update()

    def leaveEvent(self, event):
        self.pen = self.pen_normal
        self.update()

    def paintEvent(self, event):
        qp = QtGui.QPainter()
        qp.begin(self)
#        qp.drawRect(0, 0, self.width()-1, self.height()-1)
        qp.translate(4, 4)
        qp.setPen(self.pen)
        qp.setBrush(self.brush)
        qp.setRenderHints(QtGui.QPainter.Antialiasing)
        qp.drawEllipse(0, 0, 4, 4)
        qp.end()

    def move(self, x, y):
        QtGui.QWidget.move(self, x-4, y-4)

    def moveAbs(self, x, y):
        QtGui.QWidget.move(self, x, y)


class EnvelopeLine(EnvelopeObject):
    def __init__(self, parent=None, *args):
        EnvelopeObject.__init__(self, parent, *args)
        self.resize(12, 12)
#        self.setFixedSize(20, 1)
        self.pen_normal = QtGui.QPen(QtCore.Qt.NoPen)
        self.pen_highlight = QtGui.QPen(QtGui.QColor(QtCore.Qt.red), 2)
        self.pen = self.pen_normal

    def enterEvent(self, event):
        self.pen = self.pen_highlight
        self.update()

    def leaveEvent(self, event):
        self.pen = self.pen_normal
        self.update()

    def paintEvent(self, event):
        qp = QtGui.QPainter()
        qp.begin(self)
        qp.translate(.5, 6.5)
        qp.setPen(self.pen)
        qp.setRenderHints(QtGui.QPainter.Antialiasing)
        qp.drawLine(0, 0, self.width(), 0)
        qp.end()

    def move(self, x, y):
        QtGui.QWidget.move(self, x, y-6)
#
#    def moveAbs(self, x, y):
#        QtGui.QWidget.move(self, x, y)


class Envelope(QtGui.QWidget):
    border_grad = QtGui.QConicalGradient(QtCore.QPointF(.5, .5), 45)
    border_grad.setCoordinateMode(QtGui.QConicalGradient.ObjectBoundingMode)
    _up = QtGui.QColor(180, 180, 180)
    _left = QtGui.QColor(80, 80, 80)
    _right = QtGui.QColor(120, 120, 120)
    _down = QtGui.QColor(200, 200, 200)
    border_grad.setColorAt(0, _up)
    border_grad.setColorAt(.249, _up)
    border_grad.setColorAt(.25, _left)
    border_grad.setColorAt(.5, _left)
    border_grad.setColorAt(.501, _down)
    border_grad.setColorAt(.749, _down)
    border_grad.setColorAt(.75, _right)
    border_grad.setColorAt(.99, _right)
    border_grad.setColorAt(1, _up)
    border_pen = QtGui.QPen(border_grad, 1)
    env_line = QtGui.QPen(QtCore.Qt.black)
    env_line.setCapStyle(QtCore.Qt.FlatCap)
    rel_line = QtGui.QPen(QtCore.Qt.darkGray, 1, QtCore.Qt.DotLine)
    loop_line = QtGui.QPen(QtCore.Qt.lightGray, 1, QtCore.Qt.DashLine)
    loop_limit_brush = QtGui.QBrush(QtCore.Qt.gray)
    loop_limit_left = QtGui.QPolygonF([QtCore.QPointF(-8, -4), QtCore.QPointF(-2, 0), QtCore.QPointF(-8, 4)])
    loop_limit_right = QtGui.QPolygonF([QtCore.QPointF(8, -4), QtCore.QPointF(2, 0), QtCore.QPointF(8, 4)])
    bgd_brush = QtGui.QBrush(QtGui.QColor(240, 250, 250, 230))
    fgd_brush = QtGui.QBrush(QtGui.QColor(240, 250, 250))
    label_fgd = QtGui.QColor(QtCore.Qt.darkGray)
    label_bgd = QtGui.QColor(240, 240, 240, 200)
    label_font = QtGui.QFont('Decorative', 10, QtGui.QFont.Bold)
    attackChanged = QtCore.pyqtSignal(int)
    attackLevelChanged = QtCore.pyqtSignal(int)
    decayChanged = QtCore.pyqtSignal(int)
    decay2Changed = QtCore.pyqtSignal(int)
    sustainChanged = QtCore.pyqtSignal(int)
    sustain2Changed = QtCore.pyqtSignal(int)
    releaseChanged = QtCore.pyqtSignal(int)
    envelopeChanged = QtCore.pyqtSignal(int)
    def __init__(self, parent, mode=ADSR, show_points=True):
        QtGui.QWidget.__init__(self, parent)
        self.setSizePolicy(QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.Preferred)
        self.mode = mode
        self.show_points = show_points
        self.setContentsMargins(2, 2, 2, 2)
        self.setMinimumSize(68, 40)
        self.attack = 127
        self.attack_level = 127
        self.decay = 127
        self.sustain = 64
        self.decay2 = 127
        self.sustain2 = 64
        self.release = 64
        self.attack_point = None
        self.decay_point = None
        self.sustain_point = None
        self.decay2_point = None
        self.sustain2_point = None
        self.release_end = None
        self.envelope = None
        self.current_cursor = self.current_delta = self.hover_point = None
        self.font_metrics = QtGui.QFontMetrics(QtGui.QFont('Decorative', 10, QtGui.QFont.Bold))
        self.create_cursors()
        self.reset_envelope()
        self.env_rect = QtCore.QRectF(12, 4, self.width()-25, self.height()-9)

    def create_cursors(self):
        self.sustain_line = EnvelopeLine(self, 'Sustain', QtCore.Qt.SizeVerCursor)
        self.sustain_line.installEventFilter(self)
        self.attack_cursor = EnvelopePoint(self, 'Attack')
        self.attack_cursor.installEventFilter(self)
        self.decay_cursor = EnvelopePoint(self, 'Decay')
        self.decay_cursor.installEventFilter(self)
        self.decay2_cursor = EnvelopePoint(self, 'Decay2')
        self.decay2_cursor.installEventFilter(self)
        self.sustain_cursor = EnvelopePoint(self, 'Sustain', QtCore.Qt.SizeVerCursor)
        self.sustain_cursor.installEventFilter(self)
        self.release_cursor = EnvelopePoint(self, 'Release', QtCore.Qt.SizeHorCursor)
        self.release_cursor.installEventFilter(self)
        self.cursors = {
                        self.attack_cursor: self.coord_attack, 
                        self.decay_cursor: self.coord_decay, 
                        self.decay2_cursor: self.coord_decay2, 
                        self.sustain_line: self.coord_sustain2, 
                        self.sustain_cursor: self.coord_sustain2, 
                        self.release_cursor: self.coord_release, 
                        }

    def setEnvelope(self, mode):
        if mode == self.mode: return
        self.mode = mode
        self.reset_envelope()
        self.resizeEvent(None)
        self.update()
        self.envelopeChanged.emit(self.mode)

    def setValue(self, value_dict):
        for name, value in value_dict.items():
            getattr(self, 'set{}'.format(name.replace(' ', '')))(value)

    def setAttack(self, value):
        if value < 0:
            value = 0
        elif value > 127:
            value = 127
        self.attack = value
        self.compute_envelope()
        self.move_cursors()
        self.update()

    def setAttackLevel(self, value):
        if value < 0:
            value = 0
        elif value > 127:
            value = 127
        self.attack_level = value
        self.compute_envelope()
        self.move_cursors()
        self.update()

    def setDecay(self, value):
        if value < 0:
            value = 0
        elif value > 127:
            value = 127
        self.decay = value
        self.compute_envelope()
        self.move_cursors()
        self.update()

    def setSustain(self, value):
        if value < 0:
            value = 0
        elif value > 127:
            value = 127
        self.sustain = value
        self.compute_envelope()
        self.move_cursors()
        self.update()

    def setDecay2(self, value):
        if value < 0:
            value = 0
        elif value > 127:
            value = 127
        self.decay2 = value
        self.compute_envelope()
        self.move_cursors()
        self.update()

    def setSustain2(self, value):
        if value < 0:
            value = 0
        elif value > 127:
            value = 127
        self.sustain2 = value
        self.compute_envelope()
        self.move_cursors()
        self.update()

    def setRelease(self, value):
        if value < 0:
            value = 0
        elif value > 127:
            value = 127
        self.release = value
        self.compute_envelope()
        self.move_cursors()
        self.update()

    def reset_envelope(self):
        self.envelope = None
        self.cursor_labels = {}
        if self.mode == ADSR:
            self.compute_envelope = self.adsr_envelope_points
            self.create_envelope = self.adsr_envelope_path
            self.attack_range = self.release_range = 1./3
            self.decay_range = .8/3
            self.cursor_labels[self.attack_cursor] = 'attack', 'attack_level'
            self.cursor_labels[self.decay_cursor] = 'decay', 'sustain'
            self.cursor_labels[self.sustain_line] = 'sustain',
            self.cursor_labels[self.sustain_cursor] = 'sustain', 
            self.cursor_labels[self.release_cursor] = 'release', 
            self.cursors_update = {
                                   'attack': ['decay', 'sustain'], 
                                   'decay': ['sustain'], 
                                   'sustain': ['decay'], 
                                   'release': [], 
                                   }
            self.cursors.update({
                                 self.sustain_line: self.coord_sustain, 
                                 self.sustain_cursor: self.coord_sustain, 
                                 })
            self.sustain_cursor.show()
            self.sustain_line.show()
            self.decay2_cursor.hide()
        elif self.mode in [ADS1DS2R, LOOPS1S2, LOOPALL]:
            self.compute_envelope = self.ads1ds2r_envelope_points
            self.create_envelope = self.ads1ds2r_envelope_path
            self.attack_range = self.release_range = .25
            self.decay_range = .2
            self.cursor_labels[self.attack_cursor] = 'attack', 
            self.cursor_labels[self.decay_cursor] = 'decay', 'sustain'
            self.cursor_labels[self.decay2_cursor] = 'decay2', 'sustain2'
            self.cursor_labels[self.sustain_line] = 'sustain2',
            self.cursor_labels[self.sustain_cursor] = 'sustain2', 
            self.cursor_labels[self.release_cursor] = 'release', 
            self.cursors_update = {
                                   'attack': ['decay', 'decay2'], 
                                   'decay': ['decay2', 'sustain'], 
                                   'decay2': ['sustain'], 
                                   'sustain': ['decay2'], 
                                   'release': [], 
                                   }
            self.cursors.update({
                                 self.sustain_line: self.coord_sustain2, 
                                 self.sustain_cursor: self.coord_sustain2, 
                                 })
            self.sustain_cursor.show()
            self.sustain_line.show()
            self.decay2_cursor.show()
        else:
            self.compute_envelope = self.oneshot_envelope_points
            self.create_envelope = self.oneshot_envelope_path
            self.attack_range = self.release_range = self.decay_range = 1./4
            self.cursor_labels[self.attack_cursor] = 'attack', 
            self.cursor_labels[self.decay_cursor] = 'decay', 'sustain'
            self.cursor_labels[self.decay2_cursor] = 'decay2', 'sustain2'
#            self.cursor_labels[self.sustain_line] = 'sustain2',
#            self.cursor_labels[self.sustain_cursor] = 'sustain2', 
            self.cursor_labels[self.release_cursor] = 'release', 
            self.cursors_update = {
                                   'attack': ['decay', 'decay2', 'release'], 
                                   'decay': ['decay2', 'release'], 
                                   'decay2': ['sustain', 'release'], 
#                                   'sustain': ['decay2'], 
                                   'release': [], 
                                   }
            self.cursors.update({
                                 self.sustain_line: self.coord_sustain2, 
                                 self.sustain_cursor: self.coord_sustain2, 
                                 })
            self.sustain_cursor.hide()
            self.sustain_line.hide()
            self.decay2_cursor.show()
        if not self.show_points:
            for c in self.cursors.keys():
                c.hide()

    def setShowPoints(self, state):
        self.show_points = state
        if not state:
            for c in self.cursors.keys():
                c.hide()
            return
        if self.mode == ADSR:
            hide = [self.decay2_cursor]
        elif self.mode not in [ADS1DS2R, LOOPS1S2, LOOPALL]:
            hide = [self.sustain_cursor, self.sustain_line]
        else:
            hide = []
        for c in self.cursors.keys():
            c.setVisible(False if c in hide else True)


    def adsr_envelope_path(self):
        del self.envelope
        self.envelope = QtGui.QPainterPath()
        #attack
        self.envelope.lineTo(*self.attack_point)
        #decay
        self.envelope.quadTo(self.attack_point[0], self.decay_point[1], self.decay_point[0], self.decay_point[1])
        #sustain
        self.envelope.lineTo(*self.sustain_point)
        #release
        self.envelope.quadTo(self.sustain_point[0], 0, self.release_point[0], 0)
        self.envelope.lineTo(self.env_rect.x()+self.env_rect.width(), 0)

    def adsr_envelope_points(self):
        self.attack_point = self.env_rect.width()*self.attack_range*self.attack/127., -self.env_rect.height()
        self.sustain_point = self.env_rect.width()*2*self.attack_range, -self.env_rect.height()*self.sustain/127.
        self.decay_point = self.attack_point[0]+self.env_rect.width()*self.decay_range*self.decay/127., self.sustain_point[1]
        self.release_point = self.sustain_point[0]+self.env_rect.width()*self.release_range*self.release/127., 0
        self.create_envelope()

    def ads1ds2r_envelope_path(self):
        del self.envelope
        self.envelope = QtGui.QPainterPath()
        #attack
        self.envelope.lineTo(*self.attack_point)
        #decay
        self.envelope.quadTo(self.attack_point[0], self.decay_point[1], self.decay_point[0], self.decay_point[1])
        #decay2
        self.envelope.quadTo(self.decay_point[0], self.decay2_point[1], self.decay2_point[0], self.decay2_point[1])
        #sustain
        self.envelope.lineTo(*self.sustain_point)
        #release
        self.envelope.quadTo(self.sustain_point[0], 0, self.release_point[0], 0)
        self.envelope.lineTo(self.env_rect.x()+self.env_rect.width(), 0)

    def ads1ds2r_envelope_points(self):
        self.attack_point = self.env_rect.width()*self.attack_range*self.attack/127., -self.env_rect.height()*self.attack_level/127
        self.decay_point = self.attack_point[0]+self.env_rect.width()*self.decay_range*self.decay/127., -self.env_rect.height()*self.sustain/127.
        self.decay2_point = self.decay_point[0]+self.env_rect.width()*self.decay_range*self.decay2/127., -self.env_rect.height()*self.sustain2/127.
        self.sustain_point = self.env_rect.width()-self.env_rect.width()*self.attack_range, -self.env_rect.height()*self.sustain2/127.
        self.release_point = self.sustain_point[0]+self.env_rect.width()*self.release_range*self.release/127., 0
        self.create_envelope()

    def oneshot_envelope_points(self):
        self.attack_point = self.env_rect.width()*self.attack_range*self.attack/127., -self.env_rect.height()*self.attack_level/127
        self.decay_point = self.attack_point[0]+self.env_rect.width()*self.decay_range*self.decay/127., -self.env_rect.height()*self.sustain/127.
        self.decay2_point = self.decay_point[0]+self.env_rect.width()*self.decay_range*self.decay2/127., -self.env_rect.height()*self.sustain2/127.
#        self.sustain_point = self.env_rect.width()-self.env_rect.width()*self.attack_range, -self.env_rect.height()*self.sustain2/127.
        self.sustain_point = self.decay2_point[0], -self.env_rect.height()*self.sustain2/127.
        self.release_point = self.sustain_point[0]+self.env_rect.width()*self.release_range*self.release/127., 0
        self.create_envelope()

    def oneshot_envelope_path(self):
        del self.envelope
        self.envelope = QtGui.QPainterPath()
        #attack
        self.envelope.lineTo(*self.attack_point)
        #decay
        self.envelope.quadTo(self.attack_point[0], self.decay_point[1], self.decay_point[0], self.decay_point[1])
        #decay2
        self.envelope.quadTo(self.decay_point[0], self.decay2_point[1], self.decay2_point[0], self.decay2_point[1])
        #sustain
#        self.envelope.lineTo(*self.sustain_point)
        #release
        self.envelope.quadTo(self.sustain_point[0], 0, self.release_point[0], 0)
        self.envelope.lineTo(self.env_rect.x()+self.env_rect.width(), 0)



    def eventFilter(self, source, event):
        if source in self.cursors:
            if event.type() == QtCore.QEvent.MouseButtonPress and event.button() == QtCore.Qt.LeftButton:
                self.current_cursor = source
                self.current_delta = event.pos()
                return True
            elif event.type() == QtCore.QEvent.MouseMove and event.button() == QtCore.Qt.LeftButton:
                self.current_cursor = source
                self.current_delta = event.pos()
                source.setToolTip('\n'.join(['{}: {}'.format(var.capitalize().replace('_', ' '), getattr(self, var)) for var in self.cursor_labels[source]]))
                source.event(QtGui.QHelpEvent(QtCore.QEvent.ToolTip, QtCore.QPoint(20, 20), self.mapToGlobal(source.pos())+QtCore.QPoint(20, 0)))
                return True
            elif event.type() == QtCore.QEvent.MouseButtonRelease and event.button() == QtCore.Qt.LeftButton:
                self.current_cursor = self.current_delta = self.hover_point = None
                source.setToolTip('\n'.join(['{}: {}'.format(var.capitalize().replace('_', ' '), getattr(self, var)) for var in self.cursor_labels[source]]))
                source.event(QtGui.QHelpEvent(QtCore.QEvent.ToolTip, QtCore.QPoint(20, 20), self.mapToGlobal(source.pos())+QtCore.QPoint(20, 0)))
                QtGui.QApplication.changeOverrideCursor(source.cursor)
                self.repaint()
                return True
            elif event.type() == QtCore.QEvent.Enter:
                self.hover_point = source
                source.setToolTip('\n'.join(['{}: {}'.format(var.capitalize().replace('_', ' '), getattr(self, var)) for var in self.cursor_labels[source]]))
                source.event(QtGui.QHelpEvent(QtCore.QEvent.ToolTip, QtCore.QPoint(20, 20), self.mapToGlobal(source.pos())+QtCore.QPoint(20, 0)))
                QtGui.QApplication.setOverrideCursor(source.cursor)
            elif event.type() == QtCore.QEvent.Leave:
                QtGui.QApplication.restoreOverrideCursor()
#                self.repaint()
        return QtGui.QWidget.eventFilter(self, source, event)

    def mouseMoveEvent(self, event):
        if not self.current_cursor: return
        self.cursors[self.current_cursor](event.pos())
        self.current_cursor.setToolTip('\n'.join(['{}: {}'.format(var.capitalize().replace('_', ' '), getattr(self, var)) for var in self.cursor_labels[self.current_cursor]]))
        self.current_cursor.event(QtGui.QHelpEvent(QtCore.QEvent.ToolTip, QtCore.QPoint(0, 0), self.mapToGlobal(self.current_cursor.pos())+QtCore.QPoint(20, 0)))
        QtGui.QApplication.changeOverrideCursor(QtGui.QCursor(QtCore.Qt.BlankCursor))

    def coord_attack(self, pos):
        x = pos.x()-self.current_delta.x()
        y = pos.y()-self.current_delta.y()
        attack = int(round((x-self.env_rect.x()+4)*127/self.env_rect.width()/self.attack_range, 0))
        attack_level = 127-int(round((y-self.env_rect.y()+4)*127/(self.env_rect.height()-2), 0))
        if attack >= 127:
            attack = 127
        elif attack <= 0:
            attack = 0
        if attack != self.attack:
            self.attack = attack
            self.attackChanged.emit(attack)

        if attack_level >= 127:
            attack_level = 127
        elif attack_level <= 0:
            attack_level = 0
        if attack_level != self.attack_level:
            self.attack_level = attack_level
            self.attackLevelChanged.emit(attack_level)
        self.compute_envelope()
        self.move_cursors('attack')
        self.repaint()

    def coord_decay(self, pos):
        x = pos.x()-self.current_delta.x()
        y = pos.y()-self.current_delta.y()
        decay = int(round((x-self.attack_point[0]-self.env_rect.x()+4)*127/self.env_rect.width()/self.decay_range, 0))
        sustain = 127-int(round((y-self.env_rect.y()+4)*127/(self.env_rect.height()-2), 0))
        if decay >= 127:
            decay = 127
        elif decay <= 0:
            decay = 0
        if decay != self.decay:
            self.decay = decay
            self.decayChanged.emit(decay)
        if sustain >= 127:
            sustain = 127
        elif sustain <= 0:
            sustain = 0
        if sustain != self.sustain:
            self.sustain = sustain
            self.sustainChanged.emit(sustain)
        self.compute_envelope()
        self.move_cursors('decay')
        self.repaint()

    def coord_decay2(self, pos):
        x = pos.x()-self.current_delta.x()
        y = pos.y()-self.current_delta.y()
        decay2 = int(round((x-self.decay_point[0]-self.env_rect.x()+4)*127/self.env_rect.width()/self.decay_range, 0))
        sustain2 = 127-int(round((y-self.env_rect.y()+4)*127/(self.env_rect.height()-2), 0))
        if decay2 >= 127:
            decay2 = 127
        elif decay2 <= 0:
            decay2 = 0
        if decay2 != self.decay2:
            self.decay2 = decay2
            self.decay2Changed.emit(decay2)
        if sustain2 >= 127:
            sustain2 = 127
        elif sustain2 <= 0:
            sustain2 = 0
        if sustain2 != self.sustain2:
            self.sustain2 = sustain2
            self.sustain2Changed.emit(sustain2)
        self.compute_envelope()
        self.move_cursors('decay')
        self.repaint()

    def coord_sustain(self, pos):
        y = pos.y()-self.current_delta.y()
        sustain = 127-int(round((y-self.env_rect.y()+4)*127/(self.env_rect.height()-2), 0))
        if sustain >= 127:
            sustain = 127
        elif sustain <= 0:
            sustain = 0
        if sustain != self.sustain:
            self.sustain = sustain
            self.sustainChanged.emit(sustain)
        self.compute_envelope()
        self.move_cursors('sustain')
        self.repaint()

    def coord_sustain2(self, pos):
        y = pos.y()-self.current_delta.y()
        sustain2 = 127-int(round((y-self.env_rect.y()+4)*127/(self.env_rect.height()-2), 0))
        if sustain2 >= 127:
            sustain2 = 127
        elif sustain2 <= 0:
            sustain2 = 0
        if sustain2 != self.sustain2:
            self.sustain2 = sustain2
            self.sustain2Changed.emit(sustain2)
        self.compute_envelope()
        self.move_cursors('sustain')
        self.repaint()

    def coord_release(self, pos):
        x = pos.x()-self.current_delta.x()
        release = int(round((x-self.sustain_point[0]-self.env_rect.x()+4)*127/self.env_rect.width()/self.release_range, 0))
        if release >= 127:
            release = 127
        elif release <= 0:
            release = 0
        if release != self.release:
            self.release = release
            self.releaseChanged.emit(release)
        self.compute_envelope()
        self.move_cursors('release')
        self.repaint()

    def paintEvent(self, event):
        qp = QtGui.QPainter()
        qp.begin(self)
        qp.translate(.5, .5)
        qp.setRenderHints(QtGui.QPainter.Antialiasing)

        #debug rect
#        qp.setPen(QtCore.Qt.green)
#        qp.drawRect(0, 0, self.width()-1, self.height()-1)

        qp.setPen(self.border_pen)
        qp.drawRoundedRect(self.outer, 3, 3)
        qp.setPen(QtCore.Qt.NoPen)
        qp.setBrush(self.bgd_brush)
        qp.drawRoundedRect(self.display, 2, 2)

        qp.setPen(self.rel_line)
#        qp.drawRect(self.env_rect)

        #envelope
        qp.setPen(self.env_line)
        qp.drawLine(self.display.x(), self.env_rect.y()+self.env_rect.height(), self.env_rect.x(), self.env_rect.y()+self.env_rect.height())
        qp.drawLine(self.env_rect.x()+self.env_rect.width(), self.env_rect.y()+self.env_rect.height(), self.display.x()+self.display.width(), self.env_rect.y()+self.env_rect.height())

        qp.translate(self.env_rect.x(), self.env_rect.y()+self.env_rect.height())
        qp.setBrush(self.fgd_brush)
        qp.setPen(QtCore.Qt.NoPen)
        qp.drawPath(self.envelope)

        #reference lines
        qp.setPen(self.rel_line)
        qp.drawLine(self.attack_limit, 0, self.attack_limit, -self.env_rect.height())
        qp.drawLine(self.decay_limit, 0, self.decay_limit, -self.env_rect.height())
        qp.drawLine(self.sustain_point[0], 0, self.sustain_point[0], -self.env_rect.height())
        if self.decay2_limit:
            qp.drawLine(self.decay2_limit, 0, self.decay2_limit, -self.env_rect.height())
        if self.mode == LOOPALL:
            qp.save()
            qp.setPen(self.loop_line)
            qp.setBrush(QtCore.Qt.NoBrush)
            qp.drawRoundedRect(0, -10, self.release_point[0], -20, 10, 10)
            qp.translate(0, -20)
            qp.setPen(QtCore.Qt.NoPen)
            qp.setBrush(self.loop_limit_brush)
            qp.drawPolygon(self.loop_limit_left)
            qp.translate(self.release_point[0], 0)
            qp.drawPolygon(self.loop_limit_right)
            qp.restore()
        elif self.mode == LOOPS1S2:
            qp.save()
            qp.setPen(self.loop_line)
            qp.setBrush(QtCore.Qt.NoBrush)
            qp.drawRoundedRect(self.attack_point[0], -10, self.sustain_point[0]-self.attack_point[0], -20, 10, 10)
            qp.translate(self.attack_point[0], -20)
            qp.setPen(QtCore.Qt.NoPen)
            qp.setBrush(self.loop_limit_brush)
            qp.drawPolygon(self.loop_limit_left)
            qp.translate(self.sustain_point[0]-self.attack_point[0], 0)
            qp.drawPolygon(self.loop_limit_right)
            qp.restore()

        qp.setPen(self.env_line)
        qp.setBrush(QtCore.Qt.NoBrush)
        qp.drawPath(self.envelope)

        qp.end()

    def resizeEvent(self, event):
#        print self.height(), event.size().height()
        self.outer = QtCore.QRectF(0, 0, self.width()-1, self.height()-1)
        self.display = QtCore.QRectF(2, 2, self.width()-5, self.height()-5)
        self.env_rect = QtCore.QRectF(12, 4, self.width()-25, self.height()-9)

        self.attack_limit = self.env_rect.width()*self.attack_range
        self.compute_envelope()
        self.decay_limit = self.env_rect.width()*self.attack_range+self.env_rect.width()*self.decay_range
#        if self.decay2_point is not None:
        if self.mode in [ADS1DS2R, LOOPALL, LOOPS1S2]:
            self.decay2_limit = self.env_rect.width()*self.attack_range+self.env_rect.width()*2*self.decay_range
        else:
            self.decay2_limit = 0
#        self.sustain_limit = self.attack_limit+self.decay_limit+self.decay2_limit
        self.move_cursors()

    def move_cursors(self, point=None):
        if point:
            points = [point] + self.cursors_update[point]
        else:
            points = self.cursors_update.keys()
        x = self.env_rect.x()
        y = self.env_rect.y()+self.env_rect.height()
        for p in points:
            point = getattr(self, p+'_point')
            getattr(self, p+'_cursor').move(x+point[0], y+point[1])
            if p == 'sustain':
                if self.mode == ADSR:
                    decay_point = self.decay_point
                else:
                    decay_point = self.decay2_point
                self.sustain_line.resize(self.sustain_point[0]-decay_point[0], self.sustain_line.height())
                getattr(self, p+'_line').move(x+4+decay_point[0], y+self.sustain_point[1])
#                print self.sustain_line.update()
#            point.move(self.env_rect.x()+self.attack_point[0], self.env_rect.y()+self.env_rect.height()+self.attack_point[1])
            
#        print self.env_rect.height()+self.attack_point[1]
#        self.attack_cursor.move(self.env_rect.x()+self.attack_point[0], self.env_rect.y()+self.env_rect.height()+self.attack_point[1])
#        self.decay_cursor.move(self.env_rect.x()+self.decay_point[0], self.env_rect.y()+self.env_rect.height()+self.decay_point[1])
#        [x() for x in self.cursors]
#        s = set([v for k, v_setter in self.cursors_update.items() for v in v_setter])
#        [x() for x in s]


class ListView(QtGui.QListView):
    indexChanged = QtCore.pyqtSignal(int)
    def __init__(self, parent, item_list=None):
        QtGui.QListView.__init__(self, parent)
        self.main = parent
        self.setEditTriggers(QtGui.QListView.NoEditTriggers)
        self.setMouseTracking(True)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint|QtCore.Qt.Tool|QtCore.Qt.ToolTip)
        self.model = QtGui.QStandardItemModel()
        self.setModel(self.model)
        if item_list:
            self.add_items(item_list)
        self.adjust_size()
        self.clicked.connect(self.selected)
        self.activated.connect(self.selected)
        self.setSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Preferred)

    def showEvent(self, event):
        max_width = self.width()-self.viewport().width()+max([self.sizeHintForColumn(0)])
        min_width = self.main.width()
        self.setMaximumWidth(max_width if max_width > min_width else min_width)
        desktop = QtGui.QApplication.desktop().availableGeometry(self)
        geo = self.geometry()
        if not desktop.contains(geo, True):
            if geo.x() < desktop.x():
                x = desktop.x()
            elif geo.right() > desktop.right():
                x = desktop.right()-self.width()
            else:
                x = geo.x()
            if geo.y() < desktop.y():
                y = desktop.y()
            elif geo.bottom() > desktop.bottom():
                y = self.main.mapToGlobal(QtCore.QPoint(0, 0)).y()-self.height()
            else:
                y = geo.y()
            self.move(x, y)

    def add_items(self, item_list):
        for item in item_list:
            self.model.appendRow(QtGui.QStandardItem(item))
        self.adjust_size()

    def add_item(self, item):
        self.model.appendRow(QtGui.QStandardItem(item))
        self.adjust_size()

    def adjust_size(self):
#        max_width = self.width()-self.viewport().width()+max([self.sizeHintForColumn(0)])
#        min_width = self.main.width()
#        self.setMaximumWidth(max_width if max_width > min_width else min_width)
        if self.model.rowCount() > 0:
            self.setMaximumHeight(self.height()-self.viewport().height()+self.sizeHintForRow(0)*self.model.rowCount())

    def mouseMoveEvent(self, event):
        index = self.indexAt(event.pos())
        if index.row() < 0: return
        self.setCurrentIndex(index)

    def mouseReleaseEvent(self, event):
        self.selected(self.currentIndex())

    def focusOutEvent(self, event):
        self.hide()

    def selected(self, index):
        self.hide()
        self.indexChanged.emit(index.row())

    def resizeEvent(self, event):
        bmp = QtGui.QBitmap(self.width(), self.height())
        bmp.clear()
        qp = QtGui.QPainter(bmp)
        qp.setRenderHints(QtGui.QPainter.Antialiasing)
        qp.setPen(QtCore.Qt.black)
        qp.setBrush(QtCore.Qt.black)
        qp.drawRoundedRect(0, 0, self.width(), self.height(), 4, 4)
        qp.end()
        self.setMask(bmp)

#class NewCombo(QtGui.QComboBox):
#    _enabled_border_grad = QtGui.QConicalGradient(QtCore.QPointF(.5, .5), 45)
#    _enabled_border_grad.setCoordinateMode(QtGui.QConicalGradient.ObjectBoundingMode)
#    _enabled_border_grad.setColorAt(0, QtCore.Qt.darkGray)
#    _enabled_border_grad.setColorAt(.25, QtCore.Qt.darkGray)
#    _enabled_border_grad.setColorAt(.251, QtCore.Qt.gray)
#    _enabled_border_grad.setColorAt(.5, QtCore.Qt.gray)
#    _enabled_border_grad.setColorAt(.501, QtCore.Qt.white)
#    _enabled_border_grad.setColorAt(.75, QtCore.Qt.white)
#    _enabled_border_grad.setColorAt(.751, QtCore.Qt.lightGray)
#    _enabled_border_grad.setColorAt(.99, QtCore.Qt.lightGray)
#    _enabled_border_grad.setColorAt(1, QtCore.Qt.darkGray)
#    _disabled_border_grad = QtGui.QConicalGradient(QtCore.QPointF(.5, .5), 45)
#    _disabled_border_grad.setCoordinateMode(QtGui.QConicalGradient.ObjectBoundingMode)
#    for stop, color in _enabled_border_grad.stops():
#        _disabled_border_grad.setColorAt(stop, color.darker())
#    _enabled_border_pen = QtGui.QPen(_enabled_border_grad, 1)
#    _disabled_border_pen = QtGui.QPen(_disabled_border_grad, 1)
#    _border_pens = _disabled_border_pen, _enabled_border_pen
#    border_pen = _border_pens[1]
#    arrow_grad = QtGui.QConicalGradient(QtCore.QPointF(.5, .5), -90)
#    arrow_grad.setCoordinateMode(QtGui.QConicalGradient.ObjectBoundingMode)
#    arrow_grad.setColorAt(0, QtCore.Qt.white)
#    arrow_grad.setColorAt(.3125, QtCore.Qt.white)
#    arrow_grad.setColorAt(.413, QtCore.Qt.darkGray)
#    arrow_grad.setColorAt(.6875, QtCore.Qt.darkGray)
#    arrow_grad.setColorAt(.688, QtCore.Qt.gray)
#    arrow_grad.setColorAt(.99, QtCore.Qt.gray)
#    arrow_grad.setColorAt(1, QtCore.Qt.white)
#    arrow_border = QtGui.QPen(arrow_grad, 1)
#    arrow_color = QtGui.QColor(180, 180, 180)
#    arrow = QtGui.QPainterPath()
#    arrow.lineTo(8, 0)
#    arrow.lineTo(4, 4)
#    arrow.closeSubpath()
#    arrow_size = 12
#    combo_rect = QtCore.QRectF(0, 0, 1, 1)
#    combo_text_rect = QtCore.QRectF(0, 0, 1, 1)
#    label_rect = None
#    font = QtGui.QFont('Decorative', 10, QtGui.QFont.Bold)
#    label_font = QtGui.QFont('Decorative', 9, QtGui.QFont.Bold)
#    _label_pen_enabled = QtGui.QPen(QtCore.Qt.white)
#    _label_pen_disabled = QtGui.QPen(QtCore.Qt.darkGray)
#    _label_pen_colors = _label_pen_disabled, _label_pen_enabled
#    label_pen = _label_pen_colors[1]
#    def __init__(self, parent=None, value_list=None, name='', wheel_dir=True, default=0):
#        QtGui.QComboBox.__init__(self, parent)
#        self.combo_padding = 2
#        self.spacing = 4
#        self.label_font_metrics = QtGui.QFontMetrics(QtGui.QFont('Decorative', 9, QtGui.QFont.Bold))
#        self.font_metrics = QtGui.QFontMetrics(QtGui.QFont('Decorative', 10, QtGui.QFont.Bold))
##        self.list = ListView(self)
#        if name:
#            self.name = name
#            self.setMinimumSize(10, self.font_metrics.height()+self.label_font_metrics.height()+self.spacing+self.combo_padding*2)
#            self.setMaximumHeight(self.font_metrics.height()+self.label_font_metrics.height()+self.spacing+self.combo_padding*2)
#        else:
#            self.name = None
#            self.setMinimumSize(10, self.font_metrics.height()+self.combo_padding*2)
#            self.setMaximumHeight(self.font_metrics.height()+self.combo_padding*2)
#        self.setSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Fixed)
#        if value_list:
#            self.add_items(value_list)
#            if not 0 <= default <= len(value_list):
#                default = 0
#        else:
#            self.current = 'None'
#        self.setCurrentIndex(default)
#        pal = self.palette()
#        pal.setColor(self.backgroundRole(), QtGui.QColor(QtCore.Qt.gray))
##        pal.setColor(self.foregroundRole(), QtGui.QColor(QtCore.Qt.red))
#        self.setPalette(pal)
#
#    @property
#    def value(self):
#        return self.currentIndex()
#
#    @property
#    def text_value(self):
#        return self.currentText()
#
#
#    def add_items(self, value_list):
#        for item in value_list:
#            self.addItem(item)
#        max_length = max([self.font_metrics.width(txt)+self.combo_padding*2 for txt in value_list]+[self.label_font_metrics.width(self.name) if self.name else 0])
#        self.setMinimumWidth(max_length+self.arrow_size)
#        self.current = value_list[0]
##        self.list.setMinimumWidth(self.minimumWidth())
#
#    def paintEvent(self, e):
#        qp = QtGui.QPainter()
#        qp.begin(self)
#        qp.translate(.5, .5)
#        qp.setRenderHints(QtGui.QPainter.Antialiasing)
#        qp.setPen(self.border_pen)
#        qp.drawRoundedRect(self.combo_rect, 2, 2)
#
#        qp.setFont(self.font)
#        qp.setPen(self.label_pen)
#        qp.drawText(self.combo_text_rect, QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter, self.current)
#
#        if self.label_rect:
#            qp.setFont(self.label_font)
#            qp.drawText(self.label_rect, QtCore.Qt.AlignHCenter|QtCore.Qt.AlignVCenter, self.name)
#
#        qp.translate(self.width()-self.arrow_size, self.combo_rect.height()/2-2)
#        qp.setPen(self.arrow_border)
#        qp.setBrush(self.arrow_color)
#        qp.drawPath(self.arrow)
#
#        qp.end()
#
#    def resizeEvent(self, event):
#        if not self.name:
#            self.combo_rect = QtCore.QRect(0, 0, self.width()-1, self.height()-1)
#        else:
#            self.combo_rect = QtCore.QRect(0, 0, self.width()-1, self.font_metrics.height()+self.combo_padding*2)
#            self.label_rect = QtCore.QRect(0, self.combo_rect.height()+self.spacing, self.width()-1, self.font_metrics.height())
#        self.combo_text_rect = QtCore.QRect(self.combo_rect.x()+self.combo_padding, 1, self.width()-self.combo_padding-self.arrow_size, self.combo_rect.height())

class Combo(QtGui.QWidget):
    _enabled_border_grad = QtGui.QConicalGradient(QtCore.QPointF(.5, .5), 45)
    _enabled_border_grad.setCoordinateMode(QtGui.QConicalGradient.ObjectBoundingMode)
    _enabled_border_grad.setColorAt(0, QtCore.Qt.darkGray)
    _enabled_border_grad.setColorAt(.25, QtCore.Qt.darkGray)
    _enabled_border_grad.setColorAt(.251, QtCore.Qt.gray)
    _enabled_border_grad.setColorAt(.5, QtCore.Qt.gray)
    _enabled_border_grad.setColorAt(.501, QtCore.Qt.white)
    _enabled_border_grad.setColorAt(.75, QtCore.Qt.white)
    _enabled_border_grad.setColorAt(.751, QtCore.Qt.lightGray)
    _enabled_border_grad.setColorAt(.99, QtCore.Qt.lightGray)
    _enabled_border_grad.setColorAt(1, QtCore.Qt.darkGray)
    _disabled_border_grad = QtGui.QConicalGradient(QtCore.QPointF(.5, .5), 45)
    _disabled_border_grad.setCoordinateMode(QtGui.QConicalGradient.ObjectBoundingMode)
    for stop, color in _enabled_border_grad.stops():
        _disabled_border_grad.setColorAt(stop, color.darker())
    _enabled_border_pen = QtGui.QPen(_enabled_border_grad, 1)
    _disabled_border_pen = QtGui.QPen(_disabled_border_grad, 1)
    _border_pens = _disabled_border_pen, _enabled_border_pen
    border_pen = _border_pens[1]
    arrow_grad = QtGui.QConicalGradient(QtCore.QPointF(.5, .5), -90)
    arrow_grad.setCoordinateMode(QtGui.QConicalGradient.ObjectBoundingMode)
    arrow_grad.setColorAt(0, QtCore.Qt.white)
    arrow_grad.setColorAt(.3125, QtCore.Qt.white)
    arrow_grad.setColorAt(.413, QtCore.Qt.darkGray)
    arrow_grad.setColorAt(.6875, QtCore.Qt.darkGray)
    arrow_grad.setColorAt(.688, QtCore.Qt.gray)
    arrow_grad.setColorAt(.99, QtCore.Qt.gray)
    arrow_grad.setColorAt(1, QtCore.Qt.white)
    arrow_border = QtGui.QPen(arrow_grad, 1)
    arrow_color = QtGui.QColor(180, 180, 180)
    arrow = QtGui.QPainterPath()
    arrow.lineTo(8, 0)
    arrow.lineTo(4, 4)
    arrow.closeSubpath()
    arrow_size = 12
    combo_rect = QtCore.QRectF(0, 0, 1, 1)
    combo_text_rect = QtCore.QRectF(0, 0, 1, 1)
    label_rect = None
    font = QtGui.QFont('Decorative', 10, QtGui.QFont.Bold)
    label_font = QtGui.QFont('Decorative', 9, QtGui.QFont.Bold)
    _label_pen_enabled = QtGui.QPen(QtCore.Qt.white)
    _label_pen_disabled = QtGui.QPen(QtCore.Qt.darkGray)
    _label_pen_colors = _label_pen_disabled, _label_pen_enabled
    label_pen = _label_pen_colors[1]
    indexChanged = QtCore.pyqtSignal(int)
    def __init__(self, parent=None, value_list=None, name='', wheel_dir=True, default=0):
        QtGui.QWidget.__init__(self, parent)
        self.combo_padding = 2
        self.spacing = 4
        self.label_font_metrics = QtGui.QFontMetrics(QtGui.QFont('Decorative', 9, QtGui.QFont.Bold))
        self.font_metrics = QtGui.QFontMetrics(QtGui.QFont('Decorative', 10, QtGui.QFont.Bold))
        self.list = ListView(self)
        self.setFocusPolicy(QtCore.Qt.WheelFocus)
        self.list.indexChanged.connect(self.setCurrentIndex)
        if name:
            self.name = name
            self.setMinimumSize(10, self.font_metrics.height()+self.label_font_metrics.height()+self.spacing+self.combo_padding*2)
            self.setMaximumHeight(self.font_metrics.height()+self.label_font_metrics.height()+self.spacing+self.combo_padding*2)
        else:
            self.name = None
            self.setMinimumSize(10, self.font_metrics.height()+self.combo_padding*2)
            self.setMaximumHeight(self.font_metrics.height()+self.combo_padding*2)
        self.setSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Fixed)
        self.value_list = []
        self.wheel_dir = 1 if wheel_dir else -1
        if value_list:
            self.add_items(value_list)
            if not 0 <= default <= len(value_list):
                default = 0
            self.currentIndex = default
            self._setValue(default)
        else:
            self.current = 'None'
            self.currentIndex = -1

    @property
    def value(self):
        return self.currentIndex

    @property
    def count(self):
        return len(self.value_list)

    @property
    def text_value(self):
        return self.value_list[self.currentIndex]

    def focusOutEvent(self, event):
        if self.list.isVisible():
            self.list.hide()

    def changeEvent(self, event):
        if not event.type() == QtCore.QEvent.EnabledChange: return
        state = self.isEnabled()
        self.label_pen = self._label_pen_colors[state]
        self.border_pen = self._border_pens[state]
        self.update()

    def event(self, event):
        if event.type() == QtCore.QEvent.ToolTip and self.combo_rect.contains(event.pos()):
            QtGui.QToolTip.showText(event.globalPos(), self.current, self, self.combo_rect)
        return QtGui.QWidget.event(self, event)

    def _setValue(self, id):
        self.currentIndex = id
        self.current = self.value_list[id]
        self.update()

    def setCurrentIndex(self, id):
        self._setValue(id)
        self.indexChanged.emit(id)
        self.update()

    def paintEvent(self, e):
        qp = QtGui.QPainter()
        qp.begin(self)
        qp.translate(.5, .5)
        qp.setRenderHints(QtGui.QPainter.Antialiasing)
        qp.setPen(self.border_pen)
#        qp.drawRoundedRect(0, 0, self.width()-1, self.height()-1, 2, 2)
        qp.drawRoundedRect(self.combo_rect, 2, 2)

        qp.setFont(self.font)
        qp.setPen(self.label_pen)
#        qp.drawText(self.combo_padding, 0, self.width()-self.combo_padding, self.height(), QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter, self.current)
        qp.drawText(self.combo_text_rect, QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter, self.current)

        if self.label_rect:
            qp.setFont(self.label_font)
            qp.drawText(self.label_rect, QtCore.Qt.AlignHCenter|QtCore.Qt.AlignVCenter, self.name)

        qp.translate(self.width()-self.arrow_size, self.combo_rect.height()/2-2)
        qp.setPen(self.arrow_border)
        qp.setBrush(self.arrow_color)
        qp.drawPath(self.arrow)

        qp.end()

    def mousePressEvent(self, event):
        if not self.combo_rect.contains(event.pos()): return
        if event.button() == QtCore.Qt.LeftButton:
            if not self.list.isVisible():
                self.show_list()
            else:
                self.list.hide()

    def wheelEvent(self, event):
        if self.list.isVisible():
            self.list.hide()
        index = self.currentIndex - self.wheel_dir if event.delta() > 1 else self.currentIndex + self.wheel_dir
        if index < 0:
            index = 0
        if index >= len(self.value_list):
            index = len(self.value_list) - 1
        self.setCurrentIndex(index)

    def show_list(self):
        if not self.value_list: return
        pos = self.mapToGlobal(QtCore.QPoint(0, 0))
        self.list.move(pos.x(), pos.y()+self.combo_rect.height())
        self.list.show()
        self.list.setFocus(QtCore.Qt.ActiveWindowFocusReason)
        self.list.setCurrentIndex(self.list.model.index(self.currentIndex, 0))

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self.list.hide()
        if self.list.isVisible():
            self.list.keyPressEvent(event)


    def add_items(self, value_list):
        for item in value_list:
            self.add_item(item)
        max_length = max([self.font_metrics.width(txt)+self.combo_padding*2 for txt in self.value_list]+[self.label_font_metrics.width(self.name) if self.name else 0])
        self.setMinimumWidth(max_length+self.arrow_size)
        self.current = value_list[0]
        self.list.setMinimumWidth(self.minimumWidth())
        self.list.add_items(value_list)

    def add_item(self, item):
        self.value_list.append(item)

    def resizeEvent(self, event):
        if not self.name:
            self.combo_rect = QtCore.QRect(0, 0, self.width()-1, self.height()-1)
        else:
            self.combo_rect = QtCore.QRect(0, 0, self.width()-1, self.font_metrics.height()+self.combo_padding*2)
            self.label_rect = QtCore.QRect(0, self.combo_rect.height()+self.spacing, self.width()-1, self.font_metrics.height())
        self.combo_text_rect = QtCore.QRect(self.combo_rect.x()+self.combo_padding, 1, self.width()-self.combo_padding-self.arrow_size, self.combo_rect.height())
        


class GhostCursor(QtGui.QWidget):
    def __init__(self, parent, width, height=None):
        QtGui.QWidget.__init__(self, parent)
        self.setMinimumSize(2, 2)
        if width < self.minimumWidth():
            width = self.minimumWidth()
        if height is None:
            height = width
        else:
            if height < self.minimumHeight():
                height = self.minimumHeight()
        self.setFixedSize(width, height)

#    def paintEvent(self, e):
#        qp = QtGui.QPainter()
#        qp.begin(self)
#        qp.setBrush(QtCore.Qt.white)
#        qp.drawRect(0, 0, self.width(), self.height())
#        qp.end()
#
    def move(self, x, y):
#        print x, y
        QtGui.QWidget.move(self, x-self.width()/2, y-self.height()/2)


class Cursor(QtGui.QWidget):
    _fill_grad_disabled = QtGui.QRadialGradient(5, 5, 5)
    _fill_grad_disabled.setColorAt(0, QtGui.QColor(115, 115, 115))
    _fill_grad_disabled.setColorAt(1, QtGui.QColor(90, 90, 90))
    _fill_grad_enabled = QtGui.QRadialGradient(5, 5, 5)
    _fill_grad_enabled.setColorAt(0, QtGui.QColor(180, 180, 180))
    _fill_grad_enabled.setColorAt(1, QtGui.QColor(150, 150, 150))
    _fill_grad_colors = _fill_grad_disabled, _fill_grad_enabled
    fill_grad = _fill_grad_colors[1]
    _border_grad_disabled = QtGui.QRadialGradient(35, 35, 35)
    _border_grad_disabled.setColorAt(0, QtGui.QColor(127, 127, 127))
    _border_grad_disabled.setColorAt(0.5, QtGui.QColor(127, 127, 127))
    _border_grad_disabled.setColorAt(1, QtGui.QColor(80, 80, 80))
    _border_grad_enabled = QtGui.QRadialGradient(35, 35, 35)
    _border_grad_enabled.setColorAt(0, QtCore.Qt.white)
    _border_grad_enabled.setColorAt(0.5, QtCore.Qt.white)
    _border_grad_enabled.setColorAt(1, QtCore.Qt.gray)
    _border_grad_colors = _border_grad_disabled, _border_grad_enabled
    border_grad = _border_grad_colors[1]

    def __init__(self, parent, size):
        QtGui.QWidget.__init__(self, parent)
        self.setMinimumSize(2, 2)
        if size < self.minimumWidth():
            size = self.minimumWidth()
        self.setFixedSize(size, size)
#        self.fill_grad = self.fill_grad_colors[1]
#        self.border_grad = self.border_grad_colors[1]

    def setEnabled(self, state):
        self.fill_grad = self._fill_grad_colors[state]
        self.border_grad = self._border_grad_colors[state]
        QtGui.QWidget.setEnabled(self, state)

    def paintEvent(self, e):
        qp = QtGui.QPainter()
        qp.begin(self)
        qp.setRenderHints(QtGui.QPainter.Antialiasing)
        qp.setPen(QtGui.QPen(self.border_grad, self.width()/30.))
        qp.setBrush(self.fill_grad)
        qp.drawEllipse(1, 1, self.width()-1, self.width()-1)
        qp.end()

    def move(self, x, y):
        QtGui.QWidget.move(self, x-self.width()/2, y-self.width()/2)

    def resizeEvent(self, event):
        for s in range(2):
            self._fill_grad_colors[s].setCenter(self.width()/2., self.width()/2.)
            self._fill_grad_colors[s].setRadius(self.width())
            self._fill_grad_colors[s].setFocalPoint(self.width(), self.width())
            self._border_grad_colors[s].setCenter(self.width(), self.width())
            self._border_grad_colors[s].setRadius(self.width())
            self._border_grad_colors[s].setFocalPoint(self.width(), self.width())


class Dial(QtGui.QWidget):
    _start_color_disabled = QtGui.QColor(0, 128, 0)
    _start_color_enabled = QtGui.QColor(QtCore.Qt.green)
    _start_colors = [_start_color_disabled, _start_color_enabled]
    start_color = _start_colors[1]
    _end_color_disabled = QtGui.QColor(127, 44, 0)
    _end_color_enabled = QtGui.QColor(255, 89, 0)
    _end_colors = [_end_color_disabled, _end_color_enabled]
    end_color = _end_colors[1]
    _dial_bgd_disabled = QtGui.QRadialGradient(35, 35, 35)
    _dial_bgd_disabled.setColorAt(0, QtGui.QColor(96, 96, 96))
    _dial_bgd_disabled.setColorAt(1, QtGui.QColor(127, 127, 127))
    _dial_bgd_enabled = QtGui.QRadialGradient(35, 35, 35)
    _dial_bgd_enabled.setColorAt(0, QtCore.Qt.lightGray)
    _dial_bgd_enabled.setColorAt(1, QtCore.Qt.white)
    _dial_bgd_colors = [_dial_bgd_disabled, _dial_bgd_enabled]
    dial_bgd = _dial_bgd_colors[1]
    _dial_border_disabled = QtGui.QRadialGradient(35, 35, 35)
    _dial_border_disabled.setColorAt(0, QtCore.Qt.black)
    _dial_border_disabled.setColorAt(1, QtGui.QColor(127, 127, 127))
    _dial_border_enabled = QtGui.QRadialGradient(35, 35, 35)
    _dial_border_enabled.setColorAt(0, QtCore.Qt.black)
    _dial_border_enabled.setColorAt(1, QtCore.Qt.white)
    _dial_border_colors = _dial_border_disabled, _dial_border_enabled
    dial_border = _dial_border_colors[1]

    _fgd_disabled = QtGui.QColor(127, 127, 127)
    _fgd_enabled = QtCore.Qt.white
    _fgd_colors = [_fgd_disabled, _fgd_enabled]
    fgd_color = _fgd_colors[1]
    fgd_pen = QtGui.QPen(fgd_color, 1)
    cursor_pen = QtGui.QPen(fgd_color, 1)
    _dial_disabled = QtGui.QColor(80, 80, 80)
    _dial_enabled = QtCore.Qt.gray
    _dial_colors = [_dial_bgd_disabled, _dial_enabled]
    dial_color = _dial_colors[1]
    dial_pen = QtGui.QPen(dial_color, 1)
    
    _range_full_grad_disabled = QtGui.QConicalGradient(QtCore.QPointF(.5, .5), 240)
    _range_full_grad_disabled.setColorAt(0, _start_color_disabled)
    _range_full_grad_disabled.setColorAt(.83, _end_color_disabled)
    _range_full_grad_disabled.setColorAt(.99, _end_color_disabled)
    _range_full_grad_enabled = QtGui.QConicalGradient(QtCore.QPointF(.5, .5), -60)
    _range_full_grad_enabled.setColorAt(0, _end_color_enabled)
    _range_full_grad_enabled.setColorAt(.83, _start_color_enabled)
    _range_full_grad_enabled.setColorAt(.99, _start_color_enabled)
    range_full_colors = _range_full_grad_disabled, _range_full_grad_enabled

    _range_mid_grad_disabled = QtGui.QConicalGradient(QtCore.QPointF(0, 0), 90)
    _range_mid_grad_disabled.setColorAt(0, _start_color_disabled)
    _range_mid_grad_disabled.setColorAt(.4, _end_color_disabled)
    _range_mid_grad_disabled.setColorAt(.6, _end_color_disabled)
    _range_mid_grad_disabled.setColorAt(1, _start_color_disabled)
    _range_mid_grad_enabled = QtGui.QConicalGradient(QtCore.QPointF(0, 0), 90)
    _range_mid_grad_enabled.setColorAt(0, _start_color_enabled)
    _range_mid_grad_enabled.setColorAt(.4, _end_color_enabled)
    _range_mid_grad_enabled.setColorAt(.6, _end_color_enabled)
    _range_mid_grad_enabled.setColorAt(1, _start_color_enabled)
    range_mid_colors = _range_mid_grad_disabled, _range_mid_grad_enabled

    valueChanged = QtCore.pyqtSignal(int)

    def __init__(self, parent, full_range=None, min_value=0, max_value=127, step=1, value=None, default=None, name='', center=False, show_bar=True, value_list=None, scale=True, gradient=False, size=None, min_size=None, max_size=None):
        QtGui.QWidget.__init__(self, parent)
        self.setMouseTracking(True)
        self.value_font = QtGui.QFont('Decorative', 10, QtGui.QFont.Bold)
        self.value_font_metrics = QtGui.QFontMetrics(self.value_font)
        self.label_font = QtGui.QFont('Decorative', 9, QtGui.QFont.Bold)
        self.label_font_metrics = QtGui.QFontMetrics(self.label_font)
        self.setMinimumSize(QtGui.QFontMetrics(self.label_font).width(name), 46)
        self.setFocusPolicy(QtCore.Qt.WheelFocus)
        self._size = QtCore.QSize(40, 40)
        sp = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Minimum)
#        sp.setHeightForWidth(True)
        self.setSizePolicy(sp)

        if full_range:
            self.min_value, self.max_value, self.step = full_range
        else:
            self.min_value = min_value
            self.max_value = max_value
            self.step = step
        self.range_list = [n for n in range(self.min_value, self.max_value+1, self.step)]
        self.range = self.max_value-self.min_value
        self.default_value = default
        if value is not None and self.min_value <= value <= self.max_value:
            self.value = value
        elif default is not None:
            self.value = default
        else:
            self.value = self.min_value
#        self.value = value if value is not None and self.min_value<=value<=self.max_value else self.min_value
        self.dial_size = 1
        self.center = center
        self.show_bar = show_bar
        self.value_list = [QtCore.QString.fromUtf8(s) for s in value_list]
        self.name = name
        self.scale = self.range/self.step if self.range/self.step <= 50 and scale else None
        self.cursor_mode = False
        if not size:
            self.min_size = min_size
            self.max_size = max_size
        else:
            self.min_size = self.max_size = size

        self.translate = 0, 0
        self.default = 240 if not center else 90
        self.radius = 1
        self.x_line = 0.5
        self.y_line = sin(pi/3.)
        self.in_radius = self.in_ratio = 0.8
        self.cursor_ratio = self.in_ratio*0.6
        self.cursor_size = 0.4
        self.gradient = gradient
        if self.gradient:
            self.fill_color = self.range_mid_colors[1] if self.center else self.range_full_colors[1]
        else:
            self.fill_color = QtGui.QColor(*self.setColor())
        self.dial_ratio = 0.85
        self.cursor = Cursor(self, self.radius*self.cursor_ratio)
        self.cursor.installEventFilter(self)
        self.ghost = GhostCursor(self, self.radius*(1-self.in_ratio))
        self.ghost.installEventFilter(self)
        self.installEventFilter(self)
        self.setValue(self.value)

    def heightForWidth(self, width):
        return width+20

    @property
    def abs_value(self):
        if self.range&1:
            if self.value > self.min_value+self.range/2:
                delta = 1
            else:
                delta = 0
            return 1./(self.range-1 if delta else self.range+1)*(self.value-self.min_value-delta)
        else:
            return 1./(self.range)*(self.value-self.min_value)

    @property
    def comp_value(self):
        return 300*self.abs_value

    @property
    def text_value(self):
        if not self.value_list:
            return self.value
        return self.value_list[(self.value-self.min_value)/self.step]

#    def setEnabled(self, state):
#        QtGui.QWidget.setEnabled(self, state)

    def changeEvent(self, event):
        if not event.type() == QtCore.QEvent.EnabledChange: return
        state = self.isEnabled()
        self.start_color = self._start_colors[state]
        self.end_color = self._end_colors[state]
        self.dial_bgd = self._dial_bgd_colors[state]
        self.dial_border = self._dial_border_colors[state]
        if self.gradient:
            self.fill_color = self.range_mid_colors[state] if self.center else self.range_full_colors[state]
        else:
            self.fill_color = QtGui.QColor(*self.setColor())
        self.fgd_color = self._fgd_colors[state]
        self.fgd_pen = QtGui.QPen(self.fgd_color, self.dial_size/50.)
        self.cursor_pen = QtGui.QPen(self.fgd_color, self.dial_size/30.)
        self.dial_color = self._dial_colors[state]
        self.dial_pen = QtGui.QPen(self.dial_color, self.dial_size/100.)
        self.update()
        self.cursor.setEnabled(state)

    def setColor(self):
        red_start, green_start, blue_start, _ = self.start_color.getRgb()
        red_end, green_end, blue_end, _ = self.end_color.getRgb()
        if not self.center:
            red_ratio = red_start+self.abs_value*(red_end-red_start)
            green_ratio = green_start+self.abs_value*(green_end-green_start)
            blue_ratio = blue_start+self.abs_value*(blue_end-blue_start)
        else:
#            ratio = self.min_value+self.range/(self.value-self.min_value)
            red_ratio = red_start+abs(self.abs_value-.5)*(red_end-red_start)*2
            green_ratio = green_start+abs(self.abs_value-.5)*(green_end-green_start)*2
            blue_ratio = blue_start+abs(self.abs_value-.5)*(blue_end-blue_start)*2
        return red_ratio, green_ratio, blue_ratio

    def paintEvent(self, e):
        qp = QtGui.QPainter()
        qp.begin(self)
        self.drawWidget(qp)
        qp.end()

    def drawWidget(self, qp):
        #debug rect
#        qp.setPen(QtCore.Qt.white)
#        qp.drawRect(self.rect().x(), self.rect().y(), self.rect().width()-1, self.rect().height()-1)

#        qp.setRenderHints(QtGui.QPainter.Antialiasing|QtGui.QPainter.TextAntialiasing|QtGui.QPainter.SmoothPixmapTransform)
        qp.setRenderHints(QtGui.QPainter.Antialiasing)
        qp.save()
        qp.translate(*self.translate)

        #draw dial
        qp.setBrush(self.dial_bgd)
        qp.setPen(QtGui.QPen(self.dial_border, self.dial_size/60.))
        qp.drawEllipse(self.dial_rect)

        #draw range arcs
        qp.setBrush(self.fill_color)
        qp.setPen(self.dial_pen)
        qp.drawArc(1, 1, self.dial_size-2, self.dial_size-2, -960, 4800)
        qp.drawLine(self.radius-self.radius*self.x_line+1, self.radius+self.radius*self.y_line, 
                    self.radius-self.in_radius*self.x_line, self.radius+self.in_radius*self.y_line)
        qp.drawLine(self.radius+self.radius*self.x_line, self.radius+self.radius*self.y_line, 
                    self.radius+self.in_radius*self.x_line, self.radius+self.in_radius*self.y_line)
        if self.center:
            qp.drawLine(self.radius, 0, 
                        self.radius, self.radius-self.in_radius)
        if self.scale is not None:
            qp.save()
            qp.setPen(self.fgd_pen)
            l_diff = (self.radius - self.in_radius) / 4
            l_pos = self.in_radius + l_diff
            l_len = l_pos+l_diff
            qp.translate(self.radius, self.radius)
            qp.rotate(120)
            if self.scale&1:
                ratio = 150./(self.scale/2+1)
                for i in range(self.min_value+self.step, self.scale/2+2*self.step, self.step):
                    qp.rotate(ratio)
                    qp.drawLine(l_pos, 0, l_len, 0)
                ratio = 150./(self.scale/2)
                for i in range(self.scale/2+2*self.step, self.max_value, self.step):
                    qp.rotate(ratio)
                    qp.drawLine(l_pos, 0, l_len, 0)
            else:
                ratio = 300./self.scale
                for i in range(self.min_value, self.max_value-self.step, self.step):
                    qp.rotate(ratio)
                    qp.drawLine(l_pos, 0, l_len, 0)
            qp.restore()

        #draw value arc
        if self.show_bar:
            path = QtGui.QPainterPath()
            path.moveTo(self.radius+self.radius*cos(radians(self.default)), self.radius-self.radius*sin(radians(self.default)))
            path.arcTo(.5, .5, self.dial_size-1, self.dial_size-1, self.default, (150 if self.center else 0)-self.comp_value)
    #        path.lineTo(self.radius+self.in_radius*self.x_line, self.radius+self.in_radius*self.y_line)
            path.arcTo(self.in_source, self.in_source, self.in_radius*2, self.in_radius*2, self.default-self.comp_value+(150 if self.center else 0), (self.comp_value-150 if self.center else self.comp_value))
            path.closeSubpath()
            qp.drawPath(path)

        #draw cursor bar
        qp.setPen(self.cursor_pen)
        cursor_angle = radians(240-self.comp_value)
        qp.drawLine(self.radius+self.radius*cos(cursor_angle), self.radius-self.radius*sin(cursor_angle), 
                    self.radius+self.in_radius*cos(cursor_angle), self.radius-self.in_radius*sin(cursor_angle))
#        print self.radius+self.radius*sin(cursor_angle), self.radius+self.in_radius*cos(cursor_angle)

        if self.value_rect:
            qp.setPen(QtGui.QPen(self.fill_color))
            qp.setFont(self.value_font)
            x, y, w, h = self.value_rect
            qp.drawText(x, y, w, h, QtCore.Qt.AlignCenter, '{}'.format(self.text_value))

        qp.restore()
        if self.name:
            qp.setPen(self.fgd_color)
            qp.setFont(self.label_font)
#            qp.drawRect(0, self.translate[1]+2+self.dial_size, self.width(), 2+self.label_font.pointSize())
            qp.drawText(0, self.translate[1]+2+self.dial_size, self.width(), 2+self.label_font_metrics.height(), QtCore.Qt.AlignCenter, self.name)


    def resizeEvent(self, event):
#        self.resize(event.size())
#        self._size.scale(event.size(), QtCore.Qt.KeepAspectRatio)
#        print self.label_font.pointSize()
#        self.resize(self._size.width(), self._size.height()+10)
#        self.resize(event.size().width(), event.size().height()+self.label_font.pointSize())
        self.dial_size = min([self.width(), self.height()-self.label_font_metrics.height()])-self.label_font_metrics.height()
        if self.min_size and self.dial_size < self.min_size:
            self.dial_size = self.min_size
        elif self.max_size and self.dial_size > self.max_size:
            self.dial_size = self.max_size
        self.translate = (self.width()-self.dial_size)/2., (self.height()-self.dial_size-self.label_font_metrics.height())/2.
        self.radius = (self.dial_size)/2.
        self.in_radius = self.radius*self.in_ratio
        self.in_source = self.radius-self.radius*self.in_ratio
        dial_radius = self.in_radius*self.dial_ratio
        self.dial_rect = QtCore.QRectF(self.radius-dial_radius, self.radius-dial_radius, dial_radius*2, dial_radius*2)
        cursor_size = self.radius*self.cursor_size
        if cursor_size < 0: cursor_size = 0
        self.cursor.setFixedSize(cursor_size, cursor_size)
        self.cursor.move(-cos(radians(self.comp_value-60))*self.cursor_ratio*self.in_radius+self.radius+self.translate[0],
                         sin(radians(-self.comp_value+60))*self.cursor_ratio*self.in_radius+self.radius+self.translate[1]
                         )
        ghost_size = self.radius-dial_radius
        if ghost_size < 0: ghost_size = 0
        self.ghost.setFixedSize(ghost_size, ghost_size)
        self.ghost.move(-cos(radians(self.comp_value-60))*(ghost_size/2+dial_radius)+self.radius+self.translate[0],
                         sin(radians(-self.comp_value+60))*(ghost_size/2+dial_radius)+self.radius+self.translate[1]
                         )
        for s in range(2):
            self._dial_bgd_colors[s].setCenter(self.dial_size, self.dial_size*2)
            self._dial_bgd_colors[s].setRadius(self.dial_size*2)
            self._dial_bgd_colors[s].setFocalPoint(self.dial_size, self.dial_size)
            self._dial_border_colors[s].setCenter(self.dial_size, self.dial_size*2)
            self._dial_border_colors[s].setRadius(self.dial_size*2)
            self._dial_border_colors[s].setFocalPoint(self.dial_size, self.dial_size)
        font_size = self.dial_size/9
        if font_size >= 7:
            self.value_font.setPointSize(font_size)
            self.value_rect = (0, self.dial_size-font_size*.9, self.dial_size, font_size*1.2)
        else:
            self.value_rect = None
        self.fgd_pen = QtGui.QPen(self.fgd_color, self.dial_size/50.)
        self.cursor_pen = QtGui.QPen(self.fgd_color, self.dial_size/30.)
        self.dial_pen = QtGui.QPen(self.dial_color, self.dial_size/100.)
        if self.gradient:
            self.fill_color.setCenter(self.dial_size/2, self.dial_size/2)
        if self.name:
            self.setMinimumWidth(max([self.dial_size, self.label_font_metrics.width(self.name)]))

    def get_closest(self, value):
        pos = bisect_left(self.range_list, value)
        if pos == 0:
            return self.range_list[0]
        if pos == len(self.range_list):
            return self.range_list[-1]
        before = self.range_list[pos-1]
        after = self.range_list[pos]
        if after-value < value-before:
            return after
        return before

    def _setValue(self, value):
        if not self.min_value <= value <= self.max_value: return
        self.value = int(round(value, 0))
        if not self.gradient:
            self.fill_color = QtGui.QColor(*self.setColor())
        self.cursor.move(-cos(radians(self.comp_value-60))*self.cursor_ratio*self.in_radius+self.radius+self.translate[0],
                         sin(radians(-self.comp_value+60))*self.cursor_ratio*self.in_radius+self.radius+self.translate[1]
                         )
        dial_radius = self.in_radius*self.dial_ratio
        ghost_size = self.radius-dial_radius
        self.ghost.move(-cos(radians(self.comp_value-60))*(ghost_size/2+dial_radius)+self.radius+self.translate[0],
                         sin(radians(-self.comp_value+60))*(ghost_size/2+dial_radius)+self.radius+self.translate[1]
                         )
        self.update()

    def setValue(self, value):
        self._setValue(value)
        if self.isVisible() and self.value_rect is None:
#            self.setToolTip('{}'.format(self.text_value))
            point = QtCore.QPoint(self.translate[0]+self.dial_size, self.translate[1])
            QtGui.QToolTip.showText(self.mapToGlobal(point), self.text_value, self, QtCore.QRect(0, 0, 20, 20))
#            event = QtGui.QHelpEvent(QtCore.QEvent.ToolTip, point, self.mapToGlobal(point))
#            self.event(event)
#        else:
#            self.setToolTip('{}'.format(self.text_value))
        self.valueChanged.emit(self.value)

    def eventFilter(self, source, event):
        if source in [self.cursor, self.ghost]:
            if event.type() == QtCore.QEvent.MouseButtonPress and event.button() == QtCore.Qt.LeftButton:
                self.cursor_mode = True
            elif event.type() == QtCore.QEvent.MouseButtonRelease and event.button() == QtCore.Qt.LeftButton:
                self.cursor_mode = False
        if event.type() == QtCore.QEvent.ToolTip and QtCore.QRect(*self.translate+(self.dial_size, )*2).contains(event.pos()):
            QtGui.QToolTip.showText(event.globalPos(), self.text_value, self, self.dial_rect.toRect())
        return QtGui.QWidget.eventFilter(self, source, event)

    def wheelEvent(self, event):
        if event.modifiers() == QtCore.Qt.ShiftModifier:
            delta = self.step*5
        else:
            delta = self.step
        value = self.value+delta if event.delta() > 1 else self.value-delta
        if value < self.min_value:
            value = self.min_value
        elif value > self.max_value:
            value = self.max_value
        self.setValue(value)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.mouse_pos = event.pos()
            self.ghost_value = self.value
            self.mouse_dir = None
        elif event.button() == QtCore.Qt.MidButton and self.default_value is not None:
            self.setValue(self.default_value)

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.mouse_dir = None

    def mouseMoveEvent(self, event):
        if not event.buttons() == QtCore.Qt.LeftButton: return
        if self.cursor_mode:
            x = -self.translate[0]-self.dial_size/2+event.x()
            y = -self.translate[1]-self.dial_size/2+event.y()
            try:
                angle = degrees(acos(x/hypot(x, y)))
                if y < 0:
                    angle = 360 - angle
                angle += 270
                if angle >= 360:
                    angle -= 360
                if angle > 330: angle = 330
                if angle < 30: angle = 30
                value = (angle-30)/300.*self.range+self.min_value
                if self.step != 1:
                    value = self.get_closest(value)
                self.setValue(value)
                return
            except Exception as Err:
                print Err
                return
        x = self.mouse_pos.x()
        y = self.mouse_pos.y()
        diff_x = x-event.x()
        diff_y = y-event.y()
        if self.step == 1 and self.range >= 16:
            self.setValue(self.value-diff_x*self.step+diff_y*self.step)
        else:
            if self.step == 1:
                ratio = .01*self.range
            else:
                ratio = 1
            self.ghost_value = self.ghost_value-diff_x*ratio+diff_y*ratio
            self.setValue(self.get_closest(self.ghost_value))
        self.mouse_pos = event.pos()
