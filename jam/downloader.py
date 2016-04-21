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
import collections
import logging
import os
import threading
import webbrowser

import requests
import youtube_dl
import wx
from ObjectListView import ColumnDefn, ObjectListView

from .common import wrap_exceptions, get_path

logger = logging.getLogger(__name__)
PD_STYLE = wx.PD_APP_MODAL | wx.PD_AUTO_HIDE | wx.PD_CAN_ABORT | wx.PD_ELAPSED_TIME | wx.PD_ESTIMATED_TIME


class DownloaderThread(threading.Thread):
    def __init__(self, parent, song_urls, dest, opts=None):
        super(DownloaderThread, self).__init__()
        self.parent = parent
        self.song_urls = song_urls
        self.opts = opts or {'format': 'bestaudio/best', 'outtmpl': get_path(dest, '%(title)s.%(ext)s'),
                             'progress_hooks': [self.progress_hook], 'logger': logger}
        self.downloaded = 0
        self._abort = threading.Event()

        self.daemon = True

    def abort(self):
        logger.info("Aborting audio/video downloader thread.")
        self._abort.set()

    def is_aborted(self):
        return self._abort.isSet()

    @wrap_exceptions
    def run(self):
        song_urls = iter(self.song_urls)
        errors = []
        with youtube_dl.YoutubeDL(self.opts) as yt:
            while not self.is_aborted():
                try:
                    song_url = next(song_urls)
                    logger.info("Downloading audio/video from {url}".format(url=song_url))
                    try:
                        yt.download([song_url])
                    except youtube_dl.DownloadError:
                        errors.append(song_url)
                    self.downloaded += 100
                    wx.CallAfter(self.parent.download_update, message=self.downloaded)
                except StopIteration:
                    wx.CallAfter(self.parent.download_complete, errors=errors)
                    break

    @wrap_exceptions
    def progress_hook(self, status):
        try:
            total = int(status.get('total_bytes'))
            downloaded = int(status.get('downloaded_bytes'))
        except (ValueError, TypeError):
            return

        percent = round((downloaded / total) * 100)
        wx.CallAfter(self.parent.download_update, message=self.downloaded + percent)


class DownloaderDialog(wx.Dialog):
    def __init__(self, parent):
        super(DownloaderDialog, self).__init__(parent, title="pyjam Downloader",
                                               style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.parent = parent

        self.audio_links = wx.TextCtrl(self)
        audio_link_text = wx.StaticText(self, label="URL(s) (Separate with commas)")

        self.out_dir = wx.DirPickerCtrl(self, path=os.path.abspath("downloads"))
        out_dir_text = wx.StaticText(self, label="Output directory")

        warning_text = wx.StaticText(self, style=wx.ALIGN_CENTRE_HORIZONTAL,
                                     label=("Note: The program will freeze for a bit while it processes the URL "
                                            "before downloading"))
        warning_text.Wrap(self.GetSize()[0])

        search_button = wx.Button(self, label="Search")

        top_sizer = wx.BoxSizer(wx.VERTICAL)
        control_sizer = wx.BoxSizer(wx.VERTICAL)
        text_sizer = wx.BoxSizer(wx.VERTICAL)
        button_sizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)

        control_sizer.Add(audio_link_text, 0, wx.ALL ^ wx.LEFT | wx.ALIGN_LEFT, 3)
        control_sizer.Add(self.audio_links, 0, wx.ALL ^ wx.LEFT ^ wx.TOP | wx.ALIGN_LEFT | wx.EXPAND, 5)
        control_sizer.Add(out_dir_text, 0, wx.ALL ^ wx.LEFT | wx.ALIGN_LEFT, 3)
        control_sizer.Add(self.out_dir, 0, wx.ALL ^ wx.LEFT ^ wx.TOP | wx.ALIGN_LEFT | wx.EXPAND, 5)
        text_sizer.Add(warning_text, 0, wx.ALL | wx.ALIGN_CENTER, 5)
        button_sizer.Add(search_button)
        top_sizer.Add(control_sizer, 1, wx.ALL | wx.EXPAND | wx.ALIGN_TOP, 5)
        top_sizer.Add(text_sizer, 0, wx.ALL | wx.ALIGN_CENTER, 5)
        top_sizer.Add(button_sizer, 0, wx.ALL | wx.ALIGN_CENTER, 5)

        self.Bind(wx.EVT_BUTTON, handler=self.on_ok, id=wx.ID_OK)
        self.Bind(wx.EVT_BUTTON, handler=lambda x: SearchDialog(self), source=search_button)

        self.downloader = None
        self.progress_dialog = None
        self.num_songs = 0

        self.SetSizerAndFit(top_sizer)
        self.Center()
        self.ShowModal()

    def on_ok(self, event):
        songs = yt_extract(self.audio_links.GetValue().split(','))
        if not songs:
            error = wx.MessageDialog(parent=self,
                                     message="Invalid/Unsupported URL!",
                                     caption="Error!", style=wx.OK | wx.ICON_WARNING)
            error.ShowModal()
            error.Destroy()
            return

        self.num_songs = len(songs)

        self.progress_dialog = wx.ProgressDialog(title="Download", message="Downloading songs...",
                                                 maximum=self.num_songs * 100, parent=self, style=PD_STYLE)

        self.downloader = DownloaderThread(self, songs, self.out_dir.GetPath())
        self.downloader.start()

    def download_update(self, message):
        progress = "{songs} out of {total}".format(songs=message // 100, total=self.num_songs)
        if self.progress_dialog and self.downloader.isAlive():
            if not self.progress_dialog.Update(value=message, newmsg="Downloaded: {prog}".format(prog=progress))[0]:
                self.downloader.abort()
                self.downloader.join()

                alert_string = "Aborted! Only {progress} songs were downloaded".format(progress=progress)
                alert = wx.MessageDialog(parent=self, message=alert_string, caption="pyjam", style=wx.ICON_EXCLAMATION)
                alert.ShowModal()
                alert.Destroy()

                logger.info("Audio download canceled.")
                logger.info(alert_string)
                wx.CallAfter(self.progress_dialog.Destroy)

    def download_complete(self, errors):
        if self.progress_dialog:
            logger.info("Beginning download")
            self.downloader.join()
            if errors:
                done_string = "Songs downloaded with {errors} error(s)".format(errors=len(errors))
            else:
                done_string = "All songs were downloaded succesfully!"
            logger.info(done_string)
            done_message = wx.MessageDialog(parent=self, message=done_string, caption="pyjam")
            done_message.ShowModal()
            done_message.Destroy()

            if errors:
                errors = '\n'.join(errors)
                logger.critical("Error downloading these these URLs:\n{errors}".format(errors=errors))
                error_dialog = wx.MessageDialog(parent=self, message="The following URLs caused errors\n" + errors,
                                                caption="Download Error!", style=wx.ICON_ERROR)
                error_dialog.ShowModal()
                error_dialog.Destroy()

            self.progress_dialog.Destroy()
            self.Destroy()
            wx.CallAfter(self.parent.convert, event=None, in_dir=self.out_dir.GetPath())


class SearchDialog(wx.Dialog):
    def __init__(self, parent):
        super(SearchDialog, self).__init__(parent=parent, title="pyjam Audio Search")
        self.parent = parent

        self.result_list = ObjectListView(parent=self, style=wx.LC_REPORT | wx.BORDER_SUNKEN, sortable=True,
                                          useAlternateBackColors=False)
        self.result_list.SetEmptyListMsg("No results")
        self.result_list.SetColumns([
            ColumnDefn(title="Title", valueGetter="title", width=150),
            ColumnDefn(title="Description", valueGetter="desc", width=300)
        ])

        self.search_recent = collections.deque([], 10)
        search_help = wx.StaticText(parent=self, label=("Enter a search term and press Enter. "
                                                        "Then, select the videos you want from the list and press OK."))
        self.search_query = wx.SearchCtrl(parent=self, style=wx.TE_PROCESS_ENTER)
        self.search_query.ShowCancelButton(True)
        self.search_query.SetMenu(self.search_menu())

        top_sizer = wx.BoxSizer(wx.VERTICAL)
        olv_sizer = wx.BoxSizer(wx.VERTICAL)
        query_sizer = wx.BoxSizer(wx.VERTICAL)

        button_sizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)

        olv_sizer.Add(self.result_list, 1, wx.LEFT | wx.RIGHT | wx.EXPAND | wx.ALIGN_TOP, 5)
        query_sizer.Add(search_help, 0, wx.ALL ^ wx.TOP, 5)
        query_sizer.Add(self.search_query, 0, wx.ALL ^ wx.TOP | wx.EXPAND, 5)
        top_sizer.Add(olv_sizer, 1, wx.ALL | wx.EXPAND, 5)
        top_sizer.Add(query_sizer, 0, wx.ALL | wx.EXPAND, 5)
        top_sizer.Add(button_sizer, 0, wx.ALL | wx.ALIGN_CENTER, 5)

        # Context menu
        self.context_menu = wx.Menu()
        open_url = self.context_menu.Append(wx.ID_OPEN, "Open link in browser")
        copy_url = self.context_menu.Append(wx.ID_COPY, "Copy link address")

        self.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, handler=self.list_right_click, source=self.result_list)
        self.Bind(wx.EVT_MENU, handler=self.copy_url, source=copy_url)
        self.Bind(wx.EVT_MENU, handler=self.open_url, source=open_url)

        self.Bind(wx.EVT_TEXT_ENTER, handler=self.on_search, source=self.search_query)
        self.Bind(wx.EVT_BUTTON, handler=self.on_ok, id=wx.ID_OK)
        self.SetSizerAndFit(top_sizer)
        self.Center()
        self.ShowModal()

    def on_search(self, event):
        query = self.search_query.GetValue()
        if not query or query.isspace():
            alert = wx.MessageDialog(parent=self, message="Search term can't be empty!", caption="pyjam Audio Search")
            alert.ShowModal()
            alert.Destroy()
            return
        if query in self.search_recent:
            self.search_recent.remove(query)
        self.search_recent.appendleft(query)
        self.search_query.SetMenu(self.search_menu())

        results = yt_search
        if not results:
            alert = wx.MessageDialog(parent=self,
                                     message="There was an error processing your request.\nPlease try again later",
                                     caption="pyjam Audio Search", style=wx.OK | wx.ICON_WARNING)
            alert.ShowModal()
            alert.Destroy()
            return

        self.result_list.SetObjects(results)

    def on_ok(self, event):
        self.parent.audio_links.SetValue(','.join(item['url'] for item in self.result_list.GetSelectedObjects()))
        event.Skip()

    def list_right_click(self, event):
        self.selected_video = event.GetIndex()
        self.PopupMenu(self.context_menu)

    def copy_url(self, event):
        if not wx.TheClipboard.Open():
            alert = wx.MessageDialog(parent=self, message="There was an error opening the clipboard",
                                     caption="pyjam Audio Search", style=wx.OK | wx.ICON_WARNING)
            alert.ShowModal()
            alert.Destroy()
            return

        url = self.result_list.GetObjects()[self.selected_video]["url"]
        wx.TheClipboard.SetData(wx.TextDataObject(url))
        wx.TheClipboard.Close()

    def open_url(self, event):
        url = self.result_list.GetObjects()[self.selected_video]["url"]
        webbrowser.open_new_tab(url)

    def search_menu(self):
        menu = wx.Menu()
        menu.Append(wx.ID_ANY, "Recent searches").Enable(False)
        for item in self.search_recent:
            self.Bind(wx.EVT_MENU, handler=self.click_recent, source=menu.Append(wx.ID_ANY, item))
        return menu

    def click_recent(self, event):
        search = event.GetEventObject().GetLabel(event.GetId())
        self.search_query.SetValue(search)
        self.on_search(event=None)


def yt_search(query):
    # type (str) -> list
    r = requests.get('https://pyjam-api.appspot.com', params={'q': query, 'app': 'pyjam'})
    results = []

    if not r.ok:
        return results

    for item in r.json()['items']:
        results.append(
            {"title": item["snippet"]["title"],
             "desc": item["snippet"]["description"],
             "id": item["id"]["videoId"],
             "url": "https://www.youtube.com/watch?v={id}".format(id=item["id"]["videoId"])
             }
        )
    return results


def yt_extract(links):
    songs = []
    with youtube_dl.YoutubeDL() as yt_dl:
        for url in links:
            try:
                result = yt_dl.extract_info(url, download=False, process=False)
            except youtube_dl.DownloadError:
                return songs

            if 'entries' in result:
                songs.extend(vid['url'] for vid in list(result['entries']))
            else:
                songs.append(url)
        return songs
