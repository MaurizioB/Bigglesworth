from Qt import QtCore, QtGui, QtWidgets


class SelectorWidget(QtWidgets.QFrame):
    colors = (QtCore.Qt.white, QtCore.Qt.black), (QtCore.Qt.darkGray, QtCore.Qt.white)
    itemsChanged = QtCore.pyqtSignal(object)

    def __init__(self, parent, count=16, allText='ALL', names=None):
        QtWidgets.QFrame.__init__(self, parent)
        self._items = set()
        self.clickState = True
        self.setStyleSheet('''
            QFrame {
                border-radius: 2px;
                border-top: 1px solid palette(dark);
                border-left: 1px solid palette(dark);
                border-right: 1px solid palette(midlight);
                border-bottom: 1px solid palette(midlight);
                background: rgb(240, 240, 240);
            }
            ''')
        if count & 1:
            count += 1
        self.count = count
        self.half = count // 2
        self.allText = allText
        if not names:
            self.names = {i:str(i + 1) for i in range(count)}
        else:
            if isinstance(names, dict):
                self.names = names
            else:
                self.names = {i:v for i, v in enumerate(names)}
        self.rebuild()

    def rebuild(self):
        self.allFont = self.font()
        height = self.height()
        self.halfHeight = height * .5
        self.allFont.setPointSize(self.halfHeight - 3)
        self.itemFont = self.font()
        self.itemFont.setPointSize(height * .35)
        self.hRatio = (self.width() - 1) / (float(self.half) + 3)
        self.left = left = self.hRatio * 3 + 1
        self.allRect = QtCore.QRect(0, 0, left, height)
        topRects = []
        bottomRects = []
        for p in range(self.half):
            topRects.append(QtCore.QRect(left + 1, 0, self.hRatio, self.halfHeight).adjusted(1, 2, -1, -1))
            bottomRects.append(QtCore.QRect(left + 1, self.halfHeight, self.hRatio, self.halfHeight).adjusted(1, 2, -1, -1))
            left += self.hRatio
        self.itemRects = topRects + bottomRects

    def changeEvent(self, event):
        if event.type() == QtCore.QEvent.FontChange:
            self.rebuild()
        return QtWidgets.QFrame.changeEvent(self, event)

    def sizeHint(self):
        return QtCore.QSize(150, 30)

    def resizeEvent(self, event):
#        width = self.width()
#        height = self.height()
#        if width > height * 5:
#            height = width * .2
#        elif width < height * 5:
#            width = height * 5
#        self.resize(width, height)
        self.rebuild()

    @property
    def items(self):
        return set(self._items)

    def addItem(self, item):
        if item in self._items:
            return
        self._items.add(item)
        self.itemsChanged.emit(self._items)

    def removeItem(self, item):
        if item not in self._items:
            return
        self._items.discard(item)
        self.itemsChanged.emit(self._items)

    def setItems(self, items=None):
        if items is None:
            self._items = set()
        elif isinstance(items, int):
            self._items = set([items])
        elif isinstance(items, (tuple, list)):
            self._items = set(items)
        elif isinstance(items, set):
            self._items = items
        else:
            return
        self.update()
        self.itemsChanged.emit(set(self._items))

    def setAll(self):
        self.setItems(range(self.count))

    def isFull(self):
        return len(self._items) == self.count

    def mousePressEvent(self, event):
        pos = event.pos()
        if pos in self.allRect:
            if len(self._items) == self.count:
                self.setItems()
            else:
                self.setAll()
            self.update()
            self.currentRect = None
            return
        for c, rect in enumerate(self.itemRects):
            if pos in rect.adjusted(-1, -1, 1, 1):
                if c in self._items:
                    self.removeItem(c)
                    self.clickState = False
                else:
                    self.addItem(c)
                    self.clickState = True
                self.update()
                return
        self.currentRect = None

    def mouseMoveEvent(self, event):
        pos = event.pos()
        for c, rect in enumerate(self.itemRects):
            if pos in rect.adjusted(-1, -1, 1, 1):
                if self.clickState:
                    self.addItem(c)
                else:
                    self.removeItem(c)
                self.update()
                break

    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        qp.setRenderHints(qp.Antialiasing)
        qp.translate(.5, .5)
        qp.setFont(self.allFont)
        height = self.height()

        basePen = qp.pen()
        qp.setFont(self.itemFont)
        if self.isFull():
            brush, pen = self.colors[1]
            qp.setBrush(brush)
            qp.setPen(QtCore.Qt.NoPen)
            qp.drawRect(self.allRect.adjusted(2, 2, -2, -2))
            qp.setPen(pen)
            qp.drawText(self.allRect, QtCore.Qt.AlignCenter, self.allText)
            for c, rect in enumerate(self.itemRects):
                qp.setPen(QtCore.Qt.NoPen)
                qp.setBrush(brush)
                qp.drawRect(rect)
                qp.setPen(pen)
                qp.drawText(rect, QtCore.Qt.AlignCenter, self.names[c])
        else:
            qp.drawText(self.allRect, QtCore.Qt.AlignCenter, self.allText)
            for c, rect in enumerate(self.itemRects):
                brush, pen = self.colors[c in self._items]
                qp.setPen(QtCore.Qt.NoPen)
                qp.setBrush(brush)
                qp.drawRect(rect)
                qp.setPen(pen)
                qp.drawText(rect, QtCore.Qt.AlignCenter, self.names[c])

        qp.setPen(basePen)
        qp.drawLine(self.left, self.halfHeight, self.width(), self.halfHeight)
        left = self.left
        for l in range(self.half):
            qp.drawLine(left, 0, left, height)
            left += self.hRatio


class MidiChannelWidget(SelectorWidget):
    def __init__(self, parent):
        SelectorWidget.__init__(self, parent, allText='OMNI')
        self.setChannels = self.setItems


class BanksSelectionWidget(SelectorWidget):
    def __init__(self, parent):
        SelectorWidget.__init__(self, parent, count=8, names = 'ABCDEFGH')



