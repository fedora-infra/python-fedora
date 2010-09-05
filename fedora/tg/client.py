'''This is for compatibility.

The canonical location for this module from 0.3 on is fedora.client
'''
import warnings
from fedora import b_

warnings.warn(b_('fedora.tg.client has moved to fedora.client.  This location'
        ' will disappear in 0.4'), DeprecationWarning, stacklevel=2)

# pylint: disable-msg=W0401,W0614
from fedora.client import *
