import numpy as np

from xml.etree import ElementTree as ET
from Qt import QtCore, QtGui, QtWidgets
from PyQt4.QtCore import qCompress

from bigglesworth.utils import loadUi, localPath
from bigglesworth.widgets import Waiter
from bigglesworth.wavetables.utils import parseTime

import soundfile

FileInfoRole = QtCore.Qt.UserRole + 1
FilePathRole = FileInfoRole + 1
WaveDataRole = FilePathRole + 1

#this is for dev mode only...
class WaveTableArchiver(QtWidgets.QDialog):
    def __init__(self, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        loadUi('ui/wtarchiver.ui', self)
        self.fileModel = QtGui.QStandardItemModel()
        self.fileView.setModel(self.fileModel)
        self.fileModel.setHorizontalHeaderLabels(['Name', 'Slot', 'File'])

        self.fileView.horizontalHeader().setResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.fileView.horizontalHeader().setResizeMode(1, QtWidgets.QHeaderView.Fixed)
        self.fileView.horizontalHeader().setResizeMode(2, QtWidgets.QHeaderView.Stretch)
        self.fileView.verticalHeader().setDefaultSectionSize(self.fontMetrics().height() * 1.2)
        self.fileView.resizeColumnToContents(1)

        self.addBtn.clicked.connect(self.addFiles)
        self.removeBtn.clicked.connect(self.removeFiles)
        self.removePrefixBtn.clicked.connect(self.removePrefix)

        self.fileView.clicked.connect(self.updatePanel)

        self.nameEdit.textEdited.connect(self.updateData)
        self.slotSpin.valueChanged.connect(self.updateData)

        self.saveBtn = self.buttonBox.button(self.buttonBox.Save)
        self.saveBtn.setEnabled(False)
        self.saveBtn.clicked.connect(self.export)

        self.fileModel.dataChanged.connect(self.checkData)

    def removeFiles(self):
        selected = self.fileView.selectionModel().selectedRows()
        if not selected:
            return
        for index in sorted(selected, key=lambda i: i.row(), reverse=True):
            self.fileModel.takeRow(index.row())

    def addFiles(self):
        files = QtWidgets.QFileDialog.getOpenFileNames(self, 'Select files', localPath('../test/blofeld'))
        for filePath in sorted(files):
            try:
                info = soundfile.info(filePath)
                assert info.channels == 1, 'Not mono!'
                assert info.frames <= 8192, 'Too long!: {}'.format(info.frames)
                waveData, sampling = soundfile.read(filePath, always_2d=True, dtype='float32')
                self.addData(filePath, waveData[:, 0])
            except Exception as e:
                print(filePath, e)
        self.updatePanel()
        self.checkData()

    def addData(self, filePath, waveData):
        res = self.fileModel.match(self.fileModel.index(0, 2), FilePathRole, filePath, flags=QtCore.Qt.MatchExactly)
        if res:
            self.fileView.setCurrentIndex(res[0])
            return
        fileInfo = QtCore.QFileInfo(filePath)
        fileItem = QtGui.QStandardItem(fileInfo.fileName())
        fileItem.setEditable(False)
        fileItem.setData(fileInfo, FileInfoRole)
        fileItem.setData(filePath, FilePathRole)
        fileItem.setData([waveData[p:p+128] for p in xrange(0, len(waveData), 128)], WaveDataRole)
        slotCount = self.fileModel.rowCount()
        if slotCount:
            for slot in range(1, slotCount + 1):
                if not self.fileModel.match(self.fileModel.index(0, 1), QtCore.Qt.DisplayRole, slot, flags=QtCore.Qt.MatchExactly):
                    break
            else:
                slot += 1
        else:
            slot = 1
        slotItem = QtGui.QStandardItem()
        slotItem.setData(slot, QtCore.Qt.DisplayRole)

        nameItem = QtGui.QStandardItem(fileInfo.completeBaseName())

        self.fileModel.appendRow([nameItem, slotItem, fileItem])

    def updatePanel(self, index=None):
        self.slotSpin.blockSignals(True)
        if not index or len(self.fileView.selectionModel().selectedRows()) > 1:
            self.nameEdit.setText('')
            self.nameEdit.setEnabled(False)
            self.slotSpin.setValue(0)
            self.slotSpin.setEnabled(False)
        else:
            self.nameEdit.setText(index.sibling(index.row(), 0).data())
            self.nameEdit.setEnabled(True)
            self.slotSpin.setValue(index.sibling(index.row(), 1).data())
            self.slotSpin.setEnabled(True)
        self.slotSpin.blockSignals(False)

    def updateData(self):
        current = self.fileView.currentIndex()
        if not current or not current.isValid():
            return
        self.fileModel.setData(current.sibling(current.row(), 0), self.nameEdit.text())
        self.fileModel.setData(current.sibling(current.row(), 1), self.slotSpin.value())

    def checkData(self):
        names = set()
        slots = set()
        for row in range(self.fileModel.rowCount()):
            name = self.fileModel.item(row, 0).text()
            if name in names:
                break
            names.add(name)
            slot = self.fileModel.item(row, 1).data(QtCore.Qt.DisplayRole)
            if slot in slots:
                break
            slots.add(slot)
        else:
            self.saveBtn.setEnabled(True)
            return
        self.saveBtn.setEnabled(False)

    def removePrefix(self):
        for row in range(self.fileModel.rowCount()):
            item = self.fileModel.item(row, 0)
            splitted = item.text().split()
            for i, s in enumerate(splitted):
                if s.isdigit():
                    continue
                break
            item.setText(' '.join(splitted[i:]))

    def export(self):
        filePath = QtWidgets.QFileDialog.getSaveFileName(self, 'Export wavetables', QtCore.QDir.tempPath() + '/export.bwt')
        if not filePath:
            return

        file = QtCore.QFile(filePath)
        file.open(QtCore.QIODevice.WriteOnly)
        stream = QtCore.QDataStream(file)

        count = self.fileModel.rowCount()
        progress = QtWidgets.QProgressDialog('Exporting', '', 0, count, self)
        progress.setWindowTitle('Exporting {} wavetables'.format(count))
        progress.setCancelButton(None)
        root = ET.Element('Bigglesworth')
        typeElement = ET.SubElement(root, 'WaveTableData')
        countElement = ET.SubElement(typeElement, 'Count')
        countElement.text = str(count)
        fullData = []
        
        from bigglesworth.wavetables.keyframes import VirtualKeyFrames
        keyFrames = VirtualKeyFrames()

        for row in range(count):
            progress.setValue(row)

            waveData = self.fileModel.index(row, 2).data(WaveDataRole)
            print(type(waveData))
            keyFrames.setValuesMulti(0, waveData, fromFile=True)

            name = self.fileModel.index(row, 0).data()
            slot = self.fileModel.index(row, 1).data()

            byteArray = QtCore.QByteArray()
            kfStream = QtCore.QDataStream(byteArray, QtCore.QIODevice.WriteOnly)
            kfStream.writeQVariant(keyFrames.getSnapshot())
            fullData.append(qCompress(byteArray))

            wtElement = ET.SubElement(typeElement, 'WaveTable')
            ET.SubElement(wtElement, 'Name').text = name
            ET.SubElement(wtElement, 'Slot').text = str(slot)
            ET.SubElement(wtElement, 'WaveCount').text = str(len(keyFrames))


        stream.writeString(ET.tostring(root))
        try:
            for data in fullData:
                stream.writeQVariant(data)
        except Exception as e:
            print('Error writing?', e)

        progress.setValue(progress.maximum())

        file.close()


class WaveExportDialog(QtWidgets.QDialog):
    sampleShape = np.arange(.0, 128., .0625)
    sampleRange = np.arange(129.)
    waveShape = np.arange(0., 8192., .0625)
    waveRange = np.arange(8193.)

    serumTooltip = [
        'Each sample will be repeated 16 times', 
        'All sample values will be interpolated, values at the end of each ' \
        'wave will interpolate to its beginning', 
        'All sample values will be interpolated across the whole table, the ' \
        'final wave will be interpolated with the first one'
    ]

    def __init__(self, parent, waveData):
        QtWidgets.QDialog.__init__(self, parent)
        loadUi('ui/waveexport.ui', self)
        iconHeight = int(self.fontMetrics().height() * .8)
        self.firstSampleChk.setVisible(parent.devMode)
        for wave in waveData:
            for value in wave:
                if not -32768 <= value <= 32767:
                    self.clipLbl.setEnabled(True)
                    self.clipLbl.setText('''
                        <img src=":/icons/Bigglesworth/16x16/emblem-warning" 
                        height="{}"> clipping detected!'''.format(iconHeight))
                    break
            else:
                continue
            break
        self.waveData = [wave.astype('int32') for wave in waveData]

        self.serumWhatLbl.setPixmap(QtGui.QIcon.fromTheme('question').pixmap(iconHeight))
        self.serumWhatLbl.setToolTip('''
        While Blofeld's wavetables are based on 128 samples per cycle, Serum uses 2048 samples.<br/>
            Intermediate values will be computed according to this option.<br/><br/>
            - <img src=":/icons/Bigglesworth/22x22/labplot-xy-smoothing-curve" height={s}> 
                <b>None</b>: each sample is repeated 16 times<br/>
            - <img src=":/icons/Bigglesworth/22x22/labplot-xy-interpolation-curve" height={s}> 
                <b>Wave based</b>: source samples are distributed every 16 output samples, 
                intermediate values are interpolated. The final sample of each wave is 
                interpolated with the first sample.<br/>
            - <img src=":/icons/Bigglesworth/22x22/labplot-xy-equation-curve" height={s}> 
                <b>Table based</b>: same as "Wave based", but only the final value of the 
                final wave is interpolated with the first value of the first wave.
        '''.format(s=max(16, self.font().pointSize())))
        self.serumCombo.currentIndexChanged.connect(lambda i: self.serumCombo.setToolTip(self.serumTooltip[i]))
        self.serumCombo.setToolTip(self.serumTooltip[0])

    def exec_(self):
        if not QtWidgets.QDialog.exec_(self):
            return

        waveData = np.copy(self.waveData)
        if self.layoutSerum.isChecked():
            if not self.serumCombo.currentIndex():
                waveData = np.repeat(np.concatenate(waveData), 16)
            elif self.serumCombo.currentIndex() == 1:
                waves = []
                for wave in waveData:
                    wave = np.append(wave, wave[0])
                    waves.append(np.interp(self.sampleShape, self.sampleRange, wave))
                waveData = np.concatenate(waves)
            else:
                waves = np.append(np.concatenate(waveData), waveData[0][0])
                waveData = np.interp(self.waveShape, self.waveRange, waves)
        else:
            waveData = np.concatenate(waveData)

        if not self.bitCombo.currentIndex():
            subType = 'PCM_16'
            if self.s16iDecimateMax.isChecked():
                np.clip(waveData, -32768, 32767, out=waveData)
#            elif self.s16iDecimateMin.isChecked():
#                np.right_shift(waveData, 5, out=waveData)
            else:
                np.multiply(waveData, .03125, out=waveData)
            waveData = waveData.astype('int16')
        elif self.bitCombo.currentIndex() == 1:
            subType = 'PCM_24'
            if self.s24iRound.isChecked():
                np.multiply(waveData, 8, out=waveData)
        elif self.bitCombo.currentIndex() == 2:
            subType = 'PCM_32'
            np.multiply(waveData, 2048, out=waveData)
        elif self.bitCombo.currentIndex() == 3:
            subType = 'FLOAT'
            waveData = np.divide(waveData, 2.**20).astype('float32')

        return waveData, subType


class UndoView(QtWidgets.QUndoView):
    def __init__(self, undoStack):
        QtWidgets.QUndoView.__init__(self, undoStack)
        self.setWindowTitle('Wave table undo list')
        self.setEmptyLabel('New wave table')

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self.hide()
        else:
            QtWidgets.QUndoView.keyPressEvent(self, event)

    def show(self):
        QtWidgets.QUndoView.show(self)
        self.activateWindow()


class AdvancedProgressBar(QtWidgets.QProgressBar):
    count = 1

    def text(self):
        percent = QtWidgets.QProgressBar.text(self)
        return '{}/{} ({}%)'.format(self.value() / 64, self.count / 64, percent)

    def setCount(self, count):
        self.count = count * 64
        self.setMaximum(self.count)


class Dumper(QtWidgets.QDialog):
    stopRequested = QtCore.pyqtSignal()
    started = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.setWindowTitle('Wavetable dump')
        layout = QtWidgets.QGridLayout()
        self.setLayout(layout)
        self.waiter = Waiter()
        layout.addWidget(self.waiter, 0, 0, 3, 1)

        headerLayout = QtWidgets.QGridLayout()
        layout.addLayout(headerLayout, 0, 1, 1, 1)
        headerLayout.addWidget(QtWidgets.QLabel('Dumping in progress, please wait...'), 0, 0, 1, 2)
        alertIcon = QtGui.QIcon.fromTheme('emblem-warning')
        alertPixmap = QtWidgets.QLabel()
        alertPixmap.setPixmap(alertIcon.pixmap(self.fontMetrics().height() - self.fontMetrics().descent()))
        headerLayout.addWidget(alertPixmap, 1, 0)
        headerLayout.addWidget(QtWidgets.QLabel('<b>DO NOT</b> disconnect nor switch off your Blofeld!'))
        headerLayout.setHorizontalSpacing(2)

        spacer = QtWidgets.QFrame()
        spacer.setFrameStyle(spacer.HLine)
#        spacer.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred))
        layout.addWidget(spacer, 1, 1)

        partialLayout = QtWidgets.QHBoxLayout()
        layout.addLayout(partialLayout, 2, 1, 1, 1)
        partialLayout.addWidget(QtWidgets.QLabel('Sending wavetable:'))
        self.partialLabel = QtWidgets.QLabel()
        partialLayout.addWidget(self.partialLabel)
        slotLbl = QtWidgets.QLabel('Slot:')
        slotLbl.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Preferred))
        partialLayout.addWidget(slotLbl)
        self.partialSlot = QtWidgets.QLabel()
        partialLayout.addWidget(self.partialSlot)
        self.partialSlot.setMaximumWidth(self.fontMetrics().width('888'))

        self.partialProgress = QtWidgets.QProgressBar()
        layout.addWidget(self.partialProgress, 3, 1)
        self.partialProgress.setRange(1, 64)
        self.partialProgress.setFormat('%v/64')

        layout.addWidget(QtWidgets.QLabel('Overall progress:'), 4, 1)
        self.totalProgress = AdvancedProgressBar()
        self.totalProgress.setFormat('%p')
        layout.addWidget(self.totalProgress, 5, 1)

        timerLayout = QtWidgets.QGridLayout()
        layout.addLayout(timerLayout, 6, 1)
        l = QtWidgets.QLabel('Elapsed:')
        l.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Preferred))
        timerLayout.addWidget(l)
        self.elapsedLbl = QtWidgets.QLabel()
        timerLayout.addWidget(self.elapsedLbl, 0, 1)
        l = QtWidgets.QLabel('Remaining:')
        l.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Preferred))
        timerLayout.addWidget(l, 1, 0)
        self.remainingLbl = QtWidgets.QLabel()
        timerLayout.addWidget(self.remainingLbl, 1, 1)

        self.buttonBox = QtWidgets.QDialogButtonBox()
        layout.addWidget(self.buttonBox, 7, 1)
        self.stopBtn = self.buttonBox.addButton('Stop', self.buttonBox.ActionRole)
        self.stopBtn.setIcon(QtGui.QIcon.fromTheme('dialog-cancel'))
        self.stopBtn.clicked.connect(self.prepareStop)

        self.stopLbl = QtWidgets.QLabel('')
        self.buttonBox.layout().insertWidget(self.buttonBox.layout().count() - 1, self.stopLbl)

        self.tableCount = 0
        self.tableData = []

        self.elapsed = QtCore.QElapsedTimer()
        self.timer = QtCore.QTimer()
        self.timer.setSingleShot(True)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.updateCount)

    def updateCount(self):
        self.current += 1
        self.totalProgress.setValue(self.current)
        currentTable, wave = divmod(self.current, 64)
        if not wave:
            wave = 64
        self.partialProgress.setValue(wave if wave else 64)
        total = self.tableCount * 64
        if self.current < total:
            self.timer.start()
        else:
            return self.accept()
        if currentTable == self.tableCount - 1:
            self.stopBtn.setEnabled(False)
        name, slot = self.tableData[currentTable]
        self.partialLabel.setText(name)
        self.partialSlot.setText(str(slot))
        elapsed = self.elapsed.elapsed() * .001
        self.elapsedLbl.setText(parseTime(elapsed, floatSeconds=False))
        if elapsed > 5 and self.current:
            ratio = elapsed / self.current
            remaining = (total - self.current) * ratio
            if remaining < 10:
                self.remainingLbl.setText('Almost done...')
            else:
                self.remainingLbl.setText(parseTime(remaining, True, True, False))

    def closeEvent(self, event):
        event.ignore()

    def reject(self):
        pass

    def prepareStop(self):
        self.stopLbl.setText('Finishing...')
        self.tableCount = self.current // 64 + 1
        self.totalProgress.setCount(self.tableCount)
        self.stopBtn.setEnabled(False)
        self.stopRequested.emit()

#    def test(self, tableData=None):
#        tableData = [('a', 80), ('ergr', 81), ('ntoije', 84)]
#        QtCore.QTimer.singleShot(250, lambda: self.exec_(tableData))
#

    def showEvent(self, event):
        if not self.shown:
            self.shown = True
            self.started.emit()

    def exec_(self, tableData):
        self.shown = False
        self.current = 0
        self.stopLbl.setText('')
        self.tableData = tableData
        self.tableCount = len(tableData)
        self.stopBtn.setEnabled(self.tableCount > 1)
        self.totalProgress.setCount(self.tableCount)
        self.timer.start()
        self.elapsed.start()
        QtWidgets.QDialog.exec_(self)


class Loader(QtWidgets.QProgressDialog):
    texts = 'Loading, please wait...', 'Importing, please wait...'
    def __init__(self, parent):
        QtWidgets.QProgressDialog.__init__(self, parent)
        self.setWindowModality(QtCore.Qt.WindowModal)
        self.setMinimumDuration(0)
        self.setCancelButton(None)

    def finalize(self):
        self.setValue(self.maximum())

    def closeEvent(self, event):
        event.ignore()

    def keyPressEvent(self, event):
        pass

    def reject(self):
        pass

    def accept(self):
        QtWidgets.QProgressDialog.accept(self)

    def start(self, full=False, count=1):
        self.setLabelText(self.texts[full])
        self.setMaximum(count)
        self.setValue(0)
        self.show()
        QtWidgets.QApplication.processEvents()


class SetIndexDialog(QtWidgets.QDialog):
    def __init__(self, parent, start, current, end):
        from bigglesworth.wavetables.widgets import MiniSlider
        QtWidgets.QDialog.__init__(self, parent)
        self.setWindowTitle('Move wave within range')

        self.current = current

        l = QtWidgets.QGridLayout()
        self.setLayout(l)
        l.addWidget(QtWidgets.QLabel('Set new index ({}-{}):'.format(start, end)))

        self.indexSpin = QtWidgets.QSpinBox()
        l.addWidget(self.indexSpin, 0, 1)
        self.indexSpin.setRange(start, end)
        self.indexSpin.setValue(current)

        self.deltaLabel = QtWidgets.QLabel()
        l.addWidget(self.deltaLabel, 0, 2)
        self.deltaLabel.setFixedWidth(self.fontMetrics().width('+88'))
        self.indexSpin.valueChanged.connect(self.setDelta)

        self.miniSlider = MiniSlider()
        l.addWidget(self.miniSlider, 1, 1)
        self.miniSlider.setSibling(self.indexSpin)
        self.miniSlider.setMaximumHeight(8)
        self.miniSlider.setDefault(current)

        self.buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok|QtWidgets.QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        l.addWidget(self.buttonBox, l.rowCount(), 0, 1, l.columnCount())

    def setDelta(self, value):
        if value == self.current:
            self.deltaLabel.setText('')
        else:
            self.deltaLabel.setText('{:+}'.format(value - self.current))

    def exec_(self):
        if QtWidgets.QDialog.exec_(self):
            return self.indexSpin.value()


