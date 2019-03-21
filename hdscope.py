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
    driver_class = ivi.rigol.rigolDS1104Z
    ip_addr = "169.254.11.120"
    tcp_port = "5555"
    n_channels = 4
    # First channel is active after start-up
    ch_active_flags = [True, False, False, False]
    # If set to true, all configuation changes made in the controller or
    # GUI are propagated to the hardware.
    hw_online_mode = True
    # Number of samples per acquisition. Text keywords are used for the GUI.
    # The  highest memory depth value determines the internal buffer size.
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
    # 125k samples default
    mdepth_default = 125000
    # 1 GS/s default
    sample_rate_default = 1000000000
    # Set numpy float precision.
    # Beware 100 Megasamples is 800 Megabytes RAM at 64 bit.
    # Filters typically need another three to six times the per-channel RAM
    float_precision = np.float64



class AnalogChannel():
    def __init__(
            self,
            ivi_driver,
            ch_buffer, # Call by reference
            ch_active_flags, # Call by reference
            index=0,
            active_on_start=True,
            desc="Channel xyz",
            unit="V",
            invert=False,
            scale=1.0,
            probe_atten=10.0,
            offset=0.0,
            # Request hardware bandwidth limit less or equal to value supplied
            bw_limit_max=1*10**12,
            time_skew=0.0,
            coupling="DC",
            impedance="1000000",
            ):
        self.ivi_driver = ivi_driver
        self.ch_buffer = ch_buffer
        self.ch_active_flags[index] = active_on_start # Assign to reference
        self.index = index
        self.desc = desc
        self.invert = invert
        self.scale = scale
        self.probe_atten = probe_atten
        self.offset = ofset
        self.unit = unit
        self.bw_limit_max = bw_limit_max
        self.time_skew = time_skew
        self.coupling = coupling
        self.impedance = impedance

    def pull_hw_props(self):
        """Update properties from hardware settings"""
        ch_drv = self.ivi_driver.channels[self.index]
        # Some of these are renamed..
        self.ch_active_flags[self.index] = ch_drv.enabled # Assign to reference
        self.invert = ch_drv.invert
        self.scale = ch_drv.scale
        self.probe_atten = ch_drv.probe_attenuation
        self.offset = ch_drv.offset
        self.bw_limit_max = ch_drv.input_frequency_max
        self.time_skew = ch_drv.probe_skew
        self.coupling = ch_drv.coupling
        self.impedance = ch_drv.input_impedance
    def push_hw_props(self):
        """Push settings to hardware"""
        ch_drv = self.ivi_driver.channels[self.index]
        # Some of these are renamed..
        ch_drv.enabled = self.ch_active_flags[self.index]
        ch_drv.invert = self.invert
        ch_drv.scale = ch_drv.scale
        ch_drv.probe_attenuation = self.probe_atten
        ch_drv.offset = self.offset
        ch_drv.input_frequency_max = self.bw_limit_max
        ch_drv.probe_skew = self.time_skew
        ch_drv.coupling = self.coupling
        ch_drv.input_impedance = self.impedance

    def pull_samples(self):
        """Pull acquired samples from hardware if available.
        This is a non-blocking method. Returns "True" if data was read.
        """
        drv = self.ivi_driver
        # FIXME: Measurement status != acquisition status?!
        if drv.measurement.status == "complete": 
            # Assign to reference
            self.ch_buffer[self.index] = np.array(
                    drv.channels[self.index].fetch_waveform().y
                    )
            return True
        else:
            return False


class HardwareInterface():
    """Interface to the ADC/Oscilloscope data source and external controls.
    
    Init args:
    config:     Configuration settings object, see config file
    cbX_config: List of callback functions run when any config
                setting changes, e.g. update the GUI.
    cbX_data:   List of callbacks run when new data is available
    """
    def __init__(
            self,
            config,
            # Mutable default arguments are on purpose here..
            cbX_config=[],
            cbX_data=[],
            ):
        self.cbX_config = cbX_config
        self.cbX_data = cbX_data
        self.scope = config.driver_class(
                f"TCPIP0::{config.ip_addr}::{config.tcp_port}::SOCKET",
                pyvisa_opts={"read_termination":"\n", "write_termination":"\n"},
                prefer_pyvisa=True,
                )
        self.n_channels = config.n_channels
        self.ch_active_flags = config.ch_active_flags
        self.sample_rate = config.sample_rate_default
        self.hw_mdepth = config.mdepth_default
        # Initialize with maximum memory configuration to be safe.
        # In case this fails due to low memory, this fails early.
        ch_buflen = max(self.mdepth_opts.values())
        # Analog channel buffer for data access
        # self.ch_buffers = np.zeros(
        #         (self.n_channels, ch_buflen),
        #         dtype = config.float_precision,
        #         )
        self.ch_bufers = [0] * self.n_channels
        # Analog channel objects for channel-by-channel hardware interaction
        self.ch = [
                AnalogChannel(
                    ivi_driver=self.scope,
                    ch_buffer=self.ch_buffers[i],
                    index=i,
                    desc=f"Channel {i}")
                for i in range(self.n_channels)
                ]
        # If set to true, all configuation changes made in the controller or
        # GUI are propagated to the hardware.
        self.hw_online_mode = config.hw_online_mode
    
    def register_cb_data(self, callback):
        if callback not in self.cbX_data:
            self.cbX_data.append(callback)
    def register_cb_config(self, callback):
        if callback not in self.cbX_config:
            self.cbX_config.append(callback)

    def _run_cbX_config(self):
        for callback in self.cbX_config:
            callback()
    def _run_cbX_data(self):
        for callback in self.cbX_data:
            callback()

    def _get_channel_active(self, index):
        if hw_online_mode:
            self.ch[index].pull_hw_props()
        self._run_cbX_config()
    def _set_channel_active(self, index, activation=True):
        self.ch_active_flags[index] = activation
        if hw_online_mode:
            self.ch[index].push_hw_props()
        self._run_cbX_config()

    def _pull_data(self, len_min=1200):
        print("pull data!")
        # This is the current acquisition mode "run" is True, "stop" is False
        acquisition_running = self.scope.trigger.continuous
        # Only 1200 points can be read while in active RUN state, as far as
        # Rigol DS1054Z etc. are concerned. Assuming this is a common device,
        # using this as a default threshold to put the device to stop mode for
        # reading.
        if acquisition_running and len_min > 1200:
            self.scope.trigger.continuous = False
        # Updates self.sample_rate and Qt buton if necessary
        self._get_sample_rate()
        # Updates self.n_samples and Qt button if necessary
        self._get_mdepth()
        for i in range(self.n_channels):
            self.ch[i].pull_samples()
        if acquisition_running:
            self.scope.trigger.continuous = True
        self._run_cbX_data()

    def _set_mdepth(self, value=None):
        """Send memory depth requested value to the connected device.
        Does NOT update self.n_samples """
        if value is not None:
            self.hw_mdepth = int(value)
        if hw_online_mode:
            print(f"Requesting memory depth (number of samples): {self.hw_mdepth}")
            # This is a driver call
            self.scope.acquisition.number_of_points_minimum = self.hw_mdepth
        self._run_cbX_config()
    def _get_mdepth(self):
        """Get memory depth value from scope, update property and call callbacks
        """
        # This is an ivi driver call:
        if hw_online_mode:
            self.hw_mdepth = self.scope.acquisition.record_length
        print(f"Number of samples is: {self.hw_mdepth}")
        self._run_cbX_config()

    def _get_sample_rate(self):
        """Get sample rate value from scope, update self.sample_rate and Qt
        widget if necessary"""
        if hw_online_mode:
            # This is an ivi driver call:
            self.sample_rate = self.scope.acquisition.sample_rate
        print(f"Sample rate is: {self.sample_rate}")
        self._run_cbX_config()


class DataModel():
    """Measurement data model, data-dependent filter and DSP methods"""
    # Filter length, default is moving average filter.
    filter_length = 120
    def __init__(self):
        self.




#FIXME compose instead of inherit
class Workspace():
    """Central Controller"""
    def __init__(self, config, data_model, hw_interface, qt_ui):
        #super().__init__()

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

