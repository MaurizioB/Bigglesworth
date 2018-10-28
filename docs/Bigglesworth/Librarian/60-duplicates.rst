Duplicate sounds
================

.. role:: subsection

- `Find duplicate sounds in the whole library <library_>`__
- `Find duplicates of a single sound <single_>`__

Bigglesworth is able to find duplicate sounds in your collections.

Keep in mind, anyway, that Blofeld synthesizers use more than 300 parameters, 
and it's not possible to find "similar" sounds, even if they just differ by
a single parameter and by a single step.

For example, if you have two identical sounds and, at some point, you just change
the OSC1 octave parameter from 8' to 16', those sounds will not be considered
as possible duplicates anymore.

That said, sounds with identical parameters can be found even if their *name* or
*category* is different.

.. _library:

:subsection:`Find duplicate sounds in the whole library`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This function searches the whole database for any sound that is found more than 
once. Note that sounds *shared* amongst more than one collections are *not* 
considered duplicate.

Right click on a collection tab and select "Find duplicates", or, alternatively,
select the same item from the "Library" menu.

Select the scope of your search from the "Find duplicates in" drop down.

If you select the "Main Library" it will search within the whole library, 
including "orphaned" sounds (sounds that are not used in any collection).

If you select a specific collections, it will look for duplicates in 
that collection only. This is useful when you have identical sounds you 
might have saved more than once and didn't remember about them.

If "Ignore names" is checked, the search will just compare parameter values,
the same works for "Ignore categories".

In "Main Library" search mode it is possible to ignore the 3 Factory Presets,
in case you are not interested in duplicates matching those sounds.

Once you press "Start" the search will begin, and could take some time, 
depending on the search options, your collections count and their size.

Results are listed in a tree structure. For each duplicate sound found,
the top item is the first occurrency found in the database (usually 
corresponding to the sound that was added for the first time), followed
by its index and its collection, in the format **INDEX** @ **COLLECTION**.
Underneath that, every child items lists the collection for which at
least a duplicate was found, and every sub-child item lists those 
duplicates, preceded by its index.

Each sound item can be double clicked, and Bigglesworth will automatically
show it in the Library, opening the collection that sound belongs to if 
it is not open yet.

.. _single:

:subsection:`Find duplicates of a single sound`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you are just interested in finding possible duplicates of a specific 
sound, right click on it and select "Find duplicates...".

From here, similarly to the whole library search mode, you can choose
to look for duplicate of that specific sound within the whole library 
or a single collection only.

Again, you can also choose to ignore names or categories.

If duplicate sounds are found, they will be listed in a table. Each 
header shows the collection in which an occurrency has been found, and 
each table cell shows the index and the sound name; if a sound is shared 
between more than one collection, it will be shown in the same row.

As before, double clicking a sound will select it in the related 
collection.


.. meta::
    :icon: edit-duplicate
