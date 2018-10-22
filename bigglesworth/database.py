# *-* encoding: utf-8 *-*

import sys
import string
import uuid
import json
import re
from xml.etree import ElementTree as ET
#from threading import Lock

from Qt import QtCore, QtGui, QtSql
QtCore.pyqtSignal = QtCore.Signal

from bigglesworth.utils import Enum, localPath, getName, getSizeStr, elapsedFrom, getValidQColor
from bigglesworth.parameters import Parameters, oscShapes, categories
from bigglesworth.libs import midifile
from bigglesworth.const import (factoryPresets, NameColumn, chr2ord, backgroundRole, foregroundRole, 
    LogInfo, LogWarning, LogCritical, LogFatal, LogDebug)
from bigglesworth.library import CollectionModel, LibraryModel
from bigglesworth.backup import BackUp

renameRegExp = re.compile(r'^(?=.{16}$)(?P<name>.*)~(?P<count>[1-9][0-9]{0,2}){0,1} *$')
parameterList = Parameters.parameterList
validParameterList = Parameters.validParameterList
indexedValidParameterList = Parameters.indexedValidParameterList
soundsColumns = []
soundsDef = '('
for p in Parameters.parameterData:
#    parameterList.append(p.attr)
#    if not p.attr.startswith('reserved'):
#        validParameterList.append(validParameterList)
    soundsColumns.append(p.attr)
    soundsDef += '{} int, '.format(p.attr)

templateDef = soundsDef + 'name varchar, groups varchar)'
soundsColumns.append('uid')
soundsDef += 'uid varchar primary key)'
referenceColumns = ['uid', 'tags', 'blofeld_fact_200801', 'blofeld_fact_200802', 'blofeld_fact_201200', 'Blofeld']
referenceDef = '(uid varchar primary key, tags varchar, blofeld_fact_200801 int, blofeld_fact_200802 int, blofeld_fact_201200 int, Blofeld int)'


def splitter(uidList, limit=500):
    splitList = uidList[:limit]
    delta = 0
    while splitList:
        yield splitList
        delta += 1
        splitList = uidList[limit * delta: limit * (delta + 1)]


class BlofeldDB(QtCore.QObject):

    ReadError, WriteError, InvalidError, DatabaseFormatError, TableFormatError, QueryError = Enum(6)
    SoundsEmpty, ReferenceEmpty, WaveTablesEmpty = Enum(32, 64, 128)
    EmptyMask = 224

    soundNameChanged = QtCore.pyqtSignal(str, str)

    backupStarted = QtCore.pyqtSignal()
    backupStatusChanged = QtCore.pyqtSignal(int)
    backupFinished = QtCore.pyqtSignal()
    backupError = QtCore.pyqtSignal(str)
    factoryStatus = QtCore.pyqtSignal(str, int)
    wavetableStatus = QtCore.pyqtSignal(str, int)

    def __init__(self, main):
        QtCore.QObject.__init__(self)
#        self.sql = QtSql.QSqlDatabase.addDatabase('QSQLITE')
        self.main = main
        self.logger = main.logger
        self.logger.append(LogInfo, 'Starting database engine')
        self.sql = QtSql.QSqlDatabase.addDatabase('QSQLITE')
#        self.lock = Lock()
        self.lastError = None
        self.collections = {}
        self.backup = BackUp(self)
        self.backupThread = QtCore.QThread()
        self.backup.moveToThread(self.backupThread)
        self.backupThread.started.connect(self.backup.run)
        self.backup.backupStarted.connect(self.backupStarted)
        self.backup.backupStatusChanged.connect(self.backupStatusChanged)
        self.backup.backupFinished.connect(self.backupFinished)
        self.backup.backupError.connect(self.backupError)
        self.backupTimer = QtCore.QTimer()
        backupInterval = self.main.settings.value('backupInterval', 5, int) * 60000
        if backupInterval:
            backupInterval = min(backupInterval, 300000)
        self.backupTimer.setInterval(backupInterval)
#        self.backupTimer.setSingleShot(True)
        #for some reason, connecting directly to the queueBackup doesn't seem to work...
        self.backupTimer.timeout.connect(lambda: self.backup.queueBackup())

        self.statusTimer = QtCore.QTimer()
        self.statusTimer.setInterval(2000)
        self.statusTimer.setSingleShot(True)
        self.statusTimer.timeout.connect(self.resetStatusText)
        self.statusText = None

    def setBackupInterval(self, interval):
        #interval is in minutes!
        interval = interval * 60000
        if interval:
            self.backupTimer.setInterval(min(interval, 300000))
            self.backupTimer.start()
        else:
            self.backupTimer.stop()
            self.backupTimer.setInterval(0)

    def resetStatusText(self):
        self.statusText = None

    def getStatusText(self):
        if not self.statusText:
            query = QtSql.QSqlQuery('SELECT COUNT(uid) FROM reference')
            query.next()
            totSounds = query.value(0)
            query.exec_('PRAGMA table_info(reference)')
            query.seek(5)
            colCount = 0
            while query.next():
                colCount += 1
            query.finish()
            del query
            size = getSizeStr(QtCore.QFileInfo(self.path).size())
            backupFile = QtCore.QFileInfo(self.path + '.bkp')
            if backupFile.exists():
                backupInfo = 'last saved {} ago'.format(elapsedFrom(backupFile.lastModified()))
                if self.backupTimer.isActive():
                    elapsed = backupFile.lastModified().msecsTo(QtCore.QDateTime.currentDateTime())
                    if elapsed > self.backupTimer.interval():
                        elapsed = self.main.startTimer.elapsed()
                    next = int((self.backupTimer.interval() - elapsed) / 60000)
                    backupInfo += '<br/>&nbsp;&nbsp;Next backup in {} minute{}'.format(
                        next if next > 1 else 'less than a', 's' if next > 1 else '')
            else:
                if not self.backup.success:
                    backupInfo = 'Error creating backup!'
                else:
                    backupInfo = '(no backup file)'
            self.statusText = '''
                Total sounds: {totSounds}<br/>
                Collections: {colCount}<br/><br/>
                Database size: {size}<br/>
                Backup: {backupInfo}
                '''.format(
                    totSounds=totSounds, 
                    colCount=colCount, 
                    size=size, 
                    backupInfo=backupInfo
                    )
            self.statusTimer.start()
        return self.statusText

    def reconnect(self):
        self.sql.close()
        self.sql.open()
        self.referenceModel.refresh()

    @property
    def libraryModel(self):
        try:
            return self._libraryModel
        except:
            self._libraryModel = self.openCollection()
            return self._libraryModel

    def dbErrorLog(self, message, logLevel=LogCritical, extMessage='', query=None):
        print('Db error:', message)
        if not query:
            query = self.query
        dbText = query.lastError().databaseText()
        driverText = query.lastError().driverText()
        print(dbText)
        print(driverText)
        text = '{}\n{}'.format(dbText, driverText)
        if extMessage:
            text = '{}\n{}'.format(extMessage, text)
        self.logger.append(logLevel, message, text)

    def initialize(self, path=None):
        if path:
            fileInfo = QtCore.QFileInfo(path)
            if not (fileInfo.isFile() and fileInfo.isWritable()):
                self.logger.append(LogWarning, 'Database path invalid, reverting to default', path)
                path = None
        if path is not None:
            self.path = path
        else:
            self.path = self.main.settings.value('dbPath', 
                QtCore.QDir(QtGui.QDesktopServices.storageLocation(QtGui.QDesktopServices.DataLocation)).filePath(
                    'library.sqlite'), 'QString')
        self.logger.append(LogInfo, 'Loading database', self.path)
        self.backup.setPath(self.path)
        if not QtCore.QFile.exists(self.path):
            self.logger.append(LogDebug, 'Database does not exists, trying to create')
            fileInfo = QtCore.QFileInfo(self.path)
#            if not QtCore.QFile.exists(fileInfo.absolutePath()) and not QtCore.QDir().mkdir(fileInfo.absolutePath()):
            if not QtCore.QFile.exists(fileInfo.absolutePath()) and not QtCore.QDir().mkpath(fileInfo.absolutePath()):
                self.logger.append(LogFatal, 'Write error!!!', 'Cannot create db directory')
                self.lastError = self.WriteError
                return False
        elif not QtCore.QFileInfo(self.path).isWritable():
            self.logger.append(LogCritical, 'Read only database')
            self.lastError = self.WriteError
            return False

        self.sql.setDatabaseName(self.path)
        if self.sql.open():
            self.logger.append(LogDebug, 'Database successfully opened')
        else:
            self.logger.append(LogFatal, 'Cannot open database!')
        self.sql.exec_('PRAGMA synchronous="NORMAL"')
        self.query = QtSql.QSqlQuery(self.sql)

        valid = self.query.exec_('PRAGMA quick_check')
        if not valid:
            self.lastError = self.InvalidError
            return False
        valid = self.checkTables()

        #if valid?
        self.tagsModel = QtSql.QSqlTableModel()
        self.tagsModel.setEditStrategy(self.tagsModel.OnManualSubmit)
        self.tagsModel.setTable('tags')
        self.tagsModel.select()
        self.referenceModel = CollectionManagerModel()
#        self.query.exec_('PRAGMA foreign_keys=ON')
        self.backupThread.start()
        if self.backupTimer.interval() != 0:
            self.backupTimer.start()
        return valid

    def checkTables(self, deepCheck=False):
        self.logger.append(LogInfo, 'Checking tables')
        self.query.exec_('DROP TABLE IF EXISTS _oldreference')
#        self.query.exec_('SELECT name FROM sqlite_master WHERE type="table"')
        tables = set(self.sql.tables())
        defaultSet = set(('sounds', 'reference', 'ascii', 'tags', 'fake_reference', 'templates', 'wavetables', 'dumpedwt'))
        if tables and (tables | defaultSet) ^ defaultSet:
            self.logger.append(LogCritical, 'Database table mismatch', 'Missing tables or unknown tables found')
            self.lastError = self.DatabaseFormatError
            if not deepCheck:
                return False

        self.logger.append(LogDebug, 'Checking sounds table')
        createBit = 0
        if not 'sounds' in tables:
            self.logger.append(LogDebug, 'Creating sounds table')
            self.query.exec_('CREATE TABLE sounds ' + soundsDef)
            createBit |= self.SoundsEmpty
        else:
            self.query.exec_('PRAGMA table_info(sounds)')
            columns = []
            while self.query.next():
                columns.append(self.query.value(1))
            if columns != soundsColumns:
                self.logger.append(LogCritical, 'Sounds table column mismatch')
                self.lastError = self.TableFormatError
                return False

        self.logger.append(LogDebug, 'Checking reference table')
        if not 'reference' in tables:
            self.logger.append(LogDebug, 'Preparing creation of reference table')
            self.query.exec_('CREATE TABLE reference ' + referenceDef)
            createBit |= self.ReferenceEmpty
        else:
            self.query.exec_('PRAGMA table_info(reference)')
            columns = []
            while self.query.next():
                columns.append(self.query.value(1))
            newColumns = columns[len(referenceColumns):]
            baseColumns = columns[:len(referenceColumns)]
            if baseColumns != referenceColumns:
                self.logger.append(LogCritical, 'Reference table column mismatch, deep checking', extMessage=columns)
#                self.query.exec_('SAVEPOINT refRename')
                try:
                    self.sql.transaction()
                    assert self.query.exec_('ALTER TABLE reference RENAME TO reference_old'), 1
                    self.sql.commit()
                    newLayout = ', '.join('"{}"'.format(c) for c in referenceColumns + newColumns)
                    newLayoutDef = 'uid varchar primary key, tags varchar, {}'.format(
                        ', '.join('"{}" int'.format(col) for col in referenceColumns[2:] + newColumns[:]))
                    self.sql.transaction()
                    assert self.query.exec_('CREATE TABLE reference({})'.format(newLayoutDef)), 2
                    self.sql.commit()
                    reordered = referenceColumns[:]
                    if 'blofeld' in baseColumns:
                        reordered.pop(reordered.index('Blofeld'))
                        reordered.insert(referenceColumns.index('Blofeld'), 'blofeld')
                    self.sql.transaction()
                    assert self.query.exec_('INSERT INTO reference({}) SELECT {} FROM reference_old'.format(
                        newLayout, ', '.join(reordered + newColumns))), 3
                    self.sql.commit()
                except Exception as e:
                    self.sql.rollback()
#                    print(self.query.lastError().databaseText(), self.query.lastError().driverText())
                    if e == 1:
                        extMessage = 'Source not renamed'
                    elif e >= 2:
                        if e == 3:
                            self.query.exec_('DROP TABLE reference')
                            extMessage = 'Data not inserted'
                        else:
                            extMessage = 'New table not created'
                        self.query.exec_('ALTER TABLE reference_old RENAME TO reference')
                    self.logger.append(LogCritical, 'Failed to reorder reference table', extMessage)
#                    self.query.exec_('ROLLBACK TO refRename')
                    self.lastError = self.TableFormatError
                    return False
#                self.query.exec_('COMMIT')
                self.sql.transaction()
                if not self.query.exec_('DROP TABLE reference_old'):
                    self.logger.append(LogWarning, 'Old reference not removed')
                self.sql.commit()
                self.logger.append(LogDebug, 'Reference table successfully reordered')

            self.logger.append(LogDebug, 'Checking collection consistency')
            self.query.exec_('PRAGMA table_info(reference)')
            collections = []
            while self.query.next():
                collections.append(self.query.value(1))
            valid = True
            duplicatePrepareStr = 'SELECT uid FROM sounds WHERE {} AND :collection IS NOT NULL'.format(
                ' AND '.join('{0}=:{0}'.format(param) for param in validParameterList))
            for collection in collections[2:]:
                self.query.exec_('SELECT uid,"{0}" FROM reference WHERE "{0}" IS NOT NULL'.format(collection))
                items = []
                while self.query.next():
                    items.append((self.query.value(0), self.query.value(1)))
                count = len(items)
                if count > 1024:
                    self.sql.transaction()
                    self.dbErrorLog('Collection "{}" too big, trimming down to 1024'.format(collection), 
                        extMessage='{} sounds'.format(count), logLevel=LogWarning)
                    for splitted in splitter([uid for uid, index in items[1024:]], 500):
                        where = ' OR '.join('uid="{}"'.format(uid) for uid in splitted)
                        if not self.query.exec_('UPDATE reference SET "{}"=NULL WHERE {}'.format(collection, where)):
                            self.dbErrorLog('Error trimming too big collection', extMessage=collection)
                            valid = False
                            self.sql.rollback()
                            break
                        for uid in splitted:
                            values = self.getSoundDataFromUid(uid, onlyValid=True)
                            self.query.prepare(duplicatePrepareStr)
                            self.query.bindValue(':collection', collection)
                            for param, value in zip(validParameterList, values):
                                self.query.bindValue(':{}'.format(param), value)
                            if not self.query.exec_():
                                self.dbErrorLog('Error checking duplicates for trimming')
                                valid = False
                                self.sql.rollback()
                                break
                            if self.query.next() and self.query.value(0):
                                #remove duplicate sounds (probably added in previous bugged versions)
                                if not self.query.exec_('DELETE FROM reference WHERE uid="{}"'.format(uid)):
                                    self.dbErrorLog('Error removing duplicate from reference for trimming', extMessage=uid)
                                    self.sql.rollback()
                                    break
                                if not self.query.exec_('DELETE FROM sounds WHERE uid="{}"'.format(uid)):
                                    self.dbErrorLog('Error removing duplicate from sounds for trimming', extMessage=uid)
                                    self.sql.rollback()
                                    break
                    else:
                        self.sql.commit()
                        self.logger.append(LogDebug, 'Collection "{}" successfully resized'.format(collection))
                elif len(set(items)) != count:
                    self.dbErrorLog('Duplicate indexes found in "{}", purging'.format(collection), logLevel=LogWarning)
                    indexes = set()
                    duplicates = []
                    for uid, index in items:
                        if index not in indexes:
                            indexes.add(index)
                        else:
                            duplicates.append(uid)
                    for splitted in splitter(duplicates):
                        where = ' OR '.join('uid="{}"'.format(uid) for uid in splitted)
                        if not self.query.exec_('UPDATE reference SET "{}"=NULL WHERE {}'.format(collection, where)):
                            self.dbErrorLog('Error trimming too big collection', extMessage=collection)
                            valid = False
                            break
                    else:
                        self.logger.append(LogDebug, 'Collection "{}" successfully fixed'.format(collection))
                else:
                    self.logger.append(LogDebug, 'Collection "{}" checked with {}errors'.format(collection, ('', 'no ')[valid]), 
                        extMessage='{} sound{}'.format(count, '' if count == 1 else 's'))

        self.logger.append(LogDebug, 'Checking templates table')
#        self.query.exec_('PRAGMA table_info(templates)')
        if not 'templates' in tables:
            self.logger.append(LogDebug, 'Preparing creation of templates table')
            self.query.exec_('CREATE TABLE templates ' + templateDef)

        self.logger.append(LogDebug, 'Checking ascii conversion table')
        self.query.exec_('PRAGMA table_info(ascii)')
        if not self.query.next() or not all((self.query.exec_('SELECT Count(rowid) from ascii'), self.query.first(), self.query.value(0))):
            self.logger.append(LogDebug, 'Creating ascii conversion table')
            self.query.exec_('CREATE TABLE ascii (id int primary key, char varchar(1))')
            self.query.exec_('PRAGMA journal_mode=OFF')
            prepareStr = 'INSERT INTO ascii(id, char) VALUES(:id, :char)'
            for l in range(32):
                self.query.prepare(prepareStr)
                self.query.bindValue(':id', l)
                self.query.bindValue(':char', ' ')
                self.query.exec_()
            for l in range(32, 127):
                self.query.prepare(prepareStr)
                self.query.bindValue(':id', l)
                self.query.bindValue(':char', unichr(l))
                self.query.exec_()
            self.query.exec_(u'INSERT INTO ascii(id, char) VALUES(127, "°")')
            self.query.exec_('PRAGMA journal_mode=DELETE')

        self.logger.append(LogDebug, 'Checking tags table')
#        self.query.exec_('PRAGMA table_info(tags)')
        if not 'tags' in tables:
            self.logger.append(LogDebug, 'Creating tags table')
            self.query.exec_('CREATE TABLE tags (tag varchar primary key, bgColor int, fgColor int)')
        #TODO: manca check tags.

        self.logger.append(LogDebug, 'Checking empty-reference table')
        self.query.exec_('PRAGMA table_info(fake_reference)')
        if not self.query.next():
            self.logger.append(LogDebug, 'Creating empty-reference table')
            self.query.exec_('CREATE TABLE fake_reference (id int primary key)')
            if 'linux' in sys.platform:
                fake = 'INSERT INTO fake_reference (id) VALUES'
                for f in range(1024):
                    fake += '({}),'.format(f)
                if not self.query.exec_(fake[:-1] + ';'):
                    self.dbErrorLog('unknown error for fake_reference')
            else:
                self.sql.transaction()
                for f in range(1024):
                    if not self.query.exec_('INSERT INTO fake_reference (id) VALUES ({})'.format(f)):
                        self.dbErrorLog('unknown error for fake_reference')
                        self.sql.rollback()
                        break
                else:
                    self.sql.commit()

        self.logger.append(LogDebug, 'Checking local wavetables table')
        if not 'wavetables' in tables:
            self.logger.append(LogDebug, 'Creating local wavetables table')
            self.query.exec_('CREATE TABLE wavetables(uid varchar primary key, name varchar(14), slot int, edited int, data blob, preview blob)')
        else:
            self.query.exec_('PRAGMA table_info(wavetables)')

        self.logger.append(LogDebug, 'Checking dumped wavetables table')
        if not 'dumpedwt' in tables:
            self.logger.append(LogDebug, 'Preparing creation of dumped wavetables table')
            self.query.exec_('CREATE TABLE dumpedwt(uid varchar, name varchar(14), slot int primary key, edited int, data blob, preview blob, dumped int, writable int)')
            createBit |= self.WaveTablesEmpty
        else:
            self.logger.append(LogDebug, 'Updating dumped wavetable columns')
            self.query.exec_('PRAGMA table_info(dumpedwt)')
            columns = []
            while self.query.next():
                columns.append(self.query.value(1))
            if not 'writable' in columns:
                if not self.query.exec_('ALTER TABLE dumpedwt ADD COLUMN "writable" int'):
                    self.dbErrorLog('Error updating dumped wavetable columns')
                elif not self.query.exec_('UPDATE dumpedwt SET writable=1 WHERE slot BETWEEN 80 AND 118'):
                    self.dbErrorLog('Error updating dumped wavetable writable column')

            self.query.exec_('SELECT slot, data, preview FROM dumpedwt WHERE (data IS NULL OR preview IS NULL) AND slot != 0 and slot < 67')
            toCheck = []
            while self.query.next():
                toCheck.append((self.query.value(0), self.query.value(1),  self.query.value(2)))
            if toCheck:
                self.updateWavetablePresets(toCheck)

        if createBit:
            self.logger.append(LogWarning, 'Reference and sound tables empty', 'createBit: {}'.format(createBit))
            self.lastError = createBit
            return False
        else:
            self.query.exec_('SELECT Count(rowid) FROM sounds')
            self.query.first()
            if self.query.value(0) < 1:
                createBit |= self.SoundsEmpty

            self.query.exec_('SELECT Count(rowid) FROM reference')
            self.query.first()
            if self.query.value(0) < 1:
                createBit |= self.ReferenceEmpty

            self.query.exec_('SELECT Count(rowid) FROM dumpedwt')
            self.query.first()
            if self.query.value(0) < 1:
                createBit |= self.WaveTablesEmpty

            if createBit:
                self.logger.append(LogCritical, 'Unknown error creating reference', 'createBit: {}'.format(createBit))
                self.lastError = createBit
                return False

        self.logger.append(LogInfo, 'Reference/sounds completed successfully!')
        return True


    def initializeFactory(self, createBit):
        self.logger.append(LogInfo, 'Filling factory presets')
        soundCreate = createBit & self.SoundsEmpty
        refCreate = createBit & self.ReferenceEmpty

        if soundCreate and not refCreate:
            raise BaseException('Database reference mismatch!!!')

        if refCreate:
            self.query.exec_('PRAGMA journal_mode=OFF')
            soundsPre = 'INSERT INTO sounds('
            soundsPost = 'VALUES('
            for p in soundsColumns[:-1]:
                soundsPre += p + ', '
                soundsPost += ':{}, '.format(p)
            soundsPrepare = soundsPre + 'uid) ' + soundsPost + ':uid)'
            for preset in factoryPresets:
                self.logger.append(LogDebug, 'Preparing preset {}'.format(preset))
                print('preparing preset "{}"'.format(preset))
                _pattern = midifile.read_midifile(localPath('presets/{}.mid'.format(preset)))
                _track = _pattern[0]
                for i, event in enumerate(_track):
                    if isinstance(event, midifile.SysexEvent):
                        self.query.prepare(soundsPrepare)
                        data = event.data[6:391]
                        for p, d in zip(Parameters.parameterData, data[2:]):
                            self.query.bindValue(':' + p.attr, p.range.sanitize(d))
                        uid = str(uuid.uuid4())
                        self.query.bindValue(':uid', uid)
                        if not self.query.exec_():
                            self.dbErrorLog('Sound cannot be added.', extMessage='break at {}'.format(i))
                            break
                        self.query.prepare('INSERT INTO reference(uid, tags, {}) VALUES(:uid, :tags, :location)'.format(preset))
                        self.query.bindValue(':uid', uid)
                        self.query.bindValue(':tags', json.dumps([]))
                        self.query.bindValue(':location', (data[0] << 7) + data[1])
                        if not self.query.exec_():
                            self.dbErrorLog('Sound cannot be referenced', extMessage='break at {}'.format(i))
                            break

                        if data[1] == 0:
                            bank = string.ascii_uppercase[data[0]]
                            self.logger.append(LogDebug, 'starting bank ' + bank)
                            self.factoryStatus.emit(preset, data[0])
                            print('starting bank ' + bank)

            self.query.exec_('PRAGMA journal_mode=DELETE')
            self.referenceModel.refresh()

        if createBit & self.WaveTablesEmpty:
            self.initializeWavetables()

    def initializeWavetables(self):
        def getPreview(slot):
            if not slot:
                return None
            if slot in baseShapes:
                return baseShapes[slot]
            if slot in wavetableMap:
                stream = QtCore.QDataStream(wavetableMap[slot], QtCore.QIODevice.ReadOnly)
                stream.readInt()
                snapshot = stream.readQVariant()
                keyFrames.setSnapshot(snapshot)
                return virtualScene.getPreview()
            return None

        from bigglesworth.wavetables.utils import getOscPaths
        from bigglesworth.wavetables.keyframes import VirtualKeyFrames
        from bigglesworth.wavetables.graphics import VirtualWaveTableScene

        keyFrames = VirtualKeyFrames()
        virtualScene = VirtualWaveTableScene(keyFrames)
        baseShapes = getOscPaths()
        wavetableMap = self.getWavetablePresetData()

        self.query.prepare('INSERT INTO dumpedwt(uid, name, slot, data, preview) VALUES("blofeld", :name, :slot, :data, :preview)')
        for slot in range(7):
            name = oscShapes[slot]
            self.wavetableStatus.emit(name, slot)
            self.query.bindValue(':name', name)
            self.query.bindValue(':slot', -slot)
            self.query.bindValue(':data', wavetableMap[slot] if slot else None)
            self.query.bindValue(':preview', getPreview(slot))
            if not self.query.exec_():
                print(self.query.lastError().databaseText())
        for slot in range(7, 86):
            name = oscShapes[slot]
            self.wavetableStatus.emit(name, slot)
            self.query.bindValue(':name', name)
            self.query.bindValue(':slot', slot - 6)
            self.query.bindValue(':data', wavetableMap[slot] if slot <= 72 else None)
            self.query.bindValue(':preview', getPreview(slot))
            if not self.query.exec_():
                print(self.query.lastError().databaseText())
        self.query.prepare('INSERT INTO dumpedwt(name, slot, writable) VALUES(:name, :slot, 1)')
        for slot in range(86, 125):
            name = oscShapes[slot]
            self.wavetableStatus.emit(name, slot)
            self.query.bindValue(':name', name)
            self.query.bindValue(':slot', slot - 6)
            if not self.query.exec_():
                print(self.query.lastError().databaseText())

    def updateWavetablePresets(self, data):
        if not data:
            return
        self.logger.append(LogDebug, 'Preset wavetable data missing or incomplete', extMessage=len(data))

        def getPreview(slot):
            if not slot:
                return None
            if slot in baseShapes:
                return baseShapes[slot]
            if slot in wavetableMap:
                stream = QtCore.QDataStream(wavetableMap[slot], QtCore.QIODevice.ReadOnly)
                stream.readInt()
                snapshot = stream.readQVariant()
                keyFrames.setSnapshot(snapshot)
                return virtualScene.getPreview()
            return None

        from bigglesworth.wavetables.utils import getOscPaths
        from bigglesworth.wavetables.keyframes import VirtualKeyFrames
        from bigglesworth.wavetables.graphics import VirtualWaveTableScene

        keyFrames = VirtualKeyFrames()
        virtualScene = VirtualWaveTableScene(keyFrames)
        baseShapes = getOscPaths()
        wavetableMap = self.getWavetablePresetData()

        slots = []
        for slot, data, preview in data:
            self.query.prepare('UPDATE dumpedwt SET data=:data, preview=:preview WHERE slot={}'.format(slot))
            if slot < 0:
                slot = abs(slot)
            else:
                slot += 6
            if not data:
                data = wavetableMap[slot] if slot else None
            self.query.bindValue(':data', data)
            if not preview:
                preview = getPreview(slot)
            self.query.bindValue(':preview', preview)
            if not self.query.exec_():
                self.dbErrorLog('Error updating preset wavetable data', extMessage=slot)
                return
            slots.append(oscShapes[slot])
        self.logger.append(LogDebug, 'Wavetable preset data successfully updated', extMessage=', '.join(slots))

    def getWavetablePresetData(self):
        file = QtCore.QFile(localPath('presets/wavetables.bwt'))
        file.open(QtCore.QIODevice.ReadOnly)
        stream = QtCore.QDataStream(file)
        rawXml = stream.readString()
        data = []
        while not stream.atEnd():
            data.append(stream.readQVariant())

        root = ET.fromstring(rawXml)
        if root.tag != 'Bigglesworth' and not 'WaveTableData' in root.getchildren():
            return
        typeElement = root.find('WaveTableData')
        iterData = iter(data)
        wavetableMap = {}
        for wtElement in typeElement.findall('WaveTable'):
            slot = int(wtElement.find('Slot').text)
            waveCount = int(wtElement.find('WaveCount').text)

            byteArray = QtCore.QByteArray()
            stream = QtCore.QDataStream(byteArray, QtCore.QIODevice.WriteOnly)
            stream.writeInt(waveCount)
            stream.writeQVariant(iterData.next())

            wavetableMap[slot] = byteArray

        return wavetableMap

    def getTemplatesByName(self, name=None):
        templates = {}
        queryStr = 'SELECT * FROM templates'
        if name:
            queryStr += ' WHERE name="{}"'.format(name)
        if not self.query.exec_(queryStr):
            self.dbErrorLog('Error getting template', extMessage=name)
            return templates
        while self.query.next():
            values = [self.query.value(v) for v in range(383)]
            templates[self.query.value(383)] = json.loads(self.query.value(384)), values
        return templates

    def getTemplatesByGroups(self, groups):
        templates = {}
        if not self.query.exec_('SELECT * FROM templates WHERE groups IS NOT NULL'):
            self.dbErrorLog('Error getting template groups', extMessage=groups)
            return templates
        while self.query.next():
            templateGroups = json.loads(self.query.value(384))
            if not set(groups) & set(templateGroups):
                continue
            params = []
            for id, attr in indexedValidParameterList:
                value = self.query.value(id)
                try:
                    params.append((attr, int(value)))
                except:
                    pass
#            params = map(int, [self.query.value(v) for v in range(383)])
            name = self.query.value(383)
            templates[name] = templateGroups, params
        return templates

    def getTemplateNames(self):
        if not self.query.exec_('SELECT name FROM templates'):
            self.dbErrorLog('Error getting template names')
#            print(self.query.lastError().databaseText())
            return []
        names = []
        while self.query.next():
            names.append(self.query.value(0))
        return names

    def createTemplate(self, name, params, groups=None):
        tempPre = 'INSERT INTO templates('
        tempPost = ') VALUES('
        for attr, _ in params:
            tempPre += attr + ', '
            tempPost += ':{}, '.format(attr)
        self.query.prepare(tempPre + 'name, groups' + tempPost + ':name, :groups)')
        for attr, value in params:
            self.query.bindValue(':' + attr, int(value))
        self.query.bindValue(':name', name)
        self.query.bindValue(':groups', json.dumps(groups))
        if not self.query.exec_():
            self.dbErrorLog('Error creating template', extMessage=name)
            return False
        return True

    def updateTemplates(self, templates, deleted=None):
        if deleted and not self.query.exec_('DELETE FROM templates WHERE ' + ' OR '.join(['name="{}"'.format(d) for d in deleted])):
            self.dbErrorLog('Error deleting templates')
            return False
        tempPre = 'INSERT INTO templates('
        tempPost = 'VALUES('
        updateStr = 'UPDATE templates SET '
        for p in parameterList:
            tempPre += p + ', '
            tempPost += ':' + p
            updateStr += '{}=:{}, '.format(p, p)
        insertStr = tempPre + 'name, groups) ' + tempPost + ':name, :groups)'
        updateStr += 'groups=:groups WHERE name=:name'
        self.sql.transaction()
        for name, (groups, valueList) in templates.items():
            print('cerco', name)
            self.query.exec_('SELECT name FROM templates WHERE name="{}"'.format(name))
            if self.query.next():
                self.query.prepare(updateStr)
            else:
                self.query.prepare(insertStr)
            for p, value in zip(parameterList, valueList):
                self.query.bindValue(':' + p, value)
            self.query.bindValue(':name', name)
            self.query.bindValue(':groups', json.dumps(groups))
            if not self.query.exec_():
                self.dbErrorLog('Error deleting templates')
                self.sql.rollback()
                return False
        self.sql.commit()
        return True

    def getTagColors(self, tag):
        res = self.tagsModel.match(self.tagsModel.index(0, 0), QtCore.Qt.DisplayRole, tag, flags=QtCore.Qt.MatchExactly)
        if res:
            tagIndex = res[0]
            bgd = getValidQColor(tagIndex.sibling(tagIndex.row(), 1).data(), backgroundRole)
            fgd = getValidQColor(tagIndex.sibling(tagIndex.row(), 2).data(), foregroundRole)
            return bgd, fgd
        return None

    def addBatchRawSoundData(self, dataDict, collection=None, overwrite=False):
        self.logger.append(LogDebug, 'Adding batch raw data to library')
        if overwrite:
            soundsPrepareOver = 'UPDATE sounds SET '
            soundsPrepareOver += ', '.join(['{p}=:{p}'.format(p=p) for p in soundsColumns[:-1]])
            soundsPrepareOver += ' WHERE uid = :uid'
        soundsPre = 'INSERT INTO sounds('
        soundsPost = 'VALUES('
        for p in soundsColumns[:-1]:
            soundsPre += p + ', '
            soundsPost += ':{}, '.format(p)
        soundsPrepareNorm = soundsPre + 'uid) ' + soundsPost + ':uid)'
        noTags = json.dumps([])

        imported = []
        if collection:
            refPrepare = 'INSERT INTO reference(uid, tags, "{}") VALUES(:uid, :tags, :location)'.format(collection)
        else:
            refPrepare = 'INSERT INTO reference(uid, tags) VALUES(:uid, :tags)'
        self.sql.transaction()
        for index, data in dataDict.items():
            exists = False
            if collection:
                if overwrite:
                    self.query.exec_('SELECT uid FROM reference WHERE "{}" == {}'.format(collection, index))
                    self.query.first()
                    if self.query.first() and self.query.value(0):
                        print('uid trovato:', self.query.value(0))
                        uid = self.query.value(0)
                        self.query.prepare(soundsPrepareOver)
                        exists = True
                    else:
                        uid = str(uuid.uuid4())
                        self.query.prepare(soundsPrepareNorm)
                else:
                    self.query.exec_('UPDATE reference SET "{0}" = NULL WHERE "{0}" = {1}'.format(collection, index))
                    uid = str(uuid.uuid4())
                    self.query.prepare(soundsPrepareNorm)
            else:
                uid = str(uuid.uuid4())
                self.query.prepare(soundsPrepareNorm)
            for p, d in zip(Parameters.parameterData, data):
                self.query.bindValue(':' + p.attr, p.range.sanitize(int(d)))
            self.query.bindValue(':uid', uid)
            if not self.query.exec_():
                self.dbErrorLog('Error importing sound to library')
                break
            imported.append(uid)
            if exists:
                continue
            self.query.prepare(refPrepare)
            if collection:
                self.query.bindValue(':location', index)
            self.query.bindValue(':uid', uid)
            self.query.bindValue(':tags', noTags)
            if not self.query.exec_():
                self.dbErrorLog('Error adding imported sound to library/collection')
                break
        else:
            self.sql.commit()
            self.referenceModel.refresh()
            self.libraryModel.setQuery()
            while self.libraryModel.canFetchMore():
                self.libraryModel.fetchMore()
            self.libraryModel.updated.emit()
            if collection:
                if collection in self.collections:
                    self.collections[collection].query().exec_()
                    self.collections[collection].updated.emit()
                self.logger.append(LogDebug, 'Raw data successfully added to collection', collection)
            else:
                self.logger.append(LogDebug, 'Raw data successfully added to library')
            return imported
        self.logger.append(LogWarning, 'Batch data add failure')
        self.sql.rollback()
        return False

    def addRawSoundData(self, data, collection=None, index=None, targetUid=None):
        self.logger.append(LogDebug, 'Adding raw data to library')
        if isinstance(targetUid, (str, unicode)):
            uid = targetUid
            soundsPrepare = 'UPDATE sounds SET '
            soundsPrepare += ', '.join(['{p}=:{p}'.format(p=p) for p in soundsColumns])
            soundsPrepare += ' WHERE uid = "{}"'.format(uid)
        else:
            soundsPre = 'INSERT INTO sounds('
            soundsPost = 'VALUES('
            #why?!?!?
            for p in soundsColumns[:-1]:
                soundsPre += p + ', '
                soundsPost += ':{}, '.format(p)
            soundsPrepare = soundsPre + 'uid) ' + soundsPost + ':uid)'
            uid = str(uuid.uuid4())

        self.query.prepare(soundsPrepare)
        for p, d in zip(Parameters.parameterData, data):
            self.query.bindValue(':' + p.attr, p.range.sanitize(int(d)))
        self.query.bindValue(':uid', uid)
        if not self.query.exec_():
            self.dbErrorLog('Error importing sound to library', extMessage=(collection, index, targetUid))
            return False
#        print('targetUid', targetUid)
        if not isinstance(targetUid, (str, unicode)):
            if collection:
                self.query.exec_('UPDATE reference SET "{c}" = NULL WHERE "{c}" = {i}'.format(c=collection, i=index))
                self.query.prepare('INSERT INTO reference(uid, tags, "{}") VALUES(:uid, :tags, :location)'.format(collection))
                self.query.bindValue(':location', index)
            else:
                self.query.prepare('INSERT INTO reference(uid, tags) VALUES(:uid, :tags)')
            self.query.bindValue(':uid', uid)
            self.query.bindValue(':tags', json.dumps([]))
            if not self.query.exec_():
                self.dbErrorLog('Error adding imported sound to collection')
                return False
            self.collections[collection].query().exec_()
            self.collections[collection].updated.emit()

        self.referenceModel.refresh()
        self.libraryModel.setQuery()
        while self.libraryModel.canFetchMore():
            self.libraryModel.fetchMore()
        self.libraryModel.updated.emit()
        self.logger.append(LogDebug, 'Raw data successfully added', uid)
        print('success!!!')
        return uid

    def isUidWritable(self, uid):
        if not self.query.exec_('SELECT uid FROM reference WHERE uid="{uid}" AND ({f})'.format(
            f = ' OR '.join('"{}" IS NOT NULL'.format(f) for f in factoryPresets), 
            uid = uid)):
                self.dbErrorLog('Error querying for writable uid', extMessage=uid)
                return
#        print(self.query.lastQuery())
        self.query.first()
        if self.query.record().isNull(0):
            return True
        if self.query.value(0) == uid:
            return False
        return True

    def getSoundDataFromUid(self, uid, onlyValid=False):
        params = ','.join(validParameterList if onlyValid else parameterList)
        if not self.query.exec_('SELECT {} FROM sounds WHERE uid = "{}"'.format(params, uid)):
            self.dbErrorLog('Error getting sound data from uid', extMessage=uid)
            return False
        self.query.first()
        if not isinstance(self.query.value(0), (int, long)):
            return False
        return map(int, [self.query.value(v) for v in range(len(validParameterList if onlyValid else parameterList))])

    def getIndexesFromUidList(self, uidList, collection):
        if not self.query.exec_('SELECT "{}" FROM reference WHERE {}'.format(
            collection, ' OR '.join('uid="{}"'.format(uid) for uid in uidList))):
                self.dbErrorLog('Error getting indexes for collection', extMessage=collection)
                return None
        indexes = []
        while self.query.next():
            indexes.append(self.query.value(0))
        return indexes

    def getIndexForUid(self, uid, collection):
        if not self.query.exec_('SELECT "{}" FROM reference WHERE uid="{}"'.format(
            collection, uid)):
                self.dbErrorLog('Error getting indexes for collection', extMessage=collection)
                return None
        self.query.first()
        if self.query.record().isNull(0):
            return None
        try:
            return int(self.query.value(0))
        except:
            return None

    def getIndexesForCollection(self, collection):
        if not self.query.exec_('SELECT "{}" FROM reference'.format(collection)):
            self.dbErrorLog('Error getting indexes for collection', extMessage=collection)
            return False
        indexes = []
        while self.query.next():
            value = self.query.value(0)
            if isinstance(value, (int, long)):
                indexes.append(int(value))
        if len(set(indexes)) != len(indexes):
            print('WARNING: duplicate indexes in collection', collection)
        return sorted(set(indexes))

    def getUidFromCollection(self, bank, prog, collection):
        index = (bank << 7) + prog
        if not self.query.exec_('SELECT uid FROM reference WHERE "{}" = {}'.format(collection, index)):
            self.dbErrorLog('Error getting uid from collection', extMessage=(bank, prog, collection))
            return False
        self.query.first()
        return self.query.value(0)

    def getNameFromUid(self, uid):
        self.query.prepare(
            'SELECT c00.char||c01.char||c02.char||c03.char||c04.char||c05.char||c06.char||c07.char||c08.char|' \
            '|c09.char||c10.char||c11.char||c12.char||c13.char||c14.char||c15.char FROM reference,sounds ' \
            'JOIN ascii AS c00 ON sounds.nameChar00 = c00.id JOIN ascii AS c01 ON sounds.nameChar01 = c01.id ' \
            'JOIN ascii AS c02 ON sounds.nameChar02 = c02.id JOIN ascii AS c03 ON sounds.nameChar03 = c03.id ' \
            'JOIN ascii AS c04 ON sounds.nameChar04 = c04.id JOIN ascii AS c05 ON sounds.nameChar05 = c05.id ' \
            'JOIN ascii AS c06 ON sounds.nameChar06 = c06.id JOIN ascii AS c07 ON sounds.nameChar07 = c07.id ' \
            'JOIN ascii AS c08 ON sounds.nameChar08 = c08.id JOIN ascii AS c09 ON sounds.nameChar09 = c09.id ' \
            'JOIN ascii AS c10 ON sounds.nameChar10 = c10.id JOIN ascii AS c11 ON sounds.nameChar11 = c11.id ' \
            'JOIN ascii AS c12 ON sounds.nameChar12 = c12.id JOIN ascii AS c13 ON sounds.nameChar13 = c13.id ' \
            'JOIN ascii AS c14 ON sounds.nameChar14 = c14.id JOIN ascii AS c15 ON sounds.nameChar15 = c15.id ' \
            'WHERE sounds.uid = reference.uid AND reference.uid = :uid')
        self.query.bindValue(':uid', uid)
        if not self.query.exec_():
            self.dbErrorLog('Error getting name from uid', extMessage=uid)
            return ''
        self.query.next()
        return self.query.value(0)

#    def getUidNameDict(self):
#        res = self.query.exec_('SELECT uid, c00.char||c01.char||c02.char||c03.char||c04.char||c05.char||c06.char||c07.char||' \
#            'c08.char||c09.char||c10.char||c11.char||c12.char||c13.char||c14.char||c15.char' \
#            ' FROM sounds JOIN ascii AS c00 ON sounds.nameChar00 = c00.id' \
#            ' JOIN ascii AS c01 ON sounds.nameChar01 = c01.id JOIN ascii AS c02 ON sounds.nameChar02 = c02.id' \
#            ' JOIN ascii AS c03 ON sounds.nameChar03 = c03.id JOIN ascii AS c04 ON sounds.nameChar04 = c04.id' \
#            ' JOIN ascii AS c05 ON sounds.nameChar05 = c05.id JOIN ascii AS c06 ON sounds.nameChar06 = c06.id' \
#            ' JOIN ascii AS c07 ON sounds.nameChar07 = c07.id JOIN ascii AS c08 ON sounds.nameChar08 = c08.id' \
#            ' JOIN ascii AS c09 ON sounds.nameChar09 = c09.id JOIN ascii AS c10 ON sounds.nameChar10 = c10.id' \
#            ' JOIN ascii AS c11 ON sounds.nameChar11 = c11.id JOIN ascii AS c12 ON sounds.nameChar12 = c12.id' \
#            ' JOIN ascii AS c13 ON sounds.nameChar13 = c13.id JOIN ascii AS c14 ON sounds.nameChar14 = c14.id' \
#            ' JOIN ascii AS c15 ON sounds.nameChar15 = c15.id')
#        if not res:
#            print(self.query.lastError().databaseText())
#            return
#        uidNameDict = {}
#        while self.query.next():
#            uidNameDict[self.query.value(0)] = self.query.value(1)
#        return uidNameDict
#
#    def getNameUidList(self):
#        res = self.query.exec_('SELECT c00.char||c01.char||c02.char||c03.char||c04.char||c05.char||c06.char||c07.char||' \
#            'c08.char||c09.char||c10.char||c11.char||c12.char||c13.char||c14.char||c15.char' \
#            ' FROM sounds JOIN ascii AS c00 ON sounds.nameChar00 = c00.id' \
#            ' JOIN ascii AS c01 ON sounds.nameChar01 = c01.id JOIN ascii AS c02 ON sounds.nameChar02 = c02.id' \
#            ' JOIN ascii AS c03 ON sounds.nameChar03 = c03.id JOIN ascii AS c04 ON sounds.nameChar04 = c04.id' \
#            ' JOIN ascii AS c05 ON sounds.nameChar05 = c05.id JOIN ascii AS c06 ON sounds.nameChar06 = c06.id' \
#            ' JOIN ascii AS c07 ON sounds.nameChar07 = c07.id JOIN ascii AS c08 ON sounds.nameChar08 = c08.id' \
#            ' JOIN ascii AS c09 ON sounds.nameChar09 = c09.id JOIN ascii AS c10 ON sounds.nameChar10 = c10.id' \
#            ' JOIN ascii AS c11 ON sounds.nameChar11 = c11.id JOIN ascii AS c12 ON sounds.nameChar12 = c12.id' \
#            ' JOIN ascii AS c13 ON sounds.nameChar13 = c13.id JOIN ascii AS c14 ON sounds.nameChar14 = c14.id' \
#            ' JOIN ascii AS c15 ON sounds.nameChar15 = c15.id, uid')
#        if not res:
#            print(self.query.lastError().databaseText())
#            return
#        nameUidList = []
#        while self.query.next():
#            nameUidList.append((self.query.value(0), self.query.value(1)))
#        return nameUidList
#
#    def getUidNameCatDict(self):
#        print(self.referenceModel.allCollections)
#        res = self.query.exec_('SELECT sounds.uid, c00.char||c01.char||c02.char||c03.char||c04.char||c05.char||c06.char||c07.char||' \
#            'c08.char||c09.char||c10.char||c11.char||c12.char||c13.char||c14.char||c15.char, sounds.category, reference.tags' \
#            ' FROM sounds, reference JOIN ascii AS c00 ON sounds.nameChar00 = c00.id' \
#            ' JOIN ascii AS c01 ON sounds.nameChar01 = c01.id JOIN ascii AS c02 ON sounds.nameChar02 = c02.id' \
#            ' JOIN ascii AS c03 ON sounds.nameChar03 = c03.id JOIN ascii AS c04 ON sounds.nameChar04 = c04.id' \
#            ' JOIN ascii AS c05 ON sounds.nameChar05 = c05.id JOIN ascii AS c06 ON sounds.nameChar06 = c06.id' \
#            ' JOIN ascii AS c07 ON sounds.nameChar07 = c07.id JOIN ascii AS c08 ON sounds.nameChar08 = c08.id' \
#            ' JOIN ascii AS c09 ON sounds.nameChar09 = c09.id JOIN ascii AS c10 ON sounds.nameChar10 = c10.id' \
#            ' JOIN ascii AS c11 ON sounds.nameChar11 = c11.id JOIN ascii AS c12 ON sounds.nameChar12 = c12.id' \
#            ' JOIN ascii AS c13 ON sounds.nameChar13 = c13.id JOIN ascii AS c14 ON sounds.nameChar14 = c14.id' \
#            ' JOIN ascii AS c15 ON sounds.nameChar15 = c15.id WHERE sounds.uid = reference.uid')
#        if not res:
#            print(self.query.lastError().databaseText())
#            return
#        uidNameDict = {}
#        while self.query.next():
#            uidNameDict[self.query.value(0)] = self.query.value(1), self.query.value(2)
#        self.query.finish()
#        return uidNameDict

    def getCollectionsFromUid(self, uid, ignorePresets=True):
        if not self.query.exec_('SELECT * FROM reference WHERE uid == "{}"'.format(uid)):
            self.dbErrorLog('Error getting collections for uid', extMessage=(uid, ignorePresets))
            return False
        self.query.first()
        collections = []
        for c in range(2, self.query.record().count()):
            if isinstance(self.query.value(c), (int, long)):
                collection = c - 2
                if collection <= 2 and ignorePresets:
                    continue
                collections.append(collection)
        return collections

    def getNamesFromUidList(self, uidList):
        nameList = []
        splitted = uidList[:500]
        delta = 0
        while splitted:
            res = self.query.exec_('SELECT c00.char||c01.char||c02.char||c03.char||c04.char||c05.char||c06.char||c07.char||' \
                'c08.char||c09.char||c10.char||c11.char||c12.char||c13.char||c14.char||c15.char' \
                ' FROM reference,sounds JOIN ascii AS c00 ON sounds.nameChar00 = c00.id' \
                ' JOIN ascii AS c01 ON sounds.nameChar01 = c01.id JOIN ascii AS c02 ON sounds.nameChar02 = c02.id' \
                ' JOIN ascii AS c03 ON sounds.nameChar03 = c03.id JOIN ascii AS c04 ON sounds.nameChar04 = c04.id' \
                ' JOIN ascii AS c05 ON sounds.nameChar05 = c05.id JOIN ascii AS c06 ON sounds.nameChar06 = c06.id' \
                ' JOIN ascii AS c07 ON sounds.nameChar07 = c07.id JOIN ascii AS c08 ON sounds.nameChar08 = c08.id' \
                ' JOIN ascii AS c09 ON sounds.nameChar09 = c09.id JOIN ascii AS c10 ON sounds.nameChar10 = c10.id' \
                ' JOIN ascii AS c11 ON sounds.nameChar11 = c11.id JOIN ascii AS c12 ON sounds.nameChar12 = c12.id' \
                ' JOIN ascii AS c13 ON sounds.nameChar13 = c13.id JOIN ascii AS c14 ON sounds.nameChar14 = c14.id' \
                ' JOIN ascii AS c15 ON sounds.nameChar15 = c15.id WHERE (sounds.uid = reference.uid) AND (' + \
                ' OR '.join('(reference.uid == "{}")'.format(uid) for uid in splitted) + ')')
            if not res:
                self.dbErrorLog('Error getting names from list of uid', extMessage=splitted)
                return
            while self.query.next():
                nameList.append(self.query.value(0))
            delta += 1
            splitted = uidList[500 * delta: 500 * (delta + 1)]
        return nameList

    def getTagsForUidList(self, uidList):
#        where = ') OR ('.join('sounds.uid="{uid}" AND reference.uid="{uid}"'.format(uid=uid) for uid in uidList)
#        if not self.query.exec_('SELECT reference.tags FROM sounds,reference WHERE ({})'.format(where)):
        tags = {}
        splitted = uidList[:500]
        delta = 0
        while splitted:
            for uid in splitted:
                if not self.query.exec_('SELECT reference.tags FROM sounds,reference WHERE reference.uid = "{}"'.format(uid)):
                    self.dbErrorLog('Error searching tags for uid list', extMessage=', '.join(splitted))
                    return tags
                self.query.first()
                tags[uid] = json.loads(self.query.value(0))
            delta += 1
            splitted = uidList[500 * delta: 500 * (delta + 1)]
        return tags

    def setTagsForUidList(self, uidList, tags):
        splitted = uidList[:500]
        delta = 0
        while splitted:
            where = ') OR ('.join('reference.uid="{uid}"'.format(uid=uid) for uid in splitted)
            self.query.prepare('UPDATE reference SET tags = :tags WHERE ({})'.format(where))
            self.query.bindValue(':tags', json.dumps(tags))
            if not self.query.exec_():
                self.dbErrorLog('Error updating tags for uid list', extMessage='{} {}'.format(', '.join(splitted), tags))
                return
            delta += 1
            splitted = uidList[500 * delta: 500 * (delta + 1)]
        self.libraryModel.updated.emit()

    def updateSoundValue(self, uid, paramId, value):
        if not self.query.exec_('UPDATE sounds SET {attr} = {value} WHERE uid = "{uid}"'.format(
            attr=Parameters.parameterData[paramId].attr, 
            value=int(value), 
            uid=uid)):
                self.dbErrorLog('Error updating value for sound', extMessage=(uid, paramId, value))
                return False
        return True

    def updateSound(self, uid, parameters):
        fieldList = ', '.join(['{}=:{}'.format(p, p) for p in parameterList])
        self.query.prepare('UPDATE sounds SET {} WHERE uid="{}"'.format(fieldList, uid))
        for p, value in zip(parameterList, parameters):
            self.query.bindValue(':{}'.format(p), int(value))
        if not self.query.exec_():
            self.dbErrorLog('Error updating sound values', extMessage=uid)
            return False
        return True

    def checkDuplicates(self, uidList, collection):
        duplicates = []
        splitted = uidList[:250]
        delta = 0
        while splitted:
            where = ' OR '.join('reference.uid = "{}"'.format(uid) for uid in splitted)
            res = self.query.exec_('SELECT reference.uid FROM reference WHERE reference."{}" IS NOT NULL AND ({})'.format(collection, where))
            if not res:
                self.dbErrorLog('Error checking for duplicates in collection', extMessage=(splitted, collection))
                break
            else:
                while self.query.next():
                    duplicates.append(self.query.value(0))
            delta += 1
            splitted = uidList[250 * delta: 250 * (delta + 1)]
        return duplicates

    def editTag(self, newName, oldName, bgd=None, fgd=None):
        self.sql.transaction()
        if oldName and newName != oldName:
            self.query.exec_('SELECT uid, tags FROM reference WHERE tags IS NOT NULL AND tags != "[]"')
            uidDict = {}
            while self.query.next():
                tags = json.loads(self.query.value(1))
                if oldName in tags:
                    tags.remove(oldName)
                    tags.append(newName)
                    uidDict[self.query.value(0)] = sorted(tags)

            for uid, tags in uidDict.items():
                self.query.prepare('UPDATE reference SET tags=:tags WHERE uid=:uid')
                self.query.bindValue(':uid', uid)
                self.query.bindValue(':tags', json.dumps(tags))
                if not self.query.exec_():
                    self.dbErrorLog('Error updating tags for uid', extMessage=(tags, uid))
                    self.sql.rollback()
                    return

        self.sql.commit()
        if oldName:
            res = self.tagsModel.match(self.tagsModel.index(0, 0), QtCore.Qt.DisplayRole, oldName, flags=QtCore.Qt.MatchExactly)
            if not res:
                self.dbErrorLog('Error trying to update tag', extMessage=(oldName))
                return
            index = res[0]
        else:
            row = self.tagsModel.rowCount()
            self.tagsModel.insertRow(row)
            index = self.tagsModel.index(row, 0)
        self.tagsModel.setData(index, newName)
        self.tagsModel.setData(index.sibling(index.row(), 1), json.dumps(bgd.getRgb()[:3]) if bgd is not None else None)
        self.tagsModel.setData(index.sibling(index.row(), 2), json.dumps(fgd.getRgb()[:3]) if bgd is not None else None)
        return self.tagsModel.submitAll()

    def deleteTag(self, tag):
        self.sql.transaction()
        self.query.exec_('SELECT uid, tags FROM reference WHERE tags IS NOT NULL AND tags != "[]"')
        uidDict = {}
        while self.query.next():
            tags = json.loads(self.query.value(1))
            if tag in tags:
                tags.remove(tag)
                uidDict[self.query.value(0)] = sorted(tags)

        for uid, tags in uidDict.items():
            self.query.prepare('UPDATE reference SET tags=:tags WHERE uid=:uid')
            self.query.bindValue(':uid', uid)
            self.query.bindValue(':tags', json.dumps(tags))
            if not self.query.exec_():
                self.dbErrorLog('Error updating tags for uid', extMessage=(tags, uid))
                self.sql.rollback()
                return

        if not self.sql.commit():
            self.dbErrorLog('Error finalizing tag updates', extMessage=(tags, uidDict.keys()))
            return

        res = self.tagsModel.match(self.tagsModel.index(0, 0), QtCore.Qt.DisplayRole, tag, flags=QtCore.Qt.MatchExactly)
        if not res:
            self.dbErrorLog('Error trying to delete tag', extMessage=(tag))
            return
        self.tagsModel.removeRow(res[0].row())
        return self.tagsModel.submitAll()

    def createCollection(self, name, source=None, iconName=None, initBanks=None):
        if not self.query.exec_(u'ALTER TABLE reference ADD COLUMN "{}" int'.format(name)):
            self.dbErrorLog('Error creating collection', extMessage=(name))
            return False
        if source:
            if source not in factoryPresets:
                if not self.query.exec_(u'UPDATE reference SET "{}" = "{}"'.format(name, source)):
                    self.dbErrorLog('Error creating collection from source', extMessage=(name, source))
                    return False
            else:
                self.query.exec_(u'SELECT uid FROM reference WHERE {0} IS NOT NULL ORDER BY {0} ASC'.format(source))
                uidList = []
                while self.query.next():
                    uidList.append(self.query.value(0))
                self.sql.transaction()
                self.dbErrorLog('Creating duplicates from factory', LogDebug, extMessage=source)

                fieldList = [':{}'.format(p) for p in parameterList]
                prepareStr = 'SELECT {}, reference.tags FROM sounds,reference WHERE sounds.uid=:uid AND reference.uid=:uid2'.format(', '.join('sounds.' + p for p in parameterList))
                reader = QtSql.QSqlQuery()
                reader.prepare(prepareStr)
                insertPrepare = 'INSERT INTO sounds({}, uid) VALUES({}, :uid)'.format(', '.join(parameterList), ', '.join(fieldList))

                for index, uid in enumerate(uidList):
                    reader.prepare(prepareStr)
                    reader.bindValue(':uid', uid)
                    reader.bindValue(':uid2', uid)
                    reader.exec_()
                    reader.first()
                    values = [reader.value(i) for i in range(383)]
                    tags = reader.value(383)

                    self.query.prepare(insertPrepare)
                    for p, value in zip(fieldList, values):
                        self.query.bindValue(p, value)
                    newUid = str(uuid.uuid4())
                    self.query.bindValue(':uid', newUid)
                    if not self.query.exec_():
                        self.dbErrorLog('Error creating duplicate', extMessage=(uid, newUid))
                        self.sql.rollback()
                        self.referenceModel.refresh()
                        return False

                    self.query.prepare('INSERT INTO reference(uid, tags, "{}") VALUES(:uid, :tags, :target)'.format(name))
                    self.query.bindValue(':uid', newUid)
                    self.query.bindValue(':tags', tags)
                    self.query.bindValue(':target', index)
                    if not self.query.exec_():
                        self.dbErrorLog('Error updating data for duplicate', extMessage=(uid, newUid))
                        self.sql.rollback()
                        self.referenceModel.refresh()
                        return False
                    if not index % 32:
                        print(index)
                self.sql.commit()
                self.dbErrorLog('Factory cloned successfully', LogDebug)
        elif initBanks is not None:
            self.initBanks(initBanks, name)

        if iconName is not None:
            self.main.settings.beginGroup('CollectionIcons')
            self.main.settings.setValue(name, iconName)
            self.main.settings.endGroup()

        self.referenceModel.refresh()
        return True

    def initBanks(self, banks, collection, allSlots=True):
        dataDict = {}
        data = [p.default for p in Parameters.parameterData]
        ignore = self.getIndexesForCollection(collection) if not allSlots else []
        for bank in banks:
            for index in range(bank * 128, (bank + 1) * 128):
                if index in ignore:
                    continue
                dataDict[index] = data
        self.addBatchRawSoundData(dataDict, collection=collection)

    def initSound(self, index, collection):
        self.addRawSoundData([p.default for p in Parameters.parameterData], collection=collection, index=index)
        self.collections[collection].query().exec_()
        self.collections[collection].updated.emit()

    def getCountForCollection(self, collection):
        #perché non funziona con il prepare?!
        if not self.query.exec_('SELECT COUNT() FROM reference WHERE "{}" IS NOT NULL'.format(collection)):
            self.dbErrorLog('Error counting collection contents', extMessage=(collection))
        self.query.next()
        return self.query.value(0)

    def getCountForCategory(self, category):
        if not self.query.exec_('SELECT COUNT() FROM sounds WHERE category == {}'.format(category)):
            self.dbErrorLog('Error counting sounds by category', extMessage=(categories[category]))
        self.query.next()
        return self.query.value(0)

    def getCountForTag(self, tag):
        if not self.query.exec_('SELECT tags FROM reference WHERE tags IS NOT NULL AND tags != "[]"'):
            self.dbErrorLog('Error counting sounds by tag', extMessage=(tag))
        count = 0
        while self.query.next():
            tags = json.loads(self.query.value(0))
            if tag in tags:
                count += 1
        return count

    def getAlternateNameChrs(self, uid, name):
#        self.query.exec_(
#            'SELECT nameChar00, nameChar01, nameChar02, nameChar03, nameChar04, ' \
#            'nameChar05, nameChar06, nameChar07, nameChar08, nameChar09, nameChar10, ' \
#            'nameChar11, nameChar12, nameChar13, nameChar14, nameChar15 ' \
#            'FROM sounds WHERE uid != "{}"'.format(uid))
        if not name.rstrip():
            name = 'NewDuplicate    '
        else:
            reMatch = renameRegExp.match(name)
            if reMatch:
                _count = reMatch.groupdict()['count']
                if _count is not None:
                    _count = int(_count) + 1
                    if _count > 999:
                        _count = 0
                else:
                    _count = 1
                name = reMatch.groupdict()['name']
                countStr = str(_count)
            else:
                name = name.rstrip()
                countStr = '1'
            name = '{}~{}'.format(name[:15 - len(countStr)], countStr).ljust(16, ' ')
#        regexp = QtCore.QRegExp(r'^{}\s*$'.format(QtCore.QRegExp.escape(name.rstrip())))
#        res = self.libraryModel.match(self.libraryModel.index(0, NameColumn), QtCore.Qt.DisplayRole, regexp.pattern(), flags=QtCore.Qt.MatchRegExp)
        if not self.libraryModel.match(self.libraryModel.index(0, NameColumn), QtCore.Qt.DisplayRole, name, flags=QtCore.Qt.MatchExactly):
            return name
        return self.getAlternateNameChrs(uid, name)

    def duplicateSound(self, uid, collection=None, target=-1, rename=True):
        fieldList = [':{}'.format(p) for p in parameterList]
        self.query.prepare('SELECT {}, reference.tags FROM sounds,reference WHERE sounds.uid=:uid AND reference.uid=:uid2'.format(', '.join('sounds.' + p for p in parameterList)))
        self.query.bindValue(':uid', uid)
        self.query.bindValue(':uid2', uid)
        if not self.query.exec_():
            self.dbErrorLog('Error duplicating sound', extMessage=(uid, collection, target, rename))
            return False
        self.query.first()
        values = [self.query.value(i) for i in range(383)]
        tags = self.query.value(383)
        if rename:
            newNameChrs = self.getAlternateNameChrs(uid, getName(values[363:379]))
            for i, chr in enumerate(newNameChrs, 363):
                values[i] = chr2ord[chr]
        self.query.prepare('INSERT INTO sounds({}, uid) VALUES({}, :uid)'.format(', '.join(parameterList), ', '.join(fieldList)))
        for p, value in zip(fieldList, values):
            self.query.bindValue(p, value)
        newUid = str(uuid.uuid4())
        self.query.bindValue(':uid', newUid)
        if not self.query.exec_():
            self.dbErrorLog('Error inserting values for duplicate sound', extMessage=(uid, collection, target, rename))
            return False
        if collection:
            self.query.prepare('INSERT INTO reference(uid, tags, "{}") VALUES(:uid, :tags, :target)'.format(collection))
            self.query.bindValue(':uid', newUid)
            self.query.bindValue(':tags', tags)
            self.query.bindValue(':target', target)
            if not self.query.exec_():
                self.dbErrorLog('Error adding reference to collection for duplicate sound', extMessage=(uid, collection, target, rename))
                return False
        else:
            self.query.prepare('INSERT INTO reference(uid, tags) VALUES(:uid, :tags)')
            self.query.bindValue(':uid', newUid)
            self.query.bindValue(':tags', tags)
            if not self.query.exec_():
                self.dbErrorLog('Error adding reference for duplicate sound', extMessage=(uid, newUid))
                return False
        self.libraryModel.setQuery()
        while self.libraryModel.canFetchMore():
            self.libraryModel.fetchMore()
        self.libraryModel.updated.emit()
        return newUid

    def addSoundsToCollection(self, uidMap, collection):
        fieldList = [':{}'.format(p) for p in parameterList]
        prepareStr = 'SELECT {}, reference.tags FROM sounds,reference WHERE sounds.uid=:uid AND reference.uid=:uid2'.format(', '.join('sounds.' + p for p in parameterList))
        reader = QtSql.QSqlQuery()
        reader.prepare(prepareStr)
        insertPrepare = 'INSERT INTO sounds({}, uid) VALUES({}, :uid)'.format(', '.join(parameterList), ', '.join(fieldList))

        splitted = uidMap[:500]
        delta = 0
        while splitted:
            queryStr = 'UPDATE reference SET "{}" = NULL WHERE '.format(collection)
            queryStr += ' OR '.join('"{}" = {}'.format(collection, target) for _, target in uidMap)
            self.sql.transaction()
            self.query.exec_(queryStr)
            print('inizio', splitted)
            for pos, (uid, target) in enumerate(splitted):
                #preset sounds have to be duplicated before adding to collection
                if not self.query.exec_('SELECT blofeld_fact_200801,blofeld_fact_200802,blofeld_fact_201200 FROM reference WHERE uid = "{}"'.format(uid)):
                    self.dbErrorLog('Error adding sounds to collection', extMessage=(splitted, collection))
                    self.sql.rollback()
                    return False
                self.query.first()
                if isinstance(self.query.value(0), (int, long)) or \
                    isinstance(self.query.value(1), (int, long)) or \
                    isinstance(self.query.value(2), (int, long)):
                        #manual duplicate for performance
    #                    uid = self.duplicateSound(uid, rename=False)
                        reader.prepare(prepareStr)
                        reader.bindValue(':uid', uid)
                        reader.bindValue(':uid2', uid)
                        reader.exec_()
                        reader.first()
                        values = [reader.value(i) for i in range(383)]
                        tags = reader.value(383)

                        self.query.prepare(insertPrepare)
                        for p, value in zip(fieldList, values):
                            self.query.bindValue(p, value)
                        newUid = str(uuid.uuid4())
                        self.query.bindValue(':uid', newUid)
                        if not self.query.exec_():
                            self.dbErrorLog('Error creating duplicate', extMessage=(uid, newUid))
                            self.sql.rollback()
                            self.referenceModel.refresh()
                            return False

                        self.query.prepare('INSERT INTO reference(uid, tags, "{}") VALUES(:uid, :tags, :target)'.format(collection))
                        self.query.bindValue(':uid', newUid)
                        self.query.bindValue(':tags', tags)
                        self.query.bindValue(':target', target)
                        if not self.query.exec_():
                            self.dbErrorLog('Error updating data for duplicate', extMessage=(uid, newUid))
                            self.sql.rollback()
                            self.referenceModel.refresh()
                            return False
                elif not self.query.exec_('UPDATE reference SET "{}" = {} WHERE uid = "{}"'.format(
                    collection, 
                    target, 
                    uid
                    )):
                        self.dbErrorLog('Error updating reference while adding sounds to collection', extMessage=(uidMap, collection))
                        self.sql.rollback()
                        return False
                if not pos % 50:
                    print(pos)
            delta += 1
            splitted = uidMap[500 * delta: 500 * (delta + 1)]

        self.sql.commit()
        self.collections[collection].query().exec_()
        self.collections[collection].updated.emit()

        self.libraryModel.setQuery()
        while self.libraryModel.canFetchMore():
            self.libraryModel.fetchMore()
        self.libraryModel.updated.emit()

        return True

    def removeSounds(self, uidList, collection):
        splitted = uidList[:500]
        delta = 0
        while splitted:
            where = ' OR '.join('uid = "{}"'.format(uid) for uid in splitted)
            if not self.query.exec_('UPDATE reference SET "{}" = NULL WHERE {}'.format(collection, where)):
                self.dbErrorLog('Error removing sound from collection', extMessage=(splitted, collection))
                return False
            delta += 1
            splitted = uidList[500 * delta: 500 * (delta + 1)]
        self.collections[collection].query().exec_()
        self.collections[collection].updated.emit()
        return True

    def deleteSounds(self, uidList):
        splitted = uidList[:500]
        delta = 0
        collections = self.referenceModel.collections
        reference = set()
        while splitted:
            where = ' OR '.join('uid = "{}"'.format(uid) for uid in splitted)
            if not self.query.exec_('SELECT {} FROM reference WHERE {}'.format(', '.join('"{}"'.format(c) for c in collections), where)):
                self.dbErrorLog('Error deleting sounds from main library', extMessage=splitted)
                return False
            while self.query.next():
                for colId, collection in enumerate(collections):
                    try:
                        int(self.query.value(colId))
                        reference.add(collection)
                    except:
                        pass
            if not self.query.exec_('DELETE FROM reference WHERE {}'.format(where)):
                self.dbErrorLog('Error deleting reference while deleting sound', extMessage=splitted)
            if not self.query.exec_('DELETE FROM sounds WHERE {}'.format(where)):
                self.dbErrorLog('Error deleting sound data while deleting sound', extMessage=splitted)
            delta += 1
            splitted = uidList[500 * delta: 500 * (delta + 1)]

        for collection in reference:
            if collection in self.collections:
                self.collections[collection].updated.emit()
        self.libraryModel.setQuery()
        while self.libraryModel.canFetchMore():
            self.libraryModel.fetchMore()
        self.libraryModel.updated.emit()

    def duplicateAndInsert(self, uidList, collection, target):
        totRows = len(uidList)
        self.query.exec_('SELECT "{}" as location, uid FROM reference WHERE location IS NOT NULL'.format(collection))
        dataMap = {l:None for l in range(1024)}
        while self.query.next():
            dataMap[self.query.value(0)] = self.query.value(1)
        last = pos = target
        found = []
        delta = 1
        while True:
            while dataMap[pos] is not None:
                pos += delta
                if pos > 1023:
                    pos = target
                    delta = -1
            found.append(pos)
            if len(found) == totRows:
                break
            pos += delta
            if pos > 1023:
                pos = target
                delta = -1

        self.sql.transaction()
        newUidList = [self.duplicateSound(uid) for uid in uidList]
        first = min(found + [target])
        last = max(found + [target - 1])
        oldUidList = {k:v for k, v in dataMap.items() if first <= k <= last and v is not None}
        if target <= first:
            for pos, uid in enumerate(newUidList, target):
                if not self.query.exec_('UPDATE reference SET "{}" = {} WHERE uid = "{}"'.format(collection, pos, uid)):
                    self.dbErrorLog('Error updating reference', extMessage=(collection, pos, uid))
                    self.sql.rollback()
                    return
            for p in sorted(oldUidList.keys()):
                pos += 1
                if not self.query.exec_('UPDATE reference SET "{}" = {} WHERE uid = "{}"'.format(collection, pos, oldUidList[p])):
                    self.dbErrorLog('Error updating reference', extMessage=(collection, pos, oldUidList[p]))
                    self.sql.rollback()
                    return
        else:
            pos = first
            for p in sorted(oldUidList.keys()):
                if not self.query.exec_('UPDATE reference SET "{}" = {} WHERE uid = "{}"'.format(collection, pos, oldUidList[p])):
                    self.dbErrorLog('Error updating reference', extMessage=(collection, pos, oldUidList[p]))
                    self.sql.rollback()
                    return
                pos += 1
            for pos, uid in enumerate(newUidList, pos):
                if not self.query.exec_('UPDATE reference SET "{}" = {} WHERE uid = "{}"'.format(collection, pos, uid)):
                    self.dbErrorLog('Error updating reference', extMessage=(collection, pos, uid))
                    self.sql.rollback()
                    return
        self.sql.commit()
        self.collections[collection].query().exec_()
        self.collections[collection].updated.emit()

    def duplicateAndReplace(self, uidList, collection, targetRows):
        first = min(targetRows)
        last = max(targetRows)
        existing = []
        self.query.exec_('SELECT uid FROM reference WHERE ("{}" BETWEEN {} AND {}) AND uid IN ({})'.format(
            collection, 
            first, 
            last, 
            ', '.join('"{}"'.format(uid) for uid in uidList)
            ))
        while self.query.next():
            existing.append(self.query.value(0))
        self.sql.transaction()
        if not self.query.exec_('UPDATE reference SET "{c}" = NULL WHERE "{c}" BETWEEN {s} AND {e}'.format(
            c=collection, s=first, e=last)):
                self.dbErrorLog('Error clearing reference', extMessage=(collection, first, last))
                self.sql.rollback()
                return
        uidMap = []
        for uid, target in zip(uidList, targetRows):
            if uid in existing:
                uidMap.append((uid, target))
            else:
                newUid = self.duplicateSound(uid)
                uidMap.append((newUid, target))
        self.sql.commit()
        self.addSoundsToCollection(uidMap, collection)

    def swapSounds(self, uidList, collection, targetRows):
        self.query.exec_('SELECT "{c}", uid FROM reference WHERE uid in({u})'.format(
            c=collection, 
            u=', '.join('"{}"'.format(uid) for uid in uidList)))
        sourceRows = {}
        while self.query.next():
            sourceRows[self.query.value(0)] = self.query.value(1)
        self.query.exec_('SELECT uid, "{c}" FROM reference WHERE "{c}" BETWEEN {f} AND {l}'.format(
            c=collection, 
            f=min(targetRows), 
            l=max(targetRows)
            ))
        moving = {}
        while self.query.next():
            moving[self.query.value(1)] = self.query.value(0)
        self.query.finish()
        if len(uidList) == len(targetRows):
            for s in sorted(targetRows):
                if not s in moving:
                    moving[s] = None
            finalLayout = {t:u for t, u in zip(targetRows, uidList)}
            iterSourceRows = iter(sourceRows)
            for s in sorted(moving):
                if moving[s] in uidList:
                    continue
                nextOld = iterSourceRows.next()
                while nextOld in moving:
                    nextOld = iterSourceRows.next()
                finalLayout[nextOld] = moving[s]

            self.sql.transaction()
            for l, uid in finalLayout.items():
                if not self.query.exec_('UPDATE reference SET "{c}" = {l} WHERE uid = "{u}"'.format(
                    c=collection, 
                    l=l, 
                    u=uid, 
                    )):
                        self.dbErrorLog('Error swapping sound', extMessage=(collection, uid, l))
                        self.sql.rollback()
                        return
            self.sql.commit()
        else:
            print(sourceRows.keys())
            print(targetRows)
            return
        self.collections[collection].query().exec_()
        self.collections[collection].updated.emit()
#        check this:
#        https://stackoverflow.com/questions/31197144/why-is-my-sqlite-query-so-slow-in-qt5

    def insertSounds(self, uidList, collection, sourceRows, target):
        print(sourceRows, target)
        firstSource = min(sourceRows)
        lastSource = max(sourceRows)
        if lastSource - firstSource + 1 == len(sourceRows) and \
            (target == firstSource or target == lastSource + 1):
                #selection is sequential and we ignore insertions just before or after it
                return
        if target <= firstSource:
            affected = range(target, lastSource + 1)
        elif target >= lastSource:
            affected = range(firstSource, target)
        else:
            affected = range(firstSource, lastSource + 1)
        self.query.exec_('SELECT "{c}", uid FROM reference WHERE "{c}" IN ({l})'.format(
            c=collection, 
            l=', '.join(str(l) for l in affected if l not in sourceRows)
            ))
        moving = {}
        while self.query.next():
            moving[self.query.value(0)] = self.query.value(1)
        for r in affected:
            if r not in moving and r not in sourceRows:
                moving[r] = None
        finalLayout = {}
        if target <= firstSource:
            for l, uid in zip(range(target, len(uidList) + target), uidList):
                finalLayout[l] = uid
            for m, t in zip(sorted(moving), range(target + len(uidList), max(affected) + 1)):
                finalLayout[t] = moving[m]
        elif target > lastSource:
            for m, t in zip(sorted(moving), range(min(affected), target)):
                finalLayout[t] = moving[m]
            for l, uid in zip(range(target - len(uidList), target + 1), uidList):
                finalLayout[l] = uid
        else:
            #we don't need this right now, but might come useful whenever we add extended selections
#            pre = {}
#            for p in range(firstSource, target):
#                if p in moving and p not in sourceRows:
#                    pre[p] = moving[p]
#            post = {}
#            for p in range(target, lastSource + 1):
#                if p in moving and p not in sourceRows:
#                    post[p] = moving[p]
            delta = 0
            for p in range(firstSource, target):
                if p in moving and p not in sourceRows:
                    delta += 1
            iterUid = iter(uidList)
            target = firstSource + delta
            for t in range(target, target + len(uidList)):
                finalLayout[t] = iterUid.next()
        self.sql.transaction()
        for l, uid in finalLayout.items():
            if not uid:
                continue
            if not self.query.exec_('UPDATE reference SET "{c}" = {l} WHERE uid = "{u}"'.format(
                c=collection, 
                l=l, 
                u=uid, 
                )):
                    self.dbErrorLog('Error inserting sounds', extMessage=(collection, uid, l))
                    self.sql.rollback()
                    return
        self.sql.commit()
        self.collections[collection].query().exec_()
        self.collections[collection].updated.emit()


    def updateCollections(self, renamed, deleted):
        print('renamed:', renamed, 'deleted', deleted)
        for newName, oldName in renamed.items():
            if oldName in deleted:
                continue
            print('rinomino', oldName, newName)
            try:
                collection = self.collections.pop(oldName)
                self.collections[newName] = collection
            except:
                pass
        for collection in deleted:
            print('elimino', collection)
            try:
                popped = self.collections.pop(collection)
                popped.deleteLater()
            except:
                pass
        print('fatto!')

    def openCollection(self, name=None):
        if name in self.collections:
            return self.collections[name]
        if not name:
            collection = LibraryModel(self)
        else:
            collection = CollectionModel(name)
        collection.soundNameChanged.connect(self.soundNameChanged)
        if self.main.argparse.log:
            collection.logger = self.logger
#        collection.dataChanged.connect(self.collectionChanged)
        while collection.canFetchMore():
            collection.fetchMore()
        collection.updated.connect(self.collectionChanged)
        self.tagsModel.dataChanged.connect(lambda *args: collection.query().exec_())
        self.collections[name] = collection
        return collection

    def collectionChanged(self, *args):
#        sender = self.sender()
        collections = self.collections.values()
        collections.remove(self.sender())
        for collection in collections:
            collection.scheduleQueryUpdate()
            collection.modelReset.emit()


class CollectionManagerModel(QtSql.QSqlTableModel):
    updated = QtCore.pyqtSignal()

    def __init__(self):
        QtSql.QSqlTableModel.__init__(self)
        self.refresh()

    def refresh(self):
        self.setTable('reference')
        self.select()
        while self.canFetchMore():
            self.fetchMore()
        self.updated.emit()

    @property
    def collections(self):
        return [self.headerData(c, QtCore.Qt.Horizontal, QtCore.Qt.DisplayRole) for c in range(5, self.columnCount())]

    @property
    def allCollections(self):
        return [self.headerData(c, QtCore.Qt.Horizontal, QtCore.Qt.DisplayRole) for c in range(2, self.columnCount())]

    @property
    def factoryPresets(self):
        return [self.headerData(c, QtCore.Qt.Horizontal, QtCore.Qt.DisplayRole) for c in range(2, 5)]


