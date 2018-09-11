import sys
from math import sqrt, sin, pi
import re

from Qt import QtCore, QtGui

#noteFreqs = (16.35, 17.32, 18.35, 19.45, 20.6, 21.83, 23.12, 24.5, 25.96, 27.5, 29.14, 30.87, 
#    32.7, 34.65, 36.71, 38.89, 41.2, 43.65, 46.25, 49.0, 51.91, 55.0, 58.27, 61.74, 
#    65.41, 69.3, 73.42, 77.78, 82.41, 87.31, 92.5, 98.0, 103.83, 110.0, 116.54, 123.47, 
#    130.81, 138.59, 146.83, 155.56, 164.81, 174.61, 185.0, 196.0, 207.65, 220.0, 233.08, 246.94, 
#    261.63, 277.18, 293.66, 311.13, 329.63, 349.23, 369.99, 392.0, 415.3, 440.0, 466.16, 493.88, 
#    523.25, 554.37, 587.33, 622.25, 659.25, 698.46, 739.99, 783.99, 830.61, 880.0, 932.33, 987.77, 
#    1046.5, 1108.73, 1174.66, 1244.51, 1318.51, 1396.91, 1479.98, 1567.98, 1661.22, 1760.0, 1864.66, 1975.53, 
#    2093.0, 2217.46, 2349.32, 2489.02, 2637.02, 2793.83, 2959.96, 3135.96, 3322.44, 3520.0, 3729.31, 3951.07, 
#    4186.01, 4434.92, 4698.63, 4978.03, 5274.04, 5587.65, 5919.91, 6271.93, 6644.88, 7040.0, 7458.62, 7902.13)

sqrt_center = 4*(sqrt(2)-1)/3
_x0 = _y3 = 0
_y0 = _y1 = _x2 = _x3 = 1
_x1 = _y2 = sqrt_center

def balanceSqrt(t):
#   original function:
#    X0*(1-t)^3 + 3*X1*(1-t)^2*t + 3*X2*(1-t)*t**2 + X3*t**3
#    x = p0.x*pow((1-t),3) + 3*p1.x*pow((1-t),2)*t + 3*p2.x*(1-t)*pow(t,2) + p3.x*pow(t,3)
#    y = p0.y*pow((1-t),3) + 3*p1.y*pow((1-t),2)*t + 3*p2.y*(1-t)*pow(t,2) + p3.y*pow(t,3)
    x = (3 * _x1 * pow((1 - t), 2) * t) + (3 * _x2 * (1 - t) * pow(t, 2)) + (_x3 * pow(t, 3))
    y = (_y0 * pow((1 - t), 3)) + (3 * _y1 * pow((1 - t), 2) * t) + (3 * _y2 * (1 - t) * pow(t, 2))
    return y, x

def balanceLinear(t):
    return 1 - t, t

balanceFuncs = balanceLinear, balanceSqrt

noteFreqs = {}
def noteFrequency(note, tuning=440):
    try:
        return noteFreqs[note]
    except:
        f = 2 ** ((note - 69) / 12.) * tuning
        noteFreqs[note] = f
        return f


#PathRole = QtCore.Qt.UserRole + 1

#def parseTime(seconds):
#    if seconds < 60:
#        return '{:02.03f}s'.format(seconds)
#    elif seconds < 3600:
#        return '{:02.0f}:{:02.03f}'.format(*divmod(seconds, 60))
#    else:
#        minutes, seconds = divmod(seconds, 60)
#        hours, minutes = divmod(minutes, 60)
#        return '{:02.0f}:{:02.0f}:{:.03f}'.format(hours, minutes, seconds)

#sine128 = tuple(sin(2 * pi * r * (0.0078125)) for r in xrange(128))
sineData = {}
def sineValues(fract, count=128):
    try:
        return sineData[(fract, count)]
    except:
#        ratio = 0.0078125 * fract
        ratio = 1./count * fract
        values = tuple(sin(2 * pi * r * ratio) for r in xrange(count))
        sineData[(fract, count)] = values
        return values

squareData = {}
def squareValues(fract):
    try:
        return squareData[fract]
    except:
        values = tuple(1 if v >= 0 else -1 for v in sineValues(fract))
        squareData[fract] = values
        return values

sawData = {}
def sawToothValues(fract):
    try:
        return sawData[fract]
    except:
        values = [0]
        ratio = fract / 64.
        value = 0
        for sine in sineValues(fract)[1:]:
            value += ratio
            if value >= 1:
                value = -1
            values.append(value)
        sawData[fract] = values
        return values

inverseSawData = {}
def inverseSawValues(fract):
    try:
        return inverseSawData[fract]
    except:
        values = list(reversed(sawToothValues(fract)))
        inverseSawData[fract] = values
        return values

waveFunction = [sineValues, squareValues, sawToothValues, inverseSawValues]

pow22 = 2**22
pow21 = 2**21
pow20 = 2**20
pow19 = 2**19
pow16 = 2**16

baseSineValues = []
for sine in sineValues(1):
    baseSineValues.append(int(sine*pow19))

curves = {
    QtCore.QEasingCurve.Linear: 'Linear', 
    QtCore.QEasingCurve.InQuad: 'Quadratic accelerating', 
    QtCore.QEasingCurve.OutQuad: 'Quadratic decelerating', 
    QtCore.QEasingCurve.InOutQuad: 'Quadratic accel/decel', 
    QtCore.QEasingCurve.OutInQuad: 'Quadratic decel/accel', 
    QtCore.QEasingCurve.InCubic: 'Cubic accelerating', 
    QtCore.QEasingCurve.OutCubic: 'Cubic decelerating', 
    QtCore.QEasingCurve.InOutCubic: 'Cubic accel/decel', 
    QtCore.QEasingCurve.OutInCubic: 'Cubic decel/accel', 
    QtCore.QEasingCurve.InQuart: 'Quartic accelerating', 
    QtCore.QEasingCurve.OutQuart: 'Quartic decelerating', 
    QtCore.QEasingCurve.InOutQuart: 'Quartic accel/decel', 
    QtCore.QEasingCurve.OutInQuart: 'Quartic decel/accel', 
    QtCore.QEasingCurve.InQuint: 'Quintic accelerating', 
    QtCore.QEasingCurve.OutQuint: 'Quintic decelerating', 
    QtCore.QEasingCurve.InOutQuint: 'Quintic accel/decel', 
    QtCore.QEasingCurve.OutInQuint: 'Quintic decel/accel', 
    QtCore.QEasingCurve.InSine: 'Sine accelerating', 
    QtCore.QEasingCurve.OutSine: 'Sine decelerating', 
    QtCore.QEasingCurve.InOutSine: 'Sine accel/decel', 
    QtCore.QEasingCurve.OutInSine: 'Sine decel/accel', 
    QtCore.QEasingCurve.InExpo: 'Exponential accelerating', 
    QtCore.QEasingCurve.OutExpo: 'Exponential decelerating', 
    QtCore.QEasingCurve.InOutExpo: 'Exponential accel/decel', 
    QtCore.QEasingCurve.OutInExpo: 'Exponential decel/accel', 
    QtCore.QEasingCurve.InCirc: 'Circular accelerating', 
    QtCore.QEasingCurve.OutCirc: 'Circular decelerating', 
    QtCore.QEasingCurve.InOutCirc: 'Circular accel/decel', 
    QtCore.QEasingCurve.OutInCirc: 'Circular decel/accel', 
    QtCore.QEasingCurve.OutInBack: 'Overshooting decel/accel', 
    QtCore.QEasingCurve.InBounce: 'Bounce accelerating', 
    QtCore.QEasingCurve.OutBounce: 'Bounce decelerating', 
    QtCore.QEasingCurve.InOutBounce: 'Bounce accel/decel', 
    QtCore.QEasingCurve.OutInBounce: 'Bounce decel/accel', 
}

curveFuncs = {}
def getCurveFunc(curveType):
    try:
        return curveFuncs[curveType].valueForProgress
    except:
        curve = QtCore.QEasingCurve(curveType)
        curveFuncs[curveType] = curve
        return curve.valueForProgress

curvePaths = {}
def getCurvePath(curveType, size=50):
    try:
        return curvePaths[(curveType, size)]
    except:
        curveFunc = getCurveFunc(curveType)
        path = QtGui.QPainterPath()
        path.moveTo(0, size)
        fSize = float(size)
        for x in range(1, size + 1):
            y = size - curveFunc(x / fSize) * size
            path.lineTo(x, y)
        curvePaths[(curveType, size)] = path
        return path

if sys.platform == 'win32':
    forbiddenChars = re.compile(r'[<>:\"\/\\\|\?\*]')
else:
    forbiddenChars = re.compile(r'/')

fixFileName = lambda name: forbiddenChars.sub('_', name)

def parseTime(seconds, verbose=False, approx=False, floatSeconds=True):
    if seconds < 60:
        if verbose:
            if not floatSeconds:
                return '{} seconds'.format(int(seconds))
            if approx:
                if seconds >= 55:
                    return 'less than 1 minute'
        return '{:02.0{}f}{}'.format(seconds, 3 if floatSeconds else '', ' seconds' if verbose else 's')
    elif seconds < 3600:
        if verbose:
            if approx:
                if seconds >= 3300:
                    return '1 hour'
                minutes, seconds = map(int, divmod(seconds, 60))
                if seconds >= 55:
                    return '{} minutes'.format(minutes + 1)
                elif seconds <= 5:
                    return '{} minutes'.format(minutes)
                return '{} minutes and {} seconds'.format(minutes, seconds)
            if floatSeconds:
                return '{:02.0f} minutes and {:02.03f} seconds'.format(*divmod(seconds, 60))
            return '{:02.0f} minutes and {:02.0f} seconds'.format(*divmod(seconds, 60))
        if floatSeconds:
            return '{:02.0f}:{:02.03f}'.format(*divmod(seconds, 60))
        return '{:02.0f}:{:02.0f}'.format(*divmod(seconds, 60))
    else:
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if verbose:
            if approx:
                if minutes >= 55:
                    return '{} hours'.format(hours + 1)
                elif minutes <= 5:
                    return '{} hour{}'.format(hours, 's' if hours > 1 else '')
                hours, minutes, seconds = map(int, (hours, minutes, seconds))
                if seconds >= 55:
                    return '{} hour{} and {} minutes'.format(hours, 's' if hours > 1 else '', minutes + 1)
                elif seconds <= 5:
                    return '{} hour{} and {} minutes'.format(hours, 's' if hours > 1 else '', minutes)
                return '{} hour{}, {} minutes and {} seconds'.format(
                    hours, 's' if hours > 1 else '', minutes, seconds)
            return '{} hour{}, {} minutes and {} seconds'.format(hours, minutes, seconds)
        return '{:02.0f}:{:02.0f}:{:.0{}f}'.format(hours, minutes, seconds, 3 if floatSeconds else '')



class ActivateDrag(QtGui.QDrag):
    def __init__(self, *args, **kwargs):
        QtGui.QDrag.__init__(self, *args, **kwargs)
        self.targetChanged.connect(self.activateWindow)

    def activateWindow(self, target):
        try:
            if target:
                target.window().activateWindow()
        except:
            pass


