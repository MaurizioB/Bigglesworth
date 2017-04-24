from os import path
from PyQt4 import QtCore, uic
from bigglesworth.const import status_dict, cursor_list

def get_next_cycle(cycle_obj):
    return cycle_obj.next()

def load_ui(widget, ui_path):
    #fix for cx_freeze
    current = path.dirname(path.abspath(__file__))
    if current.endswith('\\library.zip\\bigglesworth') or current.endswith('\\library.zip\\bigglesworth\\dialogs'):
        current = current.replace('\\library.zip', '')
    elif current.endswith('/library.zip/bigglesworth') or current.endswith('/library.zip/bigglesworth/dialogs'):
        current = current.replace('/library.zip', '')
    return uic.loadUi(path.join(current, ui_path), widget)

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

def get_status(s):
    for k in sorted(status_dict, reverse=True):
        if k&s:
            return status_dict[k]

def cursors(index):
    return cursor_list[index]

def getAlignMask(new, default):
    if new & QtCore.Qt.AlignHorizontal_Mask:
        halign = default & (not QtCore.Qt.AlignHorizontal_Mask) | new
    else:
        halign = default & QtCore.Qt.AlignHorizontal_Mask
    if new & QtCore.Qt.AlignVertical_Mask:
        valign = default & (not QtCore.Qt.AlignVertical_Mask) | new
    else:
        valign = default & QtCore.Qt.AlignVertical_Mask
    return (halign|valign)

class fakeSet(set):
    #this is a fake set for rtmidi single port support, it will always return a single value
    def __init__(self, data=None):
        if data and len(data) > 1:
            data = (data[0], )
            super(fakeSet, self).__init__(data)
        else:
            super(fakeSet, self).__init__()

    def add(self, data):
        self.clear()
        super(fakeSet, self).add(data)

    def __or__(self, data):
        return data


