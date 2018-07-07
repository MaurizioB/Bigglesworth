from string import uppercase
import json
from collections import OrderedDict

from Qt import QtCore, QtGui, QtWidgets

from bigglesworth.utils import loadUi, localPath, Enum
from bigglesworth.const import (factoryPresetsNamesDict, INIT, IDW, IDE, CHK, END, SNDD, 
    NameColumn, UidColumn, LocationColumn, CatColumn, TagsColumn, FactoryColumn)
from bigglesworth.widgets import CategoryDelegate, TagsDelegate, CheckBoxDelegate
from bigglesworth.dialogs import SoundFileExport
from bigglesworth.parameters import categories
from bigglesworth.libs import midifile

DestColumn = FactoryColumn + 1

class AltCategoryDelegate(CategoryDelegate):
    def setModelData(self, widget, model, index):
        model.setData(index, widget.currentIndex(), QtCore.Qt.DisplayRole)


class CollectionFilter(QtCore.QSortFilterProxyModel):
    def filterAcceptsRow(self, row, parent):
        return self.sourceModel().index(row, NameColumn).flags() & QtCore.Qt.ItemIsEnabled


class ExportModel(QtGui.QStandardItemModel):
    def __init__(self):
        QtGui.QStandardItemModel.__init__(self, 0, 7)

    def headerData(self, section, orientation, role):
        if orientation == QtCore.Qt.Vertical and role == QtCore.Qt.DisplayRole:
            if self.index(section, UidColumn).data(QtCore.Qt.CheckStateRole):
                location = self.index(section, DestColumn).data()
                if location is None:
                    location = self.index(section, LocationColumn).data()
                if location >= 0:
                    return '{}{:03}'.format(uppercase[location >> 7], (location & 127) + 1)
                return '?'
            else:
                return ''
        return QtGui.QStandardItemModel.headerData(self, section, orientation, role)

class SoundExport(QtWidgets.QDialog):
    readOnlyFlags = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsDropEnabled
    SortSourceIndex, SortInserted, SortAlpha, SortCategory, SortTags = Enum(5)
    DuplicatesMaximum, UnknownMaximum = Enum(1, 2)

    alertDict = {
        1: ('emblem-warning', 'Maximum number of sounds reached, unable to reindex duplicates.'), 
        2: ('emblem-warning', 'Maximum number of sounds reached, unable to reindex unknown indexes.'), 
        }

    def __init__(self, parent, uidList, collection=None):
        QtWidgets.QDialog.__init__(self, parent)
        loadUi(localPath('ui/soundexport.ui'), self)
        self.main = QtWidgets.QApplication.instance()
        self.database = self.main.database
        self.allCollections = self.database.referenceModel.allCollections

        self.toolBtnIcons = QtGui.QIcon.fromTheme('arrow-down'), QtGui.QIcon.fromTheme('arrow-up')
        self.exportBtn = self.buttonBox.button(self.buttonBox.Save)
        self.exportBtn.setText('Export')
        self.exportBtn.setEnabled(False)
        self.exportBtn.clicked.connect(self.export)
        self.exportCloseBtn = self.buttonBox.button(self.buttonBox.Apply)
        self.exportCloseBtn.setText('Export and close')
        self.exportCloseBtn.setIcon(self.exportBtn.icon())
        self.exportCloseBtn.setEnabled(False)
        self.exportCloseBtn.clicked.connect(self.export)
        self.manualTools.setVisible(False)
        self.manualToolsBtn.toggled.connect(lambda state: self.manualToolsBtn.setIcon(self.toolBtnIcons[state]))
        self.indexModeGroup.buttonClicked.connect(lambda btn: self.manualTools.setVisible(btn == self.manualIndexRadio and self.manualToolsBtn.isChecked()))
        self.indexModeGroup.buttonClicked.connect(self.checkExport)

        currentIndex = 0
        for i, c in enumerate(self.allCollections, 1):
            collName = factoryPresetsNamesDict.get(c, c)
            self.collectionCombo.addItem(collName)
            self.collectionCombo.setItemData(i, c)
            if c in factoryPresetsNamesDict:
                self.collectionCombo.setItemIcon(i, QtGui.QIcon(':/images/factory.svg'))
            elif c == 'Blofeld':
                self.collectionCombo.setItemIcon(i, QtGui.QIcon(':/images/bigglesworth_logo.svg'))
            if c == collection:
                currentIndex = i

        self.tempName = collection if collection else 'BlofeldDump'

        self.proxyModel = CollectionFilter()
        self.sourceView.setModel(self.proxyModel)

        self.collectionCombo.setCurrentIndex(currentIndex)
        self.setCollection(currentIndex)
        self.collectionCombo.currentIndexChanged.connect(self.setCollection)

        catDelegate = CategoryDelegate(self.sourceView)
        self.sourceView.setItemDelegateForColumn(CatColumn, catDelegate)
        tagsDelegate = TagsDelegate(self)
        tagsDelegate.setTagsModel(self.database.tagsModel)
        self.sourceView.setItemDelegateForColumn(TagsColumn, tagsDelegate)

        self.sourceView.verticalHeader().setResizeMode(CatColumn, QtWidgets.QHeaderView.Fixed)
        self.sourceView.setColumnHidden(UidColumn, True)
        self.sourceView.setColumnHidden(LocationColumn, True)
        self.sourceView.horizontalHeader().setResizeMode(NameColumn, QtWidgets.QHeaderView.Stretch)
        self.sourceView.horizontalHeader().setResizeMode(CatColumn, QtWidgets.QHeaderView.Fixed)
        self.sourceView.horizontalHeader().setResizeMode(TagsColumn, QtWidgets.QHeaderView.Fixed)

        self.sourceView.selectionModel().selectionChanged.connect(self.checkAddItems)
        self.selectAllBtn.clicked.connect(self.sourceView.selectAll)
        self.selectNoneBtn.clicked.connect(self.sourceView.clearSelection)
        self.addBtn.clicked.connect(self.addItems)

        self.exportModel = ExportModel()
        self.exportView.setModel(self.exportModel)
        self.clearExportModel()
        self.exportView.setColumnHidden(LocationColumn, True)
        self.exportView.setColumnHidden(DestColumn, True)
        checkboxDelegate = CheckBoxDelegate(self.exportView)
        self.exportView.setItemDelegateForColumn(UidColumn, checkboxDelegate)
        catDelegate2 = AltCategoryDelegate(self.exportView)
        self.exportView.setItemDelegateForColumn(CatColumn, catDelegate2)
        tagsDelegate2 = TagsDelegate(self)
        tagsDelegate2.setTagsModel(self.database.tagsModel)
        self.exportView.setItemDelegateForColumn(TagsColumn, tagsDelegate2)
        self.exportView.resizeColumnToContents(UidColumn)
        self.exportView.horizontalHeader().setResizeMode(QtWidgets.QHeaderView.Fixed)
        self.exportView.horizontalHeader().setResizeMode(NameColumn, QtWidgets.QHeaderView.Stretch)
        self.exportView.horizontalHeader().setResizeMode(CatColumn, QtWidgets.QHeaderView.Fixed)
        self.exportView.horizontalHeader().setResizeMode(TagsColumn, QtWidgets.QHeaderView.Fixed)
        self.exportView.verticalHeader().setResizeMode(QtWidgets.QHeaderView.Fixed)
        self.exportModel.dataChanged.connect(self.checkExport)

        self.sortBtn.clicked.connect(self.sort)
        self.sortCombo.currentIndexChanged.connect(self.checkSorting)
        self.fixIndexBtn.clicked.connect(self.fixIndexes)
        self.sortMode = 0
        self.dataBuffer = {}

        if uidList:
            selection = QtCore.QItemSelection()
            if uidList == -1:
                self.sourceView.selectAll()
            else:
                start = self.proxyModel.index(0, UidColumn)
                for uid in uidList:
                    found = self.proxyModel.match(start, QtCore.Qt.DisplayRole, uid, flags=QtCore.Qt.MatchExactly)
                    if found:
                        index = found[0]
                        selection.select(index, index.sibling(index.row(), TagsColumn))
            self.sourceView.selectionModel().select(selection, QtCore.QItemSelectionModel.Select)
            self.addItems()
        self.shown = False

    def showEvent(self, event):
        if not self.shown:
            self.shown = True
            if self.sourceView.selectionModel().selectedRows(NameColumn):
                self.sourceView.scrollTo(
                    self.sourceView.selectionModel().selectedRows(NameColumn)[0], 
                    self.sourceView.PositionAtTop)

    def setCollection(self, index):
        self.sourceView.verticalHeader().setVisible(index)
        if not index:
            self.proxyModel.setSourceModel(self.database.openCollection())
        else:
            collection = self.collectionCombo.itemData(index)
            self.proxyModel.setSourceModel(self.database.openCollection(collection))
        self.sourceView.resizeRowsToContents()
        self.sourceView.resizeColumnToContents(CatColumn)
        self.sourceView.resizeColumnToContents(TagsColumn)

    def checkAddItems(self):
        selection = self.sourceView.selectionModel().selectedRows(NameColumn)
        self.addBtn.setEnabled(1 <= len(selection) <= 1024)

    def addItems(self):
        self.exportModel.dataChanged.disconnect(self.checkExport)
        indexDict = {}
        collection = self.collectionCombo.currentText() if self.collectionCombo.currentIndex() else ''
        for index in self.sourceView.selectionModel().selectedRows(UidColumn):
            row = index.row()
            uid = index.data()
            name = index.sibling(row, NameColumn).data()
            cat = index.sibling(row, CatColumn).data()
            tags = index.sibling(row, TagsColumn).data()
            if collection:
                location = index.sibling(row, LocationColumn).data()
            else:
                collections = self.database.getCollectionsFromUid(uid, ignorePresets=False)
                if collections:
                    collection = self.allCollections[collections[-1]]
                    location = self.database.getIndexForUid(uid, collection)
                    collection = factoryPresetsNamesDict.get(collection, collection)
                else:
                    location = -1
            uidItem = QtGui.QStandardItem(uid)
            uidItem.setCheckState(QtCore.Qt.Checked)
            locItem = QtGui.QStandardItem()
            locItem.setData(location, QtCore.Qt.DisplayRole)
            nameItem = QtGui.QStandardItem(name)
            catItem = QtGui.QStandardItem()
            catItem.setData(cat, QtCore.Qt.DisplayRole)
            tagItem = QtGui.QStandardItem()
            tagItem.setData(tags, QtCore.Qt.DisplayRole)
            tagItem.setFlags(self.readOnlyFlags)
            collItem = QtGui.QStandardItem(collection)
            collItem.setToolTip(collection)
            collItem.setFlags(self.readOnlyFlags)
            destItem = QtGui.QStandardItem()
#            destItem.setData(location, QtCore.Qt.DisplayRole)
            indexDict[row] = uidItem, locItem, nameItem, catItem, tagItem, collItem, destItem

        [self.exportModel.appendRow(indexDict[index]) for index in sorted(indexDict.keys())]
        self.exportView.resizeRowsToContents()
        self.exportView.resizeColumnToContents(CatColumn)
        self.exportView.resizeColumnToContents(TagsColumn)

#        self.exportModel.dataChanged.connect(self.checkExport)
        self.checkExport()

    def getSelected(self):
        selected = []
        for row in range(self.exportModel.rowCount()):
            if self.exportModel.item(row, UidColumn).data(QtCore.Qt.CheckStateRole):
                selected.append((row, 
                    self.exportModel.item(row, LocationColumn).data(QtCore.Qt.DisplayRole), 
                    self.exportModel.item(row, DestColumn)))
            else:
                self.exportModel.item(row, DestColumn).setData(None, QtCore.Qt.DisplayRole)
        return selected
#        return [
#            (r, self.exportModel.item(r, LocationColumn).data(QtCore.Qt.DisplayRole), self.exportModel.item(r, DestColumn))
#                for r in range(self.exportModel.rowCount()) 
#                    if self.exportModel.item(r, UidColumn).data(QtCore.Qt.CheckStateRole)]

    def checkExport(self):
        selected = self.getSelected()
        count = len(selected)
        self.exportBtn.setEnabled(count)
        self.exportCloseBtn.setEnabled(count)

        srcIndexList = []
        unknownIndexes = 0
        for row, srcIndex, destItem in selected:
            if srcIndex < 0:
                unknownIndexes += 1
            else:
                srcIndexList.append(srcIndex)
        hasDuplicates = len(srcIndexList) and len(srcIndexList) != len(set(srcIndexList))
        hasValidIndexes = not hasDuplicates and not unknownIndexes

        try:
            self.exportModel.dataChanged.disconnect(self.checkExport)
        except:
            pass

        self.setAlert()
        if self.autoIndexRadio.isChecked():
            if hasValidIndexes:
                for row, srcIndex, destItem in selected:
                    destItem.setData(srcIndex, QtCore.Qt.DisplayRole)
            elif hasDuplicates:
                if count > 1024:
                    for row, srcIndex, destItem in selected:
                        destItem.setData(srcIndex, QtCore.Qt.DisplayRole)
                    self.setAlert(self.DuplicatesMaximum)
                else:
                    done = []
                    for row, srcIndex, destItem in selected:
                        if srcIndex < 0:
                            srcIndex = 0
                        while srcIndex in done:
                            srcIndex += 1
                            if srcIndex >= 1024:
                                srcIndex = 0
                        done.append(srcIndex)
                        destItem.setData(srcIndex, QtCore.Qt.DisplayRole)
            elif unknownIndexes:
                if count > 1024:
                    for row, srcIndex, destItem in selected:
                        destItem.setData(srcIndex, QtCore.Qt.DisplayRole)
                    self.setAlert(self.UnknownMaximum)
                else:
                    for row, srcIndex, destItem in selected:
                        if srcIndex < 0:
                            srcIndex = 0
                            while srcIndex in srcIndexList:
                                srcIndex += 1
                            srcIndexList.append(srcIndex)
                        destItem.setData(srcIndex, QtCore.Qt.DisplayRole)
            self.exportView.sortByColumn(DestColumn, QtCore.Qt.AscendingOrder)
        self.exportModel.dataChanged.connect(self.checkExport)
        self.exportModel.layoutChanged.emit()

    def sort(self):
        try:
            self.exportModel.dataChanged.disconnect(self.checkExport)
        except:
            pass
        selected = self.getSelected()
        if not selected:
            self.exportModel.dataChanged.connect(self.checkExport)
            return
        if self.sortMode == self.SortSourceIndex:
            indexes = {}
            for row, srcIndex, destItem in selected:
                if srcIndex < 0:
                    srcIndex = 1024
                if srcIndex in indexes:
                    indexes[srcIndex].append(destItem)
                else:
                    indexes[srcIndex] = [destItem]
            current = 0
            for srcIndex in sorted(indexes):
                for destItem in indexes[srcIndex]:
                    destItem.setData(current, QtCore.Qt.DisplayRole)
                    current += 1
        elif self.sortMode == self.SortInserted:
            for current, (row, srcIndex, destItem) in enumerate(selected):
                destItem.setData(current, QtCore.Qt.DisplayRole)
        elif self.sortMode == self.SortAlpha:
            alpha = {}
            for row, srcIndex, destItem in selected:
                name = self.exportModel.index(row, NameColumn).data()
                if name in alpha:
                    alpha[name].append(destItem)
                else:
                    alpha[name] = [destItem]
            current = 0
            for name in sorted(alpha):
                for destItem in alpha[name]:
                    destItem.setData(current, QtCore.Qt.DisplayRole)
                    current += 1
        elif self.sortMode == self.SortCategory:
            catLen = len(categories)
            cats = OrderedDict([(c, []) for c in range(catLen)])
#            baseCats = {c:[] for c in categories}
            for row, srcIndex, destItem in selected:
                cat = self.exportModel.index(row, CatColumn).data()
                cats[cat].append(destItem)
            if self.distributeChk.isEnabled() and self.distributeChk.isChecked():
                cats = OrderedDict((k, v) for k, v in cats.items() if v)
                done = False
                if len(cats) <= 8:
                    for cat, items in cats.items():
                        if len(items) > 128:
                            break
                    else:
                        for bank, items in enumerate(cats.values()):
                            for index, destItem in enumerate(items):
                                destItem.setData((bank << 7) + index, QtCore.Qt.DisplayRole)
                        done = True
                if not done:
                    bankDict = OrderedDict((b, []) for b in range(8))
                    undone = []
                    for destItems in cats.values():
                        if len(destItems) < 128:
                            for bank, contents in bankDict.items():
                                if len(contents) + len(destItems) < 128:
                                    contents.extend(destItems)
                                else:
                                    undone.extend(destItems)
                        else:
                            undone.extend(destItems)
                    for bank, contents in bankDict.items():
                        current = 0
                        for destItem in contents:
                            destItem.setData((bank << 7) + current, QtCore.Qt.DisplayRole)
                            current += 1
                        while undone and current < 128:
                            undone.pop(0).setData(current, QtCore.Qt.DisplayRole)
                            current += 1
            else:
                current = 0
                for c in range(catLen):
                    for destItem in cats[c]:
                        destItem.setData(current, QtCore.Qt.DisplayRole)
                        current += 1

        elif self.sortMode == self.SortTags:
            tags = OrderedDict()
            orphans = []
            for row, srcIndex, destItem in selected:
                try:
                    itemTags = json.loads(self.exportModel.index(row, TagsColumn).data())
                    assert len(itemTags)
                    foundTags = set(tags) & set(itemTags)
                    if foundTags:
                        for tag in foundTags:
                            tags[tag].append(destItem)
                            break
                    else:
                        for tag in sorted(itemTags):
                            tags[tag] = [destItem]
                            break
                except:
                    orphans.append(destItem)
            done = False
            if len(tags) + (1 if orphans else 0) <= 8:
                if self.distributeChk.isEnabled() and self.distributeChk.isChecked():
                    for tag, contents in tags.items():
                        if len(contents) > 128:
                            break
                    else:
                        for bank, destItems in enumerate(tags.values()):
                            for index, destItem in enumerate(destItems):
                                destItem.setData((bank << 7) + index, QtCore.Qt.DisplayRole)
                        bank = (bank + 1) << 7
                        for index, destItem in enumerate(orphans):
                            destItem.setData(bank + index, QtCore.Qt.DisplayRole)
                        done = True
            if not done:
                current = 0
                for destItems in tags.values():
                    for destItem in destItems:
                        destItem.setData(current, QtCore.Qt.DisplayRole)
                        current += 1
                for current, destItem in enumerate(orphans, current):
                    destItem.setData(current, QtCore.Qt.DisplayRole)
        self.exportModel.dataChanged.connect(self.checkExport)
        self.exportView.sortByColumn(DestColumn, QtCore.Qt.AscendingOrder)

    def checkSorting(self, sortMode):
        self.sortMode = sortMode
        count = len(self.getSelected())
        if sortMode in (self.SortCategory, self.SortTags):
            self.distributeChk.setEnabled(count <= 888)
        else:
            self.distributeChk.setEnabled(False)

    def fixIndexes(self):
        try:
            self.exportModel.dataChanged.disconnect(self.checkExport)
        except:
            pass
        selected = self.getSelected()
        if len(selected) > 1024:
            self.exportModel.dataChanged.connect(self.checkExport)
            return
        indexes = OrderedDict((i, []) for i in range(1024))
        done = []
        for row, srcIndex, destItem in selected:
            destIndex = destItem.data(QtCore.Qt.DisplayRole)
            if destIndex < 0:
                if srcIndex < 0:
                    if not done:
                        indexes[0].append(destItem)
                    else:
                        indexes[done[-1]].append(destItem)
                else:
                    indexes[srcIndex].append(destItem)
            else:
                indexes[destIndex].append(destItem)
        if not any(len(i) > 1 for i in indexes.values()):
            self.exportModel.dataChanged.connect(self.checkExport)
            return
        new = OrderedDict()
        for index, items in indexes.items():
            current = index
            while current in new:
                current += 1
            if len(items) <= 1:
                if items:
                    new[current] = items[0]
                continue
            for item in items:
                new[current] = item
                while current in new:
                    current += 1
        maxIndex = max(new)
        if maxIndex <= 1023:
            for index, destItem in new.items():
                destItem.setData(index, QtCore.Qt.DisplayRole)
        else:
            while maxIndex in new:
                maxIndex -= 1
            maxIndex -= len([index for index in new if index > 1023])
            while maxIndex in new:
                maxIndex -= 1
            for index, destItem in new.items():
                if index < maxIndex:
                    destItem.setData(index, QtCore.Qt.DisplayRole)
                else:
                    destItem.setData(maxIndex, QtCore.Qt.DisplayRole)
                    maxIndex += 1
#        print('\n'.join(map(str, [(k, v.data(QtCore.Qt.DisplayRole)) for k, v in new.items() if v])))
        self.exportModel.dataChanged.connect(self.checkExport)
        self.exportView.sortByColumn(DestColumn, QtCore.Qt.AscendingOrder)

    def export(self):
        selected = []
        for row in range(self.exportModel.rowCount()):
            item = self.exportModel.item(row, UidColumn)
            if item.data(QtCore.Qt.CheckStateRole):
                uid = item.data(QtCore.Qt.DisplayRole)
                if uid in selected:
                    if QtWidgets.QMessageBox.question(self, 'Duplicates found', 
                        'Duplicate indexes has been found in the selected items.\nDo you want to proceed anyway?', 
                        QtWidgets.QMessageBox.Ok|QtWidgets.QMessageBox.Cancel) == QtWidgets.QMessageBox.Ok:
                            break
                    else:
                        return
                else:
                    selected.append(uid)
        close = self.sender() == self.exportCloseBtn
        res = SoundFileExport(self, self.tempName.rstrip('.syx').rstrip('.mid')).exec_()
        if res:
            self.tempName = res
            if res.endswith('syx'):
                exportFunc = self.exportSysEx
            else:
                exportFunc = self.exportMid
            export = exportFunc(res)
            if export == True:
                if close:
                    self.accept()
            else:
                QtWidgets.QMessageBox.critical(self, 
                    'Export error', 
                    'An error occurred while exporting.\n{}'.format(export)
                    )

    def setAlert(self, alert=None):
        if not alert:
            self.alertIcon.setVisible(False)
            self.alertLbl.setVisible(False)
            self.exportBtn.setEnabled(True)
            self.exportCloseBtn.setEnabled(True)
        else:
            self.exportBtn.setEnabled(False)
            self.exportCloseBtn.setEnabled(False)
            self.alertIcon.setVisible(True)
            self.alertLbl.setVisible(True)
            iconName, message = self.alertDict[alert]
            icon = QtGui.QIcon.fromTheme(iconName)
            self.alertIcon.setPixmap(icon.pixmap(self.exportBtn.iconSize()))
            self.alertLbl.setText(message)

    def clearExportModel(self):
        self.exportModel.clear()
        self.exportModel.setHorizontalHeaderLabels(['', '', 'Name', 'Category', 'Tags', 'Source coll.', ''])

    def getSelectedDataDict(self):
        dataDict = OrderedDict()
        for row, srcIndex, destItem in self.getSelected():
            uid = self.exportModel.item(row, UidColumn).data(QtCore.Qt.DisplayRole)
            data = self.dataBuffer.get(uid)
            if not data:
                data = self.dataBuffer.setdefault(uid, self.database.getSoundDataFromUid(uid))
            dataDict[destItem.data(QtCore.Qt.DisplayRole)] = data
        return dataDict

    def exportMid(self, path):
        try:
            pattern = midifile.Pattern()
            track = midifile.Track()
            pattern.append(track)
            for index, data in self.getSelectedDataDict().items():
                sysex = [131, 7, IDW, IDE, 0, SNDD, (index >> 7), index & 127] + data + [CHK]
                event = midifile.SysexEvent(tick=100, data=sysex)
                track.append(event)
            track.append(midifile.EndOfTrackEvent(tick=1))
            midifile.write_midifile(path, pattern)
            return True
        except Exception as e:
            print(type(e), e)
            return e

    def exportSysEx(self, path):
        try:
            content = []
            for index, data in self.getSelectedDataDict().items():
                sysex = [INIT, IDW, IDE, 0, SNDD, (index >> 7), index & 127] + data + [CHK, END]
                content.extend(sysex)
            with open(path, 'wb') as outFile:
                outFile.write(''.join(map(chr, content)))
            return True
        except Exception as e:
            print(e)
            return e


