from fasjson_client import Client


class NewAccountSystem(object):
    def __init__(self, base_url, principal=None, bravado_config=None, api_version=1):
        self.client = Client(url=base_url, principal=principal, bravado_config=bravado_config, api_version=api_version)

    def group_by_name(self, groupname):
        '''
        Returns a group object based on its name
        
        :arg groupname: The string representing the name of the group to retrieve
        '''
        return self.client.groups.get_group(name=groupname).response().result

    def groups(self):
        '''Returns a list of all groups'''
        return self.client.groups.list_groups().response().result

    def group_members(self, groupname):
        '''Returns a list of members of a group given the group name
        
        :arg groupname: The string representing the name of the group
        '''
        return self.client.groups.get_group_members(name=groupname).response().result
    
    def person_by_username(self, username):
        '''
        Returns a person object based on their username
        
        :arg username: The username of the person to retrieve
        '''
        return self.client.users.get_user(username=username).response().result
    
    def user_data(self):
        '''Returns a list of all users'''
        return self.client.users.list_users().response().result

    def me(self):
        '''Returns information about the current user or service'''
        return self.client.me.whoami().response().result