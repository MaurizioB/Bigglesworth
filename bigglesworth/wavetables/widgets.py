# *-* encoding: utf-8 *-*
import sys
from uuid import uuid4

from Qt import QtCore, QtGui, QtWidgets

from bigglesworth.utils import sanitize, loadUi, getCardinal
from bigglesworth.dialogs.messageboxes import AdvancedMessageBox
from bigglesworth.widgets import DroppableTabBar
from bigglesworth.wavetables import UidColumn, NameColumn, SlotColumn, EditedColumn, DataColumn, PreviewColumn, DumpedColumn
from bigglesworth.wavetables.utils import ActivateDrag, curves, getCurvePath, waveFunction, waveColors, pow20, pow21, WaveLabels
from bigglesworth.wavetables.graphics import SampleItem, NextWaveScene, WaveTransformItem


FractRole = QtCore.Qt.UserRole + 1

CurveIconType, WaveIconType = 0, 1


class IconEngine(QtGui.QIconEngineV2):

    def __init__(self, iconType, icon):
        QtGui.QIconEngineV2.__init__(self)
        self.iconType = iconType
        self.icon = icon
        self.pixmapDict = {}
        self.paths = {}

    def pixmap(self, size, mode, state):
        try:
            return self.pixmapDict[(size, mode, state)]
        except:
            pixmap = QtGui.QPixmap(size)
            pixmap.fill(QtCore.Qt.transparent)
            self.pixmapDict[(size, mode, state)] = pixmap
            qp = QtGui.QPainter(pixmap)
            if mode == QtGui.QIcon.Disabled:
                qp.setPen(QtWidgets.QApplication.palette().color(QtGui.QPalette.Disabled, QtGui.QPalette.Text))
            qp.setRenderHints(qp.Antialiasing)
            size = min(size.width(), size.height())
            if self.iconType == CurveIconType:
                qp.drawPath(getCurvePath(self.icon, size))
            else:
                path = self.paths.get(size)
                if not path:
                    values = waveFunction[self.icon](1, size)
                    path = QtGui.QPainterPath()
                    half = size * .5
                    path.moveTo(0, half)
                    for x, y in enumerate(values):
                        path.lineTo(x, -y * half + half)
                    self.paths[size] = path
                qp.drawPath(path)
            qp.end()
            return pixmap

    def paint(self, qp, rect, mode, state):
        qp.save()
        qp.setRenderHints(qp.Antialiasing)
        size = min(rect.width(), rect.height())
        qp.translate(rect.topLeft())
        if self.iconType == CurveIconType:
            qp.drawPath(getCurvePath(self.icon, size))
        else:
            path = self.paths.get(size)
            if not path:
                values = waveFunction[self.icon](1, size)
                path = QtGui.QPainterPath()
                half = size * .5
                path.moveTo(0, half)
                for x, y in enumerate(values):
                    path.lineTo(x, -y * half + half)
                self.paths[size] = path
            qp.drawPath(path)
        qp.restore()


class CurveIcon(QtGui.QIcon):
    def __init__(self, curveType=QtCore.QEasingCurve.Linear):
        QtGui.QIcon.__init__(self, IconEngine(CurveIconType, curveType))


class WaveIcon(QtGui.QIcon):
    def __init__(self, waveType=0):
        QtGui.QIcon.__init__(self, IconEngine(WaveIconType, waveType))


class MiniButton(QtWidgets.QPushButton):
    def __init__(self, *args, **kwargs):
        QtWidgets.QPushButton.__init__(self, *args, **kwargs)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Maximum))
        self.setStyleSheet('''
            MiniButton {
                border: 1px solid darkGray;
                border-style: outset;
                border-radius: 2px;
            }
            MiniButton:pressed, MiniButton:checked {
                border-style: inset;
            }
        ''')


class MultiStateButton(QtWidgets.QPushButton):
    stateChanged = QtCore.pyqtSignal(int)
    idChanged = QtCore.pyqtSignal(int)

    def __init__(self, *args, **kwargs):
        QtWidgets.QPushButton.__init__(self, *args, **kwargs)
        self.states = []
        self.ids = {}
        self.setEnabled(False)
        self.currentState = -1
        self.blocked = set()
        self.clicked.connect(self.cycle)

    @property
    def currentId(self):
        try:
            return self.ids.keys()[self.ids.values().index(self.currentState)]
        except:
            return None

    @property
    def blockedStates(self):
        return [self.ids[i] for i in self.blocked]

    def blockId(self, id):
        self.blocked.add(id)
        if self.currentId == id:
            self.cycle()

    def unblockId(self, id):
        self.blocked.discard(id)
        if self.blocked == set(self.ids.keys()):
            self.setEnabled(False)

    def release(self):
        self.blocked.clear()
        self.setEnabled(True)

    def addState(self, text, icon=None, id=None):
        if isinstance(icon, str):
            icon = QtGui.QIcon.fromTheme(icon)
        elif icon is None:
            icon = QtGui.QIcon()
        self.states.append((text, icon))
        if id is not None:
            self.ids[id] = len(self.states) - 1
        if len(self.states) == 1:
            self.setEnabled(True)
            self.setState(0)

    def addStates(self, states):
        for state in states:
            self.addState(*state)

    def cycle(self):
        nextState = self.currentState + 1
        if nextState >= len(self.states):
            nextState = 0
        while nextState in self.blockedStates:
            nextState += 1
            if nextState >= len(self.states):
                nextState = 0
        self.setState(nextState)

    def setId(self, id):
        if id == self.currentId:
            return
        state = self.ids.get(id, 0)
        self.setState(state)

    def setState(self, state):
        if state in self.blockedStates:
            return
        self.currentState = state
        text, icon = self.states[state]
        self.setText(text)
        self.setIcon(icon)
        self.stateChanged.emit(state)
        self.idChanged.emit(self.ids.keys()[self.ids.values().index(state)])


class MiniSlider(QtWidgets.QWidget):
    valueChanged = QtCore.pyqtSignal(int)
    value = 0
    arrowWidth = 8
    default = None
    minimum = maximum = 0

    def setSibling(self, spin):
        self.spin = spin
        self.setRange(spin.minimum(), spin.maximum())
        spin.valueChanged.connect(self.setValue)
        self.value = spin.value()
        self.valueChanged.connect(spin.setValue)
        spin.setRange = lambda *args: [self.setRange(*args), QtWidgets.QSpinBox.setRange(spin, *args)]

    def setRange(self, minimum, maximum):
        if self.minimum == minimum and self.maximum == maximum:
            return
        self.minimum = minimum
        self.maximum = maximum
        self.update()

    def setDefault(self, default=None):
        self.default = default
        self.update()

    def setValue(self, value):
        if value == self.value:
            return
        self.value = sanitize(self.minimum, value, self.maximum)
        self.valueChanged.emit(value)
        self.update()

    def minimumSizeHint(self):
        hint = QtWidgets.QWidget.minimumSizeHint(self)
        hint.setHeight(8)
        return hint

    def sizeHint(self):
        hint = QtWidgets.QWidget.sizeHint(self)
        hint.setHeight(16)
        return hint

    def setValueFromPos(self, pos, checkDefault=False):
        v = (pos.x() - float(self.arrowWidth)) / (self.width() - self.arrowWidth * 2)
        value = sanitize(self.minimum, int(self.minimum + v * (self.maximum - self.minimum)), self.maximum)
        if self.default is not None and checkDefault:
            if value - 2 <= self.default <= value + 2:
                value = self.default
        self.setValue(value)

    def wheelEvent(self, event):
        if event.delta() > 0:
            self.setValue(self.value + 1)
        else:
            self.setValue(self.value - 1)

    def mousePressEvent(self, event):
        if event.buttons() == QtCore.Qt.LeftButton:
            self.setValueFromPos(event.pos(), True)

    def mouseMoveEvent(self, event):
        if event.buttons() == QtCore.Qt.LeftButton:
            self.setValueFromPos(event.pos())

    def resizeEvent(self, event):
        self.arrow = QtGui.QPainterPath()
        self.arrowWidth = self.height()
        self.arrow.lineTo(-self.arrowWidth + 1, self.arrowWidth - 2)
        self.arrow.lineTo(self.arrowWidth - 1, self.arrowWidth - 2)
        self.arrow.closeSubpath()

    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        qp.setRenderHints(qp.Antialiasing)
        width = self.width() - self.arrowWidth * 2
        qp.translate(.5, .5)
        color = self.palette().color(QtGui.QPalette.ButtonText)
        qp.setPen(color.adjusted(a=128))
        left = self.arrowWidth + 1
        qp.drawLine(left, 0, left, self.arrowWidth / 2)
        qp.drawLine(left, 0, left + width, 0)
        qp.drawLine(left + width, 0, left + width, self.arrowWidth / 2)
        if self.default is not None:
            qp.setPen(QtGui.QPen(color, 2))
            defaultPos = int(self.arrowWidth + (float(self.default - self.minimum) / (self.maximum - self.minimum)) * width)
            qp.drawLine(defaultPos, 0, defaultPos, self.arrowWidth / 2)

        arrowPos = int(self.arrowWidth + (float(self.value - self.minimum) / (self.maximum - self.minimum)) * width)
        qp.translate(arrowPos, 0)
        qp.setPen(QtCore.Qt.NoPen)
        qp.setBrush(color)
        qp.drawPath(self.arrow)


class ClipSlopeSlider(QtWidgets.QSlider):
    slopeChanged = QtCore.pyqtSignal(float)
    def __init__(self, *args, **kwargs):
        QtWidgets.QSlider.__init__(self, *args, **kwargs)
        self.previous = 0
        self.valueChanged.connect(self.setValue)
        self._zeroRange = 50
        self.slope = None

    @QtCore.pyqtProperty(int)
    def zeroRange(self):
        return self._zeroRange

    @zeroRange.setter
    def zeroRange(self, zeroRange):
        self._zeroRange = zeroRange

    def mousePressEvent(self, event):
        if event.buttons() == QtCore.Qt.LeftButton:
            self.computePos(event.pos())
        else:
            QtWidgets.QSlider.mousePressEvent(self, event)

    def mouseMoveEvent(self, event):
        self.computePos(event.pos())

    def computePos(self, pos):
        option = QtWidgets.QStyleOptionSlider()
        self.initStyleOption(option)
        handleRect = self.style().subControlRect(QtWidgets.QStyle.CC_Slider, option, QtWidgets.QStyle.SC_SliderHandle, self)
        left = handleRect.width() / 2
        value = self.style().sliderValueFromPosition(self.minimum(), self.maximum(), pos.x() - left, self.width() - handleRect.width())
        if not value or value <= -self.zeroRange or value >= self.zeroRange:
            return self.setValue(value)
        if value < -self.zeroRange / 2:
            value = -self.zeroRange
        elif -self.zeroRange / 2 <= value <= self.zeroRange / 2:
            value = 0
        else:
            value = self.zeroRange
        self.setValue(value)

    def flip(self):
        self.setValue(-self.value())

    def setValue(self, value):
        if not value or value <= -self.zeroRange or value >= self.zeroRange:
            pass
        elif value < 0:
            if self.previous >= 0:
                value = -self.zeroRange
            else:
                value = 0
        else:
            if self.previous <= 0:
                value = self.zeroRange
            else:
                value = 0
        self.previous = value
        QtWidgets.QSlider.setValue(self, value)
        if value:
            self.slope = float(abs(value) - self.zeroRange + 1) / ((self.maximum() - self.minimum()) / 2 + 1 - self.zeroRange)
            self.slope *= 1 if value > 0 else -1
        else:
            self.slope = 0
        self.slopeChanged.emit(self.slope)


class ClipSlopeIcon(QtWidgets.QLabel):
    clicked = QtCore.pyqtSignal()

    def mousePressEvent(self, event):
        if event.buttons() == QtCore.Qt.LeftButton:
            self.clicked.emit()

    def setSibling(self, slider):
        self.slider = slider

    def wheelEvent(self, event):
        event = QtGui.QWheelEvent(event.pos(), -event.delta(), event.buttons(), event.modifiers(), QtCore.Qt.Horizontal)
        QtWidgets.QApplication.sendEvent(self.slider, event)


class ExpandingView(QtWidgets.QListView):
    def showEvent(self, event):
        QtWidgets.QListView.showEvent(self, event)
        self.setMinimumWidth(self.sizeHintForColumn(0) + self.parent().parent().iconSize().width())


class CurveTransformCombo(QtWidgets.QComboBox):
    def __init__(self, *args, **kwargs):
        QtWidgets.QComboBox.__init__(self, *args, **kwargs)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Maximum))
        self.curveDict = {}
        for index, curve in enumerate(sorted(curves)):
            self.addItem(CurveIcon(curve), curves[curve])
            self.setItemData(index, curve)
            self.curveDict[curve] = index
        self.setView(ExpandingView())
#        self.view().setMinimumWidth(self.view().sizeHintForColumn(0) + self.iconSize().width())
        self.currentIndexChanged.connect(lambda i: self.setToolTip(self.itemText(i)))

    def setCurrentCurve(self, curve):
        self.setCurrentIndex(self.curveDict[curve])


class WaveSelectionCombo(QtWidgets.QComboBox):
    def __init__(self, *args, **kwargs):
        QtWidgets.QComboBox.__init__(self, *args, **kwargs)
        for wave, label in enumerate(WaveLabels):
            self.addItem(WaveIcon(wave), label)


class PositiveSpin(QtWidgets.QSpinBox):
    def textFromValue(self, value):
        if value <= 0:
            return str(value)
        return '+{}'.format(value)


class TransformWidget(QtWidgets.QWidget):
    changeTransformModeRequested = QtCore.pyqtSignal(int)
    specTransformRequest = QtCore.pyqtSignal()
    changeTransformCurveRequested = QtCore.pyqtSignal(int)
    changeTransformTranslRequested = QtCore.pyqtSignal(int)
    appliesToNextToggled = QtCore.pyqtSignal(bool)

    def __init__(self, *args, **kwargs):
        QtWidgets.QWidget.__init__(self, *args, **kwargs)
        loadUi('ui/wavetablemorphwidget.ui', self)
        self.nextWaveLbl.setFixedWidth(self.fontMetrics().width('8888'))
        for mode in sorted(WaveTransformItem.modeNames.keys()):
            name = WaveTransformItem.modeNames[mode]
            icon = QtGui.QIcon.fromTheme(WaveTransformItem.modeIcons[mode])
            self.nextTransformCombo.addItem(icon, name)
        self.nextTransformCombo.currentIndexChanged.connect(self.setCurrentTransformMode)
        self.curveTransformCombo.currentIndexChanged.connect(self.setCurrentTransformCurve)
        self.translOffsetSpin.valueChanged.connect(self.changeTransformTranslRequested)
        self.currentTransform = None
        self.currentIndex = None
        self.specTransformEditBtn.clicked.connect(self.specTransformRequest)
        self.appliesToNextChk.toggled.connect(self.appliesToNextToggled)
        self.appliesToNextChk.toggled.connect(self.setApplyToNext)
        self.appliesToNextChk2.toggled.connect(self.appliesToNextChk.setChecked)

    def setCurrentTransformMode(self, mode):
        self.nextTransformCycler.setCurrentIndex(mode)
        self.changeTransformModeRequested.emit(mode)
#        self.currentTransform.setMode(mode)

    def setCurrentTransformCurve(self, index):
#        self.currentTransform.setData({'curve': self.curveTransformCombo.itemData(index)})
        self.changeTransformCurveRequested.emit(self.curveTransformCombo.itemData(index))

    def reload(self):
        try:
            self.setTransform(self.keyFrames[self.currentIndex])
        except:
            self.setTransform(self.keyFrames[0])

    def setTransform(self, keyFrame):
#        if keyFrame.nextTransform == self.currentTransform:
#            return
        self.currentIndex = keyFrame.index
        if self.currentTransform:
            self.currentTransform.changed.disconnect(self.updateTransform)
        self.currentTransform = keyFrame.nextTransform
        if self.currentTransform:
            self.currentTransform.changed.connect(self.updateTransform)
            self.setApplyToNext()
        self.updateTransform()

    def updateTransform(self):
#        if len(self.keyFrames) > 1 and self.currentTransform and self.currentTransform.isValid() and not self.currentTransform.isContiguous():
        if self.currentTransform and self.currentTransform.isValid() and not self.currentTransform.isContiguous():
            self.nextTransformCombo.setEnabled(True)
            self.nextTransformCombo.blockSignals(True)
            self.nextTransformCombo.setCurrentIndex(self.currentTransform.mode)
            self.nextTransformCombo.blockSignals(False)
            self.nextTransformCycler.setEnabled(True)
            self.nextTransformCycler.setCurrentIndex(self.currentTransform.mode)
            if self.currentTransform.mode == WaveTransformItem.CurveMorph:
                self.curveTransformCombo.blockSignals(True)
                self.curveTransformCombo.setCurrentCurve(self.currentTransform.curve)
                self.curveTransformCombo.blockSignals(False)
            elif self.currentTransform.mode == WaveTransformItem.TransMorph:
                self.translOffsetSpin.blockSignals(True)
                self.translOffsetSpin.setValue(self.currentTransform.translate)
                self.translOffsetSpin.blockSignals(False)
            self.setApplyToNext()
        else:
            self.nextTransformCombo.setEnabled(False)
            self.nextTransformCycler.setEnabled(False)
            self.nextTransformCombo.blockSignals(True)
            self.nextTransformCombo.setCurrentIndex(-1)
            self.nextTransformCombo.blockSignals(False)
        try:
            self.nextWaveLbl.setNum(self.currentTransform.nextItem.index + 1)
        except:
            pass

    def setApplyToNext(self, state=None):
        if state is None:
            state = self.currentTransform.appliesToNext
        if self.sender() != self.appliesToNextChk:
            self.appliesToNextChk.blockSignals(True)
            self.appliesToNextChk.setChecked(state)
            self.appliesToNextChk.blockSignals(False)
        if self.sender() != self.appliesToNextChk2:
            self.appliesToNextChk2.blockSignals(True)
            self.appliesToNextChk2.setChecked(state)
            self.appliesToNextChk2.blockSignals(False)


class NextWaveView(QtWidgets.QGraphicsView):
    shown = False
    doubleClicked = QtCore.pyqtSignal()

    def __init__(self, *args, **kwargs):
        QtWidgets.QGraphicsView.__init__(self, *args, **kwargs)
        self.setScene(NextWaveScene())

    def mouseDoubleClickEvent(self, event):
        self.doubleClicked.emit()

    def showEvent(self, event):
        if not self.shown:
            self.shown = True
            self.fitInView(self.sceneRect())

    def setWave(self, waveItem):
        self.scene().setWave(waveItem)
        self.fitInView(self.sceneRect())

    def sizeHint(self):
        return self.minimumSizeHint()


class PianoStatusWidget(QtWidgets.QFrame):
    stateChanged = QtCore.pyqtSignal(bool)

    def __init__(self):
        QtWidgets.QFrame.__init__(self)
        self.setFrameStyle(self.StyledPanel|self.Sunken)
        self.icon = QtGui.QIcon.fromTheme('pianoicon')
        self.state = True
        self.setToolTip('Enable/Disable input keyboard events')

    def minimumSizeHint(self):
        size = QtWidgets.QApplication.fontMetrics().height() * 2
        return QtCore.QSize(size, size)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.setState(not self.state)

    def setState(self, state):
        if state == self.state:
            return
        self.state = state
        self.setFrameStyle(self.StyledPanel|(self.Sunken if state else self.Raised))
        self.stateChanged.emit(state)

    def paintEvent(self, event):
        QtWidgets.QFrame.paintEvent(self, event)
        qp = QtGui.QPainter(self)
        l, t, r, b = self.getContentsMargins()
        rect = self.rect().adjusted(l + 2, t + 2, -r - 2, -b - 2)
        qp.drawPixmap(rect, self.icon.pixmap(rect.height(), mode=not (self.state and self.isEnabled())))


class IconWidget(QtWidgets.QWidget):
    _sizeHint = QtCore.QSize(1, 1)
    def __init__(self, *args, **kwargs):
        QtWidgets.QWidget.__init__(self, *args, **kwargs)

    def sizeHint(self):
        return self._sizeHint

    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        qp.setRenderHints(qp.Antialiasing)
        qp.drawPixmap(1, 0, self.icon.pixmap(self.iconSize, QtGui.QIcon.Normal if self.isEnabled() else QtGui.QIcon.Disabled))

    def resizeEvent(self, event):
        size = self.size().width() - 2
        self.iconSize = QtCore.QSize(size, size)


class ZoomIconWidget(IconWidget):
    def __init__(self, *args, **kwargs):
        IconWidget.__init__(self, *args, **kwargs)
        self.icon = QtGui.QIcon.fromTheme('edit-find')
        self.iconSize = self._sizeHint


class PositionWidgetIcon(IconWidget):
    entered = QtCore.pyqtSignal()
    def __init__(self, *args, **kwargs):
        IconWidget.__init__(self, *args, **kwargs)
        self.icon = QtGui.QIcon.fromTheme('transform-move-horizontal')
        self.iconSize = self._sizeHint

    def enterEvent(self, event):
        self.entered.emit()


class AddMultiEnvWidget(QtWidgets.QWidget):
    def __init__(self, parentBtn):
        QtWidgets.QWidget.__init__(self)
        layout = QtWidgets.QVBoxLayout()
        self.parentBtn = parentBtn
        self.setLayout(layout)
        layout.setSpacing(2)
        self.setContentsMargins(1, 1, 1, 1)
        self.countSpin = QtWidgets.QSpinBox()
        self.countSpin.setRange(1, 32)
        layout.addWidget(self.countSpin)
        self.parityCombo = QtWidgets.QComboBox()
        layout.addWidget(self.parityCombo)
        self.parityCombo.addItem('Incrementally')
        self.parityCombo.addItem('Odd harmonics')
        self.parityCombo.addItem('Even harmonics')
        for wave, label in enumerate(WaveLabels):
            waveBtn = QtWidgets.QPushButton(WaveIcon(wave), label)
            layout.addWidget(waveBtn)
            waveBtn.clicked.connect(lambda _, wave=wave: self.emitRequest(wave))
#            waveBtn.clicked.connect(lambda _, wave=wave: parentBtn.addRequested.emit(
#                self.countSpin.value(), wave))

    def emitRequest(self, wave):
        parity = self.parityCombo.currentIndex()
        if not parity:
            self.parentBtn.addRequested.emit([None for _ in range(self.countSpin.value())], wave)
            return
        elif parity == 1:
            items = range(3, self.countSpin.value() * 2 + 3, 2)
        else:
            items = range(2, self.countSpin.value() * 2 + 2, 2)
        self.parentBtn.addRequested.emit(items, wave)

#        self.addBtn.clicked.connect(lambda: button.addRequested.emit(self.countSpin.value(), self.waveCombo.currentIndex()))

    def showEvent(self, event):
        self.countSpin.setValue(1)
        self.parityCombo.setCurrentIndex(0)


class AddToolButton(QtWidgets.QToolButton):
    addRequested = QtCore.pyqtSignal(object, int)
    def __init__(self, *args, **kwargs):
        QtWidgets.QToolButton.__init__(self, *args, **kwargs)
        menu = QtWidgets.QMenu()
        actionWidget = QtWidgets.QWidgetAction(menu)
        actionWidget.setDefaultWidget(AddMultiEnvWidget(self))
        menu.addAction(actionWidget)
        self.setMenu(menu)
        self.clicked.connect(lambda: self.addRequested.emit((None, ), 0))
        self.addRequested.connect(menu.close)



class GraphicsSlider(QtWidgets.QWidget):
    sliderRect = QtCore.QRect(0, 0, 24, 80)
    baseSize = sliderRect.size()

    sineGradColors = QtGui.QColor(0, 128, 192, 64), QtGui.QColor(0, 128, 192, 192)
    squareGradColors = QtGui.QColor(225, 255, 99, 64), QtGui.QColor(225, 255, 99, 192)
    triangleGradColors = QtGui.QColor(89, 206, 138, 64), QtGui.QColor(89, 206, 138, 192)
    sawGradColors = QtGui.QColor(180, 160, 60, 64), QtGui.QColor(180, 160, 60, 192)
    invSawGradColors = QtGui.QColor(159, 42, 107, 64), QtGui.QColor(159, 42, 107, 192)
    gradColors = sineGradColors, squareGradColors, triangleGradColors, sawGradColors, invSawGradColors

    initialized = False
    sliderEnabled = True
    value = 0
    fract = None

    names = [
        'Fundamental', 
        '1st octave', 
        '5th above 1st octave', 
        '2nd octave', 
        '3rd above 2nd octave', 
        '5th above 2nd octave', 
        '~7th above 2nd octave', 
        '4th octave', 
        '2nd above 4th octave', 
        'maj 3rd above 4th octave', 
        '~4th above 4th octave', 
        '5th above 4th octave', 
        '~min 6th above 4th octave', 
        '~min 7th above 4th octave', 
        'maj 7th above 4th octave', 
        '5th octave'
    ]

    valueChanged = QtCore.pyqtSignal([int, float], [float, float])
    polarityChanged = QtCore.pyqtSignal(int)
    drag = QtCore.pyqtSignal(float)
    triggered = QtCore.pyqtSignal()

    def __init__(self, fract):
        QtWidgets.QWidget.__init__(self)
        if not self.__class__.initialized:
            self.initColors()

        self.setMouseTracking(True)
        self.setFixedSize(self.baseSize)
        self.setFract(fract)

    def initColors(self):
        cls = self.__class__
        cls.initialized = True
        cls.colors = []
        for f, (color, (gradColor0, gradColor1)) in enumerate(zip(waveColors, cls.gradColors)):
            borderPenEnabled = QtGui.QPen(color)
            borderPenDisabled = QtGui.QPen(color.adjusted(a=128))
            valuePenEnabled = QtGui.QPen(color, 2)
            valuePenDisabled = QtGui.QPen(color.adjusted(a=128), 2)
            brushEnabled = QtGui.QLinearGradient(0, 0, 0, 1)
            brushEnabled.setCoordinateMode(brushEnabled.ObjectBoundingMode)
#            gradColor0, gradColor1 = gradColors
            brushEnabled.setColorAt(0, gradColor0)
            brushEnabled.setColorAt(1, gradColor1)
            brushDisabled = QtGui.QLinearGradient(0, 0, 0, 1)
            brushDisabled.setCoordinateMode(brushDisabled.ObjectBoundingMode)
            brushDisabled.setColorAt(0, gradColor0.adjusted(a=gradColor0.alphaF() * .5))
            brushDisabled.setColorAt(1, gradColor1.adjusted(a=gradColor1.alphaF() * .5))
            cls.colors.append(((borderPenDisabled, borderPenEnabled), (valuePenDisabled, valuePenEnabled), (brushDisabled, brushEnabled)))
#        (cls.borderPenEnabled, cls.borderPenDisabled), (cls.valuePenEnabled, cls.valuePenDisabled), (cls.brushEnabled, cls.brushDisabled) = cls.colors[0]
        cls.borderPens, cls.valuePens, cls.brushes = cls.colors[0]
        cls.borderPen = cls.borderPens[1]
        cls.valuePen = cls.valuePens[1]
        cls.brush = cls.brushes[1]

    def setFract(self, fract):
        if fract == self.fract:
            return
        self.fract = fract
        waveForm = abs(fract) >> 7
        self.borderPens, self.valuePens, self.brushes = self.colors[waveForm]
        self.borderPen = self.borderPens[self.sliderEnabled]
        self.valuePen = self.valuePens[self.sliderEnabled]
        self.brush = self.brushes[self.sliderEnabled]
        self.update()

    def setSliderEnabled(self, enabled):
        self.sliderEnabled = enabled
        self.borderPen = self.borderPens[self.sliderEnabled]
        self.valuePen = self.valuePens[self.sliderEnabled]
        self.brush = self.brushes[self.sliderEnabled]
        self.update()

    def getValueFromY(self, y):
        y = sanitize(0, y - self.sliderRect.top(), self.sliderRect.bottom())
        return (1 - float(y) / (self.sliderRect.height() - 1))

    def mousePressEvent(self, event):
        if event.buttons() == QtCore.Qt.LeftButton:
            if not self.sliderEnabled:
                return event.accept()
            self.setValue(self.getValueFromY(event.pos().y()))
        elif event.buttons() == QtCore.Qt.MiddleButton and self.sliderEnabled:
            self.setValue(1. / (abs(self.fract) & 127))
        self.drag.emit(self.value)
        event.ignore()

    def setValue(self, value, emit=True):
        if value == self.value:
            return
        oldValue = self.value
        self.value = sanitize(0, value, 1)
        if emit:
            self.valueChanged.emit(self.fract, self.value)
            self.valueChanged[float, float].emit(self.value, oldValue)
        self.update()

    def mouseMoveEvent(self, event, ignore=False, override=.5):
        if event.buttons() == QtCore.Qt.LeftButton and (ignore or event.pos() in self.rect()) and not event.modifiers():
            if not self.sliderEnabled:
                return event.accept()
            self.setValue(self.getValueFromY(event.pos().y()))
        elif (event.buttons() == QtCore.Qt.MiddleButton or 
            (event.buttons() == QtCore.Qt.LeftButton and event.modifiers() == QtCore.Qt.ShiftModifier)) and \
            (ignore or event.pos() in self.rect()):
                self.setValue(override if event.modifiers() == QtCore.Qt.ShiftModifier else .5)
        if event.pos() not in self.rect():
            event.ignore()

    def mouseReleaseEvent(self, event):
        self.drag.emit(-1)
        QtWidgets.QWidget.mouseReleaseEvent(self, event)

    def changeEvent(self, event):
        if event.type() == QtCore.QEvent.EnabledChange:
            self.setSliderEnabled(self.isEnabled())

    def wheelEvent(self, event):
        if self.sliderEnabled:
            multi = .2 if event.modifiers() == QtCore.Qt.ShiftModifier else 1
            self.setValue(self.value + (.05 if event.delta() > 0 else -.05) * multi)

    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        qp.translate(.5, .5)
        qp.setRenderHints(qp.Antialiasing)

        qp.setPen(QtCore.Qt.NoPen)
        qp.setBrush(QtCore.Qt.black)
        rect = self.rect().adjusted(0, 0, -1, -1)
        qp.drawRect(rect)

        qp.save()
        qp.setPen(QtCore.Qt.NoPen)
        qp.setBrush(self.brush)
        valueRect = rect.adjusted(0, rect.height() * (1 - self.value) + 1, 0, 0)
        qp.drawRect(valueRect)
        qp.setPen(self.valuePen)
        qp.drawLine(valueRect.left(), valueRect.top() - 1, valueRect.right(), valueRect.top() - 1)
        qp.restore()

        qp.setPen(self.borderPen)
        qp.setBrush(QtCore.Qt.NoBrush)
        qp.drawRect(rect)
        y = rect.height() - float(rect.height()) / (abs(self.fract) & 127)
        qp.drawLine(1, y, self.width() - 2, y)


class Selector(QtWidgets.QPushButton):

    def __init__(self, selectable=False):
        QtWidgets.QPushButton.__init__(self, QtGui.QIcon.fromTheme('document-edit' if selectable else 'edit-select-all'), '')
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum))
        self.setMaximumHeight(16)
        self.setCheckable(True)
        self.setStyleSheet('''
            Selector {
                background: darkGray;
                border: 1px solid palette(dark);
                border-style: outset;
                border-radius: 1px;
            }
            Selector:on {
                background: rgb(50, 255, 50);
                border-style: inset;
            }
        ''')

    def mousePressEvent(self, event):
        self.click()


class EnvelopeSelector(Selector):
    def __init__(self, main):
        Selector.__init__(self, True)
        self.setAttribute(QtCore.Qt.WA_LayoutUsesWidgetRect, True)
        self.main = main
        self.menu = QtWidgets.QMenu()
        self.copyAction = self.menu.addAction(QtGui.QIcon.fromTheme('edit-copy'), 'Copy envelope')
        self.pasteAction = self.menu.addAction(QtGui.QIcon.fromTheme('edit-paste'), 'Paste envelope')
        self.menu.addSeparator()
        self.removeAction = self.menu.addAction(QtGui.QIcon.fromTheme('edit-delete'), 'Remove')


    def _contextMenuEvent(self, event):
        self.click()
        self.pasteAction.setEnabled(QtWidgets.QApplication.clipboard().mimeData().hasFormat('bigglesworth/EnvelopeData'))
        if len(self.main.envelopes) == 1:
            self.removeAction.setEnabled(False)
        self.menu.exec_(QtGui.QCursor.pos())


class WaveWidget(QtWidgets.QWidget):
    fract = None
    polarityChanged = QtCore.pyqtSignal(int)
    shown = False

    def __init__(self, fract):
        QtWidgets.QWidget.__init__(self)
        self.setAttribute(QtCore.Qt.WA_LayoutUsesWidgetRect, True)
        self.setFract(fract)
        self.setFixedHeight(self.fontMetrics().height() * 1.5 - 4)
        self.rebuildPaths()

    def setFract(self, fract):
        if fract == self.fract:
            return
        self.fract = fract
        self.rebuildPaths()
        self.update()

    def rebuildPaths(self):
        self.positivePath = QtGui.QPainterPath()
        self.negativePath = QtGui.QPainterPath()
        if not self.isVisible():
            return
        y = (self.height() - 5) / 2
        count = self.width() - 4
        values = waveFunction[abs(self.fract) >> 7](1, count)
        self.positivePath.moveTo(0, -values[0] * y)
        self.negativePath.moveTo(0, values[0] * y)
        for x, v in zip(range(count), values):
            self.positivePath.lineTo(x, -v * y)
            self.negativePath.lineTo(x, v * y)
        self.negativePath.translate(2.5, y + 1)
        self.positivePath.translate(2.5, y + 1)

    def mousePressEvent(self, event):
        if event.buttons() == QtCore.Qt.MiddleButton:
            self.setFract(self.fract * -1)
            self.polarityChanged.emit(self.fract)
        elif event.buttons() == QtCore.Qt.LeftButton:
            self.parent().showWaveMenu()

    def resizeEvent(self, event):
        self.rebuildPaths()

    def showEvent(self, event):
        if not self.shown:
            self.shown = True
            self.rebuildPaths()

    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        qp.setRenderHints(qp.Antialiasing)
        qp.translate(.5, .5)
        if self.fract > 0:
            qp.setPen(QtCore.Qt.white)
            qp.drawPath(self.positivePath)
        else:
            qp.setBrush(QtCore.Qt.black)
            qp.setPen(QtCore.Qt.NoPen)
            qp.drawRect(self.rect())
            qp.setPen(QtCore.Qt.white)
            qp.drawPath(self.negativePath)


class FakeCombo(QtWidgets.QComboBox):
    def __init__(self, sourceModel, fract):
        QtWidgets.QComboBox.__init__(self)
        self.setAttribute(QtCore.Qt.WA_LayoutUsesWidgetRect, True)
        model = FractProxy()
        model.setSourceModel(sourceModel)
        self.wave = abs(fract) >> 7
        model.wave = self.wave
        self.setModel(model)

    def fractData(self, index):
        return self.model().data(self.model().index(index, self.wave), FractRole)

    def setFract(self, fract):
        self.wave = abs(fract) >> 7
        self.model().wave = self.wave
        self.model().invalidateFilter()

    def paintEvent(self, event):
        pass


class FractProxy(QtCore.QSortFilterProxyModel):
    wave = 0

    def flags(self, index):
        if index.sibling(index.row(), self.wave).data(FractRole):
            return QtCore.Qt.ItemIsSelectable|QtCore.Qt.ItemIsEnabled
        return QtCore.Qt.ItemIsSelectable


class EnvelopeHarmonicsSlider(QtWidgets.QWidget):
    triggered = QtCore.pyqtSignal()
    fractChanged = QtCore.pyqtSignal(int)
    polarityChanged = QtCore.pyqtSignal(int)
    valueChanged = QtCore.pyqtSignal(float, float)
    removeRequested = QtCore.pyqtSignal()
    copyRequested = QtCore.pyqtSignal()
    pasteRequested = QtCore.pyqtSignal()

    names = [
        'Fundamental', 
        '1st octave', 
        '5th above 1st octave', 
        '2nd octave', 
        '3rd above 2nd octave', 
        '5th above 2nd octave', 
        '~7th above 2nd octave', 
        '4th octave', 
        '2nd above 4th octave', 
        'maj 3rd above 4th octave', 
        '~4th above 4th octave', 
        '5th above 4th octave', 
        '~min 6th above 4th octave', 
        '~min 7th above 4th octave', 
        'maj 7th above 4th octave', 
        '5th octave'
    ]

    def __init__(self, fract, model):
        QtWidgets.QWidget.__init__(self)
        self.setAttribute(QtCore.Qt.WA_LayoutUsesWidgetRect, True)
        layout = QtWidgets.QVBoxLayout()
        layout.setSpacing(2)
        self.setLayout(layout)
        layout.setContentsMargins(1, 2, 1, 2)

        self.arrowPath = QtGui.QPainterPath()
        size = self.fontMetrics().height() * .2
        self.arrowPath.moveTo(-size, -size)
        self.arrowPath.lineTo(size, -size)
        self.arrowPath.lineTo(0, size)
        self.arrowPath.closeSubpath()
        self.arrowWidth = self.arrowPath.boundingRect().width() + 2

        self.selector = EnvelopeSelector(self)
        layout.addWidget(self.selector)

        self.baseModel = model
        self.fakeCombo = FakeCombo(model, fract)
        layout.addWidget(self.fakeCombo)
        self.fakeCombo.view().setMinimumWidth(self.fakeCombo.view().sizeHintForColumn(0))
        self.fakeCombo.view().setResizeMode(QtWidgets.QListView.Adjust)
        self.fakeCombo.setFixedSize(24, self.fontMetrics().height())
        self.fakeCombo.setCurrentIndex((abs(fract) & 127) - 1)
        self.fakeCombo.currentIndexChanged.connect(self.setFractFromCombo)

        self.waveWidget = WaveWidget(fract)
        self.waveWidget.polarityChanged.connect(self.setFract)
        layout.addWidget(self.waveWidget)

        self.slider = GraphicsSlider(fract)
        layout.addWidget(self.slider)
        self.slider.valueChanged[float, float].connect(self.sliderValueChanged)
        self.setSliderEnabled = self.slider.setSliderEnabled

        self.menu = QtWidgets.QMenu()
        switchAction = self.menu.addAction(QtGui.QIcon.fromTheme('reverse'), 'Switch polarity')
        switchAction.triggered.connect(self.switchPolarity)
        self.menuActionGroup = QtWidgets.QActionGroup(self.menu)
        for wave, label in enumerate(WaveLabels):
            action = self.menu.addAction(WaveIcon(wave), label)
            action.setData(wave)
            action.setCheckable(True)
            self.menuActionGroup.addAction(action)

    @property
    def fract(self):
        return self.slider.fract

    @fract.setter
    def fract(self, fract):
        self.slider.setFract(fract)
        self.waveWidget.setFract(fract)
        self.fakeCombo.setFract(fract)
        self.setStatusTip()

    def setFract(self, fract):
        self.fract = fract
        self.fractChanged.emit(fract)

    def setValue(self, *args):
        self.slider.setValue(*args)
#        self.waveWidget.setValue(args[0])
        self.setStatusTip()

    def switchPolarity(self):
        self.setFract(self.fract * -1)

    def setFractFromCombo(self, index):
        wave = abs(self.fract) >> 7
        available = self.fakeCombo.fractData(index)
        if not available:
            print('errore fract disponibili?!')
            return
        newIndex = index + 1
        if abs(self.fract) & 127 == newIndex:
            return
        if self.fract > 0:
            if not available & 1:
                newIndex *= -1
        else:
            if not available & 2:
                newIndex *= -1
        if wave:
            if newIndex < 0:
                newIndex = -(abs(newIndex) + (wave << 7))
            else:
                newIndex += wave << 7
        self.setFract(newIndex)
        self.setStatusTip()
#        QtWidgets.QApplication.sendEvent(self.window(), QtGui.QStatusTipEvent(self.slider.statusTip()))

    def sliderValueChanged(self, value, oldValue):
#        self.waveWidget.setValue(value)
        self.valueChanged.emit(value, oldValue)
        self.setStatusTip()

    def setStatusTip(self):
        realFract = (abs(self.fract) & 127)
#        cardinal = getCardinal(realFract + 1)
        if realFract <= len(self.names):
            label = self.names[realFract - 1]
        else:
            label = '{} harmonic'.format(getCardinal(realFract))
        statusText = '{} ({:.02f}%)'.format(label, self.slider.value * 100)
        QtWidgets.QWidget.setStatusTip(self, statusText)
        if isinstance(self.sender(), TransformWidget) and not self.selector.isChecked():
            return
        QtWidgets.QApplication.sendEvent(self.window(), QtGui.QStatusTipEvent(self.statusTip()))
 
    def contextMenuEvent(self, event):
        event.accept()
        if event.pos() in self.waveWidget.geometry():
            self.showWaveMenu()

    def showWaveMenu(self):
        currentWave = abs(self.fract) >> 7
        harmonicIndex = (abs(self.fract) & 127) - 1

        #check that it is actually possible to change wave
        for wave, action in enumerate(self.menuActionGroup.actions()):
            if wave == currentWave:
                action.setEnabled(True)
                action.setChecked(True)
                continue
            action.setEnabled(bool(self.baseModel.index(harmonicIndex, wave).data(FractRole)))

        res = self.menu.exec_(self.mapToGlobal(self.waveWidget.geometry().bottomLeft()))
        if res is not None and res.data() is not None:
            fract = (abs(self.fract) & 127) + (res.data() << 7)
            if self.fract < 0:
                fract *= -1
            self.setFract(fract)

    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        qp.setPen(QtCore.Qt.white)
        qp.setBrush(QtCore.Qt.white)
        qp.drawText(self.fakeCombo.geometry().adjusted(0, 0, -self.arrowWidth, 0), QtCore.Qt.AlignCenter, '/{}'.format(abs(self.fract) & 127))
        qp.setRenderHints(qp.Antialiasing)
        qp.translate(self.rect().right() - self.arrowWidth / 2 - .5, self.fakeCombo.geometry().center().y() + .5)
        qp.drawPath(self.arrowPath)


class AddSliderButton(QtWidgets.QPushButton):
    def __init__(self):
        QtWidgets.QPushButton.__init__(self, ' + ')
        palette = self.palette()
        palette.setColor(palette.ButtonText, QtCore.Qt.white)
        font = self.font()
        font.setPointSizeF(font.pointSize() * 1.5)
        self.setFont(font)
        self.setPalette(palette)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Expanding))
        self.setStyleSheet('''
            QPushButton {{
                border: 1px solid rgba({});
                border-style: outset;
                border-radius: 4px;
                margin: 4px;
                background: rgba(128, 128, 128, 128);
            }}
            QPushButton:hover {{
                background: rgba(128, 128, 128, 192);
            }}
            QPushButton:pressed {{
                border-style: inset;
            }}
        '''.format(', '.join(str(c) for c in waveColors[0].getRgb()[:3])))


class HarmonicsSlider(QtWidgets.QWidget):
    baseSize = QtCore.QSize(24, 80)
    basePen = basePenEnabled = QtGui.QPen(QtGui.QColor(64, 192, 216))
    basePenDisabled = QtGui.QPen(QtGui.QColor(64, 192, 216, 128))
    valuePen = valuePenEnabled = QtGui.QPen(QtGui.QColor(64, 192, 216), 2)
    valuePenDisabled = QtGui.QPen(QtGui.QColor(64, 192, 216, 128), 2)
    midPen = midPenEnabled = QtGui.QPen(QtGui.QColor(64, 192, 216), 1)
    midPenDisabled = QtGui.QPen(QtGui.QColor(64, 192, 216), 1)
    brush = brushEnabled = QtGui.QLinearGradient(0, 0, 0, 1)
    brush.setCoordinateMode(brush.ObjectBoundingMode)
    brush.setColorAt(0, QtGui.QColor(0, 128, 192, 64))
    brush.setColorAt(1, QtGui.QColor(0, 128, 192, 192))
    brushDisabled = QtGui.QLinearGradient(0, 0, 0, 1)
    brushDisabled.setCoordinateMode(brushDisabled.ObjectBoundingMode)
    brushDisabled.setColorAt(0, QtGui.QColor(0, 128, 192, 32))
    brushDisabled.setColorAt(1, QtGui.QColor(0, 128, 192, 96))
    sliderEnabled = True

    valueChanged = QtCore.pyqtSignal([int, float], [float, float])
    polarityChanged = QtCore.pyqtSignal(int)
    selected = QtCore.pyqtSignal(bool)
    drag = QtCore.pyqtSignal(float)
    triggered = QtCore.pyqtSignal()
    value = 0
    fract = None

    names = [
        'Fundamental', 
        '1st octave', 
        '5th above 1st octave', 
        '2nd octave', 
        '3rd above 2nd octave', 
        '5th above 2nd octave', 
        '~7th above 2nd octave', 
        '4th octave', 
        '2nd above 4th octave', 
        'maj 3rd above 4th octave', 
        '~4th above 4th octave', 
        '5th above 4th octave', 
        '~min 6th above 4th octave', 
        '~min 7th above 4th octave', 
        'maj 7th above 4th octave', 
        '5th octave'
    ]

    def __init__(self, fract, interactive=False):
        QtWidgets.QWidget.__init__(self)
        self.setMouseTracking(True)
        self.interactive = interactive
        self.arrow = False
        self.setFract(fract)
        self.labelFont = self.font()
        self._selected = False
        fontHeight = self.fontMetrics().height() * 1.5
        self.baseSize = QtCore.QSize(self.baseSize)
        self.sliderRect = QtCore.QRect(QtCore.QPoint(0, 0), self.baseSize)
        if not interactive:
            self.baseSize.setHeight(self.baseSize.height() + fontHeight)
            self.setMinimumSize(self.baseSize)
            self.labelRect = QtCore.QRect(0, 0, self.baseSize.width(), fontHeight)
            self.panelRect = QtCore.QRect()
        else:
            self.baseSize.setHeight(self.baseSize.height() + fontHeight * 2)
            self.setMinimumSize(self.baseSize)
            self.panelRect = QtCore.QRect(0, 2, self.baseSize.width(), fontHeight - 4)
            self.labelRect = QtCore.QRect(0, fontHeight, self.baseSize.width(), fontHeight)

            self.menu = QtWidgets.QMenu()
            self.menuActionGroup = QtWidgets.QActionGroup(self.menu)
            for wave, label in enumerate(WaveLabels):
                action = self.menu.addAction(WaveIcon(wave), label)
                action.setCheckable(True)
                self.menuActionGroup.addAction(action)
                if wave:
                    action.setEnabled(False)

        self.sliderRect.moveTop(self.labelRect.bottom())

    def setFract(self, fract):
        if fract == self.fract:
            return
        self.fract = fract
        fract = abs(fract)
        self.label = '/{}'.format(fract)
        if self.interactive:
            if 'linux' in sys.platform:
                self.label += u' ▾'
            else:
                self.label += '   '
                self.arrow = True
        else:
            self.arrow = False
        if fract <= len(self.names):
            self.statusName = self.names[fract - 1]
        else:
            self.statusName = '{} harmonic'.format(getCardinal(fract))
        self.setStatusTip()
        self.update()

    def setStatusTip(self, emit=False):
#        strValue = '{:.02f}'.format(self.value * 50).rstrip('0').rstrip('.')
        statusText = '{} ({:.02f}%)'.format(self.statusName, self.value * 100)
        if abs(self.fract) >> 7:
            statusText += ' ' + WaveLabels[abs(self.fract >> 7)].lower()
        if self.fract < 0:
            statusText += ' negative'
        QtWidgets.QWidget.setStatusTip(self, statusText)
        if emit:
            QtWidgets.QApplication.sendEvent(self.window(), QtGui.QStatusTipEvent(self.statusTip()))

    def sizeHint(self):
        return self.baseSize

    def wheelEvent(self, event):
        if self.sliderEnabled:
            multi = .2 if event.modifiers() == QtCore.Qt.ShiftModifier else 1
            self.setValue(self.value + (.05 if event.delta() > 0 else -.05) * multi)

    def getValueFromY(self, y):
        y = sanitize(0, y - self.sliderRect.top(), self.sliderRect.bottom())
        return (1 - float(y) / self.sliderRect.height())

    def setSelected(self, selected):
        if self._selected == selected:
            return
        self._selected = selected
        self.labelFont = self.font()
        self.labelFont.setBold(selected)
        self.selected.emit(selected)

    def contextMenuEvent(self, event):
        if not self.interactive:
            event.ignore()
            return
        self.menuActionGroup.actions()[abs(self.fract) >> 7].setChecked(True)
        self.menu.exec_(QtGui.QCursor.pos())

    def mousePressEvent(self, event):
        if event.buttons() == QtCore.Qt.LeftButton:
            if event.pos() in self.panelRect:
                self.togglePolarity()
                return event.ignore()
            if event.pos() in self.labelRect:
                if not self.interactive:
                    self.setSelected(not self._selected)
                    self.update()
                else:
                    self.triggered.emit()
                return event.ignore()
            if not self.sliderEnabled:
                return event.accept()
            self.setValue(self.getValueFromY(event.pos().y()))
        elif event.buttons() == QtCore.Qt.MiddleButton and self.sliderEnabled:
            self.setValue(.5)
        self.drag.emit(self.value)
        event.ignore()

    def mouseMoveEvent(self, event, ignore=False, override=.5):
        if event.buttons() == QtCore.Qt.LeftButton and (ignore or event.pos() in self.rect()) and not event.modifiers():
            if event.pos() in self.labelRect|self.panelRect:
                return event.ignore()
            if not self.sliderEnabled:
                return event.accept()
            self.setValue(self.getValueFromY(event.pos().y()))
        elif (event.buttons() == QtCore.Qt.MiddleButton or 
            (event.buttons() == QtCore.Qt.LeftButton and event.modifiers() == QtCore.Qt.ShiftModifier)) and \
            (ignore or event.pos() in self.rect()):
                self.setValue(override if event.modifiers() == QtCore.Qt.ShiftModifier else .5)
        if event.pos() not in self.rect():
            event.ignore()

    def mouseReleaseEvent(self, event):
        self.drag.emit(-1)
        QtWidgets.QWidget.mouseReleaseEvent(self, event)

    def setValue(self, value, emit=True):
        if value == self.value:
            return
        oldValue = self.value
        self.value = sanitize(0, value, 1)
        self.rebuildPaths()
        self.update()
        self.setStatusTip(emit)
        if emit:
            self.valueChanged.emit(self.fract, self.value)
            self.valueChanged[float, float].emit(self.value, oldValue)

    def togglePolarity(self):
        self.setFract(self.fract * -1)
#        self.curvePath = self.positivePath if self.polarity > 0 else self.negativePath
        self.polarityChanged.emit(self.fract)
        self.setStatusTip(True)
        self.update()

    def setSliderEnabled(self, enabled):
        self.sliderEnabled = enabled
        if enabled:
            self.basePen = self.basePenEnabled
            self.valuePen = self.valuePenEnabled
            self.midPen = self.midPenEnabled
            self.brush = self.brushEnabled
        else:
            self.basePen = self.basePenDisabled
            self.valuePen = self.valuePenDisabled
            self.midPen = self.midPenDisabled
            self.brush = self.brushDisabled
        self.update()

    def changeEvent(self, event):
        if event.type() == QtCore.QEvent.EnabledChange:
            self.setSliderEnabled(self.isEnabled())

    def resizeEvent(self, event):
        if self.interactive:
            self.rebuildPaths()

    def rebuildPaths(self):
        self.positivePath = QtGui.QPainterPath()
        self.negativePath = QtGui.QPainterPath()
#        self.curvePath = self.positivePath if self.polarity > 0 else self.negativePath
        y = self.panelRect.height() / 2.
        count = self.panelRect.width() - 4
        values = waveFunction[abs(self.fract) >> 7](1, count)
#        ratio = self.value / 2.
        for x, v in zip(range(count), values):
            self.positivePath.lineTo(x, -v * y * self.value)
            self.negativePath.lineTo(x, v * y * self.value)
        self.negativePath.translate(2, 2 + y)
        self.positivePath.translate(2, 2 + y)
        self.arrowPath = QtGui.QPainterPath()
        size = self.fontMetrics().height() * .25
        self.arrowPath.moveTo(-size, -size)
        self.arrowPath.lineTo(size, -size)
        self.arrowPath.lineTo(0, size)
        self.arrowPath.closeSubpath()

    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        qp.translate(.5, .5)
        qp.setRenderHints(qp.Antialiasing)

        if self.interactive:
            if self.fract > 0:
                qp.drawPath(self.positivePath)
            else:
                qp.save()
                qp.setBrush(QtCore.Qt.black)
                qp.setPen(QtCore.Qt.NoPen)
                qp.drawRect(self.panelRect)
                qp.setPen(QtCore.Qt.white)
                qp.drawPath(self.negativePath)
                qp.restore()
        qp.setFont(self.labelFont)
        qp.drawText(self.labelRect, QtCore.Qt.AlignCenter, self.label)
        if self.arrow:
            qp.save()
            qp.setBrush(qp.pen().color())
            qp.setPen(QtCore.Qt.NoPen)
#            qp.translate(self.labelRect.adjusted(self.labelRect.center().x(), 0, 0, 0).center())
            qp.translate(self.labelRect.width() * .8, self.labelRect.center().y())
            qp.drawPath(self.arrowPath)
            qp.restore()

        qp.setPen(self.basePen)
        qp.setBrush(QtCore.Qt.black)
        qp.drawRect(self.sliderRect.adjusted(0, 0, -1, -1))

        qp.save()
        qp.translate(0, self.labelRect.bottom())
        qp.setPen(QtCore.Qt.NoPen)
        qp.setBrush(self.brush)
        rect = QtCore.QRectF(1, 1, self.width() - 2, self.sliderRect.height() - 2)
        rect.setTop(self.sliderRect.height() * (1 - self.value) + 1)
        qp.drawRect(rect)
        qp.setPen(self.valuePen)
        qp.drawLine(rect.left(), rect.top() - 1, rect.right(), rect.top() - 1)
        qp.restore()

        qp.setPen(self.midPen)
        y = self.sliderRect.center().y() + 1
        qp.drawLine(1, y, self.width() - 2, y)


class HarmonicsWidget(QtWidgets.QWidget):
    harmonicsChanged = QtCore.pyqtSignal(object)

    def __init__(self, *args, **kwargs):
        QtWidgets.QWidget.__init__(self, *args, **kwargs)
        layout = QtWidgets.QHBoxLayout()
#        layout.setSizeConstraint(layout.SetFixedSize)
        self.setLayout(layout)
        layout.setSpacing(2)
        self.setContentsMargins(1, 1, 1, 1)
        layout.setContentsMargins(1, 1, 1, 1)
        self.sliders = []
        self.selection = set()
        self.values = [0 for _ in range(50)]
        self.override = -1
        for f in range(1, 51):
            slider = HarmonicsSlider(f)
            layout.addWidget(slider)
            slider.installEventFilter(self)
            slider.valueChanged.connect(self.setHarmonic)
            slider.selected.connect(self.setSelection)
            slider.drag.connect(self.setOverride)
            self.sliders.append(slider)
#        self.setFixedSize(self.size())

    def setOverride(self, value):
        self.override = value

    def setSelection(self, selected):
        if selected:
            self.selection.add(self.sender().fract - 1)
        else:
            self.selection.discard(self.sender().fract - 1)

    def selectAll(self):
        [s.setSelected(True) for s in self.sliders]

    def selectNone(self):
        [s.setSelected(False) for s in self.sliders]

    def selectEven(self):
        [s.setSelected(i & 1) for i, s in enumerate(self.sliders)]

    def selectOdd(self):
        [s.setSelected(not i & 1) for i, s in enumerate(self.sliders)]

    def reset(self):
        for slider in self.sliders:
            slider.setValue(0, False)
        self.values = [0 for _ in range(50)]

    def setHarmonic(self, harmonic, value):
        harmonic -= 1
        self.values[harmonic] = value
        if harmonic in self.selection:
            for h in self.selection - set((harmonic, )):
                self.sliders[h].setValue(value, False)
                self.values[h] = value
        self.harmonicsChanged.emit(self.values)

    def contextMenuEvent(self, event):
#        slider = QtWidgets.QApplication.widgetAt(event.globalPos())
        menu = QtWidgets.QMenu()
        child = self.childAt(event.pos())
        if child:
            selected = child.fract - 1 in self.selection
            selectAction = menu.addAction('Deselect' if selected else 'Select')
            if not selected:
                selectAction.setIcon(QtGui.QIcon.fromTheme('checkbox'))
                selectAction.triggered.connect(lambda: child.setSelected(not selected))
        selectAllAction = menu.addAction(QtGui.QIcon.fromTheme('edit-select-all'), 'Select all')
        selectAllAction.triggered.connect(self.selectAll)
        selectNoneAction = menu.addAction(QtGui.QIcon.fromTheme('edit-select-none'), 'Select none')
        selectNoneAction.triggered.connect(self.selectNone)

        evenAction = menu.addAction(QtGui.QIcon.fromTheme('harmonics-even'), 'Select even harmonics')
        evenAction.triggered.connect(self.selectEven)
        oddAction = menu.addAction(QtGui.QIcon.fromTheme('harmonics-odd'), 'Select odd harmonics')
        oddAction.triggered.connect(self.selectOdd)

        menu.addSeparator()
        resetAllAction = menu.addAction(QtGui.QIcon.fromTheme('chronometer-reset'), 'Reset all harmonics')
        scaleAction = menu.addAction(QtGui.QIcon.fromTheme('harmonics-decrease'), 'Set decreasing harmonic values')
        defaultAction = menu.addAction('Set all harmonics to 100%')
        res = menu.exec_(QtGui.QCursor.pos())
        if res == resetAllAction:
            [s.setValue(0, False) for s in self.sliders]
            self.values = [0] * 50
            self.harmonicsChanged.emit(self.values)
        elif res == defaultAction:
            [s.setValue(2, False) for s in self.sliders]
            self.values = [2] * 50
            self.harmonicsChanged.emit(self.values)
        elif res == scaleAction:
            self.values = []
            self.sliders[0].setValue(1, False)
            for s, v in enumerate(range(1, 50)):
                value = 1 - v * .02
                self.sliders[s].setValue(value, False)
                self.values.append(value)
            self.sliders[-1].setValue(0, False)
            self.values.append(0)
            self.harmonicsChanged.emit(self.values)

    def eventFilter(self, source, event):
        if event.type() == QtCore.QEvent.MouseMove and \
            (event.buttons() & (QtCore.Qt.LeftButton | QtCore.Qt.MiddleButton)):
                widget = QtWidgets.QApplication.widgetAt(event.globalPos())
                if widget != source and isinstance(widget, HarmonicsSlider):
                    widget.mouseMoveEvent(event, True, self.override if self.override >= 0 else 1)
                    return True
                elif widget == source and event.modifiers() == QtCore.Qt.ShiftModifier and self.override >= 0:
                    widget.mouseMoveEvent(event, False, self.override)
                    return True
        return QtWidgets.QWidget.eventFilter(self, source, event)


class HarmonicsMiniWidget(QtWidgets.QWidget):
    grad = QtGui.QLinearGradient(0, 0, 0, 1)
    grad.setCoordinateMode(grad.StretchToDeviceMode)
    grad.setColorAt(0, QtGui.QColor(0, 128, 192, 128))
    grad.setColorAt(1, QtGui.QColor(0, 128, 192, 224))
    pen = QtGui.QPen(QtGui.QBrush(grad), 1)

    def __init__(self, scrollArea, harmonicsWidget):
        QtWidgets.QWidget.__init__(self)
        self.setFixedWidth(52)
        self.scrollArea = scrollArea
        self.harmonicsWidget = harmonicsWidget
        harmonicsWidget.harmonicsChanged.connect(self.update)
        self.scrollArea.horizontalScrollBar().valueChanged.connect(self.resetArea)
        self.extent = QtCore.QRect(0, 0, 50, self.height())

    def resetArea(self):
        left = self.harmonicsWidget.mapFrom(self.scrollArea, self.scrollArea.viewport().geometry().topLeft()).x()
        right = self.harmonicsWidget.mapFrom(self.scrollArea, self.scrollArea.viewport().geometry().topRight()).x()
        width = self.harmonicsWidget.width()
        ratio = 50./width
        self.extent.setLeft(left * ratio)
        self.extent.setRight(right * ratio)
        self.update()
#        print(left, right, self.harmonicsWidget.width())

    @property
    def values(self):
        return self.harmonicsWidget.values

    def wheelEvent(self, event):
        QtWidgets.QApplication.sendEvent(self.scrollArea.horizontalScrollBar(), event)

    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        qp.setRenderHints(qp.Antialiasing)
        qp.setBrush(QtCore.Qt.black)
        qp.drawRect(self.rect().adjusted(1, 1, -1, -1))
        qp.save()
        qp.setPen(self.pen)
        qp.translate(1.5, .5)
        bottom = self.height() - 1
        ratio = (bottom - 1.) / 2
        for i, value in enumerate(self.values):
            if not value:
                continue
            qp.save()
            y = bottom - value * ratio
            qp.translate(i, y)
            qp.drawLine(0, 0, 0, bottom - y)
            qp.restore()
        qp.setPen(QtCore.Qt.NoPen)
        qp.setBrush(QtGui.QColor(255, 255, 255, 64))
        qp.drawRect(self.extent)
        qp.restore()
        qp.setPen(QtCore.Qt.black)
        qp.setBrush(QtCore.Qt.NoBrush)
        qp.translate(.5, .5)
        qp.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 2, 2)


class HarmonicsScrollArea(QtWidgets.QScrollArea):
    mousePos = None

    def setWidget(self, widget):
        QtWidgets.QScrollArea.setWidget(self, widget)
        self.miniWidget = HarmonicsMiniWidget(self, widget)
        self.addScrollBarWidget(self.miniWidget, QtCore.Qt.AlignRight)

    @property
    def labelRect(self):
        try:
            return self._labelRect
        except:
            first = self.widget().sliders[0]
            self._labelRect = QtCore.QRect(first.mapToParent(first.labelRect.topLeft()), 
                self.widget().sliders[-1].mapToParent(first.labelRect.topLeft()))
            return self._labelRect

    def mousePressEvent(self, event):
        self.mousePos = event.pos()
        QtWidgets.QScrollArea.mousePressEvent(self, event)

    def mouseMoveEvent(self, event):
        if event.buttons() & (QtCore.Qt.LeftButton | QtCore.Qt.MiddleButton):
            delta = event.pos() - self.mousePos
            if self.horizontalScrollBar().value() < self.horizontalScrollBar().maximum() and \
                event.pos().x() >= self.rect().right() - 4 and delta.x() > 0:
                    self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() + delta.x())
            elif self.horizontalScrollBar().value() > self.horizontalScrollBar().minimum() and \
                event.pos().x() <= 4 and delta.x() < 0:
                    self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() + delta.x())
            else:
                self.mousePos = event.pos()
#        QtWidgets.QScrollArea.mouseMoveEvent(self, event)

    def mouseReleaseEvent(self, event):
        self.mousePos = None
        QtWidgets.QScrollArea.mouseReleaseEvent(self, event)

    def resizeEvent(self, event):
        left, top, right, bottom = self.getContentsMargins()
        self.setMinimumHeight(self.widget().sizeHint().height() + top + bottom)
        QtWidgets.QScrollArea.resizeEvent(self, event)
        self.miniWidget.resetArea()


class DefaultSlider(QtWidgets.QSlider):
    def reset(self):
        try:
            self.setValue(self.defaultValue)
        except:
            self.setValue(self.minimum() + (self.maximum() - self.minimum()) / 2)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MiddleButton:
            self.reset()
        else:
            QtWidgets.QSlider.mousePressEvent(self, event)

    def mouseMoveEvent(self, event):
        if event.button() != QtCore.Qt.MiddleButton:
            QtWidgets.QSlider.mouseMoveEvent(self, event)


class VolumeSlider(DefaultSlider):
    def __init__(self, *args, **kwargs):
        DefaultSlider.__init__(self, *args, **kwargs)
        self.defaultValue = 100
        self.valueChanged.connect(self.setToolTipValue)

    def setToolTipValue(self, value):
        text = '{}%'.format(value)
        self.setToolTip(text)


class VolumeIcon(QtWidgets.QLabel):
    step = QtCore.pyqtSignal(int)
    reset = QtCore.pyqtSignal()
    iconSize = 16

    def setVolume(self, value):
        if value <= 25:
            themeIcon = 'audio-volume-low'
        elif value <= 75:
            themeIcon = 'audio-volume-medium'
        elif value <= 150:
            themeIcon = 'audio-volume-high'
        else:
            themeIcon = 'audio-volume-max'
        self.setPixmap(QtGui.QIcon.fromTheme(themeIcon).pixmap(self.iconSize))
        self.setToolTip('{}%'.format(value))

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MiddleButton:
            self.reset.emit()
        else:
            QtWidgets.QLabel.mousePressEvent(self, event)

    def wheelEvent(self, event):
        if event.delta() > 0:
            step = 1
        else:
            step = -1
        self.step.emit(step)


class SwitchableHandle(QtWidgets.QWidget):
    borderPen = borderNormalPen = QtGui.QPen(QtCore.Qt.lightGray, .5)
    borderNormalPen.setCosmetic(True)
    borderHoverPen = QtGui.QPen(QtCore.Qt.darkGray, .5)
    borderHoverPen.setCosmetic(True)
    arrowPen = QtGui.QPen(QtCore.Qt.darkGray, 2)
    arrowPen.setCosmetic(True)

    arrow = QtGui.QPainterPath()
    arrow.moveTo(-4, -1.5)
    arrow.lineTo(0, 1.5)
    arrow.lineTo(4, -1.5)

    collapsed = False
    handleWidth = 11

    def sizeHint(self):
        return QtCore.QSize(1, 1)

    def enterEvent(self, event):
        self.borderPen = self.borderHoverPen
        self.update()

    def leaveEvent(self, event):
        self.borderPen = self.borderNormalPen
        self.update()

    def mousePressEvent(self, event):
        self.parent().setCollapsed(not self.collapsed)
        self.parent().toggled.emit(self.collapsed)

    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        qp.setRenderHints(qp.Antialiasing)
        width = self.width()
        qp.setPen(self.borderPen)
        qp.translate(.5, .5)
        qp.drawRoundedRect(0, 0, width - 1, self.handleWidth - 1, 2, 2)
        qp.setPen(self.arrowPen)
        ratio = width / 128
        deltaX = width / ratio
        qp.translate(deltaX * .5, (self.handleWidth - 1) * .5)
        if self.collapsed:
            qp.rotate(180)
            qp.translate(-width + deltaX, 0)
        for pos in range(int(ratio)):
            qp.drawPath(self.arrow)
            qp.translate(deltaX, 0)


class SwitchablePanel(QtWidgets.QWidget):
    collapsed = False
    contentName = ''
    switchVisible = True
    handleWidth = 11
    toggled = QtCore.pyqtSignal(bool)

    def __init__(self, *args, **kwargs):
        QtWidgets.QWidget.__init__(self, *args, **kwargs)
        self.setContentsMargins(0, self.handleWidth, 0, 0)
        self.handle = SwitchableHandle(self)
#        self.setMouseTracking(True)

    def setContentName(self, name=''):
        self.contentName = name
        self.update()

    def setHandleWidth(self, width):
        self.handleWidth = self.handle.handleWidth = width
        if self.switchVisible:
            self.setContentsMargins(0, self.handleWidth, 0, 0)

    def setSwitchVisible(self, visible):
        self.switchVisible = visible
        self.handle.setVisible(visible)
        if visible:
            self.setContentsMargins(0, self.handleWidth, 0, 0)
        else:
            self.setContentsMargins(0, 0, 0, 0)

    def event(self, event):
        if isinstance(event, QtGui.QHelpEvent):
            if event.y() <= self.handleWidth:
                QtWidgets.QToolTip.showText(
                    event.globalPos(), 
                    '{}{}'.format('Show' if self.collapsed else 'Hide', ' ' + self.contentName if self.contentName else ''), 
                    self)
        return QtWidgets.QWidget.event(self, event)

    def getFirstLevelWidgets(self, layout):
        widgets = []
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if isinstance(item, QtWidgets.QLayout):
                widgets.extend(self.getFirstLevelWidgets(item))
            elif item.widget():
                widgets.append(item.widget())
        return widgets

    @property
    def handleRect(self):
        return QtCore.QRect(0, 0, self.width(), self.handleWidth) if self.switchVisible else QtCore.QRect()

    @property
    def firstLevelWidgets(self):
        try:
            return self._firstLevelWidgets
        except:
            self._firstLevelWidgets = self.getFirstLevelWidgets(self.layout())
            return self._firstLevelWidgets

    def setCollapsed(self, collapsed):
        if self.firstLevelWidgets is None:
            self.firstLevelWidgets = self.getFirstLevelWidgets(self.layout())
        if self.collapsed != collapsed:
            if collapsed:
                [w.setVisible(False) for w in self.firstLevelWidgets]
                self.setMaximumHeight(self.minimumSizeHint().height())
            else:
                [w.setVisible(True) for w in self.firstLevelWidgets]
                self.setMaximumHeight(16777215)
            self.collapsed = collapsed
        self.handle.collapsed = collapsed

    def resizeEvent(self, event):
        self.handle.resize(self.width(), self.handleWidth)


class CollapsibleGroupBox(QtWidgets.QGroupBox):
    collapsed = False
    collapsedChanged = QtCore.pyqtSignal(bool)
    arrows = u'▾▴'

    def __init__(self, *args, **kwargs):
        QtWidgets.QGroupBox.__init__(self, *args, **kwargs)
        self.setMouseTracking(True)
        self.baseFont = self.font()
        self.hoverFont = QtGui.QFont(self.baseFont)
        self.hoverFont.setUnderline(True)
#        self._title = self.title()

    def _setTitle(self, title=None):
        if title is None:
            title = self._title
        self._title = title
        QtWidgets.QGroupBox.setTitle(self, u'{0} {1} {0}'.format(self.arrows[self.collapsed], title))

    def checkHover(self, pos):
        option = QtWidgets.QStyleOptionGroupBox()
        self.initStyleOption(option)
        rect = self.style().subControlRect(QtWidgets.QStyle.CC_GroupBox, option, QtWidgets.QStyle.SC_GroupBoxLabel, self)
        rect.setLeft(self.rect().left())
        rect.setRight(self.rect().right())
        if pos in rect:
            if not self.styleSheet():
                self.setStyleSheet('''
                    CollapsibleGroupBox {
                        text-decoration: underline;
                    }
                ''')
        else:
            self.setStyleSheet('')

    def getFirstLevelWidgets(self, layout):
        widgets = []
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if isinstance(item, QtWidgets.QLayout):
                widgets.extend(self.getFirstLevelWidgets(item))
            elif item.widget():
                widgets.append(item.widget())
        return widgets

    @property
    def firstLevelWidgets(self):
        try:
            return self._firstLevelWidgets
        except:
            self._firstLevelWidgets = self.getFirstLevelWidgets(self.layout())
            return self._firstLevelWidgets

    def setCollapsed(self, collapsed):
        if self.firstLevelWidgets is None:
            self.firstLevelWidgets = self.getFirstLevelWidgets(self.layout())
        if self.collapsed != collapsed:
            if collapsed:
                [w.setVisible(False) for w in self.firstLevelWidgets]
                self.setMaximumHeight(self.minimumSizeHint().height())
            else:
                [w.setVisible(True) for w in self.firstLevelWidgets]
                self.setMaximumHeight(16777215)
            self.collapsed = collapsed
#        self.setTitle()
        self.collapsedChanged.emit(collapsed)

    def mouseMoveEvent(self, event):
        self.checkHover(event.pos())

    def leaveEvent(self, event):
        self.setStyleSheet('')

    def mousePressEvent(self, event):
        if self.maximumHeight() == 16777215:
            self.setCollapsed(True)
        else:
            self.setCollapsed(False)
        QtWidgets.QGroupBox.mousePressEvent(self, event)

    def resizeEvent(self, event):
        self.checkHover(self.mapFromGlobal(QtGui.QCursor.pos()))
        self.arrowPath = QtGui.QPainterPath()
        size = self.fontMetrics().height() * .25
        self.arrowPath.moveTo(-size, -size)
        self.arrowPath.lineTo(size, -size)
        self.arrowPath.lineTo(0, size)
        self.arrowPath.closeSubpath()

    def paintEvent(self, event):
        QtWidgets.QGroupBox.paintEvent(self, event)
        option = QtWidgets.QStyleOptionGroupBox()
        self.initStyleOption(option)
        labelRect = self.style().subControlRect(QtWidgets.QStyle.CC_GroupBox, option, QtWidgets.QStyle.SC_GroupBoxLabel)
        qp = QtGui.QPainter(self)
        arrow = self.arrows[self.collapsed]
        width = option.fontMetrics.width(arrow)
        labelRect.setLeft(labelRect.left() - width - 5)
        labelRect.setRight(labelRect.right() + width + 5)
        if 'win32' in sys.platform:
            qp.setRenderHints(qp.Antialiasing)
            qp.setBrush(QtCore.Qt.darkGray)
            qp.save()
            qp.translate(labelRect.left(), labelRect.center().y())
            qp.drawPath(self.arrowPath)
            qp.restore()
            qp.translate(labelRect.right(), labelRect.center().y())
            qp.drawPath(self.arrowPath)
        else:
            qp.setFont(QtWidgets.QApplication.font())
            qp.drawText(labelRect, QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop, arrow)
            qp.drawText(labelRect, QtCore.Qt.AlignRight|QtCore.Qt.AlignTop, arrow)


class AdvancedSplitterHandle(QtWidgets.QSplitterHandle):
    moved = QtCore.pyqtSignal(object, int, int, int)
    released = QtCore.pyqtSignal()

    def mousePressEvent(self, event):
        self.oldY = self.pos().y()
        self.oldMouse = self.mapToGlobal(event.pos())
        QtWidgets.QSplitterHandle.mousePressEvent(self, event)

    def mouseMoveEvent(self, event):
        QtWidgets.QSplitterHandle.mouseMoveEvent(self, event)
        self.moved.emit(self, self.oldY, self.mapToGlobal(event.pos()).y() - self.oldMouse.y(), event.pos().y())


class AdvancedSplitter(QtWidgets.QSplitter):
    def __init__(self, *args, **kwargs):
        QtWidgets.QSplitter.__init__(self, *args, **kwargs)
        self.currentHandle = self.currentClosest = None

    def checkContents(self, handle, oldPos, delta, mousePos):
        widget = self.widget(handle.index)
        if not isinstance(widget, CollapsibleGroupBox) or not widget.isEnabled():
            return
        requested = oldPos + delta
        closest = self.closestLegalPosition(requested, handle.index)
        diff = requested - closest
        if diff > 20:
            if handle != self.currentHandle or closest + mousePos + 20 > self.currentClosest:
                widget.setCollapsed(True)
                self.currentHandle = handle
                self.currentClosest = closest
        elif diff < -20:
            if handle != self.currentHandle or closest + mousePos - 20 < self.currentClosest:
                widget.setCollapsed(False)
                self.currentHandle = handle
                self.currentClosest = closest
#        print(oldPos, delta)

    def createHandle(self):
        handle = AdvancedSplitterHandle(self.orientation(), self)
        handle.index = self.count() if self.count() else 0
        handle.moved.connect(self.checkContents)
        handle.released.connect(self.release)
        return handle

    def release(self):
        self.currentHandle = self.currentClosest = None


class KeyFrameView(QtWidgets.QGraphicsView):
    startMouse = currentItem = None
    selectionPen = QtGui.QPen(QtGui.QColor(40, 120, 255, 192), 2)
    selectionBrush = QtGui.QColor(40, 60, 220, 128)
    microRect = QtCore.QRectF(0, 0, 10, 60)

    def __init__(self, *args, **kwargs):
        QtWidgets.QGraphicsView.__init__(self, *args, **kwargs)

    def _resizeEvent(self, event):
        transform = QtGui.QTransform()
        height = self.viewport().height()
        ratio = height / (self.scene().height() + 8)
        transform.scale(ratio, ratio)
        self.setTransform(transform)

#    def _keyPressEvent(self, event):
#        if event.key() == QtCore.Qt.Key_Shift:
#            self.setDragMode(self.RubberBandDrag)
#        QtWidgets.QGraphicsView.keyPressEvent(self, event)
#
#    def keyReleaseEvent(self, event):
#        if event.key() == QtCore.Qt.Key_Shift:
#            self.setDragMode(self.NoDrag)
#        QtWidgets.QGraphicsView.keyReleaseEvent(self, event)

    def mousePressEvent(self, event):
        item = self.itemAt(event.pos())
        self.startMouse = event.pos()
        if isinstance(item, SampleItem):
            self.currentItem = item
        QtWidgets.QGraphicsView.mousePressEvent(self, event)
        if not self.scene().maximized and self.scene().hoverMode:
            self.viewport().update()

    def mouseMoveEvent(self, event):
        if event.buttons() & QtCore.Qt.LeftButton and self.startMouse:
#            if QtCore.QLineF(self.startMouse, event.pos()).length() >= QtWidgets.QApplication.startDragDistance():
            if (event.pos() - self.startMouse).manhattanLength() >= QtWidgets.QApplication.startDragDistance():
                if event.modifiers() == QtCore.Qt.ShiftModifier:
                    self.setDragMode(self.RubberBandDrag)
                if self.dragMode() == self.RubberBandDrag:
                    path = QtGui.QPainterPath()
                    path.addRect(QtCore.QRectF(self.startMouse, event.pos()))
                    self.scene().setSelectionArea(path, self.transform())
                    self.viewport().update()
                elif self.scene().selectedItems():
                    self.startDrag()
        elif not self.scene().maximized and self.scene().hoverMode:
            self.viewport().update()
        QtWidgets.QGraphicsView.mouseMoveEvent(self, event)

    def mouseReleaseEvent(self, event):
        self.startMouse = self.currentItem = None
        self.setDragMode(self.NoDrag)
        QtWidgets.QGraphicsView.mouseReleaseEvent(self, event)
        self.viewport().update()

    def focusInEvent(self, event):
        if not self.scene().maximized and self.scene().hoverMode:
            self.viewport().update()
        QtWidgets.QGraphicsView.focusInEvent(self, event)

    def startDrag(self):
        ratio = self.transform().m11()

        height = self.currentItem.geometry().size().height()
        selected = sorted(self.scene().selectedItems(), key=lambda i: i.index)
#        width = selected[-1].geometry().right() - selected[0].geometry().left()
        width = sum(i.geometry().width() for i in selected)

        width = int(width * ratio) + 2
        height = int(height * ratio) + 2

        self.dragObject = ActivateDrag(self)
        mimeData = QtCore.QMimeData()
        byteArray = QtCore.QByteArray()
        stream = QtCore.QDataStream(byteArray, QtCore.QIODevice.WriteOnly)

        pm = QtGui.QPixmap(width, height)
        pm.fill(QtCore.Qt.white)
        qp = QtGui.QPainter(pm)
        qp.setRenderHints(qp.Antialiasing)
        qp.setTransform(self.transform())
        qp.translate(.5, .5)

#        qp.translate(-selected[0].geometry().x(), 0)
        for item in selected:
            qp.save()
            item.paint(qp)
            qp.restore()
            qp.translate(item.geometry().width(), 0)
            stream.writeInt(item.index)
        qp.end()
        mimeData.setData('bigglesworth/SampleItemSelection', byteArray)

        self.dragObject.setPixmap(pm)
        self.dragObject.setMimeData(mimeData)
        self.dragObject.exec_(QtCore.Qt.CopyAction|QtCore.Qt.MoveAction)

    def wheelEvent(self, event):
        event = QtGui.QWheelEvent(event.pos(), -event.delta(), event.buttons(), event.modifiers(), QtCore.Qt.Horizontal)
        QtWidgets.QApplication.sendEvent(self.horizontalScrollBar(), event)
#        self.horizontalScrollBar().wheelEvent(event)

    def paintEvent(self, event):
        QtWidgets.QGraphicsView.paintEvent(self, event)
        if self.dragMode() == self.RubberBandDrag:
            qp = QtGui.QPainter(self.viewport())
            qp.setPen(self.selectionPen)
            qp.setBrush(self.selectionBrush)
            qp.drawPath(self.scene().selectionArea())
        elif self.scene().hoverMode:
            localPos = self.mapFromGlobal(QtGui.QCursor.pos())
            item = self.itemAt(localPos)
            first = self.keyFrames[0]
            if isinstance(item, (WaveTransformItem, SampleItem)):
                index = self.keyFrames.getLayoutIndex(item)
                if not item.boundingRect().width():
                    index -= 1
                    item = self.keyFrames.itemAt(index)
                if not index:
                    return
                qp = QtGui.QPainter(self.viewport())
                qp.setRenderHints(qp.Antialiasing)
                scenePos = self.mapToScene(localPos)
                delta = (item.mapFromScene(scenePos).x() - item.hoverRect.center().x()) * 2
                
                qp.translate(-delta + self.mapFromScene(item.pos()).x(), item.y())
                item.paint(qp, None, None, item.hoverRect)
                if index == 1:
                    qp.save()
                    qp.translate(-80 + delta, 0)
                    first.paint(qp, None, None, first.normalRect.adjusted(0, 0, -20 - delta, 0))
                    qp.restore()
                else:
                    qp.save()
#                    qp.setOpacity((20 - delta) / 20.)
                    qp.translate(-60, 0)
                    beforeIndex = index - 1
                    item = self.keyFrames.itemAt(beforeIndex)
                    if not item.boundingRect().width():
                        beforeIndex -= 1
                        item = self.keyFrames.itemAt(beforeIndex)
                    if item == first:
                        qp.translate(-20, 0)
                        item.paint(qp, None, None, item.hoverRect.adjusted(20 + delta, 0, 20, 0))
                    else:
                        item.paint(qp, None, None, item.hoverRect.adjusted(20 + delta, 0, 0, 0))
                    qp.restore()
                    qp.save()
                    try:
#                        qp.setOpacity((20 - delta) / 40.)
                        qp.translate(delta - 70, 0)
                        for count in range(4):
                            beforeIndex -= 1
                            item = self.keyFrames.itemAt(beforeIndex)
                            if not item.boundingRect().width():
                                beforeIndex -= 1
                                item = self.keyFrames.itemAt(beforeIndex)
                            if item == first:
                                qp.translate(-70 + count * 10 + (3 - count) * 20, 0)
                                item.paint(qp, None, None, item.hoverRect.adjusted(0, 0, -(3 - count) * 10 + 10, 0))
                                break
                            item.paint(qp, None, None, self.microRect)
                            qp.translate(-10, 0)
                    except:
                        pass
                    qp.restore()
                try:
#                    qp.setOpacity((20 + delta) / 20.)
                    restored = False
                    qp.save()
                    qp.translate(60, 0)
                    index += 1
                    item = self.keyFrames.itemAt(index)
                    if not item.boundingRect().width():
                        index += 1
                        item = self.keyFrames.itemAt(index)
                    item.paint(qp, None, None, item.hoverRect.adjusted(0, 0, -20 + delta, 0))
                    qp.restore()
                    restored = True
                    qp.translate(80 + delta, 0)
                    try:
                        for _ in range(4):
                            index += 1
                            item = self.keyFrames.itemAt(index)
                            if not item.boundingRect().width():
                                index += 1
                                item = self.keyFrames.itemAt(index)
                            item.paint(qp, None, None, self.microRect)
                            qp.translate(10, 0)
                    except:
                        pass
                except:
                    if not restored:
                        qp.restore()


class WaveView(QtWidgets.QGraphicsView):
    resized = QtCore.pyqtSignal()

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self.scene().clearSelection()
        QtWidgets.QGraphicsView.keyPressEvent(self, event)

    def resizeEvent(self, event):
        self.fitInView(self.scene().sceneRect())
        self.resized.emit()

    def enterEvent(self, event):
        self.scene().enter()
        QtWidgets.QGraphicsView.enterEvent(self, event)

    def leaveEvent(self, event):
        self.scene().leave()
        QtWidgets.QGraphicsView.leaveEvent(self, event)


class WaveTableView(QtWidgets.QGraphicsView):
    def __init__(self, *args, **kwargs):
        QtWidgets.QGraphicsView.__init__(self, *args, **kwargs)
        self.shearTransform = QtGui.QTransform().shear(0, .23)
        self.setTransform(self.shearTransform)

    def mouseMoveEvent(self, event):
        if self.dragMode() == self.RubberBandDrag:
            self.scene().checkSelection()
        QtWidgets.QGraphicsView.mouseMoveEvent(self, event)

    def resizeEvent(self, event):
#        self.setFixedHeight(self.width() * .75)
        self.fitInView(self.scene().sceneRect(), QtCore.Qt.KeepAspectRatio)


class WaveTableCurrentView(QtWidgets.QGraphicsView):
    shown = False
    wavePen = QtGui.QPen(waveColors[0], 1)
    wavePen.setCosmetic(True)

    def __init__(self, *args, **kwargs):
        QtWidgets.QGraphicsView.__init__(self, *args, **kwargs)
        scene = QtWidgets.QGraphicsScene()
        scene.setSceneRect(QtCore.QRectF(0, -pow20, 127, pow21))
        self.setScene(scene)
        #for performance we are using computed values, not wavepaths, 
        #so we vertically flip the view
        self.setTransform(QtGui.QTransform().scale(1, -1))
        self.queuedUpdate = False
        self.currentIndex = 0
        self.prevKeyFrameIndex = 0
        self.nextKeyFrameIndex = 0
        self.wavePaths = []
        self.wavePathItems = []
        for i in range(64):
            wavePath = QtGui.QPainterPath()
            wavePath.moveTo(0, 0)
            for s in range(1, 128):
                wavePath.lineTo(s, 0)
            wavePathItem = scene.addPath(wavePath)
            wavePathItem.setPen(self.wavePen)
            self.wavePaths.append(wavePath)
            self.wavePathItems.append(wavePathItem)
            wavePathItem.setOpacity(0 if i else 1)
        self.scheduleTimer = QtCore.QTimer()
        self.scheduleTimer.setInterval(50)
        self.scheduleTimer.setSingleShot(True)
        self.scheduleTimer.timeout.connect(self.rebuildPaths)

    def setKeyFramesObj(self, keyFrames):
        self.keyFrames = keyFrames
        keyFrames.changed.connect(self.scheduleUpdate)
        self.scheduleUpdate()

    def scheduleUpdate(self):
        if self.isVisible():
            self.scheduleTimer.start()
        else:
            self.queuedUpdate = True

    def setCurrentIndex(self, index):
        if index == self.currentIndex:
            return
#        if not index:
#            self.wavePathItems[self.currentIndex].setOpacity(0)
        self.wavePathItems[index].setOpacity(1)
        keyFrame = self.keyFrames.get(index)
        if keyFrame:
            if self.nextKeyFrameIndex and self.nextKeyFrameIndex != index:
                self.wavePathItems[self.nextKeyFrameIndex].setOpacity(0)
            self.nextKeyFrameIndex = self.keyFrames.nextIndex(index)
            if self.prevKeyFrameIndex and self.prevKeyFrameIndex != index:
                self.wavePathItems[self.prevKeyFrameIndex].setOpacity(0)
            self.prevKeyFrameIndex = self.keyFrames.previousIndex(index)
            if self.prevKeyFrameIndex < 0:
                self.prevKeyFrameIndex = self.keyFrames[-1].index
        else:
            prevKeyFrameIndex = self.keyFrames.previousIndex(index)
            if prevKeyFrameIndex < 0:
                prevKeyFrameIndex = self.keyFrames[-1].index
            if prevKeyFrameIndex != self.prevKeyFrameIndex:
                self.wavePathItems[self.prevKeyFrameIndex].setOpacity(0)
                self.prevKeyFrameIndex = prevKeyFrameIndex
            nextKeyFrameIndex = self.keyFrames.nextIndex(index)
            if nextKeyFrameIndex != self.nextKeyFrameIndex:
                self.wavePathItems[self.nextKeyFrameIndex].setOpacity(0)
                self.nextKeyFrameIndex = nextKeyFrameIndex
            if nextKeyFrameIndex != prevKeyFrameIndex and self.keyFrames.get(prevKeyFrameIndex).nextTransform.mode:
                last = 64 if not nextKeyFrameIndex else nextKeyFrameIndex
                pos = float(index - prevKeyFrameIndex) / (last - prevKeyFrameIndex) * .5
                self.wavePathItems[prevKeyFrameIndex].setOpacity(.5 - pos)
                self.wavePathItems[nextKeyFrameIndex].setOpacity(pos)
        self.wavePathItems[self.currentIndex].setOpacity(0)
        self.currentIndex = index

    def rebuildPaths(self):
        self.queuedUpdate = False
        waveIter = iter(zip(self.wavePaths, self.wavePathItems))
        for keyFrame in self.keyFrames:
            for i, waveData in enumerate(self.keyFrames.bounce(keyFrame.nextTransform, setValues=False)):
                wavePath, wavePathItem = waveIter.next()
                for sample, value in enumerate(waveData):
                    wavePath.setElementPositionAt(sample, sample, value)
                wavePathItem.setPath(wavePath)

    def resizeEvent(self, event):
        self.fitInView(self.scene().sceneRect(), QtCore.Qt.IgnoreAspectRatio)

    def showEvent(self, event):
        if not self.shown:
            self.shown = True
            self.fitInView(self.scene().sceneRect(), QtCore.Qt.IgnoreAspectRatio)
        if self.queuedUpdate:
            if self.keyFrames.isChanging():
                self.scheduleUpdate()
            else:
                self.rebuildPaths()



class WaveTableMiniView(QtWidgets.QGraphicsView):
    clicked = QtCore.pyqtSignal()

    def resizeEvent(self, event):
        self.setFixedWidth(self.height() * 1.25)
        self.fitInView(self.scene().sceneRect(), QtCore.Qt.KeepAspectRatio)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.clicked.emit()


class ExtendedTabBar(QtWidgets.QTabBar):
    def tabSizeHint(self, index):
        hint = QtWidgets.QTabBar.tabSizeHint(self, index)
        hint.setWidth(self.parent().width() / self.count() - 1)
        return hint


class WaveTabWidget(QtWidgets.QTabWidget):
    def __init__(self, *args, **kwargs):
        QtWidgets.QTabWidget.__init__(self, *args, **kwargs)
        self.setTabBar(ExtendedTabBar(self))

    def resizeEvent(self, event):
        if not self.minimumHeight():
            self.setMinimumHeight(self.minimumSizeHint().height())
        QtWidgets.QTabWidget.resizeEvent(self, event)


class MainTabBar(DroppableTabBar):
    def __init__(self, *args, **kwargs):
        from bigglesworth.wavetables.audioimport import AudioImportTab
        self.reference = AudioImportTab
        DroppableTabBar.__init__(self, *args, **kwargs)

    def mousePressEvent(self, event):
        self.index = self.tabAt(event.pos())
        self.importTab = self.parent().widget(self.index)
        if isinstance(self.importTab, self.reference) and not self.importTab.previewMode:
            self.startPos = event.pos()
        else:
            self.startPos = None
        QtWidgets.QTabBar.mousePressEvent(self, event)

    def mouseMoveEvent(self, event):
        if self.startPos and (event.pos() - self.startPos).manhattanLength() >= QtWidgets.QApplication.startDragDistance():
            self.startDrag()

    def startDrag(self):
        option = QtWidgets.QStyleOptionTabV3()
        self.initStyleOption(option, self.index)
        option.position = option.OnlyOneTab
        option.selectedPosition = option.NotAdjacent
        pm = QtGui.QPixmap(option.rect.size())
        pm.fill(QtCore.Qt.transparent)
        qp = QtGui.QPainter(pm)
        qp.translate(-option.rect.left(), 0)
        self.style().drawPrimitive(QtWidgets.QStyle.PE_FrameTabBarBase, option, qp)
        self.style().drawControl(QtWidgets.QStyle.CE_TabBarTab, option, qp)
        self.style().drawControl(QtWidgets.QStyle.CE_TabBarTabShape, option, qp)
        self.style().drawControl(QtWidgets.QStyle.CE_TabBarTabLabel, option, qp)
        qp.end()

        self.dragObject = ActivateDrag(self)
        mimeData = QtCore.QMimeData()
        byteArray = QtCore.QByteArray()
        stream = QtCore.QDataStream(byteArray, QtCore.QIODevice.WriteOnly)
        stream.writeQVariant(self.window().uuid)
        stream.writeQString(self.importTab.currentInfo.name)
        print(self.importTab.currentInfo.name)

        mimeData.setData('bigglesworth/WaveFilePath', byteArray)

        self.dragObject.setPixmap(pm)
        self.dragObject.setMimeData(mimeData)
        self.dragObject.exec_(QtCore.Qt.CopyAction)


class MainTabWidget(QtWidgets.QTabWidget):
    dropTabFileRequested = QtCore.pyqtSignal(str, int)

    def __init__(self, *args, **kwargs):
        QtWidgets.QTabWidget.__init__(self, *args, **kwargs)
        self.setTabBar(MainTabBar(self))
#        self.setHidden = self.tabBar().setHidden
        metrics = {}
        dpi = (self.logicalDpiX() + self.logicalDpiY()) / 2.
        ratio = 1. / 76 * dpi
        for s in (1, 2, 4, 8):
            metrics['{}px'.format(s)] = s * ratio

        self.setStyleSheet('''
                QTabBar::close-button {{
                    image: url(:/icons/Bigglesworth/32x32/window-close.svg);
                    border: {1px} solid transparent;
                }}
                QTabBar::close-button:disabled {{
                    image: url(:/icons/Bigglesworth/32x32/window-close-disabled.svg);
                }}
                QTabBar::close-button:hover {{
                    border: {1px} solid palette(mid);
                    border-radius: {2px};
                }}
                /* scroll buttons are too tall (at least on oxygen) when using stylesheets, 
                we need to override them anyway */
                QTabBar QToolButton {{
                    border: {1px} solid palette(mid);
                    border-radius: {4px};
                    margin: {8px} {1px};
                    background-color: palette(button);
                }}
                QTabBar QToolButton:hover {{
                    border-color: palette(dark);
                }}
                '''.format(**metrics))

        self.placeHolder = self.tabBar().placeHolder

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat('bigglesworth/WaveFileData') or \
            event.mimeData().hasFormat('bigglesworth/SampleItemSelection') or \
            event.mimeData().hasFormat('bigglesworth/WaveFilePath'):
                event.accept()
        else:
            QtWidgets.QTabWidget.dragEnterEvent(self, event)

    def dragMoveEvent(self, event):
        if event.pos() in self.tabBar().rect():
            tabBarPos = self.tabBar().mapFromParent(event.pos())
            tabIndex = self.tabBar().tabAt(tabBarPos)
            if event.mimeData().hasFormat('bigglesworth/WaveFilePath'):
                if not tabIndex:
                    event.ignore()
                    return
                byteArray = QtCore.QByteArray(event.mimeData().data('bigglesworth/WaveFilePath'))
                stream = QtCore.QDataStream(byteArray)
                window = stream.readQVariant()
                if window != self.window().uuid:
                    self.dropTabIndex = self.tabBar().setDropIndexAt(event.pos())
                    if self.dropTabIndex == self.count() or self.dropTabIndex <= 1:
                        self.placeHolder.hide()
                        event.ignore()
                        return
                    self.placeHolder.show()
                    self.dropTabIndex = tabIndex
                    event.accept()
                else:
                    self.placeHolder.hide()
                    event.ignore()
                return
            if event.mimeData().hasFormat('bigglesworth/SampleItemSelection') and \
                event.source().window() != self.window():
                    if tabIndex == 0:
                        self.setCurrentIndex(tabIndex)
                        event.accept()
                    else:
                        event.ignore()
                    return
            if tabIndex <= 1:
                self.setCurrentIndex(tabIndex)
                event.accept()
                return
            byteArray = QtCore.QByteArray(event.mimeData().data('bigglesworth/WaveFileData'))
            stream = QtCore.QDataStream(byteArray)
            window = stream.readQVariant()
            if window == self.window().uuid and stream.readInt() == tabIndex:
                self.setCurrentIndex(tabIndex)
        event.ignore()

    def dropEvent(self, event):
        self.placeHolder.hide()
        if event.mimeData().hasFormat('bigglesworth/WaveFilePath'):
            byteArray = QtCore.QByteArray(event.mimeData().data('bigglesworth/WaveFilePath'))
            stream = QtCore.QDataStream(byteArray)
            #ignore uuid
            stream.readQVariant()
            self.dropTabFileRequested.emit(stream.readQString(), self.dropTabIndex)
        QtWidgets.QTabWidget.dropEvent(self, event)

    def dragLeaveEvent(self, event):
        self.placeHolder.hide()
        QtWidgets.QTabWidget.dragLeaveEvent(self, event)


class SlotSpin(QtWidgets.QSpinBox):
    shown = False

    def setValue(self, value):
        QtWidgets.QSpinBox.setValue(self, value)
        if self.shown:
            self.checkWritable(value)

    def showEvent(self, event):
        if not self.shown:
            self.shown = True
            self.checkWritable(self.value())

    def checkWritable(self, value):
        if value not in self.window().writableSlots:
            self.lineEdit().setStyleSheet('color: red;')
            self.setToolTip('The selected slot has been set as read-only')
        else:
            self.lineEdit().setStyleSheet('')
            self.setToolTip('')

    def writableSlotsChanged(self):
        self.checkWritable(self.value())


class WaveIndexSpin(QtWidgets.QSpinBox):
    def setKeyFrames(self, keyFrames):
        self.keyFrames = keyFrames
        self.keyFrames.changed.connect(self.update)

    def stepBy(self, step):
        self.setValue(self.keyFrames.getClosestValidIndex(self.value() - 1, step) + 1)

    def stepEnabled(self):
        try:
            state = self.StepNone
            value = self.value()
            if value < 64:
                for item in self.keyFrames.fullList[value:]:
                    if item:
                        state |= self.StepUpEnabled
                        break
            if value > 1:
                state |= self.StepDownEnabled
            return state
        except:
            return QtWidgets.QSpinBox.stepEnabled(self)


class IndexSlider(QtWidgets.QSlider):
    validIndexes = [0]
    tickPositions = [0]

    def __init__(self, *args, **kwargs):
        QtWidgets.QSlider.__init__(self, *args, **kwargs)
        palette = self.palette()
        self.tickPen = QtGui.QPen(palette.color(palette.ButtonText).lighter(250))
        self.repeatTimer = QtCore.QTimer()
        self.repeatTimer.setSingleShot(True)
        self.repeatTimer.setInterval(250)
        self.repeatTimer.timeout.connect(self.setValueRepeat)
    
    def setKeyFrames(self, keyFrames):
        self.keyFrames = keyFrames
        self.keyFrames.changed.connect(self.updateIndexes)

    def updateIndexes(self):
        validIndexes = [i for i in range(64) if self.keyFrames.fullList[i]]
        if validIndexes != self.validIndexes:
            self.validIndexes = validIndexes
            if self.isVisible():
                self.updateTicks()

    def updateTicks(self):
        self.tickPositions = [self.ticksRatio * i for i in self.validIndexes]
        self.update()

    def mousePressEvent(self, event):
        pos = event.pos()
        option = QtWidgets.QStyleOptionSlider()
        self.initStyleOption(option)
        if self.style().hitTestComplexControl(QtWidgets.QStyle.CC_Slider, option, pos, self) == QtWidgets.QStyle.SC_SliderHandle:
            return QtWidgets.QSlider.mousePressEvent(self, event)
        target = QtWidgets.QStyle.sliderValueFromPosition(0, 63, pos.x() - self.ticksRect.x(), self.ticksRect.width())
        if target > self.value():
            self.targetDelta = 1
        else:
            self.targetDelta = -1
        newIndex = self.keyFrames.getClosestValidIndex(self.value(), self.targetDelta)
        if newIndex is not None:
            self.setValue(newIndex)
            self.repeatTimer.setInterval(250)
            self.repeatTimer.start()

    def mouseReleaseEvent(self, event):
        self.repeatTimer.stop()
        QtWidgets.QSlider.mouseReleaseEvent(self, event)

    def setValueRepeat(self):
        newIndex = self.keyFrames.getClosestValidIndex(self.value(), self.targetDelta)
        if newIndex is not None:
            self.setValue(newIndex)
            self.repeatTimer.setInterval(50)
            self.repeatTimer.start()

    def resizeEvent(self, event):
        option = QtWidgets.QStyleOptionSlider()
        self.initStyleOption(option)
        option.subControls |= QtWidgets.QStyle.SC_SliderTickmarks
        option.tickPosition |= self.TicksBothSides
        handleRect = self.style().subControlRect(QtWidgets.QStyle.CC_Slider, option, QtWidgets.QStyle.SC_SliderHandle, self)
        self.grooveRect = self.style().subControlRect(QtWidgets.QStyle.CC_Slider, option, QtWidgets.QStyle.SC_SliderGroove, self)
        ticksUpRect = QtCore.QRect(handleRect.width() / 2, 0, self.width() - handleRect.width() + 1, self.grooveRect.top())
        ticksDownRect = ticksUpRect.translated(0, self.grooveRect.bottom() - 1).adjusted(0, 0, 0, 2)
        self.ticksRect = ticksUpRect | ticksDownRect
        self.ticksRegion = QtGui.QRegion(ticksUpRect) | QtGui.QRegion(ticksDownRect)
        self.ticksRatio = (self.ticksRect.width() - 1) / 63.
        self.updateTicks()

    def paintEvent(self, event):
        if sys.platform == 'darwin':
            QtWidgets.QSlider.paintEvent(self, event)
        qp = QtGui.QPainter(self)
        qp.setRenderHints(qp.Antialiasing)
        qp.setClipRegion(self.ticksRegion)
        qp.translate(.5 + self.ticksRect.left(), .5)
        qp.setPen(self.tickPen)
        for x in self.tickPositions:
            qp.drawLine(x, 0, x, self.height() + 1)

        if sys.platform != 'darwin':
            QtWidgets.QSlider.paintEvent(self, event)


class CheckBoxDelegate(QtWidgets.QStyledItemDelegate):
    squarePenEnabled = QtGui.QColor(QtCore.Qt.darkGray)
    squarePenDisabled = QtGui.QColor(QtCore.Qt.lightGray)
    squarePen = squarePenEnabled
    selectPenEnabled = QtGui.QColor(QtCore.Qt.transparent)
    selectPenDisabled = QtGui.QColor(QtCore.Qt.darkGray)
    selectPen = selectPenEnabled
    selectBrushEnabled = QtGui.QColor(QtCore.Qt.black)
    selectBrushPartiallyEnabled = QtGui.QColor(QtCore.Qt.darkGray)
    selectBrushDisabled = QtGui.QColor(QtCore.Qt.gray)
    selectBrushPartiallyDisabled = QtGui.QColor(QtCore.Qt.lightGray)
    selectBrush = selectBrushEnabled
    selectBrushDict = {
        QtCore.Qt.ItemIsEnabled|QtCore.Qt.Checked: selectBrushEnabled, 
        QtCore.Qt.ItemIsEnabled|QtCore.Qt.PartiallyChecked: selectBrushPartiallyEnabled, 
        QtCore.Qt.Checked: selectBrushDisabled, 
        QtCore.Qt.PartiallyChecked: selectBrushPartiallyDisabled
    }

    _path = QtGui.QPainterPath()
    _path.moveTo(-3, 0)
    _path.lineTo(-1, 3)
    _path.lineTo(3, -3)
    _path.lineTo(-1, 1)
    _path.closeSubpath()

    def __init__(self, *args, **kwargs):
        if 'editable' in kwargs:
            self.editable = kwargs.pop('editable')
        else:
            self.editable = True
        if 'tristate' in kwargs:
            self.tristate = kwargs.pop('tristate')
        else:
            self.tristate = False
        if 'tinyNumber' in kwargs:
            self.tinyNumber = kwargs.pop('tinyNumber')
        else:
            self.tinyNumber = False
        QtWidgets.QStyledItemDelegate.__init__(self, *args, **kwargs)
        self.squareSize = QtWidgets.QApplication.fontMetrics().height()
        self.square = QtCore.QRectF(0, 0, self.squareSize, self.squareSize)
        scale = self.squareSize / 7.
        self.path = self._path.toFillPolygon(QtGui.QTransform().scale(scale, scale))
        self.readOnlyIcon = QtGui.QIcon.fromTheme('lock').pixmap(self.squareSize)
#        if self.readOnlyIcon.height() != self.squareSize:
#            self.readOnlyIcon = self.readOnlyIcon.scaledToHeight(self.squareSize, QtCore.Qt.SmoothTransformation)
        if self.tinyNumber:
            self.tinyFont = QtWidgets.QApplication.font()
            self.tinyFont.setPointSizeF(self.squareSize - 2)

    def paint(self, painter, style, index):
        QtWidgets.QStyledItemDelegate.paint(self, painter, style, QtCore.QModelIndex())
        enabled = index.flags() & QtCore.Qt.ItemIsEnabled
        if enabled:
            self.squarePen = self.squarePenEnabled
#            self.selectPen = self.selectPenEnabled
#            self.selectBrush = self.selectBrushEnabled
        else:
            self.squarePen = self.squarePenDisabled
#            self.selectPen = self.selectPenDisabled
#            self.selectBrush = self.selectBrushDisabled
        option = QtWidgets.QStyleOptionViewItem()
        option.__init__(style)
        self.initStyleOption(option, index)
        if option.fontMetrics.height() != self.squareSize:
            self.squareSize = option.fontMetrics.height()
            self.square = QtCore.QRect(0, 0, self.squareSize, self.squareSize)
            scale = self.squareSize / 7.
            self.path = self._path.toFillPolygon(QtGui.QTransform().scale(scale, scale))

        painter.setRenderHints(QtGui.QPainter.Antialiasing)
        painter.save()
        painter.translate(option.rect.x() + (option.rect.width() - self.squareSize) / 2, option.rect.y() + (option.rect.height() - self.squareSize) / 2)
        painter.save()
        if self.tinyNumber:
            painter.translate(0, -6)
        painter.setPen(self.squarePen)
        painter.drawRect(self.square)
        checked = index.data(QtCore.Qt.CheckStateRole)
        if checked > 0:
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(self.selectBrushDict[int(enabled|checked)])
            painter.translate(self.square.center())
            painter.drawPolygon(self.path)
        elif checked < 0:
            if checked == -2:
                painter.drawPixmap(self.square.toRect(), self.readOnlyIcon, self.readOnlyIcon.rect())
            else:
                painter.setPen(QtCore.Qt.red)
                painter.drawText(self.square, QtCore.Qt.AlignCenter, '?')
        painter.restore()
        if self.tinyNumber:
            painter.save()
            painter.translate(0, self.squareSize)
            painter.setFont(self.tinyFont)
            painter.setPen(QtCore.Qt.darkGray)
            painter.drawText(self.square, QtCore.Qt.AlignCenter, str(index.row() + 1))
            painter.restore()
        painter.restore()

    def setTriState(self, tristate):
        self.tristate = tristate

    def nextState(self, state):
        if self.tristate:
            state += 1
            if state > 2:
                state = 0
        else:
            state = bool(not state) * 2
        return state

    def editorEvent(self, event, model, option, index):
        if not self.editable or not index.flags() & QtCore.Qt.ItemIsEditable:
            return False
        if index.flags() & QtCore.Qt.ItemIsEnabled:
            if event.type() == QtCore.QEvent.MouseButtonPress and event.button() == QtCore.Qt.LeftButton:
                model.itemFromIndex(index).setData(self.nextState(index.data(QtCore.Qt.CheckStateRole)), QtCore.Qt.CheckStateRole)
                if self.parent():
                    selection = self.parent().selectionModel()
                    selection.setCurrentIndex(index, selection.NoUpdate)
            elif event.type() == QtCore.QEvent.KeyPress and event.key() in (QtCore.Qt.Key_Space, QtCore.Qt.Key_Enter):
                model.itemFromIndex(index).setData(self.nextState(index.data(QtCore.Qt.CheckStateRole)), QtCore.Qt.CheckStateRole)
        return True


class BlofeldWaveTable(QtWidgets.QTableView):
    dropRegion = None
    dropIntoPen = QtCore.Qt.blue
    dropIntoBrush = QtGui.QBrush(QtGui.QColor(32, 128, 255, 96))

    def copy(self, source, target):
        if len(source) != len(target):
            raise
#        print(source, target)
#        return
        model = self.model().sourceModel()
        waveTableModel = self.model().waveTableModel
        if source & target:
            return
        else:
            zeroIndex = waveTableModel.index(0, UidColumn)
            overwrite = []
            orphans = []
            edited = {}
            for row in sorted(target):
                index = model.index(row, UidColumn)
                uid = index.data()
                if uid:
                    overwrite.append(index)
                    found = waveTableModel.match(zeroIndex, QtCore.Qt.DisplayRole, uid, flags=QtCore.Qt.MatchExactly)
                    if not found:
                        orphans.append(index)
                    else:
                        valid = self.model().checkValidity(self.model().mapFromSource(index), uid)
                        if valid != QtCore.Qt.Checked:
                            edited[index] = found[0]
            if overwrite:
#                print(overwrite, orphans, edited)
                text = '''<head><style>
                    table {
                        border-style: solid; 
                        border-width: 1px; 
                        border-color: darkGray; 
                    }
                    </style></head><body>
                    Do you want to overwrite the following wavetables?<br/><br/>
                    <table cellspacing=1 cellpadding=4 width=80%>
                        <tr><th width=10%>Slot</th><th width=30%>Name</th><th width=60%>Notes</th></tr>
                '''
                for index in overwrite:
                    text += '<tr><td align=center>{}</td><td>{}</td>'.format(
                        index.sibling(index.row(), SlotColumn).data(), index.sibling(index.row(), NameColumn).data())
                    if index in orphans:
                        text += '<td>Not saved locally</td>'
                    elif index in edited:
                        text += '<td>Not updated</td>'
                    text += '</tr>'
                text += '</table>'
                if orphans:
                    text += '<br/><br/>NOTE: you can restore "orphaned" tables (those marked as ' \
                        '<i>Not saved locally</i>) by pressing "Restore and proceed".'
                text += '</body>'
                msgBox = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Question, 'Wavetable overwrite', 
                    text, QtWidgets.QMessageBox.Ok|QtWidgets.QMessageBox.Cancel, parent=self)
                if orphans:
                    restoreBtn = msgBox.addButton('Restore and proceed', QtWidgets.QMessageBox.ActionRole)
                    restoreBtn.setIcon(QtGui.QIcon.fromTheme('document-save'))
                else:
                    restoreBtn = False
                res = msgBox.exec_()
                if msgBox.clickedButton() == restoreBtn:
                    for index in orphans:
                        self.window().copyFromDumpUid(index.data(), True)
                elif res != QtWidgets.QMessageBox.Ok:
                    return

            else:
                if not AdvancedMessageBox(self, 'Copy wavetables', 
                    'Do you want to create {} new wavetable{}?'.format(len(source), 's' if len(source) > 1 else ''), 
                    buttons=AdvancedMessageBox.Ok|AdvancedMessageBox.Cancel, 
                    icon=AdvancedMessageBox.Question).exec_() == AdvancedMessageBox.Ok:
                        return

            for sourceRow, targetRow in zip(source, target):
                uid = str(uuid4())
                model.setData(model.index(targetRow, UidColumn), uid)
                model.setData(model.index(targetRow, NameColumn), model.index(sourceRow, NameColumn).data())
                model.setData(model.index(targetRow, EditedColumn), QtCore.QDateTime.currentMSecsSinceEpoch())
                model.setData(model.index(targetRow, DataColumn), model.index(sourceRow, DataColumn).data())
                model.setData(model.index(targetRow, PreviewColumn), model.index(sourceRow, PreviewColumn).data())
                model.setData(model.index(targetRow, DumpedColumn), 0)
                self.window().copyFromDumpUid(uid, True)
#        else:
#            print('minghiaputtanazza')
        model.submitAll()

    def dragEnterEvent(self, event):
        self.targetRows = None
        self.sourceRows = None
        if event.source() == self:
            event.accept()

    def dragLeaveEvent(self, event):
        self.dropRegion = None
        self.viewport().update()

    def dragMoveEvent(self, event):
        QtWidgets.QTableView.dragMoveEvent(self, event)
        if not event.mimeData().hasFormat('application/x-qabstractitemmodeldatalist'):
            return
        byteArray = event.mimeData().data('application/x-qabstractitemmodeldatalist')
        stream = QtCore.QDataStream(byteArray, QtCore.QIODevice.ReadOnly)
        rows = set()
        while not stream.atEnd():
            row = stream.readInt32()
            rows.add(row)
            #column is ignored
            stream.readInt32()
            roleItems = stream.readInt32()
            for i in range(roleItems):
                #role
                stream.readInt32()
                #value
                stream.readQVariant()
        model = self.model()
        sourceModel = model.sourceModel()
        dropIndex = model.mapToSource(self.indexAt(event.pos()))
        startRow = max(80, dropIndex.row())
        if len(rows) > 1:
            startRow = min(startRow, 119 - len(rows))
        emptyRows = []
        existing = set()
        for r in range(80, 119):
            uid = sourceModel.index(r, UidColumn).data()
            if uid:
                existing.add(r)
            else:
                emptyRows.append(r)
#        emptyRows = [r for r in range(self.model().rowCount()) if not self.model().index(r, UidColumn).data()]
        if not event.keyboardModifiers() == QtCore.Qt.ControlModifier:
            if len(emptyRows) < len(rows):
                return event.ignore()
            targetRows = set()
            current = startRow
            delta = 1
            while len(targetRows) < len(rows):
                if current in emptyRows and current not in targetRows:
                    targetRows.add(current)
                current += delta
                if current >= 119:
                    delta = -1
                    current = startRow - 1
                elif current <= 80:
                    delta = 1
        else:
            targetRows = set(r for r in range(startRow, startRow + len(rows)))

        columns = [c for c in range(model.columnCount()) if not self.isColumnHidden(c)]
        self.dropRegion = QtGui.QPainterPath()
        for row in targetRows:
            rect = QtCore.QRect()
            for column in columns:
                rect |= self.visualRect(model.mapFromSource(dropIndex.sibling(row, column)))
            path = QtGui.QPainterPath()
            path.addRect(QtCore.QRectF(rect))
            self.dropRegion |= path
        if event.keyboardModifiers() == QtCore.Qt.ControlModifier and targetRows & rows:
            event.ignore()
        else:
            event.accept()
        if self.indexAt(event.pos()).row() not in targetRows:
            if self.indexAt(QtCore.QPoint(0, 0)).row() > min(targetRows):
                self.scrollTo(model.mapFromSource(sourceModel.index(min(targetRows), NameColumn)))
            elif self.indexAt(self.viewport().rect().bottomLeft()).row() < max(targetRows):
                self.scrollTo(model.mapFromSource(sourceModel.index(max(targetRows), NameColumn)))
        self.targetRows = targetRows
        self.sourceRows = rows

    def dropEvent(self, event):
        self.dropRegion = None
        self.viewport().update()
        if self.targetRows:
            QtCore.QTimer.singleShot(0, lambda: self.copy(self.sourceRows, self.targetRows))

    def paintEvent(self, event):
        QtWidgets.QTableView.paintEvent(self, event)
        if self.dropRegion:
            qp = QtGui.QPainter(self.viewport())
            qp.setPen(self.dropIntoPen)
            qp.setBrush(self.dropIntoBrush)
            qp.drawPath(self.dropRegion)


class WaveTableDock(QtWidgets.QDockWidget):
    visible = False
    resizing = False
    floatingWidth = None
    dockedWidth = None

    def __init__(self, *args, **kwargs):
        QtWidgets.QDockWidget.__init__(self, *args, **kwargs)
        self.topLevelChanged.connect(self.setState)
        self.settings = QtCore.QSettings()
        if sys.platform == 'darwin':
            self.setFeatures((self.features()|self.DockWidgetFloatable) ^ self.DockWidgetFloatable)

    @property
    def localWaveTableList(self):
        return self.parent().localWaveTableList

    def changeEvent(self, event):
        if event.type() == QtCore.QEvent.ActivationChange:
            self.parent().checkActivation()
        return QtWidgets.QDockWidget.changeEvent(self, event)

    def setState(self, state):
        if state:
            self.visible = True
            if self.floatingWidth is None:
                headerWidth = sum([self.localWaveTableList.columnWidth(c) for c in range(self.localWaveTableList.model().columnCount()) if not self.localWaveTableList.isColumnHidden(c)])
                self.floatingWidth = self.width() - self.localWaveTableList.width() + headerWidth + 4
            self.resizing = True
            self.resize(self.floatingWidth, self.height())
            self.resizing = False
        else:
            try:
                self.resizing = True
                self.resize(self.dockedWidth, self.height())
            except:
                return
            finally:
                self.resizing = False
        self.saveSettings()

    def saveSettings(self, visible=None):
        if visible is None:
            visible = self.isVisible()
        self.settings.beginGroup('WaveTables')
        self.settings.setValue('Dock', [visible, self.isFloating(), self.dockedWidth, self.floatingWidth, self.geometry()])
        self.settings.endGroup()

    def showEvent(self, event):
        self.visible = True
        self.saveSettings()

    def closeEvent(self, event):
        self.visible = False
        self.saveSettings(False)

    def resizeEvent(self, event):
        if self.isFloating():
            if not self.resizing:
                self.floatingWidth = self.width()
        elif not self.resizing:
            self.dockedWidth = self.width()
        self.saveSettings()
