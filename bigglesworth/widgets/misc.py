import sys
from bisect import bisect_left

from Qt import QtCore, QtGui, QtWidgets
from PyQt4.QtGui import QStyleOptionTabV3, QStyleOptionTabWidgetFrameV2
QtWidgets.QStyleOptionTabV3 = QStyleOptionTabV3
QtWidgets.QStyleOptionTabWidgetFrameV2 = QStyleOptionTabWidgetFrameV2

class TabPlaceHolder(QtWidgets.QWidget):
    arrowTop = QtGui.QPainterPath()
    arrowTop.moveTo(-4, 0)
    arrowTop.lineTo(4, 0)
    arrowTop.lineTo(0, 4)
    arrowTop.closeSubpath()

    arrowBottom = QtGui.QPainterPath()
    arrowBottom.moveTo(-4, 0)
    arrowBottom.lineTo(4, 0)
    arrowBottom.lineTo(0, -4)
    arrowBottom.closeSubpath()

    def __init__(self, parent):
        self.tabBar = parent
        if isinstance(parent.parent(), QtWidgets.QTabWidget):
            parent = parent.parent()
        QtWidgets.QWidget.__init__(self, parent)
        self.setVisible(False)
        self.setFixedWidth(9)

    def showEvent(self, event):
        height = self.tabBar.height()
        if isinstance(self.parent(), QtWidgets.QTabWidget):
            height += 14
        self.setFixedHeight(self.tabBar.height())

    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        qp.setRenderHints(qp.Antialiasing)
        qp.setPen(QtCore.Qt.NoPen)
        qp.setBrush(self.palette().color(QtGui.QPalette.ButtonText))
        qp.translate(self.rect().center().x() + .5, .5)
        qp.drawPath(self.arrowTop)
        qp.translate(0, self.height() - 1)
        qp.drawPath(self.arrowBottom)


class DroppableTabBar(QtWidgets.QTabBar):
    def __init__(self, *args, **kwargs):
        QtWidgets.QTabBar.__init__(self, *args, **kwargs)
        self.placeHolder = TabPlaceHolder(self)

    def setDropIndexAt(self, pos):
        tabIndex = self.tabAt(self.mapFromParent(pos))
        if tabIndex < 0:
            tabIndex += self.count()
        rect = self.tabRect(tabIndex)
        if pos.x() > rect.center().x():
            tabIndex += 1
            if tabIndex < self.count():
                x = self.tabRect(tabIndex).left()
            else:
                x = rect.right()
        else:
            x = rect.left()
        self.placeHolder.move(x, rect.top())
        return tabIndex


class ShrinkButton(QtWidgets.QPushButton):
    _text = ''
    shrunk = False

    def setText(self, text):
        self._text = text
        self.checkShrink()
#        QtWidgets.QPushButton.setText(self, text)

    def setShrunk(self, shrunk):
        if shrunk == self.shrunk and ((shrunk and not self.text()) or (not shrunk and self.text())):
            return
        QtWidgets.QPushButton.setText(self, self._text if not shrunk else '')

    def checkShrink(self):
        possible = self.fontMetrics().boundingRect(self.rect(), QtCore.Qt.AlignCenter, self._text).width() + self.iconSize().width() * 2
        self.setShrunk(possible > self.width())

    def resizeEvent(self, event):
        if self.isVisible():
            self.checkShrink()


class IconSelector(QtWidgets.QToolButton):
    dirIterator = QtCore.QDirIterator(':', QtCore.QDirIterator.Subdirectories)
    icons = set()
    images = {}
    while dirIterator.hasNext():
        dirIterator.next()
        if dirIterator.filePath().startswith(':/icons') and dirIterator.fileInfo().isFile():
            icons.add(dirIterator.fileInfo().completeBaseName())
        elif dirIterator.filePath().startswith(':/images') and dirIterator.fileInfo().isFile():
            images[dirIterator.fileName()] = dirIterator.filePath()
    icons.discard('photo')
    icons = sorted(icons)
    icons.insert(0, 'photo')
    icons.insert(0, '')
    currentIndex = 1

    iconChanged = QtCore.pyqtSignal([QtGui.QIcon], [str])

    def __init__(self, *args, **kwargs):
        QtWidgets.QToolButton.__init__(self, *args, **kwargs)
        menu = QtWidgets.QMenu(self)
        for iconName in self.icons:
            icon = QtGui.QIcon.fromTheme(iconName)
            if not icon.isNull() or not iconName:
                iconAction = menu.addAction(QtGui.QIcon.fromTheme(iconName), '')
                iconAction.triggered.connect(self.setCurrentIcon)
                iconAction.setData(iconName)
        self.setMenu(menu)
        self.clicked.connect(lambda: menu.exec_(QtGui.QCursor.pos()))

    def iconName(self):
        return self.icons[self.currentIndex]

    def setIconName(self, name=''):
        try:
            self.currentIndex = self.icons.index(name)
            self.setIcon(QtGui.QIcon.fromTheme(name))
        except:
            self.currentIndex = 0
            self.setIcon(QtGui.QIcon())

    def setCurrentIcon(self):
        icon = self.sender().icon()
        self.setIcon(icon)
        self.currentIndex = self.icons.index(self.sender().data())
        if sys.platform == 'darwin':
            self.iconChanged[str].emit(self.icons[self.currentIndex])
        else:
            self.iconChanged.emit(icon)

    def wheelEvent(self, event):
        if event.delta() < 0:
            delta = 1
        else:
            delta = -1
        self.currentIndex = max(0, min(self.currentIndex + delta, len(self.icons) - 1))
        icon = QtGui.QIcon.fromTheme(self.icons[self.currentIndex])
        self.setIcon(icon)
        if sys.platform == 'darwin':
            self.iconChanged[str].emit(self.icons[self.currentIndex])
        else:
            self.iconChanged.emit(icon)


class DeltaSpin(QtWidgets.QSpinBox):
    delta = 0

    def textFromValue(self, value):
        return str(value + self.delta)

    def valueFromText(self, text):
        try:
            value = int(text) - self.delta
        except:
            value = self.value()
        self.setValue(value)


class DeviceIdSpin(QtWidgets.QSpinBox):
    def textFromValue(self, value):
        if value == 127:
            return 'Broadcast'
        return str(value)


class DevicePopupSpin(QtWidgets.QDoubleSpinBox):
    values = [0, .1, .2, .3, .4, .6, .7, .8, .9, 1.1, 1.2, 1.3, 1.4, 1.5, 1.7, 1.8, 1.9, 2, 2.2, 2.3, 2.4, 2.5, 2.6, 2.8, 2.9,
        3, 3.1, 3.3, 3.4, 3.5, 3.6, 3.8, 3.9, 4, 4.1, 4.2, 4.4, 4.5, 4.6, 4.7, 4.9, 5, 5.1, 5.2, 5.3, 5.5, 5.6, 5.7, 5.8, 
        6, 6.1, 6.2, 6.3, 6.5, 6.6, 6.7, 6.8, 6.9, 7.1, 7.2, 7.3, 7.4, 7.6, 7.7, 7.8, 7.9, 8, 8.2, 8.3, 8.4, 8.5, 8.7, 8.8, 8.9, 
        9, 9.1, 9.3, 9.4, 9.5, 9.6, 9.8, 9.9, 10, 10.1, 10.3, 10.4, 10.5, 10.6, 10.7, 10.9, 11, 11.1, 11.2, 11.4, 11.5, 11.6, 11.7, 11.8, 
        12, 12.1, 12.2, 12.3, 12.5, 12.6, 12.7, 12.8, 13, 13.1, 13.2, 13.3, 13.4, 13.6, 13.7, 13.8, 13.9, 
        14.1, 14.2, 14.3, 14.4, 14.5, 14.7, 14.8, 14.9, 15, 15.2, 15.3, 15.4, 15.5]
    locale = QtCore.QLocale.system()
    decimalPoint = locale.decimalPoint()
    textValues = []
    for v in values:
        text = locale.toString(v)
        if not decimalPoint in text:
            text += decimalPoint + '0'
        textValues.append(text)

    def textFromValue(self, value):
        return self.textValues[int(value)]

    def valueFromText(self, text):
        if text.endswith('s'):
            text = text[:-1]
        value, valid = self.locale.toFloat(text)
        if not valid:
            return self.value()
        pos = bisect_left(self.values, value)
        if pos <= 1:
            return 1
        if pos == len(self.values):
            return 127
        before = self.values[pos - 1]
        after = self.values[pos]
        if after - value < value - before:
            return pos
        return pos - 1


class LedWidget(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        QtWidgets.QWidget.__init__(self, *args, **kwargs)
        self.active = False
        self.setFixedSize(24, 10)
        self.timer = QtCore.QTimer()
        self.timer.setSingleShot(True)
        self.timer.setInterval(250)
        self.timer.timeout.connect(self.deactivate)

    def activate(self):
        self.brush = self.activeBrush
        self.update()
        self.timer.start()

    def deactivate(self):
        self.brush = self.inactiveBrush
        self.update()

    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        qp.setRenderHints(qp.Antialiasing)
        qp.translate(.5, .5)
        qp.setPen(self.pen)
        qp.setBrush(self.brush)
        qp.drawEllipse(0, 0, 8, 8)
        qp.translate(self.width() - 12, 0)
        qp.setPen(self.window().palette().color(QtGui.QPalette.Active, QtGui.QPalette.WindowText))
        qp.setBrush(QtCore.Qt.NoBrush)
        qp.drawPath(self.connPath)


class LedInWidget(LedWidget):
    pen = QtGui.QColor(QtCore.Qt.darkRed)
    inactiveBrush = QtGui.QRadialGradient(.5, .5, .6, .3, .3)
    inactiveBrush.setCoordinateMode(inactiveBrush.ObjectBoundingMode)
    inactiveBrush.setColorAt(0, QtGui.QColor(140, 80, 80))
    inactiveBrush.setColorAt(1, QtGui.QColor(80, 0, 0))
    activeBrush = QtGui.QRadialGradient(.5, .5, .5, .3, .3)
    activeBrush.setCoordinateMode(activeBrush.ObjectBoundingMode)
    activeBrush.setColorAt(0, QtGui.QColor(255, 160, 160))
    activeBrush.setColorAt(1, QtGui.QColor(255, 0, 0))
    brush = inactiveBrush

    connPath = QtGui.QPainterPath()
    connPath.moveTo(0, 4)
    connPath.lineTo(4, 4)
    connPath.moveTo(2, 4)
    connPath.arcMoveTo(2, 1, 6, 6, 135)
    connPath.arcTo(2, 1, 6, 6, 135, -270)


class LedOutWidget(LedWidget):
    pen = QtGui.QColor(QtCore.Qt.darkGreen)
    inactiveBrush = QtGui.QRadialGradient(.5, .5, .6, .3, .3)
    inactiveBrush.setCoordinateMode(inactiveBrush.ObjectBoundingMode)
    inactiveBrush.setColorAt(0, QtGui.QColor(80, 140, 80))
    inactiveBrush.setColorAt(1, QtGui.QColor(0, 80, 0))
    activeBrush = QtGui.QRadialGradient(.5, .5, .5, .3, .3)
    activeBrush.setCoordinateMode(activeBrush.ObjectBoundingMode)
    activeBrush.setColorAt(0, QtGui.QColor(160, 255, 160))
    activeBrush.setColorAt(1, QtGui.QColor(0, 255, 0))
    brush = inactiveBrush

    connPath = QtGui.QPainterPath()
    connPath.moveTo(9, 4)
    connPath.arcMoveTo(1, 1, 6, 6, 45)
    connPath.arcTo(1, 1, 6, 6, 45, 270)
    connPath.moveTo(5, 4)
    connPath.lineTo(9, 4)


class MidiStatusBarWidget(QtWidgets.QFrame):
    midiConnect = QtCore.pyqtSignal(object, int, bool)

    def __init__(self, parent, directions=3, menu=False):
        QtWidgets.QFrame.__init__(self, parent)
        self.setFrameStyle(self.StyledPanel|self.Sunken)
        layout = QtWidgets.QHBoxLayout()
        self.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)
        self.widgets = []
        if directions & 1:
            self.inputWidget = MidiStatusBarIcon('input')
            layout.addWidget(self.inputWidget)
#            self.inputWidget.customContextMenuRequested.connect(lambda: self.showMenu(0))
            self.widgets.append(self.inputWidget)
        else:
            self.inputWidget = None
            self.midiInputEvent = self.midiInputConnChanged = lambda *args: None
        if directions & 2:
            self.outputWidget = MidiStatusBarIcon('output')
            layout.addWidget(self.outputWidget)
#            self.outputWidget.customContextMenuRequested.connect(lambda: self.showMenu(1))
            self.widgets.append(self.outputWidget)
            self.midiEventSent = self.outputWidget.activate
        else:
            self.outputWidget = None
            self.midiOutputEvent = self.midiOutputConnChanged = self.midiEventSent = lambda *args: None
        self.menuEnabled = menu
        self.midiDevice = None

    def setMenuEnabled(self, enable):
        self.menuEnabled = enable

    def setMidiDevice(self, midiDevice):
        self.midiDevice = midiDevice
        self.graph = midiDevice.graph
        signals = self.graph.client_start, self.graph.client_exit, self.graph.port_start, self.graph.port_exit
        for widget in self.widgets:
            for signal in signals:
                signal.connect(widget.graphChanged)
        if self.inputWidget:
            midiDevice.midi_event.connect(self.inputWidget.activate)

    def getPortCount(self, direction=None):
        if not self.midiDevice:
            return 0
        inPorts = outPorts = 0
#        direction = int(direction == 'output')
        for portDict in self.graph.port_id_dict.values():
            for port in portDict.values():
                if port.hidden or port.client in (self.midiDevice.input.client, self.midiDevice.output.client):
                    continue
                elif port.is_input:
                    outPorts += 1
                elif port.is_output:
                    inPorts += 1
        if direction is None:
            return inPorts, outPorts
        elif direction:
            return inPorts
        return outPorts

    def contextMenuEvent(self, event):
        if self.menuEnabled:
            widget = self.childAt(event.pos())
            if widget:
                if widget == self.inputWidget:
                    menu = self.getMenu(0)
                else:
                    menu = self.getMenu(1)
                menu.exec_(event.globalPos())

    def getMenu(self, direction):
        menu = QtWidgets.QMenu()
        if not self.midiDevice:
            menu.addAction('Fake port')
            return menu
        sections = self.midiDevice.backend == self.midiDevice.Alsa
        if direction:
            connected = [conn.dest for conn in QtWidgets.QApplication.instance().connections[1]]
        else:
            connected = [conn.src for conn in QtWidgets.QApplication.instance().connections[0]]
        for clientId in sorted(self.graph.client_id_dict.keys()):
            client = self.graph.client_id_dict[clientId]
            if client in (self.midiDevice.input.client, self.midiDevice.output.client):
                continue
            portDict = self.graph.port_id_dict[clientId]
            ports = []
            for portId in sorted(portDict.keys()):
                port = portDict[portId]
                if not port.hidden and ((direction and port.is_input) or (not direction and port.is_output)):
                    ports.append(port)
            if ports:
                if sections:
                    menu.addSection(client.name)
                for port in ports:
                    portAction = menu.addAction(port.name)
                    portAction.setCheckable(True)
                    portAction.setChecked(port in connected)
                    portAction.setData(port)
                    portAction.triggered.connect(
                        lambda action, direction=direction, port=port: self.midiConnect.emit(port, direction, action))
        return menu
#        res = menu.exec_(QtGui.QCursor.pos())
#        if res:
#            self.midiConnect.emit(res.data(), direction, res.isChecked())

    def midiConnChanged(self, input, output, update=False):
        if update:
            inPorts, outPorts = self.getPortCount()
        else:
            inPorts = outPorts = None
        self.midiInputConnChanged(input, inPorts)
        self.midiOutputConnChanged(output, outPorts)

    def midiInputEvent(self):
        self.inputWidget.activate()

    def midiInputConnChanged(self, conn, inPorts=None):
        self.inputWidget.setConn(conn, inPorts)

    def midiOutputEvent(self):
        self.outputWidget.activate()

    def midiOutputConnChanged(self, conn, outPorts=None):
        self.outputWidget.setConn(conn, outPorts)


class MidiStatusBarIcon(QtWidgets.QLabel):
    shown = False

    def __init__(self, dirText):
        QtWidgets.QLabel.__init__(self)
#        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.dirText = dirText
        self.direction = dirText == 'output'
        self.icon = self.normalIcon = QtGui.QIcon(':/images/midiicon{}.svg'.format(dirText))
        self.disabledIcon = QtGui.QIcon(':/images/midiicon{}disabled.svg'.format(dirText))
        self.activeIcon = QtGui.QIcon(':/images/midiicon{}active.svg'.format(dirText))
        self.icons = {
            -1: self.disabledIcon, 
            0: self.normalIcon, 
            1: self.activeIcon
        }
        self.timer = QtCore.QTimer()
        self.timer.setSingleShot(True)
        self.timer.setInterval(150)
        self.timer.timeout.connect(lambda: self.setState(0))
        self.count = 0
        self.ports = 0

    def activate(self):
        self.setState(1)
        self.timer.start()

    def setIcon(self):
        if self.shown:
            self.setPixmap(self.icon.pixmap(self.height()))
            self.update()

    def graphChanged(self):
        self.ports = self.parent().getPortCount(self.direction)
        self.updateToolTip()

    def updateToolTip(self):
        toolTip = '{} {} connection{}'.format(self.count, self.dirText, '' if self.count == 1 else 's')
        if self.parent().midiDevice:
            toolTip += ' ({} available)'.format(self.ports)
        if self.parent().menuEnabled:
            toolTip += '\nRight click for menu'
        self.setToolTip(toolTip)

    def setConn(self, conn, ports=None):
        self.count = len([c for c in conn if not c.hidden])
        if ports is not None:
            self.ports = ports
        self.updateToolTip()
        self.setState(0 if conn else -1)

    def setState(self, state):
        self.icon = self.icons[state]
        self.setIcon()

    def showEvent(self, event):
        if not self.shown:
            self.shown = True
            self.setIcon()

    def resizeEvent(self, event):
        self.setIcon()


class MidiToolBox(QtWidgets.QWidget):
    offState = 180, 180, 180
    onState = 60, 255, 60
    pens = offState, onState

    def __init__(self):
        QtWidgets.QWidget.__init__(self)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Maximum))
        self.compute()
        self.progState = False
        self.ctrlState = False

    def compute(self):
        self.smallFont = self.font()
        self.smallFont.setBold(True)
        self.smallFont.setPointSize(self.smallFont.pointSize() * .5 + 1)
        self.smallFontMetrics = QtGui.QFontMetrics(self.smallFont)
        self.boundingRect = QtCore.QRect(0, 0, self.smallFontMetrics.width('CTRL'), self.smallFontMetrics.height() * 2)
        self.update()

    def setProgState(self, state):
        self.progState = state
        self.update()

    def setCtrlState(self, state):
        self.ctrlState = state
        self.update()

    def changeEvent(self, event):
        if event.type() == QtCore.QEvent.FontChange:
            self.compute()
        elif event.type() == QtCore.QEvent.PaletteChange:
            self.offState.setRgb(self.palette().color(QtGui.QPalette.Disabled, QtGui.QPalette.WindowText))
            self.onState.setRgb(self.palette().color(QtGui.QPalette.Active, QtGui.QPalette.WindowText))
        return QtWidgets.QWidget.changeEvent(self, event)

    def sizeHint(self):
        return self.boundingRect.size()

    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        qp.setFont(self.smallFont)
        progPen = QtGui.QColor(*self.pens[self.progState])
        ctrlPen = QtGui.QColor(*self.pens[self.ctrlState])
        if not self.isEnabled():
            progPen.setAlphaF(.5)
            ctrlPen.setAlphaF(.5)
        qp.setPen(progPen)
        qp.drawText(self.rect(), QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop, 'PGM')
        qp.translate(0, 1)
        qp.setPen(ctrlPen)
        qp.drawText(self.rect(), QtCore.Qt.AlignLeft|QtCore.Qt.AlignBottom, 'CTRL')

    def resizeEvent(self, event):
        self.compute()


class MidiWidget(QtWidgets.QFrame):
    clicked = QtCore.pyqtSignal()
    baseStyleSheet = '''
        MidiWidget {
            border: 1px solid transparent;
        }
        MidiWidget:hover {
            border-radius: 2px;
            border-left: 1px solid palette(midlight);
            border-right: 1px solid palette(mid);
            border-top: 1px solid palette(midlight);
            border-bottom: 1px solid palette(mid);
        }'''
    pressedStyleSheet = '''
        MidiWidget {
            border-radius: 2px;
            border-left: 1px solid palette(mid);
            border-right: 1px solid palette(midlight);
            border-top: 1px solid palette(mid);
            border-bottom: 1px solid palette(midlight);
        }'''

    def __init__(self, direction):
        QtWidgets.QFrame.__init__(self)
        layout = QtWidgets.QHBoxLayout()
        self.setLayout(layout)
        layout.setSpacing(2)
        layout.setContentsMargins(2, 1, 2, 1)

        self.direction = direction
        if direction:
            self.ledWidget = LedOutWidget()
            text = 'OUT'
        else:
            self.ledWidget = LedInWidget()
            text = 'IN'
        layout.addWidget(self.ledWidget)
        self.label = QtWidgets.QLabel(text + ' (0)')
        self.label.setEnabled(False)
        layout.addWidget(self.label)

        self.toolBox = MidiToolBox()
        layout.addWidget(self.toolBox)

        self.setStyleSheet(self.baseStyleSheet)
        self.count = 0
        self.setProgState = self.toolBox.setProgState
        self.setCtrlState = self.toolBox.setCtrlState

    def setConnections(self, count):
        self.count = count
        self.label.setText('{} ({})'.format('OUT' if self.direction else 'IN', int(count)))
        self.label.setEnabled(False if count else True)
        self.toolBox.setEnabled(True if count else False)

    def mousePressEvent(self, event):
        self.setStyleSheet(self.pressedStyleSheet)

    def mouseMoveEvent(self, event):
        self.setStyleSheet(self.pressedStyleSheet if event.pos() in self.rect() else self.baseStyleSheet)

    def mouseReleaseEvent(self, event):
        self.setStyleSheet(self.baseStyleSheet)
        if event.pos() in self.rect():
            self.clicked.emit()

    def leaveEvent(self, event):
        QtWidgets.QFrame.leaveEvent(self, event)
        self.setStyleSheet(self.baseStyleSheet)

    def activate(self):
        if self.count:
            self.ledWidget.activate()


class MidiInWidget(MidiWidget):
    def __init__(self, *args, **kwargs):
        MidiWidget.__init__(self, False)


class MidiOutWidget(MidiWidget):
    def __init__(self, *args, **kwargs):
        MidiWidget.__init__(self, True)


class VerticalLabel(QtWidgets.QLabel):
    def sizeHint(self):
        size = QtWidgets.QLabel.sizeHint(self)
        return QtCore.QSize(size.height(), size.width())

    def minimumSizeHint(self):
        size = QtWidgets.QLabel.minimumSizeHint(self)
        return QtCore.QSize(size.height(), size.width())

    def paintEvent(self, event):
        rect = QtCore.QRect(0, 0, self.height(), self.width())
#        print(self.rect(), rect)
#        textRect = self.fontMetrics().boundingRect(rect, QtCore.Qt.TextExpandTabs, self.text())
        qp = QtGui.QPainter(self)
        qp.rotate(-90)
        qp.translate(-self.rect().height(), 0)
        qp.drawText(rect, self.alignment(), self.text())



class Waiter(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        QtWidgets.QWidget.__init__(self, *args, **kwargs)
        self.timerRect = QtCore.QRect(0, 0, 31, 31)
        self.color = self.palette().color(QtGui.QPalette.WindowText)
        self.pen = QtGui.QPen(self.color, 2, cap=QtCore.Qt.FlatCap)
        self.timer = QtCore.QTimer()
        self.timer.setInterval(30)
        self.timer.timeout.connect(self.update)
        self.elapsedTimer = QtCore.QElapsedTimer()
        self.elapsedTimer.start()
        self.setMinimumSize(48, 48)
        self._active = True

    @property
    def active(self):
        return self._active

    @active.setter
    def active(self, active):
        self._active = active
        if active and self.isVisible():
            self.timer.start()
        else:
            self.timer.stop()

    def showEvent(self, event):
        if self.active:
            self.timer.start()

    def hideEvent(self, event):
        self.timer.stop()

    def sizeHint(self):
        return QtCore.QSize(48, 48)

    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        qp.translate(.5, .5)
        qp.setRenderHints(qp.Antialiasing)
        qp.setBrush(self.palette().color(QtGui.QPalette.WindowText))
#        qp.drawEllipse(self.timerRect)
#        qp.setPen(self.pen)
#        adjustSize = self.timerRect.width() * .05
        secs, rest = divmod(self.elapsedTimer.elapsed() * .001, 1)
        if int(secs) & 1:
            qp.drawPie(self.timerRect, 1440, -rest * 5760)
        else:
            qp.drawPie(self.timerRect, 1440, 5760 - rest * 5760)
#        if not rest:
#            qp.drawEllipse(self.timerRect.adjusted(adjustSize, adjustSize, -adjustSize, -adjustSize))
#        else:
#            qp.drawArc(self.timerRect.adjusted(adjustSize, adjustSize, -adjustSize, -adjustSize), 1440, -rest * 5760)

    def resizeEvent(self, event):
        size = min(self.width(), self.height()) - 1
        self.timerRect = QtCore.QRect((self.width() - size) * .5, (self.height() - size) * .5, size, size)
        self.pen.setWidth(size * .1)


class ExpandButton(QtWidgets.QPushButton):
    _expanded = False
    expanded = QtCore.pyqtSignal(bool)
    arrowPath = arrowPathDown = QtGui.QPainterPath()
    arrowPathDown.moveTo(-6, -3)
    arrowPathDown.lineTo(0, 3)
    arrowPathDown.lineTo(6, -3)
    arrowPathUp = QtGui.QPainterPath()
    arrowPathUp.moveTo(-6, 3)
    arrowPathUp.lineTo(0, -3)
    arrowPathUp.lineTo(6, 3)

    def __init__(self, *args, **kwargs):
        QtWidgets.QPushButton.__init__(self, *args, **kwargs)
        self.clicked.connect(self.toggleExpand)

    def toggleExpand(self):
        self._expanded = not self._expanded
        self.arrowPath = self.arrowPathUp if self._expanded else self.arrowPathDown
        self.expanded.emit(self._expanded)
        self.update()

    def setExpanded(self, expanded):
        if expanded == self._expanded:
            return
        self._expanded = expanded
        self.arrowPath = self.arrowPathUp if self._expanded else self.arrowPathDown
        self.update()

    def showEvent(self, event):
        palette = self.window().palette()
        self.setPalette(palette)
        self.setStyleSheet('''
            ExpandButton {
                border: 1px solid palette(mid);
                border-radius: 2px;
                border-style: outset;
            }
            ExpandButton:pressed {
                border-color: palette(mid);
                border-style: inset;
            }
        ''')
        self.pen = QtGui.QPen(palette.color(QtGui.QPalette.Mid), 2, cap=QtCore.Qt.RoundCap)

    def paintEvent(self, event):
        QtWidgets.QPushButton.paintEvent(self, event)
        qp = QtGui.QPainter(self)
        qp.setPen(self.pen)
        width = self.width()
        count = width / 64
        ratio = width / count
        left = int(width - ratio * count + ratio * .5) + .5
        ratio = int(ratio)
        qp.translate(left, self.height() / 2 - .5)
        for i in range(count):
            qp.drawPath(self.arrowPath)
            qp.translate(ratio, 0)


