=================
API Documentation
=================

.. contents:

------
Client
------

.. automodule:: fedora.client
    :members:
    :undoc-members:

.. autoexception:: fedora.client.FASError
    :members:
    :undoc-members:

.. autoexception:: fedora.client.CLAError
    :members:
    :undoc-members:

.. autoexception:: fedora.client.BodhiClientException
    :members:
    :undoc-members:

Generic Clients
===============

BaseClient
----------

.. autoclass:: fedora.client.BaseClient
    :members:
    :undoc-members:

ProxyClient
-----------

.. autoclass:: fedora.client.ProxyClient
    :members:
    :undoc-members:


Clients for Specific Services
=============================

Fedora Account System
----------------------

.. autoclass:: fedora.client.AccountSystem
    :members:
    :undoc-members:

Bodhi
-----

.. autoclass:: fedora.client.BodhiClient
    :members:
    :undoc-members:

Package Database
----------------

.. autoclass:: fedora.client.PackageDBClient
    :members:
    :undoc-members:

-------
Service
-------

Transforming SQLAlchemy Objects into JSON
=========================================
.. automodule:: fedora.tg.json
    :members: jsonify_sa_select_results, jsonify_salist, jsonify_saresult,
        jsonify_set
    :undoc-members:

.. autoclass:: fedora.tg.json.SABase
    :members: __json__
    :undoc-members:

TurboGears Helpers
==================
.. automodule:: fedora.tg.util
    :members:
    :undoc-members:

.. automodule:: fedora.tg.identity
    :members:
    :undoc-members:

.. automodule:: fedora.tg.visit
    :members:
    :undoc-members:
