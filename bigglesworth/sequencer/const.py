from collections import OrderedDict

import os

os.environ['QT_PREFERRED_BINDING'] = 'PyQt4'

from Qt import QtCore, QtGui
from pianokeyboard import _noteNumberToName

from bigglesworth.parameters import ctrl2sysex, Parameters
from bigglesworth.midiutils import NamedControllers

PlayheadPen = QtGui.QPen(QtCore.Qt.red)
PlayheadPen.setCosmetic(True)
EndMarkerPen = QtGui.QPen(QtGui.QColor(88, 167, 255))
EndMarkerPen.setCosmetic(True)

#NoteNames = 'C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'
OctaveOffset = 1
MinimumLength = 1./512
NoteParameter, CtrlParameter, SysExParameter, AdvancedParameter = 0, 1, 4, 6
ParameterTypes = CtrlParameter, SysExParameter, AdvancedParameter
ParameterTypeMask = 7
#TODO BeatHUnit will be set from pixelratio!
BeatHUnit = 16

TimelineEventTypes = Bar, Marker, Tempo, Meter = 0, 1, 2, 4
TimelineEventMask = Marker | Tempo | Meter
MouseModes = Select, Draw, Erase = range(3)

Mappings = OrderedDict([
    ('Blofeld',  {c:Parameters.parameterData[s].shortName for c, s in ctrl2sysex.items()}), 
    ('Standard MIDI', NamedControllers), 
])


noteNames = []
noteNamesWithPitch = []
for n in range(128):
    name = _noteNumberToName[n].upper()
    noteNames.append(name)
    noteNamesWithPitch.append('{} ({})'.format(name, n))

def getCtrlNameFromMapping(ctrl, mapping='Blofeld', short=False):
    try:
        if mapping == 'Blofeld':
            param = Parameters.parameterData[ctrl2sysex[ctrl]]
            description = param.fullName
            if param.range != (0, 127, 1) and not short:
                description += ' ({}-{})'.format(param.range.minimum, param.range.maximum)
            valid = 2
        else:
            description = Mappings[mapping][ctrl]
            valid = 2
    except:
        try:
            description = NamedControllers[ctrl]
            valid = 1
        except:
            description = '(undefined)'
            valid = 0
    return description, valid

Intervals = {
    2: (2, 1), 
    3: (4, 3), 
    4: (5, 6), 
    5: (7, 8, 6), 
    6: (9, 8, 10), 
    7: (11, 10), 
    8: (12, ), 
    9: (14, 13), 
}

Cardinals = {
    2: '2nd', 
    3: '3rd', 
    4: '4th', 
    5: '5th', 
    6: '6th', 
    7: '7th', 
    8: '8th', 
    9: '9th', 
}

IntervalNames = {}
IntervalNamesShort = {}
for diatonicInterval, intervals in Intervals.items():
    for interval in intervals:
        if diatonicInterval in (4, 5):
            if interval == intervals[0]:
                chordType = 'Perfect'
                chordTypeShort = 'perf'
            elif interval > intervals[0]:
                chordTypeShort = 'aug'
                chordType = 'Augmented'
            else:
                chordTypeShort = 'dim'
                chordType = 'Diminished'
        else:
            if interval == intervals[0]:
                chordTypeShort = 'Maj'
                chordType = 'Major'
            elif interval < intervals[0]:
                chordTypeShort = 'min'
                chordType = 'Minor'
            else:
                chordTypeShort = 'aug'
                chordType = 'Augmented'
        IntervalNames[(diatonicInterval, interval)] = '{} {}'.format(chordType, Cardinals[diatonicInterval])
        IntervalNamesShort[(diatonicInterval, interval)] = chordTypeShort

Chords = (
    ({3: 4, 5: 7}, 'Major triad'), 
    ({3: 3, 5: 7}, 'Minor triad'), 
    ({3: 3, 5: 6}, 'Diminished triad'), 
    ({3: 4, 5: 7, 7: 11}, 'Major seventh'), 
    ({3: 4, 5: 7, 7: 10}, 'Dominant seventh'), 
    ({3: 3, 5: 7, 7: 10}, 'Minor seventh'), 
    ({3: 3, 5: 6, 7: 10}, 'Half-diminished seventh'), 
    ({3: 3, 5: 6, 7: 9}, 'Diminished seventh'), 
)

class SnapMode(object):
    def __init__(self, numerator, denominator, triplet=False):
        self.denominator = denominator
        self.triplet = triplet
        self.tripletText = 't' if triplet else ''

        if numerator:
            self.iconName = 'note-{}-{}{}'.format(
                numerator, denominator, self.tripletText)
            self.icon = QtGui.QIcon.fromTheme(self.iconName)
            self.label = '{}/{}{}'.format(numerator, denominator, self.tripletText)
        else:
            self.icon = QtGui.QIcon.fromTheme('document-edit')
            self.label = 'Free'

        self.numerator = numerator
        if triplet:
            self.numerator *= 2. / 3
        self.length = float(self.numerator) / self.denominator * 4
#        if self.triplet:
#            self.length *= 2. / 3

    def __iter__(self):
        yield self.numerator
        yield self.denominator
        yield self.triplet


DefaultNoteSnapMode = SnapMode(1, 4, False)
DefaultPatternSnapMode = SnapMode(4, 4, False)

SnapModes = [
    SnapMode(1, 16, True), 
    SnapMode(1, 16, False), 
    SnapMode(1, 8, True), 
    SnapMode(1, 8, False), 
    SnapMode(3, 16, False), 
    SnapMode(1, 4, True), 
    DefaultNoteSnapMode, 
    SnapMode(3, 8, False), 
    SnapMode(2, 4, False), 
    SnapMode(3, 4, False), 
    DefaultPatternSnapMode, 
    SnapMode(0, 1, False), 
]

DefaultNoteSnapModeId = SnapModes.index(DefaultNoteSnapMode)
DefaultPatternSnapModeId = SnapModes.index(DefaultPatternSnapMode)

SnapModeRole = QtCore.Qt.UserRole + 1
QuantizeRole = QtCore.Qt.UserRole + 1
ParameterRole = QtCore.Qt.UserRole + 1
ValidMappingRole = ParameterRole + 1


