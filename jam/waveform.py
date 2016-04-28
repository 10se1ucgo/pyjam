# Copyright (C) 10se1ucgo 2016
# This file is part of pyjam.
#
# pyjam is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyjam is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyjam.  If not, see <http://www.gnu.org/licenses/>.

# An experimental waveform viewer. Requires numpy.
import os
import wave

import numpy as np
import wx
import wx.media
import wx.adv
from wx.lib import plot


class WaveformPanel(wx.Panel):
    def __init__(self, parent):
        super(WaveformPanel, self).__init__(parent=parent)
        self.parent = parent

        self.start = wx.SpinCtrlDouble(self)
        self.stop = wx.SpinCtrlDouble(self)

        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(self.start, 0, wx.ALL, 5)
        top_sizer.Add(self.stop, 0, wx.ALL, 5)

        self.Bind(wx.EVT_SPINCTRLDOUBLE, source=self.start, handler=self.on_change)
        self.Bind(wx.EVT_SPINCTRLDOUBLE, source=self.stop, handler=self.on_change)

        self.SetSizerAndFit(top_sizer)

    def set_times(self, times):
        self.start.SetValue(np.minimum(*times))
        self.stop.SetValue(np.maximum(*times))

    def set_max(self, max_time):
        self.start.Max = self.stop.Max = max_time

    def on_change(self, event):
        times = np.array([self.start.GetValue(), self.stop.GetValue()])
        self.start.SetValue(np.minimum(*times))
        self.stop.SetValue(np.maximum(*times))
        self.parent.on_change(times)


class WaveformPlot(wx.Frame):
    def __init__(self, parent, file):
        super(WaveformPlot, self).__init__(parent)

        self.file = file

        self.plot = plot.PlotCanvas(self)
        self.plot.canvas.Bind(wx.EVT_LEFT_DOWN, self.lmb_down)
        self.plot.canvas.Bind(wx.EVT_LEFT_UP, self.lmb_up)
        self.plot.canvas.Bind(wx.EVT_MOTION, self.mouse_motion)
        self.plot.EnableAxesValues = (True, False, False, False)
        self.plot.EnableGrid = (True, False)
        self.plot.AbsScale = (True, False)
        self.plot.EnableAntiAliasing = True

        self.panel = WaveformPanel(self)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.plot, 1, wx.EXPAND, 0)
        sizer.Add(self.panel, 0, wx.EXPAND, 0)
        self.SetSizer(sizer)

        self.player = wx.media.MediaCtrl(parent=self, style=wx.SIMPLE_BORDER)

        self.selected = np.array([0.0, 0.0])
        self.maximum = 0.0
        self.minimum = 0.0
        self.selection_drawn = False
        self.resized = False

        self.timer = wx.Timer(self)

        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_TIMER, self.on_timer)
        self.Bind(wx.EVT_IDLE, self.on_idle)
        self.Bind(wx.EVT_CLOSE, self.on_exit)

        self.load()
        self.Layout()
        self.Show()

    def on_size(self, event):
        self.resized = True
        event.Skip()

    def on_idle(self, event):
        if self.resized:
            self.draw_box()
            self.selection_drawn = True
            self.resized = False
        event.Skip()

    def on_change(self, times):
        if self.selection_drawn:
            self.draw_box()  # clear old
        else:
            self.selection_drawn = True
        self.selected = times
        self.set_min_max()
        self.draw_box()  # draw new
        self.play_song()

    def set_min_max(self):
        self.maximum = max(0, min(np.maximum(*self.selected) * 1000, self.player.Length()))
        self.minimum = max(0, min(np.minimum(*self.selected) * 1000, self.player.Length()))

    def mouse_motion(self, event):
        if event.LeftIsDown():
            if self.selection_drawn:
                self.draw_box()  # clear old
            else:
                self.selection_drawn = True

            self.selected[1] = self.plot.GetXY(event)[0]
            self.draw_box()  # draw new
            self.set_min_max()
            self.panel.set_times(self.selected)

    def lmb_down(self, event):
        if self.selection_drawn:
            self.draw_box()  # clear old
            self.selection_drawn = False
        self.selected[0] = self.plot.GetXY(event)[0]
        self.set_min_max()

    def lmb_up(self, event):
        self.selected[1] = self.plot.GetXY(event)[0]
        self.panel.set_times(self.selected)
        self.set_min_max()
        self.play_song()
        # self.clear()

    def draw_box(self):
        x1, x2 = self.plot._point2ClientCoord(*self.selected)[::2]
        dc = wx.ClientDC(self.plot.canvas)
        dc.SetLogicalFunction(wx.INVERT)
        dc.DrawRectangle(x1, 0, x2, dc.GetSize()[1])
        dc.SetLogicalFunction(wx.COPY)

    # def clear(self):
    #     # An experimental way to clear the canvas without redrawing the plot every time
    #     # dc.Blit() usage from SOF.
    #     if self.selection_drawn:
    #         self.draw_box()  # clear old
    #         self.selection_drawn = False
    #     dc = wx.ClientDC(self.plot.canvas)
    #     size = dc.GetSize()
    #     bmp = wx.Bitmap(size.width, size.height)
    #     prev_dc = wx.MemoryDC()
    #     prev_dc.SelectObject(bmp)
    #     prev_dc.Blit(
    #         0,  # Copy to this X coordinate
    #         0,  # Copy to this Y coordinate
    #         size.width,  # Copy this width
    #         size.height,  # Copy this height
    #         dc,  # From where do we copy?
    #         0,  # What's the X offset in the original DC?
    #         0  # What's the Y offset in the original DC?
    #     )
    #     prev_dc.SelectObject(wx.NullBitmap)
    #     dc.Clear()
    #     dc.DrawBitmap(bmp, 0, 0)
    #     # if self.plot.last_draw is not None:
    #     #     self.plot.Draw(self.plot.last_draw[0])

    def load(self):
        with wave.open(self.file) as wav:
            signal = np.fromstring(wav.readframes(-1), 'Int16')[::1000]
            length = (len(signal) * 1000) / wav.getframerate()
        samples = np.linspace(0, length, num=len(signal))
        waveform = np.column_stack((samples, signal))
        self.panel.set_max(length)

        lines = plot.PolyLine(waveform, colour='blue')
        self.plot.Draw(plot.PlotGraphics((lines,), os.path.basename(self.file), "Time (seconds)"))
        self.player.Load(self.file)
        self.timer.Start(100)

    def play_song(self):
        if not self.maximum or self.maximum == self.minimum:
            self.player.Stop()
            return

        self.player.Play()
        self.player.SetVolume(0.5)
        self.player.Seek(self.minimum)

    def on_timer(self, event):
        if not self.player:
            return

        if not (self.minimum < self.player.Tell() < self.maximum):
            self.play_song()

    def on_exit(self, event):
        # For some reason, the timer still tries to play the song even after the windows is being closed.
        # (probably because window destruction is not synchronous, a wx.Yield() would probably fix it)
        # The timer function even checks to see if the player is still loaded, but apparently the player is not
        # destroyed when the window is destroyed, resulting in the player trying to play a song
        # and Python crashes with exit code -1073741819 (0xC0000005) [Windows]
        self.timer.Stop()
        event.Skip()

if __name__ == "__main__":
    app = wx.App()
    dialog = wx.FileDialog(None, wildcard="WAV files (*.wav)|*.wav")
    if dialog.ShowModal() != wx.ID_CANCEL:
        WaveformPlot(parent=None, file=dialog.GetPath())
    dialog.Destroy()
    app.MainLoop()
