'''A module to implement python2.5 functionality for python programs less
than 2.5.
'''
# Deprecate in favor of kitchen.pycompat25.collections.defaultdict
import warnings

warnings.warn('fedora.pycompat25.defaultdict is deprecated, use'
              ' kitchen.pycompat25.collections.defaultdict instead',
              DeprecationWarning, stacklevel=2)

from kitchen.pycompat25.collections import defaultdict

__all__ = ('defaultdict',)
