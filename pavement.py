#!/usr/bin/python -tt

from paver.defaults import *
from fedora.release import *

import paver.doctools
from setuptools import setup, find_packages

options(
    setup = Bunch(
        name=NAME,
        version=VERSION,
        description=DESCRIPTION,
        author=AUTHOR,
        author_email=EMAIL,
        license=LICENSE,
        keywords='Fedora Python Modules',
        url=URL,
        download_url=DOWNLOAD_URL,
        packages=find_packages(),
        include_package_data=True,
        # non-setuptools package.  When everything we care about uses
        # python-2.5 distutils we can add these:
        #   for bodhi (koji yum)
        install_requires=['simplejson'],
        # And these to extra_require:
        #   for widgets: (bugzilla feedparser)
        extras_require = {'tg' : ['TurboGears >= 1.0.4', 'SQLAlchemy']},
        entry_points = {
            'turbogears.identity.provider' : (
                'jsonfas = fedora.tg.identity.jsonfasprovider:JsonFasIdentityProvider [tg]'),
            'turbogears.visit.manager' : (
                'jsonfas = fedora.tg.visit.jsonfasvisit:JsonFasVisitManager [tg]')
            }
        ),
    sphinx=Bunch(
        docroot='.',
        builddir='build-doc',
        sourcedir='doc'
        )


    )
