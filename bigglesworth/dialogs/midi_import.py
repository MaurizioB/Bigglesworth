# *-* coding: utf-8 *-*

from string import uppercase
from os.path import exists as file_exists
from PyQt4 import QtCore, QtGui

from bigglesworth.utils import load_ui
from bigglesworth.const import sound_headers, categories, BANK, NAME, PROG, CATEGORY, STORED
from bigglesworth.classes import Sound
from bigglesworth import midifile

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

        self.name_edit.setValidator(QtGui.QRegExpValidator(QtCore.QRegExp('[\x20-\x7f°]*')))
        self.cat_combo.addItems(categories)
        self.bank_combo.addItems([uppercase[b] for b in range(8)])
        self.single_dump_btn.setIcon(self.style().standardIcon(QtGui.QStyle.SP_ArrowRight))
        self.apply_btn.setIcon(self.style().standardIcon(QtGui.QStyle.SP_DialogApplyButton))

        self.file_open_btn.clicked.connect(self.file_open)
        self.sounds_table.currentChanged = self.currentChanged
        self.sounds_table.customContextMenuRequested.connect(self.sound_menu)
        self.sounds_table.cellDoubleClicked.connect(self.dump_temp)
        self.check_btn.clicked.connect(lambda: self.check_selection(True))
        self.uncheck_btn.clicked.connect(lambda: self.check_selection(False))
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

    def midi_output_state(self, conn):
        state = True if conn else False
        self.dump_btn.setEnabled(state)
        self.single_dump_btn.setEnabled(state)
        self.doubleclick_dump_chk.setEnabled(state)

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
        for row_index in self.sounds_table.selectionModel().selectedRows():
            self.sounds_table.cellWidget(row_index.row(), 0).setChecked(state)

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
        export = any(self.export_list)
        self.import_btn.setEnabled(export)
        self.dump_btn.setEnabled(export)
        self.sounds_table.setCurrentCell(index, 0)

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
        self.build(res)
        self.source_lbl.setText(path)
        self.show()

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
        if self.sound_list:
            self.sounds_table.clearContents()
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
            bank_item = QtGui.QTableWidgetItem(uppercase[sound.bank])
            bank_item.setTextAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter)
            prog_item = QtGui.QTableWidgetItem('{:03}'.format(sound.prog+1))
            name_item = QtGui.QTableWidgetItem(sound.name)
            cat_item = QtGui.QTableWidgetItem(categories[sound.cat])
            self.sounds_table.setItem(row, 1, bank_item)
            self.sounds_table.setItem(row, 2, prog_item)
            self.sounds_table.setItem(row, 3, name_item)
            self.sounds_table.setItem(row, 4, cat_item)
            sound.nameChanged.connect(name_item.setText)
            sound.bankChanged.connect(lambda bank, item=bank_item: item.setText(uppercase[bank]))
        if len(self.sound_list) <= 128:
            self.bankmap_btn.setEnabled(True)
            self.bankmap_combo.setEnabled(True)
            self.bankmap_lbl.setEnabled(True)




