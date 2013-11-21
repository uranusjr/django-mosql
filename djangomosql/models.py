#!/usr/bin/env python
# -*- coding: utf-8 -*-

import copy
import logging
from django.db import connections
from django.db.models import Model, Manager, get_model
from django.db.models.query import RawQuerySet
from django.db.utils import DEFAULT_DB_ALIAS
from mosql.query import select, join
from mosql.util import raw, identifier, star
try:
    basestring
except NameError:   # If basestring is not a thing, just alias it to str
    basestring = str


__all__ = ['MoQuerySet', 'MoManager']

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
        self._where = {}
        self._joins = []

    def __iter__(self):
        """Iterate through the queryset using the backed RawQuerySet"""
        return self._get_rawqueryset().__iter__()

    def __getitem__(self, k):
        return list(self)[k]

    def __getattr__(self, name):
        return getattr(self._get_rawqueryset(), name)

    def _clone(self):
        clone = MoQuerySet(
            model=self.model, fields=self.fields, using=self._db
        )
        clone._where = self._where.copy()
        clone._joins = copy.copy(self._joins)
        return clone

    def _get_rawqueryset(self):
        if self._rawqueryset is None:
            kwargs = {'select': self.fields}
            if self._where:
                kwargs['where'] = self._where
            if self._joins:
                kwargs['joins'] = [join(**j) for j in self._joins]

            # Import MoSQL's detabase specific fixes
            db = self._db or DEFAULT_DB_ALIAS
            vendor = connections[db].vendor
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

            raw_query = select(self.model._meta.db_table, **kwargs)
            self._rawqueryset = RawQuerySet(
                raw_query=raw_query, model=self.model, using=self._db
            )
        return self._rawqueryset

    def count(self):
        return len(list(self))

    def where(self, mapping):
        clone = self._clone()
        clone._where.update(mapping)
        return clone

    def join(self, model, alias, on=None, using=None, join_type=None):
        if isinstance(model, basestring):   # Try to lazy-load the model
            parts = model.split('.')
            if len(parts) == 2 and parts[0] and parts[1]:
                model = get_model(*parts)
        if issubclass(model, Model):
            table = model._meta.db_table
        else:
            table = model
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
        fields = [star] + [_as(*f) for f in extra_field_as]
        return MoQuerySet(model=self.model, fields=fields, using=self._db)
