from Qt import QtCore, QtGui, QtWidgets

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


class StatusBar(QtWidgets.QStatusBar):
    def __init__(self, *args, **kwargs):
        QtWidgets.QStatusBar.__init__(self, *args, **kwargs)
        self.databaseWidget = None
        self.progress = QtWidgets.QProgressBar()
        self.progress.setMaximumWidth(100)
        self.progress.setVisible(False)
        self.addPermanentWidget(self.progress)

    def setDatabase(self, database):
        self.database = database
        self.database.backupStarted.connect(self.backupStarted)
        self.database.backupStatusChanged.connect(self.backupStatusChanged)
        self.database.backupFinished.connect(self.backupFinished)
        self.database.backupError.connect(self.backupError)

    def backupStarted(self):
        self.showMessage('Backup started...', 2000)
        self.progress.setValue(0)
        self.progress.setVisible(True)
#        self.addWidget(self.progress)

    def backupStatusChanged(self, value):
        self.progress.setValue(value)

    def backupFinished(self):
        self.progress.setVisible(False)
        self.showMessage('Backup completed!', 2000)
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
        if not self.databaseWidget:
            self.databaseWidget = DatabaseWidget(self.height() - 2)
            self.addPermanentWidget(self.databaseWidget)
            self.databaseWidget.installEventFilter(self)
            self.databaseWidget.setValid(self.database.backup.success)
