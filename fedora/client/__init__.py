# -*- coding: utf-8 -*-
#
# Copyright (C) 2007  Red Hat, Inc.
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


.. moduleauthor:: Ricky Zhou <ricky@fedoraproject.org>
.. moduleauthor:: Luke Macken <lmacken@redhat.com>
.. moduleauthor:: Toshio Kuratomi <tkuratom@redhat.com>
'''

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

    This includes network errors and 500 response codes.
    '''
    def __init__(self, url, status, msg):
        FedoraServiceError.__init__(self)
        self.filename = url
        self.code = status
        self.msg = msg

    def __str__(self):
        return 'ServerError(%s, %s, %s)' % (self.filename, self.code, self.msg)

class AuthError(FedoraServiceError):
    '''Error during authentication.  For instance, invalid password.'''
    pass

class AppError(FedoraServiceError):
    '''Error condition that the server is passing back to the client.'''
    def __init__(self, name, message, extras=None):
        FedoraServiceError.__init__(self)
        self.name = name
        self.message = message
        self.extras = extras

    def __str__(self):
        return 'AppError(%s, %s, extras=%s)' % (self.name, self.message,
                self.extras)

class DictContainer(dict):
    '''dict whose members can be accessed via attribute lookup.

    One thing to note: You can have an entry in your container that is visible
    instead of a standard dict method.  So, for instance, you can have this
    happen::

        >>> d = DictContainer({'keys': 'key'})
        >>> d.keys()
        Traceback (most recent call last):
          File "<stdin>", line 1, in <module>
        TypeError: 'str' object is not callable

    So, as a safety precaution, you should be sure to access things via the
    dict methods::

        >>> d = DictContainer({'keys': 'key'})
        >>> dict.keys(d)
        ['keys']

    The special methods like __getitem__(), __getattr__(), setattr(), etc
    that are invoked through alternate syntax rather than called directly as
    a method are immune to this so you can do this with no ill effects::

        >>> d.__setattr__ = 1000
        >>> d.__getattr__ = 10
        >>> print d.__setattr__
        1000
        >>> print d.__getattr__
        10
    '''
    def __getitem__(self, key):
        '''Return the value for the key in the dictionary.

        If the value is a dict, convert it to a DictContainer first.
        '''
        value = super(DictContainer, self).__getitem__(key)
        if type(value) == dict:
            value = DictContainer(value)
            self[key] = value
        return value

    def __getattribute__(self, key):
        '''Return the value from the dictionary or from the real attributes.

        * If the key exists in the dict
            * If the value is a dict
                * Convert it to a DictContainer
            * Return the converted value
        * Otherwise, if it exists in the values, return that.
        * Otherwise, raise AttributeError.
        '''
        if key in self:
            value = super(DictContainer, self).__getitem__(key)
            if type(value) == dict:
                value = DictContainer(value)
                self[key] = value
            return value
        return super(DictContainer, self).__getattribute__(key)

    def __setattr__(self, key, value):
        '''Set a key to a value.

        If the key is not an existing value, set it into the dict instead of
        as an attribute.
        '''
        if hasattr(self, key) and key not in self:
            super(DictContainer, self).__setattr__(key, value)
        else:
            self[key] = value

# We want people to be able to import fedora.client.*Client directly
# pylint: disable-msg=W0611
from fedora.client.proxyclient import ProxyClient
from fedora.client.fasproxy import FasProxyClient
from fedora.client.baseclient import BaseClient
from fedora.client.fas2 import AccountSystem, FASError, CLAError
from fedora.client.pkgdb import PackageDB, PackageDBError
from fedora.client.bodhi import BodhiClient, BodhiClientException
from fedora.client.wiki import Wiki
# pylint: enable-msg=W0611

__all__ = ('FedoraServiceError', 'ServerError', 'AuthError', 'AppError',
        'FedoraClientError', 'DictContainer',
        'FASError', 'CLAError', 'BodhiClientException', 'PackageDBError',
        'ProxyClient', 'FasProxyClient', 'BaseClient', 'AccountSystem',
        'PackageDB', 'BodhiClient', 'Wiki')
