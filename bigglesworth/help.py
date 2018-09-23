#!/usr/bin/env python2.7

import sys, os
from xml.etree import ElementTree as et

os.environ['QT_PREFERRED_BINDING'] = 'PyQt4'

from Qt import QtCore, QtGui, QtWidgets, QtHelp
QtCore.pyqtProperty = QtCore.Property

if __name__ == '__main__' or 'blofeld/docs/../bigglesworth/help.py' in __file__:
    from PyQt4.uic import loadUi
    sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))
    currentPath = os.path.dirname(os.path.realpath(__file__))
    helpPath = os.path.join(currentPath,'help.qhc')
    uiPath = os.path.join(currentPath, 'ui/help.ui')
else:
    from bigglesworth.utils import loadUi, localPath
    uiPath = 'ui/help.ui'
    helpPath = localPath('help.qhc')


class HelpBrowser(QtWidgets.QTextBrowser):
    def __init__(self, *args, **kwargs):
        QtWidgets.QTextBrowser.__init__(self, *args, **kwargs)
        self.sourceChanged.connect(self.checkAnchor)

        self._highlightBgd = QtGui.QColor(209, 232, 246)
#        self._highlightBgd = QtGui.QColor('yellow')
        self.highlightAnimation = QtCore.QPropertyAnimation(self, b'highlightBgd')
        self.highlightAnimation.setDuration(2500)
        self.highlightAnimation.setStartValue(self._highlightBgd)
        self.highlightAnimation.setEndValue(QtGui.QColor(QtCore.Qt.transparent))
        self.highlightAnimation.setEasingCurve(QtCore.QEasingCurve(QtCore.QEasingCurve.InExpo))

    def checkAnchor(self, url):
        self.highlightAnimation.stop()
        anchor = url.fragment()
        if not anchor:
            return
        block = self.document().begin()
        while block != self.document().end():
            fmt = block.charFormat()
            if fmt.isAnchor() and anchor in fmt.anchorNames():
                break
            fragIter = block.begin()
            while not fragIter.atEnd():
                fragment = fragIter.fragment()
                fmt = fragment.charFormat()
                if fmt.isAnchor() and anchor in fmt.anchorNames():
                    break
                fragIter += 1
            else:
                block = block.next()
                continue
            break
        else:
            return
        cursor = QtGui.QTextCursor(block)
#        cursor.select(cursor.BlockUnderCursor)
        background = block.charFormat().background().color()
#        self.highlightAnimation.setStartValue(background.darker(150))
        self.highlightAnimation.setEndValue(background)
        self.currentHighlight = cursor, block.blockFormat()
        self.highlightAnimation.start()

    @QtCore.pyqtProperty(QtGui.QColor)
    def highlightBgd(self):
        return self._highlightBgd

    @highlightBgd.setter
    def highlightBgd(self, color):
        self._highlightBgd = color
        cursor, blockFmt = self.currentHighlight
#        fmt.setBackground(color)
#        blockFmt = block.blockFormat()
        blockFmt.setBackground(color)
        cursor.setBlockFormat(blockFmt)
#        fmt.setForeground(QtGui.QColor('red'))
#        cursor.setBlockCharFormat(fmt)
#        cursor.setCharFormat(fmt)


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


class ContentProxy(QtCore.QSortFilterProxyModel):
    def __init__(self, help):
        QtCore.QSortFilterProxyModel.__init__(self)
        self.help = help
        self.nameSpace = help.namespaceName(helpPath)
        self.help.setupFinished.connect(lambda: self.setSourceModel(self.help.contentModel()))
        self.iconCache = {}

    def data(self, index, role):
        if role == QtCore.Qt.DecorationRole:
            try:
                icon = self.iconCache[index.row(), index.column(), index.parent()]
                return icon
            except:
                root = et.fromstring(self.help.fileData(self.contentItemAt(index).url()))
                head = root.getiterator('{http://www.w3.org/1999/xhtml}head')[0]
                for meta in head.findall('{http://www.w3.org/1999/xhtml}meta'):
                    if meta.get('name') == 'icon':
                        icon = QtGui.QIcon.fromTheme(meta.get('content'))
                        break
                else:
                    icon = None
                self.iconCache[index.row(), index.column(), index.parent()] = icon
                return icon
#            return QtGui.QIcon.fromTheme('document-edit')
        return QtCore.QSortFilterProxyModel.data(self, index, role)

    def contentItemAt(self, index):
#        print(self.help.metaData(helpPath, 'version'))
#        print(self.help.files(self.help.namespaceName(helpPath), ['Bigglesworth']))
        return self.sourceModel().contentItemAt(self.mapToSource(index))


class HelpDialog(QtWidgets.QDialog):
    shown = False
    def __init__(self, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        loadUi(uiPath, self)
        self.help = QtHelp.QHelpEngine(helpPath)
        self.loaded = False
        self.help.setupFinished.connect(self.setLoaded)
        self.proxy = ContentProxy(self.help)
        self.help.setupData()

#        self.contentWidget = self.help.contentWidget()
        self.contentWidget.setModel(self.proxy)
#        self.splitter.insertWidget(0, self.contentWidget)
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
            self.contentWidget.expand(self.proxy.index(0, 0))

    def anchorClicked(self, url, parent=None):
        if url.scheme() != 'qthelp':
            QtGui.QDesktopServices.openUrl(url)
            #open external link
            return
        if parent is None:
            self.helpBrowser.setSource(url)
            parent = QtCore.QModelIndex()
        model = self.proxy
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
        url = self.help.contentModel().contentItemAt(self.proxy.mapToSource(index)).url()
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
