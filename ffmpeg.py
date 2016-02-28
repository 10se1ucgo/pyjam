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

# The downloading stuff here is pretty much Windows only.
import glob
import logging
import os
import sys
import subprocess
import threading

import requests
import wx
from pubsub import pub

import seven_zip

try:
    from shutil import which
except ImportError:
    from shutilwhich import which


class FFmpegDownloaderThread(threading.Thread):
    def __init__(self, url, file_size):
        super(FFmpegDownloaderThread, self).__init__()
        self.url = url
        self.file_size = file_size
        self.downloading = True
        self.daemon = True
        self.start()

    def run(self):
        file_size_dl = 0
        response = requests.get(self.url, stream=True)
        # chunk_size=1024 used to be fairly quick when testing, but now it's slow as a snail. weird. 1 MB chunks instead
        data_chunks = response.iter_content(chunk_size=1024 ** 2)
        if not os.path.exists('bin'):
            os.mkdir('bin')
        with open('bin/ffmpeg.7z', 'wb') as f:
            while self.downloading:
                try:
                    chunk = next(data_chunks)
                    file_size_dl += len(chunk)
                    if chunk:
                        f.write(chunk)
                        f.flush()
                        os.fsync(f.fileno())
                    pub.sendMessage('download_progress_update', message=file_size_dl)
                except StopIteration:
                    break

        pub.sendMessage('download_completed')


class FFmpegDownloader(wx.ProgressDialog):
    def __init__(self, parent, url):
        file_size = int(requests.head(url).headers["Content-Length"])
        wx.ProgressDialog.__init__(self, "Download in progress", "Downloading FFmpeg...", file_size // 1024, parent,
                                   style=wx.PD_APP_MODAL | wx.PD_ELAPSED_TIME | wx.PD_REMAINING_TIME | wx.PD_AUTO_HIDE |
                                         wx.PD_CAN_ABORT)

        pub.subscribe(self.update, 'download_progress_update')
        pub.subscribe(self.complete, 'download_completed')
        self.downloader = FFmpegDownloaderThread(url, file_size)

    def update(self, message):
        if not self.Update(value=message // 1024)[0]:
            # Cancel button pressed
            self.Pulse("Aborting...")
            self.downloader.downloading = False
            os.remove(os.path.normpath('bin/ffmpeg.7z'))
            alert = wx.MessageDialog(self, "Aborted! FFmpeg was not downloaded.", "pyjam", wx.ICON_EXCLAMATION)
            alert.ShowModal()
            alert.Destroy()
            logging.info("FFmpeg download canceled.")
            wx.CallAfter(self.Destroy)

    def complete(self):
        if seven_zip.find() is None:
            message_str = "FFmpeg was downloaded succesfully!\nPlease extract it. (bin/ffmpeg.7z)"
        else:
            seven_zip.extract_single(os.path.normpath('bin/ffmpeg.7z'), 'ffmpeg.exe', os.path.normpath('bin/'))
            os.remove(os.path.normpath('bin/ffmpeg.7z'))
            message_str = "FFmpeg was downloaded succesfully!..."
        message = wx.MessageDialog(self, message_str, "pyjam")
        message.ShowModal()
        message.Destroy()
        logging.info("FFmpeg download complete.")
        wx.CallAfter(self.Destroy)


class FFmpegConvertThread(threading.Thread):
    def __init__(self, dest, rate, vol, songs):
        super(FFmpegConvertThread, self).__init__()
        self.dest = dest
        self.rate = rate
        self.vol = vol
        self.songs = songs
        self.running = True
        self.daemon = True
        self.start()

    def run(self):
        tracks = iter(self.songs)
        converted = 0
        errors = 0
        while self.running:
            try:
                track = next(tracks)
                dest = os.path.join(self.dest, os.path.splitext(os.path.basename(track))[0] + '.wav')
                if convert_audio(track, dest, self.rate, self.vol) != 0:
                    errors += 1
                converted += 1
                pub.sendMessage('conversion_progress_update', message=converted)
            except StopIteration:
                break

        pub.sendMessage('conversion_completed', message=errors)


class FFmpegConvertDialog(wx.Dialog):
    def __init__(self, parent, rate, out):
        wx.Dialog.__init__(self, parent, title="Audio Converter", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

        self.game_rate = wx.TextCtrl(self)
        game_rate_text = wx.StaticText(self, label="Audio rate")
        self.game_rate.SetValue(rate)

        self.volume = wx.SpinCtrl(self, initial=85)
        volume_text = wx.StaticText(self, label="Volume %")

        self.in_dir = wx.DirPickerCtrl(self, name="Input directory")
        in_dir_text = wx.StaticText(self, label="Input directory")

        self.out_dir = wx.DirPickerCtrl(self, name="Output directory")
        out_dir_text = wx.StaticText(self, label="Output directory")
        self.out_dir.SetPath(out)

        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_row = wx.BoxSizer(wx.HORIZONTAL)
        rate_sizer = wx.BoxSizer(wx.VERTICAL)
        vol_sizer = wx.BoxSizer(wx.VERTICAL)
        dir_sizer = wx.BoxSizer(wx.VERTICAL)
        button_sizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)

        rate_sizer.Add(game_rate_text, 0, wx.ALL ^ wx.BOTTOM | wx.ALIGN_LEFT, 5)
        rate_sizer.Add(self.game_rate, 0, wx.ALL | wx.ALIGN_LEFT, 5)
        vol_sizer.Add(volume_text, 0, wx.ALL ^ wx.BOTTOM | wx.ALIGN_LEFT, 5)
        vol_sizer.Add(self.volume, 0, wx.ALL | wx.ALIGN_LEFT, 5)
        top_row.Add(rate_sizer)
        top_row.Add(vol_sizer)
        dir_sizer.Add(in_dir_text, 0, wx.ALL ^ wx.LEFT | wx.ALIGN_LEFT, 3)
        dir_sizer.Add(self.in_dir, 0, wx.ALL ^ wx.LEFT ^ wx.TOP | wx.ALIGN_LEFT | wx.EXPAND, 5)
        dir_sizer.Add(out_dir_text, 0, wx.ALL ^ wx.LEFT | wx.ALIGN_LEFT, 3)
        dir_sizer.Add(self.out_dir, 0, wx.ALL ^ wx.LEFT ^ wx.TOP | wx.ALIGN_LEFT | wx.EXPAND, 5)
        top_sizer.Add(top_row)
        top_sizer.Add(dir_sizer, 1, wx.ALL | wx.EXPAND | wx.ALIGN_TOP, 5)
        top_sizer.Add(button_sizer, 0, wx.ALL | wx.CENTER, 5)

        self.Bind(wx.EVT_BUTTON, self.on_ok, id=wx.ID_OK)
        pub.subscribe(self.update, 'conversion_progress_update')
        pub.subscribe(self.complete, 'conversion_completed')

        self.converter = None
        self.progress_dialog = None
        self.num_songs = 0

        self.SetSizer(top_sizer)
        self.Center()
        self.ShowModal()

    def on_ok(self, event):
        songs = glob.glob(os.path.join(self.in_dir.GetPath(), '*'))
        self.num_songs = len(songs)
        self.converter = FFmpegConvertThread(self.out_dir.GetPath(), self.game_rate.GetValue(),
                                             self.volume.GetValue(), songs)

        self.progress_dialog = wx.ProgressDialog("Conversion", "Converting songs...", self.num_songs, parent=self,
                                                 style=wx.PD_APP_MODAL | wx.PD_ELAPSED_TIME | wx.PD_AUTO_HIDE |
                                                 wx.PD_CAN_ABORT | wx.PD_SMOOTH)

    def update(self, message):
        progress = "{songs} out of {total}".format(songs=message, total=self.num_songs)
        if not self.progress_dialog.Update(value=message, newmsg="Converted: {progress}".format(progress=progress))[0]:
            self.progress_dialog.Pulse("Aborting...")
            self.converter.running = False

            alert_string = "Aborted! Only {progress} songs were converted".format(progress=progress)
            alert = wx.MessageDialog(self, alert_string, "pyjam", wx.ICON_EXCLAMATION)
            alert.ShowModal()
            alert.Destroy()

            logging.info("Audio conversion canceled canceled.")
            logging.info(progress)
            wx.CallAfter(self.progress_dialog.Destroy)

    def complete(self, message):
        done_string = "Songs converted with {errors} error(s)".format(errors=message)
        done_message = wx.MessageDialog(self, done_string, "pyjam")
        done_message.ShowModal()
        done_message.Destroy()

        logging.info(done_string)
        wx.CallAfter(self.progress_dialog.Destroy)


def find():
    # type: () -> str
    if sys.platform == "win32":
        return which('ffmpeg.exe') or which('bin/ffmpeg.exe')
    else:
        # ~~I don't know if this works.~~
        # Tested on VM, it worked on Linux Mint.
        return which('ffmpeg') or which('bin/ffmpeg')


def convert_audio(file, dest, rate, vol, codec="pcm_s16le"):
    # type: (str, str, str, str, str) -> None
    return subprocess.call('{ff} -y -i "{i}" -f wav -ac 1 -acodec {codec} -ar {rate} -vol {vol} "{dest}".wav'.format(
       ff=find(),
       i=file,
       codec=codec,
       rate=rate,
       vol=vol,
       dest=dest)
    )


logger = logging.getLogger('jam.ffmpeg')
