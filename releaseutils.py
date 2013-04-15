#!/usr/bin/python -tt

# Copyright Red Hat Inc 2013
# Licensed under the terms of the LGPLv2+

from __future__ import print_function

import ConfigParser
import glob
import os
import shutil
import sys
import textwrap

from contextlib import contextmanager
from distutils.sysconfig import get_python_lib
from distutils.util import get_platform

from kitchen.pycompat27 import subprocess
import pkg_resources

import fedora.release

#
# Helper function
#

@contextmanager
def pushd(dirname):
    '''Contextmanager so that we can switch directories that the script is
    running in and have the current working directory restored  afterwards.
    '''
    curdir = os.getcwd()
    os.chdir(dirname)
    try:
        yield curdir
    finally:
        os.chdir(curdir)

class MsgFmt(object):
    def run(self, args):
        cmd = subprocess.Popen(args, shell=False)
        cmd.wait()

def setup_message_compiler():
    # Look for msgfmt
    try:
        # Prefer msgfmt because it will throw errors on misformatted messages
        subprocess.Popen(['msgfmt', '-h'], stdout=subprocess.PIPE)
    except OSError:
        import babel.messages.frontend

        return (babel.messages.frontend.CommandLineInterface(),
            'pybabel compile -D %(domain)s -d locale -i %(pofile)s -l %(lang)s'
            )
    else:
        return (MsgFmt(), 'msgfmt -c -o locale/%(lang)s/LC_MESSAGES/%(domain)s.mo %(pofile)s')


def build_catalogs():
    # Get the directory with message catalogs
    # Reuse transifex's config file first as it will know this
    cfg = ConfigParser.SafeConfigParser()
    cfg.read('.tx/config')
    cmd, args = setup_message_compiler()

    try:
        shutil.rmtree('locale')
    except OSError, e:
        # If the error is that locale does not exist, we're okay.  We're
        # deleting it here, afterall
        if e.errno != 2:
            raise

    for section in [s for s in cfg.sections() if s != 'main']:
        try:
            file_filter = cfg.get(section, 'file_filter')
            source_file = cfg.get(section, 'source_file')
        except ConfigParser.NoOptionError:
            continue
        glob_pattern = file_filter.replace('<lang>', '*')
        pot = os.path.basename(source_file)
        if pot.endswith('.pot'):
            pot = pot[:-4]
        arg_values = {'domain': pot}
        for po_file in glob.glob(glob_pattern):
            file_pattern = os.path.basename(po_file)
            lang = file_pattern.replace('.po','')
            os.makedirs(os.path.join('locale', lang, 'LC_MESSAGES'))
            arg_values['pofile'] = po_file
            arg_values['lang'] = lang
            compile_args = args % arg_values
            compile_args = compile_args.split(' ')
            cmd.run(compile_args)

def _add_destdir(path):
    if ENVVARS['DESTDIR'] is not None:
        if path.startswith('/'):
            path = path[1:]
        path = os.path.join(ENVVARS['DESTDIR'], path)
    return path

def _install_catalogs(localedir):
    with pushd('locale'):
        for catalog in glob.glob('*/LC_MESSAGES/*.mo'):
            # Make the directory for the locale
            dirname = os.path.dirname(catalog)
            dst = os.path.join(localedir, dirname)
            try:
                os.makedirs(dst, 0755)
            except OSError as e:
                # Only allow file exists to pass
                if e.errno != 17:
                    raise
            shutil.copy2(catalog, dst)

def install_catalogs():
    # First try to install the messages to an FHS location
    if ENVVARS['INSTALLSTRATEGY'] == 'EGG':
        localedir = get_python_lib()

        # Need certain info from the user
        if ENVVARS['PACKAGENAME'] is None:
            print ('Set the PACKAGENAME environment variable and try again')
            sys.exit(2)
        if ENVVARS['MODULENAME'] is None:
            print ('Set the MODULENAME environment variable and try again')
            sys.exit(2)

        # Get teh egg name from pkg_resources
        dist = pkg_resources.Distribution(project_name=ENVVARS['PACKAGENAME'],
                                          version=fedora.release.VERSION)

        # Set the localedir to be inside the egg directory
        localedir = os.path.join(localedir, '{}.egg'.format(dist.egg_name()),
                                 ENVVARS['MODULENAME'], 'locale')
        # Tack on DESTDIR if needed
        localedir = _add_destdir(localedir)
        _install_catalogs(localedir)

    elif ENVVARS['INSTALLSTRATEGY'] == 'SITEPACKAGES':
        # For a generic utility to be used with other modules, this would also
        # need to handle arch-specific locations (get_python_lib(1))

        # Retrieve the site-packages directory
        localedir = get_python_lib()

        # Set the install path to be inside of the module in site-packages
        if ENVVARS['MODULENAME'] is None:
            print ('Set the MODULENAME environment variable and try again')
            sys.exit(2)
        localedir = os.path.join(localedir, ENVVARS['MODULENAME'], 'locale')
        localedir = _add_destdir(localedir)
        _install_catalogs(localedir)

    else:
        # FHS
        localedir = _add_destdir('/usr/share/locale')
        _install_catalogs(localedir)

def usage():
    print ('Subcommands:')
    for command in sorted(SUBCOMMANDS.keys()):
        print('%-15s  %s' % (command, SUBCOMMANDS[command][1]))

    print()
    print('This script can be customized by setting the following ENV VARS:')
    for var in sorted(ENVVARDESC.keys()):
        for line in textwrap.wrap('%-15s  %s' % (var, ENVVARDESC[var]), subsequent_indent=' '*8):
            print(line.rstrip())
    sys.exit(1)

SUBCOMMANDS = {'build_catalogs': (build_catalogs, 'Compile the message catalogs from po files'),
               'install_catalogs': (install_catalogs, 'Install the message catalogs to the system'),
               }

ENVVARDESC = {'DESTDIR': 'Alternate root directory hierarchy to install into',
              'PACKAGENAME': 'Pypi packagename (commonly the setup.py name field)',
              'MODULENAME': 'Python module name (commonly used with import NAME)',
              'INSTALLSTRATEGY': 'One of FHS, EGG, SITEPACKAGES.  FHS will work'
              ' for system packages installed using'
              ' --single-version-externally-managed.  EGG install into an egg'
              ' directory.  SITEPACKAGES will install into a $PACKAGENAME'
              ' directory directly in site-packages.  Default FHS'
              }

ENVVARS = dict(map(lambda k: (k, os.environ.get(k)), ENVVARDESC.keys()))

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('At least one subcommand is needed\n')
        usage()
    try:
        SUBCOMMANDS[sys.argv[1]][0]()
    except KeyError:
        print ('Unknown subcommand: %s\n' % sys.argv[1])
        usage()
