import pyvisa as visa
import functools
import time

class ET5410:
    '''Interface to MUSTOOL / East Tester ET5410A+ electronic load.'''

    def __init__(self, path = "ASRL/dev/instruments/ET5410::INSTR"):
        self.path = path
    
    @functools.cached_property
    def port(self):
        '''Open port on first access'''
        self.visa = visa.ResourceManager("@py")
        port = self.visa.open_resource(self.path, baud_rate = 9600, read_termination = '\n', write_termination = '\n')

        idn_response = port.query("*IDN?")
        if 'V1.0' not in idn_response:
            idn_response = port.query("*IDN?")
            if 'V1.0' not in idn_response:
                raise Exception("Unknown IDN: " + idn_response)
        
        return port

    def set_cc(self, current):
        '''Set constant current mode'''
        self.port.write("CH:MODE CC")
        self.port.write("CURR:CC %0.3f" % float(current))
    
    def set_cccv(self, current, voltage):
        '''Set constant current / constant voltage mode'''
        self.port.write("CH:MODE CCCV")
        self.port.write("CURR:CCCV %0.3f" % float(current))
        self.port.write("VOLT:CCCV %0.3f" % float(voltage))

    def is_on(self):
        return 'ON' in self.port.query("CH:SW?")
    
    def output_on(self):
        self.port.write("CH:SW ON")
    
    def output_off(self):
        self.port.write("CH:SW OFF")
    
    def measure_voltage(self):
        return float(self.port.query("MEAS:VOLT?").strip("R"))
    
    def measure_current(self):
        return float(self.port.query("MEAS:CURR?").strip("R"))

if __name__ == '__main__':
    p = ET5410()
    while True:
        print("%6.3f V, %6.3f A" % (p.measure_voltage(), p.measure_current()))
        time.sleep(1)
