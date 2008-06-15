# -*- coding: utf-8 -*-
#
# Copyright © 2007  Red Hat, Inc. All rights reserved.
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
# Red Hat Author(s): Luke Macken <lmacken@redhat.com>
#                    Toshio Kuratomi <tkuratom@redhat.com>
#

'''
fedora.client is used to interact with Fedora Services.
'''

class FedoraServiceError(Exception):
    '''Base Exception for any problem talking with the Service.'''
    pass

class ServerError(FedoraServiceError):
    '''Unable to talk to the server properly.'''
    pass

class AuthError(FedoraServiceError):
    '''Error during authentication.  For instance, invalid password.'''
    pass

class AppError(FedoraServiceError):
    '''Error condition that the server is passing back to the client.'''
    pass

### FIXME: when porting to py3k syntax, no need for try: except
# pylint: disable-msg=W0611,W0403
try:
    from .baseclient import BaseClient
    from .proxyclient import ProxyClient
except SyntaxError:
    from baseclient import BaseClient
    from proxyclient import ProxyClient
# pylint: enable-msg=W0611,W0403

__all__ = ('FedoraServiceError', 'ServerError', 'AuthError', 'AppError',
        'ProxyClient', 'BaseClient',)
