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
# Red Hat Author(s): Toshio Kuratomi <tkuratom@redhat.com>
#

'''
python-fedora, python module to interact with Fedora Infrastructure Services
'''

from datetime import datetime
from turbogears.visit.api import Visit
from turbogears.visit.savisit import SqlAlchemyVisitManager
from turbogears import config
from turbogears.util import load_class
from turbogears.database import bind_meta_data

import logging
log = logging.getLogger("turbogears.identity.savisit")

visit_class = None

### FIXME: This class is unnecessary once TG Bug #1238 is resolved
# Basically, the current VisitManager talks to the app's session.  We don't
# want to assume the app session as we might be talking to a site-wide
# session instead.  Using the session from the class's mapper does that.
class SaFasVisitManager(SqlAlchemyVisitManager):
    def __init__(self, timeout):
        global visit_class
        super(SaFasVisitManager,self).__init__(timeout)
        visit_class_path = config.get("visit.saprovider.model",
                               "turbogears.visit.savisit.TG_Visit")
        visit_class = load_class(visit_class_path)
        bind_meta_data()

    def new_visit_with_key(self, visit_key):
        visit = visit_class(visit_key=visit_key,
                        expiry=datetime.now()+self.timeout)
        visit.save()
        visit_class.mapper.get_session().flush()
        return Visit(visit_key, True)

    def update_queued_visits(self, queue):
        # TODO this should be made transactional
        #table = class_mapper(visit_class).mapped_table
        # Now update each of the visits with the most recent expiry
        for visit_key,expiry in queue.items():
            log.info("updating visit (%s) to expire at %s", visit_key,
                      expiry)
            visit = visit_class.lookup_visit(visit_key)
            visit.expiry = expiry
            visit_class.mapper.get_session().flush()
