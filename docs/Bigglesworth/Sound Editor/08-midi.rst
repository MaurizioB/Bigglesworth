MIDI panel
===========

On the right side of the display there is a small MIDI panel that shows the
current MIDI connections. For both input and output, the connection count is 
displayed. 

An optimal configuration will show "(1)" for both; remember that MIDI output is
required for the editor to work, but a MIDI input connection will also allow you 
to keep parameters updated if you change those paramters on your Blofeld.

Both input and output have LED-like indicators for Program and Control changes.

.. _progin:

`Program change input`
^^^^^^^^^^^^^^^^^^^^^^

When Program is enabled for inputs, received `program changes`_ will change 
the current selected program. This will work only if you opened a sound from 
a collection.

.. _ctrlin:

`Control change input`
^^^^^^^^^^^^^^^^^^^^^^

When Control is enabled for inputs, every parameter change (`control change`_)
received will be applied.

.. _progout:

`Program change output`
^^^^^^^^^^^^^^^^^^^^^^^

When Program is enabled for outputs and you change the bank or program in the 
display (or open a sound from a collection), Bigglesworth will send that program 
change to your Blofeld.

.. _ctrlout:

`Control change output`
^^^^^^^^^^^^^^^^^^^^^^^

When Control is enabled for outputs, any parameter change will be sent to 
your Blofeld. This is the default setting.

Both input and output controls have a context (right click) menu that allows 
to set Program and Control send/receive modes, and select the MIDI devices 
Bigglesworth is connected to.

.. _`program changes`: ../terminology.html#progchange
.. _`control change`: ../terminology.html#ctrlchange

.. meta::
    :icon: midi
