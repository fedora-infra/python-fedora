# -*- coding: utf-8 -*-
#
# Copyright (C) 2010  Red Hat, Inc.
# This file is part of python-fedora
# 
# python-fedora is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
# 
# python-fedora is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public
# License along with python-fedora; if not, see <http://www.gnu.org/licenses/>
#
'''
Functions to manipulate unicode and byte strings

.. versionadded:: 0.3.17

.. moduleauthor:: Toshio Kuratomi <tkuratom@redhat.com>
'''

from fedora import _

def to_unicode(obj, encoding='utf8', errors='replace', non_string='empty'):
    '''Convert an object into a unicode string

    Usually, this should be used on a byte string but it can take byte strings
    and unicode strings intelligently.  non_string objects are handled in
    different ways depending on the setting of the non_string parameter.

    The default values of this function are set so as to always return
    a unicode string and never raise an error when converting from bytes to
    unicode.  However, when you do not pass validly encoded text as the byte
    string (or a non-string object), you may end up with output that you don't
    expect.  Be sure you understand the requirements of your data, not just
    ignore errors by passing it through this function.

    :arg obj: Object to convert to a unicode string.  This should normally be
        a byte string
    :kwarg encoding: What encoding to try converting the byte string as.
        Defaults to utf8
    :kwarg errors: If errors are given, perform this action.  Defaults to
        'replace' which replaces the error with a character that means the bytes
        were unable to be decoded.  Other values are those that can be given to
        the unicode constructor, for instance 'strict' which raises an
        exception and 'ignore' which simply omits the non-decodable
        characters.
    :kwargs non_string: How to treat non_string values.  Possible values are:
            :empty: Return an empty string
            :strict: Raise a TypeError
            :passthru: Return the object unchanged
            :repr: Attempt to return a unicode string of the repr of the
                object
        The Default is 'empty'
    :raises TypeError: if non_string is strict and a non-basestring object is
        passed in or if :param:`non_string` is set to an unknown value
    :returns: unicode string or the original object depending on the value of
        non_string.
    '''
    if isinstance(obj, basestring):
        if isinstance(obj, unicode):
            return obj
        return unicode(obj, encoding=encoding, errors=errors)
    if non_string == 'empty':
        return u''
    elif non_string == 'passthru':
        return obj
    elif non_string in ('repr', 'strict'):
        obj_repr = repr(obj)
        if not isinstance(obj_repr, unicode):
            unicode(obj_repr, encoding=encoding, errors=errors)
        if non_string == 'strict':
            return obj_repr
        raise TypeError(_('to_unicode was given "%(obj)s" which is neither'
            ' a byte string (str) or a unicode string') % {'obj': obj_repr})

    raise TypeError(_('non_string value, %(param)s, is not set to a valid'
        ' action') % {'param': non_string})

def to_bytes(obj, encoding='utf8', errors='replace', non_string='empty'):
    '''Convert an object into a byte string

    Usually, this should be used on a unicode string but it can take byte
    strigs and unicode strings intelligently.  non_string objects are handled
    in different ways depending on the setting of the non_string parameter.

    The default values of this function are set so as to always return
    a byte string and never raise an error when converting from unicode to
    bytes.  However, when you do not pass an encoding that can validly encode
    the object (or a non-string object), you may end up with output that you
    don't expect.  Be sure you understand the requirements of your data, not
    just ignore errors by passing it through this function.

    :arg obj: Object to convert to a byte string.  this should normally be
        a unicode string.
    :kwarg encoding: What encoding to try using to convert the unicode string
        into bytes.  Defaults to utf8
    :kwarg errors: If errors are given, perform this action.  Defaults to
        'replace' which replaces the error with a '?' character to show
        a character was wunable to be decoded.  Other values are those that
        can be given to the :function:`str.encode()` method.  For instance
        'strict' which raises an exception and 'ignore' which simply omits the
        non-encodable characters.
    :kwargs non_string: How to treat non_string values.  Possible values are:
            :empty: Return an empty byte string
            :strict: Raise a TypeError
            :passthru: Return the object unchanged
            :repr: Attempt to return a byte string of the repr of the
                object
        The Default is 'empty'
    :raises TypeError: if non_string is strict and a non-basestring object is
        passed in or if :param:`non_string` is set to an unknown value
    :returns: byte string or the original object depending on the value of
        non_string.
    '''
    if isinstance(obj, basestring):
        if isinstance(obj, str):
            return obj
        return obj.encode(encoding, errors)
    if non_string == 'empty':
        return ''
    elif non_string == 'passthru':
        return obj
    elif non_string in ('repr', 'strict'):
        obj_repr = repr(obj)
        if isinstance(obj_repr, unicode):
            obj_repr =  obj_repr.encode(encoding, errors)
        else:
            obj_repr = str(obj_repr)
        if non_string == 'repr':
            return obj_repr
        raise TypeError(_('to_bytes was given "%(obj)s" which is neither'
            ' a unicode string or a byte string (str)') % {'obj': obj_repr})

    raise TypeError(_('non_string value, %(param)s, is not set to a valid'
        ' action') % {'param': non_string})

__all__ = ['to_unicode', 'to_bytes']
