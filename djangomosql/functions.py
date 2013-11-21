#!/usr/bin/env python
# -*- coding: utf-8

"""Implements MoSQL convinience functions until they go into master.
"""

__all__ = ['Avg', 'Count', 'Min', 'Max', 'Stddev', 'Sum', 'Variance']

from mosql.util import raw, concat_by_comma, identifier


def _make_simple_function(name):

    def simple_function(*args):
        return raw('%s(%s)' % (
            name.upper(),
            concat_by_comma(identifier(x) for x in args)
        ))

    return simple_function


Avg = _make_simple_function('AVG')
Count = _make_simple_function('COUNT')
Min = _make_simple_function('MIN')
Max = _make_simple_function('MAX')
Stddev = _make_simple_function('STDDEV')
Sum = _make_simple_function('SUM')
Variance = _make_simple_function('VARIANCE')
