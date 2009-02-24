from fedora.django import connection

import django.contrib.auth.models as authmodels
from django.db import models
from django.utils.translation import ugettext_lazy as _

# Map FAS user elements to model attributes
_fasmap = {
    'id': 'id',
    'username': 'username',
    'email': 'email',
}

def _new_group(group):
    try:
        g = authmodels.Group.objects.get(id=group['id'])
    except authmodels.Group.DoesNotExist:
        g = authmodels.Group(id=group['id'])
    g.name = group['name']
    g.save()
    return g

def _syncdb_handler(sender, **kwargs):
    # Import FAS groups
    if kwargs['verbosity'] > 0:
        print 'Loading FAS groups...'
    gl = connection.send_request('group/list',
        req_params={'tg_format': 'json'})
    groups = gl['groups']
    for group in groups:
        _new_group(group)

class FasUserManager(authmodels.UserManager):
    def user_from_fas(self, user):
        """
        Creates a user in the table based on the structure returned
        by FAS
        """
        d = {}
        for k, v in _fasmap.iteritems():
            d[v] = user[k]
        u = FasUser(**d)
        u.set_unusable_password()
        u.is_active = user['status'] == 'active'
#        u.is_superuser = 
        u.save()
        for group in user['approved_memberships']:
            g = _new_group(group)
            u.groups.add(g)
        u.save()
        return u

class FasUser(authmodels.User):
    def _get_name(self):
        userinfo = connection.person_by_id(self.id)
        return userinfo['human_name']
        
    name = property(_get_name)

    objects = FasUserManager()

    def get_full_name(self):
        return name.strip()
