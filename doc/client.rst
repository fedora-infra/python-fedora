=============
Fedora Client
=============
:Authors: Toshio Kuratomi
          Luke Macken
:Date: 28 May 2008
:For Version: 0.3.x

The client module allows you to easily code an application that talks to a
`Fedora Service`_.  It handles the details of decoding the data sent from the
Service into a python data structure and raises an Exception_ if an error is
encountered.

.. _`Fedora Service`: service.html
.. _Exception: Exceptions_

.. toctree::

----------
BaseClient
----------

The :class:`~fedora.client.BaseClient` class is the basis of all your
interactions with the server.  It is flexible enough to be used as is for
talking with a service but is really meant to be subclassed and have methods
written for it that do the things you specifically need to interact with the
`Fedora Service`_ you care about.  Authors of a `Fedora Service`_ are
encouraged to provide their own subclasses of
:class:`~fedora.client.BaseClient` that make it easier for other people to use
a particular Service out of the box.

Using Standalone
================

If you don't want to subclass, you can use :class:`~fedora.client.BaseClient`
as a utility class to talk to any `Fedora Service`_.  There's three steps to
this.  First you import the :class:`~fedora.client.BaseClient` and Exceptions_
from the ``fedora.client`` module.  Then you create a new
:class:`~fedora.client.BaseClient` with the URL that points to the root of the
`Fedora Service`_ you're interacting with.  Finally, you retrieve data from a
method on the server.  Here's some code that illustrates the process::

    from fedora.client import BaseClient, AppError, ServerError

    client = BaseClient('https://admin.fedoraproject.org/pkgdb')
    try:
        collectionData = client.send_request('/collections', auth=False)
    except ServerError, e:
        print '%s' % e
    except AppError, e:
        print '%s: %s' % (e.name, e.message)

    for collection in collectionData['collections']:
        print collection['name'], collection['version']

BaseClient Constructor
~~~~~~~~~~~~~~~~~~~~~~

In our example we only provide ``BaseClient()`` with the URL fragment it uses
as the base of all requests.  There are several more optional parameters that
can be helpful.

If you need to make an authenticated request you can specify the username and
password to use when you construct your :class:`~fedora.client.BaseClient`
using the ``username`` and ``password`` keyword arguments.  If you do not use
these, authenticated requests will try to connect via a cookie that was saved
from previous runs of :class:`~fedora.client.BaseClient`.  If that fails as
well, :class:`~fedora.client.BaseClient` will throw an Exception_ which you
can catch in order to prompt for a new username and password::

    from fedora.client import BaseClient, AuthError
    import getpass
    MAX_RETRIES = 5
    client = BaseClient('https://admin.fedoraproject.org/pkgdb',
            username='foo', password='bar')
    # Note this is simplistic.  It only prompts once for another password.
    # Your application may want to loop through this several times.
    while (count < MAX_RETRIES):
        try:
            collectionData = client.send_request('/collections', auth=True)
        except AuthError, e:
            client.password = getpass.getpass('Retype password for %s: ' % username)
        else:
            # data retrieved or we had an error unrelated to username/password
            break
        count = count + 1

.. warning::

    Note that although you can set the ``username`` and ``password`` as shown
    above you do have to be careful in cases where your application is
    multithreaded or simply processes requests for more than one user with the
    same :class:`~fedora.client.BaseClient`.  In those cases, you can
    accidentally overwrite the ``username`` and ``password`` between two
    requests.  To avoid this, make sure you instantiate a separate
    :class:`~fedora.client.BaseClient` for every thread of control or for
    every request you handle or use :class:`~fedora.client.ProxyClient`
    instead.

The ``useragent`` parameter is useful for identifying in log files that your
script is calling the server rather than another.  The default value is
``Fedora BaseClient/VERSION`` where VERSION is the version of the
:class:`~fedora.client.BaseClient` module.  If you want to override this just
give another string to this::

    client = BaseClient('https://admin.fedoraproject.org/pkgdb',
            useragent='Package Database Client/1.0')

The ``debug`` parameter turns on a little extra output when running the
program.  Set it to true if you're having trouble and want to figure out what
is happening inside of the :class:`~fedora.client.BaseClient` code.

send_request()
~~~~~~~~~~~~~~

``send_request()`` is what does the heavy lifting of making a request of the
server, receiving the reply, and turning that into a python dictionary.  The
usage is pretty straightforward.

The first argument to ``send_request()`` is ``method``. It contains the name
of the method on the server.  It also has any of the positional parameters
that the method expects (extra path information interpreted by the server for
those building non-`TurboGears`_ applications).

The ``auth`` keyword argument is a boolean.  If True, the session cookie for
the user is sent to the server.  If this fails, the ``username`` and
``password`` are sent.  If that fails, an Exception_ is raised that you can
handle in your code.

``req_params`` contains a dictionary of additional keyword arguments for the
server method.  These would be the names and values returned via a form if it
was a CGI.  Note that parameters passed as extra path information should be
added to the ``method`` argument instead.

An example::

    import BaseClient
    client = BaseClient('https://admin.fedoraproject.org/pkgdb/')
    client.send_request('/package/name/python-fedora', auth=False,
            req_params={'collectionVersion': '9', 'collectionName': 'Fedora'})

In this particular example, knowing how the server works, ``/packages/name/``
defines the method that the server is going to invoke.  ``python-fedora`` is a
positional parameter for the name of the package we're looking up.
``auth=False`` means that we'll try to look at this method without having to
authenticate.  The ``req_params`` sends two additional keyword arguments:
``collectionName`` which specifies whether to filter on a single distro or
include Fedora, Fedora EPEL, Fedora OLPC, and Red Hat Linux in the output and
``collectionVersion`` which specifies which version of the distribution to
output for.

The URL constructed by :class:`~fedora.client.BaseClient` to the server could
be expressed as[#]_::

    https://admin.fedoraproject.org/pkgdb/package/name/python-fedora/?collectionName=Fedora&collectionVersion=9

In previous releases of python-fedora, there would be one further query
parameter:  ``tg_format=json``.  That parameter instructed the server to
return the information as JSON data instead of HTML.  Although this is usually
still supported in the server, :class:`~fedora.client.BaseClient` has
deprecated this method.  Servers should be configured  to use an ``Accept``
header to get this information instead.  See the `JSON output`_ section of the
`Fedora Service`_ documentation for more information about the server side.

.. _`TurboGears`: http://www.turbogears.org/
.. _`JSON output`: service.html#selecting-json-output
.. _[#]: Note that the ``req_params`` are actually sent via ``POST`` request
         rather than ``GET``.  Among other things, this means that values in
         ``req_params`` won't show up in apache logs.

Subclassing
===========

Building a client using subclassing builds on the information you've already
seen inside of :class:`~fedora.client.BaseClient`.  You might want to use this
if you want to provide a module for third parties to access a particular
`Fedora Service`_.  A subclass can provide a set of standard methods for
calling the server instead of forcing the user to remember the URLs used to
access the server directly.

Here's an example that turns the previous calls into the basis of a python API
to the `Fedora Package Database`_::

    import getpass
    import sys
    from fedora.client import BaseClient, AuthError

    class MyClient(BaseClient):
        def __init__(self, baseURL='https://admin.fedoraproject.org/pkgdb',
                username=None, password=None,
                useragent='Package Database Client/1.0', debug=None):
            super(BaseClient, self).__init__(baseURL, username, password,
                    useragent, debug)

        def collection_list(self):
            '''Return a list of collections.'''
            return client.send_request('/collection')

        def package_owners(self, package, collectionName=None,
                collectionVersion=None):
            '''Return a mapping of release to owner for this package.'''
            pkgData = client.send_request('/packages/name/%s' % (package),
                    {'collectionName': collectionName,
                    'collectionVersion': collectionVersion})
            ownerMap = {}
            for listing in pkgData['packageListings']:
                ownerMap['-'.join(listing['collection']['name'],
                        listing['collection']['version'])] = \
                        listing['owneruser']
            return ownerMap

A few things to note:

1) In our constructor we list a default ``baseURL`` and ``useragent``.  This
   is usually a good idea as we know the URL of the `Fedora Service`_ we're
   connecting to and we want to know that people are using our specific API.

2) Sometimes we'll want methods that are thin shells around the server methods
   like ``collection_list()``.  Other times we'll want to do more
   post processing to get specific results as ``package_owners()`` does.  Both
   types of methods are valid if they fit the needs of your API.  If you find
   yourself writing more of the latter, though, you may want to consider
   getting a new method implemented in the server that can return results more
   appropriate to your needs as it could save processing on the server and
   bandwidth downloading the data to get information that more closely matches
   what you need.

See ``pydoc fedora.accounts.fas2`` for a module that implements a standard
client API for the `Fedora Account System`_

.. _`Fedora Package Database`: https://fedorahosted.org/packagedb
.. _`Fedora Account System`: https://fedorahosted.org/fas/

---------------
Handling Errors
---------------

:class:`~fedora.client.BaseClient` will throw a variety of errors that can be
caught to tell you what kind of error was generated.

Exceptions
==========

:``FedoraServiceError``: The base of all exceptions raised by
    :class:`~fedora.client.BaseClient`.  If your code needs to catch any of the
    listed errors then you can catch that to do so.

:``ServerError``: Raised if there's a problem communicating with the service.
    For instance, if we receive an HTML response instead of JSON.

:``AuthError``: If something happens during authentication, like an invalid
    usernsme or password, ``AuthError`` will be raised.  You can catch this to
    prompt the user for a new usernsme.

:``AppError``: If there is a `server side error`_ when processing a request,
    the `Fedora Service`_ can alert the client of this by setting certain
    flags in the response.  :class:`~fedora.client.BaseClient`  will see these
    flags and raise an AppError.  The name of the error will be stored in
    AppError's ``name`` field.  The error's message will be stored in
    ``message``.

.. _`server side error`: service.html#Error Handling

Example
=======
Here's an example of the exceptions in action::

    from fedora.client import ServerError, AuthError, AppError, BaseClient
    import getpass
    MAXRETRIES = 5

    client = BaseClient('https://admin.fedoraproject.org/pkgdb')
    for retry in range(0, MAXRETRIES):
        try:
            collectionData = client.send_request('/collections', auth=True)
        except AuthError, e:
            client.username = raw_input('Username: ').strip()
            client.password = getpass.getpass('Password: ')
            continue
        except ServerError, e:
            print 'Error talking to the server: %s' % e
            break
        except AppError, e:
            print 'The server issued the following exception: %s: %s' % (
                    e.name, e.message)

        for collection in collectionData['collections']:
            print collection[0]['name'], collection[0]['version']
