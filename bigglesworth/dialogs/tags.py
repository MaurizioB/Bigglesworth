# *-* encoding: utf-8 *-*

import json
from unidecode import unidecode as _unidecode

from Qt import QtCore, QtGui, QtWidgets, QtSql

from bigglesworth.utils import loadUi, getValidQColor, getName
from bigglesworth.const import nameRole, backgroundRole, foregroundRole
from bigglesworth.widgets.filters import FilterTagsEdit

def unidecode(text):
    output = ''
    for l in text:
        if l == u'°':
            output += l
        else:
            output += _unidecode(l)
    return output

validChars = set(' !#$%&()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~')


class TagValidator(QtGui.QValidator):
    def __init__(self):
        QtGui.QValidator.__init__(self)
        self.tagsModel = QtWidgets.QApplication.instance().tagsModel

    def validate(self, text, pos):
        text = unidecode(text)
        if not text or len(text) > 32 and not set(text).issubset(validChars):
            return self.Intermediate, text, pos
        res = self.tagsModel.match(self.tagsModel.index(0, 0), QtCore.Qt.DisplayRole, text, hits=-1, flags=QtCore.Qt.MatchFixedString)
        if not res and text.lstrip() == text:
            return self.Acceptable, text, pos
        return self.Intermediate, text, pos


class TagEdit(QtWidgets.QLineEdit):
    accepted = QtCore.pyqtSignal(str)
    ignored = QtCore.pyqtSignal()

    def __init__(self, tag='', readOnly=False, notifyLostFocus=False):
        QtWidgets.QLineEdit.__init__(self, tag)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed))
        self.setMaxLength(32)
        self.tagsModel = QtWidgets.QApplication.instance().tagsModel
        self.setReadOnly(readOnly)
        if not readOnly:
            self.textChanged.connect(self.isValid)
            self.setValidator(TagValidator())
        self.notifyLostFocus = notifyLostFocus

    def isValid(self, text):
        valid, _, _ = self.validator().validate(text, 0)
        if not self.isReadOnly():
            if valid == QtGui.QValidator.Intermediate:
                self.setStyleSheet('color: red')
            else:
                self.setStyleSheet('')
        return valid

    def focusOutEvent(self, event):
        if self.notifyLostFocus:
            self.ignored.emit()
        QtWidgets.QLineEdit.focusOutEvent(self, event)

    def keyPressEvent(self, event):
        if event.key() in (QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return):
            if self.isValid(self.text()) == QtGui.QValidator.Acceptable:
                self.accepted.emit(self.text().strip())
            return event.accept()
        elif event.key() == QtCore.Qt.Key_Escape:
            self.ignored.emit()
            return event.accept()
        QtWidgets.QLineEdit.keyPressEvent(self, event)


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

        self.addBtn.clicked.connect(self.showAddTagDialog)
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

    def showAddTagDialog(self):
        name = 'New tag'
        subStr = ''
        i = 0
        model = self.tagsView.model()
        while True:
            res = model.match(model.index(0, 0), QtCore.Qt.DisplayRole, name + subStr, hits=-1, flags=QtCore.Qt.MatchFixedString)
            if res and any(res[x].flags() & QtCore.Qt.ItemIsEnabled for x in range(len(res))):
                i += 1
                subStr = ' {}'.format(i)
            else:
                break
        name += subStr
        row = model.rowCount()
        model.insertRow(row)
        index = model.index(row, 0)
        model.setData(index, name)

        dialog = TagEditDialog(self, name, new=True)
        dialog.tagEdit.setValidator(TagTableValidator(index))
        res = dialog.exec_()
        if not res:
            model.removeRow(row)
            return

        if dialog.backgroundColor:
            model.setData(model.index(row, 1), json.dumps(dialog.backgroundColor.getRgb()[:3]), QtCore.Qt.BackgroundRole)
        if dialog.foregroundColor:
            model.setData(model.index(row, 1), json.dumps(dialog.foregroundColor.getRgb()[:3]), QtCore.Qt.ForegroundRole)

        self.tagsView.setCurrentIndex(index)
        self.tagsView.scrollToBottom()

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
        return self.changed | res


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


class TagEditDialog(QtWidgets.QDialog):
    defaultForeground = QtGui.QColor(QtCore.Qt.white)
    defaultBackground = QtGui.QColor(QtCore.Qt.darkGray)
#    colorValidator = QtGui.QRegExpValidator(QtCore.QRegExp(r'^[#](?:[a-fA-F0-9]{3}|[a-fA-F0-9]{6})$'))

    def __init__(self, parent, name='', new=False, fgd=None, bgd=None):
        QtWidgets.QDialog.__init__(self, parent)
        self.setWindowTitle('Select tag colors')
        layout = QtWidgets.QGridLayout()
        self.setLayout(layout)

        layout.addWidget(QtWidgets.QLabel('Tag name:'))
        self.tagEdit = TagEdit(name, not new)
        layout.addWidget(self.tagEdit, 0, 1, 1, 2)
        self.tagEdit.ignored.connect(self.reject)
        self.tagEdit.accepted.connect(self.accept)

        self.foregroundColor = fgd if fgd else self.defaultForeground
        self.backgroundColor = bgd if bgd else self.defaultBackground
        self.foregroundEdit = ColorLineEdit()
        basePalette = self.foregroundEdit.palette()
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
        layout.addWidget(QtWidgets.QLabel('Text color:'))
        self.foregroundEdit.setText(self.foregroundColor.name())
        self.foregroundEdit.textChanged.connect(self.validateColor)
        self.foregroundEdit.editBtnClicked.connect(self.foregroundSelect)
        self.foregroundEdit.setPalette(basePalette)
        layout.addWidget(self.foregroundEdit, 1, 1)
        autoBgBtn = QtWidgets.QPushButton('Autoset background')
        layout.addWidget(autoBgBtn, 1, 2)
        autoBgBtn.clicked.connect(lambda: self.setBackgroundColor(self.reverseColor(self.foregroundColor)))

        layout.addWidget(QtWidgets.QLabel('Background:'))
        self.backgroundEdit = ColorLineEdit()
        self.backgroundEdit.setText(self.backgroundColor.name())
        self.backgroundEdit.textChanged.connect(self.validateColor)
        self.backgroundEdit.editBtnClicked.connect(self.backgroundSelect)
        self.backgroundEdit.setPalette(basePalette)
        layout.addWidget(self.backgroundEdit, 2, 1)
        autoFgBtn = QtWidgets.QPushButton('Autoset text')
        layout.addWidget(autoFgBtn, 2, 2)
        autoFgBtn.clicked.connect(lambda: self.setForegroundColor(self.reverseColor(self.backgroundColor)))

        self.buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok|QtWidgets.QDialogButtonBox.Cancel)
        layout.addWidget(self.buttonBox, layout.rowCount(), 0, 1, layout.columnCount())
        self.okBtn = self.buttonBox.button(self.buttonBox.Ok)
        self.okBtn.clicked.connect(self.accept)
        self.buttonBox.button(self.buttonBox.Cancel).clicked.connect(self.reject)

        self.restoreBtn = self.buttonBox.addButton('Default colors', self.buttonBox.ResetRole)
        self.restoreBtn.setIcon(QtGui.QIcon.fromTheme('edit-undo'))
        self.restoreBtn.clicked.connect(lambda: [self.setBackgroundColor(), self.setForegroundColor()])

        if new:
            self.tagEdit.textChanged.connect(lambda tag: self.okBtn.setEnabled(self.tagEdit.isValid(tag) == QtGui.QValidator.Acceptable))
        else:
            self.tagEdit.setEnabled(False)

    def reverseColor(self, color):
        def isDifferent(lightDelta):
            return (abs(r - _r) + abs(g - _g) + abs(b - _b)) > 64 and abs(color.lightness() - newColor.lightness()) > lightDelta
        _r, _g, _b = color.getRgb()[:3]
        r = _r^255
        g = _g^255
        b = _b^255
        newColor = QtGui.QColor(r, g, b)
        if not isDifferent(96):
            newColor = QtGui.QColor(r, g, b).lighter()
            r, g, b = newColor.getRgb()[:3]
        if not isDifferent(48):
            newColor = QtGui.QColor(r, g, b).darker()
            r, g, b = newColor.getRgb()[:3]
        return QtGui.QColor(r, g, b)

    def validateColor(self, text):
        edit = self.sender()
        color = QtGui.QColor(edit.text())
        if color.isValid():
            if edit == self.foregroundEdit:
                self.setForegroundColor(color)
            else:
                self.setBackgroundColor(color)
#        print(self.colorValidator.validate(text, edit.cursorPosition())[0])

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


class TagTableValidator(QtGui.QValidator):
    def __init__(self, index):
        QtGui.QValidator.__init__(self)
        self.model = index.model()
        self.current = index

    def fixup(self, text):
        while '  ' in text:
            text = text.replace('  ', ' g')
        return text.strip()

    def validate(self, text, pos):
        text = unidecode(text)
        if not text or len(text) > 32 and not set(text).issubset(validChars):
            return self.Intermediate, text, pos
        res = self.model.match(self.model.index(0, 0), QtCore.Qt.DisplayRole, text, hits=-1, flags=QtCore.Qt.MatchFixedString)
        res = list(filter(lambda index: index.row() != self.current.row() and index.flags() & QtCore.Qt.ItemIsEnabled, res))
        if not res and text.lstrip() == text:
            return self.Acceptable, text, pos
        return self.Intermediate, text, pos


class TagNameDelegate(QtWidgets.QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        lineEdit = QtWidgets.QStyledItemDelegate.createEditor(self, parent, option, index)
        lineEdit.setValidator(TagTableValidator(index))
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
                fgd = index.data(QtCore.Qt.ForegroundRole)
                bgd = index.data(QtCore.Qt.BackgroundRole)
                dialog = TagEditDialog(self, index.sibling(index.row(), 0).data(), fgd=fgd, bgd=bgd)
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

    def mouseDoubleClickEvent(self, event):
        index = self.indexAt(event.pos())
        if index.isValid():
            QtWidgets.QTableView.mouseDoubleClickEvent(self, event)
        else:
            self.addTag()

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


class BaseTagsEditDialog(QtWidgets.QDialog):
    def __init__(self, parent, tagsModel):
        QtWidgets.QDialog.__init__(self, parent)
        layout = QtWidgets.QGridLayout()
        self.setLayout(layout)
        self.header = QtWidgets.QLabel()
        self.header.setWordWrap(True)
        layout.addWidget(self.header)

        self.sourceTagsModel = tagsModel
        self.filterTagsEdit = FilterTagsEdit()
        layout.addWidget(self.filterTagsEdit)
        self.filterTagsEdit.setModel(tagsModel)
        self.filterTagsEdit.installEventFilter(self)
        self.filterTagsEdit.tagsChanged.connect(self.checkTable)

        self.tagsTable = QtWidgets.QTableView()
        layout.addWidget(self.tagsTable)
        self.tagsModel = QtGui.QStandardItemModel()
        self.tagsTable.setModel(self.tagsModel)
        self.loadTags()

        self.tagsTable.setEditTriggers(self.tagsTable.NoEditTriggers)
        self.tagsTable.doubleClicked.connect(self.addTag)

        buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok|QtWidgets.QDialogButtonBox.Cancel)
        layout.addWidget(buttonBox)
        buttonBox.button(buttonBox.Ok).clicked.connect(self.accept)
        buttonBox.button(buttonBox.Cancel).clicked.connect(self.reject)
        self.tagManagerBtn = QtWidgets.QPushButton(QtGui.QIcon.fromTheme('tag'), 'Manage tags')
#        buttonBox.addButton(self.tagManagerBtn, buttonBox.ActionRole)
        buttonBox.layout().insertWidget(0, self.tagManagerBtn)
#        self.tagManagerBtn.setIcon(QtGui.QIcon.fromTheme('edit-undo'))
        self.tagManagerBtn.clicked.connect(self.showTagManager)
        self.resize(480, 320)

        self.query = QtSql.QSqlQuery()

    @property
    def tags(self):
        return self.filterTagsEdit.tags

    def showTagManager(self):
        tagsDialog = TagsDialog(self)
        if not tagsDialog.exec_() or not tagsDialog.changed:
            return
        self.filterTagsEdit.setModel(self.sourceTagsModel)
        self.loadTags()
        self.checkTable(self.filterTagsEdit.tags)

    def loadTags(self):
        self.tagsModel.clear()
        for row in range(self.sourceTagsModel.rowCount()):
            tag = self.sourceTagsModel.index(row, 0).data()
            tagItem = QtGui.QStandardItem(tag)
            if tag in self.filterTagsEdit.tags:
                tagItem.setEnabled(False)
#                tagItem.setFlags(tagItem.flags() ^ QtCore.Qt.ItemIsEnabled)
            backgroundColor = getValidQColor(self.sourceTagsModel.index(row, 2).data(), foregroundRole)
            tagItem.setData(backgroundColor, QtCore.Qt.BackgroundRole)
            tagItem.setData(backgroundColor, foregroundRole)
            foregroundColor = getValidQColor(self.sourceTagsModel.index(row, 1).data(), backgroundRole)
            tagItem.setData(foregroundColor, QtCore.Qt.ForegroundRole)
            tagItem.setData(foregroundColor, backgroundRole)
            self.tagsModel.appendRow(tagItem)
        self.tagsModel.sort(0)
        self.tagsTable.setColumnHidden(1, True)
        self.tagsTable.setColumnHidden(2, True)
        self.tagsTable.horizontalHeader().setStretchLastSection(True)
        self.tagsTable.horizontalHeader().setVisible(False)
        self.tagsTable.verticalHeader().setVisible(False)
        self.tagsTable.resizeRowsToContents()

    def addTag(self, index):
        tag = index.data()
        if tag not in self.filterTagsEdit.tags:
            self.filterTagsEdit.setTags(self.filterTagsEdit.tags + [tag])

    def checkTable(self, tags):
        for row in range(self.tagsModel.rowCount()):
            item = self.tagsModel.item(row)
            if item.text() in tags:
                item.setData(self.palette().color(QtGui.QPalette.Disabled, QtGui.QPalette.Base), QtCore.Qt.BackgroundRole)
                item.setData(self.palette().color(QtGui.QPalette.Disabled, QtGui.QPalette.Text), QtCore.Qt.ForegroundRole)
            else:
                item.setData(item.data(backgroundRole), QtCore.Qt.BackgroundRole)
                item.setData(item.data(foregroundRole), QtCore.Qt.ForegroundRole)
            item.setEnabled(False if item.text() in tags else True)

    def eventFilter(self, source, event):
        if event.type() == QtCore.QEvent.KeyPress and event.key() == QtCore.Qt.Key_Escape:
            self.reject()
            return True
        if event.type() == QtCore.QEvent.KeyPress and event.key() in (QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return) and \
            self.filterTagsEdit.text():
                return True
        return QtWidgets.QDialog.eventFilter(self, source, event)


class SoundTagsEditDialog(BaseTagsEditDialog):
    def __init__(self, parent, uid, tagsModel):
        BaseTagsEditDialog.__init__(self, parent, tagsModel)
        nameChars = ','.join('sounds.nameChar{:02}'.format(l) for l in range(16))
        self.query.exec_('SELECT reference.tags,{} FROM sounds,reference WHERE sounds.uid="{}" AND reference.uid="{}"'.format(nameChars, uid, uid))
        self.query.first()
        self.header.setText('Set tags for sound "{}"'.format(getName(self.query.value(v) for v in range(1, 17)).strip()))

        self.filterTagsEdit.setTags(sorted(json.loads(self.query.value(0))))
        self.filterTagsEdit.setText('')
#        self.checkTable(self.tags)


class MultiSoundTagsEditDialog(SoundTagsEditDialog):
    def __init__(self, parent, uidList, tags, tagsModel):
        BaseTagsEditDialog.__init__(self, parent, tagsModel)
        self.filterTagsEdit.setTags(tags)
        self.filterTagsEdit.setText('')

        nameChars = ','.join('sounds.nameChar{:02}'.format(l) for l in range(16))
        uidSelect = ') OR ('.join('sounds.uid="{uid}" AND reference.uid="{uid}"'.format(uid=uid) for uid in uidList)
        self.query.exec_('SELECT sounds.uid,reference.tags,{} FROM sounds,reference WHERE ({})'.format(nameChars, uidSelect))
        uidDict = {}
        tags = set()
        while self.query.next():
            name = getName(self.query.value(v) for v in range(2, 18)).strip()
            uidDict[name] = self.query.value(0)
            tags |= set(json.loads(self.query.value(1)))
        header = 'Set tags for the following sounds:<br/><br/><b>'
        uidNames = sorted(uidDict)
        rest = 0
        if len(uidNames) > 15:
            rest = len(uidNames) - 10
            uidNames = uidNames[:10]
        header += '</b>, <b>'.join(uidNames) + '</b>'
        if rest:
            header += ', and {} more...'.format(rest)
        header += '<br/><br/><b>NOTE</b>: tags will be applied to all selected sounds!'
        self.header.setText(header)


