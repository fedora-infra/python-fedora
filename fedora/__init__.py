# Copyright 2008 Red Hat, Inc.
# This file is part of python-fedora
# 
# python-fedora is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
# 
# python-fedora is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public
# License along with python-fedora; if not, see <http://www.gnu.org/licenses/>
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
'''
Python Fedora

Modules to communicate with and help implement Fedora Services.
'''
import kitchen
# Setup gettext for all of kitchen.
# Remember -- _() is for marking most messages
# b_() is for marking messages that are used in exceptions
(_, N_) = kitchen.i18n.easy_gettext_setup('python-fedora')
(b_, bN_) = kitchen.i18n.easy_gettext_setup('python-fedora', use_unicode=False)

from fedora import release
__version__ = release.VERSION

__all__ = ('__version__', 'accounts', 'client', 'release', 'tg')
