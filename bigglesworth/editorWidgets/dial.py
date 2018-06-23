#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
import math
#from bisect import bisect_left

from Qt import QtCore, QtGui, QtWidgets, __binding__
from metawidget import ColorValueWidget, makeQtChildProperty
from colorvaluewidgethelpers import ValueEditor
#from combo import _Combo

try:
    range = xrange
except:
    pass

def _getDisabledColor(color):
    h, s, l, a = color.getHslF()
    a *= .66
    return color.fromHslF(h, s, l, a)

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
        #minimum width is 12
        textWidth = max([self.fontMetrics().width(value) for value in self.parent().valueList] + [12]) + 4
        textHeight = self.fontMetrics().height() + 4
        parentRect = self.parent().rect()
        self.setGeometry(parentRect.x() + (parentRect.width() - textWidth) // 2, (parentRect.height() - textHeight) / 2, textWidth, textHeight)
        self.update()

    def setValue(self, value):
        self.value = value
        self.update()

    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        qp.setRenderHints(qp.Antialiasing)
        qp.setPen(QtGui.QPen(QtCore.Qt.darkGray, .5))
        qp.setBrush(QtGui.QColor(255, 255, 255, 128))
        qp.drawRoundedRect(self.rect(), 2, 2)
        qp.setPen(QtCore.Qt.black)
        qp.drawText(self.rect(), QtCore.Qt.AlignCenter, self.value)


class FakeValueList(list):
    def __init__(self, parent):
        self.valueList = range(parent.minimum, parent.maximum + 1, parent.step)

    def __iter__(self):
        return (str(v) for v in self.valueList)

    def __getitem__(self, item):
        return str(self.valueList[item])


class _Dial(QtWidgets.QWidget):
    _minWidth = _minHeight = 20
    _minimumSizeHint = QtCore.QSize(20, 20)
    _baseSizeHint = QtCore.QSize(100, 100)

    _defaultRangeStart = QtGui.QColor(QtCore.Qt.green)
    _defaultRangeEnd = QtGui.QColor(QtCore.Qt.red)
    _defaultRangePen = QtGui.QColor(QtCore.Qt.darkGray)
    _defaultScalePen = QtGui.QColor(QtCore.Qt.lightGray)
    _defaultIndicatorPen = QtGui.QColor(QtCore.Qt.white)

    dialRatio = .8
    cursorPosRadius = .6
    cursorSize = .16
    valueArcRatio = .925
    valueArcPenRatio = .075
    rangeInnerRatio = .85
    rangeScaleRatio = .9

    debugColor = QtGui.QColor(100, 0, 0, 50)

    valueChanged = QtCore.pyqtSignal(int)
    currentIndexChanged = QtCore.pyqtSignal(int)
    valueChangedStr = QtCore.pyqtSignal(str)

    def __init__(
            self, 
            parent=None, 
            fullRange=None, 
            minimum=0, 
            maximum=127, 
            step=1, 
            valueList=None, 
            label='', 
            rangeAngleStart=30, 
            rangeAngleSpan=300, 
            alignment=QtCore.Qt.AlignRight|QtCore.Qt.AlignBottom, 
            rangeZeroAngle=None, 
            centerAngle=None, 
            centerEven=True, 
            ):
        QtWidgets.QWidget.__init__(self, parent)
        self.valueWidget = ValueWidget(self)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding))
        self.setMinimumSize(self._minimumSizeHint)

        self.editor = None
        self.valueVisible = True
        self.keepValueVisible = False
        self.showValueTimer = QtCore.QTimer()
        self.showValueTimer.setSingleShot(True)
        self.showValueTimer.setInterval(500)
        self.showValueTimer.timeout.connect(self.showValue)

        self.rangeInnerRadius = self.rangeOuterRadius = self.scaleOuterRadius = 0
        self.currentDialSize = self._minWidth
        self.dialSize = self.currentDialSize * self.dialRatio
        self.dialCenter = QtCore.QPointF()
        self.dialRect = QtCore.QRectF(0, 0, 1, 1)
        self.cursorRect = QtCore.QRectF(0, 0, 1, 1)
        self.rangeRect = QtCore.QRectF(0, 0, 1, 1)
        self.valueArcRect = QtCore.QRectF(0, 0, 1, 1)
        self.rangeStart = QtCore.QLine()
        self.rangeEnd = QtCore.QLine()

        self.rangePen = QtGui.QPen(self._defaultRangePen)
        self.scalePen = QtGui.QPen(self._defaultScalePen)
        self.pointerColor = QtGui.QColor(self._defaultIndicatorPen)
        self.pointerCapStyle = QtCore.Qt.SquareCap
        self.valuePen = QtGui.QPen(self.pointerColor, 1.5, cap=self.pointerCapStyle)
        self.valueArcColorDisabled = QtGui.QConicalGradient(0, 0, 240)
        self.valueArcColorEnabled = QtGui.QConicalGradient(0, 0, 240)
        self.valueArcColors = self.valueArcColorDisabled, self.valueArcColorEnabled
        self.valueArcPenDisabled = QtGui.QPen(QtCore.Qt.black, self.valueArcPenRatio, cap=QtCore.Qt.FlatCap)
        self.valueArcPenEnabled = QtGui.QPen(QtCore.Qt.black, self.valueArcPenRatio, cap=QtCore.Qt.FlatCap)
        self.valueArcPens = self.valueArcPenDisabled, self.valueArcPenEnabled
        self.dialBgdColorDisabled = QtGui.QRadialGradient(.5, .5, 1, .25, .25)
        self.dialBgdColorDisabled.setCoordinateMode(self.dialBgdColorDisabled.ObjectBoundingMode)
        self.dialBgdColorEnabled = QtGui.QRadialGradient(self.dialBgdColorDisabled)
        self.dialBgdColors = self.dialBgdColorDisabled, self.dialBgdColorEnabled
        self.dialBorderDisabled = QtGui.QRadialGradient(self.dialBgdColorDisabled)
        self.dialBorderEnabled = QtGui.QRadialGradient(self.dialBgdColorDisabled)
        self.dialBorderColors = self.dialBorderDisabled, self.dialBorderEnabled
        self.cursorColorDisabled = QtGui.QRadialGradient(.5, .5, .5, .65, .65)
        self.cursorColorDisabled.setCoordinateMode(self.dialBgdColorDisabled.ObjectBoundingMode)
        self.cursorColorEnabled = QtGui.QRadialGradient(self.cursorColorDisabled)
        self.cursorColors = self.cursorColorDisabled, self.cursorColorEnabled

        #init values
        self.gradientScale = False
        self.rangeAngleStart = rangeAngleStart % 360
        self.rangeAngleStartMath = 270 - self.rangeAngleStart
        self.rangeAngleStartQt = self.rangeAngleStartMath * 16
        self.startXRatio = math.cos(math.radians(self.rangeAngleStartMath))
        self.startYRatio = math.sin(math.radians(self.rangeAngleStartMath))

        self.rangeAngleSpan = rangeAngleSpan % 360
        self.rangeAngleSpanMath = -self.rangeAngleSpan
        self.rangeAngleSpanQt = self.rangeAngleSpanMath * 16

        self.centerAngle = centerAngle if centerAngle is not None else self.rangeAngleSpan // 2
        self.rangeZeroAngle = rangeZeroAngle if rangeZeroAngle is not None else 0
        self.rangeZeroAngleQt = self.rangeZeroAngle * 16
        self.centerEven = centerEven

        self.rangeAngleEnd = self.rangeAngleStartMath - self.rangeAngleSpan
        self.rangeAngleEndQt = self.rangeAngleEnd * 16
        self.endXRatio = math.cos(math.radians(self.rangeAngleEnd))
        self.endYRatio = math.sin(math.radians(self.rangeAngleEnd))

        self.rangeAngleEndMath = self.rangeAngleStartMath + self.rangeAngleSpanMath
        self.startColorAngle = self.rangeAngleSpan / 360 % 1
        self.zeroColorAngle = (-self.rangeAngleSpanMath - self.rangeZeroAngle) / 360 % 1

        self.setRange(*fullRange if fullRange else (minimum, maximum, step))

        self.value = self.minimum
        self._baseValueList = FakeValueList(self)
        if valueList:
            self.setValueList(valueList)

        self._absoluteValue = 0
        self._currentIndex = 0
        self.defaultValue = self.minimum
        self.angleValue = self.rangeAngleStartMath + self.rangeAngleSpanMath * self._absoluteValue
#        self._angleValue = self.rangeAngleStartMath + self.rangeAngleSpanMath * self._absoluteValue
#        self.dialAngleValue = (-self._angleValue + 270 - self.rangeAngleStart) % 360
#        self.dialAngleValueQt = self.dialAngleValue * 16
        self._prevMousePos = None

        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.contextMenu)
        self.valueChangedStr.connect(self.setToolTip)

        self.setPalette()
        self.valueArcPen = self.valueArcPens[True]
        self.dialBgdColor = self.dialBgdColors[True]
        self.dialBorderPen = QtGui.QPen(self.dialBorderColors[True], 1)
        self.cursorColor = self.cursorColors[True]

        self.valueArcColorDisabled.setAngle(self.rangeAngleEndMath)
        self.valueArcColorEnabled.setAngle(self.rangeAngleEndMath)
        self.setRangeColorStart(self._defaultRangeEnd)
        self.setRangeColorZero(self._defaultRangeStart)
        self.setRangeColorEnd(self._defaultRangeEnd)
        self.valueArcPenLinear = self._getValueColor()

        self.setToolTip(self.valueList[0])

#        self.pressPoint = None

    def setPalette(self, palette=None):
        if palette is None:
            try:
                palette = self.parent().palette()
            except:
                palette = self.palette()

        self._dialBgdColorDark = palette.color(palette.Mid)
        self._dialBgdColorLight = palette.color(palette.Mid).lighter()
        self._dialBorderColorLight = palette.color(palette.Midlight)
        self._dialBorderColorDark = palette.color(palette.Dark)

        self.dialBgdColorDisabled.setColorAt(0, _getDisabledColor(self._dialBgdColorLight))
        self.dialBgdColorDisabled.setColorAt(1, _getDisabledColor(self._dialBgdColorDark))
        self.dialBgdColorEnabled.setColorAt(0, self._dialBgdColorLight)
        self.dialBgdColorEnabled.setColorAt(1, self._dialBgdColorDark)
        self.dialBorderDisabled.setColorAt(0, _getDisabledColor(self._dialBorderColorLight))
        self.dialBorderDisabled.setColorAt(1, _getDisabledColor(self._dialBorderColorDark))
        self.dialBorderEnabled.setColorAt(0, self._dialBorderColorLight)
        self.dialBorderEnabled.setColorAt(1, self._dialBorderColorDark)
        self.cursorColorDisabled.setColorAt(0, _getDisabledColor(self._dialBgdColorLight))
        self.cursorColorDisabled.setColorAt(1, _getDisabledColor(self._dialBgdColorDark))
        self.cursorColorEnabled.setColorAt(0, self._dialBgdColorLight)
        self.cursorColorEnabled.setColorAt(1, self._dialBgdColorDark)

    def changeEvent(self, event):
        if event.type() != QtCore.QEvent.EnabledChange: return
        state = self.isEnabled()
        if self.gradientScale:
            self.valueArcPen = self.valueArcPens[state]
        else:
            self.valueArcPenLinear = self._getValueColor()
            self.valueArcPen.setColor(self.valueArcPenLinear if self.isEnabled() else _getDisabledColor(self.valueArcPenLinear))
        self.dialBgdColor = self.dialBgdColors[state]
        self.dialBorderPen.setBrush(QtGui.QBrush(self.dialBorderColors[state]))
        self.cursorColor = self.cursorColors[state]
        self.update()

    def _computeRange(self):
        self.centerRatio = self.centerAngle / self.rangeAngleSpan
        self.rangeValues = [n for n in range(self.minimum, self.maximum + 1, self.step)]
        self.rangeLen = len(self.rangeValues)
        if self.rangeLen > 32:
            self.drawNotches = lambda qp: None
        elif (self.rangeLen & 1 or not self.centerEven) and self.centerRatio == .5:
            #might want to set an internal centerEven in case of range variations?
            self.drawNotches = self._drawNotchesOdd
        else:
            self.drawNotches = self._drawNotchesEven
        self.update()

    def setRange(self, minimum=0, maximum=127, step=1):
        self.minimum = minimum
        self.step = step
        if step == 1:
            self.maximum = maximum
        else:
            #check that the maximum value is actually within the step range
            div, rem = divmod(maximum - minimum, step)
            if rem == 0:
                self.maximum = maximum
            else:
                self.maximum = div * step
                if rem > self.step // 2:
                    self.maximum += step
        self._computeRange()

    def checkStep(self):
        if self.step > 1:
            div, rem = divmod(self.maximum - self.minimum, self.step)
            if rem != 0:
                self.maximum = self.minimum + div * self.step
                if rem > self.step // 2:
                    self.maximum += self.step
#            bigger = self.minimum
#            while bigger < self.maximum:
#                bigger += self.step
#            smaller = bigger - self.step
#            if abs(self.maximum - smaller) < abs(bigger - self.maximum):
#                self.maximum = smaller
#            else:
#                self.maximum = bigger
            self._computeRange()
            self._setValue(self.value)
        else:
            self._computeRange()
        try:
            self.setValueList(self._valueList)
        except:
            pass
        self._baseValueList = FakeValueList(self)
        self.setDefaultValue(self.defaultValue)

    def setMinimum(self, minimum):
        if minimum == self.minimum: return
        self.minimum = minimum if minimum <= self.maximum - self.step else self.maximum - self.step
        self.checkStep()
#        if self.value < self.minimum:
#            self._setValue(self.minimum)

    def setMaximum(self, maximum):
        if maximum == self.maximum: return
        self.maximum = maximum if maximum >= self.minimum + self.step else self.minimum + self.step
        self.checkStep()

    def setStep(self, step):
        if step == self.step: return
        self.step = step if step > 0 else 1
        self.checkStep()

    def setDefaultValue(self, value):
        if self.step == 1 and self.minimum <= value <= self.maximum:
            self.defaultValue = value
        elif value <= self.minimum:
            self.defaultValue = self.minimum
        elif value >= self.maximum:
            self.defaultValue = self.maximum
        else:
            self.defaultValue = self.getClosestValue(value)

    def setValueList(self, valueList=None):
        if not valueList:
            self._valueList = list(str(value) for value in range(self.minimum, self.maximum + 1, self.step))
        else:
            rangeLen = (self.maximum - self.minimum) // self.step + 1
            self._valueList = list(valueList[:rangeLen])
            while len(self._valueList) < rangeLen:
                self._valueList.append(str(len(self._valueList * self.step)))
        self.setToolTip(self._valueList[self.value])

    @property
    def valueList(self):
        try:
            return self._valueList
        except:
            return self._baseValueList

    def setRangeAngleStart(self, rangeAngleStart):
        self.rangeAngleStart = rangeAngleStart
        self.rangeAngleStartMath = 270 - rangeAngleStart
        self.rangeAngleStartQt = self.rangeAngleStartMath * 16
        self.startXRatio = math.cos(math.radians(self.rangeAngleStartMath))
        self.startYRatio = math.sin(math.radians(self.rangeAngleStartMath))
        self._computeRangeAngles()
        self._computeDialAngleValues()
        self.update()

    def setRangeAngleSpan(self, rangeAngleSpan):
        rangeAngleSpan %= 360
        self.rangeAngleSpan = rangeAngleSpan
        self.rangeAngleSpanMath = -rangeAngleSpan
        self.rangeAngleSpanQt = self.rangeAngleSpanMath * 16
        self._computeRangeAngles()
        self.update()

    def _computeRangeAngles(self):
        self.rangeAngleEnd = self.rangeAngleStartMath - self.rangeAngleSpan
        self.rangeAngleEndQt = self.rangeAngleEnd * 16
        self.endXRatio = math.cos(math.radians(self.rangeAngleEnd))
        self.endYRatio = math.sin(math.radians(self.rangeAngleEnd))
        self.rangeAngleEndMath = self.rangeAngleStartMath + self.rangeAngleSpanMath
        self.valueArcColorDisabled.setAngle(self.rangeAngleEndMath)
        self.valueArcColorEnabled.setAngle(self.rangeAngleEndMath)
        self.startColorAngle = self.rangeAngleSpan / 360 % 1
        self.zeroColorAngle = (-self.rangeAngleSpanMath - self.rangeZeroAngle) / 360 % 1
        if self.gradientScale:
            self._setRangeColorStart()
            self._setRangeColorZero()
        self._computeRangeLines()

    def _computeRangeLines(self):
        if self.rangeAngleSpan < 360:
            self.rangeStart = QtCore.QLineF(
                self.dialCenter.x() + self.rangeInnerRadius * self.startXRatio, 
                self.dialCenter.y() - self.rangeInnerRadius * self.startYRatio, 
                self.dialCenter.x() + self.rangeOuterRadius * self.startXRatio, 
                self.dialCenter.y() - self.rangeOuterRadius * self.startYRatio
                )
            self.rangeEnd = QtCore.QLineF(
                self.dialCenter.x() + self.rangeInnerRadius * self.endXRatio, 
                self.dialCenter.y() - self.rangeInnerRadius * self.endYRatio, 
                self.dialCenter.x() + self.rangeOuterRadius * self.endXRatio, 
                self.dialCenter.y() - self.rangeOuterRadius * self.endYRatio
                )

    def _setRangeColors(self):
        self.valueArcPenDisabled.setBrush(self.valueArcColorDisabled)
        self.valueArcPenEnabled.setBrush(self.valueArcColorEnabled)
        self.valueArcPen = self.valueArcPens[self.isEnabled()]

    def _setRangeColorStart(self):
        self.valueArcColorDisabled.setColorAt(self.startColorAngle, self.rangeColorStartDisabled)
        self.valueArcColorEnabled.setColorAt(self.startColorAngle, self.rangeColorStartEnabled)
        if self.gradientScale:
            self._setRangeColors()

    def setRangeColorStart(self, rangeColorStart):
        self.rangeColorStartEnabled = rangeColorStart
        self.rangeColorStartDisabled = _getDisabledColor(rangeColorStart)
        self._setRangeColorStart()

    def _setRangeColorZero(self):
        self.valueArcColorDisabled.setColorAt(self.zeroColorAngle, self.rangeColorZeroDisabled)
        self.valueArcColorEnabled.setColorAt(self.zeroColorAngle, self.rangeColorZeroEnabled)
        if self.gradientScale:
            self._setRangeColors()

    def setRangeColorZero(self, rangeColorZero):
        self.rangeColorZeroEnabled = rangeColorZero
        self.rangeColorZeroDisabled = _getDisabledColor(rangeColorZero)
        self._setRangeColorZero()

    def _setRangeColorEnd(self):
        self.valueArcColorDisabled.setColorAt(0, self.rangeColorEndDisabled)
        self.valueArcColorEnabled.setColorAt(0, self.rangeColorEndEnabled)
        if self.gradientScale:
            self._setRangeColors()
        else:
            self.valueArcPenLinear = self._getValueColor()
            self.valueArcPen.setColor(self.valueArcPenLinear if self.isEnabled() else _getDisabledColor(self.valueArcPenLinear))

    def setRangeColorEnd(self, rangeColorEnd):
        self.rangeColorEndEnabled = rangeColorEnd
        self.rangeColorEndDisabled = _getDisabledColor(rangeColorEnd)
        self._setRangeColorEnd()

    def setCenterEven(self, even):
        self.centerEven = even
        self._computeRange()

    def setCenterAngle(self, centerAngle):
        self.centerAngle = centerAngle
        self._computeRange()

    def setRangeZeroAngle(self, rangeZeroAngle):
        self.rangeZeroAngle = rangeZeroAngle
        self.rangeZeroAngleQt = self.rangeZeroAngle * 16
        self._computeRangeAngles()
        self._setRangeColorStart()
        self._setRangeColorZero()
#        self.setColors()
        self._computeRange()

    def setGradientScale(self, state):
        self.gradientScale = state
        if state:
            self._setRangeColors()
        else:
            self.valueArcPenLinear = self._getValueColor()
            self.valueArcPen.setColor(self.valueArcPenLinear if self.isEnabled() else _getDisabledColor(self.valueArcPenLinear))
        self.update()

#    def setPointerColor(self, color):
#        self.valuePen.setColor(color)
#        self.update()
#
#    def setPointerCapStyle(self, capStyle):
#        self.pointerCapStyle = capStyle
#        self.valuePen.setCapStyle(capStyle)
#        self.update()

#    @QtCore.pyqtProperty(QtGui.QPen)
#    def valuePen(self):
#        return self._valuePen
#
#    @valuePen.setter
#    def valuePen(self, pen):
#        self._valuePen = pen

    @QtCore.pyqtProperty(int, designable=False)
    def absoluteValue(self):
        return self._absoluteValue

    @absoluteValue.setter
    def absoluteValue(self, value):
        if value < 0:
            value = 0
        if value > 1:
            value = 1
        self._absoluteValue = value
        self.angleValue = self.rangeAngleStartMath + self.rangeAngleSpanMath * value
#        self._angleValue = self.rangeAngleStartMath + self.rangeAngleSpanMath * value
#        self.dialAngleValue = (-self._angleValue + 270 - self.rangeAngleStart) % 360
#        self.dialAngleValueQt = self.dialAngleValue * 16

    def setAbsoluteValue(self, value):
        self.absoluteValue = value
        self._computeCursorPos()
        self.update()

    @property
    def angleValue(self):
        #angle in geometrical reference (0° at 3 o'clock)
        return self._angleValue

    @angleValue.setter
    def angleValue(self, angle):
        self._angleValue = angle
        self._computeDialAngleValues()

    def _computeDialAngleValues(self):
        self.dialAngleValue = (-self._angleValue + 270 - self.rangeAngleStart) % 360
        self.dialAngleValueQt = self.dialAngleValue * 16
#        self._absoluteValue = ((self.rangeAngleStartMath - angle) % 360) / self.rangeAngleSpan
#        self._computeCursorPos()

    def _getValueColor(self):
        if self.rangeZeroAngle == 0:
            absoluteValue = self._absoluteValue
            redStart, greenStart, blueStart, alphaStart = self.rangeColorZeroEnabled.getRgb()
            redEnd, greenEnd, blueEnd, alphaEnd = self.rangeColorEndEnabled.getRgb()
        else:
            if self._absoluteValue >= .5:
                redStart, greenStart, blueStart, alphaStart = self.rangeColorZeroEnabled.getRgb()
                redEnd, greenEnd, blueEnd, alphaEnd = self.rangeColorEndEnabled.getRgb()
                absoluteValue = (self._absoluteValue - .5) * 2
            else:
                redStart, greenStart, blueStart, alphaStart = self.rangeColorStartEnabled.getRgb()
                redEnd, greenEnd, blueEnd, alphaEnd = self.rangeColorZeroEnabled.getRgb()
                absoluteValue = self._absoluteValue * 2
        red = redStart + absoluteValue * (redEnd - redStart)
        green = greenStart + absoluteValue * (greenEnd - greenStart)
        blue = blueStart + absoluteValue * (blueEnd - blueStart)
        return QtGui.QColor(red, green, blue)

    def _setValue(self, value):
        if value < self.minimum:
            value = self.minimum
        elif value > self.maximum:
            value = self.maximum
#        if not self.minimum <= value <= self.maximum: return
        if not value in self.valueList:
            value = self.getClosestValue(value)
        self.value = value
        self.absoluteValue = self.findAbsValue(value)
        if not self.gradientScale:
            self.valueArcPenLinear = self._getValueColor()
            self.valueArcPen.setColor(self.valueArcPenLinear if self.isEnabled() else _getDisabledColor(self.valueArcPenLinear))
        self._computeCursorPos()
        self.update()
#        self.absoluteValue = 1./(self.maximum()-self.minimum())*(self.value-self.minimum())

    def setValue(self, value):
        if self.value == value:
            return
        self._setValue(value)
        self.valueChanged.emit(self.value)
        try:
            self._currentIndex = self.rangeValues.index(self.value)
        except:
            self._currentIndex = self.getClosestIndex(self.value)
        self.valueChangedStr.emit(self.valueList[self._currentIndex])

    @QtCore.pyqtProperty(str)
    def valueStr(self):
        return self.valueList[self._currentIndex]

    @QtCore.pyqtProperty(int)
    def currentIndex(self):
        return self._currentIndex

    @currentIndex.setter
    def currentIndex(self, index):
        if index < 0:
            index = 0
        elif index >= self.rangeLen:
            index = self.rangeLen - 1
        self._currentIndex = index
        self.absoluteValue = self.findAbsValue(list(self.valueList)[index])
        self._computeCursorPos()

    def setCurrentIndex(self, index):
        if index >= self.rangeLen:
            index = self.rangeLen - 1
        elif index < 0:
            index = 0
        self.setValue(self.minimum + self.step * index)
#        self.setValue(list(self.valueList)[index])
#        self.currentIndex = index
#        self.value = list(self.valueList)[index]
#        self.valueChanged.emit(self.value)
#        self.valueChangedStr.emit(self.valueList[self.value])

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

    def findAbsValue(self, value):
        try:
            if (self.rangeLen & 1 or not self.centerEven) and self.centerRatio == .5:
                return 1 / ((self.rangeLen - 1) / self.rangeValues.index(value))
            pos = self.rangeValues.index(value)
            half = int(self.rangeLen * .5)
            if pos == half:
                return self.centerRatio
            if pos < half:
                return pos * self.centerRatio / (self.rangeLen - half - (self.rangeLen & 1))
            else:
                #ratio is changed if range is even
                return self.centerRatio  + (pos - half) * (1 - self.centerRatio) / (self.rangeLen - half - 1)
        except:
            return 0

    def getClosestIndex(self, value):
        return int(round((value - self.minimum) / self.step))
#        pos = bisect_left(self.rangeValues, value)
#        if pos == 0:
#            return 0
#        if pos == len(self.rangeValues):
#            return -1
#        before = self.rangeValues[pos - 1]
#        after = self.rangeValues[pos]
#        if after - value < value - before:
#            return pos
#        return pos - 1

    def getClosestValue(self, value):
#        return self.rangeValues[self.getClosestIndex(value)]
        return self.minimum + self.step * self.getClosestIndex(value)
    
    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        qp.setRenderHints(qp.Antialiasing)
        qp.translate(.5, .5)

        #Debug: draw "container" rects
#        qp.setPen(self.debugColor)
#        qp.drawRect(0, 0, self.width() - 1, self.height() - 1)
#        qp.drawRect(self.dialRect)
#        qp.drawLine(0, self.rect().height() / 2, self.width(), self.rect().height() / 2)
#        qp.drawLine(self.width() / 2, 0, self.width() / 2, self.height())
        #/Debug

        qp.setPen(self.rangePen)
        #range Arc
        qp.drawArc(self.rangeRect, self.rangeAngleStartQt, self.rangeAngleSpanQt)
        if self.rangeAngleSpanMath < 360:
            qp.drawLine(self.rangeStart)
            qp.drawLine(self.rangeEnd)

        #scale
        self.drawNotches(qp)

        #dial
        qp.setPen(self.dialBorderPen)
        qp.setBrush(self.dialBgdColor)
        qp.drawEllipse(self.dialRect)

        #cursor
        qp.setPen(QtCore.Qt.NoPen)
        qp.setBrush(self.cursorColor)
        qp.drawEllipse(self.cursorRect)

        #valueArc
        qp.setPen(self.valueArcPen)
        qp.drawArc(self.valueArcRect, self.rangeAngleStartQt - self.rangeZeroAngleQt, self.rangeZeroAngleQt - self.dialAngleValueQt)

        #valuePen
        qp.save()
        qp.setPen(self.valuePen)
        qp.translate(self.rect().center())
        qp.rotate(-self.angleValue)
        penWidthDelta = self.valuePen.widthF() * .5
        qp.drawLine(self.currentDialSize * .5 - penWidthDelta, 0, self.currentDialSize * self.dialRatio * .5125 + penWidthDelta, 0)
        qp.restore()

        #Debug: value line
#        qp.save()
#        qp.setPen(self.debugColor)
#        qp.translate(self.rect().center())
#        qp.rotate(-self.angleValue)
#        qp.drawLine(0, 0, max(self.rect().width(), self.rect().height()), 0)
#        qp.restore()
        #Debug: mouse press
#        if self.pressPoint:
#            qp.drawRect(self.pressPoint[0], self.pressPoint[1], 1, 1)
        #/Debug

    def _drawNotchesEven(self, qp):
        qp.save()
        qp.setPen(self.scalePen)
        qp.translate(self.rect().center())
        firstRange = int(self.rangeLen * .5)
        deltaAngle = self.centerAngle / (firstRange)
        qp.rotate(self.rangeAngleStart + 90)
        for step in range(1, firstRange + 1):
            qp.rotate(deltaAngle)
            qp.drawLine(self.rangeInnerRadius, 0, self.scaleOuterRadius, 0)
        lastRange = self.rangeLen - firstRange - 1
        deltaAngle = (self.rangeAngleSpan - self.centerAngle) / lastRange
        for step in range(1, lastRange):
            qp.rotate(deltaAngle)
            qp.drawLine(self.rangeInnerRadius, 0, self.scaleOuterRadius, 0)
        qp.restore()

    def _drawNotchesOdd(self, qp):
        qp.save()
        qp.setPen(self.scalePen)
        qp.translate(self.rect().center())
        deltaAngle = self.rangeAngleSpan / (self.rangeLen - 1)
        qp.rotate(self.rangeAngleStart + 90)
        for step in range(1, self.rangeLen - 1):
            qp.rotate(deltaAngle)
            qp.drawLine(self.rangeInnerRadius, 0, self.scaleOuterRadius, 0)
        qp.restore()

    def resizeEvent(self, event=None):
        self.currentDialSize = min(self.width(), self.height()) - 2
        self.valueArcRect.setWidth(self.currentDialSize * self.valueArcRatio)
        self.valueArcRect.setHeight(self.currentDialSize * self.valueArcRatio)
        self.valueArcRect.moveCenter(self.rect().center())

        self.dialCenter = self.rect().center()
        self.valuePen.setWidthF(self.currentDialSize * .025)

        #TODO: the widget is square-sized, do we really need to recenter gradients?
        self.valueArcColorDisabled.setCenter(self.rect().center())
        self.valueArcColorEnabled.setCenter(self.rect().center())
        arcPenWidth = self.currentDialSize * self.valueArcPenRatio
        for color, pen in zip(self.valueArcColors, self.valueArcPens):
            pen.setBrush(color)
            pen.setWidthF(arcPenWidth)

        self.rangeOuterRadius = self.currentDialSize / 2
        self.rangeInnerRadius = self.rangeOuterRadius * self.rangeInnerRatio
        self.scaleOuterRadius = self.rangeOuterRadius * self.rangeScaleRatio
        self.rangeRect.setWidth(self.currentDialSize)
        self.rangeRect.setHeight(self.currentDialSize)
        self.rangeRect.moveCenter(self.dialCenter)
        self._computeRangeLines()

        self.dialSize = self.currentDialSize * self.dialRatio
        self.dialRect.setWidth(self.dialSize)
        self.dialRect.setHeight(self.dialSize)
        self.dialRect.moveCenter(self.dialCenter)

        #set cursor size and pos
        self.cursorRect.setWidth(self.currentDialSize * self.cursorSize)
        self.cursorRect.setHeight(self.currentDialSize * self.cursorSize)
        self._computeCursorPos()
        self.showValue(self.keepValueVisible)

    def _computeCursorPos(self):
        xRatio = math.cos(math.radians(self.angleValue))
        yRatio = math.sin(math.radians(self.angleValue))
        self.cursorRect.moveCenter(QtCore.QPointF(
            self.dialCenter.x() + self.cursorPosRadius * xRatio * self.dialSize / 2, 
            self.dialCenter.y() - self.cursorPosRadius * yRatio * self.dialSize / 2)
            )

    def contextMenu(self, pos):
        if self.editor:
            self.editor.hide()
            self.editor.deleteLater()
            self.editor = None
        menu = QtWidgets.QMenu(self)
        setValueAction = menu.addAction('Set value...', self.mouseDoubleClickEvent)
        menu.addSeparator()
        defaultValueText = self.valueList[(self.defaultValue - self.minimum) // self.step]
        menu.addAction('Restore default value ({})'.format(defaultValueText), lambda: self.setValue(self.defaultValue))
        menu.setDefaultAction(setValueAction)
        menu.exec_(self.mapToGlobal(pos))

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.RightButton:
            return QtWidgets.QWidget.mousePressEvent(self, event)
        elif event.button() == QtCore.Qt.MidButton:
            self.setValue(self.defaultValue)
            return QtWidgets.QWidget.mousePressEvent(self, event)
        self.setToolTip('')
        x = event.pos().x()
        y = event.pos().y()
#        self.pressPoint = x, y
        squarePos = ((x - self.dialCenter.x()) ** 2) + ((y - self.dialCenter.y()) ** 2)
        self._prevMousePos = event.pos()
        if event.pos() in self.cursorRect:
            self.mouseMoveEvent = self._mouseMoveRadial
            self.setCursor(QtCore.Qt.ClosedHandCursor)
        elif squarePos < (self.rect().width() / 2) ** 2:
            #inside dial scale
            if squarePos < (self.dialRect.width() / 2) ** 2:
                #inside dial
                self.mouseMoveEvent = self._mouseMoveCoord
                self.setCursor(QtCore.Qt.SizeAllCursor)
            else:
                self.mouseMoveEvent = self._mouseMoveRadial
                self.setCursor(QtCore.Qt.ClosedHandCursor)
        else:
            #inside cursor
            self.mouseMoveEvent = self._mouseMoveCoord
            self.setCursor(QtCore.Qt.SizeAllCursor)
        self.update()
        if self.editor:
            try:
                self.editor.deleteLater()
                self.editor = None
            except:
                pass
            self.editor = None
        self.setFocus(QtCore.Qt.MouseFocusReason)
        self.showValue(True)
#        QtCore.QTimer.singleShot(0, lambda: QtWidgets.QToolTip.showText(self.mapToGlobal(self._prevMousePos), self.valueList[self.value], self))
        QtWidgets.QWidget.mousePressEvent(self, event)

    def mouseReleaseEvent(self, event):
#        QtWidgets.QToolTip.showText(self.mapToGlobal(event.pos()), self.valueList[self.value], self, self.rect())
        self.setToolTip(self.valueList[self._currentIndex])
        self._prevMousePos = None
        self.showValue(False)
        self.unsetCursor()

    def _mouseMoveCoord(self, event):
        if not self._prevMousePos:
            self._prevMousePos = event.pos()
            return
        deltaValue = (-self._prevMousePos.x() + event.x() + self._prevMousePos.y() - event.y())
        if self.step == 1 and self.rangeLen >= 24:
            self.setValue(self.value + deltaValue * self.step * .01 * self.rangeLen)
        else:
            ratio = (.02 * self.rangeLen * self.step)
            self.setValue(self.getClosestValue(self.value + deltaValue * ratio))
        self._prevMousePos = event.pos()
#        QtWidgets.QToolTip.showText(self.mapToGlobal(self._prevMousePos), self.valueList[self.value], self)

    def _mouseMoveRadial(self, event):
        angle = (QtCore.QLineF(self.rect().center(), event.pos()).angle())
        targetAngle = (self.rangeAngleStartMath - angle) % 360
        if targetAngle > self.rangeAngleSpan + (360 - self.rangeAngleSpan) / 2:
            targetAngle = self.rangeAngleStart
            angle = self.rangeAngleStartMath
            #set min value
        elif targetAngle > self.rangeAngleSpan:
            targetAngle = self.rangeAngleSpan
            angle = (self.rangeAngleStartMath + self.rangeAngleSpanMath) % 360
            #set max value
        absoluteValue = ((self.rangeAngleStartMath - angle) % 360) / self.rangeAngleSpan
        fullRange = self.maximum - self.minimum + 1
        baseRange = fullRange - (fullRange & 1)
        if absoluteValue < self.centerRatio:
            realValue = self.minimum + baseRange * absoluteValue / (self.centerRatio * 2)
        else:
            postRangeLen = fullRange - 2 + (fullRange & 1)
            realValue = self.minimum + baseRange * .5 + postRangeLen * (absoluteValue - self.centerRatio) / ((1 - self.centerRatio) * 2)
        value = round(realValue)
        if not value in self.rangeValues:
            value = self.getClosestValue(value)
        self.setValue(value)
#        QtWidgets.QToolTip.showText(self.mapToGlobal(event.pos()), self.valueList[self.value], self)

    def mouseDoubleClickEvent(self, event=None):
        self.mouseMoveEvent = lambda ev: QtWidgets.QWidget.mouseMoveEvent(self, ev)
        if event and event.button() != QtCore.Qt.LeftButton:
            return
        self.editor = ValueEditor(self)
        self.editor.setPalette(self.palette())
        self.editor.show()
        self.editor.setFocus(QtCore.Qt.OtherFocusReason)
        self.editor.destroyed.connect(lambda: setattr(self, 'editor', None))

    def focusOutEvent(self, event):
        if self.editor and not self.editor.hasFocus():
            self.editor.deleteLater()
            self.editor = None

    def wheelEvent(self, event):
        ratio = 5 if event.modifiers() == QtCore.Qt.ShiftModifier else 1
        if __binding__ == 'PyQt4':
            delta = 1 if event.delta() > 0 else -1
        else:
            delta = 1 if event.angleDelta().y() > 0 else -1
#        if event.angleDelta().x() > 0 or event.angleDelta().y () > 0:
        delta *= ratio
#        self.setCurrentIndex(self._currentIndex + delta)
        self.stepBy(delta)
        if self.editor:
            self.editor.deleteLater()
            self.editor = None
        self.setFocus(QtCore.Qt.MouseFocusReason)
        self.showValue(True)
        if not self.keepValueVisible:
            self.showValueTimer.start()

    def stepBy(self, steps):
        self.setCurrentIndex(self._currentIndex + steps)

class Dial(ColorValueWidget):
    valueChanged = QtCore.pyqtSignal(int)
    currentIndexChanged = QtCore.pyqtSignal(int)
    valueChangedStr = QtCore.pyqtSignal(str)

    def __init__(self, parent=None, label='dial', labelPos=QtCore.Qt.BottomEdge, *args, **kwargs):
        ColorValueWidget.__init__(self, parent, label, labelPos)
#        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred))
        self.dial = _Dial(self, *args, **kwargs)
        self.dial.valueChanged.connect(self.valueChanged)
        self.dial.currentIndexChanged.connect(self.currentIndexChanged)
        self.dial.valueChangedStr.connect(self.valueChangedStr)
        self.setWidget(self.dial)
#        self.setFont(QtGui.QFont('Droid Sans', 9, QtGui.QFont.Bold))
        self._paletteChanged(self.palette())
        self.showValue = self.dial.showValue

    @QtCore.pyqtSlot(int, int, int)
    def setRange(self, minimum, maximum, step):
        self.dial.setRange(minimum, maximum, step)

    value = makeQtChildProperty(int, 'value', '_setValue')

    @QtCore.pyqtSlot(object)
    def setValueList(self, valueList=None):
        if valueList is None:
            valueList = []
        self.widget.setValueList(valueList)

    @QtCore.pyqtSlot(int)
    def setValue(self, value):
        self.dial.setValue(value)

    minimum = makeQtChildProperty(int, 'minimum', 'setMinimum')

    @QtCore.pyqtSlot(int)
    def setMinimum(self, minimum):
        self.minimum = minimum

    maximum = makeQtChildProperty(int, 'maximum', 'setMaximum')

    @QtCore.pyqtSlot(int)
    def setMaximum(self, value):
        self.maximum = value

    step = makeQtChildProperty(int, 'step', 'setStep')

    @QtCore.pyqtSlot(int)
    def setStep(self, step):
        self.step = step

    defaultValue = makeQtChildProperty(int, 'defaultValue', 'setDefaultValue')

    @QtCore.pyqtSlot(int)
    def setDefaultValue(self, value):
        self.defaultValue = value

    rangeAngleStart = makeQtChildProperty(int, 'rangeAngleStart', 'setRangeAngleStart')

    @QtCore.pyqtSlot(int)
    def setRangeAngleStart(self, rangeAngleStart):
        self.rangeAngleStart = rangeAngleStart

    rangeZeroAngle = makeQtChildProperty(int, 'rangeZeroAngle', 'setRangeZeroAngle')

    gradientScale = makeQtChildProperty(bool, 'gradientScale', 'setGradientScale')
    centerEven = makeQtChildProperty(bool, 'centerEven', 'setCenterEven')
    centerAngle = makeQtChildProperty(int, 'centerAngle', 'setCenterAngle')
    rangeColorStart = makeQtChildProperty(QtGui.QColor, 'rangeColorStartEnabled', 'setRangeColorStart')
    rangeColorZero = makeQtChildProperty(QtGui.QColor, 'rangeColorZeroEnabled', 'setRangeColorZero')
    rangeColorEnd = makeQtChildProperty(QtGui.QColor, 'rangeColorEndEnabled', 'setRangeColorEnd')

#    pointerColor = makeQtChildProperty(QtGui.QColor, 'pointerColor', 'setPointerColor')
#    pointerCapStyle = makeQtChildProperty(QtCore.Qt.PenCapStyle, 'pointerCapStyle', 'setPointerCapStyle')

    @QtCore.pyqtProperty(QtGui.QColor)
    def rangePenColor(self):
        return self.dial.rangePen.color()

    @rangePenColor.setter
    def rangePenColor(self, color):
        self.dial.rangePen.setColor(color)

    @QtCore.pyqtProperty(QtGui.QColor)
    def scalePenColor(self):
        return self.dial.scalePen.color()

    @scalePenColor.setter
    def scalePenColor(self, color):
        self.dial.scalePen.setColor(color)

    @QtCore.pyqtProperty(QtGui.QColor)
    def pointerColor(self):
        return self.dial.valuePen.color()

    @pointerColor.setter
    def pointerColor(self, color):
        self.dial.valuePen.setColor(color)

    @QtCore.pyqtProperty(QtCore.Qt.PenCapStyle)
    def pointerCapStyle(self):
        return self.dial.valuePen.capStyle()

    @pointerCapStyle.setter
    def pointerCapStyle(self, capStyle):
        self.dial.valuePen.setCapStyle(capStyle)

    keepValueVisible = makeQtChildProperty(bool, 'keepValueVisible', 'setKeepValueVisible')

    def resizeEventg(self, event):
        if not self._label:
            height = self.height() * .98
            width = self.width() * .98
        elif self._labelPos & (QtCore.Qt.TopEdge|QtCore.Qt.BottomEdge):
            height = self.height() * .98 - self._labelWidget.height() - self._labelMargin
            width = self.width() * .98
        else:
            height = self.height() * .98
            width = self.width() * .98 - self._labelWidget.width() - self._labelMargin
        finalSize = round(min(height, width))
        self.dial.setMaximumSize(finalSize, finalSize)
        #Debug repainting
#        QtCore.QTimer.singleShot(0, self.dial.update)


if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)
    try:
        v = int(sys.argv[1])
    except:
        v = 10
    widget = QtWidgets.QWidget()
    layout = QtWidgets.QHBoxLayout()
    widget.setLayout(layout)
    dial1 = Dial(label='asdfd agagag', valueList=[str(v) for v in range(v)], maximum=v-1)
#    dial1.setValue(96)
    layout.addWidget(dial1)
    dial2 = Dial(label='puppa', labelPos=QtCore.Qt.LeftEdge, valueList=['value {}'.format(v) for v in range(v + 1)], maximum=v + 5)
    layout.addWidget(dial2)
    dial3 = Dial(label='asdf', labelPos=QtCore.Qt.TopEdge, maximum=32, step=4)
    layout.addWidget(dial3)
#    widget.setMinimumSize(640, 480)
#    widget = Dial(label='Some dial')
    widget.show()
    sys.exit(app.exec_())
