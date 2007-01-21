from datetime import datetime
from turbogears.visit.api import Visit
from turbogears.visit.savisit import SqlAlchemyVisitManager
from turbogears import config
from turbogears.util import load_class
from turbogears.database import bind_meta_data

import logging
log = logging.getLogger("turbogears.identity.savisit")

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
        visit_class.mapper.get_session().save(visit)
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
