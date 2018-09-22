#!/usr/bin/env python2.7

import sys, os

os.environ['QT_PREFERRED_BINDING'] = 'PyQt4'

from Qt import QtCore, QtGui, QtWidgets

iconSize = 48
startX = 8
startY = 40

curves = {
    QtCore.QEasingCurve.Linear: ('Linear', 
        'Linear (constant) transition: <span class="formula">x = y</span>'),
    QtCore.QEasingCurve.InQuad: ('Quadratic accelerating', 
        'Quadratic (<span class="formula">t<sup>2</sup></span>) accelerating'),
    QtCore.QEasingCurve.OutQuad: ('Quadratic decelerating', 
        ''),
    QtCore.QEasingCurve.InOutQuad: ('Quadratic accelerating/decelerating', 
        ''),
    QtCore.QEasingCurve.OutInQuad: ('Quadratic decelerating/accelerating', 
        ''),
    QtCore.QEasingCurve.InCubic: ('Cubic accelerating', 
        ''),
    QtCore.QEasingCurve.OutCubic: ('Cubic decelerating', 
        ''),
    QtCore.QEasingCurve.InOutCubic: ('Cubic accelerating/decelerating', 
        ''),
    QtCore.QEasingCurve.OutInCubic: ('Cubic decelerating/accelerating', 
        ''),
    QtCore.QEasingCurve.InQuart: ('Quartic accelerating', 
        ''),
    QtCore.QEasingCurve.OutQuart: ('Quartic decelerating', 
        ''),
    QtCore.QEasingCurve.InOutQuart: ('Quartic accelerating/decelerating', 
        ''),
    QtCore.QEasingCurve.OutInQuart: ('Quartic decelerating/accelerating', 
        ''),
    QtCore.QEasingCurve.InQuint: ('Quintic accelerating', 
        ''),
    QtCore.QEasingCurve.OutQuint: ('Quintic decelerating', 
        ''),
    QtCore.QEasingCurve.InOutQuint: ('Quintic accelerating/decelerating', 
        ''),
    QtCore.QEasingCurve.OutInQuint: ('Quintic decelerating/accelerating', 
        ''),
    QtCore.QEasingCurve.InSine: ('Sine accelerating', 
        ''),
    QtCore.QEasingCurve.OutSine: ('Sine decelerating', 
        ''),
    QtCore.QEasingCurve.InOutSine: ('Sine accelerating/decelerating', 
        ''),
    QtCore.QEasingCurve.OutInSine: ('Sine decelerating/accelerating', 
        ''),
    QtCore.QEasingCurve.InExpo: ('Exponential accelerating', 
        ''),
    QtCore.QEasingCurve.OutExpo: ('Exponential decelerating', 
        ''),
    QtCore.QEasingCurve.InOutExpo: ('Exponential accelerating/decelerating', 
        ''),
    QtCore.QEasingCurve.OutInExpo: ('Exponential decelerating/accelerating', 
        ''),
    QtCore.QEasingCurve.InCirc: ('Circular accelerating', 
        ''),
    QtCore.QEasingCurve.OutCirc: ('Circular decelerating', 
        ''),
    QtCore.QEasingCurve.InOutCirc: ('Circular accelerating/decelerating', 
        ''),
    QtCore.QEasingCurve.OutInCirc: ('Circular decelerating/accelerating', 
        ''),
    QtCore.QEasingCurve.OutInBack: ('Overshooting decelerating/accelerating', 
        ''),
    QtCore.QEasingCurve.InBounce: ('Bounce accelerating', 
        ''),
    QtCore.QEasingCurve.OutBounce: ('Bounce decelerating', 
        ''),
    QtCore.QEasingCurve.InOutBounce: ('Bounce accelerating/decelerating', 
        ''),
    QtCore.QEasingCurve.OutInBounce: ('Bounce decelerating/accelerating', 
        ''),
}

def getName(c):
    for k, v in QtCore.QEasingCurve.__dict__.items():
        if v == c:
            return k

maxName = max(len(curves[c][0]) for c in curves) + len(':curve:``')
maxIcon = max(len(getName(c)) for c in curves) + 4

#class W(QtWidgets.QWidget):
#    def __init__(self):
#        QtWidgets.QWidget.__init__(self)
#        l = QtWidgets.QGridLayout()
#        self.setLayout(l)

def buildRst():
    line = '+{}+{}+\n'.format('-' * (maxIcon), '-' * maxName)
    txt = line
    for c in curves:
        title, desc = curves[c]
        txt += '|{}|{}|\n'.format('|{}|'.format(getName(c)).center(maxIcon, ' '), ':curve:`{}`'.format(title).ljust(maxName, ' '))
        txt += '|{}|{}|\n'.format(' ' * maxIcon, desc.ljust(maxName))
        txt += line
    return txt

def buildHtml():
    txt = '''.. raw:: html
    
    <br/><table width="100%" class="curvetable" cellspacing="0" cellpadding="4">\n'''
    for c in curves:
        title, desc = curves[c]
        img = '<img src=":/images/curves/{}"/>'.format(getName(c))
        desc = '<span class="curve">{}</span><br/>{}'.format(title, desc)
        txt += '        <tr><td align="center" width="5%">{}</td><td>{}</td></tr>\n'.format(img, desc)
    txt += '    </table>\n\n'
    return txt

def doPixmap(c, bgd, gPen, cPen):
    pixmap = QtGui.QPixmap(iconSize, iconSize)
    pixmap.fill(bgd)
    qp = QtGui.QPainter(pixmap)
    qp.setRenderHints(qp.Antialiasing)

    qp.save()
    qp.setPen(gPen)
    qp.translate(.5, 1.5)
    qp.drawLine(startX, 0, startX, iconSize)
    qp.drawLine(0, startY, iconSize, startY)
    qp.restore()

    qp.save()
    qp.setPen(cPen)
    qp.translate(startX - .5, startY + 1.5)
    path = QtGui.QPainterPath()
    func = QtCore.QEasingCurve(c).valueForProgress
    ratio = 1. / startY
    for x in range((startY + 1) * 2):
        x *= .5
        path.lineTo(x, -func(x * ratio) * startY)
    qp.drawPath(path)
    qp.restore()

    qp.setPen(QtCore.Qt.black)
    font = qp.font()
    font.setPointSize(startX)
    qp.drawText(pixmap.rect(), QtCore.Qt.AlignTop|QtCore.Qt.AlignLeft, 'y')
    qp.drawText(pixmap.rect().adjusted(0, 0, 0, QtGui.QFontMetrics(font).descent() * 2), QtCore.Qt.AlignBottom|QtCore.Qt.AlignRight, 't')

    qp.end()

    fileName = '{}.png'.format(getName(c))
    pixmap.save(fileName, quality=50)

    print('"{}" done.'.format(fileName))
    return fileName

def doCurves():
    bgd = QtGui.QColor(212, 225, 222, 131)
    gPen = QtGui.QPen(QtGui.QColor(145, 181, 225), .5)
    cPen = QtGui.QPen(QtGui.QColor(16, 64, 90), 1.5)

    files = []
    for c in curves:
        files.append(doPixmap(c, bgd, gPen, cPen))
    return files

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)

    doCurves
    print('\n\n')
    print(buildRst())

    sys.exit(app.exec_())
