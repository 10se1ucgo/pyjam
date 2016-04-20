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
import glob
import json
import logging
from string import whitespace

import psutil
import unidecode
import wx  # Tested w/ wxPhoenix 3.0.2
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from . import ffmpeg
from .about import __version__
from .common import wrap_exceptions, get_path
from .downloader import DownloaderThread, yt_extract, yt_search

try:
    import winreg
except ImportError:
    try:
        import _winreg as winreg
    except ImportError:
        winreg = False

try:
    FileNotFoundError  # This will throw a NameError if the user is using Python 2.
except NameError:
    FileNotFoundError = IOError

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


class Config(object):
    def __init__(self, config_file):
        self.config_file = config_file
        self.steam_path = ''
        self.games = []
        self.load()

    def new(self):
        # this is ugly
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
        except FileNotFoundError:
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
        return [Game(get_path(game.get('audio_dir', os.curdir)), game.get('audio_rate', 11025),
                     get_path(game.get('mod_path', os.curdir)), game.get('name'), game.get('play_key', 'F8'),
                     game.get('relay_key', '='), game.get('use_aliases', True)) for game in self.games]

    def set_games(self, new_games):
        # type: (list) -> None
        # self.games = json.loads(jsonpickle.encode(new_games, unpicklable=False))
        self.games = [dict(game.__dict__) for game in new_games]

    def __repr__(self):
        return "{c}(file={file})".format(c=self.__class__, file=self.config_file)


class Track(object):
    def __init__(self, index, name, aliases, path, bind=None):
        self.index = index
        self.name = unidecode.unidecode(name)
        self.aliases = [unidecode.unidecode(alias) for alias in aliases]
        self.path = path
        self.bind = bind

    def get_aliases(self):
        return str(self.aliases).strip('[]') if self.aliases else "This track has no aliases"

    def __repr__(self):
        return "{c}(index:{index}, name:{name}, aliases:{aliases}, location:{path})".format(
            c=self.__class__, index=self.index, name=self.name, aliases=self.aliases, path=self.path
        )

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
        return "{c}(name:{name}, rate:{rate}, path:{path})".format(
            c=self.__class__, name=self.name, rate=self.audio_rate, path=self.mod_path
        )

    def __str__(self):
        return "Source Engine Game: {name}".format(name=self.name)


class Jam(object):
    def __init__(self, steam_path, game_class, track_list):
        self.steam_path = steam_path
        self.game = game_class
        self.track_list = track_list
        self.user_data = get_path(self.steam_path, 'userdata')
        self.voice = get_path(self.game.mod_path, get_path(os.path.pardir, 'voice_input.wav'))
        self.observer = JamObserver()
        self.event_handler = JamHandler(self, 'jam_cmd.cfg')
        self.total_downloads = 0
        self.previous_bind = None

    def start(self):
        self.observer.schedule(self.event_handler, self.user_data, recursive=True)
        self.observer.start()
        write_configs(self.game.mod_path, self.track_list.GetObjects(), self.game.play_key,
                      self.game.relay_key, self.game.use_aliases)

        with open(get_path(self.game.mod_path, 'cfg/autoexec.cfg'), 'a') as cfg:
            cfg.write('\nexec jam\n')

    def stop(self):
        self.observer.stop()
        self.observer.join()
        logger.info("Stopping...")
        try:
            os.remove(get_path(self.game.mod_path, 'cfg/jam.cfg'))
            os.remove(get_path(self.game.mod_path, 'cfg/jam_la.cfg'))
            os.remove(get_path(self.game.mod_path, 'cfg/jam_curtrack.cfg'))
            os.remove(get_path(self.game.mod_path, 'cfg/jam_saycurtrack.cfg'))
            os.remove(get_path(self.game.mod_path, 'cfg/jam_stdin.cfg'))
            os.remove(get_path(self.game.mod_path, self.voice))
            logger.info("Succesfully removed pyjam config files.")
        except (FileNotFoundError, IOError):
            logger.exception("Could not remove some files:")

        with open(get_path(self.game.mod_path, 'cfg/autoexec.cfg')) as cfg:
            autoexec = cfg.readlines()

        with open(get_path(self.game.mod_path, 'cfg/autoexec.cfg'), 'w') as cfg:
            for line in autoexec:
                if 'exec jam' not in line:
                    cfg.write(line)

        logger.info("Removed 'exec jam' from autoexec.")

    def on_event(self, path):
        logger.info("jam_cmd.cfg change detected, parsing config for song index/command...")
        with open(get_path(path)) as cfg:
            for line in cfg:
                if line[0:4] != 'bind':
                    continue
                line = line.replace('"', '').split()
                if line[1] != self.game.relay_key:
                    continue

                try:
                    bind = line[2:]
                except IndexError:
                    logger.exception("Relay key bind had no argument.")
                    continue

                if bind == self.previous_bind:
                    continue
                self.previous_bind = bind

                if bind[0].isdigit():
                    return self.load_song(int(bind[0]))
                else:
                    return self.read_command(bind)

    def read_command(self, bind):
        try:
            args = bind[1:]
        except IndexError:
            logger.exception("A command was found, but it lacked any arguments.")
            return

        if bind[0].strip(':').lower() == 'search':
            logger.info("Search command found, arguments: {args}".format(args=args))
            self.search(' '.join(args))
        elif bind[0].strip(':').lower() == 'download':
            self.download(''.join(args))
        elif bind[0].strip(':').lower() == 'convert':
            self.convert(os.path.abspath(''.join(args)))

    def load_song(self, index):
        try:
            track = self.track_list.GetObjects()[index]
        except IndexError:
            logger.debug("Failed to load track with index {index}, out of range.".format(index=index))
            return

        shutil.copy(track.path, self.voice)
        logger.info("Song loaded: {track}".format(track=repr(track)))
        with open(get_path(self.game.mod_path, 'cfg/jam_curtrack.cfg'), 'w') as cfg:
            cfg.write('echo "pyjam :: Song :: {name}"\n'.format(name=track.name))
        with open(get_path(self.game.mod_path, 'cfg/jam_saycurtrack.cfg'), 'w') as cfg:
            cfg.write('say "pyjam :: Song :: {name}"\n'.format(name=track.name))

    def search(self, query):
        result = yt_search(query)
        with open(get_path(self.game.mod_path, 'cfg/jam_stdin.cfg'), 'w') as cfg:
            cfg.write('echo "YOUTUBE SEARCH RESULTS"\n')
            cfg.write('echo "----------------------"\n')
            if not result:
                cfg.write('echo "There was an error processing your request. Please try again later"\n')
                return
            for item in result:
                out = unidecode.unidecode("{id}: {title} - {desc}".format(
                    title=item['title'], id=item['id'], desc=item['desc']
                ))
                cfg.write('echo "{out}"\n'.format(out=out))

    def download(self, urls):
        if self.total_downloads:
            # A download is already in progress.
            return
        with open(get_path(self.game.mod_path, 'cfg/jam_stdin.cfg'), 'w') as cfg:
            cfg.write('echo "PYJAM DOWNLOADER"\n')
            cfg.write('echo "------------------"\n')
            cfg.write('echo "Extracting URL info, starting download..."\n')
        logger.info("Recieved urls: {urls}".format(urls=urls))
        urls = yt_extract(urls.split(','))
        if not urls:
            with open(get_path(self.game.mod_path, 'cfg/jam_stdin.cfg'), 'w') as cfg:
                cfg.write('echo "PYJAM DOWNLOADER"\n')
                cfg.write('echo "------------------"\n')
                cfg.write('echo "Invalid/unsupported URL(s)!"\n')
            return
        self.total_downloads = len(urls)
        downloader = DownloaderThread(self, urls, os.path.abspath('_ingame_dl'))
        downloader.start()
        logger.info(urls)

    def download_update(self, message):
        progress = "{songs} out of {total}".format(songs=message // 100, total=self.total_downloads)
        with open(get_path(self.game.mod_path, 'cfg/jam_stdin.cfg'), 'w') as cfg:
            cfg.write('echo "PYJAM DOWNLOAD PROGRESS"\n')
            cfg.write('echo "-------------------------"\n')
            cfg.write('echo "{progress} downloaded so far"\n'.format(progress=progress))

    def download_complete(self, errors):
        with open(get_path(self.game.mod_path, 'cfg/jam_stdin.cfg'), 'w') as cfg:
            cfg.write('echo "PYJAM DOWNLOAD PROGRESS"\n')
            cfg.write('echo "-------------------------"\n')
            cfg.write('echo "Download complete! Downloaded to {folder}"\n'.format(folder=os.path.abspath('_ingame_dl')))
            cfg.write('echo "Starting conversion..."\n')
        self.convert(os.path.abspath('_ingame_dl'))

    def convert(self, folder):
        with open(get_path(self.game.mod_path, 'cfg/jam_stdin.cfg'), 'w') as cfg:
            if ffmpeg.find() is None:
                cfg.write('echo "PYJAM CONVERTER"\n')
                cfg.write('echo "---------------"\n')
                cfg.write('echo "FFmpeg could not be found on the system"\n')
                cfg.write('echo "The audio converter will not work without it."\n')
                cfg.write('echo "Please check your configuration and try again"\n')
                return
            else:
                cfg.write('echo "PYJAM CONVERTER"\n')
                cfg.write('echo "---------------"\n')
                cfg.write('echo "Beginning conversion..."\n')

        files = glob.glob(get_path(folder, '*.*'))
        converter = ffmpeg.FFmpegConvertThread(self, self.game.audio_dir, self.game.audio_rate, 85, files)
        converter.start()

    def convert_update(self, message):
        progress = "{songs} out of {total}".format(songs=message // 2, total=self.total_downloads)
        with open(get_path(self.game.mod_path, 'cfg/jam_stdin.cfg'), 'w') as cfg:
            cfg.write('echo "PYJAM CONVERSION PROGRESS"\n')
            cfg.write('echo "-------------------------"\n')
            cfg.write('echo "{progress} converted so far"\n'.format(progress=progress))

    def convert_complete(self, errors):
        self.stop()
        tracks = get_tracks(self.game.audio_dir)
        self.track_list.SetObjects(tracks)
        self.observer = JamObserver()  # Create new Observer object. Threads cannot be restarted.
        self.start()
        with open(get_path(self.game.mod_path, 'cfg/jam_stdin.cfg'), 'w') as cfg:
            cfg.write('echo "PYJAM CONVERSION PROGRESS"\n')
            cfg.write('echo "-------------------------"\n')
            cfg.write('echo "Conversion complete!"\n'.format(folder=os.path.abspath('_ingame_dl')))
            if errors:
                cfg.write('echo "Songs converted with {errors} error(s)"\n'.format(errors=len(errors)))
                cfg.write('echo "Error converting these files\n{errors}"\n'.format(errors=errors))
            else:
                cfg.write('echo "Songs converted without any errors"\n')
            cfg.write('echo "pyjam will now reload..."\n')
            cfg.write('exec jam\n')
        self.total_downloads = 0

class JamHandler(FileSystemEventHandler):
    def __init__(self, calling_class, file_name):
        super(JamHandler, self).__init__()
        self.calling = calling_class
        self.file_name = file_name

    def on_modified(self, event):
        if os.path.basename(event.src_path) == self.file_name:
            self.calling.on_event(event.src_path)

    def on_moved(self, event):
        # This isn't really needed, but it's useful for things that use something like atomic saving.
        if os.path.basename(event.src_path) == self.file_name:
            self.calling.on_event(event.src_path)
        elif os.path.basename(event.dest_path) == self.file_name:
            self.calling.on_event(event.dest_path)


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
    with open(get_path(path, 'cfg/jam.cfg'), 'w') as cfg:
        cfg.write('bind {play_key} jam_play\n'.format(play_key=play_key))
        cfg.write('alias jam_play jam_on\n')
        cfg.write('alias jam_on "voice_inputfromfile 1; voice_loopback 1; +voicerecord; alias jam_play jam_off"\n')
        cfg.write('alias jam_off "voice_inputfromfile 0; voice_loopback 0; -voicerecord; alias jam_play jam_on"\n')
        cfg.write('alias jam_cmd "host_writeconfig jam_cmd"\n')
        cfg.write('alias jam_listaudio "exec jam_la"\n')
        cfg.write('alias jam_la "exec jam_la"\n')
        cfg.write('alias la "exec jam_la"\n')
        cfg.write('alias jam_saytrack "exec jam_saycurtrack"\n')
        cfg.write('alias jam_say "exec jam_saycurtrack"\n')
        cfg.write('alias jam_echotrack "exec jam_curtrack"\n')
        cfg.write('alias jam_track "exec jam_curtrack"\n')
        cfg.write('alias jam_stdin "exec jam_stdin"\n')
        cfg.write('alias stdin "exec jam_stdin"\n')
        cfg.write('alias jam_help "exec jam_help"\n')
        cfg.write('alias jam "exec jam_help"\n')
        for x, track in enumerate(tracks):
            cfg.write('alias {x} "bind {relay} {x}; echo Loaded: {name}; jam_cmd"\n'.format(
                x=x, relay=relay_key, name=track.name
            ))
            if use_aliases:
                for alias in track.aliases:
                    cfg.write('alias {alias} "bind {relay} {x}; echo Loaded: {name}; jam_cmd"\n'.format(
                        alias=alias, relay=relay_key, x=x, name=track.name
                    ))
            if track.bind:
                cfg.write('bind {bind} "bind {relay} {x}; echo Loaded: {name}; jam_cmd"\n'.format(
                    bind=track.bind, relay=relay_key, x=x, name=track.name
                ))
        cfg.write('voice_enable 1; voice_modenable 1\n')
        cfg.write('voice_forcemicrecord 0\n')
        cfg.write('voice_fadeouttime 0.0\n')
        cfg.write('con_enable 1; hideconsole; showconsole\n')
        cfg.write('echo "pyjam v{v} loaded.'.format(v=__version__))
        cfg.write('jam_help\n')
        logger.info("Wrote jam.cfg to {path}".format(path=cfg.name))
    with open(get_path(path, 'cfg/jam_la.cfg'), 'w') as cfg:
        cfg.write('exec "jam_curtrack"\n')
        for x, track in enumerate(tracks):
            cfg.write('echo "{x}. {name}; Aliases: {aliases}"\n'.format(x=x, name=track.name, aliases=track.aliases))
        logger.info("Wrote jam_la.cfg to {path}".format(path=cfg.name))
    with open(get_path(path, 'cfg/jam_curtrack.cfg'), 'w') as cfg:
        cfg.write('echo "pyjam :: No song loaded"\n')
        logger.info("Wrote jam_curtrack.cfg to {path}".format(path=cfg.name))
    with open(get_path(path, 'cfg/jam_saycurtrack.cfg'), 'w') as cfg:
        cfg.write('say "pyjam :: No song loaded"\n')
        logger.info("Wrote jam_saycurtrack.cfg to {path}".format(path=cfg.name))
    with open(get_path(path, 'cfg/jam_stdin.cfg'), 'w') as cfg:
        cfg.write('echo "Nothing to be reported at this time."\n')
        logger.info("Wrote jam_stdin.cfg to {path}".format(path=cfg.name))
    with open(get_path(path, 'cfg/jam_help.cfg'), 'w') as cfg:
        cfg.write('echo "pyjam song playing guide:"\n')
        cfg.write('echo "1. Use the \'la\' or \'jam_la\' commands for a list of your audio tracks"\n')
        cfg.write('echo "2. Type the number of the track OR one of its aliases and press enter"\n')
        cfg.write('echo "3. Press the \'{key}\' key to start or stop the music"\n'.format(key=play_key))
        cfg.write('echo\n')
        cfg.write('echo "pyjam common commands:"\n')
        cfg.write('echo "la, jam_la, jam_listaudio: list all tracks + their index and aliases"\n')
        cfg.write('echo "jam_say, jam_saytrack: say the name of the song in all chat."\n')
        cfg.write('echo "jam_echotrack, jam_track: echo the name of the song in console."\n')
        cfg.write('echo "jam_help: view this help guide."\n')
        cfg.write('echo\n')
        cfg.write('echo "pyjam in-game downloader + converter guide:"\n')
        cfg.write('echo "Recommended only for advanced users. This may be difficult for some people."\n')
        cfg.write("echo \"1. Run the command `bind {relay} ''search: SEARCH TERM HERE''`.\"\n".format(relay=relay_key))
        cfg.write('echo "2. Now run the command \'jam_cmd\'. pyjam will then run the command."\n')
        cfg.write('echo "3. To get the results, run the commands \'stdin\' or \'jam_stdin\'."\n')
        cfg.write("echo \"4. Then, run the command `bind {relay} ''download: IDs HERE''`.\"\n".format(relay=relay_key))
        cfg.write('echo "The IDs of the videos should be separated with commas, like so: Dkm8Hteeh6M,MqgtVpD328o"\n')
        cfg.write('echo "5. Run the command \'jam_cmd\' again to get pyjam to read your command."\n')
        cfg.write('echo "6. To get periodic updates, run the commands \'stdin\' or \'jam_stdin\'."\n')
        cfg.write('echo "7. pyjam will reload after you run \'stdin\' or \'jam_stdin\' once conversion is complete."\n')
        cfg.write('echo "NOTE: \'\' IS SUPPOSED TO REPRESENT A DOUBLE QUOTE!"\n')
        cfg.write('echo\n')
        cfg.write('echo "pyjam advanced commands:"\n')
        cfg.write('echo "stdin, jam_stdin: get output from search or downloader/converter."\n')
        cfg.write('echo "jam_cmd: run a command (after setting the command with `bind`)"\n')
        cfg.write("echo \"bind {relay} ''command: arguments'': set a command\"\n".format(relay=relay_key))
        logger.info("Wrote jam_help.cfg to {path}".format(path=cfg.name))



def get_tracks(audio_path):
    # type: (str) -> list
    black_list = [
        'buy', 'cheer', 'compliment', 'coverme', 'enemydown', 'enemyspot', 'fallback', 'followme', 'getout',
        'go', 'holdpos', 'inposition', 'negative', 'regroup', 'report', 'reportingin', 'roger', 'sectorclear',
        'sticktog', 'takepoint', 'takingfire', 'thanks', 'drop', 'sm', 'jam_play', 'jam_on', 'jam_off',
        'jam_cmd', 'jam_listaudio', 'jam_la', 'la', 'jam_saytrack', 'jam_say', 'jam_echotrack',  'jam_track',
        'jam_stdin', 'stdin', 'jam_help', 'jam', 'kill', 'explode'
    ]

    current_tracks = []
    bound_keys = []

    # Format for custom track data.
    # {
    #     "song1": {"aliases": ["alias1", "alias2", "etc."], "bind": "DOWNARROW"},
    #     "song2": {"aliases": ["alias3", "alias4", "etc."], "bind": "KP_INS"}
    # }
    logger.info("Generating track list with path {path}".format(path=audio_path))
    try:
        with open(get_path(audio_path, 'track_data.json')) as f:
            track_data = json.load(f)
    except FileNotFoundError:
        track_data = {}
    except ValueError:
        track_data = {}
        logger.exception("Invalid track data for {path}".format(path=get_path(audio_path, 'track_data.json')))

    index = 0
    for track in glob.glob(get_path(audio_path, '*.wav')):
        bind = None
        name = unidecode.unidecode(os.path.splitext(os.path.basename(track))[0])  # Name of file minus path/extension
        if name in track_data and 'aliases' in track_data[name]:
            custom_aliases = track_data[name].get('aliases')
            if custom_aliases:
                aliases = [filter_alias(x) for x in custom_aliases if x not in black_list and x not in whitespace]
        else:
            aliases = [x for x in filter_alias(name).split() if x not in black_list and x not in whitespace]
        if name in track_data and 'bind' in track_data[name]:
            custom_bind = track_data[name].get('bind')
            if custom_bind and bindable(custom_bind) and custom_bind not in bound_keys:
                bind = custom_bind
                bound_keys.extend(custom_bind)
        black_list.extend(aliases)
        current_tracks.append(Track(index, name, aliases, track, bind))
        index += 1

    if current_tracks:
        logger.debug("Generated track list: {tracks}".format(tracks='\n'.join([repr(x) for x in current_tracks])))
    else:
        logger.debug("No tracks found.")
    return current_tracks


def filter_alias(alias):
    # type: (str) -> str
    # No non-alphanumerical characters, thanks. Though, 'alias' does support quite a few of them. Too lazy to filter.
    filtered = []
    for char in alias:
        if char.isalpha() or char.isspace():
            filtered.append(char.lower())
        elif char != "'" and char != '"':
            filtered.append(' ')
    return ''.join(filtered).strip()


def get_steam_path():
    # type: () -> str
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


def bindable(key):
    # type: (str) -> bool or str
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
