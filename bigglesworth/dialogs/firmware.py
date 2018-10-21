from Qt import QtCore, QtGui, QtWidgets

from bigglesworth.libs import midifile
from bigglesworth.utils import loadUi, localPath
from bigglesworth.const import factoryPresets, factoryPresetsNamesDict
from bigglesworth.midiutils import SysExEvent, INIT, END, SYSEX
from bigglesworth.widgets.misc import Waiter
from bigglesworth.widgets.midiconnections import MidiConnectionsDialog
from bigglesworth.dialogs import WarningMessageBox, QuestionMessageBox, GlobalsWaiter

FirmwareVersionRole = QtCore.Qt.UserRole + 1
FirmwareFileRole = FirmwareVersionRole + 1

firmwareInfo = [
    '''
        This is the firmware that was considered standard until August 2018.<br/>
        <b>DO NOT</b> use it if you bought a new device after August 2018.
    ''', 
    '''
        This is an alternate firmware that was available until circa 2017.<br/>
        It is similar to the 1.22 version and it has been reported that, 
        <i>in some cases</i>, it worked better.<br/>
        It is mostly provided for historical or testing reasons, but its usage 
        is highly discouraged.<br/>
        <b>DO NOT</b> use it if you bought a new device after August 2018.
    ''', 
    '''
        This is the current standard firmware for old and new Blofeld devices.<br/>
        Update to this firmware is highly recommended if you encounter problems
        with the Blofeld encoders.<br/>
        If you bought a new device after August 2018 you probably have this already.
    ''', 
]

firmwareFiles = [
    ((1, 22), 'BlofeldV122.mid'), 
    ((1, 23), 'BlofeldV123.mid'), 
    ((1, 25), 'BlofeldV125.mid'), 
]

latestVersion = '{}.{}'.format(*firmwareFiles[-1][0])


factoryInfo = [
    '''
        This preset collection is the first sound set shipped on Blofeld units 
        when it first came out.<br/>
        It is provided for historical and testing reasons only as it was followed
        by a revised version shortly after.
    ''', 
    '''
        This is the revised sound set based on the first one.<br/>
        597 sounds in total have been changed, mostly regarding the Amplifier 
        volume parameter, which were very inconsistent across the whole set
        in the previous version.
    ''', 
    '''
        This is an almost completely new sound set shipped on new units,
        starting from 2012.<br/>
        While the first 7 banks contain new sounds, the H bank, containing 
        effects and percussive sounds, is identical to the previous sets 
        (except for the INIT sound provided at slot H128), and it usually 
        differs by different Amplifier volume values and other slightly 
        changed parameters.
    '''
]


class Dumper(QtWidgets.QProgressDialog):
    def __init__(self, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        self.setCancelButton(None)
        self.elapsed = QtCore.QElapsedTimer()
        self.label = self.findChild(QtWidgets.QLabel)
        self.label.setAlignment(QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        layout = QtWidgets.QGridLayout()
        self.setLayout(layout)
        for child in self.children():
            if not isinstance(child, QtWidgets.QWidget):
                continue
            if child == self.label:
                layout.addWidget(child, 0, 1)
            else:
                layout.addWidget(child, layout.rowCount(), 1, 1, layout.columnCount())
        waiter = Waiter()
        waiter.setMaximumHeight(self.fontMetrics().height() * 3)
        layout.addWidget(waiter, 0, 0, layout.rowCount(), 1, QtCore.Qt.AlignCenter)
        layout.addWidget(QtWidgets.QLabel('<b>DO NOT</b> disconnect nor switch off your Blofeld!!!'), 
            layout.rowCount(), 0, 1, layout.columnCount())

    def closeEvent(self, event):
        event.ignore()

    def keyPressEvent(self, event):
        pass

    def reject(self):
        pass

    def increase(self):
        value = self.value() + 1
        self.setValue(self.value() + 1)
        if value and value != self.maximum():
            diff = self.lastTime - self.elapsed.elapsed()
            if diff < 5000:
                eta = 'almost there...'
            else:
                eta = '{:02}:{:02}'.format(*divmod((diff) / 1000, 60))
            self.setLabelText('{}<br/><br/>Data sent: {}/{}<br/>ETA: {}'.format(
                self.currentLabel, value, self.maximum(), eta))

    def start(self, count, lastTime, label):
        self.setLabelText('{}<br/><br/>Data sent: {}/{}<br/>ETA: unknown'.format(label, 0, count))
        self.currentLabel = label
        self.setMaximum(count)
        self.setValue(0)
        self.lastTime = lastTime
        self.count = 0
        self.show()
        self.elapsed.start()
        QtWidgets.QApplication.processEvents()


class FirmwareDialog(QtWidgets.QDialog):
    midiEvent = QtCore.pyqtSignal(object)
    shown = False

    def __init__(self, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        loadUi('ui/firmware.ui', self)
        self.main = QtWidgets.QApplication.instance()

        self.tabWidget.currentChanged.connect(self.resetSizes)

        self.detectFirmwareBtn.clicked.connect(self.detectFirmware)
        for index, (firmware, fileName) in enumerate(firmwareFiles):
            self.firmwareCombo.addItem('{}.{}'.format(*firmware))
            self.firmwareCombo.setItemData(index, firmware, FirmwareVersionRole)
            self.firmwareCombo.setItemData(index, fileName, FirmwareFileRole)
        self.firmwareCombo.currentIndexChanged.connect(self.setFirmwareInfo)
        self.firmwareCombo.setCurrentIndex(2)
        self.dumpFirmwareBtn.clicked.connect(self.dumpFirmware)

        for index, preset in enumerate(factoryPresets):
            self.factoryCombo.addItem(QtGui.QIcon.fromTheme('factory'), factoryPresetsNamesDict[preset])
            self.factoryCombo.setItemData(index, '{}.mid'.format(preset))
        self.factoryCombo.currentIndexChanged.connect(self.setPresetInfo)
        self.factoryCombo.setCurrentIndex(2)
        self.dumpPresetBtn.clicked.connect(self.dumpPreset)

        self.dumpKeyboardBtn.clicked.connect(self.dumpKeyboard)
        self.dumpRecoveryBtn.clicked.connect(self.dumpRecovery)

        self.tickRatio = 4.
        self.dumpTimer = QtCore.QTimer()
        self.dumpTimer.setSingleShot(True)
        self.dumpTimer.timeout.connect(self.dumpNext)
        self.progressDialog = Dumper(self)
        self.detectedVersion = None

        self.waiter = GlobalsWaiter(self)
        self.waiter.rejected.connect(self.undetected)
        self.midiConnectionsBtn.clicked.connect(lambda: MidiConnectionsDialog(self).exec_())

    def undetected(self):
        if not self.waiter.cancelled:
            QtWidgets.QMessageBox.warning(
                self, 
                'Device timeout', 
                'The request has timed out.<br/>Ensure that the Blofeld is correctly connected ' \
                'to both MIDI input and output ports, then try again.', 
                QtWidgets.QMessageBox.Ok)

    def detectFirmware(self):
        if not self.waiter.isVisible():
            QtCore.QTimer.singleShot(0, self.waiter.exec_)
        self.midiEvent.emit(SysExEvent(1, [INIT, 0x7e, 0x7f, 0x6, 0x1, END]))

    def midiEventReceived(self, event):
        if event.type != SYSEX or len(event.sysex) != 15 or event.sysex[3:5] != [6, 2]:
            return
        self.waiter.accept()
        sysex = event.sysex
        isWaldorf = sysex[5] == 0x3e
        isBlofeld = sysex[6:8] == [0x13, 0x0]
        try:
            versionText = ''.join([chr(l) for l in sysex[10:14]]).strip()
            version = map(int, versionText.split('.'))
        except:
            versionText = sysex[10:14]
            version = None
        if isWaldorf and isBlofeld and version is not None:
            self.detectedVersion = version
            self.detectedLbl.setEnabled(True)
            self.detectedLbl.setText(versionText)
        else:
            self.detectedLbl.setEnabled(False)
            self.detectedLbl.setText('<i>Unknown</i>')
            QtWidgets.QMessageBox.warning(self, 'Unexpected information received', 
                'Device information received, but there was an error parsing data.<br/>'
                'Received data:<br/><br/>'
                'Manufacturer: {m}<br/>Device: {d}<br/>Version: {v}'.format(
                    m=sysex[5], d=sysex[6:8], v=versionText))

    def midiConnChanged(self, input, output):
        self.dumpButtons.setEnabled(bool(output))
        self.detectFirmwareBtn.setEnabled(all((input, output)))

    def setFirmwareInfo(self, index):
        self.firmwareInfo.setHtml(firmwareInfo[index])
        self.resetSizes()

    def setPresetInfo(self, index):
        self.factoryInfo.setHtml(factoryInfo[index])
        self.resetSizes()

    def resetSizes(self):
        QtWidgets.QApplication.processEvents()
        self.firmwareInfo.setMaximumHeight(self.firmwareInfo.document().size().height() + self.fontMetrics().height())
        self.keyboardInfo.setMaximumHeight(self.keyboardInfo.document().size().height() + self.fontMetrics().height())
        self.factoryInfo.setMaximumHeight(self.factoryInfo.document().size().height() + self.fontMetrics().height())
        self.recoveryInfo.setMaximumHeight(self.recoveryInfo.document().size().height() + self.fontMetrics().height())


    def dumpFirmware(self):
        if self.detectedVersion is not None:
            detectedMaj, detectedMin = self.detectedVersion
            selectedMaj, selectedMin = self.firmwareCombo.itemData(self.firmwareCombo.currentIndex(), FirmwareVersionRole)
            if selectedMaj == detectedMaj and selectedMin == detectedMin:
                if WarningMessageBox(self, 'Same firmware detected', 
                    'The firmware version currently detected ({dMaj}.{dMin}) is the same as '
                    'the selected one. It should not be necessary to dump the firmware.<br/>'
                    'Proceed only if you know what you are doing!'.format(
                        dMaj=detectedMaj, dMin=detectedMin, sMaj=selectedMaj, sMin=selectedMin), 
                    buttons={WarningMessageBox.Ok: 'Proceed anyway', 
                        WarningMessageBox.Cancel: None}).exec_() != WarningMessageBox.Ok:
                            return
            elif selectedMaj <= detectedMaj and selectedMin < detectedMin:
                if WarningMessageBox(self, 'Firmware downgrade detected', 
                    'The firmware version currently detected ({dMaj}.{dMin}) is newer than the '
                    'one selected ({sMaj}.{sMin}). This is <u>highly</u> discouraged.<br/>'
                    '<b>DO NOT</b> dump this firmware if you bought a new Blofeld after August 2018!<br/>'
                    'In any case, you are proceeding at your own risk!'.format(
                        dMaj=detectedMaj, dMin=detectedMin, sMaj=selectedMaj, sMin=selectedMin), 
                    buttons={WarningMessageBox.Ok: 'Proceed anyway', 
                        WarningMessageBox.Cancel: None}).exec_() != WarningMessageBox.Ok:
                            return
        if QuestionMessageBox(self, 'Firmware dump', 
            'Do you want to dump the firmware version {}?<br/><br/>'
            'The procedure will require about 2 minutes; ensure that your '
            'Blofeld is connected and switched on, and <b>DO NOT</b> '
            'disconnect nor switch it off for any reason until completion.'.format(self.firmwareCombo.currentText()), 
            buttons={QuestionMessageBox.Ok: 'Dump!', 
                QtWidgets.QMessageBox.Cancel: None}).exec_() != QuestionMessageBox.Ok:
                    return
        self.finalize = self.dumpFirmwareFinalized
        fileName = self.firmwareCombo.itemData(self.firmwareCombo.currentIndex(), FirmwareFileRole)
        midiFile = QtCore.QDir(localPath('firmware/')).absoluteFilePath(fileName)
        self.dumpPrepare(midiFile, 'Dumping firmware version {}'.format(self.firmwareCombo.currentText()))

    def dumpFirmwareFinalized(self):
        QtWidgets.QMessageBox.information(self, 'Firmware dump completed', 
            'Firmware dump has been completed.<br/><br/>'
            '<b>DO NOT switch off your Blofeld!!!</b><br/>'
            'Press the <b>PLAY</b> button on your Blofeld to complete '
            'the procedure.', 
            QtWidgets.QMessageBox.Ok)
        if WarningMessageBox(self, 'Firmware updated', 
            'Since the firmware has been updated, it is possible that '
            'the new version will not be detected if you press the '
            '"Detect firmware version" button.<br/>'
            'If you have pressed the <b>PLAY</b> button on your '
            'Blofeld, you can now switch it off and on again: '
            'the current version will appear while it starts up '
            'and it will possibly correctly detected afterwards.<br/>'
            'If you have not pressed the <b>PLAY</b> button, '
            '<b>DO IT NOW!!!</b>', 
            buttons={WarningMessageBox.Apply: 'I pressed PLAY, detect again!', 
                WarningMessageBox.Ok: 'I pressed PLAY, yes!'}
            ).exec_() == WarningMessageBox.Apply and all(self.main.connections):
                        self.detectFirmware()

    def dumpPreset(self):
        if QuestionMessageBox(self, 'Preset dump', 
            'Do you want to dump the preset "{}"?<br/><br/>'
            'The procedure will require about 2 minutes; ensure that your '
            'Blofeld is connected and switched on, and <b>DO NOT</b> '
            'disconnect nor switch it off for any reason until completion.'.format(self.factoryCombo.currentText()), 
            buttons={QuestionMessageBox.Ok: 'Dump!', 
                QtWidgets.QMessageBox.Cancel: None}).exec_() != QuestionMessageBox.Ok:
                    return
        self.finalize = self.dumpPresetFinalized
        midiFile = QtCore.QDir(localPath('presets/')).absoluteFilePath(self.factoryCombo.itemData(self.factoryCombo.currentIndex()))
        self.dumpPrepare(midiFile, 'Dumping preset "{}"'.format(self.factoryCombo.currentText()))

    def dumpPresetFinalized(self):
        QtWidgets.QMessageBox.information(self, 'Preset dump completed', 
            'Preset dump has been completed.<br/><br/>'
            'You might want to sync your "Blofeld" collection in Bigglesworth, now.<br/>'
            'If so, right click on its title bar and select "Dump sounds FROM Blofeld" '
            'from the "Dump" sub menu.', 
            QtWidgets.QMessageBox.Ok)

    def dumpKeyboard(self):
        if WarningMessageBox(self, 'Confirm Keyboard firmware dump', 
            'This firmware is for the Keyboard version only.<br/><br/>'
            '<b>DO NOT</b> attempt to dump it on a Desktop version!<br/>'
            'If you do not own a Keyboard model, you are proceeding '
            '<b>at your own risk</b>!', 
            buttons={WarningMessageBox.Ok: 'I have a Blofeld Keyboard', 
                WarningMessageBox.Cancel: None}).exec_() != WarningMessageBox.Ok:
                    return
        self.finalize = self.dumpKeyboardFinalized
        midiFile = QtCore.QDir(localPath('firmware/')).absoluteFilePath('BlofeldKBC14.mid')
        self.dumpPrepare(midiFile, 'Dumping Keyboard Controller Firmware 1.4')

    def dumpKeyboardFinalized(self):
        QtWidgets.QMessageBox.information(self, 'Keyboard firmware dump completed', 
            'Keyboard firmware dump has been completed.<br/><br/>'
            '<b>DO NOT switch off your Blofeld!!!</b><br/>'
            'Press the <b>PLAY</b> button on your Blofeld to complete '
            'the procedure.', 
            QtWidgets.QMessageBox.Ok)

    def dumpRecovery(self):
        for conn in self.main.connections[1]:
            portName = conn.dest.name.lower()
            clientName = conn.dest.client.name.lower()
            if 'blofeld' in portName or 'waldorf' in portName or 'blofeld' in clientName or 'waldorf' in clientName:
                if WarningMessageBox(self, 'USB detected', 
                    'It seems that your Blofeld is connected to the USB port.<br/>'
                    'The recovery system can properly work only when connected '
                    'to MIDI ports. Since Bigglesworth cannot be absolutely certain '
                    'about the connection type, you can proceed anyway if you are '
                    'completely sure that it is connected to a MIDI port', 
                    buttons=QuestionMessageBox.Ok|QuestionMessageBox.Cancel).exec_() != QuestionMessageBox.Ok:
                        return
        if QuestionMessageBox(self, 'Recovery dump', 
            'Do you want to dump the Recovery system?<br/><br/>'
            'Use this system only when absolutely necessary!<br/>'
            'The procedure will require about 30 seconds; ensure that your '
            'Blofeld is connected and switched on, and <b>DO NOT</b> '
            'disconnect nor switch it off for any reason until completion.', 
            buttons={QuestionMessageBox.Ok: 'Recovery!', 
                QtWidgets.QMessageBox.Cancel: None}).exec_() != QuestionMessageBox.Ok:
                    return
        self.finalize = self.dumpRecoveryFinalized
        midiFile = QtCore.QDir(localPath('firmware/')).absoluteFilePath('blofeld_rescue.mid')
        self.dumpPrepare(midiFile, 'Dumping Recovery system')

    def dumpRecoveryFinalized(self):
        if QuestionMessageBox(self, 'Recovery dump completed', 
            'Recovery system dump has been completed.<br/><br/>'
            '<b>DO NOT switch off your Blofeld!!!</b><br/>'
            'If your Blofeld asks you to upload the firmware '
            'again, press "Dump firmware" and the latest firmware '
            'version will be dumped.', 
            buttons={QuestionMessageBox.Apply: ('Dump firmware', QtGui.QIcon.fromTheme('dump')), 
                QuestionMessageBox.Ok: 'Close'}).exec_() == QuestionMessageBox.Apply and \
        QuestionMessageBox(self, 'Dump firmware', 
            'Ensure that your Blofeld is asking you to upload the '
            'firmware again.<br/>If so, click Ok to proceed and '
            'dump the latest version of the firmware ({}).'.format(latestVersion), 
            buttons={QuestionMessageBox.Ok: 'Dump latest firmware', 
                QuestionMessageBox.Cancel: None}).exec_() == QuestionMessageBox.Ok:
                    self.tabWidget.setCurrentWidget(self.firmwareTab)
                    self.firmwareCombo.setCurrentIndex(2)
                    self.dumpFirmware()

    def dumpPrepare(self, midiFile, progressLabel):
        pattern = midifile.read_midifile(midiFile)
        track = pattern[0]
        bpm = 120
        events = []
        for event in track:
            if isinstance(event, midifile.SetTempoEvent):
                bpm = event.bpm
            elif isinstance(event, midifile.SysexEvent):
                events.append(event)
        self.events = iter(events)

        tickLength = 60000. / bpm
        self.tickRatio = tickLength / pattern.resolution
        pattern.make_ticks_abs()
        lastTime = int(track[-1].tick * self.tickRatio)
        pattern.make_ticks_rel()
        self.progressDialog.start(len(events), lastTime, progressLabel)

        self.dumpNext()

    def dumpNext(self):
        try:
            self.midiEvent.emit(self.currentEvent)
        except AttributeError:
            pass
        except Exception as e:
            print(e)
        try:
            event = self.events.next()
            #convert from midi sysex data (thus skipping the byte count)
            for index, value in enumerate(event.data):
                if value & 128:
                    continue
                #the first value with msb == 0 is the latest of the byte count
                #skipping it
                index += 1
                break
            else:
                index = 0
            data = list(event.data)[index:]
            self.currentEvent = SysExEvent(1, [INIT] + data + [END])
            self.progressDialog.increase()
            self.dumpTimer.setInterval(event.tick * self.tickRatio)
            self.dumpTimer.start()
        except Exception as e:
            print(e)
            self.progressDialog.setValue(self.progressDialog.maximum())
            self.finalize()

    def resizeEvent(self, event):
        QtWidgets.QDialog.resizeEvent(self, event)
        self.resetSizes()

    def showEvent(self, event):
        if not self.shown:
            self.shown = True
            self.resetSizes()

    def exec_(self):
        input, output = self.main.connections
        self.midiConnChanged(input, output)
        if all((input, output)):
            QtCore.QTimer.singleShot(100, self.detectFirmware)
        return QtWidgets.QDialog.exec_(self)
