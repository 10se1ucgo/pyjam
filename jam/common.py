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

# A module that will probably be filled with common tools for all other jam_* modules.
# This module should NOT import anything from jam_*, as it will create potential for circular imports.
import logging
import os
import traceback
import sys
from functools import wraps

import psutil
import unidecode
import wx

try:
    import winreg
except ImportError:
    try:
        import _winreg as winreg
    except ImportError:
        winreg = False

__all__ = ["SOURCE_KEYS", "WX_KEYS_CONVERSION", "Track", "Game", "wrap_exceptions", "get_steam_path",
           "get_path", "bindable", "key_choice_override"]
logger = logging.getLogger(__name__)

# Special characters taken from the VDC wiki.
SOURCE_KEYS = (
    ',', '.', "'", '/', '[', ']', '\\', '-', '=', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0',
    'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S',
    'T', 'U', 'V', 'W', 'X', 'Y', 'Z', 'F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7', 'F8', 'F9', 'F10',
    'F11', 'F12', 'TAB', 'ENTER', 'ESCAPE', 'SPACE', 'BACKSPACE', 'UPARROW', 'DOWNARROW', 'LEFTARROW',
    'RIGHTARROW', 'ALT', 'CTRL', 'SHIFT', 'INS', 'DEL', 'PGDN', 'PGUP', 'HOME', 'END', 'KP_HOME',
    'KP_UPARROW', 'KP_PGUP', 'KP_LEFTARROW', 'KP_5', 'KP_RIGHTARROW', 'KP_END', 'KP_DOWNARROW',
    'KP_PGDN', 'KP_ENTER', 'KP_INS', 'KP_DEL', 'KP_SLASH', 'KP_MULTIPLY', 'KP_MINUS', 'KP_PLUS',
    'CAPSLOCK', 'MWHEELDOWN', 'MWHEELUP', 'MOUSE1', 'MOUSE2', 'MOUSE3', 'MOUSE4', 'MOUSE5', 'PAUSE'
)
# Conversion table for wx -> Source Engine keys.
WX_KEYS_CONVERSION = {
    wx.WXK_F1: 'F1', wx.WXK_F2: "F2", wx.WXK_F3: "F3", wx.WXK_F4: "F4", wx.WXK_F5: "F5", wx.WXK_F6: "F6",
    wx.WXK_F7: "F7", wx.WXK_F8: "F8", wx.WXK_F9: "F9", wx.WXK_F10: "F10", wx.WXK_F11: "F11",
    wx.WXK_F12: "F12", wx.WXK_TAB: "TAB", wx.WXK_RETURN: "ENTER", wx.WXK_ESCAPE: "ESCAPE",
    wx.WXK_SPACE: "SPACE", wx.WXK_BACK: "BACKSPACE", wx.WXK_UP: "UPARROW", wx.WXK_DOWN: "DOWNARROW",
    wx.WXK_LEFT: "LEFTARROW", wx.WXK_RIGHT: "RIGHTARROW", wx.WXK_ALT: "ALT", wx.WXK_CONTROL: "CTRL",
    wx.WXK_SHIFT: "SHIFT", wx.WXK_INSERT: "INS", wx.WXK_DELETE: "DEL", wx.WXK_PAGEDOWN: "PGDN",
    wx.WXK_PAGEUP: "PGUP", wx.WXK_HOME: "HOME", wx.WXK_END: "END", wx.WXK_NUMPAD_HOME: "KP_HOME",
    wx.WXK_NUMPAD_UP: "KP_UPARROW", wx.WXK_NUMPAD_PAGEUP: "KP_PGUP", wx.WXK_NUMPAD_LEFT: "KP_LEFTARROW",
    wx.WXK_NUMPAD5: "KP_5", wx.WXK_NUMPAD_RIGHT: "KP_RIGHTARROW", wx.WXK_NUMPAD_END: "KP_END",
    wx.WXK_NUMPAD_DOWN: "KP_DOWNARROW", wx.WXK_NUMPAD_PAGEDOWN: "KP_PGDN", wx.WXK_NUMPAD_ENTER: "KP_ENTER",
    wx.WXK_NUMPAD_INSERT: "KP_INS", wx.WXK_NUMPAD_DELETE: "KP_DEL", wx.WXK_NUMPAD_DIVIDE: "KP_SLASH",
    wx.WXK_NUMPAD_MULTIPLY: "KP_MULTIPLY", wx.WXK_NUMPAD_SUBTRACT: "KP_MINUS", wx.WXK_NUMPAD_ADD: "KP_PLUS",
    wx.WXK_CAPITAL: "CAPSLOCK", wx.WXK_PAUSE: "PAUSE", wx.WXK_NUMPAD0: "KP_INS",
    wx.WXK_NUMPAD_DECIMAL: "KP_DEL", wx.WXK_NUMPAD1: "KP_END", wx.WXK_NUMPAD2: "KP_DOWNARROW",
    wx.WXK_NUMPAD3: "KP_PGDN", wx.WXK_NUMPAD4: "KP_LEFTARROW", wx.WXK_NUMPAD6: "KP_RIGHTARROW",
    wx.WXK_NUMPAD7: "KP_HOME", wx.WXK_NUMPAD8: "KP_UPARROW", wx.WXK_NUMPAD9: "KP_PGUP"
}


class Track(object):
    """
    A class representing a sound track.
    """
    def __init__(self, index, name, aliases, path, bind=None):
        """
        Args:
            index (int): The ID of the Track. The value can be random, it is only used for display.
            name (str): The name of the Track. Also only used for display.
            aliases (list[str]): A list of aliases that can be used in-game instead of the index.
            path (str): Path to the file.
            bind (str or None): Bind that the track can be used.
        """
        self.index = index
        self.name = unidecode.unidecode(name)
        self.aliases = [unidecode.unidecode(alias) for alias in aliases]
        self.path = path
        self.bind = bind if bindable(bind) else ''

    def get_aliases(self):
        """Get the Track's aliases..

        Returns:
            str: A string representation of the aliases.
        """
        return str(self.aliases).strip('[]') if self.aliases else "This track has no aliases"

    def __repr__(self):
        return "{c}(index:{index}, name:{name}, aliases:{aliases}, location:{path})".format(
            c=self.__class__, index=self.index, name=self.name, aliases=self.aliases, path=self.path
        )

    def __str__(self):
        return "Music Track: {name}".format(name=self.name)


class Game(object):
    """
    A class representing a Source Engine game.
    """
    def __init__(self, audio_dir=os.curdir, audio_rate=11025, mod_path=os.curdir,
                 name=None, play_key='F8', relay_key='=', use_aliases=True):
        """
        Args:
            audio_dir (str): Path for finding audio.
            audio_rate (int): The sample rate the game accepts.
            mod_path (str): Path to the mod folder (e.g. "Steam/SteamApps/common/Team Fortress 2/tf2")
            name (str): The name of the game.
            play_key (str): The key used to start/stop music in-game.
            relay_key (str): The key used to interact with the game.
            use_aliases (bool): Whether or not to use aliases to select songs in-game.
        """
        self.audio_dir = audio_dir
        self.audio_rate = audio_rate
        self.mod_path = mod_path
        self.name = unidecode.unidecode(name)
        self.play_key = play_key if bindable(play_key) else "F8"
        self.relay_key = relay_key if bindable(relay_key) else "="
        self.use_aliases = use_aliases

    def __repr__(self):
        return "{c}(name:{name}, rate:{rate}, path:{path})".format(
            c=self.__class__, name=self.name, rate=self.audio_rate, path=self.mod_path
        )

    def __str__(self):
        return "Source Engine Game: {name}".format(name=self.name)


def wrap_exceptions(func):
    """Wraps a function with an "exception hook" for threads.

    Args:
        func (function): The function to wrap.

    Returns:
        function: The wrapped function
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # args[0] = when wrapping a class method. (IT BETTER BE. WHYDOISUCKATPROGRAMMINGOHGOD)
        # This should really only be used on threads (main thread has a sys.excepthook)
        try:
            return func(*args, **kwargs)
        except (SystemExit, KeyboardInterrupt):
            raise
        except Exception:
            if isinstance(args[0], wx.TopLevelWindow):
                parent = args[0]
            elif hasattr(args[0], "parent") and isinstance(args[0].parent, wx.TopLevelWindow):
                parent = args[0].parent
            else:
                parent = wx.GetApp().GetTopWindow()
            error_message = ''.join(traceback.format_exc())
            error_dialog = wx.MessageDialog(parent=parent,
                                            message="An error has occured\n\n" + error_message,
                                            caption="Error!", style=wx.OK | wx.ICON_ERROR)
            error_dialog.RequestUserAttention()
            error_dialog.ShowModal()
            error_dialog.Destroy()
            logger.critical(error_message)
            raise

    return wrapper


def bindable(key):
    """Test if a key is a valid Source Engine key.
    Args:
        key (str or int): Either the wx.WXK key code, or the string key.

    Returns:
        bool or str: If True, the key is already a valid Source Engine key. If a str, the key was able to be converted.
            False otherwise.
    """
    if isinstance(key, str):
        return key.upper() in SOURCE_KEYS
    elif isinstance(key, int):
        if key in WX_KEYS_CONVERSION:
            return WX_KEYS_CONVERSION[key]
        elif chr(key).upper() in SOURCE_KEYS:
            return True

    return False


def key_choice_override(event):
    converted = bindable(event.GetKeyCode())
    # If converted gave us a bool, it's already a compatible key
    if converted is True:
        event.GetEventObject().SetStringSelection(chr(event.GetKeyCode()))
        return True
    # If converted gave us a string, it was converted
    elif converted:
        event.GetEventObject().SetStringSelection(converted)
        return True
    # Otherwise, it's not compatible and can't be converted.
    return False


def get_steam_path():
    """Get the path for Steam from the Steam process. If that fails, it uses the registry on Windows.
    Returns:
        str: The path to Steam. If the path could not be found, the current directory is returned instead (os.curdir)
    """
    for pid in psutil.process_iter():
        try:
            if pid.name().lower() == 'steam.exe' or pid.name().lower() == 'steam':
                return os.path.dirname(pid.exe())
        except psutil.Error:
            logger.exception("Could not get Steam path from its process.")

    if winreg:
        try:
            reg_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Valve\Steam')
            return os.path.normpath(winreg.QueryValueEx(reg_key, r'SteamPath')[0])
        except WindowsError:
            logger.exception("Could not query registry for Steam path")

    return os.curdir


def get_path(path1, path2=None):
    """Convert a string (or two) to a normalized (optionally joined) path string.

    Args:
        path1 (str): The path string to be normalized. (If path2 is given, they will be joined)
        path2 (Optional[str]): The second path string to be joined with path1. Defaults to None.

    Returns:
        str: The normalized (and joined, if path2 != None)

    Raises:
        TypeError: If `path1` or `path2` are not strings.
    """
    if path2:
        return os.path.normpath(os.path.join(path1, path2))
    return os.path.normpath(path1)


def get_resource(path):
    """Get the absolute path for a resource. Required for PyInstaller.

    Args:
        path (str): The relative path to the resource.

    Returns:
        str: The absolute path to the resource.
    """
    base = getattr(sys, '_MEIPASS', os.curdir)
    return os.path.abspath(os.path.join(base, path))
