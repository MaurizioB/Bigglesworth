from string import uppercase

from PyQt4 import QtCore, QtGui
import midifile

from const import *

class Sound(QtCore.QObject):
    bankChanged = QtCore.pyqtSignal(int)
    progChanged = QtCore.pyqtSignal(int)
    indexChanged = QtCore.pyqtSignal(int)
    nameChanged = QtCore.pyqtSignal(str)
    catChanged = QtCore.pyqtSignal(int)
    edited = QtCore.pyqtSignal(int)
    def __init__(self, data=None, source=SRC_LIBRARY):
        QtCore.QObject.__init__(self)
        self._bank = data[0]
        self._prog = data[1]
        self._data = data[2:]
        if data is not None:
            self._name = ''.join([str(unichr(l)) for l in self.data[363:379]]).strip()
            self._cat = self.data[379]
            self.source = source
            self._state = STORED|(source<<1)
        else:
            self._name = 'None'
            self._cat = None
            self.source = SRC_LIBRARY
            self._state = EMPTY

    def __getattr__(self, attr):
        try:
#            print sound_params[VALUE][self.data[params_index[attr]]]
#            print attr
            index = Params.index_from_attr(attr)
#            print self.data[index]
#            print sound_params[208][VALUE][self.data[index]]
#            return sound_params[index][VALUE][self.data[index]][0]
            return [self.data[index]][0]
        except Exception as Err:
            print Err
            print 'attr exception: {}'.format(attr)
            print '{}:{}, {}'.format(uppercase[self.bank], self.prog, self.name)
            return None

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, state):
#        print 'old state: {}\nnew state: {}'.format(self.state, state)
        self._state = self._state|state
        self.edited.emit(self._state)

    @property
    def bank(self):
        return self._bank

    @bank.setter
    def bank(self, bank):
        self._bank = bank
        self.bankChanged.emit(bank)
        self.indexChanged.emit(self.index)
        self.state = MOVED

    @property
    def prog(self):
        return self._prog

    @prog.setter
    def prog(self, prog):
        self._prog = prog
        self.progChanged.emit(prog)
        self.indexChanged.emit(self.index)
        self.state = MOVED

    @property
    def index(self):
        return self.prog + self.bank*128

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self._name = name
        self.nameChanged.emit(name)
        self.state = EDITED
        print 'changed name'

    @property
    def cat(self):
        return self._cat

    @cat.setter
    def cat(self, cat):
        self._cat = cat
        self.catChanged.emit(cat)
        self.state = EDITED

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, data):
        self._data = data


class CategoryDelegate(QtGui.QStyledItemDelegate):
    def __init__(self, parent=None):
        QtGui.QStyledItemDelegate.__init__(self, parent)
        self.commitData.connect(self.set_data)

    def createEditor(self, parent, option, index):
        self.table = parent.parent()
        self.index = index
        combo = QtGui.QComboBox(parent)
        model = QtGui.QStandardItemModel()
        [model.appendRow(QtGui.QStandardItem(cat)) for cat in categories]
        combo.setModel(model)
        combo.setCurrentIndex(index.data(CatRole).toPyObject())
        combo.activated.connect(lambda i: parent.setFocus())
        return combo

    def set_data(self, widget):
        self.index.model().sourceModel().sound(self.index).cat = widget.currentIndex()


class DumpWin(QtGui.QDialog):
    def __init__(self, parent=None):
        QtGui.QDialog.__init__(self, parent)
        self.setMinimumWidth(150)
        self.setWindowTitle('Sound dump request')
        grid = QtGui.QGridLayout(self)
        grid.addWidget(QtGui.QLabel('Dumping sounds...'), 0, 0, 1, 2)
        grid.addWidget(QtGui.QLabel('Bank: '), 1, 0, 1, 1)
        self.bank_lbl = QtGui.QLabel()
        grid.addWidget(self.bank_lbl, 1, 1, 1, 1)
        grid.addWidget(QtGui.QLabel('Sound: '), 2, 0, 1, 1)
        self.sound_lbl = QtGui.QLabel()
        grid.addWidget(self.sound_lbl, 2, 1, 1, 1)
        grid.addWidget(QtGui.QLabel('Remaining: '), 3, 0, 1, 1)
        self.time = QtGui.QLabel()
        grid.addWidget(self.time, 3, 1, 1, 1)
        self.progress = QtGui.QProgressBar()
        self.progress.setMaximum(128)
        grid.addWidget(self.progress, 4, 0, 1, 2)
        self.buttonBox = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Abort)
        self.buttonBox.button(QtGui.QDialogButtonBox.Abort).clicked.connect(self.reject)
        grid.addWidget(self.buttonBox, 5, 0, 1, 2)

    def show(self):
        self.bank_lbl.setText('')
        self.sound_lbl.setText('')
        self.time.setText('?')
        self.progress.setValue(0)
        QtGui.QDialog.show(self)


class Library(QtCore.QObject):
    def __init__(self, parent=None, banks=26):
        QtCore.QObject.__init__(self, parent)
#        self.data = [[Sound(b, p) for p in range(128)] for b in range(banks)]
        self.data = [[None for p in range(128)] for b in range(banks)]
        self.sound_index = {}
#        self.cat_count = {cat:[0 for b in banks] for c in categories}
        self.cat_count = [{c:0 for c in categories} for b in range(banks)]

    def setModel(self, model):
        self.model = model

    def sound(self, bank, prog):
        return self.data[bank][prog]

    def addSound(self, sound):
        bank = sound.bank
        prog = sound.prog
        self.data[bank][prog] = sound
        self.sound_index[sound] = bank, prog

        index_item = QtGui.QStandardItem('{}{:03}'.format(uppercase[bank], prog+1))
        index_item.setData(bank*128+prog, IndexRole)
        index_item.setEditable(False)
        bank_item = QtGui.QStandardItem(uppercase[bank])
        bank_item.setData(bank, UserRole)
        bank_item.setData(bank, BankRole)
        bank_item.setTextAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignCenter)
        bank_item.setEditable(False)
        prog_item = QtGui.QStandardItem('{:03}'.format(prog+1))
        prog_item.setData(prog, UserRole)
        prog_item.setData(prog, ProgRole)
        prog_item.setEditable(False)
        name_item = QtGui.QStandardItem(sound.name)
#        name_item.setData(sound.Amplifier_Envelope_Mode, QtCore.Qt.ToolTipRole)
        name_item.setData(sound.name, QtCore.Qt.ToolTipRole)
        cat_item = QtGui.QStandardItem(categories[sound.cat])
        cat_item.setData(sound.cat, UserRole)
        cat_item.setData(sound.cat, CatRole)
#        status_item = QtGui.QStandardItem('Dumped' if sound.state == DUMPED else 'Stored')
        status_item = QtGui.QStandardItem(status_dict[sound.state])
        status_item.setData(sound.state, EditedRole)
        status_item.setEditable(False)
        sound_item = QtGui.QStandardItem()
        sound_item.setData(sound, SoundRole)
#        sound.bankChanged.connect(lambda bank, item=bank_item: item.setData(bank, BankRole))
#        sound.progChanged.connect(lambda prog, item=prog_item: item.setData(prog, ProgRole))
        sound.indexChanged.connect(lambda index, item=index_item: item.setData(index, IndexRole))
        sound.catChanged.connect(lambda cat, bank=bank, item=cat_item: self.soundSetCategory(item, bank, cat))
        sound.edited.connect(lambda state, item=status_item: item.setData(state, EditedRole))

        found = self.model.findItems('{}{:03}'.format(uppercase[bank], prog+1), QtCore.Qt.MatchFixedString, 0)
        if found:
            self.model.takeRow(found[0].row())
        self.model.appendRow([index_item, bank_item, prog_item, name_item, cat_item, status_item, sound_item])
        self.model.sort(2)
        self.model.sort(1)


    def soundSetCategory(self, cat_item, bank, cat):
        cat_item.setData(cat, CatRole)
        

    def __getitem__(self, req):
        if not isinstance(req, tuple):
            req = divmod(req, 128)
        return self.data[req[0]][req[1]]


class LibraryModel(QtGui.QStandardItemModel):
    def __init__(self, parent=None):
        QtGui.QStandardItemModel.__init__(self, 0, 7, parent)

    def sound(self, index):
        return self.item(index.row(), 6).data(SoundRole).toPyObject()

class LibraryProxy(QtGui.QSortFilterProxyModel):
    def __init__(self, parent=None):
        QtGui.QSortFilterProxyModel.__init__(self, parent)
        self.filter_columns = {}
        self.text_filter = None

    def setTextFilter(self, text):
        if not text:
            self.text_filter = None
        else:
            self.text_filter = text.toLower()
        self.invalidateFilter()

    def setMultiFilter(self, column, index):
        if index == 0:
            self.filter_columns.pop(column)
        else:
            self.filter_columns[column] = index-1
        if not len(self.filter_columns) and not self.text_filter:
            self.reset()
            return
        self.invalidateFilter()

    def filterAcceptsRow(self, row, parent):
        if not len(self.filter_columns) and not self.text_filter:
            return True
        model = self.sourceModel()
        if len(self.filter_columns) and any([True for column, index in self.filter_columns.items() if model.item(row, column).data(UserRole) != index]):
            return False
        if not self.text_filter:
            return True
        if self.text_filter in model.item(row, NAME).text().toLower():
            return True
        return False

class LoadingThread(QtCore.QObject):
    loaded = QtCore.pyqtSignal(object, object)
    def __init__(self, parent):
        QtCore.QObject.__init__(self)
        self.blofeld_model = LibraryModel()
        self.blofeld_library = Library()
        self.blofeld_library.setModel(self.blofeld_model)

    def run(self):
        pattern = midifile.read_midifile('presets/blofeld_fact_080103/blofeld_fact_080103.mid')
        track = pattern[0]
        for event in track:
            if isinstance(event, midifile.SysexEvent):
                self.blofeld_library.addSound(Sound(event.data[6:391]))
        self.loaded.emit(self.blofeld_model, self.blofeld_library)

class LoadingWindow(QtGui.QDialog):
    def __init__(self, parent=None):
        self.main = parent
        QtGui.QDialog.__init__(self, parent)
        self.setWindowTitle('Presets loading...')
        grid = QtGui.QGridLayout(self)
        loading_lbl = QtGui.QLabel('Loading local presets, please wait')
        grid.addWidget(loading_lbl, 0, 0, 0, 0)
        self.loading = False
        self.loader = LoadingThread(self)
        self.loader_thread = QtCore.QThread()
        self.loader.moveToThread(self.loader_thread)
        self.loader_thread.started.connect(self.loader.run)
        self.loader.loaded.connect(self.set_models)
        self.loader.loaded.connect(self.main.set_models)

    def showEvent(self, event):
        if not self.loading:
            QtCore.QTimer.singleShot(100, self.loader_thread.start)
            self.loading = True

    def set_models(self, model, library):
        self.hide()

    def closeEvent(self, event):
        event.ignore()

