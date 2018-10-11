from Qt import QtCore, QtGui, QtWidgets, QtSql

from bigglesworth.utils import loadUi
from bigglesworth.const import factoryPresets, factoryPresetsNamesDict


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

