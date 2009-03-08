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
# Copyright 2009  Red Hat, Inc

"""
:mod:`fedora.client.hosted` - Fedora Hosted Module
==================================================

This module provides a class for getting information
about fedorahosted.org projects.

.. moduleauthor:: Luke Macken <lmacken@redhat.com>
"""

import urllib

from BeautifulSoup import BeautifulSoup

class FedoraHosted(object):

    def __init__(self):
        html = urllib.urlopen('http://fedorahosted.org/web').read()
        self.soup = BeautifulSoup(html)

        self.projects = {}
        self._parse_projects()

    def _parse_projects(self):
        for project in self.soup.findAll('tr', **{'class': 'rowsub'}):
            desccol = project.findChild('td', **{'class': 'desccol'}).contents[0]
            try:
                name = desccol.contents[0]
            except:
                print desccol
            self.projects[name] = {
                    'trac': desccol['href'],
                    'vcs': project.findChild('img', **{'class': 'vcsimg'})['title'],
                    'browse': project.findChild('img', alt='browse').previous['href'],
                    'anon': project.findChild('img', alt='anon').previous['href'],
                    'auth': project.findChild('img', alt='auth').previous['href'],
                    }
            self.projects[name]['feed'] = \
                    self.projects[name]['trac'] + \
                    '/timeline?changeset=on&ticket=on&milestone=on&wiki=on&max=50&daysback=90&format=rss'

    def get_project(self, project):
        return self.projects.get(project)


if __name__ == '__main__':
    from pprint import pprint
    pprint(FedoraHosted().projects)
