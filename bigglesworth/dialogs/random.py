from Qt import QtCore, QtWidgets

from bigglesworth.utils import loadUi

paramGroups = {
    'osc1': range(1, 17), 
    'osc2': range(17, 33), 
    'osc3': range(33, 50), 
    'lfo1': range(160, 171), 
    'lfo2': range(172, 183), 
    'lfo3': range(184, 194), 
    'filterEnv': range(196, 206), 
    'ampEnv': range(208, 218), 
    'env3': range(220, 230), 
    'env4': range(232, 242), 
    'filter1': range(77, 96), 
    'filter2': range(97, 116), 
    'effect1': range(128, 144), 
    'effect2': range(144, 160), 
    'arpeggiator': range(311, 327), 
    'arpUser': range(327, 359), 
    'mixer': range(61, 73), 
    'amplifier': range(121, 125), 
    'commons': [50, 51, 53, 56, 57, 58, 59], 
    'modMatrix': range(245, 309), 
    }

class RandomDialog(QtWidgets.QDialog):
    def __init__(self, *args, **kwargs):
        QtWidgets.QDialog.__init__(self, *args, **kwargs)
        loadUi('ui/randomdialog.ui', self)

        self.oscGroupChk.clicked.connect(lambda state: self.groupToggle(state, self.oscGroup, self.oscGroupChk))
        self.oscGroup.buttonClicked.connect(lambda: self.groupCheck(self.oscGroup, self.oscGroupChk))

        self.lfoGroupChk.clicked.connect(lambda state: self.groupToggle(state, self.lfoGroup, self.lfoGroupChk))
        self.lfoGroup.buttonClicked.connect(lambda: self.groupCheck(self.lfoGroup, self.lfoGroupChk))

        self.envGroupChk.clicked.connect(lambda state: self.groupToggle(state, self.envGroup, self.envGroupChk))
        self.envGroup.buttonClicked.connect(lambda: self.groupCheck(self.envGroup, self.envGroupChk))

    def groupToggle(self, state, group, checkbox):
        if state:
            checkbox.setCheckState(QtCore.Qt.Checked)
        for btn in group.buttons():
            btn.setChecked(state)

    def groupCheck(self, group, checkbox):
        count = 0
        for btn in group.buttons():
            if btn.isChecked():
                count += 1
        if not count:
            checkbox.setChecked(False)
        elif count < len(group.buttons()):
            checkbox.setCheckState(QtCore.Qt.PartiallyChecked)
        else:
            checkbox.setChecked(QtCore.Qt.Checked)
            checkbox.update()

    def getChecked(self):
        params = []
        for param, idxList in paramGroups.items():
            if getattr(self, param).isChecked():
                params.extend(idxList)
        return params


if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)
    d = RandomDialog()
    d.show()
    sys.exit(app.exec_())
