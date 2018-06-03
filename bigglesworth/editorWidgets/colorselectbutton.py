#!/usr/bin/env python

from Qt import QtCore, QtGui, QtWidgets
import metawidget

_baseColors = {
    (255, 255, 255, 255): 'White',
    (0, 0, 0, 255): 'Black',
    (0, 0, 0, 0): 'Transparent',
    (0, 0, 128, 255): 'Dark blue',
    (0, 0, 255, 255): 'Blue',
    (0, 128, 0, 255): 'Dark green',
    (0, 128, 128, 255): 'Dark cyan',
    (0, 255, 0, 255): 'Green',
    (0, 255, 255, 255): 'Cyan',
    (128, 0, 0, 255): 'Dark red',
    (128, 0, 128, 255): 'Dark magenta',
    (128, 128, 0, 255): 'Dark yellow',
    (128, 128, 128, 255): 'Dark gray',
    (160, 160, 164, 255): 'Gray',
    (192, 192, 192, 255): 'Light gray',
    (255, 0, 0, 255): 'Red',
    (255, 0, 255, 255): 'Magenta',
    (255, 255, 0, 255): 'Yellow',
    }

#svg color names, qt names/values take precedence on duplicate
_svgColors = {
    (0, 0, 205, 255): 'Medium blue',
    (0, 191, 255, 255): 'Deepskyblue',
    (0, 206, 209, 255): 'Dark turquoise',
    (0, 250, 154, 255): 'Medium springgreen',
    (0, 255, 127, 255): 'Springgreen',
    (0, 255, 255, 255): 'Cyan',
    (25, 25, 112, 255): 'Midnightblue',
    (30, 144, 255, 255): 'Dodgerblue',
    (32, 178, 170, 255): 'Light seagreen',
    (34, 139, 34, 255): 'Forestgreen',
    (46, 139, 87, 255): 'Seagreen',
    (47, 79, 79, 255): 'Dark slategrey',
    (50, 205, 50, 255): 'Limegreen',
    (60, 179, 113, 255): 'Medium seagreen',
    (64, 224, 208, 255): 'Turquoise',
    (65, 105, 225, 255): 'Royalblue',
    (70, 130, 180, 255): 'Steelblue',
    (72, 61, 139, 255): 'Dark slateblue',
    (72, 209, 204, 255): 'Medium turquoise',
    (75, 0, 130, 255): 'Indigo',
    (85, 107, 47, 255): 'Dark olivegreen',
    (95, 158, 160, 255): 'Cadetblue',
    (100, 149, 237, 255): 'Cornflowerblue',
    (102, 205, 170, 255): 'Medium aquamarine',
    (105, 105, 105, 255): 'Dimgrey',
    (106, 90, 205, 255): 'Slateblue',
    (107, 142, 35, 255): 'Olivedrab',
    (112, 128, 144, 255): 'Slategrey',
    (119, 136, 153, 255): 'Light slategrey',
    (123, 104, 238, 255): 'Medium slateblue',
    (124, 252, 0, 255): 'Lawngreen',
    (127, 255, 0, 255): 'Chartreuse',
    (127, 255, 212, 255): 'Aquamarine',
    (135, 206, 235, 255): 'Skyblue',
    (135, 206, 250, 255): 'Light skyblue',
    (138, 43, 226, 255): 'Blueviolet',
    (139, 69, 19, 255): 'Saddlebrown',
    (143, 188, 143, 255): 'Dark seagreen',
    (144, 238, 144, 255): 'Light green',
    (147, 112, 219, 255): 'Medium purple',
    (148, 0, 211, 255): 'Dark violet',
    (152, 251, 152, 255): 'Pale green',
    (153, 50, 204, 255): 'Dark orchid',
    (154, 205, 50, 255): 'Yellowgreen',
    (160, 82, 45, 255): 'Sienna',
    (165, 42, 42, 255): 'Brown',
    (169, 169, 169, 255): 'Dark grey',
    (173, 216, 230, 255): 'Light blue',
    (173, 255, 47, 255): 'Greenyellow',
    (175, 238, 238, 255): 'Pale turquoise',
    (176, 196, 222, 255): 'Light steelblue',
    (176, 224, 230, 255): 'Powderblue',
    (178, 34, 34, 255): 'Firebrick',
    (184, 134, 11, 255): 'Dark goldenrod',
    (186, 85, 211, 255): 'Medium orchid',
    (188, 143, 143, 255): 'Rosybrown',
    (189, 183, 107, 255): 'Dark khaki',
    (199, 21, 133, 255): 'Medium violetred',
    (205, 92, 92, 255): 'Indianred',
    (205, 133, 63, 255): 'Peru',
    (210, 105, 30, 255): 'Chocolate',
    (210, 180, 140, 255): 'Tan',
    (211, 211, 211, 255): 'Light grey',
    (216, 191, 216, 255): 'Thistle',
    (218, 112, 214, 255): 'Orchid',
    (218, 165, 32, 255): 'Goldenrod',
    (219, 112, 147, 255): 'Pale violetred',
    (220, 20, 60, 255): 'Crimson',
    (220, 220, 220, 255): 'Gainsboro',
    (221, 160, 221, 255): 'Plum',
    (222, 184, 135, 255): 'Burlywood',
    (224, 255, 255, 255): 'Light cyan',
    (230, 230, 250, 255): 'Lavender',
    (233, 150, 122, 255): 'Dark salmon',
    (238, 130, 238, 255): 'Violet',
    (238, 232, 170, 255): 'Pale goldenrod',
    (240, 128, 128, 255): 'Light coral',
    (240, 230, 140, 255): 'Khaki',
    (240, 248, 255, 255): 'Aliceblue',
    (240, 255, 240, 255): 'Honeydew',
    (240, 255, 255, 255): 'Azure',
    (244, 164, 96, 255): 'Sandybrown',
    (245, 222, 179, 255): 'Wheat',
    (245, 245, 220, 255): 'Beige',
    (245, 245, 245, 255): 'Whitesmoke',
    (245, 255, 250, 255): 'Mintcream',
    (248, 248, 255, 255): 'Ghostwhite',
    (250, 128, 114, 255): 'Salmon',
    (250, 235, 215, 255): 'Antiquewhite',
    (250, 240, 230, 255): 'Linen',
    (250, 250, 210, 255): 'Light goldenrodyellow',
    (253, 245, 230, 255): 'Oldlace',
    (255, 20, 147, 255): 'Deeppink',
    (255, 69, 0, 255): 'Orangered',
    (255, 99, 71, 255): 'Tomato',
    (255, 105, 180, 255): 'Hotpink',
    (255, 127, 80, 255): 'Coral',
    (255, 140, 0, 255): 'Dark orange',
    (255, 160, 122, 255): 'Light salmon',
    (255, 165, 0, 255): 'Orange',
    (255, 182, 193, 255): 'Light pink',
    (255, 192, 203, 255): 'Pink',
    (255, 215, 0, 255): 'Gold',
    (255, 218, 185, 255): 'Peachpuff',
    (255, 222, 173, 255): 'Navajowhite',
    (255, 228, 181, 255): 'Moccasin',
    (255, 228, 196, 255): 'Bisque',
    (255, 228, 225, 255): 'Mistyrose',
    (255, 235, 205, 255): 'Blanchedalmond',
    (255, 239, 213, 255): 'Papayawhip',
    (255, 240, 245, 255): 'Lavenderblush',
    (255, 245, 238, 255): 'Seashell',
    (255, 248, 220, 255): 'Cornsilk',
    (255, 250, 205, 255): 'Lemonchiffon',
    (255, 250, 240, 255): 'Floralwhite',
    (255, 250, 250, 255): 'Snow',
    (255, 255, 224, 255): 'Light yellow',
    (255, 255, 240, 255): 'Ivory',
    }

_colors = _baseColors.copy()
_colors.update(_svgColors)

_RED, _GREEN, _BLUE, _ALPHA = range(4)
_components = {
    _RED: QtCore.Qt.red, 
    _GREEN: QtCore.Qt.darkGreen, 
    _BLUE: QtCore.Qt.blue, 
    _ALPHA: QtCore.Qt.black, 
    }

def _getBitColor(r, g, b, a):
    return (r << 16) + (g << 8) + b

def setBold(item, bold=True):
    font = item.font()
    font.setBold(bold)
    item.setFont(font)

_baseColorsByRgb = sorted(_baseColors.items(), key=lambda kv: _getBitColor(*kv[0]))
_svgColorsByRgb = sorted(_svgColors.items(), key=lambda kv: _getBitColor(*kv[0]))

class ColorMenu(QtWidgets.QMenu):
    def __init__(self, parent=None):
        QtWidgets.QMenu.__init__(self, parent)
        pickerAction = self.addAction(QtGui.QIcon.fromTheme('edit-find'), 'Pick color...')
        pickerAction.setData(QtGui.QColor)
        self.svgMenu = self.addMenu('SVG colors')
        for color, name in _svgColorsByRgb:
            self.svgMenu.addAction(self.createItem(color, name))
        self.addSeparator().setText('Base colors')
        for color, name in _baseColorsByRgb:
            self.addAction(self.createItem(color, name))

    def createItem(self, color, name):
        color = QtGui.QColor(*color)
        pixmap = QtGui.QPixmap(32, 32)
        pixmap.fill(color)
        qp = QtGui.QPainter(pixmap)
        qp.drawRect(pixmap.rect().adjusted(0, 0, -1, -1))
        qp.end()
        icon = QtGui.QIcon(pixmap)
        item = QtWidgets.QAction(icon, name, self)
        item.setData(color)
        return item

    def exec_(self, pos, color=None):
        found = False
        for action in self.actions():
            if action.data() == color:
                setBold(action)
                found = True
            else:
                setBold(action, False)
        if found:
            setBold(self.svgMenu, False)
            for action in self.svgMenu.actions():
                setBold(action, False)
        else:
            for action in self.svgMenu.actions():
                if action.data() == color:
                    setBold(action)
                    found = True
                else:
                    setBold(action, False)
            if found:
                setBold(self.svgMenu.menuAction())
        return QtWidgets.QMenu.exec_(self, pos)


class ColorSelectButton(QtWidgets.QPushButton):
    colorChanged = QtCore.pyqtSignal(QtGui.QColor, QtGui.QColor)
    def __init__(self, parent=None):
        QtWidgets.QPushButton.__init__(self, parent)
        #fake icon necessary to draw the control correct width
        pixmap = QtGui.QPixmap(32, 32)
        icon = QtGui.QIcon(pixmap)
        self.setIcon(icon)
        self.clicked.connect(self.updateColor)
        self.colorRole = ''
        #fake text necessary as above
        self.setText('255 255 255 255')
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showPopup)
        self.colorMenu = ColorMenu()
        self.updateColor(QtGui.QColor(QtCore.Qt.white))

    def showPopup(self, pos):
        res = self.colorMenu.exec_(self.mapToGlobal(pos), self._color)
        if res:
            self.updateColor(res.data())

    def updateColor(self, color=None):
        if color is None:
            return
        if isinstance(color, bool) or not color.isValid():
            dialog = QtWidgets.QColorDialog(self._color, self)
            if self.colorRole:
                dialog.setWindowTitle('Set color for "{}"'.format(self.colorRole))
            dialog.setOption(dialog.ShowAlphaChannel)
            if not dialog.exec_():
                return
            else:
                color = dialog.selectedColor()
        try:
            oldColor = self._color
        except:
            oldColor = QtGui.QColor(QtCore.Qt.white)
        self._color = QtGui.QColor(color)
        r, g, b, a = self._color.getRgb()
        try:
            self.colorName = _colors[r, g, b, a]
            self.labelPaintFunc = self.labelPaintGlobal
        except:
            self.colorName = ''
            self.labelPaintFunc = self.labelPaintRgb
        self.components = {c:v for c, v in zip(range(4), (r, g, b, a))}
        self.setToolTip('''
            <font color="red">&#9632;</font> {red}
            <font color="green">&#9632;</font> {green}
            <font color="blue">&#9632;</font> {blue}
            <font color="{tooltip}">&#9633;</font> {alpha}
            <br/><br/>Right click for fast selection
            '''.format(
                red = r, 
                green = g, 
                blue = b, 
                alpha = a, 
                tooltip = self.palette().color(QtGui.QPalette.ToolTipText).name(), 
                ))
        self.update()
        self.colorChanged.emit(self._color, oldColor)

    @QtCore.pyqtProperty(QtGui.QColor)
    def color(self):
        return self._color

    @color.setter
    def color(self, newColor):
        oldColor = self._color
        self._color = newColor
        self.updateColor(newColor)
        if newColor != oldColor:
            self.colorChanged.emit(newColor, oldColor)

    def paintEvent(self, event):
        qp = QtWidgets.QStylePainter(self)
        qp.setRenderHints(qp.Antialiasing)
        option = QtWidgets.QStyleOptionButton()
        self.initStyleOption(option)
        qp.drawControl(QtWidgets.QStyle.CE_PushButtonBevel, option)
        qp.translate(.5, .5)
        rect = self.style().subElementRect(self.style().SE_PushButtonContents, option, self)
        iconSize = rect.height() * .7
        halfSize = iconSize / 2
        qp.save()
        qp.translate(halfSize, rect.center().y())
        qp.setBrush(self._color)
        qp.drawRect(0, -halfSize, iconSize, iconSize)
        qp.restore()
        self.labelPaintFunc(qp, option, iconSize + halfSize + 4)

    def labelPaintGlobal(self, qp, option, delta):
        qp.drawText(option.rect.adjusted(delta, 0, 0, 0), QtCore.Qt.AlignCenter, self.colorName)

    def labelPaintRgb(self, qp, option, delta):
        componentSize = option.fontMetrics.size(QtCore.Qt.TextSingleLine, '255 ')
        componentRect = QtCore.QRectF(0, 0, componentSize.width(), self.height())
        qp.translate(delta, 0)
        for c, v in self.components.items():
            qp.setPen(_components[c])
            qp.drawText(componentRect, QtCore.Qt.AlignCenter, str(v))
            qp.translate(componentSize.width(), 0)


if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)
    widget = ColorSelectButton()
    widget.show()
    sys.exit(app.exec_())
