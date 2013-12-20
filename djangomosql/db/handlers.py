#!/usr/bin/env python
# -*- coding: utf-8

from __future__ import unicode_literals
import logging
from django.db import connections
from django.db.models.query import RawQuerySet
from django.db.utils import DEFAULT_DB_ALIAS
from mosql.util import raw, paren, identifier
from .patch import patch_map, Patcher


logger = logging.getLogger(__name__)


class EngineHandler(object):
    """A base implementation for database engine handlers.

    This class provides an interface for accessing engine-specific values,
    implements methods for overriding when a task requires different query
    syntaxes between different engines, and allows runtime monkey-patching
    when invoking MoSQL query generation functions. In cases where different
    databases require different syntaxes, this class provides an implementation
    that conforms to the SQL stadard.
    """
    def __init__(self, connection, vendor):
        super(EngineHandler, self).__init__()
        self.connection = connection
        self.name = vendor
        self.patch_dict = patch_map.get(vendor, {})

    def __repr__(self):
        return '<EngineHandler: {name}>'.format(name=self.name)

    def patch(self):
        """Gets a patcher object for MoSQL monkey-patching

        Usage::

            with handler.patch():
                # MoSQL queries here will be patched
        """
        return Patcher(self.patch_dict)

    def no_limit_value(self):
        """Gets the ``no_limit_value`` for the backend

        Simply calls ``connection.ops.no_limit_value``.
        """
        return self.connection.ops.no_limit_value()

    def cursor(self):
        """Gets a cursor for the current connection

        Useful when you need to execute some raw SQLs directly.
        """
        return self.connection.cursor()

    def get_where_for_delete(self, queryset):
        """Generates a mapping to be used as the ``where`` parameter for a
           ``DELETE`` query

        Used when ``mosql.query.delete`` is called. This implementation simply
        generate a ``SELECT`` subquery so that the ``WHERE`` clause will be
        of form ``<primary key> IN (<subquery>)``.
        """
        pkcol = queryset.model._meta.pk.get_attname_column()[1]
        key = '{pkcol} IN'.format(pkcol=pkcol)
        value = raw(paren(queryset._get_select_query([pkcol])))
        return {key: value}

    def get_star(self, queryset):
        """Generates a ``<table_name>.*`` representation

        :rtype: :class:`mosql.util.raw`
        """
        table = queryset._params['alias'] or queryset.model._meta.db_table
        return [raw('{table}.*'.format(table=identifier(table)))]

    def get_aggregated_columns_for_group_by(self, queryset, aggregate):
        """Generates a sequence of fully-qualified column names

        This is used in an aggregated query, when :method:`get_star` cannot be
        used safety without ambiguity. Values for each field in the model are
        calculated by a SQL function specified by ``aggregate``, and then
        injected (using ``AS``) back into the fields.

        :param: aggregate: The SQL function to be used for aggregation.
        :type aggregate: str
        :returns: A sequence of fully qualified ``SELECT`` identifiers.
        """
        table = queryset._params['alias'] or queryset.model._meta.db_table
        return [
            raw('{func}({table}.{field}) AS {field}'.format(
                func=aggregate, table=identifier(table),
                field=identifier(field.get_attname_column()[1])))
            for field in queryset.model._meta.fields
        ]


class postgresql(EngineHandler):
    """PostgreSQL Handler

    Basically a no-op class since PostgreSQL conforms to the SQL standard for
    the most part.
    """
    pass


class mysql(EngineHandler):
    """MySQL Handler"""
    def get_where_for_delete(self, queryset):
        """Re-implemented from :class:`EngineHandler`

        MySQL does not support ``SELECT`` subqueries on the taget table inside
        a ``DELETE`` query. Ths implementation performs an extra ``SELECT`` to
        get a list of primary keys so that the ``DELETE`` query can be formed
        correctly.
        """
        pkname, pkcol = queryset.model._meta.pk.get_attname_column()
        key = '{pkcol} IN'.format(pkcol=pkcol)
        subqueryset = RawQuerySet(
            raw_query=queryset._get_select_query([pkcol]),
            model=queryset.model, using=queryset._db
        )
        value = [getattr(obj, pkname) for obj in subqueryset]
        return {key: value}


class sqlite(EngineHandler):
    """SQLite Handler"""
    def get_aggregated_columns_for_group_by(self, queryset, aggregate):
        """Re-implemented from :class:`EngineHandler`

        SQLite does not support SQL aggregate functions with ``GROUP BY``. This
        implementation simply calls :method:`EngineHandler.get_star` instead.
        """
        # Aggregation does not work with GROUP BY for SQLite. Give up lamely.
        return self.get_star(queryset)


def get_engine_handler(database=None):
    """Initialize an :class:`EngineHandler`-subclass instance of correct type

    This function inspects the settings in your Django project to determine
    the correct handler type, instantiates an instance of that type, and
    returns it.

    :param database: Name of the database. This should be one of the top-level
        keys in your ``DATABASES`` setting. Can be obtained from a model
        instance by its ``_db`` attribute.
    """
    try:
        connection = connections[database or DEFAULT_DB_ALIAS]
    except KeyError:            # pragma: no cover
        connection = connections[DEFAULT_DB_ALIAS]
    vendor = connection.vendor
    handler_class = globals().get(vendor)
    if handler_class is None:   # pragma: no cover
        msg = (
            'Current database ({vendor}) not supported by MoSQL. '
            'Will generate standard SQL instead.'
        ).format(vendor=vendor)
        logger.warning(msg)
        handler_class = EngineHandler
    return handler_class(connection, vendor)
