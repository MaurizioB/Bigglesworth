import os
from bisect import bisect_left
os.environ['QT_PREFERRED_BINDING'] = 'PyQt4'

from Qt import QtCore, QtGui, QtWidgets

try:
    from bigglesworth.parameters import categories
    from bigglesworth.widgets import NameEdit
    from bigglesworth.const import factoryPresetsNamesDict
except:
    QtCore.pyqtSignal = QtCore.Signal
    QtCore.pyqtProperty = QtCore.Property
    QtCore.pyqtSlot = QtCore.Slot
    from nameedit import NameEdit
    categories = ('Init', 'Arp ', 'Atmo', 'Bass', 'Drum', 'FX  ', 'Keys', 'Lead', 'Mono', 'Pad ', 'Perc', 'Poly', 'Seq ')
#from bigglesworth.const import TagsColumn

def _getCssQColorStr(color):
        return 'rgba({},{},{},{:.0f}%)'.format(color.red(), color.green(), color.blue(), color.alphaF() * 100)


class DisplayNameEdit(NameEdit):
    focusChanged = QtCore.pyqtSignal(bool)

    def focusInEvent(self, event):
        NameEdit.focusInEvent(self, event)
        self.focusChanged.emit(True)

    def focusOutEvent(self, event):
        NameEdit.focusOutEvent(self, event)
        self.focusChanged.emit(False)

    def clearFocus(self):
        NameEdit.clearFocus(self)
        self.focusChanged.emit(False)


class GraphicsSpin(QtWidgets.QSpinBox):
    def __init__(self):
        QtWidgets.QSpinBox.__init__(self)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Maximum))
        self.lineEdit().setReadOnly(True)
        self.lineEdit().selectionChanged.connect(lambda: self.lineEdit().deselect())
        self.lineEdit().setStyleSheet('''color: none''')
        self.setStyleSheet('''
            GraphicsSpin {
                border: none;
                padding-right: 12px;
                min-height: 16px;
                background: transparent;
                color: black;
                min-width: 16px;
            }
            GraphicsSpin:disabled {
                color: gray;
            }
            GraphicsSpin::up-button, GraphicsSpin::down-button {
                border: none;
                subcontrol-origin: border;
                width: 10px;
                height: 10px;
                background: transparent;
                padding-left: 4px;
            }
            GraphicsSpin::up-button {
                padding-top: -2px;
            }
            GraphicsSpin::down-button {
                padding-bottom: -2px;
            }
            GraphicsSpin::up-arrow, GraphicsSpin::down-arrow {
                width: 0px;
                height: 0px;
                border-right: 4px solid rgba(1,1,1,0);
                border-left: 4px solid rgba(1,1,1,0);
                border-top: 4px solid black;
                border-bottom: 4px solid black;
            }
            GraphicsSpin::down-arrow:disabled, GraphicsSpin::down-arrow:off {
                border-top: 4px solid gray;
            }
            GraphicsSpin::up-arrow:disabled, GraphicsSpin::up-arrow:off {
                border-bottom: 4px solid gray;
            }
            GraphicsSpin::down-arrow {
                border-bottom-width: 0;
            }
            GraphicsSpin::up-arrow {
                border-top-width: 0;
            }
           ''')

    def contextMenuEvent(self, event):
        pass

    def sizeHint(self):
        return QtCore.QSize(self.fontMetrics().width(str(self.maximum())) + 10, self.fontMetrics().height())


class TextSpin(GraphicsSpin):
    def __init__(self, values):
        GraphicsSpin.__init__(self)
        self.values = values
        self.setMaximum(len(values) - 1)

    def textFromValue(self, value):
        try:
            return self.values[value]
        except:
            return self.values[0]

    def valueFromText(self, text):
        try:
            return self.values.index(text)
        except:
            return 0

    def sizeHint(self):
        fm = self.fontMetrics()
        maxWidth = max(fm.width(v) for v in self.values)
        return QtCore.QSize(maxWidth + 10, self.fontMetrics().height())


class BankSpin(TextSpin):
    def __init__(self, values):
        TextSpin.__init__(self, values)
        self.setValidIndexes([0])

    def setValidIndexes(self, indexes):
        self.valid = []
        for index in indexes:
            bank = index >> 7
            if bank in self.valid:
                continue
            self.valid.append(bank)
#        if not self.valid:
#            self.setRange(0, 0)
#            self.setEnabled(False)
#            return
#        self.setEnabled(True)
        self.setRange(min(self.valid), max(self.valid))
        completer = QtWidgets.QCompleter(self.values, self)
        completer.setCompletionMode(completer.InlineCompletion)
        self.lineEdit().setCompleter(completer)
        self.setValue(self.getValid())

    def getValid(self, value=None):
        if value is None:
            value = self.value()
        if not value in self.valid:
            pos = bisect_left(self.valid, value)
            if pos == len(self.valid):
                pos -= 1
            elif pos != 0:
                before = self.valid[pos - 1]
                after = self.valid[pos]
                if after - value > value - before:
                    pos = pos - 1
#            print(self.valid, pos)
            value = self.valid[pos]
        return value

    def stepBy(self, step):
        step = 1 if step > 0 else -1
        if len(self.valid) != 8:
            currentIndex = self.valid.index(self.getValid())
            newIndex = currentIndex + step
            if newIndex >= len(self.valid):
                step = self.valid[-1] - self.value()
            elif newIndex > 0:
                newValue = self.valid[newIndex]
                step = newValue - self.value()
            else:
                step = self.valid[0] - self.value()
        GraphicsSpin.stepBy(self, step)


class ProgSpin(GraphicsSpin):
    def __init__(self):
        GraphicsSpin.__init__(self)
        self.setReadOnly(False)
        self.setKeyboardTracking(False)
        self.valid = []
        self.rangeLen = 128
        self.setValidIndexes([0])

    def setValidIndexes(self, indexes, bank=0):
        self.fullValid = [[], [], [], [], [], [], [], []]
        for index in indexes:
            bank = index >> 7
            prog = (index & 127) + 1
            self.fullValid[bank].append(prog)
        self.setBank(bank)

    def setBank(self, bank):
        indexes = self.fullValid[bank]
#        if not indexes:
#            self.setRange(0, 0)
#            self.setEnabled(False)
#            return
#        self.setEnabled(True)
        self.setRange(min(indexes), max(indexes))
        self.valid = indexes
        completer = QtWidgets.QCompleter([str(v) for v in indexes], self)
        completer.setCompletionMode(completer.InlineCompletion)
        self.lineEdit().setCompleter(completer)
        self.setValue(self.getValid())

    def getValid(self, value=None):
        if value is None:
            value = self.value()
        if not value in self.valid:
            pos = bisect_left(self.valid, value)
            if pos == len(self.valid):
                pos -= 1
            elif pos != 0:
                before = self.valid[pos - 1]
                after = self.valid[pos]
                if after - value > value - before:
                    pos = pos - 1
            value = self.valid[pos]
        return value

    def validate(self, input, pos):
        valid, input, pos = GraphicsSpin.validate(self, input, pos)
        if valid in (QtGui.QValidator.Intermediate, QtGui.QValidator.Acceptable):
            if input:
                for value in self.valid:
                    sValue = str(value)
                    if sValue == input:
                        valid = QtGui.QValidator.Acceptable
                        break
                    elif input in sValue:
                        valid = QtGui.QValidator.Intermediate
                        break
                else:
                    valid = QtGui.QValidator.Invalid
        return valid, input, pos

    def stepBy(self, step):
        if len(self.valid) != self.rangeLen:
            currentIndex = self.valid.index(self.getValid())
            newIndex = currentIndex + step
            if newIndex >= len(self.valid):
                step = self.valid[-1] - self.value()
            elif newIndex > 0:
                newValue = self.valid[newIndex]
                step = newValue - self.value()
            else:
                step = self.valid[0] - self.value()
        GraphicsSpin.stepBy(self, step)
#        self.setReadOnly(True)
#        self.setReadOnly(False)


class CollectionLabel(QtWidgets.QLabel):
    def __init__(self, *args, **kwargs):
        QtWidgets.QLabel.__init__(self, *args, **kwargs)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Fixed))


    def setText(self, text):
        QtWidgets.QLabel.setText(self, self.fontMetrics().elidedText(text, QtCore.Qt.ElideRight, self.width()))
        QtWidgets.QLabel.setToolTip(self, text)


#class GraphicsLabel(QtWidgets.QGraphicsWidget):
#    def __init__(self, text):
#        QtWidgets.QGraphicsWidget.__init__(self)
#        self.text = text
#        fm = QtGui.QFontMetrics(self.font())
#        self.setMinimumSize(fm.width(text) + 2, fm.height())
#        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum))
##        self.setMaximumHeight(fm.height())
##        self.setMaximumSize(fm.width(text), fm.height())
#
#    def paint(self, qp, option, widget):
#        font = qp.font()
#        font.setBold(True)
#        qp.setFont(font)
#        qp.drawText(self.rect(), QtCore.Qt.AlignCenter, self.text)
#
#
#class GraphicsGroupWidget(QtWidgets.QGraphicsWidget):
#    framePen = QtGui.QColor(120, 120, 120, 120)
#    frameBackground = QtGui.QColor(220, 220, 220, 120)
##
##    def __init__(self):
##        QtWidgets.QGraphicsWidget.__init__(self)
##        self.setSpacing(2)
#
#    def paint(self, qp, option, widget):
#        qp.translate(.5, .5)
#        qp.setRenderHints(qp.Antialiasing)
#        qp.setBrush(self.frameBackground)
#        qp.setPen(self.framePen)
#        qp.drawRoundedRect(self.rect(), 4, 4)
#

class DisplayGroup(QtWidgets.QWidget):
    framePen = QtGui.QColor(120, 120, 120, 120)
    frameBackground = QtGui.QColor(220, 220, 180, 65)

    def __init__(self):
        QtWidgets.QWidget.__init__(self)
        self.setContentsMargins(0, 0, 0, 0)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Maximum))

    def addWidget(self, widget, alignment=QtCore.Qt.Alignment(0)):
        self.layout().addWidget(widget, alignment=alignment)

    def setSpacing(self, spacing):
        self.layout().setSpacing(spacing)

    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        qp.setRenderHints(qp.Antialiasing)
        qp.translate(.5, .5)
        qp.setBrush(self.frameBackground)
        qp.setPen(self.framePen)
        qp.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 4, 4)


class VDisplayGroup(DisplayGroup):
    def __init__(self):
        DisplayGroup.__init__(self)
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(1)
        self.setLayout(layout)


class HDisplayGroup(DisplayGroup):
    def __init__(self):
        DisplayGroup.__init__(self)
        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(1)
        self.setLayout(layout)


class ProgSendWidget(VDisplayGroup):
    def __init__(self):
        VDisplayGroup.__init__(self)

    def sizeHint(self):
        base = VDisplayGroup.sizeHint(self)
        base.setWidth(self.fontMetrics().width('D'))
        base.setHeight(self.fontMetrics().height() * 3)
        return base

    def paintEvent(self, event):
        VDisplayGroup.paintEvent(self, event)
        qp = QtGui.QPainter(self)
        font = self.font()
        font.setPointSize(font.pointSize() * .7)
        qp.drawText(self.rect(), QtCore.Qt.AlignCenter, 'S\nE\nN\nD')


class UndoRedoProxy(QtCore.QSortFilterProxyModel):
    def __init__(self):
        QtCore.QSortFilterProxyModel.__init__(self)
        self.undoIndex = 0

    def setUndoIndex(self, index):
        self.undoIndex = index
        self.invalidate()


class UndoProxy(UndoRedoProxy):
    def invalidate(self):
        UndoRedoProxy.invalidate(self)
        self.sort(0, QtCore.Qt.DescendingOrder)

    def filterAcceptsRow(self, row, parent=QtCore.QModelIndex()):
        return True if row < self.undoIndex else False

    def lessThan(self, left, right):
        if left.row() < right.row():
            return True
        return False


class RedoProxy(UndoRedoProxy):
    def filterAcceptsRow(self, row, parent=QtCore.QModelIndex()):
        return True if row >= self.undoIndex + 1 else False


class UndoView(QtWidgets.QListView):
    undoSelected = QtCore.pyqtSignal(int)
    def __init__(self, view, mode):
        QtWidgets.QListView.__init__(self)
        self.undoStack = view.stack()
        self.undoView = view
        if mode:
            proxy = RedoProxy()
        else:
            proxy = UndoProxy()
        proxy.setSourceModel(self.undoView.model())
        self.undoStack.indexChanged.connect(proxy.setUndoIndex)
        self.undoStack.indexChanged.connect(self.computeSize)
        self.setModel(proxy)
        self.entered.connect(self.checkRows)
        self.setMouseTracking(True)

    def computeSize(self, *args):
        rowHeight = self.sizeHintForRow(0)
        if rowHeight <= 0:
            return
        rows = min(self.model().rowCount(), 10)
        self.setMaximumHeight(rowHeight * (rows + 1))
        self.setMaximumWidth(self.sizeHintForColumn(0) + 10)

    def mousePressEvent(self, event):
        index = self.indexAt(event.pos())
        if not index.isValid():
            QtWidgets.QListView.mousePressEvent(self, event)
        else:
            index = self.model().mapToSource(index).row()
            self.undoStack.setIndex(index)
            self.undoSelected.emit(index)

    def leaveEvent(self, event):
        self.clearSelection()
        QtWidgets.QListView.leaveEvent(self, event)

    def checkRows(self, index):
        selection = QtCore.QItemSelection(index.sibling(0, 0), index)
        self.selectionModel().select(selection, QtCore.QItemSelectionModel.ClearAndSelect)


class DisplayBtn(QtWidgets.QPushButton):
    def __init__(self, icon):
        QtWidgets.QPushButton.__init__(self)
        self.setIcon(icon)
        self.setStyleSheet('''
            DisplayBtn {
                border-radius: 1px;
                border-left: 1px solid palette(midlight);
                border-right: 1px solid palette(mid);
                border-top: 1px solid palette(midlight);
                border-bottom: 1px solid palette(mid);
                background: rgba(220, 220, 180, 65);
                min-width: 40px;
            }
            DisplayBtn::menu-indicator {
                subcontrol-origin: margin;
                subcontrol-position: right;
                width: 12px;
            }
            DisplayBtn:disabled {
                color: darkGray;
            }
            DisplayBtn:hover {
                border-left: 1px solid palette(light);
                border-right: 1px solid palette(dark);
                border-top: 1px solid palette(light);
                border-bottom: 1px solid palette(dark);
            }
            DisplayBtn:pressed {
                color: green;
                padding-top: 1px;
                padding-left: 1px;
                border-left: 1px solid palette(mid);
                border-right: 1px solid palette(midlight);
                border-top: 1px solid palette(mid);
                border-bottom: 1px solid palette(midlight);
            }
            ''')
        self.setMaximumWidth(30)

class UndoDisplayBtn(DisplayBtn):
    showUndo = QtCore.pyqtSignal()
    undoRequest = QtCore.pyqtSignal(object)

    def __init__(self, icon):
        DisplayBtn.__init__(self, icon)
        self.popupTimer = QtCore.QBasicTimer()
        self.undoActions = []
        self._menu = QtWidgets.QMenu()
        self.showUndoAction = self._menu.addAction('Show undo list')
        self.showUndoAction.triggered.connect(self.showUndo)
        self._menu.aboutToHide.connect(lambda: self.setDown(False))

    def setUndoView(self, view, mode):
        self.undoStack = view.stack()
        self.undoWidgetAction = QtWidgets.QWidgetAction(self._menu)
        self.undoView = UndoView(view, mode)
        self.undoView.undoSelected.connect(lambda: self._menu.close())
        self.undoWidgetAction.setDefaultWidget(self.undoView)
        self._menu.addAction(self.undoWidgetAction)
        if mode:
            self.clicked.connect(self.undoStack.redo)
            self.undoStack.indexChanged.connect(self.redoComputeContents)
            self.undoView.undoSelected.connect(lambda index: self.undoRequest.emit(index - 1))
        else:
            self.clicked.connect(self.undoStack.undo)
            self.undoStack.indexChanged.connect(self.undoComputeContents)
            self.undoView.undoSelected.connect(lambda index: self.undoRequest.emit(index))
        self.clicked.connect(lambda: self.undoRequest.emit(None))

    def undoComputeContents(self, index):
        if index == 0:
            self.setEnabled(False)
            self.setMenu(None)
            self.setToolTip('')
        else:
            self.setEnabled(True)
            if index > 1:
                self.setMenu(self._menu)
            else:
                self.setMenu(None)
            try:
                self.setToolTip(self.undoStack.command(index - 1).undoText())
            except:
                self.setToolTip(self.undoStack.command(index - 1).text())

    def redoComputeContents(self, index):
        if index == self.undoStack.count():
            self.setEnabled(False)
            self.setMenu(None)
            self.setToolTip('')
        else:
            self.setEnabled(True)
            if index < self.undoStack.count() - 1:
                self.setMenu(self._menu)
            else:
                self.setMenu(None)
            try:
                self.setToolTip(self.undoStack.command(index).redoText())
            except:
                self.setToolTip(self.undoStack.command(index).text())

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.popupTimer.start(600, self)
            self.setDown(True)
        else:
            DisplayBtn.mousePressEvent(self, event)

    def mouseReleaseEvent(self, event):
        self.popupTimer.stop()
        if self._menu.isVisible():
            return
        QtWidgets.QPushButton.mouseReleaseEvent(self, event)

    def timerEvent(self, event):
        if event.timerId() == self.popupTimer.timerId():
            self.showMenu()
            return
        QtWidgets.QPushButton.timerEvent(self, event)

    def showMenu(self):
        self.popupTimer.stop()
        if not (self.isDown() and self.menu()):
            return
        #remove and replace the showUndoAction to force menu resizing
        self._menu.removeAction(self.showUndoAction)
        self._menu.addAction(self.showUndoAction)
        
        proxy = self.parent().graphicsProxyWidget()
        view = proxy.scene().views()[0]
        pos = view.viewport().mapToGlobal(view.mapFromScene(self.geometry().bottomLeft()))
        pos.setY(pos.y() + 2)
        self._menu.exec_(pos)


class EditStatusWidget(QtWidgets.QWidget):
    status = 0
    disabledColor = QtGui.QColor(220, 220, 200, 128)
    enabledColor = QtGui.QColor(QtCore.Qt.black)
    colors = disabledColor, enabledColor
    statusColor = disabledColor

    def __init__(self):
        QtWidgets.QWidget.__init__(self)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Maximum))
        self.statusColor = self.disabledColor
        self.setToolTip('Sound not edited')
        self.statusLetter = 'E'

    def setStatus(self, status):
        self.status = status
        self.statusColor = self.colors[bool(status)]
        if status == 0:
            self.setToolTip('Sound at initial status')
            self.statusLetter = 'E'
        elif status == 1:
            self.setToolTip('Sound saved')
            self.statusLetter = 'S'
        else:
            self.setToolTip('Sound modified')
            self.statusLetter = 'E'
        self.update()

    def sizeHint(self):
        return QtCore.QSize(self.fontMetrics().width('E') + 4, self.fontMetrics().height() + 4)

    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        qp.setPen(QtCore.Qt.NoPen)
        qp.setBrush(self.statusColor)
        qp.setRenderHints(qp.Antialiasing)
        qp.translate(.5, .5)

        font = self.font()
        font.setBold(True)
        path = QtGui.QPainterPath()
        path.addRoundedRect(QtCore.QRectF(self.rect().adjusted(0, 0, -1, -1)), 2, 2)
        path.addText(1, self.height() - self.fontMetrics().descent() - 3, font, self.statusLetter)
        qp.drawPath(path)


class DisplayWidget(QtWidgets.QWidget):
    def __init__(self, parent):
        QtWidgets.QWidget.__init__(self)
        self.setStyleSheet('''
            DisplayWidget, DisplayGroup, QSpinBox, NameEdit {
                background: transparent;
                font-family: "Fira Sans";
            }
            QLabel#nameEdit, NameEdit {
                font-size: 24px;
                padding-left: 10px;
                margin-right: 4px;
                border-top: .5px solid rgba(240, 240, 220, 128);
                border-left: .5px solid rgba(240, 240, 220, 128);
                border-bottom: .5px solid rgba(220, 220, 200, 64);
                border-right: .5px solid rgba(220, 220, 200, 64);
                border-radius: 4px;
            }
            ''')
#        palette = self.palette()
#        palette.setColor(palette.Window, QtGui.QColor(0, 0, 0, 0))
#        self.setPalette(palette)
        self.setContentsMargins(1, 1, 1, 1)
        layout = QtWidgets.QGridLayout()
        layout.setSpacing(4)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.collectionWidget = HDisplayGroup()
        self.collectionWidget.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred))
        layout.addWidget(self.collectionWidget, 0, 0, 1, 2)
        self.collectionLabel = CollectionLabel('no collection')
        self.collectionLabel.setEnabled(False)
        self.collectionWidget.addWidget(self.collectionLabel)

        self.bankWidget = VDisplayGroup()
        self.bankWidget.setEnabled(False)
        self.bankWidget.layout().setSpacing(2)
        layout.addWidget(self.bankWidget, 1, 0)
        self.bankWidget.addWidget(QtWidgets.QLabel('Bank:'), QtCore.Qt.AlignCenter)
        self.bankSpin = BankSpin(('A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'))
        self.bankWidget.addWidget(self.bankSpin)

        self.progWidget = VDisplayGroup()
        self.progWidget.setEnabled(False)
        self.progWidget.layout().setSpacing(2)
        layout.addWidget(self.progWidget, 1, 1)
        self.progWidget.addWidget(QtWidgets.QLabel('Prog:'), QtCore.Qt.AlignCenter)
        self.progSpin = ProgSpin()
        self.progWidget.addWidget(self.progSpin)

#        self.progSendWidget = ProgSendWidget()
##        self.progSendWidget.setEnabled(False)
#        layout.addWidget(self.progSendWidget, 1, 2)

        self.catWidget = HDisplayGroup()
        self.catWidget.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum))
        layout.addWidget(self.catWidget, 2, 0, 1, 2)
        self.catWidget.layout().setSpacing(8)
        self.catWidget.addWidget(QtWidgets.QLabel('Cat:'))
        self.catSpin = TextSpin(categories)
        self.catWidget.addWidget(self.catSpin)

        editLayout = QtWidgets.QHBoxLayout()
        layout.addLayout(editLayout, 0, 2)
        self.editStatusWidget = EditStatusWidget()
        editLayout.addWidget(self.editStatusWidget)
        self.editModeLabel = QtWidgets.QLabel('Sound mode Edit buffer')
        self.editModeLabel.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Maximum))
        editLayout.addWidget(self.editModeLabel)
        self.nameEdit = DisplayNameEdit()
        self.nameEdit.setWindowFlags(QtCore.Qt.BypassGraphicsProxyWidget)
        self.nameEdit.setText('Init')
        self.nameEdit.setFrame(False)
        self.nameEdit.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum))
        self.nameEdit.setObjectName('nameEdit')
        layout.addWidget(self.nameEdit, 1, 2)

        statusLayout = QtWidgets.QHBoxLayout()
        layout.addLayout(statusLayout, 2, 2)

        self.statusLabel = QtWidgets.QLabel('Status: ready')
        statusLayout.addWidget(self.statusLabel)

        self.undoBtn = UndoDisplayBtn(QtGui.QIcon.fromTheme('edit-undo'))
        self.undoBtn.setEnabled(False)
        statusLayout.addWidget(self.undoBtn)
        self.redoBtn = UndoDisplayBtn(QtGui.QIcon.fromTheme('edit-redo'))
        self.redoBtn.setEnabled(False)
        statusLayout.addWidget(self.redoBtn)

    def mousePressEvent(self, event):
        if not event.pos() in self.nameEdit.geometry() and self.nameEdit.hasFocus():
            self.nameEdit.reset()
            self.nameEdit.clearFocus()


class DisplayScene(QtWidgets.QGraphicsScene):
    def __init__(self, parent):
        QtWidgets.QGraphicsScene.__init__(self, parent)
        self.mainWidget = self.addWidget(DisplayWidget(self))
        self.shadow = QtWidgets.QGraphicsDropShadowEffect()
        self.shadow.setBlurRadius(4)
        self.shadow.setOffset(1, 1)
        self.shadow.setColor(QtGui.QColor(100, 100, 100, 150))
        self.mainWidget.setGraphicsEffect(self.shadow)
#        self.sceneRectChanged.connect(self.resizeSceneItems)

    def resizeSceneItems(self, rect):
        self.mainWidget.setGeometry(rect)
#        self.mainWidget.widget().setGeometry(rect.toRect())
#        print(self.mainWidget.widget().size())
#        self.leftLayoutItem.resize(self.leftLayoutItem.minimumSize())


class BlofeldDisplay(QtWidgets.QGraphicsView):
    openSoundRequested = QtCore.pyqtSignal(str)

    def __init__(self, *args, **kwargs):
        QtWidgets.QGraphicsView.__init__(self, *args, **kwargs)
        self.displayScene = DisplayScene(self)
        #this is for debug only
        try:
            self.main = self.window().main
            self.database = self.main.database
            self.libraryModel = self.database.libraryModel
            self.referenceModel = self.database.referenceModel
            self.tagsModel = self.database.tagsModel
        except:
            self.displayScene.mainWidget.widget().undoBtn.setMenu(QtWidgets.QMenu())
        self.setMinimumHeight(self.displayScene.mainWidget.widget().minimumSizeHint().height() + 4)
        self.setScene(self.displayScene)

        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        self.setPalette(self.palette())

        self.mainWidget = self.displayScene.mainWidget.widget()
        self.nameEdit = self.mainWidget.nameEdit
        self.editStatusWidget = self.mainWidget.editStatusWidget
        self.category = self.mainWidget.catSpin
        self.statusLabel = self.mainWidget.statusLabel
        self.undoBtn = self.mainWidget.undoBtn
        self.redoBtn = self.mainWidget.redoBtn
        self.collectionLabel = self.mainWidget.collectionLabel
        self.bankWidget = self.mainWidget.bankWidget
        self.bankSpin = self.mainWidget.bankSpin
        self.progWidget = self.mainWidget.progWidget
        self.progSpin = self.mainWidget.progSpin

    def setLocation(self, uid, collection=None):
        self.bankSpin.blockSignals(True)
        self.progSpin.blockSignals(True)
        if collection is None:
            self.bankSpin.setValue(0)
            self.progSpin.setValue(0)
            self.bankSpin.blockSignals(False)
            self.progSpin.blockSignals(False)
            return None, None
        res = self.referenceModel.match(self.referenceModel.index(0, 0), QtCore.Qt.EditRole, uid, flags=QtCore.Qt.MatchFixedString)
        #?!?!?!?!?!?!?!?!?!
        if not res:
            print('reference "{}" not found?!?'.format(uid))
            self.bankSpin.blockSignals(False)
            self.progSpin.blockSignals(False)
            return None, None

        validIndexes = self.database.getIndexesForCollection(collection)
        self.bankSpin.setValidIndexes(validIndexes)
        self.progSpin.setValidIndexes(validIndexes)
        colId = self.referenceModel.allCollections.index(collection)
        location = int(self.referenceModel.index(res[0].row(), colId + 2).data())
        bank = location >> 7
        prog = (location & 127)
        self.bankSpin.setValue(bank)
        self.progSpin.setBank(bank)
        self.progSpin.setValue(prog + 1)
        self.bankSpin.blockSignals(False)
        self.progSpin.blockSignals(False)
        return bank, prog

    def setCollections(self, collections, uid=None, fromCollection=None):
        if not collections:
            self.collectionLabel.setText('no collection')
            self.collectionLabel.setEnabled(False)
            state = False
        elif len(collections) == 1:
            fromCollection = collections[0]
            self.collectionLabel.setText(factoryPresetsNamesDict.get(fromCollection, fromCollection))
            self.collectionLabel.setEnabled(True)
            state = True
        else:
            if fromCollection is not None:
                self.collectionLabel.setText(factoryPresetsNamesDict.get(fromCollection, fromCollection))
                state = True
            else:
                self.collectionLabel.setText('various...')
                state = False
            self.collectionLabel.setEnabled(True)
            self.collectionLabel.setToolTip('This sound is used in these collections:<br/><br/>' + '<br/>'.join(collections))
        self.bankWidget.setEnabled(state)
        self.progWidget.setEnabled(state)
        bank, prog = self.setLocation(uid, fromCollection)
        return fromCollection, bank, prog

    def setStatusText(self, text):
        self.statusLabel.setText(text)

    def setPalette(self, palette):
        self.setStyleSheet('''
            border-top: 1px solid {dark};
            border-right: 1px solid {light};
            border-bottom: 1px solid {light};
            border-left: 1px solid {dark};
            border-radius: 4px;
            background: rgb(230, 240, 230);
            '''.format(
                dark=_getCssQColorStr(palette.color(palette.Dark)), 
                light=_getCssQColorStr(palette.color(palette.Midlight)), 
                ))

    def resizeEvent(self, event):
        rect = QtCore.QRectF(self.viewport().rect())
        self.setSceneRect(rect)
        self.displayScene.resizeSceneItems(rect)

    def contextMenuEvent(self, event):
        if event.pos() in self.nameEdit.geometry() and self.nameEdit.hasFocus():
            QtWidgets.QGraphicsView.contextMenuEvent(self, event)
            return
        self.customContextMenuRequested.emit(event.pos())

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.RightButton and event.pos() in self.nameEdit.geometry() and not self.nameEdit.hasFocus():
            return
        QtWidgets.QGraphicsView.mousePressEvent(self, event)


if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)
    w = BlofeldDisplay()
    w.show()
    sys.exit(app.exec_())
