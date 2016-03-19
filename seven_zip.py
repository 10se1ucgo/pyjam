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

# An interface to 7zip
import subprocess

try:
    from shutil import which
except ImportError:
    from shutilwhich import which


def find():
    return which('7z.exe') or which('7za.exe') or which('bin/7za.exe')


def extract_single(archive, file, dest):
    cmd = "{bin} e -y {archive} -o{dest} {file} -r".format(bin=find(), archive=archive, dest=dest, file=file)
    subprocess.call(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
