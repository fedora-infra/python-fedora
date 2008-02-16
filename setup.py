#!/usr/bin/python -tt

from fedora.release import *

from setuptools import setup, find_packages

setup(name=NAME,
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
        #install_requires=['psycopg2'],
        extras_require = {'tg' : ['TurboGears >= 1.0.4']},
        entry_points = {
            'turbogears.identity.provider' : (
                'sabugzilla = fedora.tg.identity.sabzprovider:SaBugzillaIdentityProvider [tg]',
                'safas = fedora.tg.identity.safasprovider:SaFasIdentityProvider [tg]',
                'safas2 = fedora.tg.identity.safas2provider:SaFas2IdentityProvider [tg]')
            'turbogears.visit.manager' : 'safas = fedora.tg.visit.safasvisit:SaFasVisitManager [tg]'
            }
        )
