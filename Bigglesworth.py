#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

import sys, os
#sys.path.append(os.path.join(os.path.dirname(__file__), 'bigglesworth/editorWidgets'))
sys.path.append('./bigglesworth/editorWidgets')
#print(sys.path)

import argparse

#import logging
#import rollbar
#from rollbar.logger import RollbarHandler
#
#rollbar.init('1c253504c48a4f3ca05321f19c3850a7', 'devel')

#logger = logging.getLogger(__name__)
#logger.setLevel(logging.DEBUG)
## report ERROR and above to Rollbar
#rollbar_handler = RollbarHandler()
#rollbar_handler.setLevel(logging.INFO)
## attach the handlers to the root logger
#logger.addHandler(rollbar_handler)

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
    parser.add_argument('-d', '--database', metavar='DBPATH', action='store', help='Set database path (only for debugging!)')
    parser.add_argument('-L', '--librarian', metavar='COLLECTION', nargs='?', const=False, help='Show the librarian, selecting the optional COLLECTION')
    parser.add_argument('-W', '--wavetables', help='Show Wavetable editor', action='store_true')
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
    try:
        app = bigglesworth.Bigglesworth(parser, sys.argv)
#    except:
#        rollbar.report_exc_info()
    finally:
        sys.exit(app.exec_())
