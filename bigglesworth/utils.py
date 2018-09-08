#!/usr/bin/env python2.7
# *-* encoding: utf-8 *-*

from os import path
import json

from PyQt4 import QtCore, QtGui, uic
from bigglesworth.const import backgroundRole, ord2chr
from bigglesworth.libs import midifile

def getQtFlags(flags, enum, module=QtCore.Qt, values=False):
    results = {}
    for k, v in module.__dict__.items():
        if isinstance(v, enum) and flags & v:
            results[int(v)] = k
    if not values:
        return ', '.join(results[v] for v in sorted(results.keys()))
    return ', '.join('{} ({})'.format(results[v], v) for v in sorted(results.keys()))

def readMidContents(filePath, check=False):
    try:
        track = midifile.read_midifile(filePath)[0]
        sysex = []
        for event in track:
            if isinstance(event, midifile.SysexEvent):
                sysex.append(event.data[2:-1])
        if not check:
            return sysex
    except:
        return False
    return sysex

def readSyxContents(filePath, check=False):
    try:
        with open(filePath, 'rb') as raw:
            data = map(ord, raw.read())
        if not data or (data[0] != 0xf0 or data[-1] != 0xf7):
            print('qtf', data[0], data[-1])
            return False
    except:
        return False
    if not check:
        sysex = []
        buffer = []
        for value in data:
            if value == 0xf7:
                sysex.append(buffer[1:-1])
                buffer = []
                continue
            buffer.append(value)
        return sysex

def getSysExContents(filePath):
    filePath = QtCore.QUrl(filePath).toLocalFile()
    sysex = readMidContents(filePath)
    if sysex:
        return sysex
    sysex = readSyxContents(filePath)
    if sysex:
        return sysex
    return None

def getSizeStr(size):
    for m in ('B', 'kB', 'MB'):
        if size < 1024:
            size = '{:.1f}'.format(round(size, 1)).replace('.0', '')
            return '{} {}'.format(size, m)
        size /= 1024.
    return '???'

def elapsedFrom(date):
    delta = date.secsTo(QtCore.QDateTime.currentDateTime())
    for t, d in (('s', 60), ('m', 60), ('h', 24), ('d', 31), ('m', 12)):
        if delta < d:
            return '{}{}'.format(delta, t)
        delta /= d
    return '???'

def getChar(o):
    if 32 <= o <= 126:
        return unichr(o)
    if o == 127:
        return u'°'
    return '?'

def getName(values):
    return u''.join(ord2chr[c] for c in values)

def getCharacter(o):
    if 32 <= o <= 126:
        return unichr(o)
    if o == 127:
        return u'°'
    return '?'

def getQColor(variant):
    try:
        return QtGui.QColor(*json.loads(variant))
    except:
        return None

def getValidQColor(variant, role):
    color = getQColor(variant)
    if color:
        return color
    return QtGui.QColor(QtCore.Qt.darkGray if role == backgroundRole else QtCore.Qt.white)

def setBold(item, bold=True):
    font = item.font()
    font.setBold(bold)
    item.setFont(font)

def setItalic(item, italic=True):
    font = item.font()
    font.setItalic(italic)
    item.setFont(font)

def setBoldItalic(item, bold=True, italic=True):
    font = item.font()
    font.setBold(bold)
    font.setItalic(italic)
    item.setFont(font)

def sanitize(minimum, value, maximum):
    return max(minimum, min(maximum, value))

def localPath(name):
    #fix for cx_freeze
    current = path.dirname(path.abspath(__file__))
    if current.endswith('\\library.zip\\bigglesworth'):
        current = current.replace('\\library.zip', '')
    elif current.endswith('/library.zip/bigglesworth'):
        current = current.replace('/library.zip', '')
    return path.join(current, name)


def loadUi(uiPath, widget):
    #fix for cx_freeze
    current = path.dirname(path.abspath(__file__))
    if current.endswith('\\library.zip\\bigglesworth') or current.endswith('\\library.zip\\bigglesworth\\dialogs'):
        current = current.replace('\\library.zip', '')
    elif current.endswith('/library.zip/bigglesworth') or current.endswith('/library.zip/bigglesworth/dialogs'):
        current = current.replace('/library.zip', '')
    return uic.loadUi(path.join(current, uiPath), widget)


#This Enum emulation is for debugging purposes only
class EnumClass(int):
    def __new__(cls, value, name):
        return int.__new__(cls, value)

    def __init__(self, value, name):
        int.__init__(self, value)
        self.__enumname__ = name

    def __repr__(self):
        return self.__enumname__

    def __str__(self):
        return self.__enumname__

def _makeEnum(value=5):
    def getter(self):
        cls = self.__class__
        found = False
        while not found:
            for k, v in cls.__dict__.items():
                if v == propertyWrapper:
                    enum = EnumClass(value, k)
                    setattr(self.__class__, k, enum)
                    found = True
                    break
            else:
                cls = cls.__base__
#        else:
#            try:
#                cls = self.__class__
#                found = False
#                while not found:
#                    base = cls.__base__
#                    for k, v in base.__dict__.items():
#                        if v == propertyWrapper:
#                            enum = EnumClass(value, k)
#                            setattr(self.__class__, k, enum)
#                            found = True
#                            break
##            return getter(self.__class__.__base__)
#            except Exception as e:
#                print('Enum not found!!!', e)
#                print('base:', self.__class__.__base__)
#                raise BaseException('Enum not found!')
        return enum
    propertyWrapper = property(getter, lambda v: None)
    return propertyWrapper

def Enum(*args):
    if len(args) < 1:
        raise BaseException('At least 2 values needed!')
    if len(args) == 1:
        if isinstance(args[0], int):
            return [_makeEnum(v) for v in range(args[0])]
        args = list(args[0])
    return [_makeEnum(v) for v in args]


