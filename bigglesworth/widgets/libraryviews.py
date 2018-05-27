import json
from string import uppercase

from Qt import QtCore, QtGui, QtWidgets

from bigglesworth.parameters import categories
from bigglesworth.widgets import NameEdit, ContextMenu, CategoryDelegate, TagsDelegate
from bigglesworth.utils import loadUi, getSysExContents, sanitize
from bigglesworth.const import (TagsRole, UidColumn, LocationColumn, 
    NameColumn, CatColumn, TagsColumn, FactoryColumn, chr2ord, factoryPresets)
from bigglesworth.library import CleanLibraryProxy, BankProxy, CatProxy, NameProxy, TagsProxy
from bigglesworth.dialogs import SoundTagsEditDialog, MultiSoundTagsEditDialog, DeleteSoundsMessageBox, DropDuplicatesMessageBox
from bigglesworth.libs import midifile


class NameDelegate(QtWidgets.QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        lineEdit = NameEdit(parent)
        lineEdit.setText(index.data())
#        self.updateEditorGeometry(lineEdit, option, index)
        return lineEdit


#class CategoryDelegate(QtWidgets.QStyledItemDelegate):
#    def createEditor(self, parent, option, index):
#        combo = QtWidgets.QComboBox(parent)
#        combo.addItems(Parameters.parameterData.category.values)
#        combo.setCurrentIndex(index.data())
#        combo.view().activated.connect(lambda index, combo=combo: self.commit(index, combo))
#        combo.view().clicked.connect(lambda index, combo=combo: self.commit(index, combo))
#        combo.view().pressed.connect(lambda index, combo=combo: self.commit(index, combo))
##        self.updateEditorGeometry(combo, option, index)
#        return combo
#
#    def displayText(self, value, locale):
#        return Parameters.parameterData.category.values[value]
#
#    def editorEvent(self, event, model, option, index):
#        if self.parent().editTriggers() & self.parent().EditKeyPressed and \
#            event.type() == QtCore.QEvent.MouseButtonRelease and \
#            event.button() == QtCore.Qt.LeftButton:
#                self.parent().edit(index)
#                return True
#        return QtWidgets.QStyledItemDelegate.editorEvent(self, event, model, option, index)
#
##    implement this to all delegates to have single/double click editing for this only
##    def editorEvent(self, event, model, option, index):
##        return QtWidgets.QStyledItemDelegate.editorEvent(self, event, model, option, index)
#
#    def commit(self, index, combo):
#        combo.setCurrentIndex(index.row())
#        self.commitData.emit(combo)
#        self.closeEditor.emit(combo, self.NoHint)
#
#    def setModelData(self, widget, model, index):
#        model.setData(index, widget.currentIndex(), CatRole)
#        QtWidgets.QStyledItemDelegate.setModelData(self, widget, model, index)
#
#
#class TagsDelegate(QtWidgets.QStyledItemDelegate):
#    defaultBackground = QtCore.Qt.darkGray
#    defaultText = QtCore.Qt.white
#    tagsModel = None
#    tagClicked = QtCore.pyqtSignal(str)
#
#    def setTagsModel(self, tagsModel):
#        if self.tagsModel:
#            self.tagsModel.dataChanged.disconnect()
#        self.tagsModel = tagsModel
#        self.tagsModel.dataChanged.connect(self.updateTags)
#        self.updateTags()
#
#    def updateTags(self, *args):
#        self.tagColors = {}
#        for row in range(self.tagsModel.rowCount()):
#            tag = self.tagsModel.index(row, 0).data()
#            bgColor = getValidQColor(self.tagsModel.index(row, 1).data(), backgroundRole)
#            fgColor = getValidQColor(self.tagsModel.index(row, 2).data(), foregroundRole)
#            self.tagColors[tag] = bgColor, fgColor
#
#    def editorEvent(self, event, model, option, index):
#        if event.type() == QtCore.QEvent.MouseMove:
#            model.setData(index, event.pos(), HoverRole)
#        elif event.type() == QtCore.QEvent.Leave:
#            model.setData(index, False, HoverRole)
#        elif event.type() == QtCore.QEvent.MouseButtonPress and event.button() == QtCore.Qt.LeftButton and index.data():
#            self.selectTag(event, option, index)
##            self.showMenu(event, model, option, index)
#        return QtWidgets.QStyledItemDelegate.editorEvent(self, event, model, option, index)
#
#    def selectTag(self, event, option, index):
#        tags = json.loads(index.data())
#        if not tags:
#            return
#        self.initStyleOption(option, index)
#        pos = event.pos()
#        delta = 1
#        left = option.rect.x() + .5
#        height = option.fontMetrics.height() + 4
#        top = option.rect.y() + (option.rect.height() - height) * .5
#        for tag in tags:
#            width = option.fontMetrics.width(tag) + 8
#            rect = QtCore.QRectF(left + delta + 1, top, width, height)
#            if pos in rect:
#                self.tagClicked.emit(tag)
#                break
#            delta += width + 4
#
#    def showMenu(self, *args):
#        print(args)
#
#    def paint(self, painter, option, index):
#        self.initStyleOption(option, index)
#        if not option.text:
#            QtWidgets.QApplication.style().drawControl(QtWidgets.QStyle.CE_ItemViewItem, option, painter)
#            return
#        tags = json.loads(option.text)
#        option.text = ''
##        option.state |= QtWidgets.QStyle.State_Selected
##        option.state ^= QtWidgets.QStyle.State_Selected
#        QtWidgets.QApplication.style().drawControl(QtWidgets.QStyle.CE_ItemViewItem, option, painter)
##        tags = json.loads(index.data())
#        if not tags:
#            return
#        painter.save()
#        painter.setRenderHints(painter.Antialiasing)
#        painter.translate(.5, .5)
#
#        pos = index.data(HoverRole) if option.state & QtWidgets.QStyle.State_MouseOver else False
#        delta = 1
#        left = option.rect.x() + .5
#        height = option.fontMetrics.height() + 4
#        top = option.rect.y() + (option.rect.height() - height) * .5
#        stop = False
##        painter.setBrush(self.defaultBackground)
#        for tag in tags:
#            bg, fg = self.tagColors.get(tag, (self.defaultBackground, self.defaultText))
#            painter.setBrush(bg)
#            width = option.fontMetrics.width(tag) + 8
#            rect = QtCore.QRectF(left + delta + 1, top, width, height)
#            if pos and pos in rect:
#                painter.setPen(fg)
#            else:
#                painter.setPen(QtCore.Qt.transparent)
#            if rect.right() > option.rect.right() or rect.left() > option.rect.right():
#                stop = True
#                grad = QtGui.QLinearGradient(option.rect.right() - 10, 0, option.rect.right(), 0)
#                grad.setColorAt(0, bg)
#                grad.setColorAt(1, QtCore.Qt.transparent)
#                painter.setBrush(QtGui.QBrush(grad))
#                grad.setColorAt(0, painter.pen().color())
#                painter.setPen(QtGui.QPen(grad, 1))
#                painter.drawRoundedRect(rect, 2, 2)
#                grad.setColorAt(0, fg)
#                painter.setPen(QtGui.QPen(grad, 1))
#            else:
#                painter.drawRoundedRect(rect, 2, 2)
#                painter.setPen(fg)
#            painter.drawText(rect, QtCore.Qt.AlignCenter, tag)
#            delta += width + 4
#            if stop:
#                break
#        painter.restore()


class BaseLibraryView(QtWidgets.QTableView):
    dropIntoPen = QtCore.Qt.blue
    dropIntoBrush = QtGui.QBrush(QtGui.QColor(32, 128, 255, 96))
    tagsModel = None

    tagEditRequested = QtCore.pyqtSignal(object)
    tagEditMultiRequested = QtCore.pyqtSignal(object)
    duplicateRequested = QtCore.pyqtSignal(str, int)
    deleteRequested = QtCore.pyqtSignal(object)
    #blofeld index/buffer, collection, index, multi
    dumpFromRequested = QtCore.pyqtSignal(object, object, int, bool)
    #uid, blofeld index/buffer, multi
    dumpToRequested = QtCore.pyqtSignal(object, object, bool)
    dropEventSignal = QtCore.pyqtSignal()

    def __init__(self, *args, **kwargs):
        QtWidgets.QTableView.__init__(self, *args, **kwargs)
        self.horizontalHeader().setStretchLastSection(True)
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

    def soundDoubleClicked(self, index):
        if self.parent().editModeBtn.isChecked():
            return
        self.window().soundEditRequested.emit(index.sibling(index.row(), UidColumn).data(), self.parent().collection)

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

    def dragEnterEvent(self, event):
        self.dropSelectionIndexes = None
        if event.mimeData().hasFormat('text/uri-list'):
            data = event.mimeData().data('text/uri-list')
            urilist = unicode(data).replace('\r', '').strip().split('\n')
            if len(urilist) != 1 or urilist[0][-4:] not in ('.syx', '.mid'):
                event.ignore()
                return
            sysex = getSysExContents(urilist[0])
            if sysex:
                event.accept()
                self.externalFileDropContents = sysex
            else:
                event.ignore()
        elif event.mimeData().hasFormat('application/x-qabstractitemmodeldatalist') and event.source():
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
        mimeData.setData('bigglesworth/collectiondrag', byteArray)
        byteArray.clear()
        stream = QtCore.QDataStream(byteArray, QtCore.QIODevice.WriteOnly)
        stream.writeBool(False)
        mimeData.setData('bigglesworth/dragmode', byteArray)

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
        #TODO: fix for scoll page/home/end
        elif self.verticalScrollBar().isVisible():
            if event.matches(QtGui.QKeySequence.MoveToNextPage):
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
                    nextIndex = self.model().index(self.currentIndex().row() + pageSize, 2)
                while nextIndex.row() < self.model().rowCount() - 1:
                    nextIndex = self.model().index(nextIndex.row() + 1, 2)
                    if nextIndex.flags() & QtCore.Qt.ItemIsEnabled:
                        self.setCurrentIndex(nextIndex)
                        self.scrollTo(nextIndex)
                        self.scrollTo(nextIndex)
                        return
                else:
                    lastIndex = self.model().index(self.model().rowCount() - 1, 2)
                    while not lastIndex.flags() & QtCore.Qt.ItemIsEnabled:
                        lastIndex = self.model().index(lastIndex.row() - 1, 2)
                    self.setCurrentIndex(lastIndex)
                    self.scrollTo(lastIndex)
                    return
            elif event.matches(QtGui.QKeySequence.MoveToPreviousPage):
                pre = self.verticalScrollBar().value()
                QtWidgets.QTableView.keyPressEvent(self, event)
                post = self.verticalScrollBar().value()
                if pre != post:
                    return
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
                        self.setCurrentIndex(nextIndex)
                        return
                else:
                    lastIndex = self.model().index(self.model().rowCount() + 1, 2)
                    while not lastIndex.flags() & QtCore.Qt.ItemIsEnabled:
                        lastIndex = self.model().index(lastIndex.row() + 1, 2)
                    self.setCurrentIndex(lastIndex)
                    self.scrollTo(lastIndex)
                    return
            elif event.matches(QtGui.QKeySequence.MoveToEndOfLine):
                lastIndex = self.model().index(self.model().rowCount() - 1, 2)
                while not lastIndex.flags() & QtCore.Qt.ItemIsEnabled:
                    lastIndex = self.model().index(lastIndex.row() - 1, 2)
                if not self.currentIndex().isValid() or self.currentIndex().row() != lastIndex.row():
                    self.setCurrentIndex(lastIndex)
                    self.scrollTo(lastIndex)
                else:
                    if self.verticalScrollBar().value() < self.verticalScrollBar().maximum():
                        self.scrollToBottom()
                    else:
                        self.setCurrentIndex(lastIndex)
                        self.scrollTo(lastIndex)
                return
            elif event.matches(QtGui.QKeySequence.MoveToStartOfLine):
                firstIndex = self.model().index(0, 2)
                while not firstIndex.flags() & QtCore.Qt.ItemIsEnabled:
                    firstIndex = self.model().index(firstIndex.row() + 1, 2)
                if not self.currentIndex().isValid() or self.currentIndex().row() != firstIndex.row():
                    self.setCurrentIndex(firstIndex)
                    self.scrollTo(firstIndex)
                else:
                    if self.verticalScrollBar().value() > 0:
                        self.scrollToTop()
                    else:
                        self.setCurrentIndex(firstIndex)
                        self.scrollTo(firstIndex)
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
        QtWidgets.QTableView.setModel(self, model)
        model.layoutChanged.connect(self.restoreLayout)
        self.restoreLayout()

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
#            return
        else:
            valid = True
        menu = ContextMenu(self)
        menu.setSeparatorsCollapsible(False)
        nameIndex = index.sibling(index.row(), NameColumn)
        name = nameIndex.data().rstrip()
        uid = index.sibling(index.row(), UidColumn).data()

        inConn, outConn = QtWidgets.QApplication.instance().connections

        if not selRows or not valid:
            menu.addSeparator().setText('Empty slot')
            dumpMenu = menu.addMenu('Dump')
            if not all((inConn, outConn)):
                dumpMenu.setEnabled(False)
            dumpMenu.setSeparatorsCollapsible(False)
            dumpMenu.addSeparator().setText('Receive')
            dumpFromSoundBuffer = dumpMenu.addAction('Dump from Sound Edit Buffer')
            dumpFromSoundBuffer.triggered.connect(lambda: self.dumpFromRequested.emit(None, self.collection, index.row(), False))
            pos = '{}{:03}'.format(uppercase[index.row() >> 7], (index.row() & 127) + 1)
            dumpFromIndex = dumpMenu.addAction('Dump from {}'.format(pos))
            dumpFromIndex.triggered.connect(lambda: self.dumpFromRequested.emit(index.row(), self.collection, index.row(), False))
            dumpFromMultiMenu = dumpMenu.addMenu('Dump from Multi Edit Buffer')
            for part in range(16):
                dumpFromMultiAction = dumpFromMultiMenu.addAction('Part {}'.format(part + 1))
                dumpFromMultiAction.triggered.connect(lambda _, part=part: self.dumpFromRequested.emit(part, self.collection, index.row(), True))

        elif len(selRows) == 1:
            if selRows[0].row() != index.row():
                index = selRows[0]
            menu.addSeparator().setText(name)
            soundEditAction = menu.addAction('Open in the sound editor')
            soundEditAction.triggered.connect(lambda _, uid=uid: self.window().soundEditRequested.emit(uid, self.collection))
            editTagsAction = menu.addAction('Edit tags...')
            editTagsAction.triggered.connect(lambda _, index=index: self.tagEditRequested.emit(index))

            dumpMenu = menu.addMenu('Dump')
            if not outConn:
                dumpMenu.setEnabled(False)
            dumpMenu.setSeparatorsCollapsible(False)
            sendSep = dumpMenu.addSeparator()
            sendSep.setText('Send')

            duplicateAction = menu.addAction(QtGui.QIcon.fromTheme('edit-copy'), 'Duplicate')
            if isinstance(self, CollectionTableView):
                recSep = dumpMenu.insertSeparator(sendSep)
                recSep.setText('Receive')
                dumpFromSoundBuffer = QtWidgets.QAction('Dump from Sound Edit Buffer', dumpMenu)
                dumpFromSoundBuffer.triggered.connect(lambda: self.dumpFromRequested.emit(None, self.collection, index.row(), False))
                pos = '{}{:03}'.format(uppercase[index.row() >> 7], (index.row() & 127) + 1)
                dumpFromIndex = QtWidgets.QAction('Dump from {}'.format(pos), dumpMenu)
                dumpFromIndex.triggered.connect(lambda: self.dumpFromRequested.emit(index.row(), self.collection, index.row(), False))
                dumpMenu.insertActions(sendSep, [dumpFromSoundBuffer, dumpFromIndex])
                dumpFromMultiMenu = QtWidgets.QMenu('Dump from Multi Edit Buffer', dumpMenu)
                dumpMenu.insertMenu(sendSep, dumpFromMultiMenu)

                dumpToSoundBuffer = dumpMenu.addAction('Dump to Sound Edit Buffer')
                dumpToSoundBuffer.triggered.connect(lambda: self.dumpToRequested.emit(uid, None, False))
                dumpToIndex = dumpMenu.addAction('Dump to {}'.format(pos))
                dumpToIndex.triggered.connect(lambda: self.dumpToRequested.emit(uid, index.row(), False))
                dumpToMultiMenu = dumpMenu.addMenu('Dump to Multi Edit Buffer')

                for part in range(16):
                    dumpFromMultiAction = dumpFromMultiMenu.addAction('Part {}'.format(part + 1))
                    dumpFromMultiAction.triggered.connect(lambda _, part=part: self.dumpFromRequested.emit(part, self.collection, index.row(), True))
                    dumpToMultiAction = dumpToMultiMenu.addAction('Part {}'.format(part + 1))
                    dumpToMultiAction.triggered.connect(lambda _, part=part: self.dumpToRequested.emit(uid, part, True))

                if not inConn:
                    for w in (recSep, dumpFromSoundBuffer, dumpFromIndex, dumpFromMultiMenu):
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
        else:
            uidList = [idx.sibling(idx.row(), UidColumn).data(QtCore.Qt.DisplayRole) for idx in selRows]
            menu.addSeparator().setText('{} sounds selected'.format(len(selRows)))
            editTagsMultiAction = menu.addAction('Edit tags...')
            editTagsMultiAction.triggered.connect(lambda: self.tagEditMultiRequested.emit(selRows))
            if isinstance(self, CollectionTableView):
                deleteAction = menu.addAction(QtGui.QIcon.fromTheme('edit-delete'), 'Remove from "{}"'.format(self.collection))
                deleteAction.setStatusTip('Remove the selected sounds from the current collection only')
                if not self.editable:
                    deleteAction.setEnabled(False)
            else:
                deleteAction = menu.addAction(QtGui.QIcon.fromTheme('edit-delete'), 'Delete {} sounds'.format(len(selRows)))
                deleteAction.setStatusTip('Delete the selected sounds from the library and any collection')
            deleteAction.triggered.connect(lambda: self.deleteRequested.emit(uidList))
        return menu, index, name, uid

class LibraryTableView(BaseLibraryView):
    def __init__(self, *args, **kwargs):
        BaseLibraryView.__init__(self, *args, **kwargs)
        self.verticalHeader().setVisible(False)
        self.layoutChangeBuffer = None

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
            rows = self.externalFileDropContents
            print(rows)
            event.accept()
#            BaseLibraryView.dragMoveEvent(self, event)


class CollectionTableView(BaseLibraryView):
    dropIntoPen = QtCore.Qt.blue
    dropIntoBrush = QtGui.QBrush(QtGui.QColor(32, 128, 255, 96))

    def __init__(self, *args, **kwargs):
        BaseLibraryView.__init__(self, *args, **kwargs)
        self.setDropIndicatorShown(False)
        self.autoScrollTimer = QtCore.QTimer()
        self.autoScrollDelta = 0
        self.autoScrollAccel = 0
        self.autoScrollTimer.timeout.connect(self.doAutoScroll)
        self.setAutoScroll(False)
        self.dropIndicatorPosition = self.OnViewport

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
        menu.exec_(self.viewport().mapToGlobal(pos))

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
        if event.mimeData().hasFormat('bigglesworth/collectiondrag'):
            data = event.mimeData().data('bigglesworth/collectiondrag')
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
        event.acceptProposedAction()
        QtWidgets.QTableView.dropEvent(self, event)
#        self.externalFileDropContents = None
#        self.dropSelectionIndexes = None
        BaseLibraryView.dropEvent(self, event)

    def dropFromLibrary(self, uidList, targetRows, overwrite):
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
#            for d in duplicates:

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

class Fake:

    def dragMoveEvent(self, event):
        QtWidgets.QTableView.dragMoveEvent(self, event)
        rows = self.getSelectedDragRows(event)
        if event.source() == self:
            currentIndex = self.indexAt(event.pos())
            if self.dropIndicatorPosition() == self.OnItem:
                if not self.selectRows(currentIndex, rows, event.keyboardModifiers()):
                    self.dropSelectionRect = QtCore.QRect()
                    event.ignore()
            elif self.dropIndicatorPosition() == self.OnViewport:
                self.dropSelectionRect = QtCore.QRect()
                event.ignore()
            else:
                y = self.rowViewportPosition(currentIndex.row())
                if self.dropIndicatorPosition() == self.BelowItem:
                    y += self.rowHeight(currentIndex.row()) - 1
                    height = -1
                height = 1
                width = sum(self.columnWidth(c) for c in range(self.model().columnCount()))
                self.dropSelectionRect = QtCore.QRect(self.columnViewportPosition(0), y, width, height)

    def selectRows(self, index, rows, modifiers):
        if index.row() in rows:
            return False
        if modifiers ==  QtCore.Qt.ShiftModifier:
            if index.row() + len(rows) > self.model().rowCount():
                if rows[-1] + len(rows) + 1 > self.model().rowCount():
                    return False
                startRow = self.model().rowCount() - len(rows)
            elif index.row() + len(rows) - 1 in rows:
                return False
            else:
                startRow = index.row()
            endRow = startRow + len(rows)
        else:
            startRow = index.row()
            endRow = startRow + 1
        y = self.rowViewportPosition(startRow)
        height = sum(self.rowHeight(r) for r in range(startRow, endRow))
        width = sum(self.columnWidth(c) for c in range(self.model().columnCount()))
        self.dropSelectionRect = QtCore.QRect(self.columnViewportPosition(0), y, width, height)
        return True

    def dragLeaveEvent(self, event):
        self.dropSelectionRect = QtCore.QRect()
        QtWidgets.QTableView.dragLeaveEvent(self, event)

    def dropEvent(self, event):
        self.dropSelectionRect = QtCore.QRect()
        if event.source() == self:
            self.internalDropEvent(event)
            return
        QtWidgets.QTableView.dropEvent(self, event)

    def getSelectedDragRows(self, event):
        stream = QtCore.QDataStream(event.mimeData().data('application/x-qabstractitemmodeldatalist'))
        rows = set()
        while not stream.atEnd():
            rows.add(stream.readInt32())
            #column
            stream.readInt32()
            #read item role data
            [(stream.readInt32(), stream.readQVariant()) for role in range(stream.readInt32())]
        return sorted(rows)

    def internalDropEvent(self, event):
        self.dropSelectionRect = QtCore.QRect()
        originalTargetRowNumber = targetRowNumber = self.indexAt(event.pos()).row()
        rows = self.getSelectedDragRows(event)
        if self.dropIndicatorPosition() == self.OnItem:
            self.internalDropIntoEvent(event, rows, targetRowNumber)
            return
        if self.dropIndicatorPosition() == self.AboveItem:
            if rows[-1] == targetRowNumber - 1:
                event.ignore()
                return
        elif self.dropIndicatorPosition() == self.BelowItem:
            if rows[0] == targetRowNumber + 1:
                event.ignore()
                return
            originalTargetRowNumber += 1
            targetRowNumber += 1
        if targetRowNumber > rows[-1]:
            targetRowNumber -= len(rows)
        event.accept()
        self.model().rowsAboutToBeMoved.emit(rows[0], rows[-1], originalTargetRowNumber)
        sourceRows = [self.model().takeRow(rows[0]) for row in rows]
        for row in reversed(sourceRows):
            self.model().insertRow(targetRowNumber, row)
        self.model().rowsMoved.emit(rows[0], rows[-1], originalTargetRowNumber)

    def internalDropIntoEvent(self, event, rows, targetRowNumber):
        msgBox = DropOverMessageBox(self)
        if targetRowNumber == rows[-1] + 1:
            msgBox.removeButton(msgBox.beforeButton)
        elif targetRowNumber == rows[0] - 1:
            msgBox.removeButton(msgBox.afterButton)
        res = msgBox.exec_()
        if res == msgBox.Cancel:
            event.ignore()
            return
        targetRowNumber = targetRowNumber
        if res == 0:
            originalTargetRowNumber = targetRowNumber
            if originalTargetRowNumber + len(rows) > self.model().rowCount():
                originalTargetRowNumber = self.model().rowCount() - len(rows)
            if targetRowNumber > rows[-1]:
                sourceRowNumber = rows[0]
                targetRowNumber -= len(rows)
            else:
                sourceRowNumber = rows[-1]
            sourceRows = [self.model().takeRow(rows[0]) for row in rows]
            if event.keyboardModifiers() == QtCore.Qt.ShiftModifier:
                if targetRowNumber + len(rows) > self.model().rowCount():
                    targetRowNumber = self.model().rowCount() - len(rows)
                if targetRowNumber < rows[0]:
                    sourceRowNumber = rows[0]
                targetRows = [self.model().takeRow(targetRowNumber) for row in rows]
            else:
                targetRows = [self.model().takeRow(targetRowNumber)]
            self.model().rowsAboutToBeSwapped.emit(rows[0], rows[-1], originalTargetRowNumber, len(targetRows))
            for row in reversed(sourceRows):
                self.model().insertRow(targetRowNumber, row)
            for row in reversed(targetRows):
                self.model().insertRow(sourceRowNumber, row)
            event.accept()
            self.model().rowsSwapped.emit(rows[0], rows[-1], originalTargetRowNumber, len(targetRows))
            return
        self.model().rowsAboutToBeMoved.emit(rows[0], rows[-1], targetRowNumber)
        sourceRows = [self.model().takeRow(rows[0]) for row in rows]
        if res == 1:
            if targetRowNumber > rows[-1]:
                targetRowNumber -= len(rows)
            for row in reversed(sourceRows):
                self.model().insertRow(targetRowNumber, row)
        elif res == 2:
            if targetRowNumber > rows[-1]:
                targetRowNumber -= len(rows)
            targetRowNumber += 1
            for row in reversed(sourceRows):
                self.model().insertRow(targetRowNumber, row)
        event.accept()
        self.model().rowsMoved.emit(rows[0], rows[-1], targetRowNumber)

    def paintEvent(self, event):
        QtWidgets.QTableView.paintEvent(self, event)
        qp = QtGui.QPainter(self.viewport())
        qp.setPen(self.dropIntoPen)
        qp.setBrush(self.dropIntoBrush)
        qp.drawRect(self.dropSelectionRect)


class BaseLibraryWidget(QtWidgets.QWidget):
    #blofeld index/buffer, collection, index, multi
    dumpFromRequested = QtCore.pyqtSignal(object, object, int, bool)
    #uid, blofeld index/buffer, multi
    dumpToRequested = QtCore.pyqtSignal(object, object, bool)

    def __init__(self, uiPath, parent, collection=None):
        QtWidgets.QWidget.__init__(self, parent)
        loadUi(uiPath, self)
        self.database = parent.database

        self.filterTagsEdit.setModel(self.database.tagsModel)
        self.filterNameEdit.setMinimumWidth(self.fontMetrics().width('AAAAAAAAAAAAAAAA'))
        self.collectionView.tagsDelegate.tagClicked.connect(self.setTagFilter)

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
        self.collectionView.deleteRequested.connect(self.deleteRequested)

        self.collectionView.dumpToRequested.connect(self.dumpToRequested)
        self.collectionView.dumpFromRequested.connect(self.dumpFromRequested)

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
        self.collectionView.database = parent.database
        self.collectionView.collection = collection

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

        self.updateFilterCombos()

    def deleteRequested(self, uidList):
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
        if self.bankCombo.currentIndex() != 0 or \
            self.catCombo.currentIndex() != 0 or \
            self.filterNameEdit.text() or \
            self.filterTagsEdit.tags:
                self.emptySlotsChk.setEnabled(False)
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

    def duplicateRequested(self, uid, source):
        if self.database.duplicateSound(uid):
            self.collectionView.scrollToBottom()
            self.collectionView.setCurrentIndex(self.model.index(self.model.rowCount() - 1, NameColumn))

    def deleteRequested(self, uidList):
        if DeleteSoundsMessageBox(self, self.database.getNamesFromUidList(uidList)).exec_():
            self.database.deleteSounds(uidList)

