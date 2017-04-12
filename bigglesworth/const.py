#!/usr/bin/env python2.7
# *-* coding: utf-8 *-*

import pickle
from os import path
from collections import namedtuple
from PyQt4 import QtCore

def local_path(name):
    return path.join(path.dirname(path.abspath(__file__)), name)

#with open('blofeld_params', 'rb') as _params_file:
#    sound_params = pickle.load(_params_file)

MAJ_VERSION = 0
MIN_VERSION = 9
REV_VERSION = 1
VERSION = '{}.{}.{}'.format(MAJ_VERSION, MIN_VERSION, REV_VERSION)

MIDFILE, SYXFILE = 1, 2

QWIDGETSIZE_MAX = ((1 << 24) - 1)
INPUT, OUTPUT = 0, 1
LEGATO = 0
RANDOM = 0
RANGE, VALUE, NAME, SHORTNAME, FAMILY, VARNAME = range(6)
SRC_LIBRARY, SRC_BLOFELD, SRC_EXTERNAL = range(3)
EMPTY, STORED, DUMPED, MOVED, EDITED = [0, 1, 3, 4, 8]

PGMRECEIVE, MIDIRECEIVE, PGMSEND, MIDISEND = range(4)
MOVEUP, MOVEDOWN, MOVELEFT, MOVERIGHT, MOVE = range(5)

DUMP_ALL = -1
SMEB = 0x7f, 0x00
MIEB = True

MoveCursor, UpCursor, DownCursor, LeftCursor, RightCursor = range(5)
cursor_list = []
status_dict = {
               EMPTY: 'Empty', 
               STORED: 'Stored', 
               DUMPED: 'Dumped', 
               EDITED: 'Edited', 
               MOVED: 'Moved', 
               }

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

CURSOR_NORMAL, CURSOR_INSERT = range(2)


class InvalidException(Exception):
    def __init__(self, params=None):
        self.params = params

    def __str__(self):
        return repr(self.params)


class AdvParam(object):
    def __init__(self, fmt, **kwargs):
        self.fmt = fmt
        self.indexes = {}
        self.addr = {}
        self.order = []
#        self.forbidden = 0
        self.allowed = 0
        for i, l in enumerate(reversed(fmt)):
            if l == '0':
#                self.forbidden |= 1<<i
                continue
            self.allowed |= 1<<i
            if l in self.indexes:
                self.indexes[l] |= (self.indexes[l]<<1)
            else:
                self.indexes[l] = 1 << i
                self.addr[l] = i
                self.order.append(l)
        self.kwargs = {}
        self.named_kwargs = []
        for attr in self.order:
            setattr(self, kwargs[attr][0], kwargs[attr][1])
            self.kwargs[attr] = kwargs[attr][1]
            self.named_kwargs.append(kwargs[attr][0])
#        print self.kwargs, self.named_kwargs
        self.order.reverse()

    def get_indexes(self, data):
#        if data&self.forbidden:
#            raise IndexError
        data = data & self.allowed
        res = []
        for k in self.order:
            res.append((data&self.indexes[k])>>self.addr[k])
        return res

    def normalized(self, *values):
        res = 0
        for k, v in enumerate(values):
            res += v<<self.addr[self.order[k]]
        return res

    def get(self, data):
#        if data&self.forbidden:
#            raise IndexError
        data = data & self.allowed
        res = []
        for k in self.order:
            try:
                res.append(self.kwargs[k][(data&self.indexes[k])>>self.addr[k]])
            except:
                res.append(self.kwargs[k][0])
        return res

    def __getitem__(self, data):
        try:
            return self.get(data)
        except Exception as e:
            print e
            print 'Parameters malformed (format: {}): {} ({:08b})'.format(self.fmt, data, data)

arp_step_types = [
                  'normal', 
                  'pause', 
                  'previous', 
                  'first', 
                  'last', 
                  'first+last', 
                  'chord', 
                  'random', 
                  ]

arp_step_accents = [
                    'silent', 
                    '/4', 
                    '/3', 
                    '/2', 
                    '*1', 
                    '*2', 
                    '*3', 
                    '*4', 
                    ]

arp_step_timings = [
                    'random', 
                    '-3', 
                    '-2', 
                    '-1', 
                    '+0', 
                    '+1', 
                    '+2', 
                    '+3', 
                    ]

arp_step_lengths = [
                    'legato', 
                    '-3', 
                    '-2', 
                    '-1', 
                    '+0', 
                    '+1', 
                    '+2', 
                    '+3', 
                    ]

efx_short_names = {
               'Lowpass': 'LP', 
               'Highpass': 'HP', 
               'Diffusion': 'Diff.', 
               'Damping': 'Damp', 
               }

class ParamsClass(object):
    param_values_nt = namedtuple('param_values_nt', 'range values name short_name family attr')
    param_names_nt = namedtuple('param_names_nt', 'range values name short_name family attr id')
    with open(local_path('blofeld_params'), 'rb') as bp:
        param_list = []
        param_names = {}
        for i, (r, v, n, s, f, a) in enumerate(pickle.load(bp)):
            if i == 58:
                v = AdvParam('0uuu000a', u=('Unisono', ['off', 'dual', '3', '4', '5', '6']), a=('Allocation', ['Poly','Mono']))
            elif i in [196, 208, 220, 232]:
                v = AdvParam('0ttmmmmm', t=('Trigger', ['normal', 'single']), m=('Mode', ['ADSR', 'ADS1DS2R', 'One Shot', 'Loop S1S2', 'Loop All']))
            elif i in list(range(327, 343)):
                v = AdvParam('0sssgaaa', s=('Step', arp_step_types), g=('Glide', ['off', 'on']), a=('Accent', arp_step_accents))
            elif i in list(range(343, 359)):
                v = AdvParam('0lll0ttt', l=('Length', arp_step_lengths), t=('Timing', arp_step_timings))
            param_list.append(param_values_nt(r, v, n, s, f, a))
            if a is None: continue
            param_names[a] = param_names_nt(r, v, n, s, f, a, i)

    def attr_from_index(self, index):
        return self.param_list[index].attr

    def iter_attr(self):
        for p in self.param_list:
            yield p.attr

    def index_from_attr(self, par_attr):
        try:
            return self.param_names[par_attr].id
        except:
            raise KeyError('Index: Parameter {} unknown!'.format(par_attr))

    def param_from_attr(self, par_attr):
        try:
            return self.param_names[par_attr]
        except:
            raise KeyError('Param: Parameter {} unknown!'.format(par_attr))

    def __getattr__(self, par_attr):
        try:
            return self.param_names[par_attr]
        except:
            raise KeyError('Parameter {} does not exist!'.format(par_attr))

    def __getitem__(self, index):
        try:
            return self.param_list[index]
        except:
            raise IndexError('Parameter at index {} does not exist!'.format(index))

Params = ParamsClass()

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

INDEX, BANK, PROG, NAME, CATEGORY, STATUS, SOUND = range(7)
sound_headers = ['Index', 'Bank', 'Id', 'Name', 'Category', 'Status']

categories = [
              'Init', 
              'Arp', 
              'Atmo', 
              'Bass', 
              'Drum', 
              'FX', 
              'Keys', 
              'Lead', 
              'Mono', 
              'Pad', 
              'Perc', 
              'Poly', 
              'Seq', 
              ]

UserRole = QtCore.Qt.UserRole
IndexRole = UserRole + 1
BankRole = IndexRole + 1
ProgRole = BankRole + 1
SoundRole = ProgRole + 1
CatRole = SoundRole + 1
EditedRole = CatRole + 1
PortRole = EditedRole + 1
ClientRole = PortRole + 1

roles_dict = {
              INDEX: IndexRole, 
              BANK: BankRole, 
              PROG: ProgRole, 
              CATEGORY: CatRole, 
              }

note_scancodes = [
                  52, 39, 53, 40, 54, 55, 42, 56, 43, 57, 44, 58,
                  59, 46, 60, 47, 61, 24, 11, 25, 12, 26, 13, 27, 
                  28, 15, 29, 16, 30, 31, 18, 32, 19, 33, 20, 34, 
                  35, 
                  ]

note_keys = [
             'Z', 'S', 'X', 'D', 'C', 'V', 'G', 'B', 'H', 'N', 'J', 'M', 
             ',', 'L', '.', 'Ò', '-', 'Q', '2', 'W', '3', 'E', '4', 'R', 
             'T', '6', 'Y', '7', 'U', 'I', '9', 'O', '0', 'P', '\'', 'È', 
             '+', 
             ]

note_keys = [QtCore.QString().fromUtf8(key) for key in note_keys]

init_sound_data = [0, 0, 
                   1, 64, 64, 64, 66, 96, 0, 0, 2, 127, 1, 64, 0, 0, 0, 0, 0, 64, 64, 64, 66, 
                   96, 0, 0, 0, 127, 3, 64, 0, 0, 0, 0, 0, 52, 64, 64, 66, 96, 0, 0, 0, 127, 
                   5, 64, 0, 0, 0, 0, 0, 0, 2, 64, 0, 0, 0, 0, 0, 20, 0, 0, 0, 127, 0, 127, 
                   0, 127, 0, 0, 0, 64, 0, 0, 0, 0, 1, 0, 0, 1, 127, 64, 0, 0, 0, 0, 0, 0, 
                   64, 64, 64, 1, 64, 0, 0, 64, 1, 64, 0, 0, 127, 64, 0, 0, 0, 0, 0, 0, 64, 
                   64, 64, 0, 64, 0, 0, 64, 3, 64, 0, 0, 3, 0, 0, 127, 114, 5, 64, 0, 0, 0, 
                   1, 0, 20, 64, 64, 0, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 8, 
                   0, 53, 64, 100, 0, 64, 100, 0, 100, 110, 0, 15, 64, 127, 127, 0, 50, 64, 
                   0, 0, 0, 0, 64, 0, 0, 64, 0, 0, 40, 64, 0, 0, 0, 0, 64, 0, 0, 64, 0, 0, 
                   30, 64, 0, 0, 0, 0, 64, 0, 0, 64, 1, 0, 64, 0, 0, 127, 50, 0, 0, 127, 0, 
                   0, 0, 0, 64, 0, 0, 127, 52, 127, 0, 127, 0, 0, 0, 0, 64, 0, 0, 64, 64, 64, 
                   64, 64, 64, 0, 0, 0, 64, 0, 0, 64, 64, 64, 64, 64, 64, 0, 0, 1, 0, 0, 0, 
                   64, 0, 0, 0, 64, 0, 0, 0, 64, 0, 0, 0, 64, 1, 1, 64, 0, 0, 64, 0, 0, 64, 
                   0, 0, 64, 0, 0, 64, 0, 0, 64, 0, 0, 64, 0, 0, 64, 0, 0, 64, 0, 0, 64, 0, 
                   0, 64, 0, 0, 64, 0, 0, 64, 0, 0, 64, 0, 0, 64, 0, 0, 64, 16, 100, 0, 0, 
                   15, 8, 5, 0, 0, 0, 1, 12, 0, 0, 15, 0, 0, 55, 4, 4, 4, 4, 4, 4, 4, 4, 4, 
                   4, 4, 4, 4, 4, 4, 4, 68, 68, 68, 68, 68, 68, 68, 68, 68, 68, 68, 68, 68, 
                   68, 68, 68, 68, 0, 0, 0, 73, 110, 105, 116, 32, 32, 32, 32, 32, 32, 32, 
                   32, 32, 32, 32, 32, 0, 0, 0, 0]



