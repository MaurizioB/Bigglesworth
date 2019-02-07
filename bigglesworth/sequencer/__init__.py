#!/usr/bin/env python2.7

import sys, os
from math import modf
from bisect import bisect_left
from xml.etree import ElementTree as ET
from uuid import uuid4
import numpy as np

os.environ['QT_PREFERRED_BINDING'] = 'PyQt4'

from Qt import QtCore, QtGui, QtSql, QtWidgets
from PyQt4.QtGui import QStyleOptionFrameV3
QtWidgets.QStyleOptionFrameV3 = QStyleOptionFrameV3

if __name__ == '__main__':
#    sys.path.append('..')
    sys.path.append('../..')

from bigglesworth.utils import loadUi
from bigglesworth.midiutils import NOTEON, NOTEOFF, CTRL, SYSEX, MidiEvent, IDW, IDE, SNDP
from bigglesworth.sequencer.const import (SnapModes, SnapModeRole, DefaultPatternSnapModeId, BLOFELD, BeatHUnit, 
    UidColumn, DataColumn, TitleColumn, TracksColumn, EditedColumn, CreatedColumn, BlofeldParameter, CtrlParameter)
from bigglesworth.sequencer.dialogs import RepetitionsDialog, SongBrowser, InputTextDialog, BlofeldIdDialog, MidiImportProgressDialog
from bigglesworth.sequencer.structure import NoteOnEvent, NoteOffEvent, CtrlEvent, LoopStartMarker, LoopEndMarker
from bigglesworth.dialogs import SongExportDialog, SongImportDialog
from bigglesworth.libs import midifile


event2MidiFileClasses = {
    NoteOnEvent: midifile.NoteOnEvent, 
    NoteOffEvent: midifile.NoteOffEvent, 
    CtrlEvent: midifile.ControlChangeEvent, 
}
midiEvent2EventClasses = {v:k for k, v in event2MidiFileClasses.items()}

#def event2MidiFile(event):
#    midiEvent = event.midiEvent
#    if event.eventType == NoteOnEvent:
#        return midifile.NoteOnEvent(channel=midiEvent.channel, pitch=midiEvent.data1, velocity=midiEvent.velocity)
#    elif event.eventType == NoteOffEvent:
#        return midifile.NoteOffEvent(channel=midiEvent.channel, pitch=midiEvent.data1, velocity=midiEvent.velocity)
#    return midifile.ControlChangeEvent(channel=midiEvent.channel, control=midiEvent.data1, value=midiEvent.velocity)


class FakeBlofeldDB(QtCore.QObject):
    def __init__(self):
        QtCore.QObject.__init__(self)
        db = QtSql.QSqlDatabase.database()
        self.updateQuery = QtSql.QSqlQuery()
        if not 'songs' in db.tables():
            if not self.updateQuery.exec_('CREATE TABLE songs (uid varchar, data blob)'):
                print(self.updateQuery.lastError().driverText(), self.updateQuery.lastError().databaseText())


class SongModel(QtSql.QSqlTableModel):
    def __init__(self):
        QtSql.QSqlTableModel.__init__(self)
        self.updateQuery = QtSql.QSqlQuery()
        if not 'songs' in self.database().tables():
            if not self.updateQuery.exec_('CREATE TABLE songs (uid varchar, data blob)'):
                print(self.updateQuery.lastError().driverText(), self.updateQuery.lastError().databaseText())
        self.setTable('songs')
        self.select()

    def setData(self, *args, **kwargs):
        assert QtSql.QSqlTableModel.setData(self, *args, **kwargs)
        res = self.submitAll()
        print('salvato')
        return res

class SongProxyModel(QtCore.QIdentityProxyModel):
    headers = {
        TitleColumn: 'Title', 
        TracksColumn: 'Tracks', 
        EditedColumn: 'Edited', 
        CreatedColumn: 'Created', 
    }
    dataChangedSignal = QtCore.pyqtSignal(QtCore.QModelIndex)

    def __init__(self):
        QtCore.QIdentityProxyModel.__init__(self)
        self.setSourceModel(SongModel())

    def columnCount(self, parent=None):
        return 6

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            try:
                return self.headers[section]
            except:
                pass
        return QtCore.QIdentityProxyModel.headerData(self, section, orientation, role)

    def index(self, row, column, parent=QtCore.QModelIndex()):
        if column >= TitleColumn:
            return self.createIndex(row, column)
        return QtCore.QIdentityProxyModel.index(self, row, column, parent)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if index.column() >= TitleColumn and role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):
            try:
                root = ET.fromstring(self.sourceModel().index(index.row(), DataColumn).data(role))
                songElement = root.find('SequencerSong')
                column = index.column()
                if column == TitleColumn:
                    return songElement.get('title')
                elif column == TracksColumn:
                    return str(len(songElement.findall('Track')))
                elif column == EditedColumn:
                    return QtCore.QDateTime.fromMSecsSinceEpoch(int(songElement.get('edited')))
                elif column == CreatedColumn:
                    return QtCore.QDateTime.fromMSecsSinceEpoch(int(songElement.get('created')))
            except Exception as e:
                print('Not able to read data', e)
        if index.column() == TracksColumn and role == QtCore.Qt.TextAlignmentRole:
            return QtCore.Qt.AlignCenter
        return QtCore.QIdentityProxyModel.data(self, index, role)

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        if index.column() == TitleColumn and role == QtCore.Qt.EditRole:
            try:
                root = ET.fromstring(self.sourceModel().index(index.row(), DataColumn).data(role))
                root.find('SequencerSong').set('title', value)
                try:
                    return QtCore.QIdentityProxyModel.setData(self, 
                        index.sibling(index.row(), DataColumn), 
                        unicode(ET.tostring(root, encoding='utf-8').decode('utf-8')), 
                        role)
                finally:
                    self.dataChangedSignal.emit(index)
            except Exception as e:
                print('error saving title', e)
        if QtCore.QIdentityProxyModel.setData(self, index, value, role):
            print('salvato')
            return True
        else:
            print('buuuuh')
            return False

    def flags(self, index):
        flags = QtCore.QIdentityProxyModel.flags(self, index)
        flags |= QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
        if index.column() == TitleColumn:
            flags |= QtCore.Qt.ItemIsEditable
        return flags

    def getTitleFromUid(self, uid):
        indexes = self.match(self.index(0, 0), QtCore.Qt.DisplayRole, uid, flags=QtCore.Qt.MatchExactly)
        if indexes:
            return self.data(indexes[0].sibling(indexes[0].row(), TitleColumn), QtCore.Qt.DisplayRole)

    def saveSong(self, uid, data):
        model = self.sourceModel()
        indexes = model.match(model.index(0, 0), QtCore.Qt.DisplayRole, uid, flags=QtCore.Qt.MatchExactly)
        try:
            if not indexes:
                row = model.rowCount()
                assert self.insertRow(row)
            else:
                row = indexes[0].row()
            assert model.setData(model.index(row, UidColumn), uid, QtCore.Qt.EditRole)
            assert model.setData(model.index(row, DataColumn), data, QtCore.Qt.EditRole)
            return True
        except:
            return False


class TestMidiDevice(QtCore.QObject):
    midiEvent = QtCore.pyqtSignal(object)
    def __init__(self, main):
        QtCore.QObject.__init__(self)
        self.main = main
        self.backend = -1
        self.main.midiEvent.connect(self.outputEvent)
        try:
            config(
                client_name='Bigglesworth', 
                in_ports=[('Input', 'Virtual.*',  'Blofeld.*')], 
                out_ports=[('Output', 'Blofeld.*', 'Pianoteq.*', 'aseqdump.*')], 
                data_offset=0)
            self.isValid = True
        except:
            self.isValid = False

    def start(self):
        run(Filter(mdSYSEX) >> Call(self.inputEvent))

    def inputEvent(self, event):
        if event.type == mdSYSEX:
            newEvent = MidiEvent(SYSEX, event.port, map(int, event.sysex))
        else:
            return
        self.midiEvent.emit(newEvent)

    def outputEvent(self, event):
        if self.isValid:
            print(event)
            if event.type == NOTEON:
                event = mdNoteOnEvent(0, event.channel, event.note, event.velocity)
            elif event.type == NOTEOFF:
                event = mdNoteOffEvent(0, event.channel, event.note, event.velocity)
            elif event.type == CTRL:
                event = mdCtrlEvent(0, event.channel, event.data1, event.data2)
            else:
                return
            outputEvent(event)


#def getNoteName(note):
#    octave, note = divmod(note, 12)
#    return '{}{}'.format(NoteNames[note], octave - OctaveOffset)

#noteNames = ['{} ({})'.format(_noteNumberToName[v].upper(), v) for v in range(128)]

class Player(QtCore.QObject):
#    finished = QtCore.pyqtSignal()
    midiEvent = QtCore.pyqtSignal(object)
    blofeldEvent = QtCore.pyqtSignal(object)
    statusChanged = QtCore.pyqtSignal(int)
    restarted = QtCore.pyqtSignal(float)
    Stopped, Paused, Playing = 0, 1, 2

    def __init__(self, parent):
        QtCore.QObject.__init__(self, parent)
        self.buffers = []
        self.timers = []
        self.pendingNotes = set()
        self._status = self.Stopped
        self.currentStart = 0
        self.currentEnd = 0
        self.isLooping = False
        if isinstance(self.parent(), SequencerWindow):
            self.structure = parent.structure
        else:
            self.structure = parent.pattern.structure

    def midiEvents(self, start=0, end=None, pattern=None):
        if pattern is None:
            return self.parent().structure.midiEvents(start, end)
        return self.parent().structure.midiEvents(start, end, pattern)
#        if isinstance(self.parent(), SequencerWindow):
#            return self.parent().structure.midiEvents(start, end)
#        return self.parent().structure.midiEvents(start, end, pattern=self.parent().pattern)
#        return self.parent().pattern.midiEvents(start, end)

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, status):
        if status != self._status:
            self._status = status
            self.statusChanged.emit(status)

    def clearBuffers(self):
        for buffer in self.buffers:
            try:
                buffer.deleteLater()
            except:
                pass
        for timer in self.timers:
            timer.deleteLater()
        self.buffers = []
        self.timers = []

    def createBuffer(self, time, events):
        buffer = MidiBuffer(self, time, events)
        self.buffers.append(buffer)
        timer = QtCore.QTimer()
        timer.setSingleShot(True)
        timer.setInterval(time)
        timer.timeout.connect(buffer.start)
        self.timers.append(timer)

    def play(self):
        self.togglePlay(True)

    def togglePlay(self, state, time=0):
        if state:
            self.playFrom(time)
        else:
            self.stop()

    def clearLoop(self, stop=False):
        if self.status == self.Playing and self.buffers and self.isLooping:
            self.isLooping = False
#            if loop:
#                self.buffers[-1].destroyed.disconnect()
#                self.buffers[-1].destroyed.connect(lambda: self.playFrom(self.currentStart, self.currentEnd, loop))
#                self.buffers[-1].destroyed.connect(lambda: self.restarted.emit(self.structure.secsFromTime(self.currentStart)))
            self.buffers[-1].destroyed.disconnect()
            if not stop:
                self.buffers[-1].destroyed.connect(lambda: self.playFrom(self.currentEnd))
#            self.buffers[-1].destroyed.connect(self.stop)

    def stop(self):
        self.isLooping = False
        try:
            self.buffers[-1].destroyed.disconnect()
        except:
            pass
        for timer in self.timers:
            timer.stop()
        self.clearBuffers()
        self.status = self.Stopped
        while self.pendingNotes:
            note, channel = self.pendingNotes.pop()
            self.midiEvent.emit(MidiEvent(NOTEOFF, 1, channel, note, 0))

    def playFrom(self, start=None, end=None, loop=False, pattern=None):
        if start is None:
            start = self.currentStart
        self.clearBuffers()
#        bufferLength = structure.tempos[0]
        bufferLength = 2000.
        midiEvents = self.midiEvents(start, end, pattern=pattern)
        if not midiEvents:
            self.status = self.Stopped
            self.statusChanged.emit(self.status)
            return False
        currentTime = 0
        currentBuffer = {}
        for time, events in sorted(midiEvents.items()):
            if time < 0:
                continue
            if time - currentTime > bufferLength and currentBuffer:
                self.createBuffer(currentTime, currentBuffer)
                currentBuffer = {}
                currentTime = time
            currentBuffer[time] = events
        if currentBuffer:
            self.createBuffer(currentTime, currentBuffer)
        self.status = self.Playing
        self.restarted.emit(self.structure.secsFromTime(start))
        self.currentStart = start
        self.currentEnd = end
        self.isLooping = loop
        for timer in self.timers:
            timer.start()
        if loop:
            self.buffers[-1].destroyed.connect(lambda: self.playFrom(start, end, loop))
            self.buffers[-1].destroyed.connect(lambda: self.restarted.emit(self.structure.secsFromTime(start)))
        else:
            self.buffers[-1].destroyed.connect(self.stop)
        return True
#        timer.timeout.connect(self.stop)

    def playEvents(self, events):
#        return
        for event in events:
            if event.eventType < 0:
                return
            elif event.eventType == BLOFELD:
                self.blofeldEvent.emit(event)
                print(event.parameter.attr)
            else:
                event = event.midiEvent
                self.midiEvent.emit(event)
                if event.type == NOTEON:
                    self.pendingNotes.add((event.note, event.channel))
                elif event.type == NOTEOFF:
                    self.pendingNotes.discard((event.note, event.channel))


class MidiBuffer(QtCore.QObject):
    def __init__(self, player, time, eventDict):
        QtCore.QObject.__init__(self)
        self.time = time
        self.player = player
#        self.elapsed = QtCore.QElapsedTimer()
#        self.elapsed.start()

        self.timers = []
        for time, events in sorted(eventDict.items()):
            timer = QtCore.QTimer()
            timer.setSingleShot(True)
            timer.setInterval(time - self.time)
            timer.timeout.connect(lambda events=events: self.player.playEvents(events))
            self.timers.append(timer)
        timer.timeout.connect(self.deleteLater)
#        self.timers[0].timeout.connect(self.firstStarted)

#    def firstStarted(self):
#        print('first event!', self.elapsed.elapsed(), self.timers[0].interval())

    def start(self):
        [timer.start() for timer in self.timers]
#        print('started!', self.timers[-1].isActive(), self.timers[-1].interval())

    def deleteLater(self):
        [timer.stop() for timer in self.timers]
        QtCore.QObject.deleteLater(self)



class TimeStampEdit(QtWidgets.QLineEdit):
    def __init__(self, parent):
        QtWidgets.QLineEdit.__init__(self, parent)
        self.barLbl = parent.barLbl
        self.beatLbl = parent.beatLbl
        self.setFrame(False)
        self.currentWidget = None
        self.barValidator = QtGui.QIntValidator(1, 256)
        self.beatValidator = QtGui.QIntValidator(1, 32)
        self.setValidator(self.barValidator)
        self.returnPressed.connect(self.returnCheck)

    def returnCheck(self):
        self.checkoutTimeStamp()
        self.clearFocus()

    def checkoutTimeStamp(self):
        if self.currentWidget:
            valid, text, pos = self.validator().validate(self.text(), 0)
            if valid == QtGui.QValidator.Acceptable:
                if self.currentWidget == self.barLbl:
                    self.parent().timeStampChanged.emit(int(text) - 1, int(self.beatLbl.text()) - 1)
                else:
                    self.parent().timeStampChanged.emit(int(self.barLbl.text()) - 1, int(text) - 1)

    def activate(self, widget=None):
        self.checkoutTimeStamp()
        self.currentWidget = widget if widget is not None else self.barLbl
        self.setValidator(self.barValidator if self.currentWidget == self.barLbl else self.beatValidator)
        self.validator().setTop(256 if self.currentWidget == self.barLbl else 32)
        self.setGeometry(self.currentWidget.geometry().adjusted(-1, 0, 1, 0))
        self.setText(self.currentWidget.text())
        self.setFocus()
        self.selectAll()
        self.show()

#    def getBarBeat(self):
#        valid, bar, pos = self.barValidator.validate(self.barLbl.text(), 0)

    def hide(self):
        self.currentWidget = None
        QtWidgets.QLineEdit.hide(self)


class TimeStampWidget(QtWidgets.QFrame):
    timeStampChanged = QtCore.pyqtSignal(int, int)

    def __init__(self, parent):
        QtWidgets.QFrame.__init__(self, parent)
#        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setFrameStyle(self.StyledPanel|self.Sunken)
        self.structure = parent.structure
        self._bar = 0
        self._beat = 0
        self.setFixedWidth(self.fontMetrics().width('000:00') + self.lineWidth() * 2 + self.fontMetrics().height() * 2)
        self.setMaximumHeight(self.fontMetrics().height() * 2)
        layout = QtWidgets.QHBoxLayout()
        self.setLayout(layout)
        layout.setSpacing(1)
        layout.setContentsMargins(1, 1, 1, 1)
#        self.setContentsMargins(1, 1, 1, 1)

        sizePolicy = QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Preferred
        self.barLbl = QtWidgets.QLabel('001')
        layout.addWidget(self.barLbl)
        self.barLbl.setSizePolicy(*sizePolicy)
        self.barLbl.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter)

        self.divLbl = QtWidgets.QLabel(':')
        layout.addWidget(self.divLbl)
        self.divLbl.setSizePolicy(*sizePolicy)
        self.divLbl.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter)

        self.beatLbl = QtWidgets.QLabel('01')
        layout.addWidget(self.beatLbl)
        self.beatLbl.setSizePolicy(*sizePolicy)
        self.beatLbl.setAlignment(QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)

        self.edit = TimeStampEdit(self)
        self.edit.hide()
        self.edit.installEventFilter(self)
        self.setFocusProxy(self.edit)
        self.activate = self.edit.activate

    @property
    def bar(self):
        return self._bar

    @bar.setter
    def bar(self, bar):
        if bar == self._bar:
            return
        self._bar = bar
        self.barLbl.setText('{:03}'.format(bar + 1))

    @property
    def beat(self):
        return self._beat

    @beat.setter
    def beat(self, beat):
        if beat == self._beat:
            return
        self._beat = beat
        self.beatLbl.setText('{:02}'.format(beat + 1))

    def setTimeStamp(self, bar, beat):
        self.bar = bar
        self.beat = beat

#    def activate(self, widget=None):
#        self.edit.activate(widget)

    def mouseDoubleClickEvent(self, event):
        if event.pos() in self.barLbl.geometry():
            self.activate(self.barLbl)
        elif event.pos() in self.beatLbl.geometry():
            self.activate(self.beatLbl)

#    def _focusInEvent(self, event):
#        self.activate()
#        QtWidgets.QFrame.focusInEvent(self, event)

    def focusOutEvent(self, event):
        self.edit.hide()
        QtWidgets.QFrame.focusOutEvent(self, event)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self.edit.hide()
        else:
            QtWidgets.QFrame.keyPressEvent(self, event)

    def eventFilter(self, source, event):
        if event.type() == QtCore.QEvent.FocusOut:
            self.edit.hide()
        return QtWidgets.QFrame.eventFilter(self, source, event)

    def focusNextPrevChild(self, next):
        if next:
            if self.edit.currentWidget == self.barLbl:
                self.activate(self.beatLbl)
                return True
            elif self.edit.currentWidget == self.beatLbl:
                self.edit.checkoutTimeStamp()
                return False
        else:
            if self.edit.currentWidget == self.beatLbl:
                self.activate(self.barLbl)
                return True
            elif self.edit.currentWidget == self.barLbl:
                self.edit.checkoutTimeStamp()
                return False
        return False


class SequencerWindow(QtWidgets.QMainWindow):
    timeStampChanged = QtCore.pyqtSignal(int, int)
    playheadTimeChanged = QtCore.pyqtSignal(float)
#    midiEvent = QtCore.pyqtSignal(object)
#    blofeldEvent

    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        loadUi('ui/sequencer.ui', self)
        self.sequencerScene = self.sequencerView.scene()
        self.sequencerView.repeatDialogRequested.connect(self.showRepeatDialog)
        self.structure = self.sequencerView.structure
        self.setWindowTitle('Sequencer - {} [*]'.format(self.structure.title))

        self.mainToolBar.addSeparator()
        self.mainToolBar.addWidget(QtWidgets.QLabel('Snap'))
        self.snapCombo = QtWidgets.QComboBox()
        self.mainToolBar.addWidget(self.snapCombo)
        for index, snapMode in enumerate(SnapModes):
            self.snapCombo.addItem(snapMode.icon, snapMode.label)
            self.snapCombo.setItemData(index, snapMode, SnapModeRole)
        self.snapCombo.setCurrentIndex(DefaultPatternSnapModeId)
        self.snapCombo.currentIndexChanged.connect(self.setBeatSnap)
        self.windowState = True
        self.savedWindowState = None
        self.minimizeAction.triggered.connect(self.toggleWindowState)

        self.playIcons = QtGui.QIcon.fromTheme('media-playback-start'), QtGui.QIcon.fromTheme('media-playback-pause')

        self.player = Player(self)
        self.midiEvent = self.player.midiEvent
        self.blofeldEvent = self.player.blofeldEvent
        self.playAction.triggered.connect(self.togglePlay)
        self.stopAction.triggered.connect(self.stop)
        self.loopAction.triggered.connect(self.setLoop)
        self.rewindAction.triggered.connect(self.rewind)
        self.player.statusChanged.connect(self.statusChanged)

        self.main = QtWidgets.QApplication.instance()
        if __name__ == '__main__':
            self.main.blofeldId = 0
            self.midiDevice = TestMidiDevice(self)
            self.midiThread = QtCore.QThread()
            self.midiDevice.moveToThread(self.midiThread)
            self.midiThread.started.connect(self.midiDevice.start)
            self.midiThread.start()
#            self.database = FakeBlofeldDB()
#            self.player.midiEvent.connect(self.midiEvent)
        else:
            self.database = self.main.database
            self.midiDevice = self.main.midiDevice

        self.songModel = SongProxyModel()

        self.timeStampTimer = QtCore.QTimer()
        self.timeStampTimer.setInterval(50)
        self.timeStampTimer.timeout.connect(self.currentTimeChanged)
        self.timeStampWidget = TimeStampWidget(self)
        self.timeStampChanged.connect(self.timeStampWidget.setTimeStamp)
        sep = self.playToolBar.insertSeparator(self.minimizeAction)
        self.playToolBar.insertWidget(sep, self.timeStampWidget)
        self.timeStampWidget.timeStampChanged.connect(self.setTimeStamp)
        self.sequencerView.playheadMoved.connect(self.currentTimeChanged)

        self.newSongAction.triggered.connect(self.newSong)
        self.saveSongAction.triggered.connect(self.saveSong)
        self.openSongAction.triggered.connect(self.openSong)
        self.exportSongAction.triggered.connect(self.exportSong)
        self.importSongAction.triggered.connect(self.importSong)
        self.addTracksAction.triggered.connect(self.sequencerView.addTracks)

        self.playAnimation = QtCore.QSequentialAnimationGroup()
        self.player.restarted.connect(self.playAnimation.setCurrentTime)
        self.structure.timelineChanged.connect(self.setPlayAnimation)
        self._playheadTime = 0
        self.setPlayAnimation()
        self.structure.changed.connect(lambda: self.setWindowModified(True))
        self.structure.titleChanged.connect(lambda title: self.setWindowTitle('Sequencer - {} [*]'.format(title)))

        self.sequencerView.viewport().setStatusTip('Double click to create/edit patterns, Ctrl+click for multi selection, Shift+drag to duplicate; Shift+wheel for horizontal scroll.')

    def activate(self):
        self.show()
        self.activateWindow()

    def newSong(self):
        if self.isWindowModified():
            if QtWidgets.QMessageBox.question(self, 'Create new song', 
                'Do you want to create a new song?<br/>Existing data will be cleared!!!', 
                QtWidgets.QMessageBox.Ok|QtWidgets.QMessageBox.Cancel) != QtWidgets.QMessageBox.Ok:
                    return
#        elif len(self.structure.tracks) == 1 and not self.structure.tracks[0].patterns:
#            return
        self.structure.newSong()
        self.setWindowModified(False)

    def saveSong(self):
        if not self.structure.uid:
            res = InputTextDialog(self, 'Save song', 
                'Type the song name:', 
                self.structure.title).exec_()
            if res is None:
                return
            self.structure.title = res
            self.structure.uid = str(uuid4())
        self.songModel.saveSong(self.structure.uid, self.structure.getSerializedData())
        self.setWindowModified(False)
#        for track in reversed(self.structure.tracks):
#            self.structure.deleteTrack(track)

    def openSong(self):
        res = SongBrowser(self, self.songModel).exec_()
        if res:
            if self.isWindowModified():
                if QtWidgets.QMessageBox.question(self, 'Open song', 
                    '''The current song has been modified. Opening another one will '''
                    '''result in clearing existing data.<br/>Do you want to proceed?''', 
                    QtWidgets.QMessageBox.Ok|QtWidgets.QMessageBox.Cancel) != QtWidgets.QMessageBox.Ok:
                        return
            uid, data = res
            self.structure.uid = uid
            self.structure.setSerializedData(data)
            self.sequencerView.trackContainer.rebuild()
#            self.setWindowModified(False)
            QtCore.QTimer.singleShot(0, lambda: self.setWindowModified(False))
#            QtCore.QTimer.singleShot(0, lambda: self.sequencerView.trackContainer.rebuild())
        elif self.structure.uid:
            title = self.songModel.getTitleFromUid(self.structure.uid)
            if title is None:
                self.setWindowModified(True)
            else:
                self.structure.title = title

    def exportSong(self):
        events = self.structure.midiEvents()
        if len(events) == 1 and events.values()[0][0].eventType == -1:
            return
        filePath = SongExportDialog(self, self.structure.title).exec_()
        if filePath:
            if filePath.endswith('.bws'):
                self.exportToBws(filePath)
            else:
                self.exportToMidi(filePath)

    def exportToBws(self, filePath):
        try:
            with open(filePath, 'w') as f:
                f.write(self.structure.getSerializedData())
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, 'Error exporting song', 
                'There was an error while trying to export the song:<br/><br/>{}'.format(e), 
                QtWidgets.QMessageBox.Ok)

    def exportToMidi(self, filePath):
        resolution = 480
        midiPattern = midifile.Pattern()
        midiPattern.resolution = resolution
        showChildAlert = []
        blofeldEvents = []
        for index, track in enumerate(self.structure.tracks):
            midiTrack = midifile.Track()
            midiPattern.append(midiTrack)

            midiTrack.append(midifile.TrackNameEvent(text=track.label))

            channelPrefixEvent = midifile.ChannelPrefixEvent()
            channelPrefixEvent.data[0] = track.channel
            midiTrack.append(channelPrefixEvent)

            events = []
            for pattern in track.patterns:
                repetitions = pattern.repetitions
                for region in pattern.regions:
                    if region.parameterType != BlofeldParameter:
                        for event in region.patternEvents():
                            eventTime = pattern.time + event._time
                            midiEvent = event2MidiFileClasses[type(event)](
                                channel=event.channel, data=[event.midiEvent.data1, event.midiEvent.data2])
                            for r in range(repetitions):
                                events.append((
                                    eventTime + pattern.time * r, 
                                    midiEvent))
                    else:
                        if region.parameter.parent is not None:
                            showChildAlert.append(region.parameter)
                            continue
                        part = region.parameterId >> 15
                        parHigh, parLow = divmod(region.parameterId >> 4 & 511, 128)
                        for event in region.patternEvents():
                            eventTime = pattern.time + event._time
                            midiEvent = midifile.SysexEvent(
                                #9 is the length of the sysex string
                                data=[9, IDW, IDE, 0, SNDP, part, parHigh, parLow, event.value]
                                )
                            blofeldEvents.append(midiEvent)
                            for r in range(repetitions):
                                events.append((
                                    eventTime + pattern.time * r, 
                                    midiEvent))

            events.sort()
            prevTime = 0
            for time, event in events:
                event.tick = int(round((time - prevTime) * resolution, 1))
                midiTrack.append(event)
                prevTime = time

            if not index:
                midiTrack.make_ticks_abs()

                midiTrack.append(midifile.EndOfTrackEvent(tick=int(self.structure.endMarker.time * resolution)))
                for marker in self.structure.markers:
                    if marker == self.structure.endMarker:
                        continue
                    if isinstance(marker, LoopStartMarker):
                        text = 'Loop start'
                    elif isinstance(marker, LoopEndMarker):
                        text = 'Loop end'
                    else:
                        text = marker.label
                    midiTrack.append(midifile.MarkerEvent(
                        tick=int(marker.time * resolution), 
                        text=text))

                for tempoEvent in self.structure.tempos:
                    midiTrack.append(midifile.SetTempoEvent(
                        tick=int(tempoEvent.time * resolution), 
                        bpm=tempoEvent.tempo))

                for meterEvent in self.structure.meters:
                    midiTrack.append(midifile.TimeSignatureEvent(
                        tick=int(meterEvent.time * resolution), 
                        numerator=meterEvent.numerator, 
                        denominator=meterEvent.denominator, 
                        metronome=24, 
                        thirtyseconds=8, 
                        ))

                #fix for unsorted events in absolute mode
                print(midiTrack)
                midiTrack.sort(key=lambda e: e.tick)
                print(midiTrack)
                midiTrack.make_ticks_rel()
                print(midiTrack)

        if blofeldEvents and not self.main.blofeldId or self.main.blofeldId != 127:
            res = BlofeldIdDialog(self, self.main.blofeldId).exec_()
            if res is not None:
                for event in blofeldEvents:
                    event.data[4] = res

        try:
            midifile.write_midifile(filePath, midiPattern)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, 'Error exporting MIDI file', 
                'There was an error while trying to export the MIDI file:<br/><br/>{}'.format(e), 
                QtWidgets.QMessageBox.Ok)

    def importSong(self):
        filePath = SongImportDialog(self).exec_()
        if filePath:
            if filePath.endswith('.bws'):
                self.importFromBws(filePath)
            else:
                self.importFromMidi(filePath)

    def importFromBws(self, filePath):
        try:
            with open(filePath, 'r') as f:
                self.structure.setSerializedData(f.read())
            self.structure.uid = None
            self.sequencerView.trackContainer.rebuild()
#            QtCore.QTimer.singleShot(0, lambda: self.setWindowModified(False))
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, 'Error importing file', 
                'There was an error while trying to import "{}":<br/><br/>{}'.format(
                    QtCore.QFileInfo(filePath).fileName(), e), 
                QtWidgets.QMessageBox.Ok)

    def importFromMidi(self, filePath):
        try:
            midiPattern = midifile.read_midifile(filePath)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, 'Error importing MIDI file', 
                'There was an error while trying to import "{}":<br/><br/>{}'.format(
                    QtCore.QFileInfo(filePath).fileName(), e), 
                QtWidgets.QMessageBox.Ok)
            return

        progressDialog = MidiImportProgressDialog(self, len(midiPattern))

        self.structure.clearSong()
        tempoEvents = []
        meterEvents = []
        markerEvents = []
        loopStart = loopEnd = None
        endOfTrack = 0

        resolution = float(midiPattern.resolution)
        for index, midiTrack in enumerate(midiPattern):
            progressDialog.setValue(index)
            midiTrack.make_ticks_abs()
            trackName = 'Track {}'.format(index + 1)
            channel = None

            noteData = []
            noteOnEvents = {}
            ctrlEvents = {}
            blofeldEvents = {}

            for midiEvent in midiTrack:
                if isinstance(midiEvent, midifile.TrackNameEvent):
                    trackName = midiEvent.text
                elif isinstance(midiEvent, midifile.ChannelPrefixEvent):
                    channel = midiEvent.data[0]
                else:
                    if isinstance(midiEvent, midifile.NoteOnEvent):
                        try:
                            assert not midiEvent.velocity and midiEvent.pitch in noteOnEvents
                            noteOnData = noteOnEvents[midiEvent.pitch]
                            time = midiEvent.tick / resolution
                            assert noteOnData[0] < time, 'boh'
                            noteData.append((midiEvent.pitch, noteOnData[1], noteOnData[0], time - noteOnData[0], midiEvent.velocity))
                            noteOnEvents.pop(midiEvent.pitch)
                        except:
                            noteOnEvents[midiEvent.pitch] = midiEvent.tick / resolution, midiEvent.velocity
                        if channel is None:
                            channel = midiEvent.channel
                    elif isinstance(midiEvent, midifile.NoteOffEvent):
                        try:
                            noteOnData = noteOnEvents[midiEvent.pitch]
                            time = midiEvent.tick / resolution
                            assert noteOnData[0] < time, 'Wrong NoteOff time?'
                            noteData.append((midiEvent.pitch, noteOnData[1], noteOnData[0], time - noteOnData[0], midiEvent.velocity))
                            noteOnEvents.pop(midiEvent.pitch)
                        except Exception as e:
                            print(e)
                    elif isinstance(midiEvent, midifile.ControlChangeEvent):
                        try:
                            ctrlEvents[midiEvent.control].append((midiEvent.value, midiEvent.tick / resolution))
                        except:
                            ctrlEvents[midiEvent.control] = [(midiEvent.value, midiEvent.tick / resolution)]
                        if channel is None:
                            channel = midiEvent.channel
                    elif isinstance(midiEvent, midifile.SysexEvent) and midiEvent.data[:3] == [9, IDW, IDE]:
                        part = midiEvent.data[5]
                        parameterIndex = midiEvent.data[6] * 128 + midiEvent.data[7]
                        parameterId = (part << 15) + (parameterIndex << 4)
                        try:
                            blofeldEvents[parameterId].append((midiEvent.data[8], midiEvent.tick / resolution))
                        except:
                            blofeldEvents[parameterId] = [(midiEvent.data[8], midiEvent.tick / resolution)]
                    elif isinstance(midiEvent, midifile.MarkerEvent):
                        if midiEvent.text == 'Loop start':
                            loopStart = midiEvent.tick / resolution
                        elif midiEvent.text == 'Loop end':
                            loopEnd = midiEvent.tick / resolution
                        else:
                            markerEvents.append((midiEvent.text, midiEvent.tick / resolution))
                    elif isinstance(midiEvent, midifile.SetTempoEvent):
                        tempoEvents.append(midiEvent)
                    elif isinstance(midiEvent, midifile.TimeSignatureEvent):
                        meterEvents.append(midiEvent)
                    elif isinstance(midiEvent, midifile.EndOfTrackEvent):
                        endOfTrack = max(endOfTrack, midiEvent.tick / resolution)

#            if index == 2:
#                print(noteData)

            track = self.structure.addTrack(channel=channel, label=trackName)
            self.structure.blockSignals(True)

            pattern = track.addPattern()
            lastTime = 0
            for note, velocity, time, length, offVelocity in noteData:
                pattern.noteRegion.addNote(note, velocity, time=time, length=length, offVelocity=offVelocity)
                lastTime = max(lastTime, time + length)
            for ctrl in sorted(ctrlEvents):
                region = pattern.getAutomationRegion(track.addAutomation(CtrlParameter, ctrl))
                for value, time in ctrlEvents[ctrl]:
                    region.addEvent(value=value, time=time)
            for blofeld in sorted(blofeldEvents):
                region = pattern.getAutomationRegion(track.addAutomation(BlofeldParameter, blofeld))
                for value, time in blofeldEvents[blofeld]:
                    region.addEvent(value=value, time=time)
            pattern.length = lastTime
            if index == 2:
                print('lastTime', lastTime)

            self.structure.blockSignals(False)
#            self.structure.changed.emit()

        for meterEvent in meterEvents:
            if not meterEvent.tick:
                self.structure.meters[0].setMeter(meterEvent.numerator, meterEvent.denominator)
            else:
                self.structure.addMeter(meterEvent.numerator, meterEvent.denominator, meterEvent.tick / resolution)

        for tempoEvent in tempoEvents:
            if not tempoEvent.tick:
                self.structure.tempos[0].setTempo(tempoEvent.get_bpm())
            else:
                self.structure.addTempo(tempoEvent.get_bpm(), tempoEvent.tick / resolution)

        if loopStart is not None and loopEnd is not None:
            self.structure.addLoop(loopStart, loopEnd)
        for markerData in markerEvents:
            self.structure.addMarker(*markerData)

        if not endOfTrack:
            endOfTrack = 16
            for track in self.structure.tracks:
                for pattern in track.patterns:
                    endOfTrack = max(16, pattern.time + pattern.length * pattern.repetitions)
        self.structure.endMarker.time = endOfTrack
        self.structure.changed.emit()
        progressDialog.setValue(len(midiPattern))
        self.sequencerView.timelineWidget.setMinimumWidth(max(4000, self.sequencerView.trackContainer.geometry().width()))
        print(self.sequencerView.trackContainer.geometry())

    @QtCore.pyqtProperty(float)
    def playheadTime(self):
        return self._playheadTime

    @playheadTime.setter
    def playheadTime(self, time):
        self._playheadTime = time
        pos = BeatHUnit * time
        self.sequencerView.playhead.setX(pos)
        self.sequencerView.timelineWidget.setPlayheadPos(pos)
        self.sequencerView.ensurePlayheadVisible()
        self.playheadTimeChanged.emit(time)

    def setPlayheadTime(self, time):
        self.playheadTime = time

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

    def setTimeStamp(self, bar, beat):
        time = self.structure.timeFromBarBeat(bar, beat)
        self.setPlayheadTime(time)
        self.currentTimeChanged()

    def currentTimeChanged(self, time=None):
        time = time if time is not None else self.playheadTime
        val = np.interp(time, *self.structure.meterCoords)
        rest, bar = modf(val)
        try:
            meter = self.structure.meters[self.structure.meterTimes.index(time)]
            raise
        except:
            meter = self.structure.meters[max(0, bisect_left(self.structure.meterTimes, time) - 1)]
        #rounding necessary due to 0.999...
        self.timeStampChanged.emit(bar, round(rest / meter.beatRatio, 8))

    def toggleWindowState(self):
        if self.windowState:
            self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
            self.savedWindowState = self.saveGeometry()
            self.sequencerView.hide()
            for toolBar in self.findChildren(QtWidgets.QToolBar):
                if toolBar != self.playToolBar:
                    toolBar.hide()
            self.statusBar().hide()
            self.playToolBar.setMovable(False)
            self.setFixedSize(self.playToolBar.sizeHint())
            self.minimizeAction.setIcon(QtGui.QIcon.fromTheme('zoom-in-large'))
            self.menuBar().hide()
        else:
            self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowStaysOnTopHint)
            self.setMaximumSize(16777215, 16777215)
            self.sequencerView.show()
            for toolBar in self.findChildren(QtWidgets.QToolBar):
                if toolBar != self.playToolBar:
                    toolBar.show()
            self.statusBar().show()
            if self.savedWindowState:
                self.restoreGeometry(self.savedWindowState)
            self.playToolBar.setMovable(True)
            self.minimizeAction.setIcon(QtGui.QIcon.fromTheme('zoom-out-large'))
            self.menuBar().show()
        self.show()
        self.windowState = not self.windowState
#        print(self.minimumSize())

    def togglePlay(self, state, start=None, end=None, pattern=None):
        if state:
            startTime = start if start is not None else self._playheadTime
            time = self.structure.secsFromTime(startTime)
            if self.player.playFrom(startTime, end, pattern=pattern):
                self.playAnimation.start()
                self.playAnimation.setCurrentTime(time)
            elif time:
                self.setPlayheadTime(0)
                self.togglePlay(state)
                self.playAnimation.start()
                print('togglePlay resulted in failing playFrom({})? ({})'.format(self.playheadTime, time))
        else:
            self.player.stop()
            self.loopAction.blockSignals(True)
            self.loopAction.setChecked(False)
            self.loopAction.blockSignals(False)
            self.playAnimation.stop()

    def setLoop(self, loop, start=None, end=None, pattern=None):
        if loop:
            if start is None and end is None:
                if not self.structure.loopStart:
                    start = 0
                    end = self.structure.endMarker.time
                else:
                    start = self.structure.loopStart.time
                    end = self.structure.loopEnd.time
#            if not self.player.status == self.player.Playing:
#                self.sequencerView.playAnimation.setCurrentTime(start)
#                self.player.playFrom(start, end, loop)
#                return
#            else:
            if self.player.status == self.player.Playing:
                self.player.stop()
            self.player.playFrom(start, end, loop, pattern)
            self.loopAction.blockSignals(True)
            self.loopAction.setChecked(True)
            self.loopAction.blockSignals(False)
            self.playAnimation.start()
            self.playAnimation.setCurrentTime(start)
        else:
            self.player.clearLoop()

    def stop(self):
        time = self._playheadTime
        prevStatus = self.player.status
        self.player.stop()
        self.playAnimation.stop()
        if time and prevStatus == self.player.Stopped:
            self.setPlayheadTime(0)
        self.currentTimeChanged()

    def rewind(self):
        restart = self.player.status == self.player.Playing
        self.player.stop()
        self.statusChanged(False)
        self.setPlayheadTime(0)
        if restart:
            QtCore.QTimer.singleShot(0, self.player.play)
        else:
            self.currentTimeChanged()

    def statusChanged(self, state):
        self.playAction.setChecked(state)
        self.playAction.setIcon(self.playIcons[bool(state)])
        if state:
            self.timeStampTimer.start()
        else:
            self.timeStampTimer.stop()
            self.loopAction.blockSignals(True)
            self.loopAction.setChecked(False)
            self.loopAction.blockSignals(False)
            self.playAnimation.stop()

    def setBeatSnap(self, index):
        self.sequencerView.setBeatSnapMode(self.snapCombo.itemData(index, SnapModeRole))

    def showRepeatDialog(self, pattern):
        pattern.setRepetitions(RepetitionsDialog(self, pattern.repetitions).exec_())

    def showEvent(self, event):
        self.sequencerView.verticalScrollBar().setValue(0)
        self.sequencerView.horizontalScrollBar().setValue(0)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Home:
            self.rewind()
            return
        QtWidgets.QMainWindow.keyPressEvent(self, event)


if __name__ == '__main__':
    if 'linux' in sys.platform:
        from mididings import run, config, Filter, Call, SYSEX as mdSYSEX
        from mididings.engine import output_event as outputEvent
        from mididings.event import (NoteOnEvent as mdNoteOnEvent, 
            NoteOffEvent as mdNoteOffEvent, CtrlEvent as mdCtrlEvent)

    app = QtWidgets.QApplication(sys.argv)
    app.setOrganizationName('jidesk')
    app.setApplicationName('Bigglesworth')

    dataPath = QtGui.QDesktopServices.storageLocation(QtGui.QDesktopServices.DataLocation)
    db = QtSql.QSqlDatabase.addDatabase('QSQLITE')
    db.setDatabaseName(dataPath + '/library.sqlite')

    s = SequencerWindow()
    s.show()
    sys.exit(app.exec_())

