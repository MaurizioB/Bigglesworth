from Qt import QtCore, QtGui, QtWidgets

from bigglesworth.const import templates
from bigglesworth.parameters import Parameters, categories
from bigglesworth.utils import loadUi, localPath, setBold

singlesDict = {}
groupsDict = {}
for s, g in templates:
    singlesDict[s.dbName] = s
    if g:
        groupsDict[g.dbName] = g

CountRole = QtCore.Qt.UserRole + 1
GroupRole = CountRole + 1
#ValueRole = GroupRole + 1
NameRole = GroupRole
ParamRole = NameRole + 1


class TemplateModel(QtGui.QStandardItemModel):
    nameChanged = QtCore.pyqtSignal(str, str)
    def setData(self, index, value, role):
        if role == QtCore.Qt.EditRole:
            old = index.data(QtCore.Qt.DisplayRole)
            new = value
            res = QtGui.QStandardItemModel.setData(self, index, value, role)
            self.nameChanged.emit(new, old)
            return res
        return QtGui.QStandardItemModel.setData(self, index, value, role)


class ParamModel(QtGui.QStandardItemModel):
    def __init__(self):
        QtGui.QStandardItemModel.__init__(self)
        self.labelMode = 1

    def setMode(self, mode):
        self.labelMode = mode

class TemplateValidator(QtGui.QValidator):
    def __init__(self, templates):
        QtGui.QValidator.__init__(self)
        self.templates = templates
        self.baseValidator = QtGui.QRegExpValidator(QtCore.QRegExp(r'^(?!.* {2})(?=\S)[a-zA-Z0-9\ \-\_]+$'))
        self.name = None

    def setValid(self, name):
        self.name = name

    def validate(self, text, pos):
        #TODO: check for case!!!
        if not text:
            return self.Intermediate, text, pos
        res, text, pos = self.baseValidator.validate(text, pos)
        if res == self.Acceptable:
            if text == self.name:
                return res, text, pos
            elif text not in self.templates:
                return res, text, pos
            else:
                return self.Intermediate, text, pos
        else:
            return res, text, pos


class TemplateDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, templates):
        QtWidgets.QStyledItemDelegate.__init__(self)
        self.templates = templates
        self.validator = TemplateValidator(templates)

    def createEditor(self, parent, option, index):
        lineEdit = QtWidgets.QStyledItemDelegate.createEditor(self, parent, option, index)
        lineEdit.setMaxLength(16)
        self.validator.setValid(index.data(QtCore.Qt.DisplayRole))
        lineEdit.setValidator(self.validator)
        return lineEdit

    def paint(self, painter, option, index):
        self.initStyleOption(option, index)
        count = index.data(CountRole)
        if not count:
            QtWidgets.QStyledItemDelegate.paint(self, painter, option, index)
            return
        option.text += ' ({})'.format(count)
        QtWidgets.QApplication.style().drawControl(QtWidgets.QStyle.CE_ItemViewItem, option, painter)


class ParamDelegate(QtWidgets.QStyledItemDelegate):
    def paint(self, painter, option, index):
        self.initStyleOption(option, index)
        option.text = index.data(NameRole)[index.model().labelMode]
        QtWidgets.QApplication.style().drawControl(QtWidgets.QStyle.CE_ItemViewItem, option, painter)


class ValueDelegate(QtWidgets.QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        combo = QtWidgets.QComboBox(parent)
        combo.setEditable(True)
        combo.setInsertPolicy(combo.NoInsert)
        param = index.data(ParamRole)
        combo.addItems(param.values)
        value = index.data(QtCore.Qt.DisplayRole)
        if param.range.step != 1:
            value = (value - param.range.minimum) // param.range.step
        elif param.range.minimum > 0:
            value = value - param.range.minimum
        combo.setCurrentIndex(value)
        return combo

    def setModelData(self, widget, model, index):
        param = index.data(ParamRole)
        value = widget.currentIndex()
        if param.range.minimum != 0:
            value += param.range.minimum
        if param.range.step != 1:
            value *= param.range.step
        model.setData(index, value, QtCore.Qt.DisplayRole)

    def paint(self, painter, option, index):
        self.initStyleOption(option, index)
        value = index.data(QtCore.Qt.DisplayRole)
        param = index.data(ParamRole)
        if param.range.step != 1:
            value = (value - param.range.minimum) // param.range.step
        elif param.range.minimum > 0:
            value = value - param.range.minimum
        option.text = str(param.values[value])
        QtWidgets.QApplication.style().drawControl(QtWidgets.QStyle.CE_ItemViewItem, option, painter)


class TemplateManager(QtWidgets.QDialog):
    def __init__(self, parent):
        QtWidgets.QDialog.__init__(self, parent)
        loadUi(localPath('ui/templates.ui'), self)
        self.main = parent.main
        self.database = parent.main.database
        self.templateModel = TemplateModel()
        self.templateModel.nameChanged.connect(self.templateNameChanged)
        self.templateView.setModel(self.templateModel)
        self.templateView.clicked.connect(self.showTemplate)
        self.templates = {}
        self.templateDelegate = TemplateDelegate(self.templates)
        self.templateView.setItemDelegate(self.templateDelegate)
        self.templateView.customContextMenuRequested.connect(self.templateMenu)

        self.currentTemplate = None

        self.soundGroupItem = QtGui.QStandardItem('Sounds')
        self.catItems = []
        self.templateModel.appendRow(self.soundGroupItem)
        for cat in categories:
            cat = cat.strip()
            catItem = QtGui.QStandardItem(cat)
            catItem.setFlags(catItem.flags() ^ QtCore.Qt.ItemIsEditable)
            self.catItems.append(catItem)
            self.soundGroupItem.appendRow(catItem)

        self.counts = {}
        self.singleItems = {}
        self.groupItems = {}
        for single, group in templates:
            mainItem = QtGui.QStandardItem()
            mainItem.setFlags(mainItem.flags() ^ QtCore.Qt.ItemIsEditable)
            self.templateModel.appendRow(mainItem)
            self.counts[single.dbName] = [mainItem]
            if not group:
                mainItem.setText(single.fullName)
                self.singleItems[single.dbName] = mainItem
            else:
                mainItem.setText(group.fullName)
                singleItem = QtGui.QStandardItem('Single')
                singleItem.setFlags(singleItem.flags() ^ QtCore.Qt.ItemIsEditable)
                self.singleItems[single.dbName] = singleItem
                groupItem = QtGui.QStandardItem('Group')
                groupItem.setFlags(singleItem.flags())
                self.groupItems[group.dbName] = groupItem
                self.counts[single.dbName].append(singleItem)
                self.counts[group.dbName] = [mainItem, groupItem]
                mainItem.appendRows([groupItem, singleItem])

        self.parameters = []
        self.paramModel = ParamModel()
        self.paramTable.setModel(self.paramModel)
        self.valueDelegate = ValueDelegate()
        self.paramTable.setItemDelegateForColumn(1, self.valueDelegate)
        self.paramDelegate = ParamDelegate()
        self.paramTable.setItemDelegateForColumn(0, self.paramDelegate)
        paramFlags = QtCore.Qt.ItemIsEnabled|QtCore.Qt.ItemIsSelectable
        for i, p in enumerate(Parameters.parameterData):
            if p.attr.startswith('reserved'):
                self.paramModel.appendRow(QtGui.QStandardItem())
                self.paramTable.setRowHidden(i, True)
                continue
            paramItem = QtGui.QStandardItem(p.fullName)
            paramItem.setData((p.shortName, p.fullName), NameRole)
            paramItem.setFlags(paramFlags)
            valueItem = QtGui.QStandardItem()
            valueItem.setData(p.range.minimum, QtCore.Qt.DisplayRole)
            valueItem.setData(p, ParamRole)
            self.paramModel.appendRow([paramItem, valueItem])
            self.paramTable.setRowHidden(i, True)
        self.paramModel.setHorizontalHeaderLabels(['Parameter', 'Value'])
        self.paramTable.resizeRowsToContents()
        self.paramTable.horizontalHeader().setResizeMode(0, QtWidgets.QHeaderView.Fixed)

    def paramDataChanged(self, index, last=None):
        name = self.currentTemplate.data(QtCore.Qt.DisplayRole)
        self.templates[name][1][index.row()] = index.data(QtCore.Qt.DisplayRole)
        self.changed = True
#        data = self.currentTemplate.data(ValueRole)
#        data[index.row()] = index.data(QtCore.Qt.DisplayRole)
#        index.setData(data)

    def templateNameChanged(self, newName, oldName):
        self.templates[newName] = self.templates.pop(oldName)
        self.changed = True
#        print('{} > {}'.format(oldName, newName))

    def templateMenu(self, pos):
        index = self.templateView.indexAt(pos)
        if not index.flags() & QtCore.Qt.ItemIsEditable:
            return
        menu = QtWidgets.QMenu()
        renameAction = menu.addAction(QtGui.QIcon.fromTheme('edit-rename'), 'Rename...')
        deleteAction = menu.addAction(QtGui.QIcon.fromTheme('edit-delete'), 'Delete')
        res = menu.exec_(self.templateView.viewport().mapToGlobal(pos))
        if res == renameAction:
            self.templateView.edit(index)
        elif res == deleteAction:
            res = QtWidgets.QMessageBox.question(self, 'Delete template', 
                'Delete the template "{}"?'.format(index.data()), 
                QtWidgets.QMessageBox.Ok|QtWidgets.QMessageBox.Cancel)
            if res == QtWidgets.QMessageBox.Ok:
                self.templateView.setCurrentIndex(QtCore.QModelIndex())
                groups, valueList = self.templates.pop(index.data())
                for group in groups:
                    for countItem in self.counts[group]:
                        count = countItem.data(CountRole) - 1
                        countItem.setData(count, CountRole)
                        if not count:
                            setBold(countItem, False)
                self.deleted.append(index.data())
                self.changed = True
                self.templateModel.removeRow(index.row(), index.parent())
                for r in range(self.paramModel.rowCount()):
                    self.paramTable.setRowHidden(r, True)

    def showEvent(self, event):
        if not self.shown:
            self.shown = True
            size = sum(self.splitter.sizes()) * .5
            self.splitter.setSizes([size, size])

    def showTemplate(self, index):
        try:
            self.paramModel.dataChanged.disconnect(self.paramDataChanged)
        except:
            pass
        groups = index.data(GroupRole)
        if groups is None:
            return
        if len(groups) == 1:
            groups = groups[0]

        self.currentTemplate = index
#        for p, value in zip(Parameters.parameterData, index.data(ValueRole)):
        for p, value in zip(Parameters.parameterData, self.templates[index.data()][1]):
            if p.attr.startswith('reserved'):
                continue
            if isinstance(value, (int, long)):
                self.paramTable.setRowHidden(p.id, False)
            else:
                self.paramTable.setRowHidden(p.id, True)
            self.paramModel.item(p.id, 1).setData(value, QtCore.Qt.DisplayRole)
        single = groups in singlesDict
        self.paramTable.verticalHeader().setVisible(not single)
        self.paramModel.setMode(not single)
        self.paramTable.viewport().update()
        self.paramModel.dataChanged.connect(self.paramDataChanged)
        self.paramTable.resizeColumnToContents(0)

    def exec_(self):
        self.shown = False
#        reset?
#        for countItem in self.counts.values():
#            countItem.setData(0, QtCore.Qt.DisplayRole)
#        for r in range(self.paramModel.rowCount()):
#            self.paramTable.setRowHidden(r, True)

        self.deleted = []
        self.changed = False
        self.templates.clear()
        self.templates.update(self.database.getTemplatesByName())
        for name in sorted(self.templates):
            groups, valueList = self.templates[name]
            if not groups or len(groups) != 1:
                print('uhmmm...')
                continue
            item = QtGui.QStandardItem(name)
            item.setData(groups, GroupRole)
#            item.setData(valueList, ValueRole)
            group = groups[0]
            for countItem in self.counts[group]:
                count = countItem.data(CountRole)
                if count is None:
                    count = 0
                countItem.setData(count + 1, CountRole)
                setBold(countItem)
#            self.counts[group].setData(countItem.data(QtCore.Qt.DisplayRole) + 1, QtCore.Qt.DisplayRole)
            if group in self.singleItems:
                parent = self.singleItems[group]
            elif group in self.groupItems:
                parent = self.groupItems[group]
            parent.appendRow(item)
            parentIndex = self.templateModel.indexFromItem(parent)
            self.templateView.setFirstColumnSpanned(0, parentIndex, True)
            self.templateView.expand(parentIndex.parent())
            self.templateView.expand(parentIndex)
#        self.templateView.expandAll()

        return QtWidgets.QDialog.exec_(self)



