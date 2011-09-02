
# -*- coding: utf-8 -*-
#
# Copyright (C) 2008-2009  Red Hat, Inc.
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
#
'''
Miscellaneous functions of use on a TurboGears Server.  Functions in here will
work in both TG1 and TG2.  External code shouldn't import this file directly.
Instead it should import either fedora.tg.tg1utils or fedora.tg.tg2utils.  The
functions from here will be exposed in both of those files.

.. versionchanged:: 0.3.11
   Save the original turbogears.url function as :func:`fedora.tg.util.tg_url`

.. moduleauthor:: Toshio Kuratomi <tkuratom@redhat.com>
'''
import os
import pkg_resources

def fedora_template(template, template_type='genshi'):
    '''Function to return the path to a template.

    :arg template: filename of the template itself.  Ex: login.html
    :kwarg template_type: template language we need the template written in
        Defaults to 'genshi'
    :returns: filesystem path to the template
    '''
    # :E1101: pkg_resources does have resource_filename
    # pylint: disable-msg=E1101
    return pkg_resources.resource_filename('fedora', os.path.join('tg',
        'templates', template_type, template))

__all__ = ('fedora_template',)
