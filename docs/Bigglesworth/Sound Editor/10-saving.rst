Saving
======

.. role:: subsection

- `Autosave <autosave_>`__

By default, editing a sound just results in sending the changed parameters 
to your Blofeld (assuming Bigglesworth is connected to it and `Control output`_
is enabled).

Even if a sound has been opene from the library or a new sound was created or
*INITed*, it has to be saved to the library to ensure that that sound will not 
be lost forever.

To achieve that, just click on the small disk icon on the right of the MIDI 
panel. If the sound has been opened from the Library, it will automatically 
be saved, if not (or it was opened from a Factory Preset), a small dialog 
will appear, asking for the collection you want to save the sound in and 
its bank/program index.

You can also choose to save an opened sound to another slot, just keep the 
left mouse button pressed on the save button and then select "Save as..." 
from the popup menu that will appear.

Selecting "Main library" as target location will allow you to save it 
without actually adding it to a collection, which can be useful for "work 
in progress" sounds.

If you select a specific collection, and the selected bank/program slot is 
already used by another sound, you can choose to "Create new" (keeping that 
sound in the library, but actually removing it from the selected collection) 
or "Overwrite" it, which will result in overwriting that sound also for all 
collections that share it.

.. _autosave:

:subsection:`Autosave`
^^^^^^^^^^^^^^^^^^^^^^^

If you are an advanced user, you could choose to enable the "Autosave" mode.
This will automatically save *every* parameter change to a sound, including 
its name or category. This setting is also automatically remembered once 
enabled or disabled. You can change this behavior in the `settings`_


.. _`Control output`: midi.html#ctrlout
.. _`settings`: ../Settings%20and%20utilities/main.html#autosave

.. meta::
    :icon: document-save
