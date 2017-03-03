from PyQt4 import QtCore
from pyalsa import alsaseq

from midiutils import *

class AlsaMidi(QtCore.QObject):
    client_start = QtCore.pyqtSignal(object)
    client_exit = QtCore.pyqtSignal(object)
    port_start = QtCore.pyqtSignal(object)
    port_exit = QtCore.pyqtSignal(object)
    conn_register = QtCore.pyqtSignal(object, bool)
    graph_changed = QtCore.pyqtSignal()
    stopped = QtCore.pyqtSignal()
    midi_event = QtCore.pyqtSignal(object)

    def __init__(self, main):
        QtCore.QObject.__init__(self)
        self.main = main
        self.active = False
        self.sysex_buffer = []
        self.seq = alsaseq.Sequencer(clientname='Bigglesworth')
        self.keep_going = True
        input_id = self.seq.create_simple_port(name = 'input', 
                                                 type = alsaseq.SEQ_PORT_TYPE_MIDI_GENERIC|alsaseq.SEQ_PORT_TYPE_APPLICATION, 
                                                 caps = alsaseq.SEQ_PORT_CAP_WRITE|alsaseq.SEQ_PORT_CAP_SUBS_WRITE|
                                                 alsaseq.SEQ_PORT_CAP_SYNC_WRITE)
        output_id = self.seq.create_simple_port(name = 'output', 
                                                     type = alsaseq.SEQ_PORT_TYPE_MIDI_GENERIC|alsaseq.SEQ_PORT_TYPE_APPLICATION, 
                                                     caps = alsaseq.SEQ_PORT_CAP_READ|alsaseq.SEQ_PORT_CAP_SUBS_READ|
                                                     alsaseq.SEQ_PORT_CAP_SYNC_READ)

        self.seq.connect_ports((alsaseq.SEQ_CLIENT_SYSTEM, alsaseq.SEQ_PORT_SYSTEM_ANNOUNCE), (self.seq.client_id, input_id))
#        self.seq.connect_ports((16, 0), (self.seq.client_id, input_id))
#        self.seq.connect_ports((self.seq.client_id, output_id), (130, 0))
#        self.seq.connect_ports((self.seq.client_id, output_id), (132, 0))

        self.graph = self.main.graph = Graph(self.seq)
#        self.graph.client_start.connect(self.client_start)
#        self.graph.client_exit.connect(self.client_exit)
#        self.graph.port_start.connect(self.port_start)
#        self.graph.port_exit.connect(self.port_exit)
        self.graph.conn_register.connect(self.conn_register)
        self.id = self.seq.client_id
        self.input = self.graph.port_id_dict[self.id][input_id]
        self.output = self.graph.port_id_dict[self.id][output_id]

    def run(self):
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
                        self.check(event)
            except Exception as e:
                print e
                print 'something is wrong'
#        print 'stopped'
        print 'exit'
        del self.seq
        self.stopped.emit()

    def check(self, event):
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
