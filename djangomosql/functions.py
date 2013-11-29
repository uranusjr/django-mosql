#!/usr/bin/env python
# -*- coding: utf-8

__all__ = [
    'LazyFunction', 'Avg', 'Count', 'Min', 'Max', 'Stddev', 'Sum', 'Variance'
]

from . import _func as _


class LazyFunction(object):
    def __init__(self, *args):
        self._args = args

    def resolve(self):
        return self.function(*self._args)


class Avg(LazyFunction):
    function = staticmethod(_.avg)


class Count(LazyFunction):
    function = staticmethod(_.count)


class Min(LazyFunction):
    function = staticmethod(_.min)


class Max(LazyFunction):
    function = staticmethod(_.max)


class Stddev(LazyFunction):
    function = staticmethod(_.stddev)


class Sum(LazyFunction):
    function = staticmethod(_.sum)


class Variance(LazyFunction):
    function = staticmethod(_.variance)
