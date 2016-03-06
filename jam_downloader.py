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

PD_STYLE = wx.PD_APP_MODAL | wx.PD_AUTO_HIDE | wx.PD_CAN_ABORT | wx.PD_ELAPSED_TIME | wx.PD_ESTIMATED_TIME
logger = logging.getLogger('jam.downloader')


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

        self.running = True
        self.daemon = True
        self.start()

    def abort(self):
        self.running = False

    @wrap_exceptions
    def run(self):
        song_urls = iter(self.song_urls)
        errors = []
        with youtube_dl.YoutubeDL(self.opts) as yt:
            while self.running:
                try:
                    song_url = next(song_urls)
                    logger.info("Downloading audio/video from {url}".format(url=song_url))
                    try:
                        yt.download([song_url])
                    except youtube_dl.DownloadError:
                        errors.append(song_url)
                    self.downloaded += 100
                    wx.CallAfter(self.parent.update, message=self.downloaded)
                except StopIteration:
                    wx.CallAfter(self.parent.complete, message=errors)
                    break

    def progress_hook(self, status):
        try:
            total = int(status.get('total_bytes'))
            downloaded = int(status.get('downloaded_bytes'))
        except (ValueError, TypeError):
            return

        percent = round((downloaded / total) * 100)
        wx.CallAfter(self.parent.update, message=self.downloaded + percent)


class AudioDownloaderDialog(wx.Dialog):
    def __init__(self, parent):
        super(AudioDownloaderDialog, self).__init__(parent, title="Audio Downloader",
                                                    style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.parent = parent

        self.audio_link = wx.TextCtrl(self, name="URL")
        audio_link_text = wx.StaticText(self, label="URL")

        self.out_dir = wx.DirPickerCtrl(self, name="Output directory", path=os.path.abspath("downloads"))
        out_dir_text = wx.StaticText(self, label="Output directory")

        warning_text = wx.StaticText(self, style=wx.ALIGN_CENTRE_HORIZONTAL,
                                     label=("Note: The program will freeze for a bit while it processes the URL "
                                            "before downloading"))
        warning_text.Wrap(self.GetSize()[0])

        top_sizer = wx.BoxSizer(wx.VERTICAL)
        control_sizer = wx.BoxSizer(wx.VERTICAL)
        text_sizer = wx.BoxSizer(wx.VERTICAL)
        button_sizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)

        control_sizer.Add(audio_link_text, 0, wx.ALL ^ wx.LEFT | wx.ALIGN_LEFT, 3)
        control_sizer.Add(self.audio_link, 0, wx.ALL ^ wx.LEFT ^ wx.TOP | wx.ALIGN_LEFT | wx.EXPAND, 5)
        control_sizer.Add(out_dir_text, 0, wx.ALL ^ wx.LEFT | wx.ALIGN_LEFT, 3)
        control_sizer.Add(self.out_dir, 0, wx.ALL ^ wx.LEFT ^ wx.TOP | wx.ALIGN_LEFT | wx.EXPAND, 5)
        text_sizer.Add(warning_text, 0, wx.ALL | wx.ALIGN_CENTER, 5)
        top_sizer.Add(control_sizer, 1, wx.ALL | wx.EXPAND | wx.ALIGN_TOP, 5)
        top_sizer.Add(text_sizer, 0, wx.ALL | wx.ALIGN_CENTER, 5)
        top_sizer.Add(button_sizer, 0, wx.ALL | wx.ALIGN_CENTER, 5)

        self.Bind(wx.EVT_BUTTON, handler=self.on_ok, id=wx.ID_OK)

        self.downloader = None
        self.progress_dialog = None
        self.num_songs = 0

        self.SetSizerAndFit(top_sizer)
        self.Center()
        self.ShowModal()

    def on_ok(self, event):
        with youtube_dl.YoutubeDL() as yt_dl:
            try:
                result = yt_dl.extract_info(self.audio_link.GetValue(), download=False, process=False)
            except youtube_dl.DownloadError:
                error = wx.MessageDialog(parent=wx.GetApp().GetTopWindow(),
                                         message="Invalid/Unsupported URL!",
                                         caption="Error!", style=wx.OK | wx.ICON_WARNING)
                error.ShowModal()
                error.Destroy()
                return

        if 'entries' in result:  # True if link is a playlist
            songs = [vid['url'] for vid in list(result['entries'])]
        else:
            songs = [self.audio_link.GetValue()]
        self.num_songs = len(songs)

        self.progress_dialog = wx.ProgressDialog(title="Download", message="Downloading songs...",
                                                 maximum=self.num_songs * 100, parent=self, style=PD_STYLE)

        self.downloader = AudioDownloaderThread(self, songs, self.out_dir.GetPath())

    def update(self, message):
        progress = "{songs} out of {total}".format(songs=message // 100, total=self.num_songs)
        if self.progress_dialog:
            if not self.progress_dialog.Update(value=message, newmsg="Downloaded: {prog}".format(prog=progress))[0]:
                self.downloader.abort()
                self.downloader.join()

                alert_string = "Aborted! Only {progress} songs were downloaded".format(progress=progress)
                alert = wx.MessageDialog(parent=self, message=alert_string, caption="pyjam", style=wx.ICON_EXCLAMATION)
                alert.ShowModal()
                alert.Destroy()

                logging.info("Audio download canceled.")
                logging.info(alert_string)
                wx.CallAfter(self.progress_dialog.Destroy)

    def complete(self, message):
        if self.progress_dialog:
            self.downloader.join()
            if len(message) != 0:
                done_string = "Songs downloaded with {errors} error(s)".format(errors=len(message))
            else:
                done_string = "All songs were downloaded succesfully!"
            logging.info(done_string)
            done_message = wx.MessageDialog(parent=self, message=done_string, caption="pyjam")
            done_message.ShowModal()
            done_message.Destroy()

            if len(message) != 0:
                errors = '\n'.join(message)
                error_dialog = wx.MessageDialog(parent=self, message="The following URLs caused errors\n" + errors,
                                                caption="Download Error!", style=wx.ICON_ERROR)
                error_dialog.ShowModal()
                error_dialog.Destroy()
                logger.critical("Error downloading these these URLs:\n{errors}".format(errors=errors))

            self.progress_dialog.Destroy()
            self.Destroy()
            wx.CallAfter(self.parent.convert, event=None, in_dir=self.out_dir.GetPath())
