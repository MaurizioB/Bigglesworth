# *-* encoding: utf-8 *-*

import string, json

from Qt import QtCore, QtWidgets, QtSql

#from bigglesworth.widgets.librarytableview import LibraryTableView
from bigglesworth.const import (chr2ord, CatRole, HoverRole, TagsRole, 
    UidColumn, LocationColumn, NameColumn, CatColumn, TagsColumn, LogCritical, 
    headerLabels, factoryPresetsNames, factoryPresetsNamesDict)


class BaseLibraryModel(QtSql.QSqlQueryModel):
    defaultItemFlags = QtCore.Qt.ItemIsEnabled|QtCore.Qt.ItemIsEditable|QtCore.Qt.ItemIsSelectable|QtCore.Qt.ItemIsDragEnabled|QtCore.Qt.ItemIsDropEnabled
    itemFlags = {
        NameColumn: defaultItemFlags, 
        CatColumn: defaultItemFlags, 
        TagsColumn: QtCore.Qt.ItemIsEnabled|QtCore.Qt.ItemIsSelectable|QtCore.Qt.ItemIsDragEnabled|QtCore.Qt.ItemIsDropEnabled, 
        }

    updated = QtCore.pyqtSignal()
    soundNameChanged = QtCore.pyqtSignal(str, str)
    scheduledQueryUpdateSet = QtCore.pyqtSignal()

    def __init__(self):
        QtSql.QSqlQueryModel.__init__(self)
        self.updateQuery = QtSql.QSqlQuery()
        self.hoverDict = {}
        self.scheduledQueryUpdate = False
        self.logger = None

    def dbErrorLog(self, message, extMessage='', query=None):
        print('Db error:', message)
        if not query:
            query = self.query()
        dbText = query.lastError().databaseText()
        driverText = query.lastError().driverText()
        print(dbText)
        print(driverText)
        if self.logger:
            text = '{}\n{}'.format(dbText, driverText)
            if extMessage:
                text = '{}\n{}'.format(extMessage, text)
            self.logger.append(LogCritical, message, text)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if role == HoverRole:
            return self.hoverDict.get(index, QtCore.QPoint())
        return QtSql.QSqlQueryModel.data(self, index, role)

    def setData(self, index, value, role):
        if role == CatRole:
            uid = index.sibling(index.row(), 0).data()
            if not self.updateQuery.exec_('UPDATE sounds SET category = {} WHERE uid="{}"'.format(value, uid)):
                self.dbErrorLog('Error updating tags', (uid, value), self.updateQuery)
            if not self.query().exec_():
                self.dbErrorLog('Error setting category', (uid, value))
            self.updated.emit()
        elif role == HoverRole:
            self.hoverDict[index] = value
            #emit dataChanged to ensure that the view catches the update
            self.dataChanged.emit(index, index)
        elif role == QtCore.Qt.EditRole and index.column() == NameColumn:
            value = value.ljust(16, ' ')[:16]
            uid = index.sibling(index.row(), 0).data()
            letters = [chr2ord.get(l, 32) for l in value]
            updateStr = 'UPDATE sounds SET nameChar00 = {}'.format(letters[0])
            for i, l in enumerate(letters[1:], 1):
                updateStr += ', nameChar{:02} = {}'.format(i, l)
            updateStr += ' WHERE uid = "{}"'.format(uid)
            if not self.updateQuery.exec_(updateStr):
                self.dbErrorLog('Error updating tags', (uid, value), self.updateQuery)
            if not self.query().exec_():
                self.dbErrorLog('Error refreshing model', uid)
            self.soundNameChanged.emit(uid, value)
            self.updated.emit()
        elif role == TagsRole:
            uid = index.sibling(index.row(), 0).data()
            self.updateQuery.prepare('UPDATE reference SET tags = :tags WHERE uid = :uid')
            self.updateQuery.bindValue(':tags', value)
            self.updateQuery.bindValue(':uid', uid)
            if not self.updateQuery.exec_():
                self.dbErrorLog('Error updating tags', (uid, value), self.updateQuery)
            if not self.query().exec_():
                self.dbErrorLog('Error refreshing model', uid, value)
            self.updated.emit()
        return True

    def flags(self, index):
#        print(index.flags() & QtCore.Qt.ItemIsEditable)
        return self.itemFlags.get(index.column(), self.defaultItemFlags)

    def scheduleQueryUpdate(self):
        self.scheduledQueryUpdate = True
        self.scheduledQueryUpdateSet.emit()

    def queryUpdate(self):
        if self.scheduledQueryUpdate:
            self.query().exec_()
            self.scheduledQueryUpdate = False

    def headerData(self, section, orientation, role):
        if orientation == QtCore.Qt.Vertical and role == QtCore.Qt.DisplayRole and isinstance(self, CollectionModel):
            bank = section >> 7
            prog = (section & 127) + 1
            return '{}{:03}'.format(string.ascii_uppercase[bank], prog)
        #this is necessary because in some cases the headers are set to "0" once results are filtered
        elif orientation == QtCore.Qt.Horizontal:
            if role == QtCore.Qt.DisplayRole:
                return headerLabels.get(section)
#            elif role == QtCore.Qt.ToolTipRole:
#                return ''
        return QtSql.QSqlQueryModel.headerData(self, section, orientation, role)


class LibraryModel(BaseLibraryModel):
    def __init__(self, database):
        BaseLibraryModel.__init__(self)
        self.database = database
        self.collection = None
        self.setQuery()
        self.disabledFont = QtWidgets.QApplication.font()
        self.disabledFont.setItalic(True)
        self.usedFont = QtWidgets.QApplication.font()
        self.usedFont.setBold(True)

    def setQuery(self):
        colBits = []
        colCases = []
        collections = self.database.referenceModel.collections
        self.collections = {(1 << b):n for b, n in enumerate(factoryPresetsNames + collections)}

        for bit, collection in enumerate(collections, 3):
            colBits.append('("{}" << {})'.format(collection, bit))
            colCases.append('(CASE WHEN reference."{}" IS NOT NULL THEN 1 ELSE 0 END) "{}"'.format(collection, collection))

        queryStr = 'SELECT uid, blofeld_fact_200801 + (blofeld_fact_200802 << 1) + ' \
        '(blofeld_fact_201200 << 2) {colBits} as location, ' \
        'Name, Category, Tags FROM (SELECT sounds.uid AS uid, ' \
        'c00.char||c01.char||c02.char||c03.char||c04.char||c05.char||c06.char||c07.char||' \
        'c08.char||c09.char||c10.char||c11.char||c12.char||c13.char||c14.char||c15.char AS Name, ' \
        'sounds.category AS Category,reference.tags as Tags, reference.uid as rUid, ' \
        '(CASE WHEN reference.blofeld_fact_200801 IS NOT NULL THEN 1 ELSE 0 END) blofeld_fact_200801, ' \
        '(CASE WHEN reference.blofeld_fact_200802 IS NOT NULL THEN 1 ELSE 0 END) blofeld_fact_200802, ' \
        '(CASE WHEN reference.blofeld_fact_201200 IS NOT NULL THEN 1 ELSE 0 END) blofeld_fact_201200, ' \
        '(CASE WHEN reference.blofeld IS NOT NULL THEN 1 ELSE 0 END) blofeld{colCases} ' \
        'FROM sounds,reference ' \
        'JOIN ascii as c00 on sounds.nameChar00 = c00.id ' \
        'JOIN ascii as c01 on sounds.nameChar01 = c01.id JOIN ascii as c02 on sounds.nameChar02 = c02.id ' \
        'JOIN ascii as c03 on sounds.nameChar03 = c03.id JOIN ascii as c04 on sounds.nameChar04 = c04.id ' \
        'JOIN ascii as c05 on sounds.nameChar05 = c05.id JOIN ascii as c06 on sounds.nameChar06 = c06.id ' \
        'JOIN ascii as c07 on sounds.nameChar07 = c07.id JOIN ascii as c08 on sounds.nameChar08 = c08.id ' \
        'JOIN ascii as c09 on sounds.nameChar09 = c09.id JOIN ascii as c10 on sounds.nameChar10 = c10.id ' \
        'JOIN ascii as c11 on sounds.nameChar11 = c11.id JOIN ascii as c12 on sounds.nameChar12 = c12.id ' \
        'JOIN ascii as c13 on sounds.nameChar13 = c13.id JOIN ascii as c14 on sounds.nameChar14 = c14.id ' \
        'JOIN ascii as c15 on sounds.nameChar15 = c15.id )' \
        'WHERE (uid = rUid)'.format(
            colBits=' + ' + ' + '.join(colBits), 
            colCases=', ' + ', '.join(colCases), 
            )
        BaseLibraryModel.setQuery(self, queryStr)
#        'CASE WHEN COALESCE(reference.blofeld_fact_200801, reference.blofeld_fact_200802, reference.blofeld_fact_201200) IS NOT NULL THEN 1 ELSE 0 END AS Factory ' \
#        queryPre = 'SELECT uid, blo0801 + (blo0802 << 1) + (blo1200 << 2) AS location, c00.char'
#        nameCharStr = ' JOIN ascii as c00 on sounds.nameChar00 = c00.id'
#        for c in range(1, 16):
#            queryPre += '||c{:02}.char'.format(c)
#            nameCharStr += ' JOIN ascii as c{c:02} on sounds.nameChar{c:02} = c{c:02}.id'.format(c=c)
#        self.setQuery(queryPre + \
#            ' AS Name,sounds.category AS Category,reference.tags as Tags FROM ' \
#            '(SELECT reference.uid as uid, '
#            '(CASE WHEN reference.blofeld_fact_200801 IS NOT NULL THEN 1 ELSE 0 END) blo0801, ' \
#            '(CASE WHEN reference.blofeld_fact_200802 IS NOT NULL THEN 1 ELSE 0 END) blo0802, ' \
#            '(CASE WHEN reference.blofeld_fact_201200 IS NOT NULL THEN 1 ELSE 0 END) blo1200 ' \
#            'FROM sounds,reference' + nameCharStr + ''\
##            'CASE WHEN COALESCE(reference.blofeld_fact_200801, reference.blofeld_fact_200802, reference.blofeld_fact_201200) ' \
##            'IS NOT NULL THEN 1 ELSE 0 END AS Factory FROM sounds,reference' + nameCharStr + \
#            ' WHERE (sounds.uid = reference.uid)')
#        print(self.query().lastError().databaseText())


    def size(self):
        return self.rowCount()

    def data(self, index, role):
        if role == QtCore.Qt.ToolTipRole:
            nameIndex = index.sibling(index.row(), NameColumn)
            name = nameIndex.data().strip()
            location = index.sibling(index.row(), LocationColumn).data()
            toolTip = u'<b>{}</b>'.format(name)
            collectionsText = ''
            for bit, collection in enumerate(self.database.referenceModel.allCollections):
                if location & (1 << bit):
                    soundIndex = self.database.getIndexForUid(index.sibling(index.row(), UidColumn).data(), collection)
                    bank = soundIndex >> 7
                    prog = (soundIndex & 127) + 1
                    collectionsText += u'<li>{}: <b>{}{:03}</b></li>'.format(
                        factoryPresetsNamesDict.get(collection, collection), 
                        string.ascii_uppercase[bank], prog)
            if collectionsText:
                toolTip += u'<br/><br/>Collections:<br/>' \
                    '<ul style="margin-top: 0px; margin-left: 0px; margin-right:10px; -qt-list-indent: 0;">' + \
                    collectionsText + '</ul>'
            return toolTip
        if role == QtCore.Qt.StatusTipRole:
            nameIndex = index.sibling(index.row(), NameColumn)
            name = nameIndex.data().strip()
            location = index.sibling(index.row(), LocationColumn).data()
            if not nameIndex.flags() & QtCore.Qt.ItemIsEditable:
                return u'"{}" appears in the "{}" factory preset. Editing requires saving it as another sound slot.'.format(
                    name, 
                    self.collections[location & 7], 
#                    index.sibling(index.row(), UidColumn).data()
                    )
            collections = []
            for k, v in self.collections.items():
                if location & k:
                    collections.append(u'"{}"'.format(v))
            if not collections:
                return u'"{}" is not used in any collection.'.format(name)
            return u'"{}" appears in: {}'.format(name, ', '.join(collections))
        if role == QtCore.Qt.FontRole and index.column() == NameColumn:
            nameIndex = index.sibling(index.row(), NameColumn)
            if not nameIndex.flags() & QtCore.Qt.ItemIsEditable:
                return self.disabledFont
            if index.sibling(index.row(), LocationColumn).data():
                return self.usedFont
        return BaseLibraryModel.data(self, index, role)

    def flags(self, index):
        flags = self.itemFlags.get(index.column(), self.defaultItemFlags)
        if index.column() in (NameColumn, CatColumn) and index.sibling(index.row(), LocationColumn).data() & 7:
            flags = (flags | QtCore.Qt.ItemIsEditable) ^ QtCore.Qt.ItemIsEditable
        return flags


class CollectionModel(BaseLibraryModel):
    def __init__(self, collection=None):
        BaseLibraryModel.__init__(self)
        self.collection = collection
        self.database = QtWidgets.QApplication.instance().database
        #Comments are for old implementation that created "fake" results when collection has empty slots
#        queryPre = 'SELECT sounds.uid, reference.{} AS location, c00.char'.format(collection)
        queryPre = 'SELECT result.uid, result.location, result.Name, result.Category, result.Tags FROM fake_reference LEFT JOIN (SELECT sounds.uid as uid, reference."{}" as location, c00.char'.format(collection)
        nameCharStr = ' JOIN ascii as c00 on sounds.nameChar00 = c00.id'
        for c in range(1, 16):
            queryPre += '||c{:02}.char'.format(c)
            nameCharStr += ' JOIN ascii as c{c:02} on sounds.nameChar{c:02} = c{c:02}.id'.format(c=c)
#        self.setQuery(queryPre + \
#            ' AS Name,sounds.category AS Category,reference.tags as Tags FROM sounds,reference' + \
#            nameCharStr + \
#            ' WHERE (location IS NOT NULL) AND (sounds.uid = reference.uid)')
        self.setQuery(queryPre + ' AS Name,sounds.category AS Category,reference.tags as Tags FROM sounds,reference' + nameCharStr + ' WHERE (sounds.uid = reference.uid)) as result ON fake_reference.id = result.location')

    def size(self):
        res = self.updateQuery.exec_('SELECT uid FROM reference WHERE reference."{}" IS NOT NULL'.format(self.collection))
        if res:
            self.updateQuery.last()
            size = self.updateQuery.at() + 1
            self.updateQuery.finish()
            return size
        return 0

    def data(self, index, role):
        if role == QtCore.Qt.DisplayRole:
            if not BaseLibraryModel.data(self, index.sibling(index.row(), 0)) and index.column() == NameColumn:
                return 'Empty slot'
        elif role == QtCore.Qt.ToolTipRole:
            if not BaseLibraryModel.data(self, index.sibling(index.row(), 0)):
                return
            nameIndex = index.sibling(index.row(), NameColumn)
            name = nameIndex.data().strip()
            uid = index.sibling(index.row(), UidColumn).data()
            collections = self.database.getCollectionsFromUid(uid)
            if len(collections) > 1:
                toolTip = u'{} also appears in the following collections:<br/>'.format(name) + \
                    u'<ul style="margin-top: 0px; margin-left: 0px; margin-right:10px; -qt-list-indent: 0;">'
                for collectionId in collections:
                    collection = self.database.referenceModel.allCollections[collectionId]
                    if collection == self.collection:
                        continue
                    soundIndex = self.database.getIndexForUid(uid, collection)
                    bank = soundIndex >> 7
                    prog = (soundIndex & 127) + 1
                    toolTip += u'<li>{}: <b>{}{:03}</b></li>'.format(
                        factoryPresetsNamesDict.get(collection, collection), 
                        string.ascii_uppercase[bank], prog)
                return toolTip + u'</ul>'
        elif role == QtCore.Qt.StatusTipRole:
            if not BaseLibraryModel.data(self, index.sibling(index.row(), 0)):
                return 'Slot empty; drop a sound to it or right click to init a new one'
            nameIndex = index.sibling(index.row(), NameColumn)
            name = nameIndex.data().strip()
            uid = index.sibling(index.row(), UidColumn).data()
            collections = self.database.getCollectionsFromUid(uid)
            if len(collections) > 1:
                names = []
                for collectionId in collections:
                    collection = self.database.referenceModel.allCollections[collectionId]
                    if collection != self.collection:
                        names.append(u'"{}"'.format(collection))
                return u'"{}" also appears in: {}'.format(name, ', '.join(names))
#        if not index.sibling(index.row(), 0).data() and index.column() == NameColumn and role == QtCore.Qt.DisplayRole:
#            return 'suca'
#        return 0
#        if not index.sibling(index.row(), 0).data():
#            if role == QtCore.Qt.DisplayRole:
#                if index.column() == NameColumn:
#                    return 'ga'
#                else:
#                    return 0
#            else:
#                return BaseLibraryModel.data(self, index, role)
#        if role == QtCore.Qt.StatusTipRole:
#            return index.sibling(index.row(), UidColumn).data()
        return BaseLibraryModel.data(self, index, role)

    def flags(self, index):
        if not index.sibling(index.row(), 0).data():
            return QtCore.Qt.ItemIsDropEnabled
        else:
            return BaseLibraryModel.flags(self, index)


#class FullLibraryProxy(QtCore.QAbstractProxyModel):
#    def setSourceModel(self, model):
#        QtCore.QAbstractProxyModel.setSourceModel(self, model)
#        model.dataChanged.connect(self.dataChanged.emit)
#
#    def rowCount(self, parent=None):
#        return 256
#
#    def columnCount(self, parent=None):
#        return self.sourceModel().columnCount()
#
#    def index(self, row, column, parent=None):
#        return self.createIndex(row, column)
#
#    def data(self, index, role=QtCore.Qt.DisplayRole):
#        return 0
#        newIndex = self.mapToSource(index)
#        if newIndex.isValid():
#            return self.sourceModel().data(newIndex, role)
#        elif role == QtCore.Qt.DisplayRole and index.column() == NameColumn:
#            return 'Empty slot'
#        return None
#
#    def flags(self, index):
#        return QtCore.Qt.ItemIsEnabled
#        newIndex = self.mapToSource(index)
#        if newIndex.isValid():
#            return self.sourceModel().flags(newIndex)
#        return QtCore.Qt.NoItemFlags
#
#    def mapToSource(self, index):
#        res = self.sourceModel().match(self.sourceModel().index(0, LocationColumn), QtCore.Qt.DisplayRole, index.row(), flags=QtCore.Qt.MatchExactly)
#        if res:
#            return res[0].sibling(res[0].row(), index.column())
#        return QtCore.QModelIndex()
#
#    def parent(self, index):
#        return QtCore.QModelIndex()
#
#    def mapFromSource(self, index):
#        print('b')
#        if index.isValid() and 0 <= index.row() < self.rowCount():
#            return self.index(self.sourceModel().index(index.row(), 1).data(), index.column())
#        return QtCore.QModelIndex()
#
#    def setData(self, index, value, role):
#        newIndex = self.mapToSource(index)
#        if newIndex.isValid():
#            res = self.sourceModel().setData(newIndex, value, role)
#            if role == HoverRole:
#                self.dataChanged.emit(index, index)
#            return res
#        return True


class RecursiveProxy(QtCore.QSortFilterProxyModel):
    def mapFromRootSource(self, row, column=0):
        sourceModel = self.sourceModel()
        if isinstance(sourceModel, QtCore.QSortFilterProxyModel):
            index = sourceModel.mapFromRootSource(row, column)
        else:
            index = sourceModel.index(row, column)
        return self.mapFromSource(index)

    def mapToRootSource(self, index):
        sourceModel = self.sourceModel()
        if isinstance(sourceModel, QtCore.QSortFilterProxyModel):
            return sourceModel.mapToRootSource(self.mapToSource(index))
        return self.mapToSource(index)


class BaseLibraryProxy(RecursiveProxy):
    invalidated = QtCore.pyqtSignal()
    def __init__(self, *args, **kwargs):
        QtCore.QSortFilterProxyModel.__init__(self, *args, **kwargs)
        self.filterAcceptsRow = lambda *args: True

    def invalidateFilter(self):
        QtCore.QSortFilterProxyModel.invalidateFilter(self)
        self.invalidated.emit()

    def setFilter(self, filter):
        self.filter = filter
        if filter == self.__class__.filter:
            self.filterAcceptsRow = lambda *args: True
        else:
            self.filterAcceptsRow = self.customFilter
        self.invalidateFilter()

    def size(self):
        return self.sourceModel().size()


class FactoryProxy(BaseLibraryProxy):
    filter = False

    def customFilter(self, row, parent):
#        if not filter:
#            return True
        index = self.sourceModel().index(row, LocationColumn)
        if index.data() & 7:
            return False
        return True


class MainLibraryProxy(BaseLibraryProxy):
    filter = 0

    def customFilter(self, row, parent):
        index = self.sourceModel().index(row, LocationColumn)
        if self.filter == 1 and index.data() & 7:
            return False
        elif self.filter == 2 and index.data() <= 7:
            return False
        elif self.filter == 3 and index.data():
            return False
        return True


class DockLibraryProxy(BaseLibraryProxy):
    filter = 0

    def customFilter(self, row, parent):
        index = self.sourceModel().index(row, LocationColumn)
#        return index.data() & self.filter
        try:
            return index.data() & self.filter
        except:
            return False
#        if self.filter == 1 and index.data() & 7:
#            return False
#        elif self.filter == 2 and index.data() <= 7:
#            return False
#        elif self.filter == 3 and index.data():
#            return False
#        return True


class BankProxy(BaseLibraryProxy):
    filter = -1

    def customFilter(self, row, parent):
        if self.filter < 0:
            return True
        index = self.sourceModel().index(row, LocationColumn)
        #TODO: verifica se non sia meglio usare un try/except
        if not index.isValid() or not index.flags() & QtCore.Qt.ItemIsEnabled or index.data() is None:
            return False
        if index.data() >> 7 == self.filter:
            return True
        else:
            return False


class CatProxy(BaseLibraryProxy):
    filter = -1

    def customFilter(self, row, parent):
        if self.filter < 0:
            return True
        index = self.sourceModel().index(row, CatColumn)
        if not index.isValid() or index.data() is None:
            return False
        if index.data() == self.filter:
            return True
        else:
            return False


class MultiCatProxy(BaseLibraryProxy):
    filter = []

    def customFilter(self, row, parent):
        if not self.filter:
            return True
        index = self.sourceModel().index(row, CatColumn)
        if not index.isValid() or index.data() is None:
            return False
        if index.data() in self.filter:
            return True
        else:
            return False


class TagsProxy(BaseLibraryProxy):
    filter = []

    def customFilter(self, row, parent):
        if not self.filter:
            return True
        index = self.sourceModel().index(row, TagsColumn)
        if not (index.isValid() and index.data()):
            return False
        tags = set(json.loads(index.data()))
#        if set(self.filter) & set(tags):
        if set(self.filter).issubset(tags):
            return True
        else:
            return False

class CleanLibraryProxy(BaseLibraryProxy):
    filter = True

    def customFilter(self, row, parent):
        if self.filter or self.sourceModel().flags(self.sourceModel().index(row, 0)) & QtCore.Qt.ItemIsEnabled:
            return True
        return False


class NameProxy(RecursiveProxy):
    def size(self):
        return self.sourceModel().size()
