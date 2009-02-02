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
from itertools import chain
import urlparse
import cgi
import urllib

import cherrypy
from cherrypy import request
import turbogears
from turbogears import flash, redirect, config, identity
import turbogears.util as tg_util
from turbogears.controllers import check_app_root
from decorator import decorator

def url(tgpath, tgparams=None, **kw):
    """Computes URLs.

    This is a replacement for turbogears.controllers.url (aka tg.url in the
    template).  In addition to the functionality that tg.url() provides, it
    adds csrf token handling.

    :arg tgpath:  a list or a string. If the path is absolute (starts
        with a "/"), the server.webpath, SCRIPT_NAME and the approot of the
        application are prepended to the path. In order for the approot to be
        detected properly, the root object should extend
        controllers.RootController.

    :kwarg tgparams:
    :kwarg *: Query parameters for the URL can be passed in as a dictionary in
        the second argument *or* as keyword parameters.  Values which are a
        list or a tuple are used to create multiple key-value pairs.
    :returns: The changed path
    """
    if not isinstance(tgpath, basestring):
        tgpath = '/'.join(list(tgpath))
    if tgpath.startswith('/'):
        webpath = (config.get('server.webpath') or '').rstrip('/')
        if tg_util.request_available():
            check_app_root()
            tgpath = request.app_root + tgpath
            try:
                webpath += request.wsgi_environ['SCRIPT_NAME'].rstrip('/')
            except (AttributeError, KeyError):
                pass
        tgpath = webpath + tgpath
    if tgparams is None:
        tgparams = kw
    else:
        try:
            tgparams = tgparams.copy()
            tgparams.update(kw)
        except AttributeError:
            raise TypeError('url() expects a dictionary for query parameters')
    args = []
    # Add the _csrf_token
    query_params = tgparams.iteritems()
    try:
        if identity.current.csrf_token:
            query_params = chain(query_params,
                    [('_csrf_token', identity.current.csrf_token)])
    except identity.exceptions.RequestRequiredException:
        # If we are outside of a request (called from non-controller methods/
        # templates) just don't set the _csrf_token.
        pass

    # Check for query params in the current url
    scheme, netloc, path, params, query_s, fragment = urlparse.urlparse(tgpath)
    if query_s:
        query_params = chain((p for p in cgi.parse_qsl(query_s) if p[0] !=
            '_csrf_token'), query_params)

    for key, value in query_params:
        if value is None:
            continue
        if isinstance(value, (list, tuple)):
            pairs = [(key, v) for v in value]
        else:
            pairs = [(key, value)]
        for k, v in pairs:
            if v is None:
                continue
            if isinstance(v, unicode):
                v = v.encode('utf8')
            args.append((k, str(v)))
    query_string = urllib.urlencode(args, True)
    tgpath = urlparse.urlunparse((scheme, netloc, path, params, query_string,
            fragment))
    return tgpath

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

def enable_csrf():
    '''A startup function to setup csrf handling.

    This should be run at application startup.
    Code like the following in the start-APP script or the method in
    commands.py that starts it::
        from turbogears import startup
        from fedora.tg.util import enable_csrf
        startup.call_on_startup.append(enable_csrf)

    If we can get the csrf protections into upstream TurboGears, we might be
    able to remove this in the future.
    '''
    # Override the turbogears.url funciton with our own
    turbogears.url = url
    turbogears.controllers.url = url

    # Ignore the _csrf_token parameter
    ignore = config.get('tg.ignore_parameters', [])
    if '_csrf_token' not in ignore:
        ignore.append('_csrf_token')
        config.update({'tg.ignore_parameters': ignore})

__all__ = [enable_csrf, jsonify_validation_errors, json_or_redirect,
        request_format, url]
