Import/Export the current sound
===============================

Usually, you might want to import or export sounds to or from the library 
(possibly to/from a collection), but sometimes it can be useful to open 
or export a sound "on the fly".

To import a sound and edit it without importing it to your library, select 
"Import sound..." from the "File" menu of the Editor, and refer to the 
`Import sounds`_ section of the Library, and ensure that you select 
*a single sound* from the imported file.

To export the sound currently edited, select "Export current sound..." from
the "File" menu of the Editor.

A dialog will show, allowing you to change the sound name, category, target 
index and device ID.

It is possible to select an index that differs from the original one, and 
it is also possible to choose one of the 16 Multi Sound Edit Buffer as a 
target; please note that the latter is rarely necessary, use it only if 
you really know what you are doing, as "dumping" to the Multi Sound Edit 
Buffer **will not** save it to your Blofeld.

The device ID section refers to your Blofeld `Device ID`_, which can 
be sometime useful if you have set it to an ID different than 0. If you 
don't know what this means, just leave it to its default value.

Now just click the "Save" button, select the format and output file, 
and you are done!

.. _`Import sounds`: ../Librarian/files.html#import
.. _`Device ID`: ../terminology.html#deviceid

.. meta::
    :icon: document-save
