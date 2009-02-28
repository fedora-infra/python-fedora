.. _JavaScript:

==========
JavaScript
==========

:Authors: Toshio Kuratomi
:Date: 26 February 2009
:For Version: 0.3.x

python-fedora currently provides some JavaScript files to make coding
:ref:`Fedora-Services` easier.  In the future we may move these to their own
package.

------------------
:mod:`fedora.dojo`
------------------

.. module:: fedora.dojo
    :synopsis: JavaScript helper scripts using Dojo
.. moduleauthor:: Toshio Kuratomi <tkuratom@redhat.com>
.. versionadded:: 0.3.10

:term:`Dojo` is one of several JavaScript Toolkits.  It aims to be a standard
library for JavaScript.  The :mod:`fedora.dojo` module has JavaScript code
that make use of :term:`Dojo` to do their work.  It is most appropriate to use
when the :term:`Dojo` libraries are being used as the JavaScript library for
the app.  However, it is well namespaced and nothing should prevent it from
being used in other apps as well.

.. class::dojo.BaseClient(base_url, kw=[useragent, username, password, debug])

    A client configured to make requests of a particular service.

    :arg base_url: Base of every URL used to contact the server
    :kwarg useragent: useragent string to use.  If not given, default
        to "Fedora DojoClient/VERSION"
    :kwarg username: Username for establishing authenticated connections
    :kwarg password: Password to use with authenticated connections
    :kwarg debug: If True, log debug information Default: false


