from Qt import QtCore, QtGui, QtWidgets

from bigglesworth.widgets import Waiter
from bigglesworth.wavetables.utils import parseTime, getCurvePath


class CurveWidget(QtWidgets.QWidget):
    curveType = QtCore.QEasingCurve.Linear
    path = QtGui.QPainterPath()
    path.moveTo(0, 50)
    path.lineTo(50, 0)

    def __init__(self):
        QtWidgets.QWidget.__init__(self)
        self.setFixedSize(51, 51)

    def setCurve(self, curveType):
        if curveType != self.curveType:
            self.curveType = curveType
            self.path = getCurvePath(curveType)
            self.update()

    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        qp.setRenderHints(qp.Antialiasing)
        qp.setBrush(QtCore.Qt.white)
        qp.setPen(QtCore.Qt.NoPen)
        qp.drawRect(self.rect())
        qp.setPen(QtCore.Qt.black)
        qp.translate(.5, .5)
        qp.drawPath(self.path)


class CurveMorphDialog(QtWidgets.QDialog):
    curves = {
        QtCore.QEasingCurve.Linear: 'Linear', 
        QtCore.QEasingCurve.InQuad: 'Quadratic accelerating', 
        QtCore.QEasingCurve.OutQuad: 'Quadratic decelerating', 
        QtCore.QEasingCurve.InOutQuad: 'Quadratic accel/decel', 
        QtCore.QEasingCurve.OutInQuad: 'Quadratic decel/accel', 
        QtCore.QEasingCurve.InCubic: 'Cubic accelerating', 
        QtCore.QEasingCurve.OutCubic: 'Cubic decelerating', 
        QtCore.QEasingCurve.InOutCubic: 'Cubic accel/decel', 
        QtCore.QEasingCurve.OutInCubic: 'Cubic decel/accel', 
        QtCore.QEasingCurve.InQuart: 'Quartic accelerating', 
        QtCore.QEasingCurve.OutQuart: 'Quartic decelerating', 
        QtCore.QEasingCurve.InOutQuart: 'Quartic accel/decel', 
        QtCore.QEasingCurve.OutInQuart: 'Quartic decel/accel', 
        QtCore.QEasingCurve.InQuint: 'Quintic accelerating', 
        QtCore.QEasingCurve.OutQuint: 'Quintic decelerating', 
        QtCore.QEasingCurve.InOutQuint: 'Quintic accel/decel', 
        QtCore.QEasingCurve.OutInQuint: 'Quintic decel/accel', 
        QtCore.QEasingCurve.InSine: 'Sine accelerating', 
        QtCore.QEasingCurve.OutSine: 'Sine decelerating', 
        QtCore.QEasingCurve.InOutSine: 'Sine accel/decel', 
        QtCore.QEasingCurve.OutInSine: 'Sine decel/accel', 
        QtCore.QEasingCurve.InExpo: 'Exponential accelerating', 
        QtCore.QEasingCurve.OutExpo: 'Exponential decelerating', 
        QtCore.QEasingCurve.InOutExpo: 'Exponential accel/decel', 
        QtCore.QEasingCurve.OutInExpo: 'Exponential decel/accel', 
        QtCore.QEasingCurve.InCirc: 'Circular accelerating', 
        QtCore.QEasingCurve.OutCirc: 'Circular decelerating', 
        QtCore.QEasingCurve.InOutCirc: 'Circular accel/decel', 
        QtCore.QEasingCurve.OutInCirc: 'Circular decel/accel', 
        QtCore.QEasingCurve.OutInBack: 'Overshooting decel/accel', 
        QtCore.QEasingCurve.InBounce: 'Bounce accelerating', 
        QtCore.QEasingCurve.OutBounce: 'Bounce decelerating', 
        QtCore.QEasingCurve.InOutBounce: 'Bounce accel/decel', 
        QtCore.QEasingCurve.OutInBounce: 'Bounce decel/accel', 
    }

    reverseDict = {}

    def __init__(self, parent):
        from bigglesworth.wavetables.widgets import CurveIcon
        QtWidgets.QDialog.__init__(self, parent)
        layout = QtWidgets.QGridLayout()
        self.setLayout(layout)
        self.combo = QtWidgets.QComboBox()
        iconSize = self.combo.iconSize().height()
        for index, curve in enumerate(sorted(self.curves)):
            self.combo.addItem(CurveIcon(curve), self.curves[curve])
            pixmap = QtGui.QPixmap(iconSize, iconSize)
            pixmap.fill(QtCore.Qt.transparent)
            qp = QtGui.QPainter(pixmap)
            qp.setRenderHints(qp.Antialiasing)
            qp.setPen(QtCore.Qt.black)
            qp.drawPath(getCurvePath(curve, iconSize))
            qp.end()
#            self.combo.model().setData(self.combo.model().index(index, 0), pixmap, QtCore.Qt.DecorationRole)
#            self.combo.setItemData(index, pixmap, QtCore.Qt.DecorationRole)
#            self.combo.setItemIcon(index, CurveIcon())
            self.combo.setItemData(index, curve)
            self.reverseDict[curve] = index
        layout.addWidget(self.combo)
        self.curveWidget = CurveWidget()
        layout.addWidget(self.curveWidget)
        self.combo.currentIndexChanged.connect(self.updateCurve)

        self.buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok|QtWidgets.QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        layout.addWidget(self.buttonBox)

    def updateCurve(self, index):
        self.curveWidget.setCurve(self.combo.itemData(index))

    def exec_(self, transform):
        self.combo.setCurrentIndex(self.reverseDict[transform.data['curve']])
        res = QtWidgets.QDialog.exec_(self)
        if res:
            transform.setData({'curve': self.curveWidget.curveType})


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


class Loader(QtWidgets.QDialog):
    texts = 'Loading, please wait...', 'Importing, please wait...'
    def __init__(self, parent):
        QtWidgets.QDialog.__init__(self, parent)
        l = QtWidgets.QVBoxLayout()
        self.setLayout(l)
        self.label = QtWidgets.QLabel()
        l.addWidget(self.label)
        self.setModal(True)
        self.processTimer = QtCore.QTimer()
        self.processTimer.setInterval(0)
        self.processTimer.timeout.connect(QtWidgets.QApplication.processEvents)

    def refresh(self):
        QtWidgets.QApplication.processEvents()

    def closeEvent(self, event):
        event.ignore()

    def reject(self):
        pass

    def accept(self):
        self.processTimer.stop()
        QtWidgets.QDialog.accept(self)

    def start(self, full=False):
        self.label.setText(self.texts[full])
        self.show()
        QtWidgets.QApplication.processEvents()
        self.processTimer.start()


class SetIndexDialog(QtWidgets.QDialog):
    def __init__(self, parent, itemIndex, start, end):
        QtWidgets.QDialog.__init__(self, parent)
        l = QtWidgets.QGridLayout()
        self.setLayout(l)
        l.addWidget(QtWidgets.QLabel('Set new index:'))
        self.indexSpin = QtWidgets.QSpinBox()
        self.indexSpin.setRange(start, end)
        self.indexSpin.setValue(itemIndex)
        l.addWidget(self.indexSpin, 0, 1)
        self.buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok|QtWidgets.QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        l.addWidget(self.buttonBox, 1, 0, 1, 2)

    def exec_(self):
        if QtWidgets.QDialog.exec_(self):
            return self.indexSpin.value()


