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
import json
import logging
import logging.config
import os
import platform
import sys
import traceback

import wx  # Tested w/ wxPhoenix 3.0.3
import wx.adv
import wx.lib.intctrl as intctrl  # This was fixed recently. You need the latest version of wxPython-Pheonix!
from ObjectListView import ColumnDefn, ObjectListView

import jam
from jam.common import Game, get_steam_path, get_path

try:
    FileNotFoundError  # This will throw a NameError if the user is using Python 2.
except NameError:
    FileNotFoundError = IOError

NO_ALIASES = "This track has no aliases"  # im lazy, okay?


class MainFrame(wx.Frame):
    def __init__(self):
        super(MainFrame, self).__init__(parent=wx.GetApp().GetTopWindow(), title="pyjam")
        bitmap = wx.Bitmap(os.path.normpath('data/splash.png'), wx.BITMAP_TYPE_PNG)
        splash = wx.adv.SplashScreen(bitmap, wx.adv.SPLASH_CENTRE_ON_PARENT | wx.adv.SPLASH_NO_TIMEOUT, 0, parent=self)
        panel = MainPanel(self)
        self.SetSize((600, 400))

        file_menu = wx.Menu()
        settings = file_menu.Append(wx.ID_SETUP, "&Settings", "pyjam Setup")

        help_menu = wx.Menu()
        about = help_menu.Append(wx.ID_ABOUT, "&About", "About pyjam")
        licenses = help_menu.Append(wx.ID_ANY, "&Licenses", "Open source licenses")

        menu_bar = wx.MenuBar()
        menu_bar.Append(file_menu, "&File")
        menu_bar.Append(help_menu, "&Help")
        self.SetMenuBar(menu_bar)
        self.status_bar = self.CreateStatusBar()

        if sys.platform == "win32":
            icon = wx.Icon(sys.executable, wx.BITMAP_TYPE_ICO)
        else:
            icon = wx.Icon(os.path.normpath('data/icon.ico'), wx.BITMAP_TYPE_ICO)
        self.SetIcon(icon)

        self.Bind(wx.EVT_MENU, handler=panel.settings, source=settings)
        self.Bind(wx.EVT_MENU, handler=lambda x: jam.about.about_dialog(self), source=about)
        self.Bind(wx.EVT_MENU, handler=lambda x: jam.about.Licenses(self), source=licenses)
        self.Bind(wx.EVT_CLOSE, handler=panel.on_exit)

        jam.about.update_check(self)
        splash.Destroy()
        logger.info("Ready.")
        self.status_bar.SetStatusText('Status: Ready')
        self.Show()


class MainPanel(wx.Panel):
    def __init__(self, parent):
        super(MainPanel, self).__init__(parent)
        self.parent = parent
        self.games = config.get_games()
        self.game = None
        self.game_watcher = None
        while not self.games:
            error = wx.MessageDialog(parent=self,
                                     message="You have no games profiles set up. Replacing config with default.",
                                     caption="Info", style=wx.OK | wx.ICON_INFORMATION)
            error.ShowModal()
            error.Destroy()
            config.new()
            config.load()
            self.games = config.get_games()

        self.profile = wx.ComboBox(parent=self, choices=[game.name for game in self.games],
                                   style=wx.CB_READONLY)
        self.profile.SetSelection(0)

        self.track_list = ObjectListView(parent=self, style=wx.LC_REPORT | wx.BORDER_SUNKEN, sortable=True,
                                         useAlternateBackColors=False)
        self.track_list.SetEmptyListMsg("You currently do not have any sound files for this game.")
        self.track_list.SetColumns([
            ColumnDefn(title="#", fixedWidth=50, valueGetter="index", stringConverter="%i"),
            ColumnDefn(title="Title", width=250, valueGetter="name", minimumWidth=150, isSpaceFilling=True),
            ColumnDefn(title="Aliases", width=300, valueGetter="get_aliases", minimumWidth=200, isSpaceFilling=True),
            ColumnDefn(title="Bind", width=75, valueGetter="bind", minimumWidth=50, maximumWidth=120)
        ])
        self.track_list.rowFormatter = lambda x, y: x.SetTextColour(wx.RED) if y.get_aliases() == NO_ALIASES else None
        self.selected_track = None
        self.game_select(event=None)

        refresh_button = wx.Button(parent=self, label="Refresh tracks")
        self.start_stop_button = wx.Button(parent=self, label="Start")
        convert_button = wx.Button(parent=self, label="Audio converter")
        download_button = wx.Button(parent=self, label="Audio downloader")

        top_sizer = wx.BoxSizer(wx.VERTICAL)  # Root sizer
        profile_sizer = wx.BoxSizer(wx.VERTICAL)  # For the profile selection
        olv_sizer = wx.BoxSizer(wx.VERTICAL)  # For the ObjectListView
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)  # Start/Stop and Refresh buttons

        profile_sizer.Add(self.profile, 0, wx.LEFT | wx.RIGHT | wx.EXPAND | wx.ALIGN_TOP, 5)
        olv_sizer.Add(self.track_list, 1, wx.LEFT | wx.RIGHT | wx.EXPAND | wx.ALIGN_TOP, 5)
        button_sizer.Add(refresh_button, 0, wx.ALL | wx.ALIGN_LEFT, 5)
        button_sizer.Add(self.start_stop_button, 0, wx.ALL | wx.ALIGN_LEFT, 5)
        button_sizer.Add(convert_button, 0, wx.ALL | wx.ALIGN_LEFT, 5)
        button_sizer.Add(download_button, 0, wx.ALL | wx.ALIGN_LEFT, 5)

        top_sizer.Add(profile_sizer, 0, wx.ALL | wx.EXPAND, 5)
        top_sizer.Add(olv_sizer, 1, wx.ALL | wx.EXPAND, 5)
        top_sizer.Add(button_sizer, 0, wx.ALL | wx.EXPAND, 5)
        top_sizer.SetSizeHints(self.parent)
        self.SetSizerAndFit(top_sizer)

        # Context menu
        self.context_menu = wx.Menu()
        set_aliases = self.context_menu.Append(wx.ID_ANY, "Set custom aliases")
        clear_aliases = self.context_menu.Append(wx.ID_ANY, "Clear custom aliases")
        set_bind = self.context_menu.Append(wx.ID_ANY, "Set bind")
        clear_bind = self.context_menu.Append(wx.ID_ANY, "Clear bind")
        clear_all = self.context_menu.Append(wx.ID_CLEAR, "Clear EVERYTHING (all tracks)")

        self.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, handler=self.list_right_click, source=self.track_list)
        self.Bind(wx.EVT_MENU, handler=self.set_aliases, source=set_aliases)
        self.Bind(wx.EVT_MENU, handler=self.clear_aliases, source=clear_aliases)
        self.Bind(wx.EVT_MENU, handler=self.set_bind, source=set_bind)
        self.Bind(wx.EVT_MENU, handler=self.clear_bind, source=clear_bind)
        self.Bind(wx.EVT_MENU, handler=self.clear_all, source=clear_all)

        self.Bind(wx.EVT_COMBOBOX, handler=self.game_select, source=self.profile)
        self.Bind(wx.EVT_BUTTON, handler=self.refresh, source=refresh_button)
        self.Bind(wx.EVT_BUTTON, handler=self.start_stop, source=self.start_stop_button)
        self.Bind(wx.EVT_BUTTON, handler=self.convert, source=convert_button)
        self.Bind(wx.EVT_BUTTON, handler=self.download, source=download_button)

        self.Bind(wx.EVT_SIZE, handler=self.on_size)
        self.Bind(wx.EVT_CLOSE, handler=self.on_exit)

    def game_select(self, event):
        self.game = self.games[self.profile.GetSelection()]
        self.track_list.SetObjects(jam.jam.get_tracks(self.game.audio_dir))

    def start_stop(self, event):
        if not self.game_watcher:
            self.refresh(event=None)
            self.start_stop_button.SetLabel("Starting...")
            self.start_stop_button.Disable()
            self.game_watcher = jam.jam.Jam(config.steam_path, self.game, self.track_list)
            self.game_watcher.start()
            self.start_stop_button.Enable()
            self.start_stop_button.SetLabel("Stop")
            self.parent.status_bar.SetStatusText('Status: Running')
        else:
            self.start_stop_button.Disable()
            self.start_stop_button.SetLabel("Stopping...")
            self.parent.status_bar.SetStatusText('Status: Stopping...')
            self.game_watcher.stop()
            self.game_watcher = None
            self.start_stop_button.Enable()
            self.start_stop_button.SetLabel("Start")
            self.parent.status_bar.SetStatusText('Status: Stopped')

    def refresh(self, event):
        tracks = jam.jam.get_tracks(self.game.audio_dir)
        self.track_list.SetObjects(tracks)

    def convert(self, event, in_dir=None):
        if jam.ffmpeg.find() is None and sys.platform == "win32":
            message = ("Couldn't detect FFmpeg in your PATH.\n"
                       "FFmpeg is required for audio conversion. Would you like to download it?")
            do_download = wx.MessageDialog(self, message, "pyjam", wx.YES_NO | wx.ICON_QUESTION)

            if do_download.ShowModal() == wx.ID_YES:
                if platform.architecture()[0] == '64bit':
                    url = "https://ffmpeg.zeranoe.com/builds/win64/static/ffmpeg-latest-win64-static.7z"
                else:
                    url = "https://ffmpeg.zeranoe.com/builds/win32/static/ffmpeg-latest-win32-static.7z"
                jam.ffmpeg.FFmpegDownloader(self, url)

            else:
                download_info = ("Please download it and place FFmpeg.exe in your PATH\n"
                                 "or inside the /pyjam/bin/ folder. You can download it at:\n\n"
                                 "http://ffmpeg.zeranoe.com/")

                message = wx.MessageDialog(parent=self, message=download_info, caption="pyjam")
                message.ShowModal()
                message.Destroy()

            do_download.Destroy()

        elif jam.ffmpeg.find() is None:
            message = wx.MessageDialog(parent=self,
                                       message="You require FFmpeg or avconv to convert audio. Please install it.",
                                       caption="pyjam")
            message.ShowModal()
            message.Destroy()

        else:
            jam.ffmpeg.FFmpegConvertDialog(self, self.game.audio_rate, self.game.audio_dir, in_dir)
            self.game_select(event=None)

    def download(self, event):
        # youtube-dl takes a long time to load, and it hinders start up time :/
        jam.downloader.DownloaderDialog(self)

    def list_right_click(self, event):
        self.selected_track = event.GetIndex()
        self.PopupMenu(self.context_menu)

    def set_aliases(self, event):
        track_obj = self.track_list.GetObjects()[self.selected_track]
        default_aliases = ' '.join(track_obj.aliases)
        dialog = wx.TextEntryDialog(parent=self, message="Enter aliases separated by spaces.",
                                    caption="pyjam", value=default_aliases)
        dialog.Center()
        if dialog.ShowModal() != wx.ID_OK:
            dialog.Destroy()
            return

        new_aliases = dialog.GetValue()
        dialog.Destroy()
        filtered_aliases = jam.jam.filter_alias(new_aliases).split()
        self.write_track_data("aliases", filtered_aliases)

    def clear_aliases(self, event):
        self.write_track_data("aliases", None)

    def set_bind(self, event):
        dialog = wx.Dialog(parent=self, title="pyjam")

        bind_text = wx.StaticText(parent=dialog, label="Key:")
        bind_choice = wx.ComboBox(parent=dialog, choices=jam.common.SOURCE_KEYS, style=wx.CB_READONLY)
        bind = bind_choice.GetStringSelection

        top_sizer = wx.BoxSizer(wx.VERTICAL)
        key_sizer = wx.BoxSizer(wx.HORIZONTAL)
        button_sizer = dialog.CreateButtonSizer(wx.OK | wx.CANCEL)

        key_sizer.Add(bind_text, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        key_sizer.Add(bind_choice, 0, wx.ALL | wx.ALIGN_LEFT, 5)
        top_sizer.Add(key_sizer)
        top_sizer.Add(button_sizer, 0, wx.ALL | wx.ALIGN_CENTER, 5)

        bind_choice.Bind(wx.EVT_KEY_DOWN, handler=jam.common.key_choice_override)
        dialog.Bind(wx.EVT_BUTTON, handler=lambda x: (self.write_track_data('bind', bind()), x.Skip()), id=wx.ID_OK)

        dialog.SetSizerAndFit(top_sizer)
        dialog.Center()
        dialog.ShowModal()

    def clear_bind(self, event):
        self.write_track_data("bind", None)

    def clear_all(self, event):
        open(os.path.join(self.game.audio_dir, 'track_data.json'), 'w').close()
        self.track_list.SetObjects(jam.jam.get_tracks(self.game.audio_dir))

    def write_track_data(self, key, data):
        # type (str, object) -> None
        track_obj = self.track_list.GetObjects()[self.selected_track]

        data_path = os.path.join(self.game.audio_dir, 'track_data.json')
        logger.info("Writing track data to {path}".format(path=data_path))
        try:
            with open(data_path) as f:
                track_data = json.load(f)
        except FileNotFoundError:
            track_data = {}
        except ValueError:
            track_data = {}
            logger.exception("Invalid trackdata for {path}".format(path=data_path))

        # Remove duplicate track data.
        # This only really works for binds, because they're strings. Unless somehow your aliases are the exact same.
        for track, values in track_data.items():
            try:
                if key in values and data in values[key]:
                    del values[key]
            except TypeError:
                pass

        if track_obj.name not in track_data:
            track_data[track_obj.name] = {}

        track_data[track_obj.name][key] = data

        with open(os.path.join(self.game.audio_dir, 'track_data.json'), 'w') as f:
            json.dump(track_data, f, sort_keys=True)

        self.track_list.SetObjects(jam.jam.get_tracks(self.game.audio_dir))

    def settings(self, event):
        SetupDialog(self)
        self.games = config.get_games()
        self.profile.Set([game.name for game in self.games])
        self.profile.SetSelection(0)
        self.game_select(event=None)

    def on_size(self, event):
        if self.GetAutoLayout():
            self.Layout()

    def on_exit(self, event):
        if self.game_watcher:
            self.game_watcher.stop()
        event.Skip()


class SetupDialog(wx.Dialog):
    def __init__(self, parent):
        super(SetupDialog, self).__init__(parent, title="pyjam Setup", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

        self.steam_path = wx.DirPickerCtrl(self, name="Path to Steam")
        self.steam_path.SetInitialDirectory(jam.common.get_steam_path())
        steam_path_text = wx.StaticText(self, label="Path to Steam (e.g. C:\\Program Files (x86)\\Steam)")

        self.games = config.get_games()
        self.profile = wx.ComboBox(self, choices=[game.name for game in self.games], style=wx.CB_READONLY)
        self.profile.SetSelection(0)
        self.game = self.games[self.profile.GetSelection()]

        separator = wx.StaticLine(self, style=wx.LI_HORIZONTAL, size=(self.GetSize()[0], 1))

        self.prof_name = wx.TextCtrl(self)
        prof_name_text = wx.StaticText(self, label="Profile/game name")

        self.game_path = wx.DirPickerCtrl(self, name="Path to game")
        self.game_path.SetInitialDirectory(jam.common.get_steam_path())
        game_path_text = wx.StaticText(self, label="Game folder (include mod folder, e.g. games\\Team Fortress 2\\tf2)")

        self.audio_path = wx.DirPickerCtrl(self, name="Path to audio")
        self.audio_path.SetInitialDirectory(os.getcwd())
        audio_path_text = wx.StaticText(self, label="Audio folder for this game")

        self.game_rate = intctrl.IntCtrl(self)
        game_rate_text = wx.StaticText(self, label="Audio rate (usually 11025 or 22050)")

        self.relay_choice = wx.ComboBox(self, choices=jam.common.SOURCE_KEYS, style=wx.CB_READONLY)
        relay_text = wx.StaticText(self, label="Relay key (default is fine for most cases, ignore)")
        self.relay_choice.SetToolTip("Nice")

        self.play_choice = wx.ComboBox(self, choices=jam.common.SOURCE_KEYS, style=wx.CB_READONLY)
        play_text = wx.StaticText(self, label="Play audio key")

        self.aliases_box = wx.CheckBox(self, label="Enable aliases")

        save_button = wx.Button(self, wx.ID_SAVE, label="Save Game")
        new_button = wx.Button(self, wx.ID_NEW, label="New Game")
        remove_button = wx.Button(self, wx.ID_REMOVE, label="Remove Game")

        # Sizer stuff
        top_sizer = wx.BoxSizer(wx.VERTICAL)
        profile_sizer = wx.BoxSizer(wx.VERTICAL)
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)

        top_sizer.Add(profile_sizer, 1, wx.ALL | wx.EXPAND | wx.ALIGN_TOP, 5)
        top_sizer.Add(button_sizer, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
        profile_sizer.Add(steam_path_text, 0, wx.ALL ^ wx.LEFT | wx.ALIGN_LEFT, 3)
        profile_sizer.Add(self.steam_path, 0, wx.ALL ^ wx.LEFT ^ wx.TOP | wx.ALIGN_LEFT | wx.EXPAND, 5)
        profile_sizer.Add(self.profile, 0, wx.ALL ^ wx.LEFT | wx.ALIGN_LEFT, 5)
        profile_sizer.Add(separator, 0, wx.TOP | wx.BOTTOM | wx.ALIGN_LEFT, 3)
        profile_sizer.Add(prof_name_text, 0, wx.ALL ^ wx.BOTTOM ^ wx.LEFT | wx.ALIGN_LEFT, 3)
        profile_sizer.Add(self.prof_name, 0, wx.ALL ^ wx.LEFT | wx.ALIGN_LEFT | wx.EXPAND, 5)
        profile_sizer.Add(game_path_text, 0, wx.ALL ^ wx.LEFT | wx.ALIGN_LEFT, 3)
        profile_sizer.Add(self.game_path, 0, wx.ALL ^ wx.LEFT ^ wx.TOP | wx.ALIGN_LEFT | wx.EXPAND, 5)
        profile_sizer.Add(audio_path_text, 0, wx.ALL ^ wx.LEFT | wx.ALIGN_LEFT, 3)
        profile_sizer.Add(self.audio_path, 0, wx.ALL ^ wx.LEFT ^ wx.TOP | wx.ALIGN_LEFT | wx.EXPAND, 5)
        profile_sizer.Add(game_rate_text, 0, wx.ALL ^ wx.BOTTOM ^ wx.LEFT | wx.ALIGN_LEFT, 3)
        profile_sizer.Add(self.game_rate, 0, wx.ALL ^ wx.LEFT | wx.ALIGN_LEFT, 5)
        profile_sizer.Add(relay_text, 0, wx.ALL ^ wx.BOTTOM ^ wx.LEFT | wx.ALIGN_LEFT, 3)
        profile_sizer.Add(self.relay_choice, 0, wx.ALL ^ wx.LEFT | wx.ALIGN_LEFT, 5)
        profile_sizer.Add(play_text, 0, wx.ALL ^ wx.BOTTOM ^ wx.LEFT | wx.ALIGN_LEFT, 3)
        profile_sizer.Add(self.play_choice, 0, wx.ALL ^ wx.LEFT | wx.ALIGN_LEFT, 5)
        profile_sizer.Add(self.aliases_box, 0, wx.ALL ^ wx.LEFT | wx.ALIGN_LEFT, 7)
        button_sizer.Add(save_button, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        button_sizer.Add(new_button, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        button_sizer.Add(remove_button, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        # self.Bind doesn't seem to work for wx.EVT_KEY_DOWN or wx.EVT_CHAR. Very likely intentional.
        # http://wiki.wxpython.org/self.Bind%20vs.%20self.button.Bind.
        self.relay_choice.Bind(wx.EVT_KEY_DOWN, handler=jam.common.key_choice_override, source=self.relay_choice)
        self.play_choice.Bind(wx.EVT_KEY_DOWN, handler=jam.common.key_choice_override, source=self.play_choice)
        self.Bind(wx.EVT_COMBOBOX, handler=self.update_profile, source=self.profile)
        self.Bind(wx.EVT_BUTTON, handler=self.save, id=wx.ID_SAVE)
        self.Bind(wx.EVT_BUTTON, handler=self.new, id=wx.ID_NEW)
        self.Bind(wx.EVT_BUTTON, handler=self.remove, id=wx.ID_REMOVE)

        self.SetSizerAndFit(top_sizer)
        self.update_profile(event=None)
        self.Center()
        self.ShowModal()

    def update_profile(self, event):
        self.games = config.get_games()
        self.game = self.games[self.profile.GetSelection()]
        try:
            self.steam_path.SetPath(config.steam_path)
            self.prof_name.SetValue(self.game.name)
            self.game_path.SetPath(self.game.mod_path)
            self.audio_path.SetPath(self.game.audio_dir)
            self.audio_path.SetInitialDirectory(os.path.abspath(self.game.audio_dir))
            self.game_rate.SetValue(self.game.audio_rate)
            self.relay_choice.SetStringSelection(self.game.relay_key)
            self.play_choice.SetStringSelection(self.game.play_key)
            self.aliases_box.SetValue(self.game.use_aliases)
        except (IndexError, NameError, TypeError):
            self.prof_name.Clear()
            self.game_path.SetPath("")
            self.audio_path.SetPath("")
            self.game_rate.Clear()
            self.relay_choice.Clear()
            self.play_choice.Clear()

    def new(self, event):
        # type: (int) -> None
        new_profile = wx.TextEntryDialog(parent=self, message="Enter the name of your new game.", caption="pyjam")
        if new_profile.ShowModal() != wx.ID_OK:
            new_profile.Destroy()
            return

        name = new_profile.GetValue()
        new_profile.Destroy()

        self.profile.Append(name)
        self.games.append(jam.jam.Game(name=name))
        config.set_games(self.games)
        config.save()

        self.profile.SetSelection(self.profile.GetCount() - 1)
        self.update_profile(event=None)
        logger.info("New game created: {name}".format(name=name))

    def save(self, event):
        # type: (int) -> None
        config.steam_path = self.steam_path.GetPath()
        self.profile.SetString(self.profile.GetSelection(), self.prof_name.GetValue())
        self.game.name = self.prof_name.GetValue()
        self.game.mod_path = self.game_path.GetPath()
        self.game.audio_dir = self.audio_path.GetPath()
        self.game.audio_rate = self.game_rate.GetValue()
        self.game.relay_key = self.relay_choice.GetStringSelection()
        self.game.play_key = self.play_choice.GetStringSelection()
        self.game.use_aliases = self.aliases_box.IsChecked()
        config.set_games(self.games)
        config.save()
        self.update_profile(event=None)
        if not os.path.exists(self.audio_path.GetPath()):
            os.makedirs(self.audio_path.GetPath())

    def remove(self, event):
        if len(self.games) <= 1:
            message = wx.MessageDialog(parent=self, message="You can't remove your only game!",
                                       style=wx.OK | wx.ICON_EXCLAMATION)
            message.ShowModal()
            message.Destroy()
            return False

        name = self.game.name
        self.games.pop(self.profile.GetSelection())
        config.set_games(self.games)
        config.save()
        self.games = config.get_games()

        self.profile.Set([game.name for game in self.games])
        self.profile.SetSelection(0)
        self.update_profile(event=None)

        logger.info("Game removed: {name}".format(name=name))


class Config(object):
    """
    A class representing a pyjam config file.
    """
    def __init__(self, config_file):
        """
        Args:
            config_file (str): Path to the config file.
        """
        self.config_file = config_file
        self.steam_path = os.curdir
        self.games = []
        self.logger = {}
        self.load()

    def new(self):
        """Create a new config file.

        Returns:
            None

        """
        steam = get_steam_path()
        csgo_path = get_path(steam, 'steamapps/common/Counter-Strike Global Offensive/csgo')
        css_path = get_path(steam, 'steamapps/common/Counter-Strike Source/css')
        default = {'games':
                   [{'audio_dir': 'audio/csgo', 'use_aliases': True, 'audio_rate': 22050,
                     'name': 'Counter-Strike: Global Offensive',
                     'mod_path': csgo_path if steam != os.curdir else os.curdir,
                     'play_key': 'F8', 'relay_key': '='},
                    {'audio_dir': 'audio/css', 'use_aliases': True, 'audio_rate': 11025,
                     'name': 'Counter-Strike: Source',
                     'mod_path': css_path if steam != os.curdir else os.curdir,
                     'play_key': 'F8', 'relay_key': '='}],
                   'steam_path': steam}

        with open(self.config_file, 'w') as f:
            json.dump(default, f, indent=4, sort_keys=True)

    def load(self):
        """Load/reload the config file.

        Returns:
            None
        """
        # type: () -> str, list
        try:
            with open(self.config_file) as f:
                try:
                    config_json = json.load(f)
                except ValueError:
                    logger.exception("Corrupt config.")
                    error = wx.MessageDialog(parent=wx.GetApp().GetTopWindow(),
                                             message="Malformed config file! Overwriting with default.",
                                             caption="Error!", style=wx.OK | wx.ICON_WARNING)
                    error.ShowModal()
                    error.Destroy()
                    self.new()
                    return self.load()
                else:
                    self.steam_path = config_json.get('steam_path', os.curdir)
                    self.games = config_json.get('games', [])
                    self.logger = config_json.get('logger')
        except FileNotFoundError:
            self.new()
            return self.load()

    def save(self):
        """Save the config file.
        Returns:
            None
        """
        with open(self.config_file, 'w') as f:
            # config_dict = json.loads(jsonpickle.encode(self, unpicklable=False))
            config_dict = dict(self.__dict__)  # Oh god, I've been removing the actual variable from the class...
            config_dict.pop('config_file')  # Exclude the redundant config_file variable.
            json.dump(config_dict, f, indent=4, sort_keys=True)
            logger.info("Config saved to location {loc}".format(loc=self.config_file))

    def get_games(self):
        """Get the config's games.
        Returns:
            list[Game]: A list of Source Engine Game objects representing the config's games.
        """
        return [Game(get_path(game.get('audio_dir', os.curdir)), game.get('audio_rate', 11025),
                     get_path(game.get('mod_path', os.curdir)), game.get('name'), game.get('play_key', 'F8'),
                     game.get('relay_key', '='), game.get('use_aliases', True)) for game in self.games]

    def set_games(self, new_games):
        """Set the config's games.
        Args:
            new_games (list[Game]): A list of Source Engine Game objects to set.

        Returns:
            None
        """
        # self.games = json.loads(jsonpickle.encode(new_games, unpicklable=False))
        self.games = [dict(game.__dict__) for game in new_games]

    def __repr__(self):
        return "{c}(file={file})".format(c=self.__class__, file=self.config_file)

class ErrorFilter(logging.Filter):
    def filter(self, record):
        return record.levelno < logging.ERROR


def start_logger():
    if config.logger:
        logging.config.dictConfig(config.logger)
    else:
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)

        formatter = logging.Formatter(fmt='%(asctime)s::%(name)s::%(levelname)s::%(message)s', datefmt='%H:%M:%S')

        if not hasattr(sys, 'frozen'):
            stdout_log = logging.StreamHandler(sys.stdout)
            stdout_log.setLevel(logging.DEBUG)
            stdout_log.setFormatter(formatter)
            stdout_log.addFilter(ErrorFilter())
            root_logger.addHandler(stdout_log)

            stderr_log = logging.StreamHandler(sys.stderr)
            stderr_log.setLevel(logging.ERROR)
            stderr_log.setFormatter(formatter)
            root_logger.addHandler(stderr_log)

        try:
            file_log = logging.FileHandler(filename='pyjam.log')
            file_log.setLevel(logging.INFO)
            file_log.setFormatter(formatter)
            root_logger.addHandler(file_log)
        except (OSError, IOError):
            error_dialog = wx.MessageDialog(parent=wx.GetApp().GetTopWindow(),
                                            message="Could not create log file, errors will not be recorded!",
                                            caption="Error!", style=wx.OK | wx.ICON_ERROR)
            error_dialog.ShowModal()
            error_dialog.Destroy()
            root_logger.exception("Could not create log file.")

    _logger = logging.getLogger('pyjam')
    _logger.info("Python {version} on {platform}".format(version=sys.version, platform=sys.platform))
    _logger.info(platform.uname())
    _logger.info("pyjam version {v}".format(v=jam.about.__version__))

    return _logger

def exception_hook(error, value, trace):
    error_message = ''.join(traceback.format_exception(error, value, trace))
    logger.critical(error_message)
    error_dialog = wx.MessageDialog(parent=None,
                                    message="An error has occured!\n\n" + error_message,
                                    caption="Error!", style=wx.OK | wx.CANCEL | wx.ICON_ERROR)
    error_dialog.SetOKCancelLabels("Ignore", "Quit")
    error_dialog.RequestUserAttention()
    if error_dialog.ShowModal() == wx.ID_OK:
        error_dialog.Destroy()
    else:
        error_dialog.Destroy()
        sys.exit(1)


if __name__ == '__main__':
    wx_app = wx.App()
    config = Config('jamconfig.json')
    logger = start_logger()
    sys.excepthook = exception_hook
    frame = MainFrame()
    wx_app.MainLoop()
