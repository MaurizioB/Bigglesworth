#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), 'bigglesworth/editorWidgets'))

import argparse

def process_args():
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-s', '--sysex', help='Print output SysEx messages to the terminal', action='store_true')
    parser.add_argument('--rtmidi', help='Use rtmidi interface (mandatory and implicit for OSX/Windows, not recommended for Linux)', action='store_true')
#    parser.add_argument('-l', '--library-limit', metavar='N', type=int, help=argparse.SUPPRESS)
#    parser.add_argument('-w', '--wavetable', metavar='WTFILE', nargs='?', const=True, help='Open Wavetable editor (with optional WTFILE)')
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

#args = process_args()

import sys
import bigglesworth

if __name__ == '__main__':
    app = bigglesworth.Bigglesworth(process_args(), sys.argv)
    sys.exit(app.exec_())
