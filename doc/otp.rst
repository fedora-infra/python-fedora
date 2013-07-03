=====================================
Client Support for One Time Passwords
=====================================
:Authors: Toshio Kuratomi
:Date: 2 July 2013
:For Version: 0.3.x

The python-fedora client API supports the use of :term:`one time password`s
(:term:`otp`) if the server that you are authenticating against supports them.
The API in python-fedora for using :term:`otp` is structured so that
applications which know nothing about :term:`otp`s will work seamlessly with
the servers but at a slight performance penalty.  Applications which know that
they may be dealing with :term:`otp`s can be coded to remove this performance
penalty for a bit of additional code.

This overview of the API will start by explaining the support in
:class:`fedora.client.ProxyClient` and then talk about how
:class:`fedora.client.BaseClient` adds session state on top of that layer.
Client code that wants to handle :term:`otp`s in a stateful manner can either
subclass :class:`~fedora.client.BaseClient` directly or replicate its strategy
for handing :term:`otp`s off to :class:`~fedora.client.ProxyClient` 

----------------
Oblivious Method
----------------

If the client code knows nothing about :term:`otp`s then they will simply ask
for a username and password.  A user that wishes to use a :term:`otp` will
append the otp to the password.  This combined password+otp string will be
passed onto the server by :meth:`fedora.client.ProxyClient.send_request`.  If
both of the pieces are valid, the server will log the user in and return a
``session_id`` for the logged in user.  If one or both of the pieces are
invalid, the server will return a 403 http response code to indicate an error.
If the API receives a 403 from sending the username and password, it will then
try sending a ``session_id`` if it has given one.  If the API receives a 403
from this as well, thenit will translate this into a
:exc:`fedora.client.AuthError` which can be caught by the calling client code.

This means that there is an inherent inefficiency for users who have an
:term:`otp` setup exists.  The first time they use the API, their password+otp
will serve to authenticate them and get them a session_id.  Subsequent uses of
the API will first attempt to pass in their saved password+otp which will fail.
It will then use the session_id which should work (provided that their session
hasn't timed out).

.. warning:: Because we try both the ``session_id`` and username and password
    it is possible for someone with a saved ``session_id`` to give an
    incorrect username and password and still be authenticated.  Similarly, if
    your code is saving state but switching between users (for instance,
    sharing a :class:`~fedora.client.BaseClient` derived object for requests
    for multiple users), the code **must** remove the ``session_id`` from
    the :class:`~fedora.client.BaseClient` between users otherwise, if the new
    username and password are invalid, the user who is associated with the
    ``session_id`` will be used for the new query instead of the one associated
    with the new username and password.

.. note:: We thought about reversing the order in which we called the server
    to send the ``session_id`` first and the username and password+otp if that
    failed.  This would have less inefficient cases (would only make extra
    calls when the session_id has expired) but it would change one of the
    assumptions of the API, that passing in a new username and password will
    override any current ``session_id``.  This could have ramifications on
    many critical pieces of code:

        * Code that assumed it could reuse an existing
          :class:`~fedora.client.BaseClient` with a new username and password
          would continue to use the user associated with the ``session_id``
          even if the new username and password were valid.

        * ``session_id`` is stored on disk.  In case of a corrupted
          ``session_id`` causing issues we want a fresh username and password
          which are easily entered by a user to take precedence over that.

---------
Smart API
---------

To combat this inefficiency, client code which is specifically coded with
:term:`otp`s in mind can make use of additional parameters to the API to
inform the API that an :term:`otp` is being used.  The client code needs to
get the password and :term:`otp` separately from the user and store them in
separate fields (:class:`~fedora.client.BaseClient` derived objects can be
used for this.)  When the first request for a server API is made, the client
code will pass the username, password, and otp to
:meth:`fedora.client.ProxyClient.send_request` as separate entries in the
:attr:`auth_params` parameter.
:meth:`~fedora.client.ProxyClient.send_request` will send the username,
password, and otp to the server to authenticate the user, returning
:exc:`fedora.client.AuthError` if any of those is invalid.  If all the tokens
are valid, then the request succeeds.  No second try is made with the
``session_id`` if the username+password+otp combination is invalid as the
explicit presence of the otp field lets the API decide that these are to be
used in place of the session_id.


Sentinel Values and Stateful Clients
====================================

:class:`fedora.client.ProxyClient` is meant to be stateless.  It doesn't keep
any information between invocations of
:meth:`~fedora.client.ProxyClient.send_request`.  This makes it easy to map
the usage of :term:`one time passwords` to the :attr:`otp` field of
auth_params.  However, it is often useful to have a stateful API that keeps
track of the``session_id``, username and password between requests.  How do we
manage those with :term:`otp`s?  We can look at how
:class:`fedora.client.BaseClient` is implemented to understand that.

:class:`~fedora.client.BaseClient` can take a username, password, and
:term:`otp` when the object is created and stores these in similarly named
instance attributes.  The first time the `:class:`~fedora.client.BaseClient`
object makes a request to the server, it sends these credentials to
:class:`~fedora.client.ProxyClient` to authenticate the user.  The moment that
it commits to using the :term:`otp`, :class:`~fedora.client.BaseClient` sets
the :attr:`otp` attribute to :attr:`fedora.client.OTP_MAP`['USED'].  If
authentication was successful, the server returns a ``session_id`` that can be
used to authenticate the user for a short time.  On subsequent calls to the
server, :class:`~fedora.client.BaseClient` sends both this ``session_id`` and
the username, password, and an otp value of
:attr:`fedora.client.OTP_MAP`['USED'] to :class:`~fedora.client.ProxyClient`.
:class:`~fedora.client.ProxyClient` will recognize
:attr:`fedora.client.OTP_MAP`['USED'] as a sentinel value that means it should
only try to use the given ``session_id`` for authenticating as the username
and password cannot be used to authenticate until a new :term:`otp` is
generated and added to the client by the user.

If a username and password was provided to :class:`~fedora.client.BaseClient`
but no :term:`otp` then :attr:`fedora.client.OTP_MAP`['OTP_UNDEFINED'] is sent
as the :term:`otp` value which tells :class:`~fedora.client.ProxyClient` to
first try the username and password

