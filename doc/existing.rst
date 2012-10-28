=================
Existing Services
=================

There are many Services in Fedora.  Many of these have an interface that we
can query and get back information as :term:`JSON` data.  There is
documentation here about both the services and the client modules that can
access them.

.. _`Fedora-Account-System`:
.. _`FAS`:

---------------------
Fedora Account System
---------------------

FAS is the Fedora Account System.  It holds the account data for all of our
contributors.

.. toctree::
    :maxdepth: 2

.. autoclass:: fedora.client.AccountSystem
    :members:
    :undoc-members:

Threadsafe Account System Access
================================

It is not safe to use a single instance of the
:class:`~fedora.client.AccountSystem` object in multiple threads.  This is
because instance variables are used to hold some connection-specific
information (for instance, the user who is logging in).  For this reason, we
also provide the :class:`fedora.client.FasProxyClient` object.

This is especially handy when writing authn and authz adaptors that talk to
fas from a multithreaded webserver.

.. toctree::
    :maxdepth: 2

.. autoclass:: fedora.client.FasProxyClient
    :members:
    :undoc-members:

.. _`Package-Database`:
.. _`Pkgdb`:

----------------
Package Database
----------------

The Package Database holds information about packages in Fedora.  It currently
has a developer-centric view of packages that concentrates on who the owner is
of a particular package.

Plans to add an end-user view to packages is ongoing.

.. toctree::
    :maxdepth: 2

.. autoclass:: fedora.client.PackageDB
    :members:
    :undoc-members:

.. _`Bodhi`:

------------------------
Bodhi, the Update Server
------------------------

Bodhi is used to push updates from the build system to the download
repositories.  It lets packagers send packages to the testing repository or to
the update repository.

.. toctree::
    :maxdepth: 2

.. autoclass:: fedora.client.BodhiClient
    :members:
    :undoc-members:
