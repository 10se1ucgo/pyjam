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
import os
import glob
import json
import logging
from string import whitespace, punctuation

import wx  # Tested w/ wxPhoenix 3.0.2
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from jam_about import __version__


class Config(object):
    def __init__(self, config_file):
        self.config_file = config_file
        self.steam_path, self.games = self.load()

    def new(self):
        # this is ugly
        default_config = {u'steam_path': u'C:/Program Files (x86)/Steam/', u'games': [
                         {u'audio_dir': u'audio/csgo/',
                          u'name': u'Counter-Strike: Global Offensive', u'relay_key': u'=',
                          u'play_key': u'F8', u'app_id': u'730', u'audio_rate': 22050,
                          u'mod_name': u'csgo'},
                         {u'audio_dir': u'audio/css/', u'name': u'Counter-Strike: Source',
                          u'relay_key': u'+', u'play_key': u'F8', u'app_id': u'240', u'audio_rate': 11025,
                          u'mod_name': u'css'}]}

        with open(self.config_file, 'w') as f:
            json.dump(default_config, f, indent=4, sort_keys=True)

    def load(self):
        # type: () -> str, list
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                try:
                    config_json = json.load(f)
                except ValueError:
                    wx.MessageDialog(parent=None,
                                     message="Malformed config file! Overwriting with default.",
                                     caption="Error!", style=wx.OK | wx.ICON_WARNING).ShowModal()
                    self.new()
                    logger.exception("Corrupt config.")
                    return self.load()
                else:
                    for game in config_json.get('games', []):
                        if not bindable(game.get('play_key', 'F8')):
                            game['play_key'] = 'F8s'
                        if not bindable(game.get('relay_key', '=')):
                            game['relay_key'] = '='
                    return config_json.get('steam_path', ''), config_json.get('games', [])
        else:
            self.new()
            return self.load()

    def save(self, config_file=None):
        # type: (str) -> None
        if config_file is None:
            config_file = self.config_file

        with open(config_file, 'w') as f:
            # config_dict = json.loads(jsonpickle.encode(self, unpicklable=False))
            config_dict = self.__dict__
            config_dict.pop('config_file')  # Exclude the redundant config_file variable.
            json.dump(config_dict, f, indent=4, sort_keys=True)
            logger.info("Config saved to location {loc}".format(loc=config_file))

    def get_games(self):
        # type: () -> list
        # ugly as sin
        return [Game(os.path.normpath(game.get('audio_dir', os.curdir)), game.get('audio_rate', 11025),
                     os.path.normpath(game.get('config_path', os.curdir)), game.get('name'), game.get('play_key', 'F8'),
                     game.get('relay_key', '='), game.get('use_aliases', True)) for game in self.games]

    def set_games(self, new_games):
        # type: (list) -> None
        # self.games = json.loads(jsonpickle.encode(new_games, unpicklable=False))
        self.games = [game.__dict__ for game in new_games]

    def __repr__(self):
        return "{c}(file={file})".format(c=self.__class__, file=self.config_file)


class Track(object):
    def __init__(self, name, aliases, path):
        self.name = name
        self.aliases = aliases
        self.path = path

    def get_aliases(self):
        return str(self.aliases).strip('[]') if self.aliases else "This track has no aliases"

    def __repr__(self):
        return "{c}(name:{name}, aliases:{aliases}, location{path})".format(c=self.__class__,
                                                                            name=self.name,
                                                                            aliases=self.aliases,
                                                                            path=self.path)

    def __str__(self):
        return "Music Track: {name}".format(name=self.name)


class Game(object):
    def __init__(self, audio_dir=os.curdir, audio_rate=11025, config_path=os.curdir,
                 name=None, play_key='F8', relay_key='=', use_aliases=True):
        self.audio_dir = audio_dir
        self.audio_rate = audio_rate
        self.config_path = config_path
        self.name = name
        self.play_key = play_key
        self.relay_key = relay_key
        self.use_aliases = use_aliases

    def __repr__(self):
        return "{c}(name:{name}, rate:{rate}, path:{path})".format(c=self.__class__,
                                                                   name=self.name,
                                                                   rate=self.audio_rate,
                                                                   path=self.config_path)

    def __str__(self):
        return "Source Engine Game: {name}".format(name=self.name)


class FileWatcherHandler(FileSystemEventHandler):
    def on_modified(self, event):
        print(event.src_path)


class FileWatcher(Observer):
    def __init__(self, path):
        super(FileWatcher, self).__init__()
        event_handler = FileWatcherHandler()
        self.schedule(event_handler, path)


def get_tracks(audio_path):
    # type: (str) -> list
    current_tracks = []
    black_list = ['cheer', 'compliment', 'coverme', 'enemydown', 'enemyspot', 'fallback', 'followme', 'getout',
                  'go', 'holdpos', 'inposition', 'negative', 'regroup', 'report', 'reportingin', 'roger', 'sectorclear',
                  'sticktog', 'takepoint', 'takingfire', 'thanks', 'drop', 'sm']

    # TODO: Create a GUI for creating custom aliases.
    # TODO: Read an 'aliases.json' file for custom aliases. Format will be as follows:
    # {
    #     "song1.wav": ["alias1", "alias2", "etc."],
    #     "song2.wav": ["alias1", "alias2", "etc."]
    # }
    for track in glob.glob(os.path.join(audio_path, '*.wav')):
        name = os.path.splitext(os.path.basename(track))[0]  # Name of file minus path/extension
        aliases = [x for x in filter_aliases(name).split() if x not in black_list and x not in whitespace]
        black_list.extend(aliases)
        current_tracks.append(Track(name, aliases, track))

    return current_tracks


def filter_aliases(alias_or_name):
    # type: (str) -> str
    # No non-alphanumerical characters, thanks. Though, 'alias' does support quite a few of them. Too lazy to filter.
    filtered_name = ''
    for char in alias_or_name:
        if char.isalpha() or char.isspace():
            filtered_name += char.lower()
        elif char in punctuation:
            filtered_name += ' '
    return filtered_name


def bindable(key):
    # type: (str) -> bool
    key = str(key).upper()
    # Special characters taken from the VDC wiki.
    acceptable_keys = [',', '.', "'", '/', '[', ']', '\\', '-', '=', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0',
                       'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S',
                       'T', 'U', 'V', 'W', 'X', 'Y', 'Z', 'TAB', 'ENTER', 'ESCAPE', 'SPACE', 'BACKSPACE', 'UPARROW',
                       'DOWNARROW', 'LEFTARROW', 'RIGHTARROW', 'ALT', 'CTRL', 'SHIFT', 'INS', 'DEL', 'PGDN', 'PGUP',
                       'HOME', 'END', 'KP_HOME', 'KP_UPARROW', 'KP_PGUP', 'KP_LEFTARROW', 'KP_5', 'KP_RIGHTARROW',
                       'KP_END', 'KP_DOWNARROW', 'KP_PGDN', 'KP_ENTER', 'KP_INS', 'KP_DEL', 'KP_SLASH', 'KP_MULTIPLY',
                       'KP_MINUS', 'KP_PLUS', 'CAPSLOCK', 'MWHEELDOWN', 'MWHEELUP', 'MOUSE1', 'MOUSE2', 'MOUSE3',
                       'MOUSE4', 'MOUSE5', 'PAUSE']

    acceptable_keys_wx = []

    return key in acceptable_keys


def start_jam(config, tracks, play_key, relay_key):
    raise NotImplementedError


def poll_song(relay_key):
    # type: (str) -> int
    song = None
    with open('config.cfg') as cfg:
        for line in cfg:
            # Get rid of the leading/trailing spaces.
            line = line.strip()
            # Get rid of quotes
            line = line.replace('"', '').replace("'", '')
            line = line.split()
            if line[0] == 'bind' and line[1] == relay_key:
                try:
                    song = int(line[2])
                    break
                except ValueError:
                    pass
    return song


def load_song():
    song_id = poll_song('=')


def write_src_config(config, tracks, play_key, relay_key):
    # TODO: Finish this.
    # /!\ Use double-quotes (") for Source engine configs! /!\
    # Lazy debugging stuff:
    # logger.write = lambda x: logging.info(x)
    # cfg = logger
    with open(os.path.join(config, "cfg/jam.cfg"), 'w') as cfg:
        cfg.write('bind {play_key} jam_play\n'.format(play_key=play_key))
        cfg.write('alias jam_play jam_on\n')
        cfg.write('alias jam_on "voice_inputfromfile 1; voice_loopback 1; +voicerecord; alias jam_play jam_off"\n')
        cfg.write('alias jam_off "voice_inputfromfile 0; voice_loopback 0; -voicerecord; alias jam_play jam on"\n')
        cfg.write('alias jam_writecmd "host_writecfg jam_cmd"\n')
        cfg.write('alias jam_listaudio "exec jam_la.cfg"')
        cfg.write('alias la jam_listaudio')
        for x in range(len(tracks)):
            cfg.write('alias {x} "bind {relay} {x}; echo Loaded: {name}; jam_writecmd"\n'.format(x=x,
                                                                                                 relay=relay_key,
                                                                                                 name=tracks[x].name))
            for alias in tracks[x].aliases:
                cfg.write('alias {alias} {x}\n'.format(alias=alias, x=x))
        cfg.write('voice_enable 1; voice_modenable 1')
        cfg.write('voice_forcemicrecord 0')
        cfg.write('voice_fadeouttime 0.0')
        cfg.write('con_enable 1; showconsole')
        cfg.write('echo "pyjam v{v} loaded. Type "la" or "jam_listaudio" for a list of tracks.'.format(v=__version__))
    with open(os.path.join(config, "cfg/jam_la.cfg"), 'w') as cfg:
        for x in range(len(tracks)):
            cfg.write('echo {x}. {name}: {aliases}'.format(x=x, name=tracks[x].name, aliases=tracks[x].aliases))
    with open(os.path.join(config, "cfg/jam_curtrack.cfg"), 'w') as cfg:
        cfg.write('echo "pyjam :: No song loaded')
    with open(os.path.join(config, "cfg/jam_saycurtrack.cfg"), 'w') as cfg:
        cfg.write('say "pyjam :: No song loaded"')

logger = logging.getLogger('jam')
