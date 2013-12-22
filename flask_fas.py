# -*- coding: utf-8 -*-
# Flask-FAS - A Flask extension for authorizing users with FAS
#
# Primary maintainer: Ian Weller <ianweller@fedoraproject.org>
#
# Copyright (c) 2012, Red Hat, Inc.
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

'''
FAS authentication plugin for the flask web framework

.. moduleauthor:: Ian Weller <ianweller@fedoraproject.org>

..versionadded:: 0.3.30
'''
from functools import wraps
import warnings

import flask
from flask import request

try:
    from flask import _app_ctx_stack as stack
except ImportError:
    from flask import _request_ctx_stack as stack

from fedora import __version__
from fedora.client.fasproxy import FasProxyClient
from fedora.client import AuthError


class FAS(object):

    def __init__(self, app=None):
        self.app = app
        if self.app is not None:
            self._init_app(app)

    def _init_app(self, app):
        app.config.setdefault('FAS_BASE_URL',
                              'https://admin.fedoraproject.org/accounts/')
        app.config.setdefault('FAS_USER_AGENT', 'Flask-FAS/%s' % __version__)
        app.config.setdefault('FAS_CHECK_CERT', True)
        app.config.setdefault('FAS_COOKIE_NAME', 'tg-visit')
        # The default value of the next line is really True.
        # We have to set it to a sentinel value because we have to
        # handle the user using the deprecated FAS_HTTPS_REQUIRED
        app.config.setdefault('FAS_FLASK_COOKIE_REQUIRES_HTTPS', None)
        app.config.setdefault('FAS_HTTPS_REQUIRED', None)

        app.before_request(self._check_session_cookie)
        app.after_request(self._send_session_cookie)

    @property
    def fasclient(self):
        ctx = stack.top
        if not hasattr(ctx, 'fasclient'):
            ctx.fasclient = FasProxyClient(
                base_url=self.app.config['FAS_BASE_URL'],
                useragent=self.app.config['FAS_USER_AGENT'],
                insecure=not self.app.config['FAS_CHECK_CERT'],
            )
        return ctx.fasclient

    def _check_session_cookie(self):
        if self.app.config['FAS_COOKIE_NAME'] in request.cookies \
           and self.app.config['FAS_COOKIE_NAME']:
            session_id = request.cookies[self.app.config['FAS_COOKIE_NAME']]
            try:
                session_id, user = self.fasclient.get_user_info({'session_id':
                                                                 session_id})
                if hasattr(user, 'approved_memberships'):
                    user.groups = frozenset(
                        x.name for x in user.approved_memberships
                    )
                else:
                    user.groups = frozenset()
            except AuthError:
                session_id = None
                user = None
        else:
            session_id = None
            user = None
        flask.g.fas_session_id = session_id
        flask.g.fas_user = user

    def _send_session_cookie(self, response):
        # Handle the secure flag defaults here because we need to handle the
        # deprecated config name
        new_secure = self.app.config['FAS_FLASK_COOKIE_REQUIRES_HTTPS']
        old_secure = self.app.config['FAS_HTTPS_REQUIRED']
        if new_secure is None:
            if old_secure is None:
                new_secure = True
            else:
                new_secure = old_secure
        if old_secure is not None:
            warnings.warn('FAS_HTTPS_REQUIRED has been renamed to'
                          ' FAS_FLASK_COOKIE_REQUIRES_HTTPS.  Please convert'
                          ' your configuration to use the new name',
                          DeprecationWarning, stacklevel=2)

        response.set_cookie(
            key=self.app.config['FAS_COOKIE_NAME'],
            value=flask.g.fas_session_id or '',
            secure=self.app.config['FAS_FLASK_COOKIE_REQUIRES_HTTPS'],
            httponly=True,
        )
        return response

    def login(self, username, password):
        """Tries to log in a user.

        Sets the session ID cookie on :attr:`flask.g.fas_session_id` if the
        user was authenticated successfully and the user information returned
        from fas on :attr:`flask.g.fas_user`.

        :arg username: The username to log in
        :arg password: The password for the user logging in
        :returns: True if successful.  False if unsuccessful.
        """
        try:
            session_id, junk = self.fasclient.login(username, password)
            user = junk.user
            if hasattr(flask.g.fas_user, 'approved_memberships'):
                user.groups = [x.name for x in user.approved_memberships]
            else:
                user.groups = []
        except AuthError:
            return False
        except Exception:
            # We don't differentiate here between types of failures.  Could
            # log a warning here in the future
            return False
        flask.g.fas_session_id = session_id
        flask.g.fas_user = user
        return True

    def logout(self):
        '''Logout the user associated with this session
        '''
        self.fasclient.logout(flask.g.fas_session_id)
        flask.g.fas_session_id = None
        flask.g.fas_user = None


# This is a decorator we can use with any HTTP method (except login, obviously)
# to require a login.
# If the user is not logged in, it will redirect them to the login form.
# http://flask.pocoo.org/docs/patterns/viewdecorators/#login-required-decorator
def fas_login_required(function):
    """ Flask decorator to ensure that the user is logged in against FAS.
    To use this decorator you need to have a function named 'auth_login'.
    Without that function the redirect if the user is not logged in will not
    work.
    """
    @wraps(function)
    def decorated_function(*args, **kwargs):
        if flask.g.fas_user is None:
            return flask.redirect(flask.url_for('auth_login',
                                                next=flask.request.url))
        return function(*args, **kwargs)
    return decorated_function


def cla_plus_one_required(function):
    """ Flask decorator to retrict access to CLA+1.
    To use this decorator you need to have a function named 'auth_login'.
    Without that function the redirect if the user is not logged in will not
    work.
    """
    @wraps(function)
    def decorated_function(*args, **kwargs):
        valid = True
        if flask.g.fas_user is None:
            valid = False
        else:
            non_cla_groups = [
                x.name
                for x in flask.g.fas_user.approved_memberships
                if x.group_type != 'cla'
            ]

            if len(non_cla_groups) == 0:
                valid = False
        if not valid:
            return flask.redirect(flask.url_for('auth_login',
                                                next=flask.request.url))
        else:
            return function(*args, **kwargs)
    return decorated_function
