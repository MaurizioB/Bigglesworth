Send sounds
===========

Bigglesworth can send sounds to your Blofeld in various ways, depending on your needs.

.. role:: subsection

- `Full collection dump <full_>`__
- `Single sound dump <single_>`__

.. _full:

:subsection:`Full collection dump`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you want to send all sounds in a collection to your Blofeld, a full dump is required.
Open the collection you want to send (probably the "Blofeld" collection), right click on 
its tab bar and select "Dump sounds TO Blofeld" from the "Dump" sub menu.

A dialog will open, listing the contents of your collection on your right. From there you 
can check or uncheck sound slots that will be marked for the dump list.

The "Banks" section allows you to easily select or deselect all banks you want to 
send, without the need to manually checking or unchecking them.

In some cases Bigglesworth could be too "fast" sending sound data, resulting in an 
incomplete dump, with some sounds not actually saved to your Blofeld.
If this happens, you can try to increase the "Delay between sends" value. The default
value is 100ms (a little less than 10 requests per second), increasing to 150 or 200
should be enough. If you still encounter problems, there might be some problem
with your hardware or MIDI setup.

While increasing the delay will obviously make the whole process take much more time 
(the computed estimate time appears at the bottom of the dialog), it is a safer 
approach in some cases.


.. _single:

