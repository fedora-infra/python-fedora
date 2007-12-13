#!/usr/bin/python -tt

from setuptools import setup, find_packages

setup(name='python-fedora',
        version='0.2.90.22',
        description='Fedora Specific Python Modules',
        author='Toshio Kuratomi',
        author_email='toshio@fedoraproject.org',
        license='GPLv2',
        keywords='Fedora Python Modules',
        url='https://hosted.fedoraproject.org/projects/python-fedora',
        packages=find_packages(),
        include_package_data=True,
        #install_requires=['psycopg2'],
        extras_require = {'tg' : ['TurboGears >= 1.0b']},
        entry_points = {
            'turbogears.identity.provider' : (
                'sabugzilla = fedora.tg.identity.sabzprovider:SaBugzillaIdentityProvider [tg]',
                'safas = fedora.tg.identity.safasprovider:SaFasIdentityProvider [tg]',
                'safas2 = fedora.tg.identity.safas2provider:SaFas2IdentityProvider [tg]'),
            'turbogears.visit.manager' : 'safas = fedora.tg.visit.safasvisit:SaFasVisitManager [tg]'}
        )
