Wavetable Editor
================

.. role:: subsection
.. role:: summary

:summary:`The Wavetable Editor creates Blofeld-compliant wavetables with an advanced interface`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

:subsection:`What-- tables?`
----------------------------------

    Wavetable synthesis is fundamentally based on periodic reproduction of an arbitrary, 
    single-cycle waveform. In wavetable synthesis, some method is employed to vary or 
    modulate the selected waveform in the wavetable. The position in the wavetable selects 
    the single cycle waveform. Digital interpolation between adjacent waveforms allows for 
    dynamic and smooth changes of the timbre of the tone produced. Sweeping the wavetable 
    in either direction can be controlled in a number of ways, for example, by use of an 
    LFO, envelope, pressure or velocity. 

    From `"Wavetable synthesis" <https://en.wikipedia.org/wiki/Wavetable_synthesis#Principle>`_ on Wikipedia

Wavetables are a powerful feature of the Blofeld synthesizer. There are 39 slots available,
each one can contain 64 wave forms, and each form is a 128-sample wave.

By default, all 39 slots of the Blofeld are "blank", containing just a simple sine wave form repeated
along the whole table, but unfortunally, Waldorf never released an official editor.

Luckily enough, they made its specification public some years ago, and Bigglesworth's editor is 
a powerful wavetable creation and editing tool.


.. meta::
    :icon: wavetables
    :keyword: WavetableWindow
