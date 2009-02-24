from fedora.django import connection
from fedora.django.auth.models import FasUser

from django.db.models.signals import post_syncdb

class FasBackend:
    def authenticate(self, username=None, password=None):
        if connection.verify_password(username, password):
            userinfo = connection.person_by_username(username)
            user = FasUser.objects.user_from_fas(userinfo)
            if user.is_active:
                return user

    def get_user(self, userid):
        userinfo = connection.person_by_id(userid)
        return FasUser.objects.user_from_fas(userinfo)
