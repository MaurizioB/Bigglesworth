#!/usr/bin/env python2.7
# *-* encoding: utf-8 *-*

#from __future__ import print_function
import os, sys
from time import sleep
from Queue import Queue
from string import uppercase
from random import randrange
sys.path.append(os.path.join(os.path.dirname(__file__), 'bigglesworth/editorWidgets'))
os.environ['QT_PREFERRED_BINDING'] = 'PyQt4'

from Qt import QtCore, QtGui, QtWidgets, QtSql
QtCore.pyqtSlot = QtCore.Slot
QtCore.pyqtSignal = QtCore.Signal
QtCore.pyqtProperty = QtCore.Property
from PyQt4.QtGui import QIdentityProxyModel as _QIdentityProxyModel
QtCore.QIdentityProxyModel = _QIdentityProxyModel

import bigglesworth.resources
QtGui.QIcon.setThemeName('Bigglesworth')

from bigglesworth import compatibility

from bigglesworth.logger import Logger
from bigglesworth.editor import EditorWindow
from bigglesworth.database import BlofeldDB
from bigglesworth.widgets import SplashScreen
from bigglesworth.mainwindow import MainWindow
from bigglesworth.themes import ThemeCollection
from bigglesworth.dialogs import (DatabaseCorruptionMessageBox, SettingsDialog, GlobalsDialog, FirmwareDialog, 
    DumpReceiveDialog, DumpSendDialog, WarningMessageBox, SmallDumper, FirstRunWizard, LogWindow, 
    BlofeldDumper, FindDuplicates, SoundImport, SoundExportMulti, SoundListExport, MidiDuplicateDialog, 
    DonateDialog, MidiChartDialog, AboutDialog, UpdateDialog)
from bigglesworth.help import HelpDialog

from bigglesworth.const import INIT, IDE, IDW, CHK, END, SNDD, SNDP, MULD, SNDR, LogInfo, LogWarning, factoryPresets, factoryPresetsNamesDict
from bigglesworth.midiutils import SYSEX, CTRL, NOTEOFF, NOTEON, PROGRAM, SysExEvent, ClockEvent, Port

from bigglesworth.mididevice import MidiDevice

from bigglesworth.wavetables import WaveTableWindow, UidColumn, NameColumn, SlotColumn, DataColumn, EditedColumn

from bigglesworth.welcome import Welcome
from bigglesworth.version import isNewer
from bigglesworth.dialogs.updates import UpdateChecker


class SqlTableModelFix(QtSql.QSqlTableModel):
    def submitAll(self):
        self.modelAboutToBeReset.emit()
        res = QtSql.QSqlTableModel.submitAll(self)
        self.modelReset.emit()
        return res

class SessionWatcher(QtCore.QObject):
    activate = QtCore.pyqtSignal()
    def __init__(self, pid, pidFile):
        QtCore.QObject.__init__(self)
        self.pid = pid
        self.pidFile = pidFile
        self.watcher = QtCore.QFileSystemWatcher([self.pidFile.fileName()])
        self.watcher.fileChanged.connect(self.callback)
        self.waiter = Queue()

    def quit(self):
        self.waiter.put(1)

    def start(self):
        self.waiter.get(True)
        self.watcher.fileChanged.disconnect()
        self.pidFile.remove()

    def callback(self):
        self.pidFile.open(QtCore.QIODevice.ReadWrite|QtCore.QIODevice.Text)
        if self.pidFile.read(100) != self.pid:
            self.activate.emit()
            self.pidFile.seek(0)
            self.pidFile.write(self.pid)
        self.pidFile.close()


class MidiClock(QtCore.QObject):
    pulse = QtCore.pyqtSignal(object)
    beat = QtCore.pyqtSignal()
    stateChanged = QtCore.pyqtSignal(bool)

    def __init__(self):
        QtCore.QObject.__init__(self)
        self.bpm = 120.
        self.pulseTimer = QtCore.QTimer()
        self.pulseTimer.timeout.connect(self.sendPulse)
        self.pulseTimer.setInterval(2500./self.bpm)
        self.queue = Queue()
        self.pulseIndex = 0

    def run(self):
        while True:
            func = self.queue.get(True)
            if not func:
                break
            func()

    def quit(self):
        self.runOnThread(None)

    def isActive(self):
        return self.pulseTimer.isActive()

    def start(self):
        self.pulseIndex = 0
        self.queue.put(self.pulseTimer.start)
        self.queue.put(lambda: self.pulse.emit(ClockEvent(1)))
        self.queue.put(self.beat.emit)
        self.queue.put(lambda: self.stateChanged.emit(True))

    def stop(self):
        self.queue.put((self.pulseTimer.stop))
        self.queue.put(lambda: self.stateChanged.emit(False))

    def setBpm(self, bpm):
        if bpm == self.bpm:
            return
        self.bpm = bpm
        #timing is (60000ms / bpm) / 24ppqn
        self.queue.put(lambda: self.pulseTimer.setInterval(2500. / (self.bpm)))

    def sendPulse(self):
        self.pulseIndex += 1
        self.pulse.emit(ClockEvent(1))
        if self.pulseIndex >= 24:
            self.pulseIndex = 0
            self.beat.emit()


class Bigglesworth(QtWidgets.QApplication):
    progSendToggled = QtCore.pyqtSignal(bool)
    ctrlSendToggled = QtCore.pyqtSignal(bool)
    progReceiveToggled = QtCore.pyqtSignal(bool)
    ctrlReceiveToggled = QtCore.pyqtSignal(bool)
    midiConnChanged = QtCore.pyqtSignal(object, object)
    midiEventSent = QtCore.pyqtSignal(object)

    def __init__(self, argparse, args):
        QtWidgets.QApplication.__init__(self, ['Bigglesworth'] + args)
#        self.setEffectEnabled(QtCore.Qt.UI_AnimateCombo, False)
        self.setOrganizationName('jidesk')
        self.setApplicationName('Bigglesworth')
        if sys.platform == 'darwin':
            style = compatibility.CustomStyle(self)
            self.setStyle(style)

        self.startTimer = QtCore.QElapsedTimer()
        self.startTimer.start()
        self.argparse = argparse
        self._arguments = args

        self.initialized = False
        self.lastActiveWindows = []
        self.lastMidiEvent = None
        self.disconnectionQueue = set()
        self.firstRunWizard = None
        self.firstRunObject = None
        self.globalsBlock = False
        self.dumpBlock = False
        self.dumpBuffer = []
        self.watchedDialogs = []
        self.bankBuffer = None
        self.isCheckingUpdates = False

        self.logger = Logger(self)

        if QtCore.QFile.exists(QtCore.QDir.tempPath()):
            pidPath = QtCore.QDir(QtCore.QDir.tempPath())
        else:
            pidPath = QtCore.QDir(QtGui.QDesktopServices.storageLocation(QtGui.QDesktopServices.DataLocation))
        self.pid = str(self.applicationPid())
        self.pidFile = QtCore.QFile(pidPath.filePath('.Bigglesworth.pid'))
        existing = self.pidFile.exists()
        if existing:
            if QtCore.QFileInfo(self.pidFile).lastModified().secsTo(QtCore.QDateTime.currentDateTime()) < 5:
                print('Recent pid file found, quitting')
                QtCore.QTimer.singleShot(0, self.quit)
                return
        self.pidFile.open(QtCore.QIODevice.WriteOnly|QtCore.QIODevice.Text)
        written = self.pidFile.write(self.pid)
        if written > 0:
            print('pidFile ok! ({})'.format(self.pidFile.fileName()))
            self.logger.append(LogInfo, 'PID file created', self.pidFile.fileName())
        else:
            print('pidFile not written: {} ({})'.format(self.pidFile.errorString(), self.pidFile.fileName()))
            self.logger.append(LogWarning, 'PID file not created', self.pidFile.fileName())
        self.pidFile.close()
        if existing:
            print('Existing pid file found, waiting...')
            sleep(2)
            self.pidFile.open(QtCore.QIODevice.ReadOnly|QtCore.QIODevice.Text)
            newPid = self.pidFile.read(100)
            self.pidFile.close()
            if newPid != self.pid:
                print('Bigglesworth is already running, quitting')
                QtCore.QTimer.singleShot(0, self.quit)
                return
        self.watcher = SessionWatcher(self.pid, self.pidFile)
        self.watcherThread = QtCore.QThread()
        self.watcher.moveToThread(self.watcherThread)
        self.watcherThread.started.connect(self.watcher.start)
        self.watcher.activate.connect(lambda: self.logger.append(LogInfo, 'Attempt to start another session catched'))
        self.watcher.activate.connect(self.activateTopMost)

        self.splash = SplashScreen()
        self.splash.start()

        self.logger.append(LogInfo, 'Physical DPI: {}x{}'.format(self.splash.physicalDpiX(), self.splash.physicalDpiY()))
        self.logger.append(LogInfo, 'Logical DPI: {}x{}'.format(self.splash.logicalDpiX(), self.splash.logicalDpiY()))

        QtGui.QFontDatabase.addApplicationFont(':/fonts/DroidSansFallback.ttf')
        QtGui.QFontDatabase.addApplicationFont(':/fonts/FiraSans-Regular.ttf')
        QtGui.QFontDatabase.addApplicationFont(':/fonts/OPTIAlpine_Bold.otf')

        logo = QtGui.QIcon(':/images/bigglesworth_logo_whitebg.svg')
        self.setWindowIcon(logo)

        self.settings = QtCore.QSettings()
        self.settings.beginGroup('MIDI')
        rtmidi = self.settings.value('rtmidi', 0 if 'linux' in sys.platform else 1, int)
        if self.argparse.rtmidi:
            rtmidi = self.argparse.rtmidi
        self.backend = True if rtmidi else False
        self._blofeldId = self.settings.value('blofeldId', 0x7f, int)
        self._progReceiveState = self.settings.value('progReceive', True, bool)
        self._ctrlReceiveState = self.settings.value('ctrlReceive', True, bool)
        self._progSendState = self.settings.value('progSend', True, bool)
        self._ctrlSendState = self.settings.value('ctrlSend', True, bool)
        try:
            self._chanReceive = self.settings.value('chanReceive', set(range(16)), set)
        except:
            self._chanReceive = set(range(16))
            self.settings.setValue('chanReceive', self._chanReceive)
        try:
            self._chanSend = self.settings.value('chanSend', set((0, )), set)
        except:
            self._chanSend = set((0, ))
            self.settings.setValue('chanSend', self._chanSend)
        self.settings.endGroup()
        self._sendLibraryProgChange = self.settings.value('SendLibraryProgChange', False, bool)

        self.lastWindowClosed.connect(self.checkWelcomeOnClose)
        self.aboutToQuit.connect(self.closeSession)

    def closeSession(self):
        if sys.platform == 'darwin':
            self.mainWindow.saveLayout()
        #maybe not necessary?
        try:
            self.watcher.quit()
        except:
            pass
        self.pidFile.remove()

    def activateTopMost(self):
        try:
            for window in reversed(self.lastActiveWindows):
                if window.isVisible():
                    window.activateWindow()
                    break
            else:
                self.mainWindow.activate()
        except:
            pass

    def startUp(self):
        self.loggerWindow = LogWindow(self)
        if self.argparse.log:
            self.loggerWindow.show()
        self.splash.showMessage('Loading database engine', QtCore.Qt.AlignLeft|QtCore.Qt.AlignBottom, .2)

        self.database = BlofeldDB()
        if not self.database.initialize(self.argparse.database):
            if self.database.lastError & self.database.EmptyMask:
                self.database.factoryStatus.connect(self.updateSplashFactory)
                self.database.wavetableStatus.connect(self.updateSplashWavetables)
#                self.splash.showMessage('Creating factory database, this could take a while...', QtCore.Qt.AlignLeft|QtCore.Qt.AlignBottom, .25)
                self.database.initializeFactory(self.database.lastError)
            elif self.database.lastError & self.database.DatabaseFormatError:
                print(self.database.lastError)
                if not self.database.checkTables(True) and self.database.lastError & self.database.EmptyMask:
                    DatabaseCorruptionMessageBox(self.splash, str(self.database.lastError)).exec_()
                    self.splash.showMessage('Correcting factory database', QtCore.Qt.AlignLeft|QtCore.Qt.AlignBottom, .4)
                    self.database.initializeFactory(self.database.lastError)
                else:
                    print('porcozzio', self.database.lastError)
            else:
                print(self.database.lastError)
        self.tagsModel = self.database.tagsModel

        try:
            WaveTableWindow.waveTableModel = QtSql.QSqlTableModel()
            WaveTableWindow.waveTableModel.setTable('wavetables')
            WaveTableWindow.waveTableModel.select()
            WaveTableWindow.waveTableModel.setHeaderData(UidColumn, QtCore.Qt.Horizontal, 'D')
            WaveTableWindow.waveTableModel.setHeaderData(NameColumn, QtCore.Qt.Horizontal, 'Name')
            WaveTableWindow.waveTableModel.setHeaderData(SlotColumn, QtCore.Qt.Horizontal, 'Slot')
            WaveTableWindow.waveTableModel.setHeaderData(DataColumn, QtCore.Qt.Horizontal, 'Waves')
            WaveTableWindow.waveTableModel.setHeaderData(EditedColumn, QtCore.Qt.Horizontal, 'Last modified')

            WaveTableWindow.dumpModel = SqlTableModelFix()
            WaveTableWindow.dumpModel.setTable('dumpedwt')
            WaveTableWindow.dumpModel.select()
            WaveTableWindow.dumpModel.setHeaderData(UidColumn, QtCore.Qt.Horizontal, 'D')
            WaveTableWindow.dumpModel.setHeaderData(NameColumn, QtCore.Qt.Horizontal, 'Name')
            WaveTableWindow.dumpModel.setHeaderData(EditedColumn, QtCore.Qt.Horizontal, 'Last modified')
            EditorWindow.oscShapeModel = WaveTableWindow.dumpModel
        except Exception as e:
            print('init', e)

        self.splash.showMessage('Starting MIDI engine', QtCore.Qt.AlignLeft|QtCore.Qt.AlignBottom, .5)

        self.midiDevice = MidiDevice(self, mode=self.backend)
        self.graph = self.midiDevice.graph
        self.midiThread = QtCore.QThread()
        self.midiDevice.moveToThread(self.midiThread)
        self.midiDevice.stopped.connect(self.midiThread.quit)
        self.midiThread.started.connect(self.midiDevice.run)

        self.midiDuplicateDialog = MidiDuplicateDialog(self)
        self.midiDuplicateDialog.midiWidget.midiConnect.connect(self.midiConnect)

        self.seq = self.midiDevice.seq
        self.input = self.midiDevice.input
        self.output = self.midiDevice.output
#        self.connections = [0, 0]
        self.midi_duplex_state = False
        self.midiThread.start()

        self.blockForwardPorts = set()
        self.allowForwardPorts = set()

        self.settings.beginGroup('MIDI')
        blofeldDetect = self.settings.value('blofeldDetect', True, bool)
        autoConnect = self.settings.value('tryAutoConnect', True, bool)
        autoConnectInput = set(self.settings.value('autoConnectInput', [], 'QStringList'))
        autoConnectOutput = set(self.settings.value('autoConnectOutput', [], 'QStringList'))
        self.settings.endGroup()
        if blofeldDetect or autoConnect:
            if blofeldDetect or autoConnectInput or autoConnectOutput:
                for client, port_dict in self.graph.port_id_dict.items():
                    for port in port_dict.values():
                        #blofeld detect
                        if blofeldDetect:
                            if self.midiDevice.backend == MidiDevice.Alsa and \
                                port.client.name == 'Blofeld' and \
                                port.name.startswith('Blofeld MIDI ') and \
                                port.name.split()[-1].isdigit():
                                    port.connect(self.input)
                                    self.output.connect(port)
                                    continue
                            elif port.client.name.startswith('Waldorf Blofeld ') or \
                                port.client.name.startswith('Blofeld:Blofeld MIDI ') or \
                                (port.client.name.startswith('Blofeld - Blofeld MIDI') and port.name.split()[-1].isdigit()):
                                    if port.is_input:
                                        self.output.connect(port)
                                    else:
                                        port.connect(self.input)

                        #other ports
                        portName = u'{}:{}'.format(port.client.name, port.name)
                        if port.is_input and portName in autoConnectOutput:
                            self.midiConnect(port, True, True)
                        if port.is_output and portName in autoConnectInput:
                            self.midiConnect(port, False, True)

        self.updateForwardRules()

        self.midiClock = MidiClock()
        self.midiClockThread = QtCore.QThread()
        self.midiClock.moveToThread(self.midiClockThread)
        self.midiClock.pulse.connect(self.sendMidiEvent)
        self.midiClockThread.started.connect(self.midiClock.run)
        self.midiClockThread.start()

        self.graph.port_start.connect(self.newAlsaPort)
        self.graph.conn_register.connect(self.midiConnEvent)

        self.splash.showMessage('Preparing interface', QtCore.Qt.AlignLeft|QtCore.Qt.AlignBottom, .7)

        self.themes = ThemeCollection(self)

        self.mainWindow = MainWindow(self)
        self.mainWindow.closed.connect(self.checkClose)
        self.mainWindow.quitAction.triggered.connect(self.quit)
        self.mainWindow.midiConnect.connect(self.midiConnect)

        self.mainWindow.leftTabWidget.fullDumpBlofeldToCollectionRequested.connect(self.fullDumpBlofeldToCollection)
        self.mainWindow.leftTabWidget.fullDumpCollectionToBlofeldRequested.connect(self.fullDumpCollectionToBlofeld)
        self.mainWindow.rightTabWidget.fullDumpBlofeldToCollectionRequested.connect(self.fullDumpBlofeldToCollection)
        self.mainWindow.rightTabWidget.fullDumpCollectionToBlofeldRequested.connect(self.fullDumpCollectionToBlofeld)
        self.mainWindow.leftTabWidget.exportRequested.connect(lambda uidList, collection: SoundExportMulti(self.mainWindow, uidList, collection).exec_())
        self.mainWindow.leftTabWidget.exportListRequested.connect(lambda collection: SoundListExport(self.mainWindow, collection).exec_())
        self.mainWindow.rightTabWidget.exportRequested.connect(lambda uidList, collection: SoundExportMulti(self.mainWindow, uidList, collection).exec_())
        self.mainWindow.rightTabWidget.exportListRequested.connect(lambda collection: SoundListExport(self.mainWindow, collection).exec_())
        self.mainWindow.importRequested.connect(self.importRequested)
        self.mainWindow.exportRequested.connect(lambda uidList, collection: SoundExportMulti(self.mainWindow, uidList, collection).exec_())
        self.mainWindow.dumpToRequested.connect(self.dumpTo)
        self.mainWindow.dumpFromRequested.connect(self.dumpFrom)

        self.duplicatesDialog = FindDuplicates(self.mainWindow)
        self.duplicatesDialog.duplicateSelected.connect(self.showSoundInLibrary)
        self.mainWindow.duplicatesAction.triggered.connect(self.duplicatesDialog.launch)
        self.mainWindow.leftTabWidget.findDuplicatesRequested.connect(self.duplicatesDialog.launch)
        self.mainWindow.rightTabWidget.findDuplicatesRequested.connect(self.duplicatesDialog.launch)
        self.mainWindow.findDuplicatesRequested.connect(self.duplicatesDialog.launch)

        self.editorWindow = EditorWindow(self)
        self.database.soundNameChanged.connect(self.editorWindow.nameChangedFromDatabase)
        self.editorWindow.soundNameChanged.connect(self.refreshCollections)
        self.editorWindow.closed.connect(self.checkClose)
        self.editorWindow.importRequested.connect(self.importRequested)
        self.editorWindow.openLibrarianRequested.connect(self.mainWindow.activate)
        self.editorWindow.midiEvent.connect(self.sendMidiEvent)
        self.editorWindow.midiEvent[object, bool].connect(self.sendMidiEvent)
        self.editorWindow.midiConnect.connect(self.midiConnect)
        self.editorWindow.dumpFromRequested.connect(self.dumpFrom)
        self.editorWindow.dumpToRequested.connect(self.dumpTo)
        self.mainWindow.soundEditRequested.connect(self.editorWindow.openSoundFromUid)
#        self.editorWindow.midiInWidget.setConnections(len([conn for conn in self.midiDevice.input.connections.input if not conn.hidden]))
#        self.editorWindow.midiOutWidget.setConnections(len([conn for conn in self.midiDevice.output.connections.output if not conn.hidden]))

        self.splash.showMessage('Applying preferences', QtCore.Qt.AlignLeft|QtCore.Qt.AlignBottom, 1)

        self.settingsDialog = SettingsDialog(self, self.mainWindow)
        self.settingsDialog.midiEvent.connect(self.sendMidiEvent)
#        self.settingsDialog.midiConnectionsWidget.setMain(self)
        self.settingsDialog.midiConnectionsWidget.midiConnect.connect(self.midiConnect)
        self.settingsDialog.themeChanged.connect(self.editorWindow.setTheme)
        self.editorWindow.setTheme(self.themes.current)
#        self.mainWindow.setPalette(self.themes.current.palette)

        self.globalsDialog = GlobalsDialog(self.mainWindow)
        self.globalsDialog.midiEvent.connect(self.sendMidiEvent)
        self.globalsDialog.helpRequested.connect(self.showHelp)

        self.firmwareDialog = FirmwareDialog(self.mainWindow)
        self.firmwareDialog.midiEvent.connect(self.sendMidiEvent)

        self.dumpReceiveDialog = DumpReceiveDialog(self, self.mainWindow)
        self.dumpReceiveDialog.midiEvent.connect(self.sendMidiEvent)
        self.dumpSendDialog = DumpSendDialog(self, self.mainWindow)
        self.dumpSendDialog.midiEvent.connect(self.sendMidiEvent)
        self.mainDumper = SmallDumper(self.mainWindow)
        self.mainDumper.accepted.connect(lambda: setattr(self, 'dumpBlock', False))
        self.editorDumper = SmallDumper(self.editorWindow)
        self.editorDumper.accepted.connect(lambda: setattr(self, 'dumpBlock', False))
#        self.mainDumper.rejected.connect(lambda: setattr(self, 'dumpBlock', False))

        self.lastAboutEgg = randrange(2)

        self.welcome = Welcome(self)
        self.welcome.showLibrarian.connect(self.mainWindow.activate)
        self.welcome.showEditor.connect(self.editorWindow.activate)
        self.welcome.showWavetables.connect(self.showWavetables)
        self.welcome.showUtils.connect(self.showFirmwareUtils)
        self.welcome.showSettings.connect(self.showSettings)
        self.welcome.showDonation.connect(self.showDonation)
        self.welcome.destroyed.connect(self.quit)

        self.helpDialog = HelpDialog()

        self.splash.showMessage('Prepare for some coolness! ;-)', QtCore.Qt.AlignLeft|QtCore.Qt.AlignBottom)

        self.midiDevice.midi_event.connect(self.midiEventReceived)
        self.initialized = True
        QtCore.QTimer.singleShot(200, self.loadingComplete)

    @property
    def blofeldId(self):
        return self._blofeldId

    @blofeldId.setter
    def blofeldId(self, id):
        self._blofeldId = id
        self.settings.beginGroup('MIDI')
        self.settings.setValue('blofeldId', id)
        self.settings.endGroup()

    @property
    def progReceiveState(self):
        return self._progReceiveState

    @progReceiveState.setter
    def progReceiveState(self, state):
        self.progReceiveToggled.emit(state)
        self._progReceiveState = state
        self.settings.beginGroup('MIDI')
        if self.settings.value('RememberMidiReceive', True, bool):
            self.settings.setValue('progReceive', state)
        self.settings.endGroup()

    @property
    def progSendState(self):
        return self._progSendState

    @progSendState.setter
    def progSendState(self, state):
        self.progSendToggled.emit(state)
        self._progSendState = state
        self.settings.beginGroup('MIDI')
        if self.settings.value('RememberMidiSend', True, bool):
            self.settings.setValue('progSend', state)
        self.settings.endGroup()

    @property
    def ctrlReceiveState(self):
        return self._ctrlReceiveState

    @ctrlReceiveState.setter
    def ctrlReceiveState(self, state):
        self.ctrlReceiveToggled.emit(state)
        self._ctrlReceiveState = state
        self.settings.beginGroup('MIDI')
        if self.settings.value('RememberMidiReceive', True, bool):
            self.settings.setValue('ctrlReceive', state)
        self.settings.endGroup()

    @property
    def ctrlSendState(self):
        return self._ctrlSendState

    @ctrlSendState.setter
    def ctrlSendState(self, state):
        self.ctrlSendToggled.emit(state)
        self._ctrlSendState = state
        self.settings.beginGroup('MIDI')
        if self.settings.value('RememberMidiSend', True, bool):
            self.settings.setValue('ctrlSend', state)
        self.settings.endGroup()

    @property
    def chanReceive(self):
        return self._chanReceive

    @chanReceive.setter
    def chanReceive(self, channels):
        self._chanReceive = set(channels)
        self.settings.beginGroup('MIDI')
        self.settings.setValue('chanReceive', channels)
        self.settings.endGroup()

    @property
    def chanSend(self):
        return self._chanSend

    @chanSend.setter
    def chanSend(self, channels):
        self._chanSend = set(channels)
        self.settings.beginGroup('MIDI')
        self.settings.setValue('chanSend', channels)
        self.settings.endGroup()

    @property
    def sendLibraryProgChange(self):
        return self._sendLibraryProgChange

    @sendLibraryProgChange.setter
    def sendLibraryProgChange(self, state):
        self._sendLibraryProgChange = state

    def updateForwardRules(self):
        self.settings.beginGroup('MIDI')
        block = set(self.settings.value('blockForwardPorts', [], 'QStringList'))
        allow = set(self.settings.value('allowForwardPorts', [], 'QStringList'))
        self.settings.endGroup()
        ports = {}
        for conn in self.midiDevice.input.connections.input:
            if conn.hidden:
                continue
            portName = conn.src.toString()
#            if 'blofeld' in portName.lower():
#                block.add(portName)
            ports[portName] = conn.src.addr
        for port in allow:
            block.discard(port)
        self.blockForwardPorts = set(addr for name, addr in ports.items() if name in block)
        self.allowForwardPorts = set(addr for name, addr in ports.items() if name in allow)
        self.blofeldPorts = allow

    def allowPortForward(self, port):
        if isinstance(port, Port):
            addr = port.addr
        else:
            addr = port
            port = self.graph.port_id_dict[port.client.id][port.id]
        self.settings.beginGroup('MIDI')
        block = set(self.settings.value('blockForwardPorts', [], 'QStringList'))
        block.discard(port.toString())
        allow = set(self.settings.value('allowForwardPorts', [], 'QStringList'))
        allow.add(port.toString())
        self.settings.setValue('blockForwardPorts', list(block))
        self.settings.setValue('allowForwardPorts', list(allow))
        self.settings.endGroup()
        self.blockForwardPorts.discard(addr)
        self.allowForwardPorts.add(addr)

    def blockPortForward(self, port, apply=False):
        if isinstance(port, Port):
            addr = port.addr
        else:
            addr = port
            port = self.graph.port_id_dict[addr[0]][addr[1]]
        self.settings.beginGroup('MIDI')
        block = set(self.settings.value('blockForwardPorts', [], 'QStringList'))
        block.add(port.toString())
        allow = set(self.settings.value('allowForwardPorts', [], 'QStringList'))
        allow.discard(port.toString())
        self.blockForwardPorts.add(addr)
        self.allowForwardPorts.discard(addr)
        if apply:
            self.settings.setValue('blockForwardPorts', list(block))
            self.settings.setValue('allowForwardPorts', list(allow))
            self.graph.graph_changed.emit()
        self.settings.endGroup()

    def newAlsaPort(self, port):
#        print('new alsa port', port)
        if port.hidden:
            return
        self.settings.beginGroup('MIDI')
        blofeldDetect = self.settings.value('blofeldDetect', True, bool)
        if blofeldDetect and port.client.name == 'Blofeld' and \
            port.name.startswith('Blofeld MIDI ') and port.name.split()[-1].isdigit:
                port.connect(self.input)
                self.output.connect(port)
                self.settings.endGroup()
                return
        autoConnect = self.settings.value('tryAutoConnect', True, bool)
        if not autoConnect:
            self.settings.endGroup()
            return
        autoConnectInput = set(self.settings.value('autoConnectInput', [], 'QStringList'))
        autoConnectOutput = set(self.settings.value('autoConnectOutput', [], 'QStringList'))
        portName = u'{}:{}'.format(port.client.name, port.name)
        if port.is_input and portName in autoConnectOutput:
            self.output.connect(port)
        if port.is_output and portName in autoConnectInput:
            port.connect(self.input)
        self.settings.endGroup()

    @property
    def connections(self):
        return ([conn for conn in self.midiDevice.input.connections.input if not conn.hidden], 
            [conn for conn in self.midiDevice.output.connections.output if not conn.hidden])

    def midiConnEvent(self, conn, state):
        if conn.hidden or (conn.dest != self.midiDevice.input and conn.src != self.midiDevice.output):
            return
        if conn.src == self.midiDevice.output:
            direction = True
            port = conn.dest
        else:
            direction = False
            port = conn.src
            if state and 'blofeld' in port.toString().lower():
                self.blockPortForward(port)
#        portName = u'{}:{}'.format(port.client.name, port.name)

        self.midiConnChanged.emit(*self.connections)
#        inConn, outConn = self.connections
#        self.mainWindow.showGlobalsAction.setEnabled(True if all((inConn, outConn)) else False)
#        self.editorWindow.midiInWidget.setConnections(len(inConn))
#        self.editorWindow.midiOutWidget.setConnections(len(outConn))

        if self.firstRunWizard and self.firstRunWizard.isVisible() and \
            self.firstRunWizard.currentPage() == self.firstRunWizard.autoconnectPage and \
            self.firstRunWizard.autoconnectPage.querying:
                return
        self.settings.beginGroup('MIDI')
        autoConnect = self.settings.value('tryAutoConnect', True, bool)
        if not autoConnect:
            self.settings.endGroup()
            self.disconnectionQueue.clear()
            return
        autoConnectInput = set(self.settings.value('autoConnectInput', [], 'QStringList'))
        autoConnectOutput = set(self.settings.value('autoConnectOutput', [], 'QStringList'))
        #we only discard ports manually disconnected by Bigglesworth
        if autoConnect:
            if direction:
                if state:
                    autoConnectOutput.add(port.toString())
                else:
                    if (port, direction) in self.disconnectionQueue:
                        self.disconnectionQueue.discard((port, direction))
                        autoConnectOutput.discard(port.toString())
                self.settings.setValue('autoConnectOutput', list(autoConnectOutput))
            else:
                if state:
                    autoConnectInput.add(port.toString())
                else:
                    if (port, direction) in self.disconnectionQueue:
                        self.disconnectionQueue.discard((port, direction))
                        autoConnectInput.discard(port.toString())
                self.settings.setValue('autoConnectInput', list(autoConnectInput))
        self.settings.endGroup()
        self.settings.sync()

    def saveConnections(self, reset=True):
        #why is this here?!?!?
        ([conn for conn in self.midiDevice.input.connections.input if not conn.hidden], 
            [conn for conn in self.midiDevice.output.connections.output if not conn.hidden])
#        autoConnectInput = set([u'{}:{}'.format(conn.src.client.name, conn.src.name) for conn in self.midiDevice.input.connections.input if not conn.hidden])
#        autoConnectOutput = set([u'{}:{}'.format(conn.dest.client.name, conn.dest.name) for conn in self.midiDevice.output.connections.output if not conn.hidden])
        autoConnectInput = set([conn.src.toString() for conn in self.midiDevice.input.connections.input if not conn.hidden])
        autoConnectOutput = set([conn.dest.toString() for conn in self.midiDevice.output.connections.output if not conn.hidden])
        self.settings.beginGroup('MIDI')
        if not reset:
            for port in self.settings.value('autoConnectInput', [], 'QStringList'):
                autoConnectInput.add(port)
            for port in self.settings.value('autoConnectOutput', [], 'QStringList'):
                autoConnectOutput.add(port)
        self.settings.setValue('autoConnectInput', list(autoConnectInput))
        self.settings.setValue('autoConnectOutput', list(autoConnectOutput))
        self.settings.endGroup()

    def midiConnect(self, port, direction, state):
        if direction:
            print(u'midi {s}connect requested. "{src}" >> "{dst}", direction: "OUT"'.format(
                s='' if state else 'dis', 
                src=self.output, 
                dst=port
                ))
            if state:
                self.output.connect(port)
            else:
                self.output.disconnect(port)
        else:
            print(u'midi {s}connect requested. "{src}" >> "{dst}", direction: "IN"'.format(
                s='' if state else 'dis', 
                src=port, 
                dst=self.input
                ))
            if state:
                port.connect(self.input)
            else:
                port.disconnect(self.input)
        if not state:
            self.disconnectionQueue.add((port, direction))

    def midiEventReceived(self, event):
        if event.source[0] == self.midiDevice.output.client.id:
            return
        print('midi event received', event.type, 'source:', event.source, self.graph.port_id_dict[event.source[0]][event.source[1]])
        if event == self.lastMidiEvent and self.lastMidiEvent.source != event.source and \
            not (self.firstRunWizard and self.firstRunWizard.isVisible()):
                if self.startTimer.elapsed() - self.lastMidiTime < 200:
                    self.midiDuplicateDialog.activate(self.dumpBlock, set((self.lastMidiEvent.source, event.source)))
                    self.lastMidiEvent = event
                    self.lastMidiTime = self.startTimer.elapsed()
                    return
                else:
                    self.midiDuplicateDialog.dismissed = False
                
        self.lastMidiEvent = event
        self.lastMidiTime = self.startTimer.elapsed()
        if self.globalsBlock:
            return
        elif self.dumpBlock:
            if event.type == SYSEX and event.sysex[4] == SNDD:
                if self.mainDumper.isVisible():
                    self.processLibraryDumpData(event)
                elif self.editorDumper.isVisible():
                    self.processEditorDumpData(event)
            return
        if event.type == SYSEX:
            sysexType = event.sysex[4]
            print('sysex received!', sysexType)
            if sysexType == SNDD:
                if (self.firstRunWizard and self.firstRunWizard.isVisible()) or \
                    (self.firstRunObject and not self.firstRunObject.isCompleted):
                        return
                active = self.activeModalWidget()
                if active:
                    if active.topMostDumpDialog():
                        return
                    self.dumpBuffer.append(event.sysex[5:390])
                    self.watchDialog(active)
                    return
                self.dumpBuffer.append(event.sysex[5:390])
                self.processDumpBuffer()
#                self.sound_dump_received(Sound(event.sysex[5:390], SRC_BLOFELD))
            elif sysexType in (SNDP, MULD):
                self.editorWindow.midiEventReceived(event)
#            elif sysexType == GLBD:
#                self.globals_event.emit(event.sysex)
#            elif len(event.sysex) == 15 and event.sysex[3:5] == [6, 2]:
#                self.device_event.emit(event.sysex)
            return
        elif event.type in (CTRL, NOTEON, NOTEOFF, PROGRAM):
            self.editorWindow.midiEventReceived(event)
            if WaveTableWindow.openedWindows and event.type in (NOTEON, NOTEOFF):
                WaveTableWindow.openedWindows[0].midiEventReceived(event)
            if event.type == CTRL and not event.param:
                self.bankBuffer = event.value
            elif event.type == PROGRAM and self.bankBuffer is not None:
                self.mainWindow.programChange(self.bankBuffer, event.program)
                self.bankBuffer = None

    def sendMidiEvent(self, event, ignoreChanSend=False):
#        if self.debug_sysex and event.type == SYSEX:
#            print event.sysex
        if self.midiDevice.backend == MidiDevice.Alsa:
            alsa_event = event.get_event()
            alsa_event.source = self.output.client.id, self.output.id
            if event.type in (CTRL, NOTEOFF, NOTEON, PROGRAM):
                if ignoreChanSend:
                    self.seq.output_event(alsa_event)
                else:
                    for chan in sorted(self._chanSend):
                        alsa_event.set_data({'control.channel': chan})
                        self.seq.output_event(alsa_event)
            else:
                self.seq.output_event(alsa_event)
            self.seq.drain_output()
        else:
            for port in self.seq.ports[1]:
                if event.type in (CTRL, NOTEOFF, NOTEON, PROGRAM):
                    if ignoreChanSend:
                        rtmidi_event = event.get_binary()
                        port.send_message(rtmidi_event)
                    else:
                        for chan in sorted(self._chanSend):
                            event.channel = chan
                            rtmidi_event = event.get_binary()
                            port.send_message(rtmidi_event)
                else:
                    rtmidi_event = event.get_binary()
                    port.send_message(rtmidi_event)
        self.midiEventSent.emit(event)

    def importRequested(self, uriList, collection):
        dialog = SoundImport(self.sender())
        if dialog.exec_(uriList, collection):
            self.processImport(dialog)

    def processImport(self, dialog):
        dataDict = dialog.getSelectedSoundData()
        if dialog.mode & dialog.OpenSound:
            index = dataDict.keys()[0]
            data = dataDict[index]
            if dialog.mode & dialog.LibraryImport:
                if dialog.mode & dialog.NewImport:
                    collection = dialog.newEdit.text()
                    self.database.createCollection(collection, iconName=dialog.collectionIconBtn.iconName())
                else:
                    if dialog.collectionCombo.currentIndex():
                        collection = dialog.collectionCombo.currentText()
                    else:
                        collection = None
                uid = self.database.addRawSoundData(data, collection=collection, index=index)
                self.mainWindow.openCollection(collection).selectUidList([uid])
                self.editorWindow.openSoundFromUid(uid, collection)
            else:
                self.editorWindow.openOrphanSound(data)
        elif dialog.mode & dialog.LibraryImport:
            if dialog.mode & dialog.NewImport:
                collection = dialog.newEdit.text()
                self.database.createCollection(collection, iconName=dialog.collectionIconBtn.iconName())
            else:
                if dialog.collectionCombo.currentIndex():
                    collection = dialog.collectionCombo.currentText()
                else:
                    collection = None
            uidList = self.database.addBatchRawSoundData(dataDict, collection, overwrite=False)
            self.mainWindow.openCollection(collection).selectUidList(uidList)

    def fullDumpBlofeldToCollection(self, collection, sounds):
        self.dumpBlock = True
        self.midiDevice.midi_event.connect(self.dumpReceiveDialog.midiEventReceived)
        self.graph.conn_register.connect(self.dumpReceiveDialog.midiConnEvent)
        data = self.dumpReceiveDialog.exec_(collection, sounds)
        if data:
            sounds, overwrite = data
            self.database.addBatchRawSoundData(sounds, collection, overwrite)
#            for index, data in sounds.items():
#                self.database.addRawSoundData(data, collection, index)

        self.graph.conn_register.disconnect(self.dumpReceiveDialog.midiConnEvent)
        self.midiDevice.midi_event.disconnect(self.dumpReceiveDialog.midiEventReceived)
        self.dumpBlock = False

    def fullDumpCollectionToBlofeld(self, collection, sounds):
        self.dumpBlock = True
        self.midiDevice.midi_event.connect(self.dumpSendDialog.midiEventReceived)
        self.graph.conn_register.connect(self.dumpSendDialog.midiConnEvent)
        self.dumpSendDialog.exec_(collection, sounds)
        self.graph.conn_register.disconnect(self.dumpSendDialog.midiConnEvent)
        self.midiDevice.midi_event.disconnect(self.dumpSendDialog.midiEventReceived)
        self.dumpBlock = False

    def dumpFrom(self, blofeldIndex, collection=None, index=None, multi=False):
        self.dumpBlock = True
        #blofeld index/buffer, collection, index, multi
        print('dump {} FROM blofeld to collection "{}" at {}, Multi {}'.format(blofeldIndex, collection, index, multi))
        if blofeldIndex is None:
            bank = 0x7f
            prog = 0
        else:
            if multi:
                bank = 0x7f
                prog = blofeldIndex
            else:
                bank = blofeldIndex >> 7
                prog = blofeldIndex & 127
        if self.sender() == self.mainWindow:
            model = self.database.openCollection(collection)
            uid = model.index(index, 0).data()
            if uid:
                if len(self.database.getCollectionsFromUid(uid)) == 1:
                    message = 'The selected slot is not empty\nOverwrite the data or create a new slot?'
                else:
                    message = 'The selected slot is not empty and is used in {} collections.\n' \
                        'Overwrite the data or create a new slot?'
                detailed = 'Bigglesworth uses a database that stores all sounds, some of which are shared amongst collections; ' \
                    'if a shared sound is changed, its changes will reflect on all collections containing it.<br/>' \
                    'If you want to keep the existing sound, press "New", otherwise by choosing "Overwrite" it will be lost. Forever.'
                buttons = {QtWidgets.QMessageBox.Save: ('New', QtGui.QIcon.fromTheme('document-new')), 
                    QtWidgets.QMessageBox.Ignore: ('Overwrite', QtGui.QIcon.fromTheme('edit-delete')), 
                    QtWidgets.QMessageBox.Cancel: None}
                res = WarningMessageBox(self.mainWindow, 'Overwrite sound?', message, detailed, buttons).exec_()
                if res == QtWidgets.QMessageBox.Cancel:
                    self.dumpBlock = False
                    return
                elif res == QtWidgets.QMessageBox.Save:
                    uid = None
            self.dumpTargetData = {'uid': uid, 'count': 0, 'tot': 1, 'collection': collection, 'collectionIndex': index}
            tot = 1
            dumper = self.mainDumper
        else:
            self.dumpTargetData = {'collection': collection, 'collectionIndex': index}
            if index is not None:
                if not multi and index >= 0:
                    model = self.database.openCollection(collection)
                    uid = model.index(index, 0).data()
                    if not isinstance(uid, (str, unicode)):
                        uid = None
                    self.dumpTargetData['uid'] = uid
#                    self.dumpTargetData['tot'] = 1
                    tot = 1
                elif multi:
                    if index < 0:
                        tot = 16
#                        self.dumpTargetData['tot'] = 16
                        self.dumpTargetData['multi'] = -1
                    else:
                        tot = 1
#                        self.dumpTargetData['tot'] = 1
                        self.dumpTargetData['multi'] = index
                else:
                    tot = 1
            elif multi:
                #TODO: check it!
                tot = 1
            else:
                tot = 1
            self.dumpTargetData['tot'] = tot
            dumper = self.editorDumper
            
        event = SysExEvent(1, [INIT, IDW, IDE, self._blofeldId, SNDR, bank, prog, CHK, END])
        QtCore.QTimer.singleShot(50, lambda: self.sendMidiEvent(event))
        dumper.start(tot=tot)

    def processLibraryDumpData(self, event):
        #ignore bank (index 5) and prog (index 6)
        data = event.sysex[7:390]
        collection = self.dumpTargetData.get('collection', None)
        index = self.dumpTargetData.get('collectionIndex', None)
        uid = self.dumpTargetData.get('uid', None)
        self.database.addRawSoundData(data, collection, index, uid)
        count = self.dumpTargetData.get('count', 0) + 1
        tot = self.dumpTargetData.get('tot', 1)
        if tot > 1:
            self.mainDumper.count = count
        if count == tot:
            self.mainDumper.accept()
        else:
            self.dumpTargetData['count'] = count
            #process new data?

    def processEditorDumpData(self, event):
        bank, prog = event.sysex[5:7]
        data = event.sysex[7:390]
        collection = self.dumpTargetData.get('collection', None)
        index = self.dumpTargetData.get('collectionIndex', None)
        uid = self.dumpTargetData.get('uid', None)
        if isinstance(uid, (str, unicode)):
            self.database.addRawSoundData(data, collection, index, uid)
        count = self.dumpTargetData.get('count', 0) + 1
        tot = self.dumpTargetData.get('tot', 1)
        if tot > 1:
            self.editorDumper.count = count
        if count == tot:
            self.editorDumper.accept()
            if index is None:
                self.editorWindow.currentBank = self.editorWindow.currentProg = self.editorWindow.currentUid = None
                resetIndex = True
            elif uid is not None:
                self.editorWindow.currentUid = uid
                resetIndex = False
            self.editorWindow.setValues(data, fromDump=True, resetIndex=resetIndex)
            #TODO: apply data to editor for multimode
        else:
            self.dumpTargetData['count'] = count
            event = SysExEvent(1, [INIT, IDW, IDE, self._blofeldId, SNDR, 0x7f, count, CHK, END])
            QtCore.QTimer.singleShot(200, lambda: self.sendMidiEvent(event))

    def processDumpBuffer(self):
        active = self.activeWindow()
        if not active:
            active = self.mainWindow if self.mainWindow.isVisible() else self.editorWindow
        self.dumpBlock = True
        dumper = BlofeldDumper(active, self.dumpBuffer)
        self.midiDevice.midi_event.connect(dumper.midiEventReceived)
        res = dumper.exec_()
        self.midiDevice.midi_event.disconnect(dumper.midiEventReceived)
        self.dumpBlock = False
        if res:
            self.processImport(dumper)

    def dumpTo(self, uid, index, multi):
        #uid, blofeld index/buffer, multi
#        print('dump "{}" TO blofeld at {}, Multi {}'.format(uid, index, multi))
        if index is None:
            bank = 0x7f
            prog = 0
        else:
            if multi:
                bank = 0x7f
                if index >= 0:
                    prog = index
                else:
                    prog = 0
            else:
                bank = index >> 7
                prog = index & 127
        if self.sender() == self.mainWindow:
            data = self.database.getSoundDataFromUid(uid)
        else:
            data = self.editorWindow.parameters[:]
        self.sendMidiEvent(SysExEvent(1, [INIT, IDW, IDE, self._blofeldId, SNDD, bank, prog] + data + [CHK, END]))

#    def findDuplicates(self, uid=None, collection=None):
#        dialog = FindDuplicates(self.mainWindow)
#        res = dialog.exec_(uid, collection)
#        if not res:
#            return
#        print(self.sender())

    def showSoundInLibrary(self, uid, collection=None):
#        if not collection:
#            collection = None
        for side in (self.mainWindow.leftTabWidget, self.mainWindow.rightTabWidget):
            if collection in side.collections:
                side.setCurrentIndex(side.collections.index(collection))
                break
        else:
            side = self.mainWindow.focusWidget()
            while side and not isinstance(side, QtWidgets.QTabWidget):
                side = side.parent()
            self.mainWindow.openCollection(collection, side)
        collectionWidget = side.currentWidget()
        collectionWidget.focusUid(uid)

    def refreshCollections(self, uid):
        if not uid:
            return
        for collection in self.database.collections.values():
            collection.updated.emit()

    def getSoundIndexFromCommandLine(self, arguments):
        if not arguments:
            return
        if len(arguments) == 1:
            collection = 'Blofeld'
            index = arguments[0]
        else:
            collection, index = arguments[0:2]
        try:
            bank = index[0].upper()
            bank = uppercase.index(bank)
            assert 0 <= bank <= 7
            prog = int(index[1:]) - 1
            assert 0 <= prog <= 127
        except:
            return
        for c in self.database.referenceModel.allCollections:
            if c.lower() == collection.lower():
                return bank, prog, collection

    def loadingComplete(self):
        self.splash.hide()
        showLibrarianTutorial = self.settings.value('ShowLibrarianTutorial', True, bool)
        if not self.settings.value('FirstRunShown', False, bool):
            self.firstRunWizard = FirstRunWizard(self)
            self.firstRunWizard.autoconnectPage.midiConnect.connect(self.midiConnect)
            self.firstRunWizard.autoconnectPage.midiEvent.connect(self.sendMidiEvent)
            self.firstRunWizard.midiConnectionsWidget.midiConnect.connect(self.midiConnect)
            self.graph.conn_register.connect(self.firstRunWizard.midiConnEvent)
            self.midiDevice.midi_event.connect(self.firstRunWizard.midiEventReceived)
            self.globalsBlock = True
            showLibrarianTutorial = self.firstRunWizard.exec_()
            self.globalsBlock = False
            self.midiDevice.midi_event.disconnect(self.firstRunWizard.midiEventReceived)
            self.graph.conn_register.disconnect(self.firstRunWizard.midiConnEvent)
            self.firstRunWizard.midiConnectionsWidget.midiConnect.disconnect(self.midiConnect)
            self.firstRunWizard.autoconnectPage.midiEvent.disconnect(self.sendMidiEvent)
            self.firstRunWizard.autoconnectPage.midiConnect.disconnect(self.midiConnect)
        if showLibrarianTutorial:
            self.mainWindow.show()
            from bigglesworth.firstrun import FirstRunObject
            self.firstRunObject = FirstRunObject(self)
#            self.firstRunObject.completed.connect(lambda completed: self.settings.setValue('FirstRunShown', completed))
            return
        elif self.settings.value('ShowEditorTutorial', True, bool):
            from bigglesworth.firstrun import FirstRunObject
            self.firstRunObject = FirstRunObject(self, editorOnly=True)
            
        if self.settings.value('StartupUpdateCheck', True, bool):
            self.updateChecker = UpdateChecker(30)
            self.updateCheckerThread = QtCore.QThread()
            self.updateChecker.moveToThread(self.updateCheckerThread)
            self.updateChecker.error.connect(self.updateError)
            self.updateChecker.result.connect(self.updateReceived)
            self.isCheckingUpdates = True
            self.updateChecker.finished.connect(self.updateCheckerThread.quit)
            self.updateCheckerThread.started.connect(self.updateChecker.run)
            QtCore.QTimer.singleShot(4000, self.updateCheckerThread.start)

        startUp = self.settings.value('StartUpWindow', 0, int)
        if self.argparse.editor is not None or startUp == 2:
            startUp = 2
            if self.argparse.librarian is not None:
                self.mainWindow.show()
#            self.editorWindow.show()
            QtCore.QTimer.singleShot(0, self.editorWindow.activate)
            index = self.getSoundIndexFromCommandLine(self.argparse.editor)
            if index:
                self.editorWindow.openSoundFromBankProg(*index)
        if self.argparse.wavetables or startUp == 3:
            startUp = 3
            if self.argparse.librarian is not None:
                self.mainWindow.show()
            QtCore.QTimer.singleShot(0, self.showWavetables)
        if self.argparse.librarian is not None or startUp == 1:
            startUp = 1
            self.mainWindow.show()
        if not startUp:
            self.welcome.show()

    def updateReceived(self, contents):
        self.isCheckingUpdates = False
        self.updateChecker.error.connect(self.updateError)
        self.updateChecker.result.connect(self.updateReceived)
        if isNewer(contents[0]['tag_name']):
            UpdateDialog(self.activeWindow()).exec_(contents)

    def updateError(self):
        self.isCheckingUpdates = False
        self.updateChecker.error.connect(self.updateError)
        self.updateChecker.result.connect(self.updateReceived)

    def checkUpdates(self, parent):
        if self.isCheckingUpdates:
            self.updateChecker.error.disconnect(self.updateError)
            self.updateChecker.result.disconnect(self.updateReceived)
            self.isCheckingUpdates = False
        UpdateDialog(parent).exec_()

    def getActionParent(self, parent=None):
        if not isinstance(parent, QtWidgets.QWidget):
            parent = self.sender()
            while isinstance(parent, (QtWidgets.QAction, QtWidgets.QMenu)):
                parent = parent.parent()
            while not isinstance(parent, QtWidgets.QWidget) or not parent.isWindow():
                parent = parent.parent()
        if parent is None:
            parent = self.activeWindow()
        return parent

    def checkWavetableMenu(self):
        menu = self.sender()
        for action in menu.wavetableActions:
            menu.removeAction(action)
        menu.wavetableActions[:] = []
        if WaveTableWindow.openedWindows:
            wtWindow = WaveTableWindow.openedWindows[0]
            wtWindow.checkWindowsMenu()
            for windowAction in wtWindow.windowsActionGroup.actions():
                action = QtWidgets.QAction(windowAction.icon(), windowAction.text(), menu)
                menu.insertAction(menu.windowsSeparator, action)
                window = windowAction.data()
                action.triggered.connect(window.activateWindow)
                menu.wavetableActions.append(action)
        menu.wavetableSection.setVisible(bool(menu.wavetableActions))

    def getWindowsMenu(self, parent, parentMenu=None):
        menu = QtWidgets.QMenu('&Windows', parentMenu if parentMenu else parent)
        if not isinstance(parent, MainWindow):
            librarianAction = menu.addAction(QtGui.QIcon.fromTheme('tab-duplicate'), '&Librarian')
            librarianAction.setShortcut(QtGui.QKeySequence('Alt+L'))
            librarianAction.triggered.connect(lambda: self.mainWindow.activate())
        if not isinstance(parent, EditorWindow):
            soundEditorAction = menu.addAction(QtGui.QIcon.fromTheme('dial'), 'Sound &editor')
            soundEditorAction.setShortcut(QtGui.QKeySequence('Alt+E'))
            soundEditorAction.triggered.connect(lambda: self.editorWindow.activate())
        if not isinstance(parent, WaveTableWindow):
            waveTableAction = menu.addAction(QtGui.QIcon.fromTheme('wavetables'), '&Wavetable editor')
            waveTableAction.setShortcut(QtGui.QKeySequence('Alt+W'))
            waveTableAction.triggered.connect(self.showWavetables)
            menu.wavetableActions = []
            menu.aboutToShow.connect(self.checkWavetableMenu)
        menu.wavetableSection = menu.addSection('Open wavetables')
        menu.windowsSeparator = menu.addSeparator()
        settingsAction = menu.addAction(QtGui.QIcon.fromTheme('settings'), '&Settings')
        settingsAction.setShortcut(QtGui.QKeySequence('Ctrl+P'))
        settingsAction.triggered.connect(self.showSettings)
        globalsAction = menu.addAction(QtGui.QIcon.fromTheme('blofeld-b'), 'Blofeld device &query')
        globalsAction.triggered.connect(self.showGlobals)
        firmwareAction = menu.addAction(QtGui.QIcon.fromTheme('circuit'), 'Firmware utilities')
        firmwareAction.triggered.connect(self.showFirmwareUtils)

        inConn, outConn = self.connections
        globalsAction.setEnabled(all((inConn, outConn)))
        firmwareAction.setEnabled(bool(outConn))

        def enableActions(inConn, outConn, globalsAction, firmwareAction):
            globalsAction.setEnabled(all((inConn, outConn)))
            firmwareAction.setEnabled(bool(outConn))
        self.midiConnChanged.connect(lambda inConn, outConn, g=globalsAction, f=firmwareAction: enableActions(inConn, outConn, g, f))

        return menu

    def getAboutMenu(self, parent, parentMenu=None):
        menu = QtWidgets.QMenu('&?', parentMenu if parentMenu else parent)
        helpAction = menu.addAction(QtGui.QIcon.fromTheme('help-contents'), 'Bigglesworth Manual')
        helpAction.triggered.connect(self.showHelp)
        loggerAction = menu.addAction(QtGui.QIcon.fromTheme('text-x-log'), 'Show log')
        loggerAction.triggered.connect(self.loggerWindow.show)
        midiChartAction = menu.addAction(QtGui.QIcon.fromTheme('midi'), 'MIDI implementation chart...')
        midiChartAction.triggered.connect(lambda _, parent=parent: MidiChartDialog(self.getActionParent(parent)).exec_())
        menu.addSeparator()
        aboutAction = menu.addAction(QtGui.QIcon.fromTheme('help-contents'), 'About &Bigglesworth...')
        aboutAction.triggered.connect(self.showAbout)
        aboutQtAction = menu.addAction(QtGui.QIcon.fromTheme('qtcreator'), 'About &Qt...')
        aboutQtAction.triggered.connect(lambda _, parent=parent: QtWidgets.QMessageBox.aboutQt(self.getActionParent(parent), 'About Qt...'))
        donateAction = menu.addAction(QtGui.QIcon.fromTheme('help-donate'), 'Donate...')
        donateAction.triggered.connect(self.showDonation)
        menu.addSeparator()
        updatesAction = menu.addAction(QtGui.QIcon.fromTheme('system-software-update'), 'Check for updates...')
#        updatesAction.setEnabled(False)
        updatesAction.triggered.connect(lambda _, parent=parent: self.checkUpdates(parent))
        return menu

    def showWavetables(self):
        if WaveTableWindow.openedWindows:
#            wtWindow = WaveTableWindow.openedWindows[-1]
            if WaveTableWindow.lastActive:
                wtWindow = WaveTableWindow.lastActive[-1]
            else:
                wtWindow = WaveTableWindow.openedWindows[-1].createNewWindow()
        else:
            wtWindow = WaveTableWindow()
            wtWindow.midiEvent.connect(self.sendMidiEvent)
            wtWindow.midiConnect.connect(self.midiConnect)
            if sys.platform == 'darwin':
                wtWindow.closed.connect(self.checkCloseMacOS)

        wtWindow.showSettings.connect(self.showSettings)
        wtWindow.show()
        wtWindow.activateWindow()

    def showSettings(self, parent=None):
        self.settingsDialog.setParent(self.getActionParent(parent), QtCore.Qt.Dialog)
        self.globalsBlock = True
        self.midiDevice.midi_event.connect(self.settingsDialog.midiEventReceived)
        self.graph.conn_register.connect(self.settingsDialog.midiConnEvent)
        self.midiConnChanged.connect(self.settingsDialog.midiConnEvent)
        res = self.settingsDialog.exec_()
        self.midiConnChanged.disconnect(self.settingsDialog.midiConnEvent)
        self.graph.conn_register.disconnect(self.settingsDialog.midiConnEvent)
        self.midiDevice.midi_event.disconnect(self.settingsDialog.midiEventReceived)
        self.globalsBlock = False
        if not res:
            return
        self.blofeldId = self.settingsDialog.deviceIdSpin.value()
        themeName = self.settingsDialog.themeCombo.currentText()
        if themeName != self.themes.current:
            self.themes.setCurrentTheme(themeName)
            self.editorWindow.setTheme(self.themes.current)
#            self.settings.setValue('theme', self.themes.current.name)

    def showGlobals(self, parent=None):
        self.globalsDialog.setParent(self.getActionParent(parent), QtCore.Qt.Dialog)
        self.globalsBlock = True
        self.midiDevice.midi_event.connect(self.globalsDialog.midiEventReceived)
        self.midiConnChanged.connect(self.globalsDialog.midiConnChanged)
        res = self.globalsDialog.exec_()
        self.midiConnChanged.disconnect(self.globalsDialog.midiConnChanged)
        self.midiDevice.midi_event.disconnect(self.globalsDialog.midiEventReceived)
        self.globalsBlock = False
        if not res:
            return

    def showFirmwareUtils(self, parent=None):
        self.firmwareDialog.setParent(self.getActionParent(parent), QtCore.Qt.Dialog)
        self.globalsBlock = True
        self.midiDevice.midi_event.connect(self.firmwareDialog.midiEventReceived)
        self.midiConnChanged.connect(self.firmwareDialog.midiConnChanged)
        self.firmwareDialog.exec_()
        self.midiConnChanged.disconnect(self.firmwareDialog.midiConnChanged)
        self.midiDevice.midi_event.disconnect(self.firmwareDialog.midiEventReceived)
        self.globalsBlock = False

    def showDonation(self, parent=None):
        res = DonateDialog(self.getActionParent(parent)).exec_()
        if res:
            amount, currency, anonymous = res
            url = 'http://bigglesworth.it/pp/donate.php?amount={}&currency={}'.format(
                amount, currency)
            if anonymous:
                url += '&anonymous=true'
            QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))
            self.settings.setValue('DonationDone', True)

    @QtCore.pyqtSlot(str)
    def showHelp(self, keyword=''):
        parent = self.getActionParent()
#        try:
#            parent = self.sender().window()
#        except:
#            parent = self.sender()
#            while parent:
#                parent = parent.parent()
#                if isinstance(parent, (QtWidgets.QMainWindow, QtWidgets.QDialog)):
#                    break
        if not keyword and parent:
            keyword = parent.objectName()
        elif isinstance(keyword, QtCore.QObject):
            keyword = keyword.objectName()
        self.helpDialog.openKeyword(keyword, parentWindow=parent)

    def showAbout(self):
        parent = self.getActionParent()
        if randrange(100) / 33:
            AboutDialog(parent).exec_()
        else:
            self.lastAboutEgg = not self.lastAboutEgg
            from bigglesworth.forcebwu import MayTheForce
            from bigglesworth.matrixhasu import MatrixHasU
            (MayTheForce, MatrixHasU)[self.lastAboutEgg](parent).exec_()

    def progChangeRequest(self, index, collection):
        if not self.sendLibraryProgChange:
            return
        if self.editorWindow._editStatus == self.editorWindow.Modified:
            self.mainWindow.statusbar.showMessage('Failsafe active, program change ignored: current sound in Editor is unsaved!')
        else:
            bank = index >> 7
            prog = index & 127
            self.editorWindow.openSoundFromBankProg(bank, prog, collection, show=False)

    def isClean(self):
        if self.editorWindow._editStatus == self.editorWindow.Modified:
            return False
        for wtWindow in WaveTableWindow.openedWindows:
            if wtWindow.isVisible() and not wtWindow.isClean():
                return False
        return True

    def eventFilter(self, source, event):
        if source in self.watchedDialogs and event.type() == QtCore.QEvent.QCloseEvent:
            source.removeEventFilter(self)
            self.watchedDialogs.pop(self.watchedDialogs.index(source))
            active = self.activeModalWidget()
            if active:
                if active.topMostDumpDialog():
                    return
                else:
                    self.watchDialog(active)
            else:
                QtCore.QTimer.singleShot(0, self.processDumpBuffer)
        return QtWidgets.QApplication.eventFilter(self, source, event)

    def watchDialog(self, dialog):
        dialog = dialog.topMostDialog()
        if dialog not in self.watchedDialogs:
            self.watchedDialogs.append(dialog)
            dialog.installEventFilter(self)

    def notify(self, receiver, event):
        if event.type() in (QtCore.QEvent.KeyPress, QtCore.QEvent.KeyRelease):
            try:
                if self.editorWindow.isActiveWindow() and event.key() == QtCore.Qt.Key_F1 and not event.isAutoRepeat():
                    self.editorWindow.showValues(True if event.type() == QtCore.QEvent.KeyPress else False)
            except:
                pass
        return QtWidgets.QApplication.notify(self, receiver, event)

    def restart(self):
#        self.database.sql.close()
        self.watcher.quit()
        self.pidFile.remove()
        sleep(2)
        QtWidgets.QApplication.quit()
        QtCore.QProcess.startDetached(self._arguments[0], self._arguments)

    def quit(self):
        def canCloseWavetables():
            for wtWindow in WaveTableWindow.openedWindows:
                if wtWindow.isVisible() and not wtWindow.close():
                    return False
            return True

        if self.initialized:
            if isinstance(self.activeWindow(), WaveTableWindow):
                if not all((canCloseWavetables(), self.editorWindow.close())):
                    return
            elif not all((self.editorWindow.close(), canCloseWavetables())):
                return

        QtWidgets.QApplication.quit()

    def checkClose(self):
        if not (self.mainWindow.isVisible() and self.editorWindow.isVisible()) and \
            self.loggerWindow.isVisible():
                self.loggerWindow.close()
        elif sys.platform == 'darwin':
            QtCore.QTimer.singleShot(0, self.checkCloseMacOS)

    def checkCloseMacOS(self):
        if not self.activeWindow():
            self.checkWelcomeOnClose()

    def checkWelcomeOnClose(self):
        if self.settings.value('WelcomeOnClose', True, bool):
            self.welcome.show()
        elif sys.platform == 'darwin':
            self.quit()

    def updateSplashFactory(self, factory, bank):
        factoryIndex = factoryPresets.index(factory)
        pos = (factoryIndex * 8 + bank + 1) / .24
        status = '{} ({} of 3) {}%'.format(factoryPresetsNamesDict[factory], factoryIndex + 1, int(pos))
        self.splash.showMessage('Creating factory database, please wait...\n{}'.format(status), QtCore.Qt.AlignLeft|QtCore.Qt.AlignBottom, .25 + pos * .00125)

    def updateSplashWavetables(self, name, slot):
        pos = int(slot * .8)
        status = 'Slot {} of 125: {} ({}%)'.format(slot + 1, name, pos)
        self.splash.showMessage('Creating wavetable preset data, please wait...\n{}'.format(status), QtCore.Qt.AlignLeft|QtCore.Qt.AlignBottom, .375 + pos * .00125)


    def exec_(self):
        #TODO: fix, maybe with some polished signal from the splash?
        try:
            self.splash.showMessage('Starting up...', QtCore.Qt.AlignLeft|QtCore.Qt.AlignBottom, .1)
            QtCore.QTimer.singleShot(150, self.startUp)
        except:
            #existing instance found, will quit...
            pass
        return QtWidgets.QApplication.exec_()
