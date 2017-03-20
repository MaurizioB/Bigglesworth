# *-* coding: utf-8 *-*

from PyQt4 import QtCore, QtGui
from bigglesworth.utils import load_ui
from bigglesworth.const import VERSION, local_path

class AboutDialog(QtGui.QDialog):
    def __init__(self, parent):
        QtGui.QDialog.__init__(self, parent)
        load_ui(self, 'dialogs/about.ui')
        self.version_lbl.setText('Version: {}'.format(VERSION))
        logo = QtGui.QIcon(local_path('bigglesworth_logo.png')).pixmap(QtCore.QSize(280, 32)).toImage()
        logo_widget = QtGui.QLabel()
        logo_widget.setPixmap(QtGui.QPixmap().fromImage(logo))
        logo_widget.setSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.MinimumExpanding)
        self.layout().addWidget(logo_widget, 0, 0, 1, 1, QtCore.Qt.AlignCenter)
        self.setFixedSize(400, 300)


