from datetime import datetime

from sqlalchemy import *
from sqlalchemy.orm import class_mapper

from turbogears import config
from turbogears.visit.api import BaseVisitManager, Visit
from turbogears.database import get_engine, metadata, session, mapper
from turbogears.util import load_class

import gettext
t = gettext.translation('python-fedora', '/usr/share/locale', fallback=True)
_ = t.ugettext

import logging
log = logging.getLogger("turbogears.identity.savisit")

visit_class = None

class SaFasVisitManager(BaseVisitManager):

    def __init__(self, timeout):
        global visit_class
        super(SaFasVisitManager,self).__init__(timeout)
        visit_class_path = config.get("visit.saprovider.model",
                               "turbogears.visit.savisit.TG_Visit")

        visit_class = load_class(visit_class_path)
        if visit_class is None:
            msg = _('No visit class found for %(visit_class_path)s,' \
                    'did you think to setup.py develop ?'
                    % {'visit_class_path': visit_class_path})
            log.error(msg)

        get_engine()
        # Not needed as we know that we're using our own visit class.
        #if visit_class is TG_Visit:
        #    mapper(visit_class, visits_table)

    def create_model(self):
        '''
        Create the Visit table if it doesn't already exist
        '''
        get_engine()
        class_mapper(visit_class).local_table.create(checkfirst=True)

    def new_visit_with_key(self, visit_key):
        created = datetime.now()
        visit = visit_class()
        visit.visit_key = visit_key
        visit.created = created
        visit.expiry = created + self.timeout
        session.flush()
        return Visit(visit_key, True)

    def visit_for_key(self, visit_key):
        '''
        Return the visit for this key or None if the visit doesn't exist or has
        expired.
        '''
        visit = visit_class.lookup_visit(visit_key)
        if not visit:
            return None
        now = datetime.now(visit.expiry.tzinfo)
        if visit.expiry < now:
            return None

        # Visit hasn't expired, extend it
        self.update_visit(visit_key, now+self.timeout)
        return Visit(visit_key, False)

    ### FIXME: This is the only piece of code that deviates from upstream
    # TurboGears-1.0.4.  before it using get_engine() to get the database
    # engine to use but that gets the global database instead of the one
    # we use for visit and identity.  So we have to do things differently
    # until http://trac.turbogears.org/ticket/1717 is fixed
    def update_queued_visits(self, queue):
        # TODO this should be made transactional
        table = class_mapper(visit_class).mapped_table
        engine = table.get_engine()
        # Now update each of the visits with the most recent expiry
        for visit_key,expiry in queue.items():
            log.info(_("updating visit (%(key)s) to expire at %(expire)s")
                    % {'key': visit_key, 'expire': expiry})
            #get_engine().execute(table.update(table.c.visit_key==visit_key,
            engine.execute(table.update(table.c.visit_key==visit_key,
                              values={'expiry': expiry}))
