import json
from Qt import QtCore, QtGui, QtSql, QtWidgets

Init, Database, Dumped, Buffer, Edited = 0, 1, 2, 4, 64

MultiIndexRole, MultiNameRole, MultiDataRole, MultiMidiRole, MultiLabelDataRole = range(QtCore.Qt.UserRole + 1, QtCore.Qt.UserRole + 6)

EmptyFlags = QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDropEnabled

MultiNames = ', '.join('multi{:03}'.format(m) for m in range(128))

#a fake BlofeldDB for debugging purposes
class FakeBlofeldDB(QtCore.QObject):
    def getCollectionsFromUid(self, uid):
        return ['collection']

    def openCollection(self, collection=None):
        if collection is None:
            from bigglesworth.library import LibraryModel
            collection = LibraryModel(self)
        else:
            from bigglesworth.library import CollectionModel
            collection = CollectionModel(collection)
        return collection


class EmptyCollection(QtGui.QStandardItemModel):
    def __init__(self):
        QtGui.QStandardItemModel.__init__(self)
        for p in range(1024):
            self.appendRow([None, None, QtGui.QStandardItem('???')])


def makeQtProperty(name, propertyType=int):
    def getter(self):
        return getattr(self, name)
    def setter(self, value):
        if getattr(self, name) == value:
            return
        self.changed.emit()
        setattr(self, name, value)
    return QtCore.pyqtProperty(propertyType, getter, setter)


class PartObject(QtCore.QObject):
    changed = QtCore.pyqtSignal()

    def __init__(self, part=0):
        QtCore.QObject.__init__(self)
        self._part = part
        self._label = 'Part {}'.format(part + 1)
        self.labelColor = self.borderColor = None
        self._bank = self._prog = 0
        self._volume = 100
        self._pan = self._transpose = self._detune = 64
        self._channel = part + 2
        self._lowVel = self._lowKey = 0
        self._highVel = self._highKey = 127
        self._midi = self._usb = self._local = self._play = True
        self._pitch = self._mod = self._pressure = self._sustain = self._edits = self._progChange = True
        self.ctrlBit = 63
        self.unknonwnParameter = 0
        self.tailData = [1, 63, 0, 0, 0, 0, 0, 0, 0, 0]

    part = makeQtProperty('_part')
    label = makeQtProperty('_label', str)
    bank = makeQtProperty('_bank')
    prog = makeQtProperty('_prog')
    volume = makeQtProperty('_volume')
    pan = makeQtProperty('_pan')
    transpose = makeQtProperty('_transpose')
    detune = makeQtProperty('_detune')
    channel = makeQtProperty('_channel')
    lowVel = makeQtProperty('_lowVel')
    highVel = makeQtProperty('_highVel')
    lowKey = makeQtProperty('_lowKey')
    highKey = makeQtProperty('_highKey')
    midi = makeQtProperty('_midi')
    usb = makeQtProperty('_usb')
    local = makeQtProperty('_local')
    play = makeQtProperty('_play')
    pitch = makeQtProperty('_pitch')
    mod = makeQtProperty('_mod')
    pressure = makeQtProperty('_pressure')
    sustain = makeQtProperty('_sustain')
    edits = makeQtProperty('_edits')
    progChange = makeQtProperty('_progChange')

    @property
    def index(self):
        return (self.bank << 7) + self.prog

    @index.setter
    def index(self, index):
        self.bank = index >> 7
        self.prog = index & 127

    @property
    def velocityRange(self):
        return self.lowVel, self.highVel

    @velocityRange.setter
    def velocityRange(self, velRange):
        self.lowVel, self.highVel = velRange

    @property
    def keyRange(self):
        return self.lowKey, self.highKey

    @keyRange.setter
    def keyRange(self, keyRange):
        self.lowKey, self.highKey = keyRange

    @property
    def mute(self):
        return not self.play

    @mute.setter
    def mute(self, mute):
        self.play = not mute

    @property
    def receive(self):
        return (self.mute << 6) + (self.local << 2) + (self.usb << 1) + self.midi

    @receive.setter
    def receive(self, bitMask):
        self.mute = bool(bitMask & 64)
        self.local = bool(bitMask & 4)
        self.usb = bool(bitMask & 2)
        self.midi = bool(bitMask & 1)

    @property
    def ctrl(self):
        return (self.progChange << 5) + (self.edits << 4) + (self.sustain << 3) + (self.pressure << 2) + (self.mod << 1) + int(bool(self.pitch))

    @ctrl.setter
    def ctrl(self, bitMask):
        self.progChange = bool(bitMask & 32)
        self.edits = bool(bitMask & 16)
        self.sustain = bool(bitMask & 8)
        self.pressure = bool(bitMask & 4)
        self.mod = bool(bitMask & 2)
        self.pitch = bool(bitMask & 1)

    def getSerializedData(self):
        pass

    def setSerializedData(self, data):
        pass

    def getMidiData(self):
        return [self.bank, self.prog, self.volume, self.pan, self.unknonwnParameter, self.transpose, self.detune, self.channel, 
            self.lowKey, self.highKey, self.lowVel, self.highVel, self.receive, self.ctrl] + self.tailData

    def setMidiData(self, data):
        self.blockSignals(True)
        self.bank, self.prog, self.volume, self.pan, self.unknonwnParameter, self.transpose, self.detune, self.channel, \
            self.lowKey, self.highKey, self.lowVel, self.highVel, self.receive, self.ctrl = data[:14]
        self.tailData = data[14:]
        self.blockSignals(False)

    def getData(self):
        return [self.bank, self.prog, self.volume, self.pan, self.transpose, self.detune, self.channel, 
            self.lowKey, self.highKey, self.lowVel, self.highVel, 
            self.midi, self.usb, self.local, self.play, 
            self.pitch, self.mod, self.pressure, self.sustain, self.edits, self.progChange]

    def setData(self, data):
        pass

    def setLabelData(self, *data):
        self.label, self.labelColor, self.borderColor = data

    @classmethod
    def fromMidi(cls, part, data):
        obj = cls(part)
        obj.setMidiData(data)
        return obj


class MultiObject(QtCore.QObject):
    statusChanged = QtCore.pyqtSignal(int)

    def __init__(self, data=None, index=0):
        QtCore.QObject.__init__(self)
        self.unknonwnParameter = 0
        self.unknonwnData = [1, 0, 2, 4, 11, 12, 0, 0, 0, 0, 0, 0, 0]
        self._status = Init
        self.parts = []
        self.index = None
        if data is None:
            self.isNew = True
            self.setDefaultValues(index)
        else:
            self.isNew = False
            if isinstance(data, (list, tuple)) and len(data) == 418 and isinstance(data[0], int):
                self.setMidiData(data)
            else:
#                print('wtf?!', data)
                self.parseSerializedData(data)

    @property
    def name(self):
        return ''.join(map(chr, self._nameChars))

    @name.setter
    def name(self, name=''):
        self.setChanged()
        self._nameChars = map(ord, name.ljust(16)[:16])

    @property
    def volume(self):
        return self._volume

    @volume.setter
    def volume(self, volume):
        self._volume = volume
        self.setChanged()

    @property
    def tempo(self):
        return self._tempo

    @tempo.setter
    def tempo(self, tempo):
        self._tempo = tempo
        self.setChanged()

    @property
    def status(self):
        partStatus = 0
        return self._status | partStatus

    @status.setter
    def status(self, status):
        self._status = status
        self.statusChanged.emit(status)
        self.isNew = False

    def setChanged(self):
        self.status |= Edited

    def isClean(self):
        return not bool(self._status & Edited)

    def save(self):
        self.status = Database

    def setDefaultValues(self, index=0):
        if self.index is None:
            self.index = index
        self._nameChars = [73, 110, 105, 116, 32, 77, 117, 108, 116, 105, 32, 32, 32, 32, 32, 32]
        self._volume = 127
        self._tempo = 55
        if not self.parts:
            for part in range(16):
                partObject = PartObject(part)
                partObject.changed.connect(self.setChanged)
                self.parts.append(partObject)

    def setMidiData(self, data):
        #we assume that indexes received *after* object creation can be ignored,
        #expecially if from edit buffer.
        if self.index is None:
            self.index = data[1]
        self._nameChars = [c if 32 <= c <= 127 else 32 for c in data[2:18]]
        self.unknonwnParameter, self._volume, self._tempo = data[18:21]
        self.unknonwnData = data[21:34]
        partData = data[34:]
        if not self.parts:
            for part in range(16):
                partObject = PartObject.fromMidi(part, partData[part * 24: (part + 1) * 24])
                partObject.changed.connect(self.setChanged)
                self.parts.append(partObject)
        else:
            for part in self.parts:
                part.blockSignals(True)
                part.setMidiData(partData[part.part * 24: (part.part + 1) * 24])
                part.blockSignals(False)
        self.status = Buffer if data[0] else Dumped

    def getMidiData(self, buffer=None):
        if buffer:
            index = [127, 0]
        else:
            index = [0, self.index]
#        index = 0 if self.buffer or buffer is not None else self.index
        data = index + self._nameChars + \
            [self.unknonwnParameter, self.volume, self.tempo] + self.unknonwnData
        for part in self.parts:
            data.extend(part.getMidiData())
        return data

    def parseSerializedData(self, data, fromDatabase=True, emitChanged=False):
        self.blockSignals(True)
        midiData = data.get('midiData')
        if midiData:
            self.setMidiData(midiData)
        else:
            self.setDefaultValues()
        labelData = data.get('labelData')
        if labelData:
            for part, labelDict in zip(self.parts, labelData):
                part.blockSignals(True)
                part.label = labelDict.get('label', part._label)
                if labelDict.get('labelColor'):
                    part.labelColor = QtGui.QColor(*labelDict['labelColor'])
                else:
                    part.labelColor = None
                if labelDict.get('borderColor'):
                    part.borderColor = QtGui.QColor(*labelDict['borderColor'])
                else:
                    part.borderColor = None
                part.blockSignals(False)
        self.blockSignals(False)
        status = Database
        if not fromDatabase:
            status |= Edited
        self._status = status
        if emitChanged:
            self.statusChanged.emit(status)

    def getSerializedData(self):
        labelData = []
        for part in self.parts:
            labelDict = {}
            if part._label.lower() != 'part {}'.format(part.part + 1):
                labelDict['label'] = part._label
            if part.labelColor:
                labelDict['labelColor'] = part.labelColor.getRgb()[:3]
            if part.borderColor:
                labelDict['borderColor'] = part.borderColor.getRgb()[:3]
            labelData.append(labelDict)
        return {'labelData': labelData, 'midiData': self.getMidiData(), 'name': self.name}


class MultiSetObject(QtCore.QObject):
    previousIndex = 0
    collection = None

    def __init__(self):
        QtCore.QObject.__init__(self)
        self.multis = {m: None for m in range(128)}

    def isClean(self):
        for multi in self.multis.values():
            if multi is not None and multi._status & Edited:
                return False
        return True

    def count(self):
        return len(tuple(multi for multi in self.multis.values() if multi is not None))

    def existingIndexes(self):
        return sorted(i for i in range(128) if self.multis[i])

    def exists(self, index):
        return bool(self.multis[index])

    def saveAll(self):
        pass

    def saveIndex(self, index):
        pass

    def saveIndexAs(self, source, target):
        data = self.multis[source].getSerializedData()
        data['midiData'][:2] = [0, target]
        multi = MultiObject(data)
        self.multis[target] = multi
        multi._status = Init

    def __getitem__(self, index):
        multi = self.multis[index]
        if not multi:
            multi = MultiObject(index=index)
            self.multis[index] = multi
        return multi


class MultiSetObjectFromDB(MultiSetObject):
    def __init__(self, collection):
        MultiSetObject.__init__(self)
        self.collection = collection

        db = QtSql.QSqlDatabase.database()
        self.updateQuery = QtSql.QSqlQuery()
        if not 'multi' in db.tables():
            createNames = ', '.join('multi{:03} blob'.format(m) for m in range(128))
            if not self.updateQuery.exec_('CREATE TABLE multi (collection varchar, {})'.format(createNames)):
                print(self.updateQuery.lastError().driverText(), self.updateQuery.lastError().databaseText())
            if not self.updateQuery.exec_('INSERT INTO multi (collection) VALUES("Blofeld")'):
                print(self.updateQuery.lastError().driverText(), self.updateQuery.lastError().databaseText())
        self.loadData()

    def loadData(self):
        self.updateQuery.exec_('SELECT {} FROM multi WHERE collection="{}"'.format(MultiNames, self.collection))
        if not self.updateQuery.last():
            if not self.updateQuery.exec_('INSERT INTO multi (collection) VALUES("{}")'.format(self.collection)):
                print(self.updateQuery.lastError().driverText(), self.updateQuery.lastError().databaseText())
        else:
            self.updateQuery.first()
            for index in range(128):
                data = self.updateQuery.value(index)
                if data:
                    self.multis[index] = MultiObject(json.loads(data))
        self.updateQuery.finish()

    def saveAll(self):
        for index in range(128):
            multi = self.multis[index]
            if multi is not None:
                self.updateQuery.prepare('UPDATE multi SET multi{:03}=:data WHERE collection="{}"'.format(
                    index, self.collection))
                self.updateQuery.bindValue(':data', multi.getSerializedData())
                if not self.updateQuery.exec_():
                    print(self.updateQuery.lastError().driverText(), self.updateQuery.lastError().databaseText())
                multi._status = Database

    def saveIndex(self, index):
        #since we use the index, we should assume that the multi already exists, right?
        self.updateQuery.prepare('UPDATE multi SET multi{:03}=:data WHERE collection="{}"'.format(
            index, self.collection))
        self.updateQuery.bindValue(':data', json.dumps(self.multis[index].getSerializedData()))
        if not self.updateQuery.exec_():
            print(self.updateQuery.lastError().driverText(), self.updateQuery.lastError().databaseText())
        self.multis[index]._status = Database

    def saveIndexAs(self, source, target):
        self.updateQuery.prepare('UPDATE multi SET multi{:03}=:data WHERE collection="{}"'.format(
            target, self.collection))
        data = self.multis[source].getSerializedData()
        data['midiData'][:2] = [0, target]
        self.updateQuery.bindValue(':data', json.dumps(data))
        if not self.updateQuery.exec_():
            print(self.updateQuery.lastError().driverText(), self.updateQuery.lastError().databaseText())
        self.multis[target] = multi = MultiObject(data)
        multi._status = Database

    def saveDataToIndex(self, data, target):
        self.updateQuery.prepare('UPDATE multi SET multi{:03}=:data WHERE collection="{}"'.format(
            target, self.collection))
        data['midiData'][:2] = [0, target]
        self.updateQuery.bindValue(':data', json.dumps(data))
        if not self.updateQuery.exec_():
            print(self.updateQuery.lastError().driverText(), self.updateQuery.lastError().databaseText())
        self.multis[target] = multi = MultiObject(data)
        multi._status = Database


class MultiSetModel(QtCore.QIdentityProxyModel):
    def __init__(self, source):
        QtCore.QIdentityProxyModel.__init__(self)
        self.setSourceModel(source)
        self.setSupportedDragActions(QtCore.Qt.CopyAction|QtCore.Qt.MoveAction|QtCore.Qt.LinkAction)

    def setCollection(self, collection):
        self.sourceModel().setCollection(collection)

    def indexFromMultiIndex(self, multiIndex):
        return QtCore.QIdentityProxyModel.index(self, 0, multiIndex)

    def indexListFromMultiIndexes(self, indexes):
        indexList = []
        for index in indexes:
            indexList.append(QtCore.QIdentityProxyModel.index(self, 0, index))
        return indexList

    def clearMultis(self, indexes):
        self.sourceModel().clearMultis([self.mapToSource(index) for index in indexes])

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole:
            return '{:03}  {}'.format(index.data(MultiIndexRole) + 1, index.data(MultiNameRole))
        if role == QtCore.Qt.ForegroundRole:
            if not isinstance(self.mapToSource(index).data(), (str, unicode)):
                return QtWidgets.QApplication.palette().color(QtGui.QPalette.Disabled, QtGui.QPalette.Text)
        if role == MultiIndexRole:
            return self.mapToSource(index).column()
        return QtCore.QIdentityProxyModel.data(self, index, role)

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        return QtCore.QIdentityProxyModel.setData(self, index, value, role)

    def mapFromSource(self, index):
        if index.isValid():
            col, row = divmod(index.column(), 32)
            return self.createIndex(row, col)
        return QtCore.QIdentityProxyModel.mapFromSource(self, index)

    def mapToSource(self, index):
        if index.isValid():
            row = index.row() + index.column() * 32
            return self.sourceModel().index(0, row)
        return QtCore.QIdentityProxyModel.mapToSource(self, index)

    def index(self, row, column, parent=None):
        if column > 0:
            row += column * 32
        return QtCore.QIdentityProxyModel.index(self, 0, row, parent)

    def flags(self, index):
        if not isinstance(self.mapToSource(index).data(MultiNameRole), (str, unicode)):
            return EmptyFlags
        return QtCore.QIdentityProxyModel.flags(self, index)

    def rowCount(self, parent=None):
        return 32 if self.sourceModel().rowCount() else 0

    def columnCount(self, parent=None):
        return 4 if self.sourceModel().rowCount() else 0


class MultiQueryModel(QtSql.QSqlQueryModel):
    def __init__(self):
        QtSql.QSqlQueryModel.__init__(self)
        db = QtSql.QSqlDatabase.database()
        self.updateQuery = QtSql.QSqlQuery()
        if not 'multi' in db.tables():
            createNames = ', '.join('multi{:03} blob'.format(m) for m in range(128))
            if not self.updateQuery.exec_('CREATE TABLE multi (collection varchar, {})'.format(createNames)):
                print(self.updateQuery.lastError().driverText(), self.updateQuery.lastError().databaseText())
            if not self.updateQuery.exec_('INSERT INTO multi (collection) VALUES("Blofeld")'):
                print(self.updateQuery.lastError().driverText(), self.updateQuery.lastError().databaseText())
        self.currentCollection = None
        self.setCollection('Blofeld')

    def setCollection(self, collection=None):
        if collection is None:
            collection = self.currentCollection
        self.setQuery('SELECT {} FROM multi WHERE collection="{}"'.format(MultiNames, collection))
        if not self.rowCount():
            if not self.updateQuery.exec_('INSERT INTO multi (collection) VALUES("{}")'.format(collection)):
                print(self.updateQuery.lastError().driverText(), self.updateQuery.lastError().databaseText())
            else:
                self.setCollection(collection)
        else:
            self.layoutChanged.emit()
            self.currentCollection = collection

    def clearMultis(self, indexes):
        for index in indexes:
            if not self.updateQuery.exec_('UPDATE multi SET multi{:03}=NULL WHERE collection="{}"'.format(
                index.column(), self.currentCollection)):
                    print(self.updateQuery.lastError().driverText(), self.updateQuery.lastError().databaseText())
                    return False
        self.setCollection()
        return True

    def existingIndexes(self):
        if not self.updateQuery.exec_('SELECT {} FROM multi WHERE collection="{}"'.format(
            MultiNames, self.currentCollection)):
                print(self.updateQuery.lastError().driverText(), self.updateQuery.lastError().databaseText())
        self.updateQuery.next()
        indexes = []
        for v in range(128):
            if self.updateQuery.value(v):
                indexes.append(v)
        return indexes

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if role == MultiNameRole:
            try:
                return json.loads(index.data()).get('name')
            except:
                return 'Empty slot'
        elif role == MultiMidiRole:
            try:
                return json.loads(index.data()).get('midiData')
            except:
                return []
        elif role == MultiLabelDataRole:
            try:
                return json.loads(index.data()).get('labelData')
            except:
                return []
        elif role == MultiDataRole:
            try:
                return json.loads(index.data())
            except:
                pass
        return QtSql.QSqlQueryModel.data(self, index, role)

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        #this seems necessary when updating or creating new items in empty slots
        #update would work anyway, but Qt complains about invalid indexes
        #(it still complains anyway, sometimes...)
        self.beginResetModel()
        self.updateQuery.prepare('UPDATE multi SET multi{:03}=:data WHERE collection="{}"'.format(index.column(), self.currentCollection))
        if value is None and role == MultiDataRole:
            data = None
        else:
            #TODO: Preleva i valori preesistenti?!
            data = {}
            if role == MultiNameRole:
                data['name'] = value[:16]
            elif role == MultiLabelDataRole:
                data['labelData'] = value
            elif role == MultiMidiRole:
                data['midiData'] = value
            elif role == MultiDataRole:
                if value and not isinstance(value, dict):
                    value = json.dumps(value)
                    assert isinstance(value, dict), 'Format error while setting data: {}'.format(value)
                data.update(value)
            data = json.dumps(data)
        self.updateQuery.bindValue(':data', data)
        if not self.updateQuery.exec_():
            print(self.updateQuery.lastError().driverText(), self.updateQuery.lastError().databaseText())
            self.endResetModel()
            return False
        else:
            self.endResetModel()
            QtCore.QTimer.singleShot(0, self.setCollection)
#            self.setCollection(self.currentCollection)
            return True

    def flags(self, index):
        if not isinstance(QtSql.QSqlQueryModel.data(self, index), (str, unicode)):
            return EmptyFlags
        return QtSql.QSqlQueryModel.flags(self, index) | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsDropEnabled


