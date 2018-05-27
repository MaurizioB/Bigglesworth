# *-* coding: utf-8 *-*

from random import randrange
from collections import namedtuple

from Qt import QtCore, QtGui, QtWidgets, QtSql

from bigglesworth.utils import loadUi, localPath, getName, getChar, Enum, setBold
from bigglesworth.const import (chr2ord, UidColumn, LocationColumn, 
    INIT, IDW, IDE, SNDP, END, templateGroupDict)
from bigglesworth.parameters import Parameters, fullRangeCenterZero, driveCurves, arpLength, ctrl2sysex
from bigglesworth.widgets import SoundsMenu, EditorMenu, EnvelopeView
from bigglesworth.dialogs import RandomDialog, InputMessageBox, TemplateManager, SaveSoundAs, WarningMessageBox
from bigglesworth.midiutils import NoteOffEvent, NoteOnEvent, CtrlEvent, ProgramEvent, SysExEvent, SYSEX, CTRL, NOTEON, NOTEOFF, PROGRAM

from combo import Combo
from squarebutton import SquareButton
from dial import Dial
from slider import Slider
from frame import Frame

Combo.setRange = lambda *args: None
Combo.setValueList = lambda self, valueList: self.combo.addItems(valueList)
Combo.setValue = lambda self, value: self.combo.setCurrentIndex(value)
Combo.valueChanged = Combo.currentIndexChanged
SquareButton.setRange = lambda *args: None
SquareButton.setValueList = lambda *args: None
SquareButton.setValue = SquareButton.setSwitched
SquareButton.valueChanged = SquareButton.switchToggled

_efxNamedTuple = namedtuple('efx', 'efxId efxParamId efxNames valueList altValueData')
_efxNamedTuple.__new__.__defaults__ = (None, None)
_effects = [
    _efxNamedTuple((1, 2), 1, (
        ('Chorus', 'Speed'), 
        ('Flanger', 'Speed'), 
        ('Phaser', 'Speed'), 
        ('Triple', 'Speed'), 
        )), 
    _efxNamedTuple((1, 2), 2, (
        ('Chorus', 'Depth'), 
        ('Flanger', 'Depth'), 
        ('Phaser', 'Depth'), 
        ('Overdrive', 'Drive'), 
        ('Triple', 'Depth'), 
        )), 
    _efxNamedTuple((1, 2), 3, (
        ('Overdrive', 'PostGain'), 
        )), 
    _efxNamedTuple((1, 2), 4, (
        ('Triple', 'ChorusMix'), 
        )), 
    _efxNamedTuple((1, 2), 5, (
        ('Flanger', 'Feedback'), 
        ('Phaser', 'Feedback'), 
        ('Triple', 'SampleHold'), 
        )), 
    _efxNamedTuple((1, 2), 6, (
        ('Phaser', 'Center'), 
        ('Overdrive', 'Cutoff'), 
        ('Triple', 'Overdrive'), 
        )), 
    _efxNamedTuple((1, 2), 7, (
        ('Phaser', 'Spacing'), 
        )), 
    _efxNamedTuple((2, ), 8, (
        ('Reverb', 'Diffusion'), 
        )), 
    _efxNamedTuple((1, 2), 9, (
        ('Flanger', 'Polarity'), 
        ('Phaser', 'Polarity'), 
        ('Delay', 'Polarity'), 
        ('ClkDelay', 'Polarity'), 
        ('Reverb', 'Damping'), 
        ), 
            ['positive', 'negative'], 
            {'Damping': []}
        ), 
    _efxNamedTuple((1, 2), 10, (
        ('Overdrive', 'Curve'), 
        ('Delay', 'Spread'), 
        ('ClkDelay', 'Spread')
        ), 
            fullRangeCenterZero, 
            {'Curve': driveCurves[:12]}
        ), 
    _efxNamedTuple((2, ), 11, (
        ('ClkDelay', 'Length'), 
        ), 
            arpLength[:30], 
        ), 
    ]


MidiIn, MidiOut = Enum(2)


class FilterRoutingDisplay(QtWidgets.QWidget):
    paralPath = QtGui.QPainterPath()
    paralPath.moveTo(-2.5, -5)
    paralPath.lineTo(2.5, 0)
    paralPath.lineTo(-2.5, 5)

    serialPath = QtGui.QPainterPath()
    serialPath.moveTo(-5, -2.5)
    serialPath.lineTo(0, 2.5)
    serialPath.lineTo(5, -2.5)

    routingPaths = paralPath, serialPath

    pen = QtGui.QPen(QtCore.Qt.black, 2)
    hPen = QtGui.QPen(QtCore.Qt.darkGray, 2)
    def __init__(self, filtersFrame):
        QtWidgets.QWidget.__init__(self)
        self.filtersFrame = filtersFrame
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.routing = 0
        self.mainTimer = QtCore.QBasicTimer()
        self.mainTimer.start(1000, self)
        self.focusArrow = -1
        self.aniTimer = QtCore.QBasicTimer()
#        self.aniTimer.setInterval(500)
#        self.aniTimer.timeout.connect(self.animate)

    def changeEvent(self, event):
        if event.type() == QtCore.QEvent.PaletteChange:
            self.pen.setColor(self.palette().color(QtGui.QPalette.Active, QtGui.QPalette.WindowText))
            self.hPen.setColor(self.palette().color(QtGui.QPalette.Disabled, QtGui.QPalette.WindowText))

    def timerEvent(self, event):
        if event.timerId() == self.mainTimer.timerId():
            self.mainTimer.stop()
            self.maxArrow = self.height() / 80
            self.focusArrow = 0
            self.aniTimer.start(80, self)
            self.update()
        elif event.timerId() == self.aniTimer.timerId():
            self.focusArrow += 1
            if self.focusArrow >= self.maxArrow:
                self.aniTimer.stop()
                self.mainTimer.start(1000, self)
            self.update()

    def setRouting(self, routing):
        self.routing = routing
        if self.aniTimer.isActive():
            self.aniTimer.stop()
        self.mainTimer.start(200, self)
        self.update()

    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        qp.setRenderHints(qp.Antialiasing)
        divPos = self.height() / 80
        posMulti = self.height() / divPos
        qp.translate(.5 + self.width() / 2, .5 - posMulti / 2)
        for p in range(divPos):
            #if parallel, flow
            if self.routing:
                qp.setPen(self.hPen if p == self.focusArrow else self.pen)
            #if serial, blink
            else:
                qp.setPen(self.hPen if self.focusArrow == 1 else self.pen)
            qp.translate(0, posMulti)
            qp.drawPath(self.routingPaths[self.routing])
#            qp.drawLine(0, delta, self.width(), delta)
#            delta += posMulti


class BaseFakeObject(QtCore.QObject):
    valueChanged = QtCore.pyqtSignal(int)
    def __init__(self, parent, attr, widget, baseValue=0):
        QtCore.QObject.__init__(self, parent)
        self.widget = widget
        self.setObjectName(attr)
        self.value = baseValue
        self.setRange = self.setValueList = lambda *args: None

    def setValue(self, value):
        self.widget.blockSignals(True)
        self.widget.setValue(value)
        self.widget.blockSignals(False)


class FakeObject(BaseFakeObject):
    def __init__(self, *args, **kwargs):
        BaseFakeObject.__init__(self, *args, **kwargs)
        self.widget.valueChanged.connect(self.valueChanged)


class FakeArpStepGlideAccentObject(BaseFakeObject):
    def setValue(self, value):
        accent = value & 7
        self.widget.setAccent(accent, False)


class FakeArpTimingLengthObject(BaseFakeObject):
    def setValue(self, value):
        timing = value & 7
        length = (value >> 4) & 7
        self.widget.setTiming(timing, False)
        self.widget.setLength(length, False)


class FakeLetter(BaseFakeObject):
#    valueChanged = QtCore.pyqtSignal(int)
    def __init__(self, parent, lineEdit, char):
        BaseFakeObject.__init__(self, parent, 'nameChar{:02}'.format(char), lineEdit, 32)
        self.char = char

    def setValue(self, value):
        letter = getChar(value)
        oldText = self.widget.text()
        newText = oldText[:self.char] + letter + oldText[self.char + 1:]
        self.widget.blockSignals(True)
        self.widget.setText(newText, False)
        self.widget.blockSignals(False)

class EffectsFakeObject(QtCore.QObject):
    valueChanged = QtCore.pyqtSignal(int)
    def __init__(self, parent, attr, widgetList, valueList=None, altValueDict=None):
        QtCore.QObject.__init__(self, parent)
        self.setObjectName(attr)
        self.widgetList = widgetList
        for widget in widgetList:
            widget.valueChanged.connect(self.valueChanged)
            if valueList is not None:
                if altValueDict is not None and widget in altValueDict:
                    widget.setValueList(altValueDict[widget])
                else:
                    widget.setValueList(valueList)
        self.setRange = self.setValueList = lambda *args: None

    def updateSiblings(self, value):
        sender = self.sender()
        for widget in self.widgetList:
            if widget == sender:
                continue
            widget.blockSignals(True)
            widget.setValue(value)
            widget.blockSignals(False)

    def setValue(self, value):
        for widget in self.widgetList:
            widget.blockSignals(True)
            widget.setValue(value)
            widget.blockSignals(False)


class ValueUndo(QtWidgets.QUndoCommand):
    def __init__(self, parameters, attr, id, childId, newValue, oldValue, valueStr, oldValueStr):
        QtWidgets.QUndoCommand.__init__(self)
        self.parameters = parameters
        self.attr = attr
        self.undoId = id
        if childId is None:
            fullName = Parameters.parameterData[id].fullName
        else:
            fullName = Parameters.parameterData[id].children[childId].fullName
            self.undoId += childId << 9
        self.setText(u'{n} changed to {v}\n{n}'.format(n=fullName, v=valueStr))
        self.oldValueStr = oldValueStr
        self.valueStr = valueStr
        self.newValue = newValue
        self.oldValue = oldValue
        self.fullName = fullName

    def undoText(self):
        return 'Reset {} to {}'.format(self.fullName, self.oldValue)

    def redoText(self):
        return 'Restore {} to {}'.format(self.fullName, self.newValue)

    def id(self):
        return self.undoId

    def mergeWith(self, command):
        self.newValue = command.newValue
        self.setText(u'{}\n{}'.format(command.text(), command.actionText()))
        self.valueStr = command.valueStr
        return True

    def undo(self):
        self.parameters.blockSignals(True)
        setattr(self.parameters, self.attr, self.oldValue)
        self.parameters.blockSignals(False)

    def redo(self):
        self.parameters.blockSignals(True)
        setattr(self.parameters, self.attr, self.newValue)
        self.parameters.blockSignals(False)


class NameUndo(QtWidgets.QUndoCommand):
    def __init__(self, parameters, newText, oldText, chars, newValues, oldValues):
        QtWidgets.QUndoCommand.__init__(self)
        self.setText(u'Sound name changed to "{}"\nSound name'.format(newText))
        self.parameters = parameters
        self.newText = newText
        self.oldText = oldText
        if isinstance(chars, int):
            self.newChars = {chars: newValues}
            self.oldChars = {chars: oldValues}
        else:
            self.newChars = {}
            self.oldChars = {}
            for i, n, o in zip(chars, newValues, oldValues):
                self.newChars[i] = n
                self.oldChars[i] = o

    def undoText(self):
        return 'Reset name to "{}"'.format(self.oldText)

    def redoText(self):
        return 'Restore name to "{}"'.format(self.newText)

    def id(self):
        return 363

    def mergeWith(self, command):
        if command.id() not in range(363, 380):
            return False
        self.newChars = command.newChars
        self.oldChars = command.oldChars
        self.newText = command.newText
        self.setText(command.text() + '\nSound name')
        return True

    def undo(self):
        self.parameters.blockSignals(True)
        for i, char in self.oldChars.items():
            setattr(self.parameters, 'nameChar{:02}'.format(i), char)
        self.parameters.blockSignals(False)

    def redo(self):
        self.parameters.blockSignals(True)
        for i, char in self.newChars.items():
            setattr(self.parameters, 'nameChar{:02}'.format(i), char)
        self.parameters.blockSignals(False)


class DisplayMaskWidget(QtWidgets.QWidget):
    def __init__(self, maskWidget, reference):
        QtWidgets.QWidget.__init__(self)
        self.maskWidget = maskWidget
        self.reference = reference
        self.setWindowOpacity(.5)

    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        qp.setBrush(QtGui.QColor(0, 0, 0))
        qp.drawRect(self.rect().adjusted(-10, -10, 20, 20))

    def resizeEvent(self, event):
        bmp = QtGui.QBitmap(self.width(), self.height())
        bmp.clear()
        qp = QtGui.QPainter(bmp)
        qp.setPen(QtCore.Qt.black)
        qp.setBrush(QtCore.Qt.black)
        qp.drawRect(0, 0, self.width(), self.height())
        qp.eraseRect(self.maskWidget.geometry().translated(self.reference.geometry().topLeft()).adjusted(10, 10, 10, 10))
        qp.end()
        self.setMask(bmp)


class NameEditMask(QtWidgets.QGraphicsView):
    def __init__(self, parent, maskWidget, reference):
        QtWidgets.QGraphicsView.__init__(self, parent)
        self.setStyleSheet('background: transparent')
        self.setFrameStyle(0)
        self.setScene(QtWidgets.QGraphicsScene())
        self.blur = QtWidgets.QGraphicsBlurEffect()
        self.maskWidget = maskWidget
        self.reference = reference
        self.maskWidgetProxy = self.scene().addWidget(DisplayMaskWidget(maskWidget, reference))
        self.maskWidgetProxy.setGraphicsEffect(self.blur)

    def mousePressEvent(self, event):
        if event.pos() not in self.maskWidget.geometry().translated(self.reference.geometry().topLeft()):
            self.hide()

    def resizeEvent(self, event):
        self.setSceneRect(QtCore.QRectF(self.rect()))
        self.maskWidgetProxy.resize(QtCore.QSizeF(self.rect().size()))
        bmp = QtGui.QBitmap(self.width(), self.height())
        bmp.clear()
        qp = QtGui.QPainter(bmp)
        qp.setPen(QtCore.Qt.black)
        qp.setBrush(QtCore.Qt.black)
        qp.drawRect(0, 0, self.width(), self.height())
        qp.eraseRect(self.maskWidget.geometry().translated(self.reference.geometry().topLeft()).adjusted(15, 15, 5, 5))
        qp.end()
        self.setMask(bmp)




class EditorWindow(QtWidgets.QMainWindow):
    Clean, Saved, Modified = Enum(3)

    openLibrarianRequested = QtCore.pyqtSignal()
    midiEvent = QtCore.pyqtSignal(object)
    midiConnect = QtCore.pyqtSignal(object, int, bool)

    def __init__(self, parent):
        QtWidgets.QMainWindow.__init__(self)
        self.main = parent
        self.settings = parent.settings
        self.database = parent.database

        loadUi('ui/editor.ui', self)

        self.query = QtSql.QSqlQuery()
        self.referenceModel = self.database.referenceModel
        self.libraryModel = self.database.libraryModel

        self.bankBuffer = None
        self.currentUid = None
        self.currentCollection = None
        self.currentCollections = None
        self.currentBank = None
        self.currentProg = None

        self.editorMenuBar = EditorMenu(self)
        self.editorMenuBar.openSoundRequested.connect(self.openSoundFromMenu)
        self.editorMenuBar.importRequested.connect(self.importSound)
        self.editorMenuBar.randomAllRequest.connect(self.randomizeAll)
        self.editorMenuBar.randomCustomRequest.connect(self.randomizeCustom)
        self.leftLayout.insertWidget(0, self.editorMenuBar)

        self.saveBtn.button.setIcon(QtGui.QIcon.fromTheme('document-save'))
        self.autosaveBtn.switchToggled.connect(self.saveBtn.setDisabled)
        self.autosaveBtn.switchToggled.connect(lambda state: setattr(self, 'autosave', state))
        self._editStatus = self.Clean
        self._autosave = self.settings.value('autosave', False, bool)
#        self.saveBtn.setDisabled(True)
        self.saveBtn.clicked.connect(self.save)
#        self.saveFrame.setEnabled(False)

        self.display.customContextMenuRequested.connect(self.showDisplayMenu)
#        self.display.openSoundRequested.connect(self.openSoundFromUid)

        self.parameters = Parameters(self)
        self.parameters.parameterChanged.connect(self.parameterChanged)

        self.undoStack = QtWidgets.QUndoStack()
        self.undoStack.indexChanged.connect(self.editStatusCheck)
        self.undoStack.cleanChanged.connect(self.editStatusCheck)

        self.undoView = QtWidgets.QUndoView(self.undoStack)
        self.undoView.setCleanIcon(QtGui.QIcon.fromTheme('document-new'))
        self.undoView.setEmptyLabel('"Init" clean status')
        self.undoView.setWindowTitle('Bigglesworth editor undo list')
#        self.undoView.show()

        self.display.undoBtn.undoRequest.connect(self.undoUpdate)
        self.display.undoBtn.showUndo.connect(self.undoView.show)
        self.display.undoBtn.setUndoView(self.undoView, False)
        self.display.redoBtn.undoRequest.connect(self.redoUpdate)
        self.display.redoBtn.showUndo.connect(self.undoView.show)
        self.display.redoBtn.setUndoView(self.undoView, True)

        self.nameEdit = self.display.nameEdit

        self.filterEnvelopeView = EnvelopeView(self, 'filterEnvelope')
        self.filterEnvelopeFrame.layout().addWidget(self.filterEnvelopeView, 0, 1, 2, 4)
        self.filterEnvelopeView.hide()
        self.filterEnvelopePreview.clicked.connect(self.filterEnvelopeView.show)
        filterEnvelopeAdvDials = self.filterEnvelopeAttackLevel, self.filterEnvelopeDecay2, self.filterEnvelopeSustain2
        self.parameters.parameters('filterEnvelopeMode').valueChanged.connect(lambda index:
            [dial.setEnabled(index) for dial in filterEnvelopeAdvDials])

        self.amplifierEnvelopeView = EnvelopeView(self, 'amplifierEnvelope')
        self.amplifierEnvelopeFrame.layout().addWidget(self.amplifierEnvelopeView, 0, 1, 2, 4)
        self.amplifierEnvelopeView.hide()
        self.amplifierEnvelopePreview.clicked.connect(self.amplifierEnvelopeView.show)
        amplifierEnvelopeAdvDials = self.amplifierEnvelopeAttackLevel, self.amplifierEnvelopeDecay2, self.amplifierEnvelopeSustain2
        self.parameters.parameters('amplifierEnvelopeMode').valueChanged.connect(lambda index:
            [dial.setEnabled(index) for dial in amplifierEnvelopeAdvDials])

        self.envelope3View = EnvelopeView(self, 'envelope3')
        self.envelope3Frame.layout().addWidget(self.envelope3View, 0, 1, 2, 4)
        self.envelope3View.hide()
        self.envelope3Preview.clicked.connect(self.envelope3View.show)
        envelope3AdvDials = self.envelope3AttackLevel, self.envelope3Decay2, self.envelope3Sustain2
        self.parameters.parameters('envelope3Mode').valueChanged.connect(lambda index:
            [dial.setEnabled(index) for dial in envelope3AdvDials])
        
        self.envelope4View = EnvelopeView(self, 'envelope4')
        self.envelope4Frame.layout().addWidget(self.envelope4View, 0, 1, 2, 4)
        self.envelope4View.hide()
        self.envelope4Preview.clicked.connect(self.envelope4View.show)
        envelope4AdvDials = self.envelope4AttackLevel, self.envelope4Decay2, self.envelope4Sustain2
        self.parameters.parameters('envelope4Mode').valueChanged.connect(lambda index:
            [dial.setEnabled(index) for dial in envelope4AdvDials])

        for step in range(16):
            setattr(self, 'nameChar{:02}'.format(step), FakeLetter(self, self.nameEdit, step))
            for widgetId, attr in enumerate(('Step', 'Glide', 'Accent', 'Timing', 'Length')):
#                arpAttr = 'arpPattern{attr}{step}'.format(attr=attr, step=step + 1)
                arpAttr = 'arpPattern' + attr + str(step + 1)
#                print('creo attr', arpAttr)
                setattr(self, arpAttr, FakeObject(self, arpAttr, self.arpeggiatorDisplay.controlWidgets[step][widgetId]))
                if widgetId >= 2:
                    stepWidget = self.arpeggiatorDisplay.stepWidgets[step]
                    self.parameters.parameters(arpAttr).valueChanged.connect(
                        lambda value, stepWidget=stepWidget, attr=attr: getattr(stepWidget, 'set' + attr)(value, emit=False))
                    if stepWidget.twin:
                        self.parameters.parameters(arpAttr).valueChanged.connect(
                            lambda value, stepWidget=stepWidget, attr=attr: getattr(stepWidget.twin, 'set' + attr)(value, emit=False))
            arpAttr = 'arpPatternStepGlideAccent' + str(step + 1)
            setattr(self, arpAttr, FakeArpStepGlideAccentObject(
                self, arpAttr, self.arpeggiatorDisplay.stepWidgets[step]))
            arpAttr = 'arpPatternTimingLength' + str(step + 1)
            setattr(self, arpAttr, FakeArpTimingLengthObject(
                self, arpAttr, self.arpeggiatorDisplay.stepWidgets[step]))
#            arpAttr = 'arpPatternStep{}'.format(i + 1)
#            setattr(self, arpAttr, FakeObject(self, arpAttr, self.arpeggiatorDisplay.controlWidgets[0][0]))
        self.nameEditMask = NameEditMask(self, self.nameEdit, self.display)
        self.nameEditMask.hide()

        self.category = FakeObject(self, 'category', self.display.category)

        for efxIdList, efxParamId, efxNames, valueList, altValueData in _effects:
            for efxId in efxIdList:
                attr = 'effect{}Parameter{}'.format(efxId, efxParamId)
                widgetList = []
                altValueDict = {}
                for efxName, efxParamName in efxNames:
                    try:
                        widget = getattr(self, 'effect{}{}{}'.format(efxId, efxName, efxParamName))
                        widgetList.append(widget)
                        if altValueData and efxParamName in altValueData:
                            altValueDict[widget] = altValueData[efxParamName]
                    except Exception as e:
                        pass
#                        print(e)
                obj = EffectsFakeObject(self, attr, widgetList, valueList, altValueDict)
                setattr(self, attr, obj)

        #parameter and widget serialization
        self.attrList = []
        for param in Parameters.parameterData:
            if param.children:
                for child in param.children.values():
                    try:
                        widget = getattr(self, child.attr)
#                        widget.label = child.shortName
                        widget.setRange(*child.range)
                        widget.setValueList(child.values)
                        widget.setValue(child.default)
                        widget.valueChanged.connect(self.updateParameter)
                        widget.defaultValue = child.default
                    except Exception as e:
                        if not e.message.startswith('\'EditorWindow\' object has no attribute'):
                            print('c', e)
            else:
                try:
                    widget = getattr(self, param.attr)
#                    widget.label = param.shortName
                    widget.setRange(*param.range)
                    widget.setValueList(param.values)
                    widget.setValue(param.default)
                    widget.valueChanged.connect(self.updateParameter)
                    widget.defaultValue = param.default
                except Exception as e:
                    if not e.message.startswith('\'EditorWindow\' object has no attribute'):
                            print(e, param.attr)

        self.nameEdit.editingFinished.connect(self.createNameUndo)
        self.nameEdit.returnPressed.connect(self.createNameUndo)
        self.nameEdit.returnPressed.connect(self.nameEdit.clearFocus)
        self.nameEdit.focusChanged.connect(self.nameEditMask.setVisible)
        self.valueWidgets = None

        self.filterRoutingDisplay = FilterRoutingDisplay(self.filtersFrame)
        self.filtersFrame.layout().addWidget(self.filterRoutingDisplay, 1, 0, 1, 2)
        self.parameters.parameters('filterRouting').valueChanged.connect(self.filterRoutingDisplay.setRouting)

        #TODO: check if this should be _before_ serialization
        self.arpeggiatorPattern.blockSignals(True)
        self.arpeggiatorPattern.valueList = [
            u'off', 
            u'User', 
            u'●○●●|●○●●|●○●●|●○●●', 
            u'●○●○|●○○●|●○●○|●○○●', 
            u'●○●○|●○●●|●○●○|●○●●', 
            u'●○●●|●○●○|●○●●|●○●○', 
            u'●○●○|●●○●|●○●○|●●○●', 
            u'●●○●|○●●○|●●○●|○●●○', 
            u'●○●○|●○●○|●●○●|○●○●', 
            u'●○●○|●○●●|○●○●|●○●○', 
            u'●●●○|●●●○|●●●○|●●●○', 
            u'●●○●|●○●●|○●●○|●●●○', 
            u'●●○●|●○●●|○●●○|●○●○', 
            u'●●○●|●○●○|●●○●|●○●○', 
            u'●○●○|●○●○|●●○●|○●●●', 
            u'●○○●|○○●○|○●○○|●○○●', 
            u'●○●○|●○●○|●○○●|●○●○', 
            ]
        self.arpeggiatorPattern.blockSignals(False)
#        self.arpeggiatorPattern.currentIndexChanged.connect(lambda index: self.arpPatternEditBtn.setEnabled(True if index == 1 else False))
        self.parameters.parameters('arpeggiatorPattern').valueChanged.connect(lambda index: self.arpPatternEditBtn.setEnabled(True if index == 1 else False))
        self.arpPatternEditBtn.clicked.connect(lambda: self.arpEfxStackedWidget.setCurrentIndex(0))
        self.arpeggiatorDisplay.closeRequest.connect(lambda: self.arpEfxStackedWidget.setCurrentIndex(1))

        self.parameters.parameters('effect1Type').valueChanged.connect(self.efx1Widget.setCurrentIndex)
        self.parameters.parameters('effect2Type').valueChanged.connect(self.efx2Widget.setCurrentIndex)

        self.keyOctaveCombo.currentIndexChanged.connect(self.setOctave)
        logo = QtGui.QIcon(localPath('../resources/BlofeldLogo.svg')).pixmap(QtCore.QSize(140, 140))
        self.blofeldLogo.setPixmap(logo)

        self.midiInWidget.clicked.connect(self.showMidiMenu)
        self.midiInWidget.setProgState(self.main.progReceiveState)
        self.midiInWidget.setCtrlState(self.main.ctrlReceiveState)
        self.main.progReceiveToggled.connect(self.midiInWidget.setProgState)
        self.main.ctrlReceiveToggled.connect(self.midiInWidget.setCtrlState)

        self.midiOutWidget.clicked.connect(self.showMidiMenu)
        self.midiOutWidget.setProgState(self.main.progSendState)
        self.midiOutWidget.setCtrlState(self.main.ctrlSendState)
        self.main.progSendToggled.connect(self.midiOutWidget.setProgState)
        self.main.ctrlSendToggled.connect(self.midiOutWidget.setCtrlState)

        self.pianoKeyboard.noteEvent.connect(self.noteEvent)
        self.modSlider.valueChanged.connect(self.modEvent)

        self.osc1Frame.customContextMenuRequested.connect(self.templateMenu)
        self.osc2Frame.customContextMenuRequested.connect(self.templateMenu)
        self.osc3Frame.customContextMenuRequested.connect(self.templateMenu)
        self.lfo1Frame.customContextMenuRequested.connect(self.templateMenu)
        self.lfo2Frame.customContextMenuRequested.connect(self.templateMenu)
        self.lfo3Frame.customContextMenuRequested.connect(self.templateMenu)
        self.filtersFrame.customContextMenuRequested.connect(self.templateMenu)
        self.filter1Frame.customContextMenuRequested.connect(self.templateMenu)
        self.filter2Frame.customContextMenuRequested.connect(self.templateMenu)
        self.amplifierEnvelopeFrame.customContextMenuRequested.connect(self.templateMenu)
        self.filterEnvelopeFrame.customContextMenuRequested.connect(self.templateMenu)
        self.envelope3Frame.customContextMenuRequested.connect(self.templateMenu)
        self.envelope4Frame.customContextMenuRequested.connect(self.templateMenu)
        self.efx1Frame.customContextMenuRequested.connect(self.templateMenu)
        self.efx2Frame.customContextMenuRequested.connect(self.templateMenu)
        self.arpeggiatorFrame.customContextMenuRequested.connect(self.templateMenu)

        self.display.bankSpin.valueChanged.connect(self.bankChanged)
        self.display.progSpin.valueChanged.connect(self.progChanged)
        self._nextSoundChange = [None, None]
        self.nextSoundTimer = QtCore.QTimer()
        self.nextSoundTimer.setSingleShot(True)
        self.nextSoundTimer.setInterval(400)
        self.nextSoundTimer.timeout.connect(self.openSoundFromBankProg)

        saveMenu = QtWidgets.QMenu(self)
        self.saveAction = saveMenu.addAction('Save')
        self.saveAction.setShortcut(QtGui.QKeySequence('Ctrl+S'))
        self.saveAction.triggered.connect(self.save)
#        saveMenu.addAction(self.saveAction)
#        self.addAction(self.saveAction)
        self.saveAsAction = saveMenu.addAction('Save as...')
        self.saveAsAction.setShortcut(QtGui.QKeySequence('Ctrl+Shift+S'))
        self.saveAsAction.triggered.connect(self.saveAs)
#        saveMenu.addAction(self.saveAsAction)
        self.addActions(saveMenu.actions())
        self.saveBtn.setMenu(saveMenu)


#    def keyPressEvent(self, event):
#        print(QtWidgets.QApplication.focusWidget())
#        QtWidgets.QMainWindow.keyPressEvent(self, event)
#
#    def keyReleaseEvent(self, event):
#        QtWidgets.QMainWindow.keyReleaseEvent(self, event)

    @property
    def editStatus(self):
        return self._editStatus

    @editStatus.setter
    def editStatus(self, status):
        self._editStatus = status
        if status == self.Saved:
            self.saveBtn.setSwitchable(False)
            self.saveBtn.setSwitched(False)
            self.display.setStatusText('Saved!')
        elif status == self.Modified and self.currentUid and not self._autosave:
            self.saveBtn.setSwitchable(True)
            self.saveBtn.setSwitched(True)
        self.display.editStatusWidget.setStatus(status)

    @property
    def autosave(self):
        return self._autosave

    @autosave.setter
    def autosave(self, state):
        self._autosave = state
        self.settings.beginGroup('remember')
        remember = self.settings.value('autosave', True, bool)
        self.settings.endGroup()
        if remember:
            self.settings.setValue('autosave', state)
        if state and self.editStatus == self.Modified:
            self.save()

    def showMidiMenu(self):
        direction = MidiOut if self.sender() == self.midiOutWidget else MidiIn
        menu = QtWidgets.QMenu()
        menu.setSeparatorsCollapsible(False)
        sep = QtWidgets.QAction('MIDI out' if direction == MidiOut else 'MIDI in', menu)
        sep.setSeparator(True)
        menu.addAction(sep)

        if direction == MidiOut:
            ctrlAction = menu.addAction('Send MIDI events')
            ctrlAction.setCheckable(True)
            ctrlAction.setChecked(True if self.main.ctrlSendState else False)
            ctrlActionAttr = 'ctrlSendState'
            progAction = menu.addAction('Send Program changes')
            progAction.setCheckable(True)
            progAction.setChecked(True if self.main.progSendState else False)
            progActionAttr = 'progSendState'
        else:
            ctrlAction = menu.addAction('Receive MIDI events')
            ctrlAction.setCheckable(True)
            ctrlAction.setChecked(True if self.main.ctrlReceiveState else False)
            ctrlActionAttr = 'ctrlReceiveState'
            progAction = menu.addAction('Receive Program changes')
            progAction.setCheckable(True)
            progAction.setChecked(True if self.main.progReceiveState else False)
            progActionAttr = 'progReceiveState'

        clientListMenu = menu.addMenu('')
        connections = 0
        for client in [self.main.graph.client_id_dict[cid] for cid in sorted(self.main.graph.client_id_dict.keys())]:
            if client in (self.main.midiDevice.input.client, self.main.midiDevice.output.client):
                continue
            ports = []
            for port in client.ports:
                if port.hidden:
                    continue
                if (port.is_output and direction == MidiIn) or (port.is_input and direction == MidiOut):
                    ports.append(port)
            if ports:
                clientMenu = clientListMenu.addMenu(client.name)
                connected = False
                for port in ports:
                    portAction = clientMenu.addAction(port.name)
                    portAction.setCheckable(True)
                    portAction.setData(port)
                    if (direction == MidiIn and any([True for conn in port.connections.output if conn.dest == self.main.midiDevice.input])) or \
                        (direction == MidiOut and any([True for conn in port.connections.input if conn.src == self.main.midiDevice.output])):
                            portAction.setChecked(True)
                            connected = True
                            connections += 1
                if connected:
                    setBold(clientMenu.menuAction())
        clientListMenu.setTitle('Connections ({})'.format(connections))
        if not clientListMenu.actions():
            clientListMenu.setEnabled(False)

        res = menu.exec_(QtGui.QCursor.pos())
        if not res:
            return
        if res == progAction:
            setattr(self.main, progActionAttr, progAction.isChecked())
        elif res == ctrlAction:
            setattr(self.main, ctrlActionAttr, ctrlAction.isChecked())
        elif res.data():
            self.midiConnect.emit(res.data(), direction, res.isChecked())

    def templateMenu(self, pos):
        sender = self.sender()
        group, single, id = templateGroupDict[sender.objectName()]
        groupList = [group.dbName]
        if single:
            groupList.append(single.dbName)
        templates = self.database.getTemplatesByGroups(groupList)
        menu = QtWidgets.QMenu()
        menu.setSeparatorsCollapsible(False)
        menu.addSeparator().setText('Templates')
        if single:
            singleMenu = menu.addMenu('Single {}'.format(single.fullName))
            for name in sorted(templates):
                groups, valueList = templates[name]
                if single.dbName in groups:
                    singleLoadAction = singleMenu.addAction(name)
                    singleLoadAction.setData(valueList)
            if singleMenu.actions():
                singleMenu.addSeparator()
            singleSaveAction = singleMenu.addAction('Save template...')
            groupMenu = menu.addMenu(group.fullName)
        else:
            singleSaveAction = None
            groupMenu = menu

        groupTemplates = False
        for name in sorted(templates):
            groups, valueList = templates[name]
            if group.dbName in groups:
                groupLoadAction = groupMenu.addAction(name)
                groupLoadAction.setData(valueList)
                groupTemplates = True
        if groupTemplates:
            groupMenu.addSeparator()
        groupSaveAction = groupMenu.addAction('Save template for {}...'.format(group.fullName))

        menu.addSeparator()
        showManagerAction = menu.addAction('Manage templates...')

        res = menu.exec_(self.sender().mapToGlobal(pos))
        if not res:
            return
        if res == showManagerAction:
            manager = TemplateManager(self)
            if manager.exec_() and manager.changed:
                self.database.updateTemplates(manager.templates, manager.deleted)
        elif res == singleSaveAction:
            name = InputMessageBox(self, 'Save template', 
                'Select template name for single {}'.format(single.fullName), 
                invalidList=self.database.getTemplateNames()).exec_()
            if not name:
                return
#            print('save single template for {}, params:'.format(single.fullName))
            params = []
            for pid in single.params:
                pid = pid + single.groupDelta * id
                attr = Parameters.parameterData[pid].attr
                if attr.startswith('reserved'):
                    continue
                value = int(self.parameters[pid])
                params.append((attr, value))
            self.database.createTemplate(name, params, [single.dbName])
            return
#            print('\n'.join('{} {}: {}'.format(pid, p, value) for pid, p, value in params))
        elif res == groupSaveAction:
            name = InputMessageBox(self, 'Save template', 
                'Select template name for {} group'.format(group.fullName), 
                invalidList=self.database.getTemplateNames()).exec_()
            if not name:
                return
            params = []
            for pid in group.params:
                attr = Parameters.parameterData[pid].attr
                if attr.startswith('reserved'):
                    continue
                value = int(self.parameters[pid])
                params.append((attr, value))
            self.database.createTemplate(name, params, [group.dbName])
            return
        else:
#            if res.parent() == singleMenu:
#                template = single
#            else:
#                template = group
            valueList = res.data()
            if not valueList:
                return
            for attr, value in valueList:
                setattr(self.parameters, attr, value)
#            print(template, valueList)

    def bankChanged(self, bank):
        if not self.currentCollection:
            return
        self._nextSoundChange[0] = bank
        self.display.progSpin.setBank(bank)
        self.nextSoundTimer.start()

    def progChanged(self, prog):
        if not self.currentCollection:
            return
        self._nextSoundChange[1] = prog - 1
        self.nextSoundTimer.start()

    def setTheme(self, theme):
#        try:
#            self.currentTheme.changed.disconnect()
#        except:
#            pass
        self.currentTheme = theme
#        self.currentTheme.changed.connect(self.setTheme)

        self.setPalette(theme.palette)
        self.setFont(theme.font)
        dialStart, dialZero, dialEnd, dialGradient, dialBgd, dialScale, dialNotches, dialIndicator = theme.dialData
        for child in self.findChildren(Dial):
            child.rangeColorStart = dialStart
            child.rangeColorZero = dialZero
            child.rangeColorEnd = dialEnd
            child.gradientScale = dialGradient
            child.rangePenColor = dialScale
            child.scalePenColor = dialNotches
            child.pointerColor = dialIndicator
        sliderStart, sliderEnd, sliderBgd = theme.sliderData
        for child in self.findChildren(Slider):
            child.rangeColorStart = sliderStart
            child.rangeColorEnd = sliderEnd
            child.background = sliderBgd
        for child in self.findChildren(Combo):
            child.opaque = theme.comboStyle
        for child in self.findChildren(Frame):
            child.borderColor = theme.frameBorderColor
            child.labelColor = theme.frameLabelColor
        self.repaint()

    def setOctave(self, offset):
        self.pianoKeyboard.firstNote = 12 + offset * 12
        self.pianoKeyboard.noteOffset = 1

    def undoUpdate(self, index=None):
        if index is None:
            index = self.undoStack.index()
        cmd = self.undoStack.command(index)
        if isinstance(cmd, NameUndo):
            text = '{} reset to "{}"'.format(cmd.actionText(), cmd.oldText)
        else:
            text = '{} reset to {}'.format(cmd.actionText(), cmd.oldValueStr)
        self.display.setStatusText(text)

    def redoUpdate(self, index=None):
        if index is None:
            index = self.undoStack.index() - 1
        cmd = self.undoStack.command(index)
        if isinstance(cmd, NameUndo):
            text = '{} restored to "{}"'.format(cmd.actionText(), cmd.newText)
        else:
            text = '{} restored to {}'.format(cmd.actionText(), cmd.valueStr)
        self.display.setStatusText(text)

#    def getUndoText(self, index, mode):
#        cmd = self.undoStack.command(index)
#        if mode:
#            modeStr = 'Restore'
#            if isinstance(cmd, NameUndo):
#                value = '"{}"'.format(cmd.newText)
#            else:
#                value = cmd.valueStr
#        else:
#            modeStr = 'Reset'
#            if isinstance(cmd, NameUndo):
#                value = '"{}"'.format(cmd.oldText)
#            else:
#                value = cmd.oldValueStr
#        return '{m} {a} to {v}'.format(m=modeStr, a=cmd.actionText(), v=value)

    def showValues(self, state):
        if not self.valueWidgets:
            self.valueWidgets = self.findChildren(Dial) + self.findChildren(Slider)
        for widget in self.valueWidgets:
            widget.showValue(state)

    def createNameUndo(self, text=None):
#        print('cambiato! "{}'.format(text))
        if text is None:
            text = self.nameEdit.text()
        newName = text.ljust(16, ' ')[:16]
#        oldText = getName(c.default for c in Parameters.parameterData[363:379])
        oldName = getName(self.parameters[363:379])
        if newName == oldName:
            return
        changed = []
        newValues = []
        oldValues = []
        for i, (old, new) in enumerate(zip(oldName, newName)):
            if old != new:
                changed.append(i)
                newValues.append(chr2ord[new])
                oldValues.append(chr2ord[old])
        undo = NameUndo(self.parameters, newName, oldName, changed, newValues, oldValues)
        self.display.setStatusText(undo.text())
        self.undoStack.push(undo)

    
    def parameterChanged(self, id, childId, newValue, oldValue):
        location = 0
        parHigh, parLow = divmod(id, 128)
#        print par_high, par_low, value

        if self.main.ctrlSendState:
            self.midiEvent.emit(SysExEvent(1, [INIT, IDW, IDE, self.main.blofeldId, SNDP, location, parHigh, parLow, newValue, END]))
            self.midiOutWidget.activate()
        if self.autosave and self.currentUid:
            self.database.updateSoundValue(self.currentUid, id, newValue)

        #TODO: check for parameter range (here or in parameters class?)
        param = Parameters.parameterData[id]
        if id in range(363, 379):
            if newValue == oldValue:
                return
            newName = getName(self.parameters[363:379])
            oldName = getName([self.parameters[i] for i in range(363, id)] + [oldValue] + [self.parameters[i] for i in range(id + 1, 379)])
            undo = NameUndo(self.parameters, newName, oldName, id - 363, newValue, oldValue)
            self.display.setStatusText(undo.text())
            self.undoStack.push(undo)
            if self.autosave and self.currentUid:
                self.undoStack.setClean()
            return
        if childId is not None:
            param = param.children[childId]
            oldValueStr = param.values[oldValue]
            strValue = param.values[newValue]
        else:
            if param.attr.startswith('reserved'):
                return
            if param.children:
                strValues = []
                for _childId in reversed(param.children.keys()):
                    childParam = param.children[_childId]
                    childValue = getattr(self.parameters, childParam.attr)
                    strValues.append(childParam.values[(childValue - childParam.range.minimum) / childParam.range.step])
                #TODO: fix this!
                oldValueStr = '???'
                strValue = ', '.join(strValues)
            else:
#                print(param.attr, param.range, param.values, newValue - param.range[0])
#                strValue = param.values[newValue - param.range[0]]
                oldValueStr = param.values[(oldValue - param.range.minimum) / param.range.step]
                strValue = param.values[(newValue - param.range.minimum) / param.range.step]
        undo = ValueUndo(self.parameters, param.attr, id, childId, newValue, oldValue, strValue, oldValueStr)
        self.display.setStatusText(undo.text())
        self.undoStack.push(undo)
        if self.autosave and self.currentUid:
            self.undoStack.setClean()
#        self.display.editStatusWidget.setStatus(2)

    def save(self):
        if self.currentUid:
            if self._editStatus == self.Modified:
                saved = self.database.updateSound(self.currentUid, self.parameters)
                if saved:
                    self.undoStack.setClean()
                    return True
                else:
                    return False
        else:
            return self.saveAs()

    def saveAs(self):
        name = self.display.nameEdit.text()
        res = SaveSoundAs(self).exec_(name, self.currentCollection)
        if not res:
            return
        newName, collection, index, uid = res
        data = self.parameters[:]
        if newName.strip() != name.strip():
            newName = newName.ljust(16, ' ')
            self.parameters.blockSignals(True)
            for i, l in zip(range(363, 379), newName):
                o = chr2ord[l]
                data[i] = o
                self.parameters[i] = o
            self.parameters.blockSignals(False)
#        else:
#            print('nome uguale!')
#        print(getName(data[363:379]))
        self.currentUid = self.database.addRawSoundData(data, collection, index, uid)
        if not self.currentUid:
            print('error saving?!')
            return False
        self.currentCollection, self.currentBank, self.currentProg = self.display.setCollections([collection], self.currentUid, collection)
        self.undoStack.setClean()
        return True

    def midiEventReceived(self, event):
        if event.type == PROGRAM:
            if self.main.progReceiveState and event.channel in self.main.chanReceive:
                if self.bankBuffer is not None:
                    self.midiInWidget.activate()
                    print('prog change - bank', self.bankBuffer, 'prog', event.program)
            self.bankBuffer = None
            return
        if event.type == NOTEON:
            self.pianoKeyboard.triggerNoteEvent(True, event.note, event.velocity)
            self.midiInWidget.activate()
        elif event.type == NOTEOFF:
            self.pianoKeyboard.triggerNoteEvent(False, event.note, event.velocity)
            self.midiInWidget.activate()
        elif event.type == CTRL:
            if event.channel not in self.main.chanReceive:
                return
            if self.main.ctrlSendState and event.param != 0:
                pass
                self.midiEvent.emit(event)
            if event.param == 0:
                if self.main.progReceiveState:
                    self.bankBuffer = event.value
                return
            elif event.param == 1:
                self.modSlider.blockSignals(True)
                self.modSlider.setValue(event.value)
                self.modSlider.blockSignals(False)
            elif event.param in ctrl2sysex:
                self.midiInWidget.activate()
                index = ctrl2sysex[event.param]
                self.parameters[index] = event.value
                self.bankBuffer = None
#                setattr(self.parameters, self.sender().objectName(), value)
#        print(event.type == NOTE)
        pass
#        if event.type == NOTE
#        if not self.main.ctrlReceiveState
#        if event.type == SYSEX:
#            pass
#        elif event.type == CTRL:
#            if event in ctrl2sysex:
#                self.
#            print ctrl2sysex[event.data]

    def noteEvent(self, eventType, note, velocity):
        for channel in sorted(self.main.chanSend):
            event = NoteOnEvent if eventType else NoteOffEvent
            self.midiEvent.emit(event(1, channel, note, velocity))

    def modEvent(self, value):
        for channel in sorted(self.main.chanSend):
            self.midiEvent.emit(CtrlEvent(1, channel, 1, value))

    def editStatusCheck(self, data):
        #TODO verifica meglio il clean!
        if not isinstance(data, bool):
            self.editStatus = self.Modified if data and not self.undoStack.isClean() else self.Clean
        elif data:
            self.editStatus = self.Saved if self.undoStack.index() != 0 else self.Clean
        else:
            self.editStatus = self.Modified

    def updateParameter(self, value):
        setattr(self.parameters, self.sender().objectName(), value)

    def importSound(self):
        print('show import dialog')

    def openSoundFromBankProg(self, bank=None, prog=None, collection=None):
        if not collection:
            if not self.currentCollection:
                return
            collection = self.currentCollection
        if (bank, prog) == (None, None):
            bank, prog = self._nextSoundChange
        if bank is None:
            bank = self.currentBank
        if prog is None:
            prog = self.currentProg
        if (bank, prog) == (self.currentBank, self.currentProg):
            return
        print('cambio a', bank, prog, collection)
        self.openSoundFromUid(self.database.getUidFromCollection(bank, prog, collection), collection)
#        self.currentBank = bank
#        self.currentProg = prog

    def openSoundFromMenu(self, action):
        self.openSoundFromUid(action.data(), action.parentWidget().menuAction().data())

    def openSoundFromUid(self, uid, fromCollection=None):
#        self.saveFrame.setEnabled(True)
        if self._editStatus == self.Modified:
            res = QtWidgets.QMessageBox.question(self, 'Sound modified', 
                'The current sound has been modified', 
                buttons=QtWidgets.QMessageBox.Save|QtWidgets.QMessageBox.Ignore|QtWidgets.QMessageBox.Cancel)
            if res == QtWidgets.QMessageBox.Cancel:
                return
            elif res == QtWidgets.QMessageBox.Save:
                saved = self.saveAs()
                if saved == False:
                    return QtWidgets.QMessageBox.alert(self, 'Save error', 
                    'There was a problem saving the sound', 
                    QtWidgets.QMessageBox.Ok)
        self.saveBtn.setSwitchable(False)
        self.saveBtn.setSwitched(False)
        if not self.isVisible():
            self.show()
        self.activateWindow()
        data = self.database.getSoundDataFromUid(uid)
        if not data:
            return
        if self.editStatus == self.Modified:
            print('MODIFIED!!!')
        self.currentUid = uid

        self.setValues(data)
#        res = self.query.exec_('SELECT {} FROM sounds WHERE uid = "{}"'.format(','.join(Parameters.parameterList), uid))
#        if not res:
#            print(self.query.lastError().databaseText())
#        else:
#            self.query.first()
#            self.setValues([self.query.value(v) for v in range(383)])
        match = self.libraryModel.match(self.libraryModel.index(0, UidColumn), QtCore.Qt.DisplayRole, uid, flags=QtCore.Qt.MatchExactly)
        if not match:
            print('something is wrong!')
            return
        locations = match[0].sibling(match[0].row(), LocationColumn).data()
        if not locations:
            print('orphan')
            return
        collections = []
        for b, collection in zip(range(locations.bit_length()), self.referenceModel.allCollections):
            lbit = locations >> b & 1
            if lbit:
#                if uniqueCollection is not None:
#                    break
#                collection = factoryPresetsNamesDict.get(collection, collection)
                collections.append(collection)
#        else:
#            #unique collection found!
#            self.display.setCollection(collection)
#            return
        self.currentCollections = collections if collections else None
        self.currentCollection, self.currentBank, self.currentProg = self.display.setCollections(collections, uid, fromCollection)

    def setValues(self, data=None):
        self.parameters.blockSignals(True)
        if not data:
            data = [p.default for p in Parameters.parameterData]
        for p, value in zip(Parameters.parameterData, data):
            if p.attr.startswith('reserved'):
                continue
            setattr(self.parameters, p.attr, value)
        self.parameters.blockSignals(False)
        name = getName(self.parameters[363:379]).strip()
        self.undoStack.clear()
        self.undoView.setEmptyLabel('"{}" clean status'.format(name))
        self.display.setStatusText('"{}" loaded'.format(name))
#        self.display.editStatusWidget.setStatus(0)

    def showDisplayMenu(self, pos):
        #TODO: keep existing SoundsMenu instance?
        menu = SoundsMenu(self)
        if self.currentCollection and (self.display.bankWidget.isEnabled() or self.display.progWidget.isEnabled()) and \
            pos in self.display.bankWidget.geometry() | self.display.progWidget.geometry():
                actions = menu.getCollectionMenu(self.currentCollection).actions()
                menu = QtWidgets.QMenu()
                menu.setSeparatorsCollapsible(False)
                menu.addSeparator().setText(self.currentCollection)
                menu.addActions(actions)
        menu.hovered.connect(lambda action: self.statusbar.showMessage(action.statusTip()))
        res = menu.exec_(self.display.viewport().mapToGlobal(pos))
        if res and res.data():
            self.openSoundFromMenu(res)

    def randomizeAll(self):
        if self.display.editStatusWidget.status:
            pass
        for param in Parameters.parameterData:
            if param.attr.startswith('reserved'):
                continue
            if param.children:
                for child in param.children.values():
                    setattr(self.parameters, child.attr, randrange(child.range.minimum, child.range.maximum + 1, child.range.step))
            else:
                setattr(self.parameters, param.attr, randrange(param.range.minimum, param.range.maximum + 1, param.range.step))

    def randomizeCustom(self):
        randomDialog = RandomDialog()
        res = randomDialog.exec_()
        if not res:
            return
        paramList = randomDialog.getChecked()
        for param in Parameters.parameterData:
            if param.id not in paramList or param.attr.startswith('reserved'):
                continue
            if param.children:
                for child in param.children.values():
                    setattr(self.parameters, child.attr, randrange(child.range.minimum, child.range.maximum + 1, child.range.step))
            else:
                setattr(self.parameters, param.attr, randrange(param.range.minimum, param.range.maximum + 1, param.range.step))

    def changeEvent(self, event):
        if event.type() == QtCore.QEvent.PaletteChange:
            self.display.setPalette(self.palette())

    def resizeEvent(self, event):
        self.nameEditMask.setGeometry(self.geometry().adjusted(-10, -10, 20, 20))
#        print(self.osc1Shape.mapTo(self.centralWidget(), self.osc1Shape.rect().topLeft()))


