'''
Genshi version of templates to make adding certain Fedora widgets easier.

---------------------------------------------
:mod:`fedora.tg2.templates.genshi.login.html`
---------------------------------------------
.. module:: fedora.tg2.templates.genshi.login.html
    :synopsis: Templates related to logging in and out.
.. moduleauthor:: Toshio Kuratomi <tkuratom@redhat.com>
.. versionadded:: 0.3.26


Include this using::
    <xi:include href="${fedora_template('login.html', template_type='genshi')}" />

.. function:: loginform([message])

:message: Any text or elements contained by the <loginform> tag will be shown
    as a message to the user.  This is generally used to show status of the
    last login attempt ("Please provide your credentials", "Supplied
    credentials were not correct", etc)

A match template for the main login form.  This is a :term:`CSRF` token-aware
login form that will prompt for username and password when no session identity
is present and ask the user to click a link if they merely lack a token.

Typical usage would be::

    <loginform>${message}</loginform>

.. function:: logintoolitem(@href=URL)

:@href: If an href attribute is present for this tag, when a user is
    logged in, their username or display_name will be a link to the URL.

A match template to add an entry to a toolbar.  The entry will contain the
user's username and a logout button if the user is logged in, a verify login
button if the user has a session cookie but not a :term:`CSRF` token, or a
login button if the user doesn't have a session cookie.

Typical usage looks like this::

    <ul class="toolbar" id="#main-toolbar">
      <logintoolitem href="${tg.url('/users/info')}" />
    </ul>

-------------------------------------------------
:mod:`fedora.tg2.templates.genshi.jsglobals.html`
-------------------------------------------------
.. module:: fedora.tg2.templates.genshi.jsglobals.html
    :synopsis: Templates to get information into javascript
.. moduleauthor:: Toshio Kuratomi <tkuratom@redhat.com>
.. versionadded:: 0.3.26


Include this using::
    <xi:include href="${fedora_template('jsglobals.html', template_type='genshi')}" />

.. function:: jsglobals()

A match template to add global variables to a page.  Typically, you'd include
this in your :file:`master.html` template and let it be added to every other
page from there.  This adds the following variables in the fedora namespace
for other scripts to access:

    :fedora.baseurl: URL fragment to prepend to any calls to the application.
        In a :term:`TurboGears` application, this is the scheme, host, and
        server.webpath.  Example: https://admin.fedoraproject.org/pkgdb/.
        This may be a relative link.
    :fedora.identity.anonymous: If ``true``, there will be no other variables
        in the `fedora.identity` namespace.  If ``false``, these variables are
        defined:
    :fedora.identity.userid: Numeric, unique identifier for the user
    :fedora.identity.username: Publically visible unique identifier for the
        user
    :fedora.identity.display_name: Common human name for the user
    :fedora.identity.token: csrf token for this user's session to be added to
        urls that query the server.

Typical usage would be::

    <jsglobals />
'''
