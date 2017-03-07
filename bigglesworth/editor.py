#!/usr/bin/env python2.7
# *-* coding: utf-8 *-*

import pickle
from string import uppercase
from itertools import cycle
from random import randrange
from PyQt4 import QtCore, QtGui

from midiutils import *

from const import *
from classes import *
from utils import *
from ui_classes import *

class ParamObject(object):
    def __init__(self, param_tuple):
        default = param_tuple.range[0]
        values = param_tuple.values
        self.attr = param_tuple.attr
        self.short_name = param_tuple.short_name
        self._value = default
        if isinstance(values, AdvParam):
            self.adv = values
            self.adv_params = list(reversed(self.adv.named_kwargs))
            self.object_list = [[] for n in self.adv_params]
        else:
            self.adv = None
            self.object_list = []

    def add(self, obj, sub_par=None):
        if not self.adv or sub_par is None:
            self.object_list.append(obj)
            return
        self.object_list[self.adv_params.index(sub_par)].append(obj)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        if self.adv:
            if isinstance(value, tuple):
                value, sub_par = value
                values = []
                for i, field in enumerate(self.adv_params):
                    if field == sub_par:
                        values.append(value)
                    else:
                        values.append(self.object_list[i][0].value)
                self._value = self.adv.normalized(*values)
            else:
                self._value = value
                values = self.adv.get_indexes(value)
            for i, v in enumerate(values):
                for o in self.object_list[i]:
                    o._setValue(v)
            return
        self._value = value
        for o in self.object_list:
            if isinstance(o, BlofeldEnv):
                o.setValue({self.short_name:value})
                continue
            if isinstance(o, BlofeldCombo):
                if not 0 <= value <= o.count:
                    continue
            elif isinstance(o, BlofeldDial):
                if not o.min_value <= value <= o.max_value:
                    continue
            o._setValue(value)


class BlofeldButton(SquareButton):
    def __init__(self, parent, param_tuple, *args, **kwargs):
        full_range, values, name, short_name, family, attr, id = param_tuple
        if 'name' in kwargs:
            short_name = kwargs.pop('name')
        SquareButton.__init__(self, parent, name=short_name, *args, **kwargs)
        parent.object_dict[attr].add(self)
        self.attr = attr
        self.main = parent
        if self.isCheckable():
            self.toggled.connect(lambda state: setattr(self.main, self.attr, int(state)))
        else:
            pass

    def _setValue(self, state):
        self.setChecked(state)
        self.toggle_states(state)

class BlofeldSlider(Slider):
    def __init__(self, parent, param_tuple, *args, **kwargs):
        if len(param_tuple) == 7:
            full_range, values, name, short_name, family, attr, id = param_tuple
        else:
            full_range, values, name, short_name, family, attr= param_tuple
        if 'name' in kwargs:
            short_name = kwargs.pop('name')
        Slider.__init__(self, parent, name=short_name, *args, **kwargs)
        parent.object_dict[attr].add(self)
        self.attr = attr
        self.main = parent
        self.valueChanged.connect(lambda value: setattr(self.main, self.attr, value))

class BlofeldDial(Dial):
    def __init__(self, parent, param_tuple, *args, **kwargs):
        if len(param_tuple) == 7:
            full_range, values, name, short_name, family, attr, id = param_tuple
        else:
            full_range, values, name, short_name, family, attr= param_tuple
        if 'name' in kwargs:
            short_name = kwargs.pop('name')
        Dial.__init__(self, parent=parent, full_range=full_range, name=short_name, value_list=values, *args, **kwargs)
        parent.object_dict[attr].add(self)
        self.attr = attr
        self.main = parent
        self.valueChanged.connect(lambda value: setattr(self.main, self.attr, value))

class BlofeldCombo(Combo):
    internalUpdate = QtCore.pyqtSignal(int)
    def __init__(self, parent, param_tuple, sub_par=None, *args, **kwargs):
        if len(param_tuple) == 7:
            full_range, values, name, short_name, family, attr, id = param_tuple
        else:
            full_range, values, name, short_name, family, attr= param_tuple
        if 'name' in kwargs:
            short_name = kwargs.pop('name')
        if 'values' in kwargs:
            values = kwargs.pop('values')
        if 'value_list' in kwargs:
            values = kwargs.pop('value_list')
        if not (isinstance(values, list) or isinstance(values, tuple)):
            values = getattr(values, sub_par)
        Combo.__init__(self, parent=parent, value_list=values, name=short_name, *args, **kwargs)
        parent.object_dict[attr].add(self, sub_par)
        self.attr = attr
        self.main = parent
        self.indexChanged.connect(lambda id: setattr(self.main, self.attr, id if sub_par is None else (id, sub_par)))

    def _setValue(self, id):
        Combo._setValue(self, id)
        self.internalUpdate.emit(id)

class BlofeldEnv(Envelope):
    def __init__(self, parent, env_name, *args, **kwargs):
        Envelope.__init__(self, parent, *args, **kwargs)
        self.anim = QtCore.QPropertyAnimation(self, 'geometry')
        self.anim.setDuration(50)
        self.anim.finished.connect(self.checkAnimation)
        self.normal = True
        self.changing = False
        parent.object_dict['{}_Attack'.format(env_name)].add(self)
        parent.object_dict['{}_Attack_Level'.format(env_name)].add(self)
        parent.object_dict['{}_Decay'.format(env_name)].add(self)
        parent.object_dict['{}_Sustain'.format(env_name)].add(self)
        parent.object_dict['{}_Decay_2'.format(env_name)].add(self)
        parent.object_dict['{}_Sustain_2'.format(env_name)].add(self)
        parent.object_dict['{}_Release'.format(env_name)].add(self)

    def setMaximized(self):
        self.changing = False
        if not self.underMouse():
            self.normalize()

    def enterEvent(self, event):
        if not self.parent().isActiveWindow(): return
        if self.normal:
            self.normal_pos = self.pos()
            self.normal_layout = self.parent().layout()
            self.index = self.normal_layout.getItemPosition(self.normal_layout.indexOf(self))
            self.setWindowFlags(QtCore.Qt.FramelessWindowHint|QtCore.Qt.Tool|QtCore.Qt.ToolTip)
            self.setMaximumSize(QtCore.QSize(QWIDGETSIZE_MAX, QWIDGETSIZE_MAX))
#            self.resize(100, 80)
#            self.setFixedSize(240, 120)
            Envelope.move(self, self.parent().mapToGlobal(self.normal_pos))
            self.show()
            self.changing = True
            self.activateWindow()
            self.normal = False
            self.setShowPoints(True)
            desktop = QtGui.QApplication.desktop().availableGeometry(self)
            geo = QtCore.QRect(self.x(), self.y(), 240, 120)
            if not desktop.contains(geo, True):
                if geo.x() < desktop.x():
                    x = desktop.x()
                elif geo.right() > desktop.right():
                    x = desktop.right()-geo.width()
                else:
                    x = geo.x()
                if geo.y() < desktop.y():
                    y = desktop.y()
                elif geo.bottom() > desktop.bottom():
                    y = desktop.bottom()-geo.height()
                else:
                    y = geo.y()
#                self.move(x, y)
            else:
                x = self.x()
                y = self.y()
            self.anim.setStartValue(self.geometry())
            self.anim.setEndValue(QtCore.QRect(x, y, 240, 120))
            self.anim.start()

    def checkAnimation(self):
        if self.anim.direction() == QtCore.QPropertyAnimation.Forward:
            if not self.underMouse():
                self.normalize()
        else:
            self.anim.setDirection(QtCore.QPropertyAnimation.Forward)
            self.normalize()

    def activateWindow(self):
#        Envelope.activateWindow(self)
        self.setFocus(QtCore.Qt.ActiveWindowFocusReason)
        QtCore.QTimer.singleShot(50, self.setMaximized)

    def normalize(self):
        self.setFixedSize(68, 40)
        self.setWindowFlags(QtCore.Qt.Widget)
        self.normal_layout.addWidget(self, *self.index)
        self.normal = True
        self.normal_pos = self.pos()
        self.setShowPoints(False)
        Envelope.activateWindow(self)
        self.raise_()

    def leaveEvent(self, event):
        if self.changing: return
        if not self.normal:
            self.anim.setDirection(QtCore.QPropertyAnimation.Backward)
            if not self.anim.state() == QtCore.QPropertyAnimation.Running:
                self.anim.start()
#            self.normalize()


class BaseDisplayWidget(QtGui.QGraphicsWidget):
    pen = brush = QtGui.QColor(30, 50, 40)

class DownArrowWidget(BaseDisplayWidget):
    arrow = QtGui.QPainterPath()
    arrow.moveTo(-4, -2)
    arrow.lineTo(4, -2)
    arrow.lineTo(0, 2)
    arrow.closeSubpath()
    def __init__(self, parent, padding=2):
        BaseDisplayWidget.__init__(self, parent)
        width = self.arrow.boundingRect().width()+padding
        height = self.arrow.boundingRect().height()+padding
        self.setMinimumSize(width, height)
        self.setMaximumSize(width, height)
        self.setSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Minimum)

    def paint(self, painter, *args, **kwargs):
        painter.setPen(self.pen)
        painter.setBrush(self.brush)
        painter.setRenderHints(QtGui.QPainter.Antialiasing)
        painter.translate(self.rect().center())
        painter.drawPath(self.arrow)

class UpArrowWidget(DownArrowWidget):
    arrow = QtGui.QPainterPath()
    arrow.moveTo(-4, 2)
    arrow.lineTo(4, 2)
    arrow.lineTo(0, -2)
    arrow.closeSubpath()

class BaseTextWidget(BaseDisplayWidget):
    def __init__(self, text, parent):
        BaseDisplayWidget.__init__(self, parent)
        self.text = text
        self.text_align = QtCore.Qt.AlignLeft

    def paint(self, painter, *args, **kwargs):
#        painter.drawRect(self.rect())
        painter.setRenderHints(QtGui.QPainter.Antialiasing)
        painter.setPen(self.pen)
        painter.setBrush(self.brush)
        painter.setFont(self.font)
        painter.drawText(self.rect(), self.text_align, self.text)

class ProgLabelTextWidget(BaseTextWidget):
    def __init__(self, text, parent):
        BaseTextWidget.__init__(self, text, parent)
        self.font = QtGui.QFont('Fira Sans', 22)
        self.font_metrics = QtGui.QFontMetrics(self.font)
        self.setMinimumSize(self.font_metrics.width(self.text), self.font_metrics.height())
        while len(self.text) < 16:
            self.text += ' '
        self.text = QtCore.QString.fromUtf8(self.text)
        self.text_list = QtCore.QStringList([l for l in self.text])

    def setChar(self, pos, char):
        if char == 127:
            readable = QtCore.QString.fromUtf8('°')
        else:
            readable = QtCore.QString(unichr(char))
        self.text_list[pos] = readable
        self.text = self.text_list.join('')
        self.update()

class SmallTextWidget(BaseTextWidget):
    def __init__(self, text, parent):
        BaseTextWidget.__init__(self, text, parent)
        self.font = QtGui.QFont('Fira Sans', 12)
        self.font_metrics = QtGui.QFontMetrics(self.font)

class BankTextWidget(SmallTextWidget):
    def __init__(self, parent):
        SmallTextWidget.__init__(self, 'A', parent)
        max_letters = max([self.font_metrics.width(l) for l in uppercase])
        self.setMinimumSize(max_letters, self.font_metrics.height())
        self.setMaximumSize(max_letters, self.font_metrics.height())

class ProgTextWidget(SmallTextWidget):
    def __init__(self, parent):
        SmallTextWidget.__init__(self, '001', parent)
#        max_letters = max([self.font_metrics.width(l) for l in uppercase])
        max_digits = max([self.font_metrics.width(str(i)) for i in range(10)])
        width = max_digits*3
        self.setMinimumSize(width, self.font_metrics.height())
        self.setMaximumSize(width, self.font_metrics.height())

class CatTextWidget(SmallTextWidget):
    def __init__(self, parent):
        SmallTextWidget.__init__(self, 'off', parent)
        width = max([self.font_metrics.width(c) for c in categories])
        self.setMinimumSize(width, self.font_metrics.height())
        self.setMaximumSize(width, self.font_metrics.height())
        self.text_align = QtCore.Qt.AlignRight

    def setCat(self, cat):
        self.text = categories[cat]
        self.update()

class DisplayVSpacer(QtGui.QGraphicsWidget):
    def __init__(self, parent, size=2):
        QtGui.QGraphicsWidget.__init__(self, parent)
        self.setMinimumHeight(size)
        self.setMaximumSize(0, size)

#    def paint(self, painter, *args, **kwargs):
#        painter.drawRect(self.rect())

class DisplayHSpacer(QtGui.QGraphicsWidget):
    def __init__(self, parent, size=2):
        QtGui.QGraphicsWidget.__init__(self, parent)
        self.setMinimumWidth(size)
        self.setMaximumSize(size, 0)

#    def paint(self, painter, *args, **kwargs):
#        painter.drawRect(self.rect())

class SmallLabelTextWidget(BaseTextWidget):
    def __init__(self, text, parent, fixed=False, font_size=12, max_size=None, bold=False):
        BaseTextWidget.__init__(self, text, parent)
        self.font = QtGui.QFont('Fira Sans', font_size, weight=QtGui.QFont.DemiBold if bold else QtGui.QFont.Normal)
        self.font_metrics = QtGui.QFontMetrics(self.font)
        self.setMinimumSize(self.font_metrics.width(self.text), self.font_metrics.height())
        self.setMaximumHeight(self.font_metrics.height())
        if fixed:
            self.setMaximumWidth(self.font_metrics.width(self.text) if max_size is None else max_size)

class DisplayComboLabelClass(BaseTextWidget):
    def __init__(self, parent):
        BaseDisplayWidget.__init__(self, parent)
        self.currentIndex = 0
        self.count = len(self.value_list)
        self.text_align = QtCore.Qt.AlignHCenter|QtCore.Qt.AlignVCenter
        self.font = QtGui.QFont('Fira Sans', 9)
        self.font_metrics = QtGui.QFontMetrics(self.font)
        self.setMinimumSize(max([self.font_metrics.width(txt) for txt in self.value_list if isinstance(txt, QtCore.QString)]), self.font_metrics.height())
#        self.setMaximumSize(self.minimumSize())
#        if fixed:
#            self.setMaximumWidth(self.font_metrics.width(self.text) if max_size is None else max_size)

    def setCurrentIndex(self, index):
        if not 0 <= index < self.count: return
        self.currentIndex = index
        self.update()

    def paint(self, painter, *args, **kwargs):
#        painter.drawRect(self.rect())
        painter.setRenderHints(QtGui.QPainter.Antialiasing)
        painter.setPen(self.pen)
        painter.setBrush(self.brush)
        item = self.value_list[self.currentIndex]
        if isinstance(item, QtCore.QString):
            painter.setFont(self.font)
            painter.drawText(self.rect(), self.text_align, item)
        else:
            item_rect = item.boundingRect()
            painter.translate((self.rect().width()-item_rect.width())/2+1, (self.rect().height()-item_rect.height())/2)
            painter.drawPath(item)

class StepTypeComboLabel(DisplayComboLabelClass):
    value_list = [
                 '●', 
                 '○', 
                 '◀', 
                 '▼', 
                 '▲', 
                 ]
    value_list = map(QtCore.QString.fromUtf8, value_list)
    firstlast = QtGui.QPainterPath()
    firstlast.moveTo(4, 0)
    firstlast.lineTo(8, 4)
    firstlast.lineTo(0, 4)
    firstlast.closeSubpath()
    firstlast.moveTo(0, 6)
    firstlast.lineTo(8, 6)
    firstlast.lineTo(4, 10)
    firstlast.closeSubpath()
    value_list.append(firstlast)
    chord = QtGui.QPainterPath()
    chord.moveTo(4, 0)
    chord.lineTo(4, 8)
    chord.addEllipse(0, 4, 4, 2)
    chord.addEllipse(0, 7, 4, 2)
    value_list.append(chord)
    value_list.append(QtCore.QString.fromUtf8('?'))

class AccentComboLabel(DisplayComboLabelClass):
    value_list = ['sil.', '/4', '/3', '/2', '*1', '*2', '*3', '*4', ]
    value_list = map(QtCore.QString.fromUtf8, value_list)

class TimingComboLabel(DisplayComboLabelClass):
    value_list = ['rnd', '-3', '-2', '-1', '+0', '+1', '+2', '+3', ]
    value_list = map(QtCore.QString.fromUtf8, value_list)

class LengthComboLabel(DisplayComboLabelClass):
    value_list = ['leg.', '-3', '-2', '-1', '+0', '+1', '+2', '+3', ]
    value_list = map(QtCore.QString.fromUtf8, value_list)

class DisplayButton(QtGui.QGraphicsWidget):
    on_pen = on_brush = QtGui.QColor(30, 50, 40)
    off_pen = QtGui.QColor(160, 180, 170)
    off_brush = QtGui.QColor(QtCore.Qt.transparent)
    text_pen = on_pen
    pen = off_pen
    brush = off_brush
    normal_frame_border_pen = QtGui.QColor(220, 220, 220, 220)
    normal_frame_border_brush = QtGui.QColor(220, 220, 220, 120)
    focus_frame_border_pen = QtGui.QColor(180, 180, 180, 180)
    focus_frame_border_brush = QtGui.QColor(200, 200, 200, 180)
    frame_border_pen = normal_frame_border_pen
    frame_border_brush = normal_frame_border_brush
    path = None
    text = None
    toggled = QtCore.pyqtSignal(bool)
    clicked = QtCore.pyqtSignal()

    def __init__(self, parent, state=False):
        QtGui.QGraphicsWidget.__init__(self, parent)
        self.setAcceptHoverEvents(True)
        self._setState(state)

    def hoverEnterEvent(self, event):
        self.frame_border_pen = self.focus_frame_border_pen
        self.frame_border_brush = self.focus_frame_border_brush
        self.update()

    def hoverLeaveEvent(self, event):
        self.frame_border_pen = self.normal_frame_border_pen
        self.frame_border_brush = self.normal_frame_border_brush
        self.update()

    def mousePressEvent(self, event):
        pass

    def mouseReleaseEvent(self, event):
        if not self.isUnderMouse(): return
        self.clicked.emit()
        self.setState(not self.state)

    def _setState(self, state):
        self.state = state
        if state:
            self.pen = self.on_pen
            self.brush = self.on_brush
        else:
            self.pen = self.off_pen
            self.brush = self.off_brush
        self.update()

    def setState(self, state):
        self._setState(state)
        self.toggled.emit(self.state)

    def paint(self, painter, *args, **kwargs):
        painter.setRenderHints(QtGui.QPainter.Antialiasing)
        painter.save()
        painter.translate(.5, .5)
        painter.setPen(self.frame_border_pen)
        painter.setBrush(self.frame_border_brush)
        painter.drawRect(0, 0, self.boundingRect().width()-1, self.boundingRect().height()-1)
        painter.restore()
        painter.setPen(self.pen)
        painter.setBrush(self.brush)
        if self.path and not self.text:
            painter.translate((self.boundingRect().width()-self.path.boundingRect().width())/2, (self.boundingRect().height()-self.path.boundingRect().height())/2)
            painter.drawPath(self.path)
        elif self.text and not self.path:
            painter.setPen(self.text_pen)
            painter.setFont(self.font)
            painter.translate((self.boundingRect().width()-self.font_metrics.width(self.text))/2, 0)
            painter.drawText(0, self.font_metrics.height(), self.text)
        elif self.text and self.path:
            br_height = self.boundingRect().height()
            br_width = self.boundingRect().width()
            path_width = self.path.boundingRect().width()
            delta_y = (br_height-self.path.boundingRect().height())/2
            painter.translate((br_width-path_width-self.font_metrics.width(self.text))/2-2, delta_y)
            painter.drawPath(self.path)
            painter.translate((path_width+4), -delta_y)
            painter.setPen(self.text_pen)
            painter.setFont(self.font)
            painter.drawText(0, self.font_metrics.height()-.5, self.text)

class GlideDisplayButton(DisplayButton):
    path = QtGui.QPainterPath()
    path.arcTo(0, -3.5, 9, 7, 180, 90)
    path.arcTo(1, 3.5, 7, 9, 90, -90)
    path.arcTo(-1, 4.5, 9, 7, 0, 90)
    path.arcTo(0, -4.5, 7, 9, 270, -90)
    def __init__(self, parent, step, glide_list):
        DisplayButton.__init__(self, parent)
        self.step = step
        self.glide_list = glide_list
        self.siblings = [None for i in range(16)]

    def mouseMoveEvent(self, event):
        if not self.isUnderMouse():
            item = self.scene().itemAt(self.mapToScene(event.pos()))
            if not isinstance(item, self.__class__): return
            index = self.glide_list.index(item)
            if self.siblings[index] == None:
                self.siblings[index] = item.state
                item._setState(self.state)
                item.hoverEnterEvent(None)
            if index > self.step:
                for i in range(self.step+1, index+1):
                    if self.siblings[i] == None:
                        self.siblings[i] = self.glide_list[i].state
                        self.glide_list[i].hoverEnterEvent(None)
                    self.glide_list[i]._setState(self.state)
                for i in range(index+1, len(self.glide_list)):
                    if self.siblings[i] != None:
                        self.glide_list[i]._setState(self.siblings[i])
                        self.glide_list[i].hoverLeaveEvent(None)
                        self.siblings[i] = None
                for i in range(self.step):
                    if self.siblings[i] != None:
                        self.glide_list[i]._setState(self.siblings[i])
                        self.glide_list[i].hoverLeaveEvent(None)
                        self.siblings[i] = None
            else:
                for i in range(index):
                    if self.siblings[i] != None:
                        self.glide_list[i]._setState(self.siblings[i])
                        self.glide_list[i].hoverLeaveEvent(None)
                        self.siblings[i] = None
                for i in range(index, self.step):
                    if self.siblings[i] == None:
                        self.siblings[i] = self.glide_list[i].state
                        self.glide_list[i].hoverEnterEvent(None)
                    self.glide_list[i]._setState(self.state)
                for i in range(self.step+1, len(self.glide_list)):
                    if self.siblings[i] != None:
                        self.glide_list[i]._setState(self.siblings[i])
                        self.glide_list[i].hoverLeaveEvent(None)
                        self.siblings[i] = None
            return
        for i, state in enumerate(self.siblings):
            if state is None: continue
            self.glide_list[i].hoverLeaveEvent(None)
            self.glide_list[i]._setState(state)
        self.siblings = [None for i in range(16)]

    def mouseReleaseEvent(self, event):
        if not self.isUnderMouse():
            if self.siblings.count(None) == len(self.siblings): return
            for i, state in enumerate(self.siblings):
                if state is None:
                    continue
                self.glide_list[i].hoverLeaveEvent(None)
                self.glide_list[i].setState(self.state)
            self.siblings = [None for i in range(16)]
            return
        self.setState(not self.state)
        self.siblings = [None for i in range(16)]


class DisplayCombo(QtGui.QGraphicsWidget):
    pen = brush = QtGui.QColor(30, 50, 40)
    normal_frame_border_pen = QtGui.QColor(220, 220, 220, 220)
    normal_frame_border_brush = QtGui.QColor(220, 220, 220, 120)
    focus_frame_border_pen = QtGui.QColor(180, 180, 180, 180)
    focus_frame_border_brush = QtGui.QColor(200, 200, 200, 180)
    frame_border_pen = normal_frame_border_pen
    frame_border_brush = normal_frame_border_brush
    currentIndexChanged = QtCore.pyqtSignal(int)

    def __init__(self, parent, label_class):
        QtGui.QGraphicsWidget.__init__(self, parent)
        self.setAcceptHoverEvents(True)
        self.padding = 2
        self.currentIndex = 0
        self.setSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Minimum)
        self.layout = QtGui.QGraphicsGridLayout()
        self.setLayout(self.layout)
        self.value_lbl = label_class(self)
        self.count = self.value_lbl.count
        self.layout.addItem(self.value_lbl, 0, 0, 2, 1)
        self.up_arrow = UpArrowWidget(self, 0)
        self.up_arrow.setOpacity(0)
        self.layout.addItem(self.up_arrow, 0, 1, QtCore.Qt.AlignBottom)
        self.down_arrow = DownArrowWidget(self, 0)
        self.down_arrow.setOpacity(0)
        self.layout.addItem(self.down_arrow, 1, 1, QtCore.Qt.AlignTop)
        self.layout.setContentsMargins(2, 1, 2, 1)

    def hoverEnterEvent(self, event):
        self.frame_border_pen = self.focus_frame_border_pen
        self.frame_border_brush = self.focus_frame_border_brush
        self.up_arrow.setOpacity(1)
        self.down_arrow.setOpacity(1)
        self.update()

    def highlight(self):
        self.frame_border_pen = self.focus_frame_border_pen
        self.frame_border_brush = self.focus_frame_border_brush
        self.update()

    def hoverLeaveEvent(self, event):
        self.frame_border_pen = self.normal_frame_border_pen
        self.frame_border_brush = self.normal_frame_border_brush
        self.up_arrow.setOpacity(0)
        self.down_arrow.setOpacity(0)
        self.update()

    def unhighlight(self):
        self.frame_border_pen = self.normal_frame_border_pen
        self.frame_border_brush = self.normal_frame_border_brush
        self.update()

    def wheelEvent(self, event):
        delta = 1 if event.delta() > 0 else -1
        self.setCurrentIndex(self.currentIndex+delta)
        

    def mousePressEvent(self, event):
        pass

    def mouseReleaseEvent(self, event):
        if self.up_arrow.geometry().contains(event.pos()):
            if self.currentIndex == self.count-1: return
            delta = 1
        elif self.down_arrow.geometry().contains(event.pos()):
            if self.currentIndex == 0: return
            delta = -1
        else:
            return
        self.setCurrentIndex(self.currentIndex+delta)

    def _setCurrentIndex(self, index):
        if index < 0: index = 0
        elif index >= self.count: index = self.count-1
        self.currentIndex = index
        self.value_lbl.setCurrentIndex(index)

    def setCurrentIndex(self, index):
        self._setCurrentIndex(index)
        self.currentIndexChanged.emit(self.currentIndex)
        self.update()

    def paint(self, painter, *args, **kwargs):
        painter.setRenderHints(QtGui.QPainter.Antialiasing)
        painter.translate(.5, .5)
        painter.setPen(self.frame_border_pen)
        painter.setBrush(self.frame_border_brush)
        painter.drawRect(0, 0, self.boundingRect().width()-1, self.boundingRect().height()-1)
#        painter.translate(self.rect().center())
#        painter.drawPath(self.arrow)

class ArpDisplayComboClass(DisplayCombo):
    def __init__(self, parent, label_class, step, combo_list):
        DisplayCombo.__init__(self, parent, label_class)
        self.step = step
        self.combo_list = combo_list
        self.siblings = [None for i in range(16)]

    def mouseMoveEvent(self, event):
        if not self.isUnderMouse():
            item = self.scene().itemAt(self.mapToScene(event.pos()))
            if not isinstance(item, self.__class__): return
            index = self.combo_list.index(item)
            if self.siblings[index] == None:
                self.siblings[index] = item.currentIndex
                item._setCurrentIndex(self.currentIndex)
                item.highlight()
            if index > self.step:
                for i in range(self.step+1, index+1):
                    if self.siblings[i] == None:
                        self.siblings[i] = self.combo_list[i].currentIndex
                        self.combo_list[i].highlight()
                    self.combo_list[i]._setCurrentIndex(self.currentIndex)
                for i in range(index+1, len(self.combo_list)):
                    if self.siblings[i] != None:
                        self.combo_list[i]._setCurrentIndex(self.siblings[i])
                        self.combo_list[i].unhighlight()
                        self.siblings[i] = None
                for i in range(self.step):
                    if self.siblings[i] != None:
                        self.combo_list[i]._setCurrentIndex(self.siblings[i])
                        self.combo_list[i].unhighlight()
                        self.siblings[i] = None
            else:
                for i in range(index):
                    if self.siblings[i] != None:
                        self.combo_list[i]._setCurrentIndex(self.siblings[i])
                        self.combo_list[i].unhighlight()
                        self.siblings[i] = None
                for i in range(index, self.step):
                    if self.siblings[i] == None:
                        self.siblings[i] = self.combo_list[i].currentIndex
                        self.combo_list[i].highlight()
                    self.combo_list[i]._setCurrentIndex(self.currentIndex)
                for i in range(self.step+1, len(self.combo_list)):
                    if self.siblings[i] != None:
                        self.combo_list[i]._setCurrentIndex(self.siblings[i])
                        self.combo_list[i].unhighlight()
                        self.siblings[i] = None
            return
        for i, value in enumerate(self.siblings):
            if value is None: continue
            self.combo_list[i].unhighlight()
            self.combo_list[i]._setCurrentIndex(value)
        self.siblings = [None for i in range(16)]

    def mouseReleaseEvent(self, event):
        if not self.isUnderMouse():
            if self.siblings.count(None) == len(self.siblings): return
            for i, value in enumerate(self.siblings):
                if value is None:
                    continue
                self.combo_list[i].unhighlight()
                self.combo_list[i].setCurrentIndex(self.currentIndex)
            self.siblings = [None for i in range(16)]
            return
        self.siblings = [None for i in range(16)]
        DisplayCombo.mouseReleaseEvent(self, event)


class StepTypeCombo(ArpDisplayComboClass):
    def __init__(self, parent, step, combo_list):
        ArpDisplayComboClass.__init__(self, parent, StepTypeComboLabel, step, combo_list)

class AccentCombo(ArpDisplayComboClass):
    def __init__(self, parent, step, combo_list):
        ArpDisplayComboClass.__init__(self, parent, AccentComboLabel, step, combo_list)

class TimingCombo(ArpDisplayComboClass):
    def __init__(self, parent, step, combo_list):
        ArpDisplayComboClass.__init__(self, parent, TimingComboLabel, step, combo_list)

class LengthCombo(ArpDisplayComboClass):
    def __init__(self, parent, step, combo_list):
        ArpDisplayComboClass.__init__(self, parent, LengthComboLabel, step, combo_list)

class ArpStepWidget(QtGui.QGraphicsWidget):
    default_pen = QtGui.QColor(10, 30, 20)
    active_pen = QtGui.QColor(QtCore.Qt.red)
    silent_pen = QtGui.QColor(QtCore.Qt.gray)
    pen = normal_pen = default_pen
    normal_brush = QtGui.QColor(30, 50, 40, 220)
    silent_brush = QtGui.QColor(30, 50, 40, 80)
    brush = normal_brush
    unit = 10
    accent = 4
    display_timing = timing = 4
    display_length = length = 4
    next = None
    move_action = None
    shape_rect = QtCore.QRectF(0, 0, 70, 90)
    shape_rect_path = QtGui.QPainterPath()
    shape_rect_path.addRect(shape_rect)
    shape_size = QtCore.QSizeF(shape_rect.width(), shape_rect.height())

    accentChanged = QtCore.pyqtSignal(int)
    lengthChanged = QtCore.pyqtSignal(int)
    timingChanged = QtCore.pyqtSignal(int)

    def __init__(self, parent=None):
        QtGui.QGraphicsWidget.__init__(self, parent)
        self.setAcceptHoverEvents(True)
        self.rect = QtCore.QRectF(0, 35, 40, 10)
        self.top_rect = QtCore.QRectF(0, 25, 40, 10)
        self.bottom_rect = QtCore.QRectF(0, 45, 40, 10)
        self.left_rect = QtCore.QRectF(0, 35, 10, 10)
        self.right_rect = QtCore.QRectF(30, 35, 10, 10)

    def size(self):
        return self.shape_size

    def boundingRect(self):
        if self.length != LEGATO:
            return QtCore.QRectF(0, 0, self.shape_size.width(), self.shape_size.height())
        if self.next.timing > 4:
            units = self.next.timing-4
        else:
            units = 0
        width = self.size().width() + units*self.unit
        return QtCore.QRectF(0, 0, width, self.size().height())

    def shape(self):
        return self.shape_rect_path

    def hoverEnterEvent(self, event):
        pass

    def mouseMoveEvent(self, event):
#        print 'move {}'.format(event.pos())
        if self.move_action is None: return
        if self.move_action == MOVEUP:
            delta = int((self.rect.top()-event.pos().y())/self.unit)
            accent = self.accent+delta
            if self.accent < 4:
                accent = 4
            elif accent < 4:
                self.move_action = MOVEDOWN
                self.setCursor(cursors(DownCursor))
                return
            elif accent > 7:
                accent = 7
            self.setAccent(accent)
        elif self.move_action == MOVEDOWN:
            delta = int((self.rect.bottom()-event.pos().y())/self.unit)
            accent = self.accent+delta
            if self.accent > 4:
                accent = 4
            elif accent > 4:
                self.move_action = MOVEUP
                self.setCursor(cursors(UpCursor))
                return
            elif accent < 0:
                accent = 0
            self.setAccent(accent)
        elif self.move_action == MOVELEFT:
            delta = int((self.rect.left()+event.pos().x())/self.unit)
            timing = self.timing+delta
            if timing < 1:
                timing = 1
            elif timing > 7:
                timing = 7
            if timing < self.timing and self.length > 0:
                length = self.length + 1
                if length >= 7:
                    length = 7
                self.setLength(length)
            elif timing > self.timing and self.length > 0:
                length = self.length - 1
                if length <= 1:
                    length = 1
                self.setLength(length)
            self.setTiming(timing)
        elif self.move_action == MOVERIGHT:
            delta = int((event.pos().x()-self.rect.right())/self.unit)
            length = self.length+delta
            if length < 1:
                length = 1
            if length > 7:
                length = 7
            self.setLength(length)
        else:
            delta_x = int((event.pos().x()-self.rect.center().x())/self.unit)
            timing = self.timing+delta_x
            if timing > 7:
                timing = 7
            elif timing < 1:
                timing = 1
            self.setTiming(timing)
            delta_y = int((self.rect.center().y()-event.pos().y())/self.unit)
            accent = self.accent+delta_y
            if accent > 7:
                accent = 7
            elif accent < 0:
                accent = 0
            self.setAccent(accent)

    def mousePressEvent(self, event):
        pass

    def mouseReleaseEvent(self, event):
        self.setMoveAction(None)

    def setMoveAction(self, action):
        self.move_action = action

    def hoverMoveEvent(self, event):
        pos = event.pos()
        if QtGui.QApplication.mouseButtons() & QtCore.Qt.LeftButton: return
        for item in self.collidingItems():
            item.setZValue(0)
        self.setZValue(1)
        if self.top_rect.contains(pos):
            self.pen = self.active_pen
            self.setCursor(cursors(UpCursor))
            self.setMoveAction(MOVEUP)
        elif self.bottom_rect.contains(pos):
            self.pen = self.active_pen
            self.setCursor(cursors(DownCursor))
            self.setMoveAction(MOVEDOWN)
        elif self.rect.contains(pos):
            self.pen = self.active_pen
            if self.left_rect.contains(pos):
                self.setCursor(cursors(LeftCursor))
                self.setMoveAction(MOVELEFT)
            elif self.right_rect.contains(pos):
                self.setCursor(cursors(RightCursor))
                self.setMoveAction(MOVERIGHT)
            else:
                self.setCursor(cursors(MoveCursor))
                self.setMoveAction(MOVE)
        elif self.right_rect.contains(pos):
            self.setCursor(cursors(RightCursor))
            self.setMoveAction(MOVERIGHT)
        else:
            self.pen = self.normal_pen
            self.unsetCursor()
            self.setMoveAction(None)
        self.update()

    def hoverLeaveEvent(self, event):
        self.pen = self.normal_pen
        self.update()

    def setTiming(self, timing):
        if self.timing != timing:
            if timing == RANDOM:
                display_timing = 4
            else:
                if self.timing == RANDOM:
                    display_timing = timing-4
                else:
                    display_timing = timing
            self.setX(self.x()+(display_timing-self.timing)*self.unit)
        self.timing = timing
        if self.length == LEGATO:
            self.update_legato()
        self.update_rect()
        self.prepareGeometryChange()
        self.timingChanged.emit(self.timing)

    def setLength(self, length):
        self.length = length
        if length == LEGATO:
            self.update_legato()
        else:
#            self.display_length = length
            self.rect.setWidth(length*self.unit)
        self.update_rect()
        self.lengthChanged.emit(self.length)

    def setAccent(self, accent):
        if accent > 7:
            accent = 7
        elif accent < 0:
            accent = 0
        self.accent = accent
        if accent >= 4:
            self.rect.setTop(35-self.unit*(accent-4))
            self.rect.setBottom(45)
        elif accent >= 0:
            self.rect.setTop(35)
            self.rect.setBottom(85-self.unit*accent)
        if accent == 0:
            self.normal_pen = self.silent_pen
            self.brush = self.silent_brush
        else:
            self.normal_pen = self.default_pen
            self.brush = self.normal_brush
        
        if self.move_action is None:
            self.pen = self.normal_pen
        self.update_rect()
        self.accentChanged.emit(self.accent)

    def update_rect(self):
        top = self.rect.top()
        bottom = self.rect.bottom()
        self.top_rect.moveBottom(top)
        self.bottom_rect.moveTop(bottom)
        self.left_rect.moveLeft(self.rect.left())
        self.left_rect.setTop(top)
        self.left_rect.setBottom(bottom)
        if self.length in [1, 2]:
            self.left_rect.setWidth(5)
            self.right_rect.moveLeft(self.rect.right())
        else:
            self.left_rect.setWidth(10)
            self.right_rect.moveRight(self.rect.right())
        self.right_rect.setTop(top)
        self.right_rect.setBottom(bottom)
        self.update()

    def setNext(self, item):
        item.timingChanged.connect(self.update_legato)
        self.next = item

    def update_legato(self, _=None):
        if self.length != LEGATO or self.next is None: return
        if self.next.timing == 0:
            next_timing = 4
        else:
            next_timing = self.next.timing
        self.rect.setWidth((7-self.timing+next_timing)*self.unit)
        self.update()

    def paint(self, painter, *args, **kwargs):
#        painter.drawRect(self.boundingRect())
#        painter.drawRect(self.right_rect)
        painter.setPen(self.pen)
        painter.setBrush(self.brush)
        painter.setRenderHints(QtGui.QPainter.Antialiasing)
        painter.drawRect(self.rect)

class StepLine(BaseDisplayWidget):
    def __init__(self, parent, short=False):
        BaseDisplayWidget.__init__(self, parent)
        self.pen = QtGui.QPen(self.pen)
        self.pen.setStyle(QtCore.Qt.DotLine)
        self.setSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Expanding)
        self.setMaximumWidth(3)
        if short:
            self.paint = self.paintShort

    def paintShort(self, painter, *args, **kwargs):
        painter.setPen(self.pen)
        painter.drawLine(0, 10, 0, self.rect().height()-15)

    def paint(self, painter, *args, **kwargs):
        painter.setPen(self.pen)
        painter.drawLine(0, 0, 0, self.rect().height())

class FakeObject(QtCore.QObject):
    valueChanged = QtCore.pyqtSignal(int)
    def __init__(self, parent):
        self.main = parent
        self.value = 0
        QtCore.QObject.__init__(self, parent)

    def _setValue(self, value):
        self.value = value
        self.main.blockSignals(True)
        self.valueChanged.emit(value)
        self.main.blockSignals(False)

class ArpEditor(QtGui.QGraphicsView):
    border_grad = QtGui.QConicalGradient(QtCore.QPointF(.5, .5), 45)
    border_grad.setCoordinateMode(QtGui.QConicalGradient.ObjectBoundingMode)
    _up = QtGui.QColor(80, 80, 80)
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
    bgd_brush = QtGui.QBrush(QtGui.QColor(240, 250, 250))
    timing_pen = QtGui.QPen(QtCore.Qt.black, 2)
    timing_pen.setStyle(QtCore.Qt.DotLine)
    scene_rect = QtCore.QRectF(0, 0, 1150, 120)

    def __init__(self, parent):
        QtGui.QGraphicsView.__init__(self, parent)
        self.main = parent
        self.setFrameStyle(0)
        self.scene = QtGui.QGraphicsScene(self)
        self.setRenderHints(QtGui.QPainter.Antialiasing)
        self.setScene(self.scene)
        self.setStyleSheet('background: transparent')
        self.create_layout()
        self.setMinimumSize(600, 160)
        self.setSizePolicy(QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.MinimumExpanding)

        for step in range(16):
            step_object = FakeObject(self)
            step_object.valueChanged.connect(lambda value, step=step: self.step_type_list[step]._setCurrentIndex(value))
            parent.object_dict['Arp_Pattern_Step_Glide_Accent_{}'.format(step+1)].add(step_object, 'Step')
            glide_object = FakeObject(self)
            glide_object.valueChanged.connect(lambda state, step=step: self.glide_list[step]._setState(state))
            parent.object_dict['Arp_Pattern_Step_Glide_Accent_{}'.format(step+1)].add(glide_object, 'Glide')
            accent_object = FakeObject(self)
            accent_object.valueChanged.connect(lambda value, step=step: self.step_list[step].setAccent(value))
            parent.object_dict['Arp_Pattern_Step_Glide_Accent_{}'.format(step+1)].add(accent_object, 'Accent')
            timing_object = FakeObject(self)
            timing_object.valueChanged.connect(lambda value, step=step: self.step_list[step].setTiming(value))
            parent.object_dict['Arp_Pattern_Timing_Length_{}'.format(step+1)].add(timing_object, 'Timing')
            length_object = FakeObject(self)
            length_object.valueChanged.connect(lambda value, step=step: self.step_list[step].setLength(value))
            parent.object_dict['Arp_Pattern_Timing_Length_{}'.format(step+1)].add(length_object, 'Length')
#        self.valueChanged.connect(lambda value: setattr(self.main, self.attr, value))
#        parent.object_dict[attr].add(self, sub_par)
#        self.indexChanged.connect(lambda id: setattr(self.main, self.attr, id if sub_par is None else (id, sub_par)))


    def create_layout(self):
        self.step_list = []
        self.step_type_list = []
        self.accent_list = []
        self.length_list = []
        self.timing_list = []
        self.glide_list = []

        panel = QtGui.QGraphicsWidget()
        self.panel = panel
        panel.setContentsMargins(0, 0, 0, 0)
        self.scene.addItem(panel)
        layout = QtGui.QGraphicsGridLayout()
        self.layout = layout
        layout.setRowMinimumHeight(1, 60)
        panel.setLayout(layout)
        arp_widget = QtGui.QGraphicsWidget()
        self.arp_widget = arp_widget
        self.scene.addItem(arp_widget)
        arp_widget.setTransform(QtGui.QTransform.fromScale(.4, 60/90.))

        step_item = None
        for step in range(16):
            prev_item = step_item
            step_item = ArpStepWidget(arp_widget)
            if prev_item is not None:
                prev_item.setNext(step_item)
            step_item.accentChanged.connect(lambda v, step=step: self.step_accent_change(step, v))
            step_item.lengthChanged.connect(lambda v, step=step: self.step_length_change(step, v))
            step_item.timingChanged.connect(lambda v, step=step: self.step_timing_change(step, v))
            self.step_list.append(step_item)
#            self.scene.addItem(step_item)
            step_item.setX(step_item.size().width()*(step+1))
        first_item = self.step_list[0]
        self.reference_step = first_item
        step_item.setNext(first_item)
        last_item = step_item

        first_fake_item = ArpStepWidget(arp_widget)
#        first_fake_item.boundingRect = lambda: QtCore.QRectF(20, 0, 40, first_fake_item.shape_size.height())
#        self.scene.addItem(first_fake_item)
        first_fake_item.setNext(first_item)
        first_fake_item.setEnabled(False)
        first_fake_item.setX(first_item.x()-first_item.size().width())
        first_fake_item.setOpacity(.2)
        last_item.accentChanged.connect(first_fake_item.setAccent)
        last_item.lengthChanged.connect(first_fake_item.setLength)
        last_item.timingChanged.connect(first_fake_item.setTiming)

        last_fake_item = ArpStepWidget(arp_widget)
#        self.scene.addItem(last_fake_item)
        last_fake_item.setNext(first_item)
        last_fake_item.setEnabled(False)
        last_fake_item.setX(last_item.size().width()+last_item.x())
        last_fake_item.setOpacity(.2)
        first_item.accentChanged.connect(last_fake_item.setAccent)
        first_item.lengthChanged.connect(last_fake_item.setLength)
        first_item.timingChanged.connect(last_fake_item.setTiming)

        step_lbl = SmallLabelTextWidget('Step', panel, fixed=True, font_size=10)
        layout.addItem(step_lbl, 2, 0)
        layout.addItem(SmallLabelTextWidget('Glide', panel, fixed=True, font_size=10), 3, 0)
        layout.addItem(SmallLabelTextWidget('Accent', panel, fixed=True, font_size=10), 4, 0)
        layout.addItem(SmallLabelTextWidget('Timing', panel, fixed=True, font_size=10), 5, 0)
        layout.addItem(SmallLabelTextWidget('Length', panel, fixed=True, font_size=10), 6, 0)

        for step in range(16):
            col = step + 1

            is_downbeat = False if divmod(step, 4)[1] != 0 else True
            step_n = SmallLabelTextWidget(str(col), panel, font_size=9, bold=is_downbeat)
            layout.addItem(step_n, 0, col)

            step_line = StepLine(panel, short=not is_downbeat)
            layout.addItem(step_line, 1, col)

            step_combo = StepTypeCombo(panel, step, self.step_type_list)
            step_combo.currentIndexChanged.connect(lambda step_type, step=step: self.step_type_change(step, step_type))
            self.step_type_list.append(step_combo)
            layout.addItem(step_combo, 2, col)

            glide_btn = GlideDisplayButton(panel, step, self.glide_list)
            glide_btn.toggled.connect(lambda glide, step=step: self.step_glide_change(step, glide))
            self.glide_list.append(glide_btn)
            layout.addItem(glide_btn, 3, col)

            accent_combo = AccentCombo(panel, step, self.accent_list)
            accent_combo.currentIndexChanged.connect(lambda accent, step=step: self.step_list[step].setAccent(accent))
            self.step_list[step].accentChanged.connect(lambda accent, combo=accent_combo: combo._setCurrentIndex(accent))
            self.accent_list.append(accent_combo)
            layout.addItem(accent_combo, 4, col)

            timing_combo = TimingCombo(panel, step, self.timing_list)
            timing_combo.currentIndexChanged.connect(lambda timing, step=step: self.step_list[step].setTiming(timing))
            self.step_list[step].timingChanged.connect(lambda timing, combo=timing_combo: combo._setCurrentIndex(timing))
            self.timing_list.append(timing_combo)
            layout.addItem(timing_combo, 5, col)

            length_combo = LengthCombo(panel, step, self.length_list)
            length_combo.currentIndexChanged.connect(lambda timing, step=step: self.step_list[step].setLength(timing))
            self.step_list[step].lengthChanged.connect(lambda timing, combo=length_combo: combo._setCurrentIndex(timing))
            self.length_list.append(length_combo)
            layout.addItem(length_combo, 6, col)

        self.bound_ref = step_lbl, length_combo
        self.size_ref = layout.itemAt(2, 1), layout.itemAt(2, 2)

        self.panel_shadow = QtGui.QGraphicsDropShadowEffect()
        self.panel_shadow.setBlurRadius(4)
        self.panel_shadow.setOffset(1, 1)
        self.panel_shadow.setColor(QtGui.QColor(100, 100, 100, 150))
        self.panel.setGraphicsEffect(self.panel_shadow)

        self.arp_shadow = QtGui.QGraphicsDropShadowEffect()
        self.arp_shadow.setBlurRadius(4)
        self.arp_shadow.setOffset(1, 1)
        self.arp_shadow.setColor(QtGui.QColor(100, 100, 100, 150))
        self.arp_widget.setGraphicsEffect(self.arp_shadow)

    def boundaries(self):
        return QtCore.QRectF(self.bound_ref[0].x(), 0, self.bound_ref[1].x()+self.bound_ref[1].boundingRect().width(), self.bound_ref[1].y()+self.bound_ref[1].boundingRect().height())

    def step_ratio(self):
        diff = self.size_ref[1].x()-self.size_ref[0].x()
        return diff/self.reference_step.boundingRect().width()

    def step_accent_change(self, step, accent):
        if not self.signalsBlocked():
            setattr(self.main, 'Arp_Pattern_Step_Glide_Accent_{}'.format(step+1), (accent, 'Accent'))

    def step_length_change(self, step, length):
        if not self.signalsBlocked():
            setattr(self.main, 'Arp_Pattern_Timing_Length_{}'.format(step+1), (length, 'Length'))

    def step_timing_change(self, step, timing):
        if not self.signalsBlocked():
            setattr(self.main, 'Arp_Pattern_Timing_Length_{}'.format(step+1), (timing, 'Timing'))

    def step_type_change(self, step, step_type):
        if not self.signalsBlocked():
            setattr(self.main, 'Arp_Pattern_Step_Glide_Accent_{}'.format(step+1), (step_type, 'Step'))

    def step_glide_change(self, step, glide):
        if not self.signalsBlocked():
            setattr(self.main, 'Arp_Pattern_Step_Glide_Accent_{}'.format(step+1), (glide, 'Glide'))

    def paintEvent(self, event):
        qp = QtGui.QPainter(self.viewport())
        qp.setRenderHints(QtGui.QPainter.Antialiasing)
        qp.translate(.5, .5)
        qp.setPen(self.border_pen)
        qp.setBrush(self.bgd_brush)
        qp.drawRoundedRect(self.border_rect, 4, 4)
        qp.end()
        QtGui.QGraphicsView.paintEvent(self, event)

    def resizeEvent(self, event):
        width = self.width()
        height = self.height()
        self.border_rect = QtCore.QRect(0, 0, width-1, height-1)
#        self.display_rect = self.border_rect.adjusted(2, 2, -2, -2)
        self.panel.setGeometry(QtCore.QRectF(0, 0, width-2, height-2))
        self.panel.layout().setGeometry(QtCore.QRectF(0, -10, width-2, height-2))
        self.arp_widget.setY(self.layout.itemAt(1, 1).y())
        self.scene.setSceneRect(self.boundaries())
        ratio = self.step_ratio()
        self.arp_widget.setTransform(QtGui.QTransform.fromScale(ratio, 60/90.))
        self.arp_widget.setX(self.layout.itemAt(1, 1).x()-self.reference_step.x()*ratio)
        self.update()

class MidiInDisplayButton(DisplayButton):
    path = QtGui.QPainterPath()
    path.moveTo(0, 3)
    path.lineTo(5, 3)
    path.arcMoveTo(3, 0, 5.5, 6, 135)
    path.arcTo(3, 0, 5.5, 6, 135, -270)
#    path.translate(.5, 0)
    type_txt = 'input'
    def __init__(self, parent):
        self.font = QtGui.QFont('Fira Sans', 11, QtGui.QFont.Light)
        self.font_metrics = QtGui.QFontMetrics(self.font)
        self.text = '0'
        DisplayButton.__init__(self, parent)
        self.normal_frame_border_pen = self.normal_frame_border_pen.lighter(105)
        self.normal_frame_border_brush = self.normal_frame_border_brush.lighter(125)
        self.frame_border_pen = self.normal_frame_border_pen
        self.frame_border_brush = self.normal_frame_border_brush
        self.setSizePolicy(QtGui.QSizePolicy.Maximum, QtGui.QSizePolicy.Maximum)
        self.setMinimumHeight(max(self.path.boundingRect().height(), self.font_metrics.height()))
        self.setMaximumWidth(self.path.boundingRect().width()+self.font_metrics.width('0')*3+4)
        self.setAcceptHoverEvents(False)
        self.brush = self.off_brush
        self.setConn(0)

    def setConn(self, conn):
        self.text = str(conn)
        if conn:
            if conn > 1:
                tooltip = 'MIDI {} connected to {} ports'.format(self.type_txt, conn)
            else:
                tooltip = 'MIDI {} connected to 1 port'.format(self.type_txt)
            self.pen = self.on_pen
            self.text_pen = self.on_pen
        else:
            tooltip = 'MIDI {} not connected'.format(self.type_txt)
            self.pen = self.off_pen
            self.text_pen = self.off_pen
        self.setToolTip(tooltip)
        self.update()

class MidiOutDisplayButton(MidiInDisplayButton):
    path = QtGui.QPainterPath()
    path.arcMoveTo(0, 0, 5.5, 6, 45)
    path.arcTo(0, 0, 5.5, 6, 45, 270)
    path.moveTo(4, 3)
    path.lineTo(8, 3)
    type_txt = 'output'

class MidiDisplayButton(DisplayButton):
    def __init__(self, parent):
        self.path = QtGui.QPainterPath()
        self.path.addEllipse(0, 0, 11, 11)
        self.path.addEllipse(2, 5, .5, .5)
        self.path.addEllipse(2.878, 2.878, .5, .5)
        self.path.addEllipse(5.25, 2, .5, .5)
        self.path.addEllipse(7.878, 2.878, .5, .5)
        self.path.addEllipse(9, 5, .5, .5)
        self.font = QtGui.QFont('Fira Sans', 11, QtGui.QFont.Light)
        self.font_metrics = QtGui.QFontMetrics(self.font)
        self.text = 'MIDI'
        DisplayButton.__init__(self, parent)
#        self._setState(False)
        self.brush = self.off_brush
        self.normal_frame_border_pen = self.normal_frame_border_pen.lighter(105)
        self.normal_frame_border_brush = self.normal_frame_border_brush.lighter(125)
        self.focus_frame_border_brush = self.focus_frame_border_brush.lighter(125)
        self.frame_border_pen = self.normal_frame_border_pen
        self.frame_border_brush = self.normal_frame_border_brush
        self.setSizePolicy(QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.Maximum)
        self.setMinimumHeight(max(self.path.boundingRect().height(), self.font_metrics.height()))
#        self.setMaximumHeight(32)
        self.setToolTip('Open MIDI connections dialog\n(right click for direct access menu)')
        self.led_timer = QtCore.QTimer()
        self.led_timer.setSingleShot(True)
        self.led_timer.setInterval(256)
        self.led_timer.timeout.connect(self.reset)
        self.midi_in_pen = QtGui.QPen(QtCore.Qt.darkRed)

    def setState(self, state):
        pass

    def reset(self):
        self.pen = self.off_pen
        self.update()

    def midi_out(self):
        self.pen = self.on_pen
        self.led_timer.start()
        self.update()

    def midi_in(self):
        self.pen = self.midi_in_pen
        self.led_timer.start()
        self.update()

class BlofeldDisplay(QtGui.QGraphicsView):
    border_grad = QtGui.QConicalGradient(QtCore.QPointF(.5, .5), 45)
    border_grad.setCoordinateMode(QtGui.QConicalGradient.ObjectBoundingMode)
    _up = QtGui.QColor(80, 80, 80)
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
    bgd_brush = QtGui.QBrush(QtGui.QColor(240, 250, 250))
    frame_border_pen = QtGui.QColor(220, 220, 220, 220)
    frame_border_brush = QtGui.QColor(220, 220, 220, 120)

    def __init__(self, parent):
        QtGui.QGraphicsView.__init__(self, parent)
        self.main = parent
        self.setFrameStyle(0)
        self.scene = QtGui.QGraphicsScene(self)
        self.setScene(self.scene)
        self.setStyleSheet('background: transparent')
        self.shadow = QtGui.QGraphicsDropShadowEffect()
        self.shadow.setBlurRadius(4)
        self.shadow.setOffset(1, 1)
        self.shadow.setColor(QtGui.QColor(100, 100, 100, 150))
        self.create_layout()
        self.setSizePolicy(QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.Preferred)

        for char in range(16):
            char_object = FakeObject(self)
            char_object.valueChanged.connect(lambda value, char=char: self.prog_name.setChar(char, value))
            parent.object_dict['Name_Char_{:02}'.format(char)].add(char_object)
        cat_object = FakeObject(self)
        cat_object.valueChanged.connect(lambda value: self.cat_name.setCat(value))
        parent.object_dict['Category'].add(cat_object)

    def create_layout(self):
        panel = QtGui.QGraphicsWidget()
        self.panel = panel
        self.scene.addItem(panel)
        layout = QtGui.QGraphicsGridLayout()
        layout.setSpacing(0)
        panel.setLayout(layout)
        layout.setColumnSpacing(0, 4)
        layout.setColumnSpacing(1, 8)

        side = QtGui.QGraphicsGridLayout()
        side.setVerticalSpacing(1)
        side.setHorizontalSpacing(2)
        side.setSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Maximum)
        layout.addItem(side, 0, 1, 3, 1, QtCore.Qt.AlignVCenter)

        bank_layout = QtGui.QGraphicsGridLayout()
        self.bank_layout = bank_layout
        side.addItem(bank_layout, 0, 0)
        bank_label = SmallLabelTextWidget('Bank', panel, fixed=True)
        bank_layout.addItem(bank_label, 0, 0, 1, 2, QtCore.Qt.AlignHCenter)
        self.bank = BankTextWidget(panel)
        bank_layout.addItem(self.bank, 1, 0, QtCore.Qt.AlignVCenter)
        bank_arrows = QtGui.QGraphicsGridLayout()
        bank_layout.addItem(bank_arrows, 1, 1, QtCore.Qt.AlignRight)
        self.bank_up = UpArrowWidget(panel)
        bank_arrows.addItem(self.bank_up, 0, 0)
        self.bank_dn = DownArrowWidget(panel)
        bank_arrows.addItem(self.bank_dn, 1, 0)

        bp_spacer = DisplayHSpacer(panel)
#        bp_spacer.setMaximumWidth(10)
        bp_spacer.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
        side.addItem(bp_spacer, 0, 1)

        prog_layout = QtGui.QGraphicsGridLayout()
        self.prog_layout = prog_layout
        side.addItem(prog_layout, 0, 2)
        prog_label = SmallLabelTextWidget('Prog', panel, fixed=True)
        prog_layout.addItem(prog_label, 0, 1, 1, 2, QtCore.Qt.AlignHCenter)
        prog_spacer = DisplayHSpacer(panel)
        prog_layout.addItem(prog_spacer, 1, 0)
        self.prog = ProgTextWidget(panel)
        prog_layout.addItem(self.prog, 1, 1, QtCore.Qt.AlignVCenter)
        prog_arrows = QtGui.QGraphicsGridLayout()
        prog_layout.addItem(prog_arrows, 1, 2, QtCore.Qt.AlignRight)
        self.prog_up = UpArrowWidget(panel)
        prog_arrows.addItem(self.prog_up, 0, 0)
        self.prog_dn = DownArrowWidget(panel)
        prog_arrows.addItem(self.prog_dn, 1, 0)

        side.addItem(DisplayVSpacer(panel, 10), 4, 0)

        cat_layout = QtGui.QGraphicsGridLayout()
        self.cat_layout = cat_layout
        cat_layout.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Maximum)
        side.addItem(cat_layout, 5, 0, 1, 3)

        self.cat_label = SmallLabelTextWidget('Cat: ', panel, fixed=True)
        cat_layout.addItem(self.cat_label, 0, 0, QtCore.Qt.AlignHCenter|QtCore.Qt.AlignVCenter)
        cat_spacer = DisplayHSpacer(panel)
        cat_spacer.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
        cat_layout.addItem(cat_spacer, 0, 1)
        self.cat_name = CatTextWidget(panel)
        cat_layout.addItem(self.cat_name, 0, 2, QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter)
        cat_arrows = QtGui.QGraphicsGridLayout()
        cat_layout.addItem(cat_arrows, 0, 3, QtCore.Qt.AlignRight)
        self.cat_up = UpArrowWidget(panel)
        cat_arrows.addItem(self.cat_up, 0, 0)
        self.cat_dn = DownArrowWidget(panel)
        cat_arrows.addItem(self.cat_dn, 1, 0)

        self.edit_mode_label = SmallLabelTextWidget('Sound mode Edit buffer', panel)
#        self.edit_mode_label.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        layout.addItem(self.edit_mode_label, 0, 2)
        self.prog_name = ProgLabelTextWidget('Mini moog super', panel)
        layout.addItem(self.prog_name, 1, 2)

        self.status_bar = QtGui.QGraphicsGridLayout()
        layout.addItem(self.status_bar, 2, 2, 1, 2)
        status_lbl = SmallLabelTextWidget('Status:', panel, fixed=True)
        self.status_bar.addItem(status_lbl, 0, 0, QtCore.Qt.AlignLeft)

        self.status = SmallLabelTextWidget('Ready', panel)
        self.status_bar.addItem(self.status, 0, 1, QtCore.Qt.AlignLeft)

        buttons_layout = QtGui.QGraphicsGridLayout()
        layout.addItem(buttons_layout, 0, 3, 2, 1)
        self.midi_btn = MidiDisplayButton(panel)
        buttons_layout.addItem(self.midi_btn, 0, 0, 1, 2)
        self.midi_in = MidiInDisplayButton(panel)
        buttons_layout.addItem(self.midi_in, 1, 0)
        self.midi_out = MidiOutDisplayButton(panel)
        buttons_layout.addItem(self.midi_out, 1, 1)
        spacer = DisplayVSpacer(panel)
        spacer.setMaximumHeight(1000)
        spacer.setSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Maximum)
        buttons_layout.addItem(spacer, 2, 0)

        self.panel.setGraphicsEffect(self.shadow)

    def mouseReleaseEvent(self, event):
        item = self.scene.itemAt(event.pos())
        if item is None: return
        if isinstance(item, MidiDisplayButton):
            self.main.show_midi_dialog.emit()
#            QtGui.QGraphicsView.mouseReleaseEvent(self, event)
            return
        sound = self.main.sound
        bank = sound.bank
        prog = sound.prog
        cat = sound.cat
        if item == self.bank_dn:
            bank -= 1
            if bank < 0: return
        elif item == self.bank_up:
            bank += 1
            if bank > 7: return
        elif item == self.prog_dn:
            prog -= 1
            if prog < 0:
                if bank > 1:
                    bank -= 1
                    prog = 127
                else: return
        elif item == self.prog_up:
            prog += 1
            if prog > 127:
                if bank < 7:
                    bank += 1
                    prog = 0
                else: return
        elif item == self.cat_up:
            while True:
                if cat >= len(categories)-1: return
                cat_list = self.main.blofeld_library.sorted.by_cat[cat+1]
                if not len(cat_list):
                    cat += 1
                    continue
                else:
                    sound = cat_list[0]
                    break
            bank = sound.bank
            prog = sound.prog
        elif item == self.cat_dn:
            while True:
                if cat < 1: return
                cat_list = self.main.library.sorted.by_cat[cat-1]
                if not len(cat_list):
                    cat -= 1
                    continue
                else:
                    sound = cat_list[0]
                    break
            bank = sound.bank
            prog = sound.prog
        else:
            return
        self.main.setSound(bank, prog, pgm_send=True)

    def contextMenuEvent(self, event):
        item = self.scene.itemAt(event.pos())
        if item == self.midi_btn:
            self.show_midi_menu(event.pos())
            return
        elif item == self.midi_in:
            self.show_midi_menu(event.pos(), output=False)
            return
        elif item == self.midi_out:
            self.show_midi_menu(event.pos(), input=False)
            return
        bank = self.main.sound.bank
        if item == self.prog_name:
            res = self.main.blofeld_library.menu.exec_(event.globalPos())
            if not res: return
            self.main.setSound(*res.data().toPyObject(), pgm_send=True)
            return
        elif self.bank_rect.contains(event.pos()):
            res = self.main.blofeld_library.menu.actions()[0].menu().exec_(event.globalPos())
            if not res: return
            self.main.setSound(*res.data().toPyObject(), pgm_send=True)
            return
        elif self.prog_rect.contains(event.pos()):
            res = self.main.blofeld_library.menu.actions()[0].menu().actions()[bank].menu().exec_(event.globalPos())
            if not res: return
            self.main.setSound(*res.data().toPyObject(), pgm_send=True)
            return
        elif self.cat_rect.contains(event.pos()):
            res = self.main.blofeld_library.menu.actions()[1].menu().exec_(event.globalPos())
            if not res: return
            self.main.setSound(*res.data().toPyObject(), pgm_send=True)
            return

    def wheelEvent(self, event):
        item = self.scene.itemAt(event.pos())
        if item is None: return
        sound = self.main.sound
        bank = sound.bank
        prog = sound.prog
        cat = sound.cat
        delta = 1 if event.delta() > 0 else -1
        if item in [self.prog_name, self.prog]:
            prog += delta
            if prog < 0:
                if bank > 1:
                    bank -= 1
                    prog = 127
                else: return
            elif prog > 127:
                if bank < 7:
                    bank += 1
                    prog = 0
                else: return
        elif item == self.bank:
            bank += delta
            if not 0 <= bank <= 7: return
        elif item == self.cat_name:
            cat += delta
            while True:
                if not 0 <= cat <= len(categories)-1: return
                cat_list = self.main.blofeld_library.sorted.by_cat[cat]
                if not len(cat_list):
                    cat += delta
                    continue
                else:
                    sound = cat_list[0]
                    break
            bank = sound.bank
            prog = sound.prog
        else:
            return
        self.main.setSound(bank, prog, pgm_send=True)

    def show_midi_menu(self, pos, input=True, output=True):
        menu = QtGui.QMenu()

        in_menu = QtGui.QMenu()
        in_disconnect = QtGui.QAction('Disconnect all', in_menu)
        in_menu.addAction(in_disconnect)
        menu.addMenu(in_menu)

        out_menu = QtGui.QMenu()
        out_disconnect = QtGui.QAction('Disconnect all', out_menu)
        out_menu.addAction(out_disconnect)
        menu.addMenu(out_menu)

        in_clients = False
        out_clients = False
        in_menu_connections = 0
        out_menu_connections = 0
        for client in [self.main.alsa.graph.client_id_dict[cid] for cid in sorted(self.main.alsa.graph.client_id_dict.keys())]:
            in_port_list = []
            out_port_list = []
            for port in client.ports:
                if port.hidden or port.client == self.main.input.client:
                    continue
                if port.is_output:
                    in_port_list.append(port)
                if port.is_input:
                    out_port_list.append(port)
            if in_port_list:
                in_clients = True
                client_menu = QtGui.QMenu(client.name, menu)
                in_menu.addMenu(client_menu)
                for port in in_port_list:
                    port_item = QtGui.QAction(port.name, in_menu)
                    port_item.setData(port)
                    port_item.setCheckable(True)
                    if any([True for conn in port.connections.output if conn.dest==self.main.alsa.input]):
                        port_item.setChecked(True)
                        setBold(client_menu.menuAction())
                        in_menu_connections += 1
                    client_menu.addAction(port_item)
            if out_port_list:
                out_clients = True
                client_menu = QtGui.QMenu(client.name, menu)
                out_menu.addMenu(client_menu)
                for port in out_port_list:
                    port_item = QtGui.QAction(port.name, out_menu)
                    port_item.setData(port)
                    port_item.setCheckable(True)
                    if any([True for conn in port.connections.input if conn.src==self.main.alsa.output]):
                        port_item.setChecked(True)
                        setBold(client_menu.menuAction())
                        out_menu_connections += 1
                    client_menu.addAction(port_item)
        if not in_clients:
            in_menu.setTitle('Input (no clients)')
            in_menu.setEnabled(False)
        else:
            in_menu.setTitle('Input ({})'.format(in_menu_connections))
        if not out_clients:
            out_menu.setTitle('Output (no clients)')
            out_menu.setEnabled(False)
        else:
            out_menu.setTitle('Output ({})'.format(out_menu_connections))

        if not in_menu_connections:
            in_disconnect.setEnabled(False)
        if not out_menu_connections:
            out_disconnect.setEnabled(False)

        if input and output:
            res = menu.exec_(self.mapToGlobal(pos))
        elif input:
            res = in_menu.exec_(self.mapToGlobal(pos))
        else:
            res = out_menu.exec_(self.mapToGlobal(pos))

        if not res: return
        if res == in_disconnect:
            for conn in self.main.input.connections:
                if conn.hidden: continue
                conn.delete()
        elif res == out_disconnect:
            for conn in self.main.output.connections:
                if conn.hidden: continue
                conn.delete()
        elif res.parent() == in_menu:
            port = res.data().toPyObject()
            if res.isChecked():
                port.connect(self.main.input)
            else:
                port.disconnect(self.main.input)
        elif res.parent() == out_menu:
            port = res.data().toPyObject()
            if res.isChecked():
                self.main.output.connect(port)
            else:
                self.main.output.disconnect(port)

    def paintEvent(self, event):
        qp = QtGui.QPainter(self.viewport())
        qp.setRenderHints(QtGui.QPainter.Antialiasing)
        qp.translate(.5, .5)
        qp.setPen(self.border_pen)
        qp.setBrush(self.bgd_brush)
        qp.drawRoundedRect(self.border_rect, 4, 4)
        qp.setPen(self.frame_border_pen)
        qp.setBrush(self.frame_border_brush)
        qp.drawRoundedRect(self.cat_rect, 4, 4)
        qp.drawRoundedRect(self.bank_rect, 4, 4)
        qp.drawRoundedRect(self.prog_rect, 4, 4)
        qp.end()
        QtGui.QGraphicsView.paintEvent(self, event)

    def resizeEvent(self, event):
        width = self.width()
        height = self.height()
        self.panel.layout().setGeometry(QtCore.QRectF(0, 0, width-2, height-2))
        self.border_rect = QtCore.QRect(0, 0, width-1, height-1)
        self.display_rect = self.border_rect.adjusted(2, 2, -2, -2)
        self.setSceneRect(0, 0, width-1, height-1)
        bank_geo = self.bank_layout.geometry()
        self.bank_rect = QtCore.QRectF(bank_geo.x()-3, bank_geo.y()-1, bank_geo.width()+6, bank_geo.height()+4)
        prog_geo = self.prog_layout.geometry()
        self.prog_rect = QtCore.QRectF(prog_geo.x()-3, prog_geo.y()-1, prog_geo.width()+6, prog_geo.height()+4)
        cat_geo = self.cat_layout.geometry()
        self.cat_rect = QtCore.QRectF(cat_geo.x()-5, cat_geo.y()-2, cat_geo.width()+7, cat_geo.height()+4)

    def statusParamUpdate(self, attr, value):
        param = Params.param_from_attr(attr)
        if isinstance(param.values, AdvParam):
            value = list(reversed(param.values[getattr(self.main, attr)]))[param.values.named_kwargs.index(value[1])]
        else:
            value = param.values[(value-param.range[0])/param.range[2]]
        self.statusUpdate('{} changed: {}'.format(param.name, value))

    def statusUpdate(self, text):
        self.status.text = QtCore.QString.fromUtf8(text)
        self.update()
        self.panel.update()

    def setSound(self):
        sound = self.main.sound
#        self.prog_name.text = sound.name
        self.bank.text = uppercase[sound.bank]
        self.prog.text = '{:03}'.format(sound.prog+1)
#        self.cat_name.text = categories[sound.cat]
        self.update()
        self.panel.update()

class Editor(QtGui.QMainWindow):
    midi_event = QtCore.pyqtSignal(object)
    program_change = QtCore.pyqtSignal(int, int)
    midi_receive = QtCore.pyqtSignal(bool)
    pgm_receive = QtCore.pyqtSignal(bool)
    midi_send = QtCore.pyqtSignal(bool)
    pgm_send = QtCore.pyqtSignal(bool)
    show_midi_dialog = QtCore.pyqtSignal()
    show_librarian = QtCore.pyqtSignal()

    object_dict = {attr:ParamObject(param_tuple) for attr, param_tuple in Params.param_names.items()}
    with open(local_path('blofeld_efx'), 'rb') as _fx:
        efx_params = pickle.load(_fx)
    with open(local_path('blofeld_efx_ranges'), 'rb') as _fx:
        efx_ranges = pickle.load(_fx)

    def __init__(self, main):
        QtGui.QMainWindow.__init__(self, parent=None)
        load_ui(self, 'editor.ui')
        self.setContentsMargins(2, 2, 2, 2)
        pal = self.palette()
        pal.setColor(self.backgroundRole(), QtGui.QColor(20, 20, 20))
        self.setPalette(pal)

        self.main = main
        self.blofeld_library = self.main.blofeld_library
        self.alsa = self.main.alsa
        self.input = self.alsa.input
        self.output = self.alsa.output
        self.graph = self.main.graph
        self.channel = 0
        self.octave = 0
        self.params = Params
        self.send = False
        self.notify = True
        self.envelopes = []
        self.grid = self.centralWidget().layout()

        self.grid.addWidget(self.create_mixer(), 0, 0, 2, 1)

        display_layout = QtGui.QGridLayout()
        self.grid.addLayout(display_layout, 0, 1, 1, 2)
        display_layout.addLayout(self.create_display(), 0, 0, 2, 1)
        display_layout.addWidget(HSpacer(max_width=24), 0, 1)


        side_layout = QtGui.QGridLayout()
        display_layout.addLayout(side_layout, 1, 2)

        library_btn = SquareButton(self, color=QtCore.Qt.darkGreen, name='Library')
        library_btn.clicked.connect(self.show_librarian)
        side_layout.addWidget(library_btn)

        randomize_btn = SquareButton(self, color=QtCore.Qt.darkGreen, name='Randomize')
        randomize_btn.clicked.connect(self.randomize)
        side_layout.addWidget(randomize_btn, 0, 1)

        logo = QtGui.QIcon(local_path('logo.svg')).pixmap(QtCore.QSize(160, 160)).toImage()
        logo_widget = QtGui.QLabel()
        logo_widget.setPixmap(QtGui.QPixmap().fromImage(logo))
        logo_widget.setSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        logo_widget.setToolTip('Right click here for...')
        logo_widget.contextMenuEvent = self.menuEvent
        side_layout.addWidget(logo_widget, 1, 0, 1, 2, QtCore.Qt.AlignBottom|QtCore.Qt.AlignRight)

        amp_layout = QtGui.QVBoxLayout()
        amp_layout.addWidget(self.create_amplifier())
        amp_layout.addWidget(self.create_glide())
        amp_layout.addWidget(self.create_common())
        self.grid.addLayout(amp_layout, 2, 0, 2, 1)

        osc1 = self.create_osc1()
        self.grid.addWidget(osc1, 1, 1)
        osc2 = self.create_osc2()
        self.grid.addWidget(osc2, 2, 1)
        osc3 = self.create_osc3()
        self.grid.addWidget(osc3, 3, 1)
        col_max = max([self.osc1_limit_wt.width(), self.osc2_limit_wt.width(), self.osc2_sync.width()])
        btn_col = osc1.layout().getItemPosition(osc1.layout().indexOf(self.osc1_limit_wt))[1]
        for osc in (osc1, osc2, osc3):
            osc.layout().setColumnMinimumWidth(btn_col, col_max)

        self.grid.addWidget(self.create_lfo1(), 1, 2)
        self.grid.addWidget(self.create_lfo2(), 2, 2)
        self.grid.addWidget(self.create_lfo3(), 3, 2)

        filter_matrix_btn_layout = QtGui.QGridLayout()
        self.grid.addLayout(filter_matrix_btn_layout, 0, 3, 4, 2)
#        filter_matrix_widget = QtGui.QWidget()
#        filter_matrix_btn_layout.addWidget(filter_matrix_widget)
#        self.filter_matrix_layout = QtGui.QStackedLayout()
#        filter_matrix_widget.setLayout(self.filter_matrix_layout)
#        self.filter_matrix_layout.addWidget(self.create_filters())
#        self.filter_matrix_layout.addWidget(self.create_mod_widgets())

        filter_widget = self.create_filters()
        filter_matrix_btn_layout.addWidget(filter_widget)
        matrix_widget = self.create_mod_widgets()
        filter_matrix_btn_layout.addWidget(matrix_widget, 0, 0)

        btn_layout = QtGui.QHBoxLayout()
        filter_matrix_btn_layout.addLayout(btn_layout, 1, 0)
        open_mod = SquareButton(self, color=QtCore.Qt.darkGreen, size=(20, 16), name='Mod Matrix Editor', label_pos=RIGHT, text_align=QtCore.Qt.AlignLeft)
        btn_layout.addWidget(open_mod)
#        filter_matrix_lbl = Label(self, 'Mod Matrix Editor', QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
#        btn_layout.addWidget(filter_matrix_lbl)
        filter_matrix_cycle = cycle((0, 1))
        filter_matrix_cycle.next()
        filter_matrix_labels = 'Mod Matrix Editor', 'Filters'

        filter_opacity = QtGui.QGraphicsOpacityEffect()
        filter_opacity.setOpacity(1)
        filter_widget.setGraphicsEffect(filter_opacity)
        filter_widget.raise_()
        filter_opacity_anim = QtCore.QPropertyAnimation(filter_opacity, 'opacity')
        filter_opacity_anim.setDuration(200)

        matrix_opacity = QtGui.QGraphicsOpacityEffect()
        matrix_opacity.setOpacity(0)
        matrix_widget.setGraphicsEffect(matrix_opacity)
        matrix_opacity_anim = QtCore.QPropertyAnimation(matrix_opacity, 'opacity')
        matrix_opacity_anim.setDuration(200)
        filter_matrix_tuple = (filter_widget, filter_opacity_anim), (matrix_widget, matrix_opacity_anim)

        def filter_matrix_set(cycler):
            id = cycler.next()
            for i, (w, a) in enumerate(filter_matrix_tuple):
                if i == id:
                    a.setStartValue(0)
                    a.setEndValue(1)
                    a.start()
                    w.raise_()
                else:
                    a.setStartValue(1)
                    a.setEndValue(0)
                    a.start()
            open_mod.setText(filter_matrix_labels[id])

        open_mod.clicked.connect(lambda state, cycler=filter_matrix_cycle: filter_matrix_set(cycler))

        open_arp = SquareButton(self, color=QtCore.Qt.darkGreen, size=(20, 16), name='Arpeggiator Pattern Editor', label_pos=RIGHT, text_align=QtCore.Qt.AlignLeft)
        btn_layout.addWidget(open_arp)
#        adv_arp_lbl = Label(self, 'Arpeggiator Pattern Editor', QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
#        btn_layout.addWidget(adv_arp_lbl)

        adv_arp_widget = QtGui.QWidget()
        adv_arp_widget.setContentsMargins(0, 0, 0, 0)
        adv_arp_layout = QtGui.QGridLayout()
        adv_arp_layout.setContentsMargins(0, 0, 0, 0)
        adv_arp_widget.setLayout(adv_arp_layout)
        adv_arp_cycle = cycle((0, 1))
        adv_arp_cycle.next()
        adv_arp_labels = 'Arpeggiator Pattern Editor', 'Effects and Arpeggiator'

        adv_widget = QtGui.QWidget()
        adv_widget.setContentsMargins(0, 0, 0, 0)
        adv_arp_layout.addWidget(adv_widget)
        adv_layout = QtGui.QHBoxLayout()
        adv_layout.setContentsMargins(0, 0, 0, 0)
        adv_widget.setLayout(adv_layout)
        adv_layout.addWidget(self.create_effect_1())
        adv_layout.addWidget(self.create_effect_2())
        adv_layout.addWidget(self.create_arp())

        self.arp_editor = ArpEditor(self)
        arp_widget = self.arp_editor
        adv_arp_layout.addWidget(arp_widget, 0, 0)
        arp_widget.setContentsMargins(0, 0, 0, 0)
#        arp_widget.setLayout(self.create_arp_editor())

        adv_opacity = QtGui.QGraphicsOpacityEffect()
        adv_opacity.setOpacity(1)
        adv_widget.setGraphicsEffect(adv_opacity)
        adv_widget.raise_()
        adv_opacity_anim = QtCore.QPropertyAnimation(adv_opacity, 'opacity')
        adv_opacity_anim.setDuration(200)

        arp_opacity = QtGui.QGraphicsOpacityEffect()
        arp_opacity.setOpacity(0)
        arp_widget.setGraphicsEffect(arp_opacity)
        arp_opacity_anim = QtCore.QPropertyAnimation(arp_opacity, 'opacity')
        arp_opacity_anim.setDuration(200)
        adv_arp_tuple = (adv_widget, adv_opacity_anim), (arp_widget, arp_opacity_anim)

        def adv_arp_set(cycler):
            id = cycler.next()
            for i, (w, a) in enumerate(adv_arp_tuple):
                if i == id:
                    a.setStartValue(0)
                    a.setEndValue(1)
                    a.start()
                    w.raise_()
                else:
                    a.setStartValue(1)
                    a.setEndValue(0)
                    a.start()
            open_arp.setText(adv_arp_labels[id])

        open_arp.clicked.connect(lambda state, cycler=adv_arp_cycle: adv_arp_set(cycler))

        lower_layout = QtGui.QGridLayout()
        self.grid.addLayout(lower_layout, 4, 0, 1, 5)
        lower_layout.addLayout(self.create_envelopes(), 0, 0, 2, 1)

        lower_layout.addWidget(adv_arp_widget, 0, 1, 1, 2)


        self.keyboard = Piano(self, key_list=note_keys)
        self.keyboard.noteEvent.connect(self.send_note)
        lower_layout.addWidget(self.keyboard, 1, 1)
        lower_layout.addWidget(self.create_key_config(), 1, 2)
        

    def __getattr__(self, attr):
        try:
            return self.object_dict[attr].value
        except:
            raise NameError('{} attribute does not exist!'.format(attr))

    def __setattr__(self, attr, value):
        try:
            try:
                self.object_dict[attr].value = value
                if self.notify:
                    self.display.statusParamUpdate(attr, value)
                if self.send:
                    value = self.object_dict[attr].value
                    self.send_value(attr, value)
            except:
                QtCore.QObject.__setattr__(self, attr, value)
        except Exception as e:
            raise e
#            raise NameError('{} attribute does not exist!'.format(attr))

    def showEvent(self, event):
        if self.blofeld_library.menu is None:
            self.blofeld_library.create_menu()

    def menuEvent(self, event):
        menu = QtGui.QMenu()
        menu.addAction(self.main.globalsAction)
        about_item = QtGui.QAction('About Mr. Bigglesworth...', menu)
        menu.addAction(about_item)
        res = menu.exec_(event.globalPos())
        if not res: return
        elif res == about_item:
            QtGui.QMessageBox.information(self, 'Ahem...', 'Sorry, I\'m not ready yet!')

    def midi_output_state(self, conn):
        self.pgm_send_btn.setEnabled(conn)
        self.midi_send_btn.setEnabled(conn)
        self.display.midi_out.setConn(conn)

    def midi_input_state(self, conn):
        self.pgm_receive_btn.setEnabled(conn)
        self.midi_receive_btn.setEnabled(conn)
        self.display.midi_in.setConn(conn)

    def keyPressEvent(self, event):
        if event.isAutoRepeat(): return
        scancode = event.nativeScanCode()
        if scancode in note_scancodes:
            note = note_scancodes.index(scancode)+36
            self.keyboard.keys[note].push()

    def keyReleaseEvent(self, event):
        if event.isAutoRepeat(): return
        scancode = event.nativeScanCode()
        if scancode in note_scancodes:
            note = note_scancodes.index(scancode)+36
            self.keyboard.keys[note].release()

    def create_filters(self):
        container = QtGui.QWidget()
        container.setContentsMargins(-3, -3, -3, -3)
        filter_layout = QtGui.QGridLayout()
        container.setLayout(filter_layout)
        filter_layout.setRowMinimumHeight(0, 60)
        filter_layout.addWidget(self.create_filter_sel(), 0, 0, 2, 2)
        filter_layout.addWidget(self.create_filter1(), 1, 0, 1, 1)
        filter_layout.addWidget(self.create_filter2(), 1, 1, 1, 1)
        return container

    def create_key_config(self):
        def set_channel(chan):
            setattr(self, 'channel', chan)
        def set_octave(oct):
            setattr(self, 'octave', oct-2)
        frame = Frame(self)
        layout = QtGui.QGridLayout()
        frame.setLayout(layout)

        mod = Slider(self, name='MOD')
        mod.valueChanged.connect(lambda value: self.send_ctrl(1, value))
        layout.addWidget(mod, 0, 0, 3, 1)

        chan_layout = QtGui.QHBoxLayout()
        layout.addLayout(chan_layout, 0, 1)
        chan_layout.addWidget(Label(self, 'Ch'))
        channel = Combo(self, value_list=[str(c) for c in range(1, 17)])
        channel.indexChanged.connect(set_channel)
        channel.setSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        chan_layout.addWidget(channel)

        oct_layout = QtGui.QHBoxLayout()
        layout.addLayout(oct_layout, 0, 2)
        oct_layout.addWidget(Label(self, 'Oct'))
        octave = Combo(self, value_list=[str(o) for o in range(-2, 3)], default=2, wheel_dir=False)
        octave.indexChanged.connect(set_octave)
        oct_layout.addWidget(octave)

        notes_off_layout = QtGui.QHBoxLayout()
        layout.addLayout(notes_off_layout, 1, 1, 1, 2)
        all_notes_off = SquareButton(self, color=QtCore.Qt.darkRed, size=12)
        all_notes_off.clicked.connect(lambda: self.send_ctrl(123, 0))
        notes_off_layout.addWidget(all_notes_off)
        notes_off_layout.addWidget(Label(self, 'All notes OFF'), QtCore.Qt.AlignLeft)

        sounds_off_layout = QtGui.QHBoxLayout()
        layout.addLayout(sounds_off_layout, 2, 1, 1, 2)
        all_sounds_off = SquareButton(self, color=QtCore.Qt.darkRed, size=12)
        all_sounds_off.clicked.connect(lambda: self.send_ctrl(120, 0))
        sounds_off_layout.addWidget(all_sounds_off)
        sounds_off_layout.addWidget(Label(self, 'All sounds OFF'), QtCore.Qt.AlignLeft)

        return frame

    def create_arp(self):
        frame = Frame(self, 'Arpeggiator')
        frame.setContentsMargins(2, 2, 2, 2)
        layout = QtGui.QGridLayout()
        frame.setLayout(layout)

        mode_layout = QtGui.QHBoxLayout()
        layout.addLayout(mode_layout, 0, 0)
        mode_layout.addWidget(HSpacer())
        mode_layout.addWidget(Label(self, 'Mode'))
        arp_mode = BlofeldCombo(self, self.params.Arpeggiator_Mode, name='', values=['off', 'on', '1 shot', 'Hold'])
        mode_layout.addWidget(arp_mode)
        pattern_layout = QtGui.QHBoxLayout()
        layout.addLayout(pattern_layout, 1, 0)
        pattern_layout.addWidget(Label(self, 'Pattern'))
        arp_patterns = [
                        'off', 
                        'User', 
                        '●○●●|●○●●|●○●●|●○●●', 
                        '●○●○|●○○●|●○●○|●○○●', 
                        '●○●○|●○●●|●○●○|●○●●', 
                        '●○●●|●○●○|●○●●|●○●○', 
                        '●○●○|●●○●|●○●○|●●○●', 
                        '●●○●|○●●○|●●○●|○●●○', 
                        '●○●○|●○●○|●●○●|○●○●', 
                        '●○●○|●○●●|○●○●|●○●○', 
                        '●●●○|●●●○|●●●○|●●●○', 
                        '●●○●|●○●●|○●●○|●●●○', 
                        '●●○●|●○●●|○●●○|●○●○', 
                        '●●○●|●○●○|●●○●|●○●○', 
                        '●○●○|●○●○|●●○●|○●●●', 
                        '●○○●|○○●○|○●○○|●○○●', 
                        '●○●○|●○●○|●○○●|●○●○', 
                        ]
        arp_patterns = [QtCore.QString().fromUtf8(p) for p in arp_patterns]
        pattern = BlofeldCombo(self, self.params.Arpeggiator_Pattern, values=arp_patterns, name='')
        pattern_layout.addWidget(pattern)

        tempo_layout = QtGui.QHBoxLayout()
        layout.addLayout(tempo_layout, 2, 0)
        tempo_layout.addWidget(Label(self, 'Tempo'), QtCore.Qt.AlignTop)
        tempo = BlofeldDial(self, self.params.Arpeggiator_Tempo, size=24, name='')
        tempo_layout.addWidget(tempo, QtCore.Qt.AlignVCenter)
        t_values = [v.replace('bars', 'b.') for v in self.params.Arpeggiator_Clock.values]
        clock = BlofeldCombo(self, self.params.Arpeggiator_Clock, name='Clock', values=t_values)
        tempo_layout.addWidget(clock)
        length = BlofeldCombo(self, self.params.Arpeggiator_Ptn_Length, name='Length')
        tempo_layout.addWidget(length)
        ptn_reset = BlofeldButton(self, self.params.Arpeggiator_Ptn_Reset, checkable=True, size=20, name='Reset')
        tempo_layout.addWidget(ptn_reset)

        note_layout = QtGui.QHBoxLayout()
        layout.addLayout(note_layout, 3, 0)
        note_length = BlofeldCombo(self, self.params.Arpeggiator_Length, name='Note Len.')
        note_layout.addWidget(note_length)
        vel_values = ['Each', 'First', 'Last', '32', '64', '100', '127']
        note_vel = BlofeldCombo(self, self.params.Arpeggiator_Velocity, values=vel_values, name='Velocity')
        note_layout.addWidget(note_vel)
        note_timing = BlofeldCombo(self, self.params.Arpeggiator_Timing_Factor, name='Timing')
        note_layout.addWidget(note_timing)

        adv_layout = QtGui.QHBoxLayout()
        layout.addLayout(adv_layout, 4, 0)
        octave = BlofeldCombo(self, self.params.Arpeggiator_Octave, name='Octave')
        adv_layout.addWidget(octave)
        direction = BlofeldCombo(self, self.params.Arpeggiator_Direction, name='Direction')
        adv_layout.addWidget(direction)
        sort = BlofeldCombo(self, self.params.Arpeggiator_Sort_Order, name='Sort Order')
        adv_layout.addWidget(sort)

        return frame

#    def create_sorted_library(self):
#        sorted_library = SortedLibrary(self.blofeld_library)
#        del self.sorted_library_menu
#        menu = QtGui.QMenu()
#        by_bank = QtGui.QMenu('By bank', menu)
#        menu.addMenu(by_bank)
#        for id, bank in enumerate(sorted_library.by_bank):
#            if not any(bank): continue
#            bank_menu = QtGui.QMenu(uppercase[id], by_bank)
#            by_bank.addMenu(bank_menu)
#            for sound in bank:
#                if sound is None: continue
#                item = QtGui.QAction('{:03} {}'.format(sound.prog+1, sound.name), bank_menu)
#                item.setData((sound.bank, sound.prog))
#                bank_menu.addAction(item)
#        by_cat = QtGui.QMenu('By category', menu)
#        menu.addMenu(by_cat)
#        for cid, cat in enumerate(categories):
#            cat_menu = QtGui.QMenu(by_cat)
#            by_cat.addMenu(cat_menu)
#            cat_len = 0
#            for sound in sorted_library.by_cat[cid]:
#                cat_len += 1
#                item = QtGui.QAction(sound.name, cat_menu)
#                item.setData((sound.bank, sound.prog))
#                cat_menu.addAction(item)
#            if not len(cat_menu.actions()):
#                cat_menu.setEnabled(False)
#            cat_menu.setTitle('{} ({})'.format(cat, cat_len))
#        by_alpha = QtGui.QMenu('Alphabetical', menu)
#        menu.addMenu(by_alpha)
#        for alpha in sorted(sorted_library.by_alpha.keys()):
#            alpha_menu = QtGui.QMenu(by_alpha)
#            by_alpha.addMenu(alpha_menu)
#            alpha_len = 0
#            for sound in sorted_library.by_alpha[alpha]:
#                alpha_len += 1
#                item = QtGui.QAction(sound.name, alpha_menu)
#                item.setData((sound.bank, sound.prog))
#                alpha_menu.addAction(item)
#            if not len(alpha_menu.actions()):
#                alpha_menu.setEnabled(False)
#            alpha_menu.setTitle('{} ({})'.format(alpha, alpha_len))
#        self.sorted_library_menu = menu
#        self.sorted_library = sorted_library

    def receive_value(self, location, index, value):
        if not self.midi_receive_btn.isChecked(): return
        attr = Params[index].attr
        old_send = self.send
        self.send = False
        setattr(self, attr, value)
        for env in self.envelopes:
            env.compute_envelope()
            env.update()
        self.set_effect_1_widgets()
        self.set_effect_2_widgets()
        self.send = old_send
        self.display.midi_btn.midi_in()

    def send_value(self, attr, value):
        location = 0
        par_id = Params.index_from_attr(attr)
        par_high, par_low = divmod(par_id, 128)
#        print par_high, par_low, value
        
        self.midi_event.emit(SysExEvent(1, [INIT, IDW, IDE, self.main.blofeld_id, SNDP, location, par_high, par_low, value, END]))
        self.display.midi_btn.midi_out()

    def send_ctrl(self, param, value):
        self.midi_event.emit(CtrlEvent(1, self.channel, param, value))
        self.display.midi_btn.midi_out()

    def send_note(self, note, state):
        note = note+self.octave*12
        if state:
            note_event = NoteOnEvent(1, self.channel, note, state)
        else:
            note_event = NoteOffEvent(1, self.channel, note)
        self.midi_event.emit(note_event)
        self.display.midi_btn.midi_out()

    def pgm_change_received(self, bank, prog):
        if self.pgm_receive_btn.isChecked():
            self.setSound(bank, prog, False)

    def randomize(self):
#        old_send = self.send
#        self.send = False
        self.notify = False
        for p in self.params:
            if p.attr is None: continue
            try:
                start, end, step = p.range
                value = randrange(start, end+1, step)
                setattr(self, p.attr, value)
            except Exception as e:
                print e

#        self.send = old_send
        self.notify = True

    def setSound(self, bank, prog, pgm_send=False):
        sound = self.blofeld_library[bank, prog]
        if sound is None: return
        self.sound = sound
        data = sound.data
        old_send = self.send
        self.send = False
        self.notify = False
        for i, p in enumerate(data):
            try:
                attr = self.params[i].attr
                if attr is not None:
                    setattr(self, attr, p)
            except:
                pass
        for env in self.envelopes:
            env.compute_envelope()
            env.update()
        self.set_effect_1_widgets()
        self.set_effect_2_widgets()
        self.send = old_send
        self.notify = True
        self.display.setSound()
        if pgm_send and self.pgm_send_btn.isChecked():
            self.display.midi_btn.midi_out()
            self.program_change.emit(sound.bank, sound.prog)

    def create_display(self):
        layout = QtGui.QGridLayout()
        self.display = BlofeldDisplay(self)
        layout.addWidget(self.display, 0, 0, 4, 1)

        layout.addWidget(Section(self, border=True, alpha=255), 0, 1, 2, 2)

        layout.addWidget(Section(self, border=True, alpha=255), 2, 1, 2, 2)
        in_path = QtGui.QPainterPath()
        in_path.moveTo(0, 3)
        in_path.lineTo(5, 3)
        in_path.arcMoveTo(3, 0, 5.5, 6, 135)
        in_path.arcTo(3, 0, 5.5, 6, 135, -270)
        layout.addWidget(Label(self, 'IN', path=in_path, label_pos=BOTTOM), 0, 1, 2, 1)
        self.pgm_receive_btn = SquareButton(self, 'PGM receive', checkable=True, checked=False, size=12, label_pos=RIGHT)
        self.pgm_receive_btn.setEnabled(False)
        self.pgm_receive_btn.toggled.connect(lambda state: self.display.statusUpdate('PGM receive: {}'.format('enabled' if state else 'disabled')))
        self.pgm_receive_btn.toggled.connect(self.pgm_receive.emit)
        layout.addWidget(self.pgm_receive_btn, 0, 2)
        self.midi_receive_btn = SquareButton(self, 'MIDI receive', checkable=True, checked=False, size=12, label_pos=RIGHT)
        self.midi_receive_btn.setEnabled(False)
        self.midi_receive_btn.toggled.connect(lambda state: self.display.statusUpdate('MIDI receive: {}'.format('enabled' if state else 'disabled')))
        self.midi_receive_btn.toggled.connect(self.midi_receive.emit)
        layout.addWidget(self.midi_receive_btn, 1, 2)

        out_path = QtGui.QPainterPath()
        out_path.arcMoveTo(0, 0, 5.5, 6, 45)
        out_path.arcTo(0, 0, 5.5, 6, 45, 270)
        out_path.moveTo(4, 3)
        out_path.lineTo(8, 3)
        layout.addWidget(Label(self, 'OUT', path=out_path, label_pos=BOTTOM), 2, 1, 2, 1)
        self.pgm_send_btn = SquareButton(self, 'PGM send', checkable=True, checked=False, size=12, label_pos=RIGHT)
        self.pgm_send_btn.setEnabled(False)
        self.pgm_send_btn.toggled.connect(lambda state: self.display.statusUpdate('PGM send: {}'.format('enabled' if state else 'disabled')))
        self.pgm_send_btn.toggled.connect(self.pgm_send.emit)
        layout.addWidget(self.pgm_send_btn, 2, 2)
        self.midi_send_btn = SquareButton(self, 'MIDI send', checkable=True, checked=False, size=12, label_pos=RIGHT)
        self.midi_send_btn.setEnabled(False)
        self.midi_send_btn.toggled.connect(lambda state: setattr(self, 'send', state))
        self.midi_send_btn.toggled.connect(lambda state: self.display.statusUpdate('MIDI send: {}'.format('enabled' if state else 'disabled')))
        self.midi_send_btn.toggled.connect(self.midi_send.emit)
        layout.addWidget(self.midi_send_btn, 3, 2)

        return layout

    def create_common(self):
        frame = Frame(self, 'Common')
        frame.setContentsMargins(2, 2, 2, 2)
        layout = QtGui.QHBoxLayout()
        frame.setLayout(layout)

#        layout.addWidget(HSpacer())
#        hold = SquareButton(self, checkable=True)
#        layout.addWidget(hold, 0, 2, 1, 1)
#        layout.addWidget(Label(self, 'Hold'), 0, 2, 1, 1)
        pitch_layout = QtGui.QGridLayout()
        layout.addLayout(pitch_layout)
        pitch_layout.addWidget(Section(self, border=True, alpha=255), 1, 0, 2, 2)
        pitch_layout.addWidget(VSpacer(min_height=20), 0, 0, 1, 1)
        pitch_src = BlofeldCombo(self, self.params.Osc_Pitch_Source, name='Pitch Source')
        pitch_layout.addWidget(pitch_src, 1, 0, 1, 2)
        pitch_layout.addWidget(Label(self, 'Pitch\nAmount'), 2, 0)
        pitch_amount = BlofeldDial(self, self.params.Osc_Pitch_Amount, size=24, name='')
        pitch_layout.addWidget(pitch_amount, 2, 1)

        uni_layout = QtGui.QGridLayout()
        layout.addLayout(uni_layout)
        alloc = BlofeldCombo(self, self.params.Allocation_Mode_and_Unisono, sub_par='Allocation', name='Allocation')
        uni_layout.addWidget(alloc, 0, 0, 1, 2)
        unisono = BlofeldCombo(self, self.params.Allocation_Mode_and_Unisono, sub_par='Unisono', name='Unisono')
        uni_layout.addWidget(unisono, 1, 0, 1, 1, QtCore.Qt.AlignHCenter)
        detune = BlofeldDial(self, self.params.Unisono_Uni_Detune, size=24, name='Detune')
        uni_layout.addWidget(detune, 1, 1, 1, 1)

        return frame

    def create_adv(self):
        stack_layout = QtGui.QStackedLayout()
        
        main_widget = QtGui.QWidget()
        main_widget.setContentsMargins(-3, -3, -3, -3)
        main_layout = QtGui.QHBoxLayout()
        main_widget.setLayout(main_layout)
        stack_layout.addWidget(main_widget)
        main_layout.addWidget(self.create_effect_1())
        main_layout.addWidget(self.create_effect_2())
        main_layout.addWidget(self.create_arp())

        arp_widget = QtGui.QWidget()
        arp_widget.setContentsMargins(-3, -3, -3, -3)
        stack_layout.addWidget(arp_widget)
        arp_widget.setLayout(self.create_arp_editor())

#        stack_layout.setCurrentIndex(1)

        return stack_layout

    def create_arp_editor(self):
        layout = QtGui.QGridLayout()
        self.arp_editor = ArpEditor(self)
        layout.addWidget(self.arp_editor, 0, 0, 1, 16)

#        for c in range(16):
#            combo = Combo(self, value_list=[str(v) for v in range(8)])
#            layout.addWidget(combo, 1, c)
#            combo.indexChanged.connect(lambda v, step=c: self.arp_editor.step_list[step].setLength(v))
        return layout

    def create_mod_widgets(self):
        widget = QtGui.QWidget()
        widget.setContentsMargins(-3, -3, -3, -3)
        layout = QtGui.QVBoxLayout()
        widget.setLayout(layout)
        layout.addWidget(self.create_modifiers())
        layout.addWidget(self.create_mod_matrix())
        return widget

    def create_modifiers(self):
        frame = Frame(self, 'Modifiers')
        layout = QtGui.QGridLayout()
        frame.setLayout(layout)

        for m in range(1, 5):
            src_a = BlofeldCombo(self, getattr(self.params, 'Modifier_{}_Source_A'.format(m)), name='')
            oper = BlofeldCombo(self, getattr(self.params, 'Modifier_{}_Operation'.format(m)), name='')
            src_b = BlofeldCombo(self, getattr(self.params, 'Modifier_{}_Source_B'.format(m)), name='')
            const = BlofeldCombo(self, getattr(self.params, 'Modifier_{}_Constant'.format(m)), name='')
            layout.addWidget(src_a, m, 0)
            layout.addWidget(oper, m, 1)
            layout.addWidget(src_b, m, 2)
            layout.addWidget(const, m, 3)

        return frame

    def create_mod_matrix(self):
        frame = Frame(self, 'Modulation Matrix')
        layout = QtGui.QVBoxLayout()
        frame.setLayout(layout)

        mod_id = 1
        for r in range(16):
            line = QtGui.QHBoxLayout()
            layout.addLayout(line)
            src = BlofeldCombo(self, getattr(self.params, 'Modulation_{}_Source'.format(mod_id)), name='')
            amount = BlofeldSlider(self, getattr(self.params, 'Modulation_{}_Amount'.format(mod_id)), orientation=HORIZONTAL, inverted=True, name='')
            dest = BlofeldCombo(self, getattr(self.params, 'Modulation_{}_Destination'.format(mod_id)), name='')
            line.addWidget(src)
            line.addWidget(amount)
            line.addWidget(dest)
            mod_id += 1

        return frame


    def create_glide(self):
        frame = Frame(self, 'Glide')
        frame.setContentsMargins(2, 12, 2, 2)
        layout = QtGui.QHBoxLayout()
        frame.setLayout(layout)

        switch = BlofeldButton(self, self.params.Glide, checkable=True, name='')
        layout.addWidget(switch, alignment=QtCore.Qt.AlignHCenter)

        glide = BlofeldDial(self, self.params.Glide_Rate, name='Amount', size=32)
        layout.addWidget(glide)
        rate = BlofeldCombo(self, self.params.Glide_Mode)
        layout.addWidget(rate)

        return frame

    def create_effect_1(self):
        short_names = {
                       'Lowpass': 'LP', 
                       'Highpass': 'HP', 
                       'Diffusion': 'Diff.', 
                       'Damping': 'Damp', 
                       }
        def create_effects(efx_dict):
            efx_widget = QtGui.QWidget(self)
            frame_layout = QtGui.QVBoxLayout()
            items = sorted(efx_dict.items())
            _lines = []
            _line = []
            for id, efx in items:
                efx_range = self.efx_ranges[efx]
                if len(efx_range) == 128:
                    widget = BlofeldDial(self, self.params[id], name=short_names.get(efx, efx), size=24)
                    widget.setSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Fixed)
                else:
                    widget = BlofeldCombo(self, self.params[id], name=efx, values=efx_range)
                    widget.setSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
                size = sum([w.minimumWidth() for w in _line])
                if size > 150:
                    _lines.append(_line)
                    _line = [widget]
                else:
                    _line.append(widget)
            _lines.append(_line)
            if len(items) == 4 and len(_lines[0]) > 2:
                while len(_lines[0]) > 2:
                    tmp = _lines[0].pop()
                    if len(_lines) == 1:
                        _lines.append([tmp])
                    else:
                        _lines[1].insert(0, tmp)
            if len(items) >= 5 and len(_lines[0]) > 3:
                while len(_lines[0]) > 3:
                    tmp = _lines[0].pop()
                    if len(_lines) == 1:
                        _lines.append([tmp])
                    else:
                        _lines[1].insert(0, tmp)
            for l in _lines:
                line = QtGui.QHBoxLayout()
                frame_layout.addLayout(line)
                [line.addWidget(w) if isinstance(w, BlofeldDial) else line.addWidget(w, alignment=QtCore.Qt.AlignHCenter) for w in l]
            if len(_lines) == 1:
                frame_layout.addWidget(VSpacer(min_height=20))
            efx_widget.setLayout(frame_layout)
            return efx_widget
            
        frame = Frame(self, 'Efx1')
        layout = QtGui.QVBoxLayout()
        frame.setLayout(layout)
        frame.setContentsMargins(2, 2, 2, 2)

        line1 = QtGui.QHBoxLayout()
        layout.addLayout(line1)
        line1.addWidget(HSpacer(max_width=50))
        efx_type = BlofeldCombo(self, self.params.Effect_1_Type)
        efx_type.indexChanged.connect(self.set_effect_1_widgets)
        line1.addWidget(efx_type)
        efx_mix = BlofeldDial(self, self.params.Effect_1_Mix, size=24)
        line1.addWidget(efx_mix)

        self.effects_1_layout = QtGui.QStackedLayout()
        layout.addLayout(self.effects_1_layout)

        for efx in sorted(self.efx_params[0]):
            efx_layout = create_effects(self.efx_params[0][efx])
            self.effects_1_layout.addWidget(efx_layout)

        self.effects_1_layout.currentWidget().setEnabled(False)

        return frame

    def set_effect_1_widgets(self, id=None):
        if id is None:
            id = self.Effect_1_Type
        if id == 0:
            self.effects_1_layout.currentWidget().setEnabled(False)
            return
        self.effects_1_layout.setCurrentIndex(id-1)
        self.effects_1_layout.currentWidget().setEnabled(True)

    def create_effect_2(self):
        short_names = {
                       'Lowpass': 'LP', 
                       'Highpass': 'HP', 
                       'Diffusion': 'Diff.', 
                       'Damping': 'Damp', 
                       }
        def create_effects(efx_dict):
            efx_widget = QtGui.QWidget(self)
            frame_layout = QtGui.QVBoxLayout()
            items = sorted(efx_dict.items())
            _lines = []
            _line = []
            for id, efx in items:
                efx_range = self.efx_ranges[efx]
                if len(efx_range) == 128:
                    widget = BlofeldDial(self, self.params[id], name=short_names.get(efx, efx), size=24)
                    widget.setSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Fixed)
                else:
                    widget = BlofeldCombo(self, self.params[id], name=efx, values=efx_range)
                    widget.setSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
                size = sum([w.minimumWidth() for w in _line])
                if size > 150:
                    _lines.append(_line)
                    _line = [widget]
                else:
                    _line.append(widget)
            _lines.append(_line)
            if len(items) == 4 and len(_lines[0]) > 2:
                while len(_lines[0]) > 2:
                    tmp = _lines[0].pop()
                    if len(_lines) == 1:
                        _lines.append([tmp])
                    else:
                        _lines[1].insert(0, tmp)
            if len(items) >= 5 and len(_lines[0]) > 3:
                while len(_lines[0]) > 3:
                    tmp = _lines[0].pop()
                    if len(_lines) == 1:
                        _lines.append([tmp])
                    else:
                        _lines[1].insert(0, tmp)
            for l in _lines:
                line = QtGui.QHBoxLayout()
                frame_layout.addLayout(line)
                [line.addWidget(w) if isinstance(w, BlofeldDial) else line.addWidget(w, alignment=QtCore.Qt.AlignHCenter) for w in l]
            if len(_lines) == 1:
                frame_layout.addWidget(VSpacer(min_height=20))
            efx_widget.setLayout(frame_layout)
            return efx_widget
            
        frame = Frame(self, 'Efx2')
        layout = QtGui.QVBoxLayout()
        frame.setLayout(layout)
        frame.setContentsMargins(2, 2, 2, 2)

        line1 = QtGui.QHBoxLayout()
        layout.addLayout(line1)
        line1.addWidget(HSpacer(max_width=50))
        efx_type = BlofeldCombo(self, self.params.Effect_2_Type)
        efx_type.indexChanged.connect(self.set_effect_2_widgets)
        line1.addWidget(efx_type)
        efx_mix = BlofeldDial(self, self.params.Effect_2_Mix, size=24)
        line1.addWidget(efx_mix)

        self.effects_2_layout = QtGui.QStackedLayout()
        layout.addLayout(self.effects_2_layout)

        for efx in sorted(self.efx_params[1]):
            efx_layout = create_effects(self.efx_params[1][efx])
            self.effects_2_layout.addWidget(efx_layout)

        self.effects_2_layout.currentWidget().setEnabled(False)

        return frame

    def set_effect_2_widgets(self, id=None):
        if id is None:
            id = self.Effect_2_Type
        if id == 0:
            self.effects_2_layout.currentWidget().setEnabled(False)
            return
        self.effects_2_layout.setCurrentIndex(id-1)
        self.effects_2_layout.currentWidget().setEnabled(True)

    def create_amplifier(self):
        frame = Frame(self, 'Amplifier')
        layout = QtGui.QGridLayout()
        frame.setLayout(layout)
        frame.setContentsMargins(2, 2, 2, 2)

        volume = BlofeldDial(self, self.params.Amplifier_Volume)
        layout.addWidget(volume, 1, 0)
        velocity = BlofeldDial(self, self.params.Amplifier_Velocity)
        layout.addWidget(velocity, 1, 1)
        mod_source = BlofeldCombo(self, self.params.Amplifier_Mod_Source)
        layout.addWidget(mod_source, 0, 2)
        mod_amount = BlofeldDial(self, self.params.Amplifier_Mod_Amount, size=24)
        layout.addWidget(mod_amount, 1, 2)

        return frame

    def create_envelopes(self):
        layout = QtGui.QGridLayout()
        layout.addWidget(self.create_filter_env(), 0, 0, 1, 1)
        layout.addWidget(self.create_amp_env(), 0, 1, 1, 1)
        layout.addWidget(self.create_env_3(), 1, 0, 1, 1)
        layout.addWidget(self.create_env_4(), 1, 1, 1, 1)
        return layout

    def create_filter_sel(self):
        frame = Frame(self, 'Filters')
        grid = QtGui.QGridLayout()
        frame.setLayout(grid)
        frame.setContentsMargins(2, 2, 2, 2)

        combo = BlofeldCombo(self, self.params.Filter_Routing, name='')
        grid.addWidget(HSpacer(), 0, 0, 1, 1)
        grid.addWidget(Label(self, 'Routing '), 0, 1, 1, 1)
        grid.addWidget(combo, 0, 2, 1, 1)
        routing = Routing(self, BOTTOM, BOTTOM, direction=EXT, orientation=HORIZONTAL, padding=(16, 4))
        grid.addWidget(routing, 1, 0, 1, 3)
        combo.indexChanged.connect(lambda id: [routing.set_arrow(EXT if id == 0 else FROM), routing.update()])
        grid.addWidget(VSpacer())

        return frame

    def create_filter1(self):
        frame = Frame(self, '1')
        grid = QtGui.QGridLayout()
        frame.setLayout(grid)
        frame.setContentsMargins(2, 2, 2, 2)

        ftype_layout = QtGui.QHBoxLayout()
        ftype_layout.addWidget(HSpacer(self))
        ftype_layout.addWidget(Label(self, 'Type'))
        ftype = BlofeldCombo(self, self.params.Filter_1_Type, name='')
        ftype_layout.addWidget(ftype)
        grid.addLayout(ftype_layout, 0, 0, 1, 2)

        cutoff = BlofeldDial(self, self.params.Filter_1_Cutoff, size=32)
        grid.addWidget(cutoff, 1, 0, 1, 1)
        res = BlofeldDial(self, self.params.Filter_1_Resonance, name='Res.', size=32)
        grid.addWidget(res, 1, 1, 1, 1)

        env_amount = BlofeldDial(self, self.params.Filter_1_Env_Amount, size=32)
        grid.addWidget(env_amount, 2, 0, 1, 1)
        env_vel = BlofeldDial(self, self.params.Filter_1_Env_Velocity, size=32)
        grid.addWidget(env_vel, 2, 1, 1, 1)

        drive_layout = QtGui.QHBoxLayout()
        drive = BlofeldDial(self, self.params.Filter_1_Drive, size=24)
        drive_layout.addWidget(drive)
        drive_curve = BlofeldCombo(self, self.params.Filter_1_Drive_Curve)
        drive_layout.addWidget(drive_curve)
        grid.addLayout(drive_layout, 3, 0, 1, 2)

        combos = QtGui.QGridLayout()

        mod_label = Label(self, 'MOD')
        combos.addWidget(Section(self, border=True, alpha=255), 0, 0, 2, 3)
        combos.addWidget(mod_label, 0, 0)
        mod_source = BlofeldCombo(self, self.params.Filter_1_Mod_Source, name='')
        combos.addWidget(mod_source, 1, 0)
        mod_amount = BlofeldDial(self, self.params.Filter_1_Mod_Amount, name='Amount')
        combos.addWidget(mod_amount, 0, 1, 2, 1, QtCore.Qt.AlignBottom)

        fm_label = Label(self, 'FM')
        combos.addWidget(Section(self, border=True, alpha=255), 2, 0, 2, 3)
        combos.addWidget(fm_label, 2, 0)
        fm_source = BlofeldCombo(self, self.params.Filter_1_FM_Source, name='')
        combos.addWidget(fm_source, 3, 0)
        fm_amount = BlofeldDial(self, self.params.Filter_1_FM_Amount, name='Amount')
        combos.addWidget(fm_amount, 2, 1, 2, 1, QtCore.Qt.AlignBottom)

        pan_label = Label(self, 'PAN')
        combos.addWidget(Section(self, border=True, alpha=255), 4, 0, 2, 3)
        combos.addWidget(pan_label, 4, 0)
        pan_source = BlofeldCombo(self, self.params.Filter_1_Pan_Source, name='')
        combos.addWidget(pan_source, 5, 0)
        pan_amount = BlofeldDial(self, self.params.Filter_1_Pan_Amount, name='Amount')
        combos.addWidget(pan_amount, 4, 1, 2, 1, QtCore.Qt.AlignBottom)

        grid.addLayout(combos, 4, 0, 1, 2)

        keytrack = BlofeldDial(self, self.params.Filter_1_Keytrack)
        grid.addWidget(keytrack, 5, 0, 1, 1)
        pan = BlofeldDial(self, self.params.Filter_1_Pan)
        grid.addWidget(pan, 5, 1, 1, 1)

        return frame

    def create_filter2(self):
        frame = Frame(self, '2')
        grid = QtGui.QGridLayout()
        frame.setLayout(grid)
        frame.setContentsMargins(2, 2, 2, 2)

        ftype_layout = QtGui.QHBoxLayout()
        ftype_layout.addWidget(HSpacer(self))
        ftype_layout.addWidget(Label(self, 'Type'))
        ftype = BlofeldCombo(self, self.params.Filter_2_Type, name='')
        ftype_layout.addWidget(ftype)
        grid.addLayout(ftype_layout, 0, 0, 1, 2)

        cutoff = BlofeldDial(self, self.params.Filter_2_Cutoff, size=32)
        grid.addWidget(cutoff, 1, 0, 1, 1)
        res = BlofeldDial(self, self.params.Filter_2_Resonance, name='Res.', size=32)
        grid.addWidget(res, 1, 1, 1, 1)

        env_amount = BlofeldDial(self, self.params.Filter_2_Env_Amount, size=32)
        grid.addWidget(env_amount, 2, 0, 1, 1)
        env_vel = BlofeldDial(self, self.params.Filter_2_Env_Velocity, size=32)
        grid.addWidget(env_vel, 2, 1, 1, 1)

        drive_layout = QtGui.QHBoxLayout()
        drive = BlofeldDial(self, self.params.Filter_2_Drive, size=24)
        drive_layout.addWidget(drive)
        drive_curve = BlofeldCombo(self, self.params.Filter_2_Drive_Curve)
        drive_layout.addWidget(drive_curve)
        grid.addLayout(drive_layout, 3, 0, 1, 2)

        combos = QtGui.QGridLayout()

        mod_label = Label(self, 'MOD')
        combos.addWidget(Section(self, border=True, alpha=255), 0, 0, 2, 3)
        combos.addWidget(mod_label, 0, 0)
        mod_source = BlofeldCombo(self, self.params.Filter_2_Mod_Source, name='')
        combos.addWidget(mod_source, 1, 0)
        mod_amount = BlofeldDial(self, self.params.Filter_2_Mod_Amount, name='Amount')
        combos.addWidget(mod_amount, 0, 1, 2, 1, QtCore.Qt.AlignBottom)

        fm_label = Label(self, 'FM')
        combos.addWidget(Section(self, border=True, alpha=255), 2, 0, 2, 3)
        combos.addWidget(fm_label, 2, 0)
        fm_source = BlofeldCombo(self, self.params.Filter_2_FM_Source, name='')
        combos.addWidget(fm_source, 3, 0)
        fm_amount = BlofeldDial(self, self.params.Filter_2_FM_Amount, name='Amount')
        combos.addWidget(fm_amount, 2, 1, 2, 1, QtCore.Qt.AlignBottom)

        pan_label = Label(self, 'PAN')
        combos.addWidget(Section(self, border=True, alpha=255), 4, 0, 2, 3)
        combos.addWidget(pan_label, 4, 0)
        pan_source = BlofeldCombo(self, self.params.Filter_2_Pan_Source, name='')
        combos.addWidget(pan_source, 5, 0)
        pan_amount = BlofeldDial(self, self.params.Filter_2_Pan_Amount, name='Amount')
        combos.addWidget(pan_amount, 4, 1, 2, 1, QtCore.Qt.AlignBottom)

        grid.addLayout(combos, 4, 0, 1, 2)

        keytrack = BlofeldDial(self, self.params.Filter_2_Keytrack)
        grid.addWidget(keytrack, 5, 0, 1, 1)
        pan = BlofeldDial(self, self.params.Filter_2_Pan)
        grid.addWidget(pan, 5, 1, 1, 1)

        return frame

    def create_lfo1(self):
        frame = Frame(self, 'LFO 1')
        layout = QtGui.QVBoxLayout()
        frame.setLayout(layout)

        line1 = QtGui.QHBoxLayout()
        layout.addLayout(line1)

        shape = BlofeldCombo(self, self.params.LFO_1_Shape)
        line1.addWidget(shape)
        speed = BlofeldDial(self, self.params.LFO_1_Speed, size=24)
        line1.addWidget(speed)
        phase = BlofeldDial(self, self.params.LFO_1_Start_Phase, size=24)
        line1.addWidget(phase)
        sync = BlofeldButton(self, self.params.LFO_1_Sync, checkable=True, name='Sync')
        line1.addWidget(sync)

        line2 = QtGui.QHBoxLayout()
        layout.addLayout(line2)

        keytrack = BlofeldDial(self, self.params.LFO_1_Keytrack, size=24)
        line2.addWidget(keytrack)
        fade = BlofeldDial(self, self.params.LFO_1_Fade, size=24)
        line2.addWidget(fade)
        delay = BlofeldDial(self, self.params.LFO_1_Delay)
        line2.addWidget(delay)
        clock = BlofeldButton(self, self.params.LFO_1_Clocked, checkable=True, name='Clock')
        line2.addWidget(clock)

        return frame

    def create_lfo2(self):
        frame = Frame(self, 'LFO 2')
        layout = QtGui.QVBoxLayout()
        frame.setLayout(layout)

        line1 = QtGui.QHBoxLayout()
        layout.addLayout(line1)

        shape = BlofeldCombo(self, self.params.LFO_2_Shape)
        line1.addWidget(shape)
        speed = BlofeldDial(self, self.params.LFO_2_Speed, size=24)
        line1.addWidget(speed)
        phase = BlofeldDial(self, self.params.LFO_2_Start_Phase, size=24)
        line1.addWidget(phase)
        sync = BlofeldButton(self, self.params.LFO_2_Sync, checkable=True, name='Sync')
        line1.addWidget(sync)

        line2 = QtGui.QHBoxLayout()
        layout.addLayout(line2)

        keytrack = BlofeldDial(self, self.params.LFO_2_Keytrack, size=24)
        line2.addWidget(keytrack)
        fade = BlofeldDial(self, self.params.LFO_2_Fade, size=24)
        line2.addWidget(fade)
        delay = BlofeldDial(self, self.params.LFO_2_Delay)
        line2.addWidget(delay)
        clock = BlofeldButton(self, self.params.LFO_2_Clocked, checkable=True, name='Clock')
        line2.addWidget(clock)

        return frame

    def create_lfo3(self):
        frame = Frame(self, 'LFO 3')
        layout = QtGui.QVBoxLayout()
        frame.setLayout(layout)

        line1 = QtGui.QHBoxLayout()
        layout.addLayout(line1)

        shape = BlofeldCombo(self, self.params.LFO_3_Shape)
        line1.addWidget(shape)
        speed = BlofeldDial(self, self.params.LFO_3_Speed, size=24)
        line1.addWidget(speed)
        phase = BlofeldDial(self, self.params.LFO_3_Start_Phase, size=24)
        line1.addWidget(phase)
        sync = BlofeldButton(self, self.params.LFO_3_Sync, checkable=True, name='Sync')
        line1.addWidget(sync)

        line2 = QtGui.QHBoxLayout()
        layout.addLayout(line2)

        keytrack = BlofeldDial(self, self.params.LFO_3_Keytrack, size=24)
        line2.addWidget(keytrack)
        fade = BlofeldDial(self, self.params.LFO_3_Fade, size=24)
        line2.addWidget(fade)
        delay = BlofeldDial(self, self.params.LFO_3_Delay)
        line2.addWidget(delay)
        clock = BlofeldButton(self, self.params.LFO_3_Clocked, checkable=True, name='Clock')
        line2.addWidget(clock)

        return frame

    def create_filter_env(self):
        def set_enabled(id):
            if id == 0:
                for w in (attack_level, decay2, sustain2):
                    w.setEnabled(False)
            else:
                for w in (attack_level, decay2, sustain2):
                    w.setEnabled(True)

        frame = Frame(self, 'Filter Env.')
        frame.setContentsMargins(2, 12, 2, 2)
        env = BlofeldEnv(self, 'Filter_Envelope', show_points=False)
        env.setFixedSize(68, 40)
        self.envelopes.append(env)
        
        grid = QtGui.QGridLayout()
        frame.setLayout(grid)
        mode = BlofeldCombo(self, self.params.Filter_Envelope_Mode, sub_par='Mode')
        mode.internalUpdate.connect(env.setEnvelope)
        mode.internalUpdate.connect(set_enabled)
        grid.addWidget(mode, 0, 0, 1, 1, QtCore.Qt.AlignBottom)
        trigger = BlofeldCombo(self, self.params.Filter_Envelope_Mode, sub_par='Trigger')
        grid.addWidget(trigger, 1, 0, 1, 1)
        attack = BlofeldDial(self, self.params.Filter_Envelope_Attack, size=24)
        grid.addWidget(attack, 0, 1, 1, 1)
        attack_level = BlofeldDial(self, self.params.Filter_Envelope_Attack_Level, size=24, name='A. Level')
        grid.addWidget(attack_level, 1, 1, 1, 1)
        decay = BlofeldDial(self, self.params.Filter_Envelope_Decay, size=24)
        grid.addWidget(decay, 0, 2, 1, 1)
        sustain = BlofeldDial(self, self.params.Filter_Envelope_Sustain, size=24)
        grid.addWidget(sustain, 0, 3, 1, 1)
        decay2 = BlofeldDial(self, self.params.Filter_Envelope_Decay_2, size=24, name='Dec. 2')
        grid.addWidget(decay2, 1, 2, 1, 1)
        sustain2 = BlofeldDial(self, self.params.Filter_Envelope_Sustain_2, size=24, name='Sus. 2')
        grid.addWidget(sustain2, 1, 3, 1, 1)
        release = BlofeldDial(self, self.params.Filter_Envelope_Release, size=24)
        grid.addWidget(release, 0, 4, 1, 1)

        grid.addWidget(OSpacer(min_width=env.minimumWidth(), min_height=40, max_width=80, max_height=env.minimumWidth()), 1, 4, 1, 1)
        grid.addWidget(env, 1, 4, 1, 1)

        env.attackChanged.connect(attack.setValue)
        attack.valueChanged.connect(env.setAttack)
        env.attackLevelChanged.connect(lambda value: attack_level.setValue(value) if mode.currentIndex!=0 else None)
        attack_level.valueChanged.connect(env.setAttackLevel)
        env.sustainChanged.connect(sustain.setValue)
        sustain.valueChanged.connect(env.setSustain)
        env.decayChanged.connect(decay.setValue)
        decay.valueChanged.connect(env.setDecay)
        env.decay2Changed.connect(lambda value: decay2.setValue(value) if mode.currentIndex!=0 else None)
        decay2.valueChanged.connect(env.setDecay2)
        env.sustain2Changed.connect(lambda value: sustain2.setValue(value) if mode.currentIndex!=0 else None)
        sustain2.valueChanged.connect(env.setSustain2)
        env.releaseChanged.connect(release.setValue)
        release.valueChanged.connect(env.setRelease)

        set_enabled(0)

        return frame

    def create_amp_env(self):
        def set_enabled(id):
            if id == 0:
                for w in (attack_level, decay2, sustain2):
                    w.setEnabled(False)
            else:
                for w in (attack_level, decay2, sustain2):
                    w.setEnabled(True)

        frame = Frame(self, 'Amp Env.')
        frame.setContentsMargins(2, 12, 2, 2)
        env = BlofeldEnv(self, 'Amplifier_Envelope', show_points=False)
        env.setFixedSize(68, 40)
        self.envelopes.append(env)
        
        grid = QtGui.QGridLayout()
        frame.setLayout(grid)
        mode = BlofeldCombo(self, self.params.Amplifier_Envelope_Mode, sub_par='Mode')
        mode.internalUpdate.connect(env.setEnvelope)
        mode.internalUpdate.connect(set_enabled)
        grid.addWidget(mode, 0, 0, 1, 1, QtCore.Qt.AlignBottom)
        trigger = BlofeldCombo(self, self.params.Amplifier_Envelope_Mode, sub_par='Trigger')
        grid.addWidget(trigger, 1, 0, 1, 1)
        attack = BlofeldDial(self, self.params.Amplifier_Envelope_Attack, size=24)
        grid.addWidget(attack, 0, 1, 1, 1)
        attack_level = BlofeldDial(self, self.params.Amplifier_Envelope_Attack_Level, size=24, name='A. Level')
        grid.addWidget(attack_level, 1, 1, 1, 1)
        decay = BlofeldDial(self, self.params.Amplifier_Envelope_Decay, size=24)
        grid.addWidget(decay, 0, 2, 1, 1)
        sustain = BlofeldDial(self, self.params.Amplifier_Envelope_Sustain, size=24)
        grid.addWidget(sustain, 0, 3, 1, 1)
        decay2 = BlofeldDial(self, self.params.Amplifier_Envelope_Decay_2, size=24, name='Dec. 2')
        grid.addWidget(decay2, 1, 2, 1, 1)
        sustain2 = BlofeldDial(self, self.params.Amplifier_Envelope_Sustain_2, size=24, name='Sus. 2')
        grid.addWidget(sustain2, 1, 3, 1, 1)
        release = BlofeldDial(self, self.params.Amplifier_Envelope_Release, size=24)
        grid.addWidget(release, 0, 4, 1, 1)

        grid.addWidget(OSpacer(min_width=env.minimumWidth(), min_height=40, max_width=80, max_height=env.minimumWidth()), 1, 4, 1, 1)
        grid.addWidget(env, 1, 4, 1, 1)

        env.attackChanged.connect(attack.setValue)
        attack.valueChanged.connect(env.setAttack)
        env.attackLevelChanged.connect(lambda value: attack_level.setValue(value) if mode.currentIndex!=0 else None)
        attack_level.valueChanged.connect(env.setAttackLevel)
        env.sustainChanged.connect(sustain.setValue)
        sustain.valueChanged.connect(env.setSustain)
        env.decayChanged.connect(decay.setValue)
        decay.valueChanged.connect(env.setDecay)
        env.decay2Changed.connect(lambda value: decay2.setValue(value) if mode.currentIndex!=0 else None)
        decay2.valueChanged.connect(env.setDecay2)
        env.sustain2Changed.connect(lambda value: sustain2.setValue(value) if mode.currentIndex!=0 else None)
        sustain2.valueChanged.connect(env.setSustain2)
        env.releaseChanged.connect(release.setValue)
        release.valueChanged.connect(env.setRelease)

        set_enabled(0)

        return frame

    def create_env_3(self):
        def set_enabled(id):
            if id == 0:
                for w in (attack_level, decay2, sustain2):
                    w.setEnabled(False)
            else:
                for w in (attack_level, decay2, sustain2):
                    w.setEnabled(True)

        frame = Frame(self, 'Envelope 3')
        frame.setContentsMargins(2, 12, 2, 2)
        env = BlofeldEnv(self, 'Envelope_3', show_points=False)
        env.setFixedSize(68, 40)
        self.envelopes.append(env)
        
        grid = QtGui.QGridLayout()
        frame.setLayout(grid)
        mode = BlofeldCombo(self, self.params.Envelope_3_Mode, sub_par='Mode')
        mode.internalUpdate.connect(env.setEnvelope)
        mode.internalUpdate.connect(set_enabled)
        grid.addWidget(mode, 0, 0, 1, 1, QtCore.Qt.AlignBottom)
        trigger = BlofeldCombo(self, self.params.Envelope_3_Mode, sub_par='Trigger')
        grid.addWidget(trigger, 1, 0, 1, 1)
        attack = BlofeldDial(self, self.params.Envelope_3_Attack, size=24)
        grid.addWidget(attack, 0, 1, 1, 1)
        attack_level = BlofeldDial(self, self.params.Envelope_3_Attack_Level, size=24, name='A. Level')
        grid.addWidget(attack_level, 1, 1, 1, 1)
        decay = BlofeldDial(self, self.params.Envelope_3_Decay, size=24)
        grid.addWidget(decay, 0, 2, 1, 1)
        sustain = BlofeldDial(self, self.params.Envelope_3_Sustain, size=24)
        grid.addWidget(sustain, 0, 3, 1, 1)
        decay2 = BlofeldDial(self, self.params.Envelope_3_Decay_2, size=24, name='Dec. 2')
        grid.addWidget(decay2, 1, 2, 1, 1)
        sustain2 = BlofeldDial(self, self.params.Envelope_3_Sustain_2, size=24, name='Sus. 2')
        grid.addWidget(sustain2, 1, 3, 1, 1)
        release = BlofeldDial(self, self.params.Envelope_3_Release, size=24)
        grid.addWidget(release, 0, 4, 1, 1)

        grid.addWidget(OSpacer(min_width=env.minimumWidth(), min_height=40, max_width=80, max_height=env.minimumWidth()), 1, 4, 1, 1)
        grid.addWidget(env, 1, 4, 1, 1)

        env.attackChanged.connect(attack.setValue)
        attack.valueChanged.connect(env.setAttack)
        env.attackLevelChanged.connect(lambda value: attack_level.setValue(value) if mode.currentIndex!=0 else None)
        attack_level.valueChanged.connect(env.setAttackLevel)
        env.sustainChanged.connect(sustain.setValue)
        sustain.valueChanged.connect(env.setSustain)
        env.decayChanged.connect(decay.setValue)
        decay.valueChanged.connect(env.setDecay)
        env.decay2Changed.connect(lambda value: decay2.setValue(value) if mode.currentIndex!=0 else None)
        decay2.valueChanged.connect(env.setDecay2)
        env.sustain2Changed.connect(lambda value: sustain2.setValue(value) if mode.currentIndex!=0 else None)
        sustain2.valueChanged.connect(env.setSustain2)
        env.releaseChanged.connect(release.setValue)
        release.valueChanged.connect(env.setRelease)

        set_enabled(0)

        return frame

    def create_env_4(self):
        def set_enabled(id):
            if id == 0:
                for w in (attack_level, decay2, sustain2):
                    w.setEnabled(False)
            else:
                for w in (attack_level, decay2, sustain2):
                    w.setEnabled(True)

        frame = Frame(self, 'Envelope 4')
        frame.setContentsMargins(2, 12, 2, 2)
        env = BlofeldEnv(self, 'Envelope_4', show_points=False)
        env.setFixedSize(68, 40)
        self.envelopes.append(env)
        
        grid = QtGui.QGridLayout()
        frame.setLayout(grid)
        mode = BlofeldCombo(self, self.params.Envelope_4_Mode, sub_par='Mode')
        mode.internalUpdate.connect(env.setEnvelope)
        mode.internalUpdate.connect(set_enabled)
        grid.addWidget(mode, 0, 0, 1, 1, QtCore.Qt.AlignBottom)
        trigger = BlofeldCombo(self, self.params.Envelope_4_Mode, sub_par='Trigger')
        grid.addWidget(trigger, 1, 0, 1, 1)
        attack = BlofeldDial(self, self.params.Envelope_4_Attack, size=24)
        grid.addWidget(attack, 0, 1, 1, 1)
        attack_level = BlofeldDial(self, self.params.Envelope_4_Attack_Level, size=24, name='A. Level')
        grid.addWidget(attack_level, 1, 1, 1, 1)
        decay = BlofeldDial(self, self.params.Envelope_4_Decay, size=24)
        grid.addWidget(decay, 0, 2, 1, 1)
        sustain = BlofeldDial(self, self.params.Envelope_4_Sustain, size=24)
        grid.addWidget(sustain, 0, 3, 1, 1)
        decay2 = BlofeldDial(self, self.params.Envelope_4_Decay_2, size=24, name='Dec. 2')
        grid.addWidget(decay2, 1, 2, 1, 1)
        sustain2 = BlofeldDial(self, self.params.Envelope_4_Sustain_2, size=24, name='Sus. 2')
        grid.addWidget(sustain2, 1, 3, 1, 1)
        release = BlofeldDial(self, self.params.Envelope_4_Release, size=24)
        grid.addWidget(release, 0, 4, 1, 1)

        grid.addWidget(OSpacer(min_width=env.minimumWidth(), min_height=40, max_width=80, max_height=env.minimumWidth()), 1, 4, 1, 1)
        grid.addWidget(env, 1, 4, 1, 1)

        env.attackChanged.connect(attack.setValue)
        attack.valueChanged.connect(env.setAttack)
        env.attackLevelChanged.connect(lambda value: attack_level.setValue(value) if mode.currentIndex!=0 else None)
        attack_level.valueChanged.connect(env.setAttackLevel)
        env.sustainChanged.connect(sustain.setValue)
        sustain.valueChanged.connect(env.setSustain)
        env.decayChanged.connect(decay.setValue)
        decay.valueChanged.connect(env.setDecay)
        env.decay2Changed.connect(lambda value: decay2.setValue(value) if mode.currentIndex!=0 else None)
        decay2.valueChanged.connect(env.setDecay2)
        env.sustain2Changed.connect(lambda value: sustain2.setValue(value) if mode.currentIndex!=0 else None)
        sustain2.valueChanged.connect(env.setSustain2)
        env.releaseChanged.connect(release.setValue)
        release.valueChanged.connect(env.setRelease)

        set_enabled(0)

        return frame

    def create_mixer(self):
        frame = Frame(self, 'Mixer')
        frame.setContentsMargins(2, 2, 2, 2)
#        layout = QtGui.QVBoxLayout()
#        frame.setLayout(layout)

        grid = QtGui.QGridLayout()
        frame.setLayout(grid)
#        layout.addLayout(grid)
        grid.setRowMinimumHeight(0, 23)
        grid.addWidget(BlofeldSlider(self, self.params.Mixer_Osc_1_Level, name='OSC 1'), 1, 0)
        grid.addWidget(BlofeldDial(self, self.params.Mixer_Osc_1_Balance, size=24, center=True, default=64, name='Bal'), 2, 0)

        grid.addWidget(BlofeldSlider(self, self.params.Mixer_Osc_2_Level, name='OSC 2'), 1, 1)
        grid.addWidget(BlofeldDial(self, self.params.Mixer_Osc_2_Balance, size=24, center=True, default=64, name='Bal'), 2, 1)

        grid.addWidget(BlofeldSlider(self, self.params.Mixer_Osc_3_Level, name='OSC 3'), 1, 2)
        grid.addWidget(BlofeldDial(self, self.params.Mixer_Osc_3_Balance, size=24, center=True, default=64, name='Bal'), 2, 2)

        grid.addWidget(BlofeldSlider(self, self.params.Mixer_RingMod_Level, name='RingMod'), 1, 3)
        grid.addWidget(BlofeldDial(self, self.params.Mixer_RingMod_Balance, size=24, center=True, default=64, name='Bal'), 2, 3)

        noise = QtGui.QVBoxLayout()
        grid.addLayout(noise, 0, 4, 2, 1)
        noise.addWidget(BlofeldDial(self, self.params.Mixer_Noise_Colour, size=24, center=True, default=64))
        noise.addWidget(BlofeldSlider(self, self.params.Mixer_Noise_Level, name='Noise'))
        grid.addWidget(BlofeldDial(self, self.params.Mixer_Noise_Balance, size=24, center=True, default=64, name='Bal'), 2, 4)
        return frame

    def create_osc1(self):
        def set_enable(index):
            if index == 0:
                for w in widget_list:
                    w.setEnabled(False)
            elif index == 1:
                for w in widget_list:
                    w.setEnabled(False if w==limit_wt else True)
            elif index in (2, 3, 4):
                for w in widget_list:
                    w.setEnabled(False if w in normal_disable else True)
            else:
                for w in widget_list:
                    w.setEnabled(True)
        frame = Frame(self, 'OSC 1')
        frame.setContentsMargins(2, 2, 2, 2)
        layout = QtGui.QGridLayout()
        frame.setLayout(layout)

        line1 = QtGui.QHBoxLayout()
        layout.addLayout(line1, 1, 0)

        shape = BlofeldCombo(self, self.params.Osc_1_Shape)
        shape.indexChanged.connect(set_enable)
        line1.addWidget(shape)
        brill = BlofeldDial(self, self.params.Osc_1_Brilliance, size=32)
        line1.addWidget(brill)
        keytrack = BlofeldDial(self, self.params.Osc_1_Keytrack, center=True, size=32, default=64)
        line1.addWidget(keytrack)

        line2 = QtGui.QHBoxLayout()
        layout.addLayout(line2, 2, 0)

        octave = BlofeldDial(self, self.params.Osc_1_Octave, size=32)
        line2.addWidget(octave)
        semitone = BlofeldDial(self, self.params.Osc_1_Semitone, center=True, size=32, default=64)
        line2.addWidget(semitone)
        detune = BlofeldDial(self, self.params.Osc_1_Detune, center=True, size=32, default=64)
        line2.addWidget(detune)
        bend = BlofeldDial(self, self.params.Osc_1_Bend_Range, center=True, size=32, default=64)
        line2.addWidget(bend)


        layout.addWidget(Section(self, border=True, alpha=255), 0, 1, 3, 2)
        layout.addWidget(Section(self, border=True, alpha=255), 0, 3, 3, 1)
        pwm_label = Label(self, 'PWM')
        layout.addWidget(pwm_label, 0, 1, 1, 2)
        fm_label = Label(self, 'FM')
        layout.addWidget(fm_label, 0, 3, 1, 1)

        pwm_source = BlofeldCombo(self, self.params.Osc_1_PWM_Source, name='Source')
        layout.addWidget(pwm_source, 1, 1, 1, 2)
        pulsewidth = BlofeldDial(self, self.params.Osc_1_Pulsewidth, name='Width')
        layout.addWidget(pulsewidth, 2, 1)
        pwm_amount = BlofeldDial(self, self.params.Osc_1_PWM_Amount, name='Amount')
        layout.addWidget(pwm_amount, 2, 2)

        fm_source = BlofeldCombo(self, self.params.Osc_1_FM_Source, name='Source')
        layout.addWidget(fm_source, 1, 3)
        fm_amount = BlofeldDial(self, self.params.Osc_1_FM_Amount, name='Amount')
        layout.addWidget(fm_amount, 2, 3)

        limit_wt = BlofeldButton(self, self.params.Osc_1_Limit_WT, checkable=True, name='Limit WT', inverted=True)
        layout.addWidget(limit_wt, 1, 4, 2, 1, QtCore.Qt.AlignVCenter|QtCore.Qt.AlignHCenter)
        self.osc1_limit_wt = limit_wt

        widget_list = brill, keytrack, octave, semitone, detune, bend, pwm_label, pwm_source, pulsewidth, pwm_amount, fm_label, fm_source, fm_amount, limit_wt
        normal_disable = pwm_label, pwm_source, pulsewidth, pwm_amount, fm_label, fm_source, fm_amount, limit_wt

        return frame

    def create_osc2(self):
        def set_enable(index):
            if index == 0:
                for w in widget_list+(self.osc2_sync, ):
                    w.setEnabled(False)
            elif index == 1:
                for w in widget_list+(self.osc2_sync, ):
                    w.setEnabled(False if w==limit_wt else True)
            elif index in (2, 3, 4):
                for w in widget_list+(self.osc2_sync, ):
                    w.setEnabled(False if w in normal_disable else True)
            else:
                for w in widget_list+(self.osc2_sync, ):
                    w.setEnabled(True)
        frame = Frame(self, 'OSC 2')
        frame.setContentsMargins(2, 2, 2, 2)
        layout = QtGui.QGridLayout()
        frame.setLayout(layout)

        line1 = QtGui.QHBoxLayout()
        layout.addLayout(line1, 1, 0)

        shape = BlofeldCombo(self, self.params.Osc_2_Shape)
        shape.indexChanged.connect(set_enable)
        line1.addWidget(shape)
        brill = BlofeldDial(self, self.params.Osc_2_Brilliance, size=32)
        line1.addWidget(brill)
        keytrack = BlofeldDial(self, self.params.Osc_2_Keytrack, center=True, size=32, default=64)
        line1.addWidget(keytrack)

        line2 = QtGui.QHBoxLayout()
        layout.addLayout(line2, 2, 0)

        octave = BlofeldDial(self, self.params.Osc_2_Octave, size=32)
        line2.addWidget(octave)
        semitone = BlofeldDial(self, self.params.Osc_2_Semitone, center=True, size=32, default=64)
        line2.addWidget(semitone)
        detune = BlofeldDial(self, self.params.Osc_2_Detune, center=True, size=32, default=64)
        line2.addWidget(detune)
        bend = BlofeldDial(self, self.params.Osc_2_Bend_Range, center=True, size=32, default=64)
        line2.addWidget(bend)


        layout.addWidget(Section(self, border=True, alpha=255), 0, 1, 3, 2)
        layout.addWidget(Section(self, border=True, alpha=255), 0, 3, 3, 1)
        pwm_label = Label(self, 'PWM')
        layout.addWidget(pwm_label, 0, 1, 1, 2)
        fm_label = Label(self, 'FM')
        layout.addWidget(fm_label, 0, 3, 1, 1)

        pwm_source = BlofeldCombo(self, self.params.Osc_2_PWM_Source, name='Source')
        layout.addWidget(pwm_source, 1, 1, 1, 2)
        pulsewidth = BlofeldDial(self, self.params.Osc_2_Pulsewidth, name='Width')
        layout.addWidget(pulsewidth, 2, 1)
        pwm_amount = BlofeldDial(self, self.params.Osc_2_PWM_Amount, name='Amount')
        layout.addWidget(pwm_amount, 2, 2)

        fm_source = BlofeldCombo(self, self.params.Osc_2_FM_Source, name='Source')
        layout.addWidget(fm_source, 1, 3)
        fm_amount = BlofeldDial(self, self.params.Osc_2_FM_Amount, name='Amount')
        layout.addWidget(fm_amount, 2, 3)

        limit_wt = BlofeldButton(self, self.params.Osc_2_Limit_WT, checkable=True, name='Limit WT', inverted=True)
        layout.addWidget(limit_wt, 1, 4, 2, 1, QtCore.Qt.AlignVCenter|QtCore.Qt.AlignHCenter)
        self.osc2_limit_wt = limit_wt

        widget_list = brill, keytrack, octave, semitone, detune, bend, pwm_label, pwm_source, pulsewidth, pwm_amount, fm_label, fm_source, fm_amount, limit_wt
        normal_disable = pwm_label, pwm_source, pulsewidth, pwm_amount, fm_label, fm_source, fm_amount, limit_wt

        return frame

    def create_osc3(self):
        def set_enable(index):
            if index == 0:
                for w in widget_list:
                    w.setEnabled(False)
            elif index == 1:
                for w in widget_list:
                    w.setEnabled(False if w==limit_wt else True)
            elif index in (2, 3, 4):
                for w in widget_list:
                    w.setEnabled(False if w in normal_disable else True)
        frame = Frame(self, 'OSC 3')
        frame.setContentsMargins(2, 2, 2, 2)
        layout = QtGui.QGridLayout()
        frame.setLayout(layout)

        line1 = QtGui.QHBoxLayout()
        layout.addLayout(line1, 1, 0)

        shape = BlofeldCombo(self, self.params.Osc_3_Shape)
        shape.indexChanged.connect(set_enable)
        line1.addWidget(shape)
        brill = BlofeldDial(self, self.params.Osc_3_Brilliance, size=32)
        line1.addWidget(brill)
        keytrack = BlofeldDial(self, self.params.Osc_3_Keytrack, center=True, size=32, default=64)
        line1.addWidget(keytrack)

        line2 = QtGui.QHBoxLayout()
        layout.addLayout(line2, 2, 0)

        octave = BlofeldDial(self, self.params.Osc_3_Octave, size=32)
        line2.addWidget(octave)
        semitone = BlofeldDial(self, self.params.Osc_3_Semitone, center=True, size=32, default=64)
        line2.addWidget(semitone)
        detune = BlofeldDial(self, self.params.Osc_3_Detune, center=True, size=32, default=64)
        line2.addWidget(detune)
        bend = BlofeldDial(self, self.params.Osc_3_Bend_Range, center=True, size=32, default=64)
        line2.addWidget(bend)


        layout.addWidget(Section(self, border=True, alpha=255), 0, 1, 3, 2)
        layout.addWidget(Section(self, border=True, alpha=255), 0, 3, 3, 1)
        pwm_label = Label(self, 'PWM')
        layout.addWidget(pwm_label, 0, 1, 1, 2)
        fm_label = Label(self, 'FM')
        layout.addWidget(fm_label, 0, 3, 1, 1)

        pwm_source = BlofeldCombo(self, self.params.Osc_3_PWM_Source, name='Source')
        layout.addWidget(pwm_source, 1, 1, 1, 2)
        pulsewidth = BlofeldDial(self, self.params.Osc_3_Pulsewidth, name='Width')
        layout.addWidget(pulsewidth, 2, 1)
        pwm_amount = BlofeldDial(self, self.params.Osc_3_PWM_Amount, name='Amount')
        layout.addWidget(pwm_amount, 2, 2)

        fm_source = BlofeldCombo(self, self.params.Osc_3_FM_Source, name='Source')
        layout.addWidget(fm_source, 1, 3)
        fm_amount = BlofeldDial(self, self.params.Osc_3_FM_Amount, name='Amount')
        layout.addWidget(fm_amount, 2, 3)

        self.osc2_sync = BlofeldButton(self, self.params.Osc_2_Sync_to_O3, checkable=True, name='OSC2\nsync')
        layout.addWidget(self.osc2_sync, 1, 4, 2, 1, QtCore.Qt.AlignVCenter|QtCore.Qt.AlignHCenter)

        widget_list = brill, keytrack, octave, semitone, detune, bend, pwm_label, pwm_source, pulsewidth, pwm_amount, fm_label, fm_source, fm_amount
        normal_disable = pwm_label, pwm_source, pulsewidth, pwm_amount, fm_label, fm_source, fm_amount

        return frame

