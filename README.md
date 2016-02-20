# pyjam
![header image](http://i.imgur.com/ic7toeV.png)

pyjam is (or will be) an open source, cross-platform audio player for Source and GoldSrc engine based games, written in 
Python

It doesn't work yet, by the way!

# REQUIREMENTS
* Tested on Python 2.7 and 3.5
* wxPython Phoenix (Tested with 3.0.2)
* ObjectListView
* watchdog
* shutilwhich (Only for <Python 3.3)

# TODO
- [x] Base UI stuff
  - [x] Track list (ObjectListView)
  - [x] Switch between games
  - [x] Allow for custom aliases
    - [x] GUI for implementing custom ~~aliases~~ track data
    - right click on track>context menu>set [track data]
    - [x] Format for custom ~~aliases~~ track data
    - ```{"song1": {"aliases": ["alias1", "alias2", "etc"], bind="KP_DEL"}}``` etc.
      - [x] Read format
      - [x] Write format
        - [x] Write custom aliases
        - [x] Write custom bind
- [ ] Get the actual playing audio part of the program working
  - [x] Write the initial configs
  - [ ] Watch 'jam_cmd.cfg' for updates and poll for requested song
  - [ ] Copy requested song to root dir
- [ ] Implement an audio converter
  - [x] FFmpeg downloader
  - [x] FFmpeg convert command
  - [ ] GUI for accessing converter
- [x] Implement a config editor
  - [x] Base reading and writing
  - [x] Support all fields
  - [x] Make it pretty.
- [ ] Implement audio downloading?
  - [ ] youtube-dl
  - [ ] GUI for accessing downloader


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
