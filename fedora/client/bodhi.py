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
# Copyright 2007  Red Hat, Inc
# Authors: Luke Macken <lmacken@redhat.com>

"""
This module provides a client interface for bodhi.
"""

import koji
import logging

from yum import YumBase
from textwrap import wrap
from os.path import join, expanduser, exists
from iniparse.compat import ConfigParser

from fedora.client import BaseClient, FedoraClientError

__version__ = '0.5.0'
log = logging.getLogger(__name__)


class BodhiClientException(FedoraClientError):
    pass


class BodhiClient(BaseClient):

    def __init__(self, base_url='https://admin.fedoraproject.org/bodhi/',
                 useragent='Fedora Bodhi Client/%s' % __version__,
                 *args, **kwargs):
        """ The BodhiClient constructor.

        Arguments:
        :base_url: Base of every URL used to contact the server.  Defaults to
            the Fedora Bodhi instance.
        :useragent: useragent string to use.  If not given, default to
            "Fedora BaseClient/VERSION"
        :username: username for establishing authenticated connections
        :password: password to use with authenticated connections
        :session_cookie: *Deprecated*  Use session_id instead.
			User's session_cookie to connect to the server
        :session_id: user's session_id to connect to the server
        :cache_session: if set to True, cache the user's session cookie on the
            filesystem between runs.
        :debug: If True, log debug information

        """
        super(BodhiClient, self).__init__(base_url, useragent=useragent,
                                          *args, **kwargs)

    def save(self, builds='', type_='', bugs='', notes='', request='testing',
             close_bugs=True, suggest_reboot=False, inheritance=False,
             autokarma=True, stable_karma=3, unstable_karma=-3, edited=''):
        """ Save an update.

        This entails either creating a new update, or editing an existing one.
        To edit an existing update, you must specify the update title in
        the ``edited`` keyword argument.

        Arguments:
        :builds: A list of koji builds for this update.
        :type_: The type of this update: ``security``, ``bugfix``,
            ``enhancement``, and ``newpackage``.
        :bugs: A list of Red Hat Bugzilla ID's associated with this update.
        :notes: Details as to why this update exists.
        :request: Request for this update to change state, either to
            ``testing``, ``stable``, ``unpush``, ``obsolete`` or None.
        :close_bugs: Close bugs when update is stable
        :suggest_reboot: Suggest that the user reboot after update.
        :inheritance: Follow koji build inheritance, which may result in this
            update being pushed out to additional releases.
        :autokarma: Allow bodhi to automatically change the state of this
            update based on the ``karma`` from user feedback.  It will
            push your update to ``stable`` once it reaches the ``stable_karma``
            and unpush your update when reaching ``unstable_karma``.
        :stable_karma: The upper threshold for marking an update as ``stable``.
        :unstable_karma: The lower threshold for unpushing an update.
        :edited: The update title of the existing update that we are editing.

        """
        return self.send_request('save', auth=True, req_params={
                'suggest_reboot': suggest_reboot,
                'close_bugs': close_bugs,
                'unstable_karma': unstable_karma,
                'stable_karma': stable_karma,
                'inheritance': inheritance,
                'autokarma': autokarma,
                'request': request,
                'builds': builds,
                'edited': edited,
                'notes': notes,
                'type_': type_,
                'bugs': bugs,
                })

    def query(self, release=None, status=None, type_=None, bugs=None,
              request=None, mine=None, package=None, limit=10):
        """ Query bodhi for a list of updates.

        Arguments:
        :builds: A list of koji builds for this update.  Any new builds will
            be created, and any removed builds will be removed from the update
            specified by ``edited``.
        :release: The release that this update is for.
        :type_: The type of this update: ``security``, ``bugfix``,
            ``enhancement``, and ``newpackage``.
        :bugs: A list of Red Hat Bugzilla ID's associated with this update.
        :notes: Details as to why this update exists.
        :request: Request for this update to change state, either to
            ``testing``, ``stable``, ``unpush``, ``obsolete`` or None.
        :mine: If True, only query the users updates.
        :package: A package name or a name-version-release.
        :limit: The maximum number of updates to display.

        """
        params = {
                'tg_paginate_limit': limit,
                'release': release,
                'package': package,
                'request': request,
                'status': status,
                'type_': type_,
                'bugs': bugs,
                'mine': mine,
                }
        auth = False
        if params['mine']:
            auth = True
        for key, value in params.items():
            if not value:
                del params[key]
        return self.send_request('list', req_params=params, auth=auth)

    def request(self, update, request):
        """ Request an update state change.

        Arguments:
        :update: The title of the update
        :request: The request (``testing``, ``stable``, ``obsolete``)

        """
        return self.send_request('request', auth=True, req_params={
                'update': update,
                'action': request,
                })

    def comment(self, update, comment, karma=0):
        """ Add a comment to an update.

        Arguments:
        :update: The title of the update comment on.
        :comment: The text of the comment.
        :karma: The karma of this comment (-1, 0, 1)

        """
        return self.send_request('comment', auth=True, req_params={
                'karma': karma,
                'title': update,
                'text': comment,
                })

    def delete(self, update):
        """ Delete an update.

        Arguments
        :update: The title of the update to delete

        """
        return self.send_request('delete', auth=True,
                                 req_params={'update': update})

    def candidates(self):
        """ Get a list list of update candidates.

        This method is a generator that returns a list of koji builds that
        could potentially be pushed as updates.
        """
        if not self.username:
            raise BodhiClientException, 'You must specify a username'
        data = self.send_request('dist_tags')
        for tag in [tag + '-updates-candidate' for tag in data['tags']]:
            for build in self.koji_session.listTagged(tag, latest=True):
                if build['owner_name'] == self.username:
                    yield build

    def testable(self):
        """ Get a list of installed testing updates.

        This method is a generate that yields packages that you currently
        have installed that you have yet to test and provide feedback for.

        """
        yum = YumBase()
        yum.doConfigSetup(init_plugins=False)
        fedora = file('/etc/fedora-release').readlines()[0].split()[2]
        tag = 'dist-f%s-updates-testing' % fedora
        builds = self.koji_session.listTagged(tag, latest=True)
        for build in builds:
            pkgs = yum.rpmdb.searchNevra(name=build['name'],
                                         ver=build['version'],
                                         rel=build['release'],
                                         epoch=None,
                                         arch=None)
            if len(pkgs):
                yield self.query(package=[build['nvr']])

    def latest_builds(self, package):
        """ Get a list of the latest builds for this package.

        Returns a dictionary of the release dist tag to the latest build.
        """
        return self.send_request('latest_builds',
                                 req_params={'package': package})

    def masher(self):
        """ Return the status of bodhi's masher """
        return self.send_request('admin/masher', auth=True)

    def push(self):
        """ Return a list of requests """
        return self.send_request('admin/push', auth=True)

    def push_updates(self, updates):
        """ Push a list of updates.

        Arguments
        :updates: A list of update titles to ``push``.

        """
        return self.send_request('admin/mash', auth=True,
                                 req_params={'updates': updates})

    def parse_file(self, input_file):
        """ Parse an update template file.

        Arguments
        :input_file: The filename of the update template.

        Returns an array of dictionaries of parsed update values which
        can be directly passed to the ``save`` method.

        """
        log.info("Reading from %s " % input_file)
        input_file = expanduser(input_file)
        if exists(input_file):
            defaults = {
                'type': 'bugfix',
                'request': 'testing',
                'notes': '',
                'bugs': '',
                'close_bugs': 'True',
                'autokarma': 'True',
                'stable_karma': 3,
                'unstable_karma': -3,
                'suggest_reboot': 'False',
                }
            config = ConfigParser(defaults)
            f = open(input_file)
            config.readfp(f)
            f.close()
            updates = []
            for section in config.sections():
                update = {}
                update['builds'] = section
                update['type_'] = config.get(section, 'type')
                update['request'] = config.get(section, 'request')
                update['bugs'] = config.get(section, 'bugs')
                update['close_bugs'] = config.getboolean(section, 'close_bugs')
                update['notes'] = config.get(section, 'notes')
                update['autokarma'] = config.getboolean(section, 'autokarma')
                update['stable_karma'] = config.getint(section, 'stable_karma')
                update['unstable_karma'] = config.getint(section,
                                                         'unstable_karma')
                update['suggest_reboot'] = config.getboolean(section,
                                                             'suggest_reboot')
                updates.append(update)
        return updates

    def update_str(self, update, minimal=False):
        """ Return a string representation of a given update dictionary.

        Arguments
        :update: An update dictionary, acquired by the ``list`` method.
        :minimal: Return a minimal one-line representation of the update.

        """
        if isinstance(update, basestring):
            return update
        if minimal:
            val = ""
            date = update['date_pushed'] and update['date_pushed'].split()[0] \
                                          or update['date_submitted'].split()[0]
            val += ' %-43s  %-11s  %-8s  %10s ' % (update['builds'][0]['nvr'],
                                                   update['type'],
                                                   update['status'], date)
            for build in update['builds'][1:]:
                val += '\n %s' % build['nvr']
            return val
        val = "%s\n%s\n%s\n" % ('=' * 80, '\n'.join(
            wrap(update['title'].replace(',', ', '), width=80,
                 initial_indent=' '*5, subsequent_indent=' '*5)), '=' * 80)
        if update['updateid']:
            val += "  Update ID: %s\n" % update['updateid']
        val += """    Release: %s
     Status: %s
       Type: %s
      Karma: %d""" % (update['release']['long_name'], update['status'],
                      update['type'], update['karma'])
        if update['request'] != None:
            val += "\n    Request: %s" % update['request']
        if len(update['bugs']):
            bugs = ''
            i = 0
            for bug in update['bugs']:
                bugstr = '%s%s - %s\n' % (i and ' ' * 11 + ': ' or '',
                                          bug['bz_id'], bug['title'])
                bugs += '\n'.join(wrap(bugstr, width=67,
                                       subsequent_indent=' '*11+': ')) + '\n'
                i += 1
            bugs = bugs[:-1]
            val += "\n       Bugs: %s" % bugs
        if update['notes']:
            notes = wrap(update['notes'], width=67,
                         subsequent_indent=' ' * 11 + ': ')
            val += "\n      Notes: %s" % '\n'.join(notes)
        val += """
  Submitter: %s
  Submitted: %s\n""" % (update['submitter'], update['date_submitted'])
        if len(update['comments']):
            val += "   Comments: "
            comments = []
            for comment in update['comments']:
                if comment['anonymous']:
                    anonymous = " (unauthenticated)"
                else:
                    anonymous = ""
                comments.append("%s%s%s - %s (karma %s)" % (' ' * 13,
                                comment['author'], anonymous,
                                comment['timestamp'], comment['karma']))
                if comment['text']:
                    text = wrap(comment['text'], initial_indent=' ' * 13,
                                subsequent_indent=' ' * 13, width=67)
                    comments.append('\n'.join(text))
            val += '\n'.join(comments).lstrip() + '\n'
        if update['updateid']:
            val += "\n  %s\n" % ('%s%s/%s' % (self.base_url,
                                              update['release']['name'],
                                              update['updateid']))
        else:
            val += "\n  %s\n" % ('%s%s' % (self.base_url, update['title']))
        return val

    def __koji_session(self):
        """ Return an authenticated koji session """
        config = ConfigParser()
        if exists(join(expanduser('~'), '.koji', 'config')):
            config.readfp(open(join(expanduser('~'), '.koji', 'config')))
        else:
            config.readfp(open('/etc/koji.conf'))
        cert = expanduser(config.get('koji', 'cert'))
        ca = expanduser(config.get('koji', 'ca'))
        serverca = expanduser(config.get('koji', 'serverca'))
        session = koji.ClientSession(config.get('koji', 'server'))
        session.ssl_login(cert=cert, ca=ca, serverca=serverca)
        return session

    koji_session = property(fget=__koji_session)
