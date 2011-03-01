# -*- coding: utf-8 -*-
#
# Copyright (C) 2007  Red Hat, Inc.
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
Proof-of-concept Fedora TurboGears widgets

.. moduleauthor:: Luke Macken <lmacken@redhat.com>
'''

import re
import urllib2
import feedparser
try:
    import simplejson as json
except ImportError:
    import json as json

from bugzilla import Bugzilla
from turbogears.widgets import Widget

class FedoraPeopleWidget(Widget):
    '''Widget to display the Fedora People RSS Feed.
    '''
    template = """
       <table xmlns:py="http://purl.org/kid/ns#"
         class="widget FedoraPeopleWidget" py:attrs="{'id': widget_id}">
          <tr py:for="entry in entries[:5]">
            <td><img src="${entry['image']}" height="32" width="32"/></td>
            <td><a href="${entry['link']}">${entry['title']}</a></td>
          </tr>
        </table>
    """
    params = ["widget_id", "entries"]

    def __init__(self, widget_id=None):
        self.widget_id = widget_id
        self.entries = []
        regex = re.compile('<img src="(.*)" alt="" />')
        feed = feedparser.parse('http://planet.fedoraproject.org/rss20.xml')
        for entry in feed['entries']:
            self.entries.append({
                'link'  : entry['link'],
                'title' : entry['title'],
                'image' : regex.match(entry['summary']).group(1)
            })

    def __json__(self):
        return {'id': self.widget_id, 'entries': self.entries}

class FedoraMaintainerWidget(Widget):
    '''Widget to show the packages a maintainer owns.
    '''
    template = """
       <table xmlns:py="http://purl.org/kid/ns#"
         class="widget FedoraMaintainerWidget" py:attrs="{'id': widget_id}">
          <tr py:for="pkg in packages[:5]">
            <td><a href="https://admin.fedoraproject.org/pkgdb/packages/name/${pkg['name']}">${pkg['name']}</a></td>
          </tr>
       </table>
    """
    params = ["widget_id", "packages"]

    def __init__(self, username, widget_id=None):
        self.widget_id = widget_id
        page = urllib2.urlopen('https://admin.fedoraproject.org/pkgdb/' \
                'users/packages/%s/?tg_format=json' % username)
        self.packages = json.load(page)['pkgs']

    def __json__(self):
        return {'id': self.widget_id, 'packages': self.packages}

class BugzillaWidget(Widget):
    '''Widget to show the stream of bugs submitted against a package.'''
    template = """
       <table xmlns:py="http://purl.org/kid/ns#" class="widget BugzillaWidget"
          py:attrs="{'id': widget_id}">
          <tr py:for="bug in bugs">
            <td>
              <a href="${bug.url}">${bug.bug_id}</a> ${bug.short_short_desc}
            </td>
          </tr>
       </table>
    """
    params = ["widget_id", "bugs"]

    def __init__(self, email, widget_id=None):
        self.widget_id = widget_id
        bugzilla = Bugzilla(url='https://bugzilla.redhat.com/xmlrpc.cgi')
        # pylint: disable-msg=E1101
        # :E1101: Bugzilla class monkey patches itself with methods like
        # query.
        self.bugs = bugzilla.query({
            'product'           : 'Fedora',
            'email1'            : email,
            'emailassigned_to1' : True
        })[:5]
        # pylint: enable-msg=E1101

    def __json__(self):
        return {'id': self.widget_id, 'bugs': self.bugs}
