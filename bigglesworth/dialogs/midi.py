# *-* coding: utf-8 *-*

from PyQt4 import QtCore, QtGui
from bigglesworth.const import ClientRole, PortRole
from bigglesworth.utils import setBold

class MidiWidget(QtGui.QWidget):
    def __init__(self, main):
        QtGui.QDialog.__init__(self, parent=None)
        self.main = main

        layout = QtGui.QGridLayout()
        self.setLayout(layout)
        self.input_lbl = QtGui.QLabel('INPUT')
        layout.addWidget(self.input_lbl, 0, 0, QtCore.Qt.AlignHCenter)
        self.input_listview = QtGui.QListView(self)
        self.input_listview.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.input_listview.setEditTriggers(QtGui.QListView.NoEditTriggers)
        layout.addWidget(self.input_listview, 1, 0)
        line = QtGui.QFrame()
        line.setFrameShape(QtGui.QFrame.VLine)
        layout.addWidget(line, 0, 1, 2, 1)
        self.output_lbl = QtGui.QLabel('OUTPUT')
        layout.addWidget(self.output_lbl, 0, 2, QtCore.Qt.AlignHCenter)
        self.output_listview = QtGui.QListView(self)
        self.output_listview.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.output_listview.setEditTriggers(QtGui.QListView.NoEditTriggers)
        layout.addWidget(self.output_listview, 1, 2)
        self.refresh_btn = QtGui.QPushButton('Refresh')
        layout.addWidget(self.refresh_btn, 2, 0, 1, 3)

        self.graph = self.main.graph
        self.input = self.main.input
        self.output = self.main.output
        self.graph.graph_changed.connect(self.refresh_all)
        self.refresh_all()
        self.refresh_btn.clicked.connect(self.refresh_all)

        self.input_listview.doubleClicked.connect(self.port_connect_toggle)
        self.output_listview.doubleClicked.connect(self.port_connect_toggle)
        self.input_listview.customContextMenuRequested.connect(self.port_menu)
        self.output_listview.customContextMenuRequested.connect(self.port_menu)

    def _get_port_from_item_data(self, model, index):
        return self.graph.port_id_dict[model.data(index, ClientRole).toInt()[0]][model.data(index, PortRole).toInt()[0]]

    def showEvent(self, event):
        if self.input_model.rowCount():
            self.input_listview.setMinimumHeight(self.input_listview.sizeHintForRow(0)*12)
        elif self.input_model.rowCount():
            self.output_listview.setMinimumHeight(self.output_listview.sizeHintForRow(0)*12)
        self.setMinimumWidth(400)

    def port_menu(self, pos):
        sender = self.sender()
        model = sender.model()
        index = sender.indexAt(pos)
        item = model.item(index.row())
        actions = []
        if item.isEnabled():
            port = self._get_port_from_item_data(model, index)
            if (sender == self.input_listview and self.input in [conn.dest for conn in port.connections.output]) or\
                (sender == self.output_listview and self.output in [conn.src for conn in port.connections.input]):
                disconnect_action = QtGui.QAction('Disconnect', self)
                disconnect_action.triggered.connect(lambda: self.port_connect_toggle(index, sender))
                actions.append(disconnect_action)
            else:
                connect_action = QtGui.QAction('Connect', self)
                connect_action.triggered.connect(lambda: self.port_connect_toggle(index, sender))
                actions.append(connect_action)
            sep = QtGui.QAction(self)
            sep.setSeparator(True)
            actions.append(sep)
        disconnect_all_action = QtGui.QAction('Disconnect all', self)
        actions.append(disconnect_all_action)
        if sender == self.input_listview:
            disconnect_all_action.triggered.connect(lambda: self.input.disconnect_all())
        elif sender == self.output_listview:
            disconnect_all_action.triggered.connect(lambda: self.output.disconnect_all())

        menu = QtGui.QMenu()
        menu.addActions(actions)
        menu.exec_(sender.mapToGlobal(pos))

    def port_connect_toggle(self, index, sender=None):
        if sender is None:
            sender = self.sender()
        if sender == self.input_listview:
            port = self._get_port_from_item_data(self.input_model, index)
            if self.input in [conn.dest for conn in port.connections.output]:
                port.disconnect(self.input)
            else:
                port.connect(self.input)
        elif sender == self.output_listview:
            port = self._get_port_from_item_data(self.output_model, index)
            if self.output in [conn.src for conn in port.connections.input]:
                self.output.disconnect(port)
            else:
                self.output.connect(port)

    def refresh_all(self):
        self.input_model = QtGui.QStandardItemModel()
        self.input_listview.setModel(self.input_model)
        self.output_model = QtGui.QStandardItemModel()
        self.output_listview.setModel(self.output_model)
        for client in [self.graph.client_id_dict[cid] for cid in sorted(self.graph.client_id_dict.keys())]:
            in_port_list = []
            out_port_list = []
            for port in client.ports:
                if port.hidden or port.client == self.main.input.client:
                    continue
                if port.is_output:
                    in_port_list.append(port)
                if port.is_input:
                    out_port_list.append(port)
            if len(in_port_list):
                in_client_item = QtGui.QStandardItem(client.name)
                in_client_item.setData('<b>Client:</b> {c}<br/><b>Address:</b> {cid}'.format(c=client.name, cid=client.id), QtCore.Qt.ToolTipRole)
                self.input_model.appendRow(in_client_item)
                in_client_item.setEnabled(False)
                for port in in_port_list:
                    in_item = QtGui.QStandardItem('  {}'.format(port.name))
                    in_item.setData('<b>Client:</b> {c}<br/><b>Port:</b> {p}<br/><b>Address:</b> {cid}:{pid}'.format(
                                                                                                               c=client.name, 
                                                                                                               p=port.name, 
                                                                                                               cid=client.id, 
                                                                                                               pid=port.id), 
                                                                                                               QtCore.Qt.ToolTipRole)
                    in_item.setData(QtCore.QVariant(client.id), ClientRole)
                    in_item.setData(QtCore.QVariant(port.id), PortRole)
                    self.input_model.appendRow(in_item)
                    if any([conn for conn in port.connections.output if conn.dest == self.input]):
                        in_item.setData(QtGui.QBrush(QtCore.Qt.blue), QtCore.Qt.ForegroundRole)
                        setBold(in_item)
                    else:
                        in_item.setData(QtGui.QBrush(QtCore.Qt.black), QtCore.Qt.ForegroundRole)
                        setBold(in_item, False)
            if len(out_port_list):
                out_client_item = QtGui.QStandardItem(client.name)
                out_client_item.setData('<b>Client:</b> {c}<br/><b>Address:</b> {cid}'.format(c=client.name, cid=client.id), QtCore.Qt.ToolTipRole)
                self.output_model.appendRow(out_client_item)
                out_client_item.setEnabled(False)
                for port in out_port_list:
                    out_item = QtGui.QStandardItem('  {}'.format(port.name))
                    out_item.setData('<b>Client:</b> {c}<br/><b>Port:</b> {p}<br/><b>Address:</b> {cid}:{pid}'.format(
                                                                                                               c=client.name, 
                                                                                                               p=port.name, 
                                                                                                               cid=client.id, 
                                                                                                               pid=port.id), 
                                                                                                               QtCore.Qt.ToolTipRole)
                    out_item.setData(QtCore.QVariant(client.id), ClientRole)
                    out_item.setData(QtCore.QVariant(port.id), PortRole)
                    self.output_model.appendRow(out_item)
                    if any([conn for conn in port.connections.input if conn.src == self.output]):
                        out_item.setData(QtGui.QBrush(QtCore.Qt.blue), QtCore.Qt.ForegroundRole)
                        setBold(out_item)
                    else:
                        out_item.setData(QtGui.QBrush(QtCore.Qt.black), QtCore.Qt.ForegroundRole)
                        setBold(out_item, False)

        cx_text = [
                   (self.input.connections.input, self.input_lbl, 'INPUT'), 
                   (self.output.connections.output, self.output_lbl, 'OUTPUT'), 
                   ]
        for cx, lbl, ptxt in cx_text:
            n_conn = len([conn for conn in cx if not conn.hidden])
            cx_txt = ptxt
            if not n_conn:
                cx_txt += ' (not connected)'
            elif n_conn == 1:
                cx_txt += ' (1 connection)'
            else:
                cx_txt += ' ({} connections)'.format(n_conn)
            lbl.setText(cx_txt)

class MidiDialog(QtGui.QDialog):
    def __init__(self, main, parent):
        QtGui.QDialog.__init__(self, parent)
        self.main = main
        self.setModal(True)
        layout = QtGui.QVBoxLayout()
        self.setLayout(layout)

    def show(self):
        self.layout().addWidget(self.main.midiwidget)
        QtGui.QDialog.show(self)

