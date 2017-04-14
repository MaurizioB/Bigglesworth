# *-* coding: utf-8 *-*

from string import uppercase
from PyQt5 import QtWidgets
from bigglesworth.utils import load_ui

class SoundDumpDialog(QtWidgets.QDialog):
    def __init__(self, main, parent):
        QtWidgets.QDialog.__init__(self, parent)
        self.main = main
        load_ui(self, 'dialogs/dumpdialog.ui')
        self.bank_combo.currentIndexChanged.connect(self.update_label)
        self.prog_spin.valueChanged.connect(self.update_label)
        self.store_chk.toggled.connect(self.check)
        self.editor_chk.toggled.connect(self.check)
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Ignore).clicked.disconnect()
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Ignore).clicked.connect(self.reject)

    def check(self, *args):
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True if any((self.store_chk.isChecked(), self.editor_chk.isChecked())) else False)

    def update_label(self, *args):
        self.library_sound_lbl.setText(self.main.blofeld_library.sound(self.bank_combo.currentIndex(), self.prog_spin.value()-1).name)

    def exec_(self, sound):
        self.summary_widget.setSoundData(sound.data)
        self.editor_chk.setChecked(True)
        self.store_chk.setChecked(False)
        self.bank_combo.addItems([uppercase[b] for b in range(self.main.blofeld_library.banks)])
        self.dump_sound_lbl.setText(sound.name)
        if not None in self.main.blofeld_current:
            bank, prog = self.main.blofeld_current
            self.bank_combo.setCurrentIndex(bank)
            self.prog_spin.setValue(prog+1)
        res = QtWidgets.QDialog.exec_(self)
        if not res: return False
        return self.editor_chk.isChecked(), (self.bank_combo.currentIndex(), self.prog_spin.value()-1) if self.store_chk.isChecked() else False

#    def resizeEvent(self, event):
#        self.setFixedSize(self.size())

