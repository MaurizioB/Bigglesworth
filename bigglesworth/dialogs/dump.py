from string import uppercase
from unidecode import unidecode

from Qt import QtCore, QtGui, QtWidgets, QtSql

from bigglesworth.utils import loadUi, localPath, getName, setBold, setItalic, Enum
from bigglesworth.const import (chr2ord, UidColumn, LocationColumn, NameColumn, CatColumn, TagsColumn, FactoryColumn, DataRole, 
    INIT, IDE, IDW, CHK, SNDR, SNDD, END, factoryPresetsNamesDict)
from bigglesworth.widgets import CategoryDelegate, TagsDelegate, CheckBoxDelegate, MidiConnectionsDialog
from bigglesworth.midiutils import SysExEvent, SYSEX
from bigglesworth.parameters import Parameters, orderedParameterGroups
from bigglesworth.dialogs import UnknownFileImport, SoundFileImport, QuestionMessageBox
from bigglesworth.libs import midifile

IndexesRole = QtCore.Qt.UserRole + 32
CollectionRole = IndexesRole + 1
CheckColumn = UidColumn
DupColumn = TagsColumn
DestColumn = FactoryColumn

paramFields = []
paramPairs = []
for p in Parameters.parameterData:
    if p.attr.startswith('reserved') or p.attr.startswith('nameChar') or p.attr == 'category':
        continue
    paramFields.append('{a} = :{a}'.format(a=p.attr))
    paramPairs.append((':' + p.attr, p.id))
prepareStr = 'SELECT uid FROM sounds WHERE (' + ' AND '.join(paramFields) + ')'


class ValueProxy(QtCore.QSortFilterProxyModel):
    validIndexes = currentIndexes = []
    currentData = None

    def data(self, index, role):
        if role in (QtCore.Qt.DisplayRole, QtCore.Qt.ToolTipRole):
            if self.currentData:
                if index.column() == 1:
                    id = self.mapToSource(index).row()
                    if id not in self.currentIndexes:
                        return ''
                    value = self.currentData[id]
                    valueText = Parameters.parameterData[id].valueDict[value]
                    if role == QtCore.Qt.ToolTipRole:
                        valueText += ' ({})'.format(value)
                    return valueText
            elif index.column() == 0:
                return 'No sound selected'
        return QtCore.QSortFilterProxyModel.data(self, index, role)

    def headerData(self, section, orientation, role):
        if not self.currentData and role == QtCore.Qt.DisplayRole and orientation == QtCore.Qt.Vertical and section == 0:
            return ''
        if orientation == QtCore.Qt.Vertical and role == QtCore.Qt.TextAlignmentRole:
            return QtCore.Qt.AlignCenter
        return QtCore.QSortFilterProxyModel.headerData(self, section, orientation, role)

    def setFilter(self, data, indexes=None):
        if data != self.currentData:
            self.currentData = data
        if indexes is not None:
            self.currentIndexes = indexes
        else:
            self.currentIndexes = self.validIndexes
        self.invalidateFilter()

    def filterAcceptsRow(self, row, parent):
        if not self.currentData:
            return True if row == 0 else False
        return True if row in self.currentIndexes else False


class CollectionValidator(QtGui.QRegExpValidator):
    valid = QtCore.pyqtSignal(bool)
    def __init__(self):
        QtGui.QRegExpValidator.__init__(self, QtCore.QRegExp(r'^(?!.* {2})(?=\S)[a-zA-Z0-9\ \-\_]+$'))
        self.referenceModel = QtWidgets.QApplication.instance().database.referenceModel
        self.allCollections = [c.lower() for c in self.referenceModel.allCollections + factoryPresetsNamesDict.values()]
        self.allCollections.append('main library')

    def validate(self, input, pos):
        valid, input, pos = QtGui.QRegExpValidator.validate(self, input, pos)
        if valid == self.Acceptable:
            if input.lower() in self.allCollections:
                valid = self.Intermediate
        #technically this is not right, but since QLineEdit automatically manages the correction
        #we assume that the Unacceptable input will not be taken into account (hence it will be
        #Acceptable or Intermediate anyway)
        self.valid.emit(True if valid != self.Intermediate else False)
        return valid, input, pos


class CollectionNameEdit(QtWidgets.QLineEdit):
    valid = QtCore.pyqtSignal(bool)

    def __init__(self, *args, **kwargs):
        QtWidgets.QLineEdit.__init__(self, *args, **kwargs)
        self.validator = CollectionValidator()
        self.setValidator(self.validator)
        self._valid = False
        self.isValid = lambda: self._valid
        self.validator.valid.connect(self.setValid)
        self.validator.valid.connect(self.valid)
        palette = self.palette()
        self.defaultColor = (
            (palette.Disabled, palette.color(palette.Disabled, palette.Text)), 
            (palette.Active, palette.color(palette.Active, palette.Text)), 
            (palette.Inactive, palette.color(palette.Inactive, palette.Text))
            )

#    def focusInEvent(self, event):
#        self.validator.validate(self.text(), self.cursorPosition())
#        QtWidgets.QLineEdit.focusInEvent(self, event)

    def setValid(self, valid):
        self._valid = valid
        palette = self.palette()
        if valid:
            for group, color in self.defaultColor:
                palette.setColor(group, palette.Text, color)
        else:
            red = QtGui.QColor(QtCore.Qt.red)
            palette.setColor(palette.Text, red)
            red.setAlpha(128)
            palette.setColor(palette.Disabled, palette.Text, red)
        self.setPalette(palette)


class LocationDelegate(QtWidgets.QStyledItemDelegate):
    def paint(self, qp, option, index):
        self.initStyleOption(option, index)
        if index.sibling(index.row(), CheckColumn).data(QtCore.Qt.CheckStateRole):
            pos = index.data(QtCore.Qt.DisplayRole)
            if pos is not None:
                if pos & 1024:
                    option.font.setBold(True)
                    pos -= 1024
                if pos & 2048:
                    option.font.setStrikeOut(True)
                    pos -= 2048
                option.text = '{}{:03}'.format(uppercase[pos >> 7], (pos & 127) + 1)
                option.displayAlignment = QtCore.Qt.AlignCenter
        else:
            option.text = ''
        QtWidgets.QApplication.style().drawControl(QtWidgets.QStyle.CE_ItemViewItem, option, qp)


class ImportWaiter(QtWidgets.QDialog):
    shown = False
    def __init__(self, parent):
        QtWidgets.QDialog.__init__(self, parent)
        l = QtWidgets.QHBoxLayout()
        self.setLayout(l)
        l.addWidget(QtWidgets.QLabel('Loading content, please wait...'))

    def showEvent(self, event):
        if not self.shown:
            self.shown = True
            parent = self.parent()
            while parent and not parent.isVisible():
                parent = parent.parent()
            center = parent.geometry().center()
            self.move(center.x() - self.width() / 2, center.y() - self.height() / 2)

    def hide(self):
        QtWidgets.QDialog.hide(self)
        self.shown = False

    def closeEvent(self, event):
        event.ignore()

    def accept(self):
        return

    def reject(self):
        return


class BaseImportDialog(QtWidgets.QDialog):
    shown = False
    headerLabels = ['', '', 'Name', 'Category', 'Duplicates', 'Dest']

    NoImport, LibraryImport, CollectionImport, NewImport, Overwrite, AutoIndex, OpenSound = Enum(0, 1, 2, 4, 64, 128, 1024)

    def __init__(self, parent, dumpBuffer=None):
        QtWidgets.QDialog.__init__(self, parent)
        loadUi(localPath('ui/soundimport.ui'), self)
        self.waiter = ImportWaiter(self)
        self._isDumpDialog = True
        self.main = QtWidgets.QApplication.instance()
        self.database = self.main.database
        self.query = QtSql.QSqlQuery()
        self.query.prepare(prepareStr)
        self.referenceModel = self.database.referenceModel
        self.allCollections = self.referenceModel.allCollections
        self.collectionBuffer = {}

        self.okBtn = self.buttonBox.button(self.buttonBox.Ok)
        self.okBtn.setText('Import')
        self.okBtn.setEnabled(False)
        self.okBtn.clicked.connect(self.accept)
        self.openBtn = self.buttonBox.button(self.buttonBox.Open)
        self.openBtn.setEnabled(False)
        self.openBtn.clicked.connect(self.openSound)

        self.cornerButton = self.valueTable.findChild(QtWidgets.QAbstractButton)
        l = QtWidgets.QHBoxLayout()
        self.cornerButton.setLayout(l)
        indexLbl = QtWidgets.QLabel('Idx')
        indexLbl.setAlignment(QtCore.Qt.AlignCenter)
        l.addWidget(indexLbl)
        self.valueTable.verticalHeader().setMinimumWidth(self.fontMetrics().width('Idx') * 2)

        self.collectionCombo.addItems(self.referenceModel.collections)
        self.collectionCombo.setItemData(1, QtGui.QIcon(':/images/bigglesworth_logo.svg'), QtCore.Qt.DecorationRole)
        self.collectionCombo.currentIndexChanged.connect(self.collectionChanged)

        self.importCombo.currentIndexChanged.connect(self.checkImport)

        self.dumpModel = QtGui.QStandardItemModel()
        self.dumpModel.dataChanged.connect(self.checkImport)
        self.dumpTable.setModel(self.dumpModel)
        self.resetModel()
        self.dumpTable.verticalHeader().setResizeMode(QtWidgets.QHeaderView.Fixed)
        self.dumpTable.verticalHeader().setDefaultSectionSize(self.fontMetrics().height() * 1.5)
        self.dumpTable.horizontalHeader().setResizeMode(QtWidgets.QHeaderView.Fixed)
        self.dumpTable.horizontalHeader().setResizeMode(DupColumn, QtWidgets.QHeaderView.Stretch)
        self.dumpTable.clicked.connect(self.showValues)
        self.dumpTable.doubleClicked.connect(self.toggleCheck)
        self.dumpTable.customContextMenuRequested.connect(self.dumpTableMenu)
        self.dumpTable.selectionModel().selectionChanged.connect(self.showValues)
        self.paramTree.clicked.connect(self.showValues)

        checkBoxDelegate = CheckBoxDelegate(self.dumpTable)
        self.dumpTable.setItemDelegateForColumn(0, checkBoxDelegate)
        catDelegate = CategoryDelegate(self.dumpTable)
        self.dumpTable.setItemDelegateForColumn(CatColumn, catDelegate)
        destDelegate = LocationDelegate()
        self.dumpTable.setItemDelegateForColumn(DestColumn, destDelegate)

        self.timeout = QtCore.QTimer()
        self.timeout.setInterval(1000)

        self.dumper = SmallDumper(self)
        self.timeout.timeout.connect(self.dumper.accept)
        self.dumper.closeAsk = False
        self.dumper.accepted.connect(self.checkImport)
        self.dumper.accepted.connect(self.timeout.stop)
        self.dumper.rejected.connect(self.checkImport)
        self.dumper.rejected.connect(self.timeout.stop)

        self.tot = 0
        while dumpBuffer:
            self.processData(dumpBuffer.pop(0))

#        self.indexModeGroup.buttonClicked.connect(self.checkImport)
        
        self.collIndexModeGroup.buttonClicked.connect(self.checkImport)
        self.newIndexModeGroup.buttonClicked.connect(self.checkImport)

#        self.newRadio.toggled.connect(lambda state: self.newEdit.setFocus() if state else None)
        self.newEdit.valid.connect(self.checkImport)
        self.newEdit.valid.connect(self.setNewIcon)
        self.overwriteChk.toggled.connect(self.checkImport)

        self.selectAllBtn.clicked.connect(self.dumpTable.selectAll)
        self.selectNoneBtn.clicked.connect(self.dumpTable.clearSelection)
        self.checkSelectionBtn.clicked.connect(self.checkAll)
        self.uncheckSelectionBtn.clicked.connect(self.checkNone)

        self.paramSplitter.setCollapsible(1, False)
        self.paramModel = QtGui.QStandardItemModel()
        self.paramTree.setModel(self.paramModel)
        self.rootParam = QtGui.QStandardItem('Parameters')
        self.paramModel.appendRow(self.rootParam)

        self.valueModel = QtGui.QStandardItemModel()
        self.valueModel.setHorizontalHeaderLabels(['Parameter', 'Value'])
        self.valueProxy = ValueProxy()
        self.valueProxy.setFilter([], [])
        self.valueProxy.setSourceModel(self.valueModel)
        self.valueTable.setModel(self.valueProxy)
        self.valueTable.horizontalHeader().setResizeMode(0, QtWidgets.QHeaderView.Stretch)

        paramTreeDict = {}
        self.validIndexes = []
        for p in Parameters.parameterData:
            if p.attr.startswith('reserved'):
                self.valueModel.appendRow(QtGui.QStandardItem())
                continue
            ValueProxy.validIndexes.append(p.id)
            self.valueModel.appendRow(QtGui.QStandardItem(p.fullName))
            self.validIndexes.append(p.id)
            family = p.family if p.family else 'General'
            groupItem, families, groupIndexes = paramTreeDict.get(p.group, (None, {}, []))
            if not groupItem:
                groupItem = QtGui.QStandardItem(p.group)
                paramTreeDict[p.group] = groupItem, families, groupIndexes
            groupIndexes.append(p.id)
            groupItem.setData(groupIndexes, IndexesRole)
            familyItem, familyIndexes = families.get(family, (None, []))
            if not familyItem:
                familyItem = QtGui.QStandardItem(family)
                families[family] = familyItem, familyIndexes
                groupItem.appendRow(familyItem)
            familyIndexes.append(p.id)
            familyItem.setData(familyIndexes, IndexesRole)
        for group in orderedParameterGroups:
            self.rootParam.appendRow(paramTreeDict[group][0])
        self.paramTree.expand(self.paramModel.index(0, 0))
        self.mode = 0

        self.queueTimer = QtCore.QTimer()
        self.queueTimer.setSingleShot(True)
        self.queueTimer.setInterval(8)
        self.queueTimer.timeout.connect(self.checkImport)

        self.adjustTimer = QtCore.QTimer()
        self.adjustTimer.setSingleShot(True)
        self.adjustTimer.setInterval(50)
        self.adjustTimer.timeout.connect(self.adjustTableContents)

    def openSound(self):
        self.mode |= self.OpenSound
        self.accept()

    def resetModel(self):
        self.dumpModel.clear()
        self.dumpModel.setHorizontalHeaderLabels(self.headerLabels)
        self.dumpTable.setColumnHidden(LocationColumn, True)
        self.dumpTable.resizeColumnToContents(0)
        self.dumpTable.resizeColumnToContents(CatColumn)
        self.dumpTable.resizeColumnToContents(DestColumn)
#        self.dumpTable.horizontalHeader().setResizeMode(QtWidgets.QHeaderView.Fixed)
        self.dumpTable.horizontalHeader().setResizeMode(NameColumn, QtWidgets.QHeaderView.Stretch)
        self.dumpTable.horizontalHeader().setResizeMode(DupColumn, QtWidgets.QHeaderView.Stretch)

    def processData(self, data):
        self.dumpModel.dataChanged.disconnect(self.checkImport)
        bank, prog = data[:2]
        data = data[2:]
        checkItem = QtGui.QStandardItem()
        checkItem.setData(data, DataRole)
        indexItem = QtGui.QStandardItem()
        indexItem.setData((bank << 7) + prog, QtCore.Qt.DisplayRole)
        destItem = QtGui.QStandardItem()
        nameItem = QtGui.QStandardItem(getName(data[363:379]))
        catItem = QtGui.QStandardItem()
        catItem.setData(data[379], QtCore.Qt.DisplayRole)

        for attr, id in paramPairs:
            value = Parameters.parameterData[id].range.sanitize(data[id])
            self.query.bindValue(attr, value)
        if not self.query.exec_():
            print(self.query.lastError().driverText(), self.query.lastError().databaseText())
        duplicates = {}
        while self.query.next():
            uid = self.query.value(0)
            if uid in duplicates:
                continue
            duplicates[uid] = self.database.getNameFromUid(uid), self.database.getCollectionsFromUid(uid, False)
        names = []
        colls = []
        for k in sorted(duplicates, key=lambda v: duplicates[v][0]):
            name, collList = duplicates[k]
            collList = [self.allCollections[c] for c in collList]
            if not collList:
                collList = ['(Main library only)']
            names.append(name.strip())
            colls.append('<b>{}</b>: {}'.format(name.strip(), ', '.join(factoryPresetsNamesDict.get(c, c) for c in collList)))
        dupItem = QtGui.QStandardItem(', '.join(set(names)))
        if colls:
            colls = set(colls)
            dupItem.setData('Duplicate locations:<ul><li>' + '</li><li>'.join(coll for coll in colls) + '</li></ul>'
                , QtCore.Qt.ToolTipRole)
        
        self.dumpModel.appendRow([checkItem, indexItem, nameItem, catItem, dupItem, destItem])

        if self._isDumpDialog:
            if bank < 0x20:
                if bank == 0:
                    if prog > 0:
                        if self.dumpModel.rowCount() > 1:
                            self.tot = 128
                        else:
                            self.tot = 1
                    else:
                        self.tot = 1
                else:
                    if self.dumpModel.rowCount() > 127:
                        self.tot = 1024
                    else:
                        self.tot = 128
                index = '{}{:03}'.format(uppercase[bank], prog + 1)
            else:
                #TODO: check this for multiple sound edit buffer manual sends
                if self.dumpModel.rowCount() == 1 and prog == 0:
                    index = 'Buff'
                    self.tot = 1
                else:
                    index = 'M{:02}'.format(prog + 1)
                    self.tot = 16
        else:
            try:
                index = '{}{:03}'.format(uppercase[bank], prog + 1)
            except:
                index = ''
        self.dumpModel.setHeaderData(self.dumpModel.rowCount() - 1, QtCore.Qt.Vertical, index, QtCore.Qt.DisplayRole)
        if bank == 0x7f and prog > 1 and self.dumpModel.rowCount() > 1:
            self.dumpModel.setHeaderData(0, QtCore.Qt.Vertical, 'M01', QtCore.Qt.DisplayRole)
        self.dumpModel.dataChanged.connect(self.checkImport)
        if self.isVisible():
            self.waiter.hide()
        self.adjustTimer.start()

    def adjustTableContents(self):
        if self.shown:
            self.dumpTable.scrollToBottom()
        else:
            self.adjustTimer.start()

    def showValues(self, index):
        if self.sender() == self.dumpTable.selectionModel():
            if not index.indexes():
                self.valueProxy.setFilter([], [])
                self.paramGroupBox.setEnabled(False)
                self.paramGroupBox.setTitle('Sound parameters')
                self.valueTable.setSpan(0, 0, 1, 2)
            return
        elif self.sender() == self.dumpTable:
            self.paramGroupBox.setTitle('Sound parameters for "{}"'.format(
                index.sibling(index.row(), NameColumn).data().strip()))
            data = index.sibling(index.row(), CheckColumn).data(DataRole)
            if self.paramTree.currentIndex().isValid():
                indexes = self.paramTree.currentIndex().data(IndexesRole)
            else:
                indexes = None
                self.paramTree.blockSignals(True)
                self.paramTree.setCurrentIndex(self.paramModel.indexFromItem(self.rootParam))
                self.paramTree.blockSignals(False)
#                indexes = self.rootParam.data(IndexesRole)
        else:
            indexes = index.data(IndexesRole)
            currentIndex = self.dumpTable.currentIndex()
            data = currentIndex.sibling(currentIndex.row(), CheckColumn).data(DataRole)
        self.paramGroupBox.setEnabled(True)
        self.valueProxy.setFilter(data, indexes)
#        self.valueTable.setSpan(0, 0, 1, 1)
        self.valueTable.resizeColumnToContents(1)
        self.valueTable.viewport().update()

    def dumpTableMenu(self, pos):
        menu = QtWidgets.QMenu()
        selectAllAction = menu.addAction(QtGui.QIcon.fromTheme('edit-select-all'), 'Select all')
        selectNoneAction = menu.addAction(QtGui.QIcon.fromTheme('edit-select-none'), 'Select none')
        menu.addSeparator()
        checkAction = menu.addAction(QtGui.QIcon.fromTheme('checkmark'), 'Check selected')
        uncheckAction = menu.addAction(QtGui.QIcon.fromTheme('list-remove'), 'Uncheck selected')
        if not self.dumpTable.selectionModel().selectedRows():
            checkAction.setEnabled(False)
            uncheckAction.setEnabled(False)
        res = menu.exec_(QtGui.QCursor.pos())
        if res == selectAllAction:
            self.dumpTable.selectAll()
        elif res == selectNoneAction:
            self.dumpTable.clearSelection()
        elif res == checkAction:
            self.checkAll()
        elif res == uncheckAction:
            self.checkNone()

    def toggleCheck(self, index):
        index = index.sibling(index.row(), CheckColumn)
        self.dumpModel.setData(index, not index.data(QtCore.Qt.CheckStateRole), QtCore.Qt.CheckStateRole)

    def checkAll(self):
        for index in self.dumpTable.selectionModel().selectedRows():
            self.dumpModel.setData(index, QtCore.Qt.Checked, QtCore.Qt.CheckStateRole)

    def checkNone(self):
        for index in self.dumpTable.selectionModel().selectedRows():
            self.dumpModel.setData(index, QtCore.Qt.Unchecked, QtCore.Qt.CheckStateRole)

    def collectionChanged(self, id):
        self.collImportModeWidget.setEnabled(id)
        if id:
            self.checkImport()

    def setNewIcon(self, valid):
        if valid:
            self.newIcon.setPixmap(QtGui.QPixmap())
            self.newIcon.setToolTip('')
            self.newEdit.setToolTip('')
        else:
            option = QtWidgets.QStyleOptionFrame()
            option.initFrom(self.newEdit)
            height = self.style().subElementRect(
                QtWidgets.QStyle.SE_LineEditContents, option, self.newEdit).height() - \
                self.newIcon.lineWidth() * 8
            self.newIcon.setPixmap(QtGui.QIcon.fromTheme('emblem-warning').pixmap(height))
            self.newIcon.setToolTip('The selected name is invalid')
            self.newEdit.setToolTip('The selected name is invalid')

    def clearDestIndexes(self, selected):
        try:
            self.dumpModel.dataChanged.disconnect(self.checkImport)
        except:
            pass
        for row, srcIndex in selected:
            self.dumpModel.item(row, DestColumn).setData(None, QtCore.Qt.DisplayRole)
        self.dumpModel.dataChanged.connect(self.checkImport)
        self.dumpModel.layoutChanged.emit()

    def getSelected(self):
        return [(r, self.dumpModel.item(r, LocationColumn).data(QtCore.Qt.DisplayRole)) for r in range(self.dumpModel.rowCount()) \
            if self.dumpModel.item(r, CheckColumn).data(QtCore.Qt.CheckStateRole)]

    def getSelectedSoundData(self):
        data = {}
        for row in range(self.dumpModel.rowCount()):
            checkItem = self.dumpModel.item(row, CheckColumn)
            if checkItem.data(QtCore.Qt.CheckStateRole):
                if self.mode & self.CollectionImport:
                    index = self.dumpModel.item(row, DestColumn).data(QtCore.Qt.DisplayRole)
                else:
                    index = row
                data[index] = checkItem.data(DataRole)
        return data

    def checkImport(self):
        #if dumpModel is the sender, "queue" the update to avoid unnecessary
        #checks for multiple dataChanged signals
        if self.sender() == self.dumpModel:
            self.queueTimer.start()
            return
        if self.sender() == self.dumper and self.dumpModel.rowCount() == 1:
            self.dumpModel.blockSignals(True)
            self.dumpModel.item(0, CheckColumn).setCheckState(True)
            self.dumpModel.blockSignals(False)


        selected = self.getSelected()
        count = len(selected)

        if count == 1:
            self.openBtn.setEnabled(True)
            if self.importCombo.currentIndex():
                text = 'Import and edit'
            else:
                text = 'Edit'
            self.openBtn.setText(text)
        else:
            self.openBtn.setEnabled(False)
        self.destinationStack.setEnabled(count)
        self.importCombo.setEnabled(count)
        if not self.importCombo.currentIndex() or not count:
            self.countLbl.setText('0')
            self.okBtn.setEnabled(False)
            self.clearDestIndexes(selected)
            return

        self.mode = self.LibraryImport

        if self.importCombo.currentIndex() == 1:
            if self.collectionCombo.currentIndex():
                if count > 1024:
                    self.collImportModeWidget.setEnabled(False)
                    self.okBtn.setEnabled(False)
                    self.clearDestIndexes()
                    return
                self.collImportModeWidget.setEnabled(True)
                self.mode |= self.CollectionImport
                collection = self.collectionCombo.itemData(self.collectionCombo.currentIndex(), CollectionRole)
                collIndexes = self.collectionBuffer.get(collection)
                if not collIndexes:
                    collIndexes = self.collectionBuffer.setdefault(collection, self.database.getIndexesForCollection(collection))
                if self.collAutoIndexRadio.isChecked():
                    self.mode |= self.AutoIndex
                    self.countLbl.setText(str(count))
                    self.okBtn.setEnabled(True)
                if len(collIndexes) + count > 1024:
                    self.overwriteChk.setEnabled(True)
                    if not self.overwriteChk.isChecked():
                        self.okBtn.setEnabled(False)
                else:
                    self.overwriteChk.setEnabled(self.collSourceIndexRadio.isChecked())
                    if self.overwriteChk.isChecked():
                        self.okBtn.setEnabled(True)
                if self.overwriteChk.isChecked():
                    self.mode |= self.Overwrite
            else:
                self.collImportModeWidget.setEnabled(False)
                collIndexes = []
        elif self.importCombo.currentIndex() == 2:
            if count > 1024:
                self.okBtn.setEnabled(False)
                self.clearDestIndexes(selected)
                return
            self.okBtn.setEnabled(True)
            self.mode |= self.CollectionImport | self.NewImport
            if self.newAutoIndexRadio.isChecked():
                self.mode |= self.AutoIndex
            collIndexes = []

        if not self.mode & (self.CollectionImport | self.NewImport):
            self.clearDestIndexes(selected)
            return

        srcIndexList = []
        unknownIndexes = 0
        for row, srcIndex in selected:
            if srcIndex >> 7 > 7:
                unknownIndexes += 1
            else:
                srcIndexList.append(srcIndex)
        hasDuplicates = len(srcIndexList) and len(srcIndexList) != len(set(srcIndexList))
        hasValidIndexes = not hasDuplicates and not unknownIndexes

        self.newSourceIndexRadio.setEnabled(hasValidIndexes)
        if not hasValidIndexes:
            if self.mode & self.NewImport:
                self.okBtn.setEnabled(not self.newSourceIndexRadio.isChecked())
            else:
                self.collSourceIndexRadio.setEnabled(False)
                if self.collSourceIndexRadio.isChecked():
                    self.okBtn.setEnabled(False)
            if not self.okBtn.isEnabled():
                return
        else:
            self.collSourceIndexRadio.setEnabled(True)
            if self.mode & self.CollectionImport and \
                not self.mode & self.AutoIndex and \
                not self.mode & self.Overwrite:
                    self.okBtn.setEnabled(False if set(srcIndexList) & set(collIndexes) else True)

        self.dumpModel.dataChanged.disconnect(self.checkImport)
        if not self.mode & self.NewImport:
#            print('CollectionImport')
            if self.mode & self.Overwrite:
#                print('overwrite')
                if self.mode & self.AutoIndex:
                    if len(collIndexes) + count < 1024:
                        current = 0
                        for row, srcIndex in selected:
                            while current in collIndexes:
                                current += 1
                            self.dumpModel.item(row, DestColumn).setData(current, QtCore.Qt.DisplayRole)
                            current += 1
                    else:
                        current = 0
                        while current + count <= 1024 or current not in collIndexes:
                            current += 1
                        for row, srcIndex in selected:
                            newIndex = current + (1024 if current in collIndexes else 0)
                            self.dumpModel.item(row, DestColumn).setData(newIndex, QtCore.Qt.DisplayRole)
                            current += 1
                else:
                    for row, srcIndex in selected:
                        if srcIndex in collIndexes:
                            srcIndex += 1024
                        self.dumpModel.item(row, DestColumn).setData(srcIndex, QtCore.Qt.DisplayRole)
            else:
#                print('no overwrite')
                if self.mode & self.AutoIndex:
#                    print('AutoIndex')
                    current = 0
                    for row, srcIndex in selected:
                        while current in collIndexes:
                            current += 1
                        self.dumpModel.item(row, DestColumn).setData(current, QtCore.Qt.DisplayRole)
                        current += 1
                else:
                    for row, srcIndex in selected:
                        if srcIndex in collIndexes:
                            srcIndex += 2048
                        self.dumpModel.item(row, DestColumn).setData(srcIndex, QtCore.Qt.DisplayRole)
        elif self.mode & self.NewImport:
#            print('NewImport')
            if self.mode & self.AutoIndex:
#                print('AutoIndex')
                for current, (row, srcIndex) in enumerate(selected):
                    self.dumpModel.item(row, DestColumn).setData(current, QtCore.Qt.DisplayRole)
            else:
#                print('SourceIndex')
                done = {}
                invalid = []
                for row, srcIndex in selected:
                    if srcIndex >> 7 <= 7:
                        if srcIndex in done:
                            invalid.append((row, srcIndex))
                            continue
                        self.dumpModel.item(row, DestColumn).setData(srcIndex, QtCore.Qt.DisplayRole)
                        done[srcIndex] = row
                    else:
                        invalid.append((row, srcIndex))
                if invalid:
                    orphan = set()
                    for row, srcIndex in invalid:
                        if srcIndex in done:
                            srcIndex = max(done) + 1
                            if srcIndex >= 1024:
                                srcIndex = 0
                            while srcIndex in done:
                                srcIndex += 1
                            self.dumpModel.item(row, DestColumn).setData(srcIndex, QtCore.Qt.DisplayRole)
                            done[srcIndex] = row
                        else:
                            strict = set(done.values()) - orphan
                            if row < min(strict):
                                current = 0
                            else:
                                current = max(done) + 1
                            while current in done:
                                current += 1
                            self.dumpModel.item(row, DestColumn).setData(current, QtCore.Qt.DisplayRole)
                            done[current] = row
                            orphan.add(row)

        self.dumpModel.dataChanged.connect(self.checkImport)
        self.dumpModel.layoutChanged.emit()

    def exec_(self):
        self.valueTable.setSpan(0, 0, 1, 2)
        return QtWidgets.QDialog.exec_(self)


class SourceFileModel(QtCore.QSortFilterProxyModel):
    def data(self, index, role):
        if role == QtCore.Qt.DisplayRole:
            return QtCore.QDir.toNativeSeparators(self.mapToSource(index).data(QtCore.Qt.DisplayRole))
        return QtCore.QSortFilterProxyModel.data(self, index, role)


class SoundImport(BaseImportDialog):
    SysExFile, MidiFile = Enum(1, 2)
    
    def __init__(self, parent, filePath=None):
        BaseImportDialog.__init__(self, parent)
        self.setWindowTitle('Sound import')
        self._isDumpDialog = False
        self.dumpHeader.hide()
        self.browseBtn.clicked.connect(self.openFileDialog)
        self.sourceFileModel = QtGui.QStandardItemModel()
        self.pathModel = SourceFileModel()
        self.pathModel.setSourceModel(self.sourceFileModel)
        self.sourceFileView.setModel(self.pathModel)
        self.filePath = filePath
        self._loadError = None
#        self.sourceFileView.setMaximumHeight(self.sourceFileView.sizeHintForRow(0))

    @property
    def filePath(self):
        return self._filePath

    @filePath.setter
    def filePath(self, path):
        self._filePath = path
        if path:
            item = QtGui.QStandardItem(path)
            self.sourceFileModel.appendRow(item)
            count = max(1, min(self.sourceFileModel.rowCount(), 4)) + .5
            self.sourceFileView.setMaximumHeight(self.sourceFileView.sizeHintForRow(0) * count)
#        self.filePathEdit.setText(QtCore.QDir.toNativeSeparators(path))

    def showEvent(self, event):
        if not self.shown:
            self.shown = True
            self.waiter.hide()
            if self._loadError:
                QtCore.QTimer.singleShot(0, lambda: QtWidgets.QMessageBox.critical(self, 
                    'File error', 
                    'A problem occurred while loading the file:\n{}'.format(self._loadError), 
                    QtWidgets.QMessageBox.Ok))
            QtCore.QTimer.singleShot(0, self.dumpModel.layoutChanged.emit)

    def processSysEx(self):
        try:
            with open(self.filePath, 'rb') as syx:
                full = iter(map(ord, syx.read()))
            self.waiter.show()
            while True:
                init = full.next()
                if init != INIT:
                    break
                device = full.next(), full.next()
                #devId
                full.next()
                msgType = full.next()
                if device != (IDW, IDE) and msgType != SNDD:
                    current = None
                    while current != 0xf7:
                        current = full.next()
                    continue
                current = None
                data = []
                while current != 0xf7:
                    current = full.next()
                    data.append(current)
                self.processData(data[:-2])
        except StopIteration:
            return True
        except Exception as e:
            self._loadError = e
            return False

    def processMidi(self):
        try:
            content = midifile.read_midifile(self.filePath)
            self.waiter.show()
            QtWidgets.QApplication.processEvents()
            for track in content:
                for event in track:
                    if isinstance(event, midifile.SysexEvent) and \
                        len(event.data) == 392 and event.data[:4] == [131, 7, IDW, IDE] and event.data[5] == SNDD:
                            self.processData(event.data[6:-1])
            return True
        except Exception as e:
            self._loadError = e
            return False

    def openFileDialog(self):
        clear = False
#        currentCount = self.dumpModel.rowCount()
#        selected = [(r, self.dumpModel.item(r, LocationColumn).data(QtCore.Qt.DisplayRole)) for r in range(self.dumpModel.rowCount()) \
#            if self.dumpModel.item(r, CheckColumn).data(QtCore.Qt.CheckStateRole)]
#        currentCount = len(selected)
        if self.dumpModel.rowCount():
            message = 'Add to the existing contents or clear the current list?'
            details = ''
            if len(self.getSelected()) >= 1024:
                '<br/><br/><b>NOTE</b>: The current list already contains 1024 or more items. See "Details" to know more.'
                details = 'A collection can contain up to 1024 sounds. If you select more sounds, import to existing/new collection' \
                    'will be disabled, and they will only be added to the "Main library".'
            res = QuestionMessageBox(self, 
                'Import sounds', message, details, 
                buttons={QtWidgets.QMessageBox.Open: ('Add', QtGui.QIcon.fromTheme('list-add')), 
                    QtWidgets.QMessageBox.Discard: ('Clear', QtGui.QIcon.fromTheme('document-new')), 
                    QtWidgets.QMessageBox.Cancel: None
                    }).exec_()
            if res == QtWidgets.QMessageBox.Cancel:
                return
            elif res == QtWidgets.QMessageBox.Discard:
                clear = True
        dialog = SoundFileImport(self, self.filePath)
        res = dialog.exec_()
        if res:
            if dialog._selectedContent & dialog.SoundDump:
                if any(self.sourceFileModel.findItems(res)) and \
                    (self.sourceFileModel.rowCount() == 1 or not clear):
                    QtWidgets.QMessageBox.warning(self, 
                        'File already loaded', 
                        'The selected file has already been imported.', 
                        QtWidgets.QMessageBox.Ok)
                    return
                if clear:
                    self.sourceFileModel.clear()
                    self.resetModel()
                self.filePath = res
                if dialog._selectedContent & dialog.SysExFile:
                    self.processSysEx()
                else:
                    self.processMidi()
                self.checkImport()
            else:
                QtWidgets.QMessageBox.critical(self, 
                    'File content error', 
                    'The selected file does not contain valid sound data.', 
                    QtWidgets.QMessageBox.Ok)

    def getValidName(self, filePath):
        fileName = unidecode(QtCore.QFileInfo(filePath).completeBaseName())
        newName = ''.join(c for c in fileName if c in chr2ord)[:32]
        if not newName:
            newName = 'New ' + QtCore.QDate.currentDate().toString('dd-MM-yy')
        allCollections = [c.lower() for c in self.referenceModel.allCollections + factoryPresetsNamesDict.values()]
        allCollections.append('main library')
        if newName.lower() in allCollections:
            suffix = 1
            baseName = newName
            newName += '1'
            while newName.lower() in allCollections:
                newName = baseName + str(suffix)
        return newName

    def exec_(self, uriList=None, collection=None):
        if uriList:
            self.waiter.show()
            QtWidgets.QApplication.processEvents()
            validPaths = []
            for uri in uriList:
                uri = QtCore.QUrl(uri)
                if not uri.isLocalFile():
                    continue
                path = uri.toLocalFile()
                self.filePath = path
                if not self.processMidi():
                    if self.processSysEx():
                        validPaths.append(path)
                        self._loadError = None
                else:
                    validPaths.append(path)
                    self._loadError = None
            if collection:
                self.collectionCombo.setCurrentIndex(self.referenceModel.collections.index(collection) + 1)
                self.importCombo.setCurrentIndex(1)
            if validPaths:
                if len(validPaths) == 1:
                    self.newEdit.setText(self.getValidName(validPaths[0]))
                else:
                    self.newEdit.setText('Imported ' + QtCore.QDate.currentDate().toString('dd-MM-yy'))
                self.dumpTable.selectAll()
                self.checkAll()
        else:
            dialog = UnknownFileImport(self.parent())
            res = dialog.exec_()
            if not res:
                return
            if dialog._selectedContent & dialog.SoundDump:
                self.filePath = res
                if dialog._selectedContent & dialog.SysExFile:
                    self.processSysEx()
                else:
                    self.processMidi()
                self.newEdit.setText(self.getValidName(res))
                self.dumpModel.layoutChanged.emit()
                self.dumpTable.scrollToTop()
            else:
                self._loadError = 'Invalid file content'
        return BaseImportDialog.exec_(self)


class BlofeldDumper(BaseImportDialog):
    def __init__(self, parent, dumpBuffer=None):
        BaseImportDialog.__init__(self, parent, dumpBuffer)
        self.setWindowTitle('Dump receive')
        self.importHeader.hide()

    def midiEventReceived(self, event):
        if event.type != SYSEX:
            return
        if event.sysex[4] != SNDD:
            return
        self.processData(event.sysex[5:390])

    def processData(self, data):
        BaseImportDialog.processData(self, data)

        if not self.isVisible():
            return
        self.dumper.show()
        if self.dumper.tot != self.tot:
            self.dumper.start(tot=self.tot)
        self.dumper.count = self.dumpModel.rowCount()
        self.timeout.start()

    def exec_(self):
        self.newEdit.setText('Dump ' + QtCore.QDate.currentDate().toString('dd-MM-yy'))
        QtCore.QTimer.singleShot(0, lambda: [self.dumper.start(self.tot), self.timeout.start()])
        return BaseImportDialog.exec_(self)


class SmallDumper(QtWidgets.QDialog):
    def __init__(self, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        loadUi(localPath('ui/smalldumper.ui'), self)
        self._isDumpDialog = True
        self.setModal(True)
        self._count = 0
        self.closeable = False
        self.closeAsk = True
        self.closeMessage = 'Stop the dump process?'

    def closeEvent(self, event):
        if self.closeable:
            event.accept()
            return
        else:
            if self.closeAsk and QtWidgets.QMessageBox.question(self, 
                'Stop dump', 
                self.closeMessage, 
                QtWidgets.QMessageBox.Ok|QtWidgets.QMessageBox.Cancel
                ) == QtWidgets.QMessageBox.Ok:
                    event.accept()
                    return
        event.ignore()

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

    def start(self, tot=1, uid=None, collection=None, collectionIndex=None):
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
        self._isDumpDialog = True
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
        self._isDumpDialog = True
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

        #required to avoid font override of the popup, see setCollection()
        self.collectionComboView = QtWidgets.QListView()
        self.collectionCombo.setView(self.collectionComboView)
        self.collectionCombo.currentIndexChanged.connect(self.setCollection)
        self.sourceModel = self.selectedCollection = self.tableModel = None
        self.banksWidget.itemsChanged.connect(self.bankSelect)
        self.delaySpin.valueChanged.connect(self.computeEta)

        self.normalFont = self.font()
        self.strokeFont = self.font()
        self.strokeFont.setStrikeOut(True)

        self.dumper = Dumper(self)
        self.midiVisible = False
        self.midiConnectionsDialog = MidiConnectionsDialog(self)
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
                count = 0
                for row in range(128):
                    current = row + shiftBank
                    if current not in self.soundsDict:
                        continue
                    count += 1
                    if not self.tableModel.item(current, 0).data(QtCore.Qt.CheckStateRole):
                        break
                else:
                    if count:
                        banks.add(bank)
        if currentSet != banks:
            self.banksWidget.blockSignals(True)
            self.banksWidget.setItems(banks)
            self.banksWidget.blockSignals(False)
        self.computeEta()

    def setCollection(self, index):
        if self.collectionCombo.itemData(index, CollectionRole) == self.selectedCollection:
            self.collectionCombo.setStyleSheet('''
                QComboBox {
                    font-weight: bold;
                }
                QComboBox QAbstractItemView {
                    font-weight: normal;
                }
            ''')
        else:
            self.collectionCombo.setStyleSheet('')
        data = self.collectionCombo.itemData(index)
        if not data:
            sourceModel = self.database.openCollection(self.collectionCombo.itemData(index, CollectionRole))
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
        if isinstance(self, DumpSendDialog):
            collections = self.database.referenceModel.allCollections
        else:
            collections = self.database.referenceModel.collections

        collectionIndex = collections.index(collection)
        for i, coll in enumerate(collections):
            self.collectionCombo.addItem(factoryPresetsNamesDict.get(coll, coll))
            self.collectionCombo.setItemData(i, coll, CollectionRole)
            if coll in factoryPresetsNamesDict:
                self.collectionCombo.setItemData(i, QtGui.QIcon(':/images/factory.svg'), QtCore.Qt.DecorationRole)
            elif coll == 'Blofeld':
                self.collectionCombo.setItemData(i, QtGui.QIcon(':/images/bigglesworth_logo.svg'), QtCore.Qt.DecorationRole)
            if i == collectionIndex:
                font = QtWidgets.QApplication.font()
                font.setBold(True)
                self.collectionCombo.setItemData(i, font, QtCore.Qt.FontRole)
#        collections = self.database.referenceModel.collections
#        self.collectionCombo.addItems(collections)
#        self.collectionCombo.setItemData(0, QtGui.QIcon.fromTheme('go-home'), QtCore.Qt.DecorationRole)
#        font = self.collectionCombo.font()
#        font.setBold(True)
#        self.collectionCombo.setItemData(collectionIndex, font, QtCore.Qt.FontRole)
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
        elif isinstance(sounds, (tuple, list)):
            for row in sounds:
                self.tableModel.setData(self.tableModel.index(row, CheckColumn), QtCore.Qt.Checked, QtCore.Qt.CheckStateRole)

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
        self.maskObject = None

    def createMaskObject(self):
        from bigglesworth.firstrun import MaskObject
        self.maskObject = MaskObject(self)
        self.maskObject.setVisible(True)

    def destroyMaskObject(self):
        if self.maskObject:
            self.maskObject.deleteLater()
            self.maskObject = None

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

    def resizeEvent(self, event):
        if self.maskObject:
            self.maskObject.resize(self.size())
        QtWidgets.QDialog.resizeEvent(self, event)

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
        self.destroyMaskObject()
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
                current = row + shiftBank
                if current not in self.soundsDict:
                    continue
                if not self.tableModel.item(current, 0).data(QtCore.Qt.CheckStateRole):
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



