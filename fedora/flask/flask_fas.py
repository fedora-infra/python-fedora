# Flask-FAS - A Flask extension for authorizing users with FAS
# Primary maintainer: Ian Weller <ianweller@fedoraproject.org>
#
# Copyright (c) 2012, Red Hat, Inc.
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
# list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
# * Neither the name of the Red Hat, Inc. nor the names of its contributors may
# be used to endorse or promote products derived from this software without
# specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE REGENTS AND CONTRIBUTORS ''AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import flask
from flask import request

from fedora.client.fasproxy import FasProxyClient
from fedora.client import AuthError

try:
    from flask import _app_ctx_stack as stack
except ImportError:
    from flask import _request_ctx_stack as stack

__version__ = '0.1.0'  # http://semver.org/


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
        app.config.setdefault('FAS_HTTPS_REQUIRED', True)

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
                    user.groups = [x.name for x in user.approved_memberships]
                else:
                    user.groups = []
            except AuthError:
                session_id = None
                user = None
        else:
            session_id = None
            user = None
        flask.g.fas_session_id = session_id
        flask.g.fas_user = user

    def _send_session_cookie(self, response):
        response.set_cookie(
                key=self.app.config['FAS_COOKIE_NAME'],
                value=flask.g.fas_session_id or '',
                secure=self.app.config['FAS_HTTPS_REQUIRED'],
                httponly=True,
        )
        return response

    def login(self, username, password):
        """
        Tries to log in a user. Returns True if successful, False if not. Sets
        the session ID cookie.
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
        flask.g.fas_session_id = session_id
        flask.g.fas_user = user
        return True

    def logout(self):
        self.fasclient.logout(flask.g.fas_session_id)
        flask.g.fas_session_id = None
        flask.g.fas_user = None
