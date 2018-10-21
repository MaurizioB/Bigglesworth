from Qt import QtCore, QtGui, QtWidgets

from bigglesworth.utils import loadUi, localPath
from bigglesworth.const import ord2chr, INIT, IDE, IDW, GLBD, GLBR, END
from bigglesworth.midiutils import SysExEvent, SYSEX
from bigglesworth.widgets import MidiConnectionsDialog
#from bigglesworth.widgets import DeltaSpin, DeviceIdSpin


class TimerWidget(QtWidgets.QWidget):
    def __init__(self):
        QtWidgets.QWidget.__init__(self)
        self.time = 0
        self.timerRect = QtCore.QRect(0, 0, 31, 31)
        self.setMinimumSize(32, 32)
        self.color = self.palette().color(QtGui.QPalette.WindowText)
        self.pen = QtGui.QPen(self.color, 2, cap=QtCore.Qt.FlatCap)
        self.timerFont = self.font()

    def setTime(self, time):
        self.time = time
        self.update()

    def sizeHint(self):
        return QtCore.QSize(32, 32)

    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        qp.translate(.5, .5)
        qp.setRenderHints(qp.Antialiasing)
        qp.drawEllipse(self.timerRect)
        qp.setPen(self.pen)
        adjustSize = self.timerRect.width() * .05
        secs, rest = divmod(self.time, 1)
        if not rest:
            qp.drawEllipse(self.timerRect.adjusted(adjustSize, adjustSize, -adjustSize, -adjustSize))
        else:
            qp.drawArc(self.timerRect.adjusted(adjustSize, adjustSize, -adjustSize, -adjustSize), 1440, -rest * 5760)
        qp.setFont(self.timerFont)
#        qp.drawText(self.timerRect.adjusted(0, -adjustSize, 0, 0), QtCore.Qt.AlignCenter, str(10 - int(secs)))
        qp.drawText(self.timerRect, QtCore.Qt.AlignCenter, str(10 - int(secs)))

    def resizeEvent(self, event):
        size = min(self.width(), self.height()) - 1
        self.timerRect = QtCore.QRect(0, 0, size, size)
        self.pen.setWidth(size * .1)
        self.timerFont.setPointSize(size * .5)


class GlobalsWaiter(QtWidgets.QDialog):
    def __init__(self, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        self.setModal(True)
        layout = QtWidgets.QGridLayout()
        self.setLayout(layout)

        self.timerWidget = TimerWidget()
        layout.addWidget(self.timerWidget, 0, 0, 2, 1)

        self.defaultMessage = 'Waiting for a response from Blofeld'
        self.label = QtWidgets.QLabel(self.defaultMessage)
        layout.addWidget(self.label, 0, 1)
        self.cancelBtn = QtWidgets.QPushButton('Cancel')
        self.cancelBtn.clicked.connect(self.reject)
        layout.addWidget(self.cancelBtn, 1, 1)
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(5)
        self.timer.timeout.connect(self.updateTimer)
        self.elapsed = QtCore.QElapsedTimer()
        self.rejected.connect(self.timer.stop)
        self.accepted.connect(self.timer.stop)

    def reject(self):
        self.timer.stop()
        self.cancelled = True
        QtWidgets.QDialog.reject(self)

    def closeEvent(self, event):
        self.timer.stop()
        self.cancelled = True

    def updateTimer(self):
        elapsed = self.elapsed.elapsed() * .001
        if elapsed >= 10:
            self.timer.stop()
            QtWidgets.QDialog.reject(self)
            return
        self.timerWidget.setTime(elapsed)

    def exec_(self, apply=False):
        if apply:
            self.label.setText('Sending data to Blofeld and awaiting confirmation')
        else:
            self.label.setText(self.defaultMessage)
        self.cancelled = False
        self.timer.start()
        self.elapsed.start()
        return QtWidgets.QDialog.exec_(self)


class GlobalsDialog(QtWidgets.QDialog):
    midiEvent = QtCore.pyqtSignal(object)
    helpRequested = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        loadUi(localPath('ui/globals.ui'), self)
        self.main = QtWidgets.QApplication.instance()
        self.waiter = GlobalsWaiter(self)
        self.waiter.rejected.connect(self.invalid)
        self.tuneSpin.delta = 376
        self.transposeSpin.delta = -64
        self.transposeSpin.valueChanged.connect(self.setTransposePrefix)
        self.queryDeviceIdSpin.valueChanged.connect(lambda value: self.queryHexLbl.setText('({:02X}h)'.format(value)))
        self.queryDeviceIdSpin.valueChanged.connect(lambda value: self.broadcastBtn.setEnabled(True if value != 127 else False))
        self.broadcastBtn.clicked.connect(lambda: self.queryDeviceIdSpin.setValue(127))
        self.deviceIdSpin.valueChanged.connect(lambda value: self.deviceIdLbl.setText('({:02X}h)'.format(value)))

        self.queryHexLbl.setMinimumWidth(self.fontMetrics().width('(000h)'))
        self.deviceIdLbl.setMinimumWidth(self.queryHexLbl.minimumWidth())

        self.queryBtn.clicked.connect(self.startQuery)

        self.paramDict = {
            self.volumeSpin: 55, 
            self.catCombo: 56, 
            self.tuneSpin: 40, 
            self.transposeSpin: 41, 
            self.freeBtnCombo: 59, 
            self.deviceIdSpin: 37, 
            self.autoEditChk: 35, 
            self.contrastSpin: 39, 
            self.popupSpin: 38, 
            self.velocityCombo: 50, 
            self.pedalCombo: 60, 
            self.channelSpin: 36, 
            self.clockCombo: 48, 
            self.progSendChk: 46, 
            self.localCtrlChk: 57, 
            self.ctrlSendCombo: 44, 
            self.ctrlReceiveChk: 45, 
            self.ctrlWSpin: 51, 
            self.ctrlXSpin: 52, 
            self.ctrlYSpin: 53, 
            self.ctrlZSpin: 54, 
            }
        for combo in (self.catCombo, self.freeBtnCombo, self.velocityCombo, self.pedalCombo, self.clockCombo, self.ctrlSendCombo):
            combo.setValue = combo.setCurrentIndex
            combo.currentIndexChanged.connect(self.editData)
        for chk in (self.autoEditChk, self.progSendChk, self.localCtrlChk, self.ctrlReceiveChk):
            chk.setValue = chk.setChecked
            chk.toggled.connect(self.editData)
        for spin in (self.volumeSpin, self.tuneSpin, self.transposeSpin, self.deviceIdSpin, self.contrastSpin, self.popupSpin, 
            self.channelSpin, self.ctrlWSpin, self.ctrlXSpin, self.ctrlYSpin, self.ctrlZSpin):
            spin.valueChanged.connect(self.editData)

        self.midiConnectionsBtn = QtWidgets.QPushButton(QtGui.QIcon.fromTheme('midi'), 'MIDI connections')
        self.buttonBox.layout().insertWidget(0, self.midiConnectionsBtn)
        self.midiConnectionsBtn.clicked.connect(lambda: MidiConnectionsDialog(self).exec_())
        self.okBtn = self.buttonBox.button(self.buttonBox.Ok)
        self.applyBtn = self.buttonBox.button(self.buttonBox.Apply)
        self.applyBtn.clicked.connect(self.apply)
        self.buttonBox.button(self.buttonBox.Help).clicked.connect(self.helpRequested)

        self.data = None
        self.originalData = []

    def accept(self):
        if self.apply():
            QtWidgets.QDialog.accept(self)

    def apply(self):
        if self.data == self.originalData:
            return True
        savedData = self.data[:]
        originalData = self.originalData[:]
        self.waiter.show()

        self.sysex[5:-2] = self.data
        self.sysex[-2] = 0x7f
        self.midiEvent.emit(SysExEvent(1, self.sysex))

        QtCore.QTimer.singleShot(500, self.startQuery)
        res = self.waiter.exec_(True)
        if not res or not self.waiter.result():
            return False
        if self.originalData != savedData:
            for i, (s, d) in enumerate(zip(savedData, self.originalData)):
                if s != d:
                    print(i, s, d)
            QtWidgets.QMessageBox.warning(
                self, 
                'Data mismatch', 
                'The returned settings do not match the data set.', 
                QtWidgets.QMessageBox.Ok
                )
            self.setData(savedData)
            self.originalData = originalData[:]
            return False
        return True

    def editData(self, value):
        if self.waiter.isVisible():
            return
        value = int(value)
        self.data[self.paramDict[self.sender()]] = value
        self.applyBtn.setEnabled(True if self.data != self.originalData else False)

    def invalid(self):
        if not self.waiter.cancelled:
            QtWidgets.QMessageBox.warning(
                self, 
                'Device timeout', 
                'The request has timed out.<br/>Ensure that the Blofeld is correctly connected ' \
                'to both MIDI input and output ports, and the "&Device ID to query" is correctly ' \
                'set.<br/>If you don\'t know the Device ID, press the "Broadcast" button to query ' \
                'any available device.', 
                QtWidgets.QMessageBox.Ok)

    def startQuery(self, deviceId=False):
        if not self.waiter.isVisible():
            QtCore.QTimer.singleShot(0, self.waiter.exec_)
        self.enableWidgets(False)

        if isinstance(deviceId, bool):
            deviceId = self.queryDeviceIdSpin.value()
        self.deviceIdQuery = deviceId
        self.midiEvent.emit(SysExEvent(1, [INIT, 0x7e, 0x7f, 0x6, 0x1, END]))

    def globalsQuery(self):
        self.midiEvent.emit(SysExEvent(1, [INIT, IDW, IDE, self.deviceIdQuery, GLBR, END]))

    def setTransposePrefix(self, value):
        self.transposeSpin.setPrefix('+' if value >= 64 else '')

    def enableWidgets(self, state):
        self.deviceFrame.setEnabled(state)
        self.generalGroup.setEnabled(state)
        self.systemGroup.setEnabled(state)
        self.midiGroup.setEnabled(state)
        self.okBtn.setEnabled(state)
        self.applyBtn.setEnabled(state if state and self.data != self.originalData else False)

    def midiConnChanged(self, *args):
        enabled = all(args)
        self.queryBtn.setEnabled(enabled)
        self.enableWidgets(True if enabled and self.wasEnabled else False)

    def globalsResponse(self, sysex):
        self.wasEnabled = True
        self.sysex = sysex
        self.setData(sysex[5:-2])
        self.enableWidgets(True)

    def setData(self, data):
        for widget, index in self.paramDict.items():
            widget.setValue(data[index])
        self.data = data
        self.originalData = data[:]
        self.waiter.accept()

    def deviceResponse(self, sysex):
        if sysex[5] == 0x3e:
            dev_man = 'Waldorf Music'
        else:
            dev_man = 'Unknown'
        if sysex[6:8] == [0x13, 0x0]:
            dev_model = 'Blofeld'
        else:
            dev_model = 'Unknown'
#        if sysex[8:10] == [0, 0]:
#            dev_type = 'Blofeld Desktop'
#        else:
#            dev_type = 'Blofeld Keyboard'
        dev_version = ''.join([ord2chr[l] for l in sysex[10:14]]).strip()
        
        self.deviceLbl.setText('Manufacturer: {}\nModel: {}\nFirmware version: {}'.format(
            dev_man, dev_model, dev_version))
        QtCore.QTimer.singleShot(200, self.globalsQuery)

    def midiEventReceived(self, event):
        if event.type == SYSEX:
            sysex_type = event.sysex[4]
            if sysex_type == GLBD:
                self.globalsResponse(event.sysex)
            elif len(event.sysex) == 15 and event.sysex[3:5] == [6, 2]:
                self.deviceResponse(event.sysex)

    def exec_(self):
        self.queryDeviceIdSpin.setValue(self.main.blofeldId)
        self.wasEnabled = False
#        self.midiEvent.emit(SysExEvent(1, [INIT, 0x7e, 0x7f, 0x6, 0x1, END]))
#        self.midiEvent.emit(SysExEvent(1, [INIT, IDW, IDE, self.main.blofeldId, GLBR, END]))
        QtCore.QTimer.singleShot(20, self.waiter.exec_)
        QtCore.QTimer.singleShot(30, lambda: self.startQuery(self.main.blofeldId))
        QtWidgets.QDialog.exec_(self)

