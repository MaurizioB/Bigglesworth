#!/usr/bin/env python

import sys

from Qt import QtCore, QtWidgets, __binding__
#from metawidget import BaseWidget, _getCssQColorStr, _getCssQFontStr


if __binding__ == 'PyQt4':
    QtCore.Qt.TopEdge = QtCore.Qt.TopDockWidgetArea
    QtCore.Qt.LeftEdge = QtCore.Qt.LeftDockWidgetArea
    QtCore.Qt.RightEdge = QtCore.Qt.RightDockWidgetArea
    QtCore.Qt.BottomEdge = QtCore.Qt.BottomDockWidgetArea
    QtCore.Qt.Edge = QtCore.Qt.DockWidgetArea
else:
    from PyQt5.QtCore import Q_FLAGS
    QtCore.Q_FLAGS = Q_FLAGS


class StackedWidget(QtWidgets.QWidget):
    shown = False
    def __init__(self, *args, **kwargs):
        QtWidgets.QWidget.__init__(self, *args, **kwargs)
        layout = QtWidgets.QStackedLayout()
#        self.setCurrentIndex = layout.setCurrentIndex
#        self.insertWidget = layout.insertWidget
        self.widget = layout.widget
        self.remove = lambda index: layout.takeAt(index)
        self.setLayout(layout)
        if sys.platform != 'darwin':
            self._fadeEffect = True
            layout.setStackingMode(layout.StackAll)
        else:
            self._fadeEffect = False
            layout.setStackingMode(layout.StackOne)
        self._animationDuration = 200
        self.animations = {}
#        self.shown = False
        self._storedCurrentIndex = -1

    def showEvent(self, event):
        if not self.shown:
            self.shown = True
            if self._storedCurrentIndex >= 0:
                self.setCurrentIndex(self._storedCurrentIndex, False)

    def childEvent(self, event):
        #uic has problems with non boxed layouts in custom widgets, which results in child reparented and
        #not added to the actual layout.
        #see http://blog.wysota.eu.org/index.php/2007/05/07/uic-problems-with-custom-container-widgets/
        if not self.shown and event.type() == 70 and event.child().isWidgetType():
            self.addWidget(event.child())
#            print(self.layout().count())
#        print('added', event.type(), event.child(), event.child().objectName(), self.layout().count())

    @QtCore.pyqtProperty(bool)
    def fadeEffect(self):
        return self._fadeEffect

    @fadeEffect.setter
    def fadeEffect(self, fadeEffect):
        if sys.platform == 'darwin' or fadeEffect == self._fadeEffect:
            return
        self._fadeEffect = fadeEffect
        layout = self.layout()
        layout.setStackingMode(fadeEffect)
        self.animations.clear()
        if fadeEffect:
            for idx in range(layout.count()):
                widget = layout.widget(idx)
                self.animations[widget] = self.createAnimation(widget)
                if idx == layout.currentIndex():
                    widget.show()
                    widget.raise_()
                    widget.graphicsEffect().setOpacity(1)
                    continue
                widget.lower()
                widget.hide()

    @QtCore.pyqtSlot(bool)
    def setFadeEffect(self, fadeEffect):
        self.fadeEffect = fadeEffect

    @QtCore.pyqtProperty(int)
    def animationDuration(self):
        return self._animationDuration

    @animationDuration.setter
    def animationDuration(self, duration):
        self._animationDuration = duration
        for animation in self.animations.values():
            animation.setDuration(duration)

    @QtCore.pyqtProperty(int)
    def count(self):
        return self.layout().count()

    @QtCore.pyqtProperty(str, stored=False)
    def currentPageName(self):
        try:
            return self.currentWidget().objectName()
        except:
            return ''

    @currentPageName.setter
    def currentPageName(self, name):
        try:
            self.currentWidget().setObjectName(name)
        except:
            pass

    @QtCore.pyqtProperty(int)
    def currentIndex(self):
        return self.layout().currentIndex()

    @currentIndex.setter
    def currentIndex(self, index):
        self.setCurrentIndex(index)

    @QtCore.pyqtSlot(QtWidgets.QWidget)
    def currentWidget(self):
        return self.layout().currentWidget()

    @QtCore.pyqtSlot(QtWidgets.QWidget)
    def setCurrentWidget(self, widget):
        for index in range(self.layout().count()):
            if self.widget(index) == widget:
                return self.setCurrentIndex(index)

    @QtCore.pyqtSlot(QtWidgets.QWidget)
    def addWidget(self, widget):
        index = self.layout().addWidget(widget)
        if self._fadeEffect:
            animation = self.createAnimation(widget)
            self.animations[widget] = animation
            if index == self.currentIndex:
                widget.graphicsEffect().setOpacity(1)
            else:
                widget.hide()

    @QtCore.pyqtSlot(int, QtWidgets.QWidget)
    def insertWidget(self, index, widget):
        index = self.layout().insertWidget(index, widget)
        if self._fadeEffect:
            animation = self.createAnimation(widget)
            self.animations[widget] = animation
            if index == self.currentIndex:
                widget.graphicsEffect().setOpacity(1)
            else:
                widget.hide()

    @QtCore.pyqtSlot(int)
    def setCurrentIndex(self, newIndex, fade=True):
        if newIndex == self.currentIndex:
            return
        if not self.shown:
            self._storedCurrentIndex = newIndex
            return
        oldIndex = self.currentIndex
        self.layout().setCurrentIndex(newIndex)
        newWidget = self.widget(newIndex)
        if self._fadeEffect:
            newWidget.show()
            if fade:
                oldAni = self.animations[self.widget(oldIndex)]
                newAni = self.animations[newWidget]
                oldAni.setDirection(oldAni.Backward)
                oldAni.start()
                newAni.setDirection(newAni.Forward)
                newAni.start()
            else:
                newWidget.graphicsEffect().setOpacity(1)
                self.widget(oldIndex).hide()
        else:
            try:
                newWidget.graphicsEffect().setOpacity(1)
            except:
                pass

    @QtCore.pyqtProperty(int)
    def leftMargin(self):
        return self.getContentsMargins()[0]

    @leftMargin.setter
    def leftMargin(self, left):
        self.setContentsMargins(left, *self.getContentsMargins()[1:])

    @QtCore.pyqtProperty(int)
    def topMargin(self):
        return self.getContentsMargins()[1]

    @topMargin.setter
    def topMargin(self, top):
        left, _, right, bottom = self.getContentsMargins()
        self.setContentsMargins(left, top, right, bottom)

    @QtCore.pyqtProperty(int)
    def rightMargin(self):
        return self.getContentsMargins()[2]

    @rightMargin.setter
    def rightMargin(self, right):
        left, top, _, bottom = self.getContentsMargins()
        self.setContentsMargins(left, top, right, bottom)

    @QtCore.pyqtProperty(int)
    def bottomMargin(self):
        return self.getContentsMargins()[3]

    @bottomMargin.setter
    def bottomMargin(self, bottom):
        left, top, right, _ = self.getContentsMargins()
        self.setContentsMargins(left, top, right, bottom)

    def createAnimation(self, widget):
        def end(widget):
            if animation.direction() == animation.Backward:
                widget.hide()
        effect = QtWidgets.QGraphicsOpacityEffect()
        effect.setOpacity(0)
        widget.setGraphicsEffect(effect)
        animation = QtCore.QPropertyAnimation(effect, 'opacity')
        animation.finished.connect(lambda widget=widget: end(widget))
        animation.setStartValue(0)
        animation.setEndValue(1)
        animation.setDuration(self._animationDuration)
        return animation


