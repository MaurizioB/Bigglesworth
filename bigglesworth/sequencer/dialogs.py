import os

os.environ['QT_PREFERRED_BINDING'] = 'PyQt4'

from Qt import QtCore, QtGui, QtWidgets

from bigglesworth.utils import loadUi
from bigglesworth.sequencer.const import (ValidMappingRole, ParameterRole, QuantizeRole, 
    SnapModes, DefaultNoteSnapModeId, 
    Mappings, CtrlParameter, SysExParameter, getCtrlNameFromMapping)
from bigglesworth.sequencer.structure import RegionInfo, MetaRegion


class QuantizeDialog(QtWidgets.QDialog):
    def __init__(self, parent):
        QtWidgets.QDialog.__init__(self, parent)
        loadUi('ui/quantizeevents.ui', self)
        index = 0
        for snapMode in SnapModes:
            if not snapMode.numerator:
                continue
            for combo in (self.noteStartCombo, self.noteEndCombo, self.noteLengthCombo, self.otherCombo):
                combo.addItem(snapMode.icon, snapMode.label)
                combo.setItemData(index, (snapMode.numerator, snapMode.denominator), QuantizeRole)
            index += 1
        for combo in (self.noteStartCombo, self.noteEndCombo, self.noteLengthCombo, self.otherCombo):
            combo.setCurrentIndex(DefaultNoteSnapModeId)

        self.noteStartChk.toggled.connect(self.checkTimingToggle)
        self.noteEndChk.toggled.connect(self.checkTimingToggle)
        self.lockStartEndBtn.toggled.connect(self.checkTimings)
        self.noteStartCombo.currentIndexChanged.connect(self.checkTimings)
        self.noteEndCombo.currentIndexChanged.connect(self.checkTimings)
        self.noteLengthRadio.toggled.connect(lambda s: self.otherGroupBox.setEnabled(self.hasOther and not s))
        self.otherAsNoteRadio.toggled.connect(self.checkOtherTimings)
        self.buttonBox.button(self.buttonBox.Ok).setText('Quantize')

    def checkTimingToggle(self):
        if not any((self.noteStartChk.isChecked(), self.noteEndChk.isChecked())):
            if self.sender() == self.noteEndChk:
                index = self.noteStartCombo.currentIndex()
                target = self.noteStartChk
            else:
                index = self.noteEndCombo.currentIndex()
                target = self.noteEndChk
            target.toggled.disconnect(self.checkTimingToggle)
            target.setChecked(True)
            target.toggled.connect(self.checkTimingToggle)
            self.lockStartEndBtn.setEnabled(False)
            if self.otherAsNoteRadio.isChecked():
                self.otherCombo.setCurrentIndex(index)
        elif all((self.noteStartChk.isChecked(), self.noteEndChk.isChecked())):
            self.lockStartEndBtn.setEnabled(True)
            if self.sender() == self.noteEndChk:
                target = self.noteEndCombo
            else:
                index = self.noteStartCombo.currentIndex()
                target = self.noteStartCombo
            if self.lockStartEndBtn.isChecked():
                target.blockSignals(True)
                target.setCurrentIndex(index)
                target.blockSignals(False)
            if target == self.noteStartCombo and self.otherAsNoteRadio.isChecked():
                self.otherCombo.setCurrentIndex(index)
        else:
            self.lockStartEndBtn.setEnabled(False)
            if self.otherAsNoteRadio.isChecked():
                if self.noteEndChk.isChecked():
                    self.otherCombo.setCurrentIndex(self.noteEndCombo.currentIndex())
                else:
                    self.otherCombo.setCurrentIndex(self.noteStartCombo.currentIndex())

    def checkTimings(self):
        if not all((self.lockStartEndBtn.isChecked(), self.noteStartChk.isChecked(), self.noteEndChk.isChecked())):
            return
        if self.sender() == self.lockStartEndBtn:
            self.noteEndCombo.setCurrentIndex(self.noteStartCombo.currentIndex())
        else:
            if self.sender() == self.noteStartCombo:
                index = self.noteStartCombo.currentIndex()
                target = self.noteEndCombo
            else:
                index = self.noteEndCombo.currentIndex()
                target = self.noteStartCombo
            target.blockSignals(True)
            target.setCurrentIndex(index)
            target.blockSignals(False)

    def checkOtherTimings(self, state):
        if state:
            if self.noteStartChk.isChecked():
                self.otherCombo.setCurrentIndex(self.noteStartCombo.currentIndex())
            else:
                self.otherCombo.setCurrentIndex(self.noteEndCombo.currentIndex())

    def exec_(self, hasNotes=False, hasOther=False, patternMode=False):
        self.hasOther = hasOther
        self.noteGroupBox.setEnabled(hasNotes)
        self.otherGroupBox.setEnabled(hasOther)
        if patternMode:
            self.quantizeRegionCombo.setEnabled(False)
            self.quantizeRegionCombo.setCurrentIndex(2)
        if QtWidgets.QDialog.exec_(self):
            quantizeMode = 0
            if hasNotes:
                if self.noteTimeRadio.isChecked():
                    if self.noteStartChk.isChecked():
                        quantizeMode |= MetaRegion.QuantizeNoteStart
                    if self.noteEndChk.isChecked():
                        quantizeMode |= MetaRegion.QuantizeNoteEnd
                    startRatio = self.noteStartCombo.itemData(self.noteStartCombo.currentIndex(), QuantizeRole)
                    endRatio = self.noteEndCombo.itemData(self.noteEndCombo.currentIndex(), QuantizeRole)
                else:
                    quantizeMode |= MetaRegion.QuantizeNoteLength
                    startRatio = None
                    endRatio = self.noteLengthCombo.itemData(self.noteLengthCombo.currentIndex(), QuantizeRole)
            else:
                startRatio = endRatio = None
            if hasOther:
                quantizeMode |= MetaRegion.QuantizeCtrl
                otherRatio = self.otherCombo.itemData(self.otherCombo.currentIndex(), QuantizeRole)
            else:
                otherRatio = None
            return startRatio, endRatio, otherRatio, quantizeMode


class AddTracksDialog(QtWidgets.QDialog):
    def __init__(self, parent, single):
        QtWidgets.QDialog.__init__(self, parent)
        self.setWindowTitle('Add track{}'.format('' if single else 's'))
        self.structure = parent.structure
        self.single = single

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        self.countSpin = QtWidgets.QSpinBox()
        if single:
            self.countSpin.setValue(1)
        else:
            countLayout = QtWidgets.QHBoxLayout()
            layout.addLayout(countLayout)
            countLayout.addWidget(QtWidgets.QLabel('No. of tracks:'))
            countLayout.addWidget(self.countSpin)
            self.countSpin.setRange(1, 16 - self.structure.trackCount())

        labelLayout = QtWidgets.QHBoxLayout()
        layout.addLayout(labelLayout)
        labelLayout.addWidget(QtWidgets.QLabel('Label:'))
        self.labelEdit = QtWidgets.QLineEdit('')
        labelLayout.addWidget(self.labelEdit)
        self.labelEdit.setMaxLength(16)

        chanLayout = QtWidgets.QHBoxLayout()
        layout.addLayout(chanLayout)
        chanLayout.addWidget(QtWidgets.QLabel('Default channel:'))
        self.channelCombo = QtWidgets.QComboBox()
        chanLayout.addWidget(self.channelCombo)
        self.channelCombo.addItems(['Auto'] + [str(c) for c in range(1, 17)])
        self.channelCombo.currentIndexChanged.connect(self.channelChanged)
        self.labelEdit.setText('Track {}'.format(self.structure.trackCount() + 1))

        self.buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok|QtWidgets.QDialogButtonBox.Cancel)
        layout.addWidget(self.buttonBox)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

    def channelChanged(self, channel):
        if self.countSpin.value() > 1:
            return
        currentText = self.labelEdit.text()
        splitted = currentText.strip().split()
        if channel and (not currentText or len(splitted) > 1 and splitted[-1].isdigit()):
            self.labelEdit.setText('{} {}'.format(' '.join(splitted[:-1]), channel))

    def exec_(self):
        res = QtWidgets.QDialog.exec_(self)
        if res:
            return self.countSpin.value(), self.labelEdit.text().strip(), self.channelCombo.currentIndex() - 1



class MappingProxyModel(QtCore.QSortFilterProxyModel):
    filter = 0
    def setFilter(self, filter):
        self.filter = 2 if filter else 0
        self.invalidateFilter()

    def filterAcceptsRow(self, row, parent=None):
        return self.sourceModel().index(row, 0).data(ValidMappingRole) >= self.filter


class AddAutomationDialog(QtWidgets.QDialog):
    def __init__(self, parent, existing=None):
        QtWidgets.QDialog.__init__(self, parent)
        loadUi('ui/sequenceraddautomationdialog.ui', self)
        self.existing = set(existing if existing is not None else [])
        self.mappingCombo.addItem(QtGui.QIcon.fromTheme('blofeld-b'), 'Blofeld')
        self.mappingCombo.setItemData(0, 'Blofeld')
        for mappingName in Mappings.keys():
            if mappingName == 'Blofeld':
                continue
            self.mappingCombo.addItem(mappingName)
            self.mappingCombo.setItemData(self.mappingCombo.count() - 1, mappingName)
        if self.mappingCombo.count() <= 1:
            self.mappingCombo.setEnabled(False)

        self.mappingCombo.currentIndexChanged.connect(self.setMapping)
        #required to avoid font propagation
        self.ctrlList = QtWidgets.QListView()
        self.ctrlCombo.setView(self.ctrlList)
        self.ctrlCombo.setStyleSheet('''
                QListView {
                    font-weight: normal;
                }
        ''')
        self.ctrlCombo.currentIndexChanged.connect(self.setCtrlStyle)
        self.validMappingChk.toggled.connect(self.toggleValidMapping)
        self.parameterTypeGroup.setId(self.ctrlRadio, CtrlParameter)
        self.parameterTypeGroup.setId(self.sysExRadio, SysExParameter)

        self.mappingModels = {}

#        #get only existing CtrlParameter automations
#        self.existing = [a[1] for a in self.track.automations(CtrlParameter)]

        self.setMapping(0)
        self.validMappingLbl.installEventFilter(self)
#        self.validMappingChk.setChecked(True)

    def setCtrlStyle(self, index):
        try:
            self.ctrlCombo.setFont(self.ctrlCombo.itemData(index, QtCore.Qt.FontRole))
        except:
            self.ctrlCombo.setFont(self.font())

    def setMapping(self, index):
        prevIndex = self.ctrlCombo.currentIndex()
        if prevIndex >= 0:
            prevCtrl = self.ctrlCombo.itemData(prevIndex, ParameterRole)
        else:
            prevCtrl = None
        mapping = self.mappingCombo.itemData(index)
        self.ctrlCombo.currentIndexChanged.disconnect(self.setCtrlStyle)
        try:
            proxyModel = self.mappingModels[mapping]
        except:
            sourceModel = QtGui.QStandardItemModel()
            proxyModel = MappingProxyModel()
            proxyModel.setSourceModel(sourceModel)
            self.mappingModels[mapping] = proxyModel
            validFont = self.font()
            validFont.setBold(True)
            unmapFont = self.font()
            unmapFont.setItalic(True)
            for ctrl in range(128):
                description, valid = getCtrlNameFromMapping(ctrl, mapping)
                item = QtGui.QStandardItem('{} - {}'.format(ctrl, description))
                item.setData(ctrl, ParameterRole)
                item.setData(valid, ValidMappingRole)
                if valid == 2:
                    item.setData(validFont, QtCore.Qt.FontRole)
                elif not valid:
                    item.setData(unmapFont, QtCore.Qt.FontRole)
                if ctrl in self.existing:
                    item.setEnabled(False)
                sourceModel.appendRow(item)

        proxyModel.setFilter(self.validMappingChk.isChecked())
        self.ctrlCombo.setModel(proxyModel)

        if prevCtrl is not None:
            while not proxyModel.filterAcceptsRow(prevCtrl) or \
                not proxyModel.mapFromSource(proxyModel.sourceModel().index(prevCtrl, 0)).flags() & QtCore.Qt.ItemIsEnabled:
                    prevCtrl += 1
                    if prevCtrl == 128:
                        prevCtrl = 0
            self.ctrlCombo.setCurrentIndex(proxyModel.mapFromSource(proxyModel.sourceModel().index(prevCtrl, 0)).row())
        self.setCtrlStyle(self.ctrlCombo.currentIndex())
        self.ctrlCombo.currentIndexChanged.connect(self.setCtrlStyle)

    def toggleValidMapping(self, valid):
        prevIndex = self.ctrlCombo.currentIndex()
        if prevIndex >= 0:
            prevCtrl = self.ctrlCombo.itemData(prevIndex, ParameterRole)
        else:
            prevCtrl = None
        proxyModel = self.ctrlCombo.model()
        proxyModel.setFilter(valid)
        if prevCtrl is not None:
            while not proxyModel.filterAcceptsRow(prevCtrl) or \
                not proxyModel.mapFromSource(proxyModel.sourceModel().index(prevCtrl, 0)).flags() & QtCore.Qt.ItemIsEnabled:
                    prevCtrl += 1
                    if prevCtrl == 128:
                        prevCtrl = 0
            self.ctrlCombo.setCurrentIndex(proxyModel.mapFromSource(proxyModel.sourceModel().index(prevCtrl, 0)).row())

    def eventFilter(self, source, event):
        if event.type() == QtCore.QEvent.MouseButtonPress and event.button() == QtCore.Qt.LeftButton:
            self.validMappingChk.click()
        return QtWidgets.QDialog.eventFilter(self, source, event)

    def automationInfo(self):
        return RegionInfo(self.parameterTypeGroup.checkedId(), 
            self.ctrlCombo.itemData(self.ctrlCombo.currentIndex(), ParameterRole), 
            mapping=self.mappingCombo.itemData(self.mappingCombo.currentIndex()))


class RepetitionsDialog(QtWidgets.QDialog):
    def __init__(self, parent, repetitions):
        QtWidgets.QDialog.__init__(self, parent)
        self.setWindowTitle('Loop pattern')
        self.default = repetitions

        layout = QtWidgets.QGridLayout()
        self.setLayout(layout)

        layout.addWidget(QtWidgets.QLabel('Loops:'))

        self.inputEdit = QtWidgets.QSpinBox()
        layout.addWidget(self.inputEdit, 0, 1)
        self.inputEdit.setRange(1, 128)
        self.inputEdit.setValue(repetitions)
        self.inputEdit.selectAll()

        self.buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok|QtWidgets.QDialogButtonBox.Cancel)
        layout.addWidget(self.buttonBox, 1, 0, 1, 2)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

    def exec_(self):
        if QtWidgets.QDialog.exec_(self):
            return self.inputEdit.value()
        return self.default


class TempoEditDialog(QtWidgets.QDialog):
    def __init__(self, parent, tempo):
        QtWidgets.QDialog.__init__(self, parent)
        self.setWindowTitle('Edit tempo')
        layout = QtWidgets.QGridLayout()
        self.setLayout(layout)

        layout.addWidget(QtWidgets.QLabel('Tempo (BPM):'))
        self.tempoEdit = QtWidgets.QSpinBox()
        layout.addWidget(self.tempoEdit, 0, 1)
        self.tempoEdit.setRange(30, 300)
        self.tempoEdit.setValue(tempo.tempo)
        self.tempoEdit.setAccelerated(True)
        self.tempoEdit.selectAll()

        self.buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok|QtWidgets.QDialogButtonBox.Cancel)
        layout.addWidget(self.buttonBox, 1, 0, 1, 2)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

    def exec_(self):
        res = QtWidgets.QDialog.exec_(self)
        if res:
            return self.tempoEdit.value()


class DenominatorSpin(QtWidgets.QSpinBox):
    denominators = 1, 2, 4, 8, 16
    iconNames = ['note-{}'.format(d) for d in ('4-4', '2-4', '1-4', '1-8', '1-16')]
    denominatorsStr = tuple(str(d) for d in denominators)
    def __init__(self):
        QtWidgets.QSpinBox.__init__(self)
        self.setRange(0, 4)
        self.icons = [QtGui.QIcon.fromTheme(n) for n in self.iconNames]
        self.iconLabel = QtWidgets.QLabel(self)
        self.iconLabel.show()
        self.iconLabel.raise_()
        self.valueChanged.connect(self.setIcon)

    def setIcon(self):
        size = self.lineEdit().height()
        self.iconLabel.setFixedSize(size, size)
        self.iconLabel.setPixmap(self.icons[self.value()].pixmap(size))
        self.iconLabel.move(self.lineEdit().pos())

    def textFromValue(self, value):
        return self.denominatorsStr[value]

    def valueFromText(self, text):
        try:
            return self.denominatorsStr.index(text)
        except:
            return self.value()

    def resizeEvent(self, event):
        QtWidgets.QSpinBox.resizeEvent(self, event)
        self.setIcon()


class MeterEditDialog(QtWidgets.QDialog):
    def __init__(self, parent, meter):
        QtWidgets.QDialog.__init__(self, parent)
        self.setWindowTitle('Edit meter')
        layout = QtWidgets.QGridLayout()
        self.setLayout(layout)

        layout.addWidget(QtWidgets.QLabel('Meter:'), 0, 0, 2, 1)

        self.numSpin = QtWidgets.QSpinBox()
        layout.addWidget(self.numSpin, 0, 1)
        self.numSpin.setRange(1, 32)
        self.numSpin.setValue(meter.numerator)
        self.numSpin.selectAll()
        self.numSpin.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter)

        self.denSpin = DenominatorSpin()
        layout.addWidget(self.denSpin, 1, 1)
        self.denSpin.setValue(self.denSpin.denominators.index(meter.denominator))
        self.denSpin.setAlignment(self.numSpin.alignment())

        self.buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok|QtWidgets.QDialogButtonBox.Cancel)
        layout.addWidget(self.buttonBox, 2, 0, 1, 2)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

    def exec_(self):
        res = QtWidgets.QDialog.exec_(self)
        if res:
            return self.numSpin.value(), self.denSpin.denominators[self.denSpin.value()]
