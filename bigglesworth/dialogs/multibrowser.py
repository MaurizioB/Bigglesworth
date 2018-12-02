#!/usr/bin/env python2.7
# *-* encoding: utf-8 *-*

import sys, os
from itertools import chain

os.environ['QT_PREFERRED_BINDING'] = 'PyQt4'

from Qt import QtCore, QtGui, QtWidgets, QtSql

if __name__ == '__main__':
    QtCore.pyqtSignal = QtCore.Signal
    QtCore.pyqtSlot = QtCore.Slot
    sys.path.append('../..')
    #this will go away as soon as random.py is renamed in dialogs/, you idiot!
    sys.path.remove('/home/mauriziob/data/code/blofeld/bigglesworth/dialogs')
    sys.path.remove('')
    from PyQt4.uic import loadUi
    from PyQt4.QtGui import QIdentityProxyModel, QStyleOptionViewItemV4
    QtWidgets.QStyleOptionViewItemV4 = QStyleOptionViewItemV4
    QtCore.QIdentityProxyModel = QIdentityProxyModel
    uiPath = '../'
else:
    from bigglesworth.utils import loadUi
    uiPath = ''

from bigglesworth.multi import (MultiSetModel, MultiQueryModel, MultiNameRole, MultiIndexRole, MultiDataRole)
from bigglesworth.utils import sanitize
from bigglesworth.dialogs.utils import NameValidator


class MultiDelegate(QtWidgets.QStyledItemDelegate):
    disabledPen = QtGui.QPen(QtGui.QColor(QtCore.Qt.lightGray))
    disabledBrush = QtGui.QBrush(QtGui.QColor(224, 224, 224))
    enabledPen = QtGui.QColor(QtCore.Qt.darkGray)
    enabledBrush = QtGui.QColor(QtCore.Qt.lightGray)
    colors = ((disabledPen, disabledBrush), (enabledPen, enabledBrush))

    def paint(self, qp, option, index):
#        option = QtWidgets.QStyleOptionViewItemV4(option)
        self.initStyleOption(option, index)
        row = index.row()
        if not row % 8:
            option.rect.setTop(option.rect.bottom() - self.defaultHeight + 2)
        if not option.state & QtWidgets.QStyle.State_Selected:
            hMargin = option.widget.style().pixelMetric(QtWidgets.QStyle.PM_FocusFrameHMargin, option, option.widget)
            vMargin = option.widget.style().pixelMetric(QtWidgets.QStyle.PM_FocusFrameVMargin, option, option.widget)
            indexSize = option.fontMetrics.boundingRect('{:03}'.format(index.data(MultiIndexRole))).size()
            qp.save()
            qp.translate(.5, .5)
            pen, brush = self.colors[int(option.state & QtWidgets.QStyle.State_On)]
            qp.setPen(pen)
            qp.setBrush(brush)
            qp.setRenderHints(qp.Antialiasing)
            indexRect = QtCore.QRect(
                option.rect.x() + hMargin / 2, 
                option.rect.y() + vMargin / 2, 
                indexSize.width() + hMargin + 1, 
                indexSize.height() + vMargin)
            qp.drawRoundedRect(indexRect, 2, 2)
            qp.restore()
        QtWidgets.QStyledItemDelegate.paint(self, qp, option, index)
#        option.widget.style().drawControl(QtWidgets.QStyle.CE_ItemViewItem, option, qp)

    def updateEditorGeometry(self, editor, option, index):
#        option = QtWidgets.QStyleOptionViewItemV4(option)
        self.initStyleOption(option, index)
        row = index.row()
        if not row % 8:
            option.rect.setTop(option.rect.bottom() - self.defaultHeight + 1)
        QtWidgets.QStyledItemDelegate.updateEditorGeometry(self, editor, option, index)

    def createEditor(self, parent, option, index):
        editor = QtWidgets.QStyledItemDelegate.createEditor(self, parent, option, index)
        editor.setMaxLength(16)
        editor.setValidator(NameValidator())
        return editor

    def setEditorData(self, editor, index):
        try:
            editor.setText(index.data(MultiNameRole))
        except:
            pass

    def setModelData(self, editor, model, index):
        model.setData(index, editor.text(), MultiNameRole)


class SelectionModel(QtCore.QItemSelectionModel):
    def __init__(self, model):
        QtCore.QItemSelectionModel.__init__(self, model)
#        self.currentColumnChanged.connect(self.columnChanged)
#        self.currentRowChanged.connect(self.limitSelection)
        self.currentColumn = None

    def select(self, selection, flags):
        #ensure that we only select items from a single column
        if not isinstance(selection, QtCore.QModelIndex):
#            print(bool(flags & QtCore.QItemSelectionModel.Clear))
            column = self.currentIndex().column()
            selected = self.selectedIndexes()
            if flags & QtCore.QItemSelectionModel.Clear or (selected and column not in [i.column() for i in selected]):
                indexes = [self.currentIndex()]
            else:
                indexes = set(i for i in selection.indexes() + selected if i.column() == column)
                indexes = sorted(indexes, key=lambda i: i.row())
            if indexes:
                selection = QtCore.QItemSelection(indexes[0], indexes[-1])
        QtCore.QItemSelectionModel.select(self, selection, flags)



class MultiTableView(QtWidgets.QTableView):
    dropIntoPen = QtCore.Qt.blue
    dropIntoBrush = QtGui.QBrush(QtGui.QColor(32, 128, 255, 96))
    dropLinePen = QtGui.QPen(QtCore.Qt.blue, 2)

    def __init__(self, *args, **kwargs):
        QtWidgets.QTableView.__init__(self, *args, **kwargs)
        self.defaultHeight = self.fontMetrics().height() * 1.5
        self.verticalHeader().setDefaultSectionSize(self.defaultHeight)
        self.verticalHeader().setResizeMode(QtWidgets.QHeaderView.Fixed)
        self.horizontalHeader().setResizeMode(QtWidgets.QHeaderView.Stretch)
        delegate = MultiDelegate(self)
        delegate.defaultHeight = self.defaultHeight
        self.setItemDelegate(delegate)
        self.currentDropTargetRange = self.currentDropTargetIndexes = None
        self._dropIndicatorPosition = self.OnViewport

    def resetSizes(self):
        self.horizontalHeader().setMinimumSectionSize(self.fontMetrics().width(' 000 Multi Init '))
        self.verticalHeader().resizeSection(8, self.defaultHeight * 2)
        self.verticalHeader().resizeSection(16, self.defaultHeight * 2)
        self.verticalHeader().resizeSection(24, self.defaultHeight * 2)

    def getIndexFromPos(self, pos, setIndicator=False):
        index = self.indexAt(pos)
        if not setIndicator:
            self._dropIndicatorIndex = None
            self._dropIndicatorPosition = self.OnItem
            if index.isValid() and pos in self.visualRect(index):
                return index
            return
        self._dropIndicatorPosition = self.OnViewport
        if index.isValid():
            self._dropIndicatorIndex = index
            rect = self.visualRect(index)
            margin = sanitize(2, rect.height() / 5.5, 12)
            if pos.y() < rect.top() + margin:
                self._dropIndicatorPosition = self.AboveItem
            elif rect.bottom() - pos.y() < margin:
                self._dropIndicatorPosition = self.BelowItem
            elif pos in rect:
                self._dropIndicatorPosition = self.OnItem
            return index
        self._dropIndicatorIndex = None

    def createNew(self, index, edit=True):
        self.model().setData(index, 'Init Multi', MultiNameRole)
        if edit:
            QtCore.QTimer.singleShot(0, lambda: [self.setCurrentIndex(index), self.edit(index)])
        else:
            QtCore.QTimer.singleShot(0, lambda: self.setCurrentIndex(index))

    def clearIndexes(self):
        indexes = self.sender().data()
        if len(indexes) == 1:
            message = 'Do you want to clear slot {}?<br/>' \
                'The operation cannot be undone.'.format(indexes[0].data(MultiIndexRole) + 1)
        else:
            message = 'Do you want to clear the following slots?<br/>'
            if len(indexes) <= 10:
                count = 10
            else:
                count = 8
            message += ', '.join('{} ({})'.format(index.data(MultiIndexRole) + 1, index.data(MultiNameRole).strip()) for index in indexes[:count])
            if len(indexes) > 10:
                message += ', and {} more...'.format(len(indexes) - 8)
        if QtWidgets.QMessageBox.question(self, 'Clear Multi slots', message, 
            QtWidgets.QMessageBox.Ok|QtWidgets.QMessageBox.Cancel) != QtWidgets.QMessageBox.Ok:
                return
        self.model().clearMultis(indexes)

    def getDragIndexes(self, event):
#        mod = QtGui.QStandardItemModel()
#        mod.dropMimeData(event.mimeData(), QtCore.Qt.CopyAction, 0, 0, QtCore.QModelIndex())
        stream = QtCore.QDataStream(event.mimeData().data('application/x-qabstractitemmodeldatalist'))
        indexes = set()
        while not stream.atEnd():
            #ignore row
            stream.readInt32()
            indexes.add(stream.readInt32())
            #read item role data
            [(stream.readInt32(), stream.readQVariant()) for role in range(stream.readInt32())]
        return sorted(indexes)

    def setModel(self, model):
        if self.model():
            self.model().layoutChanged.disconnect(self.resetSizes)
        QtWidgets.QTableView.setModel(self, model)
        self.setSelectionModel(SelectionModel(model))
        model.layoutChanged.connect(self.resetSizes)
        self.resetSizes()

    def getValidSiblingHorizontal(self, index, direction=1):
        row = index.row()
        column = index.column()
        if not row:
            indexRange = range(32)
        elif row == 31:
            indexRange = range(32, -1, -1)
        else:
            preRange = range(row - 1, -1,  -1)
            postRange = range(row, row + len(preRange))
            indexRange = list(chain.from_iterable(zip(postRange, preRange)))
            if indexRange[-1] == 0:
                #using == for readability: 
                #if the last value is 0 it means that the postRange is incomplete
                indexRange.extend(range(indexRange[-2], 32))
            else:
                indexRange.extend(range(indexRange[-1], -1, -1))
            print(preRange, postRange, indexRange)

        while column <= 3:
            column += direction
            columnRange = iter(indexRange)
            while True:
                newIndex = index.sibling(columnRange.next(), column)
                if newIndex.flags() & QtCore.Qt.ItemIsEditable:
                    return newIndex

    def getValidSiblingVertical(self, index, direction=1):
        multiIndex = index.data(MultiIndexRole)
        while 0 <= multiIndex <= 127:
            multiIndex += direction
            index = self.model().indexFromMultiIndex(multiIndex)
            if index.isValid() and index.flags() & QtCore.Qt.ItemIsEditable:
                return index

    def moveCursor(self, action, modifiers):
        index = QtWidgets.QTableView.moveCursor(self, action, modifiers)
        if index.isValid() and index == self.currentIndex():
            if action == self.MoveRight and index.column() < 3:
                newIndex = self.getValidSiblingHorizontal(index)
                if newIndex:
                    index = newIndex
            elif action == self.MoveLeft and index.column():
                newIndex = self.getValidSiblingHorizontal(index, -1)
                if newIndex:
                    index = newIndex
            elif action == self.MoveDown and index.column() < 3:
                newIndex = self.getValidSiblingVertical(index)
                if newIndex:
                    index = newIndex
            elif action == self.MoveUp and index.column():
                newIndex = self.getValidSiblingVertical(index, -1)
                if newIndex:
                    index = newIndex
            elif action == self.MoveHome and self.currentIndex().isValid():
                index = self.currentIndex()
                newIndex = self.getValidSiblingHorizontal(index.sibling(index.row(), 1), -1)
                if newIndex:
                    index = newIndex
        elif not index.isValid():
            #moving to end sometimes makes index invalid!
            if action == self.MoveEnd:
                #index.sibling cannot be used if index is not valid!!!
                newIndex = self.getValidSiblingHorizontal(self.currentIndex().sibling(self.currentIndex().row(), 2))
                if newIndex:
                    index = newIndex
        return index

    def visualRect(self, index):
        rect = QtWidgets.QTableView.visualRect(self, index).adjusted(-1, -1, 1, 1)
        if index.row() in (8, 16, 24):
            rect.adjust(0, self.defaultHeight, 0, 0)
        return rect

    def contextMenuEvent(self, event):
        index = self.getIndexFromPos(event.pos())
        if not index:
            return
        menu = QtWidgets.QMenu()
        if index.flags() & QtCore.Qt.ItemIsEditable:
            editAction = menu.addAction(QtGui.QIcon.fromTheme('document-edit'), 
                'Rename {}'.format(index.data(MultiNameRole)))
            editAction.triggered.connect(lambda: self.edit(index))
            menu.addSeparator()
            selected = self.selectedIndexes()
            if len(selected) == 1:
                deleteAction = menu.addAction(QtGui.QIcon.fromTheme('edit-delete'), 
                    'Clear Multi slot {}'.format(index.data(MultiIndexRole) + 1))
            else:
                deleteAction = menu.addAction(QtGui.QIcon.fromTheme('edit-delete'), 
                    'Clear {} slots'.format(len(selected)))
            deleteAction.setData(selected)
            deleteAction.triggered.connect(self.clearIndexes)
        else:
            self.clearSelection()
            newAction = menu.addAction(QtGui.QIcon.fromTheme('document-new'), 
                'Create new Multi for slot {}'.format(index.data(MultiIndexRole) + 1))
            newAction.triggered.connect(lambda: self.createNew(index, False))
        menu.exec_(QtGui.QCursor.pos())

    def viewportEvent(self, event):
        if event.type() in (QtCore.QEvent.HoverMove, QtCore.QEvent.HoverEnter):
            if not self.getIndexFromPos(event.pos()):
                return False
        return QtWidgets.QTableView.viewportEvent(self, event)

    def mouseDoubleClickEvent(self, event):
        index = self.getIndexFromPos(event.pos())
        if not index:
            return
        if not index.flags() & QtCore.Qt.ItemIsEditable:
            self.createNew(index)
        else:
            QtWidgets.QTableView.mouseDoubleClickEvent(self, event)

    def mousePressEvent(self, event):
        if not self.getIndexFromPos(event.pos()):
            self.startPos = None
            return
        self.startPos = event.pos()
        QtWidgets.QTableView.mousePressEvent(self, event)

    def dragEnterEvent(self, event):
        self._dropIndicatorPosition = self.OnViewport
        QtWidgets.QTableView.dragEnterEvent(self, event)

    def dragMoveEvent(self, event):
        if not event.mimeData().hasFormat('application/x-qabstractitemmodeldatalist'):
            return event.ignore()
        pos = event.pos()
        scrollMargin = self.autoScrollMargin()
        geometry = self.viewport().geometry()
        if pos not in geometry.adjusted(scrollMargin, scrollMargin, -scrollMargin, -scrollMargin):
            if pos.x() <= geometry.left() + scrollMargin:
                self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - 1)
            elif pos.x() >= geometry.right() - scrollMargin:
                self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() + 1)
            elif pos.y() <= geometry.top() + scrollMargin:
                self.verticalScrollBar().setValue(self.verticalScrollBar().value() - 1)
            elif pos.y() >= geometry.bottom() - scrollMargin:
                self.verticalScrollBar().setValue(self.verticalScrollBar().value() + 1)
        move = event.keyboardModifiers() != QtCore.Qt.ShiftModifier
        swap = event.keyboardModifiers() == QtCore.Qt.ControlModifier
        updateRect = QtWidgets.QTableView.visualRect(self, self._dropIndicatorIndex) if self._dropIndicatorIndex else QtCore.QRect()
        index = self.getIndexFromPos(pos, setIndicator=move)
        if not index:
            if self.currentDropTargetIndexes:
                for index in self.currentDropTargetIndexes:
                    updateRect |= self.visualRect(index)
            if not self._dropIndicatorIndex:
                self.currentDropTargetRange = self.currentDropTargetIndexes = None
            self.viewport().update(updateRect)
            return event.accept() if self._dropIndicatorIndex else event.ignore()

        if swap:
            event.setDropAction(QtCore.Qt.LinkAction)
        elif move:
            event.setDropAction(QtCore.Qt.MoveAction)
        else:
            event.setDropAction(QtCore.Qt.CopyAction)

        dragIndexes = self.getDragIndexes(event)
        count = len(dragIndexes)
        targetIndex = index.data(MultiIndexRole)
        #do not use 127!
        if targetIndex + count > 128:
            targetIndex = 128 - count
        dropTargetRange = range(targetIndex, targetIndex + count)
        dropTargetIndexes = self.model().indexListFromMultiIndexes(dropTargetRange)

        if set(dragIndexes) & set(dropTargetRange):
            if move and self._dropIndicatorPosition in (self.AboveItem, self.BelowItem):
                event.accept()
                updateRect |= QtWidgets.QTableView.visualRect(self, self._dropIndicatorIndex)
            else:
                event.ignore()
        else:
            event.accept()
            if move and self._dropIndicatorPosition in (self.AboveItem, self.BelowItem):
                updateRect |= QtWidgets.QTableView.visualRect(self, self._dropIndicatorIndex)
                if self.currentDropTargetIndexes:
                    for index in self.currentDropTargetIndexes:
                        updateRect |= self.visualRect(index)
                self.currentDropTargetIndexes = dropTargetIndexes
#                self.currentDropTargetIndexes = self.currentDropTargetRange = None
                self.viewport().update(updateRect)
                return
            elif move and not swap and self._dropIndicatorPosition == self.OnItem:
                for index in dropTargetIndexes:
                    if index.flags() & QtCore.Qt.ItemIsEditable:
                        event.ignore()
                        break

        if self.currentDropTargetRange != dropTargetRange:
            for index in dropTargetIndexes:
                updateRect |= self.visualRect(index)
            if self.currentDropTargetIndexes:
                for index in self.currentDropTargetIndexes:
                    updateRect |= self.visualRect(index)
            self.currentDropTargetRange = dropTargetRange
            self.currentDropTargetIndexes = dropTargetIndexes
            self.viewport().update(updateRect)

    def dragLeaveEvent(self, event):
        self.currentDropTargetRange = self.currentDropTargetIndexes = None
        self._dropIndicatorPosition = self.OnViewport
        self._dropIndicatorIndex = None
        QtWidgets.QTableView.dragLeaveEvent(self, event)
        self.viewport().update()

    def dropEvent(self, event):
        self.viewport().update()
        #avoid cursor "memory"
        QtCore.QTimer.singleShot(0, lambda pos=self._dropIndicatorPosition, mod=event.keyboardModifiers(): self.processDrop(pos, mod))

    def overwriteDropData(self, sources, targets):
        sourceData = [i.data(MultiDataRole) for i in sources]
        for index, data in zip(targets, sourceData):
            self.model().setData(index, data, MultiDataRole)

    def swapDropData(self, sources, targets):
        sourceData = [i.data(MultiDataRole) for i in sources]
        targetData = [i.data(MultiDataRole) for i in targets]
        for index, data in zip(targets, sourceData):
            self.model().setData(index, data, MultiDataRole)
        for index, data in zip(sources, targetData):
            self.model().setData(index, data, MultiDataRole)

    def insertDropData(self, sources, target):
        if target in sources:
            return
        if target < min(sources):
            movingData = [index.data(MultiDataRole) for index in self.model().indexListFromMultiIndexes(sources)]
            movingData.extend([index.data(MultiDataRole) for index in self.model().indexListFromMultiIndexes(range(target, min(sources)))])
            targetRange = range(target, max(sources) + 1)
        else:
            movingData = [index.data(MultiDataRole) for index in self.model().indexListFromMultiIndexes(range(max(sources) + 1, target))]
            movingData.extend([index.data(MultiDataRole) for index in self.model().indexListFromMultiIndexes(sources)])
            targetRange = range(min(sources), target)
        for index, data in zip(self.model().indexListFromMultiIndexes(targetRange), movingData):
            self.model().setData(index, data, MultiDataRole)

    def processDrop(self, dropIndicatorPosition, modifiers):
        copy = modifiers == QtCore.Qt.ShiftModifier
        swap = modifiers == QtCore.Qt.ControlModifier
        overwrite = []
        if dropIndicatorPosition == self.OnItem:
            if copy:
                for index in self.currentDropTargetIndexes:
                    if index.flags() & QtCore.Qt.ItemIsEditable:
                        overwrite.append(index)
                if overwrite:
                    names = QtCore.Qt.escape(', '.join('"{}"'.format(index.data(MultiNameRole)) for index in overwrite))
                    if QtWidgets.QMessageBox.question(self, 'Overwrite Multi', 
                        'Do you want to overwrite the following Multi{}?'
                        '<br/></br>{}<br/><br/>'
                        '<b>NOTE</b>: This operation cannot be undone!'.format('s' if len(overwrite) == 1 else '', names), 
                        QtWidgets.QMessageBox.Ok|QtWidgets.QMessageBox.Cancel) != QtWidgets.QMessageBox.Ok:
                            self.currentDropTargetRange = self.currentDropTargetIndexes = None
                            return
                sources = sorted(self.selectedIndexes(), key=lambda i: i.row() + i.column() * 32)
                targets = sorted(self.currentDropTargetIndexes, key=lambda i: i.row() + i.column() * 32)
                self.overwriteDropData(sources, targets)
            elif swap:
                sources = sorted(self.selectedIndexes(), key=lambda i: i.row() + i.column() * 32)
                targets = sorted(self.currentDropTargetIndexes, key=lambda i: i.row() + i.column() * 32)
                self.swapDropData(sources, targets)
            else:
                #this should happen when drops happen on empty slots.
                #might want to think again about this behavior
                sources = sorted(self.selectedIndexes(), key=lambda i: i.row() + i.column() * 32)
                targets = sorted(self.currentDropTargetIndexes, key=lambda i: i.row() + i.column() * 32)
                self.overwriteDropData(sources, targets)
        else:
            targetIndex = sorted(self.currentDropTargetIndexes, key=lambda i: i.row() + i.column() * 32)[0]
            target = targetIndex.data(MultiIndexRole)
            if dropIndicatorPosition == self.BelowItem:
                target += 1
            self.insertDropData([i.data(MultiIndexRole) for i in self.selectedIndexes()], target)
#            if self._dropIndicatorPosition in (self.AboveItem, self.BelowItem):
#                print(self._dropIndicatorPosition)
#        for index in self.selectedIndexes():
#            print(index.row(), index.column())

        self.currentDropTargetRange = self.currentDropTargetIndexes = None
        self._dropIndicatorIndex = None
        self._dropIndicatorPosition = self.OnViewport
        self.viewport().update()

    def paintEvent(self, event):
        QtWidgets.QTableView.paintEvent(self, event)
        if self._dropIndicatorPosition in (self.AboveItem, self.BelowItem):
            qp = QtGui.QPainter(self.viewport())
            qp.setPen(self.dropLinePen)
            rect = QtWidgets.QTableView.visualRect(self, self._dropIndicatorIndex)
            if self._dropIndicatorPosition == self.AboveItem:
                qp.drawLine(rect.topLeft(), rect.topRight())
            else:
                qp.drawLine(rect.bottomLeft(), rect.bottomRight())
        elif self.currentDropTargetIndexes:
            qp = QtGui.QPainter(self.viewport())
            path = QtGui.QPainterPath()
            path.setFillRule(QtCore.Qt.WindingFill)
            qp.setPen(self.dropIntoPen)
            qp.setBrush(self.dropIntoBrush)
            rects = [QtCore.QRectF()]
            for index in self.currentDropTargetIndexes:
                rect = QtCore.QRectF(self.visualRect(index).adjusted(0, 0, -1, -1))
                if rect.top() == rects[-1].bottom():
                    rects[-1] |= rect
                else:
                    rects.append(rect)
            for rect in rects:
                qp.drawRect(rect)


class MultiBrowser(QtWidgets.QDialog):
    alphaSortRequest = QtCore.pyqtSignal()
    assembleRequest = QtCore.pyqtSignal()

    def __init__(self, parent=None, collection=None):
        QtWidgets.QDialog.__init__(self, parent)
        self.main = QtWidgets.QApplication.instance()
        loadUi('{}ui/multibrowser.ui'.format(uiPath), self)
        self.settings = QtCore.QSettings()

        if __name__ == '__main__':
            source = MultiQueryModel()
            from bigglesworth.database import CollectionManagerModel
            self.referenceModel = CollectionManagerModel()
        else:
            source = self.main.database.multiModel
            self.referenceModel = self.main.database.referenceModel

        self.model = MultiSetModel(source)
        self.multiTable.setModel(self.model)

        self.settings.beginGroup('CollectionIcons')
        collections = self.referenceModel.collections
        current = collections.index(collection) if collection is not None else 0
        for collection in collections:
            if collection == 'Blofeld':
                iconName = 'bigglesworth'
            else:
                iconName = self.settings.value(collection, '')
            self.collectionCombo.addItem(QtGui.QIcon.fromTheme(iconName), collection)
        self.collectionCombo.currentIndexChanged[str].connect(self.setCollection)
        self.collectionCombo.setCurrentIndex(current)

        organizeMenu = QtWidgets.QMenu()
        self.organizeBtn.setMenu(organizeMenu)
        organizeMenu.aboutToShow.connect(self.checkOrganizeMenu)
        self.alphaSortAction = organizeMenu.addAction(QtGui.QIcon.fromTheme('view-sort-ascending'), 'Sort alphabetically')
        self.alphaSortAction.triggered.connect(self.alphaSortRequest)
        organizeMenu.addSeparator()
        self.assembleAction = organizeMenu.addAction(QtGui.QIcon.fromTheme('edit-select-all'), 'Assemble all Multis')
        self.assembleAction.triggered.connect(self.assembleRequest)

    def checkOrganizeMenu(self):
        count = len(self.model.sourceModel().existingIndexes())
        self.alphaSortAction.setEnabled(count)
        self.assembleAction.setEnabled(count and count < 128)

    def setCollection(self, collection):
        self.model.setCollection(collection)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            return
        QtWidgets.QDialog.keyPressEvent(self, event)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    app.setOrganizationName('jidesk')
    app.setApplicationName('Bigglesworth')

    dataPath = QtGui.QDesktopServices.storageLocation(QtGui.QDesktopServices.DataLocation)
    db = QtSql.QSqlDatabase.addDatabase('QSQLITE')
    db.setDatabaseName(dataPath + '/library.sqlite')

    w = MultiBrowser()
    w.show()
    sys.exit(app.exec_())
