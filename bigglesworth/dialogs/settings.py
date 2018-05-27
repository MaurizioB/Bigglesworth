from Qt import QtCore, QtGui, QtWidgets

from dial import Dial
from combo import Combo
from slider import Slider
from frame import Frame

from bigglesworth.utils import loadUi
from bigglesworth.themes import ThemeCollection
from bigglesworth.midiutils import SysExEvent, SYSEX, GLBD, INIT, IDW, IDE, GLBR, END
from bigglesworth.dialogs import ThemeEditor, GlobalsWaiter

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
        self.backupPathEdit.setText(self.main.database.path)
        backupInterval = self.settings.value('backupInterval', 5, int)
        self.backupChk.setChecked(backupInterval)
        self.backupIntervalSpin.setValue(backupInterval if backupInterval else 5)
        self.startupSessionCombo.setCurrentIndex(self.settings.value('startupSessionMode', 0, int))

        self.settings.beginGroup('MIDI')
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
            self.settings.setValue('startupSessionMode', self.startupSessionCombo.currentIndex())
            self.settings.setValue('theme', self.themes.current.name)
            backupInterval = self.backupIntervalSpin.value() if self.backupChk.isChecked() else 0
            self.settings.setValue('backupInterval', backupInterval)
            self.main.database.setBackupInterval(backupInterval)

            self.settings.beginGroup('MIDI')
            self.settings.setValue('blofeldId', self.deviceIdSpin.value())
            self.settings.setValue('blofeldDetect', self.autoconnectUsbChk.isChecked())
            self.settings.setValue('tryAutoConnect', self.autoconnectRememberChk.isChecked())
            self.settings.setValue('chanSend', self.outputChannelWidget.items)
            self.main._chanSend = set(self.outputChannelWidget.items)
            self.settings.setValue('chanReceive', self.inputChannelWidget.items)
            self.main._chanReceive = set(self.inputChannelWidget.items)
            self.settings.endGroup()
            self.settings.sync()

        return res
