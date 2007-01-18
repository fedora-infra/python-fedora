#!/usr/bin/python -tt

from setuptools import setup, find_packages

setup(name='python-fedora',
        version='0.1',
        description='Fedora Specific Python Modules',
        author='Toshio Kuratomi',
        author_email='toshio@fedoraproject.org',
        license='GPL',
        keywords='Fedora Account System',
        url='http://www.fedoraproject.org/wiki/Infrastructure/AccountSystem2/API',
        packages=find_packages(),
        #install_requires=['psycopg2'],
        extras_require = {'tg' : ['TurboGears >= 1.0b']},
        entry_points = {
            'turbogears.identity.provider' : 'safas = fedora.tg.identity.safasprovider:SaFasIdentityProvider [tg]',
            'turbogears.visit.manager' : 'safas = fedora.tg.visit.safasvisit:SaFasVisitManager [tg]'}
        )
