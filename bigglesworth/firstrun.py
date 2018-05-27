from collections import namedtuple

from Qt import QtCore, QtGui, QtWidgets
from PyQt4.QtGui import QMatrix

Target = namedtuple('Target', 'message widget center event eventWidget')
Target.__new__.__defaults__ = (None, None, None, None)

Left, Top, Right, Bottom = range(4)

events = {v:k for k, v in QtCore.QEvent.__dict__.items() if isinstance(v, int)}

class Bubble(QtWidgets.QWidget):
    arrow = QtGui.QPainterPath()
    arrow.moveTo(6, 0)
    arrow.lineTo(0, -6)
    arrow.lineTo(0, 6)
    arrow.closeSubpath()
    finished = QtCore.pyqtSignal()
    closeRequested = QtCore.pyqtSignal()

    def __init__(self, main, targetWindow):
        QtWidgets.QWidget.__init__(self, targetWindow, QtCore.Qt.Tool|QtCore.Qt.Window|QtCore.Qt.ToolTip|QtCore.Qt.FramelessWindowHint|QtCore.Qt.CustomizeWindowHint)
        self.main = main
        self.matrix = QMatrix()
        self.targetWindow = targetWindow
        self.movePos = None
        self.targetWidget = None
        self.targetEvent = None
        self.targetSignal = None
        self.targetEventWidget = None
        self.count = -1
        self.setStyleSheet('''
            Bubble {
                border: 7px solid black;
                border-radius: 15px;
            }
            ''')

        self.setFixedSize(180, 120)
        layout = QtWidgets.QGridLayout()
        self.setLayout(layout)

        self.label = QtWidgets.QLabel()
        self.label.setWordWrap(True)
        layout.addWidget(self.label)

        self.closeBtn = QtWidgets.QToolButton()
        self.closeBtn.setAutoRaise(True)
        self.closeBtn.clicked.connect(self.closeRequested.emit)
        self.closeBtn.setFocusPolicy(QtCore.Qt.NoFocus)
        self.closeBtn.setIcon(QtGui.QIcon.fromTheme('window-close'))
        layout.addWidget(self.closeBtn, 1, 0, QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)

        self.nextBtn = QtWidgets.QToolButton()
        self.nextBtn.setText('Next')
        self.nextBtn.setLayoutDirection(QtCore.Qt.RightToLeft)
        self.nextBtn.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.nextBtn.setAutoRaise(True)
        self.nextBtn.setIcon(QtGui.QIcon.fromTheme('arrow-right'))
        layout.addWidget(self.nextBtn, 1, 0, QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.nextBtn.clicked.connect(self.nextPage)
        self.shown = False

    @property
    def message(self):
        return self.label.text()

    @message.setter
    def message(self, text):
        self.label.setText(text)

    def start(self):
        self.show()
        self.check()
        self.nextPage()

    def nextPage(self, *args):
        self.count += 1
        if self.count >= len(self.targets):
            self.hide()
            self.finished.emit()
            if self.targetSignal:
                self.targetSignal.disconnect(self.nextPage)
            if self.targetEvent:
                self.targetEventWidget.removeEventFilter(self)
            self.deleteLater()
            return
        if self.targetWidget:
            self.targetWidget.removeEventFilter(self)
        if self.targetSignal:
            self.targetSignal.disconnect(self.nextPage)
        if self.targetEventWidget and self.targetEvent and self.targetEventWidget != self.targetWidget:
            self.targetEventWidget.removeEventFilter(self)
        self.message, self.targetWidget, self.targetPos, targetEvent, self.targetEventWidget = self.targets[self.count]
        if self.targetWidget:
            if not isinstance(self.targetWidget, QtCore.QObject):
                self.targetWidget = self.targetWidget()
            self.check()
            self.targetWidget.installEventFilter(self)
            if targetEvent:
                self.nextBtn.setEnabled(False)
                try:
                    targetEvent.connect(self.nextPage)
                    self.targetSignal = targetEvent
                    self.targetEvent = None
                except:
                    self.targetEvent = targetEvent
                    self.targetSignal = None
                    if not self.targetEventWidget:
                        self.targetEventWidget = self.targetWidget
                    else:
                        self.targetEventWidget.installEventFilter(self)
            else:
                self.nextBtn.setEnabled(True)
                self.targetSignal = None

    def mousePressEvent(self, event):
        self.movePos = event.pos()

    def mouseMoveEvent(self, event):
        if self.movePos:
            self.move(self.pos() + event.pos() - self.movePos)
#            self.update()
            self.remask()

    def mouseReleaseEvent(self, event):
        self.movePos = None

    def setTarget(self, widget):
        self.targetWidget = widget

    def check(self, pos=None):
        if not self.targetWidget:
            if not pos:
                pos = self.targetWindow.pos()
            self.move(pos + self.targetWindow.rect().center() - self.rect().center())
#            self.remask()
        else:
            widgetPos = self.targetWidget.mapToGlobal(QtCore.QPoint())
            widgetRect = QtCore.QRect(widgetPos, self.targetWidget.size())
            if self.targetPos == Left:
                self.move(widgetRect.left() - self.width(), widgetRect.center().y())
            elif self.targetPos == Top:
                self.move(widgetRect.center().x() - self.width() * .5, widgetRect.top() - self.height() - 5)
            elif self.targetPos == Right:
                self.move(widgetRect.right(), widgetRect.center().y())
            elif self.targetPos == Bottom:
                self.move(widgetRect.center().x() - self.width() * .5, widgetRect.bottom() + 5)
            else:
                self.move(self.targetWindow.rect().center() - self.rect().center())
        QtWidgets.QApplication.processEvents()
        self.remask()

    def resizeEvent(self, event):
        self.remask()

    def showEvent(self, event):
        if not self.shown:
            self.shown = True
            self.check()
            self.remask()

    def remask(self):
        pm = QtGui.QPixmap(self.rect().size())
        pm.fill(QtCore.Qt.transparent)
        qp = QtGui.QPainter(pm)
        qp.setBrush(QtCore.Qt.white)
        qp.drawRoundedRect(self.rect().adjusted(6, 6, -7, -7), 8, 8)
        if self.targetWidget:
            r = self.geometry().adjusted(6, 6, -6, -6)
            vector = QtCore.QLineF(self.mapToGlobal(self.rect().center()), self.targetWidget.mapToGlobal(self.targetWidget.rect().center()))
            point = QtCore.QPointF()
            self.matrix.reset()
            if vector.intersect(QtCore.QLineF(r.topLeft(), r.bottomLeft()), point) == QtCore.QLineF.BoundedIntersection:
                point = self.mapFromGlobal(point.toPoint())
                if point.y() < 20:
                    self.matrix.rotate(225)
                    point.setY(8)
                    point.setX(8)
                elif point.y() > r.height() - 6:
                    self.matrix.rotate(135)
                    point.setX(8)
                    point.setY(r.height() + 3)
                else:
                    self.matrix.rotate(180)
            elif vector.intersect(QtCore.QLineF(r.bottomLeft(), r.bottomRight()), point) == QtCore.QLineF.BoundedIntersection:
                point = self.mapFromGlobal(point.toPoint())
                if point.x() < 20:
                    self.matrix.rotate(135)
                    point.setX(8)
                    point.setY(r.height() + 3)
                elif point.x() > r.width() - 6:
                    self.matrix.rotate(45)
                    point.setX(r.width() + 3)
                    point.setY(r.height() + 3)
                else:
                    self.matrix.rotate(90)
            elif vector.intersect(QtCore.QLineF(r.bottomRight(), r.topRight()), point) == QtCore.QLineF.BoundedIntersection:
                point = self.mapFromGlobal(point.toPoint())
                if point.y() < 20:
                    self.matrix.rotate(-45)
                    point.setX(r.width() + 3)
                    point.setY(8)
                elif point.y() > r.height() - 6:
                    self.matrix.rotate(45)
                    point.setX(r.width() + 3)
                    point.setY(r.height() + 3)
            elif vector.intersect(QtCore.QLineF(r.topRight(), r.topLeft()), point) == QtCore.QLineF.BoundedIntersection:
                point = self.mapFromGlobal(point.toPoint())
                if point.x() < 20:
                    self.matrix.rotate(225)
                    point.setY(8)
                    point.setX(8)
                elif point.x() > r.width() - 6:
                    self.matrix.rotate(-45)
                    point.setX(r.width() + 3)
                    point.setY(8)
                else:
                    self.matrix.rotate(270)
            else:
                pass
#                print('what?!')
#            print(vector, r, self.mapFromGlobal(point.toPoint()))
#            print(point)
            qp.translate(point)
#            self.matrix.rotate(-vector.angle())
            qp.drawPath(self.matrix.map(self.arrow))
        qp.end()
        self.setMask(pm.mask())

    
    def eventFilter(self, source, event):
#        print(source, events.get(event.type(), 'Unknown event {}'.format(event.type())))
        if self.targetWidget and source == self.targetWidget and event.type() in (QtCore.QEvent.Move, QtCore.QEvent.Show) and \
            self.count < len(self.targets):
                self.check()
#            print('quiquiqui')
        if self.targetEventWidget and source == self.targetEventWidget:
            if self.targetEvent:
                if event.type() == self.targetEvent:
                    self.nextPage()
        return QtWidgets.QWidget.eventFilter(self, source, event)

    def paintEvent(self, event):
        qp = QtWidgets.QStylePainter(self)
        option = QtWidgets.QStyleOption()
        option.init(self)
        qp.drawPrimitive(QtWidgets.QStyle.PE_Widget, option)
#        if self.targetWidget:
#            qp.setBrush(QtCore.Qt.black)
#            r = self.geometry().adjusted(4, 4, -4, -4)
#            vector = QtCore.QLineF(self.mapToGlobal(self.rect().center()), self.targetWidget.mapToGlobal(self.targetWidget.rect().center()))
#            point = QtCore.QPointF()
#            if vector.intersect(QtCore.QLineF(r.topLeft(), r.bottomLeft()), point) == QtCore.QLineF.BoundedIntersection:
#                print('sx')
#            elif vector.intersect(QtCore.QLineF(r.bottomLeft(), r.bottomRight()), point) == QtCore.QLineF.BoundedIntersection:
#                print('down')
#            elif vector.intersect(QtCore.QLineF(r.bottomRight(), r.topRight()), point) == QtCore.QLineF.BoundedIntersection:
#                print('dx')
#            elif vector.intersect(QtCore.QLineF(r.topRight(), r.topLeft()), point) == QtCore.QLineF.BoundedIntersection:
#                print('top')
#            else:
#                print('what?!')
#            print(vector, r, self.mapFromGlobal(point.toPoint()))
#            qp.drawLine(vector)
#            qp.translate(self.mapFromGlobal(point.toPoint()))
#            self.matrix.reset()
#            self.matrix.rotate(-vector.angle())
#            qp.drawPath(self.matrix.map(self.arrow))

#        qp.translate(self.rect().center().x(), 4)
#        self.matrix.rotate(90)
#        qp.drawPath(self.matrix.map(self.arrow))
#        self.style().drawPrimitive(QtWidgets.QStyle.PE_Widget, option, )


class MainBubble(Bubble):
    def __init__(self, main, targetWindow):
        Bubble.__init__(self, main, targetWindow)
        self.message = 'This is the Librarian, where you can organize all your sounds.'
        self.targets = [
            Target('The Main Library stores <b>every</b> sound you have, including Waldorf\'s factory presets.', targetWindow.rightTabWidget, Left), 
            Target('This is your Blofeld collection, which "mirrors" the contents of your Blofeld.', targetWindow.leftTabWidget, Right), 
            Target('Let\'s review the contents of a factory preset. Click the "+" button and select one of the 3 "Factory Presets"', 
                targetWindow.rightTabWidget.cornerWidget(), Left, targetWindow.rightTabWidget.currentChanged), 
            Target('Every collection contains up to 1024 sounds, you might easily be lost. Filters can help you!', 
                lambda: targetWindow.rightTabWidget.widget(1).filterGroupBox, Bottom), 
            Target('Preset collections are <i>read only</i>, but you can obviously add their sounds to your collections. ' \
                'Just choose one and drag it on the "Blofeld" panel on the left.', 
                lambda: targetWindow.rightTabWidget.widget(1).collectionView, Top, targetWindow.leftTabWidget.widget(0).collectionView.dropEventSignal), 
            Target('Very good, now let\'s dump your Blofeld sounds to the Blofeld library! Click on the tab with the right button', 
                targetWindow.leftTabWidget.tabBar(), Bottom, QtCore.QEvent.ContextMenu), 
            Target('Open the menu "Dump" and select "Dump sounds FROM Blofeld...', targetWindow.leftTabWidget.menu, Left, 
               QtCore.QEvent.Show, main.dumpReceiveDialog), 
            ]


class DumpBubble(Bubble):
    def __init__(self, main, targetWindow):
        Bubble.__init__(self, main, targetWindow)
        self.message = 'This is the dump dialog, here you can import all sounds from your Blofeld.'
        self.targets = [
            Target('Ensure that all banks are selected by clicking on "ALL" in the Banks selector.', 
                targetWindow.banksWidget, Bottom), 
            Target('When dumping the whole collection and "Fast dump" is checked, we use ' \
                'the Blofeld\'s dump system. ' \
                'It will not allow you to block the process, but it will be faster.', 
                targetWindow.fastChk, Bottom), 
            Target('Since we have already added some sounds, we can choose to overwrite them or not...', 
                targetWindow.overwriteChk, Bottom), 
            Target('Everything is done, now we are ready to start the dump process. Press "DUMP" and wait...', 
                targetWindow.dumpBtn, Top, QtCore.QEvent.MouseButtonRelease), 
            ]

class DumpDoneBubble(Bubble):
    def __init__(self, main, targetWindow):
        Bubble.__init__(self, main, targetWindow)
        self.message = ''
        self.targets = [
            Target('The dump process is complete, good! Now you can review which sound keep and which don\'t.', 
                targetWindow.collectionTable, Left), 
            Target('If you are ok with importing the whole library, then press "Import sounds"', 
                targetWindow.okBtn, Top, targetWindow.okBtn.clicked), 
            ]

class PreEditorBubble(Bubble):
    def __init__(self, main, targetWindow):
        Bubble.__init__(self, main, targetWindow)
        self.message = 'Now all sounds are imported and the library is updated. You can see them on the "Blofeld" collection ' \
            'and in the main library, amongst the others.'
        self.targets = [
            Target('If you want to edit a sound, just double click it...', 
                targetWindow.leftTabWidget, Right, targetWindow.soundEditRequested), 
            ]


class EditorBubble(Bubble):
    def __init__(self, main, targetWindow):
        Bubble.__init__(self, main, targetWindow)
        self.message = 'This is the Sound editor window. Cool, isn\'t it?'
        self.targets = [
            Target('boh boh boh', targetWindow.saveFrame, Bottom), 
            ]


class FinalBubble(Bubble):
    def __init__(self, main, targetWindow):
        Bubble.__init__(self, main, targetWindow)
        self.message = ''
        self.targets = [
            Target('Congratulations! You completed the first run wizard, now have fun with Bigglesworth! :-)')
            ]
        self.closeBtn.hide()
        self.nextBtn.setText('Finish')


class FirstRunObject(QtCore.QObject):
    completed = QtCore.pyqtSignal(bool)
    def __init__(self, main):
        QtCore.QObject.__init__(self, main)
        self.main = main
        self.mainWindow = main.mainWindow
        self.editorWindow = main.editorWindow
        self.dumpReceiveDialog = main.dumpReceiveDialog
        self.mainWindow.installEventFilter(self)
        self.editorWindow.installEventFilter(self)
        self.dumpReceiveDialog.installEventFilter(self)

        self.mainBubble = MainBubble(main, self.mainWindow)
        self.mainBubble.closeRequested.connect(self.closeRequested)
        self.mainBubble.show()

        self.dumpBubble = DumpBubble(main, self.dumpReceiveDialog)
        self.dumpBubble.closeRequested.connect(self.closeRequested)
        self.mainBubble.finished.connect(self.dumpBubble.show)

        self.dumpDoneBubble = DumpDoneBubble(main, self.dumpReceiveDialog)
        self.dumpDoneBubble.closeRequested.connect(self.closeRequested)
        self.dumpReceiveDialog.dumpComplete.connect(self.dumpDoneBubble.start)

        self.preEditorBubble = PreEditorBubble(main, self.mainWindow)
        self.preEditorBubble.closeRequested.connect(self.closeRequested)
        self.dumpDoneBubble.finished.connect(self.preEditorBubble.show)

        self.editorBubble = EditorBubble(main, self.editorWindow)
        self.preEditorBubble.finished.connect(self.editorBubble.show)

        self.finalBubble = FinalBubble(main, self.mainWindow)
        self.editorBubble.finished.connect(lambda: [
            self.mainWindow.show(), self.mainWindow.activateWindow(), self.finalBubble.start()])

        self.bubbles = [self.mainBubble, self.dumpBubble, self.dumpDoneBubble, 
            self.preEditorBubble, self.editorBubble, self.finalBubble]

        self.bubbles[-1].finished.connect(self.closeAll)

    def closeRequested(self):
        if QtWidgets.QMessageBox.question(self.sender(), 'Close first-run assistant', 
            'Do you want to close this assistant?\nYou can run it later from the "Help" menu.', 
            QtWidgets.QMessageBox.Ok|QtWidgets.QMessageBox.Cancel
            ) == QtWidgets.QMessageBox.Ok:
                self.closeAll(False)

    def closeAll(self, completed=True):
        try:
            self.dumpReceiveDialog.dumpComplete.disconnect(self.dumpDoneBubble.start)
        except:
            pass
        for bubble in self.bubbles:
            try:
                bubble.deleteLater()
            except:
                pass
        self.deleteLater()
        self.completed.emit(completed)

    def eventFilter(self, source, event):
        if source == self.mainWindow:
            if event.type() == QtCore.QEvent.Move:
                self.mainBubble.check(event.pos())
        elif source == self.main.dumpReceiveDialog:
            if event.type() == QtCore.QEvent.Move:
                self.dumpBubble.check(event.pos())
        elif source == self.editorWindow:
            if event.type() == QtCore.QEvent.Move:
                self.editorBubble.check(event.pos())
        return QtCore.QObject.eventFilter(self, source, event)

