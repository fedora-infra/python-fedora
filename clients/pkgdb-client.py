#!/usr/bin/python -tt
# -*- coding: utf-8 -*-
#
# Copyright © 2008  Red Hat, Inc. All rights reserved.
#
# This copyrighted material is made available to anyone wishing to use, modify,
# copy, or redistribute it subject to the terms and conditions of the GNU
# General Public License v.2.  This program is distributed in the hope that it
# will be useful, but WITHOUT ANY WARRANTY expressed or implied, including the
# implied warranties of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.  You should have
# received a copy of the GNU General Public License along with this program;
# if not, write to the Free Software Foundation, Inc., 51 Franklin Street,
# Fifth Floor, Boston, MA 02110-1301, USA. Any Red Hat trademarks that are
# incorporated in the source code or documentation are not subject to the GNU
# General Public License and may only be used or replicated with the express
# permission of Red Hat, Inc.
#
# Author(s): Toshio Kuratomi <tkuratom@redhat.com>
# Author(s): Mike Watters <valholla@fedoraproject.org>
#

__version__ = '0.3'

__requires__ = 'TurboGears'

import pkg_resources
pkg_resources.require('CherryPy >= 2.0, < 3.0alpha')

import sys
import os
import optparse
import getpass

from fedora.client import BaseClient, AuthError, PackageDBClient

import turbogears
from turbogears import config

turbogears.update_config(configfile = "/etc/pkgdb-client.cfg")
from turbogears.database import session

PACKAGEDBURL = config.get('pkgdb.url', 'https://admin.fedoraproject.org/pkgdb')
RETRIES = config.get('pkgdb.retries')
KNOWNGROUPS = config.get('pkgdb.knowngroups')

class ArgumentsError(Exception):
    pass

def store_groups(option, opt, group, parser, enable):
    parser.values.ensure_value(option.dest, {})[group] = enable

def parse_commands():
    parser = optparse.OptionParser(version = __version__,
            usage='''pkgdb-client [options] packagename

Example: pkgdb-client -u toshio -o testowner -d 'Purely a test package' -b devel -b F-7 -b EL-5 -c toshio -c kevin -m wtogami fedoratest

''')
    parser.add_option('-u', '--username',
            dest='username',
            action='store',
            default=getpass.getuser(),
            help='Set username to connect to the Package Database')
## This is insecure, do not give the user an option.
#    parser.add_option('-p', '--password',
#            dest='password',
#            action='store',
#            help='Set password to connect to the Password Database *** Warning: more secure to enter this interactively')
    parser.add_option('-o', '--owner',
            dest='owner',
            action='store',
            help='Primary owner of the package on the branch')
    parser.add_option('-d', '--description',
            dest='description',
            action='store',
            help='Short description of a package')
    parser.add_option('-b', '--branch',
            dest='branchList',
            action='append',
            help='Branch of package to create and make changes to.  May specify multiple times')
    parser.add_option('--master',
            dest='masterBranch',
            action='store',
            help='Take permissions from this branch and apply to branches specified with -b')
    parser.add_option('-c', '--cc-member',
            dest='ccList',
            action='append',
            help='Person to cc on bugs and commits for this branch.  May be specified multiple times')
    parser.add_option('-m', '--maintainer',
            dest='comaintList',
            action='append',
            help='Comaintainers for this branch.  May be specified multiple times')
    parser.add_option('--remove-user',
            dest='removeUserList',
            action='append',
            help='Remove a user from the package acls [Not Yet Implemented]')
    parser.add_option('-a', '--add-group',
            action='callback',
            callback=store_groups,
            callback_args=(True,),
            type='string',
            dest='groups',
            help='Allow GROUP to commit to this branch.  May be specified multiple times.')
    parser.add_option('-r', '--remove-group',
            action='callback',
            callback=store_groups,
            callback_args=(False,),
            type='string',
            dest='groups',
            help='Remove commit access for GROUP on this branch.  May be specified multiple times.')
    (opts, args) = parser.parse_args()

    # Must specify a  package name
    if len(args) < 1:
        raise ArgumentsError, 'No package name'
    else:
        opts.packages = args

    # We only know how to handle a few groups right now.
    if opts.groups:
        for group in opts.groups:
            if group not in KNOWNGROUPS:
                raise ArgumentsError('Do not know how to handle group %s at this time' % group)

    return opts

if __name__ == '__main__':
    try:
        options = parse_commands()
    except ArgumentsError, e:
        print e
        sys.exit(1)

    # changed this to getpass after changing to disallow the --password command
    # line option
    password = getpass.getpass('PackageDB Password:')
    pkgdb = PackageDB(PACKAGEDBURL, username=options.username,
            password=password)
    failedPackages = {}
    for package in options.packages:
        for retry in range(0, RETRIES+1):
            try:
                if options.masterBranch:
                    pkgdb.clone_branch(package, options.masterBranch,
                            options.owner, options.description,
                            options.branchList, options.ccList,
                            options.comaintList, options.groups)
                else:
                    pkgdb.add_edit_package(package, options.owner,
                            options.description, options.branchList,
                            options.ccList, options.comaintList, options.groups)
            except AuthError, e:
                if sys.stdin.isatty():
                    if retry >= RETRIES:
                        failedPackages[package] = e
                        break
                    pkgdb.password = getpass.getpass('Password: ')
                else:
                    if retry > 0:
                        failedPackages[package] = e
                        break
                    pkgdb.password = sys.stdin.readline().rstrip()
            except Exception, e:
                failedPackages[package] = e
                break
            else:
                break

    if failedPackages:
        print 'Packages which had errors:'
        for pkg in failedPackages:
            print '%s: %s' % (pkg, failedPackages[pkg])
        sys.exit(1)
    sys.exit(0)
