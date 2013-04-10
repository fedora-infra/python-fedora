#!/usr/bin/python -tt
from __future__ import print_function

import ConfigParser
import glob
import os
import shutil
import sys

from contextlib import contextmanager

from kitchen.pycompat27 import subprocess

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
    try:
        _install_catalogs(os.path.join(ENVVARS['DESTDIR'], 'usr', 'share', 'locale'))
    except:
        # Didn't work so try installing where the module was installed.  This
        # isn't perfect because the module might have been installed in a
        # different location from setup.py.  Better integration with setup.py
        # might fix that.
        # For a generic utility to be used with other modules, this would also
        # need to handle arch-specific locations (get_python_lib(1))
        from distutils.sysconfig import get_python_lib
        localedir = get_python_lib()
        if ENVVARS['PACKAGENAME'] is None:
            print ('Set the PACKAGENAME environment variable and try again')
            sys.exit(2)
        localedir = os.path.join(localedir, ENVVARS['PACKAGENAME'], 'locale')
        if ENVVARS['DESTDIR'] is not None:
            if localedir.startswith('/'):
                localedir = localedir[1:]
            localedir = os.path.join(ENVVARS['DESTDIR'], localedir)
        _install_catalogs(localedir)

def usage():
    print ('Subcommands:')
    for command in sorted(SUBCOMMANDS.keys()):
        print('%-15s  %s' % (command, SUBCOMMANDS[command][1]))

    print()
    print('Parameter passing: This script can be customized using the following'
          ' ENV VARS:')
    for var in sorted(ENVVARDESC.keys()):
        print('%-15s  %s' % (var, ENVVARDESC[var]))

    sys.exit(1)

SUBCOMMANDS = {'build_catalogs': (build_catalogs, 'Compile the message catalogs from po files'),
               'install_catalogs': (install_catalogs, 'Install the message catalogs to the system'),
               }

ENVVARDESC = {'DESTDIR': 'Alternate root directory hierarchy to install into',
              'PACKAGENAME': 'Python packagename (commonly the setup.py name field)',
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
