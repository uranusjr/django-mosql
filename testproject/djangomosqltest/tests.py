#!/usr/bin/env python
# -*- coding: utf-8 -*-

from django.db import connections
from django.db.utils import DEFAULT_DB_ALIAS
from django_nose import FastFixtureTestCase as TestCase
from nose.tools import ok_, eq_, assert_not_equal, assert_false, assert_raises
from djangomosql.functions import Min
from .models import Employee, Department, FruitProduct
try:
    basestring
except NameError:   # If basestring is not a thing, just alias it to str
    basestring = str


class EmployeeMoSQLTests(TestCase):

    fixtures = ['employees.json']

    def test_count(self):
        eq_(Employee.objects.count(), 2)

    def test_clone(self):
        people = Employee.objects.select().where({'first_name': 'Mosky'})
        clone = people._clone()
        eq_(dir(clone), dir(people))
        eq_(clone._params.keys(), people._params.keys())
        for k in people._params:
            eq_(people._params[k], clone._params[k])
            if (not isinstance(people._params[k], (int, basestring))
                    and people._params[k] is not None):
                assert_false(people._params[k] is clone._params[k])

    def test_select(self):
        people = Employee.objects.select()
        assert_not_equal(people.count(), 0)
        for p in people:
            ok_(p.first_name)
            ok_(p.last_name)

    def test_where(self):
        people = Employee.objects.select().where({'first_name': 'Mosky'})
        eq_(people.count(), 1)
        eq_(people[0].first_name, 'Mosky')
        eq_(people[0].last_name, 'Liu')
        eq_(people[0].department, None)

        people = people.where({'last_name': 'Lin'})
        eq_(people.count(), 0)

    def test_join(self):
        people = Employee.objects.select(('d.name', 'department_name')).join(
            Department, 'd', on={'department_id': 'd.id'})
        for p in people:
            ok_(hasattr(p, 'department_name'))


# Tests in this class originates from
# http://www.xaprb.com/blog/2006/12/07/how-to-select-the-firstleastmax-row-per-group-in-sql/
class FruitMoSQLTests(TestCase):

    fixtures = ['fruits.json']

    def test_slice(self):
        all_products = FruitProduct.objects.select()
        eq_(all_products[1:].count(), 8)
        eq_(all_products[1:7].count(), 6)
        eq_(all_products[1:7][2:4].count(), 2)
        eq_(all_products.count(), 9)

    def test_order_by(self):
        all_products = FruitProduct.objects.select()

        products = all_products.order_by('price')
        previous = float('-inf')
        for p in products:
            ok_(p.price >= previous)
            previous = p.price

        products = all_products.order_by('-price')
        previous = previous = float('inf')
        for p in products:
            ok_(p.price <= previous)
            previous = p.price

        products = all_products.order_by('price ASC')
        previous = previous = float('-inf')
        for p in products:
            ok_(p.price >= previous)
            previous = p.price

        products = all_products.order_by('price DESC')
        previous = previous = float('inf')
        for p in products:
            ok_(p.price <= previous)
            previous = p.price

        with assert_raises(SyntaxError):
            FruitProduct.objects.select().order_by('price kind')

        with assert_raises(SyntaxError):
            FruitProduct.objects.select().order_by('price kind variety')

    def test_group_by(self):
        products = (
            FruitProduct.objects
                        .select((Min('price'), 'minprice'))
                        .group_by('kind')
                        .order_by('kind')
        )
        eq_((products[0].kind, products[0].minprice), ('apple', 0.24))
        eq_((products[1].kind, products[1].minprice), ('cherry', 2.55))
        eq_((products[2].kind, products[2].minprice), ('orange', 3.59))
        eq_((products[3].kind, products[3].minprice), ('pear', 2.14))

    def test_as(self):
        products = FruitProduct.objects.select().as_('f')
        conn = connections[FruitProduct.objects._db or DEFAULT_DB_ALIAS]
        expect = 'SELECT "f".* FROM "djangomosqltest_fruitproduct" AS "f"'
        if conn.vendor == 'mysql':
            expect = 'SELECT `f`.* FROM `djangomosqltest_fruitproduct` AS `f`'
        eq_(products.query, expect)

    def test_subquery(self):
        m = FruitProduct.objects
        inner = m.select((Min('price'), 'minprice')).group_by('kind')
        p = m.select().as_('f').order_by('f.kind').join(
            inner, 'x', on={'f.kind': 'x.kind', 'f.price': 'x.minprice'}
        )

        def to_tuple(obj):
            return (obj.kind, obj.variety, obj.price)

        eq_(to_tuple(p[0]), ('apple', 'fuji', 0.24))
        eq_(to_tuple(p[1]), ('cherry', 'bing', 2.55))
        eq_(to_tuple(p[2]), ('orange', 'valencia', 3.59))
        eq_(to_tuple(p[3]), ('pear', 'bartlett', 2.14))
