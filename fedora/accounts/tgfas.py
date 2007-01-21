import turbogears
from datetime import *
from sqlalchemy import *
from sqlalchemy.ext.sessioncontext import SessionContext
from sqlalchemy.ext.assignmapper import assign_mapper

# The identity schema.


### FIXME: Construct the default dburi from the /etc/sysconfig file like
# website.py does

#dburi = turbogears.config.get('fedora.fasdburi', 'sqlite://')
dburi = 'sqlite:////var/tmp/fasdb.sqlite'
engine = create_engine(dburi)
metadata = DynamicMetaData()
metadata.connect(dburi)

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
'''
visit_identity_table = Table('visit_identity', metadata,
    Column('visit_key', String(40), primary_key=True),
    Column('user_id', Integer, ForeignKey('tg_user.user_id'), index=True)
)

groups_table = Table('tg_group', metadata,
    Column('group_id', Integer, primary_key=True),
    Column('group_name', Unicode(16), unique=True),
    Column('display_name', Unicode(255)),
    Column('created', DateTime, default=datetime.now)
)

users_table = Table('tg_user', metadata,
    Column('user_id', Integer, primary_key=True),
    Column('user_name', Unicode(16), unique=True),
    Column('email_address', Unicode(255), unique=True),
    Column('display_name', Unicode(255)),
    Column('password', Unicode(40)),
    Column('created', DateTime, default=datetime.now)
)

permissions_table = Table('permission', metadata,
    Column('permission_id', Integer, primary_key=True),
    Column('permission_name', Unicode(16), unique=True),
    Column('description', Unicode(255))
)

user_group_table = Table('user_group', metadata,
    Column('user_id', Integer, ForeignKey('tg_user.user_id')),
    Column('group_id', Integer, ForeignKey('tg_group.group_id'))
)

group_permission_table = Table('group_permission', metadata,
    Column('group_id', Integer, ForeignKey('tg_group.group_id')),
    Column('permission_id', Integer, ForeignKey('permission.permission_id'))
)
'''

class Visit(object):
    def lookup_visit(cls, visit_key):
        return Visit.get(visit_key)
    lookup_visit = classmethod(lookup_visit)

class VisitIdentity(object):
    pass
'''
class Group(object):
    """
    An ultra-simple group definition.
    """
    pass

class User(object):
    """
    Reasonably basic User definition. Probably would want additional
    attributes.
    """
    def permissions(self):
        perms = set()
        for g in self.groups:
            perms = perms | set(g.permissions)
        return perms
    permissions = property(permissions)

class Permission(object):
    pass
'''
assign_mapper(context, Visit, visits_table)
assign_mapper(context, VisitIdentity, visit_identity_table)
'''
assign_mapper(context, VisitIdentity, visit_identity_table,
          properties=dict(users=relation(User, backref='visit_identity')))
assign_mapper(context, User, users_table)
assign_mapper(context, Group, groups_table,
          properties=dict(users=relation(User,secondary=user_group_table, backref='groups')))
assign_mapper(context, Permission, permissions_table,
          properties=dict(groups=relation(Group,secondary=group_permission_table, backref='permissions')))
'''
