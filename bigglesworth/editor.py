import pickle
from string import uppercase
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
    def __init__(self, parent, param_tuple, sub_par=None, *args, **kwargs):
        if len(param_tuple) == 7:
            full_range, values, name, short_name, family, attr, id = param_tuple
        else:
            full_range, values, name, short_name, family, attr= param_tuple
        if 'name' in kwargs:
            short_name = kwargs.pop('name')
        if 'values' in kwargs:
            values = kwargs.pop('values')
        if not (isinstance(values, list) or isinstance(values, tuple)):
            values = getattr(values, sub_par)
        Combo.__init__(self, parent=parent, value_list=values, name=short_name, *args, **kwargs)
        parent.object_dict[attr].add(self, sub_par)
        self.attr = attr
        self.main = parent
        self.indexChanged.connect(lambda id: setattr(self.main, self.attr, id if sub_par is None else (id, sub_par)))

class BlofeldEnv(Envelope):
    def __init__(self, parent, env_name, *args, **kwargs):
        Envelope.__init__(self, parent, *args, **kwargs)
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
            self.setFixedSize(240, 120)
            self.move(self.parent().mapToGlobal(self.normal_pos))
            self.show()
            self.activateWindow()
            self.normal = False
            self.changing = True
            self.setShowPoints(True)

    def activateWindow(self):
        Envelope.activateWindow(self)
        QtCore.QTimer.singleShot(10, self.setMaximized)

    def normalize(self):
        self.setFixedSize(80, 40)
        self.setWindowFlags(QtCore.Qt.Widget)
        self.normal_layout.addWidget(self, *self.index)
        self.normal = True
        self.normal_pos = self.pos()
        self.setShowPoints(False)

    def leaveEvent(self, event):
        if self.changing: return
        if not self.normal:
            self.normalize()

class BaseDisplayWidget(QtGui.QGraphicsWidget):
    pen = brush = QtGui.QColor(30, 50, 40)

class DownArrowWidget(BaseDisplayWidget):
    arrow = QtGui.QPainterPath()
    arrow.moveTo(-4, -2)
    arrow.lineTo(4, -2)
    arrow.lineTo(0, 2)
    arrow.closeSubpath()
    def __init__(self, parent):
        BaseDisplayWidget.__init__(self, parent)
        width = self.arrow.boundingRect().width()+2
        height = self.arrow.boundingRect().height()+2
        self.setMinimumSize(width, height)
#        self.setMaximumSize(width+2, height+2)
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

class LabelTextWidget(BaseTextWidget):
    def __init__(self, text, parent):
        BaseTextWidget.__init__(self, text, parent)
        self.font = QtGui.QFont('Fira Sans', 22)
        self.font_metrics = QtGui.QFontMetrics(self.font)
        self.setMinimumSize(self.font_metrics.width(self.text), self.font_metrics.height())

class SmallLabelTextWidget(BaseTextWidget):
    def __init__(self, text, parent, fixed=False):
        BaseTextWidget.__init__(self, text, parent)
        self.font = QtGui.QFont('Fira Sans', 12)
        self.font_metrics = QtGui.QFontMetrics(self.font)
        self.setMinimumSize(self.font_metrics.width(self.text), self.font_metrics.height())
        self.setMaximumHeight(self.font_metrics.height())
        if fixed:
            self.setMaximumWidth(self.font_metrics.width(self.text))

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
#        self.setViewportUpdateMode(QtGui.QGraphicsView.FullViewportUpdate)

    def create_layout(self):
        panel = QtGui.QGraphicsWidget()
        self.panel = panel
        self.scene.addItem(panel)
        layout = QtGui.QGraphicsGridLayout()
        layout.setSpacing(0)
        panel.setLayout(layout)

        self.edit_mode_label = SmallLabelTextWidget('Sound mode Edit buffer', panel)
#        self.edit_mode_label.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        layout.addItem(self.edit_mode_label, 0, 0)
        self.prog_name = LabelTextWidget('Mini moog super', panel)
        layout.addItem(self.prog_name, 1, 0)

        self.status_bar = QtGui.QGraphicsGridLayout()
        layout.addItem(self.status_bar, 2, 0)
        status_lbl = SmallLabelTextWidget('Status:', panel, fixed=True)
        self.status_bar.addItem(status_lbl, 0, 0, QtCore.Qt.AlignLeft)

        self.status = SmallLabelTextWidget('Ready', panel)
        self.status_bar.addItem(self.status, 0, 1, QtCore.Qt.AlignLeft)

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

        self.panel.setGraphicsEffect(self.shadow)

    def mousePressEvent(self, event):
        item = self.scene.itemAt(event.pos())
        if item is None: return
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
                cat_list = self.main.sorted_library.by_cat[cat+1]
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
                cat_list = self.main.sorted_library.by_cat[cat-1]
                if not len(cat_list):
                    cat -= 1
                    continue
                else:
                    sound = cat_list[0]
                    break
            bank = sound.bank
            prog = sound.prog
        else:
            if event.button() == QtCore.Qt.RightButton:
                if item == self.prog_name:
                    res = self.main.sorted_library_menu.exec_(event.globalPos())
                    if not res: return
                    self.main.setSound(*res.data().toPyObject(), pgm_send=True)
                    return
                elif item == self.bank:
                    res = self.main.sorted_library_menu.actions()[0].menu().exec_(event.globalPos())
                    if not res: return
                    self.main.setSound(*res.data().toPyObject(), pgm_send=True)
                    return
                elif item == self.prog:
                    res = self.main.sorted_library_menu.actions()[0].menu().actions()[bank].menu().exec_(event.globalPos())
                    if not res: return
                    self.main.setSound(*res.data().toPyObject(), pgm_send=True)
                    return
                elif item in [self.cat_label, self.cat_name]:
                    res = self.main.sorted_library_menu.actions()[1].menu().exec_(event.globalPos())
                    if not res: return
                    self.main.setSound(*res.data().toPyObject(), pgm_send=True)
                    return
                else:
                    return
            else:
                return
        self.main.setSound(bank, prog, pgm_send=True)

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
                cat_list = self.main.sorted_library.by_cat[cat]
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

    def paintEvent(self, event):
        qp = QtGui.QPainter(self.viewport())
        qp.setRenderHints(QtGui.QPainter.Antialiasing)
        qp.translate(.5, .5)
        qp.setPen(self.border_pen)
        qp.setBrush(self.bgd_brush)
        qp.drawRoundedRect(self.border_rect, 4, 4)
        qp.setPen(QtGui.QColor(220, 220, 220, 220))
        qp.setBrush(QtGui.QColor(220, 220, 220, 50))
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
        self.status.text = text
        self.update()
        self.panel.update()

    def setSound(self):
        sound = self.main.sound
        self.prog_name.text = sound.name
        self.bank.text = uppercase[sound.bank]
        self.prog.text = '{:03}'.format(sound.prog+1)
        self.cat_name.text = categories[sound.cat]
        self.update()
        self.panel.update()

class BlofeldDisplayz(QtGui.QWidget):
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
    fgd_brush = QtGui.QBrush(QtGui.QColor(240, 250, 250))
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        self._font_db = QtGui.QFontDatabase()
#        self._font_db.addApplicationFont(local_path('erbos.ttf'))
#        self.name_font = QtGui.QFont('Erbos Draco 1st Open NBP', 16)
        self._font_db.addApplicationFont(local_path('FiraSans-Regular.ttf'))
        self.name_font = QtGui.QFont('Fira Sans', 22)
        self.name_font_metrics = QtGui.QFontMetrics(self.name_font)
        self.setSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Expanding)
        self.name = '...'

    def setName(self, name):
        self.name = name
        self.text_rect = QtCore.QRect(self.display_rect.x()+2, self.display_rect.y()+2, self.name_font_metrics.width(self.name), self.display_rect.height()-2)
        self.update()

    def paintEvent(self, event):
        qp = QtGui.QPainter()
        qp.begin(self)
        qp.setRenderHints(QtGui.QPainter.Antialiasing)
        qp.translate(.5, .5)

        qp.setPen(self.border_pen)
        qp.setBrush(self.fgd_brush)
        qp.drawRoundedRect(self.border_rect, 2, 2)
        qp.drawRoundedRect(self.display_rect, 2, 2)

        qp.setPen(QtCore.Qt.lightGray)
        qp.setFont(self.name_font)
        qp.drawText(self.text_rect.adjusted(1, 1, 1, 1), 0, self.name)

        qp.setPen(QtCore.Qt.black)
        qp.setFont(self.name_font)
        qp.drawText(self.text_rect, 0, self.name)

        qp.end()

    def resizeEvent(self, event):
        width = self.width()
        height = self.height()
        self.border_rect = QtCore.QRect(0, 0, width-1, height-1)
        self.display_rect = self.border_rect.adjusted(2, 2, -2, -2)
        self.text_rect = QtCore.QRect(self.display_rect.x()+2, self.display_rect.y()+2, self.name_font_metrics.width(self.name), self.display_rect.height()-2)

class Editor(QtGui.QMainWindow):
    object_dict = {attr:ParamObject(param_tuple) for attr, param_tuple in Params.param_names.items()}
    with open(local_path('blofeld_efx'), 'rb') as _fx:
        efx_params = pickle.load(_fx)
    with open(local_path('blofeld_efx_ranges'), 'rb') as _fx:
        efx_ranges = pickle.load(_fx)

    def __init__(self, parent):
        QtGui.QMainWindow.__init__(self, parent=None)
        load_ui(self, 'editor.ui')
        self.setContentsMargins(2, 2, 2, 2)
        pal = self.palette()
        pal.setColor(self.backgroundRole(), QtGui.QColor(20, 20, 20))
        self.setPalette(pal)

        self.main = parent
        self.sorted_library = None
        self.sorted_library_menu = None
        self.blofeld_library = self.main.blofeld_library
        self.create_sorted_library()
        self.alsa = self.main.alsa
        self.seq = self.main.seq
        self.channel = 0
        self.octave = 0
        self.params = Params
        self.pgm_send = False
        self.send = False
        self.notify = True
        self.envelopes = []
        self.grid = self.centralWidget().layout()

        self.grid.addLayout(self.create_display(), 0, 1, 1, 2)
        logo = QtGui.QIcon(local_path('logo.svg')).pixmap(QtCore.QSize(160, 160)).toImage()
        logo_widget = QtGui.QLabel()
        logo_widget.setPixmap(QtGui.QPixmap().fromImage(logo))
        self.grid.addWidget(logo_widget, 0, 3, 1, 1, QtCore.Qt.AlignBottom|QtCore.Qt.AlignRight)


        self.grid.addWidget(self.create_mixer(), 0, 0, 2, 1)

        amp_layout = QtGui.QVBoxLayout()
        amp_layout.addWidget(self.create_amplifier())
        amp_layout.addWidget(self.create_glide())
        amp_layout.addWidget(self.create_common())
        self.grid.addLayout(amp_layout, 2, 0, 2, 1)

        self.grid.addWidget(VSpacer(min_height=60), 0, 1, 1, 1)
        self.grid.addWidget(self.create_osc1(), 1, 1, 1, 2)
        self.grid.addWidget(self.create_osc2(), 2, 1, 1, 2)
        self.grid.addWidget(self.create_osc3(), 3, 1, 1, 2)

        self.grid.addWidget(self.create_lfo1(), 1, 3, 1, 1)
        self.grid.addWidget(self.create_lfo2(), 2, 3, 1, 1)
        self.grid.addWidget(self.create_lfo3(), 3, 3, 1, 1)

        self.grid.addWidget(self.create_filter_sel(), 0, 4, 4, 2)
        self.grid.addWidget(self.create_filter1(), 1, 4, 3, 1)
        self.grid.addWidget(self.create_filter2(), 1, 5, 3, 1)
#        self.grid.addWidget(self.create_effects(), 4, 1, 1, 2)
        self.grid.addLayout(self.create_envelopes(), 4, 0, 3, 3)
        
        efx_layout = QtGui.QHBoxLayout()
        efx_layout.addWidget(self.create_effect_1())
        efx_layout.addWidget(self.create_effect_2())
        self.grid.addLayout(efx_layout, 4, 3, 1, 2)

#        self.grid.addWidget(self.create_arp(), 4, 5)

        self.keyboard = Piano(self, key_list=note_keys)
        self.keyboard.noteEvent.connect(self.send_note)

        self.grid.addWidget(self.keyboard, 5, 3, 1, 2)
        self.grid.addWidget(self.create_key_config(), 5, 5, 1, 1)

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
        all_notes_off = SquareButton(self, color=QtCore.Qt.darkRed, max_size=12)
        all_notes_off.clicked.connect(lambda: self.send_ctrl(123, 0))
        notes_off_layout.addWidget(all_notes_off)
        notes_off_layout.addWidget(Label(self, 'All notes OFF'), QtCore.Qt.AlignLeft)

        sounds_off_layout = QtGui.QHBoxLayout()
        layout.addLayout(sounds_off_layout, 2, 1, 1, 2)
        all_sounds_off = SquareButton(self, color=QtCore.Qt.darkRed, max_size=12)
        all_sounds_off.clicked.connect(lambda: self.send_ctrl(120, 0))
        sounds_off_layout.addWidget(all_sounds_off)
        sounds_off_layout.addWidget(Label(self, 'All sounds OFF'), QtCore.Qt.AlignLeft)

        return frame

    def create_arp(self):
        def fade(op):
            if op <= 0: return
            op -= .2
            opacity.setOpacity(op)
            QtCore.QTimer.singleShot(30, lambda: fade(op))
        frame = Frame(self, 'Arpegg.')
        frame.setContentsMargins(2, 2, 2, 2)
        layout = QtGui.QGridLayout()
        frame.setLayout(layout)

        mode_layout = QtGui.QHBoxLayout()
        layout.addLayout(mode_layout, 0, 0)
        mode_layout.addWidget(HSpacer())
        arp_mode = BlofeldCombo(self, self.params.Arpeggiator_Mode, name='', values=['off', 'on', '1 shot', 'Hold'])
        mode_layout.addWidget(arp_mode)
        opacity = QtGui.QGraphicsOpacityEffect()
        opacity.setOpacity(1)
        frame.setGraphicsEffect(opacity)
        b = QtGui.QPushButton('op')
        layout.addWidget(b)
        b.clicked.connect(lambda: fade(1))

        return frame

    def create_sorted_library(self):
        sorted_library = SortedLibrary(self.blofeld_library)
        del self.sorted_library_menu
        menu = QtGui.QMenu()
        by_bank = QtGui.QMenu('By bank', menu)
        menu.addMenu(by_bank)
        for id, bank in enumerate(sorted_library.by_bank):
            if not any(bank): continue
            bank_menu = QtGui.QMenu(uppercase[id], by_bank)
            by_bank.addMenu(bank_menu)
            for sound in bank:
                if sound is None: continue
                item = QtGui.QAction('{:03} {}'.format(sound.prog+1, sound.name), bank_menu)
                item.setData((sound.bank, sound.prog))
                bank_menu.addAction(item)
        by_cat = QtGui.QMenu('By category', menu)
        menu.addMenu(by_cat)
        for cid, cat in enumerate(categories):
            cat_menu = QtGui.QMenu(by_cat)
            by_cat.addMenu(cat_menu)
            cat_len = 0
            for sound in sorted_library.by_cat[cid]:
                cat_len += 1
                item = QtGui.QAction(sound.name, cat_menu)
                item.setData((sound.bank, sound.prog))
                cat_menu.addAction(item)
            if not len(cat_menu.actions()):
                cat_menu.setEnabled(False)
            cat_menu.setTitle('{} ({})'.format(cat, cat_len))
        by_alpha = QtGui.QMenu('Alphabetical', menu)
        menu.addMenu(by_alpha)
        for alpha in sorted(sorted_library.by_alpha.keys()):
            alpha_menu = QtGui.QMenu(by_alpha)
            by_alpha.addMenu(alpha_menu)
            alpha_len = 0
            for sound in sorted_library.by_alpha[alpha]:
                alpha_len += 1
                item = QtGui.QAction(sound.name, alpha_menu)
                item.setData((sound.bank, sound.prog))
                alpha_menu.addAction(item)
            if not len(alpha_menu.actions()):
                alpha_menu.setEnabled(False)
            alpha_menu.setTitle('{} ({})'.format(alpha, alpha_len))
        self.sorted_library_menu = menu
        self.sorted_library = sorted_library

    def send_value(self, attr, value):
        location = 0
        par_id = Params.index_from_attr(attr)
        par_high, par_low = divmod(par_id, 128)
#        print par_high, par_low, value
        
        req = SysExEvent(1, [0xF0, 0x3e, 0x13, 0x00, 0x20, location, par_high, par_low, value, 0xf7])
        req.source = self.alsa.output.client.id, self.alsa.output.id
        self.seq.output_event(req.get_event())
        self.seq.drain_output()

    def send_ctrl(self, param, value):
        ctrl_event = CtrlEvent(1, self.channel, param, value)
        ctrl_event.source = self.alsa.output.client.id, self.alsa.output.id
        self.seq.output_event(ctrl_event.get_event())
        self.seq.drain_output()

    def send_note(self, note, state):
        note = note+self.octave*12
        if state:
            note_event = NoteOnEvent(1, self.channel, note, state)
        else:
            note_event = NoteOffEvent(1, self.channel, note)
        note_event.source = self.alsa.output.client.id, self.alsa.output.id
        self.seq.output_event(note_event.get_event())
        self.seq.drain_output()

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
            self.main.program_change_request(sound.bank, sound.prog)

    def create_display(self):
        layout = QtGui.QGridLayout()
        self.display = BlofeldDisplay(self)
        layout.addWidget(self.display, 0, 0, 2, 1)
        self.pgm_send_btn = SquareButton(self, 'PGM send', checkable=True, checked=False)
        self.pgm_send_btn.toggled.connect(lambda state: setattr(self, 'pgm_send', state))
        self.pgm_send_btn.toggled.connect(lambda state: self.display.statusUpdate('PGM send: {}'.format('enabled' if state else 'disabled')))
        layout.addWidget(self.pgm_send_btn, 0, 1)
        self.send_btn = SquareButton(self, 'MIDI send', checkable=True, checked=False)
        self.send_btn.toggled.connect(lambda state: setattr(self, 'send', state))
        self.send_btn.toggled.connect(lambda state: self.display.statusUpdate('MIDI send: {}'.format('enabled' if state else 'disabled')))
        layout.addWidget(self.send_btn, 1, 1)

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
        pitch_layout.addWidget(VSpacer(min_height=12), 0, 0, 1, 1)
        pitch_layout.addWidget(Label(self, 'Pitch'), 1, 0, 1, 1)
        pitch_amount = BlofeldDial(self, self.params.Osc_Pitch_Amount, size=24)
        pitch_layout.addWidget(pitch_amount, 1, 1, 1, 1)
        pitch_src = BlofeldCombo(self, self.params.Osc_Pitch_Source)
        pitch_layout.addWidget(pitch_src, 2, 0, 1, 2)

        uni_layout = QtGui.QGridLayout()
        layout.addLayout(uni_layout)
        alloc = BlofeldCombo(self, self.params.Allocation_Mode_and_Unisono, sub_par='Allocation', name='Allocation')
        uni_layout.addWidget(alloc, 0, 0, 1, 2)
        unisono = BlofeldCombo(self, self.params.Allocation_Mode_and_Unisono, sub_par='Unisono', name='Unisono')
        uni_layout.addWidget(unisono, 1, 0, 1, 1, QtCore.Qt.AlignHCenter)
        detune = BlofeldDial(self, self.params.Unisono_Uni_Detune, size=24, name='Detune')
        uni_layout.addWidget(detune, 1, 1, 1, 1)

        return frame

    def create_amp_effects(self):
        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.create_amplifier())
#        layout.addWidget(self.create_effect_1())
#        layout.addWidget(self.create_effect_2())
        layout.addWidget(self.create_glide())
#        layout.addWidget(self.create_mixer())
        return layout

    def create_glide(self):
        frame = Frame(self, 'Glide')
        frame.setContentsMargins(2, 12, 2, 2)
        layout = QtGui.QHBoxLayout()
        frame.setLayout(layout)

        switch = BlofeldButton(self, self.params.Glide, checkable=True, name='')
        layout.addWidget(switch, alignment=QtCore.Qt.AlignBottom)

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
            
        frame = Frame(self, 'Effect 1')
        layout = QtGui.QVBoxLayout()
        frame.setLayout(layout)
        frame.setContentsMargins(2, 2, 2, 2)

        line1 = QtGui.QHBoxLayout()
        layout.addLayout(line1)
        line1.addWidget(HSpacer(max_width=70))
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
            
        frame = Frame(self, 'Effect 2')
        layout = QtGui.QVBoxLayout()
        frame.setLayout(layout)
        frame.setContentsMargins(2, 2, 2, 2)

        line1 = QtGui.QHBoxLayout()
        layout.addLayout(line1)
        line1.addWidget(HSpacer(max_width=70))
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
        combos.addWidget(Section(self, border=True), 4, 0, 2, 3)
        combos.addWidget(pan_label, 4, 0)
        pan_source = BlofeldCombo(self, self.params.Filter_1_Pan_Source, name='')
        combos.addWidget(pan_source, 5, 0)
        pan_amount = BlofeldDial(self, self.params.Filter_1_Pan_Amount, name='Amount')
        combos.addWidget(pan_amount, 4, 1, 2, 1, QtCore.Qt.AlignBottom)

        grid.addLayout(combos, 4, 0, 1, 2)

        keytrack = BlofeldDial(self, self.params.Filter_1_Keytrack, size=24)
        grid.addWidget(keytrack, 5, 0, 1, 1)
        pan = BlofeldDial(self, self.params.Filter_1_Pan, size=24)
        grid.addWidget(pan, 5, 1, 1, 1)

        return frame

    def create_filter2(self):
        frame = Frame(self, '1')
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
        combos.addWidget(Section(self, border=True), 4, 0, 2, 3)
        combos.addWidget(pan_label, 4, 0)
        pan_source = BlofeldCombo(self, self.params.Filter_2_Pan_Source, name='')
        combos.addWidget(pan_source, 5, 0)
        pan_amount = BlofeldDial(self, self.params.Filter_2_Pan_Amount, name='Amount')
        combos.addWidget(pan_amount, 4, 1, 2, 1, QtCore.Qt.AlignBottom)

        grid.addLayout(combos, 4, 0, 1, 2)

        keytrack = BlofeldDial(self, self.params.Filter_2_Keytrack, size=24)
        grid.addWidget(keytrack, 5, 0, 1, 1)
        pan = BlofeldDial(self, self.params.Filter_2_Pan, size=24)
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
        def show_env(event):
            pos = env.mapToGlobal(QtCore.QPoint(0, 0))
            env.setWindowFlags(QtCore.Qt.FramelessWindowHint|QtCore.Qt.Tool|QtCore.Qt.ToolTip)
            env.setFixedSize(240, 120)
            env.move(pos)
            env.show()
            env.activateWindow()
        def hide_env(event):
            env.setWindowFlags(QtCore.Qt.Widget)
        def set_enabled(id):
            if id == 0:
                for w in (attack_level, decay2, sustain2):
                    w.setEnabled(False)
            else:
                for w in (attack_level, decay2, sustain2):
                    w.setEnabled(True)

        frame = Frame(self, 'Filter Envelope')
        frame.setContentsMargins(2, 12, 2, 2)
        env = BlofeldEnv(self, 'Filter_Envelope', show_points=False)
        env.setFixedSize(80, 40)
        self.envelopes.append(env)
        
        grid = QtGui.QGridLayout()
        frame.setLayout(grid)
        mode = BlofeldCombo(self, self.params.Filter_Envelope_Mode, sub_par='Mode')
        mode.indexChanged.connect(env.setEnvelope)
        mode.indexChanged.connect(set_enabled)
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
        decay2 = BlofeldDial(self, self.params.Filter_Envelope_Decay_2, size=24)
        grid.addWidget(decay2, 1, 2, 1, 1)
        sustain2 = BlofeldDial(self, self.params.Filter_Envelope_Sustain_2, size=24)
        grid.addWidget(sustain2, 1, 3, 1, 1)
        release = BlofeldDial(self, self.params.Filter_Envelope_Release, size=24)
        grid.addWidget(release, 0, 4, 1, 1)

        grid.addWidget(OSpacer(min_width=80, min_height=40, max_width=80, max_height=40), 1, 4, 1, 1)
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
        def show_env(event):
            pos = env.mapToGlobal(QtCore.QPoint(0, 0))
            env.setWindowFlags(QtCore.Qt.FramelessWindowHint|QtCore.Qt.Tool|QtCore.Qt.ToolTip)
            env.setFixedSize(240, 120)
            env.move(pos)
            env.show()
            env.activateWindow()
        def hide_env(event):
            env.setWindowFlags(QtCore.Qt.Widget)
        def set_enabled(id):
            if id == 0:
                for w in (attack_level, decay2, sustain2):
                    w.setEnabled(False)
            else:
                for w in (attack_level, decay2, sustain2):
                    w.setEnabled(True)

        frame = Frame(self, 'Amp Envelope')
        frame.setContentsMargins(2, 12, 2, 2)
        env = BlofeldEnv(self, 'Amplifier_Envelope', show_points=False)
        env.setFixedSize(80, 40)
        self.envelopes.append(env)
        
        grid = QtGui.QGridLayout()
        frame.setLayout(grid)
        mode = BlofeldCombo(self, self.params.Amplifier_Envelope_Mode, sub_par='Mode')
        mode.indexChanged.connect(env.setEnvelope)
        mode.indexChanged.connect(set_enabled)
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
        decay2 = BlofeldDial(self, self.params.Amplifier_Envelope_Decay_2, size=24)
        grid.addWidget(decay2, 1, 2, 1, 1)
        sustain2 = BlofeldDial(self, self.params.Amplifier_Envelope_Sustain_2, size=24)
        grid.addWidget(sustain2, 1, 3, 1, 1)
        release = BlofeldDial(self, self.params.Amplifier_Envelope_Release, size=24)
        grid.addWidget(release, 0, 4, 1, 1)

        grid.addWidget(OSpacer(min_width=80, min_height=40, max_width=80, max_height=40), 1, 4, 1, 1)
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
        def show_env(event):
            pos = env.mapToGlobal(QtCore.QPoint(0, 0))
            env.setWindowFlags(QtCore.Qt.FramelessWindowHint|QtCore.Qt.Tool|QtCore.Qt.ToolTip)
            env.setFixedSize(240, 120)
            env.move(pos)
            env.show()
            env.activateWindow()
        def hide_env(event):
            env.setWindowFlags(QtCore.Qt.Widget)
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
        env.setFixedSize(80, 40)
        self.envelopes.append(env)
        
        grid = QtGui.QGridLayout()
        frame.setLayout(grid)
        mode = BlofeldCombo(self, self.params.Envelope_3_Mode, sub_par='Mode')
        mode.indexChanged.connect(env.setEnvelope)
        mode.indexChanged.connect(set_enabled)
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
        decay2 = BlofeldDial(self, self.params.Envelope_3_Decay_2, size=24)
        grid.addWidget(decay2, 1, 2, 1, 1)
        sustain2 = BlofeldDial(self, self.params.Envelope_3_Sustain_2, size=24)
        grid.addWidget(sustain2, 1, 3, 1, 1)
        release = BlofeldDial(self, self.params.Envelope_3_Release, size=24)
        grid.addWidget(release, 0, 4, 1, 1)

        grid.addWidget(OSpacer(min_width=80, min_height=40, max_width=80, max_height=40), 1, 4, 1, 1)
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
        def show_env(event):
            pos = env.mapToGlobal(QtCore.QPoint(0, 0))
            env.setWindowFlags(QtCore.Qt.FramelessWindowHint|QtCore.Qt.Tool|QtCore.Qt.ToolTip)
            env.setFixedSize(240, 120)
            env.move(pos)
            env.show()
            env.activateWindow()
        def hide_env(event):
            env.setWindowFlags(QtCore.Qt.Widget)
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
        env.setFixedSize(80, 40)
        self.envelopes.append(env)
        
        grid = QtGui.QGridLayout()
        frame.setLayout(grid)
        mode = BlofeldCombo(self, self.params.Envelope_4_Mode, sub_par='Mode')
        mode.indexChanged.connect(env.setEnvelope)
        mode.indexChanged.connect(set_enabled)
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
        decay2 = BlofeldDial(self, self.params.Envelope_4_Decay_2, size=24)
        grid.addWidget(decay2, 1, 2, 1, 1)
        sustain2 = BlofeldDial(self, self.params.Envelope_4_Sustain_2, size=24)
        grid.addWidget(sustain2, 1, 3, 1, 1)
        release = BlofeldDial(self, self.params.Envelope_4_Release, size=24)
        grid.addWidget(release, 0, 4, 1, 1)

        grid.addWidget(OSpacer(min_width=80, min_height=40, max_width=80, max_height=40), 1, 4, 1, 1)
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
        frame = Frame(self, 'OSC 1')
        layout = QtGui.QHBoxLayout()
        frame.setLayout(layout)

        left = QtGui.QVBoxLayout()
        layout.addLayout(left)
        line1 = QtGui.QHBoxLayout()
        left.addLayout(line1)

        shape = BlofeldCombo(self, self.params.Osc_1_Shape)
        line1.addWidget(shape)
        brill = BlofeldDial(self, self.params.Osc_1_Brilliance, size=32)
        line1.addWidget(brill)
        keytrack = BlofeldDial(self, self.params.Osc_1_Keytrack, center=True, size=32, default=64)
        line1.addWidget(keytrack)

        line2 = QtGui.QHBoxLayout()
        left.addLayout(line2)

        octave = BlofeldDial(self, self.params.Osc_1_Octave, size=32)
        line2.addWidget(octave)
        semitone = BlofeldDial(self, self.params.Osc_1_Semitone, center=True, size=32, default=64)
        line2.addWidget(semitone)
        detune = BlofeldDial(self, self.params.Osc_1_Detune, center=True, size=32, default=64)
        line2.addWidget(detune)
        bend = BlofeldDial(self, self.params.Osc_1_Bend_Range, center=True, size=32, default=64)
        line2.addWidget(bend)

        right = QtGui.QGridLayout()
        layout.addLayout(right)

        right.addWidget(Section(self), 0, 0, 3, 2)
        right.addWidget(Section(self), 0, 2, 3, 1)
        pwm_label = Label(self, 'PWM')
        right.addWidget(pwm_label, 0, 0, 1, 2)
        fm_label = Label(self, 'FM')
        right.addWidget(fm_label, 0, 2, 1, 1)

        pwm_source = BlofeldCombo(self, self.params.Osc_1_PWM_Source, name='Source')
        right.addWidget(pwm_source, 1, 0, 1, 2)
        fm_source = BlofeldCombo(self, self.params.Osc_1_FM_Source, name='Source')
        right.addWidget(fm_source, 1, 2, 1, 1)
        pulsewidth = BlofeldDial(self, self.params.Osc_1_Pulsewidth, size=24, name='Width')
        right.addWidget(pulsewidth, 2, 0, 1, 1)
        pwm_amount = BlofeldDial(self, self.params.Osc_1_PWM_Amount, size=24, name='Amount')
        right.addWidget(pwm_amount, 2, 1, 1, 1)
        fm_amount = BlofeldDial(self, self.params.Osc_1_FM_Amount, size=24, name='Amount')
        right.addWidget(fm_amount, 2, 2, 1, 1)
        limit_wt = BlofeldButton(self, self.params.Osc_1_Limit_WT, checkable=True, name='Limit WT', inverted=True)
        right.addWidget(limit_wt, 0, 3, 3, 1)

        return frame

    def create_osc2(self):
        frame = Frame(self, 'OSC 2')
        layout = QtGui.QHBoxLayout()
        frame.setLayout(layout)

        left = QtGui.QVBoxLayout()
        layout.addLayout(left)
        line1 = QtGui.QHBoxLayout()
        left.addLayout(line1)

        shape = BlofeldCombo(self, self.params.Osc_2_Shape)
        line1.addWidget(shape)
        brill = BlofeldDial(self, self.params.Osc_2_Brilliance, size=32)
        line1.addWidget(brill)
        keytrack = BlofeldDial(self, self.params.Osc_2_Keytrack, center=True, size=32, default=64)
        line1.addWidget(keytrack)

        line2 = QtGui.QHBoxLayout()
        left.addLayout(line2)

        octave = BlofeldDial(self, self.params.Osc_2_Octave, size=32)
        line2.addWidget(octave)
        semitone = BlofeldDial(self, self.params.Osc_2_Semitone, center=True, size=32, default=64)
        line2.addWidget(semitone)
        detune = BlofeldDial(self, self.params.Osc_2_Detune, center=True, size=32, default=64)
        line2.addWidget(detune)
        bend = BlofeldDial(self, self.params.Osc_2_Bend_Range, center=True, size=32, default=64)
        line2.addWidget(bend)

        right = QtGui.QGridLayout()
        layout.addLayout(right)

        right.addWidget(Section(self), 0, 0, 3, 2)
        right.addWidget(Section(self), 0, 2, 3, 1)
        pwm_label = Label(self, 'PWM')
        right.addWidget(pwm_label, 0, 0, 1, 2)
        fm_label = Label(self, 'FM')
        right.addWidget(fm_label, 0, 2, 1, 1)

        pwm_source = BlofeldCombo(self, self.params.Osc_2_PWM_Source, name='Source')
        right.addWidget(pwm_source, 1, 0, 1, 2)
        fm_source = BlofeldCombo(self, self.params.Osc_2_FM_Source, name='Source')
        right.addWidget(fm_source, 1, 2, 1, 1)
        pulsewidth = BlofeldDial(self, self.params.Osc_2_Pulsewidth, size=24, name='Width')
        right.addWidget(pulsewidth, 2, 0, 1, 1)
        pwm_amount = BlofeldDial(self, self.params.Osc_2_PWM_Amount, size=24, name='Amount')
        right.addWidget(pwm_amount, 2, 1, 1, 1)
        fm_amount = BlofeldDial(self, self.params.Osc_2_FM_Amount, size=24, name='Amount')
        right.addWidget(fm_amount, 2, 2, 1, 1)
        limit_wt = BlofeldButton(self, self.params.Osc_2_Limit_WT, checkable=True, name='Limit WT', inverted=True)
        right.addWidget(limit_wt, 1, 3, 1, 1, QtCore.Qt.AlignHCenter)
        sync = BlofeldButton(self, self.params.Osc_2_Sync_to_O3, checkable=True, name='Sync OSC3')
        right.addWidget(sync, 2, 3, 1, 1)

        return frame

    def create_osc3(self):
        frame = Frame(self, 'OSC 3')
        layout = QtGui.QHBoxLayout()
        frame.setLayout(layout)

        left = QtGui.QVBoxLayout()
        layout.addLayout(left)
        line1 = QtGui.QHBoxLayout()
        left.addLayout(line1)

        shape = BlofeldCombo(self, self.params.Osc_3_Shape)
        line1.addWidget(shape)
        brill = BlofeldDial(self, self.params.Osc_3_Brilliance, size=32)
        line1.addWidget(brill)
        keytrack = BlofeldDial(self, self.params.Osc_3_Keytrack, center=True, size=32, default=64)
        line1.addWidget(keytrack)

        line2 = QtGui.QHBoxLayout()
        left.addLayout(line2)

        octave = BlofeldDial(self, self.params.Osc_3_Octave, size=32)
        line2.addWidget(octave)
        semitone = BlofeldDial(self, self.params.Osc_3_Semitone, center=True, size=32, default=64)
        line2.addWidget(semitone)
        detune = BlofeldDial(self, self.params.Osc_3_Detune, center=True, size=32, default=64)
        line2.addWidget(detune)
        bend = BlofeldDial(self, self.params.Osc_3_Bend_Range, center=True, size=32, default=64)
        line2.addWidget(bend)

        right = QtGui.QGridLayout()
        layout.addLayout(right)

        right.addWidget(Section(self), 0, 0, 3, 2)
        right.addWidget(Section(self), 0, 2, 3, 1)
        pwm_label = Label(self, 'PWM')
        right.addWidget(pwm_label, 0, 0, 1, 2)
        fm_label = Label(self, 'FM')
        right.addWidget(fm_label, 0, 2, 1, 1)

        pwm_source = BlofeldCombo(self, self.params.Osc_3_PWM_Source, name='Source')
        right.addWidget(pwm_source, 1, 0, 1, 2)
        fm_source = BlofeldCombo(self, self.params.Osc_3_FM_Source, name='Source')
        right.addWidget(fm_source, 1, 2, 1, 1)
        pulsewidth = BlofeldDial(self, self.params.Osc_3_Pulsewidth, size=24, name='Width')
        right.addWidget(pulsewidth, 2, 0, 1, 1)
        pwm_amount = BlofeldDial(self, self.params.Osc_3_PWM_Amount, size=24, name='Amount')
        right.addWidget(pwm_amount, 2, 1, 1, 1)
        fm_amount = BlofeldDial(self, self.params.Osc_3_FM_Amount, size=24, name='Amount')
        right.addWidget(fm_amount, 2, 2, 1, 1)
        right.addWidget(HSpacer(), 0, 3)

        return frame

