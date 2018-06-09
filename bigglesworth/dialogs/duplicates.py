from string import uppercase
from Qt import QtCore, QtGui, QtWidgets, QtSql

from bigglesworth.utils import loadUi, localPath
from bigglesworth.const import factoryPresetsNamesDict
from bigglesworth.parameters import Parameters

class FindDuplicates(QtWidgets.QDialog):
    def __init__(self, parent):
        QtWidgets.QDialog.__init__(self, parent)
        loadUi(localPath('ui/duplicates.ui'), self)
        self.main = QtWidgets.QApplication.instance()
        self.database = self.main.database
        self.referenceModel = self.database.referenceModel
        self.startBtn.clicked.connect(self.search)
        self.model = QtGui.QStandardItemModel()
        self.tableView.setModel(self.model)
        self.treeView.setModel(self.model)
        self.uid = None

    def search(self):
        self.model.clear()
        if self.uid:
            self.querySingle()
        else:
            self.queryMulti()

#        query = QtSql.QSqlQuery()
#        if not query.exec_(queryStr):
#            print(query.lastError().driverText(), query.lastError().databaseText())
#        ignoreFactory = self.ignoreFactoryChk.isChecked()
#        print(query.lastQuery())
#        minCount = 0 if self.uid else 1
#        while query.next():
#            uidListRaw = query.value(0)
#            print(uidListRaw)
#            if not isinstance(uidListRaw, (str, unicode)):
#                continue
#            if ignoreFactory:
#                uidList = []
#                for uid in uidListRaw.split(','):
#                    if self.database.isUidWritable(uid):
#                        uidList.append(uid)
#            else:
#                uidList = uidListRaw.split(',')
#            if len(uidList) <= minCount:
#                continue
##            print(uidList)
#            firstUid = uidList.pop(0)
#            parent = QtGui.QStandardItem(self.database.getNameFromUid(firstUid))
#            self.model.appendRow(parent)
#            collDict = {}
#            for uid in uidList:
#                name = self.database.getNameFromUid(uid)
#                collections = self.database.getCollectionsFromUid(uid, ignoreFactory)
##                if ignoreFactory and not collections:
##                    continue
#                if len(collections) > 1:
#                    name += ' (*)'
##                soundItem = QtGui.QStandardItem(name)
#                for c in collections:
#                    coll = self.referenceModel.allCollections[c]
#                    collItem = collDict.get(coll)
#                    if not collItem:
#                        collItem = QtGui.QStandardItem(factoryPresetsNamesDict.get(coll, coll))
#                        collDict[coll] = collItem
#                        parent.appendRow(collItem)
#                    collItem.appendRow(QtGui.QStandardItem(name))
#                if not collections:
#                    collItem = collDict.get('No collection')
#                    if not collItem:
#                        collItem = QtGui.QStandardItem('No collection')
#                        collDict['No collection'] = collItem
#                        parent.appendRow(collItem)
#                    collItem.appendRow(QtGui.QStandardItem(name))
#        if self.model.rowCount():
#            for r in range(self.model.rowCount()):
#                self.treeView.expand(self.model.index(r, 0))
#        else:
#            noItems = QtGui.QStandardItem('No duplicates found')
#            noItems.setEnabled(False)
#            self.model.appendRow(noItems)

    def querySingle(self):
        paramList = []
        allCollections = self.referenceModel.allCollections
        ignoreNames = self.ignoreNamesChk.isChecked()
        ignoreCats = self.ignoreCatsChk.isChecked()
        for p, v in zip(Parameters.parameterData, self.database.getSoundDataFromUid(self.uid)):
            if p.attr.startswith('reserved'):
                continue
            elif ignoreNames and p.attr.startswith('nameChar'):
                continue
            elif ignoreCats and p.attr == 'category':
                continue
            paramList.append('sounds.{} = {}'.format(p.attr, v))

        where = ' AND '.join(paramList) + ' AND reference.uid = sounds.uid AND sounds.uid != "{}"'.format(self.uid)
        if self.collectionCombo.currentIndex():
            where += 'AND reference."{}" IS NOT NULL'.format(allCollections[self.collectionCombo.currentIndex() + 2])

        queryStr = 'SELECT GROUP_CONCAT(DISTINCT sounds.uid) FROM sounds,reference WHERE ({})'.format(where)

        query = QtSql.QSqlQuery()
        if not query.exec_(queryStr):
            print(query.lastError().driverText(), query.lastError().databaseText())
        ignoreFactory = self.ignoreFactoryChk.isChecked()
        print(query.lastQuery())

        collDict = {c:0 for c in allCollections}
        collDict.update({None: 0})
        while query.next():
            uidListRaw = query.value(0)
            print(uidListRaw)
            if not isinstance(uidListRaw, (str, unicode)):
                continue
            if ignoreFactory:
                uidList = []
                for uid in uidListRaw.split(','):
                    if self.database.isUidWritable(uid):
                        uidList.append(uid)
            else:
                uidList = uidListRaw.split(',')
            if not uidList:
                continue
#            print(uidList)
            for uid in uidList:
                name = self.database.getNameFromUid(uid)
                collections = self.database.getCollectionsFromUid(uid, ignoreFactory)
                for c in collections:
                    coll = allCollections[c]
                    collDict[coll] += 1
                    index = self.database.getIndexForUid(uid, coll)
                    if index is not None:
                        text = '{b}{p:03}: {n}'.format(
                            b = uppercase[index >> 7], 
                            p = (index & 127) + 1, 
                            n = name
                            )
                    else:
                        text = name
                    self.model.setItem(self.model.rowCount(), c + 1, QtGui.QStandardItem(text))
                if not collections:
                    collDict[None] += 1
                    self.model.appendRow(QtGui.QStandardItem(name))

        if self.model.rowCount():
            self.tableView.horizontalHeader().setVisible(True)
            self.model.setHorizontalHeaderLabels(['Main library'] + [factoryPresetsNamesDict.get(c, c) for c in allCollections])
            for c, coll in enumerate(allCollections, 1):
                self.tableView.setColumnHidden(c, True if not collDict[coll] else False)
            self.tableView.setColumnHidden(0, True if not collDict[None] else False)
#            self.tableView.horizontalHeader().setStretchLastSection(False)
        else:
            self.tableView.horizontalHeader().setVisible(False)
            noItems = QtGui.QStandardItem('No duplicates found')
            noItems.setEnabled(False)
            self.model.appendRow(noItems)
#            self.tableView.horizontalHeader().setStretchLastSection(True)
        self.tableView.resizeColumnsToContents()
        self.tableView.horizontalHeader().setResizeMode(QtWidgets.QHeaderView.Stretch)

    def queryMulti(self):
        paramList = []
        ignoreNames = self.ignoreNamesChk.isChecked()
        ignoreCats = self.ignoreCatsChk.isChecked()
        for p in Parameters.parameterData:
            if p.attr.startswith('reserved'):
                continue
            elif ignoreNames and p.attr.startswith('nameChar'):
                continue
            elif ignoreCats and p.attr == 'category':
                continue
            paramList.append(p.attr)

        allCollections = self.referenceModel.allCollections
        if self.collectionCombo.currentIndex():
            where = ',reference WHERE (reference.uid = sounds.uid AND reference."{}" IS NOT NULL)'.format(
                allCollections[self.collectionCombo.currentIndex() + 2])
        else:
            where = ''

        queryStr = 'SELECT GROUP_CONCAT(DISTINCT sounds.uid) FROM sounds{where} GROUP BY {params} HAVING count(*) > 1'.format(
            where=where,
            params=','.join(paramList))

        query = QtSql.QSqlQuery()
        if not query.exec_(queryStr):
            print(query.lastError().driverText(), query.lastError().databaseText())

        ignoreFactory = self.ignoreFactoryChk.isChecked() if not self.collectionCombo.currentIndex() else True
#        print(query.lastQuery())
        while query.next():
            uidListRaw = query.value(0)
            print(uidListRaw)
            if not isinstance(uidListRaw, (str, unicode)):
                continue
            if ignoreFactory:
                uidList = []
                for uid in uidListRaw.split(','):
                    if self.database.isUidWritable(uid):
                        uidList.append(uid)
            else:
                uidList = uidListRaw.split(',')
            if len(uidList) <= 1:
                continue
#            print(uidList)
            firstUid = uidList.pop(0)
            parent = QtGui.QStandardItem(self.database.getNameFromUid(firstUid))
            self.model.appendRow(parent)
            collDict = {}
            for uid in uidList:
                name = self.database.getNameFromUid(uid)
                collections = self.database.getCollectionsFromUid(uid, ignoreFactory)
#                if ignoreFactory and not collections:
#                    continue
#                if len(collections) > 1:
#                    name += ' (*)'
                clones = True if len(collections) > 1 else False
#                soundItem = QtGui.QStandardItem(name)
                for c in collections:
                    coll = allCollections[c]
                    collItem = collDict.get(coll)
                    if not collItem:
                        collItem = QtGui.QStandardItem(factoryPresetsNamesDict.get(coll, coll))
                        collDict[coll] = collItem
                        parent.appendRow(collItem)
                    index = self.database.getIndexForUid(uid, coll)
                    if index is not None:
                        text = '{b}{p:03}{c}: {n}'.format(
                            c = ' (*)' if clones else '', 
                            b = uppercase[index >> 7], 
                            p = (index & 127) + 1, 
                            n = name
                            )
                    else:
                        text = name
                    collItem.appendRow(QtGui.QStandardItem(text))
                if not collections:
                    collItem = collDict.get(None)
                    if not collItem:
                        collItem = QtGui.QStandardItem('No collection')
                        collDict[None] = collItem
                        parent.appendRow(collItem)
                    collItem.appendRow(QtGui.QStandardItem(name))
        if self.model.rowCount():
            for r in range(self.model.rowCount()):
                self.treeView.expand(self.model.index(r, 0))
        else:
            noItems = QtGui.QStandardItem('No duplicates found')
            noItems.setEnabled(False)
            self.model.appendRow(noItems)

    def exec_(self, uid=None, collection=None):
        self.collectionCombo.addItems(self.referenceModel.collections)
        self.collectionCombo.setItemData(1, QtGui.QIcon(':/images/bigglesworth_logo.svg'), QtCore.Qt.DecorationRole)
        self.uid = uid
        if isinstance(uid, (str, unicode)) and uid:
            self.nameLbl.setText('<b>{}</b>'.format(self.database.getNameFromUid(uid)))
            self.nameWidget.setVisible(True)
            self.tableView.setVisible(True)
            self.treeView.setVisible(False)
            self.collectionCombo.currentIndexChanged.connect(self.ignoreFactoryChk.setDisabled)
        else:
            self.nameWidget.setVisible(False)
            self.tableView.setVisible(False)
            self.treeView.setVisible(True)
            try:
                self.collectionCombo.currentIndexChanged.disconnect()
            except:
                pass
        if collection is not None:
            self.collectionCombo.setCurrentIndex(self.referenceModel.collections.index(collection) + 1)
        return QtWidgets.QDialog.exec_(self)




