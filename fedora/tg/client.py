'''This is for compatibility.

The canonical location for this module from 0.3 on is fedora.client
'''
import warnings
warnings.warn('fedora.tg.client has moved to fedora.client.'
        '  This will disappear in 0.4', DeprecationWarning, stacklevel=2)

from fedora.client import *
