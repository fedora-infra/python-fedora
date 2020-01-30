#!/usr/bin/python -tt
import sys

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
    packages=find_packages(),
    py_modules=['flask_fas', 'flask_fas_openid'],
    include_package_data=True,
    # non-setuptools package.  When everything we care about uses
    # python-2.5 distutils we can add these:
    #   for bodhi (koji yum)
    install_requires=[
        'munch',
        'kitchen',
        'requests',
        'beautifulsoup4',
        'urllib3',
        'six >= 1.4.0',
        'lockfile',
        'openidc-client',
    ],
    extras_require={
        'wsgi': ['repoze.who', 'Beaker', 'Paste'],
        'flask': [
            'Flask', 'Flask_WTF', 'python-openid', 'python-openid-teams',
            'python-openid-cla',
        ],
    },
    message_extractors={
        'fedora': [
            ('**.py', 'python', None),
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: GNU Lesser General Public License v2 or later (LGPLv2+)',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)
