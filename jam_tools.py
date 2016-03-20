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
import os
import shutil
import traceback
import glob
import json
import logging
from string import whitespace, punctuation

import psutil
import unidecode
import wx  # Tested w/ wxPhoenix 3.0.2
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from jam_about import __version__

try:
    try:
        import _winreg as winreg
    except ImportError:
        import winreg
except ImportError:
    winreg = False

# If on Python 2, FileNotFoundError should be created to prevent errors.
try:
    FileNotFoundError  # This will throw a NameError if the user is using Python 2.
except NameError:
    FileNotFoundError = OSError

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
# Conversion table for wx -> Source keys.
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

logger = logging.getLogger('jam.tools')


def wrap_exceptions(func):
    def _wrap_exceptions(*args, **kwargs):
        # args[0] = InstanceOfSomeClass() when wrapping a class method. (IT BETTER BE. WHYDOISUCKATPROGRAMMINGOHGOD)
        # This should really only be used on threads (main thread has a sys.excepthook)
        try:
            return func(*args, **kwargs)
        except UnicodeError:
            pass
        except Exception:
            error_message = ''.join(traceback.format_exc())
            error_dialog = wx.MessageDialog(parent=wx.GetApp().GetTopWindow(),
                                            message="An error has occured\n\n" + error_message,
                                            caption="ERROR!", style=wx.OK | wx.ICON_ERROR)
            error_dialog.ShowModal()
            error_dialog.Destroy()
            logger.critical(error_message)
            try:
                args[0].abort()
                args[0].parent.Destroy()
            except AttributeError:
                pass
            raise

    return _wrap_exceptions


class Config(object):
    def __init__(self, config_file):
        self.config_file = config_file
        self.steam_path = ''
        self.games = []
        self.load()

    def new(self):
        # this is ugly
        steam = get_steam_path()
        csgo_path = os.path.normpath(os.path.join(steam, 'steamapps/common/Counter-Strike Global Offensive/csgo'))
        css_path = os.path.normpath(os.path.join(steam, 'steamapps/common/Counter-Strike Source/css'))
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
        # type: () -> str, list
        try:
            with open(self.config_file) as f:
                try:
                    config_json = json.load(f)
                except ValueError:
                    error = wx.MessageDialog(parent=wx.GetApp().GetTopWindow(),
                                             message="Malformed config file! Overwriting with default.",
                                             caption="Error!", style=wx.OK | wx.ICON_WARNING)
                    error.ShowModal()
                    error.Destroy()
                    self.new()
                    logger.exception("Corrupt config.")
                    return self.load()
                else:
                    for game in config_json.get('games', []):
                        if not bindable(game.get('play_key', 'F8')):
                            game['play_key'] = 'F8'
                        if not bindable(game.get('relay_key', '=')):
                            game['relay_key'] = '='
                    self.steam_path = config_json.get('steam_path', os.curdir)
                    self.games = config_json.get('games', [])
        except (FileNotFoundError, IOError):
            self.new()
            return self.load()

    def save(self):
        with open(self.config_file, 'w') as f:
            # config_dict = json.loads(jsonpickle.encode(self, unpicklable=False))
            config_dict = dict(self.__dict__)  # Oh god, I've been removing the actual variable from the class...
            config_dict.pop('config_file')  # Exclude the redundant config_file variable.
            json.dump(config_dict, f, indent=4, sort_keys=True)
            logger.info("Config saved to location {loc}".format(loc=self.config_file))

    def get_games(self):
        # type: () -> list
        # ugly as sin
        return [Game(os.path.normpath(game.get('audio_dir', os.curdir)), game.get('audio_rate', 11025),
                     os.path.normpath(game.get('mod_path', os.curdir)), game.get('name'), game.get('play_key', 'F8'),
                     game.get('relay_key', '='), game.get('use_aliases', True)) for game in self.games]

    def set_games(self, new_games):
        # type: (list) -> None
        # self.games = json.loads(jsonpickle.encode(new_games, unpicklable=False))
        self.games = [dict(game.__dict__) for game in new_games]

    def __repr__(self):
        return "{c}(file={file})".format(c=self.__class__, file=self.config_file)


class Track(object):
    def __init__(self, name, aliases, path, bind=None):
        self.name = unidecode.unidecode(name)
        self.aliases = unidecode.unidecode(aliases)
        self.path = path
        self.bind = bind

    def get_aliases(self):
        return unidecode.unidecode(str(self.aliases).strip('[]') if self.aliases else "This track has no aliases")

    def get_bind(self):
        return self.bind if self.bind else " "

    def __repr__(self):
        return unidecode.unidecode("{c}(name:{name}, aliases:{aliases}, location:{path})").format(c=self.__class__,
                                                                                                  name=self.name,
                                                                                                  aliases=self.aliases,
                                                                                                  path=self.path)

    def __str__(self):
        return "Music Track: {name}".format(name=self.name)


class Game(object):
    def __init__(self, audio_dir=os.curdir, audio_rate='11025', mod_path=os.curdir,
                 name=None, play_key='F8', relay_key='=', use_aliases=True):
        self.audio_dir = audio_dir
        self.audio_rate = audio_rate
        self.mod_path = mod_path
        self.name = unidecode.unidecode(name)
        self.play_key = play_key
        self.relay_key = relay_key
        self.use_aliases = use_aliases

    def __repr__(self):
        return "{c}(name:{name}, rate:{rate}, path:{path})".format(c=self.__class__,
                                                                   name=self.name,
                                                                   rate=self.audio_rate,
                                                                   path=self.mod_path)

    def __str__(self):
        return "Source Engine Game: {name}".format(name=self.name)


class Jam(object):
    def __init__(self, steam_path, game_class, tracks):
        self.steam_path = steam_path
        self.game = game_class
        self.tracks = tracks
        self.user_data = os.path.normpath(os.path.join(self.steam_path, 'userdata'))
        self.voice = os.path.normpath(os.path.join(self.game.mod_path, os.path.join(os.path.pardir, 'voice_input.wav')))
        self.observer = JamObserver()
        self.event_handler = JamHandler(self)

    def start(self):
        self.observer.schedule(self.event_handler, self.user_data, recursive=True)
        self.observer.start()
        write_configs(self.game.mod_path, self.tracks, self.game.play_key, self.game.relay_key, self.game.use_aliases)

        with open(os.path.normpath(os.path.join(self.game.mod_path, "cfg/autoexec.cfg")), 'a') as cfg:
            cfg.write('\nexec jam\n')

    def stop(self):
        self.observer.stop()
        self.observer.join()

        try:
            os.remove(os.path.normpath(os.path.join(self.game.mod_path, "cfg/jam.cfg")))
            os.remove(os.path.normpath(os.path.join(self.game.mod_path, "cfg/jam_la.cfg")))
            os.remove(os.path.normpath(os.path.join(self.game.mod_path, "cfg/jam_curtrack.cfg")))
            os.remove(os.path.normpath(os.path.join(self.game.mod_path, "cfg/jam_saycurtrack.cfg")))
            os.remove(os.path.normpath(os.path.join(self.game.mod_path, self.voice)))
        except (FileNotFoundError, IOError):
            logger.exception("Could not remove some files:")

        with open(os.path.normpath(os.path.join(self.game.mod_path, "cfg/autoexec.cfg"))) as cfg:
            autoexec = cfg.readlines()

        with open(os.path.normpath(os.path.join(self.game.mod_path, "cfg/autoexec.cfg")), "w") as cfg:
            for line in autoexec:
                if "exec jam" not in line:
                    cfg.write(line)

    def load_song(self, path):
        song_id = self.poll_song(path)
        try:
            track = self.tracks[song_id]
        except IndexError:
            return

        shutil.copy(track.path, self.voice)
        with open(os.path.normpath(os.path.join(self.game.mod_path, "cfg/jam_curtrack.cfg")), 'w') as cfg:
            cfg.write('echo "pyjam :: Song :: {name}"\n'.format(name=track.name))
        with open(os.path.normpath(os.path.join(self.game.mod_path, "cfg/jam_saycurtrack.cfg")), 'w') as cfg:
            cfg.write('say "pyjam :: Song :: {name}"\n'.format(name=track.name))

    def poll_song(self, path):
        song = None
        with open(path) as cfg:
            for line in cfg:
                # Get rid of the leading/trailing spaces.
                line = line.strip()
                # Get rid of quotes
                line = line.replace('"', '').replace("'", '')
                line = line.split()
                if line[0] == 'bind' and line[1] == self.game.relay_key:
                    try:
                        song = int(line[2])
                        break
                    except ValueError:
                        pass
        return song


class JamHandler(FileSystemEventHandler):
    def __init__(self, calling_class):
        super(JamHandler, self).__init__()
        self.calling = calling_class

    def on_modified(self, event):
        if os.path.basename(event.src_path) == "jam_cmd.cfg":
            self.calling.load_song(event.src_path)

    def on_moved(self, event):
        # This isn't really needed, but it's useful for things that use something like atomic saving.
        if os.path.basename(event.src_path) == "jam_cmd.cfg":
            self.calling.load_song(event.src_path)
        elif os.path.basename(event.dest_path) == "jam_cmd.cfg":
            self.calling.load_song(event.dest_path)


class JamObserver(Observer):
    @wrap_exceptions
    def run(self):
        super(JamObserver, self).run()

    def abort(self):
        self.stop()
        self.join()


def write_configs(path, tracks, play_key, relay_key, use_aliases):
    # /!\ Use double-quotes (") for Source engine configs! /!\
    # Lazy debugging stuff:
    # logger.write = lambda x: logger.debug(x)
    # cfg = logger
    with open(os.path.normpath(os.path.join(path, "cfg/jam.cfg")), 'w') as cfg:
        cfg.write('bind {play_key} jam_play\n'.format(play_key=play_key))
        cfg.write('alias jam_play jam_on\n')
        cfg.write('alias jam_on "voice_inputfromfile 1; voice_loopback 1; +voicerecord; alias jam_play jam_off"\n')
        cfg.write('alias jam_off "voice_inputfromfile 0; voice_loopback 0; -voicerecord; alias jam_play jam_on"\n')
        cfg.write('alias jam_writecmd "host_writeconfig jam_cmd"\n')
        cfg.write('alias jam_listaudio "exec jam_la"\n')
        cfg.write('alias jam_la jam_listaudio\n')
        cfg.write('alias la jam_listaudio\n')
        cfg.write('alias jam_saytrack "exec jam_saycurtrack"\n')
        cfg.write('alias jam_say jam_saytrack\n')
        cfg.write('alias jam_echotrack "exec jam_curtrack"\n')
        cfg.write('alias jam_track jam_echotrack\n')
        for x, track in enumerate(tracks):
            cfg.write('alias {x} "bind {relay} {x}; echo Loaded: {name}; jam_writecmd"\n'.format(x=x,
                                                                                                 relay=relay_key,
                                                                                                 name=track.name))
            if use_aliases:
                for alias in track.aliases:
                    cfg.write('alias {alias} {x}\n'.format(alias=alias, x=x))
            if track.bind:
                cfg.write('bind {bind} {x}\n'.format(bind=track.bind, x=x))
        cfg.write('voice_enable 1; voice_modenable 1\n')
        cfg.write('voice_forcemicrecord 0\n')
        cfg.write('voice_fadeouttime 0.0\n')
        cfg.write('con_enable 1; showconsole\n')
        cfg.write('echo "pyjam v{v} loaded. Type "la" or "jam_listaudio" for a list of tracks.\n'.format(v=__version__))
        logger.info("Wrote jam.cfg to {path}".format(path=cfg.name))
    with open(os.path.normpath(os.path.join(path, "cfg/jam_la.cfg")), 'w') as cfg:
        for x, track in enumerate(tracks):
            cfg.write('echo "{x}. {name}. Aliases: {aliases}"\n'.format(x=x, name=track.name, aliases=track.aliases))
        logger.info("Wrote jam_la.cfg to {path}".format(path=cfg.name))
    with open(os.path.normpath(os.path.join(path, "cfg/jam_curtrack.cfg")), 'w') as cfg:
        cfg.write('echo "pyjam :: No song loaded"\n')
        logger.info("Wrote jam_curtrack.cfg to {path}".format(path=cfg.name))
    with open(os.path.normpath(os.path.join(path, "cfg/jam_saycurtrack.cfg")), 'w') as cfg:
        cfg.write('say "pyjam :: No song loaded"\n')
        logger.info("Wrote jam_saycurtrack.cfg to {path}".format(path=cfg.name))


def get_tracks(audio_path):
    # type: (str) -> list
    black_list = ['cheer', 'compliment', 'coverme', 'enemydown', 'enemyspot', 'fallback', 'followme', 'getout',
                  'go', 'holdpos', 'inposition', 'negative', 'regroup', 'report', 'reportingin', 'roger', 'sectorclear',
                  'sticktog', 'takepoint', 'takingfire', 'thanks', 'drop', 'sm', 'buy']
    current_tracks = []
    bound_keys = []

    # Format for custom track data.
    # {
    #     "song1": {"aliases": ["alias1", "alias2", "etc."], "bind": "DOWNARROW"},
    #     "song2": {"aliases": ["alias3", "alias4", "etc."], "bind": "KP_INS"}
    # }
    logger.info("Generating track list with path {path}".format(path=audio_path))
    try:
        with open(os.path.join(audio_path, 'track_data.json')) as f:
            track_data = json.load(f)
    except FileNotFoundError:
        track_data = {}
    except (IOError, ValueError):
        track_data = {}
        logger.exception("Invalid track data for {path}".format(path=os.path.join(audio_path, 'track_data.json')))

    for track in glob.glob(os.path.join(audio_path, '*.wav')):
        bind = None
        name = os.path.splitext(os.path.basename(track))[0]  # Name of file minus path/extension
        name = unidecode.unidecode(name)
        if name in track_data and ('aliases' in track_data[name] or 'bind' in track_data[name]):
            custom_aliases = track_data[name].get('aliases')
            custom_bind = track_data[name].get('bind')
            if custom_aliases:
                aliases = [filter_aliases(x) for x in custom_aliases if x not in black_list and x not in whitespace]
            else:
                aliases = [x for x in filter_aliases(name).split() if x not in black_list and x not in whitespace]

            if custom_bind and bindable(custom_bind) and custom_bind not in bound_keys:
                bind = custom_bind
                bound_keys.extend(custom_bind)
        else:
            aliases = [x for x in filter_aliases(name).split() if x not in black_list and x not in whitespace]
        black_list.extend(aliases)
        current_tracks.append(Track(name, aliases, track, bind))

    logger.debug("Generated track list {tracks}".format(tracks='\n'.join([repr(x) for x in current_tracks])))
    return current_tracks


def filter_aliases(alias_or_name):
    # type: (str) -> str
    # No non-alphanumerical characters, thanks. Though, 'alias' does support quite a few of them. Too lazy to filter.
    filtered_name = ''
    for char in alias_or_name:
        if char.isalpha() or char.isspace():
            filtered_name += char.lower()
        elif char is not "'":
            filtered_name += ' '
    return filtered_name


def get_steam_path():
    # type: () -> str
    for pid in psutil.process_iter():
        try:
            if pid.name().lower() == "steam.exe" or pid.name().lower() == "steam":
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


def bindable(key):
    # type: (str) -> bool or str

    if isinstance(key, str):
        return key.upper() in SOURCE_KEYS
    elif isinstance(key, int):
        if key in WX_KEYS_CONVERSION:
            return WX_KEYS_CONVERSION[key]
        elif chr(key).upper() in SOURCE_KEYS:
            return True
        else:
            return False

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
