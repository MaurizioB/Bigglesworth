import os, sys
from time import sleep

from Qt import QtCore

from bigglesworth.utils import Enum
from bigglesworth.midiutils import Graph, MidiEvent

#if not 'linux' in sys.platform or (os.environ.has_key('MIDI_BACKEND') and os.environ['MIDI_BACKEND'] == 'RTMIDI'):
#    import rtmidi
#else:
#    from pyalsa import alsaseq
import rtmidi
try:
    from pyalsa import alsaseq
except:
    pass
INPUT, OUTPUT = xrange(2)


class RtMidiSequencer(QtCore.QObject):
    ''' A fake sequencer object that emulates ALSA sequencer'''
    conn_created = QtCore.pyqtSignal(object)
    conn_destroyed = QtCore.pyqtSignal(object)
    client_created = QtCore.pyqtSignal(object)
    client_destroyed = QtCore.pyqtSignal(object)
    port_created = QtCore.pyqtSignal(object)
    port_destroyed = QtCore.pyqtSignal(object)
    midi_event = QtCore.pyqtSignal(object, object)

    def __init__(self, clientname):
        QtCore.QObject.__init__(self)
        self.clientname = clientname
        self.api = rtmidi.get_compiled_api()[0]
        self.listener_in = rtmidi.MidiIn(self.api, clientname)
        self.listener_in.ignore_types(sysex=False)
        self.listener_out = rtmidi.MidiOut(self.api, clientname)
        self.ports = {INPUT: [self.listener_in], OUTPUT: [self.listener_out]}
        self.connections = {self.listener_in: None, self.listener_out: None}
        self.default_in_caps = 66
        self.default_out_caps = 33
        self.default_type = 1048578
#        self.alsa_mode = True if 'linux' in sys.platform else False
        self.in_graph_dict = {}
        self.out_graph_dict = {}
        self.client_dict = {}
        self.knownPorts = None

    def getInPorts(self):
        return map(lambda p: p.decode('utf-8'), self.listener_in.get_ports(None))

    def getOutPorts(self):
        return map(lambda p: p.decode('utf-8'), self.listener_out.get_ports(None))

    def getPorts(self):
        return (map(lambda p: p.decode('utf-8'), self.listener_in.get_ports(None)), 
            map(lambda p: p.decode('utf-8'), self.listener_out.get_ports(None)))

    def update_graph(self):
        currentPorts = self.getPorts()
        if currentPorts == self.knownPorts:
            return
        self.knownPorts = currentPorts
        previous_out_clients = self.out_graph_dict.keys()
        previous_in_clients = self.in_graph_dict.keys()
        for previous_list in previous_out_clients, previous_in_clients:
            for port_name in previous_list:
                if port_name.startswith('Bigglesworth'):
                    previous_list.pop(previous_list.index(port_name))
        new_out_clients = []
        for port_name in currentPorts[0]:
            if port_name.startswith('Bigglesworth'):
                continue
            if port_name in previous_out_clients:
                previous_out_clients.pop(previous_out_clients.index(port_name))
            else:
                new_out_clients.append(port_name)
        if previous_out_clients:
            for port_name in previous_out_clients:
                self.out_graph_dict.pop(port_name)
                client_id = self.client_dict.keys()[self.client_dict.values().index(port_name)]
                self.client_dict.pop(client_id)
                self.port_destroyed.emit({'addr.client': client_id, 'addr.port': 0})
                self.client_destroyed.emit({'addr.client': client_id})
        new_index = max(self.client_dict.keys()) + 1
        if new_out_clients:
            for port_name in new_out_clients:
                self.client_dict[new_index] = port_name
                self.out_graph_dict[port_name] = new_index
                self.client_created.emit({'addr.client': new_index})
                self.port_created.emit({'addr.client': new_index, 'addr.port': 0})
                new_index += 1

        new_in_clients = []
        for port_name in currentPorts[1]:
            if port_name.startswith('Bigglesworth'):
                continue
            if port_name in previous_in_clients:
                previous_in_clients.pop(previous_in_clients.index(port_name))
            else:
                new_in_clients.append(port_name)
        if previous_in_clients:
            for port_name in previous_in_clients:
                self.in_graph_dict.pop(port_name)
                client_id = self.client_dict.keys()[self.client_dict.values().index(port_name)]
                self.client_dict.pop(client_id)
                self.port_destroyed.emit({'addr.client': client_id, 'addr.port': 0})
                self.client_destroyed.emit({'addr.client': client_id})
        if new_in_clients:
            for port_name in new_in_clients:
                self.client_dict[new_index] = port_name
                self.in_graph_dict[port_name] = new_index
                self.client_created.emit({'addr.client': new_index})
                self.port_created.emit({'addr.client': new_index, 'addr.port': 0})
                new_index += 1

    def connection_list(self):
        res_list = []
#        if self.alsa_mode:
#        res_list.append(('Bigglesworth:input', 0, [('Bigglesworth:input', 0, ([], []))]))
        input_name = self.clientname + ':input'
        self.client_dict[0] = input_name
        self.in_graph_dict[input_name] = 0
#        res_list.append(('Bigglesworth:output', 0, [('Bigglesworth:output', 1, ([], []))]))
        output_name = self.clientname + ':output'
        self.client_dict[1] = output_name
        self.out_graph_dict[output_name] = 1
        in_id = 2
        inPorts, outPorts = self.getPorts()
        for in_id, port_name in enumerate(inPorts, in_id):
            self.out_graph_dict[port_name] = in_id
            self.client_dict[in_id] = port_name
        for out_id, port_name in enumerate(outPorts, in_id + 1):
            self.in_graph_dict[port_name] = out_id
            self.client_dict[out_id] = port_name
        for client_id, name in self.client_dict.items():
            res_list.append((name, client_id, [(name, 0, ([], []))]))
        return res_list

    def get_client_info(self, client_id):
        if not client_id in self.client_dict:
            raise BaseException
        return {
                'name': self.client_dict[client_id], 
                'id': client_id, 
                'broadcast_filter': 0, 
                'error_bounce': 0, 
                'event_filter': '', 
                'event_lost': 0, 
                'num_ports': 1, 
                'type': 2
                }

    def get_port_info(self, port_id, client_id):
        if client_id in self.in_graph_dict.values():
            caps = self.default_in_caps
        else:
            caps = self.default_out_caps
        return {
                'capability': caps, 
                'name': self.client_dict[client_id], 
                'type': self.default_type, 
                }

    def connect_ports(self, source, dest, *args):
        source = source[0]
        dest = dest[0]
        if source == 1:
            for port in self.ports[OUTPUT]:
                if self.connections[port]: continue
                break
            else:
                port = rtmidi.MidiOut(self.api, 'Bigglesworth')
                port.set_error_callback(self.error_callback, (port, source))
                self.ports[OUTPUT].append(port)
            dest_name = self.client_dict[dest]
#            port.open_port(port.get_ports(None).index(dest_name), 'output')
            port.open_port(self.getOutPorts().index(dest_name), 'output')
            self.connections[port] = dest_name
            self.conn_created.emit({'connect.sender.client': 1, 'connect.sender.port': 0, 'connect.dest.client': dest, 'connect.dest.port': 0})

        else:
            for port in self.ports[INPUT]:
                if self.connections[port]: continue
                break
            else:
                port = rtmidi.MidiIn(self.api, 'Bigglesworth')
                port.ignore_types(sysex=False)
                self.ports[INPUT].append(port)
            source_name = self.client_dict[source]
            try:
#                port.open_port(port.get_ports(None).index(source_name), 'input')
                port.open_port(self.getInPorts().index(source_name), 'input')
                port.set_callback(self.midi_event.emit, source)
                port.set_error_callback(self.error_callback, (port, source))
                self.connections[port] = source_name
                self.conn_created.emit({'connect.sender.client': source, 'connect.sender.port': 0, 'connect.dest.client': 0, 'connect.dest.port': 0})
            except:
                print('connection not created')

    def error_callback(self, errType, errMsg, data):
        print('ERROR!!!', errType, errMsg, data)

    def disconnect_ports(self, source, dest):
        print('rtmidi disconnect method', source, dest)
        source = source[0]
        dest = dest[0]
        if source == 1:
            target_name = self.client_dict[dest]
        else:
            target_name = self.client_dict[source]
        for port, dest in self.connections.items():
            if target_name == dest:
                print(u'rtmidi closing port "{}" target "{}"'.format(port, target_name))
                print('port is open?', port.is_port_open())
                try:
                    #TODO: let's understand better what's going on here and why sometimes this hangs...
                    port.close_port()
                    print('rtmidi port closed!')
                    self.connections[port] = None
                except Exception as e:
                    print('rtmidi port not closed. mmmh...', e)
                break
        else:
#            raise rtmidi.RtMidiError('Error disconnecting ports')
#            print 'connection already removed?'
            print('rtmidi something strange happening?')
            return
        print('rtmidi emitting destroyed signal')
        if source == 1:
            self.conn_destroyed.emit({'connect.sender.client': 1, 'connect.sender.port': 0, 'connect.dest.client': dest, 'connect.dest.port': 0})
        else:
            self.conn_destroyed.emit({'connect.sender.client': source, 'connect.sender.port': 0, 'connect.dest.client': 0, 'connect.dest.port': 0})

    def get_connect_info(self, source, dest):
        source = source[0]
        dest = dest[0]
        if source == 1:
            target_name = self.client_dict[dest]
        else:
            target_name = self.client_dict[source]
        for port, dest in self.connections.items():
            if target_name == dest:
#                port.close_port()
#                self.connections[port] = None
                break
        else:
#            print 'connection does not exist'
            raise rtmidi.RtMidiError('Connection does not exist')
        return {'exclusive': 0, 'queue': 0, 'time_real': 0, 'time_update': 0}


class MidiDevice(QtCore.QObject):
    client_start = QtCore.pyqtSignal(object)
    client_exit = QtCore.pyqtSignal(object)
    port_start = QtCore.pyqtSignal(object)
    port_exit = QtCore.pyqtSignal(object)
    conn_register = QtCore.pyqtSignal(object, bool)
    graph_changed = QtCore.pyqtSignal()
    stopped = QtCore.pyqtSignal()
    midi_event = QtCore.pyqtSignal(object)
    Alsa, RtMidi = Enum(2)

    def __init__(self, main, mode):
        QtCore.QObject.__init__(self)
        self.main = main
        self.mode = mode
        self.active = False
        self.keep_going = True
        self.sysex_buffer = []
        if mode == self.Alsa:
            self.backend = self.Alsa
            self.seq = alsaseq.Sequencer(clientname='Bigglesworth')
            input_id = self.seq.create_simple_port(
                name='input', 
                type=alsaseq.SEQ_PORT_TYPE_MIDI_GENERIC|alsaseq.SEQ_PORT_TYPE_APPLICATION, 
                caps=alsaseq.SEQ_PORT_CAP_WRITE|alsaseq.SEQ_PORT_CAP_SUBS_WRITE|
                alsaseq.SEQ_PORT_CAP_SYNC_WRITE)
            output_id = self.seq.create_simple_port(name='output', 
                                                    type=alsaseq.SEQ_PORT_TYPE_MIDI_GENERIC|alsaseq.SEQ_PORT_TYPE_APPLICATION, 
                                                    caps=alsaseq.SEQ_PORT_CAP_READ|alsaseq.SEQ_PORT_CAP_SUBS_READ|
                                                    alsaseq.SEQ_PORT_CAP_SYNC_READ)

            self.seq.connect_ports((alsaseq.SEQ_CLIENT_SYSTEM, alsaseq.SEQ_PORT_SYSTEM_ANNOUNCE), (self.seq.client_id, input_id))

            self.graph = Graph(self.seq)
            self.graph.conn_register.connect(self.conn_register)
            self.id = self.seq.client_id
            self.input = self.graph.port_id_dict[self.id][input_id]
            self.output = self.graph.port_id_dict[self.id][output_id]
            self.run = self.runAlsa
        else:
            self.backend = self.RtMidi
            self.seq = RtMidiSequencer(clientname='Bigglesworth')
            self.graph = Graph(self.seq)
            self.seq.client_created.connect(self.graph.client_created)
            self.seq.client_destroyed.connect(self.graph.client_destroyed)
            self.seq.port_created.connect(self.graph.port_created)
            self.seq.port_destroyed.connect(self.graph.port_destroyed)
            self.seq.conn_created.connect(self.graph.conn_created)
            self.seq.conn_destroyed.connect(self.graph.conn_destroyed)
            self.seq.midi_event.connect(self.create_midi_event)
            self.input = self.graph.port_id_dict[0][0]
            self.output = self.graph.port_id_dict[1][0]
            self.run = self.runRtMidi

    def runAlsa(self):
        self.active = True
        while self.keep_going:
            try:
                event_list = self.seq.receive_events(timeout=1024, maxevents=1)
                for event in event_list:
                    data = event.get_data()
                    if event.type == alsaseq.SEQ_EVENT_CLIENT_START:
                        self.graph.client_created(data)
                    elif event.type == alsaseq.SEQ_EVENT_CLIENT_EXIT:
                        self.graph.client_destroyed(data)
                    elif event.type == alsaseq.SEQ_EVENT_PORT_START:
                        self.graph.port_created(data)
                    elif event.type == alsaseq.SEQ_EVENT_PORT_EXIT:
                        self.graph.port_destroyed(data)
                    elif event.type == alsaseq.SEQ_EVENT_PORT_SUBSCRIBED:
                        self.graph.conn_created(data)
                    elif event.type == alsaseq.SEQ_EVENT_PORT_UNSUBSCRIBED:
                        self.graph.conn_destroyed(data)
                    elif event.type in [alsaseq.SEQ_EVENT_NOTEON, alsaseq.SEQ_EVENT_NOTEOFF, 
                                        alsaseq.SEQ_EVENT_CONTROLLER, alsaseq.SEQ_EVENT_PGMCHANGE,
                                        ]:
                        try:
                            newev = MidiEvent.from_alsa(event)
                            self.midi_event.emit(newev)
#                            print newev
                        except Exception as e:
                            print 'event {} unrecognized'.format(event)
                            print e
                    elif event.type in [alsaseq.SEQ_EVENT_CLOCK, alsaseq.SEQ_EVENT_SENSING]:
                        pass
                    elif event.type == alsaseq.SEQ_EVENT_SYSEX:
                        self.sysexCheck(event)
            except Exception as e:
                print e
                print 'something is wrong'
#        print 'stopped'
        print 'exit'
        del self.seq
        self.stopped.emit()

    def create_midi_event(self, dataTuple, sourceId):
        data, time = dataTuple
        newev = MidiEvent.from_binary(data)
        newev.source = (sourceId, 0)
        self.midi_event.emit(newev)

    def runRtMidi(self):
        self.active = True
        while self.keep_going:
            try:
                #better use qtimer in seq
                sleep(.5)
                self.seq.update_graph()
            except Exception as e:
                print e
                print 'something is wrong'
#        print 'stopped'
        print 'exit'
        del self.seq
        self.stopped.emit()

    def sysexCheck(self, event):
        data = event.get_data()['ext']
        try:
            if data[0] == 0xf0:
                self.buffer = data
            else:
                self.buffer.extend(data)
#            print 'sysex message length: {}'.format(len(self.buffer))
            if data[-1] != 0xf7:
                return
            else:
                sysex = MidiEvent.from_alsa(event)
                sysex.sysex = self.buffer
                self.midi_event.emit(sysex)
                self.buffer = []
        except Exception as Err:
            print len(self.buffer)
            print Err



