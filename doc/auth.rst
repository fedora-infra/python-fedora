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


.. _flask_fas:

Flask Auth Plugin
=================

.. toctree::
    :maxdepth: 2

    flask_fas

.. _flaskopenid:

Flask FAS OpenId Auth Plugin
============================

The flask_openid provider is an alternative to the flask_fas auth plugin.  It
leverages our FAS-OpenID server to do authn and authz (group memberships).
Note that not every feature is available with a generic OpenID provider -- the
plugin depends on the OpenID provider having certain extensions in order to
provide more than basic OpenID auth.

* Any compliant OpenID server should allow you to use the basic authn features of OpenID
  OpenID authentication core: http://openid.net/specs/openid-authentication-2_0.html

* Retrieving simple information about the user such as username, human name, email
  is done with sreg: http://openid.net/specs/openid-simple-registration-extension-1_0.html
  which is an extension supported by many providers.

* Advanced security features such as requiring a user to re-login to the OpenID
  provider or specifying that the user login with a hardware token requires
  the PAPE extension:
  http://openid.net/specs/openid-provider-authentication-policy-extension-1_0.html

* To get groups information, the provider must implement the
  https://dev.launchpad.net/OpenIDTeams extension.

  * We have extended the teams extension so you can request a team name of
    ``_FAS_ALL_GROUPS_`` to retrieve all the groups that a user belongs to.
    Without this addition to the teams extension you will need to manually
    configure which groups you are interested in knowing about.  See the
    documentation for how to do so.

* Retrieving information about whether a user has signed a CLA (For Fedora,
  this is the Fedora Project Contributor Agreement).
  http://fedoraproject.org/specs/open_id/cla

If the provider you use does not support one of these extensions, the plugin
should still work but naturally, it will return empty values for the
information that the extension would have provided.

.. toctree::
    :maxdepth: 2

    flask_fas_openid

.. _faswho:

FAS Who Plugin for TurboGears2
==============================
.. toctree::
    :maxdepth: 2

    faswho
