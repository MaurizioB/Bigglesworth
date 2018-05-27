# *-* encoding: utf-8 *-*

from unidecode import unidecode

from Qt import QtCore, QtGui, QtWidgets
from PyQt4.QtGui import QStyleOptionFrameV3 as _QStyleOptionFrameV3
from PyQt4.QtGui import QStyleOptionFrameV2 as _QStyleOptionFrameV2
QtWidgets.QStyleOptionFrameV3 = _QStyleOptionFrameV3
QtWidgets.QStyleOptionFrameV2 = _QStyleOptionFrameV2

try:
    from bigglesworth.const import ord2chr
except:
    ord2chr = {c:unichr(c) for c in range(32, 127)}

def getASCII(char):
    if 32 <= ord(char) <= 126 or char == u'°':
        return char
#    print('wtf? "{}"'.format(unidecode(char)))
    return unidecode(char)

class NameEdit(QtWidgets.QLineEdit):
    subcharPen = QtGui.QPen(QtCore.Qt.lightGray, 1)
    escapePressed = QtCore.pyqtSignal()
    TYPE, BACKSPACE, DELETE, CUT, PASTE = range(5)
    
    class UndoCommand(QtWidgets.QUndoCommand):
        def __init__(self, parent, mode, newText, oldText, oldCursorPosition, newCursorPosition, oldSelectionRange):
            QtWidgets.QUndoCommand.__init__(self)
            self.mode = mode
            self.lineEdit = parent
            self.newText = newText
            self.oldText = oldText
            self.oldCursorPosition = oldCursorPosition
            self.newCursorPosition = newCursorPosition
            self.oldSelectionStart, self.oldSelectionRange = oldSelectionRange
            self.newSelectionStart = self.newSelectionRange = 0
            self.initialized = False

        def id(self):
            return self.mode

        def mergeWith(self, command):
            if self.mode != command.mode or self.oldSelectionRange:
                if command.oldSelectionRange:
                    self.newSelectionStart, self.newSelectionRange = command.oldSelectionStart, command.oldSelectionRange
                return False
            elif self.mode == self.lineEdit.TYPE:
                if self.newCursorPosition == command.oldCursorPosition:
                    self.newText = command.newText
                    self.newCursorPosition = command.newCursorPosition
                    return True
                self.newSelectionStart, self.newSelectionRange = command.oldSelectionStart, command.oldSelectionRange
                return False
            elif self.mode == self.lineEdit.BACKSPACE:
                if self.newCursorPosition == command.oldCursorPosition and not command.oldSelectionRange:
                    self.newText = command.newText
                    self.newCursorPosition = command.newCursorPosition
                    return True
                self.newSelectionStart, self.newSelectionRange = command.oldSelectionStart, command.oldSelectionRange
                return False
            elif self.mode == self.lineEdit.DELETE:
                if self.newCursorPosition == command.newCursorPosition and not command.oldSelectionRange:
                    self.newText == command.newText
                    self.newCursorPosition = command.newCursorPosition
                    return True
                self.newSelectionStart, self.newSelectionRange = command.oldSelectionStart, command.oldSelectionRange
                return False
            return False

        def undo(self):
            self.lineEdit.blockSignals(True)
            QtWidgets.QLineEdit.setText(self.lineEdit, self.oldText)
            if self.oldSelectionRange:
                self.lineEdit.setSelection(self.oldSelectionStart, self.oldSelectionRange)
            else:
                self.lineEdit.setCursorPosition(self.oldCursorPosition)
            self.lineEdit.blockSignals(False)
            self.lineEdit.updateGraphics()
            self.lineEdit.textChanged.emit(self.oldText.ljust(16, ' ')[:16])

        def redo(self):
            self.lineEdit.blockSignals(True)
            QtWidgets.QLineEdit.setText(self.lineEdit, self.newText)
            if self.newSelectionRange:
                self.lineEdit.setSelection(self.newSelectionStart, self.newSelectionRange)
            else:
                self.lineEdit.setCursorPosition(self.newCursorPosition)
            self.lineEdit.blockSignals(False)
            self.lineEdit.updateGraphics()
            if self.mode == self.lineEdit.TYPE and not self.initialized:
                self.initialized = True
                return
            self.lineEdit.textChanged.emit(self.newText.ljust(16, ' ')[:16])

    def __init__(self, *args, **kwargs):
        QtWidgets.QLineEdit.__init__(self, *args, **kwargs)
        self.oldText = '  Init          '
        QtWidgets.QLineEdit.setText(self, self.oldText)
        self.textEdited.connect(self.validate)
        self.returnPressed.connect(lambda: setattr(self, 'focusInUndo', self.undoStack.index()))
        self.undoStack = QtWidgets.QUndoStack()
        self.focusInUndo = 0
        self.selectionX = self.selectionWidth = 0
        self.selectionChanged.connect(self.setSelectionSize)
        self.cursorPositionChanged.connect(lambda: [setattr(self, 'cursorState', True), self.cursorTimer.start()])

        self.oldCursorPosition = 0
        self.oldSelectionRange = 0, 0
        self.cursorTimer = QtCore.QTimer()
        self.cursorTimer.setInterval(500)
        self.cursorTimer.timeout.connect(self._setCursorColor)
        self.cursorState = False

        self.tripleClickTimer = QtCore.QTimer()
        self.tripleClickTimer.setSingleShot(True)
        self.tripleClickTimer.setInterval(QtWidgets.QApplication.doubleClickInterval())

        self.undoShortcut = QtGui.QKeySequence.keyBindings(QtGui.QKeySequence.Undo)[0].toString()
        self.redoShortcut = QtGui.QKeySequence.keyBindings(QtGui.QKeySequence.Redo)[0].toString()
        self.cutShortcut = QtGui.QKeySequence.keyBindings(QtGui.QKeySequence.Cut)[0].toString()
        self.copyShortcut = QtGui.QKeySequence.keyBindings(QtGui.QKeySequence.Copy)[0].toString()
        self.pasteShortcut = QtGui.QKeySequence.keyBindings(QtGui.QKeySequence.Paste)[0].toString()
        self.deleteShortcut = QtGui.QKeySequence.keyBindings(QtGui.QKeySequence.Delete)[0].toString()
        self.selectAllShortcut = QtGui.QKeySequence.keyBindings(QtGui.QKeySequence.SelectAll)[0].toString()
        self.spacings = [self.fontMetrics().width(l) for l in self.text().ljust(16, ' ')]

    def setSelectionSize(self):
        if self.selectedText():
            selStart = self.selectionStart()
            selLen = len(self.selectedText())
            self.selectionX = sum(self.spacings[:selStart]) + 2 * selStart
            self.selectionWidth = sum(self.spacings[selStart:selStart + selLen]) + 2 * (selLen - 1)
        else:
            self.selectionX = self.selectionWidth = 0

    def sizeHint(self):
        sizeHint = QtWidgets.QLineEdit.sizeHint(self)
        sizeHint.setWidth(max(self.fontMetrics().width(ord2chr[l]) for l in range(32, 126)) * 16 + 2 * 15)
        return sizeHint

    def setText(self, text, reset=True):
        if reset:
            finalText = ''
            for letter in text:
                uLetter = getASCII(letter)
                if uLetter:
                    finalText += uLetter
                else:
                    finalText += '?'
            finalText = finalText[:16].ljust(16, ' ')
            self.blockSignals(True)
            QtWidgets.QLineEdit.setText(self, finalText)
            self.blockSignals(False)
            self.undoStack.clear()
            self.oldText = finalText
            self.oldCursorPosition = len(finalText.rstrip())
            self.oldSelectionRange = 0, 0
            self.updateGraphics()
        else:
            self.validate(text)

    def getSelectionRange(self):
        selected = len(self.selectedText())
        if not selected:
            return self.cursorPosition(), 0
        selStart = self.selectionStart()
        cursor = self.cursorPosition()
        if selStart != cursor:
            return selStart, cursor - selStart
        return selStart + selected, -selected

    def validate(self, text, mode=TYPE):
        finalText = ''
        for letter in text:
            uLetter = getASCII(letter)
            if uLetter:
                finalText += uLetter
            else:
                finalText += '?'
        finalText = finalText[:16].ljust(16, ' ')
        self.undoStack.push(self.UndoCommand(self, mode, finalText, self.oldText, self.oldCursorPosition, self.cursorPosition(), self.oldSelectionRange))

    def updateGraphics(self):
        if self.hasFocus():
            self.cursorState = True
            self.cursorTimer.start()
        self.spacings = [self.fontMetrics().width(l) for l in self.text().ljust(16, ' ')]
        self.setSelectionSize()

    def _setCursorColor(self):
        if not self.hasFocus():
            self.cursorTimer.stop()
            self.cursorState = False
        else:
            self.cursorState = not self.cursorState
        self.update()

    def paste(self):
        text = QtWidgets.QApplication.clipboard().text()
        if not text:
            return
        oldText = self.text()
        selRange = len(text)
        self.oldCursorPosition = self.cursorPosition()
        self.oldSelectionRange = self.getSelectionRange()
        if self.selectedText():
            pre = oldText[:self.selectionStart()]
            post = oldText[self.selectionStart() + len(self.selectedText()):].rstrip()
            paste = text[:16 - len((pre + post))][:selRange]
        else:
            pos = self.oldCursorPosition
            pre = oldText[:pos]
            paste = text[:16 - pos - len(oldText[pos:].rstrip())][:selRange]
            post = oldText[pos:]
        text = pre + paste + post
        finalText = ''
        for letter in text:
            uLetter = getASCII(letter)
            if uLetter:
                finalText += uLetter
            else:
                finalText += '?'
        self.undoStack.push(self.UndoCommand(self, self.PASTE, finalText, self.text(), self.oldCursorPosition, len(pre + paste), self.oldSelectionRange))

    def cut(self):
        if not self.selectedText():
            return
        self.oldCursorPosition = self.cursorPosition()
        self.oldSelectionRange = self.getSelectionRange()
        self.oldText = self.text()
        self.blockSignals(True)
        QtWidgets.QLineEdit.cut(self)
        self.blockSignals(False)
        self.undoStack.push(self.UndoCommand(self, self.CUT, self.text(), self.oldText, self.oldCursorPosition, self.cursorPosition(), self.oldSelectionRange))

    def showEvent(self, event):
        self.updateGraphics()

    def focusInEvent(self, event):
        self.focusInUndo = self.undoStack.index()
        self.cursorState = True
        self.cursorTimer.start()
        self.update()
        QtWidgets.QLineEdit.focusInEvent(self, event)

    def keyPressEvent(self, event):
        self.oldSelectionRange = self.getSelectionRange()
        self.oldCursorPosition = self.cursorPosition()
        self.oldText = self.text()
        if len(event.text()) and event.key() not in \
            (QtCore.Qt.Key_Backspace, QtCore.Qt.Key_Delete, QtCore.Qt.Key_Enter, QtCore.Qt.Key_Tab, QtCore.Qt.Key_Return) and \
            event.modifiers() in (QtCore.Qt.NoModifier, QtCore.Qt.ShiftModifier):
                letter = getASCII(event.text())
#                print('qui', letter)
                if letter:
                    if self.selectedText() or (self.cursorPosition() < 16 and self.text().ljust(16, ' ').endswith(' ')):
                        if self.cursorPosition() < 15 and not self.selectedText() and self.text().endswith(' '):
                            self.blockSignals(True)
                            QtWidgets.QLineEdit.setText(self, self.text()[:-1])
                            self.setCursorPosition(self.oldCursorPosition)
                            self.blockSignals(False)
                        QtWidgets.QLineEdit.keyPressEvent(self, event)
#                print('???')
                return
        elif event.matches(QtGui.QKeySequence.Paste):
            self.paste()
            return
        elif event.matches(QtGui.QKeySequence.Cut):
            self.cut()
            return
        elif event.matches(QtGui.QKeySequence.Undo):
            self.undoStack.undo()
            return
        elif event.matches(QtGui.QKeySequence.Redo):
            self.undoStack.redo()
            return
        elif event.matches(QtGui.QKeySequence.Delete):
            self.blockSignals(True)
            QtWidgets.QLineEdit.keyPressEvent(self, event)
            self.blockSignals(False)
            self.validate(self.text(), self.DELETE)
            return
        elif event.key() == QtCore.Qt.Key_Backspace:
            self.blockSignals(True)
            QtWidgets.QLineEdit.keyPressEvent(self, event)
            self.blockSignals(False)
            self.validate(self.text(), self.BACKSPACE)
            return
#        elif event.key() == QtCore.Qt.Key_Escape:
#            self.escapePressed.emit()
#            self.clearFocus()
#            return
        QtWidgets.QLineEdit.keyPressEvent(self, event)

    def keyReleaseEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self.escapePressed.emit()
            self.undoStack.setIndex(self.focusInUndo)
            self.clearFocus()
        QtWidgets.QLineEdit.keyReleaseEvent(self, event)

    def reset(self):
        self.undoStack.setIndex(self.focusInUndo)

    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        qp.setRenderHints(qp.Antialiasing)
        option = QtWidgets.QStyleOptionFrameV3()
        self.initStyleOption(option)
        self.style().drawPrimitive(QtWidgets.QStyle.PE_PanelLineEdit, option, qp, self)
        qp.translate(.5, .5)
        textRect = self.style().subElementRect(QtWidgets.QStyle.SE_LineEditContents, option, self)
        y = textRect.y()
        height = textRect.height()
        fontMetrics = self.fontMetrics()
        lineY = textRect.y() + textRect.height() - fontMetrics.descent() / 2
        qp.translate(textRect.x(), 0)
        fontPen = qp.pen()
        hasFocus = self.hasFocus()
        if self.selectionWidth and hasFocus:
            qp.save()
            qp.setPen(QtCore.Qt.NoPen)
            qp.setBrush(QtGui.QColor(149, 188, 241, 128))
            qp.translate(self.selectionX, 0)
            qp.drawRect(0, y, self.selectionWidth, height)
            qp.restore()
        qp.setBrush(QtCore.Qt.lightGray)
        for l, (char, w) in enumerate(zip(self.text().ljust(16, ' '), self.spacings)):
            if hasFocus:
                qp.setPen(self.subcharPen)
                qp.drawLine(0, lineY, w, lineY)
                if self.cursorState and l == self.cursorPosition():
                    qp.setPen(fontPen)
                    qp.drawLine(-1, y, -1, y + height)
            qp.setPen(fontPen)
            qp.drawText(0, y, w + 2, height, QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter, char)
            qp.translate(w + 2, 0)
        if self.cursorState and self.cursorPosition() == 16:
            qp.setPen(fontPen)
            qp.drawLine(-1, y, -1, y + height)

    def getIndexFromPos(self, pos):
        option = QtWidgets.QStyleOptionFrameV3()
        self.initStyleOption(option)
        textRect = self.style().subElementRect(QtWidgets.QStyle.SE_LineEditContents, option, self)
        textRect.setWidth(sum(self.spacings) + 30)
        x = pos.x()
        l = 0
        if not pos in textRect or textRect.x() > x > textRect.right():
            if x < textRect.x():
                l = 0
            elif x > textRect.right():
                l = 16
        else:
            delta = textRect.x()
            for l, s in enumerate(self.spacings):
                if x < delta + s // 2:
                    break
                delta += s + 2
        return l

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            if self.tripleClickTimer.isActive():
                self.selectAll()
                return
            if not event.modifiers() == QtCore.Qt.ShiftModifier:
                self.setCursorPosition(self.getIndexFromPos(event.pos()))
            else:
                selStart, selRange = self.getSelectionRange()
                if selRange:
                    self.setSelection(selStart, self.getIndexFromPos(event.pos()) - selStart)
                else:
                    self.setSelection(self.cursorPosition(), self.getIndexFromPos(event.pos()) - self.cursorPosition())
            self.setSelectionSize()

    def mouseMoveEvent(self, event):
        if event.buttons() == QtCore.Qt.LeftButton:
            cursorPosition = self.cursorPosition()
            mouseCursorPosition = self.getIndexFromPos(event.pos())
            if not self.selectedText():
                self.setSelection(cursorPosition, mouseCursorPosition - cursorPosition)
            else:
                selStart = self.selectionStart()
                if selStart >= cursorPosition:
                    selStart = selStart + len(self.selectedText())
                if selStart > mouseCursorPosition:
                    self.setSelection(selStart, mouseCursorPosition - selStart)
                elif selStart == mouseCursorPosition:
                    self.setSelection(selStart, 0)
                else:
                    self.setSelection(selStart, mouseCursorPosition - selStart)

    def mouseDoubleClickEvent(self, event):
        #TODO: check double click selection!
        QtWidgets.QLineEdit.mouseDoubleClickEvent(self, event)
        self.tripleClickTimer.start()

    def createStandardContextMenu(self):
        self.oldSelectionRange = self.getSelectionRange()
        self.oldCursorPosition = self.cursorPosition()
        self.oldText = self.text()
        menu = QtWidgets.QLineEdit.createStandardContextMenu(self)
#        print([s.toString() for s in QtGui.QKeySequence.keyBindings(QtGui.QKeySequence.Paste)])
        for action in menu.actions():
#            print('testing', action.text(), action.shortcut().toString())
            if self.pasteShortcut in action.text():
                action.triggered.disconnect()
                action.triggered.connect(self.paste)
            elif self.cutShortcut in action.text():
                action.triggered.disconnect()
                action.triggered.connect(self.cut)
            elif self.undoShortcut in action.text():
                action.triggered.disconnect()
                action.triggered.connect(self.undoStack.undo)
                action.setEnabled(self.undoStack.canUndo())
            elif self.redoShortcut in action.text():
                action.triggered.disconnect()
                action.triggered.connect(self.undoStack.redo)
                action.setEnabled(self.undoStack.canRedo())
#                print('ok!')
#        action.triggered.disconnect()
#        action.triggered.connect(self.paste)
        return menu

