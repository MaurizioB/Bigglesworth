# *-* encoding: utf-8 *-*

from string import uppercase

from Qt import QtCore, QtGui, QtWidgets

from bigglesworth.const import UidColumn, NameColumn, factoryPresets
from bigglesworth.library import BankProxy
from bigglesworth.utils import loadUi, localPath

from bigglesworth.dialogs.utils import NameValidator


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

        settings = QtCore.QSettings()
        settings.beginGroup('collectionIcons')
        for index, collection in enumerate(self.database.referenceModel.collections, 1):
            self.collectionCombo.addItem(collection)
            icon = QtGui.QIcon.fromTheme(settings.value(collection, ''))
            if not icon.isNull():
                self.collectionCombo.setItemIcon(index, icon)
        settings.endGroup()
        self.collectionCombo.setItemIcon(1, QtGui.QIcon.fromTheme('bigglesworth'))
        self.collectionCombo.currentIndexChanged.connect(self.setCollection)

        self.progCombo.currentIndexChanged.connect(self.checkOverwrite)
        self.saveBtn = self.buttonBox.button(self.buttonBox.Save)
        self.saveText = self.saveBtn.text()
        self.overwriteGroup.buttonClicked.connect(self.setOverwrite)
        self.nameEdit.setValidator(NameValidator(self))
        self.alertPixmap = QtGui.QIcon.fromTheme('emblem-warning').pixmap(self.fontMetrics().height())

    def setOverwrite(self, btn):
        if btn == self.newRadio:
            self.saveBtn.setText(self.saveText)
            self.overwriteLbl.setText('')
            self.overwriteIcon.setVisible(False)
        else:
            self.checkOverwrite(self.progCombo.currentIndex())
#            self.saveBtn.setText('Overwrite')
#            self.overwriteLbl.setText('The selected sound will be overwritten!')
#            self.overwriteIcon.setPixmap(self.alertPixmap)
#            self.overwriteIcon.setVisible(True)

    def checkOverwrite(self, row):
        model = self.progCombo.model().sourceModel()
        row += self.bankCombo.currentIndex() << 7
        showAlertIcon = False
        if model.flags(model.index(row, NameColumn)) & QtCore.Qt.ItemIsEnabled:
            self.newRadio.setEnabled(True)
            self.overwriteRadio.setEnabled(True)
            if self.newRadio.isChecked():
                saveText = self.saveText
                overwrite = ''
            else:
                saveText = 'Overwrite'
                overwrite = 'The selected sound will be overwritten!'
                showAlertIcon = True
                try:
                    currentCollectionId = self.collectionCombo.currentIndex() - 1
                    uid = self.database.getUidFromCollection(
                        self.bankCombo.currentIndex(), 
                        self.progCombo.currentIndex(), 
                        self.database.referenceModel.collections[currentCollectionId])
                    collections = self.database.getCollectionsFromUid(uid)
                    if len(collections) > 1:
                        collList = []
                        for collectionId in collections:
                            if collectionId != currentCollectionId:
                                collList.append('"{}"'.format(self.database.referenceModel.collections[collectionId]))
                        overwrite += '<br/><br/>The same sound is also used in the following collections:<br/>{}'.format(
                            ', '.join(collList))
                except Exception as e:
                    print(e)
        else:
            self.newRadio.setEnabled(False)
            self.overwriteRadio.setEnabled(False)
            saveText = self.saveText
            overwrite = ''
        self.saveBtn.setText(saveText)
        self.overwriteLbl.setText(overwrite)
        if showAlertIcon:
            self.overwriteIcon.setVisible(True)
            self.overwriteIcon.setPixmap(self.alertPixmap)
        else:
            self.overwriteIcon.setVisible(False)

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
            self.overwriteIcon.setVisible(False)
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
        self.progCombo.setCurrentIndex(progIndex if progIndex >= 0 else 0)
        self.progCombo.blockSignals(False)
        self.checkOverwrite(self.progCombo.currentIndex())

    def exec_(self, name='', collection=None, readOnly=False, bank=None, prog=None):
        self.readOnlyLbl.setVisible(readOnly)
        if collection is None or collection in factoryPresets:
            self.locationWidget.setEnabled(False)
        else:
            self.collectionCombo.setCurrentIndex(self.database.referenceModel.collections.index(collection) + 1)
        self.nameEdit.setText(name)
        if bank is not None:
            self.bankCombo.setCurrentIndex(bank)
            if prog is not None:
                self.progCombo.setCurrentIndex(prog)

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
