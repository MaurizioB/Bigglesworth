#!/usr/bin/env python2.7
# *-* encoding: utf-8 *-*

from Qt import QtCore, QtGui, QtWidgets, QtSql

from bigglesworth.const import factoryPresetsNamesDict
from bigglesworth.utils import loadUi, setBold
#from bigglesworth.library import LibraryModel
from bigglesworth.widgets import LibraryWidget, CollectionWidget
from bigglesworth.dialogs import NewCollectionDialog, ManageCollectionsDialog, TagsDialog, AboutDialog

class MainWindow(QtWidgets.QMainWindow):
    closed = QtCore.pyqtSignal()
    soundEditRequested = QtCore.pyqtSignal(str, str)
    #blofeld index/buffer, collection, index, multi
    dumpFromRequested = QtCore.pyqtSignal(object, object, int, bool)
    #uid, blofeld index/buffer, multi
    dumpToRequested = QtCore.pyqtSignal(object, object, bool)

    def __init__(self, parent):
        QtWidgets.QMainWindow.__init__(self)
        loadUi('ui/mainwindow.ui', self)
        self.main = parent
        self.database = parent.database
        self.referenceModel = QtSql.QSqlTableModel()
        self.statusbar.setDatabase(parent.database)

        self.leftTabWidget.setSiblings(self.leftTabBar, self.rightTabWidget)
        self.rightTabWidget.setSiblings(self.rightTabBar, self.leftTabWidget)
        self.leftTabBar.hide()
        self.leftTabWidget.minimize.connect(lambda: self.setLeftVisible(False))
        self.leftTabBar.maximize.connect(lambda tab: self.setLeftVisible(True, tab))
        self.rightTabBar.hide()
        self.rightTabWidget.minimize.connect(lambda: self.setRightVisible(False))
        self.rightTabBar.maximize.connect(lambda tab: self.setRightVisible(True, tab))

        #TODO: load previous session (check if collection exists!)
        sessionMode = self.main.settings.value('startupSessionMode', 2, int)
        if sessionMode >= 2:
            left = self.main.settings.value('sessionLayoutLeft', ['Blofeld'], 'QStringList')
            right = self.main.settings.value('sessionLayoutRight', [None], 'QStringList')
            if not all((left, right)):
                if None not in left and None not in right:
                    if not left:
                        left = [None]
                    else:
                        right = [None]
                elif 'Blofeld' not in left and 'Blofeld' not in right:
                    if not left:
                        left = ['Blofeld']
                    else:
                        right = ['Blofeld']
                else:
                    left = ['Blofeld']
                    right = [None]
        elif sessionMode:
            left = [None]
            right = ['Blofeld']
        else:
            left = ['Blofeld']
            right = [None]

        for tab, collections in (self.leftTabWidget, left), (self.rightTabWidget, right):
            for collection in collections:
                self.openCollection(collection, tab)

#        if self.leftTabWidget.count() < 1:
#            collectionWidget = CollectionWidget(self, 'Blofeld')
#            self.leftTabWidget.addTab(collectionWidget, 'Blofeld')
#        if self.rightTabWidget.count() < 1:
#            libraryWidget = LibraryWidget(self)
#            self.rightTabWidget.addTab(libraryWidget, 'Main library')

        self.splitter.moved.connect(self.checkSplitter)

        self.leftTabWidget.openCollection.connect(self.openCollection)
        self.leftTabWidget.newCollection.connect(self.newCollection)
        self.leftTabWidget.manageCollections.connect(self.manageCollections)
        self.leftTabWidget.tabCloseRequested.connect(self.closeCollection)
        self.leftTabWidget.tabMoveRequested.connect(self.moveCollection)
        self.rightTabWidget.openCollection.connect(self.openCollection)
        self.rightTabWidget.newCollection.connect(self.newCollection)
        self.rightTabWidget.newCollection.connect(self.manageCollections)
        self.rightTabWidget.tabCloseRequested.connect(self.closeCollection)
        self.rightTabWidget.tabMoveRequested.connect(self.moveCollection)

        self.editTagsAction.triggered.connect(self.editTags)
        self.manageCollectionsAction.triggered.connect(self.manageCollections)
        self.createCollectionAction.triggered.connect(self.newCollection)
        self.libraryMenu.aboutToShow.connect(self.createOpenCollectionActions)
#        self.openCollectionAction.triggered.connect(self.openCollection)

        self.aboutAction.triggered.connect(AboutDialog(self).exec_)
        self.aboutQtAction.triggered.connect(lambda: QtWidgets.QMessageBox.aboutQt(self, 'About Qt...'))

    def createOpenCollectionActions(self):
        self.openCollectionMenu.clear()
        self.referenceModel.setTable('reference')
#        self.referenceModel.refresh()
        current = [self.leftTabWidget.tabText(t).lower() for t in range(self.leftTabWidget.count())] + \
            [self.rightTabWidget.tabText(t).lower() for t in range(self.rightTabWidget.count())]
        self.openCollectionMenu.setSeparatorsCollapsible(False)
        sep = self.openCollectionMenu.addSeparator()
        sep.setText('Custom collections')
        for c in range(5, self.referenceModel.columnCount()):
            collection = self.referenceModel.headerData(c, QtCore.Qt.Horizontal)
            if collection.lower() in current:
                continue
            action = self.openCollectionMenu.addAction(collection)
            action.triggered.connect(lambda state, collection=collection: self.openCollection(collection, self.leftTabWidget))
            if collection == 'Blofeld':
                setBold(action)
                action.setIcon(QtGui.QIcon.fromTheme('go-home'))
        if len(self.openCollectionMenu.actions()) <= 1:
            sep.setVisible(False)
        sep = self.openCollectionMenu.addSeparator()
        sep.setText('Factory presets')
        for c in range(2, 5):
            collection = self.referenceModel.headerData(c, QtCore.Qt.Horizontal)
            if collection.lower() in current:
                continue
            action = self.openCollectionMenu.addAction(factoryPresetsNamesDict[collection])
            action.triggered.connect(lambda state, collection=collection: self.openCollection.emit(collection))
        if len(self.openCollectionMenu.actions()) <= 1:
            sep.setVisible(False)
        if not 'main library' in current:
            self.openCollectionMenu.addSeparator()
            action = self.openCollectionMenu.addAction(QtGui.QIcon.fromTheme('go-home'), 'Main library')
            action.triggered.connect(lambda: self.openCollection.emit(''))

    def editTags(self):
        tagsView = TagsDialog(self)
        if tagsView.exec_():
            for tabwidget in self.leftTabWidget, self.rightTabWidget:
                for tab in range(tabwidget.count()):
                    tabwidget.widget(tab).filterTagsEdit.setTags([])
        for collection in self.database.collections.values():
            collection.updated.emit()

    def openCollection(self, collection='', dest=None):
        if collection:
            name = factoryPresetsNamesDict.get(collection, collection)
            colWidget = CollectionWidget(self, collection)
        else:
            name = 'Main library'
            colWidget = LibraryWidget(self)
        if dest is None:
            dest = self.sender()
        colWidget.dumpFromRequested.connect(self.dumpFromRequested)
        colWidget.dumpToRequested.connect(self.dumpToRequested)
        index = dest.addTab(colWidget, name)
        dest.setCurrentIndex(index)

    def newCollection(self, clone=''):
        if isinstance(self.sender(), QtWidgets.QTabWidget):
            dest = self.sender()
        else:
            dest = self.leftTabWidget
        dialog = NewCollectionDialog(self)
        collection = dialog.exec_(clone)
        if not collection:
            return
        if dialog.cloneChk.isChecked():
            res = self.database.createCollection(collection, dialog.cloneCombo.itemData(dialog.cloneCombo.currentIndex()))
        else:
            res = self.database.createCollection(collection)
        if not res:
            QtWidgets.QMessageBox.critical(
                self, 
                'Error creating collection', 
                'An error occured while trying to create the collection.\nThis is the message returned:\n\n{}'.format(self.database.query.lastError().databaseText()))
            return
        self.openCollection(collection, dest)

    def manageCollections(self):
        dialog = ManageCollectionsDialog(self, self.leftTabWidget.collections + self.rightTabWidget.collections)
        res = dialog.exec_()
        print(res)

    def closeCollection(self, index):
        if self.sender().count() <= 1:
            return
        widget = self.sender().removeTab(index)
        widget.deleteLater()

    def moveCollection(self, index, dest):
        if self.sender().count() <= 1:
            return
        name = self.sender().tabText(index)
        widget = self.sender().removeTab(index)
        index = dest.addTab(widget, name)
        dest.setCurrentIndex(index)

    def checkSplitter(self, pos):
        if pos < self.leftTabWidget.currentWidget().minimumSizeHint().width() * .5 and not self.rightTabBar.isVisible():
            self.setLeftVisible(False)
        else:
            self.setLeftVisible(True)
        if pos > self.splitter.width() - (self.rightTabWidget.currentWidget().minimumSizeHint().width() * .5) and not self.leftTabBar.isVisible():
            self.setRightVisible(False)
        else:
            self.setRightVisible(True)

    def setLeftVisible(self, visible, tab=-1):
        if visible:
            self.leftTabWidget.setMaximumWidth(16777215)
            if tab >= 0:
                self.leftTabWidget.setCurrentIndex(tab)
        else:
            self.leftTabWidget.setMaximumWidth(0)
        self.leftTabBar.setVisible(not visible)
        self.rightTabWidget.minimizeBtn.setVisible(visible)
        QtWidgets.QApplication.processEvents()

    def setRightVisible(self, visible, tab=-1):
        if visible:
            self.rightTabWidget.setMaximumWidth(16777215)
            if tab >= 0:
                self.rightTabWidget.setCurrentIndex(tab)
        else:
            self.rightTabWidget.setMaximumWidth(0)
        self.rightTabBar.setVisible(not visible)
        self.leftTabWidget.minimizeBtn.setVisible(visible)
        QtWidgets.QApplication.processEvents()

    def closeEvent(self, event):
        self.main.settings.setValue('sessionLayoutLeft', self.leftTabWidget.collections)
        self.main.settings.setValue('sessionLayoutRight', self.rightTabWidget.collections)
        QtWidgets.QMainWindow.closeEvent(self, event)
        self.closed.emit()

