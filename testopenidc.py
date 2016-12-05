from fedora.client.openidcclient import OpenIDCBaseClient

import logging
logging.basicConfig(level=logging.DEBUG)

inst = OpenIDCBaseClient('http://myapp.com', 'myapp', id_provider='http://172.17.0.2:8080/openidc/')

print inst.get_token(['ipsilon'], False)
