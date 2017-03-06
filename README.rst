Bigglesworth
============

.. image:: https://cloud.githubusercontent.com/assets/523596/23536074/e2759486-ffc2-11e6-9350-7b3eb916c389.jpg
   :target: https://cloud.githubusercontent.com/assets/523596/23536073/e25f7e08-ffc2-11e6-9af5-dfd48cd2e906.jpg
   :alt: Screenshot

Bigglesworth is a GNU/Linux editor and librarian for the Waldorf Blofeld 
synthesizer.

This is an early version, some of the features are not available yet.

Features
--------

Features in *italics* are still under development

- Direct sound parameter editing
- Virtual keyboard (with input from the computer keyboard)
- Dumping sounds from Blofeld
- *Dumping sounds to Blofeld (not yet)*
- *Organizing sounds and adding/restoring them from factory presets (not yet)*

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

A small window will show, listing the latest version of the presets from
Waldorf, from here you can edit a sound by right clicking on it.

Bigglesworth will try to automatically connect to a Blofeld if it's connected 
through USB, if not you'll have to connect it manually, using Patchage or
QJackCtl, for example.

Remember that sound dumping (receiving sounds from the Blofeld) works only if 
you own a Blofeld Keyboard or by connecting it via USB, since the Desktop 
version doesn't have a MIDI out port.

What works
~~~~~~~~~~

- Sound dumping (single, bank or full).
- Sound parameters send/receive for the current sound in *"Sound Mode Edit
  Buffer"*, not for Multi Mode.
- Virtual keyboard from the Editor window.
- Global parameters send/receive (requires USB connection the Desktop version,
  since both input and output MIDI is required)
- MIDI connections (through menu and dialog), remember connections

What doesn't work (yet)
~~~~~~~~~~~~~~~~~~~~~~~

- Multi Mode editing
- Everything related to sound saving (rename, saving current sound parameters, 
  ordering)

Future
~~~~~~

Apart from completing what is in the *What doesn't work* section above
and fixing the whole Editor window, I'll add:

- Factory/User library, even with custom libraries (older versions, etc.)
- MIDI input and mapping, to allow the use of an external control surface, also
  using a "live mode": a simple MIDI interface for the control surface, without
  the need to load presets or the whole editor window
- direct sysex file loading and saving
- sound template "favorites" library
- arpeggiator template library
- WaveTable management (and editing?); but I'm afraid I'll need the sampling 
  license for that...
- Online shared sound presets
- coffee maker

Known issues
------------

Since I'm still in the middle of the development, a lot of (unexpected)
things still happen... Anyway.

- some scaled dials don't look very good
- the base font family might not be installed on your system, I'm still 
  looking for the best font for the interface, then I'll include in the
  repository 
- the whole Editor window layout is temporary and resizing is allowed. This
  means that the controls can look ugly and in unexpected places
- the Librarian doesn't know the current sound if you don't manually change it 
  from the Blofeld, this means that if you manually send a sound dump from the 
  Blofeld, it will not know what to do with it.
  If you want to edit a sound coming from the Blofeld, you have to select it by
  changing at least 2 sounds from it (I suppose it's a firmware bug).

