#!/usr/bin/env python
# *-* encoding: utf-8 *-*

from __future__ import division
import sys
from Qt import QtCore, QtGui, QtWidgets
from metawidget import ColorValueWidget, makeQtChildProperty, _getCssQColorStr
from colorvaluewidgethelpers import ValueEditor

def avg(v0, v1):
    return (v0 + v1) / 2


class ValueWidget(QtWidgets.QWidget):
    def __init__(self, parent):
        QtWidgets.QWidget.__init__(self, parent)
        parent.valueChangedStr.connect(self.setValue)
        self.hide()
        self.value = ''

    def setVisible(self, visible):
        if visible:
            self.value = self.parent().valueStr
            self.updateRect()
        QtWidgets.QWidget.setVisible(self, visible)

    def showEvent(self, event):
        self.value = self.parent().valueStr
        self.updateRect()

    def updateRect(self):
        parent = self.parent()
        #minimum width is 12
        textWidth = max([self.fontMetrics().width(value) for value in parent.valueList] + [12]) + 4
        textHeight = self.fontMetrics().height() + 4
        parentRect = parent.rect()
        x = parentRect.x() + (parentRect.width() - textWidth)
        y = (parentRect.height() - textHeight)
        if parent.value() < (parent.maximum() - parent.minimum()) / 2 + parent.minimum():
            factor = .25
        else:
            factor = .75
        if parent.orientation() == QtCore.Qt.Horizontal:
            x *= factor
            y *= .5
        else:
            x *= .5
            y *= factor
            
        self.setGeometry(x, y, textWidth, textHeight)
        self.update()

    def setValue(self, value):
        self.value = value
#        self.update()
        self.updateRect()

    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        qp.setRenderHints(qp.Antialiasing)
        qp.setPen(QtGui.QPen(QtCore.Qt.darkGray, .5))
        qp.setBrush(QtGui.QColor(255, 255, 255, 192))
        qp.drawRoundedRect(self.rect(), 2, 2)
        qp.setPen(QtCore.Qt.black)
        qp.drawText(self.rect(), QtCore.Qt.AlignCenter, self.value)


class FakeValueList(list):
    def __init__(self, parent):
        self.valueList = range(parent.minimum(), parent.maximum() + 1, parent.step)

    def __iter__(self):
        return (str(v) for v in self.valueList)

    def __getitem__(self, item):
        return str(self.valueList[item])


class MacOSHandle(QtWidgets.QFrame):
    def __init__(self, parent):
        QtWidgets.QFrame.__init__(self, parent)
        palette = self.palette()
        handleLight = palette.color(palette.Midlight)
        handleDark = palette.color(palette.Dark)
        self.setStyleSheet('''
            MacOSHandle {{
                border: 1px solid darkGray;
                border-style: outset;
                border-radius: 2px;
            }}
        '''.format(
                handleColor=_getCssQColorStr(QtGui.QColor.fromRgb(*map(lambda c: avg(*c), zip(handleLight.getRgb(), handleDark.getRgb()))))
            ))
        self.setOrientation(parent.orientation())

    def setOrientation(self, orientation):
        if orientation == QtCore.Qt.Horizontal:
            self.setFixedSize(8, 18)
        else:
            self.setFixedSize(18, 8)


class _Slider(QtWidgets.QSlider):
    _grooveExtent = 96
    _grooveSize = 16
    _defaultRangeStart = QtGui.QColor(QtCore.Qt.green)
    _defaultRangeEnd = QtGui.QColor(QtCore.Qt.red)

    valueChangedStr = QtCore.pyqtSignal(str)

    def __init__(self, parent, orientation):
        QtWidgets.QSlider.__init__(self, orientation, parent)

        if sys.platform == 'darwin':
            self.handle = MacOSHandle(self)
            self.handleOption = QtWidgets.QStyleOptionSlider()
            self.valueChanged.connect(self.moveMacOSHandle)
        self.valueWidget = ValueWidget(self)
        self.valueChanged.connect(lambda value: self.valueChangedStr.emit(self.valueList[value]))
        #TODO: fix orientation change
        if orientation == QtCore.Qt.Horizontal:
            self._minWidth = self._grooveExtent
            self._minHeight = self._grooveSize
        else:
            self._minWidth = self._grooveSize
            self._minHeight = self._grooveExtent
        self.defaultValue = self.minimum()
        self.setRange(0, 127)

        self._minimumColor = self._defaultRangeStart
        self._maximumColor = self._defaultRangeEnd
        self.centerGradient = False
        self.colorCurve = QtCore.QEasingCurve(0)

        self._background = QtGui.QColor(QtCore.Qt.black)
        self._clipPath = QtGui.QPainterPath()
        if orientation == QtCore.Qt.Horizontal:
            self._valueColor = QtGui.QRadialGradient(0, .5, 1)
            self.createClipPath = self._createClipPathHorizontal
        else:
            self._valueColor = QtGui.QRadialGradient(.5, 1, 1)
            self.createClipPath = self._createClipPathVertical
        self._valueColor.setCoordinateMode(self._valueColor.ObjectBoundingMode)
        self.setValueColor()
        self.valueChanged.connect(lambda v: self.setValueColor())
        self.valueChangedStr.connect(self.setToolTip)

        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.contextMenu)

        self.valueVisible = True
        self.keepValueVisible = False
        self.showValueTimer = QtCore.QTimer()
        self.showValueTimer.setSingleShot(True)
        self.showValueTimer.setInterval(500)
        self.showValueTimer.timeout.connect(self.showValue)

        self._baseValueList = FakeValueList(self)

    @property
    def valueList(self):
        try:
            return self._valueList
        except:
            return self._baseValueList

    def setValueList(self, valueList=None):
        if not valueList:
            self._valueList = list(str(value) for value in range(self.minimum(), self.maximum() + 1, self.step))
        else:
            rangeLen = (self.maximum() - self.minimum()) // self.step + 1
            self._valueList = valueList[:rangeLen]
            while len(self._valueList) < rangeLen:
                self._valueList.append(str(len(self._valueList * self.step)))
        self.setToolTip(self._valueList[self.value()])

    @QtCore.pyqtProperty(str)
    def valueStr(self):
        return self.valueList[self.value()]

    @QtCore.pyqtProperty(int)
    def step(self):
        return 1

    def setBackground(self, color):
        self._background = color
        self.setValueColor()

    def setMinimumColor(self, color):
        self._minimumColor = color
        self.setValueColor()

    def setMaximumColor(self, color):
        self._maximumColor = color
        self.setValueColor()

    def _getColor(self, startColor, endColor, ratio):
        color = []
        for start, end in zip(startColor.getRgb(), endColor.getRgb()):
            color.append(start + (end - start) * ratio)
        return QtGui.QColor(*color)

    def setValueColor(self):
        ratio = (self.value() - self.minimum()) / (self.maximum() - self.minimum())
        if self.invertedAppearance():
            startColor = self._maximumColor
            endColor = self._minimumColor
        else:
            startColor = self._minimumColor
            endColor = self._maximumColor
        if self.orientation() == QtCore.Qt.Horizontal:
            if self.centerGradient:
                self._valueColor.setFocalPoint(-.5 + ratio * 2, .5)
                self._valueColor.setCenter(ratio, .5)
            else:
                self._valueColor.setFocalPoint(-.5 + ratio, .5)
        else:
            if self.centerGradient:
                self._valueColor.setFocalPoint(.5, 1.5 - ratio * 2)
                self._valueColor.setCenter(.5, ratio)
            else:
                self._valueColor.setFocalPoint(.5, 1.5 - ratio)
        if self.centerGradient:
            ratio = abs(.5 - ratio) * 2
        colorRatio = self.colorCurve.valueForProgress(ratio)
        self._valueColor.setStops([(ratio * .5, self._getColor(startColor, endColor, colorRatio)), (1, self._background)])
#        self.setStyleSheet('''
#            QSlider::groove:horizontal {{
#                background-color: qradialgradient(cx: 0, cy: .5, radius: 1, fx: {fx}, fy: .5, stop: {ratio} {valueColor}, stop: 1 black);
#            }}
#            QSlider::groove:vertical {{
#                background-color: qradialgradient(cx: .5, cy: 1, radius: 1, fx: .5, fy: {fy}, stop: {ratio} {valueColor}, stop: 1 black);
#            }}
#            '''.format(
#                startColor=_getCssQColorStr(startColor), 
#                endColor=_getCssQColorStr(endColor), 
#                fx=-.5 + ratio, 
#                fy=1.5 - ratio, 
#                ratio=ratio * .5, 
#                valueColor=_getCssQColorStr(self._getColor(startColor, endColor, ratio)), 
#                )
#            )
#        print(self.styleSheet())

    def setMinimum(self, minimum):
        QtWidgets.QSlider.setMinimum(self, minimum)
        self.setDefaultValue(self.defaultValue)

    def setMaximum(self, maximum):
        QtWidgets.QSlider.setMaximum(self, maximum)
        self.setDefaultValue(self.defaultValue)

    def setRange(self, minimum, maximum, step=1):
        QtWidgets.QSlider.setRange(self, minimum, maximum)
        self.setDefaultValue(self.defaultValue)

    def setDefaultValue(self, value):
        if self.step == 1 and self.minimum() <= value <= self.maximum():
            self.defaultValue = value
        elif value <= self.minimum():
            self.defaultValue = self.minimum()
        elif value >= self.maximum():
            self.defaultValue = self.maximum()
        else:
            self.defaultValue = self.minimum() + int(self.step * round((value - self.minimum())/self.step))

    def setOrientation(self, orientation):
        if orientation == QtCore.Qt.Horizontal:
            self.createClipPath = self._createClipPathHorizontal
            self._valueColor.setCenter(0, .5)
        else:
            self.createClipPath = self._createClipPathVertical
            self._valueColor.setCenter(.5, 1)
        if sys.platform == 'darwin':
            self.handle.setOrientation(orientation)
        QtWidgets.QSlider.setOrientation(self, orientation)

    def setValueVisible(self, visible):
        self.valueVisible = visible
        if not visible:
            self.valueWidget.setVisible(False)

    def setKeepValueVisible(self, state):
        self.keepValueVisible = state
        self.valueWidget.setVisible(True)

    def showValue(self, show=False):
        if not self.valueVisible:
            return
        if not show and self.keepValueVisible:
            show = True
        self.valueWidget.setVisible(show)

    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        qp.setRenderHints(qp.Antialiasing)
        qp.translate(.5, .5)
        qp.setPen(QtCore.Qt.NoPen)
        qp.setBrush(self._valueColor)
        qp.drawPath(self._clipPath)
        QtWidgets.QSlider.paintEvent(self, event)

    def _createClipPathHorizontal(self):
        self._clipPath = QtGui.QPainterPath()
        self._clipPath.addRoundedRect(0, self.height() / 2. - 4, self.width(), 6, 2, 2)
#        self._scale = self.width() / self._clipPath.boundingRect().width(), 1

    def _createClipPathVertical(self):
        self._clipPath = QtGui.QPainterPath()
        self._clipPath.addRoundedRect(self.width() / 2. - 4, 0, 6, self.height(), 2, 2)
#        self._scale = 1, self.height() / self._clipPath.boundingRect().height()

    def contextMenu(self, pos):
#        if self.editor:
#            self.editor.hide()
#            self.editor.deleteLater()
#            self.editor = None
        menu = QtWidgets.QMenu(self)
        setValueAction = menu.addAction('Set value...', self.mouseDoubleClickEvent)
        menu.addSeparator()
        menu.addAction('Restore default value ({})'.format(self.valueList[self.defaultValue]), lambda: self.setValue(self.defaultValue))
        menu.setDefaultAction(setValueAction)
        menu.exec_(self.mapToGlobal(pos))

    def moveMacOSHandle(self):
        self.initStyleOption(self.handleOption)
        if self.orientation() == QtCore.Qt.Horizontal:
            handleSize = self.handle.width()
            maxWidth = self.rect().width() - handleSize
            upsideDown = False
            x = self.style().sliderPositionFromValue(self.minimum(), self.maximum(), self.sliderPosition(), maxWidth, upsideDown)
            y = (self.height() - self.handle.height()) / 2 - 1
        else:
            handleSize = self.handle.height()
            maxWidth = self.rect().height() - handleSize
            upsideDown = True
            x = (self.width() - self.handle.width()) / 2 - 1
            y = self.style().sliderPositionFromValue(self.minimum(), self.maximum(), self.sliderPosition(), maxWidth, upsideDown)
        self.handle.move(x, y)

    def mouseDoubleClickEvent(self, event=None):
        if event and event.button() != QtCore.Qt.LeftButton:
            return
        self.editor = ValueEditor(self)
        self.editor.setPalette(self.palette())
        self.editor.show()
        self.editor.setFocus(QtCore.Qt.OtherFocusReason)
        self.editor.destroyed.connect(lambda: setattr(self, 'editor', None))

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MidButton:
            self.setValue(self.defaultValue)
            return
        QtWidgets.QSlider.mousePressEvent(self, event)
        if event.button() == QtCore.Qt.LeftButton:
            self.showValue(True)

    def mouseReleaseEvent(self, event):
        QtWidgets.QSlider.mouseReleaseEvent(self, event)
        if event.button() == QtCore.Qt.LeftButton:
            self.showValue(False)

    def wheelEvent(self, event):
        QtWidgets.QSlider.wheelEvent(self, event)
        self.showValue(True)
        if not self.keepValueVisible:
            self.showValueTimer.start()

    def resizeEvent(self, event):
        QtWidgets.QSlider.resizeEvent(self, event)
        self.createClipPath()
        self.showValue(self.keepValueVisible)
        if sys.platform == 'darwin':
            self.moveMacOSHandle()


class Slider(ColorValueWidget):
    valueChanged = QtCore.pyqtSignal(int)
    grooveDark = _getCssQColorStr(QtGui.QColor(QtCore.Qt.black))
    grooveLight = _getCssQColorStr(QtGui.QColor(QtCore.Qt.darkGray))
    def __init__(self, parent=None, label='slider', labelPos=QtCore.Qt.BottomEdge, orientation=QtCore.Qt.Vertical):
        ColorValueWidget.__init__(self, parent, label, labelPos)
        self.slider = _Slider(self, orientation)
        self.slider.valueChanged.connect(self.valueChanged)
        self._orientation = orientation
#        self.orientation = orientation
        self.setWidget(self.slider)
#        self.setFont(QtGui.QFont('Droid Sans', 9, QtGui.QFont.Bold))
        self._paletteChanged(self.palette())
        self._colorCurve = 0
        self.showValue = self.slider.showValue

#    rangeColorStart = QtCore.pyqtProperty(QtGui.QColor, lambda *args: None, lambda *args: None)
    rangeColorZero = makeQtChildProperty(QtGui.QColor, '_minimumColor', 'setMinimumColor')
    rangeColorEnd = makeQtChildProperty(QtGui.QColor, '_maximumColor', 'setMaximumColor')
    background = makeQtChildProperty(QtGui.QColor, '_background', 'setBackground')

    @QtCore.pyqtSlot(object)
    def setValueList(self, valueList=None):
        if valueList is None:
            valueList = []
        self.widget.setValueList(valueList)

    @QtCore.pyqtProperty(QtGui.QColor, designable=False)
    def rangeColorStart(self):
        return QtGui.QColor()

    @rangeColorStart.setter
    def rangeColorStart(self, color):
        pass

    @QtCore.pyqtProperty(int)
    def minimum(self):
        return self.slider.minimum()

    @minimum.setter
    def minimum(self, minimum):
        self.slider.setMinimum(minimum)

    @QtCore.pyqtSlot(int)
    def setMinimum(self, minimum):
        self.minimum = minimum

    @QtCore.pyqtProperty(int)
    def maximum(self):
        return self.slider.maximum()

    @maximum.setter
    def maximum(self, maximum):
        self.slider.setMaximum(maximum)

    @QtCore.pyqtSlot(int)
    def setMaximum(self, maximum):
        self.maximum = maximum

    defaultValue = makeQtChildProperty(int, 'defaultValue', 'setDefaultValue')

    @QtCore.pyqtSlot(int)
    def setDefaultValue(self, value):
        self.defaultValue = value

    @QtCore.pyqtProperty(QtCore.Qt.Orientation)
    def orientation(self):
        return self._orientation

    #TODO: che cazzo succede?
    @orientation.setter
    def orientation(self, orientation):
        self._orientation = orientation
        if orientation == QtCore.Qt.Horizontal:
            self.slider.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Maximum))
        else:
            self.slider.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Expanding))
        self.slider.setOrientation(orientation)

    #TODO: trova un'alternativa per il problema di inheritance degli stylesheet
    #perché al cambio di palette successivo questo potrebbe essere ignorato
    def _paletteChanged(self, palette):
        handleLight = palette.color(palette.Midlight)
        handleDark = palette.color(palette.Dark)
        self.slider.setStyleSheet('''
            QSlider::groove {{
                border: 1px solid #999999;
                border-top: 1px solid {grooveDark};
                border-right: 1px solid {grooveLight};
                border-bottom: 1px solid {grooveLight};
                border-left: 1px solid {grooveDark};
                border-radius: 2px;
                background-color: transparent;
            }}
            QSlider::groove:horizontal {{
                height: 6px;
                margin: 2px 0;
            }}
            QSlider::groove:vertical {{
                width: 6px;
                margin: 0 2px;
            }}
            QSlider::handle {{
                background: {handleColor};
                border-top: 1px solid {handleLight};
                border-right: 1px solid {handleDark};
                border-bottom: 1px solid {handleDark};
                border-left: 1px solid {handleLight};
                border-radius: 2px;
            }}
            QSlider MacOSHandle {{
                background: {handleColor};
            }}
            QSlider::handle:pressed {{
                border-top: 1px solid {handleDark};
                border-right: 1px solid {handleLight};
                border-bottom: 1px solid {handleLight};
                border-left: 1px solid {handleDark};
            }}
            QSlider::handle:horizontal {{
                width: 6px;
                margin: -6px 0;
            }}
            QSlider::handle:vertical {{
                height: 6px;
                margin: 0 -6px;
            }}
            '''.format(
                grooveDark=self.grooveDark, 
                grooveLight=self.grooveLight, 
                handleLight=_getCssQColorStr(handleLight), 
                handleDark=_getCssQColorStr(handleDark), 
                handleColor=_getCssQColorStr(QtGui.QColor.fromRgb(*map(lambda c: avg(*c), zip(handleLight.getRgb(), handleDark.getRgb()))))
                ))

    @QtCore.pyqtProperty(int)
    def value(self):
        return self.widget.value()

    @value.setter
    def value(self, value):
        self.widget.setValue(value)

    @QtCore.pyqtProperty(bool)
    def centerGradient(self):
        return self.slider.centerGradient

    @centerGradient.setter
    def centerGradient(self, center):
        self.slider.centerGradient = center
        self.slider.setValueColor()

    @QtCore.pyqtSlot(int)
    def setValue(self, value):
        self.widget.setValue(value)

    @QtCore.pyqtSlot(int, int, int)
    def setRange(self, minimum, maximum, step=1):
        self.widget.setRange(minimum, maximum, step)

    keepValueVisible = makeQtChildProperty(bool, 'keepValueVisible', 'setKeepValueVisible')

    @QtCore.pyqtProperty(int)
    def colorCurve(self):
        return self._colorCurve

    @colorCurve.setter
    def colorCurve(self, curve):
        self._colorCurve = max(0, min(28, curve))
        self.slider.colorCurve.setType(self._colorCurve)
        self.slider.setValueColor()

if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)
    w = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout()
    w.setLayout(layout)
    layout.addWidget(Slider())
    layout.addWidget(Slider(orientation=QtCore.Qt.Horizontal))
    w.show()
    sys.exit(app.exec_())


