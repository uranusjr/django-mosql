#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import copy
import inspect

from django.db import router
from django.db.models import Model, Manager
from django.db.models.query import RawQuerySet
from django.utils import six

from mosql.query import select, join, delete
from mosql.util import raw, identifier, paren

from .compat import get_model
from .db.handlers import get_engine_handler

__all__ = ['MoQuerySet', 'MoManager']


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
        self._for_write = False
        self._params = {
            'offset': 0,
            'limit': None,
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
        if not isinstance(k, (slice,) + six.integer_types):
            raise TypeError('Expecting {expect}, got {got}'.format(
                expect='slice object or integer',
                got=k.__class__.__name__
            ))
        assert (
            (isinstance(k, slice)
                and (k.start is None or k.start >= 0)
                and (k.stop is None or k.stop >= 0))
            or (not isinstance(k, slice) and k >= 0)
        ), 'Negative indexing is not supported.'

        if isinstance(k, slice):
            clone = self._clone()
            if k.start is not None:
                clone._params['offset'] += k.start
            if k.stop is not None:
                limit = k.stop - (k.start or 0)
                if (clone._params['limit'] is None
                        or limit < clone._params['limit']):
                    clone._params['limit'] = limit
            return clone
        else:
            return list(self)[k]

    @property
    def db(self):
        if self._for_write:
            return self._db or router.db_for_write(self.model)
        return self._db or router.db_for_read(self.model)

    def _clone(self):
        clone = MoQuerySet(
            model=self.model,
            extra_fields=copy.copy(self.extra_fields),
            using=self._db
        )
        for k in self._params:
            clone._params[k] = copy.copy(self._params[k])
        return clone

    def _get_select_query(self, fields=None):
        """The raw SQL that will be used to resolve the queryset."""
        handler = get_engine_handler(self.db)

        with handler.patch():
            params = copy.deepcopy(self._params)
            if params['joins']:
                params['joins'] = [
                    join(table=(j.pop('table'),), **j)
                    for j in params['joins']
                ]

            table = self.model._meta.db_table
            alias = params.pop('alias', None)

            kwargs = {k: v for k, v in params.items() if v}

            # Inject default field names.
            # If this query does not contain a GROUP BY clause, we can safely
            #   use a "*" to indicate all fields;
            # If the query has aggregation (GROUP BY), however, we will need to
            #   choose a value to display for each field (especially pk because
            #   it is needed by Django). Since accessing those fields doesn't
            #   really make sense anyway, We arbitrarily use MIN.
            table_name = alias or table

            if fields is not None:
                kwargs['select'] = [
                    f if '.' in f or isinstance(f, raw)
                    else raw('{table}.{field}'.format(
                        table=identifier(table_name), field=identifier(f))
                    ) for f in fields
                ]
            elif self._params['group_by']:
                kwargs['select'] = (
                    handler.get_aggregated_columns_for_group_by(self, 'MIN')
                )
            else:
                kwargs['select'] = handler.get_star(self)

            kwargs['select'].extend(self.extra_fields)
            if 'offset' in kwargs and 'limit' not in kwargs:
                kwargs['limit'] = handler.no_limit_value()

            if alias:
                table = ((table, alias),)
            query = select(table, **kwargs)
            return query

    @property
    def query(self):
        return self._get_select_query()

    def delete(self):
        """Delete objects selected by the QuerySet"""
        # Try to keep things simple by resolving a direct DELETE ... WHERE ...
        # query. If that proves impossible, fallback to the naive DELETE ...
        # WHERE <pk> IN (SELECT ...) solution.
        self._for_write = True
        handler = get_engine_handler(self.db)
        table = self.model._meta.db_table

        params = copy.deepcopy(self._params)
        where = params.pop('where')

        with handler.patch():
            if any(params.values()):
                # If any of the remaining params is not empty, play safe and
                # fallback to subquery
                query = delete(table, where=handler.get_where_for_delete(self))
            else:
                # Try to be smart
                query = delete(table, where=where)

        # Execute the query
        cursor = handler.cursor()
        cursor.execute(query)
        return cursor.rowcount

    def resolve(self):
        """Resolve the queryset."""
        if self._rawqueryset is None:
            self._rawqueryset = RawQuerySet(
                raw_query=self.query, model=self.model, using=self._db
            )
        return self._rawqueryset

    def count(self):
        return len(list(self))

    def select(self, *extra_fields_as):
        """Provide extra fields to select on.

        :param extra_fields_as: Each item should be a 2-tuple indicating the
            field name and the attribute name it will be injected as.
        """
        clone = self._clone()
        clone.extra_fields += extra_fields_as
        return clone

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
        if isinstance(model, six.string_types):   # Try to lazy-load the model
            parts = model.split('.')
            if len(parts) == 2 and all(parts):
                model = get_model(*parts) or model
        elif isinstance(model, MoQuerySet):     # Handle subquery
            model = raw(paren(model.query))

        if inspect.isclass(model) and issubclass(model, Model):
            table = model._meta.db_table
        elif isinstance(model, six.string_types):
            table = model
        else:
            raise TypeError('join() arg 1 must be a Django model or a str '
                            'subclass instance')
        clone = self._clone()
        join_info = {'table': (table, alias), 'on': on, 'using': using}
        if join_type is not None:
            join_info['type'] = join_type
        clone._params['joins'].append(join_info)
        return clone


class MoManager(Manager):
    """Django model manager subclass with MoSQL bridging"""

    def select(self, *extra_fields_as):
        """Generate a MoQuerySet to kick-off MoSQL query syntax

        :param extra_fields_as: Each item should be a 2-tuple indicating the
            field name and the attribute name it will be injected as.
        """
        return MoQuerySet(
            model=self.model,
            extra_fields=extra_fields_as,
            using=self._db
        )
