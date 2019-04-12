import sys
from Qt import QtCore, QtGui, QtWidgets, __binding__
QtCore.pyqtSignal = QtCore.Signal
QtCore.pyqtProperty = QtCore.Property
QtCore.pyqtSlot = QtCore.Slot

if __binding__ == 'PyQt4':
    QtCore.Qt.TopEdge = QtCore.Qt.TopDockWidgetArea
    QtCore.Qt.LeftEdge = QtCore.Qt.LeftDockWidgetArea
    QtCore.Qt.RightEdge = QtCore.Qt.RightDockWidgetArea
    QtCore.Qt.BottomEdge = QtCore.Qt.BottomDockWidgetArea
    QtCore.Qt.Edge = QtCore.Qt.DockWidgetArea
else:
    from PyQt5.QtCore import Q_FLAGS
    QtCore.Q_FLAGS = Q_FLAGS

LabelPositions = {
    QtCore.Qt.TopEdge: (1, 2, QtCore.Qt.AlignHCenter|QtCore.Qt.AlignBottom), 
    QtCore.Qt.LeftEdge: (2, 1, QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter),  
    QtCore.Qt.RightEdge: (2, 3, QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter), 
    QtCore.Qt.BottomEdge: (3, 2, QtCore.Qt.AlignHCenter|QtCore.Qt.AlignTop), 
    }

#def makeQProperty(type, name, actions=None, *args, **kwargs):
#    def getter(self):
#        return getattr(self, name)
#    def setter(self, value):
#        setattr(self, name, value)
#        if actions:
#            [getattr(self, a)() for a in actions]
#    return QtCore.pyqtProperty(type, getter, setter, *args, **kwargs)

def makeQtProperty(propertyType, name, actions=None, signal=None, *args, **kwargs):
    def getter(self):
        return getattr(self, name)
    def setter(self, value):
        setattr(self, name, value)
        if actions:
            [a(self) for a in actions]
        if signal:
            getattr(self, signal).emit(value)
    return QtCore.pyqtProperty(propertyType, getter, setter, *args, **kwargs)

def makeQtChildProperty(propertyType, name, fset):
    def getter(self):
        return getattr(self.widget, name)
    def setter(self, value):
        getattr(self.widget, fset)(value)
    return QtCore.pyqtProperty(propertyType, getter, setter)

def makeQtFlag(flagType, name, actions=None, flags=None, zero=None, *args, **kwargs):
    def getter(self):
        return getattr(self, name)
    def setter(self, value):
        prev = getattr(self, name)
        _value = 0
        if flags:
            if value == 0 or (value & zero and not prev & zero):
                setattr(self, name, zero)
            else:
                if value & zero:
                    value ^= zero
                for mask, default in flags:
#                    print('prev: {} ({}) next: {} ({}) mask: {}'.format(prev, bin(prev), value, bin(value), bin(mask)))
                    prevMask = (prev & mask)
                    newMask = (value & mask)
                    if newMask == 0 and newMask != default:
                        _value += default
                    elif prevMask == newMask:
                        _value += prevMask
                    else:
                        _value += (prev & mask) ^ (value & mask)
#                    print('value: {} ({})'.format(_value, bin(_value)))
                setattr(self, name, _value)
        if actions:
            [a(self) for a in actions]
    return QtCore.pyqtProperty(flagType, getter, setter, *args, **kwargs)

def _getCssQFontStr(font):
#    print(font.pointSize(), font.family())
    return('{bold}{size}pt {family}'.format(
        bold='bold ' if font.weight() > font.Normal else '', 
        size=font.pointSize(), 
        family=font.family(), 
        ))

if __binding__ == 'PyQt4':
    def _getCssQColorStr(color):
        return 'rgba({},{},{},{:.0f}%)'.format(color.red(), color.green(), color.blue(), color.alphaF() * 100)
else:
    def _getCssQColorStr(color):
        return 'rgba({},{},{},{})'.format(color.red(), color.green(), color.blue(), color.alphaF())

def _getCssQColor255(color):
    return 'rgba({},{},{},{})'.format(*color.getRgb())

class QColorStr(QtGui.QColor):
    def __str__(self):
        return 'rgba({},{},{},{})'.format(self.red(), self.green(), self.blue(), self.alphaF())


#class MetaWidget(object):
#
#    labelChanged = QtCore.pyqtSignal(str)
#    labelPosChanged = QtCore.pyqtSignal(QtCore.Qt.Edge)
#
#    def __init__(self, label='', labelPos=QtCore.Qt.BottomEdge, labelColor=QtCore.Qt.white):
#        self._label = label
#        self._labelPos = labelPos
#        self._labelColor = QtCore.Qt.black
#        #TODO: what?!
#        for _method in ('_paletteChanged', ):
#            try:
#                getattr(self, _method)
#            except:
#                raise NotImplementedError('{}() must be implemented!'.format(_method))
#
#    label = makeQProperty(str, '_label', ('_labelChanged',))
#    labelColor = makeQProperty(QColorStr, '_labelColor', ('update'))
#
#    def setLabel(self, label):
#        self.label = label
#        self.labelChanged.emit(label)
#
#    if __binding__ == 'PyQt4':
#        @QtCore.pyqtProperty(QtCore.Qt.DockWidgetArea)
#        def labelPos(self):
#            return self._labelPos
#    else:
#        @QtCore.pyqtProperty(QtCore.Qt.Edge)
#        def labelPos(self):
#            return self._labelPos
#
#    @labelPos.setter
#    def labelPos(self, labelPos):
#        self._labelPos = labelPos
#        self._labelPosChanged()
#
#    def setLabelPos(self, labelPos):
#        self.labelPos = labelPos
#        self.labelPosChanged.emit(labelPos)
#
#    @QtCore.pyqtProperty(QtGui.QColor)
#    def labelColor(self):
#        return self._labelColor
#
#    @labelColor.setter
#    def labelColor(self, labelColor):
#        self._labelColor = labelColor
#        self._colorsChanged()
#
#
#class Spacer(QtWidgets.QWidget):
#    pass


class BaseWidget(QtWidgets.QWidget):
    labelChanged = QtCore.pyqtSignal(str)
    labelPosChanged = QtCore.pyqtSignal(QtCore.Qt.Edge)

    def __init__(self, parent=None, label='', labelPos=QtCore.Qt.BottomEdge):
        QtWidgets.QWidget.__init__(self, parent)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred))
        self._label = label
        self._labelPos = labelPos
        self._labelMargin = 2
        layout = QtWidgets.QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(self._labelMargin)
        layout.setVerticalSpacing(self._labelMargin)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(4, 1)
        layout.setRowStretch(0, 1)
        layout.setRowStretch(4, 1)
        self.setLayout(layout)
        self.spacers = []
        for gridPos in ((0, 2), (2, 0), (2, 4), (4, 2)):
#            continue
#            i = QtWidgets.QWidget()
#            i.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred))
#            i.setStyleSheet('QWidget {background: green;}')
#            layout.addWidget(i, *gridPos)
            spacer = QtWidgets.QSpacerItem(10, 10, QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
            layout.addItem(spacer, *gridPos)
            self.spacers.append(spacer)
        self._spacerSizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self._labelWidget = QtWidgets.QLabel(label)
        self._labelWidget.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Maximum))
        if label:
            x, y, labelAlign = LabelPositions[labelPos]
            layout.addWidget(self._labelWidget, x, y, 1, 1, labelAlign)
#            self._labelWidget.setAlignment(labelAlign)
        self._labelAlignAuto = True
        self._labelAlign = self.LabelAlignment.AlignAuto if __binding__ == 'PyQt5' else QtCore.Qt.Alignment(0)
        for _method in ('_paletteChanged', ):
            try:
                getattr(self, _method)
            except:
                raise NotImplementedError('{}() must be implemented!'.format(_method))

    def setWidget(self, widget):
        self.widget = widget
#        self._minimumWidgetSize = QtCore.QSize(self.widget._minWidth, self.widget._minHeight)
        self.layout().addWidget(widget, 2, 2)
        self.layout().setRowStretch(0, 1)
        self.layout().setRowStretch(1, 1)
        self.layout().setRowStretch(2, 98)
        self.layout().setRowStretch(3, 1)
        self.layout().setRowStretch(4, 1)
        self.layout().setColumnStretch(0, 1)
        self.layout().setColumnStretch(1, 1)
        self.layout().setColumnStretch(2, 98)
        self.layout().setColumnStretch(3, 1)
        self.layout().setColumnStretch(4, 1)

    def sizeHint(self):
        widgetSize = self.widget.sizeHint()

        maxSize = self.widget.maximumSize()
        if maxSize.width() < widgetSize.width():
            widgetSize.setWidth(maxSize.width())
        if maxSize.height() < widgetSize.height():
            widgetSize.setHeight(maxSize.height())

        l, t, r, b = self.layout().getContentsMargins()

        if not self._label:
            width = widgetSize.width() + l + r
            height = widgetSize.height() + t + b
        else:
            labelSize = self._labelWidget.minimumSizeHint()
            if self._labelPos & (QtCore.Qt.TopEdge|QtCore.Qt.BottomEdge):
                width = max(widgetSize.width(), labelSize.width()) + l + r
                height = widgetSize.height() + labelSize.height() + self._labelMargin + t + b
            else:
                width = widgetSize.width() + labelSize.width() + self._labelMargin + l + r
                height = max(widgetSize.height(), labelSize.height()) + t + b
        return QtCore.QSize(width, height)

#        try:
#            text = self._label.decode('string_escape') if sys.version_info.major==2 else bytes(self._label, 'utf-8').decode('unicode_escape')
#        except:
#            pass
#        textSize = self.fontMetrics().size(QtCore.Qt.TextExpandTabs, text)
#        if self._labelPos & (QtCore.Qt.TopEdge|QtCore.Qt.BottomEdge):
#            return QtCore.QSize(max(textSize.width(), widgetSize.width()), (textSize + widgetSize).height() + self._labelMargin)
#        else:
#            return QtCore.QSize((textSize + widgetSize).width() + self._labelMargin, max(textSize.height(), widgetSize.height()))

    def minimumSizeHint(self):
        widgetSize = self.widget.minimumSize()
        if widgetSize.isNull():
            widgetSize = self.widget.minimumSizeHint()
            if widgetSize.isNull():
                widgetSize = self.widget.sizeHint()

        l, t, r, b = self.layout().getContentsMargins()

        if not self._label:
            width = widgetSize.width() + l + r
            height = widgetSize.height() + t + b
        else:
            labelSize = self._labelWidget.minimumSize()
            if labelSize.isNull():
                labelSize = self._labelWidget.minimumSizeHint()
            if self._labelPos & (QtCore.Qt.TopEdge|QtCore.Qt.BottomEdge):
                width = max(widgetSize.width(), labelSize.width()) + l + r
                height = widgetSize.height() + labelSize.height() + self._labelMargin + t + b
            else:
                width = widgetSize.width() + labelSize.width() + self._labelMargin + l + r
                height = max(widgetSize.height(), labelSize.height()) + t + b
        return QtCore.QSize(width, height)

#        try:
#            text = self._label.decode('string_escape') if sys.version_info.major==2 else bytes(self._label, 'utf-8').decode('unicode_escape')
#        except:
#            pass
#        textSize = self.fontMetrics().size(QtCore.Qt.TextExpandTabs, text)
##        textSize.setWidth(textSize.width() + 2)
#        if self._labelPos & (QtCore.Qt.TopEdge|QtCore.Qt.BottomEdge):
#            return QtCore.QSize(max(textSize.width(), widgetSize.width()), (textSize + widgetSize).height() + self._labelMargin)
#        else:
#            return QtCore.QSize((textSize + widgetSize).width() + self._labelMargin, max(textSize.height(), widgetSize.height()))

    def _paletteChanged(self, palette):
        self.widget.setPalette(palette)

    def _fontChanged(self, font):
        self.widget.setFont(font)

    def _labelChanged(self):
        try:
            self._labelWidget.setText(self.label.decode('string_escape') if sys.version_info.major==2 else bytes(self.label, 'utf-8').decode('unicode_escape'))
        except:
            self._labelWidget.setText(self.label)
        if not self.label:
            try:
                self.layout().removeWidget(self._labelWidget)
            except:
                print('Label not visible')
        else:
            x, y, labelAlign = LabelPositions[self._labelPos]
            if __binding__ == 'PyQt5':
                if self._labelAlign != self.LabelAlignment.AlignAuto:
                    labelAlign = self._labelAlign
            else:
                if self._labelAlign:
                    labelAlign = self._labelAlign
            self.layout().addWidget(self._labelWidget, x, y, 1, 1, labelAlign)
#            self._labelWidget.setAlignment(QtCore.Qt.AlignmentFlag(labelAlign))
            self.adjustSize()

    label = makeQtProperty(str, '_label', (_labelChanged,))

    @QtCore.pyqtProperty(QtCore.Qt.Alignment)
    def labelTextAlign(self):
        return self._labelWidget.alignment()

    @labelTextAlign.setter
    def labelTextAlign(self, alignment):
        self._labelWidget.setAlignment(alignment)


    def _labelPosChanged(self):
        if not self._label: return
        x, y, labelAlign = LabelPositions[self._labelPos]
        if __binding__ == 'PyQt5':
            if self._labelAlign != self.LabelAlignment.AlignAuto:
                labelAlign = self._labelAlign
        else:
            if self._labelAlign:
                labelAlign = self._labelAlign
        self.layout().addWidget(self._labelWidget, x, y, 1, 1, labelAlign)
#        self._labelWidget.setAlignment(QtCore.Qt.AlignmentFlag(labelAlign))
        self.adjustSize()

    def _labelMarginChanged(self):
        self.layout().setHorizontalSpacing(self._labelMargin)
        self.layout().setVerticalSpacing(self._labelMargin)

    def _labelAlignChanged(self):
        if (__binding__ == 'PyQt5' and self._labelAlign == self.LabelAlignment.AlignAuto) or not self._labelAlign:
            x, y, labelAlign = LabelPositions[self._labelPos]
        else:
            labelAlign = self._labelAlign
#        self._labelWidget.setAlignment(QtCore.Qt.AlignmentFlag(labelAlign))
        self.layout().setAlignment(self._labelWidget, QtCore.Qt.AlignmentFlag(labelAlign))

    labelPos = makeQtProperty(QtCore.Qt.Edge, '_labelPos', (_labelPosChanged,))
    labelMargin = makeQtProperty(int, '_labelMargin', (_labelMarginChanged,))

    if __binding__ == 'PyQt5':
        class LabelAlignment(object):
            AlignAuto = 256
            AlignLeft = int(QtCore.Qt.AlignLeft)
            AlignHCenter = int(QtCore.Qt.AlignHCenter)
            AlignRight = int(QtCore.Qt.AlignRight)
            AlignTop = int(QtCore.Qt.AlignTop)
            AlignVCenter = int(QtCore.Qt.AlignVCenter)
            AlignBottom = int(QtCore.Qt.AlignBottom)
        QtCore.Q_FLAGS(LabelAlignment)
        labelAlign = makeQtFlag(
            LabelAlignment, 
            '_labelAlign', 
            (_labelAlignChanged, ), 
            flags=(
                (LabelAlignment.AlignTop|LabelAlignment.AlignBottom|LabelAlignment.AlignVCenter, LabelAlignment.AlignVCenter), 
                (LabelAlignment.AlignLeft|LabelAlignment.AlignRight|LabelAlignment.AlignHCenter, LabelAlignment.AlignHCenter), 
            ), 
            zero=(LabelAlignment.AlignAuto)
            )
    else:
        class LabelAlignment:
            AlignAuto = QtCore.Qt.Alignment(256)
            AlignLeft = QtCore.Qt.AlignLeft
            AlignHCenter = QtCore.Qt.AlignHCenter
            AlignRight = QtCore.Qt.AlignRight
            AlignTop = QtCore.Qt.AlignTop
            AlignVCenter = QtCore.Qt.AlignVCenter
            AlignBottom = QtCore.Qt.AlignBottom

        @QtCore.pyqtProperty(bool)
        def labelAlignAuto(self):
            return self._labelAlignAuto

        @labelAlignAuto.setter
        def labelAlignAuto(self, state):
            if state:
                self._labelAlign = QtCore.Qt.Alignment(0)
                self._labelAlignChanged()
            else:
                if not self._labelAlign:
                    self._labelAlign = QtCore.Qt.AlignCenter
                    self._labelAlignChanged()
            self._labelAlignAuto = state

        @QtCore.pyqtProperty(QtCore.Qt.Alignment)
        def labelAlign(self):
            return self._labelAlign

        @labelAlign.setter
        def labelAlign(self, labelAlign):
            if not labelAlign:
                self._labelAlign = labelAlign
                if not self._labelAlignAuto:
                    self._labelAlignAuto = True
            else:
                if self._labelAlignAuto:
                    self._labelAlignAuto = False
                hMask = QtCore.Qt.AlignLeft|QtCore.Qt.AlignHCenter|QtCore.Qt.AlignRight
                vMask = QtCore.Qt.AlignVertical_Mask
                horizontalNew = labelAlign & hMask
                verticalNew = labelAlign & vMask
                horizontalOld = self._labelAlign & hMask
                verticalOld = self._labelAlign & vMask
                if horizontalNew != horizontalOld:
                    horizontalNew = (horizontalNew & horizontalOld) ^ horizontalNew
                if not horizontalNew & hMask or int(horizontalNew) > int(QtCore.Qt.AlignHCenter):
                    horizontalNew = QtCore.Qt.AlignHCenter
                if verticalNew != verticalOld:
                    verticalNew = (verticalNew & verticalOld) ^ verticalNew
                if not verticalNew & vMask or int(verticalNew) > int(QtCore.Qt.AlignVCenter):
                    verticalNew = QtCore.Qt.AlignVCenter
                self._labelAlign = horizontalNew | verticalNew
            self._labelAlignChanged()

    @QtCore.pyqtProperty(QtWidgets.QSizePolicy, stored=False)
    def widgetSizePolicy(self):
        return self.widget.sizePolicy()

    @widgetSizePolicy.setter
    def widgetSizePolicy(self, sizePolicy):
        self.widget.setSizePolicy(sizePolicy)
        self.hWidgetSizePolicy = int(sizePolicy.horizontalPolicy())
        self.vWidgetSizePolicy = int(sizePolicy.verticalPolicy())

    @QtCore.pyqtProperty(int)
    def hWidgetSizePolicy(self):
        return int(self.widget.sizePolicy().horizontalPolicy())

    @hWidgetSizePolicy.setter
    def hWidgetSizePolicy(self, hPolicy):
        policy = self.widget.sizePolicy()
        policy.setHorizontalPolicy(QtWidgets.QSizePolicy.Policy(hPolicy))
        self.widget.setSizePolicy(policy)

    @QtCore.pyqtProperty(int)
    def vWidgetSizePolicy(self):
        return int(self.widget.sizePolicy().verticalPolicy())

    @vWidgetSizePolicy.setter
    def vWidgetSizePolicy(self, vPolicy):
        policy = self.widget.sizePolicy()
        policy.setVerticalPolicy(QtWidgets.QSizePolicy.Policy(vPolicy))
        self.widget.setSizePolicy(policy)

    @QtCore.pyqtProperty(QtCore.QSize)
    def minimumWidgetSize(self):
#        return self._minimumWidgetSize
        return self.widget.minimumSize()

    @minimumWidgetSize.setter
    def minimumWidgetSize(self, size):
        if isinstance(size, QtCore.QSize):
            minWidth = size.width()
            minHeight = size.height()
        elif isinstance(size, int):
            minWidth = minHeight = size
        elif isinstance(size, (tuple, list)):
            minWidth, minHeight = size
        if minWidth < self.widget._minWidth:
            minWidth = self.widget._minWidth
        if minHeight < self.widget._minHeight:
            minHeight = self.widget._minHeight
        #TODO: serve davvero una variabile apposta?
#        self._minimumWidgetSize = QtCore.QSize(minWidth, minHeight)
        self.widget.setMinimumSize(QtCore.QSize(minWidth, minHeight))

    @QtCore.pyqtProperty(QtCore.QSize)
    def maximumWidgetSize(self):
        return self.widget.maximumSize()

    @maximumWidgetSize.setter
    def maximumWidgetSize(self, size):
        if isinstance(size, QtCore.QSize):
            maxWidth = size.width()
            maxHeight = size.height()
        elif isinstance(size, int):
            maxWidth = maxHeight = size
        elif isinstance(size, (tuple, list)):
            maxWidth, maxHeight = size
        if maxWidth < self.widget._minWidth:
            maxWidth = self.widget._minWidth
        if maxHeight < self.widget._minHeight:
            maxHeight = self.widget._minHeight
        self.widget.setMaximumSize(QtCore.QSize(maxWidth, maxHeight))

    def changeEvent(self, event):
        if event.type() == QtCore.QEvent.EnabledChange:
#            self._enabledChange()
            self.update()
        elif event.type() == QtCore.QEvent.PaletteChange:
            self._paletteChanged(self.palette())
        elif event.type() == QtCore.QEvent.FontChange:
            self._fontChanged(self.font())

#    def paintEvent(self, event):
    def paintEventDebug(self, event):
        qp = QtGui.QPainter(self)
        qp.setPen(QtCore.Qt.darkRed)
        qp.drawRect(self.rect().adjusted(0, 0, -1, -1))
        qp.drawRect(self.widget.geometry().adjusted(-1, -1, 0, 0))
        qp.drawRect(self._labelWidget.geometry().adjusted(0, 0, -1, -1))
        qp.drawLine(0, self.height() / 2, self.width(), self.height() / 2)
        qp.drawLine(self.width() / 2, 0, self.width() / 2, self.height())
        qp.drawRect(self.widget.geometry())

    def paintEventFocus(self, event):
        if not self.hasFocus():
            return
        qp = QtGui.QPainter(self)
        qp.setPen(QtCore.Qt.lightGray)
        qp.drawRect(self.rect().adjusted(0, 0, -1, -1))

class ColorValueWidget(BaseWidget):
    pass



