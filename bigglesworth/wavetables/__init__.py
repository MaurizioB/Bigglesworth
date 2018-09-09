#!/usr/bin/env python2.7
# *-* encoding: utf-8 *-*

import sys, os
from itertools import chain
from xml.etree import ElementTree as ET
from uuid import uuid4

import numpy as np
from unidecode import unidecode
os.environ['QT_PREFERRED_BINDING'] = 'PyQt4'

sys.path.append('../..')

from Qt import QtCore, QtGui, QtWidgets, QtSql

#from PyQt4.uic import loadUi
#from dial import _Dial

#from collections import OrderedDict, namedtuple
#
#polyPoints = namedtuple('polyPoints', 'topLeft topRight bottomRight bottomLeft')
UidColumn, NameColumn, SlotColumn, EditedColumn, DataColumn, PreviewColumn, DumpedColumn = range(7)

try:
    from Qt import QtMultimedia
#    from bigglesworth.wavetables.waveplay import Player, AudioSettingsDialog
#    from audiosettings import AudioSettingsDialog
    QTMULTIMEDIA = True
except:
    QTMULTIMEDIA = False


#import soundfile

from bigglesworth.libs import midifile
#from bigglesworth.mididevice import MidiDevice
from bigglesworth.utils import loadUi, setItalic
from bigglesworth.midiutils import SysExEvent, NoteOnEvent, NoteOffEvent, NOTEOFF, NOTEON

from bigglesworth.const import INIT, END, CHK, IDW, IDE, WTBD
from bigglesworth.parameters import oscShapes
from bigglesworth.dialogs.messageboxes import AdvancedMessageBox
from bigglesworth.widgets import MidiStatusBarWidget

#from bigglesworth.wavetables.utils import baseSineValues, sineValues, noteFrequency

from bigglesworth.wavetables.utils import pow20, pow21, fixFileName, sineValues, parseTime
#from bigglesworth.wavetables.dialogs import Dumper, AudioSettingsDialog, SetIndexDialog
from bigglesworth.wavetables.dialogs import Dumper, SetIndexDialog, CurveMorphDialog

if QTMULTIMEDIA:
    from bigglesworth.wavetables.waveplay import Player, AudioSettingsDialog

class UndoStack(QtWidgets.QUndoStack):
    indexesChanged = QtCore.pyqtSignal(object)


class FreeDrawUndo(QtWidgets.QUndoCommand):
    done = False
    def __init__(self, main, keyFrame, sample, newValue, buttonTimer):
        QtWidgets.QUndoCommand.__init__(self)
        self.main = main
        self.keyFrames = main.keyFrames
        self.index = keyFrame.index
        self.oldValues = keyFrame.values[:]
        if isinstance(sample, int):
            self.newValues = {sample: newValue}
        else:
            self.newValues = {s:v for s, v in zip(sample, newValue)}
        self.buttonTimer = buttonTimer
        self.timer = QtCore.QElapsedTimer()
        self.timer.start()
        self.setText('Free draw on wave {}'.format(self.index + 1))

    def id(self):
        return 1

    def mergeWith(self, other):
        if self.buttonTimer != other.buttonTimer and self.timer.msecsTo(other.timer) > 5000:
            return False
        self.timer = other.timer
        self.buttonTimer = other.buttonTimer
        self.newValues.update(other.newValues)
        return True

    def redo(self):
        self.keyFrames.setValues(self.index, self.newValues)

    def undo(self):
        self.keyFrames.setValues(self.index, self.oldValues)


class GenericDrawUndo(QtWidgets.QUndoCommand):
    def __init__(self, main, mouseMode, keyFrame, newValues):
        QtWidgets.QUndoCommand.__init__(self)
        self.main = main
        self.keyFrames = main.keyFrames
        self.mouseMode = mouseMode
        self.index = keyFrame.index
        self.oldValues = keyFrame.values[:]
        self.newValues = newValues
        self.setText(self.labels[mouseMode].format(self.index + 1))

    def id(self):
        return self.mouseMode

    def redo(self):
        self.keyFrames.setValues(self.index, self.newValues)

    def undo(self):
        self.keyFrames.setValues(self.index, self.oldValues)


class WaveUndo(QtWidgets.QUndoCommand):
    def __init__(self, main, mode, keyFrame, values):
        self.index = keyFrame.index
        QtWidgets.QUndoCommand.__init__(self, self.labels[mode].format(self.index + 1))
        self.main = main
        self.keyFrames = main.keyFrames
        self.mode = mode
        self.oldValues = keyFrame.values[:]
        self.newValues = values

    def redo(self):
        self.keyFrames.setValues(self.index, self.newValues)

    def undo(self):
        self.keyFrames.setValues(self.index, self.oldValues)


class KeyFrameUndo(QtWidgets.QUndoCommand):
    done = False
    oldIndexes = newIndexes = None

    def __init__(self, main, text=''):
        QtWidgets.QUndoCommand.__init__(self, text)
        self.main = main
        self.keyFrames = main.keyFrames
        self.undoStack = main.undoStack

    def checkIndexes(self, before, after):
        if not (before and after):
            return
        changed = {}
        for uuid, oldIndex in before.items():
            if uuid in after:
                if after[uuid] != oldIndex:
                    changed[uuid] = after[uuid]
            else:
                changed[uuid] = None
        if changed:
            self.undoStack.indexesChanged.emit(changed)

    def redo(self):
        self.keyFrames.setSnapshot(self.newState)
        self.checkIndexes(self.oldIndexes, self.newIndexes)

    def undo(self):
        self.keyFrames.setSnapshot(self.oldState)
        self.checkIndexes(self.newIndexes, self.oldIndexes)


class CreateKeyFrameUndo(KeyFrameUndo):
    def __init__(self, main, index, values, after):
        KeyFrameUndo.__init__(self, main)
        self.index = index
        self.values = values
        self.after = after

    def redo(self):
        if not self.done:
            self.oldIndexes = self.keyFrames.getUuidDict()
            self.oldState = self.keyFrames.getSnapshot()
            self.keyFrame = self.keyFrames.createAt(self.index, self.values, self.after)
            self.newState = self.keyFrames.getSnapshot()
            self.done = True
            self.setText('Wave created at index {}'.format(self.keyFrame.index + 1))
            self.newIndexes = self.keyFrames.getUuidDict()
            self.checkIndexes(self.oldIndexes, self.newIndexes)
        else:
            KeyFrameUndo.redo(self)


class MoveKeyFramesUndo(KeyFrameUndo):
    def __init__(self, main, keyFrameList, newIndex):
        if len(keyFrameList) == 1:
            text = 'Wave moved to index {}'.format(newIndex + 1)
        else:
            text = 'Waves {} to {} move to index {}'.format(keyFrameList[0].index, keyFrameList[-1].index, newIndex)
        KeyFrameUndo.__init__(self, main, text)
        self.keyFrameList = keyFrameList
#        self.oldIndex = keyFrame.index
        self.newIndex = newIndex

    def redo(self):
        if not self.done:
            self.oldIndexes = self.keyFrames.getUuidDict()
            self.oldState = self.keyFrames.getSnapshot()
            self.keyFrames.moveKeyFrames(self.keyFrameList, self.newIndex)
            self.newState = self.keyFrames.getSnapshot()
            self.done = True
            self.newIndexes = self.keyFrames.getUuidDict()
            self.checkIndexes(self.oldIndexes, self.newIndexes)
        else:
            KeyFrameUndo.redo(self)


class RemoveWavesUndo(KeyFrameUndo):
    def __init__(self, main, items):
        KeyFrameUndo.__init__(self, main, '{} wave{} removed'.format(len(items), 's' if len(items) > 1 else ''))
        self.items = items

    def redo(self):
        if not self.done:
            self.oldIndexes = self.keyFrames.getUuidDict()
            self.oldState = self.keyFrames.getSnapshot()
            if len(self.items) > 1:
                self.keyFrames.deleteKeyFrames(self.items)
            else:
                self.keyFrames.deleteKeyFrame(self.items[0])
            self.newState = self.keyFrames.getSnapshot()
            self.done = True
            self.newIndexes = self.keyFrames.getUuidDict()
            self.checkIndexes(self.oldIndexes, self.newIndexes)
        else:
            KeyFrameUndo.redo(self)


class MergeWavesUndo(KeyFrameUndo):
    def __init__(self, main, start, end):
        KeyFrameUndo.__init__(self, main, 'Waves {} to {} merged'.format(start + 1, end + 1))
        self.start = start
        self.end = end

    def redo(self):
        if not self.done:
            self.oldIndexes = self.keyFrames.getUuidDict()
            self.oldState = self.keyFrames.getSnapshot()
            self.keyFrames.merge(self.start, self.end)
            self.newState = self.keyFrames.getSnapshot()
            self.done = True
            self.newIndexes = self.keyFrames.getUuidDict()
            self.checkIndexes(self.oldIndexes, self.newIndexes)
        else:
            KeyFrameUndo.redo(self)


class RemoveTransformUndo(KeyFrameUndo):
    def __init__(self, main, transform):
        KeyFrameUndo.__init__(self, main, 'Orphan transform removed')
        self.transform = transform

    def redo(self):
        if not self.done:
            self.oldState = self.keyFrames.getSnapshot()
            self.keyFrames.deleteTransform(self.transform)
            self.newState = self.keyFrames.getSnapshot()
            self.done = True
        else:
            KeyFrameUndo.redo(self)


class GenericValuesUndo(KeyFrameUndo):
    def __init__(self, main, start, data, fromFile=False, isDrop=True):
        KeyFrameUndo.__init__(self, main)
        self.start = start
        self.data = data
        self.fromFile = fromFile
        self.isDrop = isDrop

    def redo(self):
        if not self.done:
            self.done = True
            self.oldIndexes = self.keyFrames.getUuidDict()
            self.oldState = self.keyFrames.getSnapshot()
            self.keyFrames.setValuesMulti(self.start, self.data, self.fromFile)
            self.newState = self.keyFrames.getSnapshot()
            self.newIndexes = self.keyFrames.getUuidDict()
            self.checkIndexes(self.oldIndexes, self.newIndexes)
            if len(self.data) > 1:
                text = 'Waves {} to {} '.format(self.start + 1, self.start + len(self.data) + 1)
            else:
                text = 'Wave '
            if self.fromFile:
                if self.isDrop:
                    text += 'dropped from file "{}"'
                else:
                    text += 'pasted from file "{}"'
                self.setText(text.format(QtCore.QFileInfo(self.fromFile).fileName()))
            else:
                self.setText(text + 'pasted')
        else:
            KeyFrameUndo.redo(self)


class AdvancedValuesUndo(KeyFrameUndo):
    def __init__(self, main, dropData, values, fromFile):
        KeyFrameUndo.__init__(self, main)
        self.dropData = dropData
        self.values = values
        self.fromFile = fromFile

    def redo(self):
        if not self.done:
            self.done = True
            self.oldIndexes = self.keyFrames.getUuidDict()
            self.oldState = self.keyFrames.getSnapshot()
            self.keyFrames.setValuesFromDrop(self.values, self.dropData, self.fromFile)
            self.newState = self.keyFrames.getSnapshot()
            self.newIndexes = self.keyFrames.getUuidDict()
            self.checkIndexes(self.oldIndexes, self.newIndexes)
            count = self.dropData[0]
            text = '{} wave{} dropped'.format(count, 's' if count > 1 else '')
            if self.fromFile:
                text += 'dropped from file "{}"'.format(QtCore.QFileInfo(self.fromFile).fileName())
        else:
            KeyFrameUndo.redo(self)


class DropSelectionUndo(KeyFrameUndo):
    def __init__(self, main, dropData, data, sourceName):
        count = len(dropData[0])
        KeyFrameUndo.__init__(self, main, '{} wave{} dropped from WaveTable "{}"'.format(
            count, 's' if count > 1 else '', sourceName))
        self.dropData = dropData
        self.data = data
        self.sourceName = sourceName

    def redo(self):
        if not self.done:
            self.done = True
            self.oldIndexes = self.keyFrames.getUuidDict()
            self.oldState = self.keyFrames.getSnapshot()
            self.keyFrames.setDataFromDropSelection(self.data, self.dropData)
            self.newState = self.keyFrames.getSnapshot()
            self.newIndexes = self.keyFrames.getUuidDict()
            self.checkIndexes(self.oldIndexes, self.newIndexes)
        else:
            KeyFrameUndo.redo(self)


class DistributeWaveTableUndo(KeyFrameUndo):
    def __init__(self, main, start, end):
        if (start, end) == (0, 63):
            text = 'Waves equally distributed'
        else:
            text = 'Waves {} to {} equally distributed'.format(start + 1, end)
        KeyFrameUndo.__init__(self, main, text)
        self.start = start
        self.end = end

    def id(self):
        return pow20

    def redo(self):
        if not self.done:
            self.done = True
            self.oldIndexes = self.keyFrames.getUuidDict()
            self.oldState = self.keyFrames.getSnapshot()
            self.keyFrames.distribute(self.start, self.end)
            self.newState = self.keyFrames.getSnapshot()
            self.newIndexes = self.keyFrames.getUuidDict()
            self.checkIndexes(self.oldIndexes, self.newIndexes)
        else:
            KeyFrameUndo.redo(self)

    def mergeWith(self, other):
        if isinstance(other, DistributeWaveTableUndo) and self.start == other.start and self.end == other.end:
            self.newState = other.newState
            self.newIndexes = other.newIndexes
            return True
        return False


class ReverseWaveTableUndo(KeyFrameUndo):
    def __init__(self, main, start, end):
        KeyFrameUndo.__init__(self, main, 'Wavetable reversed')
        self.start = start
        self.end = end

    def redo(self):
        if not self.done:
            self.done = True
            self.oldIndexes = self.keyFrames.getUuidDict()
            self.oldState = self.keyFrames.getSnapshot()
            self.keyFrames.reverse(self.start, self.end)
            self.newState = self.keyFrames.getSnapshot()
            self.newIndexes = self.keyFrames.getUuidDict()
            self.checkIndexes(self.oldIndexes, self.newIndexes)
        else:
            KeyFrameUndo.redo(self)


class LocalProxyModel(QtCore.QSortFilterProxyModel):
    def __init__(self, sourceModel, dumpModel):
        QtCore.QSortFilterProxyModel.__init__(self)
        self.setSourceModel(sourceModel)
        self.setSortCaseSensitivity(QtCore.Qt.CaseInsensitive)
#        self.searchQuery = QtSql.QSqlQuery()
        self.dumpModel = dumpModel
        self.baseFont = QtWidgets.QApplication.font()
        self.dumpedFont = QtGui.QFont(self.baseFont)
        self.dumpedFont.setBold(True)
        self.editedFont = QtGui.QFont(self.dumpedFont)
        self.editedFont.setItalic(True)
        self.fontTuple = self.baseFont, self.editedFont, self.dumpedFont

    def checkValidity(self, index, uid):
        if uid:
            sourceRow = index.row()
            res = self.dumpModel.match(self.dumpModel.index(0, UidColumn), QtCore.Qt.DisplayRole, uid)
            if res:
                found = res[0]
                foundRow = found.row()
#                if found.sibling(foundRow, NameColumn).data() == self.mapToSource(index).sibling(sourceRow, NameColumn).data() and \
#                    found.sibling(foundRow, SlotColumn).data() == index.sibling(sourceRow, SlotColumn).data() and \
#                    found.sibling(foundRow, EditedColumn).data() == self.mapToSource(index).sibling(sourceRow, EditedColumn).data() and \
#                    found.sibling(foundRow, DataColumn).data() == self.mapToSource(index).sibling(sourceRow, DataColumn).data():
#                        return QtCore.Qt.Checked
                if found.sibling(foundRow, NameColumn).data() == self.mapToSource(index).sibling(sourceRow, NameColumn).data() and \
                    found.sibling(foundRow, SlotColumn).data() == self.mapToSource(index).sibling(sourceRow, SlotColumn).data() and \
                    found.sibling(foundRow, EditedColumn).data() == self.mapToSource(index).sibling(sourceRow, EditedColumn).data() and \
                    found.sibling(foundRow, DataColumn).data() == self.mapToSource(index).sibling(sourceRow, DataColumn).data():
                        return QtCore.Qt.Checked
                return QtCore.Qt.PartiallyChecked
        return QtCore.Qt.Unchecked

    def data(self, index, role):
        if role == QtCore.Qt.DisplayRole:
            if index.column() == EditedColumn:
                date = QtCore.QDateTime.fromMSecsSinceEpoch(QtCore.QSortFilterProxyModel.data(self, index, role))
                return date.toString(QtCore.Qt.SystemLocaleShortDate)
            elif index.column() == DataColumn:
                data = QtCore.QSortFilterProxyModel.data(self, index, role)
                ds = QtCore.QDataStream(data, QtCore.QIODevice.ReadOnly)
                return str(ds.readInt())
        elif role == QtCore.Qt.CheckStateRole and index.column() == UidColumn:
            uid = index.sibling(index.row(), UidColumn).data()
            return self.checkValidity(index, uid)
#            sourceRow = index.row()
#            res = self.dumpModel.match(self.dumpModel.index(0, UidColumn), QtCore.Qt.DisplayRole, )
#            if res:
#                found = res[0]
#                foundRow = found.row()
##                foundName = found.sibling(foundRow, NameColumn).data()
##                foundSlot = found.sibling(foundRow, SlotColumn).data()
##                foundEdited = found.sibling(foundRow, EditedColumn).data()
##                sourceName = self.mapToSource(index).sibling(sourceRow, NameColumn).data()
##                sourceSlot = index.sibling(sourceRow, SlotColumn).data()
##                sourceEdited = self.mapToSource(index).sibling(sourceRow, EditedColumn).data()
##                foundData = found.sibling(foundRow, DataColumn).data()
##                sourceData = self.mapToSource(index).sibling(sourceRow, DataColumn).data()
##                if foundName == sourceName and foundSlot == sourceSlot and foundEdited == sourceEdited:
#                if found.sibling(foundRow, NameColumn).data() == self.mapToSource(index).sibling(sourceRow, NameColumn).data() and \
#                    found.sibling(foundRow, SlotColumn).data() == index.sibling(sourceRow, SlotColumn).data() and \
#                    found.sibling(foundRow, EditedColumn).data() == self.mapToSource(index).sibling(sourceRow, EditedColumn).data() and \
#                    found.sibling(foundRow, DataColumn).data() == self.mapToSource(index).sibling(sourceRow, DataColumn).data():
#                        return QtCore.Qt.Checked
##                print(foundName, sourceName)
#                return QtCore.Qt.PartiallyChecked
#            return QtCore.Qt.Unchecked
        elif role == QtCore.Qt.TextAlignmentRole and index.column() in (SlotColumn, DataColumn, EditedColumn):
            return QtCore.Qt.AlignCenter
        elif role == QtCore.Qt.FontRole and index.column() == NameColumn:
            return self.fontTuple[self.data(index.sibling(index.row(), UidColumn), QtCore.Qt.CheckStateRole)]
        elif role == QtCore.Qt.ToolTipRole:
            pm = index.sibling(index.row(), PreviewColumn).data()
            if pm:
                return '<img src="data:image/png;base64, {}">'.format(pm.toBase64())
        return QtCore.QSortFilterProxyModel.data(self, index, role)

    def setSortRole(self, role):
        if role == QtCore.Qt.DisplayRole:
            self.lessThan = self.lessThanDefault
        else:
            self.lessThan = self.lessThanDump
        QtCore.QSortFilterProxyModel.setSortRole(self, role)

    lessThan = lessThanDefault = lambda *args: QtCore.QSortFilterProxyModel.lessThan(*args)

    def lessThanDump(self, left, right):
        if left.column() != UidColumn:
            return QtCore.QSortFilterProxyModel.lessThan(self, left, right)
        leftUid = left.data()
        leftFound = self.dumpModel.match(self.dumpModel.index(0, UidColumn), QtCore.Qt.DisplayRole, leftUid)
        rightUid = right.data()
        rightFound = self.dumpModel.match(self.dumpModel.index(0, UidColumn), QtCore.Qt.DisplayRole, rightUid)
        if not leftFound and not rightFound:
            return QtCore.QSortFilterProxyModel.lessThan(self, left, right)
        elif leftFound and rightFound:
            leftFound = leftFound[0]
            rightFound = rightFound[0]
#            print(leftFound.sibling(leftFound.row(), NameColumn).data(), leftFound.row())
#            print(rightFound.sibling(rightFound.row(), NameColumn).data(), rightFound.row())
            return leftFound.row() < rightFound.row()
        elif leftFound and not rightFound:
            return True
        return False


class BlofeldProxyModel(QtCore.QSortFilterProxyModel):
    def __init__(self, dumpModel, waveTableModel):
        QtCore.QSortFilterProxyModel.__init__(self)
        self.waveTableModel = waveTableModel
        self.setSourceModel(dumpModel)
        self.unknownFont = QtWidgets.QApplication.font()
        self.unknownFont.setItalic(True)
        palette = QtWidgets.QApplication.palette()
        self.unknownForegroundColor = palette.color(palette.Disabled, palette.WindowText)
        self.undumpedForegroundColor = QtGui.QColor(QtCore.Qt.red)
        self.systemWaves = False

    def showSystemWaves(self, show):
        self.systemWaves = show
        self.invalidateFilter()

    def checkValidity(self, index, uid):
        if uid:
            sourceRow = index.row()
            res = self.waveTableModel.match(self.waveTableModel.index(0, UidColumn), QtCore.Qt.DisplayRole, uid)
            if res:
                found = res[0]
                foundRow = found.row()
#                if not found.sibling(foundRow, EditedColumn).data() == index.sibling(sourceRow, EditedColumn).data():
#                    print (sourceRow, found.sibling(foundRow, EditedColumn).data(), index.sibling(sourceRow, EditedColumn).data())
                if found.sibling(foundRow, NameColumn).data() == index.sibling(sourceRow, NameColumn).data() and \
                    found.sibling(foundRow, SlotColumn).data() == index.sibling(sourceRow, SlotColumn).data() and \
                    found.sibling(foundRow, EditedColumn).data() == self.mapToSource(index.sibling(sourceRow, EditedColumn)).data() and \
                    found.sibling(foundRow, DataColumn).data() == index.sibling(sourceRow, DataColumn).data():
                        return QtCore.Qt.Checked
#                print(index.sibling(sourceRow, NameColumn).data(), 
#                    found.sibling(foundRow, SlotColumn).data(), index.sibling(sourceRow, SlotColumn).data(), 
#                    found.sibling(foundRow, EditedColumn).data() == self.mapToSource(index.sibling(sourceRow, EditedColumn)).data(), 
#                    found.sibling(foundRow, DataColumn).data() == index.sibling(sourceRow, DataColumn).data())
                return QtCore.Qt.PartiallyChecked
        return QtCore.Qt.Unchecked

    def headerData(self, section, orientation, role):
        if orientation == QtCore.Qt.Vertical and role == QtCore.Qt.DisplayRole:
#            return self.mapToSource(self.index(section, SlotColumn)).data()
            slot = self.mapToSource(self.index(section, SlotColumn)).data()
            return slot if slot >= 1 else ''
        return QtCore.QSortFilterProxyModel.headerData(self, section, orientation, role)

    def data(self, index, role):
        if role == QtCore.Qt.DisplayRole:
            if index.column() == NameColumn:
                name = QtCore.QSortFilterProxyModel.data(self, index, role)
                if name:
                    return name
                return 'Unknown/empty'
            if index.column() == EditedColumn:
                try:
                    date = QtCore.QDateTime.fromMSecsSinceEpoch(QtCore.QSortFilterProxyModel.data(self, index, role))
                    return date.toString(QtCore.Qt.SystemLocaleShortDate)
                except:
                    return None
        elif role == QtCore.Qt.TextAlignmentRole and index.column() == EditedColumn:
            return QtCore.Qt.AlignCenter
        elif role == QtCore.Qt.FontRole and index.column() == NameColumn:
            uid = index.sibling(index.row(), UidColumn).data()
            if not uid:
                return self.unknownFont
            if self.checkValidity(index, uid) == QtCore.Qt.PartiallyChecked:
                return self.unknownFont
            return QtCore.QSortFilterProxyModel.data(self, index, role)
        elif role == QtCore.Qt.ForegroundRole and index.column() == NameColumn:
#            if index.sibling(index.row(), SlotColumn).data() == 81:
#                print(index.sibling(index.row(), DumpedColumn).data())
            if not index.sibling(index.row(), UidColumn).data():
                return self.unknownForegroundColor
            if self.mapToSource(index).row() >= 86 and not index.sibling(index.row(), DumpedColumn).data():
                return self.undumpedForegroundColor
        elif role == QtCore.Qt.StatusTipRole:
            uid = index.sibling(index.row(), UidColumn).data()
            slot = index.sibling(index.row(), SlotColumn).data()
            if not uid:
                return 'Wavetable {} has not been dumped yet'.format(slot)
            elif uid == 'blofeld':
                return 'This is an internal Blofeld wave'
            valid = self.checkValidity(index, uid)
            if not valid:
                return 'Wavetable {} NOT stored locally!'.format(slot)
            if valid == QtCore.Qt.PartiallyChecked:
                return 'Wavetable {} is not updated to the local copy'.format(slot)
            if not index.sibling(index.row(), DumpedColumn).data():
                return 'Wavetable {} is not yet synched with your Blofeld'.format(slot)
            return 'Wavetable {} is synched with your Blofeld'.format(slot)
        elif role == QtCore.Qt.ToolTipRole:
            uid = index.sibling(index.row(), UidColumn).data()
            slot = index.sibling(index.row(), SlotColumn).data()
            if not uid:
                return 'Wavetable {} has not been dumped yet.<br/><br/>Bigglesworth does not know ' \
                    'its content on your Blofeld, which means that it could be an empty sine wave ' \
                    'or a previously dumped wavetable'.format(slot)
            pm = index.sibling(index.row(), PreviewColumn).data()
            if pm:
                pm = '<img src="data:image/png;base64, {}" style="float: left; margin-top: 55px;">'.format(pm.toBase64())
                if uid == 'blofeld':
                    return 'This is an internal Blofeld wave<br/>{}'.format(pm)
            else:
                if uid == 'blofeld':
                    return 'This is an internal Blofeld wave'
                pm = ''
            valid = self.checkValidity(index, uid)
            if not valid:
                return '<table><td style="vertical-align: middle;">{}</td><td>Wavetable {} ' \
                    '<b>NOT</b> stored locally.<br/><br/>This wavetable has been previously ' \
                    'dumped, but the local copy has been deleted since. To restore it, open ' \
                    'it or use the context menu.</td></table>'.format(pm, slot)
            elif valid == QtCore.Qt.PartiallyChecked:
                return '<table><td style="vertical-align: middle;">{}</td><td>Wavetable {} is ' \
                    'not updated.<br/><br/>The local wavetable has been modified ' \
                    'but the modified version has not been saved to the dump list ' \
                    'yet and it\'s also not synched with your Blofeld.</td></table>'.format(pm, slot)
            if not index.sibling(index.row(), DumpedColumn).data():
                return '<table><td style="vertical-align: middle;">{}</td><td>Wavetable {} is ' \
                    'not dumped.<br/><br/>The local wavetable is updated ' \
                    'but it has not been dumped to your Blofeld yet.<br/>' \
                    'Press "Apply changes" to sync.</td></table>'.format(pm, slot)
            return 'Wavetable {}<br/>{}'.format(slot, pm)
        elif role == QtCore.Qt.CheckStateRole and index.column() == UidColumn:
            if self.mapToSource(index).row() < 86:
                return QtCore.Qt.PartiallyChecked
            valid = self.checkValidity(index, index.data())
            if valid:
                return valid
            if index.data():
                return -1
            return 0
        return QtCore.QSortFilterProxyModel.data(self, index, role)

    def flags(self, index):
        flags = QtCore.QSortFilterProxyModel.flags(self, index)
#        if index.row() < 73 or self.checkValidity(index, index.sibling(index.row(), UidColumn).data()):
        if self.checkValidity(index, index.sibling(index.row(), UidColumn).data()) or \
            (self.mapToSource(index).row() >= 86 and index.sibling(index.row(), UidColumn).data()):
                flags |= QtCore.Qt.ItemIsDragEnabled
        else:
            flags ^= QtCore.Qt.ItemIsSelectable
        return flags

    def filterAcceptsRow(self, row, parent):
        if not self.systemWaves:
            return row >= 86
        return not 72 < row < 86 and row


class NameValidator(QtGui.QValidator):
    def validate(self, input, pos):
        output = ''
        for c in input:
            if 32 <= ord(c) < 127 or c == u'°':
                output += c
                continue
            try:
                decoded = unidecode(c)
                assert 32 <= ord(decoded) < 127
                output += decoded
            except:
                res = self.Invalid
        else:
            res = self.Acceptable
        return res, output, pos


class TestMidiDevice(QtCore.QObject):
    midiEvent = QtCore.pyqtSignal(object)
    def __init__(self, main):
        QtCore.QObject.__init__(self)
        self.main = main
        self.backend = -1
        self.main.midiEvent.connect(self.outputEvent)
        config(
            client_name='Bigglesworth', 
            in_ports=[('Input', 'Virtual.*')], 
            out_ports=[('Output', 'Blofeld.*', 'aseqdump.*')])

    def start(self):
        run(Filter(mdNOTE) >> Call(self.inputEvent))

    def inputEvent(self, event):
        if event.type == mdNOTEON:
            newEvent = NoteOnEvent(event.port, event.channel, event.note, event.velocity)
        elif event.type == mdNOTEOFF:
            newEvent = NoteOffEvent(event.port, event.channel, event.note, event.velocity)
        else:
            return
        self.midiEvent.emit(newEvent)

    def outputEvent(self, event):
#        print(event)
        outputEvent(mdSysExEvent(1, event.sysex))


class WaveTableWindow(QtWidgets.QMainWindow):
    midiDevice = None
    shown = False
    isClosing = False
    waveTableModel = None
    currentTransform = None
    windowsDict = {}
    openedWindows = []
    lastActive = []
    recentTables = []

    midiEvent = QtCore.pyqtSignal(object)
    midiConnect = QtCore.pyqtSignal(object, int, bool)

    def __init__(self, waveTable=None):
        QtWidgets.QMainWindow.__init__(self)
        loadUi('ui/wavetables.ui', self)
        self.showLibrarianAction.setIcon(QtGui.QIcon(':/images/bigglesworth_logo.svg'))
        self.showEditorAction.setIcon(QtGui.QIcon(':/images/dial.svg'))

        self.windowsActionGroup = QtWidgets.QActionGroup(self.windowsMenu)
        self.newWindowSeparator = self.windowsMenu.insertSeparator(self.newWindowAction)
        self.windowsMenu.aboutToShow.connect(self.checkWindowsMenu)

        self.pianoIcon = PianoStatusWidget()
        self.statusbar.addPermanentWidget(self.pianoIcon)

        self.midiWidget = MidiStatusBarWidget(self, 3, True)
        self.statusbar.addPermanentWidget(self.midiWidget)
        self.midiEvent.connect(self.midiWidget.midiOutputEvent)

        for mode in sorted(WaveTransformItem.modeNames.keys()):
            name = WaveTransformItem.modeNames[mode]
            icon = QtGui.QIcon.fromTheme(WaveTransformItem.modeIcons[mode])
            self.nextTransformCombo.addItem(icon, name)
        self.nextTransformCombo.currentIndexChanged.connect(self.setCurrentTransformMode)
        self.curveTransformCombo.currentIndexChanged.connect(self.setCurrentTransformCurve)
#        self.curveTransformCombo = CurveTransformCombo()
#        self.nextTransformCycler.addWidget(self.curveTransformCombo)
#        self.nextTransformCycler.setCurrentIndex(1)
#        self.nextTransformEditBtn.clicked.connect(self.editTransform)

        self.uuid = uuid4()
        self._isClean = True
        self.openedWindows.append(self)

        if __name__ == '__main__':
#            self.midiWidget.setMenuEnabled(False)
            if not self.midiDevice:
                self.__class__.midiDevice = TestMidiDevice(self)
                self.midiThread = QtCore.QThread()
                self.midiDevice.moveToThread(self.midiThread)
                self.midiThread.started.connect(self.midiDevice.start)
                self.midiThread.start()
                self.midiDevice.midiEvent.connect(self.midiEventReceived)
            else:
                self.midiEvent.connect(self.openedWindows[0].midiEvent)
#                self.midiEvent.connect(self.midiDevice.outputEvent)
        else:
            self.main = QtWidgets.QApplication.instance()
            self.main.midiConnChanged.connect(self.midiConnChanged)
            self.midiDevice = self.main.midiDevice
            self.graph = self.midiDevice.graph
            self.midiWidget.setMidiDevice(self.midiDevice)
            self.midiWidget.midiConnect.connect(self.midiConnect)
#            self.main.midiConnChanged.connect(self.midiWidget.midiConnChanged)
            inConn, outConn = self.main.connections
            self.midiConnChanged(inConn, outConn, True)
            #signal cannot be shared between two instances?
            if self.openedWindows[0] != self:
                self.midiEvent.connect(self.openedWindows[0].midiEvent)
                self.midiConnect.connect(self.openedWindows[0].midiConnect)

        if self.openedWindows[0] != self:
            self.pianoIcon.stateChanged.connect(self.openedWindows[0].pianoIcon.setState)
            self.openedWindows[0].pianoIcon.stateChanged.connect(self.pianoIcon.setState)

        self.dumper = Dumper(self)
        self.dumper.stopRequested.connect(self.stopRequested)
        self.dumpTimer = QtCore.QTimer()
        self.dumpTimer.setSingleShot(True)
#        self.dumpTimer.setInterval(100)
        self.dumpTimer.timeout.connect(self.sendData)
        self.dumper.started.connect(self.dumpTimer.start)

        self.settings = QtCore.QSettings()
        self.dumpTimer.setInterval(self.settings.value('DumpInterval', 100))
        self.player = Player(self, self.settings.value('AudioDevice'), self.settings.value('SampleRateConversion', 2))

        self.settings.beginGroup('WaveTables')
        if self.openedWindows[0] == self:
            self.pianoIcon.setState(self.settings.value('AcceptMidiNotes', True, bool))
        else:
            self.pianoIcon.setState(self.openedWindows[0].pianoIcon.state)

        if self.settings.contains('Dock'):
            visible, floating, dockedWidth, floatingWidth, geometry = self.settings.value('Dock', [])
            if dockedWidth:
                self.waveTableDock.dockedWidth = int(dockedWidth)
            if floatingWidth:
                self.waveTableDock.floatingWidth = int(floatingWidth)
            if visible != 'true':
                self.waveTableDock.setVisible(False)
                self.waveTableDock.visible = False
            if floating == 'true':
                self.waveTableDock.blockSignals(True)
                self.waveTableDock.setFloating(True)
                self.waveTableDock.blockSignals(False)
                self.waveTableDock.setGeometry(geometry)
        else:
            self.waveTableDock.setFloating(True)
            self.waveTableDock.setVisible(False)
            self.waveTableDock.setFloating(False)
        self.settings.endGroup()

        if __name__ == '__main__':
            self.checkDatabase()
            if not self.waveTableModel:
                self.__class__.waveTableModel = QtSql.QSqlTableModel()
                self.waveTableModel.setTable('wavetables')
                self.waveTableModel.select()
                self.waveTableModel.setHeaderData(UidColumn, QtCore.Qt.Horizontal, 'D')
                self.waveTableModel.setHeaderData(NameColumn, QtCore.Qt.Horizontal, 'Name')
                self.waveTableModel.setHeaderData(SlotColumn, QtCore.Qt.Horizontal, 'Slot')
                self.waveTableModel.setHeaderData(DataColumn, QtCore.Qt.Horizontal, 'Waves')
                self.waveTableModel.setHeaderData(EditedColumn, QtCore.Qt.Horizontal, 'Last modified')

                self.__class__.dumpModel = QtSql.QSqlTableModel()
                self.dumpModel.setTable('dumpedwt')
                self.dumpModel.select()
                self.dumpModel.setHeaderData(UidColumn, QtCore.Qt.Horizontal, 'D')
                self.dumpModel.setHeaderData(NameColumn, QtCore.Qt.Horizontal, 'Name')
                self.dumpModel.setHeaderData(EditedColumn, QtCore.Qt.Horizontal, 'Last modified')

#                self.__class__.initialized = True

        self.waveTableModel.beforeDelete.connect(self.checkRemoval)
        self.localProxy = LocalProxyModel(self.waveTableModel, self.dumpModel)
        self.dumpModel.dataChanged.connect(self.checkDumps)

        self.localWaveTableList.verticalHeader().setDefaultSectionSize(self.fontMetrics().height() * 1.5)
        self.localWaveTableList.setModel(self.localProxy)
        self.checkBoxDelegate1 = CheckBoxDelegate(editable=False)
        self.localWaveTableList.setItemDelegateForColumn(UidColumn, self.checkBoxDelegate1)
        self.localWaveTableList.setColumnHidden(PreviewColumn, True)
        self.localWaveTableList.doubleClicked.connect(self.openFromLocalList)
        self.localWaveTableList.selectionModel().selectionChanged.connect(self.checkSelection)
        wtHeader = self.localWaveTableList.horizontalHeader()
        for column, label in ((UidColumn, 'D'), (SlotColumn, 'Slot'), (DataColumn, 'Waves')):
            hint = wtHeader.sectionSizeHint(column)
            fmWidth = self.fontMetrics().width(label)
            self.localWaveTableList.setColumnWidth(column, (hint - fmWidth) * .3 + fmWidth)
            wtHeader.setResizeMode(column, wtHeader.Fixed)
        
        wtHeader.moveSection(DataColumn, EditedColumn)
        wtHeader.setResizeMode(NameColumn, wtHeader.Fixed)
        wtHeader.setResizeMode(EditedColumn, wtHeader.Stretch)
        wtHeader.sectionClicked.connect(self.setWaveTableSorting)
        self.localWaveTableList.resizeColumnToContents(NameColumn)
        self.localWaveTableList.resizeColumnToContents(EditedColumn)
        self.localWaveTableList.customContextMenuRequested.connect(self.showLocalMenu)

        self.blofeldProxy = BlofeldProxyModel(self.dumpModel, self.waveTableModel)
        self.blofeldWaveTableList.setModel(self.blofeldProxy)
        self.blofeldWaveTableList.verticalHeader().setDefaultSectionSize(self.fontMetrics().height() * 1.5)
        self.checkBoxDelegate2 = CheckBoxDelegate(editable=False)
        self.blofeldWaveTableList.setItemDelegateForColumn(UidColumn, self.checkBoxDelegate2)
        self.blofeldWaveTableList.setColumnHidden(SlotColumn, True)
        self.blofeldWaveTableList.setColumnHidden(DataColumn, True)
        self.blofeldWaveTableList.setColumnHidden(PreviewColumn, True)
        self.blofeldWaveTableList.setColumnHidden(DumpedColumn, True)
        self.blofeldWaveTableList.doubleClicked.connect(self.openFromDumpList)
        blHeader = self.blofeldWaveTableList.horizontalHeader()
        self.blofeldWaveTableList.setColumnWidth(UidColumn, self.localWaveTableList.columnWidth(UidColumn))
        blHeader.setResizeMode(UidColumn, blHeader.Fixed)
        blHeader.setResizeMode(NameColumn, blHeader.Stretch)
        blHeader.setResizeMode(EditedColumn, blHeader.Stretch)
        self.blofeldWaveTableList.verticalHeader().setDefaultAlignment(QtCore.Qt.AlignCenter)
        self.blofeldWaveTableList.verticalHeader().setResizeMode(blHeader.Fixed)

        cornerButton = self.blofeldWaveTableList.findChild(QtWidgets.QAbstractButton)
        cornerButtonLayout = QtWidgets.QHBoxLayout()
        cornerButton.setLayout(cornerButtonLayout)
        cornerButtonLayout.setContentsMargins(0, 0, 0, 0)
        cornerLbl = QtWidgets.QLabel('Slot')
        cornerLbl.setAlignment(QtCore.Qt.AlignCenter)
        cornerButtonLayout.addWidget(cornerLbl)

        self.blofeldWaveTableList.customContextMenuRequested.connect(self.showBlofeldMenu)
        self.blofeldFilterChk.toggled.connect(self.blofeldProxy.showSystemWaves)

        self.newWindowAction.triggered.connect(self.createNewWindow)
        self.importAction.triggered.connect(self.importFiles)
        self.exportAction.triggered.connect(self.exportCurrent)
        self.newBtn.clicked.connect(self.createNewWindow)
        self.duplicateBtn.clicked.connect(self.duplicateWaveTable)
        self.deleteBtn.clicked.connect(self.deleteWaveTables)

        self.waveTableMenu.aboutToShow.connect(self.fillWaveTableMenu)
        self.waveTableMenuSeparator = self.waveTableMenu.addSection('Recent wavetables')
        self.showDockAction.triggered.connect(self.toggleDock)
        self.audioSettingsAction = QtWidgets.QAction('Audio settings', self)
        self.audioSettingsAction.triggered.connect(self.setAudioDevice)
        self.menubar.addAction(self.audioSettingsAction)

        self.undoStack = UndoStack()
        self.undoStack.canUndoChanged.connect(lambda state: [self.mainUndoBtn.setEnabled(state), self.waveUndoBtn.setEnabled(state)])
        self.undoStack.undoTextChanged.connect(lambda text: [self.mainUndoBtn.setToolTip(text), self.waveUndoBtn.setToolTip(text)])
        self.undoStack.canRedoChanged.connect(lambda state: [self.mainRedoBtn.setEnabled(state), self.waveRedoBtn.setEnabled(state)])
        self.undoStack.redoTextChanged.connect(lambda text: [self.mainRedoBtn.setToolTip(text), self.waveRedoBtn.setToolTip(text)])
#        self.undoStack.indexChanged.connect(lambda i: self.setWindowModified(i != self.undoStack.cleanIndex()))
        self.undoStack.cleanChanged.connect(self.checkClean)
        self.mainUndoBtn.clicked.connect(self.undoStack.undo)
        self.waveUndoBtn.clicked.connect(self.undoStack.undo)
        self.mainRedoBtn.clicked.connect(self.undoStack.redo)
        self.waveRedoBtn.clicked.connect(self.undoStack.redo)
        self.undoView = QtWidgets.QUndoView(self.undoStack)
        self.undoView.show = lambda: [QtWidgets.QUndoView.show(self.undoView), self.undoView.activateWindow()]
        self.undoView.setWindowTitle('Wave table undo list')
        self.undoView.setEmptyLabel('New wave table')
        self.mainUndoHistoryBtn.clicked.connect(self.undoView.show)
        self.waveUndoHistoryBtn.clicked.connect(self.undoView.show)
        self.undoAction = self.undoStack.createUndoAction(self)
        self.undoAction.setShortcut(QtGui.QKeySequence(QtGui.QKeySequence.Undo))
        self.redoAction = self.undoStack.createRedoAction(self)
        self.redoAction.setShortcut(QtGui.QKeySequence(QtGui.QKeySequence.Redo))
        self.addActions([self.undoAction, self.redoAction])
#        self.undoAction.setShortcutContext(QtCore.Qt.)

        self.keyFrameScene = KeyFrameScene(self.keyFrameView)
        self.keyFrameView.setScene(self.keyFrameScene)
        self.keyFrameScene.setIndexRequested.connect(self.setKeyFrameIndex)
        self.keyFrameScene.highlight.connect(self.setCurrentKeyFrame)
#        self.keyFrameScene.transformSelected.connect(self.selectTransform)
        self.keyFrameScene.deleteRequested.connect(self.deleteRequested)
        self.keyFrameScene.mergeRequested.connect(self.mergeRequested)
        self.keyFrameScene.pasteTransformRequested.connect(self.pasteTransform)
        self.keyFrameScene.createKeyFrameRequested.connect(self.createKeyFrame)
        self.keyFrameScene.externalDrop.connect(self.keyFrameSceneExternalDrop)
        self.keyFrameScene.waveDrop.connect(self.keyFrameSceneWaveDrop)
        self.keyFrames = self.keyFrameScene.keyFrames
        self.keyFrames.changed.connect(self.setNextKeyFrame)
        self.mainTransformWidget.keyFrames = self.keyFrames

        self.nameValidator = NameValidator()
        self.nameEdit.setValidator(self.nameValidator)
        self.nameEdit.textEdited.connect(lambda t: self.setWindowTitle(u'Wavetable Editor - {} [*]'.format(t)))
        self.nameEdit.textEdited.connect(lambda: self.setWindowModified(True))
        self.waveTableScene = WaveTableScene(self)
        self.waveTableScene.waveDoubleClicked.connect(lambda keyFrame: self.setCurrentKeyFrame(keyFrame, True))
        self.waveTableScene.highlight.connect(self.updateMiniWave)
        self.waveTableScene.createKeyFrameRequested.connect(self.createKeyFrame)
        self.waveTableScene.deleteRequested.connect(self.deleteRequested)
#        self.waveTableScene.moveKeyFrameRequested.connect(self.moveKeyFrame)
        self.waveTableScene.moveKeyFramesRequested.connect(self.moveKeyFrames)
        self.waveTableScene.waveDrop.connect(self.waveTableDrop)
        self.waveTableView.setScene(self.waveTableScene)
        self.waveTableView.fitInView(self.waveTableScene.sceneRect(), QtCore.Qt.KeepAspectRatio)
        self.slotSpin.valueChanged.connect(lambda: self.setWindowModified(True))

        self.indexSlider.valueChanged.connect(self.highlightKeyFrame)
        self.indexSlider.valueChanged.connect(lambda i: self.indexSpin.setValue(i + 1))
        self.indexSlider.valueChanged.connect(lambda i: self.waveEditBtn.setEnabled(True if self.keyFrames.fullList[i] else False))
        self.indexSlider.setKeyFrames(self.keyFrames)
        self.indexSpin.valueChanged.connect(lambda i: self.indexSlider.setValue(i - 1))
        self.indexSpin.setKeyFrames(self.keyFrames)
        self.waveEditBtn.clicked.connect(lambda: self.setCurrentKeyFrame(self.keyFrames.get(self.indexSlider.value()), True))
        self.saveBtn.clicked.connect(self.save)
        self.dumpBtn.setIcon(QtGui.QIcon(':/images/dump.svg'))
        self.dumpBtn.clicked.connect(self.saveAndDump)
        self.importBtn.clicked.connect(self.importFiles)
        self.exportLibraryBtn.clicked.connect(self.exportFiles)
        self.exportBtn.clicked.connect(self.exportCurrent)
        self.dumpAllBtn.setIcon(QtGui.QIcon(':/images/dump.svg'))

        option = QtWidgets.QStyleOptionSpinBox()
        self.indexSpin.initStyleOption(option)
        spinButtonWidth = self.style().subControlRect(QtWidgets.QStyle.CC_SpinBox, option, QtWidgets.QStyle.SC_SpinBoxUp).width() + 4
        self.indexSpin.setMaximumWidth(spinButtonWidth + self.fontMetrics().width('8888'))
        self.slotSpin.setMaximumWidth(spinButtonWidth + self.fontMetrics().width('888'))
        self.quantizeSpin.setMaximumWidth(spinButtonWidth + self.fontMetrics().width('888888'))

        self.reverseBtn.clicked.connect(self.reverseWaveTable)
        self.distributeBtn.clicked.connect(self.distributeWaveTable)

        #WaveScene
        self.waveScene = WaveScene(self)
        self.waveView.setScene(self.waveScene)
        self.waveView.fitInView(self.waveScene.sceneRect())
        self.waveScene.freeDraw.connect(self.freeDraw)
        self.waveScene.freeDrawInterpolate.connect(self.freeDraw)
        self.waveScene.genericDraw.connect(self.genericDraw)
        self.waveScene.waveTransform.connect(self.waveTransform)
        self.harmonicsWidget.harmonicsChanged.connect(
            lambda harmonics: self.waveScene.harmonicsChanged(harmonics, self.waveTypeCombo.currentIndex(), self.addHarmonicsChk.isChecked()))
        self.addHarmonicsChk.toggled.connect(
            lambda state: self.waveScene.harmonicsChanged(self.harmonicsWidget.values, self.waveTypeCombo.currentIndex(), state))
        self.waveTypeCombo.currentIndexChanged.connect(
            lambda waveType: self.waveScene.harmonicsChanged(self.harmonicsWidget.values, waveType, self.addHarmonicsChk.isChecked()))
        self.applyHarmonicsBtn.clicked.connect(self.applyHarmonics)
        self.harmonicsPanel.setVisible(False)
        self.waveScene.selectionChanged.connect(self.setQuantizeRatio)

        self.undoStack.indexesChanged.connect(self.waveScene.indexesChanged)

        self.fullTableMiniScene = QtWidgets.QGraphicsScene()
        self.fullTableMiniView.setScene(self.fullTableMiniScene)

        self.gridCombo.currentIndexChanged.connect(self.waveScene.setGridMode)
        self.waveScene.setGridMode(self.gridCombo.currentIndex())

        self.mouseModeGroup.buttonClicked[int].connect(self.waveScene.setMouseMode)
        self.mouseModeGroup.setId(self.drawFreeBtn, self.waveScene.FreeDraw)
        self.mouseModeGroup.setId(self.drawQuadCurveBtn, self.waveScene.QuadCurveDraw)
        self.mouseModeGroup.setId(self.drawCubicCurveBtn, self.waveScene.CubicCurveDraw)
        self.mouseModeGroup.setId(self.drawLineBtn, self.waveScene.LineDraw)
        self.mouseModeGroup.setId(self.selectBtn, self.waveScene.Select)
        self.mouseModeGroup.setId(self.hLockBtn, self.waveScene.HLock)
        self.mouseModeGroup.setId(self.vLockBtn, self.waveScene.VLock)
        self.mouseModeGroup.setId(self.moveBtn, self.waveScene.Drag)
        self.mouseModeGroup.setId(self.shiftBtn, self.waveScene.Shift)
        self.mouseModeGroup.setId(self.gainBtn, self.waveScene.Gain)
        self.mouseModeGroup.setId(self.harmonicsBtn, self.waveScene.Harmonics)
        self.noMouseModeBtn = QtWidgets.QPushButton()
        self.noMouseModeBtn.setCheckable(True)
        self.mouseModeGroup.addButton(self.noMouseModeBtn)
        self.mouseModeGroup.setId(self.noMouseModeBtn, 0)
        self.harmonicsBtn.toggled.connect(lambda state: [self.harmonicsPanel.setVisible(state), self.harmonicsWidget.reset() if not state else None])
        self.discardHarmonicsBtn.clicked.connect(lambda: [self.noMouseModeBtn.setChecked(True), self.waveScene.setMouseMode(0)])

        self.showCrosshairChk.toggled.connect(self.waveScene.setCrosshair)
        self.snapCombo.currentIndexChanged.connect(self.waveScene.setSnapMode)
        self.showNodesChk.toggled.connect(self.waveScene.setNodes)

        self.miniView.setScene(self.waveTableView.scene())
        self.miniView.setTransform(self.waveTableView.transform())
        self.miniView.clicked.connect(lambda: self.mainTabWidget.setCurrentIndex(0))

        self.smoothBtn.clicked.connect(lambda: self.waveScene.smoothen(self.smoothEdgesChk.isChecked()))
        self.randomBtn.clicked.connect(self.waveScene.randomize)
        self.quantizeBtn.clicked.connect(lambda: self.waveScene.quantize(self.quantizeSpin.value()))
        self.hRevBtn.clicked.connect(self.waveScene.reverseHorizontal)
        self.vRevBtn.clicked.connect(self.waveScene.reverseVertical)

        self.mainTabWidget.currentChanged.connect(self.miniView.setVisible)
        self.mainTabWidget.tabCloseRequested.connect(self.tabCloseRequested)
        self.mainTabBar = self.mainTabWidget.tabBar()
        self.mainTabBar.setTabIcon(1, QtGui.QIcon(':/images/wavetable.svg'))

#        self.transformEditor = TransformEditor(self)
#        self.mainTabWidget.setHidden(self.mainTabWidget.addTab(self.transformEditor, QtGui.QIcon.fromTheme('exchange-positions'), 'Transform edit'), True)
#        self.mainTabWidget.setHidden(2, True)
#        self.mainTabBar = MainTabBar(self)
#        self.mainTabBar.setTabsClosable(True)
#        self.mainTabWidget.setTabBar(self.mainTabBar)

        try:
            for tabId in range(2):
                self.mainTabBar.setTabButton(tabId, self.mainTabBar.RightSide, None)
            self.tabCloseButtonSide = self.mainTabBar.RightSide
        except:
            for tabId in range(2):
                self.mainTabBar.tabButton(tabId, self.mainTabBar.LeftSide, None)
            self.tabCloseButtonSide = self.mainTabBar.LeftSide
        self.addAudioImportTab()
#        self.mainTabWidget.setCurrentIndex(self.mainTabWidget.count() - 1)

        self.waveTablePlayerPanel.contentName = 'play controls'
        self.pianoKeyboard.noteEvent.connect(self.playFullTableNote)
        self.speedSlider.valueChanged.connect(
            lambda value: self.speedLbl.setText('Speed (1/{})'.format(max(1, value))))

        self.wavePlayerPanel.contentName = 'play controls'
        self.wavePianoKeyboard.noteEvent.connect(self.playWaveNote)

        self.openFromUid(waveTable)
        if not waveTable:
            res = self.waveTableModel.match(self.waveTableModel.index(0, NameColumn), QtCore.Qt.DisplayRole, 'MyWaveTable', hits=-1)
            existing = [index.data() for index in res]
            existing.extend([w.nameEdit.text() for w in self.openedWindows])
            base = 'MyWaveTable{:03}'
            index = 1
            while index < 1000:
                name = base.format(index)
                if name not in existing:
                    break
                index += 1
            self.nameEdit.setText(name)

        self.checkDumps()
        self.dumpAllBtn.clicked.connect(self.dumpAll)
        self.applyBtn.clicked.connect(self.dumpUpdated)
        self.mainTransformWidget.setTransform(self.keyFrames[0])

    def isClean(self):
        return self.undoStack.isClean() and self._isClean

    def canDump(self):
        if isinstance(self.midiDevice, TestMidiDevice):
            return True
        return bool(len([c for c in self.main.connections[1] if not c.hidden]))

    @property
    def currentWaveTableName(self):
        return self.nameEdit.text()

    def toggleDock(self, show):
        if show:
            self.waveTableDock.setVisible(True), self.waveTableDock.activateWindow()
        else:
            self.waveTableDock.setVisible(False)

    def fillWaveTableMenu(self):
        self.showDockAction.setChecked(self.waveTableDock.isVisible())
        self.showDockAction.setText('{} library'.format('Hide' if self.waveTableDock.isVisible() else 'Show'))
        actions = self.waveTableMenu.actions()
        for action in actions[actions.index(self.waveTableMenuSeparator) + 1:]:
            self.waveTableMenu.removeAction(action)
        self.settings.beginGroup('WaveTables')
        recentLoaded = self.settings.value('Recent', [])
        existing = []
        count = 0
        for uid in recentLoaded:
            found = self.waveTableModel.match(self.waveTableModel.index(0, UidColumn), QtCore.Qt.DisplayRole, 
                uid, flags=QtCore.Qt.MatchExactly)
            if not found:
                found = self.dumpModel.match(self.dumpModel.index(0, UidColumn), 
                    QtCore.Qt.DisplayRole, uid, flags=QtCore.Qt.MatchExactly)
                if not found:
                    continue
            count += 1
            found = found[0]
            text = '&{}. {} (slot {})'.format(count, found.sibling(found.row(), NameColumn).data().strip(), 
                found.sibling(found.row(), SlotColumn).data())
            action = self.waveTableMenu.addAction(text)
            action.triggered.connect(lambda _, found=found: self.openFromModel(found))
            existing.insert(0, uid)
            if count >= 10:
                break
        if existing != recentLoaded:
            if existing:
                self.settings.setValue('Recent', existing)
            else:
                self.settings.remove('Recent')
        self.settings.endGroup()

    def checkWindowsMenu(self):
        windows = [w for w in self.openedWindows if w.isVisible()]
        for action in self.windowsActionGroup.actions():
            if action.data() not in windows:
                self.windowsMenu.removeAction(action)
                self.windowsActionGroup.removeAction(action)
            else:
                window = action.data()
                windows.remove(window)
                if window.isClean():
                    text = window.nameEdit.text().strip()
                    icon = QtGui.QIcon.fromTheme('checkbox')
                    italic = False
                else:
                    text = '(*) ' + window.nameEdit.text().strip()
                    icon = QtGui.QIcon.fromTheme('document-edit')
                    italic = True
                action.setText(text)
                action.setIcon(icon)
                setItalic(action, italic)
                action.setChecked(window == self)
        for window in windows:
            text = window.nameEdit.text().strip()
            if window.isClean():
                icon = QtGui.QIcon.fromTheme('checkbox')
                italic = False
            else:
                icon = QtGui.QIcon.fromTheme('document-edit')
                italic = True
                text = '(*) ' + text
            action = QtWidgets.QAction(icon, text, self.windowsMenu)
            self.windowsMenu.insertAction(self.newWindowSeparator, action)
            self.windowsActionGroup.addAction(action)
            action.setData(window)
            action.setCheckable(True)
            setItalic(action, italic)
            action.setChecked(window == self)
            action.triggered.connect(window.activateWindow)

    def checkDatabase(self):
        db = QtSql.QSqlDatabase.database()
        print('creo database?!')
        query = QtSql.QSqlQuery()
        if not 'wavetables' in db.tables():
            if not query.exec_('CREATE TABLE wavetables(uid varchar primary key, name varchar(14), slot int, edited int, data blob, preview blob)'):
                print(query.lastError().databaseText())
#        else:
#            record = db.record('wavetables')
#            columns = [record.fieldName(i) for i in range(record.count())]
#            print(columns)

        if not 'dumpedwt' in db.tables():
#            if not query.exec_('CREATE TABLE dumpedwt(slot int primary key, uid varchar, name varchar(14), edited int)'):
            if not query.exec_('CREATE TABLE dumpedwt(uid varchar, name varchar(14), slot int primary key, edited int, data blob, preview blob, dumped int)'):
                print(query.lastError().databaseText())
            query.prepare('INSERT INTO dumpedwt(uid, name, slot,preview) VALUES("blofeld", :name, :slot, :preview)')
            shapes = self.drawOscShapes()
            for slot in range(7):
                query.bindValue(':name', oscShapes[slot])
                query.bindValue(':slot', -slot)
                query.bindValue(':preview', shapes.get(slot))
                if not query.exec_():
                    print(query.lastError().databaseText())
            query.prepare('INSERT INTO dumpedwt(uid, name, slot) VALUES("blofeld", :name, :slot)')
            for slot in range(7, 86):
                query.bindValue(':name', oscShapes[slot])
                query.bindValue(':slot', slot - 6)
                if not query.exec_():
                    print(query.lastError().databaseText())
            query.prepare('INSERT INTO dumpedwt(name, slot) VALUES(:name, :slot)')
            for slot in range(86, 125):
                query.bindValue(':name', oscShapes[slot])
                query.bindValue(':slot', slot - 6)
                if not query.exec_():
                    print(query.lastError().databaseText())

    def drawOscShapes(self):
        wavePen = QtGui.QPen(QtGui.QColor(64, 192, 216), 1.2, cap=QtCore.Qt.RoundCap)
        wavePen.setCosmetic(True)

        paths = []

        #Pulse
        path = QtGui.QPainterPath()
        path.moveTo(1, 35)
        path.lineTo(1, 4)
        path.lineTo(64, 4)
        path.lineTo(64, 68)
        path.lineTo(127, 68)
        path.lineTo(127, 35)
        paths.append(path)

        #Sawtooth
        path = QtGui.QPainterPath()
        path.moveTo(1, 35)
        path.lineTo(1, 4)
        path.lineTo(127, 68)
        path.lineTo(127, 35)
        paths.append(path)

        #Triangle
        path = QtGui.QPainterPath()
        path.moveTo(1, 35)
        path.lineTo(32, 4)
        path.lineTo(96, 68)
        path.lineTo(127, 35)
        paths.append(path)

        #Sine
        path = QtGui.QPainterPath()
        path.moveTo(0, 35)
        for x, y in enumerate(sineValues(1), 1):
            path.lineTo(x, -y * 28 + 35)
        paths.append(path)

        paths = iter(paths)
        shapes = {}
        for shape in range(1, 5):
            pixmap = QtGui.QPixmap(128, 72)
            pixmap.fill(QtCore.Qt.transparent)
            qp = QtGui.QPainter(pixmap)
            qp.setRenderHints(qp.Antialiasing)
            qp.setPen(wavePen)
            qp.drawPath(paths.next())
#            qp.drawLine(0, 0, 128, 72)
            qp.end()
            byteArray = QtCore.QByteArray()
            buffer = QtCore.QBuffer(byteArray)
            pixmap.save(buffer, 'PNG', 32)
            shapes[shape] = byteArray
        return shapes

    def setWaveTableSorting(self, column):
        if column:
            self.localProxy.setSortRole(QtCore.Qt.DisplayRole)
        else:
            self.localProxy.setSortRole(QtCore.Qt.CheckStateRole)

    def setAudioDevice(self):
        self.player.stop()
        res = AudioSettingsDialog(self.window(), self.player).exec_()
        if not res:
            return
        device, conversion = res
        if device is not None:
            self.player.setAudioDevice(device)
        self.player.setSampleRateConversion(conversion)

    def midiEventReceived(self, event):
        if not event.type in (NOTEOFF, NOTEON) or not self.pianoIcon.state:
            return
        print([w for w in QtWidgets.QApplication.topLevelWidgets() if w.isVisible() and isinstance(w, QtWidgets.QMainWindow)])
        for window in reversed(self.openedWindows + self.lastActive):
            if window.isVisible():
                break
        else:
            return

        keyboard = window.wavePianoKeyboard if window.mainTabWidget.currentIndex() == 1 else window.pianoKeyboard
        keyboard.triggerNoteEvent(event.type == NOTEON, event.note, event.velocity)

    def midiConnChanged(self, input, output, update=False):
        self.midiWidget.midiConnChanged(input, output, update)
        self.checkDumps(bool(len(output)))
        self.pianoIcon.setEnabled(bool(len(input)))

    def applyHarmonics(self):
        self.waveScene.applyHarmonics()
#        self.harmonicsWidget.reset()
        self.noMouseModeBtn.setChecked(True)

    def setQuantizeRatio(self):
        selected = self.waveScene.selectedItems()
        if len(selected) < 1:
            valid = True
            count = 128
        elif len(selected) < 4:
            valid = False
            count = 0
        else:
            indexes = [n.sample for n in selected]
            indexes.sort()
            count = len(indexes)
            valid = max(indexes) - min(indexes) + 1 == count
        self.quantizeBtn.setEnabled(valid)
        self.quantizeSpin.setEnabled(valid)
#        print(count)
        if valid:
            self.quantizeSpin.setMaximum(count / 2)
            self.quantizeSpin.setValue(count / 4)
            self.quantizeSpin.setPrefix('{}/'.format(count))

    #UndoStack

    def waveTableDrop(self, start, data, fromFile=False):
        print(fromFile)
        self.undoStack.push(GenericValuesUndo(self, start, data, fromFile))

    def keyFrameSceneExternalDrop(self, dropData, data, sourceName):
        self.undoStack.push(DropSelectionUndo(self, dropData, data, sourceName))

    def keyFrameSceneWaveDrop(self, dropData, values, filePath):
        self.undoStack.push(AdvancedValuesUndo(self, dropData, values, filePath))

    def freeDraw(self, keyFrame, sample, value, buttonTimer, other=None):
        if other is None:
            undo = FreeDrawUndo(self, keyFrame, sample, value, buttonTimer)
        else:
            #interpolate values
            lastValue = keyFrame.values[other]
            if sample < other:
                ratio = int((value - lastValue) / float(other - sample))
                sampleRange = range(sample, other)
                values = list(reversed([value + ratio * s for s in range(len(sampleRange))]))
            else:
                ratio = int((lastValue - value) / float(sample - other))
                sampleRange = range(other + 1, sample + 1)
                values = [value - ratio * s for s in range(len(sampleRange))]
            undo = FreeDrawUndo(self, keyFrame, sampleRange, values, buttonTimer)
        self.undoStack.push(undo)

    def genericDraw(self, mouseMode, keyFrame, values):
        self.undoStack.push(GenericDrawUndo(self, mouseMode, keyFrame, values))

    def waveTransform(self, mode, keyFrame, values):
        self.undoStack.push(WaveUndo(self, mode, keyFrame, values))

    #end UndoStack

#    def playFullWave(self, state):
#        self.player.stop()
#        if state:
#            self.player.playData(self.keyFrames.fullTableValues(60, 10, self.player.sampleRate), volume=self.volumeDial.value * .01)

    def playFullTableNote(self, state, note, velocity):
        try:
            self.player.notify.disconnect(self.setFullTablePlayhead)
        except:
            pass
        self.player.stop()
        if state:
            multiplier = max(1, self.speedSlider.value())
            self.player.notify.connect(self.setFullTablePlayhead)
            self.player.playData(
                self.keyFrames.fullTableValues(note, multiplier, self.player.sampleRate, index=None, reverse=self.backForthChk.isChecked()), 
                volume=max(1, velocity) / 127.)

    def playWaveNote(self, state, note, velocity):
        try:
            self.player.notify.disconnect(self.setFullTablePlayhead)
        except:
            pass
        self.player.stop()
        if state:
            if self.harmonicsWidget.isVisible():
                wavePath = self.waveScene.currentWavePath.path()
                index = [-wavePath.elementAt(s).y + pow20 for s in range(128)]
            else:
                index = self.waveScene.currentKeyFrame.index
#                index = self.waveScene.currentKeyFrame.values
#            print(index[:10])
#                data = np.concatenate(np.array([wavePath.elementAt(s).y for s in range(128)]))
            data = self.keyFrames.fullTableValues(note, 1, self.player.sampleRate, index=index)
            self.player.playData(data, volume=max(1, velocity) / 127.)

    def setFullTablePlayhead(self):
#        inBuffer = self.player.output.bufferSize() - self.player.output.bytesFree()
#        usInBuffer = inBuffer * 1000000 / (2 * self.player.sampleSize / 8.) / self.player.sampleRate
#        secs = (self.player.output.processedUSecs() - usInBuffer) / 1000000.
        secs = self.player.output.processedUSecs() / 1000000.
        rest, pos = divmod(int(secs * self.keyFrames.sampleRatio), 64)
        if self.backForthChk.isChecked() and rest & 1:
            pos = 64 - pos
        self.waveTableScene.highlight.emit(pos)

    def addAudioImportTab(self):
        importTab = AudioImportTab(self)
        importTab.imported.connect(self.fileImported)
        self.mainTabWidget.addTab(importTab, QtGui.QIcon.fromTheme('document-open'), 'Audio import')
        self.checkTabButtons()

    def checkTabButtons(self):
        count = self.mainTabBar.count()
        enable = count > 3
        for tabId in range(2, count - 1):
            self.mainTabBar.tabButton(tabId, self.tabCloseButtonSide).setEnabled(enable)
        self.mainTabBar.tabButton(count - 1, self.tabCloseButtonSide).setEnabled(False)

    def tabCloseRequested(self, tabId):
#        importTab = self.mainTabWidget.widget(tabId)
        self.mainTabWidget.removeTab(tabId)
        self.checkTabButtons()

    def fileImported(self, info):
        fileInfo = QtCore.QFileInfo(info.name)
        tabId = self.mainTabWidget.indexOf(self.sender())
        self.mainTabBar.setTabText(tabId, fileInfo.fileName())
        self.mainTabBar.setTabToolTip(tabId, fileInfo.absoluteFilePath())
        self.mainTabBar.setTabIcon(tabId, QtGui.QIcon.fromTheme('audio-x-generic'))
        self.addAudioImportTab()

    def highlightKeyFrame(self, index):
        prevKeyFrame = nextKeyFrame = None
        for keyFrame in self.keyFrames:
            if keyFrame.index == index:
                self.waveTableScene.updateSlice(keyFrame)
                self.updateMiniWave(keyFrame)
                return
            elif keyFrame.index > index:
                nextKeyFrame = keyFrame
                break
            prevKeyFrame = keyFrame
        if nextKeyFrame is None:
            if prevKeyFrame.index < 63:
                nextKeyFrame = self.keyFrames[0]
                keyRange = 63 - prevKeyFrame.index
        else:
            keyRange = nextKeyFrame.index - prevKeyFrame.index
        self.waveTableScene.updateSlice(index)
        self.fullTableMiniScene.clear()
        prevItem = self.fullTableMiniScene.addPath(prevKeyFrame.wavePath)
        prevColor = QtGui.QColor(SampleItem.highlightPen)
        if nextKeyFrame and prevKeyFrame.nextTransform.mode:
            nextItem = self.fullTableMiniScene.addPath(nextKeyFrame.wavePath)
            nextColor = QtGui.QColor(SampleItem.highlightPen)
            pos = (index - prevKeyFrame.index) / float(keyRange)
            prevColor.setAlphaF(1 - pos)
            nextColor.setAlphaF(pos)
            nextItem.setPen(nextColor)
        prevItem.setPen(prevColor)
        self.mainTransformWidget.setTransform(prevKeyFrame)

    def updateMiniWave(self, keyFrame):
        #workaround, maybe should rethink the whole signaling structure
        if isinstance(keyFrame, int):
            self.indexSlider.setValue(keyFrame)
            return
        self.fullTableMiniScene.clear()
        item = self.fullTableMiniScene.addPath(keyFrame.wavePath)
        item.setPen(keyFrame.highlightPen)
        rect = QtCore.QRectF(0, 0, keyFrame.wavePathMaxWidth, keyFrame.wavePathMaxHeight)
        self.fullTableMiniView.fitInView(rect)
        index = keyFrame.index
        self.indexSlider.blockSignals(True)
        self.indexSlider.setValue(index)
        self.indexSlider.blockSignals(False)
        self.indexSpin.blockSignals(True)
        self.indexSpin.setValue(index + 1)
        self.indexSpin.blockSignals(False)
        self.waveEditBtn.setEnabled(True if self.keyFrames.fullList[index] else False)
        self.mainTransformWidget.setTransform(keyFrame)

    #Keyframes
    def createKeyFrame(self, index, values, after):
        self.undoStack.push(CreateKeyFrameUndo(self, index, values, after))

#    def moveKeyFrame(self, keyFrame, index):
#        if keyFrame.index == index:
#            return
#        self.undoStack.push(MoveKeyFrameUndo(self, keyFrame, index))
        #create undoCommand here
#        self.keyFrames.moveKeyFrame(keyFrame, index)

    def moveKeyFrames(self, keyFrames, index):
        if keyFrames[0].index == index:
            return
        self.undoStack.push(MoveKeyFramesUndo(self, keyFrames, index))

    def deleteRequested(self, items):
        if isinstance(items, list):
            if QtWidgets.QMessageBox.question(self, 'Remove waves?', 
                'Remove {} waves from the wavetable?'.format(len(items)), 
                QtWidgets.QMessageBox.Ok|QtWidgets.QMessageBox.Cancel) == QtWidgets.QMessageBox.Ok:
#                    self.keyFrames.deleteKeyFrames(items)
                    self.undoStack.push(RemoveWavesUndo(self, items))
        elif isinstance(items, WaveTransformItem):
#            self.keyFrames.deleteTransform(items)
            self.undoStack.push(RemoveTransformUndo(self, items))
        elif QtWidgets.QMessageBox.question(self, 'Remove wave?', 
            'Remove wave {} from the wavetable?'.format(items.index), 
            QtWidgets.QMessageBox.Ok|QtWidgets.QMessageBox.Cancel) == QtWidgets.QMessageBox.Ok:
#                self.keyFrames.deleteKeyFrame(items)
                self.undoStack.push(RemoveWavesUndo(self, [items]))

    def mergeRequested(self, items):
        indexes = [item.index for item in items]
        start = min(indexes)
        end = max(indexes)
        if end - start < 2:
            return
        self.undoStack.push(MergeWavesUndo(self, start, end))

    def pasteTransform(self, transform, values):
        #create undoCommand here
        transform.setParameters(values)

    def reverseWaveTable(self):
        selection = self.waveTableScene.currentSelection
        if len(selection) == 1:
            return
        elif not selection:
            start = 0
            end = 64
        else:
            start = selection[0].index
            end = selection[-1].index + 1
        self.undoStack.push(ReverseWaveTableUndo(self, start, end))

    def distributeWaveTable(self):
        selection = self.waveTableScene.currentSelection
        if len(selection) == 1 or len(self.keyFrames) == 1:
            return
        elif not selection:
            if len(self.keyFrames) >= 63:
                return
            start = 0
            end = 64
        else:
            start = selection[0].index
            end = selection[-1].index
            if len(selection) >= end - start:
                return
            end += 1
        self.undoStack.push(DistributeWaveTableUndo(self, start, end))

    def setCurrentKeyFrame(self, keyFrame, activate=False):
        if activate:
            self.mainTabWidget.setCurrentWidget(self.waveEditTab)
        self.waveScene.setKeyFrame(keyFrame)
        self.setNextKeyFrame()

    def setCurrentTransformMode(self, mode):
        self.nextTransformCycler.setCurrentIndex(mode)
        self.currentTransform.setMode(mode)

    def setCurrentTransformCurve(self, index):
        self.currentTransform.setData({'curve': self.curveTransformCombo.itemData(index)})

#    def editTransform(self):
#        if not self.currentTransform.isValid() or self.currentTransform.isContiguous() or not self.currentTransform.mode:
##            self.nextTransformEditBtn.setEnabled(False)
#            return
#        if self.currentTransform.mode == self.currentTransform.CurveMorph:
#            dialog = CurveMorphDialog(self)
#        else:
#            return
#        dialog.exec_(self.currentTransform)

    def setNextKeyFrame(self):
        if self.currentTransform:
            self.currentTransform.changed.disconnect(self.updateTransform)
        self.currentTransform = self.waveScene.currentKeyFrame.nextTransform
        if self.currentTransform:
            self.currentTransform.changed.connect(self.updateTransform)
        self.updateTransform()

    def updateTransform(self):
        if len(self.keyFrames) > 1 and self.currentTransform and self.currentTransform.isValid() and not self.currentTransform.isContiguous():
            self.nextTransformCombo.setEnabled(True)
            self.nextTransformCombo.blockSignals(True)
            self.nextTransformCombo.setCurrentIndex(self.currentTransform.mode)
            self.nextTransformCombo.blockSignals(False)
            self.nextTransformCycler.setCurrentIndex(self.currentTransform.mode)
            if self.currentTransform.mode == WaveTransformItem.CurveMorph:
                self.curveTransformCombo.blockSignals(True)
                self.curveTransformCombo.setCurrentCurve(self.currentTransform.curve)
                self.curveTransformCombo.blockSignals(False)
#            self.nextTransformEditBtn.setEnabled(self.currentTransform.mode > 1)
        else:
            self.nextTransformCombo.setEnabled(False)
#            self.nextTransformEditBtn.setEnabled(False)
        try:
            self.nextView.setWave(self.currentTransform.nextItem)
        except Exception as e:
            print('no update?', e)

    def _selectTransform(self, transform, activate=False):
        if not transform.isValid() or transform.isContiguous() or not transform.mode or len(self.keyFrames) == 1:
            self.mainTabWidget.setHidden(2, True)
        else:
            self.mainTabWidget.setHidden(2, False)
            if activate:
                self.mainTabWidget.setCurrentIndex(2)
            self.transformTab.setTransform(transform)

    def setKeyFrameIndex(self, item):
        prev = 0
        next = item.index
        for keyFrame in self.keyFrameScene.keyFrames:
            if keyFrame.index < item.index:
                prev = keyFrame.index
            elif keyFrame.index > item.index:
                next = keyFrame.index
                break
        if item.final:
            next = 128
        res = SetIndexDialog(self, item.index + 1, prev + 2, next).exec_()
        if res is not None:
            item.setIndex(res - 1)

    def importFiles(self):
        files = QtWidgets.QFileDialog.getOpenFileNames(self, 'Import WaveTable(s)', 
            QtGui.QDesktopServices.storageLocation(QtGui.QDesktopServices.HomeLocation), 
            'WaveTable files (*.bwt *.syx *.mid);;Bigglesworth WaveTables (*.bwt);;SysEx files (*.syx);;MIDI files (*.mid);;All files (*)')
        if not files:
            return
        rows = []
        invalid = []
#        [rows.extend(self.importFile(filePath)) for filePath in files]
        for filePath in files:
            try:
                fileInfo = QtCore.QFileInfo(filePath)
                assert fileInfo.exists()
                assert fileInfo.isFile()
                assert 0 < fileInfo.size() < 1048576
                created = fileInfo.created().toMSecsSinceEpoch()
                try:
                    res = self.importMidiData(midifile.read_midifile(filePath), created)
                    if res:
                        rows.extend(res)
                    else:
                        invalid.append(fileInfo)
                    continue
                except Exception as e:
                    print(e)
                file = QtCore.QFile(filePath)
                assert file.open(QtCore.QIODevice.ReadOnly)
                stream = QtCore.QDataStream(file)
                raw = stream.readString()
                if raw:
                    data = []
                    while not stream.atEnd():
                        data.append(stream.readQVariant())
                    res = self.importWaveTableData(raw, data, created)
                    if res:
                        rows.extend(res)
                    else:
                        invalid.append(fileInfo)
                else:
#                    if not fileInfo.size() % 26240:
                    file.seek(0)
                    res = self.importSysExData(map(ord, stream.readRawData(fileInfo.size())), created)
                    if res:
                        rows.extend(res)
                    else:
                        invalid.append(fileInfo)
            except Exception as e:
                print(e)
                invalid.append(fileInfo)
        if rows:
            selection = QtCore.QItemSelection(self.localProxy.index(rows[0], 0), self.localProxy.index(rows[-1], 0))
            self.localWaveTableList.selectionModel().select(selection, QtCore.QItemSelectionModel.ClearAndSelect|QtCore.QItemSelectionModel.Rows)
            self.localWaveTableList.resizeColumnToContents(NameColumn)
            self.localWaveTableList.resizeColumnToContents(EditedColumn)
        if invalid:
            title = 'Invalid file'
            if len(invalid) == 1:
                text = 'The file "{}" is not a valid wavetable file or is not readable.'.format(invalid[0].fileName())
            else:
                title += 's'
                text = 'The following files are not valid wavetable files or are not readable:\n{}'.format(', '.join(f.fileName() for f in invalid))
            QtWidgets.QMessageBox.warning(self, title, text, QtWidgets.QMessageBox.Ok)

    def importWaveTableData(self, rawXml, fullData, created=None):
        root = ET.fromstring(rawXml)
        if root.tag != 'Bigglesworth' and not 'WaveTableData' in root.getchildren():
            return
        typeElement = root.find('WaveTableData')
#        count = int(typeElement.find('Count'))
        iterData = iter(fullData)
        rows = []
        for wtElement in typeElement.findall('WaveTable'):
            name = wtElement.find('Name').text
            slot = int(wtElement.find('Slot').text)
            waveCount = int(wtElement.find('WaveCount').text)

            byteArray = QtCore.QByteArray()
            stream = QtCore.QDataStream(byteArray, QtCore.QIODevice.WriteOnly)
            stream.writeInt(waveCount)
            stream.writeQVariant(iterData.next())

            row = self.localProxy.rowCount()
            self.localProxy.insertRows(row, 1)
            dbData = [str(uuid4()), name, slot, created if created else QtCore.QDateTime.currentMSecsSinceEpoch(), byteArray]
            for column, data in enumerate(dbData):
                self.localProxy.setData(self.localProxy.index(row, column), data)
            self.waveTableModel.submitAll()
            rows.append(row)
        return rows

    def sysEx2Int(self, values):
        intList = []
        current = None
        countBytes = 0
        for v in values:
            if current is not None:
                if v & 128:
                    current = (current << 7) + (v & 127)
                    countBytes -= 1
                else:
                    intList.append((current << 7) + v)
                    current = None
                    if countBytes <= 0:
                        countBytes = abs(countBytes) + 1
            else:
                if v & 128:
                    current = v & 127
#                    if countBytes <= 0:
#                        countBytes -= 1
                else:
                    intList.append(v)
        if current:
            intList.append(current|128)
        return countBytes, intList

    def decodeWaveValues(self, sysexData, wave):
        values = []
        if len(sysexData) == 408 and sysexData[:2] == [IDW, IDE] and sysexData[3] == WTBD and sysexData[5] == wave:
            values = []
            bitValues = iter(sysexData[7:391])
            for s in xrange(128):
                value = (bitValues.next() << 14) + (bitValues.next() << 7) + bitValues.next()
                if value >= 1048576:
                    value -= 2097152
                values.append(value)
#        else:
#            print(sysexData[5], wave)
        return values

    def importMidiData(self, pattern, created=None):
        rows = []
        wave = 0
        currentTable = []
        for track in pattern:
            for event in track:
                if isinstance(event, midifile.SysexEvent):
                    countBytes, data = self.sysEx2Int(event.data)
#                    print(len(event.data), countBytes, event.data[:10], event.data[-2:])
                    sysexData = data[countBytes:]
#                    print(len(event.data), countBytes, len(data))
                    values = self.decodeWaveValues(sysexData, wave)
                    if values:
                        currentTable.append(values)
                        if len(currentTable) == 64:
                            slot = sysexData[4]
                            name = ''.join([str(unichr(l)) for l in sysexData[391:405]])
                            print(slot, name)
                            row = self.localProxy.rowCount()
                            self.localProxy.insertRows(row, 1)
                            snapshot = []
                            for w, values in enumerate(currentTable):
                                snapshot.append((uuid4(), w, values))
                                snapshot.append((0, {}, w))
                            byteArray = QtCore.QByteArray()
                            stream = QtCore.QDataStream(byteArray, QtCore.QIODevice.WriteOnly)
                            stream.writeInt(64)
                            stream.writeQVariant(snapshot)
                            dbData = [str(uuid4()), name, slot, created if created else QtCore.QDateTime.currentMSecsSinceEpoch(), byteArray]
                            print(created)
                            for column, itemData in enumerate(dbData):
                                self.localProxy.setData(self.localProxy.index(row, column), itemData)
                            self.waveTableModel.submitAll()
                            rows.append(row)
                            wave = 0
                            currentTable = []
                        else:
                            wave += 1
        return rows

    def importSysExData(self, data, created=None):
        if not data[0] == 240:
            return []
        rows = []
        data = iter(data)
        while True:
            currentTable = []
            wave = 0
            while wave <= 63:
                try:
                    #ignore INIT
                    data.next()
                    sysexData = []
                    value = data.next()
                    while value != 0xf7:
                        sysexData.append(value)
                        try:
                            value = data.next()
                        except Exception as e:
                            print('inner', e)
                            break
                    else:
                        values = self.decodeWaveValues(sysexData, wave)
                        if values:
                            currentTable.append(values)
                            wave += 1
                            continue
                    break
                except Exception as e:
                    print('finito?', e)
                    break
            else:
                slot = sysexData[4]
                name = ''.join([str(unichr(l)) for l in sysexData[391:405]])
                row = self.localProxy.rowCount()
                self.localProxy.insertRows(row, 1)
                snapshot = []
                for wave, values in enumerate(currentTable):
                    snapshot.append((uuid4(), wave, values))
                    snapshot.append((0, {}, wave))
                byteArray = QtCore.QByteArray()
                stream = QtCore.QDataStream(byteArray, QtCore.QIODevice.WriteOnly)
                stream.writeInt(64)
                stream.writeQVariant(snapshot)
                dbData = [str(uuid4()), name, slot, created if created else QtCore.QDateTime.currentMSecsSinceEpoch(), byteArray]
                for column, itemData in enumerate(dbData):
                    self.localProxy.setData(self.localProxy.index(row, column), itemData)
                self.waveTableModel.submitAll()
                rows.append(row)
                continue
            break
#        if rows:
        return rows

#    def createDumpDataFromIndex(self, index):
#        name = index.sibling(index.row(), NameColumn).data()
#        slot = index.sibling(index.row(), SlotColumn).data()
#        raw = index.sibling(index.row(), DataColumn).data()
#        ds = (QtCore.QDataStream(raw, QtCore.QIODevice.ReadOnly))
#        ds.readInt()
#        virtualKeyFrames = VirtualKeyFrames(ds.readQVariant())
#        waves = virtualKeyFrames.fullTableValues(-1, 1, -1, export=True)
#        return self.createDumpData(name, slot, waves)

    def createDumpData(self, *args):
        if args:
            if len(args) == 1:
                index = args[0]
                if isinstance(index.model(), QtCore.QSortFilterProxyModel):
                    index = index.model().mapToSource(index)
                name = index.sibling(index.row(), NameColumn).data()
                slot = index.sibling(index.row(), SlotColumn).data()
                raw = index.sibling(index.row(), DataColumn).data()
                ds = (QtCore.QDataStream(raw, QtCore.QIODevice.ReadOnly))
                ds.readInt()
                virtualKeyFrames = VirtualKeyFrames(ds.readQVariant())
                waves = virtualKeyFrames.fullTableValues(-1, 1, -1, export=True)
            else:
                name, slot, waves = args
        else:
            name = self.nameEdit.text()
            slot = self.slotSpin.value()
            waves = self.keyFrames.fullTableValues(-1, 1, -1, export=True)

        sysexList = []
        nameData = []
        for l in name.ljust(14, u' '):
            try:
                c = ord(l)
                assert 32 <= c <= 126
                nameData.append(c)
            except:
                nameData.append(127)

        blofeldID = 0
        for n, wave in enumerate(waves):
            sysexData = [INIT, IDW, IDE, blofeldID, WTBD, slot, n, 0]
            for value in wave:
                value = int(value)
                if value < 0:
                    value = pow21 + value
                sysexData.extend((value >> 14, (value >> 7) & 127,  value & 127))
            sysexData.extend(nameData)
            sysexData.extend((0, 0, CHK))
            sysexData.append(END)

            sysexList.append(sysexData)
        return sysexList

    def exportCurrent(self):
        path = QtWidgets.QFileDialog.getSaveFileName(self, 'Export WaveTable',  
            QtGui.QDesktopServices.storageLocation(QtGui.QDesktopServices.HomeLocation) + '/{}.syx'.format(fixFileName(self.nameEdit.text())), 
            'SysEx files (*.syx);;Bigglesworth WaveTables (*.bwt);;All files (*)')
        if not path:
            return

        try:
            file = QtCore.QFile(path)
            print('file?', file)
            assert file
            file.open(QtCore.QIODevice.WriteOnly)
            stream = QtCore.QDataStream(file)
            if not path.endswith('.bwt'):
                dumpData = list(chain(*self.createDumpData()))
#                print(len(dumpData), dumpData[-1])
                assert stream.writeRawData(''.join(chr(c) for c in dumpData))
            else:
                root = ET.Element('Bigglesworth')
                typeElement = ET.SubElement(root, 'WaveTableData')
                countElement = ET.SubElement(typeElement, 'Count')
                countElement.text = '1'
                fullData = []
                wtElement = ET.SubElement(typeElement, 'WaveTable')
                ET.SubElement(wtElement, 'Name').text = self.nameEdit.text().ljust(14, ' ')
                ET.SubElement(wtElement, 'Slot').text = str(self.slotSpin.value())
                ET.SubElement(wtElement, 'WaveCount').text = len(self.keyFrames)
                stream.writeString(ET.tostring(root))
                for data in fullData:
                    stream.writeQVariant(self.keyFrames.getSnapshot())
            file.close()
        except Exception as e:
            print('Exception', e)
            QtWidgets.QMessageBox.warning(self, 'Error writing data', 
                'There was a problem while writing data, check file permissions and available space', 
                QtWidgets.QMessageBox.Ok)

    def exportFiles(self):
        selection = self.localWaveTableList.selectionModel().selectedRows()
        if not selection:
            return
        elif len(selection) == 1:
            caption = 'Export WaveTable'
            name = selection[0].sibling(selection[0].row(), 1).data().strip()
            filters = 'SysEx files (*.syx);;Bigglesworth WaveTables (*.bwt);;All files (*)'
            extension = 'syx'
        else:
            caption = 'Export WaveTables'
            name = 'WaveTables-' + QtCore.QDate.currentDate().toString('dd-MM-yy')
            filters = 'Bigglesworth WaveTables (*.bwt);;All files (*)'
            extension = 'bwt'
        path = QtWidgets.QFileDialog.getSaveFileName(self, caption,  
            QtGui.QDesktopServices.storageLocation(QtGui.QDesktopServices.HomeLocation) + '/{}.{}'.format(fixFileName(name), extension), 
            filters)
        if not path:
            return

        try:
            file = QtCore.QFile(path)
            print('file?', file)
            assert file
            file.open(QtCore.QIODevice.WriteOnly)
            stream = QtCore.QDataStream(file)
            if len(selection) == 1 and not path.endswith('.bwt'):
                dumpData = list(chain(*self.createDumpData(selection[0])))
#                index = selection[0]
#                name = index.sibling(index.row(), 1).data()
#                slot = index.sibling(index.row(), 2).data()
#                raw = self.localProxy.index(index.row(), 3).data()
#                ds = (QtCore.QDataStream(raw, QtCore.QIODevice.ReadOnly))
#                ds.readInt()
#                virtualKeyFrames = VirtualKeyFrames(ds.readQVariant())
#                waves = virtualKeyFrames.fullTableValues(-1, 1, -1, export=True)
#                dumpData = list(chain(*self.createDumpData(name, slot, waves)))
#                print(len(dumpData), dumpData[-1])
                assert stream.writeRawData(''.join(chr(c) for c in dumpData))
            else:
                root = ET.Element('Bigglesworth')
                typeElement = ET.SubElement(root, 'WaveTableData')
                countElement = ET.SubElement(typeElement, 'Count')
                countElement.text = str(len(selection))
                fullData = []
                for index in selection:
                    name = index.sibling(index.row(), 1).data()
                    slot = index.sibling(index.row(), 2).data()
                    raw = self.localProxy.index(index.row(), 3).data()
                    ds = (QtCore.QDataStream(raw, QtCore.QIODevice.ReadOnly))
                    count = ds.readInt()
                    fullData.append(ds.readQVariant())
                    wtElement = ET.SubElement(typeElement, 'WaveTable')
                    ET.SubElement(wtElement, 'Name').text = name
                    ET.SubElement(wtElement, 'Slot').text = str(slot)
                    ET.SubElement(wtElement, 'WaveCount').text = str(count)
                stream.writeString(ET.tostring(root))
                for data in fullData:
                    stream.writeQVariant(data)
            file.close()
        except Exception as e:
            print('Exception', e)
            QtWidgets.QMessageBox.warning(self, 'Error writing data', 
                'There was a problem while writing data, check file permissions and available space', 
                QtWidgets.QMessageBox.Ok)

    def copyFromDumpSlot(self, slot, clone=False):
        index = self.dumpModel.index(slot + 6, UidColumn)
        found = self.waveTableModel.match(self.waveTableModel.index(0, UidColumn), QtCore.Qt.DisplayRole, 
            index.data(), flags=QtCore.Qt.MatchExactly)
        if found:
            print('trovat')
            row = found[0].row()
        else:
            print('nuovo')
            row = self.waveTableModel.rowCount()
        uid = index.data() if clone else str(uuid4())
        self.waveTableModel.insertRows(row, 1)
        self.waveTableModel.setData(self.waveTableModel.index(row, UidColumn), uid)
        self.waveTableModel.setData(self.waveTableModel.index(row, NameColumn), index.sibling(index.row(), NameColumn).data())
        self.waveTableModel.setData(self.waveTableModel.index(row, SlotColumn), index.sibling(index.row(), SlotColumn).data())
        self.waveTableModel.setData(self.waveTableModel.index(row, EditedColumn), index.sibling(index.row(), EditedColumn).data())
        self.waveTableModel.setData(self.waveTableModel.index(row, DataColumn), index.sibling(index.row(), DataColumn).data())
        self.waveTableModel.setData(self.waveTableModel.index(row, PreviewColumn), index.sibling(index.row(), PreviewColumn).data())
        if not self.waveTableModel.submitAll():
            print(self.waveTableModel.lastError().databaseText())
#        print('correttamente aggiornato, riga {}'.format(row))

    def copyFromDumpUid(self, uid, clone=False):
        found = self.dumpModel.match(self.dumpModel.index(0, UidColumn), QtCore.Qt.DisplayRole, uid, flags=QtCore.Qt.MatchExactly)[0]
        self.copyFromDumpSlot(found.sibling(found.row(), SlotColumn).data(), clone)

#    def restoreFromDumpUid(self, uid):
#        found = self.dumpModel.match(self.dumpModel.index(0, UidColumn), QtCore.Qt.DisplayRole, uid)[0]

    def searchAndCompareDumpLocal(self, index, uid):
        found = self.waveTableModel.match(self.waveTableModel.index(0, UidColumn), QtCore.Qt.DisplayRole, uid, flags=QtCore.Qt.MatchExactly)
        if not found:
            return False
        found = found[0]
        res = []
        res.append(found.sibling(found.row(), NameColumn).data() == index.sibling(index.row(), NameColumn).data())
        res.append(found.sibling(found.row(), SlotColumn).data() == index.sibling(index.row(), SlotColumn).data())
        res.append(found.sibling(found.row(), EditedColumn).data() == index.sibling(index.row(), EditedColumn).data())
        res.append(found.sibling(found.row(), DataColumn).data() == index.sibling(index.row(), DataColumn).data())
#        print(type(found.sibling(found.row(), DataColumn).data()), type(index.sibling(index.row(), DataColumn).data()))
        return res

    def getNameFromDump(self, req):
        if isinstance(req, (int, long)):
            return self.dumpModel.index(req + 6, NameColumn).data()
        if isinstance(req, (str, unicode)):
            found = self.dumpModel.match(self.dumpModel.index(0, UidColumn), QtCore.Qt.DisplayRole, req, flags=QtCore.Qt.MatchExactly)[0]
            return found.sibling(found.row(), NameColumn).data()

    def saveAndDump(self):
        self.settings.beginGroup('MessageBoxes')
        if not self.canDump() and self.settings.value('WaveTableNoMidiDump', True, bool):
            msgBox = AdvancedMessageBox(self, 'No MIDI connection', 
                'No MIDI device is connected! The wavetable will only be saved in the dump list.<br/><br/>' \
                'Undumped wavetables can be sent later from the "Blofeld" tab in the "Wavetable library" panel.', 
                icon=AdvancedMessageBox.Warning, checkBox=True)
            msgBox.exec_()
            if msgBox.isChecked():
                self.settings.setValue('WaveTableNoMidiDump', False)
        self.settings.endGroup()

        slot = self.slotSpin.value()
        sameUid = sameUidSlot = None
        if self.currentWaveTable:
            sameUid = self.blofeldProxy.match(self.blofeldProxy.index(0, UidColumn), QtCore.Qt.DisplayRole, 
                self.currentWaveTable, flags=QtCore.Qt.MatchExactly)
            if sameUid:
                sameUid = sameUid[0]
                sameUidSlot = sameUid.sibling(sameUid.row(), SlotColumn).data()
        sameSlotIndex = self.dumpModel.index(slot + 6, UidColumn)
#        sameSlotUid = self.blofeldProxy.mapFromSource(sameSlotIndex).data()
        sameSlotUid = sameSlotIndex.data()
#        print(sameUidSlot, sameSlotUid)
        if sameUid and sameUidSlot == slot:
            #uid and slot match, just save and dump
            pass
        elif sameSlotUid:
            #the slot is occupied by another wavetable
            if sameUidSlot is not None:
                askDuplicate = '<br/><br/>NOTE: the wavetable you are going to dump has been ' \
                    'dumped on slot {} too. By proceeding, another copy will be created to ' \
                    'keep track of it.'.format(sameUidSlot)
            else:
                askDuplicate = ''
            dumpedFound = self.searchAndCompareDumpLocal(sameSlotIndex, sameSlotUid)
            if not dumpedFound:
                #dumped wavetable is not in local, recreate copy?
                if QtWidgets.QMessageBox.question(self, 'Wavetable overwrite', 
                    'Slot {} already contains a previously dumped wavetable that is not ' \
                    'stored locally anymore.<br/>If you proceed, a local copy will be recreated ' \
                    'to keep track of it, then the current one will be dumped.{}'.format(slot, askDuplicate), 
                    QtWidgets.QMessageBox.Ok|QtWidgets.QMessageBox.Cancel) != QtWidgets.QMessageBox.Ok:
                        return
                self.copyFromDumpUid(sameSlotUid)
            elif all(dumpedFound):
                #uid exists as dumped and it fully matches
                if QtWidgets.QMessageBox.question(self, 'Wavetable overwrite', 
                    'Slot {} already contains another wavetable. Do you want to ' \
                    'overwrite it?<br/>That wavetable ("{}") is correctly stored locally.{}'.format(
                        slot, sameSlotIndex.sibling(sameSlotIndex.row(), NameColumn).data(), askDuplicate), 
                    QtWidgets.QMessageBox.Ok|QtWidgets.QMessageBox.Cancel) != QtWidgets.QMessageBox.Ok:
                        return
            else:
                text = 'Slot {} already contains another wavetable (named "{}"), but the dumped data ' \
                    'doesn\'t match with the local copy. Press "Save as new" to create a new copy ' \
                    'from the dumped version, or "Ignore" to discard the previously dumped ' \
                    'wavetable, which will be lost permanently.<br/><br/>' \
                    'Unmatching content:<ul><li>'.format(slot, self.getNameFromDump(slot))
                unmatching = []
                for c, label in zip(dumpedFound, ('Name', 'Slot', 'Modified date', 'Wavetable contents')):
                    if not c:
                        unmatching.append(label)
                text += '</li><li>'.join(unmatching) + '</li></ul>{}'.format(askDuplicate)
                msgBox = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Question, 'Wavetable overwrite', 
                    text, parent=self)
                saveBtn = msgBox.addButton(QtWidgets.QMessageBox.Save)
                saveBtn.setText('Save as new')
                msgBox.addButton(QtWidgets.QMessageBox.Ignore)
                msgBox.addButton(QtWidgets.QMessageBox.Cancel)
                res = msgBox.exec_()
                if res == QtWidgets.QMessageBox.Save:
                    self.copyFromDumpUid(sameSlotUid)
                elif res != QtWidgets.QMessageBox.Ignore:
                    return
            if askDuplicate:
                self.copyFromDumpSlot(sameUidSlot)
#            print('slot occupato', self.currentWaveTable)
        elif sameUidSlot is not None:
            #uid exists in another slot
            #ask to change uid, save and dump
            if QtWidgets.QMessageBox.question(self, 'Wavetable slot changed', 
                'This wavetable has been previously dumped to slot {}.<br/>If you proceed, ' \
                'a copy will be created to keep track of it, then the current one will be dumped.'.format(sameUidSlot), 
                QtWidgets.QMessageBox.Ok|QtWidgets.QMessageBox.Cancel) != QtWidgets.QMessageBox.Ok:
                    return
            self.copyFromDumpSlot(sameUidSlot)
        else:
            text = 'There is no way to know the actual wavetable contents of ' \
                'Blofeld\'s wavetables, and it\'s not possible to backup previously existing' \
                'tables that have been saved with another software.<br/>' \
                ''
#            if not QtWidgets.QMessageBox.question(self, 'Wavetable overwrite', 
#                'Slot {} seems empty. Do you want to overwrite the existing table on the Blofeld?')

        edited, data, preview = self.save()
#        dumpData = self.createDumpData()
        slotRow = self.slotSpin.value() + 6
        self.dumpModel.setData(self.dumpModel.index(slotRow, UidColumn), self.currentWaveTable)
        self.dumpModel.setData(self.dumpModel.index(slotRow, NameColumn), self.nameEdit.text().ljust(14, ' '))
        self.dumpModel.setData(self.dumpModel.index(slotRow, EditedColumn), edited)
        self.dumpModel.setData(self.dumpModel.index(slotRow, DataColumn), data)
        self.dumpModel.setData(self.dumpModel.index(slotRow, PreviewColumn), preview)
        self.dumpModel.setData(self.dumpModel.index(slotRow, DumpedColumn), 0)
        self.dumpModel.submitAll()
        if self.canDump():
            self.initializeDump()

    def initializeDump(self, *args):
        slotToSave = []
        tableData = []
        if not args:
            tableData.append((self.nameEdit.text(), self.slotSpin.value()))
            slotToSave.append(self.slotSpin.value())
            self.sysexList = [list(reversed(self.createDumpData()))]
        else:
            if isinstance(args, (tuple, list)) and len(args) == 1:
                args = args[0]
            self.sysexList = []
            for index in args:
                if isinstance(index.model(), QtCore.QSortFilterProxyModel):
                    index = index.model().mapToSource(index)
                name = index.sibling(index.row(), NameColumn).data()
                slot = index.sibling(index.row(), SlotColumn).data()
                raw = index.sibling(index.row(), DataColumn).data()
                ds = (QtCore.QDataStream(raw, QtCore.QIODevice.ReadOnly))
                ds.readInt()
                virtualKeyFrames = VirtualKeyFrames(ds.readQVariant())
                waves = virtualKeyFrames.fullTableValues(-1, 1, -1, export=True)

                slotToSave.append(slot)
                tableData.append((name, slot))
                self.sysexList.append(list(reversed(self.createDumpData(name, slot, waves))))

        self.currentSysexData = self.sysexList.pop(0)
        self.slotToSave = reversed(slotToSave)
        self.stopped = False
        QtCore.QTimer.singleShot(250, lambda: self.dumper.exec_(tableData))

    def stopRequested(self):
        self.stopped = True

    def sendData(self):
        if self.currentSysexData:
#            print('sending sysex {}'.format(len(sysex)))
            sysex = self.currentSysexData.pop()
            self.midiEvent.emit(SysExEvent(1, sysex))
            self.dumpTimer.start()
            return
        elif not self.stopped and self.sysexList:
#            print('new wavetable, sending first sysex')
            self.currentSysexData = self.sysexList.pop(0)
            sysex = self.currentSysexData.pop()
            self.midiEvent.emit(SysExEvent(1, sysex))
            self.dumpTimer.start()

        #remember that the actual slot index is +6
        self.dumpModel.setData(self.dumpModel.index(self.slotToSave.next() + 6, DumpedColumn), 1)
        self.dumpModel.submitAll()

    def save(self, addDump=False):
        row = None
        slot = self.slotSpin.value()
        if self.currentWaveTable:
            res = self.localProxy.match(self.localProxy.index(0, UidColumn), QtCore.Qt.DisplayRole, 
                self.currentWaveTable, flags=QtCore.Qt.MatchExactly)
            if res:
                row = res[0].row()
        else:
            self.currentWaveTable = str(uuid4())
        if row is None:
            row = self.localProxy.rowCount()
            self.localProxy.insertRows(row, 1)

        edited = QtCore.QDateTime.currentMSecsSinceEpoch()
        preview = self.getPreview()
        byteArray = QtCore.QByteArray()
        stream = QtCore.QDataStream(byteArray, QtCore.QIODevice.WriteOnly)
        stream.writeInt(len(self.keyFrames))
        stream.writeQVariant(self.keyFrames.getSnapshot())
        dbData = [self.currentWaveTable, self.nameEdit.text().ljust(14, ' '), slot, edited, byteArray, preview]
        for column, data in enumerate(dbData):
            self.localProxy.setData(self.localProxy.index(row, column), data)
        self.waveTableModel.submitAll()
        if self.localProxy.rowCount() == 1:
            self.localWaveTableList.resizeColumnToContents(NameColumn)
            self.localWaveTableList.resizeColumnToContents(EditedColumn)
        self.windowsDict[self.currentWaveTable] = self
        self._isClean = True
        self.undoStack.setClean()
        self.undoView.setCleanIcon(QtGui.QIcon.fromTheme('document-save'))
        self.checkClean(self.undoStack.isClean())
        self.blofeldWaveTableList.viewport().update()
        if addDump:
#            dumpIndex = self.dumpModel.index(slot + 6)
            self.localWaveTableList.setCurrentIndex(self.localProxy.index(row, UidColumn))
            slot += 6
            for column, data in enumerate(dbData):
                if column == SlotColumn:
                    continue
                self.dumpModel.setData(self.dumpModel.index(slot, column), data)
            self.dumpModel.submitAll()
            self.blofeldWaveTableList.setCurrentIndex(self.blofeldProxy.mapFromSource(self.dumpModel.index(slot, UidColumn)))
        return edited, byteArray, preview

    def openFromModel(self, index):
        if index.model() == self.waveTableModel:
            self.openFromLocalList(self.localProxy.mapFromSource(index))
        elif index.model() == self.dumpModel:
            self.openFromDumpList(self.blofeldProxy.mapFromSource(index))
        else:
            print('Not found?!', index.row(), index.model())

    def openFromLocalList(self, index):
        uid = self.localProxy.index(index.row(), UidColumn).data()
        if not self.currentWaveTable:
            self.openFromUid(uid)
        elif self.currentWaveTable != uid:
            new = self.windowsDict.get(uid)
            if not new:
                new = WaveTableWindow(uid)
            new.show()
            new.activateWindow()
            return new

    def openFromDumpList(self, index):
#        slot = self.blofeldProxy.mapToSource(index).row()
        slot = index.sibling(index.row(), SlotColumn).data()
        if slot < 80:
            return
        uid = self.blofeldProxy.index(index.row(), UidColumn).data()
        res = self.localProxy.match(self.localProxy.index(0, 0), QtCore.Qt.DisplayRole, uid, flags=QtCore.Qt.MatchExactly)
        if res:
            window = self.openFromLocalList(res[0])
            if window and window.waveTableDock.isVisible():
                window.dockTabWidget.setCurrentIndex(1)
        else:
            if not uid:
                if QtWidgets.QMessageBox.question(self, 'Create new wavetable', 
                    'Do you want to create a new wavetable at slot {}?'.format(slot), 
                    QtWidgets.QMessageBox.Ok|QtWidgets.QMessageBox.Cancel) != QtWidgets.QMessageBox.Ok:
                        return
                if not self.currentWaveTable and not self.isWindowModified():
                    window = self
                else:
                    window = self.createNewWindow()
                window.slotSpin.blockSignals(True)
                window.slotSpin.setValue(slot)
                window.slotSpin.blockSignals(False)
                window.save(True)
                if window.waveTableDock.isVisible():
                    window.dockTabWidget.setCurrentIndex(1)
            else:
                if QtWidgets.QMessageBox.question(self, 'Restore wavetable', 
                    'The selected wavetable has been previously dumped, but the local copy ' \
                    'has been deleted.<br/>Do you want to restore it?', 
                    QtWidgets.QMessageBox.Ok|QtWidgets.QMessageBox.Cancel) != QtWidgets.QMessageBox.Ok:
                        return
                self.copyFromDumpUid(uid, True)
                res = self.localProxy.match(self.localProxy.index(0, 0), QtCore.Qt.DisplayRole, uid, flags=QtCore.Qt.MatchExactly)[0]
                self.openFromLocalList(res)

    def openFromUid(self, uid):
        self.currentWaveTable = uid
        try:
            res = self.waveTableModel.match(self.waveTableModel.index(0, UidColumn), QtCore.Qt.DisplayRole, self.currentWaveTable, flags=QtCore.Qt.MatchExactly)
            row = res[0].row()
        except:
            if isinstance(self.sender(), QtWidgets.QAction):
                self.settings.beginGroup('WaveTables')
                recent = self.settings.value('Recent', [])
                if uid in recent:
                    recent.remove(uid)
                self.settings.setValue('Recent', recent)
                self.settings.endGroup()
            return
        name = self.waveTableModel.index(row, NameColumn).data().rstrip()
        self.nameEdit.setText(name)
        self.setWindowTitle('Wavetable Editor - {} [*]'.format(name))
        self.slotSpin.blockSignals(True)
        self.slotSpin.setValue(self.waveTableModel.index(row, SlotColumn).data())
        self.slotSpin.blockSignals(False)
        byteArray = self.waveTableModel.index(row, DataColumn).data()
        stream = QtCore.QDataStream(byteArray, QtCore.QIODevice.ReadOnly)
        stream.readInt()
        snapshot = stream.readQVariant()
        self.currentWaveTable = uid
        self.keyFrames.setSnapshot(snapshot)
        self.windowsDict[self.currentWaveTable] = self
        self.undoView.setEmptyLabel('{} opened'.format(name))
        self.undoView.setCleanIcon(QtGui.QIcon.fromTheme('document-save'))
        viewIndex = self.localProxy.mapFromSource(self.waveTableModel.index(row, UidColumn))
        self.localWaveTableList.setCurrentIndex(viewIndex)
        self.localWaveTableList.scrollTo(viewIndex)

        self.settings.beginGroup('WaveTables')
        recent = self.settings.value('Recent', [])
        if uid in recent:
            recent.remove(uid)
        recent.insert(0, uid)
        self.settings.setValue('Recent', recent[:10])
        self.settings.endGroup()


    def createNewWindow(self):
        for window in self.openedWindows:
            if not window.isVisible() and not window.currentWaveTable and not window.undoStack.count():
                break
        else:
            window = WaveTableWindow()
        window.show()
        window.activateWindow()
        return window

    def checkSelection(self, first, last):
        selection = self.localWaveTableList.selectionModel().selectedRows()
        self.deleteBtn.setEnabled(len(selection))
        self.exportLibraryBtn.setEnabled(len(selection))
        self.duplicateBtn.setEnabled(len(selection) == 1)

    def rect2Poly(self, rect):
        return QtGui.QPolygonF([rect.topLeft(), rect.topRight(), rect.bottomRight(), rect.bottomLeft()])

    def getPreview(self):
        pixmap = QtGui.QPixmap(128, 72)
        pixmap.fill(QtCore.Qt.transparent)
        qp = QtGui.QPainter(pixmap)
        qp.setRenderHints(qp.Antialiasing)
        if len(self.keyFrames) == 1:
            targetRect = QtCore.QRectF(0, 4, 128, 64)
            qp.setPen(self.waveScene.wavePen)
            wavePath = self.keyFrames[0].wavePath
            scale = QtGui.QTransform()
            #for some reason, using QRectF doesn't work
            QtGui.QTransform.quadToQuad(self.rect2Poly(wavePath.boundingRect()), self.rect2Poly(targetRect), scale)
            qp.setTransform(scale)
            qp.drawPath(wavePath)
        else:
            targetRect = QtCore.QRectF(0, 0, 128, 64)
            sourceRect = self.waveTableScene.front.sceneBoundingRect()
            sourceRect |= self.waveTableScene.back.sceneBoundingRect()
            qp.setTransform(self.waveTableView.shearTransform)
            qp.translate(0, -10)
            self.waveTableScene.getPreview(qp, targetRect, sourceRect)
        qp.end()
        byteArray = QtCore.QByteArray()
        buffer = QtCore.QBuffer(byteArray)
        pixmap.save(buffer, 'PNG', 32)
        print('img size: {}'.format(byteArray.size()))
        return byteArray

    def duplicateWaveTable(self):
        selection = [index.row() for index in self.localWaveTableList.selectionModel().selectedRows()]
        if len(selection) != 1:
            return

    def deleteWaveTables(self):
        selection = [index.row() for index in self.localWaveTableList.selectionModel().selectedRows()]
        if not selection:
            return
        count = len(selection)
        title = 'Delete wavetable'
        text = 'Do you want to permanently delete '
        if count == 1:
            text += 'the wavetable "{}"?'.format(self.localProxy.index(selection[0], 1).data().strip())
        else:
            title += 's'
            text += 'the {} selected wavetables?'.format(count)
        text += '\n\nNOTE: the operation cannot be undone!'
        if QtWidgets.QMessageBox.question(self, title, text, 
            QtWidgets.QMessageBox.Ok|QtWidgets.QMessageBox.Cancel) != QtWidgets.QMessageBox.Ok:
                return
        start = min(selection)
        end = max(selection)
        if end - start + 1 == count:
            self.localProxy.removeRows(min(selection), len(selection))
        else:
            for row in reversed(sorted(selection)):
                self.localProxy.removeRows(row, 1)
        self.waveTableModel.submitAll()

    def checkRemoval(self, row):
        if self.currentWaveTable and self.localProxy.index(row, 0).data() == self.currentWaveTable:
            self._isClean = False

    def checkClean(self, clean):
        self.setWindowModified(not (clean and self._isClean))

    def isDumpClean(self):
        hasContents = 0
        for row in range(86, 125):
            if self.dumpModel.index(row, UidColumn).data():
                hasContents = 2
                if not self.dumpModel.index(row, DumpedColumn).data():
                    return 1
        return hasContents

    def blofeldCount(self):
        return len([row for row in range(86, 125) if self.dumpModel.index(row, UidColumn).data()])

    def undumpedCount(self):
        count = 0
        for row in range(86, 125):
            if self.dumpModel.index(row, UidColumn).data() and not self.dumpModel.index(row, DumpedColumn).data():
                count += 1
        return count

    @QtCore.pyqtSlot()
    def checkDumps(self, canDump=None):
        res = self.isDumpClean()
        if canDump is None:
            canDump = self.canDump()
        self.dumpAllBtn.setEnabled(res and canDump)
        self.applyBtn.setEnabled(res == 1 and canDump)
#        hasContents = False
#        for row in range(86, 125):
#            if self.dumpModel.index(row, UidColumn).data():
#                hasContents = True
#                if not self.dumpModel.index(row, DumpedColumn).data():
#                    self.applyBtn.setEnabled(True)
#                    break
#        else:
#            self.applyBtn.setEnabled(False)
#        self.dumpAllBtn.setEnabled(hasContents)

    def showMidiMenu(self):
        menu = QtWidgets.QMenu()
        connected = [conn.dest for conn in QtWidgets.QApplication.instance().connections[1]]
        if not isinstance(self.midiDevice, TestMidiDevice):
            for clientId in sorted(self.graph.client_id_dict.keys()):
                client = self.graph.client_id_dict[clientId]
                if client == self.midiDevice.input.client:
                    continue
                portDict = self.graph.port_id_dict[clientId]
                ports = []
                for portId in sorted(portDict.keys()):
                    port = portDict[portId]
                    if not port.hidden and port.is_input:
                        ports.append(port)
                if ports:
                    menu.addSection(client.name)
                    for port in ports:
                        portAction = menu.addAction(port.name)
                        portAction.setCheckable(True)
                        portAction.setChecked(port in connected)
                        portAction.setData(port)
        res = menu.exec_(QtGui.QCursor.pos())
        if res:
            self.midiConnect.emit(res.data(), True, res.isChecked())

    def showLocalMenu(self, pos):
        pass

    def showBlofeldMenu(self, pos):
        proxyIndex = self.blofeldWaveTableList.indexAt(pos)
        index = self.blofeldProxy.mapToSource(proxyIndex)
        slot = index.sibling(index.row(), SlotColumn).data()
        if not index.isValid():
            return

        selection = self.blofeldWaveTableList.selectionModel().selectedRows(UidColumn)
        selectedUids = [i.data() for i in selection]
        count = len(selectedUids)
        if count == 1 and selectedUids[0] == 'blofeld':
            return

        menu = QtWidgets.QMenu()
        editAction = restoreAction = newAction = dumpAction = False
        
        if not selectedUids:
            newAction = menu.addAction(QtGui.QIcon.fromTheme('document-new'), 'Create wavetable for slot {}'.format(slot))
        if count == 1:
            uid = selectedUids[0]
            valid = self.blofeldProxy.checkValidity(proxyIndex, uid)
            if valid > 0:
                editAction = menu.addAction(QtGui.QIcon.fromTheme('document-edit'), 'Edit wavetable')
            else:
                restoreAction = menu.addAction(QtGui.QIcon.fromTheme('document-save'), 'Restore wavetable')
            menu.addSeparator()
            dumpAction = menu.addAction(QtGui.QIcon(':/images/dump.svg'), 'Dump wavetable')
            dumpAction.setEnabled(self.canDump())
        else:
            dumpAction = menu.addAction(QtGui.QIcon(':/images/dump.svg'), 'Dump {} wavetables'.format(count))
            dumpAction.setEnabled(self.canDump())

        res = menu.exec_(QtGui.QCursor.pos())
        if res == editAction:
            self.openFromUid(uid)
        elif res == newAction:
            if not self.currentWaveTable and not self.isWindowModified():
                window = self
            else:
                window = self.createNewWindow()
            window.slotSpin.blockSignals(True)
            window.slotSpin.setValue(slot)
            window.slotSpin.blockSignals(False)
            window.save(True)
            if window.waveTableDock.isVisible():
                window.dockTabWidget.setCurrentIndex(1)
        elif res == restoreAction:
            self.copyFromDumpUid(uid, True)
            self.openFromUid(uid)
        elif res == dumpAction:
            if count > 2:
                time = parseTime(int(count * 64 * self.dumpTimer.interval() * .0015), True, True, False)
                if not AdvancedMessageBox(self, 'Dump selected wavetables', 
                    'Do you want to dump {} wavetables?\n\nThe process will take about {}.'.format(count, time), 
                    buttons=AdvancedMessageBox.Ok|AdvancedMessageBox.Cancel, 
                    icon=AdvancedMessageBox.Question).exec_() == AdvancedMessageBox.Ok:
                        return
            self.initializeDump(selection)

    def setLastActive(self, active=True):
        if active:
            if self in self.lastActive:
                self.lastActive.remove(self)
            self.lastActive.append(self)
        else:
            try:
                self.lastActive.remove(self)
            except Exception as e:
                print(e)

    def checkActivation(self):
        if self.isClosing:
            return
        if self.isActiveWindow():
            self.setLastActive()
            if self.waveTableDock.visible and self.waveTableDock.isFloating():
                self.waveTableDock.setVisible(True)
        else:
            active = QtWidgets.QApplication.activeWindow()
            if active and active.parent() == self:
                if self.waveTableDock.visible:
                    self.waveTableDock.setVisible(True)
            elif self.waveTableDock.isFloating():
                self.waveTableDock.setVisible(False)

    def dumpAll(self):
        count = self.blofeldCount()
        if count > 1:
            time = parseTime(int(count * 64 * self.dumpTimer.interval() * .0015), True, True, False)
            if not AdvancedMessageBox(self, 'Dump all wavetables', 
                'Do you want to dump all {} wavetables?\n\nThe process will take about {}.'.format(count, time), 
                buttons=AdvancedMessageBox.Ok|AdvancedMessageBox.Cancel, 
                icon=AdvancedMessageBox.Question).exec_() == AdvancedMessageBox.Ok:
                    return
        indexes = []
        for row in range(86, 125):
            index = self.dumpModel.index(row, UidColumn)
            if index.data():
                indexes.append(index)
        self.initializeDump(indexes)

    def dumpUpdated(self):
        indexes = []
        for row in range(86, 125):
            index = self.dumpModel.index(row, UidColumn)
            if index.data() and not index.sibling(index.row(), DumpedColumn).data():
                indexes.append(index)
        if len(indexes) > 2:
            time = parseTime(int(len(indexes) * 64 * self.dumpTimer.interval() * .0015), True, True, False)
            if not AdvancedMessageBox(self, 'Dump updated wavetables', 
                'Do you want to dump {} wavetables?\n\nThe process will take about {}.'.format(len(indexes), time), 
                buttons=AdvancedMessageBox.Ok|AdvancedMessageBox.Cancel, 
                icon=AdvancedMessageBox.Question).exec_() == AdvancedMessageBox.Ok:
                    return
        self.initializeDump(indexes)

    def changeEvent(self, event):
        if event.type() == QtCore.QEvent.ActivationChange:
            self.checkActivation()
        return QtWidgets.QMainWindow.changeEvent(self, event)

    def closeEvent(self, event):
        if not self.isClean():
            res = QtWidgets.QMessageBox.question(self, 'Wavetable not saved', 
                'Wavetable "{}" has been modified, what do you want to do?'.format(self.nameEdit.text()), 
                QtWidgets.QMessageBox.Save|QtWidgets.QMessageBox.Ignore|QtWidgets.QMessageBox.Cancel)
            if res == QtWidgets.QMessageBox.Cancel:
                return event.ignore()
            elif res == QtWidgets.QMessageBox.Save:
                self.save()

        isLast = not any(w.isVisible() for w in self.openedWindows if w != self)
        self.settings.beginGroup('WaveTables')
        self.settings.setValue('Dock', [self.waveTableDock.isVisible(), self.waveTableDock.isFloating(), self.waveTableDock.dockedWidth, self.waveTableDock.floatingWidth, self.waveTableDock.geometry()])
        if isLast:
            self.settings.setValue('AcceptMidiNotes', self.pianoIcon.state)
        self.settings.endGroup()

        self.settings.beginGroup('MessageBoxes')
        if self.settings.value('WaveTableAskUndumpedOnClose', True, bool) and \
            self.isDumpClean() == 1 and isLast:
                msgBox = AdvancedMessageBox(self, 'Wavetables not dumped', 
                    '{} wavetables in the dump list have not been updated with your Blofeld yet.'.format(self.undumpedCount()), 
                    buttons=[
                        (QtWidgets.QMessageBox.Apply, 'Update'), 
                        (QtWidgets.QMessageBox.Ignore, 'Later', QtGui.QIcon.fromTheme('clock')), 
                        (QtWidgets.QMessageBox.Cancel, )], 
                    checkBox='Always close without asking', 
                    icon=AdvancedMessageBox.Question)
                res = msgBox.exec_()
                if res == QtWidgets.QMessageBox.Apply:
                    self.dumpUpdated()
                elif res != QtWidgets.QMessageBox.Ignore:
                    self.settings.endGroup()
                    return event.ignore()
                if msgBox.isChecked():
                    self.settings.setValue('WaveTableAskUndumpedOnClose', False)
        self.settings.endGroup()
        self.settings.setValue('defaultVolume', AudioImportTab.defaultVolume)
        self.isClosing = True
        if not self.currentWaveTable:
            self.setLastActive(False)

    def showEvent(self, event):
        if not self.shown:
            self.shown = True
            self.fullTableMiniView.setFixedHeight(self.fullTableMiniView.width() * .4)
#            self.fullTableMiniView.fitInView(self.fullTableMiniScene.sceneRect())
            self.setCurrentKeyFrame(self.keyFrames[0])
            self.updateMiniWave(self.keyFrames[0])

    def resizeEvent(self, event):
        QtWidgets.QMainWindow.resizeEvent(self, event)
        self.fullTableMiniView.setFixedHeight(self.fullTableMiniView.width() * .4)
#        self.fullTableMiniView.fitInView(self.fullTableMiniScene.sceneRect())
        rect = QtCore.QRectF(0, 0, SampleItem.wavePathMaxWidth, SampleItem.wavePathMaxHeight)
        self.fullTableMiniView.fitInView(rect)
        height = self.morphLabel.sizeHint().height() + self.nextTransformCombo.sizeHint().height() + self.nextTab.layout().verticalSpacing()
        self.nextView.setMaximumSize(height * 1.3, height)


from bigglesworth.wavetables.keyframes import VirtualKeyFrames
from bigglesworth.wavetables.widgets import CheckBoxDelegate, PianoStatusWidget
from bigglesworth.wavetables.graphics import WaveScene, SampleItem, WaveTransformItem, WaveTableScene, KeyFrameScene
from bigglesworth.wavetables.audioimport import AudioImportTab

WaveUndo.labels = {
    WaveScene.Randomize: 'Wave {} randomized', 
    WaveScene.Smoothen: 'Wave {} smoothened', 
    WaveScene.Quantize: 'Wave {} quantized', 
    WaveScene.HorizontalReverse: 'Wave {} reversed horizontally', 
    WaveScene.VerticalReverse: 'Wave {} reversed vertically', 
    }

GenericDrawUndo.labels = {
    WaveScene.LineDraw: 'Line draw on wave {}', 
    WaveScene.QuadCurveDraw: 'Simple curve draw on wave {}', 
    WaveScene.CubicCurveDraw: 'Simple curve draw on wave {}', 
    WaveScene.Shift: 'Wave {} shift', 
    WaveScene.Gain: 'Sample gain change on wave {}', 
    WaveScene.HLock: 'Samples vertically shifte on wave {}', 
    WaveScene.VLock: 'Samples horizontally shifte on wave {}', 
    WaveScene.Drag: 'Samples drag on wave {}', 
    WaveScene.Harmonics: 'Harmonics drawn on wave {}', 
    WaveScene.Paste: 'Samples pasted to wave {}', 
    WaveScene.Drop: 'Samples dropped to wave {}', 
    }

if __name__ == '__main__':

    from mididings import run, config, Filter, Call, NOTE as mdNOTE, NOTEOFF as mdNOTEOFF, NOTEON as mdNOTEON
    from mididings.engine import output_event as outputEvent
    from mididings.event import SysExEvent as mdSysExEvent

#    if 'linux' in sys.platform:
#        def addSection(self, text=''):
#            action = self.addSeparator()
#            action.setText(text)
#            return action
#
#        def insertSection(self, before, text=''):
#            action = self.insertSeparator(before)
#            action.setText(text)
#            return action
#    else:
#        from bigglesworth.compatibility import addSection, insertSection
#
#    QtWidgets.QMenu.addSection = addSection
#    QtWidgets.QMenu.insertSection = insertSection

    app = QtWidgets.QApplication(sys.argv)
    app.setOrganizationName('jidesk')
    app.setApplicationName('Bigglesworth')
    dataPath = QtGui.QDesktopServices.storageLocation(QtGui.QDesktopServices.DataLocation)
    db = QtSql.QSqlDatabase.addDatabase('QSQLITE')
    db.setDatabaseName(dataPath + '/library.sqlite')
    #print(db.databaseName())
    db.open()
    w = WaveTableWindow()
    w._db = db
    w.show()
    sys.exit(app.exec_())

