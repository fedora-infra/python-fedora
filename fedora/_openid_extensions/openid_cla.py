"""CLA extension request and response parsing and object representation
@var cla_uri: The URI used for the CLA extension namespace and XRD Type Value
"""

from openid.message import registerNamespaceAlias, \
     NamespaceAliasRegistrationError
from openid.extension import Extension
import logging

try:
    basestring #pylint:disable-msg=W0104
except NameError:
    # For Python 2.2
    basestring = (str, unicode) #pylint:disable-msg=W0622

__all__ = [
    'CLARequest',
    'CLAResponse',
    'cla_uri',
    'supportsCLA',
    ]

# The namespace for this extension
cla_uri = 'http://fedoraproject.org/specs/open_id/cla'

# Some predefined CLA uris
CLA_URI_FEDORA_CLICK = 'http://admin.fedoraproject.org/accounts/cla/click'
CLA_URI_FEDORA_DELL = 'http://admin.fedoraproject.org/accounts/cla/dell'
CLA_URI_FEDORA_DONE = 'http://admin.fedoraproject.org/accounts/cla/done'
CLA_URI_FEDORA_FEDORA = 'http://admin.fedoraproject.org/accounts/cla/fedora'
CLA_URI_FEDORA_FPCA = 'http://admin.fedoraproject.org/accounts/cla/fpca'
CLA_URI_FEDORA_IBM = 'http://admin.fedoraproject.org/accounts/cla/ibm'
CLA_URI_FEDORA_INTEL = 'http://admin.fedoraproject.org/accounts/cla/intel'
CLA_URI_FEDORA_REDHAT = 'http://admin.fedoraproject.org/accounts/cla/redhat'


try:
    registerNamespaceAlias(cla_uri, 'cla')
except NamespaceAliasRegistrationError, e:
    logging.exception('registerNamespaceAlias(%r, %r) failed: %s' % (cla_uri,
                                                               'cla', str(e),))

def supportsCLA(endpoint):
    return endpoint.usesExtension(cla_uri)

class CLARequest(Extension):
    ns_uri = 'http://fedoraproject.org/specs/open_id/cla'
    ns_alias = 'cla'

    def __init__(self, requested=None):
        Extension.__init__(self)
        self.requested = []

        if requested:
            self.requestCLAs(requested)

    def requestedCLAs(self):
        return self.requested

    def fromOpenIDRequest(cls, request):
        self = cls()

        # Since we're going to mess with namespace URI mapping, don't
        # mutate the object that was passed in.
        message = request.message.copy()

        args = message.getArgs(self.ns_uri)
        self.parseExtensionArgs(args)

        return self

    fromOpenIDRequest = classmethod(fromOpenIDRequest)

    def parseExtensionArgs(self, args):
        items = args.get('query_cla')
        if items:
            for cla_uri in items.split(','):
                self.requestCLA(cla_uri)

    def wereCLAsRequested(self):
        return bool(self.requested)

    def __requests__(self, cla_uri):
        return cla_uri in self.requested

    def requestCLA(self, cla_uri):
        if not cla_uri in self.requested:
            self.requested.append(cla_uri)

    def requestCLAs(self, cla_uris):
        if isinstance(cla_uris, basestring):
            raise TypeError('CLA URIs should be passed as a list of '
                            'strings (not %r)' % (type(field_names),))

        for cla_uri in cla_uris:
            self.requestCLA(cla_uri)

    def getExtensionArgs(self):
        args = {}

        if self.requested:
            args['query_cla'] = ','.join(self.requested)

        return args

class CLAResponse(Extension):
    ns_uri = 'http://fedoraproject.org/specs/open_id/cla'
    ns_alias = 'cla'

    def __init__(self, clas=None):
        Extension.__init__(self)
        if clas is None:
            self.clas = []
        else:
            self.clas = clas

    def extractResponse(cls, request, clas):
        self = cls()
        for cla in request.requestedCLAs():
            if cla in clas:
                self.clas.append(cla)
        return self

    extractResponse = classmethod(extractResponse)

    def fromSuccessResponse(cls, success_response, signed_only=True):
        self = cls()
        if signed_only:
            args = success_response.getSignedNS(self.ns_uri)
        else:
            args = success_response.message.getArgs(self.ns_uri)

        if not args:
            return None

        self.clas = args['signed_cla'].split(',')

        return self

    fromSuccessResponse = classmethod(fromSuccessResponse)

    def getExtensionArgs(self):
        return {'signed_cla': ','.join(self.clas)}
