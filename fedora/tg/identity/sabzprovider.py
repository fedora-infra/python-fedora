# $Id: sobzprovider.py,v 1.2 2007/01/03 21:21:18 lmacken Exp $
# python-fedora, python module to interact with Fedora Infrastructure Services
# Copyright (C) 2007  Red Hat Software Inc
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
# Authors: Luke Macken <lmacken@rehat.com>
#          Toshio Kuratomi <tkuratom@redhat.com>

"""
This plugin provides authentication of passwords against Bugzilla via XML-RPC
"""

import logging
import xmlrpclib

from turbogears.identity.saprovider import *
from turbogears import config
from fedora.accounts.tgfas import VisitIdentity

log = logging.getLogger(__name__)
class FakeUser(object):
    def __init__(self, user_id, user_name, user, groups, permissions):
        self.user_id = user_id
        self.user_name = user_name
        self.user = user
        self.groups = groups
        self.permissions = permissions
        self.display_name = 'Toshio Kuratomi'

class FakeGroup(object):
    def __init__(self, gid):
        self.group_id = gid
        self.group_name = 'first' + str(gid)
        self.display_name = 'Group: #' + str(gid)

class SaBugzillaIdentity(SqlAlchemyIdentity):
    def _get_user(self):
        visit = visit_class.get_by(visit_key = self.visit_key)
        if not visit:
            self._user = None
            return None
        self._user = FakeUser(1, 'my fake user name', None, (FakeGroup(1), FakeGroup(2), FakeGroup(3)), None)
        return self._user
    user = property(_get_user)

class SaBugzillaIdentityProvider(SqlAlchemyIdentityProvider):
    """
    IdentityProvider that authenticates users against Bugzilla via XML-RPC
    """
    def __init__(self):
        super(SaBugzillaIdentityProvider, self).__init__()
        self.bz_server = config.get('identity.sabugzilla.bz_server')
        global visit_class
        visit_class_path = config.get("identity.saprovider.model.visit", None)
        log.info("Loading: %s", visit_class_path)
        visit_class = load_class(visit_class_path)

    def validate_identity(self, user_name, password, visit_key):
        user = FakeUser(1, user_name, None, (FakeGroup(1), FakeGroup(2), FakeGroup(3)), None)

        if not self.validate_password(user, user_name, password):
            log.warning("Invalid password for %s" % user_name)
            return None
        log.info("Login successful for %s" % user_name)

        link = visit_class.get_by(visit_key=visit_key)
        if not link:
            link = visit_class(visit_key=visit_key, user_id = user.user_id)
            visit_class.mapper.get_session().save(link)
        else:
            link.user_id = user.user_id
        visit_class.mapper.get_session().flush()
        return SaBugzillaIdentity(visit_key, user)

    def validate_password(self, user, user_name, password):
        """
        Complete hack, but it works.
        Request bug #1 with the given username and password.  If a Fault is
        thrown, the username/pass is invalid; else, we're good to go.
        """
        try:
            server = xmlrpclib.Server(self.bz_server)
            server.bugzilla.getBugSimple('1', user_name, password)
        except xmlrpclib.Fault:
            return False
        return True

    def load_identity(self, visit_key):
        return SaBugzillaIdentity(visit_key)
