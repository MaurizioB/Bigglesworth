from Qt import QtWidgets

from bigglesworth.utils import loadUi

class DonateDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        loadUi('ui/donate.ui', self)

        self.textEdit.setHtml('''
            <p>The creation of Bigglesworth requires lots of efforts in terms
            of time, energy and sometimes money.</p>
            <p>While it is available for free, donations are always welcome and also
            encourage further development, adding new features and solving bugs.</p>
            <p>If you want to support this project, just select any amount and 
            press "Donate now": a new browser window will open on Paypal and 
            from there you can review your donation before submitting it
            (no Paypal account is required).</p>
            <p>Donors are usually listed in the About box, if you do not want 
            your name publicly available, just select "Keep my donation anonymous".</p>
        ''')

        self.buttonBox.button(self.buttonBox.Ok).setText('Donate now')
        self.buttonBox.button(self.buttonBox.Cancel).setText('Maybe later')

    def exec_(self):
        if QtWidgets.QDialog.exec_(self):
            return self.amountSpin.value(), ('EUR', 'USD')[self.currencyCombo.currentIndex()], self.anonymousChk.isChecked()
