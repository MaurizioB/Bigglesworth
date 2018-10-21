MIDI
====

Send and receive options
^^^^^^^^^^^^^^^^^^^^^^^^

Device ID
.........

.. role:: blofeldshift
.. role:: blofeldkey

In the rare (and lucky) case you own more than one Blofeld, the Device ID allows you to 
identify it between your other MIDI devices.
The default setting ("Broadcast") should be fine enough for most users, but you can
customize its value according to the one appearing on the "Globals" panel on your Blofeld;
you can access it by pressing :blofeldshift:`Shift` and :blofeldkey:`Global` together.
This is valid for `SysEx`_ events only.

Receive channel
...............

This selects which MIDI channels Bigglesworth will react to when receiving MIDI messages
such as Control Change, Program Change or Note events. This setting has no effect on
received SysEx messages. The default and suggested value is "OMNI", which means that
any event received will be processed, despite of its MIDI channel.

Send channel
............

This selects which MIDI channels Bigglesworth will send events to. As per the Receive 
channel setting, this only refers to Control Change, Program Change and Note events.
If you have set your Blofeld on a specific channel (instead of "omni"), you have to
specify it here accordingly. The default and suggested value is channel 1, even when
Blofeld is set to "omni".

**NOTE**: Use multiple channels only when you know what you are doing: remember that 
setting more than one channel on Bigglesworth (including "OMNI") will cause it to send 
a distinct MIDI message for **every** channel set, which might confuse your Blofeld.

Detect global parameters
........................

If your Blofeld is connected to both MIDI Input and Output (the default when using USB), 
you can try and press this button to automatically set the aforementioned parameters.

MIDI connections
^^^^^^^^^^^^^^^^^

Bigglesworth requires *at least* a MIDI output connection to work with your Blofeld,
but a 2 way communication is preferred, as it allows to keep your sound collections
updated, and provides better feedback when editing a sound from both Bigglesworth and
the Blofeld.

USB connected Blofelds are automatically connected if they have been detected as such.

Obviously, it is possible to connect to any MIDI device, depending on your needs.

Every MIDI event received by Bigglesworth is automatically forwarded to any
device connected to its output. The only exception is when events are received
*from* a device that is believed to be a Blofeld: in this case, Bigglesworth assumes
that the event has been received from the same device it would send it to, and 
to avoid unnecessary "feedback", it will not send it back.

To manually chaneg this behavior, read more in the "Input" section below.

If you own a MIDI controller which is already mapped to your Blofeld, it can be
useful to connect to it too: Bigglesworth will react to it and will forward all
MIDI events to your Blofeld, obviously assuming it is connected to Bigglesworth.

Input
.....

.. role:: graybold

This panel shows all available and usable MIDI ports Bigglesworth can connect to for
receiving MIDI events. Just click on the small checkbox to connect or disconnect to
a midi port.

If your Blofeld is connected through USB it is usually automatically recognized, and 
will show a small :graybold:`b` besides it. This will disable any event forwarding
from that port (as explained before). If you think that the detection is in error, 
use the context menu on the port to manually select "This is NOT my Blofeld".

On the contrary, if you own a Blofeld Keyboard and have it connected using MIDI 
cables, you might want to manually apply this setting using the relative option.

Output
......

Nothing particular to say about this, except that you should never select ports
that are not Blofeld synthesizers, unless you really know what you are doing.
If you are using USB and your Blofeld was not detected, test the other ports 
as you wish, but once you have found the right one, it is always better to 
disconnect the other.

Automatic connection
^^^^^^^^^^^^^^^^^^^^

As mentioned before, Bigglesworth is usually able to detect an USB connected Blofeld,
but if you want to disable this option for any reason, you can.

Bigglesworth is also able to remember the MIDI devices you connected it to. If you 
think that its connections are behaving in a strange way, try disabling this option 
and press the "Clear saved connections" button.

MIDI backend (Linux only)
^^^^^^^^^^^^^^^^^^^^^^^^^

On Linux the default backend is ALSA, which has better performance and control than 
the RtMIDI backend used on other systems. While using RtMIDI is possible, it is 
highly recommended to use ALSA instead, unless absolutely required.



.. _`SysEx`: ../terminology.html#sysex

.. meta::
    :icon: midi
