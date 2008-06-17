# -*- coding: utf-8 -*-
#
# Copyright © 2008  Red Hat, Inc. All rights reserved.
# Copyright © 2008  Ricky Zhou. All rights reserved.
#
# This copyrighted material is made available to anyone wishing to use, modify,
# copy, or redistribute it subject to the terms and conditions of the GNU
# General Public License v.2.  This program is distributed in the hope that it
# will be useful, but WITHOUT ANY WARRANTY expressed or implied, including the
# implied warranties of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.  You should have
# received a copy of the GNU General Public License along with this program;
# if not, write to the Free Software Foundation, Inc., 51 Franklin Street,
# Fifth Floor, Boston, MA 02110-1301, USA. Any Red Hat trademarks that are
# incorporated in the source code or documentation are not subject to the GNU
# General Public License and may only be used or replicated with the express
# permission of Red Hat, Inc.
#
# Author(s): Toshio Kuratomi <tkuratom@redhat.com>
#             Ricky Zhou <ricky@fedoraproject.org>
#
'''Miscellaneous functions of use on the server.
'''
import cherrypy

def request_format():
    '''Return the output format that was reqeusted
    '''
    format = cherrypy.request.params.get('tg_format', '').lower()
    if not format:
        format = cherrypy.request.headers.get('Accept', 'default').lower()
    return format

def jsonify_validation_errors():
    '''Return an error for json if validation failed.

    This function checks for two things:

    1) We're expected to return json data.
    2) There were errors in the validation process.

    If both of those are true, this function constructs a response that
    will return the validation error messages as json data.

    All controller methods that are error_handlers need to use this::

        @expose(template='templates.numberform')
        def enter_number(self, number):
            errors = fedora.tg.util.jsonify_validation_errors()
            if errors:
                return errors

        @expose(allow_json=True)
        @error_handler(enter_number)
        @validate(form=number_form)
        def save(self, number):
            return dict(success=True)

    Returns: None if there are no validation errors or json isn't requested,
        otherwise returns a dictionary with the error that's suitable for
        return from the controller.
    '''
    errors = getattr(cherrypy.request, 'validation_errors', None)
    if not (errors and request_format() == 'json'):
        return None

    message = '\n'.join([u'%s: %s' % (param, msg) for param, msg in
        errors.items()])

    # Note: explicit setting of tg_template is needed in TG < 1.0.4.4
    # A fix has been applied for TG-1.0.4.5
    return dict(exc='Invalid', tg_flash=message, tg_template='json')
