from Qt import QtCore, QtGui, QtWidgets

from bigglesworth.utils import loadUi, localPath, setBold

class MidiConnectionsDialog(QtWidgets.QDialog):
    def __init__(self, main, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        self.setWindowTitle('MIDI connections')
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        self.midiConnectionWidget = MidiConnectionsWidget()
        layout.addWidget(self.midiConnectionWidget)
        self.midiConnectionWidget.setMain(main)
#        self.midiConnectionWidget.midiConnect.connect(main.editorWindow.midiConnect)
        self.midiConnectionWidget.midiConnect.connect(main.midiConnect)


class MidiConnectionsWidget(QtWidgets.QWidget):
    midiConnect = QtCore.pyqtSignal(object, int, bool)

    def __init__(self, *args, **kwargs):
        QtWidgets.QWidget.__init__(self, *args, **kwargs)
        loadUi(localPath('ui/midiconnections.ui'), self)
        self.refreshBtn.clicked.connect(self.refresh)

        self.inputModel = QtGui.QStandardItemModel()
        self.inputTreeView.setModel(self.inputModel)
        self.inputTreeView.doubleClicked.connect(self.doubleClicked)
        self.inputTreeView.customContextMenuRequested.connect(self.contextMenu)

        self.outputModel = QtGui.QStandardItemModel()
        self.outputTreeView.setModel(self.outputModel)
        self.outputTreeView.doubleClicked.connect(self.doubleClicked)
        self.outputTreeView.customContextMenuRequested.connect(self.contextMenu)

    def focusInEvent(self, event):
        #TODO: fix next widget focus
        QtWidgets.QWidget.focusInEvent(self, event)
        self.inputTreeView.setFocus()

    def doubleClicked(self, index):
        if not index.isValid():
            return
        view = self.sender()
        item = view.model().itemFromIndex(index)
        if not item.isEnabled():
            return
        direction = True if view == self.outputTreeView else False
        port = item.data()
        if direction:
            connected = any([True for conn in port.connections.input if conn.src == self.main.midiDevice.output])
        else:
            connected = any([True for conn in port.connections.output if conn.dest == self.main.midiDevice.input])
        self.midiConnect.emit(port, direction, not connected)

    def contextMenu(self, pos):
        view = self.sender()
        direction = True if view == self.outputTreeView else False
        index = view.indexAt(pos)
        if not index.isValid():
            return

        item = view.model().itemFromIndex(index)
        menu = QtWidgets.QMenu()

        if item.isEnabled():
            connected = index.data(QtCore.Qt.FontRole).bold()
            portAction = menu.addAction('Disconnect' if connected else 'Connect')
            port = item.data()
        else:
            portAction = None

        disconnectAllAction = menu.addAction('Disconnect all')
        if view == self.inputTreeView:
            if not any(conn for conn in self.main.midiDevice.input.connections.input if not conn.hidden):
                disconnectAllAction.setEnabled(False)
        elif not any(conn for conn in self.main.midiDevice.output.connections.output if not conn.hidden):
            disconnectAllAction.setEnabled(False)

        res = menu.exec_(view.viewport().mapToGlobal(pos))
        if not res:
            return
        elif res == portAction:
            self.midiConnect.emit(port, direction, not connected)
        elif res == disconnectAllAction:
            if direction:
                ports = [conn.dest for conn in self.main.midiDevice.output.connections.output if not conn.hidden]
            else:
                ports = [conn.src for conn in self.main.midiDevice.input.connections.input if not conn.hidden]
            for port in ports:
#                print(port)
                self.midiConnect.emit(port, direction, False)

    def setMain(self, main):
        self.main = main
        self.backend = self.main.midiDevice.mode
        self.input = self.main.midiDevice.input
        self.output = self.main.midiDevice.output
        self.graph = self.main.graph
        self.graph.graph_changed.connect(self.refresh)
        self.refresh()

    def unsetMain(self):
        self.graph.graph_changed.disconnect(self.refresh)

    def refresh(self):
        inPos = self.inputTreeView.verticalScrollBar().value()
        outPos = self.outputTreeView.verticalScrollBar().value()
        self.inputModel.clear()
        self.outputModel.clear()
        self.clientList = [[], []]
        inConn = 0
        outConn = 0
        for client in [self.main.graph.client_id_dict[cid] for cid in sorted(self.main.graph.client_id_dict.keys())]:
            if client in (self.main.midiDevice.input.client, self.main.midiDevice.output.client):
                continue
            in_ports = []
            out_ports = []
            for port in client.ports:
                if port.hidden:
                    continue
                if port.is_input:
                    in_ports.append(port)
                if port.is_output:
                    out_ports.append(port)
            if in_ports:
                self.clientList[1].append((client, in_ports))
                clientItem = QtGui.QStandardItem(client.name)
                clientItem.setData('<b>Client:</b> {c}<br/><b>Address:</b> {cid}'.format(c=client.name, cid=client.id), QtCore.Qt.ToolTipRole)
                clientItem.setEnabled(False)
                for port in in_ports:
                    portItem = QtGui.QStandardItem(port.name)
                    connected = any([True for conn in port.connections.input if conn.src == self.main.midiDevice.output])
                    setBold(portItem, connected)
                    if connected:
                        outConn += 1
                    portItem.setData('<b>Client:</b> {c}<br/><b>Port:</b> {p}<br/><b>Address:</b> {cid}:{pid}'.format(
                        c=client.name, p=port.name, cid=client.id, pid=port.id), QtCore.Qt.ToolTipRole)
                    portItem.setData(port)
                    clientItem.appendRow(portItem)
                self.outputModel.appendRow(clientItem)
            if out_ports:
                self.clientList[1].append((client, out_ports))
                clientItem = QtGui.QStandardItem(client.name)
                clientItem.setData(u'<b>Client:</b> {name}<br/><b>Address:</b> {id}'.format(name=client.name, id=client.id), QtCore.Qt.ToolTipRole)
                clientItem.setEnabled(False)
                for port in out_ports:
                    portItem = QtGui.QStandardItem(port.name)
                    connected = any([True for conn in port.connections.output if conn.dest == self.main.midiDevice.input])
                    setBold(portItem, connected)
                    if connected:
                        inConn += 1
                    portItem.setData(u'<b>Client:</b> {c}<br/><b>Port:</b> {p}<br/><b>Address:</b> {cid}:{pid}'.format(
                        c=client.name, p=port.name, cid=client.id, pid=port.id), QtCore.Qt.ToolTipRole)
                    portItem.setData(port)
                    clientItem.appendRow(portItem)
                self.inputModel.appendRow(clientItem)
        self.inputTreeView.expandAll()
        self.outputTreeView.expandAll()

        self.inputModel.setHeaderData(0, QtCore.Qt.Horizontal, 'Input ({})'.format(inConn if inConn else 'not connected'))
        self.inputModel.setHeaderData(0, QtCore.Qt.Horizontal, QtCore.Qt.AlignCenter, QtCore.Qt.TextAlignmentRole)
        self.outputModel.setHeaderData(0, QtCore.Qt.Horizontal, 'Output ({})'.format(outConn if outConn else 'not connected'))
        self.outputModel.setHeaderData(0, QtCore.Qt.Horizontal, QtCore.Qt.AlignCenter, QtCore.Qt.TextAlignmentRole)

        self.inputTreeView.verticalScrollBar().setValue(inPos)
        self.outputTreeView.verticalScrollBar().setValue(outPos)

