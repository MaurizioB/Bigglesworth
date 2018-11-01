from Qt import QtCore, QtGui, QtWidgets, QtSql

from bigglesworth.utils import loadUi
from bigglesworth.const import factoryPresets, factoryPresetsNamesDict
#from bigglesworth.widgets import CheckBoxDelegate


class NewCollectionDialog(QtWidgets.QDialog):
    def __init__(self, parent):
        QtWidgets.QDialog.__init__(self, parent)
        loadUi('ui/newcollection.ui', self)
        self.nameEdit.textChanged.connect(self.checkNames)
        self.okBtn = self.buttonBox.button(self.buttonBox.Ok)
        self.okBtn.setEnabled(False)
        self.cloneCombo.currentIndexChanged.connect(self.cloneSet)
        self.cloneChk.toggled.connect(lambda state: self.cloneSet(self.cloneCombo.currentIndex()) if state else None)
        self.validator = QtGui.QRegExpValidator(QtCore.QRegExp(r'^(?!.* {2})(?=\S)[a-zA-Z0-9\ \-\_]+$'))
        self.nameEdit.setValidator(self.validator)

        self.cloneChk.toggled.connect(self.initWidget.setDisabled)

        self.initBankModel = QtGui.QStandardItemModel()
        self.initBankList.setModel(self.initBankModel)
        banks = iter('ABCDEFGH')
        self.bankItems = []
        for row in range(2):
            items = []
            for column in range(4):
                item = QtGui.QStandardItem('Bank ' + banks.next())
                item.setCheckable(True)
                items.append(item)
                self.bankItems.append(item)
            self.initBankModel.appendRow(items)
        for column in range(4):
            self.initBankList.horizontalHeader().setResizeMode(column, QtWidgets.QHeaderView.Stretch)
        self.initBankList.resizeRowsToContents()
        rowHeight = self.initBankList.verticalHeader().defaultSectionSize()
        self.initBankList.setFixedHeight((rowHeight + self.initBankList.frameWidth() + self.initBankList.lineWidth()) * 2)
        self.bankStates = None

        self.initSelectRadio.toggled.connect(self.initBankList.setEnabled)
        self.initButtonGroup.buttonClicked.connect(self.setInitItems)

        self.adjustSize()

    def setInitItems(self, button):
        if button == self.initAllRadio:
            for bank, item in enumerate(self.bankItems):
                if self.bankStates:
                    if self.bankStates[bank] == QtCore.Qt.Checked:
                        item.setCheckState(QtCore.Qt.Checked)
                    else:
                        item.setCheckState(QtCore.Qt.PartiallyChecked)
                elif item.checkState() != QtCore.Qt.Checked:
                    item.setCheckState(QtCore.Qt.PartiallyChecked)
            self.bankStates = None
        elif button == self.initSelectRadio:
            for bank, item in enumerate(self.bankItems):
                if self.bankStates:
                    if self.bankStates[bank] == QtCore.Qt.Checked:
                        item.setCheckState(QtCore.Qt.Checked)
                    else:
                        item.setCheckState(QtCore.Qt.Unchecked)
                elif item.checkState() != QtCore.Qt.Checked:
                    item.setCheckState(QtCore.Qt.Unchecked)
            self.bankStates = None
        elif button == self.initNoneRadio:
            self.bankStates = []
            for item in self.bankItems:
                self.bankStates.append(item.checkState())
                item.setCheckState(QtCore.Qt.Unchecked)

    def initBanks(self):
        return [bank for bank, item in enumerate(self.bankItems) if item.checkState()]

    def currentIconName(self):
        return self.iconBtn.iconName()

    def cloneSet(self, index):
        if any((self.nameEdit.isUndoAvailable(), self.nameEdit.isRedoAvailable())):
            return
        self.nameEdit.setText('Copy of {}'.format(self.cloneCombo.currentText()))

    def checkNames(self, name):
        if not name:
            self.buttonBox.button(self.buttonBox.Ok).setEnabled(False)
        else:
            current = [c.lower() for c in self.current.keys() + self.current.values() + factoryPresets] + \
                ['main library', 'uid', 'tags']
            if name.lower() in current:
                self.okBtn.setEnabled(False)
                self.nameEdit.setStyleSheet('color: red')
            else:
                self.okBtn.setEnabled(True)
                self.nameEdit.setStyleSheet('')

    def exec_(self, clone=''):
        query = QtSql.QSqlQuery()
        query.exec_('pragma table_info(reference)')
        self.current = {}
        self.cloneCombo.blockSignals(True)
        while query.next():
            if query.value(1) in ('uid', 'tags'):
                continue
            name = query.value(1)
            if name in factoryPresets:
                ref = factoryPresetsNamesDict[name]
            else:
                ref = name
            self.current[name] = ref
            self.cloneCombo.addItem(ref, name)
        self.cloneCombo.blockSignals(False)
        if clone:
            self.cloneChk.toggle(True)
            self.cloneCombo.setCurrentIndex(self.cloneCombo.findData(clone))
        res = QtWidgets.QDialog.exec_(self)
        if not res:
            return res
        return self.nameEdit.text().strip()

