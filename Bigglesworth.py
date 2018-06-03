#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

import sys, os
#sys.path.append(os.path.join(os.path.dirname(__file__), 'bigglesworth/editorWidgets'))
sys.path.append('./bigglesworth/editorWidgets')
#print(sys.path)

import argparse

def process_args():
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-s', '--sysex', help='Print output SysEx messages to the terminal', action='store_true')
    if 'linux' in sys.platform:
        parser.add_argument('--rtmidi', help='(not recommended)', action='store_true')
    else:
        parser.add_argument('--rtmidi', help=argparse.SUPPRESS, default=True)
#    parser.add_argument('-l', '--library-limit', metavar='N', type=int, help=argparse.SUPPRESS)
#    parser.add_argument('-w', '--wavetable', metavar='WTFILE', nargs='?', const=True, help='Open Wavetable editor (with optional WTFILE)')
    parser.add_argument('--log', help='Show log dialog on startup', action='store_true')
    parser.add_argument('-L', '--librarian', metavar='COLLECTION', nargs='?', const=True, help='Show the librarian, selecting the optional COLLECTION')
    parser.add_argument('-E', '--editor', nargs=argparse.REMAINDER, 
        help='Show the Sound Editor, with optional arguments [[COLLECTION] BXXX]\nIf no argument is given, the editor will show the INIT sound.\n' \
            'If no COLLECTION is given, the sound will be opened from the internal "Blofeld" collection.\nThe index tries to open ' \
            'the sound XXX from bank B, eg. A001.')
    res, unknown = parser.parse_known_args()
    if unknown:
        print('Unknown parameters ignored:')
        for p in unknown:
            print(p)
    return res

parser = process_args()
if parser.rtmidi:
    os.environ['MIDI_BACKEND'] = 'RTMIDI'
    if 'linux' in sys.platform:
        print('Requested RtMidi on command line. RtMidi on Linux is not recommended!')
else:
    os.environ['MIDI_BACKEND'] = 'ALSA'

import bigglesworth

if __name__ == '__main__':
    app = bigglesworth.Bigglesworth(parser, sys.argv)
    sys.exit(app.exec_())
