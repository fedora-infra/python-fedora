====================
Python Fedora Module
====================

:Author: Patrick Uiterwijk
:Date: 21 April 2016
:Version: 0.8.x

The Fedora module provides a python API for building `Fedora Services`_ and
clients that connect to them.  It has functions and classes that help to build
TurboGears_ applications and classes to make building clients of those
services much easier.

.. _`Fedora Services`: doc/service.html
.. _TurboGears: http://www.turbogears.org

.. contents::

-------
License
-------

This python module is distributed under the terms of the GNU Lesser General
Public License Version 2 or later.

------------
Dependencies
------------

``python-fedora`` requires the ``munch``, ``kitchen``, and ``requests`` python
modules.  It used to use ``pycurl``, but was updated to use ``requests`` as of
version ``0.3.32``.
The ``flask_fas_openid`` module requires the ``python-openid`` and
``python-openid-teams`` modules.

----------
Installing
----------

``python-fedora`` is found in rpm form in Fedora proper.  Sometimes a new
version will be placed in the Fedora Infrastructure ``yum`` repository for testing
within Infrastructure before being released to the general public.  Installing
from the yum repository should be as easy as::

	$ yum install python-fedora

If you want to install from a checkout of the development branch, follow these
procedures::

    $ git clone https://github.com/fedora-infra/python-fedora.git
    $ cd python-fedora
    $ ./setup.py install

See the configuration notes in each section for information on configuring
your application after install.

---------------------------
Fedora Accounts Integration
---------------------------

We provide several modules that make connecting to the `Fedora Account
System`_ easier.

.. _`Fedora Account System`: https://fedorahosted.org/fas

General Purpose API
===================
The ``fedora.accounts.fas2`` module allows code to integrate with the `Fedora
Account System`_. It uses the JSON interface provided by the Account System
servre to retrieve information about users.

Note: This API is not feature complete. If you'd like to help add methods,
document the existing methods, or otherwise aid in development of this API
please contact us on the infrastructure list: infrastructure@lists.fedoraproject.org
or on IRC: lmacken, abadger1999, and ricky in ``#fedora-admin``, ``irc.freenode.net``

Using the general API requires instantiating an ``AccountSystem`` object. You
then use methods on the ``AccountSystem`` to get and set information on the
people in the account system.

At the moment, there are only a few methods implemented. Full documentation on
these methods is available from the ``AccountSystem``'s docstrings from the
interpreter or, for instance, by running::

    $ pydoc fedora.accounts.fas2.AccountSystem

Here's an example of using the ``AccountSystem``::

	from fedora.accounts.fas2 import AccountSystem
	from fedora.client import AuthError

	# Get an AccountSystem object.  All AccountSystem methods need to be
	# authenticated so you might as well give username and password here.
	fas = AccountSystem(username='foo', password='bar')

	people = fas.people_by_id()

TurboGears Interface
====================

The TurboGears_ interface also uses the JSON interface to the account system.
It provides a TurboGears_ ``visit`` and ``identity`` plugin so a TurboGears_
application can authorize via FAS. Since the plugin operates over JSON, it is
possible to use these plugins on hosts outside of Fedora Infrastructure as
well as within.  Remember, however, that entering your Fedora password on a
third party website requires you to trust that website. So doing things this
way is more useful for developers wanting to work on their apps outside of
Fedora Infrastructure than a general purpose solution for allowing Fedora
Users to access your web app. (SSL client certificates and OpenID are better
solutions to this problem but they are still being implemented in the FAS2
server.)

Configuring
-----------
To configure your TurboGears_ application, you need to set the following
variables in your pkgname/config/app.cfg file::

    fas.url='https://admin.fedoraproject.org/accounts/'
    visit.on=True
    visit.manager="jsonfas"
    identity.on="True"
    identity.failure_url="/login"
    identity.provider="jsonfas"

---------------
Fedora Services
---------------

``python-fedora`` provides several helper classes and functions for building a
TurboGears_ application that works well with other `Fedora Services`_.  the
`Fedora Services`_ documentation is the best place to learn more about these.

-----------------
TurboGears Client
-----------------
There is a module to make writing a client for our TurboGears services very
easy.  Please see the `client documentation`_ for more details

.. _`client documentation`: doc/client.rst

-----------------
Building the docs
-----------------

You'll need to install python-sphinx for this::

    yum install python-sphinx

Then run this command::

    python setup.py build_sphinx

------------
Translations
------------

The strings in python-fedora has mainly error messages.  These are translated
so we should make sure that translators are able to translate them when
necessary.  You will need babel, setuptools, and zanata-client to run these
commands::

    yum install babel setuptools zanata-client

Much information about using zanata for translations can be found in the
`zanata user's guide`_.  The information in this section is largely from
experimenting with the information in the `zanata client documentation`_

.. _`zanata user's guide`: http://zanata.readthedocs.org
.. _`zanata client documentation`: http://zanata-client.readthedocs.org/en/latest/

Updating the POT File
=====================

When you make changes that change the translatable strings in the package, you
should update the POT file.  Use the following distutils command (provided by
python-babel) to do that::

    ./setup.py extract_messages -o translations/python-fedora.pot
    zanata-cli push

Then commit your changes to source control.

Updating the PO Files
=====================

`fedora.zanata.org <https://fedora.zanata.org/>`_ will merge the strings inside the pot file with the already
translated strings.  To merge these, we just need to pull revised versions of
the po files::

    zanata-cli pull

Then commit the changes to source control (look for any brand new PO files that
zanata may have created).

Creating a new PO File
======================

The easiest way to create a new po file for a new language is in 's
web UI.

* Visit `this <https://fedora.zanata.org/iteration/view/python-fedora>`_


Compiling Message Catalogs
==========================

Message catalogs can be compiled for testing and should always be compiled
just prior to release.  Do this with the following script::

    python releaseutils.py build_catalogs

Compiled message catalogs should not be committed to source control.

Installing Message Catalogs
===========================

``python releaseutils.py install_catalogs`` will install the catalogs.  This
command may be customized through the use of environment variables.  See ``python
releaseutils.py --help`` for details.

-------
Release
-------

0) Commit all features, hotfixes, etc that you want in the release into the
   develop branch.

1) Checkout a copy of the repository and setup git flow::

        git clone https://github.com/fedora-infra/python-fedora.git
        cd python-fedora
        git flow init

2) Create a release branch for all of our work::

        git flow release start $VERSION

3) Download new translations and verify they are valid by compiling them::

        zanata-cli pull
        python releaseutils.py build_catalogs
        # If everything checks out
        git commit -m 'Merge new translations from fedora.zanata.org'

4) Make sure that the NEWS file is accurate (use ``git log`` if needed).

5) Update python-fedora.spec and fedora/release.py with the new version
   information.::

        # Make edits to python-fedora.spec and release.py
        git commit

6) Make sure the docs are proper and publish them::

        # Build docs and check for errors
        python setup.py build_sphinx
        # pypi
        python setup.py upload_docs

7) Push the release branch to the server::

        # Update files
        git flow release publish $VERSION

8) Go to a temporary directory and checkout a copy of the release::

        cd ..
        git clone https://github.com/fedora-infra/python-fedora.git release
        cd release
        git checkout release/$VERSION

9) Create the tarball in this clean checkout::

        python setup.py sdist

10) copy the dist/python-fedora-VERSION.tar.gz and python-fedora.spec files to
    where you build Fedora RPMS.  Do a test build::

        cp dist/python-fedora-*.tar.gz python-fedora.spec /srv/git/python-fedora/
        pushd /srv/git/python-fedora/
        fedpkg switch-branch master
        make mockbuild

11) Make sure the build completes.  Run rpmlint on the results.  Install and
    test the new packages::

        rpmlint *rpm
        sudo rpm -Uvh *noarch.rpm
        [test]

12) When satisfied that the build works, create a fresh tarball and upload to
    pypi::

        popd   # Back to the release directory
        python setup.py sdist upload --sign

13) copy the same tarball to fedorahosted.  The directory to upload to is
    slightly different for fedorahosted admins vs normal fedorahosted users:
    Admin::

        scp dist/python-fedora*tar.gz* fedorahosted.org:/srv/web/releases/p/y/python-fedora/

    Normal contributor::

        scp dist/python-fedora*tar.gz* fedorahosted.org:python-fedora

14) mark the release as finished in git::

        cd ../python-fedora
        git flow release finish $VERSION
        git push --all
        git push --tags

15) Finish building and pushing packages for Fedora.
