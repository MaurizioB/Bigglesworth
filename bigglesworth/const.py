import pickle
from os import path
from collections import namedtuple
from PyQt4 import QtCore

def local_path(name):
    return path.join(path.dirname(path.abspath(__file__)), name)

#with open('blofeld_params', 'rb') as _params_file:
#    sound_params = pickle.load(_params_file)

RANGE, VALUE, NAME, SHORTNAME, FAMILY, VARNAME = range(6)
SRC_LIBRARY, SRC_BLOFELD = 0, 1
EMPTY, STORED, DUMPED, MOVED, EDITED = [0, 1, 3, 4, 8]
status_dict = {
          EMPTY: 'Empty', 
          STORED: 'Stored', 
          DUMPED: 'Dumped', 
          EDITED: 'Edited', 
          MOVED: 'Moved', 
          }


SNDR = 0
SNDD = 0x10
SNDP = 0x20
GLBR = 0x4
GLBD = 0x14

class AdvParam(object):
    def __init__(self, fmt, **kwargs):
        self.fmt = fmt
        self.indexes = {}
        self.addr = {}
        self.order = []
        self.forbidden = 0
        for i, l in enumerate(reversed(fmt)):
            if l == '0':
                self.forbidden |= 1<<i
                continue
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
        if data&self.forbidden:
            raise IndexError
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
        if data&self.forbidden:
            raise IndexError
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
            param_list.append(param_values_nt(r, v, n, s, f, a))
            param_names[a] = param_names_nt(r, v, n, s, f, a, i)

    def index_from_attr(self, par_attr):
        try:
            return self.param_names[par_attr].id
        except:
            raise KeyError('Parameter {} unknown!'.format(par_attr))

    def __getattr__(self, par_attr):
        try:
            return self.param_names[par_attr]
        except:
            raise KeyError('Parameter {} does not exist!'.format(par_attr))

    def __getitem__(self, id):
        try:
            return self.param_list[id]
        except:
            raise IndexError('Parameter at index {} does not exist!'.format(id))

Params = ParamsClass()

#sound_params[58][VALUE] = AdvParam('0uuu000a', u=['off', 'dual', '3', '4', '5', '6'], a=['Poly','Mono'])
#for i in [196, 208, 220, 232]:
#    sound_params[i][VALUE] = AdvParam('0ttmmmmm', t=['normal', 'single'], m=['ADSR', 'ADS1DS2R', 'One Shot', 'Loop S1S2', 'Loop All'])
#params_index = {s[VARNAME]:i for i, s in enumerate(sound_params) if len(s) and s[VARNAME] is not None}

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




