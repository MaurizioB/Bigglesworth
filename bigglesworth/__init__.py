#!/usr/bin/env python2.7

from __future__ import print_function
import os, sys
from string import uppercase
sys.path.append(os.path.join(os.path.dirname(__file__), 'bigglesworth/editorWidgets'))
os.environ['QT_PREFERRED_BINDING'] = 'PyQt4'

from Qt import QtCore, QtGui, QtWidgets
QtCore.pyqtSlot = QtCore.Slot
QtCore.pyqtSignal = QtCore.Signal
QtCore.pyqtProperty = QtCore.Property
from PyQt4.QtGui import QIdentityProxyModel as _QIdentityProxyModel
QtCore.QIdentityProxyModel = _QIdentityProxyModel

from bigglesworth.editor import EditorWindow
from bigglesworth.database import BlofeldDB
from bigglesworth.widgets import SplashScreen
from bigglesworth.mainwindow import MainWindow
from bigglesworth.themes import ThemeCollection
from bigglesworth.dialogs import (DatabaseCorruptionMessageBox, SettingsDialog, GlobalsDialog, 
    DumpReceiveDialog, DumpSendDialog, WarningMessageBox, SmallDumper, FirstRunWizard)
from bigglesworth.utils import localPath
from bigglesworth.const import INIT, IDE, IDW, CHK, END, SNDD, SNDP, SNDR
from bigglesworth.midiutils import SYSEX, CTRL, SysExEvent

os.environ['MIDI_BACKEND'] = 'ALSA'

from bigglesworth.mididevice import MidiDevice, midiBackend, Alsa, RtMidi

class Bigglesworth(QtWidgets.QApplication):
    progSendToggled = QtCore.pyqtSignal(bool)
    ctrlSendToggled = QtCore.pyqtSignal(bool)
    progReceiveToggled = QtCore.pyqtSignal(bool)
    ctrlReceiveToggled = QtCore.pyqtSignal(bool)

    def __init__(self, argparse, args):
        QtWidgets.QApplication.__init__(self, ['Bigglesworth'] + args)
        self.argparse = argparse
        self._arguments = args
        self.setOrganizationName('jidesk')
        self.setApplicationName('Bigglesworth')
        self.settings = QtCore.QSettings()
        self.firstRunWizard = None

        self.settings.beginGroup('MIDI')
        self._blofeldId = self.settings.value('blofeldId', 0x7f, int)
        self._progReceiveState = self.settings.value('progReceive', True, bool)
        self._ctrlReceiveState = self.settings.value('ctrlReceive', True, bool)
        self._chanReceive = self.settings.value('chanReceive', set(range(16)), set)
        self._progSendState = self.settings.value('progSend', True, bool)
        self._ctrlSendState = self.settings.value('ctrlSend', True, bool)
        self._chanSend = self.settings.value('chanSend', set((0, )), set)
        self.settings.endGroup()
        self.globalsBlock = False
        self.dumpBlock = False

        self.splash = SplashScreen()
        self.splash.start()

    def startUp(self):
        self.splash.showMessage('Loading database engine', QtCore.Qt.AlignLeft|QtCore.Qt.AlignBottom, .2)

        self.database = BlofeldDB(self)
        if not self.database.initialize(localPath('library.sqlite')):
            if self.database.lastError & (self.database.SoundsEmpty|self.database.ReferenceEmpty):
                self.splash.showMessage('Creating factory database', QtCore.Qt.AlignLeft|QtCore.Qt.AlignBottom, .25)
                self.database.initializeFactory(self.database.lastError)
            elif self.database.lastError & self.database.DatabaseFormatError:
                print(self.database.lastError)
                if not self.database.checkTables(True) and self.database.lastError & (self.database.SoundsEmpty|self.database.ReferenceEmpty):
                    DatabaseCorruptionMessageBox(self.splash, str(self.database.lastError)).exec_()
                    self.splash.showMessage('Correcting factory database', QtCore.Qt.AlignLeft|QtCore.Qt.AlignBottom, .4)
                    self.database.initializeFactory(self.database.lastError)
                else:
                    print('porcozzio', self.database.lastError)
            else:
                print(self.database.lastError)

        self.splash.showMessage('Starting MIDI engine', QtCore.Qt.AlignLeft|QtCore.Qt.AlignBottom, .5)

        self.midiDevice = MidiDevice(self)
        self.graph = self.midiDevice.graph
        self.midiThread = QtCore.QThread()
        self.midiDevice.moveToThread(self.midiThread)
        self.midiDevice.stopped.connect(self.midiThread.quit)
        self.midiThread.started.connect(self.midiDevice.run)

        self.seq = self.midiDevice.seq
        self.input = self.midiDevice.input
        self.output = self.midiDevice.output
#        self.connections = [0, 0]
        self.midi_duplex_state = False
        self.midiThread.start()

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
                        if blofeldDetect and port.client.name == 'Blofeld' and \
                            port.name.startswith('Blofeld MIDI ') and port.name.split()[-1].isdigit:
                                port.connect(self.input)
                                self.output.connect(port)
                                continue
                        portName = '{}:{}'.format(port.client.name, port.name)
                        if port.is_input and portName in autoConnectOutput:
                            self.midiConnect(port, True, True)
                        if port.is_output and portName in autoConnectInput:
                            self.midiConnect(port, False, True)

        self.graph.port_start.connect(self.newAlsaPort)
        self.graph.conn_register.connect(self.alsaConnEvent)
        self.midiDevice.midi_event.connect(self.midiEventReceived)

        self.splash.showMessage('Preparing interface', QtCore.Qt.AlignLeft|QtCore.Qt.AlignBottom, .7)

        self.themes = ThemeCollection(self)

        self.mainWindow = MainWindow(self)
        self.mainWindow.quitAction.triggered.connect(self.quit)
        self.mainWindow.showSettingsAction.triggered.connect(self.showSettings)
        self.mainWindow.showGlobalsAction.triggered.connect(self.showGlobals)
        self.mainWindow.showGlobalsAction.setEnabled(True if all(self.connections) else False)
        self.mainWindow.leftTabWidget.fullDumpBlofeldToCollectionRequested.connect(self.fullDumpBlofeldToCollection)
        self.mainWindow.leftTabWidget.fullDumpCollectionToBlofeldRequested.connect(self.fullDumpCollectionToBlofeld)
        self.mainWindow.rightTabWidget.fullDumpBlofeldToCollectionRequested.connect(self.fullDumpBlofeldToCollection)
        self.mainWindow.rightTabWidget.fullDumpCollectionToBlofeldRequested.connect(self.fullDumpCollectionToBlofeld)
        self.mainWindow.dumpToRequested.connect(self.dumpTo)
        self.mainWindow.dumpFromRequested.connect(self.dumpFrom)

        self.editorWindow = EditorWindow(self)
        self.editorWindow.openLibrarianRequested.connect(lambda: [self.mainWindow.show(), self.mainWindow.activateWindow()])
        self.editorWindow.midiEvent.connect(self.sendMidiEvent)
        self.editorWindow.midiConnect.connect(self.midiConnect)
        self.mainWindow.showEditorAction.triggered.connect(self.editorWindow.show)
        self.mainWindow.soundEditRequested.connect(self.editorWindow.openSoundFromUid)
        self.editorWindow.midiInWidget.setConnections(len([conn for conn in self.midiDevice.input.connections.input if not conn.hidden]))
        self.editorWindow.midiOutWidget.setConnections(len([conn for conn in self.midiDevice.output.connections.output if not conn.hidden]))

        self.splash.showMessage('Applying preferences', QtCore.Qt.AlignLeft|QtCore.Qt.AlignBottom, 1)

        self.settingsDialog = SettingsDialog(self, self.mainWindow)
        self.settingsDialog.midiEvent.connect(self.sendMidiEvent)
        self.settingsDialog.midiConnectionsWidget.setMain(self)
        self.settingsDialog.midiConnectionsWidget.midiConnect.connect(self.midiConnect)
        self.settingsDialog.themeChanged.connect(self.editorWindow.setTheme)
        self.editorWindow.setTheme(self.themes.current)
#        self.mainWindow.setPalette(self.themes.current.palette)

        self.globalsDialog = GlobalsDialog(self, self.mainWindow)
        self.globalsDialog.midiEvent.connect(self.sendMidiEvent)

        self.dumpReceiveDialog = DumpReceiveDialog(self, self.mainWindow)
        self.dumpReceiveDialog.midiEvent.connect(self.sendMidiEvent)
        self.dumpSendDialog = DumpSendDialog(self, self.mainWindow)
        self.dumpSendDialog.midiEvent.connect(self.sendMidiEvent)
        self.mainDumper = SmallDumper(self)
        self.mainDumper.accepted.connect(lambda: setattr(self, 'dumpBlock', False))
        self.editorDumper = SmallDumper(self)
        self.editorDumper.accepted.connect(lambda: setattr(self, 'dumpBlock', False))
#        self.mainDumper.rejected.connect(lambda: setattr(self, 'dumpBlock', False))


        self.splash.showMessage('Prepare for some coolness! ;-)', QtCore.Qt.AlignLeft|QtCore.Qt.AlignBottom)

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
                return
        autoConnect = self.settings.value('tryAutoConnect', True, bool)
        if not autoConnect:
            self.settings.endGroup()
            return
        autoConnectInput = set(self.settings.value('autoConnectInput', [], 'QStringList'))
        autoConnectOutput = set(self.settings.value('autoConnectOutput', [], 'QStringList'))
        portName = '{}:{}'.format(port.client.name, port.name)
        if port.is_input and portName in autoConnectOutput:
            self.output.connect(port)
        if port.is_output and portName in autoConnectInput:
            port.connect(self.input)
        self.settings.endGroup()

    @property
    def connections(self):
        return ([conn for conn in self.midiDevice.input.connections.input if not conn.hidden], 
            [conn for conn in self.midiDevice.output.connections.output if not conn.hidden])

    def alsaConnEvent(self, conn, state):
        print('connection event', conn, state)
        if conn.hidden or (conn.dest != self.midiDevice.input and conn.src != self.midiDevice.output):
            return
        if conn.src == self.midiDevice.output:
            direction = True
            port = conn.dest
        else:
            direction = False
            port = conn.src
        portName = '{}:{}'.format(port.client.name, port.name)

        inConn, outConn = self.connections
        self.mainWindow.showGlobalsAction.setEnabled(True if all((inConn, outConn)) else False)
        self.editorWindow.midiInWidget.setConnections(len(inConn))
        self.editorWindow.midiOutWidget.setConnections(len(outConn))

        self.settings.beginGroup('MIDI')
        autoConnect = self.settings.value('tryAutoConnect', True, bool)
        if not autoConnect:
            self.settings.endGroup()
            return
        autoConnectInput = set(self.settings.value('autoConnectInput', [], 'QStringList'))
        autoConnectOutput = set(self.settings.value('autoConnectOutput', [], 'QStringList'))
        if autoConnect:
            if direction:
                if state:
                    autoConnectOutput.add(portName)
                else:
                    autoConnectOutput.discard(portName)
                self.settings.setValue('autoConnectOutput', list(autoConnectOutput))
            else:
                if state:
                    autoConnectInput.add(portName)
                else:
                    autoConnectInput.discard(portName)
                self.settings.setValue('autoConnectInput', list(autoConnectInput))
        self.settings.endGroup()
        self.settings.sync()

    def midiConnect(self, port, direction, state):
        if direction:
            if state:
                self.output.connect(port)
            else:
                self.output.disconnect(port)
        else:
            if state:
                port.connect(self.input)
            else:
                port.disconnect(self.input)

    def midiEventReceived(self, event):
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
                pass
#                self.sound_dump_received(Sound(event.sysex[5:390], SRC_BLOFELD))
            elif sysexType == SNDP:
                self.editorWindow.midiEventReceived(event)
#            elif sysexType == GLBD:
#                self.globals_event.emit(event.sysex)
#            elif len(event.sysex) == 15 and event.sysex[3:5] == [6, 2]:
#                self.device_event.emit(event.sysex)
            return
        elif event.type == CTRL:
            self.editorWindow.midiEventReceived(event)
        print('midi event received', event, 'source:', self.graph.port_id_dict[event.source[0]][event.source[1]])

    def sendMidiEvent(self, event):
#        if self.debug_sysex and event.type == SYSEX:
#            print event.sysex
        if midiBackend == Alsa:
            alsa_event = event.get_event()
            alsa_event.source = self.output.client.id, self.output.id
            self.seq.output_event(alsa_event)
            self.seq.drain_output()
        else:
            rtmidi_event = event.get_binary()
            for port in self.seq.ports[1]:
                port.send_message(rtmidi_event)

    def fullDumpBlofeldToCollection(self, collection, sounds):
        self.dumpBlock = True
        self.midiDevice.midi_event.connect(self.dumpReceiveDialog.midiEventReceived)
        self.graph.conn_register.connect(self.dumpReceiveDialog.alsaConnEvent)
        sounds = self.dumpReceiveDialog.exec_(collection, sounds)
        if sounds:
            self.database.addBatchRawSoundData(sounds, collection)
#            for index, data in sounds.items():
#                self.database.addRawSoundData(data, collection, index)

        self.graph.conn_register.disconnect(self.dumpReceiveDialog.alsaConnEvent)
        self.midiDevice.midi_event.disconnect(self.dumpReceiveDialog.midiEventReceived)
        self.dumpBlock = False

    def fullDumpCollectionToBlofeld(self, collection, sounds):
        self.dumpBlock = True
        self.midiDevice.midi_event.connect(self.dumpSendDialog.midiEventReceived)
        self.graph.conn_register.connect(self.dumpSendDialog.alsaConnEvent)
        self.dumpSendDialog.exec_(collection, sounds)
        self.graph.conn_register.disconnect(self.dumpSendDialog.alsaConnEvent)
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
                    message = 'The selected slot is not empty, overwrite the data or create a new slot?'
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
            self.dumpTargetData = {'collection': collection}
            if index is not None:
                if not multi and index >= 0:
                    model = self.database.openCollection(collection)
                    uid = model.index(index, 0).data()
                    if not isinstance(uid, (str, unicode)):
                        uid = None
                    self.dumpTargetData['uid'] = uid
                    self.dumpTargetData['tot'] = 1
                elif multi:
                    if index < 0:
                        self.dumpTargetData['tot'] = 16
                        self.dumpTargetData['multi'] = -1
                    else:
                        self.dumpTargetData['tot'] = 1
                        self.dumpTargetData['multi'] = index
            elif multi:
                self.dumpTargetData['tot'] = 1
            dumper = self.editor
            
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
            self.editorWindow.currentBank = self.editorWindow.currentProg = self.editorWindow.currentUid = None
            self.editorWindow.setValues(data)
            #TODO: apply data to editor for multimode
        else:
            self.dumpTargetData['count'] = count
            event = SysExEvent(1, [INIT, IDW, IDE, self._blofeldId, SNDR, 0x7f, count, CHK, END])
            QtCore.QTimer.singleShot(200, lambda: self.sendMidiEvent(event))


    def dumpTo(self, uid, index, multi):
        #uid, blofeld index/buffer, multi
#        print('dump "{}" TO blofeld at {}, Multi {}'.format(uid, index, multi))
        data = self.database.getSoundDataFromUid(uid)
        if index is None:
            bank = 0x7f
            prog = 0
        else:
            if multi:
                bank = 0x7f
                prog = index
            else:
                bank = index >> 7
                prog = index & 127
        self.sendMidiEvent(SysExEvent(1, [INIT, IDW, IDE, self._blofeldId, SNDD, bank, prog] + data + [CHK, END]))

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
        if not self.settings.value('FirstRunShown', False, bool):
            self.firstRunWizard = FirstRunWizard(self)
            self.firstRunWizard.autoconnectPage.midiConnect.connect(self.midiConnect)
            self.firstRunWizard.autoconnectPage.midiEvent.connect(self.sendMidiEvent)
            self.firstRunWizard.midiConnectionsWidget.midiConnect.connect(self.midiConnect)
            self.graph.conn_register.connect(self.firstRunWizard.alsaConnEvent)
            self.midiDevice.midi_event.connect(self.firstRunWizard.midiEventReceived)
            self.globalsBlock = True
            res = self.firstRunWizard.exec_()
            self.globalsBlock = False
            self.midiDevice.midi_event.disconnect(self.firstRunWizard.midiEventReceived)
            self.graph.conn_register.disconnect(self.firstRunWizard.alsaConnEvent)
            self.firstRunWizard.midiConnectionsWidget.midiConnect.disconnect(self.midiConnect)
            self.firstRunWizard.autoconnectPage.midiEvent.disconnect(self.sendMidiEvent)
            self.firstRunWizard.autoconnectPage.midiConnect.disconnect(self.midiConnect)
            if res:
                pass
#                self.settings.setValue('FirstRunShown', True)
                self.mainWindow.show()
                from bigglesworth.firstrun import FirstRunObject
                self.firstRunObject = FirstRunObject(self)
                self.firstRunObject.completed.connect(lambda completed: self.settings.setValue('FirstRunShown', completed))
                return
        if self.argparse.editor is not None:
            if self.argparse.librarian:
                self.mainWindow.show()
            self.editorWindow.show()
            index = self.getSoundIndexFromCommandLine(self.argparse.editor)
            if index:
                self.editorWindow.openSoundFromBankProg(*index)
        else:
            self.mainWindow.show()

    def showSettings(self):
        self.globalsBlock = True
        self.midiDevice.midi_event.connect(self.settingsDialog.midiEventReceived)
#        self.graph.conn_register.connect(self.settingsDialog.alsaConnEvent)
        res = self.settingsDialog.exec_()
#        self.graph.conn_register.disconnect(self.settingsDialog.alsaConnEvent)
        self.midiDevice.midi_event.disconnect(self.settingsDialog.midiEventReceived)
        self.globalsBlock = False
        if not res:
            return
        themeName = self.settingsDialog.themeCombo.currentText()
        if themeName != self.themes.current:
            self.themes.setCurrentTheme(themeName)
            self.editorWindow.setTheme(self.themes.current)
#            self.settings.setValue('theme', self.themes.current.name)

    def showGlobals(self):
        self.globalsBlock = True
        self.midiDevice.midi_event.connect(self.globalsDialog.midiEventReceived)
        res = self.globalsDialog.exec_()
        self.midiDevice.midi_event.disconnect(self.globalsDialog.midiEventReceived)
        self.globalsBlock = False
        if not res:
            return

    def notify(self, receiver, event):
        if event.type() in (QtCore.QEvent.KeyPress, QtCore.QEvent.KeyRelease):
            if self.editorWindow.isActiveWindow() and event.key() == QtCore.Qt.Key_F1:
                self.editorWindow.showValues(True if event.type() == QtCore.QEvent.KeyPress else False)
        return QtWidgets.QApplication.notify(self, receiver, event)

    def restart(self):
        QtWidgets.QApplication.quit()
        QtCore.QProcess.startDetached(self._arguments[0], self._arguments)

    def quit(self):
        QtWidgets.QApplication.quit()

    def exec_(self):
        #TODO: fix, maybe with some polished signal from the splash?
        self.splash.showMessage('Starting up...', QtCore.Qt.AlignLeft|QtCore.Qt.AlignBottom, .1)
        QtCore.QTimer.singleShot(150, self.startUp)
        return QtWidgets.QApplication.exec_()
