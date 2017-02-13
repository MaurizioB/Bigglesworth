import pickle
from PyQt4 import QtCore, QtGui

from midiutils import *

from const import *
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



class Editor(QtGui.QMainWindow):
    object_dict = {attr:ParamObject(param_tuple) for attr, param_tuple in Params.param_names.items()}
    with open('blofeld_efx', 'rb') as _fx:
        effects = pickle.load(_fx)
    with open('blofeld_efx_ranges', 'rb') as _fx:
        efx_ranges = pickle.load(_fx)

    def __init__(self, parent):
        QtGui.QMainWindow.__init__(self, parent=None)
        load_ui(self, 'editor.ui')
        self.setContentsMargins(2, 2, 2, 2)
        pal = self.palette()
        pal.setColor(self.backgroundRole(), QtGui.QColor(20, 20, 20))
        self.setPalette(pal)

        self.main = parent
        self.alsa = self.main.alsa
        self.seq = self.main.seq
        self.params = Params
        self.send = False
        self.envelopes = []
        self.grid = self.centralWidget().layout()

        self.send_btn = SquareButton(self, 'MIDI send', checkable=True, checked=False)
        self.send_btn.toggled.connect(lambda state: setattr(self, 'send', state))
        self.grid.addWidget(self.send_btn, 0, 1)
        logo = QtGui.QIcon('logo.svg').pixmap(QtCore.QSize(160, 160)).toImage()
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
#        b = QtGui.QPushButton()
#        b.clicked.connect(self.setPreset)
#        self.grid.addWidget(b, 4, 5)

#        for r in range(self.grid.rowCount()):
#            if r == 0:
#                self.grid.setRowStretch(r, 5)
#            else:
#                self.grid.setRowStretch(r, 6)

    def __getattr__(self, attr):
        try:
            return self.object_dict[attr].value
        except:
            raise NameError('{} attribute does not exist!'.format(attr))

    def __setattr__(self, attr, value):
        try:
            try:
                self.object_dict[attr].value = value
                if self.send:
                    self.send_value(attr, value)
            except:
                QtCore.QObject.__setattr__(self, attr, value)
        except Exception as e:
            raise e
#            raise NameError('{} attribute does not exist!'.format(attr))

    def send_value(self, attr, value):
        location = 0
        par_id = Params.index_from_attr(attr)
        par_high, par_low = divmod(par_id, 128)
        
        req = SysExEvent(1, [0xF0, 0x3e, 0x13, 0x00, 0x20, location, par_high, par_low, value, 0xf7])
        req.source = self.alsa.output.client.id, self.alsa.output.id
        self.seq.output_event(req.get_event())
        self.seq.drain_output()

    def setData(self, data):
        old_send = self.send
        self.send = False
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
        self.send = old_send

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
        def set_effects(id):
            if id == 0:
                self.effects_1_layout.currentWidget().setEnabled(False)
                return
            self.effects_1_layout.setCurrentIndex(id-1)
            self.effects_1_layout.currentWidget().setEnabled(True)
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
        efx_type.indexChanged.connect(set_effects)
        line1.addWidget(efx_type)
        efx_mix = BlofeldDial(self, self.params.Effect_1_Mix, size=24)
        line1.addWidget(efx_mix)

        self.effects_1_layout = QtGui.QStackedLayout()
        layout.addLayout(self.effects_1_layout)

        for efx in sorted(self.effects[0]):
            efx_layout = create_effects(self.effects[0][efx])
            self.effects_1_layout.addWidget(efx_layout)

        set_effects(0)

        return frame

    def create_effect_2(self):
        short_names = {
                       'Lowpass': 'LP', 
                       'Highpass': 'HP', 
                       'Diffusion': 'Diff.', 
                       'Damping': 'Damp', 
                       }
        def set_effects(id):
            if id == 0:
                self.effects_2_layout.currentWidget().setEnabled(False)
                return
            self.effects_2_layout.setCurrentIndex(id-1)
            self.effects_2_layout.currentWidget().setEnabled(True)
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
        efx_type.indexChanged.connect(set_effects)
        line1.addWidget(efx_type)
        efx_mix = BlofeldDial(self, self.params.Effect_2_Mix, size=24)
        line1.addWidget(efx_mix)

        self.effects_2_layout = QtGui.QStackedLayout()
        layout.addLayout(self.effects_2_layout)

        for efx in sorted(self.effects[1]):
            efx_layout = create_effects(self.effects[1][efx])
            self.effects_2_layout.addWidget(efx_layout)

        set_effects(0)

        return frame

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
        layout = QtGui.QVBoxLayout()
        frame.setLayout(layout)

        grid = QtGui.QGridLayout()
        layout.addLayout(grid)
        grid.addWidget(BlofeldSlider(self, self.params.Mixer_Osc_1_Level, name='OSC 1'), 0, 0, 2, 1)
        grid.addWidget(BlofeldDial(self, self.params.Mixer_Osc_1_Balance, size=24, center=True, default=64, name='Bal'), 2, 0, 1, 1)
        grid.addWidget(BlofeldSlider(self, self.params.Mixer_Osc_2_Level, name='OSC 2'), 0, 1, 2, 1)
        grid.addWidget(BlofeldDial(self, self.params.Mixer_Osc_2_Balance, size=24, center=True, default=64, name='Bal'), 2, 1, 1, 1)
        grid.addWidget(BlofeldSlider(self, self.params.Mixer_Osc_3_Level, name='OSC 3'), 0, 2, 2, 1)
        grid.addWidget(BlofeldDial(self, self.params.Mixer_Osc_3_Balance, size=24, center=True, default=64, name='Bal'), 2, 2, 1, 1)
        grid.addWidget(BlofeldSlider(self, self.params.Mixer_RingMod_Level, name='RingMod'), 0, 3, 2, 1)
        grid.addWidget(BlofeldDial(self, self.params.Mixer_RingMod_Balance, size=24, center=True, default=64, name='Bal'), 2, 3, 1, 1)
        grid.addWidget(BlofeldDial(self, self.params.Mixer_Noise_Colour, size=24, center=True, default=64), 0, 4, 1, 1)
        grid.addWidget(BlofeldSlider(self, self.params.Mixer_Noise_Level, name='Noise'), 1, 4, 1, 1)
        grid.addWidget(BlofeldDial(self, self.params.Mixer_Noise_Balance, size=24, center=True, default=64, name='Bal'), 2, 4, 1, 1)
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
        limit_wt = BlofeldButton(self, self.params.Osc_1_Limit_WT, checkable=True, name='Limit WT')
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
        limit_wt = BlofeldButton(self, self.params.Osc_2_Limit_WT, checkable=True, name='Limit WT')
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

