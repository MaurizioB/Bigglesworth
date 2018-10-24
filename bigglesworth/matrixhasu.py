#!/usr/bin/env python2.7
# *-* encoding: utf-8 *-*

import os

from random import choice, randrange

os.environ['QT_PREFERRED_BINDING'] = 'PyQt4'

from Qt import QtCore, QtGui, QtWidgets

try:
    from bigglesworth.version import __version__
    from bigglesworth.dialogs.about import helpers, contributors, testers, donors
except:
    __version__ = '0.15.2'
    helpers = 'Fabio "Faber" Vescarelli', 'Benedetto Schiavone', 
    contributors = 'Thibault Appourchaux', 
    testers = 'Don Petersen', 
    donors = 'Nick Sherman', 'Piet Wagner'

convMatrix = {
    '"': u'`', 
    '.': u'·', 
    'I': 'I1', 
    'E': 'E\\', 
    'O': 'O0'
}

def _conv(text):
    newText = u''
    for l in text:
        letter = l.upper()
        if letter in convMatrix:
            alt = convMatrix[letter] + convMatrix[letter][0] * 2 * len(convMatrix[letter])
            newText += choice(alt)
        else:
            newText += letter
    return newText


class FontDisplay(QtWidgets.QTableView):
    def __init__(self):
        QtWidgets.QTableView.__init__(self)
        self.model = QtGui.QStandardItemModel()
        self.setModel(self.model)
        sFont = self.font()
        sFont.setBold(True)
        mFont = QtGui.QFont('Matrix Code NFI')
        col = 0
        row0 = []
        row1 = []
        row2 = []
        for c in range(32, 128):
            char = chr(c)
            charItem = QtGui.QStandardItem(str(c))
            normItem = QtGui.QStandardItem(char)
            normItem.setData(sFont, QtCore.Qt.FontRole)
            mItem = QtGui.QStandardItem(char)
            mItem.setData(mFont, QtCore.Qt.FontRole)
            row0.append(charItem)
            row1.append(normItem)
            row2.append(mItem)
            col += 1
            if col >= 16:
                self.model.appendRow(row0)
                self.model.appendRow(row1)
                self.model.appendRow(row2)
                col = 0
                row0 = []
                row1 = []
                row2 = []
        self.resizeRowsToContents()
        self.resizeColumnsToContents()
        self.horizontalHeader().setVisible(False)
        self.verticalHeader().setVisible(False)


class BootCursor(QtWidgets.QGraphicsRectItem):
    def __init__(self, *args, **kwargs):
        QtWidgets.QGraphicsRectItem.__init__(self, *args, **kwargs)
        self.blinkTimer = QtCore.QTimer()
        self.blinkTimer.setInterval(335)
        self.blinkTimer.timeout.connect(lambda: self.setVisible(not self.isVisible()))
        self.blinkTimer.start()
        self.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        self.setBrush(QtGui.QColor(126, 245, 141).lighter(125))

    def setPos(self, *args):
        QtWidgets.QGraphicsRectItem.setPos(self, *args)
        self.blinkTimer.start()
        self.setVisible(True)

    def hide(self):
        self.blinkTimer.stop()
        self.setVisible(False)


class MatrixChar(QtWidgets.QGraphicsSimpleTextItem):
#    color = QtGui.QColor(76, 255, 11)
    baseColor = QtGui.QColor(52, 189, 77)
    highColor = QtGui.QColor(166, 255, 211)
    bootColor = QtGui.QColor(126, 245, 141)
    def __init__(self):
        QtWidgets.QGraphicsSimpleTextItem.__init__(self)
        self.setBrush(self.baseColor)

    def setBootChar(self, char):
        self.setText(char)
        self.setBrush(self.bootColor)

    def setRandomChar(self):
        self.setBrush((self.baseColor, self.highColor)[randrange(2)])
        self.setText(choice(self.chars))

    def setHighlightChar(self, char):
        self.setBrush(self.highColor)
        self.setText(char)

    def setNormalChar(self, char):
        self.setBrush(self.baseColor)
        self.setText(char)

    def setHighlight(self):
        self.setBrush(self.highColor)

    def setNormal(self):
        self.setBrush(self.baseColor)

    def clear(self):
        self.setBrush(self.baseColor)
        self.setText('')


def makeProperty(id):
    attr = 'aniValue{:02}'.format(id)
    def getter(self):
        return getattr(self, attr)
    def setter(self, value):
        setattr(self, attr, value)

    return QtCore.Property(int, getter, setter)


class MatrixScene(QtWidgets.QGraphicsScene):
    cleared = QtCore.Signal()
    viewRect = QtCore.QRectF(16, 8, 1280, 532)

    def __init__(self, view):
        QtWidgets.QGraphicsScene.__init__(self)
        self.view = view

        self.bootFont = QtGui.QFont('Courier')
        self.bootFont.setPointSize(32)
        self.bootFont.setBold(True)
        self.baseFont = QtGui.QFont('Matrix Code NFI')
        self.baseFont.setPointSizeF(32)
        self.baseMetrics = QtGui.QFontMetricsF(self.baseFont)
        widths = []
        self.chars = []
        for c in range(32, 127):
            if c == 64: continue
            char = chr(c)
            self.chars.append(char)
            widths.append(self.baseMetrics.width(char))

        self.baseWidth = int(sum(widths) / len(widths)) + 2
        self.baseHeight = self.baseMetrics.height()
        self.matrix = []
        self.group = QtWidgets.QGraphicsItemGroup()
        self.addItem(self.group)
        self.shadow = QtWidgets.QGraphicsDropShadowEffect()
        self.shadow.setColor(QtGui.QColor(76, 255, 11))
        self.shadow.setOffset(QtCore.QPointF())
        self.shadow.setBlurRadius(15)
        self.group.setGraphicsEffect(self.shadow)
        center = self.viewRect.center()

        #debug only...
#        self.view.setDragMode(self.view.ScrollHandDrag)
#        r = self.addRect(self.viewRect)
#        r.setPen(QtGui.QPen(QtCore.Qt.white))
#        hCenter = self.addLine(0, center.y(), self.viewRect.right(), center.y())
#        hCenter.setPen(r.pen())
#        vCenter = self.addLine(center.x(), 0, center.x(), self.viewRect.bottom())
#        vCenter.setPen(r.pen())

        maxWidth = self.viewRect.width() + self.baseWidth * 2
        maxHeight = self.viewRect.height() + self.baseHeight
        y = 0
        while y < maxHeight:
            x = 0
            rowList = []
            self.matrix.append(rowList)
            while x < maxWidth:
                mChar = MatrixChar()
                mChar.chars = self.chars
                mChar.setFont(self.baseFont)
                rowList.append(mChar)
                mChar.setPos(x, y)
                self.group.addToGroup(mChar)
                x += self.baseWidth
            y += self.baseHeight
        self.rows = len(self.matrix)
        self.columns = len(self.matrix[0])

        last = self.matrix[-1][-1]
        last.setText('0')
        self.cursor = BootCursor(last.boundingRect().translated(0, 4))
        self.addItem(self.cursor)
        self.group.addToGroup(self.cursor)
        groupRect = QtCore.QRectF(0, 0, last.sceneBoundingRect().right(), last.sceneBoundingRect().bottom())
        last.clear()
        self.group.setPos(self.group.pos() + (center - groupRect.center()))

        self.aniColumns = {}
        self.animations = []
        self.activeAnimations = {}
        for index, prop in enumerate(self.props):
            setattr(self, 'aniValue{:02}'.format(index), max(0, randrange(-2, 2)))
            ani = QtCore.QPropertyAnimation(self, 'aniProperty{:02}'.format(index))
            ani.index = index
            self.animations.append(ani)
            self.activeAnimations[ani] = True
            if not randrange(5):
                ani.clearBack = randrange(4, 12)
                ani.setEndValue(self.rows - 1 + ani.clearBack)
            else:
                ani.clearBack = 0
                ani.setEndValue(self.rows - 1)
            ani.setDuration(randrange(100, 2000))
            ani.valueChanged.connect(self.aniChanged)
            ani.finished.connect(self.resetAnimation)
#            ani.finished.connect(self.checkActive)
            self.aniColumns[ani] = randrange(self.columns)

        self.randomCleaner = QtCore.QTimer()
        self.randomCleaner.setInterval(2000)
        self.randomCleaner.timeout.connect(self.clearColumns)

        self.randomChar = QtCore.QTimer()
        self.randomChar.timeout.connect(self.randomize)
        self.randomChar.setInterval(10)

        self.cleaner = QtCore.QTimer()
        self.cleaner.timeout.connect(self.cleanRemaining)
        self.cleaner.setInterval(randrange(50))

        self.clearScene = QtCore.QTimer()
        self.clearScene.timeout.connect(self.clearVisible)
        self.clearScene.setSingleShot(True)
        self.clearScene.setInterval(randrange(100))

        self.currentText = {}
        self.currentRowRange = []
        self.currentColRange = []
        self.columnsDue = set()
        self.visibleText = []
        self.defaultKeepTime = self.keepTime = 2000
        self.defaultBlankTime = self.blankTime = 0

        self.charTimer = QtCore.QTimer()
        self.charTimer.setSingleShot(True)
        self.charTimer.setInterval(22)
        self.charTimer.timeout.connect(self.nextChar)
        for c in range(self.columns):
            self.matrix[1][c].setFont(self.bootFont)

    def writeText(self, line):
        for c in range(self.columns):
            self.matrix[1][c].clear()
        if line:
            self.bootIter = iter(zip(range(3, len(line) + 3), line))
        else:
            self.bootIter = iter([(2, '')])
        self.bootText = line
        self.charTimer.start()

    def nextChar(self):
        try:
            pos, char = self.bootIter.next()
            self.matrix[1][pos].setBootChar(char)
            rect = QtCore.QRectF(self.matrix[1][pos + 1].pos(), self.matrix[2][pos + 2].pos())
#            self.cursor.setPos(rect.right() + rect.width() * .6, rect.top() + rect.height() * .3)
            self.cursor.setPos(rect.left() + rect.width() * .2, rect.top())
            self.charTimer.start()
        except Exception as e:
            print(e)

    def startMatrix(self):
        self.cursor.hide()
        for c in range(2, len(self.bootText) + 1):
            QtCore.QTimer.singleShot(randrange(2000), lambda c=c: [self.matrix[1][c].setFont(self.baseFont), self.matrix[1][c].setRandomChar()])
#            self.matrix[1][c].clear()
#            self.matrix[1][c].setFont(self.baseFont)
        for c in [0, 1] + range(len(self.bootText) + 1, self.columns):
            self.matrix[1][c].setFont(self.baseFont)
        self.randomCleaner.start()
        QtCore.QTimer.singleShot(2000, self.randomChar.start)
#        self.randomChar.start()
        for ani in self.animations:
            QtCore.QTimer.singleShot(randrange(500, 4000), lambda ani=ani: ani.start())

    def restart(self, text, limit=False, keepTime=None, blankTime=None):
        self.keepTime = keepTime if keepTime is not None else self.defaultKeepTime
        self.blankTime = blankTime if blankTime is not None else self.defaultBlankTime
        if not limit:
            colRange = range(self.columns)
        else:
            width = max(len(r) for r in text.split())
            left = (self.columns - width) / 2
            colRange = range(left, left + width)
        for animation in self.animations:
            self.activeAnimations[animation] = True
            if not randrange(5):
                animation.clearBack = randrange(4, 12)
                animation.setEndValue(self.rows - 1 + animation.clearBack)
            else:
                animation.clearBack = 0
                animation.setEndValue(self.rows - 1)
            animation.setDuration(randrange(100, 2000))
#            animation.valueChanged.connect(self.aniChanged)
            animation.finished.disconnect(self.checkActive)
            animation.finished.connect(self.resetAnimation)
#            setattr(self, str(animation.propertyName()), 0)
#            animation.setStartValue(0)
#            animation.setDuration(0)
            self.aniColumns[animation] = choice(colRange)
            QtCore.QTimer.singleShot(randrange(100, 500), lambda animation=animation: animation.start())

        self.currentRowRange = []
        self.currentColRange = []
        self.columnsDue = set()
        self.currentText = {}
        self.visibleText = []

        QtCore.QTimer.singleShot(500, lambda: self.setCurrentText(text, limit))

    def randomize(self):
        row = randrange(self.rows)
        column = randrange(self.columns)
        if not (row, column) in self.currentText:
            self.matrix[row][column].setNormalChar(choice(self.chars))

    def clearColumns(self):
        column = randrange(self.columns)
        startRow = max(0, randrange(-(self.rows / 2), self.rows - 2))
        endRow = min(self.rows, randrange(self.rows))
        for row in range(startRow, endRow):
            if not (row, column) in self.currentText:
                self.matrix[row][column].clear()
        self.randomCleaner.setInterval(randrange(100))

    def clearColumn(self, column):
        for row in range(self.rows):
            charItem = self.matrix[row][column]
            if charItem.text() and (row, column) not in self.currentText:
                QtCore.QTimer.singleShot(randrange(50, 1000), lambda charItem=charItem: charItem.clear())

    def checkActive(self):
        animation = self.sender()
        self.activeAnimations[animation] = False
        if not any(self.activeAnimations.values()):
            self.remaining = []
            for row in range(self.rows):
                for column in range(self.columns):
                    if (row, column) in self.currentText or self.matrix[row][column].text():
                        self.remaining.append((row, column))
            self.cleaner.start()

    def cleanRemaining(self):
        if not self.remaining:
            self.cleaner.stop()
            QtCore.QTimer.singleShot(self.keepTime, self.clearScene.start)
            return
        index = randrange(len(self.remaining))
        row, column = self.remaining[index]
        if (row, column) in self.currentText:
            if randrange(8):
                self.remaining.pop(index)
                text = self.currentText[(row, column)]
            else:
                text = choice(self.chars)
            self.matrix[row][column].setHighlightChar(text)
        else:
            self.remaining.pop(index)
            self.matrix[row][column].clear()
        try:
            self.cleaner.setInterval(randrange(100 / len(self.remaining)))
        except:
            self.cleaner.setInterval(randrange(10))

    def clearVisible(self):
        if not self.visibleText:
            QtCore.QTimer.singleShot(self.blankTime, self.cleared.emit)
#            self.cleared.emit()
        else:
            index = randrange(len(self.visibleText))
            row, column = self.visibleText.pop(index)
            self.matrix[row][column].clear()
            try:
                self.clearScene.setInterval(randrange(100 / len(self.visibleText)))
            except:
                self.clearScene.setInterval(randrange(50))
            self.clearScene.start()

    def resetAnimation(self):
        animation = self.sender()
        column = self.aniColumns[animation]
        for row in range(self.rows):
            if not self.currentText and row not in self.currentRowRange:
                self.matrix[row][column].setNormal()
        if not randrange(5):
            animation.clearBack = randrange(4, 12)
        else:
            animation.clearBack = 0
        duration = randrange(100, 2000)
        if self.currentText:
            if self.randomChar.isActive():
                self.randomChar.stop()
                self.randomCleaner.stop()
            if self.columnsDue:
                duration /= 2
                column = choice(list(self.columnsDue))
                self.columnsDue.discard(column)
                self.aniColumns[animation] = column
#                animation.setStartValue(max(0, randrange(min(self.currentRowRange) - 2)))
                QtCore.QTimer.singleShot(duration + 500 * 2, lambda c=column: self.clearColumn(c))
#                if len(self.columnsDue) < self.columns:
            else:
                animation.finished.disconnect(self.resetAnimation)
                animation.finished.connect(self.checkActive)
            animation.clearBack = 3
            animation.setStartValue(0)
            animation.setEndValue(self.rows + 12)
            QtCore.QTimer.singleShot(randrange(500), animation.start)
        else:
            self.aniColumns[animation] = randrange(self.columns)
            animation.setStartValue(max(0, randrange(-10, self.rows)))
            QtCore.QTimer.singleShot(randrange(500), animation.start)
        animation.setDuration(duration)


    def aniChanged(self, row):
        animation = self.sender()
        column = self.aniColumns[animation]
        if self.currentText and column in self.currentColRange:
            if row < min(self.currentRowRange):
                self.matrix[row][column].setHighlightChar(choice(self.chars))
            elif row in self.currentRowRange:
                if randrange(8):
                    text = self.currentText[(row, column)]
                else:
                    text = choice(self.chars)
                self.matrix[row][column].setHighlightChar(text)
            animation.setEndValue(self.rows - 1)
            animation.clearBack = 3
        else:
            try:
                if animation.state() == animation.Running and randrange(3):
                    self.matrix[row][column].setHighlightChar(choice(self.chars))
            except:
                pass
        if row > 0 and row <= self.rows and (row - 1, column) not in self.currentText:
            self.matrix[row - 1][column].setNormal()
        if animation.clearBack:
            if not (row - animation.clearBack, column) in self.currentText:
                try:
                    self.matrix[row - animation.clearBack][column].clear()
                except:
                    pass


#    def _aniChanged(self, row):
#        animation = self.sender()
#        column = self.aniColumns[animation]
#        if self.currentText:
#            if row in self.currentRowRange and column in self.currentColRange:
#                char = self.currentText[(row, column)]
#            elif row == animation.endValue():
#                try:
#                    animation.finished.disconnect()
#                except:
#                    pass
#                if self.columnsDue and column not in self.columnsDue:
#                    newColumn = choice(list(self.columnsDue))
#                    self.columnsDue.discard(newColumn)
#                    self.aniColumns[animation] = newColumn
#                    animation.stop()
#                    animation.setStartValue(0)
#                    animation.setEndValue(max(self.currentRowRange))
#                    animation.start()
#                else:
#                    animation.stop()
#                return
#            else:
#                charId = randrange(32, 126)
#                if charId == 64:
#                    charId += 1
#                char = chr(charId)
#        else:
#            charId = randrange(32, 126)
#            if charId == 64:
#                charId += 1
#            char = chr(charId)
#        try:
#            current = self.matrix[row][column]
#            current.setText(char)
#            current.setBrush(MatrixChar.highColor)
#        except:
#            pass
#        if row > 0:
#            if self.currentText and row - 1 in self.currentRowRange:
#                return
#            try:
#                self.matrix[row - 1][column].setBrush(MatrixChar.baseColor)
#            except:
#                pass
#            if animation.clearBack and row - animation.clearBack >= 0 and not (self.currentText and row - animation.clearBack in self.currentRowRange):
#                try:
#                    self.matrix[row - animation.clearBack][column].setText('')
#                except:
#                    pass

    def center(self, line):
        if len(line) & 1 and ' ' in line:
            spaces = line.count(' ')
            splitted = line.split()
            if spaces & 1 and spaces >= 1:
                centerSpace = spaces / 2 + 1
                line = ' '.join(splitted[:centerSpace]) + '  ' + ' '.join(splitted[centerSpace:])
            elif spaces and not spaces & 1:
                if spaces == 1:
                    line = '  '.join(splitted)
                else:
                    center = len(line) / 2
                    wordPos = 1
                    while len(' '.join(splitted[:wordPos])) < center:
                        wordPos += 1
                    if wordPos < spaces - 2:
                        asBefore = len(' '.join(splitted[:wordPos - 1]))
                        asAfter = len(' '.join(splitted[:wordPos]))
                        if center - asBefore < asAfter - center:
                            wordPos -= 1
                    line = ' '.join(splitted[:wordPos]) + '  ' + ' '.join(splitted[wordPos:])
        return line

    def setCurrentText(self, text, limit=False):
        if not text:
            self.currentText = {}
            return
#        lines = text.split('\n')
        lines = [self.center(line) for line in text.splitlines()]
        maxWidth = max(len(l) for l in lines)
        left = (self.columns - maxWidth) / 2
        startLine = (self.rows - len(lines)) / 2
#        print(self.columns, self.rows)
#        if not self.rows & 1 and not len(lines) & 1:
#            startLine -= 1
        self.currentRowRange = range(startLine, startLine + len(lines))
        self.currentColRange = range(left, left + maxWidth)
        self.columnsDue = set(range(self.columns) if not limit else self.currentColRange)
        self.currentText = {}
        self.visibleText = []
        for l, line in enumerate(lines, startLine):
            for c, char in enumerate(line.center(maxWidth, ' '), left):
                self.currentText[(l, c)] = char
                if char:
                    self.visibleText.append((l, c))


    aniProperty00 = makeProperty(0)
    aniProperty01 = makeProperty(1)
    aniProperty02 = makeProperty(2)
    aniProperty03 = makeProperty(3)
    aniProperty04 = makeProperty(4)
    aniProperty05 = makeProperty(5)
    aniProperty06 = makeProperty(6)
    aniProperty07 = makeProperty(7)
    aniProperty08 = makeProperty(8)
    aniProperty09 = makeProperty(9)
    aniProperty10 = makeProperty(10)
    aniProperty11 = makeProperty(11)
    aniProperty12 = makeProperty(12)
    aniProperty13 = makeProperty(13)
    aniProperty14 = makeProperty(14)
    aniProperty15 = makeProperty(15)
    aniProperty16 = makeProperty(16)
    aniProperty17 = makeProperty(17)
    aniProperty18 = makeProperty(18)
    aniProperty19 = makeProperty(19)
#    aniProperty20 = makeProperty(20)
#    aniProperty21 = makeProperty(21)
#    aniProperty22 = makeProperty(22)
#    aniProperty23 = makeProperty(23)
#    aniProperty24 = makeProperty(24)
    props = [aniProperty00, aniProperty01, aniProperty02, aniProperty03, 
        aniProperty04, aniProperty05, aniProperty06, aniProperty07, 
        aniProperty08, aniProperty09, aniProperty10, aniProperty11, 
        aniProperty12, aniProperty13, aniProperty14, aniProperty15, 
        aniProperty16, aniProperty17, aniProperty18, aniProperty19, ]
#        aniProperty20, aniProperty21, aniProperty22, aniProperty23, aniProperty24]



class MatrixView(QtWidgets.QGraphicsView):
    def resizeEvent(self, event):
        self.fitInView(self.scene().viewRect, QtCore.Qt.KeepAspectRatio)
#        self.centerOn(self.scene().viewRect.center())

#    def paintEvent(self, event):
#        qp = QtGui.QPainter(self.viewport())
#        qp.setPen(QtCore.Qt.white)
#        qp.drawRect()
#

class MatrixHasU(QtWidgets.QDialog):
    shown = False

    def __init__(self, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        QtGui.QFontDatabase.addApplicationFont(':/fonts/MatrixCodeNFImod.ttf')
        l = QtWidgets.QGridLayout()
        self.setLayout(l)
        self.setContentsMargins(0, 0, 0, 0)
        l.setContentsMargins(0, 0, 0, 0)
        self.matrixView = MatrixView()
        self.matrixScene = MatrixScene(self.matrixView)
        self.matrixScene.setSceneRect(-1000, -1000, 5000, 5000)
        l.addWidget(self.matrixView)
        self.matrixView.setRenderHints(QtGui.QPainter.Antialiasing)
        self.matrixView.setScene(self.matrixScene)
        self.matrixView.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.matrixView.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.matrixView.setFrameShape(0)
        self.matrixView.setBackgroundBrush(QtGui.QBrush(QtGui.QColor(QtCore.Qt.black)))

        self.slides = [
        _conv(u'Welcome to the mod matrix...'), 
        ('B1GGLESWORTH', True, 4000), 
        (_conv('Version\n' + __version__)), 
        (_conv('CREATED BY\nM4URIZIO BeRTI')), 
        (_conv('THANKS TO\n\n' + '\n'.join(helpers)), True), 
        (_conv('Contributors\n' + '\n'.join(contributors)), True), 
        (_conv('Testers\n' + '\n'.join(testers)), True), 
        (_conv('donors\n' + '\n'.join(donors)), True), 
        (_conv(u'Kudos to\nThe people at Synth Cafe\nand all the users...'), False, 4000, 4000), 
        (_conv(u'Ok. now go back to work_\nand do some fine patches...'), True, 2000, 8000), 
        _conv(u'Seriously.\nWe are done here.'), 
        (_conv(u'ok. Since you\'re doing nothing\nI would suggest to make a donation...'), False, 6000, 6000), 
        (_conv(u'Ok. Have fun.\nI will leave you to this blank screen.\n\nBye'), True, 4000), 
        ]
        self.currentSlide = -1

        self.lineTimer = QtCore.QTimer()
        self.lineTimer.setSingleShot(True)
        self.lineTimer.setInterval(5000)
        self.lineTimer.timeout.connect(self.updateLines)
        self.matrixScene.cleared.connect(self.lineTimer.start)
#        self.fontDisplay = FontDisplay()
#        self.fontDisplay.show()

        locale = QtCore.QLocale()
        dateFormat = locale.dateFormat(locale.ShortFormat)
        if dateFormat.lower().startswith('y'):
            fmt = 'yy-dd-MM hh:mm:ss'
        elif dateFormat.lower().startswith('m'):
            fmt = 'M-d-yy hh:mm:ss'
        else:
            fmt = 'd-M-yy hh:mm:ss'
        bootLines = [
        ('', 6700), 
        ('Call trans opt: received. {} REC:Log>'.format(QtCore.QDateTime.currentDateTime().toString(fmt)), 3500), 
        ('WARNING: carrier wave anomaly', 5000), 
        ('Trace program: running', 5000), 
        ('SYSEX FAILURE', 4000), 
        ]

        self.bootWaiter = QtCore.QTimer()
        self.bootWaiter.setSingleShot(True)
        self.bootWaiter.timeout.connect(self.boot)
        self.bootLines = iter(bootLines)

    def boot(self):
        try:
            text, interval = self.bootLines.next()
            self.matrixScene.writeText(text)
            self.bootWaiter.setInterval(interval)
            self.bootWaiter.start()
        except Exception as e:
            print(e)
            self.matrixScene.startMatrix()
            self.lineTimer.start()

    def updateLines(self):
        self.currentSlide += 1
        try:
            if not self.currentSlide:
                self.matrixScene.setCurrentText(self.slides[self.currentSlide])
                self.lineTimer.setInterval(500)
            else:
                data = self.slides[self.currentSlide]
                if isinstance(data, (str, unicode)):
                    self.matrixScene.restart(data)
                else:
                    self.matrixScene.restart(*data)
        except:
            pass

    def showEvent(self, event):
        if not self.shown:
            self.shown = True
            desktop = QtWidgets.QDesktopWidget()
            rect = desktop.availableGeometry()
            width = rect.width() * .8
            height = width / 2.40
            self.setFixedSize(width, height)
            self.move(rect.center().x() - width / 2, rect.center().y() - height / 2)
            self.matrixView.fitInView(self.matrixScene.viewRect, QtCore.Qt.KeepAspectRatio)
            self.boot()


if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)
    w = MatrixHasU()
    w.show()
    sys.exit(app.exec_())
