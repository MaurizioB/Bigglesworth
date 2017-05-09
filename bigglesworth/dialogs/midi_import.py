# *-* coding: utf-8 *-*

from string import uppercase
from os.path import exists as file_exists
from PyQt4 import QtCore, QtGui

from bigglesworth.utils import load_ui, setBold
from bigglesworth.const import sound_headers, categories, Params, BANK, NAME, PROG, CATEGORY, STORED, ValuesRole, EditedRole
from bigglesworth.classes import Sound
from bigglesworth import midifile

_UNCHANGED, _MINIMUM, _MAXIMUM = None, 0, -1

class NoEditItem(QtGui.QStandardItem):
    def __init__(self, *args, **kwargs):
        QtGui.QStandardItem.__init__(self, *args, **kwargs)
        self.setFlags(self.flags() ^ QtCore.Qt.ItemIsEditable)

class FixDelegate(QtGui.QStyledItemDelegate):
    def __init__(self, parent=None):
        QtGui.QStyledItemDelegate.__init__(self, parent)
        self.commitData.connect(self.set_data)

    def createEditor(self, parent, option, index):
        self.index = index
        combo = QtGui.QComboBox(parent)
        combo.addItems(['Unchanged'] + index.data(ValuesRole).toPyObject())
#        model = QtGui.QStandardItemModel()
#        [model.appendRow(QtGui.QStandardItem(value)) for value in index.data(ValuesRole).toPyObject()]
#        combo.setModel(model)
        combo.setCurrentIndex(index.data(EditedRole).toPyObject() + 1)
        combo.activated.connect(lambda i: parent.setFocus())
        return combo

    def set_data(self, widget):
        item = self.index.model().itemFromIndex(self.index)
        item.setData(widget.currentIndex() - 1, EditedRole)
#        sound = self.index.model().sound(self.index)
#        if sound.cat == widget.currentIndex(): return
#        self.index.model().sound(self.index).cat = widget.currentIndex()


class ParamFixDialog(QtGui.QDialog):
    def __init__(self, sound_list, invalid, parent=None):
        QtGui.QDialog.__init__(self, parent)
        self.sound_list = sound_list
        self.edited = {sound:[] for sound in sound_list}
        self.invalid = invalid
        layout = QtGui.QGridLayout()
        self.setLayout(layout)
        self.setWindowTitle('Invalid sound parameters detected')
        icon = self.style().standardIcon(QtGui.QStyle.SP_MessageBoxWarning)
        icon_label = QtGui.QLabel()
        icon_label.setSizePolicy(QtGui.QSizePolicy.Maximum, QtGui.QSizePolicy.Preferred)
        icon_label.setPixmap(QtGui.QPixmap(icon.pixmap(32, 32)))
        layout.addWidget(icon_label, 0, 0)
        layout.addWidget(QtGui.QLabel('The following sounds contain invalid data, how do you want to proceed?'), 0, 1, 1, 2)
        self.table = QtGui.QTreeView()
        self.table.header().setResizeMode(QtGui.QHeaderView.ResizeToContents)
        self.model = QtGui.QStandardItemModel()
        self.model.setHorizontalHeaderLabels(['Sound parameter', 'Value', 'Allowed range', 'Fix value'])
        self.model.itemChanged.connect(self.highlight)
        self.table.setModel(self.model)
        self.table.setItemDelegateForColumn(3, FixDelegate())
        layout.addWidget(self.table, 1, 0, 1, 3)
        for inv, param_ids in invalid:
            sound = sound_list[inv]
            sound_item = NoEditItem(sound.name)
            self.model.appendRow([sound_item, NoEditItem(), NoEditItem(), NoEditItem()])
            for child, param_info in enumerate(param_ids):
                if isinstance(param_info, int):
                    param = Params[param_info]
                    param_item = NoEditItem(param.name)
                    value_item = NoEditItem(str(getattr(sound, param.attr)))
                    range_item = NoEditItem('{} - {}'.format(*param.range[:2]))
                    edited_item = QtGui.QStandardItem('Unchanged')
                    edited_item.setData(['{} - {}'.format(i, v) for i, v in zip(xrange(param.range[0], param.range[1] + 1), param.values)], ValuesRole)
                    edited_item.setData(-1, EditedRole)
                    self.edited[sound].append((param, edited_item))
                    sound_item.setChild(child, param_item)
                    sound_item.setChild(child, 1, value_item)
                    sound_item.setChild(child, 2, range_item)
                    sound_item.setChild(child, 3, edited_item)
                else:
                    param = Params[param_info[0]]
                    main_item = NoEditItem(param.name)
                    sound_item.setChild(child, main_item)
                    for sub_id, (sub_param_name, short, value, values) in enumerate(param_info[1]):
                        param_item = NoEditItem(sub_param_name)
                        value_item = NoEditItem(str(value))
                        range_item = NoEditItem('0 - {}'.format(len(values) - 1))
                        edited_item = QtGui.QStandardItem('Unchanged')
                        edited_item.setData(['{} - {}'.format(i, v) for i, v in zip(xrange(len(values)), values)], ValuesRole)
                        edited_item.setData(-1, EditedRole)
                        self.edited[sound].append((param, short, edited_item))
                        main_item.setChild(sub_id, param_item)
                        main_item.setChild(sub_id, 1, value_item)
                        main_item.setChild(sub_id, 2, range_item)
                        main_item.setChild(sub_id, 3, edited_item)
        self.table.expandAll()
        unchanged_btn = QtGui.QPushButton('Leave all values unchanged')
        unchanged_btn.clicked.connect(lambda: self.set_all_values(_UNCHANGED))
        layout.addWidget(unchanged_btn, 2, 0)
        min_btn = QtGui.QPushButton('Set all values to minimum')
        min_btn.clicked.connect(lambda: self.set_all_values(_MINIMUM))
        layout.addWidget(min_btn, 2, 1)
        max_btn = QtGui.QPushButton('Set all values to maximum')
        max_btn.clicked.connect(lambda: self.set_all_values(_MAXIMUM))
        layout.addWidget(max_btn, 2, 2)

        buttonBox = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Apply)
        proceed_btn = buttonBox.button(QtGui.QDialogButtonBox.Apply)
        proceed_btn.setText('Proceed')
        proceed_btn.clicked.connect(self.apply)
        layout.addWidget(buttonBox, 3, 0, 1, 3)

    def set_all_values(self, mode):
        def _set_data(item):
            if mode == _UNCHANGED:
                item.setData(-1, EditedRole)
                item.setText('Unchanged')
            elif mode == _MINIMUM:
                item.setData(0, EditedRole)
                item.setText(item.data(ValuesRole).toPyObject()[0])
            else:
                values = item.data(ValuesRole).toPyObject()
                item.setData(len(values) - 1, EditedRole)
                item.setText(values[-1])

        for row in xrange(self.model.rowCount()):
            parent = self.model.item(row, 0)
            for child_row in xrange(parent.rowCount()):
                child = parent.child(child_row, 0)
                if child.hasChildren():
                    for sub_row in xrange(child.rowCount()):
                        _set_data(child.child(sub_row, 3))
                else:
                    _set_data(parent.child(child_row, 3))

    def highlight(self, item):
        setBold(item, True if item.data(EditedRole).toPyObject() >= 0 else False)

    def apply(self):
        if not self.ignore_confirm():
            return
        for sound, edited in self.edited.items():
            if not edited: continue
            for data in edited:
                param = data[0]
                value = data[-1].data(EditedRole).toPyObject()
                if value < 0: continue
                if len(data) == 2:
                    setattr(sound, param.attr, value)
                else:
                    param, short = data[:-1]
                    shift, max_value = param.values.indexes_range[short]
                    reset_mask = (2**max_value.bit_length()-1) << shift
                    current_value = getattr(sound, param.attr)
                    new_value = (current_value ^ reset_mask) + (value << shift)
                    setattr(sound, param.attr, new_value)
        self.accept()

    def ignore_confirm(self):
        if any(True for params in self.edited.values() for field in params if (field and field[-1].data(EditedRole).toPyObject() < 0)):
            res = QtGui.QMessageBox.question(
                                             self, 'Invalid data', 
                                             'Some invalid data is still present in the library, do you want to proceed?', 
                                             QtGui.QMessageBox.Yes|QtGui.QMessageBox.No
                                             )
            if res != QtGui.QMessageBox.Yes:
                return False
        return True

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self.reject()

    def exec_(self):
        res = QtGui.QDialog.exec_(self)
        if not res:
            return
        return self.sound_list


class GrowingFileLabel(QtGui.QLabel):
    dots = QtCore.QString.fromUtf8('…')

    def __init__(self, *args, **kwargs):
        QtGui.QLabel.__init__(self, *args, **kwargs)
        self.font_metrics = QtGui.QFontMetrics(self.font())
        self.full_text = ''

    def ellipse_text(self):
        text = self.full_text
        if self.font_metrics.width(text) <= self.width():
            QtGui.QLabel.setText(self, text)
            return
        split = text.split('/')
        file = '/'+split[-1]
        path = split[:-1].join('/')
        path_len = len(path)
        cutter = 1
        while self.font_metrics.width(text) > self.width():
            text = path[:-cutter] + self.dots + file
            cutter += 1
            if cutter == path_len:
                break
        QtGui.QLabel.setText(self, text)

    def setText(self, text):
        if text.startsWith(str(QtCore.QDir.homePath())):
            text = text.replace(QtCore.QDir.homePath(), '~')
        self.full_text = text
        self.ellipse_text()

    def resizeEvent(self, event):
        self.ellipse_text()


class SmallCheck(QtGui.QCheckBox):
    square_pen = QtGui.QColor(QtCore.Qt.darkGray)
    select_pen = QtGui.QColor(QtCore.Qt.black)
    select_brush = QtGui.QColor(QtCore.Qt.black)
    path = QtGui.QPainterPath()
    path.moveTo(2, 5)
    path.lineTo(4, 8)
    path.lineTo(8, 2)
    path.lineTo(4, 6)
    def __init__(self, *args, **kwargs):
        QtGui.QCheckBox.__init__(self, *args, **kwargs)
        self.setSizePolicy(QtGui.QSizePolicy.Maximum, QtGui.QSizePolicy.Minimum)
        self.square = QtCore.QRectF()
        self.setChecked(True)

    def sizeHint(self):
        return QtCore.QSize(4, 4)

    def paintEvent(self, event):
        qp = QtGui.QPainter()
        qp.begin(self)
        qp.setRenderHints(QtGui.QPainter.Antialiasing)
        qp.translate(.5, .5)
        qp.setPen(self.square_pen)
        qp.drawRect(self.square)
        if self.isChecked():
            qp.setPen(self.select_pen)
            qp.setBrush(self.select_brush)
            qp.translate(self.square.left(), self.square.top())
            qp.drawPath(self.path)
        qp.end()

    def resizeEvent(self, event):
        self.square = QtCore.QRectF(self.width()/2.-5, self.height()/2.-5, 10, 10)

class MidiImportDialog(QtGui.QDialog):
    dump_send = QtCore.pyqtSignal(object)
    sound_headers = [''] + [sound_headers[i] for i, n in enumerate(sound_headers) if i in (BANK, PROG, NAME, CATEGORY)]

    def __init__(self, main, parent):
        QtGui.QDialog.__init__(self, parent)
        load_ui(self, 'dialogs/midi_import.ui')
        self.main = main

        self.import_btn = QtGui.QPushButton('Import to library')
        self.import_btn.setIcon(self.style().standardIcon(QtGui.QStyle.SP_DialogSaveButton))
        self.buttonBox.addButton(self.import_btn, QtGui.QDialogButtonBox.ActionRole)
        self.import_btn.clicked.connect(self.import_sounds)

        self.export_state = False
        self.midi_state = False

        self.dump_btn = QtGui.QPushButton('Dump all')
        self.dump_btn.setEnabled(False)
        self.dump_btn.setIcon(self.style().standardIcon(QtGui.QStyle.SP_ArrowRight))
        self.buttonBox.addButton(self.dump_btn, QtGui.QDialogButtonBox.ActionRole)
        self.dump_btn.clicked.connect(self.dump_sounds)

        self.splitter.setCollapsible(1, True)

        self.sound_list = []
        self.export_list = []

        self.model = self.sounds_table.model()
        self.sounds_table.setColumnCount(len(self.sound_headers))
        self.sounds_table.setHorizontalHeaderLabels(self.sound_headers)
        self.sounds_table.horizontalHeader().setResizeMode(QtGui.QHeaderView.ResizeToContents)
        self.sounds_table.horizontalHeader().setResizeMode(3, QtGui.QHeaderView.Stretch)
        self.sounds_table.verticalHeader().setVisible(False)
        self.sounds_table.horizontalHeader().setVisible(True)
        self.sounds_table.verticalHeader().setResizeMode(QtGui.QHeaderView.ResizeToContents)
        self.bankmap_combo.addItems([uppercase[b] for b in range(8)])
        self.bankmap_btn.setIcon(self.style().standardIcon(QtGui.QStyle.SP_DialogApplyButton))

        self.destination_group.setId(self.sound_buffer_radio, 0)
        self.destination_group.setId(self.multi_buffer_radio, 1)
        self.destination_group.setId(self.library_radio, 2)

        self.name_edit.setValidator(QtGui.QRegExpValidator(QtCore.QRegExp('[\x20-\x7f°]*')))
        self.cat_combo.addItems(categories)
        self.bank_combo.addItems([uppercase[b] for b in range(8)])
        self.single_dump_btn.setIcon(self.style().standardIcon(QtGui.QStyle.SP_ArrowRight))
        self.apply_btn.setIcon(self.style().standardIcon(QtGui.QStyle.SP_DialogApplyButton))

        self.file_open_btn.clicked.connect(self.file_open)
        self.sounds_table.currentChanged = self.currentChanged
        self.sounds_table.selectionChanged = self.selectionChanged
        self.sounds_table.customContextMenuRequested.connect(self.sound_menu)
        self.sounds_table.cellDoubleClicked.connect(self.dump_temp)
        self.check_btn.clicked.connect(lambda: self.check_selection(True))
        self.uncheck_btn.clicked.connect(lambda: self.check_selection(False))
        self.single_dump_btn.clicked.connect(self.dump_single)
        self.bankmap_btn.clicked.connect(self.bankmap_update)

        self.name_edit.textChanged.connect(lambda t: self.apply_btn.setEnabled(True))
        self.cat_combo.currentIndexChanged.connect(lambda i: self.apply_btn.setEnabled(True))
        self.apply_btn.clicked.connect(self.sound_update)

    def currentChanged(self, index, prev):
        QtGui.QTableWidget.currentChanged(self.sounds_table, index, prev)
        sound = self.sound_list[index.row()]
        self.summary_widget.setSoundData(sound.data)
        self.name_edit.setText(sound.name)
        self.cat_combo.setCurrentIndex(sound.cat)
        self.bank_combo.setCurrentIndex(sound.bank)
        self.prog_spin.setValue(sound.prog + 1)
        self.apply_btn.setEnabled(False)

    def selectionChanged(self, selected, deselected):
        QtGui.QTableWidget.selectionChanged(self.sounds_table, selected, deselected)
        selection = set([index.row() for index in self.sounds_table.selectionModel().selectedIndexes()])
        self.sound_groupbox.setEnabled(True if len(selection) == 1 else False)

    def midi_output_state(self, conn):
        self.midi_state = True if conn else False
        self.doubleclick_dump_chk.setEnabled(self.midi_state)
        self.single_dump_btn.setEnabled(self.midi_state)
        self.enable_export_btns()

    def enable_export_btns(self):
        state = True if (self.export_state and self.midi_state) else False
        self.dump_btn.setEnabled(state)
        self.import_btn.setEnabled(state)

    def import_sounds(self):
        export_len = len([i for i in self.export_list if i])
        res = QtGui.QMessageBox.question(
                                         self, 'Import to library',
                                         'You are about to overwrite {} sound{} to the local library, do you want to proceed?'.format(export_len, 's' if export_len>1 else ''), 
                                         QtGui.QMessageBox.Yes|QtGui.QMessageBox.No
                                         )
        if res != QtGui.QMessageBox.Yes: return
        sound_list = []
        for i, state in enumerate(self.export_list):
            if state:
                sound = self.sound_list[i].copy()
                sound._state = STORED
                sound_list.append(sound)
        self.main.blofeld_library.addSoundBulk(sound_list)
        self.hide()

    def dump_sounds(self):
        export_len = len([i for i in self.export_list if i])
        res = QtGui.QMessageBox.question(
                                         self, 'Dump to Blofeld',
                                         'You are about to dump {} sound{} to the Blofeld, do you want to proceed?'.format(export_len, 's' if export_len>1 else ''), 
                                         QtGui.QMessageBox.Yes|QtGui.QMessageBox.No
                                         )
        if res != QtGui.QMessageBox.Yes: return
        sound_list = []
        for i, state in enumerate(self.export_list):
            if state:
                sound = self.sound_list[i].copy()
                sound._state = STORED
                sound_list.append(sound)
        self.main.external_dump_bulk_send(sound_list)
        self.hide()

    def dump_temp(self, row, column):
        if not self.doubleclick_dump_chk.isChecked(): return
        copy = self.sound_list[row].copy()
        copy.bank = 0x7f
        copy.prog = 0
        self.dump_send.emit(copy)

    def dump_single(self):
        checked = self.destination_group.checkedId()
        if checked == 0:
            bank = 0x7f
            prog = 0
        elif checked == 1:
            bank = 0x7f
            prog = self.multi_spin.value() - 1
        else:
            bank = self.bank_combo.currentIndex()
            prog = self.prog_spin.value() - 1
            res = QtGui.QMessageBox.question(self, 'Dump selected sound',
                                             'You are going to send a sound dump to the Blofeld at location "{}{:03}".\nThis action cannot be undone. Do you want to proceed?'.format(uppercase[bank], prog+1), 
                                             QtGui.QMessageBox.Ok|QtGui.QMessageBox.Cancel
                                             )
            if not res == QtGui.QMessageBox.Ok: return
        row = self.sounds_table.selectedIndexes()[0].row()
        copy = self.sound_list[row].copy()
        copy.bank = bank
        copy.prog = prog
        self.dump_send.emit(copy)

    def bankmap_update(self):
        newbank = self.bankmap_combo.currentIndex()
        for sound in self.sound_list:
            sound.bank = newbank

    def sound_update(self):
        sound = self.sound_list[self.sounds_table.currentRow()]
        sound.name = str(self.name_edit.text().toUtf8()).ljust(16, ' ')
        self.name_edit.setText(sound.name)
        sound.cat = self.cat_combo.currentIndex()
        self.summary_widget.setSoundData(sound.data)
        self.apply_btn.setEnabled(False)

    def check_selection(self, state):
        for index in self.sounds_table.selectionModel().selectedRows():
            row = index.row()
            check = self.sounds_table.cellWidget(row, 0)
            check.blockSignals(True)
            check.setChecked(state)
            check.blockSignals(False)
            self.export_list[row] = state
        self.export_state = any(self.export_list)
        self.enable_export_btns()

    def sound_menu(self, pos):
        state = self.dump_btn.isEnabled()
        row = self.sounds_table.indexAt(pos).row()
        self.sounds_table.selectRow(row)
        menu = QtGui.QMenu()
        menu.setSeparatorsCollapsible(False)
        header = QtGui.QAction('Dump to...', menu)
        header.setIcon(self.style().standardIcon(QtGui.QStyle.SP_ArrowRight))
        header.setSeparator(True)
        buffer_item = QtGui.QAction('Sound Edit Buffer', menu)
        buffer_item.setEnabled(state)
        menu.addActions([header, buffer_item])
        multi_menu = QtGui.QMenu('Multi Instrument Edit Buffer')
        multi_menu.setEnabled(state)
        menu.addMenu(multi_menu)
        for m in range(16):
            multi_item = QtGui.QAction('Part {}'.format(m+1), multi_menu)
            multi_item.setData(m)
            multi_menu.addAction(multi_item)
        res = menu.exec_(self.sounds_table.mapToGlobal(pos))
        if not res: return
        copy = self.sound_list[row].copy()
        copy.bank = 0x7f
        if res == buffer_item:
            copy.prog = 0
        else:
            copy.prog = res.data().toPyObject()
        self.dump_send.emit(copy)

    def export_set(self, index, state):
        self.export_list[index] = state
        self.export_state = any(self.export_list)
        self.sounds_table.setCurrentCell(index, 0)
        self.enable_export_btns()

    def file_open(self):
        while True:
            path = QtGui.QFileDialog.getOpenFileName(self, 'Open MIDI sound set', QtGui.QDesktopServices.storageLocation(QtGui.QDesktopServices.HomeLocation), 'MIDI files (*.mid);;All files (*)')
            if not path: return
            if not file_exists(str(path)):
                QtGui.QMessageBox.warning(self, 'File does not exists', 'The selected does not exist.\nCheck the file name and path.')
            else:
                try:
                    res = self.midi_load(path)
                    if not res:
                        retry = QtGui.QMessageBox.information(
                                                      self, 'No sounds found', 
                                                      'It looks like the selected file does not contain any sound.\nTry with another file?', 
                                                      QtGui.QMessageBox.Yes|QtGui.QMessageBox.No
                                                      )
                        if retry != QtGui.QMessageBox.Yes: return
                    break
                except:
                    QtGui.QMessageBox.warning(self, 'Unexpected error', 'Something is wrong with the selected file...\nTry with another one.')
        self.setSource(res, path)

    def setSource(self, res, path):
        if not self.build(res):
            return
        self.source_lbl.setText(path)
        self.show()
        self.enable_export_btns()
        self.sounds_table.selectRow(0)

    def midi_load(self, path):
        if isinstance(path, QtCore.QString):
            path = str(path.toUtf8())
        sound_list = []
        try:
            pattern = midifile.read_midifile(path)
        except:
            return False
        for track in pattern:
            for event in track:
                if isinstance(event, midifile.SysexEvent) and len(event.data) == 392:
                    sound_list.append(Sound(event.data[6:391]))
        return sound_list

    def build(self, sound_list):
        invalid = []
        for sound_id, sound in enumerate(sound_list):
            res = sound.checkout()
            if res is not None:
                invalid.append((sound_id, res))
        if invalid:
            sound_list = ParamFixDialog(sound_list, invalid, self).exec_()
            if not sound_list:
                return False
        if self.sound_list:
            self.sounds_table.setRowCount(0)
        self.sound_list = sound_list
        self.export_list = []
        self.sounds_table.setRowCount(len(self.sound_list))
        for row, sound in enumerate(self.sound_list):
            export_item = QtGui.QStandardItem()
            export_item.setCheckable(True)
            check = SmallCheck()
            check.toggled.connect(lambda state, index=row: self.export_set(index, state))
            self.export_list.append(True)
            self.sounds_table.setCellWidget(row, 0, check)
            bank_item = QtGui.QTableWidgetItem(uppercase[sound.bank] if sound.bank < len(uppercase) else uppercase[-1])
            bank_item.setTextAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter)
            prog_item = QtGui.QTableWidgetItem('{:03}'.format(sound.prog+1))
            name_item = QtGui.QTableWidgetItem(QtCore.QString.fromUtf8(sound.name))
            cat_item = QtGui.QTableWidgetItem(categories[sound.cat] if sound.cat < len(categories) else categories[-1])
            self.sounds_table.setItem(row, 1, bank_item)
            self.sounds_table.setItem(row, 2, prog_item)
            self.sounds_table.setItem(row, 3, name_item)
            self.sounds_table.setItem(row, 4, cat_item)
            sound.nameChanged.connect(name_item.setText)
            sound.bankChanged.connect(lambda bank, item=bank_item: item.setText(uppercase[bank]))
        if len(self.sound_list) <= 128:
            allow_remap = True
        else:
            allow_remap = False
        self.bankmap_btn.setEnabled(allow_remap)
        self.bankmap_combo.setEnabled(allow_remap)
        self.bankmap_lbl.setEnabled(allow_remap)
        self.export_state = True
        return True




