#!/usr/bin/env python

from Qt import QtCore, QtGui, QtWidgets
from metawidget import BaseWidget, _getCssQColorStr, _getCssQFontStr, makeQtChildProperty
from listview import ListView

try:
    range = xrange
except:
    pass

class _Combo(QtWidgets.QComboBox):
    padding = 1
    _minWidth = 24
    _minHeight = 8
    _minimumSizeHint = QtCore.QSize(_minWidth, _minHeight)
    _minimumDataWidth = _dataWidth = 16
    indexBeforeChange = -1
    resetting = False

    def __init__(self, parent, valueList=None):
        QtWidgets.QComboBox.__init__(self, parent)
        self.setAttribute(QtCore.Qt.WA_LayoutUsesWidgetRect, True)
        self.setMinimumSize(self._minimumSizeHint)
        self._baseStyleSheet = ''
        self.computeMetrics()
        self.addItems(valueList)
#        self.addItems(['aaa', 'bbb', 'ccc', 'ddd', 'aaa', 'bbb', 'ccc', 'ddd', 'aaa', 'bbb', 'ccc', 'ddd'])
        self._setModelSignals()
        #this seems to be necessary to correctly apply css styling
        self.setView(ListView())
        self.opaque = False

    def computeMetrics(self):
        self._metrics = {}
        dpi = (self.logicalDpiX() + self.logicalDpiY()) / 2.
        ratio = 1. / 76 * dpi
        for s in (1, 2, 4, 8, 80):
            self._metrics['{}px'.format(s)] = s * ratio
        self.padding *= ratio

    def _setOpaque(self, opaque):
        self.opaque = opaque
        self.setPalette(self.parent().palette())

    def setFont(self, font):
        self.applyStyleSheet()

    def setPalette(self, palette):
        if self.opaque:
            foreground = palette.color(palette.Active, palette.Text)
            background = palette.color(palette.Active, palette.Base)
        else:
            foreground = palette.color(palette.WindowText)
            background = palette.color(palette.Window)
        foregroundDisabled = QtGui.QColor(foreground)
        foregroundDisabled.setAlpha(128)
        self._baseStyleSheet = '''
            QComboBox {{
                color: {foreground};
                padding: {padding}px;
                border-top: {1px} solid {light};
                border-right: {1px} solid {dark};
                border-bottom: {1px} solid {dark};
                border-left: {1px} solid {light};
                border-radius: {2px};
                background: {background};
            }}
            QComboBox::disabled {{
                color: {foregroundDisabled};
            }}
            QComboBox:on {{
                border-top: {1px} solid {dark};
                border-right: {1px} solid {light};
                border-bottom: {1px} solid {light};
                border-left: {1px} solid {dark};
                border-radius: {2px};
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: right;
                width: {8px};
                border: none;
            }}
            QComboBox::down-arrow {{
                subcontrol-origin: padding;
                subcontrol-position: right;
                width: 0px;
                height: 0px;
                margin-right: {2px};
                border-left: {4px} solid {background};
                border-right: {4px} solid {background};
                border-top: {4px} solid {foreground};
                border-bottom: none;
            }}
            QComboBox::down-arrow:disabled {{
                border-top: {4px} solid {itemFgdColorDisabled};
            }}
            QComboBox::down-arrow:on {{
                border-top: none;
                border-bottom: {4px} solid {foreground};
            }}
            QListView::item:!selected {{
                background: {itemBgdColorEnabled};
                color: {itemFgdColorEnabled};
                min-width: {80px};
            }}
            QListView::item:disabled:!selected {{
                background: {itemBgdColorDisabled};
                color: {itemFgdColorDisabled};
            }}
            QListView::item:selected {{
                background: {selectedItemBgdColorEnabled};
                color: {selectedItemFgdColorEnabled};
            }}
            QListView::item:disabled:selected {{
                background: {selectedItemBgdColorDisabled};
                color: {selectedItemFgdColorDisabled};
            }}
            QComboBox QListView {{
                border: none;
            }}
            '''.format(
                padding=self.padding, 
                foreground=_getCssQColorStr(foreground), 
                foregroundDisabled=_getCssQColorStr(foregroundDisabled), 
                background=_getCssQColorStr(background), 
                light=_getCssQColorStr(palette.color(palette.Midlight)), 
                dark=_getCssQColorStr(palette.color(palette.Dark)), 
                itemBgdColorDisabled=_getCssQColorStr(palette.color(palette.Disabled, palette.Base)), 
                itemFgdColorDisabled=_getCssQColorStr(palette.color(palette.Disabled, palette.Text)), 
                itemBgdColorEnabled=_getCssQColorStr(palette.color(palette.Active, palette.Base)), 
                itemFgdColorEnabled=_getCssQColorStr(palette.color(palette.Active, palette.Text)), 
                selectedItemBgdColorDisabled=_getCssQColorStr(palette.color(palette.Disabled, palette.Highlight)), 
                selectedItemFgdColorDisabled=_getCssQColorStr(palette.color(palette.Disabled, palette.HighlightedText)), 
                selectedItemBgdColorEnabled=_getCssQColorStr(palette.color(palette.Active, palette.Highlight)), 
                selectedItemFgdColorEnabled=_getCssQColorStr(palette.color(palette.Active, palette.HighlightedText)), 
                **self._metrics
                )
        self.applyStyleSheet()
#        print(_getCssQColorStr(palette.color(palette.Active, palette.Text)), _getCssQFontStr(self.font()))

    def applyStyleSheet(self):
        _fontSheet = '''
            QComboBox {{
                font: {font};
            }}
            QListView {{
                font: {font};
                min-width: {width};
            }}
            '''.format(
                font=_getCssQFontStr(self.parent().font()), 
                width=self._dataWidth + 12, 
                )
        self.setStyleSheet(self._baseStyleSheet + _fontSheet)
        self.view().setPalette(self.parent().palette())

    def minimumSizeHint(self):
        return QtCore.QSize(self._dataWidth, self.fontMetrics().height() + self.padding * 2 + 2)

    def sizeHint(self):
        return QtCore.QSize(self._dataWidth, self.fontMetrics().height() + self.padding * 2 + 2)

    def addItems(self, valueList):
        if not valueList: return
        QtWidgets.QComboBox.addItems(self, valueList)
        self._updateDataWidth()

    def _updateDataWidth(self, *args):
        model = self.model()
        if model.rowCount():
            count = model.rowCount()
            self._dataWidth = max([max(self.fontMetrics().width(model.index(i, self.modelColumn()).data()) for i in range(count))] + [self._minimumDataWidth + 16 + self.padding * 2])
        else:
            self._dataWidth = self._minimumDataWidth
        self.applyStyleSheet()
#        self.setStyleSheet(self.styleSheet() + 'QListView {{min-width: {width};}}'.format(width=self._dataWidth + 30))

    def _setModelSignals(self):
        if self.model():
            self.model().columnsInserted.connect(self._updateDataWidth)
            self.model().columnsRemoved.connect(self._updateDataWidth)
            self.model().rowsInserted.connect(self._updateDataWidth)
            self.model().rowsRemoved.connect(self._updateDataWidth)
            self.model().layoutChanged.connect(self._updateDataWidth)
            self.model().modelAboutToBeReset.connect(self.updateIndexBeforeChange)
            self.model().modelReset.connect(self.modelReset)

    def setModel(self, model):
        if self.model():
            self.model().columnsInserted.disconnect(self._updateDataWidth)
            self.model().columnsRemoved.disconnect(self._updateDataWidth)
            self.model().rowsInserted.disconnect(self._updateDataWidth)
            self.model().rowsRemoved.disconnect(self._updateDataWidth)
            self.model().layoutChanged.disconnect(self._updateDataWidth)
            self.model().modelAboutToBeReset.disconnect(self.updateIndexBeforeChange)
            self.model().modelReset.disconnect(self.modelReset)
        QtWidgets.QComboBox.setModel(self, model)
        self._setModelSignals()

    def updateIndexBeforeChange(self):
        self.blockSignals(True)
        self.indexBeforeChange = self.currentIndex()
        self.resetting = True

    def modelReset(self):
        if self.resetting:
            self.setCurrentIndex(self.indexBeforeChange)
        self.blockSignals(False)
        if self.resetting and self.currentIndex() != self.indexBeforeChange:
            self.currentIndexChanged.emit(self.currentIndex())
        self.resetting = False


class Combo(BaseWidget):
#    labelMargin = 2
#    comboPadding = 2
#    arrowDown = QtGui.QPainterPath()
#    arrowDown.moveTo(-4, -2)
#    arrowDown.lineTo(4, -2)
#    arrowDown.lineTo(0, 2)
#    arrowDown.closeSubpath()
#    arrowSize = 8
#    arrowUp = QtGui.QPainterPath()
#    arrowUp.moveTo(-4, 2)
#    arrowUp.lineTo(4, 2)
#    arrowUp.lineTo(0, -2)
#    arrowUp.closeSubpath()
#    arrows = arrowDown, arrowUp
#
    currentIndexChanged = QtCore.pyqtSignal(int)

    def __init__(self, parent=None, label='combo', labelPos=QtCore.Qt.BottomEdge, valueList=None):
#        self._minimumWidgetSize = QtCore.QSize(self._minWidth, self._minHeight)
        BaseWidget.__init__(self, parent, label, labelPos)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed))
        self.combo = _Combo(self, valueList)
        self.combo.currentIndexChanged.connect(self.currentIndexChanged)
        self.valueList = valueList if valueList is not None else []
        self.setWidget(self.combo)
#        self.model = self.combo.model()
#        self.setFont(QtGui.QFont('Droid Sans', 9, QtGui.QFont.Bold))
        self._paletteChanged(self.palette())
        self.setModel = self.combo.setModel
        self.setModelColumn = self.combo.setModelColumn
        self.itemText = self.combo.itemText
        self.setExpanding = self.combo.view().setExpanding

    opaque = makeQtChildProperty(bool, 'opaque', '_setOpaque')

    @property
    def model(self):
        return self.combo.model()

    @property
    def valueListStr(self):
        return [self.model.item(i).text() for i in range(self.count())]

    @QtCore.pyqtProperty('QStringList')
    def valueList(self):
        return self._valueList
#        return [self.combo.itemText(i) for i in range(self.combo.count())]

    @valueList.setter
    def valueList(self, valueList):
        self._valueList = valueList
        self.combo.clear()
        self.combo.addItems(valueList)

    @QtCore.pyqtProperty(int)
    def currentIndex(self):
        return self.combo.currentIndex()

    @currentIndex.setter
    def currentIndex(self, index):
        self.combo.setCurrentIndex(index)

    def enterEvent(self, event):
        pass

    def leaveEvent(self, event):
        pass

    def setDisabledItems(self, items):
        if not isinstance(items, (range, list, tuple)):
            items = (items, )
        for itemId in items:
            if not 0 <= itemId < self.model.rowCount():
                continue
            item = self.model.item(itemId)
            item.setFlags((item.flags() | QtCore.Qt.ItemIsEnabled) ^ QtCore.Qt.ItemIsEnabled)


if __name__ == '__main__':
    import sys
    from string import ascii_letters
    from random import randrange
    app = QtWidgets.QApplication(sys.argv)
    valueList = [''.join((ascii_letters + ' ')[randrange(53)] for l in range(randrange(1, 11))) for i in range(30)]
    win = QtWidgets.QWidget()
    layout = QtWidgets.QHBoxLayout()
    win.setLayout(layout)
    combo1 = Combo(label='Combo test', labelPos=QtCore.Qt.LeftEdge, valueList=valueList)
    combo1.setDisabledItems(range(8))
    combo1.show()
    layout.addWidget(combo1)
    combo2 = Combo(label='Combo test', labelPos=QtCore.Qt.LeftEdge, valueList=valueList)
    palette = combo2.palette()
    window = palette.color(palette.Window)
    windowText = palette.color(palette.WindowText)
    palette.setColor(palette.WindowText, window)
    palette.setColor(palette.Window, windowText)
    combo2.setPalette(palette)
    layout.addWidget(combo2)
    win.show()
    sys.exit(app.exec_())
