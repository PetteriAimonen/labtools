import cv2
import numpy as np
import PIL.Image
import struct
import serial
import functools
import math
import argparse

class TinySA:
    '''Interface for TinySA spectrum analyzer'''
    
    # Some ideas from https://github.com/erikkaashoek/tinySA/blob/main/python/nanovna.py
    
    screenwidth = 480
    screenheight = 320
    
    def __init__(self, path = '/dev/instruments/tinysa'):
        self.path = path

    @functools.cached_property
    def port(self):
        '''Open serial port on first use'''

        port = serial.Serial( self.path, 115200, timeout = 0.5)
        
        port.reset_input_buffer()
        while port.read(1024 * 1024):
            continue

        port.write(b"\r\ninfo\r\n")
        resp = port.read(1024)
        
        if b'tinySA' not in resp:
            raise Exception("TinySA: Unexpected response: %s" % resp)
        
        return port
    
    def run_cmd(self, cmd):
        '''Run command and capture response until ch> prompt reappears.'''
        if isinstance(cmd, str):
            cmd = cmd.encode('ascii')
        
        self.port.flushInput()
        self.port.write(cmd + b"\r\n")
        self.port.readline() # Discard command echo
        data = b''
        for line in self.port:
            if line.startswith(b'ch>'):
                break
            data += line
        return data
    
    def screenshot(self):
        '''Capture screenshot'''
        self.port.flushInput()
        self.port.write(b'capture\r\n')
        self.port.readline()

        totallen = self.screenwidth * self.screenheight * 2
        data = b''
        while len(data) < totallen:
            piece = self.port.read(totallen - len(data))
            if not piece: raise Exception("Timeout while reading screenshot, after %d bytes" % len(data))
            data += piece
        
        # Convert from RGB565
        pixels = list(struct.iter_unpack(">H", data))
        a = np.array(pixels, dtype = np.uint32)
        a = 0xFF000000 + ((a & 0xF800) >> 8) + ((a & 0x07E0) << 5) + ((a & 0x001F) << 19)
        return PIL.Image.frombuffer('RGBA', (self.screenwidth, self.screenheight), a, 'raw', 'RGBA', 0, 1)

    def scan(self, start = 1e6, stop = 100e6, rbw = 850e3, step = 0.5, logscale = False):
        '''Scan from start to end frequency (Hz).
        Resolution bandwidth rbw (Hz) (200, 1e3, 3e3, 10e3, 30e3, 100e3, 300e3, 600e3, 850e3)
        Measurement point interval is step * rbw.
        Returns numpy array with first column frequency and second column dBm.
        '''
        
        assert rbw in (200, 1e3, 3e3, 10e3, 30e3, 100e3, 300e3, 600e3, 850e3)
        assert stop > start
        
        step = step * rbw
        points = math.ceil((stop - start) / step)
        results = np.zeros((0, 2))
        
        if logscale:
            freqs = np.logspace(math.log10(start), math.log10(stop), points)
        else:
            freqs = np.linspace(start, stop, points)
        
        segment_len = 200
        for i in range(0, points, segment_len):
            freqseg = freqs[i:i + segment_len]
            
            data = self.run_cmd('scan %d %d %d 3' % (freqseg[0], freqseg[-1], len(freqseg)))
            data = np.genfromtxt(data.decode('ascii').split('\n'))
            results = np.vstack((results, data[:,:2]))
        
        return results

if __name__ == '__main__':
    argparser = argparse.ArgumentParser(description = "Utility for TinySA spectrum analyzer")
    argparser.add_argument('--screenshot', dest="screenshot", metavar="FILENAME")
    argparser.add_argument('--scan', dest="scan", metavar="FILENAME")
    argparser.add_argument('--start', dest='start', metavar='Hz', default='1e6')
    argparser.add_argument('--stop', dest='stop', metavar='Hz', default='900e6')
    argparser.add_argument('--rbw', dest='rbw', metavar='Hz', default="850e3")
    argparser.add_argument('--logscale', dest='logscale', action="store_true")
    args = argparser.parse_args()
    
    sa = TinySA()
    
    if args.screenshot:
        sa.screenshot().save(args.screenshot)
    
    if args.scan:
        data = sa.scan(float(args.start), float(args.stop), float(args.rbw), logscale = args.logscale)
        np.savetxt(args.scan, data)

