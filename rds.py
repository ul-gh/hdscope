# -*- coding: utf-8 -*-
"""
RTH1004
"""
import sys
import numpy as np
import pandas as pd
import scipy.signal
import matplotlib.pyplot as plt
from matplotlib.pyplot import plot
import visa
from iterators_generators import slice_range


class Rigol_DS1054Z():
    """Remote control and data transfer for Rigol DS1054Z
    """
    def __init__(self, resource_str, n_channels=4, timeout=10000):
        assert sys.version_info.major >= 3, "End of support for Python2!"
        # With "@py", this uses pyvisa-py, otherwise NI-VISA lib is used
        rm = visa.ResourceManager("@py")
        dev = rm.open_resource(resource_str)
        # VXI-11 mode seems to have a maximum limit of 3960 somewhat samples.
        # Raw sockets do not have this limitation. USB and HTTP modes are not
        # tested. Assuming 2 kiB is a safe choice...
        #if not "socket" in resource_str.lower():
        #    dev.chunk_size = 2048
        dev.read_termination = "\n"
        dev.write_termination = "\n"
        dev.timeout = timeout
        self.rm = rm
        self.dev = dev
        self.n_channels = n_channels
    
    def idn(self):
        return self.dev.query("*IDN?")
    
    def read_samples(self, ch, n_samples=24*10**6):
        """Reads all samples acquired for the specified channel and returns a
        numpy.ndarray vector with scaled and offset-corrected physical units.

        Usually this is samples in volts.
        """
        self.dev.write("stop")
        # Wait for acquisition to finish
        self.dev.query('*OPC?')
        # Set output format to int16, little endian
        self.dev.write("waveform:source channel{ch};mode raw;format byte")
        samples_raw = np.zeros(n_samples)
        for start, stop in slice_range(1, n_samples, 750000):
            self.dev.write(f"waveform:start {start};:waveform:stop {stop}")
            samples_raw[start-1:stop] = self.dev.query_binary_values(
                    "waveform:data?",
                    datatype="B",
                    header_fmt="ieee",
                    #is_big_endian=False,
                    container=np.array)
        # See programming manual for the RTH series oscilloscope: Channel
        # offset can be entered numerically in physical units or by setting a
        # vertical shift in terms of grid divisions
        return samples_raw

    def downsample_average(self, x, N):
        """Downsample using simple average as anti-aliasing filter.
        
        This is not only fastest but offers best possible random noise
        reduction, yielding enhanced resolution when sufficient white noise is
        present. Extra resolution bits are log(N)/log(4).

        Disadvantage is poor frequency stopband attenuation.
        Use this as the first step of any further processing.
        """
        assert x.size % N == 0, "Input vector must be divisible by N"
        return np.mean(x.reshape(-1, N), axis=1)
    
    def moving_average1(self, x, N):
        # Fast. Processing 100 megasample float values needs approx. 4 GiB RAM.
        # See: https://stackoverflow.com/a/27681394/675674
        cumsum = np.cumsum(np.insert(x, 0, 0)) 
        return (cumsum[N:] - cumsum[:-N]) / float(N)
    
    def moving_average2(self, x, N):
        # Uses convolution. Approx. 10x slower than np.cumsums but uses less
        # memory: approx. 2.5 GiB for 100 megasamples.
        return np.convolve(x, np.ones((N,))/N, mode="valid")
        
    def moving_average3(self, x, N):
        # Uses convolution via FFT and IFFT. Similar speed than np.convolve but
        # much more memory usage, approx. 8.5 GiB for 100 megasamples.
        return scipy.signal.fftconvolve(x, np.ones((N,))/N, mode="valid")
        
    def moving_average4(self, x, N):
        # Using pandas, approx. 4x slower than np.cumsum. Approx. 8 GiB for 100
        # megasamples.
        return pd.Series(x).rolling(window=N).mean().iloc[N-1:].values
 



rds_resource_VXI = "TCPIP0::192.168.178.64::INSTR"
rds_resource_socket = "TCPIP0::192.168.178.64::5555::SOCKET"

rds = Rigol_DS1054Z(rds_resource_socket)
