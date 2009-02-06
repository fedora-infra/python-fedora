.. _CSRF-Protection:

===============
CSRF Protection
===============

:Authors: Toshio Kuratomi
:Date: 02 February 2009
:For Version: 0.3.x

.. currentmodule::
   fedora.tg.util

:term:`CSRF`, Cross-Site Request Forgery is a technique where a malicious
website can gain access to a Fedora Service by hijacking a currently open
session in a user's web browser.  This technique affects identification via SSL
Certificates, cookies, or anything else that the browser sends to the server
automatically when a request to that server is made.  It can take place over
both GET and POST.  GET requests just need to hit a vulnerable URL.  POST
requests require JavaScript to construct the form that is sent to the
vulnerable server.

.. note::

   If you just want to implement this in :ref:`Fedora-Service`, skip to the
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

The :mod:`~fedora.tg.identity.jsonfasprovider` does the work of
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

.. seealso:: The :mod:`~fedora.tg.identity.jsonfasprovider`
   documentation has more information on methods that are provided by the
   identity provider in case you do need to tell what the authentication token
   is and whether it is missing.

Getting the Token into the Page
-------------------------------

Embedding the :term:`CSRF` token into the URLs that the user can click on is
the other half of this problem.  :mod:`fedora.tg.util` provides two functions
to make this easier.

.. autofunction::
   url

This function does everything :func:`tg.url` does in the templates.  In
addition it makes sure that ``_csrf_token`` is appended to the URL.

.. autofunction::
   enable_csrf

This function sets config values to allow ``_csrf_token`` to be passed to any
any URL on the server and makes :func:`turbogears.url` point to our
:func:`url` function.  Once this is run, the :func:`tg.url` function you use
in the templates will make any links that use with it contain the :term:`CSRF`
protecting token.

Intra-Application Links
~~~~~~~~~~~~~~~~~~~~~~~

We support single sign-on among the web applications we've written for Fedora.
In order to continue to do this With this :term:`CSRF` protection scheme we
have to add the ``_csrf_token`` parameter to links between
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

Each app's :meth:`login` page needs to be modified in several ways.

The ``forward_url`` and ``previous_url`` parameters that are passed in hidden
form elements need to be run through :func:`tg.url` in order to get the
``_csrf_token`` added.  The page needs to be updated to allow "Click through
validation" when a user has a valid :var:`tg-visit` but does not have a
``_csrf_token``.  These can be enabled by using the login form from
:mod:`fedora.tg.templates.login`

FIXME: More information and examples here.

Using AJAX and SSL certificate authentication with the login methods there is
one further problem.  Using SSL certificates (rather than username and
password, which is sufficient), we can login using a two step process of going
to the login page and retrieving the token from there.  However, as we request
json data from the login method, we need to make that token available in the
data returned from json.  This can be 

If you aren't doing anything out of the ordinary in your login method, you can
use :func:`fedora.tg.controllers.login` to enable both of these.

.. note::

   Fedora Services do not currently use certificate authentication but doing
   it would not take much code.  Working out the security ramifications within
   Infrastructure is the main sticking point to turning this on.

.. note::
   The `Fedora Account System <https://admin.fedoraproject.org/accounts/>`_ has a slightly different login() method.  This is because it has to handle account expiration, mandatory password resets, and other things tied to the status of an account.  Other Fedora Services rely on FAS to do this instead of us.

certificate authentication
For SSL authentication, with AJAX methods, a two step process is needed.  Step
one is for the user to 
the body of the response.  This way when we use SSL auth in an AJAX method,
the AJAX call will be able to retrieve the token and use it in subsequent
calls to the app.

Without this, username/password auth will still work (since username/password
is sufficient to tell that it wasn't the browser acting alone) but SSL
Certificate Authentication will not.

The login() page (or another URL) will have to be modified to distinguish the
lack of csrf_token but presence of tg-visit and return a click-through page in
that case.

WebUI
=====

The WebUI must make sure that it sends back the token with every
call.  For AJAX calls, this can be abstracted into the JavaScript BaseClient.
For standard links on a page (for instance, the link in FAS to get a new
certificate), or GET requests in FAS, it makes more sense for the server to
make the links.

So static resources like links should have the token appended to the URL as a
query parameter.  The easiest way for us to do this is to override the
tg.url() method to add the necessary query parameter to the end of the URL::

  <a href="${tg.url('/packages/dispatcher/do_action')}">

becomes::

  <a href="https://admin.fedoraproject.org/pkgdb/packages/dispatcher/do_action?_csrf_token=0123456789ABCDEF">

Static forms could be done with a hidden field but it's probably easier to
override the method attribute::

  <form action="POST" method="${tg.url('/packages/dispatcher/do_action')}">

becomes::

  <form action="POST"
    method="https://admin.fedoraproject.org/pkgdb/packages/dispatcher/do_action?_csrf_token=admin0123456789ABCDE">

AJAX calls should all be made through an API method.  The API method can take
care of adding the token to the data returned to the server.  The server will
add the hash of the tg-visit cookie to identity.current.token so that it's
available to the template.  It is highly recommended that the master template
for the web app make this variable available to the JavaScript so that every
page has access to it.  Here's a sample of doing that from the pkgdb::

    <script type="text/javascript" py:if="not tg.identity.anonymous">
      tg = {userid: "${tg.identity.user.id}",
        username: "${tg.identity.user.username}",
        display_name: "${tg.identity.user.human_name}",
        token: "${tg.identity.token}",
        anonymous: false
      };
    </script>
    <script type="text/javascript">
      if (typeof(tg) == 'undefined') {
        tg = {anonymous: true};
      }
      tg.baseurl = "${tg.url('/')}".slice(0, -1);
    </script>

The fedora.dojo.BaseClient.start_request() method is one example of an API
method we can use this way.

python-fedora
=============

send_request() in :class:`~fedora.client.ProxyClient` can be adapted to send
the session key to the server.  Note that we shouldn't have to ever revert to
sending username and password once to get the session key because username +
password is sufficient.  The session_key addition is only necessary when we
only have the session key and not a password.

When we implement SSL certificate authentication in python-fedora we will have
a problem here.  Without a valid session_id we still need to have the user's
password in order to authenticate.  With the user's password we have no need to
use SSL certificate auth.  It is possible for us to not expire the _csrf_token
parameter in which case we can simply create a fake _csrf_token and tg-visit to
send with SSL certificate auth.  However, this makes browser-based
Authentication weaker.  Barring browser bugs, it should still be safe since the
web browser should just send the cookie that is stored for the domain, not
allow the malicious page to change it.


== Notes ==

Adding the token information to links on the application page is a tad messy
as it means that copying and pasting a link will include the _csrf_token.  If
we used JavaScript instead of static URLs this could be avoided but we'd have
to figure out how to modify the page templates for this.

Summary of Changes Per App
--------------------------

This section is a work in progress.  As I implement this for a few apps I'll
add the changes that web application authors need to implement in order to be
protected against :term:`CSRF`.  When that is done, this paragraph will be
removed.

These have been implemented:

 * On startup, run :func:`~fedora.tg.util.enable_csrf`.  Code like this will
   do it::

    from turbogears import startup
    from fedora.tg.util import enable_csrf
    startup.call_on_startup.append(enable_csrf)

 * Links to other :ref:`Fedora-Services` in the templates must be run through
   the :func:`tg.url` method.

 * You must use an updated login template.  One that works is checked into the
   fas repository, :term:`CSRF` branch.  I'm working out whether we'll place a
   copy into python-fedora or have some other way of using it.

 * Optional: update the master template that show the Login/Logout Link to
   have a "Verify Login" button (better name?)  If the user clicks it
   redirects to the current page with the :term:`CSRF` token.  This is
   controlled with a check of tg.identity.only_token.This is also in the fas
   repository, :term:`CSRF` branch and we're working out how to give everyone
   access to this.

These have not been implemented:

 * Use an updated identity provider from python-fedora.  At this time, the plan
   is to have a minimum version of python-fedora that provides the necessary
   functionality.  We could also define a new version of the
   :mod:`~fedora.tg.identity.jsonfasprovider`  if necessary.

 * Get the :term:`CSRF` token into your forms and URLs.  The recommended way
   to do this is to override the ``tg.url()`` method in your forms with the
   one provided in :func:`~fedora.tg.util.url`.

2) Change the login template to the one in fas
3) Check your :func:`login` method to make sure you are setting ``forward_url
   = request.path_info``, not ``request.path``
5) AJAX calls need to be enhanced to append the CSRF token to the data.  This
   is best done using a JavaScript function for this like the
   fedora.dojo.BaseClient library.
