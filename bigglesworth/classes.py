from string import uppercase, ascii_letters
from collections import namedtuple
from bisect import bisect_left

from PyQt4 import QtCore, QtGui

import midifile

from midiutils import SysExEvent
from const import *
from utils import load_ui, setBold

class SoundDumpDialog(QtGui.QDialog):
    def __init__(self, main, parent):
        QtGui.QDialog.__init__(self, parent)
        self.main = main
        load_ui(self, 'dumpdialog.ui')
        self.bank_combo.currentIndexChanged.connect(self.update_label)
        self.prog_spin.valueChanged.connect(self.update_label)
        self.store_chk.toggled.connect(self.check)
        self.editor_chk.toggled.connect(self.check)

    def check(self, *args):
        self.buttonBox.button(QtGui.QDialogButtonBox.Ok).setEnabled(True if any((self.store_chk.isChecked(), self.editor_chk.isChecked())) else False)

    def update_label(self, *args):
        self.library_sound_lbl.setText(self.main.blofeld_library.sound(self.bank_combo.currentIndex(), self.prog_spin.value()-1).name)

    def exec_(self, name):
        self.editor_chk.setChecked(True)
        self.store_chk.setChecked(False)
        self.bank_combo.addItems([uppercase[b] for b in range(self.main.blofeld_library.banks)])
        self.dump_sound_lbl.setText(name)
        if not None in self.main.blofeld_current:
            bank, prog = self.main.blofeld_current
            self.bank_combo.setCurrentIndex(bank)
            self.prog_spin.setValue(prog+1)
        res = QtGui.QDialog.exec_(self)
        if not res: return False
        if res == QtGui.QDialogButtonBox.Ignore:
            return False
        return self.editor_chk.isChecked(), (self.bank_combo.currentIndex(), self.prog_spin.value()-1) if self.store_chk.isChecked() else False

class MidiWidget(QtGui.QWidget):
    def __init__(self, main):
        QtGui.QDialog.__init__(self, parent=None)
        self.main = main

        layout = QtGui.QGridLayout()
        self.setLayout(layout)
        self.input_lbl = QtGui.QLabel('INPUT')
        layout.addWidget(self.input_lbl, 0, 0, QtCore.Qt.AlignHCenter)
        self.input_listview = QtGui.QListView(self)
        self.input_listview.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.input_listview.setEditTriggers(QtGui.QListView.NoEditTriggers)
        layout.addWidget(self.input_listview, 1, 0)
        line = QtGui.QFrame()
        line.setFrameShape(QtGui.QFrame.VLine)
        layout.addWidget(line, 0, 1, 2, 1)
        self.output_lbl = QtGui.QLabel('OUTPUT')
        layout.addWidget(self.output_lbl, 0, 2, QtCore.Qt.AlignHCenter)
        self.output_listview = QtGui.QListView(self)
        self.output_listview.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.output_listview.setEditTriggers(QtGui.QListView.NoEditTriggers)
        layout.addWidget(self.output_listview, 1, 2)
        self.refresh_btn = QtGui.QPushButton('Refresh')
        layout.addWidget(self.refresh_btn, 2, 0, 1, 3)

        self.graph = self.main.graph
        self.input = self.main.input
        self.output = self.main.output
        self.graph.graph_changed.connect(self.refresh_all)
        self.refresh_all()
        self.refresh_btn.clicked.connect(self.refresh_all)

        self.input_listview.doubleClicked.connect(self.port_connect_toggle)
        self.output_listview.doubleClicked.connect(self.port_connect_toggle)
        self.input_listview.customContextMenuRequested.connect(self.port_menu)
        self.output_listview.customContextMenuRequested.connect(self.port_menu)

    def _get_port_from_item_data(self, model, index):
        return self.graph.port_id_dict[model.data(index, ClientRole).toInt()[0]][model.data(index, PortRole).toInt()[0]]

    def showEvent(self, event):
        if self.input_model.rowCount():
            self.input_listview.setMinimumHeight(self.input_listview.sizeHintForRow(0)*12)
        elif self.input_model.rowCount():
            self.output_listview.setMinimumHeight(self.output_listview.sizeHintForRow(0)*12)
        self.setMinimumWidth(400)

    def port_menu(self, pos):
        sender = self.sender()
        model = sender.model()
        index = sender.indexAt(pos)
        item = model.item(index.row())
        actions = []
        if item.isEnabled():
            port = self._get_port_from_item_data(model, index)
            if (sender == self.input_listview and self.input in [conn.dest for conn in port.connections.output]) or\
                (sender == self.output_listview and self.output in [conn.src for conn in port.connections.input]):
                disconnect_action = QtGui.QAction('Disconnect', self)
                disconnect_action.triggered.connect(lambda: self.port_connect_toggle(index, sender))
                actions.append(disconnect_action)
            else:
                connect_action = QtGui.QAction('Connect', self)
                connect_action.triggered.connect(lambda: self.port_connect_toggle(index, sender))
                actions.append(connect_action)
            sep = QtGui.QAction(self)
            sep.setSeparator(True)
            actions.append(sep)
        disconnect_all_action = QtGui.QAction('Disconnect all', self)
        actions.append(disconnect_all_action)
        if sender == self.input_listview:
            disconnect_all_action.triggered.connect(lambda: self.input.disconnect_all())
        elif sender == self.output_listview:
            disconnect_all_action.triggered.connect(lambda: self.output.disconnect_all())

        menu = QtGui.QMenu()
        menu.addActions(actions)
        menu.exec_(sender.mapToGlobal(pos))

    def port_connect_toggle(self, index, sender=None):
        if sender is None:
            sender = self.sender()
        if sender == self.input_listview:
            port = self._get_port_from_item_data(self.input_model, index)
            if self.input in [conn.dest for conn in port.connections.output]:
                port.disconnect(self.input)
            else:
                port.connect(self.input)
        elif sender == self.output_listview:
            port = self._get_port_from_item_data(self.output_model, index)
            if self.output in [conn.src for conn in port.connections.input]:
                self.output.disconnect(port)
            else:
                self.output.connect(port)

    def refresh_all(self):
        self.input_model = QtGui.QStandardItemModel()
        self.input_listview.setModel(self.input_model)
        self.output_model = QtGui.QStandardItemModel()
        self.output_listview.setModel(self.output_model)
        for client in [self.graph.client_id_dict[cid] for cid in sorted(self.graph.client_id_dict.keys())]:
            in_port_list = []
            out_port_list = []
            for port in client.ports:
                if port.hidden or port.client == self.main.input.client:
                    continue
                if port.is_output:
                    in_port_list.append(port)
                if port.is_input:
                    out_port_list.append(port)
            if len(in_port_list):
                in_client_item = QtGui.QStandardItem(client.name)
                in_client_item.setData('<b>Client:</b> {c}<br/><b>Address:</b> {cid}'.format(c=client.name, cid=client.id), QtCore.Qt.ToolTipRole)
                self.input_model.appendRow(in_client_item)
                in_client_item.setEnabled(False)
                for port in in_port_list:
                    in_item = QtGui.QStandardItem('  {}'.format(port.name))
                    in_item.setData('<b>Client:</b> {c}<br/><b>Port:</b> {p}<br/><b>Address:</b> {cid}:{pid}'.format(
                                                                                                               c=client.name, 
                                                                                                               p=port.name, 
                                                                                                               cid=client.id, 
                                                                                                               pid=port.id), 
                                                                                                               QtCore.Qt.ToolTipRole)
                    in_item.setData(QtCore.QVariant(client.id), ClientRole)
                    in_item.setData(QtCore.QVariant(port.id), PortRole)
                    self.input_model.appendRow(in_item)
                    if any([conn for conn in port.connections.output if conn.dest == self.input]):
                        in_item.setData(QtGui.QBrush(QtCore.Qt.blue), QtCore.Qt.ForegroundRole)
                        setBold(in_item)
                    else:
                        in_item.setData(QtGui.QBrush(QtCore.Qt.black), QtCore.Qt.ForegroundRole)
                        setBold(in_item, False)
            if len(out_port_list):
                out_client_item = QtGui.QStandardItem(client.name)
                out_client_item.setData('<b>Client:</b> {c}<br/><b>Address:</b> {cid}'.format(c=client.name, cid=client.id), QtCore.Qt.ToolTipRole)
                self.output_model.appendRow(out_client_item)
                out_client_item.setEnabled(False)
                for port in out_port_list:
                    out_item = QtGui.QStandardItem('  {}'.format(port.name))
                    out_item.setData('<b>Client:</b> {c}<br/><b>Port:</b> {p}<br/><b>Address:</b> {cid}:{pid}'.format(
                                                                                                               c=client.name, 
                                                                                                               p=port.name, 
                                                                                                               cid=client.id, 
                                                                                                               pid=port.id), 
                                                                                                               QtCore.Qt.ToolTipRole)
                    out_item.setData(QtCore.QVariant(client.id), ClientRole)
                    out_item.setData(QtCore.QVariant(port.id), PortRole)
                    self.output_model.appendRow(out_item)
                    if any([conn for conn in port.connections.input if conn.src == self.output]):
                        out_item.setData(QtGui.QBrush(QtCore.Qt.blue), QtCore.Qt.ForegroundRole)
                        setBold(out_item)
                    else:
                        out_item.setData(QtGui.QBrush(QtCore.Qt.black), QtCore.Qt.ForegroundRole)
                        setBold(out_item, False)

        cx_text = [
                   (self.input.connections.input, self.input_lbl, 'INPUT'), 
                   (self.output.connections.output, self.output_lbl, 'OUTPUT'), 
                   ]
        for cx, lbl, ptxt in cx_text:
            n_conn = len([conn for conn in cx if not conn.hidden])
            cx_txt = ptxt
            if not n_conn:
                cx_txt += ' (not connected)'
            elif n_conn == 1:
                cx_txt += ' (1 connection)'
            else:
                cx_txt += ' ({} connections)'.format(n_conn)
            lbl.setText(cx_txt)

class MidiDialog(QtGui.QDialog):
    def __init__(self, main, parent):
        QtGui.QDialog.__init__(self, parent)
        self.main = main
        self.setModal(True)
        layout = QtGui.QVBoxLayout()
        self.setLayout(layout)

    def show(self):
        self.layout().addWidget(self.main.midiwidget)
        QtGui.QDialog.show(self)

class SettingsDialog(QtGui.QDialog):
    def __init__(self, main, parent):
        QtGui.QDialog.__init__(self, parent)
        load_ui(self, 'settings.ui')
        self.main = main
        self.settings = main.settings
        self.setModal(True)

        self.previous = 0
        self.connections = {INPUT: None, OUTPUT: None}
        self.deviceID_spin.valueChanged.connect(lambda value: self.deviceID_hex_lbl.setText('({:02X}h)'.format(value)))
        self.deviceID_spin.valueChanged.connect(self.check_broadcast)
        self.broadcast_chk.toggled.connect(self.set_broadcast)
        self.deviceID_detect_btn.clicked.connect(self.detect)
        self.detect_msgbox = QtGui.QMessageBox(QtGui.QMessageBox.Information, 'Detecting Device ID', 'Waiting for the Blofeld to reply, please wait...', QtGui.QMessageBox.Abort, self)

        self.detect_timer = QtCore.QTimer()
        self.detect_timer.setInterval(5000)
        self.detect_timer.setSingleShot(True)
        self.detect_timer.timeout.connect(self.no_response)

        self.no_response_msgbox = QtGui.QMessageBox(QtGui.QMessageBox.Warning, 'No response', 'We got no response from the Blofeld.\nPlease check MIDI connections or try to switch it off and on again.', QtGui.QMessageBox.Ok, self)

    def detect(self):
        self.main.midi_lock.emit(True)
        self.main.globals_event.connect(self.detect_response)
        self.main.globals_request()
        self.detect_timer.start()
        self.detect_msgbox.exec_()
        self.detect_timer.stop()
        self.main.midi_lock.emit(False)
        self.main.globals_event.disconnect(self.detect_response)

    def detect_response(self, data):
        self.detect_timer.stop()
        self.detect_msgbox.accept()
        self.no_response_msgbox.accept()
        id = data[42]
        self.previous = id
        if id == 127:
            self.broadcast_chk.setChecked(True)
            self.broadcast_chk.toggled.emit(True)
        else:
            self.deviceID_spin.setValue(id)

    def no_response(self):
        self.detect_msgbox.reject()
        self.no_response_msgbox.exec_()

    def detect_connections(self, dir, conn):
        self.connections[dir] = conn
        if self.connections[INPUT] and self.connections[OUTPUT]:
            self.deviceID_detect_btn.setEnabled(True)
        else:
            self.deviceID_detect_btn.setEnabled(False)

    def set_broadcast(self, state):
        if state:
            self.previous = self.deviceID_spin.value()
            self.deviceID_spin.blockSignals(True)
            self.deviceID_spin.setValue(127)
            self.deviceID_hex_lbl.setText('({:02X}h)'.format(127))
            self.deviceID_spin.blockSignals(False)
        else:
            self.deviceID_spin.setValue(self.previous)

    def check_broadcast(self, value):
        if value == 127:
            self.broadcast_chk.blockSignals(True)
            self.broadcast_chk.setChecked(True)
            self.broadcast_chk.setEnabled(False)
            self.broadcast_chk.blockSignals(False)
        else:
            self.broadcast_chk.setChecked(False)
            self.broadcast_chk.setEnabled(True)

    def exec_(self):
        self.library_doubleclick_combo.setCurrentIndex(self.main.library_doubleclick)

        self.editor_pgm_send_combo.setCurrentIndex(self.main.editor_remember_states[PGMSEND])
        self.editor_midi_send_combo.setCurrentIndex(self.main.editor_remember_states[MIDISEND])
        self.editor_remember_chk.setChecked(self.main.editor_remember)

        self.midi_groupbox.layout().addWidget(self.main.midiwidget)

        id = self.main.blofeld_id
        if id == 127:
            self.broadcast_chk.setChecked(True)
            self.broadcast_chk.toggled.emit(True)
        else:
            self.previous = id
            self.deviceID_spin.setValue(id)
            self.broadcast_chk.setChecked(False)
            self.broadcast_chk.toggled.emit(False)

        self.blofeld_autoconnect_chk.setChecked(self.main.blofeld_autoconnect)
        self.remember_connections_chk.setChecked(self.main.remember_connections)
        res = QtGui.QDialog.exec_(self)
        if not res: return

        self.main.library_doubleclick = self.library_doubleclick_combo.currentIndex()

        self.main.editor_remember = self.editor_remember_chk.isChecked()
        if self.editor_remember_chk.isChecked():
            self.main.editor_remember_states = [
                                                self.main.editor.pgm_receive_btn.isChecked(), 
                                                self.main.editor.midi_receive_btn.isChecked(), 
                                                self.main.editor.pgm_send_btn.isChecked(), 
                                                self.main.editor.midi_send_btn.isChecked(), 
                                                ]
        else:
            self.main.editor_remember_states = [
                                                bool(self.editor_pgm_receive_combo.currentIndex()), 
                                                bool(self.editor_midi_receive_combo.currentIndex()), 
                                                bool(self.editor_pgm_send_combo.currentIndex()), 
                                                bool(self.editor_midi_send_combo.currentIndex()), 
                                                ]

        self.main.blofeld_id = self.deviceID_spin.value()
        self.main.blofeld_autoconnect = self.blofeld_autoconnect_chk.isChecked()
        self.main.remember_connections = self.remember_connections_chk.isChecked()


class DirCursorClass(QtGui.QCursor):
    limit_pen = QtGui.QPen(QtCore.Qt.black, 2)
    limit_pen.setCapStyle(QtCore.Qt.RoundCap)
    arrow_pen = QtGui.QPen(QtCore.Qt.black, 1)
    arrow_pen.setCapStyle(QtCore.Qt.RoundCap)
    brush = QtGui.QBrush(QtCore.Qt.black)

class UpCursorClass(DirCursorClass):
    def __init__(self):
        pixmap = QtGui.QPixmap(32, 32)
        pixmap.fill(QtCore.Qt.transparent)
        qp = QtGui.QPainter(pixmap)
        qp.setRenderHints(QtGui.QPainter.Antialiasing)
        qp.translate(.5, .5)
        qp.setPen(self.limit_pen)
        qp.drawLine(0, 1, 15, 1)
        qp.setPen(self.arrow_pen)
        qp.setBrush(self.brush)
        path = QtGui.QPainterPath()
        path.moveTo(7.5, 1)
        path.lineTo(12, 8)
        path.lineTo(3, 8)
        path.closeSubpath()
        qp.drawPath(path)
        del qp
        DirCursorClass.__init__(self, pixmap, 8, 1)

class DownCursorClass(DirCursorClass):
    def __init__(self):
        pixmap = QtGui.QPixmap(32, 32)
        pixmap.fill(QtCore.Qt.transparent)
        qp = QtGui.QPainter(pixmap)
        qp.setRenderHints(QtGui.QPainter.Antialiasing)
        qp.translate(.5, .5)
        qp.setPen(self.limit_pen)
        qp.drawLine(0, 8, 15, 8)
        qp.setPen(self.arrow_pen)
        qp.setBrush(self.brush)
        path = QtGui.QPainterPath()
        path.moveTo(3, 1)
        path.lineTo(12, 1)
        path.lineTo(7.5, 7)
        path.closeSubpath()
        qp.drawPath(path)
        del qp
        DirCursorClass.__init__(self, pixmap, 8, 8)

class LeftCursorClass(DirCursorClass):
    def __init__(self):
        pixmap = QtGui.QPixmap(32, 32)
        pixmap.fill(QtCore.Qt.transparent)
        qp = QtGui.QPainter(pixmap)
        qp.setRenderHints(QtGui.QPainter.Antialiasing)
        qp.translate(.5, .5)
        qp.setPen(self.limit_pen)
        qp.drawLine(1, 0, 1, 15)
        qp.setPen(self.arrow_pen)
        qp.setBrush(self.brush)
        path = QtGui.QPainterPath()
        path.moveTo(1, 7.5)
        path.lineTo(8, 12)
        path.lineTo(8, 3)
        path.closeSubpath()
        qp.drawPath(path)
        del qp
        DirCursorClass.__init__(self, pixmap, 1, 8)

class RightCursorClass(DirCursorClass):
    def __init__(self):
        pixmap = QtGui.QPixmap(32, 32)
        pixmap.fill(QtCore.Qt.transparent)
        qp = QtGui.QPainter(pixmap)
        qp.setRenderHints(QtGui.QPainter.Antialiasing)
        qp.translate(.5, .5)
        qp.setPen(self.limit_pen)
        qp.drawLine(8, 0, 8, 15)
        qp.setPen(self.arrow_pen)
        qp.setBrush(self.brush)
        path = QtGui.QPainterPath()
        path.moveTo(1, 3)
        path.lineTo(1, 12)
        path.lineTo(7, 7.5)
        path.closeSubpath()
        qp.drawPath(path)
        del qp
        DirCursorClass.__init__(self, pixmap, 8, 8)

class Sound(QtCore.QObject):
    bankChanged = QtCore.pyqtSignal(int)
    progChanged = QtCore.pyqtSignal(int)
    indexChanged = QtCore.pyqtSignal(int)
    nameChanged = QtCore.pyqtSignal(str)
    catChanged = QtCore.pyqtSignal(int)
    edited = QtCore.pyqtSignal(int)
    def __init__(self, data=None, source=SRC_LIBRARY):
        QtCore.QObject.__init__(self)
        if data is not None:
            self._bank = data[0]
            self._prog = data[1]
            self._data = data[2:]
            self._name = ''.join([str(unichr(l)) for l in self.data[363:379]])
            self._cat = self.data[379]
            self.source = source
            self._state = STORED|(source<<1)
        else:
            self._bank = self._prog = 0
            self._data = []
            self._name = 'None'
            self._cat = None
            self.source = SRC_LIBRARY
            self._state = EMPTY

        self._done = True

    def __getattr__(self, attr):
        try:
#            print sound_params[VALUE][self.data[params_index[attr]]]
#            print attr
            index = Params.index_from_attr(attr)
#            print self.data[index]
#            print sound_params[208][VALUE][self.data[index]]
#            return sound_params[index][VALUE][self.data[index]][0]
            return [self.data[index]][0]
        except Exception as Err:
            print Err
            print 'attr exception: {}'.format(attr)
            print '{}:{}, {}'.format(uppercase[self.bank], self.prog, self.name)
            return None

    def __setattr__(self, attr, value):
        if '_done' in self.__dict__.keys() and attr not in self.__dict__.keys():
            try:
                index = Params.index_from_attr(attr)
                self._data[index] = value
                self._state = self._state|EDITED
                self.edited.emit(self._state)
            except Exception as Err:
                print Err
        else:
            super(QtCore.QObject, self).__setattr__(attr, value)

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, state):
#        print 'old state: {}\nnew state: {}'.format(self.state, state)
        self._state = self._state|state
        self.edited.emit(self._state)

    @property
    def bank(self):
        return self._bank

    @bank.setter
    def bank(self, bank):
        self._bank = bank
        self.bankChanged.emit(bank)
        self.indexChanged.emit(self.index)
        self.state = MOVED

    @property
    def prog(self):
        return self._prog

    @prog.setter
    def prog(self, prog):
        self._prog = prog
        self.progChanged.emit(prog)
        self.indexChanged.emit(self.index)
        self.state = MOVED

    @property
    def index(self):
        return self.prog + self.bank*128

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        while len(name) < 16:
            name += ' '
        if len(name) > 16:
            name = name[:16]
        self._name = name
        self.data[363:379] = [ord(l) for l in name]
        self.nameChanged.emit(name)
        self.state = EDITED
        print 'changed name'

    @property
    def cat(self):
        return self._cat

    @cat.setter
    def cat(self, cat):
        self._cat = cat
        self.catChanged.emit(cat)
        self.state = EDITED

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, data):
        self._data = data


class CategoryDelegate(QtGui.QStyledItemDelegate):
    def __init__(self, parent=None):
        QtGui.QStyledItemDelegate.__init__(self, parent)
        self.commitData.connect(self.set_data)

    def createEditor(self, parent, option, index):
        self.table = parent.parent()
        self.index = index
        combo = QtGui.QComboBox(parent)
        model = QtGui.QStandardItemModel()
        [model.appendRow(QtGui.QStandardItem(cat)) for cat in categories]
        combo.setModel(model)
        combo.setCurrentIndex(index.data(CatRole).toPyObject())
        combo.activated.connect(lambda i: parent.setFocus())
        return combo

    def set_data(self, widget):
        self.index.model().sourceModel().sound(self.index).cat = widget.currentIndex()

class PauseIcon(QtGui.QIcon):
    def __init__(self):
        icon = QtGui.QPixmap(12, 12)
        icon.fill(QtCore.Qt.transparent)
        qp = QtGui.QPainter(icon)
        qp.setRenderHints(QtGui.QPainter.Antialiasing)
        qp.setPen(QtCore.Qt.lightGray)
        qp.setBrush(QtCore.Qt.darkGray)
        qp.translate(.5, .5)
        qp.drawRect(0, 0, 4, 11)
        qp.drawRect(7, 0, 4, 11)
        del qp
        QtGui.QIcon.__init__(self, icon)

class ResumeIcon(QtGui.QIcon):
    def __init__(self):
        icon = QtGui.QPixmap(12, 12)
        icon.fill(QtCore.Qt.transparent)
        qp = QtGui.QPainter(icon)
        qp.setRenderHints(QtGui.QPainter.Antialiasing)
        qp.setPen(QtCore.Qt.lightGray)
        qp.setBrush(QtCore.Qt.darkGray)
        qp.translate(.5, .5)
        qp.drawPolygon(QtCore.QPointF(0, 0), QtCore.QPointF(11, 5.5), QtCore.QPointF(0, 11))
        del qp
        QtGui.QIcon.__init__(self, icon)

class DumpWin(QtGui.QDialog):
    pause = QtCore.pyqtSignal()
    resume = QtCore.pyqtSignal()
    def __init__(self, parent=None):
        QtGui.QDialog.__init__(self, parent)
        self.setModal(True)
        self.setMinimumWidth(150)
        self.setWindowTitle('Sound dump request')
        grid = QtGui.QGridLayout(self)
        grid.addWidget(QtGui.QLabel('Dumping sounds...'), 0, 0, 1, 2)
        grid.addWidget(QtGui.QLabel('Bank: '), 1, 0, 1, 1)
        self.bank_lbl = QtGui.QLabel()
        grid.addWidget(self.bank_lbl, 1, 1, 1, 1)
        grid.addWidget(QtGui.QLabel('Sound: '), 2, 0, 1, 1)
        self.sound_lbl = QtGui.QLabel()
        grid.addWidget(self.sound_lbl, 2, 1, 1, 1)
        grid.addWidget(QtGui.QLabel('Remaining: '), 3, 0, 1, 1)
        self.time = QtGui.QLabel()
        grid.addWidget(self.time, 3, 1, 1, 1)
        self.progress = QtGui.QProgressBar()
        self.progress.setMaximum(128)
        grid.addWidget(self.progress, 4, 0, 1, 2)

        button_box = QtGui.QHBoxLayout()
        grid.addLayout(button_box, 5, 0, 1, 2)

        self.toggle_btn = QtGui.QPushButton('Pause', self)
        self.pause_icon = PauseIcon()
        self.resume_icon = ResumeIcon()
        self.toggle_btn.setIcon(self.pause_icon)
        self.toggle_btn.clicked.connect(self.toggle)
        button_box.addWidget(self.toggle_btn)

        stop = QtGui.QPushButton('Stop', self)
        stop.setIcon(self.style().standardIcon(QtGui.QStyle.SP_DialogCloseButton))
        stop.clicked.connect(self.accept)
        button_box.addWidget(stop)

        cancel = QtGui.QPushButton('Cancel', self)
        cancel.setIcon(self.style().standardIcon(QtGui.QStyle.SP_DialogCancelButton))
        cancel.setSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Preferred)
        cancel.clicked.connect(self.reject)
        button_box.addWidget(cancel)

        self.paused = False

    def toggle(self):
        if self.paused:
            self.paused = False
            self.resume.emit()
            self.toggle_btn.setIcon(self.pause_icon)
            self.toggle_btn.setText('Pause')
        else:
            self.paused = True
            self.pause.emit()
            self.toggle_btn.setIcon(self.resume_icon)
            self.toggle_btn.setText('Resume')

    def reject(self):
        self.pause.emit()
        res = QtGui.QMessageBox.question(self, 'Cancel dumping?', 'Do you want to cancel the current dumping process?', QtGui.QMessageBox.Yes|QtGui.QMessageBox.No)
        if res == QtGui.QMessageBox.Yes:
            QtGui.QMessageBox.reject(self)
        elif not self.paused:
            self.resume.emit()

    def show(self):
        self.bank_lbl.setText('')
        self.sound_lbl.setText('')
        self.time.setText('?')
        self.progress.setValue(0)
        QtGui.QDialog.show(self)

class SortedLibrary(object):
    def __init__(self, library):
        self.by_bank = library.data
        self.by_cat = {i:[] for i in range(len(categories))}
        self.by_alpha = {l:[] for l in ['0..9']+list(uppercase)}

    def reload(self):
        by_cat = {i:[] for i in range(len(categories))}
        by_alpha = {l:[] for l in ['0..9']+list(uppercase)}
        for b, progs in enumerate(self.by_bank):
            for p in progs:
                if p is None: continue
                if p.name[0] in ascii_letters:
                    by_alpha[p.name[0].upper()].append(p)
                else:
                    by_alpha['0..9'].append(p)
                by_cat[p.cat].append(p)
        self.by_cat = by_cat
        self.by_alpha = {}
        for letter, sound_list in by_alpha.items():
            self.by_alpha[letter] = sorted(sound_list, key=lambda s: s.name.lower())


class Library(QtCore.QObject):
    def __init__(self, model, parent=None, banks=26):
        QtCore.QObject.__init__(self, parent)
#        self.data = [[Sound(b, p) for p in range(128)] for b in range(banks)]
        self.model = model
        self.banks = banks
        self.model.cleared.connect(self.clear)
        self.clear()
        self.sorted = SortedLibrary(self)
        self.menu = None
#        self.create_menu()

    def clear(self):
        self.data = [[None for p in range(128)] for b in range(self.banks)]
        self.sound_index = {}
        self.cat_count = [{c:0 for c in categories} for b in range(self.banks)]

    def sound(self, bank, prog):
        return self.data[bank][prog]

    def _addSound(self, sound):
        bank = sound.bank
        prog = sound.prog
        self.data[bank][prog] = sound
        self.sound_index[sound] = bank, prog

        index_item = QtGui.QStandardItem('{}{:03}'.format(uppercase[bank], prog+1))
        index_item.setData(bank*128+prog, IndexRole)
        index_item.setEditable(False)
        bank_item = QtGui.QStandardItem(uppercase[bank])
        bank_item.setData(bank, UserRole)
        bank_item.setData(bank, BankRole)
        bank_item.setTextAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignCenter)
        bank_item.setEditable(False)
        prog_item = QtGui.QStandardItem('{:03}'.format(prog+1))
        prog_item.setData(prog, UserRole)
        prog_item.setData(prog, ProgRole)
        prog_item.setEditable(False)
        name_item = QtGui.QStandardItem(sound.name)
        name_item.setData(sound.Osc_1_Shape, QtCore.Qt.ToolTipRole)
#        name_item.setData(sound.name, QtCore.Qt.ToolTipRole)
        cat_item = QtGui.QStandardItem(categories[sound.cat])
        cat_item.setData(sound.cat, UserRole)
        cat_item.setData(sound.cat, CatRole)
#        status_item = QtGui.QStandardItem('Dumped' if sound.state == DUMPED else 'Stored')
        status_item = QtGui.QStandardItem(status_dict[sound.state])
        status_item.setData(sound.state, EditedRole)
        status_item.setEditable(False)
        sound_item = QtGui.QStandardItem()
        sound_item.setData(sound, SoundRole)
#        sound.bankChanged.connect(lambda bank, item=bank_item: item.setData(bank, BankRole))
#        sound.progChanged.connect(lambda prog, item=prog_item: item.setData(prog, ProgRole))
        sound.indexChanged.connect(lambda index, item=index_item: item.setData(index, IndexRole))
        sound.catChanged.connect(lambda cat, bank=bank, item=cat_item: self.soundSetCategory(item, bank, cat))
        sound.edited.connect(lambda state, item=status_item: item.setData(state, EditedRole))

        found = self.model.findItems('{}{:03}'.format(uppercase[bank], prog+1), QtCore.Qt.MatchFixedString, 0)
        if found:
            self.model.takeRow(found[0].row())

        self.model.appendRow([index_item, bank_item, prog_item, name_item, cat_item, status_item, sound_item])

    def addSound(self, sound):
        self._addSound(sound)
        self.sort()
        self.create_menu()

    def addSoundBulk(self, sound_list):
        for sound in sound_list:
            self._addSound(sound)
        self.sort()
        if self.menu:
            self.create_menu()

    def sort(self):
        delete_list = []
        for i, bank in enumerate(self.data):
            if not any(bank):
                delete_list.append(i)
        for empty in reversed(delete_list):
            self.data.pop(empty)
        self.banks = len(self.data)
        self.model.sort(2)
        self.model.sort(1)
        self.sorted.reload()

    def create_menu(self):
        del self.menu
        menu = QtGui.QMenu()
        by_bank = QtGui.QMenu('By bank', menu)
        menu.addMenu(by_bank)
        for id, bank in enumerate(self.sorted.by_bank):
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
            for sound in self.sorted.by_cat[cid]:
                cat_len += 1
                item = QtGui.QAction(sound.name, cat_menu)
                item.setData((sound.bank, sound.prog))
                cat_menu.addAction(item)
            if not len(cat_menu.actions()):
                cat_menu.setEnabled(False)
            cat_menu.setTitle('{} ({})'.format(cat, cat_len))
        by_alpha = QtGui.QMenu('Alphabetical', menu)
        menu.addMenu(by_alpha)
        for alpha in sorted(self.sorted.by_alpha.keys()):
            alpha_menu = QtGui.QMenu(by_alpha)
            by_alpha.addMenu(alpha_menu)
            alpha_len = 0
            for sound in self.sorted.by_alpha[alpha]:
                alpha_len += 1
                item = QtGui.QAction(sound.name, alpha_menu)
                item.setData((sound.bank, sound.prog))
                alpha_menu.addAction(item)
            if not len(alpha_menu.actions()):
                alpha_menu.setEnabled(False)
            alpha_menu.setTitle('{} ({})'.format(alpha, alpha_len))
        self.menu = menu

    def soundSetCategory(self, cat_item, bank, cat):
        cat_item.setData(cat, CatRole)

    def __getitem__(self, req):
        if not isinstance(req, tuple):
            req = divmod(req, 128)
        return self.data[req[0]][req[1]]


class LibraryModel(QtGui.QStandardItemModel):
    cleared = QtCore.pyqtSignal()
    def __init__(self, parent=None):
        QtGui.QStandardItemModel.__init__(self, 0, 7, parent)
        self.setHorizontalHeaderLabels(sound_headers)

    def clear(self):
        QtGui.QStandardItemModel.clear(self)
        self.setHorizontalHeaderLabels(sound_headers)
        self.cleared.emit()

    def sound(self, index):
        return self.item(index.row(), 6).data(SoundRole).toPyObject()

class LibraryProxy(QtGui.QSortFilterProxyModel):
    def __init__(self, parent=None):
        QtGui.QSortFilterProxyModel.__init__(self, parent)
        self.filter_columns = {}
        self.text_filter = None

    def setTextFilter(self, text):
        if not text:
            self.text_filter = None
        else:
            self.text_filter = text.toLower()
        self.invalidateFilter()

    def setMultiFilter(self, column, index):
        if index == 0:
            self.filter_columns.pop(column)
        else:
            self.filter_columns[column] = index-1
        if not len(self.filter_columns) and not self.text_filter:
            self.reset()
            return
        self.invalidateFilter()

    def filterAcceptsRow(self, row, parent):
        if not len(self.filter_columns) and not self.text_filter:
            return True
        model = self.sourceModel()
        if len(self.filter_columns) and any([True for column, index in self.filter_columns.items() if model.item(row, column).data(UserRole) != index]):
            return False
        if not self.text_filter:
            return True
        if self.text_filter in model.item(row, NAME).text().toLower():
            return True
        return False

class LoadingThread(QtCore.QObject):
    loaded = QtCore.pyqtSignal()
    def __init__(self, parent, library, limit=None):
        self.limit = limit
        QtCore.QObject.__init__(self)
        self.library = library

    def run(self):
        pattern = midifile.read_midifile(local_path('presets/blofeld_fact_080103/blofeld_fact_080103.mid'))
        track = pattern[0]
        i = 0
        sound_list = []
        for event in track:
            if isinstance(event, midifile.SysexEvent):
                sound_list.append(Sound(event.data[6:391]))
                i += 1
                if i == self.limit: break
        self.library.addSoundBulk(sound_list)
        self.loaded.emit()

class LoadingWindow(QtGui.QDialog):
    shown = QtCore.pyqtSignal()
    def __init__(self, parent=None):
        self.main = parent
        QtGui.QDialog.__init__(self, parent)
        self.setWindowTitle('Presets loading...')
        self.setModal(True)
        grid = QtGui.QGridLayout(self)
        loading_lbl = QtGui.QLabel('Loading local presets, please wait')
        grid.addWidget(loading_lbl, 0, 0)
        self.loading = False
#        self.loader = LoadingThread(self)
#        self.loader_thread = QtCore.QThread()
#        self.loader.moveToThread(self.loader_thread)
#        self.loader_thread.started.connect(self.loader.run)
#        self.loader.loaded.connect(self.set_models)
#        self.loader.loaded.connect(self.main.set_models)

    def showEvent(self, event):
        if not self.loading:
            self.loading = True
            QtCore.QTimer.singleShot(100, self.shown.emit)

    def set_models(self, model, library):
        self.hide()

    def closeEvent(self, event):
        event.ignore()

class PopupSpin(QtGui.QDoubleSpinBox):
    indexChanged = QtCore.pyqtSignal(int)
    def __init__(self, parent):
        self.indexMinimum = 1
        self.indexMaximum = len(popup_values) - 1
        self.indexRange = self.indexMinimum, self.indexMaximum
        QtGui.QDoubleSpinBox.__init__(self, parent)
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
        res = QtGui.QDoubleSpinBox.validate(self, text, pos)
        if res in (QtGui.QValidator.Invalid, QtGui.QValidator.Intermediate):
            return res
        new_value = QtGui.QDoubleSpinBox.valueFromText(self, text)
        if not popup_values[self.indexMinimum] <= new_value <= popup_values[self.indexMaximum]:
            return QtGui.QValidator.Invalid, res[1]
        return res

    def valueFromText(self, text):
        new_value = QtGui.QDoubleSpinBox.valueFromText(self, text)
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

class Globals(QtGui.QDialog):
    midi_event = QtCore.pyqtSignal(object)
    def __init__(self, main, parent):
        pt = namedtuple('pt', 'index delta')
        pt.__new__.__defaults__ = (0, )
        QtGui.QDialog.__init__(self, parent)
        load_ui(self, 'globals.ui')
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

        self.resetBtn = self.buttonBox.button(QtGui.QDialogButtonBox.Reset)
        self.resetBtn.setText('Reload from Blofeld')
        self.applyBtn = self.buttonBox.button(QtGui.QDialogButtonBox.Apply)
        self.applyBtn.clicked.connect(self.send_data)
        self.okBtn = self.buttonBox.button(QtGui.QDialogButtonBox.Ok)
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
            if isinstance(w, QtGui.QSpinBox):
                w.valueChanged.connect(self.editData)
            elif isinstance(w, PopupSpin):
                w.indexChanged.connect(self.editData)
            elif isinstance(w, QtGui.QComboBox):
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
            if isinstance(w, QtGui.QSpinBox):
                w.setValue(data[p.index] + p.delta)
            elif isinstance(w, PopupSpin):
                w.setIndex(data[p.index])
            elif isinstance(w, QtGui.QComboBox):
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

class SettingsGroup(object):
    def __init__(self, settings, name=None):
        self._settings = settings
        self._group = settings.group()
        for k in settings.childKeys():
            value = settings.value(k).toPyObject()
            if isinstance(value, QtCore.QStringList):
                _value = []
                for v in value:
                    try:
                        v = str(v)
                        if v.isdigit():
                            v = int(v)
                        elif v == 'true':
                            v = True
                        elif v == 'false':
                            v = False
                        else:
                            v = float(v)
                    except Exception as e:
                        print e
                    _value.append(v)
                value = _value
            elif isinstance(value, QtCore.QString):
                value = str(value)
                if value == 'true':
                    value = True
                elif value == 'false':
                    value = False
                elif self._is_int(value):
                    value = int(value)
                else:
                    try:
                        value = float(value)
                    except:
                        pass
            setattr(self, self._decode(str(k)), value)
        if len(self._group):
            for g in settings.childGroups():
                settings.beginGroup(g)
                setattr(self, 'g{}'.format(self._decode(g)), SettingsGroup(settings))
                settings.endGroup()
        self._done = True

    def _is_int(self, value):
        try:
            int(value)
            return True
        except:
            return False

    def _encode(self, txt):
        txt = txt.replace('__', '::')
        txt = txt.replace('_', ' ')
        txt = txt.replace('::', '_')
        return txt

    def _decode(self, txt):
        txt = txt.replace('_', '__')
        txt = txt.replace(' ', '_')
        return txt

    def createGroup(self, name):
        self._settings.beginGroup(self._group)
        self._settings.beginGroup(name)
        gname = 'g{}'.format(self._decode(name))
        setattr(self, gname, SettingsGroup(self._settings))
        self._settings.endGroup()
        self._settings.endGroup()

    def __setattr__(self, name, value):
        if '_done' in self.__dict__.keys():
            if not isinstance(value, SettingsGroup):
                dname = self._encode(name)
                if len(self._group):
                    self._settings.beginGroup(self._group)
                    self._settings.setValue(dname, value)
                    self._settings.endGroup()
                else:
                    self._settings.setValue(dname, value)
                super(SettingsGroup, self).__setattr__(name, value)
            else:
                super(SettingsGroup, self).__setattr__(name, value)
        else:
            super(SettingsGroup, self).__setattr__(name, value)

    def __getattr__(self, name):
        def save_func(value):
            self._settings.beginGroup(self._group)
            self._settings.setValue(self._encode(name[4:]), value)
            self._settings.endGroup()
            setattr(self, name[4:], value)
            return value
        if name.startswith('set_'):
            obj = type('setter', (object, ), {})()
            obj.__class__.__call__ = lambda x, y=None: setattr(self, name[4:], y)
            return obj
        if not name.startswith('get_'):
            return
        try:
            orig = super(SettingsGroup, self).__getattribute__(name[4:])
            if isinstance(orig, bool):
                obj = type(type(orig).__name__, (object,), {'value': orig})()
                obj.__class__.__call__ = lambda x,  y=None, save=False, orig=orig: orig
                obj.__class__.__len__ = lambda x: orig
                obj.__class__.__eq__ = lambda x, y: True if x.value==y else False
            else:
                obj = type(type(orig).__name__, (type(orig), ), {})(orig)
                obj.__class__.__call__ = lambda x, y=None, save=False, orig=orig: orig
            return obj
        except AttributeError:
            print 'Setting {} not found, returning default'.format(name[4:])
            obj = type('obj', (object,), {})()
            obj.__class__.__call__ = lambda x, y=None, save=False:y if not save else save_func(y)
            return obj

class SettingsObj(object):
    def __init__(self, settings):
        self._settings = settings
        self._sdata = []
        self._load()
        self._done = True

    def _load(self):
        for d in self._sdata:
            delattr(self, d)
        self._sdata = []
        self._settings.sync()
        self.gGeneral = SettingsGroup(self._settings)
        self._sdata.append('gGeneral')
        for g in self._settings.childGroups():
            self._settings.beginGroup(g)
            gname = 'g{}'.format(self._decode(g))
            self._sdata.append(gname)
            setattr(self, gname, SettingsGroup(self._settings))
            self._settings.endGroup()

    def __getattr__(self, name):
        if not (name.startswith('g') and name[1] in uppercase):
            raise AttributeError(name)
        name = name[1:]
        self._settings.beginGroup(name)
        gname = 'g{}'.format(self._decode(name))
        self._sdata.append(gname)
        new_group = SettingsGroup(self._settings)
        setattr(self, gname, new_group)
        self._settings.endGroup()
        return new_group

    def sync(self):
        self._settings.sync()

    def createGroup(self, name):
        self._settings.beginGroup(name)
        gname = 'g{}'.format(self._decode(name))
        self._sdata.append(gname)
        setattr(self, gname, SettingsGroup(self._settings))
        self._settings.endGroup()

    def _decode(self, txt):
        txt = txt.replace('_', '__')
        txt = txt.replace(' ', '_')
        return txt







