#!/usr/bin/env python

from Qt import QtCore, QtGui, QtWidgets
from metawidget import _getCssQColorStr

class ListView(QtWidgets.QListView):
    def __init__(self, *args, **kwargs):
        QtWidgets.QListView.__init__(self, *args, **kwargs)
#        verticalScrollBar = CustomScrollBar(QtCore.Qt.Vertical)
#        self.setVerticalScrollBar(verticalScrollBar)

    def changeEvent(self, event):
        if event.type() == QtCore.QEvent.PaletteChange:
            self.setPalette(self.palette())

    def setPalette(self, palette):
        scrollSheet = '''
            QScrollBar {{
                border-top: 1px solid {dark};
                border-right: 1px solid {light};
                border-bottom: 1px solid {light};
                border-left: 1px solid {dark};
                width: 12px;
                background: {dark};
            }}
            QScrollBar:vertical {{
                margin: 14px 0 14px 0;
            }}
            QScrollBar:horizontal {{
                margin: 0 14px 0 14px;
            }}
            QScrollBar::handle {{
                border-top: 1px solid {light};
                border-right: 1px solid {dark};
                border-bottom: 1px solid {dark};
                border-left: 1px solid {light};
                border-radius: 2px;
                min-height: 12px;
                background: {mid};
            }}
            QScrollBar::handle:hover {{
                background: {light};
            }}
            QScrollBar::add-line, QScrollBar::sub-line {{
                border-top: 1px solid {light};
                border-right: 1px solid {dark};
                border-bottom: 1px solid {dark};
                border-left: 1px solid {light};
                border-radius: 2px;
                background: {light};
            }}
            QScrollBar::add-line:pressed, QScrollBar::sub-line:pressed {{
                border-top: 1px solid {dark};
                border-right: 1px solid {light};
                border-bottom: 1px solid {light};
                border-left: 1px solid {dark};
            }}
            QScrollBar::add-line:vertical {{
                subcontrol-origin: margin;
                subcontrol-position: bottom;
                height: 12px;
            }}
            QScrollBar::sub-line:vertical {{
                subcontrol-origin: margin;
                subcontrol-position: top;
                height: 12px;
            }}
            QScrollBar::down-arrow {{
                width: 0px;
                height: 0px;
                border-top: 4px solid {itemFgdColorEnabled};
                border-left: 4px solid {itemBgdColorEnabled};
                border-right: 4px solid {itemBgdColorEnabled};
                border-bottom: none;
            }}
            QScrollBar::down-arrow:disabled, QScrollBar::down-arrow:off {{
                background: red;
            }}
            QScrollBar::up-arrow {{
                width: 0px;
                height: 0px;
                border-top: none;
                border-left: 4px solid {itemBgdColorEnabled};
                border-right: 4px solid {itemBgdColorEnabled};
                border-bottom: 4px solid {itemFgdColorEnabled};
            }}
            '''.format(
            light=_getCssQColorStr(palette.color(palette.Midlight)), 
            mid=_getCssQColorStr(palette.color(palette.Midlight).darker(105)), 
            dark=_getCssQColorStr(palette.color(palette.Dark)), 
            itemFgdColorEnabled=_getCssQColorStr(palette.color(palette.Active, palette.Text)), 
            itemBgdColorEnabled=_getCssQColorStr(palette.color(palette.Active, palette.Base)), 
            )
        self.verticalScrollBar().setStyleSheet(scrollSheet)
        self.horizontalScrollBar().setStyleSheet(scrollSheet)
#        self.verticalScrollBar().setPalette(palette)
#        QtWidgets.QListView.setPalette(self, palette)
#        self.setStyleSheet('QScrollBar:vertical {width: 30px;}')
