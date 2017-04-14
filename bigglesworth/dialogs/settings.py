# *-* coding: utf-8 *-*

from PyQt5 import QtCore, QtWidgets
from bigglesworth.utils import load_ui
from bigglesworth.const import PGMSEND, MIDISEND

class SettingsDialog(QtWidgets.QDialog):
    preset_texts = {
                    '201200': 'Latest official version', 
                    '200802': 'Same as January 2008, with slight modifications (mostly regarding Amp Volume)', 
                    '200801': 'Original sound set', 
                    'personal': '', 
                    }
    def __init__(self, main, parent):
        QtWidgets.QDialog.__init__(self, parent)
        load_ui(self, 'dialogs/settings.ui')
        self.main = main
        self.settings = main.settings
        self.setModal(True)

        self.preset_group.buttonClicked.connect(self.set_preset_labels)

        self.editor_appearance_filter_matrix_group.setId(self.adv_filter_radio, 0)
        self.editor_appearance_filter_matrix_group.setId(self.adv_matrix_radio, 1)
        self.editor_appearance_filter_matrix_group.setId(self.adv_last_radio, 2)
        self.editor_appearance_efx_arp_group.setId(self.arp_efx_radio, 0)
        self.editor_appearance_efx_arp_group.setId(self.arp_arp_radio, 1)
        self.editor_appearance_efx_arp_group.setId(self.arp_last_radio, 2)
        self.editor_appearance_efx_arp_group.buttonClicked.connect(self.editor_appearance_groups_check)
        self.editor_appearance_filter_matrix_group.buttonClicked.connect(self.editor_appearance_groups_check)
        self.editor_appearance_remember_last_chk.toggled.connect(self.editor_appearance_groups_check)
        self.editor_appearance_efx_arp_latest = self.editor_appearance_filter_matrix_latest = 0

        self.previous_id = 0
        self.deviceID_spin.valueChanged.connect(lambda value: self.deviceID_hex_lbl.setText('({:02X}h)'.format(value)))
        self.deviceID_spin.valueChanged.connect(self.check_broadcast)
        self.broadcast_chk.toggled.connect(self.set_broadcast)
        self.deviceID_detect_btn.clicked.connect(self.detect)
        self.main.midi_duplex_state_change.connect(self.deviceID_detect_btn.setEnabled)
        self.detect_msgbox = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Information, 'Detecting Device ID', 'Waiting for the Blofeld to reply, please wait...', QtWidgets.QMessageBox.Abort, self)

        self.detect_timer = QtCore.QTimer()
        self.detect_timer.setInterval(5000)
        self.detect_timer.setSingleShot(True)
        self.detect_timer.timeout.connect(self.no_response)

        self.no_response_msgbox = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Warning, 'No response', 'We got no response from the Blofeld.\nPlease check MIDI connections or try to switch it off and on again.', QtWidgets.QMessageBox.Ok, self)

    def editor_appearance_groups_check(self, btn):
        if all([self.adv_last_radio.isChecked(), self.arp_last_radio.isChecked()]):
            self.editor_appearance_remember_last_chk.setChecked(True)
        else:
            self.editor_appearance_remember_last_chk.setChecked(False)

    def set_preset_labels(self, btn):
        self.preset_desc_lbl.setText(self.preset_texts[str(btn.objectName())[7:-6]])

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
        self.previous_id = id
        if id == 127:
            self.broadcast_chk.setChecked(True)
            self.broadcast_chk.toggled.emit(True)
        else:
            self.deviceID_spin.setValue(id)

    def no_response(self):
        self.detect_msgbox.reject()
        self.no_response_msgbox.exec_()

    def set_broadcast(self, state):
        if state:
            self.previous_id = self.deviceID_spin.value()
            self.deviceID_spin.blockSignals(True)
            self.deviceID_spin.setValue(127)
            self.deviceID_hex_lbl.setText('({:02X}h)'.format(127))
            self.deviceID_spin.blockSignals(False)
        else:
            self.deviceID_spin.setValue(self.previous_id)

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
        #Library
        self.library_doubleclick_combo.setCurrentIndex(self.main.library_doubleclick)
        preset_btn = getattr(self, 'preset_{}_radio'.format(self.settings.gGeneral.get_Source_Library('personal')))
        preset_btn.setChecked(True)

        #Editor
        self.editor_appearance_filter_matrix_group.button(min(2, self.main.editor_appearance_filter_matrix)).click()
        self.editor_appearance_efx_arp_group.button(min(2, self.main.editor_appearance_efx_arp)).click()
        self.editor_pgm_send_combo.setCurrentIndex(self.main.editor_remember_states[PGMSEND])
        self.editor_midi_send_combo.setCurrentIndex(self.main.editor_remember_states[MIDISEND])
        self.editor_remember_chk.setChecked(self.main.editor_remember)

        #MIDI
        self.midi_groupbox.layout().addWidget(self.main.midiwidget)

        id = self.main.blofeld_id
        if id == 127:
            self.broadcast_chk.setChecked(True)
            self.broadcast_chk.toggled.emit(True)
        else:
            self.previous_id = id
            self.deviceID_spin.setValue(id)
            self.broadcast_chk.setChecked(False)
            self.broadcast_chk.toggled.emit(False)

        self.blofeld_autoconnect_chk.setChecked(self.main.blofeld_autoconnect)
        self.remember_connections_chk.setChecked(self.main.remember_connections)

        #EXEC
        res = QtWidgets.QDialog.exec_(self)
        if not res: return

        self.main.library_doubleclick = self.library_doubleclick_combo.currentIndex()
        self.settings.gGeneral.set_Source_Library(str(self.preset_group.checkedButton().objectName())[7:-6])


        if self.editor_appearance_filter_matrix_group.checkedId() > 1:
            if not self.main.editor_appearance_filter_matrix & 2:
                self.main.editor_appearance_filter_matrix = self.editor_appearance_filter_matrix_latest+2
        else:
            self.main.editor_appearance_filter_matrix = self.editor_appearance_filter_matrix_group.checkedId()
        if self.editor_appearance_efx_arp_group.checkedId() > 1:
            if not self.main.editor_appearance_efx_arp & 2:
                self.main.editor_appearance_efx_arp = self.editor_appearance_efx_arp_latest+2
        else:
            self.main.editor_appearance_efx_arp = self.editor_appearance_efx_arp_group.checkedId()
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
