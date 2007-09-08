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
#

"""
This plugin provides authentication of passwords against Bugzilla via XML-RPC
"""

import logging
import xmlrpclib

from soprovider import *
from turbogears import config
from updatessystem.model import User, VisitIdentity

log = logging.getLogger(__name__)

class SoBugzillaIdentityProvider(SqlObjectIdentityProvider):
    """
    IdentityProvider that authenticates users against Bugzilla via XML-RPC
    """
    def __init__(self):
        super(SoBugzillaIdentityProvider, self).__init__()
        self.bz_server = config.get('bz_server')

    def validate_identity(self, user_name, password, visit_key):
        if not self.validate_password(None, user_name, password):
            log.warning("Invalid password for %s" % user_name)
            return None
        log.info("Login successful for %s" % user_name)

        user_name = to_db_encoding(user_name, self.user_class_db_encoding)

        try:
            user = User.by_user_name(user_name)
        except SQLObjectNotFound:
            log.info("Creating new user %s" % user_name)
            user = User(user_name=user_name)

        try:
            link = VisitIdentity.by_visit_key(visit_key)
            link.user_id = user.id
        except SQLObjectNotFound:
            link = VisitIdentity(visit_key=visit_key, user_id=user.id)

        return SqlObjectIdentity(visit_key, user)

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
