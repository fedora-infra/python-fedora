# -*- coding: utf-8 -*-
#
# Copyright (C) 2007-2008  Red Hat, Inc.
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
JSON Helper functions.  Most JSON code directly related to classes is
implemented via the __json__() methods in model.py.  These methods define
methods of transforming a class into json for a few common types.

A JSON-based API(view) for your app.  Most rules would look like::

    @jsonify.when("isinstance(obj, YourClass)")
    def jsonify_yourclass(obj):
        return [obj.val1, obj.val2]

@jsonify can convert your objects to following types:
lists, dicts, numbers and strings

.. moduleauthor:: Toshio Kuratomi <tkuratom@redhat.com>
'''

# Pylint ignored messages
# :E1101: turbogears.jsonify monkey patches some functionality in.  These do
#   not show up when we pylint so it thinks the members di not exist.

import sqlalchemy
import sqlalchemy.orm
import sqlalchemy.ext.associationproxy
import sqlalchemy.engine.base
from turbojson.jsonify import jsonify

class SABase(object):
    '''Base class for SQLAlchemy mapped objects.

    This base class makes sure we have a __json__() method on each SQLAlchemy
    mapped object that knows how to:

    1) Return json for the object.
    2) Selectively add tables pulled in from the table to the data we're
       returning.
    '''
    # :R0903: The SABase object just adds a __json__ method to all SA mapped
    #   classes so they can be serialized as json.  It's used as a base class
    #   and that's it.
    # pylint: disable-msg=R0903
    def __json__(self):
        '''Transform any SA mapped class into json.

        This method takes an SA mapped class and turns the "normal" python
        attributes into json.  The properties (from properties in the mapper)
        are also included if they have an entry in json_props.  You make
        use of this by setting json_props in the controller.

        Example controller::

            john = model.Person.get_by(name='John')
            # Person has a property, addresses, linking it to an Address class.
            # Address has a property, phone_nums, linking it to a Phone class.
            john.json_props = {'Person': ['addresses'],
                  'Address': ['phone_nums']}
            return dict(person=john)

        json_props is a dict that maps class names to lists of properties you
        want to output.  This allows you to selectively pick properties you
        are interested in for one class but not another.  You are responsible
        for avoiding loops.  ie: *don't* do this::

            john.json_props = {'Person': ['addresses'], 'Address': ['people']}
        '''
        props = {}
        prop_list = {}
        if hasattr(self, 'json_props'):
            for base_class in self.__class__.__mro__:
                # pylint: disable-msg=E1101
                if base_class.__name__ in self.json_props:
                    prop_list = self.json_props[base_class.__name__]
                    break
                # pylint: enable-msg=E1101

        # Load all the columns from the table
        for column in sqlalchemy.orm.object_mapper(self).iterate_properties:
            if isinstance(column, sqlalchemy.orm.properties.ColumnProperty):
                props[column.key] = getattr(self, column.key)

        # Load things that are explicitly listed
        for field in prop_list:
            props[field] = getattr(self, field)
            try:
                # pylint: disable-msg=E1101
                props[field].json_props = self.json_props
            except AttributeError: # pylint: disable-msg=W0704
                # :W0704: Certain types of objects are terminal and won't
                #   allow setting json_props
                pass

            # Note: Because of the architecture of simplejson and turbojson,
            # anything that inherits from a builtin list, tuple, basestring,
            # or dict but needs special handling needs to be specified
            # expicitly here.  Using the @jsonify.when() decorator won't work.
            if isinstance(props[field],
                    sqlalchemy.orm.collections.InstrumentedList):
                props[field] = jsonify_salist(props[field])

        return props

@jsonify.when('isinstance(obj, sqlalchemy.orm.query.Query)')
def jsonify_sa_select_results(obj):
    '''Transform selectresults into lists.

    The one special thing is that we bind the special json_props into each
    descendent.  This allows us to specify a json_props on the toplevel
    query result and it will pass to all of its children.

    :arg obj: sqlalchemy Query object to jsonify
    :Returns: list representation of the Query with each element in it given
        a json_props attributes
    '''
    if 'json_props' in obj.__dict__:
        for element in obj:
            element.json_props = obj.json_props
    return list(obj)

# Note: due to the way simplejson works, InstrumentedList has to be taken care
# of explicitly in SABase's __json__() method.  (This is true of any object
# derived from a builtin type (list, dict, tuple, etc))
@jsonify.when('''(
        isinstance(obj, sqlalchemy.orm.collections.InstrumentedList) or
        isinstance(obj, sqlalchemy.orm.attributes.InstrumentedAttribute) or
        isinstance(obj, sqlalchemy.ext.associationproxy._AssociationList))''')
def jsonify_salist(obj):
    '''Transform SQLAlchemy InstrumentedLists into json.

    The one special thing is that we bind the special json_props into each
    descendent.  This allows us to specify a json_props on the toplevel
    query result and it will pass to all of its children.

    :arg obj: One of the sqlalchemy list types to jsonify
    :Returns: list of jsonified elements
    '''
    if 'json_props' in obj.__dict__:
        for element in obj:
            element.json_props = obj.json_props
    return [jsonify(element) for element in  obj]

@jsonify.when('''(
        isinstance(obj, sqlalchemy.engine.base.ResultProxy)
        )''')
def jsonify_saresult(obj):
    '''Transform SQLAlchemy ResultProxy into json.

    The one special thing is that we bind the special json_props into each
    descendent.  This allows us to specify a json_props on the toplevel
    query result and it will pass to all of its children.

    :arg obj: sqlalchemy ResultProxy to jsonify
    :Returns: list of jsonified elements
    '''
    if 'json_props' in obj.__dict__:
        for element in obj:
            element.json_props = obj.json_props
    return [list(row) for row in obj]

@jsonify.when('''(isinstance(obj, set))''')
def jsonify_set(obj):
    '''Transform a set into a list.

    simplejson doesn't handle sets natively so transform a set into a list.

    :arg obj: set to jsonify
    :Returns: list representation of the set
    '''
    return list(obj)
