Main settings
=============

.. role:: subsection

Library
^^^^^^^^

Database path
...............

The database where all data about your collections, tags, templates, and wavetables is stored.
Normally you should not edit this, but in some cases it can be necessary. For example, when
trying to restore a previous database because the current one is corrupted, or when you 
have reinstalled your system and want to import the database from a previous installation.

Database backup
.................

The backup process automatically creates a copy of your backup, and is enabled by default.
It can be useful in case something goes wrong (the system crashes during a dump or you deleted
some sound or wavetable by mistake and it cannot be retrieved otherwise).
Bigglesworth has 2 backup stages: before starting a new backup process, the previous one 
is copied on a new file. In this way there is always at least a (hopefully) valid backup, 
even if the process fails or the program/system crashes in the meantime.

Bigglesworth creates a backup every 5 minutes by default, but you can disable this function 
if you want to. Also, on less modern computers, the process could require more system resources 
than you'd expect, it might be better to increase the backup interval. This is also suggested 
if you use an "old" SSD as your primary disk, as it takes a lot of write cycles in some
circumstances.

It has been reported that *sometimes* the backup process can cause an unexpected system crash
(but the user is unaware that the backup is the culprit). If you happen to see repeated 
crashes after some minutes you are using Bigglesworth, try to disable the backup completely.
If the problem doesn't occur anymore, please report this using the official 
`Bigglesworth website`_ contact form, or through a private message to the 
`Facebook page`_.

Startup options
.................

These are pretty self-explanatory. Usually you don't need to change anything here, but
are provided for further customization anyway, though.
On some systems it could also be useful to disable the "Restore window position", if
it happens that the Librarian is showed a bit "off" screen on startup.

Editor
^^^^^^

.. _autosave:

:subsection:`Autosave`
......................

The Autosave option is useful to automatically save a sounds while editing, but remember
that every editing translates in a writing on the database. As said before, if you own
an old computer or use an old SSD, it might be better to automatically disable this 
feature.

Other options
^^^^^^^^^^^^^

Send Program Change
....................

**NOTE**: This is an advanced and, sometimes, dangerous setting.

By activating this option, whenever you select a sound in any collection (besides 
the "Main library", and the Sound Editor window has not unsaved parameter values, 
a `Program change`_ event is send.

If Bigglesworth is connected to both input and output MIDI ports of your Blofeld, 
it should be smart enough to not send that change to your Blofeld, but if that 
is not the case and you changed some sound parameter *on* your Blofeld without 
having Bigglesworth to be acknowledged about that, the Blofeld will just change 
the sound (according to its sound bank) and those changes will be lost. Forever.

Activate this option only if you are really sure about how it works.

First-run wizard
.................

The first-run wizard is an assistant that is shown just the first time you started 
Bigglesworth, walking through the first configuration process after installation 
and basic usage. If you dismissed it for any reason and want to see it again, check
"Show first-run wizard on next startup", then close and restart Bigglesworth.
Activating the "Skip Blofeld auto-detection" can be useful in those rare cases when
this feature blocks the MIDI device detection process.


.. _Bigglesworth website: http://bigglesworth.it/support
.. _Facebook page: https://fb.me/bigglesworthapp
.. _`Program change`: ../terminology.html#progchange

.. meta::
    :icon: window
