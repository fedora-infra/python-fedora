============
FASWhoPlugin
============
:Authors: Luke Macken
          Toshio Kuratomi
:Date: 11 Dec 2009

This plugin provdes authenticate to the Fedora Account System using
the `repoze.who` WSGI middleware.

Authenticating against FAS with TurboGears2
-------------------------------------------

Hooking up the FASWhoPlugin entails overwriting the default TurboGears2
`AppConfig.add_auth_middleware` method.

.. code-block:: diff

   --- a/ testtg2/config/app_cfg.py
   +++ b/ testtg2/config/app_cfg.py
   @@ -19,7 +19,13 @@ import testtg2
    from testtg2 import model
    from testtg2.lib import app_globals, helpers 

   -base_config = AppConfig()
   +from fedora.wsgi.faswho import add_fas_auth_middleware
   +
   +class MyAppConfig(AppConfig):
   +    add_auth_middleware = add_fas_auth_middleware
   +
   +base_config = MyAppConfig()
   +
    base_config.renderers = []

    base_config.package = testtg2

