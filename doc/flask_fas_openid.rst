============================
FAS Flask OpenID Auth Plugin
============================

:Authors: Patrick Uiterwjk
:Date: 18 February 2013
:For Version: 0.3.x

The :ref:`Fedora-Account-System` has a :term:`OpenID` provider that applications
can use to authenticate users in web apps. For our :term:`Flask` applications
we have an identity provider that uses this OpenID service to authenticate users.
It is almost completely compatible with :ref:`flask_fas` except that it does not
use the username/password provided by the client application (it is silently
ignored). It can be configured to use any OpenID authentication service that
implements the OpenID Teams Extension, Simple Registration Extension and
CLA Extension.

-------------
Configuration
-------------

The FAS OpenID auth plugin has several config values that can be used to control
how the auth plugin functions.  You can set these in your application's config
file.

FAS_OPENID_ENDPOINT
    Set this to the OpenID endpoint url you are authenticating against.
    Default is "http://id.fedoraproject.org/"

FAS_CHECK_CERT
    When set, this will check the SSL Certificate for the FAS server to make
    sure that it is who it claims to be.  This is useful to set to False when
    testing against a local FAS server but should always be set to True in
    production.  Default: True

------------------
Sample Application
------------------

The following is a sample, minimal flask application that uses fas_flask for
authentication::

    #!/usr/bin/python -tt
    # Flask-FAS-OpenID - A Flask extension for authorizing users with OpenID
    # Primary maintainer: Patrick Uiterwijk <puiterwijk@fedoraproject.org>
    #
    # Copyright (c) 2012-2013, Red Hat, Inc., Patrick Uiterwijk
    #
    # Redistribution and use in source and binary forms, with or without
    # modification, are permitted provided that the following conditions are met:
    #
    # * Redistributions of source code must retain the above copyright notice, this
    # list of conditions and the following disclaimer.
    # * Redistributions in binary form must reproduce the above copyright notice,
    # this list of conditions and the following disclaimer in the documentation
    # and/or other materials provided with the distribution.
    # * Neither the name of the Red Hat, Inc. nor the names of its contributors may
    # be used to endorse or promote products derived from this software without
    # specific prior written permission.
    #
    # THIS SOFTWARE IS PROVIDED BY THE REGENTS AND CONTRIBUTORS ''AS IS'' AND ANY
    # EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
    # WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
    # DISCLAIMED. IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE FOR ANY
    # DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
    # (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
    # LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
    # ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
    # (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
    # SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

    # This is a sample application.

    import flask
    from flask_fas_openid import fas_login_required, cla_plus_one_required, FAS

    # Set up Flask application
    app = flask.Flask(__name__)
    # Set up FAS extension
    fas = FAS(app)

    # Application configuration
    # SECRET_KEY is necessary for the Flask session system.  It nees to be secret to
    # make the sessions secret but if you have multiple servers behind
    # a load balancer, the key needs to be the same on each.
    app.config['SECRET_KEY'] = 'change me!'
    # Other configuration options for Flask-FAS-OpenID:
    #     FAS_OPENID_ENDPOINT: the OpenID endpoint URL
    #         (default http://id.fedoraproject.org/)
    #     FAS_CHECK_CERT: check the SSL certificate of FAS (default True)
    # You should use these options' defaults for production applications!
    app.config['FAS_OPENID_ENDPOINT'] = 'http://id.fedoraproject.org/'
    app.config['FAS_CHECK_CERT'] = True


    # Inline templates keep this test application all in one file. Don't do this in
    # a real application. Please.
    TEMPLATE_START = """
    <h1>Flask-FAS-OpenID test app</h1>
    {% if g.fas_user %}
        <p>Hello, {{ g.fas_user.username }} &mdash;
        <a href="{{ url_for("logout") }}">Log out</a>
    {% else %}
        <p>You are not logged in &mdash;
        <a href="{{ url_for("auth_login", next=request.url) + '' }}">Log in</a>
    {% endif %}
    &mdash; <a href="{{ url_for("index") }}">Main page</a></p>
    """


    @app.route('/')
    def index():
        data = TEMPLATE_START
        data += '<p><a href="%s">Check if you are cla+1</a></p>' % \
                flask.url_for('claplusone')
        data += '<p><a href="%s">See a secret message (requires login)</a></p>' % \
                flask.url_for('secret')
        return flask.render_template_string(data)


    @app.route('/login', methods=['GET', 'POST'])
    def auth_login():
        # Your application should probably do some checking to make sure the URL
        # given in the next request argument is sane. (For example, having next set
        # to the login page will cause a redirect loop.) Some more information:
        # http://flask.pocoo.org/snippets/62/
        if 'next' in flask.request.args:
            next_url = flask.request.args['next']
        else:
            next_url = flask.url_for('index')
        # If user is already logged in, return them to where they were last
        if flask.g.fas_user:
            return flask.redirect(next_url)
        return fas.login(return_url=next_url)

    @app.route('/logout')
    def logout():
        if flask.g.fas_user:
            fas.logout()
        return flask.redirect(flask.url_for('index'))

    # This demonstrates the use of the fas_login_required decorator. The
    # secret message can only be viewed by those who are logged in.
    @app.route('/secret')
    @fas_login_required
    def secret():
        data = TEMPLATE_START + '<p>Be sure to drink your Ovaltine</p>'
        return flask.render_template_string(data)


    # This demonstrates checking for group membership inside of a function.
    # The flask_fas adapter also provides a cla_plus_one_required decorator that
    # can restrict a url so that you can only access it from an account that has
    # cla +1.
    @app.route('/claplusone')
    @cla_plus_one_required
    def claplusone():
        data = TEMPLATE_START
        data += '<p>Your account is cla+1.</p>'
        return flask.render_template_string(data)


    if __name__ == '__main__':
        app.run(debug=True)
