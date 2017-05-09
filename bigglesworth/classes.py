# *-* coding: utf-8 *-*

import urllib2
import pickle
from uuid import uuid4
from os import path, makedirs
from itertools import chain
from shutil import copy
from string import uppercase, ascii_letters
from PyQt4 import QtCore, QtGui

import midifile
from bigglesworth.const import *
from bigglesworth import version

pow21 = 2**21

class VersionCheck(QtCore.QObject):
    url = 'https://github.com/MaurizioB/Bigglesworth/raw/master/bigglesworth/version.py'
    v_maj = version.MAJ_VERSION
    v_min = version.MIN_VERSION
    v_rev = version.REV_VERSION
    res = QtCore.pyqtSignal(object)
    error = QtCore.pyqtSignal()
    done = QtCore.pyqtSignal()
    update = QtCore.pyqtSignal(bool)

    def __init__(self, main):
        QtCore.QObject.__init__(self)
        self.main = main
        self.timer = QtCore.QTimer()
        self.timer.setInterval(30000)
        self.timer.timeout.connect(self.error.emit)

    def run(self):
        self.timer.start()
        try:
            try:
                res = urllib2.urlopen(self.url)
                self.timer.stop()
                exec(res.read())
                self.check(MAJ_VERSION, MIN_VERSION, REV_VERSION)
            except:
                self.timer.stop()
                self.error.emit()
        except:
            self.timer.stop()
            self.error.emit()
        self.done.emit()

    def check(self, v_maj, v_min, v_rev):
#        print 'Current: {}.{}.{}'.format(self.v_maj, self.v_min, self.v_rev)
#        print '{}.{}.{}'.format(v_maj, v_min, v_rev)
#        print type(self.v_maj), type(v_maj)
        if (self.v_maj, self.v_min, self.v_rev) == (v_maj, v_min, v_rev):
            self.update.emit(False)
            return
        current = (self.v_maj << 32) + (self.v_min << 16) + self.v_rev
        remote = (v_maj << 32) + (v_min << 16) + v_rev
        if current > remote:
            self.update.emit(False)
        else:
            self.update.emit(True)


class Wavetable(QtCore.QObject):
    def __init__(self, data):
        QtCore.QObject.__init__(self)
        self.splitted_values = []
        for w in xrange(64):
            data_iter = iter(data[w * 410 + 8:w * 410 + 392])
            values = []
            for s in xrange(128):
                value = (data_iter.next() << 14) + (data_iter.next() << 7) + data_iter.next()
                if value >= 1048576:
                    value -= 2097152
                values.append(value)
            self.splitted_values.append(values)
        self.slot = data[5]
        self.name = ''.join([str(unichr(l)) if l!=127 else '°' for l in data[392:406]])

    @property
    def values(self):
        return chain.from_iterable(self.splitted_values)

    def setSlot(self, slot):
        for wt_data in self.splitted_values:
            wt_data[5] = slot

    def setName(self, name):
        print 'son qui'
        print self.splitted_values[0][392:406]
        if isinstance(name, QtCore.QString):
            name = unicode(name.toUtf8(), encoding='utf-8')
        name = name.ljust(14)
        name_values = []
        for char in name:
            if char == u'°':
                name_values.append(127)
            else:
                name_values.append(ord(char))
        for wt_data in self.splitted_values:
            wt_data[392:406] = name_values
        print 'ok'
        print self.splitted_values[0][392:406]


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
            self._name = ''.join([str(unichr(l)) if l != 127 else u'°' for l in self.data[363:379]])
            cat = self.data[379]
            if cat < len(categories):
                self._cat = cat
            else:
                self._cat = len(categories) - 1
            self.source = source
            self._state = STORED|(source<<1)
        else:
            self._bank = self._prog = 0
            self._data = []
            self._name = 'None'
            self._cat = None
            self.source = SRC_LIBRARY
            self._state = EMPTY

        self._done = True

    def checkout(self):
        invalid = []
        for i, (param, value) in enumerate(zip(Params, self._data)):
            if param.range == 'reserved': continue
            if isinstance(param.values, AdvParam):
#                if value & param.values.forbidden:
#                    print 'FORBIDDEN! {}{:03} "{}" {}: {:07b} {:07b}'.format(uppercase[self.bank], self.prog, self.name, param.attr, param.values.forbidden, value)
                res = param.values.is_valid(value)
                if res is not True:
                    invalid.append((i, res))
                continue
            p_min, p_max = param.range[:-1]
            if not p_min <= value <= p_max:
                invalid.append(i)
        return invalid if invalid else None

    def copy(self):
        return Sound([self.bank, self.prog] + self.data)

    def __dir__(self):
        return self.__dict__.keys() + Params.param_names.keys()

    def trait_names(self):
        return None

    def _getAttributeNames(self):
        return None

    def __getattr__(self, attr):
        try:
            index = Params.index_from_attr(attr)
            return [self.data[index]][0]
        except Exception as Err:
            print Err
            print 'attr exception: {}'.format(attr)
            print '{}:{}, {}'.format(uppercase[self.bank], self.prog, self.name)
            return None

    def __setattr__(self, attr, value):
        if '_done' in self.__dict__.keys() and attr not in self.__dict__.keys():
            try:
                index = Params.index_from_attr(attr)
                self._data[index] = value
                if 363 <= index <= 378:
                    self.name_reload()
                self._state = self._state|EDITED
                self.edited.emit(self._state)
            except Exception as Err:
#                print Err
                super(QtCore.QObject, self).__setattr__(attr, value)
        else:
            super(QtCore.QObject, self).__setattr__(attr, value)

    def __repr__(self):
        return self.name

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
        name = name.replace('\xc2\xb0', '\x7f')
        if name == self._name: return
        if len(name) > 16:
            name = name[:16]
        else:
            name.ljust(16, ' ')
        self._name = name
        self.data[363:379] = [ord(l) for l in name]
        self.nameChanged.emit(name)
        self.state = EDITED
#        print 'changed name'

    def name_reload(self):
        new = ''.join([str(unichr(l)) for l in self.data[363:379]])
#        if new == self._name: return
        self._name = new
        self.nameChanged.emit(new)

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


class SortedLibrary(object):
    def __init__(self, library):
        self.by_bank = library.data
        self.by_cat = {i: [] for i in range(len(categories))}
        self.by_alpha = {l: [] for l in ['0..9']+list(uppercase)}

    def reload(self):
        by_cat = {i: [] for i in range(len(categories))}
        by_alpha = {l: [] for l in ['0..9']+list(uppercase)}
        for b, progs in enumerate(self.by_bank):
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


class WavetableLibrary(QtCore.QObject):
    def __init__(self, main):
        QtCore.QObject.__init__(self)
        self.main = main
        self.model = QtGui.QStandardItemModel()
        self.model.setHorizontalHeaderLabels(['Name', 'Slot', 'Last modified'])
        self.wavetable_data = {}

    def add_local_sysex(self, file_info):
        if file_info.size() != 26240:
            raise BaseException('Wavetable file "{}", doesn\'t match size.'.format(file_info.fileName()))
        try:
            with open(str(file_info.absoluteFilePath().toUtf8()), 'rb') as sf:
                data = list(ord(i) for i in sf.read(406))
            if data[:4] != [IDW, IDE] and data[4] != WTBD and data[7] != 0:
                raise BaseException('SysEx file "{}" is not a Wavetable'.format(file_info.fileName()))
        except Exception as e:
            raise BaseException('An error occurred while loading wavetable file {}:\n{}'.format(file_info.fileName(), e))
        wt_slot = data[5]
        wt_name = ''.join([str(unichr(l)) for l in data[392:406]])
        name_item = QtGui.QStandardItem(wt_name)
        slot_item = QtGui.QStandardItem(str(wt_slot))
        date_item = QtGui.QStandardItem(file_info.lastModified().toString(QtCore.Qt.SystemLocaleShortDate))
        file_item = QtGui.QStandardItem()
        file_item.setData(file_info)
        uid = str(uuid4())
        uid_item = QtGui.QStandardItem(uid)
        self.model.appendRow([name_item, slot_item, date_item, file_item, uid_item])
        self.wavetable_data[uid] = None

    def load_list(self, files):
        for file_info in files:
            try:
                self.add_local_sysex(file_info)
            except Exception as e:
                print e

    def count(self):
        return self.model.rowCount()

    def delete(self, uid):
        uid_item = self.model.findItems(uid, QtCore.Qt.MatchExactly, 4)[0]
        row = uid_item.row()
        file_info = self.model.item(row, 3).data().toPyObject()
        QtCore.QDir().remove(file_info.absoluteFilePath())
        self.model.takeRow(uid_item.row())
        self.wavetable_data.pop(str(uid))

    def sanitize(self, file_name):
        for char in set(file_name) & set('<>:"/\|?* '):
            file_name = file_name.replace(char, '_')
        return file_name

    def duplicate(self, uid):
        uid_item = self.model.findItems(uid, QtCore.Qt.MatchExactly, 4)[0]
        row = uid_item.row()
        file_info = self.model.item(row, 3).data().toPyObject()
        base_name = str(self.model.item(row, 0).text().toUtf8())
#        base_name = str(file_info.baseName().toUtf8())
        pos = 1
        index = 0
        while True:
            last = base_name[-pos]
            if not last.isdigit():
                base_name = base_name[:-pos] + str(index)
                new_file_info = QtCore.QFileInfo('{}/{}'.format(file_info.absolutePath(), self.sanitize(base_name) + '.syx'))
                if not new_file_info.exists():
                    break
                if index == 9:
                    pos += 1
                index += 1
            else:
                old_index = int(last)
                if old_index == 9:
                    pos += 1
                index = old_index + 1
                base_name = base_name[:-pos] + str(index)
                new_file_info = QtCore.QFileInfo('{}/{}'.format(file_info.absolutePath(), self.sanitize(base_name) + '.syx'))
                if not new_file_info.exists():
                    break
        new_uid = str(uuid4())
        current_data, current_slot, _ = self[uid]
        self[new_uid] = chain.from_iterable(current_data), current_slot, QtCore.QString(base_name)

    def nameExists(self, name):
        return True if len(self.model.findItems(name)) else False

    def __getitem__(self, uid):
        wavetable_data = self.wavetable_data.get(uid)
        if wavetable_data is None:
            uid_item = self.model.findItems(uid, QtCore.Qt.MatchExactly, 4)[0]
            wavetable_path = self.model.item(uid_item.row(), 3).data().toPyObject().absoluteFilePath()
            with open(str(wavetable_path.toUtf8()), 'rb') as sf:
                sysex_list = list(ord(i) for i in sf.read())
            wavetable_values = []
            for w in xrange(64):
                data = iter(sysex_list[w * 410 + 8:w * 410 + 392])
                values = []
                for s in xrange(128):
                    value = (data.next() << 14) + (data.next() << 7) + data.next()
                    if value >= 1048576:
                        value -= 2097152
                    values.append(value)
                wavetable_values.append(values)
            slot = sysex_list[5]
            name = ''.join([str(unichr(l)) for l in sysex_list[392:406]])
            self.wavetable_data[uid] = wavetable_values, slot, name
            wavetable_data = wavetable_values, slot, name
        return wavetable_data

    def __setitem__(self, uid, (wavetable_values, slot, name)):
        if uid not in self.wavetable_data:
#            uid = uuid4()
            self.wavetable_data[uid] = wavetable_values, slot, name
            original_name = None
            name_item = QtGui.QStandardItem(name)
            slot_item = QtGui.QStandardItem(str(slot))
            date_item = QtGui.QStandardItem()
            file_item = QtGui.QStandardItem()
            file_item.setData(QtCore.QFileInfo(QtCore.QDir(QtGui.QDesktopServices.storageLocation(QtGui.QDesktopServices.DataLocation) + '/wavetables/'), '_'))
            uid_item = QtGui.QStandardItem(uid)
            self.model.appendRow([name_item, slot_item, date_item, file_item, uid_item])
        else:
            original_name = str(self.wavetable_data[uid][2])
            item = self.model.findItems(uid, column=4)[0]
            _row = item.row()
            self.model.item(_row, 0).setText(name)
            self.model.item(_row, 1).setText(str(slot))
            date_item = self.model.item(_row, 2)
            file_item = self.model.item(_row, 3)

        name = str(name.toUtf8())
        name_data = tuple(ord(l) if l != '°' else 127 for l in name.replace('\xc2\xb0', '\x7f').ljust(14, ' '))
        sysex_data = []
        values_iter = iter(wavetable_values)
        wavetable_data_list = []
        for n in xrange(64):
            sysex_data.extend([INIT, IDW, IDE, self.main.blofeld_id, WTBD, slot, n, 0])
            values = []
            for i in xrange(128):
                value = values_iter.next()
                values.append(value)
                if value < 0:
                    value = pow21 + value
                sysex_data.extend((value >> 14, (value >> 7) & 127,  value & 127))
            wavetable_data_list.append(values)
            sysex_data.extend(name_data)
            sysex_data.extend((0, 0, CHK))
            sysex_data.append(END)

        self.wavetable_data[uid] = wavetable_data_list, slot, name

        file_name = self.sanitize(name)
#        for char in set(file_name) & set('<>:"/\|?*'):
#            file_name = file_name.replace(char, '_')
        old_file = file_item.data().toPyObject()
        wavetable_filepath = '{}/{}.syx'.format(old_file.absolutePath().toUtf8(), file_name.ljust(14, '_'))
        with open(wavetable_filepath, 'wb') as sf:
            sf.write(bytearray(sysex_data))
        if original_name is not None and original_name != name:
            QtCore.QDir().remove(old_file.absoluteFilePath())
        file_info = QtCore.QFileInfo(wavetable_filepath)
        date_item.setText(file_info.lastModified().toString(QtCore.Qt.SystemLocaleShortDate))
        file_item.setData(file_info)
#        file_name = self.model.item(index, 3).data().toPyObject().absoluteFilePath()
#        print self.model.item(index, 3).data().toPyObject().fileName()

class Library(QtCore.QObject):
    def __init__(self, model, parent=None, banks=26):
        QtCore.QObject.__init__(self, parent)
#        self.data = [[Sound(b, p) for p in range(128)] for b in range(banks)]
        self.model = model
        self.banks = banks
        self.model.cleared.connect(self.clear)
        self.clear()
        self.sorted = SortedLibrary(self)
        self.menu = None
#        self.create_menu()

    def clear(self):
        self.data = [[None for p in range(128)] for b in range(self.banks)]
#        self.sound_index = {}
        self.cat_count = [{c: 0 for c in categories} for b in range(self.banks)]

    def sound(self, bank, prog):
        return self.data[bank][prog]

    def _addSound(self, sound):
        bank = sound.bank
        prog = sound.prog
        self.data[bank][prog] = sound
#        self.sound_index[sound] = bank, prog

        index_item = QtGui.QStandardItem('{}{:03}'.format(uppercase[bank], prog+1))
        index_item.setData(bank*128+prog, IndexRole)
        index_item.setEditable(False)
        bank_item = QtGui.QStandardItem(uppercase[bank])
#        bank_item.setData(bank, UserRole)
        bank_item.setData(bank, BankRole)
        bank_item.setTextAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignCenter)
        bank_item.setEditable(False)
        prog_item = QtGui.QStandardItem('{:03}'.format(prog+1))
#        prog_item.setData(prog, UserRole)
        prog_item.setData(prog, ProgRole)
        prog_item.setEditable(False)
        name_item = QtGui.QStandardItem(sound.name)
#        name_item.setData(sound.Osc_1_Shape, QtCore.Qt.ToolTipRole)
#        name_item.setData(sound.name, QtCore.Qt.ToolTipRole)
        cat_item = QtGui.QStandardItem(categories[sound.cat])
#        cat_item.setData(sound.cat, UserRole)
        cat_item.setData(sound.cat, CatRole)
#        status_item = QtGui.QStandardItem('Dumped' if sound.state == DUMPED else 'Stored')
        status_item = QtGui.QStandardItem(status_dict[sound.state])
        status_item.setData(sound.state, EditedRole)
        status_item.setEditable(False)
        sound_item = QtGui.QStandardItem()
        sound_item.setData(sound, SoundRole)
        sound.bankChanged.connect(lambda bank, item=bank_item: item.setData(bank, BankRole))
        sound.progChanged.connect(lambda prog, item=prog_item: item.setData(prog, ProgRole))
        sound.indexChanged.connect(lambda index, item=index_item: item.setData(index, IndexRole))
        sound.nameChanged.connect(lambda name, item=name_item: item.setText(name))
        sound.catChanged.connect(lambda cat, bank=bank, item=cat_item: self.soundSetCategory(item, bank, cat))
        sound.edited.connect(lambda state, item=status_item: item.setData(state, EditedRole))

        found = self.model.findItems('{}{:03}'.format(uppercase[bank], prog+1), QtCore.Qt.MatchFixedString, 0)
        if found:
            self.model.takeRow(found[0].row())

        self.model.appendRow([index_item, bank_item, prog_item, name_item, cat_item, status_item, sound_item])

    def addSound(self, sound):
        self._addSound(sound)
        self.sort()
        self.create_menu()

    def addSoundBulk(self, sound_list):
        for sound in sound_list:
            self._addSound(sound)
        self.sort()
        if self.menu:
            self.create_menu()

    def sort(self):
        delete_list = []
        for i, bank in enumerate(self.data):
            if not any(bank):
                delete_list.append(i)
        for empty in reversed(delete_list):
            self.data.pop(empty)
        self.banks = len(self.data)
        self.model.sort(PROG)
        self.model.sort(BANK)
        self.sorted.reload()

    def swap(self, source, target):
        first = min(source)
        last = max(source)
        if first/128 == last/128 == target/128:
            bank, first = divmod(first, 128)
            last = last%128
            target = target%128
            clip = self.data[bank][first:last+1]
            del self.data[bank][first:last+1]
            if target > first:
                target = target - len(clip) + 1
            self.data[bank][target:target] = clip
        else:
            full = []
            [full.extend(l) for l in self.data]
            clip = full[first:last+1]
            del full[first:last+1]
            if target > first:
                target = target - len(clip) + 15
            full[target:target] = clip
            for b in range(len(self.data)):
                delta = b*128
                self.data[b] = full[delta:delta+128]
        self.sorted.reload()

    def create_menu(self):
        del self.menu
        menu = QtGui.QMenu()
        by_bank = QtGui.QMenu('By bank', menu)
        menu.addMenu(by_bank)
        for id, bank in enumerate(self.sorted.by_bank):
            if not any(bank): continue
            bank_menu = QtGui.QMenu(uppercase[id], by_bank)
            by_bank.addMenu(bank_menu)
            for sound in bank:
                if sound is None: continue
                item = QtGui.QAction('{:03} {}'.format(sound.prog+1, sound.name), bank_menu)
                item.setData((sound.bank, sound.prog))
                bank_menu.addAction(item)
        by_cat = QtGui.QMenu('By category', menu)
        menu.addMenu(by_cat)
        for cid, cat in enumerate(categories):
            cat_menu = QtGui.QMenu(by_cat)
            by_cat.addMenu(cat_menu)
            cat_len = 0
            for sound in self.sorted.by_cat[cid]:
                cat_len += 1
                item = QtGui.QAction(sound.name, cat_menu)
                item.setData((sound.bank, sound.prog))
                cat_menu.addAction(item)
            if not len(cat_menu.actions()):
                cat_menu.setEnabled(False)
            cat_menu.setTitle('{} ({})'.format(cat, cat_len))
        by_alpha = QtGui.QMenu('Alphabetical', menu)
        menu.addMenu(by_alpha)
        for alpha in sorted(self.sorted.by_alpha.keys()):
            alpha_menu = QtGui.QMenu(by_alpha)
            by_alpha.addMenu(alpha_menu)
            alpha_len = 0
            for sound in self.sorted.by_alpha[alpha]:
                alpha_len += 1
                item = QtGui.QAction(sound.name, alpha_menu)
                item.setData((sound.bank, sound.prog))
                alpha_menu.addAction(item)
            if not len(alpha_menu.actions()):
                alpha_menu.setEnabled(False)
            alpha_menu.setTitle('{} ({})'.format(alpha, alpha_len))
        self.menu = menu

    def soundSetCategory(self, cat_item, bank, cat):
        cat_item.setData(cat, CatRole)

    def __getitem__(self, req):
        if req is None:
            return None
        if not isinstance(req, tuple):
            req = divmod(req, 128)
        try:
            return self.data[req[0]][req[1]]
        except:
            return None


class LibraryModel(QtGui.QStandardItemModel):
    cleared = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        QtGui.QStandardItemModel.__init__(self, 0, 7, parent)
        self.setHorizontalHeaderLabels(sound_headers)

    def clear(self):
        QtGui.QStandardItemModel.clear(self)
        self.setHorizontalHeaderLabels(sound_headers)
        self.cleared.emit()

    def sound(self, index):
        return self.item(index.row(), SOUND).data(SoundRole).toPyObject()


class LibraryProxy(QtGui.QSortFilterProxyModel):
    def __init__(self, parent=None):
        QtGui.QSortFilterProxyModel.__init__(self, parent)
        self.setDynamicSortFilter(True)
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
        if len(self.filter_columns) and any([True for column, index in self.filter_columns.items() if model.item(row, column).data(roles_dict[column]) != index]):
            return False
        if not self.text_filter:
            return True
        if self.text_filter in model.item(row, NAME).text().toLower():
            return True
        return False


class LoadingThread(QtCore.QObject):
    loaded = QtCore.pyqtSignal()

    def __init__(self, parent, library, source, wavetable_library, limit=None):
        self.limit = limit
        QtCore.QObject.__init__(self)
        self.library = library
        self.wavetable_library = wavetable_library
        source = str(source)
        if source == 'personal':
            #should do pass
#            self.source = local_path('presets/blofeld_fact_200802.mid')
            self.source = source
        elif source in ['200801', '200802', '201200']:
            self.source = local_path('presets/blofeld_fact_{}.mid'.format(source))
        else:
            self.source = source

    def run(self):
        #sound library load
        if self.source == 'personal':
            try:
                sound_list = self.load_library()
            except Exception as e:
                print e
#                print 'personal library not found, reverting to default (factory 200802)'
                sound_list = self.load_midi(local_path('presets/blofeld_fact_200802.mid'))
        else:
            sound_list = self.load_midi(self.source)
        self.library.addSoundBulk(sound_list)

        #wavetable library load
        path_txt = QtGui.QDesktopServices.storageLocation(QtGui.QDesktopServices.DataLocation) + '/wavetables/'
        wt_path = QtCore.QDir(path_txt)
        if not wt_path.exists():
            QtCore.QDir().mkpath(path_txt)
        else:
            self.wavetable_library.load_list(wt_path.entryInfoList(['*.syx'], sort=QtCore.QDir.Name))
#        print contents.join('\n')

        self.loaded.emit()

    def load_midi(self, path):
#        print 'opening "{}"'.format(path)
        pattern = midifile.read_midifile(path)
        track = pattern[0]
        i = 0
        sound_list = []
        for event in track:
            if isinstance(event, midifile.SysexEvent):
                sound_list.append(Sound(event.data[6:391]))
                i += 1
                if i == self.limit:
                    break
#        print 'done: {}'.format(len(sound_list))
        return sound_list

    def load_library(self):
        sound_list = []
        data_dir = str(QtGui.QDesktopServices.storageLocation(QtGui.QDesktopServices.DataLocation).toUtf8())
        data_path = path.join(data_dir, 'personal_library')
        if not path.exists(data_path):
            try:
                makedirs(data_dir)
            except:
                pass
            old_path = local_path('presets/personal_library')
            if path.exists(old_path):
                print 'moving old library'
                copy(old_path, data_path)
            else:
                raise
        with open(data_path, 'rb') as of:
            i = 0
            for data in pickle.load(of):
                sound_list.append(Sound(list(data)))
                i += 1
                if i == self.limit:
                    break
        return sound_list


class SettingsGroup(object):
    def __init__(self, settings, name=None):
        self._settings = settings
        self._group = settings.group()
        for k in settings.childKeys():
            value = settings.value(k).toPyObject()
            if isinstance(value, QtCore.QStringList):
                _value = []
                for v in value:
                    try:
                        v = str(v)
                        if v.isdigit():
                            v = int(v)
                        elif v == 'true':
                            v = True
                        elif v == 'false':
                            v = False
                        else:
                            v = float(v)
                    except Exception as e:
                        print e
                    _value.append(v)
                value = _value
            elif isinstance(value, QtCore.QString):
                value = str(value)
                if value == 'true':
                    value = True
                elif value == 'false':
                    value = False
                elif self._is_int(value):
                    value = int(value)
                else:
                    try:
                        value = float(value)
                    except:
                        pass
            setattr(self, self._decode(str(k)), value)
        if len(self._group):
            for g in settings.childGroups():
                settings.beginGroup(g)
                setattr(self, 'g{}'.format(self._decode(g)), SettingsGroup(settings))
                settings.endGroup()
        self._done = True

    def _is_int(self, value):
        try:
            int(value)
            return True
        except:
            return False

    def _encode(self, txt):
        txt = txt.replace('__', '::')
        txt = txt.replace('_', ' ')
        txt = txt.replace('::', '_')
        return txt

    def _decode(self, txt):
        txt = txt.replace('_', '__')
        txt = txt.replace(' ', '_')
        return txt

    def createGroup(self, name):
        self._settings.beginGroup(self._group)
        self._settings.beginGroup(name)
        gname = 'g{}'.format(self._decode(name))
        setattr(self, gname, SettingsGroup(self._settings))
        self._settings.endGroup()
        self._settings.endGroup()

    def __setattr__(self, name, value):
        if '_done' in self.__dict__.keys():
            if not isinstance(value, SettingsGroup):
                dname = self._encode(name)
                if len(self._group):
                    self._settings.beginGroup(self._group)
                    self._settings.setValue(dname, value)
                    self._settings.endGroup()
                else:
                    self._settings.setValue(dname, value)
                super(SettingsGroup, self).__setattr__(name, value)
            else:
                super(SettingsGroup, self).__setattr__(name, value)
        else:
            super(SettingsGroup, self).__setattr__(name, value)

    def __getattr__(self, name):
        def save_func(value):
            self._settings.beginGroup(self._group)
            self._settings.setValue(self._encode(name[4:]), value)
            self._settings.endGroup()
            setattr(self, name[4:], value)
            return value
        if name.startswith('set_'):
            obj = type('setter', (object, ), {})()
            obj.__class__.__call__ = lambda x, y=None: setattr(self, name[4:], y)
            return obj
        if not name.startswith('get_'):
            return
        try:
            orig = super(SettingsGroup, self).__getattribute__(name[4:])
            if isinstance(orig, bool):
                obj = type(type(orig).__name__, (object,), {'value': orig})()
                obj.__class__.__call__ = lambda x,  y=None, save=False, orig=orig: orig
                obj.__class__.__len__ = lambda x: orig
                obj.__class__.__eq__ = lambda x, y: True if x.value==y else False
            else:
                obj = type(type(orig).__name__, (type(orig), ), {})(orig)
                obj.__class__.__call__ = lambda x, y=None, save=False, orig=orig: orig
            return obj
        except AttributeError:
            print 'Setting {} not found, returning default'.format(name[4:])
            obj = type('obj', (object,), {})()
            obj.__class__.__call__ = lambda x, y=None, save=False: y if not save else save_func(y)
            return obj


class SettingsObj(object):
    def __init__(self, settings):
        self._settings = settings
        self._sdata = []
        self._load()
        self._done = True

    def _load(self):
        for d in self._sdata:
            delattr(self, d)
        self._sdata = []
        self._settings.sync()
        self.gGeneral = SettingsGroup(self._settings)
        self._sdata.append('gGeneral')
        for g in self._settings.childGroups():
            self._settings.beginGroup(g)
            gname = 'g{}'.format(self._decode(g))
            self._sdata.append(gname)
            setattr(self, gname, SettingsGroup(self._settings))
            self._settings.endGroup()

    def __getattr__(self, name):
        if not (name.startswith('g') and name[1] in uppercase):
            raise AttributeError(name)
        name = name[1:]
        self._settings.beginGroup(name)
        gname = 'g{}'.format(self._decode(name))
        self._sdata.append(gname)
        new_group = SettingsGroup(self._settings)
        setattr(self, gname, new_group)
        self._settings.endGroup()
        return new_group

    def sync(self):
        self._settings.sync()

    def createGroup(self, name):
        self._settings.beginGroup(name)
        gname = 'g{}'.format(self._decode(name))
        self._sdata.append(gname)
        setattr(self, gname, SettingsGroup(self._settings))
        self._settings.endGroup()

    def _decode(self, txt):
        txt = txt.replace('_', '__')
        txt = txt.replace(' ', '_')
        return txt







