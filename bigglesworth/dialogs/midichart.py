#!/usr/bin/env python2.7

from collections import OrderedDict

#import os
#os.environ['QT_PREFERRED_BINDING'] = 'PyQt4'

from Qt import QtCore, QtGui, QtWidgets, QtPrintSupport
#QtCore.pyqtSignal = QtCore.Signal
from bigglesworth.parameters import Parameters, ctrl2sysex

sysex2ctrl = {v:k for k, v in ctrl2sysex.items()}
PrinterRole = QtCore.Qt.UserRole + 1
PrinterInfoRole = PrinterRole + 1

class ExportDialog(QtWidgets.QDialog):
    Print, Image, TextFile = range(3)
    paperSizes = OrderedDict(
        sorted((size, label) for label, size in QtPrintSupport.QPrinter.__dict__.items() 
            if isinstance(size, QtPrintSupport.QPrinter.PageSize)))

    def __init__(self, parent):
        QtWidgets.QDialog.__init__(self, parent)
        l = QtWidgets.QGridLayout()
        self.setLayout(l)
        self.exportCombo = QtWidgets.QComboBox()
        l.addWidget(self.exportCombo, 0, 0, 1, 2)
        self.exportCombo.addItems(['Print/PDF', 'Image (as screenshot)', 'Text file'])

        self.printerCombo = QtWidgets.QComboBox()
        l.addWidget(self.printerCombo, 1, 0)

        self.pdfPrinter = QtPrintSupport.QPrinter(QtPrintSupport.QPrinter.HighResolution)
        self.pdfPrinter.setOutputFormat(self.pdfPrinter.PdfFormat)
        self.pdfPrinter.setPageMargins(160, 160, 160, 160, self.pdfPrinter.DevicePixel)
        self.pdfPrinter.setFontEmbeddingEnabled(True)
        self.pdfPrinter.setPaperSize(self.pdfPrinter.A4)
        self.printerCombo.addItem('PDF file')
        self.printerCombo.setItemData(0, self.pdfPrinter, PrinterRole)
        self.printerCombo.setItemData(0, QtPrintSupport.QPrinterInfo(self.pdfPrinter), PrinterInfoRole)

        self.paperCombo = QtWidgets.QComboBox()
        l.addWidget(self.paperCombo)

        for i, printerInfo in enumerate(QtPrintSupport.QPrinterInfo.availablePrinters(), 1):
            name = printerInfo.printerName()
            if printerInfo.isDefault():
                name += ' (default)'
            self.printerCombo.addItem(name)
            self.printerCombo.setItemData(i, QtPrintSupport.QPrinter(printerInfo, QtPrintSupport.QPrinter.HighResolution), PrinterRole)
            self.printerCombo.setItemData(i, printerInfo, PrinterInfoRole)
        self.exportCombo.currentIndexChanged.connect(self.printerCombo.setDisabled)
        self.exportCombo.currentIndexChanged.connect(self.paperCombo.setDisabled)
        self.printerCombo.currentIndexChanged.connect(self.setPrinter)
        self.paperCombo.currentIndexChanged.connect(self.setPaperSize)
        self.setPrinter(0)

        self.buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok|QtWidgets.QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        l.addWidget(self.buttonBox, 2, 0, 1, 2)

    def getPaperSizes(self, requested):
        sizes = []
        for i in self.paperSizes:
            if i in requested:
                sizes.append((i, self.paperSizes[i]))
        return sizes

    def setPaperSize(self, index):
        self.currentPrinter.setPaperSize(self.paperCombo.itemData(index, PrinterRole))

    def setPrinter(self, index):
        self.currentPrinter = self.printerCombo.itemData(index, PrinterRole)
#        self.currentPrinter.setOrientation(self.pdfOrientationCombo.currentIndex())

        if self.paperCombo.count():
            currentPaperSize = self.paperCombo.itemData(self.paperCombo.currentIndex(), PrinterRole)
        else:
            currentPaperSize = -1
        self.paperCombo.blockSignals(True)
        self.paperCombo.clear()
        #TODO: maybe just disable not accepted sizes, instead of rebuilding?
        if self.currentPrinter == self.pdfPrinter:
            paperSizes = self.paperSizes.items()
        else:
            printerInfo = self.printerCombo.itemData(index, PrinterInfoRole)
            paperSizes = self.getPaperSizes(printerInfo.supportedPaperSizes())
        sizes = [p for p, _ in paperSizes]
        if currentPaperSize not in sizes:
            currentPaperSize = min(sizes)
        currentPaperSizeIndex = 0
        for i, (p, name) in enumerate(paperSizes):
            self.paperCombo.addItem(name)
            self.paperCombo.setItemData(i, p, PrinterRole)
            if p == currentPaperSize:
                currentPaperSizeIndex = i
        self.paperCombo.setCurrentIndex(currentPaperSizeIndex)
        self.currentPrinter.setPaperSize(currentPaperSize)
        self.paperCombo.blockSignals(False)
        print(currentPaperSize, self.currentPrinter.paperSize())

    def exec_(self):
        res = QtWidgets.QDialog.exec_(self)
        if res:
            return self.exportCombo.currentIndex()


class FilterEdit(QtWidgets.QLineEdit):
    def __init__(self, parent=None):
        QtWidgets.QLineEdit.__init__(self, parent)
        self.icon = QtGui.QIcon.fromTheme('edit-clear')
        self.iconPixmap = None
        self.textChanged.connect(self.setIcon)
        self.rightMargin = self.getTextMargins()[2]
        self.textRect = QtCore.QRect()

    def setIcon(self, content, force=False):
        if content and (not self.iconPixmap or force):
            option = QtWidgets.QStyleOptionFrame()
            self.initStyleOption(option)
            self.textRect = self.style().subElementRect(QtWidgets.QStyle.SE_LineEditContents, option, self)
            self.iconPixmap = self.icon.pixmap(self.textRect.height() - 2)
            margins = list(self.getTextMargins())
            if self.iconPixmap.width() > self.textRect.width() / 2:
                margins[2] = self.rightMargin
            else:
                margins[2] = self.rightMargin + self.iconPixmap.width() + 2
            self.setTextMargins(*margins)
        elif not content and self.iconPixmap:
            self.iconPixmap = None
            margins = list(self.getTextMargins())
            margins[2] = self.rightMargin
            self.setTextMargins(*margins)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            if self.text():
                self.setText('')
        else:
            QtWidgets.QLineEdit.keyPressEvent(self, event)

    def mousePressEvent(self, event):
        if self.text() and event.pos().x() > self.textRect.right() - self.iconPixmap.width() - 2:
            self.setText('')
        else:
            QtWidgets.QLineEdit.mousePressEvent(self, event)

    def mouseMoveEvent(self, event):
        if self.text() and event.pos().x() > self.textRect.right() - self.iconPixmap.width() - 2:
            self.setCursor(QtCore.Qt.ArrowCursor)
        else:
            self.setCursor(QtCore.Qt.IBeamCursor)

    def resizeEvent(self, event):
        self.setIcon(self.text(), True)

    def paintEvent(self, event):
        QtWidgets.QLineEdit.paintEvent(self, event)
        if self.text():
            if self.iconPixmap.width() > self.textRect.width() / 2:
                return
            left = self.textRect.right() - self.iconPixmap.width() - 2
            rect = self.iconPixmap.rect()
            rect.moveCenter(self.textRect.center())
            rect.moveLeft(left)
            qp = QtGui.QPainter(self)
            qp.drawPixmap(rect, self.iconPixmap)


class FilterHeader(QtWidgets.QHeaderView):
    filterChanged = QtCore.pyqtSignal(int, str)

    def __init__(self, orientation, table):
        QtWidgets.QHeaderView.__init__(self, orientation, table)
        self.table = table
        self.table.horizontalScrollBar().valueChanged.connect(self.checkLayout)
        self.sectionResized.connect(self.checkLayout)
        self.sectionMoved.connect(self.checkLayout)
        self.padding = 2
        self.filters = []
        self.setClickable(True)
        self.setMovable(True)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)

    def setModel(self, model):
        if self.model():
            self.model().columnsInserted.disconnect(self.checkLayout)
            self.model().columnsRemoved.disconnect(self.checkLayout)
        QtWidgets.QHeaderView.setModel(self, model)
        model.columnsInserted.connect(self.checkLayout)
        model.columnsRemoved.connect(self.checkLayout)

    def updateGeometries(self):
        if self.filters:
            height = self.filters[0].sizeHint().height()
            self.setViewportMargins(0, 0, 0, height + self.padding)
        else:
            self.setViewportMargins(0, 0, 0, 0)
        QtWidgets.QHeaderView.updateGeometries(self)
        self.checkLayout()

    def checkLayout(self):
        if not self.model():
            return
        count = self.model().columnCount()
        if count != len(self.filters):
            while count > len(self.filters):
                index = len(self.filters)
                filter = FilterEdit(self)
                filter.index = index
                filter.textChanged.connect(lambda text, index=index: self.filterChanged.emit(index, text))
                self.filters.append(filter)
            while count < len(self.filters):
                filter = self.filters.pop()
                filter.deleteLater()
#        if self.table.verticalHeader().isVisible():
#            left = self.table.verticalHeader().sizeHint().width()
#        else:
#            left = 0
        if not self.filters:
            return
        top = QtWidgets.QHeaderView.sizeHint(self).height()
        height = self.filters[0].sizeHint().height()
        for index, filter in enumerate(self.filters):
            filter.move(self.sectionPosition(index) - self.offset(), top + self.padding / 2)
            filter.resize(self.sectionSize(index), height)

    def sizeHint(self):
        hint = QtWidgets.QHeaderView.sizeHint(self)
        if self.filters:
            height = self.filters[0].sizeHint().height()
            hint.setHeight(hint.height() + height + self.padding)
        return hint


class CornerLabel(QtWidgets.QLabel):
    clicked = QtCore.pyqtSignal()
    def mousePressEvent(self, event):
        if event.buttons() == QtCore.Qt.LeftButton:
            self.clicked.emit()


class FilterTable(QtWidgets.QTableView):
    def __init__(self, *args, **kwargs):
        QtWidgets.QTableView.__init__(self, *args, **kwargs)
        self.cornerButton = self.findChild(QtWidgets.QAbstractButton)
        cornerLayout = QtWidgets.QHBoxLayout()
        self.cornerButton.setLayout(cornerLayout)
        self.cornerButton.setContentsMargins(0, 0, 0, 0)
        cornerLayout.setContentsMargins(0, 0, 0, 0)
        self.cornerLabel = CornerLabel('SysEx')
        self.cornerLabel.setAlignment(QtCore.Qt.AlignCenter)
        cornerLayout.addWidget(self.cornerLabel)

    def resizeEvent(self, event):
        self.cornerButton.setMaximumHeight(QtWidgets.QHeaderView.sizeHint(self.horizontalHeader()).height())
        QtWidgets.QTableView.resizeEvent(self, event)



class ParamProxy(QtCore.QSortFilterProxyModel):
    reserved = True
    showSysEx = True
    hidden = set()
    hiddenChanged = QtCore.pyqtSignal(int)

    def headerData(self, section, orientation, role):
        if orientation == QtCore.Qt.Vertical and role == QtCore.Qt.DisplayRole:
            return str(self.index(section, 0).data(QtCore.Qt.UserRole))
        return QtCore.QSortFilterProxyModel.headerData(self, section, orientation, role)

    def setRowsVisible(self, show, rows):
        if not show:
            [self.hidden.add(row) for row in rows]
        else:
            #this throws a "Set changed size during iteration" RuntimeError...?
#            [self.hidden.discard(row) for row in rows]
            self.hidden = set(row for row in self.hidden if row not in rows)
        self.invalidateFilter()
        self.hiddenChanged.emit(len(self.hidden))

    def hideSysEx(self, show):
        self.showSysEx = show
        self.invalidateFilter()

    def hideReserved(self, hidden):
        self.reserved = not hidden
        self.invalidateFilter()

    def filterAcceptsRow(self, row, parent):
        index = self.sourceModel().index(row, 0)
        if (self.reserved or index.flags() & QtCore.Qt.ItemIsEnabled) and \
            QtCore.QSortFilterProxyModel.filterAcceptsRow(self, row, parent):
                if not (self.showSysEx or index.data()):
                    return False
                return row not in self.hidden
        return False


class MidiChartDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        self.setWindowTitle('Ctrl and SysEx parameters')
        l = QtWidgets.QGridLayout()
        self.setLayout(l)
        l.setContentsMargins(2, 2, 2, 2)

        panelLayout = QtWidgets.QHBoxLayout()
        l.addLayout(panelLayout, 0, 0)

        self.showCtrlChk = QtWidgets.QCheckBox('CC parameters only')
        panelLayout.addWidget(self.showCtrlChk)
        self.showCtrlChk.toggled.connect(self.showCtrl)

        self.hideReservedChk = QtWidgets.QCheckBox('Hide invalid parameters')
        panelLayout.addWidget(self.hideReservedChk)

        vLine = QtWidgets.QFrame()
        vLine.setFrameShape(vLine.VLine)
        vLine.setFrameShadow(vLine.Sunken)
        panelLayout.addWidget(vLine)
        panelLayout.addSpacerItem(QtWidgets.QSpacerItem(1, 1, QtWidgets.QSizePolicy.Expanding))

        self.exportBtn = QtWidgets.QPushButton(QtGui.QIcon.fromTheme('document-save'), 'Export...')
        panelLayout.addWidget(self.exportBtn)
        self.exportBtn.clicked.connect(self.export)

        self.table = FilterTable()
        l.addWidget(self.table)
        self.table.verticalHeader().setDefaultAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter)
        self.table.verticalHeader().setMovable(True)
        self.table.verticalHeader().setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.table.verticalHeader().customContextMenuRequested.connect(self.rowsMenu)
        self.table.setEditTriggers(self.table.NoEditTriggers)
        self.table.setHorizontalScrollMode(self.table.ScrollPerPixel)
        self.table.setSelectionBehavior(self.table.SelectRows)
        self.header = FilterHeader(QtCore.Qt.Horizontal, self.table)
        self.header.filterChanged.connect(self.setFilter)
        self.header.sectionClicked.connect(self.setSorting)
        self.table.setHorizontalHeader(self.header)
        self.table.setSortingEnabled(True)

        self.model = QtGui.QStandardItemModel()
        self.proxy = ParamProxy()
        self.proxy.setSourceModel(self.model)
        self.proxy.hiddenChanged.connect(self.hiddenChanged)
        self.table.setModel(self.proxy)
        self.table.cornerLabel.clicked.connect(self.reindex)
        self.table.cornerLabel.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.table.cornerLabel.customContextMenuRequested.connect(self.headerMenu)
        self.hideReservedChk.toggled.connect(self.proxy.hideReserved)
        self.hideReservedChk.toggled.connect(self.table.resizeRowsToContents)

        self.columns = ['CC', 'Hex', 'Parameter', 'Group', 'Parameter', 'Values', 'Min', 'Max', 'Step']
        self.model.setHorizontalHeaderLabels(self.columns)
        for param in Parameters.parameterData:
            ctrl = sysex2ctrl.get(param.id)
            if ctrl is not None:
                ctrlItem = QtGui.QStandardItem()
                ctrlItem.setData(ctrl, QtCore.Qt.DisplayRole)
                ctrlItem.setData(QtCore.Qt.AlignCenter, QtCore.Qt.TextAlignmentRole)
                hexItem = QtGui.QStandardItem('0x{:X}'.format(ctrl))
                hexItem.setData(QtCore.Qt.AlignCenter, QtCore.Qt.TextAlignmentRole)
            else:
                ctrlItem = QtGui.QStandardItem()
                hexItem = QtGui.QStandardItem()
            ctrlItem.setData(param.id, QtCore.Qt.UserRole)
            if param.attr.startswith('reserved'):
                fullNameItem = QtGui.QStandardItem('reserved')
                items = [ctrlItem, hexItem, fullNameItem, QtGui.QStandardItem(), fullNameItem.clone()]
                while len(items) < len(self.columns):
                    items.append(QtGui.QStandardItem())
                for item in items:
                    item.setEnabled(False)
                self.model.appendRow(items)
            else:
                fullNameItem = QtGui.QStandardItem(param.fullName)
                familyItem = QtGui.QStandardItem(param.family)
                shortNameItem = QtGui.QStandardItem(param.shortName)
                minItem = QtGui.QStandardItem(str(param.range.minimum))
                minItem.setData(QtCore.Qt.AlignCenter, QtCore.Qt.TextAlignmentRole)
                maxItem = QtGui.QStandardItem(str(param.range.maximum))
                maxItem.setData(QtCore.Qt.AlignCenter, QtCore.Qt.TextAlignmentRole)
                stepItem = QtGui.QStandardItem(str(param.range.step))
                stepItem.setData(QtCore.Qt.AlignCenter, QtCore.Qt.TextAlignmentRole)
                rangeItem = QtGui.QStandardItem(u'{} .. {}'.format(param.values[0], param.values[-1]))
                rangeItem.setToolTip(u'<body>{}</body>'.format(u', '.join(param.values)))
                self.model.appendRow([ctrlItem, hexItem, fullNameItem, familyItem, shortNameItem, rangeItem, minItem, maxItem, stepItem])

        self.table.setStatusTip('Right click on headers to show or hide rows and columns; headers can be dragged to change ordering')
        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()
        self.header.setResizeMode(self.header.Fixed)
        self.header.setResizeMode(2, self.header.Stretch)
        self.header.setResizeMode(3, self.header.Stretch)
        self.header.setResizeMode(4, self.header.Stretch)
        self.table.verticalHeader().setResizeMode(QtWidgets.QHeaderView.Fixed)
        self.header.customContextMenuRequested.connect(self.headerMenu)
        self.table.setColumnHidden(3, True)
        self.table.setColumnHidden(4, True)
        self.hideReservedChk.setChecked(True)

        self.statusbar = QtWidgets.QStatusBar(self)
        l.addWidget(self.statusbar)
        self.hiddenLabel = QtWidgets.QLabel()
        self.hiddenLabel.setFrameShape(self.hiddenLabel.StyledPanel)
        self.hiddenLabel.setFrameShadow(self.hiddenLabel.Sunken)
        self.hiddenLabel.setVisible(False)
        self.statusbar.addPermanentWidget(self.hiddenLabel)
        self.resize(640, 480)

    def hiddenChanged(self, hidden):
        if hidden:
            self.hiddenLabel.setText('{} row{} hidden'.format(hidden, 's' if hidden > 1 else ''))
        self.hiddenLabel.setVisible(hidden)

    def event(self, event):
        if event.type() == QtCore.QEvent.StatusTip:
            self.statusbar.showMessage(event.tip())
        return QtWidgets.QDialog.event(self, event)

    def rowsMenu(self, pos):
        menu = QtWidgets.QMenu()
        selected = self.table.selectionModel().selectedRows()
        index = self.table.indexAt(pos)
        if not selected:
            if index.isValid():
                self.table.selectRow(index.row())
                selected = [index]
        if selected:
            if index.isValid() and index not in selected:
                self.table.selectRow(index.row())
                selected = self.table.selectionModel().selectedRows()
            hideAction = menu.addAction('Hide {} row{}'.format(len(selected), 's' if len(selected) > 1 else ''))
            hideAction.setData((False, [self.proxy.mapToSource(index).row() for index in selected]))
        hiddenMenu = menu.addMenu('Restore hidden rows')
        if self.proxy.hidden:
            if len(self.proxy.hidden) > 1:
                restoreAction = hiddenMenu.addAction('Restore all rows')
                restoreAction.setData((True, self.proxy.hidden))
                hiddenMenu.addSeparator()
            for row in self.proxy.hidden:
                text = self.model.index(row, 2).data(QtCore.Qt.DisplayRole)
                action = hiddenMenu.addAction(text)
                action.setData((True, [row]))
        else:
            hiddenMenu.setEnabled(False)
        res = menu.exec_(QtGui.QCursor.pos())
        if res and res.data():
            self.proxy.setRowsVisible(*res.data())
            self.table.resizeRowsToContents()

    def headerMenu(self, pos):
        menu = QtWidgets.QMenu()

        sysExAction = menu.addAction('SysEx indexes')
        sysExAction.setCheckable(True)
        sysExAction.setChecked(self.table.verticalHeader().isVisible())

        for column, label in enumerate(['Control Change', 'CC Hex', 'Parameter (full)', 'Parameter group', 'Parameter (short)', 'Values', 'Minimum', 'Maximum', 'Step']):
            action = menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(not self.table.isColumnHidden(column))
            action.setData(column)
            if label == 'Minimum':
                minimumAction = action

        menu.insertSeparator(minimumAction)
        rangeAction = QtWidgets.QAction('Range', menu)
        rangeAction.setCheckable(True)
        rangeAction.setChecked(not any(self.table.isColumnHidden(c) for c in (6, 7, 8)))
        rangeAction.setData((6, 7, 8))
        menu.insertAction(minimumAction, rangeAction)

        res = menu.exec_(QtGui.QCursor.pos())
        if res == sysExAction:
            self.table.verticalHeader().setVisible(sysExAction.isChecked())
        elif res and res.data() is not None:
            data = res.data()
            if isinstance(data, int):
                self.table.setColumnHidden(data, not res.isChecked())
                if data == 2 and res.isChecked():
                    self.table.setColumnHidden(3, True)
                    self.table.setColumnHidden(4, True)
                elif data in (3, 4) and res.isChecked():
                    self.table.setColumnHidden(2, True)
                    if data == 3:
                        self.table.setColumnHidden(4, False)
            else:
                for column in data:
                    self.table.setColumnHidden(column, not res.isChecked())
            self.header.checkLayout()

    def showCtrl(self, show):
        self.proxy.hideSysEx(not show)
        self.hideReservedChk.setDisabled(show)

    def reindex(self):
        self.header.setSortIndicator(-1, QtCore.Qt.AscendingOrder)
        self.proxy.setSortRole(QtCore.Qt.InitialSortOrderRole)
        self.proxy.invalidate()

    def setFilter(self, index, text):
        if text:
            self.proxy.hideReserved(True)
            self.hideReservedChk.setEnabled(False)
        else:
            self.hideReservedChk.setEnabled(True)
            self.proxy.hideReserved(self.hideReservedChk.isChecked())
        self.proxy.setSortRole(QtCore.Qt.DisplayRole)
        self.proxy.setFilterKeyColumn(index)
        self.proxy.setFilterRegExp(QtCore.QRegExp(text, QtCore.Qt.CaseInsensitive, QtCore.QRegExp.FixedString))

    def setSorting(self, index):
        self.proxy.setSortRole(QtCore.Qt.DisplayRole)
        self.header.setSortIndicator(index, self.header.sortIndicatorOrder())

    def export(self):
        if not self.proxy.rowCount():
            return
        dialog = ExportDialog(self)
        res = dialog.exec_()
        if res == dialog.Print:
            self.printExport(dialog.currentPrinter)
#                dialog.printerCombo.itemData(dialog.printerCombo.currentIndex(), PrinterRole), 
#                dialog.printerCombo.itemData(dialog.printerCombo.currentIndex(), PrinterRole), 
##                dialog.paperCombo.itemData(dialog.paperCombo.currentIndex()))
#                dialog.paperCombo.itemData(dialog.paperCombo.currentIndex()))
        elif res == dialog.TextFile:
            self.textExport()
        elif res == dialog.Image:
            self.imageExport()

    def printExport(self, printer):
        if printer.outputFormat() == QtPrintSupport.QPrinter.PdfFormat:
            path = QtWidgets.QFileDialog.getSaveFileName(self, 'Export to PDF', 
                QtGui.QDesktopServices.storageLocation(QtGui.QDesktopServices.DocumentsLocation) + '/MidiChart.pdf', 
                'PDF files (*.pdf);;All files (*.*)')
            if not path:
                return
            printer.setOutputFileName(path)

        def doHeaders():
            qp.save()
            widths = iter(sizes)
            line = 0
            if showSysEx:
                width = widths.next()
                qp.drawText(0, 0, width, baseHeight, QtCore.Qt.AlignCenter, 'SysEx')
                qp.translate(width, 0)
                line += width
            for column in columns:
                width = widths.next()
                qp.drawText(0, 0, width, baseHeight, QtCore.Qt.AlignCenter, self.columns[column])
                qp.translate(width, 0)
                line += width
            qp.restore()
            qp.setPen(headerPen)
            qp.drawLine(0, baseHeight * 1.5, line, baseHeight * 1.5)
            qp.translate(0, baseHeight * 2)

        baseFont = self.font()
        baseMetrics = QtGui.QFontMetricsF(baseFont, printer)
        baseHeight = baseMetrics.height()
        descent = baseMetrics.descent() * .25
        pointRatio = baseHeight / baseFont.pointSizeF()

        leftAlign = QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter
        centerAlign = QtCore.Qt.AlignCenter
        alignments = {c:(leftAlign if 1 < c < 6 else centerAlign) for c in range(len(self.columns))}

        columns = []
        labels = []
        data = []
        sizes = []
        sysEx = []
        for c in range(self.model.columnCount()):
            if not self.table.isColumnHidden(c):
                columns.append(c)
                label = self.model.headerData(c, QtCore.Qt.Horizontal, QtCore.Qt.DisplayRole)
                labels.append(label)
                sizes.append(baseMetrics.width(label))
                data.append([])
        for row in range(self.proxy.rowCount()):
            for c, column in enumerate(columns):
                text = self.proxy.index(row, column).data()
                if text is None:
                    text = ''
                elif isinstance(text, int):
                    text = str(text)
                data[c].append(text)
                sizes[c] = max(sizes[c], baseMetrics.width(text))
            sysEx.append(self.proxy.headerData(row, QtCore.Qt.Vertical, QtCore.Qt.DisplayRole))

        sizes = [s + 16 * pointRatio for s in sizes]

        qp = QtGui.QPainter(printer)
        basePen = qp.pen()
        headerPen = QtGui.QPen(QtCore.Qt.darkGray, .5 * pointRatio)
        linePen = QtGui.QPen(QtCore.Qt.lightGray, .15 * pointRatio)

        left, top, right, bottom = printer.getPageMargins(printer.DevicePixel)
        fullPage = qp.viewport().adjusted(left, top, -right, -bottom)
        width = fullPage.width()
        height = fullPage.height()

        if self.table.verticalHeader().isVisible():
            showSysEx = True
            sizes.insert(0, baseMetrics.width('SysEx'))
        else:
            showSysEx = False
        qp.translate(left, top)

        qp.save()
        doHeaders()
        vPos = top + baseHeight * 2
        qp.setPen(basePen)

        for row in range(len(data[0])):
            widths = iter(sizes)
            line = 0
            qp.save()
            if showSysEx:
                width = widths.next()
                qp.drawText(0, 0, width, baseHeight, QtCore.Qt.AlignCenter, sysEx[row])
                qp.translate(width, 0)
                line += width
            for c, column in enumerate(columns):
                width = widths.next()
                text = data[c][row]
                qp.drawText(0, 0, width, baseHeight, alignments[column], text)
                qp.translate(width, 0)
                line += width
            qp.restore()
            if vPos + baseHeight > height:
                printer.newPage()
                qp.restore()
                qp.save()
                doHeaders()
                vPos = top + baseHeight * 2
                qp.setPen(basePen)
            else:
                vPos += baseHeight
                qp.translate(0, baseHeight)
                qp.setPen(linePen)
                qp.drawLine(0, -descent, line, -descent)
                qp.setPen(basePen)

        qp.restore()
        qp.end()
        print(width, height)

    def imageExport(self):
        path = QtWidgets.QFileDialog.getSaveFileName(self, 'Export as image', 
                QtGui.QDesktopServices.storageLocation(QtGui.QDesktopServices.PicturesLocation) + '/MidiChart.png', 
                'PNG images (*.png);;JPG images (*.jpg *.jpeg);;XPM images (*.xpm);;BPM images (*.bpm);;All files (*.*)')
        if not path:
            return
        font = self.font()
        font.setPointSizeF(font.pointSizeF() * 1.2)
        table = QtWidgets.QTableView()
        table.setModel(self.proxy)
        for c in range(self.model.columnCount()):
            table.setColumnHidden(c, self.table.isColumnHidden(c))
        table.setFont(font)
        table.horizontalHeader().setFont(font)
        if self.table.verticalHeader().isVisible():
            cornerButton = table.findChild(QtWidgets.QAbstractButton)
            cornerLayout = QtWidgets.QHBoxLayout()
            cornerButton.setLayout(cornerLayout)
            cornerButton.setContentsMargins(0, 0, 0, 0)
            cornerLayout.setContentsMargins(0, 0, 0, 0)
            cornerLabel = CornerLabel('SysEx')
            cornerLabel.setAlignment(QtCore.Qt.AlignCenter)
            cornerLayout.addWidget(cornerLabel)
        else:
            table.verticalHeader().setVisible(False)
        table.resizeColumnsToContents()
        table.resizeRowsToContents()
        table.resize(
            table.horizontalHeader().length() + table.verticalHeader().width(), 
            table.verticalHeader().length() + table.horizontalHeader().height() + table.frameWidth() * 2)
        table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        img = QtGui.QImage(table.size(), QtGui.QImage.Format_ARGB32_Premultiplied)
        qp = QtGui.QPainter(img)
        table.render(qp)
        qp.end()
        img.save(path)

    def textExport(self):
        path = QtWidgets.QFileDialog.getSaveFileName(self, 'Export to file', 
            QtGui.QDesktopServices.storageLocation(QtGui.QDesktopServices.DocumentsLocation) + '/MidiChart.txt', 
            'Text files (*.txt);;All files (*.*)')
        if not path:
            return
        columns = []
        labels = []
        data = []
        sizes = []
        sysEx = []
        for c in range(self.model.columnCount()):
            if not self.table.isColumnHidden(c):
                columns.append(c)
                label = self.model.headerData(c, QtCore.Qt.Horizontal, QtCore.Qt.DisplayRole)
                labels.append(label)
                data.append([label])
                sizes.append(len(label))
        for c, label in enumerate(labels):
            data[c].extend(('=' * len(label), ''))
#            sizes[c] = max(sizes[c], len(label))
        for row in range(self.proxy.rowCount()):
            for c, column in enumerate(columns):
                text = self.proxy.index(row, column).data()
                if text is None:
                    text = ''
                elif isinstance(text, int):
                    text = str(text)
                data[c].append(text)
                sizes[c] = max(sizes[c], len(text))
            sysEx.append(self.proxy.headerData(row, QtCore.Qt.Vertical, QtCore.Qt.DisplayRole))
        text = u''
        showSysEx = self.table.verticalHeader().isVisible()
        for row in range(len(data[0])):
            if showSysEx:
                if row > 2:
                    text += u'{}'.format(sysEx[row - 3]).ljust(8, ' ')
                elif row == 2:
                    text += '        '
                elif row == 1:
                    text += '=====   '
                else:
                    text += 'SysEx   '
            for column in range(len(columns)):
                size = sizes[column] + 3
                text += data[column][row].ljust(size, ' ') 
            text += u'\n'
        try:
            with open(path, 'wb') as txtFile:
                txtFile.write(text.encode('utf-8'))
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, 'Write error', 
                'An error occured while writing to file:\n{}'.format(e), 
                QtWidgets.QMessageBox.Ok)

if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)
    w = CheatsDialog()
    w.show()
    sys.exit(app.exec_())
