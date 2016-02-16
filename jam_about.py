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

# jam.py is cluttered enough as is.
import wx.adv

__version__ = "1.0"


def about_info(parent):
    license_text = """
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
    along with this program.  If not, see <http://www.gnu.org/licenses/>."""

    about_pg = wx.adv.AboutDialogInfo()
    about_pg.SetName("pyjam")
    about_pg.SetVersion("v{v}".format(v=__version__))
    about_pg.SetCopyright("Copyright (C) 10se1ucgo 2016")
    about_pg.SetDescription("An opensource, cross-platform audio player for Source and GoldSrc engine based games.")
    about_pg.SetWebSite("https://github.com/10se1ucgo/pyjam", "GitHub repo")
    about_pg.AddDeveloper("10se1ucgo")
    about_pg.SetLicense(license_text)
    wx.adv.AboutBox(about_pg, parent)
