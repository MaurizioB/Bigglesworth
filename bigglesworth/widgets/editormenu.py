import re
from string import uppercase
import json

from Qt import QtCore, QtGui, QtWidgets

from bigglesworth.const import factoryPresetsNames, factoryPresetsNamesDict, UidColumn, LocationColumn, NameColumn, CatColumn, TagsColumn
from bigglesworth.parameters import categories
from bigglesworth.utils import setItalic, setBold

_mnemonics = re.compile('(?<!&)&(?!&)')

def escapeAmp(txt):
    return _mnemonics.sub(u'&&', txt)

class FactoryMenu(QtWidgets.QMenu):
    @QtCore.pyqtSlot(QtGui.QIcon, str)
    @QtCore.pyqtSlot(str)
    def addMenu(self, *args):
        menu = FactoryMenu(args[-1], self)
        if len(args) > 1:
            menu.setIcon(args[0])
        self.addAction(menu.menuAction())
        return menu

    def createSoundAction(self, menu, name, uid, location):
        name = escapeAmp(name.strip())
        action = menu.addAction(name)
        action.setData(uid)
        if location & 7:
            setItalic(action)
            for c, b in enumerate(range(location.bit_length() & 7)):
                if b:
                    break
            action.setStatusTip(u'"{}" is part of the preset "{}": changes will not be stored unless manually saved.'.format(
                name, 
                factoryPresetsNames[c]))
        elif location >> 3:
            location = (location | 7) ^ 7
            setBold(action)
            allCollections = self.referenceModel.allCollections
            collections = []
            for b in range(location.bit_length()):
                if location & (1 << b):
                    collections.append(allCollections[b])
            if len(collections) == 1:
                text = u'"{}" is part of the collection "{}"'.format(name, collections[0])
            else:
                text = u'"{}" is part of the following collections: '.format(name) + ', '.join(u'"{}"'.format(c) for c in collections)
            action.setStatusTip(text)
        else:
            action.setStatusTip(u'"{}" is not part of any collection'.format(name))
#            print(self.referenceModel.allCollections)

class SoundsMenu(FactoryMenu):
    def __init__(self, parent):
        FactoryMenu.__init__(self, '&Library', parent)
        self.settings = QtCore.QSettings()
        self.main = QtWidgets.QApplication.instance()
        self.database = self.main.database
        self.libraryModel = self.database.libraryModel
        self.libraryModel.dataChanged.connect(lambda: setattr(self, 'done', False))
        self.libraryModel.updated.connect(lambda: setattr(self, 'done', False))
        self.referenceModel = self.database.referenceModel
        self.tagsModel = self.database.tagsModel
        self.tagsModel.dataChanged.connect(lambda: setattr(self, 'done', False))

        self.locationsMenu = self.addMenu('By collection')
        self.locationsMenu.menuAction().setIcon(QtGui.QIcon.fromTheme('document-open'))
        self.locationsMenu.aboutToShow.connect(self.loadLocations)
        self.alphaMenu = self.addMenu('Alphabetical')
        self.alphaMenu.menuAction().setIcon(QtGui.QIcon.fromTheme('view-sort-ascending'))
        self.alphaMenu.aboutToShow.connect(self.loadAlpha)
        self.tagsMenu = self.addMenu('By tag')
        self.tagsMenu.menuAction().setIcon(QtGui.QIcon.fromTheme('tag'))
        self.tagsMenu.aboutToShow.connect(self.loadTags)
        self.catsMenu = self.addMenu('By category')
        self.catsMenu.menuAction().setIcon(QtGui.QIcon.fromTheme('bookmarks'))
        self.catsMenu.aboutToShow.connect(self.loadCats)
        self.addSeparator()
        self.initNewAction = self.addAction(QtGui.QIcon.fromTheme('document-new'), 'New INIT sound')
        self.initNewAction.triggered.connect(self.parent().window().initNew)
        self.initCurrentAction = self.addAction(QtGui.QIcon.fromTheme('document-new-from-template'), 're-INIT the current sound')
        self.initCurrentAction.triggered.connect(self.parent().window().initCurrent)

        self.lastShownTimer = QtCore.QElapsedTimer()
        self.lastShownTimer.start()
        self.aboutToShow.connect(self.checkAge)
        self.aboutToHide.connect(self.startShownTimer)
        self.openLibrarianAction = None
        self.done = False

    def checkAge(self):
#        if isinstance(self.parent(), QtWidgets.QMenuBar) and not self.openLibrarianAction:
#            first = self.actions()[0]
#            #old icon: view-list-details
#            self.openLibrarianAction = QtWidgets.QAction(QtGui.QIcon.fromTheme('tab-duplicate'), 'Open &librarian', self)
##            self.openLibrarianAction.setShortcut(QtGui.QKeySequence('Ctrl+Alt+L'))
#            self.openLibrarianAction.triggered.connect(self.parent().window().openLibrarianRequested)
#            self.insertAction(first, self.openLibrarianAction)
#            self.importAction = QtWidgets.QAction(QtGui.QIcon.fromTheme('document-open'), '&Import sound', self)
#            self.importAction.triggered.connect(lambda: self.parent().importRequested.emit())
#            self.insertAction(first, self.importAction)
#            self.insertSeparator(first).setText('Open sound')
        if not self.done or self.lastShownTimer.hasExpired(10000):
            self.populate()
        self.tagsMenu.setEnabled(True if self.tags else False)
        self.done = True

    def startShownTimer(self):
        self.lastShownTimer.start()

    def populate(self):
        self.referenceModel.refresh()
        self.libraryModel.query().exec_()
        self.locationsDone = self.alphaDone = self.tagsDone = self.catsDone = False
        self.locationsMenu.clear()
        self.alphaMenu.clear()
        self.tagsMenu.clear()
        self.catsMenu.clear()
        self.tags = {}
        self.collections = self.referenceModel.allCollections
        self.locations = {l:[] for l in range(len(self.collections))}

        self.alpha = {
            'A': [], 'B': [], 'C': [], 'D': [], 'E': [], 'F': [], 
            'G': [], 'H': [], 'I': [], 'J': [], 'K': [], 'L': [], 
            'M': [], 'N': [], 'O': [], 'P': [], 'Q': [], 'R': [], 
            'S': [], 'T': [], 'U': [], 'V': [], 'W': [], 'X': [], 
            'Y': [], 'Z': [], '0..9..': []}
        self.cats = {c: [] for c in range(13)}

        for row in range(self.libraryModel.rowCount()):
            uid = self.libraryModel.index(row, UidColumn).data()
            name = self.libraryModel.index(row, NameColumn).data()
            location = self.libraryModel.index(row, LocationColumn).data()
            cat = self.libraryModel.index(row, CatColumn).data()
            soundTags = json.loads(self.libraryModel.index(row, TagsColumn).data())

            dataTuple = name, uid, location
            try:
                self.alpha[name[0].upper()].append(dataTuple)
            except:
                self.alpha['0..9..'].append(dataTuple)
            for tag in soundTags:
                try:
                    self.tags[tag].append(dataTuple)
                except:
                    self.tags[tag] = [dataTuple]
            self.cats[cat].append(dataTuple)
            
            if not isinstance(location, int):
                return
            for b in range(location.bit_length()):
                if location >> b & 1:
                    loc = self.referenceModel.index(row, 2 + b).data()
                    if isinstance(loc, (int, long)):
                        self.locations[b].append((loc, name, uid))
        print('qui', self.referenceModel.index(0, 0).data(QtCore.Qt.DisplayRole), self.referenceModel.index(3330, 5).data())

    def getCollectionMenu(self, collection):
        if not self.done:
            self.populate()
        if not self.locationsDone:
            self.loadLocations()
        return self.collectionMenus.get(collection, None)

    def loadLocations(self):
        if self.locationsDone:
            return
        self.locationsDone = True
        self.collectionMenus = {}
        self.settings.beginGroup('CollectionIcons')
        for c, collection in enumerate(self.collections):
            if collection in factoryPresetsNamesDict:
                icon = QtGui.QIcon('factory')
            elif collection == 'Blofeld':
                icon = QtGui.QIcon('blofeld-b')
            else:
                icon = QtGui.QIcon.fromTheme(self.settings.value(collection))
            colMenu = self.locationsMenu.addMenu(icon, '')
            self.collectionMenus[collection] = colMenu
            colMenu.menuAction().setData(collection)
            content = self.locations[c]
            title = factoryPresetsNamesDict.get(collection, collection)
            if not content:
                colMenu.setTitle(title + ' (empty)')
                colMenu.setEnabled(False)
                continue
            colMenu.setTitle(u'{} ({})'.format(title, len(content)))
            if len(content) <= 128:
                for locId, name, uid in sorted(content):
                    bank = uppercase[locId >> 7]
                    prog = (locId & 127) + 1
                    soundAction = colMenu.addAction(u'{}{:03} {}'.format(bank, prog, name))
                    soundAction.setData(uid)
                    if c <= 2:
                        setItalic(soundAction)
                continue
            alphaSet = {}
            for locId, name, uid in sorted(content):
                bank = uppercase[locId >> 7]
                prog = (locId & 127) + 1
                try:
                    alphaMenu = alphaSet[bank]
                except:
                    alphaMenu = alphaSet.setdefault(bank, colMenu.addMenu('Bank ' + bank))
                soundAction = alphaMenu.addAction(u'{:03} {}'.format(prog, name))
                soundAction.setData(uid)
                if c <= 2:
                    setItalic(soundAction)
        self.settings.endGroup()

    def getCommonLetters(self, a, b):
        text = u''
        for la, lb in zip(a, b):
            text += la
            if la != lb:
                break
        return text

    def createSubMenu(self, mainMenu, refDict, subLevel=False, titleKey=None):
        for mainKey, content in sorted(refDict.items()):
            if titleKey:
                title = titleKey[mainKey]
            else:
                title = mainKey
            menuIcon = QtGui.QIcon()
            if mainMenu == self.tagsMenu:
                menuIcon = self.getTagIcon(mainKey)
            if not content:
                subMenu = mainMenu.addMenu(menuIcon, title + u'empty)')
                subMenu.setEnabled(False)
                continue
            if len(content) < 64:
                subMenu = mainMenu.addMenu(menuIcon, '')
                subMenu.setTitle(u'{} ({})'.format(title, len(content)))
                for name, uid, location in sorted(content, key=lambda _: _[0].lower()):
                    self.createSoundAction(subMenu, name, uid, location)
                continue
            if subLevel:
                parentMenu = mainMenu.addMenu(u'{} ({})'.format(title, len(content)))
            else:
                parentMenu = mainMenu
            division = len(content) / 64.
            if division != int(division):
                division = int(division) + 1
                multi = len(content) / division + 1
            else:
                division = int(division)
                multi = len(content) / division
            content = sorted(content, key=lambda _: _[0].lower())
            prevMenu = lastName = None
            prevFirstName = escapeAmp(content[0][0][0])
            lastCount = 0
            for pos in range(division):
                first = multi * pos
                last = multi * (pos + 1)
                firstName = content[first][0]
                if prevMenu:
                    titleLast = self.getCommonLetters(lastName, firstName)
                    titleFirst = prevFirstName[:len(titleLast)]
                    if pos == 1:
                        titleFirst = titleFirst[:2]
                    prevMenu.setTitle(u'{}..{} ({})'.format(escapeAmp(titleFirst), escapeAmp(titleLast), lastCount))
                subAlphaMenu = parentMenu.addMenu('')
                subContent = content[first:last]
                for name, uid, location in subContent:
                    self.createSoundAction(subAlphaMenu, name, uid, location)
                prevMenu = subAlphaMenu
                prevFirstName = firstName
                lastName = name
                lastCount = len(subContent)
            subAlphaMenu.setTitle(u'{}..{} ({})'.format(
                escapeAmp(firstName[:len(titleLast)]), 
                escapeAmp(self.getCommonLetters(lastName, titleLast)), 
                lastCount
                ))

    def getTagIcon(self, tag):
        colors = self.main.database.getTagColors(tag)
        if not colors:
            return QtGui.QIcon()
        bgd, fgd = colors
        option = QtWidgets.QStyleOptionMenuItem()
        option.initFrom(self)
        iconSize = self.style().pixelMetric(QtWidgets.QStyle.PM_SmallIconSize, option, self)
        icon = QtGui.QPixmap(iconSize, iconSize)
        icon.fill(QtCore.Qt.transparent)
        qp = QtGui.QPainter(icon)
        qp.setRenderHints(qp.Antialiasing)
        qp.setPen(QtGui.QPen(bgd, iconSize * .25))
        qp.setBrush(fgd)
#            qp.translate(.5, .5)
        deltaPos = iconSize * .125
        qp.drawRoundedRect(deltaPos, deltaPos, iconSize - deltaPos * 2 - 1, iconSize - deltaPos * 2 - 1, deltaPos * .5, deltaPos * .5)
        qp.end()
        return QtGui.QIcon(icon)

    def loadAlpha(self):
        if self.alphaDone:
            return
        self.alphaDone = True
        self.createSubMenu(self.alphaMenu, self.alpha)

    def loadTags(self):
        if self.tagsDone:
            return
        self.tagsDone = True
        self.createSubMenu(self.tagsMenu, self.tags, True)

    def loadCats(self):
        if self.catsDone:
            return
        self.catsDone = True
        self.createSubMenu(self.catsMenu, self.cats, True, categories)


class EditorMenu(QtWidgets.QMenuBar):
    openSoundRequested = QtCore.pyqtSignal(object)
    importRequested = QtCore.pyqtSignal()
    exportRequested = QtCore.pyqtSignal()

    def __init__(self, parent):
        QtWidgets.QMenuBar.__init__(self, parent)
        self.editorWindow = parent
        self.main = parent.main
        self.referenceModel = parent.referenceModel
        self.libraryModel = parent.libraryModel

#        fileMenu = self.addMenu('&File')
#        importAction = fileMenu.addAction('Import sound...')
#        importAction.triggered.connect(self.importRequested)

        #Due to the menu section hack for MacOS, menus have to be 
        #manually created, otherwise PyQt will complain about unaccessible 
        #objects when they're not created from python

        self.fileMenu = QtWidgets.QMenu('&File', self)
        self.addMenu(self.fileMenu)
        self.importAction = self.fileMenu.addAction(QtGui.QIcon.fromTheme('document-open'), 'Import sound...')
        self.importAction.setShortcut(QtGui.QKeySequence('Ctrl+O'))
        self.importAction.triggered.connect(self.importRequested.emit)
        self.exportAction = self.fileMenu.addAction(QtGui.QIcon.fromTheme('document-save'), 'Export current sound...')
        self.exportAction.setShortcut(QtGui.QKeySequence('Ctrl+E'))
        self.exportAction.triggered.connect(self.exportRequested.emit)
        self.fileMenu.addSeparator()
        self.quitAction = self.fileMenu.addAction(QtGui.QIcon.fromTheme('application-exit'), '&Quit Bigglesworth :-(')
        self.quitAction.setShortcut(QtGui.QKeySequence('Ctrl+Q'))

        self.libraryMenu = SoundsMenu(self)
        self.libraryMenu.triggered.connect(self.openSoundTriggered)
        self.addMenu(self.libraryMenu)

        self.addMenu(self.main.getWindowsMenu(parent, self))

        self.addMenu(self.main.getAboutMenu(parent, self))

    def openSoundTriggered(self, action):
        if action.data():
            self.openSoundRequested.emit(action)


