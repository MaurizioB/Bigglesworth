Spectral morphing
=================

This transition is probably the most complex and interesting morph type, and it works 
like additive synthesis by overlaying harmonics to a linear transition between two waves.

.. role:: subsection

- `Principle <principle_>`__
- `Usage <usage_>`__


.. _principle:

:subsection:`Principle`
^^^^^^^^^^^^^^^^^^^^^^^

Spectral morphing is a special kind of transition that actually *adds* harmonics to 
the linear transition between two existing waves, using customizable envelopes to 
select how much of each harmonic is added throughout the transition.

Each envelope can use one of the 5 basic wave shapes (Sine, Square, Triangle, Sawtooth
and Inverse sawtooth) and is set to add an order of harmonic selectable from the 
first (the fundamental tone) to the fiftieth; additionally, it is possible to inverse 
the polarity of the wave shape.

As per the `translate`_ morph, this transition can apply itself to the next 
wave, possibly dramatically changing its contents and the transition applied to 
it. To accomplish that, select the "Apply to next wave" checkbox. This option 
is not available if the wavetable contains a single wave.

If the envelope is left to a 0 value from the beginning to the end, the transition
will behave just like a normal `linear curve`_ transition.

The basic concept is that you start from a wave form from your wavetable, and then
add harmonics to that wave, according to the amount of selected in the envelope.

Let's say that your basic wave is a sine shape, like the first wave you get when 
you create a new wavetable:

|wtsp01|

Each sound is composed of a fundamental wave and a certain amount of harmonics, 
which are exact fractions of the fundamental wave: the second harmonic is 1/2 of 
the first, the third is 1/3, and so on. 
The basic sine wave has no harmonics at all, and that's why it sounds "synthetic", 
as all natural sounds we hear actually include various amounts of harmonics.

When harmonics are added to the fundamental, they add "secondary sounds" to it, 
following the acoustic harmonic series, making it more and more characteristic.

The second harmonic in the series corresponds to an octave above the fundamental, 
the third is a fifth above that first octave, the fourth is two octaves above.

Following this principle, the second harmonic sine wave looks like this:

|wtsp02|

If you hear this wave, it will be exactly one octave above the first note.

Whenever an envelope is active in a spectral transition, and it's using the second 
harmonic sine wave, it will *add* its values to the fundamental, giving this result:

|wtsp03|

The perceived sound will be composed of both waves, with the octave above the 
fundamental slightly audible. Adding harmonics can enrich the sound dramatically,
expecially when using different types of wave forms and changing the amount 
of their influence over the fundamental.


.. _usage:

:subsection:`Usage`
^^^^^^^^^^^^^^^^^^^^


For this type of transition even a single wave (the first one) is sufficient.

Once the spectral morph is selected, click the "Edit" button to open its editor.

By default a new spectral morph only contains a single sine wave with 0 value, 
meaning that the starting wave will "crossfade" to the next one as it would with 
a linear curve transition.

Each harmonic can be customized by setting the wave type (sine, square, triangle, 
sawtooth and inverse sawtooth), the harmonic number and its envelope shape.

Envelopes can be drawn by dragging existing points (the small circles) and creating 
new ones by double clicking in the desired point. Points are united by linear segments,
but it is possible to use custom curves instead by right clicking on a node: this will 
allow you to change the curve type for the segment that unites the current node to the 
previous one. To delete a node, shift-click on it or use the right click menu.

Please note that both *X* (time) and *Y* (amount) axis on the envelope view are relative.
While the *X* axis will show all the slots that go from the starting wave to the next, 
only "real" values are actually used, from 0.0 to 1.0, where the point at X=0 is 
the first wave and X=1 is the next one. The amount is the percentage of the value of the
computed wave, so if you have two silent waves, the resulting transition will be 
silent also.

In the example given in the `Principle`_ section, the "new" wave computed in the middle
of the transition is the result of a similar envelope:

|wtsp00|

[To be continued...]

.. _`translate`: translate.html
.. _`linear curve`: curves.html#linear
.. |wtsp00| image:: :/images/wtsp00.png
.. |wtsp01| image:: :/images/wtsp01.png
.. |wtsp02| image:: :/images/wtsp02.png
.. |wtsp03| image:: :/images/wtsp03.png
.. meta::
    :icon: pathshape
    :keyword: SpectralMorph
