# *-* encoding: utf-8 *-*

from Qt import QtCore

#from bigglesworth.version import __version__

LogInfo, LogDebug, LogWarning, LogCritical, LogFatal = range(5)

#library roles
UidRole = QtCore.Qt.UserRole + 1
DataRole = UidRole + 1
CatRole = DataRole + 1
LocationRole = CatRole + 1
TagsRole = LocationRole + 1
TagColorRole = TagsRole + 1
HoverRole = QtCore.Qt.UserRole + 64

#library model data
UidColumn, LocationColumn, NameColumn, CatColumn, TagsColumn, FactoryColumn = range(6)
headerLabels = {
    NameColumn: 'Name', 
    CatColumn: 'Category', 
    TagsColumn: 'Tags'
    }

#tag roles
nameRole = QtCore.Qt.UserRole + 1
backgroundRole = nameRole + 1
foregroundRole = backgroundRole + 1

#blofeld constants
INIT = 0xf0
END = 0xf7
BROADCAST = 0x7f
CHK = 0x7f
IDW = 0x3e
IDE = 0x13
SNDR = 0
SNDD = 0x10
SNDP = 0x20
GLBR = 0x4
GLBD = 0x14
WTBD = 0x12


factoryPresets = ['blofeld_fact_200801', u'blofeld_fact_200802', u'blofeld_fact_201200']
#factoryPresetsPaths = ['presets/{}.mid'.format(f) for f in factoryPresets]
factoryPresetsNames = ['Waldorf Factory Jan.2008', 'Waldorf Factory Feb.2008', 'Waldorf Factory 2012']
#factoryPresetsNamesDict = {f:n for f, n in zip(factoryPresets, factoryPresetsNames)}
factoryPresetsNamesDict = dict(zip(factoryPresets, factoryPresetsNames))
#    'blofeld_fact_200801': 'Waldorf Factory Jan.2008', 
#    'blofeld_fact_200802': 'Waldorf Factory Feb.2008', 
#    'blofeld_fact_201200': 'Waldorf Factory 2012', 
#    }

ord2chr = {
    0: u' ', 
    1: u' ', 
    2: u' ', 
    3: u' ', 
    4: u' ', 
    5: u' ', 
    6: u' ', 
    7: u' ', 
    8: u' ', 
    9: u' ', 
    10: u' ', 
    11: u' ', 
    12: u' ', 
    13: u' ', 
    14: u' ', 
    15: u' ', 
    16: u' ', 
    17: u' ', 
    18: u' ', 
    19: u' ', 
    20: u' ', 
    21: u' ', 
    22: u' ', 
    23: u' ', 
    24: u' ', 
    25: u' ', 
    26: u' ', 
    27: u' ', 
    28: u' ', 
    29: u' ', 
    30: u' ', 
    31: u' ', 
    32: u' ', 
    33: u'!', 
    34: u'"', 
    35: u'#', 
    36: u'$', 
    37: u'%', 
    38: u'&', 
    39: u"'", 
    40: u'(', 
    41: u')', 
    42: u'*', 
    43: u'+', 
    44: u',', 
    45: u'-', 
    46: u'.', 
    47: u'/', 
    48: u'0', 
    49: u'1', 
    50: u'2', 
    51: u'3', 
    52: u'4', 
    53: u'5', 
    54: u'6', 
    55: u'7', 
    56: u'8', 
    57: u'9', 
    58: u':', 
    59: u';', 
    60: u'<', 
    61: u'=', 
    62: u'>', 
    63: u'?', 
    64: u'@', 
    65: u'A', 
    66: u'B', 
    67: u'C', 
    68: u'D', 
    69: u'E', 
    70: u'F', 
    71: u'G', 
    72: u'H', 
    73: u'I', 
    74: u'J', 
    75: u'K', 
    76: u'L', 
    77: u'M', 
    78: u'N', 
    79: u'O', 
    80: u'P', 
    81: u'Q', 
    82: u'R', 
    83: u'S', 
    84: u'T', 
    85: u'U', 
    86: u'V', 
    87: u'W', 
    88: u'X', 
    89: u'Y', 
    90: u'Z', 
    91: u'[', 
    92: u'\\', 
    93: u']', 
    94: u'^', 
    95: u'_', 
    96: u'`', 
    97: u'a', 
    98: u'b', 
    99: u'c', 
    100: u'd', 
    101: u'e', 
    102: u'f', 
    103: u'g', 
    104: u'h', 
    105: u'i', 
    106: u'j', 
    107: u'k', 
    108: u'l', 
    109: u'm', 
    110: u'n', 
    111: u'o', 
    112: u'p', 
    113: u'q', 
    114: u'r', 
    115: u's', 
    116: u't', 
    117: u'u', 
    118: u'v', 
    119: u'w', 
    120: u'x', 
    121: u'y', 
    122: u'z', 
    123: u'{', 
    124: u'|', 
    125: u'}', 
    126: u'~', 
    127: u'°', 
    }

chr2ord = {
    u' ': 32,
    u'!': 33,
    u'"': 34,
    u'#': 35,
    u'$': 36,
    u'%': 37,
    u'&': 38,
    u"'": 39,
    u'(': 40,
    u')': 41,
    u'*': 42,
    u'+': 43,
    u',': 44,
    u'-': 45,
    u'.': 46,
    u'/': 47,
    u'0': 48,
    u'1': 49,
    u'2': 50,
    u'3': 51,
    u'4': 52,
    u'5': 53,
    u'6': 54,
    u'7': 55,
    u'8': 56,
    u'9': 57,
    u':': 58,
    u';': 59,
    u'<': 60,
    u'=': 61,
    u'>': 62,
    u'?': 63,
    u'@': 64,
    u'A': 65,
    u'B': 66,
    u'C': 67,
    u'D': 68,
    u'E': 69,
    u'F': 70,
    u'G': 71,
    u'H': 72,
    u'I': 73,
    u'J': 74,
    u'K': 75,
    u'L': 76,
    u'M': 77,
    u'N': 78,
    u'O': 79,
    u'P': 80,
    u'Q': 81,
    u'R': 82,
    u'S': 83,
    u'T': 84,
    u'U': 85,
    u'V': 86,
    u'W': 87,
    u'X': 88,
    u'Y': 89,
    u'Z': 90,
    u'[': 91,
    u'\\': 92,
    u']': 93,
    u'^': 94,
    u'_': 95,
    u'`': 96,
    u'a': 97,
    u'b': 98,
    u'c': 99,
    u'd': 100,
    u'e': 101,
    u'f': 102,
    u'g': 103,
    u'h': 104,
    u'i': 105,
    u'j': 106,
    u'k': 107,
    u'l': 108,
    u'm': 109,
    u'n': 110,
    u'o': 111,
    u'p': 112,
    u'q': 113,
    u'r': 114,
    u's': 115,
    u't': 116,
    u'u': 117,
    u'v': 118,
    u'w': 119,
    u'x': 120,
    u'y': 121,
    u'z': 122,
    u'{': 123,
    u'|': 124,
    u'}': 125,
    u'~': 126,
    u'°': 127, 
    }


class TemplateClass(object):
    def __init__(self, fullName, dbName, params, groupDelta=None):
        self.fullName = fullName
        self.dbName = dbName
        self.params = params
        self.groupDelta = groupDelta
        self.single = True if groupDelta is not None else False

SingleOsc = TemplateClass('Oscillator', 'singleOsc', range(1, 17), 16)
GroupOsc = TemplateClass('Oscillators', 'osc', range(1, 52))
SingleFilter = TemplateClass('Filter', 'singleFilter', range(77, 96), 20)
GroupFilter = TemplateClass('Filters', 'filters', range(77, 118))
SingleEffect = TemplateClass('Effect', 'singleEffect', range(128, 144), 16)
GroupEffect = TemplateClass('Effects', 'effects', range(128, 160))
SingleLFO = TemplateClass('LFO', 'singleLfo', range(160, 171), 12)
GroupLFO = TemplateClass('LFOs', 'lfo', range(160, 195))
SingleEnvelope = TemplateClass('Envelope', 'singleEnv', range(196, 206), 12)
GroupEnvelope = TemplateClass('Envelopes', 'env', range(196, 242))
Arpeggiator = TemplateClass('Arpeggiator', 'arpeggiator', range(311, 359))

templates = (
    (SingleOsc, GroupOsc), 
    (SingleFilter, GroupFilter), 
    (SingleEffect, GroupEffect), 
    (SingleLFO, GroupLFO), 
    (SingleEnvelope, GroupEnvelope), 
    (Arpeggiator, None), 
    )

templateGroupDict = {
    'osc1Frame': (GroupOsc, SingleOsc, 0), 
    'osc2Frame': (GroupOsc, SingleOsc, 1), 
    'osc3Frame': (GroupOsc, SingleOsc, 2), 
    'lfo1Frame': (GroupLFO, SingleLFO, 0), 
    'lfo2Frame': (GroupLFO, SingleLFO, 1), 
    'lfo3Frame': (GroupLFO, SingleLFO, 2), 
    'filtersFrame': (GroupFilter, None, None), 
    'filter1Frame': (GroupFilter, SingleFilter, 0), 
    'filter2Frame': (GroupFilter, SingleFilter, 1), 
    'efx1Frame': (GroupEffect, SingleEffect, 0), 
    'efx2Frame': (GroupEffect, SingleEffect, 1),
    'arpeggiatorFrame': (Arpeggiator, None, None), 
    'filterEnvelopeFrame': (GroupEnvelope, SingleEnvelope, 0), 
    'amplifierEnvelopeFrame': (GroupEnvelope, SingleEnvelope, 1), 
    'envelope3Frame': (GroupEnvelope, SingleEnvelope, 2), 
    'envelope4Frame': (GroupEnvelope, SingleEnvelope, 3), 
    }
