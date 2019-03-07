#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import random
import atexit
import numpy as np
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
    scope = ivi.rigol.rigolDS1054Z(
#            "TCPIP0::169.254.11.120::INSTR",
            "TCPIP0::169.254.11.120::5555::SOCKET",
            pyvisa_opts={"read_termination":"\n", "write_termination":"\n"},
            prefer_pyvisa=True)
    mdepth_text = ("24M", "12M", "6M", "3M", "2M", "1M", "500k", "250k", "125k")
    mdepth_values = (24, 12, 6, 3, 2, 1, 0.5, 0.25, 0.125)
    # Indexes of channels active at start. Starting at zero.
    channels_active = {0}

class HDScope(QMainWindow):
    def __init__(self, config):
        super().__init__()
        # Loads Qt Designer .ui file and creates an instance of the user
        # interface in this QMainWindow instance. This automatically adds
        # any further widgets defined in the .ui file to this main instance.
        # (e.g. MplWidget)
        PyQt5.uic.loadUi("hdscope.ui", baseinstance=self)
        self.setWindowTitle("PyQt5 & Matplotlib HD Oscilloscope")
        self.addToolBar(MplToolbar(self.MplWidget.canvas_qt, self))

        # All configuration settings
        self.config = config
        # Shortcut for oscilloscope IVI driver instance
        self.scope = config.scope

        self.channels_active = config.channels_active
        self.ydata = [0.0] * 4

        for text, value in zip(config.mdepth_text, config.mdepth_values):
            self.mdepth.addItem(text, value)
        self.mdepth.activated[str].connect(self._set_mdepth)
        
        self.pull_data.clicked.connect(self._pull_data)

        self.ch1.clicked.connect(lambda x: self._set_channel_active(0, x))
        self.ch2.clicked.connect(lambda x: self._set_channel_active(1, x))
        self.ch3.clicked.connect(lambda x: self._set_channel_active(2, x))
        # FIXME: Test only
        self.ch4.clicked.connect(self.MplWidget.update_graph_simulation)

        self.H1.stateChanged.connect(self.MplWidget.cursors[0].set_enabled)
        self.MplWidget.cursors[0].callback = self.H1.setChecked
        self.H2.stateChanged.connect(self.MplWidget.cursors[1].set_enabled)
        self.MplWidget.cursors[1].callback = self.H2.setChecked
        self.V1.stateChanged.connect(self.MplWidget.cursors[2].set_enabled)
        self.MplWidget.cursors[2].callback = self.V1.setChecked
        self.V2.stateChanged.connect(self.MplWidget.cursors[3].set_enabled)
        self.MplWidget.cursors[3].callback = self.V2.setChecked

    def _set_channel_active(self, i, activation=True):
        if activation:
            self.channels_active.add(i)
        else:
            self.channels_active.remove(i)

    def _pull_data(self):
        print("pull data!")
        for i in self.channels_active:
            self.ydata[i] = self.scope.channels[i].measurement.fetch_waveform()
        self.MplWidget.plot_new(self.ydata)

    def _set_mdepth(self, selection):
        n_samples = int(self.mdepth.currentData() * 10E6)
        print(f"Numeric: {n_samples}")
        self.scope.acquisition.number_of_points_minimum = n_samples
    def _get_mdepth(self):
        print("Getting mdepth")
        value = self.scope.acquisition.record_length()
        print(f"Value is: {value}")
        if not value in self.config.mdepth_values:
            self.mdepth.insertItem(0, f"{value:1.1e}", value)

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

window = HDScope(Config)
window.show()
atexit.register(window.scope.close)

# Shortcuts for interactive use
mplw = window.MplWidget
scope = window.scope
instr = window.scope._interface.instrument
