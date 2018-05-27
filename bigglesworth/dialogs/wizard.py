import os, sys

os.environ['QT_PREFERRED_BINDING'] = 'PyQt4'

from Qt import QtCore, QtGui, QtWidgets

#from PyQt4 import uic
from bigglesworth.utils import loadUi, localPath
from bigglesworth.const import ord2chr
from bigglesworth.midiutils import SysExEvent, INIT, END, SYSEX
#from bigglesworth.widgets import MidiConnectionWidget


class AutoconnectPage(QtWidgets.QWizardPage):
    midiEvent = QtCore.pyqtSignal(object)
    midiConnect = QtCore.pyqtSignal(object, object, object)
    found = QtCore.pyqtSignal(bool, object, object)
    def __init__(self, *args, **kwargs):
        QtWidgets.QWizardPage.__init__(self, *args, **kwargs)
        self.tested = []
        self.timer = QtCore.QTimer()
        self.timer.setSingleShot(True)
        self.timer.setInterval(500)
        self.timer.timeout.connect(self.testNext)
        self.bloTesting = False
        self.shown = False
        self.found.connect(self.checkFound)

    def showEvent(self, event):
        if not self.shown:
            self.shown = True
            self.foundLbl = QtWidgets.QLabel()
            self.foundLbl.setAlignment(QtCore.Qt.AlignCenter)
            row, column, rowSpan, colSpan = self.layout().getItemPosition(self.layout().indexOf(self.waiter))
            self.layout().addWidget(self.foundLbl, row, column, rowSpan, colSpan)

    def log(self, message, newLine=False, bold=False):
        if bold:
            html = '<b>{}</b>'.format(message)
        else:
            html = message
        if newLine:
            html += '<br/><br/>'
        self.logger.insertHtml(html)
        self.logger.ensureCursorVisible()
        self.logger.verticalScrollBar().setValue(self.logger.verticalScrollBar().maximum())

    def query(self):
        self.midiEvent.emit(SysExEvent(1, [INIT, 0x7e, 0x7f, 0x6, 0x1, END]))
        self.timer.start()

    def midiEventReceived(self, event):
        if event.type != SYSEX or len(event.sysex) != 15 or event.sysex[3:5] != [6, 2]:
            return
        sysex = event.sysex
        self.timer.stop()
        if sysex[5] == 0x3e:
            manufacturer = 'Waldorf Music'
        else:
            manufacturer = 'Unknown'
        if sysex[6:8] == [0x13, 0x0]:
            model = 'Blofeld'
        else:
            model = 'Unknown'
        if sysex[8:10] == [0, 0]:
            devType = 'Blofeld Desktop'
            self.setBlofeldImage('dt')
        else:
            devType = 'Blofeld Keyboard'
            self.setBlofeldImage('kb')
        dev_version = ''.join([ord2chr[l] for l in sysex[10:14]]).strip()
        self.log('&nbsp;Found!', True, True)
        self.log('<br/>Device info:<br/><br/>Manufacturer: {}<br/>Model: {}<br/>Type: {}<br/>Firmware version: {}'.format(
            manufacturer, model, devType, dev_version), True, True)
        src = self.graph.port_id_dict[event.source[0]][event.source[1]]
        self.found.emit(True, src, self.bloTesting if self.bloTesting else self.tested[-1])

    def setBlofeldImage(self, t):
        pm = QtGui.QPixmap(localPath('../resources/blofeld_{}_perspective_alpha.png'.format(t))).scaledToWidth(
                self.waiter.width(), QtCore.Qt.SmoothTransformation)
        self.foundLbl.setPixmap(pm)
#        self.waiter.active = False
#        self.waiter.hide()

    def startDetection(self, already=True):
        self.log('Starting detection', True, True)
        inConn, outConn = self.main.connections
        if already and all((inConn, outConn)):
            bloFound = False
            for conn in inConn:
                if conn.src.client.name == 'Blofeld' and conn.src.name.startswith('Blofeld MIDI'):
                    for conn in outConn:
                        if conn.dest.client.name == 'Blofeld' and conn.dest.name.startswith('Blofeld MIDI'):
                            bloFound = conn.dest
                            break
                    break
            if bloFound:
                self.log('Querying possible USB connected Blofeld, waiting for response...')
                self.bloTesting = bloFound
                QtCore.QTimer.singleShot(500, self.query)
                return
        inFound = outFound = False
        for client, portDict in self.graph.port_id_dict.items():
            if self.graph.client_id_dict[client].name == 'Blofeld':
                for port in portDict.values():
                    if port.is_input and port.name.startswith('Blofeld MIDI'):
                        outFound = True
                        self.midiConnect.emit(port, True, True)
                    if port.is_output and port.name.startswith('Blofeld MIDI'):
                        inFound = port
                        self.midiConnect.emit(port, False, True)
                    if inFound and outFound:
                        break
            if inFound and outFound:
                break
        if inFound and outFound:
            self.log('Querying possible USB connected Blofeld, waiting for response...')
            self.bloTesting = inFound
            self.tested.append(inFound)
            QtCore.QTimer.singleShot(500, self.query)
            return
        self.log('Connecting output device ports to Bigglesworth\'s input.<br/>', True)
        for client, portDict in self.graph.port_id_dict.items():
            for port in portDict.values():
                if port.is_output and not port.hidden and port != self.main.output:
                    self.midiConnect.emit(port, False, True)
                if port.is_input and not port.hidden and port != self.main.input and not self.tested:
                    self.midiConnect.emit(port, True, True)
                    self.tested.append(port)
        self.log('Testing port "{}"...'.format(self.tested[0]))
        QtCore.QTimer.singleShot(500, self.query)

    def checkFound(self, found, src, dest):
        self.waiter.active = False
        self.waiter.hide()
        self.foundLbl.show()
        if not found:
            self.foundLbl.setText('?')
            font = self.font()
            font.setPointSize(font.pointSize() * 4)
            self.foundLbl.setFont(font)

        inConn, outConn = self.main.connections
        for conn in inConn:
            if conn.src != src and not conn.src.hidden:
                self.midiConnect.emit(conn.src, False, False)
        for conn in outConn:
            if conn.dest != dest and not conn.dest.hidden:
                self.midiConnect.emit(conn.dest, True, False)

    def stop(self):
        self.timer.stop()
        self.log('<br/><br/>Detection stopped...<br/>You can restart it or proceed to the next page to manually connect your Blofeld.')
        self.bloTesting = False
        self.waiter.active = False
        self.waiter.hide()
        self.foundLbl.show()
        self.foundLbl.setText('')
        inConn, outConn = self.main.connections
        for conn in inConn:
            if not conn.src.hidden:
                self.midiConnect.emit(conn.src, False, False)
        for conn in outConn:
            if not conn.dest.hidden:
                self.midiConnect.emit(conn.dest, True, False)

    def restart(self):
        self.logger.clear()
        self.bloTesting = False
        self.tested = []
        self.waiter.active = True
        self.waiter.show()
        self.foundLbl.hide()
        for client, portDict in self.graph.port_id_dict.items():
            for port in portDict.values():
                if port.is_output and not port.hidden and port != self.main.output:
                    self.midiConnect.emit(port, False, True)
                if port.is_input and not port.hidden:
                    self.midiConnect.emit(port, True, False)
        self.startDetection(already=False)

    def testNext(self):
        if not self.timer.isActive():
            return
        self.log('&nbsp;No response', True)
        if self.bloTesting:
            self.bloTesting = False
            for client, portDict in self.graph.port_id_dict.items():
                for port in portDict.values():
                    if port.is_output and not port.hidden and port != self.main.output:
                        self.midiConnect.emit(port, False, True)
                    if port.is_input and not port.hidden and port != self.main.input and not self.tested:
                        self.midiConnect.emit(port, True, True)
                        self.tested.append(port)
        else:
            newFound = False
            for client, portDict in self.graph.port_id_dict.items():
                for port in portDict.values():
                    if port.is_input and not port.hidden and port != self.main.input and not port in self.tested:
                        self.midiConnect.emit(port, True, True)
                        self.tested.append(port)
                        newFound = True
                        break
                if newFound:
                    break
            else:
                self.log('<br/>Blofeld not found!!!<br/>', True, True)
                self.log('Ensure that your Blofeld is powered on and that it is connected to both MIDI input and output ' \
                    'and try again by pressing "Restart".<br/>Remember that the USB cable connection is needed ' \
                    'for two-ways communication with the Blofeld Desktop.<br/><br/>' \
                    'You can try to manually connect it in the next page, anyway.')
                self.found.emit(False, None, None)
                return
        self.log('Testing port "{}"...'.format(self.tested[-1]))
        QtCore.QTimer.singleShot(250, self.query)


class FirstRunWizard(QtWidgets.QWizard):
#    midiEvent = QtCore.pyqtSignal(object)
    def __init__(self, main):
        QtWidgets.QWizard.__init__(self)
        loadUi(localPath('ui/wizard.ui'), self)
        self.main = main
        self.midiConnectionsWidget.setMain(main)
        self.autoconnectPage.main = main
        self.autoconnectPage.graph = main.graph
        self.autoconnectPage.logger = self.logger
        self.autoconnectPage.found.connect(self.bloFound)
        self.autoconnectPage.waiter = self.waiter
        self.setButtonText(self.CancelButton, 'I\'m a pro, leave me alone!')
        self.logo = QtGui.QPixmap(localPath('../resources/bigglesworth_logo.svg'))
        self.restartBtn.clicked.connect(self.autoDetectRestart)
        self.stopBtn.clicked.connect(self.autoconnectPage.stop)
        self.stopBtn.clicked.connect(self.autoDetectStop)
        self.currentIdChanged.connect(self.pageChanged)
        self.autoconnectPage.isComplete = lambda: False
        self.midiPage.isComplete = lambda: True if self.main.connections[0] else False
        self.shown = False
        self.found = False
#        self.autoconnectPage.midiEvent.connect(self.midiEvent)

    def autoDetectRestart(self):
        self.stopBtn.setEnabled(True)
        self.restartBtn.setEnabled(False)
        self.button(self.NextButton).setEnabled(False)
        self.autoconnectPage.restart()

    def autoDetectStop(self):
        self.restartBtn.setEnabled(True)
        self.stopBtn.setEnabled(False)
        self.button(self.NextButton).setEnabled(True)

    def bloFound(self, found, src, dest):
        self.found = found
        self.button(self.NextButton).setEnabled(True)
        self.stopBtn.setEnabled(False)
        self.restartBtn.setEnabled(True)

    def showEvent(self, event):
        if not self.shown:
            self.shown = True
            scaledBanner = QtGui.QPixmap(localPath('../resources/bigglesworth_textonly_gray.svg')).scaledToWidth(
                self.width() * .8, QtCore.Qt.SmoothTransformation)
            fullRect = QtCore.QRect(0, 0, self.width(), scaledBanner.height() * 1.25)
            realBanner = QtGui.QPixmap(fullRect.size())
            realBanner.fill(QtCore.Qt.transparent)
            qp = QtGui.QPainter(realBanner)
            qp.drawPixmap(fullRect.center().x() - scaledBanner.width() * .5125, fullRect.center().y() - scaledBanner.height() * .5, scaledBanner)
            qp.end()
            self.setPixmap(self.BannerPixmap, realBanner)
            self.setPixmap(self.LogoPixmap, self.logo.scaledToHeight(scaledBanner.height() * .6, QtCore.Qt.SmoothTransformation))
            self.logoLbl.setPixmap(QtGui.QPixmap(localPath('../resources/bigglesworth_textonly.svg')).scaledToWidth(
                self.width() * .95, QtCore.Qt.SmoothTransformation))

    def alsaConnEvent(self, conn):
        if self.currentPage() != self.midiPage:
            return
        self.button(self.NextButton).setEnabled(True if self.main.connections[0] else False)

    def midiEventReceived(self, event):
        if self.currentPage() == self.autoconnectPage:
            self.autoconnectPage.midiEventReceived(event)

    def pageChanged(self, id):
        if id >= 1:
            if 0 in self.visitedPages():
                self.removePage(0)
                self.setOption(self.NoCancelButton, True)

    def nextId(self):
        if self.currentPage() == self.autoconnectPage and all(self.main.connections):
            return 3 if self.found else 2
#        elif self.currentPage() == self.midiPage and not self.main.connections[0]:
#            return 3
        return QtWidgets.QWizard.nextId(self)

    def initializePage(self, id):
        if id == 0:
            self.logo
        elif id == 1 and id not in self.visitedPages():
            self.autoconnectPage.startDetection()

    def validateCurrentPage(self):
        if self.currentPage() == self.midiPage and not self.main.connections[0]:
            res = QtWidgets.QMessageBox.question(self, 
                'No MIDI connection', 
                'Bigglesworth needs at least a MIDI input connection.\n' \
                'Press "Cancel" to review the connections; you can proceed anyway by pressing "Ok"', 
                QtWidgets.QMessageBox.Ignore|QtWidgets.QMessageBox.Cancel
                )
            if res == QtWidgets.QMessageBox.Cancel:
                return False
#            elif res == QtWidgets.QMessageBox.Ok:
#                self.accept()
#                return False
        return True

    def exec_(self):
        return QtWidgets.QWizard.exec_(self)

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    w = FirstRunWizard()
    w.show()
    sys.exit(app.exec_())
