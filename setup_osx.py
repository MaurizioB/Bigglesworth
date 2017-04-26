from cx_Freeze import setup, Executable

def read_version():
    with open('bigglesworth/version.py', 'rb') as version_file:
        exec(version_file.read())
    return VERSION

# Dependencies are automatically detected, but it might need
# fine tuning.

files = [
         'bigglesworth/FiraSans-Regular.ttf', 
         'bigglesworth/blofeld_efx', 
         'bigglesworth/blofeld_efx_ranges', 
         'bigglesworth/blofeld_params', 
         'bigglesworth/.bw_secret', 
         'bigglesworth/magnifying-glass.png', 
         'bigglesworth/dial_icon.png', 
         'bigglesworth/wt_icon.png', 
         'bigglesworth/bigglesworth_logo.png', 
         'bigglesworth/blofeld_logo.svg', 
         'bigglesworth/presets/blofeld_fact_200801.mid', 
         'bigglesworth/presets/blofeld_fact_200802.mid', 
         'bigglesworth/presets/blofeld_fact_201200.mid', 

         'bigglesworth/editor.ui', 
         'bigglesworth/main.ui', 
         'bigglesworth/wavetable.ui', 

         'bigglesworth/dialogs/about.ui', 
         'bigglesworth/dialogs/dumpdialog.ui', 
         'bigglesworth/dialogs/globals.ui', 
         'bigglesworth/dialogs/midi_import.ui', 
         'bigglesworth/dialogs/print_library.ui', 
         'bigglesworth/dialogs/settings.ui', 
         'bigglesworth/dialogs/summary.ui', 
         'bigglesworth/dialogs/wave_panel.ui', 
         'bigglesworth/dialogs/wavetable_undo.ui', 

         ]
buildOptions = dict(packages = [], excludes = [], includes = ['atexit'], include_files = zip(files, files))
macbuildOptions = {'iconfile': 'icons/bigglesworth_icon.icns', 'bundle_name': 'Bigglesworth'}
dmgOptions = {'applications_shortcut': True}

import sys
base = 'Win32GUI' if sys.platform=='win32' else None

executables = [
    Executable('Bigglesworth.py', base=base, targetName = 'BigglesworthApp')
]
setup(name='Bigglesworth',
      version = read_version(),
      description = 'Editor/librarian for Blofeld',
      options = dict(build_exe = buildOptions, bdist_mac = macbuildOptions),
      executables = executables)
