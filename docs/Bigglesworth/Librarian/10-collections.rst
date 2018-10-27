Collections
===========

.. role:: subsection

Bigglesworth uses collections to organize sounds stored in its database.

- `What are collections? <what_>`__
- `Sounds shared amongst collections <shared_>`__
- `Create a new collection <new_>`__
- `Manage existing collections <manage_>`__
- `Index, sort and filter <sort_>`__
- `Organize sounds <organize_>`__
- `Edit name or categories <rename_>`__

.. _what:

:subsection:`What are collections?`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A collection is a group of sounds, indexed as they are on the Blofeld (from A001 to A128, B001, etc.), and
each one of them can contain up to 1024 sounds. There is no limit to the number of collections one can have.
If you are familiar with the Multi mode of the Blofeld, imagine them as an extended version of it.

Besides the 3 Waldorf presets (which cannot be deleted nor modified), the only other default and not deletable
collection is the "Blofeld" one. It can be used to "mirror" the contents of your Blofeld and keep track of what
sounds you have on it.

To open a collection, right click on one of the top tab bars, and select it from the "Open collection" menu.
Alternatively, use the same sub-menu from the "Library" menu of the Librarian window.


.. _shared:

:subsection:`Sounds shared amongst collections`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

An important thing to understand about collections is that a sound can exist in multiple collections
at once. Editing a shared sound means that any modification applied and saved to that particular 
sound will reflect in the collections that contain it.
When a shared sound is opened in the Sound editor, the top display will show the collection from
which it was opened and will also list other collections containing it.

.. _new:

:subsection:`Create a new collection`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To create a new collection click on the "+" button on the main tab bar of the Librarian 
(or use the Library menu) and select "Create new collection".

Alternatively, if the Library sidebar is opened, just click the "+" icon near the 
"User collections" folder.

While usually you would create a new, empty collection, it is also possible to clone
an existing one. The cloned collection will contain and share *exactly* the same sounds 
of the source (except when cloning one of the Factory presets), as explained in the
previous section.

When creating a new empty collection, it is also possible to "INIT" its sounds.
If you select this option, the selected *INITed* banks will not be empty slots, but
new INIT sounds. One would not use this feature normally, but it can be useful if 
you want to "blank" your Blofeld banks.

A collection *must* have a name, and names have to be unique. I suggest to avoid
similar names to avoid confusion; you can also select an icon, so that it can be 
easily recognized from anywhere in the program.


.. _manage:

:subsection:`Manage existing collections`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

From the "Manage collections" in the Library menu you can access the collection
manager dialog.

From there you can create new collections, change icons of the existing ones, 
rename them or completely delete them.

Note that, while the Blofeld collection is listed, it cannot be modified. Also, 
factory presets are not listed.

For technical reasons, deleting or renaming an existing collection requires
Bigglesworth to be restarted. Ensure that you don't have unsaved work before 
performing such an action.

.. _sort:

:subsection:`Sort and filter`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Collections can contain from 0 to 1024 sounds, organized in the same way the Blofeld does, with 8 banks
from A to H, each one containing sounds from 001 to 128. You are not restricted by the indexes, for example
it is possible to have a sound at index A023, another at index B110, the C bank full, and the other banks
completely empty. By default, all slots from A001 to H128 are visible even if they are not used, and you 
can use the "Empty slots" checkbox to show only slots that actually store a sound in the collection.

On top of every collection there is a panel that can be used to filter sounds by Bank from A to H, by sound 
category, and by name or by tag_. Filters are cumulative, meaning that selecting Bank D and Category "Bass" will 
shorten the list whenever you type something in the "Name" or "Tags" fields.

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

.. _rename:

:subsection:`Edit names or categories`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To edit a sound name or category, press the small pencil button at the bottom of the vertical scroll 
bar, then double click its name or click on the category field to edit it.

Remember that Blofeld names cannot be longer than 16 characters, and you can only use spaces, 
letters from ``A`` to ``Z`` (both lower and upper case), numbers, and the following symbols: 
``!"#$%&\'()*+,-./:;<=>?@[\\]^_\`{|}~°``.

Special letters, including accents and other symbols will
be automatically translated to their simplified version, so "``À``" will become "``A``", and "``ç``" will
become "``c``".

**NOTE**: since Bigglesworth can share the same sound between more collections, if a sound is also 
used in another collection, the editing of its name or category will reflect on other collections as well.


.. _tag: tags.html
.. _Main Library: main-library.html

.. meta::
    :icon: document-open
