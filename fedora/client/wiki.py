#!/usr/bin/python -tt
# coding: utf-8
#
# Copyright (C) 2008 Red Hat Inc.
# Authors: Luke Macken <lmacken@redhat.com>
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version.  See http://www.gnu.org/copyleft/gpl.html for
# the full text of the license.

"""
Fedora Wiki Client
"""

from datetime import datetime, timedelta
from collections import defaultdict

from fedora.client import BaseClient

class FedoraWiki(BaseClient):

    def __init__(self, *args, **kw):
        super(FedoraWiki, self).__init__('http://fedoraproject.org/w/',
                                         *args, **kw)

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
        return data

    def print_recent_changes(self, days=7, show=10):
        now = datetime.utcnow()
        then = now - timedelta(days=days)
        print "From %s to %s" % (then, now)
        data = self.get_recent_changes(now=now, then=then)
        num_changes = len(data['query']['recentchanges'])
        print "%d wiki changes in the past week" % num_changes
        if num_changes == 500:
            print "Warning: Number of changes reaches the API return limit."
            print "You will not get the complete list of changes unless "
            print "you run this script using a 'bot' account."

        users = defaultdict(list) # {username: [change,]}
        pages = defaultdict(int)  # {pagename: # of edits}

        for change in data['query']['recentchanges']:
            users[change['user']].append(change['title'])
            pages[change['title']] += 1

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
    wiki = FedoraWiki()
    wiki.print_recent_changes()
