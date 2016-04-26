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


class TrimmerPanel(wx.Panel):
    def __init__(self, parent):
        super(TrimmerPanel, self).__init__(parent=parent)
        self.parent = parent

        self.start = wx.SpinCtrlDouble(self, style=wx.SP_WRAP | wx.SP_ARROW_KEYS)
        self.stop = wx.SpinCtrlDouble(self)

        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(self.start, 0, wx.ALL, 5)
        top_sizer.Add(self.stop, 0, wx.ALL, 5)

        self.Bind(wx.EVT_SPINCTRLDOUBLE, source=self.start, handler=self.parent.on_change)
        self.Bind(wx.EVT_SPINCTRLDOUBLE, source=self.stop, handler=self.parent.on_change)

        self.SetSizerAndFit(top_sizer)

    def set_times(self, times):
        self.start.SetValue(np.minimum(*times))
        self.stop.SetValue(np.maximum(*times))

    def set_max(self, max_time):
        self.start.Max = max_time
        self.stop.Max = max_time


class AudioTrimmer(wx.Frame):
    def __init__(self, parent=None):
        super(AudioTrimmer, self).__init__(parent)

        sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.client = plot.PlotCanvas(self)
        self.client.canvas.Bind(wx.EVT_LEFT_DOWN, self.lmb_down)
        self.client.canvas.Bind(wx.EVT_LEFT_UP, self.lmb_up)
        self.client.canvas.Bind(wx.EVT_MOTION, self.mouse_motion)
        self.client.EnableAxesValues = (True, False, False, False)
        self.client.EnableGrid = (True, False)
        self.client.AbsScale = (True, False)
        self.client.EnableAntiAliasing = True

        self.panel = TrimmerPanel(self)

        sizer.Add(self.client, 1, wx.EXPAND, 0)
        sizer.Add(self.panel, 0, wx.EXPAND, 0)

        self.mc = wx.media.MediaCtrl(parent=self, style=wx.SIMPLE_BORDER)

        self.selected = np.array([0.0, 0.0])
        self.maximum = 0.0
        self.minimum = 0.0

        self.timer = wx.Timer(self)

        self.dragged = False

        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_TIMER, self.on_timer)
        self.Bind(wx.EVT_IDLE, self.on_idle)
        self.load()
        self.SetSizer(sizer)
        self.Show()

    def on_size(self, event):
        self.resized = True
        event.Skip()

    def on_idle(self, event):
        if self.resized:
            self.draw_box()
            self.dragged = True
            self.resized = False

    def on_change(self, event):
        if self.dragged:
            self.draw_box()
        else:
            self.dragged = True
        self.selected[0] = self.panel.start.GetValue()
        self.selected[1] = self.panel.stop.GetValue()
        self.set_min_max()
        self.draw_box()
        self.play_song()

    def set_min_max(self):
        self.maximum = max(0, min(np.maximum(*self.selected) * 1000, self.mc.Length()))
        self.minimum = max(0, min(np.minimum(*self.selected) * 1000, self.mc.Length()))

    def mouse_motion(self, event):
        if event.LeftIsDown():
            if self.dragged:
                self.draw_box()
            else:
                self.dragged = True

            self.selected[1] = self.client.GetXY(event)[0]
            self.draw_box()
            self.set_min_max()
            self.panel.set_times((self.selected[0], self.selected[1]))

    def lmb_down(self, event):
        if self.dragged:
            self.draw_box()
            self.dragged = False
        self.selected[0] = self.client.GetXY(event)[0]
        self.set_min_max()

    def lmb_up(self, event):
        self.selected[1] = self.client.GetXY(event)[0]
        self.panel.set_times((self.selected[0], self.selected[1]))
        self.set_min_max()
        self.play_song()

    def draw_box(self):
        x1, x2 = self.client._point2ClientCoord(self.selected[0], self.selected[1])[::2]
        dc = wx.ClientDC(self.client.canvas)
        dc.SetLogicalFunction(wx.INVERT)
        dc.DrawRectangle(x1, 0, x2, dc.GetSize()[1])
        dc.SetLogicalFunction(wx.COPY)

    def clear(self):
        dc = wx.ClientDC(self.client.canvas)
        dc.Clear()
        if self.client.last_draw is not None:
            self.client.Draw(self.client.last_draw[0])

    def load(self):
        dialog = wx.FileDialog(self, wildcard="WAV files (*.wav)|*.wav")
        if dialog.ShowModal() == wx.ID_CANCEL:
            self.Destroy()

        file = dialog.GetPath()
        wav = wave.open(file)

        signal = np.fromstring(wav.readframes(-1), 'Int16')[::1000]
        length = (len(signal) * 1000) / wav.getframerate()
        samples = np.linspace(0, length, num=len(signal))
        waveform = np.column_stack((samples, signal))
        self.panel.set_max(length)

        lines = plot.PolyLine(waveform, colour='blue', width=1.5)
        self.client.Draw(plot.PlotGraphics((lines,), os.path.basename(file), "Time (seconds)"))
        self.mc.Load(file)
        self.timer.Start(100)

    def play_song(self):
        self.mc.Play()
        self.mc.SetVolume(0.5)
        self.mc.Seek(self.minimum)

    def on_timer(self, event):
        if not self.mc:
            return

        if not (self.minimum < self.mc.Tell() < self.maximum):
            self.play_song()

if __name__ == "__main__":
    app = wx.App()
    AudioTrimmer()
    app.MainLoop()
