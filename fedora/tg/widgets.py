# Proof-of-concept Fedora TurboGears widgets
# Authors: Luke Macken <lmacken@redhat.com>

import re
import urllib2
import feedparser
import simplejson

from bugzilla import Bugzilla
from turbogears.widgets import Widget

class FedoraPeopleWidget(Widget):
    template = """
       <table xmlns:py="http://purl.org/kid/ns#" border="0">
          <tr py:for="entry in entries">
            <td><img src="${entry['image']}" height="32" width="32"/></td>
            <td><a href="${entry['link']}">${entry['title']}</a></td>
          </tr>
        </table>
    """
    params = ["entries"]

    def __init__(self):
        self.entries = []
        regex = re.compile('<img src="(.*)" alt="" />')
        feed = feedparser.parse('http://planet.fedoraproject.org/rss20.xml')
        for entry in feed['entries'][:5]:
            self.entries.append({
                'link'  : entry['link'],
                'title' : entry['title'],
                'image' : regex.match(entry['summary']).group(1)
            })


class FedoraMaintainerWidget(Widget):
    template = """
       <table xmlns:py="http://purl.org/kid/ns#" border="0">
          <tr py:for="pkg in packages">
            <td><a href="https://admin.fedoraproject.org/pkgdb/packages/name/${pkg['name']}">${pkg['name']}</a></td>
          </tr>
       </table>
    """
    params = ["packages"]

    def __init__(self, username):
        page = urllib2.urlopen('https://admin.fedoraproject.org/pkgdb/users/packages/%s/?tg_format=json' % username)
        self.packages = simplejson.load(page)['pkgs'][:5]


class BugzillaWidget(Widget):
    template = """
       <table xmlns:py="http://purl.org/kid/ns#" border="0">
          <tr py:for="bug in bugs">
            <td>
              <a href="${bug.url}">${bug.bug_id}</a> ${bug.short_short_desc}
            </td>
          </tr>
       </table>
    """
    params = ["bugs"]

    def __init__(self, email):
        bz = Bugzilla(url='https://bugzilla.redhat.com/xmlrpc.cgi')
        self.bugs = bz.query({
            'product'           : 'Fedora',
            'email1'            : email,
            'emailassigned_to1' : True
        })[:5]
