Collections
===========

.. role:: subsection

Bigglesworth uses collections to organize sounds stored in its database.

- `What are collections? <what_>`__
- `Sort and filter <sort_>`__
- `Organize sounds <organize_>`__

.. _what:

:subsection:`What are collections?`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A collection is a group of sounds, indexed as they are on the Blofeld (from A001 to A128, B001, etc.), and
each one of them can contain up to 1024 sounds. There is no limit to the number of collections one can have.

Besides the 3 Waldorf presets (which cannot be deleted nor modified), the only other default and not deletable
collection is the "Blofeld" one. It can be used to "mirror" the contents of your Blofeld and keep track of what
sounds you have on it.

To open a collection, right click on one of the top tab bars, and select it from the "Open collection" menu.
Alternatively, use the same sub-menu from the "Library" menu of the Librarian window.

.. _sort:

:subsection:`Sort and filter`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
On top of every collection there is a panel that can be used to sort sounds by Bank from A to H, by sound 
category, by name or by tag_. By default, all slots from A001 to H128 are visible even if they are empty,
you can use the "Empty slots" checkbox to show only slots that actually store a sound.

Sounds are usually sorted by their index, but clicking on any of the table headers can change the sorting
order. Remember that sorting and filtering will not change the actual index-order of those sounds, it is only used to
facilitate the search of a specific sound. To restore the original sort index, click on "Index" in the top
left corner of the table.

.. _organize:

:subsection:`Organize sounds (moving, adding, removing)`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Sounds in a collection can be organized by dragging and dropping them with the mouse. To select more than
one sound, keep SHIFT pressed while clicking on the sounds you are interested into.

To move sounds into another position amongst other sounds, drag them *between* the items identifying the 
target slot.

To switch places of two or more sounds with another, drag *onto* the desired destination position.

Keeping SHIFT pressed *while dropping* sounds will enable "duplicate" mode, meaning that the selected 
sounds will be "cloned". Editing the original sound does not affect its duplicate.

To add a sound from another collection (or the main library), just drag them whenever you want them.
Sounds dropped from one of the factory presets will be automatically duplicated. To overwrite an occupied
slot, keep CTRL pressed while dropping. The previous sound will still exist in the Main Library.

To create a new sound in an empty slot, right click on it and select "INIT this slot".

To delete a sound from a collection, select the "Remove from (...)" item from its right click menu.
Sounds deleted from a collection still exist on the `Main Library`_.

To edit a sound name or category, press the small pencil button at the bottom of the vertical scroll 
bar, then double click its name or click on the category to edit it.


.. _tag: tags.html
.. _Main Library: main-library.html
