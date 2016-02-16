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
import logging

import wx  # Tested w/ wxPhoenix 3.0.2
import wx.lib.intctrl
import ObjectListView as OLV

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

ID_SELECT_GAME = wx.NewId()
ID_SELECT_PROFILE = wx.NewId()
ID_START = wx.NewId()
ID_TRACKS = wx.NewId()
NO_ALIASES = "This track has no aliases"  # im lazy, okay?

class MainFrame(wx.Frame):
    def __init__(self):
        super(MainFrame, self).__init__(parent=None, title="pyjam", size=(600, 400))
        self.SetMinSize(self.GetSize())
        panel = MainPanel(self)

        file_menu = wx.Menu()
        file_menu.Append(wx.ID_SETUP, "&Settings", "Jam Setup")
        help_menu = wx.Menu()
        help_menu.Append(wx.ID_ABOUT, "&About", "About pyjam")

        menu_bar = wx.MenuBar()
        menu_bar.Append(file_menu, "&File")
        menu_bar.Append(help_menu, "&Help")

        self.SetMenuBar(menu_bar)

        icon = wx.Icon('pyjam.ico', wx.BITMAP_TYPE_ICO)
        self.SetIcon(icon)

        self.Bind(wx.EVT_MENU, panel.settings, id=wx.ID_SETUP)
        self.Bind(wx.EVT_MENU, lambda x: jam_about.about_info(self), id=wx.ID_ABOUT)
        self.Show()


class MainPanel(wx.Panel):
    def __init__(self, parent):
        super(MainPanel, self).__init__(parent)
        self.parent_frame = parent
        self.games = config.get_games()

        while not self.games:
            wx.MessageDialog(parent=None,
                             message="You have no games profiles set up. Please set one up now.",
                             caption="Info", style=wx.OK | wx.ICON_INFORMATION).ShowModal()
            self.settings(None)

        self.profile = wx.ComboBox(self, ID_SELECT_GAME, choices=[game.name for game in self.games],
                                   style=wx.CB_READONLY)
        self.profile.SetSelection(0)
        self.selection = self.profile.GetSelection()
        self.audio_dir = self.games[self.selection].audio_dir

        self.track_list = OLV.ObjectListView(self, id=ID_TRACKS, style=wx.LC_REPORT | wx.BORDER_SUNKEN, sortable=False,
                                             useAlternateBackColors=False)
        self.track_list.SetEmptyListMsg("You currently do not have any sound files for this game.")
        self.track_list.SetColumns([
            OLV.ColumnDefn(title="Title", align="left", width=220, valueGetter="name", isSpaceFilling=True),
            OLV.ColumnDefn(title="Aliases", align="left", width=300, valueGetter="get_aliases", isSpaceFilling=True),
        ])

        self.track_list.rowFormatter = lambda x, y: x.SetTextColour(wx.RED) if y.get_aliases() == NO_ALIASES else None
        self.track_list.SetObjects(jam_tools.get_tracks(self.audio_dir))

        refresh_but = wx.Button(self, wx.ID_REFRESH, "Refresh tracks")
        start_button = wx.Button(self, ID_START, "Start")
        convert_button = wx.Button(self, wx.ID_CONVERT, "Audio converter")

        top_sizer = wx.BoxSizer(wx.VERTICAL)  # Root sizer
        profile_sizer = wx.BoxSizer(wx.VERTICAL)  # For the profile selection
        olv_sizer = wx.BoxSizer(wx.VERTICAL)  # For the ObjectListView
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)  # Start/Stop and Refresh buttons

        profile_sizer.Add(self.profile, 0, wx.LEFT | wx.RIGHT | wx.EXPAND | wx.ALIGN_TOP, 5)
        olv_sizer.Add(self.track_list, 1, wx.LEFT | wx.RIGHT | wx.EXPAND | wx.ALIGN_TOP, 5)
        button_sizer.Add(refresh_but, 0, wx.ALL | wx.ALIGN_LEFT, 5)
        button_sizer.Add(start_button, 0, wx.ALL | wx.ALIGN_LEFT, 5)
        button_sizer.Add(convert_button, 0, wx.ALL | wx.ALIGN_LEFT, 5)

        top_sizer.Add(profile_sizer, 0, wx.ALL | wx.EXPAND, 5)
        top_sizer.Add(olv_sizer, 1, wx.ALL | wx.EXPAND, 5)
        top_sizer.Add(button_sizer, 0, wx.ALL | wx.EXPAND, 5)
        self.SetSizerAndFit(top_sizer)

        self.Bind(wx.EVT_COMBOBOX, self.game_select, id=ID_SELECT_GAME)
        self.Bind(wx.EVT_BUTTON, lambda x: self.track_list.SetObjects(jam_tools.get_tracks(self.audio_dir)), id=wx.ID_REFRESH)
        self.Bind(wx.EVT_BUTTON, self.start, id=ID_START)
        self.Bind(wx.EVT_BUTTON, self.convert, id=wx.ID_CONVERT)
        # TODO: Use this for things such as manually adding aliases
        # TODO: Create a GUI for above. (Context menu>Set aliases>GUI)
        # self.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, lambda x: logger.info(x.GetIndex()), id=ID_TRACKS)

    def game_select(self, event):
        # type: (int) -> None
        self.selection = self.profile.GetSelection()
        self.game = self.games[self.selection]
        self.audio_dir = self.game.audio_dir
        self.track_list.SetObjects(jam_tools.get_tracks(self.audio_dir))

    def start(self, event):
        # type: (int) -> None
        # logger.info(len(self.track_list.GetObjects()))
        # for track in self.track_list.GetObjects():
        #     logger.info("{}, {}, {}".format(track.name, track.aliases, track.path))
        tracks = self.track_list.GetObjects()
        play_key = self.game.play_key
        relay_key = self.game.play_key
        jam_tools.write_src_config(None, tracks, play_key, relay_key)

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
                info = ("Please download it and place FFmpeg.exe in your PATH\n"
                        "or inside the folder pyjam is in. You can download it at:\n\n"
                        "http://ffmpeg.zeranoe.com/")

                wx.MessageDialog(self, info, "pyjam").ShowModal()
        elif ffmpeg.find() is None:
            wx.MessageDialog(self, "You require FFmpeg to convert audio. Please install it.", "pyjam").ShowModal()
        else:
            # TODO: Implement audio conversion with FFmpeg.
            ffmpeg.FFmpegConvertDialog(self)

    def settings(self, event):
        # type: (int) -> None
        SetupDialog(self)
        self.games = config.get_games()
        self.profile.Set([game.name for game in self.games])
        self.profile.SetSelection(0)
        self.selection = self.profile.GetSelection()
        self.game = self.games[self.selection]
        self.audio_dir = self.game.audio_dir


class SetupDialog(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, title="pyjam Setup", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

        self.games = config.get_games()
        self.profile = wx.ComboBox(self, ID_SELECT_PROFILE, choices=[game.name for game in self.games],
                                   style=wx.CB_READONLY)
        self.selection = self.profile.GetSelection()

        separator = wx.StaticLine(self, style=wx.LI_HORIZONTAL, size=(self.profile.GetSize()[0], 1))

        self.prof_name = wx.TextCtrl(self)
        prof_name_text = wx.StaticText(self, label="Real Name (e.g. Counter-Strike: Source)")

        self.game_path = wx.DirPickerCtrl(self, name="Path to game")
        game_path_text = wx.StaticText(self, label="Path to game (e.g. steamapps/common/Team Fortress 2/tf2)")
        if not config.steam_path:
            self.game_path.SetInitialDirectory(get_steam_path())
        else:
            self.game_path.SetPath(config.steam_path)

        self.game_rate = wx.lib.intctrl.IntCtrl(self, allow_none=False)
        game_rate_text = wx.StaticText(self, label="Audio rate (usually 11025 or 22050)")

        save_button = wx.Button(self, wx.ID_SAVE, label="Save Game")
        new_button = wx.Button(self, wx.ID_NEW, label="New Game")
        done_button = wx.Button(self, wx.ID_EXIT, label="Finished")

        # Sizer stuff
        top_sizer = wx.BoxSizer(wx.VERTICAL)
        profile_sizer = wx.BoxSizer(wx.VERTICAL)
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)

        top_sizer.Add(profile_sizer, 1, wx.ALL | wx.EXPAND | wx.ALIGN_TOP, 5)
        top_sizer.Add(button_sizer, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
        profile_sizer.Add(self.profile, 0, wx.ALL ^ wx.LEFT | wx.ALIGN_LEFT, 5)
        profile_sizer.Add(separator, 0, wx.TOP | wx.BOTTOM | wx.ALIGN_LEFT)
        profile_sizer.Add(self.prof_name, 0, wx.ALL ^ wx.LEFT | wx.ALIGN_LEFT | wx.EXPAND, 5)
        profile_sizer.Add(prof_name_text, 0, wx.ALL | wx.ALIGN_LEFT)
        profile_sizer.Add(self.game_path, 0, wx.ALL ^ wx.LEFT ^ wx.RIGHT | wx.ALIGN_LEFT | wx.EXPAND, 5)
        profile_sizer.Add(game_path_text, 0, wx.BOTTOM | wx.ALIGN_LEFT, 10)
        profile_sizer.Add(self.game_rate, 0, wx.ALL ^ wx.LEFT | wx.ALIGN_LEFT, 5)
        profile_sizer.Add(game_rate_text, 0, wx.ALL | wx.ALIGN_LEFT)
        button_sizer.Add(save_button, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        button_sizer.Add(new_button, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        button_sizer.Add(done_button, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        self.Bind(wx.EVT_COMBOBOX, self.update_profile, id=ID_SELECT_PROFILE)
        self.Bind(wx.EVT_BUTTON, self.save, id=wx.ID_SAVE)
        self.Bind(wx.EVT_BUTTON, self.new, id=wx.ID_NEW)
        self.Bind(wx.EVT_BUTTON, lambda x: self.Close(), id=wx.ID_EXIT)
        self.SetSizerAndFit(top_sizer)
        self.Center()
        if not self.games:
            self.new(None)
        self.ShowModal()

    def update_profile(self, event):
        # type: (int) -> None
        self.selection = self.profile.GetSelection()
        self.games = config.get_games()
        try:
            self.prof_name.SetValue(str(self.games[self.selection].name))
            self.game_path.SetPath(str(self.games[self.selection].config_path))
            self.game_rate.SetValue(str(self.games[self.selection].audio_rate))
        except (IndexError, NameError):  # I don't think a TypeError can happen. Now, at least.
            self.prof_name.Clear()
            self.game_path.Clear()
            self.game_rate.Clear()

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
        self.games = config.get_games()  # Just in case, to keep it in sync.
        self.profile.SetSelection(self.profile.GetCount() - 1)
        self.update_profile(None)
        logger.info("New game created: {name}".format(name=name))

    def save(self, event):
        # type: (int) -> None
        if self.selection == wx.NOT_FOUND:
            return wx.MessageBox(message="You must select a game first!", caption="Info", parent=self)

        self.profile.SetString(self.selection, self.name.GetValue())
        self.games[self.selection].name = self.prof_name.GetValue()
        self.games[self.selection].config_path = self.game_path.GetPath()
        self.games[self.selection].audio_rate = self.game_rate.GetValue()
        config.set_games(self.games)
        config.save()


# This stuff will probably get moved somewhere

def get_steam_path():
    # type: () -> str
    if not windows:
        return ''

    try:
        reg_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Valve\Steam')
        return winreg.QueryValueEx(reg_key, r'SteamPath')[0]
    except WindowsError:
        return ''


def start_logger():
    global logger  # Is this bad practice?
    logger = logging.getLogger()
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
        print("Could not create log file.")

    return logger



if __name__ == "__main__":
    start_logger()
    wx_app = wx.App()
    # We call Config() after calling the wx.App() because the Config().load() function shows a wx.MessageBox if failed.
    config = jam_tools.Config('jamconfig.json')
    frame = MainFrame()
    wx_app.MainLoop()
