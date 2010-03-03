=====================
Authentication to FAS
=====================

The :ref:`Fedora-Account-System` has a :term:`JSON` interface that we make use
of to authenticate users in our web apps.  Currently, there are two modes of
operation.  Some web apps have :term:`single sign-on` capability with
:ref:`FAS`.  These are the :term:`TurboGears` applications that use the
:mod:`~fedora.tg.identity.jsonfasprovider`.  Other apps do not have
:term:`single sign-on` but they do connect to :ref:`FAS` to verify the
username and password so changing the password in :ref:`FAS` changes it
everywhere.

.. _jsonfas2:

TurboGears Identity Provider 2
==============================

An identity provider with :term:`CSRF` protection.

This will install as a TurboGears identity plugin.  To use it, set the
following in your :file:`APPNAME/config/app.cfg` file::

    identity.provider='jsonfas2'
    visit.manager='jsonfas2'


.. seealso:: :ref:`CSRF-Protection`

.. automodule:: fedora.tg.identity.jsonfasprovider2
    :members: JsonFasIdentity, JsonFasIdentityProvider
    :undoc-members:

.. automodule:: fedora.tg.visit.jsonfasvisit2
    :members: JsonFasVisitManager
    :undoc-members:

.. _jsonfas1:

Turbogears Identity Provider 1
==============================

These methods are **deprecated** because they do not provide the :term:`CSRF`
protection of :ref:`jsonfas2`.  Please use that identity provider instead.

.. automodule:: fedora.tg.identity.jsonfasprovider1
    :members: JsonFasIdentity, JsonFasIdentityProvider
    :undoc-members:
    :deprecated:

.. automodule:: fedora.tg.visit.jsonfasvisit1
    :members: JsonFasVisitManager
    :undoc-members:
    :deprecated:

.. _djangoauth:

Django Authentication Backend
=============================
.. toctree::
    :maxdepth: 2

    django

.. _faswho:

FAS Who Plugin for TurboGears2
==============================
.. toctree::
    :maxdepth: 2

    faswho
