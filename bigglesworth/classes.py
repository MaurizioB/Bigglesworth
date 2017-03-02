from string import uppercase, ascii_letters
from collections import namedtuple
from bisect import bisect_left

from PyQt4 import QtCore, QtGui

import midifile

from midiutils import SysExEvent
from const import *
from utils import load_ui

class DirCursorClass(QtGui.QCursor):
    limit_pen = QtGui.QPen(QtCore.Qt.black, 2)
    limit_pen.setCapStyle(QtCore.Qt.RoundCap)
    arrow_pen = QtGui.QPen(QtCore.Qt.black, 1)
    arrow_pen.setCapStyle(QtCore.Qt.RoundCap)
    brush = QtGui.QBrush(QtCore.Qt.black)

class UpCursorClass(DirCursorClass):
    def __init__(self):
        pixmap = QtGui.QPixmap(32, 32)
        pixmap.fill(QtCore.Qt.transparent)
        qp = QtGui.QPainter(pixmap)
        qp.setRenderHints(QtGui.QPainter.Antialiasing)
        qp.translate(.5, .5)
        qp.setPen(self.limit_pen)
        qp.drawLine(0, 1, 15, 1)
        qp.setPen(self.arrow_pen)
        qp.setBrush(self.brush)
        path = QtGui.QPainterPath()
        path.moveTo(7.5, 1)
        path.lineTo(12, 8)
        path.lineTo(3, 8)
        path.closeSubpath()
        qp.drawPath(path)
        del qp
        DirCursorClass.__init__(self, pixmap, 8, 1)

class DownCursorClass(DirCursorClass):
    def __init__(self):
        pixmap = QtGui.QPixmap(32, 32)
        pixmap.fill(QtCore.Qt.transparent)
        qp = QtGui.QPainter(pixmap)
        qp.setRenderHints(QtGui.QPainter.Antialiasing)
        qp.translate(.5, .5)
        qp.setPen(self.limit_pen)
        qp.drawLine(0, 8, 15, 8)
        qp.setPen(self.arrow_pen)
        qp.setBrush(self.brush)
        path = QtGui.QPainterPath()
        path.moveTo(3, 1)
        path.lineTo(12, 1)
        path.lineTo(7.5, 7)
        path.closeSubpath()
        qp.drawPath(path)
        del qp
        DirCursorClass.__init__(self, pixmap, 8, 8)

class LeftCursorClass(DirCursorClass):
    def __init__(self):
        pixmap = QtGui.QPixmap(32, 32)
        pixmap.fill(QtCore.Qt.transparent)
        qp = QtGui.QPainter(pixmap)
        qp.setRenderHints(QtGui.QPainter.Antialiasing)
        qp.translate(.5, .5)
        qp.setPen(self.limit_pen)
        qp.drawLine(1, 0, 1, 15)
        qp.setPen(self.arrow_pen)
        qp.setBrush(self.brush)
        path = QtGui.QPainterPath()
        path.moveTo(1, 7.5)
        path.lineTo(8, 12)
        path.lineTo(8, 3)
        path.closeSubpath()
        qp.drawPath(path)
        del qp
        DirCursorClass.__init__(self, pixmap, 1, 8)

class RightCursorClass(DirCursorClass):
    def __init__(self):
        pixmap = QtGui.QPixmap(32, 32)
        pixmap.fill(QtCore.Qt.transparent)
        qp = QtGui.QPainter(pixmap)
        qp.setRenderHints(QtGui.QPainter.Antialiasing)
        qp.translate(.5, .5)
        qp.setPen(self.limit_pen)
        qp.drawLine(8, 0, 8, 15)
        qp.setPen(self.arrow_pen)
        qp.setBrush(self.brush)
        path = QtGui.QPainterPath()
        path.moveTo(1, 3)
        path.lineTo(1, 12)
        path.lineTo(7, 7.5)
        path.closeSubpath()
        qp.drawPath(path)
        del qp
        DirCursorClass.__init__(self, pixmap, 8, 8)

class Sound(QtCore.QObject):
    bankChanged = QtCore.pyqtSignal(int)
    progChanged = QtCore.pyqtSignal(int)
    indexChanged = QtCore.pyqtSignal(int)
    nameChanged = QtCore.pyqtSignal(str)
    catChanged = QtCore.pyqtSignal(int)
    edited = QtCore.pyqtSignal(int)
    def __init__(self, data=None, source=SRC_LIBRARY):
        QtCore.QObject.__init__(self)
        if data is not None:
            self._bank = data[0]
            self._prog = data[1]
            self._data = data[2:]
            self._name = ''.join([str(unichr(l)) for l in self.data[363:379]]).strip()
            self._cat = self.data[379]
            self.source = source
            self._state = STORED|(source<<1)
        else:
            self._bank = self._prog = 0
            self._data = []
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
        pattern = midifile.read_midifile(local_path('presets/blofeld_fact_080103/blofeld_fact_080103.mid'))
        track = pattern[0]
        _ = 0
        for event in track:
            if isinstance(event, midifile.SysexEvent):
                self.blofeld_library.addSound(Sound(event.data[6:391]))
                _ += 1
#                if _ == 208: break
        self.loaded.emit(self.blofeld_model, self.blofeld_library)

class LoadingWindow(QtGui.QDialog):
    def __init__(self, parent=None):
        self.main = parent
        QtGui.QDialog.__init__(self, parent)
        self.setWindowTitle('Presets loading...')
        self.setModal(True)
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

class PopupSpin(QtGui.QDoubleSpinBox):
    indexChanged = QtCore.pyqtSignal(int)
    def __init__(self, parent):
        self.indexMinimum = 1
        self.indexMaximum = len(popup_values) - 1
        self.indexRange = self.indexMinimum, self.indexMaximum
        QtGui.QDoubleSpinBox.__init__(self, parent)
        self.setRange(.1, 15.5)
        self.setSuffix('s')
        self.setDecimals(1)
        self.setSingleStep(.1)
        self.index = 0
        self.setIndex(1)

    def stepBy(self, steps):
        new_index = self.index + steps
        if new_index > self.indexMaximum:
            new_index = self.indexMaximum
        elif new_index < self.indexMinimum:
            new_index = self.indexMinimum
        self.setIndex(new_index)

    def setIndex(self, index):
        if not self.indexMinimum <= index <= self.indexMaximum: return
        self.index = index
        self.indexChanged.emit(index)
        self.setValue(popup_values[index])

    def validate(self, text, pos):
        res = QtGui.QDoubleSpinBox.validate(self, text, pos)
        if res in (QtGui.QValidator.Invalid, QtGui.QValidator.Intermediate):
            return res
        new_value = QtGui.QDoubleSpinBox.valueFromText(self, text)
        if not popup_values[self.indexMinimum] <= new_value <= popup_values[self.indexMaximum]:
            return QtGui.QValidator.Invalid, res[1]
        return res

    def valueFromText(self, text):
        new_value = QtGui.QDoubleSpinBox.valueFromText(self, text)
        pos = bisect_left(popup_values, new_value)
        if pos == 1:
            self.index = pos
            self.indexChanged.emit(pos)
            return popup_values[0]
        if pos == len(popup_values):
            self.index = pos
            self.indexChanged.emit(pos)
            return popup_values[-1]
        before = popup_values[pos-1]
        after = popup_values[pos]
        if after-new_value < new_value-before:
            self.index = after
            self.indexChanged.emit(after)
            return after
        self.index = before
        self.indexChanged.emit(before)
        return before

class Globals(QtGui.QDialog):
    def __init__(self, parent=None):
        QtGui.QDialog.__init__(self, parent=None)
        load_ui(self, 'globals.ui')
        pt = namedtuple('pt', 'index delta')
        pt.__new__.__defaults__ = (0, )
        self.main = parent
        self.sysex = []
        self.data = []
        self.original_data = []
        self.receiving = False
        self.general_layout = self.general_group.layout()
        self.system_layout = self.system_group.layout()
        self.midi_layout = self.midi_group.layout()
        self.layouts = self.general_layout, self.system_layout, self.midi_layout

        self.buttonBox.button(QtGui.QDialogButtonBox.Reset).setText('Reload from Blofeld')
        self.buttonBox.button(QtGui.QDialogButtonBox.Apply).clicked.connect(self.send_data)
        self.accepted.connect(self.check_changes)

        self.transp_spin.valueChanged.connect(lambda value: self.transp_spin.setPrefix('+' if value >= 0 else ''))
        self.transp_spin.valueChanged.emit(self.transp_spin.value())
        self.param_dict = {
                           self.volume_spin: pt(55), 
                           self.cat_combo: pt(56), 
                           self.tune_spin: pt(40, 376), 
                           self.transp_spin: pt(41, -64), 
                           self.freeBtn_combo: pt(59), 
                           self.devId_spin: pt(37), 
                           self.autoEdit_chk: pt(35), 
                           self.contrast_spin: pt(39), 
                           self.popup_spin: pt(38), 
                           self.velocity_combo: pt(50), 
                           self.pedal_combo: pt(60), 
                           self.channel_spin: pt(36), 
                           self.clock_combo: pt(48), 
                           self.pgmSend_chk: pt(46), 
                           self.localCtrl_chk: pt(57), 
                           self.ctrlSend_combo: pt(44), 
                           self.ctrlReceive_chk: pt(45), 
                           self.ctrlW_spin: pt(51), 
                           self.ctrlX_spin: pt(52), 
                           self.ctrlY_spin: pt(53), 
                           self.ctrlZ_spin: pt(54), 
                           }
        for w in self.param_dict:
            if isinstance(w, QtGui.QSpinBox):
                w.valueChanged.connect(self.editData)
            elif isinstance(w, PopupSpin):
                w.indexChanged.connect(self.editData)
            elif isinstance(w, QtGui.QComboBox):
                w.currentIndexChanged.connect(self.editData)
            else:
                w.toggled.connect(self.editData)


    def editData(self, value):
        if self.receiving: return
        value = int(value)
        self.data[self.param_dict[self.sender()].index] = value

    def get_column_size_request(self, column):
        width = 0
        for layout in self.layouts:
            for row in range(layout.rowCount()):
                item = layout.itemAtPosition(row, column)
                if not item: continue
                width = max(item.sizeHint().width(), width)
        return width

    def showEvent(self, event):
        widget_width = max(self.get_column_size_request(1), self.get_column_size_request(4))
        label_width = max(self.get_column_size_request(0), self.get_column_size_request(3))
        for layout in self.layouts:
            layout.setColumnMinimumWidth(1, widget_width)
            layout.setColumnMinimumWidth(4, widget_width)
            layout.setColumnMinimumWidth(0, label_width)
            layout.setColumnMinimumWidth(3, label_width)

    def setData(self, sysex):
        self.sysex = sysex
        data = sysex[5:-2]
        self.receiving = True
        if self.data:
            for i, v in enumerate(self.data):
                if v != data[i]:
                    print 'value {} changed from {} to {}'.format(i, v, data[i])
        for w, p in self.param_dict.items():
            if isinstance(w, QtGui.QSpinBox):
                w.setValue(data[p.index] + p.delta)
            elif isinstance(w, PopupSpin):
                w.setIndex(data[p.index])
            elif isinstance(w, QtGui.QComboBox):
                w.setCurrentIndex(data[p.index])
            else:
                w.setChecked(data[p.index])

        self.data = data
        self.original_data = data[:]
        self.receiving = False
        self.show()

    def check_changes(self):
        if self.data != self.original_data:
            self.send_data()

    def send_data(self):
        self.sysex[5:-2] = self.data
        self.sysex[-2] = 0x7f
        req = SysExEvent(1, self.sysex)
        req.source = self.main.alsa.output.client.id, self.main.alsa.output.id
        self.main.seq.output_event(req.get_event())
        self.main.seq.drain_output()


class SortedLibrary(object):
    def __init__(self, library):
        self.by_bank = library.data
        by_cat = {i:[] for i in range(len(categories))}
        by_alpha = {l:[] for l in ['0..9']+list(uppercase)}
        for b, progs in enumerate(library.data):
            for p in progs:
                if p is None: continue
                if p.name[0] in ascii_letters:
                    by_alpha[p.name[0].upper()].append(p)
                else:
                    by_alpha['0..9'].append(p)
                by_cat[p.cat].append(p)
        self.by_cat = by_cat
        self.by_alpha = {}
        for letter, sound_list in by_alpha.items():
            self.by_alpha[letter] = sorted(sound_list, key=lambda s: s.name.lower())





