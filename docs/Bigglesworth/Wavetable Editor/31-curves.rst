Curve morphing
==============

.. role:: subsection

- `Principle <principle_>`__
- `Linear curve <linear_>`__
- `Curve function list <curves_>`__

.. _principle:

:subsection:`Principle`
^^^^^^^^^^^^^^^^^^^^^^^

Curve morphing is the most simple way of transitioning between two keyframes, as it
applies a mathematical function to compute the intermediate values of each sample between
the first wave and the next.

The interpolation is computed using this function:

.. math::
        V_x = V_1 + ( V_2 - V_1 ) × f_t

Where :math:`f_t` is value of the curve function at the position in the range of the first 
and next keyframe.

.. _linear:

:subsection:`Linear curve`
^^^^^^^^^^^^^^^^^^^^^^^^^^

While the name can be misleading, a "Curve" morph is not necessarily a curve. In fact, 
the most simple curve mode is "Linear", for which :math:`f_t` is always ``1``.

This means that, if the first sample of the first wave has ``value = 0`` and the first 
sample of the keyframe placed 10 waves after has ``value = 10``, the first sample of the 
second wave will have ``value = 1``, that of the third ``value = 2`` and so on.

.. _curves:

:subsection:`Curve function list`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

There are 34 curve modes available, and some can create much interesting transitions.
Here is the complete list.

.. include:: CURVES

