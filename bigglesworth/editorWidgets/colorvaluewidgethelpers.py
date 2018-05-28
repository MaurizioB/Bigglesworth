#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division

from Qt import QtCore, __binding__
from combo import _Combo

class ValueEditor(_Combo):
    def __init__(self, parent):
        _Combo.__init__(self, parent.window())
        self.parentWidget = parent
        self.setEditable(True)
        self.setInsertPolicy(self.NoInsert)
        self.addItems(list(parent.valueList))
        self.setMinimumWidth(self._dataWidth)
        try:
            currentValue = parent.value()
            self.minimum = parent.minimum()
        except:
            currentValue = parent.value
            self.minimum = parent.minimum
        self.step = parent.step
        self.setCurrentIndex((currentValue - self.minimum) / self.step)
        self.lineEdit().returnPressed.connect(self.lookUpValue)
        self.currentIndexChanged.connect(lambda index: parent.setValue(self.minimum + index * self.step))
        self.setMouseTracking(True)
        self.window().installEventFilter(self)

    def eventFilter(self, source, event):
        if event.type() == QtCore.QEvent.MouseButtonPress and event.pos() not in self.rect():
            self.deleteLater()
            return True
        return _Combo.eventFilter(self, source, event)

    def showEvent(self, event):
        x = int(self.parentWidget.rect().center().x() - (self.width() / 2))
        y = int(self.parentWidget.rect().center().y() - (self.height() / 2))
        pos = self.parentWidget.mapTo(self.window(), QtCore.QPoint(x, y))
        if pos.x() + self.width() > self.window().width():
            pos.setX(self.window().width() - self.width())
        if pos.x() < 0:
            pos.setX(0)
        if pos.y() + self.height() > self.window().height():
            pos.setY(self.window().height() - self.height())
        if pos.y() < 0:
            pos.setY(0)
        self.move(pos)
        self.lineEdit().selectAll()

    def wheelEvent(self, event):
        #inverted implementation of wheelEvent
        shift = 10 if event.modifiers() == QtCore.Qt.ShiftModifier else 1
        if __binding__ == 'PyQt4':
            delta = event.delta()
        else:
            delta = event.pixelDelta()
            if not delta:
                delta = event.angleDelta()
                if not delta:
                    return
            if abs(delta.x()) > abs(delta.y()):
                delta = delta.x()
            else:
                delta = delta.y()
        newIndex = self.currentIndex()
        if delta > 0:
            newIndex += 1 * shift
            while not self.model().flags(self.model().index(newIndex, 0)) & QtCore.Qt.ItemIsEnabled:
                newIndex -= 1
            while newIndex < self.count() and not self.model().flags(self.model().index(newIndex, 0)) & QtCore.Qt.ItemIsEnabled:
                newIndex += 1
        else:
            newIndex -= 1 * shift
            while not self.model().flags(self.model().index(newIndex, 0)) & QtCore.Qt.ItemIsEnabled:
                newIndex += 1
            while newIndex >= 0 and not self.model().flags(self.model().index(newIndex, 0)) & QtCore.Qt.ItemIsEnabled:
                newIndex -= 1
        if 0 <= newIndex < self.count() and newIndex != self.currentIndex():
            self.setCurrentIndex(newIndex)
        event.accept()

    def focusOutEvent(self, event):
        if not self.view().isVisible():
            self.deleteLater()

    def lookUpValue(self):
        index = self.findText(self.lineEdit().text(), flags=QtCore.Qt.MatchFixedString)
        if index >= 0:
#            self.parentWidget.setCurrentIndex(index)
            self.parentWidget.setValue(self.minimum + index * self.step)
            self.deleteLater()
#        if self.lineEdit().text() in self.parentWidget.valueList:
#            self.parentWidget.setCurrentIndex(self.parentWidget.valueList.index(self.lineEdit().text()))
#            self.deleteLater()

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self.deleteLater()
        else:
            _Combo.keyPressEvent(self, event)


