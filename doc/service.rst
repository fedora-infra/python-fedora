===============
Fedora Services
===============
:Authors: Toshio Kuratomi
          Luke Macken
:Date: 4 April 2008
:For Version: 0.3.x

In the loosest sense, a Fedora Service is a web application that sends data
that BaseClient_ is able to understand.  This document defines things that a
web application must currently do for BaseClient_ to understand it.

.. _BaseClient: client.html

.. contents::

----------
TurboGears
----------

All current Fedora Services are written in TurboGears_.  Examples in this
document will be for that framework.  However, other frameworks can be used
to write a Service if they can correctly create the data that BaseClient needs.

The TurboGears_ framework separates an application into model, view, and
controller layers.  The model is typically a database and holds the raw data
that the application needs.  The view formats the data before output.  The
controller binds the other two pieces together.  For the purpose of building a
Service that works with BaseClient_ we will mostly be concerned with the
controller level although there are a few advanced features that can be used
to help code the model [#]_ and view [#]_ layer for particular tricky problems.

A Fedora Service differs from other web applications in that certain URLs for
the web application are an API layer that the Service can send and receive
json data from for BaseClient_ to interpret.  This imposes certain constraints
on what data can be sent and what data can be received from those URLs.

.. _TurboGears: http://www.turbogears.org/
.. [#] `Using SABase`_
.. [#] `Using __json__()`_

-----------------
Sample Controller
-----------------

This is the sample controller method that we will modify throughout this
document::

    from turbogears.controllers import RootController
    from turbogears import expose

    class mycontroller(RootController):
        @expose(template='my.templates.amplifypage')
        def amplify(self, data):
            return dict(data=data.upper())

-----------
URLs as API
-----------

In TurboGears_ and most web frameworks, a URL is a kind of API for accessing
the data your web app provides.  This data can be made available in multiple
formats.  TurboGears_ allows you to use one URL to serve multiple formats by
specifying a query parameter or a special header.

Selecting JSON Output
=====================

A URL in TurboGears_ can serve double duty by returning multiple formats
depending on how it is called.  In most cases, the URL will return html or
xhtml by default.  By adding the query parameter, ``tg_format=json`` you can
switch from returning the default format to returning json data.  You need to
add an ``@expose(allow_json=True)`` decorator [#]_ to your controller method to
tell TurboGears_ that this controller should return json data::

    @expose(allow_json=True)
    @expose(template='my.templates.amplifypage')
    def amplify(self, data):

``allow_json=True`` is a shortcut for this::

    @expose("json", content_type="text/javascript",
            as_format="json", accept_format="text/javascript")

That means that the controller method will use the ``json`` template (uses
TurboJson to marshall the returned data to json) to return data of type
``text/javascript`` when either of these conditions is met:  a query param of 
``tg_format=json`` or an ``Accept: text/javascript`` header is sent.

BaseClient_ in python-fedora 0.1.x and 0.2.x use the query parameter method of
selecting json output.  BaseClient_ 0.2.99.6 and 0.3.x use both the header
method and the query parameter since the argument was made that the header
method is friendlier to other web frameworks.  0.4 intends to use the header
alone.  If you use ``allow_json=True`` this change shouldn't matter.  If you
specify the ``@expose("json")`` decorator manually it is advisable to include
both ``as_format`` and ``accept_format`` in your decorator so you can handle
either method.

.. [#] http://docs.turbogears.org/1.0/ExposeDecorator#same-method-different-template

Why Two Formats from a Single URL?
==================================

When designing your URLs you might wonder why you'd want to return json and
html from a single controller method instead of having two separate controller
methods.  For instance, separating the URLs into their own namespaces might
seem logical: ``/app/json/get_user/USERNAME`` as opposed to
``/app/user/USERNAME``.  Doing things with two URLs as opposed to one has both
benefits and drawbacks:

Benefits of One Method Handling Multiple Formats
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Usually less code as there's only one controller method
* When a user sees a page that they want to get data from, they can get it as
  json instead of screen scraping.
* Forces the application designer to think more about the API that is being
  provided to the users instead of just the needs of the web page they are
  creating.
* Makes it easier to see what data an application will need to implement an
  alternate interface since you can simply look at the template code to see
  what variables are being used on a particular page.

Benefits of Multiple Methods for Each Format
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Avoids special casing for error handlers (See below)
* Separates URLs that you intend users to grab json data from URLs where you
  only want to display html.
* Allows the URLs that support json to concentrate on trimming the size of the
  data sent while URLs that only return html can return whole objects.
* Organization can be better if you don't have to include all of the pages
  that may only be useful for user interface elements.

Personal use has found that allowing json requests on one controller method
works well for cases where you want the user to get data and for traditional
form based user interaction.  AJAX requests have been better served via
dedicated methods.

-------------
Return Values
-------------

The toplevel of the return values should be a dict.  This is the natural
return value for TurboGears_ applications.

Marshalling
===========
All data should be encoded in json before being returned.  This is normally
taken care of automatically by TurboGears and simplejson.  If you are
returning non-builtin objects you may have to define an `__json__()`_ method.

.. _`__json__()`: `Using __json__()`_

Unicode
=======
simplejson (and probably other json libraries) will take care of encoding
unicode strings to json so be sure that you are passing unicode strings
around rather than encoded byte strings.

Error Handling
==============

In python, error conditions are handled by raising an exception.  However,
an exception object will not propogate automatically through a return from
the server.  Instead we set several special variables in the returned data
to inform BaseClient_ of any errors.

At present, when BaseClient_ receives an error it raises an exception of its
own with the exception information from the server inside.  Raising the same
exception as the server is being investigated but may pose security risks so
hasn't yet been implemented.

exc
~~~
All URLs which return json data should set the ``exc`` variable when the
method fails unexpectedly (a database call failed, a place where you would
normally raise an exception, or where you'd redirect to an error page if a
user was viewing the html version of the web app).  ``exc`` should be set
to the name of an exception and tg_flash_ set to the message that wold
normally be given to the exception's constructor.  If the return is a success
(expected values are being returned from the method or a value was updated
successfully) ``exc`` may either be unset or set to ``None``.

tg_flash
~~~~~~~~
When viewing the html web app, ``tg_flash`` can be set with a message to
display to the user either on the next page load or via an AJAX handler.
When used in conjunction with json, ``exc=EXCEPTIONNAME``, and BaseClient_,
``tg_flash`` should be set to an error message that the client can use to
identify what went wrong or display to the user.  It's equivalent to the
message you would normally give when raising an exception.

------------------------------------------------
Performing Different Actions when Returning JSON
------------------------------------------------

So far we've run across two features of TurboGears that provide value to a
web application but don't work when returning json data.  We provide a
function that can code around this.  ``fedora.tg.util.request_format()`` will
return the format that the page is being returned as.  Code can use this to
check whether json output is expected and do something different based on it::

    output = {'tg_flash': 'An Error Occurred'}
    if fedora.tg.util.request_format() == 'json':
        output['exc'] = 'ServerError'
    else:
        output['tg_template'] = 'my.templates.error'
    return output

In this example, we return an error through our "exception" mechanism if we
are returning json and return an error page by resetting the template if not.

Redirects
=========
Redirects do not play well with JSON [#] because TurboGears is unable to turn
the function returned from the redirect into a dictionary that can be turned
into JSON.

Redirects are commonly used to express errors.  This is actually better
expressed using tg_template_ because that method leaves the URL intact.
That allows the end user to look for spelling mistakes in their URL.  If you
need to use a redirect, the same recipe as above will allow you to split your
code paths.

.. [#] Last checked in TurboGears 1.0.4

tg_template
===========

Setting what template is returnedto a user by setting tg_template in the
return dict (for instance, to display an error page without changing the URL)
is a perfectly valid way to use TurboGears_.  Unfortunately, since JSON is
simply another template in TurboGears_ you have to be sure not to interfere
with the generation of json data.  You need to check whether json was
requested using ``fedora.tg.util.request_format()`` and only return a
different template if that's not the case.

------------
Using SABase
------------

``fedora.tg.json`` contains several functions that help to convert SQLAlchemy_
objects into json.  For the most part, these do their work behind the scenes.
The ``SABase`` object, however, is one that you might need to take an active
role in using.

When you return an SQLAlchemy_ object in a controller to a template, the
template is able to access any of the relations mapped to it.  So, instead of
having to construct a list of people records from a table and
the the list of groups that each of them are in you can pass in the list of
people and let your template reference the relation properties to get the
groups.  This is extremely convenient for templates but has a negative effect
when returning json. Namely, the default methods for marshalling SQLAlchemy_
objects to JSON only return the attributes of the object, not the relations
that are linked to it.  So you can easily run into a situation where someone
querying the JSON data for a page will not have all the information that a
template has access to.

SABase fixes this by allowing you to specify relations that your
SQLAlchemy_ backed objects should marshall as json data.

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

Now, when someone requests json data from my_info, they should get back a
record for person that includes a property addresses.  Addresses will be a
list of address records associated with the person.

How it Works
============

SABase adds a special `__json__()`_ method to the class.  By default, this
method returns a dict with all of the attributes that are backed by fields in
the database.

Adding entries to jsonProps adds the values for those properties to the
returned dict as well.  If you need to override the `__json__()`_ method in
your class you probably want to call SABase's `__json__()`_ unless you know
that neither you nor any future subclasses will need it.

----------------
Using __json__()
----------------

Sometimes you need to return an object that isn't a basic python type (list,
tuple, dict, number. string, etc).  When that occurs, simplejson_ won't know
how to marshall the data into json until you write own method to transform the
values.  If this method is named __json__(), TurboGears_ will automatically
perform the conversion when you return the object.

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
from a controller method without defining the __json__() method, TurboGears_
would give you an error that it was unable to adapt the object to json.  The
json method transforms the object into a dict with sensibly named values for
the variable and property so that simplejson is able to marshall the data to
json.  Note that you will often have to choose between space (more data takes
more bandwidth to deliver to the enduser) and completeness (you need to return
enough data so the client isn't looking for another method that can complete
its needs) when returning data.

.. _simplejson: http://undefined.org/python/#simplejson
