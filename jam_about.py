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
import webbrowser
from distutils.version import StrictVersion

import requests
import wx
import wx.lib.scrolledpanel as sp
import wx.adv

__version__ = "1.2.8"


def about_dialog(parent):
    license_text = """
    Copyright (C) 10se1ucgo 2016

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program. If not, see <http://www.gnu.org/licenses/>."""

    about_info = wx.adv.AboutDialogInfo()
    about_info.SetName("pyjam")
    about_info.SetVersion("v{v}".format(v=__version__))
    about_info.SetCopyright("Copyright (C) 10se1ucgo 2016")
    about_info.SetDescription("An open source, cross-platform audio player for Source and GoldSrc engine based games.")
    about_info.SetWebSite("https://github.com/10se1ucgo/pyjam", "GitHub repository")
    about_info.AddDeveloper("10se1ucgo")
    about_info.AddDeveloper("Dx724")
    about_info.AddArtist("Dx724 - Icon")
    about_info.SetLicense(license_text)
    wx.adv.AboutBox(about_info, parent)


class Licenses(wx.Dialog):
    def __init__(self, parent):
        super(Licenses, self).__init__(parent, title="Licenses", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
                                       size=(600, 400))

        self.scrolled_panel = sp.ScrolledPanel(self)

        mono_font = wx.Font()
        mono_font.SetFamily(wx.FONTFAMILY_TELETYPE)

        info = wx.StaticText(self.scrolled_panel, label=("pyjam uses a number of open source software. The following "
                                                         "are the licenses for these software."))

        wxw = wx.StaticText(self.scrolled_panel, label=("pyjam uses wxWidgets and wxPython. Their licenses are below.\n"
                                                        "More info at https://www.wxwidgets.org/about/\n"
                                                        "pyjam uses ObjectListView. License is also below."))
        wxw_license = """
                  wxWindows Library Licence, Version 3.1
                  ======================================

    Copyright (c) 1998-2005 Julian Smart, Robert Roebling et al

    Everyone is permitted to copy and distribute verbatim copies
    of this licence document, but changing it is not allowed.

                         WXWINDOWS LIBRARY LICENCE
       TERMS AND CONDITIONS FOR COPYING, DISTRIBUTION AND MODIFICATION

    This library is free software; you can redistribute it and/or modify it
    under the terms of the GNU Library General Public Licence as published by
    the Free Software Foundation; either version 2 of the Licence, or (at your
    option) any later version.

    This library is distributed in the hope that it will be useful, but WITHOUT
    ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
    FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Library General Public
    Licence for more details.

    You should have received a copy of the GNU Library General Public Licence
    along with this software, usually in a file named COPYING.LIB.  If not,
    write to the Free Software Foundation, Inc., 51 Franklin Street, Fifth
    Floor, Boston, MA 02110-1301 USA.

    EXCEPTION NOTICE

    1. As a special exception, the copyright holders of this library give
    permission for additional uses of the text contained in this release of the
    library as licenced under the wxWindows Library Licence, applying either
    version 3.1 of the Licence, or (at your option) any later version of the
    Licence as published by the copyright holders of version 3.1 of the Licence
    document.

    2. The exception is that you may use, copy, link, modify and distribute
    under your own terms, binary object code versions of works based on the
    Library.

    3. If you copy code from files distributed under the terms of the GNU
    General Public Licence or the GNU Library General Public Licence into a
    copy of this library, as this licence permits, the exception does not apply
    to the code that you add in this way.  To avoid misleading anyone as to the
    status of such modified files, you must delete this exception notice from
    such code and/or adjust the licensing conditions notice accordingly.

    4. If you write modifications of your own for this library, it is your
    choice whether to permit this exception to apply to your modifications.  If
    you do not wish that, you must delete the exception notice from such code
    and/or adjust the licensing conditions notice accordingly."""
        wxw_text = wx.StaticText(self.scrolled_panel, label=wxw_license)
        wxw_text.SetFont(mono_font)

        seven = wx.StaticText(self.scrolled_panel, label=("pyjam bundles 7-zip Extra in binary form. "
                                                          "Its license is below.\n"
                                                          "Downloads and source: http://www.7zip.org"))
        seven_license = """
    7-Zip Extra
    ~~~~~~~~~~~
    License for use and distribution
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Copyright (C) 1999-2015 Igor Pavlov.

    7-Zip Extra files are under the GNU LGPL license.


    Notes:
    You can use 7-Zip Extra on any computer, including a computer in a commercial
    organization. You don't need to register or pay for 7-Zip.


    GNU LGPL information
    --------------------

    This library is free software; you can redistribute it and/or
    modify it under the terms of the GNU Lesser General Public
    License as published by the Free Software Foundation; either
    version 2.1 of the License, or (at your option) any later version.

    This library is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
    Lesser General Public License for more details.

    You can receive a copy of the GNU Lesser General Public License from
    http://www.gnu.org/"""
        seven_text = wx.StaticText(self.scrolled_panel, label=seven_license)
        seven_text.SetFont(mono_font)

        ffmpeg = wx.StaticText(self.scrolled_panel, label=("pyjam uses FFmpeg in binary form. A note and "
                                                           "license info is below."))
        ffmpeg_info = """
    NOTE
    ----

    FFmpeg <https://ffmpeg.org> is downloaded upon the user's request (not bundled due to size).
    You can download binaries, including source and instructions, from https://ffmpeg.zeranoe.com/
    Builds from https://ffmpeg.zeranoe.com/ are licensed under the GNU GPL 3.0

    GNU GPL information
    -------------------

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program. If not, see <http://www.gnu.org/licenses/>."""
        ffmpeg_text = wx.StaticText(self.scrolled_panel, label=ffmpeg_info)
        ffmpeg_text.SetFont(mono_font)

        watchdog = wx.StaticText(self.scrolled_panel, label="pyjam uses watchdog. Copying notice below.")
        watchdog_notice = """
    Copyright 2011 Yesudeep Mangalapilly <yesudeep@gmail.com>
    Copyright 2012 Google, Inc.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License."""
        watchdog_text = wx.StaticText(self.scrolled_panel, label=watchdog_notice)
        watchdog_text.SetFont(mono_font)

        psutil = wx.StaticText(self.scrolled_panel, label="pyjam uses psutil. License below.")
        psutil_license = """
    psutil is distributed under BSD license reproduced below.

    Copyright (c) 2009, Jay Loden, Dave Daeschler, Giampaolo Rodola'
    All rights reserved.

    Redistribution and use in source and binary forms, with or without modification,
    are permitted provided that the following conditions are met:

     * Redistributions of source code must retain the above copyright notice, this
       list of conditions and the following disclaimer.
     * Redistributions in binary form must reproduce the above copyright notice,
       this list of conditions and the following disclaimer in the documentation
       and/or other materials provided with the distribution.
     * Neither the name of the psutil authors nor the names of its contributors
       may be used to endorse or promote products derived from this software without
       specific prior written permission.

    THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
    ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
    WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
    DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
    ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
    (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
    LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
    ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
    (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
    SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE."""
        psutil_text = wx.StaticText(self.scrolled_panel, label=psutil_license)
        psutil_text.SetFont(mono_font)

        requests_info = wx.StaticText(self.scrolled_panel, label="pyjam uses requests. License below.")
        requests_license = """
    Copyright 2016 Kenneth Reitz

       Licensed under the Apache License, Version 2.0 (the "License");
       you may not use this file except in compliance with the License.
       You may obtain a copy of the License at

           http://www.apache.org/licenses/LICENSE-2.0

       Unless required by applicable law or agreed to in writing, software
       distributed under the License is distributed on an "AS IS" BASIS,
       WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
       See the License for the specific language governing permissions and
       limitations under the License."""
        requests_text = wx.StaticText(self.scrolled_panel, label=requests_license)
        requests_text.SetFont(mono_font)

        unidecode = wx.StaticText(self.scrolled_panel, label="pyjam uses unidecode. License below.")
        unidecode_license = """
    Original character transliteration tables:

    Copyright 2001, Sean M. Burke <sburke@cpan.org>, all rights reserved.

    Python code and later additions:

    Copyright 2016, Tomaz Solc <tomaz.solc@tablix.org>

    This program is free software; you can redistribute it and/or
    modify it under the terms of the GNU General Public License
    as published by the Free Software Foundation; either version 2
    of the License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; if not, write to the Free Software
    Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA."""
        unidecode_text = wx.StaticText(self.scrolled_panel, label=unidecode_license)
        unidecode_text.SetFont(mono_font)

        yt_dl_text = wx.StaticText(self.scrolled_panel, label=("pyjam also uses youtube-dl. youtube-dl is released "
                                                               "under public domain"))

        self.top_sizer = wx.BoxSizer(wx.VERTICAL)
        self.scroll_sizer = wx.BoxSizer(wx.VERTICAL)

        self.scroll_sizer.Add(info, 0, wx.ALL, 2)
        self.scroll_sizer.Add(wxw, 0, wx.ALL, 2)
        self.scroll_sizer.Add(wxw_text, 0, wx.EXPAND | wx.ALL, 3)
        self.scroll_sizer.Add(seven, 0, wx.ALL, 2)
        self.scroll_sizer.Add(seven_text, 0, wx.EXPAND | wx.ALL, 3)
        self.scroll_sizer.Add(ffmpeg, 0, wx.ALL, 2)
        self.scroll_sizer.Add(ffmpeg_text, 0, wx.EXPAND | wx.ALL, 3)
        self.scroll_sizer.Add(watchdog, 0, wx.ALL, 2)
        self.scroll_sizer.Add(watchdog_text, 0, wx.EXPAND | wx.ALL, 3)
        self.scroll_sizer.Add(psutil, 0, wx.ALL, 2)
        self.scroll_sizer.Add(psutil_text, 0, wx.EXPAND | wx.ALL, 3)
        self.scroll_sizer.Add(requests_info, 0, wx.ALL, 2)
        self.scroll_sizer.Add(requests_text, 0, wx.EXPAND | wx.ALL, 3)
        self.scroll_sizer.Add(unidecode, 0, wx.ALL, 2)
        self.scroll_sizer.Add(unidecode_text, 0, wx.EXPAND | wx.ALL, 3)
        self.scroll_sizer.Add(yt_dl_text, 0, wx.ALL, 2)
        self.top_sizer.Add(self.scrolled_panel, 1, wx.EXPAND)

        self.SetSizer(self.top_sizer)
        self.scrolled_panel.SetSizerAndFit(self.scroll_sizer)
        self.scrolled_panel.SetupScrolling()
        self.Show()


def update_check(parent):
    r = requests.get('https://api.github.com/repos/10se1ucgo/pyjam/releases/latest')

    if not r.ok:
        return

    new = r.json()['tag_name']

    try:
        if StrictVersion(__version__) < StrictVersion(new.lstrip('v')):
            info = wx.MessageDialog(parent, message="pyjam {v} is now available!\nGo to download page?".format(v=new),
                                    caption="pyjam Update", style=wx.OK | wx.CANCEL | wx.ICON_INFORMATION)
            if info.ShowModal() == wx.ID_OK:
                webbrowser.open_new_tab(r.json()['html_url'])
            info.Destroy()
    except ValueError:
        pass


