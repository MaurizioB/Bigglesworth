from Qt import QtCore, QtGui, QtWidgets

from bigglesworth.utils import loadUi

class InitEmptySlotsDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, bank=None):
        QtWidgets.QDialog.__init__(self, parent)
        loadUi('ui/initemptyslots.ui', self)
        self.initBankModel = QtGui.QStandardItemModel()
        self.initBankList.setModel(self.initBankModel)
        banks = iter('ABCDEFGH')
        self.bankItems = []
        for row in range(2):
            items = []
            for column in range(4):
                item = QtGui.QStandardItem('Bank ' + banks.next())
                item.setCheckable(True)
                items.append(item)
                self.bankItems.append(item)
            self.initBankModel.appendRow(items)
        if bank is not None:
            self.bankItems[bank].setCheckState(QtCore.Qt.Checked)

        for column in range(4):
            self.initBankList.horizontalHeader().setResizeMode(column, QtWidgets.QHeaderView.Stretch)

        self.initBankList.resizeRowsToContents()
        rowWidth = self.initBankList.sizeHintForIndex(self.initBankModel.index(0, 0)).width() * 4
        width = rowWidth + (self.initBankList.frameWidth() + self.initBankList.lineWidth()) * 2
        rowHeight = self.initBankList.verticalHeader().defaultSectionSize()
        height = (rowHeight + self.initBankList.frameWidth() + self.initBankList.lineWidth()) * 2
        self.initBankList.setFixedSize(width, height)

        self.initSelectRadio.toggled.connect(self.initBankList.setEnabled)
        self.initAllRadio.toggled.connect(self.setInitItems)

        self.adjustSize()

    def setInitItems(self, state):
        for item in self.bankItems:
            if not item.checkState() == QtCore.Qt.Checked:
                item.setCheckState(state)

    def exec_(self):
        res = QtWidgets.QDialog.exec_(self)
        if res:
            return [bank for bank, item in enumerate(self.bankItems) if item.checkState()]

