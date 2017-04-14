# *-* coding: utf-8 *-*

from PyQt5 import QtCore, QtWidgets

class LoadingWindow(QtWidgets.QDialog):
    shown = QtCore.pyqtSignal()
    def __init__(self, parent=None):
        self.main = parent
        QtWidgets.QDialog.__init__(self, parent)
        self.setWindowTitle('Presets loading...')
        self.setModal(True)
        grid = QtWidgets.QGridLayout(self)
        loading_lbl = QtWidgets.QLabel('Loading local presets, please wait')
        grid.addWidget(loading_lbl, 0, 0)
        self.loading = False

    def showEvent(self, event):
        if not self.loading:
            self.loading = True
            QtCore.QTimer.singleShot(100, self.shown.emit)

    def set_models(self, model, library):
        self.hide()

    def closeEvent(self, event):
        event.ignore()

