from Qt import QtCore, QtGui, QtWidgets

from bigglesworth.utils import loadUi, localPath

logLevels = ['Info', 'Debug', 'Warning', 'Critical', 'Fatal']
logIcons = [QtGui.QIcon.fromTheme(i) for i in ('dialog-information', 'preferences-system', 'dialog-warning', 'dialog-error', 'application-exit')]

class TimeDelegate(QtWidgets.QStyledItemDelegate):
    relative = False
    def __init__(self, startTime):
        QtWidgets.QStyledItemDelegate.__init__(self)
        self.startTime = startTime

    def sizeHint(self, option, index):
        self.initStyleOption(option, index)
        return QtCore.QSize(option.fontMetrics.width('  00:00:00 '), option.fontMetrics.height())

    def setStartTime(self, startTime):
        self.startTime = startTime

    def setRelative(self, relative):
        self.relative = relative

    def paint(self, qp, option, index):
        self.initStyleOption(option, index)
        time = index.data(QtCore.Qt.DisplayRole)
        if self.relative:
            option.text = QtCore.QTime(0, 0, msec=time).toString('hh:mm:ss')
        else:
            option.text = self.startTime.addMSecs(time).toString('hh:mm:ss')
        QtWidgets.QApplication.style().drawControl(QtWidgets.QStyle.CE_ItemViewItem, option, qp)


class LogLevelDelegate(QtWidgets.QStyledItemDelegate):
    noIcon = QtGui.QIcon()
    def paint(self, qp, option, index):
        self.initStyleOption(option, index)
        if option.icon.isNull():
            option.text = logLevels[index.data(QtCore.Qt.DisplayRole)]
            QtWidgets.QApplication.style().drawControl(QtWidgets.QStyle.CE_ItemViewItem, option, qp)
        else:
            option.text = ''
            icon = QtGui.QIcon(option.icon)
            option.icon = self.noIcon
            QtWidgets.QApplication.style().drawControl(QtWidgets.QStyle.CE_ItemViewItem, option, qp)
#            qp.drawRect(option.rect.adjusted(2, 2, -2, -2))
            s = min(option.rect.width(), option.rect.height())
            r = QtCore.QRect(option.rect.center().x() - s * .5, option.rect.center().y() - s * .5, s, s)
            qp.drawPixmap(r, icon.pixmap(s))


class LogProxy(QtCore.QSortFilterProxyModel):
    logLevel = 0
    def filterAcceptsRow(self, row, index):
        if self.sourceModel().index(row, 1).data() < self.logLevel:
            return False
        return True


class LogWindow(QtWidgets.QDialog):
    def __init__(self, main):
        QtWidgets.QDialog.__init__(self)
        loadUi(localPath('ui/logger.ui'), self)
        self.logger = main.logger
        self.model = QtGui.QStandardItemModel()
        self.model.setHorizontalHeaderLabels(['Time', 'Type', 'Message', 'Info'])
        self.proxy = LogProxy()
        self.proxy.setSourceModel(self.model)
        self.logView.setModel(self.proxy)
        self.timeDelegate = TimeDelegate(self.logger.startTime)
        self.logView.setItemDelegateForColumn(0, self.timeDelegate)
        self.logLevelDelegate = LogLevelDelegate()
        self.logView.setItemDelegateForColumn(1, self.logLevelDelegate)

        self.relativeChk.toggled.connect(self.setRelative)
        self.reloadBtn.clicked.connect(self.loadFull)
        self.clearBtn.clicked.connect(self.clear)
        self.logView.horizontalHeader().setResizeMode(0, QtWidgets.QHeaderView.Fixed)
        self.logView.horizontalHeader().setResizeMode(1, QtWidgets.QHeaderView.Fixed)
        self.logView.horizontalHeader().setResizeMode(2, QtWidgets.QHeaderView.Interactive)
        self.logView.horizontalHeader().setResizeMode(3, QtWidgets.QHeaderView.Interactive)

        self.levelCombo.currentIndexChanged.connect(self.setFilter)

    def setFilter(self, logLevel):
        self.proxy.logLevel = logLevel
        self.proxy.invalidateFilter()

    def setRelative(self, relative):
        self.timeDelegate.setRelative(relative)
        self.logView.viewport().update()

    def show(self):
        self.logger.updated.connect(self.append)
        QtWidgets.QDialog.show(self)

    def hide(self):
        self.logger.updated.disconnect(self.append)
        QtWidgets.QDialog.hide(self)

    def appendRow(self, timestamp, logLevel, message, extMessage):
        timeItem = QtGui.QStandardItem()
        timeItem.setData(timestamp, QtCore.Qt.DisplayRole)
        logLevelItem = QtGui.QStandardItem()
        logLevelItem.setData(logLevel, QtCore.Qt.DisplayRole)
        logLevelItem.setData(logIcons[logLevel], QtCore.Qt.DecorationRole)
        logLevelItem.setData(logLevels[logLevel], QtCore.Qt.ToolTipRole)
#        logLevelItem.setData(QtCore.Qt.AlignCenter, QtCore.Qt.TextAlignmentRole)
        self.model.appendRow([timeItem, logLevelItem, QtGui.QStandardItem(message), QtGui.QStandardItem(extMessage)])

    def append(self, *data):
        self.appendRow(*data)
#        timeItem = QtGui.QStandardItem()
#        timeItem.setData(timestamp, QtCore.Qt.DisplayRole)
#        logLevelItem = QtGui.QStandardItem()
#        logLevelItem.setData(logLevel, QtCore.Qt.DisplayRole)
#        self.model.appendRow([timeItem, logLevelItem, QtGui.QStandardItem(message), QtGui.QStandardItem(extMessage)])
        self.logView.resizeRowsToContents()
        self.logView.resizeColumnsToContents()

    def clear(self):
        self.model.clear()
        self.model.setHorizontalHeaderLabels(['Time', 'Type', 'Message', 'Info'])

    def loadFull(self):
        self.clear()
        for data in self.logger.log:
            self.appendRow(*data)
        self.logView.resizeRowsToContents()
        self.logView.resizeColumnsToContents()

    def closeEvent(self, event):
        self.logger.updated.disconnect(self.append)
#        event.accept()

