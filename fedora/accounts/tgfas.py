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
from sqlalchemy import MetaData
from sqlalchemy import Table, Column, ForeignKey
from sqlalchemy import String, Integer, DateTime
from turbogears.database import mapper

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

metadata = MetaData(dbUri)

visits_table = Table('visit', metadata,
    Column('visit_key', String(40), primary_key=True),
    Column('created', DateTime, nullable=False, default=datetime.now),
    Column('expiry', DateTime)
)

visit_identity_table = Table('visit_identity', metadata,
    Column('visit_key', String(40), ForeignKey('visit.visit_key'),
        primary_key=True),
    Column('user_id', Integer, index=True)
)

class Visit(object):
    '''
    A visit to your site
    '''
    def lookup_visit(cls, visit_key):
        return cls.query.get(visit_key)
    lookup_visit = classmethod(lookup_visit)

class VisitIdentity(object):
    '''
    A Visit that is linked to a User object
    '''
    pass

mapper(Visit, visits_table)
mapper(VisitIdentity, visit_identity_table)
