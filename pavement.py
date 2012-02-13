try:
    # 1.0
    from paver.easy import path as paver_path
    from paver.easy import sh as paver_sh
    from paver.easy import *
    import paver.misctasks
    from paver import setuputils
    setuputils.install_distutils_tasks()
    PAVER_VER = '1.0'
except ImportError:
    # 0.8
    from paver.defaults import *
    from paver.runtime import path as paver_path
    from paver.runtime import sh as paver_sh
    PAVER_VER = '0.8'

import sys, os
import glob
import paver.doctools
from setuptools import find_packages, command

sys.path.insert(0, str(paver_path.getcwd()))

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
        #   pycurl
        install_requires=['bunch', 'kitchen'],
        # And these to extra_require:
        #   for widgets: (bugzilla feedparser)
        extras_require = {
            'tg' : ['TurboGears >= 1.0.4', 'SQLAlchemy', 'decorator'],
            'wsgi': ['repoze.who', 'Beaker', 'Paste'],
            },
        test_require = ['TurboGears >= 2.0', 'nose', ],
        entry_points = {
            'turbogears.identity.provider' : (
                'jsonfas = fedora.tg.identity.jsonfasprovider1:JsonFasIdentityProvider [tg]',
                'jsonfas2 = fedora.tg.identity.jsonfasprovider2:JsonFasIdentityProvider [tg]',
                'sqlobjectcsrf = fedora.tg.identity.soprovidercsrf:SqlObjectCsrfIdentityProvider [tg]'),
            'turbogears.visit.manager' : (
                'jsonfas = fedora.tg.visit.jsonfasvisit1:JsonFasVisitManager [tg]',
                'jsonfas2 = fedora.tg.visit.jsonfasvisit2:JsonFasVisitManager [tg]'),
            # Needed for the test suite
            'paste.app_factory' : (
                'main = fedora.wsgi.test.testapp:make_app'),
            'paste.app_install' : (
                'main = pylons.util:PylonsInstaller'),
            'paste.filter_app_factory': (
                'faswho = fedora.wsgi.faswho:make_faswho_middleware')
            },
        message_extractors = {
            'fedora': [('**.py', 'python', None),
                ('tg2/templates/mako/**.mak', 'mako', None),
                ('tg2/templates/genshi/**.html', 'mako', None),
                ('tg/templates/genshi/**.html', 'genshi', None),],
            },
        classifiers = [
            'Development Status :: 4 - Beta',
            'Framework :: TurboGears',
            'Framework :: Django',
            'Intended Audience :: Developers',
            'Intended Audience :: System Administrators',
            'License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)',
            'Programming Language :: Python :: 2.4',
            'Programming Language :: Python :: 2.5',
            'Programming Language :: Python :: 2.6',
            'Programming Language :: Python :: 2.7',
            'Topic :: Internet :: WWW/HTTP',
            'Topic :: Software Development :: Libraries :: Python Modules',
            ],
        ),
    minilib=Bunch(
        extra_files=['doctools']
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
    i18n=Bunch(
        builddir='locale',
        installdir='/usr/share/locale',
        domain='python-fedora',
        ),
    ### FIXME: These are due to a bug in paver-1.0
    # http://code.google.com/p/paver/issues/detail?id=24
    sdist=Bunch(),
    )

@task
@needs(['html'])
def publish_doc():
    options.order('publish', add_rest=True)
    command = 'rsync -av build-doc/html/ %s' % (options.doc_location,)
    if PAVER_VER == '0.8':
        command = [command]
    dry(command, paver_sh, command)

@task
@needs(['sdist'])
def publish_tarball():
    options.order('publish', add_rest=True)
    tarname = '%s-%s.tar.gz' % (options.name, options.version)
    command = 'scp dist/%s %s' % (tarname, options.tarball_location)
    if PAVER_VER == '0.8':
        command = [command]
    dry(command, paver_sh, command)

@task
@needs(['publish_doc', 'publish_tarball'])
def publish():
    pass

try:
    import babel.messages.frontend
    has_babel = True
except ImportError:
    has_babel = False

if has_babel and PAVER_VER != '0.8':
    @task
    def make_catalogs():
        '''Compile all message catalogs for release'''
        options.order('i18n', add_rest=True)
        for po_file in glob.glob('translations/*.po'):
            locale, ext = os.path.splitext(os.path.basename(po_file))
            build_dir = paver_path(os.path.join(options.builddir, locale,
                'LC_MESSAGES'))

            try:
                build_dir.makedirs(mode=0755)
            except OSError, e:
                # paver < 1.0 raises if directory exists
                if e.errno == 17:
                    pass
                else:
                    raise
            if 'compile_catalog' in options.keys():
                defaults = options.compile_catalog
            else:
                defaults = Bunch(domain=options.domain,
                        directory=options.builddir)
                options.compile_catalog = defaults

            defaults.update({'input-file': po_file, 'locale': locale})
            ### FIXME: compile_catalog cannot handle --dry-run on its own
            dry('paver compile_catalog -D %(domain)s -d %(directory)s'
                    ' -i %(input-file)s --locale %(locale)s' % defaults,
                    paver_sh, 'paver compile_catalog -D %(domain)s' \
                        ' -d %(directory)s -i %(input-file)s' \
                        ' --locale %(locale)s' % defaults)
            ### FIXME: Need to get call_task to call this repeatedly
            # because options.compile_catalog has changed
            #dry('paver compile_catalog -D %(domain)s -d %(directory)s'
            #        ' -i %(input-file)s --locale %(locale)s' % defaults,
            #        call_task, 'babel.messages.frontend.compile_catalog', options)

#
# Backends
#

def _apply_root(args, path):
    '''Add the root value to the start of the path'''
    if 'root' in args:
        if path.startswith('/'):
            path = path[1:]
        path = paver_path(os.path.join(args['root'], path))
    else:
        path = paver_path(path)
    return path

def _install_catalogs(args):
    '''Install message catalogs in their proper location on the filesystem.

    Note: To use this with non-default commandline arguments, you must use 
    '''
    # Rebuild message catalogs
    if 'skip_build' not in args and 'skip-build' not in args:
        call_task('make_catalogs')

    options.order('i18n', add_rest=True)
    # Setup the install_dir
    if 'install_catalogs' in args:
        cat_dir = args['install_catalogs']
    elif 'install_data' in args:
        cat_dir = os.path.join(args['install_data'], 'locale')
    else:
        cat_dir = options.installdir

    # Setup the install_dir
    cat_dir = _apply_root(args, cat_dir)

    for catalog in paver_path(options.builddir).walkfiles('*.mo'):
        locale_dir = catalog.dirname()
        path = paver_path('.')
        for index, nextpath in enumerate(locale_dir.splitall()):
            path = path.joinpath(nextpath)
            if paver_path(options.builddir).samefile(path):
                install_locale = cat_dir.joinpath(os.path.join(
                        *locale_dir.splitall()[index + 1:]))
                try:
                    install_locale.makedirs(mode=0755)
                except OSError, e:
                    # paver < 1.0 raises if directory exists
                    if e.errno == 17:
                        pass
                    else:
                        raise
                install_locale = install_locale.joinpath(catalog.basename())
                if install_locale.exists():
                    install_locale.remove()
                dry('cp %s %s'%  (catalog, install_locale),
                        catalog.copy, install_locale)
                dry('chmod 0644 %s'%  install_locale,
                        install_locale.chmod, 0644)

@task
@cmdopts([('root=', None, 'Base root directory to install into'),
    ('install-catalogs=', None, 'directory that locale catalogs go in'),
    ('skip-build', None, 'Skip directly to installing'),
    ])
def install_catalogs():
    _install_catalogs(options.install_catalogs)
    pass

@task
@needs(['make_catalogs', 'setuptools.command.sdist'])
def sdist():
    pass

### FIXME: setuptools.command.install does not respond to --dry-run
if PAVER_VER != '0.8':
    # Paver 0.8 will have to explicitly install the message catalogs
    # As overriding setuptools.command gives errors on paver-0.8
    @task
    @needs(['setuptools.command.install'])
    def install():
        '''Override the setuptools install.'''
        _install_catalogs(options.install)

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


@task
def test():
    sh("nosetests --where=fedora/wsgi/test")
