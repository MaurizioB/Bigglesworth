#!/usr/bin/env python2.7

import sys, os

os.environ['QT_PREFERRED_BINDING'] = 'PyQt4'

from Qt import QtCore, QtGui, QtWidgets


class BigButton(QtWidgets.QWidget):
    clicked = QtCore.pyqtSignal()

    def __init__(self, parent=None, text='', iconName='', bgColor=QtCore.Qt.green, fgColor=QtCore.Qt.black):
        QtWidgets.QWidget.__init__(self, parent)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.text = text
        self.icon = QtGui.QIcon.fromTheme(iconName)
        self.bgColor = bgColor
        self.fgColor = fgColor
        self.pixmap = QtGui.QPixmap()

        self.setMinimumSize(88, 88)

        self.hoverAlpha = .5
        self.hoverAnimation = QtCore.QPropertyAnimation(self, b'hoverAlpha')
        self.hoverAnimation.setDuration(200)
        self.hoverAnimation.setStartValue(.5)
        self.hoverAnimation.setEndValue(1)

    @QtCore.pyqtProperty(float)
    def hoverAlpha(self):
        return self._hoverAlpha

    @hoverAlpha.setter
    def hoverAlpha(self, alpha):
        self._hoverAlpha = alpha
        self.update()

    def enterEvent(self, event):
        self.hoverAnimation.setDirection(self.hoverAnimation.Forward)
        self.hoverAnimation.start()

    def leaveEvent(self, event):
        self.hoverAnimation.setDirection(self.hoverAnimation.Backward)
        self.hoverAnimation.start()

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.clicked.emit()
        QtWidgets.QWidget.mouseReleaseEvent(self, event)

    def resizeEvent(self, event):
        height = int(self.height() * .8)
        self.borderRadius = margin = height * .2
        if not self.icon.isNull():
            iconSize = height * .45
            self.pixmap = self.icon.pixmap(iconSize)
            if self.pixmap.height() > iconSize:
                self.pixmap = self.pixmap.scaledToHeight(iconSize, QtCore.Qt.SmoothTransformation)
        else:
            iconSize = 0
            margin = height * .25

        font = QtGui.QFont(self.font())
        font.setPointSizeF(max(14, height * .15))
        self.setFont(font)

        metrics = QtGui.QFontMetrics(font)
        lines = len(self.text.splitlines())
        self.iconRect = QtCore.QRectF((self.width() - iconSize) * .5, margin, iconSize, iconSize).toRect()
#        textTop = self.iconRect.bottom() + margin * .5
        self.textRect = QtCore.QRect(0, 0, self.width(), metrics.height() * 1.1 * lines).translated(0, self.height() - margin * 3)
        if lines > 1:
            delta = - metrics.height() / lines
            self.iconRect.translate(0, delta)
            self.textRect.translate(0, delta)

    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        qp.setRenderHints(qp.Antialiasing)
        qp.translate(.5, .5)
        qp.setOpacity(self.hoverAlpha)
        qp.setPen(QtCore.Qt.NoPen)
        qp.setBrush(self.bgColor)
        qp.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), self.borderRadius, self.borderRadius)
        if not self.pixmap.isNull():
            qp.drawPixmap(self.iconRect, self.pixmap, self.pixmap.rect())
        qp.setPen(self.fgColor)
        qp.drawText(self.textRect, QtCore.Qt.AlignHCenter|QtCore.Qt.AlignBottom, self.text)


class Logo(QtWidgets.QWidget):
    def __init__(self):
        QtWidgets.QWidget.__init__(self)
        self.reference = QtGui.QPixmap(':/images/bigglesworth_textonly.svg')
        self.ratio = float(self.reference.height()) / self.reference.width()

    def resizeEvent(self, event):
        self.pixmap = self.reference.scaled(self.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        self.pixmapTop = (self.height() - self.width() * self.ratio) * .5

    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        qp.setRenderHints(qp.Antialiasing)
        qp.drawPixmap(self.pixmap.rect().translated(0, self.pixmapTop), self.pixmap, self.pixmap.rect())


class ButtonsContainer(QtWidgets.QWidget):
    def __init__(self, parent):
        QtWidgets.QWidget.__init__(self, parent)
        layout = QtWidgets.QGridLayout()
        self.setLayout(layout)

        self.logo = Logo()
        layout.addWidget(self.logo, 1, 1, 1, 3)

        self.librarianBtn = BigButton(self, 'Librarian', 'tab-duplicate', bgColor=QtGui.QColor(170, 180, 255))
        layout.addWidget(self.librarianBtn, 3, 1)
        self.editorBtn = BigButton(self, 'Editor', 'dial', bgColor=QtGui.QColor(184, 255, 131))
        layout.addWidget(self.editorBtn, 3, 3)
        self.wavetablesBtn = BigButton(self, 'Wavetables', 'wavetables', bgColor=QtGui.QColor(255, 139, 126))
        layout.addWidget(self.wavetablesBtn, 5, 1)
        self.utilsBtn = BigButton(self, 'Blofeld\nUtilities', 'circuit', bgColor=QtGui.QColor(222, 173, 255))
        layout.addWidget(self.utilsBtn, 5, 3)

        getSpacer = lambda: QtWidgets.QSpacerItem(10, 10, QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.topLeftSpacer = getSpacer()
        self.bottomRightSpacer = getSpacer()
        self.logoSpacer = getSpacer()
        self.midSpacer = getSpacer()
        layout.addItem(self.topLeftSpacer, 0, 0, 1, 1)
        layout.addItem(self.bottomRightSpacer, 6, 4, 1, 1)
        layout.addItem(self.logoSpacer, 2, 2, 1, 1)
        layout.addItem(self.midSpacer, 4, 2, 1, 1)

        self.setContentsMargins(0, 0, 0, 0)
        layout.setContentsMargins(0, 0, 0, 0)
        self.baseMargin = 10

        self.background = QtGui.QLinearGradient(.5, .2, .7, .9)
        self.background.setCoordinateMode(self.background.ObjectBoundingMode)
        self.background.setColorAt(0, QtGui.QColor(237, 239, 240))
        self.background.setColorAt(.5, QtGui.QColor(199, 215, 240, 192))
        self.background.setColorAt(1, QtGui.QColor(229, 233, 240))

    def resizeEvent(self, event):
        reference = min(self.height(), self.width())
        minSize = max(50, (reference - self.baseMargin * 3) / 2)

        margin = minSize / 10
        vSpace = max(self.baseMargin, (self.height() - minSize * 2 - margin) / 2)
        hSpace = max(self.baseMargin, (self.width() - minSize * 2 - margin) / 2)
        layout = self.layout()
        layout.setRowStretch(0, margin)
        layout.setRowStretch(1, minSize * .5)
        for r in range(5):
            if r == 2:
                layout.setRowStretch(r + 2, margin)
                layout.setColumnStretch(r, margin)
            else:
                layout.setRowStretch(r + 2, minSize if r & 1 else vSpace)
                layout.setColumnStretch(r, minSize if r & 1 else hSpace)

        self.layout().invalidate()

    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        qp.setPen(QtCore.Qt.NoPen)
        qp.setRenderHints(qp.Antialiasing)
        qp.setBrush(self.background)
        qp.translate(.5, .5)
        borderRadius = self.height() * .05
        qp.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), borderRadius, borderRadius)


class WelcomeButton(QtWidgets.QPushButton):
    pass


class Welcome(QtWidgets.QDialog):
    showLibrarian = QtCore.pyqtSignal()
    showEditor = QtCore.pyqtSignal()
    showWavetables = QtCore.pyqtSignal()
    showSettings = QtCore.pyqtSignal()
    showUtils = QtCore.pyqtSignal()

    def __init__(self, main):
        QtWidgets.QDialog.__init__(self)
        self.setWindowTitle('Bigglesworth')
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.main = main
        self.settings = QtCore.QSettings()
        layout = QtWidgets.QVBoxLayout()
        layout.setSpacing(12)
        self.setLayout(layout)
        self.buttons = ButtonsContainer(self)
        layout.addWidget(self.buttons)

        self.buttons.librarianBtn.clicked.connect(self.showLibrarian)
        self.buttons.librarianBtn.clicked.connect(self.hide)
        self.buttons.librarianBtn.customContextMenuRequested.connect(self.showButtonMenu)
        self.buttons.editorBtn.clicked.connect(self.showEditor)
        self.buttons.editorBtn.clicked.connect(self.hide)
        self.buttons.editorBtn.customContextMenuRequested.connect(self.showButtonMenu)
        self.buttons.wavetablesBtn.clicked.connect(self.showWavetables)
        self.buttons.wavetablesBtn.clicked.connect(self.hide)
        self.buttons.wavetablesBtn.customContextMenuRequested.connect(self.showButtonMenu)
        self.buttons.utilsBtn.clicked.connect(self.showUtils)

        bottom = QtWidgets.QHBoxLayout()
        layout.addLayout(bottom)
        self.showAgainCombo = QtWidgets.QComboBox()
        bottom.addWidget(self.showAgainCombo)

        self.showAgainCombo.addItem('Always show this window on startup')
        self.showAgainCombo.addItem('Always start with the Librarian')
        self.showAgainCombo.addItem('Always start with the Sound editor')
        self.showAgainCombo.addItem('Always start with the Wavetable editor')
        self.showAgainCombo.currentIndexChanged.connect(self.setDefault)

        bottom.addStretch(1)

        self.settingsBtn = WelcomeButton(QtGui.QIcon.fromTheme('settings'), 'Settings')
        bottom.addWidget(self.settingsBtn)
        self.settingsBtn.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred))
        self.settingsBtn.clicked.connect(self.showSettings)

        bottom.addStretch(2)

        self.quitBtn = WelcomeButton(QtGui.QIcon.fromTheme('window-close'), '')
        bottom.addWidget(self.quitBtn)
        self.quitBtn.setToolTip('Quit Bigglesworth :-(')
        self.quitBtn.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred))
        self.quitBtn.setFixedWidth(self.fontMetrics().height() * 2)
        self.quitBtn.clicked.connect(self.close)

        self.setStyleSheet('''
            WelcomeButton {
                border: 1px solid palette(mid);
                border-radius: 4px;
                padding-left: 4px;
                padding-right: 4px;
            }
            WelcomeButton:hover {
                border-color: palette(dark);
                border-style: outset;
            }
            WelcomeButton:pressed {
                border-style: inset;
            }
        ''')
        self.shown = False
        self.doResize = True

    def showButtonMenu(self, pos):
        pass

    def setDefault(self, index):
        self.settings.setValue('StartUpWindow', index)

    def hide(self):
        QtWidgets.QDialog.hide(self)
        self.shown = False

    def keyPressEvent(self, event):
        if event.key() != QtCore.Qt.Key_Escape:
            QtWidgets.QDialog.keyPressEvent(self, event)

    def showEvent(self, event):
        if not self.shown:
            self.shown = True
            geo = QtWidgets.QApplication.desktop().availableGeometry()
            if self.doResize:
                self.doResize = False
                reference = min(geo.width(), geo.height())
                minSize = min(1000, max(self.minimumWidth(), self.minimumHeight(), reference * .4))
                self.resize(minSize, minSize)
            self.move(geo.center().x() - self.width() / 2, geo.center().y() - self.height() / 2)

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    w = Welcome()
    w.show()
    sys.exit(app.exec_())
