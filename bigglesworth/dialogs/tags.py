# *-* encoding: utf-8 *-*

import json

from Qt import QtCore, QtGui, QtWidgets, QtSql

from bigglesworth.utils import loadUi, getValidQColor
from bigglesworth.const import nameRole, backgroundRole, foregroundRole


#class ShadowWidget(QtWidgets.QWidget):
#    def __init__(self, parent):
#        QtWidgets.QWidget.__init__(self, parent)
#        palette = self.palette()
#        palette.setColor(palette.Window, QtGui.QColor(255, 255, 255, 172))
#        self.setPalette(palette)
#        self.setAutoFillBackground(True)
#        layout = QtWidgets.QGridLayout()
#        self.setLayout(layout)
#        label = QtWidgets.QLabel('Updating database, please wait...')
#        layout.addWidget(label, 0, 0, 1, 1, QtCore.Qt.AlignCenter)
#        self.progress = QtWidgets.QProgressBar()
#        layout.addWidget(self.progress)
#        self.progress.setMinimum(0)
#
#    def showEvent(self, event):
#        self.progress.setMaximum(0)
#
#    def hideEvent(self, event):
#        self.progress.setMaximum(1)


class TagsDialog(QtWidgets.QDialog):
    def __init__(self, parent):
        QtWidgets.QDialog.__init__(self, parent)
        loadUi('ui/tagsdialog.ui', self)
        self.changed = False
#        self.shadow = ShadowWidget(self)
#        self.shadow.hide()
#        self.layout().addWidget(self.shadow, 0, 0, self.layout().rowCount(), self.layout().columnCount())
#        self.tagsView.updateStart.connect(self.shadow.show)
#        self.tagsView.updateEnd.connect(self.shadow.hide)

        self.applyBtn = self.buttonBox.button(self.buttonBox.Apply)
        self.applyBtn.setEnabled(False)
        QtWidgets.QApplication.processEvents()
        self.applyBtn.clicked.connect(self.apply)
        self.buttonBox.button(self.buttonBox.Ok).clicked.connect(lambda: [self.apply(), self.accept()])

        self.tagsModel = QtWidgets.QApplication.instance().database.tagsModel
        self.tagsView.setModel(self.tagsModel)
        self.tagsView.selectionModel().selectionChanged.connect(self.selectionChanged)
        self.tagsModel.dataChanged.connect(self.selectionChanged)
#        self.tagsView.model().layoutChanged.connect(self.enableAppy)
#        self.tagsModel.dataChanged.connect(self.enableAppy)

        self.addBtn.clicked.connect(self.tagsView.addTag)
        self.rejected.connect(self.tagsModel.revertAll)
        self.buttonBox.rejected.connect(self.tagsModel.revertAll)
        self.delBtn.clicked.connect(self.delTags)
#        self.buttonBox.button(self.buttonBox.Apply).clicked.connect(self.tagsView.apply)
#        self.tagsView.updateEnd.connect(lambda: self.buttonBox.button(self.buttonBox.Apply).setEnabled(False))
#        self.addBtn.clicked.connect(lambda: self.buttonBox.button(self.buttonBox.Apply).setEnabled(True))
#        self.buttonBox.accepted.connect(self.commit)

    def enableAppy(self):
        self.applyBtn.setEnabled(True)

    def apply(self):
        if not self.applyBtn.isEnabled():
            return
        renamed = {}
        for index, (oldTag, newTag) in self.tagsView.renamed.items():
            if index in self.tagsView.deleted:
                continue
            renamed[oldTag] = newTag
        deleted = set(self.tagsView.deleted.values())
        changed = set(renamed) | deleted
        affected = {}
        query = QtSql.QSqlQuery()
        query.exec_('SELECT uid, tags FROM reference WHERE tags IS NOT NULL AND tags != "[]"')
        while query.next():
            tags = set(json.loads(query.value(1)))
            if tags & changed:
                affected[query.value(0)] = json.loads(query.value(1))
        query.finish()
        self.tagsModel.database().transaction()
        if not self.tagsModel.database().commit():
            print(self.tagsModel.database().lastError().databaseText())
        if self.tagsModel.submitAll():
            self.tagsModel.database().transaction()
            if not self.tagsModel.database().commit():
                print(self.tagsModel.database().lastError().databaseText())
        else:
            print(self.tagsModel.lastError().text())
        for row in range(self.tagsView.model().rowCount()):
            self.tagsView.setRowHidden(row, False)

        for uid, tags in affected.items():
            tags = (set(tags) | deleted) ^ deleted
            tags = sorted([renamed.get(tag, tag) for tag in tags])
            query.prepare('UPDATE reference SET tags=:tags WHERE uid=:uid')
            query.bindValue(':uid', uid)
            query.bindValue(':tags', json.dumps(tags))
            res = query.exec_()
            if not res:
                print(query.lastError().databaseText())

        self.applyBtn.setEnabled(False)
        self.tagsView.applied()
        self.changed = True

    def selectionChanged(self, *args):
        self.delBtn.setEnabled(True if self.tagsView.selectionModel().selectedRows() else False)

    def delTags(self):
        rows = [idx for idx in self.tagsView.selectionModel().selectedRows() if not self.tagsView.isRowHidden(idx.row())]
        self.tagsView.deleteTagsAsk(rows)
        self.buttonBox.button(self.buttonBox.Apply).setEnabled(True)

    def exec_(self):
        #TODO: controlla se serve davvero
        self.tagsView.model().layoutChanged.connect(self.enableAppy)
        self.tagsModel.dataChanged.connect(self.enableAppy)
        res = QtWidgets.QDialog.exec_(self)
        self.tagsView.model().layoutChanged.disconnect(self.enableAppy)
        self.tagsModel.dataChanged.disconnect(self.enableAppy)
        return res

class DeleteTagsMessageBox(QtWidgets.QMessageBox):
    def __init__(self, parent, tags):
        QtWidgets.QMessageBox.__init__(self, parent)
        self.setWindowFlags(QtCore.Qt.Dialog)
        self.setWindowTitle('Remove tags')
        self.setIcon(self.Question)
        self.setText('Remove the following tags?')
        self.setInformativeText('x')
        l = self.findChildren(QtWidgets.QLabel)[-1]
        r, c, rs, cs = self.layout().getItemPosition(self.layout().indexOf(l))
        self.layout().removeWidget(l)
        l.hide()
        self.setStandardButtons(self.Yes|self.No)

        table = QtWidgets.QTableView()
        self.layout().addWidget(table, r, c, rs, cs)
        table.setEditTriggers(table.NoEditTriggers)
        table.horizontalHeader().setVisible(False)
        table.verticalHeader().setVisible(False)
        model = QtGui.QStandardItemModel()
        table.setModel(model)
        for tag in sorted(tags.keys()):
            tagItem = QtGui.QStandardItem(tag)
            tagItem.setFlags(tagItem.flags() ^ QtCore.Qt.ItemIsSelectable)
            soundsItem = QtGui.QStandardItem(str(tags[tag]))
            soundsItem.setFlags(soundsItem.flags() ^ QtCore.Qt.ItemIsSelectable)
            model.appendRow([tagItem, soundsItem])

        table.resizeRowsToContents()
        table.resizeColumnToContents(1)
        table.horizontalHeader().setResizeMode(0, QtWidgets.QHeaderView.Stretch)
        table.horizontalHeader().setResizeMode(1, QtWidgets.QHeaderView.Fixed)
        table.verticalHeader().setResizeMode(QtWidgets.QHeaderView.Fixed)
        table.setMinimumWidth(table.horizontalHeader().sectionSizeHint(0) + table.horizontalHeader().sectionSize(1))
        table.setMinimumHeight(table.verticalHeader().sectionSize(0) * (len(tags) + 1))
#        self.resize(640, 480)
#        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding))
#        self.setMaximumWidth(16777215)
#        self.setMaximumHeight(16777215)


class ColorLineEdit(QtWidgets.QLineEdit):
    editBtnClicked = QtCore.pyqtSignal()
    def __init__(self, *args, **kwargs):
        QtWidgets.QLineEdit.__init__(self, *args, **kwargs)
        self.editBtn = QtWidgets.QPushButton(u'…', self)
        self.editBtn.setCursor(QtCore.Qt.ArrowCursor)
        self.editBtn.clicked.connect(self.editBtnClicked.emit)

    def resizeEvent(self, event):
        size = self.height() - 8
        self.editBtn.resize(size, size)
        self.editBtn.move(self.width() - size - 4, (self.height() - size) / 2)


class ColorDialog(QtWidgets.QDialog):
    def __init__(self, parent, index):
        QtWidgets.QDialog.__init__(self, parent)
        self.setWindowTitle('Select tag colors')
        layout = QtWidgets.QGridLayout()
        self.setLayout(layout)
        layout.addWidget(QtWidgets.QLabel('Set color for tag "{}":'.format(index.sibling(index.row(), 0).data())))
        self.foregroundColor = index.data(QtCore.Qt.ForegroundRole)
        self.backgroundColor = index.data(QtCore.Qt.BackgroundRole)
        self.foregroundEdit = ColorLineEdit()
        basePalette = self.foregroundEdit.palette()
        self.defaultForeground = QtGui.QColor(QtCore.Qt.white)
        self.defaultBackground = QtGui.QColor(QtCore.Qt.darkGray)
        if self.foregroundColor is None:
            self.foregroundColor = self.defaultForeground
        else:
            basePalette.setColor(basePalette.Active, basePalette.Text, self.foregroundColor)
            basePalette.setColor(basePalette.Inactive, basePalette.Text, self.foregroundColor)
        if self.backgroundColor is None:
            self.backgroundColor = self.defaultBackground
        else:
            basePalette.setColor(basePalette.Active, basePalette.Base, self.backgroundColor)
            basePalette.setColor(basePalette.Inactive, basePalette.Base, self.backgroundColor)
        self.foregroundEdit.setText(self.foregroundColor.name())
        self.foregroundEdit.textChanged.connect(self.setForegroundColor)
        self.foregroundEdit.editBtnClicked.connect(self.foregroundSelect)
        self.foregroundEdit.setPalette(basePalette)
        layout.addWidget(self.foregroundEdit, 0, 1)
        autoBgBtn = QtWidgets.QPushButton('Autoset background')
        layout.addWidget(autoBgBtn, 0, 2)
        autoBgBtn.clicked.connect(lambda: self.setBackgroundColor(self.reverseColor(self.foregroundColor)))

        layout.addWidget(QtWidgets.QLabel('Background:'))
        self.backgroundEdit = ColorLineEdit()
        self.backgroundEdit.setText(self.backgroundColor.name())
        self.backgroundEdit.textChanged.connect(self.setBackgroundColor)
        self.backgroundEdit.editBtnClicked.connect(self.backgroundSelect)
        self.backgroundEdit.setPalette(basePalette)
        layout.addWidget(self.backgroundEdit, 1, 1)
        autoFgBtn = QtWidgets.QPushButton('Autoset text')
        layout.addWidget(autoFgBtn, 1, 2)
        autoFgBtn.clicked.connect(lambda: self.setForegroundColor(self.reverseColor(self.backgroundColor)))

        self.buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok|QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.RestoreDefaults)
        layout.addWidget(self.buttonBox, layout.rowCount(), 0, 1, layout.columnCount())
        self.okBtn = self.buttonBox.button(self.buttonBox.Ok)
        self.okBtn.clicked.connect(self.accept)
        self.buttonBox.button(self.buttonBox.Cancel).clicked.connect(self.reject)
        self.restoreBtn = self.buttonBox.button(self.buttonBox.RestoreDefaults)
        self.restoreBtn.setIcon(QtGui.QIcon.fromTheme('edit-undo'))
        self.restoreBtn.clicked.connect(lambda: [self.setBackgroundColor(), self.setForegroundColor()])

    def reverseColor(self, color):
        r, g, b, a = color.getRgb()
        return QtGui.QColor(r^255, g^255, b^255)

    def foregroundSelect(self):
        color = QtWidgets.QColorDialog.getColor(self.foregroundColor, self, 'Select text color')
        if color.isValid():
            self.foregroundEdit.setText(color.name())
            self.setForegroundColor(color)

    def setForegroundColor(self, color=None):
        if not color:
            color = self.defaultForeground
        elif isinstance(color, (str, unicode)):
            color = QtGui.QColor(color)
        self.foregroundColor = color
        palette = self.foregroundEdit.palette()
        palette.setColor(palette.Active, palette.Text, self.foregroundColor)
        palette.setColor(palette.Inactive, palette.Text, self.foregroundColor)
        self.foregroundEdit.setPalette(palette)
        self.backgroundEdit.setPalette(palette)
        self.foregroundEdit.setText(color.name())

    def backgroundSelect(self):
        color = QtWidgets.QColorDialog.getColor(self.backgroundColor, self, 'Select background color')
        if color.isValid():
            self.backgroundEdit.setText(color.name())
            self.setBackgroundColor(color)

    def setBackgroundColor(self, color=None):
        if not color:
            color = self.defaultBackground
        elif isinstance(color, (str, unicode)):
            color = QtGui.QColor(color)
        self.backgroundColor = color
        palette = self.backgroundEdit.palette()
        palette.setColor(palette.Active, palette.Base, self.backgroundColor)
        palette.setColor(palette.Inactive, palette.Base, self.backgroundColor)
        self.foregroundEdit.setPalette(palette)
        self.backgroundEdit.setPalette(palette)
        self.backgroundEdit.setText(color.name())

    def exec_(self):
        res = QtWidgets.QDialog.exec_(self)
        if self.foregroundColor == self.defaultForeground and self.backgroundColor == self.defaultBackground:
            self.foregroundColor = None
            self.backgroundColor = None
        return res


class DeleteDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, *args, **kwargs):
        QtWidgets.QStyledItemDelegate.__init__(self, *args, **kwargs)
        self.delIcon = QtGui.QIcon.fromTheme('edit-delete')

    def paint(self, qp, option, index):
        self.initStyleOption(option, index)
        iconSize = option.decorationSize.width()
        QtWidgets.QStyledItemDelegate.paint(self, qp, option, index)
        if not index.flags() & QtCore.Qt.ItemIsEnabled:
            return
        iconRect = QtCore.QRect((option.rect.width() - iconSize) / 2, (option.rect.height() - iconSize) / 2, iconSize, iconSize)
        qp.save()
        qp.translate(option.rect.x(), option.rect.y())
        qp.drawPixmap(iconRect, self.delIcon.pixmap(iconSize, iconSize))
        qp.restore()


class ColorDelegate(QtWidgets.QStyledItemDelegate):
    def paint(self, qp, option, index):
        if not index.flags() & QtCore.Qt.ItemIsEnabled:
            QtWidgets.QStyledItemDelegate.paint(self, qp, option, QtCore.QModelIndex())
            return
        self.initStyleOption(option, index)
        option.state ^= option.state & (QtWidgets.QStyle.State_Enabled|QtWidgets.QStyle.State_Selected)
        p = option.palette
        p.setColor(p.HighlightedText, index.data(QtCore.Qt.ForegroundRole))
        QtWidgets.QApplication.style().drawPrimitive(QtWidgets.QStyle.PE_PanelItemViewItem, option, qp)
        QtWidgets.QApplication.style().drawItemText(qp, option.rect, option.displayAlignment, p, True, 'Edit...', p.HighlightedText)


class TagValidator(QtGui.QValidator):
    def __init__(self, index):
        QtGui.QValidator.__init__(self)
        self.model = index.model()
        self.current = index

    def fixup(self, text):
        while '  ' in text:
            text = text.replace('  ', ' g')
        return text.strip()

    def validate(self, text, pos):
        if not text:
            return self.Intermediate, text, pos
        res = self.model.match(self.model.index(0, 1), QtCore.Qt.DisplayRole, text, hits=-1, flags=QtCore.Qt.MatchFixedString)
        res = list(filter(lambda index: index.row() != self.current.row() and index.flags() & QtCore.Qt.ItemIsEnabled, res))
        if not res and text.strip() == text:
            return self.Acceptable, text, pos
        return self.Intermediate, text, pos


class TagNameDelegate(QtWidgets.QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        lineEdit = QtWidgets.QStyledItemDelegate.createEditor(self, parent, option, index)
        lineEdit.setValidator(TagValidator(index))
        return lineEdit

    def setModelData(self, editor, model, index):
        text = editor.text().strip()
        if not text:
            return
        res = model.match(model.index(0, 0), QtCore.Qt.DisplayRole, text, hits=-1, flags=QtCore.Qt.MatchFixedString)
        res = list(filter(lambda idx: idx.row() != index.row() and idx.flags() & QtCore.Qt.ItemIsEnabled, res))
        if not res:
            QtWidgets.QStyledItemDelegate.setModelData(self, editor, model, index)
            return
        subStr = ''
        i = 0
        while True:
            res = model.match(model.index(0, 0), QtCore.Qt.DisplayRole, text + subStr, hits=-1, flags=QtCore.Qt.MatchFixedString)
            if index in res:
                res.remove(index)
            if res and any(res[x].flags() & QtCore.Qt.ItemIsEnabled for x in range(len(res))):
                i += 1
                subStr = ' {}'.format(i)
            else:
                break
        model.setData(index, text + subStr)


class TagsProxyModel(QtCore.QIdentityProxyModel):
    columnLabels = ['Tag name', 'Colors', 'Sounds', '']
    tagNameChanged = QtCore.pyqtSignal(object, str)
    def __init__(self, *args, **kwargs):
        QtCore.QIdentityProxyModel.__init__(self, *args, **kwargs)
        self.cachedCounts = {}
        self.query = QtSql.QSqlQuery()
        self.query.prepare('SELECT uid,tags FROM reference WHERE tags IS NOT NULL')

    def headerData(self, section, orientation, role):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return self.columnLabels[section]

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 4

    def data(self, index, role):
        if index.column() == 1:
            if role == QtCore.Qt.BackgroundRole:
                return getValidQColor(self.sourceModel().index(index.row(), 1).data(), backgroundRole)
            if role == QtCore.Qt.ForegroundRole:
                return getValidQColor(self.sourceModel().index(index.row(), 2).data(), foregroundRole)
            if role == QtCore.Qt.DisplayRole:
                return 'Edit...'
        if index.column() == 2:
            if role == QtCore.Qt.DisplayRole:
#                return self.cachedCounts.get(index.sibling(index.row(), 0), 0)
                return self.cachedCounts.get(self.mapToSource(index.sibling(index.row(), 0)), 0)
            if role == QtCore.Qt.TextAlignmentRole:
                return QtCore.Qt.AlignCenter
        return QtCore.QIdentityProxyModel.data(self, index, role)

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        if index.column() == 0 and role == QtCore.Qt.EditRole:
            self.tagNameChanged.emit(index, value)
        if index.column() == 1:
            if role == QtCore.Qt.BackgroundRole:
                self.sourceModel().setData(self.sourceModel().index(index.row(), 1), value)
                self.dataChanged.emit(index, index)
                return True
            if role == QtCore.Qt.ForegroundRole:
                self.sourceModel().setData(self.sourceModel().index(index.row(), 2), value)
                self.dataChanged.emit(index, index)
                return True
        return QtCore.QIdentityProxyModel.setData(self, index, value, role)

    def index(self, row, column, parent=QtCore.QModelIndex()):
        if column == 3:
            return self.createIndex(row, column)
        return QtCore.QIdentityProxyModel.index(self, row, column, parent)

    def flags(self, index):
        if index.column() in (1, 2, 3):
            return QtCore.Qt.ItemIsEnabled
        return QtCore.QIdentityProxyModel.flags(self, index)

    def setSourceModel(self, model):
        QtCore.QIdentityProxyModel.setSourceModel(self, model)
        self.query.exec_()
        existing = set([model.index(row, 0).data() for row in range(model.rowCount())])
        counts = {}
        while self.query.next():
            tags = json.loads(self.query.value(1))
            for tag in tags:
                try:
                    counts[tag] += 1
                except:
                    counts[tag] = 1
        if not set(counts).issubset(existing):
            newTags = (existing | set(counts)) ^ existing
            if newTags:
                oldRowCount = self.rowCount()
                self.insertRows(oldRowCount, len(newTags))
                for row, tag in enumerate(sorted(newTags), oldRowCount):
                    self.setData(self.index(row, 0), tag)
                model.submitAll()
                print(newTags)
        for row in range(model.rowCount()):
            index = model.index(row, 0)
            tag = index.data()
            self.cachedCounts[index] = counts.get(tag, 0)


class TagsTableView(QtWidgets.QTableView):
    updateStart = QtCore.pyqtSignal()
    updateEnd = QtCore.pyqtSignal()

    def __init__(self, *args, **kwargs):
        QtWidgets.QTableView.__init__(self, *args, **kwargs)
        tagNameDelegate = TagNameDelegate(self)
        self.setItemDelegateForColumn(0, tagNameDelegate)
        deleteDelegate = DeleteDelegate(self)
        self.setItemDelegateForColumn(3, deleteDelegate)
        self.deleted = {}
        self.renamed = {}

    def applied(self):
        self.deleted = {}
        self.renamed = {}

    def setModel(self, model):
        self.proxy = TagsProxyModel()
        self.proxy.setSourceModel(model)
        QtWidgets.QTableView.setModel(self, self.proxy)
        self.resizeColumnsToContents()
        self.horizontalHeader().setResizeMode(0, QtWidgets.QHeaderView.Stretch)
        for col in range(1, self.model().columnCount()):
            self.horizontalHeader().setResizeMode(col, QtWidgets.QHeaderView.Fixed)
        self.proxy.tagNameChanged.connect(self.updateRename)

    def updateRename(self, index, name):
        if not index in self.renamed:
            self.renamed[index] = [index.data(), name]
        else:
            self.renamed[index][1] = name

    def keyPressEvent(self, event):
        if event.matches(QtGui.QKeySequence.Delete):
            self.deleteTagsAsk([idx for idx in self.selectionModel().selectedRows() if not self.isRowHidden(idx.row())])
        else:
            QtWidgets.QTableView.keyPressEvent(self, event)

    def mousePressEvent(self, event):
        index = self.indexAt(event.pos())
        if index.isValid():
            if index.column() == 1:
                dialog = ColorDialog(self, index)
                res = dialog.exec_()
                if not res:
                    return
                if dialog.backgroundColor:
                    self.model().setData(index, json.dumps(dialog.backgroundColor.getRgb()[:3]), QtCore.Qt.BackgroundRole)
                else:
                    self.model().setData(index, None, QtCore.Qt.BackgroundRole)
                if dialog.foregroundColor:
                    self.model().setData(index, json.dumps(dialog.foregroundColor.getRgb()[:3]), QtCore.Qt.ForegroundRole)
                else:
                    self.model().setData(index, None, QtCore.Qt.ForegroundRole)
            elif index.column() == 3:
                self.deleteTagAsk(index)
        QtWidgets.QTableView.mousePressEvent(self, event)

    def deleteTagsAsk(self, indexList):
        if len(indexList) == 1:
            self.deleteTagAsk(indexList[0])
            return
        tags = {}
        for index in indexList:
            tagName = index.sibling(index.row(), 0).data()
            sounds = index.sibling(index.row(), 2).data()
            tags[tagName] = sounds
        if not sum(tags.values()):
            self.deleteTags(indexList)
            return
        msgBox = DeleteTagsMessageBox(self, tags)
        res = msgBox.exec_()
        if res == msgBox.Yes:
            self.deleteTags(indexList)
            self.selectionModel().clear()

    def deleteTagAsk(self, index):
        sounds = index.sibling(index.row(), 2).data()
        if not sounds:
            self.deleteTags([index])
            self.selectionModel().clear()
            return
        soundsStr = '<br/><br/>This action applies to {} sound{}.'.format(sounds, 's' if sounds > 1 else '')
        tagName = index.sibling(index.row(), 0).data()
        res = QtWidgets.QMessageBox.question(
            self, 
            'Delete tag?', 
            'Do you want to delete the tag "<b>{}</b>"?{}'.format(tagName, soundsStr), 
            QtWidgets.QMessageBox.Yes|QtWidgets.QMessageBox.No)
        if res == QtWidgets.QMessageBox.Yes:
            self.deleteTags([index])
        self.selectionModel().clear()

    def deleteTags(self, tagList):
        rowList = []
        for index in tagList:
            index = index.sibling(index.row(), 0)
            self.deleted[index] = index.data()
            self.model().removeRows(index.row(), 1)
            rowList.append(index.row())
        for row in rowList:
            self.setRowHidden(row, True)
        self.model().layoutChanged.emit()

    def addTag(self):
        name = 'New tag'
        subStr = ''
        i = 0
        while True:
            res = self.model().match(self.model().index(0, 0), QtCore.Qt.DisplayRole, name + subStr, hits=-1, flags=QtCore.Qt.MatchFixedString)
            if res and any(res[x].flags() & QtCore.Qt.ItemIsEnabled for x in range(len(res))):
                i += 1
                subStr = ' {}'.format(i)
            else:
                break
        name += subStr
        oldRowCount = self.model().rowCount()
        self.model().insertRow(oldRowCount)
        currentIndex = self.model().index(oldRowCount, 0)
        self.model().setData(currentIndex, name)
        self.setCurrentIndex(currentIndex)
        self.edit(currentIndex)
        self.scrollToBottom()


#class xTagsTableView(QtWidgets.QTableView):
#    updateStart = QtCore.pyqtSignal()
#    updateEnd = QtCore.pyqtSignal()
#
#    def __init__(self, *args, **kwargs):
#        QtWidgets.QTableView.__init__(self, *args, **kwargs)
#
#        model = QtGui.QStandardItemModel()
#        QtWidgets.QTableView.setModel(self, model)
#        self.query = QtSql.QSqlQuery()
#        
##        tagNameDelegate = TagNameDelegate(self)
##        self.setItemDelegateForColumn(1, tagNameDelegate)
##        colorDelegate = ColorDelegate(self)
##        self.setItemDelegateForColumn(2, colorDelegate)
##        deleteDelegate = DeleteDelegate(self)
##        self.setItemDelegateForColumn(4, deleteDelegate)
#
#        self.defaultForeground = QtGui.QColor(QtCore.Qt.white)
#        self.defaultBackground = QtGui.QColor(QtCore.Qt.darkGray)
#
#    def keyPressEvent(self, event):
#        if event.matches(QtGui.QKeySequence.Delete):
#            self.deleteTagsAsk(self.selectionModel().selectedRows())
#        else:
#            QtWidgets.QTableView.keyPressEvent(self, event)
#
#    def setDatabase(self, database):
#        self.database = database
#        self.tagsModel = database.tagsModel
##        model.dataChanged.connect(lambda *args: self.updateModel())
#        self.updateModel()
#
#    def updateModel(self):
#        self.model().clear()
#        self.model().setHorizontalHeaderLabels(['', 'Tag name', 'Colors', 'Sounds', ''])
#        self.setColumnHidden(0, True)
#        self.launchQuery()
#
#    def launchQuery(self):
#        res = self.query.exec_('SELECT uid,tags FROM reference WHERE tags IS NOT NULL')
#        if not res:
#            print(self.query.lastError().databaseText())
#            self.query.finish()
#            QtCore.QTimer.singleShot(500, self.launchQuery)
#        else:
#            self.populate()
#
#    def populate(self):
#        self.tagsModel.select()
#        self.updateEnd.emit()
#        self.tagsDict = {}
#        self.revTagsDict = {}
#        while self.query.next():
#            uid = self.query.value(0)
#            tags = json.loads(self.query.value(1))
#            if tags:
#                self.revTagsDict[uid] = tags
#            for tag in tags:
#                if not tag in self.tagsDict:
#                    self.tagsDict[tag] = [uid]
#                    #add tags that do not appear in the table
#                    if not self.tagsModel.match(self.tagsModel.index(0, 0), QtCore.Qt.DisplayRole, tag, flags=QtCore.Qt.MatchExactly):
#                        row = self.tagsModel.rowCount()
#                        self.tagsModel.insertRow(row)
#                        self.tagsModel.setData(self.tagsModel.index(row, 0), tag)
#                        self.tagsModel.data(self.tagsModel.index(row, 0))
#                        self.tagsModel.submitAll()
#                        self.tagsModel.select()
#                else:
#                    self.tagsDict[tag].append(uid)
#
#        for row in range(self.tagsModel.rowCount()):
#            name = self.tagsModel.index(row, 0).data()
#            originalBackground = self.tagsModel.index(row, 1).data()
#            background = getValidQColor(originalBackground, backgroundRole)
#            originalForeground = self.tagsModel.index(row, 2).data()
#            foreground = getValidQColor(originalForeground, foregroundRole)
#            nameItem = QtGui.QStandardItem(name)
#            refItem = nameItem.clone()
#            colorItem = QtGui.QStandardItem(u'Edit...')
#            colorItem.setFlags(colorItem.flags() ^ QtCore.Qt.ItemIsEditable)
#            colorItem.setData(background, QtCore.Qt.BackgroundRole)
#            colorItem.setData(foreground, QtCore.Qt.ForegroundRole)
#            colorItem.setData(QtCore.Qt.AlignCenter, QtCore.Qt.TextAlignmentRole)
#            colorItem.setData(originalBackground, backgroundRole)
#            colorItem.setData(originalForeground, foregroundRole)
#            colorItem.setData(name, nameRole)
#            soundsItem = QtGui.QStandardItem()
#            soundsItem.setData(len(self.tagsDict.get(name, [])), QtCore.Qt.DisplayRole)
#            soundsItem.setFlags(soundsItem.flags() ^ QtCore.Qt.ItemIsEditable)
#            soundsItem.setData(QtCore.Qt.AlignCenter, QtCore.Qt.TextAlignmentRole)
#            deleteItem = QtGui.QStandardItem()
##            deleteItem.setIcon(QtGui.QIcon.fromTheme('edit-delete'))
#            deleteItem.setFlags(deleteItem.flags() ^ QtCore.Qt.ItemIsEditable)
#            self.model().appendRow([refItem, nameItem, colorItem, soundsItem, deleteItem])
#        self.resizeColumnsToContents()
#        self.horizontalHeader().setResizeMode(1, QtWidgets.QHeaderView.Stretch)
#        for col in range(2, self.model().columnCount()):
#            self.horizontalHeader().setResizeMode(col, QtWidgets.QHeaderView.Fixed)
#
#    def mousePressEvent(self, event):
#        index = self.indexAt(event.pos())
#        if index.isValid():
#            if index.column() == 2:
#                dialog = ColorDialog(self, index)
#                res = dialog.exec_()
#                if not res:
#                    return
#                if dialog.backgroundColor:
#                    self.model().setData(index, dialog.backgroundColor, QtCore.Qt.BackgroundRole)
#                    self.model().setData(index, json.dumps(dialog.backgroundColor.getRgb()[:3]), backgroundRole)
#                else:
#                    self.model().setData(index, self.defaultBackground, QtCore.Qt.BackgroundRole)
#                    self.model().setData(index, None, backgroundRole)
##                    self.tagsModel.setData(self.tagsModel.index(index.row(), 1), json.dumps(dialog.backgroundColor.getRgb()[:3]))
#                if dialog.foregroundColor:
#                    self.model().setData(index, dialog.foregroundColor, QtCore.Qt.ForegroundRole)
#                    self.model().setData(index, json.dumps(dialog.foregroundColor.getRgb()[:3]), foregroundRole)
#                else:
#                    self.model().setData(index, self.defaultForeground, QtCore.Qt.ForegroundRole)
#                    self.model().setData(index, None, foregroundRole)
##                    self.tagsModel.setData(self.tagsModel.index(index.row(), 2), json.dumps(dialog.foregroundColor.getRgb()[:3]))
#            elif index.column() == 4:
#                self.deleteTagAsk(index)
#            else:
#                QtWidgets.QTableView.mousePressEvent(self, event)
#                return
##            self.tagsModel.query().exec_()
##            self.tagsModel.submitAll()
#        else:
#            QtWidgets.QTableView.mousePressEvent(self, event)
#
#    def deleteTagAsk(self, index):
#        sounds = index.sibling(index.row(), 3).data()
#        if not sounds:
#            self.deleteTag(index)
#            self.selectionModel().clear()
#            return
#        soundsStr = '<br/><br/>This action applies to {} sound{}.'.format(sounds, 's' if sounds > 1 else '')
#        tagName = index.sibling(index.row(), 0).data()
#        res = QtWidgets.QMessageBox.question(
#            self, 
#            'Delete tag?', 
#            'Do you want to delete the tag "<b>{}</b>"?{}'.format(tagName, soundsStr), 
#            QtWidgets.QMessageBox.Yes|QtWidgets.QMessageBox.No)
#        if res == QtWidgets.QMessageBox.Yes:
#            self.deleteTag(index)
#        self.selectionModel().clear()
#
#    def deleteTagsAsk(self, indexList):
#        if len(indexList) == 1:
#            self.deleteTagAsk(indexList[0])
#            return
#        tags = {}
#        for index in indexList:
#            tagName = index.sibling(index.row(), 1).data()
#            sounds = index.sibling(index.row(), 3).data()
#            tags[tagName] = sounds
#        if not sum(tags.values()):
#            [self.deleteTag(index) for index in indexList]
#            return
#        msgBox = DeleteTagsMessageBox(self, tags)
#        res = msgBox.exec_()
#        if res == msgBox.Yes:
#            [self.deleteTag(index) for index in indexList]
#            self.selectionModel().clear()
#
#    def deleteTag(self, index):
#        row = index.row()
#        for c in range(self.model().columnCount()):
#            item = self.model().item(row, c)
#            item.setFlags((index.flags() | QtCore.Qt.ItemIsEnabled) ^ QtCore.Qt.ItemIsEnabled)
#
#    def addTag(self):
#        name = 'New tag'
#        subStr = ''
#        i = 0
#        while True:
#            res = self.model().match(self.model().index(0, 1), QtCore.Qt.DisplayRole, name + subStr, hits=-1, flags=QtCore.Qt.MatchFixedString)
#            if res and any(res[x].flags() & QtCore.Qt.ItemIsEnabled for x in range(len(res))):
#                i += 1
#                subStr = ' {}'.format(i)
#            else:
#                break
#        nameItem = QtGui.QStandardItem(name + subStr)
#        refItem = QtGui.QStandardItem()
#        colorItem = QtGui.QStandardItem(u'Edit...')
#        colorItem.setFlags(colorItem.flags() ^ QtCore.Qt.ItemIsEditable)
#        colorItem.setData(self.defaultBackground, QtCore.Qt.BackgroundRole)
#        colorItem.setData(self.defaultForeground, QtCore.Qt.ForegroundRole)
#        colorItem.setData(QtCore.Qt.AlignCenter, QtCore.Qt.TextAlignmentRole)
##        colorItem.setData(json.dumps(self.defaultBackground.getRgb()[:3]), backgroundRole)
##        colorItem.setData(json.dumps(self.defaultForeground.getRgb()[:3]), foregroundRole)
#        colorItem.setData('New tag', nameRole)
#        soundsItem = QtGui.QStandardItem()
#        soundsItem.setData(0, QtCore.Qt.DisplayRole)
#        soundsItem.setFlags(soundsItem.flags() ^ QtCore.Qt.ItemIsEditable)
#        soundsItem.setData(QtCore.Qt.AlignCenter, QtCore.Qt.TextAlignmentRole)
#        deleteItem = QtGui.QStandardItem()
#        deleteItem.setFlags(deleteItem.flags() ^ QtCore.Qt.ItemIsEditable)
#        self.model().appendRow([refItem, nameItem, colorItem, soundsItem, deleteItem])
#        currentIndex = self.model().index(self.model().rowCount() - 1, 1)
#        self.setCurrentIndex(currentIndex)
#        self.edit(currentIndex)
#        self.scrollToBottom()
#
#    def apply(self):
#        self.updateStart.emit()
#        QtWidgets.QApplication.processEvents()
#        newTags = {}
#        renamed = {}
#        deleted = []
#        for row in range(self.model().rowCount()):
#            refItem = self.model().item(row, 0)
#            nameItem = self.model().item(row, 1)
#            if not refItem.flags() & QtCore.Qt.ItemIsEnabled:
#                sounds = self.model().item(row, 3).data(QtCore.Qt.DisplayRole)
#                if refItem.text() and sounds:
#                    deleted.append(refItem.text())
#                continue
#            colorItem = self.model().item(row, 2)
#            fg = colorItem.data(foregroundRole)
#            bg = colorItem.data(backgroundRole)
#            newTags[nameItem.text()] = bg, fg
#            if refItem.text() and refItem.text() != nameItem.text() and refItem.text() not in deleted:
#                renamed[refItem.text()] = nameItem.text()
#
##        print(newTags, renamed, deleted)
#        totOrig = self.tagsModel.rowCount()
#        totNew = len(newTags)
#        if totOrig < totNew:
#            self.tagsModel.insertRows(totOrig, totNew - totOrig)
#        elif totOrig > totNew:
#            self.tagsModel.removeRows(totNew, totOrig - totNew)
#        oldStrategy = self.tagsModel.editStrategy()
#        self.tagsModel.setEditStrategy(self.tagsModel.OnManualSubmit)
#        self.database.sql.transaction()
#        for row, tag in enumerate(sorted(newTags.keys())):
#            self.tagsModel.setData(self.tagsModel.index(row, 0), tag)
#            bg, fg = newTags[tag]
#            self.tagsModel.setData(self.tagsModel.index(row, 1), bg)
#            self.tagsModel.setData(self.tagsModel.index(row, 2), fg)
#        print('submit', row, tag, self.tagsModel.submitAll())
#        print(self.tagsModel.lastError().text())
#        self.database.sql.commit()
#        self.tagsModel.setEditStrategy(oldStrategy)
##        self.tagsModel.query().exec_()
##        self.tagsModel.query().finish()
##        self.query.finish()
##        while self.tagsModel.query().next() and self.query.next():
##            pass
##        return
#
#        if renamed or deleted:
#            for uid, tags in self.revTagsDict.items():
#                #remove deleted tags
#                newTags = (set(tags) | set(deleted)) ^ set(deleted)
#                #update tags
#                newTags = [renamed.get(k, k) for k in newTags]
#                if set(tags) == set(newTags):
#                    continue
#                self.query.prepare('UPDATE reference SET tags=:tags WHERE uid=:uid')
#                self.query.bindValue(':tags', json.dumps(sorted(newTags)))
#                self.query.bindValue(':uid', uid)
#                res = self.query.exec_()
#                if not res:
#                    print(self.query.lastError().databaseText())
#
##        self.query.exec_('SELECT * FROM reference')
##        self.query.first()
##        while self.tagsModel.query().next() and self.query.next():
##            pass
##        self.query.finish()
#
##        self.database.sql.close()
##        self.database.sql.open()
#        self.updateModel()
#        self.tagsModel.select()
#
#
##    def dbdeleteTag(self, tagName, row):
##        uidList = self.tagsDict.get(tagName)
##        if uidList:
##            uidDict = {}
##            querySelStr = 'SELECT uid, tags FROM reference WHERE '
##            querySetStr = 'UPDATE reference SET tags=:tags WHERE uid =:uid'
##            queryWhere = []
##            for uid in uidList:
##    #            uidDict[uid] = []
##                queryWhere.append('uid = "{}"'.format(uid))
##            self.query.exec_(querySelStr + ' OR '.join(queryWhere))
##            while self.query.next():
##                tags = json.loads(self.query.value(1))
##                tags.pop(tags.index(tagName))
##                uidDict[self.query.value(0)] = tags
##            self.query.prepare(querySetStr)
##            for uid, tags in uidDict.items():
##                self.query.bindValue(':tags', json.dumps(tags))
##                self.query.bindValue(':uid', uid)
##                self.query.exec_()
##        #we could wait for the Sql model to update, but it takes up to 2 seconds, let's remove it manually
##        self.tagsModel.removeRow(row)
##        self.model().removeRow(row)
