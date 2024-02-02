import pyvisa as visa
import functools
import time

class P4603:
    '''Interface to OWON P4603 power supply.'''

    def __init__(self, path = "ASRL/dev/instruments/P4603::INSTR"):
        self.path = path
    
    @functools.cached_property
    def port(self):
        '''Open port on first access'''
        self.visa = visa.ResourceManager("@py")
        port = self.visa.open_resource(self.path, baud_rate = 115200)

        idn_response = port.query("*IDN?")
        if 'P4603' not in idn_response:
            raise Exception("Unknown IDN: " + idn_response)
        
        return port

    def set_current(self, current):
        self.port.write("CURR %0.3f" % float(current))
    
    def set_voltage(self, voltage, wait = True):
        voltage = float(voltage)
        self.port.write("VOLT %0.3f" % voltage)

        if wait and self.is_on():
            # Wait for output to reach target voltage
            for i in range(50):
                v = self.measure_voltage()
                if abs(v - voltage) < 0.01:
                    break
                time.sleep(0.1)
            else:
                raise Exception("P4603: Voltage is %f, target %f" % (v, voltage))
    
    def is_on(self):
        return bool(int(self.port.query("OUTP?")))
    
    def output_on(self):
        self.port.write("OUTP 1")
        self.port.query("OUTP?")
    
    def output_off(self):
        self.port.write("OUTP 0")
        self.port.query("OUTP?")
    
    def measure_voltage(self):
        return float(self.port.query("MEAS:VOLT?"))
    
    def measure_current(self):
        return float(self.port.query("MEAS:CURR?"))

if __name__ == '__main__':
    p = P4603()
    while True:
        print("%6.3f V, %6.3f A" % (p.measure_voltage(), p.measure_current()))
        time.sleep(1)
