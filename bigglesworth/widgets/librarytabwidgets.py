import sys
from Qt import QtCore, QtGui, QtWidgets, QtSql

from bigglesworth.const import factoryPresetsNamesDict, NameColumn
from bigglesworth.utils import setBold

Left, Right = 0, 1
NumKeys = {getattr(QtCore.Qt, 'Key_{}'.format(n)):n for n in range(10)}

class BaseCornerBtn(QtWidgets.QToolButton):
    def __init__(self, *args, **kwargs):
        QtWidgets.QToolButton.__init__(self, *args, **kwargs)
        size = self.fontMetrics().height()
        self.setFixedSize(size, size)

    def enterEvent(self, event):
        self.update()
        QtWidgets.QToolButton.enterEvent(self, event)

    def leaveEvent(self, event):
        self.update()
        QtWidgets.QToolButton.leaveEvent(self, event)

    def paintBase(self, qp):
        qp.setRenderHints(qp.Antialiasing)
        qp.translate(.5, .5)
        if self.mapFromGlobal(QtGui.QCursor.pos()) in self.rect():
            pen = qp.pen()
            qp.setPen(QtCore.Qt.lightGray)
            qp.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 2, 2)
            pen.setWidth(2)
            pen.setCapStyle(QtCore.Qt.RoundCap)
            qp.setPen(pen)


class LeftCornerBtn(BaseCornerBtn):
    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        self.paintBase(qp)
        path = QtGui.QPainterPath()
        path.moveTo(self.rect().width() * .65, self.rect().height() * .25)
        path.lineTo(self.rect().width() * .35, self.rect().height() * .5)
        path.lineTo(self.rect().width() * .65, self.rect().height() * .75)
        qp.drawPath(path)


class RightCornerBtn(BaseCornerBtn):
    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        self.paintBase(qp)
        path = QtGui.QPainterPath()
        path.moveTo(self.rect().width() * .35, self.rect().height() * .25)
        path.lineTo(self.rect().width() * .65, self.rect().height() * .5)
        path.lineTo(self.rect().width() * .35, self.rect().height() * .75)
        qp.drawPath(path)
#        qp.drawLine(self.rect().width() * .35, self.rect().height() * .25, self.rect().width() * .65, self.rect().height() * .5)
#        qp.drawLine(self.rect().width() * .65, self.rect().height() * .5, self.rect().width() * .35, self.rect().height() * .75)


class SideTabBar(QtWidgets.QTabBar):
    def __init__(self, *args, **kwargs):
        QtWidgets.QTabBar.__init__(self, *args, **kwargs)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding))

    def mousePressEvent(self, event):
        QtWidgets.QTabBar.mousePressEvent(self, event)
        if self.tabAt(event.pos()) >= 0:
            self.parent().maximize.emit(self.tabAt(event.pos()))


class SideTabBarWidget(QtWidgets.QWidget):
    maximize = QtCore.pyqtSignal(int)
    def __init__(self, *args, **kwargs):
        QtWidgets.QWidget.__init__(self, *args, **kwargs)
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        self.tabBar = SideTabBar(self)
        layout.addWidget(self.tabBar)
        self.addTab = self.tabBar.addTab
        self.removeTab = self.tabBar.removeTab
        self.setCurrentIndex = self.tabBar.setCurrentIndex
        self.moveTab = self.tabBar.moveTab
        self.setTabIcon = self.tabBar.setTabIcon
        self.count = self.tabBar.count

    def tabs(self):
        for index in range(self.tabBar.count()):
            print(self.tabBar.tabText(index))

class LeftTabBar(SideTabBarWidget):
    def __init__(self, *args, **kwargs):
        SideTabBarWidget.__init__(self, *args, **kwargs)
        self.tabBar.setShape(self.tabBar.RoundedWest)
        self.maximizeBtn = RightCornerBtn(clicked=lambda: self.maximize.emit(-1))
        self.layout().insertWidget(0, self.maximizeBtn, alignment=QtCore.Qt.AlignCenter)


class RightTabBar(SideTabBarWidget):
    def __init__(self, *args, **kwargs):
        SideTabBarWidget.__init__(self, *args, **kwargs)
        self.tabBar.setShape(self.tabBar.RoundedEast)
        self.maximizeBtn = LeftCornerBtn(clicked=lambda: self.maximize.emit(-1))
        self.layout().insertWidget(0, self.maximizeBtn, alignment=QtCore.Qt.AlignCenter)


class TabCornerWidget(QtWidgets.QWidget):
    def __init__(self, direction):
        QtWidgets.QWidget.__init__(self)
        layout = QtWidgets.QHBoxLayout()
        self.setLayout(layout)
        self.addBtn = QtWidgets.QToolButton()
        self.addBtn.setText('+')
        self.addBtn.setToolTip('Open collections menu')
        size = self.fontMetrics().width('+') + self.fontMetrics().descent() + 4
        self.addBtn.setFixedHeight(size)
        layout.addWidget(self.addBtn, alignment=QtCore.Qt.AlignLeft)
        self.minimizeBtn = LeftCornerBtn() if direction == Left else RightCornerBtn()
        self.minimizeBtn.setToolTip('Collapse to window side')
        layout.addWidget(self.minimizeBtn)
        if not 'linux' in sys.platform:
            if sys.platform == 'win32':
                layout.setContentsMargins(8, 2, 8, 2)
                self.setMinimumHeight(self.addBtn.minimumHeight() + 4)
            else:
                self.setMinimumHeight(layout.getContentsMargins()[3] + size)

#    def minimumSizeHint(self):
#        base = QtWidgets.QWidget.sizeHint(self)
#        height = self.fontMetrics().width('+')
#        base.setHeight(max(base.height(), 50))
#        return base


class LibraryTabBar(QtWidgets.QTabBar):
    def __init__(self, *args, **kwargs):
        QtWidgets.QTabBar.__init__(self, *args, **kwargs)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showMenu)

    def showMenu(self, pos):
        self.parent().showMenu(self.tabAt(pos), self.mapToGlobal(pos))


class BaseTabWidget(QtWidgets.QTabWidget):
    minimize = QtCore.pyqtSignal()
    newCollection = QtCore.pyqtSignal()
    openCollection = QtCore.pyqtSignal(str)
    exportRequested = QtCore.pyqtSignal(object, object)
    exportListRequested = QtCore.pyqtSignal(str)
    manageCollections = QtCore.pyqtSignal()
    tabMoveRequested = QtCore.pyqtSignal(int, object)
    tabSwapRequested = QtCore.pyqtSignal()
    fullDumpCollectionToBlofeldRequested = QtCore.pyqtSignal(str, bool)
    fullDumpBlofeldToCollectionRequested = QtCore.pyqtSignal(str, bool)
    findDuplicatesRequested = QtCore.pyqtSignal(object, object)

    def __init__(self, *args, **kwargs):
        QtWidgets.QTabWidget.__init__(self, *args, **kwargs)
        self.main = QtWidgets.QApplication.instance()
        self.database = self.main.database
        self.referenceModel = self.database.referenceModel
        tabBar = LibraryTabBar()
        self.setTabBar(tabBar)
#        self.referenceModel = QtSql.QSqlTableModel()
        self.settings = QtCore.QSettings()
        self.menu = QtWidgets.QMenu(self)

        metrics = {}
        dpi = (self.logicalDpiX() + self.logicalDpiY()) / 2.
        ratio = 1. / 76 * dpi
        for s in (1, 2, 4, 8):
            metrics['{}px'.format(s)] = s * ratio

        self.setStyleSheet('''
                QTabBar::close-button {{
                    image: url(:/icons/Bigglesworth/32x32/window-close.svg);
                    border: {1px} solid transparent;
                }}
                QTabBar::close-button:disabled {{
                    image: url(:/icons/Bigglesworth/32x32/window-close-disabled.svg);
                }}
                QTabBar::close-button:hover {{
                    border: {1px} solid palette(mid);
                    border-radius: {2px};
                }}
                /* scroll buttons are too tall (at least on oxygen) when using stylesheets, 
                we need to override them anyway */
                QTabBar QToolButton {{
                    border: {1px} solid palette(mid);
                    border-radius: {4px};
                    margin: {8px} {1px};
                    background-color: palette(button);
                }}
                QTabBar QToolButton:hover {{
                    border-color: palette(dark);
                }}
                '''.format(**metrics))

    @property
    def collections(self):
#        collections = []
#        for i in range(self.count()):
#            collections.append(self.widget(i).collection)
        return [self.widget(i).collection for i in range(self.count())]

    def keyPressEvent(self, event):
        if event.modifiers() == QtCore.Qt.ControlModifier:
            if ((event.key() == QtCore.Qt.Key_L and isinstance(self, RightTabWidget)) or \
            (event.key() == QtCore.Qt.Key_R and isinstance(self, LeftTabWidget))):
                siblingFocusWidget = self.siblingTabWidget.focusWidget()
                if siblingFocusWidget and not isinstance(siblingFocusWidget, (QtWidgets.QTabWidget, QtWidgets.QTabBar)):
                    siblingFocusWidget.setFocus()
                else:
                    self.siblingTabWidget.currentWidget().filterNameEdit.setFocus()
                return
            elif event.key() in NumKeys:
                tabIndex = NumKeys[event.key()]
                if tabIndex > 0:
                    self.setCurrentIndex(tabIndex - 1)
                    return
            elif event.key() == QtCore.Qt.Key_O:
                self.openCollectionMenu()
        elif event.key() == QtCore.Qt.Key_F2 and self.focusWidget() != self.currentWidget().collectionView and \
            self.currentWidget().editable:
                startEdit = not self.currentWidget().editModeBtn.isChecked()
                self.currentWidget().editModeBtn.setChecked(startEdit)
                if not self.currentWidget().collectionView.currentIndex().isValid():
                    self.currentWidget().collectionView.setCurrentIndex(self.currentWidget().collectionView.model().index(0, NameColumn))
                    if startEdit:
                        self.currentWidget().collectionView.setFocus()
        QtWidgets.QTabWidget.keyPressEvent(self, event)

    def setSiblings(self, tabBar, tabWidget):
        self.sideTabBar = tabBar
        self.tabBar().tabMoved.connect(self.sideTabBar.moveTab)
        self.siblingTabWidget = tabWidget
        self.currentChanged.connect(self.sideTabBar.setCurrentIndex)

    def addTab(self, widget, name):
        self.sideTabBar.addTab(name)
        index = QtWidgets.QTabWidget.addTab(self, widget, name)
        if sys.platform == 'darwin':
            self.setTabToolTip(index, 'ctrl+click or right click for menu')
        icon = QtGui.QIcon()
        if widget.collection is None:
            icon = QtGui.QIcon.fromTheme('go-home')
        elif widget.collection == 'Blofeld':
            icon = QtGui.QIcon(':/images/bigglesworth_logo.svg')
        elif widget.collection in factoryPresetsNamesDict:
            icon = QtGui.QIcon(':/images/factory.svg')
        else:
            self.settings.beginGroup('CollectionIcons')
            icon = QtGui.QIcon.fromTheme(self.settings.value(name, ''))
            self.settings.endGroup()
        if not icon.isNull():
            self.setTabIcon(index, icon)
        try:
            self.tabBar().tabButton(0, self.tabBar().RightSide).setVisible(False if self.count() == 1 else True)
        except:
            self.tabBar().tabButton(0, self.tabBar().LeftSide).setVisible(False if self.count() == 1 else True)
        if self.count() > 1:
            self.setMovable(True)
        return index

    def removeTab(self, index):
        self.sideTabBar.removeTab(index)
        widget = self.widget(index)
        QtWidgets.QTabWidget.removeTab(self, index)
        if self.count():
            try:
                self.tabBar().tabButton(0, self.tabBar().RightSide).setVisible(False if self.count() == 1 else True)
            except:
                self.tabBar().tabButton(0, self.tabBar().LeftSide).setVisible(False if self.count() == 1 else True)
        if self.count() <= 1:
            self.setMovable(False)
        return widget

    def setTabIcon(self, index, icon):
        QtWidgets.QTabWidget.setTabIcon(self, index, icon)
        self.sideTabBar.setTabIcon(index, icon)

    def showMenu(self, index, pos):
        self.menu.clear()
#        menu = self.getOpenCollectionMenu()
        closeAction = self.menu.addAction(QtGui.QIcon.fromTheme('window-close'), 'Close collection')
        closeAction.triggered.connect(lambda: self.tabCloseRequested.emit(index))
        side = 'right' if self.side == Left else 'left'
        tabSwapAction = self.menu.addAction(QtGui.QIcon.fromTheme('document-swap'), 'Swap views')
        tabSwapAction.triggered.connect(self.tabSwapRequested)
        moveTabAction = self.menu.addAction(QtGui.QIcon.fromTheme('arrow-{}'.format(side)), 'Move to {} panel'.format(side))
        moveTabAction.triggered.connect(lambda: self.tabMoveRequested.emit(index, self.siblingTabWidget))
        if self.count() <= 1:
            closeAction.setEnabled(False)
            moveTabAction.setEnabled(False)

        collection = self.widget(index).collection
        if collection:
            dumpMenu = self.menu.addMenu(QtGui.QIcon(':/images/dump.svg'), 'Dump "{}"'.format(collection))
            dumpMenu.setSeparatorsCollapsible(False)
            if collection not in factoryPresetsNamesDict:
                dumpMenu.addSection('Receive')
                self.dumpFromAllAction = dumpMenu.addAction('Dump all sounds FROM Blofeld')
                self.dumpFromAllAction.triggered.connect(lambda: self.fullDumpBlofeldToCollectionRequested.emit(collection, True))
                dumpFromPromptAction = dumpMenu.addAction('Dump sounds FROM Blofeld...')
                dumpFromPromptAction.triggered.connect(lambda: self.fullDumpBlofeldToCollectionRequested.emit(collection, False))
            dumpMenu.addSection('Send')
            dumpToAllAction = dumpMenu.addAction('Dump all sounds TO Blofeld')
            dumpToAllAction.triggered.connect(lambda: self.fullDumpCollectionToBlofeldRequested.emit(collection, True))

        exportMenu = self.menu.addMenu(QtGui.QIcon.fromTheme('document-save'), 'Export')
        exportAction = exportMenu.addAction(QtGui.QIcon.fromTheme('document-save'), 'Export sounds...')
        exportAction.triggered.connect(lambda: self.exportRequested.emit(-1, collection))
        exportListAction = exportMenu.addAction(QtGui.QIcon.fromTheme('document-print'), 'Save/print sound list...')
        exportListAction.triggered.connect(lambda: self.exportListRequested.emit(collection))
        if not collection:
            exportListAction.setEnabled(False)

        self.menu.addSeparator()
        collectionMenu = self.menu.addMenu(self.getOpenCollectionMenu())
        collectionMenu.setIcon(QtGui.QIcon.fromTheme('document-open'))
        self.menu.addSeparator()
        findDuplicatesAction = self.menu.addAction(QtGui.QIcon.fromTheme('edit-find'), 'Find duplicates...')
        findDuplicatesAction.triggered.connect(lambda: self.findDuplicatesRequested.emit(None, collection))
        self.menu.exec_(pos)

    def getOpenCollectionMenu(self):
        opened = self.collections + self.siblingTabWidget.collections
        menu = QtWidgets.QMenu('Open collection', self)
        menu.setSeparatorsCollapsible(False)
        menu.addSection('Custom collections')
        self.settings.beginGroup('CollectionIcons')
        for collection in self.referenceModel.collections:
            action = menu.addAction(factoryPresetsNamesDict.get(collection, collection))
            action.triggered.connect(lambda state, collection=collection: self.openCollection.emit(collection))
            if collection in opened:
                action.setEnabled(False)
            if collection == 'Blofeld':
                setBold(action)
                action.setIcon(QtGui.QIcon(':/images/bigglesworth_logo.svg'))
            elif self.settings.contains(collection):
                action.setIcon(QtGui.QIcon.fromTheme(self.settings.value(collection)))
        self.settings.endGroup()
        menu.addSection('Factory presets')
        for factory in self.referenceModel.factoryPresets:
            action = menu.addAction(QtGui.QIcon(':/images/factory.svg'), factoryPresetsNamesDict[factory])
            action.triggered.connect(lambda state, collection=factory: self.openCollection.emit(collection))
            if factory in opened:
                action.setEnabled(False)
        menu.addSeparator()
        mainLibraryAction = menu.addAction(QtGui.QIcon.fromTheme('go-home'), 'Main library')
        mainLibraryAction.triggered.connect(lambda: self.openCollection.emit(''))
        if '' in opened or None in opened:
            mainLibraryAction.setEnabled(False)
        menu.addSeparator()
        newAction = menu.addAction(QtGui.QIcon.fromTheme('document-new'), 'Create new collection')
        newAction.triggered.connect(self.newCollection)
        menu.addSeparator()
        manageAction = menu.addAction(QtGui.QIcon.fromTheme('preferences-other'), 'Manage collections')
        manageAction.triggered.connect(self.manageCollections)
        return menu

    def openCollectionMenu(self):
        self.getOpenCollectionMenu().exec_(self.cornerWidget().mapToGlobal(self.cornerWidget().addBtn.geometry().bottomLeft()))

    def checkIcons(self):
        self.settings.beginGroup('CollectionIcons')
        for index in range(self.count()):
            widget = self.widget(index)
            if widget.collection and widget.editable and widget.collection != 'Blofeld':
                iconName = self.settings.value(widget.collection, '')
                self.setTabIcon(index, QtGui.QIcon.fromTheme(iconName))
        self.settings.endGroup()



class LeftTabWidget(BaseTabWidget):
    def __init__(self, *args, **kwargs):
        BaseTabWidget.__init__(self, *args, **kwargs)
        cornerWidget = TabCornerWidget(Left)
        cornerWidget.addBtn.clicked.connect(self.openCollectionMenu)
        cornerWidget.minimizeBtn.clicked.connect(self.minimize)
        self.minimizeBtn = cornerWidget.minimizeBtn
        self.setCornerWidget(cornerWidget, QtCore.Qt.TopRightCorner)
        self.side = Left


class RightTabWidget(BaseTabWidget):
    def __init__(self, *args, **kwargs):
        BaseTabWidget.__init__(self, *args, **kwargs)
        cornerWidget = TabCornerWidget(Right)
        cornerWidget.addBtn.clicked.connect(self.openCollectionMenu)
        cornerWidget.minimizeBtn.clicked.connect(self.minimize)
        self.minimizeBtn = cornerWidget.minimizeBtn
        self.setCornerWidget(cornerWidget, QtCore.Qt.TopRightCorner)
        self.side = Right


