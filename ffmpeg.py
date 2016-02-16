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
import logging
import os
import sys
import subprocess
import threading
import time

import requests
import wx
from wx.lib.pubsub import pub

# Is this how the cool kids do it?
if sys.version_info[0:2] < (3, 3):
    from shutilwhich import which
else:
    from shutil import which


class FFmpegDownloaderThread(threading.Thread):
    def __init__(self, url, file_size):
        threading.Thread.__init__(self)
        self.url = url
        self.file_size = file_size
        self.downloading = True
        self.daemon = True
        self.start()

    def abort_dl(self):
        self.downloading = False

    # Essentially the best_block_size() function in youtube-dl.
    def get_chunk_size(self, time, bytes):
        pass

    def run(self):
        file_size_dl = 0
        now = time.time()
        response = requests.get(self.url, stream=True)
        # chunk_size=1024 used to be fairly quick when testing, but now it's slow as a snail. weird. 1 MB chunks instead
        data_chunks = response.iter_content(chunk_size=1024 ** 2)
        with open('bin/ffmpeg.7z', 'wb') as f:
            while self.downloading:
                try:
                    chunk = next(data_chunks)
                    file_size_dl += len(chunk)
                    if chunk:
                        f.write(chunk)
                        f.flush()
                        os.fsync(f.fileno())
                    pub.sendMessage("progress_update", message=file_size_dl)
                except StopIteration:
                    after = time.time()
                    print(after - now)
                    pub.sendMessage("completed")
                    break


class FFmpegDownloader(wx.ProgressDialog):
    def __init__(self, parent, url):
        file_size = int(requests.head(url).headers["Content-Length"])
        wx.ProgressDialog.__init__(self, "Download in progress", "Downloading FFmpeg...", file_size // 1024, parent,
                                   style=wx.PD_APP_MODAL | wx.PD_ELAPSED_TIME | wx.PD_REMAINING_TIME | wx.PD_AUTO_HIDE |
                                   wx.PD_CAN_ABORT)

        pub.subscribe(self.update, "progress_update")
        pub.subscribe(self.complete, "completed")
        self.downloader = FFmpegDownloaderThread(url, file_size)

    def update(self, message):
        if not self.Update(value=message//1024)[0]:
            # Cancel button pressed
            self.Pulse("Aborting...")
            self.downloader.abort_dl()
            wx.MessageDialog(self, "Aborted! FFmpeg was not downloaded.", "pyjam", wx.ICON_EXCLAMATION).ShowModal()
            wx.CallAfter(self.Destroy)

    def complete(self):
        wx.MessageDialog(self, "FFmpeg was downloaded succesfully!", "pyjam").ShowModal()
        wx.CallAfter(self.Destroy)


class FFmpegConvertDialog(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, title='Audio Converter', style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        wx.StaticText(self, label="Hi, I don't know how to program.", pos=(self.GetSize()[0] // 2, self.GetSize()[1] // 2))

        wx.MessageDialog(self, "Not implemented!", "pyjam").ShowModal()

        self.Center()
        self.ShowModal()


def find():
    # type: () -> str
    if sys.platform == "win32":
        return which('ffmpeg.exe') or which('bin/ffmpeg.exe')
    else:
        # I don't know if this works.
        return which('ffmpeg') or which('bin/ffmpeg')


def convert_audio(file, dest, rate, vol, codec="pcm_s16le"):
    # type: (str, str, str, str, str) -> None
    subprocess.call("{bin} -y -i {file} -f -ac {codec} -ar {rate} -vol {vol} {destination}.wav".format(bin=find(),
                                                                                                       file=file,
                                                                                                       codec=codec,
                                                                                                       rate=rate,
                                                                                                       dest=dest))

logger = logging.getLogger('jam')
