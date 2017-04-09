# *-* coding: utf-8 *-*

from os import stat as file_stat
from os.path import exists as file_exists
from string import uppercase
from collections import OrderedDict
from PyQt4 import QtCore, QtGui

from bigglesworth.utils import load_ui
from bigglesworth.classes import Sound
from bigglesworth.const import *

sources = {
           SRC_LIBRARY: 'Local library', 
           SRC_BLOFELD: 'Blofeld', 
           SRC_EXTERNAL: 'Imported', 
           }
WidgetRole = QtCore.Qt.UserRole + 1

class GrowingLineEdit(QtGui.QLineEdit):
    def __init__(self, *args, **kwargs):
        QtGui.QLineEdit.__init__(self, *args, **kwargs)

    def setText(self, text):
        QtGui.QLineEdit.setText(self, text)
        self.setMinimumWidth(self.fontMetrics().boundingRect(text).width() + 8)


class SummaryWidget(QtGui.QSplitter):
    def __init__(self, *args, **kwargs):
        QtGui.QSplitter.__init__(self, *args, **kwargs)
        self.setOrientation(QtCore.Qt.Horizontal)
        self.setChildrenCollapsible(False)
        self.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.MinimumExpanding)

        self.tree = QtGui.QTreeView()
        self.eater = False
        self.addWidget(self.tree)
        self.tree.setEditTriggers(QtGui.QTreeView.NoEditTriggers)
        self.tree.setExpandsOnDoubleClick(False)
        self.tree.setHeaderHidden(True)
        self.tree.setTextElideMode(QtCore.Qt.ElideNone)
        self.model = QtGui.QStandardItemModel()
        self.tree.setModel(self.model)
        self.tree.clicked.connect(self.param_select)
        self.tree.currentChanged = self.param_select

        self.param_widget = QtGui.QWidget()
        self.addWidget(self.param_widget)
        self.build_summary()
        self.tree.header().setResizeMode(QtGui.QHeaderView.ResizeToContents)
        self.tree.expandAll()
        self.tree.setMinimumWidth(self.tree.sizeHintForColumn(0))
        self.tree.collapseAll()

    def build_summary(self):
        def add_family_param(granpa, param, parent=False):
            family = param.family if not parent else None
            if not granpa in families:
#                families[granpa] = {param.family: [param]}
                families[granpa] = OrderedDict([(family, [param])])
                return
            if not family in families[granpa]:
                families[granpa][family] = [param]
            else:
                families[granpa][family].append(param)

        def add_param(parent, param):
            if not parent in families:
                families[parent] = [param]
            else:
                families[parent].append(param)

        self.param_objects = {}
        families = OrderedDict()
        for p in Params.param_list:
            if p.range == 'reserved': continue
            if p.family:
                if 'Envelope' in p.family:
                    add_family_param('Envelopes', p)
                elif p.family.startswith('Arp'):
                    if p.family.startswith('Arpeggiator'):
                        add_family_param('Arpeggiator', p, True)
                    else:
                        add_family_param('Arpeggiator', p)
                elif p.family.startswith('LFO'):
                    add_family_param('LFOs', p)
                elif p.family.startswith('Mixer'):
                    add_family_param('Mixer', p, True)
                elif p.family.startswith('Modifier '):
                    add_family_param('Modifiers', p, True)
                elif p.family.startswith('Osc '):
                    if p.family == 'Osc Pitch':
                        add_family_param('Oscillators', p, True)
                    else:
                        add_family_param('Oscillators', p)
                elif p.family.startswith('Modulation '):
                    add_param('Modulations', p)
                elif p.family.startswith('Amplifier'):
                    add_param('Amplifier', p)
                elif p.family.startswith('Filter'):
                    if p.family == 'Filter':
                        add_family_param('Filters', p, True)
                    else:
                        add_family_param('Filters', p)
                elif p.family.startswith('Effect'):
                    add_family_param('Effects', p)
                else:
                    add_param(p.family, p)
            else:
                add_param('Common', p)
        stack = QtGui.QStackedLayout()
        self.param_widget.setLayout(stack)
        self.empty_params = QtGui.QWidget()
        stack.addWidget(self.empty_params)

        def create_view(name, params):
            widget = QtGui.QGroupBox(name)
            stack.addWidget(widget)
            widget.setLayout(QtGui.QVBoxLayout())
            scroll = QtGui.QScrollArea(widget)
            scroll.setAlignment(QtCore.Qt.AlignHCenter|QtCore.Qt.AlignTop)
            widget.layout().addWidget(scroll)
            scroll_widget = QtGui.QWidget(scroll)
            scroll.setWidget(scroll_widget)
            layout = QtGui.QFormLayout()
            layout.setFormAlignment(QtCore.Qt.AlignHCenter|QtCore.Qt.AlignTop)
            scroll_widget.setLayout(layout)
            for param in params:
                edit = GrowingLineEdit()
                edit.setReadOnly(True)
                edit.setMinimumWidth(64)
                layout.addRow('{}:'.format(param.name), edit)
                self.param_objects[Params.index_from_attr(param.attr)] = (param, edit)
            layout.setSizeConstraint(QtGui.QFormLayout.SetMinAndMaxSize)
            return widget, layout.minimumSize().width()

        param_width = 0
        for family, children in families.items():
            fam_item = QtGui.QStandardItem(family)
            self.model.appendRow(fam_item)
            if isinstance(children, dict):
                for child, params in children.items():
                    if child is None:
                        child_widget, width = create_view(family, params)
                        fam_item.setData(child_widget, WidgetRole)
                        param_width = max(param_width, width)
                        continue
                    child_item = QtGui.QStandardItem(child)
                    fam_item.appendRow([child_item])
                    child_widget, width = create_view(child, params)
                    child_item.setData(child_widget, WidgetRole)
                    param_width = max(param_width, width)
            else:
                child_widget, width = create_view(family, children)
                fam_item.setData(child_widget, WidgetRole)
                param_width = max(param_width, width)
        margins = child_widget.getContentsMargins()
        self.param_widget.setMinimumWidth(param_width + margins[0] + margins[2])
        self.setStretchFactor(0, 1)
        self.setStretchFactor(1, 3)

    def param_select(self, index, prev=None):
        self.tree.scrollTo(index)
        widget = index.data(WidgetRole).toPyObject()
        empty = False
        if isinstance(widget, QtGui.QGroupBox):
            self.param_widget.layout().setCurrentWidget(widget)
        else:
#            self.param_widget.layout().setCurrentWidget(self.empty_params)
            empty = True
        if self.model.itemFromIndex(index).hasChildren():
            if not self.tree.isExpanded(index):
                self.tree.setExpanded(index, True)
            if empty:
                QtCore.QTimer.singleShot(0, lambda: self.tree.setCurrentIndex(index.child(0, 0)))

    def setSoundData(self, data):
        for i, p in enumerate(Params.param_list):
            if p.range == 'reserved': continue
            try:
                if isinstance(p.values, AdvParam):
                    param, edit = self.param_objects[i]
                    edit.setText(', '.join(p.values[data[i]]))
                else:
                    param, edit = self.param_objects[i]
                    value = data[i]
                    if param.range[2] != 1:
                        value = (value - param.range[0]) / param.range[2]
                    else:
                        value = value - param.range[0]
                    edit.setText(param.values[value])
            except Exception as e:
                print 'Exception: {}'.format(e)
                try:
                    print 'Something wrong with param {} "{}": {}'.format(i, param.name, param.values[data[i]])
                except:
                    print 'Out of range for param "{}" (range: {}): {} (value: {})'.format(param.name, param.range, data[i], value)



class FileLabel(QtGui.QLabel):
    dots = QtCore.QString.fromUtf8('…')

    def __init__(self, *args, **kwargs):
        QtGui.QLabel.__init__(self, *args, **kwargs)
        self.font_metrics = QtGui.QFontMetrics(self.font())

    def setEllipsisText(self, text):
        text = text.replace(QtCore.QDir.homePath(), '~')
        if self.font_metrics.width(text) <= self.width():
            self.setText(text)
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
        self.setText(text)


class SummaryDialog(QtGui.QDialog):
    dump_send = QtCore.pyqtSignal(object)

    def __init__(self, main, parent):
        QtGui.QDialog.__init__(self, parent)
        load_ui(self, 'dialogs/summary.ui')
        self.main = main

        dump_btn = QtGui.QPushButton('Dump')
        dump_btn.clicked.connect(self.sound_dump)
        dump_btn.setIcon(self.style().standardIcon(QtGui.QStyle.SP_ArrowRight))
        self.buttonBox.addButton(dump_btn, QtGui.QDialogButtonBox.ActionRole)

        dial_icon = QtGui.QIcon()
        dial_icon.addFile(local_path('dial_icon.png'))
        edit_btn = QtGui.QPushButton('Edit')
        edit_btn.clicked.connect(self.sound_edit)
        edit_btn.setIcon(dial_icon)
        self.buttonBox.addButton(edit_btn, QtGui.QDialogButtonBox.AcceptRole)

        self.bank_combo.addItems([uppercase[l] for l in range(8)])
        self.import_btn.clicked.connect(self.open)
        self.buttonBox.button(QtGui.QDialogButtonBox.Discard).clicked.connect(self.reject)
        self.summary_widget.setFocus()


    def open(self):
        while True:
            file = QtGui.QFileDialog.getOpenFileName(self, 'Open SysEx sound file', QtGui.QDesktopServices.storageLocation(QtGui.QDesktopServices.HomeLocation), 'SysEx files (*.syx);; All files (*)')
            if not file: return
            if not file_exists(str(file)):
                QtGui.QMessageBox.warning(self, 'File does not exists', 'The selected does not exist.\nCheck the file name and path.')
            elif file_stat(file).st_size != 392:
                QtGui.QMessageBox.warning(self, 'Wrong file size', 'The selected file does not seem to be a Blofeld Sound file.\nTry with another file.')
            else:
                try:
                    with open(file, 'rb') as sf:
                        sysex = list(ord(i) for i in sf.read())
                    break
                except:
                    QtGui.QMessageBox.warning(self, 'Unexpected error', 'Something is wrong with the selected file...\nTry with another one.')
        self.show()
        self.setSound(Sound(sysex[5:-2]), source=file)

    def sound_edit(self):
        self.main.editor.setSoundDump(self.sound)
        self.main.editor.show()

    def sound_dump(self):
        if self.sound_buffer_radio.isChecked():
            self.sound.bank = 0x7f
            self.sound.prog = 0x00
            self.dump_send.emit(self.sound)
            self.accept()
        elif self.multi_buffer_radio.isChecked():
            self.sound.bank = 0x7f
            self.sound.prog = self.multi_spin.value() - 1
            self.dump_send.emit(self.sound)
            self.accept()
        else:
            res = QtGui.QMessageBox.warning(
                                       self, 'Confirm sound dump', 
                                       'You are about to dump a sound to the Blofeld\'s memory at index {}{:03}, overwriting the existing sound.\n\nDo you want to proceed?'.format(uppercase[self.bank_combo.currentIndex()], self.prog_spin.value()), 
                                       QtGui.QMessageBox.Ok|QtGui.QMessageBox.Cancel
                                       )
            if res == QtGui.QMessageBox.Ok:
                self.sound.bank = self.bank_combo.currentIndex()
                self.sound.prog = self.prog_spin.value() - 1
                self.dump_send.emit(self.sound)
                self.accept()
        

    def setSound(self, sound, source=None):
        self.sound = sound
        data = sound.data
        bank = sound.bank
        prog = sound.prog
        if (bank, prog) == SMEB:
            self.sound_buffer_radio.setChecked(True)
        elif bank == 0x7f:
            self.multi_buffer_radio.setChecked(True)
            self.multi_spin.setValue(prog+1)
        else:
            self.bank_combo.setCurrentIndex(bank)
            self.prog_spin.setValue(prog+1)
        self.name_lbl.setText(''.join([str(unichr(l)) for l in data[363:379]]))
        if source:
            try:
                self.source_lbl.setEllipsisText(source)
            except Exception as e:
                print e
        else:
            self.source_lbl.setText('Local library' if sound.source == SRC_LIBRARY else 'Blofeld dump')
        self.show()
        self.summary_widget.setSoundData(sound.data)





