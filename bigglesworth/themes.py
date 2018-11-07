from uuid import uuid4

from Qt import QtCore, QtGui

from dial import _Dial

DARK, LIGHT = range(2)
FONTDATA, DIALDATA, SLIDERDATA, COMBODATA = 32, 33, 34, 35
DIALSTART, DIALZERO, DIALEND, DIALGRADIENT, DIALBGD, DIALSCALE, DIALNOTCHES, DIALINDICATOR = range(8)
DIALCOLORFULL, DIALCOLORGRADIENT = 0, 1
TRANSPARENT, OPAQUE = 0, 1
UNDOFONTFAMILY, UNDOFONTSIZE, UNDOFONTBOLD, UNDOFONTITALIC, UNDODIALGRADIENT, UNDOCOMBOSTYLE, UNDODIALSTART, UNDOLINKSLIDER = range(8)

palette = QtGui.QPalette

DarkTheme = {
    palette.Window: (20, 20, 20), 
    palette.WindowText: {
        palette.Active: (230, 230, 230), 
        palette.Inactive: (230, 230, 230), 
        palette.Disabled: QtCore.Qt.lightGray, 
        }, 
    FONTDATA: ('Droid Sans', 9, True, False), 
    DIALDATA: {
        'dialGradient': DIALCOLORGRADIENT, 
        }, 
    SLIDERDATA: {
        'sliderBgd': QtCore.Qt.black, 
        }, 
    }

LightTheme = {
    palette.Window: (230, 230, 230), 
    palette.WindowText: {
        palette.Active: QtCore.Qt.black, 
        palette.Disabled: QtCore.Qt.darkGray, 
        }, 
    FONTDATA: ('Droid Sans', 9, True, False), 
    }

BaseThemes = {
    'Dark': DarkTheme, 
    'Light': LightTheme, 
    }


def getColor(color):
    if isinstance(color, QtGui.QColor):
        return color
    try:
        color = QtGui.QColor(color)
    except:
        color = QtGui.QColor(*color)
    return color


class Theme(QtCore.QObject):
    changed = QtCore.pyqtSignal(object)

    def __init__(
            self, name, 
            palette=None, font=None, 
            rangeStart=_Dial._defaultRangeEnd, rangeZero=_Dial._defaultRangeStart, rangeEnd=_Dial._defaultRangeEnd, 
            dialStart=None, dialZero=None, dialEnd=None, dialGradient=DIALCOLORFULL, dialBgd=None, 
            dialScale=_Dial._defaultRangePen, dialNotches=_Dial._defaultScalePen, dialIndicator=_Dial._defaultIndicatorPen, 
            sliderStart=None, sliderEnd=None, sliderBgd=None, 
            frameBorderColor=None, frameLabelColor=None, 
            comboStyle=TRANSPARENT, uuid=None
            ):
        QtCore.QObject.__init__(self)
        self.uuid = uuid if uuid else str(uuid4())
        if isinstance(name, Theme):
            self.name = name.name
            self.clone(name)
            return
        self.name = name
        if isinstance(palette, Theme):
            self.clone(palette)
            return
        self.palette = QtGui.QPalette(palette)
        try:
            self._font = QtGui.QFont(font)
        except:
            self._font = QtGui.QFont(*font)
        if dialStart is None:
            dialStart = rangeStart
        if dialZero is None:
            dialZero = rangeZero
        if dialEnd is None:
            dialEnd = rangeEnd
        if dialBgd is None:
            dialBgd = palette.color(palette.Mid)
        self.dialStart = dialStart
        self.dialZero = dialZero
        self.dialEnd = dialEnd
        self.dialGradient = dialGradient
        self.dialBgd = dialBgd
        self.dialScale = dialScale
        self.dialNotches = dialNotches
        self.dialIndicator = dialIndicator
        if sliderStart is None:
            sliderStart = rangeZero
        if sliderEnd is None:
            sliderEnd = rangeEnd
        if sliderBgd is None:
            sliderBgd = palette.color(palette.Window).darker()
        self.sliderStart = sliderStart
        self.sliderEnd = sliderEnd
        self.sliderBgd = sliderBgd
        self._comboStyle = comboStyle
        if frameBorderColor is None:
            frameBorderColor = palette.color(palette.Midlight)
        self._frameBorderColor = frameBorderColor
        if frameLabelColor is None:
            frameLabelColor = palette.color(palette.Shadow)
            if abs(frameBorderColor.lightness() - frameLabelColor.lightness()) < 32:
                if frameLabelColor.lightness() < 128:
                    frameLabelColor = frameLabelColor.lighter()
                else:
                    frameLabelColor = frameLabelColor.darker()
        self._frameLabelColor = frameLabelColor

    @property
    def dialData(self):
        return self.dialStart, self.dialZero, self.dialEnd, self.dialGradient, self.dialBgd, self.dialScale, self.dialNotches, self.dialIndicator

    @dialData.setter
    def dialData(self, data):
        self.dialStart, self.dialZero, self.dialEnd, self.dialGradient, self.dialBgd, self.dialScale, self.dialNotches, self.dialIndicator = data
        self.changed.emit(self)

    @property
    def sliderData(self):
        return self.sliderStart, self.sliderEnd, self.sliderBgd

    @sliderData.setter
    def sliderData(self, data):
        sliderColors = []
        for color in data:
            if not isinstance(color, QtGui.QColor):
                try:
                    color = QtGui.QColor(color)
                except:
                    color = QtGui.QColor(*color)
            sliderColors.append(color)
        self.sliderStart, self.sliderEnd, self.sliderBgd = sliderColors
        self.changed.emit(self)

    def setDialData(self, data):
        if isinstance(data, (tuple, list)):
            data = iter(data)
            for field in ('dialStart', 'dialZero', 'dialEnd', 'dialGradient', 'dialBgd', 'dialScale', 'dialNotches', 'dialIndicator'):
                try:
                    setattr(self, field, data.next())
                except:
                    break
        else:
            for k, v in data.items():
                setattr(self, k, v)
        self.changed.emit(self)

    def setSliderData(self, data):
        if isinstance(data, (tuple, list)):
            data = iter(data)
            for field in ('sliderStart', 'sliderEnd', 'sliderBgd'):
                try:
                    setattr(self.field.data.next())
                except:
                    break
        else:
            for k, v in data.items():
                setattr(self, k, getColor(v))
        self.changed.emit(self)

    @property
    def comboStyle(self):
        return self._comboStyle

    @comboStyle.setter
    def comboStyle(self, comboStyle):
        self._comboStyle = comboStyle
        self.changed.emit(self)

    @property
    def frameBorderColor(self):
        return self._frameBorderColor

    @frameBorderColor.setter
    def frameBorderColor(self, color):
        self._frameBorderColor = color
        self.changed.emit(self)

    @property
    def frameLabelColor(self):
        return self._frameLabelColor

    @frameLabelColor.setter
    def frameLabelColor(self, color):
        self._frameLabelColor = color
        self.changed.emit(self)

    @property
    def font(self):
        return self._font

    @font.setter
    def font(self, font):
        self._font = font
        self.changed.emit(self)

    def color(self, *args):
        if len(args) == 1 and isinstance(args[0], (str, unicode)):
            return getattr(self, args[0])
        return self.palette.color(*args)

    def setColor(self, *args):
        self.palette.setColor(*args)
        self.changed.emit(self)

    def setFont(self, font):
        self.font = font
        self.changed.emit(self)

    def data(self):
        return (self.palette, self._font, self.dialData, self.sliderData, self._frameBorderColor, self._frameLabelColor, self.comboStyle)

    def setData(self, data):
        self.blockSignals(True)
        self.palette, self._font, self.dialData, self.sliderData, self._frameBorderColor, self._frameLabelColor, self._comboStyle = data
        self.blockSignals(False)

    def map(self):
        themeDict = {}
        for attr in ('font', 'palette', 
            'dialStart', 'dialZero', 'dialEnd', 'dialBgd', 'dialScale', 
            'dialNotches', 'dialIndicator', 'dialGradient', 
            'sliderStart', 'sliderEnd', 'sliderBgd', 
            'frameBorderColor', 'frameLabelColor', 'comboStyle', 'uuid'):
                themeDict[attr] = getattr(self, attr)
        return themeDict

    def clone(self, theme):
        #TODO: write to _properties?
        self.palette = QtGui.QPalette(theme.palette)
        self.font = QtGui.QFont(theme.font)
        self.dialData = theme.dialData
        self.sliderData = theme.sliderData
        self.comboStyle = theme.comboStyle
        self._frameBorderColor = theme._frameBorderColor
        self._frameLabelColor = theme._frameLabelColor

    def __eq__(self, other):
        if not isinstance(other, Theme):
            return False
        if self.palette != other.palette or self.font != other.font or \
            self.dialData != other.dialData or self.sliderData != other.sliderData or \
            self._comboStyle != other._comboStyle:
                return False
        return True


class ThemeCollection(QtCore.QObject):
    def __init__(self, main):
        QtCore.QObject.__init__(self)
        self.main = main
        self.themeDict = {}
        self.themeList = ['Dark', 'Light', 'System']
        self.customThemes = []
        self.themeDir = QtCore.QDir(QtGui.QDesktopServices.storageLocation(QtGui.QDesktopServices.DataLocation) + '/themes/')
        if self.themeDir.exists():
            for fileName in self.themeDir.entryList('*', self.themeDir.Files|self.themeDir.NoDotAndDotDot):
                self.themeList.append(fileName)
                self.customThemes.append(fileName)

    @property
    def current(self):
        try:
            return self._currentTheme
        except:
            settingsValue = self.main.settings.value('theme', 'Dark')
            if not settingsValue in self.themeList:
                settingsValue = 'Dark'
                self.main.settings.remove('theme')
            self._currentTheme = self[settingsValue]
            return self._currentTheme

    def setCurrentTheme(self, themeName):
        self._currentTheme = self[themeName]
#        self.main.settings.setValue('theme', themeName)

    def createTheme(self, themeName, theme=None):
        if theme:
            theme = Theme(themeName, theme)
        else:
            theme = Theme(themeName, self.main.palette())
        self.themeDict[themeName] = theme
        self.themeList.append(themeName)
        if not self.themeDir.exists():
            self.themeDir.mkpath('.')
        themeFile = QtCore.QFile(self.themeDir.filePath(themeName))
        if themeFile.open(QtCore.QIODevice.WriteOnly):
            ds = QtCore.QDataStream(themeFile)
#            ds.writeQVariant(theme.palette)
            ds.writeQVariantMap(theme.map())
            themeFile.close()

    def saveTheme(self, theme):
        if not self.themeDir.exists():
            self.themeDir.mkpath('.')
        themeFile = QtCore.QFile(self.themeDir.filePath(theme.name))
        if themeFile.open(QtCore.QIODevice.WriteOnly):
            ds = QtCore.QDataStream(themeFile)
#            ds.writeQVariant(theme.palette)
            ds.writeQVariantMap(theme.map())
            themeFile.close()

    def renameTheme(self, oldName, newName):
        theme = self.themeDict.pop(oldName)
        theme.name = newName
        self.themeDict[newName] = theme
        self.themeList.pop(self.themeList.index(oldName))
        self.themeList.append(newName)
        self.themeDir.rename(oldName, newName)

    def deleteTheme(self, themeName):
        if themeName in ('Dark', 'Light', 'System'):
            return
        self.themeDir.remove(themeName)
        self.themeDict.pop(themeName)
        self.themeList.pop(self.themeList.index(themeName))

    def buildTheme(self, themeName):
        if themeName in self.customThemes:
            themeFile = QtCore.QFile(self.themeDir.filePath(themeName))
            if not themeFile.open(QtCore.QIODevice.ReadOnly):
                raise
            ds = QtCore.QDataStream(themeFile)
#            palette = ds.readQVariant()
            themeData = ds.readQVariantMap()
            themeFile.close()
            theme = Theme(themeName, **themeData)
            self.themeDict[themeName] = theme
            return theme

        palette = self.main.palette()
        palette.setColor(palette.Active, palette.Button, QtGui.QColor(124, 240, 110))
        font = self.main.font()
        theme = Theme(themeName, palette, font)
        self.themeDict[themeName] = theme

        if themeName in BaseThemes:
            themeData = BaseThemes[themeName]
            palette = theme.palette
        else:
            themeData = None
        if themeData:
            for k, v in themeData.items():
                if isinstance(k, QtGui.QPalette.ColorRole):
                    if isinstance(v, dict):
                        for group, color in v.items():
                            try:
                                palette.setColor(group, k, color)
                            except:
                                palette.setColor(group, k, QtGui.QColor(*color))
                    else:
                        try:
                            palette.setColor(k, v)
                        except:
                            palette.setColor(k, QtGui.QColor(*v))
                elif k == FONTDATA:
                    family, size, bold, italic = v
                    font = QtGui.QFont(family, size)
                    font.setBold(bold)
                    font.setItalic(italic)
                    theme.font = font
                elif k == DIALDATA:
                    theme.setDialData(v)
                elif k == SLIDERDATA:
                    theme.setSliderData(v)
                elif k == COMBODATA:
                    theme._comboStyle = v
        return theme

    def __getitem__(self, themeName):
        if themeName not in self.themeDict:
            self.buildTheme(themeName)
        return self.themeDict[themeName]

