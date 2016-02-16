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
from subprocess import call

if sys.version_info[0:2] < (3, 3):
    from shutilwhich import which
else:
    from shutil import which


def find():
    if sys.platform == "win32":
        return which('7z.exe') or which('7za.exe') or which('bin/7za.exe')
    else:
        # I don't know if this works.
        return which('7z') or which('7za') or which('bin/7za')


def extract_single(archive, file, overwrite=True, recurse=True):
    cmd = "{bin} e".format(bin=find())
    if overwrite: cmd += " -y"
    cmd += " {archive} {file}".format(archive=archive, file=file)
    if recurse: cmd += "  -r"
    call(cmd)
