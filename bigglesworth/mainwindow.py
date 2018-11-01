#!/usr/bin/env python2.7
# *-* encoding: utf-8 *-*

from random import randrange
from collections import OrderedDict
from Qt import QtCore, QtGui, QtWidgets

from bigglesworth.const import factoryPresetsNamesDict
from bigglesworth.utils import loadUi
#from bigglesworth.library import LibraryModel
from bigglesworth.widgets import LibraryWidget, CollectionWidget, MidiStatusBarWidget
from bigglesworth.dialogs import NewCollectionDialog, ManageCollectionsDialog, TagsDialog, SoundListExport, TagEditDialog
from bigglesworth.version import getUniqueVersionToMin
#import icons

class MainWindow(QtWidgets.QMainWindow):
    closed = QtCore.pyqtSignal()
    midiConnect = QtCore.pyqtSignal(object, int, bool)
    findDuplicatesRequested = QtCore.pyqtSignal(str, object)
    exportRequested = QtCore.pyqtSignal(object, object)
    importRequested = QtCore.pyqtSignal(object, object)
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
        self.settings = self.main.settings
        self.database = parent.database
        self.database.tagsModel.dataChanged.connect(self.checkTagFilters)
#        self.referenceModel = QtSql.QSqlTableModel()
        self.referenceModel = self.database.referenceModel
        self.midiWidget = MidiStatusBarWidget(self, menu=True)
        self.midiWidget.setMidiDevice(self.main.midiDevice)
        self.main.midiConnChanged.connect(self.midiWidget.midiConnChanged)
        self.main.midiEventSent.connect(self.midiWidget.midiEventSent)
        inConn, outConn = self.main.connections
        self.midiWidget.midiConnChanged(inConn, outConn, True)
        self.midiWidget.midiConnect.connect(self.midiConnect)
        self.statusbar.addPermanentWidget(self.midiWidget)
        self.statusbar.setDatabase(parent.database)

        self.leftTabWidget.setSiblings(self.leftTabBar, self.rightTabWidget)
        self.rightTabWidget.setSiblings(self.rightTabBar, self.leftTabWidget)
        self.leftTabBar.hide()
        self.leftTabWidget.minimizePanelRequested.connect(lambda: self.setLeftVisible(False))
        self.leftTabBar.maximize.connect(lambda tab: self.setLeftVisible(True, tab))
        self.rightTabBar.hide()
        self.rightTabWidget.minimizePanelRequested.connect(lambda: self.setRightVisible(False))
        self.rightTabBar.maximize.connect(lambda tab: self.setRightVisible(True, tab))

        #override sidebar and dualmode if firstrun/tutorial is on
        tutorialActive = not self.settings.value('FirstRunShown', False, bool) or self.settings.value('ShowLibrarianTutorial', True, bool)
        self.maskObject = None
            
        if tutorialActive:
            self.sidebar.setVisible(True)
        else:
            sidebarMode = self.settings.value('startupSidebarMode', 2, int) if not tutorialActive else 2
            if sidebarMode == 2:
                if self.main.settings.value('windowState'):
                    try:
                        self.restoreState(self.main.settings.value('windowState'), getUniqueVersionToMin())
                        print('Window state successfully restored')
                    except Exception as e:
                        print('Error restoring main window state: {}'.format(e))
            else:
                self.sidebar.setVisible(sidebarMode)

        if self.main.settings.value('saveLibrarianGeometry', True, bool) and self.main.settings.contains('librarianGeometry'):
            self.restoreGeometry(self.main.settings.value('librarianGeometry'))

        #import sessions and use OrderedDicts to remove duplicates and keep ordering
        #but, before that, check unset configurations from previous versions for testers...
        #TODO: this can be removed in the future versions...
        existsStartupDualMode = self.main.settings.contains('startupDualMode')
        startupDualMode = self.main.settings.value('startupDualMode', 2, int)
        dualMode = self.main.settings.value('dualMode', False, bool)
        startupSessionMode = self.main.settings.value('startupSessionMode', 2, int)

        if not tutorialActive and ((startupDualMode and dualMode) or (not existsStartupDualMode and self.main.settings.contains('sessionLayoutRight'))):
            if startupSessionMode >= 2:
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
            elif startupSessionMode:
                left = [None]
                right = ['Blofeld']
            else:
                left = ['Blofeld']
                right = [None]

            actualCollections = []
            for tab, collections in (self.leftTabWidget, left), (self.rightTabWidget, right):
                for collection in collections:
                    if collection not in (None, 'Blofeld') and collection not in self.database.referenceModel.allCollections:
                        print (collection, 'not found?!')
                        continue
                    actualCollections.append(collection)
                    self.openCollection(collection, tab)
            while not all((left, right)):
                for collection in reversed(self.database.referenceModel.allCollections):
                    if collection not in actualCollections:
                        if not left:
                            self.openCollection(collection, self.leftTabWidget)
                            left.append(collection)
                        else:
                            self.openCollection(collection, self.rightTabWidget)
                            right.append(collection)

            panelLayout = self.settings.value('sessionPanelLayout', 3, int)
            if panelLayout == 1:
                self.setRightVisible(False)
            elif panelLayout == 2:
                self.setLeftVisible(False)
            else:
                sizes = self.settings.value('sessionPanelSizes', None)
                if sizes:
                    self.splitter.restoreState(sizes)

        else:
            if tutorialActive:
                left = ['Blofeld']
            elif startupSessionMode >= 2:
                left = list(OrderedDict.fromkeys(self.main.settings.value('sessionLayoutLeft', ['Blofeld'], 'QStringList')))
            elif startupSessionMode:
                left = [None]
            else:
                left = ['Blofeld']
            if '' in left:
                left[left.index('')] = None
            for c in reversed(left):
                if c in ['Blofeld', None]:
                    continue
                if c not in self.database.referenceModel.allCollections:
                    left.remove(c)
            if not left:
                left = ['Blofeld']

            for collection in left:
                self.openCollection(collection, self.leftTabWidget)

            self.rightTabWidget.setVisible(False)
            self.rightTabBar.setVisible(False)
            self.leftTabWidget.minimizeBtn.setVisible(False)

#        self.sidebar.setVisible(self.settings.value('librarySideBar', True, bool))
        self.dockLibrary.newCollection.connect(self.newCollection)
        self.dockLibrary.manageCollections.connect(self.manageCollections)
        self.dockLibrary.openCollection.connect(self.openCollection)
        self.dockLibrary.editTag.connect(self.editTag)
        self.dockLibrary.editTags.connect(self.editTags)
        self.dockLibrary.deleteTag.connect(self.deleteTag)
        self.splitter.moved.connect(self.checkSplitter)

        self.exportSoundListAction.triggered.connect(lambda: SoundListExport(self, None).exec_())

        self.leftTabWidget.openCollection.connect(self.openCollection)
        self.leftTabWidget.openCollection[str, object].connect(self.openCollection)
        self.leftTabWidget.openCollection[str, object, int].connect(self.openCollection)
        self.leftTabWidget.newCollection.connect(self.newCollection)
        self.leftTabWidget.manageCollections.connect(self.manageCollections)
        self.leftTabWidget.tabCloseRequested.connect(self.closeCollection)
        self.leftTabWidget.tabMoveRequested.connect(self.moveCollection)
        self.leftTabWidget.panelSwapRequested.connect(self.panelSwap)
        self.leftTabWidget.toggleDualView.connect(self.toggleDualView)
        self.rightTabWidget.openCollection.connect(self.openCollection)
        self.rightTabWidget.openCollection[str, object].connect(self.openCollection)
        self.rightTabWidget.openCollection[str, object, int].connect(self.openCollection)
        self.rightTabWidget.newCollection.connect(self.newCollection)
        self.rightTabWidget.manageCollections.connect(self.manageCollections)
        self.rightTabWidget.tabCloseRequested.connect(self.closeCollection)
        self.rightTabWidget.tabMoveRequested.connect(self.moveCollection)
        self.rightTabWidget.panelSwapRequested.connect(self.panelSwap)
        self.rightTabWidget.toggleDualView.connect(self.toggleDualView)

        self.editTagsAction.triggered.connect(self.editTags)
        self.manageCollectionsAction.triggered.connect(self.manageCollections)
        self.createCollectionAction.triggered.connect(self.newCollection)
        self.libraryMenu.aboutToShow.connect(self.updateLibraryMenu)
#        self.openCollectionAction.triggered.connect(self.openCollection)

        self.importAction.triggered.connect(lambda: self.importRequested.emit(None, None))
        self.exportAction.triggered.connect(lambda: self.exportRequested.emit([], None))
        self.toggleLibrarySidebarAction.triggered.connect(lambda: self.sidebar.setVisible(not self.sidebar.isVisible()))
        self.toggleDualViewAction.triggered.connect(self.toggleDualView)

        self.openCollectionMenu.addSection('Custom collections')
        blofeldAction = self.openCollectionMenu.addAction(QtGui.QIcon(':/images/bigglesworth_logo.svg'), 
            'Blofeld ({})'.format(self.database.getCountForCollection('Blofeld')))
        blofeldAction.triggered.connect(lambda: self.openCollection('Blofeld', self.leftTabWidget))

        self.collections = {'Blofeld': blofeldAction}
        self.settings.beginGroup('CollectionIcons')
        for collection in self.referenceModel.collections[1:]:
            if self.settings.contains(collection):
                icon = QtGui.QIcon.fromTheme(self.settings.value(collection))
            else:
                icon = QtGui.QIcon()
            action = self.openCollectionMenu.addAction(icon, '{} ({})'.format(
                collection, self.database.getCountForCollection(collection)))
            action.triggered.connect(lambda state, collection=collection: self.openCollection(collection, self.leftTabWidget))
            self.collections[collection] = action
        self.settings.endGroup()

        self.openCollectionMenu.addSection('Factory presets')
        for collection in self.referenceModel.factoryPresets:
            action = self.openCollectionMenu.addAction(QtGui.QIcon(':/images/factory.svg'), factoryPresetsNamesDict[collection])
            action.triggered.connect(lambda state, collection=collection: self.openCollection(collection, self.leftTabWidget))

        self.openCollectionMenu.addSeparator()
        action = self.openCollectionMenu.addAction(QtGui.QIcon.fromTheme('go-home'), 'Main library')
        action.triggered.connect(lambda: self.openCollection(''))

        self.menubar.addMenu(self.main.getWindowsMenu(self, self.menubar))
        self.menubar.addMenu(self.main.getAboutMenu(self, self.menubar))

#        self.createMaskObject()

    def activate(self):
        self.show()
        self.activateWindow()

    def createMaskObject(self):
        from bigglesworth.firstrun import MaskObject
        self.maskObject = MaskObject(self)
        self.maskObject.setVisible(True)

    def destroyMaskObject(self):
        if self.maskObject:
            self.maskObject.deleteLater()
            self.maskObject = None

    @property
    def panelLayout(self):
        return int(not self.leftTabBar.isVisible()) | (not self.rightTabBar.isVisible()) << 1

    @property
    def editorWindow(self):
        return QtWidgets.QApplication.instance().editorWindow

    @property
    def dualMode(self):
        return bool(self.rightTabWidget.width()) or self.rightTabBar.isVisible()

    def updateLibraryMenu(self):
        self.toggleLibrarySidebarAction.setText('{} library sidebar'.format(('Show', 'Hide')[self.sidebar.isVisible()]))
        if self.dualMode:
            self.toggleDualViewAction.setText('Close twin panel view')
            self.toggleDualViewAction.setIcon(QtGui.QIcon.fromTheme('view-right-close'))
        else:
            self.toggleDualViewAction.setText('Open twin panel view')
            self.toggleDualViewAction.setIcon(QtGui.QIcon.fromTheme('view-split-left-right'))
#        self.openCollectionMenu.clear()
#        self.referenceModel.setTable('reference')
        exists = []
        self.settings.beginGroup('CollectionIcons')
        for collection in self.referenceModel.collections:
            exists.append(collection)
            if collection in self.collections:
                continue
            if self.settings.contains(collection):
                icon = QtGui.QIcon.fromTheme(self.settings.value(collection))
            else:
                icon = QtGui.QIcon()
            action = self.openCollectionMenu.addAction(icon, collection)
            action.triggered.connect(lambda state, collection=collection: self.openCollection(collection, self.leftTabWidget))
            self.collections[collection] = action
        for collection, action in self.collections.items():
            if collection not in exists:
                self.openCollectionMenu.removeAction(action)
                self.collections.pop(collection)
        self.settings.endGroup()
        return

    @QtCore.pyqtSlot()
    def toggleDualView(self, toRemove=None):
        if self.dualMode:
            if self.leftTabBar.isVisible():
                self.setLeftVisible(True)
            self.rightTabWidget.setVisible(False)
            self.rightTabBar.setVisible(False)
            self.leftTabWidget.minimizeBtn.setVisible(False)
            current = self.rightTabWidget.currentIndex() + self.leftTabWidget.count()
            for i in range(self.rightTabWidget.count()):
                name = self.rightTabWidget.tabText(0)
                widget = self.rightTabWidget.removeTab(0)
                self.leftTabWidget.addTab(widget, name)
            self.leftTabWidget.setCurrentIndex(current)
        else:
            self.rightTabWidget.setVisible(True)
            self.leftTabWidget.minimizeBtn.setVisible(True)
            self.setRightVisible(True, 0)
            if toRemove is None:
                current = self.leftTabWidget.currentIndex()
                count = self.leftTabWidget.count()
                last = count - 1
                toRemove = -1
                if current < last:
                    toRemove = last
                elif current >= 1:
                    toRemove = 0
            if toRemove >= 0:
                name = self.leftTabWidget.tabText(toRemove)
                widget = self.leftTabWidget.removeTab(toRemove)
                self.rightTabWidget.addTab(widget, name)
            else:
                for collection in reversed(self.referenceModel.allCollections):
                    if collection not in self.leftTabWidget.collections:
                        self.openCollection(collection, self.rightTabWidget)
                        break

    def programChange(self, bank, prog):
        if isinstance(self.leftTabWidget.currentWidget(), CollectionWidget):
            self.leftTabWidget.currentWidget().focusIndex(bank, prog)
        if self.dualMode and isinstance(self.rightTabWidget.currentWidget(), CollectionWidget):
            self.rightTabWidget.currentWidget().focusIndex(bank, prog)

    def editTag(self, oldName=''):
        new = not oldName
        dialog = TagEditDialog(self, oldName, new=new)
        if not dialog.exec_():
            return
        self.database.editTag(dialog.tagEdit.text(), oldName, dialog.backgroundColor, dialog.foregroundColor)
        if new and self.sidebar.isVisible():
            self.dockLibrary.expandTags()

    def editTags(self):
        tagsView = TagsDialog(self)
        if tagsView.exec_():
            for tabwidget in self.leftTabWidget, self.rightTabWidget:
                for tab in range(tabwidget.count()):
                    collWidget = tabwidget.widget(tab)
                    collWidget.filterTagsEdit.setTags([])
                    collWidget.collectionView.viewport().update()
        if tagsView.changed:
            for collection in self.database.collections.values():
                collection.updated.emit()

    def deleteTag(self, tag):
        message = 'Delete tag "{}"?'.format(tag)
        tagCount = self.database.getCountForTag(tag)
        if tagCount:
            message += '\n\nThis action will affect {} sound{}.'.format(tagCount, 's' if tagCount > 1 else '')
        else:
            message += '\n\nIt seems that no sound is using it.'

        if QtWidgets.QMessageBox.question(self, 'Delete tag', message, 
            QtWidgets.QMessageBox.Ok|QtWidgets.QMessageBox.Cancel) != QtWidgets.QMessageBox.Ok:
                return

        if self.database.deleteTag(tag):
            for tabwidget in self.leftTabWidget, self.rightTabWidget:
                for tab in range(tabwidget.count()):
                    collWidget = tabwidget.widget(tab)
                    collWidget.filterTagsEdit.setTags([])
                    collWidget.collectionView.viewport().update()
            for collection in self.database.collections.values():
                collection.updated.emit()

    def openCollection(self, collection='', dest=None, index=-1):
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
        colWidget.importRequested.connect(self.importRequested)
        colWidget.exportRequested.connect(self.exportRequested)
        index = dest.insertTab(index, colWidget, name)
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
            res = self.database.createCollection(collection, dialog.cloneCombo.itemData(dialog.cloneCombo.currentIndex()), iconName=dialog.currentIconName())
        else:
            res = self.database.createCollection(collection, iconName=dialog.currentIconName(), initBanks=dialog.initBanks())
        if not res:
            QtWidgets.QMessageBox.critical(
                self, 
                'Error creating collection', 
                'An error occured while trying to create the collection.\nThis is the message returned:\n\n{}'.format(self.database.query.lastError().databaseText()))
            return
#        self.main.settings.beginGroup('CollectionIcons')
#        self.main.settings.setValue(collection, dialog.currentIconName())
#        self.main.settings.endGroup()
        self.openCollection(collection, dest)
        if self.sidebar.isVisible():
            self.dockLibrary.expandCollections()

    def manageCollections(self):
        ManageCollectionsDialog(self, self.leftTabWidget.collections + self.rightTabWidget.collections).exec_()
        self.leftTabWidget.checkIcons()
        self.rightTabWidget.checkIcons()
        self.dockLibrary.rebuild()

    def closeCollection(self, index):
        source = self.sender()
        if not self.dualMode and source.count() <= 1:
            return
        widget = source.removeTab(index)
        widget.deleteLater()
        if not source.count():
            self.rightTabWidget.setVisible(False)
            self.rightTabBar.setVisible(False)
            self.leftTabWidget.minimizeBtn.setVisible(False)
            if source == self.leftTabWidget:
                current = self.rightTabWidget.currentIndex()
                for i in range(self.rightTabWidget.count()):
                    name = self.rightTabWidget.tabText(0)
                    widget = self.rightTabWidget.removeTab(0)
                    self.leftTabWidget.addTab(widget, name)
                self.leftTabWidget.setCurrentIndex(current)
            if self.leftTabWidget.count() == 1:
                try:
                    self.leftTabWidget.tabBar().tabButton(0, self.leftTabWidget.tabBar().RightSide).setVisible(False)
                except:
                    self.leftTabWidget.tabBar().tabButton(0, self.leftTabWidget.tabBar().LeftSide).setVisible(False)

    def moveCollection(self, index, dest, targetIndex=-1):
        source = dest.siblingTabWidget
        if source.count() <= 1 and not self.dualMode:
            return
        if self.dualMode and source.count() > 1:
            name = source.tabText(index)
            widget = source.removeTab(index)
            targetIndex = dest.insertTab(targetIndex, widget, name)
            dest.setCurrentIndex(targetIndex)
        else:
            self.toggleDualView(index)
#        source.tabRemoved(index)
#        source.update()

    def panelSwap(self):
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
        for widget in self.leftTabWidget.collections + self.rightTabWidget.collections:
            if isinstance(widget, CollectionWidget):
                widget.filterTagsEdit.setTags()

    def resizeEvent(self, event):
        if self.maskObject:
            self.maskObject.resize(self.size())
        QtWidgets.QMainWindow.resizeEvent(self, event)

    def saveLayout(self):
        #prima o poi questo puoi rimuoverlo
        self.main.settings.remove('librarySideBar')
#        self.main.settings.setValue('librarySideBar', self.sidebar.isVisible())
        self.main.settings.setValue('windowState', self.saveState(getUniqueVersionToMin()))
        if self.main.settings.value('saveLibrarianGeometry', True, bool):
            self.main.settings.setValue('librarianGeometry', self.saveGeometry())
        else:
            self.main.settings.remove('librarianGeometry')
        self.main.settings.setValue('sessionLayoutLeft', self.leftTabWidget.collections)
        self.main.settings.setValue('dualMode', self.dualMode)
        if not self.dualMode:
            self.main.settings.remove('sessionLayoutRight')
            self.main.settings.remove('sessionPanelLayout')
            self.main.settings.remove('sessionPanelSizes')
        else:
            self.main.settings.setValue('sessionLayoutRight', self.rightTabWidget.collections)
            self.main.settings.setValue('sessionPanelLayout', self.panelLayout)
            if self.panelLayout == 3:
                self.main.settings.setValue('sessionPanelSizes', self.splitter.saveState())
            else:
                self.main.settings.remove('sessionPanelSizes')
        self.main.settings.sync()

    def closeEvent(self, event):
        self.saveLayout()
        QtWidgets.QMainWindow.closeEvent(self, event)
        self.closed.emit()

