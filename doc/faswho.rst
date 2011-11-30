=============
FASWho Plugin
=============
:Authors: Luke Macken
          Toshio Kuratomi
:Date: 3 September 2011

This plugin provides authentication to the Fedora Account System using the
`repoze.who` WSGI middleware.  It is designed for use with :term:`TurboGears2`
but it may be used with any `repoze.who` using application.  Like
:ref:`jsonfas2`, faswho has builtin :term:`CSRF` protection.  This protection
is implemented as a second piece of middleware and may be used with other
`repoze.who` authentication schemes.

-------------------------------------------
Authenticating against FAS with TurboGears2
-------------------------------------------

Setting up authentication against FAS in :term:`TurboGears2` is very easy.  It
requires one change to be made to :file:`app/config/app_cfg.py`.  This change
will take care of registering faswho as the authentication provider, enabling
:term:`CSRF` protection, switching :func:`tg.url` to use
:func:`fedora.ta2g.utils.url` instead, and allowing the `_csrf_token`
parameter to be given to any URL.

.. autofunction:: fedora.tg2.utils.add_fas_auth_middleware

.. autofunction:: fedora.wsgi.faswho.faswhoplugin.make_faswho_middleware

---------------------------------------------
Using CSRF middleware with other Auth Methods
---------------------------------------------

This section needs to be made clearer so that apps like mirrormanager can be
ported to use this.

.. automodule:: fedora.wsgi.csrf
.. autoclass:: fedora.wsgi.csrf.CSRFProtectionMiddleware
.. autoclass:: fedora.wsgi.csrf.CSRFMetadataProvider

---------
Templates
---------

The :mod:`fedora.tg2.utils` module contains some templates to help you
write :term:`CSRF` aware login forms and buttons.  You can use the
:func:`~fedora.tg2.utils.fedora_template` function to integrate them into your
templates:

.. autofunction:: fedora.tg2.utils.fedora_template

The templates themselves come in two flavors.  One set for use with mako and
one set for use with genshi.

Mako
====

.. automodule:: fedora.tg2.templates.mako

Genshi
======

.. automodule:: fedora.tg2.templates.genshi
