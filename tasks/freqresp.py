#!/bin/env python3

from labtools import instruments
import numpy as np
import math
import sigfig
import click
import pandas
import time

def measure_response(freq, delay = 1.0, autorange = False, memdepth = 120000):
    '''Default measurement callback, returns amplitude and phase.
    Uses channel 1 as measurement channel and channel 2 as reference channel.'''
    instruments.awg.set_frequency(1, freq)
    instruments.scope.run()
    instruments.scope.set_memdepth(memdepth)
    instruments.scope.set_timebase(1.0 / freq)
    delay += 40.0 / freq

    if autorange:
        instruments.scope.set_channel_scale(1, 1.0)
        instruments.scope.set_channel_scale(2, 1.0)
        instruments.scope.force_trigger()
        time.sleep(delay)
        instruments.scope.stop()
        a1 = np.max(np.abs(instruments.scope.fetch_data(1)))
        a2 = np.max(np.abs(instruments.scope.fetch_data(2)))
        instruments.scope.set_channel_scale(1, a1 / 4.0)
        instruments.scope.set_channel_scale(2, a2 / 4.0)
        instruments.scope.run()

    instruments.scope.force_trigger()
    time.sleep(delay)
    instruments.scope.stop()

    a1, p1 = instruments.scope.dft_at_freq(1, freq, use_raw = True)
    a2, p2 = instruments.scope.dft_at_freq(2, freq, use_raw = True)

    phase_delta = ((p1 - p2) + 180.0) % 360.0 - 180.0
    return (a1 / a2, phase_delta)

def freqresp_iter(freq_min = 100.0, freq_max = 100.0e3, log_stepsdec = 10,
             lin_interval = None,
             measure = measure_response, **kwargs):
    '''Measure frequency response using signal generator and oscilloscope.'''

    if lin_interval:
        freqs = np.arange(freq_min, freq_max, lin_interval)
    else:
        sigfigs = math.ceil(log_stepsdec / 10 + 1)
        base = 10**(1.0 / log_stepsdec)
        steps = math.ceil(math.log(freq_max / freq_min) / math.log(base))
        first = math.log(freq_min) / math.log(base)
        freqs = [sigfig.round(base ** (first + x), sigfigs=sigfigs) for x in range(steps + 1)]

    results = []

    for freq in freqs:
        a, p = measure(freq, **kwargs)
        dB = 10.0 * math.log10(a)
        yield {'freq': freq, 'amplitude': a, 'dB': dB, 'phase': p}

def freqresp(freq_min = 100.0, freq_max = 100.0e3, log_stepsdec = 10,
             lin_interval = None,
             measure = measure_response, delay = 1.0, autorange = False, **kwargs):
    '''Measure frequency response using signal generator and oscilloscope.'''

    try:
        from IPython import get_ipython
        from IPython.display import display, clear_output
        from matplotlib import pyplot as plt
        ipython = get_ipython()
    except:
        ipython = None

    if ipython:
        fig = plt.figure()
        ax = fig.add_axes([0.2,0.2,0.8,0.6])

    data = []
    for row in freqresp_iter(freq_min, freq_max, log_stepsdec, lin_interval, measure, delay = delay, autorange = autorange, **kwargs):
        data.append(row)

        if ipython:
            r = pandas.DataFrame(data)
            clear_output(wait = True)
            ax.clear()
            ax.plot(list(r['freq']), list(r['dB']), label = 'dB')
            ax.plot(list(r['freq']), list(r['phase']), label = 'phase')
            ax.set_xlabel('Frequency (Hz)', labelpad = 15)
            ax.grid()
            ax.legend(loc='upper right', bbox_to_anchor=(1, 1.2))
            display(fig)
            display(r)

    r = pandas.DataFrame(data)

    if ipython:
        clear_output()
        display(r)

    return r


@click.command()
@click.option('--freq_min', default = 100.0)
@click.option('--freq_max', default = 100.0e3)
@click.option('--log_stepsdec', default = 10)
@click.option('--lin_interval', default = None, type = float)
@click.option('--delay', default = 1.0)
@click.option('--autorange', is_flag = True)
def freqresp_cli(*args, **kwargs):
    click.echo("# Frequency(Hz)   Amplitude(abs)   Amplitude(dB)     Phase(deg)")
    for row in freqresp_iter(*args, **kwargs):
        click.echo("%15.3f  %15.9f  %15.3f  %15.3f" % (row['freq'], row['amplitude'], row['dB'], row['phase']))

if __name__ == '__main__':
    freqresp_cli()
