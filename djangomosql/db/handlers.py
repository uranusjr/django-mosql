#!/usr/bin/env python
# -*- coding: utf-8

import logging
from django.db import connections
from django.db.models.query import RawQuerySet
from django.db.utils import DEFAULT_DB_ALIAS
from mosql.util import raw, paren, identifier
from .utils import patch_map, Patcher


logger = logging.getLogger(__name__)


class EngineHandler(object):
    def __init__(self, connection, vendor):
        super(EngineHandler, self).__init__()
        self.connection = connection
        self.name = vendor
        self.patch_dict = patch_map.get(vendor, {})

    def __repr__(self):
        return '<EngineHandler: {name}>'.format(name=self.name)

    def patch(self):
        return Patcher(self.patch_dict)

    def no_limit_value(self):
        return self.connection.ops.no_limit_value()

    def cursor(self):
        return self.connection.cursor()

    def get_where_for_delete(self, queryset):
        pkcol = queryset.model._meta.pk.get_attname_column()[1]
        key = '{pkcol} IN'.format(pkcol=pkcol)
        value = raw(paren(queryset._get_select_query([pkcol])))
        return {key: value}

    def get_star(self, queryset):
        table = queryset._params['alias'] or queryset.model._meta.db_table
        return [raw('{table}.*'.format(table=identifier(table)))]

    def get_aggregated_columns_for_group_by(self, queryset, aggregate):
        table = queryset._params['alias'] or queryset.model._meta.db_table
        return [
            raw('{func}({table}.{field}) AS {field}'.format(
                func=aggregate, table=identifier(table),
                field=identifier(field.get_attname_column()[1])))
            for field in queryset.model._meta.fields
        ]


class postgresql(EngineHandler):
    pass


class mysql(EngineHandler):
    def get_where_for_delete(self, queryset):
        pkname, pkcol = queryset.model._meta.pk.get_attname_column()
        key = '{pkcol} IN'.format(pkcol=pkcol)
        subqueryset = RawQuerySet(
            raw_query=queryset._get_select_query([pkcol]),
            model=queryset.model, using=queryset._db
        )
        value = [getattr(obj, pkname) for obj in subqueryset]
        return {key: value}


class sqlite(EngineHandler):
    def get_aggregated_columns_for_group_by(self, queryset, aggregate):
        # Aggregation does not work with GROUP BY for SQLite. Give up lamely.
        return self.get_star(queryset)


def get_engine_handler(database=None):
    connection = connections[database or DEFAULT_DB_ALIAS]
    vendor = connection.vendor
    handler_class = globals().get(vendor)
    if handler_class is None:
        msg = (
            'Current database ({vendor}) not supported by MoSQL. '
            'Will generate standard SQL instead.'
        ).format(vendor=vendor)
        logger.warning(msg)
        handler_class = EngineHandler
    return handler_class(connection, vendor)
