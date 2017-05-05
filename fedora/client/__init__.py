# -*- coding: utf-8 -*-
#
# Copyright (C) 2007-2013  Red Hat, Inc.
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
fedora.client is used to interact with Fedora Services.

.. versionchanged:: 0.3.21
    Deprecate DictContainer in favor of bunch.Bunch
.. versionchanged:: 0.3.35
    Add the openid clients

.. moduleauthor:: Ricky Zhou <ricky@fedoraproject.org>
.. moduleauthor:: Luke Macken <lmacken@redhat.com>
.. moduleauthor:: Toshio Kuratomi <tkuratom@redhat.com>
'''
import errno
import os
import warnings

from munch import Munch


class FedoraClientError(Exception):

    '''Base Exception for problems which originate within the Clients.

    This should be the base class for any exceptions that the Client generates
    generate.  For instance, if the client performs validation before passing
    the data on to the Fedora Service.

    Problems returned while talking to the Services should be returned via a
    `FedoraServiceError` instead.

    '''
    pass


class FedoraServiceError(Exception):

    '''Base Exception for any problem talking with the Service.

    When the Client gets an error talking to the server, an exception of this
    type is raised.  This can be anything in the networking layer up to an
    error returned from the server itself.

    '''
    pass


class ServerError(FedoraServiceError):

    '''Unable to talk to the server properly.

    This includes network errors and 500 response codes.  If the error was
    generated from an http response, :attr:`code` is the HTTP response code.
    Otherwise, :attr:`code` will be -1.

    '''
    def __init__(self, url, status, msg):
        FedoraServiceError.__init__(self)
        self.filename = url
        self.code = status
        self.msg = msg

    def __str__(self):
        return 'ServerError(%s, %s, %s)' % (self.filename, self.code, self.msg)

    def __repr__(self):
        return 'ServerError(%r, %r, %r)' % (self.filename, self.code, self.msg)


class AuthError(FedoraServiceError):

    '''Error during authentication.  For instance, invalid password.'''
    pass


class LoginRequiredError(AuthError):

    """ Exception raised when the call requires a logged-in user. """

    pass


class AppError(FedoraServiceError):

    '''Error condition that the server is passing back to the client.'''
    def __init__(self, name, message, extras=None):
        FedoraServiceError.__init__(self)
        self.name = name
        self.message = message
        self.extras = extras

    def __str__(self):
        return 'AppError(%s, %s, extras=%s)' % (
            self.name, self.message, self.extras)

    def __repr__(self):
        return 'AppError(%r, %r, extras=%r)' % (
            self.name, self.message, self.extras)


class UnsafeFileError(Exception):
    def __init__(self, filename, message):
        super(UnsafeFileError, self).__init__(message)
        self.message = message
        self.filename = filename

    def __str__(self):
        return 'Unsafe file permissions! {}: {}'.format(self.filename,
                                                        self.message)


# Backwards compatibility
class DictContainer(Munch):
    def __init__(self, *args, **kwargs):
        warnings.warn(
            'DictContainer is deprecated.  Use the Munch class'
            ' from python-bunch instead.', DeprecationWarning, stacklevel=2)
        Munch.__init__(self, *args, **kwargs)


def check_file_permissions(filename, allow_notexists=False):
    if os.path.islink(filename):
        raise UnsafeFileError(filename, 'File is a symlink')
    try:
        stat = os.stat(filename)
    except OSError as e:
        if e.errno == errno.ENOENT and allow_notexists:
            return
        raise
    if stat.st_uid != os.getuid():
        raise UnsafeFileError(filename, 'File not owned by current user')
    if stat.st_gid != os.getgid():
        raise UnsafeFileError(filename, 'File not owner by primary group')
    if stat.st_mode & 0o007:
        raise UnsafeFileError(filename, 'File is world-readable')


# We want people to be able to import fedora.client.*Client directly
# pylint: disable-msg=W0611
from fedora.client.proxyclient import ProxyClient
from fedora.client.fasproxy import FasProxyClient
from fedora.client.baseclient import BaseClient
from fedora.client.openidproxyclient import OpenIdProxyClient
from fedora.client.openidbaseclient import OpenIdBaseClient
from fedora.client.fas2 import AccountSystem, FASError, CLAError
from fedora.client.bodhi import BodhiClient, BodhiClientException
from fedora.client.wiki import Wiki
# pylint: enable-msg=W0611

__all__ = ('FedoraServiceError', 'ServerError', 'AuthError', 'AppError',
           'FedoraClientError', 'LoginRequiredError', 'DictContainer',
           'FASError', 'CLAError', 'BodhiClientException',
           'ProxyClient', 'FasProxyClient', 'BaseClient', 'OpenIdProxyClient',
           'OpenIdBaseClient', 'AccountSystem', 'BodhiClient',
           'Wiki')
