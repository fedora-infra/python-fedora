# -*- coding: utf-8 -*-
#
# Copyright (C) 2008-2009  Red Hat, Inc.
# Copyright (C) 2008  Ricky Zhou
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
Miscellaneous functions of use on a TurboGears Server

.. versionchanged:: 0.3.14
   Save the original turbogears.url function as :func:`fedora.tg.util.tg_url`

.. versionchanged:: 0.3.17
   Renamed from fedora.tg.util

.. versionchanged:: 0.3.25
   Renamed from fedora.tg.tg1utils
   
.. moduleauthor:: Toshio Kuratomi <tkuratom@redhat.com>
.. moduleauthor:: Ricky Zhou <ricky@fedoraproject.org>
'''
from itertools import chain
import urlparse
import cgi
import os
import urllib

import cherrypy
from cherrypy import request
from decorator import decorator
import pkg_resources
import turbogears
from turbogears import flash, redirect, config, identity
import turbogears.util as tg_util
from turbogears.controllers import check_app_root
from turbogears.identity.exceptions import RequestRequiredException

from fedora import b_

# Save this for people who need the original url() function
tg_url = turbogears.url

def add_custom_stdvars(new_vars):
    return new_vars.update({'fedora_template': fedora_template})

def url(tgpath, tgparams=None, **kwargs):
    '''Computes URLs.

    This is a replacement for :func:`turbogears.controllers.url` (aka
    :func:`tg.url` in the template).  In addition to the functionality that
    :func:`tg.url` provides, it adds a token to prevent :term:`CSRF` attacks.

    :arg tgpath:  a list or a string. If the path is absolute (starts
        with a "/"), the :attr:`server.webpath`, :envvar:`SCRIPT_NAME` and
        the approot of the application are prepended to the path. In order for
        the approot to be detected properly, the root object should extend
        :class:`turbogears.controllers.RootController`.
    :kwarg tgparams: See param: ``kwargs``
    :kwarg kwargs: Query parameters for the URL can be passed in as a dictionary
        in the second argument *or* as keyword parameters.  Values which are a
        list or a tuple are used to create multiple key-value pairs.
    :returns: The changed path

    .. versionadded:: 0.3.10
       Modified from turbogears.controllers.url for :ref:`CSRF-Protection`
    '''
    if not isinstance(tgpath, basestring):
        tgpath = '/'.join(list(tgpath))
    if tgpath.startswith('/'):
        webpath = (config.get('server.webpath') or '').rstrip('/')
        if tg_util.request_available():
            check_app_root()
            tgpath = request.app_root + tgpath
            try:
                webpath += request.wsgi_environ['SCRIPT_NAME'].rstrip('/')
            except (AttributeError, KeyError): # pylint: disable-msg=W0704
                # :W0704: Lack of wsgi environ is fine... we still have
                # server.webpath
                pass
        tgpath = webpath + tgpath
    if tgparams is None:
        tgparams = kwargs
    else:
        try:
            tgparams = tgparams.copy()
            tgparams.update(kwargs)
        except AttributeError:
            raise TypeError(
                    b_('url() expects a dictionary for query parameters'))
    args = []
    # Add the _csrf_token
    try:
        if identity.current.csrf_token:
            tgparams.update({'_csrf_token': identity.current.csrf_token})
    except RequestRequiredException: # pylint: disable-msg=W0704
        # :W0704: If we are outside of a request (called from non-controller
        # methods/ templates) just don't set the _csrf_token.
        pass

    # Check for query params in the current url
    query_params = tgparams.iteritems()
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
        for key, value in pairs:
            if value is None:
                continue
            if isinstance(value, unicode):
                value = value.encode('utf8')
            args.append((key, str(value)))
    query_string = urllib.urlencode(args, True)
    tgpath = urlparse.urlunparse((scheme, netloc, path, params, query_string,
            fragment))
    return tgpath

# this is taken from turbogears 1.1 branch
def _get_server_name():
    """Return name of the server this application runs on.

    Respects 'Host' and 'X-Forwarded-Host' header.

    See the docstring of the 'absolute_url' function for more information.

    .. note:: This comes from turbogears 1.1 branch.  It is only needed for
        _tg_absolute_url().  If we find that turbogears.get_server_name()
        exists, we replace this function with that one.
    """
    get = config.get
    h = request.headers
    host = get('tg.url_domain') or h.get('X-Forwarded-Host', h.get('Host'))
    if not host:
        host = '%s:%s' % (get('server.socket_host', 'localhost'),
            get('server.socket_port', 8080))
    return host

# this is taken from turbogears 1.1 branch
def tg_absolute_url(tgpath='/', params=None, **kw):
    """Return absolute URL (including schema and host to this server).

    Tries to account for 'Host' header and reverse proxying
    ('X-Forwarded-Host').

    The host name is determined this way:

    * If the config setting 'tg.url_domain' is set and non-null, use this value.
    * Else, if the 'base_url_filter.use_x_forwarded_host' config setting is
      True, use the value from the 'Host' or 'X-Forwarded-Host' request header.
    * Else, if config setting 'base_url_filter.on' is True and
      'base_url_filter.base_url' is non-null, use its value for the host AND
      scheme part of the URL.
    * As a last fallback, use the value of 'server.socket_host' and
      'server.socket_port' config settings (defaults to 'localhost:8080').

    The URL scheme ('http' or 'http') used is determined in the following way:

    * If 'base_url_filter.base_url' is used, use the scheme from this URL.
    * If there is a 'X-Use-SSL' request header, use 'https'.
    * Else, if the config setting 'tg.url_scheme' is set, use its value.
    * Else, use the value of 'cherrypy.request.scheme'.

    .. note:: This comes from turbogears 1.1 branch.  If we find that
        turbogears.absolute_url() exists, we replace this function with that
        one.

    .. versionadded:: 0.3.19
       Modified from turbogears.absolute_url() for :ref:`CSRF-Protection`
    """
    get = config.get
    use_xfh = get('base_url_filter.use_x_forwarded_host', False)
    if request.headers.get('X-Use-SSL'):
        scheme = 'https'
    else:
        scheme = get('tg.url_scheme')
    if not scheme:
        scheme = request.scheme
    base_url = '%s://%s' % (scheme, _get_server_name())
    if get('base_url_filter.on', False) and not use_xfh:
        base_url = get('base_url_filter.base_url').rstrip('/')
    return '%s%s' % (base_url, tg_url(tgpath, params, **kw))

def absolute_url(tgpath='/', params=None, **kw):
    """Return absolute URL (including schema and host to this server).

    Tries to account for 'Host' header and reverse proxying
    ('X-Forwarded-Host').

    The host name is determined this way:

    * If the config setting 'tg.url_domain' is set and non-null, use this value.
    * Else, if the 'base_url_filter.use_x_forwarded_host' config setting is
      True, use the value from the 'Host' or 'X-Forwarded-Host' request header.
    * Else, if config setting 'base_url_filter.on' is True and
      'base_url_filter.base_url' is non-null, use its value for the host AND
      scheme part of the URL.
    * As a last fallback, use the value of 'server.socket_host' and
      'server.socket_port' config settings (defaults to 'localhost:8080').

    The URL scheme ('http' or 'http') used is determined in the following way:

    * If 'base_url_filter.base_url' is used, use the scheme from this URL.
    * If there is a 'X-Use-SSL' request header, use 'https'.
    * Else, if the config setting 'tg.url_scheme' is set, use its value.
    * Else, use the value of 'cherrypy.request.scheme'.

    .. versionadded:: 0.3.19
       Modified from turbogears.absolute_url() for :ref:`CSRF-Protection`
    """
    return url(tg_absolute_url(tgpath, params, **kw))

def enable_csrf():
    '''A startup function to setup :ref:`CSRF-Protection`.

    This should be run at application startup.  Code like the following in the
    start-APP script or the method in :file:`commands.py` that starts it::

        from turbogears import startup
        from fedora.tg.util import enable_csrf
        startup.call_on_startup.append(enable_csrf)

    If we can get the :ref:`CSRF-Protection` into upstream :term:`TurboGears`,
    we might be able to remove this in the future.

    .. versionadded:: 0.3.10
       Added to enable :ref:`CSRF-Protection`
    '''
    # Override the turbogears.url function with our own
    turbogears.url = url
    turbogears.controllers.url = url
    if hasattr(turbogears, 'absolute_url'):
        turbogears.absolute_url = absolute_url

    # Ignore the _csrf_token parameter
    ignore = config.get('tg.ignore_parameters', [])
    if '_csrf_token' not in ignore:
        ignore.append('_csrf_token')
        config.update({'tg.ignore_parameters': ignore})

    # Add a function to the template tg stdvars that looks up a template.
    turbogears.view.variable_providers.append(add_custom_stdvars)

def request_format():
    '''Return the output format that was requested by the user.

    The user is able to specify a specific output format using either the
    ``Accept:`` HTTP header or the ``tg_format`` query parameter.  This
    function checks both of those to determine what format the reply should
    be in.

    :rtype: string
    :returns: The requested format.  If none was specified, 'default' is
        returned

    .. versionchanged:: 0.3.17
        Return symbolic names for json, html, xhtml, and xml instead of
        letting raw mime types through
    '''
    output_format = cherrypy.request.params.get('tg_format', '').lower()
    if not output_format:
        ### TODO: Two problems with this:
        # 1) TG lets this be extended via as_format and accept_format.  We need
        #    tie into that as well somehow.
        # 2) Decide whether to standardize on "json" or "application/json"
        accept = tg_util.simplify_http_accept_header(
                request.headers.get('Accept', 'default').lower())
        if accept in ('text/javascript', 'application/json'):
            output_format = 'json'
        elif accept == 'text/html':
            output_format = 'html'
        elif accept == 'text/plain':
            output_format = 'plain'
        elif accept == 'text/xhtml':
            output_format = 'xhtml'
        elif accept == 'text/xml':
            output_format = 'xml'
        else:
            output_format = accept
    return output_format

def jsonify_validation_errors():
    '''Return an error for :term:`JSON` if validation failed.

    This function checks for two things:

    1) We're expected to return :term:`JSON` data.
    2) There were errors in the validation process.

    If both of those are true, this function constructs a response that
    will return the validation error messages as :term:`JSON` data.

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

    :rtype: None or dict
    :Returns: None if there are no validation errors or :term:`JSON` isn't
        requested, otherwise a dictionary with the error that's suitable for
        return from the controller.  The error message is set in tg_flash
        whether :term:`JSON` was requested or not.
    '''
    # Check for validation errors
    errors = getattr(cherrypy.request, 'validation_errors', None)
    if not errors:
        return None

    # Set the message for both html and json output
    message = u'\n'.join([u'%s: %s' % (param, msg) for param, msg in
        errors.items()])
    format = request_format()
    if format in ('html', 'xhtml'):
        message.translate({ord('\n'): u'<br />\n'})
    flash(message)

    # If json, return additional information to make this an exception
    if format == 'json':
        # Note: explicit setting of tg_template is needed in TG < 1.0.4.4
        # A fix has been applied for TG-1.0.4.5
        return dict(exc='Invalid', tg_template='json')
    return None

def json_or_redirect(forward_url):
    '''If :term:`JSON` is requested, return a dict, otherwise redirect.

    This is a decorator to use with a method that returns :term:`JSON` by
    default.  If :term:`JSON` is requested, then it will return the dict from
    the method.  If :term:`JSON` is not requested, it will redirect to the
    given URL.  The method that is decorated should be constructed so that it
    calls turbogears.flash() with a message that will be displayed on the
    forward_url page.

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
    :func:`turbogears.flash` to tell people of the result in either case.  If
    :term:`JSON` data is requested, the user will get back a :term:`JSON`
    string with the proper information.  If html is requested, we will be
    redirected to 'http://localhost/calc/' where the flashed message will be
    displayed.

    :arg forward_url: If :term:`JSON` was not requested, redirect to this URL
        after.

    .. versionadded:: 0.3.7
       To make writing methods that use validation easier
    '''
    def call(func, *args, **kwargs):
        if request_format() == 'json':
            return func(*args, **kwargs)
        else:
            func(*args, **kwargs)
            raise redirect(forward_url)
    return decorator(call)

if hasattr(turbogears, 'absolute_url'):
    tg_absolute_url = turbogears.absolute_url

if hasattr(turbogears, 'get_server_name'):
    _get_server_name = turbogears.get_server_name

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

__all__ = ('add_custom_stdvars', 'absolute_url', 'enable_csrf',
        'fedora_template', 'jsonify_validation_errors', 'json_or_redirect',
        'request_format', 'tg_absolute_url', 'tg_url', 'url')
