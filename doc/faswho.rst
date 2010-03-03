=============
FASWho Plugin
=============
:Authors: Luke Macken
          Toshio Kuratomi
:Date: 11 Dec 2009

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
requires one change to be made to :file:`app/config/app_cfg.py`.

.. autofunction:: fedora.tg.tg2utils.add_fas_auth_middleware

This function will take care of registering faswho as the authentication
provider, enabling CSRF protection, switching :func:`tg.url` to use
:func:`fedora.tg.tg2utils.url` instead, and allowing the `_csrf_token`
parameter to be given to any URL.

---------------------------------------------
Using CSRF middleware with other Auth Methods
---------------------------------------------

This section needs to be made clearer so that apps like mirrormanager can be
ported to use this.

.. automodule:: fedora.wsgi.csrf
.. autoclass:: fedora.wsgi.csrf.CSRFProtectionMiddleware
.. autoclass:: fedora.wsgi.csrf.CSRFMetadataProvider
