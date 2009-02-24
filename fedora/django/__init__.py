from fedora.client import AccountSystem

from django.conf import settings

connection = None

def _connect():
    global connection
    connection = AccountSystem(username=settings.FAS_USERNAME,
        password=settings.FAS_PASSWORD, useragent=settings.FAS_USERAGENT)

_connect()
