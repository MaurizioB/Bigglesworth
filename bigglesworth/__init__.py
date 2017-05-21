#!/usr/bin/env python2.7
# *-* coding: utf-8 *-*

import sys
import argparse
import pickle
import re
from os import path, makedirs
from string import uppercase
from PyQt4 import QtCore, QtGui

from midiutils import *
from const import *
from utils import *
from classes import *
from widgets import *
from dialogs import *

from editor import Editor
from wavetable import WaveTableEditor

def process_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--sysex', help='Print output SysEx messages to the terminal', action='store_true')
    parser.add_argument('--rtmidi', help='Use rtmidi interface (mandatory for OSX/Windows, not recommended for Linux)', action='store_true')
    parser.add_argument('-l', '--library-limit', metavar='N', type=int, help=argparse.SUPPRESS)
    parser.add_argument('-w', '--wavetable', metavar='WTFILE', nargs='?', const=True, help='Open Wavetable editor (with optional WTFILE)')
    parser.add_argument('-e', '--editor', metavar='BXXX', nargs='?', const=True, help='Open Sound editor (with INIT sound or optional sound XXX from bank B, eg. A001)')
    res, unknown = parser.parse_known_args()
    if unknown:
        print 'Unknown parameters ignored:'
        for p in unknown:
            print p
    return res

args = process_args()
if sys.platform in ('win32', 'darwin') or args.rtmidi:
    from rt import MidiDevice
else:
    from alsa import MidiDevice

class BigglesworthObject(QtCore.QObject):
    midi_lock = QtCore.pyqtSignal(bool)
    globals_event = QtCore.pyqtSignal(object)
    device_event = QtCore.pyqtSignal(object)
    parameter_change_received = QtCore.pyqtSignal(int, int, int)
    program_change_received = QtCore.pyqtSignal(int, int)
    input_conn_state_change = QtCore.pyqtSignal(int)
    output_conn_state_change = QtCore.pyqtSignal(int)
    midi_duplex_state_change = QtCore.pyqtSignal(bool)

    def __init__(self, app, args):
        QtCore.QObject.__init__(self)
        self.app = app
        self.qsettings = QtCore.QSettings()
        self.settings = SettingsObj(self.qsettings)

        self.font_db = QtGui.QFontDatabase()
        self.font_db.addApplicationFont(local_path('FiraSans-Regular.ttf'))
        self.font_db.addApplicationFont(local_path('DroidSansFallback.ttf'))

        if args.sysex:
            self.debug_sysex = True
        else:
            self.debug_sysex = False
        if args.library_limit:
            limit = args.library_limit
        else:
            limit = None

        self.midi = MidiDevice(self)
        if args.rtmidi or sys.platform in ('win32', 'darwin'):
            self.backend = RTMIDI
        else:
            self.backend = ALSA
        self.midi_thread = QtCore.QThread()
        self.midi.moveToThread(self.midi_thread)
        self.midi.stopped.connect(self.midi_thread.quit)
        self.midi_thread.started.connect(self.midi.run)

        self.graph.port_start.connect(self.new_alsa_port)
        self.graph.conn_register.connect(self.alsa_conn_event)
        self.seq = self.midi.seq
        self.input = self.midi.input
        self.output = self.midi.output
        self.connections = [0, 0]
        self.midi_duplex_state = False
        self.midi_thread.start()

        self.midi.midi_event.connect(self.midi_event_received)


        self.blofeld_current = [None, None]
        self.blofeld_model = LibraryModel()
        self.wavetable_library = WavetableLibrary(self)
        self.blofeld_library = Library(self.blofeld_model)


        #LOADING
        self.loader = LoadingThread(self, self.blofeld_library, self.source_library, self.wavetable_library, limit=limit)
        self.loader_thread = QtCore.QThread()
        self.loader.moveToThread(self.loader_thread)
        self.loader_thread.started.connect(self.loader.run)

        self.midi_lock_status = False
        self.midi_lock.connect(lambda state: setattr(self, 'midi_lock_status', state))

        #LIBRARY
        QtGui.QIcon.setThemeName(QtGui.QApplication.style().objectName())
        self.librarian = Librarian(self)
        self.librarian.dump_send.connect(self.dump_send)
        self.librarian.dump_bulk_send.connect(self.dump_bulk_send)
        self.quitAction = self.librarian.quitAction
        self.importAction = self.librarian.importAction
        self.importAction.triggered.connect(self.file_import)
        self.saveAction = self.librarian.saveAction
        self.saveAction.triggered.connect(self.save_library)
        self.settingsAction = self.librarian.settingsAction
        self.settingsAction.setIcon(QtGui.QIcon(QtGui.QIcon.fromTheme('preferences-other')))
        self.quitAction.setIcon(QtGui.QIcon.fromTheme('application-exit'))
        dial_icon = QtGui.QIcon()
        dial_icon.addFile(local_path('dial_icon.png'))
        self.librarian.editorAction.setIcon(dial_icon)
        wt_icon = QtGui.QIcon()
        wt_icon.addFile(local_path('wt_icon.png'))
        self.librarian.wavetableAction.setIcon(wt_icon)
        self.quitAction.triggered.connect(self.quit)
        self.librarian.aboutQtAction.triggered.connect(lambda: QtGui.QMessageBox.aboutQt(self.librarian, 'About Qt'))
        self.deviceAction = self.librarian.deviceAction
        self.deviceAction.triggered.connect(self.device_request)
        self.globalsAction = self.librarian.globalsAction
        self.globalsAction.triggered.connect(self.globals_request)
        self.updateCheckAction = self.librarian.updateCheckAction
        self.updateCheckAction.triggered.connect(lambda: self.update_check(silent=False))

        self.midi_duplex_state_change.connect(self.globalsAction.setEnabled)

        self.device_event.connect(lambda event: self.device_response(event, self.librarian))
        self.loader.loaded.connect(self.librarian.create_proxy)
        self.loading_win = LoadingWindow(self.librarian)
        self.librarian.shown.connect(self.loading_win.show)
        self.loading_win.shown.connect(self.loader_thread.start)
        self.loader.loaded.connect(self.loading_win.hide)
        self.loader.loaded.connect(self.librarian.cat_count_update)

        self.librarian.dump_request.connect(self.dump_request)
        self.librarian.midi_event.connect(self.output_event)
        self.librarian.program_change_request.connect(self.program_change_request)

        self.about_win = AboutDialog(self.librarian)
        self.aboutAction = self.librarian.aboutAction
        self.aboutAction.triggered.connect(self.about_win.show)

        #DUMPING
        self.dump_bulk = False
        self.dump_bulk_count = 0
        self.dump_bulk_timer = QtCore.QTimer()
        self.dump_bulk_timer.setInterval(500)
        self.dump_bulk_timer.setSingleShot(True)

        self.dump_timer = QtCore.QTimer()
        self.dump_timer.setInterval(100)
        self.dump_timer.setSingleShot(True)

        self.dump_active = False
        self.dump_pause = False
        self.dump_temp = []
        self.dump_elapsed = QtCore.QElapsedTimer()
        self.dump_win = DumpWin(self.librarian)
        self.dump_bulk_timer.timeout.connect(self.dump_win.accept)
        self.dump_bulk_timer.timeout.connect(lambda: self.blofeld_library.addSoundBulk(self.dump_temp))
        self.dump_bulk_timer.timeout.connect(lambda: setattr(self, 'dump_bulk', False))
        self.dump_bulk_timer.timeout.connect(lambda: setattr(self, 'dump_bulk_count', 0))
        self.dump_win.resume.connect(lambda: setattr(self, 'dump_pause', False))
        self.dump_win.resume.connect(self.dump_timer.start)
        self.dump_win.pause.connect(self.dump_timer.stop)
        self.dump_win.pause.connect(lambda: setattr(self, 'dump_pause', True))
        self.dump_win.accepted.connect(lambda: self.blofeld_library.addSoundBulk(self.dump_temp))
        self.dump_win.accepted.connect(lambda: setattr(self, 'dump_active', False))
        self.dump_win.rejected.connect(lambda: setattr(self, 'dump_active', False))
        self.dump_win.rejected.connect(self.dump_timer.stop)

        self.dump_send_win = DumpWin(self.librarian)
        self.dump_send_timer = QtCore.QTimer()
        self.dump_send_timer.setInterval(200)
        self.dump_send_win.resume.connect(self.dump_send_timer.start)
        self.dump_send_win.pause.connect(self.dump_send_timer.stop)
        self.dump_send_win.accepted.connect(self.dump_send_timer.stop)
        self.dump_send_win.accepted.connect(self.dump_send_timer.timeout.disconnect)
        self.dump_send_win.rejected.connect(self.dump_send_timer.stop)
        self.dump_send_win.rejected.connect(self.dump_send_timer.timeout.disconnect)

        #EDITOR
        self.editor = Editor(self)
        if self.editor_appearance_efx_arp & 1:
            self.editor.efx_arp_toggle_btn.clicked.emit(1)
        self.editor.efx_arp_toggle_state.connect(lambda state: setattr(self, 'editor_appearance_efx_arp', 2|state) if self.editor_appearance_efx_arp&2 else None)
        if self.editor_appearance_filter_matrix & 1:
            self.editor.filter_matrix_toggle_btn.clicked.emit(1)
        self.editor.filter_matrix_toggle_state.connect(lambda state: setattr(self, 'editor_appearance_filter_matrix', 2|state) if self.editor_appearance_filter_matrix&2 else None)


        self.editor_dump_state = False
        self.editor_dump_timer = QtCore.QTimer()
        self.editor_dump_timer.setSingleShot(True)
        self.editor_dump_timer.setInterval(200)
        self.editor_dump_timer.timeout.connect(lambda: setattr(self, 'editor_dump_state', False))
        self.editor.dump_request.connect(self.dump_request)
        self.editor.dump_request.connect(lambda data: [setattr(self, 'editor_dump_state', True), self.editor_dump_timer.start()])

        self.editor.dump_send.connect(self.dump_send)

        self.editor.pgm_receive_btn.blockSignals(True)
        self.editor.pgm_receive_btn.setChecked(self.editor_remember_states[PGMRECEIVE])
        self.editor.pgm_receive_btn.blockSignals(False)
        self.editor.midi_receive_btn.blockSignals(True)
        self.editor.midi_receive_btn.setChecked(self.editor_remember_states[MIDIRECEIVE])
        self.editor.midi_receive_btn.blockSignals(False)

        self.editor.pgm_send_btn.blockSignals(True)
        self.editor.pgm_send_btn.setChecked(self.editor_remember_states[PGMSEND])
        self.editor.pgm_send_btn.blockSignals(False)

        midi_send = self.editor_remember_states[MIDISEND]
        self.editor.midi_send_btn.blockSignals(True)
        self.editor.midi_send_btn.setChecked(midi_send)
        self.editor.send = midi_send
        self.editor.midi_send_btn.blockSignals(False)
        self.editor.autosave_btn.setChecked(self.editor_autosave & 1)
        self.editor.save = self.editor_autosave & 1

        self.librarian.activate_editor.connect(self.activate_editor)
        self.librarian.editorAction.triggered.connect(lambda: [self.editor.show(), self.editor.activateWindow()])
        self.program_change_received.connect(self.editor.program_change_received)
        self.editor.show_librarian.connect(lambda: [self.librarian.show(), self.librarian.activateWindow()])
        self.editor.midi_event.connect(self.output_event)
        self.editor.program_change_request.connect(self.program_change_request)
        self.editor.pgm_receive.connect(lambda state: self.set_editor_remember(PGMRECEIVE, state))
        self.editor.midi_receive.connect(lambda state: self.set_editor_remember(MIDIRECEIVE, state))
        self.editor.pgm_send.connect(lambda state: self.set_editor_remember(PGMSEND, state))
        self.editor.midi_send.connect(lambda state: self.set_editor_remember(MIDISEND, state))
        self.parameter_change_received.connect(self.editor.receive_value)
        self.output_conn_state_change.connect(self.editor.midi_output_state)
        self.input_conn_state_change.connect(self.editor.midi_input_state)

        self.dump_dialog = SoundDumpDialog(self, self.librarian)

        self.globals = Globals(self, self.librarian)
        self.globals.midi_event.connect(self.output_event)
        self.globals_event.connect(self.activate_globals)
        self.globals.buttonBox.button(QtGui.QDialogButtonBox.Reset).clicked.connect(self.globals_request)

        self.librarian.show()

        self.midiwidget = MidiWidget(self)
        self.mididialog = MidiDialog(self, self.editor)
        self.editor.show_midi_dialog.connect(self.mididialog.show)

        self.settings_dialog = SettingsDialog(self, self.librarian)
        self.settingsAction.triggered.connect(self.show_settings)
        self.editor.filter_matrix_toggle_state.connect(lambda state: setattr(self, 'editor_appearance_filter_matrix_latest', state))
        self.editor.efx_arp_toggle_state.connect(lambda state: setattr(self, 'editor_appearance_efx_arp_latest', state))

        #SUMMARY
        self.summary = SummaryDialog(self, self.librarian)
        self.summary.dump_send.connect(self.dump_send)
        self.librarian.summary_request.connect(self.summary.setSound)

        #MIDI IMPORT
        self.midi_import = MidiImportDialog(self, self.librarian)
        self.midi_import.dump_send.connect(self.dump_send)
        self.output_conn_state_change.connect(self.midi_import.midi_output_state)

        #WAVE IMPORT
        self.wave_import = WaveLoad(self)

        #WAVETABLE
        self.wavetable_list_window = WavetableListWindow(self)
#        self.wavetable_list_window.show()
        self.wavetable_windows_list = []
        self.librarian.wavetableAction.triggered.connect(lambda _: self.wavetable_show())

        self.midi_connect()

        if args.wavetable:
            if args.wavetable is True:
                self.wavetable_show()
        if args.editor:
            self.startup_show_editor(args.editor)

        self.version_request_dialog = VersionRequestDialog(self.librarian)
        self.updated_dialog = UpdatedDialog(self, self.librarian)
        self.updated_dialog.never_chk.toggled.connect(lambda state: self.settings.gGeneral.set_StartupUpdateCheck(not state))
        self.create_version_request()
        if self.startup_version_check:
            self.update_check(silent=True)
#        QtGui.QMessageBox.information(self.librarian, 'Test build', 'This is a test build!!! Have fun!')

    def wavetable_show(self, uid=None):
        if not self.wavetable_windows_list:
            self.new_wavetable(uid)
        else:
            if uid is not None:
                for window in self.wavetable_windows_list:
                    if window.wavetable_uid == uid:
                        break
                else:
                    self.new_wavetable(uid)
                    return
            else:
                window = self.wavetable_windows_list[-1]
            window.show()
            window.activateWindow()

    def new_wavetable(self, uid=None, wavetable_data=None):
        wavetable_window = WaveTableEditor(self, uid=uid, wavetable_data=wavetable_data)
        self.wavetable_windows_list.append(wavetable_window)
        wavetable_window.wavetable_send.connect(self.wavetable_send)
        self.output_conn_state_change.connect(wavetable_window.midi_output_state)
        wavetable_window.show()
        wavetable_window.activateWindow()
        wavetable_window.newWavetableAction.triggered.connect(lambda _: self.new_wavetable())
        return wavetable_window

    def startup_show_editor(self, data):
        def show_editor():
            self.loader.loaded.disconnect(show_editor)
            self.activate_editor(*sound)
        self.loader.loaded.connect(show_editor)
        if isinstance(data, bool):
            sound = None, None
        else:
            valid = re.compile(r'^([a-zA-Z])([0-9]{1,3})$')
            res = valid.match(data)
            if not res:
                sound = None, None
            else:
                bank = uppercase.index(res.groups()[0].upper())
                prog = int(res.groups()[1]) - 1
                if prog < 0:
                    prog = 0
                elif prog > 127:
                    prog = 127
                sound = bank, prog

    def create_version_request(self, silent=True):
        self.version_request = VersionRequest(self)
        self.version_thread = QtCore.QThread()
        self.version_request.moveToThread(self.version_thread)
        self.version_thread.started.connect(self.version_request.run)
        self.version_request.done.connect(self.version_thread.quit)
        self.version_request.done.connect(self.version_request_dialog.hide)
        self.version_request.error.connect(self.version_request_dialog.hide)
        self.version_request_dialog.rejected.connect(self.version_request.stop)

    def update_check(self, silent=False):
        if not self.version_thread.isRunning():
            if self.version_thread.isFinished():
                self.create_version_request(silent)
            self.version_thread.start()
        try:
            self.version_request.updated.disconnect()
        except:
            pass
        if not silent:
            self.version_request_dialog.show()
            self.version_request.setSilent(False)
            self.version_request.updated.connect(lambda updated, content: self.updated_dialog.exec_(content))
            self.updated_dialog.never_chk.setVisible(False)
        else:
            self.version_request.updated.connect(lambda updated, content: self.updated_dialog.exec_(content) if updated else None)

    def show_settings(self):
        self.settings_dialog.exec_()

    def file_import(self, trigger, mode=ALLFILE):
        dialog = FileOpen(mode)
        res = dialog.exec_()
        if not res: return
        if isinstance(dialog.res[0], Sound):
            self.summary.setSound(*res)
        elif isinstance(dialog.res[0], Wavetable):
            wavetable = dialog.res[0]
            name = wavetable.name
            if self.wavetable_library.nameExists(wavetable.name):
                pos = 1
                index = 0
                while True:
                    last = name[-pos]
                    if not last.isdigit():
                        name = name[:-pos] + str(index)
                        if not self.wavetable_library.nameExists(name):
                            break
                        if index == 9:
                            pos += 1
                        index += 1
                    else:
                        old_index = int(last)
                        if old_index == 9:
                            pos += 1
                        index = old_index + 1
                        name = name[:-pos] + str(index)
                        if not self.wavetable_library.nameExists(name):
                            break
            uid = str(uuid4())
            self.wavetable_library[uid] = wavetable.values, wavetable.slot, QtCore.QString(name)
            self.new_wavetable(uid)
        else:
            self.midi_import.setSource(*res)

    def save_library(self):
        data = []
        for bank in self.blofeld_library.data:
            for sound in bank:
                data.append((sound.bank, sound.prog) + tuple(sound.data))
        data_dir = str(QtGui.QDesktopServices.storageLocation(QtGui.QDesktopServices.DataLocation).toUtf8())
        data_path = path.join(data_dir, 'personal_library')
        if not path.exists(data_path):
            try:
                makedirs(data_dir)
            except:
                pass
        with open(data_path, 'wb') as of:
            pickle.dump(tuple(data), of)

    @property
    def blofeld_id(self):
        try:
            return self._blofeld_id
        except:
            self._blofeld_id = self.settings.gMIDI.get_Blofeld_ID(0x7f, True)
            return self._blofeld_id

    @blofeld_id.setter
    def blofeld_id(self, value):
        self.settings.gMIDI.set_Blofeld_ID(value)
        self._blofeld_id = value

    @property
    def source_library(self):
        return self.settings.gGeneral.get_Source_Library('personal')

    @property
    def startup_version_check(self):
        try:
            return self._startup_version_check
        except:
            self._startup_version_check = self.settings.gGeneral.get_StartupUpdateCheck(True)
            return self._startup_version_check

    @startup_version_check.setter
    def startup_version_check(self, value):
        self.settings.gGeneral.set_StartupUpdateCheck(value)
        self._startup_version_check = value

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
#            if self.backend == RTMIDI:
#                self._autoconnect = self.settings.gMIDI.get_Autoconnect({INPUT: fakeSet(), OUTPUT: fakeSet()}, True)
#            else:
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
    def editor_autosave(self):
        try:
            return self._editor_autosave
        except:
            self._editor_autosave = self.settings.gEditor.get_Autosave(3, True)
            return self._editor_autosave

    @editor_autosave.setter
    def editor_autosave(self, value):
        self.settings.gEditor.set_Autosave(value)
        self._editor_autosave = value

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
    def editor_appearance_efx_arp(self):
        try:
            return self._editor_appearance_efx_arp
        except:
            self._editor_appearance_efx_arp = self.settings.gEditor.get_Remember_Appearance_EfxArp(2, True)
            return self._editor_appearance_efx_arp

    @editor_appearance_efx_arp.setter
    def editor_appearance_efx_arp(self, value):
        self._editor_appearance_efx_arp = self.settings.gEditor.set_Remember_Appearance_EfxArp(value)
        self._editor_appearance_efx_arp = value

    @property
    def editor_appearance_filter_matrix(self):
        try:
            return self._editor_appearance_filter_matrix
        except:
            self._editor_appearance_filter_matrix = self.settings.gEditor.get_Remember_Appearance_FilterMatrix(2, True)
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
            self.duplex_state_check(INPUT, len(conn_list))
            if self.remember_connections and not conn.hidden:
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
            self.duplex_state_check(OUTPUT, len(conn_list))
            if self.remember_connections and not conn.hidden:
                port_fmt = '{}:{}'.format(conn.dest.client.name, conn.dest.name)
                if port_fmt == 'Blofeld:Blofeld MIDI 1': return
                if state:
                    self.autoconnect[OUTPUT] = self.autoconnect[OUTPUT] | set([port_fmt])
                else:
                    self.autoconnect[OUTPUT].discard(port_fmt)
                self.settings.gMIDI.set_Autoconnect(self.autoconnect)

    def duplex_state_check(self, dir, conn):
        self.connections[dir] = conn
        duplex_state = all(self.connections)
        if self.midi_duplex_state != duplex_state:
            self.midi_duplex_state_change.emit(duplex_state)
            self.midi_duplex_state = duplex_state

    def midi_connect(self):
        if not (self.blofeld_autoconnect or self.remember_connections): return
        for cid, client in self.graph.client_id_dict.items():
            if self.blofeld_autoconnect:
                if self.backend == RTMIDI:
                    if sys.platform == 'win32':
                        if client.name.startswith('Waldorf Blofeld '):
                            blofeld_port = self.graph.port_id_dict[cid][0]
                            if blofeld_port.is_input:
                                self.output.connect(blofeld_port)
                            else:
                                blofeld_port.connect(self.input)
                            continue
                    else:
                        if client.name.startswith('Blofeld:Blofeld MIDI '):
                            blofeld_port = self.graph.port_id_dict[cid][0]
                            if blofeld_port.is_input:
                                self.output.connect(blofeld_port)
                            else:
                                blofeld_port.connect(self.input)
                            continue
                elif client.name == 'Blofeld' and len(client.ports) == 1 and client.ports[0].name.startswith('Blofeld MIDI 1'):
                    self.graph.port_id_dict[cid][0].connect(self.seq.client_id, self.input.id)
#                    self.graph.port_id_dict[self.seq.client_id][self.output.id].connect(cid, 0)
                    self.output.connect(cid, 0)
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
        if self.debug_sysex and event.type == SYSEX:
            print event.sysex
        if self.backend == ALSA:
            alsa_event = event.get_event()
            alsa_event.source = self.output.client.id, self.output.id
            self.seq.output_event(alsa_event)
            self.seq.drain_output()
        else:
            rtmidi_event = event.get_binary()
            for port in self.seq.ports[OUTPUT]:
                port.send_message(rtmidi_event)

    def midi_event_received(self, event):
        if event.type == SYSEX:
#            print 'receiving event: {}'.format(len(event.sysex))
#            print event.sysex
            sysex_type = event.sysex[4]
            if sysex_type == SNDD:
                self.sound_dump_received(Sound(event.sysex[5:390], SRC_BLOFELD))
            elif sysex_type == SNDP:
                self.sysex_parameter(event.sysex[5:])
            elif sysex_type == GLBD:
                self.globals_event.emit(event.sysex)
#                self.main.globals.setData(event.sysex)
            elif len(event.sysex) == 15 and event.sysex[3:5] == [6, 2]:
                self.device_event.emit(event.sysex)
        elif event.type == CTRL:
            if event.data1 == 0:
                self.blofeld_current[0] = event.data2
            else:
                self.ctrl_parameter(event.data1, event.data2)
        elif event.type == PROGRAM:
            self.blofeld_current[1] = event.data2
            if None in self.blofeld_current: return
            self.librarian.blofeld_sounds_table.selectRow(self.librarian.blofeld_model_proxy.mapFromSource(self.blofeld_model.index(self.blofeld_current[0]*128+self.blofeld_current[1], 0)).row())
            self.program_change_received.emit(*self.blofeld_current)

    def sysex_parameter(self, data):
        location = data[0]
        index = data[1]*128+data[2]
        value = data[3]
        self.parameter_change_received.emit(location, index, value)

    def ctrl_parameter(self, param_id, value):
        if param_id in ctrl2sysex:
            self.parameter_change_received.emit(0, ctrl2sysex[param_id], value)

    def activate_editor(self, bank, prog):
        self.editor.show()
        self.editor.setSound(bank, prog)
        self.editor.activateWindow()

    def activate_globals(self, data):
        if self.midi_lock_status: return
        self.globals.setData(data)

    def sound_dump_received(self, sound):
        if sound.bank > 25:
            if self.editor_dump_state == True:
                self.editor.setSoundDump(sound)
                self.editor.show()
                self.editor.activateWindow()
                return
            res = self.dump_dialog.exec_(sound)
            if not res or not any(res): return
            editor, library = res
            if not library:
                self.editor.setSoundDump(sound)
                self.editor.show()
                self.editor.activateWindow()
            else:
                sound._bank, sound._prog = library
                self.blofeld_library.addSound(sound)
                if editor:
                    self.activate_editor(library)
            return
        bank = sound.bank
        prog = sound.prog

        if self.dump_bulk:
            self.dump_temp.append(sound)
            self.dump_bulk_count += 1
            dump_all = self.dump_bulk_count/128
            self.dump_bulk_timer.stop()
            self.dump_bulk_timer.start()
            self.dump_win.bank_lbl.setText('{}{}'.format(uppercase[bank], ' {}/8'.format(bank+1) if dump_all else ''))
            self.dump_win.sound_lbl.setText('{:03}/{}'.format(prog+1+(128*bank if dump_all else 0), 1024 if dump_all else 128))
            dump_time = None
            if dump_all:
                self.dump_win.progress.setMaximum(1024)
                self.dump_win.progress.setValue(prog+1+(128*bank))
                if not (bank == 0 and prog < 10):
                    dump_time = self.dump_elapsed.elapsed()/float(prog+1+128*bank)*(1024-prog-128*bank)/1000
            else:
                self.dump_win.progress.setValue(prog+1)
                if prog > 5:
                    dump_time = self.dump_elapsed.elapsed()/float(prog+1)*(128-prog)/1000
            if dump_time is not None:
                self.dump_win.time.setText('{}:{:02}'.format(*divmod(int(dump_time)+1, 60)))
            return
        if not self.dump_active:
            if not self.dump_bulk_timer.isActive():
                self.dump_bulk_timer.start()
            else:
                self.dump_bulk = True
                self.dump_bulk_count += 1
                self.dump_temp = []
                self.dump_bulk_timer.stop()
                self.dump_bulk_timer.start()
                self.dump_elapsed.start()
                self.dump_win.showDisabled()
            self.blofeld_library.addSound(sound)
            if self.editor_dump_state == True and (sound.bank, sound.prog) == (self.editor.sound.bank, self.editor.sound.prog):
                self.editor.setSoundDump(sound)
#            self.cat_count_update()
#            self.blofeld_sounds_table.resizeColumnToContents(2)
#            self.blofeld_sounds_table.resizeColumnToContents(5)
            return
        self.dump_temp.append(sound)
        dump_all = True if self.dump_mode == DUMP_ALL else False
        if prog >= 127:
            if dump_all:
                bank += 1
                if bank >= 8:
                    self.dump_active = False
                    self.blofeld_library.addSoundBulk(self.dump_temp)
                    self.dump_win.accept()
#                    self.cat_count_update()
#                    self.blofeld_sounds_table.resizeColumnToContents(2)
#                    self.blofeld_sounds_table.resizeColumnToContents(5)
                    return
                prog = -1
            else:
                self.dump_active = False
                self.blofeld_library.addSoundBulk(self.dump_temp)
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
        try:
            self.dump_timer.timeout.disconnect()
        except:
            pass
        self.dump_timer.timeout.connect(lambda: self.sound_request(bank, prog+1))
        if not self.dump_pause:
            self.dump_timer.start()


    def dump_request(self, req):
        if isinstance(req, tuple):
            self.sound_request(*req)
            return
        self.dump_active = True
        self.dump_pause = False
        self.dump_mode = req
        self.dump_temp = []
        self.dump_elapsed.start()
        self.dump_win.show()
        self.dump_win.paused = False
        if req == DUMP_ALL:
            bank = 0
            self.dump_win.progress.setMaximum(1024)
        else:
            bank = req
            self.dump_win.progress.setMaximum(128)
        self.sound_request(bank, 0)

    def dump_send(self, sound, bank=None, prog=None):
        data = sound.data
        if bank is None:
            bank = sound.bank
            prog = sound.prog
        self.output_event(SysExEvent(1, [INIT, IDW, IDE, self.blofeld_id, SNDD, bank, prog] + data + [CHK, END]))

    def wavetable_send(self, sysex):
        self.output_event(SysExEvent(1, sysex))
    
    def dump_bulk_send(self, first, last):
        def consume():
            if not dump_bulk_list:
                self.dump_send_win.accept()
                return
            sound = dump_bulk_list.pop(0)
            self.dump_send(sound)
            current = tot_sounds-len(dump_bulk_list)
            self.dump_send_win.bank_lbl.setText('{} {}/{}'.format(uppercase[sound.bank], tot_banks-last[0]+sound.bank, tot_banks))
            self.dump_send_win.sound_lbl.setText('{:03} {}/{}'.format(sound.prog+1, current, tot_sounds))
            self.dump_send_win.progress.setValue(current)
            dump_time = None
            if (tot_sounds > 100 and current > 10) or (tot_sounds <= 100 and current > 5):
                dump_time = self.dump_elapsed.elapsed()/float(current)*(len(dump_bulk_list))/1000
            if dump_time is not None:
                self.dump_send_win.time.setText('{}:{:02}'.format(*divmod(int(dump_time)+1, 60)))
        bank, prog = first
        tot_banks = last[0]-bank+1
        _last = (last[0], last[1]+1) if last[1]+1 <= 127 else (last[0]+1, 0)
        dump_bulk_list = []
        while (bank, prog) != _last:
            dump_bulk_list.append(self.blofeld_library[bank, prog])
            prog += 1
            if prog > 127:
                bank += 1
                if bank > self.blofeld_library.banks: break
                prog = 0
        tot_sounds = len(dump_bulk_list)
        self.dump_send_win.progress.setMaximum(tot_sounds)
        self.dump_send_win.show()
        self.dump_send_timer.timeout.connect(consume)
        self.dump_send(dump_bulk_list.pop(0))
        self.dump_send_timer.start()
        self.dump_elapsed.start()

    def external_dump_bulk_send(self, sound_list):
        def consume():
            if not sound_list:
                self.dump_send_win.accept()
                return
            sound = sound_list.pop(0)
            self.dump_send(sound)
            current = tot_sounds-len(sound_list)
            self.dump_send_win.bank_lbl.setText('{} {}/{}'.format(uppercase[sound.bank], tot_banks-last[0]+sound.bank, tot_banks))
            self.dump_send_win.sound_lbl.setText('{:03} {}/{}'.format(sound.prog+1, current, tot_sounds))
            self.dump_send_win.progress.setValue(current)
            dump_time = None
            if (tot_sounds > 100 and current > 10) or (tot_sounds <= 100 and current > 5):
                dump_time = self.dump_elapsed.elapsed()/float(current)*(len(sound_list))/1000
            if dump_time is not None:
                self.dump_send_win.time.setText('{}:{:02}'.format(*divmod(int(dump_time)+1, 60)))
        tot_banks = len(set([s.bank for s in sound_list]))
        tot_sounds = len(sound_list)
        self.dump_send_win.progress.setMaximum(tot_sounds)
        self.dump_send_win.show()
        self.dump_send_timer.timeout.connect(consume)
        self.dump_send(sound_list.pop(0))
        self.dump_send_timer.start()
        self.dump_elapsed.start()

    def sound_request(self, bank, sound):
        self.output_event(SysExEvent(1, [INIT, IDW, IDE, self.blofeld_id, SNDR, bank, sound, CHK, END]))

    def device_request(self):
        self.output_event(SysExEvent(1, [INIT, 0x7e, 0x7f, 0x6, 0x1, END]))

    def globals_request(self):
        self.output_event(SysExEvent(1, [INIT, IDW, IDE, BROADCAST, GLBR, END]))

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

    def closeDetect(self, win=None):
        if win:
            win_list = set((self.librarian, self.editor) + tuple(self.wavetable_windows_list))
            win_list.discard(win)
            if any(win.isVisible() for win in win_list):
                return True
            if not self.library_changed():
                return True
        msgbox = QtGui.QMessageBox(
                                   QtGui.QMessageBox.Question, 
                                   'Confirm exit', 'The library has been modified, do you want to quit anyway?', 
                                   QtGui.QMessageBox.Abort|QtGui.QMessageBox.Save|QtGui.QMessageBox.Cancel, 
                                   self.librarian
                                   )
        buttonBox = msgbox.findChild(QtGui.QDialogButtonBox)
        abort_btn = buttonBox.button(QtGui.QDialogButtonBox.Abort)
        abort_btn.setText('Ignore and quit')
        abort_btn.setIcon(QtGui.QIcon.fromTheme('application-exit'))
        res = msgbox.exec_()
        if res == QtGui.QMessageBox.Cancel:
            return False
        elif res == QtGui.QMessageBox.Abort:
            return True
        self.save_library()
        return True

    def library_changed(self):
        index_list = self.blofeld_model.match(self.blofeld_model.index(0, STATUS), EditedRole, QtCore.QVariant(STORED), hits=-1)
        if len(index_list) == self.blofeld_model.rowCount():
            return False
        return True

    def quit(self):
        if not self.closeDetect(): return
        self.app.quit()


class Librarian(QtGui.QMainWindow):
    shown = QtCore.pyqtSignal()
    program_change_request = QtCore.pyqtSignal(int, int)
    dump_request = QtCore.pyqtSignal(object)
    dump_bulk_send = QtCore.pyqtSignal(object, object)
    dump_send = QtCore.pyqtSignal(object)
    midi_event = QtCore.pyqtSignal(object)
    activate_editor = QtCore.pyqtSignal(int, int)
    summary_request = QtCore.pyqtSignal(object)

    def __init__(self, main):
        QtGui.QMainWindow.__init__(self, parent=None)
        load_ui(self, 'main.ui')
        self.setContentsMargins(2, 2, 2, 2)

        self.main = main

        self.blofeld_model = self.main.blofeld_model
        self.blofeld_library = self.main.blofeld_library
        self.blofeld_current = self.main.blofeld_current
        self.blofeld_model.itemChanged.connect(self.sound_update)

        self.loading_complete = False
        self.edit_mode = False

        self.bank_dump_combo.addItems(['All']+[l for l in uppercase[:8]])
        self.sound_dump_combo.addItems(['All']+[str(s) for s in range(1, 129)])
        self.bank_filter_combo.addItems(['All']+[l for l in uppercase[:8]])
        self.cat_filter_combo.addItem('All')
        for cat in categories:
            self.cat_filter_combo.addItem(cat, cat)
        self.bank_filter_combo.currentIndexChanged.connect(lambda index: self.blofeld_model_proxy.setMultiFilter(BANK, index))
        self.bank_filter_combo.currentIndexChanged.connect(self.cat_count_update)
        self.cat_filter_combo.currentIndexChanged.connect(lambda index: self.blofeld_model_proxy.setMultiFilter(CATEGORY, index))

        self.print_win = PrintDialog(main, self)
        self.textExportAction.triggered.connect(self.print_win.exec_)

        self.dump_btn.clicked.connect(self.dump_request_create)
        self.bank_dump_combo.currentIndexChanged.connect(lambda b: self.sound_dump_combo.setEnabled(True if b != 0 else False))
        self.edit_btn.toggled.connect(self.edit_mode_set)
        self.search_edit.textChanged.connect(self.search_filter)
        self.search_clear_btn.setIcon(self.style().standardIcon(QtGui.QStyle.SP_DialogResetButton))
        self.search_clear_btn.clicked.connect(lambda _: self.search_edit.setText(''))
        self.search_filter_chk.toggled.connect(self.search_filter_set)
        self.blofeld_sounds_table.doubleClicked.connect(self.sound_doubleclick)
        self.blofeld_sounds_table.keyPressEvent = self.table_key_press
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

#    def closeEvent(self, event):
#        if self.main.closeDetect(self):
#            event.accept()
#        else:
#            event.ignore()

    def eventFilter(self, source, event):
        if event.type() == QtCore.QEvent.KeyPress:
            if event.key() == QtCore.Qt.Key_F5:
                self.dump_request_create()
            elif event.key() == QtCore.Qt.Key_Escape and source == self.search_edit:
                self.search_edit.setText('')
        if source == self.search_filter_chk and event.type() == QtCore.QEvent.FocusIn and event.reason() == QtCore.Qt.OtherFocusReason:
            self.search_edit.setFocus()
        return QtGui.QMainWindow.eventFilter(self, source, event)


    def edit_mode_set(self, state):
        self.edit_mode = state
        if state:
            self.blofeld_sounds_table.setEditTriggers(QtGui.QTableView.DoubleClicked|QtGui.QTableView.EditKeyPressed)
            self.blofeld_sounds_table.setDragEnabled(False)
            self.blofeld_sounds_table.setSelectionMode(QtGui.QTableView.SingleSelection)
        else:
            self.blofeld_sounds_table.setEditTriggers(QtGui.QTableView.NoEditTriggers)
            self.blofeld_sounds_table.setDragEnabled(True)
            self.blofeld_sounds_table.setSelectionMode(QtGui.QTableView.ContiguousSelection)

    def search_filter_set(self, state):
        if not state:
            self.blofeld_model_proxy.setTextFilter('')
        self.search_filter(self.search_edit.text())
        return

    def search_filter(self, text):
        filter =  self.search_filter_chk.isChecked()
        if not text and not filter: return
        if not filter:
            found = self.blofeld_model.findItems(text, QtCore.Qt.MatchContains, NAME)
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
            self.program_change_request.emit(sound.bank, sound.prog)
        elif behaviour == 2:
            self.activate_editor.emit(sound.bank, sound.prog)
        else:
            self.program_change_request.emit(sound.bank, sound.prog)
            self.activate_editor.emit(sound.bank, sound.prog)

    def table_key_press(self, event):
        if event.key() == QtCore.Qt.Key_Home:
            self.blofeld_sounds_table.selectRow(0)
        elif event.key() == QtCore.Qt.Key_End:
            self.blofeld_sounds_table.selectRow(self.blofeld_model_proxy.rowCount()-1)
        else:
            QtGui.QTableView.keyPressEvent(self.blofeld_sounds_table, event)

    def right_click(self, event):
        if event.button() != QtCore.Qt.RightButton: return
        rows = set([self.blofeld_model_proxy.mapToSource(index).row() for index in self.blofeld_sounds_table.selectedIndexes()])
        index = self.blofeld_sounds_table.indexAt(event.pos())
        sound = self.blofeld_model.item(self.blofeld_model_proxy.mapToSource(index).row(), SOUND).data(SoundRole).toPyObject()
        menu = QtGui.QMenu()
        menu.setSeparatorsCollapsible(False)
        header = QtGui.QAction(sound.name, menu)
        header.setSeparator(True)
        menu.addAction(header)
        edit_item = QtGui.QAction('Edit...', menu)
        summary_item = QtGui.QAction('Show summary', menu)
        sep = QtGui.QAction(menu)
        sep.setSeparator(True)
        dump_request_item = QtGui.QAction('Request dump', menu)
        dump_send_item = QtGui.QAction('Dump to Blofeld', menu)
        menu.addActions([edit_item, summary_item, sep, dump_request_item, dump_send_item])
        if len(rows) > 1:
            dump_bulk_send_item = QtGui.QAction('Dump selected sounds', menu)
            menu.addAction(dump_bulk_send_item)
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
        if not res: return
        elif res == edit_item:
            self.activate_editor.emit(sound.bank, sound.prog)
        elif res == summary_item:
            self.summary_request.emit(sound)
        elif res == dump_request_item:
            self.dump_request.emit((sound.bank, sound.prog))
        elif res == dump_send_item:
            res = QtGui.QMessageBox.question(self, 'Dump selected sound',
                                             'You are going to send a sound dump to the Blofeld at location "{}{:03}".\nThis action cannot be undone. Do you want to proceed?'.format(uppercase[sound.bank], sound.prog+1), 
                                             QtGui.QMessageBox.Ok|QtGui.QMessageBox.Cancel
                                             )
            if not res == QtGui.QMessageBox.Ok: return
            self.dump_send.emit(sound)
        elif rows > 1 and res == dump_bulk_send_item:
            first = self.blofeld_model.item(min(rows), SOUND).data(SoundRole).toPyObject()
            last = self.blofeld_model.item(max(rows), SOUND).data(SoundRole).toPyObject()
            res = QtGui.QMessageBox.question(self, 'Dump selected sounds',
                                             'You are going to send a sound dump to the Blofeld for locations "{}{:03}" through "{}{:03}".\nThis action cannot be undone. Do you want to proceed?'.format(uppercase[first.bank], first.prog+1, uppercase[last.bank], last.prog+1), 
                                             QtGui.QMessageBox.Ok|QtGui.QMessageBox.Cancel
                                             )
            if not res == QtGui.QMessageBox.Ok: return
            self.dump_bulk_send.emit((first.bank, first.prog), (last.bank, last.prog))

    def sound_drop_event(self, event):
        def rename(sound_range):
            first = min(sound_range)
            last = max(sound_range)
            for row in range(first, last+1):
                bank, prog = divmod(row, 128)
                self.blofeld_model.item(row, BANK).setText(uppercase[bank])
                self.blofeld_model.item(row, PROG).setText('{:03}'.format(prog+1))
                sound = self.blofeld_model.item(row, SOUND).data(SoundRole).toPyObject()
                sound.bank = bank
                sound.prog = prog
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
            self.blofeld_library.swap((source, ), target)
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
                items = self.blofeld_model.takeRow(first if not before else first+d)
                self.blofeld_model.insertRow(target if not before else target+d, items)
            rename((target, )+tuple(rows))
            self.blofeld_library.swap(rows, target)

#        self.blofeld_model.sort(2)
#        self.blofeld_model.sort(1)


    def sound_update(self, item, _=None):
        if item.column() == STATUS:
            status = item.data(EditedRole).toPyObject()
            item.setText(get_status(status))
            setBold(item, True if status!=STORED else False)
#        elif item.column() == NAME:
#            sound = self.blofeld_model.item(item.row(), SOUND).data(SoundRole).toPyObject()
#            sound.name = item.text()

    def dump_request_create(self):
        bank = self.bank_dump_combo.currentIndex()
        sound = self.sound_dump_combo.currentIndex()
        if bank != 0 and sound != 0:
            self.dump_request.emit((bank-1, sound-1))
        elif bank != 0 and sound == 0:
            self.dump_request.emit(bank-1)
        else:
            self.dump_request.emit(DUMP_ALL)
        

    def create_proxy(self):
        self.loading_complete = True
        self.blofeld_model_proxy = LibraryProxy()
        self.blofeld_model_proxy.setSourceModel(self.blofeld_model)
        self.blofeld_sounds_table.setModel(self.blofeld_model_proxy)
        self.blofeld_sounds_table.horizontalHeader().setResizeMode(QtGui.QHeaderView.ResizeToContents)
        self.blofeld_sounds_table.horizontalHeader().setResizeMode(NAME, QtGui.QHeaderView.Stretch)
        self.blofeld_sounds_table.verticalHeader().setResizeMode(QtGui.QHeaderView.ResizeToContents)
        self.blofeld_sounds_table.setItemDelegateForColumn(CATEGORY, CategoryDelegate(self))
        self.blofeld_sounds_table.setItemDelegateForColumn(NAME, NameDelegate(self))
        self.blofeld_sounds_table.setColumnHidden(INDEX, True)
        for c in range(len(sound_headers), self.blofeld_model.columnCount()):
            self.blofeld_sounds_table.setColumnHidden(c, True)
        self.blofeld_sounds_table.horizontalHeader().setResizeMode(PROG, QtGui.QHeaderView.Fixed)
        self.blofeld_sounds_table.resizeColumnToContents(PROG)


    def cat_count_update(self):
        cat_len = [0 for cat_id in categories]
        current_bank = self.bank_filter_combo.currentIndex()
        for bank, sound_list in enumerate(self.blofeld_library.data):
            if current_bank != 0 and current_bank != bank+1: continue
            for s in sound_list:
                if not s: break
                if s.data is None: continue
                cat_len[s.cat] += 1
        for cat_id in range(1, self.cat_filter_combo.model().rowCount()):
            self.cat_filter_combo.setItemText(cat_id, '{} ({})'.format(
                                               self.cat_filter_combo.model().item(cat_id).data(QtCore.Qt.UserRole).toPyObject(),
                                               cat_len[cat_id-1]
                                               ))


def main():
    argv = sys.argv[:]
    argv[0] = 'Bigglesworth'
    app = QtGui.QApplication(argv)
    app.setOrganizationName('jidesk')
    app.setApplicationName('Bigglesworth')
    cursor_list.extend((QtCore.Qt.SizeAllCursor, UpCursorClass(), DownCursorClass(), LeftCursorClass(), RightCursorClass()))
    BigglesworthObject(app, args)
    sys.exit(app.exec_())
    print 'Blofix has been quit!'

if __name__ == '__main__':
    main()









