from string import uppercase

from Qt import QtCore, QtGui, QtWidgets


def setButtonData(button, data):
    if not data:
        return
    elif isinstance(data, (str, unicode)):
        button.setText(data)
    elif isinstance(data, QtGui.QIcon):
        button.setIcon(data)
    elif isinstance(data, (tuple, list)):
        for d in data:
            setButtonData(button, d)


class MessageBoxDetailedHtml(QtWidgets.QMessageBox):
    textEdit = None
    def setDetailedText(self, text):
        if not self.textEdit:
            QtWidgets.QMessageBox.setDetailedText(self, ' ')
            self.textEdit = self.findChildren(QtWidgets.QTextEdit)[0]
        self.textEdit.setHtml(text)


class RemoveSoundsMessageBox(MessageBoxDetailedHtml):
    def __init__(self, parent, collection, nameList):
        MessageBoxDetailedHtml.__init__(self, parent)
        self.setIcon(self.Question)
        self.setWindowTitle('Remove sounds from collection')
        if len(nameList) == 1:
            self.setText('Do you want to remove "{}" from the collection "{}"?'.format(nameList[0].strip(), collection))
        else:
            self.setText('Do you want to remove {} sounds from the collection "{}"?'.format(len(nameList), collection))
            self.setDetailedText(', '.join('"<b>{}</b>"'.format(name.strip()) for name in nameList))
        self.setStandardButtons(self.Ok|self.Cancel)

    def exec_(self):
        return QtWidgets.QMessageBox.exec_(self) == self.Ok


class DeleteSoundsMessageBox(MessageBoxDetailedHtml):
    def __init__(self, parent, uidList):
        MessageBoxDetailedHtml.__init__(self, parent)
        self.setIcon(self.Warning)
        self.setWindowTitle('Delete sounds from library')
        self.setInformativeText('<b>NOTE</b>: This operation <u>cannot</u> be undone!')
        database = QtWidgets.QApplication.instance().database
        collections = database.referenceModel.allCollections
        if len(uidList) == 1:
            name = database.getNameFromUid(uidList[0]).strip()
            text = 'Do you want to delete "{}" from the library?'.format(name)
            collectionIds = database.getCollectionsFromUid(uidList[0])
            if collectionIds:
                text += '<br/><br/>This sound is used in the following collections:<br/>' + \
                    ', '.join('"{}"'.format(collections[c]) for c in collectionIds)
            self.setText(text)
        else:
            text = 'Do you want to delete {} sounds from the library?'.format(len(uidList))
            collectionIds = set()
            for uid in uidList:
                collectionIds |= set(database.getCollectionsFromUid(uid))
            if collectionIds:
                text += '<br/><br/>This operation affects the following collections:<br/>' + \
                    ', '.join('"{}"'.format(collections[c]) for c in collectionIds)
            self.setText(text)
            self.setDetailedText(', '.join(
                '"<b>{}</b>"'.format(name.strip()) for name in database.getNamesFromUidList(uidList)))
        self.setStandardButtons(self.Ok|self.Cancel)

    def exec_(self):
        return QtWidgets.QMessageBox.exec_(self) == self.Ok


class DropDuplicatesMessageBox(MessageBoxDetailedHtml):
    def __init__(self, parent, nameList, collection, all=False):
        MessageBoxDetailedHtml.__init__(self, parent)
        self.setIcon(self.Question)
        self.setWindowTitle('Duplicate sounds found')
        if len(nameList) == 1:
            pre = 'The sound "{}" already exists in the collection "{}"'.format(nameList[0].strip(), collection)
        else:
            pre = '{} of the selected sounds are already in the collection "{}".\n'.format(
                'All' if all else 'Some', 
                collection
                )
            self.setDetailedText(', '.join('"<b>{}</b>"'.format(name.strip()) for name in nameList))
        self.setText(pre + '\nWhat do you want to do with them?')
        self.setStandardButtons(self.Open|self.Cancel|(self.Ignore if not all else self.NoButton))
        self.button(self.Open).setText('Duplicate')


class DatabaseCorruptionMessageBox(MessageBoxDetailedHtml):
    def __init__(self, parent, error):
        MessageBoxDetailedHtml.__init__(self, parent)
        self.setIcon(self.Critical)
        self.setWindowTitle('Database error')
        self.setText('It looks like there is a problem with the database. :-(\nI\'m deeply sorry...\n\nPress OK to continue.')
        self.setStandardButtons(self.Ok)
        self.setDetailedText(error)


class AdvancedMessageBox(MessageBoxDetailedHtml):
    def __init__(self, parent, title, message, detailed='', buttons=QtWidgets.QMessageBox.Ok, icon=None, checkBox=None):
        MessageBoxDetailedHtml.__init__(self, parent)
        if icon:
            if isinstance(icon, MessageBoxDetailedHtml.Icon):
                self.setIcon(icon)
            else:
                self.setIcon(MessageBoxDetailedHtml.Question)
                if isinstance(icon, QtGui.QPixmap):
                    self.setIconPixmap(icon.scaled(self.iconPixmap().size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
                else:
                    self.setIconPixmap(icon.pixmap(self.iconPixmap().size()))
        self.setWindowTitle(title)
        self.setText(message)
        if detailed:
            self.setDetailedText(detailed)
        if isinstance(buttons, (self.StandardButtons, self.StandardButton)):
            self.setStandardButtons(buttons)
        else:
            if isinstance(buttons, dict):
                for standardButton, data in buttons.items():
                    button = self.addButton(standardButton)
                    setButtonData(button, data)
            else:
                for b in buttons:
                    if isinstance(b, self.StandardButtons):
                        self.addButton(b)
                    else:
                        button = self.addButton(b[0])
                        if len(b) > 1:
                            setButtonData(button, b[1:])
        if checkBox:
            text = checkBox if isinstance(checkBox, (str, unicode)) else 'Do not show again this message'
            self.checkBox = QtWidgets.QCheckBox(text)
            self.layout().addWidget(self.checkBox, self.layout().rowCount(), 0, 1, self.layout().columnCount())
        else:
            self.checkBox = None

    def isChecked(self):
        return self.checkBox.isChecked() if self.checkBox else False


class QuestionMessageBox(AdvancedMessageBox):
    def __init__(self, *args, **kwargs):
        AdvancedMessageBox.__init__(self, *args, **kwargs)
        self.setIcon(self.Question)


class WarningMessageBox(AdvancedMessageBox):
    def __init__(self, *args, **kwargs):
        AdvancedMessageBox.__init__(self, *args, **kwargs)
        self.setIcon(self.Warning)


class InputMessageBox(QtWidgets.QDialog):
    def __init__(self, parent, title, message, inputText='', invalidList=None):
        QtWidgets.QDialog.__init__(self, parent)
        self.setWindowTitle(title)
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        layout.addWidget(QtWidgets.QLabel(message))
        self.lineEdit = QtWidgets.QLineEdit(inputText)
        self.lineEdit.setMaxLength(16)
        layout.addWidget(self.lineEdit)
        self.validator = QtGui.QRegExpValidator(QtCore.QRegExp(r'^(?!.* {2})(?=\S)[a-zA-Z0-9\ \-\_]+$'))
        self.lineEdit.setValidator(self.validator)

        self.buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok|QtWidgets.QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        layout.addWidget(self.buttonBox)
        if not inputText:
            self.buttonBox.button(self.buttonBox.Ok).setEnabled(False)

        self.lineEdit.textChanged.connect(self.checkText)
        self.inputText = inputText
        self.invalidList = invalidList

    def checkText(self, text):
        if not text:
            state = False
        elif self.inputText and text == self.inputText:
            state = True
        elif self.invalidList and text in self.invalidList:
            state = False
        else:
            state = True
        self.buttonBox.button(self.buttonBox.Ok).setEnabled(state)

    def exec_(self):
        res = QtWidgets.QDialog.exec_(self)
        if not res:
            return res
        return self.lineEdit.text()


class LocationRequestDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, bank=None, prog=None):
        QtWidgets.QDialog.__init__(self, parent)
        layout = QtWidgets.QGridLayout()
        self.setLayout(layout)
        layout.addWidget(QtWidgets.QLabel('Please select the desired location:'), 0, 0, 1, 2)

        layout.addWidget(QtWidgets.QLabel('Bank:'))
        self.bankCombo = QtWidgets.QComboBox()
        self.bankCombo.addItems([uppercase[b] for b in range(8)])
        self.bankCombo.setCurrentIndex(bank if bank is not None else 0)
        layout.addWidget(self.bankCombo, 1, 1)

        layout.addWidget(QtWidgets.QLabel('Program:'))
        self.progSpin = QtWidgets.QSpinBox()
        self.progSpin.setRange(1, 128)
        self.progSpin.setValue(prog if prog is not None else 0)
        layout.addWidget(self.progSpin, 2, 1)

        self.buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok|QtWidgets.QDialogButtonBox.Cancel)
        layout.addWidget(self.buttonBox, 3, 0, 1, 2)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

    def exec_(self):
        res = QtWidgets.QDialog.exec_(self)
        if not res:
            return None, None
        return self.bankCombo.currentIndex(), self.progSpin.value() - 1


