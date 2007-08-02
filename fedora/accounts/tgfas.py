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

import turbogears
from datetime import *
from sqlalchemy import *
from sqlalchemy.ext.sessioncontext import SessionContext
from sqlalchemy.ext.assignmapper import assign_mapper

import fas

# Retrieve the database visit information is stored in from the filesystem
try:
    dbName = 'fassession'
    dbInfo = fas.retrieve_db_info(dbName)
    dbInfo['dbname'] = dbName
    if dbInfo.has_key('password'):
        dbInfo['password'] = ':%s' % dbInfo['password']
    else:
        dbInfo['password'] = ''

    dbUri = 'postgres://%(user)s%(password)s@%(host)s/%(dbname)s' % dbInfo
except:
    # Fallback to a local session db so we can operate locally
    dbUri = 'sqlite:////var/tmp/fasdb.sqlite'

engine = create_engine(dbUri)
metadata = DynamicMetaData()
metadata.connect(dbUri)

context = SessionContext(lambda:create_session(bind_to=engine))

visits_table = Table('visit', metadata,
    Column('visit_key', String(40), primary_key=True),
    Column('created', DateTime, nullable=False, default=datetime.now),
    Column('expiry', DateTime)
)

visit_identity_table = Table('visit_identity', metadata,
    Column('visit_key', String(40), primary_key=True),
    Column('user_id', Integer, index=True)
)

metadata.create_all(checkfirst=True)

class Visit(object):
    def lookup_visit(cls, visit_key):
        return Visit.get(visit_key)
    lookup_visit = classmethod(lookup_visit)

class VisitIdentity(object):
    pass
assign_mapper(context, Visit, visits_table)
assign_mapper(context, VisitIdentity, visit_identity_table)
