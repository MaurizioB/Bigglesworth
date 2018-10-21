Tags
====

.. role:: subsection

- `Why tags? <what_>`__
- `Create and manage tags <manage_>`__
- `Edit sounds tags <apply_>`__

.. _what:

:subsection:`Why tags?`
^^^^^^^^^^^^^^^^^^^^^^^

While Blofeld's Categories can be useful, they can be a limitation.

Tags have no such limits, as you can assign more than one to each sound, so that you can have a
sound tagged as "Strings", "Pad" and "Dark".

In addition to this, tags can be colored using both background and foreground (text) colors,
to better identify them in your collections.

Remember that tags are a feature specific to Bigglesworth, you will never see them in your Blofeld
and will be ignored when exporting to a `SysEx`_ file.

.. _manage:

:subsection:`Create and manage tags`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Tags can be managed from |tagIcon| "Edit tags" in "Library" menu of the Librarian.

From this dialog, you can create, rename or delete any tag, and it is also possible to set its
background and foreground color.

|Note| Suggestion: try to avoid very long tags, they could become invisible if multiple tags
are applied to a sound; also, do not use very similar names, or select different colors to better 
identify them.

.. _apply:

:subsection:`Edit sounds tags`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Tags can be applied to a sound or a selected group of sounds by right clicking on them and selecting
the submenu "|tagIcon| Tags".

The submenu will show the existing tags, if any; if the selected sounds already have some tags applied,
they will appear as checked. If multiple sounds have unmatching tags, those tags will appear as "partially"
checked. After checking or unchecking the tags you want, press "Apply". Note that all selected sounds will
be updated accordingly, and _all_ tags set (or unset) will be applied to them, so if you have some sounds
with tags that have not been selected, those tags will be removed for those sounds also.

By clicking on "|editIcon| Edit tags..." a  dialog window will appear, showing the current tags for the 
selected sounds (if any) and a list of all available tags. They can be added by selecting them from the 
list or by typing the tag name in the tag field. The keyboard allows to add and remove existing tags 
using Backspace or Delete. As per the menu mode explained above, all sounds will be updated with the
new selected tags.

The dialog also allows to edit tags (and add new ones) from the "Manage tags" button.


.. |Note| image:: :/icons/Bigglesworth/16x16/edit-find

.. |tagIcon| image:: :/icons/Bigglesworth/16x16/tag

.. |editIcon| image:: :/icons/Bigglesworth/16x16/document-edit

.. _`SysEx`: ../terminology.html#sysex

.. meta::
    :icon: tag
