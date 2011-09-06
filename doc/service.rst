.. _Fedora-Services:

===============
Fedora Services
===============
:Authors: Toshio Kuratomi
          Luke Macken
:Date: 02 February 2009
:For Version: 0.3.x

In the loosest sense, a Fedora Service is a web application that sends data
that :class:`~fedora.client.BaseClient` is able to understand.  This document
defines things that a web application must currently do for
:class:`~fedora.client.BaseClient` to understand it.


.. fedora.tg:

------------------------
TurboGears and fedora.tg
------------------------

.. automodule:: fedora.tg

All current Fedora Services are written in :term:`TurboGears`.  Examples in
this document will be for that framework.  However, other frameworks can be
used to write a Service if they can correctly create the data that
:class:`~fedora.client.BaseClient` needs.

A Fedora Service differs from other web applications in that certain URLs for
the web application are an API layer that the Service can send and receive
:term:`JSON` data from for :class:`~fedora.client.BaseClient` to interpret.
This imposes certain constraints on what data can be sent and what data can be
received from those URLs.  The :mod:`fedora.tg` module contains functions that
help you write code that communicated well with
:class:`~fedora.client.BaseClient`.

The :term:`TurboGears` framework separates an application into :term:`model`,
:term:`view`, and :term:`controller` layers.  The model is typically a
database and holds the raw data that the application needs.  The view formats
the data before output.  The controller makes decisions about what data to
retrieve from the model and which view to pass it onto.  The code that you'll
most often need to use from :mod:`fedora.tg` operates on the :term:`controller`
layer but there's also code that works on the model and view behind the scenes.

-----------
Controllers
-----------
.. automodule:: fedora.tg.utils

The :term:`controller` is the code that processes an http request.  It
validates and processes requests and parameters sent by the user, gets data
from the model to satisfy the request, and then passes it onto a view layer to
be returned to the user.  :mod:`fedora.tg.utils` contains several helpful
functions for working with controllers.

-----------
URLs as API
-----------

.. autofunction::
   request_format

.. autofunction::
   jsonify_validation_errors

.. autofunction::
  json_or_redirect

In :term:`TurboGears` and most web frameworks, a URL is a kind of API for
accessing the data your web app provides.  This data can be made available in
multiple formats.  :term:`TurboGears` allows you to use one URL to serve
multiple formats by specifying a query parameter or a special header.

Selecting JSON Output
=====================

A URL in :term:`TurboGears` can serve double duty by returning multiple
formats depending on how it is called.  In most cases, the URL will return
HTML or XHTML by default.  By adding the query parameter, ``tg_format=json``
you can switch from returning the default format to returning :term:`JSON`
data.  You need to add an ``@expose(allow_json=True)`` decorator [#]_ to your
controller method to tell :term:`TurboGears` that this controller should
return :term:`JSON` data::

    @expose(allow_json=True)
    @expose(template='my.templates.amplifypage')
    def amplify(self, data):

``allow_json=True`` is a shortcut for this::

    @expose("json", content_type="text/javascript",
            as_format="json", accept_format="text/javascript")

That means that the controller method will use the ``json`` template (uses
TurboJson to marshal the returned data to :term:`JSON`) to return data of type
``text/javascript`` when either of these conditions is met:  a query param of
``tg_format=json`` or an ``Accept: text/javascript`` header is sent.

:class:`~fedora.client.BaseClient` in python-fedora 0.1.x and 0.2.x use the
query parameter method of selecting :term:`JSON` output.
:class:`~fedora.client.BaseClient` 0.2.99.6 and 0.3.x use both the header
method and the query parameter since the argument was made that the header
method is friendlier to other web frameworks.  0.4 intends to use the header
alone.  If you use ``allow_json=True`` this change shouldn't matter.  If you
specify the ``@expose("json")`` decorator only ``accept_format`` is set.  So
it is advisable to include both ``as_format`` and ``accept_format`` in your
decorator.  Note that this is a limitation of :term:`TurboGears` <= 1.0.4.4.
If your application is only going to run on :term:`TurboGears` > 1.0.4.4 you
should be able to use a plain ``@expose("json")`` [#]_.

.. [#] http://docs.turbogears.org/1.0/ExposeDecorator#same-method-different-template

.. [#] http://trac.turbogears.org/ticket/1459#comment:4

Why Two Formats from a Single URL?
==================================

When designing your URLs you might wonder why you'd want to return
:term:`JSON` and HTML from a single controller method instead of having two
separate controller methods.  For instance, separating the URLs into their own
namespaces might seem logical: ``/app/json/get_user/USERNAME`` as opposed to
``/app/user/USERNAME``.  Doing things with two URLs as opposed to one has both
benefits and drawbacks.

Benefits of One Method Handling Multiple Formats
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Usually less code as there's only one controller method
* When a user sees a page that they want to get data from, they can get it as
  :term:`JSON` instead of screen scraping.
* Forces the application designer to think more about the API that is being
  provided to the users instead of just the needs of the web page they are
  creating.
* Makes it easier to see what data an application will need to implement an
  alternate interface since you can simply look at the template code to see
  what variables are being used on a particular page.

Benefits of Multiple Methods for Each Format
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Avoids special casing for error handlers (See below)
* Separates URLs that you intend users to grab :term:`JSON` data from URLs
  where you only want to display HTML.
* Allows the URLs that support :term:`JSON` to concentrate on trimming the
  size of the data sent while URLs that only return HTML can return whole
  objects.
* Organization can be better if you don't have to include all of the pages
  that may only be useful for user interface elements.

Personal use has found that allowing :term:`JSON` requests on one controller
method works well for cases where you want the user to get data and for
traditional form based user interaction.  AJAX requests have been better
served via dedicated methods.

-------------
Return Values
-------------

The toplevel of the return values should be a dict.  This is the natural
return value for :term:`TurboGears` applications.

Marshaling
===========
All data should be encoded in :term:`JSON` before being returned.  This is
normally taken care of automatically by :term:`TurboGears` and simplejson.  If
you are returning non-builtin objects you may have to define an `__json__()`_
method.

.. _`__json__()`: `Using __json__()`_

Unicode
=======
simplejson (and probably other :term:`JSON` libraries) will take care of
encoding Unicode strings to :term:`JSON` so be sure that you are passing
Unicode strings around rather than encoded byte strings.

Error Handling
==============

In python, error conditions are handled by raising an exception.  However,
an exception object will not propagate automatically through a return from
the server.  Instead we set several special variables in the returned data
to inform :class:`~fedora.client.BaseClient` of any errors.

At present, when :class:`~fedora.client.BaseClient` receives an error it raises an exception of its
own with the exception information from the server inside.  Raising the same
exception as the server is being investigated but may pose security risks so
hasn't yet been implemented.

exc
~~~
All URLs which return :term:`JSON` data should set the ``exc`` variable when
the method fails unexpectedly (a database call failed, a place where you would
normally raise an exception, or where you'd redirect to an error page if a
user was viewing the HTML version of the web app).  ``exc`` should be set to
the name of an exception and tg_flash_ set to the message that would normally
be given to the exception's constructor.  If the return is a success (expected
values are being returned from the method or a value was updated successfully)
``exc`` may either be unset or set to ``None``.

tg_flash
~~~~~~~~
When viewing the HTML web app, ``tg_flash`` can be set with a message to
display to the user either on the next page load or via an AJAX handler.
When used in conjunction with :term:`JSON`, ``exc=EXCEPTIONNAME``, and
:class:`~fedora.client.BaseClient`, ``tg_flash`` should be set to an error
message that the client can use to identify what went wrong or display to the
user.  It's equivalent to the message you would normally give when raising an
exception.

Authentication Errors
~~~~~~~~~~~~~~~~~~~~~
Errors in authentication are a special case.  Instead of returning an error
with ``exc='AuthError'`` set, the server should return with ``response.status =
403``.  :class:`~fedora.client.BaseClient` will see the 403 and raise an
`AuthError`.

This is the signal for the client to ask the user for new credentials (usually
a new username and password).

.. note::
    Upstream :term:`TurboGears` has switched to sending a 401 for
    authentication problems.  However, their use of 401 is against the http
    specification (It doesn't set the 'WWW-Authentication' header) and it
    causes problems for konqueror and webkit based browsers so we probably
    will not be switching.

------------------------------------------------
Performing Different Actions when Returning JSON
------------------------------------------------

So far we've run across three features of :term:`TurboGears` that provide
value to a web application but don't work when returning :term:`JSON` data.
We provide a function that can code around this.
``fedora.tg.utils.request_format()`` will return the format that the page
is being returned as.  Code can use this to check whether :term:`JSON` output
is expected and do something different based on it::

    output = {'tg_flash': 'An Error Occurred'}
    if fedora.tg.utils.request_format() == 'json':
        output['exc'] = 'ServerError'
    else:
        output['tg_template'] = 'my.templates.error'
    return output

In this example, we return an error through our "exception" mechanism if we
are returning :term:`JSON` and return an error page by resetting the template
if not.

Redirects
=========
Redirects do not play well with :term:`JSON` [#]_ because :term:`TurboGears`
is unable to turn the function returned from the redirect into a dictionary
that can be turned into :term:`JSON`.

Redirects are commonly used to express errors.  This is actually better
expressed using tg_template_ because that method leaves the URL intact.
That allows the end user to look for spelling mistakes in their URL.  If you
need to use a redirect, the same recipe as above will allow you to split your
code paths.

.. [#] Last checked in TurboGears 1.0.4

tg_template
===========

Setting what template is returned to a user by setting tg_template in the
return dict (for instance, to display an error page without changing the URL)
is a perfectly valid way to use :term:`TurboGears`.  Unfortunately, since
:term:`JSON` is simply another template in :term:`TurboGears` you have to be
sure not to interfere with the generation of :term:`JSON` data.  You need to
check whether :term:`JSON` was requested using
``fedora.tg.utils.request_format()`` and only return a different template
if that's not the case.  The recipe above shows how to do this.

Validators
==========

Validators are slightly different than the issues we've encountered so far.
Validators are used to check and convert parameters sent to a controller
method so that only good data is dealt with in the controller method itself.
The problem is that when a validator detects a parameter that is invalid, it
performs a special internal redirect to a method that is its ``error_handler``.
We can't intercept this redirect because it happens in the decorators before
our method is invoked.  So we have to deal with the aftermath of the redirect
in the ``error_handler`` method::

    class NotNumberValidator(turbogears.validators.FancyValidator):
        messages = {'Number': 'Numbers are not allowed'}

        def to_python(self, value, state=None):
            try:
                number = turbogears.validators.Number(value.strip())
            except:
                return value
            raise validators.Invalid(self.message('Number', state), value,
                    state)

    class AmplifyForm(turbogears.widgets.Form):
        template = my.templates.amplifyform
        submit_text = 'Enter word to amplify'
        fields = [
                turbogears.widgets.TextField(name='data',
                        validator=NotNumberValidator())
                ]

    amplify_form = AmplifyForm()

    class mycontroller(RootController):

        @expose(template='my.templates.errorpage', allow_json=True)
        def no_numbers(self, data):
            errors = fedora.tg.utils.jsonify_validation_errors()
            if errors:
                return errors
            # Construct a dict to return the data error message as HTML via
            # the errorpage template
            pass

        @validate(form=amplify_form)
        @error_handler('no_numbers')
        @expose(template='my.templates.amplifypage', allow_json=True)
        def amplify(self, data):
            return dict(data=data.upper())

When a user hits ``amplify()``'s URL, the validator checks whether ``data`` is
a number.  If it is, it redirects to the error_handler, ``no_numbers()``.
``no_numbers()`` will normally return HTML which is fine if we're simply
hitting ``amplify()`` from a web browser.  If we're hitting it from a
:class:`~fedora.client.BaseClient` app, however, we need it to return
:term:`JSON` data instead.  To do that we use ``jsonify_validation_errors()``
which checks whether there was a validation error and whether we need to
return :term:`JSON` data.  If both of those are true, it returns a dictionary
with the validation errors.  This dictionary is appropriate for returning from
the controller method in response to a :term:`JSON` request.

.. warning::

    When defining @error_handler() order of decorators can be important.  The
    short story is to always make @validate() and @error_handler() the first
    decorators of your method.  The longer version is that this is known to
    cause errors with the json request not being honored or skipping identity
    checks when the method is its own error handler.

----------------
Expected Methods
----------------

Certain controller methods are necessary in order for
:class:`~fedora.client.BaseClient` to properly talk to your service.
:term:`TurboGears` can quickstart an application template for you that sets
most of these variables correctly::

    $ tg-admin quickstart -i -s -p my my
    # edit my/my/controllers.py

login()
=======

You need to have a ``login()`` method in your application's root.  This method
allows :class:`~fedora.client.BaseClient` to authenticate against your Service::

         @expose(template="my.templates.login")
    +    @expose(allow_json=True)
         def login(self, forward_url=None, previous_url=None, \*args, \**kw):

             if not identity.current.anonymous \
                 and identity.was_login_attempted() \
                 and not identity.get_identity_errors():
    +            # User is logged in
    +            if 'json' == fedora.tg.utils.request_format():
    +                return dict(user=identity.current.user)
    +            if not forward_url:
    +                forward_url = turbogears.url('/')
                 raise redirect(forward_url)

For non-TurboGears Implementors
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you are implementing a server in a non-TurboGears framework, note that one
of the ways to reach the ``login()`` method is through special parameters
parsed by the :term:`TurboGears` framework.
:class:`~fedora.client.BaseClient` uses these parameters instead of invoking
the ``login()`` method directly as it saves a round trip when authenticating
to the server.  It will be necessary for you to implement handling of these
parameters (passed via ``POST``) on your application as well.

The parameters are: ``user_name``, ``password``, and ``login``.  When these
three parameters are sent to the server, the server authenticates the user
and records their information before deciding what information to return to
them from the URL.

logout()
========

The ``logout()`` method is similar to ``login()``.  It also needs to be
modified to allow people to connect to it via :term:`JSON`::

    -    @expose()
    +    @expose(allow_json=True)
         def logout(self):
             identity.current.logout()
    +        if 'json' in fedora.tg.utils.request_format():
    +            return dict()
             raise redirect("/")

---------------
CSRF Protection
---------------

For an overview of CSRF and how to protect :term:`TurboGears` 1 based
services, look at this document.

.. toctree::
   :maxdepth: 2

   CSRF

.. _Using-SABase:

------------
Using SABase
------------

``fedora.tg.json`` contains several functions that help to convert SQLAlchemy_
objects into :term:`JSON`.  For the most part, these do their work behind the
scenes.  The ``SABase`` object, however, is one that you might need to take an
active role in using.

When you return an SQLAlchemy_ object in a controller to a template, the
template is able to access any of the relations mapped to it.  So, instead of
having to construct a list of people records from a table and
the the list of groups that each of them are in you can pass in the list of
people and let your template reference the relation properties to get the
groups.  This is extremely convenient for templates but has a negative effect
when returning :term:`JSON`. Namely, the default methods for marshaling
SQLAlchemy_ objects to :term:`JSON` only return the attributes of the object,
not the relations that are linked to it.  So you can easily run into a
situation where someone querying the :term:`JSON` data for a page will not
have all the information that a template has access to.

SABase fixes this by allowing you to specify relations that your
SQLAlchemy_ backed objects should marshal as :term:`JSON` data.

Further information on SABase can be found in the API documentation::

  pydoc fedora.tg.json

.. _SQLAlchemy: http://www.sqlalchemy.org

Example
=======

SABase is a base class that you can use when defining objects
in your project's model.  So the first step is defining the classes in your
model to inherit from SABase::

    from fedora.tg.json import SABase
    from sqlalchemy import Table, Column, Integer, String, MetaData, ForeignKey
    from turbogears.database import metadata, mapper

    class Person(SABase):
        pass
    PersonTable = Table('person', metadata
        Column('name', String, primary_key=True),
        )

    class Address(SABase):
        pass
    AddressTable = Table (
        Column('id', Integer, primary_key=True),
        Column('street', string),
        Column('person_id', Integer, ForeignKey('person.name')
        )

    mapper(PersonTable, Person)
    mapper(AddressTable, Address, properties = {
        person: relation(Person, backref = 'addresses'),
    })

The next step is to tell SABase which properties should be copied (this
allows you to omit large trees of objects when you only need the data from
a few of them)::

    @expose('my.templates.about_me')
    @expose(allow_json=True)
    def my_info(self):
        person = Person.query.filter_by(name='Myself').one()
        person.jsonProps = {'Person': ['addresses']}
        return dict(myself=person}

Now, when someone requests :term:`JSON` data from my_info, they should get
back a record for person that includes a property addresses.  Addresses will
be a list of address records associated with the person.

How it Works
============

SABase adds a special `__json__()`_ method to the class.  By default, this
method returns a dict with all of the attributes that are backed by fields in
the database.

Adding entries to jsonProps adds the values for those properties to the
returned dict as well.  If you need to override the `__json__()`_ method in
your class you probably want to call SABase's `__json__()`_ unless you know
that neither you nor any future subclasses will need it.

.. _Using-__json__:

----------------
Using __json__()
----------------

Sometimes you need to return an object that isn't a basic python type (list,
tuple, dict, number. string, etc).  When that occurs, simplejson_ won't know
how to marshal the data into :term:`JSON` until you write own method to
transform the values.  If this method is named __json__(), :term:`TurboGears`
will automatically perform the conversion when you return the object.

Example::

    class MyObject(object):
        def _init__(self, number):
            self.someNumber = number
            self.cached = None

        def _calc_data(self):
            if not self.cached:
                self.cached = self.someNumber * 2
            return self.cached

        twiceData = property(_calc_data)

        def __json__(self):
            return {'someNumber': self.someNumber, 'twiceData': self.twiceData}

In this class, you have a variable and a property.  If you were to return it
from a controller method without defining the __json__() method,
:term:`TurboGears` would give you an error that it was unable to adapt the
object to :term:`JSON`.  The :term:`JSON` method transforms the object into a
dict with sensibly named values for the variable and property so that
simplejson is able to marshal the data to :term:`JSON`.  Note that you will
often have to choose between space (more data takes more bandwidth to deliver
to the end user) and completeness (you need to return enough data so the
client isn't looking for another method that can complete its needs) when
returning data.

.. _simplejson: http://undefined.org/python/#simplejson
