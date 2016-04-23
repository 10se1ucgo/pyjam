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

import unidecode
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from . import ffmpeg
from .about import __version__
from .common import *
from .downloader import DownloaderThread, yt_extract, yt_search

try:
    FileNotFoundError  # This will throw a NameError if the user is using Python 2.
except NameError:
    FileNotFoundError = IOError

logger = logging.getLogger(__name__)

class Jam(object):
    """
    The actual worker that does the playing of music.
    """
    def __init__(self, steam_path, game_class, track_list):
        """
        Args:
            steam_path (str): Path to Steam.
            game_class (Game): The game class for the running game.
            track_list (ObjectListView[Track]): The ObjectListView that contains all of the Tracks.
        """
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
        """Start the observer and event handler + write the configs.
        Returns:
            None
        """
        self.observer.schedule(self.event_handler, self.user_data, recursive=True)
        self.observer.start()
        write_configs(self.game.mod_path, self.track_list.GetObjects(), self.game.play_key,
                      self.game.relay_key, self.game.use_aliases)

        with open(get_path(self.game.mod_path, 'cfg/autoexec.cfg'), 'a') as cfg:
            cfg.write('\nexec jam\n')

    def stop(self):
        """Stop the observer and remove all configs.
        Returns:
            None
        """
        self.observer.stop()
        self.observer.join()
        logger.info("Stopping...")
        try:
            os.remove(get_path(self.game.mod_path, 'cfg/jam.cfg'))
            os.remove(get_path(self.game.mod_path, 'cfg/jam_la.cfg'))
            os.remove(get_path(self.game.mod_path, 'cfg/jam_curtrack.cfg'))
            os.remove(get_path(self.game.mod_path, 'cfg/jam_saycurtrack.cfg'))
            os.remove(get_path(self.game.mod_path, 'cfg/jam_stdin.cfg'))
            os.remove(get_path(self.game.mod_path, 'cfg/jam_help.cfg'))
            os.remove(get_path(self.game.mod_path, self.voice))
            logger.info("Succesfully removed pyjam config files.")
        except (FileNotFoundError, OSError):
            logger.exception("Could not remove some files:")

        with open(get_path(self.game.mod_path, 'cfg/autoexec.cfg')) as cfg:
            autoexec = cfg.readlines()

        with open(get_path(self.game.mod_path, 'cfg/autoexec.cfg'), 'w') as cfg:
            for line in autoexec:
                if 'exec jam' not in line:
                    cfg.write(line)

        logger.info("Removed 'exec jam' from autoexec.")

    def on_event(self, path):
        """
        Args:
            path (str): The path to the event.

        Returns:
            None
        """
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
        """Read the relay key for a command to run.

        Args:
            bind (list[str]): The command the bind was set to.

        Returns:
            None
        """
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
        """Load a song with the specified index.

        Args:
            index (int): The index of the song to load.

        Returns:
            None
        """
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
        """Perform a YouTube search with a query (in-game).

        Args:
            query (str): The query to search for.

        Returns:
            None
        """
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
        """Download videos from a list of URLs

        Args:
            urls (str): The comma seperated list of URLs to download

        Returns:
            None
        """
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
        """Convert all files in a folder.
        Args:
            folder (str): Path to the folder

        Returns:
            None
        """
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
    """Write the initial configs for running pyjam within the game.
    Args:
        path (str): The mod path for the Source Engine game.
        tracks (list[Track]): The list of valid tracks.
        play_key (str): The key used to start/stop music.
        relay_key (str): The key used to interact with the game.
        use_aliases (bool): Whether or not to use aliases

    Returns:
        None
    """
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
        cfg.write('echo "pyjam v{v} loaded.\n'.format(v=__version__))
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
    """Get all track files from a folder and generate aliases/binds (as well as read custom track data).
    Args:
        audio_path (str): The path to where all the .wavs are stored.

    Returns:
        list[Track]: A list of Track objects for all of the tracks found..
    """
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
    """Filter an alias, removing all non-alphabetic characters or spaces.
    Args:
        alias (str): The alias to filter.

    Returns:
        str: The filtered alias.
    """
    filtered = []
    for char in alias:
        if char.isalpha() or char.isspace():
            filtered.append(char.lower())
        elif char != "'" and char != '"':
            filtered.append(' ')
    return ''.join(filtered).strip()
