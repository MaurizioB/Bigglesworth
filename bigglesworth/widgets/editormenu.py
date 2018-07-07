import re
from string import uppercase
import json

from Qt import QtCore, QtGui, QtWidgets

from bigglesworth.const import factoryPresetsNames, factoryPresetsNamesDict, UidColumn, LocationColumn, NameColumn, CatColumn, TagsColumn
from bigglesworth.parameters import categories
from bigglesworth.utils import setItalic, setBold
from bigglesworth.dialogs import LocationRequestDialog, WarningMessageBox

_mnemonics = re.compile('(?<!&)&(?!&)')

def escapeAmp(txt):
    return _mnemonics.sub('&&', txt)

class FactoryMenu(QtWidgets.QMenu):
    @QtCore.pyqtSlot(str)
    def addMenu(self, title):
        menu = FactoryMenu(title, self)
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
            action.setStatusTip('"{}" is part of the preset "{}": changes will not be stored unless manually saved.'.format(
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
                text = '"{}" is part of the collection "{}"'.format(name, collections[0])
            else:
                text = '"{}" is part of the following collections: '.format(name) + ', '.join('"{}"'.format(c) for c in collections)
            action.setStatusTip(text)
        else:
            action.setStatusTip('"{}" is not part of any collection'.format(name))
#            print(self.referenceModel.allCollections)

class SoundsMenu(FactoryMenu):
    def __init__(self, parent):
        FactoryMenu.__init__(self, '&Library', parent)
        self.libraryModel = parent.libraryModel
        self.referenceModel = parent.referenceModel
        self.locationsMenu = self.addMenu('By collection')
        self.locationsMenu.aboutToShow.connect(self.loadLocations)
        self.alphaMenu = self.addMenu('Alphabetical')
        self.alphaMenu.aboutToShow.connect(self.loadAlpha)
        self.tagsMenu = self.addMenu('By tag')
        self.tagsMenu.aboutToShow.connect(self.loadTags)
        self.catsMenu = self.addMenu('By category')
        self.catsMenu.aboutToShow.connect(self.loadCats)
        self.addSeparator()
        self.initNewAction = self.addAction('New INIT sound')
        self.initNewAction.triggered.connect(self.parent().window().initNew)
        self.initCurrentAction = self.addAction('re-INIT the current sound')
        self.initCurrentAction.triggered.connect(self.parent().window().initCurrent)

        self.lastShownTimer = QtCore.QElapsedTimer()
        self.lastShownTimer.start()
        self.aboutToShow.connect(self.checkAge)
        self.aboutToHide.connect(self.startShownTimer)
        self.openLibrarianAction = None
        self.done = False

    def checkAge(self):
        if isinstance(self.parent(), QtWidgets.QMenuBar) and not self.openLibrarianAction:
            first = self.actions()[0]
            self.openLibrarianAction = QtWidgets.QAction('Open &librarian', self)
#            self.openLibrarianAction.setShortcut(QtGui.QKeySequence('Ctrl+Alt+L'))
            self.openLibrarianAction.triggered.connect(self.parent().window().openLibrarianRequested)
            self.insertAction(first, self.openLibrarianAction)
            self.importAction = QtWidgets.QAction('&Import sound', self)
            self.importAction.triggered.connect(lambda: self.parent().importRequested.emit())
            self.insertAction(first, self.importAction)
            self.insertSeparator(first)
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
        for c, collection in enumerate(self.collections):
            colMenu = self.locationsMenu.addMenu('')
            self.collectionMenus[collection] = colMenu
            colMenu.menuAction().setData(collection)
            content = self.locations[c]
            title = factoryPresetsNamesDict.get(collection, collection)
            if not content:
                colMenu.setTitle(title + ' (empty)')
                colMenu.setEnabled(False)
                continue
            colMenu.setTitle('{} ({})'.format(title, len(content)))
            if len(content) <= 128:
                for locId, name, uid in sorted(content):
                    bank = uppercase[locId >> 7]
                    prog = (locId & 127) + 1
                    soundAction = colMenu.addAction('{}{:03} {}'.format(bank, prog, name))
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
                soundAction = alphaMenu.addAction('{:03} {}'.format(prog, name))
                soundAction.setData(uid)
                if c <= 2:
                    setItalic(soundAction)

    def getCommonLetters(self, a, b):
        text = ''
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
            if not content:
                subMenu = mainMenu.addMenu(title + ('empty)'))
                subMenu.setEnabled(False)
                continue
            if len(content) < 64:
                subMenu = mainMenu.addMenu('')
                subMenu.setTitle('{} ({})'.format(title, len(content)))
                for name, uid, location in sorted(content, key=lambda _: _[0].lower()):
                    self.createSoundAction(subMenu, name, uid, location)
                continue
            if subLevel:
                parentMenu = mainMenu.addMenu('{} ({})'.format(title, len(content)))
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
                    prevMenu.setTitle('{}..{} ({})'.format(escapeAmp(titleFirst), escapeAmp(titleLast), lastCount))
                subAlphaMenu = parentMenu.addMenu('')
                subContent = content[first:last]
                for name, uid, location in subContent:
                    self.createSoundAction(subAlphaMenu, name, uid, location)
                prevMenu = subAlphaMenu
                prevFirstName = firstName
                lastName = name
                lastCount = len(subContent)
            subAlphaMenu.setTitle('{}..{} ({})'.format(
                escapeAmp(firstName[:len(titleLast)]), 
                escapeAmp(self.getCommonLetters(lastName, titleLast)), 
                lastCount
                ))

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
    #blofeld index/buffer, collection, index, multi
    dumpFromRequested = QtCore.pyqtSignal(object, object, object, bool)
    #uid, blofeld index/buffer, multi
    dumpToRequested = QtCore.pyqtSignal(object, object, bool)
    randomAllRequest = QtCore.pyqtSignal()
    randomCustomRequest = QtCore.pyqtSignal()

    def __init__(self, parent):
        QtWidgets.QMenuBar.__init__(self, parent)
        self.editorWindow = parent
        self.main = parent.main
        self.referenceModel = parent.referenceModel
        self.libraryModel = parent.libraryModel

#        fileMenu = self.addMenu('&File')
#        importAction = fileMenu.addAction('Import sound...')
#        importAction.triggered.connect(self.importRequested)

        self.libraryMenu = SoundsMenu(self)
        self.libraryMenu.triggered.connect(self.openSoundTriggered)
        self.addMenu(self.libraryMenu)
#        self.openLibrarianAction = self.libraryMenu.openLibrarianAction
#        self.addAction(self.openLibrarianAction)

        self.dumpMenu = self.addMenu('&Dump')
        self.dumpMenu.aboutToShow.connect(self.updatedumpMenu)
        self.dumpMenu.setSeparatorsCollapsible(False)
        self.dumpMenu.addSection('Receive')
        self.dumpFromSoundEditAction = self.dumpMenu.addAction('Request from Sound Edit buffer')
        self.dumpFromSoundEditAction.triggered.connect(lambda: self.dumpFromRequested.emit(None, None, None, False))
        self.dumpFromCurrentIndexAction = self.dumpMenu.addAction('')
        self.dumpFromCurrentIndexAction.triggered.connect(self.dumpFromCurrentRequestCheck)
        self.dumpFromAskIndexAction = self.dumpMenu.addAction('Request from location...')
        self.dumpFromAskIndexAction.triggered.connect(self.dumpFromAsk)
        self.dumpFromMultiMenu = self.dumpMenu.addMenu('Multi')
        dumpFromMultiAction = self.dumpFromMultiMenu.addAction('Request all Multi parts')
        dumpFromMultiAction.setEnabled(False)

        self.dumpMenu.addSection('Send')
        self.dumpToSoundEditAction = self.dumpMenu.addAction('Send to Blofeld Sound Edit Buffer')
        self.dumpToSoundEditAction.triggered.connect(lambda: self.dumpToRequested.emit(None, None, False))
        self.dumpToCurrentIndexAction = self.dumpMenu.addAction('')
        self.dumpToAskIndexAction = self.dumpMenu.addAction('Send to Blofeld at location...')
        self.dumpToAskIndexAction.triggered.connect(self.dumpToAsk)
        self.dumpToMultiMenu = self.dumpMenu.addMenu('Multi')
        dumpToMultiAction = self.dumpToMultiMenu.addAction('Send all Multi parts')
        dumpToMultiAction.setEnabled(False)

        for part in range(16):
            dumpFromMultiPartAction = self.dumpFromMultiMenu.addAction('Part {}'.format(part + 1))
            dumpFromMultiPartAction.triggered.connect(lambda part=part: self.dumpFromRequested.emit(part, None, None, True))
            dumpToMultiPartAction = self.dumpToMultiMenu.addAction('Part {}'.format(part + 1))
            dumpToMultiPartAction.triggered.connect(lambda part=part: self.dumpToRequested.emit(None, part, True))

        randomMenu = self.addMenu('&Randomize')
        randomAllAction = randomMenu.addAction('Randomize &all parameters')
        randomAllAction.triggered.connect(self.randomAllRequest)
        randomCustomAction = randomMenu.addAction('Custom randomize...')
        randomCustomAction.triggered.connect(self.randomCustomRequest)

    def updatedumpMenu(self):
        inConn, outConn = map(any, self.main.connections)

        self.dumpFromSoundEditAction.setEnabled(inConn)
        self.dumpFromCurrentIndexAction.setEnabled(inConn)
        self.dumpFromAskIndexAction.setEnabled(inConn)
        self.dumpFromMultiMenu.setEnabled(inConn)

        self.dumpToSoundEditAction.setEnabled(outConn)
        self.dumpToCurrentIndexAction.setEnabled(outConn)
        self.dumpToAskIndexAction.setEnabled(outConn)
        self.dumpToMultiMenu.setEnabled(outConn)
        try:
            self.dumpToCurrentIndexAction.triggered.disconnect()
        except:
            pass
        if self.editorWindow.currentBank is not None and self.editorWindow.currentProg is not None:
            location = '{}{:03}'.format(
                uppercase[self.editorWindow.currentBank], 
                self.editorWindow.currentProg + 1)
            self.dumpFromCurrentIndexAction.setText('Request from current location ({})'.format(location))
            self.dumpFromCurrentIndexAction.setVisible(True)

            self.dumpToCurrentIndexAction.setText('Send to Blofeld at current location({}'.format(location))
            index = (self.editorWindow.currentBank << 7) + self.editorWindow.currentProg
            self.dumpToCurrentIndexAction.triggered.connect(lambda: self.dumpToRequested.emit(None, index, False))
            self.dumpToCurrentIndexAction.setVisible(True)
        else:
            self.dumpFromCurrentIndexAction.setVisible(False)
            self.dumpToCurrentIndexAction.setVisible(False)

    def dumpFromCurrentRequestCheck(self):
        detailed = 'Bigglesworth uses a database that stores all sounds, some of which are shared amongst collections; ' \
            'if a shared sound is changed, its changes will reflect on all collections containing it.<br/>' \
            'If you want to keep the existing sound, press {}, otherwise by choosing "Overwrite" it will be lost. Forever.'

        if self.editorWindow._editStatus == self.editorWindow.Modified or self.editorWindow.setFromDump:
            if self.editorWindow._editStatus == self.editorWindow.Modified:
                title = 'Sound modified'
                message = 'The current sound has been modified\nWhat do you want to do?'
            else:
                title = 'Sound dumped'
                message = 'The current sound has been dumped from the Blofeld\nWhat do you want to do?'
                detailed = ''
            buttons = {QtWidgets.QMessageBox.Save: 'Save and proceed', 
                QtWidgets.QMessageBox.Discard: (QtGui.QIcon.fromTheme('document-save'), 'Overwrite'), 
                QtWidgets.QMessageBox.Ignore: None, QtWidgets.QMessageBox.Cancel: None}
            altText = '"Save and proceed" or "Ignore"'
        else:
            title = 'Sound stored in library'
            message = 'The current sound is stored in the library\nWhat do you want to do?'
            buttons = {QtWidgets.QMessageBox.Discard: (QtGui.QIcon.fromTheme('document-save'), 'Overwrite'), 
                QtWidgets.QMessageBox.Ignore: None, QtWidgets.QMessageBox.Cancel: None}
            altText = '"Ignore"'
        res = WarningMessageBox(self, title, message, detailed.format(altText), buttons).exec_()
        if not res or res == QtWidgets.QMessageBox.Cancel:
            return
        blofeldIndex = (self.editorWindow.currentBank << 7) + self.editorWindow.currentProg
        if res == QtWidgets.QMessageBox.Save:
            if not self.editorWindow.save():
                return
        if res == QtWidgets.QMessageBox.Discard:
            collection = self.editorWindow.currentCollection
            target = blofeldIndex
        else:
            collection = None
            target = None
        self.dumpFromRequested.emit(blofeldIndex, collection, target, False)

    def dumpFromAsk(self):
        if self.editorWindow._editStatus == self.editorWindow.Modified or self.editorWindow.setFromDump:
            if self.editorWindow._editStatus == self.editorWindow.Modified:
                title = 'Sound modified'
                message = 'The current sound has been modified\nWhat do you want to do?'
            else:
                title = 'Sound dumped'
                message = 'The current sound has been dumped from the Blofeld\nWhat do you want to do?'
            res = QtWidgets.QMessageBox.question(self, title, message, 
                buttons=QtWidgets.QMessageBox.Save|QtWidgets.QMessageBox.Ignore|QtWidgets.QMessageBox.Cancel)
            if res == QtWidgets.QMessageBox.Cancel:
                return
            elif res == QtWidgets.QMessageBox.Save:
                if not self.editorWindow.save():
                    return
        bank, prog = LocationRequestDialog(self.editorWindow, self.editorWindow.currentBank, self.editorWindow.currentProg).exec_()
        if bank is None:
            return
        blofeldIndex = (bank << 7) + prog
        self.dumpFromRequested.emit(blofeldIndex, None, None, False)

    def dumpToAsk(self):
        bank, prog = LocationRequestDialog(self.editorWindow, self.editorWindow.currentBank, self.editorWindow.currentProg).exec_()
        if bank is None:
            return
        blofeldIndex = (bank << 7) + prog
        self.dumpToRequested.emit(None, blofeldIndex, False)

    def openSoundTriggered(self, action):
        if action.data():
            self.openSoundRequested.emit(action)


