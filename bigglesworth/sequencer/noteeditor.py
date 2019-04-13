import os

os.environ['QT_PREFERRED_BINDING'] = 'PyQt4'

from Qt import QtCore, QtGui, QtWidgets

from bigglesworth.utils import sanitize, loadUi
from bigglesworth.midiutils import MidiEvent, NOTEOFF, NOTEON
from bigglesworth.parameters import Parameters
from bigglesworth.dialogs import AdvancedMessageBox
from bigglesworth.sequencer.const import (noteNames, Intervals, IntervalNames, IntervalNamesShort, IntervalTypes, Chords, Cardinals, 
    SnapModes, SnapModeRole, DefaultNoteSnapModeId, Erase, Draw, Select, PlayheadPen, 
    BlofeldParameter, CtrlParameter, ParameterRole, getCtrlNameFromMapping)
from bigglesworth.sequencer.dialogs import AddAutomationDialog
from bigglesworth.sequencer.widgets import ScrollBarSpacer, ZoomWidget
from bigglesworth.sequencer.graphics import NoteRegionScene
from bigglesworth.sequencer.structure import BlofeldParameterRegion


class VerticalPiano(QtWidgets.QWidget):
    playNote = QtCore.pyqtSignal(int)
    stopNote = QtCore.pyqtSignal(int)

    def __init__(self, parent):
        QtWidgets.QWidget.__init__(self, parent)
        self.setAutoFillBackground(True)
        self.setMouseTracking(True)
        self.setBackgroundRole(QtGui.QPalette.Window)
        self.cKeys = [QtWidgets.QLabel('C{} '.format(o), self) for o in range(8, -3, -1)]

        self.noteHighlightWidget = QtWidgets.QLabel(self)
        self.noteHighlightWidget.setVisible(False)
        self.noteHighlightWidget.setAutoFillBackground(True)
        self.noteHighlightWidget.setBackgroundRole(QtGui.QPalette.Window)
        palette = self.palette()
        palette.setColor(palette.Window, QtGui.QColor(255, 170, 0))
        self.noteHighlightWidget.setPalette(palette)

        self.setNoteHeight()
        self.pendingNote = None

    def setNoteHeight(self, ratio=1):
        self.noteHeight = self.fontMetrics().height() * ratio
        self.setFixedSize(self.fontMetrics().height() * 4, self.noteHeight * 128)

        width = self.width()
        pixmap = QtGui.QPixmap(width, self.noteHeight * 12)
        pixmap.fill(QtCore.Qt.white)
        qp = QtGui.QPainter(pixmap)
        qp.setBrush(QtCore.Qt.black)
        qp.setRenderHints(qp.Antialiasing)
        qp.translate(.5, 1.5)
        qp.drawLine(width - 1, -1, width - 1, pixmap.height())

        self.blackWidth = width * .6
        blackSize = self.noteHeight * .5
        halfBlackSize = blackSize * .5
        y = 0
        for note in range(12):
            y += self.noteHeight
            if note in (1, 4, 6, 9, 11):
                qp.drawRect(0, y - blackSize * 2 - 1, self.blackWidth, blackSize + halfBlackSize)
            elif note in (2, 7):
                qp.drawLine(0, y - halfBlackSize, width, y - halfBlackSize)
            else:
                qp.drawLine(0, y + halfBlackSize, width, y + halfBlackSize)
        qp.end()
        palette = self.palette()
        palette.setBrush(palette.Window, QtGui.QBrush(pixmap))
        self.setPalette(palette)

        fm = self.fontMetrics()
        cY = self.noteHeight * 7 - fm.descent()
        for o, cKey in enumerate(self.cKeys):
            cKey.move(width - fm.width(cKey.text()), cY)
            cY += self.noteHeight * 12

        noteHighlightHeight = self.noteHeight * .6
        self.noteHighlightDelta = (self.noteHeight - int(noteHighlightHeight)) / 2 - 1
        self.noteHighlightWidget.setFixedSize(self.blackWidth - 2, int(noteHighlightHeight) + 1)
        font = self.font()
        font.setPointSizeF(noteHighlightHeight)
        self.noteHighlightWidget.setFont(font)
        self.update()

    def mousePressEvent(self, event):
        if event.buttons() == QtCore.Qt.LeftButton:
            note = 127 - int(event.y() // self.noteHeight)
            self.playNote.emit(note)
            self.pendingNote = note

    def mouseMoveEvent(self, event):
        note = 127 - int(event.y() // self.noteHeight)
        self.noteHighlight(note)
        if event.buttons() == QtCore.Qt.LeftButton:
            if self.pendingNote is not None and self.pendingNote != note:
                self.stopNote.emit(self.pendingNote)
                self.playNote.emit(note)
            self.pendingNote = note
        QtWidgets.QWidget.mouseMoveEvent(self, event)

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton and self.pendingNote is not None:
            self.stopNote.emit(self.pendingNote)
            self.pendingNote = None

    def event(self, event):
        if event.type() == QtCore.QEvent.ToolTip and self.noteHighlightWidget.isVisible():
            note = 127 - int(event.y() // self.noteHeight)
            rect = self.noteHighlightWidget.geometry()
            if note % 12 in (0, 2, 4, 5, 7, 9, 11):
                rect.setWidth(self.width())
            QtWidgets.QToolTip.showText(event.globalPos(), '{} ({})'.format(noteNames[note], note), self, rect)
        return QtWidgets.QWidget.event(self, event)

    def leaveEvent(self, event):
        self.noteHighlight()
        QtWidgets.QWidget.leaveEvent(self, event)

    def noteHighlight(self, note=None):
        if note is None:
            self.noteHighlightWidget.setVisible(False)
        else:
            self.noteHighlightWidget.setVisible(True)
            self.noteHighlightWidget.setText(noteNames[note])
            self.noteHighlightWidget.move(1, self.noteHeight * (127 -note) + self.noteHighlightDelta)


class ChordButton(QtWidgets.QWidget):
    activeChanged = QtCore.pyqtSignal(bool)
    intervalChanged = QtCore.pyqtSignal(int, int)
    
    def __init__(self, diatonicInterval):
        QtWidgets.QWidget.__init__(self)
        self.diatonicInterval = diatonicInterval
        self.intervals = Intervals[diatonicInterval]
        self.diatonicIntervalName = Cardinals[diatonicInterval]
        self.baseInterval = self.intervals[0]
        self.toggleTexts = 'Enable {} interval'.format(self.diatonicIntervalName), 'Disable {} interval'.format(self.diatonicIntervalName)
        intervalTypes = IntervalTypes[diatonicInterval]
        if len(intervalTypes) > 1:
            self.toggleIntervalText = 'Toggle between '
            self.toggleIntervalText += ', '.join([i.lower() for i in intervalTypes[:-1]])
            self.toggleIntervalText += ' and {} {}'.format(intervalTypes[-1].lower(), self.diatonicIntervalName.lower())
        else:
            self.toggleIntervalText = ''
        self._currentIndex = 0
        self._active = False

        fm = self.fontMetrics()
        self.setFixedSize(fm.width(' Perf '), fm.height() * 2 + 2)

        self.setStyleSheet('''
            ChordButton {
                border: 1px solid palette(dark);
                border-radius: 2px;
            }
            ChordButton[active="false"] {
                border-style: outset;
            }
            ChordButton[active="true"] {
                border-style: inset;
            }
        ''')
        self.rebuild()
        self.menu = QtWidgets.QMenu(self)
        actionGroup = QtWidgets.QActionGroup(self)
        for index, interval in enumerate(self.intervals):
            action = self.menu.addAction(IntervalNames[(diatonicInterval, interval)])
            action.setCheckable(True)
            action.setData(index)
            actionGroup.addAction(action)

    @QtCore.pyqtProperty(bool)
    def active(self):
        return self._active

    def setActive(self, active):
        self.active = active

    @active.setter
    def active(self, active):
        if active != self._active:
            self._active = active
            self.activeChanged.emit(active)
            self.style().unpolish(self)
            self.style().polish(self)
            self.update()

    def toggle(self):
        self.active = not self._active

    @property
    def interval(self):
        return self.intervals[self._currentIndex]

    def setInterval(self, interval):
        try:
            self.setCurrentIndex(self.intervals.index(interval))
        except:
            pass

    @property
    def currentIndex(self):
        return self._currentIndex

    @currentIndex.setter
    def currentIndex(self, index):
        if index != self._currentIndex:
            self._currentIndex = index
            self.intervalChanged.emit(self.diatonicInterval, self.intervals[index])
            self.rebuild()

    def setCurrentIndex(self, index):
        self.currentIndex = index

    def rebuild(self):
        self.chordType = IntervalNamesShort[(self.diatonicInterval, self.interval)]
        self.update()

    def cycle(self):
        index = self._currentIndex + 1
        if index == len(self.intervals):
            index = 0
        self.currentIndex = index

#    def previous(self):
#        index = self._currentIndex - 1
#        if index < 0:
#            index = len(self.intervals) - 1
#        self.currentIndex = index

    def event(self, event):
        if event.type() == QtCore.QEvent.ToolTip and self.isEnabled():
            if event.y() < self.height() / 2:
                QtWidgets.QToolTip.showText(event.globalPos(), self.toggleTexts[self._active], self, self.rect().adjusted(0, 0, 0, -self.height() / 2))
            else:
                QtWidgets.QToolTip.showText(event.globalPos(), self.toggleIntervalText, self, self.rect().adjusted(0, 0, 0, -self.height() / 2))
        return QtWidgets.QWidget.event(self, event)

    def mousePressEvent(self, event):
        if event.buttons() == QtCore.Qt.LeftButton:
            if event.y() < self.height() / 2:
                self.toggle()
            elif not self._active:
                self.active = True
            else:
                self.cycle()

    def contextMenuEvent(self, event):
        for action in self.menu.actions():
            if action.data() == self._currentIndex:
                action.setChecked(True)
        res = self.menu.exec_(event.globalPos())
        if res:
            self.setCurrentIndex(res.data())

    def paintEvent(self, event):
        option = QtWidgets.QStyleOption()
        option.init(self)
        qp = QtWidgets.QStylePainter(self)
        option.rect.setHeight(option.rect.height() / 2)
        qp.drawPrimitive(QtWidgets.QStyle.PE_Widget, option)

        state = QtGui.QPalette.Normal if self._active and self.isEnabled()else QtGui.QPalette.Disabled
        if self._active:
            font = self.font()
            font.setBold(True)
            qp.setFont(font)
            qp.drawText(option.rect, QtCore.Qt.AlignCenter, self.diatonicIntervalName)
            qp.setFont(self.font())
        else:
            qp.drawText(option.rect, QtCore.Qt.AlignCenter, self.diatonicIntervalName)
        qp.setPen(self.palette().color(state, QtGui.QPalette.WindowText))
        qp.drawText(self.rect().adjusted(0, option.rect.bottom() + 2, 0, 0), QtCore.Qt.AlignCenter, self.chordType)


class AutoChordWidget(QtWidgets.QFrame):
    def __init__(self, *args, **kwargs):
        QtWidgets.QFrame.__init__(self, *args, **kwargs)
        layout = QtWidgets.QHBoxLayout()
        self.setLayout(layout)
        self.setContentsMargins(0, 0, 0, 0)
        layout.setContentsMargins(2, 0, 2, 0)

        self.chordButtons = []

        for diatonicInterval in range(2, 10):
            chordButton = ChordButton(diatonicInterval)
            layout.addWidget(chordButton)
            self.chordButtons.append(chordButton)

    def intervals(self):
        if not self.isEnabled():
            return []
        intervals = []
        for chordButton in self.chordButtons:
            if chordButton.active:
                intervals.append((chordButton.diatonicInterval, chordButton.interval))
        return intervals

    def setIntervals(self, intervals):
        if not isinstance(intervals, dict):
            intervals = dict(intervals)
        for chordButton in self.chordButtons:
            if chordButton.diatonicInterval in intervals:
                chordButton.setActive(True)
                chordButton.setInterval(intervals[chordButton.diatonicInterval])
            else:
                chordButton.setActive(False)

    def setChord(self, intervals):
        for chordButton in self.chordButtons:
            active = chordButton.diatonicInterval in intervals
            chordButton.setActive(active)
            if active:
                chordButton.setInterval(intervals[chordButton.diatonicInterval])


class NoteEditorAutomationHandle(QtWidgets.QFrame):
    def __init__(self, parent):
        QtWidgets.QFrame.__init__(self, parent)
        self.setFrameStyle(self.StyledPanel|self.Raised)
        self.mousePos = None
        self.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.setCursor(QtCore.Qt.SizeVerCursor)


class NoteEditorAutomationHover(QtWidgets.QWidget):
    shown = False
    addAutomationRequested = QtCore.pyqtSignal()

    def __init__(self, parent):
        QtWidgets.QWidget.__init__(self, parent)
        layout = QtWidgets.QHBoxLayout()
        self.setLayout(layout)
        self.setContentsMargins(0, 0, 0, 0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum)
        self.setAutoFillBackground(True)

        self.addAutomationBtn = QtWidgets.QPushButton(QtGui.QIcon.fromTheme('list-add'), '')
        layout.addWidget(self.addAutomationBtn)
        size = self.fontMetrics().height() * 2
        self.addAutomationBtn.setFixedSize(size, size)
        self.addAutomationBtn.clicked.connect(self.addAutomationRequested)

        self.automationCombo = QtWidgets.QComboBox()
        layout.addWidget(self.automationCombo)
        self.automationCombo.setEnabled(False)
        self.automationCombo.setSizeAdjustPolicy(self.automationCombo.AdjustToContents)
        self.automationCombo.view().installEventFilter(self)

        self.leaveTimer = QtCore.QTimer()
        self.leaveTimer.setSingleShot(True)
        self.leaveTimer.setInterval(250)
        self.leaveTimer.timeout.connect(self.hide)

    def eventFilter(self, source, event):
        if event.type() == QtCore.QEvent.Hide and not self.underMouse():
            self.leaveTimer.start()
        return QtWidgets.QWidget.eventFilter(self, source, event)

    def enterEvent(self, event):
        self.leaveTimer.stop()

    def leaveEvent(self, event):
        if not self.automationCombo.view().isVisible():
            self.leaveTimer.start()

    def showEvent(self, event):
        if not self.shown:
            self.setFixedWidth(self.sizeHint().width())


class NoteEditorAutomationLabel(QtWidgets.QWidget):
    def __init__(self):
        QtWidgets.QWidget.__init__(self)
        self.text = 'No automation'
        self.data = None
        self.setMinimumHeight(self.fontMetrics().height())
        self.setEnabled(False)

    def setAutomation(self, text, data):
        self.text = text
        self.data = data
        self.setEnabled(True)
        self.update()

    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        qp.drawText(self.rect(), QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter, 
            self.fontMetrics().elidedText(self.text, QtCore.Qt.ElideRight, self.width()))


class AutoItem(QtWidgets.QGraphicsEllipseItem):
    defaultPen = QtGui.QPen(QtGui.QColor(QtCore.Qt.black), 1)
    defaultPen.setCosmetic(True)
    selectedPen = QtGui.QPen(QtGui.QColor(255, 81, 61), 2)
    selectedPen.setCosmetic(True)
    pens = defaultPen, selectedPen

    def __init__(self, event, scene):
        QtWidgets.QGraphicsEllipseItem.__init__(self, -2.5, -2.5, 5, 5)
        self.setFlags(self.flags() | self.ItemIgnoresTransformations | self.ItemIsSelectable)
        self.setPos(event.time * scene.beatSize, 127 - event.value)
        self.scene = scene
        self.event = event
        self.event.valueChanged.connect(self.reset)

    def reset(self):
        self.setPos(self.event.time * self.scene.beatSize, 127 - self.event.value)

    def itemChange(self, change, value):
        if change == self.ItemSelectedHasChanged:
            self.setPen(self.pens[value])
        return QtWidgets.QGraphicsRectItem.itemChange(self, change, value)

    def paint(self, qp, option, widget):
        #this is necessary to override the dashed pen of selected items :-(
        option.state &= ~QtWidgets.QStyle.State_Selected
        QtWidgets.QGraphicsEllipseItem.paint(self, qp, option, widget)


class AutomationScene(QtWidgets.QGraphicsScene):
    vLinePen = QtGui.QPen(QtCore.Qt.darkGray, 1.5)
    vLinePen.setCosmetic(True)
    divLinePen = QtGui.QPen(QtCore.Qt.lightGray, 1)
    divLinePen.setCosmetic(True)
    automationPen = QtGui.QPen(QtGui.QColor(255, 80, 9), 1)
    automationPen.setCosmetic(True)

    def __init__(self, view, pattern):
        QtWidgets.QGraphicsScene.__init__(self)
        self.view = view
        self.pattern = pattern
        self.track = pattern.track
        self.automationPoints = {}
        self.edited = False
        self.currentRegion = None
        self.mousePos = self.currentItem = self.moveModifiers = None
        self.beatSnap = SnapModes[DefaultNoteSnapModeId].length

        self.beatSize = self.view.window().noteView.piano.width()
        width = self.beatSize * pattern.length
        showSixt = pattern.length % 1 in (.25, .5)
        deltaSixtBeat = self.beatSize * .25
        deltaThirdBeat = self.beatSize / 3.
        self.eights = []
        self.thirds = []
        self.sixteenths = []
        for b in range(int(pattern.length) + 1):
            x = self.beatSize * b
            vLine = self.addLine(x, 0, x, 127)
            vLine.setPen(self.vLinePen)

            sixtX = thirdX = x
            for d in range(1, 4):
                sixtX += deltaSixtBeat
                if sixtX >= width:
                    break
                vLine = self.addLine(sixtX, 0, sixtX, 127)
                vLine.setPen(self.divLinePen)
                vLine.setVisible(showSixt)
                if d == 2:
                    self.eights.append(vLine)
                else:
                    self.sixteenths.append(vLine)

                thirdX += deltaThirdBeat
                if thirdX >= width:
                    break
                vLine = self.addLine(thirdX, 0, thirdX, 127)
                vLine.setPen(self.divLinePen)
                self.thirds.append(vLine)
                vLine.setVisible(False)

        self.autoLine = self.addPath(QtGui.QPainterPath())
        self.autoLine.setPen(self.automationPen)

        self.setSceneRect(0, 0, self.beatSize * pattern.length, 128)

    def isClean(self):
        return not self.edited

    def mouseMode(self):
        return self.view.window().mouseMode()

    @property
    def currentPoints(self):
        return self.automationPoints[self.currentRegion]

    def setAutomation(self, automationInfo):
        try:
            for item in self.currentPoints:
                self.removeItem(item)
        except:
            pass
        self.currentRegion = self.pattern.getAutomationRegion(automationInfo)
        try:
            self.currentRegion.continuousModeChanged.connect(self.continuousModeChanged, QtCore.Qt.UniqueConnection)
        except:
            pass
        try:
            automationPoints = self.automationPoints[self.currentRegion]
        except:
            automationPoints = self.automationPoints[self.currentRegion] = []
            for event in self.currentRegion.events:
                if 0 <= event.time <= self.pattern.length:
                    item = AutoItem(event, self)
                    automationPoints.append(item)
        for autoItem in automationPoints:
            self.addItem(autoItem)
        self.redrawLine()

    def continuousModeChanged(self, continuous):
        self.redrawLine(False)
        self.edited = True

    def redrawLine(self, keep=True):
        currentPoints = self.currentPoints
        if currentPoints:
            self.autoLine.setVisible(True)
            #"speed up" the redrawing, if len(elementCount) != points act as keep is False
            #someday we might want to check out if this actually helps.....
            try:
                assert keep, 'keep'
                path = self.autoLine.path()
                if self.currentRegion.continuous:
                    assert len(currentPoints) + 2 == path.elementCount(), 'len'
                    path.setElementPositionAt(0, 0, currentPoints[0].y())
                    for index, point in enumerate(currentPoints, 1):
                        path.setElementPositionAt(index, point.x(), point.y())
                    path.setElementPositionAt(index + 1, self.sceneRect().right(), point.y())
                else:
                    assert len(currentPoints) * 2 + 1 == path.elementCount(), 'len'
                    currentY = currentPoints[0].y()
                    path.setElementPositionAt(0, 0, currentY)
                    path.setElementPositionAt(1, currentPoints[0].x(), currentY)
                    index = 2
                    for point in currentPoints[1:]:
                        currentX = point.x()
                        path.setElementPositionAt(index, currentX, currentY)
                        currentY = point.y()
                        path.setElementPositionAt(index + 1, currentX, currentY)
                        index += 2
                    path.setElementPositionAt(index, self.sceneRect().right(), currentY)
            except Exception as e:
#                print('redrawing because:', e)
                path = QtGui.QPainterPath()
                if self.currentRegion.continuous:
                    path.moveTo(0, currentPoints[0].y())
                    for point in currentPoints:
                        path.lineTo(point.x(), point.y())
                    path.lineTo(self.sceneRect().right(), point.y())
                else:
                    currentY = currentPoints[0].y()
                    path.moveTo(0, currentY)
                    path.lineTo(currentPoints[0].x(), currentY)
                    for point in currentPoints[1:]:
                        currentX = point.x()
                        path.lineTo(currentX, currentY)
                        currentY = point.y()
                        path.lineTo(currentX, currentY)
                    path.lineTo(self.sceneRect().right(), currentY)
            self.autoLine.setPath(path)
        else:
            self.autoLine.setVisible(False)
            return

    def createEventAtPos(self, pos):
        if pos not in self.sceneRect():
            return
        try:
            time = pos.x() // (self.beatSnap * self.beatSize) * self.beatSnap
        except:
            time = pos.x() / self.beatSize
        time = min(time, self.pattern.length - self.beatSnap)
        value = sanitize(0, 127 - int(pos.y()), 127)
        event = self.currentRegion.addEvent(
#            ctrl=self.currentRegion.id, 
            value=value, 
#            channel=self.pattern.track.channel, 
            time=time)
        autoItem = AutoItem(event, self)
        automationPoints = self.automationPoints[self.currentRegion]
        automationPoints.append(autoItem)
        automationPoints.sort(key=lambda i: i.x())
        self.addItem(autoItem)
        autoItem.setZValue(10)
#        self.playNote[int].emit(note)
        self.redrawLine(False)
        self.edited = True
        return autoItem

    def setBeatSnapMode(self, snapMode):
        for item in self.thirds:
            item.setVisible(snapMode.triplet)
        for item in self.eights:
            item.setVisible(snapMode.denominator in (8, 16))
        for item in self.sixteenths:
            item.setVisible(snapMode.denominator == 16)
        self.beatSnap = snapMode.length

    def moveEvents(self, scenePos):
        minTime = self.pattern.length
        maxTime = 0
        minValue = 127
        maxValue = 0
        for item in self.selectedItems():
            minTime = min(minTime, item.event.time)
            maxTime = max(maxTime, item.event.time)
            minValue = min(minValue, item.event.value)
            maxValue = max(maxValue, item.event.value)

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

        if minValue or maxValue < 127:
            #value coordinates are inverted!
            deltaValue = int(self.mousePos.y() - scenePos.y())
            if isinstance(self.currentRegion, BlofeldParameterRegion):
                if self.currentRegion.parameter.range.step > 1:
                    step = self.currentRegion.parameter.range.step
                    deltaValue = (deltaValue // step) * step
            if minValue + deltaValue < 0 or maxValue + deltaValue > 127:
                deltaValue = None
        else:
            deltaValue = None

        if self.moveModifiers == QtCore.Qt.ShiftModifier:
            pass
#            if not self.movingItems:
#                for item in self.selectedItems():
#                    rectItem = self.addRect(item.rect())
#                    rectItem.setPos(item.pos())
#                    rectItem.setPen(QtCore.Qt.red)
#                    rectItem.setZValue(50)
#                    self.movingItems[item] = rectItem
#            if deltaNote is not None and deltaTime is not None:
#                for noteItem, rectItem in self.movingItems.items():
#                    rectItem.setPos(noteItem.x() + deltaTime * self.beatSize, 
#                        noteItem.y() - deltaNote * self.noteHeight)
#            self._deltaNote = deltaNote if deltaNote is not None else 0
        else:
            self.currentRegion.moveEventsBy([item.event for item in self.selectedItems()], deltaValue=deltaValue, deltaTime=deltaTime)
            self.redrawLine(True)
            if deltaTime is not None:
                self.mousePos.setX(self.mousePos.x() + deltaTime * self.beatSize)
            if deltaValue is not None:
                self.mousePos.setY(self.mousePos.y() + -deltaValue)
            self.edited = True
        if deltaTime is not None:
            self.currentPoints.sort(key=lambda i: i.x())
        return deltaValue, deltaTime

    def erasePoints(self, items=None):
        if items is None:
            items = self.selectedItems()
        if not items:
            return
        events = []
        for item in items:
            events.append(item.event)
            self.removeItem(item)
            self.currentPoints.remove(item)
        self.edited = True
        self.currentRegion.removeEvents(events)
        self.redrawLine()

    def mousePressEvent(self, event):
        self.moveModifiers = event.modifiers()
        selected = self.selectedItems()
        if event.buttons() == QtCore.Qt.LeftButton:
            if self.mouseMode() == Erase:
                item = self.itemAt(event.scenePos())
                if isinstance(item, AutoItem):
                    if item not in selected:
                        self.clearSelection()
                        self.erasePoints([item])
                    else:
                        self.erasePoints(selected)
                    return
            elif self.mouseMode() == Draw:
                item = self.itemAt(event.scenePos())
                if not isinstance(item, AutoItem):
                    self.clearSelection()
                    self.currentItem = self.createEventAtPos(event.scenePos())
                    self.currentItem.setSelected(True)
                    self.mousePos = event.scenePos()
                    return
        QtWidgets.QGraphicsScene.mousePressEvent(self, event)
        if event.buttons() == QtCore.Qt.RightButton:
            underMouse = self.itemAt(event.scenePos())
            if isinstance(underMouse, AutoItem):
                if underMouse in selected or event.modifiers() == QtCore.Qt.ControlModifier:
#                    self.selectionChanged.disconnect(self.checkSelection)
                    for item in set(selected + [underMouse]):
                        item.setSelected(True)
#                    self.selectionChanged.connect(self.checkSelection)
                else:
                    underMouse.setSelected(True)
        elif self.selectedItems():
            self.mousePos = event.scenePos()
            for item in self.items(self.mousePos):
                if isinstance(item, AutoItem):
                    self.currentItem = item
#                    self.playNote.emit(item.noteOnEvent.note, item.noteOnEvent.velocity)
                    break
            else:
                self.currentItem = self.selectedItems()[0]

    def mouseDoubleClickEvent(self, event):
        if not self.selectedItems() and not self.mouseMode() == Erase:
            self.mousePos = event.scenePos()
            self.currentItem = self.createEventAtPos(self.mousePos)
            self.currentItem.setSelected(True)

    def mouseMoveEvent(self, event):
        if event.buttons() == QtCore.Qt.LeftButton and self.currentItem:
            self.moveEvents(event.scenePos())
            pass
        QtWidgets.QGraphicsScene.mouseMoveEvent(self, event)

    def mouseReleaseEvent(self, event):
        self.mousePos = self.currentItem = self.moveModifiers = None
        QtWidgets.QGraphicsScene.mouseReleaseEvent(self, event)


class NoteEditorAutomationView(QtWidgets.QGraphicsView):
    addAutomationRequested = QtCore.pyqtSignal()

    def __init__(self):
        QtWidgets.QGraphicsView.__init__(self)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setRenderHints(QtGui.QPainter.Antialiasing)

    def mousePressEvent(self, event):
        if not self.isInteractive() and event.buttons() == QtCore.Qt.LeftButton:
            self.addAutomationRequested.emit()
        else:
            QtWidgets.QGraphicsView.mousePressEvent(self, event)

    def contextMenuEvent(self, event):
        menu = QtWidgets.QMenu()
        addAutoAction = menu.addAction(QtGui.QIcon.fromTheme('list-add'), 'Add automation...')
        addAutoAction.triggered.connect(self.addAutomationRequested)
        menu.addSeparator()

        automationGroup = QtWidgets.QActionGroup(self)

        discreteAction = menu.addAction(QtGui.QIcon.fromTheme('labplot-xy-smoothing-curve'), 'Discrete')
        automationGroup.addAction(discreteAction)
        discreteAction.setCheckable(True)
        discreteAction.setChecked(True)

        continuousAction = menu.addAction(QtGui.QIcon.fromTheme('labplot-xy-interpolation-curve'), 'Continuous')
        automationGroup.addAction(continuousAction)
        continuousAction.setCheckable(True)

        if not self.isInteractive():
            discreteAction.setEnabled(False)
            continuousAction.setEnabled(False)
        else:
            currentRegion = self.scene().currentRegion
            discreteAction.triggered.connect(lambda: currentRegion.setContinuous(False))
            continuousAction.triggered.connect(lambda: currentRegion.setContinuous(True))
            if currentRegion.continuous:
                continuousAction.setChecked(True)
        menu.exec_(QtGui.QCursor.pos())

    def resizeEvent(self, event):
        QtWidgets.QGraphicsView.resizeEvent(self, event)
        if self.scene():
            self.setTransform(QtGui.QTransform().scale(self.transform().m11(), self.viewport().rect().height() / 127.))


class NoteEditorAutomationWidget(QtWidgets.QWidget):
    shown = False

    def __init__(self, parent):
        QtWidgets.QWidget.__init__(self, parent)
        layout = QtWidgets.QGridLayout()
        self.setLayout(layout)
        self.setContentsMargins(0, 0, 0, 0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.handle = NoteEditorAutomationHandle(self)
        layout.addWidget(self.handle, 0, 0, 1, 2)
        self.handle.setFixedHeight(8)

        self.automationLabel = NoteEditorAutomationLabel()
        layout.addWidget(self.automationLabel, 1, 0)
        self.automationLabel.installEventFilter(self)

        self.automationView = NoteEditorAutomationView()
        layout.addWidget(self.automationView, 1, 1, 2, 1)
        self.automationView.setMinimumHeight(1)
        self.automationView.setInteractive(False)
        self.automationView.addAutomationRequested.connect(self.addAutomation)

        self.hoverWidget = NoteEditorAutomationHover(self)
        self.hoverWidget.addAutomationRequested.connect(self.addAutomation)
        self.automationCombo = self.hoverWidget.automationCombo
        self.automationCombo.currentIndexChanged.connect(self.setAutomation)

    def setPattern(self, pattern):
        self.pattern = pattern
        self.track = pattern.track

        self.automationScene = AutomationScene(self.automationView, pattern)
        self.automationView.setScene(self.automationScene)

        index = 0
        self.automationCombo.blockSignals(True)
        for automation in self.track.automations():
            if automation.parameterType == BlofeldParameter:
                parameter = Parameters.parameterData[automation.parameterId >> 4 & 511]
                if parameter.children:
                    parameter = parameter[automation.parameterId & 7]
                label = parameter.fullName
                part = automation.parameterId >> 15
                if part:
                    label += ' (part {})'.format(part + 1)
                self.automationCombo.addItem(parameter.fullName)
                self.automationCombo.setItemData(index, automation, ParameterRole)
                index += 1
            elif automation.parameterType == CtrlParameter:
                self.automationCombo.addItem(getCtrlNameFromMapping(automation.parameterId)[0])
                self.automationCombo.setItemData(index, automation, ParameterRole)
                index += 1
        self.automationCombo.blockSignals(False)
        if self.automationCombo.count():
            self.setAutomation(0)

    def setAutomation(self, index):
        self.automationCombo.setEnabled(True)
        self.automationView.setInteractive(True)
        automationInfo = self.automationCombo.itemData(index, ParameterRole)
        self.automationLabel.setAutomation(self.automationCombo.currentText(), automationInfo)
        self.automationScene.setAutomation(automationInfo)

    def addAutomation(self):
        dialog = AddAutomationDialog(self, [r.regionInfo for r in self.pattern.regions[1:]])
        if not dialog.exec_():
            return
        #TODO: let's uniform automationData variable names to automationInfo...
        #automation is manually added to the temporary pattern, NOT to the track!
        #maybe we'll change this in the future...
        newAutomationInfo = self.pattern.addAutomation(dialog.automationInfo()).regionInfo

        #rebuild automationCombo model
        automationInfoSet = set([newAutomationInfo])
        for index in range(self.automationCombo.count()):
            automationInfoSet.add(self.automationCombo.itemData(index, ParameterRole))

        newIndex = self.automationCombo.currentIndex()
        index = 0
        self.automationCombo.blockSignals(True)
        self.automationCombo.clear()
        for automationInfo in sorted(automationInfoSet):
            if automationInfo.parameterType == BlofeldParameter:
                parameter = Parameters.parameterData[automationInfo.parameterId >> 4 & 511]
                if parameter.children:
                    parameter = parameter.children[automationInfo.parameterId & 7]
                self.automationCombo.addItem(parameter.fullName)
                self.automationCombo.setItemData(index, automationInfo, ParameterRole)
                if automationInfo == newAutomationInfo:
                    newIndex = index
                index += 1
            elif automationInfo.parameterType == CtrlParameter:
                self.automationCombo.addItem(getCtrlNameFromMapping(automationInfo.parameterId)[0])
                self.automationCombo.setItemData(index, automationInfo, ParameterRole)
                if automationInfo == newAutomationInfo:
                    newIndex = index
                index += 1
        self.automationCombo.setCurrentIndex(newIndex)
        self.automationCombo.blockSignals(False)
        self.setAutomation(newIndex)

    def eventFilter(self, source, event):
        if event.type() == QtCore.QEvent.Enter:
            self.hoverWidget.move(self.automationLabel.pos())
            self.hoverWidget.setVisible(True)
        return QtWidgets.QWidget.eventFilter(self, source, event)

    def showEvent(self, event):
        if not self.shown:
            self.shown = True
            self.baseHeight = self.hoverWidget.height() + self.handle.height() + self.layout().spacing()
            self.setMinimumHeight(self.baseHeight)
            self.setMaximumHeight(self.baseHeight)
            self.automationLabel.setFixedHeight(self.hoverWidget.height())
        self.hoverWidget.hide()

    def resizeEvent(self, event):
        self.handle.move(0, 1)
        self.handle.setFixedWidth(self.width())


class TimelineWidget(QtWidgets.QWidget):
    playheadMoveRequested = QtCore.pyqtSignal(float)

    def __init__(self, parent):
        QtWidgets.QWidget.__init__(self, parent)
        self.setFixedHeight(self.fontMetrics().height() + 2)
#        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.zoomFactor = 1
        self.playheadPos = 0
        self.offset = 0
        self.setMinimumWidth(4000)
        self.beatSize = self.parent().piano.width()

    def setOffset(self, offset):
        self.offset = offset + self.beatSize -self.pattern.time * self.beatSize * self.zoomFactor
        self.move(self.offset, 0)

    def setPattern(self, pattern):
        self.pattern = pattern
        self.start = pattern.time
        self.structure = pattern.track.structure
        self.playheadPos = self.pattern.time * self.beatSize * self.zoomFactor

    def setPlayheadPos(self, pos):
        self.playheadPos = pos
        self.update()

    def mouseMoveEvent(self, event):
        self.playheadMoveRequested.emit(sanitize(
            self.pattern.time, 
            float(event.x()) / self.beatSize / self.zoomFactor, 
            self.pattern.time + self.pattern.length
            ))

    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        qp.translate(.5, .5)
#        qp.fillRect(self.rect(), QtCore.Qt.lightGray)
        meters = iter(self.structure.meters)

        currentMeter = meters.next()
        try:
            nextMeter = meters.next()
        except:
            nextMeter = None

        rect = event.rect()

        barBgdColor = self.palette().color(QtGui.QPalette.Window).lighter(150)
        x = 0
        align = QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter
        bar = 1
        beats = 0
        height = self.height()
        unit = self.beatSize * self.zoomFactor
        currentBarPixels = unit * currentMeter.beats
        currentBeatPixels = unit / currentMeter.denominator * 4
        if currentBarPixels < qp.fontMetrics().width('88'):
            barTextDivisor = 4
        else:
            barTextDivisor = 1
        barData = []
        while x < rect.right():
            if nextMeter:
                if beats + currentMeter.beats > nextMeter.time:
#                    print(bar, currentMeter.beats, bar * currentMeter.beats, nextMeter.time)
                    currentMeter = nextMeter
                    currentBarPixels = unit * currentMeter.beats
                    currentBeatPixels = unit / currentMeter.denominator * 4
                    try:
                        nextMeter = meters.next()
                    except:
                        nextMeter = None
            if x < rect.left() - currentBarPixels:
                x += currentBarPixels
                beats += currentMeter.beats
                bar += 1
                continue
            textX = x + 2
            qp.save()
            qp.setPen(QtCore.Qt.darkGray)
            qp.drawLine(x, 0, x, height)
            qp.restore()

            if currentBeatPixels > 4:
                beatPixels = currentBeatPixels
                qp.save()
                qp.setPen(QtCore.Qt.lightGray)
                while beatPixels < currentBarPixels:
                    qp.drawLine(x + beatPixels, 0, x + beatPixels, height)
                    beatPixels += currentBeatPixels
                qp.restore()

            if not (bar - 1) % barTextDivisor:
                barData.append((QtCore.QRect(x + 1, 0, qp.fontMetrics().width(str(bar)) + 1, height), QtCore.QRect(textX, 2, 50, height - 2), str(bar)))

            beats += currentMeter.beats
            bar += 1
            x += currentBarPixels

        for barBgd, barRect, barText in barData:
            qp.fillRect(barBgd, barBgdColor)
            qp.drawText(barRect, align, barText)
        qp.setPen(PlayheadPen)
        qp.drawLine(self.playheadPos, 0, self.playheadPos, height)


class NoteRegionView(QtWidgets.QGraphicsView):
    horizontalZoomChanged = QtCore.pyqtSignal(float)
    verticalZoomChanged = QtCore.pyqtSignal(float)
    hasLeft = QtCore.pyqtSignal()
    shown = False

    def __init__(self, *args, **kwargs):
        QtWidgets.QGraphicsView.__init__(self, *args, **kwargs)
        self.piano = VerticalPiano(self)
        self.piano.installEventFilter(self)

        self.automationWidget = NoteEditorAutomationWidget(self)
        self.automationWidget.handle.installEventFilter(self)

        self.timelineWidget = TimelineWidget(self)
        self.playheadMoveRequested = self.timelineWidget.playheadMoveRequested
        self.timelineHeight = self.timelineWidget.height()

#        self.addScrollBarWidget(ScrollBarSpacer(self, QtCore.Qt.Horizontal, self.piano.width()), QtCore.Qt.AlignLeft)
        self.verticalScrollBarSpacer = ScrollBarSpacer(self, QtCore.Qt.Vertical, self.automationWidget.height())
        self.addScrollBarWidget(self.verticalScrollBarSpacer, QtCore.Qt.AlignBottom)

        self.horizontalZoomWidget = ZoomWidget(self, QtCore.Qt.Horizontal, minimum=.0625)
        self.horizontalZoomWidget.zoomChanged.connect(self.setHorizontalZoom)
        self.horizontalZoomChanged.connect(self.horizontalZoomWidget.setZoom)
        self.addScrollBarWidget(self.horizontalZoomWidget, QtCore.Qt.AlignRight)

        self.verticalZoomWidget = ZoomWidget(self, QtCore.Qt.Vertical, minimum=.25, maximum=2.)
        self.verticalZoomWidget.zoomChanged.connect(self.setVerticalZoom)
        self.verticalZoomChanged.connect(self.verticalZoomWidget.setZoom)
        self.addScrollBarWidget(self.verticalZoomWidget, QtCore.Qt.AlignBottom)

        self.setViewportMargins(self.piano.width(), self.timelineHeight, 0, self.automationWidget.height())

        self.horizontalScrollBar().valueChanged.connect(self.updateTimelinePosition)
        self.verticalScrollBar().valueChanged.connect(self.updatePianoPosition)

        self.scrollMargin = 16
        self._centerTarget = QtCore.QPointF()
        self.centerAnimation = QtCore.QPropertyAnimation(self, b'centerTarget')
        self.centerAnimation.setDuration(250)
        self.centerAnimation.setEasingCurve(QtCore.QEasingCurve(QtCore.QEasingCurve.InOutQuad))

    def setBeatSnapMode(self, *args):
        self.scene().setBeatSnapMode(*args)
        self.automationScene.setBeatSnapMode(*args)

    def setPattern(self, pattern):
        self.pattern = pattern
        self.automationWidget.setPattern(pattern)
        self.automationView = self.automationWidget.automationView
        self.horizontalScrollBar().valueChanged.connect(self.automationView.horizontalScrollBar().setValue)
        self.automationScene = self.automationView.scene()
        self.timelineWidget.setPattern(pattern)

    def setHorizontalZoom(self, delta):
        factor = self.transform().m11()
        if delta > 0:
            factor *= 2
        else:
            factor *= .5
        factor = sanitize(.125, factor, 8)
        if factor != self.transform().m11():
            self.setTransform(QtGui.QTransform().scale(factor, self.transform().m22()))
            self.horizontalZoomChanged.emit(factor)
            self.automationView.setTransform(QtGui.QTransform().scale(factor, self.automationView.transform().m22()))
            self.automationView.horizontalScrollBar().setValue(self.horizontalScrollBar().value())
            self.timelineWidget.zoomFactor = factor
            self.updateTimelinePosition()
#            self.timelineWidget.updateZoom(factor, self.mapFromScene(QtCore.QPoint(0, 0)).x())

    def setVerticalZoom(self, delta):
        factor = self.transform().m22()
        if delta > 0:
            factor *= 2
        else:
            factor *= .5
        factor = sanitize(.25, factor, 2)
        if factor != self.transform().m22():
            self.setTransform(QtGui.QTransform().scale(self.transform().m11(), factor))
            self.verticalZoomChanged.emit(factor)
            self.piano.setNoteHeight(factor)
            self.updatePianoPosition()

    @QtCore.pyqtProperty(QtCore.QPointF)
    def centerTarget(self):
        return self._centerTarget

    @centerTarget.setter
    def centerTarget(self, target):
        self._centerTarget = target
        self.centerOn(target)
        self.viewport().update()

#    def setMouseMode(self, mode):
#        if mode == Draw:
#            self.setDragMode(self.NoDrag)
#        else:
#            self.setDragMode(self.RubberBandDrag)

    def updateTimelinePosition(self):
        x = self.mapFromScene(QtCore.QPoint(0, 0)).x()
        self.timelineWidget.setOffset(x)
        mask = QtGui.QBitmap(self.timelineWidget.width(), self.timelineHeight)
        mask.clear()
        qp = QtGui.QPainter(mask)
        qp.setBrush(QtCore.Qt.black)
        qp.drawRect(-self.timelineWidget.x() + self.piano.width(), 0, self.viewport().width(), self.timelineHeight)
        qp.end()
        self.timelineWidget.setMask(mask)

    def updatePianoPosition(self):
        y = self.mapFromScene(QtCore.QPoint(0, 0)).y()
        self.piano.move(0, y + self.timelineHeight)
        height = self.viewport().height()
        mask = QtGui.QBitmap(self.piano.width(), max(self.piano.height(), height))
        mask.clear()
        qp = QtGui.QPainter(mask)
        qp.setBrush(QtCore.Qt.black)
        qp.drawRect(0, -y, self.piano.width(), height - 1)
        qp.end()
        self.piano.setMask(mask)

    def focusNotes(self, selected=False):
        if selected:
            items = self.scene().selectedItems()
        else:
            items = self.scene().noteItems()
        rect = QtCore.QRectF()
        for noteItem in items:
            rect |= noteItem.sceneBoundingRect()
        if rect.isNull():
            rect = QtCore.QRectF(self.sceneRect().center(), QtCore.QSizeF(1, 1))
        current = self.mapToScene(self.viewport().rect()).boundingRect()
        if not current.contains(rect):
            self.centerAnimation.setEndValue(rect.center())
            if self.centerAnimation.state() != self.centerAnimation.Running:
                self.centerAnimation.setStartValue(current.center())
                self.centerAnimation.start()

    def keyPressEvent(self, event):
        if event.key() in (QtCore.Qt.Key_Delete, QtCore.Qt.Key_Backspace):
            if self.viewport().hasFocus():
                self.scene().eraseNotes()
            elif self.automationView.hasFocus():
                self.automationScene.erasePoints()
        QtWidgets.QGraphicsView.keyPressEvent(self, event)

    def mouseMoveEvent(self, event):
        if event.buttons() == QtCore.Qt.LeftButton:
            rect = self.viewport().rect()
            if event.x() > rect.right() - self.scrollMargin:
                self.horizontalScrollBar().setValue(
                    self.horizontalScrollBar().value() + event.x() - rect.right() + self.scrollMargin)
            elif event.x() < self.scrollMargin:
                self.horizontalScrollBar().setValue(
                    self.horizontalScrollBar().value() + event.x() - rect.left() - self.scrollMargin)
            if event.y() > rect.bottom() - self.scrollMargin:
                self.verticalScrollBar().setValue(
                    self.verticalScrollBar().value() + event.y() - rect.bottom() + self.scrollMargin)
            elif event.y() < self.scrollMargin:
                self.verticalScrollBar().setValue(
                    self.verticalScrollBar().value() + event.y() - rect.top() - self.scrollMargin)
        QtWidgets.QGraphicsView.mouseMoveEvent(self, event)

    def leaveEvent(self, event):
        self.piano.noteHighlight()
        QtWidgets.QGraphicsView.leaveEvent(self, event)

    def setAutomationHeight(self, height):
        height = sanitize(self.automationWidget.baseHeight, height, 250)
        self.automationWidget.setFixedHeight(height)
        self.setViewportMargins(self.piano.width(), self.timelineHeight, 0, height)

    def handleResizeDelta(self, pos):
        delta = (pos - self.mousePos).y()
        if (delta < 0 and self.automationWidget.height() < 250) or \
            delta > 0 and self.automationWidget.height() > self.automationWidget.baseHeight:
                self.setAutomationHeight(self.automationWidget.height() - delta)
                self.mousePos = pos

    def eventFilter(self, source, event):
        if source == self.piano:
            if event.type() == QtCore.QEvent.Wheel:
                self.wheelEvent(event)
        else:
            if event.type() == QtCore.QEvent.MouseButtonPress and event.buttons() == QtCore.Qt.LeftButton:
                self.mousePos = source.mapTo(self, event.pos())
            elif event.type() == QtCore.QEvent.MouseMove and event.buttons() == QtCore.Qt.LeftButton:
                self.handleResizeDelta(source.mapTo(self, event.pos()))
            elif event.type() == QtCore.QEvent.MouseButtonRelease:
                self.mousePos = None
        return QtWidgets.QGraphicsView.eventFilter(self, source, event)

    def resizeEvent(self, event):
        QtWidgets.QGraphicsView.resizeEvent(self, event)
        self.updatePianoPosition()
        self.updateTimelinePosition()
        self.setViewportMargins(self.piano.width(), self.timelineHeight, 0, self.automationWidget.height())
        self.automationWidget.move(0, self.viewport().geometry().bottom())
        self.automationWidget.setFixedWidth(self.width())
        self.automationWidget.automationLabel.setFixedWidth(self.piano.width())
        self.verticalScrollBarSpacer.setFixedHeight(self.automationWidget.height())

    def showEvent(self, event):
        QtWidgets.QGraphicsView.showEvent(self, event)
        if not self.shown:
            self.shown = True
            self.focusNotes()
            self.setViewportMargins(self.piano.width(), self.timelineHeight, 0, self.automationWidget.height())
            self.verticalScrollBarSpacer.setFixedHeight(self.automationWidget.height())
            self.automationWidget.setContentsMargins(0, 0, self.verticalScrollBar().width(), 0)


class NoteRegionEditor(QtWidgets.QDialog):
    def __init__(self, parent, pattern):
        QtWidgets.QDialog.__init__(self, parent)
        loadUi('ui/noteregioneditor.ui', self)
        self.midiEvent = parent.midiEvent
        self.player = parent.player
        self.pattern = pattern.clone()
#        print('Orig {} copy {}'.format(pattern, self.pattern))
#        self.baseHeight = self.fontMetrics().height()
        self.timelineWidget = self.noteView.timelineWidget
        self.noteScene = NoteRegionScene(self.noteView, self.pattern)
        self.noteView.setScene(self.noteScene)
        self.noteView.setPattern(self.pattern)
        self.automationView = self.noteView.automationWidget.automationView
        self.automationScene = self.automationView.scene()

        self.playheadStartPos = -pattern.time * self.noteScene.beatSize
        self.noteScene.noteHighlight.connect(self.noteView.piano.noteHighlight)
        self.noteView.piano.playNote.connect(self.playNote)
        self.noteView.piano.stopNote.connect(self.stopNote)
        self.noteScene.playNote.connect(self.playNote)
        self.noteScene.playNote[int].connect(self.playNote)
        self.noteScene.stopNote.connect(self.stopNote)

        for index, snapMode in enumerate(SnapModes):
            self.snapCombo.addItem(snapMode.icon, snapMode.label)
            self.snapCombo.setItemData(index, snapMode, SnapModeRole)
            self.defaultLengthCombo.addItem(snapMode.icon, snapMode.label)
            self.defaultLengthCombo.setItemData(index, snapMode, SnapModeRole)
        #TODO: set snapmode according to pattern.length?
#        self.snapCombo.setCurrentIndex(DefaultNoteSnapModeId)
        self.snapCombo.currentIndexChanged.connect(self.setBeatSnap)
        self.snapCombo.currentIndexChanged.connect(self.checkSnapLengthLink)
        self.saveCloseBtn.clicked.connect(self.accept)

#        self.defaultLengthCombo.setCurrentIndex(DefaultNoteSnapModeId)
        self.defaultLengthCombo.currentIndexChanged.connect(self.checkSnapLengthLink)
        self.defaultVelocityCombo.setRange(0, 127)
        self.defaultVelocityCombo.setValue(100)

        self.mouseModeGroup.setId(self.drawBtn, Draw)
        self.mouseModeGroup.setId(self.selectBtn, Select)
        self.mouseModeGroup.setId(self.eraseBtn, Erase)
        self.mouseModeGroup.buttonClicked[int].connect(self.setMouseMode)

        self.settings = QtCore.QSettings()
        self.settings.beginGroup('Sequencer')
        if self.settings.contains('NoteEditorGeometry'):
            self.restoreGeometry(self.settings.value('NoteEditorGeometry'))
        self.lockSnapLengthBtn.setChecked(self.settings.value('LockSnapLength', True, type=bool))
        self.snapCombo.setCurrentIndex(self.settings.value('NoteSnapMode', DefaultNoteSnapModeId, type=int))
        self.defaultLengthCombo.setCurrentIndex(self.settings.value('NoteLength', DefaultNoteSnapModeId, type=int))
        self.mouseModeGroup.button(self.settings.value('NoteEditorMouseMode', Draw, type=int)).click()
        self.autoChordBtn.setChecked(self.settings.value('AutoChordState', False, type=bool))
        if self.settings.value('AutoChordIntervals'):
            self.autoChordWidget.setIntervals(self.settings.value('AutoChordIntervals'))
        self.settings.endGroup()

        self.chordMenu = QtWidgets.QMenu(self)
        self.chordMenu.setSeparatorsCollapsible(False)
        for intervals, chordName in Chords:
            if not intervals:
                self.chordMenu.addSection(chordName)
                continue
            action = self.chordMenu.addAction(chordName)
            action.setData(intervals)
        self.autoChordBtn.setMenu(self.chordMenu)
        self.autoChordBtn.triggered.connect(self.setAutoChord)
        self.noteScene.autoChordWidget = self.autoChordWidget

        self.rewindBtn.clicked.connect(self.rewind)
        self.playBtn.toggled.connect(self.togglePlay)
        self.player.statusChanged.connect(self.togglePlay)
        self.loopBtn.toggled.connect(self.setLoop)
        self.stopBtn.clicked.connect(self.parent().stop)

        option = QtWidgets.QStyleOption()
        option.initFrom(self)
        toolBarSpacing = self.style().pixelMetric(QtWidgets.QStyle.PM_ToolBarItemSpacing, option, self)
        self.mainToolBarLayout.setSpacing(toolBarSpacing)
        self.inputToolBarLayout.setSpacing(toolBarSpacing)
        sepSize = self.style().pixelMetric(QtWidgets.QStyle.PM_ToolBarSeparatorExtent, option, self)
        for layout in (self.mainToolBarLayout, self.inputToolBarLayout):
            for index in range(layout.count()):
                item = layout.itemAt(index)
                try:
                    widget = item.widget()
                    if type(widget) == QtWidgets.QFrame and widget.minimumWidth() < sepSize:
                        widget.setMinimumWidth(sepSize)
                except:
                    pass

#        self.copyAction = QtWidgets.QAction(QtGui.QIcon.fromTheme('edit-copy'), 'Copy', self)
#        self.copyAction.setShortcut(QtGui.QKeySequence(QtGui.QKeySequence.Copy))
#        self.copyAction.setShortcutContext(QtCore.Qt.WindowShortcut)
#        self.copyAction.triggered.connect(self.stopcazz)

        self.noteView.playheadMoveRequested.connect(self.playheadMoveRequested)
        self.parent().playheadTimeChanged.connect(self.setPlayheadPos)
        self.parent().playheadTime = pattern.time
        self.playIcons = QtGui.QIcon.fromTheme('media-playback-start'), QtGui.QIcon.fromTheme('media-playback-pause')
        self.noteView.setFocus()

    def stopcazz(self):
        print('staocazzoooooooooooo')

    def playheadMoveRequested(self, time):
        self.parent().playheadTime = time

    def setPlayheadPos(self, pos):
        pos *= self.noteScene.beatSize
        self.timelineWidget.setPlayheadPos(pos)
        self.noteScene.playhead.setX(pos + self.playheadStartPos)

    def setLoop(self, loop):
        if loop:
            if self.player.status == self.player.Playing:
                self.loopBtn.blockSignals(True)
                self.player.stop()
                self.loopBtn.setChecked(True)
                self.loopBtn.blockSignals(False)
                return QtCore.QTimer.singleShot(0, lambda: self.loopBtn.setChecked(True))
            self.parent().playheadTime = self.pattern.time
            self.player.playFrom(self.pattern.time, self.pattern.time + self.pattern.length, loop=loop, pattern=self.pattern)
        else:
            self.player.stop()
            self.togglePlay(True)

    def togglePlay(self, state=None):
        if state is None:
            return self.playBtn.setChecked(not self.playBtn.isChecked())
        if state:
            start = self.parent().playheadTime
            if start >= self.pattern.time + self.pattern.length - .125:
                start = self.pattern.time
#            self.player.playFrom(self.pattern.time, self.pattern.time + self.pattern.length, pattern=self.pattern)
            self.parent().togglePlay(True, start, self.pattern.time + self.pattern.length, pattern=self.pattern)
        else:
            self.parent().togglePlay(False)
            QtCore.QTimer.singleShot(0, self.checkLoop)
        self.playBtn.blockSignals(True)
        self.playBtn.setChecked(state)
        self.playBtn.blockSignals(False)
        self.playBtn.setIcon(self.playIcons[bool(state)])

    def checkLoop(self):
        if self.player.status != self.player.Playing:
            self.loopBtn.blockSignals(True)
            self.loopBtn.setChecked(False)
            self.loopBtn.blockSignals(False)

    def rewind(self):
        restart = self.player.status == self.player.Playing
        self.player.stop()
        self.parent().setPlayheadTime(self.pattern.time)
        if restart:
            QtCore.QTimer.singleShot(0, self.togglePlay)

    def setAutoChord(self, action):
        self.autoChordBtn.setChecked(True)
        self.autoChordWidget.setEnabled(True)
        self.autoChordWidget.setChord(action.data())

    def playNote(self, note, velocity=None):
#        print('playo', note)
        self.midiEvent.emit(MidiEvent(NOTEON, 1, self.pattern.track.channel, data1=note, 
            data2=velocity if velocity is not None else self.defaultVelocityCombo.value()))
        if self.sender() == self.noteScene:
            QtCore.QTimer.singleShot(500, lambda: self.stopNote(note))

    def stopNote(self, note):
        self.midiEvent.emit(MidiEvent(NOTEOFF, 1, self.pattern.track.channel, data1=note, data2=self.defaultVelocityCombo.value()))

    def mouseMode(self):
        return self.mouseModeGroup.checkedId()

    def setMouseMode(self, mode):
        mode = QtWidgets.QGraphicsView.NoDrag if mode == Draw else QtWidgets.QGraphicsView.RubberBandDrag
        self.noteView.setDragMode(mode)
        self.automationView.setDragMode(mode)

    def checkSnapLengthLink(self, index):
        if self.lockSnapLengthBtn.isChecked():
            self.snapCombo.setCurrentIndex(index)
            self.defaultLengthCombo.setCurrentIndex(index)

    def setBeatSnap(self, index):
        self.noteView.setBeatSnapMode(self.snapCombo.itemData(index, SnapModeRole))

    def keyPressEvent(self, event):
        if event.key() in (QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return):
            return
        elif event.key() == QtCore.Qt.Key_Shift and self.mouseMode() != Select:
            self.setMouseMode(Select)
            self.selectBtn.setDown(True)
        elif event.key() == QtCore.Qt.Key_Space:
            self.togglePlay()
        elif event.key() == QtCore.Qt.Key_Home:
            self.rewindBtn.click()
        elif event.key() == QtCore.Qt.Key_Period:
            self.stopBtn.click()
        elif event.key() == QtCore.Qt.Key_L:
            self.loopBtn.toggle()
        elif event.key() == QtCore.Qt.Key_F1:
            self.mouseModeGroup.button(Draw).setChecked(True)
        elif event.key() == QtCore.Qt.Key_F2:
            self.mouseModeGroup.button(Select).setChecked(True)
        elif event.key() == QtCore.Qt.Key_F3:
            self.mouseModeGroup.button(Erase).setChecked(True)
        elif event.key() == QtCore.Qt.Key_A and event.modifiers() == QtCore.Qt.ShiftModifier | QtCore.Qt.ControlModifier:
            self.autoChordBtn.toggle()
        QtWidgets.QDialog.keyPressEvent(self, event)

    def keyReleaseEvent(self, event):
        if event.key() == QtCore.Qt.Key_Shift:
            if self.mouseMode() != Select:
                self.setMouseMode(self.mouseMode())
                self.selectBtn.setDown(False)
        QtWidgets.QDialog.keyReleaseEvent(self, event)

    def reject(self):
        if self.noteScene.isClean() and self.automationScene.isClean():
           return QtWidgets.QDialog.reject(self)
        res = AdvancedMessageBox(self, 'Pattern modified', 'The pattern has been modified.<br/>If you don\'t save it, all changes will be lost', 
            icon=AdvancedMessageBox.Question, 
            buttons={AdvancedMessageBox.Save: 'Save and close', 
                AdvancedMessageBox.Ignore: None, 
                AdvancedMessageBox.Cancel: None}).exec_()
        if res == AdvancedMessageBox.Cancel:
            return
        elif res == AdvancedMessageBox.Ignore:
            QtWidgets.QDialog.reject(self)
        else:
            self.accept()

    def showEvent(self, event):
        if not event.spontaneous():
            self.settings.beginGroup('Sequencer')
            self.noteView.setAutomationHeight(self.settings.value(
                'NoteEditorAutomationHeight', self.noteView.automationWidget.baseHeight, type=int))
            self.settings.endGroup()

    def exec_(self):
        res = QtWidgets.QDialog.exec_(self)
        self.player.stop()
        self.settings.beginGroup('Sequencer')
        self.settings.setValue('NoteEditorGeometry', self.saveGeometry())
        self.settings.setValue('NoteSnapMode', self.snapCombo.currentIndex())
        self.settings.setValue('NoteLength', self.defaultLengthCombo.currentIndex())
        self.settings.setValue('LockSnapLength', self.lockSnapLengthBtn.isChecked())
        self.settings.setValue('NoteEditorMouseMode', self.mouseModeGroup.checkedId())
        self.settings.setValue('AutoChordState', self.autoChordBtn.isChecked())
        self.settings.setValue('AutoChordIntervals', self.autoChordWidget.intervals())
        self.settings.setValue('NoteEditorAutomationHeight', self.noteView.automationWidget.height())
        self.settings.endGroup()
        return res

