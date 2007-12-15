# -*- coding: utf-8 -*-
#
# Copyright © 2007  Red Hat, Inc. All rights reserved.
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
#

'''
python-fedora, python module to interact with Fedora Infrastructure Services
'''

import os

class FASError(Exception):
    pass

class AuthError(FASError):
    pass

def retrieve_db_info(dbKey):
    '''Retrieve information to connect to the db from the filesystem.
    
    Arguments:
    :dbKey: The string identifying the database entry in the config file.

    Returns: A dictionary containing the values to use in connecting to the
      database.

    Exceptions:
    :IOError: Returned if the config file is not on the system.
    :AuthError: Returned if there is no record found for dbKey in the
      config file.
    '''
    # Open a filehandle to the config file
    if os.environ.has_key('HOME') and os.path.isfile(
            os.path.join(os.environ.get('HOME'), '.fedora-db-access')):
        fh = file(os.path.join(
            os.environ.get('HOME'), '.fedora-db-access'), 'r')
    elif os.path.isfile('/etc/sysconfig/fedora-db-access'):
        fh = file('/etc/sysconfig/fedora-db-access', 'r')
    else:
        raise IOError, 'fedora-db-access file does not exist.'

    # Read the file until we get the information for the requested db
    dbInfo = None
    for line in fh.readlines():
        if not line:
            break
        line = line.strip()
        if not line or line[0] == '#':
            continue
        pieces = line.split(None, 1)
        if len(pieces) < 2:
            continue
        if pieces[0] == dbKey:
            dbInfo = eval(pieces[1])
            break

    if fh:
        fh.close()
    if not dbInfo:
        raise AuthError, 'Authentication source "%s" not configured' % (dbKey,)
    return dbInfo

