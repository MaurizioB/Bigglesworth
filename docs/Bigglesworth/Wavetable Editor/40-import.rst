Import wave files
=================

.. role:: subsection

- `Selecting files <select_>`__
- `Prepare for import <prepare_>`__
- `Import samples <import_>`__
- `Supported file types and formats <formats_>`__


.. _select:

:subsection:`Selecting files`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Click on the "Audio import" tab in the Wavetable window, and you will see 
a left panel that will allow you to browse through your computer files.

You can add specific directories as "favorites" by right clicking on them.
They will appear at the bottom of the browse panel, so that you can access 
them easily.

To preview a listed file, click on it. If the file is short enough, it will 
automatically be shown on the preview panel on the right, and you will be 
able to play it. Additionally, you can just manually select a file by using 
the "Open..." button.

.. _prepare:

:subsection:`Prepare a file for import`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Before being able to actually import a file, it has to be better analyzed by 
Bigglesworth. Once you've found a file you are interested into, click the 
"Open for import" button.

At this point you can edit its gain (the "volume") and balance, if it is a 
stereo file or has more than 2 channels. On the left side of the wave preview 
you will be able to select the view: the "Source" tab will display the original 
content of the file as shown before opening it, while the "Mixed" tab shows 
the results of the gain/balance controls shown at the bottom.

.. _import:

:subsection:`Import samples`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Since a standard Blofeld wavetable is composed of 64 waves with 128 samples 
each, Bigglesworth can import groups or "chunks" of 128 samples each.

As you can see, white vertical lines are now visible in the wave preview.
These lines are the margins of each "chunk". Use the vertical scroll bar to 
zoom in/out, and you will see where each sample groups start and end. Since 
the wave(s) you might be interested into could actually begin a bit later or 
earlier than shown, it is possible to edit the sample start offset by using 
the "Offset" spinbox shown at the bottom of the preview.

Bigglesworth automatically selects the first 8192 samples of the selected
file, assuming that it's long enough. The selection range is displayed by 
the "Select from/to" spinboxes, with the "count" spinbox showing the current 
amount of "chunks" that you are going to import.

Selection can be done by using the mouse also. Find the wave you want to 
select for import using the scrollbars, and keep pressed the SHIFT key 
on your keyboard while clicking and dragging on the chunks you want. This 
operation automatically updates the selection data.

If 64 chunks are actually selected, the "Import full table" button will be 
enabled, allowing you to automatically import the selected range as a full 
wavetable. This will obviously overwrite any existing wave in the table.

To manually import chunks instead, click and drag the selection in the 
preview. If you drag and drop the selection on the wave view on top of the 
wavetable window, Bigglesworth will try to automatically position the 
imported samples in the best way possible; you can also drag your mouse on 
the "Full table" tab, which will focus the 3D view of the wavetable, allowing 
you to drop the samples wherever you like.

If a single sample chunk is selected, it is possible to drag and drop it 
on the "Wave edit" tab, which will overwrite the currently active wave.


.. _formats:

:subsection:`Supported file types and formats`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Bigglesworth is able to import wave files of almost any kind, but be aware that 
uncommon formats, sample rates or sizes could result in unexpected results in 
some cases.

To avoid issues, try to use standard formats, like 16/32 bit files, using a 
sampling rate of 44.1kHz or 48kHz and possibly just mono or stereo. While 
files with more than 2 audio channels can be imported, there could be issues 
while trying to mix them and import their samples to a wavetable.

Also, keep in mind that it is preferable to avoid very big/long files, since 
they will increase the memory usage and overall performance deterioration. 
If you want to import samples from files longer than 2-3 minutes, it's better 
to use an external editor like `Audacity <https://www.audacityteam.org/>`_, 
trim down the file to the sections you are interested into, and export it as 
a plain wave file.

Other than the standard Wave (.WAV) files, other formats are also supported;
unfortunately, for technical reasons, import from MP3 files is not yet 
supported. This list contains all supported formats.

- WAV (Microsoft)
- AIFF (Apple/SGI)
- OGG (OGG Container format)
- MAT4 (GNU Octave 2.0 / Matlab 4.2)
- MAT5 (GNU Octave 2.1 / Matlab 5.0)
- FLAC (Free Lossless Audio Codec)
- SD2 (Sound Designer II)
- PAF (Ensoniq PARIS)
- CAF (Apple Core Audio File)
- W64 (SoundFoundry WAVE 64)
- RAW (header-less)
- PVF (Portable Voice Format)
- WAV (NIST Sphere)
- WVE (Psion Series 3)
- RF64 (RIFF 64)
- XI (FastTracker 2)
- MPC (Akai MPC 2k)
- SF (Berkeley/IRCAM/CARL)
- AU (Sun/NeXT)
- IFF (Amiga IFF/SVX8/SV16)
- SDS (Midi Sample Dump Standard)
- VOC (Creative Labs)
- HTK (HMM Tool Kit)
- AVR (Audio Visual Research)
- WAVEX (Microsoft)
 
.. meta::
    :icon: document-open
