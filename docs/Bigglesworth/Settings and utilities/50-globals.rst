Blofeld device query
======================

.. role:: blofeldshift
.. role:: blofeldkey

Blofeld synthesizers can send and receive their Global settings (normally available by
pressing :blofeldshift:`Shift` and :blofeldkey:`Global` together) through MIDI.

To use this feature, your Blofeld has to be connected to both input and output MIDI,
which means that USB is mandatory for Desktop devices, but standard MIDI cable 
connections are equally fine for Keyboards.

Since most of the available settings are self-explanatory, the following documentation
only refers to specific topics that require further information.

Device ID to query
^^^^^^^^^^^^^^^^^^^

When querying a Blofeld, Bigglesworth defaults to the Broadcast ID number (0x7F, or 
127). This is usually fine for most users, but also means that *any* Blofeld connected
to your computer will accept and reply to this request. If you happen to own more than
a Blofeld synthesizer, access its Global menu (see above) and it will appear on the
fourth page.

See also `Device ID`_.

General settings
^^^^^^^^^^^^^^^^^

While the "Volume" setting is provided and editable, it is known to be unreliable 
sometimes.

The "Free button" setting applies to Blofeld Keyboards only, since the Desktop version
does not have such a button.

System settings
^^^^^^^^^^^^^^^^

The "Contrast" setting will be applied after switching the Blofeld off and on again.

Whenever a parameter that does not currently appear on display is changed, a small "popup"
appears, showing the new value for a few seconds before disappearing.
"Popup Time" allows you to set how many seconds that popup will be visible.

MIDI settings
^^^^^^^^^^^^^

MIDI channel
..............

This setting only applies to Control Change and Note events.
Bigglesworth only uses SysEx events to change sound parameters, so this will only affect
the Modulation wheel (that actually is *not* a sound parameter, at least for the Blofeld), 
and the virtual keyboard used in the Sound Editor.

Program send
.............

When Bigglesworth is also connected to your Blofeld MIDI output, it is important that 
this parameter is enabled; if it is not and you switch to another sound on your Blofeld,
Bigglesworth will not know about it.

Ctrl send
..........

When Bigglesworth is also connected to your Blofeld MIDI output, it is important that 
this parameter is set to "Ctrl+SysEx", otherwise Bigglesworth will not know if you 
change any parameters on your Blofeld, leading to inconsistency between the stored 
sound parameters and those values on your synthesizer.

Notes about other MIDI settings
................................

The "Ctrl receive" settings does not seem to actually change anything.

While the four "Control" settings deserve an important note about their values on 
the Blofeld manual (see page 85), this is not an issue for Bigglesworth, since 
it only uses SysEx messages to send parameter changes.


.. _`Device ID`: ../terminology.html#deviceid

.. meta::
    :icon: blofeld-b
    :keyword: GlobalsDialog
