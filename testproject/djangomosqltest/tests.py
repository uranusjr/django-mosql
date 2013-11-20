#!/usr/bin/env python
# -*- coding: utf-8 -*-

from django_nose import FastFixtureTestCase as TestCase
from nose.tools import ok_, eq_, assert_not_equal
from .models import Employee, Department


class DjangoMoSQLTests(TestCase):

    fixtures = ['employees.json']

    def test_count(self):
        eq_(Employee.objects.count(), 2)

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
