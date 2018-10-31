import sys
import urllib2
import json
import re

from Qt import QtCore, QtGui, QtWidgets

from bigglesworth.utils import loadUi
from bigglesworth.version import isNewer
from bigglesworth.libs import markdown2
from bigglesworth.dialogs.messageboxes import AdvancedMessageBox

def humanSize(size):
    if size < 1024:
        return '{} b'.format(size)
    if size < 1048576:
        return '{} Kb'.format('{:.02f}'.format(size / 1024.).rstrip('0').rstrip('.'))
    return '{} Mb'.format('{:.02f}'.format(size / 1048576.).rstrip('0').rstrip('.'))

def humanTime(secs):
    if secs < 60:
        return '{}s'.format(secs)
    return '{}:{}'.format(*divmod(secs, 60))

def getDownloadFolder():
    homeDir = QtCore.QDir(QtGui.QDesktopServices.storageLocation(QtGui.QDesktopServices.HomeLocation))
    docDir = QtCore.QDir(QtGui.QDesktopServices.storageLocation(QtGui.QDesktopServices.DocumentsLocation))
    for qDir in (homeDir, docDir):
        if not qDir.exists():
            continue
        for fileInfo in qDir.entryInfoList('', QtCore.QDir.AllDirs|QtCore.QDir.NoDotAndDotDot):
            if fileInfo.fileName().lower() == 'download' or fileInfo.fileName().lower() == 'downloads':
                return fileInfo.absoluteFilePath()
    return homeDir.absolutePath() if sys.platform == 'darwin' else QtGui.QDesktopServices.storageLocation(QtGui.QDesktopServices.HomeLocation)


class Downloader(QtCore.QObject):
    error = QtCore.pyqtSignal(object)
    size = QtCore.pyqtSignal(int)
    dataReceived = QtCore.pyqtSignal(object)
    finished = QtCore.pyqtSignal()

    def __init__(self, url, chunkSize=32768):
        QtCore.QObject.__init__(self)
        self.url = url
        self.chunkSize = chunkSize
        self.keepGoing = True

    def stop(self):
        self.keepGoing = False

    def run(self):
        try:
            response = urllib2.urlopen(self.url, None, 10)
            self.size.emit(int(response.info().getheader('Content-Length').strip()))
            while self.keepGoing:
                data = response.read(self.chunkSize)
                if data:
                    self.dataReceived.emit(data)
                else:
                    break
        except Exception as e:
            print('error', e)
            self.error.emit(e)
        self.finished.emit()


class Loader(QtWidgets.QDialog):
    def __init__(self, parent):
        from bigglesworth.widgets import Waiter
        QtWidgets.QDialog.__init__(self, parent)
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        layout = QtWidgets.QGridLayout()
        self.setLayout(layout)
        self.waiter = Waiter()
        layout.addWidget(self.waiter, 0, 0, 2, 1)
        layout.addWidget(QtWidgets.QLabel('Checking for updates, please wait...'), 0, 1)
        self.buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Cancel)
        layout.addWidget(self.buttonBox, 1, 0, 1, 2)
        self.buttonBox.rejected.connect(self.reject)


class UpdateChecker(QtCore.QObject):
    release_url = 'https://api.github.com/repos/MaurizioB/Bigglesworth/releases'
    error = QtCore.pyqtSignal(object)
    finished = QtCore.pyqtSignal()
    result = QtCore.pyqtSignal(object)

    def __init__(self, timeout=10):
        QtCore.QObject.__init__(self)
        self.silent = True
        self.timeout = timeout

    def run(self):
        try:
            self.result.emit(json.loads(urllib2.urlopen(self.release_url, None, self.timeout).read()))
        except Exception as e:
            print('error', e)
            self.error.emit(e)
        self.finished.emit()


class UpdateDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        loadUi('ui/updates.ui', self)
        self.main = QtWidgets.QApplication.instance()
        self.settings = QtCore.QSettings()
        self.updateModeChk.setChecked(self.settings.value('StartupUpdateCheck', True, bool))
        self.updateModeChk.toggled.connect(lambda check: self.settings.setValue('StartupUpdateCheck', check))

        self.loader = Loader(self)
        self.loader.accepted.connect(self.disconnectRequest)
        self.loader.rejected.connect(self.disconnectRequest)
        self.updateChecker = None
        self.downloadUrl = None

        self.cancelBtn = self.buttonBox.addButton(self.buttonBox.Cancel)
        self.cancelBtn.clicked.connect(self.reject)
        self.retryBtn = self.buttonBox.button(self.buttonBox.Retry)
        self.retryBtn.clicked.connect(self.startRequest)
        self.retryBtn.setText('Check again')
        self.retryBtn.setIcon(QtGui.QIcon.fromTheme('view-refresh'))
        self.openBtn = self.buttonBox.button(self.buttonBox.Open)
        self.openBtn.clicked.connect(self.download)
        self.openBtn.setText('Download')
        self.openBtn.setIcon(QtGui.QIcon.fromTheme('system-software-update'))
        self.openBtn.setEnabled(False)

        self.infoText.document().setIndentWidth(20)
        self.css_base = '''
            .version {
                font-size: xx-large; margin-left: .5em; font-weight: bold;
            } 
            .release {
                margin-left: 1.5em; margin-top: .5em;
            } 
            .content {
                margin-left: .3em; margin-top: .8em; margin-bottom: .8em;
            }
            '''

        self.downloadProgress = QtWidgets.QProgressDialog(self)
        self.elapsed = QtCore.QElapsedTimer()

    def download(self):
        if not self.downloadUrl:
            res = AdvancedMessageBox(self, 'Linux update', 
                'Sorry, but there is no update procedure for Linux yet.', 
                icon=AdvancedMessageBox.Warning, 
                buttons={AdvancedMessageBox.Open: 'Open GitHub repository', 
                    AdvancedMessageBox.Cancel: None}).exec_()
            if res == AdvancedMessageBox.Open:
                QtGui.QDesktopServices.openUrl(
                    QtCore.QUrl('https://github.com/MaurizioB/Bigglesworth/'))
            return
        try:
            self.downloadProgress.canceled.disconnect(self.downloadStopped)
        except:
            pass
        self.downloadProgress.canceled.connect(self.downloadStopped)

        self.fileDir = QtCore.QDir(getDownloadFolder())
        fileName = self.downloadUrl.split('/')[-1]
        filePath = self.fileDir.absoluteFilePath(fileName)
        self.file = QtCore.QFile(filePath)
        self.file.open(QtCore.QIODevice.WriteOnly)

        self.downloader = Downloader(self.downloadUrl)
        self.downloaderThread = QtCore.QThread()
        self.downloader.moveToThread(self.downloaderThread)
        self.downloaderThread.started.connect(self.downloader.run)
        self.downloader.finished.connect(self.downloaderThread.quit)
        self.downloader.error.connect(self.downloadStopped)
        self.downloader.finished.connect(self.finished)

        self.downloader.size.connect(self.setSize)
        self.downloader.dataReceived.connect(self.dataReceived)
        self.downloadProgress.setValue(0)
        self.downloadProgress.setLabelText('Awaiting response<br/>Size: Unknown<br/>ETA: Unknown')
        self.downloadProgress.show()
        self.downloaderThread.start()

    def downloadStopped(self, error=None):
        try:
            self.file.close()
        except:
            pass
        self.downloadProgress.canceled.disconnect()
        self.downloader.finished.disconnect(self.finished)
        self.downloader.dataReceived.disconnect(self.dataReceived)
        if self.sender() == self.downloadProgress:
            self.downloader.stop()
        else:
            message = 'There was a problem downloading the update.<br/>Please ensure that your network properly works.'
            if error:
                message += '<br/><br/>The reported error is:<br/>{}'.format(error)
            QtWidgets.QMessageBox.warning(self, 'Network error', message, QtWidgets.QMessageBox.Ok)
        self.downloadProgress.cancel()

    def setSize(self, size):
        self.fileSize = size
        self.downloadProgress.setMaximum(size)
        self.elapsed.start()

    def dataReceived(self, data):
        self.file.writeData(data)
        chunkSize = len(data)
        current = self.downloadProgress.value() + chunkSize
        elapsed = self.elapsed.elapsed()
        speed = float(current) / (elapsed * .001)
        text = 'Downloading<br/>{} of {}<br/>'.format(
            humanSize(current), 
            humanSize(self.fileSize))
        if elapsed > 20:
            remaining = int((elapsed * .001) / current * (self.fileSize - current))
            if remaining < 2:
                remaining = 'almost done'
            else:
                remaining = humanTime(remaining)
            text += 'ETA: {} ({}/s)'.format(remaining, humanSize(speed))
        else:
            text += 'ETA: computing'

        self.downloadProgress.setLabelText(text)
        self.downloadProgress.setValue(current)

    def finished(self):
        self.retryBtn.setVisible(False)
        self.openBtn.clicked.disconnect()
        self.file.close()
        self.downloadProgress.canceled.disconnect()
        self.downloader.finished.disconnect(self.finished)
        self.downloadProgress.cancel()

        message = 'The update has been downloaded to the following path:<br/><br/>{}'.format(
            QtCore.QDir.toNativeSeparators(self.fileDir.absolutePath()))
        buttons = {AdvancedMessageBox.Save: 'Open path', AdvancedMessageBox.Close: None}
        if self.main.isClean():
            buttons.update({AdvancedMessageBox.Open: ('Quit and install', QtGui.QIcon.fromTheme('system-software-update'))})
        else:
            message += '<br/><br/>Some windows have unsaved content; save data and close before updating'

        res = AdvancedMessageBox(self, 'Update downloaded', message, buttons=buttons).exec_()
        if res == AdvancedMessageBox.Open:
            self.install()
        elif res == AdvancedMessageBox.Save:
            self.openDownloadPath()
        else:
            self.openBtn.setText('Quit and install')
            self.openBtn.clicked.connect(self.install)
            if not self.main.isClean():
                self.openBtn.setEnabled(False)
            self.fileDirBtn = self.buttonBox.addButton(self.buttonBox.Save)
            self.fileDirBtn.setText('Open download path')
            self.fileDirBtn.clicked.connect()

    def install(self):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(self.file.fileName(), QtCore.QUrl.TolerantMode))
        self.accept()
        self.main.quit()

    def openDownloadPath(self):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(self.fileDir.absolutePath(), QtCore.QUrl.TolerantMode))
        self.accept()

    def disconnectRequest(self):
        try:
            self.updateChecker.error.disconnect(self.checkError)
            self.updateChecker.result.disconnect(self.processResult)
        except:
            pass

    def checkError(self, error=None):
        self.disconnectRequest()
        message = 'There was a problem checking for updates.<br/>Please ensure that your network properly works.'
        if error:
            message += '<br/><br/>The reported error is:<br/>{}'.format(error)
        QtWidgets.QMessageBox.warning(self, 'Network error', message, QtWidgets.QMessageBox.Ok)

    def processResult(self, contents):
        if self.loader.isVisible():
            self.loader.accept()
        html = ''
        previous = []
        older = []
        latest = contents[0]['tag_name']
#        print('isNewer', latest, isNewer(latest))

        if isNewer(latest):
            html += '<div="summary"><h1>A new version is available!</h1>'
            html += '<a href="#{tag}">Read more about version {tag}</a>'.format(tag=latest)
            self.openBtn.setEnabled(True)
            self.cancelBtn.setText('Ignore')
        else:
            html += '<div="summary"><h1>You are running the latest version!</h1>'

        for release in contents[1:]:
            tag = release['tag_name']
            if isNewer(tag):
                previous.append(tag)
            else:
                older.append(tag)

        if previous:
            html += '<h3>Previous versions (yet newer than the current:)</h3><ul>'
            for tag in previous:
                html += '<li><a href="#{tag}">{tag}</a></li>'.format(tag=tag)
            html += '</ul>'
        if older:
            html += '<h3>Older versions:</h3>Please note that using a version previous ' \
                'to the one currently installed is highly discouraged.<ul>'
            for tag in older:
                html += '<li><a href="#{tag}">{tag}</a></li>'.format(tag=tag)
            html += '</ul>'
        html += '</div><hr/>'

        older_tag = False
        for i, release in enumerate(contents):
            tag = release['tag_name']
            if tag != latest and not older_tag:
                html += '<font color="gray">'
                html += '<h2>Older versions:</h2>'
                older_tag = True
            name = release['name']
            if name.startswith(tag):
                name = name[len(tag):].lstrip(' - ')
            html += '<a name={tag}></a><div class="version">{tag}<span style="font-weight: normal;"> - {name}</span></div>'.format(tag=tag, name=name)
            date = QtCore.QDateTime.fromString(release['published_at'], 'yyyy-MM-ddTHH:mm:ssZ').toString('dd/MM/yyyy')
            html += u'<div class="release">Release date: {date}<br/>'.format(date=date)
            html += 'Availability: <ul>'

            base = 'https://github.com/MaurizioB/Bigglesworth/archive/{}.{}'
            html += '<li>Linux (source): <a href="{tar}">tar</a>, <a href="{zip}">zip</a></li>'.format(
                tar=base.format(tag, 'tar.gz'), zip=base.format(tag, 'zip'))
#                tar=release['tarball_url'], zip=release['zipball_url'])

            for asset in release['assets']:
                file_name = asset['name'].lower()
                if file_name.endswith('.exe') or file_name.endswith('.msi'):
                    os = 'Windows'
                    if tag == latest and sys.platform == 'win32':
                        self.downloadUrl = asset['browser_download_url']
                elif file_name.endswith('.dmg'):
                    os = 'OSX'
                    if tag == latest and sys.platform == 'darwin':
                        self.downloadUrl = asset['browser_download_url']
                html += u'<li>{os}: <a href="{url}">Direct link</a></li>'.format(os=os, url=asset['browser_download_url'])

            html += '</ul>'
            html += '</div>'
            md = markdown2.Markdown(extras=['cuddled-lists'])
            body = md.convert(re.sub(r'(?<=[a-zA-Z0-9\.\;])\r?\n(?<![a-zA-Z0-9])', '    \n', release['body']))
            html += u'<div class="content">{body}</div>'.format(body=body)
            if i < len(contents) - 1:
                html += '<hr/>'
            else:
                html += '<br/>'
        if older_tag:
            html += '</font>'

        self.infoText.setHtml(html)

    def startRequest(self):
        self.loader.show()
        if self.updateChecker:
            self.disconnectRequest()
        self.infoText.setHtml('')
        self.updateChecker = UpdateChecker()
        self.updateCheckerThread = QtCore.QThread()
        self.updateChecker.moveToThread(self.updateCheckerThread)
        self.updateChecker.error.connect(self.checkError)
        self.updateChecker.result.connect(self.processResult)
        self.updateChecker.finished.connect(self.updateCheckerThread.quit)
        self.updateCheckerThread.started.connect(self.updateChecker.run)
        self.updateCheckerThread.start()

    def exec_(self, result=None):
        self.show()
        if not result:
            QtCore.QTimer.singleShot(0, self.startRequest)
        else:
            self.processResult(result)
        QtWidgets.QDialog.exec_(self)
