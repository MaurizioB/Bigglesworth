from Qt import QtGui, QtCore, QtWidgets
from bigglesworth.widgets import MidiConnectionsWidget

class MidiDuplicateDialog(QtWidgets.QMessageBox):
    def __init__(self, main):
        QtWidgets.QMessageBox.__init__(self, QtWidgets.QMessageBox.Warning, 'Duplicate MIDI events', 
            'Duplicate MIDI events received from more than one source<br/>' \
            'Further duplicate events will be ignored.<br/><br/>' \
            'Please check your midi connections.', 
            QtWidgets.QMessageBox.Ok)
        self.main = main
        self.setModal(True)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)

        self.midiWidget = MidiConnectionsWidget(hideOutput=True, hideAlert=True)
        self.layout().addWidget(self.midiWidget, self.layout().rowCount(), 0, 1, self.layout().columnCount())
#        self.accepted.connect(lambda: setattr(self, 'shown', False))
        self.shown = False
        self.dismissed = False

    def reject(self):
        pass

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            return
        QtWidgets.QMessageBox.keyPressEvent(self, event)

    def closeEvent(self, event):
        event.ignore()

    def showEvent(self, event):
        if not self.shown:
            self.shown = True
            QtWidgets.QApplication.processEvents()
            self.center()

    def hideEvent(self, event):
        self.shown = False
        self.dismissed = True

    def center(self):
        desktop = QtWidgets.QApplication.desktop()
        center = desktop.availableGeometry(QtGui.QCursor.pos()).center()
        self.move(center.x() - self.width() / 2, center.y() - self.height() / 2)

    def activate(self, dumping=True, sources=None):
        if dumping:
            if self.dismissed:
                return
            self.dismissed = False
        self.midiWidget.setVisible(not dumping)
        if sources:
            self.midiWidget.setPossibleDuplicates(sources)
        self.show()
        self.center()
        self.activateWindow()

