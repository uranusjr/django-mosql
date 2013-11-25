#!/usr/bin/env python
# -*- coding: utf-8 -*-

__all__ = ['MoQuerySet', 'MoManager']

import copy
import importlib
import inspect
import logging
from django.db import connections
from django.db.models import Model, Manager, get_model
from django.db.models.query import RawQuerySet
from django.db.utils import DEFAULT_DB_ALIAS
from mosql.query import select, join
from mosql.util import raw, identifier, paren
try:
    basestring
except NameError:   # If basestring is not a thing, just alias it to str
    basestring = str

logger = logging.getLogger(__name__)


def _as(src, dest):
    return raw('%s AS %s' % (identifier(src), identifier(dest)))


class MoQuerySet(object):
    """Django query set wrapper to bridge with MoSQL"""

    def __init__(self, model, extra_fields, using):
        """Initialize a :class:`MoQuerySet` object.

        :param model: Model class to be queried on.
        :type model: :class:`django.db.models.Model`
        :param extra_fields: Extra fields to be injected into the resulting
            instances. Each item should be a 2-tuple indicating the field name
            and the attribute name it will be injected as.
        :param using: Database to use when quering. If given `None`, the
            default database will be used.
        :type using: `str` or `None`
        """
        self.model = model
        self.extra_fields = extra_fields
        self._db = using
        self._rawqueryset = None
        self._params = {
            'alias': None,
            'where': {},
            'joins': [],
            'group_by': [],
            'order_by': []
        }

    def __repr__(self):
        return '<MoQuerySet: {query}>'.format(query=self.query)

    def __iter__(self):
        """Iterate through the queryset using the backed RawQuerySet"""
        return iter(self.resolve())

    def __getitem__(self, k):
        return list(self)[k]

    def _clone(self):
        clone = MoQuerySet(
            model=self.model,
            extra_fields=copy.copy(self.extra_fields),
            using=self._db
        )
        for k in self._params:
            clone._params[k] = copy.copy(self._params[k])
        return clone

    @property
    def query(self):
        """The raw SQL that will be used to resolve the queryset."""
        # Import MoSQL's detabase specific fixes
        try:
            conn = connections[self._db or DEFAULT_DB_ALIAS]
        except KeyError:
            conn = connections[DEFAULT_DB_ALIAS]
        vendor = conn.vendor
        if vendor == 'postgresql':
            pass
        elif vendor == 'mysql':
            importlib.import_module('mosql.mysql')
        else:
            msg = (
                'Current database ({vendor}) not supported by MoSQL. '
                'Will generate standard SQL instead.'
            ).format(vendor=vendor)
            logger.warning(msg)

        if self._params['joins']:
            for join_info in self._params['joins']:
                join_info['table'] = join_info['table']()
            self._params['joins'] = [join(**j) for j in self._params['joins']]

        table = self.model._meta.db_table
        alias = self._params.pop('alias', None)
        star = raw('{table}.*'.format(table=identifier(alias or table)))

        kwargs = {'select': [star] + [_as(*f) for f in self.extra_fields]}
        for k in self._params:
            if self._params[k]:
                kwargs[k] = self._params[k]

        if alias:
            table = _as(table, alias)
        return select(table, **kwargs)

    def resolve(self):
        """Resolve the queryset."""
        if self._rawqueryset is None:
            self._rawqueryset = RawQuerySet(
                raw_query=self.query, model=self.model, using=self._db
            )
        return self._rawqueryset

    def count(self):
        return len(list(self))

    def as_(self, alias):
        """Create an ``AS`` clause for the current model in the query.

        :param alias: The alias for the ``AS`` clause.
        :type alias: `str`
        """
        clone = self._clone()
        clone._params['alias'] = alias
        return clone

    def where(self, mapping):
        """Create a ``WHERE`` clause in the query.

        Example::

            Fruit.objects.where({'kind': 'apple', 'price >=': 2.0})

        which will be translated into something like
        ::

            SELECT * FROM fruit WHERE find = 'apple' AND price >= 2.0

        """
        clone = self._clone()
        clone._params['where'].update(mapping)
        return clone

    def group_by(self, *fields):
        """Create a ``GROUP BY`` clause in the query."""
        clone = self._clone()
        clone._params['group_by'] += list(fields)
        return clone

    def order_by(self, *fields):
        """Create a ``ORDER BY`` clause in the query.

        Each field can contain either "ASC", "DESC", or Django-style ``-``
        prefix to indicate ordering direction.
        """
        # Try to be sensitive and allow both MoSQL's usage (ASC and DESC) and
        # Django ORM's convention (the "-" prefix), while maintaining support
        # for field names with leading dash (-field) with "-field ASC" and
        # "-field DESC"
        order_by = []
        for f in fields:
            parts = f.split(' ')
            if len(parts) == 1:
                fieldname = parts[0]
                if fieldname.startswith('-'):
                    fieldname = fieldname[1:] + ' DESC'
                order_by.append(fieldname)
            elif len(parts) == 2 and parts[1] == 'ASC' or parts[1] == 'DESC':
                    order_by.append(f)
            else:
                raise SyntaxError('Invalid ordering field {}'.format(f))
        clone = self._clone()
        clone._params['order_by'] += order_by
        return clone

    def join(self, model, alias, on=None, using=None, join_type=None):
        """Create a ``JOIN`` clause in the query.

        :param model: A model to be joined on. This can be a model class, or
            a ``<appname>.<ModelName>`` string to lazy-load the model. For
            joining a non-Django model, you can also provide a plain table
            name.
        :type model: `str` or `django.db.models.Model`
        :param alias: The alias for the to-be-joined model. An ``AS`` clause
            will be created automatically based on this value.
        :param on: A mapping for fields to be joined on. Results in a
            ``JOIN ... ON`` query.
        :type on: `dict`
        :param using: A sequence of fields to be joined on. Results in a
            ``JOIN ... USING`` query.
        :param join_type: The type of ``JOIN`` to be used. Possible values
            include ``INNER``, ``LEFT``, ``CROSS`` and other standard SQL
            ``JOIN`` types. If ommited, a suitable type will be inferred
            automatically.
        """
        if isinstance(model, basestring):   # Try to lazy-load the model
            parts = model.split('.')
            if len(parts) == 2 and all(parts):
                model = get_model(*parts) or model
        elif isinstance(model, MoQuerySet):     # Handle subquery
            model = raw(paren(model.query))

        if inspect.isclass(model) and issubclass(model, Model):
            table = model._meta.db_table
        elif isinstance(model, basestring):
            table = model
        else:
            raise TypeError('join() arg 1 must be a Django model or a str '
                            'subclass instance')
        clone = self._clone()
        join_info = {
            'table': lambda: _as(table, alias),
            'on': on, 'using': using
        }
        if join_type is not None:
            join_info['type'] = join_type
        clone._params['joins'].append(join_info)
        return clone


class MoManager(Manager):
    """Django model manager subclass with MoSQL bridging"""

    def select(self, *extra_field_as):
        """Generate a MoQuerySet to kick-off MoSQL query syntax

        :param extra_field_as: Each item should be a 2-tuple indicating the
            field name and the attribute name it will be injected as.
        """
        return MoQuerySet(
            model=self.model,
            extra_fields=extra_field_as,
            using=self._db
        )
