Firmware utilities
==================

.. role:: subsection

- `Firmware update <firmware_>`__
- `Factory presets <factory_>`__
- `Keyboard controller update <keyboard_>`__
- `System recovery <recovery_>`__

Sometimes, manufacturers want to add some new features to their products, or realize that 
there are bugs that prevent users to properly use their devices.

When speaking about electronic devices, this is possible by doing a "Firmware update",
which usually consists of a file that has to be sent to the device in some way.

.. _firmware:

:subsection:`Firmware update`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Blofeld synthesizers were created more than 10 years ago, and since then Waldorf has
both fixed some software issues their users faced in the meantime, and added features 
also. The latest version of the firmware is 1.25, and was published in the summer of 
2018 as the new models produced since then used a different component that required
a small change in the programming.

Bigglesworth allows you to dump that latest version to your Blofeld with ease.

Just be aware of this:

- If you bought a new Blofeld after the summer of 2018, you probably already have
  the latest version, and there is no need for an update.
- It is possible to dump a previous version (currently 1.22 and 1.23 are available),
  *but* you do that **at your own risk**!!!
- **NEVER** dump a previous version on a new Blofeld. It could make it completely
  unusable, requiring you to send it back to Waldorf to fix it.
- The firmware update is a very delicate process. If you switch off or disconnect
  its MIDI or USB cable while transferring data, it could make it completely 
  unusable.
- Carefully read the instructions on screen before, while and after the process.
- **ALWAYS** press the *PLAY* button on your Blofeld once the update is complete.
  Ignoring this step could make your Blofeld unusable.
- Finally, while Bigglesworth is able to perform this procedure and every test done
  worked out fine, remember that it is **not** an official software, meaning that
  you are acting without any warranty. If something goes wrong in the process, 
  and (for some very unlikely but not impossible reason) your Blofeld becomes 
  definitely broken, **I cannot and will not be considered responsible**.

If your Blofeld is connected to both MIDI input and output (or you are using the
USB cable, Bigglesworth will automatically try to detect the current firmware
version you are using, and then check if the firmware is necessary or not.

.. _factory:

:subsection:`Factory presets`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

While usually not necessary, since Bigglesworth's librarian can do that in other
(and better, library-management-wise) ways, it is possible to dump one of the
three "Factory presets" provided by Waldorf since Blofeld's release.

There are 3 sound sets, each one with full 8-banks-per-128-sounds.

The first two, are those found in brand new Blofelds since 2008, the second one
is actually the same as the first, but with some parameters adjusted after 
the first release, mostly to make Amplifier volumes more consistent across the
library.

The third was the one shipped on new units after 2012, and is almost completely
new, except for the H Bank, that contains the same sounds as the previous presets
but with volumes and other parameters fixed again.

.. _keyboard:

:subsection:`Keyboard controller update`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you own a Blofeld Keyboard and it was not updated in the last 4-5 years, 
you can use this firmware to update its keyboard controller (which is *not*
the same as the main firmware update).

Normally you shouldn't need to do his.


.. _recovery:

:subsection:`System recovery`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In the rare case of problems during a firmware dump (power loss, accidental MIDI 
or USB disconnection), your Blofeld could become unresponsive.

You can use this system to try and recover it. Remember to *always* use the MIDI 
connection, not the USB one.

Once the process is complete and you still have your fingers crossed, you might 
need to dump the firmware again too.

  .. meta::
    :icon: circuit
