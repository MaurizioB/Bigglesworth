#!/usr/bin/env python2.7
# *-* coding: utf-8 *-*

import sys
from string import uppercase
from PyQt4 import QtCore, QtGui

from alsa import *
from midiutils import *
from utils import *
from classes import *
from const import *
from utils import *

from editor import Editor

class BigglesworthObject(QtCore.QObject):
    globals_event = QtCore.pyqtSignal(object)
    device_event = QtCore.pyqtSignal(object)
    sound_dump = QtCore.pyqtSignal(object)
    parameter_change = QtCore.pyqtSignal(int, int, int)
    pgm_change_received = QtCore.pyqtSignal(int, int)
    input_conn_state_change = QtCore.pyqtSignal(int)
    output_conn_state_change = QtCore.pyqtSignal(int)
    def __init__(self, app, argv):
        QtCore.QObject.__init__(self)
        self.app = app
        self.qsettings = QtCore.QSettings()
        self.settings = SettingsObj(self.qsettings)

#        self.app.lastWindowClosed.connect(self.save_settings)
        self.font_db = QtGui.QFontDatabase()
        self.font_db.addApplicationFont(local_path('FiraSans-Regular.ttf'))

        self.alsa_thread = QtCore.QThread()
        self.alsa = AlsaMidi(self)
        self.alsa.moveToThread(self.alsa_thread)
        self.alsa.stopped.connect(self.alsa_thread.quit)
        self.alsa_thread.started.connect(self.alsa.run)

        self.alsa.midi_event.connect(self.midi_event_received)
        self.graph.port_start.connect(self.new_alsa_port)
        self.alsa.conn_register.connect(self.alsa_conn_event)
        self.alsa_thread.start()

        self.seq = self.alsa.seq
        self.input = self.alsa.input
        self.output = self.alsa.output
        self.midi_connect()

        self.deviceAction = QtGui.QAction(self)
        self.deviceAction.triggered.connect(self.device_request)
        self.globalsAction = QtGui.QAction('Global parameters...', self)
        self.globalsAction.triggered.connect(self.globals_request)

        self.blofeld_current = [None, None]
        self.blofeld_model = LibraryModel()
        self.blofeld_library = Library(self.blofeld_model)

        if len(argv) > 1 and argv[1].isdigit():
            limit = int(argv[1])
        else:
            limit = None
        self.loader = LoadingThread(self, self.blofeld_library, limit)
        self.loader_thread = QtCore.QThread()
        self.loader.moveToThread(self.loader_thread)
        self.loader_thread.started.connect(self.loader.run)


        self.librarian = Librarian(self)
        self.librarian.quitAction.triggered.connect(self.app.quit)
        self.device_event.connect(lambda event: self.device_response(event, self.librarian))
        self.sound_dump.connect(self.librarian.sound_dump)
        self.loader.loaded.connect(self.librarian.create_proxy)
        self.loader.loaded.connect(self.librarian.create_proxy)
        self.loading_win = LoadingWindow(self.librarian)
        self.librarian.shown.connect(self.loading_win.show)
        self.loading_win.shown.connect(self.loader_thread.start)
        self.loader.loaded.connect(self.loading_win.hide)

        self.librarian.midi_event.connect(self.output_event)
        self.librarian.program_change.connect(self.program_change_request)

        self.editor = Editor(self)
        self.editor.pgm_receive_btn.setChecked(self.editor_remember_states[PGMRECEIVE])
        self.editor.midi_receive_btn.setChecked(self.editor_remember_states[MIDIRECEIVE])
        self.editor.pgm_send_btn.setChecked(self.editor_remember_states[PGMSEND])
        self.editor.midi_send_btn.setChecked(self.editor_remember_states[MIDISEND])
        self.librarian.activate_editor.connect(self.activate_editor)
        self.pgm_change_received.connect(self.editor.pgm_change_received)
        self.editor.show_librarian.connect(lambda: [self.librarian.show(), self.librarian.activateWindow()])
        self.editor.midi_event.connect(self.output_event)
        self.editor.program_change.connect(self.program_change_request)
        self.editor.pgm_receive.connect(lambda state: self.set_editor_remember(PGMRECEIVE, state))
        self.editor.midi_receive.connect(lambda state: self.set_editor_remember(MIDIRECEIVE, state))
        self.editor.pgm_send.connect(lambda state: self.set_editor_remember(PGMSEND, state))
        self.editor.midi_send.connect(lambda state: self.set_editor_remember(MIDISEND, state))
        self.parameter_change.connect(self.editor.receive_value)
        self.output_conn_state_change.connect(self.editor.midi_output_state)
        self.input_conn_state_change.connect(self.editor.midi_input_state)

        self.globals = Globals(self, self.librarian)
        self.globals.midi_event.connect(self.output_event)
        self.globals_event.connect(self.activate_globals)
        self.globals.buttonBox.button(QtGui.QDialogButtonBox.Reset).clicked.connect(self.globals_request)

        self.librarian.show()
        self.midiwidget = MidiWidget(self)
        self.mididialog = MidiDialog(self, self.editor)
        self.editor.show_midi_dialog.connect(self.mididialog.show)

        self.settings_dialog = SettingsDialog(self, self.librarian)
        self.librarian.settingsAction.triggered.connect(self.show_settings)
#        self.settings_dialog.show()

    def show_settings(self):
        self.settings_dialog.exec_()

    @property
    def library_doubleclick(self):
        try:
            return self._library_doubleclick
        except:
            self._library_doubleclick = self.settings.gGeneral.get_Library_doubleclick(3, True)
            return self._library_doubleclick

    @library_doubleclick.setter
    def library_doubleclick(self, value):
        self.settings.gGeneral.set_Library_doubleclick(value)
        self._library_doubleclick = value

    @property
    def autoconnect(self):
        try:
            return self._autoconnect
        except:
            self._autoconnect = self.settings.gMIDI.get_Autoconnect({INPUT: set(), OUTPUT: set()}, True)
            return self._autoconnect

    @property
    def blofeld_autoconnect(self):
        try:
            return self._blofeld_autoconnect
        except:
            self._blofeld_autoconnect = self.settings.gMIDI.get_Blofeld_autoconnect(True, True)
            return self._blofeld_autoconnect

    @blofeld_autoconnect.setter
    def blofeld_autoconnect(self, value):
        self.settings.gMIDI.set_Blofeld_autoconnect(value)
        self._blofeld_autoconnect = value

    @property
    def remember_connections(self):
        try:
            return self._remember_connections
        except:
            self._remember_connections = self.settings.gMIDI.get_Remember_connections(True, True)
            return self._remember_connections

    @remember_connections.setter
    def remember_connections(self, value):
        self.settings.gMIDI.set_Remember_connections(value)
        self._remember_connections = value

    @property
    def editor_remember(self):
        try:
            return self._editor_remember
        except:
            self._editor_remember = self.settings.gEditor.get_Remember(True, True)
            return self._editor_remember

    @editor_remember.setter
    def editor_remember(self, value):
        self.settings.gEditor.set_Remember(value)
        self._editor_remember = value

    @property
    def editor_remember_states(self):
        try:
            return self._editor_remember_states
        except:
            self._editor_remember_states = self.settings.gEditor.get_Remember_states(list((True, True, True, True)), True)
            return self._editor_remember_states

    @editor_remember_states.setter
    def editor_remember_states(self, value):
        self.settings.gEditor.set_Remember_states(value)
        self._editor_remember_states = value

    @property
    def editor_appearance_remember(self):
        try:
            return self._editor_appearance_remember
        except:
            self._editor_appearance_remember = self.settings.gEditor.get_Remember_Appearance(True, True)
            return self._editor_appearance_remember

    @editor_appearance_remember.setter
    def editor_appearance_remember(self, value):
        self._editor_appearance_remember = self.settings.gEditor.set_Remember_Appearance(value)
        self._editor_appearance_remember = value

    @property
    def editor_appearance_filter_matrix(self):
        try:
            return self._editor_appearance_filter_matrix
        except:
            self._editor_appearance_filter_matrix = self.settings.gEditor.get_Remember_Appearance_FilterMatrix(0, True)
            return self._editor_appearance_filter_matrix

    @editor_appearance_filter_matrix.setter
    def editor_appearance_filter_matrix(self, value):
        self._editor_appearance_filter_matrix = self.settings.gEditor.set_Remember_Appearance_FilterMatrix(value)
        self._editor_appearance_filter_matrix = value


    def set_editor_remember(self, _type, state):
        if not self.editor_remember: return
        current = self.editor_remember_states[:]
        current[_type] = state
        self.editor_remember_states = current

    def new_alsa_port(self, port):
        if self.blofeld_autoconnect and port.client.name == 'Blofeld' and port.name == 'Blofeld MIDI 1':
            port.connect(self.input)
            self.output.connect(port)
        if not self.remember_connections: return
        port_fmt = '{}:{}'.format(port.client.name, port.name)
        if port.is_output and port_fmt in self.autoconnect[INPUT]:
            port.connect(self.input)
        if port.is_input and port_fmt in self.autoconnect[OUTPUT]:
            self.output.connect(port)

    def alsa_conn_event(self, conn, state):
        if conn.dest == self.input:
            conn_list = [c for c in self.input.connections.input if not c.hidden]
            self.input_conn_state_change.emit(len(conn_list))
            if self.remember_connections:
                port_fmt = '{}:{}'.format(conn.src.client.name, conn.src.name)
                if port_fmt == 'Blofeld:Blofeld MIDI 1': return
                if state:
                    self.autoconnect[INPUT] = self.autoconnect[INPUT] | set([port_fmt])
                else:
                    self.autoconnect[INPUT].discard(port_fmt)
                self.settings.gMIDI.set_Autoconnect(self.autoconnect)
        elif conn.src == self.output:
            conn_list = [c for c in self.output.connections.output if not c.hidden]
            self.output_conn_state_change.emit(len(conn_list))
            if self.remember_connections:
                port_fmt = '{}:{}'.format(conn.dest.client.name, conn.dest.name)
                if port_fmt == 'Blofeld:Blofeld MIDI 1': return
                if state:
                    self.autoconnect[OUTPUT] = self.autoconnect[OUTPUT] | set([port_fmt])
                else:
                    self.autoconnect[OUTPUT].discard(port_fmt)
                self.settings.gMIDI.set_Autoconnect(self.autoconnect)

    def midi_connect(self):
        if not (self.blofeld_autoconnect or self.remember_connections): return
        for cid, client in self.graph.client_id_dict.items():
            if self.blofeld_autoconnect and client.name == 'Blofeld' and len(client.ports) == 1 and client.ports[0].name == 'Blofeld MIDI 1':
                self.graph.port_id_dict[cid][0].connect(self.seq.client_id, self.input.id)
                self.graph.port_id_dict[self.seq.client_id][self.output.id].connect(cid, 0)
                continue
            if not self.remember_connections: continue
            for port in client.ports:
                port_fmt = '{}:{}'.format(client.name, port.name)
                if port.is_output and port_fmt in self.autoconnect[INPUT]:
                    port.connect(self.input)
                if port.is_input and port_fmt in self.autoconnect[OUTPUT]:
                    self.output.connect(port)


    def program_change_request(self, bank, prog):
        self.output_event(CtrlEvent(1, 0, 0, bank))
        self.output_event(ProgramEvent(1, 0, prog))

    def output_event(self, event):
        alsa_event = event.get_event()
        alsa_event.source = self.output.client.id, self.output.id
        self.seq.output_event(alsa_event)
        self.seq.drain_output()

    def midi_event_received(self, event):
        if event.type == SYSEX:
#            print 'receiving event: {}'.format(len(event.sysex))
#            print event.sysex
            sysex_type = event.sysex[4]
            if sysex_type == SNDD:
                self.sound_dump.emit(event.sysex[5:390])
            elif sysex_type == SNDP:
                self.sysex_parameter(event.sysex[5:])
            elif sysex_type == GLBD:
                self.globals_event.emit(event.sysex)
#                self.main.globals.setData(event.sysex)
            elif len(event.sysex) == 15 and event.sysex[3:5] == [6, 2]:
                self.device_event.emit(event.sysex)
#                self.device_response(event.sysex)
        elif event.type == CTRL:
            if event.data1 == 0:
                self.blofeld_current[0] = event.data2
            else:
                self.ctrl_parameter(event.data1, event.data2)
        elif event.type == PROGRAM:
            self.blofeld_current[1] = event.data2
            if None in self.blofeld_current: return
            self.librarian.blofeld_sounds_table.selectRow(self.librarian.blofeld_model_proxy.mapFromSource(self.blofeld_model.index(self.blofeld_current[0]*128+self.blofeld_current[1], 0)).row())
            self.pgm_change_received.emit(*self.blofeld_current)

    def sysex_parameter(self, data):
        location = data[0]
        index = data[1]*128+data[2]
        value = data[3]
        self.parameter_change.emit(location, index, value)

    def ctrl_parameter(self, param_id, value):
        if param_id in ctrl2sysex:
            self.parameter_change.emit(0, ctrl2sysex[param_id], value)

    def activate_editor(self, bank, prog):
        self.editor.show()
        self.editor.setSound(bank, prog)
        self.editor.activateWindow()

    def activate_globals(self, data):
        self.globals.setData(data)

    def device_request(self):
        self.output_event(SysExEvent(1, [0xF0, 0x7e, 0x7f, 0x6, 0x1, 0xf7]))

    def globals_request(self):
        self.output_event(SysExEvent(1, [0xF0, 0x3e, 0x13, 0x0, GLBR, 0xf7]))

    def device_response(self, sysex, parent):
        if sysex[5] == 0x3e:
            dev_man = 'Waldorf Music'
        else:
            dev_man = 'Unknown'
        if sysex[6:8] == [0x13, 0x0]:
            dev_model = 'Blofeld'
        else:
            dev_model = 'Unknown'
        if sysex[8:10] == [0, 0]:
            dev_type = 'Blofeld Desktop'
        else:
            dev_type = 'Blofeld Keyboard'
        dev_version = ''.join([str(unichr(l)) for l in sysex[10:14]]).strip()
        
        QtGui.QMessageBox.information(parent, 'Device informations', 
                                      'Device info:\n\nManufacturer: {}\nModel: {}\nType: {}\nVersion: {}'.format(
                                       dev_man, dev_model, dev_type, dev_version))

    def save_settings(self):
        print self.connections


class Librarian(QtGui.QMainWindow):
    shown = QtCore.pyqtSignal()
    program_change = QtCore.pyqtSignal(int, int)
    midi_event = QtCore.pyqtSignal(object)
    dump_waiter = QtCore.pyqtSignal()
    activate_editor = QtCore.pyqtSignal(int, int)
    def __init__(self, main):
        QtGui.QMainWindow.__init__(self, parent=None)
        load_ui(self, 'main.ui')

        self.main = main

        self.blofeld_model = self.main.blofeld_model
        self.blofeld_library = self.main.blofeld_library
        self.blofeld_current = self.main.blofeld_current
        self.blofeld_model.itemChanged.connect(self.sound_update)

        self.loading_complete = False
        self.edit_mode = False

        self.dump_timer = QtCore.QTimer()
        self.dump_timer.setInterval(100)
        self.dump_timer.setSingleShot(True)
        self.dump_timer.timeout.connect(lambda: self.dump_waiter.emit())

        self.dump_active = False
        self.dump_elapsed = QtCore.QElapsedTimer()
        self.dump_win = DumpWin(self)
        self.dump_win.rejected.connect(lambda: setattr(self, 'dump_active', False))
        self.dump_win.rejected.connect(self.dump_timer.stop)

        self.bank_dump_combo.addItems(['All']+[l for l in uppercase[:8]])
        self.sound_dump_combo.addItems(['All']+[str(s) for s in range(1, 129)])
        self.bank_filter_combo.addItems(['All']+[l for l in uppercase[:8]])
        self.cat_filter_combo.addItem('All')
        for cat in categories:
            self.cat_filter_combo.addItem(cat, cat)
        self.bank_filter_combo.currentIndexChanged.connect(lambda index: self.blofeld_model_proxy.setMultiFilter(BANK, index))
        self.bank_filter_combo.currentIndexChanged.connect(self.bank_list_update)
        self.cat_filter_combo.currentIndexChanged.connect(lambda index: self.blofeld_model_proxy.setMultiFilter(CATEGORY, index))

        self.device_btn.clicked.connect(self.main.deviceAction.trigger)
        self.globals_btn.clicked.connect(self.main.globalsAction.trigger)
        self.dump_btn.clicked.connect(self.dump_request)
        self.bank_dump_combo.currentIndexChanged.connect(lambda b: self.sound_dump_combo.setEnabled(True if b != 0 else False))
        self.edit_btn.toggled.connect(self.edit_mode_set)
        self.search_edit.textChanged.connect(self.search_filter)
        self.search_clear_btn.clicked.connect(lambda _: self.search_edit.setText(''))
        self.search_filter_chk.toggled.connect(self.search_filter_set)
        self.blofeld_sounds_table.doubleClicked.connect(self.sound_doubleclick)
        self.blofeld_sounds_table.mouseReleaseEvent = self.right_click
        self.blofeld_sounds_table.dropEvent = self.sound_drop_event
#        self.blofeld_model.dataChanged.connect(self.sound_update)
#        self.blofeld_model.itemChanged.connect(self.sound_update)
        self.installEventFilter(self)
        self.search_edit.installEventFilter(self)
        self.search_filter_chk.installEventFilter(self)


    def showEvent(self, event):
        if not self.loading_complete:
            QtCore.QTimer.singleShot(10, self.shown.emit)

    def eventFilter(self, source, event):
        if event.type() == QtCore.QEvent.KeyPress:
            if event.key() == QtCore.Qt.Key_F5:
                self.dump_request()
            elif event.key() == QtCore.Qt.Key_Escape and source == self.search_edit:
                self.search_edit.setText('')
        if source == self.search_filter_chk and event.type() == QtCore.QEvent.FocusIn and event.reason() == QtCore.Qt.OtherFocusReason:
            self.search_edit.setFocus()
        return QtGui.QMainWindow.eventFilter(self, source, event)


    def edit_mode_set(self, state):
        self.edit_mode = state
        self.blofeld_sounds_table.setEditTriggers(QtGui.QTableView.DoubleClicked|QtGui.QTableView.EditKeyPressed if state else QtGui.QTableView.NoEditTriggers)
        self.blofeld_sounds_table.setDragEnabled(False if state else True)
        self.blofeld_sounds_table.setSelectionMode(QtGui.QTableView.SingleSelection if state else QtGui.QTableView.ContiguousSelection)

    def search_filter_set(self, state):
        if not state:
            self.blofeld_model_proxy.setTextFilter('')
        self.search_filter(self.search_edit.text())
        return

    def search_filter(self, text):
        filter =  self.search_filter_chk.isChecked()
        if not text and not filter: return
        if not filter:
            found = self.blofeld_model.findItems(text, QtCore.Qt.MatchContains, 3)
            if found:
                self.blofeld_sounds_table.selectRow(found[0].row())
            return
        self.blofeld_model_proxy.setTextFilter(text)

    def sound_doubleclick(self, index):
        if self.edit_mode: return
        behaviour = self.main.library_doubleclick
        if behaviour == 0: return
        sound = self.blofeld_model.item(self.blofeld_model_proxy.mapToSource(index).row(), SOUND).data(SoundRole).toPyObject()
        if behaviour == 1:
            self.program_change.emit(sound.bank, sound.prog)
        elif behaviour == 2:
            self.activate_editor.emit(sound.bank, sound.prog)
        else:
            self.program_change.emit(sound.bank, sound.prog)
            self.activate_editor.emit(sound.bank, sound.prog)

    def right_click(self, event):
        if event.button() != QtCore.Qt.RightButton: return
        index = self.blofeld_sounds_table.indexAt(event.pos())
        sound = self.blofeld_model.item(self.blofeld_model_proxy.mapToSource(index).row(), SOUND).data(SoundRole).toPyObject()
        menu = QtGui.QMenu()
        menu.setSeparatorsCollapsible(False)
        header = QtGui.QAction(sound.name, menu)
        header.setSeparator(True)
        menu.addAction(header)
        edit_item = QtGui.QAction('Edit...', menu)
        menu.addAction(edit_item)
        menu.show()
        fm = QtGui.QFontMetrics(edit_item.font())
        minsize = 0
        for a in menu.actions():
            if a == header: continue
            width = fm.width(a.text())
            if width > minsize:
                minsize = width
        frame_delta = menu.width()-minsize
        menu.setMinimumWidth(frame_delta+QtGui.QFontMetrics(header.font()).width(header.text()))
        res = menu.exec_(event.globalPos())
        if res == edit_item:
            self.activate_editor.emit(sound.bank, sound.prog)

    def sound_drop_event(self, event):
        def rename(sound_range):
#            first, last = sorted(sound_range)
            first = min(sound_range)
            last = max(sound_range)
            print first, last
            for row in range(first, last+1):
                bank, prog = divmod(row, 128)
                sound = self.blofeld_library[bank, prog]
                sound.prog += 1
#                sound.bank, sound.prog = divmod(row+1, 128)
                self.blofeld_model.item(row, BANK).setText(uppercase[sound.bank])
                self.blofeld_model.item(row, PROG).setText('{:03}'.format(sound.prog+1))
#                self.blofeld_model.item(row, 0).setText(str(row+1))
#                sound = self.blofeld_model.item(row, SOUND).data(SoundRole).toPyObject()
#                sound.prog, sound.bank = divmod(row, 128)
                
#                bank = index_item.data(SoundRole).toPyObject()/128
#                self.blofeld_model.item(row, 0).setData(bank*128+row, SoundRole)
        drop_pos = self.blofeld_sounds_table.dropIndicatorPosition()
        rows = set([self.blofeld_model_proxy.mapToSource(index).row() for index in self.blofeld_sounds_table.selectedIndexes()])
        current_bank = self.bank_filter_combo.currentIndex() - 1
        if len(rows) == 1:
            source = self.blofeld_model_proxy.mapToSource(self.blofeld_sounds_table.currentIndex()).row()
            if drop_pos == QtGui.QTableView.OnViewport:
                if current_bank < 0:
                    target = self.blofeld_model.rowCount()-1
                else:
                    target = 127 + current_bank * 128
            else:
                target = self.blofeld_model_proxy.mapToSource(self.blofeld_sounds_table.indexAt(event.pos())).row()
            items = self.blofeld_model.takeRow(source)
            self.blofeld_model.insertRow(target, items)
            rename((source, target))
        else:
            if drop_pos == QtGui.QTableView.OnViewport:
                if current_bank < 0:
                    if max(rows) == self.blofeld_model.rowCount()-1: return
                    target = self.blofeld_model.rowCount()-1
                else:
                    target = 127 + current_bank * 128
            else:
                target = self.blofeld_model_proxy.mapToSource(self.blofeld_sounds_table.indexAt(event.pos())).row()
                if target in rows: return
            first = min(rows)
            before = True if target < first else False
            for d in range(max(rows)+1-first):
                items = self.blofeld_model.takeRow(first)
                self.blofeld_model.insertRow(target if not before else target+d, items)
            rename((target, )+tuple(rows))

#        self.blofeld_model.sort(2)
#        self.blofeld_model.sort(1)


    def sound_update(self, item, _=None):
#        print 'updating {}'.format(item.column())
#        print self.sender()
        if item.column() == STATUS:
            item.setText(get_status(item.data(EditedRole).toPyObject()))
            setBold(item)

    def program_change_request(self, bank, prog):
        self.midi_event.emit(CtrlEvent(1, 0, 0, bank))
        self.midi_event.emit(ProgramEvent(1, 0, prog))

    def dump_request(self):
        bank = self.bank_dump_combo.currentIndex()
        sound = self.sound_dump_combo.currentIndex()
        if bank != 0 and sound != 0:
            self.sound_request(bank-1, sound-1)
        elif bank != 0 and sound == 0:
            self.dump_active = True
            self.dump_elapsed.start()
            self.dump_win.show()
            self.dump_win.progress.setMaximum(128)
            self.sound_request(bank-1, 0)
        else:
            self.dump_active = True
            self.dump_elapsed.start()
            self.dump_win.show()
            self.dump_win.progress.setMaximum(1024)
            self.sound_request(0, 0)
        

    def sound_request(self, bank, sound):
        self.midi_event.emit(SysExEvent(1, [0xF0, 0x3e, 0x13, 0x0, 0x0, bank, sound, 0x7f, 0xf7]))

#    def create_models(self):
#        self.bank_dump_combo.addItems(['All']+[l for l in uppercase[:8]])
#        self.sound_dump_combo.addItems(['All']+[str(s) for s in range(1, 129)])
#
#        self.bank_filter_combo.addItems(['All']+[l for l in uppercase[:8]])
#        self.cat_filter_combo.addItem('All')
#        for cat in categories:
#            self.cat_filter_combo.addItem(cat, cat)
#        self.bank_filter_combo.currentIndexChanged.connect(lambda index: self.blofeld_model_proxy.setMultiFilter(BANK, index))
#        self.bank_filter_combo.currentIndexChanged.connect(self.bank_list_update)
#        self.cat_filter_combo.currentIndexChanged.connect(lambda index: self.blofeld_model_proxy.setMultiFilter(CATEGORY, index))

    def create_proxy(self):
        self.loading_complete = True
#        self.blofeld_library = self.editor.blofeld_library = library
##        self.editor.create_sorted_library()
#        self.blofeld_model = model
#        self.blofeld_model.itemChanged.connect(self.sound_update)
        self.blofeld_model_proxy = LibraryProxy()
        self.blofeld_model_proxy.setSourceModel(self.blofeld_model)
        self.blofeld_sounds_table.setModel(self.blofeld_model_proxy)
        self.blofeld_sounds_table.horizontalHeader().setResizeMode(QtGui.QHeaderView.ResizeToContents)
        self.blofeld_sounds_table.horizontalHeader().setResizeMode(NAME, QtGui.QHeaderView.Stretch)
        self.blofeld_sounds_table.verticalHeader().setResizeMode(QtGui.QHeaderView.ResizeToContents)
        self.blofeld_sounds_table.setItemDelegateForColumn(4, CategoryDelegate(self))
        self.blofeld_sounds_table.setColumnHidden(INDEX, True)
        for c in range(len(sound_headers), self.blofeld_model.columnCount()):
            self.blofeld_sounds_table.setColumnHidden(c, True)
        self.blofeld_sounds_table.horizontalHeader().setResizeMode(PROG, QtGui.QHeaderView.Fixed)
        self.blofeld_sounds_table.resizeColumnToContents(PROG)


    def bank_list_update(self, bank):
        self.cat_count_update()

#    def filter_update(self, id=None):
#        bank_filter = self.bank_filter_combo.currentIndex()
#        cat_filter = self.cat_filter_combo.currentIndex()
#        self.blofeld_model_proxy.setMultiFilter(bank_filter-1, cat_filter-1)
#        return
#        print 'filtering with {} and {}'.format(bank_filter, cat_filter)
#        if bank_filter == 0 and cat_filter == 0:
#            for r in range(self.blofeld_model.rowCount()):
#                self.blofeld_sounds_table.setRowHidden(r, False)
#            print 'done'
#            return
#        print 'what'
#        for r in range(self.blofeld_model.rowCount()):
#            self.blofeld_sounds_table.setRowHidden(
#                                                   r, 
#                                                   False if (
#                                                             bank_filter == 0 or self.blofeld_model.index(r, 0).data(BankRole).toPyObject() == bank_filter-1
#                                                             ) and (
#                                                             cat_filter == 0 or self.blofeld_model.index(r, 4).data(CatRole).toPyObject() == cat_filter-1
#                                                             ) else True
#                                                   )

    def cat_count_update(self):
        cat_len = [0 for cat_id in categories]
        current_bank = self.bank_filter_combo.currentIndex()
        return
        for bank, sound_list in enumerate(self.blofeld_library):
            if current_bank != 0 and current_bank != bank+1: continue
            for s in sound_list:
                if s.data is None: continue
                cat_len[s.cat] += 1
        for cat_id in range(1, self.cat_filter_combo.model().rowCount()):
            self.cat_filter_combo.setItemText(cat_id, '{} ({})'.format(
                                               self.cat_filter_combo.model().item(cat_id).data(QtCore.Qt.UserRole).toPyObject(),
                                               cat_len[cat_id-1]
                                               ))



    def globals_dump(self, data):
        globals = self.main.globals
        globals.autoEdit_chk.setEnabled(data[35])
        globals.contrast_spin.setValue(data[39])
        globals.cat_combo.setCurrentIndex(data[56])
        globals.show()

    def sound_dump(self, sound_event):
        sound = Sound(sound_event, SRC_BLOFELD)
        if sound.bank > 25:
            if None in self.blofeld_current:
                #you'll ask what to do with incoming sysex, we don't know where it goes
                print 'no current sound selected'
                return
            else:
                sound._bank, sound._prog = self.blofeld_current
        bank, prog = sound.bank, sound.prog
        self.blofeld_library.addSound(sound)

        if not self.dump_active:
            self.cat_count_update()
            self.blofeld_sounds_table.resizeColumnToContents(2)
            self.blofeld_sounds_table.resizeColumnToContents(5)
            return
        dump_all = True if self.bank_dump_combo.currentIndex()==0 else False
        if prog >= 127:
            if dump_all:
                bank += 1
                if bank >= 8:
                    self.dump_active = False
                    self.dump_win.done(1)
                    self.cat_count_update()
                    self.blofeld_sounds_table.resizeColumnToContents(2)
                    return
                prog = -1
            else:
                self.dump_active = False
                self.dump_win.accept()
                return
        self.dump_win.bank_lbl.setText('{}{}'.format(uppercase[bank], ' {}/8'.format(bank+1) if dump_all else ''))
        self.dump_win.sound_lbl.setText('{:03}/{}'.format(prog+1+(128*bank if dump_all else 0), 1024 if dump_all else 128))
        dump_time = None
        if dump_all:
            if not (bank == 0 and prog < 10):
                dump_time = self.dump_elapsed.elapsed()/float(prog+1+128*bank)*(1024-prog-128*bank)/1000
        else:
            if prog > 5:
                dump_time = self.dump_elapsed.elapsed()/float(prog+1)*(128-prog)/1000
        if dump_time is not None:
            self.dump_win.time.setText('{}:{:02}'.format(*divmod(int(dump_time)+1, 60)))
        self.dump_win.progress.setValue(prog+1+(128*bank if dump_all else 0))
        self.dump_timer.timeout.disconnect()
        self.dump_timer.timeout.connect(lambda: self.sound_request(bank, prog+1))
        self.dump_timer.start()
#        QtCore.QTimer.singleShot(200, lambda: self.sound_request(0, prog+1))



def main():
    argv = sys.argv[:]
    argv[0] = 'Bigglesworth'
    app = QtGui.QApplication(argv)
    app.setOrganizationName('jidesk')
    app.setApplicationName('Bigglesworth')
#    app.setQuitOnLastWindowClosed(False)
    cursor_list.extend((QtCore.Qt.SizeAllCursor, UpCursorClass(), DownCursorClass(), LeftCursorClass(), RightCursorClass()))
    bigglesworth = BigglesworthObject(app, argv)
    sys.exit(app.exec_())
    print 'Blofix has been quit!'

if __name__ == '__main__':
    main()









