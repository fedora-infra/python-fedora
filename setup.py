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
                'jsonfas = fedora.tg.identity.jsonfasprovider:JsonFasIdentityProvider [tg]'),
            'turbogears.visit.manager' : (
                'jsonfas = fedora.tg.visit.jsonfasvisit:JsonFasVisitManager [tg]')
            }
        )
