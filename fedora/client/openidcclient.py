# -*- coding: utf-8 -*-
#
# Copyright (C) 2016, 2017  Red Hat, Inc.
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

"""Base client for applications relying on OpenID Connect for authentication.

Implementation note: this implementation hardcodes certain endpoints at the IdP
to the ones as implemented by Ipsilon 2.0 and higher.

.. moduleauthor:: Patrick Uiterwijk <puiterwijk@redhat.com>

.. versionadded: 0.3.35

"""

from fedora import __version__

from openidc_client import OpenIDCClient

PROD_IDP = 'https://id.fedoraproject.org/openidc/'
STG_IDP = 'https://id.stg.fedoraproject.org/openidc/'
DEV_IDP = 'https://iddev.fedorainfracloud.org/openidc/'


class OpenIDCBaseClient(OpenIDCClient):
    def __init__(self, app_identifier, id_provider, client_id, use_post=False,
                 cachedir=None):
        """Client for interacting with web services relying on OpenID Connect.

        :arg app_identifier: Identifier for storage of retrieved tokens
        :kwarg id_provider: URL of the identity provider to get tokens from
        :kwarg client_id: The Client Identifier used to request credentials
        :kwarg use_post: Whether to use POST submission of client secrets
            rather than Authorization header
        :kwarg cachedir: The directory in which to store the token caches. Will
            be put through expanduer. Default is ~/.fedora. If this does not
            exist and we are unable to create it, the OSError will e thrown up.
        """
        if cachedir is None:
            cachedir = '~/.fedora/'
        super(OpenIDCBaseClient, self).__init__(
            self,
            app_identifier=app_identifier,
            id_provider=id_provider,
            id_provider_mapping={'Token': 'Token',
                                 'Authorization': 'Authorization'},
            client_id=client_id,
            use_post=use_post,
            useragent='Python-Fedora/%s' % __version__,
            cachedir=cachedir)
