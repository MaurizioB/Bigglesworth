#!/usr/bin/env python2.7

import sys, os

os.environ['QT_PREFERRED_BINDING'] = 'PyQt4'

from Qt import QtCore, QtGui, QtWidgets, QtHelp

if __name__ == '__main__':
    from PyQt4.uic import loadUi
    sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))
    helpPath = 'help.qhc'
else:
    from bigglesworth.utils import loadUi, localPath
    helpPath = localPath('help.qhc')


class HelpBrowser(QtWidgets.QTextBrowser):
    def loadResource(self, rType, url):
        if url.scheme() == 'qthelp':
            return self.help.fileData(url)
        elif url.scheme().startswith('http'):
            self.reload()
            return
        return QtWidgets.QTextBrowser.loadResource(self, rType, url)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.XButton1:
            self.backward()
        elif event.button() == QtCore.Qt.XButton2:
            self.forward()
        QtWidgets.QTextBrowser.mousePressEvent(self, event)


class HelpDialog(QtWidgets.QDialog):
    shown = False
    def __init__(self, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        loadUi('ui/help.ui', self)
        self.help = QtHelp.QHelpEngine(helpPath)
        self.loaded = False
        self.help.setupFinished.connect(self.setLoaded)
        self.help.setupData()

        self.contentWidget = self.help.contentWidget()
        self.splitter.insertWidget(0, self.contentWidget)
        self.splitter.setStretchFactor(0, 2)
        self.splitter.setStretchFactor(1, 5)
        self.splitter.setCollapsible(1, False)
        self.contentWidget.clicked.connect(self.openLinkFromIndex)

        self.helpBrowser.help = self.help
        self.helpBrowser.setSource(QtCore.QUrl('qthelp://jidesk.net.Bigglesworth.1.0/html/index.html'))
        self.helpBrowser.document().setIndentWidth(16)
        self.helpBrowser.anchorClicked.connect(self.anchorClicked)
        self.helpBrowser.backwardAvailable.connect(self.backBtn.setEnabled)
        self.helpBrowser.forwardAvailable.connect(self.fwdBtn.setEnabled)
        self.backBtn.clicked.connect(self.helpBrowser.backward)
        self.fwdBtn.clicked.connect(self.helpBrowser.forward)
        self.homeBtn.clicked.connect(lambda: self.helpBrowser.setSource(QtCore.QUrl('qthelp://jidesk.net.Bigglesworth.1.0/html/index.html')))

    def setLoaded(self):
        self.loaded = True
        self.checkExpanded()

    def checkExpanded(self):
        if not (self.loaded and self.shown):
            QtCore.QTimer.singleShot(10, self.checkExpanded)
        else:
            self.contentWidget.expandAll()

    def anchorClicked(self, url, parent=None):
        if url.scheme() != 'qthelp':
            QtGui.QDesktopServices.openUrl(url)
            #open external link
            return
        if parent is None:
            self.helpBrowser.setSource(url)
            parent = QtCore.QModelIndex()
        model = self.help.contentModel()
        for row in range(model.rowCount(parent)):
            index = model.index(row, 0, parent)
            if model.contentItemAt(index).url().toString() == url.toString():
                self.contentWidget.expand(index)
                self.contentWidget.setCurrentIndex(index)
                return True
            for row in range(model.rowCount(index)):
                if self.anchorClicked(url, index):
                    self.contentWidget.expand(index)
                    return True

    def openLinkFromIndex(self, index):
        url = self.help.contentModel().contentItemAt(index).url()
        print(url)
        self.helpBrowser.setSource(url)

    def showEvent(self, event):
        if not self.shown:
            self.shown = True
            self.checkExpanded()

if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)
    w = HelpDialog()
    w.show()
    sys.exit(app.exec_())
