import os

os.environ['QT_PREFERRED_BINDING'] = 'PyQt4'

from Qt import QtCore, QtGui, QtWidgets

from bigglesworth.utils import loadUi
from bigglesworth.parameters import Parameters, ctrl2sysex, sysex2ctrl
from bigglesworth.sequencer.const import (ValidMappingRole, ParameterRole, QuantizeRole, 
    SnapModes, DefaultNoteSnapModeId, UnicodeValidator, 
    UidColumn, DataColumn, TitleColumn, TracksColumn, EditedColumn, CreatedColumn, 
    Mappings, CtrlParameter, SysExParameter, BlofeldParameter, getCtrlNameFromMapping)
from bigglesworth.sequencer.structure import RegionInfo, MetaRegion

ParameterIdRole = ParameterRole + 1


class MidiImportProgressDialog(QtWidgets.QProgressDialog):
    def __init__(self, parent, count):
        QtWidgets.QProgressDialog.__init__(self, 'Importing {} MIDI tracks...'.format(count), '', 0, count, parent)
        self.setCancelButton(None)
        self.setWindowTitle('Importing MIDI file')

    def closeEvent(self, event):
        if self.value() >= self.maximum():
            QtWidgets.QProgressDialog.closeEvent(self, event)
        else:
            event.ignore()

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            event.ignore()
        else:
            QtWidgets.QProgressDialog.keyPressEvent(self, event)


class BlofeldIdDialog(QtWidgets.QDialog):
    def __init__(self, parent, blofeldId=127):
        QtWidgets.QDialog.__init__(self, parent)
        self.setWindowTitle('Specify Device ID')
        layout = QtWidgets.QGridLayout()
        self.setLayout(layout)
        if not blofeldId:
            text = '''
            The current song has some Blofeld parameter automation set, but the current 
            <i>Device ID</i> is set to 0.<br/>
            While this usually works for most scenarios, using the "broadcast" ID (127) 
            is suggested.
            '''
        else:
            text = '''
            The current song has some Blofeld parameter automation set, but the current 
            <i>Device ID</i> is set to 0.<br/>
            Setting the ID to the "broadcast" value (127) is preferred.
            '''
        label = QtWidgets.QLabel(text)
        layout.addWidget(label, 0, 0, 1, 3)
        label.setWordWrap(True)
        label.setTextFormat(QtCore.Qt.RichText)
#        label.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Preferred)

        layout.addWidget(QtWidgets.QLabel('Device ID:'), 1, 0)

        self.idSpin = QtWidgets.QSpinBox()
        layout.addWidget(self.idSpin, 1, 1)
        self.idSpin.setMaximum(127)
        self.idSpin.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Preferred)

        self.broadcastBtn = QtWidgets.QPushButton('Broadcast')
        layout.addWidget(self.broadcastBtn, 1, 2)
        self.broadcastBtn.clicked.connect(lambda: self.idSpin.setValue(127))
        self.broadcastBtn.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Preferred)

        buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok|QtWidgets.QDialogButtonBox.RestoreDefaults)
        layout.addWidget(buttonBox, 2, 0, 1, 3)
        buttonBox.button(buttonBox.RestoreDefaults).clicked.connect(lambda: self.idSpin.setValue(blofeldId))
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)

    def exec_(self):
        if QtWidgets.QDialog.exec_(self) is not None:
            return self.idSpin.value()


class InputTextDialog(QtWidgets.QDialog):
    def __init__(self, parent, title, label, text='', maxLength=16):
        QtWidgets.QDialog.__init__(self, parent)
        self.setWindowTitle(title)
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        layout.addWidget(QtWidgets.QLabel(label))
        self.lineEdit = QtWidgets.QLineEdit(text)
        layout.addWidget(self.lineEdit)
        self.lineEdit.setMaxLength(16)
        self.lineEdit.setValidator(UnicodeValidator())
        buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok|QtWidgets.QDialogButtonBox.Cancel)
        layout.addWidget(buttonBox)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)

    def exec_(self):
        if QtWidgets.QDialog.exec_(self):
            return self.lineEdit.text().strip()

class SongItemDelegate(QtWidgets.QStyledItemDelegate):
    validator = UnicodeValidator()

    def createEditor(self, parent, option, index):
        editor = QtWidgets.QStyledItemDelegate.createEditor(self, parent, option, index)
        editor.setValidator(self.validator)
        return editor


class SongBrowser(QtWidgets.QDialog):
    def __init__(self, parent, songModel):
        QtWidgets.QDialog.__init__(self, parent)
        loadUi('ui/sequencerbrowser.ui', self)
        self.songModel = songModel
        self.songTable.setModel(songModel)
        self.songTable.setColumnHidden(UidColumn, True)
        self.songTable.setColumnHidden(DataColumn, True)
        self.songTable.horizontalHeader().setResizeMode(TitleColumn, QtWidgets.QHeaderView.Stretch)
        self.songTable.horizontalHeader().setResizeMode(TracksColumn, QtWidgets.QHeaderView.ResizeToContents)
        self.songTable.horizontalHeader().setResizeMode(EditedColumn, QtWidgets.QHeaderView.ResizeToContents)
        self.songTable.horizontalHeader().setResizeMode(CreatedColumn, QtWidgets.QHeaderView.ResizeToContents)
        self.songTable.selectionModel().selectionChanged.connect(self.selectionChanged)

        self.songTable.doubleClicked.connect(self.openSong)
        self.songTable.setItemDelegate(SongItemDelegate())
        self.songModel.dataChangedSignal.connect(self.checkSelection)

        self.renameBtn.clicked.connect(self.renameSong)
        self.deleteBtn.clicked.connect(self.deleteSong)
        self.buttonBox.button(self.buttonBox.Open).setEnabled(False)

    def openSong(self, index):
        self.accept()

    def renameSong(self):
        index = self.songTable.currentIndex()
        if not index.isValid():
            self.renameBtn.setEnabled(False)
            return
        self.songTable.edit(index)

    def deleteSong(self):
        indexes = self.songTable.selectionModel().selectedRows()
        if not indexes:
            self.deleteBtn.setEnabled(False)
            return
        if QtWidgets.QMessageBox.question(self, 'Delete songs', 
            'Do you want to permanently delete the {count}selected song{p}?'.format(
                count='{} '.format(len(indexes)) if len(indexes) > 1 else '', 
                p='s' if len(indexes) > 1 else '', 
                ),
            QtWidgets.QMessageBox.Ok|QtWidgets.QMessageBox.Cancel
            ) != QtWidgets.QMessageBox.Ok:
                return
        for index in sorted(indexes, key=lambda i: i.row(), reverse=True):
            self.songModel.removeRow(index.row())

    def checkSelection(self, index):
        if index.isValid():
            QtCore.QTimer.singleShot(0, lambda: self.songTable.selectRow(index.row()))

    def selectionChanged(self, current, prev):
        selectedRows = len(set([i.row() for i in current.indexes()]))
        self.buttonBox.button(self.buttonBox.Open).setEnabled(selectedRows == 1)
        self.renameBtn.setEnabled(selectedRows == 1)
        self.deleteBtn.setEnabled(selectedRows >= 1)

    def exec_(self):
        if QtWidgets.QDialog.exec_(self):
            uid = self.songModel.data(
                self.songTable.currentIndex().sibling(
                    self.songTable.currentIndex().row(), UidColumn), QtCore.Qt.DisplayRole)
            data = self.songModel.data(
                self.songTable.currentIndex().sibling(
                    self.songTable.currentIndex().row(), DataColumn), QtCore.Qt.DisplayRole)
            return uid, data


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


class BlofeldExistingModel(QtCore.QSortFilterProxyModel):
    part = 0
    existing = [set() for p in range(16)]
    def __init__(self, model, existing):
        QtCore.QSortFilterProxyModel.__init__(self)
        self.setSourceModel(model)
        for parameterId in existing:
            part = parameterId >> 15
            realId = parameterId & 32767
            self.existing[part].add(realId)

    def setPart(self, part):
        if part != self.part:
            self.part = part
            self.invalidate()

    def flags(self, index):
        flags = QtCore.QSortFilterProxyModel.flags(self, index)
        try:
            if index.data(ParameterIdRole) in self.existing[self.part]:
                flags &= ~ QtCore.Qt.ItemIsEnabled
        except Exception as e:
            print(e)
        return flags


class AddAutomationDialog(QtWidgets.QDialog):
    def __init__(self, parent, existing=None):
        QtWidgets.QDialog.__init__(self, parent)
        loadUi('ui/sequenceraddautomationdialog.ui', self)
        self.existingCtrl = set()
        self.existingBlofeld = set()
        if existing is not None:
            for regionInfo in existing:
                if regionInfo.parameterType == CtrlParameter:
                    self.existingCtrl.add(regionInfo.parameterId)
                    if regionInfo.parameterId in ctrl2sysex:
                        self.existingBlofeld.add(ctrl2sysex[regionInfo.parameterId] << 4)
                elif regionInfo.parameterType == BlofeldParameter:
                    self.existingBlofeld.add(regionInfo.parameterId)
                    if regionInfo.parameterId >> 4 & 511 in sysex2ctrl:
                        self.existingCtrl.add(sysex2ctrl[regionInfo.parameterId >> 4 & 511])

        model = QtGui.QStandardItemModel()
        self.blofeldModel = BlofeldExistingModel(model, self.existingBlofeld)
        self.blofeldCombo.setModel(self.blofeldModel)
        index = 0
        for param in Parameters.parameterData:
            if param.id >= 359:
                break
            elif param.attr.startswith('reserved'):
                continue
            if param.children:
                for childId in sorted(param.children.keys()):
                    child = param.children[childId]
                    item = QtGui.QStandardItem(child.fullName)
                    item.setData(child, ParameterRole)
                    item.setData((param.id << 4) + childId, ParameterIdRole)
#                    if (param.id << 4) + childId in self.existingBlofeld:
#                        item.setFlags(item.flags() ^ QtCore.Qt.ItemIsEnabled)
                    model.appendRow(item)
#                    self.blofeldCombo.addItem(child.fullName)
#                    self.blofeldCombo.setItemData(index, child, ParameterRole)
                    index += 1
            else:
                item = QtGui.QStandardItem(param.fullName)
                item.setData(param, ParameterRole)
                item.setData(param.id << 4, ParameterIdRole)
                #no, a questo punto vedi se val la pena far lo sbattimento di aggiungereun "sub parameterId"
                #o lasciar perdere completamente l'implementazione dei parametri blofeld non ctrl
#                if param.id << 4 in self.existingBlofeld:
#                    item.setFlags(item.flags() ^ QtCore.Qt.ItemIsEnabled)
#                self.blofeldCombo.addItem(param.fullName)
#                self.blofeldCombo.setItemData(index, param, ParameterRole)
                model.appendRow(item)
                index += 1

        self.blofeldCombo.currentIndexChanged.connect(self.setBlofeldLabel)
        self.blofeldCombo.currentIndexChanged.connect(self.checkBlofeldValid)
        self.partCombo.currentIndexChanged.connect(self.blofeldModel.setPart)
        self.partCombo.currentIndexChanged.connect(self.checkBlofeldValid)
        self.tabWidget.currentChanged.connect(self.checkBlofeldValid)

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

        self.validLbl.setVisible(False)
        self.validIcon.setVisible(False)
        self.multiLbl.setVisible(False)
        icon = QtGui.QIcon.fromTheme('emblem-warning')
        iconSize = self.fontMetrics().height()
        pm = icon.pixmap(iconSize)
        if pm.height() != iconSize or True:
            pm = pm.scaledToHeight(iconSize, QtCore.Qt.SmoothTransformation)
        self.validIcon.setPixmap(pm)

        self.setMapping(0)
        self.setBlofeld(0)
        self.validMappingLbl.installEventFilter(self)
#        self.validMappingChk.setChecked(True)

    def setBlofeld(self, index):
        if self.blofeldModel.index(index, 0).flags() & QtCore.Qt.ItemIsEnabled:
            self.blofeldCombo.setCurrentIndex(index)
            return
        for row in range(self.blofeldModel.rowCount()):
            if self.blofeldModel.index(row, 0).flags() & QtCore.Qt.ItemIsEnabled:
                self.blofeldCombo.setCurrentIndex(row)
                return

    def setBlofeldLabel(self, index):
        param = self.blofeldCombo.itemData(index, ParameterRole)
        text = 'Minimum: {minVal} ({minText})<br/>Maximum: {maxVal} ({maxText})<br/>' \
            'Default: {defaultVal} ({defaultText})'.format(
            minVal=param.range.minimum, 
            minText=param.values[0], 
            maxVal=param.range.maximum, 
            maxText=param.values[-1], 
            defaultVal=param.default, 
            defaultText=param.valueDict[param.default])
        if param.range.step > 1:
            text += '<br/><br/>This parameter has steps of {}'.format(param.range.step)
        self.blofeldLbl.setText(text)

    def checkBlofeldValid(self):
        if self.tabWidget.currentIndex():
            valid = True
        else:
            valid = bool(self.blofeldModel.index(self.blofeldCombo.currentIndex(), 0).flags() & QtCore.Qt.ItemIsEnabled)
        self.validLbl.setVisible(not valid)
        self.validIcon.setVisible(not valid)
        self.multiLbl.setVisible(self.partCombo.currentIndex())
        self.buttonBox.button(self.buttonBox.Ok).setEnabled(valid)

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
                if ctrl in self.existingCtrl:
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
        if self.tabWidget.currentIndex():
            return RegionInfo(self.parameterTypeGroup.checkedId(), 
                self.ctrlCombo.itemData(self.ctrlCombo.currentIndex(), ParameterRole), 
                mapping=self.mappingCombo.itemData(self.mappingCombo.currentIndex()))
        parameter = self.blofeldCombo.itemData(self.blofeldCombo.currentIndex(), ParameterRole)
        if parameter.parent:
            id = (parameter.parent.id << 4) + parameter.id
        else:
            id = parameter.id << 4
        id += self.partCombo.currentIndex() << 15
        return RegionInfo(BlofeldParameter, id)


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

        self.tapBtn = QtWidgets.QPushButton('Tap')
        layout.addWidget(self.tapBtn, 1, 0, 1, 2)
        self.tapBtn.clicked.connect(self.tap)

        self.buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok|QtWidgets.QDialogButtonBox.Cancel)
        layout.addWidget(self.buttonBox, 2, 0, 1, 2)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        self.tapTimer = QtCore.QElapsedTimer()

    def tap(self):
        elapsed = self.tapTimer.elapsed()
        if elapsed > 4000:
            pass
        elif elapsed > 2000:
            self.tempoEdit.setValue(30)
        else:
            self.tempoEdit.setValue(60000 / elapsed)
        self.tapTimer.start()

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

    def validate(self, text, pos):
        if text in ('1', '2', '4', '8', '16'):
            return QtGui.QValidator.Acceptable, text, pos
        return QtWidgets.QSpinBox.validate(self, text, pos)

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
