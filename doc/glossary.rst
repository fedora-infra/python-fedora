.. _glossary:

========
Glossary
========

.. glossary::

    controller
        In MVC design, the controller is in charge of things.  It takes
        processes events and decides what data to ask the :term:`model` for,
        manipulates the data according to the information in the event, and
        decides which :term:`view` to send the results to to be rendered.

    CSRF
        `Cross-site request forgery
        <http://en.wikipedia.org/wiki/Cross-site_request_forgery>`_ is a
        technique where a malicious website can gain access to another web
        site by hijaacking a currently open session that the user has open to
        the site.  This technique can also affect identification via SSL
        Certificates or anything else that the browser sends to the server
        automatically when a request is made.

        .. seealso:: :ref:`CSRF-Protection`

    Dojo
        Dojo is a JavaScript toolkit that aims to be a standard library for
        JavaScript.  It provides a small core library with useful functions
        and an expanded set of scripts that can be added that provide widgets
        and other features.

        .. seealso:: http://www.dojotoolkit.org

    double submit
        A strategy to foil :term:`CSRF` attacks.  This strategy involves
        sending the value of the authentication cookie (or something derivable
        only from knowing the value of the authentication cookie) in the body
        of the request.  Since the :term:`Same Origin Policy` prevents a web
        site other than the one originating the cookie from reading what's in
        the cookie, the server can be reasonably assured that the request does
        not originate from an unknown request on another website.  Note that
        this and other anti-CSRF measures do not protect against spoofing or
        getting a user to actively click on a link on an attacked website by
        mistake.

    JSON
        `JavaScript Object Notation <http://json.org>`_ is a format for
        marshalling data.  It is based on a subset of JavaScript that is used
        to declare objects.  Compared to xml, JSON is a lightweight, easily
        parsed format.

        .. seealso:: `Wikipedia's JSON Entry <http://en.wikipedia.org/wiki/JSON>`_

    model
        In MVC design, the layer that deals directly with the data.

    Same Origin Policy
        A web browser security policy that prevents one website from reading:
        1) the cookies from another website
        2) the response body from another website

        .. seealso:: http://en.wikipedia.org/wiki/Same_origin_policy

    single sign-on
        A feature that allows one login to authenticate a user for multiple
        applications.  So logging into one application will authenticate you
        for all the applications that support the same single-sign-on
        infrastructure.

    TurboGears
        A Python web framework that most of Fedora Infrastructure's apps are
        built on.

        .. seealso:: http://www.turbogears.org/

    TurboGears2
        The successor to :term:`TurboGears`, TurboGears2 provides a very
        similar framework to coders but has some notable differences. It is
        based on pylons and paste so it is much more tightly integrated with
        :term:`WSGI`.  The differences with :ref`TurboGears`1 are largely with
        the organization of code and how to configure the application.

        .. seealso:: http://www.turbogears.org/

    view
        In MVC design, the layer that takes care of formatting and rendering
        data for the consumer.  This could be displaying the data as an html
        page or marshalling it into :term:`JSON` objects.

    WSGI
        WSGI is an interface between web servers and web frameworks that
        originated in the Python community.  WSGI lets different components
        embed each other even if they were originally written for different
        python web frameworks.

        .. seealso:: http://en.wikipedia.org/wiki/Web_Server_Gateway_Interface
