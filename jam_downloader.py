# Copyright (C) 10se1ucgo 2016
#
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
from __future__ import division
import logging
import os
import threading

import youtube_dl
import wx

from jam_tools import wrap_exceptions


class AudioDownloaderThread(threading.Thread):
    def __init__(self, parent, song_urls, dest, opts=None):
        super(AudioDownloaderThread, self).__init__()
        self.parent = parent
        self.song_urls = song_urls

        if opts is None:
            self.opts = {'format': 'bestaudio/best', 'outtmpl': os.path.join(dest, '%(title)s.%(ext)s'),
                         'progress_hooks': [self.progress_hook]}
        else:
            self.opts = opts

        self.downloaded = 0
        self.progress = 0

        self.running = True
        self.daemon = True
        self.start()

    def abort(self):
        self.running = False

    @wrap_exceptions
    def run(self):
        song_urls = iter(self.song_urls)
        errors = 0
        with youtube_dl.YoutubeDL(self.opts) as yt:
            while self.running:
                try:
                    song_url = next(song_urls)
                    logger.info("Downloading audio/video from {url}".format(url=song_url))
                    try:
                        yt.download([song_url])
                    except youtube_dl.DownloadError:
                        errors += 1
                    self.downloaded += self.progress
                    self.parent.update(self.downloaded)
                except StopIteration:
                    self.parent.complete(errors)
                    break

    def progress_hook(self, status):
        try:
            total = int(status.get('total_bytes'))
            downloaded = int(status.get('downloaded_bytes'))
        except (ValueError, TypeError):
            return

        self.progress = round((downloaded / total) * 100)
        self.parent.update(self.downloaded + self.progress)



class AudioDownloaderDialog(wx.Dialog):
    def __init__(self, parent):
        super(AudioDownloaderDialog, self).__init__(parent, title="Audio Downloader",
                                                    style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.parent = parent

        self.audio_link = wx.TextCtrl(self, name="Link to audio")
        audio_link_text = wx.StaticText(self, label="Link to audio")

        self.out_dir = wx.DirPickerCtrl(self, name="Output directory")
        out_dir_text = wx.StaticText(self, label="Output directory")

        top_sizer = wx.BoxSizer(wx.VERTICAL)
        dir_sizer = wx.BoxSizer(wx.VERTICAL)
        button_sizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)

        dir_sizer.Add(audio_link_text, 0, wx.ALL ^ wx.LEFT | wx.ALIGN_LEFT, 3)
        dir_sizer.Add(self.audio_link, 0, wx.ALL ^ wx.LEFT ^ wx.TOP | wx.ALIGN_LEFT | wx.EXPAND, 5)
        dir_sizer.Add(out_dir_text, 0, wx.ALL ^ wx.LEFT | wx.ALIGN_LEFT, 3)
        dir_sizer.Add(self.out_dir, 0, wx.ALL ^ wx.LEFT ^ wx.TOP | wx.ALIGN_LEFT | wx.EXPAND, 5)
        top_sizer.Add(dir_sizer, 1, wx.ALL | wx.EXPAND | wx.ALIGN_TOP, 5)
        top_sizer.Add(button_sizer, 0, wx.ALL | wx.CENTER, 5)

        self.Bind(wx.EVT_BUTTON, self.on_ok, id=wx.ID_OK)

        self.downloader = None
        self.progress_dialog = None
        self.num_songs = 0

        self.SetSizer(top_sizer)
        self.Center()
        self.ShowModal()

    def on_ok(self, event):
        with youtube_dl.YoutubeDL() as yt_dl:
            result = wrap_exceptions(yt_dl.extract_info)(self.audio_link.GetValue(), download=False, process=False)

        if 'entries' in result:  # True if link is a playlist
            songs = [vid['url'] for vid in list(result['entries'])]
        else:
            songs = [self.audio_link.GetValue()]
        self.num_songs = len(songs)

        self.progress_dialog = wx.ProgressDialog("Download", "Downloading songs...", self.num_songs * 100, parent=self,
                                                 style=wx.PD_ELAPSED_TIME | wx.PD_CAN_ABORT |
                                                       wx.PD_AUTO_HIDE | wx.PD_APP_MODAL)

        self.downloader = AudioDownloaderThread(self, songs, self.out_dir.GetPath())

    def update(self, message):
        progress = "{songs} out of {total}".format(songs=message // 100, total=self.num_songs)
        if self.progress_dialog:
            if not self.progress_dialog.Update(value=message, newmsg="Downloaded: {prog}".format(prog=progress))[0]:
                self.downloader.abort()

                alert_string = "Aborted! Only {progress} songs were downloaded".format(progress=progress)
                alert = wx.MessageDialog(self.progress_dialog, alert_string, "pyjam", wx.ICON_EXCLAMATION)
                alert.ShowModal()
                alert.Destroy()

                logging.info("Audio download canceled.")
                logging.info(alert_string)
                wx.CallAfter(self.progress_dialog.Destroy)

    def complete(self, message):
        if self.progress_dialog:
            done_string = "Songs downloaded with {errors} error(s)".format(errors=message)
            done_message = wx.MessageDialog(self.progress_dialog, done_string, "pyjam")
            done_message.ShowModal()
            done_message.Destroy()

            logging.info(done_string)
            wx.CallAfter(self.progress_dialog.Destroy)

logger = logging.getLogger('jam.downloader')
