#!/usr/bin/python -tt
# coding: utf-8
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#
# Copyright 2008-2009  Red Hat, Inc
'''
A Wiki Client

.. moduleauthor:: Luke Macken <lmacken@redhat.com>
.. moduleauthor:: Toshio Kuratomi <tkuratom@redhat.com>
'''

from datetime import datetime, timedelta
from fedora.client import BaseClient

class Wiki(BaseClient):

    def __init__(self, base_url='http://fedoraproject.org/w/', *args, **kw):
        super(Wiki, self).__init__(base_url, *args, **kw)

    def get_recent_changes(self, now, then, limit=500):
        """ Get recent wiki changes from `now` until `then` """
        data = self.send_request('api.php', req_params={
                'list'    : 'recentchanges',
                'action'  : 'query',
                'format'  : 'json',
                'rcprop'  : 'user|title',
                'rcend'   : then.isoformat().split('.')[0] + 'Z',
                'rclimit' : limit,
                })
        if 'error' in data:
            raise Exception(data['error']['info'])
        return data['query']['recentchanges']

    def login(self, username, password):
        data = self.send_request('api.php', req_params={
                'action': 'login',
                'format': 'json',
                'lgname': username,
                'lgpassword': password,
                })
        if 'lgtoken' not in data.get('login', {}):
            raise Exception('Login failed: %s' % data)
        #self.session_id = data['login']['lgtoken']
        #self.username = data['login']['lgusername']
        return data

    def print_recent_changes(self, days=7, show=10):
        now = datetime.utcnow()
        then = now - timedelta(days=days)
        print "From %s to %s" % (then, now)
        changes = self.get_recent_changes(now=now, then=then)
        num_changes = len(changes)
        print "%d wiki changes in the past week" % num_changes
        if num_changes == 500:
            print "Warning: Number of changes reaches the API return limit."
            print "You will not get the complete list of changes unless "
            print "you run this script using a 'bot' account."

        users = {}
        pages = {}
        for change in changes:
            users.setdefault(change['user'], []).append(change['title'])
            pages[change['title']] = pages.setdefault(change['title'], 0) + 1

        print '\n== Most active wiki users =='
        for user, changes in sorted(users.items(),
                                    cmp=lambda x, y: cmp(len(x[1]), len(y[1])),
                                    reverse=True)[:show]:
            print ' %-50s %d' % (('%s' % user).ljust(50, '.'),
                                  len(changes))

        print '\n== Most edited pages =='
        for page, num in sorted(pages.items(),
                                cmp=lambda x, y: cmp(x[1], y[1]),
                                reverse=True)[:show]:
            print ' %-50s %d' % (('%s' % page).ljust(50, '.'), num)


if __name__ == '__main__':
    #from getpass import getpass
    #username = raw_input('Username: ')
    #password = getpass()
    wiki = Wiki()
    #cookie = wiki.login(username=username, password=password)
    #print "login response =", cookie
    #wiki = Wiki(username=username, session_id=cookie['login']['lgtoken'],
    #            session_name='fpo-mediawiki_en_Token')
    wiki.print_recent_changes()
