from Qt import QtCore, QtGui, QtWidgets

from bigglesworth.utils import loadUi, getValidQColor
from bigglesworth.const import factoryPresets, factoryPresetsNamesDict, backgroundRole, foregroundRole, NameColumn, UidColumn
from bigglesworth.parameters import categories
from bigglesworth.library import NameProxy, TagsProxy, DockLibraryProxy, MultiCatProxy
from bigglesworth.dialogs.tags import TagValidator
from bigglesworth.dialogs.messageboxes import DeleteSoundsMessageBox


CollectionRole = QtCore.Qt.UserRole + 1
CatRole = CollectionRole + 1
FilterRole = CatRole + 1
PlusRole = QtCore.Qt.UserRole + 32
FilterCollection, FilterCategory, FilterTags, FilterText = range(4)

SelectOff = QtCore.Qt.ItemIsEnabled
SelectOn = SelectOff | QtCore.Qt.ItemIsSelectable

class UnselectableItem(QtGui.QStandardItem):
    def __init__(self, *args, **kwargs):
        QtGui.QStandardItem.__init__(self, *args, **kwargs)
        self.setFlags(SelectOff)


class MultiSelectItem(QtGui.QStandardItem):
    def __init__(self, *args, **kwargs):
        QtGui.QStandardItem.__init__(self, *args, **kwargs)
        self.setFlags(SelectOn)


class DockTreeView(QtWidgets.QTreeView):
    selectionUpdated = QtCore.pyqtSignal(object)
    clickTimer = QtCore.QElapsedTimer()
    clickTimer.start()
    factoryIndex = None
    startPos = QtCore.QPoint()

    def clearSelection(self):
        QtWidgets.QTreeView.clearSelection(self)
        self.selectionUpdated.emit([])

    def sizeHint(self):
        hint = QtWidgets.QTreeView.sizeHint(self)
        if self.factoryIndex:
            hint.setWidth(self.sizeHintForIndex(self.factoryIndex).width())
        return hint

    def mousePressEvent(self, event):
        self.startPos = event.pos()
        if event.buttons() == QtCore.Qt.LeftButton:
            index = self.indexAt(self.startPos)
            if self.clickTimer.elapsed() > QtWidgets.QApplication.instance().doubleClickInterval():
                if index.isValid() and self.startPos in self.visualRect(index):
                    if self.checkSelection(index, event.modifiers()):
                        self.selectionUpdated.emit(self.selectionModel().selectedRows())
                        self.clickTimer.start()
                        return
            elif index.isValid():
                self.doubleClicked.emit(index)
                return
        if event.buttons() == QtCore.Qt.LeftButton:
            QtWidgets.QTreeView.mousePressEvent(self, event)
            self.clickTimer.start()
            self.selectionUpdated.emit(self.selectionModel().selectedRows())

    def mouseMoveEvent(self, event):
        index = self.indexAt(self.startPos)
        if index.parent() in self.collectionIndexes and len(self.selectionModel().selectedRows()) == 1 and \
            (self.startPos - event.pos()).manhattanLength() > QtWidgets.QApplication.instance().startDragDistance():
                self.startDrag(index)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_F2:
            if self.edit(self.currentIndex(), self.AllEditTriggers, event):
                return
        QtWidgets.QTreeView.keyPressEvent(self, event)

    def startDrag(self, index):
        if index.column():
            index = index.sibling(index.row(), 0)
        mimeData = self.model().mimeData([index])
        if not mimeData:
            return
        byteArray = QtCore.QByteArray()
        stream = QtCore.QDataStream(byteArray, QtCore.QIODevice.WriteOnly)
        stream.writeQVariant(index.data(CollectionRole))
        mimeData.setData('bigglesworth/collectionObject', byteArray)

        iconSize = self.fontMetrics().height()
        rect = QtCore.QRect(0, 0, self.fontMetrics().width(index.data() + ' ' * 4), iconSize * 2)
        icon = index.data(QtCore.Qt.DecorationRole)
        if not icon.isNull():
            rect.setWidth(rect.width() + iconSize + 8)

        pixmap = QtGui.QPixmap(rect.size())
        pixmap.fill(QtCore.Qt.transparent)

        palette = self.palette()
        qp = QtGui.QPainter(pixmap)
        qp.setRenderHints(qp.Antialiasing)
        qp.translate(.5, .5)
        qp.setPen(palette.color(palette.Mid))
        qp.setBrush(palette.color(palette.Midlight))
        qp.drawRoundedRect(rect.adjusted(0, 0, -1, -1), 4, 4)

        if not icon.isNull():
            left = iconSize + 4
            iconPixmap = icon.pixmap(iconSize)
            if iconPixmap.width() != iconSize:
                iconPixmap = iconPixmap.scaledToWidth(iconSize, QtCore.Qt.SmoothTransformation)
            qp.drawPixmap(QtCore.QRect(4, rect.center().y() - iconSize / 2, iconSize, iconSize), iconPixmap, iconPixmap.rect())
        else:
            left = 0
        qp.setPen(palette.color(palette.WindowText))
        qp.drawText(rect.adjusted(left, 0, 0, 0), QtCore.Qt.AlignCenter, index.data())
        qp.end()
        del qp

        dragObject = QtGui.QDrag(self)
        dragObject.setPixmap(pixmap)
        dragObject.setMimeData(mimeData)
        dragObject.setHotSpot(QtCore.QPoint(-20, -20))
        dragObject.exec_(QtCore.Qt.CopyAction|QtCore.Qt.LinkAction, QtCore.Qt.CopyAction)

    def unselectCollection(self, collection):
        if collection in factoryPresets:
            res = self.model().match(self.factoryIndex.child(0, 0), CollectionRole, collection, hits=1, flags=QtCore.Qt.MatchExactly)
        else:
            res = self.model().match(self.userIndex.child(0, 0), CollectionRole, collection, hits=1, flags=QtCore.Qt.MatchExactly)
        if res:
            selection = QtCore.QItemSelection(res[0], res[0])
            self.selectionModel().select(selection, self.selectionModel().Deselect | self.selectionModel().Rows)

    def unselectCategory(self, category):
        catIndex = self.catIndexes[category]
        selection = QtCore.QItemSelection(catIndex, catIndex)
        self.selectionModel().select(selection, self.selectionModel().Deselect | self.selectionModel().Rows)

    def unselectTag(self, tag):
        res = self.model().match(self.tagsIndex.child(0, 0), QtCore.Qt.DisplayRole, tag, hits=1, flags=QtCore.Qt.MatchExactly)
        if res:
            selection = QtCore.QItemSelection(res[0], res[0])
            self.selectionModel().select(selection, self.selectionModel().Deselect | self.selectionModel().Rows)

    def rebuildStart(self):
        self.cachedSelection = self.selectionModel().selectedRows()

    def rebuildEnd(self, removedTags):
        indexes = []
        selection = QtCore.QItemSelection()
        for index in self.cachedSelection:
            index = self.model().index(index.row(), index.column(), index.parent())
            if index.parent() == self.tagsIndex and index.data() in removedTags:
                continue
            if not index.column() and index.isValid():
                indexes.append(index)
                selection.merge(QtCore.QItemSelection(index, index), QtCore.QItemSelectionModel.Select)
        self.selectionUpdated.emit(indexes)
        self.selectionModel().select(selection, QtCore.QItemSelectionModel.ClearAndSelect | QtCore.QItemSelectionModel.Rows)
        self.cachedSelection = []

    def deselectCollections(self):
        indexes = []
        for mainIndex in self.collectionIndexes:
            for row in range(self.model().rowCount(mainIndex)):
                index = mainIndex.child(row, 0)
                if index in self.selectionModel().selectedIndexes():
                    indexes.append(index)
        if indexes:
            selection = QtCore.QItemSelection(indexes[0], indexes[-1])
            self.selectionModel().select(selection, self.selectionModel().Deselect | self.selectionModel().Rows)

    def deselectFilterGroup(self, parent):
        indexes = []
        for row in range(self.model().rowCount(parent)):
            index = parent.child(row, 0)
            if index in self.selectionModel().selectedIndexes():
                indexes.append(index)
        if indexes:
            selection = QtCore.QItemSelection(indexes[0], indexes[-1])
            self.selectionModel().select(selection, QtCore.QItemSelectionModel.Deselect | QtCore.QItemSelectionModel.Rows)

    def checkSelection(self, index, modifiers):
        #This is an alternate selection behavior that allows to keep selection
        #of other parent items, unless the selection is a collection, so that
        #filters are updated in a more intuitive way
        item = self.model().itemFromIndex(index)
        if not isinstance(item, MultiSelectItem):
            if index.parent().isValid():
                if index.parent() in self.collectionIndexes:
                    self.deselectCollections()
                    indexes = []
                    for row in range(self.model().rowCount(index)):
                        indexes.append(index.child(row, 0))
                    selection = QtCore.QItemSelection(indexes[0], indexes[-1])
                    self.selectionModel().select(selection, QtCore.QItemSelectionModel.Select | QtCore.QItemSelectionModel.Rows)
                    self.selectionModel().setCurrentIndex(indexes[0], QtCore.QItemSelectionModel.NoUpdate)
                else:
                    self.deselectFilterGroup(index)
            return True
        else:
            if not modifiers:
                #toggle selected single item
                if index in self.selectionModel().selectedIndexes():
                    setCurrent = False
                    selection = QtCore.QItemSelection()
                else:
                    setCurrent = True
                    selection = QtCore.QItemSelection(index, index)
                #select only one collection, keep other filters
                if index.parent() in self.collectionIndexes:
                    self.deselectCollections()
                    for other in self.selectionModel().selectedRows():
                        if other in self.catIndexes or other.parent() == self.tagsIndex:
                            selection.merge(QtCore.QItemSelection(other, other), QtCore.QItemSelectionModel.Select)
                else:
                    #update filter only for parent (tag or cat), keep the other and the collection
                    if index in self.catIndexes:
                        otherParents = self.collectionIndexes + (self.tagsIndex, )
                    else:
                        otherParents = self.collectionIndexes + (self.catIndex, )
                    for other in self.selectionModel().selectedRows():
                        if other.parent() in otherParents:
                            selection.merge(QtCore.QItemSelection(other, other), QtCore.QItemSelectionModel.Select)
                self.selectionModel().select(selection, QtCore.QItemSelectionModel.ClearAndSelect | QtCore.QItemSelectionModel.Rows)
                if setCurrent:
                    self.selectionModel().setCurrentIndex(index, QtCore.QItemSelectionModel.NoUpdate)
            elif modifiers == QtCore.Qt.ControlModifier:
                selection = QtCore.QItemSelection(index, index)
                selectFlag = QtCore.QItemSelectionModel.Deselect if index in self.selectionModel().selectedIndexes() else QtCore.QItemSelectionModel.Select
                self.selectionModel().select(selection, selectFlag | QtCore.QItemSelectionModel.Rows)
                self.selectionModel().setCurrentIndex(index, QtCore.QItemSelectionModel.NoUpdate)
            elif modifiers == QtCore.Qt.ShiftModifier:
                return
        return True


class LibraryFilterList(QtWidgets.QListView):
    def setModel(self, model):
        QtWidgets.QListView.setModel(self, model)
        model.rowsInserted.connect(self.checkLayout)
        model.rowsRemoved.connect(self.checkLayout)
        self.checkLayout()

    def checkLayout(self):
        minHeight = self.sizeHintForRow(0)
        if minHeight <= 0:
            minHeight = self.fontMetrics().height() * 2
        if self.minimumHeight() <= 0:
            self.setMinimumHeight(minHeight)
        if self.model().rowCount():
            maxHeight = self.visualRect(self.model().index(self.model().rowCount() - 1, 0)).bottom()
        else:
            maxHeight = minHeight
        self.setMaximumHeight(maxHeight + (self.frameWidth() + self.lineWidth()) * 2)

    def resizeEvent(self, event):
        QtWidgets.QListView.resizeEvent(self, event)
        self.checkLayout()

    def paintEvent(self, event):
        if not self.model().rowCount():
            qp = QtGui.QPainter(self.viewport())
            qp.setPen(self.palette().color(QtGui.QPalette.Disabled, QtGui.QPalette.WindowText))
            font = self.font()
            font.setItalic(True)
            qp.setFont(font)
            qp.drawText(self.viewport().rect(), QtCore.Qt.AlignCenter, 'No filters selected')
        else:
            QtWidgets.QListView.paintEvent(self, event)


class PlusDelegate(QtWidgets.QStyledItemDelegate):
    plusClicked = QtCore.pyqtSignal(object)

    def __init__(self, *args, **kwargs):
        QtWidgets.QStyledItemDelegate.__init__(self, *args, **kwargs)
        self.plusIcon = QtGui.QIcon.fromTheme('emblem-added')
        self.tagsValidator = TagValidator()
        self.database = QtWidgets.QApplication.instance().database
        self.iconStates = {0: QtGui.QIcon.Disabled, int(QtWidgets.QStyle.State_MouseOver): QtGui.QIcon.Normal}

    def paint(self, qp, option, index):
        QtWidgets.QStyledItemDelegate.paint(self, qp, option, index)
        if index.data(PlusRole):
            #for some reason, using initStyleOption when the item is drawn causes issues with
            #decorations on _other_ items (?!?!?) of QTreeView, so we use a new option
            option = QtWidgets.QStyleOptionViewItemV4(option)
            self.initStyleOption(option, index)
            qp.setRenderHints(qp.Antialiasing)
            iconSize = option.fontMetrics.height()
            pixmap = self.plusIcon.pixmap(iconSize, mode=self.iconStates[int(option.state & QtWidgets.QStyle.State_MouseOver)]).scaledToHeight(iconSize, QtCore.Qt.SmoothTransformation)
            left = option.rect.right() - iconSize - 2
            top = option.rect.top() + (option.rect.height() - iconSize) / 2 - 1
            qp.drawPixmap(
                pixmap.rect().translated(left, top), 
                pixmap, pixmap.rect())

    def editorEvent(self, event, model, option, index):
        if event.type() == QtCore.QEvent.MouseButtonRelease and event.button() == QtCore.Qt.LeftButton and index.data(PlusRole):
            self.initStyleOption(option, index)
            if event.x() >= option.rect.right() - option.rect.height():
                self.plusClicked.emit(index)
                return True
        return QtWidgets.QStyledItemDelegate.editorEvent(self, event, model, option, index)

    def createEditor(self, parent, option, index):
        editor = QtWidgets.QStyledItemDelegate.createEditor(self, parent, option, index)
        editor.setValidator(self.tagsValidator)
        editor.textChanged.connect(self.setValid)
        return editor

    def setValid(self, text):
        valid, _, _ = self.tagsValidator.validate(text, 0)
        if valid == QtGui.QValidator.Intermediate:
            self.sender().setStyleSheet('color: red')
        else:
            self.sender().setStyleSheet('')

    def setModelData(self, editor, model, index):
        self.database.editTag(editor.text(), index.data(), index.data(QtCore.Qt.BackgroundRole), index.data(QtCore.Qt.ForegroundRole))
#        res = self.tagsModel.match(self.tagsModel.index(0, 0), QtCore.Qt.DisplayRole, index.data(), flags=QtCore.Qt.MatchExactly)
#        if res:
#            self.tagsModel.setData(res[0], editor.text())
#            self.tagsModel.submitAll()


class FilterDelegate(QtWidgets.QStyledItemDelegate):
    tagsModel = None
    removeRequested = QtCore.pyqtSignal(object)

    def sizeHint(self, option, index):
        self.initStyleOption(option, index)
        baseHeight = option.fontMetrics.height()
        width = option.fontMetrics.width(index.data()) + 16 + baseHeight
        if index.data(FilterRole) in (FilterCategory, FilterCollection):
            width += baseHeight
        return QtCore.QSize(width, baseHeight * 2)

    def setTagsModel(self, tagsModel):
        if self.tagsModel:
            self.tagsModel.dataChanged.disconnect()
        self.tagsModel = tagsModel
        self.tagsModel.dataChanged.connect(self.updateTags)
        self.updateTags()

    def updateTags(self, *args):
        self.tagColors = {}
        for row in range(self.tagsModel.rowCount()):
            tag = self.tagsModel.index(row, 0).data()
            bgColor = getValidQColor(self.tagsModel.index(row, 1).data(), backgroundRole)
            fgColor = getValidQColor(self.tagsModel.index(row, 2).data(), foregroundRole)
            self.tagColors[tag] = bgColor, fgColor

    def editorEvent(self, event, model, option, index):
        if event.type() == QtCore.QEvent.MouseButtonPress and event.buttons() == QtCore.Qt.LeftButton:
            self.initStyleOption(option, index)
            baseHeight = option.fontMetrics.height()
            if event.x() >= option.rect.right() - baseHeight:
                self.removeRequested.emit(index)
        return QtWidgets.QStyledItemDelegate.editorEvent(self, event, model, option, index)

    def paint(self, qp, option, index):
        self.initStyleOption(option, index)
        qp.setRenderHints(qp.Antialiasing)
        qp.save()
        qp.translate(.5, .5)
        iconSize = option.fontMetrics.height()
        rightMargin = iconSize + 4
        topMargin = (option.rect.height() - iconSize) * .5
        qp.save()
        qp.setPen(option.palette.color(option.palette.Mid))
        qp.setBrush(option.palette.color(option.palette.Midlight))
        qp.drawRoundedRect(option.rect.adjusted(1, 1, -1, -1), 4, 4)
        qp.drawRoundedRect(option.rect.adjusted(1, 1, -1 - rightMargin, -1), 4, 4)
        qp.restore()
        if index.data(FilterRole) in (FilterCategory, FilterCollection):
            icon = index.data(QtCore.Qt.DecorationRole)
            if not icon.isNull():
                pixmap = icon.pixmap(iconSize).scaledToHeight(iconSize, QtCore.Qt.SmoothTransformation)
                iconRect = pixmap.rect()
                qp.drawPixmap(iconRect.translated(2 + option.rect.left(), topMargin + option.rect.top()), pixmap, iconRect)
            qp.setPen(option.palette.color(option.palette.WindowText))
            qp.drawText(option.rect.adjusted(topMargin + iconSize, 2, -2 - topMargin, -2), QtCore.Qt.AlignVCenter|QtCore.Qt.AlignLeft, option.text)
        else:
            bgColor, fgColor = self.tagColors[index.data()]
            qp.setPen(fgColor)
            qp.setBrush(bgColor)
            rect = option.rect.adjusted(1, 1, -1 - rightMargin, -1)
            qp.drawRoundedRect(rect, 4, 4)
#            qp.setPen(option.palette.color(option.palette.WindowText))
            qp.drawText(rect, QtCore.Qt.AlignCenter, option.text)
        qp.translate(option.rect.right() - iconSize - 2, topMargin + option.rect.top())
        closePixmap = QtGui.QIcon.fromTheme('window-close').pixmap(iconSize)
        qp.drawPixmap(closePixmap.rect(), closePixmap, closePixmap.rect())
        qp.restore()


class DockLibrary(QtWidgets.QWidget):
    shown = False
    newCollection = QtCore.pyqtSignal()
    manageCollections = QtCore.pyqtSignal()
    cloneCollection = QtCore.pyqtSignal(str)
    openCollection = QtCore.pyqtSignal(object)
    editTag = QtCore.pyqtSignal(str)
    editTags = QtCore.pyqtSignal()
    deleteTag = QtCore.pyqtSignal(str)

    def __init__(self, *args, **kwargs):
        QtWidgets.QWidget.__init__(self, *args, **kwargs)
        loadUi('ui/docklibrary.ui', self)
        self.settings = QtCore.QSettings()

        self.filterModel = QtGui.QStandardItemModel()
        self.filterList.setModel(self.filterModel)
        self.filterDelegate = FilterDelegate()
        self.filterDelegate.removeRequested.connect(self.removeFilter)
        self.filterList.setItemDelegate(self.filterDelegate)

        self.treeModel = QtGui.QStandardItemModel(0, 2)
        self.treeView.setModel(self.treeModel)
        self.treeView.header().setResizeMode(0, QtWidgets.QHeaderView.Stretch)

        self.rootItem = UnselectableItem(QtGui.QIcon(':/images/bigglesworth_logo.svg'), 'All presets')
        self.rootCountItem = UnselectableItem()
        self.treeModel.appendRow([self.rootItem, self.rootCountItem])
        self.rootIndex = self.treeModel.indexFromItem(self.rootItem)

        self.factoryItem = UnselectableItem(QtGui.QIcon.fromTheme('folder'), 'Factory presets')
        self.rootItem.appendRow([self.factoryItem, UnselectableItem('3072')])
        self.factoryIndex = self.treeModel.indexFromItem(self.factoryItem)

        self.userItem = UnselectableItem(QtGui.QIcon.fromTheme('folder'), 'User collections')
        self.userItem.setData(True, PlusRole)
        self.userCountItem = UnselectableItem()
        self.rootItem.appendRow([self.userItem, self.userCountItem])
        self.userIndex = self.treeModel.indexFromItem(self.userItem)

        self.catItem = UnselectableItem(QtGui.QIcon.fromTheme('bookmarks'), 'Categories')
        self.catCountItem = UnselectableItem()
        self.rootItem.appendRow([self.catItem, self.catCountItem])
        self.catIndex = self.treeModel.indexFromItem(self.catItem)

        self.tagsItem = UnselectableItem(QtGui.QIcon.fromTheme('tag'), 'Tags')
        self.tagsItem.setData(True, PlusRole)
        self.tagsCountItem = UnselectableItem()
        self.rootItem.appendRow([self.tagsItem, self.tagsCountItem])
        self.tagsIndex = self.treeModel.indexFromItem(self.tagsItem)

        self.treeDelegate = PlusDelegate()
        self.treeView.setItemDelegate(self.treeDelegate)
        self.treeDelegate.plusClicked.connect(self.plusClicked)

#        self.collectionPlusDelegate = PlusDelegate()
#        self.collectionPlusDelegate.plusClicked.connect(self.newCollection)
#        self.treeView.setItemDelegateForRow(1, self.collectionPlusDelegate)

#        self.tagsPlusDelegate = PlusDelegate()
#        self.tagsPlusDelegate.plusClicked.connect(lambda: self.editTag.emit(''))
#        self.treeView.setItemDelegateForRow(3, self.tagsPlusDelegate)

        self.rootIndexes = self.factoryIndex, self.userIndex, self.catIndex, self.tagsIndex

        self.catCountItems = []
        self.catIndexes = []
        for c, cat in enumerate(categories):
            catItem = MultiSelectItem(QtGui.QIcon.fromTheme(cat.strip().lower()), cat)
            catItem.setData(c, CatRole)
            catCountItem = MultiSelectItem()
            self.catItem.appendRow([catItem, catCountItem])
            self.catCountItems.append(catCountItem)
            self.catIndexes.append(self.treeModel.indexFromItem(catItem))

        self.treeView.expand(self.rootIndex)
        self.treeView.doubleClicked.connect(self.doubleClicked)
        self.treeView.collectionIndexes = self.collectionIndexes = self.factoryIndex, self.userIndex
        self.treeView.factoryIndex = self.factoryIndex
        self.treeView.userIndex = self.userIndex
        self.treeView.catIndexes = self.catIndexes
        self.treeView.catIndex = self.catIndex
        self.treeView.tagsIndex = self.tagsIndex
        self.treeView.selectionUpdated.connect(self.updateFilters)
        self.treeView.customContextMenuRequested.connect(self.treeMenu)

        self.currentCollection = None
        self.libraryView.doubleClicked.disconnect()
        self.libraryView.deleteRequested.connect(self.deleteRequested)
#        self.libraryView.doubleClicked.connect(self.soundDoubleClicked)
        self.clearFiltersBtn.clicked.connect(self.treeView.clearSelection)

    def plusClicked(self, index):
        if index == self.userIndex:
            self.newCollection.emit()
        elif index == self.tagsIndex:
            self.editTag.emit('')

    def treeMenu(self, pos):
        index = self.treeView.indexAt(pos)
        if not index.isValid() or not index.parent().isValid():
            return
        menu = QtWidgets.QMenu()

        if index.parent() == self.tagsIndex:
            menu.setSeparatorsCollapsible(False)
            menu.addSection(index.data())
            newTagAction = menu.addAction(QtGui.QIcon.fromTheme('tag-new'), 'New tag...')
            newTagAction.triggered.connect(lambda: self.editTag.emit(''))
            renameTagAction = menu.addAction(QtGui.QIcon.fromTheme('document-edit-sign'), 'Rename tag')
            renameTagAction.triggered.connect(lambda: self.treeView.edit(index, self.treeView.AllEditTriggers, QtCore.QEvent(QtCore.QEvent.None_)))
            editTagAction = menu.addAction(QtGui.QIcon.fromTheme('document-edit'), 'Edit colors...')
            editTagAction.triggered.connect(lambda: self.editTag.emit(index.data()))
            removeTagAction = menu.addAction(QtGui.QIcon.fromTheme('edit-delete'), 'Delete tag')
            removeTagAction.triggered.connect(lambda: self.deleteTag.emit(index.data()))
            menu.addSeparator()
            editTagsAction = menu.addAction(QtGui.QIcon.fromTheme('tag'), 'Edit tags...')
            editTagsAction.triggered.connect(self.editTags)

        elif index == self.tagsIndex:
            newTagAction = menu.addAction(QtGui.QIcon.fromTheme('tag-new'), 'New tag...')
            newTagAction.triggered.connect(lambda: self.editTag.emit(''))
            editTagsAction = menu.addAction(QtGui.QIcon.fromTheme('tag'), 'Edit tags...')
            editTagsAction.triggered.connect(self.editTags)

        elif index.parent() == self.userIndex or index == self.userIndex:
            if index.parent() == self.userIndex:
                openCollectionAction = menu.addAction(QtGui.QIcon.fromTheme('edit-find'), 'Browse collection')
                openCollectionAction.triggered.connect(lambda: self.openCollection.emit(index.data(CollectionRole)))
            newCollectionAction = menu.addAction(QtGui.QIcon.fromTheme('document-new'), 'Create new collection')
            newCollectionAction.triggered.connect(self.newCollection)
            manageCollectionAction = menu.addAction(QtGui.QIcon.fromTheme('preferences-other'), 'Manage collections...')
            manageCollectionAction.triggered.connect(self.manageCollections)

        elif index.parent() == self.factoryIndex:
            openCollectionAction = menu.addAction(QtGui.QIcon.fromTheme('edit-find'), 'Browse collection')
            openCollectionAction.triggered.connect(lambda: self.openCollection.emit(index.data(CollectionRole)))

        menu.addSeparator()
        clearFiltersAction = menu.addAction(QtGui.QIcon.fromTheme('edit-clear-all-symbolic'), 'Clear filters')
        clearFiltersAction.triggered.connect(self.treeView.clearSelection)
        clearFiltersAction.setEnabled(self.filterModel.rowCount())
        menu.exec_(QtGui.QCursor.pos())

    def expandFactory(self):
        self.treeView.expand(self.factoryIndex)

    def expandCollections(self):
        self.treeView.expand(self.userIndex)

    def expandTags(self):
        self.treeView.expand(self.tagsIndex)

    def expandCategories(self):
        self.treeView.expand(self.catIndex)

    def firstRunExpand(self):
        self.expandFactory()
        self.expandCategories()

    def firstRunFilter(self):
        selection = QtCore.QItemSelection(self.factoryIndex.child(2, 0), self.factoryIndex.child(2, 1))
        selection.merge(QtCore.QItemSelection(self.catIndexes[4], self.catIndexes[4]), 
            QtCore.QItemSelectionModel.Select)
        self.treeView.selectionModel().select(selection, QtCore.QItemSelectionModel.SelectCurrent|QtCore.QItemSelectionModel.Rows)
        self.updateFilters(self.treeView.selectionModel().selectedRows())

    def soundDoubleClicked(self, index):
        self.window().soundEditRequested.emit(index.sibling(index.row(), UidColumn).data(), self.currentCollection)

    def deleteRequested(self, uidList):
        if DeleteSoundsMessageBox(self, uidList).exec_():
            self.database.deleteSounds(uidList)

    def doubleClicked(self, index):
        if index.parent().isValid() and self.treeModel.rowCount(index):
            if self.treeView.isExpanded(index):
                self.treeView.collapse(index)
            else:
                self.treeView.expand(index)

    @QtCore.pyqtSlot()
    def rebuild(self, init=False):
        #TODO: verificare meglio questa meccanica di aggiornamento
        if not init:
            self.libraryModel.query().exec_()
        self.treeView.rebuildStart()
        
        self.settings.beginGroup('CollectionIcons')

        self.treeModel.removeRows(0, self.treeModel.rowCount(self.userIndex), self.userIndex)
        totUser = 0
        totSounds = 0

        for collection in self.referenceModel.allCollections:
            count = self.database.getCountForCollection(collection)
            countItem = MultiSelectItem()
            countItem.setData(count, QtCore.Qt.DisplayRole)
            collectionItem = MultiSelectItem(factoryPresetsNamesDict.get(collection, collection))
            collectionItem.setData(collection, CollectionRole)
            if collection in factoryPresets:
                if self.treeModel.rowCount(self.factoryIndex) == len(factoryPresets):
                    continue
                parent = self.factoryItem
                icon = QtGui.QIcon.fromTheme('factory')
            else:
                parent = self.userItem
                if collection == 'Blofeld':
                    icon = QtGui.QIcon.fromTheme('bigglesworth')
                else:
                    icon = QtGui.QIcon.fromTheme(self.settings.value(collection, ''))
                totUser += count
            collectionItem.setIcon(icon)
            totSounds += count
            parent.appendRow([collectionItem, countItem])
        self.userCountItem.setData(totUser, QtCore.Qt.DisplayRole)
        self.rootCountItem.setData(totSounds, QtCore.Qt.DisplayRole)

        self.settings.endGroup()

        totCat = 0
        for cat, catItem in enumerate(self.catCountItems):
            count = self.database.getCountForCategory(cat)
            catItem.setData(count, QtCore.Qt.DisplayRole)
            totCat += count
        self.catCountItem.setData(totCat, QtCore.Qt.DisplayRole)

        totTags = 0
        self.treeModel.removeRows(0, self.treeModel.rowCount(self.tagsIndex), self.tagsIndex)
        tags = []
        for row in range(self.tagsModel.rowCount()):
            index = self.tagsModel.index(row, 0)
            tag = index.data()
            tags.append(tag)
            tagItem = MultiSelectItem(tag)
            tagItem.setEditable(True)
            tagItem.setData(getValidQColor(index.sibling(index.row(), 2).data(), foregroundRole), QtCore.Qt.ForegroundRole)
            tagItem.setData(getValidQColor(index.sibling(index.row(), 1).data(), backgroundRole), QtCore.Qt.BackgroundRole)
            tagCountItem = MultiSelectItem()
            count = self.database.getCountForTag(tag)
            tagCountItem.setData(count, QtCore.Qt.DisplayRole)
            self.tagsItem.appendRow([tagItem, tagCountItem])
            totTags += count
        self.tagsCountItem.setData(totTags, QtCore.Qt.DisplayRole)
        self.treeView.resizeColumnToContents(1)
        self.treeContainer.setMaximumWidth(self.checkWidth(self.treeView.minimumWidth()) + self.treeView.verticalScrollBar().sizeHint().width())

        removedTagsIndexes = []
        removedTags = []
        for row in range(self.filterModel.rowCount()):
            index = self.filterModel.index(row, 0)
            if index.data(FilterRole) == FilterTags and index.data() not in tags:
                removedTags.append(index.data())
                removedTagsIndexes.append(index)
        [self.removeFilter(i) for i in removedTagsIndexes]
        self.treeView.rebuildEnd(removedTags)

    def checkWidth(self, width, parent=None, level=0):
        if parent is None:
            parent = QtCore.QModelIndex()
        indentation = level * self.treeView.indentation()
        for row in range(self.treeModel.rowCount(parent)):
            colWidth = 0
            childWidth = 0
            for column in range(self.treeModel.columnCount(parent)):
                index = self.treeModel.index(row, column, parent)
                colWidth += self.treeView.sizeHintForIndex(index).width()
                if self.treeModel.rowCount(index):
                    childWidth = max(childWidth, self.checkWidth(width, index, level + 1)) 
            width = max(colWidth + indentation, childWidth, width)
        return width

        width = sum([self.treeView.sizeHintForColumn(c) for c in range(self.treeModel.columnCount())])
        self.treeView.setMaximumWidth(width + 4)

    def removeFilter(self, index):
        filter = index.data(FilterRole)
        if filter == FilterCollection:
            collection = index.data(CollectionRole)
            collectionBit = 1 << self.referenceModel.allCollections.index(collection)
            self.libraryProxy.setFilter(max(0, self.libraryProxy.filter - collectionBit))
            self.treeView.unselectCollection(collection)
        elif filter == FilterCategory:
            current = self.catProxy.filter[:]
            current.remove(index.data(CatRole))
            self.catProxy.setFilter(current)
            self.treeView.unselectCategory(index.data(CatRole))
        else:
            current = self.tagsProxy.filter[:]
            current.remove(index.data())
            self.tagsProxy.setFilter(current)
            self.treeView.unselectTag(index.data())
        self.filterModel.takeRow(index.row())
        self.clearFiltersBtn.setEnabled(self.filterModel.rowCount())

    def updateFilters(self, indexes):
        self.filterModel.clear()

        collections = []
        cats = []
        tags = []
        for index in indexes:
            if index.column():
                continue
            parent = index.parent()
            if parent in self.collectionIndexes:
                collections.append(index.data(CollectionRole))
            elif parent == self.catIndex:
                cats.append(index.data(CatRole))
            elif parent == self.tagsIndex:
                tags.append(index.data())

        collectionBit = 0
        for collection in collections:
            self.currentCollection = collection
            self.settings.beginGroup('CollectionIcons')
            icon = QtGui.QIcon.fromTheme(self.settings.value(collection, ''))
            if icon.isNull():
                if collection in factoryPresets:
                    icon = QtGui.QIcon(':/images/factory.svg')
                elif collection == 'Blofeld':
                    icon = QtGui.QIcon(':/images/bigglesworth_logo.svg')
                else:
                    icon = QtGui.QIcon.fromTheme('view-filter')
            filterItem = QtGui.QStandardItem(icon, factoryPresetsNamesDict.get(collection, collection))
            self.settings.endGroup()
            filterItem.setData(collection, CollectionRole)
            filterItem.setData(FilterCollection, FilterRole)
            self.filterModel.appendRow(filterItem)
            collectionBit += 1 << self.referenceModel.allCollections.index(collection)
        self.libraryProxy.setFilter(collectionBit)

        for cat in cats:
            filterItem = QtGui.QStandardItem(QtGui.QIcon.fromTheme('bookmarks'), categories[cat])
            filterItem.setData(FilterCategory, FilterRole)
            filterItem.setData(cat, CatRole)
            self.filterModel.appendRow(filterItem)

        for tag in tags:
            filterItem = QtGui.QStandardItem(QtGui.QIcon.fromTheme('tag'), tag)
            filterItem.setData(FilterTags, FilterRole)
            self.filterModel.appendRow(filterItem)

        self.catProxy.setFilter(cats)
        self.tagsProxy.setFilter(tags)
        self.clearFiltersBtn.setEnabled(self.filterModel.rowCount())

    def filtersInvalidated(self):
        if self.libraryView.currentIndex().isValid():
            #for some reason (event loop?), we need to fire this twice
            self.libraryView.scrollTo(self.libraryView.currentIndex(), self.libraryView.PositionAtCenter)
            self.libraryView.scrollTo(self.libraryView.currentIndex(), self.libraryView.PositionAtCenter)

    def showEvent(self, event):
        if not self.shown:
            self.shown = True
            self.database = QtWidgets.QApplication.instance().database
            self.referenceModel = self.database.referenceModel
            self.referenceModel.updated.connect(self.rebuild)
            self.tagsModel = self.database.tagsModel
            self.tagsModel.dataChanged.connect(self.rebuild)

            self.filterDelegate.setTagsModel(self.tagsModel)
            self.libraryModel = self.database.libraryModel
            self.libraryModel.updated.connect(self.rebuild)
            while self.libraryModel.canFetchMore():
                self.libraryModel.fetchMore()
            self.libraryModel.scheduledQueryUpdateSet.connect(self.scheduledQueryUpdateSet)
            self.updated = False

            self.libraryProxy = DockLibraryProxy()
            self.libraryProxy.setSourceModel(self.libraryModel)
            self.libraryProxy.invalidated.connect(self.filtersInvalidated)

            self.nameProxy = NameProxy()
            self.nameProxy.setSourceModel(self.libraryProxy)
            self.nameProxy.setFilterKeyColumn(NameColumn)
            self.nameProxy.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)
#            self.nameProxy.invalidated.connect(self.filtersInvalidated)

            self.catProxy = MultiCatProxy()
            self.catProxy.setSourceModel(self.nameProxy)
            self.catProxy.invalidated.connect(self.filtersInvalidated)

            self.tagsProxy = TagsProxy()
            self.tagsProxy.setSourceModel(self.catProxy)
            self.tagsProxy.invalidated.connect(self.filtersInvalidated)

            self.libraryView.setModel(self.tagsProxy)
            self.libraryView.setTagsModel(self.tagsModel)

            self.filterNameEdit.textChanged.connect(self.nameProxy.setFilterWildcard)

            self.rebuild(True)

        elif not self.updated:
            self.libraryModel.queryUpdate()
            self.updated = True

    def scheduledQueryUpdateSet(self):
        if self.isVisible():
            self.libraryModel.queryUpdate()
            self.updated = True
        else:
            self.updated = False


