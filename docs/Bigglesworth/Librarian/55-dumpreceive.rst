Receive sounds
==============

Bigglesworth can receive sounds from your Blofeld in various ways, depending on your needs.

.. role:: subsection

- `Full collection dump <full_>`__
- `Single sound dump <single_>`__
- `Dump detection <detect_>`__

.. _full:


:subsection:`Full collection dump`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you want to get all your sounds you have in your Blofeld, a full dump is required.
Open the collection you want to fill in with those sounds (probably the "Blofeld" 
collection), right click on its tab bar and select "Dump sounds FROM Blofeld" from the
"Dump" sub menu.

Bidirectional MIDI communication is required for this mode to work: if you own a
Blofeld Desktop you will need to use the USB connection.

A dialog will open, listing the (possibly empty) contents of your collection on your
right. From there you can check or uncheck sound slots that will be marked for the
dump list. Don't worry if you checked a sound by mistake, it is possible to unselect
it before committing changes once the dump process is completed.

The "Banks" section allows you to easily select or deselect all banks you want to 
write into, without the need to manually checking or unchecking them.

If all banks are selected, you can use the "Fast dump" mode, which will tell your
Blofeld to send the whole sound bank automatically (otherwise Bigglesworth will 
request them one by one). As this operation is automatic, it cannot be interrupted
for any reason, and you will have to wait for the whole process to complete before
being able to use Bigglesworth or your Blofeld again.

In "Fast dump" mode, the complete sound bank dump requires about 3 minutes and a half.

By default "Overwrite existing sounds" is not selected, and all existing sounds in that
collection will be still available in the Main Library (and any other collection they
are used). If you want to overwrite them, check the "Overwrite" option, but be aware
that overwritten sounds will not be available anymore.

Once a dump receive process is completed, you can still review the list of received 
sounds, allowing you, for example, to unselect sounds previously selected by mistake.
The "Direct database import" skips this passage, automatically importing all
received sounds to the selected collection.

As explained before, when "Fast dump" mode is not active, Bigglesworth progressively 
requests each sound to your Blofeld. In some cases these requests might occur too 
often and it could result in an incomplete dump, missing some sound or entire banks.
If this happens, you can try to increase the "Delay between requests" value. The default
value is 100ms (a little less than 10 requests per second), increasing to 150 or 200
should be enough. If you still encounter problems, there might be some problem
with your hardware or MIDI setup.

While increasing the delay will obviously make the whole process take much more time 
(the computed estimate time appears at the bottom of the dialog), it is a safer 
approach in some cases.

Once all options are set, just press that big "DUMP!" button and wait for the 
dump to complete. Remember to not switch off your Blofeld, nor disconnect its USB or
MIDI connections.

As soon as the dump is finished, you can review the list of received sounds; if
everything is in place, click "Import sounds"... Et voilà!

.. _single:

:subsection:`Single sound dump`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Bidirectional MIDI communication is required for this feature: if you own a
Blofeld Desktop you will need to use the USB connection.

Sounds can be dumped singularly to any collection. Right click on a slot, open 
its "Dump" submenu and look at the "Receive" section.

- **Dump from Sound Edit Buffer**: dump the current (possible edited) sound currently
  active on your Blofeld to the selected slot.
- **Dump from <INDEX>** (where <INDEX> is the index of the currently selected slot, such
  as A032 or F110): dump the sound stored in the Blofeld in the selected 
  Bank/Program index.
- **Dump from Multi Edit Buffer**: if you are in Multi Mode on you Blofeld, dump the 
  current data of the sound at the selected Multi Mode slot.
- **Show dump receive dialog...**: shows the dialog `explained above <full_>`__

Similar items are available in the Sound Editor "Dump" menu.

In that case, the contents of the dump will not be stored in the library, but will
be applied to the Sound Editor itself, and the sound will have to be manually
saved.


.. _detect:

:subsection:`Dump detection`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Bigglesworth is able to automatically detect a sound dump manually activated from
a Blofeld.
Whenever a dump is received a special dialog will open, and will wait some seconds 
for possible further data.
In this mode, Bigglesworth will list all received sounds, and, for each of them
it will try to detect possible existing duplicates and guess its bank/prog 
destination. Every sound parameter can be reviewed from the summary page on 
the right side of the dialog.

At this point, you can decide to create a completely new collection including 
the selected sounds, import them to an existing one (eventually overwriting 
existing slots), or, if only one sound is selected, edit it in the Sound Editor.

In this particular case only, the MIDI input alone is sufficient (as Bigglesworth 
does not need to actively communicate with your Blofeld).

.. meta::
    :icon: arrow-left-double
