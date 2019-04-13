import sys

from Qt import QtCore, QtGui, QtWidgets
QtCore.pyqtSignal = QtCore.Signal

from bigglesworth.utils import setBold
from bigglesworth.const import SingleClickActions, DoubleClickActions

class DatabaseWidget(QtWidgets.QLabel):
    def __init__(self, size):
        QtWidgets.QLabel.__init__(self)
        self.basePixmap = QtGui.QIcon.fromTheme('server-database').pixmap(size, size)
        self.warningPixmap = QtGui.QPixmap(self.basePixmap)
        half = size * .5
        #TODO: why does not work using fromTheme?
        warningSource = QtGui.QIcon(':/icons/Bigglesworth/16x16/emblem-warning').pixmap(half, half)
        qp = QtGui.QPainter(self.warningPixmap)
        qp.drawPixmap(half, half, half, half, warningSource)
        qp.end()
        self.pixmaps = self.warningPixmap, self.basePixmap
        self.setPixmap(self.basePixmap)

    def setValid(self, valid):
        self.setPixmap(self.pixmaps[valid])


class MouseActionSelector(QtWidgets.QFrame):
    actionChanged = QtCore.pyqtSignal(int)
    def __init__(self, label, shortLbl, suffix, data):
        QtWidgets.QFrame.__init__(self)
        self.setFrameShape(self.StyledPanel|self.Sunken)
        layout = QtWidgets.QHBoxLayout()
        self.setLayout(layout)
        layout.setContentsMargins(1, 1, 1, 1)
        self.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        layout.addWidget(QtWidgets.QLabel(shortLbl))
        self.suffix = suffix

        self.icon = QtWidgets.QLabel()
        layout.addWidget(self.icon)
        self.label = QtWidgets.QLabel()
        layout.addWidget(self.label)

        self.icons = []
        self.pixmaps = []
        self.labels = []
        self.toolTips = []
        self.menu = QtWidgets.QMenu()
        self.menu.setSeparatorsCollapsible(False)
        self.menu.addSection(label)
        self.menuActions = []

        fontMetrics = self.fontMetrics()
        width = 0
        height = fontMetrics.height()
        for actionId, (iconName, label, toolTip) in enumerate(data):
            icon = QtGui.QIcon.fromTheme(iconName)
            self.icons.append(icon)

            action = self.menu.addAction(icon, toolTip)
            action.setData(actionId)
            self.menuActions.append(action)

            pixmap = icon.pixmap(height)
            if pixmap.height() != height:
                pixmap = pixmap.scaledToHeight(height, QtCore.Qt.SmoothTransformation)
            self.pixmaps.append(pixmap)
            self.labels.append(label)
            width = max(width, fontMetrics.width(label))
            self.toolTips.append(toolTip)
        self.label.setFixedWidth(width)
        self.currentActionId = -1
        self.setAction(0, emit=False)

    def setAction(self, actionId, emit=True):
        if actionId >= len(self.icons):
            actionId = 0
        if actionId == self.currentActionId:
            return
        self.icon.setPixmap(self.pixmaps[actionId])
        self.label.setText(self.labels[actionId])
        self.setToolTip(self.toolTips[actionId] + ' {}'.format(self.suffix))
        self.currentActionId = actionId
        if emit:
            self.actionChanged.emit(actionId)

    def mousePressEvent(self, event):
        if event.buttons() == QtCore.Qt.LeftButton:
            self.setAction(self.currentActionId + 1)

    def contextMenuEvent(self, event):
        for actionId, action in enumerate(self.menuActions):
            setBold(action, actionId == self.currentActionId)
        res = self.menu.exec_(self.mapToGlobal(self.rect().bottomLeft()))
        if res:
            self.setAction(res.data())


class StatusBar(QtWidgets.QStatusBar):
    def __init__(self, *args, **kwargs):
        QtWidgets.QStatusBar.__init__(self, *args, **kwargs)
        self.databaseWidget = self.database = None
        self.progress = QtWidgets.QProgressBar()
        self.progress.setMaximumWidth(100)
        self.progress.setVisible(False)
        self.addPermanentWidget(self.progress)
        self.doubleClickSelector = MouseActionSelector('Double click action', 'Dbl:', 'on double click', DoubleClickActions.actionInfo)
        self.addPermanentWidget(self.doubleClickSelector)
        self.doubleActionChanged = self.doubleClickSelector.actionChanged

        self.singleClickSelector = MouseActionSelector('Single click action', 'Sgl:', 'on single click', SingleClickActions.actionInfo)
        self.addPermanentWidget(self.singleClickSelector)
        self.singleActionChanged = self.singleClickSelector.actionChanged

    def setDatabase(self, database):
        self.database = database
        self.database.backupStarted.connect(self.backupStarted)
        self.database.backupStatusChanged.connect(self.backupStatusChanged)
        self.database.backupFinished.connect(self.backupFinished)
        self.database.backupError.connect(self.backupError)

    def backupStarted(self):
        self.showMessage('Backup started...')
        self.progress.setValue(0)
        self.progress.setVisible(True)
#        self.addWidget(self.progress)

    def backupStatusChanged(self, value):
        self.progress.setValue(value)

    def backupFinished(self):
        self.progress.setVisible(False)
        self.showMessage('Backup completed!', 8000)
        if self.databaseWidget:
            self.databaseWidget.setValid(self.database.backup.success)

    def backupError(self, error):
        self.progress.setVisible(False)
        self.showMessage('Backup error!', 1000000)
        if self.databaseWidget:
            self.databaseWidget.setValid(self.database.backup.success)

    def eventFilter(self, source, event):
        if event.type() == QtCore.QEvent.ToolTip and source == self.databaseWidget:
            self.databaseWidget.setToolTip(self.database.getStatusText())
        return QtWidgets.QLabel.eventFilter(self, source, event)

    def resizeEvent(self, event):
        if not self.databaseWidget and self.database:
            self.databaseWidget = DatabaseWidget(self.height() - 2)
            self.addPermanentWidget(self.databaseWidget)
            self.databaseWidget.installEventFilter(self)
            self.databaseWidget.setValid(self.database.backup.success)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    w = QtWidgets.QMainWindow()
    w.setStatusBar(StatusBar(w))
    w.show()
    sys.exit(app.exec_())
