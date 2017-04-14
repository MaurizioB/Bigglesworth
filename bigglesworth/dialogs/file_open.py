# *-* coding: utf-8 *-*

from PyQt5 import QtCore, QtWidgets

from bigglesworth.classes import Sound
from bigglesworth.const import MIDFILE, SYXFILE
from bigglesworth import midifile


ALLFILE = MIDFILE|SYXFILE
_file_types = {
               ALLFILE: 'Sound files (*.mid, *.syx)(*.mid *.syx)', 
               MIDFILE: 'MIDI files (*.mid)', 
               SYXFILE: 'SysEx files (*.syx)', 
               }
_titles = {
           ALLFILE: 'Import sound file', 
           MIDFILE: 'Import MIDI sound set', 
           SYXFILE: 'Import SysEx sound file'
           }

nomidi_msgbox = lambda parent: QtWidgets.QMessageBox.warning(
                                                         parent, 'MIDI import', 
                                                         'The selected MIDI file does not seem to contain any sounds.'
                                                         )

nosysex_msgbox = lambda parent: QtWidgets.QMessageBox.warning(
                                                          parent, 'SysEx import', 
                                                          'The selected SysEx file does not seem to be a Blofeld sound.'
                                                          )

none_msgbox = lambda parent: QtWidgets.QMessageBox.warning(
                                                       parent, 'Sound import', 
                                                       'The selected file does not seem to be a Blofeld compatible file.'
                                                       )

_factory = QtCore.QUrl.fromLocalFile(QtCore.QDir.currentPath()+'/bigglesworth/presets')
_midi_sets = QtCore.QUrl.fromLocalFile(QtCore.QDir.currentPath()+'/bigglesworth/sounds/sets')
_single_sets = QtCore.QUrl.fromLocalFile(QtCore.QDir.currentPath()+'/bigglesworth/sounds/single')

class FileOpen(QtWidgets.QFileDialog):
    def __init__(self, mode=ALLFILE, *args, **kwargs):
        QtWidgets.QFileDialog.__init__(self, *args, **kwargs)
        if mode == ALLFILE:
            self.setNameFilters([_file_types[ALLFILE], _file_types[MIDFILE], _file_types[SYXFILE], 'Any files (*)'])
        else:
            self.setNameFilters([_file_types[mode], 'Any files (*)'])
        self.mode = mode
        self.res = None
        self.setWindowTitle(_titles[mode])
        self.setFileMode(QtWidgets.QFileDialog.ExistingFile)
        self.setOption(QtWidgets.QFileDialog.HideNameFilterDetails, True)
        self.setAcceptMode(QtWidgets.QFileDialog.AcceptOpen)
        self.setFileMode(QtWidgets.QFileDialog.ExistingFile)
        self.setDirectory(QtCore.QDir.homePath())
        urls = []
        if mode == MIDFILE|SYXFILE:
            urls.append(_factory)
        if mode & MIDFILE:
            urls.append(_midi_sets)
        if mode & SYXFILE:
            urls.append(_single_sets)
        self.setSidebarUrls(urls)
        buttonBox = self.findChildren(QtWidgets.QDialogButtonBox)[0]
        buttonBox.removeButton(buttonBox.button(QtWidgets.QDialogButtonBox.Open))
        self.import_btn = QtWidgets.QPushButton('Import')
        self.import_btn.clicked.connect(self.accept)
        self.import_btn.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DialogOpenButton))
        buttonBox.addButton(self.import_btn, QtWidgets.QDialogButtonBox.ActionRole)

        self.currentChanged.connect(lambda path: self.import_btn.setText('Open' if QtCore.QFileInfo(path).isDir() else 'Import'))

    def accept(self):
        if not self.selectedFiles(): return
        path = self.selectedFiles()[0]
        stats = QtCore.QFileInfo(path)
        if stats.isDir():
            self.setDirectory(path)
            return
        if not stats.exists():
            return
        if self.mode & MIDFILE:
            sound_list = []
            try:
                pattern = midifile.read_midifile(path)
                for track in pattern:
                    for event in track:
                        if isinstance(event, midifile.SysexEvent) and len(event.data) == 392:
                            sound_list.append(Sound(event.data[6:391]))
                if sound_list:
                    self.res = sound_list, path
                    return QtWidgets.QFileDialog.accept(self)
                elif self.mode == MIDFILE:
                    nomidi_msgbox(self)
                    return
            except:
                if self.mode == MIDFILE:
                    nomidi_msgbox(self)
                    return
        if self.mode & SYXFILE:
            try:
                with open(path, 'rb') as sf:
                    sysex = list(ord(i) for i in sf.read())
                if len(sysex) == 392:
                    self.res = Sound(sysex[5:-2]), path
                    return QtWidgets.QFileDialog.accept(self)
                elif self.mode == SYXFILE:
                    nosysex_msgbox(self)
                    return
            except:
                if self.mode == SYXFILE:
                    nosysex_msgbox(self)
                    return
        none_msgbox(self)
        return

    def exec_(self):
        res = QtWidgets.QFileDialog.exec_(self)
        if not res: return
        return self.res
        


class MidOpen(FileOpen):
    def __init(self, *args, **kwargs):
        FileOpen.__init__(MIDFILE, *args, **kwargs)


class SyxOpen(FileOpen):
    def __init(self, *args, **kwargs):
        FileOpen.__init__(SYXFILE, *args, **kwargs)



