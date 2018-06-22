from Qt import QtCore, QtGui, QtWidgets

from bigglesworth.utils import getValidQColor
from bigglesworth.const import foregroundRole, backgroundRole

class FilterNameEdit(QtWidgets.QLineEdit):
    def __init__(self, *args, **kwargs):
        QtWidgets.QLineEdit.__init__(self, *args, **kwargs)
        self.rightMargin = self.getTextMargins()[2]
        self.setup(self.height())

    def setup(self, height):
        self.baseHeight = height
        size = self.baseHeight * .66
        self.pm = QtGui.QIcon.fromTheme('edit-clear').pixmap(size, size)
        self.pmRect = QtCore.QRectF(self.pm.rect())
        self.clearRect = QtCore.QRectF(0, 0, size, size)
        l, t, _, b = self.getTextMargins()
        self.setTextMargins(l, t, self.rightMargin + size + 4, b)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self.setText('')
        else:
            QtWidgets.QLineEdit.keyPressEvent(self, event)

    def paintEvent(self, event):
        QtWidgets.QLineEdit.paintEvent(self, event)
        if self.text():
            qp = QtGui.QPainter(self)
            qp.setRenderHints(qp.Antialiasing)
            qp.drawPixmap(self.clearRect, self.pm, self.pmRect)

    def resizeEvent(self, event):
        if self.height() != self.baseHeight:
            self.setup(self.height())
        self.clearRect.moveTop((self.height() - self.pm.height()) / 2)
        self.clearRect.moveRight(self.width() - self.clearRect.top())

    def mousePressEvent(self, event):
        if self.text() and event.button() == QtCore.Qt.LeftButton and event.pos().x() >= self.clearRect.x():
            self.setText('')
        else:
            QtWidgets.QLineEdit.mousePressEvent(self, event)

    def mouseMoveEvent(self, event):
        if self.text() and event.pos().x() >= self.clearRect.x():
            self.setCursor(QtCore.Qt.ArrowCursor)
        else:
            self.setCursor(QtCore.Qt.IBeamCursor)
        QtWidgets.QLineEdit.mouseMoveEvent(self, event)


class TagsCompleter(QtWidgets.QCompleter):
    def __init__(self, model, parent):
        self.baseModel = QtGui.QStandardItemModel()
        self.createBaseModel(model)
        QtWidgets.QCompleter.__init__(self, self.baseModel, parent)
        self.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.setWidget(parent)
        self.highlighted.connect(self.setText)
        parent.tagsChanged.connect(self.updateModel)
#        self.setCompletionMode(self.UnfilteredPopupCompletion)

    def createBaseModel(self, model):
        self.baseModel.clear()
        for row in range(model.rowCount()):
            tagItem = QtGui.QStandardItem(model.index(row, 0).data())
            tagItem.setData(getValidQColor(model.index(row, 1).data(), backgroundRole), QtCore.Qt.BackgroundRole)
            tagItem.setData(getValidQColor(model.index(row, 2).data(), foregroundRole), QtCore.Qt.ForegroundRole)
            self.baseModel.appendRow(tagItem)

    def updateModel(self, tags):
        if not tags:
            self.setModel(self.baseModel)
            return
        model = QtGui.QStandardItemModel()
        for row in range(self.baseModel.rowCount()):
#            tag = self.baseModel.index(row, 0).data()
            tagItem = self.baseModel.item(row, 0)
            if not tagItem.text() in tags:
                model.appendRow(tagItem.clone())
        self.setModel(model)

    def setText(self, text):
        pos = self.widget().cursorPosition()
        self.widget().setText(text)
        self.widget().setSelection(len(text), pos - len(text))

    def setCompletionPrefix(self, prefix):
        QtWidgets.QCompleter.setCompletionPrefix(self, prefix)
        if prefix:
            self.complete()
        else:
            self.popup().hide()

    def complete(self, rect=QtCore.QRect()):
        rect = self.widget().rect()
        fm = self.widget().fontMetrics()
        cm = self.completionModel()
        if cm.rowCount():
            width = max(fm.width(cm.index(r, 0).data()) for r in range(cm.rowCount()))
            option = QtWidgets.QStyleOptionFrameV3()
            self.widget().initStyleOption(option)
            rect.setX(rect.x() + self.widget().getTextMargins()[0] + option.lineWidth)
            rect.setWidth(width + 12)
            QtWidgets.QCompleter.complete(self, rect)
            pos = self.widget().cursorPosition()
            current = self.currentCompletion()
            self.widget().setText(current)
            self.widget().setSelection(len(current), pos - len(current))
        else:
            self.popup().hide()


class FilterTagsEdit(FilterNameEdit):
    tagsChanged = QtCore.pyqtSignal(object)
    def __init__(self, *args, **kwargs):
        FilterNameEdit.__init__(self, *args, **kwargs)
        self.returnPressed.connect(self.checkCompletion)
        self.leftMargin = self.getTextMargins()[0]
        self.tags = []
        self._tagCursor = None
        self.cursorTimer = QtCore.QTimer()
        self.cursorTimer.setInterval(500)
        self.cursorTimer.timeout.connect(self._setCursorBlink)
        self.cursorBlink = False
        self.installEventFilter(self)
        self.tagsX = 0
        self.completer = None
        self.autoPopup = False

    def setAutoPopup(self, auto):
        self.autoPopup = auto

    @property
    def tagCursor(self):
        return self._tagCursor

    @tagCursor.setter
    def tagCursor(self, pos):
        if pos is None:
            self.cursorTimer.stop()
            self.cursorBlink = False
        else:
            self.cursorTimer.start()
            self.cursorBlink = True
        self._tagCursor = pos
        self.update()

    def _setCursorBlink(self):
        if not self.hasFocus() or not self.tags or self.tagCursor is None:
            self.cursorTimer.stop()
            self.cursorBlink = False
        else:
            self.cursorBlink = not self.cursorBlink
        self.update()

    def setText(self, text):
        QtWidgets.QLineEdit.setText(self, text)
        self.checkMargins()

    def setTags(self, tags=None):
        if tags is None:
            tags = []
        self.tags = tags
        self.tagsChanged.emit(tags)
        self.setText('')

    def checkCompletion(self):
        if self.completer.completionCount() and self.text().strip():
            self.tags.append(self.text())
            self.tagsChanged.emit(self.tags)
            QtWidgets.QLineEdit.setText(self, '')
            self.checkMargins()
            self.completer.popup().hide()
#            self.setCursorPosition(len(self.text()))

    def checkMargins(self):
        l, t, r, b = self.getTextMargins()
        if not self.tags:
            self.setTextMargins(self.leftMargin, t, r, b)
            self.update()
            return
        l = sum(self.fontMetrics().width(t) + 6 for t in self.tags) + len(self.tags) * 4
#        option = QtWidgets.QStyleOptionFrameV3()
#        self.initStyleOption(option)
#        textRect = self.style().subElementRect(QtWidgets.QStyle.SE_LineEditContents, option, self)
        self.setTextMargins(l, t, r, b)
        self.update()

    def focusInEvent(self, event):
        QtWidgets.QLineEdit.focusInEvent(self, event)
        if self.tagCursor is not None:
            self.cursorBlink = True
            self.cursorTimer.start()

    def mousePressEvent(self, event):
        if (self.text() or self.tags) and event.button() == QtCore.Qt.LeftButton and event.pos().x() >= self.clearRect.x():
            self.setText('')
            self.tags = []
            self.tagsChanged.emit([])
            self.checkMargins()
        else:
            if event.pos().x() < self.clearRect.x() or event.pos().x() > (self.tagsX + self.getTextMargins()[0]):
                self.setReadOnly(False)
                self.tagCursor = None
            QtWidgets.QLineEdit.mousePressEvent(self, event)

    def mouseMoveEvent(self, event):
        if (self.text() or self.tags) and (event.pos().x() >= self.clearRect.x() or event.pos().x() < (self.tagsX + self.getTextMargins()[0])):
            self.setCursor(QtCore.Qt.ArrowCursor)
        else:
            self.setCursor(QtCore.Qt.IBeamCursor)
        QtWidgets.QLineEdit.mouseMoveEvent(self, event)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Backspace:
            if self.completer.completionCount() and len(self.text()) > 1:
                self.textEdited.disconnect(self.completer.setCompletionPrefix)
                QtWidgets.QLineEdit.keyPressEvent(self, event)
                self.textEdited.connect(self.completer.setCompletionPrefix)
            elif not self.text() and self.tags:
                if self.tagCursor is None:
                    self.tags.pop(-1)
                    self.tagsChanged.emit(self.tags)
                elif self.tagCursor > 0:
                    self.tagCursor -= 1
                    self.tags.pop(self.tagCursor)
                    self.tagsChanged.emit(self.tags)
                self.checkMargins()
            else:
                QtWidgets.QLineEdit.keyPressEvent(self, event)
        elif event.matches(QtGui.QKeySequence.Delete) and self.tags and self.cursorPosition() == 0 and self.tagCursor is not None:
            self.tags.pop(self.tagCursor)
            self.tagsChanged.emit(self.tags)
            self.checkMargins()
            if not self.tags or self.tagCursor == len(self.tags):
                self.setReadOnly(False)
            self.update()
        elif event.matches(QtGui.QKeySequence.MoveToPreviousChar) and self.tags and self.cursorPosition() == 0:
            self.setReadOnly(True)
            if self.tagCursor is None:
                self.tagCursor = len(self.tags) - 1
            elif self.tagCursor > 0:
                self.tagCursor -= 1
            self.update()
        elif event.matches(QtGui.QKeySequence.MoveToNextChar) and self.tags and self.cursorPosition() == 0 and self.tagCursor is not None:
            self.tagCursor += 1
            if self.tagCursor == len(self.tags):
                self.setReadOnly(False)
                self.tagCursor = None
            self.update()
        elif event.key() == QtCore.Qt.Key_Space:
            self.checkCompletion()
            QtWidgets.QLineEdit.setText(self, self.text().rstrip())
        elif event.key() == QtCore.Qt.Key_End:
            self.tagCursor = None
            self.setReadOnly(False)
            QtWidgets.QLineEdit.keyPressEvent(self, event)
        elif event.key() == QtCore.Qt.Key_Escape:
            QtWidgets.QLineEdit.setText(self, '')
            self.completer.popup().hide()
        elif event.key() == QtCore.Qt.Key_Down and self.autoPopup and not self.completer.popup().isVisible():
            self.completer.setCompletionPrefix(self.text())
            self.completer.complete()
            if self.completer.popup().model().rowCount():
                self.completer.popup().show()
        else:
            QtWidgets.QLineEdit.keyPressEvent(self, event)

    def eventFilter(self, source, event):
        if event.type() == QtCore.QEvent.KeyPress:
            if event.key() == QtCore.Qt.Key_Tab:
                if not self.completer.popup().isVisible():
                    return False
                self.checkCompletion()
                return True
            elif event.key() == QtCore.Qt.Key_Escape and (self.text() or self.tags) and not self.completer.popup().isVisible():
                self.setText('')
                self.tags = []
                self.tagsChanged.emit([])
                self.checkMargins()
                return True
        return QtWidgets.QLineEdit.eventFilter(self, source, event)

    def setModel(self, tagsModel):
        try:
            self.textEdited.disconnect(self.completer.setCompletionPrefix)
            self.tagsModel.dataChanged.disconnect(self.reloadTags)
        except:
            pass
        self.completer = TagsCompleter(tagsModel, self)
        self.completer.popup().installEventFilter(self)
        self.textEdited.connect(self.completer.setCompletionPrefix)
        self.tagsModel = tagsModel
        self.tagsModel.dataChanged.connect(self.reloadTags)
        self.reloadTags()

    def reloadTags(self, *args):
        self.tagColors = {}
        for row in range(self.tagsModel.rowCount()):
            tag = self.tagsModel.index(row, 0).data()
            bgColor = getValidQColor(self.tagsModel.index(row, 1).data(), backgroundRole)
            fgColor = getValidQColor(self.tagsModel.index(row, 2).data(), foregroundRole)
            self.tagColors[tag] = bgColor, fgColor
        newTags = []
        for tag in self.tags:
            if tag in self.tagColors:
                newTags.append(tag)
        if set(newTags) != set(self.tags):
            self.setTags(newTags)

    def contextMenuEvent(self, event):
        menu = self.createStandardContextMenu()
        firstAction = menu.actions()[0]
        tags = {}
        for row in range(self.completer.model().rowCount()):
            tagItem = self.completer.model().item(row, 0)
            tags[tagItem.text()] = tagItem
#        firstAction.setIcon(QtGui.QIcon.fromTheme('edit-undo'))
        option = QtWidgets.QStyleOptionMenuItem()
        option.initFrom(menu)
        iconSize = self.style().pixelMetric(QtWidgets.QStyle.PM_SmallIconSize, option, menu)
        for tag in sorted(tags):
            tagItem = tags[tag]
            icon = QtGui.QPixmap(iconSize, iconSize)
            icon.fill(QtCore.Qt.transparent)
            qp = QtGui.QPainter(icon)
            qp.setRenderHints(qp.Antialiasing)
            qp.setPen(QtGui.QPen(tagItem.data(QtCore.Qt.BackgroundRole), iconSize * .25))
            qp.setBrush(tagItem.data(QtCore.Qt.ForegroundRole))
#            qp.translate(.5, .5)
            deltaPos = iconSize * .125
            qp.drawRoundedRect(deltaPos, deltaPos, iconSize - deltaPos * 2 - 1, iconSize - deltaPos * 2 - 1, deltaPos * .5, deltaPos * .5)
            qp.end()
            tagAction = QtWidgets.QAction(QtGui.QIcon(icon), tag, menu)
            tagAction.triggered.connect(lambda _, tag=tag: self.setTags(self.tags + [tag]))
            menu.insertAction(firstAction, tagAction)
        menu.insertSeparator(firstAction)
        menu.exec_(self.mapToGlobal(event.pos()))

    def paintEvent(self, event):
        QtWidgets.QLineEdit.paintEvent(self, event)
        if not (self.tags or self.text()):
            return
        qp = QtGui.QPainter(self)
        qp.setRenderHints(qp.Antialiasing)
        option = QtWidgets.QStyleOptionFrameV3()
        self.initStyleOption(option)
        qp.save()
        qp.translate(.5 + option.lineWidth * .5, .5)
        textRect = self.style().subElementRect(QtWidgets.QStyle.SE_LineEditContents, option, self)
        self.tagsX = option.lineWidth * .5 + textRect.x() + 2
        y = textRect.y()
        height = textRect.height()
        fontMetrics = self.fontMetrics()
        baseBrush = qp.brush()
        basePen = qp.pen()
#        pos = QtCore.QPoint(2.5 + option.lineWidth * .5 + textRect.x(), 0)
        qp.translate(textRect.x() + 2, 0)
        for i, tag in enumerate(self.tags):
            if self.cursorBlink and self.tagCursor == i:
                qp.setPen(basePen)
                qp.drawLine(-2, y + (height - fontMetrics.height()) * .5, -2, y + fontMetrics.height() + 1)
            width = fontMetrics.width(tag) + 6
            bg, fg = self.tagColors.get(tag, (baseBrush, basePen))
            qp.setPen(QtCore.Qt.NoPen)
            qp.setBrush(bg)
            qp.drawRoundedRect(0, y, width, height, 2, 2)
            qp.setPen(fg)
            qp.drawText(0, y, width, height, QtCore.Qt.AlignCenter, tag)
#            if self.mapFromGlobal(QtGui.QCursor.pos()) in QtCore.QRect(pos.x(), pos.y(), width, height):
#                qp.drawEllipse(width - height, y + 1, height - 2, height - 2)
            qp.translate(width + 4, 0)
#            pos.setX(pos.x() + width + 4)
        qp.restore()
        qp.drawPixmap(self.clearRect, self.pm, self.pmRect)

