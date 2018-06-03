from Qt import QtCore, QtGui, QtWidgets

#used for sidebar:
#DisplayRole = EditRole = displayed name
#DecorationRole = icon
#ToolTipRole = full path
#UrlRole = QtCore.Qt.UserRole + 1 #33
#EnabledRole = QtCore.Qt.UserRole + 2 #34
#Computer url path is "file:"

class BaseFileDialog(QtWidgets.QFileDialog):
    Computer, Desktop, Documents, Music, Home, Data, Program = 1, 2, 4, 8, 16, 32, 64
    _locations = {
        Desktop: QtGui.QDesktopServices.DesktopLocation, 
        Documents: QtGui.QDesktopServices.DocumentsLocation, 
        Music: QtGui.QDesktopServices.MusicLocation, 
        Home: QtGui.QDesktopServices.HomeLocation, 
        Data: QtGui.QDesktopServices.DataLocation, 
        }
    for k, v in _locations.items():
        _locations[k] = QtCore.QUrl.fromLocalFile(QtGui.QDesktopServices.storageLocation(v))
    _locations[Computer] = QtCore.QUrl('file://')
    _locations[Program] = QtCore.QUrl.fromLocalFile(QtCore.QDir.currentPath())

    _icons = {
        Computer: QtGui.QIcon.fromTheme('computer'), 
        Desktop: QtGui.QIcon.fromTheme('user-desktop'), 
        Documents: QtGui.QIcon.fromTheme('folder-documents'), 
        Music: QtGui.QIcon.fromTheme('folder-music'), 
        Home: QtGui.QIcon.fromTheme('user-home'), 
        }

    def __init__(self, parent=None, acceptMode=QtWidgets.QFileDialog.AcceptOpen):
        QtWidgets.QFileDialog.__init__(self, parent)
        self.defaultSuffixCheckBox = None
        self.canOverwrite = True
        self.directoryEntered.connect(self.dirCheck)
        self.systemUrls = self.Computer|self.Documents
        self.customUrls = []
        self.setAcceptMode(acceptMode)
        self.setOption(self.DontUseNativeDialog)
        self.setNameFilters(['SQLite database (*.sqlite)', 'All files (*)'])
        self.buttonBox = self.okBtn = self.cancelBtn = self.lineEdit = \
            self.splitter = self.splitterState = self.sidebar = self.lookInCombo = None
        for child in self.children():
#            print(child)
            if isinstance(child, QtWidgets.QDialogButtonBox):
                self.buttonBox = child
                for btn in self.buttonBox.buttons():
                    if self.buttonBox.buttonRole(btn) == self.buttonBox.AcceptRole:
                        self.okBtn = btn
                    else:
                        self.cancelBtn = btn
            elif isinstance(child, QtWidgets.QLineEdit):
                self.lineEdit = child
            elif isinstance(child, QtWidgets.QSplitter):
                self.splitter = child
                for listView in child.children():
                    if isinstance(listView, QtWidgets.QListView):
                        self.sidebar = listView
                        #the sidebar restores its icons whenever the file system changes
                        #but we are smarter ;-)
                        listView.model().dataChanged.connect(self.restoreSidebar)
                        break
            elif isinstance(child, QtWidgets.QComboBox) and child.objectName() == 'lookInCombo':
                self.lookInCombo = child
                child.currentIndexChanged['QString'].connect(self.dirCheck)
        self.setSidebarUrls()

    def setDefaultSuffix(self, suffix=''):
        QtWidgets.QFileDialog.setDefaultSuffix(self, suffix)
        if suffix:
            if not self.defaultSuffixCheckBox:
                self.defaultSuffixCheckBox = QtWidgets.QCheckBox('Automatically select filename e&xtension (.{})'.format(suffix))
                self.defaultSuffixCheckBox.setChecked(True)
                self.layout().addWidget(self.defaultSuffixCheckBox, self.layout().rowCount(), 0, 1, self.layout().columnCount())
                self.defaultSuffixCheckBox.toggled.connect(lambda state: QtWidgets.QFileDialog.setDefaultSuffix(self, suffix if state else ''))
            else:
                self.defaultSuffixCheckBox.setText('Automatically select filename e&xtension (.{})'.format(suffix))
                self.defaultSuffixCheckBox.blockSignals(True)
                self.defaultSuffixCheckBox.setChecked(True)
                self.defaultSuffixCheckBox.blockSignals(False)
            self.defaultSuffixCheckBox.show()
        elif self.defaultSuffixCheckBox:
            self.defaultSuffixCheckBox.hide()


    def setSidebarUrls(self, paths=None):
        urls = []
        icons = {}
        index = 0
        self.customUrls = paths if paths else []
        for l in sorted(self._locations):
            if l & self.systemUrls:
                urls.append(self._locations[l])
                if l == self.Program:
                    windowIcon = QtWidgets.QApplication.windowIcon()
                    if not windowIcon.isNull:
                        icons[index] = windowIcon
                elif l in self._icons:
                    icons[index] = self._icons[l]
                index += 1
        if paths:
            index = len(urls)
            for path in paths:
                if isinstance(path, (tuple, list)):
                    path, icon = path
                    icons[index] = icon
                urls.append(QtCore.QUrl.fromLocalFile(path))
                index += 1
        self.sidebar.model().blockSignals(True)
        QtWidgets.QFileDialog.setSidebarUrls(self, urls)
        #Ensure that the icons are set before changing them
        QtWidgets.QApplication.processEvents()
        if icons:
            for index, icon in icons.items():
                self.sidebar.model().item(index, 0).setData(icon, QtCore.Qt.DecorationRole)
        self.sidebar.model().blockSignals(False)
        self.sidebar.viewport().update()
        if not self.sidebarUrls():
            self.splitterState = self.splitter.saveState()
            self.splitter.setSizes([0, self.splitter.width()])
        else:
            if self.splitterState:
                self.splitter.restoreState(self.splitterState)
            else:
                self.splitter.setSizes([self.sidebar.sizeHint().width() * 1.2, self.sidebar.sizeHint().width() * 5])

    def setOverwrite(self, can):
        self.canOverwrite = can

    def restoreSidebar(self):
        self.setSidebarUrls(self.customUrls)

    def setSystemUrls(self, flags=0):
        self.systemUrls = flags
        self.setSidebarUrls(self.customUrls)

    def dirCheck(self, dirPath):
        if self.acceptMode() == self.AcceptSave:
            if not dirPath:
                dirPath = self.directory().absolutePath()
            info = QtCore.QFileInfo(dirPath)
            self.okBtn.setEnabled(info.isWritable())

    def accept(self):
        path = self.selectedFiles()[0]
        info = QtCore.QFileInfo(path)
        if info.isFile():
            if info.isWritable():
                if self.canOverwrite and self.confirm(path):
                    QtWidgets.QFileDialog.accept(self)
                else:
                    self.errorMessage(path)
            else:
                QtWidgets.QMessageBox.warning(self, 'Read-only file', 
                    '"{}" is read only and cannot be written onto.'.format(info.fileName()), 
                    QtWidgets.QMessageBox.Ok)
        elif info.isDir():
            if info.isWritable():
                QtWidgets.QFileDialog.accept(self)
        elif self.confirm(path):
            QtWidgets.QFileDialog.accept(self)

    def errorMessage(self, path):
        return

    def confirm(self, path):
        return True

    def exec_(self):
        if QtWidgets.QFileDialog.exec_(self):
            return self.selectedFiles()[0]
        return 0


