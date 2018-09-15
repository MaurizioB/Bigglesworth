from math import sqrt
from itertools import chain
from collections import OrderedDict
import numpy as np

from Qt import QtCore, QtGui, QtWidgets

try:
    from Qt import QtMultimedia
#    from bigglesworth.wavetables.waveplay import Player, AudioSettingsDialog
#    from audiosettings import AudioSettingsDialog
    QTMULTIMEDIA = True
except:
    QTMULTIMEDIA = False

import soundfile

from dial import _Dial
from bigglesworth.wavetables.utils import balanceFuncs, balanceSqrt, ActivateDrag, parseTime
from bigglesworth.wavetables.widgets import DefaultSlider
from bigglesworth.wavetables.graphics import ChunkItem, LoadItem, InvalidItem, SilentItem
from bigglesworth.wavetables.dialogs import Loader
from bigglesworth.utils import sanitize, setBold, loadUi


PathRole = QtCore.Qt.UserRole + 1
HomeRole = PathRole + 1

class FileSystemModel(QtWidgets.QFileSystemModel):
    #fix for wrong text alignment in size column
    def data(self, index, role):
        if role == QtCore.Qt.TextAlignmentRole and index.column() == 1:
            return QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter
        return QtWidgets.QFileSystemModel.data(self, index, role)


class WaveInfoModel(QtGui.QStandardItemModel):
    def data(self, index, role):
        if role == QtCore.Qt.ToolTipRole and index.column() in (1, 3, 5):
            return index.data()
        return QtGui.QStandardItemModel.data(self, index, role)


class WaveSourcePreview(QtWidgets.QGraphicsView):
    def mousePressEvent(self, event):
        if self.scene().loadItem:
            self.scene().drawWaveFile()

    def resizeEvent(self, event):
        self.fitInView(self.sceneRect())


class AudioImportDialogPreview(QtWidgets.QGroupBox):
    def __init__(self, *args, **kwargs):
        QtWidgets.QGroupBox.__init__(self, *args, **kwargs)
        loadUi('ui/audioimportdialogwidget.ui', self)
        self.playerPanel.setVisible(QTMULTIMEDIA)
#        self.waveView.setFixedSize(self.waveView.sizeHint())
#        self.waveView

        self.volumeIcon.iconSize = self.playBtn.iconSize()
        self.volumeIcon.setVolume(self.volumeSlider.value())
        self.volumeIcon.step.connect(lambda step: self.volumeSlider.setValue(self.volumeSlider.value() + self.volumeSlider.pageStep() * step))
        self.volumeIcon.reset.connect(self.volumeSlider.reset)
        self.volumeSlider.valueChanged.connect(self.volumeIcon.setVolume)

        self.waveInfoModel = WaveInfoModel()
        self.waveInfoView.setModel(self.waveInfoModel)
        for row in [('File', ), ('Format', ), ('Subtype', ), ('Chans', 'Duration'), ('Freq', 'Frames')]:
            items = []
            for label in row:
                item = QtGui.QStandardItem(label)
                setBold(item)
                items.append(item)
                item.setFlags(item.flags() ^ QtCore.Qt.ItemIsSelectable)
                items.append(QtGui.QStandardItem())
            self.waveInfoModel.appendRow(items)
        self.waveInfoView.resizeColumnToContents(0)
        self.waveInfoView.resizeColumnToContents(2)
        self.waveInfoView.horizontalHeader().setResizeMode(0, QtWidgets.QHeaderView.Fixed)
        self.waveInfoView.horizontalHeader().setResizeMode(1, QtWidgets.QHeaderView.Stretch)
        self.waveInfoView.horizontalHeader().setResizeMode(2, QtWidgets.QHeaderView.Fixed)
        self.waveInfoView.horizontalHeader().setResizeMode(3, QtWidgets.QHeaderView.Stretch)
        self.waveInfoView.setSpan(0, 1, 1, 3)
        self.waveInfoView.setSpan(1, 1, 1, 3)
        self.waveInfoView.setSpan(2, 1, 1, 3)
        self.waveInfoView.resizeRowsToContents()
        self.waveInfoView.setFixedHeight(self.waveInfoView.verticalHeader().length() + self.waveInfoView.lineWidth() * 5)


class OpenAudioFileDialog(QtWidgets.QFileDialog):
    def __init__(self, parent):
        QtWidgets.QFileDialog.__init__(self, parent, 'Open audio file', 
            QtGui.QDesktopServices.storageLocation(QtGui.QDesktopServices.HomeLocation))
        self.setOptions(self.DontUseNativeDialog|self.HideNameFilterDetails)
        self.setAcceptMode(self.AcceptOpen)
        filters = ['All supported audio files ({})'.format(' '.join(
            ['*.{}'.format(k.lower()) for k in soundfile.available_formats().keys()]))]
        filters.extend(['{} (*.{})'.format(desc, ext.lower()) for ext, desc in AudioImportTab.sortedFormats.items()])
        self.setNameFilters(filters + ['All files (*)'])

        self.player = parent.player

        self.buttonBox = self.findChild(QtWidgets.QDialogButtonBox)
        self.openBtn = self.buttonBox.button(self.buttonBox.Open)

        hint = self.sizeHint()
        self.preview = AudioImportDialogPreview(self)
        self.layout().addWidget(self.preview, 0, self.layout().columnCount(), self.layout().rowCount(), 1)
        hint.setWidth(hint.width() + self.preview.sizeHint().width())
        self.resize(hint)

        self.previewBox = self.preview.previewBox
        self.waveInfoModel = self.preview.waveInfoModel
        self.waveInfoView = self.preview.waveInfoView
        self.waveView = self.preview.waveView
        self.playerPanel = self.preview.playerPanel
        self.playBtn = self.preview.playBtn
        self.stopBtn = self.preview.stopBtn
        self.autoPlayChk = self.preview.autoPlayChk
        self.volumeSlider = self.preview.volumeSlider

        self.volumeSlider.setValue(AudioImportTab.defaultVolume)
        self.settings = QtCore.QSettings()
        self.settings.beginGroup('WaveTables')
        self.autoPlayChk.setChecked(self.settings.value('AutoPlayFileImport', False, bool))
        self.settings.endGroup()

        self.loader = Loader(self)
        self.waveScene = WaveSourceScene(self.waveView)
#        self.waveScene.loaded.connect(self.playerPanel.setEnabled)
        self.waveScene.loadingStarted.connect(self.loader.start)
        self.waveScene.loading.connect(self.loader.refresh)
#        self.waveScene.loaded.connect(self.loader.accept)
        self.waveScene.loaded.connect(self.loaded)
        self.waveView.setScene(self.waveScene)

        self.currentChanged.connect(self.checkFile)
        self.playBtn.toggled.connect(self.play)
        self.stopBtn.clicked.connect(self.player.stop)
        self.isValid = False

    def loaded(self, loaded):
        self.playerPanel.setEnabled(loaded)
        if loaded:
            self.loader.accept()
            if self.autoPlayChk.isChecked() and not self.player.isActive():
                self.playBtn.setChecked(True)

    def checkFile(self, filePath):
        self.player.stop()
        self.playBtn.setChecked(False)
        fileInfo = QtCore.QFileInfo(filePath)
        try:
            assert fileInfo.isFile()
            self.currentInfo = info = soundfile.info(filePath)
#            ('File name', 'Path'), ('Format', 'Subtype', 'Duration'), ('Channels', 'Frequency', 'Frames')
            self.waveInfoModel.item(0, 1).setText(fileInfo.fileName())
            self.waveInfoModel.item(1, 1).setText(info.format_info)
            self.waveInfoModel.item(2, 1).setText(info.subtype_info)
            self.waveInfoModel.item(3, 1).setText(str(info.channels))
            self.waveInfoModel.item(3, 3).setText(parseTime(info.duration))
            self.waveInfoModel.item(4, 1).setText('{}kHz'.format(info.samplerate * .001))
            self.waveInfoModel.item(4, 3).setText(str(info.frames))
#            self.currentPreviewFile = filePath
            self.previewBox.setEnabled(True)
#            self.currentData, self.currentSampling = soundfile.read(self.currentPreviewFile, always_2d=True, dtype='float32')
            self.currentData, sampling = soundfile.read(filePath, always_2d=True, dtype='float32')
            self.playerPanel.setEnabled(
                self.waveScene.setPreviewData(self.currentData, info))
            self.isValid = True
#            if self.autoPlayChk.isChecked() and self.playerPanel.isEnabled():
#                self.playBtn.setChecked(True)
        except Exception as e:
            print(e)
            self.previewBox.setEnabled(False)
            for row, col in [(0, 1), (1, 1), (2, 1), (3, 1), (3, 3), (4, 1), (4, 3)]:
                self.waveInfoModel.item(row, col).setText('')
#            self.waveInfoView.setEnabled(False)
            if fileInfo.isDir():
                self.waveScene.setEmpty()
            else:
                self.waveScene.setInvalid()
#            self.playerPanel.setEnabled(False)
            self.isValid = False
        QtCore.QTimer.singleShot(0, lambda: self.openBtn.setEnabled(self.isValid))

    def play(self, state):
        if state:
            themeIcon = 'media-playback-pause'
        else:
            themeIcon = 'media-playback-start'
        self.playBtn.setIcon(QtGui.QIcon.fromTheme(themeIcon))
        if self.player.isPaused() and state:
            self.player.resume()
        elif self.player.isPlaying() and not state:
            self.player.pause()
        elif state:
            self.waveScene.playhead.setX(0)
            self.waveScene.playhead.setVisible(True)
            self.player.playWaveFile(self.currentData, self.currentInfo, self.volumeSlider.value() * .01)

    def stopped(self):
        self.waveScene.playhead.setVisible(False)
        self.playBtn.blockSignals(True)
        self.playBtn.setChecked(False)
        self.playBtn.blockSignals(False)
        self.playBtn.setIcon(QtGui.QIcon.fromTheme('media-playback-start'))

    def movePlayhead(self):
        self.waveScene.setPlayhead(self.player.output.processedUSecs() / 1000000.)

    def accept(self):
        if self.isValid:
            QtWidgets.QFileDialog.accept(self)

    def exec_(self):
        self.player.notify.connect(self.movePlayhead)
        self.player.stopped.connect(self.stopped)
        res = QtWidgets.QFileDialog.exec_(self)
        self.player.stop()
        self.player.stopped.disconnect(self.stopped)
        self.player.notify.disconnect(self.movePlayhead)
        self.settings.beginGroup('WaveTables')
        self.settings.setValue('AutoPlayFileImport', self.autoPlayChk.isChecked())
        self.settings.endGroup()
        if res:
            return self.selectedFiles()[0]


class AudioImportEditTab(QtWidgets.QWidget):
    gainFullRange = ['{:.3f}'.format(g * .01) for g in range(801)]

    gainChanged = QtCore.pyqtSignal(float)
    channelsChanged = QtCore.pyqtSignal(object)

    def __init__(self, mainTab):
        QtWidgets.QWidget.__init__(self)
        self.mainTab = mainTab
        self.currentData = mainTab.currentData
        self.currentInfo = mainTab.currentInfo
        self._channelValues = []
        self._gain = 1.

        layout = QtWidgets.QGridLayout()
        self.setLayout(layout)

        self.inLayout = QtWidgets.QGridLayout()
        layout.addLayout(self.inLayout, 0, 0, 1, 1)
        gainLabel = QtWidgets.QLabel('Gain')
        gainLabel.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum))
        self.inLayout.addWidget(gainLabel, 0, 0, alignment=QtCore.Qt.AlignCenter)
        self.gainDial = _Dial(self, fullRange=(0, 800, 1), valueList=self.gainFullRange, centerAngle=240)
        self.gainDial.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred))
        self.gainDial.setDefaultValue(100)
        self.gainDial.setMaximum(800)
        self.gainDial.setMinimumHeight(60)
        self.inLayout.addWidget(self.gainDial, 1, 0)

        self.gainSpin = QtWidgets.QDoubleSpinBox()
        self.gainSpin.setRange(0, 8)
        self.gainSpin.setSingleStep(0.1)
        self.gainSpin.setDecimals(3)
        self.gainValidPalette = self.gainSpin.palette()
        self.gainInvalidPalette = QtGui.QPalette(self.gainValidPalette)
        self.gainInvalidPalette.setColor(QtGui.QPalette.Text, QtGui.QColor(QtCore.Qt.red))
        self.inLayout.addWidget(self.gainSpin, 2, 0)

        self.gainDial.valueChanged.connect(lambda value: self.gainSpin.setValue(value * .01))
#        self.gainSpin.valueChanged.connect(
#            lambda value: [self.gainDial.blockSignals(True), self.gainDial.setValue(int(value * 100)), self.gainDial.blockSignals(False)])
        self.gainSpin.valueChanged.connect(self.setGain)
        self.gainDial.setValue(100)

        textWidth = self.fontMetrics().width('8.88888')
        option = QtWidgets.QStyleOptionSpinBox()
        self.gainSpin.initStyleOption(option)
        spinButtonWidth = self.style().subControlRect(QtWidgets.QStyle.CC_SpinBox, option, QtWidgets.QStyle.SC_SpinBoxUp).width() + 4
        self.maxSpinWidth = spinButtonWidth + textWidth
        self.gainSpin.setMaximumWidth(self.maxSpinWidth)

        self.channels = []
        if self.currentInfo.channels > 1:
            if self.currentInfo.channels == 2:
                self.addStereo()
            else:
                self.addChannels(self.currentInfo.channels)
        else:
            self._channelValues = [1.]

        spacer = QtWidgets.QSpacerItem(1, 1, QtWidgets.QSizePolicy.Expanding)
        layout.addItem(spacer, 0, layout.columnCount())

    def setValid(self, valid):
        self.gainSpin.lineEdit().setPalette(self.gainValidPalette if valid else self.gainInvalidPalette)

    @property
    def gain(self):
        return self._gain

    @property
    def channelValues(self):
        return self._channelValues

    @channelValues.setter
    def channelValues(self, values):
        self._channelValues = values
        self.channelsChanged.emit(values)

    def addStereo(self):
        vLine = QtWidgets.QFrame()
        vLine.setFrameShape(vLine.VLine)
        vLine.setFrameShadow(vLine.Sunken)
        self.inLayout.addWidget(vLine, 0, self.inLayout.columnCount(), 3, 1)

        column = self.inLayout.columnCount()
        self.inLayout.addWidget(QtWidgets.QLabel('Left'), 0, column, alignment=QtCore.Qt.AlignCenter)
        self.leftSlider = QtWidgets.QSlider(QtCore.Qt.Vertical)
        self.leftSlider.setRange(0, 100)
        self.leftSlider.setTickPosition(self.leftSlider.TicksBothSides)
        self.leftSlider.setTickInterval(20)
        self.inLayout.addWidget(self.leftSlider, 1, column, alignment=QtCore.Qt.AlignCenter)

        self.leftSpin = QtWidgets.QDoubleSpinBox()
        self.leftSpin.setRange(0, 1)
        self.leftSpin.setDecimals(3)
        self.leftSpin.setSingleStep(0.05)
        self.leftSpin.setMaximumWidth(self.maxSpinWidth)
        self.channels.append(self.leftSpin)
        self.inLayout.addWidget(self.leftSpin, 2, column)

        column = self.inLayout.columnCount()
        self.balanceChk = QtWidgets.QCheckBox('Balance')
        self.balanceChk.setChecked(True)
        self.inLayout.addWidget(self.balanceChk, 0, column, alignment=QtCore.Qt.AlignCenter)

        self.balSlider = DefaultSlider(QtCore.Qt.Horizontal)
        self.balSlider.defaultValue = 50
        self.balSlider.setRange(0, 100)
        self.balSlider.setTickPosition(self.balSlider.TicksAbove)
        self.balSlider.setTickInterval(50)
        self.balSlider.setValue(50)
        self.inLayout.addWidget(self.balSlider, 1, column, alignment=QtCore.Qt.AlignCenter)

        self.balCombo = QtWidgets.QComboBox()
        self.balCombo.addItems(['Eq. Amp', 'Eq. Power'])
        self.balCombo.setCurrentIndex(1)
        self.inLayout.addWidget(self.balCombo, 2, column, alignment=QtCore.Qt.AlignCenter)

        column = self.inLayout.columnCount()
        self.inLayout.addWidget(QtWidgets.QLabel('Right'), 0, column, alignment=QtCore.Qt.AlignCenter)
        self.rightSlider = QtWidgets.QSlider(QtCore.Qt.Vertical)
        self.rightSlider.setRange(0, 100)
        self.rightSlider.setTickPosition(self.rightSlider.TicksBothSides)
        self.rightSlider.setTickInterval(20)
        self.inLayout.addWidget(self.rightSlider, 1, column, alignment=QtCore.Qt.AlignCenter)

        self.rightSpin = QtWidgets.QDoubleSpinBox()
        self.rightSpin.setRange(0, 1)
        self.rightSpin.setDecimals(3)
        self.rightSpin.setSingleStep(0.05)
        self.rightSpin.setMaximumWidth(self.maxSpinWidth)
        self.channels.append(self.rightSpin)
        self.inLayout.addWidget(self.rightSpin, 2, column)

        self._channelValues = list(balanceSqrt(.5))
        self.leftSpin.setValue(self._channelValues[0])
        self.leftSlider.setValue(70)
        #avoid slider approximation correction
        self.leftSpin.valueChanged.connect(
            lambda value: [self.leftSlider.blockSignals(True), self.leftSlider.setValue(value * 100), self.leftSlider.blockSignals(False)])
        self.leftSlider.valueChanged.connect(lambda value: self.leftSpin.setValue(value * .01))
        self.rightSpin.setValue(self._channelValues[0])
        self.rightSlider.setValue(70)
        self.rightSpin.valueChanged.connect(
            lambda value: [self.rightSlider.blockSignals(True), self.rightSlider.setValue(value * 100), self.rightSlider.blockSignals(False)])
        self.rightSlider.valueChanged.connect(lambda value: self.rightSpin.setValue(value * .01))

        self.balControls = self.leftSpin, self.leftSlider, self.rightSpin, self.rightSlider
        for w in self.balControls:
            w.setEnabled(False)

        self.balanceChk.toggled.connect(self.toggleBalance)
        self.balSlider.valueChanged.connect(self.setBalance)
        self.balCombo.currentIndexChanged.connect(lambda: self.setBalance(self.balSlider.value()))

    def toggleBalance(self, state):
        [w.setDisabled(state) for w in self.balControls]
        self.balSlider.setEnabled(state)
        self.balCombo.setEnabled(state)
        if state:
            self.setBalance(self.balSlider.value())
            self.leftSpin.valueChanged.disconnect(self.channelChanged)
            self.rightSpin.valueChanged.disconnect(self.channelChanged)
        else:
            self.leftSpin.valueChanged.connect(self.channelChanged)
            self.rightSpin.valueChanged.connect(self.channelChanged)

    def setGain(self, gain):
        self.gainDial.blockSignals(True)
        self.gainDial.setValue(int(gain * 100))
        self.gainDial.blockSignals(False)
        self._gain = gain
        self.gainChanged.emit(gain)

    def setBalance(self, value):
        left, right = balanceFuncs[self.balCombo.currentIndex()](value * .01)
        self.leftSpin.setValue(left)
        self.rightSpin.setValue(right)
        self.channelValues = [left, right]
#        self.channelsChanged.emit([left, right])

    def addChannels(self, channels):
        vLine = QtWidgets.QFrame()
        vLine.setFrameShape(vLine.VLine)
        vLine.setFrameShadow(vLine.Sunken)
        self.inLayout.addWidget(vLine, 0, self.inLayout.columnCount(), 3, 1)

        btnLayout = QtWidgets.QVBoxLayout()
        self.inLayout.addLayout(btnLayout, 0, self.inLayout.columnCount(), 3, 1)
        lockChannelsChk = QtWidgets.QCheckBox('Lock channels')
        lockChannelsChk.toggled.connect(self.setLock)
        btnLayout.addWidget(lockChannelsChk)

        ePowValue = sqrt(2) / channels
        eAmpValue = 1. / channels
        self._channelValues = [ePowValue for _ in range(self.currentInfo.channels)]

        ePowBtn = QtWidgets.QPushButton('Eq. Power')
        ePowBtn.clicked.connect(lambda: self.setChannels(ePowValue))
        btnLayout.addWidget(ePowBtn)
        eAmpBtn = QtWidgets.QPushButton('Eq. Amp')
        eAmpBtn.clicked.connect(lambda: self.setChannels(eAmpValue))
        btnLayout.addWidget(eAmpBtn)

        for channel in range(self.currentInfo.channels):
            vLine = QtWidgets.QFrame()
            vLine.setFrameShape(vLine.VLine)
            vLine.setFrameShadow(vLine.Sunken)
            self.inLayout.addWidget(vLine, 0, self.inLayout.columnCount(), 3, 1)

            column = self.inLayout.columnCount()
            self.inLayout.addWidget(QtWidgets.QLabel('Ch. {}'.format(channel + 1)), 0, column, alignment=QtCore.Qt.AlignCenter)
            gainSlider = QtWidgets.QSlider(QtCore.Qt.Vertical)
            gainSlider.setRange(0, 100)
            gainSlider.setTickPosition(gainSlider.TicksBothSides)
            gainSlider.setTickInterval(20)
            self.inLayout.addWidget(gainSlider, 1, column, alignment=QtCore.Qt.AlignCenter)

            gainSpin = QtWidgets.QDoubleSpinBox()
            gainSpin.slider = gainSlider
            gainSpin.setRange(0, 1)
            gainSpin.setDecimals(3)
            gainSpin.setSingleStep(0.05)
            gainSpin.setMaximumWidth(self.maxSpinWidth)
            self.inLayout.addWidget(gainSpin, 2, column)
            self.channels.append(gainSpin)

            gainSlider.setValue(ePowValue * 100)
            gainSpin.setValue(ePowValue)
            gainSlider.valueChanged.connect(lambda value, spin=gainSpin: spin.setValue(value * .01))
            #avoid slider approximation correction
            gainSpin.valueChanged.connect(
                lambda value, slider=gainSlider: [slider.blockSignals(True), slider.setValue(value * 100), slider.blockSignals(False)])
            gainSpin.valueChanged.connect(self.channelChanged)


    def setLock(self, state):
        if state:
            for spin in self.channels:
                spin.valueChanged.disconnect(self.channelChanged)
                spin.valueChanged.connect(self.setChannels)
        else:
            for spin in self.channels:
                spin.valueChanged.disconnect(self.setChannels)
                spin.valueChanged.connect(self.channelChanged)

    def setChannels(self, value):
        for spin in self.channels:
            spin.blockSignals(True)
            spin.setValue(value)
            spin.slider.setValue(value * 100)
            spin.blockSignals(False)
        self.channelValues = [value for _ in range(len(self.channels))]
#        self.channelsChanged.emit([value for _ in range(len(self.channels))])

    def channelChanged(self):
        self.channelValues = [spin.value() for spin in self.channels]
#        values = []
#        for spin in self.channels:
#            values.append(spin.value())
#        self.channelsChanged.emit(values)


class PositionWidget(QtWidgets.QWidget):
    moved = QtCore.pyqtSignal(float)

    pen = QtGui.QPen(QtCore.Qt.lightGray, 1)
    pen.setCosmetic(True)
    brush = QtGui.QColor(64, 96, 96, 160)

    def __init__(self, main, sceneRect, pixmap):
        QtWidgets.QWidget.__init__(self)
        self.setWindowFlags(QtCore.Qt.Widget|QtCore.Qt.Tool|QtCore.Qt.FramelessWindowHint|QtCore.Qt.X11BypassWindowManagerHint)
        self.main = main
        self.sceneRect = sceneRect
        self.pixmap = pixmap
        self.setFixedSize(120, 60)
        self.ratio = 1

    def showEvent(self, event):
        QtWidgets.QWidget.showEvent(self, event)
        rect = QtWidgets.QApplication.desktop().availableGeometry(self)
        x = sanitize(rect.left(), self.x(), rect.right() - self.width())
        y = sanitize(rect.top(), self.y(), rect.bottom() - self.height())
        self.move(x, y)

    def setRect(self, rect):
        if rect.x() > 0:
            x = rect.x() / self.sceneRect.width() * 120
        else:
            x = 0
        width = rect.width() / self.sceneRect.width() * 120
        self.currentRect = QtCore.QRectF(x, 0, width - 1, 59)

    def mouseMoveEvent(self, event):
        halfWidth = self.currentRect.width() / 2
        x = sanitize(halfWidth, event.pos().x(), self.width() - halfWidth)
        self.currentRect.moveCenter(QtCore.QPoint(x, self.currentRect.center().y()))
        self.moved.emit((x - halfWidth) / (120. - halfWidth * 2))
        self.update()

    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        qp.drawPixmap(0, 0, self.pixmap)
        qp.translate(.5, .5)
        qp.setPen(self.pen)
        qp.setBrush(self.brush)
        qp.drawRect(self.currentRect)

    def leaveEvent(self, event):
        self.hide()


class WaveViewTabBar(QtWidgets.QTabBar):
    def tabSizeHint(self, index):
        hint = QtWidgets.QTabBar.tabSizeHint(self, index)
        hint.setHeight(self.height() / self.count())
        return hint

class PathCombo(QtWidgets.QComboBox):
    pathChanged = QtCore.Signal(object)

    def setFileSystemModel(self, model):
        self.completer().setModel(model)
        self.fsModel = model
        myComputer = self.fsModel.myComputer
        self.addItem(myComputer(self.fsModel.FileIconRole), myComputer())
        locations = [
            ('go-home', QtGui.QDesktopServices.HomeLocation), 
            ('desktop', QtGui.QDesktopServices.DesktopLocation), 
            ('folder-music', QtGui.QDesktopServices.MusicLocation), 
            ('folder-documents', QtGui.QDesktopServices.DocumentsLocation)
        ]
        index = 0
        for iconName, location in locations:
            path = QtGui.QDesktopServices.storageLocation(location)
            if not QtCore.QFileInfo(path).exists():
                continue
            name = QtGui.QDesktopServices.displayName(location)
            if not name:
                name = QtCore.QFileInfo(path).completeBaseName()
            self.addItem(QtGui.QIcon.fromTheme(iconName), name)
            index += 1
            self.setItemData(index, path, PathRole)
        self.setCurrentIndex(-1)
        self.currentIndexChanged.connect(self.emitPathChanged)

    def emitPathChanged(self, index):
        path = self.itemData(index, PathRole)
        if path is None:
            path = self.itemText(index)
        self.pathChanged.emit(self.fsModel.index(path))

    def event(self, event):
        if event.type() == QtCore.QEvent.KeyPress:
            if event.key() == QtCore.Qt.Key_Tab and self.completer().completionCount() and \
                self.lineEdit().hasSelectedText():
                    if self.completer().completionCount() == 1:
                        self.lineEdit().setCursorPosition(len(self.currentText()))
                    else:
                        row = self.completer().currentRow() + 1
                        if row == self.completer().completionCount():
                            row = 0
                        self.completer().setCurrentRow(row)
                    self.completer().complete()
                    return True
            elif event.key() in (QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return) and \
                self.completer().completionCount() and QtCore.QFileInfo(self.completer().currentCompletion()).isDir():
                    self.lineEdit().setCursorPosition(len(self.currentText()))
                    self.pathChanged.emit(self.fsModel.index(self.currentText()))
        return QtWidgets.QComboBox.event(self, event)


class ToolTipModel(QtGui.QStandardItemModel):
    def data(self, index, role):
        if role == QtCore.Qt.ToolTipRole:
            path = QtGui.QStandardItemModel.data(self, index, PathRole)
            if path:
                return QtGui.QStandardItemModel.data(self, index, QtCore.Qt.DisplayRole)
        return QtGui.QStandardItemModel.data(self, index, role)


class AudioImportTab(QtWidgets.QWidget):
    sortedFormats = OrderedDict([(k, soundfile.available_formats()[k]) for k in ['WAV', 'AIFF', 'FLAC', 'OGG']])
    for format in sorted(soundfile.available_formats().keys()):
        if format not in sortedFormats:
            sortedFormats[format] = soundfile.available_formats()[format]
    shown = False
    previewMode = True
    imported = QtCore.pyqtSignal(object)

    recentModel = ToolTipModel()
    recentLoaded = False
    favoriteModel = ToolTipModel()
    favoriteLoaded = False

    defaultVolume = None

    def __init__(self, waveTableWindow):
        QtWidgets.QWidget.__init__(self)
        loadUi('ui/audioimporttab.ui', self)
        self.waveTableWindow = waveTableWindow
        self.player = waveTableWindow.player
        self.tabWidget = waveTableWindow.mainTabWidget
        self.settings = QtCore.QSettings()
        self.loader = Loader(self)
        self.selectionWidget.setVisible(False)

        self.waveScene = WaveSourceScene(self.waveView)
        self.waveScene.loaded.connect(self.playerPanel.setEnabled)
        self.waveScene.loadingStarted.connect(self.loader.start)
        self.waveScene.loading.connect(self.loader.refresh)
        self.waveScene.loaded.connect(self.loader.accept)
        self.waveView.setScene(self.waveScene)

        self.formatCombo.addItem('All supported audio files', ['*.{}'.format(k.lower()) for k in soundfile.available_formats().keys()])
        self.formatCombo.addItem('All files', ['*'])
        for k, v in self.sortedFormats.items():
            self.formatCombo.addItem(v, ['*.{}'.format(k.lower())])

        self.fileSystemModel = FileSystemModel()
        self.fileSystemModel.setFilter(QtCore.QDir.AllEntries | QtCore.QDir.AllDirs | QtCore.QDir.NoDot)
        self.fileSystemModel.setRootPath(QtCore.QDir.rootPath())
        self.fileSystemModel.setNameFilterDisables(False)
        self.pathCombo.setFileSystemModel(self.fileSystemModel)
        self.pathCombo.pathChanged.connect(self.setCurrentDirectory)

        self.fileSystemView.setModel(self.fileSystemModel)
        self.fileSystemView.setColumnHidden(2, True)
        self.fileSystemView.setColumnHidden(3, True)
        self.fileSystemView.horizontalHeader().setResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.fileSystemView.horizontalHeader().setResizeMode(1, QtWidgets.QHeaderView.Fixed)
        self.fileSystemView.doubleClicked.connect(self.setCurrentDirectory)
        self.fileSystemView.clicked.connect(self.fileSelected)
        self.fileSystemView.customContextMenuRequested.connect(self.fileSystemMenu)
#        self.fileSystemModel.directoryLoaded.connect(self.directoryLoaded)

        self.history = []
        self.goBackBtn.clicked.connect(self.goBack)
        self.goUpBtn.clicked.connect(self.goUp)

        self.settings.beginGroup('WaveTables')
        for path in (self.settings.value('BrowseHome'), self.settings.value('BrowsePath')):
            if path and QtCore.QDir().exists(path):
                break
        else:
            path = QtGui.QDesktopServices.storageLocation(QtGui.QDesktopServices.HomeLocation)
        self.fileSystemView.setRootIndex(self.fileSystemModel.index(path))
#        self.fileSystemView.setRootIndex(self.fileSystemModel.index('/tmp/stocazzo'))
#        self.fileSystemView.setRootIndex(self.fileSystemModel.index(QtCore.QDir.currentPath()))
#        self.fileSystemView.setRootIndex(self.fileSystemModel.index(
#            self.settings.value('BrowsePath', QtGui.QDesktopServices.storageLocation(QtGui.QDesktopServices.HomeLocation))))

        self.recentView.setModel(self.recentModel)
        self.recentView.clicked.connect(self.fileSelected)
        self.recentView.customContextMenuRequested.connect(self.recentMenu)

        recents = self.settings.value('RecentFiles', [])
        if not self.recentLoaded:
            self.recentModel.setHorizontalHeaderLabels(['Name', 'Location'])
            for path in recents:
                fileInfo = QtCore.QFileInfo(path)
                nameItem = QtGui.QStandardItem(fileInfo.fileName())
                nameItem.setData(fileInfo.absoluteFilePath(), PathRole)
                locationItem = QtGui.QStandardItem(QtCore.QDir.toNativeSeparators(fileInfo.absolutePath()))
                locationItem.setData(fileInfo.absoluteFilePath(), PathRole)
                self.recentModel.appendRow([nameItem, locationItem])
            self.__class__.recentLoaded = True
        if recents:
            self.recentView.resizeColumnToContents(0)
            self.recentView.resizeRowsToContents()

        self.favoriteView.setModel(self.favoriteModel)
        self.favoriteView.doubleClicked.connect(self.openFavorite)
        self.favoriteView.customContextMenuRequested.connect(self.favoriteMenu)

        favorites = self.settings.value('Favorites', [])
        homePath = self.settings.value('BrowseHome')
        if not self.favoriteLoaded:
            self.favoriteModel.setHorizontalHeaderLabels(['Name', 'Full path'])

            for path in favorites:
                fileInfo = QtCore.QFileInfo(path)
                nameItem = QtGui.QStandardItem(fileInfo.fileName())
                nameItem.setData(fileInfo.absoluteFilePath(), PathRole)
                if path == homePath:
                    nameItem.setIcon(QtGui.QIcon.fromTheme('go-home'))
                    nameItem.setData(True, HomeRole)
                locationItem = QtGui.QStandardItem(QtCore.QDir.toNativeSeparators(fileInfo.absoluteFilePath()))
                locationItem.setData(fileInfo.absoluteFilePath(), PathRole)
                self.favoriteModel.appendRow([nameItem, locationItem])
            self.__class__.favoriteLoaded = True

        if favorites:
            self.favoriteView.resizeColumnToContents(0)
            self.favoriteView.resizeRowsToContents()

        self.settings.endGroup()

        self.waveInfoModel = WaveInfoModel()
        self.waveInfoView.setModel(self.waveInfoModel)
        for row in [('File name', 'Path'), ('Format', 'Subtype', 'Duration'), ('Channels', 'Frequency', 'Frames')]:
            items = []
            for label in row:
                item = QtGui.QStandardItem(label)
                setBold(item)
                items.append(item)
                item.setFlags(item.flags() ^ QtCore.Qt.ItemIsSelectable)
                items.append(QtGui.QStandardItem())
            self.waveInfoModel.appendRow(items)
        self.waveInfoView.resizeColumnToContents(0)
        self.waveInfoView.resizeColumnToContents(2)
        self.waveInfoView.resizeColumnToContents(4)
        self.waveInfoView.horizontalHeader().setResizeMode(0, QtWidgets.QHeaderView.Fixed)
        self.waveInfoView.horizontalHeader().setResizeMode(1, QtWidgets.QHeaderView.Stretch)
        self.waveInfoView.horizontalHeader().setResizeMode(2, QtWidgets.QHeaderView.Fixed)
        self.waveInfoView.horizontalHeader().setResizeMode(3, QtWidgets.QHeaderView.Stretch)
        self.waveInfoView.horizontalHeader().setResizeMode(4, QtWidgets.QHeaderView.Fixed)
        self.waveInfoView.horizontalHeader().setResizeMode(5, QtWidgets.QHeaderView.Stretch)
        self.waveInfoView.setSpan(0, 3, 1, 3)
        self.waveInfoView.resizeRowsToContents()
        self.waveInfoView.setMaximumHeight(self.waveInfoView.verticalHeader().length() + self.waveInfoView.lineWidth() * 4)

        self.formatCombo.currentIndexChanged.connect(self.setFormatFilter)

        self.playBtn.toggled.connect(self.play)
        self.stopBtn.clicked.connect(self.stop)
        self.volumeSlider.valueChanged.connect(self.setVolume)
#        self.volumeSlider.valueChanged.connect(self.volumeSpin.setValue)
#        self.volumeSlider.valueChanged.connect(self.volumeIcon.setVolume)
        self.volumeSpin.valueChanged.connect(self.volumeSlider.setValue)
        self.volumeIcon.iconSize = self.playBtn.iconSize()
        self.volumeIcon.setVolume(self.volumeSlider.value())
        self.volumeIcon.step.connect(lambda step: self.volumeSlider.setValue(self.volumeSlider.value() + self.volumeSlider.pageStep() * step))
        self.volumeIcon.reset.connect(self.volumeSlider.reset)
        self.volumeSpin.setMaximumWidth(self.volumeSpin.minimumSizeHint().width() * .75)
        if not self.defaultVolume:
            self.__class__.defaultVolume = self.settings.value('defaultVolume', 80, type=int)
        self.volumeSlider.setValue(self.defaultVolume)

        self.openWaveBtn.clicked.connect(self.openFileDialog)
        self.importBtn.clicked.connect(self.importFile)
        self.lowerPanel.setSwitchVisible(False)

    def openFileDialog(self):
        self.player.stop()
        try:
            self.player.notify.disconnect(self.movePlayhead)
            self.player.stopped.disconnect(self.stopped)
        except:
            pass
        path = OpenAudioFileDialog(self).exec_()
        if path:
            self.fileSelected(self.fileSystemModel.index(path), True)
            self.importFile()
        try:
            self.player.stopped.connect(self.stopped, QtCore.Qt.UniqueConnection)
            self.player.notify.connect(self.movePlayhead, QtCore.Qt.UniqueConnection)
        except:
            pass

    def setVolume(self, volume):
        self.volumeSpin.setValue(volume)
        self.volumeIcon.setVolume(volume)
        if self.previewMode:
            self.__class__.defaultVolume = volume

    def play(self, state):
        self.volumeSlider.setEnabled(False)
        self.volumeSpin.setEnabled(False)
        self.volumeIcon.setEnabled(False)
        self.playSelectionChk.setEnabled(False)
        if state:
            themeIcon = 'media-playback-pause'
        else:
            themeIcon = 'media-playback-start'
        self.playBtn.setIcon(QtGui.QIcon.fromTheme(themeIcon))
        if self.player.isPaused() and state:
            self.player.resume()
        elif self.player.isPlaying() and not state:
            self.player.pause()
        else:
            if self.previewMode:
                self.playPreview()
            else:
                self.playWave()
#        if self.previewMode:
#            if self.player.isPaused():
#                self.player.resume()
#            elif self.player.isPlaying():
#                self.player.pause()
#            else:
#                self.playPreview()
#        else:
#            self.playWave()

    def playPreview(self):
        self.waveScene.playhead.setX(0)
        self.waveScene.playhead.setVisible(True)
        self.player.playWaveFile(self.currentData, self.currentInfo, self.volumeSlider.value() * .01)

    def playWave(self):
        self.waveScene.playhead.setVisible(True)
        if self.playSelectionChk.isChecked() and self.selectCountSpin.value():
            start = self.offsetSpin.value() + self.selectFromSpin.value() * 128
            end = start + self.selectCountSpin.value() * 128
            data = self.waveScene.outValues[start:end]
            self.waveScene.playhead.setX(start)
        else:
            data = self.waveScene.outValues
            self.waveScene.playhead.setX(0)
        self.player.playData(data, self.volumeSlider.value() * .01, True)

    def stop(self):
        self.player.stop()

    def stopped(self):
        self.playBtn.blockSignals(True)
        self.playBtn.setChecked(False)
        self.playBtn.blockSignals(False)
        self.playBtn.setIcon(QtGui.QIcon.fromTheme('media-playback-start'))
        self.volumeSlider.setEnabled(True)
        self.volumeSpin.setEnabled(True)
        self.volumeIcon.setEnabled(True)
        self.playSelectionChk.setEnabled(True)
        self.waveScene.playhead.setVisible(False)

    def movePlayhead(self):
        self.waveScene.setPlayhead(self.player.output.processedUSecs() / 1000000.)
        if not self.previewMode:
            self.waveView.ensureVisible(self.waveScene.playhead)

    def fileSelected(self, index, force=False):
        self.stop()
        if self.sender() == self.fileSystemView:
            if self.fileSystemModel.isDir(index):
                return
            filePath = self.fileSystemModel.filePath(index)
        else:
            filePath = index.data(PathRole)
        try:
            fileInfo = QtCore.QFileInfo(filePath)
            self.currentInfo = info = soundfile.info(filePath)
#            ('File name', 'Path'), ('Format', 'Subtype', 'Duration'), ('Channels', 'Frequency', 'Frames')
            self.waveInfoModel.item(0, 1).setText(fileInfo.fileName())
            self.waveInfoModel.item(0, 3).setText(fileInfo.absolutePath())
            self.waveInfoModel.item(1, 1).setText(info.format_info)
            self.waveInfoModel.item(1, 3).setText(info.subtype_info)
            self.waveInfoModel.item(1, 5).setText(parseTime(info.duration))
            self.waveInfoModel.item(2, 1).setText(str(info.channels))
            self.waveInfoModel.item(2, 3).setText('{}kHz'.format(info.samplerate * .001))
            self.waveInfoModel.item(2, 5).setText(str(info.frames))
            self.waveInfoView.resizeColumnToContents(5)
            self.waveInfoView.setEnabled(True)
            self.currentPreviewFile = filePath
            self.currentData, self.currentSampling = soundfile.read(self.currentPreviewFile, always_2d=True, dtype='float32')
            self.playerPanel.setEnabled(
                self.waveScene.setPreviewData(self.currentData, self.currentInfo, force))
        except Exception as e:
            print(e)
            for row, col in [(0, 1), (0, 3), (1, 1), (1, 3), (1, 5), (2, 1), (2, 3), (2, 5)]:
                self.waveInfoModel.item(row, col).setText('')
            self.waveInfoView.setEnabled(False)
            self.waveScene.setInvalid()
            self.playerPanel.setEnabled(False)

    def importFile(self):
        self.player.stop()
        self.previewMode = False
        self.browsePanel.setVisible(False)
        self.importBtn.setVisible(False)
        self.selectionWidget.setVisible(True)

        filePath = self.currentInfo.name
        fileInfo = QtCore.QFileInfo(filePath)

        self.settings.beginGroup('WaveTables')
        recents = self.settings.value('RecentFiles', [])
        if filePath not in recents:
            recents.append(filePath)
            self.settings.setValue('RecentFiles', recents)
            nameItem = QtGui.QStandardItem(fileInfo.fileName())
            nameItem.setData(fileInfo.absoluteFilePath(), PathRole)
            locationItem = QtGui.QStandardItem(QtCore.QDir.toNativeSeparators(fileInfo.absolutePath()))
            locationItem.setData(fileInfo.absoluteFilePath(), PathRole)
            self.recentModel.appendRow([nameItem, locationItem])
        self.settings.endGroup()

        self.audioImportEditTab = AudioImportEditTab(self)
        self.waveTabWidget.insertTab(0, self.audioImportEditTab, 'Import options')
        self.waveTabWidget.setCurrentIndex(0)
#        self.audioImportEditTab.gainChanged.connect(self.gainChanged)
#        self.audioImportEditTab.channelsChanged.connect(self.channelsChanged)

        ChunkItem.paint = ChunkItem.wavePaint
        pixmap = QtGui.QPixmap(120, 60)
        pixmap.fill(QtCore.Qt.black)
        qp = QtGui.QPainter(pixmap)
        self.waveScene.render(qp, QtCore.QRectF(pixmap.rect()), self.waveScene.sceneRect(), QtCore.Qt.IgnoreAspectRatio)
        self.waveScene.importCurrent(self.audioImportEditTab)

        self.imported.emit(self.currentInfo)
        self.zoomBar.setRange(0, 99)
        self.zoomBar.setValue(100 - self.waveView.transform().m11() * 100)
        self.zoomBar.setEnabled(True)
        self.zoomBar.valueChanged.connect(self.setZoom)
        self.positionWidgetIcon.setEnabled(True)
        self.zoomBarIcon.setEnabled(True)
        self.positionWidget = PositionWidget(self, self.waveScene.sceneRect(), pixmap)
        self.positionWidgetIcon.entered.connect(self.showPositionWidget)
        self.positionWidget.moved.connect(self.moveView)
        self.waveView.zoom.connect(lambda z: self.zoomBar.setValue(self.zoomBar.value() - z))
        self.waveView.scroll.connect(
            lambda step: self.waveView.horizontalScrollBar().setValue(
                self.waveView.horizontalScrollBar().value() + self.waveView.horizontalScrollBar().pageStep() * step))
        self.waveView.setStatusTip('Mouse wheel to scoll position, CTRL + wheel for zoom, SHIFT + click/drag to select waves')

        selectSpinWidth = self.fontMetrics().width(str(self.waveScene.totChunks) + '88')
        option = QtWidgets.QStyleOptionSpinBox()
        self.selectFromSpin.initStyleOption(option)
        spinButtonWidth = self.style().subControlRect(QtWidgets.QStyle.CC_SpinBox, option, QtWidgets.QStyle.SC_SpinBoxUp).width() + 4

        self.selectFromSpin.setMaximum(self.waveScene.totChunks)
        self.selectToSpin.setMaximum(self.waveScene.totChunks)
        self.selectCountSpin.setMaximum(min(64, self.waveScene.totChunks))

        self.selectFromSpin.setMaximumWidth(selectSpinWidth + spinButtonWidth)
        self.selectToSpin.setMaximumWidth(self.selectFromSpin.maximumWidth())
        self.selectCountSpin.setMaximumWidth(self.fontMetrics().width('6488') + spinButtonWidth)
        self.offsetSpin.setMaximumWidth(self.fontMetrics().width('12888') + spinButtonWidth)

        self.selectFromSpin.valueChanged.connect(self.selectRange)
        self.selectToSpin.valueChanged.connect(self.selectRange)
        self.selectCountSpin.valueChanged.connect(self.selectRange)
        self.offsetSpin.valueChanged.connect(self.waveView.setOffset)
        self.waveView.selectionChanged.connect(self.selectionChanged)

        self.waveViewTabBar = WaveViewTabBar()
        self.waveViewTabBar.setShape(self.waveViewTabBar.RoundedWest)
        self.waveViewLeftLayout.addWidget(self.waveViewTabBar)
        self.waveViewTabBar.addTab('Source')
        self.waveViewTabBar.addTab('Mixed')
        self.waveViewTabBar.setCurrentIndex(1)
        self.waveViewTabBar.currentChanged.connect(self.waveScene.setMode)
#        self.waveViewTabBar.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding))
#        self.waveViewTabBar.setExpanding(True)

        self.lowerPanel.setSwitchVisible(True)
        self.lowerPanel.contentName = 'import options and info'

    def selectionChanged(self, selection):
        self.selectFromSpin.blockSignals(True)
        self.selectToSpin.blockSignals(True)
        self.selectCountSpin.blockSignals(True)

        if selection:
            self.selectFromSpin.setValue(selection[0].index)
            self.selectToSpin.setValue(selection[-1].index)
            self.selectCountSpin.setValue(selection[-1].index - selection[0].index + 1)
        else:
            self.selectCountSpin.setValue(0)

        self.selectFromSpin.blockSignals(False)
        self.selectToSpin.blockSignals(False)
        self.selectCountSpin.blockSignals(False)

    def showPositionWidget(self):
        self.positionWidget.move(self.positionWidgetIcon.mapToGlobal(QtCore.QPoint(0, 0)))
        self.positionWidget.setRect(self.waveView.mapToScene(self.waveView.viewport().rect()).boundingRect())
        self.positionWidget.show()

    def selectRange(self, value):
        self.selectFromSpin.blockSignals(True)
        self.selectToSpin.blockSignals(True)
        self.selectCountSpin.blockSignals(True)
        if self.sender() == self.selectFromSpin:
            if not self.selectCountSpin.value():
                self.selectCountSpin.setValue(1)
                value = 1
            self.selectToSpin.setValue(value + self.selectCountSpin.value() - 1)
        elif self.sender() == self.selectToSpin:
            self.selectFromSpin.setValue(min(self.selectFromSpin.value(), value))
            self.selectCountSpin.setValue(value - self.selectFromSpin.value() + 1)
        else:
            if value:
                self.selectToSpin.setValue(self.selectFromSpin.value() + value - 1)

        self.selectFromSpin.blockSignals(False)
        self.selectToSpin.blockSignals(False)
        self.selectCountSpin.blockSignals(False)
        self.waveView.setSelection(self.selectFromSpin.value() - 1, self.selectCountSpin.value())

    def moveView(self, pos):
        scrollBar = self.waveView.horizontalScrollBar()
        scrollBar.setValue(scrollBar.maximum() * pos)

    def setZoom(self, zoom):
        zoom = (100 - zoom) * .01
        if zoom > .1:
            zoom *= 5
            ChunkItem.paint = ChunkItem.wavePaint
        else:
            ChunkItem.paint = ChunkItem.normalPaint
        self.waveView.setTransform(QtGui.QTransform().scale(zoom, self.waveView.transform().m22()))

    def saveCollapsed(self):
        self.settings.beginGroup('WaveTables')
        self.settings.setValue('HideRecents', self.recentBox.collapsed)
        self.settings.setValue('HideFavorites', self.favoriteBox.collapsed)
        self.settings.endGroup()

    def showEvent(self, event):
        if not self.shown:
            self.shown = True
            self.setFormatFilter(0)

            self.settings.beginGroup('WaveTables')
            self.checkRecents()
            if self.recentBox.isEnabled() and self.settings.value('HideRecents', False, bool):
                self.recentBox.setCollapsed(True)
            self.checkFavorites()
            if self.favoriteBox.isEnabled() and self.settings.value('HideFavorites', False, bool):
                self.favoriteBox.setCollapsed(True)
            self.settings.endGroup()
            self.recentBox.collapsedChanged.connect(self.saveCollapsed)
            self.favoriteBox.collapsedChanged.connect(self.saveCollapsed)

            zoomSize = self.zoomBar.sizeHint().width()
            self.zoomBarIcon.setFixedSize(zoomSize, zoomSize)
            self.positionWidgetIcon.setFixedSize(zoomSize, zoomSize)

        try:
            self.player.stopped.connect(self.stopped, QtCore.Qt.UniqueConnection)
            self.player.notify.connect(self.movePlayhead, QtCore.Qt.UniqueConnection)
        except:
            pass

        self.updatePathCombo(False)

    def hideEvent(self, event):
        try:
            self.player.stopped.disconnect(self.stopped)
            self.player.notify.disconnect(self.movePlayhead)
        except:
            pass
        self.playBtn.setChecked(False)

    def checkRecents(self):
        if not self.recentModel.rowCount():
            self.recentBox.setEnabled(False)
            self.recentBox.setCollapsed(True)

    def checkFavorites(self):
        if not self.favoriteModel.rowCount():
            self.favoriteBox.setEnabled(False)
            self.favoriteBox.setCollapsed(True)

    def fileSystemMenu(self, pos):
        index = self.fileSystemView.indexAt(pos)
        menu = QtWidgets.QMenu()
        addFavoriteAction = False
        if index.isValid() and index.data() != '/':
            info = self.fileSystemModel.fileInfo(index)
            if info.isDir():
                if index.data() == '..':
                    index = self.fileSystemView.rootIndex()
                    info = self.fileSystemModel.fileInfo(index)
                path = info.absoluteFilePath()
                baseName = info.completeBaseName()
#                print(path, info.completeBaseName(), self.fileSystemModel.filePath(self.fileSystemView.rootIndex()))
            else:
                path = info.absolutePath()
                baseName = QtCore.QFileInfo(path).completeBaseName()
            if path and not self.favoriteModel.match(
                self.favoriteModel.index(0, 1), QtCore.Qt.DisplayRole, path, -1, QtCore.Qt.MatchExactly):
                    addFavoriteAction = menu.addAction(QtGui.QIcon.fromTheme('emblem-favorite'), 'Add "{}" to favorites'.format(baseName))
                    menu.addSeparator()
        goHomeAction = menu.addAction(QtGui.QIcon.fromTheme('go-home'), 'Go Home')
        goHomeAction.setData(QtGui.QDesktopServices.storageLocation(QtGui.QDesktopServices.HomeLocation))
        res = menu.exec_(QtGui.QCursor.pos())
        if res == addFavoriteAction:
            self.addFavorite(index)

    def recentMenu(self, pos):
        if not self.recentModel.rowCount():
            return
        index = self.recentView.indexAt(pos)
        menu = QtWidgets.QMenu()
        if index.isValid():
            openPathAction = menu.addAction(QtGui.QIcon.fromTheme('document-open'), 'Show parent directory')
            openPathAction.triggered.connect(lambda: self.setCurrentDirectory(
                self.fileSystemModel.index(QtCore.QFileInfo(index.data(PathRole)).absolutePath())))
            copyPathAction = menu.addAction(QtGui.QIcon.fromTheme('edit-copy'), 'Copy path')
            copyPathAction.triggered.connect(lambda: QtWidgets.QApplication.clipboard().setText(
                QtCore.QDir.toNativeSeparators(index.data(PathRole))))
            menu.addSeparator()
            removeAction = menu.addAction(QtGui.QIcon.fromTheme('edit-delete'), 'Remove')
            removeAction.setData(index)
            menu.addSeparator()
        removeAllAction = menu.addAction(QtGui.QIcon.fromTheme('edit-delete'), 'Clear recent files')
        res = menu.exec_(QtGui.QCursor.pos())
        if not res:
            return
        elif res == removeAllAction:
            if QtWidgets.QMessageBox.question(self, 'Remove all recent files', 
                'Do you want to clear all your recent files?', 
                QtWidgets.QMessageBox.Ok|QtWidgets.QMessageBox.Cancel) == QtWidgets.QMessageBox.Ok:
                    self.settings.beginGroup('WaveTables')
                    self.settings.remove('RecentFiles')
                    self.settings.endGroup()
                    for _ in range(self.recentModel.rowCount()):
                        self.recentModel.takeRow(0)
        elif res.data():
            recents = []
            for row in range(self.recentModel.rowCount()):
                if row == index.row():
                    continue
                index = self.recentModel.index(row, 0)
                recents.append(index.data(PathRole))
            self.settings.beginGroup('WaveTables')
            if recents:
                self.settings.setValue('RecentFiles', recents)
            else:
                self.settings.remove('RecentFiles')
            self.settings.endGroup()
            self.recentModel.takeRow(index.row())
        self.checkRecents()

    def favoriteMenu(self, pos):
        if not self.favoriteModel.rowCount():
            return
        index = self.favoriteView.indexAt(pos)
        menu = QtWidgets.QMenu()
        if index.isValid():
            if index.sibling(index.row(), 0).data(HomeRole):
                setHome = False
                text = 'Unset as default'
            else:
                setHome = True
                text = 'Set as default'
            homeAction = menu.addAction(QtGui.QIcon.fromTheme('go-home'), text)
            copyPathAction = menu.addAction(QtGui.QIcon.fromTheme('edit-copy'), 'Copy path')
            copyPathAction.triggered.connect(lambda: QtWidgets.QApplication.clipboard().setText(
                QtCore.QDir.toNativeSeparators(index.data(PathRole))))
            menu.addSeparator()
            removeAction = menu.addAction(QtGui.QIcon.fromTheme('edit-delete'), 'Remove')
            removeAction.setData(index)
            menu.addSeparator()
        else:
            homeAction = False
        removeAllAction = menu.addAction(QtGui.QIcon.fromTheme('edit-delete'), 'Clear favorites')
        res = menu.exec_(QtGui.QCursor.pos())
        if not res:
            return
        elif res == removeAllAction:
            if QtWidgets.QMessageBox.question(self, 'Remove all favorites', 
                'Do you want to clear all your favorite directories?', 
                QtWidgets.QMessageBox.Ok|QtWidgets.QMessageBox.Cancel) == QtWidgets.QMessageBox.Ok:
                    self.settings.beginGroup('WaveTables')
                    self.settings.remove('Favorites')
                    self.settings.remove('BrowseHome')
                    self.settings.endGroup()
                    for _ in range(self.favoriteModel.rowCount()):
                        self.favoriteModel.takeRow(0)
            self.favoriteView.resizeColumnToContents(0)
        elif res == homeAction:
            self.settings.beginGroup('WaveTables')
            if setHome:
                for row in range(self.favoriteModel.rowCount()):
                    iconIndex = index.sibling(row, 0)
                    if index.row() == row:
                        self.favoriteModel.setData(iconIndex, QtGui.QIcon.fromTheme('go-home'), QtCore.Qt.DecorationRole)
                        self.favoriteModel.setData(iconIndex, True, HomeRole)
                        self.settings.setValue('BrowseHome', index.sibling(row, 1).data(PathRole))
                    else:
                        self.favoriteModel.setData(iconIndex, None, QtCore.Qt.DecorationRole)
                        self.favoriteModel.setData(iconIndex, None, HomeRole)
            else:
                iconIndex = index.sibling(index.row(), 0)
                self.favoriteModel.setData(iconIndex, None, QtCore.Qt.DecorationRole)
                self.favoriteModel.setData(iconIndex, None, HomeRole)
                self.settings.remove('BrowseHome')
            self.settings.endGroup()
            self.favoriteView.resizeColumnToContents(0)
        elif res.data():
            favorites = []
            for row in range(self.favoriteModel.rowCount()):
                if row == index.row():
                    continue
                favorites.append((self.favoriteModel.index(row, 1).data(PathRole)))
            self.settings.beginGroup('WaveTables')
            if favorites:
                self.settings.setValue('Favorites', favorites)
            else:
                self.settings.remove('Favorites')
            self.settings.endGroup()
            self.favoriteModel.takeRow(index.row())
        self.checkFavorites()

    def addFavorite(self, index):
        self.settings.beginGroup('WaveTables')
        favorites = self.settings.value('Favorites', [])
        fileInfo = self.fileSystemModel.fileInfo(index)
        if not fileInfo.isDir():
            print('beh?!')
            fileInfo = QtCore.QFileInfo(fileInfo.absolutePath())
        favorites.append(fileInfo.absoluteFilePath())
        self.settings.setValue('Favorites', favorites)
        self.settings.endGroup()
        nameItem = QtGui.QStandardItem(fileInfo.fileName())
        nameItem.setData(fileInfo.absoluteFilePath(), PathRole)
        locationItem = QtGui.QStandardItem(QtCore.QDir.toNativeSeparators(fileInfo.absoluteFilePath()))
        locationItem.setData(fileInfo.absoluteFilePath(), PathRole)
        self.favoriteModel.appendRow([nameItem, locationItem])
        self.favoriteBox.setCollapsed(False)
        self.favoriteBox.setEnabled(True)
        self.favoriteView.setVisible(True)
        self.favoriteView.resizeColumnToContents(0)
        self.favoriteView.resizeRowsToContents()

#    def directoryChanged(self, path):
#        self.pathLbl.setText(self.fontMetrics().elidedText(path, QtCore.Qt.ElideMiddle, self.pathLbl.width()))
#        self.fileSystemView.resizeColumnToContents(1)
#        self.fileSystemView.resizeRowsToContents()

    def updatePathCombo(self, update=True):
        path = self.fileSystemModel.filePath(self.fileSystemView.rootIndex())
        nativePath = QtCore.QDir.toNativeSeparators(path)
        if self.sender() != self.pathCombo:
            self.pathCombo.setEditText(nativePath)
        if update:
            self.settings.beginGroup('WaveTables')
            if not self.settings.contains('BrowseHome'):
                self.settings.setValue('BrowsePath', path)
            self.settings.endGroup()

    def openFavorite(self, index):
        path = index.data(PathRole)
        if QtCore.QFile.exists(path):
            self.history.append(self.fileSystemModel.filePath(self.fileSystemView.rootIndex()))
            newIndex = self.fileSystemModel.index(path)
            self.fileSystemView.setRootIndex(newIndex)
            self.favoriteModel.setData(index.sibling(index.row(), 0), None, QtCore.Qt.ForegroundRole)
            self.favoriteModel.setData(index.sibling(index.row(), 1), None, QtCore.Qt.ForegroundRole)
            self.goBackBtn.setEnabled(True)
            self.updatePathCombo()
        else:
            self.favoriteModel.setData(index.sibling(index.row(), 0), QtGui.QColor(QtCore.Qt.red), QtCore.Qt.ForegroundRole)
            self.favoriteModel.setData(index.sibling(index.row(), 1), QtGui.QColor(QtCore.Qt.red), QtCore.Qt.ForegroundRole)
            self.favoriteView.setCurrentIndex(QtCore.QModelIndex())

    def setCurrentDirectory(self, index):
        if self.fileSystemModel.isDir(index):
#            self.history.append(self.fileSystemModel.filePath(newIndex))
            self.history.append(self.fileSystemModel.filePath(self.fileSystemView.rootIndex()))
            newIndex = self.fileSystemModel.index(self.fileSystemModel.filePath(index))
            self.fileSystemView.setRootIndex(newIndex)
            self.goBackBtn.setEnabled(True)
            self.updatePathCombo()

    def goBack(self):
        self.fileSystemView.setRootIndex(self.fileSystemModel.index(self.history[-1]))
        self.history.pop(len(self.history) - 1)
        self.goBackBtn.setEnabled(len(self.history))
        self.updatePathCombo()

    def goUp(self):
        current = self.fileSystemView.rootIndex()
        if current != current.parent():
            self.history.append(self.fileSystemModel.filePath(current))
            self.fileSystemView.setRootIndex(current.parent())
            self.goBackBtn.setEnabled(True)
            self.updatePathCombo()

    def setFormatFilter(self, index):
        self.fileSystemModel.setNameFilters(self.formatCombo.itemData(index))

    def resizeEvent(self, event):
        self.updatePathCombo()


class WaveSourceView(QtWidgets.QGraphicsView):
    zoom = QtCore.pyqtSignal(int)
    scroll = QtCore.pyqtSignal(int)
    selectionChanged = QtCore.pyqtSignal(object)

    _previewMode = True
    rubberSelectRect = adjustedRect = selectRect = currentSelection = None
    maybeDrag = False
    offset = 0
    selected = []
    offsetPen = QtGui.QPen(QtCore.Qt.white, .5)
    offsetPen.setCosmetic(True)
    offsetPenThin = QtGui.QPen(QtCore.Qt.white, .15)
    offsetPenThin.setCosmetic(True)
    selectionBrush = QtGui.QColor(120, 120, 120, 120)
    mousePos = QtCore.QPoint()

    drawBackground = lambda self, qp, rect: QtWidgets.QGraphicsView.drawBackground(self, qp, rect)
    paintEvent = lambda self, event: QtWidgets.QGraphicsView.paintEvent(self, event)
#    drawForeground = lambda self, qp, rect: QtWidgets.QGraphicsView.drawForeground(self, qp, rect)

    @property
    def previewMode(self):
        return self._previewMode

    @previewMode.setter
    def previewMode(self, mode):
        self._previewMode = mode
        self.drawBackground = self.drawBackground2
        self.paintEvent = self.paintEvent2
        self.currentRect = QtCore.QRectF()
        self.currentTransform = self.transform()
        self.fullScene = self.scene()
#        self.setDragMode(self.ScrollHandDrag)
        self.setMouseTracking(True)

    def drawBackground2(self, qp, rect):
        QtWidgets.QGraphicsView.drawBackground(self, qp, rect)
        if (rect != self.currentRect and not self.currentRect.contains(rect)) or self.transform() != self.currentTransform:
            self.fullScene.updateRect(rect)
            self.currentRect = rect
            self.currentTransform = self.transform()

    def setOffset(self, offset):
        self.offset = offset
        self.viewport().update()
#        for chunks in self.scene().chunks:
#            [chunk.setOffset(offset) for chunk in chunks]

    def setSelection(self, start, count):
        self.currentSelection = start, count
        if count:
            self.selected = list(chain(*self.scene().chunks[start:start + count]))
        else:
            self.selected = []
        self.viewport().update()

    def startDrag(self):
        parent = self.parent()
        while not isinstance(parent, QtWidgets.QTabWidget):
            parent = parent.parent()
        self.dragObject = ActivateDrag(self)
        start, count = self.currentSelection

        mimeData = QtCore.QMimeData()
        byteArray = QtCore.QByteArray()
        stream = QtCore.QDataStream(byteArray, QtCore.QIODevice.WriteOnly)
        stream.writeQVariant(self.window().uuid)
        stream.writeInt(parent.currentIndex())
        stream.writeInt(count)

        start = start * 128 + self.offset
        outValues = self.scene().outValues
        for slice in range(count):
            stream.writeQVariant(outValues[start + slice * 128:start + (slice + 1) * 128])
        stream.writeQVariant(self.scene().currentInfo.name)
        mimeData.setData('bigglesworth/WaveFileData', byteArray)
        self.dragObject.setMimeData(mimeData)
        self.dragObject.exec_(QtCore.Qt.CopyAction)
        self.maybeDrag = False

    def mousePressEvent(self, event):
        if self.previewMode:
            if self.scene().loadItem:
                self.scene().drawWaveFile()
        else:
            self.mousePos = event.pos()
            if event.modifiers() == QtCore.Qt.ShiftModifier:
                #using QRect(mousePos, mousePos) gives an 1x1 rect, we need it empty
                self.rubberSelectRect = QtCore.QRect(self.mousePos.x(), self.mousePos.y(), 0, 0)
                self.adjustedRect = QtCore.QRect(self.mousePos.x(), 0, 1, self.viewport().height())
                self.selected = []
            else:
                if event.modifiers() == QtCore.Qt.ControlModifier:
                    self.setDragMode(self.ScrollHandDrag)
                elif not event.modifiers() and self.selectRect and event.pos() in self.selectRect:
                    self.maybeDrag = True
                QtWidgets.QGraphicsView.mousePressEvent(self, event)

    def mouseMoveEvent(self, event):
        if event.buttons() == QtCore.Qt.LeftButton:
            if self.maybeDrag:
                if (event.pos() - self.mousePos).manhattanLength() > QtWidgets.QApplication.startDragDistance():
                    self.startDrag()
            elif self.rubberSelectRect is not None:
#                self.rubberSelectRect = QtCore.QRect(self.mousePos, event.pos())
                self.rubberSelectRect.setBottomRight(event.pos())
                self.adjustedRect.setRight(event.pos().x())
                if not self.adjustedRect.width():
                    self.adjustedRect.setWidth(1)
#                items = sorted([i for i in self.items(self.adjustedRect.normalized()) if isinstance(i, ChunkItem)], key=lambda chunk: chunk.index)[:64]
                #for non-mono files we have multiple parallel chunks, 
                #so we use a dict to get unique indexes for the selection
                items = {chunk.index:chunk for chunk in self.items(self.adjustedRect.normalized()) if isinstance(chunk, ChunkItem)}
                items = sorted(items.values(), key=lambda chunk: chunk.index, reverse=self.adjustedRect.width() < 0)[:64]
                if items != self.selected:
                    self.selectionChanged.emit(items)
                    self.selected = items
                self.viewport().update()
            else:
                #create alternate event to avoid Y scrolling
                pos = event.pos()
                pos.setY(self.mousePos.y())
                event = QtGui.QMouseEvent(event.type(), pos, event.button(), event.buttons(), event.modifiers())
        QtWidgets.QGraphicsView.mouseMoveEvent(self, event)

    def mouseReleaseEvent(self, event):
        if self.rubberSelectRect is not None:
#            items = sorted([i for i in self.items(self.adjustedRect.normalized()) if isinstance(i, ChunkItem)], key=lambda chunk: chunk.index)[:64]
            items = {chunk.index:chunk for chunk in self.items(self.adjustedRect.normalized()) if isinstance(chunk, ChunkItem)}
            items = sorted(items.values(), key=lambda chunk: chunk.index, reverse=self.adjustedRect.width() < 0)[:64]
            if items:
                self.currentSelection = items[0].index, len(items)
            if items != self.selected:
                self.selectionChanged.emit(items)
                self.selected = items
        elif not self._previewMode and event.modifiers() == QtCore.Qt.ShiftModifier:
            items = [i for i in self.items(self.adjustedRect.normalized()) if isinstance(i, ChunkItem)]
            if items and items != self.selected:
                #select the first item, in case the cursor was between two items
                self.selectionChanged.emit(items[:1])
                self.selected = items[:1]
        self.rubberSelectRect = None
        self.viewport().update()
        QtWidgets.QGraphicsView.mouseReleaseEvent(self, event)

    def keyPressEvent(self, event):
        if event.modifiers() == QtCore.Qt.ControlModifier:
            self.setDragMode(self.ScrollHandDrag)
        else:
            self.setDragMode(self.NoDrag)
        QtWidgets.QGraphicsView.keyPressEvent(self, event)

    def keyReleaseEvent(self, event):
        if event.modifiers() == QtCore.Qt.ControlModifier:
            self.setDragMode(self.ScrollHandDrag)
        else:
            self.setDragMode(self.NoDrag)
        QtWidgets.QGraphicsView.keyPressEvent(self, event)

    def wheelEvent(self, event):
        if not event.modifiers():
            self.scroll.emit(1 if event.delta() > 0 else -1)
        elif event.modifiers() == QtCore.Qt.ControlModifier:
            self.zoom.emit(1 if event.delta() > 0 else -1)

    def paintEvent2(self, event):
        QtWidgets.QGraphicsView.paintEvent(self, event)
        qp = QtGui.QPainter(self.viewport())
        ratio = self.transform().m11()
        x = -((self.currentRect.x() - self.offset) % 128) * ratio
        if self.currentRect.x() < 0:
            x -= self.currentRect.x() * ratio + x
        right = self.currentRect.right() * ratio
        qp.setPen(self.offsetPen if ratio > .03 else self.offsetPenThin)
        height = self.viewport().height()
        while x <= right:
            qp.drawLine(x, 0, x, height)
            x += 128 * ratio
        if self.rubberSelectRect is not None:
            qp.setPen(QtCore.Qt.red)
            qp.setBrush(QtGui.QColor(120, 120, 120, 120))
            qp.drawRect(self.rubberSelectRect)
        if self.selected:
            rect = self.selected[0].sceneBoundingRect()|self.selected[-1].sceneBoundingRect()
            rect = QtCore.QRectF(rect.left(), 0, rect.width(), self.sceneRect().height())
            self.selectRect = self.mapFromScene(rect).boundingRect()
            self.selectRect.setBottom(height - 2)
            qp.translate(self.offset * ratio, 0)
            qp.setPen(QtCore.Qt.NoPen)
            qp.setBrush(self.selectionBrush)
            qp.drawRect(self.selectRect)

    def resizeEvent(self, event):
        if self.previewMode:
            self.fitInView(self.sceneRect())
            self.centerOn(self.sceneRect().center())
        else:
            oldTransform = self.transform()
            sceneRect = self.sceneRect()
            transform = QtGui.QTransform().scale(oldTransform.m11(), self.viewport().height() / sceneRect.height())
            self.setTransform(transform)


class WaveSourceScene(QtWidgets.QGraphicsScene):
    baseLinePen = QtGui.QPen(QtGui.QColor(QtCore.Qt.red), .8)
    baseLinePen.setCosmetic(True)
    noPen = QtGui.QPen(QtCore.Qt.NoPen)
    wavePen = QtGui.QPen(QtGui.QColor(64, 192, 216), 1.2, cap=QtCore.Qt.RoundCap)
    wavePen.setCosmetic(True)

    waveBackground = QtGui.QLinearGradient(0, -1, 0, 1)
    waveBackground.setColorAt(0, QtGui.QColor(0, 128, 192, 64))
    waveBackground.setColorAt(.5, QtGui.QColor(0, 128, 192, 192))
    waveBackground.setColorAt(1, QtGui.QColor(0, 128, 192, 64))

    waveFilePen = QtGui.QPen(QtGui.QBrush(waveBackground), 1)
    waveFilePen.setCosmetic(True)

    playPen = QtGui.QPen(QtGui.QColor('orange'))
    playPen.setCosmetic(True)

    loadingStarted = QtCore.pyqtSignal(bool)
    loading = QtCore.pyqtSignal()
    loaded = QtCore.pyqtSignal(bool)

    waveCache = {}

    def __init__(self, view):
        QtWidgets.QGraphicsScene.__init__(self)
#        self.tabWidget = tabWidget
        self.view = view
        self.waveItems = []
        self.zeroLines = []
        self.waveData = None
        self.loadItem = None
        self.currentInfo = None
        self.updateTimer = QtCore.QTimer()
        self.updateTimer.setSingleShot(True)
        self.updateTimer.setInterval(250)
        self.updateTimer.timeout.connect(self.updateChunks)

    def setEmpty(self):
        self.clear()
        self.waveData = None
        self.loadItem = None

    def setInvalid(self):
        self.clear()
        self.waveData = None
        self.loadItem = None
        invalidItem = InvalidItem()
        self.addItem(invalidItem)
        self.view.setTransform(QtGui.QTransform())
        self.setSceneRect(invalidItem.sceneBoundingRect())
        self.view.centerOn(invalidItem.sceneBoundingRect().center())

    def setPreviewData(self, waveData, info, force=False):
        if waveData is self.waveData:
            self.loaded.emit(True)
            return True
        self.currentInfo = info
        self.waveData = waveData

        self.clear()
        if force or self.waveData.shape[0] <= 262144 or info.name in self.waveCache:
            self.drawWaveFile()
            self.loaded.emit(True)
            return True
        else:
            self.loadItem = LoadItem()
            self.addItem(self.loadItem)
            self.view.setTransform(QtGui.QTransform())
            self.setSceneRect(self.loadItem.sceneBoundingRect())
            self.view.centerOn(self.loadItem.sceneBoundingRect().center())
            self.loaded.emit(False)
            return False

    def drawWaveFile(self):
        self.loadItem = None
        self.clear()
        self.loadingStarted.emit(False)
        QtWidgets.QApplication.processEvents()

        self.waveItems = []
        self.zeroLines = []
        samples, channels = self.waveData.shape

        cachedPaths = self.waveCache.get(self.currentInfo.name)
        if cachedPaths:
            for channel in range(channels):
                path = cachedPaths[channel]
                waveItem = self.addPath(path)
                waveItem.setY(1 + 2.1 * channel)
                waveItem.setPen(self.waveFilePen)
                self.waveItems.append(waveItem)

                #see below
#                lineItem = self.addLine(0, 0, waveItem.sceneBoundingRect().width(), 0)
                lineItem = self.addLine(0, 0, path.elementAt(path.elementCount() - 1).x + .5, 0)
                lineItem.setY(waveItem.pos().y())
                lineItem.setPen(self.baseLinePen)
                self.zeroLines.append(lineItem)

        else:
            ratio = max(2, samples / 4096)
            count = samples / ratio
            paths = []
            for channel in range(channels):
                data = self.waveData[:, channel]

                path = QtGui.QPainterPath()
                for slice in xrange(count):
                    pos = ratio * slice
                    sliceData = data[pos: ratio * (slice + 1)]
                    maxValue = max(0, max(sliceData))
                    minValue = min(0, min(sliceData))
                    
                    path.moveTo(pos + .5, -maxValue)
                    path.lineTo(pos + .5, -minValue)
                paths.append(path)

                waveItem = self.addPath(path)
                waveItem.setY(1 + 2.1 * channel)
                waveItem.setPen(self.waveFilePen)
                self.waveItems.append(waveItem)

#                lineItem = self.addLine(0, 0, waveItem.sceneBoundingRect().width(), 0)
                #fix for silent files (path would be empty)
                lineItem = self.addLine(0, 0, path.elementAt(path.elementCount() - 1).x + .5, 0)
                lineItem.setY(waveItem.pos().y())
                lineItem.setPen(self.baseLinePen)
                self.zeroLines.append(lineItem)
                self.loading.emit()
            self.waveCache[self.currentInfo.name] = paths

        rect = QtCore.QRectF(0, 0, 0, 2)
        rect.setRight(self.zeroLines[0].sceneBoundingRect().right())
        rect.setBottom(self.zeroLines[-1].pos().y() + 1)

        self.playhead = self.addLine(0, 0, 0, rect.height())
        self.playhead.setPen(self.playPen)
        self.playhead.setVisible(False)

        self.setSceneRect(rect)
        self.view.centerOn(rect.center())
        self.view.fitInView(rect)
        self.loaded.emit(True)
#        self.view.centerOn(rect.center())

        if waveItem.boundingRect().isNull():
            silentItem = SilentItem()
            self.addItem(silentItem)
            silentItem.setPos(rect.center())

    def importCurrent(self, mixer):
#        self.clear()
        self.mixer = mixer
        mixer.gainChanged.connect(self.updateTimer.start)
        mixer.channelsChanged.connect(self.updateTimer.start)
        ratio = mixer.channelValues[0]
        [waveItem.setVisible(False) for waveItem in self.waveItems]

        self.loadingStarted.emit(True)
        QtWidgets.QApplication.processEvents()

        samples, channels = self.waveData.shape
        count = samples / 128

        self.inChunks = [[] for _ in range(count)]
        for channel in range(channels):
            data = self.waveData[:, channel]
            y = 1 + channel * 2.1
            for slice in xrange(count):
#                chunkData = data[slice * 128:(slice + 1) * 128]
                chunk = ChunkItem(data, slice)
                self.addItem(chunk)
                self.inChunks[slice].append(chunk)
                chunk.setPos(slice * 128, y)

        self.outValues = np.sum(self.waveData, axis=1) * ratio
        self.outChunks = []
        outCenter = 1 + (y - 1) / 2
        for slice in xrange(count):
            chunk = ChunkItem(self.outValues, slice)
            self.addItem(chunk)
            self.outChunks.append([chunk])
            chunk.setPos(slice * 128, outCenter)

        if channels == 1:
            self.outZeroLine = self.zeroLines[0]
            [line.setVisible(False) for line in self.zeroLines[1:]]
        else:
            self.outZeroLine = QtWidgets.QGraphicsLineItem(self.zeroLines[0].line())
            self.addItem(self.outZeroLine)
            self.outZeroLine.setPen(self.baseLinePen)
            self.outZeroLine.setY(outCenter)
            [line.setVisible(False) for line in self.zeroLines]

        self.totChunks = len(self.outChunks)
        [z.setZValue(10) for z in self.zeroLines]
        visible = []
        for c in range(min(64, self.totChunks)):
            for chunk in self.outChunks[c]:
                visible.append(chunk)
                chunk.setVisible(True)
            
        self.view.previewMode = False
#        visible = [self.chunks[c] for c in range(min(64, len(self.chunks)))]
        rect = visible[0].sceneBoundingRect()|visible[-2 * channels].sceneBoundingRect()
        rect.setTop(0)
        rect.setBottom(2 * channels)

        self.chunks = self.outChunks
        self.visible = set(visible)
        self.loaded.emit(True)
        self.view.fitInView(rect)

    def updateRect(self, rect):
        visible = set()
        first = max(0, int(rect.x() / 128))
        count = min(self.totChunks - first, int(rect.width() / 128) + 2)
#        print(self.totChunks, first, count)
        for c in range(first, first + count):
            for chunk in self.chunks[c]:
                visible.add(chunk)
                self.visible.discard(chunk)
                chunk.setVisible(True)
        [chunk.setVisible(False) for chunk in self.visible]
        self.visible = visible
        self.lastRect = rect

    def setMode(self, mode):
        if mode:
            self.chunks = self.outChunks
            [line.setVisible(False) for line in self.zeroLines]
            self.outZeroLine.setVisible(True)
        else:
            self.chunks = self.inChunks
            self.outZeroLine.setVisible(False)
            [line.setVisible(True) for line in self.zeroLines]
        self.updateRect(self.lastRect)

    def updateChunks(self):
        newValues = np.sum(self.waveData * self.mixer.channelValues, axis=1) * self.mixer.gain
        np.copyto(self.outValues, newValues)
        [chunk.invalidate() for chunks in self.outChunks for chunk in chunks]
        self.mixer.setValid(np.amax(newValues) < 1 and np.amin(newValues) > -1)

    def setPlayhead(self, secs):
        self.playhead.setX(secs * self.sceneRect().width() / self.currentInfo.duration)


