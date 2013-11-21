#!/usr/bin/env python
# -*- coding: utf-8 -*-

__all__ = ['MoQuerySet', 'MoManager']

import copy
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

    def __init__(self, model, fields, using):
        self.model = model
        self.fields = fields
        self._db = using
        self._rawqueryset = None
        self._alias = None
        self._where = {}
        self._joins = []
        self._group_by = []
        self._order_by = []

    def __repr__(self):
        rqs = self._get_rawqueryset()
        text = repr(rqs)
        return '<MoQuerySet: ' + text[14:]  # Replace "<RawQuerySet: "

    def __iter__(self):
        """Iterate through the queryset using the backed RawQuerySet"""
        return iter(self._get_rawqueryset())

    def __getitem__(self, k):
        return list(self)[k]

    def __getattr__(self, name):
        return getattr(self._get_rawqueryset(), name)

    def _clone(self):
        clone = MoQuerySet(
            model=self.model, fields=self.fields, using=self._db
        )
        clone._alias = self._alias
        clone._where = self._where.copy()
        clone._joins = copy.copy(self._joins)
        clone._group_by = copy.copy(self._group_by)
        clone._order_by = copy.copy(self._order_by)
        return clone

    def _get_query_string(self):
        table = self.model._meta.db_table
        star = raw('{table}.*'.format(table=identifier(self._alias or table)))
        kwargs = {'select': [star] + self.fields}
        if self._where:
            kwargs['where'] = self._where
        if self._joins:
            kwargs['joins'] = [join(**j) for j in self._joins]
        if self._group_by:
            kwargs['group_by'] = self._group_by
        if self._order_by:
            kwargs['order_by'] = self._order_by

        # Import MoSQL's detabase specific fixes
        try:
            conn = connections[self._db or DEFAULT_DB_ALIAS]
        except KeyError:
            conn = connections[DEFAULT_DB_ALIAS]
        vendor = conn.vendor
        if vendor == 'postgresql':
            pass
        elif vendor == 'mysql':
            import mosql.mysql as _
            del _   # Get around PyFlakes "imported but not used" warning
        else:
            msg = (
                'Current database ({vendor}) not supported by MoSQL. '
                'Will generate standard SQL instead.'
            ).format(vendor=vendor)
            logger.warning(msg)

        if self._alias:
            table = _as(table, self._alias)
        return select(table, **kwargs)

    def _get_rawqueryset(self):
        if self._rawqueryset is None:
            raw_query = self._get_query_string()
            self._rawqueryset = RawQuerySet(
                raw_query=raw_query, model=self.model, using=self._db
            )
        return self._rawqueryset

    def count(self):
        return len(list(self))

    def as_(self, alias=None):
        clone = self._clone()
        clone._alias = alias
        return clone

    def where(self, mapping):
        clone = self._clone()
        clone._where.update(mapping)
        return clone

    def group_by(self, *fields):
        clone = self._clone()
        clone._group_by += list(fields)
        return clone

    def order_by(self, *fields):
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
        clone._order_by += order_by
        return clone

    def join(self, model, alias, on=None, using=None, join_type=None):
        if isinstance(model, basestring):   # Try to lazy-load the model
            parts = model.split('.')
            if len(parts) == 2 and parts[0] and parts[1]:
                model = get_model(*parts)
        elif isinstance(model, MoQuerySet):     # Handle subquery
            model = raw(paren(model._get_query_string()))

        if inspect.isclass(model) and issubclass(model, Model):
            table = model._meta.db_table
        elif isinstance(model, basestring):
            table = model
        else:
            raise TypeError('join() arg 1 must be a Django model or a str '
                            'subclass instance')
        clone = self._clone()
        join_info = {'table': _as(table, alias), 'on': on, 'using': using}
        if join_type is not None:
            join_info['type'] = join_type
        clone._joins.append(join_info)
        return clone


class MoManager(Manager):
    """Django model manager subclass with MoSQL bridging"""

    def select(self, *extra_field_as):
        """Generate a MoQuerySet to kick-off MoSQL query syntax

        :param extra_field_as: Each item should be a 2-tuple indicating the
            field name and the attribute name it will be injected as.
        """
        fields = [_as(*f) for f in extra_field_as]
        return MoQuerySet(model=self.model, fields=fields, using=self._db)
