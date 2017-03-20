# *-* coding: utf-8 *-*

from string import digits, uppercase
from PyQt4 import QtCore, QtGui
from bigglesworth.utils import load_ui

TEXT, PDF = range(2)

class PrinterOutsideWidget(QtGui.QWidget):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        layout = QtGui.QHBoxLayout()
        self.setLayout(layout)
        icon = self.style().standardIcon(QtGui.QStyle.SP_MessageBoxWarning)
        icon_label = QtGui.QLabel(self)
        icon_label.setPixmap(icon.pixmap(16, 16))
        layout.addWidget(icon_label)
        self.label = QtGui.QLabel()
        layout.addWidget(self.label)

    def setText(self, text):
        self.label.setText(text)

class PrinterPageRect(QtGui.QGraphicsRectItem):
    chars = ''.join(chr(x) for x in range(32, 127))
    def __init__(self, main, device, font):
        QtGui.QGraphicsRectItem.__init__(self)
        self.setPen(QtCore.Qt.black)
        self.setBrush(QtCore.Qt.white)
        self.setRect(0, 0, 40, 60)
        self.font = font
        self.font_size = font.pixelSize()
        self.main = main
        self.device = device
        self.spacing = 16
        self.compute_metrics()
        self.cols = 1
        self.pagebank = False
        self.contents = []
        self.margins = (0, 0, 0, 0)
        self.text_rect = self.rect()

    @property
    def max_lines(self):
        return int(self.text_rect.height()/self.font_metrics.lineSpacing())-1

    def compute_metrics(self):
        self.font_metrics = QtGui.QFontMetrics(self.font)
        cat = max([self.font_metrics.width(c) for c in digits+uppercase])*4 + self.font_metrics.width('    ')
        name = max([self.font_metrics.width(c) for c in self.chars])*16 + self.spacing
        self.prog_size = cat+name

    def setFont(self, font):
        self.font = font
        self.font.setPixelSize(self.font_size)
        self.compute_metrics()
        self.update()

    def setFontSize(self, size):
        self.font.setPixelSize(size)
        self.font_size = size
        self.compute_metrics()
        self.update()

    def pageUpdate(self):
        size = self.device.paperRect(1)
        margins = self.device.getPageMargins(1)
        self.setRect(QtCore.QRectF(0, 0, size.width(), size.height()))
        self.text_rect = self.rect().adjusted(margins[0], margins[1], -margins[2], -margins[3])
        self.compute_metrics()
        self.update()

    def setText(self, text):
        contents = text.split('\n')
        if len(contents) < 4:
            self.cols = 1
        elif '\t\t' in contents[4]:
            self.cols = contents[4].count('\t\t')+1
        else:
            self.cols = 1
        self.contents = []
        for l, line in enumerate(contents):
            if not '\t' in line:
                if not '=' in line:
                    self.contents.append(line)
                else:
                    self.contents.append('')
                continue
            self.contents.append([l.replace('\t', '    ') for l in line.split('\t\t')])

    def setSpacing(self, value):
        self.spacing = value
        self.compute_metrics()
        self.update()

    def setPageBank(self, state):
        self.pagebank = state
        self.update()

    def paint(self, painter, *args, **kwargs):
        QtGui.QGraphicsRectItem.paint(self, painter, *args, **kwargs)
        painter.setClipRect(self.text_rect)
        painter.setFont(self.font)
        space = self.font_metrics.lineSpacing()
        delta = self.text_rect.y() + space
        left = self.text_rect.x()
        max_lines = self.max_lines
        cols = 0
        outside = False
        for l, line in enumerate(self.contents):
            if l > max_lines:
                break
            if isinstance(line, str):
                if l > 5 and self.pagebank:
                    break
                painter.drawText(left, delta, line)
                delta += space
            else:
                for c, p in enumerate(line):
                    painter.drawText(left+self.prog_size*cols, delta, p)
                    if left+self.prog_size*cols+self.font_metrics.width(p) > self.text_rect.right():
                        outside = True
                    cols += 1
                    if cols == self.cols:
                        delta += space
                        cols = 0
        self.main.outside.emit(outside)


class MultiCombo(QtGui.QComboBox):
    selectionChanged = QtCore.pyqtSignal(object)
    def __init__(self, parent):
        QtGui.QComboBox.__init__(self, parent)
        self.model = QtGui.QStandardItemModel()
        self.state_item = QtGui.QStandardItem('all')
        self.state_item.setEnabled(False)
        self.model.appendRow(self.state_item)
        all_item = QtGui.QStandardItem('select all')
        self.model.appendRow(all_item)
        none_item = QtGui.QStandardItem('select none')
        self.model.appendRow(none_item)
        self.bank_items = []
        for i in range(8):
            item = QtGui.QStandardItem(uppercase[i])
            item.setCheckable(True)
            item.setCheckState(2)
            item.setTristate(False)
            self.model.appendRow(item)
            self.bank_items.append(item)
        self.setModel(self.model)
        self.activated.connect(self.check)
        self.setCurrentIndex(0)
        self.installEventFilter(self)

    def hidePopup(self):
        if not self.view().rect().contains(self.view().mapFromGlobal(QtGui.QCursor().pos())):
            QtGui.QComboBox.hidePopup(self)

    def check(self, index):
        if index == 1:
            for item in self.bank_items:
                item.setCheckState(2)
            self.state_item.setText('all')
            self.selectionChanged.emit(tuple(range(8)))
            self.setCurrentIndex(0)
            return
        elif index == 2:
            for item in self.bank_items:
                item.setCheckState(0)
            self.state_item.setText('none')
            self.selectionChanged.emit(())
            self.setCurrentIndex(0)
            return
        item = self.model.item(index)
        state = item.checkState()
        item.setCheckState(state^2)
        selected = []
        for i, item in enumerate(self.bank_items):
            if not item.checkState(): continue
            selected.append(i)
        self.state_item.setText(', '.join(uppercase[i] for i in selected) if selected else 'none')
        self.selectionChanged.emit(selected)
        self.setCurrentIndex(0)

    def keyPressEvent(self, event):
        event.ignore()

    def wheelEvent(self, event):
        event.ignore()

class PrintDialog(QtGui.QDialog):
    outside = QtCore.pyqtSignal(bool)
    def __init__(self, main, parent):
        QtGui.QDialog.__init__(self, parent)
        load_ui(self, 'dialogs/print_library.ui')
        self.setModal(True)
        self.main = main
        self.format_group.setId(self.text_radio, TEXT)
        self.format_group.setId(self.pdf_radio, 1)
        self.mode = TEXT
        self.monofont = QtGui.QFont('Monospace')
        self.monofont.setPixelSize(10)
        self.font_size_spin.setValue(9)
        self.font_combo.setCurrentFont(self.monofont)
        self.format_group.buttonClicked[int].connect(self.mode_set)

        self.text = ''
        self.monotext = QtGui.QGraphicsTextItem(self.text)
        self.output = QtGui.QPrinter()
        self.output.setOutputFormat(QtGui.QPrinter.PdfFormat)
        self.output.setFontEmbeddingEnabled(True)
        self.output.setPaperSize(QtGui.QPrinter.A4)
        pagefont = QtGui.QFont('Monospace')
        pagefont.setPixelSize(9)
        self.page = PrinterPageRect(self, self.output, pagefont)
        self.outside.connect(lambda state: self.outside_widget.setVisible(True if state else False))
        self.outside_widget.hide()


        page_sizes = []
        self.ps_ids = {}
        ps_id = 0
        a4_id = None
        for attr in dir(QtGui.QPrinter):
            ps = getattr(QtGui.QPrinter, attr)
            if attr == 'Custom': continue
            if isinstance(ps, QtGui.QPrinter.PageSize):
                page_sizes.append(attr)
                self.ps_ids[ps_id] = ps
                if attr == 'A4': a4_id = ps_id
                ps_id += 1
        self.ps_ids[len(page_sizes)] = QtGui.QPrinter.Custom
        page_sizes.append('Custom')
        self.format_combo.addItems(page_sizes)

        self.format_combo.setCurrentIndex(a4_id)
        self.page.pageUpdate()

        self.printview = QtGui.QGraphicsView()
        self.gridLayout.addWidget(self.printview)
        self.printscene = QtGui.QGraphicsScene()
        self.printscene.addItem(self.monotext)
        self.monotext.hide()
        self.printscene.addItem(self.page)
        self.page.hide()
        self.printview.setScene(self.printscene)

        self.col_spin.valueChanged.connect(self.redraw)
        self.col_spin.valueChanged.connect(lambda value: self.vertical_chk.setEnabled(True if value > 1 else False))
        self.vertical_chk.toggled.connect(self.redraw)
        self.format_combo.currentIndexChanged.connect(self.setPageSize)
        self.font_combo.currentFontChanged.connect(self.setFont)
        self.font_size_spin.valueChanged.connect(self.setFontSize)
        self.orientation_combo.currentIndexChanged.connect(self.setOrientation)
        self.spacing_spin.valueChanged.connect(self.setSpacing)
        self.banks_combo.selectionChanged.connect(self.bank_selection_update)
        self.bank_selection = tuple(range(len(self.main.blofeld_library.data)))

    def setFont(self, font):
        self.page.setFont(font)
        self.update()

    def setFontSize(self, size):
        self.page.setFontSize(size)
        self.update()

    def setSpacing(self, value):
        self.page.setSpacing(value)
        self.update()

    def setOrientation(self, orientation):
        self.output.setOrientation(orientation)
        self.page.pageUpdate()
        if self.page.isVisible():
            self.printview.setSceneRect(self.page.boundingRect())
            self.printview.fitInView(self.page.boundingRect(), QtCore.Qt.KeepAspectRatio)
        self.update()

    def setPageSize(self, id):
        self.output.setPaperSize(self.ps_ids[id])
        self.page.pageUpdate()
        if self.page.isVisible():
            self.printview.setSceneRect(self.page.boundingRect())
            self.printview.fitInView(self.page.boundingRect(), QtCore.Qt.KeepAspectRatio)
        self.update()

    def mode_set(self, mode):
        self.pdf_group.setEnabled(mode)
        if mode == TEXT:
            self.printscene.setFont(self.monofont)
            self.outside_widget.hide()
        else:
            self.printview.setSceneRect(self.page.boundingRect())
            self.printview.fitInView(self.page.boundingRect(), QtCore.Qt.KeepAspectRatio)
        self.mode = mode
        self.redraw()

    def redraw(self, *args):
        self.compute(self.col_spin.value(), self.vertical_chk.isChecked())
        if self.mode == TEXT:
            self.printview.resetTransform()
            self.page.hide()
            self.printview.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
            self.printview.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
            self.printscene.removeItem(self.monotext)
            self.monotext = QtGui.QGraphicsTextItem()
            self.monotext.setPlainText(self.text.replace('\t\t', '        ').replace('\t', '    '))
            self.monotext.setFont(self.monofont)
            self.printscene.addItem(self.monotext)
            self.printview.setAlignment(QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop)
            #for some reason, very long plain text contents always set QGraphicsTextItem's height to 2012, then we use metrics
            self.printview.setSceneRect(0, 0, self.monotext.boundingRect().width(), QtGui.QFontMetrics(self.monofont).lineSpacing()*len(self.text.split('\n')))
            self.printview.verticalScrollBar().setValue(0)
            self.printview.horizontalScrollBar().setValue(0)
            return
        self.monotext.hide()
        self.printview.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.printview.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.printview.setAlignment(QtCore.Qt.AlignCenter)
        self.page.setText(self.text)
        self.page.show()
        self.printview.setSceneRect(self.page.boundingRect())
        self.printview.fitInView(self.page.boundingRect(), QtCore.Qt.KeepAspectRatio)
        self.pagebank_chk.toggled.connect(self.page.setPageBank)

    def bank_selection_update(self, selection):
        self.bank_selection = selection
        self.redraw()
        self.buttonBox.button(QtGui.QDialogButtonBox.Ok).setEnabled(True if selection else False)

    def compute(self, cols=1, vertical=False):
        text = 'Blofeld preset list:\n\n'
        for b, bank in enumerate(self.main.blofeld_library.data):
            if b not in self.bank_selection: continue
            sounds = []
            for sound in bank:
                sounds.append('{}{:03}\t{}'.format(uppercase[sound.bank], sound.prog+1, sound.name))
            if sounds:
                text += 'Bank {}:\n=======\n'.format(uppercase[sound.bank])
                if cols == 1:
                    text += '\n'.join(sounds)
                else:
                    if vertical:
                        div = len(sounds)/cols
                        if div*cols < len(sounds):
                            div += 1
                        for d in range(div):
                            for col in range(cols):
                                try:
                                    text += sounds[d + div*col]
                                    if col == cols-1:
                                        text += '\n'
                                    else:
                                        text += '\t\t'
                                except:
                                    text += '\n'
                                    break
                    else:
                        col = 0
                        for txt in sounds:
                            text += txt
                            col += 1
                            if col == cols:
                                text += '\n'
                                col = 0
                            else:
                                text += '\t\t'
                text += '\n\n'
        self.text = text

    def resizeEvent(self, event):
        if self.page.isVisible():
            self.printview.fitInView(self.page.boundingRect(), QtCore.Qt.KeepAspectRatio)

    def exec_(self):
        self.show()
        self.redraw()
        res = QtGui.QDialog.exec_(self)
        if not res: return
        if self.mode == TEXT:
            while True:
                file = QtGui.QFileDialog.getSaveFileName(self, 'Export to text file', QtCore.QDir.homePath()+'/blofeld_presets.txt', 'Text files (*.txt);; All files (*)')
                if not file: break
                try:
                    with open(file, 'wb') as of:
                        of.write(self.text)
                    break
                except:
                    QtGui.QMessageBox.critical(self, 'Error saving the file', 'There was a problem saving the file.\nBe sure to have write permissions and sufficient free space for the selected path.')
        while True:
            file = QtGui.QFileDialog.getSaveFileName(self, 'Export to PDF file', QtCore.QDir.homePath()+'/blofeld_presets.pdf', 'PDF files (*.pdf);; All files (*)')
            if not file: break
            try:
                self.output.setOutputFileName(file)
                self.pdf_print()
                break
            except Exception as e:
                print e
                QtGui.QMessageBox.critical(self, 'Error saving the file', 'There was a problem saving the file.\nBe sure to have write permissions and sufficient free space for the selected path.')

    def pdf_print(self):
        painter = QtGui.QPainter()
        painter.begin(self.output)

        painter.setClipRect(self.page.text_rect)
        painter.setFont(self.page.font)
        space = self.page.font_metrics.lineSpacing()
        delta = self.page.text_rect.y() + space
        left = self.page.text_rect.x()
        max_lines = self.page.max_lines
        cols = 0
        l = 0
        for line in self.page.contents:
            if l % max_lines == 0 and l != 0:
                self.output.newPage()
                delta = self.page.text_rect.y() + space
            if isinstance(line, str):
                if l >= 5 and len(line) and self.pagebank_chk.isChecked():
                    self.output.newPage()
                    delta = self.page.text_rect.y() + space
                    l = 0
                painter.drawText(left, delta, line)
                delta += space
            else:
                for c, p in enumerate(line):
                    painter.drawText(left+self.page.prog_size*cols, delta, p)
                    cols += 1
                    if cols == self.page.cols:
                        delta += space
                        cols = 0
            l += 1

        painter.end()


