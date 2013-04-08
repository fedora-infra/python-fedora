#!/usr/bin/python -tt

import ConfigParser
import glob
import os
import shutil
from kitchen.pycompat27 import subprocess

class MsgFmt(object):
    def run(self, args):
        cmd = subprocess.Popen(args, shell=False)
        cmd.wait()

def setup_message_compiler():
    # Look for msgfmt
    try:
        subprocess.Popen(['msgfmt', '-h'], stdout=subprocess.PIPE)
    except OSError:
        import babel.messages.frontend

        return (babel.messages.frontend.CommandLineInterface(),
            'pybabel compile -D %(domain)s -d locale -i %(pofile)s -l %(lang)s'
            )
    else:
        return (MsgFmt(), 'msgfmt -c -o locale/%(lang)s/LC_MESSAGES/%(domain)s.mo %(pofile)s')

def main():
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

if __name__ == '__main__':
    main()
