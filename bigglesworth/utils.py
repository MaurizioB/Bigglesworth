from os import path
from PyQt4 import QtCore, uic
from const import *

def get_next_cycle(cycle_obj):
    return cycle_obj.next()

def load_ui(widget, ui_path):
    return uic.loadUi(path.join(path.dirname(path.abspath(__file__)), ui_path), widget)

def setBold(item, bold=True):
    font = item.font()
    font.setBold(bold)
    item.setFont(font)

def get_status(s):
    for k in sorted(status_dict, reverse=True):
        if k&s:
            return status_dict[k]

def cursors(id):
    return cursor_list[id]

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



