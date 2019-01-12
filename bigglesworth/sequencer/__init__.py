#!/usr/bin/env python2.7

import sys, os

os.environ['QT_PREFERRED_BINDING'] = 'PyQt4'

from Qt import QtCore, QtGui, QtWidgets
from PyQt4.QtGui import QStyleOptionFrameV3
QtWidgets.QStyleOptionFrameV3 = QStyleOptionFrameV3

if __name__ == '__main__':
#    sys.path.append('..')
    sys.path.append('../..')

from bigglesworth.utils import loadUi
from bigglesworth.midiutils import NOTEON, NOTEOFF, CTRL, SYSEX, MidiEvent
from bigglesworth.sequencer.const import SnapModes, SnapModeRole, DefaultPatternSnapModeId
from bigglesworth.sequencer.dialogs import RepetitionsDialog


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

    def midiEvents(self, start=0, end=None):
        if isinstance(self.parent(), SequencerWindow):
            return self.parent().structure.midiEvents(start, end)
        return self.parent().pattern.midiEvents(start, end)

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

    def clearLoop(self):
        if self.status == self.Playing and self.buffers and self.isLooping:
            self.isLooping = False
#            if loop:
#                self.buffers[-1].destroyed.disconnect()
#                self.buffers[-1].destroyed.connect(lambda: self.playFrom(self.currentStart, self.currentEnd, loop))
#                self.buffers[-1].destroyed.connect(lambda: self.restarted.emit(self.structure.secsFromTime(self.currentStart)))
            self.buffers[-1].destroyed.disconnect()
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

    def playFrom(self, start=None, end=None, loop=False):
        if start is None:
            start = self.currentStart
        self.clearBuffers()
#        bufferLength = structure.tempos[0]
        bufferLength = 2000.
        midiEvents = self.midiEvents(start, end)
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


class SequencerWindow(QtWidgets.QMainWindow):
    midiEvent = QtCore.pyqtSignal(object)

    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        loadUi('ui/sequencer.ui', self)
        self.sequencerScene = self.sequencerView.scene()
        self.sequencerView.repeatDialogRequested.connect(self.showRepeatDialog)
        self.structure = self.sequencerView.structure

        self.mainToolBar.addSeparator()
        self.mainToolBar.addWidget(QtWidgets.QLabel('Snap'))
        self.snapCombo = QtWidgets.QComboBox()
        self.mainToolBar.addWidget(self.snapCombo)
        for index, snapMode in enumerate(SnapModes):
            self.snapCombo.addItem(snapMode.icon, snapMode.label)
            self.snapCombo.setItemData(index, snapMode, SnapModeRole)
        self.snapCombo.setCurrentIndex(DefaultPatternSnapModeId)
        self.snapCombo.currentIndexChanged.connect(self.setBeatSnap)

        self.playIcons = QtGui.QIcon.fromTheme('media-playback-start'), QtGui.QIcon.fromTheme('media-playback-pause')

        self.player = Player(self)
        self.player.restarted.connect(self.sequencerView.playAnimation.setCurrentTime)
        self.playAction.triggered.connect(self.togglePlay)
        self.stopAction.triggered.connect(self.stop)
        self.loopAction.triggered.connect(self.setLoop)
        self.rewindAction.triggered.connect(self.rewind)
        self.player.statusChanged.connect(self.statusChanged)
        if __name__ == '__main__':
            self.midiDevice = TestMidiDevice(self)
            self.midiThread = QtCore.QThread()
            self.midiDevice.moveToThread(self.midiThread)
            self.midiThread.started.connect(self.midiDevice.start)
            self.midiThread.start()
            self.player.midiEvent.connect(self.midiEvent)
        else:
            self.midiDevice = QtWidgets.QApplication.instance().midiDevice

        self.addTracksAction.triggered.connect(self.sequencerView.addTracks)

    @property
    def playheadTime(self):
        return self.sequencerView.playheadTime

    def togglePlay(self, state):
        if state:
            time = self.structure.secsFromTime(self.playheadTime)
            if self.player.playFrom(self.playheadTime):
                self.sequencerView.playAnimation.setCurrentTime(time)
            elif time:
                self.sequencerView.setPlayheadTime(0)
                self.togglePlay(state)
        else:
            self.player.stop()
            self.loopAction.blockSignals(True)
            self.loopAction.setChecked(False)
            self.loopAction.blockSignals(False)

    def setLoop(self, loop):
        if loop:
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
            self.player.playFrom(start, end, loop)
            self.loopAction.blockSignals(True)
            self.loopAction.setChecked(True)
            self.loopAction.blockSignals(False)
        else:
            self.player.clearLoop()

    def stop(self):
        time = self.playheadTime
        prevStatus = self.player.status
        self.player.stop()
        if time and prevStatus == self.player.Stopped:
            self.sequencerView.setPlayheadTime(0)

    def rewind(self):
        restart = self.player.status == self.player.Playing
        self.player.stop()
        self.statusChanged(False)
        self.sequencerView.setPlayheadTime(0)
        if restart:
            QtCore.QTimer.singleShot(0, self.player.play)

    def statusChanged(self, state):
        self.playAction.setChecked(state)
        self.playAction.setIcon(self.playIcons[bool(state)])
        self.sequencerView.togglePlay(state)
        if not state:
            self.loopAction.blockSignals(True)
            self.loopAction.setChecked(False)
            self.loopAction.blockSignals(False)

    def setBeatSnap(self, index):
        self.sequencerView.setBeatSnapMode(self.snapCombo.itemData(index, SnapModeRole))

    def showRepeatDialog(self, pattern):
        pattern.setRepetitions(RepetitionsDialog(self, pattern.repetitions).exec_())

    def showEvent(self, event):
        self.sequencerView.verticalScrollBar().setValue(0)
        self.sequencerView.horizontalScrollBar().setValue(0)



if __name__ == '__main__':
    if 'linux' in sys.platform:
        from mididings import run, config, Filter, Call, SYSEX as mdSYSEX
        from mididings.engine import output_event as outputEvent
        from mididings.event import (NoteOnEvent as mdNoteOnEvent, 
            NoteOffEvent as mdNoteOffEvent, CtrlEvent as mdCtrlEvent)

    app = QtWidgets.QApplication(sys.argv)
    app.setOrganizationName('jidesk')
    app.setApplicationName('Bigglesworth')
    s = SequencerWindow()
    s.show()
    sys.exit(app.exec_())

