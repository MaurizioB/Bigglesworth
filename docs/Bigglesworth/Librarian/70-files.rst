Import/Export sounds
====================

Sounds can be imported from standard MIDI (\*.mid) and SysEx (\*.syx) files.

This section of the manual only refers to importing and exporting sounds from 
collections. Import and export operations of sounds currently opened in the Editor
Window is explained in `this page`_.


.. role:: subsection

- `Import sounds <import_>`__
- `Export sounds <export_>`__

.. _import:

:subsection:`Import sounds`
^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you have got a patch, sound, or what is sometimes called a "Sound set" in 
*Waldorf's jargon*, such as those sold in their website, you can import them to 
Bigglesworth.

To import sounds into Bigglesworth, just select the "Import file..." in the "Files"
menu of the Librarian, and select your file.

If the file is recognized as valid, a dialog window will show its contents. From 
this window you can select all sounds you are interested into (clicking on each 
sound will show its details on the right side).

At this point you can choose between these options:

- **Edit**: this option is available only if you select a single sound, and will open
  it in the editor window; the sound will **not** be saved until you manually do
  so.
- **Import to collection**: if you select the "Main library", the sound will just be 
  imported, but will *not* be saved to any collection; if you select an existing 
  collection, Bigglesworth will automatically try to add all selected sounds to the 
  selected collection, based on the original sound index and the empty slots 
  of that collection. You can also try and select "Use original index", which 
  will ignore the (possible) unempty slots of the selected collection, overwriting
  them if the relative option is selected.
- **Create new collection**: create a brand new collection, containing all the 
  selected sounds.

.. _export:

:subsection:`Export sounds`
^^^^^^^^^^^^^^^^^^^^^^^^^^^

You can also export single sounds or entire collections, for backup purposes or 
to share them with somebody else.

**NOTE**: sharing sounds that are part of a purchased sound set is **illegal** in 
some countries, and is considered unethical anyway. Please, don't do that: 
whoever created those sounds has put lots of efforts in doing that, and if he
or she decided that his or her efforts had to be payed, you should respect 
that choice. I strongly discourage you from doing it.

To export sounds from a collection, right click on its tab bar, and select 
"Export sounds.." from the "Export" menu. This will automatically create a 
new group of sounds from the current collection.

Alternatively, you can select "Export sounds..." from the "File" menu of 
the Library window. In this case, the sound list will be empty, and you will
have to manually add sounds you want to export.

Bigglesworth will try to automatically index the selected sounds, but you
can also use the "Manual index" option. In this case, click the "Sorting 
tools" button, select one of the sorting options and press the apply 
button to let it sort according to the selected sorting method.

Once you are done, just click "Export and close" to complete the process, 
select the format and file you want to save your sounds to and press "Save".

The two possible format are "MIDI file" and "SysEx file". There is not 
much difference between for this purpose, and you might choose any of 
them as well. The only advantage of MIDI files over SysEx is that the 
former type can be opened in a sequencer or a daw and be "played" to 
the output device. At this moment, most of the programs that can open 
MIDI files also are able to do the same for SysEx files.

If you have multiple export operations to be done, use the "Export" 
button, which will not close the export dialog once the save process 
has been completed.

.. _`this page`: ../Sound%20Editor/files.html

.. meta::
    :icon: document-save
