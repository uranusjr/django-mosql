#!/usr/bin/env python
# -*- coding: utf-8 -*-

from django.db.models.manager import Manager
from django.db.models.query import RawQuerySet
from mosql.query import select
try:
    basestring
except NameError:   # If basestring is not a thing, just alias it to str
    basestring = str


class MoQuerySet(object):
    """Django query set subclass with MoSQL bridging"""

    def __init__(self, model=None, using=None):
        self.model = model
        self._db = using
        self.raw_query_set = None
        self.where = {}

    def __iter__(self):
        """Iterate through the queryset using the backed RawQuerySet"""
        if self.raw_query_set is None:
            raw_query = self.get_raw_query()
            self.raw_query_set = RawQuerySet(
                raw_query=raw_query, model=self.model, using=self._db
            )
        return self.raw_query_set.__iter__()

    def __getitem__(self, k):
        return list(self)[k]

    def _clone(self):
        clone = MoQuerySet(self.model, self._db)
        clone.where = self.where
        return clone

    def count(self):
        return len(list(self))

    def get_raw_query(self):
        """Invoke mosql.query.select to generate the raw query"""
        where = self.where_mapping or None
        return select(self.model._meta.db_table, where=where)

    def where(self, mapping):
        clone = self._clone()
        clone.where.update(mapping)
        return clone


class MoManager(Manager):
    """Django model manager subclass with MoSQL bridging"""

    def select(self):
        return MoQuerySet(model=self.model, using=self._db)
