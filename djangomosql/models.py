#!/usr/bin/env python
# -*- coding: utf-8 -*-

import copy
from django.db.models import Model, Manager, get_model
from django.db.models.query import RawQuerySet
from mosql.query import select, join
try:
    basestring
except NameError:   # If basestring is not a thing, just alias it to str
    basestring = str


class MoQuerySet(object):
    """Django query set subclass with MoSQL bridging"""

    def __init__(self, model=None, using=None):
        self.model = model
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
        clone = MoQuerySet(model=self.model, using=self._db)
        clone._where = self._where.copy()
        clone._joins = copy.copy(self._joins)
        return clone

    def _get_rawqueryset(self):
        if self._rawqueryset is None:
            kwargs = {}
            if self._where:
                kwargs['where'] = self._where
            if self._joins:
                kwargs['joins'] = [join(*j) for j in self._joins]
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

    def join(self, model, as_, on=None, using=None, join_type=None):
        if isinstance(model, basestring):   # Try to lazy-load the model
            parts = model.split('.')
            if len(parts) == 2 and parts[0] and parts[1]:
                model = get_model(*parts)
        if issubclass(model, Model):
            table = model._meta.db_table
        else:
            table = model
        clone = self._clone()
        clone._joins.append({
            'table': table, 'on': on, 'using': using,
            'type': join_type or ''
        })
        return clone


class MoManager(Manager):
    """Django model manager subclass with MoSQL bridging"""

    def select(self):
        return MoQuerySet(model=self.model, using=self._db)
