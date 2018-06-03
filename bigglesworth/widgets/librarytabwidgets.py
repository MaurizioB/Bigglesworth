from Qt import QtCore, QtGui, QtWidgets, QtSql

from bigglesworth.const import factoryPresetsNamesDict
from bigglesworth.utils import setBold

Left, Right = 0, 1

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
        size = max(self.fontMetrics().width('+'), self.fontMetrics().height())
        self.addBtn.setMinimumHeight(size)
        layout.addWidget(self.addBtn, alignment=QtCore.Qt.AlignLeft)
        self.minimizeBtn = LeftCornerBtn() if direction == Left else RightCornerBtn()
        layout.addWidget(self.minimizeBtn)

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
    manageCollections = QtCore.pyqtSignal()
    tabMoveRequested = QtCore.pyqtSignal(int, object)
    tabSwapRequested = QtCore.pyqtSignal()
    fullDumpCollectionToBlofeldRequested = QtCore.pyqtSignal(str, bool)
    fullDumpBlofeldToCollectionRequested = QtCore.pyqtSignal(str, bool)

    def __init__(self, *args, **kwargs):
        QtWidgets.QTabWidget.__init__(self, *args, **kwargs)
        tabBar = LibraryTabBar()
        self.setTabBar(tabBar)
        self.referenceModel = QtSql.QSqlTableModel()
        self.menu = QtWidgets.QMenu(self)

    @property
    def collections(self):
#        collections = []
#        for i in range(self.count()):
#            collections.append(self.widget(i).collection)
        return [self.widget(i).collection for i in range(self.count())]

    def setSiblings(self, tabBar, tabWidget):
        self.sideTabBar = tabBar
        self.tabBar().tabMoved.connect(self.sideTabBar.moveTab)
        self.siblingTabWidget = tabWidget
        self.currentChanged.connect(self.sideTabBar.setCurrentIndex)

    def addTab(self, widget, name):
        self.sideTabBar.addTab(name)
        index = QtWidgets.QTabWidget.addTab(self, widget, name)
        self.tabBar().tabButton(0, self.tabBar().RightSide).setVisible(False if self.count() == 1 else True)
        if self.count() > 1:
            self.setMovable(True)
        return index

    def removeTab(self, index):
        self.sideTabBar.removeTab(index)
        widget = self.widget(index)
        QtWidgets.QTabWidget.removeTab(self, index)
        if self.count():
            self.tabBar().tabButton(0, self.tabBar().RightSide).setVisible(False if self.count() == 1 else True)
        if self.count() <= 1:
            self.setMovable(False)
        return widget

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
            dumpMenu = self.menu.addMenu('Dump "{}"'.format(collection))
            dumpMenu.setSeparatorsCollapsible(False)
            sep = dumpMenu.addSeparator()
            sep.setText('Receive')
            self.dumpFromAllAction = dumpMenu.addAction('Dump all sounds FROM Blofeld')
            self.dumpFromAllAction.triggered.connect(lambda: self.fullDumpBlofeldToCollectionRequested.emit(collection, True))
            dumpFromPromptAction = dumpMenu.addAction('Dump sounds FROM Blofeld...')
            dumpFromPromptAction.triggered.connect(lambda: self.fullDumpBlofeldToCollectionRequested.emit(collection, False))
            sep = dumpMenu.addSeparator()
            sep.setText('Send')
            dumpToAllAction = dumpMenu.addAction('Dump all sounds TO Blofeld')
            dumpToAllAction.triggered.connect(lambda: self.fullDumpCollectionToBlofeldRequested.emit(collection, True))

        self.menu.addSeparator()
        self.menu.addMenu(self.getOpenCollectionMenu())
#        menu.insertAction(menu.actions()[0], moveTabAction)
#        menu.insertAction(moveTabAction, closeAction)
        self.menu.exec_(pos)

    def getOpenCollectionMenu(self):
        self.referenceModel.setTable('reference')
#        self.referenceModel.refresh()
        current = [self.tabText(t).lower() for t in range(self.count())]
        current.extend([self.siblingTabWidget.tabText(t).lower() for t in range(self.siblingTabWidget.count())])
        menu = QtWidgets.QMenu('Open collection', self)
        menu.setSeparatorsCollapsible(False)
        sep = menu.addSeparator()
        sep.setText('Custom collections')
        for c in range(5, self.referenceModel.columnCount()):
            collection = self.referenceModel.headerData(c, QtCore.Qt.Horizontal)
            if collection.lower() in current:
                continue
            action = menu.addAction(collection)
            action.triggered.connect(lambda state, collection=collection: self.openCollection.emit(collection))
            if collection == 'Blofeld':
                setBold(action)
                action.setIcon(QtGui.QIcon.fromTheme('go-home'))
        if len(menu.actions()) <= 1:
            sep.setVisible(False)
        sep = menu.addSeparator()
        sep.setText('Factory presets')
        for c in range(2, 5):
            collection = self.referenceModel.headerData(c, QtCore.Qt.Horizontal)
            if collection.lower() in current:
                continue
            action = menu.addAction(factoryPresetsNamesDict[collection])
            action.triggered.connect(lambda state, collection=collection: self.openCollection.emit(collection))
        if len(menu.actions()) <= 1:
            sep.setVisible(False)
        if not 'main library' in current:
            menu.addSeparator()
            action = menu.addAction(QtGui.QIcon.fromTheme('go-home'), 'Main library')
            action.triggered.connect(lambda: self.openCollection.emit(''))
        menu.addSeparator()
        newAction = menu.addAction(QtGui.QIcon.fromTheme('document-new'), 'Create new collection')
        newAction.triggered.connect(self.newCollection)
        menu.addSeparator()
        manageAction = menu.addAction(QtGui.QIcon.fromTheme('preferences-other'), 'Manage collections')
        manageAction.triggered.connect(self.manageCollections)
        return menu

    def openCollectionMenu(self):
        self.getOpenCollectionMenu().exec_(self.cornerWidget().mapToGlobal(self.cornerWidget().addBtn.geometry().bottomLeft()))


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


