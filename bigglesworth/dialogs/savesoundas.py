# *-* encoding: utf-8 *-*

from string import uppercase
from unidecode import unidecode

from Qt import QtCore, QtGui, QtWidgets

from bigglesworth.const import UidColumn, NameColumn, factoryPresets
from bigglesworth.library import BankProxy
from bigglesworth.utils import loadUi, localPath


def getASCII(char):
    if 32 <= ord(char) <= 126 or char == u'°':
        return char
#    print('wtf? "{}"'.format(unidecode(char)))
    return unidecode(char)

class NameValidator(QtGui.QValidator):
    def validate(self, input, pos):
        output = ''
        for l in input:
            output += getASCII(l)
        return self.Acceptable, output, pos


class CollectionProxy(BankProxy):
    def data(self, index, role=QtCore.Qt.DisplayRole):
        data = QtCore.QSortFilterProxyModel.data(self, index, role)
        if role == QtCore.Qt.DisplayRole:
            data = '{} - {}'.format(index.row() + 1, data)
        if role == QtCore.Qt.FontRole:
            index = self.mapToSource(index)
            if self.sourceModel().flags(index) & QtCore.Qt.ItemIsEnabled:
                index = self.sourceModel().data(index, role)
                if not data:
                    data = QtWidgets.QApplication.font()
                data.setBold(True)
        return data

    def flags(self, *args):
        return QtCore.Qt.ItemIsEnabled|QtCore.Qt.ItemIsSelectable

    def customFilter(self, row, parent):
        return True if row >> 7 == self.filter else False


class SaveSoundAs(QtWidgets.QDialog):
    def __init__(self, parent):
        QtWidgets.QDialog.__init__(self, parent)
        loadUi(localPath('ui/savesoundas.ui'), self)
        self.main = parent.main
        self.database = parent.database
        self.collectionCombo.addItems(self.database.referenceModel.collections)
        self.collectionCombo.setItemData(1, QtGui.QIcon.fromTheme('go-home'), QtCore.Qt.DecorationRole)
        self.collectionCombo.currentIndexChanged.connect(self.setCollection)
        self.progCombo.currentIndexChanged.connect(self.checkOverwrite)
        self.saveBtn = self.buttonBox.button(self.buttonBox.Save)
        self.saveText = self.saveBtn.text()
        self.overwriteGroup.buttonClicked.connect(self.setOverwrite)
        self.nameEdit.setValidator(NameValidator(self))

    def setOverwrite(self, btn):
        if btn == self.newRadio:
            saveText = self.saveText
            overwrite = ''
        else:
            saveText = 'Overwrite'
            overwrite = 'The selected sound will be overwritten!'
        self.saveBtn.setText(saveText)
        self.overwriteLbl.setText(overwrite)

    def checkOverwrite(self, row):
        model = self.progCombo.model().sourceModel()
        row += self.bankCombo.currentIndex() << 7
        if model.flags(model.index(row, NameColumn)) & QtCore.Qt.ItemIsEnabled:
            self.newRadio.setEnabled(True)
            self.overwriteRadio.setEnabled(True)
            if self.newRadio.isChecked():
                saveText = self.saveText
                overwrite = ''
            else:
                saveText = 'Overwrite'
                overwrite = 'The selected sound will be overwritten!'
        else:
            self.newRadio.setEnabled(False)
            self.overwriteRadio.setEnabled(False)
            saveText = self.saveText
            overwrite = ''
        self.saveBtn.setText(saveText)
        self.overwriteLbl.setText(overwrite)

    def setCollection(self, index):
        bankIndex = self.bankCombo.currentIndex()
        progIndex = self.progCombo.currentIndex()
        self.locationWidget.setEnabled(index)
        try:
            self.bankCombo.currentIndexChanged.disconnect()
        except:
            pass
        if not index:
            self.saveBtn.setText(self.saveText)
            self.overwriteLbl.setText('')
            self.collectionCombo.setModel(None)
            return
        data = self.collectionCombo.itemData(index)
        self.bankCombo.clear()
        if data:
            bankItems, bankProxy = data
        else:
            collection = self.collectionCombo.itemText(index)
            bankProxy = CollectionProxy()
            bankProxy.setSourceModel(self.database.openCollection(collection))
            bankCount = [128, 128, 128, 128, 128, 128, 128, 128]
            for index in self.database.getIndexesForCollection(collection):
                bankCount[index >> 7] -= 1
            bankItems = []
            for b, count in enumerate(bankCount):
                bankItems.append('{} ({} free slot{})'.format(
                    uppercase[b], 
                    count, 
                    '' if count == 1 else 's'
                    ))
            self.collectionCombo.setItemData(index, (bankItems, bankProxy))
        self.bankCombo.addItems(bankItems)
        self.bankCombo.setCurrentIndex(bankIndex if bankIndex >= 0 else 0)
        bankProxy.setFilter(bankIndex if bankIndex >= 0 else 0)
        self.bankCombo.currentIndexChanged.connect(lambda idx, proxy=bankProxy: proxy.setFilter(idx))
        self.progCombo.blockSignals(True)
        self.progCombo.setModel(bankProxy)
        self.progCombo.setModelColumn(NameColumn)
        self.progCombo.blockSignals(False)
        self.progCombo.setCurrentIndex(progIndex if progIndex >= 0 else 0)

    def exec_(self, name='', collection=None, readOnly=False):
        self.readOnlyLbl.setVisible(readOnly)
        if collection is None or collection in factoryPresets:
            self.locationWidget.setEnabled(False)
        else:
            self.collectionCombo.setCurrentIndex(self.database.referenceModel.collections.index(collection) + 1)
        self.nameEdit.setText(name)
        res = QtWidgets.QDialog.exec_(self)
        if not res:
            return res
        if not self.collectionCombo.currentIndex():
            collection = None
            index = None
        else:
            collection = self.collectionCombo.currentText()
            index = (self.bankCombo.currentIndex() << 7) + self.progCombo.currentIndex()
        if index is not None and self.overwriteRadio.isEnabled() and self.overwriteRadio.isChecked():
            model = self.progCombo.model().sourceModel()
            uid = model.data(model.index(index, UidColumn), QtCore.Qt.DisplayRole)
        else:
            uid = None
        return self.nameEdit.text(), collection, index, uid
