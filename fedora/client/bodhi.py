# -*- coding: utf-8 -*-
#
# Copyright 2007-2011  Red Hat, Inc.
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
"""
This module provides a client interface for bodhi.


.. moduleauthor:: Luke Macken <lmacken@redhat.com>
.. moduleauthor:: Toshio Kuratomi <tkuratom@redhat.com>
"""

import logging

from textwrap import wrap
from os.path import join, expanduser, exists

from fedora.client import BaseClient, FedoraClientError
from fedora import b_

__version__ = '0.5.1'
log = logging.getLogger(__name__)


class BodhiClientException(FedoraClientError):
    pass


class BodhiClient(BaseClient):

    def __init__(self, base_url='https://admin.fedoraproject.org/updates/',
                 useragent='Fedora Bodhi Client/%s' % __version__,
                 *args, **kwargs):
        """The BodhiClient constructor.

        :kwarg base_url: Base of every URL used to contact the server.
            Defaults to the Fedora Bodhi instance.
        :kwarg useragent: useragent string to use.  If not given, default to
            "Fedora Boshi Client/VERSION"
        :kwarg username: username for establishing authenticated connections
        :kwarg password: password to use with authenticated connections
        :kwarg session_cookie: *Deprecated*  Use session_id instead.
            User's session_cookie to connect to the server
        :kwarg session_id: user's session_id to connect to the server
        :kwarg cache_session: if set to True, cache the user's session cookie
            on the filesystem between runs.
        :kwarg debug: If True, log debug information
        """
        self.log = log
        super(BodhiClient, self).__init__(base_url, useragent=useragent,
                                          *args, **kwargs)

    def save(self, builds='', type_='', bugs='', notes='', request='testing',
             close_bugs=True, suggest_reboot=False, inheritance=False,
             autokarma=True, stable_karma=3, unstable_karma=-3, edited=''):
        """ Save an update.

        This entails either creating a new update, or editing an existing one.
        To edit an existing update, you must specify the update title in
        the ``edited`` keyword argument.

        :kwarg builds: A list of koji builds for this update.
        :kwarg type\_: The type of this update: ``security``, ``bugfix``,
            ``enhancement``, and ``newpackage``.
        :kwarg bugs: A list of Red Hat Bugzilla ID's associated with this
            update.
        :kwarg notes: Details as to why this update exists.
        :kwarg request: Request for this update to change state, either to
            ``testing``, ``stable``, ``unpush``, ``obsolete`` or None.
        :kwarg close_bugs: Close bugs when update is stable
        :kwarg suggest_reboot: Suggest that the user reboot after update.
        :kwarg inheritance: Follow koji build inheritance, which may result in
            this update being pushed out to additional releases.
        :kwarg autokarma: Allow bodhi to automatically change the state of this
            update based on the ``karma`` from user feedback.  It will
            push your update to ``stable`` once it reaches the ``stable_karma``
            and unpush your update when reaching ``unstable_karma``.
        :kwarg stable_karma: The upper threshold for marking an update as
            ``stable``.
        :kwarg unstable_karma: The lower threshold for unpushing an update.
        :kwarg edited: The update title of the existing update that we are
            editing.

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
              request=None, mine=None, package=None, username=None, limit=10):
        """ Query bodhi for a list of updates.

        :kwarg release: The release that you wish to query updates for.
        :kwarg status: The update status (``pending``, ``testing``, ``stable``,
            ``obsolete``)
        :kwarg type_: The type of this update: ``security``, ``bugfix``,
            ``enhancement``, and ``newpackage``.
        :kwarg bugs: A list of Red Hat Bugzilla ID's
        :kwarg request: An update request to query for
            ``testing``, ``stable``, ``unpush``, ``obsolete`` or None.
        :kwarg mine: If True, only query the users updates.  Default: False.
        :kwarg package: A package name or a name-version-release.
        :kwarg limit: The maximum number of updates to display.  Default: 10.
        """
        params = {
                'tg_paginate_limit': limit,
                'username': username,
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

        :arg update: The title of the update
        :arg request: The request (``testing``, ``stable``, ``obsolete``)

        """
        return self.send_request('request', auth=True, req_params={
                'update': update,
                'action': request,
                })

    def comment(self, update, comment, karma=0, email=None):
        """ Add a comment to an update.

        :arg update: The title of the update comment on.
        :arg comment: The text of the comment.
        :kwarg karma: The karma of this comment (-1, 0, 1)
        :kwarg email: Whether or not to trigger email notifications

        """
        params = {
            'karma': karma,
            'title': update,
            'text': comment,
        }
        if email is not None:
            params['email'] = email
        return self.send_request('comment', auth=True, req_params=params)

    def delete(self, update):
        """ Delete an update.

        :arg update: The title of the update to delete

        """
        return self.send_request('delete', auth=True,
                                 req_params={'update': update})

    def candidates(self):
        """ Get a list list of update candidates.

        This method is a generator that returns a list of koji builds that
        could potentially be pushed as updates.
        """
        if not self.username:
            raise BodhiClientException(b_('You must specify a username'))
        data = self.send_request('candidate_tags')
        koji = self.get_koji_session(login=False)
        for tag in data['tags']:
            for build in koji.listTagged(tag, latest=True):
                if build['owner_name'] == self.username:
                    yield build

    def testable(self):
        """ Get a list of installed testing updates.

        This method is a generate that yields packages that you currently
        have installed that you have yet to test and provide feedback for.

        """
        from yum import YumBase
        yum = YumBase()
        yum.doConfigSetup(init_plugins=False)
        fedora = file('/etc/fedora-release').readlines()[0].split()[2]
        tag = 'dist-f%s-updates-testing' % fedora
        builds = self.get_koji_session(login=False).listTagged(tag, latest=True)
        for build in builds:
            pkgs = yum.rpmdb.searchNevra(name=build['name'],
                                         ver=build['version'],
                                         rel=build['release'],
                                         epoch=None,
                                         arch=None)
            if len(pkgs):
                update_list = self.query(package=[build['nvr']])['updates']
                for update in update_list:
                    yield update

    def latest_builds(self, package):
        """ Get a list of the latest builds for this package.

        :arg package: package name to find builds for.
        :returns: a dictionary of the release dist tag to the latest build.

        .. versionadded:: 0.3.2
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

        :arg updates: A list of update titles to ``push``.

        """
        return self.send_request('admin/mash', auth=True,
                                 req_params={'updates': updates})

    def parse_file(self, input_file):
        """ Parse an update template file.

        :arg input_file: The filename of the update template.

        Returns an array of dictionaries of parsed update values which
        can be directly passed to the ``save`` method.

        """
        from iniparse.compat import ConfigParser
        self.log.info(b_('Reading from %s ') % input_file)
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
            template_file = open(input_file)
            config.readfp(template_file)
            template_file.close()
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

        :arg update: An update dictionary, acquired by the ``list`` method.
        :kwarg minimal: Return a minimal one-line representation of the update.

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

    def get_koji_session(self, login=True):
        """ Return an authenticated koji session """
        import koji
        from iniparse.compat import ConfigParser
        config = ConfigParser()
        if exists(join(expanduser('~'), '.koji', 'config')):
            config.readfp(open(join(expanduser('~'), '.koji', 'config')))
        else:
            config.readfp(open('/etc/koji.conf'))
        cert = expanduser(config.get('koji', 'cert'))
        ca = expanduser(config.get('koji', 'ca'))
        serverca = expanduser(config.get('koji', 'serverca'))
        session = koji.ClientSession(config.get('koji', 'server'))
        if login:
            session.ssl_login(cert=cert, ca=ca, serverca=serverca)
        return session

    koji_session = property(fget=get_koji_session)

    def get_releases(self):
        """ Return a list of bodhi releases.

        This method returns a dictionary in the following format::

            {"releases": [
                {"dist_tag": "dist-f12", "id_prefix": "FEDORA",
                 "locked": false, "name": "F12", "long_name": "Fedora 12"}]}
        """
        return self.send_request('releases')

