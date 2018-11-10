Translate morphing
==================

.. role:: subsection

- `Principle <principle_>`__

.. _principle:

:subsection:`Principle`
^^^^^^^^^^^^^^^^^^^^^^^

Translation works by "shifting" the next wave by a customizable number of samples (from -128 to +128),
and computes the intermediate values as a `Linear curve <curves.html#linear>`_.

To fully achieve the desired effect, you should ensure that the "Apply to next wave" option is 
checked, otherwise you will get an unexpected (yet sometimes interesting) "bump", once the next 
wave is reached. Alternatively, the destination keyframe should have a wave shape similar to the
first and will have to be shifted by the amount of samples selected.

.. meta::
    :icon: kdenlive-object-width
