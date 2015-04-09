import functools
import os

from nose.exc import SkipTest

try:
    from nose.tools.nontrivial import make_decorator
except ImportError:
    # It lives here in older versions of nose (el6)
    from nose.tools import make_decorator


def _asbool(s):
    return s.lower() in ['y', 'yes', 'true', '1']


def networked(func):
    """A decorator that skips tests if $NETWORKED is false or undefined.

    This decorator allows us to have tests that a developer might want to
    run but shouldn't be run by random people building the package.  It
    also makes non-networked build systems happy.
    """
    @functools.wraps(func)
    def newfunc(self, *args, **kw):
        if not _asbool(os.environ.get('NETWORKED', 'False')):
            raise SkipTest('Only run if you have network access.')
        return func(self, *args, **kw)
    return make_decorator(func)(newfunc)


