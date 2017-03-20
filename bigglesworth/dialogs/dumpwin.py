# *-* coding: utf-8 *-*

from PyQt4 import QtCore, QtGui

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
        self.setWindowTitle('Sound dump')
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

        self.button_box = QtGui.QWidget(self)
        button_box_layout = QtGui.QHBoxLayout()
        self.button_box.setLayout(button_box_layout)
        grid.addWidget(self.button_box, 5, 0, 1, 2)

        self.toggle_btn = QtGui.QPushButton('Pause', self)
        self.pause_icon = PauseIcon()
        self.resume_icon = ResumeIcon()
        self.toggle_btn.setIcon(self.pause_icon)
        self.toggle_btn.clicked.connect(self.toggle)
        button_box_layout.addWidget(self.toggle_btn)

        stop = QtGui.QPushButton('Stop', self)
        stop.setIcon(self.style().standardIcon(QtGui.QStyle.SP_DialogCloseButton))
        stop.clicked.connect(self.accept)
        button_box_layout.addWidget(stop)

        cancel = QtGui.QPushButton('Cancel', self)
        cancel.setIcon(self.style().standardIcon(QtGui.QStyle.SP_DialogCancelButton))
        cancel.setSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Preferred)
        cancel.clicked.connect(self.reject)
        button_box_layout.addWidget(cancel)

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
        if not self.button_box.isEnabled(): return
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

    def showDisabled(self):
        self.button_box.setEnabled(False)
        self.show()

    def done(self, *args):
        QtGui.QDialog.done(self, *args)
        self.button_box.setEnabled(True)

