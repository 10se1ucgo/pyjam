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
from __future__ import division

import logging
import os
import subprocess
import sys
import threading

import requests
import wx
import wx.lib.intctrl as intctrl

import seven_zip
from jam_tools import wrap_exceptions

try:
    from shutil import which
except ImportError:
    from shutilwhich import which

logger = logging.getLogger('jam.ffmpeg')
ENCODER_START = 36
ENCODER_LEN = 34
PD_STYLE = wx.PD_APP_MODAL | wx.PD_AUTO_HIDE | wx.PD_CAN_ABORT | wx.PD_ELAPSED_TIME | wx.PD_ESTIMATED_TIME

# Converted from a list of MIME types. If there is something missing, file an issue or create a PR!
FILE_EXTS = (
    '*.3g2', '*.3gp', '*.aac', '*.adp', '*.aif', '*.aifc', '*.aiff', '*.asf', '*.asx', '*.au', '*.avi', '*.caf',
    '*.dra', '*.dts', '*.dtshd', '*.dvb', '*.ecelp4800', '*.ecelp7470', '*.ecelp9600', '*.eol', '*.f4v', '*.flac',
    '*.fli', '*.flv', '*.fvt', '*.h261', '*.h263', '*.h264', '*.jpgm', '*.jpgv', '*.jpm', '*.kar', '*.lvp',
    '*.m1v', '*.m2a', '*.m2v', '*.m3a', '*.m3u', '*.m4a', '*.m4u', '*.m4v', '*.mid', '*.midi', '*.mj2', '*.mjp2',
    '*.mk3d', '*.mka', '*.mks', '*.mkv', '*.mng', '*.mov', '*.movie', '*.mp2', '*.mp2a', '*.mp3', '*.mp4',
    '*.mp4a', '*.mp4v', '*.mpa', '*.mpe', '*.mpeg', '*.mpg', '*.mpg4', '*.mpga', '*.mxu', '*.oga', '*.ogg',
    '*.ogv', '*.pya', '*.pyv', '*.qt', '*.ra', '*.ram', '*.rip', '*.rmi', '*.rmp', '*.s3m', '*.sil', '*.smv',
    '*.snd', '*.spx', '*.uva', '*.uvh', '*.uvm', '*.uvp', '*.uvs', '*.uvu', '*.uvv', '*.uvva', '*.uvvh', '*.uvvm',
    '*.uvvp', '*.uvvs', '*.uvvu', '*.uvvv', '*.viv', '*.vob', '*.wav', '*.wax', '*.weba', '*.webm', '*.wm',
    '*.wma', '*.wmv', '*.wmx', '*.wvx', '*.xm'
)


class FFmpegDownloaderThread(threading.Thread):
    def __init__(self, parent, url, file_size):
        super(FFmpegDownloaderThread, self).__init__()
        self.url = url
        self.parent = parent
        self.file_size = file_size
        self._abort = threading.Event()

        self.daemon = True

    def abort(self):
        logger.debug("Aborting FFmpeg downloader thread.")
        self._abort.set()

    def is_aborted(self):
        return self._abort.isSet()

    @wrap_exceptions
    def run(self):
        file_size_dl = 0
        response = requests.get(self.url, stream=True)
        data_chunks = response.iter_content(chunk_size=1024)

        if not os.path.exists('bin'):
            os.mkdir('bin')

        with open('bin/ffmpeg.7z', 'wb') as f:
            while not self.is_aborted():
                try:
                    chunk = next(data_chunks)
                    file_size_dl += len(chunk)
                    logger.debug("FFmpeg downloader: Downloaded chunk: {chunk}".format(chunk=len(chunk)))
                    logger.debug("FFmpeg downloader: Total downloaded so far: {total}".format(total=file_size_dl))
                    logger.debug("FFmpeg downloader: Remaining: {r}".format(r=self.file_size - file_size_dl))
                    if chunk:
                        f.write(chunk)
                        f.flush()
                        # This makes the download super slow.
                        # os.fsync(f.fileno())
                    wx.CallAfter(self.parent.update, message=file_size_dl)
                except StopIteration:
                    wx.CallAfter(self.parent.complete)
                    break


class FFmpegDownloader(wx.ProgressDialog):
    def __init__(self, parent, url):
        self.file_size = int(requests.head(url).headers["Content-Length"])
        super(FFmpegDownloader, self).__init__(title="pyjam FFmpeg Downloader", message="Downloading FFmpeg...",
                                               maximum=self.file_size // 1024, parent=parent, style=PD_STYLE)

        self.downloader = FFmpegDownloaderThread(parent=self, url=url, file_size=self.file_size)
        self.downloader.start()

    def update(self, message):
        if self and self.downloader.isAlive():  # True PD has not been destroyed.
            if not self.Update(value=message // 1024)[0]:
                # Cancel button pressed
                self.downloader.abort()
                self.downloader.join()
                logger.info("FFmpeg download canceled.")

                alert = wx.MessageDialog(parent=self, message="Aborted! FFmpeg was not downloaded.", caption="pyjam",
                                         style=wx.ICON_EXCLAMATION)
                alert.ShowModal()
                alert.Destroy()

                wx.CallAfter(self.Destroy)

    def complete(self):
        if self:
            logger.info("FFmpeg download complete.")

            if seven_zip.find() is None:
                message_str = "FFmpeg was downloaded succesfully!\nPlease extract it. (bin/ffmpeg.7z)"
            else:
                seven_zip.extract_single(os.path.normpath('bin/ffmpeg.7z'), 'ffmpeg.exe', os.path.normpath('bin/'))
                os.remove(os.path.normpath('bin/ffmpeg.7z'))
                message_str = "FFmpeg was downloaded succesfully!"
            message = wx.MessageDialog(self, message_str, "pyjam")
            message.ShowModal()
            message.Destroy()

            wx.CallAfter(self.Destroy)


class FFmpegConvertThread(threading.Thread):
    def __init__(self, parent, dest, rate, vol, songs):
        super(FFmpegConvertThread, self).__init__()
        self.parent = parent
        self.dest = dest
        self.rate = rate
        self.vol = vol
        self.songs = songs
        self.converted = 0
        self._abort = threading.Event()

        self.daemon = True

    def abort(self):
        logger.debug("Aborting FFmpeg converter thread.")
        self._abort.set()

    def is_aborted(self):
        return self._abort.isSet()

    @wrap_exceptions
    def run(self):
        tracks = iter(self.songs)
        errors = []
        while not self.is_aborted():
            try:
                track = next(tracks)
                file = os.path.join(self.dest, os.path.splitext(os.path.basename(track))[0])
                logger.debug("FFmpeg converter: Total converted so far: {total}".format(total=self.converted // 2))
                logger.debug("FFmpeg converter: Remaining: {r}".format(r=len(self.songs) - self.converted // 2))
                logger.debug("Converting {track} with params: rate: {rate} volume: {vol}".format(track=track,
                                                                                                 rate=self.rate,
                                                                                                 vol=self.vol))
                try:
                    logger.info(convert_audio(track, file, self.rate, self.vol).decode('ascii', 'replace'))
                except subprocess.CalledProcessError as e:
                    logger.exception("FFmpeg converter: Couldn't convert {track}".format(track=track))
                    logger.critical("FFmpeg converter: Error output log\n" + e.output.decode('ascii', 'replace'))
                    errors.append(track)
                    # File's headers aren't stripped, which normally would increase self.converted by 1.
                    self.converted += 1
                else:
                    self.strip_encoder(file)
                self.converted += 1
                wx.CallAfter(self.parent.update, message=self.converted)
            except StopIteration:
                wx.CallAfter(self.parent.complete, message=errors)
                break

    @wrap_exceptions
    def strip_encoder(self, file):
        logger.debug("Stripping metadata from {file}".format(file=file + '.wav'))
        with open(file + '.wav', 'rb') as f:
            wav = bytearray(f.read())
        del wav[ENCODER_START:ENCODER_START + ENCODER_LEN]
        with open(file + '.wav', 'wb') as f:
            f.write(wav)
        self.converted += 1
        wx.CallAfter(self.parent.update, message=self.converted)


class FFmpegConvertDialog(wx.Dialog):
    def __init__(self, parent, rate=None, out_dir=None, in_dir=None):
        super(FFmpegConvertDialog, self).__init__(parent=parent, title="pyjam Audio Converter",
                                                  style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

        self.in_dir = in_dir

        self.game_rate = intctrl.IntCtrl(self)
        game_rate_text = wx.StaticText(self, label="Audio rate")
        if rate is not None:
            self.game_rate.SetValue(rate)

        self.volume = wx.SpinCtrl(self, initial=85)
        volume_text = wx.StaticText(self, label="Volume %")

        self.in_picker = wx.FilePickerCtrl(self, style=wx.FLP_USE_TEXTCTRL)
        in_picker_text = wx.StaticText(self, label="Input file names (manually changing them has no effect)")
        self.in_files = []
        # the dumbest thing i've done all year (i'm overriding the controls of the PickerBase)
        for child in self.in_picker.GetChildren():
            if isinstance(child, wx.Button):
                child.Bind(wx.EVT_BUTTON, self.browse)

        self.out_dir = wx.DirPickerCtrl(self, name="Output directory")
        out_dir_text = wx.StaticText(self, label="Output directory")
        if out_dir is not None:
            self.out_dir.SetPath(out_dir)

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
        dir_sizer.Add(in_picker_text, 0, wx.ALL ^ wx.LEFT | wx.ALIGN_LEFT, 3)
        dir_sizer.Add(self.in_picker, 0, wx.ALL ^ wx.LEFT ^ wx.TOP | wx.ALIGN_LEFT | wx.EXPAND, 5)
        dir_sizer.Add(out_dir_text, 0, wx.ALL ^ wx.LEFT | wx.ALIGN_LEFT, 3)
        dir_sizer.Add(self.out_dir, 0, wx.ALL ^ wx.LEFT ^ wx.TOP | wx.ALIGN_LEFT | wx.EXPAND, 5)
        top_sizer.Add(top_row)
        top_sizer.Add(dir_sizer, 1, wx.ALL | wx.EXPAND | wx.ALIGN_TOP, 5)
        top_sizer.Add(button_sizer, 0, wx.ALL | wx.ALIGN_CENTER, 5)

        self.Bind(wx.EVT_BUTTON, self.on_ok, id=wx.ID_OK)

        self.converter = None
        self.progress_dialog = None
        self.num_songs = 0

        self.SetSizer(top_sizer)
        self.Center()
        self.ShowModal()

    def on_ok(self, event):
        self.num_songs = len(self.in_files)
        if self.num_songs <= 0:
            alert = wx.MessageDialog(self, "No songs selected!", "pyjam", wx.ICON_EXCLAMATION)
            alert.ShowModal()
            alert.Destroy()
            return

        self.progress_dialog = wx.ProgressDialog(title="Conversion", message="Converting songs...",
                                                 maximum=self.num_songs * 2, parent=self, style=PD_STYLE)

        self.converter = FFmpegConvertThread(parent=self, dest=self.out_dir.GetPath(), rate=self.game_rate.GetValue(),
                                             vol=self.volume.GetValue(), songs=self.in_files)
        self.converter.start()

    def update(self, message):
        progress = "{songs} out of {total}".format(songs=message // 2, total=self.num_songs)
        if self.progress_dialog and self.converter.isAlive():
            if not self.progress_dialog.Update(value=message, newmsg="Converted: {prog}".format(prog=progress))[0]:
                self.converter.abort()
                self.converter.join()
                self.progress_dialog.Destroy()

                alert_string = "Aborted! Only {progress} songs were converted".format(progress=progress)
                alert = wx.MessageDialog(parent=self, message=alert_string, caption="pyjam", style=wx.ICON_EXCLAMATION)
                alert.ToggleWindowStyle(wx.STAY_ON_TOP)
                alert.ShowModal()
                alert.Destroy()

                logger.info("Audio conversion canceled canceled.")
                logger.info(progress)
                # wx.CallAfter(self.progress_dialog.Destroy)

    def complete(self, message):
        if self.progress_dialog:
            self.converter.join()
            if len(message) != 0:
                done_string = "Songs converted with {errors} error(s)".format(errors=len(message))
            else:
                done_string = "All songs were converted succesfully!"
            done_message = wx.MessageDialog(parent=self, message=done_string, caption="pyjam")
            done_message.ToggleWindowStyle(wx.STAY_ON_TOP)
            done_message.ShowModal()
            done_message.Destroy()

            if len(message) != 0:
                errors = '\n'.join(message)
                error_dialog = wx.MessageDialog(parent=self, message="The following files caused errors\n" + errors,
                                                caption="Conversion Error!", style=wx.OK | wx.ICON_ERROR)
                error_dialog.ShowModal()
                error_dialog.Destroy()
                logger.critical("Error converting these files\n{errors}".format(errors=errors))

            logger.info(done_string)
            wx.CallAfter(self.progress_dialog.Destroy)

    def browse(self, event):
        wildcard = "Audio and Video files ({wildcards})|{wildcards}".format(wildcards=';'.join(FILE_EXTS))
        file_dialog = wx.FileDialog(self, message="Select files",
                                    style=wx.FD_OPEN | wx.FD_MULTIPLE | wx.FD_FILE_MUST_EXIST, wildcard=wildcard)
        file_dialog.SetDirectory(self.in_dir) if self.in_dir else None
        if file_dialog.ShowModal() != wx.ID_OK:
            file_dialog.Destroy()
            return
        self.in_files = file_dialog.GetPaths()
        self.in_picker.GetTextCtrl().SetValue(str(file_dialog.GetFilenames()).strip('[]'))
        file_dialog.Destroy()


def find():
    # type: () -> str or None
    if sys.platform == "win32":
        ff = which('ffmpeg.exe') or which('bin/ffmpeg.exe') or which('avconv')
    else:
        # ~~I don't know if this works.~~
        # Tested on VM, it worked on Linux Mint.
        ff = which('ffmpeg') or which('bin/ffmpeg') or which('avconv')

    return os.path.normpath(ff) if ff else None


def convert_audio(file, dest, rate, vol, codec="pcm_s16le"):
    rate = str(rate)
    # type: (str, str, int or str, int, str) -> int
    # cmd = '{ff} -y -i "{i}" -map_metadata -1 -ac 1 -aq 100 -acodec {codec} -ar {rate} -af volume={vol} "{dest}.wav"'
    # cmd = cmd.format(ff=find(), i=file, codec=codec, rate=rate, vol=vol / 100, dest=dest)
    cmd = (find(), '-y', '-i', file, '-map_metadata', '-1', '-ac', '1', '-aq', '100',
           '-acodec', codec, '-ar', rate, '-af', 'volume={vol}'.format(vol=vol/100), '{dest}.wav'.format(dest=dest))
    return subprocess.check_output(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
