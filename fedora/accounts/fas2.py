import urllib
import urllib2
import simplejson
from urlparse import urljoin
from fedora.tg.client import BaseClient, AuthError, ServerError

class AccountSystem(BaseClient):

    def __init__(self, baseURL, username=None, password=None, debug=False):
        super(AccountSystem, self).__init__(baseURL=baseURL, username=username, password=password, debug=debug)

    # TODO: Use exceptions properly
    def group_by_id(self, id):
        """Returns a group object based on its id"""
        params = {'id': id}
        request = self.send_request('json/group_by_id', auth=True, input=params)
        if request['success']:
            return request['group']
        else:
            return dict()

    def person_by_id(self, id):
        """Returns a person object based on its id"""
        params = {'id': id}
        request = self.send_request('json/person_by_id', auth=True, input=params)
        if request['success']:
            return request['person']
        else:
            return dict()

    def group_by_name(self, groupname):
        """Returns a group object based on its name"""
        params = {'groupname': groupname}
        request = self.send_request('json/group_by_name', auth=True, input=params)
        if request['success']:
            return request['group']
        else:
            return dict()

    def person_by_username(self, username):
        """Returns a person object based on its username"""
        params = {'username': username}
        request = self.send_request('json/person_by_username', auth=True, input=params)
        if request['success']:
            return request['person']
        else:
            return dict()

    def user_id(self):
        """Returns a dict relating user IDs to usernames"""
        request = self.send_request('json/user_id', auth=True)
        return request['people']

    def authenticate(self, username, password):
        """TODO"""
        req = urllib2.Request(urljoin(self.baseURL, 'login?tg_format=json'))
        req.add_data(urllib.urlencode({
            'user_name' : username,
            'password'  : password,
            'login'     : 'Login'
            }))
        try:
            response = urllib2.urlopen(req)
        except urllib2.HTTPError, e:
            if e.msg == 'Forbidden':
                return False
        jsonString = response.read()
        try:
            data = simplejson.loads(jsonString)
        except ValueError, e:
            # The response wasn't JSON data
            raise ServerError, str(e)
        try:
            if data['user']:
                return data['user']['username'] == username
        except KeyError:
            pass
        return False
