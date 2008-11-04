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
from turbogears import flash, redirect
from decorator import decorator

def request_format():
    '''Return the output format that was requested.
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
            [...]

        @expose(allow_json=True)
        @error_handler(enter_number)
        @validate(form=number_form)
        def save(self, number):
            return dict(success=True)

    :Returns: None if there are no validation errors or json isn't requested,
        otherwise returns a dictionary with the error that's suitable for
        return from the controller.  The error message is set in tg_flash
        regardless.
    '''
    # Check for validation errors
    errors = getattr(cherrypy.request, 'validation_errors', None)
    if not errors:
        return None

    # Set the message for both html and json output
    message = u'\n'.join([u'%s: %s' % (param, msg) for param, msg in
        errors.items()])
    format = request_format()
    if format == 'html':
        message.translate({ord('\n'): u'<br />\n'})
    flash(message)

    # If json, return additional information to make this an exception
    if format == 'json':
        # Note: explicit setting of tg_template is needed in TG < 1.0.4.4
        # A fix has been applied for TG-1.0.4.5
        return dict(exc='Invalid', tg_template='json')
    return None

def json_or_redirect(forward_url):
    '''If json is wanted, return a dict, otherwise redirect.

    :arg forward_url: If json was not requested, redirect to this URL after.

    This is a decorator to use with a method that returns json by default.
    If json is requested, then it will return the dict from the method.  If
    json is not requested, it will redirect to the given URL.  The method that
    is decorated should be constructed so that it calls turbogears.flash()
    with a message that will be displayed on the forward_url page.

    Use it like this::

        import turbogears

        @json_or_redirect('http://localhost/calc/')
        @expose(allow_json=True)
        def divide(self, dividend, divisor):
            try:
                answer = dividend * 1.0 / divisor
            except ZeroDivisionError:
                turbogears.flash('Division by zero not allowed')
                return dict(exc='ZeroDivisionError')
            turbogears.flash('The quotient is %s' % answer)
            return dict(quotient=answer)

    In the example, we return either an exception or an answer, using
    turbogears.flash() to tell people of the result in either case.  If json
    data is requested, the user will get back a json string with the proper
    information.  If html is requested, we will be redirected to
    'http://localhost/calc/' where the flashed message will be displayed.
    '''
    def call(func, *args, **kw):
        if request_format() == 'json':
            return func(*args, **kw)
        else:
            func(*args, **kw)
            raise redirect(forward_url)
    return decorator(call)

__all__ = [request_format, jsonify_validation_errors, json_or_redirect]
