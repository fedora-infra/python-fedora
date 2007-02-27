import ldap

class Server:
    def __init__(self, server='localhost', who='', password=''):
        self.ldapConn = ldap.open(server)
        self.ldapConn.simple_bind_s(who, password)

class Group:
    ''' Individual Group abstraction class '''
    def __init__(self, fedoraRoleApprovalDate, fedoraRoleSponsor, cn, fedoraRoleCreationDate, objectClass, fedoraRoleType, fedoraRoleStatus, fedoraRoleDomain):
        self.fedoraRoleApprovalDate = fedoraRoleApprovalDate
        self.fedoraRoleSponsor = fedoraRoleSponsor
        self.cn = cn
        self.fedoraRoleCreationDate = fedoraRoleCreationDate
        self.objectClass = objectClass
        self.fedoraRoleType = fedoraRoleType
        self.fedoraRoleStatus = fedoraRoleStatus
        self.fedoraRoleDomain = fedoraRoleDomain

class Groups:
    ''' Class contains group information '''
    @classmethod
    def byUserName(self, cn):
        server = Server()
        groups = {}
        filter = 'objectClass=FedoraRole'
        base = 'ou=Roles,cn=%s,ou=People,dc=fedoraproject,dc=org' % cn
        groupsDict = search(server.ldapConn, base, filter)
        for group in groupsDict:
            cn = group[0][1]['cn'][0]
            groups[cn] = Group(
                fedoraRoleApprovalDate = group[0][1]['fedoraRoleApprovalDate'][0],
                fedoraRoleSponsor = group[0][1]['fedoraRoleSponsor'][0],
                cn = group[0][1]['cn'][0],
                fedoraRoleCreationDate = group[0][1]['fedoraRoleCreationDate'][0],
                objectClass = group[0][1]['objectClass'][0],
                fedoraRoleType = group[0][1]['fedoraRoleType'][0],
                fedoraRoleStatus = group[0][1]['fedoraRoleStatus'][0],
                fedoraRoleDomain = group[0][1]['fedoraRoleDomain'][0]
                        )
        return groups

    @classmethod
    def byGroupName(self, cn):
        server = Server()
        users = {}
        filter = 'cn=%s' % cn
        base = 'ou=People,dc=fedoraproject,dc=org'
        attributes = ['cn']
        usersDict = search(server.ldapConn, base, filter)
        for user in usersDict:
            userName = user[0][0].split(',')[2].split('=')[1]

            users[userName] = Group(
                fedoraRoleApprovalDate = user[0][1]['fedoraRoleApprovalDate'][0],
                fedoraRoleSponsor = user[0][1]['fedoraRoleSponsor'][0],
                cn = user[0][1]['cn'][0],
                fedoraRoleCreationDate = user[0][1]['fedoraRoleCreationDate'][0],
                objectClass = user[0][1]['objectClass'][0],
                fedoraRoleType = user[0][1]['fedoraRoleType'][0],
                fedoraRoleStatus = user[0][1]['fedoraRoleStatus'][0],
                fedoraRoleDomain = user[0][1]['fedoraRoleDomain'][0]
            )
        return users

class Person:
    ''' information and attributes about users '''
    base = 'ou=People,dc=fedoraproject,dc=org'
    @classmethod
    def byFilter(self, filter):
        server = Server()
        person = search(server.ldapConn, self.base, filter)[0][0]
        self.telephoneNumber = person[1]['telephoneNumber'][0]
        self.userName = person[1]['cn'][0]
        self.bugzillaEmail = person[1]['fedoraPersonBugzillaMail'][0]
        self.ircNick = person[1]['fedoraPersonIrcNick'][0]
        self.pgpKey = person[1]['fedoraPersonKeyId'][0]
        self.primaryEmail = person[1]['mail'][0]
        self.postalAddress = person[1]['postalAddress'][0]
        self.givenName = person[1]['givenName'][0]
        self.sshPubKey = person[1]['fedoraPersonSshKey'][0]
        self.description = person[1]['description'][0]
        return self

    @classmethod
    def byUserName(self, cn):
        '''Wrapper for byFilter - search by cn'''
        return self.byFilter('cn=%s' % cn)
    
    @classmethod
    def auth(self, who, password, server='localhost'):
        ''' Basic Authentication Module '''
        server = Server()
        who = 'cn=%s,ou=People,dc=fedoraproject,dc=org' % who
        server.ldapConn.simple_bind_s(who, password)


class UserAccount:
    def __init__(self):
        self.realName = 'Mike McGrath'
        self.userName = 'mmcgrath'
        self.primaryEmail = 'mmcgrath@redhat.com'
        self.groups = []
        self.groups.append('Fedora Documentation Team')
        self.groups.append('Fedora Infrastructure Team')

def search(ldapServer, base, filter, attributes=None):
    scope = ldap.SCOPE_SUBTREE
    count = 0
    timeout = 2
    result_set = []
    try:
        result_id = ldapServer.search(base, scope, filter, attributes)
        while 1:
            result_type, result_data = ldapServer.result(result_id, timeout)
            if (result_data == []):
                break
            else:
                if result_type == ldap.RES_SEARCH_ENTRY:
                    result_set.append(result_data)
        if len(result_set) == 0:
            print "No results."
            return
    except ldap.LDAPError, e:
        print "Crap: %s" % e
        raise

    return result_set
