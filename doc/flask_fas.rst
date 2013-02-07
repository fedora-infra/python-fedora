=====================
FAS Flask Auth Plugin
=====================

:Authors: Toshio Kuratomi, Ian Weller
:Date: 29 October 2012
:For Version: 0.3.x

The :ref:`Fedora-Account-System` has a :term:`JSON` interface that we make use
of to authenticate users in our web apps.  For our :term:`Flask` applications
we have an identity provider that has :term:`single sign-on` with our
:term:`TurboGears` 1 and 2 applications.  It does not protect against
:term:`CSRF` attacks in the identity layer.  The flask-wtf forms package
should be used to provide that.

-------------
Configuration
-------------

The FAS auth plugin has several config values that can be used to control how
the auth plugin functions.  You can set these in your application's config
file.

FAS_BASE_URL
    Set this to the URL of the FAS server you are authenticating against.
    Default is "https://admin.fedoraproject.org/accounts/"

FAS_USER_AGENT
    User agent string to be used when connecting to FAS.  You can set this to
    something specific to your application to aid in debugging a connection to
    the FAS server as it will show up in the FAS server's logs.  Default is
    "Flask-FAS/|version|"

FAS_CHECK_CERT
    When set, this will check the SSL Certificate for the FAS server to make
    sure that it is who it claims to be.  This is useful to set to False when
    testing against a local FAS server but should always be set to True in
    production.  Default: True

FAS_COOKIE_NAME
    The name of the cookie used to store the session id across the Fedora
    Applications that support :term:`single sign-on`.  Default: "tg-visit"

FAS_FLASK_COOKIE_REQUIRES_HTTPS
    When this is set to True, the session cookie will only be returned to the
    server via ssl (https).  If you connect to the server via plain http, the
    cookie will not be sent.  This prevents sniffing of the cookie contents.
    This may be set to False when testing your application but should always
    be set to True in production.  Default is True.

------------------
Sample Application
------------------

The following is a sample, minimal flask application that uses fas_flask for
authentication::

    #!/usr/bin/python -tt
    # Flask-FAS - A Flask extension for authorizing users with FAS
    # Primary maintainer: Ian Weller <ianweller@fedoraproject.org>
    #
    # Copyright (c) 2012, Red Hat, Inc.
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

    # This is a sample application. In addition to using Flask-FAS, it uses
    # Flask-WTF (WTForms) to handle the login form. Use of Flask-WTF is highly
    # recommended because of its CSRF checking.

    import flask
    from flask.ext import wtf
    from flask.ext.fas import FAS, fas_login_required

    # Set up Flask application
    app = flask.Flask(__name__)
    # Set up FAS extension
    fas = FAS(app)

    # Application configuration
    # SECRET_KEY is necessary to CSRF in WTForms.  It nees to be secret to
    # make the csrf tokens unguessable but if you have multiple servers behind
    # a load balancer, the key needs to be the same on each.
    app.config['SECRET_KEY'] = 'change me!'
    # Other configuration options for Flask-FAS:
    #     FAS_BASE_URL: the base URL for the accounts system
    #         (default https://admin.fedoraproject.org/accounts/)
    #     FAS_CHECK_CERT: check the SSL certificate of FAS (default True)
    #     FAS_FLASK_COOKIE_REQUIRES_HTTPS: send the 'secure' option with
    #          the login cookie (default True)
    # You should use these options' defaults for production applications!
    app.config['FAS_BASE_URL'] = 'https://fakefas.fedoraproject.org/accounts/'
    app.config['FAS_CHECK_CERT'] = False
    app.config['FAS_FLASK_COOKIE_REQUIRES_HTTPS'] = False


    # A basic login form
    class LoginForm(wtf.Form):
        username = wtf.TextField('Username', [wtf.validators.Required()])
        password = wtf.PasswordField('Password', [wtf.validators.Required()])


    # Inline templates keep this test application all in one file. Don't do this in
    # a real application. Please.
    TEMPLATE_START = """
    <h1>Flask-FAS test app</h1>
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
        # Init login form
        form = LoginForm()
        # Init template
        data = TEMPLATE_START
        data += ('<p>Log into the <a href="{{ config.FAS_BASE_URL }}">'
                 'Fedora Accounts System</a>:')
        # If this is POST, process the form
        if form.validate_on_submit():
            if fas.login(form.username.data, form.password.data):
                # Login successful, return
                return flask.redirect(next_url)
            else:
                # Login unsuccessful
                data += '<p style="color:red">Invalid login</p>'
        data += """
    <form action="" method="POST">
    {% for field in [form.username, form.password] %}
        <p>{{ field.label }}: {{ field|safe }}</p>
        {% if field.errors %}
            <ul style="color:red">
            {% for error in field.errors %}
                <li>{{ error }}</li>
            {% endfor %}
            </ul>
        {% endif %}
    {% endfor %}
    <input type="submit" value="Log in">
    {{ form.csrf_token }}
    </form>"""
        return flask.render_template_string(data, form=form)


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
    def claplusone():
        data = TEMPLATE_START
        if not flask.g.fas_user:
            # Not logged in
            return flask.render_template_string(data +
                    '<p>You must log in to check your cla +1 status</p>')
        non_cla_groups = [x.name for x in flask.g.fas_user.approved_memberships
                          if x.group_type != 'cla']
        if len(non_cla_groups) > 0:
            data += '<p>Your account is cla+1.</p>'
        else:
            data += '<p>Your account is <em>not</em> cla+1.</p>'
        return flask.render_template_string(data)


    if __name__ == '__main__':
        app.run(debug=True)
