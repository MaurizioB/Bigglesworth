# *-* encoding: utf-8 *-*

import sys
import json
from string import uppercase
from unidecode import unidecode as _unidecode

from Qt import QtCore, QtGui, QtWidgets

from bigglesworth.parameters import categories
from bigglesworth.widgets import NameEdit, ContextMenu, CategoryDelegate, TagsDelegate
from bigglesworth.utils import loadUi, getSysExContents, sanitize, getValidQColor, getQtFlags
from bigglesworth.const import (TagsRole, backgroundRole, foregroundRole, UidColumn, LocationColumn, 
    NameColumn, CatColumn, TagsColumn, FactoryColumn, chr2ord, factoryPresets)
from bigglesworth.library import CleanLibraryProxy, BankProxy, CatProxy, NameProxy, TagsProxy, MainLibraryProxy
from bigglesworth.dialogs import (SoundTagsEditDialog, MultiSoundTagsEditDialog, RemoveSoundsMessageBox, 
    DeleteSoundsMessageBox, DropDuplicatesMessageBox, InitEmptySlotsDialog)
from bigglesworth.dialogs.tags import TagEdit
from bigglesworth.libs import midifile

def unidecode(text):
    output = ''
    for l in text:
        if l == u'°':
            output += l
        else:
            output += _unidecode(l)
    return output

validChars = set(' !#$%&()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~')


class NameDelegate(QtWidgets.QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        lineEdit = NameEdit(parent)
        lineEdit.setText(index.data())
#        self.updateEditorGeometry(lineEdit, option, index)
        return lineEdit


class TagsCheckBox(QtWidgets.QCheckBox):
    def __init__(self, tag, bgd=QtGui.QColor(QtCore.Qt.darkGray), fgd=QtGui.QColor(QtCore.Qt.white), state=QtCore.Qt.Unchecked):
        QtWidgets.QCheckBox.__init__(self, tag)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed))
        self.brush = bgd
        self.pen = QtGui.QPen(fgd, 1)
        self.edited = False
        self.state = state
        if state == QtCore.Qt.Checked:
            self.setChecked(True)
        self.clicked.connect(self.setEdited)

    def mousePressEvent(self, event):
        #workaround to set entire area as clickable, as QCheckBox only maps the label width
        if event.button() == QtCore.Qt.LeftButton:
            self.pen.setWidth(2)
            self.setDown(True)

    def mouseMoveEvent(self, event):
        if event.buttons() == QtCore.Qt.LeftButton:
            if event.pos() in self.rect():
                self.pen.setWidth(2)
                self.setDown(True)
            else:
                self.pen.setWidth(1)
                self.setDown(False)

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton and event.pos() in self.rect():
            self.pen.setWidth(1)
            self.click()
            self.setDown(False)

    def setEdited(self):
        self.edited = True
        self.update()

    def paintEvent(self, event):
        option = QtWidgets.QStyleOptionButton()
        self.initStyleOption(option)
        qp = QtWidgets.QStylePainter(self)
        qp.setRenderHints(qp.Antialiasing)
        labelRect = self.style().subElementRect(QtWidgets.QStyle.SE_CheckBoxContents, option, self)
        checkRect = self.style().subElementRect(QtWidgets.QStyle.SE_CheckBoxIndicator, option, self)
        option.rect = checkRect
#        print(int(option.state), getQtFlags(option.state, QtWidgets.QStyle.State, QtWidgets.QStyle))
        if not self.edited and self.state == QtCore.Qt.PartiallyChecked:
            option.state |= QtWidgets.QStyle.State_NoChange | QtWidgets.QStyle.State_On
        qp.drawPrimitive(QtWidgets.QStyle.PE_FrameFocusRect, option)
        qp.drawPrimitive(QtWidgets.QStyle.PE_IndicatorCheckBox, option)
        qp.setBrush(self.brush)
        qp.setPen(self.pen)
        qp.drawRoundedRect(labelRect, 4, 4)
        qp.drawText(labelRect, QtCore.Qt.AlignCenter, self.text())


class TagsMiniWidget(QtWidgets.QWidget):
    def __init__(self, uidList, widgetAction):
        QtWidgets.QWidget.__init__(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum)
        self.setSizePolicy(sizePolicy)
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        layout.setSpacing(1)
        self.widgetAction = widgetAction

        self.database = QtWidgets.QApplication.instance().database
        self.tagsModel = self.database.tagsModel
        self.uidList = uidList

        currentTags = self.database.getTagsForUidList(uidList)
        inverted = {}
        for uid, tags in currentTags.items():
            for tag in tags:
                if not tag in inverted:
                    inverted[tag] = [uid]
                else:
                    inverted[tag].append(uid)

        self.checkboxes = []
        for row in range(self.tagsModel.rowCount()):
            tag = self.tagsModel.index(row, 0).data()
            bgd = getValidQColor(self.tagsModel.index(row, 1).data(), backgroundRole)
            fgd = getValidQColor(self.tagsModel.index(row, 2).data(), foregroundRole)
            if tag in inverted:
                if len(inverted[tag]) == len(uidList):
                    state = QtCore.Qt.Checked
                else:
                    state = QtCore.Qt.PartiallyChecked
            else:
                state = QtCore.Qt.Unchecked
            check = TagsCheckBox(tag, bgd, fgd, state)
            layout.addWidget(check)
            check.toggled.connect(self.activated)
            self.checkboxes.append(check)

        self.addTagEdit = TagEdit(notifyLostFocus=True)
        layout.addWidget(self.addTagEdit)
#        self.addTagEdit.setVisible(False)
        self.addTagEdit.ignored.connect(self.hideAddTag)
        self.addTagEdit.accepted.connect(self.addTag)

        self.newBtn = QtWidgets.QPushButton(QtGui.QIcon.fromTheme('document-new'), 'New tag')
        self.newBtn.setFlat(True)
        self.newBtn.setVisible(False)
        layout.addWidget(self.newBtn)
        self.newBtn.clicked.connect(self.showAddTag)
        self.newBtn.setSizePolicy(sizePolicy)

        self.applyBtn = QtWidgets.QPushButton(QtGui.QIcon.fromTheme('dialog-ok-apply'), 'Apply')
        self.applyBtn.setEnabled(False)
        layout.addWidget(self.applyBtn)
        self.applyBtn.clicked.connect(self.apply)
#        self.applyBtn.setSizePolicy(sizePolicy)
        self.applyBtn.setFixedHeight(self.applyBtn.sizeHint().height())
        self.canApply = False

    def addTag(self, tag):
        row = self.tagsModel.rowCount()
        self.tagsModel.insertRows(row, 1)
        self.tagsModel.setData(self.tagsModel.index(row, 0), tag)
        self.tagsModel.submitAll()

        self.setMinimumWidth(self.width())
        oldWidth = self.width()
        menu = self.parent()
        menuSize = menu.size()
        check = TagsCheckBox(tag)
        check.setChecked(True)
        self.setMinimumHeight(self.height() + check.minimumSizeHint().height() + self.layout().spacing())
        self.setMinimumWidth(max(oldWidth, check.minimumSizeHint().width() + 10))
        self.hideAddTag()
        self.layout().insertWidget(self.layout().indexOf(self.addTagEdit), check)
        check.toggled.connect(self.activated)
        self.checkboxes.append(check)
        menuSize.setHeight(menuSize.height() + check.minimumSizeHint().height() + self.layout().spacing())
        menuSize.setWidth(menuSize.width() + self.width() - oldWidth)
        menu.resize(menuSize)

        desktop = QtWidgets.QApplication.desktop().availableGeometry(menu)
        x = menu.pos().x()
        y = menu.pos().y()
        if y + menuSize.height() > desktop.bottom():
            y = desktop.bottom() - menuSize.height()
        if x + menuSize.width() > desktop.right():
            x = desktop.right() - menuSize.width()
        menu.move(x, y)

        self.activated()

    def showAddTag(self):
        self.applyBtn.setEnabled(False)
        self.addTagEdit.setVisible(True)
        self.addTagEdit.setFocus()
        self.newBtn.setVisible(False)
        self.adjustSize()

    def hideAddTag(self):
        self.addTagEdit.setVisible(False)
        self.addTagEdit.setText('')
        self.applyBtn.setEnabled(self.canApply)
        self.newBtn.setVisible(True)

    def activated(self):
        self.canApply = True
        self.applyBtn.setEnabled(True)
        [check.setEdited() for check in self.checkboxes]

    def apply(self):
#        self.widgetAction.activate(self.widgetAction.Trigger)
        self.database.setTagsForUidList(self.uidList, [c.text() for c in self.checkboxes if c.isChecked()])
        parent = self.widgetAction.parent()
        while isinstance(parent.parent(), QtWidgets.QMenu):
            parent = parent.parent()
        parent.close()

    def mousePressEvent(self, event):
        event.accept()

    def showEvent(self, event):
        self.hideAddTag()


class BaseLibraryView(QtWidgets.QTableView):
    dropIntoPen = QtCore.Qt.blue
    dropIntoBrush = QtGui.QBrush(QtGui.QColor(32, 128, 255, 96))
    tagsModel = None

    tagEditRequested = QtCore.pyqtSignal(object)
    tagEditMultiRequested = QtCore.pyqtSignal(object)
    duplicateRequested = QtCore.pyqtSignal(str, int)
    findDuplicatesRequested = QtCore.pyqtSignal(str, object)
    importRequested = QtCore.pyqtSignal(object)
    exportRequested = QtCore.pyqtSignal(object, object)
    deleteRequested = QtCore.pyqtSignal(object)
    #blofeld index/buffer, collection, index, multi
    dumpFromRequested = QtCore.pyqtSignal(object, object, int, bool)
    #uid, blofeld index/buffer, multi
    dumpToRequested = QtCore.pyqtSignal(object, object, bool)
    fullDumpCollectionToBlofeldRequested = QtCore.pyqtSignal(str, object)
    fullDumpBlofeldToCollectionRequested = QtCore.pyqtSignal(str, object)
    dropEventSignal = QtCore.pyqtSignal()

    def __init__(self, *args, **kwargs):
        QtWidgets.QTableView.__init__(self, *args, **kwargs)
        self.database = QtWidgets.QApplication.instance().database
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.horizontalHeader().customContextMenuRequested.connect(self.sortMenu)
        #TODO: think about disabling sort by click (then uncomment highlightHeader in sortByColumn)
        self.horizontalHeader().sectionClicked.connect(self.sortByColumn)
        self.horizontalHeader().sortIndicatorChanged.connect(self.highlightHeader)

        self.setMouseTracking(True)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showMenu)

        self.setSelectionBehavior(self.SelectRows)
        self.setSelectionMode(self.ContiguousSelection)
        self.setDragDropMode(self.DragDrop)
        self.setDragDropOverwriteMode(True)

        nameDelegate = NameDelegate(self)
        self.setItemDelegateForColumn(NameColumn, nameDelegate)

        catDelegate = CategoryDelegate(self)
        self.setItemDelegateForColumn(CatColumn, catDelegate)

        self.tagsDelegate = TagsDelegate(self)
        self.setItemDelegateForColumn(TagsColumn, self.tagsDelegate)

        self.dropSelectionIndexes = None
        self.editable = True

        self.searchString = ''
        self.searchTimer = QtCore.QTimer()
        self.searchTimer.setSingleShot(True)
        self.searchTimer.setInterval(1000)
        self.searchTimer.timeout.connect(self.setSearch)
        self.externalFileDropContents = None

        self.doubleClicked.connect(self.soundDoubleClicked)
        self.cornerButton = None

    def selectIndexes(self, uidList):
        selection = QtCore.QItemSelection()
        model = self.model()
        indexes = []
        for uid in uidList:
            res = model.match(model.index(0, UidColumn), QtCore.Qt.DisplayRole, uid, flags=QtCore.Qt.MatchExactly)
            if not res:
                print('uid not found?!', uid)
                continue
            index = res[0]
            indexes.append(index)
            selection.select(index, index.sibling(index.row(), model.columnCount() - 1))
#        model = self.model()
#        for row in self.database.getIndexesFromUidList(uidList, self.collection):
#            index = model.index(row, NameColumn)
#            selection.select(index, index)
        self.selectionModel().select(selection, QtCore.QItemSelectionModel.ClearAndSelect)
        self.scrollTo(indexes[0])

    def sortMenu(self, *args):
#        if isinstance(args, QtCore.QPoint):
#            pos = args
#        elif isinstance(args, QtCore.QEvent):
#            pos = args.pos()
        menu = QtWidgets.QMenu()
        sortDefaultAction = menu.addAction(QtGui.QIcon.fromTheme('database-index'), 
            'Sort by index' if isinstance(self, CollectionTableView) else 'Restore default order')
        sortDefaultAction.setData((-1, ))
        menu.addSeparator()
        alphaMenu = menu.addMenu(QtGui.QIcon.fromTheme('view-sort-ascending'), 'Alphabetically')
        sortNameAscAction = alphaMenu.addAction(QtGui.QIcon.fromTheme('arrow-down-double'), 'Ascending')
        sortNameAscAction.setData((NameColumn, ))
        sortNameDescAction = alphaMenu.addAction(QtGui.QIcon.fromTheme('arrow-up-double'), 'Descending')
        sortNameDescAction.setData((NameColumn, QtCore.Qt.DescendingOrder))
        catMenu = menu.addMenu(QtGui.QIcon.fromTheme('bookmarks'), 'By category')
        sortCatAscAction = catMenu.addAction(QtGui.QIcon.fromTheme('arrow-down-double'), 'Ascending')
        sortCatAscAction.setData((CatColumn, ))
        sortCatDescAction = catMenu.addAction(QtGui.QIcon.fromTheme('arrow-up-double'), 'Descending')
        sortCatDescAction.setData((CatColumn, QtCore.Qt.DescendingOrder))
        tagMenu = menu.addMenu(QtGui.QIcon.fromTheme('tag'), 'By tag')
        sortTagAscAction = tagMenu.addAction(QtGui.QIcon.fromTheme('arrow-down-double'), 'Ascending')
        sortTagAscAction.setData((TagsColumn, ))
        sortTagDescAction = tagMenu.addAction(QtGui.QIcon.fromTheme('arrow-up-double'), 'Descending')
        sortTagDescAction.setData((TagsColumn, QtCore.Qt.DescendingOrder))

        if self.model().size() <= 0:
            [a.setEnabled(False) for a in menu.actions()]
        res = menu.exec_(QtGui.QCursor.pos())
        if res and res.data():
            self.sortByColumn(*res.data())

    def sortByColumn(self, column, order=QtCore.Qt.AscendingOrder):
        if self.model().size() <= 0:
            return
        header = self.horizontalHeader()
        if column <= 0:
            if self.model().sortRole() == QtCore.Qt.InitialSortOrderRole:
                return
            self.model().setSortRole(QtCore.Qt.InitialSortOrderRole)
            self.model().invalidate()
            header.setSortIndicatorShown(False)
            header.setSortIndicator(-1, order)
#            self.highlightHeader(-1, order)
            return
        if self.sender() == self.horizontalHeader():
            if not header.isSortIndicatorShown() or self.model().sortColumn() != column:
                order = QtCore.Qt.AscendingOrder
            elif self.model().sortOrder() == QtCore.Qt.AscendingOrder:
                order = QtCore.Qt.DescendingOrder
            else:
                self.model().setSortRole(QtCore.Qt.InitialSortOrderRole)
                self.model().invalidate()
                header.setSortIndicatorShown(False)
                header.setSortIndicator(-1, order)
#                self.highlightHeader(-1, order)
                return
        self.model().setSortRole(QtCore.Qt.DisplayRole)
        header.setSortIndicatorShown(True)
        QtWidgets.QTableView.sortByColumn(self, column, order)
#        self.highlightHeader(column, order)

    def highlightHeader(self, index, order):
        if self.model().size() <= 0:
            return
        normalFont = self.font()
        highlightFont = self.font()
        highlightFont.setBold(True)
        if self.cornerButton:
            self.cornerButton.setFont(highlightFont if index < 0 else normalFont)
        model = self.model()
        for section in range(model.columnCount()):
            if self.isColumnHidden(section):
                continue
            model.setHeaderData(section, QtCore.Qt.Horizontal, 
                highlightFont if section == index else normalFont, QtCore.Qt.FontRole)

    def soundDoubleClicked(self, index):
        if self.parent().editModeBtn.isChecked():
            return
        self.window().soundEditRequested.emit(index.sibling(index.row(), UidColumn).data(), self.collection)

    def showStatusBarMessage(self, message):
        self.window().statusBar().showMessage(message)

    def clearStatusBar(self):
        self.window().statusBar().clearMessage()

    def getDropContents(self, filePath):
        try:
#            print(QtCore.QUrl(midiFile).toLocalFile())
            track = midifile.read_midifile(QtCore.QUrl(filePath).toLocalFile())[0]
            sysex = []
            for event in track:
                if isinstance(event, midifile.SysexEvent):
                    sysex.append(event.data)
            print(sysex[0])
            
        except Exception as e:
            print(e)
        return True

    def getDragRows(self, event):
        stream = QtCore.QDataStream(event.mimeData().data('application/x-qabstractitemmodeldatalist'))
        rows = set()
        while not stream.atEnd():
            rows.add(stream.readInt32())
            #column
            stream.readInt32()
            #read item role data
            [(stream.readInt32(), stream.readQVariant()) for role in range(stream.readInt32())]
        return sorted(rows)

    def moveCursor(self, action, modifiers):
        if action in (self.MoveNext, self.MoveRight):
            index = self.currentIndex()
            if not index.isValid():
                return self.model().index(0, 0)
            row = index.row() + 1
            nextIndex = index.sibling(row, NameColumn)
            if isinstance(self, CollectionTableView):
                rowCount = self.model().rowCount()
                while not nextIndex.flags() & QtCore.Qt.ItemIsEnabled:
                    row += 1
                    if row == rowCount:
                        break
                    nextIndex = nextIndex.sibling(row, NameColumn)
                self.scrollTo(nextIndex)
            return nextIndex
        elif action in (self.MovePrevious, self.MoveLeft):
            index = self.currentIndex()
            if not index.isValid():
                return self.model().index(0, 0)
            row = index.row() - 1
            prevIndex = index.sibling(row, NameColumn)
            if isinstance(self, CollectionTableView):
                while not prevIndex.flags() & QtCore.Qt.ItemIsEnabled:
                    row -= 1
                    if row < 0:
                        break
                    prevIndex = prevIndex.sibling(row, NameColumn)
                self.scrollTo(prevIndex)
            return prevIndex
        return QtWidgets.QTableView.moveCursor(self, action, modifiers)

    def mouseDoubleClickEvent(self, event):
        index = self.indexAt(event.pos())
        if not index.isValid() or index.flags() & QtCore.Qt.ItemIsEnabled:
            return QtWidgets.QTableView.mouseDoubleClickEvent(self, event)
        soundIndex = index.row()
        bank = soundIndex >> 7
        prog = soundIndex & 127
        if QtWidgets.QMessageBox.question(self, 'Empty sound slot', 
            'Do you want to <b>INIT</b> and open the sound at index {}{:03}?'.format(uppercase[bank], prog + 1), 
            QtWidgets.QMessageBox.Ok|QtWidgets.QMessageBox.Cancel) != QtWidgets.QMessageBox.Ok:
                return
        self.database.initSound(soundIndex, self.collection)
        self.window().soundEditRequested.emit(self.database.getUidFromCollection(bank, prog, self.collection), self.collection)
        self.setCurrentIndex(index.sibling(index.row(), NameColumn))

    def dragEnterEvent(self, event):
        self.dropSelectionIndexes = None
        if not self.editable:
            event.ignore()
        elif event.mimeData().hasFormat('text/uri-list'):
            data = event.mimeData().data('text/uri-list')
            urilist = unicode(data).replace('\r', '').strip().split('\n')
#            if len(urilist) != 1 or urilist[0][-4:] not in ('.syx', '.mid'):
            if urilist[0][-4:] not in ('.syx', '.mid'):
                event.ignore()
                return
            sysex = getSysExContents(urilist[0])
            if sysex:
                event.accept()
                self.externalFileDropContents = sysex
            else:
                event.ignore()
        elif event.mimeData().hasFormat('application/x-qabstractitemmodeldatalist') and \
            event.source() and event.mimeData().hasFormat('bigglesworth/collectionItems'):
                QtWidgets.QTableView.dragEnterEvent(self, event)
        else:
            event.ignore()

    def startDrag(self, actions):
        if not self.model().flags(self.indexAt(self.viewport().mapFromGlobal(QtGui.QCursor.pos()))) & QtCore.Qt.ItemIsEnabled:
            return
        items = [index for index in self.selectionModel().selectedRows(NameColumn) if index.flags() & QtCore.Qt.ItemIsDragEnabled]
        if not items:
            return
        mimeData = self.model().mimeData(items)
        if not mimeData:
            return
        byteArray = QtCore.QByteArray()
        stream = QtCore.QDataStream(byteArray, QtCore.QIODevice.WriteOnly)
        for uid in self.getUidFromIndexList(items):
            stream.writeQVariant(uid)
        mimeData.setData('bigglesworth/collectionItems', byteArray)
        byteArray.clear()
        stream = QtCore.QDataStream(byteArray, QtCore.QIODevice.WriteOnly)
        stream.writeBool(False)
        mimeData.setData('bigglesworth/collectionDragMode', byteArray)

        itemWidth = self.horizontalHeader().sectionSize(NameColumn)
        itemHeight = self.verticalHeader().sectionSize(0)
        pixmap = QtGui.QPixmap(itemWidth, itemHeight * len(items[:10 if len(items) <= 10 else 11]))
        pixmap.fill(QtCore.Qt.transparent)
        qp = QtGui.QPainter(pixmap)
        option = QtWidgets.QStyleOptionViewItem()
        option.state |= QtWidgets.QStyle.State_Selected|QtWidgets.QStyle.State_Enabled
        option.rect = QtCore.QRect(0, 0, itemWidth, itemHeight)
        option.displayAlignment = QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter
        for item in items[:10]:
            QtWidgets.QStyledItemDelegate(self).paint(qp, option, item)
            option.rect.translate(0, itemHeight)
        if len(items) > 10:
            qp.setPen(QtCore.Qt.NoPen)
            qp.setBrush(QtCore.Qt.white)
            qp.drawRect(option.rect)
            qp.setPen(QtCore.Qt.black)
            qp.drawText(option.rect.adjusted(4, 0, 0, 0), option.displayAlignment, 'and {} more...'.format(len(items) - 10))
        del qp
        drag = QtGui.QDrag(self)
        drag.setPixmap(pixmap)
        drag.setMimeData(mimeData)
        drag.setHotSpot(QtCore.QPoint(-20, -20))
        drag.exec_(QtCore.Qt.MoveAction|QtCore.Qt.CopyAction|QtCore.Qt.LinkAction, QtCore.Qt.CopyAction)

    def dropEvent(self, event):
        self.window().statusBar().clearMessage()
        self.externalFileDropContents = None
        self.dropSelectionIndexes = None

    def dragLeaveEvent(self, event):
        QtWidgets.QTableView.dragLeaveEvent(self, event)
        self.window().statusBar().clearMessage()
        self.dropSelectionIndexes = None

    def getUidFromIndex(self, index):
        return self.model().data(index.sibling(index.row(), UidColumn))

    def getUidFromIndexList(self, indexList):
        return [self.getUidFromIndex(index) for index in indexList]

    def getUidFromRow(self, row):
        return self.model().data(self.model().index(row, UidColumn))

    def getUidFromRowList(self, rowList):
        return [self.getUidFromRow(row) for row in rowList]

    def setTagsModel(self, tagsModel):
        if self.tagsModel:
            self.tagsModel.dataChanged.disconnect(self.viewport().update)
        self.tagsModel = tagsModel
        self.tagsDelegate.setTagsModel(tagsModel)
        self.tagsModel.dataChanged.connect(self.viewport().update)

    def keyPressEvent(self, event):
        if event.text() in chr2ord:
            self.setSearch(event.text())
            return
        elif event.matches(QtGui.QKeySequence.Delete) and self.selectionModel().hasSelection() and self.editable:
            uidList = [index.data() for index in self.selectionModel().selectedRows()]
            if isinstance(self, LibraryTableView):
                uidList = [uid for uid in uidList if self.database.isUidWritable(uid)]
            if uidList:
                self.deleteRequested.emit(uidList)
#        elif self.verticalScrollBar().isVisible():
        elif self.verticalScrollBar().maximum():
            #fixes for various scroll functions when items are not valid
            #some of these have to be moved to moveCursor, maybe?
            if event.key() in (QtCore.Qt.Key_Up, QtCore.Qt.Key_Down):
                if event.modifiers() == QtCore.Qt.ControlModifier:
                    delta = 1 if event.key() == QtCore.Qt.Key_Down else -1
                    self.verticalScrollBar().setValue(self.verticalScrollBar().value() + delta)
                else:
                    QtWidgets.QTableView.keyPressEvent(self, event)
                    self.scrollTo(self.currentIndex())
                return
            elif event.modifiers() == QtCore.Qt.ControlModifier and event.key() in (QtCore.Qt.Key_PageUp, QtCore.Qt.Key_PageDown):
                sign = 1 if event.key() == QtCore.Qt.Key_PageDown else -1
                self.verticalScrollBar().setValue(self.verticalScrollBar().value() + self.verticalScrollBar().pageStep() * sign)
                return
            elif event.modifiers() == QtCore.Qt.ControlModifier and event.key() in (QtCore.Qt.Key_Home, QtCore.Qt.Key_End):
                if event.key() == QtCore.Qt.Key_Home:
                    self.scrollToTop()
                else:
                    self.scrollToBottom()
                return
            elif event.modifiers() == QtCore.Qt.ControlModifier|QtCore.Qt.ShiftModifier and event.key() == QtCore.Qt.Key_Home:
                self.scrollTo(self.currentIndex())
                return
            elif event.matches(QtGui.QKeySequence.MoveToNextPage) or event.matches(QtGui.QKeySequence.SelectNextPage):
                updateSelection = event.matches(QtGui.QKeySequence.SelectNextPage)
                pre = self.verticalScrollBar().value()
                QtWidgets.QTableView.keyPressEvent(self, event)
                post = self.verticalScrollBar().value()
                if pre != post:
                    return
                if not self.currentIndex().isValid():
                    nextIndex = self.model().index(0, 2)
                else:
                    startRow = self.rowAt(0)
                    endRow = self.rowAt(self.viewport().height())
                    if endRow < 0:
                        endRow = self.model().rowCount() - 1
                    pageSize = endRow - startRow - 1
                    nextRow = min(self.model().rowCount() - 1, self.currentIndex().row() + pageSize)
                    nextIndex = self.model().index(nextRow, 2)
                while nextIndex.row() < self.model().rowCount() - 1:
                    nextIndex = self.model().index(nextIndex.row() + 1, 2)
                    if nextIndex.flags() & QtCore.Qt.ItemIsEnabled:
                        if updateSelection and self.currentIndex().isValid():
                            selection = QtCore.QItemSelection(self.selectionModel().selectedRows()[0], nextIndex)
                            self.selectionModel().select(selection, QtCore.QItemSelectionModel.Rows|QtCore.QItemSelectionModel.ClearAndSelect)
                            self.selectionModel().setCurrentIndex(nextIndex, QtCore.QItemSelectionModel.NoUpdate)
                        else:
                            self.setCurrentIndex(nextIndex)
                        self.scrollTo(nextIndex)
                        self.scrollTo(nextIndex)
                        return
                else:
                    lastIndex = self.model().index(self.model().rowCount() - 1, 2)
                    while not lastIndex.flags() & QtCore.Qt.ItemIsEnabled:
                        lastIndex = self.model().index(lastIndex.row() - 1, 2)
                    if updateSelection and self.currentIndex().isValid():
                        selection = QtCore.QItemSelection(self.selectionModel().selectedRows()[0], lastIndex)
                        self.selectionModel().select(selection, QtCore.QItemSelectionModel.Rows|QtCore.QItemSelectionModel.ClearAndSelect)
                        self.selectionModel().setCurrentIndex(lastIndex, QtCore.QItemSelectionModel.NoUpdate)
                    else:
                        self.setCurrentIndex(lastIndex)
                    self.scrollTo(lastIndex)
                    return
            elif event.matches(QtGui.QKeySequence.MoveToPreviousPage) or event.matches(QtGui.QKeySequence.SelectPreviousPage):
                updateSelection = event.matches(QtGui.QKeySequence.SelectPreviousPage)
#                pre = self.verticalScrollBar().value()
#                QtWidgets.QTableView.keyPressEvent(self, event)
#                post = self.verticalScrollBar().value()
#                if pre != post:
#                    return
                if not self.currentIndex().isValid():
                    nextIndex = self.model().index(self.model().rowCount() - 1, 2)
                else:
                    startRow = self.rowAt(0)
                    endRow = self.rowAt(self.viewport().height())
                    if endRow < 0:
                        endRow = self.model().rowCount() - 1
                    pageSize = endRow - startRow - 1
                    nextIndex = self.model().index(self.currentIndex().row() - pageSize, 2)
                while nextIndex.row() > 0:
                    nextIndex = self.model().index(nextIndex.row() - 1, 2)
                    if nextIndex.flags() & QtCore.Qt.ItemIsEnabled:
                        if updateSelection and self.currentIndex().isValid():
                            selection = QtCore.QItemSelection(self.selectionModel().selectedRows()[0], nextIndex)
                            self.selectionModel().select(selection, QtCore.QItemSelectionModel.Rows|QtCore.QItemSelectionModel.ClearAndSelect)
                            self.selectionModel().setCurrentIndex(nextIndex, QtCore.QItemSelectionModel.NoUpdate)
                        else:
                            self.setCurrentIndex(nextIndex)
                        self.scrollTo(nextIndex)
                        return
                else:
                    firstIndex = self.model().index(0, 2)
                    while not firstIndex.flags() & QtCore.Qt.ItemIsEnabled:
                        firstIndex = self.model().index(firstIndex.row() + 1, 2)
                    if updateSelection and self.currentIndex().isValid():
                        selection = QtCore.QItemSelection(firstIndex, self.selectionModel().selectedRows()[-1])
                        self.selectionModel().select(selection, QtCore.QItemSelectionModel.Rows|QtCore.QItemSelectionModel.ClearAndSelect)
                        self.selectionModel().setCurrentIndex(firstIndex, QtCore.QItemSelectionModel.NoUpdate)
                    else:
                        self.setCurrentIndex(firstIndex)
                    self.scrollTo(firstIndex)
                    return
            elif event.matches(QtGui.QKeySequence.MoveToEndOfLine) or event.matches(QtGui.QKeySequence.SelectEndOfLine):
                updateSelection = event.matches(QtGui.QKeySequence.SelectEndOfLine)
                lastIndex = self.model().index(self.model().rowCount() - 1, 2)
                while not lastIndex.flags() & QtCore.Qt.ItemIsEnabled:
                    lastIndex = self.model().index(lastIndex.row() - 1, 2)
                if not self.currentIndex().isValid() or self.currentIndex().row() != lastIndex.row():
                    if updateSelection and self.currentIndex().isValid():
                        selection = QtCore.QItemSelection(self.selectionModel().selectedRows()[0], lastIndex)
                        self.selectionModel().select(selection, QtCore.QItemSelectionModel.Rows|QtCore.QItemSelectionModel.ClearAndSelect)
                        self.selectionModel().setCurrentIndex(lastIndex, QtCore.QItemSelectionModel.NoUpdate)
                    else:
                        self.setCurrentIndex(lastIndex)
                    self.scrollTo(lastIndex)
                else:
                    if self.verticalScrollBar().value() < self.verticalScrollBar().maximum():
                        self.scrollToBottom()
                    else:
                        if updateSelection:
                            if self.currentIndex().row() != lastIndex.row():
                                selection = QtCore.QItemSelection(self.selectionModel().selectedRows()[0], lastIndex)
                                self.selectionModel().select(selection, QtCore.QItemSelectionModel.Rows|QtCore.QItemSelectionModel.ClearAndSelect)
                                self.selectionModel().setCurrentIndex(lastIndex, QtCore.QItemSelectionModel.NoUpdate)
                        else:
                            self.setCurrentIndex(lastIndex)
                        self.scrollTo(lastIndex)
                return
            elif event.matches(QtGui.QKeySequence.MoveToStartOfLine) or event.matches(QtGui.QKeySequence.SelectStartOfLine):
                updateSelection = event.matches(QtGui.QKeySequence.SelectStartOfLine)
                firstIndex = self.model().index(0, 2)
                while not firstIndex.flags() & QtCore.Qt.ItemIsEnabled:
                    firstIndex = self.model().index(firstIndex.row() + 1, 2)
                if not self.currentIndex().isValid() or self.currentIndex().row() != firstIndex.row():
                    if updateSelection and self.currentIndex().isValid():
                        selection = QtCore.QItemSelection(self.selectionModel().selectedRows()[-1], firstIndex)
                        self.selectionModel().select(selection, QtCore.QItemSelectionModel.Rows|QtCore.QItemSelectionModel.ClearAndSelect)
                        self.selectionModel().setCurrentIndex(firstIndex, QtCore.QItemSelectionModel.NoUpdate)
                    else:
                        self.setCurrentIndex(firstIndex)
                    self.scrollTo(firstIndex)
                else:
                    if self.verticalScrollBar().value() > 0:
                        self.scrollToTop()
                    else:
                        if updateSelection:
                            if self.currentIndex().row() != firstIndex.row():
                                selection = QtCore.QItemSelection(self.selectionModel().selectedRows()[-1], firstIndex)
                                self.selectionModel().select(selection, QtCore.QItemSelectionModel.Rows|QtCore.QItemSelectionModel.ClearAndSelect)
                                self.selectionModel().setCurrentIndex(firstIndex, QtCore.QItemSelectionModel.NoUpdate)
                        else:
                            self.setCurrentIndex(firstIndex)
                        self.scrollTo(firstIndex)
                return
            elif event.matches(QtGui.QKeySequence.NextChild) or event.matches(QtGui.QKeySequence.PreviousChild) or \
                (event.modifiers() == QtCore.Qt.ControlModifier and event.key() in (QtCore.Qt.Key_L, QtCore.Qt.Key_R)):
                    #ctrl+tab navigation
                    self.parent().keyPressEvent(event)
                    return
        QtWidgets.QTableView.keyPressEvent(self, event)

    def setSearch(self, text=None):
        if not text:
            self.searchString = ''
            return
        self.searchString += text
        res = self.model().match(self.model().index(0, NameColumn), QtCore.Qt.DisplayRole, self.searchString, flags=QtCore.Qt.MatchStartsWith)
        if not res:
            res = self.model().match(self.model().index(0, NameColumn), QtCore.Qt.DisplayRole, self.searchString, flags=QtCore.Qt.MatchContains)
        if res:
            self.setCurrentIndex(res[0])
            self.searchTimer.start()
        else:
            self.searchString = ''

    def setModel(self, model):
        self.sourceModel = model
        while isinstance(self.sourceModel, QtCore.QSortFilterProxyModel):
            self.sourceModel = self.sourceModel.sourceModel()
        QtWidgets.QTableView.setModel(self, model)
        if isinstance(self, CollectionTableView):
            self.sourceModel.modelReset.connect(self.checkModelSize)
            self.sourceModel.updated.connect(self.checkModelSize)
        model.layoutChanged.connect(self.restoreLayout)
        self.restoreLayout()
        libAlert = '<br/><br/><b>WARNING</b>: this could take a lot of time in the full library view! ' \
            'Use the context menu to restore default order.' if isinstance(self, LibraryTableView) else ''
        for column in range(model.columnCount()):
            if column == NameColumn:
                colName = 'alphabetically'
            elif column == CatColumn:
                colName = 'by category'
            elif column == TagsColumn:
                colName = 'by tag'
            else:
                continue
            model.setHeaderData(column, QtCore.Qt.Horizontal, 'Sort {}{}'.format(colName, libAlert), QtCore.Qt.ToolTipRole)

    def restoreLayout(self):
        self.setColumnHidden(UidColumn, True)
        self.setColumnHidden(LocationColumn, True)
        self.setColumnWidth(NameColumn, self.fontMetrics().width('AAAAAAAAAAAAAAAAAAAA'))
        self.resizeColumnToContents(CatColumn)
        self.horizontalHeader().setResizeMode(CatColumn, QtWidgets.QHeaderView.Fixed)
        self.setWordWrap(False)
        self.resizeRowsToContents()
        self.verticalHeader().setResizeMode(QtWidgets.QHeaderView.Fixed)
        self.verticalHeader().setDefaultSectionSize(self.verticalHeader().sectionSize(0))

    def getBaseMenu(self, pos):
        index = self.indexAt(pos)
        selRows = self.selectionModel().selectedRows()
        if not index.isValid() or not index.flags() & QtCore.Qt.ItemIsEnabled or not selRows:
            valid = False
            if isinstance(self, LibraryTableView):
                return
#            return
        else:
            valid = True
        menu = ContextMenu(self)
        menu.setSeparatorsCollapsible(False)
        nameIndex = index.sibling(index.row(), NameColumn)
        name = nameIndex.data().rstrip() if valid else None
        uid = index.sibling(index.row(), UidColumn).data()

        inConn, outConn = QtWidgets.QApplication.instance().connections

        if (not selRows or not valid) and isinstance(self, CollectionTableView):
            pos = '{}{:03}'.format(uppercase[index.row() >> 7], (index.row() & 127) + 1)
            menu.addSection('Empty slot ' + pos)
            initAction = menu.addAction(QtGui.QIcon.fromTheme('document-new'), 'INIT this slot')
            initAction.triggered.connect(lambda: self.database.initSound(index.row(), self.collection))
            initAllAction = menu.addAction(QtGui.QIcon.fromTheme('document-new'), 'INIT all empty slots...')
            initAllAction.triggered.connect(lambda _, index=index: self.initBanks(index.row() >> 7))
            menu.addSeparator()
            dumpMenu = menu.addMenu(QtGui.QIcon(':/images/dump.svg'), 'Dump')
            if not all((inConn, outConn)):
                dumpMenu.setEnabled(False)
            dumpMenu.setSeparatorsCollapsible(False)
            receiveSection = dumpMenu.addSection('Receive')
            if self.collection not in factoryPresets:
                dumpFromSoundBuffer = dumpMenu.addAction('Dump from Sound Edit Buffer')
                dumpFromSoundBuffer.triggered.connect(lambda: self.dumpFromRequested.emit(None, self.collection, index.row(), False))
                dumpFromIndex = dumpMenu.addAction('Dump from {}'.format(pos))
                dumpFromIndex.triggered.connect(lambda: self.dumpFromRequested.emit(index.row(), self.collection, index.row(), False))
                dumpFromMultiMenu = dumpMenu.addMenu('Dump from Multi Edit Buffer')
                for part in range(16):
                    dumpFromMultiAction = dumpFromMultiMenu.addAction('Part {}'.format(part + 1))
                    dumpFromMultiAction.triggered.connect(lambda _, part=part: self.dumpFromRequested.emit(part, self.collection, index.row(), True))

            sendSection = dumpMenu.addSection('Send')

        elif len(selRows) == 1:
            if selRows[0].row() != index.row():
                index = selRows[0]
            menu.addSection(name)
            soundEditAction = menu.addAction(QtGui.QIcon.fromTheme('dial'), 'Open in the sound editor')
            soundEditAction.triggered.connect(lambda _, uid=uid: self.window().soundEditRequested.emit(uid, self.collection))

            dumpMenu = menu.addMenu(QtGui.QIcon(':/images/dump.svg'), 'Dump')
            if not outConn:
                dumpMenu.setEnabled(False)
            dumpMenu.setSeparatorsCollapsible(False)
            sendSection = dumpMenu.addSection('Send')

            tagsMenu = menu.addMenu(QtGui.QIcon.fromTheme('tag'), 'Tags')
            tagsMenu.aboutToShow.connect(lambda: self.populateTagsMenu([uid]))
            tagsMenu.addSeparator()
            editTagsAction = tagsMenu.addAction(QtGui.QIcon.fromTheme('document-edit'), 'Edit tags...')
            editTagsAction.triggered.connect(lambda _, index=index: self.tagEditRequested.emit(index))

            duplicateAction = menu.addAction(QtGui.QIcon.fromTheme('edit-copy'), 'Duplicate')
            findDuplicatesAction = menu.addAction(QtGui.QIcon.fromTheme('edit-find'), 'Find duplicates...')

            if isinstance(self, CollectionTableView):
                findDuplicatesAction.triggered.connect(lambda: self.findDuplicatesRequested.emit(uid, self.collection))

                receiveSection = dumpMenu.insertSection(sendSection, 'Receive')

                if self.collection not in factoryPresets:
                    dumpFromSoundBuffer = QtWidgets.QAction('Dump from Sound Edit Buffer', dumpMenu)
                    dumpFromSoundBuffer.triggered.connect(lambda: self.dumpFromRequested.emit(None, self.collection, index.row(), False))
                    pos = '{}{:03}'.format(uppercase[index.row() >> 7], (index.row() & 127) + 1)
                    dumpFromIndex = QtWidgets.QAction('Dump from {}'.format(pos), dumpMenu)
                    dumpFromIndex.triggered.connect(lambda: self.dumpFromRequested.emit(index.row(), self.collection, index.row(), False))
                    dumpMenu.insertActions(sendSection, [dumpFromSoundBuffer, dumpFromIndex])
                    dumpFromMultiMenu = QtWidgets.QMenu('Dump from Multi Edit Buffer', dumpMenu)
                    dumpMenu.insertMenu(sendSection, dumpFromMultiMenu)
                else:
                    receiveSection.setVisible(False)

                dumpToSoundBuffer = dumpMenu.addAction('Dump to Sound Edit Buffer')
                dumpToSoundBuffer.triggered.connect(lambda: self.dumpToRequested.emit(uid, None, False))
                dumpToIndex = dumpMenu.addAction('Dump to {}'.format(pos))
                dumpToIndex.triggered.connect(lambda: self.dumpToRequested.emit(uid, index.row(), False))
                dumpToMultiMenu = dumpMenu.addMenu('Dump to Multi Edit Buffer')

                for part in range(16):
                    if self.collection not in factoryPresets:
                        dumpFromMultiAction = dumpFromMultiMenu.addAction('Part {}'.format(part + 1))
                        dumpFromMultiAction.triggered.connect(lambda _, part=part: self.dumpFromRequested.emit(part, self.collection, index.row(), True))
                    dumpToMultiAction = dumpToMultiMenu.addAction('Part {}'.format(part + 1))
                    dumpToMultiAction.triggered.connect(lambda _, part=part: self.dumpToRequested.emit(uid, part, True))

                if not inConn:
                    for w in (receiveSection, dumpFromSoundBuffer, dumpFromIndex, dumpFromMultiMenu):
                        w.setEnabled(False)

                menu.addSeparator()
                deleteAction = menu.addAction(QtGui.QIcon.fromTheme('edit-delete'), 'Remove from "{}"'.format(self.collection))
                deleteAction.setStatusTip('Remove the selected sound from the current collection only')
                duplicateAction.setStatusTip('Duplicate the selected sound to the closest available free slot')
                if self.model().size() >= 1024:
                    duplicateAction.setEnabled(False)
                if not self.editable:
                    deleteAction.setEnabled(False)
                    duplicateAction.setEnabled(False)
            else:
                findDuplicatesAction.triggered.connect(lambda: self.findDuplicatesRequested.emit(uid, None))
                dumpToSoundBuffer = dumpMenu.addAction('Dump to Sound Edit Buffer')
                dumpToSoundBuffer.triggered.connect(lambda: self.dumpToRequested.emit(uid, None, False))
                dumpToMultiMenu = dumpMenu.addMenu('Dump to Multi Edit Buffer')

                for part in range(16):
                    dumpToMultiAction = dumpToMultiMenu.addAction('Part {}'.format(part + 1))
                    dumpToMultiAction.triggered.connect(lambda _, part=part: self.dumpToRequested.emit(uid, part, True))

                menu.addSeparator()
                deleteAction = menu.addAction(QtGui.QIcon.fromTheme('edit-delete'), 'Delete "{}"'.format(name))
                deleteAction.setStatusTip('Delete the selected sound from the library and any collection')
                duplicateAction.setStatusTip('Duplicate the selected sound')
                if not nameIndex.flags() & QtCore.Qt.ItemIsEditable:
                    deleteAction.setEnabled(False)
            duplicateAction.triggered.connect(lambda: self.duplicateRequested.emit(uid, index.row()))
            deleteAction.triggered.connect(lambda: self.deleteRequested.emit([uid]))
            menu.addSeparator()
            exportAction = menu.addAction(QtGui.QIcon.fromTheme('document-save'), 'Export...')
            exportAction.triggered.connect(lambda: self.exportRequested.emit([uid], self.collection))
        else:
            uidList = [idx.sibling(idx.row(), UidColumn).data(QtCore.Qt.DisplayRole) for idx in selRows]
            menu.addSection('{} sounds selected'.format(len(selRows)))

            if isinstance(self, CollectionTableView):
                dumpMenu = menu.addMenu(QtGui.QIcon(':/images/dump.svg'), 'Dump')
                dumpMenu.setSeparatorsCollapsible(False)
                if not outConn:
                    dumpMenu.setEnabled(False)

                if self.collection not in factoryPresets:
                    receiveSection = dumpMenu.addSection('Receive')
                sendSection = dumpMenu.addSection('Send')

            tagsMenu = menu.addMenu(QtGui.QIcon.fromTheme('tag'), 'Tags')
            tagsMenu.aboutToShow.connect(lambda: self.populateTagsMenu(uidList))
            tagsMenu.addSeparator()
            editTagsMultiAction = tagsMenu.addAction(QtGui.QIcon.fromTheme('document-edit'), 'Edit tags...')
            editTagsMultiAction.triggered.connect(lambda: self.tagEditMultiRequested.emit(selRows))

            if isinstance(self, CollectionTableView):
                deleteAction = menu.addAction(QtGui.QIcon.fromTheme('edit-delete'), 'Remove from "{}"'.format(self.collection))
                deleteAction.setStatusTip('Remove the selected sounds from the current collection only')
                if self.editable:
                    deletable = uidList[:]
                else:
                    deletable = []
                    deleteAction.setEnabled(False)
            else:
                deletable = [_uid for _uid in uidList if self.database.isUidWritable(_uid)]
                deleteAction = menu.addAction(QtGui.QIcon.fromTheme('edit-delete'), 'Delete {} sounds'.format(len(deletable)))
                deleteAction.setStatusTip('Delete the selected sounds from the library and any collection')
            if not deletable:
                deleteAction.setText('Sounds not deletable')
                deleteAction.setEnabled(False)
            deleteAction.triggered.connect(lambda: self.deleteRequested.emit(deletable))
            menu.addSeparator()
            exportAction = menu.addAction(QtGui.QIcon.fromTheme('document-save'), 'Export...')
            exportAction.triggered.connect(lambda: self.exportRequested.emit(uidList, self.collection))
            if len(uidList) > 1024:
                exportAction.setEnabled(False)

        if isinstance(self, CollectionTableView):
            if len(selRows) > 1:
                indexes = [self.model().mapToRootSource(i).row() for i in selRows]
                fromText = toText = 'Dump {} selected sounds...'.format(len(selRows))
            else:
                indexes = False
                fromText = 'Show dump receive dialog...'
                toText = 'Show dump send dialog...'
            if self.collection not in factoryPresets:
                dumpFromAllAction = QtWidgets.QAction(QtGui.QIcon.fromTheme('arrow-left-double'), fromText, dumpMenu)
                dumpFromAllAction.triggered.connect(lambda: self.fullDumpBlofeldToCollectionRequested.emit(self.collection, indexes))
                dumpMenu.insertAction(sendSection, dumpFromAllAction)
            dumpToAllAction = dumpMenu.addAction(QtGui.QIcon.fromTheme('arrow-right-double'), toText)
            dumpToAllAction.triggered.connect(lambda: self.fullDumpCollectionToBlofeldRequested.emit(self.collection, indexes))

        return menu, index, name, uid

    def initBanks(self, bank):
        banks = InitEmptySlotsDialog(self, bank).exec_()
        if banks is not None:
            self.database.initBanks(banks, self.collection, allSlots=False)

    def populateTagsMenu(self, uidList):
        menu = self.sender()
        firstAction = menu.actions()[0]
        if isinstance(firstAction, QtWidgets.QWidgetAction):
            return
        action = QtWidgets.QWidgetAction(menu)
        widget = TagsMiniWidget(uidList, action)
        action.setDefaultWidget(widget)
        menu.insertAction(firstAction, action)


class LibraryTableView(BaseLibraryView):
    def __init__(self, *args, **kwargs):
        BaseLibraryView.__init__(self, *args, **kwargs)
        self.verticalHeader().setVisible(False)
        self.layoutChangeBuffer = None
        self.collection = None

    def restoreLayout(self):
        self.setColumnHidden(FactoryColumn, True)
        BaseLibraryView.restoreLayout(self)

    def showMenu(self, pos):
        res = self.getBaseMenu(pos)
        if not res:
            return
        menu, index, name, uid = res
        menu.exec_(self.viewport().mapToGlobal(pos))

    def dragMoveEvent(self, event):
        if isinstance(event.source(), BaseLibraryView):
            event.ignore()
        elif self.externalFileDropContents:
#            rows = self.externalFileDropContents
#            print(rows)
            event.accept()
#            BaseLibraryView.dragMoveEvent(self, event)

    def dropEvent(self, event):
        if self.externalFileDropContents:
            data = event.mimeData().data('text/uri-list')
            uriList = unicode(data).replace('\r', '').strip().split('\n')
            self.importRequested.emit(uriList)
        BaseLibraryView.dropEvent(self, event)


class CollectionTableView(BaseLibraryView):
    dropIntoPen = QtCore.Qt.blue
    dropIntoBrush = QtGui.QBrush(QtGui.QColor(32, 128, 255, 96))
    emptyBrush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 160))

    def __init__(self, *args, **kwargs):
        BaseLibraryView.__init__(self, *args, **kwargs)
        self.setDropIndicatorShown(False)
        self.menuActive = None
        self.autoScrollTimer = QtCore.QTimer()
        self.autoScrollDelta = 0
        self.autoScrollAccel = 0
        self.autoScrollTimer.timeout.connect(self.doAutoScroll)
        self.setAutoScroll(False)
        self.dropIndicatorPosition = self.OnViewport
        self.cornerButton = self.findChild(QtWidgets.QAbstractButton)
        self.cornerButton.clicked.disconnect()
        self.cornerButton.setToolTip('Restore default order (by bank/prog)')
        self.cornerButton.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.cornerButton.customContextMenuRequested.connect(self.sortMenu)
        self.cornerButton.clicked.connect(lambda: self.sortByColumn(-1))
        cornerLayout = QtWidgets.QHBoxLayout()
        cornerLayout.setContentsMargins(0, 0, 0, 0)
        self.cornerButton.setLayout(cornerLayout)
        self.cornerLbl = QtWidgets.QLabel('Index')
        self.cornerLbl.setAlignment(QtCore.Qt.AlignCenter)
        cornerLayout.addWidget(self.cornerLbl)
        font = self.font()
        font.setBold(True)
        self.cornerButton.setFont(font)

        self.emptyInfoBox = QtGui.QTextDocument(
            'This collection is empty.\n\n'
            'Drag sounds from a collection or the Main Library, '
            'otherwise use the right click menu to create a new sound '
            'or dump content from your Blofeld.')
        option = self.emptyInfoBox.defaultTextOption()
        option.setWrapMode(option.WordWrap)
        option.setAlignment(QtCore.Qt.AlignCenter)
        self.emptyInfoBox.setDefaultTextOption(option)
        self.emptyInfoBoxHCenter = self.emptyInfoBoxVCenter = 0
        self.preferredInfoBoxWidth = self.fontMetrics().width(self.emptyInfoBox.toPlainText().splitlines()[0]) * 2.5


    @property
    def cachedSize(self):
        try:
            return self._cachedSize
        except:
            self._cachedSize = None
            self.checkModelSize()
            return self._cachedSize

    @cachedSize.setter
    def cachedSize(self, size):
        self._cachedSize = size

    def checkModelSize(self):
        newSize = self.model().size()
        if newSize != self.cachedSize:
            #on windows/osx, the paintEvent.rect() does not include the full geometry
            #so we connect the scrollbars to avoid drawing artifacts on the empty
            #collection infobox
            if not 'linux' in sys.platform:
                #remember, the size might be -1!
                if newSize > 0:
                    try:
                        self.verticalScrollBar().valueChanged.disconnect(self.viewport().update)
                        self.horizontalScrollBar().valueChanged.disconnect(self.viewport().update)
                    except:
                        pass
                else:
                    try:
                        self.verticalScrollBar().valueChanged.connect(self.viewport().update, QtCore.Qt.UniqueConnection)
                        self.horizontalScrollBar().valueChanged.connect(self.viewport().update, QtCore.Qt.UniqueConnection)
                    except Exception as e:
                        print(e)
        if newSize <= 0:
            self.parent().clearFilters()
        self.cachedSize = newSize

    def doAutoScroll(self):
        self.verticalScrollBar().setValue(self.verticalScrollBar().value() + self.autoScrollDelta)
        if self.verticalScrollBar().value() in (0, self.verticalScrollBar().maximum()):
            self.autoScrollTimer.stop()
            self.autoScrollAccel = 0
            return
        if self.autoScrollAccel < 48:
            self.autoScrollAccel += 1

    def checkAutoScroll(self, pos):
        y = pos.y()
        margin = self.autoScrollMargin()
        if y < margin:
            if self.verticalScrollBar().value() > 0:
                self.autoScrollDelta = -1
                self.autoScrollTimer.setInterval(150 - (margin - y) * 100 / margin - self.autoScrollAccel)
                if not self.autoScrollTimer.isActive():
                    self.autoScrollAccel = 0
                    self.autoScrollTimer.start()
                    self.doAutoScroll()
                return
        elif y > self.viewport().height() - margin:
            if self.verticalScrollBar().value() < self.verticalScrollBar().maximum():
                self.autoScrollDelta = 1
                self.autoScrollTimer.setInterval(150 - (margin - self.viewport().height() + y) * 100 / margin - self.autoScrollAccel)
                if not self.autoScrollTimer.isActive():
                    self.autoScrollAccel = 0
                    self.autoScrollTimer.start()
                    self.doAutoScroll()
                return
        self.autoScrollTimer.stop()
#        if pos.y() < self.autoScrollMargin() and self.verticalScrollBar().value() > 0:
#            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - 1)
#        elif pos.y() > self.viewport().height() - self.autoScrollMargin() and self.verticalScrollBar().value() < self.verticalScrollBar().maximum():
#            self.verticalScrollBar().setValue(self.verticalScrollBar().value() + 1)

    def showMenu(self, pos):
        res = self.getBaseMenu(pos)
        if not res:
            return
        menu, index, name, uid = res
        self.menuActive = index
        menu.exec_(self.viewport().mapToGlobal(pos))
        self.menuActive = None
        #required of MacOS
        self.update()

    def dragEnterEvent(self, event):
        self.checkAutoScroll(event.pos())
        BaseLibraryView.dragEnterEvent(self, event)

    def dragMoveEvent(self, event):
        self.checkAutoScroll(event.pos())
        if self.externalFileDropContents:
            rows = self.externalFileDropContents
        else:
            rows = self.getDragRows(event)
        if event.source() != self:
            if event.keyboardModifiers() == QtCore.Qt.ControlModifier:
                event.setDropAction(QtCore.Qt.CopyAction)
                dropIndex = self.indexAt(event.pos())
                self.createDropIndexes(dropIndex, len(rows), event.pos(), False)
                self.showStatusBarMessage('Overwrite mode active.')
                event.accept()
                self.viewport().update()
                return
            self.dropIndicatorPosition = self.OnItem
#            print(len(rows), self.model().size())
            if len(rows) + self.model().size() > 1024:
                self.showStatusBarMessage('Cannot add sounds as the collection is full!')
                event.ignore()
                return
            elif self.externalFileDropContents:
                dropIndex = self.indexAt(event.pos())
            else:
                dropIndex = self.indexAt(event.pos())
                if dropIndex.flags() & QtCore.Qt.ItemIsEnabled:
                    self.showStatusBarMessage('Sounds can be added to empty slots only! Keep CTRL pressed to overwrite.')
                    self.dropSelectionIndexes = None
                    event.ignore()
                    self.viewport().update()
                    return
                elif self.model().rowCount() < 1024:
                    self.showStatusBarMessage('Cannot import sounds to a collection when filters are active!')
                    event.ignore()
                    return
            self.createDropIndexesEmptySlots(dropIndex, len(rows))
            QtWidgets.QTableView.dragMoveEvent(self, event)
            event.accept()
            if self.dropSelectionIndexes[-1].row() - self.dropSelectionIndexes[0].row() + 1 != len(self.dropSelectionIndexes):
                self.showStatusBarMessage('Not sequential empty slots found, press CTRL to overwrite existing sounds.')
            else:
                self.clearStatusBar()
            return
        else:
            dropIndex = self.indexAt(event.pos())
            dropIndex = dropIndex.sibling(dropIndex.row(), NameColumn)
            if self.externalFileDropContents:
                pass
            else:
                event.setDropAction(QtCore.Qt.MoveAction)
                self.createDropIndexes(dropIndex, len(rows), event.pos())
                selRows = self.selectionModel().selectedRows(NameColumn)
                dropIndicator = self.getDropIndicatorPosition(self.visualRect(dropIndex), event.pos())
                duplicate = ''
                if event.keyboardModifiers() == QtCore.Qt.ShiftModifier:
                    if dropIndicator != self.OnItem:
                        if len(rows) + self.model().size() > 1024:
                            self.showStatusBarMessage('Unable to duplicate, not enough empty slots!')
                            event.ignore()
                            self.viewport().update()
                            return
                        else:
                            self.showStatusBarMessage('Selected indexes will be duplicated and inserted between items.')
                    elif selRows == self.dropSelectionIndexes:
                        event.ignore()
                        self.viewport().update()
                        return
                    else:
                        self.showStatusBarMessage('Duplicate mode active; existing slots will be overwritten.')
                    event.accept()
                    self.viewport().update()
                    return
                if len(selRows) > 1 and event.keyboardModifiers() == QtCore.Qt.ControlModifier:
                    if self.dropSelectionIndexes[0] in selRows:
                        self.dropSelectionIndexes = None
                        event.ignore()
                        self.viewport().update()
                        self.clearStatusBar()
                        return
                    self.dropSelectionIndexes = self.dropSelectionIndexes[:1]
                    event.accept()
                    self.viewport().update()
                    if dropIndicator == self.OnItem and len(rows) > 1:
                        self.showStatusBarMessage('Single swap in use, only the dropped item will be swapped with the selection.')
                    else:
                        self.clearStatusBar()
                    return
#                    if self.dropSelectionIndexes
                if (dropIndex in selRows and dropIndicator in (self.AboveItem, self.BelowItem)):
                        self.dropSelectionIndexes = None
                        self.dropIndicatorPosition = self.OnViewport
                        BaseLibraryView.dragMoveEvent(self, event)
                        event.ignore()
                        self.viewport().update()
                        self.clearStatusBar()
                        return
                if dropIndicator == self.OnItem and len(rows) > 1 and not duplicate:
                    text = 'Full swap: the selected item will be swapped with those on which they will be dropped; press CTRL to swap a single entry or SHIFT to duplicate.'
                    self.showStatusBarMessage(text)
                else:
                    self.clearStatusBar()
                event.accept()
                self.viewport().update()
                return

        self.clearStatusBar()
        event.acceptProposedAction()
        if event.mimeData().hasFormat('application/x-qabstractitemmodeldatalist'):
            QtWidgets.QTableView.dragMoveEvent(self, event)

    def getDropIndicatorPosition(self, rect=QtCore.QRect(), pos=QtCore.QPoint(), apply=True):
        margin = sanitize(2, rect.height() / 5.5, 12)
        y = pos.y()
        if y - rect.top() < margin:
            dropIndicatorPosition = self.AboveItem
        elif rect.bottom() - y < margin:
            dropIndicatorPosition = self.BelowItem
        elif rect.y() <= y <= rect.bottom():
            dropIndicatorPosition = self.OnItem
        else:
            dropIndicatorPosition = self.OnViewport
        if apply:
            self.dropIndicatorPosition = dropIndicatorPosition
        return dropIndicatorPosition

    def dragLeaveEvent(self, event):
        self.autoScrollTimer.stop()
        self.getDropIndicatorPosition()
        BaseLibraryView.dragLeaveEvent(self, event)

    def dropEvent(self, event):
        self.autoScrollTimer.stop()
        self.window().statusBar().clearMessage()
        if self.dropIndicatorPosition == self.OnViewport:
            event.ignore()
            return
        if event.mimeData().hasFormat('bigglesworth/collectionItems'):
            data = event.mimeData().data('bigglesworth/collectionItems')
            stream = QtCore.QDataStream(data)
            uidList = []
            while not stream.atEnd():
                uidList.append(stream.readQVariant())
            targetRows = [idx.row() for idx in self.dropSelectionIndexes]
            if event.source() != self:
                #we need this hack to dismiss the drop cursor, might want to use a signal instead
                QtWidgets.QApplication.processEvents()
                if event.keyboardModifiers() == QtCore.Qt.ControlModifier:
                    overwrite = True
                else:
                    overwrite = False
                QtCore.QTimer.singleShot(0, lambda: [self.dropFromLibrary(uidList, targetRows, overwrite), event.accept(), BaseLibraryView.dropEvent(self, event)])
                return
            if event.keyboardModifiers() == QtCore.Qt.ShiftModifier:
                if self.dropIndicatorPosition != self.OnItem:
                    self.database.duplicateAndInsert(uidList, self.collection, self.dropSelectionIndexes[0].row())
                else:
                    self.database.duplicateAndReplace(uidList, self.collection, targetRows)
            elif event.keyboardModifiers() == QtCore.Qt.ControlModifier:
                self.dropSelectionIndexes = self.dropSelectionIndexes[:1]
            if self.dropIndicatorPosition == self.OnItem:
                self.database.swapSounds(uidList, self.collection, targetRows)
            else:
                self.database.insertSounds(uidList, self.collection, self.getDragRows(event), self.dropSelectionIndexes[0].row())

        elif self.externalFileDropContents:
            data = event.mimeData().data('text/uri-list')
            uriList = unicode(data).replace('\r', '').strip().split('\n')
            self.importRequested.emit(uriList)
        event.acceptProposedAction()
        QtWidgets.QTableView.dropEvent(self, event)
#        self.externalFileDropContents = None
#        self.dropSelectionIndexes = None
        BaseLibraryView.dropEvent(self, event)

    def dropFromLibrary(self, uidList, targetRows, overwrite):
        scrollPos = self.verticalScrollBar().value()
        self.dropEventSignal.emit()
        duplicates = self.database.checkDuplicates(uidList, self.collection)
        if overwrite:
            for idx in self.dropSelectionIndexes:
                uid = idx.sibling(idx.row(), UidColumn).data()
                if uid in duplicates:
                    duplicates.remove(uid)
        if duplicates:
            dialog = DropDuplicatesMessageBox(
                self, 
                self.database.getNamesFromUidList(duplicates), 
                self.collection, 
                len(uidList) == len(duplicates)
                )
            res = dialog.exec_()
            if res == dialog.Open:
                #duplicate existing sounds!
                newUidList = []
                for uid in uidList:
                    if uid in duplicates:
                        newUidList.append(self.database.duplicateSound(uid))
                    else:
                        newUidList.append(uid)
#                print(newUidList)
                res = self.database.addSoundsToCollection(
                    zip(newUidList, targetRows), 
                    self.collection
                    )
#                print(res)
            elif res == dialog.Ignore:
                #ignore duplicates
                uidMap = []
                indexList = iter(targetRows)
                for uid in uidList:
                    if uid not in duplicates:
                        uidMap.append((uid, indexList.next()))
                self.database.addSoundsToCollection(uidMap, self.collection)
        else:
            print('adding duplicate-free')
            self.database.addSoundsToCollection(zip(uidList, [idx.row() for idx in self.dropSelectionIndexes]), self.collection)
            print('done!')

        self.dropSelectionIndexes = None
        selection = QtCore.QItemSelection(self.model().index(min(targetRows), 2), self.model().index(max(targetRows), 2))
        self.selectionModel().select(selection, QtCore.QItemSelectionModel.Rows|QtCore.QItemSelectionModel.ClearAndSelect)
        self.selectionModel().setCurrentIndex(selection.indexes()[0], QtCore.QItemSelectionModel.NoUpdate)
        self.verticalScrollBar().setValue(scrollPos)


    def createDropIndexesEmptySlots(self, firstIndex, rowCount):
#        if self.dropSelectionIndexes and self.dropSelectionIndexes[0].row() == firstIndex.row():
#            return
        firstRow = row = firstIndex.row()
        firstIndex = firstIndex.sibling(firstIndex.row(), NameColumn)
        if firstRow == 1023 and rowCount == 1:
            self.dropSelectionIndexes = [firstIndex]
            return
        indexList = []
        delta = 1
        while len(indexList) < rowCount:
            index = self.model().index(row, NameColumn)
            if not index.flags() & QtCore.Qt.ItemIsEnabled:
                if delta == 1:
                    indexList.append(index)
                else:
                    indexList.insert(0, index)
            row += delta
            if row == 1024:
                row = firstRow - 1
                delta = -1
        self.dropSelectionIndexes = indexList

    def createDropIndexes(self, firstIndex, rowCount, pos, checkPos=True):
#        if self.dropSelectionIndexes and self.dropSelectionIndexes[0].row() == firstIndex.row():
#            return
        p = self.getDropIndicatorPosition(self.visualRect(firstIndex), pos, False)
        if checkPos and p == self.BelowItem:
            below = 1
        else:
            below = 0
        firstRow = row = firstIndex.row() + below
        firstIndex = firstIndex.sibling(firstIndex.row(), NameColumn)
        if firstRow == 1023 and rowCount == 1:
            self.dropSelectionIndexes = [firstIndex]
            return
        indexList = []
        delta = 1
        while len(indexList) < rowCount:
            index = self.model().index(row, NameColumn)
            if delta == 1:
                indexList.append(index)
            else:
                indexList.insert(0, index)
            row += delta
            if row == 1024:
                row = firstRow - 1
                delta = -1
        self.dropSelectionIndexes = indexList

    def paintEvent(self, event):
        QtWidgets.QTableView.paintEvent(self, event)
        if self.dropSelectionIndexes:
            qp = QtGui.QPainter(self.viewport())
            qp.setPen(self.dropIntoPen)
            qp.setBrush(self.dropIntoBrush)
            if self.dropIndicatorPosition == self.OnItem:
                #map to the last column already for performance reasons
                rect = self.visualRect(self.dropSelectionIndexes[0])
                rect |= self.visualRect(self.dropSelectionIndexes[0].sibling(self.dropSelectionIndexes[0].row(), TagsColumn))
                try:
                    for index in self.dropSelectionIndexes:
                        newRect = self.visualRect(index)
                        if newRect.intersect(self.viewport().rect()):
                            if newRect.top() - 1 <= rect.bottom() + 1:
                                rect |= newRect
                            else:
                                qp.drawRect(rect)
                                rect = newRect | self.visualRect(index.sibling(index.row(), TagsColumn))
                    qp.drawRect(rect)
                except Exception as e:
                    print(e)
            elif self.dropIndicatorPosition == self.BelowItem:
                rect = self.visualRect(self.dropSelectionIndexes[0])
                rect |= self.visualRect(self.dropSelectionIndexes[0].sibling(self.dropSelectionIndexes[0].row(), TagsColumn))
                y = rect.bottom() - self.verticalHeader().sectionSize(0)
                qp.drawLine(rect.x(), y, rect.width(), y)
            elif self.dropIndicatorPosition == self.AboveItem:
                rect = self.visualRect(self.dropSelectionIndexes[0])
                rect |= self.visualRect(self.dropSelectionIndexes[0].sibling(self.dropSelectionIndexes[0].row(), TagsColumn))
                qp.drawLine(rect.x(), rect.top(), rect.width(), rect.top())
        elif self.menuActive and self.menuActive.isValid() and not self.menuActive.flags() & QtCore.Qt.ItemIsEnabled:
            viewport = self.viewport()
            qp = QtGui.QPainter(viewport)
            qp.setPen(self.dropIntoPen)
            qp.setBrush(self.dropIntoBrush)
            left = self.visualRect(self.menuActive.sibling(self.menuActive.row(), NameColumn))
            right = self.visualRect(self.menuActive.sibling(self.menuActive.row(), TagsColumn))
            qp.drawRect(left | right)
        elif not self.menuActive:
            if self.cachedSize <= 0:
                viewport = self.viewport()
                qp = QtGui.QPainter(viewport)
                qp.setPen(QtCore.Qt.NoPen)
                qp.setBrush(self.emptyBrush)
                qp.translate(.5, .5)
                qp.drawRect(viewport.rect())
                qp.setPen(self.palette().color(QtGui.QPalette.WindowText))
                qp.translate(viewport.rect().center().x() - self.emptyInfoBoxHCenter, viewport.rect().center().y() - self.emptyInfoBoxVCenter)
                self.emptyInfoBox.drawContents(qp, QtCore.QRectF(viewport.rect()))
            elif not self.model().rowCount():
                viewport = self.viewport()
                qp = QtGui.QPainter(viewport)
                qp.setPen(QtCore.Qt.NoPen)
                qp.setBrush(self.emptyBrush)
                qp.translate(.5, .5)
                qp.drawRect(viewport.rect())
                qp.setPen(self.palette().color(QtGui.QPalette.WindowText))
                qp.drawText(viewport.rect(), QtCore.Qt.AlignCenter, 'Current filters return no result')

    def resizeEvent(self, event):
        BaseLibraryView.resizeEvent(self, event)
        if not event.size().isEmpty():
            self.emptyInfoBox.setTextWidth(min(self.viewport().width(), self.preferredInfoBoxWidth))
            self.emptyInfoBoxHCenter = self.emptyInfoBox.size().width() / 2
            #add a line height to vertically align slightly above than the center
            self.emptyInfoBoxVCenter = (self.emptyInfoBox.size().height() + self.fontMetrics().height()) / 2


class BaseLibraryWidget(QtWidgets.QWidget):
    importRequested = QtCore.pyqtSignal(object, object)
    exportRequested = QtCore.pyqtSignal(object, object)
    findDuplicatesRequested = QtCore.pyqtSignal(str, object)
    #blofeld index/buffer, collection, index, multi
    dumpFromRequested = QtCore.pyqtSignal(object, object, int, bool)
    #uid, blofeld index/buffer, multi
    dumpToRequested = QtCore.pyqtSignal(object, object, bool)
    fullDumpCollectionToBlofeldRequested = QtCore.pyqtSignal(str, object)
    fullDumpBlofeldToCollectionRequested = QtCore.pyqtSignal(str, object)

    def __init__(self, uiPath, parent, collection=None):
        QtWidgets.QWidget.__init__(self, parent)
        loadUi(uiPath, self)
        self.database = parent.database

        self.filterTagsEdit.setModel(self.database.tagsModel)
        self.filterTagsEdit.setAutoPopup(True)
        self.filterNameEdit.setMinimumWidth(self.fontMetrics().width('AAAAAAAAAAAAAAAA'))
        self.collectionView.tagsDelegate.tagClicked.connect(self.setTagFilter)
        self.collectionView.importRequested.connect(lambda uriList: self.importRequested.emit(uriList, self.collection))
        self.editModeBtn = QtWidgets.QPushButton(QtGui.QIcon.fromTheme('edit-rename'), '')
        self.editModeBtn.setToolTip('Toggle edit mode')
        self.editModeBtn.setStatusTip('Toggle edit mode to rename sounds or change category')
        self.editModeBtn.setCheckable(True)
        self.collectionView.setCornerWidget(self.editModeBtn)

        self.model = self.database.openCollection(collection)
        while self.model.canFetchMore():
            self.model.fetchMore()
        self.model.scheduledQueryUpdateSet.connect(self.scheduledQueryUpdateSet)

        self.nameProxy = NameProxy()
        self.nameProxy.setSourceModel(self.model)
        self.nameProxy.setFilterKeyColumn(NameColumn)
        self.nameProxy.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)
#        self.nameProxy.invalidated.connect(self.filtersInvalidated)
        self.filterNameEdit.textChanged.connect(self.nameProxy.setFilterWildcard)

        self.tagsProxy = TagsProxy()
        self.tagsProxy.setSourceModel(self.nameProxy)
        self.tagsProxy.invalidated.connect(self.filtersInvalidated)
        self.filterTagsEdit.tagsChanged.connect(self.tagsProxy.setFilter)

        self.collectionView.setModel(self.tagsProxy)
        self.collectionView.setTagsModel(self.database.tagsModel)
        self.collectionView.tagEditRequested.connect(self.tagEditRequested)
        self.collectionView.tagEditMultiRequested.connect(self.tagEditMultiRequested)
        self.collectionView.duplicateRequested.connect(self.duplicateRequested)
        self.collectionView.findDuplicatesRequested.connect(self.findDuplicatesRequested)
        self.collectionView.deleteRequested.connect(self.deleteRequested)
        self.collectionView.exportRequested.connect(self.exportRequested)
        self.collectionView.fullDumpCollectionToBlofeldRequested.connect(self.fullDumpCollectionToBlofeldRequested)
        self.collectionView.fullDumpBlofeldToCollectionRequested.connect(self.fullDumpBlofeldToCollectionRequested)


        self.collectionView.dumpToRequested.connect(self.dumpToRequested)
        self.collectionView.dumpFromRequested.connect(self.dumpFromRequested)

    def selectUidList(self, uidList):
        self.clearFilters()
        self.collectionView.selectIndexes(uidList)

    def setTagFilter(self, tag):
        if not tag in self.filterTagsEdit.tags:
            self.filterTagsEdit.setTags(self.filterTagsEdit.tags + [tag])

    def filtersInvalidated(self):
        if self.collectionView.currentIndex().isValid():
            #for some reason (event loop?), we need to fire this twice
            self.collectionView.scrollTo(self.collectionView.currentIndex(), self.collectionView.PositionAtCenter)
            self.collectionView.scrollTo(self.collectionView.currentIndex(), self.collectionView.PositionAtCenter)

    def tagEditRequested(self, index):
        uid = index.sibling(index.row(), UidColumn).data()
        dialog = SoundTagsEditDialog(self, uid, self.database.tagsModel)
        res = dialog.exec_()
        if res:
            self.model.setData(index.sibling(index.row(), TagsColumn), json.dumps(sorted(dialog.tags)), TagsRole)

    def tagEditMultiRequested(self, indexList):
        uidList = []
        tags = []
        for index in indexList:
            uidList.append(index.sibling(index.row(), UidColumn).data())
            tags.extend(json.loads(index.sibling(index.row(), TagsColumn).data()))
        dialog = MultiSoundTagsEditDialog(self, uidList, sorted(set(tags)), self.database.tagsModel)
        res = dialog.exec_()
        if res:
            tags = json.dumps(sorted(dialog.tags))
            self.model.blockSignals(True)
            for index in indexList:
                self.model.setData(index.sibling(index.row(), TagsColumn), tags, TagsRole)
            self.model.blockSignals(False)
            self.model.dataChanged.emit(index, index)
            self.model.updated.emit()

    def showEvent(self, event):
        QtWidgets.QWidget.showEvent(self, event)
        self.model.queryUpdate()

    def scheduledQueryUpdateSet(self):
        if self.isVisible():
            self.model.queryUpdate()

    def setEditMode(self, mode):
        if mode:
            self.collectionView.setEditTriggers(self.collectionView.DoubleClicked|self.collectionView.EditKeyPressed)
        else:
            self.collectionView.setEditTriggers(self.collectionView.NoEditTriggers)


class CollectionWidget(BaseLibraryWidget):
    def __init__(self, parent, collection):
        BaseLibraryWidget.__init__(self, 'ui/collectionwidget.ui', parent, collection)
#        loadUi('ui/collectionwidget.ui', self)
#        self.collectionView.database = parent.database
        self.collectionView.collection = collection
        self.collectionView.horizontalHeader().sortIndicatorChanged.connect(self.checkFilters)

#        self.filterTagsEdit.setModel(self.database.tagsModel)
#        self.filterNameEdit.setMinimumWidth(self.fontMetrics().width('AAAAAAAAAAAAAAAA'))
#        self.collectionView.tagsDelegate.tagClicked.connect(self.setTagFilter)

        self.collection = collection
        if collection in factoryPresets:
            self.editModeBtn.setEnabled(False)
            self.editable = False
            self.emptySlotsChk.setEnabled(False)
        else:
            self.editable = True
            self.editModeBtn.toggled.connect(self.setEditMode)

        self.collectionView.editable = self.editable

#        self.model = self.database.openCollection(collection)
#        while self.model.canFetchMore():
#            self.model.fetchMore()
        self.model.updated.connect(self.checkFilters)
#        self.model.scheduledQueryUpdateSet.connect(self.scheduledQueryUpdateSet)

#        self.fullLibraryProxy = FullLibraryProxy()
#        self.fullLibraryProxy.setSourceModel(self.model)

        self.cleanLibraryProxy = CleanLibraryProxy()
        self.cleanLibraryProxy.setSourceModel(self.model)
        self.cleanLibraryProxy.invalidated.connect(self.filtersInvalidated)
        self.emptySlotsChk.toggled.connect(self.cleanLibraryProxy.setFilter)

        self.bankProxy = BankProxy()
        self.bankProxy.setSourceModel(self.cleanLibraryProxy)
        self.bankProxy.invalidated.connect(self.filtersInvalidated)
        self.bankCombo.currentIndexChanged.connect(lambda idx: self.bankProxy.setFilter(idx - 1))
        self.bankCombo.currentIndexChanged.connect(self.checkFilters)

        self.catProxy = CatProxy()
        self.catProxy.setSourceModel(self.bankProxy)
        self.catProxy.invalidated.connect(self.filtersInvalidated)
        self.catCombo.currentIndexChanged.connect(lambda idx: self.catProxy.setFilter(idx - 1))
        self.catCombo.currentIndexChanged.connect(self.checkFilters)

#        self.nameProxy = NameProxy()
        self.nameProxy.setSourceModel(self.catProxy)
#        self.nameProxy.setFilterKeyColumn(NameColumn)
#        self.nameProxy.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)
##        self.nameProxy.invalidated.connect(self.filtersInvalidated)
#        self.filterNameEdit.textChanged.connect(self.nameProxy.setFilterWildcard)
        self.filterNameEdit.textChanged.connect(self.checkFilters)

#        self.tagsProxy = TagsProxy()
#        self.tagsProxy.setSourceModel(self.nameProxy)
#        self.tagsProxy.invalidated.connect(self.filtersInvalidated)
#        self.filterTagsEdit.tagsChanged.connect(self.tagsProxy.setFilter)
        self.filterTagsEdit.tagsChanged.connect(self.checkFilters)

#        self.collectionView.setModel(self.tagsProxy)
#        self.collectionView.setTagsModel(self.database.tagsModel)
#        self.collectionView.tagEditRequested.connect(self.tagEditRequested)
#        self.collectionView.tagEditMultiRequested.connect(self.tagEditMultiRequested)
#        self.collectionView.duplicateRequested.connect(self.duplicateRequested)
#        self.collectionView.deleteRequested.connect(self.deleteRequested)

        self.catCombo.view().setUniformItemSizes(True)
        self.bankCombo.view().setUniformItemSizes(True)
        self.updateFilterCombos()
        self.filterGroupBox.setEnabled(True if self.model.size() > 0 else False)

    def clearFilters(self):
        self.bankCombo.setCurrentIndex(0)
        self.catCombo.setCurrentIndex(0)
        self.filterNameEdit.setText('')
        self.filterTagsEdit.setTags()
        self.emptySlotsChk.setChecked(True)

    def focusUid(self, uid):
        self.clearFilters()
        index = self.collectionView.model().index(
            self.database.getIndexForUid(uid, self.collection), NameColumn)
        self.collectionView.setCurrentIndex(index)
        self.collectionView.scrollTo(index)

    def focusIndex(self, bank, prog):
        index = self.collectionView.model().mapFromRootSource((bank << 7) + prog, NameColumn)
        if index.isValid():
            self.collectionView.setCurrentIndex(index)
            self.collectionView.scrollTo(index)

    def deleteRequested(self, uidList):
        if RemoveSoundsMessageBox(self, self.collection, self.database.getNamesFromUidList(uidList)).exec_():
            self.database.removeSounds(uidList, self.collection)

    def duplicateRequested(self, uid, sourceRow):
        if self.model.size() >= 1024:
            return
        preRow = sourceRow - 1
        postRow = sourceRow + 1
        while True:
            if postRow <= 1024:
                if not self.model.data(self.model.index(postRow, UidColumn), QtCore.Qt.DisplayRole):
                    target = postRow
                    break
                postRow += 1
            if preRow >= 0:
                if not self.model.data(self.model.index(preRow, UidColumn), QtCore.Qt.DisplayRole):
                    target = preRow
                    break
                preRow -= 1
        else:
            print('wtf!?')
            return
        newUid = self.database.duplicateSound(uid, self.collection, target)
        if newUid:
            newIndex = self.collectionView.model().match(self.model.index(0, UidColumn), QtCore.Qt.DisplayRole, newUid, flags=QtCore.Qt.MatchFixedString)[0]
            newIndex = newIndex.sibling(newIndex.row(), NameColumn)
            self.collectionView.setCurrentIndex(newIndex)
            self.collectionView.scrollTo(newIndex)

    def checkFilters(self, *args):
        print('cambio filtri', self.collection, self.model.size(), self.model)
        self.filterGroupBox.setEnabled(True if self.model.size() > 0 else False)
        if self.collectionView.horizontalHeader().isSortIndicatorShown() or \
            self.bankCombo.currentIndex() != 0 or \
            self.catCombo.currentIndex() != 0 or \
            self.filterNameEdit.text() or \
            self.filterTagsEdit.tags:
                self.emptySlotsChk.setEnabled(False)
                #TODO: is this necessary?!?
                self.cleanLibraryProxy.setFilter(False)
        else:
            self.emptySlotsChk.setEnabled(True)
            self.cleanLibraryProxy.setFilter(self.emptySlotsChk.isChecked())
        self.updateFilterCombos()

    def updateFilterCombos(self):
        banks = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0}
        cats = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0, 9: 0, 10: 0, 11: 0, 12: 0}
        totProgs = 0
        for row in range(self.model.rowCount()):
            index = self.model.index(row, LocationColumn)
            if not (index.isValid() and self.model.flags(index) & QtCore.Qt.ItemIsEnabled):
                continue
            totProgs += 1
            bank = index.data() >> 7
            banks[bank] += 1
        totCats = 0
        for row in range(self.bankProxy.rowCount()):
            index = self.bankProxy.index(row, LocationColumn)
            if not (index.isValid() and self.bankProxy.flags(index) & QtCore.Qt.ItemIsEnabled):
                continue
            totCats += 1
            cat = self.bankProxy.index(row, CatColumn).data()
            cats[cat] += 1

        self.bankCombo.setItemText(0, 'All ({})'.format(totProgs))
        for b in range(8):
            progs = banks[b]
            if progs:
                self.bankCombo.setItemText(b + 1, '{} ({})'.format(uppercase[b], progs))
                item = self.bankCombo.model().item(b + 1, 0)
                item.setFlags(item.flags() | QtCore.Qt.ItemIsEnabled)
            else:
                self.bankCombo.setItemText(b + 1, '{}'.format(uppercase[b]))
                item = self.bankCombo.model().item(b + 1, 0)
                item.setFlags((item.flags() | QtCore.Qt.ItemIsEnabled) ^ QtCore.Qt.ItemIsEnabled)

        self.catCombo.setItemText(0, 'All ({})'.format(totCats))
        for c in range(13):
            progs = cats[c]
            if progs:
                self.catCombo.setItemText(c + 1, '{} ({})'.format(categories[c], progs))
                item = self.catCombo.model().item(c + 1, 0)
                item.setFlags(item.flags() | QtCore.Qt.ItemIsEnabled)
            else:
                self.catCombo.setItemText(c + 1, '{}'.format(categories[c]))
                item = self.catCombo.model().item(c + 1, 0)
                item.setFlags((item.flags() | QtCore.Qt.ItemIsEnabled) ^ QtCore.Qt.ItemIsEnabled)

    def hideEvent(self, event):
        self.model.hoverDict.clear()


class LibraryWidget(BaseLibraryWidget):
    def __init__(self, parent):
        BaseLibraryWidget.__init__(self, 'ui/librarywidget.ui', parent)
#        loadUi('ui/librarywidget.ui', self)

#        self.filterTagsEdit.setModel(self.database.tagsModel)
#        self.filterNameEdit.setMinimumWidth(self.fontMetrics().width('AAAAAAAAAAAAAAAA'))
#        self.collectionView.tagsDelegate.tagClicked.connect(self.setTagFilter)

        self.collection = None
        self.editModeBtn.toggled.connect(self.setEditMode)

        self.mainLibraryProxy = MainLibraryProxy()
        self.mainLibraryProxy.setSourceModel(self.model)
        self.mainLibraryProxy.invalidated.connect(self.filtersInvalidated)
        self.nameProxy.setSourceModel(self.mainLibraryProxy)
        self.locationCombo.currentIndexChanged.connect(self.mainLibraryProxy.setFilter)
#        self.hideFactoryChk.toggled.connect(self.mainLibraryProxy.setFilter)

#        self.model = self.database.openCollection()
#        while self.model.canFetchMore():
#            self.model.fetchMore()
#        self.model.scheduledQueryUpdateSet.connect(self.scheduledQueryUpdateSet)

#        self.nameProxy = NameProxy()
#        self.nameProxy.setSourceModel(self.model)
#        self.nameProxy.setFilterKeyColumn(NameColumn)
#        self.nameProxy.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)
##        self.nameProxy.invalidated.connect(self.filtersInvalidated)
#        self.filterNameEdit.textChanged.connect(self.nameProxy.setFilterWildcard)
#
#        self.tagsProxy = TagsProxy()
#        self.tagsProxy.setSourceModel(self.nameProxy)
#        self.tagsProxy.invalidated.connect(self.filtersInvalidated)
#        self.filterTagsEdit.tagsChanged.connect(self.tagsProxy.setFilter)
#
#        self.collectionView.setModel(self.tagsProxy)
#        self.collectionView.setTagsModel(self.database.tagsModel)
#        self.collectionView.tagEditRequested.connect(self.tagEditRequested)
#        self.collectionView.tagEditMultiRequested.connect(self.tagEditMultiRequested)
#        self.collectionView.duplicateRequested.connect(self.duplicateRequested)
#        self.collectionView.deleteRequested.connect(self.deleteRequested)

    def clearFilters(self):
        self.filterNameEdit.setText('')
        self.filterTagsEdit.setTags()
        self.locationCombo.setCurrentIndex(0)
#        self.hideFactoryChk.setChecked(False)

    def focusUid(self, uid):
        self.clearFilters()
        res = self.collectionView.model().match(
            self.collectionView.model().index(0, UidColumn), 
            QtCore.Qt.DisplayRole, uid, flags=QtCore.Qt.MatchFixedString)
        if res:
            index = res[0]
            self.collectionView.setCurrentIndex(index)
            #for some reason, scrollTo doesn't always work fine in library (too many elements?)
            pos = index.row()
            tot = self.collectionView.model().rowCount()
            scrollValue = pos * self.collectionView.verticalScrollBar().maximum() / float(tot)
            self.collectionView.verticalScrollBar().setValue(int(scrollValue) + 2)

    def duplicateRequested(self, uid, source):
        if self.database.duplicateSound(uid):
            self.collectionView.scrollToBottom()
            self.collectionView.setCurrentIndex(self.model.index(self.model.rowCount() - 1, NameColumn))

    def deleteRequested(self, uidList):
        if DeleteSoundsMessageBox(self, self.database.getNamesFromUidList(uidList)).exec_():
            self.database.deleteSounds(uidList)

