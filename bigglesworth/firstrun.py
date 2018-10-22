import sys

from Qt import QtCore, QtGui, QtWidgets
from PyQt4.QtGui import QMatrix

#Target = namedtuple('Target', 'message widget center event eventWidget')
#Target.__new__.__defaults__ = (None, None, None, None)

Left, Top, Right, Bottom = 1, 2, 4, 8

events = {v:k for k, v in QtCore.QEvent.__dict__.items() if isinstance(v, int)}


class Target(QtCore.QObject):
    def __init__(self, message, targetWidget=None, targetPos=None, targetEvent=None, eventWidget=None, mask=1, maskWidgets=None, actions=None, actionsAfter=None, require=None):
        QtCore.QObject.__init__(self)
        self.message = message
        self.targetWidget = targetWidget
        self.targetPos = targetPos
        self.targetEvent = targetEvent
        self.eventWidget = eventWidget

        self.mask = mask
        if mask == 2 and (not maskWidgets and self.targetWidget):
            self.maskWidgets = [self.targetWidget]
        else:
            self.maskWidgets = maskWidgets

        if actions and not isinstance(actions, (tuple, list)):
            self.actions = [actions]
        else:
            self.actions = actions
        if actionsAfter and not isinstance(actionsAfter, (tuple, list)):
            self.actionsAfter = [actionsAfter]
        else:
            self.actionsAfter = actionsAfter
        self.require = require


class MaskObject(QtWidgets.QWidget):
    maskBrush = QtGui.QColor(192, 192, 192, 128)
    fullMaskBrush = QtGui.QColor(208, 208, 208, 64)

    def __init__(self, parent):
        QtWidgets.QWidget.__init__(self, parent)
        self.target = None
        self.maskWidgets = False

    def showEvent(self, event):
        self.resize(self.parent().size())

    def setTarget(self, target=None, mask=False, maskWidgets=False):
        self.target = target
        if target and (mask or maskWidgets):
#            if isinstance(maskWidgets, (bool, int)):
#                if maskWidgets > 1:
#                    maskWidgets = [target]
#                elif maskWidgets:
#                    maskWidgets = False
            self.maskWidgets = maskWidgets
        else:
            self.maskWidgets = False
        self.updateMask()
        self.update()

    def updateMask(self):
        if not self.target or not self.maskWidgets:
            self.clearMask()
        else:
            mask = QtGui.QRegion(self.rect())
            for widget in self.maskWidgets:
                if not isinstance(widget, QtWidgets.QWidget):
                    widget = widget()
                topLeft = widget.mapTo(self.parent(), QtCore.QPoint())
                mask = mask.subtracted(QtGui.QRegion(QtCore.QRect(topLeft, widget.size())))
            self.setMask(mask)

    def resizeEvent(self, event):
        self.updateMask()
        QtWidgets.QWidget.resizeEvent(self, event)

    def paintEvent(self, event):
        if self.target:
            qp = QtGui.QPainter(self)
            full = QtGui.QRegion(self.rect())
            maskRect = QtCore.QRect(self.target.mapTo(self.parent(), QtCore.QPoint()), self.target.size())
            path = QtGui.QPainterPath()
            path.addRoundedRect(QtCore.QRectF(maskRect), 4, 4)
            mask = full.subtracted(QtGui.QRegion(path.toFillPolygon().toPolygon()))
            qp.setClipRegion(mask)
            qp.fillRect(self.rect(), self.maskBrush)
        elif not self.target or self.target == self.parent():
            qp = QtGui.QPainter(self)
            qp.fillRect(self.rect(), self.fullMaskBrush)


class Bubble(QtWidgets.QWidget):
    arrow = QtGui.QPainterPath()
    arrow.moveTo(6, 0)
    arrow.lineTo(0, -6)
    arrow.lineTo(0, 6)
    arrow.closeSubpath()
    finished = QtCore.pyqtSignal()
    closeRequested = QtCore.pyqtSignal()

    def __init__(self, main, targetWindow):
        QtWidgets.QWidget.__init__(self, targetWindow, QtCore.Qt.WindowStaysOnTopHint|QtCore.Qt.Tool|QtCore.Qt.Window|QtCore.Qt.ToolTip|QtCore.Qt.FramelessWindowHint|QtCore.Qt.CustomizeWindowHint)
        self.main = main
        self.matrix = QMatrix()
        self.targetWindow = targetWindow
        self.currentTarget = None
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
            QToolButton {
                border: 1px solid lightGray;
                border-radius: 4px;
            }
            QToolButton:hover {
                border-color: darkGray;
            }
            ''')

#        self.setFixedSize(180, 120)
        layout = QtWidgets.QGridLayout()
        self.setLayout(layout)

        self.label = QtWidgets.QLabel()
        self.label.setWordWrap(True)
        layout.addWidget(self.label)

        self.closeBtn = QtWidgets.QToolButton()
        layout.addWidget(self.closeBtn, 1, 0, QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.closeBtn.setText('Exit')
        self.closeBtn.setToolTip('Close wizard')
        self.closeBtn.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.closeBtn.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.closeBtn.setAutoRaise(True)
        self.closeBtn.setIcon(QtGui.QIcon.fromTheme('window-close'))
        self.closeBtn.setFocusPolicy(QtCore.Qt.NoFocus)
        self.closeBtn.clicked.connect(self.closeRequested.emit)

        self.nextBtn = QtWidgets.QToolButton()
        layout.addWidget(self.nextBtn, 1, 0, QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.nextBtn.setText('Next')
        self.nextBtn.setToolTip('Proceed to the next step')
        self.nextBtn.setLayoutDirection(QtCore.Qt.RightToLeft)
        self.nextBtn.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.nextBtn.setAutoRaise(True)
        self.nextBtn.setIcon(QtGui.QIcon.fromTheme('arrow-right'))
        self.nextBtn.clicked.connect(self.nextPage)
        self.shown = False

        self.posAnimation = QtCore.QPropertyAnimation(self, b'position')
        self.posAnimation.setDuration(500)
        self.posAnimation.setEasingCurve(QtCore.QEasingCurve(QtCore.QEasingCurve.InOutCubic))
        self.posAnimation.finished.connect(self.remask)

    @QtCore.pyqtProperty(QtCore.QPoint)
    def position(self):
        return self.pos()

    @position.setter
    def position(self, pos):
        self.move(pos)

    @property
    def message(self):
        return self.label.text()

    @message.setter
    def message(self, text):
        self.label.setText(text)

    @property
    def targetPos(self):
        return self.currentTarget.targetPos

    def start(self):
        self.show()
        self.check()
        self.nextPage()

    def nextPage(self, *args):
        self.count += 1
        if self.currentTarget and self.currentTarget.actionsAfter:
            for action in self.currentTarget.actionsAfter:
                action()
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
            self.targetSignal = None
        if self.targetEventWidget and self.targetEvent and self.targetEventWidget != self.targetWidget:
            self.targetEventWidget.removeEventFilter(self)

        self.currentTarget = self.targets[self.count]
        if self.currentTarget.require and not self.currentTarget.require():
            self.targetSignal = self.targetEvent = self.targetWidget = self.targetEventWidget = None
            return self.nextPage()
        self.message = self.currentTarget.message
        self.adjustSize()
#        targetEvent, self.targetEventWidget = self.targets[self.count]
        if not self.currentTarget.targetWidget:
            self.targetWidget = None
            self.check()
            self.nextBtn.setEnabled(self.currentTarget.targetEvent is None)
        elif self.currentTarget.targetWidget:
            if not isinstance(self.currentTarget.targetWidget, QtCore.QObject):
                self.targetWidget = self.currentTarget.targetWidget()
            else:
                self.targetWidget = self.currentTarget.targetWidget
            self.check()
            self.targetWidget.installEventFilter(self)
            if self.currentTarget.targetEvent:
                self.nextBtn.setEnabled(False)
                try:
                    self.currentTarget.targetEvent.connect(self.nextPage)
                    self.targetSignal = self.currentTarget.targetEvent
                    self.targetEvent = None
                except:
                    self.targetEvent = self.currentTarget.targetEvent
                    self.targetSignal = None
                    if not self.currentTarget.eventWidget:
                        self.targetEventWidget = self.targetWidget
                    else:
                        self.targetEventWidget = self.currentTarget.eventWidget
                        self.targetEventWidget.installEventFilter(self)
            else:
                self.nextBtn.setEnabled(True)
                self.targetSignal = None
        if self.currentTarget.actions:
            for action in self.currentTarget.actions:
                try:
                    action()
                except Exception as e:
                    print(e)

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
            pos = pos + self.targetWindow.rect().center() - self.rect().center()
            if self.count < 0:
                self.move(pos)
            else:
                self.posAnimation.setStartValue(self.pos())
                self.posAnimation.setEndValue(pos)
                self.posAnimation.start()
            self.targetWindow.maskObject.setTarget()
#            self.remask()
        else:
            widgetPos = self.targetWidget.mapToGlobal(QtCore.QPoint())
            widgetRect = QtCore.QRect(widgetPos, self.targetWidget.size())
            if self.targetPos is None:
                pos = self.targetWindow.rect().center() - self.rect().center()
            else:
                if self.targetPos & Left:
                    x = widgetRect.left() - self.width()
                elif self.targetPos & Right:
                    x = widgetRect.right()
                else:
                    x = widgetRect.center().x() - self.width() * .5
                if self.targetPos & Top:
                    y = widgetRect.top() - self.height() - 5
                elif self.targetPos & Bottom:
                    y = widgetRect.bottom() + 5
                else:
                    y = widgetRect.center().y()
                pos = QtCore.QPoint(x, y)
            if self.count < 0:
                self.move(pos)
            else:
                self.posAnimation.setStartValue(self.pos())
                self.posAnimation.setEndValue(pos)
                self.posAnimation.start()
#            if self.targetPos == Left:
#                self.move(widgetRect.left() - self.width(), widgetRect.center().y())
#            elif self.targetPos == Top:
#                self.move(widgetRect.center().x() - self.width() * .5, widgetRect.top() - self.height() - 5)
#            elif self.targetPos == Right:
#                self.move(widgetRect.right(), widgetRect.center().y())
#            elif self.targetPos == Bottom:
#                self.move(widgetRect.center().x() - self.width() * .5, widgetRect.bottom() + 5)
#            else:
#                self.move(self.targetWindow.rect().center() - self.rect().center())

            if self.currentTarget.mask:
                self.targetWindow.maskObject.setTarget(self.targetWidget, self.currentTarget.mask, self.currentTarget.maskWidgets)
            else:
                self.targetWindow.maskObject.setTarget()

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


    def sizeHint(self):
        return QtCore.QSize(180, 120)

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
        rightClick = 'Right click '
        if sys.platform == 'darwin':
            rightClick += 'or CTRL+click '
        self.message = 'This is the Librarian, where you can organize all your sounds.'
        self.targets = [
            Target('This is your Blofeld collection, which can "mirror" the contents of your Blofeld.', targetWindow.leftTabWidget, Left), 
            Target('Every "collection" has a filter section that can help you find sounds, for example by filtering a category and a bank.', 
                lambda: targetWindow.leftTabWidget.currentWidget().filterGroupBox, Bottom, 
                actions=lambda: targetWindow.leftTabWidget.currentWidget().catCombo.setCurrentIndex(2),
#                actions=(lambda: targetWindow.leftTabWidget.currentWidget().catCombo.setCurrentIndex(2)), 
                actionsAfter=lambda: targetWindow.leftTabWidget.currentWidget().catCombo.setCurrentIndex(0)), 
            Target('The side library panel contains the full library, storing <b>every</b> available sounds, including Waldorf\'s factory presets.', targetWindow.dockLibrary, Right), 
            Target('Sounds in the side library can be searched by using the tree view.', targetWindow.dockLibrary.treeView, Right, 
                actions=targetWindow.dockLibrary.firstRunExpand), 
            Target('For example, by selecting a preset and a category, you can filter all sounds in that collection matching that filter.', 
                targetWindow.dockLibrary, Right, actions=targetWindow.dockLibrary.firstRunFilter), 
            Target('Once you have found the sounds you have been looking for, the can be dragged to any collection.', 
                lambda: targetWindow.leftTabWidget.currentWidget().collectionView, Left), 
            Target('To rename a sound or change its category, you can enable the "Edit mode" by clicking the small pencil icon in the bottom right corner.', 
                lambda: targetWindow.leftTabWidget.currentWidget().editModeBtn, Left|Top), 
            Target('Single sounds or entire collections can be sent (dumped <i>to</i>) or received (dumped <i>from</i>) their tab menu.', 
                targetWindow.leftTabWidget.tabBar(), Bottom), 
            Target('{} on the tab title to open the context menu.'.format(rightClick), 
                targetWindow.leftTabWidget.tabBar(), Bottom, QtCore.QEvent.ContextMenu, mask=2, require=lambda: all(main.connections)), 
            Target('Open the menu "Dump" and select "Dump sounds FROM Blofeld...', targetWindow.leftTabWidget.menu, Left, 
               QtCore.QEvent.Show, main.dumpReceiveDialog, actions=main.dumpReceiveDialog.createMaskObject, require=lambda: all(main.connections)), 
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
                'It will make the dump faster, but the process cannot be stopped until completion.', 
                targetWindow.fastChk, Bottom), 
            Target('If some sounds are already in the collection, you can choose to overwrite them or not...', 
                targetWindow.overwriteChk, Bottom, mask=2), 
            Target('When a dump is completed, its contents can be reviewed before import. This can be automatically skipped (at your own risk) by selecting "Oirect database import"', 
                targetWindow.directChk, Right), 
            Target('Sometimes the dump process can be too fast if not managed by the Blofeld (see "Fast dump"). '
                'Increasing the "Delay between requests" value might help.', 
                targetWindow.delaySpin, Right), 
            Target('Everything is done, now we are ready to start the dump process. Press "DUMP" and wait...', 
                targetWindow.dumpBtn, Top, QtCore.QEvent.MouseButtonRelease, mask=2), 
            ]

class DumpDoneBubble(Bubble):
    def __init__(self, main, targetWindow):
        Bubble.__init__(self, main, targetWindow)
        self.message = ''
        self.targets = [
            Target('The dump process is complete, good! Now you can review which sound keep and which don\'t.', 
                targetWindow.collectionTable, Left, mask=2), 
            Target('If you are ok with importing the whole library, then press "Import sounds"', 
                targetWindow.okBtn, Top, targetWindow.okBtn.clicked, mask=2), 
            ]

class PreEditorBubble(Bubble):
    def __init__(self, main, targetWindow):
        Bubble.__init__(self, main, targetWindow)
        self.message = 'Now all sounds are imported and the library is updated. You can see them on the "Blofeld" collection ' \
            'and in the main library, amongst the others.'
        self.targets = [
            Target('If you want to edit a sound, just double click it...', 
                lambda: targetWindow.leftTabWidget.currentWidget().collectionView, Left, targetWindow.soundEditRequested, mask=2), 
            ]


class EditorBubble(Bubble):
    def __init__(self, main, targetWindow):
        Bubble.__init__(self, main, targetWindow)
        self.message = 'This is the Sound editor window.<br/><br/>It looks cool, doesn\'t it?'
        self.targets = [
            Target('The top display is similar to the Blofeld one, and also provides information about the current editing', 
                targetWindow.display, Bottom), 
            Target('On the left side of the display you can see the collection used for the current sound and its index', 
                targetWindow.display, Left), 
            Target('The MIDI Panel monitors and manages the current active connections, and can toggle send/receive events', 
                targetWindow.midiWidget, Bottom), 
            Target('The Modulation Matrix is accessible from its dedicated button.<br/>Let\'s try and push it!', 
                targetWindow.modMatrixBtn, Bottom, targetWindow.modMatrixBtn.clicked, mask=2), 
            Target('The Matrix editor shows all available modulation sources and targets, which can be connected by a simple click and drag of your mouse', 
                actions=(QtWidgets.QApplication.processEvents, targetWindow.maskObject.raise_, lambda: targetWindow.modMatrixView.scene().panel.toggleView(False))), 
            Target('Once a modulation has been created, it appears in the "Modulations" list', 
                targetWindow.display, Left, 
                actions=lambda: targetWindow.modMatrixView.scene().modTableDialogProxy.dialog.toggleShade(), 
                actionsAfter=lambda: targetWindow.modMatrixView.scene().modTableDialogProxy.dialog.toggleShade()), 
            Target('This small panel can be used to toggle animations on slow computers, or just close the Modulation Matrix', 
                targetWindow.filterRouting, Bottom, 
                actions=lambda: targetWindow.modMatrixView.scene().panel.toggleView(True), 
                actionsAfter=[targetWindow.hideModMatrix, lambda: targetWindow.modMatrixView.scene().panel.toggleView(False)]), 
            Target('The four envelopes have standard dials to edit their parameters', targetWindow.filterEnvelopeFrame, Top), 
            Target('Each envelope can be edited in a fancier way also. Try clicking on top of the envelope preview', 
                targetWindow.filterEnvelopePreview, Right, maskWidgets=[targetWindow.filterEnvelopePreview], 
                targetEvent=targetWindow.filterEnvelopePreview.clicked), 
            Target('See? You can use the mouse to change position of every control point. Once you\'re done, click the "X" button on the top right corner to close it', 
                targetWindow.filterEnvelopeView, Right|Top, targetEvent=targetWindow.filterEnvelopeView.closeBtn.clicked, 
                maskWidgets=[targetWindow.filterEnvelopeView]), 
            Target('Now, let\'s see the arpeggiator editor: ensure that the Arpeggiator Pattern is set to "User", then click the "Edit" button', 
                targetWindow.arpeggiatorFrame, Top, targetEvent=targetWindow.arpPatternEditBtn.clicked, 
                maskWidgets=(targetWindow.arpeggiatorPattern, targetWindow.arpPatternEditBtn)), 
            Target('As you can see, it is very similar to what you see in your Blofeld. Well. Maybe a bit better, right? ;-)', 
                targetWindow.arpeggiatorDisplay, Top), 
            Target('The bottom side lets you change every aspect of every step', 
                targetWindow.arpeggiatorFrame, Left), 
            Target('You can use the mouse to edit step timing and accents. Play with it, then press the "X" button on the top right corner to close it', 
                targetWindow.arpeggiatorDisplay, Top, targetEvent=targetWindow.arpeggiatorDisplay.closeRequest, 
                maskWidgets=[targetWindow.arpeggiatorDisplay]), 
            Target('Almost done! Whenever you want to save your patch, press the save button '
            '(the one with the floppy disk icon, if you know what a floppy disk is :-D )', 
                targetWindow.saveFrame, Bottom), 
            Target('This can also be done automatically at each change by enabling the "Auto" mode', 
                targetWindow.autosaveBtn, Bottom), 
            Target('Ok, we\'re done here! If you still have some doubts, remember that you can read the manual, available from the "?" menu. Have fun!')
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
    def __init__(self, main, editorOnly=False):
        QtCore.QObject.__init__(self, main)
        self.main = main
        self.settings = QtCore.QSettings()
        self.isCompleted = False
        self.mainWindow = main.mainWindow
        self.editorWindow = main.editorWindow
        self.dumpReceiveDialog = main.dumpReceiveDialog

        self.editorWindow.createMaskObject()
        self.editorWindow.installEventFilter(self)
        self.editorBubble = EditorBubble(main, self.editorWindow)

        self.editorOnly = editorOnly
        if not editorOnly:
            self.mainWindow.createMaskObject()
            self.mainWindow.installEventFilter(self)
            self.dumpReceiveDialog.installEventFilter(self)

            self.mainBubble = MainBubble(main, self.mainWindow)
            self.mainBubble.closeRequested.connect(self.closeRequested)
            self.mainBubble.show()

            self.dumpBubble = DumpBubble(main, self.dumpReceiveDialog)
            self.dumpBubble.closeRequested.connect(self.closeRequested)
    #        self.mainBubble.finished.connect(self.dumpBubble.show)
    #        self.mainBubble.finished.connect(lambda: self.dumpBubble.show() if all(main.connections) else self.preEditorBubble.show())
            self.mainBubble.finished.connect(self.librarianFinished)

            self.dumpDoneBubble = DumpDoneBubble(main, self.dumpReceiveDialog)
            self.dumpDoneBubble.closeRequested.connect(self.closeRequested)
            self.dumpReceiveDialog.dumpComplete.connect(self.dumpDoneBubble.start)

            self.preEditorBubble = PreEditorBubble(main, self.mainWindow)
            self.preEditorBubble.closeRequested.connect(self.closeRequested)
            self.dumpDoneBubble.finished.connect(self.preEditorBubble.show)

            self.preEditorBubble.finished.connect(self.editorBubble.show)

            self.finalBubble = FinalBubble(main, self.mainWindow)

            self.bubbles = [self.mainBubble, self.dumpBubble, self.dumpDoneBubble, 
                self.preEditorBubble, self.editorBubble, self.finalBubble]

            self.editorBubble.finished.connect(lambda: [self.settings.setValue('ShowEditorTutorial', False), 
                self.mainWindow.activate(), self.finalBubble.start()])

        else:

            self.bubbles = [self.editorBubble]

            self.editorBubble.closeRequested.connect(self.closeRequested)
            self.editorBubble.finished.connect(lambda: self.settings.setValue('ShowEditorTutorial', False))

        self.bubbles[-1].finished.connect(self.closeAll)

    def librarianFinished(self):
        if all(self.main.connections):
            self.dumpBubble.show()
            self.dumpDoneBubble.finished.connect(lambda: self.settings.setValue('ShowLibrarianTutorial', False))
        else:
            self.settings.setValue('ShowLibrarianTutorial', False)
            self.preEditorBubble.show()

    def closeRequested(self):
        from bigglesworth.dialogs import QuestionMessageBox
        res = QuestionMessageBox(self.sender(), 'Close first-run wizard', 
            'Do you want to close the first-run wizard?', 
            buttons={QuestionMessageBox.Discard: 'Close and never show again', 
                QuestionMessageBox.Close: 'Close', 
                QuestionMessageBox.Cancel: None
            }).exec_()
        if res == QuestionMessageBox.Discard:
            self.closeAll()
        elif res == QuestionMessageBox.Close:
            self.closeAll(False)
#        if QtWidgets.QMessageBox.question(self.sender(), 'Close first-run assistant', 
#            'Do you want to close this assistant?<br/>You can run it later from the "Help" menu.', 
#            QtWidgets.QMessageBox.Ok|QtWidgets.QMessageBox.Cancel
#            ) == QtWidgets.QMessageBox.Ok:
#                self.closeAll(False)

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
        self.isCompleted = True
#        self.completed.emit(completed)
        self.settings.setValue('FirstRunShown', completed)
        if completed:
            self.settings.setValue('ShowLibrarianTutorial', False)
            self.settings.setValue('ShowEditorTutorial', False)
        try:
            self.mainWindow.destroyMaskObject()
            self.mainWindow.removeEventFilter(self)
        except:
            pass
        try:
            self.dumpReceiveDialog.destroyMaskObject()
            self.dumpReceiveDialog.removeEventFilter(self)
        except:
            pass
        try:
            self.editorWindow.destroyMaskObject()
            self.editorWindow.removeEventFilter(self)
        except:
            pass

    def eventFilter(self, source, event):
        if source == self.mainWindow:
            if event.type() == QtCore.QEvent.Move:
                self.mainBubble.check(event.pos())
        elif source == self.main.dumpReceiveDialog:
            if event.type() == QtCore.QEvent.Move and self.main.dumpReceiveDialog.isVisible():
                self.dumpBubble.check(event.pos())
        elif source == self.editorWindow:
            if event.type() == QtCore.QEvent.Show and not self.editorBubble.isVisible():
                self.editorBubble.show()
            elif event.type() == QtCore.QEvent.Move and self.editorWindow.isVisible():
                self.editorBubble.check(event.pos())
        return QtCore.QObject.eventFilter(self, source, event)

