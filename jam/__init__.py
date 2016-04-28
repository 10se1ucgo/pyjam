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
import logging

from . import about, common, ffmpeg, seven_zip, jam
from .jam import *

logger = logging.getLogger(__name__)

try:
    from . import downloader
except ImportError:
    downloader = None
    logger.exception("Error importing downloader, youtube-dl is likely not installed.")

try:
    from . import waveform
except ImportError:
    waveform = None
    logger.exception("Error importing waveform viewer, numpy is likely not installed.")


__all__ = ['about', 'common', 'downloader', 'ffmpeg', 'seven_zip', 'jam', 'waveform']
