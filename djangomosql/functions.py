#!/usr/bin/env python
# -*- coding: utf-8

__all__ = [
    'LazyFunction', 'Avg', 'Count', 'Min', 'Max', 'Stddev', 'Sum', 'Variance'
]

from . import _func as _


class LazyFunction(object):
    def __init__(self, func, *args):
        self._f = (func,)
        self._args = args

    def resolve(self):
        return self._f[0](*self._args)


class Avg(LazyFunction):
    def __init__(self, *args):
        super(Avg, self).__init__(_.avg, *args)


class Count(LazyFunction):
    def __init__(self, *args):
        super(Count, self).__init__(_.count, *args)


class Min(LazyFunction):
    def __init__(self, *args):
        super(Min, self).__init__(_.min, *args)


class Max(LazyFunction):
    def __init__(self, *args):
        super(Max, self).__init__(_.max, *args)


class Stddev(LazyFunction):
    def __init__(self, *args):
        super(Stddev, self).__init__(_.stddev, *args)


class Sum(LazyFunction):
    def __init__(self, *args):
        super(Sum, self).__init__(_.sum, *args)


class Variance(LazyFunction):
    def __init__(self, *args):
        super(Variance, self).__init__(_.variance, *args)
