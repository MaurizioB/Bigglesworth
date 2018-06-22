import json

from Qt import QtCore, QtGui, QtWidgets, QtSql

from bigglesworth.widgets.filters import FilterTagsEdit
from bigglesworth.utils import getName, getValidQColor
from bigglesworth.const import backgroundRole, foregroundRole
from bigglesworth.dialogs import TagsDialog

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


