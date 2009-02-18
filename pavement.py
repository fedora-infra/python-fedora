from paver.defaults import *

import sys, os
import glob
import paver.doctools
import paver.runtime
import paver.path

from setuptools import find_packages

sys.path.insert(0, str(paver.runtime.path.getcwd()))

from fedora.release import *

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
        extras_require = {'tg' : ['TurboGears >= 1.0.4', 'SQLAlchemy',
            'decorator']},
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
        ),
    pylint=Bunch(
        module=['fedora']
        ),
    publish=Bunch(
        doc_location='fedorahosted.org:/srv/web/releases/p/y/python-fedora/doc/',
        tarball_location='fedorahosted.org:/srv/web/releases/p/y/python-fedora/'
        ),
    )

@task
@needs(['html'])
def publish_doc():
    options.order('publish', add_rest=True)
    command = 'rsync -av build-doc/html/ %s' % (options.doc_location,)
    dry(command, paver.runtime.sh, [command])

@task
@needs(['sdist'])
def publish_tarball():
    options.order('publish', add_rest=True)
    tarname = '%s-%s.tar.gz' % (options.name, options.version)
    command = 'scp dist/%s %s' % (tarname, options.tarball_location)
    dry(command, paver.runtime.sh, [command])

@task
@needs(['publish_doc', 'publish_tarball'])
def publish():
    pass

#
# Generic Tasks
#

try:
    from pylint import lint
    has_pylint = True
except ImportError:
    has_pylint = False

if has_pylint:
    @task
    def pylint():
        '''Check the module you're building with pylint.'''
        options.order('pylint', add_rest=True)
        pylintopts = options.module
        dry('pylint %s' % (" ".join(pylintopts)), lint.Run, pylintopts)


