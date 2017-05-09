# *-* coding: utf-8 *-*

from PyQt4 import QtCore, QtGui
from bigglesworth.utils import load_ui
from bigglesworth.dialogs import SYXFILE

class WavetableListWindow(QtGui.QDialog):
    def __init__(self, main):
        QtGui.QDialog.__init__(self)
        load_ui(self, 'dialogs/wavetable_list.ui')
        self.main = main
        self.wavetable_library = self.main.wavetable_library
        self.wavetable_model = self.wavetable_library.model
        self.wavetable_view.setModel(self.wavetable_model)
        self.wavetable_view.verticalHeader().setResizeMode(QtGui.QHeaderView.ResizeToContents)
        self.wavetable_view.horizontalHeader().setResizeMode(1, QtGui.QHeaderView.ResizeToContents)
        self.wavetable_view.horizontalHeader().setResizeMode(2, QtGui.QHeaderView.ResizeToContents)

        self.new_btn.setIcon(QtGui.QIcon.fromTheme('document-new'))
        self.import_btn.setIcon(QtGui.QIcon.fromTheme('document-open'))
        self.duplicate_btn.setIcon(QtGui.QIcon.fromTheme('edit-copy'))
        self.delete_btn.setIcon(QtGui.QIcon.fromTheme('edit-delete'))

        self.new_btn.clicked.connect(self.new_wavetable)
        self.import_btn.clicked.connect(self.import_wavetable)
        self.duplicate_btn.clicked.connect(self.duplicate)
        self.delete_btn.clicked.connect(self.delete)

        self.wavetable_view.doubleClicked.connect(self.wavetable_show)
        self.wavetable_view.doubleClicked.connect(self.enable_buttons)
        self.wavetable_view.activated.connect(self.enable_buttons)
        self.wavetable_view.clicked.connect(self.enable_buttons)
        self.wavetable_model.columnsInserted.connect(self.update_columns)
        self.wavetable_model.rowsInserted.connect(self.resort)
        self.wavetable_model.rowsRemoved.connect(self.resort)
        self.wavetable_model.rowsRemoved.connect(lambda *_: self.duplicate_btn.setEnabled(False) if not self.wavetable_model.rowCount() else None)

    def resort(self):
        #TODO: check this, doesn't work as it should. maybe use a proxymodel?
        sort = self.wavetable_view.horizontalHeader().sortIndicatorSection()
        rule = self.wavetable_view.horizontalHeader().sortIndicatorOrder()
        self.wavetable_view.horizontalHeader().setSortIndicator(-1, 0)
        QtCore.QTimer.singleShot(0, lambda: self.wavetable_view.horizontalHeader().setSortIndicator(sort, rule))

    def update_columns(self, index, start, end):
        self.wavetable_view.setColumnHidden(3, True)
        self.wavetable_view.setColumnHidden(4, True)

    def new_wavetable(self):
        self.main.wavetable_show()

    def import_wavetable(self):
        self.main.file_import(mode=SYXFILE)

    def wavetable_show(self, index):
        uid = self.wavetable_model.item(index.row(), 4).text()
        self.main.wavetable_show(uid)

    def enable_buttons(self, *args):
        self.duplicate_btn.setEnabled(True)
        self.delete_btn.setEnabled(True)

    def duplicate(self):
        row = self.wavetable_view.selectedIndexes()[0].row()
        uid = str(self.wavetable_model.item(row, 4).text())
        self.wavetable_library.duplicate(uid)

    def delete(self):
        row = self.wavetable_view.selectedIndexes()[0].row()
        uid = self.wavetable_model.item(row, 4).text()
        for window in self.main.wavetable_windows_list:
            if window.wavetable_uid == uid:
                QtGui.QMessageBox.critical(self, 'Wavetable is open', 'The selected wavetable is currently open.\nClose its window to allow deletion.')
                return
        name = self.wavetable_model.item(row, 0).text()
        res = QtGui.QMessageBox.question(self, 'Delete wavetable', 'Do you want to delete wavetable "{}"?'.format(name), QtGui.QMessageBox.Yes|QtGui.QMessageBox.No)
        if res == QtGui.QMessageBox.Yes:
            self.wavetable_library.delete(uid)




