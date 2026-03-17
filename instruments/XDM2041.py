#!/bin/env python

import pyvisa as visa
import functools
import time

class XDM2041:
    '''Interface to OWON XDM2041 multimeter.'''

    def __init__(self, path = "ASRL/dev/instruments/XDM2041::INSTR"):
        self.path = path
    
    @functools.cached_property
    def port(self):
        '''Open port on first access'''
        self.visa = visa.ResourceManager("@py")
        port = self.visa.open_resource(self.path, baud_rate = 115200)

        idn_response = port.query("*IDN?")
        if 'XDM2041' not in idn_response:
            raise Exception("Unknown IDN: " + idn_response)
        
        return port

    def set_rate_fast():
        self.port.write("RATE F")

    def set_rate_slow():
        self.port.write("RATE L")

    def set_voltage_range(self, maxval):
        ranges = [0.05, 0.5, 5, 50, 500, 1000]
        r = min(x for x in ranges if x >= float(maxval))
        self.port.write("CONF:VOLT:DC %0.3f" % r)

    def set_resistance_range(self, maxval):
        ranges = [500, 5e3, 50e3, 500e3, 5e6, 50e6]
        r = min(x for x in ranges if x >= float(maxval))
        self.port.write("CONF:RES %0.3f" % r)

    def measure(self):
        return float(self.port.query("MEAS1?"))
    
if __name__ == '__main__':
    import sys

    interval = 1.0
    if len(sys.argv) > 1: interval = float(sys.argv[1])

    x = XDM2041()
    start = None
    i = 0
    
    while True:
        value = x.measure()
        timenow = time.time()
        if not start: start = timenow
        print("%10.3f %12.6f" % (timenow - start, value))
        sys.stdout.flush()

        i += 1
        time.sleep(i * interval - (timenow - start))
