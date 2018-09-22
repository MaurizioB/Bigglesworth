Introduction
============

.. role:: subsection
.. role:: subsection-italic

- `Wavetable structure <structure_>`__
- `Keyframes <keyframes_>`__
- `Transitions, or Morphs <morphs_>`__
- `Save, dump, import and export <dump_>`__

.. _structure:

:subsection:`Wavetable structure`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Blofeld's wavetables are based on 64 wave forms, each one made of 128 samples.
While it is possible to have 64 different waves, it's usually not the best nor interesting way of
using wavetables: usually, a wavetable "shapes" along its full size with gradual changes between 
every wave form.

Since manually creating each one of the 64 waves is not very feasible, Bigglesworth uses a
concept known as "keyframes".

.. _keyframes:

:subsection:`Keyframes`
^^^^^^^^^^^^^^^^^^^^^^^

The term _keyframe_ is borrowed from the animation and filmmaking world, and indicates a drawing
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

A _morph_ allows you to have a (not necessarily) smooth transition from a keyframe to the next one.

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

.. _dump:

:subsection:`Save, dump, import and export`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The Wavetable Editor uses Bigglesworth's database to store your custom wavetables, saved in
the internal keyframe format to allow editing in further sessions, and they are automatically 
converted in Blofeld's wavetable format when they are sent (dumped) to it.

It is obviously possible to import and export wavetables to file: using Bigglesworth's wavetable format
(``*.bwt`` files) which stores all keyframe and transition data, `SysEx`_ (both ``*.mid`` and 
``*.syx`` files), and ``PCM`` wave files, compatible with other wavetable editors.


.. _Curve: curves.html
.. _Translate: translate.html
.. _Spectral: spectral.html
.. _`SysEx`: ../terminology.html#sysex
