=================
API Documentation
=================

This API Documentation is currently a catch-all.  We're going to merge the API
docs into the hand created docs as we have time to integrate them.

.. toctree::
   :maxdepth: 2

------
Client
------

.. automodule:: fedora.client
    :members: FedoraServiceError, ServerError, AuthError, AppError,
        FedoraClientError, FASError, CLAError, BodhiClientException,
        PackageDBError, DictContainer

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

Wiki
----

.. autoclass:: fedora.client.Wiki
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
