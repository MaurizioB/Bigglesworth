Translate morphing
==================

.. role:: subsection

- `Principle <principle_>`__

.. _principle:

:subsection:`Principle`
^^^^^^^^^^^^^^^^^^^^^^^

Translation works by "shifting" the next wave by a customizable number of samples (from -128 to +128),
and computes the intermediate values as a `Linear curve <curves.html#linear>`_.

To fully achieve the desired effect, the destination keyframe should have a wave shape similar to the
first and shifted by the amount of samples selected.
