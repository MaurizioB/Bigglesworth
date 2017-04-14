# *-* coding: utf-8 *-*

from collections import namedtuple
from bisect import bisect_left
from PyQt5 import QtCore, QtGui, QtWidgets

from bigglesworth.midiutils import SysExEvent
from bigglesworth.utils import load_ui

popup_values = [None, .1, .2, .3, .4, .6, .7, .8, .9, 1.1, 1.2, 1.3, 1.4, 1.5, 1.7, 1.8, 1.9, 2, 2.2, 2.3, 2.4, 2.5, 2.6, 2.8, 2.9,
                3, 3.1, 3.3, 3.4, 3.5, 3.6, 3.8, 3.9, 4, 4.1, 4.2, 4.4, 4.5, 4.6, 4.7, 4.9, 5, 5.1, 5.2, 5.3, 5.5, 5.6, 5.7, 5.8, 
                6, 6.1, 6.2, 6.3, 6.5, 6.6, 6.7, 6.8, 6.9, 7.1, 7.2, 7.3, 7.4, 7.6, 7.7, 7.8, 7.9, 8, 8.2, 8.3, 8.4, 8.5, 8.7, 8.8, 8.9, 
                9, 9.1, 9.3, 9.4, 9.5, 9.6, 9.8, 9.9, 10, 10.1, 10.3, 10.4, 10.5, 10.6, 10.7, 10.9, 11, 11.1, 11.2, 11.4, 11.5, 11.6, 11.7, 11.8, 
                12, 12.1, 12.2, 12.3, 12.5, 12.6, 12.7, 12.8, 13, 13.1, 13.2, 13.3, 13.4, 13.6, 13.7, 13.8, 13.9, 
                14.1, 14.2, 14.3, 14.4, 14.5, 14.7, 14.8, 14.9, 15, 15.2, 15.3, 15.4, 15.5]


class PopupSpin(QtWidgets.QDoubleSpinBox):
    indexChanged = QtCore.pyqtSignal(int)
    def __init__(self, parent):
        self.indexMinimum = 1
        self.indexMaximum = len(popup_values) - 1
        self.indexRange = self.indexMinimum, self.indexMaximum
        QtWidgets.QDoubleSpinBox.__init__(self, parent)
        self.setRange(.1, 15.5)
        self.setSuffix('s')
        self.setDecimals(1)
        self.setSingleStep(.1)
        self.index = 0
        self.setIndex(1)

    def stepBy(self, steps):
        new_index = self.index + steps
        if new_index > self.indexMaximum:
            new_index = self.indexMaximum
        elif new_index < self.indexMinimum:
            new_index = self.indexMinimum
        self.setIndex(new_index)

    def setIndex(self, index):
        if not self.indexMinimum <= index <= self.indexMaximum: return
        self.index = index
        self.indexChanged.emit(index)
        self.setValue(popup_values[index])

    def validate(self, text, pos):
        res = QtWidgets.QDoubleSpinBox.validate(self, text, pos)
        if res in (QtGui.QValidator.Invalid, QtGui.QValidator.Intermediate):
            return res
        new_value = QtWidgets.QDoubleSpinBox.valueFromText(self, text)
        if not popup_values[self.indexMinimum] <= new_value <= popup_values[self.indexMaximum]:
            return QtGui.QValidator.Invalid, res[1]
        return res

    def valueFromText(self, text):
        new_value = QtWidgets.QDoubleSpinBox.valueFromText(self, text)
        pos = bisect_left(popup_values, new_value)
        if pos == 1:
            self.index = pos
            self.indexChanged.emit(pos)
            return popup_values[0]
        if pos == len(popup_values):
            self.index = pos
            self.indexChanged.emit(pos)
            return popup_values[-1]
        before = popup_values[pos-1]
        after = popup_values[pos]
        if after-new_value < new_value-before:
            self.index = after
            self.indexChanged.emit(after)
            return after
        self.index = before
        self.indexChanged.emit(before)
        return before

class Globals(QtWidgets.QDialog):
    midi_event = QtCore.pyqtSignal(object)
    def __init__(self, main, parent):
        pt = namedtuple('pt', 'index delta')
        pt.__new__.__defaults__ = (0, )
        QtWidgets.QDialog.__init__(self, parent)
        load_ui(self, 'dialogs/globals.ui')
        self.setModal(True)

        self.main = main
        self.graph = main.graph
        self.input = main.input
        self.output = main.output
        self.sysex = []
        self.data = []
        self.original_data = []
        self.receiving = False
        self.general_layout = self.general_group.layout()
        self.system_layout = self.system_group.layout()
        self.midi_layout = self.midi_group.layout()
        self.layouts = self.general_layout, self.system_layout, self.midi_layout

        self.resetBtn = self.buttonBox.button(QtWidgets.QDialogButtonBox.Reset)
        self.resetBtn.setText('Reload from Blofeld')
        self.applyBtn = self.buttonBox.button(QtWidgets.QDialogButtonBox.Apply)
        self.applyBtn.clicked.connect(self.send_data)
        self.okBtn = self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok)
        self.accepted.connect(self.check_changes)
        self.main.input_conn_state_change.connect(self.conn_check)
        self.main.output_conn_state_change.connect(self.conn_check)

        self.transp_spin.valueChanged.connect(lambda value: self.transp_spin.setPrefix('+' if value >= 0 else ''))
        self.transp_spin.valueChanged.emit(self.transp_spin.value())
        self.param_dict = {
                           self.volume_spin: pt(55), 
                           self.cat_combo: pt(56), 
                           self.tune_spin: pt(40, 376), 
                           self.transp_spin: pt(41, -64), 
                           self.freeBtn_combo: pt(59), 
                           self.devId_spin: pt(37), 
                           self.autoEdit_chk: pt(35), 
                           self.contrast_spin: pt(39), 
                           self.popup_spin: pt(38), 
                           self.velocity_combo: pt(50), 
                           self.pedal_combo: pt(60), 
                           self.channel_spin: pt(36), 
                           self.clock_combo: pt(48), 
                           self.pgmSend_chk: pt(46), 
                           self.localCtrl_chk: pt(57), 
                           self.ctrlSend_combo: pt(44), 
                           self.ctrlReceive_chk: pt(45), 
                           self.ctrlW_spin: pt(51), 
                           self.ctrlX_spin: pt(52), 
                           self.ctrlY_spin: pt(53), 
                           self.ctrlZ_spin: pt(54), 
                           }
        for w in self.param_dict:
            if isinstance(w, QtWidgets.QSpinBox):
                w.valueChanged.connect(self.editData)
            elif isinstance(w, PopupSpin):
                w.indexChanged.connect(self.editData)
            elif isinstance(w, QtWidgets.QComboBox):
                w.currentIndexChanged.connect(self.editData)
            else:
                w.toggled.connect(self.editData)

    def editData(self, value):
        if self.receiving: return
        value = int(value)
        self.data[self.param_dict[self.sender()].index] = value

    def get_column_size_request(self, column):
        width = 0
        for layout in self.layouts:
            for row in range(layout.rowCount()):
                item = layout.itemAtPosition(row, column)
                if not item: continue
                width = max(item.sizeHint().width(), width)
        return width

    def showEvent(self, event):
        widget_width = max(self.get_column_size_request(1), self.get_column_size_request(4))
        label_width = max(self.get_column_size_request(0), self.get_column_size_request(3))
        for layout in self.layouts:
            layout.setColumnMinimumWidth(1, widget_width)
            layout.setColumnMinimumWidth(4, widget_width)
            layout.setColumnMinimumWidth(0, label_width)
            layout.setColumnMinimumWidth(3, label_width)
        self.conn_check()

    def conn_check(self, *args):
        input = any((True for conn in self.input.connections if not conn.hidden))
        output = any((True for conn in self.output.connections if not conn.hidden))
        self.resetBtn.setEnabled(True if all((input, output)) else False)
        self.applyBtn.setEnabled(True if output else False)
        self.okBtn.setEnabled(True if output else False)

    def setData(self, sysex):
        self.sysex = sysex
        data = sysex[5:-2]
        self.receiving = True
#        if self.data:
#            for i, v in enumerate(self.data):
#                if v != data[i]:
#                    print 'value {} changed from {} to {}'.format(i, v, data[i])
        for w, p in self.param_dict.items():
            if isinstance(w, QtWidgets.QSpinBox):
                w.setValue(data[p.index] + p.delta)
            elif isinstance(w, PopupSpin):
                w.setIndex(data[p.index])
            elif isinstance(w, QtWidgets.QComboBox):
                w.setCurrentIndex(data[p.index])
            else:
                w.setChecked(data[p.index])

        self.data = data
        self.original_data = data[:]
        self.receiving = False
        self.show()

    def check_changes(self):
        if self.data != self.original_data:
            self.send_data()

    def send_data(self):
        self.sysex[5:-2] = self.data
        self.sysex[-2] = 0x7f
        self.midi_event.emit(SysExEvent(1, self.sysex))

