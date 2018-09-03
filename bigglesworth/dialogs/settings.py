import sys
import sqlite3
from Qt import QtCore, QtGui, QtWidgets

from dial import Dial
from combo import Combo
from slider import Slider
from frame import Frame

from bigglesworth.utils import loadUi
from bigglesworth.themes import ThemeCollection
from bigglesworth.midiutils import SysExEvent, SYSEX, GLBD, INIT, IDW, IDE, GLBR, END
from bigglesworth.dialogs import ThemeEditor, GlobalsWaiter, BaseFileDialog


class MoveDbDialog(BaseFileDialog):
    def __init__(self, parent, currentDbFile, selectedFile=None):
        BaseFileDialog.__init__(self, parent, BaseFileDialog.AcceptSave)
        self.setWindowTitle('Move database location')
        self.setNameFilters(['SQLite database (*.sqlite)', 'All files (*)'])
        self.currentDbFile = currentDbFile
        self.setDefaultSuffix('sqlite')
        self.setOverwrite(False)
        self.selectedFile = selectedFile if selectedFile else currentDbFile
        self.selectedFileInfo = QtCore.QFileInfo(self.selectedFile)
        if QtCore.QDir(self.selectedFileInfo.absolutePath()).exists():
            self.setDirectory(self.selectedFileInfo.absolutePath())
            self.selectFile(self.selectedFileInfo.fileName())
        else:
            self.setDirectory(self._locations[self.Home].toLocalFile())
        self.setSystemUrls(self.Computer|self.Documents)

    def errorMessage(self, path):
        QtWidgets.QMessageBox.critical(self, 'Cannot overwrite', 
            'You choose to move the database, but selected an existing file.\nPlease select a new file path and name', 
            QtWidgets.QMessageBox.Ok)


class OpenDbDialog(BaseFileDialog):
    def __init__(self, parent, currentDbFile, selectedFile=None):
        BaseFileDialog.__init__(self, parent, BaseFileDialog.AcceptOpen)
        self.setWindowTitle('Open database location')
        self.setNameFilters(['SQLite database (*.sqlite)', 'All files (*)'])
        self.currentDbFile = currentDbFile
        self.setDefaultSuffix('sqlite')
        self.selectedFile = selectedFile if selectedFile else currentDbFile
        self.selectedFileInfo = QtCore.QFileInfo(self.selectedFile)
        if QtCore.QDir(self.selectedFileInfo.absolutePath()).exists():
            self.setDirectory(self.selectedFileInfo.absolutePath())
            self.selectFile(self.selectedFileInfo.fileName())
        else:
            self.setDirectory(self._locations[self.Home].toLocalFile())
        self.setSystemUrls(self.Computer|self.Documents|self.Program)

    def errorMessage(self, path):
        QtWidgets.QMessageBox.critical(self, 'Unrecognized file', 
            'You selected an existing file, but it does not seem to be a valid database file.\nAt least for me...', 
            QtWidgets.QMessageBox.Ok)

    def confirm(self, path):
        if not QtCore.QFileInfo(path).exists():
            return True
        conn = sqlite3.connect(path)
        cur = conn.cursor()
        try:
            cur.execute('SELECT name FROM sqlite_master WHERE type="table"')
            format = set(('sounds', 'ascii', 'tags', 'fake_reference', 'reference'))
            tables = set()
            for table in cur.fetchall():
                tables.add(table[0])
            assert format & tables
            return True
        except Exception as e:
            print('Something wrong with the selected file!', e)
            return False


class SettingsDialog(QtWidgets.QDialog):
    midiEvent = QtCore.pyqtSignal(object)
    themeChanged = QtCore.pyqtSignal(object)

    def __init__(self, main, parent):
        QtWidgets.QDialog.__init__(self, parent)
        loadUi('ui/settings.ui', self)
        self.main = main
        self.settings = main.settings
        self.themes = main.themes
#        self.themeSettings = QtCore.QSettings()
        self.themeTab.layout().addWidget(QtWidgets.QWidget(), *self.themeTab.layout().getItemPosition(self.themeTab.layout().indexOf(self.previewWidget)))
        self.themeCombo.currentIndexChanged.connect(self.applyThemeId)
        self.pressedBtn.widget.setDown(True)
        self.pressedBtnDisabled.widget.setDown(True)
        self.themeEditorBtn.clicked.connect(self.showThemeEditor)
        self.detectBtn.clicked.connect(self.midiDetect)
        self.waiter = GlobalsWaiter(self)
        self.broadcastChk.clicked.connect(lambda: self.deviceIdSpin.setValue(127))
        self.deviceIdSpin.valueChanged.connect(lambda value: self.deviceIdLbl.setText('({:02X}h)'.format(value)))
        self.dbPathBtn.clicked.connect(self.changeDbPath)
        self.dbPathRestoreBtn.clicked.connect(self.restoreDbPath)
        self.dbPathEdit.setText = lambda text: QtWidgets.QLineEdit.setText(
            self.dbPathEdit, QtCore.QDir.toNativeSeparators(text))
        self.dbPathEdit.text = lambda: QtCore.QDir.fromNativeSeparators(QtWidgets.QLineEdit.text(self.dbPathEdit))
        if not 'linux' in sys.platform:
            self.alsaBackendRadio.setEnabled(False)
        else:
            self.alsaBackendRadio.setText(self.alsaBackendRadio.text() + ' (recommended)')
        self.backendGroup.setId(self.alsaBackendRadio, 0)
        self.backendGroup.setId(self.rtmidiBackendRadio, 1)

    def restoreDbPath(self):
        defaultDbPath = QtCore.QDir(
            QtGui.QDesktopServices.storageLocation(QtGui.QDesktopServices.DataLocation)).filePath(
                'library.sqlite')
        if self.main.database.path != defaultDbPath:
            question = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Question, 'Restore database path', 
                'Do you want to move the current database to the default location or open/create a new (or possibly existing) one?<br/><br/>' \
                '<b>NOTE</b> changing the database path will require <i>immediate</i> restart of Bigglesworth.', 
                QtWidgets.QMessageBox.Save|QtWidgets.QMessageBox.Open|QtWidgets.QMessageBox.Cancel, self)
            question.button(question.Save).setText('Move')
            question.button(question.Open).setText('Open/create')
            res = question.exec_()
            if res == question.Cancel:
                return
            if res == question.Save:
                self.dbPathMove = True
            else:
                self.dbPathMove = False
            self.dbPathEdit.setText(defaultDbPath)
        else:
            self.dbPathEdit.setText(self.main.database.path)
        self.dbPathRestoreBtn.setEnabled(False)

    def changeDbPath(self):
        question = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Question, 'Change database path', 
            'Do you want to move the existing database or open/create another one?<br/><br/>' \
            '<b>NOTE</b> changing the database path will require <i>immediate</i> restart of Bigglesworth.', 
            QtWidgets.QMessageBox.Save|QtWidgets.QMessageBox.Open|QtWidgets.QMessageBox.Cancel, self)
        question.button(question.Save).setText('Move')
        question.button(question.Open).setText('Open/create')
        res = question.exec_()
        if res == question.Cancel:
            return
        if res == question.Save:
            self.dbPathMove = True
            dialog = MoveDbDialog
        else:
            self.dbPathMove = False
            dialog = OpenDbDialog
        path = dialog(self, self.main.database.path, self.dbPathEdit.text()).exec_()
        if path:
            self.dbPathEdit.setText(path)
            if path != QtCore.QDir(
                QtGui.QDesktopServices.storageLocation(QtGui.QDesktopServices.DataLocation)).filePath(
                    'library.sqlite'):
                        self.dbPathRestoreBtn.setEnabled(True)
            else:
                self.dbPathRestoreBtn.setEnabled(False)


    def midiEventReceived(self, event):
        if event.type == SYSEX:
            sysex_type = event.sysex[4]
            if sysex_type == GLBD:
                self.waiter.accept()
                self.globalsResponse(event.sysex)

    def globalsResponse(self, sysex):
        data = sysex[5:-2]
        channel, deviceId = data[36:38]
        self.inputChannelWidget.setChannels(channel)
        self.outputChannelWidget.setChannels(channel)
        self.deviceIdSpin.setValue(deviceId)

    def midiDetect(self):
        QtCore.QTimer.singleShot(200, lambda: self.midiEvent.emit(SysExEvent(1, [INIT, IDW, IDE, self.main.blofeldId, GLBR, END])))
        res = self.waiter.exec_()
        if (not res or not self.waiter.result()) and not self.waiter.cancelled:
            QtWidgets.QMessageBox.warning(
                self, 
                'Device timeout', 
                'The request has timed out.\nEnsure that the Blofeld is correctly connected to both MIDI input and output ports', 
                QtWidgets.QMessageBox.Ok)

    def showThemeEditor(self):
        oldCurrentTheme = self.themes.current
        oldSelectedTheme = self.themeCombo.itemData(self.themeCombo.currentIndex())
        themeEditor = ThemeEditor(self)
        themeEditor.exec_(self.themeCombo.itemData(self.themeCombo.currentIndex()))
        if themeEditor.changed:
            self.main.themes = self.themes = ThemeCollection(self.main)

            selectedName = oldSelectedTheme.name
            if oldSelectedTheme.name not in ('Dark', 'Light', 'System'):
                if not oldSelectedTheme.name in self.themes.themeList:
                    for themeName in self.themes.themeList:
                        theme = self.themes[themeName]
                        if oldSelectedTheme.uuid == theme.uuid:
                            selectedName = theme.name
                            break
                    else:
                        selectedName = 'Dark'

            emitChanged = False
            if oldSelectedTheme != oldCurrentTheme and oldCurrentTheme.name not in ('Dark', 'Light', 'System'):
                if not oldCurrentTheme.name in self.themes.themeList:
                    for themeName in self.themes.themeList:
                        theme = self.themes[themeName]
                        if oldCurrentTheme.uuid == theme.uuid:
                            self.settings.setValue('theme', theme.name)
                            break
                    else:
                        self.settings.remove('theme')
                    emitChanged = True
                elif oldCurrentTheme != self.themes[oldCurrentTheme.name]:
                    emitChanged = True
            if emitChanged or oldCurrentTheme != self.themes.current:
                self.themeChanged.emit(self.themes.current)

            self.themeCombo.blockSignals(True)
            self.themeCombo.clear()
            self.themeCombo.addItems(self.themes.themeList)
            currentTheme = self.themes[selectedName]
            currentIndex = self.themes.themeList.index(currentTheme.name)
            self.themeCombo.setCurrentIndex(currentIndex)
            self.themeCombo.setItemData(currentIndex, currentTheme)
            self.applyTheme(currentTheme)
            self.themeCombo.blockSignals(False)

    def applyThemeId(self, themeId):
        theme = self.themeCombo.itemData(themeId)
        if not theme:
            theme = self.themes[self.themeCombo.itemText(themeId)]
            self.themeCombo.setItemData(themeId, theme)
        self.applyTheme(theme)

    def applyTheme(self, theme):
        palette = QtGui.QPalette(theme.palette)
        if palette.color(palette.Window) == self.palette().color(palette.Window):
            palette.setColor(palette.Window, QtCore.Qt.transparent)

        self.previewWidget.setPalette(palette)
#        self.previewWidget.setPalette(theme.palette)
        self.previewWidget.setFont(theme.font)
        dialStart, dialZero, dialEnd, dialGradient, dialBgd, dialScale, dialNotches, dialIndicator = theme.dialData
        for child in self.previewWidget.findChildren(Dial):
            child.rangeColorStart = dialStart
            child.rangeColorZero = dialZero
            child.rangeColorEnd = dialEnd
            child.gradientScale = dialGradient
            child.rangePenColor = dialScale
            child.scalePenColor = dialNotches
            child.pointerColor = dialIndicator
        sliderStart, sliderEnd, sliderBgd = theme.sliderData
        for child in self.previewWidget.findChildren(Slider):
            child.rangeColorStart = sliderStart
            child.rangeColorEnd = sliderEnd
            child.background = sliderBgd
        for child in self.previewWidget.findChildren(Combo):
            child.setPalette(theme.palette)
            child.opaque = theme.comboStyle
        for child in self.previewWidget.findChildren(Frame):
            child.borderColor = theme.frameBorderColor
            child.labelColor = theme.frameLabelColor

    def exec_(self):
        self.dbPathMove = False
        self.dbPathEdit.setText(self.main.database.path)
        if self.main.database.path != QtCore.QDir(
            QtGui.QDesktopServices.storageLocation(QtGui.QDesktopServices.DataLocation)).filePath(
                'library.sqlite'):
                    self.dbPathRestoreBtn.setEnabled(True)
        backupInterval = self.settings.value('backupInterval', 5, int)
        self.backupChk.setChecked(backupInterval)
        self.backupIntervalSpin.setValue(backupInterval if backupInterval else 5)
        self.startupSessionCombo.setCurrentIndex(self.settings.value('startupSessionMode', 0, int))
        self.showFirstRunChk.setChecked(not self.settings.value('FirstRunShown', False, bool))
        if self.showFirstRunChk.isChecked():
            self.firstRunSkipBlofeldDetectChk.setChecked(not self.settings.value('FirstRunAutoDetect', True, bool))

        self.settings.beginGroup('MessageBoxes')
        self.restoreMsgBoxBtn.setEnabled(len(self.settings.childKeys()))
        self.settings.endGroup()

        self.settings.beginGroup('MIDI')
        if not 'linux' in sys.platform:
            self.rtmidiBackendRadio.setChecked(True)
        else:
            if not self.main.argparse.rtmidi:
                if self.settings.value('rtmidi', 0, int):
                    self.rtmidiBackendRadio.setChecked(True)
                else:
                    self.alsaBackendRadio.setChecked(True)
            else:
                if not self.settings.value('rtmidi', 0, int):
                    self.backendGroup.setExclusive(False)
                    self.rtmidiBackendRadio.setChecked(False)
                    self.alsaBackendRadio.setChecked(False)
                    self.backendGroup.setExclusive(True)
                else:
                    self.rtmidiBackendRadio.setChecked(True)
        self.deviceIdSpin.setValue(self.main.blofeldId)
        self.autoconnectUsbChk.setChecked(self.settings.value('blofeldDetect', True, bool))
        self.autoconnectRememberChk.setChecked(self.settings.value('tryAutoConnect', True, bool))
        self.settings.endGroup()
        self.inputChannelWidget.setChannels(self.main.chanReceive)
        self.outputChannelWidget.setChannels(self.main.chanSend)

        self.themeCombo.blockSignals(True)
        self.themeCombo.clear()
        self.themeCombo.addItems(self.themes.themeList)
        currentTheme = self.themes.current
        currentIndex = self.themes.themeList.index(currentTheme.name)
        self.themeCombo.setCurrentIndex(currentIndex)
        self.themeCombo.setItemData(currentIndex, currentTheme)
        self.applyTheme(currentTheme)
        self.themeCombo.blockSignals(False)

        res = QtWidgets.QDialog.exec_(self)
        if res:
            restart = False

            if self.restoreMsgBoxBtn.isChecked():
                self.settings.remove('MessageBoxes')

            self.settings.setValue('startupSessionMode', self.startupSessionCombo.currentIndex())
#            self.settings.setValue('theme', self.themes.current.name)
            self.settings.setValue('theme', self.themeCombo.currentText())
            backupInterval = self.backupIntervalSpin.value() if self.backupChk.isChecked() else 0
            self.settings.setValue('backupInterval', backupInterval)
            self.main.database.setBackupInterval(backupInterval)
            self.settings.setValue('FirstRunShown', False if self.showFirstRunChk.isChecked() else True)
            self.settings.setValue('FirstRunAutoDetect', False if self.firstRunSkipBlofeldDetectChk.isChecked() else True)

            self.settings.beginGroup('MIDI')
            self.settings.setValue('blofeldId', self.deviceIdSpin.value())
            self.settings.setValue('blofeldDetect', self.autoconnectUsbChk.isChecked())
            self.settings.setValue('tryAutoConnect', self.autoconnectRememberChk.isChecked())
            self.settings.setValue('chanSend', self.outputChannelWidget.items)
            self.main._chanSend = set(self.outputChannelWidget.items)
            self.settings.setValue('chanReceive', self.inputChannelWidget.items)
            self.main._chanReceive = set(self.inputChannelWidget.items)
            if 'linux' in sys.platform:
                if self.backendGroup.checkedId() >= 0:
                    self.settings.setValue('rtmidi', self.backendGroup.checkedId())
                    if self.main.midiDevice.backend != self.backendGroup.checkedId():
                        restart = True
            self.settings.endGroup()

            if self.dbPathEdit.text() != self.main.database.path:
                if self.dbPathMove:
                    QtCore.QFile(self.main.database.path).copy(self.dbPathEdit.text())
                self.settings.setValue('dbPath', self.dbPathEdit.text())
                QtWidgets.QMessageBox.warning(self, 'Restarting Bigglesworth', 
                    'Bigglesworth will now be restarted, press "Ok" to continue.', 
                    QtWidgets.QMessageBox.Ok)
                restart = True
            self.settings.sync()
            if restart:
                QtWidgets.QApplication.instance().restart()
        return res

    def keyPressEvent(self, event):
        if event.matches(QtGui.QKeySequence.NextChild):
            self.tabWidget.setCurrentIndex(self.tabWidget.currentIndex() + 1)
        elif event.matches(QtGui.QKeySequence.PreviousChild):
            self.tabWidget.setCurrentIndex(self.tabWidget.currentIndex() - 1)
        QtWidgets.QDialog.keyPressEvent(self, event)


