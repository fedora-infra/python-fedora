from fedora.django.auth import models

from django.db.models.signals import post_syncdb

post_syncdb.connect(models._syncdb_handler, sender=models)
