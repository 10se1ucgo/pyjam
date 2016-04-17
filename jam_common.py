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

# A module that will probably be filled with common tools for all other jam_* modules.
# This module should NOT import anything from jam_*, as it will create potential for circular imports.
import logging
import traceback

import wx

logger = logging.getLogger('jam.common')


def wrap_exceptions(func):
    def _wrap_exceptions(*args, **kwargs):
        # args[0] = InstanceOfSomeClass() when wrapping a class method. (IT BETTER BE. WHYDOISUCKATPROGRAMMINGOHGOD)
        # This should really only be used on threads (main thread has a sys.excepthook)
        try:
            return func(*args, **kwargs)
        except (SystemExit, KeyboardInterrupt):
            raise
        except Exception:
            if isinstance(args[0], wx.TopLevelWindow):
                parent = args[0]
            elif hasattr(args[0], "parent") and isinstance(args[0].parent, wx.TopLevelWindow):
                parent = args[0].parent
            else:
                parent = wx.GetApp().GetTopWindow()
            error_message = ''.join(traceback.format_exc())
            error_dialog = wx.MessageDialog(parent=parent,
                                            message="An error has occured\n\n" + error_message,
                                            caption="Error!", style=wx.OK | wx.ICON_ERROR)
            error_dialog.ShowModal()
            error_dialog.Destroy()
            logger.critical(error_message)
            raise

    return _wrap_exceptions
