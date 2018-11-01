# *-* encoding: utf-8 *-*

from unidecode import unidecode

from Qt import QtGui

def getASCII(char):
    if 32 <= ord(char) <= 126 or char == u'°':
        return char
    #Some characters (like ß) are converted as multiple letters; to avoid
    #confusion with 16 characters limit in names, get only the first one
    return unidecode(char)[0]

class NameValidator(QtGui.QValidator):
    def validate(self, input, pos):
        output = ''
        for l in input:
            output += getASCII(l)
        return self.Acceptable, output, pos
