#!/usr/bin/env python2.7
# *-* encoding: utf-8 *-*

from random import randrange
from collections import OrderedDict
from Qt import QtCore, QtGui, QtWidgets, QtSql

from bigglesworth.const import factoryPresetsNamesDict
from bigglesworth.utils import loadUi, setBold
#from bigglesworth.library import LibraryModel
from bigglesworth.widgets import LibraryWidget, CollectionWidget
from bigglesworth.dialogs import NewCollectionDialog, ManageCollectionsDialog, TagsDialog, AboutDialog, SoundListExport
from bigglesworth.forcebwu import MayTheForce
#import icons

class MainWindow(QtWidgets.QMainWindow):
    closed = QtCore.pyqtSignal()
    findDuplicatesRequested = QtCore.pyqtSignal(str, object)
    exportRequested = QtCore.pyqtSignal(object, object)
    importRequested = QtCore.pyqtSignal()
    soundEditRequested = QtCore.pyqtSignal(str, str)
    #blofeld index/buffer, collection, index, multi
    dumpFromRequested = QtCore.pyqtSignal(object, object, int, bool)
    #uid, blofeld index/buffer, multi
    dumpToRequested = QtCore.pyqtSignal(object, object, bool)

    def __init__(self, parent):
        QtWidgets.QMainWindow.__init__(self)
        loadUi('ui/mainwindow.ui', self)
#        QtGui.QIcon.setThemeName('iconTheme')
        self.main = parent
        self.main.midiConnChanged.connect(lambda inConn, outConn: self.showGlobalsAction.setEnabled(True if all((inConn, outConn)) else False))
        self.database = parent.database
        self.database.tagsModel.dataChanged.connect(self.checkTagFilters)
#        self.referenceModel = QtSql.QSqlTableModel()
        self.referenceModel = self.database.referenceModel
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
            #import sessions and remove duplicates
            left = list(OrderedDict.fromkeys(self.main.settings.value('sessionLayoutLeft', ['Blofeld'], 'QStringList')))
            right = list(OrderedDict.fromkeys(self.main.settings.value('sessionLayoutRight', [None], 'QStringList')))
            for side in (left, right):
                for i, c in enumerate(side):
                    if c == '':
                        side[i] = None
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
                if collection not in (None, 'Blofeld') and collection not in self.database.referenceModel.allCollections:
                    print (collection, 'not found?!')
                    continue
                self.openCollection(collection, tab)

#        if self.leftTabWidget.count() < 1:
#            collectionWidget = CollectionWidget(self, 'Blofeld')
#            self.leftTabWidget.addTab(collectionWidget, 'Blofeld')
#        if self.rightTabWidget.count() < 1:
#            libraryWidget = LibraryWidget(self)
#            self.rightTabWidget.addTab(libraryWidget, 'Main library')

        self.splitter.moved.connect(self.checkSplitter)

        self.exportSoundListAction.triggered.connect(lambda: SoundListExport(self, None).exec_())

        self.leftTabWidget.openCollection.connect(self.openCollection)
        self.leftTabWidget.newCollection.connect(self.newCollection)
        self.leftTabWidget.manageCollections.connect(self.manageCollections)
        self.leftTabWidget.tabCloseRequested.connect(self.closeCollection)
        self.leftTabWidget.tabMoveRequested.connect(self.moveCollection)
        self.leftTabWidget.tabSwapRequested.connect(self.tabSwap)
        self.rightTabWidget.openCollection.connect(self.openCollection)
        self.rightTabWidget.newCollection.connect(self.newCollection)
        self.rightTabWidget.newCollection.connect(self.manageCollections)
        self.rightTabWidget.tabCloseRequested.connect(self.closeCollection)
        self.rightTabWidget.tabMoveRequested.connect(self.moveCollection)
        self.rightTabWidget.tabSwapRequested.connect(self.tabSwap)

        self.editTagsAction.triggered.connect(self.editTags)
        self.manageCollectionsAction.triggered.connect(self.manageCollections)
        self.createCollectionAction.triggered.connect(self.newCollection)
        self.libraryMenu.aboutToShow.connect(self.updateCollectionMenu)
#        self.openCollectionAction.triggered.connect(self.openCollection)

        self.importAction.triggered.connect(self.importRequested)
        self.exportAction.triggered.connect(lambda: self.exportRequested.emit([], None))
        self.aboutAction.triggered.connect(self.showAbout)
        self.aboutQtAction.triggered.connect(lambda: QtWidgets.QMessageBox.aboutQt(self, 'About Qt...'))

        self.openCollectionMenu.addSeparator().setText('Personal collections')
        blofeldAction = self.openCollectionMenu.addAction(QtGui.QIcon(':/images/bigglesworth_logo.svg'), 'Blofeld')
        blofeldAction.triggered.connect(lambda: self.openCollection('Blofeld', self.leftTabWidget))

        self.collections = {'Blofeld': blofeldAction}
        for collection in self.referenceModel.collections[1:]:
            action = self.openCollectionMenu.addAction(collection)
            action.triggered.connect(lambda state, collection=collection: self.openCollection(collection, self.leftTabWidget))
            self.collections[collection] = action

        self.openCollectionMenu.addSeparator().setText('Factory presets')
        for collection in self.referenceModel.factoryPresets:
            action = self.openCollectionMenu.addAction(QtGui.QIcon(':/images/factory.svg'), factoryPresetsNamesDict[collection])
            action.triggered.connect(lambda state, collection=collection: self.openCollection(collection, self.leftTabWidget))

        self.openCollectionMenu.addSeparator()
        action = self.openCollectionMenu.addAction(QtGui.QIcon.fromTheme('go-home'), 'Main library')
        action.triggered.connect(lambda: self.openCollection.emit(''))

    @property
    def editorWindow(self):
        return QtWidgets.QApplication.instance().editorWindow

    def updateCollectionMenu(self):
#        self.openCollectionMenu.clear()
#        self.referenceModel.setTable('reference')
        exists = []
        for collection in self.referenceModel.collections:
            exists.append(collection)
            if collection in self.collections:
                continue
            action = self.openCollectionMenu.addAction(collection)
            action.triggered.connect(lambda state, collection=collection: self.openCollection(collection, self.leftTabWidget))
            self.collections.append[collection] = action
        for collection, action in self.collections.items():
            if collection not in exists:
                self.openCollectionMenu.removeAction(action)
                self.collections.pop(collection)
        return

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
                    collWidget = tabwidget.widget(tab)
                    collWidget.filterTagsEdit.setTags([])
                    collWidget.collectionView.viewport().update()
        for collection in self.database.collections.values():
            collection.updated.emit()

    def openCollection(self, collection='', dest=None):
        if collection:
            name = factoryPresetsNamesDict.get(collection, collection)
            colWidget = CollectionWidget(self, collection)
        else:
            name = 'Main library'
            colWidget = LibraryWidget(self)
        if collection in self.leftTabWidget.collections:
            self.leftTabWidget.setCurrentIndex(self.leftTabWidget.collections.index(collection))
            return self.leftTabWidget.currentWidget()
        elif collection in self.rightTabWidget.collections:
            self.rightTabWidget.setCurrentIndex(self.rightTabWidget.collections.index(collection))
            return self.rightTabWidget.currentWidget()
        if dest is None:
            dest = self.sender()
            if not dest in (self.leftTabWidget, self.rightTabWidget):
                dest = self.leftTabWidget
        colWidget.dumpFromRequested.connect(self.dumpFromRequested)
        colWidget.dumpToRequested.connect(self.dumpToRequested)
        colWidget.findDuplicatesRequested.connect(self.findDuplicatesRequested)
        colWidget.exportRequested.connect(self.exportRequested)
        index = dest.addTab(colWidget, name)
        dest.setCurrentIndex(index)
        return colWidget

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

    def tabSwap(self):
        leftTabs = []
        rightTabs = []
        leftIndex = self.leftTabWidget.currentIndex()
        rightIndex = self.rightTabWidget.currentIndex()
        for tab, destTabList in zip((self.leftTabWidget, self.rightTabWidget), (rightTabs, leftTabs)):
            for index in range(tab.count()):
                name = tab.tabText(0)
                widget = tab.removeTab(0)
                destTabList.append((widget, name))
        for tab, destTabList in zip((self.leftTabWidget, self.rightTabWidget), (leftTabs, rightTabs)):
            for widget, name in destTabList:
                tab.addTab(widget, name)
        self.leftTabWidget.setCurrentIndex(rightIndex)
        self.rightTabWidget.setCurrentIndex(leftIndex)

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

    def checkTagFilters(self):
#        print('checco')
        for widget in self.leftTabWidget.collections + self.rightTabWidget.collections:
            if isinstance(widget, CollectionWidget):
                widget.filterTagsEdit.setTags()

    def showAbout(self):
        if not randrange(3):
            MayTheForce(self).exec_()
        else:
            AboutDialog(self).exec_()

    def closeEvent(self, event):
        self.main.settings.setValue('sessionLayoutLeft', self.leftTabWidget.collections)
        self.main.settings.setValue('sessionLayoutRight', self.rightTabWidget.collections)
        QtWidgets.QMainWindow.closeEvent(self, event)
        self.closed.emit()

