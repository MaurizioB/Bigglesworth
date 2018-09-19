#!/usr/bin/env python2.7

import sys, os

os.environ['QT_PREFERRED_BINDING'] = 'PyQt4'

from Qt import QtCore, QtGui, QtWidgets, QtHelp

class HelpBrowser(QtWidgets.QTextBrowser):
    def loadResource(self, rType, url):
        if url.scheme() == 'qthelp':
            return self.help.fileData(url)
        return QtWidgets.QTextBrowser.loadResource(self, rType, url)

class W(QtWidgets.QWidget):
    def __init__(self):
        QtWidgets.QWidget.__init__(self)
        self.help = QtHelp.QHelpEngine('bigglesworth.qhc')
#        self.help.setupFinished.connect(self.boh)

        l = QtWidgets.QVBoxLayout()
        self.setLayout(l)
        splitter = QtWidgets.QSplitter()
        l.addWidget(splitter)
        self.contentWidget = self.help.contentWidget()
        splitter.addWidget(self.contentWidget)

        self.helpBrowser = HelpBrowser()
        splitter.addWidget(self.helpBrowser)
        self.helpBrowser.help = self.help
        self.help.setupData()
        self.helpBrowser.setSource(QtCore.QUrl('qthelp://jidesk.net.Bigglesworth.1.0/html/index.html'))

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 5)
        splitter.setCollapsible(1, False)

        self.contentWidget.clicked.connect(self.openLinkFromIndex)
        self.resize(640, 480)

    def openLinkFromIndex(self, index):
        url = self.help.contentModel().contentItemAt(index).url()
        self.helpBrowser.setSource(url)



app = QtWidgets.QApplication(sys.argv)
w = W()
w.show()
sys.exit(app.exec_())
