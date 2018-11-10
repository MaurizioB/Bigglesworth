Introduction
============

.. role:: subsection
.. role:: subsection-italic

- `Wavetable structure <structure_>`__
- `Keyframes <keyframes_>`__
- `Transitions, or Morphs <morphs_>`__
- `Save, dump, import and export <dump_>`__
- `Factory wavetables <factory_>`__

.. _structure:

:subsection:`Wavetable structure`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Blofeld's wavetables are based on 64 wave forms, each one made of 128 samples.
While it is possible to have 64 different waves, it's usually not the best nor interesting way of
using wavetables: usually, a wavetable "shapes" along its full size with gradual changes between 
every wave form.

Since manually creating each one of the 64 waves is not always very feasible, Bigglesworth 
uses a concept known as "keyframes".

.. _keyframes:

:subsection:`Keyframes`
^^^^^^^^^^^^^^^^^^^^^^^

The term *keyframe* is borrowed from the animation and filmmaking world, and indicates a drawing
defining the starting and/or ending point of a transition.

Keyframes are used in the same way in Bigglesworth: you have two waves at different points in the
wavetable, and the intermediate wave forms are computed according to certain parameters.

Since wavetables are usually fully "sweeped" (played from the beginning to the end, sometimes even
backwards), it is possible to use even a single wave as a basis for the table, and play with a
transition that *morphs* that wave within the table range.

Final transitions (those starting from the last keyframe, which is not necessarily at the end of 
the table) automatically morph themselves to the first keyframe at the beginning of the table.

.. _morphs:

:subsection:`Transitions, or` :subsection-italic:`Morphs`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A *morph* allows you to have a (not necessarily) smooth transition from a keyframe to the next one.

There are 4 types of transitions in Bigglesworth:

The most basic transition is called "*Constant*", which simply repeats the wave until the next keyframe, 
and actually is *not* a real transition, indeed; it can be useful if you want to achieve some peculiar 
effects, though.

The most common and simple transition is the "`Curve`_", which "draws" a smooth transition
between the two affected keyframes. In its simplest form, "Linear".

The "`Translate`_" morph transforms to the next keyframe, but with its values shifted by a
customizable amount of samples.

The "`Spectral`_" morph is the most advanced (and interesting) type of transition. It applies
harmonics to the linear transition between two keyframes, using different envelopes for each
harmonic specified.

Note that both *translate* and *spectral* morphs have an "Apply to next wave" option. Due to 
the nature of these transformations, they can dramatically change the shape of the next wave.
For *translate* morphs the option is almost mandatory, as it expects that the wave shift is
respected and maintained once the actual target wave is reached. In the *spectral* transition
this is not necessary if all of its envelopes reach the end of the transition cycle with 0 
values.

.. _dump:

:subsection:`Save, dump, import and export`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The Wavetable Editor uses Bigglesworth's database to store your custom wavetables, saved in
the internal keyframe format to allow editing in further sessions, and they are automatically 
converted in Blofeld's wavetable format when they are sent (dumped) to it.

It is obviously possible to import and export wavetables to file: using Bigglesworth's wavetable format
(``*.bwt`` files) which stores all keyframe and transition data, `SysEx`_ (both ``*.mid`` and 
``*.syx`` files), and ``PCM`` wave files, compatible with other wavetable editors.

.. _factory:

:subsection:`Factory wavetables`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Bigglesworth contains an internal "collection" of wavetables that mirrors the factory
tables included in the Blofeld, that can be used as a starting point to create new 
wavetables. Just open the "Blofeld" panel in the Wavetable library and ensure that the
option "Show Blofeld system wavetables and shapes" is checked. You will see the full 
wave shapes and tables your Blofeld has by default, up to index 66. If you want to 
inspect or import from one of them, right click on any of it and select "Create wavetable
based on...". A new and complete wavetable will appear, from which you can play with 
as you wish.


.. _Curve: curves.html
.. _Translate: translate.html
.. _Spectral: spectral.html
.. _`SysEx`: ../terminology.html#sysex

.. meta::
    :icon: wavetables
