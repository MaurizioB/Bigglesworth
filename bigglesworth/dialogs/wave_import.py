#!/usr/bin/env python2.7
# *-* coding: utf-8 *-*

import wave, audioop
from PyQt4 import QtGui, QtCore, QtMultimedia

from bigglesworth.utils import load_ui

def secs2time(secs):
    min, sec = divmod(secs, 60)
    intsec = int(sec)
    return '{:02}\' {:02}" {:.03}'.format(int(min), intsec, str(sec-intsec)[2:])


class WaveImportSceneView(QtGui.QGraphicsView):
    def __init__(self, *args, **kwargs):
        QtGui.QGraphicsView.__init__(self, *args, **kwargs)
        self.scene = QtGui.QGraphicsScene()
        self.setScene(self.scene)
        self.setRenderHints(QtGui.QPainter.Antialiasing)
        self.setMinimumHeight(128)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setSizePolicy(QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.Fixed)
        self.setBackgroundBrush(QtCore.Qt.lightGray)
        self.pen = QtGui.QPen(QtGui.QColor(QtCore.Qt.darkGray), 2)

        self.wavepath = None

    def setWave(self, stream):
        if self.wavepath:
            self.scene.removeItem(self.wavepath)
            self.fitInView(0, 0, 1, 1)
        if stream.getnchannels() == 2:
            self.setStereoWave(stream)
        else:
            self.setMonoWave(stream)

    def setStereoWave(self, stream):
        sampwidth = stream.getsampwidth()
        left_delta = 2**(8 * sampwidth)
        right_delta = left_delta * 2
        frames = stream.getnframes()
        ratio = frames / 255
        data = stream.readframes(float('inf'))
        left_data = audioop.tomono(data, sampwidth, 1, 0)
        right_data = audioop.tomono(data, sampwidth, 0, 1)
        wavepath = QtGui.QPainterPath()
        try:
            for frame_set in xrange(256):
                left_min = left_max = right_min = right_max = 0
                for frame in xrange(ratio):
                    try:
                        pos = frame + frame_set * ratio
                        left_value = audioop.getsample(left_data, sampwidth, pos)
                        left_min = min(left_min, left_value)
                        left_max = max(left_max, left_value)
                        right_value = audioop.getsample(right_data, sampwidth, pos)
                        right_min = min(right_min, right_value)
                        right_max = max(right_max, right_value)
                    except:
                        break
                wavepath.moveTo(frame_set, left_delta - left_min)
                wavepath.lineTo(frame_set, left_delta - left_max)
                wavepath.moveTo(frame_set, right_delta - right_min)
                wavepath.lineTo(frame_set, right_delta - right_max)
#                left_wavepath.lineTo(frame, left_sampwidth_int - left_value)
#                right_wavepath.lineTo(frame, right_sampwidth_int - right_value)
        except:
            pass
#        left_wavepath.addPath(right_wavepath)
        self.wavepath = self.scene.addPath(wavepath)
        self.wavepath.setPen(self.pen)
        self.fitInView(0, 0, 256, right_delta)
        self.centerOn(self.wavepath)
        self.setBackgroundBrush(QtCore.Qt.white)

    def setMonoWave(self, stream):
        sampwidth = stream.getsampwidth()
        delta = 2**(8*sampwidth)
        frames = stream.getnframes()
        ratio = frames / 255
        data = stream.readframes(float('inf'))
        wavepath = QtGui.QPainterPath()
        try:
            for frame_set in xrange(256):
                frame_min = frame_max = 0
                for frame in xrange(ratio):
                    try:
                        value = audioop.getsample(data, sampwidth, frame + frame_set * ratio)
                        frame_min = min(frame_min, value)
                        frame_max = max(frame_max, value)
                    except:
                        break
                wavepath.moveTo(frame_set, delta - frame_min)
                wavepath.lineTo(frame_set, delta - frame_max)
        except:
            pass
        self.wavepath = self.scene.addPath(wavepath)
        self.wavepath.setPen(self.pen)
        self.wavepath.setY(delta * .5)
        self.fitInView(0, 0, 256, delta)
        self.centerOn(self.wavepath)
        self.setBackgroundBrush(QtCore.Qt.white)

    def clear(self):
        self.setBackgroundBrush(QtCore.Qt.lightGray)
        if self.wavepath:
            self.scene.removeItem(self.wavepath)
            self.fitInView(0, 0, 1, 1)
            del self.wavepath
            self.wavepath = None


class WavePanel(QtGui.QWidget):
    isValid = QtCore.pyqtSignal(bool)

    def __init__(self, *args, **kwargs):
        QtGui.QWidget.__init__(self, *args, **kwargs)
        load_ui(self, 'dialogs/wave_panel.ui')
        width = self.fontMetrics().width('8'*32)
        self.setMinimumWidth(width)
        self.setMaximumWidth(width)

        self.stream = None
        self.output = None
        self.file = None

        icon = self.style().standardIcon(QtGui.QStyle.SP_MessageBoxWarning)
        self.info_icon.setPixmap(icon.pixmap(16, 16))
        self.info_icon.setVisible(False)

        self.info_lbl.setMinimumHeight(self.info_lbl.fontMetrics().lineSpacing()*2)
        self.play_btn.clicked.connect(self.play_toggle)
        self.pause_btn.toggled.connect(self.pause_toggle)

    def clear_labels(self):
        for lbl in (self.channels_lbl, self.framerate_lbl, self.frames_lbl, self.sampwidth_lbl, self.length_lbl):
            lbl.setText('')

    def setWave(self, file):
        try:
            wavestream = wave.open(str(file.toUtf8()))
            self.file = file
            self.info_lbl.setText('')
        except wave.Error:
            self.file = None
            self.stream = None
            self.info_lbl.setText('Unknown or unsupported format')
            self.clear_labels()
            self.set_valid(False)
            self.info_icon.setVisible(True)
            return
        except:
            self.file = None
            self.stream = None
            self.info_lbl.setText('')
            self.clear_labels()
            self.set_valid(False)
            self.info_icon.setVisible(False)
            return
        channels = wavestream.getnchannels()
        sampwidth = wavestream.getsampwidth()
        if channels == 1:
            chan_txt = 'Mono'
        elif channels == 2:
            chan_txt = 'Stereo'
        else:
            chan_txt = str(channels)
        framerate = wavestream.getframerate()
        frames = wavestream.getnframes()
        length = frames/float(framerate)
        self.channels_lbl.setText(chan_txt)
        self.sampwidth_lbl.setText('{} bit'.format(sampwidth*8))
        self.framerate_lbl.setText('{} Hz'.format(framerate))
        self.frames_lbl.setText(str(frames))
        self.length_lbl.setText(secs2time(length))
        if channels > 2:
            self.info_lbl.setText('Too many channels: only mono or stereo files are supported.')
            self.info_icon.setVisible(True)
            self.set_valid(False)
        elif sampwidth > 2:
            self.info_lbl.setText('Only 8bit and 16 bit sample resolutions are accepted.')
            self.info_icon.setVisible(True)
            self.set_valid(False)
        elif length > 60:
            self.info_lbl.setText('File too long, please select a file with length less than a minute.')
            self.info_icon.setVisible(True)
            self.set_valid(False)
        else:
            self.set_valid(file, wavestream)

    def set_valid(self, file, stream=None):
        if file is False:
            if self.output:
                try:
                    self.output.deleteLater()
                except:
                    pass
            self.wave_view.clear()
            self.file = None
            self.stream = None
            self.play_btn.setEnabled(False)
            self.pause_btn.setEnabled(False)
            self.isValid.emit(False)
        else:
            self.wave_view.setWave(stream)
            self.file = file
            self.stream = stream
            self.play_btn.setEnabled(True)
            if self.autoplay_chk.isChecked():
                self.play_btn.setChecked(True)
                self.play_toggle(True)
            self.info_icon.setVisible(False)
            self.isValid.emit(True)

    def pause_toggle(self, state):
        if self.output.state() == QtMultimedia.QAudio.ActiveState:
            self.output.suspend()
        elif self.output.state() == QtMultimedia.QAudio.SuspendedState:
            self.output.resume()

    def play_toggle(self, state):
        if not self.stream: return
        if not state:
            self.output.stop()
            self.pause_btn.setEnabled(False)
            self.pause_btn.setChecked(False)
            if self.output:
                try:
                    self.output.deleteLater()
                except:
                    pass
            return
        format = QtMultimedia.QAudioFormat()
        format.setChannels(self.stream.getnchannels())
        format.setFrequency(self.stream.getframerate())
        format.setSampleSize(self.stream.getsampwidth()*8)
        format.setCodec("audio/pcm")
        format.setByteOrder(QtMultimedia.QAudioFormat.LittleEndian)
        format.setSampleType(QtMultimedia.QAudioFormat.SignedInt)
        if self.output:
            try:
                self.output.deleteLater()
            except:
                pass
        self.output = QtMultimedia.QAudioOutput(format, self)
        self.output.stateChanged.connect(self.stop)
        buffer = QtCore.QBuffer(self)
        data = QtCore.QByteArray()
        self.stream.rewind()
        data.append(self.stream.readframes(float('inf')))
        buffer.setData(data)
        buffer.open(QtCore.QIODevice.ReadOnly)
        buffer.seek(0)
        self.output.start(buffer)
        self.pause_btn.setEnabled(True)

    def stop(self, state):
        if state == QtMultimedia.QAudio.IdleState:
            self.play_btn.setChecked(False)
            self.pause_btn.setEnabled(False)
            self.output.deleteLater()


class WaveLoad(QtGui.QFileDialog):
    def __init__(self, main, *args, **kwargs):
        QtGui.QFileDialog.__init__(self, *args, **kwargs)
        self.setDirectory('/home/mauriziob/data/code/blofeld/test/')
        self.main = main
        self.setOption(self.DontUseNativeDialog)
        self.setAcceptMode(self.AcceptOpen)
        self.setFileMode(self.ExistingFile)
        self.buttonBox = self.findChildren(QtGui.QDialogButtonBox)[0]
        self.open_btn = [b for b in self.buttonBox.buttons() if self.buttonBox.buttonRole(b) == QtGui.QDialogButtonBox.AcceptRole][0]
        self.setNameFilters(('Wave files (*.wav)', 'Any files (*)'))
        self.setSidebarUrls([QtCore.QUrl.fromLocalFile(QtCore.QDir.homePath()), QtCore.QUrl.fromLocalFile(QtGui.QDesktopServices.storageLocation(QtGui.QDesktopServices.MusicLocation))])

        self.splitter = self.findChildren(QtGui.QSplitter)[0]
        self.wave_panel = WavePanel(self)
        self.wave_panel.isValid.connect(self.open_enable)
        self.valid = False

        self.splitter.addWidget(self.wave_panel)
        self.splitter.setCollapsible(2, False)
        self.currentChanged.connect(self.wave_panel.setWave)

    def accept(self):
        if self.valid:
            QtGui.QFileDialog.accept(self)

    def open_enable(self, state):
        self.valid = state
        if not state:
            QtCore.QTimer.singleShot(0, lambda: self.open_btn.setEnabled(state))

    def exec_(self):
        res = QtGui.QFileDialog.exec_(self)
        if res:
            return self.selectedFiles()[0]
        return res




