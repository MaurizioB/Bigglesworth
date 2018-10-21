Dumping
=======

.. role:: subsection

- `What does dump mean? <what_>`__
- `Sound memory dump <dump_>`__

.. _what:

:subsection:`What does dump mean?`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In the world of MIDI, *dumping* generally refers to the transfer of data that 
does not directly relate to the playback or its parameters.

A dump can contain some of (or all) the contents of the system memory, which 
can be useful to do a backup when dumping *from* a MIDI device to a storing 
device, or to update the device itself.

Usually there are two types of dumps, when talking about MIDI instruments: 
firmware and memory.

A firmware dump is less common but very important, as it allows to fix issues 
and add new features, and most devices only support receiving them.

Your Blofeld can receive these updates, and Waldorf has made them available for 
free since it was released. Read more about this (and how to update your Blofeld 
if you need or want to) on `Firmware updates`_.

The Blofeld also supports a "Global dump", that contains global settings like
display contrast, MIDI configuration and so on. Read more on 
`Global parameters`_.

.. _dump:

:subsection:`Sound memory dump`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Memory dumps usually contain all sound parameters, sent all at once, 
opposed to the normal one-parameter-at-a-time operation.

Bigglesworth can use this feature to communicate with your Blofeld, 
receive all its sounds or even make it store whole new banks in its
memory.

It is very important to understand and remember the difference between
the two dump directions:

- "*Dump from*" means that you are transferring data **from** your Blofeld 
  to Bigglesworth
- "*Dump to*" is the process of sending data from Bigglesworth **to** your Blofeld

Read more about this in `Receive sounds`_ and `Send sounds`_.


.. _`Global parameters`: globals.html
.. _`Firmware updates`: firmware.html
.. _`Receive sounds`: dumpreceive.html
.. _`Send sounds`: dumpsend.html
