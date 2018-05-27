from Qt import QtCore, QtGui, QtWidgets

class DatabaseWidget(QtWidgets.QLabel):
    def __init__(self, size):
        QtWidgets.QLabel.__init__(self)
        self.setPixmap(QtGui.QIcon.fromTheme('server-database').pixmap(size, size))

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

    def eventFilter(self, source, event):
        if event.type() == QtCore.QEvent.ToolTip and source == self.databaseWidget:
            self.databaseWidget.setToolTip(self.database.getStatusText())
        return QtWidgets.QLabel.eventFilter(self, source, event)

    def resizeEvent(self, event):
        if not self.databaseWidget:
            self.databaseWidget = DatabaseWidget(self.height() - 2)
            self.addPermanentWidget(self.databaseWidget)
            self.databaseWidget.installEventFilter(self)
