====================================
Fedora Django Authentication Backend
====================================
:Authors: Ignacio Vazquez-Abrams
:Date: 23 Feb 2009
:For Version: 0.3.x

The django.auth package provides an authentication backend for Django
projects.

------------------
fedora.django.auth
------------------

As FAS users are authenticated they are added to
:class:`~fedora.django.auth.models.FasUser`. FAS groups are added to
:class:`~django.contrib.auth.models.Group` both during ``syncdb`` and when
a user is authenticated.

Integrating into a Django Project
=================================

Add the following lines to the project's :file:`settings.py`::

    AUTHENTICATION_BACKENDS = (
        'fedora.django.auth.backends.FasBackend',
    )

    FAS_USERNAME = '<username>'
    FAS_PASSWORD = '<password>'
    FAS_USERAGENT = '<user agent>'

``FAS_ADMINS`` is a tuple of usernames that you want to have superuser
rights in the Django project.

Additionally, set ``FAS_GENERICEMAIL`` to ``False`` in order to use the
email address specified in FAS instead of <username>``@fedoraproject.org``.

Add ``fedora.django.auth`` to ``INSTALLED_APPS``.

.. warning::
    The ``User.first_name`` and ``User.last_name`` attributes are always
    empty since FAS does not have any equivalents. The ``name``
    read-only property results in a round trip to the FAS server.

In order to transparently activate experimental FAS single sign-on, add 
``fedora.django.auth.middleware.FasMiddleware`` to ``MIDDLEWARE_CLASSES``
in ``settings.py``.
