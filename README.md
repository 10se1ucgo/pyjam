# pyjam
![header image](http://i.imgur.com/ic7toeV.png)

An opensource, cross-platform audio player for Source and GoldSrc engine based games, written in Python

It doesn't work yet, by the way!

# TODO
- [x] Base UI stuff
  - [x] Track list (ObjectListView)
  - [x] Switch between games
  - [x] Allow for custom aliases
    - [x] GUI for implementing custom aliases 
    - right click on track>context menu>set aliases
    - [x] Format for custom aliases 
    - ```{"song1": ["alias1", "alias2", "etc."], "song2": ["alias1", "alias2", "etc"]}```
      - [x] Read format
      - [x] Write format
- [ ] Get the actual playing audio part of the program working
  - [x] Write the initial configs
  - [ ] Watch 'jam_cmd.cfg' for updates and poll for requested song
  - [ ] Copy requested song to root dir
- [ ] Implement an audio converter
  - [x] FFmpeg downloader
  - [x] FFmpeg convert command
  - [ ] GUI for accessing converter
- [ ] Implement a config editor
  - [x] Base reading and writing
  - [ ] Support all fields
  - [ ] Make it pretty.
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
