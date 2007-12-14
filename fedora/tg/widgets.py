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
# Red Hat Author(s): Luke Macken <lmacken@redhat.com>
'''
Proof-of-concept Fedora TurboGears widgets
'''

import re
import urllib2
import feedparser
import simplejson

from bugzilla import Bugzilla
from turbogears.widgets import Widget

class FedoraPeopleWidget(Widget):
    template = """
       <table xmlns:py="http://purl.org/kid/ns#"
         class="widget FedoraPeopleWidget" py:attrs="{'id': widgetId}">
          <tr py:for="entry in entries[:5]">
            <td><img src="${entry['image']}" height="32" width="32"/></td>
            <td><a href="${entry['link']}">${entry['title']}</a></td>
          </tr>
        </table>
    """
    params = ["widgetId", "entries"]

    def __init__(self, widgetId=None):
        self.widgetId = widgetId
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
        return {'id': self.widgetId, 'entries': self.entries}

class FedoraMaintainerWidget(Widget):
    template = """
       <table xmlns:py="http://purl.org/kid/ns#"
         class="widget FedoraMaintainerWidget" py:attrs="{'id': widgetId}">
          <tr py:for="pkg in packages[:5]">
            <td><a href="https://admin.fedoraproject.org/pkgdb/packages/name/${pkg['name']}">${pkg['name']}</a></td>
          </tr>
       </table>
    """
    params = ["widgetId", "packages"]

    def __init__(self, username, widgetId=None):
        self.widgetId = widgetId
        page = urllib2.urlopen('https://admin.fedoraproject.org/pkgdb/users/packages/%s/?tg_format=json' % username)
        self.packages = simplejson.load(page)['pkgs']

    def __json__(self):
        return {'id': self.widgetId, 'packages': self.packages}

class BugzillaWidget(Widget):
    template = """
       <table xmlns:py="http://purl.org/kid/ns#" class="widget BugzillaWidget"
          py:attrs="{'id': widgetId}">
          <tr py:for="bug in bugs">
            <td>
              <a href="${bug.url}">${bug.bug_id}</a> ${bug.short_short_desc}
            </td>
          </tr>
       </table>
    """
    params = ["widgetId", "bugs"]

    def __init__(self, email, widgetId=None):
        self.widgetId = widgetId
        bz = Bugzilla(url='https://bugzilla.redhat.com/xmlrpc.cgi')
        self.bugs = bz.query({
            'product'           : 'Fedora',
            'email1'            : email,
            'emailassigned_to1' : True
        })[:5]

    def __json__(self):
        return {'id': self.widgetId, 'bugs': self.bugs}
