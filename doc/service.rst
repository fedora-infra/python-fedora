===============
Fedora Services
===============
:Authors: Toshio Kuratomi
          Luke Macken
:Date: 2 April 2008
:Document Version: 0.3.0

In the loosest sense, a Fedora Service is a web application that is able to
send data that BaseClient_ is able to understand.  This document defines
things that a web application must currently do for BaseClient_ to understand
it.

.. _BaseClient: client.html

.. contents::

----------
TurboGears
----------

All current Fedora Services are written in TurboGears_.  Examples in this
document will all be for that framework.  However, other frameworks can be
used to write a Service if they can correctly create the data that BaseClient
needs.

The TurboGears_ framework separates an application into model, view, and
controller layers.  The model is typically a database and holds the raw data
that the application needs.  The view formats the data before output.  The
controller binds the other two pieces together.  For the purpose of building a
Service that works with BaseClient_ we will mostly be concerned with the
controller level although there are a few advanced features that can be used
to help code the model[#]_ and view[#]_ layer for particular tricky problems

.  A Fedora Service differs from
other web applications in that certain URLs for the web application are an API
layer that the Service can send and receive data from.  This imposes certain
constraints on what data can be sent and what data can be received from those
URLs.

.. _TurboGears: http://www.turbogears.org/
.. [#]: SABase
.. [#]: `Using __json__`

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
formats.  TrboGears_ allows you to use one URL to serve multiple formats by
specifying a query parameter or a special header.

Selecting JSON Output
=====================

A URL in TurboGears_ can serve double duty by returning multiple formats
depending on how it is called.  In most cases, the URL will return html or
xhtml by default.  By adding the query parameter, ``tg_format=json`` you can
switch from returning the default format to returning json data.  You need to
add an ``@expose(allow_json=True)`` decorator to your controller method to
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

BaseClient_ in python-fedora 0.1 - 0.2.99.5 used the query parameter method of
selecting json output.  BaseClient_ 0.2.99.6 and up use the header method
since the argument was made that this is friendlier to otherweb frameworks.  If
you use ``allow_json=True`` this change shouldn't matter.  If you specify the
``@expose("json"`` decorator manually it is advisable to include both
``as_format`` and ``accept_format`` in your decorator.  If you are using
another framework, be sure that your code handles at least the Accept header
method.

Why Two Formats from a Single URL?
==================================

When designing your URLs you might wonder why you'd want to return json and
html from a single controller method instead of having two separate controller
methods.  For instance, separating the URLs into their own namespaces might
seem logical: ``/app/json/get_user/USERNAME`` as opposed to
``/app/user/USERNAME``.  Doing things with two URLs as opposed to one has both
benefits and drawbacks:

Benefits of One Controller, Multiple Formats
* Usually less code as there's only one controller method
* When a user sees a page that they want to get data from, they can get it as
  json instead of screen scraping.
* Forces the application designer to think more about the API that is being
  provided to the users instead of just the needs of the web page they are
  creating.
* Makes it easier to see what data an application will need to implement an
  alternate interface since you can simply look at the template code to see
  what variables are being used on a particular page.

Benefits of Multiple Controllers for Each Format
* Avoids special casing for error handlers (See below)
* Separates URLs that you intend users to grab json data from URLs where you
  only want to display html.
* Allows the URLs that support json to concentrate on trimming the size of the
  data sent while URLs that only return html can return whole objects.
* Organization can be better if you don't have to include all of the pages
  that may only be useful for user interface elements.

Personal use has found that allowing json requests on one controller method
works well for cases where you want the user to get data and for traditional
form based user interaction.  So far, AJAX type requests have been better
served via dedicated methods.

-------------
Return Values
-------------



Marshalling
===========
All data should be encoded in json before being returned.

Unicode
=======
simplejson (and probably other json libraries) will take care of encoding
unicode strings to json so be sure that strings are unicode rather than
latin-1 or another string type before returning them.

--------------
Error Handling
--------------

status
======

tg_flash
========

Redirects
=========

------
SABase
------

Fill me up

--------------
Using __json__
--------------

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
