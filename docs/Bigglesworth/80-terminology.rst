Reference terminology
=====================

.. role:: subsection

- `Control Change <ctrlchange_>`__
- `Device ID <deviceid_>`__
- `Note Event <noteevent_>`__
- `Program Change <progchange_>`__
- `SysEx <sysEx_>`__


.. _ctrlchange:

:subsection:`Control Change (CC)`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Control Change, sometimes abbreviated CtrlChange or CC, are the most common type of MIDI 
message besides `Note events <noteEvent_>`__.

The most common and known CC's are the Sustain Pedal and the Mod Wheel. A CC message contains
an identifier (ranging 0-127) that tells what kind of control is going to be changed, and the
relative value (again 0-127).

Some CC identifiers are considered standards (like the aforementioned Mod and Sustain, set as 1 
and 64 respectively). Other are less used and sometimes manufacturers decide to use a CC id for
other purposes than commonly used because the original purpose is not appliable and there is
no standard id for what that control achieves.

CC identifiers for the Blofeld can be found at page 113 in the User Manual, or by mean of the
"Midi implementation chart" item in the "?" menu of Bigglesworth.

.. _deviceid:

:subsection:`Device ID`
^^^^^^^^^^^^^^^^^^^^^^^

The Device ID is a special number that can be used to identify a specific device whenever
users have more identical devices connected in their setup, and is used when sending or 
receiving SysEx messages (which are not subject to channel numbers).
Suppose you have 2 Blofelds, the first has Device ID set to 0, and the second one to 10.
If a SysEx with Device ID 0 is sent, only the former will use it, while the 
latter will just ignore it.

This allows the controller (Bigglesworth, in our case) to specifically target that 
device when sending SysEx messages, and receive only messages sent from it while
ignoring others.

Bigglesworth can be set to send and receive a single Device ID, which can also be
"Broadcast" (0x7F, or 127). In Broadcast mode, every connected Blofeld will accept
SysEx events, and Bigglesworth will accept events disregarding their Device ID.


.. _noteevent:

:subsection:`MIDI Note`
^^^^^^^^^^^^^^^^^^^^^^^

The most basic MIDI message type, can be a `Note On` or a `Note Off` event, indicating the press and 
release of a key on the keyboard, and as with most MIDI messages has 2 values ranging from 0 to 127:
the first one indicates the pitch (with 60 usually as the "middle-C" of a standard piano keyboard)
and the second one the "velocity", the "volume" at which the note will be played.

.. _progchange:

:subsection:`Program Change`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Program Changes are MIDI Events used to tell a MIDI instrument to change "its sound", following
specific presets and/or values. For synthesizers, this usually recalls from its memory a full set
of sound parameters, while for keyboards or samplers it defines the type of sounds that will be
used (a piano, a string section, a drumset, etc).


.. _sysex:

:subsection:`System Exclusive (SysEx)`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

SysEx messages are more complex MIDI messages, and they do not have a specific length or format, 
except for their beginning and final value. They are used to send specific parameters and values 
to a MIDI device whenever the 0-127 range is not enough for the identifier or its parameters; 
this is the case of the Blofeld, that uses more than 300 parameters and some of them use non 
linear values.

These messages are sometimes used to send "bulk" messages, such as memory/sound dumps or firmware 
updates.

SysEx messages usually start with a manufacturer number, a model number and, possibly, a 
`Device ID <deviceid_>`__. In the case of Blofeld synthesizers, the first is 0x3E (integer
62), the second is 0x13 (integer 19), while the Device ID defaults to 0 and can be changed 
from the Blofeld's Global menu or Bigglesworth's "`Blofeld Device`_" utility.

.. meta::
    :icon: help-about

.. _`Blofeld Device`: "Settings and utilities/globals.html"
