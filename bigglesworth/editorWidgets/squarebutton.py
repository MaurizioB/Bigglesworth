#!/usr/bin/env python3

from Qt import QtCore, QtWidgets, QtGui
from metawidget import BaseWidget, _getCssQColorStr, _getCssQFontStr, makeQtProperty, makeQtChildProperty

class _Button(QtWidgets.QPushButton):
    switchToggled = QtCore.pyqtSignal(bool)
    _minWidth = _minHeight = 8
    _minimumSizeHint = QtCore.QSize(_minWidth, _minHeight)
    _baseSizeHint = QtCore.QSize(40, 40)

    def __init__(self, parent=None):
        QtWidgets.QPushButton.__init__(self, parent)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred))
        self.setAttribute(QtCore.Qt.WA_LayoutUsesWidgetRect, True)
        self.setMinimumSize(self._minimumSizeHint)
        self.setMaximumSize(QtCore.QSize(80, 80))
        self.sizeHint = lambda: self._baseSizeHint
        self.minimumSizeHint = lambda: self._minimumSizeHint
        self.clicked.connect(self.switch)

    def mousePressEvent(self, event):
        if self.parent()._popup:
            if event.button() == QtCore.Qt.LeftButton:
                self.parent().popupTimer.start()
            elif event.button() == QtCore.Qt.RightButton:
                self.parent().showPopup()
                return
        QtWidgets.QPushButton.mousePressEvent(self, event)

    def mouseMoveEvent(self, event):
        if self.parent()._popup:
            pre = self.isDown()
            QtWidgets.QPushButton.mouseMoveEvent(self, event)
            post = self.isDown()
            if pre != post:
                if post:
                    self.parent().popupTimer.start()
                else:
                    self.parent().popupTimer.stop()
        else:
            QtWidgets.QPushButton.mouseMoveEvent(self, event)

    def mouseReleaseEvent(self, event):
        if self.parent()._popup and self.parent().popupTimer.isActive():
            self.parent().popupTimer.stop()
        QtWidgets.QPushButton.mouseReleaseEvent(self, event)

    def switch(self):
        if self.parent().switchable:
            self.parent().switched = not self.parent()._switched
#    def mouseReleaseEvent(self, event):
#        QtWidgets.QPushButton.mouseReleaseEvent(self, event)
#        if event.pos() in self.rect() and self.parent().switchable:
#            self.parent().switched = not self.parent()._switched

    def setPalette(self, palette):
        self._setColors(palette)

    def _setColors(self, palette=None):
        if palette is None:
            palette = self.parent().palette()
        state = palette.Active if self.parent()._switchable and self.parent()._switched else palette.Inactive
        if self.parent()._inverted:
            state = palette.Inactive if state == palette.Active else palette.Active
        backgroundBase = palette.color(state, palette.Button)
        backgroundNormal = backgroundBase.darker(180)
        backgroundNormalLight = backgroundBase
        backgroundPressed = backgroundBase.darker(110)
        backgroundPressedLight = backgroundBase.lighter(125)

#        backgroundDisabled = backgroundBase.darker(200)
        backgroundDisabledLight = backgroundBase.darker(140)
        backgroundDisabledPressed = backgroundBase.darker(160)
#                border-top: 1px solid {light};
#                border-right: 1px solid {dark};
#                border-bottom: 1px solid {dark};
#                border-left: 1px solid {light};
#                border-radius: 2px;
#                border-top: 1px solid {dark};
#                border-right: 1px solid {light};
#                border-bottom: 1px solid {light};
#                border-left: 1px solid {dark};
#                border-radius: 2px;
        self.setStyleSheet('''
            QPushButton {{
                color: palette(button-text);
                padding: 1px;
                background: qradialgradient(cx:0.4, cy:0.4, radius: 1, fx:0.5, fy:0.5, 
                    stop:0 {backgroundNormalLight},
                    stop:1 {backgroundNormal});
                border-style: outset;
                border-radius: 2px;
                border-width: 1px;
                border-color: {backgroundNormal};
            }}
            QPushButton:pressed {{
                background: qradialgradient(cx:0.4, cy:0.4, radius: 1, fx:0.5, fy:0.5, 
                    stop:0 {backgroundPressedLight},
                    stop:1 {backgroundPressed});
                border-style: inset;
            }}
            QPushButton:disabled {{
                background: qradialgradient(cx:0.4, cy:0.4, radius: 1, fx:0.5, fy:0.5, 
                    stop:0 {backgroundDisabledLight},
                    stop:1 {backgroundDisabledPressed});
                    border-color: {dark};
            }}
            '''.format(
#                light=_getCssQColorStr(backgroundBase.lighter(150)), 
                dark=_getCssQColorStr(backgroundBase.darker()), 
                backgroundNormal=_getCssQColorStr(backgroundNormal), 
                backgroundNormalLight=_getCssQColorStr(backgroundNormalLight), 
                backgroundPressed=_getCssQColorStr(backgroundPressed), 
                backgroundPressedLight=_getCssQColorStr(backgroundPressedLight), 
                backgroundDisabledLight=_getCssQColorStr(backgroundDisabledLight), 
                backgroundDisabledPressed=_getCssQColorStr(backgroundDisabledPressed), 
#                font=_getCssQFontStr(self.font()), 
                )
            )

    defaultPaintEvent = lambda *args: QtWidgets.QPushButton.paintEvent(*args)

    def popupPaintEvent(self, event):
        option = QtWidgets.QStyleOptionButton()
        self.initStyleOption(option)
        qp = QtWidgets.QStylePainter(self)
        option.features |= option.HasMenu
        qp.drawControl(QtWidgets.QStyle.CE_PushButton, option)


class SquareButton(BaseWidget):
    switchableChanged = QtCore.pyqtSignal(bool)
    switchToggled = QtCore.pyqtSignal(bool)
    clicked = QtCore.pyqtSignal()

    def __init__(self, parent=None, label='', switchable=False, switched=False, labelPos=QtCore.Qt.BottomEdge):
        BaseWidget.__init__(self, parent, label, labelPos)
#        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred))
        self._switchable = switchable
        self._switched = switched
        self._inverted = False
        self.button = _Button(self)
        self.button.clicked.connect(self.clicked)
        self.setWidget(self.button)
#        self.setFont(QtGui.QFont('Droid Sans', 9, QtGui.QFont.Bold))
        self._paletteChanged(self.palette())
        self._fullMode = False
        self._pressing = False
        self._menu = None
        self._popup = False
        self._hidePopupArrow = False
        self.popupTimer = QtCore.QTimer()
        self.popupTimer.setInterval(250)
        self.popupTimer.setSingleShot(True)
        self.popupTimer.timeout.connect(self.showPopup)
#        self.mousePressEvent = self.button.mousePressEvent

    switchable = makeQtProperty(bool, '_switchable', actions=(lambda self: self.button._setColors(self.palette()), ), signal='switchableChanged')
    switched = makeQtProperty(bool, '_switched', actions=(lambda self: self.button._setColors(self.palette()), ), signal='switchToggled')
    inverted = makeQtProperty(bool, '_inverted', actions=(lambda self: self.button._setColors(self.palette()), ))

    def setMenu(self, menu=None):
        self._menu = menu
        if menu and not self._hidePopupArrow:
            self.button.paintEvent = self.button.popupPaintEvent
        else:
            self.button.paintEvent = self.button.defaultPaintEvent

    def showPopup(self):
        if self._menu:
            self._menu.exec_(self.mapToGlobal(self.rect().bottomLeft()))
            self.button.setDown(False)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton and self._fullMode and self._label and event.pos() in self._labelWidget.geometry():
            self._pressing = True
            self.button.setDown(True)
            if self._popup:
                self.popupTimer.start()
            elif self._menu:
                self.showPopup()

    def contextMenuEvent(self, event):
        if self._popup:
            self.showPopup()

    def mouseMoveEvent(self, event):
        if self._fullMode and self._label and self._pressing:
            if event.pos() in self._labelWidget.geometry()|self.button.geometry():
                if not self.button.isDown():
                    self.button.setDown(True)
                    self.popupTimer.start()
            elif self.button.isDown():
                self.popupTimer.stop()
                self.button.setDown(False)

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton and self._fullMode and self._label:
            if event.pos() in self._labelWidget.geometry()|self.button.geometry():
                if self._switchable:
                    self.switched = not self._switched
                else:
                    self.clicked.emit()
            self.button.setDown(False)
            self._pressing = False
            self.popupTimer.stop()

    @QtCore.pyqtProperty(bool)
    def fullMode(self):
        return self._fullMode

    @fullMode.setter
    def fullMode(self, mode):
        self._fullMode = mode

    @QtCore.pyqtProperty(str)
    def insideText(self):
        return self.button.text()

    @insideText.setter
    def insideText(self, text):
        self.button.setText(text)

    @QtCore.pyqtSlot(bool)
    def setSwitchable(self, switchable):
        self.switchable = switchable

    @QtCore.pyqtSlot(bool)
    def setSwitched(self, switched):
        self.switched = switched

    @QtCore.pyqtProperty(bool)
    def popup(self):
        return self._popup

    @popup.setter
    def popup(self, mode):
        self._popup = mode

    @QtCore.pyqtProperty(QtGui.QIcon)
    def icon(self):
        return self.button.icon()

    @icon.setter
    def icon(self, icon):
        self.button.setIcon(icon)

    @QtCore.pyqtProperty(QtCore.QSize)
    def iconSize(self):
        return self.button.iconSize()

    @iconSize.setter
    def iconSize(self, iconSize):
        self.button.setIconSize(iconSize)

    @QtCore.pyqtProperty(bool)
    def hidePopupArrow(self):
        return self._hidePopupArrow

    @hidePopupArrow.setter
    def hidePopupArrow(self, hide):
        self._hidePopupArrow = hide
        if self._menu:
            if not hide:
                self.button.paintEvent = self.button.popupPaintEvent
            else:
                self.button.paintEvent = self.button.defaultPaintEvent


def switched(state):
    print(state)

if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)
    widget = SquareButton(label='Button test')
    palette = widget.palette()
    widget.switchable = True
    palette.setColor(palette.Active, palette.Button, QtGui.QColor('green'))
    widget.setPalette(palette)
    widget.show()
    widget.switchToggled.connect(switched)
    sys.exit(app.exec_())
