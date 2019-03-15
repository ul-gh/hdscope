# -*- coding: utf-8 -*-
"""
RTH1004
"""
import sys
import numpy as np
import pandas as pd
import scipy.signal
import matplotlib.pyplot as plt
import visa


class Rohde_Schwarz_RTH():
    """Remote control and data transfer for Rohde & Schwarz RTH-Series two- and
    four-channel insulated handheld oscilloscopes.
    
    This supports models RTH1002 and RTH1004 with currently only basic
    functinality but offers high performance data transfer for PC-based signal
    processing.
    
    The RTH oscilloscopes can be controlled over TCP network using VXI-11 mode,
    where dynamically allocated TCP ports are used for device handshaking via
    ONC RPC calls, via raw TCP socket (5025), via HTTP interface (SCPI is at
    least partly implemented via HTTP POST RESTful API) and over USB using
    USBTMC protocol.

    VXI-11 mode is slower compared to raw sockets, and also not firewall-
    friendly. HTTP REST API is not implemented via VISA. USBTMC requires
    separate binary drivers when running under Windows but works out-of-the-box
    with current Linux versions using PyVISA and the USBTMC kernel module.

    Raw sockets should work right away on all platforms and are thus a
    recommendation.
    """
    def __init__(self, resource_str, n_channels=4, timeout=5000):
        assert sys.version_info.major >= 3, "End of support for Python2!"
        # With "@py", this uses pyvisa-py, otherwise NI-VISA lib is used
        rm = visa.ResourceManager("@py")
        dev = rm.open_resource(resource_str)
        # VXI-11 mode seems to have a maximum limit of 3960 somewhat samples.
        # Raw sockets do not have this limitation. USB and HTTP modes are not
        # tested. Assuming 2 kiB is a safe choice...
        if not "socket" in resource_str.lower():
            dev.chunk_size = 2048
        dev.read_termination = "\n"
        dev.write_termination = "\n"
        dev.timeout = timeout
        self.rm = rm
        self.dev = dev
        self.n_channels = n_channels
    
    def idn(self):
        return self.dev.query("*IDN?")
    
    def read_samples(self, ch):
        """Reads all samples acquired for the specified channel and returns a
        numpy.ndarray vector with scaled and offset-corrected physical units.

        Usually this is samples in volts.
        """
        # Set output format to int16, little endian
        self.dev.write("FORM INT,16;:FORM:BORD LSBF")
        # Wait for acquisition to finish
        self.dev.query('*OPC?')
        samples_raw = self.dev.querry_binary_values(
                f"CHAN{ch}:DATA?",
                datatype="h",
                header_fmt="ieee",
                is_big_endian=False,
                container=np.array)
        # See programming manual for the RTH series oscilloscope: Channel
        # offset can be entered numerically in physical units or by setting a
        # vertical shift in terms of trid divisions
        scale, position, offset = (self.dev.query_ascii_values(i)[0] for i in (
                f"CHAN{ch}:SCAL?", f"CHAN{ch}:POS?", f"CHAN{ch}:OFFS?"))
        # "samples_raw" is a numpy array, i.e. these operations are elementwise:
        samples_phys = samples_raw*scale*8/2**16 + offset - position*scale
        return samples_phys

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
 



#rth_resource_VXI = "TCPIP0::192.168.0.1::INSTR"
rth_resource_socket = "TCPIP0::169.254.11.120::5025::SOCKET"
#rth_resource_socket = "TCPIP0::RTH-103752::5025::SOCKET"

#rth = Rohde_Schwarz_RTH(rth_resource_socket)



# #rth.write('*RST;*CLS')  # Reset the instrument, clear the Error queue
#rth.ext_error_checking()  # Error Checking after Initialization block
# -----------------------------------------------------------
# Basic Settings:
# -----------------------------------------------------------
#rth.write('TIM:RANG 0.01')  # 10ms Acquisition time
#rth.write('CHAN1:PROB V100TO1') # Set 100:1 probe
#rth.write('CHAN1:BAND B5') # Set 5 MHz bandwidth
#rth.write('CHAN1:SCAL 0.5')  # Horizontal sensitivity 0.5V/div
#rth.write('CHAN1:OFFS 0.0')  # Offset 0
#rth.write('CHAN1:COUP ACL')  # Coupling AC 1MOhm
#rth.write('CHAN1:COUP DCL')  # Coupling DC 1MOhm
#rth.write('CHAN1:STAT ON')  # Switch Channel 1 ON
#rth.ext_error_checking()  # Error Checking after Basic Settings block
# -----------------------------------------------------------
# Trigger Settings:
# -----------------------------------------------------------
#rth.write('TRIG:MODE AUTO')  # Trigger Auto mode in case of no signal is applied
#rth.write('TRIG:TYPE EDGE;:TRIG:EDGE:SLOP POS')  # Trigger type Edge Positive
#rth.write('TRIG:SOUR C4')  # Trigger source CH1
#rth.write('TRIG:LEV1:VAL 0.5')  # Trigger level 0.5V
#rth.query('*OPC?')  # Using *OPC? query waits until all the instrument settings are finished
#rth.ext_error_checking()  # Error Checking after Trigger Settings block

# -----------------------------------------------------------
# SyncPoint 'SettingsApplied' - all the settings were applied
# -----------------------------------------------------------
# Arming the rth
# -----------------------------------------------------------
#rth.timeout = 10000  # Acquisition timeout in milliseconds - set it higher than the acquisition time
#rth.write('TRIG:MODE NORM')
# -----------------------------------------------------------
# DUT_Generate_Signal() - in our case we use Probe compensation signal
# where the trigger event (positive edge) is reoccurring
# -----------------------------------------------------------
#print('Waiting for the acquisition to finish... ')
#rth.query('*OPC?')  # Using *OPC? query waits until the instrument finished the acquisition
#rth.ext_error_checking()  # Error Checking after the acquisition is finished
# -----------------------------------------------------------
# SyncPoint 'AcquisitionFinished' - the results are ready
# -----------------------------------------------------------
# Fetching the waveform in ASCII format
# -----------------------------------------------------------
#print('Fetching waveform in ASCII format... ')
#rth.query('*OPC?')
#waveformASCII = rth.query_ascii_values('FORM ASC;:CHAN4:DATA?')
#print('ASCII data samples read: {}'.format(len(waveformASCII)))
#rth.ext_error_checking()  # Error Checking after the data transfer
# -----------------------------------------------------------
# Fetching the trace in Binary format
# Transfer of traces in binary format is faster.
# The waveformBIN data and waveformASC data are however the same.
# -----------------------------------------------------------
#print('Fetching waveform in binary format... ')
#rth.write("FORM INT,16;:FORM:BORD LSBF")
#raw_samples = rth.query_binary_values(
#    'CHAN4:DATA?', datatype="h", header_fmt="ieee", is_big_endian=False)
#print(f"Binary data samples read: {len(samples)}")
#rth.ext_error_checking()  # Error Checking after the data transfer
#x_bin = range(0, len(waveformBIN))

#plt.plot(x_bin, waveformPHYS)
#plt.plot(x_bin, waveformASCII)

    
