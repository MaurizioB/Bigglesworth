import sys
from collections import namedtuple
from math import sin, pi, sqrt

import samplerate
import numpy as np
from Qt import QtCore, QtGui, QtWidgets, QtMultimedia

from bigglesworth.utils import loadUi, setBold, setItalic
from bigglesworth.wavetables.utils import sineValues, defaultBufferSize

bufferSizes = [
    4096, 
    8192, 
    16384, 
    32768, 
    65536, 
]

channelsLabels = {
    1: 'Mono', 
    2: 'Stereo', 
    3: 'Stereo + Central/Rear', 
    4: 'Quad/Surround', 
    5: 'Surround + Center', 
    6: '5.1', 
    7: '3 Front + 3 Rear + Sub', 
    8: '7.1'
    }

ValidRole = QtCore.Qt.UserRole + 1
DataRole = QtCore.Qt.UserRole + 1
DeviceRole = ValidRole + 1
SampleRateRole = DeviceRole + 1
SampleSizeRole = SampleRateRole + 1
ChannelsRole = SampleSizeRole + 1
FormatRole = ChannelsRole + 1

audioDevice = namedtuple('audioDevice', 'device name sampleRates sampleSizes channels')


class AudioDeviceProber(QtCore.QObject):
    deviceList = QtCore.pyqtSignal(object)
    def probe(self):
        deviceList = []
        for device in QtMultimedia.QAudioDeviceInfo.availableDevices(QtMultimedia.QAudio.AudioOutput):
            deviceInfo = audioDevice(device, device.deviceName(), device.supportedSampleRates(), device.supportedSampleSizes(), device.supportedChannelCounts())
            deviceList.append(deviceInfo)
        self.deviceList.emit(deviceList)


#class AudioDevicesListView(QtWidgets.QListView):
#    deviceSelected = QtCore.pyqtSignal(object)
#    def currentChanged(self, current, previous):
#        self.deviceSelected.emit(current)


class AudioSettingsDialog(QtWidgets.QDialog):
    Best, Medium, Fastest, Zero, Linear = range(5)

    def __init__(self, parent, player):
        QtWidgets.QDialog.__init__(self, parent)
        loadUi('ui/audiosettings.ui', self)
        self.waveTableWindow = parent
        self.player = player
        self.settings = QtCore.QSettings()

        self.popup = QtWidgets.QMessageBox(
            QtWidgets.QMessageBox.Information, 
            'Probing audio devices', 
            'Probing audio devices, please wait...', 
            parent=self)
        self.popup.setStandardButtons(self.popup.NoButton)
        self.popup.setModal(True)
        self.deviceModel = QtGui.QStandardItemModel()
        self.deviceCombo.setModel(self.deviceModel)
        self.sampleRatesModel = QtGui.QStandardItemModel()
        self.sampleRatesList.setModel(self.sampleRatesModel)
        self.deviceCombo.currentIndexChanged.connect(self.deviceSelected)
        self.channelsModel = QtGui.QStandardItemModel()
        self.channelsList.setModel(self.channelsModel)

        for chk in (self.depth8Chk, self.depth16Chk, self.depth32Chk):
            chk.mousePressEvent = lambda *args: None
            chk.keyPressEvent = lambda *args: None

        for conversion, radio in enumerate((self.sinc_bestRadio, self.sinc_mediumRadio, 
            self.sinc_fastestRadio, self.zero_order_holdRadio, self.linearRadio)):
                self.sampleRateGroup.setId(radio, conversion)

        for size in bufferSizes:
            self.bufferCombo.addItem(str(size))

        self.reloadBtn.clicked.connect(self.probe)
        self.testDeviceBtn.clicked.connect(self.test)

    def deviceSelected(self, comboIndex):
        index = self.deviceModel.index(comboIndex, 0)
        self.deviceInfoBox.setEnabled(True)
        self.sampleRatesModel.clear()
        device = index.data(DeviceRole)
        self.buttonBox.button(self.buttonBox.Ok).setEnabled(True if index.data(ValidRole) != False else False)
        self.deviceInfoBox.setTitle('Properties of "{}"'.format(device.deviceName()))
        preferredFormat = index.data(FormatRole)
        if not preferredFormat:
            preferredFormat = device.preferredFormat()
        for sampleRate in sorted(index.data(SampleRateRole), reverse=True):
            item = QtGui.QStandardItem('{:.1f} kHz'.format(sampleRate/1000.))
            if sampleRate == preferredFormat.sampleRate():
                setItalic(item)
            if sampleRate == 44100:
                setBold(item)
            self.sampleRatesModel.appendRow(item)
        sampleSizes = index.data(SampleSizeRole)
        for sampleSize in (8, 16, 32):
            checkBox = getattr(self, 'depth{}Chk'.format(sampleSize))
            checkBox.setChecked(sampleSize in sampleSizes)
            setItalic(checkBox, sampleSize == preferredFormat.sampleSize())
            setBold(checkBox, sampleSize == 16)
        self.channelsModel.clear()
        for channelCount in sorted(index.data(ChannelsRole)):
            item = QtGui.QStandardItem('{}: {}'.format(channelCount, channelsLabels.get(channelCount, '(unknown configuration)')))
            setItalic(item, channelCount == preferredFormat.channelCount())
            setBold(item, channelCount == 2)
            self.channelsModel.appendRow(item)

    def test(self):
        device = self.deviceModel.item(self.deviceCombo.currentIndex()).data(DeviceRole)
        output = QtMultimedia.QAudioOutput(device, self.player.format, self)
        waveData = np.concatenate((sineValues(1, 256), ) * 100)
        waveData = np.multiply(waveData, 32768 * .5).astype('int16')
        buffer = QtCore.QBuffer(self)
        buffer.setData(waveData.tostring())
        buffer.open(QtCore.QIODevice.ReadOnly)
        buffer.seek(0)
        output.start(buffer)

    def probed(self, deviceList):
        self.popup.hide()
        self.deviceModel.clear()
        default = QtMultimedia.QAudioDeviceInfo.defaultOutputDevice()
        self.currentLbl.setText(self.player.audioDevice.deviceName())
        current = None
        for device, name, sampleRates, sampleSizes, channels in deviceList:
            deviceItem = QtGui.QStandardItem(name)
            if name == self.player.audioDevice.deviceName():
                current = deviceItem
            if device.deviceName() == default.deviceName():
                deviceItem.setText('{} (default)'.format(name))
            deviceItem.setData(device, DeviceRole)
            deviceItem.setData(sampleRates, SampleRateRole)
            deviceItem.setData(sampleSizes, SampleSizeRole)
            deviceItem.setData(channels, ChannelsRole)
            if not (sampleRates and sampleSizes and channels):
                deviceItem.setData(False, ValidRole)
                deviceItem.setEnabled(False)
            self.deviceModel.appendRow(deviceItem)
#        currentDeviceName = self.settings.value('AudioDevice')
        if current:
            self.deviceCombo.setCurrentIndex(self.deviceModel.indexFromItem(current).row())
#            if currentDeviceName:
#                match = self.deviceModel.match(self.deviceModel.index(0, 0), QtCore.Qt.DisplayRole, currentDeviceName, flags=QtCore.Qt.MatchExactly)
#                if not match:
#                    self.deviceList.setCurrentIndex(current.index())
#                else:
#                    self.deviceList.setCurrentIndex(match[0])
#            else:
#                self.deviceList.setCurrentIndex(current.index())

    def probe(self):
        self.popup.show()
        prober = AudioDeviceProber()
        proberThread = QtCore.QThread()
        prober.moveToThread(proberThread)
        proberThread.started.connect(prober.probe)
        prober.deviceList.connect(self.probed)
        prober.deviceList.connect(lambda _: [proberThread.quit(), prober.deleteLater(), proberThread.deleteLater()])
        proberThread.start()

    def exec_(self):
        self.sampleRateGroup.button(self.settings.value('SampleRateConversion', 2, type=int)).setChecked(True)

        self.bufferCombo.setCurrentIndex(bufferSizes.index(self.settings.value('BufferSize', defaultBufferSize, int)))
        self.show()
        self.probe()
        res = QtWidgets.QDialog.exec_(self)
        if not res:
            return res
        device = self.deviceCombo.itemData(self.deviceCombo.currentIndex(), DeviceRole)
        if device is not None:
            self.settings.setValue('AudioDevice', device.deviceName())
        conversion = self.sampleRateGroup.checkedId()
        if conversion == self.Fastest:
            self.settings.remove('SampleRateConversion')
        else:
            self.settings.setValue('SampleRateConversion', conversion)
        bufferSize = int(self.bufferCombo.currentText())
        if bufferSize != defaultBufferSize:
            self.settings.setValue('BufferSize', bufferSize)
        else:
            self.settings.remove('BufferSize')
        return device, conversion, bufferSize


class WaveIODevice(QtCore.QIODevice):
    finished = QtCore.pyqtSignal()

    def __init__(self, parent):
        QtCore.QIODevice.__init__(self, parent)
        self.player = parent
        self.inputWaveData = np.array([])
        self.currentWaveData = np.array([])
        self.currentSampleRate = 44100
        self.currentSampleSize = 16
        self.currentVolume = 1.
        self.byteArray = QtCore.QByteArray()
        self.bytePos = 0
        self.clean = False
        self.player.dirty.connect(self.setDirty)

    def setDirty(self):
        self.clean = False

    def stop(self):
        self.bytePos = 0
        self.close()

    def volumeMultiplier(self, volume):
        if volume == 1:
            return 1.
        elif volume < 1:
            return pow(2.0, (sqrt(sqrt(sqrt(volume))) * 192 - 192.)/6.0)
        else:
            return 1 + sin((volume - 1) * pi / 2)

    def setWaveFileData(self, waveData, info, volume):
        if waveData is not self.inputWaveData or info.samplerate != self.player.sampleRate:
            if waveData is not self.inputWaveData:
                self.inputWaveData = waveData.copy()

            if info.samplerate != self.player.sampleRate:
                #ratio is output/input
                waveData = samplerate.resample(waveData, self.player.sampleRate / float(info.samplerate), 0)

            if info.channels == 1:
                waveData = waveData.repeat(2, axis=1)/2
            elif info.channels == 2:
                pass
            elif info.channels == 3:
                front = waveData[:, [0, 1]]/1.5
                center = waveData[:, [2]].repeat(2, axis=1)/2
                waveData = front + center
            elif info.channels == 4:
                front = waveData[:, [0, 1]]/2
                rear = waveData[:, [2, 3]]/2
                waveData = front + rear
            elif info.channels == 5:
                front = waveData[:, [0, 1]]/2.5
                rear = waveData[:, [2, 3]]/2.5
                center = waveData[:, [4]].repeat(2, axis=1)/2
                waveData = front + rear + center
            elif info.channels == 6:
                front = waveData[:, [0, 1]]/3
                rear = waveData[:, [2, 3]]/3
                center = waveData[:, [4]].repeat(2, axis=1)/2
                sub = waveData[:, [5]].repeat(2, axis=1)/2
                waveData = front + rear + center + sub
            if self.player.sampleSize == 16:
                waveData = (waveData * 32767).astype('int16')
            self.currentWaveData = waveData.copy()

#        if volume != self.currentVolume:
#            #I really don't know why changing waveData and appending it to the
#            #byteArray works only the first time... Let numpy take care of it.
##            self.currentWaveData /= self.currentVolume
##            self.currentWaveData *= volume
#            volume = self.volumeMultiplier(volume)
#            self.currentWaveData = np.multiply(
#                np.divide(
#                    self.currentWaveData, self.currentVolume, out=self.currentWaveData, casting='unsafe'), 
#                volume, out=self.currentWaveData, casting='unsafe')
#            self.currentVolume = volume

        waveData = np.multiply(self.currentWaveData, volume).astype('int16')

        self.byteArray.clear()
        self.byteArray.append(waveData.tostring())
        self.bytePos = 0
        self.infinite = False
        self.open(QtCore.QIODevice.ReadOnly)

    def setWaveData(self, waveData, volume, preview=False):
        if not np.array_equal(waveData, self.inputWaveData) or volume != self.currentVolume or not self.clean:
            if preview:
                volume = self.volumeMultiplier(volume)
                waveData = waveData.repeat(2) * .5
            else:
                waveData = waveData.copy()
            self.inputWaveData = waveData
#            if self.currentSampleRate != self.player.sampleRate and self.player.sampleRate != 48000:
#                #ratio is output/input
#                waveData = samplerate.resample(waveData, self.player.sampleRate / 48000., 0)
            self.currentSampleRate = self.player.sampleRate
#            if self.currentSampleSize != self.player.sampleSize or self.player.sampleSize == 16:
#                waveData = (waveData * 32768).astype('int16')
            self.currentSampleSize = self.player.sampleSize
            if volume != self.currentVolume:
#                waveData /= self.currentVolume
                self.currentVolume = volume
#            waveData *= volume
            waveData = np.multiply(waveData, volume * 32768.).astype('int16')
            self.clean = True
            self.currentWaveData = waveData
        self.byteArray.clear()
        self.byteArray.append(self.currentWaveData.tostring())
        self.bytePos = 0
        self.infinite = not preview
        self.open(QtCore.QIODevice.ReadOnly)

    def seekPos(self, pos):
        self.bytePos = int(self.byteArray.size() * pos) // self.player.sampleSize * self.player.sampleSize
#        print(pos, self.byteArray.size())

    def readData(self, maxlen):
        if self.bytePos >= self.byteArray.size():
            self.finished.emit()
            return None

        data = QtCore.QByteArray()
        total = 0

        arraySize = self.byteArray.size()
        while maxlen > total and self.bytePos < arraySize:
            chunk = min(arraySize - self.bytePos, maxlen - total)
            data.append(self.byteArray.mid(self.bytePos, chunk))
#            self.bytePos = (self.bytePos + chunk) % self.byteArray.size()
            self.bytePos += chunk
            total += chunk

        if self.infinite and self.bytePos >= arraySize:
            self.bytePos = 0

        return data.data()


class Player(QtCore.QObject):
    stateChanged = QtCore.pyqtSignal(object)
    dirty = QtCore.pyqtSignal()
#    notify = QtCore.pyqtSignal(float)
    started = QtCore.pyqtSignal()
    stopped = QtCore.pyqtSignal()
    paused = QtCore.pyqtSignal()

    def __init__(self, main, audioDeviceName=None, sampleRateConversion=2):
        QtCore.QObject.__init__(self)
        self.main = main
#        self.audioBufferArray = QtCore.QBuffer(self)
        self.waveIODevice = WaveIODevice(self)
        #for some reason, on windows (or Wine? and OSX?) stateChanged 
        #is not emitted at the end of file buffer...
        if sys.platform == 'win32':
            self.waveIODevice.finished.connect(self.checkFinished)
        self.output = None
        self.audioDevice = None
        self.settings = QtCore.QSettings()

        self.format = QtMultimedia.QAudioFormat()
        self.format.setSampleRate(44100)
        self.format.setChannelCount(2)
        self.format.setSampleSize(16)
        self.format.setCodec('audio/pcm')
        self.format.setByteOrder(QtMultimedia.QAudioFormat.LittleEndian)
        self.format.setSampleType(QtMultimedia.QAudioFormat.SignedInt)

        self.setAudioDeviceByName(audioDeviceName)
        self.setAudioDevice()
        self.sampleRateConversion = sampleRateConversion

    def checkFinished(self):
        if self.output.bytesFree() >= self.output.bufferSize():
            self.output.stop()

    def seekPos(self, pos):
        if pos < 0:
            pos = 0
        if pos > 1:
            pos = 1
        self.waveIODevice.seekPos(pos)

    def setSampleRateConversion(self, sampleRateConversion=2):
        self.sampleRateConversion = sampleRateConversion
        self.dirty.emit()

    def setBufferSize(self, bufferSize=defaultBufferSize):
        self.output.setBufferSize(bufferSize)

    def setAudioDeviceByName(self, audioDeviceName):
        defaultDevice = QtMultimedia.QAudioDeviceInfo.defaultOutputDevice()
        if not audioDeviceName:
            self.audioDevice = defaultDevice
        elif audioDeviceName == defaultDevice:
            self.audioDevice = defaultDevice
        else:
            for sysDevice in QtMultimedia.QAudioDeviceInfo.availableDevices(QtMultimedia.QAudio.AudioOutput):
                if sysDevice.deviceName() == audioDeviceName:
                    break
            else:
                sysDevice = defaultDevice
            self.audioDevice = sysDevice
#        self.audioDeviceName = audioDeviceName if audioDeviceName else QtMultimedia.QaudioDeviceInfo.defaultOutputDevice()

    def setAudioDevice(self, audioDevice=None):
        if audioDevice:
            self.audioDevice = audioDevice
#        sampleSize = 32 if 32 in self.audioDevice.supportedSampleSizes() else 16
        sampleSize = 16
#        sampleRate = 48000 if 48000 in self.audioDevice.supportedSampleRates() else 44100
        sampleRate = 44100

        if not self.audioDevice.isFormatSupported(self.format):
            self.format = self.audioDevice.nearestFormat(self.format)
            #do something else with self.audioDevice.nearestFormat(format)?
        self.sampleSize = self.format.sampleSize()
        self.sampleRate = self.format.sampleRate()
        try:
            self.output.notify.disconnect()
            del self.output
        except:
            pass
        self.output = QtMultimedia.QAudioOutput(self.audioDevice, self.format)

        self.output.setNotifyInterval(25)
        self.output.stateChanged.connect(self.stateChanged)
        self.output.setBufferSize(self.settings.value('BufferSize', defaultBufferSize, int))
        self.dirty.emit()
        self.notify = self.output.notify

    def isPlaying(self):
        return self.output.state() == QtMultimedia.QAudio.ActiveState

    def isPaused(self):
        return self.output.state() == QtMultimedia.QAudio.SuspendedState

    def isActive(self):
        return self.output.state() in (QtMultimedia.QAudio.ActiveState, QtMultimedia.QAudio.SuspendedState)

    def stateChanged(self, state):
#        print('statechanged')
        if state in (QtMultimedia.QAudio.StoppedState, QtMultimedia.QAudio.IdleState):
            self.stopped.emit()
        elif state == QtMultimedia.QAudio.ActiveState:
            self.started.emit()
        else:
            self.paused.emit()

    def stop(self):
        self.output.stop()
        self.waveIODevice.stop()

    def playWaveFile(self, waveData, info, volume=1):
        self.waveIODevice.setWaveFileData(waveData, info, volume)
#        self.output.start(self.audioBufferArray)
        self.output.start(self.waveIODevice)

    def playData(self, waveData, volume=1, preview=False):
        self.waveIODevice.setWaveData(waveData, volume, preview)
        self.output.start(self.waveIODevice)

    def pause(self):
        self.output.suspend()

    def resume(self):
        self.output.resume()

    def setVolume(self, volume):
#        try:
#            volume = QtMultimedia.QAudio.convertVolume(volume / 100, QtMultimedia.QAudio.LogarithmicVolumeScale, QtMultimedia.QAudio.LinearVolumeScale)
#        except:
#            if volume >= 100:
#                volume = 1
#            else:
#                volume = -log(1 - volume/100) / 4.60517018599
        self.output.setVolume(volume/100)

