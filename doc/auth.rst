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

TurboGears Identity Provider
============================
.. automodule:: fedora.tg.identity.jsonfasprovider
    :members: JsonFasIdentity, JsonFasIdentityProvider
    :undoc-members:

.. automodule:: fedora.tg.visit.jsonfasvisit
    :members: JsonFasVisitManager
    :undoc-members:

Django Authentication Backend
=============================
.. toctree::
    :maxdepth: 2

    django
