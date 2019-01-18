import os

os.environ['QT_PREFERRED_BINDING'] = 'PyQt4'

from Qt import QtCore, QtGui, QtWidgets

from bigglesworth.utils import sanitize
from bigglesworth.sequencer.const import (BeatHUnit, noteNamesWithPitch, SnapModes, DefaultNoteSnapModeId, 
    SnapModeRole, Erase, Draw, Intervals, PlayheadPen, EndMarkerPen)

KeyToInterval = {
    QtCore.Qt.Key_2: 2, 
    QtCore.Qt.Key_3: 3, 
    QtCore.Qt.Key_4: 4, 
    QtCore.Qt.Key_5: 5, 
    QtCore.Qt.Key_6: 6, 
    QtCore.Qt.Key_7: 7, 
    QtCore.Qt.Key_8: 8, 
    QtCore.Qt.Key_9: 9, 
}


class NoteItem(QtWidgets.QGraphicsRectItem):
    defaultPen = QtGui.QPen(QtGui.QColor(QtCore.Qt.black), 1)
    defaultPen.setCosmetic(True)
    selectedPen = QtGui.QPen(QtGui.QColor(88, 189, 255), 2)
    selectedPen.setCosmetic(True)
    pens = defaultPen, selectedPen

    def __init__(self, noteOnEvent, noteOffEvent, scene):
        x = noteOnEvent.time * scene.beatSize
        width = (noteOffEvent.time - noteOnEvent.time) * scene.beatSize
        y = scene.noteHeight * (127 - noteOnEvent.note)
        QtWidgets.QGraphicsRectItem.__init__(self, 0, 0, width, scene.noteHeight)
        self.setPen(self.defaultPen)
        self.setPos(x, y)
        self.setAcceptHoverEvents(True)
        self.setFlags(self.flags() | self.ItemIsSelectable)
        self.noteOnEvent = noteOnEvent
        self.noteOffEvent = noteOffEvent
        self.noteOnEvent.timeChanged.connect(self.reset)
        self.noteOffEvent.timeChanged.connect(self.reset)
        self.noteOnEvent.noteChanged.connect(self.reset)
        self.noteOnEvent.velocityChanged.connect(self.setVelocityColor)
        self.setVelocityColor()

    def time(self):
        return self.noteOnEvent.time

    def note(self):
        return self.noteOnEvent.note

    def length(self):
        return self.noteOffEvent.time - self.noteOnEvent.time

    def velocity(self):
        return self.noteOnEvent.velocity

    def reset(self):
        x = self.noteOnEvent.time * self.scene().beatSize
        width = (self.noteOffEvent.time - self.noteOnEvent.time) * self.scene().beatSize
        y = self.scene().noteHeight * (127 - self.noteOnEvent.note)
        self.setRect(0, 0, width, self.scene().noteHeight)
        self.setPos(x, y)
        self.updateToolTip()

    def setVelocityColor(self, velocity=None):
        if velocity is None:
            velocity = self.noteOnEvent.velocity
        if velocity < 64:
            brightNess = (64 - velocity) * 2
            color = QtGui.QColor(brightNess, 255, brightNess, 192)
        else:
            deltaV = (velocity - 64) * 4
            color = QtGui.QColor(deltaV, 255 - deltaV, 0, 192)
        self.setBrush(color)
        self.updateToolTip()
        self.resizeMode = 0

    def updateToolTip(self):
        self.setToolTip('{}<br/>Vel: {}'.format(noteNamesWithPitch[self.noteOnEvent.note], self.noteOnEvent.velocity))

    def hoverMoveEvent(self, event):
        rect = self.rect()
        diff = sanitize(2, rect.width() / 6, self.scene().noteHeight)
        x = event.pos().x()
        if x < diff:
            self.setCursor(QtCore.Qt.SizeHorCursor)
            self.resizeMode = -1
        elif x > rect.right() - diff:
            self.setCursor(QtCore.Qt.SizeHorCursor)
            self.resizeMode = 1
        else:
            self.unsetCursor()
            self.resizeMode = 0
        QtWidgets.QGraphicsRectItem.hoverMoveEvent(self, event)

#    def mousePressEvent(self, event):
#        if not self.contains(event.pos()):
#            #Dismissing a menu keeps the current item as mousePressEvent recipient
#            #might need to further investigate about this
#            return event.ignore()
#        if event.buttons() == QtCore.Qt.RightButton:
#            self.setSelected(True)
#            event.accept()
#        else:
#            QtWidgets.QGraphicsRectItem.mousePressEvent(self, event)

    def itemChange(self, change, value):
        if change == self.ItemSelectedHasChanged:
            self.setPen(self.pens[value])
#        elif change == self.ItemPositionChange and self.isSelected():
#            value.setY(self.y())
        return QtWidgets.QGraphicsRectItem.itemChange(self, change, value)

    def paint(self, qp, option, widget):
        #this is necessary to override the dashed pen of selected items :-(
        option.state &= ~QtWidgets.QStyle.State_Selected
        QtWidgets.QGraphicsRectItem.paint(self, qp, option, widget)


class NoteRegionScene(QtWidgets.QGraphicsScene):
    whiteBrush = QtGui.QBrush(QtGui.QColor(232, 232, 232))
    blackBrush = QtGui.QBrush(QtGui.QColor(208, 208, 208))
    hLinePen = QtGui.QPen(QtCore.Qt.lightGray, 1)
    hLinePen.setCosmetic(True)
    vLinePen = QtGui.QPen(QtCore.Qt.darkGray, 1.5)
    vLinePen.setCosmetic(True)
    divLinePen = QtGui.QPen(QtCore.Qt.lightGray, 1)
    divLinePen.setCosmetic(True)

    noteHighlight = QtCore.pyqtSignal(int)
    stopNote = QtCore.pyqtSignal(int)
    playNote = QtCore.pyqtSignal([int, int], [int])

    def __init__(self, view, pattern):
        QtWidgets.QGraphicsScene.__init__(self)
        self.view = view
        self.pattern = pattern
        self.mousePos = self.currentItem = None
        self.newNotes = {}
        self.beatSnap = SnapModes[DefaultNoteSnapModeId].length
        self.edited = False
        self.movingItems = {}

        self.beatSize = self.view.piano.width()
        width = self.beatSize * pattern.length
        height = self.view.piano.height()
        self.noteHeight = self.view.piano.noteHeight
        self.setSceneRect(0, 0, width, height)

        whiteKeys = (0, 2, 3, 5, 7, 8, 10)
        for n in range(128):
            y = self.noteHeight * n - .5
            key = self.addRect(0, y, width, self.noteHeight - .5)
            key.setPen(self.hLinePen)
            key.setBrush(self.whiteBrush if n % 12 in whiteKeys else self.blackBrush)

        showSixt = pattern.length % 1 in (.25, .5)
        deltaSixtBeat = self.beatSize * .25
        deltaThirdBeat = self.beatSize / 3.
        self.eights = []
        self.thirds = []
        self.sixteenths = []
        for b in range(int(pattern.length) + 1):
            x = self.beatSize * b
            vLine = self.addLine(x, 0, x, height)
            vLine.setPen(self.vLinePen)

            sixtX = thirdX = x
            for d in range(1, 4):
                sixtX += deltaSixtBeat
                if sixtX >= width:
                    break
                vLine = self.addLine(sixtX, 0, sixtX, height)
                vLine.setPen(self.divLinePen)
                vLine.setVisible(showSixt)
                if d == 2:
                    self.eights.append(vLine)
                else:
                    self.sixteenths.append(vLine)

                thirdX += deltaThirdBeat
                if thirdX >= width:
                    break
                vLine = self.addLine(thirdX, 0, thirdX, height)
                vLine.setPen(self.divLinePen)
                self.thirds.append(vLine)
                vLine.setVisible(False)

        self.notes = []
        for noteOnEvent, noteOffEvent in pattern.notes():
            noteItem = NoteItem(noteOnEvent, noteOffEvent, self)
            self.notes.append(noteItem)
            self.addItem(noteItem)
            noteItem.setZValue(10)

        self.selectionChanged.connect(self.checkSelection)
        self.pendingNotes = set()

    @property
    def defaultVelocity(self):
        return self.view.window().defaultVelocityCombo.value()

    @property
    def defaultLength(self):
        combo = self.view.window().defaultLengthCombo
        numerator, denominator, triplet = combo.itemData(combo.currentIndex(), SnapModeRole)
        length = float(numerator) / denominator * 4
        if triplet:
            length *= 2. / 3
        return length

    def mouseMode(self):
        return self.view.window().mouseMode()

    def isClean(self):
        return not self.edited

    def checkSelection(self):
        selected = self.selectedItems()
        for noteItem in self.noteItems():
            noteItem.setZValue(20 if noteItem in selected else 10)
            if noteItem in selected:
                if noteItem not in self.pendingNotes:
                    self.playNote.emit(noteItem.noteOnEvent.note, noteItem.noteOnEvent.velocity)
                    self.pendingNotes.add(noteItem)
            else:
                try:
                    self.pendingNotes.remove(noteItem)
                    self.stopNote.emit(noteItem.noteOnEvent.note)
                except:
                    pass

    def noteItems(self):
        for item in self.items():
            if isinstance(item, NoteItem):
                yield item

    def setBeatSnapMode(self, snapMode):
        for item in self.thirds:
            item.setVisible(snapMode.triplet)
        for item in self.eights:
            item.setVisible(snapMode.denominator in (8, 16))
        for item in self.sixteenths:
            item.setVisible(snapMode.denominator == 16)
        self.beatSnap = snapMode.length

    def eraseNotes(self, pos=None):
        items = set(self.selectedItems())
        if isinstance(pos, QtCore.QPointF):
            items.add(self.itemAt(pos))
        for item in items:
            self.pattern.noteRegion.deleteNote(item.noteOnEvent)
            self.removeItem(item)
        self.edited = True

    def moveNotes(self, scenePos, deltaPos):
#        print(deltaPos)
        minTime = self.pattern.length
        maxTime = 0
        minNote = 127
        maxNote = 0
        for item in self.selectedItems():
            minTime = min(minTime, item.noteOnEvent.time)
            maxTime = max(maxTime, item.noteOffEvent.time)
            minNote = min(minNote, item.noteOnEvent.note)
            maxNote = max(maxNote, item.noteOnEvent.note)

        if minTime or maxTime < self.pattern.length:
            if self.beatSnap:
                snapRatio = self.beatSnap * self.beatSize
                targetTime = scenePos.x() // snapRatio
                sourceTime = self.mousePos.x() // snapRatio
                deltaTime = (targetTime - sourceTime) * self.beatSnap
            else:
                targetTime = scenePos.x() / self.beatSize
                sourceTime = self.mousePos.x() / self.beatSize
                deltaTime = targetTime - sourceTime
            if minTime + deltaTime < 0 or maxTime + deltaTime > self.pattern.length:
                deltaTime = None
        else:
            deltaTime = None

        if minNote or maxNote < 127:
            targetNote = scenePos.y() // self.noteHeight
            sourceNote = self.mousePos.y() // self.noteHeight
            #note coordinates are inverted!
            deltaNote = int(sourceNote - targetNote)
            if minNote + deltaNote < 0 or maxNote + deltaNote > 127:
                deltaNote = None
        else:
            deltaNote = None

        if self.moveModifiers == QtCore.Qt.ShiftModifier:
            if not self.movingItems:
                for item in self.selectedItems():
                    rectItem = self.addRect(item.rect())
                    rectItem.setPos(item.pos())
                    rectItem.setPen(QtCore.Qt.red)
                    rectItem.setZValue(50)
                    self.movingItems[item] = rectItem
            if deltaNote is not None and deltaTime is not None:
                for noteItem, rectItem in self.movingItems.items():
                    rectItem.setPos(noteItem.x() + deltaTime * self.beatSize, 
                        noteItem.y() - deltaNote * self.noteHeight)
            self._deltaNote = deltaNote if deltaNote is not None else 0
        else:
            self.pattern.noteRegion.moveNotesBy([item.noteOnEvent for item in self.selectedItems()], deltaNote=deltaNote, deltaTime=deltaTime)
            if deltaTime is not None:
                self.mousePos.setX(self.mousePos.x() + deltaTime * self.beatSize)
            if deltaNote is not None:
                self.mousePos.setY(self.mousePos.y() + -deltaNote * self.noteHeight)
            self.edited = True
        return deltaNote, deltaTime

    def resizeNotes(self, deltaX):
        snapRatio = self.beatSnap * self.beatSize
        try:
            diff, rest = divmod(deltaX, snapRatio)
            diff *= self.beatSnap
        except:
            diff, rest = deltaX / self.beatSize, 0
        if self.currentItem.resizeMode < 0:
            if diff < 0:
                if rest > snapRatio * .5:
                    diff += self.beatSnap
            elif rest > snapRatio * .5:
                diff += self.beatSnap
            if diff:
                for item in self.selectedItems():
                    #ensure that the length is at least one beatSnap
                    noteStart = min(item.noteOnEvent.time + diff, item.noteOffEvent.time - self.beatSnap)
#                    if self.pattern.noteRegion.noteLength(item.noteOnEvent) - diff < 
                    self.pattern.noteRegion.setNoteStart(item.noteOnEvent, noteStart)
#                #reset mousePos to avoid recursive action
                self.mousePos.setX(self.mousePos.x() + diff * self.beatSize)
        else:
            if diff > 0:
                if rest > snapRatio * .5:
                    diff += self.beatSnap
            elif rest > snapRatio * .5:
                diff += self.beatSnap
            if diff:
                for item in self.selectedItems():
                    #ensure that the length is at least one beatSnap
                    self.pattern.noteRegion.setNoteLength(item.noteOnEvent, max(self.beatSnap, item.noteOffEvent.time - item.noteOnEvent.time + diff))
                #reset mousePos to avoid recursive action
                self.mousePos.setX(max(self.currentItem.sceneBoundingRect().x(), self.mousePos.x() + diff * self.beatSize))
        self.edited = True

    def createNoteAtPos(self, pos, velocity=None, length=None):
        if pos not in self.sceneRect():
            return
        try:
            time = pos.x() // (self.beatSnap * self.beatSize) * self.beatSnap
        except:
            time = pos.x() / self.beatSize
        time = min(time, self.pattern.length - self.beatSnap)
        note = sanitize(0, 127 - int(pos.y() // self.noteHeight), 127)
        noteOnEvent, noteOffEvent = self.pattern.noteRegion.addNote(
            note, 
            velocity=velocity if velocity is not None else self.defaultVelocity, 
            channel=self.pattern.track.channel, 
            length=length if length is not None else self.defaultLength, 
            time=time)
        noteItem = NoteItem(noteOnEvent, noteOffEvent, self)
        self.notes.append(noteItem)
        self.addItem(noteItem)
        noteItem.setZValue(10)
#        self.playNote[int].emit(note)
        self.edited = True
        return noteItem

    def addNote(self, time, note, velocity=None, length=None):
        noteOnEvent, noteOffEvent = self.pattern.noteRegion.addNote(
            note, 
            velocity=velocity if velocity is not None else self.defaultVelocity, 
            channel=self.pattern.track.channel, 
            length=length if length is not None else self.defaultLength, 
            time=time)
        noteItem = NoteItem(noteOnEvent, noteOffEvent, self)
        self.notes.append(noteItem)
        self.addItem(noteItem)
        noteItem.setZValue(10)
        self.playNote[int].emit(note)
        self.edited = True
        return noteItem

    def mousePressEvent(self, event):
        self.moveModifiers = event.modifiers()
        self._deltaNote = 0
        self.pendingNotes.clear()
        if event.buttons() == QtCore.Qt.LeftButton:
            if self.mouseMode() == Erase:
                item = self.itemAt(event.scenePos())
                if isinstance(item, NoteItem):
                    if item not in self.selectedItems():
                        self.clearSelection()
                    self.eraseNotes(event.scenePos())
                    return
            elif self.mouseMode() == Draw:
                pos = event.scenePos()
                if not isinstance(self.itemAt(pos), NoteItem) and self.moveModifiers != QtCore.Qt.ShiftModifier:
                    self.clearSelection()
                    noteItem = self.createNoteAtPos(pos)
                    if noteItem:
                        self.newNotes[1] = noteItem
                        self.currentItem = noteItem
                        self.currentItem.setSelected(True)
                        self.currentItem.resizeMode = 1
                        self.mousePos = pos
                    x = pos.x()
                    y = pos.y()
                    for diatonicInterval, interval in self.autoChordWidget.intervals():
                        chordNoteItem = self.createNoteAtPos(
                            QtCore.QPointF(x, y - (interval * self.noteHeight)))
                        if chordNoteItem:
                            self.newNotes[diatonicInterval] = chordNoteItem
                            chordNoteItem.setSelected(True)
                    return
        selected = self.selectedItems()
        QtWidgets.QGraphicsScene.mousePressEvent(self, event)
        if event.buttons() == QtCore.Qt.RightButton:
            underMouse = self.itemAt(event.scenePos())
            if isinstance(underMouse, NoteItem):
                if underMouse in selected or event.modifiers() == QtCore.Qt.ControlModifier:
                    self.selectionChanged.disconnect(self.checkSelection)
                    for item in set(selected + [underMouse]):
                        item.setSelected(True)
                    self.selectionChanged.connect(self.checkSelection)
                else:
                    underMouse.setSelected(True)
        elif self.selectedItems():
            self.mousePos = event.scenePos()
            for item in self.items(self.mousePos):
                if isinstance(item, NoteItem):
                    self.currentItem = item
                    self.playNote.emit(item.noteOnEvent.note, item.noteOnEvent.velocity)
                    break
            else:
                self.currentItem = self.selectedItems()[0]

    def mouseDoubleClickEvent(self, event):
        if not self.selectedItems() and not self.mouseMode() == Erase:
            pos = event.scenePos()
            noteItem = self.createNoteAtPos(pos)
            if noteItem:
                self.newNotes[1] = noteItem
                self.currentItem = noteItem
                self.currentItem.setSelected(True)
                self.currentItem.resizeMode = 1
                self.mousePos = pos
            x = pos.x()
            y = pos.y()
            for diatonicInterval, interval in self.autoChordWidget.intervals():
                chordNoteItem = self.createNoteAtPos(
                    QtCore.QPointF(x, y - (interval * self.noteHeight)))
                if chordNoteItem:
                    self.newNotes[diatonicInterval] = chordNoteItem
                    chordNoteItem.setSelected(True)

    def mouseMoveEvent(self, event):
        if event.buttons() == QtCore.Qt.LeftButton and self.currentItem:
            if not self.currentItem.resizeMode:
                if self.moveModifiers == QtCore.Qt.ShiftModifier and self.movingItems:
                    prevNotes = set([item.noteOnEvent.note + self._deltaNote for item in self.selectedItems()])
                    self.moveNotes(event.scenePos(), event.scenePos() - self.mousePos)
                    newNotes = set([item.noteOnEvent.note + self._deltaNote for item in self.selectedItems()])
                else:
                    prevNotes = set([item.noteOnEvent.note for item in self.selectedItems()])
                    self.moveNotes(event.scenePos(), event.scenePos() - self.mousePos)
                    newNotes = set([item.noteOnEvent.note for item in self.selectedItems()])
                if prevNotes != newNotes:
                    for note in prevNotes:
                        self.stopNote.emit(note)
                    for note in newNotes:
                        self.playNote[int].emit(note)
            else:
                self.resizeNotes((event.scenePos() - self.mousePos).x())
                if self.newNotes:
                    mouseNote = 127 - int(event.scenePos().y() // self.noteHeight)
                    deltaNote = mouseNote - self.newNotes[1].note()
                    if deltaNote:
                        self.pattern.noteRegion.moveNotesBy([item.noteOnEvent for item in self.newNotes.values()], deltaNote=deltaNote)
                        self.mousePos.setY(event.scenePos().y())
                        for noteItem in self.newNotes.values():
                            self.playNote[int].emit(noteItem.note())
        self.noteHighlight.emit(sanitize(0, 127 - int(event.scenePos().y() // self.noteHeight), 127))
        QtWidgets.QGraphicsScene.mouseMoveEvent(self, event)

    def mouseReleaseEvent(self, event):
        if self.moveModifiers and self.movingItems:
            deltaNote, deltaTime = self.moveNotes(event.scenePos(), event.scenePos() - self.mousePos)
            if deltaNote or deltaTime and self.selectedItems():
                for item in self.selectedItems():
                    item.setSelected(False)
                    noteOnEvent = item.noteOnEvent
                    noteOnEvent, noteOffEvent = self.pattern.noteRegion.addNote(
                        noteOnEvent.note + (deltaNote if deltaNote is not None else 0), 
                        velocity=noteOnEvent.velocity, 
                        channel=noteOnEvent.channel, 
                        length=item.noteOffEvent.time - noteOnEvent.time, 
                        time=noteOnEvent.time + (deltaTime if deltaTime is not None else 0))
                    noteItem = NoteItem(noteOnEvent, noteOffEvent, self)
                    self.notes.append(noteItem)
                    self.addItem(noteItem)
                    noteItem.setSelected(True)
                    noteItem.setZValue(10)
                self.edited = True
            for noteItem in self.movingItems.keys():
                rectItem = self.movingItems.pop(noteItem)
                self.removeItem(rectItem)
        self.mousePos = self.currentItem = self.moveModifiers = None
        self.newNotes.clear()
        QtWidgets.QGraphicsScene.mouseReleaseEvent(self, event)

    def copyNotes(self):
        mimeData = QtCore.QMimeData()
        byteArray = QtCore.QByteArray()
        stream = QtCore.QDataStream(byteArray, QtCore.QIODevice.WriteOnly)
        deltaT = min(noteItem.time() for noteItem in self.selectedItems())
        for noteItem in self.selectedItems():
            stream.writeQVariant((noteItem.time() - deltaT, noteItem.note(), noteItem.velocity(), noteItem.length()))
#        stream.writeInt(self.parent().track.index())
        mimeData.setData('bigglesworth/NoteRegion', byteArray)
        QtWidgets.QApplication.clipboard().setMimeData(mimeData)

    def pasteNotes(self, pos=None):
        if isinstance(pos, (QtCore.QPoint, QtCore.QPointF)):
            time = pos.x() // (self.beatSnap * self.beatSize) * self.beatSnap
            time = min(time, self.pattern.length - self.beatSnap)
        else:
            time = 0

        byteArray = QtWidgets.QApplication.clipboard().mimeData().data('bigglesworth/NoteRegion')
        stream = QtCore.QDataStream(byteArray)
        
        while not stream.atEnd():
            noteTime, note, velocity, length = stream.readQVariant()
            self.addNote(time + noteTime, note, velocity, length)

    def contextMenuEvent(self, event):
        menu = QtWidgets.QMenu()
        selected = self.selectedItems()
        copyAction = menu.addAction(QtGui.QIcon.fromTheme('edit-copy'), 'Copy')
        copyAction.setEnabled(len(selected))
        copyAction.triggered.connect(self.copyNotes)
        pasteAction = menu.addAction(QtGui.QIcon.fromTheme('edit-paste'), 'Paste')
        if event.scenePos() in self.sceneRect() and QtWidgets.QApplication.clipboard().mimeData().hasFormat('bigglesworth/NoteRegion'):
            pasteAction.triggered.connect(lambda: self.pasteNotes(event.scenePos()))
        else:
            pasteAction.setEnabled(False)

        menu.addSeparator()
        deleteAction = menu.addAction(QtGui.QIcon.fromTheme('edit-delete'), 
            'Delete note{}'.format('' if len(selected) == 1 else 's'))
        if selected:
            deleteAction.triggered.connect(self.eraseNotes)
        else:
            deleteAction.setEnabled(False)
        menu.exec_(QtGui.QCursor.pos())

    def wheelEvent(self, event):
        if isinstance(self.itemAt(event.scenePos()), NoteItem):
            event.accept()
            if event.delta() > 0:
                delta = 1
            else:
                delta = -1
            if event.modifiers() == QtCore.Qt.ShiftModifier:
                delta *= 8
            item = self.itemAt(event.scenePos())
            if item in self.selectedItems():
                items = set(self.selectedItems())
            else:
                self.clearSelection()
                item.setSelected(True)
                items = [item]
            for noteItem in items:
                noteItem.noteOnEvent.setVelocity(sanitize(0, noteItem.noteOnEvent.velocity + delta, 127))
#                noteItem.setVelocityColor()
            QtWidgets.QToolTip.showText(QtGui.QCursor.pos(), item.toolTip())
        else:
            event.ignore()
#            QtWidgets.QGraphicsScene.wheelEvent(self, event)

    def editChord(self, interval):
        #interval is in "musical" sense
        fundNoteItem = self.newNotes[1]
        fundamental = fundNoteItem.note()
        x = fundNoteItem.x()
        y = fundNoteItem.y()
        noteItem = self.newNotes.get(interval)
        noteDeltas = Intervals[interval]
        if not noteItem:
            noteItem = self.createNoteAtPos(QtCore.QPointF(x, y - self.noteHeight * noteDeltas[0]), length=fundNoteItem.length())
            if noteItem:
                self.newNotes[interval] = noteItem
                noteItem.setSelected(True)
                for item in self.newNotes.values():
                    if item != noteItem:
                        self.playNote[int].emit(item.note())
        else:
            for index, noteDelta in enumerate(noteDeltas[1:]):
                if noteItem.noteOnEvent.note == fundamental + noteDeltas[index]:
                    noteDelta -= noteDeltas[index]
                    self.pattern.noteRegion.moveNotesBy([noteItem.noteOnEvent], deltaNote=noteDelta)
                    break
            else:
                self.pattern.noteRegion.deleteNote(noteItem.noteOnEvent)
                self.removeItem(noteItem)
                self.newNotes.pop(interval)
            for noteItem in self.newNotes.values():
                self.playNote[int].emit(noteItem.note())

    def keyPressEvent(self, event):
        if event.key() in (QtCore.Qt.Key_Up, QtCore.Qt.Key_Down):
            items = self.selectedItems()
            if items:
                noteOnEvents = []
                deltaNote = 1 if event.key() == QtCore.Qt.Key_Up else -1
                if event.modifiers() == QtCore.Qt.ShiftModifier:
                    deltaNote *= 12
                for item in items:
                    noteOnEvents.append(item.noteOnEvent)
                    if deltaNote < 0 and item.noteOnEvent.note + deltaNote < 0:
                        deltaNote = max(deltaNote, -item.noteOnEvent.note)
                    elif deltaNote > 0 and item.noteOnEvent.note + deltaNote > 127:
                        deltaNote = min(deltaNote, 127 - item.noteOnEvent.note)
                self.pattern.noteRegion.moveNotesBy([item.noteOnEvent for item in items], deltaNote=deltaNote)
                self.view.focusNotes(True)
                return
        elif event.key() in (QtCore.Qt.Key_Left, QtCore.Qt.Key_Right):
            items = self.selectedItems()
            if items:
                noteOnEvents = []
                deltaTime = self.beatSnap if event.key() == QtCore.Qt.Key_Right else -self.beatSnap
                for item in items:
                    noteOnEvents.append(item.noteOnEvent)
                    if deltaTime < 0 and item.noteOnEvent.time + deltaTime < 0:
                        deltaTime = max(deltaTime, -item.noteOnEvent.time)
                    elif deltaTime > 0 and item.noteOffEvent.time + deltaTime > self.pattern.length:
                        deltaTime = min(deltaTime, self.pattern.length - item.length() - item.noteOnEvent.time)
                self.pattern.noteRegion.moveNotesBy(noteOnEvents, deltaTime=deltaTime)
                self.view.focusNotes(True)
                return
        elif event.key() in KeyToInterval and self.newNotes and not event.isAutoRepeat():
            self.editChord(KeyToInterval[event.key()])
        QtWidgets.QGraphicsScene.keyPressEvent(self, event)


class PatternRectItem(QtWidgets.QGraphicsRectItem):
    basePen = QtGui.QPen(QtCore.Qt.darkGray, .5)
    basePen.setCosmetic(True)
    baseBrush = QtGui.QBrush(QtGui.QColor(128, 128, 128, 96))
    mousePos = None
    __args = None

    def __init__(self, parent, x, y, w, h, pattern):
        QtWidgets.QGraphicsRectItem.__init__(self, x, y, w, h, parent)
        self.pattern = pattern
        self.repeatedRects = []
        if isinstance(parent, self.__class__):
            self.setPen(self.basePen)
            self.setBrush(self.baseBrush)
        else:
            pattern.repetitionsAboutToChange.connect(self.checkRepetitions)
            self.setFlags(self.flags() | self.ItemIsSelectable)
            self.setPen(self.defaultPen)
            self.setBrush(self.defaultBrush)
            self.setAcceptHoverEvents(True)

    def finalize(self):
        if not isinstance(self.parentItem(), self.__class__):
            if self.pattern.repetitions > 1:
                self.checkRepetitions(self.pattern.repetitions)

    def checkRepetitions(self, repetitions):
        self.prepareGeometryChange()
        count = len(self.repeatedRects)
        if count < repetitions - 1:
            x, y, w, h = self.rect().getCoords()
            for r in range(count + 1, repetitions):
                rectItem = self.__class__(self, 0, 0, w, h, self.pattern, self.__args)
                rectItem.setX(r * w)
                self.repeatedRects.append(rectItem)
        else:
            while len(self.repeatedRects) > repetitions - 1:
                rectItem = self.repeatedRects.pop(-1)
                self.scene().removeItem(rectItem)
                del rectItem

    def hoverMoveEvent(self, event):
        rect = self.rect()
        diff = sanitize(2, rect.width() / 6, BeatHUnit * self.pattern.length)
        x = event.pos().x()
        if x < diff:
            self.setCursor(QtCore.Qt.SizeHorCursor)
            self.resizeMode = -1
        elif x > rect.right() - diff:
            self.setCursor(QtCore.Qt.SizeHorCursor)
            self.resizeMode = 1
        else:
            self.unsetCursor()
            self.resizeMode = 0
        QtWidgets.QGraphicsRectItem.hoverMoveEvent(self, event)

    def mousePressEvent(self, event):
        if not self.contains(event.pos()):
            #Dismissing a menu keeps the current item as mousePressEvent recipient
            #might need to further investigate about this
            return event.ignore()
        if event.buttons() == QtCore.Qt.RightButton:
            self.setSelected(True)
            event.accept()
        else:
            QtWidgets.QGraphicsRectItem.mousePressEvent(self, event)

    def mouseDoubleClickEvent(self, event):
        self.scene().editRequested.emit(self)


class NotePatternItem(PatternRectItem):
    defaultPen = QtGui.QPen(QtCore.Qt.lightGray, .5)
    defaultPen.setCosmetic(True)
    selectedPen = QtGui.QPen(QtGui.QColor(255, 128, 128), 1)
    selectedPen.setCosmetic(True)
    pens = defaultPen, selectedPen
    defaultBrush = QtGui.QBrush(QtGui.QColor(128, 128, 128, 128))
    selectedBrush = QtGui.QBrush(QtGui.QColor(192, 192, 192, 128))
    brushes = defaultBrush, selectedBrush

    def __init__(self, parent, x, y, w, h, pattern, *args):
        PatternRectItem.__init__(self, parent, x, y, w, h, pattern)
        self.notePath = QtGui.QPainterPath()
        self.notePathItem = QtWidgets.QGraphicsPathItem(self)
        self.notePathItem.setPen(QtCore.Qt.white)
        self.setNotes()
        self.finalize()

    def setNotes(self):
        if isinstance(self.parentItem(), self.__class__):
            self.notePathItem.setPath(self.parentItem().notePath)
            self.notePathItem.setTransform(self.parentItem().notePathItem.transform())
        else:
            self.notePath = QtGui.QPainterPath()
            notes = self.pattern.notes()
            if not notes:
                self.notePathItem.setPath(self.notePath)
            else:
                right = self.rect().right()
                for noteOnEvent, noteOffEvent in self.pattern.notes():
                    if noteOffEvent.time < 0:
                        continue
                    if noteOnEvent.time > self.pattern.length:
                        break
                    note = 127 - noteOnEvent.note
                    self.notePath.moveTo(max(0, noteOnEvent.time * BeatHUnit), note)
                    self.notePath.lineTo(min(noteOffEvent.time * BeatHUnit, right), note)
#                    print(noteOnEvent.time * BeatHUnit, noteOnEvent.note)
                self.notePathItem.setPath(self.notePath)
                self.notePathItem.setTransform(QtGui.QTransform.fromScale(1, self.rect().height() / 128.))

    def setRect(self, rect):
        QtWidgets.QGraphicsRectItem.setRect(self, rect)
        self.setNotes()
        height = rect.height()
        scale = QtGui.QTransform.fromScale(1, height / 128.)
        self.notePathItem.setTransform(scale)
        for rectItem in self.repeatedRects:
            rect = rectItem.rect()
            rect.setHeight(height)
            rectItem.setRect(rect)
            rectItem.notePathItem.setTransform(scale)

    def itemChange(self, change, value):
        if change == self.ItemSelectedHasChanged:
            self.setPen(self.pens[value])
            self.setBrush(self.brushes[value])
        elif change == self.ItemSceneChange:
            if value is None and not isinstance(self, self.__class__):
                #disconnect before updating
                self.pattern.repetitionsAboutToChange.disconnect(self.checkRepetitions)
#        elif change == self.ItemPositionChange and self.isSelected():
#            value.setY(self.y())
        return QtWidgets.QGraphicsRectItem.itemChange(self, change, value)

    def _mouseMoveEvent(self, event):
        x = self.x()
        y = self.y()
        QtWidgets.QGraphicsRectItem.mouseMoveEvent(self, event)
        size = self.pattern.length * BeatHUnit
        if self.x() % size > size / 2:
            if self.x() > x:
                x += size
        elif x and self.x() < x:
            x -= size
        print(x)
        self.setPos(x, y)

    def paint(self, qp, option, widget):
        #this is necessary to override the dashed pen of selected items :-(
        option.state &= ~QtWidgets.QStyle.State_Selected
        QtWidgets.QGraphicsRectItem.paint(self, qp, option, widget)


class AutoPatternItem(PatternRectItem):
    defaultPen = QtGui.QPen(QtCore.Qt.lightGray, .5)
    defaultPen.setCosmetic(True)
    eventLinePen = QtGui.QPen(QtCore.Qt.red, .5)
    eventLinePen.setCosmetic(True)
#    selectedPen = QtGui.QPen(QtGui.QColor(255, 128, 128), 1)
#    selectedPen.setCosmetic(True)
#    pens = defaultPen, selectedPen
    defaultBrush = QtGui.QBrush(QtGui.QColor(96, 96, 96, 128))
#    selectedBrush = QtGui.QBrush(QtGui.QColor(192, 192, 192, 128))
#    brushes = defaultBrush, selectedBrush

    def __init__(self, parent, x, y, w, h, pattern, regionInfo):
        PatternRectItem.__init__(self, parent, x, y, w, h, pattern)
        self.setFlags(self.flags() & ~self.ItemIsSelectable)
        self.pattern = pattern
        self.regionInfo = self.__args = regionInfo
        self.eventPath = QtGui.QPainterPath()
        self.eventPathItem = QtWidgets.QGraphicsPathItem(self)
        self.eventPathItem.setPen(self.eventLinePen)
        self.setEvents()
        self.finalize()

    def setEvents(self):
        if isinstance(self.parentItem(), self.__class__):
            self.eventPathItem.setPath(self.parentItem().eventPath)
            self.eventPathItem.setTransform(self.parentItem().eventPathItem.transform())
        else:
            self.eventPath = QtGui.QPainterPath()
            region = self.pattern.getAutomationRegion(self.regionInfo)
            events = [event for event in region.events if 0 <= event.time <= self.pattern.length]
            if not events:
                self.eventPathItem.setPath(self.eventPath)
            else:
                right = self.rect().right()
                self.eventPath.moveTo(0, 127 - events[0].value)
                for index, event in enumerate(events):
                    value = 127 - event.value
                    self.eventPath.lineTo(min(event.time * BeatHUnit, right), value)
                    if not region.continuous:
                        try:
                            newEvent = events[index + 1]
                            self.eventPath.lineTo(newEvent.time * BeatHUnit, value)
                            self.eventPath.lineTo(newEvent.time * BeatHUnit, 127 - newEvent.value)
                        except:
                            break
                self.eventPath.lineTo(right, value)
                self.eventPathItem.setPath(self.eventPath)
                self.eventPathItem.setTransform(QtGui.QTransform.fromScale(1, self.rect().height() / 128.))

    def setRect(self, rect):
        QtWidgets.QGraphicsRectItem.setRect(self, rect)
        self.setEvents()
        height = rect.height()
        scale = QtGui.QTransform.fromScale(1, height / 128.)
        self.eventPathItem.setTransform(scale)
        for rectItem in self.repeatedRects:
            rect = rectItem.rect()
            rect.setHeight(height)
            rectItem.setRect(rect)
            rectItem.eventPathItem.setTransform(scale)


class TrackContainer(QtWidgets.QGraphicsWidget):
    def __init__(self, view, structure, trackContainerWidget):
        QtWidgets.QGraphicsWidget.__init__(self)
        self.view = view
        self.structure = structure
        self.trackContainerWidget = trackContainerWidget
        self.rebuild()

    def rebuild(self):
        print('rebuilding')
        self.patterns = {}
        self.automations = {}
        scene = self.scene()
        for child in self.childItems():
            scene.removeItem(child)
        for track in self.structure.tracks:
            trackWidget = self.trackContainerWidget.trackWidgets[track]
            automations = track.automations()
            trackAutomations = self.automations[track] = {}
            automationTrackWidgets = self.trackContainerWidget.automationTrackWidgets[track]
            autoSizes = {}
            for automation in automations:
                try:
                    autoWidget = automationTrackWidgets[automation]
                    autoSizes[automation] = autoWidget.geometry().y() + trackWidget.margin, autoWidget.geometry().height() - trackWidget.margin * 2
                    trackAutomations[automation] = []
                except:
                    print('track possibly without automation widgets set yet')

            trackPatterns = self.patterns[track] = []
            y = trackWidget.geometry().y()
            height = trackWidget.geometry().height() - trackWidget.margin
            for pattern in track.patterns:
                width = pattern.length * BeatHUnit
                patternRectItem = NotePatternItem(self, 
                    0, 0, width, height, pattern)
                x = pattern.time * BeatHUnit
                patternRectItem.setPos(x, y)
                trackPatterns.append(patternRectItem)

                for automation in automations:
                    autoY, autoHeight = autoSizes[automation]
                    autoRectItem = AutoPatternItem(self, 
                        0, 0, width, autoHeight, pattern, automation)
                    autoRectItem.setPos(x, autoY)
                    if not automationTrackWidgets[automation].isVisible():
                        autoRectItem.setVisible(False)
                    trackAutomations[automation].append(autoRectItem)

        self.checkGeometry()
#        self.setGeometry(self.childrenBoundingRect())
#                vUnit += 32
#                print(pattern, pattern.time, pattern.length, pattern.repetitions)
#                trackRect = self.addRect(pattern.time * BeatHUnit, vUnit, pattern.length * BeatHUnit * 4, 32)
#                trackRect.setPen(QtGui.QPen(QtCore.Qt.white))
#                rects.append(trackRect)

    def resizeTracks(self):
        print('resizing')
        for track, patterns in self.patterns.items():
            trackWidget = self.trackContainerWidget.trackWidgets[track]
            y = trackWidget.geometry().y()
            height = trackWidget.geometry().height() - trackWidget.margin
            for patternRectItem in patterns:
                patternRect = patternRectItem.rect()
                patternRect.setHeight(height)
                patternRectItem.setRect(patternRect)
                patternRectItem.setY(y)
            automations = track.automations()
            trackAutomations = self.automations[track]
            automationTrackWidgets = self.trackContainerWidget.automationTrackWidgets[track]
            for automation in automations:
                autoWidget = automationTrackWidgets[automation]
                y = autoWidget.geometry().y() + trackWidget.margin
                height = autoWidget.geometry().height() - trackWidget.margin * 2
                try:
                    for autoRectItem in trackAutomations[automation]:
                        autoRect = autoRectItem.rect()
                        autoRect.setHeight(height)
                        autoRectItem.setRect(autoRect)
                        autoRectItem.setY(y)
                        autoRectItem.setVisible(autoWidget.isVisible())
                except:
                    pass

        self.checkGeometry()

    def checkGeometry(self):
        self.setGeometry(QtCore.QRectF(0, 0, self.childrenBoundingRect().right(), self.trackContainerWidget.height()))


class SequencerScene(QtWidgets.QGraphicsScene):
    editRequested = QtCore.pyqtSignal(object)
    cursorPen = QtGui.QPen(QtCore.Qt.blue, 1)
    cursorPen.setCosmetic(True)

    def __init__(self, view, structure, trackContainerWidget):
        QtWidgets.QGraphicsScene.__init__(self)
        self.view = view
#        self.setSceneRect(QtCore.QRectF(0, 0, 1200, 1200))

        self.structure = structure
        self.trackContainerWidget = trackContainerWidget
        self.trackContainerWidget.installEventFilter(self)

        self.trackContainer = TrackContainer(self.view, structure, trackContainerWidget)
        self.addItem(self.trackContainer)
        self.structure.changed.connect(self.trackContainer.rebuild)
        self.structure.changed.connect(self.checkSceneSize)

        self.cursorLine = self.addLine(0, -10, 0, 5000)
        self.cursorLine.setPen(self.cursorPen)
        self.cursorLine.setVisible(False)

        self.playhead = self.addLine(0, -10, 0, 5000)
        self.playhead.setPen(PlayheadPen)

        self.setSceneRect(QtCore.QRectF(0, 0, 1024, 10))

        self.endLine = self.addLine(0, -10, 0, 5000)
        self.endLine.setPen(EndMarkerPen)

        self.patterns = {}
        self.currentItem = None
        self._dragCopy = False
        self.resizeItems = {}

    def checkSceneSize(self):
#        self.trackContainer.resizeTracks()
        rect = self.sceneRect()
        if self.trackContainer.geometry().width() > self.sceneRect().width():
            rect.setWidth(self.trackContainer.geometry().width())
        if self.trackContainer.geometry().height() >= self.sceneRect().height() - 10:
            rect.setHeight(self.trackContainer.geometry().height() + 10)
        self.view.setSceneRect(rect)

    def movePatterns(self, pos):
        snapRatio = self.beatSnap * BeatHUnit
        diffX, rest = divmod(pos.x() - self.currentItem.x(), snapRatio)
        diffX *= self.beatSnap

        currentTrack = self.currentItem.pattern.track.index()
        diffY = 0

        minTime = 10000
        maxTime = 0
        minTrack = 16
        maxTrack = 0
        trackCount = self.structure.trackCount()
        trackSizes = self.view.trackSizes()
        
        for track, top, bottom in trackSizes:
            if not track.index() and pos.y() < top:
                diffY = -currentTrack
                break
            elif top <= pos.y() <= bottom:
                diffY = track.index() - currentTrack
                break
        else:
            diffY = trackCount - currentTrack - 1

        if not self.resizeItems:
            for item in self.selectedItems():
                rectItem = self.addRect(item.rect())
                rectItem.setPos(item.pos())
                rectItem.setPen(QtCore.Qt.white)
                self.resizeItems[item] = rectItem

        for item in self.selectedItems():
            minTime = min(minTime, item.pattern.time)
            maxTime = max(maxTime, item.pattern.time)
            trackIndex = item.pattern.track.index()
            minTrack = min(minTrack, trackIndex)
            maxTrack = max(maxTrack, trackIndex)

        if diffX < 0:
            diffX = max(diffX, -minTime)
        if diffY < 0:
            diffY = max(diffY, -minTrack)
        elif diffY > 0:
            diffY = min(diffY, trackCount - maxTrack - 1)

        for patternItem, rectItem in self.resizeItems.items():
            rectItem.setX(patternItem.x() + diffX * BeatHUnit)
            newTrackIndex = patternItem.pattern.track.index() + diffY
            _, top, bottom = trackSizes[newTrackIndex]
            rectItem.setY(top)
            rect = rectItem.rect()
            rect.setHeight(bottom - top)
            rectItem.setRect(rect)
        return diffX, diffY

    def resizePatterns(self, x):
        if x < 0:
            return
        snapRatio = self.beatSnap * BeatHUnit
        diff, rest = divmod(x - self.currentItem.x(), snapRatio)
        diff *= self.beatSnap

        if not self.resizeItems:
            for item in self.selectedItems():
                rectItem = self.addRect(item.rect())
                rectItem.setPos(item.pos())
                rectItem.setPen(QtCore.Qt.white)
                self.resizeItems[item] = rectItem
        if self.currentItem.resizeMode < 0:
            if rest > snapRatio * .5:
                diff += self.beatSnap
            for item in self.selectedItems():
                if item.pattern.time + diff < 0:
                    diff = -item.pattern.time
                elif item.pattern.length - diff <= 0:
                    diff = item.pattern.length - self.beatSnap
            for patternItem, rectItem in self.resizeItems.items():
                rect = rectItem.rect()
                rect.setLeft(patternItem.rect().left() + diff * BeatHUnit)
                rectItem.setRect(rect)
        else:
            if rest > snapRatio * .5:
                diff += self.beatSnap
            diff = max(self.beatSnap, diff)
            for rectItem in self.resizeItems.values():
                rect = rectItem.rect()
                rect.setWidth(diff * BeatHUnit)
                rectItem.setRect(rect)
        return diff

    def eventFilter(self, source, event):
        if event.type() == QtCore.QEvent.Resize:
            #the resizing has to be delayed to ensure that all widgets visibility are applied
            QtCore.QTimer.singleShot(0, self.trackContainer.resizeTracks)
            rect = self.trackContainer.geometry()
            if rect.width() < 1024:
                rect.setWidth(1024)
            rect.setHeight(rect.height() + 10)
            self.view.setSceneRect(rect)
            self.view.viewport().update()
        return QtWidgets.QGraphicsScene.eventFilter(self, source, event)

    def mousePressEvent(self, event):
        if not self.itemAt(event.scenePos()):
            #see the mousePressEvent workaround for PatternRectItem
            #after a menu is dismissed
            self.clearSelection()
        QtWidgets.QGraphicsScene.mousePressEvent(self, event)
        if self.selectedItems():
            self.mousePos = event.scenePos()
            for item in self.items(self.mousePos):
                if isinstance(item, PatternRectItem):
                    self.currentItem = item
                    break
            else:
                self.currentItem = self.selectedItems()[0]
            self._dragCopy = event.modifiers() == QtCore.Qt.ShiftModifier and not self.currentItem.resizeMode

    def mouseMoveEvent(self, event):
        if event.buttons() == QtCore.Qt.LeftButton and self.currentItem:
            if not self.currentItem.resizeMode:
                self.movePatterns(event.scenePos())
            else:
                self.resizePatterns(event.scenePos().x())
#        self.noteHighlight.emit(sanitize(0, 127 - int(event.scenePos().y() // self.noteHeight), 127))
        QtWidgets.QGraphicsScene.mouseMoveEvent(self, event)

    def mouseReleaseEvent(self, event):
        if self.resizeItems:
            if not self.currentItem.resizeMode:
                diffX, diffY = self.movePatterns(event.scenePos())
                if diffX or diffY:
                    if self._dragCopy:
                        for patternItem in self.selectedItems():
                            pattern = patternItem.pattern.clone()
                            if diffX:
                                pattern.time += diffX
                            if diffY:
                                track = self.structure.tracks[pattern.track.index() + diffY]
                            else:
                                track = pattern.track
                            track.addPattern(pattern)
                    else:
                        for patternItem in self.selectedItems():
                            if diffX:
                                patternItem.pattern.time += diffX
                            if diffY:
                                currentTrack = patternItem.pattern.track.index()
                                self.structure.tracks[currentTrack + diffY].addPattern(
                                    self.structure.tracks[currentTrack].removePattern(patternItem.pattern))
                    QtCore.QTimer.singleShot(0, self.structure.changed)
            else:
                diff = self.resizePatterns(event.scenePos().x())
                if diff:
                    if self.currentItem.resizeMode < 0:
                        for patternItem in self.selectedItems():
                            patternItem.pattern.moveStartBy(diff)
                    else:
                        for patternItem in self.selectedItems():
                            patternItem.pattern.length = diff
                    QtCore.QTimer.singleShot(0, self.structure.changed)
        self.mousePos = self.currentItem = None
        for patternItem in self.resizeItems.keys():
            rectItem = self.resizeItems.pop(patternItem)
            self.removeItem(rectItem)
        QtWidgets.QGraphicsScene.mouseReleaseEvent(self, event)


