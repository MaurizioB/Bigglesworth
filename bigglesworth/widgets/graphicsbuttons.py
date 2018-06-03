from Qt import QtCore, QtGui, QtWidgets

class GraphicsButton(QtWidgets.QPushButton):
    def __init__(self, parent=None):
        QtWidgets.QPushButton.__init__(self, parent)
        self.setStyleSheet('''
            GraphicsButton {
                color: rgb(30, 50, 40);
                border-radius: 1px;
                border-left: 1px solid palette(midlight);
                border-right: 1px solid palette(mid);
                border-top: 1px solid palette(midlight);
                border-bottom: 1px solid palette(mid);
                background: rgba(220, 220, 220, 120);
            }
            GraphicsButton:disabled {
                color: darkGray;
            }
            GraphicsButton:hover {
                border-left: 1px solid palette(light);
                border-right: 1px solid palette(dark);
                border-top: 1px solid palette(light);
                border-bottom: 1px solid palette(dark);
            }
            GraphicsButton:pressed, GraphicsButton:checked {
                padding-top: 1px;
                padding-left: 1px;
                border-left: 1px solid palette(shadow);
                border-right: 1px solid palette(mid);
                border-top: 1px solid palette(shadow);
                border-bottom: 1px solid palette(mid);
            }
            GraphicsButton:checked {
                background: rgba(120, 120, 100, 196);
            }
            ''')


class CloseBtn(GraphicsButton):
    def __init__(self, parent=None):
        GraphicsButton.__init__(self, parent)
        self.setStyleSheet(self.styleSheet() + '''
            CloseBtn {
                color: rgba(180, 180, 160, 255);
                background: rgba(200, 200, 200, 120);
                min-height: 16px;
                min-height: 16px;
            }
            CloseBtn:hover {
                background: rgba(220, 220, 220, 190);
            }
            ''')

    def sizeHint(self):
        return QtCore.QSize(20, 20)

    def paintEvent(self, event):
#        GraphicsButton.paintEvent(self, event)
        qp = QtGui.QPainter(self)
        qp.setRenderHints(qp.Antialiasing)
        qp.translate(.5, .5)
        qp.setPen(QtGui.QPen(qp.pen().color() if not self.underMouse() else QtCore.Qt.darkGray, 2, cap=QtCore.Qt.RoundCap))
        rect = self.rect()
        qp.drawLine(3, 3, rect.width() - 4, rect.bottom() - 3)
        qp.drawLine(rect.width() - 4, 3, 3, rect.bottom() - 3)


