#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import random
import atexit
import numpy as np
from functools import partial
from IPython import get_ipython
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QMainWindow, QApplication
import PyQt5.uic
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as MplToolbar
# "from python-ivi import ivi" does not work since python-ivi has dash in name
import importlib
ivi = importlib.import_module("python-ivi.ivi")
import filters

get_ipython().run_line_magic("gui", "qt5")
#get_ipython().run_line_magic("matplotlib", "qt5")

class Config():
    ip_addr = 169.254.11.120
    tcp_port = 5555

class DataModel():
    pass

class AnalogChannel():
    def __init__(
            self,
            ivi_driver,
            samples_buffer,
            index=0,
            desc="Channel xyz",
            unit="V",
            active=True,
            invert=False,
            scale=1.0,
            probe_atten=10.0,
            offset=0.0,
            hw_bandwidth=1*10**9,
            time_skew=0.0,
            coupling="DC",
            impedance="1000000",
            ):
        self.ivi_driver = ivi_driver
        self.index = index
        self.desc = desc
        self.active = active
        self.invert = invert
        self.scale = scale
        self.probe_atten = probe_atten
        self.offset = ofset
        self.unit = unit
        self.hw_bandwidth = hw_bandwidth
        self.time_skew = time_skew
        self.coupling = coupling
        self.impedance = impedance

    def pull_hw_props(self):
        """Update properties from hardware settings"""
        ch_drv = self.ivi_driver.channels[self.index]
        # Some of these are renamed..
        self.active = ch_drv.enabled
        self.invert = ch_drv.invert
        self.scale = ch_drv.scale
        self.probe_atten = ch_drv.probe_attenuation
        self.offset = ch_drv.offset
        self.hw_bandwidth = ch_drv.input_frequency_max
        self.time_skew = ch_drv.probe_skew
        self.coupling = ch_drv.coupling
        self.impedance = ch_drv.input_impedance
    def push_hw_props(self):
        """Push settings to hardware"""
        ch_drv = self.ivi_driver.channels[self.index]
        # Some of these are renamed..
        ch_drv.enabled = self.active
        ch_drv.invert = self.invert
        ch_drv.scale = ch_drv.scale
        ch_drv.probe_attenuation = self.probe_atten
        ch_drv.offset = self.offset
        ch_drv.input_frequency_max = self.hw_bandwidth
        ch_drv.probe_skew = self.time_skew
        ch_drv.coupling = self.coupling
        ch_drv.input_impedance = self.impedance

    def pull_samples(self):
        """Pull acquired samples from hardware if available.
        This is a non-blocking method. Returns "True" if data was read.
        """
        drv = self.ivi_driver
        if drv.measurement.status == "complete": 
            self.samples_buffer = drv.channels[self.index].fetch_waveform().y
            return True
        else:
            return False
 



class HardwareInterface():
    """Interface to the ADC/Oscilloscope data source and external controls"""
    # Number of samples per acquisition. Text keywords are used for the GUI.
    mdepth_opts = {
        "24M": 24000000,
        "12M": 12000000,
        "6M": 6000000,
        "3M": 3000000,
        "2M": 2000000,
        "1M": 1000000,
        "500k": 500000,
        "250k": 250000,
        "125k": 125000,
        }
    # Indexes of channels active at start. Starting at zero.
    channels = {
            0: {active: False, "Channel 1",
        1: "Channel 2",
        2: "Channel 3",
        3: "Channel 4"
        }
    channels_active = {0: "Channel 1"}

    def __init__(self, config):
        self.scope = ivi.rigol.rigolDS1054Z(
                # "TCPIP0::169.254.11.120::INSTR",
                f"TCPIP0::{config.ip_addr}::{config.tcp_port}::SOCKET",
                pyvisa_opts={"read_termination":"\n", "write_termination":"\n"},
                prefer_pyvisa=True,)
    def _set_channel_active(self, i, activation=True):
        if activation:
            self.channels_active.update({i:self.channels[i]})
        else:
            self.channels_active.pop(i)

    def _pull_data(self):
        print("pull data!")
        # This is the current acquisition mode "run" is True, "stop" is False
        acquisition_running = self.scope.trigger.continuous
        if acquisition_running and self.mdepth.currentData() > 1200:
            self.scope.trigger.continuous = False
        # Updates self.sample_rate and Qt buton if necessary
        self._get_sample_rate()
        # Updates self.n_samples and Qt button if necessary
        self._get_mdepth()
        for i in self.channels_active:
            self.ydata[i] = self.scope.channels[i].measurement.fetch_waveform()
        if acquisition_running:
            self.scope.trigger.continuous = True
        self.update_plot()

    def _set_mdepth(self, value=None):
        """Send memory depth requested value to the connected device.
        Does NOT update self.n_samples """
        if value is None:
            n_samples = int(self.mdepth.currentData() * 10E6)
        else:
            n_samples = value
        print(f"Requesting memory depth (number of samples): {n_samples}")
        self.scope.acquisition.number_of_points_minimum = n_samples

    def _get_mdepth(self):
        """Get memory depth value from scope, update self.n_samples and Qt
        widget if necessary"""
        # This is an ivi driver call:
        value = self.scope.acquisition.record_length
        print(f"Number of samples is: {value}")
        if not value in self.config.mdepth_values:
            self.mdepth.insertItem(0, f"{value:1.1e}", value)
        self.n_samples = value

    def _get_sample_rate(self):
        """Get sample rate value from scope, update self.sample_rate and Qt
        widget if necessary"""
        # This is an ivi driver call:
        value = self.scope.acquisition.sample_rate
        print(f"Sample rate is: {value}")
        self.n_samples = value


class SampleData():
    """Measurement data model, data-dependent filter and DSP methods"""
    # Filter length, default is moving average filter.
    filter_length = 120


class Workspace(HardwareInterface, SampleData, QtUi):
    """Central Controller"""
    ydata = [[0.0], ] * 4
    
    def __init__(self):
        super().__init__()

        # FIXME
        #self.time_span = float(self.scope._ask("acq:mdepth?"))/float(self.scope._ask("acq:srate?"))

        for text, value in zip(config.mdepth_text, config.mdepth_values):
            self.select_mdepth.addItem(text, value)
        self.mdepth.activated[str].connect(self._set_mdepth)
        
        self.pull_data.clicked.connect(self._pull_data)
        self.apply_filter.clicked.connect(self.apply_filter)

        # Beware this is early-binding the channel number to _set_channel_active
        self.ch1.clicked.connect(partial(self._set_channel_active, 0))
        self.ch2.clicked.connect(partial(self._set_channel_active, 1))
        self.ch3.clicked.connect(partial(self._set_channel_active, 2))
        self.ch4.clicked.connect(partial(self._set_channel_active, 3))
#        self.ch4.clicked.connect(self.MplWidget.update_graph_simulation)

        self.H1.stateChanged.connect(self.MplWidget.cursors[0].set_enabled)
        self.MplWidget.cursors[0].callback = self.H1.setChecked
        self.H2.stateChanged.connect(self.MplWidget.cursors[1].set_enabled)
        self.MplWidget.cursors[1].callback = self.H2.setChecked
        self.V1.stateChanged.connect(self.MplWidget.cursors[2].set_enabled)
        self.MplWidget.cursors[2].callback = self.V1.setChecked
        self.V2.stateChanged.connect(self.MplWidget.cursors[3].set_enabled)
        self.MplWidget.cursors[3].callback = self.V2.setChecked

    def apply_filter(self, channel):
        """Apply filter"""
        self.ydata[channel] = filters.moving_average1(
                self.ydata[channel], self.filter_length)
        self.update_plot()

    def update_plot(self):
        self.MplWidget.plot_new(self.sample_rate, self.n_samples,
                self.channels_active, self.ydata)



class QtUi(QMainWindow, Config):
    def __init__(self):
        super().__init__()
        # Loads Qt Designer .ui file and creates an instance of the user
        # interface in this QMainWindow instance. This automatically adds
        # any further widgets defined in the .ui file to this main instance.
        # (e.g. MplWidget)
        PyQt5.uic.loadUi("hdscope.ui", baseinstance=self)
        self.setWindowTitle("PyQt5 & Matplotlib HD Oscilloscope")
        self.addToolBar(MplToolbar(self.MplWidget.canvas_qt, self))


        for text, value in zip(config.mdepth_text, config.mdepth_values):
            self.select_mdepth.addItem(text, value)
        self.mdepth.activated[str].connect(self._set_mdepth)
        
        self.pull_data.clicked.connect(self._pull_data)
        self.apply_filter.clicked.connect(self.apply_filter)

        # Beware this is early-binding the channel number to _set_channel_active
        self.ch1.clicked.connect(partial(self._set_channel_active, 0))
        self.ch2.clicked.connect(partial(self._set_channel_active, 1))
        self.ch3.clicked.connect(partial(self._set_channel_active, 2))
        self.ch4.clicked.connect(partial(self._set_channel_active, 3))
#        self.ch4.clicked.connect(self.MplWidget.update_graph_simulation)

        self.H1.stateChanged.connect(self.MplWidget.cursors[0].set_enabled)
        self.MplWidget.cursors[0].callback = self.H1.setChecked
        self.H2.stateChanged.connect(self.MplWidget.cursors[1].set_enabled)
        self.MplWidget.cursors[1].callback = self.H2.setChecked
        self.V1.stateChanged.connect(self.MplWidget.cursors[2].set_enabled)
        self.MplWidget.cursors[2].callback = self.V1.setChecked
        self.V2.stateChanged.connect(self.MplWidget.cursors[3].set_enabled)
        self.MplWidget.cursors[3].callback = self.V2.setChecked



class WorkerThread(QThread):
    signal = pyqtSignal("PyQt_PyObject")
    
    def __init__(self):
        super().__init__()

    def __del__(self):
        self.wait()

    def run(self):
        pass

if QApplication.instance() is None:
    app = QApplication(sys.argv) 

window = HDScope()
window.show()
atexit.register(window.scope.close)

# Shortcuts for interactive use
mplw = window.MplWidget
scope = window.scope
instr = window.scope._interface.instrument

