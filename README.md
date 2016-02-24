pyjam
--
![header image](http://i.imgur.com/ic7toeV.png)

pyjam is an open source, cross-platform audio player for Source and GoldSrc engine based games, written in Python

~~It doesn't work yet, by the way!~~  
As of 2/21/16, it works!

REQUIREMENTS
--
* Tested on CPython 3.5. 2.7+ should work.
* [wxPython Phoenix](https://github.com/wxWidgets/Phoenix) - GUI
    * Compiling for Python 3.5 is a bit broken. [Patch + a wheel for CPython 3.5 x64 can be found here](https://gist.github.com/10se1ucgo/65ee42ad2fdc59091c6e)
* [ObjectListView](https://pypi.python.org/pypi/ObjectListView) - wx.ListCtrl wrapper (much easier to use)
* [watchdog](https://pypi.python.org/pypi/watchdog) - Cross-platform file system monitoring

Backwards compatibility
--
* [shutilwhich](https://pypi.python.org/pypi/shutilwhich) - Backport of shutil.which() for Python <3.3

TODO
--
- [x] Base UI stuff
    - [x] Track list (ObjectListView)
    - [x] Switch between games
    - [x] Allow for custom aliases
        - [x] GUI for implementing custom ~~aliases~~ track data
        - right click on track>context menu>set [track data]
        - [x] Format for custom ~~aliases~~ track data
        - ```{"song1": {"aliases": ["alias1", "alias2", "etc"], bind: "KP_DEL"}}``` etc.
            - [x] Read format
            - [x] Write format
- [x] Get the actual playing audio part of the program working
      - [x] Write the initial configs
      - [x] Watch 'jam_cmd.cfg' for updates and poll for requested song
      - [x] Copy requested song to root dir
- [x] Implement a config editor
      - [x] Base reading and writing
      - [x] Support all fields
      - [x] Make it pretty.
- [ ] Implement an audio converter
      - [x] FFmpeg downloader
      - [x] FFmpeg convert command
      - [ ] GUI for accessing converter
- [ ] Implement audio downloading?
      - [ ] youtube-dl
      - [ ] GUI for accessing downloader


LICENSE
--
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
