import os

os.environ['QT_PREFERRED_BINDING'] = 'PyQt4'

from Qt import QtCore, QtGui, QtWidgets

from bigglesworth.utils import sanitize
from bigglesworth.parameters import Parameters
from bigglesworth.sequencer.const import (Bar, Marker, Tempo, Meter, BeatHUnit, 
    PlayheadPen, EndMarkerPen, SnapModes, DefaultPatternSnapModeId, 
    CtrlParameter, BlofeldParameter, Mappings, getCtrlNameFromMapping)
from bigglesworth.sequencer.structure import Structure, MarkerEvent, EndMarker, LoopStartMarker, LoopEndMarker, TempoEvent, MeterEvent, RegionInfo, NoteOffEvent, NoteOnEvent
from bigglesworth.sequencer.graphics import SequencerScene, NotePatternItem, PatternRectItem, TrackContainer
from bigglesworth.sequencer.dialogs import TempoEditDialog, MeterEditDialog, AddAutomationDialog, AddTracksDialog, QuantizeDialog
from bigglesworth.sequencer.widgets import ComboSpin, ZoomWidget, ScrollBarSpacer
from bigglesworth.sequencer.noteeditor import NoteRegionEditor


class TimelineEventWidget(QtWidgets.QWidget):
    markerMoveRequested = QtCore.pyqtSignal(int)
    deleteRequested = QtCore.pyqtSignal()
    leftLabel = False

    def __init__(self, parent, event):
        QtWidgets.QWidget.__init__(self, parent)
        self.event = event
        self.timelineHeader = parent.timelineHeader
        self.mousePos = None
        self.setLabel()
        self.show()

    def setLabel(self):
        fm = self.fontMetrics()
        self.setFixedSize(fm.width(self.event.label) + fm.height() + 1, fm.height())
        self.reset()

    def reset(self):
        fm = self.fontMetrics()
        height = fm.height()
        midSize = height * .5
        self.offset = midSize * .5
        margin = self.offset * 3
        self.markerPoly = QtGui.QPolygonF([
            QtCore.QPointF(0, 0), 
            QtCore.QPointF(midSize, 0), 
            QtCore.QPointF(midSize, midSize), 
            QtCore.QPointF(midSize * .5, height - 1), 
            QtCore.QPointF(0, midSize), 
        ])
        if self.leftLabel:
            self.labelRect = self.rect().adjusted(0, 0, -margin, -1)
            self.markerPoly.translate(self.labelRect.right() + self.offset, 0)
            self.focusPoint = self.offset
        else:
            self.focusPoint = -self.offset
            self.labelRect = self.rect().adjusted(margin, 0, -1, -1)

    def setX(self, x):
        if self.leftLabel:
            self.move(x - self.width() + self.offset, self.timelineHeader.rulerPositions[self.event.eventType])
        else:
            self.move(x - self.offset, self.timelineHeader.rulerPositions[self.event.eventType])

    def changeEvent(self, event):
        if event.type() == QtCore.QEvent.FontChange:
            self.reset()

    def mousePressEvent(self, event):
        if event.buttons() == QtCore.Qt.LeftButton:
            self.mousePos = event.pos()
        elif event.buttons() == QtCore.Qt.RightButton and event.modifiers() == QtCore.Qt.ShiftModifier:
            self.deleteRequested.emit()
        self.raise_()

    def mouseMoveEvent(self, event):
        if self.mousePos is not None:
            self.markerMoveRequested.emit(event.x())

    def mouseReleaseEvent(self, event):
        self.mousePos = None

    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        qp.setRenderHints(qp.Antialiasing)
        qp.setBrush(self.brush)
        qp.translate(.5, .5)
        qp.drawPolygon(self.markerPoly)
        qp.setBrush(self.labelBgd)
        qp.drawRoundedRect(self.labelRect, 2, 2)
        qp.drawText(self.labelRect.adjusted(0, 1, 0, 0), QtCore.Qt.AlignCenter, self.event.label)


class MarkerWidget(TimelineEventWidget):
    brush = QtGui.QColor(255, 171, 0)
    labelBgd = QtGui.QColor(223, 202, 115, 156)
    editActionName = 'Rename...'
    deleteActionName = 'Delete marker'

    def __init__(self, parent, event):
        TimelineEventWidget.__init__(self, parent, event)
        event.labelChanged.connect(self.setLabel)

    def edit(self):
        newLabel, res = QtWidgets.QInputDialog.getText(self, 'Rename marker', 
            'Type the marker label (16 characters max):', text=self.event.label)
        if res:
            self.event.label = newLabel[:16].strip()

    def mouseDoubleClickEvent(self, event):
        if event.buttons() == QtCore.Qt.LeftButton:
            self.edit()

    def contextMenuEvent(self, event):
        if event.modifiers() == QtCore.Qt.ShiftModifier:
            return
        menu = QtWidgets.QMenu()
        renameAction = menu.addAction(QtGui.QIcon.fromTheme('document-edit'), self.editActionName)
        renameAction.triggered.connect(self.edit)
        deleteAction = menu.addAction(QtGui.QIcon.fromTheme('edit-delete'), self.deleteActionName)
        deleteAction.triggered.connect(self.deleteRequested)
        if self.event.first:
            deleteAction.setEnabled(False)
        menu.exec_(QtGui.QCursor.pos())


class LoopStartMarkerWidget(MarkerWidget):
    brush = QtGui.QColor(103, 68, 255)
    labelBgd = QtGui.QColor(146, 133, 255)
    loopToFullRequested = QtCore.pyqtSignal()

    def edit(self):
        pass

    def contextMenuEvent(self, event):
        menu = QtWidgets.QMenu()
        setToFullAction = menu.addAction(QtGui.QIcon.fromTheme('transform-move-horizontal'), 'Set to full song')
        setToFullAction.triggered.connect(self.loopToFullRequested)
        removeAction = menu.addAction(QtGui.QIcon.fromTheme('edit-delete'), 'Remove loop')
        removeAction.triggered.connect(self.deleteRequested)
        menu.exec_(event.globalPos())


class LoopEndMarkerWidget(LoopStartMarkerWidget):
    leftLabel = True


class TempoMarkerWidget(MarkerWidget):
    brush = QtGui.QColor(92, 122, 223)
    labelBgd = QtGui.QColor(152, 198, 238, 156)
    editActionName = 'Edit tempo...'
    deleteActionName = 'Delete tempo'

    def edit(self):
        res = TempoEditDialog(self, self.event).exec_()
        if res:
            self.event.setTempo(res)

    def wheelEvent(self, event):
        delta = 1 if event.delta() > 0 else -1
#        if event.modifiers() & QtCore.Qt.ShiftModifier:
#            delta *= 8
        self.event.setTempo(self.event._tempo + delta)
        self.update()


class MeterMarkerWidget(MarkerWidget):
    brush = QtGui.QColor(84, 223, 103)
    labelBgd = QtGui.QColor(136, 233, 160, 156)
    editActionName = 'Edit meter...'
    deleteActionName = 'Delete meter'

    def edit(self):
        res = MeterEditDialog(self, self.event).exec_()
        if res:
            self.event.setMeter(*res)


class EndMarkerWidget(TimelineEventWidget):
    brush = QtGui.QColor(255, 0, 0)
    labelBgd = QtGui.QColor(223, 202, 115, 156)
    leftLabel = True

    def __init__(self, parent, event):
        TimelineEventWidget.__init__(self, parent, event)
        self.referencePos = 0

    def _reset(self):
        fm = self.fontMetrics()
        height = fm.height()
        self.setFixedSize(fm.width(self.event.label) + height, height)
        midSize = height * .5
        self.offset = midSize * .5
        self.margin = self.offset * 3
        self.markerPoly = QtGui.QPolygonF([
            QtCore.QPointF(0, 0), 
            QtCore.QPointF(midSize, 0), 
            QtCore.QPointF(midSize, midSize), 
            QtCore.QPointF(midSize * .5, height - 1), 
            QtCore.QPointF(0, midSize), 
        ])

#    def setX(self, x):
#        self.referencePos = x
#        self.move(x - self.width() + self.offset, self.timelineHeader.rulerPositions[Marker])

    def changeEvent(self, event):
        if event.type() == QtCore.QEvent.FontChange:
            self.reset()

    def _paintEvent(self, event):
        qp = QtGui.QPainter(self)
        qp.setRenderHints(qp.Antialiasing)
        qp.translate(.5, .5)
        rect = self.rect().adjusted(0, 0, -self.margin, -1)
        qp.setBrush(self.labelBgd)
        qp.drawRoundedRect(rect, 2, 2)
        qp.drawText(rect.adjusted(0, 1, 0, 0), QtCore.Qt.AlignCenter, self.event.label)
        qp.setBrush(self.brush)
        qp.translate(rect.right() + self.offset, 0)
        qp.drawPolygon(self.markerPoly)


class LoopLine(QtWidgets.QWidget):
    def __init__(self, parent, loopStart, loopEnd):
        QtWidgets.QWidget.__init__(self, parent)
        self.pen = QtGui.QColor(103, 68, 255, 192)
        self.setFixedHeight(self.fontMetrics().height())
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        self.loopStart = loopStart
        self.loopStart.installEventFilter(self)
        self.loopEnd = loopEnd
        self.loopEnd.installEventFilter(self)
        self.loopEnd.destroyed.connect(self.deleteLater)
        self.show()

    def updatePosition(self):
        self.move(self.loopStart.pos() + QtCore.QPoint(self.loopStart.offset, 0))
        self.setFixedWidth(self.loopEnd.geometry().right() - self.x())

    def eventFilter(self, source, event):
        if event.type() == QtCore.QEvent.Move:
            self.updatePosition()
        return QtWidgets.QWidget.eventFilter(self, source, event)

    def showEvent(self, event):
        if not event.spontaneous():
            self.updatePosition()
            self.lower()

    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        y = self.rect().center().y()
        qp.setPen(self.pen)
        qp.drawLine(0, y, self.width(), y)


class TimelineWidget(QtWidgets.QWidget):
    addTimelineEventRequested = QtCore.pyqtSignal(int, int)
    addLoopRequested = QtCore.pyqtSignal(int)
    loopToFullRequested = QtCore.pyqtSignal()
    moveMarker = QtCore.pyqtSignal(object, int)
    deleteMarker = QtCore.pyqtSignal(object)
    dragMovement = QtCore.pyqtSignal()
    dragPlayhead = QtCore.pyqtSignal()
    markerTypeDict = {
        MarkerEvent: MarkerWidget,
        EndMarker: EndMarkerWidget, 
        TempoEvent: TempoMarkerWidget, 
        MeterEvent: MeterMarkerWidget, 
        LoopStartMarker: LoopStartMarkerWidget, 
        LoopEndMarker: LoopEndMarkerWidget, 
    }

    def __init__(self, parent, timelineHeader, structure):
        QtWidgets.QWidget.__init__(self, parent)
        self.timelineHeader = timelineHeader
        self.structure = structure
        structure.timelineChanged.connect(self.checkMarkers)
        structure.timelineChanged.connect(self.update)
        structure.changed.connect(self.checkMarkers)
        self.markers = {}
        self.endMarker = None
        self.loopStart = self.loopEnd = self.loopLine = None
        self.zoomFactor = 1
        self.checkMarkers()
#        self.structure.changed.connect(self.rebuildTimeline)
        self.setMinimumWidth(4000)
        self.view = parent
        self.playheadPos = 0
        self.mousePos = None
        self.shown = False
        self.longPressTimer = QtCore.QTimer()
        self.longPressTimer.setSingleShot(True)
        self.longPressTimer.setInterval(200)
        self.longPressTimer.timeout.connect(self.dragPlayhead)

    def zoomChanged(self, factor):
        if factor != self.zoomFactor:
            self.playheadPos = self.playheadPos / self.zoomFactor * factor
            self.zoomFactor = factor
            self.checkMarkers()
            self.update()

    def setPlayheadPos(self, x):
        if self.playheadPos != x:
            self.playheadPos = x * self.zoomFactor
            self.update()

    def markerMoveRequested(self, x):
        self.moveMarker.emit(self.sender().event, x / self.zoomFactor + self.sender().focusPoint)
        x = self.mapFromGlobal(QtGui.QCursor.pos()).x()
        if x > self.width():
            self.setMinimumWidth(x)

    def markerDeleteRequested(self):
        self.deleteMarker.emit(self.sender().event)

    def checkMarkers(self):
        for marker, markerWidget in self.markers.items():
            if marker not in self.structure.timelineEvents:
                self.markers.pop(marker).deleteLater()
        if self.loopStart and not self.structure.loopStart:
            self.loopStart.deleteLater()
            self.loopEnd.deleteLater()
            self.loopStart = self.loopEnd = self.loopLine = None
        for marker in self.structure.timelineEvents:
            markerWidget = self.markers.get(marker)
            if markerWidget is None:
                markerWidget = self.markerTypeDict[marker.__class__](self, marker)
                self.markers[marker] = markerWidget
                markerWidget.markerMoveRequested.connect(self.markerMoveRequested)
                if not isinstance(markerWidget, EndMarkerWidget):
                    markerWidget.deleteRequested.connect(self.markerDeleteRequested)
                    if isinstance(markerWidget, LoopStartMarkerWidget):
                        markerWidget.loopToFullRequested.connect(self.loopToFullRequested)
                        if isinstance(markerWidget, LoopEndMarkerWidget):
                            self.loopEnd = markerWidget
                        else:
                            self.loopStart = markerWidget
                markerWidget.installEventFilter(self)
            markerWidget.setX(marker.time * BeatHUnit * self.zoomFactor)
            if isinstance(markerWidget, EndMarkerWidget):
                markerWidget.raise_()
        if not self.endMarker:
            for marker in self.markers.values():
                if isinstance(marker, EndMarkerWidget):
                    self.endMarker = marker
                    break
        if self.loopStart and not self.loopLine:
            self.loopLine = LoopLine(self, self.loopStart, self.loopEnd)

    def eventFilter(self, source, event):        
        if event.type() == QtCore.QEvent.MouseMove:
            self.dragMovement.emit()
        return QtWidgets.QWidget.eventFilter(self, source, event)

    def mousePressEvent(self, event):
        if event.buttons() == QtCore.Qt.LeftButton:
            self._mousePos = self.mousePos = event.x()
            self.longPressTimer.start()

    def mouseDoubleClickEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.longPressTimer.stop()
            timelineEventType = self.timelineHeader.timelineTypeFromPos(event.y())
            if timelineEventType:
                self.addTimelineEventRequested.emit(timelineEventType, event.pos().x())

    def mouseMoveEvent(self, event):
        if event.buttons() == QtCore.Qt.LeftButton:
            self.longPressTimer.stop()
            self.dragPlayhead.emit()
#            self.dragMovement.emit()

    def mouseReleaseEvent(self, event):
        self.mousePos = None
        self.longPressTimer.stop()

    def wheelEvent(self, event):
        if event.modifiers() & QtCore.Qt.ShiftModifier:
            delta = 1 if event.delta() > 0 else -1
            scrollBar = self.parent().horizontalScrollBar()
            scrollBar.setValue(scrollBar.value() + (scrollBar.pageStep() + scrollBar.singleStep()) * delta * .125)
#            self.parent().horizontalScrollBar().setValue(self.parent().horizontalS)

    def contextMenuEvent(self, event):
        timelineEventType = self.timelineHeader.timelineTypeFromPos(event.y())
        if not timelineEventType:
            return
        menu = QtWidgets.QMenu()
        if timelineEventType == Marker:
            addAction = menu.addAction(QtGui.QIcon.fromTheme('bookmarks'), 'Add Marker here')
            if not self.structure.loopStart:
                addLoopAction = menu.addAction(QtGui.QIcon.fromTheme('view-refresh'), 'Add Loop')
                addLoopAction.triggered.connect(lambda: self.addLoopRequested.emit(event.pos().x()))
            else:
                removeLoopAction = menu.addAction(QtGui.QIcon.fromTheme('edit-delete'), 'Remove Loop')
                removeLoopAction.triggered.connect(self.structure.removeLoop)
        elif timelineEventType == Tempo:
            addAction = menu.addAction(QtGui.QIcon.fromTheme('list-add'), 'Add Tempo change here')
        else:
            addAction = menu.addAction(QtGui.QIcon.fromTheme('list-add'), 'Add Meter change here')
        res = menu.exec_(QtGui.QCursor.pos())
        if not res:
            return
        if res == addAction:
            self.addTimelineEventRequested.emit(timelineEventType, event.pos().x())
#        elif res == addLoopAction:
#            self.addLoopRequested.emit(event.pos().x())

    def showEvent(self, event):
        if not self.shown:
            self.shown = True
            self.checkMarkers()

    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        qp.translate(.5, .5)
        meters = iter(self.structure.meters)
#        tempos = iter(self.structure.tempos)

#        currentTempo = tempos.next()
#        try:
#            nextTempo = tempos.next()
#        except:
#            nextTempo = None
#        tempoDone = False

        currentMeter = meters.next()
        try:
            nextMeter = meters.next()
        except:
            nextMeter = None

        rulerHeight = self.timelineHeader.rulerHeight
        spacing = self.timelineHeader.layout().spacing()
        barY = self.timelineHeader.rulerPositions[Bar]
        markerY = self.timelineHeader.rulerPositions[Marker]
        tempoY = self.timelineHeader.rulerPositions[Tempo]
        meterY = self.timelineHeader.rulerPositions[Meter]

        rect = event.rect()

        qp.save()
        qp.setPen(QtCore.Qt.lightGray)
        qp.drawLine(rect.left(), markerY - spacing + 1, rect.right(), markerY - spacing + 1)
        qp.drawLine(rect.left(), tempoY - spacing + 1, rect.right(), tempoY - spacing + 1)
        qp.drawLine(rect.left(), meterY - spacing + 1, rect.right(), meterY - spacing + 1)
        qp.restore()

        barBgdColor = self.palette().color(QtGui.QPalette.Window).lighter(150)
        x = 0
        align = QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter
        bar = 1
        beats = 0
        height = self.height()
        unit = BeatHUnit * self.zoomFactor
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
                barData.append((QtCore.QRect(x + 1, barY - 2, qp.fontMetrics().width(str(bar)) + 1, rulerHeight), QtCore.QRect(textX, barY, 50, rulerHeight), str(bar)))

            beats += currentMeter.beats
            bar += 1
            x += currentBarPixels

        for barBgd, barRect, barText in barData:
            qp.fillRect(barBgd, barBgdColor)
            qp.drawText(barRect, align, barText)
        qp.setPen(PlayheadPen)
        qp.drawLine(self.playheadPos, 0, self.playheadPos, height)
        qp.setPen(EndMarkerPen)
        qp.drawLine(self.endMarker.referencePos, 0, self.endMarker.referencePos, height)


class TimelineHeader(QtWidgets.QWidget):
#    Bar, Marker, Tempo, Meter = range(4)

    def __init__(self, parent):
        QtWidgets.QWidget.__init__(self, parent)
        layout = QtWidgets.QVBoxLayout()
        self.setAutoFillBackground(True)
        self.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)
        self.margin = 2
        layout.setSpacing(self.margin)
        self.setContentsMargins(0, self.margin, 10, self.margin)

        align = QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter

        self.barLbl = QtWidgets.QLabel('Bars')
        layout.addWidget(self.barLbl)
        self.barLbl.setAlignment(align)

        self.markerLbl = QtWidgets.QLabel('Markers')
        layout.addWidget(self.markerLbl)
        self.markerLbl.setAlignment(align)

        self.tempoLbl = QtWidgets.QLabel('Tempo')
        layout.addWidget(self.tempoLbl)
        self.tempoLbl.setAlignment(align)

        self.meterLbl = QtWidgets.QLabel('Meter')
        layout.addWidget(self.meterLbl)
        self.meterLbl.setAlignment(align)

        self.timelineLabels = [self.barLbl, self.markerLbl, self.tempoLbl, self.meterLbl]
        self.timelineTypes = {
            self.barLbl: Bar, 
            self.markerLbl: Marker, 
            self.tempoLbl: Tempo, 
            self.meterLbl: Meter, 
        }

        self.rulerHeight = self.fontMetrics().height() - 1
        self.setFixedHeight(self.rulerHeight * 4 + layout.spacing() * 3)

        self.rulerPositions = {
            Bar: 0, 
            Marker: 0, 
            Tempo: 0, 
            Meter: 0, 
        }

    def timelineTypeFromPos(self, y):
        for label in self.timelineLabels:
            if label.isVisible() and label.y() - 1 <= y <= label.geometry().bottom() + 1:
                return self.timelineTypes[label]

    def showEvent(self, event):
        if not event.spontaneous():
            self.rulerPositions[Bar] = self.barLbl.y()
            self.rulerPositions[Marker] = self.markerLbl.y()
            self.rulerPositions[Tempo] = self.tempoLbl.y()
            self.rulerPositions[Meter] = self.meterLbl.y()
            self.raise_()


class MetaRegionWidget(QtWidgets.QFrame):
    _sizeHint = None
    heightChanged = QtCore.pyqtSignal(int)
    wheelEventSignal = QtCore.pyqtSignal(object)

    automationPadding = 10
    baseStyleSheet = '''
        MetaRegionWidget {{
            border: 1px solid lightGray;
            border-style: outset;
        }}
        AutomationTrackWidget {{
            margin-left: {automationPadding}px;
        }}
    '''.format(automationPadding=automationPadding)
    focusStyleSheet = '''
        MetaRegionWidget {
            border: 1px solid red;
        }
    '''
    sheets = baseStyleSheet, focusStyleSheet

    def __init__(self, track):
        QtWidgets.QFrame.__init__(self)
#        self.setFrameStyle(self.Box|self.Plain)
        self.setStyleSheet(self.baseStyleSheet)
        self.track = track
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 6)
        self.margin = 2
        self.setContentsMargins(2, 2, 2, 2)
        self.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.mousePos = None
        self.setMouseTracking(True)
#        QtWidgets.QApplication.instance().focusChanged.connect(self.checkFocus)

#    def checkFocus(self, prev, current):
#        self.setStyleSheet(self.sheets[current in self.children() or self.hasFocus()])

    def sizeHint(self):
        if self._sizeHint is None:
            return QtWidgets.QFrame.sizeHint(self)
        return self._sizeHint

    def mouseMoveEvent(self, event):
        if event.buttons() == QtCore.Qt.LeftButton and self.mousePos is not None:
            self.setCursor(QtCore.Qt.SizeVerCursor)
            height = max(self._sizeHint.height(), event.pos().y())
#            self.heightChanged.emit(height)
            self.setFixedHeight(height)
            self.parent().layout().invalidate()
        elif event.y() > self.height() - 8:
            self.setCursor(QtCore.Qt.SizeVerCursor)
        else:
            self.unsetCursor()

    def mousePressEvent(self, event):
        if event.buttons() == QtCore.Qt.LeftButton and event.y() > self.height() - 8:
            if self._sizeHint is None:
                self._sizeHint = self.size()
                self.setMinimumHeight(self.height())
            self.mousePos = event.pos()
        QtWidgets.QWidget.mousePressEvent(self, event)

    def mouseReleaseEvent(self, event):
        self.mousePos = None
        if event.y() <= self.height() - 8:
            self.unsetCursor()

    def wheelEvent(self, event):
        self.wheelEventSignal.emit(QtGui.QWheelEvent(
            event.pos(), event.globalPos(), event.delta(), event.buttons(), event.modifiers(), event.orientation()))


class AutomationWidget(QtWidgets.QWidget):
    statusChanged = QtCore.pyqtSignal(int)
    Collapsed, Partial, Expanded = 0, 1, 2

    def __init__(self, track):
        QtWidgets.QWidget.__init__(self)
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        self.track = track
        self._status = self.Collapsed
        self.addBtn = QtWidgets.QPushButton('+', self)
        self.addBtn.setStyleSheet('''
            QPushButton {
                border: 1px solid palette(mid);
                border-style: outset;
            }
            QPushButton:hover {
                border-color: palette(dark);
            }
            QPushButton:pressed {
                border-style: inset;
            }
            ''')
        self.addBtn.setFixedWidth(self.fontMetrics().height())
        self.addBtn.setFlat(True)
        self.addBtn.setToolTip('Add automation')

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, status):
        if status != self._status:
            if status and not self.track.automations():
                return
            self._status = status
            self.update()
            self.statusChanged.emit(status)

    def expand(self):
        self.status = self.Expanded

    def collapse(self):
        self.status = self.Collapsed

    def createArrows(self):
        fm = self.fontMetrics()
        self.arrowSize = fm.height()
        self.setFixedHeight(self.arrowSize)
        size = self.arrowSize - self.fontMetrics().descent()
        halfSize = size * .5
        quartSize = halfSize * .5
        center = QtCore.QRectF(0, 0, self.rect().height(), self.rect().height()).center()

        collapsedPoly = QtGui.QPolygonF(QtGui.QPolygon([
            -quartSize, -halfSize, 
            quartSize, 0, 
            -quartSize, halfSize
            ]))
        collapsedArrow = QtGui.QPainterPath()
        collapsedArrow.addPolygon(collapsedPoly.translated(center))

        partialPoly = QtGui.QPolygonF(QtGui.QPolygon([
            -quartSize, quartSize, 
            quartSize, -quartSize, 
            quartSize, quartSize
            ]))
        partialArrow = QtGui.QPainterPath()
        partialArrow.addPolygon(partialPoly.translated(center))

        expandedPoly = QtGui.QPolygonF(QtGui.QPolygon([
            -halfSize, -quartSize, 
            halfSize, -quartSize, 
            0, quartSize
            ]))
        expandedArrow = QtGui.QPainterPath()
        expandedArrow.addPolygon(expandedPoly.translated(center))

        self.arrows = collapsedArrow, partialArrow, expandedArrow


    def mousePressEvent(self, event):
        if event.buttons() == QtCore.Qt.LeftButton:
            if not self._status:
                self.status = self.Expanded
            else:
                self.status = self.Collapsed
            self.update()

    def changeEvent(self, event):
        if event.type() == QtCore.QEvent.FontChange:
            self.createArrows()
#            self.update()

    def resizeEvent(self, event):
        self.createArrows()
        self.addBtn.setFixedHeight(self.height())
        self.addBtn.move(self.width() - self.addBtn.width() - 1, 0)

    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        qp.setRenderHints(qp.Antialiasing)
        qp.translate(.5, .5)
#        qp.drawRect(self.rect().adjusted(0, 0, -1, -1))
        qp.save()
        qp.setPen(QtCore.Qt.NoPen)
        qp.setBrush(QtCore.Qt.black if self.track.automations() else QtCore.Qt.darkGray)
        qp.drawPath(self.arrows[self._status])

        qp.restore()
        qp.drawText(self.rect().adjusted(self.arrowSize, 0, 0, 0), QtCore.Qt.AlignVCenter|QtCore.Qt.AlignLeft, 'Automations')


class TrackHandle(QtWidgets.QFrame):
    def __init__(self, parent):
        QtWidgets.QFrame.__init__(self, parent)
        self.setFrameStyle(self.StyledPanel|self.Raised)
        self.mousePos = None
        self.setFocusPolicy(QtCore.Qt.ClickFocus)

    def mousePressEvent(self, event):
        if event.buttons() == QtCore.Qt.LeftButton:
            self.mousePos = event.pos()

    def mouseMoveEvent(self, event):
        if self.mousePos is not None and (self.mousePos - event.pos()).manhattanLength() >= QtWidgets.QApplication.startDragDistance():
            dragObject = QtGui.QDrag(self.parent())

            mimeData = QtCore.QMimeData()
            byteArray = QtCore.QByteArray()
#            stream = QtCore.QDataStream(byteArray, QtCore.QIODevice.WriteOnly)
#            stream.writeInt(self.parent().track.index())
            mimeData.setData('bigglesworth/SequencerTrack', byteArray)
            dragObject.setMimeData(mimeData)

            palette = self.palette()
            pm = QtGui.QPixmap(self.parent().size())
            pm.fill(palette.color(palette.Window))
            qp = QtGui.QPainter(pm)
            self.parent().render(qp)
            qp.end()

            dragObject.setPixmap(pm)
            dragObject.exec_(QtCore.Qt.CopyAction|QtCore.Qt.MoveAction, QtCore.Qt.MoveAction)

    def mouseReleaseEvent(self, event):
        self.mousePos = None


class MainTrackWidget(MetaRegionWidget):
    addAutomationRequested = QtCore.pyqtSignal([], [object])
    deleteRequested = QtCore.pyqtSignal()

    def __init__(self, track):
        MetaRegionWidget.__init__(self, track)
        l, t, r, b = self.layout().getContentsMargins()
        self.layout().setContentsMargins(l + 8, t, r, b)

        self.handle = TrackHandle(self)
        self.handle.setFixedWidth(8)

        self._label = track.label
        self.labelEdit = QtWidgets.QLineEdit(track.label)
        self.layout().addWidget(self.labelEdit)
        self.labelEdit.setMaxLength(16)
        self.labelEdit.setFrame(False)
        self.labelEdit.editingFinished.connect(self.setTrackLabel)

        chanLayout = QtWidgets.QHBoxLayout()
        self.layout().addLayout(chanLayout)
        chanLbl = QtWidgets.QLabel('Channel:')
        chanLbl.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Preferred)
        chanLayout.addWidget(chanLbl)
        self.channelCombo = ComboSpin(self)
        chanLayout.addWidget(self.channelCombo)
        self.channelCombo.setRange(1, 16)
        self.channelCombo.setFrame(False)
        self.channelCombo.setCurrentIndex(track.channel)
        self.channelCombo.currentIndexChanged.connect(self.setTrackChannel)

        self.layout().addStretch(0)

        self.automationWidget = AutomationWidget(track)
        self.layout().addWidget(self.automationWidget)
        self.automationWidget.addBtn.clicked.connect(self.addAutomationRequested)

    def setTrackLabel(self):
        self.track.label = self.labelEdit.text()

    def setTrackChannel(self, channel):
        self.track.channel = channel

    def contextMenuEvent(self, event):
        menu = QtWidgets.QMenu()
        menu.setSeparatorsCollapsible(False)
        menu.addSection(self.track.label)
        addAutoAction = menu.addAction(QtGui.QIcon.fromTheme('document-new'), 'Add automation...')
        addAutoAction.triggered.connect(self.addAutomationRequested)
        autoMenu = menu.addMenu('Automations')
        mapping = Mappings['Blofeld']
        autoSubMenu = autoMenu.addMenu('')
        firstValid = lastValid = count = 0
        existing = [p[1] for p in self.track.automations(CtrlParameter)]
        for ctrl in range(128):
            try:
                assert ctrl in mapping
                count += 1
                if count > 16:
                    title = '{} - {}'.format(firstValid, lastValid)
                    count = len([a for a in autoSubMenu.actions() if a.isChecked()])
                    if count:
                        title += ' ({})'.format(count)
                    autoSubMenu.setTitle(title)
                    firstValid = lastValid = ctrl
                    count = 0
                    autoSubMenu = autoMenu.addMenu('')
                else:
                    lastValid = ctrl
                addAutoAction = autoSubMenu.addAction('{} - {}'.format(ctrl, getCtrlNameFromMapping(ctrl)[0]))
                addAutoAction.triggered.connect(lambda _, ctrl=ctrl: self.addAutomationRequested[object].emit(RegionInfo(CtrlParameter, ctrl, mapping='Blofeld')))
                addAutoAction.setCheckable(True)
                if ctrl in existing:
                    addAutoAction.setChecked(True)
            except:
                pass
        title = '{} - {}'.format(firstValid, lastValid)
        count = len([a for a in autoSubMenu.actions() if a.isChecked()])
        if count:
            title += ' ({})'.format(count)
        autoSubMenu.setTitle(title)
        if self.track.automations():
            if self.automationWidget.status != self.automationWidget.Expanded:
                showAllAutoAction = menu.addAction('Show all automations')
                showAllAutoAction.triggered.connect(self.automationWidget.expand)
            if self.automationWidget.status != self.automationWidget.Collapsed:
                hideAllAutoAction = menu.addAction('Hide all automations')
                hideAllAutoAction.triggered.connect(self.automationWidget.collapse)
        menu.addSeparator()
        deleteAction = menu.addAction(QtGui.QIcon.fromTheme('edit-delete'), 'Delete track')
        deleteAction.triggered.connect(self.deleteRequested)
        if self.track.structure.trackCount() == 1:
            deleteAction.setEnabled(False)
        menu.exec_(QtGui.QCursor.pos())

    def resizeEvent(self, event):
        self.handle.move(1, 0)
        self.handle.setFixedHeight(self.height())


class AutomationTrackWidget(MetaRegionWidget):
    addAutomationRequested = QtCore.pyqtSignal()
    deleteRequested = QtCore.pyqtSignal()

    def __init__(self, track, automationInfo):
        MetaRegionWidget.__init__(self, track)
        l, t, r, b = self.layout().getContentsMargins()
        self.layout().setContentsMargins(l + self.automationPadding, t, r, b)
        self.automationInfo = automationInfo

        if automationInfo.parameterType == BlofeldParameter:
            param = Parameters.parameterData[automationInfo.parameterId >> 4]
            if param.children:
                param.children[automationInfo.parameterId & 7]
            self.label = QtWidgets.QLabel(param.fullName)
            self.setToolTip(param.fullName)
        elif automationInfo.parameterType == CtrlParameter:
            description = getCtrlNameFromMapping(automationInfo.parameterId, mapping=automationInfo.mapping, short=True)[0]
            self.label = QtWidgets.QLabel(description)
            self.setToolTip('CC {}\n{}'.format(automationInfo.parameterId, description))
        self.layout().addWidget(self.label)


class TrackContainerWidget(QtWidgets.QWidget):
    addAutomationRequested = QtCore.pyqtSignal([object], [object, object])
    dragPen = QtGui.QPen(QtCore.Qt.blue, 2)
    dragPen.setCosmetic(True)
    wheelEventSignal = QtCore.pyqtSignal(object)

    def __init__(self, parent, structure):
        QtWidgets.QWidget.__init__(self, parent)
        self.structure = structure
        self.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding)
        self.setMinimumSize(10, 10)
        self.setMouseTracking(True)
        self.setAcceptDrops(True)

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSizeConstraint(layout.SetFixedSize)
        layout.setSpacing(0)

        self.dropIndex = None
        self.trackWidgets = {}
        self.automationTrackWidgets = {}
        self.handles = {}
        for track in structure.tracks:
            self.addTrack(track)

    def addAutomation(self, track, automationInfo):
        if track.index() == self.structure.trackCount() - 1:
            index = self.layout().count()
        else:
            index = self.layout().indexOf(self.trackWidgets[self.structure.tracks[track.index() + 1]])
        widget = AutomationTrackWidget(track, automationInfo)
        widget.setMaximumWidth(self.width())
        self.automationTrackWidgets[track][automationInfo] = widget
        self.layout().insertWidget(index, widget)
        #this is necessary for the following comprehension, as for some reason the widget is added but not yet visible
        widget.setVisible(True)
        visible = [w.isVisible() for w in self.automationTrackWidgets[track].values()]
        automationWidget = self.trackWidgets[track].automationWidget
        automationWidget.blockSignals(True)
        automationWidget.status = automationWidget.Expanded if all(visible) else automationWidget.Partial
        automationWidget.blockSignals(False)

    def deleteTrack(self, track):
        if QtWidgets.QMessageBox.warning(self, 'Delete track', 
            'Do you want to remove track "{}" and all its contents?<br>'
            'This operation cannot be undone!'.format(track.label), 
            QtWidgets.QMessageBox.Ok|QtWidgets.QMessageBox.Cancel) == QtWidgets.QMessageBox.Ok:
                trackWidget = self.trackWidgets.pop(track)
                self.layout().removeWidget(trackWidget)
                self.structure.deleteTrack(track)
                trackWidget.deleteLater()

    def addTrack(self, track):
        self.automationTrackWidgets[track] = {}
        trackWidget = MainTrackWidget(track)
        trackWidget.addAutomationRequested.connect(lambda track=track: self.addAutomationRequested.emit(track))
        trackWidget.addAutomationRequested[object].connect(
            lambda automationInfo, track=track: self.addAutomationRequested[object, object].emit(track, automationInfo))
        trackWidget.automationWidget.statusChanged.connect(self.automationDisplayChanged)
        trackWidget.deleteRequested.connect(lambda track=track: self.deleteTrack(track))
        trackWidget.wheelEventSignal.connect(self.wheelEventSignal)
        self.trackWidgets[track] = trackWidget
        self.layout().addWidget(trackWidget)
        for automation in track.automations():
            self.addAutomation(track, automation)

    def automationDisplayChanged(self, status):
        track = self.sender().track
        for widget in self.automationTrackWidgets[track].values():
            widget.setVisible(status)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat('bigglesworth/SequencerTrack'):
            event.accept()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat('bigglesworth/SequencerTrack'):
            for trackWidget in self.trackWidgets.values():
                if event.pos() in trackWidget.geometry():
                    self.dropIndex = trackWidget.track.index()
                    if event.pos().y() > trackWidget.geometry().center().y():
                        self.dropIndex += 1
                    self.dropIndex = min(self.dropIndex, self.structure.trackCount())
                    break
            else:
                self.dropIndex = None
                event.ignore()
                self.update()
                return
            event.accept()
            self.update()

    def dragLeaveEvent(self, event):
        self.dropIndex = None
        self.update()

    def dropEvent(self, event):
        self.structure.moveTrack(event.source().track, self.dropIndex)
        self.dropIndex = None
        index = 0
        for track in self.structure.tracks:
            self.layout().insertWidget(index, self.trackWidgets[track])
            index += 1
            automationTrackWidgets = self.automationTrackWidgets[track]
            for automationInfo in sorted(automationTrackWidgets.keys()):
                self.layout().insertWidget(index, automationTrackWidgets[automationInfo])
                index += 1

        QtWidgets.QApplication.processEvents()
        self.structure.changed.emit()
        self.update()

    def paintEvent(self, event):
        QtWidgets.QWidget.paintEvent(self, event)
        if self.dropIndex is not None:
            qp = QtGui.QPainter(self)
            qp.setRenderHints(qp.Antialiasing)
            qp.translate(.5, .5)
            qp.setPen(self.dragPen)
            if self.dropIndex == len(self.trackWidgets):
                y = self.height() - 2
            else:
                trackWidget = self.trackWidgets[self.structure.tracks[self.dropIndex]]
                y = max(0, trackWidget.geometry().top() - 1)
            qp.drawLine(0, y, self.width(), y)


class TrackBackground(QtWidgets.QWidget):
    doubleClicked = QtCore.pyqtSignal()

    def mouseDoubleClickEvent(self, event):
        self.doubleClicked.emit()


class SequencerView(QtWidgets.QGraphicsView):
    repeatDialogRequested = QtCore.pyqtSignal(object)
    zoomChanged = QtCore.pyqtSignal(float)
    playheadMoved = QtCore.pyqtSignal(float)

    barPen = QtGui.QPen(QtCore.Qt.lightGray, 1)
    barPen.setCosmetic(True)
    thinPen = QtGui.QPen(QtCore.Qt.darkGray, .5)
    thinPen.setCosmetic(True)

    def __init__(self, *args, **kwargs):
        QtWidgets.QGraphicsView.__init__(self, *args, **kwargs)
        self.structure = Structure()
        self.structure.timelineChanged.connect(self.viewport().update)
        self.structure.changed.connect(self.viewport().update)

        l, t, r, b = self.getContentsMargins()
        fm = self.fontMetrics()
        borderWidth = max(1, int(fm.height() / 10.)) * 2 + l
        self.trackWidth = fm.width('Track 8888888888888') + borderWidth * 2
        self.timelineHeight = fm.height() * 2

        self.timelineHeader = TimelineHeader(self)
        self.timelineHeader.setMinimumWidth(self.trackWidth)
#        self.timelineHeader.resize(self.trackWidth, self.timelineHeight)

        self.trackBackground = TrackBackground(self)
        self.trackBackground.doubleClicked.connect(self.addTracks)
        self.trackBackground.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
#        self.trackBackground.setFocusPolicy(QtCore.Qt.NoFocus)
        self.trackBackground.customContextMenuRequested.connect(self.showTrackMenu)

        self.trackContainerWidget = TrackContainerWidget(self, self.structure)
        self.trackContainerWidget.move(0, self.timelineHeight)
        self.trackContainerWidget.setMinimumWidth(self.trackWidth)
        self.trackContainerWidget.addAutomationRequested.connect(self.addAutomation)
        self.trackContainerWidget.addAutomationRequested[object, object].connect(self.addAutomation)
        self.trackContainerWidget.wheelEventSignal.connect(self.wheelEvent)
        self.trackContainerWidget.raise_()

        self.timelineWidget = TimelineWidget(self, self.timelineHeader, self.structure)
        self.timelineWidget.addTimelineEventRequested.connect(self.addTimelineEvent)
        self.timelineWidget.addLoopRequested.connect(self.addLoop)
        self.timelineWidget.loopToFullRequested.connect(self.structure.setLoopToFull)
        self.timelineWidget.moveMarker.connect(self.moveMarker)
        self.timelineWidget.deleteMarker.connect(self.deleteMarker)
        self.timelineWidget.dragMovement.connect(self.timelineDragMovement)
        self.timelineWidget.dragPlayhead.connect(self.dragPlayhead)
        self.zoomChanged.connect(self.timelineWidget.zoomChanged)

        scene = SequencerScene(self, self.structure, self.trackContainerWidget)
        self.setScene(scene)
        self.trackContainer = scene.trackContainer
        self.cursorLine = scene.cursorLine
        scene.editRequested.connect(self.editItem)
        self.beatSnap = scene.beatSnap = SnapModes[DefaultPatternSnapModeId].length
        self.menuActive = False

        self.playhead = scene.playhead
#        self.playheadTimer = QtCore.QTimer()
#        self.playheadTimer.setInterval(20)
#        self.playheadTimer.timeout.connect(self.setPlayhead)
#        self.elapsedTimer = QtCore.QElapsedTimer()
        self.endLine = scene.endLine
        self.followPlayhead = True
        self.playAnimation = QtCore.QSequentialAnimationGroup()
        self.structure.timelineChanged.connect(self.setPlayAnimation)
        self._playheadTime = 0
        self.setPlayAnimation()

    def setZoom(self, delta):
        factor = self.transform().m11()
        if delta > 0:
            factor *= 2
        else:
            factor *= .5
        factor = sanitize(.125, factor, 8)
        if factor != self.transform().m11():
            self.setTransform(QtGui.QTransform().scale(factor, 1.))
            self.zoomChanged.emit(factor)

    @property
    def addTracksAction(self):
        return self.window().addTracksAction

    @QtCore.pyqtProperty(float)
    def playheadTime(self):
        return self._playheadTime

    @playheadTime.setter
    def playheadTime(self, time):
        self._playheadTime = time
        pos = BeatHUnit * time
        self.playhead.setX(pos)
        self.timelineWidget.setPlayheadPos(pos)

    def _wheelEvent(self, event):
        print(self, event)

    def showTrackMenu(self):
        menu = QtWidgets.QMenu()
        menu.addAction(self.addTracksAction)
        menu.exec_(QtGui.QCursor.pos())

    def dragPlayhead(self):
        x = self.viewport().mapFromGlobal(QtGui.QCursor.pos()).x() / self.transform().m11()
        time = max(0, (float(x) / BeatHUnit) // self.beatSnap * self.beatSnap)
        self.playheadTime = time
        self.timelineDragMovement(x)
        self.playheadMoved.emit(time)

    def timelineDragMovement(self, x=None):
        viewport = self.viewport()
        rect = viewport.rect()
        if x is None:
            x = viewport.mapFromGlobal(QtGui.QCursor.pos()).x()
        if x < rect.x() + 16:
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() + x - rect.x() - 16)
        elif x > rect.right() - 16:
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() + x - rect.right() + 16)
        mapped = self.mapToScene(QtCore.QPoint(x, 0)).x()
        if mapped > self.sceneRect().right():
            rect = self.sceneRect()
            rect.setRight(mapped)
            self.setSceneRect(rect)
#        print(x, self.viewport().geometry())

    def moveMarker(self, marker, x):
        time = marker.time + (float(x) / BeatHUnit)
        if isinstance(marker, EndMarker):
            try:
                marker.time = max(self.beatSnap, time // self.beatSnap * self.beatSnap)
            except:
                marker.time = time
            self.endLine.setX(marker.time * BeatHUnit)
        elif isinstance(marker, (MarkerEvent, TempoEvent, LoopStartMarker, LoopEndMarker)):
            try:
                marker.time = max(0, time // self.beatSnap * self.beatSnap)
            except:
                marker.time = max(0, time)
        else:
            marker.bar = self.structure.barFromTime(max(0, time))
#            print('NO!!! devi spostare per battuta!')
#            marker.time = max(0, time // self.beatSnap * self.beatSnap)

    def addTimelineEvent(self, eventType, x):
        x /= self.transform().m11()
        try:
            time = (x / BeatHUnit) // self.beatSnap * self.beatSnap
        except:
            time = x / BeatHUnit
        self.structure.addTimelineEvent(eventType, time)

    def addLoop(self, x):
        x /= self.transform().m11()
        try:
            time = (x / BeatHUnit) // self.beatSnap * self.beatSnap
        except:
            time = x / BeatHUnit
        self.structure.addLoop(time, time + max(1, self.beatSnap))

    def deleteMarker(self, marker):
        self.structure.deleteMarker(marker)

    def setPlayAnimation(self):
        self.playAnimation.clear()
        tempoIter = iter(self.structure.tempos)
        currentTempo = tempoIter.next()
        currentTime = 0
        currentPos = 0
        keepGoing = True
        while keepGoing:
            animation = QtCore.QPropertyAnimation(self, b'playheadTime')
            try:
                nextTempo = tempoIter.next()
                diff = nextTempo.time - currentTempo.time
            except:
                nextTempo = None
                diff = 20000
                keepGoing = False
            duration = diff * currentTempo.beatLengthMs
            animation.setDuration(duration)
            currentTime += duration
            animation.setStartValue(currentPos)
            currentPos += duration * currentTempo.beatSize
            animation.setEndValue(currentPos)
            self.playAnimation.addAnimation(animation)
            currentTempo = nextTempo

    def stop(self):
        self.playheadTime = 0
        self.playAnimation.stop()

    def togglePlay(self, state):
        if state:
            self.playAnimation.start()
        else:
            self.playAnimation.stop()

    def ensurePlayheadVisible(self):
        if not self.followPlayhead:
            return
        self.ensureVisible(QtCore.QRectF(self.playhead.x(), self.mapToScene(self.viewport().rect().center()).y(), 1, 1))

    def setPlayheadTime(self, time):
        self.playheadTime = time
        self.ensurePlayheadVisible()

#    def setPlayhead(self):
##        x = self.tempoMapLambda(self.elapsedTimer.elapsed())
##        self.playhead.setX(self.elapsedTimer.elapsed() * .002 * BeatHUnit)
##        elapsed = self.elapsedTimer.elapsed() * .001
##        if 0 <= elapsed % 1000 <= 100:
##            e = elapsed * .002 * BeatHUnit
##            l = self.tempoMapLambda(elapsed * .001 / BeatHUnit)
##            print('e: {:.2f}, l: {:.02f}, d: {:.05f}'.format(e, l, e-l))
#        elapsed = self.elapsedTimer.elapsed()
#        for time, func in self.tempoLambdas:
#            if time > elapsed:
##                x = elapsed * .002 * BeatHUnit
##                print(x, func(elapsed) * BeatHUnit)
#                x = func(elapsed) * BeatHUnit
#                break
#        self.playhead.setX(x)
#        self.timelineWidget.setPlayheadPos(x)
#        self.ensurePlayheadVisible()

    def addAutomation(self, track, automationInfo=None):
        if automationInfo is None:
            dialog = AddAutomationDialog(self, track.automations(CtrlParameter))
            if not dialog.exec_():
                return
            automationInfo = track.addAutomation(dialog.automationInfo())
        else:
            automationInfo = track.addAutomation(automationInfo)
        if automationInfo:
            self.trackContainerWidget.addAutomation(track, automationInfo)
            self.trackContainer.rebuild()

    def setBeatSnapMode(self, snapMode):
        self.beatSnap = self.scene().beatSnap = snapMode.length
#    assert 'stocazzo, fare il rebuild del trackcontainer con automation' == False

    def editItem(self, item):
        if isinstance(item, NotePatternItem):
            editor = NoteRegionEditor(self.window(), item.pattern)
            if editor.exec_():
                track = item.pattern.track
                existing = track.automations()
                item.pattern.copyFrom(editor.pattern)
                for automation in track.automations():
                    if automation not in existing:
                        self.trackContainerWidget.addAutomation(track, automation)
                self.trackContainer.rebuild()

    def trackSizes(self):
        tracks = []
        for track in self.structure.tracks:
            trackWidget = self.trackContainerWidget.trackWidgets[track]
            geo = trackWidget.geometry()
            tracks.append((track, geo.top(), geo.bottom()))
        return tracks

    def addPattern(self, track, pos=None):
        if pos is not None:
            pos = self.mapToScene(pos)
            time = pos.x() // (BeatHUnit * self.beatSnap) * self.beatSnap
        else:
            time = None
        track.addPattern(time=time, length=self.beatSnap)
        self.trackContainer.rebuild()

    def addSingleTrack(self):
        self.addTracks(single=True)

    def addTracks(self, single=False):
        if self.structure.trackCount() >= 16:
            return
        res = AddTracksDialog(self, single).exec_()
        if not res:
            return
        count, label, channel = res
        for t in range(count):
            track = self.structure.addTrack(label=label, channel=channel)
            self.trackContainerWidget.addTrack(track)
        self.trackContainer.rebuild()

    def deletePatterns(self, items):
        if QtWidgets.QMessageBox.warning(self, 'Delete patterns', 
            'Do you want to remove the selected patterns?<br>'
            'This operation cannot be undone!', 
            QtWidgets.QMessageBox.Ok|QtWidgets.QMessageBox.Cancel) == QtWidgets.QMessageBox.Ok:
                self.structure.deletePatterns([patternItem.pattern for patternItem in items])

    def quantizePatterns(self, items):
        dialog = QuantizeDialog(self)
        hasOther = hasNotes = False
        patterns = [item.pattern for item in items]
        for pattern in patterns:
            for event in pattern.events:
                if isinstance(event, (NoteOffEvent, NoteOnEvent)):
                    hasNotes = True
                else:
                    hasOther = True
                if hasOther and hasNotes:
                    break
            if hasOther and hasNotes:
                break
        if not (hasNotes or hasOther):
            QtWidgets.QMessageBox.information(self, 'No events to quantize', 
                'The selected items do not contain events to quantize.', 
                QtWidgets.QMessageBox.Ok)
            return
        res = dialog.exec_(patternMode=True, hasNotes=hasNotes, hasOther=hasOther)
        if res:
            for pattern in patterns:
                pattern.quantize(*res)

    def drawBackground(self, qp, rect):
        qp.fillRect(rect, self.backgroundBrush())
        meters = iter(self.structure.meters)

        currentMeter = meters.next()
        try:
            nextMeter = meters.next()
        except:
            nextMeter = None

        height = self.height()

        qp.save()
        qp.setPen(self.thinPen)
        trackLayout = self.trackContainerWidget.layout()
        for index in range(trackLayout.count()):
            item = trackLayout.itemAt(index)
            if item.widget() and item.widget().isVisible():
                geo = item.geometry()
                height = geo.bottom()
                if height > 0:
                    qp.drawLine(rect.left(), height, rect.right(), height)
        qp.restore()

        x = 0
        bar = 1
        beats = 0
        unit = BeatHUnit
        currentBarPixels = unit * currentMeter.beats
        currentBeatPixels = unit / currentMeter.denominator * 4
        xtransform = self.transform().m11()
        while x < rect.right():
            if nextMeter:
                if beats + currentMeter.beats > nextMeter.time:
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
            qp.save()
            qp.setPen(self.barPen)
            qp.drawLine(x, 0, x, height)
            qp.restore()

            if currentBeatPixels * xtransform > 4:
                beatPixels = currentBeatPixels
                qp.save()
                qp.setPen(self.thinPen)
                while beatPixels < currentBarPixels:
                    qp.drawLine(x + beatPixels, 0, x + beatPixels, height)
                    beatPixels += currentBeatPixels
                qp.restore()


            beats += currentMeter.beats
            bar += 1
            x += currentBarPixels

#        qp.setPen(PlayheadPen)
#        qp.drawLine(self.playheadPos, 0, self.playheadPos, height)
#        qp.setPen(EndMarkerPen)
#        qp.drawLine(self.endMarker.referencePos, 0, self.endMarker.referencePos, height)

    def viewportEvent(self, event):
        if event.type() == QtCore.QEvent.MouseMove:
            if self.scene().currentItem and event.buttons() == QtCore.Qt.LeftButton:
                self.cursorLine.setVisible(False)
            else:
                self.cursorLine.setVisible(True)
                if self.beatSnap:
                    snapRatio = BeatHUnit * self.beatSnap
                    snap, rest = divmod(self.mapToScene(event.pos()).x(), snapRatio)
                    snap *= snapRatio
                    if rest > snapRatio * .75:
                        snap += snapRatio
                    self.cursorLine.setX(snap)
                else:
                    self.cursorLine.setX(self.mapToScene(event.pos()).x())
        elif event.type() == QtCore.QEvent.Leave and not self.menuActive:
            self.cursorLine.setVisible(False)
        elif event.type() == QtCore.QEvent.Enter:
            self.cursorLine.setVisible(True)
        return QtWidgets.QGraphicsView.viewportEvent(self, event)

    def mouseDoubleClickEvent(self, event):
        item = self.itemAt(event.pos())
        if item and not isinstance(item, TrackContainer):
            QtWidgets.QGraphicsView.mouseDoubleClickEvent(self, event)
        else:
            for track, top, bottom in self.trackSizes():
                if top <= event.y() - self.trackContainerWidget.y() + self.timelineHeader.height() <= bottom:
                    self.addPattern(track, event.pos())
                    break
            else:
                menu = QtWidgets.QMenu()
                menu.addAction(self.addTracksAction)
                menu.exec_(QtGui.QCursor.pos())

    def __mouseMoveEvent(self, event):
        print('move')
        QtWidgets.QGraphicsView.mouseMoveEvent(self, event)

    def contextMenuEvent(self, event):
        selected = self.scene().selectedItems()
        menu = QtWidgets.QMenu()
        if not selected:
            for track, top, bottom in self.trackSizes():
                if top <= event.y() - self.trackContainerWidget.y() + self.timelineHeader.height() <= bottom:
                    newPatternAction = menu.addAction(QtGui.QIcon.fromTheme('document-new'), 'Add pattern to "{}"'.format(track.label))
                    newPatternAction.triggered.connect(lambda: self.addPattern(track, pos=event.pos()))
                    break
            menu.addSeparator()
            menu.addAction(self.addTracksAction)
        else:
            if len(selected) == 1:
                plural = ''
                item = selected[0]
                if isinstance(item, PatternRectItem):
                    if event.modifiers() != QtCore.Qt.ControlModifier:
                        self.scene().clearSelection()
                    item.setSelected(True)
                    editAction = menu.addAction(QtGui.QIcon.fromTheme('document-edit'), 'Edit...')
                    editAction.triggered.connect(lambda: self.editItem(item))
                    repeatAction = menu.addAction(QtGui.QIcon.fromTheme('edit-duplicate'), 'Loop...')
                    repeatAction.triggered.connect(lambda: self.repeatDialogRequested.emit(item.pattern))
                    if item.pattern.repetitions > 1:
                        unloopAction = menu.addAction('Unlink {} loops'.format(item.pattern.repetitions - 1))
                        unloopAction.triggered.connect(item.pattern.unloop)
            else:
                plural = 's'
            quantizeAction = menu.addAction(QtGui.QIcon.fromTheme('grid-rectangular'), 'Quantize pattern' + plural)
            quantizeAction.triggered.connect(lambda: self.quantizePatterns(selected))
            menu.addSeparator()
            delPatternAction = menu.addAction(QtGui.QIcon.fromTheme('edit-delete'), 'Delete pattern' + plural)
            delPatternAction.triggered.connect(lambda: self.deletePatterns(selected))
        self.menuActive = True
        menu.exec_(QtGui.QCursor.pos())
        self.menuActive = False
        if not self.underMouse():
            self.cursorLine.setVisible(False)

    def showEvent(self, event):
        QtWidgets.QGraphicsView.showEvent(self, event)
        if not event.spontaneous() and not self.scrollBarWidgets(QtCore.Qt.AlignTop):
            self.timelineHeight = self.timelineHeader.height()
            self.timelineHeader.setFixedHeight(self.timelineHeight)
            self.setViewportMargins(self.trackWidth, self.timelineHeight, 0, 0)
            self.timelineWidget.setFixedHeight(self.timelineHeight)

            self.zoomWidget = ZoomWidget(self, QtCore.Qt.Horizontal)
            self.zoomWidget.zoomChanged.connect(self.setZoom)
            self.zoomChanged.connect(self.zoomWidget.setZoom)
            self.addScrollBarWidget(self.zoomWidget, QtCore.Qt.AlignRight)
            self.addScrollBarWidget(ScrollBarSpacer(self, QtCore.Qt.Vertical, self.timelineHeight), QtCore.Qt.AlignTop)
            self.addScrollBarWidget(ScrollBarSpacer(self, QtCore.Qt.Horizontal, self.trackWidth), QtCore.Qt.AlignLeft)

            self.verticalScrollBar().valueChanged.connect(self.updateTrackPositions)
            self.horizontalScrollBar().valueChanged.connect(self.updateTimelinePosition)
            self.updateTimelinePosition()
            self.updateTrackPositions()
            QtWidgets.QApplication.processEvents()
            self.trackBackground.setFixedSize(self.trackContainerWidget.width(), self.height())
            self.endLine.setX(self.structure.endMarker.time * BeatHUnit)

    def updateTrackPositions(self):
        y = self.mapFromScene(QtCore.QPoint(0, 0)).y()
        self.trackContainerWidget.move(0, y + self.timelineHeight)
        height = self.viewport().height()
        mask = QtGui.QBitmap(self.trackWidth, max(self.trackContainerWidget.height(), height))
        mask.clear()
        qp = QtGui.QPainter(mask)
        qp.setBrush(QtCore.Qt.black)
        qp.drawRect(0, -y, self.trackWidth, height)
        qp.end()
        self.trackContainerWidget.setMask(mask)

    def updateTimelinePosition(self):
        x = self.mapFromScene(QtCore.QPoint(0, 0)).x()
        self.timelineWidget.move(x + self.trackWidth, 0)
        width = self.viewport().width()
        mask = QtGui.QBitmap(max(self.timelineWidget.width(), width), self.timelineHeight)
        mask.clear()
        qp = QtGui.QPainter(mask)
        qp.setBrush(QtCore.Qt.black)
        qp.drawRect(-x, 0, width, self.timelineHeight)
        qp.end()
        self.timelineWidget.setMask(mask)

    def resizeEvent(self, event):
        QtWidgets.QGraphicsView.resizeEvent(self, event)
        self.updateTimelinePosition()
        self.updateTrackPositions()
        self.trackBackground.setFixedSize(self.trackContainerWidget.width(), self.height())
#        self.setSceneRect(QtCore.QRectF(self.viewport().rect()))

