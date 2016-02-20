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
import sys
import os
import logging
import json
import traceback

import wx  # Tested w/ wxPhoenix 3.0.2
from ObjectListView import ColumnDefn, ObjectListView

import ffmpeg
import jam_tools
import jam_about

try:
    if sys.version_info[0:2] >= (3, 0):
        import winreg
    else:
        import _winreg as winreg
    windows = True
except ImportError:
    windows = False

if sys.version_info[0:2] < (3, 0):
    FileNotFoundError = OSError

NO_ALIASES = "This track has no aliases"  # im lazy, okay?


class MainFrame(wx.Frame):
    def __init__(self):
        super(MainFrame, self).__init__(parent=None, title="pyjam", size=(600, 400))
        self.SetMinSize(self.GetSize())
        panel = MainPanel(self)

        file_menu = wx.Menu()
        settings = file_menu.Append(wx.ID_SETUP, "&Settings", "pyjam Setup")
        help_menu = wx.Menu()
        about = help_menu.Append(wx.ID_ABOUT, "&About", "About pyjam")
        licenses = help_menu.Append(wx.ID_ANY, "&Licenses", "Open source licenses")

        menu_bar = wx.MenuBar()
        menu_bar.Append(file_menu, "&File")
        menu_bar.Append(help_menu, "&Help")

        self.SetMenuBar(menu_bar)

        icon = wx.Icon('pyjam.ico', wx.BITMAP_TYPE_ICO)
        self.SetIcon(icon)

        self.Bind(wx.EVT_MENU, panel.settings, settings)
        self.Bind(wx.EVT_MENU, lambda x: jam_about.about_info(self), about)
        self.Bind(wx.EVT_MENU, lambda x: jam_about.Licenses(self), licenses)
        self.Show()


class MainPanel(wx.Panel):
    def __init__(self, parent):
        super(MainPanel, self).__init__(parent)
        self.parent_frame = parent
        self.games = config.get_games()
        self.game = None
        while not self.games:
            wx.MessageDialog(parent=None,
                             message="You have no games profiles set up. Replacing config with default.",
                             caption="Info", style=wx.OK | wx.ICON_INFORMATION).ShowModal()
            config.new()
            config.load()
            self.games = config.get_games()
            print(self.games)

        self.profile = wx.ComboBox(self, choices=[game.name for game in self.games],
                                   style=wx.CB_READONLY)
        self.profile.SetSelection(0)

        self.track_list = ObjectListView(self, style=wx.LC_REPORT | wx.BORDER_SUNKEN, sortable=False,
                                         useAlternateBackColors=False)
        self.track_list.SetEmptyListMsg("You currently do not have any sound files for this game.")
        self.track_list.SetColumns([
            ColumnDefn(title="Title", align="left", width=250, valueGetter="name", minimumWidth=150),
            ColumnDefn(title="Aliases", align="left", width=300, valueGetter="get_aliases", minimumWidth=200),
            ColumnDefn(title="Bind", align="left", width=75, valueGetter="get_bind", minimumWidth=50, maximumWidth=120)
        ])
        self.track_list.rowFormatter = lambda x, y: x.SetTextColour(wx.RED) if y.get_aliases() == NO_ALIASES else None
        self.selected_track = None
        self.game_select(None)

        refresh_button = wx.Button(self, label="Refresh tracks")
        start_button = wx.Button(self, label="Start")
        convert_button = wx.Button(self, label="Audio converter")

        top_sizer = wx.BoxSizer(wx.VERTICAL)  # Root sizer
        profile_sizer = wx.BoxSizer(wx.VERTICAL)  # For the profile selection
        olv_sizer = wx.BoxSizer(wx.VERTICAL)  # For the ObjectListView
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)  # Start/Stop and Refresh buttons

        profile_sizer.Add(self.profile, 0, wx.LEFT | wx.RIGHT | wx.EXPAND | wx.ALIGN_TOP, 5)
        olv_sizer.Add(self.track_list, 1, wx.LEFT | wx.RIGHT | wx.EXPAND | wx.ALIGN_TOP, 5)
        button_sizer.Add(refresh_button, 0, wx.ALL | wx.ALIGN_LEFT, 5)
        button_sizer.Add(start_button, 0, wx.ALL | wx.ALIGN_LEFT, 5)
        button_sizer.Add(convert_button, 0, wx.ALL | wx.ALIGN_LEFT, 5)

        top_sizer.Add(profile_sizer, 0, wx.ALL | wx.EXPAND, 5)
        top_sizer.Add(olv_sizer, 1, wx.ALL | wx.EXPAND, 5)
        top_sizer.Add(button_sizer, 0, wx.ALL | wx.EXPAND, 5)
        self.SetSizerAndFit(top_sizer)

        # Context menu
        self.context_menu = wx.Menu()
        set_aliases = self.context_menu.Append(wx.ID_ANY, "Set custom aliases")
        clear_aliases = self.context_menu.Append(wx.ID_ANY, "Clear custom aliases")
        set_bind = self.context_menu.Append(wx.ID_ANY, "Set bind")
        clear_bind = self.context_menu.Append(wx.ID_ANY, "Clear bind")
        clear_all = self.context_menu.Append(wx.ID_CLEAR, "Clear EVERYTHING (all tracks)")

        self.Bind(wx.EVT_COMBOBOX, self.game_select, self.profile)
        self.Bind(wx.EVT_BUTTON, self.refresh, refresh_button)
        self.Bind(wx.EVT_BUTTON, self.start, start_button)
        self.Bind(wx.EVT_BUTTON, self.convert, convert_button)

        self.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.list_right_click, self.track_list)
        self.Bind(wx.EVT_MENU, self.set_aliases, set_aliases)
        self.Bind(wx.EVT_MENU, self.clear_aliases, clear_aliases)
        self.Bind(wx.EVT_MENU, self.set_bind, set_bind)
        self.Bind(wx.EVT_MENU, self.clear_bind, clear_bind)
        self.Bind(wx.EVT_MENU, self.clear_all, clear_all)

    def game_select(self, event):
        # type: (int) -> None
        self.game = self.games[self.profile.GetSelection()]
        self.track_list.SetObjects(jam_tools.get_tracks(self.game.audio_dir))

    def start(self, event):
        # type: (int) -> None
        # logger.info(len(self.track_list.GetObjects()))
        # for track in self.track_list.GetObjects():
        #     logger.info("{}, {}, {}".format(track.name, track.aliases, track.path))
        tracks = self.track_list.GetObjects()
        config_path = self.game.config_path
        play_key = self.game.play_key
        relay_key = self.game.relay_key
        use_aliases = self.game.use_aliases
        jam_tools.write_src_config(config_path, tracks, play_key, relay_key, use_aliases)

    def refresh(self, event):
        tracks = jam_tools.get_tracks(self.game.audio_dir)
        self.track_list.SetObjects(tracks)

    def convert(self, event):
        # type: (int) -> None
        if ffmpeg.find() is None and sys.platform == "win32":
            message = ("Couldn't detect FFmpeg in your PATH.\n"
                       "FFmpeg is required for audio conversion. Would you like to download it?")
            do_download = wx.MessageDialog(self, message, "pyjam", wx.YES_NO | wx.ICON_QUESTION).ShowModal()
            if do_download == wx.ID_YES:
                url = "http://ffmpeg.zeranoe.com/builds/win32/static/ffmpeg-latest-win32-static.7z"
                ffmpeg.FFmpegDownloader(self, url)
            elif do_download == wx.ID_NO:
                download_info = ("Please download it and place FFmpeg.exe in your PATH\n"
                                 "or inside the folder pyjam is in. You can download it at:\n\n"
                                 "http://ffmpeg.zeranoe.com/")

                wx.MessageDialog(self, download_info, "pyjam").ShowModal()
        elif ffmpeg.find() is None:
            wx.MessageDialog(self, "You require FFmpeg to convert audio. Please install it.", "pyjam").ShowModal()
        else:
            # TODO: Implement audio conversion with FFmpeg.
            ffmpeg.FFmpegConvertDialog(self)

    def list_right_click(self, event):
        self.selected_track = event.GetIndex()
        self.PopupMenu(self.context_menu)

    def set_aliases(self, event):
        track_obj = self.track_list.GetObjects()[self.selected_track]
        default_aliases = ' '.join(track_obj.aliases)
        dialog = wx.TextEntryDialog(self, "Enter aliases separated by spaces.", "pyjam", default_aliases)
        dialog.Center()
        if dialog.ShowModal() != wx.ID_OK:
            dialog.Destroy()
            return

        new_aliases = dialog.GetValue()
        dialog.Destroy()
        filtered_aliases = jam_tools.filter_aliases(new_aliases).split()
        self.write_track_data("aliases", filtered_aliases)

    def clear_aliases(self, event):
        self.write_track_data("aliases", '')

    def set_bind(self, event):
        dialog = wx.Dialog(self, title="pyjam")

        bind_text = wx.StaticText(dialog, label="Key:")
        bind_choice = wx.ComboBox(dialog, choices=jam_tools.allowed_keys, style=wx.CB_READONLY)
        ok_button = wx.Button(dialog, id=wx.ID_OK, label="OK")
        cancel_button = wx.Button(dialog, id=wx.ID_CANCEL, label="Cancel")

        top_sizer = wx.BoxSizer(wx.VERTICAL)
        key_sizer = wx.BoxSizer(wx.HORIZONTAL)
        button_sizer = wx.StdDialogButtonSizer()

        key_sizer.Add(bind_text, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        key_sizer.Add(bind_choice, 0, wx.ALL | wx.ALIGN_LEFT, 5)
        button_sizer.AddButton(ok_button) # , 0, wx.ALL | wx.ALIGN_CENTER, 5
        button_sizer.AddButton(cancel_button)
        button_sizer.Realize()
        top_sizer.Add(key_sizer)
        top_sizer.Add(button_sizer, 0, wx.ALL | wx.ALIGN_CENTER, 5)


        dialog.SetSizerAndFit(top_sizer)
        bind_choice.Bind(wx.EVT_KEY_DOWN, self.key_choice_override)
        ok_button.Bind(wx.EVT_BUTTON, lambda x: (self.write_track_data('bind', bind_choice.GetStringSelection()), x.Skip()))
        dialog.Center()
        dialog.Show()

    def clear_bind(self, event):
        self.write_track_data("bind", '')

    def clear_all(self, event):
        open(os.path.join(self.game.audio_dir, 'track_data.json'), 'w').close()
        self.track_list.SetObjects(jam_tools.get_tracks(self.game.audio_dir))

    def write_track_data(self, key, data):
        track_obj = self.track_list.GetObjects()[self.selected_track]

        try:
            with open(os.path.join(self.game.audio_dir, 'track_data.json')) as f:
                track_data = json.load(f)
        except (FileNotFoundError, IOError, ValueError):
            open(os.path.join(self.game.audio_dir, 'track_data.json'), 'w').close()
            track_data = {}

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

        self.track_list.SetObjects(jam_tools.get_tracks(self.game.audio_dir))

    def key_choice_override(self, event):
        converted = jam_tools.bindable(event.GetKeyCode())
        # If converted gave us a bool, it's already a compatible key
        if converted is True:
            event.GetEventObject().SetStringSelection(chr(event.GetKeyCode()))
            return True
        # If converted gave us a string, it was converted
        elif converted:
            event.GetEventObject().SetStringSelection(converted)
            return True
        # Otherwise, it's not compatible and can't be converted.
        else:
            return False

    def settings(self, event):
        # type: (int) -> None
        SetupDialog(self)
        self.games = config.get_games()
        self.profile.Set([game.name for game in self.games])
        self.profile.SetSelection(0)
        self.game_select(None)

class SetupDialog(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, title="pyjam Setup", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

        self.games = config.get_games()
        self.profile = wx.ComboBox(self, choices=[game.name for game in self.games], style=wx.CB_READONLY)
        self.profile.SetSelection(0)
        self.game = self.games[self.profile.GetSelection()]

        separator = wx.StaticLine(self, style=wx.LI_HORIZONTAL, size=(self.GetSize()[0], 1))

        self.prof_name = wx.TextCtrl(self)
        prof_name_text = wx.StaticText(self, label="Profile/game name")

        self.game_path = wx.DirPickerCtrl(self, name="Path to game")
        self.game_path.SetInitialDirectory(get_steam_path())
        game_path_text = wx.StaticText(self, label="Game folder (include mod folder, e.g. games\\Team Fortress 2\\tf2)")

        self.audio_path = wx.DirPickerCtrl(self, name="Path to audio")
        self.audio_path.SetInitialDirectory(os.getcwd())
        audio_path_text = wx.StaticText(self, label="Audio folder for this game")

        self.game_rate = wx.TextCtrl(self)
        game_rate_text = wx.StaticText(self, label="Audio rate (usually 11025 or 22050)")

        self.relay_choice = wx.ComboBox(self, choices=jam_tools.allowed_keys, style=wx.CB_READONLY)
        relay_text = wx.StaticText(self, label="Relay key (default is fine for most cases, ignore)")

        self.play_choice = wx.ComboBox(self, choices=jam_tools.allowed_keys, style=wx.CB_READONLY)
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

        # self.Bind doesn't seem to work for wx.EVT_KEY_DOWN or wx.EVT_CHAR. Reproduced by commenters at:
        # http://wiki.wxpython.org/self.Bind%20vs.%20self.button.Bind. Probably intentional.
        self.relay_choice.Bind(wx.EVT_KEY_DOWN, self.key_choice_override, self.relay_choice)
        self.play_choice.Bind(wx.EVT_KEY_DOWN, self.key_choice_override, self.play_choice)
        self.game_rate.Bind(wx.EVT_CHAR, self.audio_rate_int, self.game_rate)
        self.Bind(wx.EVT_COMBOBOX, self.update_profile, self.profile)
        self.Bind(wx.EVT_BUTTON, self.save, id=wx.ID_SAVE)
        self.Bind(wx.EVT_BUTTON, self.new, id=wx.ID_NEW)
        self.Bind(wx.EVT_BUTTON, self.remove, id=wx.ID_REMOVE)
        self.SetSizerAndFit(top_sizer)
        self.update_profile(None)
        self.Center()
        self.ShowModal()

    def key_choice_override(self, event):
        converted = jam_tools.bindable(event.GetKeyCode())
        # If converted gave us a bool, it's already a compatible key
        if converted is True:
            event.GetEventObject().SetStringSelection(chr(event.GetKeyCode()))
            return True
        # If converted gave us a string, it was converted
        elif converted:
            event.GetEventObject().SetStringSelection(converted)
            return True
        # Otherwise, it's not compatible and can't be converted.
        else:
            return False

    def audio_rate_int(self, event):
        if event.GetKeyCode() < 256:
            if chr(event.GetKeyCode()).isalpha() or chr(event.GetKeyCode()).isspace():
                return
        event.Skip()

    def update_profile(self, event):
        # type: (int) -> None
        self.games = config.get_games()
        self.game = self.games[self.profile.GetSelection()]
        try:
            self.prof_name.SetValue(self.game.name)
            self.game_path.SetPath(self.game.config_path)
            self.audio_path.SetPath(self.game.audio_dir)
            self.audio_path.SetInitialDirectory(os.path.abspath(self.game.audio_dir))
            self.game_rate.SetValue(self.game.audio_rate)
            self.relay_choice.SetStringSelection(self.game.relay_key)
            self.play_choice.SetStringSelection(self.game.play_key)
            self.aliases_box.SetValue(self.game.use_aliases)
        except (IndexError, NameError, TypeError):
            self.prof_name.Clear()
            self.game_path.Clear()
            self.audio_path.Clear()
            self.game_rate.Clear()
            self.relay_choice.Clear()
            self.play_choice.Clear()

    def new(self, event):
        # type: (int) -> None
        new_profile = wx.TextEntryDialog(self, "Enter the name of your new game.")
        if new_profile.ShowModal() != wx.ID_OK:
            new_profile.Destroy()
            return
        new_profile.Destroy()

        name = new_profile.GetValue()
        self.profile.Append(name)
        self.games.append(jam_tools.Game(name=name, audio_dir='audio'))
        config.set_games(self.games)
        config.save()
        self.profile.SetSelection(self.profile.GetCount() - 1)
        self.update_profile(None)
        logger.info("New game created: {name}".format(name=name))

    def save(self, event):
        # type: (int) -> None
        self.profile.SetString(self.profile.GetSelection(), self.prof_name.GetValue())
        self.game.name = self.prof_name.GetValue()
        self.game.config_path = self.game_path.GetPath()
        self.game.audio_dir = os.path.relpath(self.audio_path.GetPath())
        self.game.audio_rate = self.game_rate.GetValue()
        self.game.relay_key = self.relay_choice.GetStringSelection()
        self.game.play_key = self.play_choice.GetStringSelection()
        config.set_games(self.games)
        config.save()
        self.games = config.get_games()  # Just in case, to keep it in sync.

    def remove(self, event):
        name = self.game.name
        print(self.profile.GetSelection())
        self.games.pop(self.profile.GetSelection())
        config.set_games(self.games)
        config.save()
        self.profile.Set([game.name for game in self.games])
        self.profile.SetSelection(0)
        self.update_profile(None)
        logger.info("Game removed: {name}".format(name=name))


def get_steam_path():
    # type: () -> str
    if not windows:
        return ''

    try:
        reg_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Valve\Steam')
        return winreg.QueryValueEx(reg_key, r'SteamPath')[0]
    except WindowsError:
        logger.exception("Could not query registry for Steam path")
        return ''


def start_logger():
    global logger  # Is this bad practice?
    logger = logging.getLogger('jam')
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(fmt='%(asctime)s %(levelname)s: %(message)s', datefmt='%H:%M:%S')

    stream_log = logging.StreamHandler(sys.stdout)
    stream_log.setLevel(logging.DEBUG)
    stream_log.setFormatter(formatter)
    logger.addHandler(stream_log)

    try:
        file_log = logging.FileHandler(filename='pyjam.log')
        file_log.setLevel(logging.DEBUG)
        file_log.setFormatter(formatter)
        logger.addHandler(file_log)
    except (OSError, IOError):
        logger.exception("Could not create log file.")

    sys.excepthook = lambda type, value, tb: logger.critical('\n'+''.join(traceback.format_exception(type, value, tb)))


if __name__ == '__main__':
    start_logger()
    wx_app = wx.App()
    # We call Config() after calling the wx.App() because the Config().load() function shows a wx.MessageBox if failed.
    config = jam_tools.Config('jamconfig.json')
    frame = MainFrame()
    wx_app.MainLoop()
