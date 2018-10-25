from bigglesworth.dialogs.logger import LogWindow
from bigglesworth.dialogs.wizard import FirstRunWizard, AutoconnectPage, ImportOldPage
from bigglesworth.dialogs.themeeditor import ThemeEditor
from bigglesworth.dialogs.templatemanager import TemplateManager
from bigglesworth.dialogs.tags import TagsDialog, TagEditDialog, TagsTableView, SoundTagsEditDialog, MultiSoundTagsEditDialog
#from bigglesworth.dialogs.soundtagsedit import SoundTagsEditDialog, MultiSoundTagsEditDialog
from bigglesworth.dialogs.newcollection import NewCollectionDialog
from bigglesworth.dialogs.managecollections import ManageCollectionsDialog
from bigglesworth.dialogs.messageboxes import (RemoveSoundsMessageBox, DeleteSoundsMessageBox, DropDuplicatesMessageBox, 
    DatabaseCorruptionMessageBox, QuestionMessageBox, WarningMessageBox, InputMessageBox, LocationRequestDialog)
from bigglesworth.dialogs.about import AboutDialog
from bigglesworth.dialogs.random import RandomDialog
from bigglesworth.dialogs.globals import GlobalsWaiter, GlobalsDialog
from bigglesworth.dialogs.filedialogs import BaseFileDialog, UnknownFileImport, SoundFileImport, SoundFileExport
from bigglesworth.dialogs.settings import SettingsDialog
from bigglesworth.dialogs.dump import DumpReceiveDialog, DumpSendDialog, SmallDumper, BlofeldDumper, SoundImport
from bigglesworth.dialogs.savesoundas import SaveSoundAs
from bigglesworth.dialogs.duplicates import FindDuplicates
from bigglesworth.dialogs.soundexport import SoundExport
from bigglesworth.dialogs.soundlistexport import SoundListExport
from bigglesworth.dialogs.midichart import MidiChartDialog
from bigglesworth.dialogs.mididuplicate import MidiDuplicateDialog
from bigglesworth.dialogs.initemptyslots import InitEmptySlotsDialog
from bigglesworth.dialogs.firmware import FirmwareDialog
from bigglesworth.dialogs.donate import DonateDialog
