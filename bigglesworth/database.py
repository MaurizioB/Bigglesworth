# *-* encoding: utf-8 *-*

import string
import uuid
import json
import re
#from threading import Lock

from Qt import QtCore, QtSql
QtCore.pyqtSignal = QtCore.Signal

from bigglesworth.utils import Enum, localPath, getName, getSizeStr, elapsedFrom
from bigglesworth.parameters import Parameters
from bigglesworth.libs import midifile
from bigglesworth.const import factoryPresets, NameColumn, chr2ord
from bigglesworth.library import CollectionModel, LibraryModel
from bigglesworth.backup import BackUp

renameRegExp = re.compile(r'^(?=.{16}$)(?P<name>.*)~(?P<count>[1-9][0-9]{0,2}){0,1} *$')
_parameterList = []
soundsColumns = []
soundsDef = '('
for p in Parameters.parameterData:
    _parameterList.append(p.attr)
    soundsColumns.append(p.attr)
    soundsDef += '{} int, '.format(p.attr)

templateDef = soundsDef + 'name varchar, groups varchar)'
soundsColumns.append('uid')
soundsDef += 'uid varchar primary key)'
referenceColumns = ['uid', 'tags', 'blofeld_fact_201200', 'blofeld_fact_200801', 'blofeld_fact_200802', 'blofeld']
referenceDef = '(uid varchar primary key, tags varchar, blofeld_fact_201200 int, blofeld_fact_200801 int, blofeld_fact_200802 int, blofeld int)'


class BlofeldDB(QtCore.QObject):

    ReadError, WriteError, InvalidError, DatabaseFormatError, TableFormatError, QueryError = Enum(6)
    SoundsEmpty, ReferenceEmpty = Enum(32, 64)

    backupStarted = QtCore.pyqtSignal()
    backupStatusChanged = QtCore.pyqtSignal(int)
    backupFinished = QtCore.pyqtSignal()
    backupError = QtCore.pyqtSignal(str)

    def __init__(self, main):
        QtCore.QObject.__init__(self)
#        self.sql = QtSql.QSqlDatabase.addDatabase('QSQLITE')
        print('Available SQL drivers for PyQt4:', QtSql.QSqlDatabase.drivers())
        self.sql = QtSql.QSqlDatabase.addDatabase('QSQLITE')
#        self.lock = Lock()
        self.main = main
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

    def initialize(self, path):
        self.path = path
        self.backup.setPath(path)
        if not QtCore.QFile.exists(path):
            fileInfo = QtCore.QFileInfo(path)
            if not QtCore.QFile.exists(fileInfo.absolutePath()) and not QtCore.QDir().mkdir(fileInfo.absolutePath()):
                self.lastError = self.WriteError
                return False
        elif not QtCore.QFileInfo(path).isWritable():
            self.lastError = self.WriteError
            return False

        self.sql.setDatabaseName(self.path)
        self.sql.open()
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
        self.query.exec_('DROP TABLE IF EXISTS _oldreference')
        self.query.exec_('SELECT name FROM sqlite_master WHERE type="table"')
        tables = set()
        while self.query.next():
            tables.add(self.query.value(0))
        defaultSet = set(('sounds', 'reference', 'ascii', 'tags', 'fake_reference', 'templates'))
        if tables and (tables | defaultSet) ^ defaultSet:
            self.lastError = self.DatabaseFormatError
            if not deepCheck:
                return False

        self.query.exec_('PRAGMA table_info(sounds)')
        createBit = 0
        if not self.query.next():
            self.query.exec_('CREATE TABLE sounds ' + soundsDef)
            createBit |= self.SoundsEmpty
        else:
            self.query.seek(-1)
            columns = []
            while self.query.next():
                columns.append(self.query.value(1))
            if columns != soundsColumns:
                self.lastError = self.TableFormatError
                return False

        self.query.exec_('PRAGMA table_info(reference)')
        if not self.query.next():
            self.query.exec_('CREATE TABLE reference ' + referenceDef)
            createBit |= self.ReferenceEmpty
        else:
            self.query.seek(-1)
            columns = []
            while self.query.next():
                columns.append(self.query.value(1).lower())
            if columns[:len(referenceColumns)] != referenceColumns:
                self.lastError = self.TableFormatError
                return False

        self.query.exec_('PRAGMA table_info(templates)')
        if not self.query.next():
            self.query.exec_('CREATE TABLE templates ' + templateDef)

        self.query.exec_('PRAGMA table_info(ascii)')
        if not self.query.next() or not all((self.query.exec_('SELECT Count(rowid) from ascii'), self.query.first(), self.query.value(0))):
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

        self.query.exec_('PRAGMA table_info(tags)')
        if not self.query.next():
            self.query.exec_('CREATE TABLE tags (tag varchar primary key, bgColor int, fgColor int)')

        self.query.exec_('PRAGMA table_info(fake_reference)')
        if not self.query.next():
            self.query.exec_('CREATE TABLE fake_reference (id int primary key)')
            fake = 'INSERT INTO fake_reference (id) VALUES'
            for f in range(1024):
                fake += '({}),'.format(f)
            res = self.query.exec_(fake[:-1] + ';')
            if not res:
                print(self.query.lastError().databaseText())

        if createBit:
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
            if createBit:
                self.lastError = createBit
                return False
        return True

    def initializeFactory(self, createBit):
        soundCreate = createBit & self.SoundsEmpty
        refCreate = createBit & self.ReferenceEmpty
        if soundCreate and not refCreate:
            raise BaseException('Database reference mismatch!!!')

        self.query.exec_('PRAGMA journal_mode=OFF')
        soundsPre = 'INSERT INTO sounds('
        soundsPost = 'VALUES('
        for p in soundsColumns[:-1]:
            soundsPre += p + ', '
            soundsPost += ':{}, '.format(p)
        soundsPrepare = soundsPre + 'uid) ' + soundsPost + ':uid)'
        for preset in factoryPresets:
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
                    res = self.query.exec_()
                    if not res:
                        print(self.query.lastError().driverText())
                        print(self.query.lastError().databaseText())
                        print('break at', i)
                        break
                    self.query.prepare('INSERT INTO reference(uid, tags, {}) VALUES(:uid, :tags, :location)'.format(preset))
                    self.query.bindValue(':uid', uid)
                    self.query.bindValue(':tags', json.dumps([]))
                    self.query.bindValue(':location', (data[0] << 7) + data[1])
                    res = self.query.exec_()
                    if not res:
                        print(self.query.lastError().driverText())
                        print(self.query.lastError().databaseText())
                        print('break at', i)
                        break

                    if data[1] == 0:
                        print('starting bank {}'.format(string.ascii_uppercase[data[0]]))
        self.query.exec_('PRAGMA journal_mode=DELETE')

    def getTemplatesByName(self, name=None):
        templates = {}
        queryStr = 'SELECT * FROM templates'
        if name:
            queryStr += ' WHERE name="{}"'.format(name)
        if not self.query.exec_(queryStr):
            print(self.query.lastError().databaseText())
            return templates
        while self.query.next():
            values = [self.query.value(v) for v in range(383)]
            templates[self.query.value(383)] = json.loads(self.query.value(384)), values
        return templates

    def getTemplatesByGroups(self, groups):
        templates = {}
        if not self.query.exec_('SELECT * FROM templates WHERE groups IS NOT NULL'):
            print(self.query.lastError().databaseText())
            return templates
        while self.query.next():
            templateGroups = json.loads(self.query.value(384))
            if not set(groups) & set(templateGroups):
                continue
            params = []
            for id, attr in enumerate(_parameterList):
                if attr.startswith('reserved'):
                    continue
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
            print(self.query.lastError().databaseText())
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
            print(self.query.lastError().driverText())
            print(self.query.lastError().databaseText())
            return False
        return True

    def updateTemplates(self, templates, deleted=None):
        if deleted and not self.query.exec_('DELETE FROM templates WHERE ' + ' OR '.join(['name="{}"'.format(d) for d in deleted])):
            print('error deleting templates')
            print(self.query.lastError().driverText())
            print(self.query.lastError().databaseText())
            return False
        tempPre = 'INSERT INTO templates('
        tempPost = 'VALUES('
        updateStr = 'UPDATE templates SET '
        for p in _parameterList:
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
            for p, value in zip(_parameterList, valueList):
                self.query.bindValue(':' + p, value)
            self.query.bindValue(':name', name)
            self.query.bindValue(':groups', json.dumps(groups))
            if not self.query.exec_():
                print('error deleting templates')
                print(self.query.lastError().driverText())
                print(self.query.lastError().databaseText())
                self.sql.rollback()
                return False
        self.sql.commit()
        return True

    def addBatchRawSoundData(self, dataList, collection=None):
        self.sql.transaction()
        soundsPre = 'INSERT INTO sounds('
        soundsPost = 'VALUES('
        for p in soundsColumns[:-1]:
            soundsPre += p + ', '
            soundsPost += ':{}, '.format(p)
        soundsPrepare = soundsPre + 'uid) ' + soundsPost + ':uid)'
        noTags = json.dumps([])

        if collection:
            refPrepare = 'INSERT INTO reference(uid, tags, "{}") VALUES(:uid, :tags, :location)'.format(collection)
        else:
            refPrepare = 'INSERT INTO reference(uid, tags) VALUES(:uid, :tags)'
        for index, data in dataList.items():
            self.query.prepare(soundsPrepare)
            for p, d in zip(Parameters.parameterData, data):
                self.query.bindValue(':' + p.attr, p.range.sanitize(int(d)))
            uid = str(uuid.uuid4())
            self.query.bindValue(':uid', uid)
            if not self.query.exec_():
                print('error importing sound to library')
                print(self.query.lastError().driverText())
                print(self.query.lastError().databaseText())
                break
            self.query.prepare(refPrepare)
            if collection:
                self.query.bindValue(':location', index)
            self.query.bindValue(':uid', uid)
            self.query.bindValue(':tags', noTags)
            if not self.query.exec_():
                print('error adding imported sound to library/collection')
                print(self.query.lastError().driverText())
                print(self.query.lastError().databaseText())
                break
        else:
            self.sql.commit()
            self.libraryModel.setQuery()
            while self.libraryModel.canFetchMore():
                self.libraryModel.fetchMore()
            self.libraryModel.updated.emit()
            if collection:
                self.collections[collection].query().exec_()
                self.collections[collection].updated.emit()
            return True
        print('uhm...')
        self.sql.rollback()
        return False

    def addRawSoundData(self, data, collection=None, index=None, targetUid=None):
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
        res = self.query.exec_()
        if not res:
            print('error importing sound to library')
            print(self.query.lastError().driverText())
            print(self.query.lastError().databaseText())
            return False
        print('targetUid', targetUid)
        if not isinstance(targetUid, (str, unicode)):
            print('son quih')
            if collection:
                self.query.prepare('INSERT INTO reference(uid, tags, "{}") VALUES(:uid, :tags, :location)'.format(collection))
                self.query.bindValue(':location', index)
            else:
                self.query.prepare('INSERT INTO reference(uid, tags) VALUES(:uid, :tags)')
            self.query.bindValue(':uid', uid)
            self.query.bindValue(':tags', json.dumps([]))
            res = self.query.exec_()
            if not res:
                print('error adding imported sound to collection')
                print(self.query.lastError().driverText())
                print(self.query.lastError().databaseText())
                return False
            self.collections[collection].query().exec_()
            self.collections[collection].updated.emit()

        self.referenceModel.refresh()
        self.libraryModel.setQuery()
        while self.libraryModel.canFetchMore():
            self.libraryModel.fetchMore()
        self.libraryModel.updated.emit()
        print('success!!!')
        return uid

    def getSoundDataFromUid(self, uid):
#        print(uid)
        if not self.query.exec_('SELECT {} FROM sounds WHERE uid = "{}"'.format(','.join(Parameters.parameterList), uid)):
            print(self.query.lastError().databaseText())
            return False
        self.query.first()
        if not isinstance(self.query.value(0), (int, long)):
            return False
        return map(int, [self.query.value(v) for v in range(383)])

    def getIndexesForCollection(self, collection):
        if not self.query.exec_('SELECT "{}" FROM reference'.format(collection)):
            print(self.query.lastError().databaseText())
            return False
        indexes = []
        while self.query.next():
            value = self.query.value(0)
            if isinstance(value, (int, long)):
                indexes.append(value)
        if len(set(indexes)) != len(indexes):
            print('WARNING: duplicate indexes in collection', collection)
        return sorted(set(indexes))

    def getUidFromCollection(self, bank, prog, collection):
        index = (bank << 7) + prog
        if not self.query.exec_('SELECT uid FROM reference WHERE "{}" = {}'.format(collection, index)):
            print(self.query.lastError().databaseText())
            return False
        self.query.first()
        return self.query.value(0)

    def getNameFromUid(self, uid):
        res = self.query.exec_(
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
            'WHERE sounds.uid = reference.uid AND reference.uid = "{}"'.format(uid))
        if not res:
            print(self.query.lastError().databaseText())
            return
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
        res = self.query.exec_('SELECT * FROM reference WHERE uid == "{}"'.format(uid))
        if not res:
            print(self.query.lastError().databaseText())
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
            ' OR '.join('(reference.uid == "{}")'.format(uid) for uid in uidList) + ')')
        if not res:
            print(self.query.lastError().databaseText())
            return
        nameList = []
        while self.query.next():
            nameList.append(self.query.value(0))
        return nameList

    def updateSoundValue(self, uid, paramId, value):
        if not self.query.exec_('UPDATE sounds SET {attr} = {value} WHERE uid = "{uid}"'.format(
            attr=Parameters.parameterData[paramId].attr, 
            value=int(value), 
            uid=uid)):
                print(self.query.lastError().databaseText())
                return False
        return True

    def updateSound(self, uid, parameters):
        fieldList = ', '.join(['{}=:{}'.format(p, p) for p in _parameterList])
        self.query.prepare('UPDATE sounds SET {} WHERE uid="{}"'.format(fieldList, uid))
        for p, value in zip(_parameterList, parameters):
            self.query.bindValue(':{}'.format(p), int(value))
        if not self.query.exec_():
            print(self.query.lastError().databaseText())
            return False
        return True

    def checkDuplicates(self, uidList, collection):
        where = ' OR '.join('reference.uid = "{}"'.format(uid) for uid in uidList)
        res = self.query.exec_('SELECT reference.uid FROM reference WHERE reference.{} IS NOT NULL AND ({})'.format(collection, where))
        if not res:
            print(self.query.lastError().databaseText())
        else:
            duplicates = []
            while self.query.next():
                duplicates.append(self.query.value(0))
            return duplicates

    def createCollection(self, name, source=None):
        res = self.query.exec_(u'ALTER TABLE reference ADD COLUMN "{}" int'.format(name))
        if not res:
            return False
        if source:
            res = self.query.exec_(u'UPDATE reference SET "{}" = "{}"'.format(name, source))
            if not res:
                return False
        return True

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
        fieldList = [':{}'.format(p) for p in _parameterList]
        self.query.prepare('SELECT {}, reference.tags FROM sounds,reference WHERE sounds.uid=:uid AND reference.uid=:uid2'.format(', '.join('sounds.' + p for p in _parameterList)))
        self.query.bindValue(':uid', uid)
        self.query.bindValue(':uid2', uid)
        res = self.query.exec_()
        if not res:
            print(self.query.lastError().databaseText())
            return False
        self.query.first()
        values = [self.query.value(i) for i in range(383)]
        tags = self.query.value(383)
        if rename:
            newNameChrs = self.getAlternateNameChrs(uid, getName(values[363:379]))
            for i, chr in enumerate(newNameChrs, 363):
                values[i] = chr2ord[chr]
        self.query.prepare('INSERT INTO sounds({}, uid) VALUES({}, :uid)'.format(', '.join(_parameterList), ', '.join(fieldList)))
        for p, value in zip(fieldList, values):
            self.query.bindValue(p, value)
        newUid = str(uuid.uuid4())
        self.query.bindValue(':uid', newUid)
        res = self.query.exec_()
        if not res:
            print(self.query.lastError().databaseText())
            return False
        if collection:
            self.query.prepare('INSERT INTO reference(uid, tags, "{}") VALUES(:uid, :tags, :target)'.format(collection))
            self.query.bindValue(':uid', newUid)
            self.query.bindValue(':tags', tags)
            self.query.bindValue(':target', target)
            res = self.query.exec_()
            if not res:
                print(self.query.lastError().databaseText())
                return False
        else:
            self.query.prepare('INSERT INTO reference(uid, tags) VALUES(:uid, :tags)')
            self.query.bindValue(':uid', newUid)
            self.query.bindValue(':tags', tags)
            res = self.query.exec_()
            if not res:
                print(self.query.lastError().databaseText())
                return False
        self.libraryModel.setQuery()
        while self.libraryModel.canFetchMore():
            self.libraryModel.fetchMore()
        self.libraryModel.updated.emit()
        return newUid

    def addSoundsToCollection(self, uidMap, collection):
        queryStr = 'UPDATE reference SET "{}" = NULL WHERE '.format(collection)
        queryStr += ' OR '.join('"{}" = {}'.format(collection, target) for _, target in uidMap)
        self.sql.transaction()
        self.query.exec_(queryStr)
        for uid, target in uidMap:
            #preset sounds have to be duplicated before adding to collection
            if not self.query.exec_('SELECT blofeld_fact_200801,blofeld_fact_200802,blofeld_fact_201200 FROM reference WHERE uid = "{}"'.format(uid)):
                    print(self.query.lastError().databaseText())
                    self.sql.rollback()
                    return False
            self.query.first()
            if isinstance(self.query.value(0), (int, long)) or \
                isinstance(self.query.value(1), (int, long)) or \
                isinstance(self.query.value(2), (int, long)):
                    uid = self.duplicateSound(uid, rename=False)
            if not self.query.exec_('UPDATE reference SET "{}" = {} WHERE uid = "{}"'.format(
                collection, 
                target, 
                uid
                )):
                    print(self.query.lastError().databaseText())
                    self.sql.rollback()
                    return False
        self.sql.commit()
        self.collections[collection].query().exec_()
        self.collections[collection].updated.emit()
        return True

    def removeSounds(self, uidList, collection):
        where = ' OR '.join('uid = "{}"'.format(uid) for uid in uidList)
        res = self.query.exec_('UPDATE reference SET "{}" = NULL WHERE {}'.format(collection, where))
        if not res:
            print(self.query.lastError().databaseText())
            return False
        self.collections[collection].query().exec_()
        self.collections[collection].updated.emit()
        return True

    def deleteSounds(self, uidList):
        where = ' OR '.join('uid = "{}"'.format(uid) for uid in uidList)
        collections = self.referenceModel.collections
        reference = set()
        res = self.query.exec_('SELECT {} FROM reference WHERE {}'.format(', '.join('"{}"'.format(c) for c in collections), where))
        if not res:
            print(self.query.lastError().databaseText())
            return False
        while self.query.next():
            for colId, collection in enumerate(collections):
                try:
                    int(self.query.value(colId))
                    reference.add(collection)
                except:
                    pass
        res = self.query.exec_('DELETE FROM reference WHERE {}'.format(where))
        if not res:
            print(self.query.lastError().databaseText())
        res = self.query.exec_('DELETE FROM sounds WHERE {}'.format(where))
        if not res:
            print(self.query.lastError().databaseText())
        for collection in reference:
            self.collections[collection].updated.emit()
        self.libraryModel.setQuery()
        while self.libraryModel.canFetchMore():
            self.libraryModel.fetchMore()
        self.libraryModel.updated.emit()

    def duplicateAndInsert(self, uidList, collection, target):
        totRows = len(uidList)
        self.query.exec_('SELECT "{}" as location, uid FROM reference WHERE location IS NOT NULL'.format(collection))
        map = {l:None for l in range(1024)}
        while self.query.next():
            map[self.query.value(0)] = self.query.value(1)
        last = pos = target
        found = []
        delta = 1
        while True:
            while map[pos] is not None:
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
        newUidList = [self.duplicateSound(uid) for uid in uidList]
        first = min(found + [target])
        last = max(found + [target - 1])
        oldUidList = {k:v for k, v in map.items() if first <= k <= last and v is not None}
        if target <= first:
            for pos, uid in enumerate(newUidList, target):
                self.query.exec_('UPDATE reference SET "{}" = {} WHERE uid = "{}"'.format(collection, pos, uid))
            for p in sorted(oldUidList.keys()):
                pos += 1
                self.query.exec_('UPDATE reference SET "{}" = {} WHERE uid = "{}"'.format(collection, pos, oldUidList[p]))
        else:
            pos = first
            for p in sorted(oldUidList.keys()):
                self.query.exec_('UPDATE reference SET "{}" = {} WHERE uid = "{}"'.format(collection, pos, oldUidList[p]))
                pos += 1
            for pos, uid in enumerate(newUidList, pos):
                self.query.exec_('UPDATE reference SET "{}" = {} WHERE uid = "{}"'.format(collection, pos, uid))
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
        self.query.exec_('UPDATE reference SET "{c}" = NULL WHERE "{c}" BETWEEN {s} AND {e}'.format(
            c=collection, s=first, e=last))
        uidMap = []
        for uid, target in zip(uidList, targetRows):
            if uid in existing:
                uidMap.append((uid, target))
            else:
                newUid = self.duplicateSound(uid)
                uidMap.append((newUid, target))
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

            for l, uid in finalLayout.items():
                res = self.query.exec_('UPDATE reference SET "{c}" = {l} WHERE uid = "{u}"'.format(
                    c=collection, 
                    l=l, 
                    u=uid, 
                    ))
                if not res:
                    print(self.query.lastError().databaseText())
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
        for l, uid in finalLayout.items():
            if not uid:
                continue
            res = self.query.exec_('UPDATE reference SET "{c}" = {l} WHERE uid = "{u}"'.format(
                c=collection, 
                l=l, 
                u=uid, 
                ))
            if not res:
                print(self.query.lastError().databaseText())
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
    def __init__(self):
        QtSql.QSqlTableModel.__init__(self)
        self.setTable('reference')
        self.refresh()

    def refresh(self):
        self.select()
        while self.canFetchMore():
            self.fetchMore()

    @property
    def collections(self):
        return [self.headerData(c, QtCore.Qt.Horizontal, QtCore.Qt.DisplayRole) for c in range(5, self.columnCount())]

    @property
    def allCollections(self):
        return [self.headerData(c, QtCore.Qt.Horizontal, QtCore.Qt.DisplayRole) for c in range(2, self.columnCount())]

