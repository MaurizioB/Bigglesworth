import os
os.environ['QT_PREFERRED_BINDING'] = 'PyQt4'

from threading import Lock
from random import randrange
from math import cos, sin, radians

from Qt import QtCore, QtGui, QtWidgets

from metawidget import BaseWidget
from dial import _Dial
from combo import _Combo
try:
    from bigglesworth.parameters import Parameters
except:
    pass

In, Out = 0, 1
Left, Top, Right, Bottom = 1, 2, 4, 8

QtCore.pyqtSignal = QtCore.Signal
def setItalic(item, italic=True):
    font = item.font()
    font.setBold(italic)
    item.setFont(font)

fullRangeCenterZero = tuple(['{:+}'.format(n) for n in range(-64, 64)])

modOperator = ('+', '-', '*', 'AND', 'OR', 'XOR', 'MAX', 'min')
modSource = ('off', 'LFO 1', 'LFO1*MW', 'LFO 2', 'LFO2*Press', 'LFO 3', 'FilterEnv', 'AmpEnv', 'Env3', 'Env4', 'Keytrack',
    'Velocity', 'Rel. Velo', 'Pressure', 'Poly Press', 'Pitch Bend', 'Mod Wheel', 'Sustain', 'Foot Ctrl', 'BreathCtrl',
    'Control W', 'Control X', 'Control Y', 'Control Z', 'Unisono V.', 'Modifier 1', 'Modifier 2', 'Modifier 3', 'Modifier 4',
    'minimum', 'MAXIMUM')
modDest = ('Pitch', 'O1 Pitch', 'O1 FM', 'O1 PW/Wave', 'O2 Pitch', 'O2 FM', 'O2 PW/Wave', 'O3 Pitch', 'O3 FM', 'O3 PW',
    'O1 Level', 'O1 Balance', 'O2 Level', 'O2 Balance', 'O3 Level', 'O3 Balance', 'RMod Level', 'RMod Bal.',
    'NoiseLevel', 'Noise Bal.', 'F1 Cutoff', 'F1 Reson.', 'F1 FM', 'F1 Drive', 'F1 Pan',
    'F2 Cutoff', 'F2 Reson.', 'F2 FM', 'F2 Drive', 'F2 Pan',
    'Volume', 'LFO1Speed', 'LFO2Speed', 'LFO3Speed', 'FE Attack', 'FE Decay', 'FE Sustain', 'FE Release',
    'AE Attack', 'AE Decay', 'AE Sustain', 'AE Release', 'E3 Attack', 'E3 Decay', 'E3 Sustain', 'E3 Release',
    'E4 Attack', 'E4 Decay', 'E4 Sustain', 'E4 Release', 'M1 Amount', 'M2 Amount', 'M3 Amount', 'M4 Amount')

modSourceGroups = {
    'Keyboard': range(10, 20), 
    'Envelopes': (6, 7, 8, 9), 
    'Other': range(1, 6) + range(20, 31)
    }

modDestGroups = {
    'OSC': range(1, 10), 
    'Mixer': range(10, 20), 
    'Filters': range(20, 30), 
    'LFO': range(31, 34), 
    'Envelopes': range(34, 50), 
    'Modifiers': range(50, 54)
    }

modColors = [
    QtGui.QColor(0, 0, 0), 
    QtGui.QColor(216, 216, 0), 
    QtGui.QColor(128, 0, 0), 
    QtGui.QColor(64, 192, 128), 
    QtGui.QColor(255, 0, 255), 
    QtGui.QColor(128, 128, 0), 
    QtGui.QColor(0, 0, 128), 
    QtGui.QColor(0, 255, 255), 
    QtGui.QColor(192, 64, 128), 
    QtGui.QColor(255, 0, 0), 
    QtGui.QColor(0, 128, 0), 
    QtGui.QColor(0, 0, 255), 
    QtGui.QColor(128, 128, 255), 
    QtGui.QColor(128, 0, 128), 
    QtGui.QColor(0, 128, 128), 
    QtGui.QColor(0, 255, 0), 
]


class BaseModParamObject(QtCore.QObject):
    valueChanged = QtCore.pyqtSignal(int)
    def __init__(self, main, id, paramId, baseValue=None):
        QtCore.QObject.__init__(self, main)
        self.main = main
        self.id = id
        self.paramId = paramId
        self.value = baseValue if baseValue is not None else Parameters.parameterData[self.paramDelta + id * 3 + paramId].default
        self.setRange = self.setValueList = lambda *args: None
        self.setObjectName(self.baseName.format(id + 1, self.attrList[paramId]))


class ModulationObject(BaseModParamObject):
    paramDelta = 261
    baseName = 'modulation{}{}'
    attrList = ('Source', 'Destination', 'Amount')
    def __init__(self, main, modId, paramId, baseValue=None):
        BaseModParamObject.__init__(self, main, modId, paramId, baseValue=None)
        self.main = main
        self.modId = modId
        self.paramId = paramId
        self.value = baseValue
        if paramId == 0:
            self.setter = self.main.checkSource
        elif paramId == 1:
            self.setter = self.main.checkTarget
        else:
            self.setter = self.main.checkAmount

    def setValue(self, value):
        values = [-1, -1, -1]
        values[self.paramId] = value
        self.setter(self.modId, value)
        self.main.modTable.modulationChanged(self.modId, *values)


class ModifierObject(BaseModParamObject):
    paramDelta = 245
    baseName = 'modifier{}{}'
    attrList = ('SourceA', 'SourceB', 'Operation', 'Constant')
    def __init__(self, main, id, paramId, widget, baseValue=None):
        BaseModParamObject.__init__(self, main, id, paramId, baseValue=None)
        self.main = main
        self.id = id
        self.paramId = paramId
#        if paramId == 0:
#            self.setValue = lambda value: self.main.setModifierSourceA(id, value)
#        elif paramId == 1:
#            self.setValue = lambda value: self.main.setModifierSourceB(id, value)
#        elif paramId == 2:
#            self.setValue = lambda value: self.main.setModifierOperator(id, value)
#        else:
#            self.setValue = lambda value: self.main.setModifierConstant(id, value)
        self.widget = widget
        self.widget.currentIndexChanged.connect(self.valueChanged)

    def setValue(self, value):
        self.widget.blockSignals(True)
        self.widget.setValue(value)
        self.widget.blockSignals(False)

class VerticalHeader(QtWidgets.QHeaderView):
#    sectionHighlight = QtCore.pyqtSignal(int)
    switchRequest = QtCore.pyqtSignal(int, int)
    def __init__(self, *args, **kwargs):
        QtWidgets.QHeaderView.__init__(self, *args, **kwargs)
        self.setMouseTracking(True)
#        self.hoverIndex = -1

#    def mouseMoveEvent(self, event):
#        index = self.logicalIndexAt(event.pos())
#        if index != self.hoverIndex:
#            self.sectionHighlight.emit(index)
#        self.hoverIndex = index
#        QtWidgets.QHeaderView.mouseMoveEvent(self, event)

#    def leaveEvent(self, event):
#        self.hoverIndex = -1
#        self.sectionHighlight.emit(-1)
#        QtWidgets.QHeaderView.leaveEvent(self, event)

    def contextMenuEvent(self, event):
        modulations = self.parent().modulations
        menu = QtWidgets.QMenu()
        current = self.logicalIndexAt(event.pos())
        for i in range(16):
            pm = QtGui.QPixmap(16, 16)
            pm.fill(modColors[i])
            switchAction = menu.addAction('')
            switchAction.setIcon(QtGui.QIcon(pm))
            switchAction.triggered.connect(lambda _, dest=i: self.switchRequest.emit(current, dest))
            if i == current:
                switchAction.setEnabled(False)
            text = 'Switch with {}'.format(i + 1)
            if modulations[i] is None:
                text += ' (off)'
                setItalic(switchAction)
            switchAction.setText(text)
        menu.exec_(QtGui.QCursor.pos())


class AmountSpinBox(QtWidgets.QSpinBox):
    regexp = QtGui.QRegExpValidator(QtCore.QRegExp(r'^[+|-]{0,1}\d+$'))

    def __init__(self):
        QtWidgets.QSpinBox.__init__(self)
        self.setRange(0, 127)
        self.valueChanged.connect(self.update)
        self.setStyleSheet('''
        QSpinBox::up-button, QSpinBox::down-button {
            border: none;
            width: 10px;
        }
        QSpinBox::down-arrow, QSpinBox::up-arrow {
            width: 0px;
            height: 0px;
            border-left: 3px solid palette(base);
            border-right: 3px solid palette(base);
        }
        QSpinBox::up-arrow {
            border-top: none;
            border-bottom: 3px solid black;
        }
        QSpinBox::up-arrow:disabled {
            border-bottom: 3px solid palette(mid);
        }
        QSpinBox::down-arrow {
            border-top: 3px solid black;
            border-bottom: none;
        }
        QSpinBox::down-arrow:disabled {
            border-top: 3px solid palette(mid);
        }
        QSpinBox::up-arrow:pressed, QSpinBox::down-arrow:pressed {
            left: 1px;
        }
        ''')

    def textFromValue(self, value):
        return fullRangeCenterZero[value]

    def validate(self, text, pos):
        return self.regexp.validate(text, pos)

    def valueFromText(self, text):
        if text[0].isdigit():
            text = '+' + text
        try:
            return fullRangeCenterZero.index(text)
        except Exception as e:
            print(e)
            return self.value()


class ModTable(QtWidgets.QTableWidget):
#    sectionHighlight = QtCore.pyqtSignal(int)
    modSourceChanged = QtCore.pyqtSignal(int, int)
    modAmountChanged = QtCore.pyqtSignal(int, int)
    modDestinationChanged = QtCore.pyqtSignal(int, int)

    def __init__(self):
        QtWidgets.QTableWidget.__init__(self, 16, 3)
        self.setHorizontalHeaderLabels(['Source', 'Amount', 'Destination'])
        self.setHorizontalScrollMode(self.ScrollPerPixel)
        self.setVerticalHeader(VerticalHeader(QtCore.Qt.Vertical))
#        self.verticalHeader().sectionHighlight.connect(self.sectionHighlight)
        #workaround for content not scrolled, see https://bugreports.qt.io/browse/QTBUG-12253
        self.verticalScrollBar().valueChanged.connect(lambda v: self.model().layoutChanged.emit())
        #we need to manually set the vertical labels to allow correct color settings
        self.setVerticalHeaderLabels([str(x) for x in range(1, 17)])

        palette = self.palette()
        for row in range(16):
            self.model().setHeaderData(row, QtCore.Qt.Vertical, QtGui.QColor(modColors[row]), QtCore.Qt.BackgroundRole)
            self.model().setHeaderData(row, QtCore.Qt.Vertical, QtGui.QColor(QtCore.Qt.white), QtCore.Qt.ForegroundRole)

            sourceCombo = _Combo(self)
            sourceCombo.setValue = sourceCombo.setCurrentIndex
            sourceCombo.value = sourceCombo.currentIndex
            sourceCombo.addItems(modSource)
            sourceCombo.currentIndexChanged.connect(lambda idx, m=row: self.modSourceChanged.emit(m, idx))
            sourceCombo.currentIndexChanged.connect(lambda idx, m=row: self.checkSource(m, idx))
            self.setCellWidget(row, 0, sourceCombo)

            spin = AmountSpinBox()
            spin.setEnabled(False)
            spin.valueChanged.connect(lambda v, m=row: self.modAmountChanged.emit(m, v))
            self.setCellWidget(row, 1, spin)

            destCombo = _Combo(self)
            destCombo.setEnabled(False)
            destCombo.setValue = destCombo.setCurrentIndex
            destCombo.value = destCombo.currentIndex
            destCombo.addItems(modDest)
            destCombo.setCurrentIndex(-1)
            destCombo.currentIndexChanged.connect(lambda idx, m=row: self.modDestinationChanged.emit(m, idx))
            self.setCellWidget(row, 2, destCombo)

            sourceCombo.setPalette(palette)
            spin.setPalette(palette)
            destCombo.setPalette(palette)

        self.resizeRowsToContents()
        self.resizeColumnsToContents()
        self.horizontalHeader().setResizeMode(self.horizontalHeader().Stretch)
        self.horizontalHeader().setHighlightSections(False)
        self.verticalHeader().setDefaultSectionSize(self.fontMetrics().height() * 1.5)
        self.verticalHeader().setResizeMode(self.verticalHeader().Fixed)
#        self.setSelectionBehavior(self.SelectRows)

        self.setStyleSheet('''
            _Combo, QSpinBox {
                border-top: 1px solid palette(light);
                border-right: 1px solid palette(dark);
                border-bottom: 1px solid palette(dark);
                border-left: 1px solid palette(light);
                border-radius: 2px;
            }
            ''')

    def checkSource(self, modId, value):
        state = True if value else False
        self.cellWidget(modId, 1).setEnabled(state)
        self.cellWidget(modId, 2).setEnabled(state)

    def modulationChanged(self, modId, sourceId, targetId, amount):
        for col, value in enumerate((sourceId, amount, targetId)):
            widget = self.cellWidget(modId, col)
            widget.blockSignals(True)
            if value >= 0:
                widget.setValue(value)
            if col > 0:
                widget.setEnabled(True if sourceId else False)
            widget.blockSignals(False)
        self.scrollTo(self.model().index(modId, 0))
        self.repaint()

    def amountChanged(self, mod, amount):
        self.cellWidget(mod, 1).setValue(amount)


class BaseDialog(QtWidgets.QDialog):
    def __init__(self, main):
        QtWidgets.QDialog.__init__(self)
        self.main = main
        self.storedSize = None
        self.minimized = False
        layout = QtWidgets.QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

    def showEvent(self, event):
        self.storedSize = self.size()

    def toggleShade(self):
        if self.minimized:
            self.setMinimumHeight(50)
            self.resize(self.storedSize)
        else:
            self.setMinimumHeight(0)
            self.storedSize = self.size()
            self.resize(self.width(), 0)
        self.minimized = not self.minimized


class ModifiersDialog(BaseDialog):
    shown = False
    sourceAChanged = QtCore.pyqtSignal(int, int)
    sourceBChanged = QtCore.pyqtSignal(int, int)
    operatorChanged = QtCore.pyqtSignal(int, int)
    constantChanged = QtCore.pyqtSignal(int, int)

    def __init__(self, main):
        BaseDialog.__init__(self, main)
        self.setWindowTitle('Modifiers')
        layout = self.layout()

        for col, label in enumerate(('Source A', 'Oper.', 'Source B', 'Const.'), 1):
            lbl = QtWidgets.QLabel(label)
            lbl.setAlignment(QtCore.Qt.AlignCenter)
            layout.addWidget(lbl, 0, col)

        self.modifiers = []
        palette = self.palette()
        modSourceBItems = ['Constant'] + list(modSource[1:])
        maxSizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Preferred)
        for row in range(1, 5):
            layout.addWidget(QtWidgets.QLabel('Mod. {}'.format(row)))
            sourceACombo = _Combo(self)
            sourceACombo.addItems(modSource)
            sourceACombo.setValue = sourceACombo.setCurrentIndex
            sourceACombo.value = sourceACombo.currentIndex
            sourceACombo.currentIndexChanged.connect(lambda idx, m=row: self.sourceAChanged.emit(m, idx))
            layout.addWidget(sourceACombo, row, 1)

            operatorCombo = _Combo(self)
            operatorCombo.addItems(modOperator)
            operatorCombo.setSizePolicy(maxSizePolicy)
            operatorCombo.setValue = operatorCombo.setCurrentIndex
            operatorCombo.value = operatorCombo.currentIndex
            operatorCombo.currentIndexChanged.connect(lambda idx, m=row: self.operatorChanged.emit(m, idx))
            layout.addWidget(operatorCombo, row, 2)

            sourceBCombo = _Combo(self)
            sourceBCombo.addItems(modSourceBItems)
            sourceBCombo.value = sourceBCombo.currentIndex
            sourceBCombo.currentIndexChanged.connect(lambda idx, m=row: self.sourceBChanged.emit(m, idx))
            layout.addWidget(sourceBCombo, row, 3)

            constantCombo = _Combo(self)
            constantCombo.setEnabled(False)
            constantCombo.addItems(fullRangeCenterZero)
            constantCombo.setValue = constantCombo.setCurrentIndex
            constantCombo.value = constantCombo.currentIndex
            constantCombo.currentIndexChanged.connect(lambda idx, m=row: self.constantChanged.emit(m, idx))
            layout.addWidget(constantCombo, row, 4)

            sourceBCombo.setValue = lambda idx, src=sourceBCombo, const=constantCombo: [
                src.setCurrentIndex(idx), const.setDisabled(idx)]
            sourceBCombo.currentIndexChanged.connect(lambda idx, combo=constantCombo: combo.setDisabled(idx))

            sourceACombo.setPalette(palette)
            operatorCombo.setPalette(palette)
            sourceBCombo.setPalette(palette)
            constantCombo.setPalette(palette)

            self.modifiers.append((sourceACombo, sourceBCombo, operatorCombo, constantCombo))

    def showEvent(self, event):
        if not self.shown:
            self.shown = True
            self.setFixedSize(self.size())


class ModTableDialog(BaseDialog):
    def __init__(self, main):
        BaseDialog.__init__(self, main)
        self.setWindowTitle('Modulations')
        self.modTable = ModTable()
        self.layout().addWidget(self.modTable)

        self.setMinimumWidth(256)
        self.setMaximumWidth(480)
        self.setMinimumHeight(80)
        self.setMaximumHeight(self.modTable.verticalHeader().defaultSectionSize() * 18)


class BaseDialogProxy(QtWidgets.QGraphicsProxyWidget):
    minimizeColors = QtGui.QColor(QtCore.Qt.lightGray), QtGui.QColor(QtCore.Qt.darkGray)

    def __init__(self):
        QtWidgets.QGraphicsProxyWidget.__init__(
            self, 
            flags=QtCore.Qt.Dialog|QtCore.Qt.CustomizeWindowHint|QtCore.Qt.WindowTitleHint|QtCore.Qt.WindowShadeButtonHint
            )
        self.siblings = []
        self.geometryChanged.connect(self.checkPos)
        self.minimizeColor = self.minimizeColors[0]
        self.shown = False

    def setShadow(self, shadow):
        if shadow:
            shadow = QtWidgets.QGraphicsDropShadowEffect()
            shadow.setBlurRadius(5)
            shadow.setOffset(2, 2)
        else:
            shadow = None
        self.setGraphicsEffect(shadow)

    def showEvent(self, event):
        if not self.shown:
            self.shown = True
            self.dialog.toggleShade()

    def mouseDoubleClickEvent(self, event):
        left, top, right, bottom = self.getWindowFrameMargins()
        if not event.scenePos() in self.geometry().adjusted(-left, 0, right, bottom) and event.scenePos() not in self.minimizeRect:
            self.dialog.toggleShade()
        else:
            QtWidgets.QGraphicsProxyWidget.mouseDoubleClickEvent(self, event)

    def hoverMoveEvent(self, event):
        hoverMinimize = event.pos() in self.minimizeRect
        if hoverMinimize:
            QtWidgets.QToolTip.showText(QtGui.QCursor.pos(), 'Minimize/expand window')
        else:
            QtWidgets.QToolTip.showText(QtCore.QPoint(), '')
        self.minimizeColor = self.minimizeColors[hoverMinimize]
        QtWidgets.QGraphicsProxyWidget.hoverMoveEvent(self, event)
        self.update(self.minimizeRect)

    def hoverLeaveEvent(self, event):
        self.minimizeColor = self.minimizeColors[0]
        QtWidgets.QGraphicsProxyWidget.hoverLeaveEvent(self, event)
        self.update(self.minimizeRect)

    def wheelEvent(self, event):
        QtWidgets.QGraphicsProxyWidget.wheelEvent(self, event)
        if not self.dialog.minimized:
            self.dialog.repaint()
#            self.update(self.boundingRect())

    def checkPos(self):
        if not self.scene():
            return
        self.geometryChanged.disconnect(self.checkPos)
        left, top, right, bottom = self.getWindowFrameMargins()
        b = self.sceneBoundingRect()
        for s in self.siblings:
            sRect = s.sceneBoundingRect()
            if not b.intersects(sRect.adjusted(-5, -5, 5, 5)):
                continue
            sRight = sRect.right() + right
            if sRight - 15 <= b.left() - left <= sRight + 10:
                self.setX(sRight)
            elif sRight - 15 <= b.right() - right <= sRight + 10:
                self.setX(sRight - b.width())

            sLeft = sRect.left()
            if sLeft - 15 <= b.left() - left <= sLeft + 10:
                self.setX(sLeft + left)
            elif sLeft - 15 <= b.right() + right <= sLeft + 10:
                self.setX(sLeft - b.width() + right)

            sBottom = sRect.bottom() + bottom
            if sBottom - 15 <= b.top() <= sBottom + 10:
                self.setY(sBottom + top - bottom)
            elif sBottom - 15 <= b.bottom() <= sBottom + 10:
                self.setY(sBottom - b.height() + top - bottom)

            sTop = sRect.top()
            if sTop - 15 <= b.top() <= sTop + 10:
                self.setY(sTop + top)
            elif sTop - 15 <= b.bottom() <= sTop + 10:
                self.setY(sTop - b.height() + top)

        sceneRect = self.scene().sceneRect()
        if b.x() < 10:
            self.setX(left)
        elif b.right() > sceneRect.right() - right - 10:
            self.setX(sceneRect.right() - b.width())
        if b.y() < 10:
            self.setY(top)
        elif b.bottom() > sceneRect.bottom() - bottom - 10:
            self.setY(sceneRect.bottom() - b.height() + top)

        self.geometryChanged.connect(self.checkPos)

    def event(self, event):
        if event.type() == QtCore.QEvent.GraphicsSceneMousePress and \
            event.button() == QtCore.Qt.LeftButton and event.pos() in self.minimizeRect:
                self.dialog.toggleShade()
                return True
        return QtWidgets.QGraphicsProxyWidget.event(self, event)

    def paint(self, qp, option, widget):
        QtWidgets.QGraphicsProxyWidget.paint(self, qp, option, widget)
        qp.save()
        qp.setPen(QtCore.Qt.darkGray)
        qp.translate(.5, .5)
        qp.drawRoundedRect(self.minimizeRect, 2, 2)
        qp.setBrush(self.minimizeColor)
        if self.dialog.minimized:
            qp.drawRect(self.minimizeRect.adjusted(2, 2, -2, -2))
            #draw fill rect to avoid background widgets drawing
#            qp.setBrush(widget.palette().color(QtGui.QPalette.Window))
            qp.setBrush(QtWidgets.QApplication.palette().color(QtGui.QPalette.Active, QtGui.QPalette.Window))
            qp.setPen(QtCore.Qt.NoPen)
            qp.drawRect(self.dialog.rect().adjusted(-1, -2, 1, 1))
        else:
            qp.drawRect(self.minimizeRect.adjusted(2, 2, -2, - self.minimizeRect.height() + 6))
        qp.setPen(QtCore.Qt.darkGray)
        qp.setBrush(QtCore.Qt.NoBrush)
        qp.drawRoundedRect(self.boundingRect(), 2, 2)
        qp.restore()

    def windowFrameSectionAt(self, pos):
        section = QtWidgets.QGraphicsProxyWidget.windowFrameSectionAt(self, pos)
        if self.dialog.minimized and section:
            return QtCore.Qt.TitleBarArea
        return section

    def resizeEvent(self, event):
        QtWidgets.QGraphicsProxyWidget.resizeEvent(self, event)
        r = QtCore.QRectF(self.boundingRect())
        r.setBottom(0)
        r.setLeft(r.right() - r.height())
        r.adjust(4, 4, -4, -4)
        self.minimizeRect = r


class ModifiersDialogProxy(BaseDialogProxy):
    def __init__(self, main):
        BaseDialogProxy.__init__(self)
        self.dialog = ModifiersDialog(main)
        self.setWidget(self.dialog)


class ModTableDialogProxy(BaseDialogProxy):
    sectionHighlight = QtCore.pyqtSignal(int)

    def __init__(self, main):
        BaseDialogProxy.__init__(self)
        self.setAcceptHoverEvents(True)
        self.dialog = ModTableDialog(main)
        self.setWidget(self.dialog)
        self.modTable = self.dialog.modTable

    def hoverMoveEvent(self, event):
        BaseDialogProxy.hoverMoveEvent(self, event)
        #embedded views doesn't seem to correctly receive all mouse events, so we manually check
        #hover position to get something like QHeaderView.sectionEntered and QTable*.entered signals
        point = event.pos().toPoint()
        if point in self.modTable.viewport().geometry():
            point = self.modTable.viewport().mapFrom(self.widget(), point)
            index = self.modTable.indexAt(point)
            self.sectionHighlight.emit(index.row())
        elif point in self.modTable.verticalHeader().geometry():
            point = self.modTable.viewport().mapFrom(self.widget(), point)
            self.sectionHighlight.emit(self.modTable.verticalHeader().logicalIndexAt(point))
        else:
            self.sectionHighlight.emit(-1)

    def hoverLeaveEvent(self, event):
        BaseDialogProxy.hoverLeaveEvent(self, event)
        self.sectionHighlight.emit(-1)


class MenuIcon(QtWidgets.QLabel):
    shown = False

    def showEvent(self, event):
        if not self.shown:
            self.shown = True
            self.repaint()

    def repaint(self):
        height = self.height()
        pm = QtGui.QPixmap(height, height)
        pm.fill(QtCore.Qt.transparent)
        qp = QtGui.QPainter(pm)
        rectHeight = height / 7.
        qp.translate(.5, rectHeight + .5)
        qp.setPen(QtCore.Qt.NoPen)
        qp.setBrush(QtCore.Qt.black)
        for p in range(3):
            qp.drawRect(2, 0, height - 4, rectHeight)
            qp.translate(0, rectHeight * 2)
        qp.end()
        self.setPixmap(pm)

#    def resizeEvent(self, event):
#        self.repaint()


class Panel(QtWidgets.QWidget):
    playIcons = QtGui.QIcon.fromTheme('media-playback-pause'), QtGui.QIcon.fromTheme('media-playback-start')
    def __init__(self, proxy):
        QtWidgets.QWidget.__init__(self)
#        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Preferred))
        self.setContentsMargins(0, 0, 0, 0)
        self.setMinimumWidth(20)
        self.shown = False

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        self.setLayout(layout)

        self.labelIcon = MenuIcon()
        self.labelIcon.setVisible(False)
        layout.addWidget(self.labelIcon)

        self.playBtn = QtWidgets.QPushButton(self.playIcons[1], 'Animate')
        self.playBtn.setToolTip('Start/stop animations')
        self.playBtn.setFocusPolicy(QtCore.Qt.NoFocus)
        self.playBtn.setCheckable(True)
        self.playBtn.setChecked(True)
#        self.playBtn.setMaximumSize(24, 24)
        self.playBtn.toggled.connect(self.playToggled)
        layout.addWidget(self.playBtn)

        self.focusBtn = QtWidgets.QPushButton(QtGui.QIcon.fromTheme('system-search'), 'Transp.')
        self.focusBtn.setToolTip('Enable/Disable transparency')
        self.focusBtn.setFocusPolicy(QtCore.Qt.NoFocus)
        self.focusBtn.setCheckable(True)
        self.focusBtn.setChecked(True)
#        self.focusBtn.setMaximumSize(24, 24)
        layout.addWidget(self.focusBtn)

        self.shadowBtn = QtWidgets.QPushButton(QtGui.QIcon.fromTheme('stateshape'), 'Shadows')
        self.shadowBtn.setToolTip('Enable/Disable shadows')
        self.shadowBtn.setFocusPolicy(QtCore.Qt.NoFocus)
        self.shadowBtn.setCheckable(True)
        self.shadowBtn.setChecked(True)
        layout.addWidget(self.shadowBtn)

        self.exitBtn = QtWidgets.QPushButton(QtGui.QIcon.fromTheme('window-close'), '')
        self.exitBtn.setFocusPolicy(QtCore.Qt.NoFocus)
        layout.addWidget(self.exitBtn)

    def playToggled(self, state):
        self.playBtn.setIcon(self.playIcons[state])

    def showEvent(self, event):
        if not self.shown:
            self.shown = True
#            self.labelIcon.setFixedHeight(self.height())
            #alt icon: application-menu
#            self.labelIcon.setPixmap(QtGui.QIcon.fromTheme('preferences-other').pixmap(self.height()))
            opt = QtWidgets.QStyleOptionButton()
            opt.initFrom(self.exitBtn)
            for btn in (self.exitBtn, self.playBtn, self.focusBtn, self.shadowBtn):
                btn.setMaximumWidth(btn.iconSize().width() + 4 + btn.fontMetrics().width(btn.text()) + \
                    self.style().pixelMetric(QtWidgets.QStyle.PM_ButtonMargin, opt, btn) * 2)
                btn.setFlat(True)
                btn.setMinimumSize(10, 10)
#            QtCore.QTimer.singleShot(2000, lambda: self.toggleView(False))

    def toggleView(self, state):
        if not state:
            self.labelIcon.setFixedHeight(self.height())
        self.labelIcon.setVisible(not state)
#        self.exitBtn.setVisible(state)
        self.playBtn.setVisible(state)
        self.focusBtn.setVisible(state)
        self.shadowBtn.setVisible(state)
        self.adjustSize()

    def resizeEvent(self, event):
        mask = QtGui.QBitmap(self.rect().size())
        mask.fill(QtCore.Qt.white)
        qp = QtGui.QPainter(mask)
        qp.setBrush(QtCore.Qt.black)
        qp.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 2, 2)
        qp.end()
        self.setMask(mask)


class PanelProxy(QtWidgets.QGraphicsProxyWidget):
    modAnimation = QtCore.pyqtSignal(bool)
    modFocus = QtCore.pyqtSignal(bool)
    modShadow = QtCore.pyqtSignal(bool)
    def __init__(self):
        QtWidgets.QGraphicsProxyWidget.__init__(self)
        self.panel = Panel(self)
        self.setWidget(self.panel)
        self.panel.playBtn.toggled.connect(self.modAnimation)
        self.panel.focusBtn.toggled.connect(self.modFocus)
        self.panel.shadowBtn.toggled.connect(self.modShadow)
        self.leaveTimer = QtCore.QBasicTimer()
        QtCore.QTimer.singleShot(2000, lambda: self.toggleView(False))

    def hoverEnterEvent(self, event):
        self.leaveTimer.stop()
        self.toggleView(True)
        QtWidgets.QGraphicsProxyWidget.hoverEnterEvent(self, event)

    def hoverLeaveEvent(self, event):
        self.leaveTimer.start(500, self)
        QtWidgets.QGraphicsProxyWidget.hoverLeaveEvent(self, event)

    def timerEvent(self, event):
        if event.timerId() == self.leaveTimer.timerId():
            self.leaveTimer.stop()
            self.toggleView(False)

    def toggleView(self, state):
        self.panel.toggleView(state)
        self.repos()

    def repos(self, rect=None):
        if not rect:
            rect = self.scene().sceneRect()
        self.setX(rect.right() - self.boundingRect().width())


class DialProxy(QtWidgets.QGraphicsProxyWidget):
    pass


class ModMixer(QtWidgets.QGraphicsWidget):
    backgroundBrush = QtGui.QColor(240, 240, 240, 220)
    def __init__(self, parent, id, amount):
        QtWidgets.QGraphicsWidget.__init__(self, parent)
        self.modParent = parent
#        self.setFlags(self.flags() | self.ItemIsMovable)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Maximum))
        self.id = id
        layout = QtWidgets.QGraphicsLinearLayout(QtCore.Qt.Vertical)
        self.setLayout(layout)
        self.dialProxy = DialProxy()
        self.dial = _Dial(valueList=fullRangeCenterZero)
        self.dial.setContextMenuPolicy(QtCore.Qt.NoContextMenu)
        self.dial.setValue(amount)
        self.dial.defaultValue = 64
#        self.dial.setKeepValueVisible(True)
        self.dial.setStyleSheet('background: transparent;')
        self.dial.setMinimumSize(40, 40)
        self.dial.setAutoFillBackground(True)
        palette = self.dial.palette()
        palette.setColor(palette.Window, QtCore.Qt.transparent)
        layout.setContentsMargins(2, 20, 2, 2)
        self.dialProxy.setWidget(self.dial)
        self.dial.setPalette(palette)
        self.dialProxy.setPalette(palette)
        layout.addItem(self.dialProxy)
        self.translation = QtCore.QPointF()
        self.done = False
        self.setAcceptHoverEvents(True)

    def boundingRect(self):
        try:
            return self.layout().geometry().translated(self.layout().geometry().topLeft())
        except:
            return QtCore.QRectF(-24, -10, 48, 20)

    @QtCore.pyqtSlot(QtCore.QPointF)
    def setPos(self, pos):
        QtWidgets.QGraphicsWidget.setPos(self, pos - self.translation)

    def updateGeometry(self):
        if self.layout() and self.layout().count() and not self.translation:
            self.translation = self.layout().geometry().center() - self.layout().geometry().topLeft()
            if self.translation:
                QtWidgets.QGraphicsWidget.setPos(self, self.pos() - self.translation)
        QtWidgets.QGraphicsWidget.updateGeometry(self)

    def sizeHint(self, *args):
        return self.boundingRect().size()

    def paint(self, qp, option, widget):
#        qp.translate(.5, .5)
        qp.setBrush(self.backgroundBrush)
        qp.drawRoundedRect(self.boundingRect(), 2, 2)
        qp.drawText(self.boundingRect(), QtCore.Qt.AlignHCenter|QtCore.Qt.AlignTop, 'Mod {}'.format(self.id + 1))

    def wheelEvent(self, event):
        self.dialProxy.wheelEvent(event)

    def hoverEnterEvent(self, event):
        self.parentItem().checkOpacity(True)
        QtWidgets.QGraphicsWidget.hoverEnterEvent(self, event)

    def hoverLeaveEvent(self, event):
        self.parentItem().checkOpacity(False)
        QtWidgets.QGraphicsWidget.hoverEnterEvent(self, event)

    def mousePressEvent(self, event):
        if event.pos() not in self.dialProxy.geometry():
            QtWidgets.QGraphicsWidget.mousePressEvent(self, event)
            return
#        QtWidgets.QGraphicsWidget.mousePressEvent(self, event)
#        event.accept()
#        print('press')
        pos = self.dialProxy.mapFromScene(event.pos()).toPoint()
        mappedEvent = QtGui.QMouseEvent(QtCore.QEvent.MouseButtonPress, pos, event.button(), event.buttons(), event.modifiers())
        self.dial.mousePressEvent(mappedEvent)

    def mouseMoveEvent(self, event):
        pos = self.dialProxy.mapFromScene(event.pos()).toPoint()
        mappedEvent = QtGui.QMouseEvent(QtCore.QEvent.MouseMove, pos, event.button(), event.buttons(), event.modifiers())
        self.dial.mouseMoveEvent(mappedEvent)

    def mouseReleaseEvent(self, event):
        pos = self.dialProxy.mapFromScene(event.pos()).toPoint()
        mappedEvent = QtGui.QMouseEvent(QtCore.QEvent.MouseButtonRelease, pos, event.button(), event.buttons(), event.modifiers())
        self.dial.mouseReleaseEvent(mappedEvent)


class Modulation(QtWidgets.QGraphicsObject):
    def __init__(self, id, source, target, pathItem=None, amount=0):
        QtWidgets.QGraphicsObject.__init__(self)
        self.setAcceptHoverEvents(True)
        self.id = id
        if pathItem:
            self.pathItem = pathItem
#            self.addToGroup(pathItem)
        else:
            self.pathItem = ConnectionPath(source, target.pos())
#            self.addToGroup(self.pathItem)
        self.pathItem.setParentItem(self)
        self.pathItem.finalize(target)
        self.mixer = ModMixer(self, id, amount)
        self.mixer.setParentItem(self)
        self.mixerPos = None
        self.mixerDelta = None
        self.mixer.setPos(self.pathItem.path().pointAtPercent(.5))
        self.mixer.setZValue(self.pathItem.zValue() + .1)
        self.setZValue(1000)

        if source.direction == Out:
            self.source = source
            self.target = target
        else:
            self.source = target
            self.target = source
#        self.source.modulations.add(self)
#        self.target.modulations.add(self)
        self.sourceContainer = self.source.parentItem()
        self.sourceContainer.moved.connect(self.objectMoved)
        self.targetContainer = self.target.parentItem()
        self.targetContainer.moved.connect(self.objectMoved)

        self.tracking = False
        self.opacityAnimation = QtCore.QPropertyAnimation(self, b'opacity')
        self.opacityAnimation.setDirection(self.opacityAnimation.Backward)
        self.opacityAnimation.setStartValue(.5)
        self.opacityAnimation.setEndValue(1)
        self.opacityAnimation.setLoopCount(1)
        self.opacityAnimation.setDuration(50)

        self.shadow = QtWidgets.QGraphicsDropShadowEffect()
        self.shadow.setBlurRadius(5)
        self.shadow.setOffset(2, 2)
#        self.setGraphicsEffect(self.shadow)

    def setShadow(self, shadow):
        if shadow:
            shadow = QtWidgets.QGraphicsDropShadowEffect()
            shadow.setBlurRadius(5)
            shadow.setOffset(2, 2)
        else:
            shadow = None
        self.setGraphicsEffect(shadow)

    @property
    def vector(self):
        return self.pathItem.vector

    @property
    def refLine(self):
        return self.pathItem.refLine

    @property
    def referenceH(self):
        return self.pathItem.referenceH

    @referenceH.setter
    def referenceH(self, value):
        self.pathItem.referenceH = value

    @property
    def referenceX(self):
        return self.pathItem.referenceX

    @referenceX.setter
    def referenceX(self, value):
        self.pathItem.referenceX = value

    @property
    def amount(self):
        return self.mixer.dialProxy.widget().value

    def boundingRect(self):
        return self.pathItem.strokePath.boundingRect()|self.mixer.sceneBoundingRect()
        #maybe this? check for painting issues
#        return self.pathItem.boundingRect()|self.mixer.sceneBoundingRect()

    def shape(self):
        return self.mixer.shape().translated(self.mixer.geometry().topLeft())|self.pathItem.strokePath

    def remove(self):
        self.sourceContainer.moved.disconnect(self.objectMoved)
        try:
            self.targetContainer.moved.disconnect(self.objectMoved)
        except:
            #ignore if the container is the same of the source
            pass
        self.deleteLater()

    def setSource(self, connector):
        if self.sourceContainer:
            self.sourceContainer.moved.disconnect(self.objectMoved)
#        self.source.modulations.discard(self)
        self.source = connector
#        self.source.modulations.add(self)
        self.sourceContainer = connector.parentItem()
        self.sourceContainer.moved.connect(self.objectMoved)
        self.pathItem.setSource(connector)
        self.mixer.setPos(self.pathItem.path().pointAtPercent(.5))

    def setTarget(self, connector):
        if self.targetContainer:
#            print(self.targetContainer)
            try:
                self.targetContainer.moved.disconnect(self.objectMoved)
            except:
                print('shit!')
#        self.target.modulations.discard(self)
        self.target = connector
#        self.target.modulations.add(self)
        self.targetContainer = connector.parentItem()
        self.targetContainer.moved.connect(self.objectMoved)
        self.pathItem.setTarget(connector)
        self.mixer.setPos(self.pathItem.path().pointAtPercent(.5))

    def objectMoved(self, sender):
#        print(self.sourceContainer.pos())
        self.vector.setPoints(self.source.snapPoint, self.target.snapPoint)
        if not self.referenceH:
#            pos = self.mixer.pos() + self.mixer.translation
            pos = self.vector.pointAt(.5)
            self.refLine.setPoints(self.vector.pointAt(.25), self.vector.pointAt(.75))
        else:
#            pos = self.mixer.pos() + self.mixer.translation
#            ipo = QtCore.QLineF(self.source.snapPoint, self.mixer.pos() + self.mixer.translation)
#            rad = radians(ipo.angleTo(self.vector))
#            self.referenceH = sin(rad) * ipo.length() / self.vector.length() * 2
#            self.referenceX = cos(rad) * ipo.length() / self.vector.length()

            angle = self.vector.angle()
            h = QtCore.QLineF.fromPolar(self.referenceH * self.vector.length() * .5, angle - 90)
            h.translate(self.vector.pointAt(self.referenceX))
            pos = h.p2()
            pos.setX(max(0, min(pos.x(), self.scene().width())))
            pos.setY(max(0, min(pos.y(), self.scene().height())))
            width = self.vector.length() * .25
            p0 = QtCore.QLineF.fromPolar(width, angle)
            p0.translate(pos)
            p1 = QtCore.QLineF.fromPolar(width, angle + 180)
            p1.translate(pos)
            self.refLine.setPoints(p1.p2(), p0.p2())
        self.mixer.setPos(pos)

        if sender == self.sourceContainer:
            self.pathItem.setSourcePos()
        else:
            self.pathItem.setTargetPos()

    def stackBefore(self):
        children = self.childItems()
        for item in self.collidingItems(QtCore.Qt.IntersectsItemShape):
            if item in children or isinstance(item, BaseDialogProxy):
                continue
            try:
                self.setZValue(item.topLevelItem().zValue() + .1)
            except:
                self.setZValue(item.zValue() + .1)
            break

    def getMenus(self):
        try:
            return self._factMenus
        except:
            pass
        srcMenu = QtWidgets.QMenu('Set source')
        sDict = {k:srcMenu.addMenu(k) for k in sorted(modSourceGroups)}
        for grp, items in modSourceGroups.items():
            subMenu = sDict[grp]
            for srcId in items:
                name = modSource[srcId]
                srcAction = subMenu.addAction(name)
                srcAction.triggered.connect(lambda _, srcId=srcId: self.scene().checkSource(self.id, srcId, True))
        srcMenu.addSeparator()
        offAction = srcMenu.addAction('off (remove)')
        offAction.triggered.connect(lambda: self.scene().checkSource(self.id, 0))
        setItalic(offAction)

        destMenu = QtWidgets.QMenu('Set destination')
        dDict = {k:destMenu.addMenu(k) for k in sorted(modDestGroups)}
        for grp, items in modDestGroups.items():
            subMenu = dDict[grp]
            for destId in items:
                name = modDest[destId]
                srcAction = subMenu.addAction(name)
                srcAction.triggered.connect(lambda _, destId=destId: self.scene().checkTarget(self.id, destId, True))
        pitchAction = destMenu.addAction('Pitch')
        pitchAction.triggered.connect(lambda: self.scene().checkTarget(self.id, 0, True))
        volAction = destMenu.addAction('Volume')
        volAction.triggered.connect(lambda: self.scene().checkTarget(self.id, 30, True))

        self._factMenus = srcMenu, destMenu
        return self._factMenus

    def contextMenuEvent(self, event):
        modulations = self.scene().modulations
        if event.pos() in self.mixer.sceneBoundingRect():
            menu = QtWidgets.QMenu()
            removeAction = menu.addAction('Remove modulation')
            removeAction.triggered.connect(lambda: self.scene().removeRequest.emit(self.id))
            switchMenu = menu.addMenu('Switch position')
            for i in range(16):
                pm = QtGui.QPixmap(16, 16)
                pm.fill(modColors[i])
                switchAction = switchMenu.addAction('')
                switchAction.setIcon(QtGui.QIcon(pm))
                switchAction.triggered.connect(lambda _, dest=i: self.scene().switchRequest.emit(self.id, dest))
                if i == self.id:
                    switchAction.setEnabled(False)
                text = 'Mod {}'.format(i + 1)
                if modulations[i] is None:
                    text += ' (off)'
                    setItalic(switchAction)
                switchAction.setText(text)

            srcMenu, destMenu = self.getMenus()
            menu.addMenu(srcMenu)
            menu.addMenu(destMenu)
            menu.exec_(event.screenPos())

    def mousePressEvent(self, event):
        if self.mixer in self.scene().items(event.scenePos(), QtCore.Qt.IntersectsItemShape, QtCore.Qt.DescendingOrder):
            self.stackBefore()
            if self.scene().itemAt(event.scenePos()) == self.mixer.dialProxy:
                self.mixer.mousePressEvent(event)
                self.tracking = True
                event.accept()
            self.mixerPos = self.mixer.geometry().center()
            self.mixerDelta = self.mixer.mapFromScene(event.pos() - self.mixer.rect().center())
            return
        else:
            event.ignore()
#        QtWidgets.QGraphicsItemGroup.mousePressEvent(self, event)

    def mouseMoveEvent(self, event):
        if self.tracking:
            self.mixer.mouseMoveEvent(event)
            return
        pos = event.pos() - self.mixerDelta
        mixerGeo = self.mixer.geometry()
        width = mixerGeo.width() * .5
        height = mixerGeo.height() * .5
        pos.setX(max(width, min(self.scene().width() - width, pos.x())))
        pos.setY(max(height, min(self.scene().height() - height, pos.y())))
        pre = self.mixer.pos() + self.mixer.translation
        if pre != pos:
            ipo = QtCore.QLineF(self.source.snapPoint, pos)
            rad = radians(ipo.angleTo(self.vector))
            referenceH = sin(rad) * ipo.length()
            referenceX = cos(rad) * ipo.length()
            midVector = self.vector.length() * .5
            if -16 <= referenceH <= 16 and \
                midVector - 32 <= referenceX <= midVector + 32:
                    self.referenceH = 0
                    self.referenceX = .5
                    pos = self.vector.pointAt(.5)
            else:
                self.referenceH = referenceH / self.vector.length() * 2
                self.referenceX = referenceX / self.vector.length()
            self.mixer.setPos(pos)
            self.refLine.translate(pos - pre)
            self.pathItem.setFullPath()
        QtWidgets.QGraphicsObject.mouseMoveEvent(self, event)

    def mouseReleaseEvent(self, event):
        if self.tracking:
            self.mixer.mouseReleaseEvent(event)
            self.tracking = False
#        self.mixerDelta = None
#        self.mixerPos = None

    def wheelEvent(self, event):
#        print(self.scene().items(event.scenePos(), QtCore.Qt.IntersectsItemShape, QtCore.Qt.DescendingOrder))
        if self.mixer.dialProxy in self.scene().items(event.scenePos(), QtCore.Qt.IntersectsItemShape, QtCore.Qt.DescendingOrder):
            self.mixer.wheelEvent(event)

    def checkOpacity(self, state):
        if not self.scene().opacityState:
            self.setOpacity(1)
            return
        if state and self.opacity() < 1:
            self.opacityAnimation.setDirection(self.opacityAnimation.Forward)
            self.opacityAnimation.start()
        elif not state and self.opacity() > .5:
            self.opacityAnimation.setDirection(self.opacityAnimation.Backward)
            self.opacityAnimation.start()

    def hoverMoveEvent(self, event):
        self.checkOpacity(True)
        QtWidgets.QGraphicsObject.hoverMoveEvent(self, event)

    def hoverLeaveEvent(self, event):
        self.checkOpacity(False)
        QtWidgets.QGraphicsObject.hoverLeaveEvent(self, event)

    def paint(self, *args):
        pass


class ConnectionPath(QtWidgets.QGraphicsPathItem):
    def __init__(self, connector, cursorPos):
        QtWidgets.QGraphicsPathItem.__init__(self)
        if connector.direction == In:
            self.source = None
            self.target = connector
        else:
            self.source = connector
            self.target = None
        self.startPos = connector.snapPoint

#        self.setPathMode(connector)
        self.endPos = cursorPos

        self.vector = QtCore.QLineF(self.startPos, self.endPos)
        self.refLine = QtCore.QLineF(self.vector.pointAt(.25), self.vector.pointAt(.75))
        self.referenceH = 0
        self.referenceX = .5

        self.setPen(QtGui.QPen(QtCore.Qt.red, 2))
        self._strokePathObject = QtGui.QPainterPathStroker()
        self._strokePathObject.setWidth(10)
        self._strokePath = None
        self._clipRegion = QtGui.QRegion(QtCore.QRect(0, 0, 10000, 10000))
        self._cachedPath = QtGui.QPainterPath()
        #optimization (sort of) the boundingRect, since the original implementation
        #takes all the points of the cubic coordinates into account
        self.boundingRect = lambda: self._cachedPath.boundingRect()

    @property
    def strokePath(self):
        return self._strokePath

    @property
    def clipRegion(self):
        return self._clipRegion

    def finalize(self, connector):
        if connector.direction == In:
            self.target = connector
        else:
            self.source = connector
#        self.setPathMode(self.source, self.target)
#        self.setSourcePos()
#        self.setTargetPos()
        self.startPos = self.source.snapPoint
        self.endPos = self.target.snapPoint
        self.vector.setPoints(self.startPos, self.endPos)
        self.refLine.setP1(self.vector.pointAt(.25))
        self.refLine.setP2(self.vector.pointAt(.75))
        self.setFullPath()

    def setSource(self, connector):
        self.source = connector
        self.startPos = self.source.snapPoint
        self.vector.setP1(self.startPos)
        self.refLine.setPoints(self.vector.pointAt(.25), self.vector.pointAt(.75))
        self.setFullPath()

    def setTarget(self, connector):
        self.target = connector
        self.endPos = self.target.snapPoint
        self.vector.setP2(self.endPos)
        self.refLine.setPoints(self.vector.pointAt(.25), self.vector.pointAt(.75))
        self.setTargetPos()

    def setSourcePos(self):
        self.startPos = self.source.snapPoint
        self.vector.setP1(self.startPos)
        self.setFullPath()

    def setTargetPos(self):
        self.endPos = self.target.snapPoint
        self.vector.setP2(self.endPos)
        self.setFullPath()

    def setCursorPos(self, pos):
        self.endPos = pos
        path = QtGui.QPainterPath()
        path.moveTo(self.startPos)
        path.lineTo(self.endPos)
        self.setPath(path)
        self._cachedPath = path

#    def setPath(self, path):
#        QtWidgets.QGraphicsPathItem.setPath(self, path)
#        self._cachedPath = path

    def setFullPath(self):
        path = self.path()
        self.setPath(path)
        self._cachedPath = path
        self._strokePath = self._strokePathObject.createStroke(path)
        self._clipRegion = QtGui.QRegion(path.boundingRect().toRect().adjusted(-1, -1, 1, 1)) ^ QtGui.QRegion(self.source.boundingRect().toRect())

    def path(self):
        path = QtGui.QPainterPath()
        path.moveTo(self.startPos)
        path.quadTo(self.refLine.p1(), self.refLine.pointAt(.5))
        path.quadTo(self.refLine.p2(), self.endPos)
        path.lineTo(self.endPos)
        return path

    def paint(self, qp, option, widget):
#        print(self.path().boundingRect())
        qp.setClipRegion(self._clipRegion)
        QtWidgets.QGraphicsPathItem.paint(self, qp, option, widget)


_holeColor = QtGui.QColor(64, 64, 64)
def createConnGradient(baseColor, darker=200):
    grad = QtGui.QRadialGradient(0.5, 0.5, 0.5)
    grad.setCoordinateMode(grad.ObjectBoundingMode)
    grad.setColorAt(0, _holeColor)
    grad.setColorAt(0.49, _holeColor)
    grad.setColorAt(0.5, baseColor.darker(darker))
    grad.setColorAt(0.75, baseColor)
    grad.setColorAt(1, baseColor.darker(darker * 1.5))
    return grad


class Connector(QtWidgets.QGraphicsWidget):
#    _disabledOutColor = _outColor.darker()
#    _disabledOutColor.setAlpha(128)
#    _disabledInColor = _inColor.darker()
#    _disabledInColor.setAlpha(128)

    inColor = createConnGradient(QtGui.QColor(QtCore.Qt.red).lighter(115), 175)
    
#    inColor.setCoordinateMode(inColor.ObjectBoundingMode)
#    inColor.setColorAt(0, _holeColor)
#    inColor.setColorAt(0.49, _holeColor)
#    inColor.setColorAt(0.5, _inColor.darker())
#    inColor.setColorAt(0.75, _inColor)
#    inColor.setColorAt(1, _inColor.darker())

    outColor = createConnGradient(QtGui.QColor(QtCore.Qt.green))
    disabledOutColor = createConnGradient(QtGui.QColor(0, 127, 0, 127))
    disabledInColor = createConnGradient(QtGui.QColor(127, 0, 0, 127))

    def __init__(self, parent, id, direction, name='', labelPos=Bottom):
        QtWidgets.QGraphicsWidget.__init__(self, parent)
        self.setAcceptHoverEvents(True)
        self.id = id
        self.direction = direction
        self.name = name
#        self.modulations = set()
        if direction == Out:
            self.colors = self.disabledOutColor, self.outColor
        else:
            self.colors = self.disabledInColor, self.inColor

        self.connRect = QtCore.QRectF(0, 0, 16, 16)
#        self.snapPoint = QtCore.QPointF(8, 8)
        self.labelPos = labelPos
        font = self.font()
        font.setBold(False)
        self.setFont(font)
        if self.name:
            self.labelRect = QtCore.QRectF(QtWidgets.QApplication.fontMetrics().boundingRect(
                QtCore.QRect(), QtCore.Qt.TextExpandTabs, self.name)).adjusted(-3, -2, 3, 0)
            if labelPos == Bottom:
                self.labelRect.moveTop(20)
                self.labelRect.moveLeft(-(self.labelRect.width() - self.connRect.width()) * .5)
            elif labelPos == Right:
                self.labelRect.moveCenter(self.connRect.center())
                self.labelRect.moveLeft(self.connRect.right() + 4)
        else:
            self.labelRect = QtCore.QRectF()
        self.fullRect = self.connRect|self.labelRect
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred))
        self.geometryChanged.connect(self.invalidateRect)

    def invalidateRect(self):
        center = self.boundingRect().center()
        self.fullRect.moveCenter(center)
        self.connRect.moveCenter(center)
        if self.labelRect:
            self.labelRect.moveCenter(center)
            if self.labelPos == Bottom:
                self.connRect.moveTop(self.fullRect.top())
                self.labelRect.moveBottom(self.fullRect.bottom())
            elif self.labelPos == Right:
                self.connRect.moveLeft(self.fullRect.left())
                self.labelRect.moveRight(self.fullRect.right())

    @property
    def snapPoint(self):
        return self.mapToScene(self.connRect.center())

    def _boundingRect(self):
        try:
            print(QtWidgets.QGraphicsWidget.boundingRect(self))
            return self.fullRect
        except:
            return QtCore.QRectF(0, 0, 16, 16)

    def setCenterPos(self, ref):
#        if isinstance(ref, BaseWidget) and not self.labelRect.isNull():
#            x = ref.geometry().center().x() - self.boundingRect().center().x()
#            y = ref.geometry().y() + ref._labelWidget.y() - self.labelRect.top()
#            self.setPos(x, y)
#        else:
            self.setPos(QtCore.QPointF(ref.geometry().center()) - self.boundingRect().center())

    def hoverEnterEvent(self, event):
        if self.scene().opacityState:
            for mod in self.scene().modulations.values():
                if mod and self in (mod.source, mod.target):
#            for mod in self.modulations:
                    mod.checkOpacity(True)

    def hoverLeaveEvent(self, event):
        if self.scene().opacityState:
            for mod in self.scene().modulations.values():
                if mod and self in (mod.source, mod.target):
                    mod.checkOpacity(False if not mod.isUnderMouse() else True)
#            for mod in self.modulations:
#                mod.checkOpacity(False if not mod.isUnderMouse() else True)

    def paint(self, qp, option, widget):
        qp.translate(.5, .5)
        qp.setBrush(self.colors[self.isEnabled()])
        qp.setPen(QtCore.Qt.NoPen)
        qp.drawEllipse(self.connRect)
#        return
#        qp.setBrush(QtCore.Qt.darkGray)
#        qp.drawEllipse(self.connRect.adjusted(4, 4, -4, -4))

        if self.name:
            qp.setBrush(QtCore.Qt.white)
            qp.drawRoundedRect(self.labelRect, 2, 2)
            qp.setPen(QtCore.Qt.black)
            qp.setFont(self.font())
            qp.drawText(self.labelRect, QtCore.Qt.AlignCenter, self.name)


class BaseContainer(QtWidgets.QGraphicsWidget):
    moved = QtCore.pyqtSignal(object)
    def __init__(self, name, reference=None, labelPos=None):
        QtWidgets.QGraphicsWidget.__init__(self)
        self.name = name
        self.reference = reference
        self.referenceRect = QtCore.QRectF()
        self.setFlags(self.flags() | self.ItemIsMovable)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred))
        self.setAcceptHoverEvents(True)
        self.geometryChanged.connect(lambda: self.moved.emit(self))
        self.connectors = {}
        self.connRef = {}
        self.labelPos = labelPos
        font = self.font()
        font.setBold(False)
        self.setFont(font)
        if name and labelPos is not None:
            self.labelRect = QtWidgets.QApplication.fontMetrics().boundingRect(self.name).adjusted(-4, -2, 4, 2)
            self.labelRect.moveTopLeft(QtCore.QPoint(0, 0))
            if labelPos == Left:
                self.labelRect.moveLeft(-self.labelRect.width())
        else:
            self.labelRect = None

    def connectToScene(self):
        if self.reference:
            self.scene().sceneRectChanged.connect(lambda: QtCore.QTimer.singleShot(0, self.setRefGeometry))

    def setRefGeometry(self, *args):
        pos = self.reference.mapTo(self.reference.window(), self.reference.rect().topLeft())
        self.referenceRect = QtCore.QRectF(pos, QtCore.QSizeF(self.reference.rect().size()))
        self.setGeometry(self.referenceRect)
        for conn, ref in self.connRef.items():
            if isinstance(ref, QtWidgets.QWidget):
                conn.setCenterPos(ref)

    def stackBefore(self):
        children = self.childItems()
        for item in self.collidingItems(QtCore.Qt.IntersectsItemShape):
            if item in children or not isinstance(item, BaseContainer):
                continue
            try:
                self.setZValue(item.topLevelItem().zValue() + .1)
            except:
                print('over container exception!')
                self.setZValue(item.zValue() + .1)
            break

    def mouseMoveEvent(self, event):
        QtWidgets.QGraphicsWidget.mouseMoveEvent(self, event)
        if self.referenceRect:
            geo = self.geometry()
            left, top, right, bottom = self.referenceRect.getCoords()
            if left - 10 <= geo.left() <= left + 10 and \
                top - 10 <= geo.top() <= top + 10:
                    self.setPos(left, top)
                    self.stackBefore()
                    return
        if self.geometry() not in self.scene().sceneRect():
            sceneRect = self.scene().sceneRect()
            geo = self.geometry()
            self.setX(min(sceneRect.right() - geo.width(), max(self.x(), sceneRect.left())))
            self.setY(min(sceneRect.bottom() - geo.height(), max(self.y(), sceneRect.top())))
        self.stackBefore()

    def paint(self, qp, option, widget):
        qp.save()
        qp.translate(-.5, -.5)
        qp.setBrush(QtGui.QColor(240, 240, 240, 120))
        qp.drawRoundedRect(self.boundingRect(), 2, 2)
        if self.labelRect:
#            qp.setPen(QtCore.Qt.lightGray)
            qp.setBrush(QtCore.Qt.white)
            if self.labelPos == Left:
                qp.rotate(-90)
            qp.drawRoundedRect(self.labelRect, 2, 2)
            qp.setFont(self.font())
            qp.drawText(self.labelRect, QtCore.Qt.AlignCenter, self.name)
        qp.restore()


class ReferenceContainer(BaseContainer):
    def __init__(self, name, reference, labelPos=None):
        BaseContainer.__init__(self, name, reference, labelPos)

    def addConnector(self, id, direction, name, reference):
        connector = Connector(self, id, direction, name)
        self.connectors[name] = connector
        self.connRef[connector] = reference
        return connector


class LayoutContainer(BaseContainer):
    def __init__(self, name, reference=None, labelPos=None):
        BaseContainer.__init__(self, name, reference, labelPos)
        self.layout = QtWidgets.QGraphicsGridLayout()
        left = top = right = bottom = 0
        if labelPos == Top:
            top = self.labelRect.height()
        elif labelPos == Left:
            left = self.labelRect.height()
        self.layout.setContentsMargins(left, top, right, bottom)
        self.layout.setSpacing(0)
        self.setLayout(self.layout)

    def addConnector(self, id, direction, name, labelPos=Bottom, row=None, column=None, rowSpan=1, columnSpan=1):
        connector = Connector(self, id, direction, name, labelPos)
        self.connectors[name] = connector
        if row is None:
            self.layout.addItem(connector, self.layout.rowCount(), self.layout.columnCount())
        else:
            self.layout.addItem(connector, row, column, rowSpan, columnSpan, QtCore.Qt.AlignCenter)
        return connector


class ModMatrixScene(QtWidgets.QGraphicsScene):
    removeRequest = QtCore.pyqtSignal(int)
    switchRequest = QtCore.pyqtSignal(int, int)
    amountChanged = QtCore.pyqtSignal(int, int)
    modulationChanged = QtCore.pyqtSignal(int, int, int, int)
    closeModMatrix = QtCore.pyqtSignal()

    def __init__(self, editorWindow):
        QtWidgets.QGraphicsScene.__init__(self)
        self.editorWindow = editorWindow
        self.settings = QtCore.QSettings()
        self.view = None
        self.tempLine = None
        self.containers = {}
        self.modulations = {m:None for m in range(16)}
        self.sources = {}
        self.destinations = {}
        self.shadowItems = set()

        self.panel = PanelProxy()
        self.panel.widget().setMaximumHeight(self.editorWindow.editorMenuBar.height())
        self.panel.widget().exitBtn.clicked.connect(self.closeModMatrix)
        self.addItem(self.panel)
#        self.panel.setPos(10, 10)
        self.panel.setZValue(2000000)
        self.sceneRectChanged.connect(self.panel.repos)

        self.modTableDialogProxy = ModTableDialogProxy(self)
        self.modTableDialogProxy.sectionHighlight.connect(self.highlight)
        self.modTable = self.modTableDialogProxy.modTable
        self.modTable.modulations = self.modulations
        self.modTable.modSourceChanged.connect(self.checkSource)
        self.modTable.modAmountChanged.connect(self.checkAmount)
        self.modTable.modDestinationChanged.connect(self.checkTarget)
#        self.modTable.sectionHighlight.connect(self.highlight)
        self.modTable.verticalHeader().switchRequest.connect(self.switchRequest)
        self.modulationChanged.connect(self.modTable.modulationChanged)
        self.amountChanged.connect(self.modTable.amountChanged)
        self.addItem(self.modTableDialogProxy)
        self.modTableDialogProxy.setPos(250, 0)
        #this should be enough to keep this on top, right?
        self.modTableDialogProxy.setZValue(1000000)

        self.modifiersDialogProxy  = ModifiersDialogProxy(self)
        self.addItem(self.modifiersDialogProxy)
        self.modifiersDialogProxy.setPos(
            self.modTableDialogProxy.x() + self.modTableDialogProxy.geometry().width() + 40, 0)
        self.modifiersDialogProxy.setZValue(1000000)

        self.modifiersDialogProxy.siblings.append(self.modTableDialogProxy)
        self.modTableDialogProxy.siblings.append(self.modifiersDialogProxy)

        self.buildLayout()

        self.connPen = QtGui.QPen(QtGui.QColor(88, 120, 96, 190), 2, QtCore.Qt.DashLine)
        self.connPen.setDashPattern([32, 5, 2, 5])
        self.dashSize = sum(self.connPen.dashPattern())
        self.dashOffset = 0

        self.animationTimer = QtCore.QTimer()
        self.animationTimer.setInterval(100)
        self.animationTimer.timeout.connect(self.setDashOffset)
        self.animationState = True
        self.panel.modAnimation.connect(self.setAnimationState)

        self.removeRequest.connect(self.removeMod)
        self.switchRequest.connect(self.switchMods)
        self.modLock = Lock()
        self.highlighted = -1
        self.opacityState = True
        self.panel.modFocus.connect(self.setOpacityState)

        self.panel.modShadow.connect(self.setShadowState)

        self.shadowState = True

    def addItem(self, item):
        QtWidgets.QGraphicsScene.addItem(self, item)
        try:
            item.setShadow(self.settings.value('modShadows', True, bool))
            self.shadowItems.add(item)
        except:
            pass

    def setShadowState(self, state):
        self.shadowState = state
        self.panel.panel.shadowBtn.setChecked(state)
        for item in self.shadowItems:
            item.setShadow(state)

    def setAnimationState(self, state):
        self.panel.panel.playBtn.setChecked(state)
        if not state:
            self.animationTimer.stop()
        else:
            self.animationTimer.start()
        self.animationState = state

    def setOpacityState(self, state):
        self.opacityState = state
        self.panel.panel.focusBtn.setChecked(state)
        for mod in self.modulations.values():
            if mod:
                mod.checkOpacity(not state)

    def setDashOffset(self):
        offset = self.connPen.dashOffset() - .4
        if offset < -self.dashSize:
            offset = 0
        self.connPen.setDashOffset(offset)
        if not any(self.modulations.values()):
            self.animationTimer.stop()
            return
        self.modLock.acquire()
        for id, mod in self.modulations.items():
            if not mod:
                continue
            self.connPen.setColor(modColors[id])
            mod.pathItem.setPen(self.connPen)
        self.modLock.release()

    def highlight(self, modId):
        if self.highlighted >= 0 and self.highlighted != modId and self.modulations[self.highlighted]:
            self.modulations[self.highlighted].checkOpacity(False)
        if modId >= 0 and self.modulations[modId]:
            mod = self.modulations[modId]
            mod.checkOpacity(True)
            mod.stackBefore()
        self.highlighted = modId

    def removeAll(self):
        for modId, mod in self.modulations.items():
            if mod:
                self.removeMod(modId)

    def removeMod(self, modId):
        modulation = self.modulations.get(modId)
        if modulation:
            self.modLock.acquire()
            self.modulations[modId] = None
            self.modTable.modulationChanged(modId, 0, -1, -1)
            modulation.remove()
            self.modLock.release()

    def randomizeMods(self, modList=None):
        if modList is None:
            modList = range(16)
        for modId in modList:
            modulation = self.modulations[modId]
            sourceId = randrange(1, len(modSource))
            destinationId = randrange(len(modDest))
            amount = randrange(128)
            if not modulation:
                self.createMod(modId, sourceId, destinationId, amount)
            else:
                modulation.setSource(self.sources[sourceId])
                modulation.setTarget(self.destinations[destinationId])
                self.modTable.modulationChanged(modId, modulation.source.id, destinationId, -1)
                modulation.mixer.dial.setValue(amount)
#                self.checkSource(modId, sourceId, emit=True)
#                self.checkTarget(modId, destinationId)
#                self.checkAmount(modId, amount)
#            print('randomizzo', modId)

    def switchMods(self, srcId, destId):
        srcMod = self.modulations[srcId]
        destMod = self.modulations.get(destId)
        if not srcMod:
            if not destMod:
                return
            srcMod = destMod
            _srcId = srcId
            srcId = destId
            destId = _srcId
            destMod = None
        if destMod:
            self.modulationChanged.emit(srcId, destMod.source.id, destMod.target.id, destMod.amount)
            destMod.id = srcId
            destMod.mixer.id = srcId
            destMod.mixer.dial.valueChanged.disconnect()
            destMod.mixer.dial.valueChanged.connect(lambda value, m=srcId: self.amountChanged.emit(m, value))
        else:
            self.modulationChanged.emit(srcId, 0, -1, -1)
        srcMod.id = destId
        srcMod.mixer.id = destId
        srcMod.mixer.dial.valueChanged.disconnect()
        srcMod.mixer.dial.valueChanged.connect(lambda value, m=destId: self.amountChanged.emit(m, value))
        self.modulationChanged.emit(destId, srcMod.source.id, srcMod.target.id, srcMod.amount)
        self.modulations[srcId] = destMod
        self.modulations[destId] = srcMod
        self.update(self.sceneRect())
        
#            self.removeMod(dest)
#            self.modTable.cellWidget(src, 0).setCurrentIndex(0)
#            srcMod.id = dest
#            srcMod.mixer.id = dest
#            self.update(self.sceneRect())

#    def createModFromTable(self, modId, source=0):
#        destination = self.destinations.get(self.modTable.cellWidget(modId, 2).currentIndex())
#        if not destination:
#            destination = self.destinations[0]
#            self.modTable.cellWidget(modId, 2).setCurrentIndex(0)
#        modulation = self.createMod(modId, source, destination, amount=self.modTable.cellWidget(modId, 1).value())
#        self.modulationChanged.emit(modId, modulation.source.id, modulation.target.id, 0)

    def createMod(self, modId, sourceId, destinationId=None, amount=None):
        if sourceId <= 0:
            sourceId = self.modTable.cellWidget(modId, 0).currentIndex()
            if sourceId <= 0:
                return
        if amount is None:
            amount = self.modTable.cellWidget(modId, 1).value()
        if destinationId is None:
            destinationId = max(0, self.modTable.cellWidget(modId, 2).currentIndex())
        modulation = Modulation(
            modId, 
            self.sources[sourceId], 
            self.destinations[destinationId], 
            amount=amount
            )
        modulation.mixer.dial.valueChanged.connect(lambda value, m=modId: self.amountChanged.emit(m, value))
        self.modulations[modId] = modulation
        self.modulationChanged.emit(modId, modulation.source.id, modulation.target.id, modulation.amount)
        self.addItem(modulation)
        if not self.animationTimer.isActive() and self.animationState:
            self.animationTimer.start()
        else:
            self.connPen.setColor(modColors[modId])
            modulation.pathItem.setPen(self.connPen)
        return modulation

    def checkSource(self, modId, sourceId, emit=False):
        modulation = self.modulations[modId]
        if modulation and modulation.source.id == sourceId:
            return
        elif modulation and not sourceId:
            self.removeMod(modId)
        elif not modulation and sourceId:
            self.createMod(modId, sourceId)
        else:
            try:
                modulation.setSource(self.sources[sourceId])
            except:
                self.createMod(modId, sourceId)
        if emit:
            self.modTable.modulationChanged(modId, sourceId, -1, -1)
        self.modulationChanged.disconnect(self.modTable.modulationChanged)
        self.modulationChanged.emit(modId, sourceId, -1, -1)
        self.modulationChanged.connect(self.modTable.modulationChanged)

    def checkAmount(self, modId, amount):
        modulation = self.modulations[modId]
        if not modulation:
            modulation = self.createMod(modId, -1, amount=amount)
        elif modulation.amount == amount:
            return
#            print('amount changed for no modulation?!')
#            return
        modulation.mixer.dial.blockSignals(True)
        modulation.mixer.dial.setValue(amount)
        modulation.mixer.dial.blockSignals(False)
        self.modulationChanged.disconnect(self.modTable.modulationChanged)
        self.modulationChanged.emit(modId, -1, -1, amount)
        self.modulationChanged.connect(self.modTable.modulationChanged)

    def checkTarget(self, modId, destinationId, emit=False):
        modulation = self.modulations[modId]
        if not modulation:
            modulation = self.createMod(modId, -1, destinationId=destinationId)
#            print('target changed for no modulation?!')
#            return
        elif modulation.target.id == destinationId:
            return
        modulation.setTarget(self.destinations[destinationId])
        if emit:
            self.modTable.modulationChanged(modId, modulation.source.id, destinationId, -1)
        self.modulationChanged.disconnect(self.modTable.modulationChanged)
        self.modulationChanged.emit(modId, -1, destinationId, -1)
        self.modulationChanged.connect(self.modTable.modulationChanged)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton and \
            event.scenePos() not in self.modifiersDialogProxy.sceneBoundingRect() and \
            event.scenePos() not in self.modTableDialogProxy.sceneBoundingRect():
                for item in self.items(event.scenePos(), QtCore.Qt.IntersectsItemShape, QtCore.Qt.DescendingOrder):
                    if isinstance(item, (ModMixer, BaseDialogProxy)):
                        break
                    if isinstance(item, Connector) and event.scenePos() in item.mapToScene(item.fullRect).boundingRect():
                        return self.dragStart(item, event.scenePos())
        QtWidgets.QGraphicsScene.mousePressEvent(self, event)

    def mouseMoveEvent(self, event):
        if event.buttons():
            QtWidgets.QGraphicsScene.mouseMoveEvent(self, event)
            return

        mouseItems = self.items(event.scenePos(), QtCore.Qt.IntersectsItemShape, QtCore.Qt.DescendingOrder)
        mixList = []
        modList = []
        connector = None
        for item in mouseItems:
            if isinstance(item, ModMixer):
                mixList.append(item)
                if modList:
                    break
            elif isinstance(item, (Modulation, ConnectionPath)):
                modList.append(item)
            elif isinstance(item, Connector) and self.opacityState:
                connector = item
        if mixList and modList and mixList[0] != modList[0].topLevelItem():
            mixList[0].topLevelItem().setZValue(modList[0].topLevelItem().zValue() + .1)
        if not self.opacityState and connector and not mixList:
            for m in self.modulations.values():
                if m and m not in modList:
                    if (connector.direction and m.source == connector) or \
                        (not connector.direction and m.target == connector):
                            m.checkOpacity(True)
                    else:
                        m.checkOpacity(False)
        QtWidgets.QGraphicsScene.mouseMoveEvent(self, event)
        item = self.itemAt(event.scenePos())
        if item:
            self.views()[0].window().statusBar().showMessage('{} {}'.format(item.__class__.__name__, item.zValue()))

    def dragStart(self, connector, pos):
        self.tempLine = ConnectionPath(connector, pos)
        self.addItem(self.tempLine)
        self.tempLine.setZValue(connector.parentItem().zValue() + .01)
        try:
            assert isinstance(self.view, QtWidgets.QWidget)
            drag = QtGui.QDrag(self.view)
        except:
            self.view = self.views()[0]
            drag = QtGui.QDrag(self.view)
        mime = QtCore.QMimeData()
        drag.setMimeData(mime)
        byteArray = QtCore.QByteArray()
        stream = QtCore.QDataStream(byteArray, QtCore.QIODevice.WriteOnly)
        stream.writeString(connector.parentItem().name)
        stream.writeString(connector.name)
        mime.setData('bigglesworth/matrixdrag', byteArray)
        connList = self.sources.values() if connector.direction == Out else self.destinations.values()
        for conn in connList:
            if conn == connector:
                continue
            conn.setEnabled(False)
        if not drag.exec_(QtCore.Qt.MoveAction|QtCore.Qt.LinkAction, QtCore.Qt.LinkAction):
            self.removeItem(self.tempLine)
        for conn in connList:
            conn.setEnabled(True)

    def getDragData(self, event):
        stream = QtCore.QDataStream(event.mimeData().data('bigglesworth/matrixdrag'))
        container = self.containers[stream.readString()]
        connector = container.connectors[stream.readString()]
        return container, connector

    def dragMoveEvent(self, event):
#        print(self.tempLine.boundingRect(), self.tempLine.path().boundingRect())
        if event.source() != self.view:
            return
        self.tempLine.setCursorPos(event.scenePos())
        target = self.itemAt(event.scenePos())
        if not isinstance(target, Connector):
            items = self.items(event.scenePos(), QtCore.Qt.IntersectsItemShape, QtCore.Qt.DescendingOrder)
            for target in items:
                if isinstance(target, Connector):
                    break
            else:
                event.setDropAction(QtCore.Qt.MoveAction)
                return
        container, connector = self.getDragData(event)
        if connector == target or connector.direction == target.direction:
            event.ignore()
            return
        self.tempLine.setCursorPos(target.snapPoint)
        event.setDropAction(QtCore.Qt.LinkAction)
        event.accept()

    def dropEvent(self, event):
        if event.source() != self.view:
            return
        target = self.itemAt(event.scenePos())
        if not isinstance(target, Connector):
            items = self.items(event.scenePos(), QtCore.Qt.IntersectsItemShape, QtCore.Qt.DescendingOrder)
            for target in items:
                if isinstance(target, Connector):
                    break
            else:
                self.removeItem(self.tempLine)
                return
        for modId in sorted(self.modulations):
            if self.modulations[modId] is None:
                break
        else:
            self.removeItem(self.tempLine)
            return
        container, connector = self.getDragData(event)
        modulation = Modulation(modId, connector, target, pathItem=self.tempLine)
        self.modulations[modId] = modulation
        self.modulationChanged.emit(modId, modulation.source.id, modulation.target.id, modulation.amount)
        modulation.mixer.dial.valueChanged.connect(lambda value, m=modId: self.amountChanged.emit(m, value))
        self.addItem(modulation)
        if not self.animationTimer.isActive() and self.animationState:
            self.animationTimer.start()
        else:
            self.connPen.setColor(modColors[modId])
            modulation.pathItem.setPen(self.connPen)

    def resetPositions(self):
        for container in self.containers.values():
            container.setRefGeometry()

    def helpEvent(self, event):
        item = self.itemAt(event.scenePos())
        if isinstance(item, (ModMixer, DialProxy)):
            modulation = item.topLevelItem()
            modulation.mixer.setToolTip('''
                    <b><font color={color}>&#9632;</font> Modulation {id}</b><br/>
                    source: {src}<br/>
                    dest: {dest}<br/>
                    amount: {amount}
                '''.format(
                    color=QtGui.QColor(modColors[modulation.id]).name(), 
                    id=modulation.id + 1, 
                    src=modulation.source.name, 
                    dest=modulation.target.name, 
                    amount=modulation.amount
                    ))
        QtWidgets.QGraphicsScene.helpEvent(self, event)

    def contextMenuEvent(self, event):
        if event.scenePos() in self.modTableDialogProxy.geometry():
            QtWidgets.QGraphicsScene.contextMenuEvent(self, event)
            return
        for item in self.items(event.scenePos(), QtCore.Qt.IntersectsItemShape, QtCore.Qt.DescendingOrder):
            if isinstance(item, ModMixer):
                QtWidgets.QGraphicsScene.contextMenuEvent(self, event)
                return
        menu = QtWidgets.QMenu()
        existingMods = list(modId for modId, mod in self.modulations.items() if mod)
        modCount = len(existingMods)
        if existingMods and modCount < 16:
            if modCount == 1:
                text = 'Randomize modulation {}'.format(existingMods[0] + 1)
            else:
                text = 'Randomize {} existing modulations'.format(modCount)
            randomizeExistingAction = menu.addAction(text)
            randomizeExistingAction.triggered.connect(lambda: self.randomizeMods(existingMods))
        randomizeAllAction = menu.addAction('Randomize all 16 modulations')
        randomizeAllAction.triggered.connect(lambda: self.randomizeMods())
        menu.addSeparator()
        clearAction = menu.addAction('Clear all')
        clearAction.triggered.connect(self.removeAll)
        menu.addSeparator()
        resetPosAction = menu.addAction('Reset container positions')
        resetPosAction.triggered.connect(self.resetPositions)
        menu.exec_(event.screenPos())

    def createLayoutContainer(self, name, sources, targets, refWidget=None, labelPos=Left, connLabelPos=Bottom):
        if refWidget:
            refWidget = getattr(self.editorWindow, refWidget)
        cont = LayoutContainer(name, refWidget, labelPos)
        self.addItem(cont)
        cont.connectToScene()
        self.containers[name] = cont
        for id, name, pos in sources:
            self.sources[id] = cont.addConnector(id, Out, name, connLabelPos, *pos)
        for id, name, pos in targets:
            self.destinations[id] = cont.addConnector(id, In, name, connLabelPos, *pos)
        return cont

    def createRefContainer(self, name, sources, targets, refWidget=None, labelPos=Top, connLabelPos=Bottom):
        refWidget = getattr(self.editorWindow, refWidget)
        cont = ReferenceContainer(name, refWidget, labelPos)
        self.addItem(cont)
        cont.connectToScene()
        self.containers[name] = cont
        for id, name, refWidget in sources:
            refWidget = getattr(self.editorWindow, refWidget)
            self.sources[id] = cont.addConnector(id, Out, name, refWidget)
        for id, name, refWidget in targets:
            refWidget = getattr(self.editorWindow, refWidget)
            self.destinations[id] = cont.addConnector(id, In, name, refWidget)

    def buildLayout(self):
        self.createRefContainer('OSC 1', [], [
            (1, 'Pitch', 'osc1Shape'), 
            (2, 'FM', 'osc1FMSource'), 
            (3, 'PW/Wave', 'osc1PWMSource')
            ], 'osc1Frame')

        self.createRefContainer('OSC 2', [], [
            (4, 'Pitch', 'osc2Shape'), 
            (5, 'FM', 'osc2FMSource'), 
            (6, 'PW/Wave', 'osc2PWMSource')
            ], 'osc2Frame')

        self.createRefContainer('OSC 3', [], [
            (7, 'Pitch', 'osc3Shape'), 
            (8, 'FM', 'osc3FMSource'), 
            (9, 'PW/Wave', 'osc3PWMSource')
            ], 'osc3Frame')

        self.createRefContainer('LFO 1', [
            (1, 'LFO', 'LFO1Shape'), 
            (2, 'Press', 'LFO1Keytrack')
            ], [
            (31, 'Speed', 'LFO1Speed')
            ], 'lfo1Frame')

        self.createRefContainer('LFO 2', [
            (3, 'LFO', 'LFO2Shape'), 
            (4, 'Press', 'LFO2Keytrack')
            ], [
            (32, 'Speed', 'LFO2Speed')
            ], 'lfo2Frame')

        self.createRefContainer('LFO 3', [
            (5, 'LFO', 'LFO3Shape'), 
            ], [
            (33, 'Speed', 'LFO3Speed')
            ], 'lfo3Frame')

        self.createRefContainer('Mixer', [], [
            (10, 'O1\nlevel', 'mixerOsc1Level'), (11, 'O1\nbal', 'mixerOsc1Balance'), 
            (12, 'O2\nlevel', 'mixerOsc2Level'), (13, 'O2\nbal', 'mixerOsc2Balance'), 
            (14, 'O3\nlevel', 'mixerOsc3Level'), (15, 'O3\nbal', 'mixerOsc3Balance'), 
            (16, 'Ring\nlevel', 'mixerRingModLevel'), (17, 'Ring\nbal', 'mixerRingModBalance'), 
            (18, 'Noise\nlevel', 'mixerNoiseLevel'), (19, 'Noise\nbal', 'mixerNoiseBalance')
            ], 'mixerFrame', Left)

        self.createRefContainer('Filter 1', [], [
            (20, 'Cutoff', 'filter1Cutoff'), (21, 'Reson.', 'filter1Resonance'), 
            (22, 'FM', 'filter1FMSource'), (23, 'Drive', 'filter1Drive'), 
            (24, 'Pan', 'filter1PanSource')
            ], 'filter1Frame')

        self.createRefContainer('Filter 2', [], [
            (25, 'Cutoff', 'filter2Cutoff'), (26, 'Reson.', 'filter2Resonance'), 
            (27, 'FM', 'filter2FMSource'), (28, 'Drive', 'filter2Drive'), 
            (29, 'Pan', 'filter2PanSource')
            ], 'filter2Frame')

        self.createRefContainer('Filter Env.', [
            (6, 'Filt', 'filterEnvelopeMode')
            ], [
            (34, 'Attack', 'filterEnvelopeAttack'), 
            (35, 'Decay', 'filterEnvelopeDecay'), 
            (36, 'Sustain', 'filterEnvelopeSustain'), 
            (37, 'Release', 'filterEnvelopeRelease'), 
            ], 'filterEnvelopeFrame')

        self.createRefContainer('Amp Env.', [
            (7, 'Amp', 'amplifierEnvelopeMode')
            ], [
            (38, 'Attack', 'amplifierEnvelopeAttack'), 
            (39, 'Decay', 'amplifierEnvelopeDecay'), 
            (40, 'Sustain', 'amplifierEnvelopeSustain'), 
            (41, 'Release', 'amplifierEnvelopeRelease'), 
            ], 'amplifierEnvelopeFrame')

        self.createRefContainer('Envelope 3', [
            (8, 'Env3', 'envelope3Mode')
            ], [
            (42, 'Attack', 'envelope3Attack'), 
            (43, 'Decay', 'envelope3Decay'), 
            (44, 'Sustain', 'envelope3Sustain'), 
            (45, 'Release', 'envelope3Release'), 
            ], 'envelope3Frame')

        self.createRefContainer('Envelope 4', [
            (9, 'Env4', 'envelope4Mode')
            ], [
            (46, 'Attack', 'envelope4Attack'), 
            (47, 'Decay', 'envelope4Decay'), 
            (48, 'Sustain', 'envelope4Sustain'), 
            (49, 'Release', 'envelope4Release'), 
            ], 'envelope4Frame')

        self.createLayoutContainer('Keyboard', [
            (10, 'Keytrack', (0, 0)), 
            (11, 'Velocity', (0, 1)), 
            (12, 'RelVel', (0, 2)), 
            (13, 'Press', (0, 3)), 
            (14, 'PolyPress', (0, 4)), 
            (15, 'PitchBend', (1, 0)), 
            (16, 'ModWheel', (1, 1)), 
            (17, 'Sustain', (1, 2)), 
            (18, 'FootCtrl', (1, 3)), 
            (19, 'BreathCtrl', (1, 4)), 
            ], [], 'pianoKeyboard', Left, Right)

        self.createLayoutContainer('General', [
            (20, 'CtrlW', (0, 3)), 
            (21, 'CtrlX', (1, 3)), 
            (22, 'CtrlY', (2, 3)), 
            (23, 'CtrlZ', (3, 3)), 
            (24, 'Unisono', (3, 5)), 
            (25, 'Modifier1', (0, 0)), 
            (26, 'Modifier2', (1, 0)), 
            (27, 'Modifier3', (2, 0)), 
            (28, 'Modifier4', (3, 0)), 
            (29, 'minimum', (0, 5)), 
            (30, 'Maximum', (0, 6)), 
            ], [
            (50, 'M1 Amount', (0, 1)), 
            (51, 'M2 Amount', (1, 1)), 
            (52, 'M3 Amount', (2, 1)), 
            (53, 'M4 Amount', (3, 1)), 
            (0, 'Pitch', (2, 5)), 
            (30, 'Volume', (2, 6)), 
            ], 'arpEfxStackedWidget', Left, Right)

#        self.createLayoutContainer('Pitch', [], [(0, 'Pitch')])
#        self.createLayoutContainer('CtrlW', [(20, 'CtrlW', Top)], [])
#        self.createLayoutContainer('CtrlX', [(21, 'CtrlX', Top)], [])
#        self.createLayoutContainer('CtrlY', [(22, 'CtrlY', Top)], [])
#        self.createLayoutContainer('CtrlZ', [(23, 'CtrlZ', Top)], [])
#        self.createLayoutContainer('Unisono', [(24, 'Unisono', Right)], [])
#        self.createLayoutContainer('Modifier1', [(25, 'Modifier1', Top)], [(50, 'Amount', Top)])
#        self.createLayoutContainer('Modifier2', [(26, 'Modifier2', Top)], [(51, 'Amount', Top)])
#        self.createLayoutContainer('Modifier3', [(27, 'Modifier3', Top)], [(52, 'Amount', Top)])
#        self.createLayoutContainer('Modifier4', [(28, 'Modifier4', Top)], [(53, 'Amount', Top)])
#        self.createLayoutContainer('Volume', [], [(30, 'Vol', Left)])
#        self.createLayoutContainer('minimum', [(29, 'minimum', Top)], [])
#        self.createLayoutContainer('Maximum', [(30, 'Maximum', Top)], [])


class ModMatrixView(QtWidgets.QGraphicsView):
    modAnimationChanged = QtCore.pyqtSignal(bool)
    modFocusChanged = QtCore.pyqtSignal(bool)
    modShadowChanged = QtCore.pyqtSignal(bool)
    closeModMatrix = QtCore.pyqtSignal()
    shown = False

    def __init__(self, editorWindow):
        QtWidgets.QGraphicsView.__init__(self, editorWindow)
        self.editorWindow = editorWindow
        self.main = QtWidgets.QApplication.instance()

        self.setRenderHints(QtGui.QPainter.Antialiasing)
        self.setContentsMargins(0, 0, 0, 0)
        self.setFrameShape(0)
        #inherit base background color, we need it for the "minimized" modDialog background workaround
        disColor = self.palette().color(QtGui.QPalette.Window)
        self.setStyleSheet('''
            ModMatrixView {{
                background: rgba(96, 96, 96, 128);
                border-width: 0px;
            }}
            ModMatrixView:disabled {{
                background: {dis};
            }}
            QFrame {{
                border: none;
                padding: 0px;
                margin: 0px;
            }}
            '''.format(dis='rgb({}, {}, {})'.format(*disColor.getRgb()[:3])))

        scene = ModMatrixScene(self.editorWindow)
        self.setScene(scene)
        scene.closeModMatrix.connect(self.closeModMatrix)

        self.settings = QtCore.QSettings()
        scene.setAnimationState(self.settings.value('modAnimation', True, bool))
        scene.setOpacityState(self.settings.value('modFocus', True, bool))
        scene.setShadowState(self.settings.value('modShadows', True, bool))
        scene.panel.modAnimation.connect(self.modAnimationChanged)
        scene.panel.modFocus.connect(self.modFocusChanged)
        scene.panel.modShadow.connect(self.modShadowChanged)

        self.modObjects = []
        for m in range(16):
            paramId = 261 + m * 3
            sourceId = self.editorWindow.parameters[paramId]
            destinationId = self.editorWindow.parameters[paramId + 1]
            amount = self.editorWindow.parameters[paramId + 2]
            if sourceId > 0:
                scene.createMod(m, sourceId, destinationId, amount)
            modSourceObj = ModulationObject(scene, m, 0, sourceId)
            modDestObj = ModulationObject(scene, m, 1, destinationId)
            modAmountObj = ModulationObject(scene, m, 2, amount)
            setattr(self, modSourceObj.objectName(), modSourceObj)
            setattr(self, modDestObj.objectName(), modDestObj)
            setattr(self, modAmountObj.objectName(), modAmountObj)
            self.modObjects.append((modSourceObj, modDestObj, modAmountObj))
            scene.modulationChanged.emit(m, sourceId, destinationId, amount)
        scene.modulationChanged.connect(self.emitModulationChanged)
        scene.amountChanged.connect(lambda modId, amount: self.emitModulationChanged(modId, -1, -1, amount))

        self.modifierObjects = []
        for m in range(4):
            paramId = 245 + m * 4
            sourceA = self.editorWindow.parameters[paramId]
            sourceB = self.editorWindow.parameters[paramId + 1]
            operator = self.editorWindow.parameters[paramId + 2]
            constant = self.editorWindow.parameters[paramId + 3]
            sourceACombo, sourceBCombo, operatorCombo, constantCombo = scene.modifiersDialogProxy.dialog.modifiers[m]
            sourceACombo.setValue(sourceA)
            sourceBCombo.setValue(sourceB)
            operatorCombo.setValue(operator)
            constantCombo.setValue(constant)
            sourceAObj = ModifierObject(scene, m, 0, sourceACombo, sourceA)
            sourceBObj = ModifierObject(scene, m, 1, sourceBCombo, sourceB)
            operatorObj = ModifierObject(scene, m, 2, operatorCombo, operator)
            constantObj = ModifierObject(scene, m, 3, constantCombo, constant)
            setattr(self, sourceAObj.objectName(), sourceAObj)
            setattr(self, sourceBObj.objectName(), sourceBObj)
            setattr(self, operatorObj.objectName(), operatorObj)
            setattr(self, constantObj.objectName(), constantObj)
            self.modifierObjects.append((sourceAObj, sourceBObj, operatorObj, constantObj))

    def showEvent(self, event):
        if self.scene().animationState:
            self.scene().animationTimer.start()
        if not self.shown:
            self.shown = False
            self.scene().modTable.scrollToTop()

    def hideEvent(self, event):
        self.scene().animationTimer.stop()

    def emitModulationChanged(self, modId, source, destination, amount):
#        print(modId, source, destination, amount)
        modSourceObj, modDestObj, modAmountObj = self.modObjects[modId]
        self.scene().modulationChanged.disconnect(self.emitModulationChanged)
        if source >= 0:
            modSourceObj.valueChanged.emit(source)
#        else:
#            self.scene().modulationChanged.connect(self.emitModulationChanged)
#            return
        if destination >= 0:
            modDestObj.valueChanged.emit(destination)
        if amount >= 0:
            modAmountObj.valueChanged.emit(amount)
        self.scene().modulationChanged.connect(self.emitModulationChanged)

    def resizeEvent(self, event):
        self.scene().setSceneRect(QtCore.QRectF(self.viewport().rect()))

if __name__ == '__main__':
    import sys
    from PyQt4 import uic
    sys.path.append(os.path.expanduser('~/data/code/blofeld/'))
    from bigglesworth.parameters import Parameters

    class EditorWindow(QtWidgets.QMainWindow):
        def __init__(self):
            QtWidgets.QMainWindow.__init__(self)
            uic.loadUi(os.path.expanduser('~/data/code/blofeld/wip/editorTemp.ui'), self)
            self.parameters = {p: 0 for p in range(389)}
            self.posLabel = QtWidgets.QLabel()
            self.statusBar().addPermanentWidget(self.posLabel)

        def eventFilter(self, source, event):
            if event.type() == QtCore.QEvent.HoverMove:
#                self.statusBar().showMessage('{}, {}'.format(event.pos().x(), event.pos().y()))
                self.posLabel.setText('{}, {}'.format(event.pos().x(), event.pos().y()))
            return QtWidgets.QMainWindow.eventFilter(self, source, event)

        def resizeEvent(self, event):
            self.modMatrix.resize(self.centralWidget().size())

    class EditorMenuBar(QtWidgets.QMenuBar):
        pass

    app = QtWidgets.QApplication(sys.argv)


    ew = EditorWindow()
    ew.editorMenuBar = EditorMenuBar()
    ew.editorMenuBar.addAction('test sdfgdfgdfg')
    ew.modMatrix = ModMatrixView(ew)
    ew.modMatrix.show()
    ew.modMatrix.installEventFilter(ew)
    ew.show()
    sys.exit(app.exec_())

