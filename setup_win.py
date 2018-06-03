from glob import glob
from cx_Freeze import setup, Executable

import sys
MAJ_VERSION, MIN_VERSION, REV_VERSION = 0, 0, 0

def read_version():
    with open('bigglesworth/version.py', 'rb') as version_file:
        exec(version_file.read())
    return MAJ_VERSION, MIN_VERSION, REV_VERSION
v = read_version()

versionDot = '{}.{}.{}'.format(*v)
versionComma = '{},{},{},0'.format(*v)
description = 'Editor/librarian for Blofeld'

resData = '''

1 VERSIONINFO
FILEVERSION {versionComma}
PRODUCTVERSION {versionComma}
FILEOS 0x40004
FILETYPE 0x1
{{
BLOCK "StringFileInfo"
{{
	BLOCK "040904E4"
	{{
		VALUE "LegalCopyright", ""
		VALUE "InternalName", "Bigglesworth.exe"
		VALUE "FileVersion", "{versionDot}"
		VALUE "CompanyName", ""
		VALUE "OriginalFilename", "Bigglesworth.exe"
		VALUE "ProductVersion", "{versionDot}"
		VALUE "FileDescription", "{description}"
		VALUE "LegalTrademarks", ""
		VALUE "Comments", ""
		VALUE "ProductName", "Bigglesworth"
	}}
}}

BLOCK "VarFileInfo"
{{
	VALUE "Translation", 0x0409 0x04E4  
}}
}}
'''.format(versionComma=versionComma, versionDot=versionDot, description=description)


files = [
#         'bigglesworth/FiraSans-Regular.ttf', 
#         'bigglesworth/blofeld_efx', 
#         'bigglesworth/blofeld_efx_ranges', 
#         'bigglesworth/blofeld_params', 
#         'bigglesworth/.bw_secret', 
#         'bigglesworth/magnifying-glass.png', 
#         'bigglesworth/dial_icon.png', 
#         'bigglesworth/wt_icon.png', 
#         'bigglesworth/bigglesworth_logo.png', 
#         'bigglesworth/blofeld_logo.svg', 
        'bigglesworth/presets/blofeld_fact_200801.mid', 
        'bigglesworth/presets/blofeld_fact_200802.mid', 
        'bigglesworth/presets/blofeld_fact_201200.mid', 

#         'bigglesworth/editor.ui', 
#         'bigglesworth/main.ui', 
#         'bigglesworth/wavetable.ui', 

#         'bigglesworth/dialogs/about.ui', 
#         'bigglesworth/dialogs/dumpdialog.ui', 
#         'bigglesworth/dialogs/globals.ui', 
#         'bigglesworth/dialogs/midi_import.ui', 
#         'bigglesworth/dialogs/print_library.ui', 
#         'bigglesworth/dialogs/settings.ui', 
#         'bigglesworth/dialogs/summary.ui', 
#         'bigglesworth/dialogs/wave_panel.ui', 
#         'bigglesworth/dialogs/wavetable_undo.ui', 
#         'bigglesworth/dialogs/wavetable_list.ui', 

         ]

files.extend(glob('bigglesworth/ui/*.ui'))
files.extend(glob('resources/*.svg'))
files.extend(glob('resources/*.png'))
files.extend(glob('bigglesworth/editorWidgets/*py'))
files.extend(glob('bigglesworth/editorWidgets/*json'))

buildOptions = dict(packages = [], excludes = [], includes = ['atexit'], include_files = zip(files, files))
macbuildOptions = {'iconfile': 'icons/bigglesworth_icon.icns', 'bundle_name': 'Bigglesworth'}
dmgOptions = {'applications_shortcut': True}

base = 'Win32GUI' if sys.platform=='win32' else None

executables = [
#    Executable('Bigglesworth.py', base=base, icon='resources/bigglesworth_icon.ico')
    Executable('Bigglesworth.py', base=base), 
    Executable('Bigglesworth.py', targetName='BigglesworthDebug.exe', base='Console')
#    Executable('simple.py', base=base)
]
setup(name='Bigglesworth',
      version = versionDot,
      description = description,
      options = dict(build_exe = buildOptions, bdist_mac = macbuildOptions),
      executables = executables)

with open('build/winResource.rc', 'w') as winFile:
    winFile.write(resData)
    

