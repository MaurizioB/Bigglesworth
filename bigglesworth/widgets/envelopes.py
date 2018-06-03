from Qt import QtCore, QtGui, QtWidgets

from bigglesworth.utils import sanitize
from bigglesworth.widgets import CloseBtn

def makeEnvProperty(name):
    vName = '_{}'.format(name)
    cName = name[0].upper() + name[1:]

    def getter(self):
        return getattr(self, vName)

    def setter(self, value):
        setattr(self, vName, value)
        setattr(self.main.parameters, self.envName + cName, value)

    return property(getter, setter)


class FocusPoint(QtWidgets.QGraphicsWidget):
    normalPen = QtGui.QPen(QtGui.QColor(QtCore.Qt.darkGray))
    focusPen = QtGui.QPen(QtGui.QColor(QtCore.Qt.red))
    pen = normalPen
    baseRect = QtCore.QRectF(-2, -2, 4, 4)
    fullBoundingRect = baseRect.adjusted(-4, -4, 4, 4)
    baseShape = QtGui.QPainterPath()
    baseShape.addRect(baseRect.adjusted(-2, -2, 2, 2))
#    positionChanged = QtCore.pyqtSignal(QtCore.QPointF)
    def __init__(self, orientation=None):
        QtWidgets.QGraphicsWidget.__init__(self)
        if orientation == QtCore.Qt.Horizontal:
            self.hoverCursor = QtCore.Qt.SizeHorCursor
        elif orientation == QtCore.Qt.Vertical:
            self.hoverCursor = QtCore.Qt.SizeVerCursor
        else:
            self.hoverCursor = QtCore.Qt.SizeAllCursor
        self.setAcceptHoverEvents(True)
        self.setFlags(self.flags() | self.ItemIgnoresTransformations | self.ItemIsMovable)
        self._laterConnections = []
        self.geometryChanged.connect(self.applyLaterConnect)

    def laterConnect(self, func):
        self._laterConnections.append(func)

    def applyLaterConnect(self):
        #geometryChanged is emitted after the item is added and then "resized" in the scene,
        #we are only interested in it once the item is actually placed and correctly sized
        if self.size().isNull():
            return
        self.geometryChanged.disconnect()
        for func in self._laterConnections:
            self.geometryChanged.connect(func)

#    def itemChange(self, change, value):
#        if change == self.ItemPositionHasChanged and not self.size().isNull():
#            #geometryChanged is emitted
#            self.positionChanged.emit(self.pos())
#        return QtWidgets.QGraphicsWidget.itemChange(self, change, value)
#        self.initialized.emit()

    def hoverEnterEvent(self, event):
        self.pen = self.focusPen
        self.setCursor(self.hoverCursor)
        self.update()

    def hoverLeaveEvent(self, event):
        self.pen = self.normalPen
        self.unsetCursor()
        self.update()

    def mousePressEvent(self, event):
        self.setCursor(QtCore.Qt.BlankCursor)
        QtWidgets.QGraphicsWidget.mousePressEvent(self, event)

    def mouseReleaseEvent(self, event):
        self.unsetCursor()
        QtWidgets.QGraphicsWidget.mouseReleaseEvent(self, event)

    def boundingRect(self):
        return self.fullBoundingRect

    def shape(self):
        return self.baseShape

    def paint(self, qp, option, widget):
        qp.setPen(self.pen)
        qp.drawEllipse(self.baseRect)


class LimitLine(QtWidgets.QGraphicsLineItem):
    def __init__(self, *args, **kwargs):
        QtWidgets.QGraphicsLineItem.__init__(self, *args, **kwargs)
        pen = QtGui.QPen(QtCore.Qt.darkGray, 1, QtCore.Qt.DotLine)
        pen.setCosmetic(True)
        self.setPen(pen)


class ToolTipWidget(QtWidgets.QGraphicsWidget):
    def __init__(self):
        QtWidgets.QGraphicsWidget.__init__(self)
        self.setAcceptHoverEvents(True)
        self.fontMetrics = QtGui.QFontMetrics(self.font())
        self.setFlags(self.flags() | self.ItemIgnoresTransformations)
        self.brush = QtGui.QColor(220, 220, 200, 200)

    def hoverEnterEvent(self, event):
        self.hide()

    def showMessage(self, message):
        self.message = message
        self.prepareGeometryChange()
        self._boundingRect = QtCore.QRectF(self.fontMetrics.boundingRect(0, 0, 200, 200, QtCore.Qt.TextExpandTabs, self.message).adjusted(0, 0, 4, 4))
        self._textRect = self._boundingRect.adjusted(2, 2, -2, -2)
        self.setVisible(True)

    def size(self):
        try:
            return self._boundingRect.size()
        except:
            return QtWidgets.QGraphicsWidget.size(self)

    def boundingRect(self):
        try:
            return self._boundingRect
        except:
            return QtCore.QRectF(0, 0, 20, 20)

    def paint(self, qp, option, widget):
#        qp.save()
#        qp.translate(.5, .5)
        qp.setBrush(self.brush)
        qp.drawRect(self._boundingRect)
        qp.drawText(self._textRect, QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter, self.message)
#        qp.restore()


class LoopStart(QtWidgets.QGraphicsPathItem):
    def __init__(self):
        QtWidgets.QGraphicsPathItem.__init__(self)
        self.setFlags(self.flags() | self.ItemIgnoresTransformations)
        path = QtGui.QPainterPath()
        path.moveTo(-6, -3)
        path.lineTo(0, 0)
        path.lineTo(-6, 3)
        path.closeSubpath()
        self.setPath(path)
#        self.setPen(QtGui.QPen(QtCore.Qt.lightGray, 1, QtCore.Qt.DashLine))
        self.setPen(QtGui.QPen(QtCore.Qt.darkGray))
        self.setBrush(QtCore.Qt.lightGray)


class LoopEnd(QtWidgets.QGraphicsPathItem):
    def __init__(self):
        QtWidgets.QGraphicsPathItem.__init__(self)
        self.setFlags(self.flags() | self.ItemIgnoresTransformations)
        path = QtGui.QPainterPath()
        path.lineTo(6, -3)
        path.lineTo(6, 3)
        path.closeSubpath()
        self.setPath(path)
#        self.setPen(QtGui.QPen(QtCore.Qt.lightGray, 1, QtCore.Qt.DashLine))
        self.setPen(QtGui.QPen(QtCore.Qt.darkGray))
        self.setBrush(QtCore.Qt.lightGray)


class LoopPath(QtWidgets.QGraphicsPathItem):
    def __init__(self):
        QtWidgets.QGraphicsPathItem.__init__(self)
        self.start = 10
        self.end = 90
        self.pen = QtGui.QPen(QtCore.Qt.lightGray, 1, QtCore.Qt.DashLine)
        self.dashOffset = self.pen.dashOffset()
        self.dashMaximum = sum(self.pen.dashPattern())
        self.pen.setCosmetic(True)
        self.setPen(self.pen)
        self.setBrush(QtGui.QBrush(QtCore.Qt.NoBrush))
        self.createPath()
        self.animationTimer = QtCore.QTimer()
        self.animationTimer.setInterval(200)
        self.animationTimer.timeout.connect(self.setDashOffset)

    def setAnimation(self, state):
        if state:
            self.animationTimer.start()
        else:
            self.animationTimer.stop()

    def setDashOffset(self):
        self.dashOffset += 1
        if self.dashOffset == self.dashMaximum:
            self.dashOffset = 0
        self.pen.setDashOffset(self.dashOffset)
        self.setPen(self.pen)

    def setStart(self, start):
        self.start = start
        self.createPath()

    def setEnd(self, end):
        self.end = end
        self.createPath()

    def setRange(self, start, end):
        self.start = start
        self.end = end
        self.createPath()

    def createPath(self):
        path = QtGui.QPainterPath()
        path.moveTo(self.start + 6, -8)
        path.arcTo(self.start, -8, 12, 16, 90, 180)
        path.lineTo(self.end - 6, 8)
        path.arcTo(self.end - 12, -8, 12, 16, 270, 180)
        path.closeSubpath()
        self.setPath(path)


class EnvelopeScene(QtWidgets.QGraphicsScene):
    def __init__(self, main, envName):
        QtWidgets.QGraphicsScene.__init__(self)
        self.setSceneRect(QtCore.QRectF(0, 0, 100, 100))
        self.main = main
        self.envName = envName
        main.parameters.parameters(envName + 'Mode').valueChanged.connect(self.setEnvelopeMode)
        main.parameters.parameters(envName + 'Attack').valueChanged.connect(self.attackChanged)
        main.parameters.parameters(envName + 'Decay').valueChanged.connect(self.decayChanged)
        main.parameters.parameters(envName + 'Sustain').valueChanged.connect(self.sustainChanged)
        main.parameters.parameters(envName + 'Release').valueChanged.connect(self.releaseChanged)
        main.parameters.parameters(envName + 'AttackLevel').valueChanged.connect(self.attackLevelChanged)
        main.parameters.parameters(envName + 'Decay2').valueChanged.connect(self.decay2Changed)
        main.parameters.parameters(envName + 'Sustain2').valueChanged.connect(self.sustain2Changed)

        self._attack = getattr(main.parameters, envName + 'Attack')
        self._attackLevel = getattr(main.parameters, envName + 'AttackLevel')
        self._decay = getattr(main.parameters, envName + 'Decay')
        self._decay2 = getattr(main.parameters, envName + 'Decay2')
        self._sustain = getattr(main.parameters, envName + 'Sustain')
        self._sustain2 = getattr(main.parameters, envName + 'Sustain2')
        self._release = getattr(main.parameters, envName + 'Release')

        self.startPos = QtCore.QPointF(10, 90)
        self.endPos = QtCore.QPointF(90, 90)
        self.addLine(QtCore.QLineF(QtCore.QPointF(-2, 90), self.startPos))
        self.addLine(QtCore.QLineF(self.endPos, QtCore.QPointF(102, 90)))

        self.attackPoint = FocusPoint()
        self.addItem(self.attackPoint)
        self.attackPoint.setPos(10, 10)
#        self.attackPoint.laterConnect(self.attackMoved)
        self.attackPoint.laterConnect(self.attackMoved)
#        self.attackPoint.xChanged.connect(self.attackMoved)
#        self.attackPoint.yChanged.connect(self.attackMoved)

        self.decayPoint = FocusPoint()
        self.addItem(self.decayPoint)
        self.decayPoint.setPos(20, 50)
        self.decayPoint.laterConnect(self.decayMoved)

        self.decay2Point = FocusPoint()
        self.addItem(self.decay2Point)
        self.decay2Point.setPos(20, 50)
        self.decay2Point.laterConnect(self.decay2Moved)

        self.sustainPoint = FocusPoint(QtCore.Qt.Vertical)
        self.addItem(self.sustainPoint)
        self.sustainPoint.setPos(80, 50)
        self.sustainPoint.laterConnect(self.sustainMoved)

        self.releasePoint = FocusPoint(QtCore.Qt.Horizontal)
        self.addItem(self.releasePoint)
        self.releasePoint.setPos(90, 90)
        self.releasePoint.laterConnect(self.releaseMoved)

        self.attackLimitLine = LimitLine(0, -5, 0, 105)
        self.addItem(self.attackLimitLine)
        self.attackLimitLine.setZValue(-1)

        self.decayLimitLine = LimitLine(0, -5, 0, 105)
        self.addItem(self.decayLimitLine)
        self.decayLimitLine.setZValue(-1)

        self.decay2LimitLine = LimitLine(0, -5, 0, 105)
        self.addItem(self.decay2LimitLine)
        self.decay2LimitLine.setZValue(-1)

        self.sustainLimitLine = LimitLine(0, -5, 0, 105)
        self.addItem(self.sustainLimitLine)
        self.sustainLimitLine.setZValue(-1)

#        self.envelopePath = QtGui.QPainterPath()
        self.envelopePathItem = self.addPath(QtGui.QPainterPath())
        self.envelopePathItem.setZValue(-1)

        self.attackPath = QtGui.QPainterPath()
        self.decayPath = QtGui.QPainterPath()
        self.decay2Path =  QtGui.QPainterPath()
        self.sustainPath = QtGui.QPainterPath()
        self.releasePath = QtGui.QPainterPath()

        self.loopStart = LoopStart()
        self.addItem(self.loopStart)
        self.loopStart.setPos(10, 70)
        self.loopStart.setZValue(-2)

        self.loopEnd = LoopEnd()
        self.addItem(self.loopEnd)
        self.loopEnd.setPos(90, 70)
        self.loopEnd.setZValue(-2)

        self.loopPath = LoopPath()
        self.addItem(self.loopPath)
        self.loopPath.setPos(0, 70)
        self.loopPath.setZValue(-2)

        self.toolTipWidget = ToolTipWidget()
        self.addItem(self.toolTipWidget)
        self.toolTipWidget.hide()

        self.previewMode = False
        self.setEnvelopeMode(0)
        self.setPreviewMode(False)

    attack = makeEnvProperty('attack')
    attackLevel = makeEnvProperty('attackLevel')
    decay = makeEnvProperty('decay')
    sustain = makeEnvProperty('sustain')
    decay2 = makeEnvProperty('decay2')
    sustain2 = makeEnvProperty('sustain2')
    release = makeEnvProperty('release')

    @property
    def attackLimit(self):
        if self.mode:
            return 20
        return 30

    @property
    def decayLimit(self):
        if self.mode:
            return 15
        return 25

    @property
    def decayLength(self):
        if self.mode:
            return self._decay * 0.1171875
        return self._decay * 0.1953125

    @property
    def decay2Limit(self):
        return 15

    @property
    def decay2Length(self):
        return self._decay2 * 0.1171875

    @property
    def sustainLimit(self):
        return 10 + (65 if self.mode else 60)

    def setPreviewMode(self, state):
        self.previewMode = state
        for child in self.items():
            if isinstance(child, (FocusPoint, LimitLine)):
                child.setVisible(state)
        self.decay2LimitLine.setVisible(self.mode and self.previewMode)
        self.decay2Point.setVisible(self.mode and self.previewMode)
        self.loopPath.setAnimation(state and self.mode >= 3)

    def setEnvelopeMode(self, mode):
        self.mode = mode
        self.decay2LimitLine.setVisible(self.mode and self.previewMode)
        self.decay2Point.setVisible(self.mode and self.previewMode)
        self.loopPath.setAnimation(self.mode >= 3 and self.previewMode)

        self.attackPoint.blockSignals(True)
        self.decayPoint.blockSignals(True)
        loop = True if self.mode >= 3 else False
        self.loopStart.setVisible(loop)
        self.loopEnd.setVisible(loop)
        self.loopPath.setVisible(loop)
        if self.mode:
            self.attackPoint.setX(10 + self._attack * 0.15625)
            self.attackPoint.setY(90 - self._attackLevel * .625)
            self.decayPoint.setX(self.attackPoint.x() + self._decay * 0.1171875)
            self.decay2Point.blockSignals(True)
            self.decay2Point.setX(self.decayPoint.x() + self.decay2Length)
            self.decay2Point.setY(self.sustainPoint.y())
            self.decay2Point.blockSignals(False)
            self.decay2LimitLine.setX(self.decayPoint.x() + self.decay2Limit)
            if self.mode == 3:
                self.loopStart.setX(self.attackPoint.x())
                self.loopEnd.setX(self.sustainLimit)
                self.loopPath.setRange(self.attackPoint.x(), self.sustainLimit)
            elif self.mode == 4:
                self.loopStart.setX(self.startPos.x())
                self.loopEnd.setX(self.releasePoint.x())
                self.loopPath.setRange(self.startPos.x(), self.releasePoint.x())
        else:
            self.attackPoint.setX(10 + self._attack * 0.234375)
            self.attackPoint.setY(10)
            self.decayPoint.setX(self.attackPoint.x() + self._decay * 0.1953125)
            self.decayPoint.setY(self.sustainPoint.y())
        self.attackPoint.blockSignals(False)
        self.decayPoint.blockSignals(False)
        self.sustainPoint.blockSignals(True)
        self.sustainPoint.setX(self.sustainLimit)
        self.sustainPoint.blockSignals(False)

        self.rebuildAttackPath()
        self.rebuildDecayPath()
        self.rebuildDecay2Path()
        self.rebuildSustainPath()
        self.rebuildReleasePath()
        self.attackLimitLine.setX(10 + self.attackLimit)
        self.sustainLimitLine.setX(self.sustainLimit)
        self.decayLimitLine.setX(self.attackPoint.x() + self.decayLimit)
        self.rebuildPath()

    def attackMoved(self):
        self.attackPoint.setX(sanitize(10, self.attackPoint.x(), 10 + self.attackLimit))
        self.attack = int((self.attackPoint.x() - 10) * 127 / self.attackLimit)
        if self.mode:
            self.attackPoint.setY(sanitize(10, self.attackPoint.y(), 90))
            self.attackLevel = int((90 - self.attackPoint.y()) * 1.6)
            if self.mode == 3:
                self.loopStart.setX(self.attackPoint.x())
                self.loopPath.setStart(self.attackPoint.x())
        else:
            self.attackPoint.setY(10)
        self.decayPoint.blockSignals(True)
        self.decayPoint.setX(self.attackPoint.x() + self.decayLength)
        self.decayPoint.blockSignals(False)
        self.decay2Point.blockSignals(True)
        self.decay2Point.setX(self.decayPoint.x() + self.decay2Length)
        self.decay2Point.blockSignals(False)
        self.decayLimitLine.setX(self.attackPoint.x() + self.decayLimit)
        self.decay2LimitLine.setX(self.decayPoint.x() + self.decay2Limit)
        self.rebuildAttackPath()
        self.rebuildDecayPath()
        self.rebuildDecay2Path()
        self.rebuildSustainPath()
        self.rebuildPath()

    def decayMoved(self):
        self.decayPoint.setX(sanitize(self.attackPoint.x(), self.decayPoint.x(), self.attackPoint.x() + self.decayLimit))
        self.decay = int((self.decayPoint.x() - self.attackPoint.x()) * 127 / self.decayLimit)
        self.decayPoint.setY(sanitize(10, self.decayPoint.y(), 90))
        self.rebuildDecayPath()
        if self.mode:
            self.decay2Point.blockSignals(True)
            self.decay2Point.setX(self.decayPoint.x() + self.decay2Length)
            self.decay2Point.blockSignals(False)
            self.decay2LimitLine.setX(self.decayPoint.x() + self.decay2Limit)
            self.rebuildDecay2Path()
        else:
            self.sustainPoint.blockSignals(True)
            self.sustainPoint.setY(self.decayPoint.y())
            self.sustainPoint.blockSignals(False)
            self.sustain = int((90 - self.decayPoint.y()) * 1.6)
            self.rebuildReleasePath()
        self.rebuildSustainPath()
        self.rebuildPath()

    def decay2Moved(self):
        self.decay2Point.setX(sanitize(self.decayPoint.x(), self.decay2Point.x(), self.decayPoint.x() + self.decay2Limit))
        self.decay2 = int((self.decay2Point.x() - self.decayPoint.x()) * 127 / self.decay2Limit)
        self.decay2Point.setY(sanitize(10, self.decay2Point.y(), 90))
        self.sustainPoint.blockSignals(True)
        self.sustainPoint.setY(self.decay2Point.y())
        self.sustainPoint.blockSignals(False)
        self.sustain2 = int((90 - self.decay2Point.y()) * 1.6)
        self.rebuildDecay2Path()
        self.rebuildSustainPath()
        self.rebuildReleasePath()
        self.rebuildPath()

    def sustainMoved(self):
#        self.sustainPoint.setX(sanitize(self.decay2Point.x(), self.sustainPoint.x(), 90))
        self.sustainPoint.setX(self.sustainLimit)
        self.sustainPoint.setY(sanitize(10, self.sustainPoint.y(), 90))
        self.sustain = int((90 - self.sustainPoint.y()) * 1.6)
        if self.mode:
            self.decay2Point.blockSignals(True)
            self.decay2Point.setY(self.sustainPoint.y())
            self.decay2Point.blockSignals(False)
            self.rebuildDecay2Path()
        else:
            self.decayPoint.blockSignals(True)
            self.decayPoint.setY(self.sustainPoint.y())
            self.decayPoint.blockSignals(False)
            self.rebuildDecayPath()
        self.rebuildSustainPath()
        self.rebuildReleasePath()
        self.rebuildPath()

    def releaseMoved(self):
        self.releasePoint.setX(sanitize(self.sustainLimit, self.releasePoint.x(), 90))
        self.releasePoint.setY(90)
        self.release = int((self.releasePoint.x() - self.sustainLimit) / (90 - self.sustainLimit) * 127)
        if self.mode == 4:
            self.loopEnd.setX(self.releasePoint.x())
            self.loopPath.setEnd(self.releasePoint.x())
        self.rebuildReleasePath()
        self.rebuildPath()

    def rebuildPath(self):
        envelopePath = QtGui.QPainterPath()
        envelopePath.addPath(self.attackPath)
        envelopePath.addPath(self.decayPath)
        if self.mode:
            envelopePath.addPath(self.decay2Path)
        envelopePath.addPath(self.sustainPath)
        envelopePath.addPath(self.releasePath)
        self.envelopePathItem.setPath(envelopePath)

    def rebuildAttackPath(self):
        self.attackPath = QtGui.QPainterPath()
        self.attackPath.moveTo(self.startPos)
        self.attackPath.lineTo(self.attackPoint.pos())

    def rebuildDecayPath(self):
        self.decayPath = QtGui.QPainterPath()
        self.decayPath.moveTo(self.attackPoint.pos())
        self.decayPath.quadTo(self.attackPoint.x(), self.decayPoint.y(), self.decayPoint.x(), self.decayPoint.y())

    def rebuildDecay2Path(self):
        self.decay2Path = QtGui.QPainterPath()
        self.decay2Path.moveTo(self.decayPoint.pos())
        self.decay2Path.quadTo(self.decayPoint.x(), self.decay2Point.y(), self.decay2Point.x(), self.decay2Point.y())

    def rebuildSustainPath(self):
        self.sustainPath = QtGui.QPainterPath()
        if self.mode:
            self.sustainPath.moveTo(self.decay2Point.pos())
        else:
            self.sustainPath.moveTo(self.decayPoint.pos())
        self.sustainPath.lineTo(self.sustainPoint.pos())

    def rebuildReleasePath(self):
        self.releasePath = QtGui.QPainterPath()
        self.releasePath.moveTo(self.sustainPoint.pos())
        self.releasePath.quadTo(self.sustainPoint.x(), self.releasePoint.y(), self.releasePoint.x(), self.releasePoint.y())
        self.releasePath.lineTo(self.endPos)

    def attackChanged(self, attack):
        if attack == self._attack:
            return
        self._attack = attack
        self.attackPoint.blockSignals(True)
        self.attackPoint.setX(10 + attack * (0.15625 if self.mode else 0.234375))
        self.attackPoint.blockSignals(False)
        self.decayPoint.blockSignals(True)
        self.decayPoint.setX(self.attackPoint.x() + self.decayLength)
        self.decayPoint.blockSignals(False)
        self.decay2Point.blockSignals(True)
        self.decay2Point.setX(self.decayPoint.x() + self.decay2Length)
        self.decay2Point.blockSignals(False)
        self.decayLimitLine.setX(self.attackPoint.x() + self.decayLimit)
        self.decay2LimitLine.setX(self.decayPoint.x() + self.decay2Limit)
        self.rebuildAttackPath()
        self.rebuildDecayPath()
        self.rebuildDecay2Path()
        self.rebuildSustainPath()
        self.rebuildPath()

    def decayChanged(self, decay):
        if decay == self._decay:
            return
        self._decay = decay
        self.decayPoint.blockSignals(True)
        self.decayPoint.setX(self.attackPoint.x() + self.decayLength)
        self.decayPoint.blockSignals(False)
        self.rebuildDecayPath()
        if self.mode:
            self.decay2LimitLine.setX(self.decayPoint.x() + self.decay2Limit)
            self.rebuildDecay2Path()
        self.rebuildSustainPath()
        self.rebuildPath()

    def sustainChanged(self, sustain):
        if sustain == self._sustain:
            return
        self._sustain = sustain
        self.decayPoint.blockSignals(True)
        self.decayPoint.setY(90 - sustain * .625)
        self.decayPoint.blockSignals(False)
        self.rebuildDecayPath()
        if self.mode:
            self.rebuildDecay2Path()
        self.rebuildSustainPath()
        self.rebuildReleasePath()
        self.rebuildPath()

    def releaseChanged(self, release):
        if release == self._release:
            return
        self._release = release
        self.releasePoint.blockSignals(True)
        self.releasePoint.setX(self.sustainLimit + release * (90 - self.sustainLimit) / 127)
        self.releasePoint.blockSignals(False)
        self.rebuildReleasePath()
        self.rebuildPath()

    def attackLevelChanged(self, attackLevel):
        if attackLevel == self._attackLevel:
            return
        self._attackLevel = attackLevel
        self.attackPoint.blockSignals(True)
        self.attackPoint.setY(90 - attackLevel * .625)
        self.attackPoint.blockSignals(False)
        self.rebuildAttackPath()
        self.rebuildDecayPath()
        self.rebuildPath()

    def decay2Changed(self, decay2):
        if decay2 == self._decay2:
            return
        self._decay2 = decay2
        self.decay2Point.blockSignals(True)
        self.decay2Point.setX(self.decayPoint.x() + self.decay2Length)
        self.decay2Point.blockSignals(False)
        self.rebuildDecayPath()
        self.rebuildDecay2Path()
        self.rebuildSustainPath()
        self.rebuildPath()

    def sustain2Changed(self, sustain2):
        if sustain2 == self._sustain2:
            return
        self._sustain2 = sustain2
        self.sustainPoint.blockSignals(True)
        self.sustainPoint.setY(90 - sustain2 * .625)
        self.sustainPoint.blockSignals(False)
        if self.mode:
            self.decay2Point.blockSignals(True)
            self.decay2Point.setY(self.sustainPoint.y())
            self.decay2Point.blockSignals(False)
            self.rebuildDecay2Path()
        else:
            self.decayPoint.blockSignals(True)
            self.decayPoint.setY(self.sustainPoint.y())
            self.decayPoint.blockSignals(False)
            self.rebuildDecayPath()
        self.rebuildSustainPath()
        self.rebuildReleasePath()
        self.rebuildPath()

    def mainView(self):
        try:
            return self._mainView
        except:
            for view in self.views():
                if isinstance(view, EnvelopeView):
                    break
            self._mainView = view
            return view

    def mouseMoveEvent(self, event):
        if self.mouseGrabberItem():
            item = self.mouseGrabberItem()
        else:
            item = self.itemAt(event.scenePos())
        if isinstance(item, FocusPoint):
            if item == self.attackPoint:
                self.toolTipWidget.showMessage('Attack: {}\nAttack Level: {}'.format(self.attack, self.attackLevel))
            elif item == self.decayPoint:
                self.toolTipWidget.showMessage('Decay: {}\nSustain: {}'.format(self.decay, self.sustain))
            elif item == self.decay2Point:
                self.toolTipWidget.showMessage('Decay 2: {}\nSustain 2: {}'.format(self.decay2, self.sustain2))
            elif item == self.sustainPoint:
                self.toolTipWidget.showMessage('Sustain: {}'.format(self.sustain2 if self.mode else self.sustain))
            else:
                self.toolTipWidget.showMessage('Release: {}'.format(self.release))
            size = self.toolTipWidget.size()
            mainView = self.mainView()
            sceneTransform = mainView.transform()
#            pos = sceneTransform.map(event.scenePos())
            pos = sceneTransform.map(item.pos())
            sceneRect = sceneTransform.mapRect(self.sceneRect())
            if pos.x() + size.width() + 10 > sceneRect.right():
#                x = min(pos.x() - size.width() - 10, sceneRect.right() - size.width())
                x = sceneRect.right() - size.width()
            else:
                x = max(pos.x() + 10, 2)
            if pos.y() + size.height() + 10 > sceneRect.bottom():
                y = min(pos.y() - size.height() - 10, sceneRect.bottom() - size.height())
            else:
                y = max(pos.y() + 10, 2)
            self.toolTipWidget.setPos(mainView.mapToScene(x, y))
        else:
            self.toolTipWidget.hide()
        QtWidgets.QGraphicsScene.mouseMoveEvent(self, event)


class BaseEnvelopeView(QtWidgets.QGraphicsView):
    def __init__(self, *args, **kwargs):
        QtWidgets.QGraphicsView.__init__(self, *args, **kwargs)
        self.setRenderHints(QtGui.QPainter.Antialiasing)
        self.setFrameShape(0)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setStyleSheet('''
            BaseEnvelopeView {
                background: rgba(240, 250, 250, 230);
                border-left: 1px solid palette(mid);
                border-right: 1px solid palette(midlight);
                border-top: 1px solid palette(mid);
                border-bottom: 1px solid palette(midlight);
            }
            EnvelopeView {
                border-radius: 2px;
            }
            EnvelopePreview {
                border-radius: 1px;
            }
            ''')

    def setScene(self, scene):
        QtWidgets.QGraphicsView.setScene(self, scene)
#        self.translate(.5, .5)
        self.fitInView(scene.sceneRect())

    def resizeEvent(self, event):
        self.fitInView(self.sceneRect())


class EnvelopeView(BaseEnvelopeView):
    def __init__(self, parent, envName):
        BaseEnvelopeView.__init__(self, parent)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored))
        self.envName = envName
        scene = EnvelopeScene(parent, envName)
        self.setScene(scene)
#        self.translate(.5, .5)
        self.preview = getattr(parent, '{}Preview'.format(envName))
        self.preview.view.setScene(scene)
        self.closeBtn = CloseBtn(self)
        self.closeBtn.setToolTip('Close envelope editor')
        self.closeBtn.clicked.connect(self.hide)
        self.shown = False

    def hideEvent(self, event):
        self.preview.show()
        self.scene().setPreviewMode(False)

    def showEvent(self, event):
        if not self.shown:
            self.shown = True
            self.closeBtn.move(self.width() - self.closeBtn.width(), self.closeBtn.y())
        self.preview.hide()
        self.scene().setPreviewMode(True)

    def sizeHint(self):
        return QtCore.QSize(120, 60)

    def resizeEvent(self, event):
        self.closeBtn.move(self.width() - self.closeBtn.width(), self.closeBtn.y())
        BaseEnvelopeView.resizeEvent(self, event)


class EnvelopePreview(BaseEnvelopeView):
    clicked = QtCore.pyqtSignal()

    def __init__(self, *args, **kwargs):
        BaseEnvelopeView.__init__(self, *args, **kwargs)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Preferred))
        self.setMinimumSize(40, 30)

    def mouseReleaseEvent(self, event):
        if event.pos() in self.rect():
            self.clicked.emit()

    def sizeHint(self):
        return QtCore.QSize(40, 30)

    def resizeEvent(self, event):
#        self.setMaximumHeight(self.width() * .75)
        self.resize(self.width(), self.width() * .75)
        BaseEnvelopeView.resizeEvent(self, event)


class PreviewMaximizeBtn(QtWidgets.QPushButton):
    pressedStyleSheet = '''
        PreviewMaximizeBtn:pressed {
            border-radius: 2px;
            border-left: 1px solid palette(mid);
            border-right: 1px solid palette(midlight);
            border-top: 1px solid palette(mid);
            border-bottom: 1px solid palette(midlight);
        }'''
    normalStyleSheet = '''
        PreviewMaximizeBtn {
            border: none;
        }''' + pressedStyleSheet
    hoverStyleSheet = '''
        PreviewMaximizeBtn {
            border-radius: 2px;
            border-left: 1px solid palette(midlight);
            border-right: 1px solid palette(mid);
            border-top: 1px solid palette(midlight);
            border-bottom: 1px solid palette(mid);
        }''' + pressedStyleSheet
    styleSheets = normalStyleSheet, hoverStyleSheet

    arrowPath = QtGui.QPainterPath()
    arrowPath.moveTo(0, 5)
    arrowPath.lineTo(3, 1)
    arrowPath.lineTo(6, 5)
    arrowPen = QtGui.QPen(QtCore.Qt.darkGray, 1.5, cap=QtCore.Qt.RoundCap)

    def __init__(self):
        QtWidgets.QPushButton.__init__(self)
        self.setMaximumHeight(8)
        self.setMinimumHeight(8)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum))
        self.setStyleSheet(self.normalStyleSheet)
        self.paintEvent = lambda event: QtWidgets.QPushButton.paintEvent(self, event)

    def setHover(self, state):
        self.setStyleSheet(self.styleSheets[state])
        self.paintEvent = self.hoverPaintEvent if state else lambda event: QtWidgets.QPushButton.paintEvent(self, event)

    def normalPaintEvent(self, event):
        qp = QtGui.QPainter(self)
        qp.translate(.5, .5)
#        qp.setBrush(QtCore.Qt.darkGray)
        qp.drawRect(self.rect().adjusted(0, 0, -1, -1))

    def hoverPaintEvent(self, event):
        QtWidgets.QPushButton.paintEvent(self, event)
        count = self.width() // 16
        ratio = float(self.width()) / count
        qp = QtGui.QPainter(self)
        qp.setRenderHints(qp.Antialiasing)
        qp.translate(-3 + ratio * .5, .5)
        qp.setPen(self.arrowPen)
        for c in range(count):
            qp.drawPath(self.arrowPath)
            qp.translate(ratio, 0)

class EnvelopePreviewWidget(QtWidgets.QWidget):
    clicked = QtCore.pyqtSignal()

    def __init__(self, *args, **kwargs):
        QtWidgets.QWidget.__init__(self, *args, **kwargs)
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        self.maximizeBtn = PreviewMaximizeBtn()
        layout.addWidget(self.maximizeBtn)
        self.maximizeBtn.clicked.connect(self.clicked)

        self.view = EnvelopePreview(self)
        layout.addWidget(self.view)
        self.view.clicked.connect(self.clicked)

        self.setToolTip('Open envelope editor')

    def enterEvent(self, event):
        self.maximizeBtn.setHover(True)

    def leaveEvent(self, event):
        self.maximizeBtn.setHover(False)

    def sizeHint(self):
        return QtCore.QSize(40, 30)


