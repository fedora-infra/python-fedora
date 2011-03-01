#!/usr/bin/python -tt
# -*- coding: utf-8 -*-
#
# Copyright 2008-2009  Red Hat, Inc.
# This file is part of python-fedora
# 
# python-fedora is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
# 
# python-fedora is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public
# License along with python-fedora; if not, see <http://www.gnu.org/licenses/>
#
'''
A Wiki Client

.. moduleauthor:: Luke Macken <lmacken@redhat.com>
.. moduleauthor:: Toshio Kuratomi <tkuratom@redhat.com>
.. moduleauthor:: Ian Weller <ian@ianweller.org>
'''

from datetime import datetime, timedelta
import time

from kitchen.text.converters import to_bytes

from fedora.client import BaseClient, AuthError
from fedora import _, b_

MEDIAWIKI_DATEFORMAT = "%Y-%m-%dT%H:%M:%SZ"

class Wiki(BaseClient):
    api_high_limits = False

    def __init__(self, base_url='https://fedoraproject.org/w/',
            *args, **kwargs):
        super(Wiki, self).__init__(base_url, *args, **kwargs)

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
            raise AuthError(b_('Login failed: %(data)s') %
                    {'data':to_bytes(data)})
        #self.session_id = data['login']['lgtoken']
        #self.username = data['login']['lgusername']
        self.check_api_limits()
        return data

    def check_api_limits(self):
        """ Checks whether you have the 'apihighlimits' right or not. """
        data = self.send_request('api.php', req_params={
                'action': 'query',
                'meta': 'userinfo',
                'uiprop': 'rights',
                'format': 'json',
                })
        self.api_high_limits = "apihighlimits" in \
                data['query']['userinfo']['rights']
        return self.api_high_limits

    def print_recent_changes(self, days=7, show=10):
        now = datetime.utcnow()
        then = now - timedelta(days=days)
        print _(u"From %(then)s to %(now)s") % {'then': then, 'now': now}
        changes = self.get_recent_changes(now=now, then=then)
        num_changes = len(changes)
        print _(u"%d wiki changes in the past week") % num_changes
        if num_changes == 500:
            print _(u"""Warning: Number of changes reaches the API return limit.
You will not get the complete list of changes unless
you run this script using a 'bot' account.""")

        users = {}
        pages = {}
        for change in changes:
            users.setdefault(change['user'], []).append(change['title'])
            pages[change['title']] = pages.setdefault(change['title'], 0) + 1

        print _(u'\n== Most active wiki users ==')
        for user, changes in sorted(users.items(),
                                    cmp=lambda x, y: cmp(len(x[1]), len(y[1])),
                                    reverse=True)[:show]:
            print u' %-50s %d' % (('%s' % user).ljust(50, '.'),
                                  len(changes))

        print _(u'\n== Most edited pages ==')
        for page, num in sorted(pages.items(),
                                cmp=lambda x, y: cmp(x[1], y[1]),
                                reverse=True)[:show]:
            print u' %-50s %d' % (('%s' % page).ljust(50, '.'), num)

    def fetch_all_revisions(self, start=1, flags=True, timestamp=True,
                            user=True, size=False, comment=True, content=False,
                            title=True, ignore_imported_revs=True,
                            ignore_wikibot=False, callback=None):
        """
        Fetch data for all revisions. This could take a long time. You can start
        at a specific revision by modifying the 'start' keyword argument.

        To ignore revisions made by "ImportUser" and "Admin" set
        ignore_imported_revs to True (this is the default). To ignore edits made
        by Wikibot set ignore_wikibot to True (False is the default).

        Modifying the remainder of the keyword arguments will return less/more
        data.
        """
        # first we need to get the latest revision id
        change = self.send_request('api.php', req_params={
                'list': 'recentchanges',
                'action': 'query',
                'format': 'json',
                'rcprop': 'ids',
                'rclimit': 1,
                'rctype': 'edit|new',
        })
        latest_revid = change['query']['recentchanges'][0]['revid']
        # now we loop through all the revisions we want
        rvprop_list = {
                'flags': flags,
                'timestamp': timestamp,
                'user': True,
                'size': size,
                'comment': comment,
                'content': content,
                'ids': True,
        }
        rvprop = '|'.join([key for key in rvprop_list if rvprop_list[key]])
        revs_to_get = range(start, latest_revid)
        all_revs = {}
        if self.api_high_limits:
            limit = 500
        else:
            limit = 50
        for i in xrange(0, len(revs_to_get), limit):
            revid_list = revs_to_get[i:i+limit]
            revid_str = '|'.join([str(rev) for rev in revid_list])
            data = self.send_request('api.php', req_params={
                    'action': 'query',
                    'prop': 'revisions',
                    'rvprop': rvprop,
                    'revids': revid_str,
                    'format': 'json',
            })
            if 'pages' not in data['query'].keys():
                continue
            if 'badrevids' in data['query'].keys():
                [revs_to_get.remove(i['revid']) for i in \
                 data['query']['badrevids'].values()]
            for pageid in data['query']['pages']:
                page = data['query']['pages'][pageid]
                for revision in page['revisions']:
                    if ignore_imported_revs and \
                       revision['user'] in ['ImportUser', 'Admin'] or \
                       ignore_wikibot and revision['user'] == 'Wikibot':
                        revs_to_get.remove(revision['revid'])
                        continue
                    this_rev = {}
                    if flags:
                        this_rev['minor'] = 'minor' in revision.keys()
                    if timestamp:
                        this_rev['time'] = time.strptime(revision['timestamp'],
                                                         MEDIAWIKI_DATEFORMAT)
                    if user:
                        this_rev['user'] = revision['user']
                    if size:
                        this_rev['size'] = revision['size']
                    if comment:
                        if 'comment' in revision.keys():
                            this_rev['comment'] = revision['comment']
                        else:
                            this_rev['comment'] = None
                    if content:
                        this_rev['content'] = revision['content']
                    if title:
                        this_rev['title'] = page['title']
                    all_revs[revision['revid']] = this_rev
            if callback:
                callback(all_revs, revs_to_get)
        return all_revs


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
