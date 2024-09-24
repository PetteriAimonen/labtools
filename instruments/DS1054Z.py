import pyvisa as visa
from pyvisa import constants
import functools
import time
import numpy
import scipy, scipy.signal
import math
import cmath
import time
import PIL.Image
import io
import socket

class DS1054Z:
    '''Interface to Rigol DS1054Z oscilloscope.'''

    timebases = [
        2e-9, 5e-9,
        1e-8, 2e-8, 5e-8,
        1e-7, 2e-7, 5e-7,
        1e-6, 2e-6, 5e-6,
        1e-5, 2e-5, 5e-5,
        1e-4, 2e-4, 5e-4,
        1e-3, 2e-3, 5e-3,
        1e-2, 2e-2, 5e-2,
        1e-1, 2e-1, 5e-1,
        1e-0, 2e-0, 5e-0,
        1e+1, 2e+1, 5e+1
    ]

    vertical_scales = [
        1e-2, 2e-2, 5e-2,
        1e-1, 2e-1, 5e-1,
        1e-0, 2e-0, 5e-0,
        1e+1, 2e+1, 5e+1,
        1e+2
    ]

    def __init__(self, path = "TCPIP::scope::5555::SOCKET"):
        self.path = path
    
    @functools.cached_property
    def port(self):
        '''Open port on first access'''
        self.visa = visa.ResourceManager("@py")
        port = self.visa.open_resource(self.path, read_termination = '\n', write_termination = '\n')
        port.timeout = 10000

        # NOTE: For fastest data transfer from DS1054Z, use ::SOCKET connection mode
        # and TCPIP_NODELAY.
        # See https://www.eevblog.com/forum/testgear/download-speed-from-rigol-ds1054z-or-similar-oscilloscope-to-a-pc/25/
        port.visalib.sessions[port.session]._set_tcpip_nodelay(constants.VI_ATTR_TCPIP_NODELAY, True)
        
        idn_response = port.query("*IDN?")
        if 'RIGOL' not in idn_response:
            raise Exception("Unknown IDN: " + idn_response)
        
        return port
    
    def set_timebase(self, timebase, round = True):
        if round:
            timebase = min(self.timebases, key = lambda x: abs(x - timebase))

        self.port.write("TIM:SCAL %s" % timebase)
    
    def config_channel(self, channel, scale, ac_mode = False, probe_scale = 10, bwlimit = False, display = True):
        channel = int(channel)
        self.port.write("CHAN%d:COUP %s" % (channel, 'AC' if ac_mode else 'DC'))
        self.port.write("CHAN%d:DISP %s" % (channel, 'ON' if display else 'OFF'))
        self.port.write("CHAN%d:PROB %d" % (channel, probe_scale))
        self.port.write("CHAN%d:BWLIMIT %s" % (channel, '20M' if bwlimit else 'OFF'))
        self.port.write("CHAN%d:SCAL %s" % (channel, scale))
    
    def set_channel_scale(self, channel, scale, round = True):
        if round:
            scale = min(self.vertical_scales, key = lambda x: abs(x - scale))

        self.port.write("CHAN%d:SCAL %s" % (channel, scale))

    def autoscale(self):
        self.port.write("AUTOSCALE")
        
        for i in range(20):
            if '1' in self.port.query("*OPC?"):
                break
            time.sleep(0.5)
        time.sleep(1)
    
    def run(self):
        self.port.write("RUN")
    
    def single(self):
        self.port.write("SINGLE")

    def stop(self):
        self.port.write("STOP")

    def force_trigger(self):
        self.port.write("TFORCE")

    def wait_stopped(self):
        for i in range(20):
            if 'STOP' in self.port.query("TRIG:STAT?"):
                return
            time.sleep(0.5)
    
    def acquire_normal(self):
        '''Set scope to normal (non-average) acquire mode.'''
        self.port.write("ACQ:TYPE NORM")

    def acquire_average(self, averages = 128):
        '''Set scope to averaging acquire mode.'''
        self.port.write("ACQ:TYPE AVER")
        self.port.write("ACQ:AVER %d" % int(averages))

    def set_trigger_rising(self, channel, level):
        self.port.write("TRIG:EDGE:SOUR CHAN%d" % int(channel))
        self.port.write("TRIG:EDGE:SLOP POS")
        self.port.write("TRIG:EDGE:LEV %f" % float(level))

    def set_trigger_falling(self, channel, level):
        self.port.write("TRIG:EDGE:SOUR CHAN%d" % int(channel))
        self.port.write("TRIG:EDGE:SLOP NEG")
        self.port.write("TRIG:EDGE:LEV %f" % float(level))

    def measure(self, channel, parameter):
        '''Measure parameter of channel.
        Parameter is one of: VMAX, VMIN, VPP, VTOP, BASE, VAMP, VAVG, VRMS,
        OVERSHOOT, PRESHOOT, MAREA, MPAREA, PERIOD, FREQUENCY, RTIME, FTIME,
        PWIDTH, NWIDTH, PDUTY, NDUTY, RDELAY, FDELAY, RPHASE, FPHASE, TVMAX,
        TVMIN, PSLEWRATE, NSLEWRATE, VUPPER, VMID, VLOWER, VARIANCE, PVRMS,
        PPULSES, NPULSES, PEDGES, NEDGES
        '''
        response = self.port.query("MEAS:ITEM? %s,CHAN%d" %
                      (parameter, int(channel)))
        return float(response)
    
    def measure_rdelay(self, channel1, channel2):
        '''Measure rising edge delay between two channels'''
        response = self.port.query("MEAS:ITEM? RDELAY,CHAN%d,CHAN%d" %
                      (int(channel1), int(channel2)))
        return float(response)

    def screenshot(self):
        '''Take a screenshot.'''
        data = self.port.query_binary_values("DISP:DATA? ON,OFF,PNG", datatype = 'B')
        data = bytes(data)
        #data = self.port.read_raw()
        #open('data', 'wb').write(bytes(data))
#        offset, datalen = visa.util.parse_ieee_block_header(data)
#        data = data[offset:offset + datalen]
        return PIL.Image.open(io.BytesIO(data))

    def set_memdepth(self, depth):
        '''Set memory depth. Depth is None for automatic or numeric value.'''
        if not depth:
            self.port.write("ACQ:MDEPTH AUTO")
        else:
            self.port.write("ACQ:MDEPTH %d" % depth)

    def sample_interval(self):
        '''Return sample interval in seconds'''
        return float(self.port.query("WAV:XINC?"))

    def fetch_data(self, channel):
        '''Fetch waveform data from scope to buffer (uses screen buffer).'''
        self.port.write("WAV:SOUR CHAN%d" % int(channel))
        self.port.write("WAV:MODE NORM")
        self.port.write("WAV:FORM BYTE")
        self.port.write("WAV:STAR 1")
        self.port.write("WAV:STOP 1200")
        sample_scale = float(self.port.query("WAV:YINC?"))
        sample_offset = float(self.port.query("WAV:YOR?"))
        sample_ref = float(self.port.query("WAV:YREF?"))
        data = self.port.query_binary_values("WAV:DATA?", datatype='B')
        return (numpy.array(data) - sample_ref - sample_offset) * sample_scale

    def fetch_data_raw(self, channel, start = 1, end = None):
        '''Fetch waveform data from the full capture buffer. Stops capture.'''
        self.port.write("STOP")
        self.port.write("WAV:SOUR CHAN%d" % int(channel))
        self.port.write("WAV:MODE RAW")
        self.port.write("WAV:FORM BYTE")
        sample_scale = float(self.port.query("WAV:YINC?"))
        sample_offset = float(self.port.query("WAV:YOR?"))
        sample_ref = float(self.port.query("WAV:YREF?"))
        
        if end is None:
            end = int(self.port.query("ACQ:MDEPTH?"))
        
        alldata = []
        
        start = int(start)
        end = int(end)
        maxblocklen = 250000
        for blockstart in range(start, end, maxblocklen):
            self.port.write("WAV:START %d" % blockstart)
            self.port.write("WAV:STOP %d" % min(blockstart + maxblocklen, end))
            block = self.port.query_binary_values("WAV:DATA?", datatype='B')
            alldata += block

        return (numpy.array(alldata) - sample_ref - sample_offset) * sample_scale

    def dft_at_freq(self, channel, freq, use_raw = False):
        '''Calculate amplitude and phase at given frequency from
        data fetched from screen buffer or raw buffer.'''

        if use_raw:
            data = self.fetch_data_raw(channel)
        else:
            data = self.fetch_data(channel)

        freq = float(freq)
        sample_interval = self.sample_interval()
        samples_per_period = round((1.0 / freq) / sample_interval)

        if samples_per_period < 5:
            raise Exception("DS1054Z too large timestep %g for freq %f" % (sample_interval, freq))
        
        periods = len(data) // samples_per_period
        samples = periods * samples_per_period
        
        if periods < 1:
            raise Exception("DS1054Z too small timestep %g for freq %f" % (sample_interval, freq))

        exp = numpy.exp(math.tau * 1j * numpy.linspace(0, periods, samples, endpoint = False))
        dft = numpy.sum(numpy.multiply(exp, data[:samples])) / samples

        amplitude = 4 * abs(dft) # Convert to Vpp reading
        phase = numpy.degrees(cmath.phase(dft))

        return amplitude, phase

if __name__ == '__main__':
    import sys
    d = DS1054Z()
    
    d.screenshot().save("ds1054z.png")
    
    #start = time.time()
#    data = d.fetch_data_raw(1, end = 1000000)
#    end = time.time()
    
#    print("Time", end - start)
    
#    print(max(data), min(data))
#    print(len(data))
#    numpy.savetxt("data.txt", data)
