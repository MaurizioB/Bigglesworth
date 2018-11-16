#!/usr/bin/env python2.7
# *-* encoding: utf-8 *-*

from Qt import QtCore

ctrl2sysex = {
    5: 57,                                                        #glide
    12: 316, 13: 323, 14: 311,                                    #arp
    15: 160, 16: 161, 17: 163, 18: 166,                           #lfo 1
    19: 172, 20: 173, 21: 175, 22: 178,                           #lfo 2
    23: 184, 24: 185, 25: 187, 26: 190,                           #lfo 3
    27: 1, 28: 2, 29: 3, 30: 7, 31: 8, 33: 9, 34: 11,             #osc 1
    35: 17, 36: 18, 37: 19, 38: 23, 39: 24, 40: 25, 41: 27,       #osc 2
    42: 33, 43: 34, 44: 35, 45: 39, 46: 40, 47: 41, 48: 43,       #osc 3
    49: 49,                                                       #sync
    50: 51,                                                       #pitchmod
    51: 56,                                                       #glide mode
    52: 61, 53: 62,                                               #osc 1 lev/bal
    54: 71, 55: 72,                                               #ringmod lev/bal
    56: 63, 57: 64,                                               #osc 2 lev/bal
    58: 65, 59: 66,                                               #osc 3 lev/bal
    60: 67, 61: 68, 62: 69,                                       #noise lev/bal/col
    65: 53,                                                       #glide active
    #66: sostenuto?
    67: 117,                                                      #filter routing
    68: 77, 69: 78, 70: 80, 71: 81, 72: 86, 73: 87,               #filter 1
    74: 88, 75: 90, 76: 92, 77: 93, 78: 95, 
    79: 97, 80: 98, 81: 100, 82: 101, 83: 106, 84: 107,           #filter 2
    85: 108, 86: 110, 87: 112, 88: 113, 89: 115, 
    90: 121, 91: 122, 92: 124, 93: 129, 94: 145, 95: 199,         #fil env
    96: 201, 97: 202, 98: 203, 99: 204, 100: 205,             
    101: 211, 102: 213, 103: 214, 104: 215, 105: 216, 106: 217,   #amp env
    107: 223, 108: 225, 109: 226, 110: 227, 111: 228, 112: 229,   #env3 env
    113: 235, 114: 237, 115: 238, 116: 239, 117: 240, 118: 241,   #env4 env
    }

class RangeObject(tuple):
    def __init__(self, args):
        tuple.__init__(self, args)
        self.minimum, self.maximum, self.step = args
        if (self.minimum, self.maximum) == (0, 1):
            self._range = 0, 1
            self.__contains__ = lambda v: v in 0, 1
            self.sanitize = self.sanitizeFull
        elif self.step == 1:
            self._range = tuple(range(self.minimum, self.maximum + 1))
            self.__contains__ = lambda v: v in self._range
            self.sanitize = self.sanitizeFull
        else:
            self._range = tuple(range(self.minimum, self.maximum + 1, self.step))
            self.__contains__ = lambda v: not (v - self.minimum) % self.step
            self.sanitize = self.sanitizeStep
#        return self

    @property
    def rangeData(self):
        return self.minimum, self.maximum + 1, self.step

    @property
    def fullRange(self):
        return tuple(range(self.minimum, self.maximum + 1, self.step))

    def sanitizeFull(self, value):
        if value < self.minimum:
            return self.minimum
        if value > self.maximum:
            return self.maximum
        return value

    def sanitizeStep(self, value):
        if value in self:
            return value
        if value < self.minimum:
            return self.minimum
        if value > self.maximum:
            return self.maximum
        return self.minimum + int(self.step * round((value - self.minimum)/float(self.step)))

class ValuesObject(dict):
    def __new__(cls, rangeObject, values):
        self = dict.__new__(cls)
        self.rangeObject = rangeObject
        return self

    def __init__(self, rangeObject, values):
        self.rangeObject = rangeObject
        dict.__init__(self, zip(rangeObject.fullRange, values))

    def __getitem__(self, value):
#        print(self.rangeObject.sanitize(value))
        return dict.__getitem__(self, self.rangeObject.sanitize(value))

#_parameterData = namedtuple('parameter', 'id attr range values default fullName shortName family children parent')
#_parameterData.__new__.__defaults__ = ('reserved', None, None, None, None, None, None, None, None)
##workaround to use a list as default parameter
#def _(*args, **kwargs):
#    new = _parameterData(*args,  **kwargs)
#    if new.range:
#        new = new._replace(range=RangeObject(*new.range))
#    if new.children is None:
#        new = new._replace(children={})
#    return new

_groups = (
    ('Osc', 'Oscillators'), 
    ('Glide', 'Common'), 
    ('Modulation', 'Modulation'), 
    ('Arp', 'Arpeggiator'), 
    ('Filter Envelope', 'Envelopes'), 
    ('Amplifier Envelope', 'Envelopes'), 
    ('Envelope 3', 'Envelopes'), 
    ('Envelope 4', 'Envelopes'), 
    ('Name Char', 'Name'), 
    ('Filter 1', 'Filters'), 
    ('Filter 2', 'Filters'), 
    ('LFO', 'LFOs'), 
    ('Modifier', 'Modifiers'), 
    ('Amplifier Mod', 'Common'), 
    ('Effect', 'Effects'), 
    ('', 'Common'), 
    (None, 'Common'), 
    )

orderedParameterGroups = ['Common', 'Oscillators', 'LFOs', 'Envelopes', 'Filters', 'Effects', 'Arpeggiator', 'Modulation', 'Modifiers', 'Name']

class _ParameterData(object):
    def __init__(self, parameterData):
        self._parameterData = parameterData
        self._parameterDict = {}
        for p in parameterData:
            self._parameterDict[p.attr] = p

    def __getitem__(self, item):
        if isinstance(item, int):
            return self._parameterData[item]
        return self._parameterDict[item]

    def __getslice__(self, start=None, end=None, step=None):
        return self._parameterData[start:end:step]

    def __getattr__(self, attr):
        return self._parameterDict[attr]


class _(object):
    def __init__(self, id, attr, range=None, values=None, default=0, fullName=None, shortName=None, family=None, children=None, parent=None):
        self.id = id
        self.attr = attr
        self.range = RangeObject(range) if range else RangeObject((0, 127, 1))
        if values:
            self.values = values
            self.valueDict = ValuesObject(self.range, values)
        else:
            self.values = values
            self.valueDict = {}
        self.default = default
        self.fullName = fullName
        self.shortName = shortName
        self.family = family
        self.children = children if children else {}
        self.parent = parent
        if attr.startswith('reserved'):
            self.group = 'None'
            return
        if family:
            for groupStr, group in _groups:
                if family.startswith(groupStr):
                    self.group = group
                    break
        else:
            self.group = 'Common'

    def __repr__(self):
        return 'Parameter "{fullName}" ({attr}): from {min} to {max}{step}'.format(
            fullName=self.fullName, 
            attr=self.attr, 
            min=self.range.minimum, 
            max=self.range.maximum, 
            step=', in steps of {}'.format(self.range.step) if self.range.step > 1 else ''
            )

    def __str__(self):
        return self.__repr__()


#TODO might want to place the parameter definitions in a separate file
fullRange = tuple([str(x) for x in range(128)])
fmAmount = ('off', )+fullRange[1:]
octave = ('128\'', '64\'', '32\'', '16\'', '8\'', '4\'', '2\'', '1\'', '1/2\'')
#semitoneRange = tuple(['{s}{n}'.format(n=n, s='+' if n>0 else '') for n in range(-12, 13)])
semitoneRange = tuple(['{:{}}'.format(n, '+' if n else '') for n in range(-12, 13)])
#fullRangeCenterZero = tuple(['{s}{n}'.format(n=n, s='+' if n>0 else '') for n in range(-64, 64)])
fullRangeCenterZero = tuple(['{:{}}'.format(n, '+' if n else '') for n in range(-64, 64)])
#bendRange = tuple(['{s}{n}'.format(n=n, s='+' if n>0 else '') for n in range(-24, 25)])
bendRange = tuple(['{:{}}'.format(n, '+' if n else '') for n in range(-24, 25)])
#keytrackRange = tuple('{s}{v}%'.format(s='' if v < 0 else '+', v=v) for v in (-204 + m + 25 * r for r in range(16) for m in (4, 7, 10, 13, 16, 19, 22, 25)))
keytrackRange = tuple('{:{}}%'.format(v, '+' if v else '') for v in (-204 + m + 25 * r for r in range(16) for m in (4, 7, 10, 13, 16, 19, 22, 25)))
balanceRange = tuple('F1 {}'.format(x) for x in range(64, 0, -1)) + ('middle', ) + tuple('F2 {}'.format(x) for x in range(1, 64))
panRange = tuple('left {}'.format(x) for x in range(64, 0, -1)) + ('center', ) + tuple('right {}'.format(x) for x in range(1, 64))
filterRouting = ('parallel', 'serial')
offOn = ('off', 'on')
onOff = ('on', 'off')
phaseRange = ('free', ) + tuple(u'{}°'.format(int(round(i*(3-.2)))) for i in range(127))
arpMode = ('off', 'on', 'One Shot', 'Hold')
arpPattern = ('off', 'User', ) + tuple(str(p) for p in range(16))
arpLength = ('1/96', '1/48', '1/32', '1/16T', '1/32.', '1/16', '1/8T', '1/16.', '1/8', '1/4T', '1/8.', '1/4', '1/2T', '1/4.', '1/2', '1/1T', '1/2.', '1 bar', '1.5 bars', '2 bars', '2.5 bars', '3 bars', '3.5 bars') +\
            tuple('{} bars'.format(b) for b in range(4, 10)+range(10, 20, 2)+range(20, 40, 4)+range(40, 65, 8))
arpOctave = tuple([str(x) for x in range(1, 11)])
arpDirection = ('Up', 'Down', 'Alt Up', 'Alt Down')
arpPatternLength = tuple(str(pl) for pl in range(1, 17))
arpTempo = tuple([str(x) for x in range(40,90,2)+range(90,165)+range(165,301,5)])
characters = tuple(str(unichr(l)) for l in range(32,127))
characters = characters + (u'°', )
effectPolarity = ('positive', 'negative')
fmSource = ('off', 'Osc 1', 'Osc 2', 'Osc 3', 'Noise', 'LFO 1', 'LFO 2', 'LFO 3', 'FilterEnv', 'AmpEnv', 'Env3', 'Env4')
oscShapes = ('off', 'Pulse', 'Saw', 'Triangle', 'Sine', 'Alt 1', 'Alt 2', 'Resonant', 'Resonant2', 'MalletSyn', 'Sqr-Sweep', 
    'Bellish', 'Pul-Sweep', 'Saw-Sweep', 'MellowSaw', 'Feedback', 'Add Harm', 'Reso 3 HP', 'Wind Syn', 'High Harm',
    'Clipper', 'Organ Syn', 'SquareSaw', 'Formant 1', 'Polated', 'Transient', 'ElectricP', 'Robotic', 'StrongHrm', 'PercOrgan', 
    'ClipSweep', 'ResoHarms', '2 Echoes', 'Formant 2', 'FmntVocal', 'MicroSync', 'Micro PWM', 'Glassy', 'Square HP', 
    'SawSync 1', 'SawSync 2', 'SawSync 3', 'PulSync 1', 'PulSync 2', 'PulSync 3', 'SinSync 1', 'SinSync 2', 'SinSync 3',
    'PWM Pulse', 'PWM Saw', 'Fuzz Wave', 'Distorted', 'HeavyFuzz', 'Fuzz Sync', 'K+Strong1', 'K+Strong2', 'K+Strong3',
    '1-2-3-4-5', '19/twenty', 'Wavetrip1', 'Wavetrip2', 'Wavetrip3', 'Wavetrip4', 'MaleVoice', 'Low Piano', 'ResoSweep',
    'Xmas Bell', 'FM Piano', 'Fat Organ', 'Vibes', 'Chorus 2', 'True PWM', 'UpperWaves') + ('reserved', ) * 13 + \
    tuple('User Wt. {}'.format(w) for w in range(1, 40))
glide = ('Portamento', 'fingered P', 'Glissando', 'fingered G')
driveCurves = ('Clipping', 'Tube', 'Hard', 'Medium', 'Soft', 'Pickup 1', 'Pickup 2', 'Rectifier', 'Square', 'Binary', 
    'Overflow', 'Sine Shaper', 'Osc 1 Mod')
filters = ('Bypass', 'LP 24dB', 'LP 12dB', 'BP 24dB', 'BP 12dB', 'HP 24dB', 'HP 12dB', 'Notch24dB', 'Notch12dB',
    'Comb+', 'Comb-', 'PPG LP')
effectType = ('Bypass', 'Chorus', 'Flanger', 'Phaser', 'Overdrive', 'Triple FX', 'Delay', 'Clk.Delay', 'Reverb')
lfoShapes = ('Sine', 'Triangle', 'Square', 'Saw', 'Random', 'S&H')
lfoSpeeds = tuple('{} bars'.format(b) for b in tuple(
    v for s in range(7, -1, -1) for v in range(5 * (2**(s + 1)), 5 * (2**s), -2**s)) + \
    (5, 4, 3.5, 3, 2.5, 2, 1.5)) + ('1 bar', ) + \
    tuple('1/{}'.format(d) for d in ('2.', '1T', '2', '4.', '2T', '4', '8.', '4T', '8', '16.', '8T', '16', '32.', '16T', '32', '48'))
lfoSpeeds = [l for l in lfoSpeeds for r in 0, 1]
modSource = ('off', 'LFO 1', 'LFO1*MW', 'LFO 2', 'LFO2*Press', 'LFO 3', 'FilterEnv', 'AmpEnv', 'Env3', 'Env4', 'Keytrack',
    'Velocity', 'Rel. Velo', 'Pressure', 'Poly Press', 'Pitch Bend', 'Mod Wheel', 'Sustain', 'Foot Ctrl', 'BreathCtrl',
    'Control W', 'Control X', 'Control Y', 'Control Z', 'Unisono V.', 'Modifier 1', 'Modifier 2', 'Modifier 3', 'Modifier 4',
    'minimum', 'MAXIMUM')
modOperator = ('+', '-', '*', 'AND', 'OR', 'XOR', 'MAX', 'min')
modDest = ('Pitch', 'O1 Pitch', 'O1 FM', 'O1 PW/Wave', 'O2 Pitch', 'O2 FM', 'O2 PW/Wave', 'O3 Pitch', 'O3 FM', 'O3 PW',
    'O1 Level', 'O1 Balance', 'O2 Level', 'O2 Balance', 'O3 Level', 'O3 Balance', 'RMod Level', 'RMod Bal.',
    'NoiseLevel', 'Noise Bal.', 'F1 Cutoff', 'F1 Reson.', 'F1 FM', 'F1 Drive', 'F1 Pan',
    'F2 Cutoff', 'F2 Reson.', 'F2 FM', 'F2 Drive', 'F2 Pan',
    'Volume', 'LFO1Speed', 'LFO2Speed', 'LFO3Speed', 'FE Attack', 'FE Decay', 'FE Sustain', 'FE Release',
    'AE Attack', 'AE Decay', 'AE Sustain', 'AE Release', 'E3 Attack', 'E3 Decay', 'E3 Sustain', 'E3 Release',
    'E4 Attack', 'E4 Decay', 'E4 Sustain', 'E4 Release', 'M1 Amount', 'M2 Amount', 'M3 Amount', 'M4 Amount')
arpOrder = ('as played', 'reversed', 'Key Lo>Hi', 'Key Hi>Lo', 'Vel Lo>Hi', 'Vel Hi>Lo')
arpVelocity = ('Each Note', 'First Note', 'Last Note', 'fix 32', 'fix 64', 'fix 100', 'fix 127')
categories = ('Init', 'Arp ', 'Atmo', 'Bass', 'Drum', 'FX  ', 'Keys', 'Lead', 'Mono', 'Pad ', 'Perc', 'Poly', 'Seq ')


#default values are taken from the "Init" sound of the 1.22 firmware
#some of these values are out of range, init original value is referenced as a comment
parameterData = _ParameterData([
    _(0, 'reserved0'), 
    _(1, 'osc1Octave', (16, 112, 12), octave, 64, 'Osc 1 Octave', 'Octave', 'Osc 1'), #init: 0
    _(2, 'osc1Semitone', (52, 76, 1), semitoneRange, 64, 'Osc 1 Semitone', 'Semitone', 'Osc 1'), #init: 1, (52?!)
    _(3, 'osc1Detune', (0, 127, 1), fullRangeCenterZero, 64, 'Osc 1 Detune', 'Detune', 'Osc 1'), 
    _(4, 'osc1BendRange', (40, 88, 1), bendRange, 64, 'Osc 1 Bend Range', 'Bend Range', 'Osc 1'), 
    _(5, 'osc1Keytrack', (0, 127, 1), keytrackRange, 64, 'Osc 1 Keytrack', 'Keytrack', 'Osc 1'), 
    _(6, 'osc1FMSource', (0, 11, 1), fmSource, 0, 'Osc 1 FM Source', 'FM Source', 'Osc 1'), #init: 66
    _(7, 'osc1FMAmount', (0, 127, 1), fullRange, 96, 'Osc 1 FM Amount', 'FM Amount', 'Osc 1'), 
    _(8, 'osc1Shape', (0, 124, 1), oscShapes, 2, 'Osc 1 Shape', 'Shape', 'Osc 1'), 
    _(9, 'osc1Pulsewidth', (0, 127, 1), fullRange, 0, 'Osc 1 Pulsewidth', 'Pulsewidth', 'Osc 1'), 
    _(10, 'osc1PWMSource', (0, 30, 1), modSource, 2, 'Osc 1 PWM Source', 'PWM Source', 'Osc 1'), 
    _(11, 'osc1PWMAmount', (0, 127, 1), fullRangeCenterZero, 127, 'Osc 1 PWM Amount', 'PWM Amount', 'Osc 1'), 
    _(12, 'reserved12'), 
    _(13, 'reserved13'), 
    _(14, 'osc1LimitWT', (0, 1, 1), onOff, 0, 'Osc 1 Limit WT', 'Limit WT', 'Osc 1'), 
    _(15, 'reserved15'), 
    _(16, 'osc1Brilliance', (0, 127, 1), fullRange, 0, 'Osc 1 Brilliance', 'Brilliance', 'Osc 1'), 
    _(17, 'osc2Octave', (16, 112, 12), octave, 64, 'Osc 2 Octave', 'Octave', 'Osc 2'), #init: 0
    _(18, 'osc2Semitone', (52, 76, 1), semitoneRange, 64, 'Osc 2 Semitone', 'Semitone', 'Osc 2'), #init: 0, (52?!)
    _(19, 'osc2Detune', (0, 127, 1), fullRangeCenterZero, 64, 'Osc 2 Detune', 'Detune', 'Osc 2'), 
    _(20, 'osc2BendRange', (40, 88, 1), bendRange, 64, 'Osc 2 Bend Range', 'Bend Range', 'Osc 2'), 
    _(21, 'osc2Keytrack', (0, 127, 1), keytrackRange, 64, 'Osc 2 Keytrack', 'Keytrack', 'Osc 2'), 
    _(22, 'osc2FMSource', (0, 11, 1), fmSource, 0, 'Osc 2 FM Source', 'FM Source', 'Osc 2'), #init: 66
    _(23, 'osc2FMAmount', (0, 127, 1), fullRange, 96, 'Osc 2 FM Amount', 'FM Amount', 'Osc 2'), 
    _(24, 'osc2Shape', (0, 124, 1), oscShapes, 0, 'Osc 2 Shape', 'Shape', 'Osc 2'), 
    _(25, 'osc2Pulsewidth', (0, 127, 1), fullRange, 0, 'Osc 2 Pulsewidth', 'Pulsewidth', 'Osc 2'), 
    _(26, 'osc2PWMSource', (0, 30, 1), modSource, 0, 'Osc 2 PWM Source', 'PWM Source', 'Osc 2'), 
    _(27, 'osc2PWMAmount', (0, 127, 1), fullRangeCenterZero, 127, 'Osc 2 PWM Amount', 'PWM Amount', 'Osc 2'), 
    _(28, 'reserved28'), 
    _(29, 'reserved29'), 
    _(30, 'osc2LimitWT', (0, 1, 1), onOff, 0, 'Osc 2 Limit WT', 'Limit WT', 'Osc 2'), 
    _(31, 'reserved31'), 
    _(32, 'osc2Brilliance', (0, 127, 1), fullRange, 0, 'Osc 2 Brilliance', 'Brilliance', 'Osc 2'), 
    _(33, 'osc3Octave', (16, 112, 12), octave, 52, 'Osc 3 Octave', 'Octave', 'Osc 3'), #init: 0
    _(34, 'osc3Semitone', (52, 76, 1), semitoneRange, 64, 'Osc 3 Semitone', 'Semitone', 'Osc 3'), #init: 0, (52!?)
    _(35, 'osc3Detune', (0, 127, 1), fullRangeCenterZero, 52, 'Osc 3 Detune', 'Detune', 'Osc 3'), 
    _(36, 'osc3BendRange', (40, 88, 1), bendRange, 64, 'Osc 3 Bend Range', 'Bend Range', 'Osc 3'), 
    _(37, 'osc3Keytrack', (0, 127, 1), keytrackRange, 64, 'Osc 3 Keytrack', 'Keytrack', 'Osc 3'), 
    _(38, 'osc3FMSource', (0, 11, 1), fmSource, 0, 'Osc 3 FM Source', 'FM Source', 'Osc 3'), #init: 66
    _(39, 'osc3FMAmount', (0, 127, 1), fullRange, 96, 'Osc 3 FM Amount', 'FM Amount', 'Osc 3'), 
    _(40, 'osc3Shape', (0, 4, 1), oscShapes[:5], 0, 'Osc 3 Shape', 'Shape', 'Osc 3'), 
    _(41, 'osc3Pulsewidth', (0, 127, 1), fullRange, 0, 'Osc 3 Pulsewidth', 'Pulsewidth', 'Osc 3'), 
    _(42, 'osc3PWMSource', (0, 30, 1), modSource, 0, 'Osc 3 PWM Source', 'PWM Source', 'Osc 3'), 
    _(43, 'osc3PWMAmount', (0, 127, 1), fullRangeCenterZero, 127, 'Osc 3 PWM Amount', 'PWM Amount', 'Osc 3'), 
    _(44, 'reserved44'), 
    _(45, 'reserved45'), 
    _(46, 'reserved46'), 
    _(47, 'reserved47'), 
    _(48, 'osc3Brilliance', (0, 127, 1), fullRange, 0, 'Osc 3 Brilliance', 'Brilliance', 'Osc 3'), 
    _(49, 'osc2SyncToO3', (0, 1, 1), offOn, 0, 'Osc 2 Sync to O3', 'Sync to O3', 'Osc 2'), 
    _(50, 'oscPitchSource', (0, 30, 1), modSource, 0, 'Osc Pitch Source', 'Source', 'Osc Pitch'), 
    _(51, 'oscPitchAmount', (0, 127, 1), fullRangeCenterZero, 0, 'Osc Pitch Amount', 'Amount', 'Osc Pitch'), 
    _(52, 'reserved52'), 
    _(53, 'glide', (0, 1, 1), offOn, 0, 'Glide', '', 'Glide'), #init: 64
    _(54, 'reserved54'), 
    _(55, 'reserved55'), 
    _(56, 'glideMode', (0, 3, 1), glide, 0, 'Glide Mode', 'Mode', 'Glide'), 
    _(57, 'glideRate', (0, 127, 1), fullRange, 0, 'Glide Rate', 'Rate', 'Glide'), 
    _(58, 'allocationModeAndUnisono', (0, 127, 1), fullRange, 0, 'Allocation Mode and Unisono', 'Allocation Mode and Unisono', ''), 
    _(59, 'unisonoUniDetune', (0, 127, 1), fullRange, 20, 'Unisono Uni Detune', 'Unisono Uni Detune', ''), 
    _(60, 'reserved60'), 
    _(61, 'mixerOsc1Level', (0, 127, 1), fullRange, 0, 'Mixer Osc 1 Level', 'Level', 'Mixer Osc 1'), 
    _(62, 'mixerOsc1Balance', (0, 127, 1), balanceRange, 0, 'Mixer Osc 1 Balance', 'Balance', 'Mixer Osc 1'), 
    _(63, 'mixerOsc2Level', (0, 127, 1), fullRange, 127, 'Mixer Osc 2 Level', 'Level', 'Mixer Osc 2'), 
    _(64, 'mixerOsc2Balance', (0, 127, 1), balanceRange, 0, 'Mixer Osc 2 Balance', 'Balance', 'Mixer Osc 2'), 
    _(65, 'mixerOsc3Level', (0, 127, 1), fullRange, 127, 'Mixer Osc 3 Level', 'Level', 'Mixer Osc 3'), 
    _(66, 'mixerOsc3Balance', (0, 127, 1), balanceRange, 0, 'Mixer Osc 3 Balance', 'Balance', 'Mixer Osc 3'), 
    _(67, 'mixerNoiseLevel', (0, 127, 1), fullRange, 127, 'Mixer Noise Level', 'Level', 'Mixer Noise'), 
    _(68, 'mixerNoiseBalance', (0, 127, 1), balanceRange, 0, 'Mixer Noise Balance', 'Balance', 'Mixer Noise'), 
    _(69, 'mixerNoiseColour', (0, 127, 1), fullRangeCenterZero, 0, 'Mixer Noise Colour', 'Colour', 'Mixer Noise'), 
    _(70, 'reserved70'), 
    _(71, 'mixerRingModLevel', (0, 127, 1), fullRange, 64, 'Mixer RingMod Level', 'Level', 'Mixer RingMod'), 
    _(72, 'mixerRingModBalance', (0, 127, 1), balanceRange, 0, 'Mixer RingMod Balance', 'Balance', 'Mixer RingMod'), 
    _(73, 'reserved73'), 
    _(74, 'reserved74'), 
    _(75, 'reserved75'), 
    _(76, 'reserved76'), 
    _(77, 'filter1Type', (0, 11, 1), filters, 0, 'Filter 1 Type', 'Type', 'Filter 1'), 
    _(78, 'filter1Cutoff', (0, 127, 1), fullRange, 0, 'Filter 1 Cutoff', 'Cutoff', 'Filter 1'), 
    _(79, 'reserved79'), 
    _(80, 'filter1Resonance', (0, 127, 1), fullRange, 127, 'Filter 1 Resonance', 'Resonance', 'Filter 1'), 
    _(81, 'filter1Drive', (0, 127, 1), fullRange, 64, 'Filter 1 Drive', 'Drive', 'Filter 1'), 
    _(82, 'filter1DriveCurve', (0, 12, 1), driveCurves, 0, 'Filter 1 Drive Curve', 'Drive Curve', 'Filter 1'), 
    _(83, 'reserved83'), 
    _(84, 'reserved84'), 
    _(85, 'reserved85'), 
    _(86, 'filter1Keytrack', (0, 127, 1), keytrackRange, 0, 'Filter 1 Keytrack', 'Keytrack', 'Filter 1'), 
    _(87, 'filter1EnvAmount', (0, 127, 1), fullRangeCenterZero, 0, 'Filter 1 Env Amount', 'Env Amount', 'Filter 1'), 
    _(88, 'filter1EnvVelocity', (0, 127, 1), fullRangeCenterZero, 64, 'Filter 1 Env Velocity', 'Env Velocity', 'Filter 1'), 
    _(89, 'filter1ModSource', (0, 30, 1), modSource, 0, 'Filter 1 Mod Source', 'Mod Source', 'Filter 1'), #init: 64
    _(90, 'filter1ModAmount', (0, 127, 1), fullRangeCenterZero, 64, 'Filter 1 Mod Amount', 'Mod Amount', 'Filter 1'), 
    _(91, 'filter1FMSource', (0, 11, 1), fmSource, 1, 'Filter 1 FM Source', 'FM Source', 'Filter 1'), 
    _(92, 'filter1FMAmount', (0, 127, 1), fmAmount, 64, 'Filter 1 FM Amount', 'FM Amount', 'Filter 1'), 
    _(93, 'filter1Pan', (0, 127, 1), panRange, 0, 'Filter 1 Pan', 'Pan', 'Filter 1'), 
    _(94, 'filter1PanSource', (0, 30, 1), modSource, 0, 'Filter 1 Pan Source', 'Pan Source', 'Filter 1'), 
    _(95, 'filter1PanAmount', (0, 127, 1), fullRangeCenterZero, 64, 'Filter 1 Pan Amount', 'Pan Amount', 'Filter 1'), 
    _(96, 'reserved96'), 
    _(97, 'filter2Type', (0, 11, 1), filters, 0, 'Filter 2 Type', 'Type', 'Filter 2'), #init: 64
    _(98, 'filter2Cutoff', (0, 127, 1), fullRange, 0, 'Filter 2 Cutoff', 'Cutoff', 'Filter 2'), 
    _(99, 'reserved99'), 
    _(100, 'filter2Resonance', (0, 127, 1), fullRange, 127, 'Filter 2 Resonance', 'Resonance', 'Filter 2'), 
    _(101, 'filter2Drive', (0, 127, 1), fullRange, 64, 'Filter 2 Drive', 'Drive', 'Filter 2'), 
    _(102, 'filter2DriveCurve', (0, 12, 1), driveCurves, 0, 'Filter 2 Drive Curve', 'Drive Curve', 'Filter 2'), 
    _(103, 'reserved103'), 
    _(104, 'reserved104'), 
    _(105, 'reserved105'), 
    _(106, 'filter2Keytrack', (0, 127, 1), keytrackRange, 0, 'Filter 2 Keytrack', 'Keytrack', 'Filter 2'), 
    _(107, 'filter2EnvAmount', (0, 127, 1), fullRangeCenterZero, 0, 'Filter 2 Env Amount', 'Env Amount', 'Filter 2'), 
    _(108, 'filter2EnvVelocity', (0, 127, 1), fullRangeCenterZero, 64, 'Filter 2 Env Velocity', 'Env Velocity', 'Filter 2'), 
    _(109, 'filter2ModSource', (0, 30, 1), modSource, 0, 'Filter 2 Mod Source', 'Mod Source', 'Filter 2'), #init: 64
    _(110, 'filter2ModAmount', (0, 127, 1), fullRangeCenterZero, 64, 'Filter 2 Mod Amount', 'Mod Amount', 'Filter 2'), 
    _(111, 'filter2FMSource', (0, 11, 1), fmSource, 0, 'Filter 2 FM Source', 'FM Source', 'Filter 2'), 
    _(112, 'filter2FMAmount', (0, 127, 1), fmAmount, 64, 'Filter 2 FM Amount', 'FM Amount', 'Filter 2'), 
    _(113, 'filter2Pan', (0, 127, 1), panRange, 0, 'Filter 2 Pan', 'Pan', 'Filter 2'), 
    _(114, 'filter2PanSource', (0, 30, 1), modSource, 0, 'Filter 2 Pan Source', 'Pan Source', 'Filter 2'), 
    _(115, 'filter2PanAmount', (0, 127, 1), fullRangeCenterZero, 64, 'Filter 2 Pan Amount', 'Pan Amount', 'Filter 2'), 
    _(116, 'reserved116'), 
    _(117, 'filterRouting', (0, 1, 1), filterRouting, 0, 'Filter Routing', 'Routing', 'Filter'), #init: 64
    _(118, 'reserved118'), 
    _(119, 'reserved119'), 
    _(120, 'reserved120'), 
    _(121, 'amplifierVolume', (0, 127, 1), fullRange, 0, 'Amplifier Volume', 'Volume', 'Amplifier'), 
    _(122, 'amplifierVelocity', (0, 127, 1), fullRangeCenterZero, 0, 'Amplifier Velocity', 'Velocity', 'Amplifier'), 
    _(123, 'amplifierModSource', (0, 30, 1), modSource, 5, 'Amplifier Mod Source', 'Source', 'Amplifier Mod'), #init: 127
    _(124, 'amplifierModAmount', (0, 127, 1), fullRangeCenterZero, 114, 'Amplifier Mod Amount', 'Amount', 'Amplifier Mod'), 
    _(125, 'reserved125'), 
    _(126, 'reserved126'), 
    _(127, 'reserved127'), 
    _(128, 'effect1Type', (0, 5, 1), effectType[:6], 0, 'Effect 1 Type', 'Type', 'Effect 1'), 
    _(129, 'effect1Mix', (0, 127, 1), fullRange, 0, 'Effect 1 Mix', 'Mix', 'Effect 1'), 
    _(130, 'effect1Parameter1', (0, 127, 1), fullRange, 1, 'Effect 1 Parameter 1', 'Parameter 1', 'Effect 1'), 
    _(131, 'effect1Parameter2', (0, 127, 1), fullRange, 0, 'Effect 1 Parameter 2', 'Parameter 2', 'Effect 1'), 
    _(132, 'effect1Parameter3', (0, 127, 1), fullRange, 20, 'Effect 1 Parameter 3', 'Parameter 3', 'Effect 1'), 
    _(133, 'effect1Parameter4', (0, 127, 1), fullRange, 64, 'Effect 1 Parameter 4', 'Parameter 4', 'Effect 1'), 
    _(134, 'effect1Parameter5', (0, 127, 1), fullRange, 64, 'Effect 1 Parameter 5', 'Parameter 5', 'Effect 1'), 
    _(135, 'effect1Parameter6', (0, 127, 1), fullRange, 0, 'Effect 1 Parameter 6', 'Parameter 6', 'Effect 1'), 
    _(136, 'effect1Parameter7', (0, 127, 1), fullRange, 127, 'Effect 1 Parameter 7', 'Parameter 7', 'Effect 1'), 
    _(137, 'effect1Parameter8', (0, 127, 1), fullRange, 127, 'Effect 1 Parameter 8', 'Parameter 8', 'Effect 1'), 
    _(138, 'effect1Parameter9', (0, 1, 1), effectPolarity, 0, 'Effect 1 Parameter 9', 'Parameter 9', 'Effect 1'), #init: 127
    _(139, 'effect1Parameter10', (0, 11, 1), driveCurves[:12], 0, 'Effect 1 Parameter 10', 'Parameter 10', 'Effect 1'), #init: 127
    _(140, 'effect1Parameter11', (0, 127, 1), fullRange, 127, 'Effect 1 Parameter 11', 'Parameter 11', 'Effect 1'), 
    _(141, 'effect1Parameter12', (0, 127, 1), fullRange, 127, 'Effect 1 Parameter 12', 'Parameter 12', 'Effect 1'), 
    _(142, 'effect1Parameter13', (0, 127, 1), fullRange, 127, 'Effect 1 Parameter 13', 'Parameter 13', 'Effect 1'), 
    _(143, 'effect1Parameter14', (0, 127, 1), fullRange, 127, 'Effect 1 Parameter 14', 'Parameter 14', 'Effect 1'), 
    _(144, 'effect2Type', (0, 8, 1), effectType, 8, 'Effect 2 Type', 'Type', 'Effect 2'), #init: 127
    _(145, 'effect2Mix', (0, 127, 1), fullRange, 127, 'Effect 2 Mix', 'Mix', 'Effect 2'), 
    _(146, 'effect2Parameter1', (0, 127, 1), fullRange, 8, 'Effect 2 Parameter 1', 'Parameter 1', 'Effect 2'), 
    _(147, 'effect2Parameter2', (0, 127, 1), fullRange, 0, 'Effect 2 Parameter 2', 'Parameter 2', 'Effect 2'), 
    _(148, 'effect2Parameter3', (0, 127, 1), fullRange, 53, 'Effect 2 Parameter 3', 'Parameter 3', 'Effect 2'), 
    _(149, 'effect2Parameter4', (0, 127, 1), fullRange, 64, 'Effect 2 Parameter 4', 'Parameter 4', 'Effect 2'), 
    _(150, 'effect2Parameter5', (0, 127, 1), fullRange, 100, 'Effect 2 Parameter 5', 'Parameter 5', 'Effect 2'), 
    _(151, 'effect2Parameter6', (0, 127, 1), fullRange, 0, 'Effect 2 Parameter 6', 'Parameter 6', 'Effect 2'), 
    _(152, 'effect2Parameter7', (0, 127, 1), fullRange, 64, 'Effect 2 Parameter 7', 'Parameter 7', 'Effect 2'), 
    _(153, 'effect2Parameter8', (0, 127, 1), fullRange, 100, 'Effect 2 Parameter 8', 'Parameter 8', 'Effect 2'), 
    _(154, 'effect2Parameter9', (0, 127, 1), fullRange, 0, 'Effect 2 Parameter 9', 'Parameter 9', 'Effect 2'), 
    _(155, 'effect2Parameter10', (0, 127, 1), fullRangeCenterZero, 100, 'Effect 2 Parameter 10', 'Parameter 10', 'Effect 2'), 
    _(156, 'effect2Parameter11', (0, 29, 1), arpLength[:30], 15, 'Effect 2 Parameter 11', 'Parameter 11', 'Effect 2'), #init: 110
    _(157, 'effect2Parameter12', (0, 127, 1), fullRange, 0, 'Effect 2 Parameter 12', 'Parameter 12', 'Effect 2'), 
    _(158, 'effect2Parameter13', (0, 127, 1), fullRange, 15, 'Effect 2 Parameter 13', 'Parameter 13', 'Effect 2'), 
    _(159, 'effect2Parameter14', (0, 127, 1), fullRange, 64, 'Effect 2 Parameter 14', 'Parameter 14', 'Effect 2'), 
    _(160, 'LFO1Shape', (0, 5, 1), lfoShapes, 0, 'LFO 1 Shape', 'Shape', 'LFO 1'), #init: 127
    _(161, 'LFO1Speed', (0, 127, 1), lfoSpeeds, 50, 'LFO 1 Speed', 'Speed', 'LFO 1'), #init: 127
    _(162, 'reserved162'), 
    _(163, 'LFO1Sync', (0, 1, 1), offOn, 0, 'LFO 1 Sync', 'Sync', 'LFO 1'), #init: 50
    _(164, 'LFO1Clocked', (0, 1, 1), offOn, 0, 'LFO 1 Clocked', 'Clocked', 'LFO 1'), #init: 64
    _(165, 'LFO1StartPhase', (0, 127, 1), phaseRange, 0, 'LFO 1 Start Phase', 'Start Phase', 'LFO 1'), 
    _(166, 'LFO1Delay', (0, 127, 1), fullRange, 0, 'LFO 1 Delay', 'Delay', 'LFO 1'), 
    _(167, 'LFO1Fade', (0, 127, 1), fullRangeCenterZero, 0, 'LFO 1 Fade', 'Fade', 'LFO 1'), 
    _(168, 'reserved168'), 
    _(169, 'reserved169'), 
    _(170, 'LFO1Keytrack', (0, 127, 1), keytrackRange, 0, 'LFO 1 Keytrack', 'Keytrack', 'LFO 1'), 
    _(171, 'reserved171'), 
    _(172, 'LFO2Shape', (0, 5, 1), lfoShapes, 0, 'LFO 2 Shape', 'Shape', 'LFO 2'), #init: 64
    _(173, 'LFO2Speed', (0, 127, 1), lfoSpeeds, 0, 'LFO 2 Speed', 'Speed', 'LFO 2'), 
    _(174, 'reserved174'), 
    _(175, 'LFO2Sync', (0, 1, 1), offOn, 0, 'LFO 2 Sync', 'Sync', 'LFO 2'), #init: 40
    _(176, 'LFO2Clocked', (0, 1, 1), offOn, 0, 'LFO 2 Clocked', 'Clocked', 'LFO 2'), #init: 64
    _(177, 'LFO2StartPhase', (0, 127, 1), phaseRange, 0, 'LFO 2 Start Phase', 'Start Phase', 'LFO 2'), 
    _(178, 'LFO2Delay', (0, 127, 1), fullRange, 0, 'LFO 2 Delay', 'Delay', 'LFO 2'), 
    _(179, 'LFO2Fade', (0, 127, 1), fullRangeCenterZero, 0, 'LFO 2 Fade', 'Fade', 'LFO 2'), 
    _(180, 'reserved180'), 
    _(181, 'reserved181'), 
    _(182, 'LFO2Keytrack', (0, 127, 1), keytrackRange, 0, 'LFO 2 Keytrack', 'Keytrack', 'LFO 2'), 
    _(183, 'reserved183'), 
    _(184, 'LFO3Shape', (0, 5, 1), lfoShapes, 0, 'LFO 3 Shape', 'Shape', 'LFO 3'), #init: 64
    _(185, 'LFO3Speed', (0, 127, 1), lfoSpeeds, 0, 'LFO 3 Speed', 'Speed', 'LFO 3'), 
    _(186, 'reserved186'), 
    _(187, 'LFO3Sync', (0, 1, 1), offOn, 0, 'LFO 3 Sync', 'Sync', 'LFO 3'), #init: 30
    _(188, 'LFO3Clocked', (0, 1, 1), offOn, 0, 'LFO 3 Clocked', 'Clocked', 'LFO 3'), #init: 64
    _(189, 'LFO3StartPhase', (0, 127, 1), phaseRange, 0, 'LFO 3 Start Phase', 'Start Phase', 'LFO 3'), 
    _(190, 'LFO3Delay', (0, 127, 1), fullRange, 0, 'LFO 3 Delay', 'Delay', 'LFO 3'), 
    _(191, 'LFO3Fade', (0, 127, 1), fullRangeCenterZero, 0, 'LFO 3 Fade', 'Fade', 'LFO 3'), 
    _(192, 'reserved192'), 
    _(193, 'reserved193'), 
    _(194, 'LFO3Keytrack', (0, 127, 1), keytrackRange, 0, 'LFO 3 Keytrack', 'Keytrack', 'LFO 3'), 
    _(195, 'reserved195'), 
    _(196, 'filterEnvelopeModeAndTriggers', (0, 4, 1), fullRange, 0, 'Filter Envelope Mode and Triggers', 'Mode and Triggers', 'Filter Envelope'), #init: 64
    _(197, 'reserved197'), 
    _(198, 'reserved198'), 
    _(199, 'filterEnvelopeAttack', (0, 127, 1), fullRange, 64, 'Filter Envelope Attack', 'Attack', 'Filter Envelope'), 
    _(200, 'filterEnvelopeAttackLevel', (0, 127, 1), fullRange, 0, 'Filter Envelope Attack Level', 'Attack Level', 'Filter Envelope'), 
    _(201, 'filterEnvelopeDecay', (0, 127, 1), fullRange, 0, 'Filter Envelope Decay', 'Decay', 'Filter Envelope'), 
    _(202, 'filterEnvelopeSustain', (0, 127, 1), fullRange, 127, 'Filter Envelope Sustain', 'Sustain', 'Filter Envelope'), 
    _(203, 'filterEnvelopeDecay2', (0, 127, 1), fullRange, 50, 'Filter Envelope Decay 2', 'Decay 2', 'Filter Envelope'), 
    _(204, 'filterEnvelopeSustain2', (0, 127, 1), fullRange, 0, 'Filter Envelope Sustain 2', 'Sustain 2', 'Filter Envelope'), 
    _(205, 'filterEnvelopeRelease', (0, 127, 1), fullRange, 0, 'Filter Envelope Release', 'Release', 'Filter Envelope'), 
    _(206, 'reserved206'), 
    _(207, 'reserved207'), 
    _(208, 'amplifierEnvelopeModeAndTriggers', (0, 4, 1), fullRange, 0, 'Amplifier Envelope Mode and Triggers', 'Mode and Triggers', 'Amplifier Envelope'), 
    _(209, 'reserved209'), 
    _(210, 'reserved210'), 
    _(211, 'amplifierEnvelopeAttack', (0, 127, 1), fullRange, 64, 'Amplifier Envelope Attack', 'Attack', 'Amplifier Envelope'), 
    _(212, 'amplifierEnvelopeAttackLevel', (0, 127, 1), fullRange, 0, 'Amplifier Envelope Attack Level', 'Attack Level', 'Amplifier Envelope'), 
    _(213, 'amplifierEnvelopeDecay', (0, 127, 1), fullRange, 0, 'Amplifier Envelope Decay', 'Decay', 'Amplifier Envelope'), 
    _(214, 'amplifierEnvelopeSustain', (0, 127, 1), fullRange, 127, 'Amplifier Envelope Sustain', 'Sustain', 'Amplifier Envelope'), 
    _(215, 'amplifierEnvelopeDecay2', (0, 127, 1), fullRange, 52, 'Amplifier Envelope Decay 2', 'Decay 2', 'Amplifier Envelope'), 
    _(216, 'amplifierEnvelopeSustain2', (0, 127, 1), fullRange, 127, 'Amplifier Envelope Sustain 2', 'Sustain 2', 'Amplifier Envelope'), 
    _(217, 'amplifierEnvelopeRelease', (0, 127, 1), fullRange, 0, 'Amplifier Envelope Release', 'Release', 'Amplifier Envelope'), 
    _(218, 'reserved218'), 
    _(219, 'reserved219'), 
    _(220, 'envelope3ModeAndTriggers', (0, 4, 1), fullRange, 0, 'Envelope 3 Mode and Triggers', 'Mode and Triggers', 'Envelope 3'), 
    _(221, 'reserved221'), 
    _(222, 'reserved222'), 
    _(223, 'envelope3Attack', (0, 127, 1), fullRange, 64, 'Envelope 3 Attack', 'Attack', 'Envelope 3'), 
    _(224, 'envelope3AttackLevel', (0, 127, 1), fullRange, 0, 'Envelope 3 Attack Level', 'Attack Level', 'Envelope 3'), 
    _(225, 'envelope3Decay', (0, 127, 1), fullRange, 0, 'Envelope 3 Decay', 'Decay', 'Envelope 3'), 
    _(226, 'envelope3Sustain', (0, 127, 1), fullRange, 64, 'Envelope 3 Sustain', 'Sustain', 'Envelope 3'), 
    _(227, 'envelope3Decay2', (0, 127, 1), fullRange, 64, 'Envelope 3 Decay 2', 'Decay 2', 'Envelope 3'), 
    _(228, 'envelope3Sustain2', (0, 127, 1), fullRange, 64, 'Envelope 3 Sustain 2', 'Sustain 2', 'Envelope 3'), 
    _(229, 'envelope3Release', (0, 127, 1), fullRange, 64, 'Envelope 3 Release', 'Release', 'Envelope 3'), 
    _(230, 'reserved230'), 
    _(231, 'reserved231'), 
    _(232, 'envelope4ModeAndTriggers', (0, 4, 1), fullRange, 0, 'Envelope 4 Mode and Triggers', 'Mode and Triggers', 'Envelope 4'), 
    _(233, 'reserved233'), 
    _(234, 'reserved234'), 
    _(235, 'envelope4Attack', (0, 127, 1), fullRange, 64, 'Envelope 4 Attack', 'Attack', 'Envelope 4'), 
    _(236, 'envelope4AttackLevel', (0, 127, 1), fullRange, 0, 'Envelope 4 Attack Level', 'Attack Level', 'Envelope 4'), 
    _(237, 'envelope4Decay', (0, 127, 1), fullRange, 0, 'Envelope 4 Decay', 'Decay', 'Envelope 4'), 
    _(238, 'envelope4Sustain', (0, 127, 1), fullRange, 64, 'Envelope 4 Sustain', 'Sustain', 'Envelope 4'), 
    _(239, 'envelope4Decay2', (0, 127, 1), fullRange, 64, 'Envelope 4 Decay 2', 'Decay 2', 'Envelope 4'), 
    _(240, 'envelope4Sustain2', (0, 127, 1), fullRange, 64, 'Envelope 4 Sustain 2', 'Sustain 2', 'Envelope 4'), 
    _(241, 'envelope4Release', (0, 127, 1), fullRange, 64, 'Envelope 4 Release', 'Release', 'Envelope 4'), 
    _(242, 'reserved242'), 
    _(243, 'reserved243'), 
    _(244, 'reserved244'), 
    _(245, 'modifier1SourceA', (0, 30, 1), modSource, 0, 'Modifier 1 Source A', 'Source A', 'Modifier 1'), 
    _(246, 'modifier1SourceB', (0, 30, 1), modSource, 1, 'Modifier 1 Source B', 'Source B', 'Modifier 1'), 
    _(247, 'modifier1Operation', (0, 7, 1), modOperator, 0, 'Modifier 1 Operation', 'Operation', 'Modifier 1'), 
    _(248, 'modifier1Constant', (0, 127, 1), fullRangeCenterZero, 0, 'Modifier 1 Constant', 'Constant', 'Modifier 1'), 
    _(249, 'modifier2SourceA', (0, 30, 1), modSource, 0, 'Modifier 2 Source A', 'Source A', 'Modifier 2'), 
    _(250, 'modifier2SourceB', (0, 30, 1), modSource, 0, 'Modifier 2 Source B', 'Source B', 'Modifier 2'), #init: 64
    _(251, 'modifier2Operation', (0, 7, 1), modOperator, 0, 'Modifier 2 Operation', 'Operation', 'Modifier 2'), 
    _(252, 'modifier2Constant', (0, 127, 1), fullRangeCenterZero, 0, 'Modifier 2 Constant', 'Constant', 'Modifier 2'), 
    _(253, 'modifier3SourceA', (0, 30, 1), modSource, 0, 'Modifier 3 Source A', 'Source A', 'Modifier 3'), 
    _(254, 'modifier3SourceB', (0, 30, 1), modSource, 0, 'Modifier 3 Source B', 'Source B', 'Modifier 3'), #init: 64
    _(255, 'modifier3Operation', (0, 7, 1), modOperator, 0, 'Modifier 3 Operation', 'Operation', 'Modifier 3'), 
    _(256, 'modifier3Constant', (0, 127, 1), fullRangeCenterZero, 0, 'Modifier 3 Constant', 'Constant', 'Modifier 3'), 
    _(257, 'modifier4SourceA', (0, 30, 1), modSource, 0, 'Modifier 4 Source A', 'Source A', 'Modifier 4'), 
    _(258, 'modifier4SourceB', (0, 30, 1), modSource, 0, 'Modifier 4 Source B', 'Source B', 'Modifier 4'), #init: 64
    _(259, 'modifier4Operation', (0, 7, 1), modOperator, 0, 'Modifier 4 Operation', 'Operation', 'Modifier 4'), 
    _(260, 'modifier4Constant', (0, 127, 1), fullRangeCenterZero, 0, 'Modifier 4 Constant', 'Constant', 'Modifier 4'), 
    _(261, 'modulation1Source', (0, 30, 1), modSource, 0, 'Modulation 1 Source', 'Source', 'Modulation 1'), 
    _(262, 'modulation1Destination', (0, 53, 1), modDest, 1, 'Modulation 1 Destination', 'Destination', 'Modulation 1'), #init: 64
    _(263, 'modulation1Amount', (0, 127, 1), fullRangeCenterZero, 1, 'Modulation 1 Amount', 'Amount', 'Modulation 1'), 
    _(264, 'modulation2Source', (0, 30, 1), modSource, 1, 'Modulation 2 Source', 'Source', 'Modulation 2'), 
    _(265, 'modulation2Destination', (0, 53, 1), modDest, 0, 'Modulation 2 Destination', 'Destination', 'Modulation 2'), #init: 64
    _(266, 'modulation2Amount', (0, 127, 1), fullRangeCenterZero, 0, 'Modulation 2 Amount', 'Amount', 'Modulation 2'), 
    _(267, 'modulation3Source', (0, 30, 1), modSource, 0, 'Modulation 3 Source', 'Source', 'Modulation 3'), 
    _(268, 'modulation3Destination', (0, 53, 1), modDest, 0, 'Modulation 3 Destination', 'Destination', 'Modulation 3'), #init: 64
    _(269, 'modulation3Amount', (0, 127, 1), fullRangeCenterZero, 0, 'Modulation 3 Amount', 'Amount', 'Modulation 3'), 
    _(270, 'modulation4Source', (0, 30, 1), modSource, 0, 'Modulation 4 Source', 'Source', 'Modulation 4'), 
    _(271, 'modulation4Destination', (0, 53, 1), modDest, 0, 'Modulation 4 Destination', 'Destination', 'Modulation 4'), #init: 64
    _(272, 'modulation4Amount', (0, 127, 1), fullRangeCenterZero, 0, 'Modulation 4 Amount', 'Amount', 'Modulation 4'), 
    _(273, 'modulation5Source', (0, 30, 1), modSource, 0, 'Modulation 5 Source', 'Source', 'Modulation 5'), 
    _(274, 'modulation5Destination', (0, 53, 1), modDest, 0, 'Modulation 5 Destination', 'Destination', 'Modulation 5'), #init: 64
    _(275, 'modulation5Amount', (0, 127, 1), fullRangeCenterZero, 0, 'Modulation 5 Amount', 'Amount', 'Modulation 5'), 
    _(276, 'modulation6Source', (0, 30, 1), modSource, 0, 'Modulation 6 Source', 'Source', 'Modulation 6'), 
    _(277, 'modulation6Destination', (0, 53, 1), modDest, 0, 'Modulation 6 Destination', 'Destination', 'Modulation 6'), #init: 64
    _(278, 'modulation6Amount', (0, 127, 1), fullRangeCenterZero, 0, 'Modulation 6 Amount', 'Amount', 'Modulation 6'), 
    _(279, 'modulation7Source', (0, 30, 1), modSource, 0, 'Modulation 7 Source', 'Source', 'Modulation 7'), 
    _(280, 'modulation7Destination', (0, 53, 1), modDest, 0, 'Modulation 7 Destination', 'Destination', 'Modulation 7'), #init: 64
    _(281, 'modulation7Amount', (0, 127, 1), fullRangeCenterZero, 0, 'Modulation 7 Amount', 'Amount', 'Modulation 7'), 
    _(282, 'modulation8Source', (0, 30, 1), modSource, 0, 'Modulation 8 Source', 'Source', 'Modulation 8'), 
    _(283, 'modulation8Destination', (0, 53, 1), modDest, 0, 'Modulation 8 Destination', 'Destination', 'Modulation 8'), #init: 64
    _(284, 'modulation8Amount', (0, 127, 1), fullRangeCenterZero, 0, 'Modulation 8 Amount', 'Amount', 'Modulation 8'), 
    _(285, 'modulation9Source', (0, 30, 1), modSource, 0, 'Modulation 9 Source', 'Source', 'Modulation 9'), 
    _(286, 'modulation9Destination', (0, 53, 1), modDest, 0, 'Modulation 9 Destination', 'Destination', 'Modulation 9'), #init: 64
    _(287, 'modulation9Amount', (0, 127, 1), fullRangeCenterZero, 0, 'Modulation 9 Amount', 'Amount', 'Modulation 9'), 
    _(288, 'modulation10Source', (0, 30, 1), modSource, 0, 'Modulation 10 Source', 'Source', 'Modulation 10'), 
    _(289, 'modulation10Destination', (0, 53, 1), modDest, 0, 'Modulation 10 Destination', 'Destination', 'Modulation 10'), #init: 64
    _(290, 'modulation10Amount', (0, 127, 1), fullRangeCenterZero, 0, 'Modulation 10 Amount', 'Amount', 'Modulation 10'), 
    _(291, 'modulation11Source', (0, 30, 1), modSource, 0, 'Modulation 11 Source', 'Source', 'Modulation 11'), 
    _(292, 'modulation11Destination', (0, 53, 1), modDest, 0, 'Modulation 11 Destination', 'Destination', 'Modulation 11'), #init: 64
    _(293, 'modulation11Amount', (0, 127, 1), fullRangeCenterZero, 0, 'Modulation 11 Amount', 'Amount', 'Modulation 11'), 
    _(294, 'modulation12Source', (0, 30, 1), modSource, 0, 'Modulation 12 Source', 'Source', 'Modulation 12'), 
    _(295, 'modulation12Destination', (0, 53, 1), modDest, 0, 'Modulation 12 Destination', 'Destination', 'Modulation 12'), #init: 64
    _(296, 'modulation12Amount', (0, 127, 1), fullRangeCenterZero, 0, 'Modulation 12 Amount', 'Amount', 'Modulation 12'), 
    _(297, 'modulation13Source', (0, 30, 1), modSource, 0, 'Modulation 13 Source', 'Source', 'Modulation 13'), 
    _(298, 'modulation13Destination', (0, 53, 1), modDest, 0, 'Modulation 13 Destination', 'Destination', 'Modulation 13'), #init: 64
    _(299, 'modulation13Amount', (0, 127, 1), fullRangeCenterZero, 0, 'Modulation 13 Amount', 'Amount', 'Modulation 13'), 
    _(300, 'modulation14Source', (0, 30, 1), modSource, 0, 'Modulation 14 Source', 'Source', 'Modulation 14'), 
    _(301, 'modulation14Destination', (0, 53, 1), modDest, 0, 'Modulation 14 Destination', 'Destination', 'Modulation 14'), #init: 64
    _(302, 'modulation14Amount', (0, 127, 1), fullRangeCenterZero, 0, 'Modulation 14 Amount', 'Amount', 'Modulation 14'), 
    _(303, 'modulation15Source', (0, 30, 1), modSource, 0, 'Modulation 15 Source', 'Source', 'Modulation 15'), 
    _(304, 'modulation15Destination', (0, 53, 1), modDest, 0, 'Modulation 15 Destination', 'Destination', 'Modulation 15'), #init: 64
    _(305, 'modulation15Amount', (0, 127, 1), fullRangeCenterZero, 0, 'Modulation 15 Amount', 'Amount', 'Modulation 15'), 
    _(306, 'modulation16Source', (0, 30, 1), modSource, 0, 'Modulation 16 Source', 'Source', 'Modulation 16'), 
    _(307, 'modulation16Destination', (0, 53, 1), modDest, 0, 'Modulation 16 Destination', 'Destination', 'Modulation 16'), #init: 64
    _(308, 'modulation16Amount', (0, 127, 1), fullRangeCenterZero, 0, 'Modulation 16 Amount', 'Amount', 'Modulation 16'), 
    _(309, 'reserved309'), 
    _(310, 'reserved310'), 
    _(311, 'arpeggiatorMode', (0, 3, 1), arpMode, 0, 'Arpeggiator Mode', 'Mode', 'Arpeggiator'), #init: 16
    _(312, 'arpeggiatorPattern', (0, 16, 1), arpPattern, 0, 'Arpeggiator Pattern', 'Pattern', 'Arpeggiator'), #init: 100
    _(313, 'reserved313'), 
    _(314, 'arpeggiatorClock', (0, 42, 1), arpLength, 0, 'Arpeggiator Clock', 'Clock', 'Arpeggiator'), 
    _(315, 'arpeggiatorLength', (0, 43, 1), arpLength + ('legato', ), 15, 'Arpeggiator Length', 'Length', 'Arpeggiator'), 
    _(316, 'arpeggiatorOctave', (0, 9, 1), arpOctave, 8, 'Arpeggiator Octave', 'Octave', 'Arpeggiator'), 
    _(317, 'arpeggiatorDirection', (0, 3, 1), arpDirection, 0, 'Arpeggiator Direction', 'Direction', 'Arpeggiator'), #init: 5
    _(318, 'arpeggiatorSortOrder', (0, 5, 1), arpOrder, 0, 'Arpeggiator Sort Order', 'Order', 'Arpeggiator Sort'), 
    _(319, 'arpeggiatorVelocity', (0, 6, 1), arpVelocity, 0, 'Arpeggiator Velocity', 'Velocity', 'Arpeggiator'), 
    _(320, 'arpeggiatorTimingFactor', (0, 127, 1), fullRange, 0, 'Arpeggiator Timing Factor', 'Factor', 'Arpeggiator Timing'), 
    _(321, 'reserved321'), 
    _(322, 'arpeggiatorPtnReset', (0, 1, 1), offOn, 0, 'Arpeggiator Ptn Reset', 'Reset', 'Arpeggiator Ptn'), #init: 12
    _(323, 'arpeggiatorPtnLength', (0, 15, 1), arpPatternLength, 0, 'Arpeggiator Ptn Length', 'Length', 'Arpeggiator Ptn'), 
    _(324, 'reserved324'), 
    _(325, 'reserved325'), 
    _(326, 'arpeggiatorTempo', (0, 127, 1), arpTempo, 0, 'Arpeggiator Tempo', 'Tempo', 'Arpeggiator'), 
    _(327, 'arpPatternStepGlideAccent1', (0, 127, 1), fullRange, 4, 'Arp Pattern Step/Glide/Accent 1', '1', 'Arp Pattern Step/Glide/Accent'), #init: 0
    _(328, 'arpPatternStepGlideAccent2', (0, 127, 1), fullRange, 4, 'Arp Pattern Step/Glide/Accent 2', '2', 'Arp Pattern Step/Glide/Accent'), #init: 55
    _(329, 'arpPatternStepGlideAccent3', (0, 127, 1), fullRange, 4, 'Arp Pattern Step/Glide/Accent 3', '3', 'Arp Pattern Step/Glide/Accent'), 
    _(330, 'arpPatternStepGlideAccent4', (0, 127, 1), fullRange, 4, 'Arp Pattern Step/Glide/Accent 4', '4', 'Arp Pattern Step/Glide/Accent'), 
    _(331, 'arpPatternStepGlideAccent5', (0, 127, 1), fullRange, 4, 'Arp Pattern Step/Glide/Accent 5', '5', 'Arp Pattern Step/Glide/Accent'), 
    _(332, 'arpPatternStepGlideAccent6', (0, 127, 1), fullRange, 4, 'Arp Pattern Step/Glide/Accent 6', '6', 'Arp Pattern Step/Glide/Accent'), 
    _(333, 'arpPatternStepGlideAccent7', (0, 127, 1), fullRange, 4, 'Arp Pattern Step/Glide/Accent 7', '7', 'Arp Pattern Step/Glide/Accent'), 
    _(334, 'arpPatternStepGlideAccent8', (0, 127, 1), fullRange, 4, 'Arp Pattern Step/Glide/Accent 8', '8', 'Arp Pattern Step/Glide/Accent'), 
    _(335, 'arpPatternStepGlideAccent9', (0, 127, 1), fullRange, 4, 'Arp Pattern Step/Glide/Accent 9', '9', 'Arp Pattern Step/Glide/Accent'), 
    _(336, 'arpPatternStepGlideAccent10', (0, 127, 1), fullRange, 4, 'Arp Pattern Step/Glide/Accent 10', '10', 'Arp Pattern Step/Glide/Accent'), 
    _(337, 'arpPatternStepGlideAccent11', (0, 127, 1), fullRange, 4, 'Arp Pattern Step/Glide/Accent 11', '11', 'Arp Pattern Step/Glide/Accent'), 
    _(338, 'arpPatternStepGlideAccent12', (0, 127, 1), fullRange, 4, 'Arp Pattern Step/Glide/Accent 12', '12', 'Arp Pattern Step/Glide/Accent'), 
    _(339, 'arpPatternStepGlideAccent13', (0, 127, 1), fullRange, 4, 'Arp Pattern Step/Glide/Accent 13', '13', 'Arp Pattern Step/Glide/Accent'), 
    _(340, 'arpPatternStepGlideAccent14', (0, 127, 1), fullRange, 4, 'Arp Pattern Step/Glide/Accent 14', '14', 'Arp Pattern Step/Glide/Accent'), 
    _(341, 'arpPatternStepGlideAccent15', (0, 127, 1), fullRange, 4, 'Arp Pattern Step/Glide/Accent 15', '15', 'Arp Pattern Step/Glide/Accent'), 
    _(342, 'arpPatternStepGlideAccent16', (0, 127, 1), fullRange, 4, 'Arp Pattern Step/Glide/Accent 16', '16', 'Arp Pattern Step/Glide/Accent'), 
    _(343, 'arpPatternTimingLength1', (0, 127, 1), fullRange, 68, 'Arp Pattern Timing/Length 1', '1', 'Arp Pattern Timing/Length'), #init: 4
    _(344, 'arpPatternTimingLength2', (0, 127, 1), fullRange, 68, 'Arp Pattern Timing/Length 2', '2', 'Arp Pattern Timing/Length'), #init: 4
    _(345, 'arpPatternTimingLength3', (0, 127, 1), fullRange, 68, 'Arp Pattern Timing/Length 3', '3', 'Arp Pattern Timing/Length'), 
    _(346, 'arpPatternTimingLength4', (0, 127, 1), fullRange, 68, 'Arp Pattern Timing/Length 4', '4', 'Arp Pattern Timing/Length'), 
    _(347, 'arpPatternTimingLength5', (0, 127, 1), fullRange, 68, 'Arp Pattern Timing/Length 5', '5', 'Arp Pattern Timing/Length'), 
    _(348, 'arpPatternTimingLength6', (0, 127, 1), fullRange, 68, 'Arp Pattern Timing/Length 6', '6', 'Arp Pattern Timing/Length'), 
    _(349, 'arpPatternTimingLength7', (0, 127, 1), fullRange, 68, 'Arp Pattern Timing/Length 7', '7', 'Arp Pattern Timing/Length'), 
    _(350, 'arpPatternTimingLength8', (0, 127, 1), fullRange, 68, 'Arp Pattern Timing/Length 8', '8', 'Arp Pattern Timing/Length'), 
    _(351, 'arpPatternTimingLength9', (0, 127, 1), fullRange, 68, 'Arp Pattern Timing/Length 9', '9', 'Arp Pattern Timing/Length'), 
    _(352, 'arpPatternTimingLength10', (0, 127, 1), fullRange, 68, 'Arp Pattern Timing/Length 10', '10', 'Arp Pattern Timing/Length'), 
    _(353, 'arpPatternTimingLength11', (0, 127, 1), fullRange, 68, 'Arp Pattern Timing/Length 11', '11', 'Arp Pattern Timing/Length'), 
    _(354, 'arpPatternTimingLength12', (0, 127, 1), fullRange, 68, 'Arp Pattern Timing/Length 12', '12', 'Arp Pattern Timing/Length'), 
    _(355, 'arpPatternTimingLength13', (0, 127, 1), fullRange, 68, 'Arp Pattern Timing/Length 13', '13', 'Arp Pattern Timing/Length'), 
    _(356, 'arpPatternTimingLength14', (0, 127, 1), fullRange, 68, 'Arp Pattern Timing/Length 14', '14', 'Arp Pattern Timing/Length'), 
    _(357, 'arpPatternTimingLength15', (0, 127, 1), fullRange, 68, 'Arp Pattern Timing/Length 15', '15', 'Arp Pattern Timing/Length'), 
    _(358, 'arpPatternTimingLength16', (0, 127, 1), fullRange, 68, 'Arp Pattern Timing/Length 16', '16', 'Arp Pattern Timing/Length'), 
    _(359, 'reserved359'), 
    _(360, 'reserved360'), 
    _(361, 'reserved361'), 
    _(362, 'reserved362'), 
    _(363, 'nameChar00', (32, 127, 1), characters, 32, 'Name Char 00', '00', 'Name Char'), #init: 0
    _(364, 'nameChar01', (32, 127, 1), characters, 32, 'Name Char 01', '01', 'Name Char'), #init: 0
    _(365, 'nameChar02', (32, 127, 1), characters, 73, 'Name Char 02', '02', 'Name Char'), 
    _(366, 'nameChar03', (32, 127, 1), characters, 110, 'Name Char 03', '03', 'Name Char'), 
    _(367, 'nameChar04', (32, 127, 1), characters, 105, 'Name Char 04', '04', 'Name Char'), 
    _(368, 'nameChar05', (32, 127, 1), characters, 116, 'Name Char 05', '05', 'Name Char'), 
    _(369, 'nameChar06', (32, 127, 1), characters, 32, 'Name Char 06', '06', 'Name Char'), 
    _(370, 'nameChar07', (32, 127, 1), characters, 32, 'Name Char 07', '07', 'Name Char'), 
    _(371, 'nameChar08', (32, 127, 1), characters, 32, 'Name Char 08', '08', 'Name Char'), 
    _(372, 'nameChar09', (32, 127, 1), characters, 32, 'Name Char 09', '09', 'Name Char'), 
    _(373, 'nameChar10', (32, 127, 1), characters, 32, 'Name Char 10', '10', 'Name Char'), 
    _(374, 'nameChar11', (32, 127, 1), characters, 32, 'Name Char 11', '11', 'Name Char'), 
    _(375, 'nameChar12', (32, 127, 1), characters, 32, 'Name Char 12', '12', 'Name Char'), 
    _(376, 'nameChar13', (32, 127, 1), characters, 32, 'Name Char 13', '13', 'Name Char'), 
    _(377, 'nameChar14', (32, 127, 1), characters, 32, 'Name Char 14', '14', 'Name Char'), 
    _(378, 'nameChar15', (32, 127, 1), characters, 32, 'Name Char 15', '15', 'Name Char'), 
    _(379, 'category', (0, 12, 1), categories, 0, 'Category', 'Category', ''), #init: 32
    _(380, 'reserved380'), 
    _(381, 'reserved381'), 
    _(382, 'reserved382'), 
])

normalSingle = ('normal', 'single')
adsr = ('ADSR', 'ADS1DS2R', 'One Shot', 'Loop S1S2', 'Loop All')

parameterData[196].children[5] = _(5, 'filterEnvelopeTrigger', (0, 1, 1), normalSingle, 0, 'Filter Envelope Trigger', 'Trigger', 'Filter Envelope')
parameterData[196].children[0] = _(0, 'filterEnvelopeMode', (0, 4, 1), adsr, 0, 'Filter Envelope Mode', 'Mode', 'Filter Envelope')
parameterData[208].children[5] = _(5, 'amplifierEnvelopeTrigger', (0, 1, 1), normalSingle, 0, 'Amplifier Envelope Trigger', 'Trigger', 'Amplifier Envelope')
parameterData[208].children[0] = _(0, 'amplifierEnvelopeMode', (0, 4, 1), adsr, 0, 'Amplifier Envelope Mode', 'Mode', 'Amplifier Envelope')
parameterData[220].children[5] = _(5, 'envelope3Trigger', (0, 1, 1), normalSingle, 0, 'Envelope 3 Trigger', 'Trigger', 'Envelope 3')
parameterData[220].children[0] = _(0, 'envelope3Mode', (0, 4, 1), adsr, 0, 'Envelope 3 Mode', 'Mode', 'Envelope 3')
parameterData[232].children[5] = _(5, 'envelope4Trigger', (0, 1, 1), normalSingle, 0, 'Envelope 4 Trigger', 'Trigger', 'Envelope 4')
parameterData[232].children[0] = _(0, 'envelope4Mode', (0, 4, 1), adsr, 0, 'Envelope 4 Mode', 'Mode', 'Envelope 4')

parameterData[58].children[4] = _(4, 'unisono', (0, 5, 1), ('off', 'dual', '3', '4', '5', '6'), 0, 'Unisono', 'Unisono', 'Allocation Mode and Unisono')
parameterData[58].children[0] = _(0, 'allocationMode', (0, 1, 1), ('Poly', 'Mono'), 0, 'Allocation Mode', 'Allocation', 'Allocation Mode and Unisono')

steps = ('normal', 'pause', 'previous', 'first', 'last', 'first+last', 'chord', 'random')
accents = ('silent', '/4', '/3', '/2', '*1', '*2', '*3', '*4')
length = ('legato', '-3', '-2', '-1', '+0', '+1', '+2', '+3')
timing = ('random', '-3', '-2', '-1', '+0', '+1', '+2', '+3')


sgaID = 326
tlID = 342
for s in range(1, 17):
    stepGlideAccent = parameterData[sgaID + s]
    timingLength = parameterData[tlID + s]
    s = str(s)

    stepGlideAccent.children[4] = _(4, 'arpPatternStep' + s, (0, 7, 1), steps, 0, 'Arpeggiator Pattern Step ' + s, 'Step ' + s, 'Arpeggiator Pattern')
    stepGlideAccent.children[3] = _(3, 'arpPatternGlide' + s, (0, 1, 1), offOn, 0, 'Arpeggiator Pattern Glide ' + s, 'Glide ' + s, 'Arpeggiator Pattern')
    stepGlideAccent.children[0] = _(0, 'arpPatternAccent' + s, (0, 7, 1), accents, 4, 'Arpeggiator Pattern Accent ' + s, 'Accent ' + s, 'Arpeggiator Pattern')

    timingLength.children[4] = _(4, 'arpPatternLength' + s, (0, 7, 1), length, 4, 'Arpeggiator Pattern Length ' + s, 'Length ' + s, 'Arpeggiator Pattern')
    timingLength.children[0] = _(0, 'arpPatternTiming' + s, (0, 7, 1), timing, 4, 'Arpeggiator Pattern Timing ' + s, 'Timing ' + s, 'Arpeggiator Pattern')


def MakeParameter(id, name, rangeObject, default, children):

    def getter(self):
        try:
            return getattr(self, varName)
        except:
            setattr(self, varName, default)
            return default

    def setter(self, value):
        oldValue = getter(self)
        if value == oldValue:
            return
        value = rangeObject.sanitize(value)
        setattr(self, varName, value)
        self.emit(id, name, value, oldValue)

    def advGetter(self):
        value = 0
        for shift, child, mask in children:
            value += child.fget(self) << shift
        return value

    def advSetter(self, value):
        oldValue = advGetter(self)
        if value == oldValue:
            return
        for shift, child, mask in children:
            child.fset(self, value >> shift & mask, False)
        #get again the value from children, since it has been sanitized
        self.emit(id, name, advGetter(self), oldValue)

    varName = '_' + name
    if children:
        return property(advGetter, advSetter)
    return property(getter, setter)

def MakeChildParameter(parentid, id, name, rangeObject, default):

    def getter(self):
        try:
            return getattr(self, varName)
        except:
            setattr(self, varName, default)
            return default

    def setter(self, value, emit=True):
        oldValue = getter(self)
        if value == oldValue:
            return
        value = rangeObject.sanitize(value)
        setattr(self, varName, value)
        if emit:
            self.emit(parentid, name, value, oldValue, id)

    varName = '_' + name
    return property(getter, setter)


class ParameterSubscription(QtCore.QObject):
    valueChanged = QtCore.pyqtSignal([int], [str])
#    _connected = QtCore.pyqtSignal()
#    _disconnected = QtCore.pyqtSignal()


class Parameters(QtCore.QObject):
    #local variable to ensure that the properties are created only once
    __initialized = False
    parameterData = parameterData
    validParameterData = []
    parameterList = []
    validParameterList = []
    indexedValidParameterList = []
    ids = []
    groups = set()

    def __new__(cls, *args, **kwargs):
        obj = QtCore.QObject.__new__(cls, *args, **kwargs)
        obj.widgets = {}
        if not cls.__initialized:
            for param in parameterData:
                childProperties = []
                for childId in sorted(param.children.keys()):
                    child = param.children[childId]
                    mask = sum(1 << b for b in range(child.range.maximum.bit_length()))
                    childProperty = MakeChildParameter(param.id, childId, child.attr, child.range, child.default)
                    setattr(cls, child.attr, childProperty)
                    childProperties.append((childId, childProperty, mask))
                parameterProperty = MakeParameter(param.id, param.attr, param.range, param.default, childProperties)
                cls.ids.append(param.attr)
                setattr(cls, param.attr, parameterProperty)
                cls.parameterList.append(param.attr)
                if not param.attr.startswith('reserved'):
                    cls.validParameterData.append(param)
                    cls.validParameterList.append(param.attr)
                    cls.indexedValidParameterList.append((param.id, param.attr))
            cls.__initialized = True
        return obj

    parameterChanged = QtCore.pyqtSignal(int, object, int, int)

    def __init__(self, parent=None):
        QtCore.QObject.__init__(self, parent)
        self._subscriptions = {}

    def __getitem__(self, item):
        if isinstance(item, int):
            return getattr(self, self.ids[item])
        return getattr(self, item)

    def __getslice__(self, start=None, end=None, step=None):
        return list(self)[start:end:step]

    def __setitem__(self, item, value):
        if isinstance(item, int):
            setattr(self, self.ids[item], value)
        else:
            setattr(self, item, value)

    def __iter__(self):
        for i in range(383):
            yield self[i]

#    def getValues(self):
#        return [getattr()]

    def addWidget(self, parameter, widget):
        self.widgets[parameter] = self.widgets.get(parameter, []) + [widget]
#        if not parameter in self.widgets:
#            self.widgets[parameter] = [widget]
#        else:
#            self.widgets[parameter].append(widget)

    def addWidgets(self, parameter, widgetList):
        self.widgets[parameter] = self.widgets.get(parameter, []) + list(widgetList)

    #create a "ghost" object to subscribe to, which is necessary to connect to widgets 
    #and objects that always need updates (filter routing, effect type, etc.)
    def parameters(self, param):
        if not isinstance(param, str):
            param = self.parameterList[param]
        try:
            return self._subscriptions[param]
        except:
            obj = ParameterSubscription()
            self._subscriptions[param] = obj
            return obj

    def emit(self, id, parameter, value, oldValue, childId=None):
#        print(id, parameter, value, oldValue, childId)
        try:
            widget = getattr(self.parent(), parameter)
            widget.blockSignals(True)
            widget.setValue(value)
            widget.blockSignals(False)
        except Exception as e:
            print('Error trying to set parameter "{}" ({})'.format(parameter, e))
        for widget in self.widgets.get(parameter, []):
            widget.blockSignals(True)
            widget.setValue(value)
            widget.blockSignals(False)
        for child in parameterData[id].children.values():
            try:
                widget = getattr(self.parent(), child.attr)
                widget.blockSignals(True)
                widget.setValue(getattr(self, child.attr))
                widget.blockSignals(False)
            except:
                print('Error trying to set parameter "{}"'.format(child.attr))
        self.parameterChanged.emit(id, childId, value, oldValue)
        try:
            self._subscriptions[parameter].valueChanged.emit(value)
        except:
            pass

    def getValues(self, name=None, category=None):
        from bigglesworth.const import chr2ord
        data = self[:]
        if name is not None:
            for i, l in zip(range(363, 379), name.ljust(16)):
                o = chr2ord.get(l, '?')
                data[i] = o
        if category is not None:
            data[379] = category
        return data

# a fake Parameters object to let it initialize the class
#TODO: maybe you should use a smarter way to do this...
_ = Parameters()
del _
