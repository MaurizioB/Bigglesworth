Bigglesworth
============

Bigglesworth is a Waldorf Blofeld editor and librarian for GNU/Linux.
This is an early version, most of the features are not available yet.

Features
--------

-  Direct sound parameter editing
-  Dumping sounds from Blofeld
-  Dumping sounds to Blofeld (not yet)
-  Organizing sounds and adding/restoring them from factory presets (not
   yet)

Requirements
------------

-  Python 2.7
-  PyQt4 >= 4.11.1
-  pyalsa

Usage
-----

There is not an installation procedure yet, just run the script in the
main directory:

::

    $ ./Bigglesworth

If it doesn't work, just browse to the bigglesworth directory and run:

::

    $ python __init__.py

A small window will show, listing the latest version of the presets from
Waldorf, from here you can edit a sound by right clicking on it.

| Bigglesworth will try to automatically connect to a Blofeld if it's
connected through USB, if not you'll have to connect it manually, using
Patchage or QJackCtl, for example.
| Remember that sound dumping (receiving sounds from the Blofeld) works
only if you own a Blofeld Keyboard or by connecting it via USB, since
the Desktop version doesn't have a MIDI out port.

What works
~~~~~~~~~~

-  Sound dumping (single, bank or full)
-  Sound parameters sending for the current sound in "Sound Mode Edit
   Buffer", not for Multi Mode.

What doesn't work
~~~~~~~~~~~~~~~~~

-  Arpeggiator and Modulation matrix, since they're not there yet :)
-  Everything related to sound saving (rename, saving current sound
   parameters, ordering)

Future
~~~~~~

Apart from completing what is in the *What doesn't work* section above
and fixing the whole Editor window, I'll add: - MIDI configuration
panel, with auto-connect features - Factory/User library, even with
different custom libraries (older versions, etc.) - MIDI input with mini
keyboard and mapping, to allow the use of an external control surface,
also using a "live mode": a simple MIDI interface for the control
surface, without the need to load presets or the whole editor window -
direct sysex file loading and saving - sound template "favorites"
library - arpeggiator template library - WaveTable management (and
editing?); but I'm afraid I'll need the sampling license for that... -
coffee maker

Known issues
------------

Since I'm still in the middle of the development, a lot of (unexpected)
things still happen. Anyway. - some scaled dials don't look very good -
the whole Editor window layout is temporary and resizing is allowed.
This means that the controls can be ugly and in unexpected places - the
Librarian doesn't know the current sound if you don't manually change it
from the Blofeld, this means that if you manually send a sound dump from
the Blofeld, it will not know what to do with it. If you want to edit a
sound coming from the Blofeld, you have to select it by changing at
least 2 sounds from it (I suppose it's a bug).
