import json

from Qt import QtCore, QtGui, QtWidgets

from bigglesworth.parameters import categories
from bigglesworth.utils import getValidQColor
from bigglesworth.const import CatRole, HoverRole, backgroundRole, foregroundRole

class ExpandingView(QtWidgets.QListView):
    def showEvent(self, event):
        QtWidgets.QListView.showEvent(self, event)
        self.setMinimumWidth(self.sizeHintForColumn(0) + 
            self.verticalScrollBar().sizeHint().width() + 
            self.parent().parent().iconSize().width())


class CategoryDelegate(QtWidgets.QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        combo = QtWidgets.QComboBox(parent)
        combo.setView(ExpandingView())
        for cat in categories:
            combo.addItem(QtGui.QIcon.fromTheme(cat.strip().lower()), cat)
        combo.setCurrentIndex(index.data())
        combo.view().activated.connect(lambda index, combo=combo: self.commit(index, combo))
        combo.view().clicked.connect(lambda index, combo=combo: self.commit(index, combo))
        combo.view().pressed.connect(lambda index, combo=combo: self.commit(index, combo))
        return combo

    def updateEditorGeometry(self, editor, option, index):
        QtWidgets.QStyledItemDelegate.updateEditorGeometry(self, editor, option, index)
        editor.setGeometry(option.rect)

    def displayText(self, value, locale):
        return categories[value]

    def editorEvent(self, event, model, option, index):
        if index.flags() & QtCore.Qt.ItemIsEditable and \
            self.parent().editTriggers() & self.parent().EditKeyPressed and \
            event.type() == QtCore.QEvent.MouseButtonRelease and \
            event.button() == QtCore.Qt.LeftButton:
                self.parent().edit(index)
                return True
        return QtWidgets.QStyledItemDelegate.editorEvent(self, event, model, option, index)

#    implement this to all delegates to have single/double click editing for this only
#    def editorEvent(self, event, model, option, index):
#        return QtWidgets.QStyledItemDelegate.editorEvent(self, event, model, option, index)

    def commit(self, index, combo):
        combo.setCurrentIndex(index.row())
        self.commitData.emit(combo)
        self.closeEditor.emit(combo, self.NoHint)

    def setModelData(self, widget, model, index):
        model.setData(index, widget.currentIndex(), CatRole)
        QtWidgets.QStyledItemDelegate.setModelData(self, widget, model, index)


class TagsDelegate(QtWidgets.QStyledItemDelegate):
    defaultBackground = QtCore.Qt.darkGray
    defaultText = QtCore.Qt.white
    tagsModel = None
    tagClicked = QtCore.pyqtSignal(str)

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
        if event.type() == QtCore.QEvent.MouseMove:
            model.setData(index, event.pos(), HoverRole)
        elif event.type() == QtCore.QEvent.Leave:
            model.setData(index, False, HoverRole)
        elif event.type() == QtCore.QEvent.MouseButtonPress and event.button() == QtCore.Qt.LeftButton and index.data():
            self.selectTag(event, option, index)
#            self.showMenu(event, model, option, index)
        return QtWidgets.QStyledItemDelegate.editorEvent(self, event, model, option, index)

    def selectTag(self, event, option, index):
        tags = json.loads(index.data())
        if not tags:
            return
        self.initStyleOption(option, index)
        pos = event.pos()
        delta = 1
        left = option.rect.x() + .5
        height = option.fontMetrics.height() + 4
        top = option.rect.y() + (option.rect.height() - height) * .5
        for tag in tags:
            width = option.fontMetrics.width(tag) + 8
            rect = QtCore.QRectF(left + delta + 1, top, width, height)
            if pos in rect:
                self.tagClicked.emit(tag)
                break
            delta += width + 4

    def showMenu(self, *args):
        print(args)

    def paint(self, painter, option, index):
        self.initStyleOption(option, index)
        if not option.text:
            QtWidgets.QApplication.style().drawControl(QtWidgets.QStyle.CE_ItemViewItem, option, painter)
            return
        tags = json.loads(option.text)
        option.text = ''
#        option.state |= QtWidgets.QStyle.State_Selected
#        option.state ^= QtWidgets.QStyle.State_Selected
        QtWidgets.QApplication.style().drawControl(QtWidgets.QStyle.CE_ItemViewItem, option, painter)
#        tags = json.loads(index.data())
        if not tags:
            return
        painter.save()
        painter.setRenderHints(painter.Antialiasing)
        painter.translate(.5, .5)

        pos = index.data(HoverRole) if option.state & QtWidgets.QStyle.State_MouseOver else False
        delta = 1
        left = option.rect.x() + .5
        height = option.fontMetrics.height() + 4
        top = option.rect.y() + (option.rect.height() - height) * .5
        stop = False
#        painter.setBrush(self.defaultBackground)
        for tag in tags:
            bg, fg = self.tagColors.get(tag, (self.defaultBackground, self.defaultText))
            painter.setBrush(bg)
            width = option.fontMetrics.width(tag) + 8
            rect = QtCore.QRectF(left + delta + 1, top, width, height)
            if pos and pos in rect:
                painter.setPen(fg)
            else:
                painter.setPen(QtCore.Qt.transparent)
            if rect.right() > option.rect.right() or rect.left() > option.rect.right():
                stop = True
                grad = QtGui.QLinearGradient(option.rect.right() - 10, 0, option.rect.right(), 0)
                grad.setColorAt(0, bg)
                grad.setColorAt(1, QtCore.Qt.transparent)
                painter.setBrush(QtGui.QBrush(grad))
                grad.setColorAt(0, painter.pen().color())
                painter.setPen(QtGui.QPen(grad, 1))
                painter.drawRoundedRect(rect, 2, 2)
                grad.setColorAt(0, fg)
                painter.setPen(QtGui.QPen(grad, 1))
            else:
                painter.drawRoundedRect(rect, 2, 2)
                painter.setPen(fg)
            painter.drawText(rect, QtCore.Qt.AlignCenter, tag)
            delta += width + 4
            if stop:
                break
        painter.restore()


class CheckBoxDelegate(QtWidgets.QStyledItemDelegate):
    square_pen_enabled = QtGui.QColor(QtCore.Qt.darkGray)
    square_pen_disabled = QtGui.QColor(QtCore.Qt.lightGray)
    square_pen = square_pen_enabled
    select_pen_enabled = QtGui.QColor(QtCore.Qt.black)
    select_pen_disabled = QtGui.QColor(QtCore.Qt.darkGray)
    select_pen = select_pen_enabled
    select_brush_enabled = QtGui.QColor(QtCore.Qt.black)
    select_brush_disabled = QtGui.QColor(QtCore.Qt.black)
    select_brush = select_brush_enabled
    path = QtGui.QPainterPath()
    path.moveTo(2, 5)
    path.lineTo(4, 8)
    path.lineTo(8, 2)
    path.lineTo(4, 6)
    def __init__(self, *args, **kwargs):
        if 'editable' in kwargs:
            self.editable = kwargs.pop('editable')
        else:
            self.editable = True
        QtWidgets.QStyledItemDelegate.__init__(self, *args, **kwargs)
#        self.editable = editable
        self.square = QtCore.QRectF()

    def paint(self, painter, style, index):
        QtWidgets.QStyledItemDelegate.paint(self, painter, style, QtCore.QModelIndex())
        if index.flags() & QtCore.Qt.ItemIsEnabled:
            self.square_pen = self.square_pen_enabled
            self.select_pen = self.select_pen_enabled
            self.select_brush = self.select_brush_enabled
        else:
            self.square_pen = self.square_pen_disabled
            self.select_pen = self.select_pen_disabled
            self.select_brush = self.select_brush_disabled
        option = QtWidgets.QStyleOptionViewItem()
        option.__init__(style)
        self.initStyleOption(option, index)
        painter.setRenderHints(QtGui.QPainter.Antialiasing)
        painter.save()
        painter.translate(option.rect.x() + option.rect.width() / 2 - 5, option.rect.y() + option.rect.height() / 2 - 5)
        painter.setPen(self.square_pen)
        painter.drawRect(0, 0, 10, 10)
        if index.data(QtCore.Qt.CheckStateRole):
            painter.setPen(self.select_pen)
            painter.setBrush(self.select_brush)
#            painter.translate(self.square.left(), self.square.top())
            painter.drawPath(self.path)
        painter.restore()

    def editorEvent(self, event, model, option, index):
        if not self.editable or not index.flags() & QtCore.Qt.ItemIsEditable:
            return False
        if index.flags() & QtCore.Qt.ItemIsEnabled:
            if event.type() == QtCore.QEvent.MouseButtonPress and event.button() == QtCore.Qt.LeftButton:
                model.itemFromIndex(index).setData(not index.data(QtCore.Qt.CheckStateRole), QtCore.Qt.CheckStateRole)
                if self.parent():
                    selection = self.parent().selectionModel()
                    selection.setCurrentIndex(index, selection.NoUpdate)
            elif event.type() == QtCore.QEvent.KeyPress and event.key() in (QtCore.Qt.Key_Space, QtCore.Qt.Key_Enter):
                model.itemFromIndex(index).setData(not index.data(QtCore.Qt.CheckStateRole), QtCore.Qt.CheckStateRole)
        return True

