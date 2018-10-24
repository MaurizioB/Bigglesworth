import sys
from Qt import QtCore, QtGui, QtWidgets

#things that Qt.py doesn't import as we need
from PyQt4.QtCore import qCompress, qUncompress
QtCore.qCompress = qCompress
QtCore.qUncompress = qUncompress

from PyQt4.QtGui import (
    QIconEngineV2, QMatrix, 
    QStyleOptionFrameV2, QStyleOptionFrameV3, 
    QStyleOptionTabV3, QStyleOptionTabWidgetFrameV2, QStyleOptionViewItemV4)

QtGui.QIconEngineV2 = QIconEngineV2
QtGui.QMatrix = QMatrix

QtWidgets.QStyleOptionFrameV2 = QStyleOptionFrameV2
QtWidgets.QStyleOptionFrameV3 = QStyleOptionFrameV3
QtWidgets.QStyleOptionTabV3 = QStyleOptionTabV3
QtWidgets.QStyleOptionTabWidgetFrameV2 = QStyleOptionTabWidgetFrameV2
QtWidgets.QStyleOptionViewItemV4 = QStyleOptionViewItemV4

#custom virtual utilities
def colorAdjusted(color, **kwargs):
    if not kwargs:
        raise ValueError('Color arguments expected')
    newColor = QtGui.QColor(color)
    if set(('r', 'g', 'b')) & set(kwargs):
        r = kwargs.get('b', color.red())
        if isinstance(r, float):
            r *= 255
        g = kwargs.get('g', color.green())
        if isinstance(g, float):
            g *= 255
        b = kwargs.get('b', color.blue())
        if isinstance(b, float):
            b *= 255
        newColor.setRgb(r, g, b)
    elif set(('c', 'm', 'y', 'k')) & set(kwargs):
        c = kwargs.get('c', color.cyan())
        if isinstance(c, float):
            c *= 255
        m = kwargs.get('m', color.magenta())
        if isinstance(m, float):
            m *= 255
        y = kwargs.get('y', color.yellow())
        if isinstance(y, float):
            y *= 255
        k = kwargs.get('k', color.black())
        if isinstance(k, float):
            k *= 255
        newColor.setCmyk(c, m, y, k)
    a = kwargs.get('a', color.alpha())
    if isinstance(a, float):
        a *= 255
    newColor.setAlpha(a)
    return newColor

QtGui.QColor.adjusted = colorAdjusted


def topMostDumpDialog(instance):
    if instance._isDumpDialog:
        return instance
    if instance.parent() and isinstance(instance.parent(), QtWidgets.QDialog):
            return instance.parent().topMostDumpDialog()
    return instance

def topMostDialog(instance):
    if not instance.parent():
        return instance
    if isinstance(instance.parent(), QtWidgets.QDialog):
        return instance.parent().topMostDialog()
    return instance

QtWidgets.QDialog._isDumpDialog = False
QtWidgets.QDialog.topMostDumpDialog = topMostDumpDialog


if 'linux' in sys.platform:

    def addSection(self, text=''):
        action = self.addSeparator()
        action.setText(text)
        return action

    def insertSection(self, before, text=''):
        action = self.insertSeparator(before)
        action.setText(text)
        return action

else:

    #workarounds for menu separators with labels on Windows and Mac
    class MenuSection(QtWidgets.QWidgetAction):
        def __init__(self, parent, text=''):
            QtWidgets.QWidgetAction.__init__(self, parent)
            self.label = QtWidgets.QLabel(text)
            self.label.setAlignment(QtCore.Qt.AlignCenter)
            self.label.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum))
#            self.label.setMaximumHeight(self.label.frameWidth())
            self.label.setFrameStyle(QtWidgets.QFrame.StyledPanel|QtWidgets.QFrame.Sunken)
            if sys.platform == 'darwin':
                self.label.setContentsMargins(4, 2, 4, 2)
                if self.parent():
                    self.parent().aboutToShow.connect(self.setMenuFont)
            self.setDefaultWidget(self.label)
            self.setText = self.label.setText

        def setMenuFont(self):
            #menu item font sizes have to be forced to float (at least for osx 10.5)
            #also, they seem to be slightly bigger than they claim...
            menu = self.parent()
            menu.aboutToShow.disconnect(self.setMenuFont)
            for action in menu.actions():
                if not isinstance(action, QtWidgets.QWidgetAction):
                    if action.isSeparator():
                        continue
                    itemFont = action.font()
                    itemFont.setPointSizeF(itemFont.pointSizeF() + 1)
                    self.label.setFont(itemFont)
                    break

    if sys.platform == 'win32':

        def addSection(self, text=''):
            action = MenuSection(self, text)
            QtWidgets.QMenu.addAction(self, action)
            return action

        def insertSection(self, before, text=''):
            action = MenuSection(self, text)
            QtWidgets.QMenu.insertAction(self, before, action)
            return action

    else:

        class MacMenuSectionLabel(QtWidgets.QLabel):
            done = False
            def __init__(self, parentMenu, text=''):
                QtWidgets.QLabel.__init__(self, text)
                self.parentMenu = parentMenu
                self.setAlignment(QtCore.Qt.AlignCenter)

            def setText(self, text):
                QtWidgets.QLabel.setText(self, text)
                if self.done:
                    self.compute()

            def showEvent(self, event):
                if not self.done:
                    self.done = True
                    parent = self.parent()
                    layout = QtWidgets.QHBoxLayout()
                    parent.setLayout(layout)
                    layout.addWidget(self)
                    left, top, right, bottom = layout.getContentsMargins()
                    self.margins = left + right
                    layout.setContentsMargins(0, 0, 0, 0)
                    parent.setContentsMargins(0, 0, 0, 0)
#                    self.setContentsMargins(left, 0, right, 0)
                    self.setContentsMargins(0, 0, 0, 0)
                    parent.installEventFilter(self)
                    parent.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred))
                    self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred))
                    parent.setStyleSheet('''
                    MacMenuSectionLabel {{
                        border: 1px solid lightgray;
                        border-style: inset;
                        margin: 2px;
                        padding-left: {l}px;
                        padding-right: {r}px;
                    }}
                    '''.format(l=left - 1, r=right - 1))

            def compute(self):
                option = QtWidgets.QStyleOptionMenuItem()
                maxWidth = 0
                minHeight = 0
                baseSize = QtCore.QSize(0, 0)
                for action in self.parentMenu.actions():
                    if isinstance(action, QtWidgets.QWidgetAction):
                        widget = action.defaultWidget()
                        if widget != self and isinstance(widget, MacMenuSectionLabel):
                            maxWidth = max(maxWidth, widget.fontMetrics().width(widget.text()))
                        continue
                    self.parentMenu.initStyleOption(option, action)
                    #font has to be "reset" using pointsize, for unknown reasons
                    option.font.setPointSizeF(option.font.pointSizeF())
                    contents = self.parentMenu.style().sizeFromContents(QtWidgets.QStyle.CT_MenuItem, option, baseSize)
                    maxWidth = max(maxWidth, contents.width(), QtGui.QFontMetrics(option.font).width(option.text) + self.margins)
                    minHeight = min(minHeight, contents.height())

                self.setFont(option.font)
                fontMetrics = self.fontMetrics()
                minWidth = max((maxWidth + self.margins), fontMetrics.width(self.text()) + self.margins)
                self.setMinimumWidth(minWidth)
                self.parent().setMinimumWidth(minWidth)
                l, t, r, b = self.getContentsMargins()
                
                self.setContentsMargins(l, fontMetrics.descent(), r, fontMetrics.descent())
                self.parent().setMinimumHeight(minHeight)

            def eventFilter(self, source, event):
                if event.type() == QtCore.QEvent.Paint:
                    self.parentPaintEvent(event)
                    return True
                return QtWidgets.QLabel.eventFilter(self, source, event)

            def parentPaintEvent(self, event):
                self.compute()
                qp = QtGui.QPainter(self.parent())
                qp.setPen(QtCore.Qt.NoPen)
                qp.setBrush(QtGui.QColor(255, 255, 255, 245))
                qp.drawRect(self.parent().rect())


        class MacMenuBarSection(QtWidgets.QWidgetAction):
            def __init__(self, parent, text=''):
                QtWidgets.QWidgetAction.__init__(self, parent)
                self.label = MacMenuSectionLabel(parent, text)
                self.setDefaultWidget(self.label)
                self.setText = self.label.setText


        #QWidgetAction in a QMenuBar don't draw the backgrounds, this hack
        #ensures that the QMacNativeWidget (which is created as a parent of the 
        #defaultWidget) is correctly layed out and stylized.
        def addSection(self, text=''):
            parent = self.parent()
            while isinstance(parent, QtWidgets.QMenu):
                parent = parent.parent()
            if isinstance(parent, QtWidgets.QMenuBar):
                action = MacMenuBarSection(self, text)
            else:
                action = MenuSection(self, text)
            self.addAction(action)
            return action

        def insertSection(self, before, text=''):
            parent = self.parent()
            while isinstance(parent, QtWidgets.QMenu):
                parent = parent.parent()
            if isinstance(parent, QtWidgets.QMenuBar):
                action = MacMenuBarSection(self, text)
            else:
                action = MenuSection(self, text)
            self.insertAction(before, action)
            return action
    
        #workaround for QIcon.fromTheme not properly working on OSX with cx_freeze
        QtGui.QIcon._fromTheme = QtGui.QIcon.fromTheme
        sizes = (64, 32, 24, 22, 16, 8)
        iconCache = {}
        iconDir = QtCore.QDir(':/icons/{}/'.format(QtGui.QIcon.themeName()))

        @staticmethod
        def fromTheme(name, fallback=None):
            if fallback:
                icon = QtGui.QIcon._fromTheme(name, fallback)
                if not icon.isNull():
                    return icon
            icon = iconCache.get(name)
            if icon:
                return icon
            icon = QtGui.QIcon._fromTheme('')
    #            if icon.isNull():
            for size in sizes:
                path = '{s}x{s}/{n}.svg'.format(s=size, n=name)
                if iconDir.exists(path):
                    icon.addFile(iconDir.filePath(path), QtCore.QSize(size, size))
            iconCache[name] = icon
            return icon

        QtGui.QIcon.fromTheme = fromTheme


QtWidgets.QMenu.addSection = addSection
QtWidgets.QMenu.insertSection = insertSection

