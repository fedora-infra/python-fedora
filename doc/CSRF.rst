.. _CSRF-Protection:

===============
CSRF Protection
===============

:Authors: Toshio Kuratomi
:Date: 21 February 2009
:For Version: 0.3.x

.. currentmodule:: fedora.tg.utils

:term:`CSRF`, Cross-Site Request Forgery is a technique where a malicious
website can gain access to a Fedora Service by hijacking a currently open
session in a user's web browser.  This technique affects identification via SSL
Certificates, cookies, or anything else that the browser sends to the server
automatically when a request to that server is made.  It can take place over
both GET and POST.  GET requests just need to hit a vulnerable URL.  POST
requests require JavaScript to construct the form that is sent to the
vulnerable server.

.. note::
    If you just want to implement this in :ref:`Fedora-Services`, skip to the
    `Summary of Changes Per App`_ section

--------------
How CSRF Works
--------------

1) A vulnerable web service allows users to change things on their site using
   just a cookie for authentication and submission of a form or by hitting a
   URL with an ``img`` tag.

2) A malicious website is crafted that looks harmless but has JavaScript or an
   ``img`` tag that sends a request to the web service with the form data or
   just hits the vulnerable URL.

3) The user goes somewhere that people who are frequently logged into the site
   are at and posts something innocuous that gets people to click on the link
   to the malicious website.

4) When a user who is logged into the vulnerable website clicks on the link,
   their web browser loads the page.  It sees the img tag and contacts the
   vulnerable website to request the listed URL *sending the user's
   authentication cookie automatically*.

5) The vulnerable server performs the action that the URL requires as the
   user whose cookies were sent and the damage is done... typically without
   the user knowing any better until much later.

-----------------
How to Prevent It
-----------------

Theory
======

In order to remove this problem we need to have a shared secret between the
user's browser and the web site that is only available via the http
request-response.  This secret is required in order for any actions to be
performed on the site.  Because the :term:`Same Origin Policy` prevents the
malicious website from reading the web page itself, a shared secret passed in
this manner will prevent the malicious site from performing any actions.
Note that this secret cannot be transferred from the user's browser to the
server via a cookie because this is something that the browser does
automatically.  It can, however, be transferred from the server to the browser
via a cookie because the browser prevents scripts from other domains from
*reading* the cookies.

Practice
========

The strategy we've adopted is sometimes called :term:`double submit`.  Every
time we POST a form or make a GET request that requires us to be authenticated
we must also submit a token consisting of a hash of the ``tg-visit`` to show
the server that we were able to read either the cookie or the response from a
previous request.  We store the token value in a GET or POST parameter named
``_csrf_token``.  If the server receives the ``tg-visit`` without the
``_csrf_token`` parameter, the server renders the user anonymous until the
user clicks another link.

.. note::
   We hash the ``tg-visit`` session to make the token because we sometimes
   send the token as a parameter in GET requests so it will show up in the
   servers http logs.

Verifying the Token
-------------------

The :mod:`~fedora.tg.identity.jsonfasprovider1` does the work of
verifying that ``_csrf_token`` has been set and that it is a valid hash of the
``tg-visit`` token belonging to the user.  The sequence of events to verify a
user's identity follows this outline:

1) If username and password given

  1. Verify with the identity provider that the username and password match

    1) [YES] authenticate the user
    2) [NO] user is anonymous.

2) if tg-visit cookie present

  1. if session_id from ``tg-visit`` is in the db and not expired and
     (sha1sum(``tg-visit``) matches ``_csrf_token`` given as a (POST variable
     or GET variable)

    1) [YES] authenticate the user
    2) [NO] Take user to login page that just requires the user to click a
       link.  Clicking the link shows that it's not just JavaScript in the
       browser attempting to load the page but an actual user.  Once the link
       is clicked, the user will have a ``_csrf_token``.  If the link is not
       clicked the user is treated as anonymous.

  2. Verify via SSL Certificate

    1) SSL Certificate is not revoked and  able to retrieve info for the
       username and (sha1sum(``tg-visit``) matches ``_csrf_token`` given as a
       POST variable or GET variable)

     1. [YES] authenticate the user
     2. [NO] Take user to login page that just requires the user to click a
        link.  Clicking the link shows that it's not just JavaScript in the
        browser attempting to load the page but an actual user.  Once the link
        is clicked, the user will have a ``_csrf_token``.  If the link is not
        clicked the user is treated as anonymous.

This work should mostly happen behind the scenes so the application programmer
does not need to worry about this.

.. seealso:: The :mod:`~fedora.tg.identity.jsonfasprovider1`
   documentation has more information on methods that are provided by the
   identity provider in case you do need to tell what the authentication token
   is and whether it is missing.

Getting the Token into the Page
-------------------------------

Embedding the :term:`CSRF` token into the URLs that the user can click on is
the other half of this problem.  :mod:`fedora.tg.utils` provides two
functions to make this easier.

.. autofunction:: url

This function does everything :func:`tg.url` does in the templates.  In
addition it makes sure that ``_csrf_token`` is appended to the URL.

.. autofunction:: enable_csrf

This function sets config values to allow ``_csrf_token`` to be passed to any
URL on the server and makes :func:`turbogears.url` point to our :func:`url`
function.  Once this is run, the :func:`tg.url` function you use in the
templates will make any links that use with it contain the :term:`CSRF`
protecting token.

Intra-Application Links
~~~~~~~~~~~~~~~~~~~~~~~

We support single sign-on among the web applications we've written for Fedora.
In order for this to continue working with this :term:`CSRF` protection scheme
we have to add the ``_csrf_token`` parameter to links between
:ref:`Fedora-Services`.  Linking from the PackageDB to Bodhi, for instance,
needs to have the hash appended to the URL for Bodhi.  Our :func:`url`
function is capable of generating these by passing the full URL into the
function like this::

    <a href="${tg.url('https://admin.fedoraproject.org/updates')}">Bodhi</a>

.. note::

   You probably already use :func:`tg.url` for links within you web app to
   support :attr:`server.webpath`.  Adding :func:`tg.url` to external links is
   new.  You will likely have to update your application's templates to call
   :func:`url` on these URLs.

Logging In
----------

Each app's :meth:`login` controller method and templates need to be modified
in several ways.

.. _CSRF-Login-Template:

Templates
~~~~~~~~~

For the templates, python-fedora provides a set of standard templates that can
be used to add the token.

.. automodule:: fedora.tg.templates.genshi

Using the ``<loginform>`` template will give you a login form that
automatically does several things for you.

1. The ``forward_url`` and ``previous_url`` parameters that are passed in
   hidden form elements will be run through :func:`tg.url` in order to get the
   ``_csrf_token`` added.
2. The page will allow "Click through validation" of a user when they have a
   valid ``tg-visit`` but do not have a ``_csrf_token``.

Here's a complete login.html from the pkgdb to show what this could look
like::

  <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
  <html xmlns="http://www.w3.org/1999/xhtml"
        xmlns:py="http://genshi.edgewall.org/"
        xmlns:xi="http://www.w3.org/2001/XInclude">
    <xi:include href="master.html" />
    <xi:include href="${tg.fedora_template('login.html')}" />

    <head>
      <meta content="text/html; charset=UTF-8"
      http-equiv="content-type" py:replace="''"/>
      <title>Login to the PackageDB</title>
    </head>

    <body>
      <loginform>${message}</loginform>
    </body>
  </html>

You should notice that this looks like a typical genshi_ template in your
project with two new features.  The ``<loginform>`` tag in the body that's
defined in :mod:`fedora.tg.templates.genshi` is used in the body to pull in
the login formand the ``<xi:include>`` of :file:`login.html`
uses :func:`tg.fedora_template` to load the template from python-fedora.
This function resides in :mod:`fedora.tg.utils` and is added to the
``tg`` template variable when :func:`~fedora.tg.utils.enable_csrf` is
called at startup.  It does the following:

.. currentmodule:: fedora.tg.utils

.. autofunction:: fedora_template

.. _genshi: http://genshi.edgewall.org
.. _`genshi match template`: http://genshi.edgewall.org/wiki/Documentation/0.5.x/xml-templates.html#py:match

The second match template in :file:`login.html` is to help you modify the
login and logout links that appear at the top of a typical application's page.
This is an optional change that lets the links display a click-through login
link in addition to the usual login and logout.  To use this, you would follow
the example to add a ``toolbar`` with the ``<logintoolitem>`` into your master
template.  Here's some snippets from a :file:`master.html` to illustrate::

  <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
  <html xmlns="http://www.w3.org/1999/xhtml"
        xmlns:py="http://genshi.edgewall.org/"
        xmlns:xi="http://www.w3.org/2001/XInclude">

  [...]
    <body py:match="body" py:attrs="select('@*')">
  [...]
      <div id="head">
        <h1><a href="http://fedoraproject.org/index.html">Fedora</a></h1>
        <ul class="toolbar" id="#main-toolbar">
          <logintoolitem href="${tg.url('/users/info')}" />
        </ul>
      </div>
  [...]
    </body>
    <xi:include href="${tg.fedora_template('login.html')}" />
    <xi:include href="${tg.fedora_template('jsglobals.html')}" />
  </html>

.. warning::

    Notice that the ``<xi:include>`` of :file:`login.html` happens after the
    ``<body>`` tag?  It is important to do that because the ``<body>`` tag in
    :file:`master.html` is a match template just like ``<logintoolitem>``.  In
    genshi_, the order in which match templates are defined is significant.

If you need to look at these templates to modify them yourself (perhaps to
port them to a different templating language) you can find them in
:file:`fedora/tg/templates/genshi/login.html` in the source tarball.

.. _CSRF-controller-methods:

Controllers
~~~~~~~~~~~

Calling :ref:`Fedora-Services` from JavaScript poses one further problem.
Sometimes the user will not have a current :term:`CSRF` token and will need to
log in.  When this is done with a username and password there's no
problem because the username and password are sufficient to prove the user is
in control of the browser.  However, when using an SSL Certificate, we need
the browser to log in and then use the new :term:`CSRF` token to show the user
is in control.  Since JavaScript calls are most likely going to request the
information as JSON, we need to provide the token in the dict returned from
:meth:`login`.  You can either modify your :meth:`login` method to do that or
use the one provided in :func:`fedora.tg.controllers.login`.

.. note::

   Fedora Services do not currently use certificate authentication but doing
   it would not take much code.  Working out the security ramifications within
   Infrastructure is the main sticking point to turning this on.

.. note::
   The `Fedora Account System <https://admin.fedoraproject.org/accounts/>`_
   has a slightly different login() method.  This is because it has to handle
   account expiration, mandatory password resets, and other things tied to the
   status of an account.  Other Fedora Services rely on FAS to do this instead
   of having to handle it themselves.

.. automodule:: fedora.tg.controllers
    :members:

AJAX
====

Making JavaScript calls requires that we can get the token and add it to the
URLs we request.  Since JavaScript doesn't have a standard library of crypto
functions we provide the token by setting it via a template so we do not have
to calculate it on the client.  This has the added bonus of propagating a
correct token even if we change the hash function later.  Making use of the
token can then be done in ad hoc JavaScript code but is better handled via a
dedicated JavaScript method like the :class:`fedora.dojo.BaseClient`.

Template
--------

.. automodule:: fedora.tg.templates.genshi.jsglobals

.. warning::
    Just like :file:`login.html`, the ``<xi:include>`` tag needs to come after
    the ``<body>`` tag since they're both match templates.


JavaScript
----------

The :class:`fedora.dojo.BaseClient` class has been modified to send and update
the csrf token that is provided by fedora.identity.token.  It is highly
recommended that you use this library or another like it to make all calls to
the server.  This keeps you from having to deal with adding the :term:`CSRF`
token to every call yourself.

Here's a small bit of sample code::

    <script type="text/javascript" src="/js/dojo/dojo.js"></script>
    <script type="text/javascript">
        dojo.require('fedora.dojo.BaseClient');
        dojo.addOnLoad(function() {
            pkgdb = new fedora.dojo.BaseClient(fedora.baseurl, {
                username: '', password:''});
            pkg_data = pkgdb.start_request('/packages/name/python',
                {req_params: {collectionName: 'Fedora',
                        collectionVersion: 'devel'}});

        });
    </script>

--------------------------
Summary of Changes Per App
--------------------------

 * On startup, run :func:`~fedora.tg.utils.enable_csrf`.  This could be
   done in a start-APP.py and APP.wsgi scripts.  Code like this will do it::

    from turbogears import startup
    from fedora.tg.utils import enable_csrf
    startup.call_on_startup.append(enable_csrf)

 * Links to other :ref:`Fedora-Services` in the templates must be run through
   the :func:`tg.url` method so that the :term:`CSRF` token can be appended.

 * You must use an updated login template.  Using the one provided in
   python-fedora is possible by changing your login template as shown in the
   :ref:`CSRF-login-template` section.

 * Optional: update the master template that shows the Login/Logout Link to
   have a "Verify Login" button.  You can add one to a toolbar in your
   application following the instructions in the :ref:`CSRF-login-template`
   section.

 * Use an updated identity provider from python-fedora.  At this time, you
   need python-fedora 0.3.10 or later which has a
   :mod:`~fedora.tg.identity.jsonfasprovider2` and
   :mod:`~fedora.tg.visit.jsonfasvisit2` that provide :term:`CSRF` protection.
   The original :mod:`~fedora.tg.identity.jsonfasprovider1` is provided for
   applications that have not yet started using
   :func:`~fedora.tg.utils.enable_csrf` so you have to make this change in
   your configuration file (:file:`APPNAME/config/app.cfg`)

 * Get the :term:`CSRF` token into your forms and URLs.  The recommended way
   to do this is to use :func:`tg.url` in your forms for URLs that are local
   to the app or are for :ref:`Fedora-Services`.

 * Update your :meth:`login` method to make sure you're setting
   ``forward_url = request.path_info`` rather than ``request.path``.  One easy
   way to do this is to use the :meth:`~fedora.tg.controllers.login` and
   :meth:`~fedora.tg.controllers.logout` as documented in
   :ref:`CSRF-controller-methods`

 * Add the token and other identity information so JavaScript can get at it.
   Use the :mod:`~fedora.tg.templates.genshi.jsglobals` template to accomplish
   this.

**This one still needs to be implemented**
 * AJAX calls need to be enhanced to append the CSRF token to the data.  This
   is best done using a JavaScript function for this like the
   :class:`fedora.dojo.BaseClient` library.
