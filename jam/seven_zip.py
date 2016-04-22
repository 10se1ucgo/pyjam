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
import shlex

try:
    from shutil import which
except ImportError:
    from shutilwhich import which


def find():
    """Get the path to 7zip.
    Returns:
        None or str: The path to 7zip. None if not found.
    """
    return which('7z.exe') or which('7za.exe') or which('bin/7za.exe')


def extract_single(archive, file, dest):
    """Extract a file from an archive using 7zip.
    Args:
        archive (str): The path to the archive to extract.
        file (str): The name of the file to be extracted from the archive.
        dest (str): The destination to the file.

    Returns:
        None
    """
    cmd = "{bin} e -y {archive} -o{dest} {file} -r".format(bin=find(), archive=archive, dest=dest, file=file)
    subprocess.call(shlex.split(cmd), stdin=subprocess.PIPE, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
