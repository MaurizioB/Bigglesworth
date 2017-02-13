#!/usr/bin/env python2.7
# *-* coding: utf-8 *-*

from collections import namedtuple
import pickle

sound_params_nt = namedtuple('data', 'range value name')
global_params_nt = namedtuple('data', 'range value name')
with open('blofeld_params_nt', 'rb') as _params_file:
    params_list = pickle.load(_params_file)
with open('blofeld_globals_nt', 'rb') as _globals_file:
    globals_list = pickle.load(_globals_file)

with open('blofeld_sysex_v1_04.txt', 'rb') as _bsx:
    ref_raw = _bsx.readlines()

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
        self.order.reverse()
        self.kwargs = kwargs
            

    def get(self, data):
        if data&self.forbidden:
            raise IndexError
        res = []
        for k in self.order:
            res.append(self.kwargs[k][(data&self.indexes[k])>>self.addr[k]])
        return res

    def __getitem__(self, data):
        try:
            return self.get(data)
        except:
            print 'Parameters malformed (format: {}): {} ({:08b})'.format(self.fmt, data, data)

idx = {}
done = False
doing = False
data = []
sect = None
efx = {0: {}, 1: {}}
efx_names = []
efx_ref = {}
for n, l in enumerate(ref_raw):
    if l.startswith('*******'):
        if not doing:
            sect_title = ref_raw[n-1].split()
            sect = sect_title[0]
            sect_name = ' '.join(sect_title[1:]).replace(' Effect Parameters',  '')
            doing = True
            continue
        else:
            doing = False
            idx[sect] = data
            sect = None
            data = []
            
    elif len(l) and ' ' in l and l[0].isdigit() and sect is not None:
        if l.startswith(sect):
            continue
        if sect.startswith('4'):
            if sect == '4.6':
                data.extend([l.rstrip('\r\n')[16:] for i in range(2)])
            elif sect in ['4.10', '4.12']:
                continue
            else:
                data.append(l.rstrip('\r\n')[16:])
        elif sect.startswith('5'):
            if sect == '5.1':
                fx_line = l.rstrip('\r\n')[16:]
                pos = fx_line.index('  FX')
                fx = fx_line[:pos].rstrip()
                if ',' in fx:
                    fx = fx[:fx.index(',')]
                avail = fx_line[pos:].split()
                data.append((fx, avail))
                efx_names.append(fx)
            else:
                l = l.rstrip('\r\n')
                id = map(int, l[:10].rstrip().split())
                r = l[10:18].rstrip()
                values = l[18:42].rstrip()
                name = l[42:]
                for e, i in enumerate(id):
                    if len(id) == 1: e = 1
                    if efx_names.index(sect_name) not in efx[e]:
                        efx[e][efx_names.index(sect_name)] = {i: name}
                    else:
                        efx[e][efx_names.index(sect_name)][i] = name
                    if values == '0..127':
                        efx_ref[name] = tuple([str(x) for x in range(128)])
                    elif values.startswith('Clipping'):
                        efx_ref[name] = tuple(idx['4.11'][:-1])
                    elif values == 'positive,negative':
                        efx_ref[name] = 'positive', 'negative'
                    elif values.startswith('1/96'):
                        efx_ref[name] = idx['4.13'][:30]
                    elif values == '-64..+63':
                        efx_ref[name] = tuple(['{s}{n}'.format(n=n, s='+' if n>0 else '') for n in range(-64, 64)])


#idx['4.10'] = AdvParam('0uuu000a', u=['off', 'dual', '3', '4', '5', '6'], a=['Poly','Mono'])
#idx['4.12'] = AdvParam('0ttmmmmm', t=['normal', 'single'], m=['ADSR', 'ADS1DS2R', 'One Shot', 'Loop S1S2', 'Loop All'])

RANGE, VALUE, NAME, SHORTNAME, FAMILY, VARNAME = range(6)
params = []
params_names = {}

r = 1/9.
full_range = tuple([str(x) for x in range(128)])
oct_range = ('128\'', '64\'', '32\'', '16\'', '8\'', '4\'', '2\'', '1\'', '1/2\'')
semit_range = tuple(['{s}{n}'.format(n=n, s='+' if n>0 else '') for n in range(-12, 13)])
detune_range = tuple(['{s}{n}'.format(n=n, s='+' if n>0 else '') for n in range(-64, 64)])
bend_range = tuple(['{s}{n}'.format(n=n, s='+' if n>0 else '') for n in range(-24, 25)])
keytrack_range = tuple(['{s}{n}%'.format(n=n+1 if n>0 else n, s='+' if n>-2 else '') for n in (int(-200+round(i*(3+r))) for i in range(128))])
balance_range = tuple('F1 {}'.format(x) for x in range(64, 0, -1)) + ('middle', ) + tuple('F2 {}'.format(x) for x in range(1, 64))
pan_range = tuple('left {}'.format(x) for x in range(64, 0, -1)) + ('center', ) + tuple('right {}'.format(x) for x in range(1, 64))
filter_routing = ('parallel', 'serial')
off_on = ('off', 'on')
on_off = ('on', 'off')
phase_range = ('free', ) + tuple('{}°'.format(int(round(i*(3-.2)))) for i in range(127))
arp_mode = ('off', 'on', 'One Shot', 'Hold')
arp_pattern = ('off', 'User') + tuple(range(1, 16))
arp_length = ('1/96', '1/48', '1/32', '1/16T', '1/32.', '1/16', '1/8T', '1/16.', '1/8', '1/4T', '1/8.', '1/4', '1/2T', '1/4.', '1/2', '1/1T', '1/2.', '1 bar', '1.5 bars', '2 bars', '2.5 bars', '3 bars', '3.5 bars') +\
            tuple('{} bars'.format(b) for b in range(4, 10)+range(10, 20, 2)+range(20, 40, 4)+range(40, 65, 8)) + ('legato', )
arp_octave = tuple([str(x) for x in range(1, 11)])
arp_dir = ('Up', 'Down', 'Alt Up', 'Alt Down')
arp_ptn_len = range(1, 17)
arp_tempo = tuple([str(x) for x in range(40,90,2)+range(90,165)+range(165,301,5)])
char_range = tuple(str(unichr(l)) for l in range(32,128))
effect_polarity = ('positive', 'negative')

range_ref = {
             '128\'..1/2\'': oct_range, 
             '-12..+12': semit_range, 
             '-64..+63': detune_range, 
             '-24..+24': bend_range, 
             '-200%..+196%': keytrack_range, 
             '0..127': full_range, 
             'on,off': on_off, 
             'off,on': off_on, 
             'F1 64..F2 63': balance_range, 
             'left 64..right 63': pan_range, 
             'parallel,serial': filter_routing, 
             'free..355 degree': phase_range, 
             'off,on,One Shot,Hold': arp_mode, 
             'off..15': arp_pattern, 
             '1/96..legato': arp_length, 
             '1..10': arp_octave, 
             'Up,Down,Alt Up,Alt Down': arp_dir, 
             '1..16': arp_ptn_len, 
             '40..300': arp_tempo, 
             'ASCII': char_range, 
             'positive,negative': effect_polarity, 
             }

nc = 0
def get_short_names(name, fam=2):
    splitted = name.split()
    if len(splitted) == 2:
#        return ' '.join(splitted[1]), ' '.join(splitted[0])
        return splitted[1], splitted[0]
    return ' '.join(splitted[fam:]), ' '.join(splitted[:fam])

for i, p in enumerate(params_list):
    full_range = p.range
    if full_range == 'reserved':
        params.append(('reserved', None, None, None, None, None))
        continue
    if '..' in full_range:
        full_range = map(int, full_range.split('..')) + [1]
    else:
        full_range = None
    if p.name == 'Name Char':
        name = 'Name Char {:02}'.format(nc)
        nc += 1
    elif p.name.find(',') > 0:
        name = p.name[0:p.name.index(',')]
        full_range[2] = 12
    else:
        name = p.name
    if name.startswith('Osc ') or name.startswith('Glide ') or name.startswith('Mixer Noise') or\
        name.startswith('Mixer RingMod') or name.startswith('Filter ') or name.startswith('Effect ') or\
        name.startswith('LFO ') or name.startswith('Amplifier ') or name.startswith('Envelope ') or\
        name.startswith('Modifier '):
        short_name, family = get_short_names(name)
    elif name.startswith('Mixer Osc'):
        short_name, family = get_short_names(name, 3)
    else:
        short_name = name
        family = ''
    if p.value.startswith('see '):
        ref = p.value.split()[1]
        if ref.startswith('4'):
            if ref not in ['4.10', '4.12']:
                values = idx[ref]
            else:
                pass
#                print name
        if ref.startswith('5'):
            if name=='Effect 1 Type':
                values = [eff for eff, avail in idx['5.1'] if 'FX1' in avail]
            elif name=='Effect 2 Type':
                values = [eff for eff, avail in idx['5.1'] if 'FX2' in avail]
            elif name in ['Effect 1 Mix', 'Effect 2 Mix']:
                values = range_ref[p.value]
            else:
                pass
#                if i in efx_ref:
#                    if efx_ref[i] in range_ref:
#                        values = range_ref[efx_ref[i]]
#                    elif efx_ref[i].startswith('Clipping'):
#                        values = idx['4.11'][:-1]
#                    elif efx_ref[i].startswith('1/96'):
#                        values = idx['4.13'][:30]
#                    else:
#                        continue
#                    print efx_ref[i]
    elif p.value in range_ref:
        values = range_ref[p.value]
    params.append([tuple(full_range), values, name, short_name, family, name.replace(' ', '_').replace('/', '_')])
#    params.append({NAME: name, RANGE: tuple(full_range), VALUE: values, VARNAME: name.replace(' ', '_').replace('/', '_')})

#print params[121]

with open('blofeld_params', 'wb') as of:
    pickle.dump(params, of)
with open('blofeld_efx', 'wb') as of:
    pickle.dump(efx, of)
with open('blofeld_efx_ranges', 'wb') as of:
    pickle.dump(efx_ref, of)











