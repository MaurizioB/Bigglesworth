import re

from Qt import QtCore, QtGui, QtWidgets

from dial import Dial
from combo import Combo
from slider import Slider
from frame import Frame
from colorselectbutton import ColorSelectButton

from bigglesworth.utils import loadUi
from bigglesworth.themes import Theme, ThemeCollection

Stored = QtCore.Qt.UserRole + 1
Dirty = Stored + 1

_mnemonics = re.compile('(?<!&)&(?!&)')

class RenameDialog(QtWidgets.QDialog):
    def __init__(self, parent, name):
        QtWidgets.QDialog.__init__(self, parent)
        self.name = name
        self.setWindowTitle('Theme name')
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        self.lineEdit = QtWidgets.QLineEdit(name)
        layout.addWidget(self.lineEdit)
        self.lineEdit.setMaxLength(16)
        self.lineEdit.textChanged.connect(self.checkName)
        self.lineEdit.setValidator(QtGui.QRegExpValidator(QtCore.QRegExp(r'^[a-zA-Z\ 0-9\(\)\[\]\{\}\-]+$')))

        self.buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok|QtWidgets.QDialogButtonBox.Cancel)
        layout.addWidget(self.buttonBox)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

    def checkName(self, name):
        if name == self.name:
            valid = True
        elif not name or not name.strip() or name.strip() in self.parent().themes.themeList:
            valid = False
        else:
            valid = True
        self.buttonBox.button(self.buttonBox.Ok).setEnabled(valid)

    def exec_(self):
        res = QtWidgets.QDialog.exec_(self)
        if not res:
            return
        return self.lineEdit.text().strip()


class ThemeEditor(QtWidgets.QDialog):
    def __init__(self, parent):
        QtWidgets.QDialog.__init__(self, parent)
        loadUi('ui/themeeditor.ui', self)
        self.main = parent.main
        self.settings = parent.settings
        self.themes = ThemeCollection(self.main)
        self.themeCombo.currentIndexChanged.connect(self.applyThemeId)
        self.copyBtn.clicked.connect(self.copyTheme)
        self.renameBtn.clicked.connect(self.rename)
        self.currentTheme = None
        self.changed = False
        self.saveBtn.clicked.connect(self.save)
        self.restoreBtn.clicked.connect(self.restore)
        self.deleteBtn.clicked.connect(self.delete)

        self.combo.setDisabledItems(self.combo.combo.count() - 1)
        self.pressedBtnEnabled.button.setDown(True)
        self.pressedBtnDisabled.button.setDown(True)
        self.switchableBtnEnabled.switchToggled.connect(lambda state: setattr(self.switchableBtnEnabled, 'insideText', ('Off', 'On')[state]))
        self.switchableBtnDisabled.switchToggled.connect(lambda state: setattr(self.switchableBtnDisabled, 'insideText', ('Off', 'On')[state]))

        self.buddies = {}
        for label in self.findChildren(QtWidgets.QLabel):
            widget = label.buddy()
            if widget:
                self.buddies[widget] = label

        self.colorButtons = {
            self.windowBgdColorBtn: QtGui.QPalette.Window, 
            self.fontColorBtn: QtGui.QPalette.WindowText, 
            self.lightBorderColorBtn: QtGui.QPalette.Midlight, 
            self.darkBorderColorBtn: QtGui.QPalette.Dark, 
            self.frameBorderColorBtn: 'frameBorderColor', 
            self.frameLabelColorBtn: 'frameLabelColor', 
            self.itemColorBtn: QtGui.QPalette.Text, 
            self.itemBgdColorBtn: QtGui.QPalette.Base, 
            self.highlightColorBtn: QtGui.QPalette.HighlightedText, 
            self.highlightBgdColorBtn: QtGui.QPalette.Highlight, 
            self.normalButtonColorBtn: (QtGui.QPalette.Inactive, QtGui.QPalette.Button), 
            self.activeButtonColorBtn: (QtGui.QPalette.Active, QtGui.QPalette.Button), 
            self.dialZeroBtn: 'dialZero', 
            self.dialStartBtn: 'dialStart', 
            self.dialEndBtn: 'dialEnd', 
            self.dialBgdBtn: 'dialBgd', 
            self.dialIndicatorColorBtn: 'dialIndicator', 
            self.dialNotchesColorBtn: 'dialNotches', 
            self.dialScaleColorBtn: 'dialScale', 
            self.sliderBgdColorBtn: 'sliderBgd', 
            self.sliderStartColorBtn: 'sliderStart', 
            self.sliderEndColorBtn: 'sliderEnd', 
            }
#        for colorButton in self.findChildren(ColorSelectButton):
        for colorButton, attr in self.colorButtons.items():
#            self.colorButtons.append(colorButton)
            colorButton.colorAttr = attr

            systemRestoreAction = QtWidgets.QAction(QtGui.QIcon.fromTheme('edit-undo'), 'Use system default', colorButton)
            systemRestoreAction.triggered.connect(self.systemColorRestore)
            themeRestoreAction = QtWidgets.QAction(QtGui.QIcon.fromTheme('edit-undo'), 'Restore saved color', colorButton)
            themeRestoreAction.triggered.connect(self.themeColorRestore)
            colorButton.colorMenu.insertSeparator(colorButton.colorMenu.actions()[0])
            colorButton.colorMenu.insertAction(colorButton.colorMenu.actions()[0], systemRestoreAction)
            colorButton.colorMenu.insertAction(colorButton.colorMenu.actions()[0], themeRestoreAction)

            try:
                label = self.buddies[colorButton]
                colorButton.colorRole = _mnemonics.sub('', self.buddies[colorButton].text())
            except:
                #add support for dialStartBtn
                pass

        self.windowBgdColorBtn.colorChanged.connect(self.updateBackground)
        self.fontColorBtn.colorChanged.connect(self.updateWindowText)

        self.fontCombo.currentFontChanged.connect(self.updateFont)
        self.fontSizeSpin.valueChanged.connect(self.updateFont)
        self.fontBoldChk.toggled.connect(self.updateFont)
        self.fontItalicChk.toggled.connect(self.updateFont)

        self.lightBorderColorBtn.colorChanged.connect(self.updateLightBorder)
        self.darkBorderColorBtn.colorChanged.connect(self.updateDarkBorder)

        self.frameBorderColorBtn.colorChanged.connect(self.updateFrameBorder)
        self.frameLabelColorBtn.colorChanged.connect(self.updateFrameLabel)

        self.comboStyleCombo.currentIndexChanged.connect(self.updateCombo)
        self.itemColorBtn.colorChanged.connect(self.updateItemColor)
        self.itemBgdColorBtn.colorChanged.connect(self.updateItemBgdColor)
        self.highlightColorBtn.colorChanged.connect(self.updateItemHighlightColor)
        self.highlightBgdColorBtn.colorChanged.connect(self.updateItemHighlightBgdColor)

        self.normalButtonColorBtn.colorChanged.connect(self.updateNormalButton)
        self.activeButtonColorBtn.colorChanged.connect(self.updateActiveButton)

        self.dialZeroBtn.colorChanged.connect(self.updateDialZero)
        self.dialEndBtn.colorChanged.connect(self.updateDialEnd)
        self.linkDialColorsChk.toggled.connect(self.checkDialZero)
        self.dialStartBtn.colorChanged.connect(self.updateDialStart)
        self.dialBgdBtn.colorChanged.connect(self.updateDialColor)
        self.dialIndicatorColorBtn.colorChanged.connect(self.updateDialPointerColor)
        self.dialScaleColorBtn.colorChanged.connect(self.updateDialScaleColor)
        self.dialNotchesColorBtn.colorChanged.connect(self.updateDialNotchesColor)

        self.sliderBgdColorBtn.colorChanged.connect(self.updateSliderBgdColor)
        self.linkSlidersToDialsChk.toggled.connect(self.checkSliderColors)
        self.sliderStartColorBtn.colorChanged.connect(self.updateSliderStartColor)
        self.sliderEndColorBtn.colorChanged.connect(self.updateSliderEndColor)

        self.step8Dial = 1
        self.stepFullDial = 1
        self.step8Timer = QtCore.QTimer(self)
        self.step8Timer.setInterval(250)
        self.step8Timer.timeout.connect(self.step8Dials)
        self.stepFullTimer = QtCore.QTimer(self)
        self.stepFullTimer.setInterval(50)
        self.stepFullTimer.timeout.connect(self.stepFullDials)
        self.animateBtn.toggled.connect(self.startTimers)
        self.startTimers()

    def startTimers(self, state=True):
        if state:
            self.step8Timer.start()
            self.stepFullTimer.start()
        else:
            self.step8Timer.stop()
            self.stepFullTimer.stop()

    def step8Dials(self):
        if self.dial1Normal.value >= self.dial1Normal.maximum:
            self.step8Dial = -1
        elif self.dial1Normal.value <= self.dial1Normal.minimum:
            self.step8Dial = 1
        self.dial1Normal.widget.stepBy(self.step8Dial)

    def stepFullDials(self):
        try:
            if self.dial2Normal.value >= self.dial2Normal.maximum:
                self.stepFullDial = -1
            elif self.dial2Normal.value <= self.dial2Normal.minimum:
                self.stepFullDial = 1
            self.dial2Normal.widget.stepBy(self.stepFullDial)
            self.dial3Normal.widget.stepBy(self.stepFullDial)
            self.sliderEnabled.setValue(self.dial2Normal.value)
            self.sliderDisabled.setValue(self.dial2Normal.value)
        except Exception as e:
            print(e)

    def systemColorRestore(self):
        button = self.sender().parent()
        attr = button.colorAttr
        if isinstance(attr, tuple):
            color = self.themes['System'].color(*attr)
        else:
            color = self.themes['System'].color(attr)
        button.updateColor(color)

    def themeColorRestore(self):
        button = self.sender().parent()
        attr = button.colorAttr
        if isinstance(attr, tuple):
            color = self.themeCombo.itemData(self.themeCombo.currentIndex(), Stored).color(*attr)
        else:
            color = self.themeCombo.itemData(self.themeCombo.currentIndex(), Stored).color(attr)
        button.updateColor(color)

    def updateBackground(self, newColor, oldColor):
        self.currentTheme.setColor(QtGui.QPalette.Window, newColor)

    def updateWindowText(self, newColor, oldColor):
        self.currentTheme.setColor(QtGui.QPalette.WindowText, newColor)
        newColor.setAlpha(newColor.alpha() * .8)
        self.currentTheme.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.WindowText, newColor)

    def updateFont(self, *args):
        font = self.fontCombo.currentFont()
        font.setPointSize(self.fontSizeSpin.value())
        font.setBold(self.fontBoldChk.isChecked())
        font.setItalic(self.fontItalicChk.isChecked())
        self.currentTheme.font = font

    def updateLightBorder(self, newColor, oldColor):
        self.currentTheme.setColor(QtGui.QPalette.Midlight, newColor)

    def updateDarkBorder(self, newColor, oldColor):
        self.currentTheme.setColor(QtGui.QPalette.Dark, newColor)

    def updateFrameBorder(self, newColor, oldColor):
        self.currentTheme.frameBorderColor = newColor

    def updateFrameLabel(self, newColor, oldColor):
        self.currentTheme.frameLabelColor = newColor

    def updateCombo(self, mode):
        self.currentTheme.comboStyle = bool(mode)

    def updateItemColor(self, newColor, oldColor):
        self.currentTheme.setColor(QtGui.QPalette.Text, newColor)
        newColor.setAlpha(newColor.alpha() * .8)
        self.currentTheme.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.Text, newColor)

    def updateItemBgdColor(self, newColor, oldColor):
        self.currentTheme.setColor(QtGui.QPalette.Base, newColor)
        newColor.setAlpha(newColor.alpha() * .8)
        self.currentTheme.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.Base, newColor)

    def updateItemHighlightColor(self, newColor, oldColor):
        self.currentTheme.setColor(QtGui.QPalette.HighlightedText, newColor)
        newColor.setAlpha(newColor.alpha() * .8)
        self.currentTheme.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.HighlightedText, newColor)

    def updateItemHighlightBgdColor(self, newColor, oldColor):
        self.currentTheme.setColor(QtGui.QPalette.Highlight, newColor)
        newColor.setAlpha(newColor.alpha() * .8)
        self.currentTheme.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.Highlight, newColor)

    def updateNormalButton(self, newColor, oldColor):
        self.currentTheme.setColor(QtGui.QPalette.Inactive, QtGui.QPalette.Button, newColor)
        newColor.setAlpha(newColor.alpha() * .8)
        self.currentTheme.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.Button, newColor)

    def updateActiveButton(self, newColor, oldColor):
        self.currentTheme.setColor(QtGui.QPalette.Active, QtGui.QPalette.Button, newColor)

    def updateDialZero(self, newColor, oldColor):
        self.currentTheme.dialZero = newColor
        if self.linkSlidersToDialsChk.isChecked():
            self.currentTheme.sliderStart = newColor
        self.currentTheme.changed.emit(self.currentTheme)

    def updateDialEnd(self, newColor, oldColor):
        self.currentTheme.dialEnd = newColor
        if not self.linkDialColorsChk.isChecked():
            self.currentTheme.dialStart = newColor
        if self.linkSlidersToDialsChk.isChecked():
            self.currentTheme.sliderEnd = newColor
        self.currentTheme.changed.emit(self.currentTheme)

    def checkDialZero(self, state):
        if not state:
            self.dialStartBtn.color = self.dialEndBtn.color

    def updateDialStart(self, newColor, oldColor):
        self.currentTheme.dialStart = newColor
        self.currentTheme.changed.emit(self.currentTheme)

    def updateDialColor(self, newColor, oldColor):
        self.currentTheme.setColor(QtGui.QPalette.Mid, newColor)
        newColor.setAlpha(newColor.alpha() * .8)
        self.currentTheme.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.Mid, newColor)

    def updateDialPointerColor(self, newColor, oldColor):
        self.currentTheme.dialIndicator = newColor
        self.currentTheme.changed.emit(self.currentTheme)

    def updateDialScaleColor(self, newColor, oldColor):
        self.currentTheme.dialScale = newColor
        self.currentTheme.changed.emit(self.currentTheme)

    def updateDialNotchesColor(self, newColor, oldColor):
        self.currentTheme.dialNotches = newColor
        self.currentTheme.changed.emit(self.currentTheme)

    def updateSliderBgdColor(self, newColor, oldColor):
        self.currentTheme.sliderBgd = newColor
        self.currentTheme.changed.emit(self.currentTheme)

    def checkSliderColors(self, state):
        if not state:
            self.sliderStartColorBtn.color = self.dialZeroBtn.color
            self.sliderEndColorBtn.color = self.dialEndBtn.color

    def updateSliderStartColor(self, newColor, oldColor):
        self.currentTheme.sliderStart = newColor
        self.currentTheme.changed.emit(self.currentTheme)

    def updateSliderEndColor(self, newColor, oldColor):
        self.currentTheme.sliderEnd = newColor
        self.currentTheme.changed.emit(self.currentTheme)

    def applyThemeId(self, themeId):
        if self.currentTheme:
            self.currentTheme.changed.disconnect(self.setDirty)
            self.currentTheme.changed.disconnect(self.applyTheme)
        theme = self.themeCombo.itemData(themeId)
        if not theme:
            theme = self.themes[self.themeCombo.itemText(themeId)]
            self.themeCombo.setItemData(themeId, theme)
            storedTheme = Theme(theme)
            storedTheme.setParent(self)
            self.themeCombo.setItemData(themeId, storedTheme, Stored)
        if theme.name in ('Dark', 'Light', 'System'):
            mode = False
        else:
            mode = True
        self.themeTabWidget.setEnabled(mode)
        self.renameBtn.setEnabled(mode)
        self.deleteBtn.setEnabled(mode)
        if mode and not self.themeCombo.itemData(themeId, Dirty):
            mode = False
        self.saveBtn.setEnabled(mode)
        self.restoreBtn.setEnabled(mode)

        theme.changed.connect(self.setDirty)
        theme.changed.connect(self.applyTheme)
        self.currentTheme = theme
        self.applyTheme(theme, True)

    def applyTheme(self, theme, changed=False):
        palette = QtGui.QPalette(theme.palette)
        if palette.color(palette.Window) == self.palette().color(palette.Window):
            palette.setColor(palette.Window, QtCore.Qt.transparent)

        self.previewWidget.setPalette(palette)
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

#        palette, font, dialData, sliderData, comboStyle = theme.data()
        dialStart, dialZero, dialEnd, dialGradient, dialBgd, dialScale, dialNotches, dialIndicator = theme.dialData
        sliderStart, sliderEnd, sliderBgd = theme.sliderData
        widgetList = self.colorButtons.keys() + [
                self.fontCombo, self.fontSizeSpin, self.fontBoldChk, self.fontItalicChk, 
                self.linkDialColorsChk, self.linkSlidersToDialsChk, 
                self.comboStyleCombo
                ]
        for widget in widgetList:
            widget.blockSignals(True)

        self.windowBgdColorBtn.updateColor(theme.palette.color(palette.Window))
        self.darkBorderColorBtn.updateColor(palette.color(palette.Dark))
        self.lightBorderColorBtn.updateColor(palette.color(palette.Midlight))
        self.comboStyleCombo.setCurrentIndex(theme.comboStyle)

        self.fontColorBtn.updateColor(palette.color(palette.WindowText))
        self.fontCombo.setCurrentFont(theme.font)
        self.fontSizeSpin.setValue(theme.font.pointSize())
        self.fontBoldChk.setChecked(theme.font.bold())
        self.fontItalicChk.setChecked(theme.font.italic())

        self.itemColorBtn.updateColor(palette.color(palette.Text))
        self.itemBgdColorBtn.updateColor(palette.color(palette.Base))
        self.highlightColorBtn.updateColor(palette.color(palette.HighlightedText))
        self.highlightBgdColorBtn.updateColor(palette.color(palette.Highlight))

        self.frameBorderColorBtn.updateColor(theme.frameBorderColor)
        self.frameLabelColorBtn.updateColor(theme.frameLabelColor)

        self.normalButtonColorBtn.updateColor(palette.color(palette.Inactive, palette.Button))
        self.activeButtonColorBtn.updateColor(palette.color(palette.Active, palette.Button))

        if dialStart == dialEnd and changed:
            self.linkDialColorsChk.setChecked(False)
        self.dialStartBtn.updateColor(dialStart)
        self.dialZeroBtn.updateColor(dialZero)
        self.dialEndBtn.updateColor(dialEnd)
        self.dialBgdBtn.updateColor(dialBgd)
        self.dialScaleColorBtn.updateColor(dialScale)
        self.dialNotchesColorBtn.updateColor(dialNotches)
        self.dialIndicatorColorBtn.updateColor(dialIndicator)

        if (sliderStart == dialZero) and (sliderEnd == dialEnd) and changed:
            self.linkSlidersToDialsChk.setChecked(True)
        self.sliderStartColorBtn.updateColor(sliderStart)
        self.sliderEndColorBtn.updateColor(sliderEnd)
        self.sliderBgdColorBtn.updateColor(sliderBgd)

        for widget in widgetList:
            widget.blockSignals(False)

    def setDirty(self, *args):
        self.themeCombo.setItemData(self.themeCombo.currentIndex(), True, Dirty)
        self.saveBtn.setEnabled(True)
        self.restoreBtn.setEnabled(True)

    def save(self):
        currentIndex = self.themeCombo.currentIndex()
        oldStoredTheme = self.themeCombo.itemData(currentIndex)
        oldStoredTheme.deleteLater()
        storedTheme = Theme(self.currentTheme)
        storedTheme.setParent(self)
        self.themeCombo.setItemData(currentIndex, storedTheme, Stored)
        self.themeCombo.setItemData(currentIndex, False, Dirty)
        self.saveBtn.setEnabled(False)
        self.restoreBtn.setEnabled(False)
        self.themes.saveTheme(self.currentTheme)
        self.changed = True

    def restore(self):
        currentIndex = self.themeCombo.currentIndex()
        oldStoredTheme = self.themeCombo.itemData(currentIndex, Stored)
        self.currentTheme.setData(oldStoredTheme.data())
        self.currentTheme.changed.emit(self.currentTheme)
        self.themeCombo.setItemData(currentIndex, False, Dirty)
        self.saveBtn.setEnabled(False)
        self.restoreBtn.setEnabled(False)

    def delete(self):
        res = QtWidgets.QMessageBox.question(
            self, 
            'Delete theme?', 
            'Are you sure you want to delete the theme "{}"?'.format(self.currentTheme.name), 
            QtWidgets.QMessageBox.Ok|QtWidgets.QMessageBox.Cancel)
        if res != QtWidgets.QMessageBox.Ok:
            return
#        currentIndex = self.themeCombo.currentIndex()
        self.themes.deleteTheme(self.currentTheme.name)
        self.themeCombo.removeItem(self.themeCombo.currentIndex())

    def copyTheme(self):
        theme = self.themeCombo.itemData(self.themeCombo.currentIndex())
        name = RenameDialog(self, theme.name + ' copy').exec_()
        if not name:
            return
        newTheme = self.themes.createTheme(name, theme)
#        newTheme = Theme(name, theme)
        self.themeCombo.addItem(name, newTheme)
        self.themeCombo.setCurrentIndex(self.themeCombo.count() - 1)
#        self.themes.themeDict[name] = newTheme
#        self.themes.themeList.append(name)
        self.renameBtn.setEnabled(True)
        self.deleteBtn.setEnabled(True)
        self.changed = True

    def rename(self):
        oldName = self.themeCombo.currentText()
        newName = RenameDialog(self, oldName).exec_()
        if not newName:
            return
        currentIndex = self.themeCombo.currentIndex()
        self.themeCombo.setItemText(currentIndex, newName)
        self.themes.renameTheme(oldName, newName)
        self.changed = True
#        theme = self.themes.themeDict.pop(oldName)
#        self.themes.themeDict[newName] = theme
#        self.themes.themeList.pop(self.themes.themeList.index(oldName))
#        self.themes.themeList.append(newName)

    def closeEvent(self, event):
        if not self.closeCheck():
            event.ignore()

    def reject(self):
        if self.closeCheck():
            QtWidgets.QDialog.reject(self)

    def closeCheck(self):
        dirty = []
        for index in range(self.themeCombo.count()):
            if self.themeCombo.itemData(index, Dirty):
                dirty.append(self.themeCombo.itemData(index))
        if not dirty:
            return True
        res = QtWidgets.QMessageBox.question(
            self, 
            'Unsaved themes', 
            'Some themes have not been saved.\nHow do you want to proceed?', 
            QtWidgets.QMessageBox.Save|QtWidgets.QMessageBox.Discard|QtWidgets.QMessageBox.Cancel
            )
        if res == QtWidgets.QMessageBox.Cancel:
            return False
        elif res == QtWidgets.QMessageBox.Save:
            for theme in dirty:
                self.themes.saveTheme(theme)
            self.changed = True
        return True

    def exec_(self, theme):
        self.themeCombo.blockSignals(True)
        self.themeCombo.clear()
        for index, themeName in enumerate(self.themes.themeList):
            self.themeCombo.addItem(themeName)
#            self.themeCombo.setItemData(index, False, Dirty)
        currentIndex = self.themes.themeList.index(theme.name)
        self.themeCombo.blockSignals(False)
        self.themeCombo.setCurrentIndex(currentIndex)
        self.themeCombo.currentIndexChanged.emit(currentIndex)
        return QtWidgets.QDialog.exec_(self)
        
