# pyjam
![header image](http://i.imgur.com/ic7toeV.png)

pyjam is an open source, cross-platform audio player for Source and GoldSrc engine based games, written in Python

# FEATURES
* Cross-platform -- Supports (in theory) Windows, GNU/Linux and OSX!
* Open source -- Licensed under the GNU General Public License, v3.
* Native GUI -- wxMSW on Windows, wxGTK on GNU/Linux, wxMAC on OSX
* Easy to use settings dialog
* Track aliases -- select tracks by name instead of index!
  * Set custom track aliases (generated from track name by default)
* Custom binds -- select tracks with a keybind
* ***Built-in audio converter*** -- uses [`FFmpeg`](https://ffmpeg.org/)
* ***Built-in audio downloader!*** -- [`youtube-dl`](https://github.com/rg3/youtube-dl) (supports MANY (hundreds) websites, [full list here](https://rg3.github.io/youtube-dl/supportedsites.html))

# USAGE
1. Download the latest version from the [`Releases`](https://github.com/10se1ucgo/pyjam/releases) tab
2. Launch `pyjam` and go to `File>Settings`
   1. Browse for your Steam path into the `Path to Steam` option. 
      - The program will try to guess where Steam is beforehand and may be filled out
   2. Enter the name into the `Profile/game name` option. 
      - It's simply used as a profile name and the name does not matter.
   3. Browse for the folder of the game into the `Game path` option. 
      - ***BE SURE TO INCLUDE THE MOD FOLDER IN THERE AS WELL***, e.g., `/Steam/steamapps/common/Team Fortress 2/tf2/`
   4. Browse for the path of the audio folder you want for this game into the `Audio path` option.
   5. Enter the audio rate of that game into the `Audio rate` option.
      - Normally, this is 11025.
      - However, CS:GO uses the CELT audio codec, so use 22050 if creating a CS:GO profile. (Higher quality!)
   6. Select a key for the `Relay key` option.
      - For quick selection, click on the drop down arrow and press a key on your keyboard to select a key
      - The default option usually works just fine (unless you have a bind that uses `=`)
   7. Select a key for the `Play key` option.
      - For quick selection, click on the drop down arrow and press a key on your keyboard to select a key
   8. Select whether or not you want to use aliases.
      - Aliases allow for you to select songs in console using words instead of an index number
      - Disable if you think there might be conflicts.
   9. Press `Save game`, and then exit the dialog.
   9. Congratulations! Your first game has been set up.
3. Put in your audio!
   1. If you already have audio converted and ready to go, drop them into the audio folder you designated for the game
   2. Otherwise, if you have audio downloaded, but not converted, use the `Audio converter` to convert them to the proper format
   3. If you don't have an audio at all, use the `Audio downloader` and download from your favorite streaming sites!
   4. Lastly, hit the `Refresh tracks` button in order to make sure that pyjam has detected all of your songs.
4. Ready? Press `Start`, and load up your game.
   - If pyjam is not immediately loaded when you start the game, type `exec jam.cfg` in console to fix that.
5. Run `jam_help` in console to get help on usage.
6. Have fun!


# REQUIREMENTS
***This is only for those who plan on running the Python script. Most users can simply just download a pre-frozen executable from the [`Releases`](https://github.com/10se1ucgo/pyjam/releases) tab***
* Tested on `CPython 3.5`. 2.7+ should work.
* [wxPython Phoenix](https://github.com/wxWidgets/Phoenix) - GUI
    * Compiling it yourself can be a bit ugly, [pre-built wheels here](http://wxpython.org/Phoenix/snapshot-builds/)
* [ObjectListView](https://pypi.python.org/pypi/ObjectListView) - wx.ListCtrl wrapper (much easier to use)
* [watchdog](https://pypi.python.org/pypi/watchdog) - Cross-platform file system monitoring
* [**OPTIONAL**: youtube-dl](https://github.com/rg3/youtube-dl/) - Audio/Video downloader (supports many websites, not just 
YouTube)
* [**OPTIONAL**: psutil](https://github.com/giampaolo/psutil) - Process/system utilities  (Used for detecting Steam 
path)
* [requests](http://docs.python-requests.org/en/master/) - HTTP library used for downloading FFmpeg
* [unidecode](https://pypi.python.org/pypi/Unidecode) - Filter out pesky unicode characters that cause problems :(

## Python <3.3
* [shutilwhich](https://pypi.python.org/pypi/shutilwhich) - Backport of shutil.which()

# TODO
- [ ] [EASY] Drop 7-zip module on Windows. https://ffmpeg.zeranoe.com/builds now offers .zip builds.


# KNOWN ISSUES
None!



# LICENSE
```
Copyright (C) 10se1ucgo 2016

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
```

# THANKS
Thanks to Dx724 for the wonderful icon.
