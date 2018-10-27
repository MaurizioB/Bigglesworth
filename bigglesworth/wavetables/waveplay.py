import sys
from collections import namedtuple
from math import sin, pi, sqrt
import datetime
currentTime = datetime.datetime.now

import samplerate
import numpy as np
from Qt import QtCore, QtGui, QtWidgets, QtMultimedia
import pyaudio

from bigglesworth.utils import loadUi, setBold, setItalic
from bigglesworth.wavetables.utils import sineValues, defaultBufferSize

sampleRates = [
    8000, 
    11025, 
    22050, 
    44100, 
    48000, 
    96000, 
]

bufferSizes = [
    1024, 
    2048, 
    4096, 
    8192, 
    16384, 
    32768, 
    65536, 
]

paSampleSizes = {
    8: pyaudio.paInt8, 
    16: pyaudio.paInt16, 
    32: pyaudio.paFloat32, 
}

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


class PyAudioFormat(object):
    _rates = _counts = -1
    _sampleRate = 44100
    _channelCount = 2
    _sampleSize = 16

    def __init__(self, audioDevice=None):
        self.audioDevice = audioDevice

    def sampleSize(self):
        return self._sampleSize

    def sampleRate(self):
        if not self.audioDevice:
            return self._sampleRate
        if self._rates == -1:
            self._rates = self.audioDevice.supportedChannelCounts()
        if 44100 in self._rates:
            return 44100
        return max(self._rates)

    def channelCount(self):
        if not self.audioDevice:
            return self._channelCount
        if self._counts == -1:
            self._counts = self.audioDevice.supportedChannelCounts()
        if 2 in self._counts:
            return 2
        return max(self._counts)


class PyAudioDevice(object):
    def __init__(self, index=None):
        self.interface = pyaudio.PyAudio()
        if index is not None:
            self.index = index
        else:
            self.index = self.interface.get_default_output_device_info()['index']
        self.info = self.interface.get_device_info_by_index(self.index)
        self.defaultSampleRate = int(self.info['defaultSampleRate'])
        self._preferredFormat = PyAudioFormat(self)

    def api(self):
        return self.interface.get_host_api_info_by_index(self.info['hostApi'])['name']

    def isFormatSupported(self, format):
        return all([
            format.sampleRate() in self.supportedSampleRates(), 
            format.channelCount() in self.supportedChannelCounts(), 
            format.sampleSize() in self.supportedSampleSizes()
            ])

    def nearestFormat(self, format):
        rates = self.supportedSampleRates()
        if not format.sampleRate() in rates:
            for rate in reversed(sampleRates):
                if rate in rates:
                    break
        counts = self.supportedChannelCounts()
        if not format.channelCount() in counts:
            for c in range(8, 0, -1):
                if c in counts:
                    break
        sizes = self.supportedSampleSizes()
        if not format.sampleSize() in sizes:
            for s in (32, 16, 8):
                if s in sizes:
                    break
        format = PyAudioFormat()
        format._sampleRate = rate
        format._channelCount = c
        format._sampleSize = s
        return format

    def preferredFormat(self):
        return self._preferredFormat

    def isOutput(self):
        return self.info['maxOutputChannels']

    def deviceName(self):
        return self.info['name']

    def supportedSampleRates(self):
        rates = []
        for rate in sampleRates:
            try:
                self.interface.is_format_supported(
                    rate, 
                    output_device=self.index, 
                    output_channels=2, 
                    output_format=pyaudio.paInt16
                    )
                rates.append(rate)
            except:
                pass
        return rates

    def supportedSampleSizes(self):
        sizes = []
        for paFormat, size in ((pyaudio.paInt8, 8), (pyaudio.paInt16, 16), (pyaudio.paFloat32, 32)):
            try:
                self.interface.is_format_supported(
                    self.defaultSampleRate, 
                    output_device=self.index, 
                    output_channels=2, 
                    output_format=paFormat
                    )
                sizes.append(size)
            except:
                pass
        return sizes

    def supportedChannelCounts(self):
        channels = []
        for c in range(1, 9):
            try:
                self.interface.is_format_supported(
                    self.defaultSampleRate, 
                    output_device=self.index, 
                    output_channels=c, 
                    output_format=pyaudio.paInt16
                    )
                channels.append(c)
            except:
                pass
        return channels


class PyAudioOutput(QtCore.QObject):
    notify = QtCore.pyqtSignal(float)
    stateChanged = QtCore.pyqtSignal(int)
    ActiveState, SuspendedState, StoppedState, IdleState = range(4)

    def __init__(self, audioDevice, format, parent=None, bufferSize=1024):
        QtCore.QObject.__init__(self, parent)
        self.audioDevice = audioDevice
        self.format = format
        self.pyaudio = pyaudio.PyAudio()
        self.chunkSize = 512
        self.channelCount = format.channelCount()
        self.sampleRate = format.sampleRate()
        self.sampleSize = format.sampleSize()
        self.paSampleSize = paSampleSizes[self.sampleSize]
        self.stream = None
        self._currentState = self.StoppedState
        self.currentTime = 0
        self.bufferSize = bufferSize

    @property
    def currentState(self):
        return self._currentState

    @currentState.setter
    def currentState(self, state):
        self._currentState = state
        self.stateChanged.emit(state)

    def initialize(self):
        self.stream = self.pyaudio.open(
            channels=self.channelCount, 
            format=self.paSampleSize, 
            rate=self.sampleRate, 
            frames_per_buffer=self.bufferSize, 
            output_device_index=self.audioDevice.index, 
            output=True, 
            start=False, 
            stream_callback=self.readData
            )

    def readData(self, _, frameCount, timeInfo, status):
        data = self.waveIODevice.readData(frameCount * 4)
        if data:
            self.notify.emit((currentTime() - self.currentTime).total_seconds())
            return data, pyaudio.paContinue
        self.currentState = self.StoppedState
        try:
            self.waveIODevice.stop()
        except:
            pass
        return None, pyaudio.paComplete

    def start(self, waveIODevice):
        #since the audio settings dialog can create lots of audio outputs, the stream
        #is created only when actually needed.
        if not self.stream:
            self.initialize()
        self.waveIODevice = waveIODevice
        self.currentTime = currentTime()
        #if the data returned from a previous readData did not fill the buffer, the stream
        #is still "open", even if not is_active.
        if not self.stream.is_stopped():
            self.stream.stop_stream()
        self.stream.start_stream()
        self.currentState = self.ActiveState

    def suspend(self):
        self.stream.stop_stream()
        self.suspendTime = currentTime()
        self.currentState = self.SuspendedState

    def resume(self):
        self.currentTime += currentTime() - self.suspendTime
        self.stream.start_stream()
        self.currentState = self.ActiveState

    def stop(self):
        if self.stream:
            self.stream.stop_stream()
            try:
                self.waveIODevice.stop()
            except:
                pass
        self.currentState = self.StoppedState

    def state(self):
        return self.currentState


class AudioDeviceProber(QtCore.QObject):
    deviceList = QtCore.pyqtSignal(object)

    def probeQt(self):
        deviceList = []
        for device in QtMultimedia.QAudioDeviceInfo.availableDevices(QtMultimedia.QAudio.AudioOutput):
            deviceInfo = audioDevice(device, device.deviceName(), device.supportedSampleRates(), device.supportedSampleSizes(), device.supportedChannelCounts())
            deviceList.append(deviceInfo)
        self.deviceList.emit(deviceList)

    def probePy(self):
        deviceList = []
        audio = pyaudio.PyAudio()
        for index in range(audio.get_device_count()):
            device = PyAudioDevice(index)
            if not device.isOutput():
                continue
            deviceInfo = audioDevice(device, device.deviceName(), device.supportedSampleRates(), device.supportedSampleSizes(), device.supportedChannelCounts())
            deviceList.append(deviceInfo)
        self.deviceList.emit(deviceList)


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

        self.backend = self.player.backend
        if self.backend == 'qt':
            self.qtMultimediaRadio.setChecked(True)
        else:
            self.pyAudioRadio.setChecked(True)
        self.backendDict = {self.qtMultimediaRadio: 'qt', self.pyAudioRadio: 'py'}
        self.backendGroup.buttonClicked.connect(self.setBackend)

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
        self.testOutput = None

    def setBackend(self, radio):
        backend = self.backendDict[radio]
        if backend == self.backend:
            return
        self.backend = backend
        self.bufferSizeWidget.setEnabled(self.backend == 'qt')
        self.probe()

    def deviceSelected(self, comboIndex):
        index = self.deviceModel.index(comboIndex, 0)
        self.deviceInfoBox.setEnabled(True)
        self.sampleRatesModel.clear()
        device = index.data(DeviceRole)
        self.buttonBox.button(self.buttonBox.Ok).setEnabled(True if index.data(ValidRole) != False else False)
        self.deviceNameLbl.setText(device.deviceName())
        if self.backend == 'qt':
            self.apiTypeLbl.setVisible(False)
            self.apiLbl.setVisible(False)
        else:
            self.apiTypeLbl.setVisible(True)
            self.apiLbl.setVisible(True)
            self.apiTypeLbl.setText(device.api())
        preferredFormat = index.data(FormatRole)
        if not preferredFormat:
            preferredFormat = device.preferredFormat()
        for sampleRate in sorted(index.data(SampleRateRole), reverse=True):
            item = QtGui.QStandardItem('{:.03f}'.format(sampleRate/1000.).rstrip('0').rstrip('.') + ' kHz')
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
        if self.backend == 'qt':
            self.testOutput = QtMultimedia.QAudioOutput(device, self.player.format, self)
        else:
            self.testOutput = PyAudioOutput(device, self.player.format, self)
        sineBase = np.tile(sineValues(1, 256), 4)
        attack = np.concatenate([np.multiply(sineBase, x * .05) for x in range(20)])
        sustain = np.tile(sineBase, 80)
        decay = np.concatenate([np.multiply(sineBase, x * .05) for x in range(19, -1, -1)])
        waveData = np.concatenate((attack, sustain, decay, np.multiply(sineBase, 0)))
        waveData = np.multiply(waveData, 32768 * .5).astype('int16')
        buffer = QtCore.QBuffer(self)
        buffer.setData(waveData.tostring())
        buffer.open(QtCore.QIODevice.ReadOnly)
        buffer.seek(0)
        try:
            self.testOutput.start(buffer)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, 'Device error', 
                'There was an error while testing the device "{}":<br/>{}'.format(device.deviceName(), e), 
                QtWidgets.QMessageBox.Ok)
            invalid = self.deviceCombo.currentIndex()
            self.deviceModel.item(invalid).setEnabled(False)
            indexes = []
            for index in range(self.deviceModel.rowCount()):
                if self.deviceModel.item(index).isEnabled():
                    indexes.append(index)
                    break
            else:
                self.testDeviceBtn.setEnabled(False)
                return
            interface = pyaudio.PyAudio()
            if self.backend != 'qt':
                default = interface.get_default_output_device_info()
                for row in range(self.deviceModel.rowCount()):
                    if self.deviceModel.item(row).data(DeviceRole).deviceName() == default['name']:
                        indexes.insert(0, row)
            self.deviceCombo.setCurrentIndex(indexes[0])

    def probed(self, deviceList):
        self.popup.hide()
        self.deviceModel.clear()
        if self.backend == 'qt':
            default = QtMultimedia.QAudioDeviceInfo.defaultOutputDevice()
        else:
            default = PyAudioDevice()
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
        if current:
            self.deviceCombo.setCurrentIndex(self.deviceModel.indexFromItem(current).row())

    def probe(self):
        self.popup.show()
        prober = AudioDeviceProber()
        self.proberThread = QtCore.QThread()
        prober.moveToThread(self.proberThread)
        self.proberThread.started.connect(prober.probeQt if self.backend == 'qt' else prober.probePy)
        prober.deviceList.connect(self.probed)
        prober.deviceList.connect(lambda _: [self.proberThread.quit(), prober.deleteLater()])
        self.proberThread.start()

    def exec_(self):
        self.sampleRateGroup.button(self.settings.value('SampleRateConversion', 2, type=int)).setChecked(True)

        self.bufferCombo.setCurrentIndex(bufferSizes.index(self.settings.value('BufferSize', defaultBufferSize, int)))
        self.show()
        self.probe()
        self.bufferSizeWidget.setEnabled(self.backend == 'qt')
        res = QtWidgets.QDialog.exec_(self)
        if self.testOutput:
            self.testOutput.stop()
        if not res:
            return res
        #TODO: delete the other device objects to free memoryi?
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
        return self.backend, device, conversion, bufferSize


class WaveIODevice(QtCore.QIODevice):
    finished = QtCore.pyqtSignal()

    def __init__(self, parent):
        QtCore.QIODevice.__init__(self, parent)
        self.player = parent
        self.inputWaveData = np.array([])
        self.currentWaveData = np.array([])
        self.outputWaveData = np.array([])
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

    def setVolume(self, volume):
        self.outputWaveData = np.multiply(self.currentWaveData, self.volumeMultiplier(volume)).astype('int16')

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

        self.outputWaveData = np.multiply(self.currentWaveData, self.volumeMultiplier(volume)).astype('int16')

        self.bytePos = 0

        self.waveLength = len(self.currentWaveData) * 4
        self.waveMultiplier = 4

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
            waveData = np.multiply(waveData, 32768.).astype('int16')
            self.clean = True
            self.currentWaveData = waveData

        self.outputWaveData = np.multiply(self.currentWaveData, volume).astype('int16')

        self.bytePos = 0
        self.waveLength = len(self.currentWaveData)
        self.waveMultiplier = 2
        self.infinite = not preview
        self.open(QtCore.QIODevice.ReadOnly)

    def seekPos(self, pos):
        self.bytePos = int(self.waveLength * pos) // self.player.sampleSize * self.player.sampleSize

    def readData(self, maxlen):
        if self.bytePos >= self.waveLength:
            self.finished.emit()
            return None

        nextPos = self.bytePos + maxlen / self.waveMultiplier
        data = self.outputWaveData[self.bytePos:nextPos]

        if self.infinite and nextPos >= self.waveLength:
            nextPos = maxlen / self.waveMultiplier - len(data)
            data = np.concatenate((data, self.outputWaveData[:nextPos]))

        self.bytePos = nextPos
        
        return data.tostring()


class Player(QtCore.QObject):
    stateChanged = QtCore.pyqtSignal(object)
    dirty = QtCore.pyqtSignal()
#    notify = QtCore.pyqtSignal(float)
    started = QtCore.pyqtSignal()
    stopped = QtCore.pyqtSignal()
    paused = QtCore.pyqtSignal()

    ActiveState, SuspendedState, StoppedState, IdleState = range(4)

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

        self.backend = self.settings.value('AudioBackend', 'qt' if 'linux' in sys.platform else 'py', str)

        self.format = self.getDefaultFormat(self.backend)

        if self.backend == 'qt':
            self.setAudioDeviceByNameQt(audioDeviceName)
        else:
            self.pyaudio = pyaudio.PyAudio()
            self.setAudioDeviceByNamePy(audioDeviceName)

        self.setAudioDevice()
        self.sampleRateConversion = sampleRateConversion

    def getDefaultFormat(self, backend):
        if backend == 'qt':
            format = QtMultimedia.QAudioFormat()
            format.setSampleRate(44100)
            format.setChannelCount(2)
            format.setSampleSize(16)
            format.setCodec('audio/pcm')
            format.setByteOrder(QtMultimedia.QAudioFormat.LittleEndian)
            format.setSampleType(QtMultimedia.QAudioFormat.SignedInt)
        else:
            format = PyAudioFormat()
        return format

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
        if self.backend == 'qt':
            self.output.setBufferSize(bufferSize)
#        else:
#            self.output = self.output.clone(bufferSize=bufferSize)

    def setAudioDeviceByNameQt(self, audioDeviceName):
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

    def setAudioDeviceByNamePy(self, audioDeviceName):
        defaultDevice = PyAudioDevice(self.pyaudio.get_default_output_device_info()['index'])
        if not audioDeviceName:
            self.audioDevice = defaultDevice
        elif audioDeviceName == defaultDevice:
            self.audioDevice = defaultDevice
        else:
            for index in range(self.pyaudio.get_device_count()):
                if self.pyaudio.get_device_info_by_index(index)['name'] == audioDeviceName:
                    sysDevice = PyAudioDevice(index)
                    break
            else:
                sysDevice = defaultDevice
            self.audioDevice = sysDevice

    def setAudioDevice(self, audioDevice=None, backend=None):
        if audioDevice:
            self.audioDevice = audioDevice
        if backend is not None:
            self.backend = backend

        try:
            self.output.notify.disconnect()
            del self.output
        except:
            pass

        if (isinstance(self.format, PyAudioFormat) and self.backend == 'qt') or \
            (isinstance(self.format, QtMultimedia.QAudioFormat) and self.backend == 'py'):
                self.format = self.getDefaultFormat(self.backend)
        if not self.audioDevice.isFormatSupported(self.format):
            self.format = self.audioDevice.nearestFormat(self.format)
            #do something else with self.audioDevice.nearestFormat(format)?

        self.sampleSize = self.format.sampleSize()
        self.sampleRate = self.format.sampleRate()

        if self.backend == 'qt':
            bufferSize = self.settings.value('BufferSize', defaultBufferSize, int)
            self.output = QtMultimedia.QAudioOutput(self.audioDevice, self.format)
            self.output.setBufferSize(bufferSize)
            self.output.setNotifyInterval(25)
        else:
            self.output = PyAudioOutput(self.audioDevice, self.format)

        self.output.stateChanged.connect(self.stateChanged)
        self.notify = self.output.notify
        self.dirty.emit()

    def isPlaying(self):
        return self.output.state() == self.ActiveState

    def isPaused(self):
        return self.output.state() == self.SuspendedState

    def isActive(self):
        return self.output.state() in (self.ActiveState, self.SuspendedState)

    def stateChanged(self, state):
#        print('statechanged')
        if state in (self.StoppedState, self.IdleState):
            self.stopped.emit()
        elif state == self.ActiveState:
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
        self.waveIODevice.setVolume(volume * .01)
