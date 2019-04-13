import os

os.environ['QT_PREFERRED_BINDING'] = 'PyQt4'

from Qt import QtCore, QtGui, QtWidgets

from bigglesworth.utils import sanitize


class FakeToolBarHandle(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        QtWidgets.QWidget.__init__(self, *args, **kwargs)
        self.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Preferred)
        try:
            self.setMinimumSize(self._option.rect.size())
        except:
            self.setMinimumSize(1, 1)
            self._option = self.__class__._option = QtWidgets.QStyleOptionToolBar()
            self._option.initFrom(self)
            self._option.features = self._option.Movable
            self._option.toolBarArea = QtCore.Qt.TopToolBarArea
            self._option.positionOfLine = self._option.Beginning
            self._option.state |= QtWidgets.QStyle.State_Horizontal
            self._option.positionWithinLine = self._option.Beginning
            self._option.rect.setWidth(self.style().pixelMetric(QtWidgets.QStyle.PM_ToolBarHandleExtent, QtWidgets.QStyleOptionToolBar(), self))
            self.setMinimumSize(self._option.rect.size())

    def paintEvent(self, event):
        qp = QtWidgets.QStylePainter(self)
        qp.drawPrimitive(QtWidgets.QStyle.PE_IndicatorToolBarHandle, self._option)


class ComboSpin(QtWidgets.QComboBox):
    def __init__(self, *args, **kwargs):
        QtWidgets.QComboBox.__init__(self, *args, **kwargs)
        self.setEditable(True)
        self.setInsertPolicy(self.NoInsert)
        self.lineEdit().setAlignment(QtCore.Qt.AlignRight)
        self.lineEdit().returnPressed.disconnect()
        self.lineEdit().returnPressed.connect(self.clearFocus)

    def setRange(self, start, end, deltaStr=0):
        self.setValidator(QtGui.QIntValidator(start, end))
        for i in range(start, end + 1):
            self.addItem(str(i + deltaStr))
            self.setItemData(i, QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter, QtCore.Qt.TextAlignmentRole)

    def wheelEvent(self, event):
        if event.delta() > 0:
            delta = 1
        else:
            delta = -1
        if event.modifiers() == QtCore.Qt.ShiftModifier:
            delta *= 8
        self.setCurrentIndex(sanitize(0, self.currentIndex() + delta, self.count() - 1))

    def value(self):
        return self.currentIndex()

    def setValue(self, value):
        self.setCurrentIndex(value)


class ScrollBarSpacer(QtWidgets.QWidget):
    def __init__(self, parent, orientation, size):
        QtWidgets.QWidget.__init__(self, parent)
        if orientation == QtCore.Qt.Horizontal:
            self.setFixedWidth(size)
        else:
            self.setFixedHeight(size)
        self.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Maximum)


class ZoomWidget(QtWidgets.QWidget):
    zoomChanged = QtCore.pyqtSignal(int)

    def __init__(self, parent, zoomOrientation, minimum=.125, maximum=8):
        QtWidgets.QWidget.__init__(self, parent)
        self.zoomOrientation = zoomOrientation
        self.minimum = minimum
        self.maximum = maximum
        self.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Maximum)
        if zoomOrientation == QtCore.Qt.Horizontal:
            layout = QtWidgets.QHBoxLayout()
        else:
            layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        layout.setSpacing(1)

        layout.setContentsMargins(0, 0, 0, 0)
        self.setContentsMargins(1, 1, 1, 1)

        self.setStyleSheet('''
            QPushButton {
                border: 1px solid palette(mid);
                border-style: outset;
            }
            QPushButton:hover {
                border-color: palette(dark);
            }
            QPushButton:pressed {
                border-style: inset;
            }
            ''')

        size = self.fontMetrics().height()
        self.plusBtn = QtWidgets.QPushButton('+', self)
        layout.addWidget(self.plusBtn)
        self.plusBtn.setFixedSize(size, size)
        self.plusBtn.setFocusPolicy(QtCore.Qt.NoFocus)

        self.minusBtn = QtWidgets.QPushButton('-', self)
        layout.addWidget(self.minusBtn)
        self.minusBtn.setFixedSize(size, size)
        self.minusBtn.setFocusPolicy(QtCore.Qt.NoFocus)

        self.plusBtn.clicked.connect(lambda: self.zoomChanged.emit(1))
        self.minusBtn.clicked.connect(lambda: self.zoomChanged.emit(-1))

        self.minusBtn.installEventFilter(self)
        self.plusBtn.installEventFilter(self)

        self.setToolTip('100%')

    def setZoom(self, zoom):
        self.setToolTip(str(zoom * 100).rstrip('0').rstrip('.') + '%')
        self.plusBtn.setEnabled(zoom < self.maximum)
        self.minusBtn.setEnabled(zoom > self.minimum)
        if self.underMouse():
            QtWidgets.QToolTip.showText(QtGui.QCursor.pos(), self.toolTip())

    def eventFilter(self, source, event):
        if event.type() == QtCore.QEvent.Wheel:
            self.wheelEvent(event)
            return True
        return QtWidgets.QWidget.eventFilter(self, source, event)

    def wheelEvent(self, event):
        self.zoomChanged.emit(1 if event.delta() > 0 else -1)

    def resizeEvent(self, event):
        if self.zoomOrientation == QtCore.Qt.Horizontal:
            size = self.height() - 2
        else:
            size = self.width() - 2
        self.plusBtn.setFixedSize(size, size)
        self.minusBtn.setFixedSize(size, size)

