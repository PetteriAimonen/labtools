import pyvisa as visa
import functools
import time

class RelayMux:
    '''Interface to 2x4 relay mux.'''

    def __init__(self, path = "ASRL/dev/instruments/relaymux::INSTR"):
        self.path = path
    
    @functools.cached_property
    def port(self):
        '''Open port on first access'''
        self.visa = visa.ResourceManager("@py")
        port = self.visa.open_resource(self.path, baud_rate = 115200)

        idn_response = port.query("*IDN?")
        if 'RelayMux' not in idn_response:
            raise Exception("Unknown IDN: " + idn_response)
        
        return port
    
    def close(self, channels):
        '''Close one or multiple channels'''
        if isinstance(channels, int): channels = [channels]
        self.port.write("CLOSE (@%s)" % ','.join(str(x) for x in channels))

    def open(self, channels):
        '''Open one or multiple channels'''
        if isinstance(channels, int): channels = [channels]
        self.port.write("OPEN (@%s)" % ','.join(str(x) for x in channels))

    def open_all(self):
        self.port.write("OPEN:ALL")
    
    def get(self):
        '''Get relay states as integer'''
        return int(self.port.query('ROUTE:GET?'))
    
    def set(self, state):
        '''Set relay states as integer'''
        self.port.write("ROUTE:SET %d" % state)

if __name__ == '__main__':
    import sys
    p = RelayMux()

    if len(sys.argv) > 1:
        p.set(int(sys.argv[1], 0))
    else:
        print(hex(p.get()))

