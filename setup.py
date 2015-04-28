#!/usr/bin/python -tt
import sys

# Work around setuptools multi-version silliness
try:
    __requires__ = ['Sphinx >= 1.0']
    if sys.version_info[0] == 2:
        __requires__.append('CherryPy < 3')
    import pkg_resources
except:
    # And also workaround the workaround being broken inside of a virtualenv
    # *sigh*  setuptools is such a broken implementation
    # When setuptools is imported later, it will see the CherryPy requirement
    # and barf.  So we have to delete it here.
    del __requires__

exec(compile(open("fedora/release.py").read(), "fedora/release.py", 'exec'))

from setuptools import find_packages, setup

setup(
    name=NAME,
    version=VERSION,
    description=DESCRIPTION,
    author=AUTHOR,
    author_email=EMAIL,
    license=LICENSE,
    keywords='Fedora Python Webservices',
    url=URL,
    download_url=DOWNLOAD_URL,
    packages=find_packages(),
    py_modules=['flask_fas', 'flask_fas_openid'],
    include_package_data=True,
    # non-setuptools package.  When everything we care about uses
    # python-2.5 distutils we can add these:
    #   for bodhi (koji yum)
    install_requires=['munch', 'kitchen', 'requests', 'beautifulsoup4', 'urllib3', 'six'],
    extras_require={
        'tg': ['TurboGears >= 1.0.4', 'SQLAlchemy', 'decorator'],
        'wsgi': ['repoze.who', 'Beaker', 'Paste'],
        'flask': [
            'Flask', 'Flask_WTF', 'python-openid', 'python-openid-teams',
            'python-openid-cla',
        ],
    },
    entry_points={
        'turbogears.identity.provider': (
            'jsonfas = fedora.tg.identity.jsonfasprovider1:JsonFasIdentityProvider [tg]',
            'jsonfas2 = fedora.tg.identity.jsonfasprovider2:JsonFasIdentityProvider [tg]',
            'sqlobjectcsrf = fedora.tg.identity.soprovidercsrf:SqlObjectCsrfIdentityProvider [tg]'),
        'turbogears.visit.manager': (
            'jsonfas = fedora.tg.visit.jsonfasvisit1:JsonFasVisitManager [tg]',
            'jsonfas2 = fedora.tg.visit.jsonfasvisit2:JsonFasVisitManager [tg]'
        ),
    },
    message_extractors={
        'fedora': [
            ('**.py', 'python', None),
            ('tg2/templates/mako/**.mak', 'mako', None),
            ('tg2/templates/genshi/**.html', 'mako', None),
            ('tg/templates/genshi/**.html', 'genshi', None),
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Framework :: TurboGears',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: GNU Lesser General Public License v2 or later (LGPLv2+)',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)
