import sys
from unidecode import unidecode
from Qt import QtCore, QtGui, QtWidgets, QtSql

from bigglesworth.utils import loadUi
from bigglesworth.const import factoryPresets

EditRole = QtCore.Qt.UserRole + 1
IconRole = EditRole + 1
Delete, Keep, Rename, Copy, New = -1, 0, 1, 2, 4


class NameValidator(QtGui.QValidator):
    def validate(self, text, pos):
        text = unidecode(text)
        if not text or len(text) > 32 or text in ['uid', 'tags'] + factoryPresets:
            return self.Intermediate, text, pos
        return self.Acceptable, text, pos


class NameDelegate(QtWidgets.QStyledItemDelegate):
    nameValidator = NameValidator()

    def paint(self, qp, option, index):
        self.initStyleOption(option, index)
        font = option.font
        extraIcon = None
        if index.data(EditRole) & Rename:
            font.setItalic(True)
            extraIcon = QtGui.QIcon.fromTheme('edit-rename')
        elif index.data(EditRole) & Copy:
            font.setUnderline(True)
            extraIcon = QtGui.QIcon.fromTheme('edit-copy')
        elif index.data(EditRole) & New:
            font.setBold(True)
            extraIcon = QtGui.QIcon.fromTheme('document-new')
        if extraIcon:
            left = option.decorationSize.width()
            height = option.decorationSize.height()
            iconSize = option.fontMetrics.height()
            currentIcon = QtGui.QIcon(option.icon)
            option.icon = QtGui.QIcon()
            option.decorationSize.setWidth(left + iconSize + 2)
            option.features |= option.HasDecoration
#        if index.data(EditRole) & Rename:
#            font = option.font
#            font.setBold(True)
#            option.font = font
#        if index.data(EditRole) & Rename:
#            icon = QtGui.QIcon.fromTheme('edit-rename')
#            if not icon.isNull():
#                option.features |= option.HasDecoration
#                option.icon = icon
#        elif index.data(EditRole) & Copy:
#            option.features |= option.HasDecoration
#            option.icon = QtGui.QIcon.fromTheme('edit-copy')
#        elif index.data(EditRole) & New:
#            option.features |= option.HasDecoration
#            option.icon = QtGui.QIcon.fromTheme('document-new')
        QtWidgets.QStyledItemDelegate.paint(self, qp, option, QtCore.QModelIndex())
        if extraIcon:
            decoRect = QtWidgets.QApplication.style().subElementRect(QtWidgets.QStyle.SE_ItemViewItemDecoration, option)
            vCenter = decoRect.center().y()
            if not currentIcon.isNull():
                pixmap = currentIcon.pixmap(left, height)
                qp.drawPixmap(QtCore.QRect(decoRect.left(), vCenter - height / 2, left, height), pixmap, pixmap.rect())
            iconRect = QtCore.QRect(decoRect.left() + left + 2, option.rect.center().y() - iconSize / 2, iconSize, iconSize)
            pixmap = extraIcon.pixmap(iconSize).scaledToWidth(iconSize, QtCore.Qt.SmoothTransformation)
            qp.drawPixmap(iconRect, pixmap, pixmap.rect())

    def createEditor(self, parent, option, index):
        if index.data() != 'Blofeld':
            editor = QtWidgets.QStyledItemDelegate.createEditor(self, parent, option, index)
            editor.setValidator(self.nameValidator)
            editor.textChanged.connect(self.setValid)
            return editor
        return None

    def setValid(self, text):
        valid, _, _ = self.nameValidator.validate(text, 0)
        if valid == QtGui.QValidator.Intermediate:
            self.sender().setStyleSheet('color: red')
        else:
            self.sender().setStyleSheet('')

    def setModelData(self, widget, model, index):
        name = widget.text().strip()
        res = model.match(model.index(0, 1), QtCore.Qt.DisplayRole, name, hits=-1, flags=QtCore.Qt.MatchFixedString)
        res = list(filter(lambda idx: idx.row() != index.row() and idx.flags() & QtCore.Qt.ItemIsEnabled, res))
        if len(res) >= 1:
            name = self.parent().getUnique(name)
        model.setData(index, name)
        if index.data(EditRole) == 0 and index.data().lower() != index.sibling(index.row(), 0).data().lower():
            model.setData(index, Rename, EditRole)


class DeleteDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, *args, **kwargs):
        QtWidgets.QStyledItemDelegate.__init__(self, *args, **kwargs)
        self.delIcon = QtGui.QIcon.fromTheme('edit-delete')

    def displayText(self, *args):
        return ''

    def sizeHint(self, option, index):
        hint = QtWidgets.QStyledItemDelegate.sizeHint(self, option, index)
        hint.setWidth(20)
        return hint

    def paint(self, qp, option, index):
        self.initStyleOption(option, index)
        QtWidgets.QStyledItemDelegate.paint(self, qp, option, QtCore.QModelIndex())
        if not (index.flags() & QtCore.Qt.ItemIsEnabled and index.data(QtCore.Qt.DisplayRole)):
            return
        iconSize = option.decorationSize.width()
        iconRect = QtCore.QRect((option.rect.width() - iconSize) / 2, (option.rect.height() - iconSize) / 2, iconSize, iconSize)
        qp.save()
        qp.translate(option.rect.x(), option.rect.y())
        qp.drawPixmap(iconRect, self.delIcon.pixmap(iconSize, iconSize))
        qp.restore()


class ManageCollectionsDialog(QtWidgets.QDialog):
    def __init__(self, parent, activeCollections):
        QtWidgets.QDialog.__init__(self, parent)
        loadUi('ui/managecollection.ui', self)
        self.database = parent.database
        self.activeCollections = activeCollections
#        self.referenceModel = parent.database.getCollections()
        self.model = QtGui.QStandardItemModel()
        self.pragmaQuery = QtSql.QSqlQuery()
        self.query = QtSql.QSqlQuery()
        self.settings = QtCore.QSettings()

        self.applyBtn = self.buttonBox.button(self.buttonBox.Apply)
        self.applyBtn.setEnabled(False)
        self.applyBtn.clicked.connect(self.apply)

        self.populate()

        self.collectionsView.selectionModel().selectionChanged.connect(self.selectionChanged)
        nameDelegate = NameDelegate(self)
        self.collectionsView.setItemDelegateForColumn(1, nameDelegate)
        deleteDelegate = DeleteDelegate(self)
        self.collectionsView.setItemDelegateForColumn(3, deleteDelegate)
        self.collectionsView.clicked.connect(self.delClickCheck)

        self.addBtn.clicked.connect(self.addCollection)
        self.delBtn.clicked.connect(self.delCollection)
        self.copyBtn.clicked.connect(self.copyCollection)
        if sys.platform == 'darwin':
            self.iconBtn.iconChanged[str].connect(self.iconChanged)
        else:
            self.iconBtn.iconChanged.connect(self.iconChanged)
        self.iconBtn.setIconName()

    def dataChanged(self, *args):
        self.applyBtn.setEnabled(True)

    def delClickCheck(self, index):
        if index.column() == 3 and index.data(QtCore.Qt.DisplayRole) and index.flags() & QtCore.Qt.ItemIsEnabled:
            row = index.row()
            self.collectionsView.selectionModel().selection().select(index.sibling(row, 1), index.sibling(row, 2))
            self.collectionsView.setCurrentIndex(index.sibling(row, 1))
            self.delCollection()

    def selectionChanged(self, *args):
        selection = self.collectionsView.selectionModel()
#        for index in selection.selectedRows():
#            if index.flags() & 
        if len(selection.selectedRows()) >= 1 and \
            all(index.data(QtCore.Qt.DisplayRole) for index in selection.selectedRows(3)) and \
            any((index.flags() & (QtCore.Qt.ItemIsEnabled|QtCore.Qt.ItemIsEditable)) == (QtCore.Qt.ItemIsEnabled|QtCore.Qt.ItemIsEditable) for index in selection.selectedRows(1)):
                self.delBtn.setEnabled(True)
        else:
            self.delBtn.setEnabled(False)
#        self.delBtn.setEnabled(True if selection.selectedRows() else False)
        if len(selection.selectedRows()) == 1 and selection.selectedRows()[0].flags() & (QtCore.Qt.ItemIsEnabled|QtCore.Qt.ItemIsEditable):
            self.copyBtn.setEnabled(True)
        else:
            self.copyBtn.setEnabled(False)
        self.iconBtn.blockSignals(True)
        if len(selection.selectedRows()) == 1 and selection.selectedRows()[0].row() > 0:
            index = selection.selectedRows(1)[0]
            self.iconBtn.setIconName(index.data(IconRole))
            self.iconBtn.setEnabled(True)
        else:
            self.iconBtn.setIconName()
            self.iconBtn.setEnabled(False)
        self.iconBtn.blockSignals(False)

    def iconChanged(self, icon):
        index = self.collectionsView.currentIndex().sibling(self.collectionsView.currentIndex().row(), 1)
        if sys.platform == 'darwin':
            iconName = icon
            icon = QtGui.QIcon.fromTheme(icon)
        else:
            iconName = icon.name()
        self.model.setData(index, icon, QtCore.Qt.DecorationRole)
        self.model.setData(index, iconName if not icon.isNull() else None, IconRole)

    def getUnique(self, name):
        subStr = ''
        i = 0
        while True:
            res = self.model.match(self.model.index(0, 1), QtCore.Qt.DisplayRole, name + subStr, hits=-1, flags=QtCore.Qt.MatchFixedString)
            if res and any(res[x].flags() & QtCore.Qt.ItemIsEnabled for x in range(len(res))):
                i += 1
                subStr = ' {}'.format(i)
            else:
                break
        return name + subStr

    def addCollection(self):
        self.applyBtn.setEnabled(True)
        name = self.getUnique('New collection')
        referenceItem = QtGui.QStandardItem(name)
        referenceItem.setData(New, EditRole)
        nameItem = referenceItem.clone()
        sumItem = QtGui.QStandardItem('0')
        sumItem.setData(QtCore.Qt.AlignCenter, QtCore.Qt.TextAlignmentRole)
        delItem = QtGui.QStandardItem()
        delItem.setData(True, QtCore.Qt.DisplayRole)
        delItem.setFlags(delItem.flags() ^ (QtCore.Qt.ItemIsEditable|QtCore.Qt.ItemIsSelectable))
        self.model.appendRow([referenceItem, nameItem, sumItem, delItem])
        self.collectionsView.setCurrentIndex(self.model.index(self.model.rowCount() - 1, 1))
        self.collectionsView.edit(self.collectionsView.currentIndex())
        self.collectionsView.scrollToBottom()

    def delCollection(self):
        rows = sorted(index.row() for index in self.collectionsView.selectionModel().selectedRows())
        for row in reversed(rows):
            if row == 0:
                continue
#            self.model.removeRow(row)
            item = self.model.item(row, 1)
            if not self.model.index(row, 0).data(EditRole) & Copy:
                res = self.model.match(self.model.index(row, 0), QtCore.Qt.DisplayRole, self.model.item(row, 0).text(), hits=-1, flags=QtCore.Qt.MatchFixedString|QtCore.Qt.MatchWrap)
                for index in res[1:]:
                    if self.model.itemFromIndex(index).flags() & QtCore.Qt.ItemIsEnabled:
                        continue
            item.setFlags((item.flags() | QtCore.Qt.ItemIsEnabled) ^ QtCore.Qt.ItemIsEnabled)
            item = self.model.item(row, 0)
            item.setFlags(item.flags() ^ QtCore.Qt.ItemIsEnabled)
            item = self.model.item(row, 2)
            item.setFlags(item.flags() ^ QtCore.Qt.ItemIsEnabled)
        rows = sorted(index.row() for index in self.collectionsView.selectionModel().selectedRows())
        for row in reversed(rows):
            if self.model.item(row, 1).data(EditRole) & Copy:
                self.model.removeRow(row)
        self.selectionChanged()
        self.applyBtn.setEnabled(True)

    def copyCollection(self):
        sourceIndex = self.collectionsView.selectionModel().selectedRows()[0]
        oldName = sourceIndex.data()
        if oldName.lower().startswith('copy of '):
            oldName = oldName[8:]
            if oldName.split()[-1].isdigit():
                oldName = ' '.join(oldName.split()[:-1])
        name = self.getUnique('Copy of {}'.format(oldName))
        referenceItem = QtGui.QStandardItem(sourceIndex.sibling(sourceIndex.row(), 0).data())
        referenceItem.setData(Copy, EditRole)
        nameItem = QtGui.QStandardItem(name)
        nameItem.setData(Copy, EditRole)
        sumItem = QtGui.QStandardItem(sourceIndex.sibling(sourceIndex.row(), 2).data())
        sumItem.setData(QtCore.Qt.AlignCenter, QtCore.Qt.TextAlignmentRole)
        self.model.appendRow([referenceItem, nameItem, sumItem])
        self.collectionsView.scrollToBottom()
        self.applyBtn.setEnabled(True)

    def populate(self):
        self.applyBtn.setEnabled(False)
        try:
            self.model.dataChanged.disconnect(self.dataChanged)
        except:
            pass
        self.settings.beginGroup('CollectionIcons')
        self.model.clear()
        self.model.setHorizontalHeaderLabels(['', 'Collection', 'Sounds', ''])
        self.pragmaQuery.exec_('PRAGMA table_info(reference)')
        self.collectionsView.setModel(self.model)
        self.collectionsView.setSelectionBehavior(self.collectionsView.SelectRows)
        self.pragmaQuery.seek(4)

        while self.pragmaQuery.next():
            collection = self.pragmaQuery.value(1)
            referenceItem = QtGui.QStandardItem(collection)
            referenceItem.setData(0, EditRole)
            nameItem = referenceItem.clone()
            res = self.query.exec_('SELECT COUNT("{c}") FROM reference WHERE "{c}" IS NOT NULL'.format(c=collection))
            if not res:
                print(self.query.lastError().databaseText())
            self.query.first()
            sumItem = QtGui.QStandardItem(str(self.query.value(0)))
            sumItem.setData(QtCore.Qt.AlignCenter, QtCore.Qt.TextAlignmentRole)
            sumItem.setFlags(sumItem.flags() ^ QtCore.Qt.ItemIsEditable)
            delItem = QtGui.QStandardItem()
            delItem.setFlags(delItem.flags() ^ (QtCore.Qt.ItemIsEditable|QtCore.Qt.ItemIsSelectable))
            self.model.appendRow([referenceItem, nameItem, sumItem, delItem])
            if collection in self.activeCollections:
                nameItem.setFlags(nameItem.flags() ^ QtCore.Qt.ItemIsEditable)
                delItem.setData(False, QtCore.Qt.DisplayRole)
            else:
                delItem.setData(True, QtCore.Qt.DisplayRole)

            if self.settings.contains(collection):
                iconName = self.settings.value(collection)
                icon = QtGui.QIcon.fromTheme(iconName)
                if not icon.isNull():
                    nameItem.setIcon(icon)
                    nameItem.setData(iconName, IconRole)

        self.pragmaQuery.finish()
        self.settings.endGroup()
        self.query.finish()
        self.model.item(0, 1).setFlags(self.model.item(0, 1).flags() ^ QtCore.Qt.ItemIsEditable)
        self.model.item(0, 1).setIcon(QtGui.QIcon(':/images/bigglesworth_logo.svg'))

        self.collectionsView.resizeColumnToContents(2)
        self.collectionsView.resizeColumnToContents(3)
        self.collectionsView.resizeRowsToContents()
        self.collectionsView.setColumnHidden(0, True)
        self.collectionsView.horizontalHeader().setResizeMode(1, QtWidgets.QHeaderView.Stretch)
        self.collectionsView.verticalHeader().setDefaultSectionSize(self.collectionsView.verticalHeader().sectionSize(0))
        self.model.dataChanged.connect(self.dataChanged)

    def printError(self, query):
        print('Error with this query: {}\n'.format(query.lastQuery()))
        print('Driver message:', query.lastError().driverText())
        print('Database message:', query.lastError().databaseText())

    def accept(self):
        if self.applyBtn.isEnabled():
            if not self.apply():
                return
        QtWidgets.QDialog.accept(self)

    def apply(self):
        currentRow = self.collectionsView.currentIndex().row()

        newSchema = []
        delete = []
        rename = {}
        new = []
        copy = {}

        self.settings.beginGroup('CollectionIcons')
        for row in range(1, self.model.rowCount()):
            referenceItem = self.model.item(row, 0)
            nameItem = self.model.item(row, 1)
            if not nameItem.flags() & QtCore.Qt.ItemIsEnabled:
                delete.append(referenceItem.text())
                self.settings.remove(nameItem.text())
                continue
            status = nameItem.data(EditRole)
            if status & Copy:
                copy[nameItem.text()] = referenceItem.text()
            elif status & Rename:
                rename[nameItem.text()] = referenceItem.text()
            elif status & New:
                new.append(nameItem.text())
            newSchema.append(nameItem.text())

            iconName = nameItem.data(IconRole)
            if not iconName:
                self.settings.remove(nameItem.text())
            else:
                self.settings.setValue(nameItem.text(), iconName)

        self.settings.endGroup()
        if not any((new, delete, rename, copy)):
            self.applyBtn.setEnabled(False)
            return True

        if delete or rename:
            res = QtWidgets.QMessageBox.critical(
                self, 
                'Restart required', 
                'Bigglesworth *has* to be restarted when renaming or deleting an existing collection.\n' \
                'If you proceed, Bigglesworth will automatically restart itself after completing all the operations.\n\n' \
                'Do you wish to proceed?', 
                QtWidgets.QMessageBox.Ok|QtWidgets.QMessageBox.Cancel)
            if res != QtWidgets.QMessageBox.Ok:
                return False

        self.applyBtn.setEnabled(False)

        if (new or copy) and not (delete or rename):
            for c, src in copy.items():
                self.database.createCollection(c, src)
            for c in new:
                self.database.createCollection(c)
        else:
            createStr = 'CREATE TABLE _temp(uid varchar primary key, tags varchar, blofeld_fact_200801 int, blofeld_fact_200802 int, blofeld_fact_201200 int, '

            schemaStr = ['"Blofeld" int']
            insertStr = ['"Blofeld"']
            selectStr = ['"Blofeld"']
#            self.database.sql.transaction()
            self.query.exec_('ALTER TABLE reference RENAME TO _oldreference')
            for k in newSchema:
                schemaStr.append('"{}" int'.format(k))
                insertStr.append('"{}"'.format(k))
                if k in copy:
                    selectStr.append('"{}"'.format(copy[k]))
                elif k in rename:
                    selectStr.append('"{}"'.format(rename[k]))
                else:
                    selectStr.append('"{}"'.format(k))
            createStr += ', '.join(schemaStr) + ')'
            commitStr = 'INSERT INTO _temp (uid, tags, blofeld_fact_200801, blofeld_fact_200802, blofeld_fact_201200, {}) SELECT uid, tags, blofeld_fact_200801, blofeld_fact_200802, blofeld_fact_201200, {} FROM _oldreference'.format(', '.join(insertStr), ', '.join(selectStr))
            res = self.query.exec_(createStr)
#            self.database.sql.commit()
            if not res:
                self.printError(self.query)
            else:
                self.query.finish()
                res = self.query.exec_(commitStr)
                if not res:
                    self.printError(self.query)
                else:
                    #we need to do a couple of queries, close and open the connection to avoid locking...
                    self.query.finish()
                    self.query.exec_('SELECT "Blofeld" FROM _temp')
                    while self.query.next():
                        pass
                    self.query.finish()
#                    self.database.reconnect()
                    self.query.clear()
                    self.pragmaQuery.clear()
                    res = self.query.exec_('DROP TABLE IF EXISTS _oldreference')
                    if not res:
                        self.printError(self.query)
                    res = self.query.exec_('ALTER TABLE _temp RENAME TO reference')
                    if not res:
                        self.printError(self.query)
            self.database.updateCollections(rename, delete)

        self.populate()
        currentIndex = self.model.index(currentRow, 1)
        self.collectionsView.setCurrentIndex(currentIndex)
        self.collectionsView.scrollTo(currentIndex, self.collectionsView.PositionAtCenter)
        if delete or rename:
            QtWidgets.QApplication.instance().restart()
        return True

    def exec_(self):
        self.populate()
        res = QtWidgets.QDialog.exec_(self)

