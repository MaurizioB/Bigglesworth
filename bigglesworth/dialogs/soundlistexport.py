from string import uppercase
from collections import OrderedDict
import json
from Qt import QtCore, QtGui, QtWidgets, QtPrintSupport

from bigglesworth.const import factoryPresetsNamesDict, LocationColumn, NameColumn, CatColumn, TagsColumn, chr2ord
from bigglesworth.utils import loadUi, localPath, Enum
from bigglesworth.parameters import categories

ValidRole = QtCore.Qt.UserRole + 1
SortRole = ValidRole + 1
PrinterRole = SortRole + 1
PrinterInfoRole = PrinterRole + 1
MarginsRole = PrinterInfoRole + 1

class PageMarginsWidget(QtWidgets.QWidget):
    def setPrinter(self, printer):
        self.printer = printer
        self.page = printer.paperSize(printer.Millimeter)
        self.pageWidth = self.page.width()
        self.pageHeight = self.page.height()
        self.orientation = printer.orientation()
        self.left, self.top, self.right, self.bottom = printer.getPageMargins(printer.Millimeter)
        self.pointRatio = self.logicalDpiX() / 76.
        self.padding = 10 * self.pointRatio
        self.shadowDelta = 3 * self.pointRatio
        self.pagePen = QtGui.QPen(QtCore.Qt.black, self.pointRatio * .5)
        self.marginPen = QtGui.QPen(QtCore.Qt.darkGray, self.pointRatio * .5, QtCore.Qt.DotLine)
        self.textPen = QtGui.QPen(QtCore.Qt.darkGray, self.pointRatio * 1.5)

    def setMargins(self, margins):
        self.left, self.top, self.right, self.bottom = margins
        self.update()

    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        qp.setRenderHints(qp.Antialiasing)
        qp.drawRect(self.rect())
        qp.translate(.5, .5)

        realWidth = self.rect().width() - 1 - self.padding
        realHeight = self.rect().height() - 1 - self.padding
        xRatio = realWidth / self.pageWidth
        yRatio = realHeight / self.pageHeight
        ratio = min(xRatio, yRatio)
        pageRect = QtCore.QRectF(0, 0, self.pageWidth * ratio, self.pageHeight * ratio)
        pageRect.moveCenter(self.rect().center())

        shadow = pageRect.translated(self.shadowDelta, self.shadowDelta)
        qp.setPen(QtCore.Qt.NoPen)
        qp.setBrush(QtCore.Qt.lightGray)
        qp.drawRect(shadow)

        qp.setPen(self.pagePen)
        qp.setBrush(QtCore.Qt.white)
        qp.drawRect(pageRect)

        qp.setBrush(QtCore.Qt.NoBrush)
        qp.setPen(self.marginPen)
        marginRect = pageRect.adjusted(self.left * ratio, self.top * ratio, -self.right * ratio, -self.bottom * ratio)
        qp.drawRect(marginRect)

        qp.setPen(self.textPen)
        textPadding = ratio * 5
        textRect = marginRect.adjusted(textPadding, 2 * textPadding, -textPadding, -textPadding)
        qp.drawLine(textRect.center().x() - 10 * ratio, textRect.top(), textRect.center().x() + 10 * ratio, textRect.top())
        qp.translate(0, textRect.top() + textPadding)
        lines = 40
        lineRatio = (textRect.height() - textPadding * 2) / lines
        for line in range(lines):
            qp.drawLine(textRect.left(), 0, textRect.right(), 0)
            qp.translate(0, lineRatio)


class MarginsEditor(QtWidgets.QDialog):
    Centimeters, Millimeters, Inches, Points = Enum(4)

    def __init__(self, parent, printer, defaults):
        QtWidgets.QDialog.__init__(self, parent)
        loadUi(localPath('ui/printmargins.ui'), self)
        self.printer = printer
        self.defaults = defaults
        self.pagePreview.setPrinter(printer)
        self.setWindowTitle('Set margins for "{}"'.format(QtPrintSupport.QPrinterInfo(printer)))

        self.page = printer.pageRect(printer.Millimeter)
        self.margins = self.left, self.top, self.right, self.bottom = list(printer.getPageMargins(printer.Millimeter))
        self.leftSpin.setValue(self.left * 10)
        self.topSpin.setValue(self.top * 10)
        self.rightSpin.setValue(self.right * 10)
        self.bottomSpin.setValue(self.bottom * 10)

        self.mode = self.Centimeters
        self.units = {
            #unit: (suffix,mm2unit, unit2mm)
            self.Centimeters: (' cm', lambda v: v * .1, lambda v: v * 10), 
            self.Millimeters: (' mm', lambda v: v, lambda v: v), 
            self.Inches: (' in', self.mm2inch, self.inch2mm), 
            self.Points: (' pt', self.mm2point, self.point2mm), 
            }

        self.spinBoxes = self.leftSpin, self.topSpin, self.rightSpin, self.bottomSpin
        for spin in self.spinBoxes:
            spin.valueChanged.connect(self.setMargins)

        if QtCore.QLocale().measurementSystem():
            self.unitCombo.setCurrentIndex(2)
            self.setConversion(2)
        else:
            self.setConversion(0)

        self.unitCombo.currentIndexChanged.connect(self.setConversion)
        self.restoreBtn = self.buttonBox.button(self.buttonBox.RestoreDefaults)
        self.restoreBtn.setIcon(QtGui.QIcon.fromTheme('edit-undo'))
        self.restoreBtn.clicked.connect(self.setDefaults)

    def setConversion(self, unit):
        suffix, self.mm2unit, self.unit2mm = self.units[unit]
        for spin, margin in zip(self.spinBoxes, self.margins):
            spin.blockSignals(True)
            spin.setValue(self.mm2unit(margin))
            spin.setSuffix(suffix)
            spin.blockSignals(False)
        self.pagePreview.setMargins(self.margins)

    def setDefaults(self):
        self.margins = self.left, self.top, self.right, self.bottom = self.defaults
        for spin, margin in zip(self.spinBoxes, self.margins):
            spin.blockSignals(True)
            spin.setValue(self.mm2unit(margin))
            spin.blockSignals(False)
        self.pagePreview.setMargins(self.margins)

    def setMargins(self):
        oldLeft, oldTop, oldRight, oldBottom = self.margins
        margins = []
        for spin in self.spinBoxes:
            margins.append(self.unit2mm(spin.value()))
        left, top, right, bottom = margins
        if left + right > self.page.width():
            if self.sender() == self.leftSpin:
                left = oldLeft
                self.leftSpin.blockSignals(True)
                self.leftSpin.setValue(self.mm2unit(left))
                self.leftSpin.blockSignals(False)
            else:
                right = oldRight
                self.rightSpin.blockSignals(True)
                self.rightSpin.setValue(self.mm2unit(right))
                self.rightSpin.blockSignals(False)
        if top + bottom > self.page.height():
            if self.sender() == self.topSpin:
                top = oldTop
                self.topSpin.blockSignals(True)
                self.topSpin.setValue(self.mm2unit(top))
                self.topSpin.blockSignals(False)
            else:
                bottom = oldBottom
                self.bottomSpin.blockSignals(True)
                self.bottomSpin.setValue(self.mm2unit(bottom))
                self.bottomSpin.blockSignals(False)

        self.margins = self.left, self.top, self.right, self.bottom = left, top, right, bottom
        self.pagePreview.setMargins(self.margins)

    def mm2inch(self, value):
        return value * .0393701

    def inch2mm(self, value):
        return value * 25.4

    def mm2point(self, value):
        return value * 2.8346

    def point2mm(self, value):
        return value * .3527

    def exec_(self):
        res = QtWidgets.QDialog.exec_(self)
        if res:
            return self.margins


class Borders(QtCore.QObject):
    changed = QtCore.pyqtSignal()
    background = QtGui.QColor(QtCore.Qt.white)
    alternate = QtGui.QColor(221, 234, 255)
    hLine = QtGui.QPen(QtCore.Qt.darkGray, .5)
    vLine = QtGui.QPen(QtCore.Qt.darkGray, .5)
    leftBorder = topBorder = rightBorder = bottomBorder = False

    def setBackground(self, color):
        self.background = color
        self.changed.emit()

    def setAlternate(self, alternate):
        self.alternate = alternate
        self.changed.emit()

    def setHLine(self, pen):
        self.hLine = pen
        self.changed.emit()

    def setVLine(self, pen):
        self.vLine = pen
        self.changed.emit()

    def setLeftBorder(self, border):
        self.leftBorder = border
        self.changed.emit()

    def setTopBorder(self, border):
        self.topBorder = border
        self.changed.emit()

    def setRightBorder(self, border):
        self.rightBorder = border
        self.changed.emit()

    def setBottomBorder(self, border):
        self.bottomBorder = border
        self.changed.emit()

    def setBorders(self, borders):
        self.leftBorder, self.topBorder, self.rightBorder, self.bottomBorder = borders
        self.changed.emit()

    @property
    def contours(self):
        return self.leftBorder, self.topBorder, self.rightBorder, self.bottomBorder

    def clone(self):
        borders = Borders()
        borders.background = self.background
        borders.alternate = self.alternate
        borders.hLine = self.hLine
        borders.vLine = self.vLine
        borders.leftBorder = self.leftBorder
        borders.topBorder = self.topBorder
        borders.rightBorder = self.rightBorder
        borders.bottomBorder = self.bottomBorder
        return borders


class BordersPreview(QtWidgets.QWidget):
    def __init__(self, borders, baseFont, baseFontColor, vSpacing):
        QtWidgets.QWidget.__init__(self)
        self.borders = borders
        self.baseFont = baseFont
        self.baseFontColor = baseFontColor
        self.baseFontMetrics = QtGui.QFontMetrics(baseFont)
        self.setMinimumHeight(self.baseFontMetrics.height() * 8)
        self.setMinimumWidth(self.baseFontMetrics.width('A001 ABCDEFGHIJKLMNOP') * 5)
        self.vSpacing = vSpacing

        self.names = [
            ['Bigglesworth', 'Do you agree?', 'Maybe U could', 'Surely... I\'d'], 
            ['It\'s a wonderful', 'I really did', 'Consider to...', 'Appreciate I.T.'], 
            ['Editor 4', 'A lot of work', 'Make A small', '& Will'], 
            ['Your Blofeld', 'Developing it', 'Don A.tion', 'Be thankful!'], 
        ]

    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        qp.setRenderHints(qp.Antialiasing)
        qp.fillRect(self.rect(), QtCore.Qt.white)
        hRatio = self.rect().width() / 5.
        lineHeight = self.baseFontMetrics.height() + self.vSpacing
        left = self.baseFontMetrics.width('  ')
        qp.translate(int(hRatio * .5) + .5, int(self.baseFontMetrics.height() * 1.5) + .5)

        width = hRatio * 4
        height = lineHeight * 4

        qp.save()

        leftBorder, topBorder, rightBorder, bottomBorder = self.borders.contours
        qp.setPen(self.borders.vLine)
        if leftBorder:
            qp.drawLine(0, 0, 0, height)
        if rightBorder:
            qp.drawLine(width, 0, width, height)
        qp.setPen(self.borders.hLine)
        if topBorder:
            qp.drawLine(0, 0, width, 0)
        if bottomBorder:
            qp.drawLine(0, height, width, height)


        if self.borders.background:
            qp.setPen(QtCore.Qt.NoPen)
            if not self.borders.alternate:
                qp.setBrush(self.borders.background)
                qp.drawRect(0, 0, width, height)
            else:
                qp.save()
                for row in range(4):
                    if row & 1:
                        qp.setBrush(self.borders.alternate)
                    else:
                        qp.setBrush(self.borders.background)
                    qp.drawRect(0, 0, width, lineHeight)
                    qp.translate(0, lineHeight)
                qp.restore()

        if self.borders.hLine:
            qp.save()
            qp.setPen(self.borders.hLine)
            for i in range(3):
                qp.drawLine(0, lineHeight, width, lineHeight)
                qp.translate(0, lineHeight)
            qp.restore()

        if self.borders.vLine:
            qp.save()
            qp.setPen(self.borders.vLine)
            qp.translate(hRatio, 0)
            for i in range(3):
                qp.drawLine(0, 0, 0, height)
                qp.translate(hRatio, 0)
            qp.restore()

        qp.restore()

        count = 0
        for line in self.names:
            qp.save()
            for name in line:
                count += 1
                qp.drawText(left, 0, hRatio, lineHeight, QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter, 'A{:03}  {}'.format(count, name))
                qp.translate(hRatio, 0)
            qp.restore()
            qp.translate(0, lineHeight)


class BordersEditor(QtWidgets.QDialog):
    def __init__(self, parent, borders, baseFont, baseFontColor, vSpacing):
        QtWidgets.QDialog.__init__(self, parent)
        loadUi(localPath('ui/soundlistexportborders.ui'), self)
        self.borders = borders.clone()

        if borders.background:
            self.backgroundChk.setChecked(True)
            self.backgroundColorBtn.setColor(borders.background)
        if borders.alternate:
            self.alternateChk.setChecked(True)
            self.alternateColorBtn.setColor(borders.alternate)

        if borders.hLine:
            self.hLineGroupBox.setChecked(True)
            self.hPenColorBtn.setColor(borders.hLine.color())
            self.hPenStyleCombo.setCurrentIndex(borders.hLine.style() - 1)
            self.hPenWidthSpin.setValue(borders.hLine.widthF())
        if borders.vLine:
            self.vLineGroupBox.setChecked(True)
            self.vPenColorBtn.setColor(borders.vLine.color())
            self.vPenStyleCombo.setCurrentIndex(borders.vLine.style() - 1)
            self.vPenWidthSpin.setValue(borders.vLine.widthF())

        self.borderChecks = self.leftChk, self.topChk, self.rightChk, self.bottomChk
        for chk in self.borderChecks:
            chk.toggled.connect(self.checkBorders)

        if borders.leftBorder:
            self.leftChk.setChecked(True)
        if borders.topBorder:
            self.topChk.setChecked(True)
        if borders.rightBorder:
            self.rightChk.setChecked(True)
        if borders.bottomBorder:
            self.bottomChk.setChecked(True)

        self.backgroundColorBtn.colorChanged.connect(self.borders.setBackground)
        self.backgroundChk.toggled.connect(lambda state: self.borders.setBackground(self.backgroundColorBtn.color if state else state))

        self.alternateColorBtn.colorChanged.connect(self.borders.setAlternate)
        self.alternateChk.toggled.connect(lambda state: self.borders.setAlternate(self.alternateColorBtn.color if state else state))

        self.hLineGroupBox.toggled.connect(self.setHLine)
        self.hLineGroupBox.toggled.connect(self.checkBorders)
        self.hPenColorBtn.colorChanged.connect(self.setHLine)
        self.hPenStyleCombo.currentIndexChanged.connect(self.setHLine)
        self.hPenWidthSpin.valueChanged.connect(self.setHLine)
        self.copyVerticalBtn.clicked.connect(self.copyVtoH)

        self.vLineGroupBox.toggled.connect(self.setVLine)
        self.vLineGroupBox.toggled.connect(self.checkBorders)
        self.vPenColorBtn.colorChanged.connect(self.setVLine)
        self.vPenStyleCombo.currentIndexChanged.connect(self.setVLine)
        self.vPenWidthSpin.valueChanged.connect(self.setVLine)
        self.copyHorizontalBtn.clicked.connect(self.copyHtoV)

        self.invertBtn.clicked.connect(self.invertBackground)
        self.previewWidget = BordersPreview(self.borders, baseFont, baseFontColor, vSpacing)
        self.previewLayout.addWidget(self.previewWidget)
        self.borders.changed.connect(self.previewWidget.update)

    def invertBackground(self):
        base = self.backgroundColorBtn.color
        alt = self.alternateColorBtn.color
        self.alternateColorBtn.setColor(base)
        self.backgroundColorBtn.setColor(alt)

    def checkBorders(self):
        hLine = self.hLineGroupBox.isChecked()
        vLine = self.vLineGroupBox.isChecked()
        self.bordersChk.setEnabled(any([hLine, vLine]))
        states = []
        for o, chk in enumerate(self.borderChecks):
            if o & 1:
                chk.setEnabled(hLine)
            else:
                chk.setEnabled(vLine)
            states.append(chk.isChecked())
        self.borders.setBorders(states)
        self.bordersChk.blockSignals(True)
        self.bordersChk.setChecked(all(states))
        self.bordersChk.blockSignals(False)

    def setHLine(self):
        if self.hLineGroupBox.isChecked():
            pen = QtGui.QPen(self.hPenColorBtn.color, self.hPenWidthSpin.value(), self.hPenStyleCombo.currentIndex() + 1)
        else:
            pen = False
        self.borders.setHLine(pen)

    def copyVtoH(self):
#        self.borders.setHLine(self.borders.vLine)
        self.hPenColorBtn.setColor(self.borders.vLine.color())
        self.hPenStyleCombo.setCurrentIndex(self.borders.vLine.style() - 1)
        self.hPenWidthSpin.setValue(self.borders.vLine.widthF())

    def copyHtoV(self):
#        self.borders.setVLine(self.borders.hLine)
        self.vPenColorBtn.setColor(self.borders.hLine.color())
        self.vPenStyleCombo.setCurrentIndex(self.borders.hLine.style() - 1)
        self.vPenWidthSpin.setValue(self.borders.hLine.widthF())

    def setVLine(self):
        if self.vLineGroupBox.isChecked():
            pen = QtGui.QPen(self.vPenColorBtn.color, self.vPenWidthSpin.value(), self.vPenStyleCombo.currentIndex() + 1)
        else:
            pen = False
        self.borders.setVLine(pen)

    def exec_(self):
        res = QtWidgets.QDialog.exec_(self)
        if res:
            return self.borders.clone()
        return res


class HeaderFrame(QtCore.QObject):
    changed = QtCore.pyqtSignal()
    framePen = QtGui.QPen(QtCore.Qt.black, .5, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap)
#    frameBrush = QtGui.QBrush(QtCore.Qt.transparent)
    frameBrush = None
    extended = False
    _leftMargin = _topMargin = _rightMargin = _bottomMargin = 4
    roundX = roundY = 2

    def setPenColor(self, color):
#        if not self.framePen:
#            self.framePen = QtGui.QPen()
#            self.framePen.setWidth(1)
        self.framePen.setColor(color)
        self.changed.emit()

    def setPen(self, pen):
        self.framePen = pen
        self.changed.emit()

    def setPenStyle(self, style):
#        if not self.framePen:
#            self.framePen = QtGui.QPen(QtCore.Qt.black)
#            self.framePen.setWidth(1)
        self.framePen.setStyle(style)
        self.changed.emit()

    def setPenWidth(self, width):
#        if not self.framePen:
#            self.framePen = QtGui.QPen(QtCore.Qt.black)
        self.framePen.setWidthF(width)
        self.changed.emit()

    def setBrush(self, color):
        if not color:
            self.frameBrush = color
        else:
            if not self.frameBrush:
                self.frameBrush = QtGui.QBrush(QtCore.Qt.SolidPattern)
            self.frameBrush.setColor(color)
        self.changed.emit()

    def setLeftMargin(self, margin):
        self.leftMargin = margin

    @property
    def leftMargin(self):
        return self._leftMargin

    @leftMargin.setter
    def leftMargin(self, margin):
        self._leftMargin = margin
        self.changed.emit()

    def setTopMargin(self, margin):
        self.topMargin = margin

    @property
    def topMargin(self):
        return self._topMargin

    @topMargin.setter
    def topMargin(self, margin):
        self._topMargin = margin
        self.changed.emit()

    def setRightMargin(self, margin):
        self.rightMargin = margin

    @property
    def rightMargin(self):
        return self._rightMargin

    @rightMargin.setter
    def rightMargin(self, margin):
        self._rightMargin = margin
        self.changed.emit()

    def setBottomMargin(self, margin):
        self.bottomMargin = margin

    @property
    def bottomMargin(self):
        return self._bottomMargin

    @bottomMargin.setter
    def bottomMargin(self, margin):
        self._bottomMargin = margin
        self.changed.emit()

    @property
    def margins(self):
        return (0 if self.extended else -self.leftMargin, 
            -self.topMargin, 
            0 if self.extended else self.rightMargin, 
            self.bottomMargin)

    @margins.setter
    def margins(self, margins):
        self._leftMargin, self._topMargin, self._rightMargin, self._bottomMargin = margins
        self.changed.emit()

    def setRoundX(self, value):
        self.roundX = value
        self.changed.emit()

    def setRoundY(self, value):
        self.roundY = value
        self.changed.emit()

    def setExtended(self, extended):
        self.extended = extended
        self.changed.emit()

    @property
    def rounded(self):
        return (self.roundX, self.roundY) if self.roundX and self.roundY else False

    def clone(self):
        headerFrame = HeaderFrame()
        headerFrame.framePen = self.framePen
        headerFrame.frameBrush = self.frameBrush
        headerFrame.extended = self.extended
        headerFrame.leftMargin = self.leftMargin
        headerFrame.rightMargin = self.rightMargin
        headerFrame.topMargin = self.topMargin
        headerFrame.bottomMargin = self.bottomMargin
        headerFrame.roundX = self.roundX
        headerFrame.roundY = self.roundY
        return headerFrame


class HeaderPreview(QtWidgets.QWidget):
    def __init__(self, headerFrame, headerFont, headerFontColor):
        QtWidgets.QWidget.__init__(self)
        self.headerFrame = headerFrame
        self.headerFont = headerFont
        self.headerFontColor = headerFontColor
        self.headerMetrics = QtGui.QFontMetrics(headerFont)
        self.setMinimumHeight(self.headerMetrics.height() * 3)

    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        qp.setRenderHints(qp.Antialiasing)
        qp.fillRect(self.rect(), QtCore.Qt.white)
        qp.translate(.5, .5)
        qp.save()
        qp.setPen(self.headerFrame.framePen if self.headerFrame.framePen else QtCore.Qt.NoPen)
        if self.headerFrame.frameBrush:
            qp.setBrush(self.headerFrame.frameBrush)
        textRect = self.headerMetrics.boundingRect(self.rect(), QtCore.Qt.AlignCenter, 'Header test')
        if self.headerFrame.extended:
            left, top, right, bottom = self.headerFrame.margins
            textRect.setRight(self.rect().width() - 1 - qp.pen().width() * .5)
            textRect.setLeft(-.5 + qp.pen().width() * .5)
            textRect.setTop(textRect.top() + top)
            textRect.setBottom(textRect.bottom() + bottom)
            qp.drawRoundedRect(textRect, self.headerFrame.roundX, self.headerFrame.roundY)
        else:
            qp.drawRoundedRect(textRect.adjusted(*self.headerFrame.margins), self.headerFrame.roundX, self.headerFrame.roundY)
        qp.restore()
        qp.setPen(self.headerFontColor)
        qp.setFont(self.headerFont)
        qp.drawText(self.rect(), QtCore.Qt.AlignCenter, 'Header test')


class HeaderEditor(QtWidgets.QDialog):
    def __init__(self, parent, headerFrame, headerFont, headerFontColor):
        QtWidgets.QDialog.__init__(self, parent)
        loadUi(localPath('ui/soundlistexportheader.ui'), self)
        self.headerFrame = headerFrame.clone()
        if headerFrame.framePen:
            self.penGroupBox.setChecked(True)
            self.penColorBtn.setColor(headerFrame.framePen.color())
            self.penStyleCombo.setCurrentIndex(headerFrame.framePen.style() - 1)
            self.penWidthSpin.setValue(headerFrame.framePen.widthF())
        if headerFrame.frameBrush:
            self.brushChk.setChecked(True)
            self.brushColorBtn.setColor(headerFrame.frameBrush.color())
        self.leftSpin.setValue(headerFrame.leftMargin)
        self.topSpin.setValue(headerFrame.topMargin)
        self.rightSpin.setValue(headerFrame.rightMargin)
        self.bottomSpin.setValue(headerFrame.bottomMargin)
        self.roundXSpin.setValue(headerFrame.roundX)
        self.roundYSpin.setValue(headerFrame.roundY)
        self.extendChk.setChecked(headerFrame.extended)

        self.penGroupBox.toggled.connect(self.setBorder)
        self.penColorBtn.colorChanged.connect(self.headerFrame.setPenColor)
        self.penStyleCombo.currentIndexChanged.connect(lambda style: self.headerFrame.setPenStyle(style + 1))
        self.penWidthSpin.valueChanged.connect(self.headerFrame.setPenWidth)

        self.brushChk.toggled.connect(lambda state: self.headerFrame.setBrush(self.brushColorBtn.color if state else state))
        self.brushColorBtn.colorChanged.connect(self.headerFrame.setBrush)

        self.leftSpin.valueChanged.connect(self.headerFrame.setLeftMargin)
        self.topSpin.valueChanged.connect(self.headerFrame.setTopMargin)
        self.rightSpin.valueChanged.connect(self.headerFrame.setRightMargin)
        self.bottomSpin.valueChanged.connect(self.headerFrame.setBottomMargin)
        self.roundXSpin.valueChanged.connect(self.headerFrame.setRoundX)
        self.roundYSpin.valueChanged.connect(self.headerFrame.setRoundY)

        self.penGroupBox.toggled.connect(self.checkMargins)
        self.brushChk.toggled.connect(self.checkMargins)

        self.extendChk.toggled.connect(self.headerFrame.setExtended)

        self.previewWidget = HeaderPreview(self.headerFrame, headerFont, headerFontColor)
        self.previewLayout.addWidget(self.previewWidget)
        self.headerFrame.changed.connect(self.previewWidget.update)

    def checkMargins(self):
        self.marginGroupBox.setEnabled(self.penGroupBox.isChecked() or self.brushChk.isChecked())

    def setBorder(self, state):
        if not state:
            self.headerFrame.setPen(state)
        else:
            pen = QtGui.QPen(self.penColorBtn.color, self.penWidthSpin.value(), 
                self.penStyleCombo.currentIndex() + 1, QtCore.Qt.RoundCap)
            self.headerFrame.setPen(pen)

    def exec_(self):
        res = QtWidgets.QDialog.exec_(self)
        if res:
            return self.headerFrame.clone()
        return res


class PreviewPanel(QtWidgets.QWidget):
    prev = QtCore.pyqtSignal()
    next = QtCore.pyqtSignal()
    single = QtCore.pyqtSignal()
    multi = QtCore.pyqtSignal()
    fitToggled = QtCore.pyqtSignal(bool)

    def __init__(self, parent):
        QtWidgets.QWidget.__init__(self, parent)
        layout = QtWidgets.QGridLayout()
        self.setLayout(layout)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Maximum))
        self.setStyleSheet('''
        PreviewPanel {
            border: 1px solid palette(mid);
            border-style: outset;
            border-radius: 4px;
            background: palette(midlight);
        }
        ''')

        self.pageLbl = QtWidgets.QLabel()
        self.pageLbl.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.pageLbl, 0, 1, 1, 3)

        self.prevBtn = QtWidgets.QPushButton(QtGui.QIcon.fromTheme('go-previous'), '', self)
        self.prevBtn.clicked.connect(self.prev)
        self.prevBtn.setToolTip('Go to previous page')
        layout.addWidget(self.prevBtn, 0, 0, 2, 1)

        self.singleBtn = QtWidgets.QPushButton(QtGui.QIcon.fromTheme('page-simple'), '', self)
        self.singleBtn.clicked.connect(self.single)
        self.singleBtn.setToolTip('Show single pages')
        layout.addWidget(self.singleBtn)

        self.fitBtn = QtWidgets.QPushButton(QtGui.QIcon.fromTheme('page-zoom'), '', self)
        self.fitBtn.setCheckable(True)
        self.fitBtn.toggled.connect(self.fitToggled)
        self.fitBtn.setToolTip('Toggle zoom mode')
        layout.addWidget(self.fitBtn)

        self.multiBtn = QtWidgets.QPushButton(QtGui.QIcon.fromTheme('page-2sides'), '', self)
        self.multiBtn.clicked.connect(self.multi)
        self.multiBtn.setToolTip('Show facing pages side by side')
        layout.addWidget(self.multiBtn)

        self.nextBtn = QtWidgets.QPushButton(QtGui.QIcon.fromTheme('go-next'), '', self)
        self.nextBtn.clicked.connect(self.next)
        self.nextBtn.setToolTip('Go to next page')
        layout.addWidget(self.nextBtn, 0, 4, 2, 1)

        self.opacity = QtWidgets.QGraphicsOpacityEffect()
        self.opacity.setOpacity(.5)
        self.setGraphicsEffect(self.opacity)
        self.opacityAnimation = QtCore.QPropertyAnimation(self.opacity, b'opacity')
        self.opacityAnimation.setStartValue(.5)
        self.opacityAnimation.setEndValue(1)
        self.opacityAnimation.setDuration(250)

    def setPage(self, current, count):
        self.prevBtn.setEnabled(current > 1)
        self.nextBtn.setEnabled(current < count)
        self.pageLbl.setText('{} / {}'.format(current, count))

    def enterEvent(self, event):
        self.opacityAnimation.setDirection(self.opacityAnimation.Forward)
        self.opacityAnimation.start()
#        self.opacity.setOpacity(1)

    def leaveEvent(self, event):
        self.opacityAnimation.setDirection(self.opacityAnimation.Backward)
        self.opacityAnimation.start()
#        self.opacity.setOpacity(.7)

    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        option = QtWidgets.QStyleOption()
        option.init(self)
        self.style().drawPrimitive(QtWidgets.QStyle.PE_Widget, option, qp, self)


class PrintPreview(QtPrintSupport.QPrintPreviewWidget):
    def __init__(self, *args, **kwargs):
        QtPrintSupport.QPrintPreviewWidget.__init__(self, *args, **kwargs)
        self.view = self.findChildren(QtWidgets.QGraphicsView)[0]
        self.panel = PreviewPanel(self)
        self.panel.next.connect(self.nextPage)
        self.panel.prev.connect(lambda: self.setCurrentPage(self.currentPage() - 1))
        self.panel.single.connect(lambda: self.setViewMode(self.SinglePageView))
        self.panel.multi.connect(lambda: self.setViewMode(self.FacingPagesView))
        self.panel.fitToggled.connect(lambda fit: [self.fitToWidth, self.fitInView][fit]())
        #horizontal scroll bar disabled for some strange recursive bug
        self.view.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.verticalScrollBar = self.view.verticalScrollBar()
        self.verticalScrollBar.valueChanged.connect(self.updatePanel)
        self.fitToWidth()

    def scrollToTop(self):
        self.verticalScrollBar.setValue(self.verticalScrollBar.minimum())

    def nextPage(self):
        current = self.currentPage()
        if self.viewMode() and not current & 1:
            self.setCurrentPage(current + 2)
        else:
            self.setCurrentPage(current + 1)

    def updatePanel(self):
        self.panel.setPage(self.currentPage(), self.pageCount())

    def resizeEvent(self, event):
        QtPrintSupport.QPrintPreviewWidget.resizeEvent(self, event)
        self.panel.move(5, self.height() - self.panel.height() - 5)

    def _wheelEvent(self, event):
        print('paggina')
        if event.delta() > 0:
            delta = 1
        else:
            delta = -1
        self.setCurrentPage(self.currentPage() + delta)
        print(self.currentPage())


class CollectionModel(QtCore.QSortFilterProxyModel):
    showAll = False
    def showAll(self, state):
        self.showAll = state
        self.invalidateFilter()

    def filterAcceptsRow(self, row, parent):
        return self.sourceModel().index(row, NameColumn).flags() & QtCore.Qt.ItemIsEnabled and self.showAll


class BaseOrderDialog(QtWidgets.QDialog):
    def __init__(self, parent, rows, orderModel=None):
        QtWidgets.QDialog.__init__(self, parent)
        loadUi(localPath('ui/soundlistexportorder.ui'), self)
        self.model = QtGui.QStandardItemModel()
        self.listView.setModel(self.model)

        for row, label in enumerate(rows):
            item = QtGui.QStandardItem(label)
            item.setData(row, SortRole)
            self.model.appendRow(item)

        if orderModel is not None:
            self.sort(orderModel)

        self.ascendingBtn.clicked.connect(self.resort)
        self.descendingBtn.clicked.connect(lambda: self.resort(True))

        self.topBtn.clicked.connect(self.moveToTop)
        self.upBtn.clicked.connect(self.moveUp)
        self.downBtn.clicked.connect(self.moveDown)
        self.bottomBtn.clicked.connect(self.moveBottom)

    def sort(self, orderModel):
        items = {}
        for _ in range(self.model.rowCount()):
            item = self.model.takeRow(0)[0]
            items[item.data(SortRole)] = item
        for row in orderModel:
            self.model.appendRow(items[row])

    def resort(self, reverse=False):
        items = {}
        for row in range(self.model.rowCount()):
            item = self.model.takeRow(0)[0]
            items[item.data(SortRole)] = item
        for row in sorted(items, reverse=reverse):
            self.model.appendRow(items[row])

    def moveToTop(self):
        rows = [index.row() for index in self.listView.selectionModel().selectedRows()]
        if not rows or min(rows) == 0:
            return
        taken = []
        for row in reversed(rows):
            taken.append(self.model.takeRow(row))
        new = QtCore.QItemSelection()
        for row in taken:
            self.model.insertRow(0, row)
            index = self.model.indexFromItem(row[0])
            new.select(index, index)
        self.listView.selectionModel().select(new, QtCore.QItemSelectionModel.SelectCurrent)

    def moveUp(self):
        rows = sorted([index.row() for index in self.listView.selectionModel().selectedRows()])
        if not rows or min(rows) == 0:
            return
        taken = OrderedDict()
        for row in reversed(rows):
            taken[row] = self.model.takeRow(row)[0]
        new = QtCore.QItemSelection()
        for row, item in reversed(taken.items()):
            self.model.insertRow(row - 1, item)
            index = self.model.indexFromItem(item)
            new.select(index, index)
        self.listView.selectionModel().select(new, QtCore.QItemSelectionModel.SelectCurrent)

    def moveDown(self):
        rows = sorted([index.row() for index in self.listView.selectionModel().selectedRows()])
        if not rows or max(rows) == self.model.rowCount() - 1:
            return
        taken = OrderedDict()
        for row in reversed(rows):
            taken[row] = self.model.takeRow(row)[0]
        new = QtCore.QItemSelection()
        for row, item in reversed(taken.items()):
            self.model.insertRow(row + 1, item)
            index = self.model.indexFromItem(item)
            new.select(index, index)
        self.listView.selectionModel().select(new, QtCore.QItemSelectionModel.SelectCurrent)

    def moveBottom(self):
        rows = sorted([index.row() for index in self.listView.selectionModel().selectedRows()])
        if not rows or max(rows) == self.model.rowCount() - 1:
            return
        taken = OrderedDict()
        for row in reversed(rows):
            taken[row] = self.model.takeRow(row)[0]
        new = QtCore.QItemSelection()
        for row, item in reversed(taken.items()):
            self.model.insertRow(self.model.rowCount(), item)
            index = self.model.indexFromItem(item)
            new.select(index, index)
        self.listView.selectionModel().select(new, QtCore.QItemSelectionModel.SelectCurrent)

    def exec_(self):
        res = QtWidgets.QDialog.exec_(self)
        if res:
            order = []
            for row in range(self.model.rowCount()):
                order.append(self.model.item(row).data(SortRole))
            return order

class BankOrder(BaseOrderDialog):
    def __init__(self, parent=None, orderModel=None):
        rows = ['Bank {}'.format(bank) for bank in uppercase[:8]]
        BaseOrderDialog.__init__(self, parent, rows, orderModel)


class AlphaOrder(BaseOrderDialog):
    def __init__(self, parent=None, orderModel=None):
        rows = ['Starting with "{}"'.format(l) for l in uppercase] + ['Starting with numbers or special characters']
        BaseOrderDialog.__init__(self, parent, rows, orderModel)


class CatOrder(BaseOrderDialog):
    def __init__(self, parent=None, orderModel=None):
        BaseOrderDialog.__init__(self, parent, categories, orderModel)


class TagsOrder(BaseOrderDialog):
    def __init__(self, parent=None, orderModel=None):
        tagsModel = QtWidgets.QApplication.instance().database.tagsModel
        rows = sorted([tagsModel.index(row, 0).data() for row in range(tagsModel.rowCount())])
        BaseOrderDialog.__init__(self, parent, rows, orderModel)


class SoundListExport(QtWidgets.QDialog):
    shown = False
    Banks, Alpha, Cat, Tags = Enum(4)

    alphaLabels = list(uppercase) + ['0..9..']

    paperSizes = OrderedDict(
        sorted((size, label) for label, size in QtPrintSupport.QPrinter.__dict__.items() 
            if isinstance(size, QtPrintSupport.QPrinter.PageSize)))

    def __init__(self, parent, collection=None):
        QtWidgets.QDialog.__init__(self, parent)
        loadUi(localPath('ui/soundlistexport.ui'), self)
        self.main = QtWidgets.QApplication.instance()
        self.database = self.main.database
        self.allCollections = self.database.referenceModel.allCollections
        tagsModel = QtWidgets.QApplication.instance().database.tagsModel
        self.tags = sorted([tagsModel.index(row, 0).data() for row in range(tagsModel.rowCount())])
        self.tagLabels = self.tags + ['No tags']

        self.validIcons = QtGui.QIcon.fromTheme('emblem-warning'), QtGui.QIcon.fromTheme('checkbox')
        self.okBtn = self.buttonBox.button(self.buttonBox.Ok)

        self.textEdit.setStyleSheet('''
            QTextEdit {
                font-family: monospace;
                padding: 10px;
            }
        ''')
        self.currentLayout = OrderedDict()
        self.cache = {}
        self.emptyCache = {}
        self.bankChecks = []
        self.borders = Borders()
        self.headerFrame = HeaderFrame()

        for bank in uppercase[:8]:
            chk = getattr(self, 'bank{}Chk'.format(bank))
            self.bankChecks.append(chk)
            chk.valid = False
            chk.toggled.connect(self.updateBankChecks)
            chk.toggled.connect(lambda: self.checkOrder())

        currentIndex = 0
        for i, c in enumerate(self.allCollections):
            collName = factoryPresetsNamesDict.get(c, c)
            self.collectionCombo.addItem(collName)
            self.collectionCombo.setItemData(i, c)
            if c in factoryPresetsNamesDict:
                self.collectionCombo.setItemIcon(i, QtGui.QIcon(':/images/factory.svg'))
            elif c == 'Blofeld':
                self.collectionCombo.setItemIcon(i, QtGui.QIcon(':/images/bigglesworth_logo.svg'))
            if c == collection:
                currentIndex = i
        self.collectionCombo.setCurrentIndex(currentIndex)
        self.collectionCombo.currentIndexChanged.connect(self.setCollection)

        self.allBanksChk.toggled.connect(self.checkAllBanks)
        self.validBanksChk.toggled.connect(self.checkValidBanks)

        self.sortCombo.currentIndexChanged.connect(self.setSortRule)
        self.orderCombo.currentIndexChanged.connect(self.checkOrder)
        self.orderEditBtn.clicked.connect(self.editOrder)

        self.exportTabWidget.currentChanged.connect(self.updatePreview)
        self.exportTabWidget.currentChanged.connect(self.setOkButton)

        font = self.font()
        self.fontCombo.setCurrentFont(font)
        self.fontCombo.currentFontChanged.connect(self.updatePdf)
        self.fontSizeSpin.setValue(font.pointSizeF())
        self.fontSizeSpin.valueChanged.connect(self.updatePdf)
        self.boldBtn.setChecked(font.bold())
        self.boldBtn.toggled.connect(self.updatePdf)
        self.italicBtn.setChecked(font.italic())
        self.italicBtn.toggled.connect(self.updatePdf)
        self.underlineBtn.setChecked(font.underline())
        self.underlineBtn.toggled.connect(self.updatePdf)
        self.textColorBtn.colorChanged.connect(self.updatePdf)

        self.lineSpacingSpin.valueChanged.connect(self.updatePdf)
        self.horizontalSpacingSpin.valueChanged.connect(self.updatePdf)
        self.justifyChk.toggled.connect(self.updatePdf)
        self.pageBreakChk.toggled.connect(self.updatePdf)
        self.bordersChk.toggled.connect(self.updatePdf)
        self.borderEditBtn.clicked.connect(self.editBorders)

        self.pdfOptionsBtn.toggled.connect(self.togglePdfOptions)
        self.customHeaderBox.toggled.connect(self.updatePdf)
        self.headerFontCombo.setCurrentFont(font)
        self.headerFontCombo.currentFontChanged.connect(self.updatePdf)
        self.headerFontSizeSpin.setValue(font.pointSizeF() + 4)
        self.headerFontSizeSpin.valueChanged.connect(self.updatePdf)
        self.headerBoldBtn.setChecked(font.bold())
        self.headerBoldBtn.toggled.connect(self.updatePdf)
        self.headerItalicBtn.setChecked(font.italic())
        self.headerItalicBtn.toggled.connect(self.updatePdf)
        self.headerUnderlineBtn.setChecked(font.underline())
        self.headerUnderlineBtn.toggled.connect(self.updatePdf)
        self.headerTextColorBtn.colorChanged.connect(self.updatePdf)

        self.headerTopMarginSpin.valueChanged.connect(self.updatePdf)
        self.headerBottomMarginSpin.valueChanged.connect(self.updatePdf)
        self.headerAlignmentGroup.setId(self.headerLeftChk, QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.headerAlignmentGroup.setId(self.headerCenterChk, QtCore.Qt.AlignCenter)
        self.headerAlignmentGroup.setId(self.headerRightChk, QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter)
        self.headerAlignmentGroup.buttonClicked.connect(self.updatePdf)
        self.headerFrameChk.toggled.connect(self.updatePdf)
        self.headerFrameEditBtn.clicked.connect(self.editHeader)

        self.pdfOrientationCombo.currentIndexChanged.connect(self.setPdfOrientation)
        self.paperCombo.currentIndexChanged.connect(self.setPaperSize)

        self.orderDialogs = {
            self.Banks: BankOrder, 
            self.Alpha: AlphaOrder, 
            self.Cat: CatOrder, 
            self.Tags: TagsOrder, 
        }

        self.previewMode = {
            self.fileTab: self.updateTxt, 
            self.printTab: self.updatePdf, 
        }

        self.previewWidgets = {}
        self.printPreview = None

        self.pdfPrinter = QtPrintSupport.QPrinter(QtPrintSupport.QPrinter.HighResolution)
        self.pdfPrinter.setOutputFormat(self.pdfPrinter.PdfFormat)
        self.pdfPrinter.setPageMargins(160, 160, 160, 160, self.pdfPrinter.DevicePixel)
        self.pdfPrinter.setFontEmbeddingEnabled(True)
        self.pdfPrinter.setPaperSize(self.pdfPrinter.A4)

        self.printerCombo.addItem(QtGui.QIcon.fromTheme('document-new'), 'PDF file')
        self.printerCombo.setItemData(0, self.pdfPrinter, PrinterRole)
        self.printerCombo.setItemData(0, QtPrintSupport.QPrinterInfo(self.pdfPrinter), PrinterInfoRole)
        self.printerCombo.setItemData(0, self.pdfPrinter.getPageMargins(self.pdfPrinter.Millimeter), MarginsRole)

#        currentPrinter = 0
        for i, printerInfo in enumerate(QtPrintSupport.QPrinterInfo.availablePrinters(), 1):
            if printerInfo.isDefault():
                self.defaultPrinter = printer = QtPrintSupport.QPrinter(printerInfo, QtPrintSupport.QPrinter.HighResolution)
                self.printerCombo.addItem('{} (default)'.format(printerInfo.printerName()))
                font = self.font()
                font.setBold(True)
                self.printerCombo.setItemData(i, font, QtCore.Qt.FontRole)
#                currentPrinter = i
            else:
                self.printerCombo.addItem(printerInfo.printerName())
                printer = QtPrintSupport.QPrinter(printerInfo, QtPrintSupport.QPrinter.HighResolution)
#            printer.setFullPage(True)
            printer.setPaperSize(printer.A4)
            self.printerCombo.setItemIcon(i, QtGui.QIcon.fromTheme('document-print'))
            self.printerCombo.setItemData(i, printer, PrinterRole)
            self.printerCombo.setItemData(i, printerInfo, PrinterInfoRole)
            self.printerCombo.setItemData(i, printer.getPageMargins(printer.Millimeter), MarginsRole)
#        self.printerCombo.setCurrentIndex(currentPrinter)
        self.printerCombo.currentIndexChanged.connect(self.setPrinter)
        self.printerCombo.currentIndexChanged.connect(self.setOkButton)
#        self.setPrinter(currentPrinter)
        self.setPrinter(0)

        self.emptySlotsChk.toggled.connect(lambda: self.checkOrder())
        self.stripSpacesChk.toggled.connect(self.updatePreview)
        self.addBanksChk.toggled.connect(self.updatePreview)
        self.leadingZerosChk.toggled.connect(self.updatePreview)
        self.leadingZerosChk.toggled.connect(self.updatePreview)
        self.columnSpin.valueChanged.connect(self.updatePreview)
        self.orientationCombo.currentIndexChanged.connect(self.updatePreview)

        self.txtSpacingSpin.valueChanged.connect(self.updateTxt)
        self.txtSectionSpacingSpin.valueChanged.connect(self.updateTxt)
        self.txtCenterChk.toggled.connect(self.updateTxt)
        self.txtHighlighChk.toggled.connect(self.updateTxt)

        self.marginsBtn.clicked.connect(self.editMargins)

        self.setCollection(currentIndex)
        self.setOkButton()
        self.pdfOptions.hide()

    def accept(self):
        if self.exportTabWidget.currentWidget() == self.fileTab:
            path = QtWidgets.QFileDialog.getSaveFileName(self, 'Export to text file', 
                QtGui.QDesktopServices.storageLocation(QtGui.QDesktopServices.DocumentsLocation) + '/Blofeld library.txt', 
                'Text files (*.txt);;All files (*)')
            if not path:
                return
            try:
                with open(path, 'w') as fb:
                    fb.write(self.textEdit.toPlainText())
            except:
                QtWidgets.QMessageBox.warning(self, 'Error writing file', 
                    'An error occurred while saving the file.\nCheck user permissions and available space.', 
                    QtWidgets.QMessageBox.Ok)
                return
        else:
            if self.currentPrinter == self.pdfPrinter:
                path = QtWidgets.QFileDialog.getSaveFileName(self, 'Export to PDF file', 
                    QtGui.QDesktopServices.storageLocation(QtGui.QDesktopServices.DocumentsLocation) + '/Blofeld library.pdf', 
                    'PDF files (*.pdf);;PostScript (*.ps);;All files (*)')
                if path:
                    self.pdfPrinter.setOutputFileName(path)
                else:
                    return
            else:
                if not QtPrintSupport.QPrintDialog(self.currentPrinter, self).exec_():
                    return
            self.previewContainer.currentWidget().print_()
        QtWidgets.QDialog.accept(self)


    def setOkButton(self):
        if self.exportTabWidget.currentWidget() == self.fileTab:
            save = True
        else:
            save = True if self.currentPrinter == self.pdfPrinter else False
        if save:
            self.okBtn.setText('Save')
            self.okBtn.setIcon(QtGui.QIcon.fromTheme('document-save'))
        else:
            self.okBtn.setText('Print')
            self.okBtn.setIcon(QtGui.QIcon.fromTheme('document-print'))

    def editMargins(self):
        defaults = self.printerCombo.itemData(self.printerCombo.currentIndex(), MarginsRole)
        res = MarginsEditor(self, self.currentPrinter, defaults).exec_()
        if res:
            left, top, right, bottom = res
            self.currentPrinter.setPageMargins(left, top, right, bottom, self.currentPrinter.Millimeter)
            self.updatePdf()

    def editBorders(self):
        res = BordersEditor(self, self.borders, self.currentFont, self.textColorBtn.color, 
            self.lineSpacingSpin.value()).exec_()
        if res:
            self.borders = res
            self.updatePdf()

    def editHeader(self):
        res = HeaderEditor(self, self.headerFrame, self.currentHeaderFont, self.headerTextColorBtn.color).exec_()
        if res:
            self.headerFrame = res
            self.updatePdf()

    def showEvent(self, event):
        if not self.shown:
            self.shown = True
            maxWidth = self.fontMetrics().width('-32') * 4
            for spin in self.pdfOptions.findChildren(QtWidgets.QSpinBox):
                spin.setMinimumWidth(maxWidth)
            self.printPreview.scrollToTop()

    @property
    def currentFont(self):
        font = self.fontCombo.currentFont()
        font.setPointSizeF(self.fontSizeSpin.value())
        font.setBold(self.boldBtn.isChecked())
        font.setItalic(self.italicBtn.isChecked())
        font.setUnderline(self.underlineBtn.isChecked())
        return font

    @property
    def currentHeaderFont(self):
        if self.customHeaderBox.isChecked():
            font = self.headerFontCombo.currentFont()
            font.setPointSizeF(self.headerFontSizeSpin.value())
            font.setBold(self.headerBoldBtn.isChecked())
            font.setItalic(self.headerItalicBtn.isChecked())
            font.setUnderline(self.headerUnderlineBtn.isChecked())
        else:
            font = self.currentFont
            font.setPointSizeF(font.pointSize() + 4)
        return font

    def updateBankChecks(self):
        checked = []
        valid = []
        for chk in self.bankChecks:
            checked.append(chk.isChecked())
            valid.append(chk.valid and chk.isChecked())

        self.allBanksChk.blockSignals(True)
        self.allBanksChk.setChecked(all(checked))
        self.allBanksChk.blockSignals(False)

        self.validBanksChk.blockSignals(True)
        self.validBanksChk.setChecked(all(valid))
        self.validBanksChk.blockSignals(False)

    def checkAllBanks(self, state):
        for chk in self.bankChecks:
            chk.blockSignals(True)
            chk.setChecked(state)
            chk.blockSignals(False)
        self.validBanksChk.blockSignals(True)
        self.validBanksChk.setChecked(False)
        self.validBanksChk.blockSignals(False)
        self.checkOrder()

    def checkValidBanks(self, state):
        count = 0
        for chk in self.bankChecks:
            chk.blockSignals(True)
            chk.setChecked(state and chk.valid if state else True)
            chk.blockSignals(False)
            if state and chk.valid:
                count += 1
        self.allBanksChk.blockSignals(True)
        self.allBanksChk.setChecked(all(chk.isChecked() for chk in self.bankChecks))
        self.allBanksChk.blockSignals(False)
        self.validBanksChk.blockSignals(True)
        self.validBanksChk.setChecked(count)
        self.validBanksChk.blockSignals(False)
        self.checkOrder()

    def checkOrder(self, order=None):
        if order is None:
            order = self.orderCombo.currentIndex()
        if order == 4:
            self.orderEditBtn.setEnabled(True)
#            self.setCustomOrder(self.sortCombo.currentIndex())
        else:
            self.orderEditBtn.setEnabled(False)
        self.setSortRule(self.sortCombo.currentIndex(), order)

    def setSortRule(self, index, order=None):
        self.validBanksChk.setDisabled(index)
        self.emptySlotsChk.setDisabled(index)

        if order is None:
            order = self.orderCombo.currentIndex()
        if index == 0:
            self.sortBanks(order)
        elif index == 1:
            self.sortAlpha(order)
        elif index == 2:
            self.sortCat(order)
        else:
            self.sortTags(order)
        self.updatePreview()

    def setOrder(self, order):
        if order == 4:
            orderModel = self.sortCombo.itemData(self.sortCombo.currentIndex())
            if not orderModel:
                order = 0
            else:
                new = OrderedDict()
                for key in orderModel:
                    values = self.currentLayout.get(key)
                    if values is not None:
                        new[key] = values
                self.currentLayout = new
        if order in (2, 3):
            self.currentLayout = OrderedDict((k, v) for k, v in sorted(list(self.currentLayout.items()), key=lambda i: len(i[1])))
        if order in (1, 3):
            self.currentLayout = OrderedDict((k, v) for k, v in reversed(list(self.currentLayout.items())))

    def sortBanks(self, order):
        base = None
        cache = self.cache.get(self.collection)
        if cache:
            base = cache.get(self.Banks)
        else:
            self.cache[self.collection] = {}
        if not base:
            base = OrderedDict()
            for bank in range(8):
                bankList = base.setdefault(bank, [])
                bankShift = bank << 7
                for prog in range(128):
                    pos = bankShift + prog
                    index = self.model.index(pos, NameColumn)
                    bankList.append((bank, prog, index.data(QtCore.Qt.DisplayRole) if index.flags() & QtCore.Qt.ItemIsEnabled else None))
            self.cache[self.collection][self.Banks] = base

        includeEmpty = self.emptySlotsChk.isChecked()
        self.currentLayout.clear()
        for bank, items in base.items():
            if not self.bankChecks[bank].isChecked():
                continue
            bankList = self.currentLayout.setdefault(bank, [])
            for bank, prog, name in items:
                if name is not None or includeEmpty:
                    bankList.append((bank, prog, name))
            if not bankList:
                self.currentLayout.pop(bank)
        self.setOrder(order)

    def sortAlpha(self, order):
        base = None
        cache = self.cache.get(self.collection)
        if cache:
            base = cache.get(self.Alpha)
        else:
            self.cache[self.collection] = {}
        if not base:
            base = OrderedDict((i, []) for i in range(len(self.alphaLabels)))
            last = base.values()[-1]
            for prog in range(1024):
                index = self.model.index(prog, NameColumn)
                if index.flags() & QtCore.Qt.ItemIsEnabled:
                    name = index.data()
                    try:
                        charList = base[uppercase.index(name[0])]
                    except:
                        charList = last
                    charList.append((prog >> 7, prog & 127, name))
            self.cache[self.collection][self.Alpha] = base

        self.currentLayout.clear()
        for alpha, items in base.items():
            alphaList = self.currentLayout.setdefault(alpha, [])
            for bank, prog, name in items:
                if self.bankChecks[bank].isChecked():
                    alphaList.append((bank, prog, name))
            if not alphaList:
                self.currentLayout.pop(alpha)
        self.setOrder(order)


    def sortCat(self, order):
        base = None
        cache = self.cache.get(self.collection)
        if cache:
            base = cache.get(self.Cat)
        else:
            self.cache[self.collection] = {}
        if not base:
            base = OrderedDict((i, []) for i in range(len(categories)))
            for prog in range(1024):
                index = self.model.index(prog, NameColumn)
                if index.flags() & QtCore.Qt.ItemIsEnabled:
                    name = index.data()
                    cat = self.model.index(prog, CatColumn).data()
                    base[cat].append((prog >> 7, prog & 127, name))
            self.cache[self.collection][self.Cat] = base

        self.currentLayout.clear()
        for cat, items in base.items():
            catList = self.currentLayout.setdefault(cat, [])
            for bank, prog, name in items:
                if self.bankChecks[bank].isChecked():
                    catList.append((bank, prog, name))
            if not catList:
                self.currentLayout.pop(cat)
        self.setOrder(order)


    def sortTags(self, order):
        base = None
        cache = self.cache.get(self.collection)
        if cache:
            base = cache.get(self.Tags)
        else:
            self.cache[self.collection] = {}
        if not base:
            base = OrderedDict((i, []) for i in range(len(self.tagLabels)))
            last = base.values()[-1]
            for prog in range(1024):
                index = self.model.index(prog, NameColumn)
                if index.flags() & QtCore.Qt.ItemIsEnabled:
                    name = index.data()
                    try:
                        tags = json.loads(self.model.index(prog, TagsColumn).data())
                        if not tags:
                            last.append((prog >> 7, prog & 127, name))
                        for tag in tags:
                            base[self.tags.index(tag)].append((prog >> 7, prog & 127, name))
                    except Exception as e:
                        print('Tag search exception', type(e), e)
                        last.append((prog >> 7, prog & 127, name))
            self.cache[self.collection][self.Tags] = base

        self.currentLayout.clear()
        for tag, items in base.items():
            tagList = self.currentLayout.setdefault(tag, [])
            for bank, prog, name in items:
                if self.bankChecks[bank].isChecked():
                    tagList.append((bank, prog, name))
            if not tagList:
                self.currentLayout.pop(tag)
        self.setOrder(order)

    def editOrder(self):
        sortRule = self.sortCombo.currentIndex()
        dialog = self.orderDialogs[sortRule](self, self.sortCombo.itemData(sortRule))
        orderModel = dialog.exec_()
        if orderModel is not None:
            self.sortCombo.setItemData(sortRule, orderModel)
            self.setOrder(4)
            self.updatePreview()

    def setCollection(self, index):
        self.collection = self.collectionCombo.itemData(index)
#        self.model.setSourceModel(self.database.openCollection(collection))
        self.model= self.database.openCollection(self.collection)
        valid = self.emptyCache.get(self.collection)
        if valid is None:
            valid = []
            for bank in range(8):
                bankShift = bank << 7
                for prog in range(128):
                    if self.model.index(bankShift + prog, NameColumn).flags() & QtCore.Qt.ItemIsEnabled:
                        valid.append(bank)
                        break
            self.emptyCache[self.collection] = valid
        checkValid = self.validBanksChk.isChecked()
        for i, chk in enumerate(self.bankChecks):
            chk.valid = i in valid
            if checkValid:
                chk.blockSignals(True)
                chk.setChecked(chk.valid)
                chk.blockSignals(False)
        self.checkOrder()

    def togglePdfOptions(self, show):
        self.pdfOptionsBtn.setText('Hide options' if show else 'Show options')
        self.pdfOptions.setVisible(show)

    def updatePreview(self):
        self.previewMode[self.exportTabWidget.currentWidget()]()

    def updateTxt(self):
        mode = self.sortCombo.currentIndex()
        if mode == self.Banks:
            keys = ['Bank {}'.format(bank) for bank in uppercase[:8]]
        elif mode == self.Alpha:
            keys = self.alphaLabels
        elif mode == self.Cat:
            keys = categories
        else:
            keys = ['Tag "{}"'.format(tag) for tag in self.tags] + ['No tags']
        content = ''
        addBanks = self.addBanksChk.isChecked()
        leading = '03' if self.leadingZerosChk.isChecked() else ''
        strip = self.stripSpacesChk.isChecked()
        columns = self.columnSpin.value()
        spacing = self.txtSpacingSpin.value()
        maxWidth = 22 + spacing
        sectionSpacing = self.txtSectionSpacingSpin.value()
        center = self.txtCenterChk.isChecked()
        totWidth = maxWidth * columns - spacing
        highlight = self.txtHighlighChk.isChecked()

        if self.orientationCombo.currentIndex():
            #vertical
            for key, items in self.currentLayout.items():
                keyTxt = keys[key]
                if center:
                    content += keyTxt.center(totWidth, ' ')
                    if highlight:
                        content += '\n' + ('=' * len(keyTxt)).center(totWidth, ' ')
                    content += '\n\n'
                else:
                    content += keyTxt
                    if highlight:
                        content += '\n' + ('=' * len(keyTxt))
                    content += '\n\n'
                maxRows, rest = divmod(len(items), columns)
                if rest:
                    maxRows += 1
                rows = ['' for _ in range(maxRows)]
                row = 0
                for bank, prog, name in items:
                    if name is None:
                        name = '(empty slot)'
                    line = ''
                    if addBanks:
                        line += uppercase[bank]
                    line += '{:{}}'.format(prog + 1, leading)
                    line = line.ljust(6, ' ')
                    if strip:
                        name = ' '.join(name.split())
                    line += name
                    rows[row] += line.ljust(maxWidth, ' ')
                    row += 1
                    if row == maxRows:
                        row = 0
                content += '\n'.join(rows) + '\n' * (sectionSpacing + 1)
        else:
            #horizontal
            for key, items in self.currentLayout.items():
                keyTxt = keys[key]
                if center:
                    content += keyTxt.center(totWidth, ' ')
                    if highlight:
                        content += '\n' + ('=' * len(keyTxt)).center(totWidth, ' ')
                    content += '\n\n'
                else:
                    content += keyTxt
                    if highlight:
                        content += '\n' + ('=' * len(keyTxt))
                    content += '\n\n'
                col = 0
                for bank, prog, name in items:
                    if name is None:
                        name = '(empty slot)'
                    line = ''
                    if addBanks:
                        line += uppercase[bank]
                    line += '{:{}}'.format(prog + 1, leading)
                    line = line.ljust(6, ' ')
                    if strip:
                        name = ' '.join(name.split())
                    line += name
                    col += 1
                    if col == columns:
                        col = 0
                        line += '\n'
                    else:
                        line = line.ljust(maxWidth, ' ')
                    content += line
                content += '\n' * (sectionSpacing + 1)
        try:
            scrollBar = self.textEdit.verticalScrollBar()
            pos = scrollBar.value() / float(scrollBar.maximum())
        except:
            pos = 0
        self.textEdit.setPlainText('\n'.join(line.rstrip() for line in content.split('\n')))
        self.textEdit.verticalScrollBar().setValue(pos * scrollBar.maximum())
        self.infoLbl.setText('{} lines, {} columns'.format(len(content.split('\n')), totWidth))
        self.validIcon.setVisible(False)

    def updatePdf(self):
#        print('pdf! update')
        mode = self.sortCombo.currentIndex()
        if mode == self.Banks:
            keys = ['Bank {}'.format(bank) for bank in uppercase[:8]]
        elif mode == self.Alpha:
            keys = self.alphaLabels
        elif mode == self.Cat:
            keys = categories
        else:
            keys = ['Tag "{}"'.format(tag) for tag in self.tags] + ['No tags']
        addBanks = self.addBanksChk.isChecked()
        leading = '03' if self.leadingZerosChk.isChecked() else ''
        strip = self.stripSpacesChk.isChecked()
        columns = self.columnSpin.value()

        self.pdfLayout = []
        if self.orientationCombo.currentIndex():
            #vertical
            for key, items in self.currentLayout.items():
                maxRows, rest = divmod(len(items), columns)
                if rest:
                    maxRows += 1
                lines = [[] for _ in range(maxRows)]
                row = 0
                for bank, prog, name in items:
                    if addBanks:
                        pos = '{}{:{}}'.format(uppercase[bank], prog + 1, leading)
                    else:
                        pos = '{:{}}'.format(prog + 1, leading)
                    if name is None:
                        name = '(empty slot)'
                    elif strip:
                        name = ' '.join(name.split())
                    lines[row].append((pos, name))
                    row += 1
                    if row == maxRows:
                        row = 0

                keyTxt = keys[key]
                self.pdfLayout.append((keyTxt, lines))
        else:
            #horizontal
            for key, items in self.currentLayout.items():
                lines = []
                col = 0
                currentLine = []
                for bank, prog, name in items:
                    if addBanks:
                        pos = '{}{:{}}'.format(uppercase[bank], prog + 1, leading)
                    else:
                        pos = '{:{}}'.format(prog + 1, leading)
                    if name is None:
                        name = '(empty slot)'
                    elif strip:
                        name = ' '.join(name.split())
                    currentLine.append((pos, name))
                    col += 1
                    if col == columns:
                        lines.append(currentLine)
                        currentLine = []
                        col = 0
                if currentLine:
                    lines.append(currentLine)

                keyTxt = keys[key]
                self.pdfLayout.append((keyTxt, lines))

        self.printPreview.updatePreview()

    def setPdfOrientation(self, orientation):
        self.printPreview.setOrientation(orientation)
        self.updatePdf()

    def getPaperSizes(self, requested):
        sizes = []
        for i in self.paperSizes:
            if i in requested:
                sizes.append((i, self.paperSizes[i]))
        return sizes

    def setPaperSize(self, index):
        self.currentPrinter.setPaperSize(self.paperCombo.itemData(index, PrinterRole))
        self.updatePdf()
        self.printPreview.scrollToTop()

    def setPrinter(self, index):
        self.currentPrinter = self.printerCombo.itemData(index, PrinterRole)
        self.currentPrinter.setOrientation(self.pdfOrientationCombo.currentIndex())
        printerInfo = self.printerCombo.itemData(index, PrinterInfoRole)

        if self.paperCombo.count():
            currentPaperSize = self.paperCombo.itemData(self.paperCombo.currentIndex(), PrinterRole)
        else:
            currentPaperSize = -1
        self.paperCombo.blockSignals(True)
        self.paperCombo.clear()
        paperSizes = self.getPaperSizes(printerInfo.supportedPaperSizes())
        sizes = [p for p, _ in paperSizes]
        if currentPaperSize not in sizes:
            currentPaperSize = min(sizes)
        currentPaperSizeIndex = 0
        for i, (p, name) in enumerate(paperSizes):
            self.paperCombo.addItem(name)
            self.paperCombo.setItemData(i, p, PrinterRole)
            if p == currentPaperSize:
                currentPaperSizeIndex = i
        self.paperCombo.setCurrentIndex(currentPaperSizeIndex)
        self.currentPrinter.setPaperSize(currentPaperSize)
        self.paperCombo.blockSignals(False)

        currentPreview = self.previewContainer.currentWidget()
        if currentPreview:
            currentPreview.paintRequested.disconnect()

        previous = self.printPreview
        self.printPreview = self.previewWidgets.get(index)
        if not self.printPreview:
            self.printPreview = self.previewWidgets.setdefault(index, PrintPreview(self.currentPrinter))
            self.previewContainer.addWidget(self.printPreview)
        self.printPreview.paintRequested.connect(self.drawPrinter)
        self.previewContainer.setCurrentWidget(self.printPreview)
        if previous:
            self.printPreview.blockSignals(True)
            self.printPreview.setZoomMode(previous.zoomMode())
            self.printPreview.setViewMode(previous.viewMode())
            self.printPreview.blockSignals(False)
        self.updatePdf()

    def drawPrinter(self, printer=None):
        def doBorders(remaining=None):
            if not remaining:
                remaining = len(lines)
                fromStart = True
                altDelta = 0
            else:
                fromStart = False
                altDelta = (len(lines) - remaining) % 2
            qp.save()
            maxLines = min(int((height - vPos) / lineSpacing) + 1, remaining)
            maxHeight = maxLines * lineSpacing
            if justify:
                right = width
            else:
                right = hSpacing * columns
            if borders.background:
                qp.setPen(QtCore.Qt.NoPen)
                if not borders.alternate:
                    qp.setBrush(borders.background)
                    qp.drawRect(0, 0, right, maxHeight)
                else:
                    qp.save()
                    for line in range(maxLines):
                        if line + altDelta & 1:
                            qp.setBrush(borders.alternate)
                        else:
                            qp.setBrush(borders.background)
                        qp.drawRect(0, 0, right, lineSpacing)
                        qp.translate(0, lineSpacing)
                    qp.restore()
            leftBorder, topBorder, rightBorder, bottomBorder = borders.contours
            if borders.hLine:
                pen = QtGui.QPen(borders.hLine)
                pen.setWidthF(pen.widthF() * pointRatio)
                qp.setPen(pen)
                if topBorder and fromStart:
                    qp.drawLine(0, 0, right, 0)
                qp.save()
                qp.translate(0, lineSpacing)
                for line in range(maxLines - int(not bottomBorder)):
                    qp.drawLine(0, 0, right, 0)
                    qp.translate(0, lineSpacing)
                qp.restore()
            if borders.vLine:
                pen = QtGui.QPen(borders.vLine)
                pen.setWidthF(pen.widthF() * pointRatio)
                qp.setPen(pen)
                if leftBorder:
                    qp.drawLine(0, 0, 0, maxHeight)
                qp.save()
                qp.translate(hSpacing, 0)
                for column in range(columns - int(not rightBorder)):
                    qp.drawLine(0, 0, 0, maxHeight)
                    qp.translate(hSpacing, 0)
                qp.restore()
            qp.restore()

        if not isinstance(printer, QtPrintSupport.QPrinter):
            printer = self.currentPrinter
        qp = QtGui.QPainter(printer)
        qp.setRenderHints(qp.Antialiasing)

        headerFont = self.currentHeaderFont
        headerMetrics = QtGui.QFontMetrics(headerFont, printer)
        headerHeight = headerMetrics.height()
        headerColor = self.headerTextColorBtn.color
        baseFont = self.currentFont
        baseMetrics = QtGui.QFontMetrics(baseFont, printer)
        baseHeight = baseMetrics.height()
        baseColor = self.textColorBtn.color

        pointRatio = baseHeight / baseFont.pointSizeF()

        left, top, right, bottom = printer.getPageMargins(printer.DevicePixel)
        fullPage = qp.viewport().adjusted(left, top, -right, -bottom)
        width = fullPage.width()
        height = fullPage.height()

#        qp.drawRect(fullPage)

        columns = self.columnSpin.value()
        lineSpacing = baseMetrics.lineSpacing() + self.lineSpacingSpin.value() * pointRatio
        pageBreak = self.pageBreakChk.isChecked()

        if self.bordersChk.isChecked():
            borders = self.borders
            if borders.leftBorder or borders.vLine:
                leftMargin = 4 * pointRatio
            else:
                leftMargin = 0
        else:
            borders = False
            leftMargin = 0
        if self.customHeaderBox.isChecked():
            headerAlignment = self.headerAlignmentGroup.checkedId()
            headerTop = self.headerTopMarginSpin.value() * pointRatio
            headerBottom = self.headerBottomMarginSpin.value() * pointRatio
            headerFrame = self.headerFrame if self.headerFrameChk.isChecked() else False
        else:
            headerAlignment = QtCore.Qt.AlignCenter
            headerTop = 16 * pointRatio
            headerBottom = 16 * pointRatio
            headerFrame = False

        indexMargin = '  '
        if self.justifyChk.isChecked():
            justify = True
            hSpacing = width / columns
        else:
            justify = False
            maxLetter = max(baseMetrics.width(l) for l in chr2ord)
            hSpacing = baseMetrics.width('000{}'.format(indexMargin)) + maxLetter * 16
            hSpacing += self.horizontalSpacingSpin.value() * pointRatio
            if self.addBanksChk.isChecked():
                hSpacing += max(baseMetrics.width(l) for l in 'ABCDEFGH')

        vPos = top
        qp.translate(left, vPos)
        qp.save()

        hValid = True
        renderedPages = 0
        for count, (section, lines) in enumerate(self.pdfLayout):
            if (pageBreak and count) or vPos + headerTop + headerHeight >= height:
                qp.restore()
                printer.newPage()
                qp.save()
                vPos = top
                renderedPages += 1

            headerRect = QtCore.QRectF(0, 0, width, headerHeight)
            qp.translate(0, headerTop)
            if headerFrame:
                if headerFrame.framePen:
                    pen = QtGui.QPen(headerFrame.framePen)
                    pen.setWidthF(pen.widthF() * pointRatio)
                    qp.setPen(pen)
                else:
                    qp.setPen(QtCore.Qt.NoPen)
                if headerFrame.frameBrush:
                    qp.setBrush(headerFrame.frameBrush)
                if headerFrame.extended:
                    frameRect = QtCore.QRect(0, 0, width, headerHeight)
                else:
                    headerWidth = headerMetrics.width(section)
                    frameRect = QtCore.QRect((width - headerWidth) / 2, 0, headerWidth, headerHeight)

                frameRect.adjust(*map(lambda m: m * pointRatio, headerFrame.margins))

                if headerAlignment & QtCore.Qt.AlignLeft:
                    headerRect.setLeft(headerFrame.leftMargin * pointRatio)
                    if not headerFrame.extended:
                        frameRect.moveLeft(0)
                elif headerAlignment & QtCore.Qt.AlignRight:
                    headerRect.setRight(headerRect.right() - headerFrame.rightMargin * pointRatio)
                    if not headerFrame.extended:
                        frameRect.moveRight(width)

                if headerFrame.rounded:
                    qp.drawRoundedRect(frameRect, headerFrame.roundX * pointRatio, headerFrame.roundY * pointRatio)
                else:
                    qp.drawRect(frameRect)

            qp.setFont(headerFont)
            qp.setPen(headerColor)
            qp.drawText(headerRect, headerAlignment, section)
            qp.translate(0, headerHeight + headerBottom)

            vPos += headerTop + headerHeight + headerBottom

            if borders:
                doBorders()

            qp.setFont(baseFont)
            qp.setPen(baseColor)
            for count, line in enumerate(lines):
                hPos = 0
                qp.save()
                for index, name in line:
                    text = '{i}{m}{n}'.format(i=index, m=indexMargin, n=name)
                    qp.drawText(leftMargin, 0, width, lineSpacing, QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter, text)
                    qp.translate(hSpacing, 0)
                    if hPos + baseMetrics.width(text) > width:
                        hValid = False
                    hPos += hSpacing
                qp.restore()
#                qp.drawText(0, 0, width, baseHeight, QtCore.Qt.AlignJustify|QtCore.Qt.AlignVCenter, lineText)
                vPos += lineSpacing
                if vPos >= height:
                    qp.restore()
                    printer.newPage()
                    vPos = top
                    if borders:
                        doBorders(len(lines) - count - 1)
                    qp.save()
                    renderedPages += 1
                else:
                    qp.translate(0, lineSpacing)
#                qp.drawLine(0, 0, fullPage.width(), 0)

        qp.restore()
#        qp.drawText(printer.pageRect(printer.DevicePixel), QtCore.Qt.AlignCenter, 'test')
        qp.end()
        self.infoLbl.setText('Total pages: {}{}'.format(renderedPages, '' if hValid else ' (outside margins)'))
        self.validIcon.setVisible(True)
        self.validIcon.setToolTip('The layout is valid' if hValid else 'There is a problem with the layout')
        self.validIcon.setPixmap(self.validIcons[hValid].pixmap(self.okBtn.iconSize()))


