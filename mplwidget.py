# -*- coding: utf-8 -*-
from pyqt_debug import debug_trace
import numpy as np
from PyQt5.QtWidgets import QWidget,QVBoxLayout
import matplotlib.backends.backend_qt5agg as mpl_backend_qt
import matplotlib.figure

class Cursor():
    handle = None # matplotlib.lines.Line2D object
    is_active = False

    def __init__(self,
            canvas_qt, # Matplotlib figure instance
            subplot, # AxesSubplot instance within that figure
            callback=lambda *x: None, # E.g. QCheckBox setChecked method
            name="v1", # "vertical measurement cursor 1"
            is_vertical=True,
            linestyle="--"
            ):
        self.canvas_qt = canvas_qt
        self.subplot = subplot
        self.callback = callback
        self.name = name
        self.is_vertical = is_vertical
        self.linestyle = linestyle

    def set_enabled(self, activation):
        "Show cursor if activation argument is true, else remove cursor"
        if activation:
            if self.handle is not None:
                pass
            else:
                if self.is_vertical:
                    self.handle = self.subplot.axhline(
                            y=0.0, color="k", linewidth=1.5,
                            linestyle=self.linestyle, picker="5.0")
                else:
                    self.handle = self.subplot.axvline(
                            x=0.0, color="k", linewidth=1.5,
                            linestyle=self.linestyle, picker="5.0")
            self.callback(True)
            self.is_active = True
            self.canvas_qt.draw_idle()
        else:
            self.is_active = False
            self.callback(False)
            if self.handle is None:
                pass
            else:
                self.subplot.lines.remove(self.handle)
                self.handle = None
            self.canvas_qt.draw_idle()

    def restore(self):
        if self.is_active:
            self.set_enabled(True)
        else:
            self.set_enabled(False)

    def move(self, x, y):
        if self.is_vertical:
            self.handle.set_ydata(y)
        else:
            self.handle.set_xdata(x)


class MplWidget(QWidget):
    cursor_selected = None

    def __init__(self, parent=None):
        super().__init__(parent)

        # Matplotlib figure instance passed to FigureCanvas of matplotlib
        # Qt5Agg backend. This returns the matplotlib canvas Qt widget.
        self.canvas_qt = mpl_backend_qt.FigureCanvas(matplotlib.figure.Figure())
        # Basic plot setup
        self.subplot1 = self.canvas_qt.figure.add_subplot(111)

        # Further QtWidget setup
        vertical_layout = QVBoxLayout()
        vertical_layout.addWidget(self.canvas_qt)
        self.setLayout(vertical_layout)

        # Setup callbacks
        self.canvas_qt.mpl_connect("motion_notify_event", self.onMouseMove)
        self.canvas_qt.mpl_connect("pick_event", self.itemPicked)
        self.cursors = [
                Cursor(self.canvas_qt, self.subplot1, name="Hor. Cursor 1",
                    is_vertical=False, linestyle="--"),
                Cursor(self.canvas_qt, self.subplot1, name="Hor. Cursor 2",
                    is_vertical=False, linestyle="-."),
                Cursor(self.canvas_qt, self.subplot1, name="Vert. Cursor 1",
                    is_vertical=True, linestyle="--"),
                Cursor(self.canvas_qt, self.subplot1, name="Vert. Cursor 2",
                    is_vertical=True, linestyle="-."),
                ]
        self.canvas_qt.draw_idle()

    def plot_new(self, time_span, channels, ydata):
        self.subplot1.clear()
        time = np.arange(0.0, time_span, time_span/len(ydata))
        print(f"Len_time: {len(time)}")
        print(f"Len_ydata: {len(ydata[0].x)}")
        for y_i in ydata:
            if len(y_i) > 1:
                self.subplot1.plot(y_i)
#        self.subplot1.legend(('cosinus', 'sinus'),loc='upper right')
        self.subplot1.set_title('Scope Data')
        for i in self.cursors:
            i.restore()
        self.canvas_qt.draw_idle()


    def update_graph_simulation(self):
        fs = 500
        f = 3
        ts = 1/fs
        length_of_signal = 100
        t = np.linspace(0,1,length_of_signal)

        cosinus_signal = np.cos(2*np.pi*f*t)
        sinus_signal = np.sin(2*np.pi*f*t)

        self.subplot1.clear()
        self.subplot1.plot(t, cosinus_signal)
        self.subplot1.plot(t, sinus_signal)
        self.subplot1.legend(('cosinus', 'sinus'),loc='upper right')
        self.subplot1.set_title('Cosinus - Sinus Signal')
        for i in self.cursors:
            i.restore()
        self.canvas_qt.draw_idle()

    def onMouseMove(self, event):
        if self.cursor_selected is not None:
            self.cursor_selected.move(event.xdata, event.ydata)
            self.canvas_qt.draw_idle()

    def itemPicked(self, event):
        cursor_handles = [i.handle for i in self.cursors]
        if event.artist in cursor_handles:
            # Toggle
            if self.cursor_selected is None:
                index = cursor_handles.index(event.artist)
                self.cursor_selected = self.cursors[index]
                print(f"Selected cursor: {self.cursor_selected.name}")
            else:
                # When two or more curors are inside the pick radius, multiple
                # events are triggered when clicking. We do not want to disable
                # the cursor that was activated just with this click, i.e. we
                # have to ignore any further events when a cursor is already
                # activated.
                if self.cursor_selected.handle is event.artist:
                    print(f"Cursor deactivated: {self.cursor_selected.name}")
                    self.cursor_selected = None

