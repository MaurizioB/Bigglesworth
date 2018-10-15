#!/usr/bin/env python

import sys

from Qt import QtCore, QtGui, QtWidgets, __binding__
#from metawidget import BaseWidget, _getCssQColorStr, _getCssQFontStr
from metawidget import _getCssQColorStr

if __binding__ == 'PyQt4':
    QtCore.Qt.TopEdge = QtCore.Qt.TopDockWidgetArea
    QtCore.Qt.LeftEdge = QtCore.Qt.LeftDockWidgetArea
    QtCore.Qt.RightEdge = QtCore.Qt.RightDockWidgetArea
    QtCore.Qt.BottomEdge = QtCore.Qt.BottomDockWidgetArea
    QtCore.Qt.Edge = QtCore.Qt.DockWidgetArea
else:
    from PyQt5.QtCore import Q_FLAGS
    QtCore.Q_FLAGS = Q_FLAGS

QtCore.pyqtSignal = QtCore.Signal
QtCore.pyqtProperty = QtCore.Property

class Section(QtWidgets.QWidget):
    shown = False

    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored))
        self.setColors(self.palette())

    def setColors(self, palette):
        self.pen = QtGui.QPen(palette.color(palette.Dark))
        background = palette.color(palette.Window).darker(115)
        background.setAlpha(160)
        self.brush = background

    def changeEvent(self, event):
        if event.type() == QtCore.QEvent.PaletteChange:
            self.setColors(self.palette())

    def showEvent(self, event):
        #add contents margins to underlying widgets to have actual margins within
        #the section itself
        if not self.shown:
            self.shown = True
            if not isinstance(self.parent(), Frame):
                return
            layout = self.parent().layout()
            rowStart, colStart, rowSpan, colSpan = layout.getItemPosition(layout.indexOf(self))
            if not colSpan:
                return

            for row in range(rowStart, rowStart + rowSpan):
                if colSpan == 1:
                    item = layout.itemAtPosition(row, colStart)
                    if not item or item.widget() == self or not item.widget().layout():
                        continue
                    if not sum(item.widget().layout().getContentsMargins()):
                        item.widget().layout().setContentsMargins(2, 0, 2, 0)
                else:
                    for col in range(colStart, colStart + colSpan):
                        item = layout.itemAtPosition(row, col)
                        if not item or item.widget() == self or not item.widget().layout():
                            continue
                        l, t, r, b = item.widget().layout().getContentsMargins()
                        if not l + r:
                            item.widget().layout().setContentsMargins(2, t, 2, b)


    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        qp.setRenderHints(qp.Antialiasing)
        qp.translate(.5, .5)
        qp.setPen(self.pen)
        qp.setBrush(self.brush)
        qp.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 2, 2)


class Frame(QtWidgets.QFrame):
    def __init__(self, parent=None, label='', labelPos=QtCore.Qt.TopLeftCorner, orientation=QtCore.Qt.Horizontal, fakeGroups=False):
        QtWidgets.QFrame.__init__(self, parent)
        self.fakeGroups = fakeGroups
        palette = self.palette()
        if fakeGroups:
            self.drawFrameFunc = self.drawFrameFakeGroups
            self.framePen = QtGui.QPen(palette.color(palette.Dark))
            background = palette.color(palette.Window).darker(115)
            background.setAlpha(160)
            self.frameBrush = background
        else:
            self.drawFrameFunc = self.drawFrameNormal
        self._label = label
        self._labelPos = labelPos
        self._labelColor = QtGui.QColor(palette.color(palette.Text))
        self._orientation = orientation
#        self._labelMargin = 2
        self._sunken = True
        self._padding = 2
        self._borderGradient = QtGui.QConicalGradient(QtCore.QPointF(.5, .5), 45)
        self._borderGradient.setCoordinateMode(QtGui.QConicalGradient.ObjectBoundingMode)
        self.borderPen = QtGui.QPen(self._borderGradient, 1)
        self._setBorderColor = self._borderHighlight = self.palette().color(self.palette().Midlight)
        self._borderColorChanged = False
        self._marginOverride = False
        self._labelRect = QtCore.QRectF()
        self._labelBackgroundPath = QtGui.QPainterPath()
        self.setPalette(self.palette())
        self.borderAnimation = QtCore.QPropertyAnimation(self, b'borderHighlight')
        self.borderAnimation.setStartValue(QtGui.QColor(*self._setBorderColor.getRgb()[:3] + (0, )))
        self.borderAnimation.setEndValue(self._setBorderColor)
        self.borderAnimation.valueChanged.connect(lambda value: self.update())
        self._setLabelRect()
        self._computeMargins()
        self._sectionsStr = []
        self._sections = []
        self._sectionWidgets = []
        self.sectionsDone = False
        self.contentArea = 0, 0, 0, 0
        self.installEventFilter(self)
        self.destroyed.connect(self.destroyEvent)

    def destroyEvent(self):
        self.borderAnimation.stop()

    def _breakLayout(self):
        if not self.layout() or (not self._sectionsStr and self._sectionWidgets):
            for section in reversed(self._sectionWidgets):
                section.deleteLater()
                self._sectionWidgets.pop()
            self._sections = []
            self.sectionsDone = False

    @QtCore.pyqtProperty('QStringList', designable=False)
    def sections(self):
        return self._sectionsStr

    @sections.setter
    def sections(self, sectionsStr):
#        print(framesStr)
        self._sectionsStr = sectionsStr
        self.sectionsDone = False
        self.doSections()

    def doSections(self):
        layout = self.layout()
        if not layout or not self._sectionsStr:
            self._breakLayout()
            return
        rowSize = 0
        sectionRowSize = 0
        colSize = 0
        sectionColSize = 0
        for widget in self.children():
            #ignore invisible widgets, probally part of Qt Designer layout manager
            if widget is layout or not widget.isVisible():
                continue
            r, c, rs, cs = layout.getItemPosition(layout.indexOf(widget))
            if isinstance(widget, Section):
                sectionRowSize = max(r + rs, sectionRowSize)
                sectionColSize = max(c + cs, sectionColSize)
                continue
            rowSize = max(r + rs, rowSize)
            colSize = max(c + cs, colSize)
        if self.sectionsDone and not (sectionRowSize > rowSize or sectionColSize > colSize):
            return
        for section in reversed(self._sectionWidgets):
            section.deleteLater()
            self._sectionWidgets.pop()

        #widgets are probably not layed out yet?
        if not rowSize or not colSize:
            return

        remove = []
        self._sections = []
        for sectionStr in self._sectionsStr:
            row, col, rowSpan, colSpan = map(int, sectionStr.split())
            if (row + rowSpan) > rowSize or (col + colSpan) > colSize:
                remove.append(sectionStr)
                continue
            self._sections.append((row, col, rowSpan, colSpan))
            if self.fakeGroups:
                continue
            section = Section()
            self._sectionWidgets.append(section)
            layout.addWidget(section, row, col, rowSpan, colSpan)
            section.lower()
#        for sectionStr in reversed(remove):
#            self._sectionWidgets.pop(self._sectionWidgets.index(sectionStr))
        self.sectionsDone = True

    def changeEvent(self, event):
        if event.type() == QtCore.QEvent.PaletteChange:
#            print('setPalette')
            self.setPalette(self.palette())

    def eventFilter(self, source, event):
        if event.type() == QtCore.QEvent.LayoutRequest:
#            print('layoutRequest')
            self.doSections()
        return False

    def setPalette(self, palette):
#        QtWidgets.QFrame.setPalette(self, palette)
        if self.fakeGroups:
            palette = self.palette()
            self.framePen = QtGui.QPen(palette.color(palette.Dark))
            background = palette.color(palette.Window).darker(115)
            background.setAlpha(160)
            self.frameBrush = background
        self._borderColor = self._borderHighlight = palette.color(palette.Midlight)
        if self._borderColorChanged:
            light = self._setBorderColor
            dark = self._setBorderColor.darker()
        else:
            light = palette.color(palette.Midlight)
            dark = palette.color(palette.Dark)
#        light = _getCssQColorStr(self._setBorderColor if not self._borderColorChanged else self._borderColor)
#        light = _getCssQColorStr(self.borderColor)
#        dark = _getCssQColorStr(palette.color(palette.Dark))
        if self._sunken:
            topleft = dark
            bottomright = light
        else:
            topleft = light
            bottomright = dark
        self._borderGradient.setColorAt(0, topleft)
        self._borderGradient.setColorAt(.249, topleft)
        self._borderGradient.setColorAt(.25, topleft)
        self._borderGradient.setColorAt(.5, topleft)
        self._borderGradient.setColorAt(.501, bottomright)
        self._borderGradient.setColorAt(.749, bottomright)
        self._borderGradient.setColorAt(.75, bottomright)
        self._borderGradient.setColorAt(.999, bottomright)
        self._borderGradient.setColorAt(1, topleft)
        self.borderPen.setBrush(self._borderGradient)
#        self.setStyleSheet('''
#            .Frame {{
#                border-top: 1px solid {topleft};
#                border-right: 1px solid {bottomright};
#                border-bottom: 1px solid {bottomright};
#                border-left: 1px solid {topleft};
#                border-radius: 2px;
#                }}
#            '''.format(
#                topleft=topleft, 
#                bottomright=bottomright, 
#                ))

    @QtCore.pyqtProperty(QtGui.QColor, designable=False)
    def borderHighlight(self):
        return self._borderHighlight

    @borderHighlight.setter
    def borderHighlight(self, value):
        self._borderHighlight = value

    def enterEvent(self, event):
        self.borderAnimation.setDirection(QtCore.QPropertyAnimation.Forward)
        self.borderAnimation.start()

    def leaveEvent(self, event):
        self.borderAnimation.setDirection(QtCore.QPropertyAnimation.Backward)
        self.borderAnimation.start()

    @QtCore.pyqtProperty(str)
    def label(self):
        return self._label

    @label.setter
    def label(self, label):
        self._label = label
        if label:
            self._setLabelRect()
        self._computeMargins()

    @QtCore.pyqtProperty(QtCore.Qt.Corner)
    def labelPos(self):
        return self._labelPos

    @labelPos.setter
    def labelPos(self, labelPos):
        self._labelPos = labelPos
        self._computeMargins()

    @QtCore.pyqtProperty(QtCore.Qt.Orientation)
    def orientation(self):
        return self._orientation

    @orientation.setter
    def orientation(self, orientation):
        self._orientation = orientation
        self._computeMargins()

    @QtCore.pyqtProperty(bool)
    def marginOverride(self):
        return self._marginOverride

    @marginOverride.setter
    def marginOverride(self, state):
        self._marginOverride = state
        self._computeMargins()

    @QtCore.pyqtProperty(bool)
    def sunken(self):
        return self._sunken

    @sunken.setter
    def sunken(self, state):
        self._sunken = state
        self.setPalette(self.palette())
        self.update()

    @QtCore.pyqtProperty(int)
    def padding(self):
        return self._padding

    @padding.setter
    def padding(self, padding):
        self._padding = padding
        self._computeMargins()

    @QtCore.pyqtProperty(QtGui.QColor)
    def borderColor(self):
        if self._borderColorChanged:
            return self._setBorderColor
        else:
            return self.palette().color(self.palette().Midlight)

    @borderColor.setter
    def borderColor(self, color):
        self._setBorderColor = color
        #this is a workaround that might not work around...
        self._borderColorChanged = True if color != self.palette().color(self.palette().Midlight) else False
        self.borderAnimation.setEndValue(color)
        self.setPalette(self.palette())

    @QtCore.pyqtProperty(QtGui.QColor)
    def labelColor(self):
        return self._labelColor

    @labelColor.setter
    def labelColor(self, color):
        self._labelColor = color
        self.update()

    def _setLabelRect(self):
#        self._labelRect = rect = QtCore.QRectF(0, 0, self.fontMetrics().width(self._label) + 4, self.fontMetrics().height() + 2)
        fontMetrics = self.fontMetrics()
        hMargin = fontMetrics.height() / 4
        vMargin = hMargin / 2
        if sys.platform == 'darwin':
            hMargin *= 2
        self._labelRect = rect = self.fontMetrics().boundingRect(self._label).adjusted(0, 0, hMargin, vMargin)
        rect.translate(-rect.topLeft())
        self._labelBackgroundPath = QtGui.QPainterPath()
        self._labelBackgroundPath.moveTo(2, 0)
        self._labelBackgroundPath.arcTo(0, 0, 4, 4, 90, 90)
        self._labelBackgroundPath.arcTo(0, rect.height() - 4, 4, 4, 180, 90)
        closeRect = QtCore.QRectF(rect.width() - rect.height() / 2 - 8, rect.y(), rect.height(), rect.height())
        self._labelBackgroundPath.arcTo(closeRect, 270, 90)
        closeRect.translate(rect.height(), 0)
        self._labelBackgroundPath.arcTo(closeRect, 180, -90)

    def _computeMargins(self):
        top = bottom = left = right = self._padding
        if self._label and not self._marginOverride:
            height = self.fontMetrics().height()
            if self._orientation & QtCore.Qt.Horizontal:
                if self._labelPos in (QtCore.Qt.TopLeftCorner, QtCore.Qt.TopRightCorner):
                    top += height
                else:
                    bottom += height
            else:
                if self._labelPos in (QtCore.Qt.TopLeftCorner, QtCore.Qt.BottomLeftCorner):
                    left += height
                else:
                    right += height
        self.setContentsMargins(left, top, right, bottom)
        self.update()

    _labelTransform = {
        QtCore.Qt.Horizontal: {
            QtCore.Qt.TopRightCorner: lambda qp, labelRect: (0, (qp.viewport().width(), 0), (-1, 1), (-labelRect.width(), 0)), 
            QtCore.Qt.BottomLeftCorner: lambda qp, labelRect: (0, (0, qp.viewport().height()), (1, -1), (0, -labelRect.height())), 
            QtCore.Qt.BottomRightCorner: lambda qp, labelRect: (0, (qp.viewport().width(), qp.viewport().height()), (-1, -1), (-labelRect.width(), -labelRect.height())), 
            }, 
        QtCore.Qt.Vertical: {
            QtCore.Qt.BottomLeftCorner: lambda qp, labelRect: (-90, (-qp.viewport().height(), 0), (1, 1), (0, 0)), 
            QtCore.Qt.TopLeftCorner: lambda qp, labelRect: (-90, (0, 0), (-1, 1), (-labelRect.width(), 0)), 
            QtCore.Qt.TopRightCorner: lambda qp, labelRect: (90, (0, -qp.viewport().width()), (1, 1), (0, 0)), 
            QtCore.Qt.BottomRightCorner: lambda qp, labelRect: (90, (qp.viewport().height(), -qp.viewport().width()), (-1, 1), (-labelRect.width(), 0))
            }
        }

    def _drawLabel(self, qp):
        qp.setPen(QtCore.Qt.NoPen)
        qp.setBrush(self.borderColor)
        try:
            rotation, translate, scale, textTranslate = self._labelTransform[self._orientation][self._labelPos](qp, self._labelRect)
            qp.save()
            qp.rotate(rotation)
            qp.save()
            qp.translate(*translate)
            qp.save()
            qp.scale(*scale)
            qp.drawPath(self._labelBackgroundPath)
            qp.restore()
            qp.translate(*textTranslate)
            qp.setPen(self._labelColor)
            qp.drawText(self._labelRect, QtCore.Qt.AlignHCenter|QtCore.Qt.AlignVCenter, self._label)
            qp.restore()
            qp.restore()
        except:
            qp.setPen(QtCore.Qt.NoPen)
            qp.setBrush(self.borderColor)
            qp.drawPath(self._labelBackgroundPath)
            qp.setPen(self._labelColor)
            qp.drawText(self._labelRect, QtCore.Qt.AlignHCenter|QtCore.Qt.AlignVCenter, self._label)

    def paintEvent(self, event):
        QtWidgets.QFrame.paintEvent(self, event)
        qp = QtGui.QPainter(self)
        qp.setRenderHints(qp.Antialiasing)
        self.drawFrameFunc(qp)

    def drawFrameNormal(self, qp):
        qp.translate(.5, .5)
        qp.setPen(self.borderPen)
        qp.drawRoundedRect(0, 0, self.width() - 1, self.height() - 1, 2, 2)
        qp.setPen(self.borderHighlight)
        qp.drawRoundedRect(1, 1, self.width() - 3, self.height() - 3, 2, 2)
        if self._label:
            self._drawLabel(qp)

    def drawFrameFakeGroups(self, qp):
        self.drawFrameNormal(qp)
#        if not self.layout():
#            return
        layout = self.layout()
        qp.setPen(self.framePen)
        qp.setBrush(self.frameBrush)
        for row, col, rowSpan, colSpan in self._sections:
            rect = layout.cellRect(row, col)
            if rowSpan > 1:
                rect.setBottom(layout.cellRect(row + rowSpan - 1, col + colSpan - 1).bottom())
            if colSpan > 1:
                rect.setRight(layout.cellRect(row + rowSpan - 1, col + colSpan - 1).right())
            qp.drawRoundedRect(rect, 2, 2)

    def resizeEvent(self, event):
        self._setLabelRect()
        self._computeMargins()
        QtWidgets.QFrame.resizeEvent(self, event)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    f = Frame(label='asdf')
    f.borderColor = QtGui.QColor(QtCore.Qt.blue)
    f.show()
    sys.exit(app.exec_())

