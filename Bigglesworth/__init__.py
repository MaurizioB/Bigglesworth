#!/usr/bin/env python2.7
# *-* coding: utf-8 *-*

import sys
from string import uppercase
from PyQt4 import QtCore, QtGui

from alsa import *
from midiutils import *
from utils import *
from classes import *
from const import *
from utils import *

from editor import Editor

class Librarian(QtGui.QMainWindow):
    dump_waiter = QtCore.pyqtSignal()
    def __init__(self, parent=None):
        QtGui.QMainWindow.__init__(self, parent=None)
        load_ui(self, 'main.ui')

        self.alsa_thread = QtCore.QThread()
        self.alsa = AlsaMidi(self)
        self.alsa.moveToThread(self.alsa_thread)
        self.alsa.stopped.connect(self.alsa_thread.quit)
        self.alsa_thread.started.connect(self.alsa.run)
        self.alsa.midi_signal.connect(self.alsa_midi_event)
        self.alsa.port_start.connect(self.new_alsa_port)
        self.alsa.conn_register.connect(self.alsa_conn_event)
        self.alsa_thread.start()
        self.seq = self.alsa.seq
        self.input = self.alsa.input
        self.output = self.alsa.output

        self.blofeld_current = None, None
        self.loading_win = LoadingWindow(self)
        self.loading_complete = False
        self.blofeld_library = Library()
        self.editor = Editor(self)
        self.edit_mode = False

        self.dump_timer = QtCore.QTimer()
        self.dump_timer.setInterval(100)
        self.dump_timer.setSingleShot(True)
        self.dump_timer.timeout.connect(lambda: self.dump_waiter.emit())

        self.dump_active = False
        self.dump_elapsed = QtCore.QElapsedTimer()
        self.dump_win = DumpWin(self)
        self.dump_win.rejected.connect(lambda: setattr(self, 'dump_active', False))
        self.dump_win.rejected.connect(self.dump_timer.stop)

        self.create_models()
        self.midi_connect()

        self.device_btn.clicked.connect(self.device_request)
        self.dump_btn.clicked.connect(self.dump_request)
        self.bank_dump_combo.currentIndexChanged.connect(lambda b: self.sound_dump_combo.setEnabled(True if b != 0 else False))
        self.edit_btn.toggled.connect(self.edit_mode_set)
        self.search_edit.textChanged.connect(self.search_filter)
        self.search_clear_btn.clicked.connect(lambda _: self.search_edit.setText(''))
        self.search_filter_chk.toggled.connect(self.search_filter_set)
        self.blofeld_sounds_table.doubleClicked.connect(self.sound_doubleclick)
        self.blofeld_sounds_table.mouseReleaseEvent = self.right_click
        self.blofeld_sounds_table.dropEvent = self.sound_drop_event
#        self.blofeld_model.dataChanged.connect(self.sound_update)
#        self.blofeld_model.itemChanged.connect(self.sound_update)
        self.installEventFilter(self)

    def showEvent(self, event):
        if not self.loading_win.isVisible() and not self.loading_complete:
            QtCore.QTimer.singleShot(10, self.loading_win.show)

    def eventFilter(self, source, event):
        if event.type() == QtCore.QEvent.KeyPress and event.key() == QtCore.Qt.Key_F5:
            self.dump_request()
        return QtGui.QMainWindow.eventFilter(self, source, event)


    def edit_mode_set(self, state):
        self.edit_mode = state
        self.blofeld_sounds_table.setEditTriggers(QtGui.QTableView.DoubleClicked|QtGui.QTableView.EditKeyPressed if state else QtGui.QTableView.NoEditTriggers)
        self.blofeld_sounds_table.setDragEnabled(False if state else True)
        self.blofeld_sounds_table.setSelectionMode(QtGui.QTableView.SingleSelection if state else QtGui.QTableView.ContiguousSelection)

    def search_filter_set(self, state):
        return
        if not state:
            self.filter_update()

    def search_filter(self, text):
        filter =  self.search_filter_chk.isChecked()
        if not text and not filter: return
        found = self.blofeld_model.findItems(text, QtCore.Qt.MatchContains, 3)
        if not filter:
            if found:
                self.blofeld_sounds_table.selectRow(found[0].row())
            return
        self.blofeld_model_proxy.setTextFilter(text)

    def sound_doubleclick(self, index):
        if self.edit_mode: return
        sound = self.blofeld_model.item(self.blofeld_model_proxy.mapToSource(index).row(), SOUND).data(SoundRole).toPyObject()
        self.output_event(CtrlEvent(1, 0, 0, sound.bank))
#        bank_req.source = self.seq.client_id, 1
        self.output_event(ProgramEvent(1, 0, sound.prog))
#        prog_req.source = self.seq.client_id, 1
#        self.seq.output_event(bank_req.get_event())
#        self.seq.output_event(prog_req.get_event())
#        self.seq.drain_output()

    def right_click(self, event):
        if event.button() != QtCore.Qt.RightButton: return
        index = self.blofeld_sounds_table.indexAt(event.pos())
        sound = self.blofeld_model.item(self.blofeld_model_proxy.mapToSource(index).row(), SOUND).data(SoundRole).toPyObject()
        menu = QtGui.QMenu()
        menu.setSeparatorsCollapsible(False)
        header = QtGui.QAction(sound.name, self)
        header.setSeparator(True)
        menu.addAction(header)
        edit_item = QtGui.QAction('Edit...', self)
        menu.addAction(edit_item)
        menu.show()
        fm = QtGui.QFontMetrics(edit_item.font())
        minsize = 0
        for a in menu.actions():
            if a == header: continue
            width = fm.width(a.text())
            if width > minsize:
                minsize = width
        frame_delta = menu.width()-minsize
        menu.setMinimumWidth(frame_delta+QtGui.QFontMetrics(header.font()).width(header.text()))
        res = menu.exec_(event.globalPos())
        if res == edit_item:
            self.editor.show()
            self.editor.setData(sound.data)

    def sound_drop_event(self, event):
        def rename(sound_range):
#            first, last = sorted(sound_range)
            first = min(sound_range)
            last = max(sound_range)
            print first, last
            for row in range(first, last+1):
                bank, prog = divmod(row, 128)
                sound = self.blofeld_library[bank, prog]
                sound.prog += 1
#                sound.bank, sound.prog = divmod(row+1, 128)
                self.blofeld_model.item(row, BANK).setText(uppercase[sound.bank])
                self.blofeld_model.item(row, PROG).setText('{:03}'.format(sound.prog+1))
#                self.blofeld_model.item(row, 0).setText(str(row+1))
#                sound = self.blofeld_model.item(row, SOUND).data(SoundRole).toPyObject()
#                sound.prog, sound.bank = divmod(row, 128)
                
#                bank = index_item.data(SoundRole).toPyObject()/128
#                self.blofeld_model.item(row, 0).setData(bank*128+row, SoundRole)
        drop_pos = self.blofeld_sounds_table.dropIndicatorPosition()
        rows = set([self.blofeld_model_proxy.mapToSource(index).row() for index in self.blofeld_sounds_table.selectedIndexes()])
        current_bank = self.bank_filter_combo.currentIndex() - 1
        if len(rows) == 1:
            source = self.blofeld_model_proxy.mapToSource(self.blofeld_sounds_table.currentIndex()).row()
            if drop_pos == QtGui.QTableView.OnViewport:
                if current_bank < 0:
                    target = self.blofeld_model.rowCount()-1
                else:
                    target = 127 + current_bank * 128
            else:
                target = self.blofeld_model_proxy.mapToSource(self.blofeld_sounds_table.indexAt(event.pos())).row()
            items = self.blofeld_model.takeRow(source)
            self.blofeld_model.insertRow(target, items)
            rename((source, target))
        else:
            if drop_pos == QtGui.QTableView.OnViewport:
                if current_bank < 0:
                    if max(rows) == self.blofeld_model.rowCount()-1: return
                    target = self.blofeld_model.rowCount()-1
                else:
                    target = 127 + current_bank * 128
            else:
                target = self.blofeld_model_proxy.mapToSource(self.blofeld_sounds_table.indexAt(event.pos())).row()
                if target in rows: return
            first = min(rows)
            before = True if target < first else False
            for d in range(max(rows)+1-first):
                items = self.blofeld_model.takeRow(first)
                self.blofeld_model.insertRow(target if not before else target+d, items)
            rename((target, )+tuple(rows))

#        self.blofeld_model.sort(2)
#        self.blofeld_model.sort(1)


    def sound_update(self, item, _=None):
#        print 'updating {}'.format(item.column())
#        print self.sender()
        if item.column() == STATUS:
            item.setText(get_status(item.data(EditedRole).toPyObject()))
            setBold(item)

    def midi_connect(self):
        for cid, client in self.graph.client_id_dict.items():
            if client.name == 'Blofeld':
                self.graph.port_id_dict[cid][0].connect(self.seq.client_id, self.input.id)
                self.graph.port_id_dict[self.seq.client_id][self.output.id].connect(cid, 0)
                break

    def output_event(self, event):
        alsa_event = event.get_event()
        alsa_event.source = self.output.client.id, self.output.id
        self.seq.output_event(alsa_event)
        self.seq.drain_output()


    def device_request(self):
        req = SysExEvent(1, [0xF0, 0x7e, 0x7f, 0x6, 0x1, 0xf7])
        req.source = self.seq.client_id, 1
        self.seq.output_event(req.get_event())
        self.seq.drain_output()

    def dump_request(self):
        bank = self.bank_dump_combo.currentIndex()
        sound = self.sound_dump_combo.currentIndex()
        if bank != 0 and sound != 0:
            self.sound_request(bank-1, sound-1)
        elif bank != 0 and sound == 0:
            self.dump_active = True
            self.dump_elapsed.start()
            self.dump_win.show()
            self.dump_win.progress.setMaximum(128)
            self.sound_request(bank-1, 0)
        else:
            self.dump_active = True
            self.dump_elapsed.start()
            self.dump_win.show()
            self.dump_win.progress.setMaximum(1024)
            self.sound_request(0, 0)
        

    def sound_request(self, bank, sound):
        req = SysExEvent(1, [0xF0, 0x3e, 0x13, 0x0, 0x0, bank, sound, 0x7f, 0xf7])
        req.source = self.seq.client_id, 1
        self.seq.output_event(req.get_event())
        self.seq.drain_output()

    def create_models(self):
        self.bank_dump_combo.addItems(['All']+[l for l in uppercase[:8]])
        self.sound_dump_combo.addItems(['All']+[str(s) for s in range(1, 129)])

        self.bank_filter_combo.addItems(['All']+[l for l in uppercase[:8]])
        self.cat_filter_combo.addItem('All')
        for cat in categories:
            self.cat_filter_combo.addItem(cat, cat)
        self.bank_filter_combo.currentIndexChanged.connect(lambda index: self.blofeld_model_proxy.setMultiFilter(BANK, index))
        self.bank_filter_combo.currentIndexChanged.connect(self.bank_list_update)
        self.cat_filter_combo.currentIndexChanged.connect(lambda index: self.blofeld_model_proxy.setMultiFilter(CATEGORY, index))

    def set_models(self, model, library):
        self.loading_complete = True
        self.blofeld_library = library
        self.blofeld_model = model
        self.blofeld_model.setHorizontalHeaderLabels(sound_headers)
        self.blofeld_model.itemChanged.connect(self.sound_update)
        self.blofeld_model_proxy = LibraryProxy()
        self.blofeld_model_proxy.setSourceModel(self.blofeld_model)
        self.blofeld_sounds_table.setModel(self.blofeld_model_proxy)
        self.blofeld_sounds_table.horizontalHeader().setResizeMode(QtGui.QHeaderView.ResizeToContents)
        self.blofeld_sounds_table.horizontalHeader().setResizeMode(NAME, QtGui.QHeaderView.Stretch)
        self.blofeld_sounds_table.verticalHeader().setResizeMode(QtGui.QHeaderView.ResizeToContents)
        self.blofeld_sounds_table.setItemDelegateForColumn(4, CategoryDelegate(self))
        self.blofeld_sounds_table.setColumnHidden(INDEX, True)
        for c in range(len(sound_headers), self.blofeld_model.columnCount()):
            self.blofeld_sounds_table.setColumnHidden(c, True)
        self.blofeld_sounds_table.horizontalHeader().setResizeMode(PROG, QtGui.QHeaderView.Fixed)
        self.blofeld_sounds_table.resizeColumnToContents(PROG)


    def bank_list_update(self, bank):
        self.cat_count_update()

    def filter_update(self, id=None):
        bank_filter = self.bank_filter_combo.currentIndex()
        cat_filter = self.cat_filter_combo.currentIndex()
        self.blofeld_model_proxy.setMultiFilter(bank_filter-1, cat_filter-1)
        return
        print 'filtering with {} and {}'.format(bank_filter, cat_filter)
        if bank_filter == 0 and cat_filter == 0:
            for r in range(self.blofeld_model.rowCount()):
                self.blofeld_sounds_table.setRowHidden(r, False)
            print 'done'
            return
        print 'what'
        for r in range(self.blofeld_model.rowCount()):
            self.blofeld_sounds_table.setRowHidden(
                                                   r, 
                                                   False if (
                                                             bank_filter == 0 or self.blofeld_model.index(r, 0).data(BankRole).toPyObject() == bank_filter-1
                                                             ) and (
                                                             cat_filter == 0 or self.blofeld_model.index(r, 4).data(CatRole).toPyObject() == cat_filter-1
                                                             ) else True
                                                   )

    def cat_count_update(self):
        cat_len = [0 for cat_id in categories]
        current_bank = self.bank_filter_combo.currentIndex()
        return
        for bank, sound_list in enumerate(self.blofeld_library):
            if current_bank != 0 and current_bank != bank+1: continue
            for s in sound_list:
                if s.data is None: continue
                cat_len[s.cat] += 1
        for cat_id in range(1, self.cat_filter_combo.model().rowCount()):
            self.cat_filter_combo.setItemText(cat_id, '{} ({})'.format(
                                               self.cat_filter_combo.model().item(cat_id).data(QtCore.Qt.UserRole).toPyObject(),
                                               cat_len[cat_id-1]
                                               ))


    def alsa_midi_event(self, event):
#        print 'receiving event: {}'.format(event)
        if event.type == SYSEX:
            if event.sysex[4] == SNDD:
                self.sound_dump(event)
            elif len(event.sysex) == 15 and event.sysex[3:5] == [6, 2]:
                self.device_response(event.sysex)
        elif event.type == CTRL and event.data1 == 0:
            self.blofeld_current = event.data2, self.blofeld_current[1]
        elif event.type == PROGRAM:
            self.blofeld_current = self.blofeld_current[0], event.data2

    def device_response(self, sysex):
        if sysex[5] == 0x3e:
            dev_man = 'Waldorf Music'
        else:
            dev_man = 'Unknown'
        if sysex[6:8] == [0x13, 0x0]:
            dev_model = 'Blofeld'
        else:
            dev_model = 'Unknown'
        if sysex[8:10] == [0, 0]:
            dev_type = 'Blofeld Desktop'
        else:
            dev_type = 'Blofeld Keyboard'
        dev_version = ''.join([str(unichr(l)) for l in sysex[10:14]]).strip()
        
        QtGui.QMessageBox.information(self, 'Device informations', 
                                      'Device info:\n\nManufacturer: {}\nModel: {}\nType: {}\nVersion: {}'.format(
                                       dev_man, dev_model, dev_type, dev_version))


    def sound_dump(self, sound_event):
        sound = Sound(sound_event.sysex[5:390], SRC_BLOFELD)
        if sound.bank > 25:
            if None in self.blofeld_current:
                #you'll ask what to do with incoming sysex, we don't know where it goes
                print 'no current sound selected'
                return
            else:
                sound._bank, sound._prog = self.blofeld_current
        bank, prog = sound.bank, sound.prog
        self.blofeld_library.addSound(sound)

        self.cat_count_update()
        self.blofeld_sounds_table.resizeColumnToContents(2)
        if not self.dump_active: return
        dump_all = True if self.bank_dump_combo.currentIndex()==0 else False
        if prog >= 127:
            if dump_all:
                bank += 1
                if bank >= 8:
                    self.dump_active = False
                    self.dump_win.done(1)
                    return
                prog = -1
            else:
                self.dump_active = False
                self.dump_win.accept()
                return
        self.dump_win.bank_lbl.setText('{}{}'.format(uppercase[bank], ' {}/8'.format(bank+1) if dump_all else ''))
        self.dump_win.sound_lbl.setText('{:03}/{}'.format(prog+1+(128*bank if dump_all else 0), 1024 if dump_all else 128))
        dump_time = None
        if dump_all:
            if not (bank == 0 and prog < 10):
                dump_time = self.dump_elapsed.elapsed()/float(prog+1+128*bank)*(1024-prog-128*bank)/1000
        else:
            if prog > 5:
                dump_time = self.dump_elapsed.elapsed()/float(prog+1)*(128-prog)/1000
        if dump_time is not None:
            self.dump_win.time.setText('{}:{:02}'.format(*divmod(int(dump_time)+1, 60)))
        self.dump_win.progress.setValue(prog+1+(128*bank if dump_all else 0))
        self.dump_timer.timeout.disconnect()
        self.dump_timer.timeout.connect(lambda: self.sound_request(bank, prog+1))
        self.dump_timer.start()
#        QtCore.QTimer.singleShot(200, lambda: self.sound_request(0, prog+1))


    def new_alsa_port(self, port):
        pass

    def alsa_conn_event(self, conn, state):
        pass


def main():
    app = QtGui.QApplication(sys.argv)
    app.setOrganizationName('jidesk')
    app.setApplicationName('Blofix')
#    app.setQuitOnLastWindowClosed(False)
    blofix = Librarian(app)
    blofix.show()
    sys.exit(app.exec_())
    print 'Blofix has been quit!'

if __name__ == '__main__':
    main()









