import sys
import fedora.client

import getpass

print(sys.version)
print(fedora.client.__file__)

password = getpass.getpass()
#fas = fedora.client.AccountSystem(username='ralph', password=password)
#print(fas.people_by_groupname('sysadmin-main'))
#print(fas.person_by_username('ralph'))

bodhi = fedora.client.BodhiClient(username='ralph', password=password)
print(bodhi.latest_builds('ansi2html'))
print(bodhi.get_releases())
print(bodhi.query(mine=True))
