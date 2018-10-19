import sys
from Qt import QtCore, QtGui, QtWidgets, QtSql

from bigglesworth.const import factoryPresetsNamesDict, NameColumn
from bigglesworth.utils import setBold
from bigglesworth.widgets import DroppableTabBar

Left, Right = 1, 2
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
        self.insertTab = self.tabBar.insertTab
        self.removeTab = self.tabBar.removeTab
        self.setCurrentIndex = self.tabBar.setCurrentIndex
        self.moveTab = self.tabBar.moveTab
        self.setTabIcon = self.tabBar.setTabIcon
        self.count = self.tabBar.count
        self.iconSize = self.tabBar.iconSize


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


class LibraryTabBar(DroppableTabBar):
    def __init__(self, *args, **kwargs):
        DroppableTabBar.__init__(self, *args, **kwargs)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showMenu)
        self.startIndex = None
        self.deltaX = 0
        self.settings = QtCore.QSettings()

    def startDrag(self):
        byteArray = QtCore.QByteArray()
        stream = QtCore.QDataStream(byteArray, QtCore.QIODevice.WriteOnly)
        collection = self.parent().collections[self.currentIndex()]
        stream.writeQVariant(collection)
        mimeData = QtCore.QMimeData()
        mimeData.setData('bigglesworth/collectionObject', byteArray)

        iconSize = self.fontMetrics().height()
        displayName = self.tabText(self.currentIndex())
        rect = QtCore.QRect(0, 0, self.fontMetrics().width(displayName + ' ' * 4), iconSize * 2)
        
        icon = self.tabIcon(self.currentIndex())
        if not icon.isNull():
            rect.setWidth(rect.width() + iconSize + 8)

        pixmap = QtGui.QPixmap(rect.size())
        pixmap.fill(QtCore.Qt.transparent)

        palette = self.palette()
        qp = QtGui.QPainter(pixmap)
        qp.setRenderHints(qp.Antialiasing)
        qp.translate(.5, .5)
        qp.setPen(palette.color(palette.Mid))
        qp.setBrush(palette.color(palette.Midlight))
        qp.drawRoundedRect(rect.adjusted(0, 0, -1, -1), 4, 4)

        if not icon.isNull():
            left = iconSize + 4
            iconPixmap = icon.pixmap(iconSize)
            if iconPixmap.width() != iconSize:
                iconPixmap = iconPixmap.scaledToWidth(iconSize, QtCore.Qt.SmoothTransformation)
            qp.drawPixmap(QtCore.QRect(4, rect.center().y() - iconSize / 2, iconSize, iconSize), iconPixmap, iconPixmap.rect())
        else:
            left = 0
        qp.setPen(palette.color(palette.WindowText))
        qp.drawText(rect.adjusted(left, 0, 0, 0), QtCore.Qt.AlignCenter, displayName)
        qp.end()
        del qp

        dragObject = QtGui.QDrag(self)
        dragObject.setPixmap(pixmap)
        dragObject.setMimeData(mimeData)
        dragObject.setHotSpot(QtCore.QPoint(-20, -20))
        dragObject.exec_(QtCore.Qt.CopyAction|QtCore.Qt.MoveAction, QtCore.Qt.CopyAction)

    def showMenu(self, pos):
        self.parent().showMenu(self.tabAt(pos), self.mapToGlobal(pos))

    def mousePressEvent(self, event):
        DroppableTabBar.mousePressEvent(self, event)
        if self.isMovable():
            self.startX = event.x()
            self.startIndex = self.currentIndex()
            self.deltaX = self.startX - self.tabRect(self.startIndex).x()

    def mouseMoveEvent(self, event, internal=False):
        mapRect = self.rect()
        mapRect.setLeft(self.deltaX)
        mapRect.setRight(mapRect.right() - self.tabRect(self.count() - 1).width() + self.deltaX)
        if not self.isMovable():
            DroppableTabBar.mouseMoveEvent(self, event)
        elif not event.pos() in mapRect:
            pos = QtCore.QPoint(self.startX, 0)
            event = QtGui.QMouseEvent(event.type(), pos, QtCore.Qt.NoButton, QtCore.Qt.MouseButtons(QtCore.Qt.LeftButton), event.modifiers())
            DroppableTabBar.mouseMoveEvent(self, event)
            if self.window().dualMode and self.count() > 1 and not internal:
                self.startDrag()
        else:
            if self.isMovable() and self.startIndex != self.currentIndex():
                self.startX = self.tabRect(self.currentIndex()).x() + self.deltaX
                self.startIndex = self.currentIndex()
            DroppableTabBar.mouseMoveEvent(self, event)

    def mouseReleaseEvent(self, event):
        DroppableTabBar.mouseReleaseEvent(self, event)
        self.startIndex = None


class BaseTabWidget(QtWidgets.QTabWidget):
    newCollection = QtCore.pyqtSignal()
    openCollection = QtCore.pyqtSignal([str], [str, object], [str, object, int])
    exportRequested = QtCore.pyqtSignal(object, object)
    exportListRequested = QtCore.pyqtSignal(str)
    manageCollections = QtCore.pyqtSignal()
    tabMoveRequested = QtCore.pyqtSignal(int, object)
    panelSwapRequested = QtCore.pyqtSignal()
    toggleDualView = QtCore.pyqtSignal()
    minimizePanelRequested = QtCore.pyqtSignal()
    fullDumpCollectionToBlofeldRequested = QtCore.pyqtSignal(str, object)
    fullDumpBlofeldToCollectionRequested = QtCore.pyqtSignal(str, object)
    findDuplicatesRequested = QtCore.pyqtSignal(object, object)

    def __init__(self, *args, **kwargs):
        QtWidgets.QTabWidget.__init__(self, *args, **kwargs)
        self.main = QtWidgets.QApplication.instance()
        self.database = self.main.database
        self.referenceModel = self.database.referenceModel
        tabBar = LibraryTabBar(self)
        self.setTabBar(tabBar)
        self.placeHolder = tabBar.placeHolder
#        self.referenceModel = QtSql.QSqlTableModel()
        self.settings = QtCore.QSettings()
        self.menu = QtWidgets.QMenu(self)
        self.menu.setSeparatorsCollapsible(False)

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
        self.insertTab(-1, widget, name)

    def insertTab(self, index, widget, name):
        self.sideTabBar.insertTab(index, name)
        index = QtWidgets.QTabWidget.insertTab(self, index, widget, name)
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
        if widget.collection not in [None] + factoryPresetsNamesDict.keys():
            widget.fullDumpCollectionToBlofeldRequested.connect(self.fullDumpCollectionToBlofeldRequested)
            widget.fullDumpBlofeldToCollectionRequested.connect(self.fullDumpBlofeldToCollectionRequested)
        elif widget.collection in factoryPresetsNamesDict.keys():
            widget.fullDumpCollectionToBlofeldRequested.connect(self.fullDumpCollectionToBlofeldRequested)
        if not icon.isNull():
            self.setTabIcon(index, icon)
        #this is necessary at startup
        showClose = self.window().dualMode or self.count() > 1
        try:
            self.tabBar().tabButton(0, self.tabBar().RightSide).setVisible(showClose)
            side = self.tabBar().RightSide
        except:
            self.tabBar().tabButton(0, self.tabBar().LeftSide).setVisible(showClose)
            side = self.tabBar().LeftSide
        if self.count() > 1:
            self.setMovable(True)
        if self.window().dualMode and self.siblingTabWidget.count() == 1:
            self.siblingTabWidget.tabBar().tabButton(0, side).setVisible(True)
        return index

    def removeTab(self, index):
        self.sideTabBar.removeTab(index)
        widget = self.widget(index)
        QtWidgets.QTabWidget.removeTab(self, index)
        if self.count():
            showClose = self.window().dualMode or self.count() > 1
            try:
                self.tabBar().tabButton(0, self.tabBar().RightSide).setVisible(showClose)
            except:
                self.tabBar().tabButton(0, self.tabBar().LeftSide).setVisible(showClose)
        if self.count() <= 1:
            self.setMovable(False)
        return widget

    def setTabIcon(self, index, icon):
        QtWidgets.QTabWidget.setTabIcon(self, index, icon)
#        pixmap = icon.pixmap(self.sideTabBar.iconSize())
        size = self.sideTabBar.iconSize()
        pixmap = QtGui.QPixmap(size)
        pixmap.fill(QtCore.Qt.transparent)
        qp = QtGui.QPainter(pixmap)
        if self.side == Left:
            qp.rotate(90)
            qp.translate(0, -size.height())
        else:
            qp.rotate(-90)
            qp.translate(-size.height(), 0)
        qp.drawPixmap(pixmap.rect(), icon.pixmap(size))
        qp.end()
        self.sideTabBar.setTabIcon(index, QtGui.QIcon(pixmap))

    def showMenu(self, index, pos):
        self.menu.clear()
        collection = self.widget(index).collection
        if not collection:
            self.menu.addSection('Main Library')
        else:
            self.menu.addSection(factoryPresetsNamesDict.get(collection, collection))

        closeAction = self.menu.addAction(QtGui.QIcon.fromTheme('window-close'), 'Close collection')
        closeAction.triggered.connect(lambda: self.tabCloseRequested.emit(index))
        otherSide = 'right' if self.side == Left else 'left'
        if self.window().dualMode:
            tabSwapAction = self.menu.addAction(QtGui.QIcon.fromTheme('document-swap'), 'Swap panels')
            tabSwapAction.triggered.connect(self.panelSwapRequested)
            toggleDualViewAction = self.menu.addAction(QtGui.QIcon.fromTheme('view-right-close'), 'Switch to single panel view')
            toggleDualViewAction.triggered.connect(self.toggleDualView)
            if self.side == Right or self.count() > 1:
                moveTabAction = self.menu.addAction('Move to {} panel'.format(otherSide))
                moveTabAction.triggered.connect(lambda: self.tabMoveRequested.emit(index, self.siblingTabWidget))
                if self.side == Right and self.count() == 1:
                    toggleDualViewAction.setVisible(False)
                    moveTabAction.setIcon(QtGui.QIcon.fromTheme('view-right-close'))
                else:
                    moveTabAction.setIcon(QtGui.QIcon.fromTheme('arrow-{}'.format(otherSide)))
        else:
            if self.count() > 1:
                toggleDualViewAction = self.menu.addAction(QtGui.QIcon.fromTheme('view-split-left-right'), 'Move to right panel')
                toggleDualViewAction.triggered.connect(lambda: self.tabMoveRequested.emit(index, self.siblingTabWidget))
            else:
                closeAction.setEnabled(False)

        self.menu.addSeparator()
        if collection:
            dumpMenu = self.menu.addMenu(QtGui.QIcon(':/images/dump.svg'), 'Dump "{}"'.format(collection))
            dumpMenu.setSeparatorsCollapsible(False)
            if collection not in factoryPresetsNamesDict:
                dumpMenu.addSection('Receive')
                dumpFromAllAction = dumpMenu.addAction('Dump sounds FROM Blofeld')
                dumpFromAllAction.triggered.connect(lambda: self.fullDumpBlofeldToCollectionRequested.emit(collection, True))
#                dumpFromPromptAction = dumpMenu.addAction('Dump sounds FROM Blofeld...')
#                dumpFromPromptAction.triggered.connect(lambda: self.fullDumpBlofeldToCollectionRequested.emit(collection, False))
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
        self.menu.addMenu(self.getOpenCollectionMenu())
        self.menu.addSeparator()
        findDuplicatesAction = self.menu.addAction(QtGui.QIcon.fromTheme('edit-find'), 'Find duplicates...')
        findDuplicatesAction.triggered.connect(lambda: self.findDuplicatesRequested.emit(None, collection))
        self.menu.exec_(pos)

    def getOpenCollectionMenu(self):
        menu = QtWidgets.QMenu('Open collection', self)
        menu.setIcon(QtGui.QIcon.fromTheme('document-open'))
        menu.setSeparatorsCollapsible(False)
        menu.addSection('Custom collections')

        opened = self.collections + self.siblingTabWidget.collections
        self.settings.beginGroup('CollectionIcons')
        for collection in self.referenceModel.collections:
            action = menu.addAction('{} ({})'.format(
                factoryPresetsNamesDict.get(collection, collection), 
                self.database.getCountForCollection(collection)))
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

    def contextMenuEvent(self, event):
        menu = QtWidgets.QMenu(self)
        if self.window().dualMode:
            tabSwapAction = menu.addAction(QtGui.QIcon.fromTheme('document-swap'), 'Swap panels')
            tabSwapAction.triggered.connect(self.panelSwapRequested)
            iconName = 'arrow-left-double' if self.side == Left else 'arrow-right-double'
            hideAction = menu.addAction(QtGui.QIcon.fromTheme(iconName), 'Minimize panel')
            hideAction.triggered.connect(self.minimizePanelRequested)
            if self.window().panelLayout < 3:
                hideAction.setEnabled(False)
            menu.addSeparator()
            toggleDualViewAction = menu.addAction(QtGui.QIcon.fromTheme('view-right-close'), 'Switch to single panel view')
        else:
            toggleDualViewAction = menu.addAction(QtGui.QIcon.fromTheme('view-split-left-right'), 'Switch to dual panel view')
        toggleDualViewAction.triggered.connect(self.toggleDualView)
        menu.addMenu(self.getOpenCollectionMenu())
        menu.exec_(event.globalPos())

    def dragEnterEvent(self, event):
        self.dragSource = event.source()
        if event.mimeData().hasFormat('bigglesworth/collectionObject'):
            collection = QtCore.QDataStream(event.mimeData().data('bigglesworth/collectionObject')).readQVariant()
            if collection in self.collections:
                if event.source() == self.tabBar():
                    moveEvent = QtGui.QMouseEvent(QtCore.QEvent.MouseMove, event.pos(), QtCore.Qt.NoButton, event.mouseButtons(), event.keyboardModifiers())
                    self.tabBar().mouseMoveEvent(moveEvent, True)
                    event.accept()
                else:
                    self.setCurrentIndex(self.collections.index(collection))
                    event.ignore()
            elif not event.source() == self.siblingTabWidget.tabBar() and collection in self.siblingTabWidget.collections:
                self.siblingTabWidget.setCurrentIndex(self.siblingTabWidget.collections.index(collection))
                event.ignore()
            else:
                event.accept()

    def dragMoveEvent(self, event):
        #use the tabbar geometry adjusted to the tabwidget width
        tabRect = self.tabBar().geometry()
        tabRect.setLeft(0)
        tabRect.setWidth(self.width())
        if event.pos() in tabRect and event.mimeData().hasFormat('bigglesworth/collectionObject'):
            self.dropTabIndex = self.tabBar().setDropIndexAt(event.pos())
            if event.source() == self.tabBar():
                event.setDropAction(QtCore.Qt.MoveAction)
                moveEvent = QtGui.QMouseEvent(QtCore.QEvent.MouseMove, event.pos(), QtCore.Qt.NoButton, event.mouseButtons(), event.keyboardModifiers())
                self.tabBar().mouseMoveEvent(moveEvent, True)
            else:
                self.placeHolder.show()
            event.accept()
        else:
            self.placeHolder.hide()
            event.ignore()

    def dragLeaveEvent(self, event):
        if self.dragSource == self.tabBar():
            moveEvent = QtGui.QMouseEvent(
                QtCore.QEvent.MouseMove, self.mapFromGlobal(QtGui.QCursor.pos()), QtCore.Qt.NoButton, 
                QtCore.Qt.MouseButtons(QtCore.Qt.LeftButton), QtCore.Qt.KeyboardModifiers())
            self.tabBar().mouseMoveEvent(moveEvent, True)
        else:
            self.placeHolder.hide()

    def dropEvent(self, event):
        self.placeHolder.hide()
        collection = QtCore.QDataStream(event.mimeData().data('bigglesworth/collectionObject')).readQVariant()
        if collection in self.collections:
            pass
        elif collection in self.siblingTabWidget.collections:
            self.tabMoveRequested.emit(self.siblingTabWidget.collections.index(collection), self)
            self.tabBar().setCurrentIndex(self.currentIndex())
        else:
            self.openCollection[str, object, int].emit(collection, self, self.dropTabIndex)
        #create "fake" button release event to let qtabbar know we've finished
        source = event.source()
        if isinstance(source, QtWidgets.QTabBar):
            releaseEvent = QtGui.QMouseEvent(
                QtCore.QEvent.MouseMove, source.mapFromGlobal(QtGui.QCursor.pos()), QtCore.Qt.LeftButton, 
                QtCore.Qt.MouseButtons(), QtCore.Qt.KeyboardModifiers())
            source.mouseReleaseEvent(releaseEvent)
            source.update()
            #since there are some indexing and painting issues with this system,
            #ensure that the sibling tabbar and tabwidget are updated
            if source != self.tabBar():
                index = source.count() - 1
                source.setCurrentIndex(index)
                source.parent().setCurrentIndex(index)


class LeftTabWidget(BaseTabWidget):
    def __init__(self, *args, **kwargs):
        BaseTabWidget.__init__(self, *args, **kwargs)
        cornerWidget = TabCornerWidget(Left)
        cornerWidget.addBtn.clicked.connect(self.openCollectionMenu)
        cornerWidget.minimizeBtn.clicked.connect(self.minimizePanelRequested)
        self.minimizeBtn = cornerWidget.minimizeBtn
        self.setCornerWidget(cornerWidget, QtCore.Qt.TopRightCorner)
        self.side = Left


class RightTabWidget(BaseTabWidget):
    def __init__(self, *args, **kwargs):
        BaseTabWidget.__init__(self, *args, **kwargs)
        cornerWidget = TabCornerWidget(Right)
        cornerWidget.addBtn.clicked.connect(self.openCollectionMenu)
        cornerWidget.minimizeBtn.clicked.connect(self.minimizePanelRequested)
        self.minimizeBtn = cornerWidget.minimizeBtn
        self.setCornerWidget(cornerWidget, QtCore.Qt.TopRightCorner)
        self.side = Right


