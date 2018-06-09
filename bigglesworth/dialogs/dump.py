from string import uppercase

from Qt import QtCore, QtGui, QtWidgets

from bigglesworth.utils import loadUi, localPath, getName
from bigglesworth.const import (UidColumn, LocationColumn, NameColumn, CatColumn, TagsColumn, CatRole, TagsRole, 
    INIT, IDE, IDW, CHK, SNDR, SNDD, END)
from bigglesworth.widgets import CategoryDelegate, TagsDelegate, CheckBoxDelegate, MidiConnectionsDialog
from bigglesworth.midiutils import SysExEvent, SYSEX


class SmallDumper(QtWidgets.QDialog):
    def __init__(self, main, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        loadUi(localPath('ui/smalldumper.ui'), self)
        self.setModal(True)
        self._count = 0

    def showEvent(self, event):
        self.waiter.active = True

    def hideEvent(self, event):
        self.waiter.active = False

    @property
    def count(self):
        return self._count

    @count.setter
    def count(self, count):
        self._count = count
        self.progressBar.setValue(count)

    def start(self, uid=None, tot=1, collection=None, collectionIndex=None):
#        self.waiter.active = True
        self.tot = tot
        self.progressBar.setVisible(True if tot > 1 else False)
        self.progressBar.setMaximum(tot)
        self.count = 0
        self.target = collection, collectionIndex
        self.show()



class Dumper(QtWidgets.QDialog):
    def __init__(self, parent):
        QtWidgets.QDialog.__init__(self, parent)
        loadUi(localPath('ui/dumper.ui'), self)
        self.blockable = False
        self.elapsed = QtCore.QElapsedTimer()
        self.clock = QtCore.QTimer()
        self.clock.setInterval(1000)
        self.clock.timeout.connect(self.updateClock)
        self.timerCheck = QtCore.QTimer()
        self.timerCheck.setInterval(5000)
        self.timerCheck.timeout.connect(self.checkClock)
        self.nameLbl.setMinimumWidth(self.fontMetrics().width('W' * 16))
        self.abortBtn.clicked.connect(self.reject)
        self.pauseBtn.toggled.connect(self.pauseToggle)

    def pauseToggle(self, state):
        self.mainWidget.setEnabled(not state)
        self.waiter.active = not state
        if state:
            self.pauseZero = self.elapsed.elapsed()
            self.timerCheck.stop()
            self.clock.stop()
        else:
            self.deltaT += self.elapsed.elapsed() - self.pauseZero
            if self.elapsed.elapsed() - self.deltaT > 5:
                self.timerCheck.start()
            self.clock.start()

    def setData(self, count, bank, prog, name=''):
        self.count = count
        self.progressBar.setValue(count)
        self.posLbl.setText('{}{:03}'.format(uppercase[bank], prog + 1))
        self.nameLbl.setText(name)

    def updateClock(self):
        elapsed = (self.elapsed.elapsed() - self.deltaT) * .001
        min, secs = map(int, divmod(elapsed, 60))
        if min:
            text = '{:01}m {:02}s'.format(min, secs)
        else:
            text = '{:02}s'.format(secs)
        self.elapsedLbl.setText(text)
        if secs > 5 and self.eta:
            eta = self.eta - elapsed
            if eta < 1:
                text = 'almost...'
            else:
                min, secs = map(int, divmod(eta, 60))
                if min:
                    text = '{:01}m {:02}s'.format(min, secs)
                else:
                    text = '{:02}s'.format(secs)
            self.etaLbl.setText(text)
            self.etaLbl.setEnabled(True)

    def checkClock(self):
        if not self.count:
            return
        self.eta = (self.elapsed.elapsed() - self.deltaT) * .001 * self.tot / self.count

    def reject(self):
        if self.blockable:
            QtWidgets.QDialog.reject(self)

    def closeEvent(self, event):
        if self.blockable:
            event.accept()
            print('accetto')
        else:
            event.ignore()
            print('ignoro')

    def start(self, tot):
        self.count = 0
        self.pauseBtn.blockSignals(True)
        self.pauseBtn.setChecked(False)
        self.pauseBtn.blockSignals(False)
        if tot:
            self.tot = tot
            self.buttonBox.setEnabled(True)
            self.blockable = True
        else:
            self.tot = 1024
            self.buttonBox.setEnabled(False)
            self.blockable = False
        if self.tot > 5:
            self.timerCheck.start()
            self.etaLbl.setText('computing...')
        else:
            self.etaLbl.setText('')
        self.progressBar.setMaximum(self.tot)
        self.elapsedLbl.setText('00s')
        self.etaLbl.setEnabled(False)
        self.eta = 0
        self.pauseZero = self.deltaT = 0
        self.show()
        self.elapsed.start()
        self.clock.start()
        self.setModal(True)


class DumpDialog(QtWidgets.QDialog):
    midiEvent = QtCore.pyqtSignal(object)

    def __init__(self, uiPath, main, parent):
        QtWidgets.QDialog.__init__(self, parent)
        loadUi(localPath(uiPath), self)
        self.main = main
        self.database = main.database
        self.cancelBtn = self.buttonBox.button(self.buttonBox.Cancel)
        self.ignoreDuplexConnectionLost = False

        checkBoxDelegate = CheckBoxDelegate(self.collectionTable)
        self.collectionTable.setItemDelegateForColumn(0, checkBoxDelegate)
        catDelegate = CategoryDelegate(self.collectionTable)
        self.collectionTable.setItemDelegateForColumn(2, catDelegate)
        self.tagsDelegate = TagsDelegate(self.collectionTable)
        self.tagsDelegate.setTagsModel(self.database.tagsModel)
        self.collectionTable.setItemDelegateForColumn(3, self.tagsDelegate)
        self.collectionTable.customContextMenuRequested.connect(self.tableMenu)

        self.collectionCombo.currentIndexChanged.connect(self.setCollection)
        self.sourceModel = self.selectedCollection = self.tableModel = None
        self.banksWidget.itemsChanged.connect(self.bankSelect)
        self.delaySpin.valueChanged.connect(self.computeEta)

        self.normalFont = self.font()
        self.strokeFont = self.font()
        self.strokeFont.setStrikeOut(True)

        self.dumper = Dumper(self)
        self.midiVisible = False
        self.midiConnectionsDialog = MidiConnectionsDialog(self.main, self)
        self.midiBtn.clicked.connect(self.showMidiConnections)

    def showMidiConnections(self):
        self.midiVisible = True
        self.midiConnectionsDialog.exec_()
        self.midiVisible = False

    def tableMenu(self, pos):
        menu = QtWidgets.QMenu()
        checkAction = menu.addAction('Check selected sounds')
        uncheckAction = menu.addAction('Uncheck selected sounds')
#        if not self.collectionTable.selectionModel().selectedRows():
        if not self.collectionTable.selectedIndexes():
            checkAction.setEnabled(False)
            uncheckAction.setEnabled(False)
        else:
            enable = any([index.flags() & QtCore.Qt.ItemIsEditable for index in self.collectionTable.selectionModel().selectedRows()])
            checkAction.setEnabled(enable)
            uncheckAction.setEnabled(enable)
        menu.addSeparator()
        selectAllAction = menu.addAction('Select all')
        res = menu.exec_(self.collectionTable.viewport().mapToGlobal(pos))
        if not res:
            return
        elif res == selectAllAction:
            self.collectionTable.selectAll()
            return
        if isinstance(self, DumpReceiveDialog):
            for index in self.collectionTable.selectionModel().selectedRows():
                self.tableModel.setData(index, True if res == checkAction else False, QtCore.Qt.CheckStateRole)
        else:
            for index in self.collectionTable.selectionModel().selectedRows():
                if index.row() not in self.soundsDict:
                    continue
                self.tableModel.setData(index, True if res == checkAction else False, QtCore.Qt.CheckStateRole)

    def setEta(self, time):
        if not time:
            self.etaLbl.setText('')
            return
        text = 'Estimate time: '
        time = int(time * .001)
        min, sec = divmod(time, 60)
        if sec > 50:
            min += 1
            sec = 0
        elif min and sec < 10:
            sec = 0
        elif sec > 10:
            sec = int(round(sec * .1) * 10)
        if min:
            if sec:
                text += '{}m {:02}s'.format(min, sec)
            else:
                text += '~{}m'.format(min)
        else:
            text += '~{}s'.format(sec)
        self.etaLbl.setText(text)

    def setModel(self, sourceModel, tableModel=None, soundsDict=None):
#        if self.overwriteChk:
#            self.overwriteChk.blockSignals(True)
#            self.overwriteChk.setChecked(False)
#            self.overwriteChk.blockSignals(False)

        if self.tableModel:
            self.tableModel.dataChanged.disconnect(self.dataChanged)
        self.sourceModel = sourceModel

        activeFlags = QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled
        disabled = self.palette().color(QtGui.QPalette.Disabled, QtGui.QPalette.Text)
        if tableModel is None:
            tableModel = QtGui.QStandardItemModel()
            soundsDict = {}
            for row in range(sourceModel.rowCount()):
                checkItem = QtGui.QStandardItem()
                nameIndex = sourceModel.index(row, NameColumn)
                catIndex = sourceModel.index(row, CatColumn)
                tagIndex = sourceModel.index(row, TagsColumn)
                nameItem = QtGui.QStandardItem(nameIndex.data(QtCore.Qt.DisplayRole))
                soundFlags = nameIndex.flags()
                if soundFlags & QtCore.Qt.ItemIsEnabled:
                    soundsDict[row] = sourceModel.index(row, UidColumn).data(QtCore.Qt.DisplayRole), nameItem, checkItem
                else:
                    if isinstance(self, DumpSendDialog):
                        checkItem.setEditable(False)
                    nameItem.setData(disabled, QtCore.Qt.ForegroundRole)
                nameItem.setFlags(soundFlags | activeFlags)
                catItem = QtGui.QStandardItem()
                catItem.setFlags(catIndex.flags() | activeFlags)
                catItem.setData(catIndex.data(QtCore.Qt.DisplayRole), QtCore.Qt.DisplayRole)
                tagItem = QtGui.QStandardItem()
                tagItem.setFlags(tagIndex.flags() | activeFlags)
                tagItem.setData(tagIndex.data(QtCore.Qt.DisplayRole), QtCore.Qt.DisplayRole)
                tableModel.appendRow([checkItem, nameItem, catItem, tagItem])
            tableModel.setHorizontalHeaderLabels(['', 'Name', 'Category', 'Tags'])

            vLabels = []
            for i in range(1024):
#                b, p = divmod(i, 128)
                vLabels.append('{}{:03}'.format(uppercase[i >> 7], (i & 127) + 1))
            tableModel.setVerticalHeaderLabels(vLabels)

        self.tableModel = tableModel
        self.tableModel.dataChanged.connect(self.dataChanged)

        self.collectionTable.setModel(tableModel)
        self.soundsDict = soundsDict

        if not self.shown:
            self.shown = True
            self.collectionTable.setWordWrap(False)
            self.collectionTable.resizeColumnsToContents()
            self.collectionTable.resizeRowsToContents()
            self.collectionTable.horizontalHeader().setResizeMode(QtWidgets.QHeaderView.Fixed)
            self.collectionTable.horizontalHeader().setResizeMode(3, QtWidgets.QHeaderView.Stretch)
            self.collectionTable.verticalHeader().setResizeMode(QtWidgets.QHeaderView.Fixed)
            self.collectionTable.verticalHeader().setDefaultSectionSize(self.collectionTable.verticalHeader().sectionSize(0))
            width = self.collectionTable.horizontalHeader().length()
#            self.collectionTable.verticalHeader().minimumSizeHint().width() * 2 + \
#            self.collectionTable.verticalScrollBar().sizeHint().width() * 2
            self.collectionTable.setMinimumWidth(width)

        if self.overwriteChk:
            self.overwriteChk.setEnabled(len(self.soundsDict))
#            self.overwrite(self.overwriteChk.isChecked())

        #TODO: verifica, forse meglio salvare il default in exec_
        self.banksWidget.blockSignals(True)
        if self.overwriteChk:
            self.overwriteChk.blockSignals(True)
        if not sourceModel in self.changedCollections:
            self.changedCollections[sourceModel] = [None, None]
            self.bankSelect(self.banksWidget.items, False)
            if self.overwriteChk:
                self.overwrite(self.overwriteChk.isChecked(), False)
        else:
            banksState, overwriteState = self.changedCollections[sourceModel]
            if banksState is not None:
                self.bankSelect(banksState)
                self.banksWidget.setItems(banksState)
            else:
                self.bankSelect(self.banksWidget.items, False)
            if self.overwriteChk:
                if overwriteState is not None:
                    self.overwrite(overwriteState)
                    self.overwriteChk.setChecked(overwriteState)
                else:
                    self.overwrite(self.overwriteChk.isChecked(), False)
        if self.overwriteChk:
            self.overwriteChk.blockSignals(False)
        self.banksWidget.blockSignals(False)

    def bankSelect(self, banks, save=True):
        self.tableModel.blockSignals(True)
        #TODO: verifica anche questo, forse meglio gestire il tutto diversamente?
        #font?!?!
        model = self.tableModel
        if isinstance(self, DumpReceiveDialog):
            for row in range(model.rowCount()):
                bank = row >> 7
                model.item(row, 0).setData(True if bank in banks else False, QtCore.Qt.CheckStateRole)
        else:
            for row in range(model.rowCount()):
                if row not in self.soundsDict:
                    continue
                bank = row >> 7
                model.item(row, 0).setData(True if bank in banks else False, QtCore.Qt.CheckStateRole)
        if save:
            self.changedCollections[self.sourceModel][0] = set(banks)
        self.tableModel.blockSignals(False)
        self.collectionTable.viewport().update()
        self.computeEta()

    def dataChanged(self, index, last=None):
        if index.column():
            return
        row = index.row()
        checked = index.data(QtCore.Qt.CheckStateRole)
        if self.overwriteChk and row in self.soundsDict:
            if checked and self.overwriteChk.isChecked():
                font = self.strokeFont
            else:
                font = self.normalFont
            self.soundsDict[row][1].setData(font, QtCore.Qt.FontRole)

        #TODO: usa un timer per accodare la richiesta
        if checked and all(self.main.connections):
            self.dumpBtn.setEnabled(True)

        currentSet = set(self.banksWidget.items)
        banks = set()
        currentBank = row >> 7
        for bank in range(8):
            if currentBank == bank and not checked:
                continue
            shiftBank = bank << 7
            if isinstance(self, DumpReceiveDialog):
                for row in range(128):
                    if not self.tableModel.item(row + shiftBank, 0).data(QtCore.Qt.CheckStateRole):
                        break
                else:
                    banks.add(bank)
            else:
                for row in range(128):
                    if row not in self.soundsDict:
                        continue
                    if not self.tableModel.item(row + shiftBank, 0).data(QtCore.Qt.CheckStateRole):
                        break
                else:
                    banks.add(bank)
        if currentSet != banks:
            self.banksWidget.blockSignals(True)
            self.banksWidget.setItems(banks)
            self.banksWidget.blockSignals(False)
        self.computeEta()

    def setCollection(self, index):
        font = self.collectionCombo.font()
        font.setBold(self.collectionCombo.itemText(index) == self.selectedCollection)
        self.collectionCombo.setFont(font)
        data = self.collectionCombo.itemData(index)
        if not data:
            sourceModel = self.database.openCollection(self.collectionCombo.itemText(index))
            self.setModel(sourceModel)
            self.collectionCombo.setItemData(index, (self.sourceModel, self.collectionTable.model(), self.soundsDict))
        else:
            self.setModel(*data)

    def exec_(self, collection, sounds=False):
        self.collectionTable.verticalScrollBar().setValue(0)
        self.collectionCombo.setEnabled(True)
        self.banksWidget.setEnabled(True)

        self.changedCollections = {}
        self.shown = False
        self.selectedCollection = collection
        self.collectionCombo.blockSignals(True)
        collections = self.database.referenceModel.collections
        self.collectionCombo.addItems(collections)
        self.collectionCombo.setItemData(0, QtGui.QIcon.fromTheme('go-home'), QtCore.Qt.DecorationRole)
        collectionIndex = collections.index(collection)
        font = self.collectionCombo.font()
        font.setBold(True)
        self.collectionCombo.setItemData(collectionIndex, font, QtCore.Qt.FontRole)
        self.collectionCombo.setCurrentIndex(collectionIndex)
        self.collectionCombo.blockSignals(False)
        self.setCollection(collectionIndex)

        if isinstance(sounds, bool):
            if sounds:
                #TODO: cambia questi if ed usa un attributo generico
                self.banksWidget.setAll()
                if self.overwriteChk:
                    self.overwriteChk.toggled.emit(True)
                    self.fastChk.setChecked(True)
            else:
                self.banksWidget.setItems()
        else:
            pass

        res = QtWidgets.QDialog.exec_(self)
        self.collectionCombo.blockSignals(True)
        self.collectionCombo.clear()
        self.collectionCombo.blockSignals(False)
        return res


class DumpReceiveDialog(DumpDialog):
    dumpComplete = QtCore.pyqtSignal()
    def __init__(self, main, parent=None):
        DumpDialog.__init__(self, 'ui/dumpreceive.ui', main, parent)
        self.okBtn = self.buttonBox.button(self.buttonBox.Apply)
        self.okBtn.setText('Import sounds')
        self.okBtn.clicked.connect(self.accept)
        self.direction = False
        self.overwriteChk.toggled.connect(self.overwrite)
        self.dumpBtn.clicked.connect(self.dump)
        self.receiving = False
        self.count = 0
        self.fastChk.toggled.connect(self.computeEta)
#        self.fastChk.toggled.connect(lambda state: self.delaySpin.setEnabled(False if state and self.banksWidget.isFull() else True))
        self.fastChk.toggled.connect(self.delaySpin.setDisabled)

    def dump(self):
        self.count = 0
        self.soundData = {}
        self.soundList = []
        if self.banksWidget.isFull() and self.fastChk.isChecked():
            event = SysExEvent(1, [INIT, IDW, IDE, self.main.blofeldId, SNDR, 0x40, 00, CHK, END])
        else:
            if self.overwriteChk.isChecked():
                for row in range(self.tableModel.rowCount()):
                    if self.tableModel.item(row, 0).data(QtCore.Qt.CheckStateRole):
                        self.soundList.append(row)
            else:
                for row in range(self.tableModel.rowCount()):
                    if self.tableModel.item(row, 0).data(QtCore.Qt.CheckStateRole) and \
                        not row in self.soundsDict:
                            self.soundList.append(row)
            if not self.soundList:
                return
            first = self.soundList[0]
            event = SysExEvent(1, [INIT, IDW, IDE, self.main.blofeldId, SNDR, first >> 7, first & 127, CHK, END])
        self.dumper.start(len(self.soundList))
        self.dumper.rejected.connect(lambda: setattr(self, 'receiving', False))
        self.dumper.accepted.connect(lambda: setattr(self, 'receiving', False))
        self.receiving = True
        QtCore.QTimer.singleShot(250, lambda: self.midiEvent.emit(event))

    def bankSelect(self, banks, save=True):
        if not all(self.main.connections):
            self.dumpBtn.setEnabled(False)
        elif all(self.main.connections):
            if self.sender() != self.banksWidget:
                for row in range(self.tableModel.rowCount()):
                    if self.tableModel.item(row, 0).data(QtCore.Qt.CheckStateRole):
                        self.dumpBtn.setEnabled(True)
                        break
                else:
                    self.dumpBtn.setEnabled(False)
            else:
                self.dumpBtn.setEnabled(True if banks else False)
        if not self.tableModel:
            return
        DumpDialog.bankSelect(self, banks, save=True)
        self.fastChk.setEnabled(self.banksWidget.isFull())
        self.delaySpin.setEnabled(False if self.banksWidget.isFull() and self.fastChk.isChecked() else True)

    def overwrite(self, state, save=True):
        self.tableModel.blockSignals(True)
        for index, (uid, nameItem, checkItem) in self.soundsDict.items():
            if checkItem.data(QtCore.Qt.CheckStateRole) and state:
                font = self.strokeFont
            else:
                font = self.normalFont
            checkItem.setEnabled(state)
            nameItem.setData(font, QtCore.Qt.FontRole)
        self.tableModel.blockSignals(False)
        self.collectionTable.viewport().update()
        if save:
            self.changedCollections[self.sourceModel][1] = state

    def midiConnEvent(self, conn, state):
        inConn, outConn = connections = self.main.connections
        if all(connections):
            for row in range(self.tableModel.rowCount()):
                if self.tableModel.item(row, 0).data(QtCore.Qt.CheckStateRole):
                    self.dumpBtn.setEnabled(True)
                    return
            self.dumpBtn.setEnabled(False)
            return
        if not self.ignoreDuplexConnectionLost and not all(connections):
            self.dumpBtn.setEnabled(False)
            if not self.midiVisible:
                self.midiVisible = True
                QtWidgets.QMessageBox.critical(
                    self, 
                    'MIDI connection lost', 
                    'Bidirectional MIDI connections required.\nPlease check connections and try again.', 
                    QtWidgets.QMessageBox.Ok
                    )
                self.showMidiConnections()
        elif (self.direction and not outConn) or (not self.direction and not inConn):
            self.dumpBtn.setEnabled(False)
            if not self.midiVisible:
                self.midiVisible = True
                dirText = 'output' if self.direction else 'input'
                QtWidgets.QMessageBox.critical(
                    self, 
                    'MIDI connection lost', 
                    'At least one {} MIDI connection is required.\nPlease check connections and try again.'.format(dirText), 
                    QtWidgets.QMessageBox.Ok
                    )
                self.showMidiConnections()

    def midiEventReceived(self, event):
        if self.receiving and event.type == SYSEX and event.sysex[4] == SNDD:
#            if not self.soundList:
            data = event.sysex[5:390]
            bank, prog = data[0:2]
#            print(bank, prog, getName(data[363:379]))
            index = (bank << 7) + prog
#            data = sound[2:]
            self.soundData[index] = data[2:]

            self.count += 1
            if self.count == 1024 or self.count == len(self.soundList):
                self.dumper.hide()
                self.processData()
                return
            #TODO: manage stop/abort?
            if not self.receiving:
                return
            if self.soundList:
                sound = self.soundList[self.count]
                if not self.dumper.pauseBtn.isChecked():
                    QtCore.QTimer.singleShot(self.delaySpin.value(), lambda: 
                        self.midiEvent.emit(SysExEvent(1, [INIT, IDW, IDE, self.main.blofeldId, SNDR, sound >> 7, sound & 127, CHK, END])))
                else:
                    self.unpauseEvent = SysExEvent(1, [INIT, IDW, IDE, self.main.blofeldId, SNDR, sound >> 7, sound & 127, CHK, END])
                    self.dumper.pauseBtn.toggled.connect(self.unpause)
            self.dumper.setData(self.count, bank, prog, getName(data[363:379]).strip())

    def unpause(self, state):
        if not state:
            self.dumper.pauseBtn.toggled.disconnect(self.unpause)
            self.midiEvent.emit(self.unpauseEvent)

    def processData(self, complete=True):
        self.activateWindow()
        self.dumpComplete.emit()
        self.tableModel.dataChanged.disconnect(self.dataChanged)
        self.tableModel.dataChanged.connect(self.dataChangedImport)
        self.collectionCombo.setEnabled(False)
        self.directChk.setEnabled(False)
        self.banksWidget.setEnabled(False)
        self.fastChk.setEnabled(False)
        self.delaySpin.setEnabled(False)
        self.etaLbl.setText('')
        self.okBtn.setEnabled(True)
        self.overwriteChk.setEnabled(False)
        self.dumpBtn.setEnabled(False)

        enabled = self.palette().color(QtGui.QPalette.Active, QtGui.QPalette.Text)
        disabled = self.palette().color(QtGui.QPalette.Disabled, QtGui.QPalette.Text)
        for row in range(self.tableModel.rowCount()):
            data = self.soundData.get(row)
            nameItem = self.tableModel.item(row, 1)
            font = nameItem.font()
            font.setStrikeOut(False)
            nameItem.setFont(font)
            if data:
                nameItem.setText(getName(data[363:379]))
                nameItem.setData(enabled, QtCore.Qt.ForegroundRole)
                self.tableModel.item(row, 2).setData(data[379], QtCore.Qt.DisplayRole)
                self.tableModel.item(row, 3).setData('[]', QtCore.Qt.DisplayRole)
            else:
                nameItem.setData(disabled, QtCore.Qt.ForegroundRole)
                nameItem.setEnabled(False)
                nameItem.setFlags(nameItem.flags() ^ QtCore.Qt.ItemIsSelectable)
                checkItem = self.tableModel.item(row, 0)
#                checkItem.setEnabled(False)
                checkItem.setCheckState(False)
                checkItem.setFlags(checkItem.flags() ^ (QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable))
#                checkItem.setFlags(checkItem.flags() ^ QtCore.Qt.ItemIsEnabled)
#                self.tableModel.item(row, 2).setData(disabled, QtCore.Qt.ForegroundRole)
                catItem = self.tableModel.item(row, 2)
                catItem.setFlags(catItem.flags() ^ (QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable))
                tagItem = self.tableModel.item(row, 3)
                tagItem.setFlags(tagItem.flags() ^ (QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable))

    def dataChangedImport(self, index, last=None):
        for row in range(self.tableModel.rowCount()):
            if self.tableModel.item(row, 0).data(QtCore.Qt.CheckStateRole):
                self.okBtn.setEnabled(True)
                return
        self.okBtn.setEnabled(False)

    def computeEta(self, *args):
        if self.banksWidget.isFull() and self.fastChk.isChecked():
            time = 210000
        else:
            time = 0
            interval = self.delaySpin.value() + 150
            for row in range(self.tableModel.rowCount()):
                if self.tableModel.item(row, 0).data(QtCore.Qt.CheckStateRole):
                    time += interval
        self.setEta(time)
    
    def exec_(self, collection, sounds=False):
        self.soundData = {}
        self.overwriteChk.setEnabled(True)
        self.overwriteChk.blockSignals(True)
        self.overwriteChk.setChecked(True)
        self.overwriteChk.blockSignals(False)
        self.okBtn.setEnabled(False)
        self.dumpBtn.setEnabled(all(self.main.connections))
        self.fastChk.setEnabled(True)
        self.delaySpin.setEnabled(True)
        self.directChk.setEnabled(True)
        res = DumpDialog.exec_(self, collection, sounds)
        self.tableModel.dataChanged.disconnect()
        if not res:
            self.sourceModel = self.tableModel = self.selectedCollection = None
            return
        sounds = {}
        for row, data in self.soundData.items():
            if self.tableModel.item(row, 0).data(QtCore.Qt.CheckStateRole):
                sounds[row] = data
        self.sourceModel = self.tableModel = self.selectedCollection = None
        return sounds, self.overwriteChk.isChecked()


class DumpSendDialog(DumpDialog):
    def __init__(self, main, parent=None):
        DumpDialog.__init__(self, 'ui/dumpsend.ui', main, parent)
        self.dumpBtn = self.okBtn = self.buttonBox.button(self.buttonBox.Ok)
        self.okBtn.setText('Dump sounds')
        self.okBtn.clicked.connect(self.dump)
        self.direction = True
        self.sending = False
        self.overwriteChk = None

    def dump(self):
        self.count = -1
        self.soundList = []
        for index in sorted(self.soundsDict):
            uid, nameItem, checkItem = self.soundsDict[index]
            if not checkItem.data(QtCore.Qt.CheckStateRole):
                continue
            data = self.database.getSoundDataFromUid(uid)
            bank = index >> 7
            prog = index & 127
            #F0h, 3Eh, 13h, DEV, 10h, BB, NN, --SDATA--, CHK, F7h
            #[INIT, IDW, IDE, self.main.blofeldId, SNDR, 0x40, 00, CHK, END]
            event = SysExEvent(1, [INIT, IDW, IDE, self.main.blofeldId, SNDD, bank, prog] + data + [CHK, END])
            self.soundList.append((bank, prog, getName(data[363:379]).strip(), event))
        self.dumper.start(len(self.soundList))
        self.dumper.rejected.connect(lambda: [setattr(self, 'sending', False), self.activateWindow()])
        self.dumper.accepted.connect(lambda: [setattr(self, 'sending', False), self.activateWindow()])
        self.sending = True
        QtCore.QTimer.singleShot(250, self.sendDump)

    def sendDump(self):
        if not self.sending:
            return
        self.count += 1
        if self.count == len(self.soundList):
            self.dumper.hide()
            if self.closeOnDumpBtn.isChecked():
                self.done(self.Accepted)
            return
        bank, prog, name, event = self.soundList[self.count]
        self.dumper.setData(self.count, bank, prog, name)
        self.midiEvent.emit(event)
        if not self.dumper.pauseBtn.isChecked():
            QtCore.QTimer.singleShot(self.delaySpin.value(), self.sendDump)
        else:
            self.dumper.pauseBtn.toggled.connect(self.unpause)

    def unpause(self, state):
        if not state:
            self.dumper.pauseBtn.toggled.disconnect(self.unpause)
            self.sendDump()

    def bankSelect(self, banks, save=True):
        outConn = self.main.connections[1]
        if not outConn:
            self.dumpBtn.setEnabled(False)
        elif outConn:
            if self.sender() != self.banksWidget and self.sender().window() == self.window():
                for row in range(self.tableModel.rowCount()):
                    if self.tableModel.item(row, 0).data(QtCore.Qt.CheckStateRole):
                        self.dumpBtn.setEnabled(True)
                        break
                else:
                    self.dumpBtn.setEnabled(False)
            else:
                #ignore empty banks and remove from set
                for bank in range(8):
                    shiftBank = bank << 7
                    progs = set(range(shiftBank, shiftBank + 128))
                    if not progs & set(self.soundsDict):
                        banks.discard(bank)
        if not self.tableModel:
            return
        DumpDialog.bankSelect(self, banks, save=True)
        #check again
        valid = False
        for bank in range(8):
            shiftBank = bank << 7
            for row in range(128):
                if row not in self.soundsDict:
                    continue
                if not self.tableModel.item(row + shiftBank, 0).data(QtCore.Qt.CheckStateRole):
                    banks.discard(bank)
                    break
                else:
                    valid = True
        self.banksWidget.blockSignals(True)
        self.banksWidget.setItems(banks)
        self.banksWidget.blockSignals(False)
        self.dumpBtn.setEnabled(valid)

    def midiConnEvent(self, conn, state):
        if self.main.connections[1]:
            for row in range(self.tableModel.rowCount()):
                if self.tableModel.item(row, 0).data(QtCore.Qt.CheckStateRole):
                    self.dumpBtn.setEnabled(True)
                    return
            self.dumpBtn.setEnabled(False)
            return
        self.dumpBtn.setEnabled(False)
        QtWidgets.QMessageBox.critical(
            self, 
            'MIDI connection lost', 
            'Output MIDI connection required.\nPlease check connections and try again.', 
            QtWidgets.QMessageBox.Ok
            )

    def midiEventReceived(self, event):
        pass

    def computeEta(self, *args):
        time = 0
        interval = self.delaySpin.value() + 150
        for row in range(self.tableModel.rowCount()):
            if self.tableModel.item(row, 0).data(QtCore.Qt.CheckStateRole):
                time += interval
        self.setEta(time)

    def exec_(self, collection, sounds=True):
#        self.dumpBtn.setEnabled(any(self.main.connections[1]))
        res = DumpDialog.exec_(self, collection, sounds)
        self.sourceModel = self.tableModel = self.selectedCollection = None
        return res



