Terminology reference
=====================

.. role:: subsection

- `Control Change <ctrlchange_>`__
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

CC identifiers for the BLofeld can be found at page 113 in the User Manual, or by mean of the
"Midi implementation chart" item in the "?" menu of Bigglesworth.


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


.. meta::
    :icon: help-about
