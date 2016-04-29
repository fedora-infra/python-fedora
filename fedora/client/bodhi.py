# -*- coding: utf-8 -*-
#
# Copyright 2007-2015  Red Hat, Inc.
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
.. moduleauthor:: Ralph Bean <rbean@redhat.com>
"""

import os
import datetime
import functools
import getpass
import logging
import textwrap
import warnings
import re

import six

from fedora.client import OpenIdBaseClient, FedoraClientError, BaseClient
import fedora.client.openidproxyclient

__version__ = '2.0.0'
log = logging.getLogger(__name__)

BODHI1_BASE_URL = 'https://admin.fedoraproject.org/updates/'
BODHI2_BASE_URL = 'https://bodhi.fedoraproject.org/'
BODHI1_STG_BASE_URL = 'https://admin.stg.fedoraproject.org/updates/'
BODHI2_STG_BASE_URL = 'https://bodhi.stg.fedoraproject.org/'
STG_OPENID_API = 'https://id.stg.fedoraproject.org/api/v1/'

# We default to Bodhi2 now
BASE_URL = BODHI2_BASE_URL
STG_BASE_URL = BODHI2_STG_BASE_URL


class BodhiClientException(FedoraClientError):
    pass


def BodhiClient(base_url=BASE_URL, staging=False, **kwargs):
    # XXX - This is a temporary compat shim to get the bodhi1 /usr/bin/bodhi
    # tool to play nicely with us.  It still hands us the base_url for Bodhi1,
    # which breaks us.
    if base_url == BODHI1_BASE_URL:
        log.warn('Overriding %r with bodhi2, %r.  If you want to use Bodhi1, '
                 'use fedora.client.bodhi:Bodhi1Client explicitly.' % (
                     base_url, BODHI2_BASE_URL))
        base_url = BODHI2_BASE_URL

    if staging:
        log.info('Using bodhi2 STAGING environment')
        base_url = STG_BASE_URL

    log.debug('Using Bodhi2Client.')
    return Bodhi2Client(base_url=base_url, staging=staging, **kwargs)


def errorhandled(method):
    """ A decorator for Bodhi2Client that raises exceptions on failure. """
    @functools.wraps(method)
    def wrapper(*args, **kwargs):
        result = method(*args, **kwargs)

        if 'errors' not in result:
            return result

        # Otherwise, there was a problem...
        problems = 'An unhandled error occurred in the BodhiClient'
        try:
            problems = "\n".join([e['description'] for e in result['errors']])
        except Exception:
            pass
        raise BodhiClientException(problems)
    return wrapper


class Bodhi2Client(OpenIdBaseClient):

    def __init__(self, base_url=BODHI2_BASE_URL, username=None, password=None, staging=False, **kwargs):
        if staging:
            fedora.client.openidproxyclient.FEDORA_OPENID_API = STG_OPENID_API
            base_url = BODHI2_STG_BASE_URL

        super(Bodhi2Client, self).__init__(base_url, login_url=base_url +
                'login', username=username, **kwargs)

        self._password = password
        self.csrf_token = None

    @property
    def password(self):
        if not self._password:
            self._password = getpass.getpass()
        return self._password

    @property.setter
    def password(self, value):
        self._password = value

    @errorhandled
    def save(self, **kwargs):
        """ Save an update.

        This entails either creating a new update, or editing an existing one.
        To edit an existing update, you must specify the update title in
        the ``edited`` keyword argument.

        :kwarg builds: A list of koji builds for this update.
        :kwarg type: The type of this update: ``security``, ``bugfix``,
            ``enhancement``, and ``newpackage``.
        :kwarg bugs: A list of Red Hat Bugzilla ID's associated with this
            update.
        :kwarg notes: Details as to why this update exists.
        :kwarg request: Request for this update to change state, either to
            ``testing``, ``stable``, ``unpush``, ``obsolete`` or None.
        :kwarg close_bugs: Close bugs when update is stable
        :kwarg suggest: Suggest that the user reboot or logout after update.
            (``reboot``, ``logout``)
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
        :kwarg severity: The severity of this update (``urgent``, ``high``,
            ``medium``, ``low``)
        :kwarg requirements: A list of required Taskotron tests that must pass
            for this update to reach stable. (``depcheck``, ``upgradepath``,
            ``rpmlint``)
        :kwarg require_bugs: A boolean to require that all of the bugs in your
            update have been confirmed by testers.
        :kwarg require_testcases: A boolean to require that this update passes
            all test cases before reaching stable.

        """
        kwargs['csrf_token'] = self.csrf()
        if 'type_' in kwargs:
            # backwards compat
            kwargs['type'] = kwargs['type_']
        return self.send_request('updates/', verb='POST', auth=True,
                                 data=kwargs)

    @errorhandled
    def request(self, update, request):
        """ Request an update state change.

        :arg update: The title of the update
        :arg request: The request (``testing``, ``stable``, ``obsolete``,
                                   ``unpush``, ``revoke``)
        """
        return self.send_request('updates/{0}/request'.format(update),
                                 verb='POST', auth=True,
                                 data={'update': update, 'request': request,
                                       'csrf_token': self.csrf()})

    @errorhandled
    def delete(self, update):
        warnings.warn('Deleting updates has been disabled in Bodhi2. '
                      'This API call will unpush the update instead. '
                      'Please use `set_request(update, "unpush")` instead')
        self.request(update, 'unpush')

    @errorhandled
    def query(self, **kwargs):
        """ Query bodhi for a list of updates.

        :kwarg releases: A list of releases that you wish to query updates for.
        :kwarg status: The update status (``pending``, ``testing``, ``stable``,
            ``obsolete``, ``unpushed``, ``processing``)
        :kwarg type: The type of this update: ``security``, ``bugfix``,
            ``enhancement``, and ``newpackage``.
        :kwarg bugs: A list of Red Hat Bugzilla ID's
        :kwarg request: An update request to query for
            ``testing``, ``stable``, ``unpush``, ``obsolete`` or None.
        :kwarg mine: If True, only query the users updates.  Default: False.
        :kwarg packages: A space or comma delimited list of package names
        :kwarg limit: A deprecated argument, sets ``rows_per_page``. See its docstring for more info.
        :kwarg approved_before: A datetime string
        :kwarg approved_since: A datetime string
        :kwarg builds: A space or comma delimited string of build nvrs
        :kwarg critpath: A boolean to query only critical path updates
        :kwarg cves: Filter by CVE IDs
        :kwarg locked: A boolean to filter only locked updates
        :kwarg modified_before: A datetime string to query updates that have
            been modified before a certain time.
        :kwarg modified_since: A datetime string to query updates that have
            been modified since a certain time.
        :kwarg pushed: A boolean to filter only pushed updates
        :kwarg pushed_before: A datetime string to filter updates pushed before a
            certain time.
        :kwarg pushed_since: A datetime string to filter updates pushed since a
            certain time.
        :kwarg severity: A severity type to filter by (``unspecified``,
            ``urgent``, ``high``, ``medium``, ``low``)
        :kwarg submitted_before: A datetime string to filter updates submitted
            before a certain time.
        :kwarg submitted_since: A datetime string to filter updates submitted
            after a certain time.
        :kwarg suggest: Query for updates that suggest a user restart
            (``logout``, ``reboot``)
        :kwarg user: Query for updates submitted by a specific user.
        :kwarg rows_per_page: Limit the results to a certain number of rows per
                    page (min:1 max: 100 default: 20)
        :kwarg page: Return a specific page of results

        """
        # bodhi1 compat
        if 'limit' in kwargs:
            kwargs['rows_per_page'] = kwargs['limit']
            del(kwargs['limit'])
        # 'mine' may be in kwargs, but set False
        if kwargs.get('mine'):
            kwargs['user'] = self.username
        if 'package' in kwargs:
            # for Bodhi 1, 'package' could be a package name, build, or
            # update ID, so try and figure it out
            if re.search(r'(\.el|\.fc)\d\d?', kwargs['package']):
                kwargs['builds'] = kwargs['package']
            elif re.search(r'FEDORA-(EPEL)?-\d{4,4}', kwargs['package']):
                kwargs['updateid'] = kwargs['package']
            else:
                kwargs['packages'] = kwargs['package']
            del(kwargs['package'])
        if 'release' in kwargs:
            kwargs['releases'] = kwargs['release']
            del(kwargs['release'])
        if 'type_' in kwargs:
            kwargs['type'] = kwargs['type_']
            del(kwargs['type_'])
        # Old Bodhi CLI set bugs default to "", but new Bodhi API
        # checks for 'if bugs is not None', not 'if not bugs'
        if 'bugs' in kwargs and kwargs['bugs'] == '':
            kwargs['bugs'] = None
        return self.send_request('updates/', verb='GET', params=kwargs)

    @errorhandled
    def comment(self, update, comment, karma=0, email=None):
        """ Add a comment to an update.

        :arg update: The title of the update comment on.
        :arg comment: The text of the comment.
        :kwarg karma: The karma of this comment (-1, 0, 1)
        :kwarg email: Whether or not to trigger email notifications

        """
        return self.send_request('comments/', verb='POST', auth=True,
                data={'update': update, 'text': comment,
                      'karma': karma, 'email': email,
                      'csrf_token': self.csrf()})

    @errorhandled
    def save_override(self, nvr, duration, notes):
        """ Save a buildroot override.

        This entails either creating a new buildroot override, or editing an
        existing one.

        :kwarg nvr: A nvr of a koji build.
        :kwarg duration: Number of days from now that this override should
            expire.
        :kwarg notes: Notes about why this override is in place.

        """
        expiration_date = datetime.datetime.utcnow() + \
            datetime.timedelta(days=duration)

        return self.send_request(
            'overrides/', verb='POST', auth=True, data={
                'nvr': nvr,
                'expiration_date': expiration_date,
                'notes': notes,
                'csrf_token': self.csrf(),
            })

    @errorhandled
    def list_overrides(self, user=None):
        """ Save a buildroot overrides.

        This entails either creating a new buildroot override, or editing an
        existing one.

        :kwarg user: A username whose buildroot overrides you want returned.

        """
        params = {}
        if user:
            params['user'] = user
        return self.send_request('overrides/', verb='GET', params=params)

    @errorhandled
    def csrf(self):
        if not self.csrf_token:
            if not self.has_cookies():
                self.login(self.username, self.password)
            self.csrf_token = self.send_request(
                'csrf', verb='GET', auth=True)['csrf_token']
        return self.csrf_token

    def parse_file(self, input_file):
        """ Parse an update template file.

        :arg input_file: The filename of the update template.

        Returns an array of dictionaries of parsed update values which
        can be directly passed to the ``save`` method.

        """
        from six.moves import configparser

        if not os.path.exists(input_file):
            raise ValueError("No such file or directory: %s" % input_file)

        defaults = dict(severity='unspecified', suggest='unspecified')
        config = configparser.SafeConfigParser(defaults=defaults)
        read = config.read(input_file)

        if len(read) != 1 or read[0] != input_file:
            raise ValueError("Invalid input file: %s" % input_file)

        updates = []

        for section in config.sections():
            update = {
                'builds': section,
                'bugs': config.get(section, 'bugs', raw=True),
                'close_bugs': config.getboolean(section, 'close_bugs'),
                'type': config.get(section, 'type', raw=True),
                'type_': config.get(section, 'type', raw=True),
                'request': config.get(section, 'request', raw=True),
                'severity': config.get(section, 'severity', raw=True),
                'notes': config.get(section, 'notes', raw=True),
                'autokarma': config.get(section, 'autokarma', raw=True),
                'stable_karma': config.get(section, 'stable_karma', raw=True),
                'unstable_karma': config.get(
                    section, 'unstable_karma', raw=True),
                'suggest': config.get(section, 'suggest', raw=True),
                }

            updates.append(update)

        return updates

    @errorhandled
    def latest_builds(self, package):
        return self.send_request('latest_builds', params={'package': package})

    def testable(self):
        """ Get a list of installed testing updates.

        This method is a generate that yields packages that you currently
        have installed that you have yet to test and provide feedback for.

        Only works on systems with dnf.
        """
        import dnf
        base = dnf.Base()
        sack = base.fill_sack(load_system_repo=True)
        query = sack.query()
        installed = query.installed()
        with open('/etc/fedora-release', 'r') as f:
            fedora = f.readlines()[0].split()[2]
        tag = 'f%s-updates-testing' % fedora
        builds = self.get_koji_session(
            login=False).listTagged(tag, latest=True)
        for build in builds:
            pkgs = installed.filter(name=build['name'], version=build['version'],
                                    release=build['release']).run()
            if len(pkgs):
                update_list = self.query(builds=build['nvr'])['updates']
                for update in update_list:
                    yield update

    def override_str(self, override):
        """ Return a string representation of a given override dictionary.

        :arg override: An override dictionary.

        """
        if isinstance(override, six.string_types):
            return override

        # TODO -- make this fancy.
        return "{submitter}'s {build} override (expires {expiry})".format(
            submitter=override['submitter']['name'],
            build=override['build']['nvr'],
            expiry=override['expiration_date'],
        )

    def update_str(self, update, minimal=False):
        """ Return a string representation of a given update dictionary.

        :arg update: An update dictionary, acquired by the ``list`` method.
        :kwarg minimal: Return a minimal one-line representation of the update.

        """
        if isinstance(update, six.string_types):
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
            textwrap.wrap(update['title'].replace(',', ', '), width=80,
                          initial_indent=' '*5, subsequent_indent=' '*5)), '=' * 80)
        if update['alias']:
            val += "  Update ID: %s\n" % update['alias']
        val += """    Release: %s
     Status: %s
       Type: %s
      Karma: %d""" % (update['release']['long_name'], update['status'],
                      update['type'], update['karma'])
        if update['request'] is not None:
            val += "\n    Request: %s" % update['request']
        if len(update['bugs']):
            bugs = ''
            i = 0
            for bug in update['bugs']:
                bugstr = '%s%s - %s\n' % (i and ' ' * 11 + ': ' or '',
                                          bug['bug_id'], bug['title'])
                bugs += '\n'.join(textwrap.wrap(bugstr, width=67,
                                                subsequent_indent=' '*11+': ')) + '\n'
                i += 1
            bugs = bugs[:-1]
            val += "\n       Bugs: %s" % bugs
        if update['notes']:
            notes = textwrap.wrap(update['notes'], width=67,
                                  subsequent_indent=' ' * 11 + ': ')
            val += "\n      Notes: %s" % '\n'.join(notes)
        val += """
  Submitter: %s
  Submitted: %s\n""" % (update['user']['name'], update['date_submitted'])
        if len(update['comments']):
            val += "   Comments: "
            comments = []
            for comment in update['comments']:
                if comment['anonymous']:
                    anonymous = " (unauthenticated)"
                else:
                    anonymous = ""
                comments.append("%s%s%s - %s (karma %s)" % (' ' * 13,
                                comment['user']['name'], anonymous,
                                comment['timestamp'], comment['karma']))
                if comment['text']:
                    text = textwrap.wrap(comment['text'], initial_indent=' ' * 13,
                                         subsequent_indent=' ' * 13, width=67)
                    comments.append('\n'.join(text))
            val += '\n'.join(comments).lstrip() + '\n'
        if update['alias']:
            val += "\n  %s\n" % ('%supdates/%s' % (self.base_url,
                                                   update['alias']))
        else:
            val += "\n  %s\n" % ('%s%s' % (self.base_url, update['title']))
        return val

    @errorhandled
    def get_releases(self, **kwargs):
        """ Return a list of bodhi releases.

        This method returns a dictionary in the following format::

            {"releases": [
                {"dist_tag": "dist-f12", "id_prefix": "FEDORA",
                 "locked": false, "name": "F12", "long_name": "Fedora 12"}]}
        """
        return self.send_request('releases/', params=kwargs)

    def get_koji_session(self, login=True):
        """ Return an authenticated koji session """
        import koji
        from iniparse.compat import ConfigParser
        config = ConfigParser()
        if os.path.exists(os.path.join(os.path.expanduser('~'), '.koji', 'config')):
            config.readfp(open(os.path.join(os.path.expanduser('~'), '.koji', 'config')))
        else:
            config.readfp(open('/etc/koji.conf'))
        cert = os.path.expanduser(config.get('koji', 'cert'))
        ca = os.path.expanduser(config.get('koji', 'ca'))
        serverca = os.path.expanduser(config.get('koji', 'serverca'))
        session = koji.ClientSession(config.get('koji', 'server'))
        if login:
            session.ssl_login(cert=cert, ca=ca, serverca=serverca)
        return session

    koji_session = property(fget=get_koji_session)

    def candidates(self):
        """ Get a list list of update candidates.

        This method is a generator that returns a list of koji builds that
        could potentially be pushed as updates.
        """
        if not self.username:
            raise BodhiClientException('You must specify a username')
        builds = []
        data = self.get_releases()
        koji = self.get_koji_session(login=False)
        for release in data['releases']:
            try:
                for build in koji.listTagged(release['candidate_tag'], latest=True):
                    if build['owner_name'] == self.username:
                        builds.append(build)
            except:
                log.exception('Unable to query candidate builds for %s' % release)
        return builds


class Bodhi1Client(BaseClient):

    def __init__(self, base_url='https://admin.fedoraproject.org/updates/',
                 useragent='Fedora Bodhi Client/%s' % __version__,
                 *args, **kwargs):
        """The BodhiClient constructor.

        :kwarg base_url: Base of every URL used to contact the server.
            Defaults to the Fedora Bodhi instance.
        :kwarg useragent: useragent string to use.  If not given, default to
            "Fedora Bodhi Client/VERSION"
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
        super(Bodhi1Client, self).__init__(base_url, useragent=useragent,
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
        return self.send_request(
            'save', auth=True, req_params={
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
            'updates_tgp_limit': limit,
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
        for key, value in list(params.items()):
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
            raise BodhiClientException('You must specify a username')
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
        with open('/etc/fedora-release', 'r') as f:
            fedora = f.readlines()[0].split()[2]
        tag = 'f%s-updates-testing' % fedora
        builds = self.get_koji_session(
            login=False).listTagged(tag, latest=True)
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
        self.log.info('Reading from %s ' % input_file)
        input_file = os.path.expanduser(input_file)
        if os.path.exists(input_file):
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
                update['type_'] = config.get(section, 'type', raw=True)
                update['request'] = config.get(section, 'request', raw=True)
                update['bugs'] = config.get(section, 'bugs', raw=True)
                update['close_bugs'] = config.getboolean(section, 'close_bugs')
                update['notes'] = config.get(section, 'notes', raw=True)
                update['autokarma'] = config.getboolean(section, 'autokarma')
                update['stable_karma'] = config.getint(section, 'stable_karma')
                update['unstable_karma'] = config.getint(
                    section, 'unstable_karma')
                update['suggest_reboot'] = config.getboolean(
                    section, 'suggest_reboot')
                updates.append(update)
        return updates

    def update_str(self, update, minimal=False):
        """ Return a string representation of a given update dictionary.

        :arg update: An update dictionary, acquired by the ``list`` method.
        :kwarg minimal: Return a minimal one-line representation of the update.

        """
        if isinstance(update, six.string_types):
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
        val = "%s\n%s\n%s\n" % ('=' * 80, '\n'.join(textwrap.wrap(
                update['title'].replace(',', ', '), width=80,
                initial_indent=' '*5, subsequent_indent=' '*5)), '=' * 80)
        if update['updateid']:
            val += "  Update ID: %s\n" % update['updateid']
        val += """    Release: %s
     Status: %s
       Type: %s
      Karma: %d""" % (update['release']['long_name'], update['status'],
                      update['type'], update['karma'])
        if update['request'] is not None:
            val += "\n    Request: %s" % update['request']
        if len(update['bugs']):
            bugs = ''
            i = 0
            for bug in update['bugs']:
                bugstr = '%s%s - %s\n' % (i and ' ' * 11 + ': ' or '',
                                          bug['bz_id'], bug['title'])
                bugs += '\n'.join(textwrap.wrap(
                    bugstr, width=67, subsequent_indent=' '*11+': ')) + '\n'
                i += 1
            bugs = bugs[:-1]
            val += "\n       Bugs: %s" % bugs
        if update['notes']:
            notes = textwrap.wrap(
                update['notes'], width=67, subsequent_indent=' ' * 11 + ': ')
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
                    text = textwrap.wrap(
                        comment['text'], initial_indent=' ' * 13,
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
        if os.path.exists(os.path.join(os.path.expanduser('~'), '.koji', 'config')):
            config.readfp(open(os.path.join(os.path.expanduser('~'), '.koji', 'config')))
        else:
            config.readfp(open('/etc/koji.conf'))
        cert = os.path.expanduser(config.get('koji', 'cert'))
        ca = os.path.expanduser(config.get('koji', 'ca'))
        serverca = os.path.expanduser(config.get('koji', 'serverca'))
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
        return self.send_request('releases/')
