# *-* coding: utf-8 *-*

from PyQt4 import QtCore, QtGui

from bigglesworth.const import categories, CatRole, local_path

class MagnifyingCursor(QtGui.QCursor):
    def __init__(self):
        pixmap = QtGui.QPixmap(local_path('magnifying-glass.png'))
        QtGui.QCursor.__init__(self, pixmap)


class LineCursor(QtGui.QCursor):
    def __init__(self):
        pixmap = QtGui.QPixmap(16, 16)
        pixmap.fill(QtCore.Qt.transparent)
        qp = QtGui.QPainter(pixmap)
        qp.setRenderHints(QtGui.QPainter.Antialiasing)
        qp.setPen(QtGui.QPen(QtCore.Qt.black, 2))
        qp.translate(.5, .5)
        qp.drawLine(0, 4, 12, 14)
        qp.end()
        QtGui.QCursor.__init__(self, pixmap, 0, 0)


class FreeDrawIcon(QtGui.QIcon):
    def __init__(self):
        pixmap = QtGui.QPixmap(12, 12)
        pixmap.fill(QtCore.Qt.transparent)
        qp = QtGui.QPainter(pixmap)
        qp.setRenderHints(QtGui.QPainter.Antialiasing)
        qp.setPen(QtGui.QPen(QtCore.Qt.black, 1))
        qp.translate(.5, .5)
        path = QtGui.QPainterPath()
        path.arcTo(0, -2.5, 5, 5, 180, 90)
        path.arcTo(0, 2.5, 8, 12.5, 90, -90)
        path.lineTo(11, 5)
        qp.drawPath(path)
        qp.end()
        QtGui.QIcon.__init__(self, pixmap)


class LineDrawIcon(QtGui.QIcon):
    def __init__(self):
        pixmap = QtGui.QPixmap(12, 12)
        pixmap.fill(QtCore.Qt.transparent)
        qp = QtGui.QPainter(pixmap)
        qp.setRenderHints(QtGui.QPainter.Antialiasing)
        qp.setPen(QtGui.QPen(QtCore.Qt.black, 1))
        qp.translate(.5, .5)
        qp.drawLine(0, 0, 11, 11)
        qp.end()
        QtGui.QIcon.__init__(self, pixmap)


class CurveDrawIcon(QtGui.QIcon):
    def __init__(self):
        pixmap = QtGui.QPixmap(12, 12)
        pixmap.fill(QtCore.Qt.transparent)
        qp = QtGui.QPainter(pixmap)
        qp.setRenderHints(QtGui.QPainter.Antialiasing)
        qp.setPen(QtGui.QPen(QtCore.Qt.black, 1))
        qp.translate(.5, .5)
        qp.drawArc(0, -11, 22, 22, 2880, 1440)
        qp.end()
        QtGui.QIcon.__init__(self, pixmap)


class DirCursorClass(QtGui.QCursor):
    limit_pen = QtGui.QPen(QtCore.Qt.black, 2)
    limit_pen.setCapStyle(QtCore.Qt.RoundCap)
    arrow_pen = QtGui.QPen(QtCore.Qt.black, 1)
    arrow_pen.setCapStyle(QtCore.Qt.RoundCap)
    brush = QtGui.QBrush(QtCore.Qt.black)


class UpCursorClass(DirCursorClass):
    def __init__(self):
        pixmap = QtGui.QPixmap(32, 32)
        pixmap.fill(QtCore.Qt.transparent)
        qp = QtGui.QPainter(pixmap)
        qp.setRenderHints(QtGui.QPainter.Antialiasing)
        qp.translate(.5, .5)
        qp.setPen(self.limit_pen)
        qp.drawLine(0, 1, 15, 1)
        qp.setPen(self.arrow_pen)
        qp.setBrush(self.brush)
        path = QtGui.QPainterPath()
        path.moveTo(7.5, 1)
        path.lineTo(12, 8)
        path.lineTo(3, 8)
        path.closeSubpath()
        qp.drawPath(path)
        del qp
        DirCursorClass.__init__(self, pixmap, 8, 1)


class DownCursorClass(DirCursorClass):
    def __init__(self):
        pixmap = QtGui.QPixmap(32, 32)
        pixmap.fill(QtCore.Qt.transparent)
        qp = QtGui.QPainter(pixmap)
        qp.setRenderHints(QtGui.QPainter.Antialiasing)
        qp.translate(.5, .5)
        qp.setPen(self.limit_pen)
        qp.drawLine(0, 8, 15, 8)
        qp.setPen(self.arrow_pen)
        qp.setBrush(self.brush)
        path = QtGui.QPainterPath()
        path.moveTo(3, 1)
        path.lineTo(12, 1)
        path.lineTo(7.5, 7)
        path.closeSubpath()
        qp.drawPath(path)
        del qp
        DirCursorClass.__init__(self, pixmap, 8, 8)


class LeftCursorClass(DirCursorClass):
    def __init__(self):
        pixmap = QtGui.QPixmap(32, 32)
        pixmap.fill(QtCore.Qt.transparent)
        qp = QtGui.QPainter(pixmap)
        qp.setRenderHints(QtGui.QPainter.Antialiasing)
        qp.translate(.5, .5)
        qp.setPen(self.limit_pen)
        qp.drawLine(1, 0, 1, 15)
        qp.setPen(self.arrow_pen)
        qp.setBrush(self.brush)
        path = QtGui.QPainterPath()
        path.moveTo(1, 7.5)
        path.lineTo(8, 12)
        path.lineTo(8, 3)
        path.closeSubpath()
        qp.drawPath(path)
        del qp
        DirCursorClass.__init__(self, pixmap, 1, 8)


class RightCursorClass(DirCursorClass):
    def __init__(self):
        pixmap = QtGui.QPixmap(32, 32)
        pixmap.fill(QtCore.Qt.transparent)
        qp = QtGui.QPainter(pixmap)
        qp.setRenderHints(QtGui.QPainter.Antialiasing)
        qp.translate(.5, .5)
        qp.setPen(self.limit_pen)
        qp.drawLine(8, 0, 8, 15)
        qp.setPen(self.arrow_pen)
        qp.setBrush(self.brush)
        path = QtGui.QPainterPath()
        path.moveTo(1, 3)
        path.lineTo(1, 12)
        path.lineTo(7, 7.5)
        path.closeSubpath()
        qp.drawPath(path)
        del qp
        DirCursorClass.__init__(self, pixmap, 8, 8)


class NameDelegate(QtGui.QStyledItemDelegate):
    def __init__(self, parent=None):
        QtGui.QStyledItemDelegate.__init__(self, parent)
        self.commitData.connect(self.set_data)

    def createEditor(self, parent, option, index):
        self.proxy = index.model()
        self.index = self.proxy.mapToSource(index)
        edit = QtGui.QLineEdit(parent)
        edit.setValidator(QtGui.QRegExpValidator(QtCore.QRegExp('[\x20-\x7f°]*')))
        edit.setMaxLength(16)
        return edit

    def set_data(self, widget):
        self.index.model().sound(self.index).name = str(widget.text().toUtf8())


class CategoryDelegate(QtGui.QStyledItemDelegate):
    def __init__(self, parent=None):
        QtGui.QStyledItemDelegate.__init__(self, parent)
        self.commitData.connect(self.set_data)

    def createEditor(self, parent, option, index):
        self.proxy = index.model()
        self.index = self.proxy.mapToSource(index)
        combo = QtGui.QComboBox(parent)
        model = QtGui.QStandardItemModel()
        [model.appendRow(QtGui.QStandardItem(cat)) for cat in categories]
        combo.setModel(model)
        combo.setCurrentIndex(index.data(CatRole).toPyObject())
        combo.activated.connect(lambda i: parent.setFocus())
        return combo

    def set_data(self, widget):
        sound = self.index.model().sound(self.index)
        if sound.cat == widget.currentIndex(): return
        self.index.model().sound(self.index).cat = widget.currentIndex()

