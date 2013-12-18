#!/usr/bin/env python
# -*- coding: utf-8

__all__ = ['Avg', 'Count', 'Min', 'Max', 'Stddev', 'Sum', 'Variance']

from mosql import func as _
from mosql.util import raw
from .utils import LazyString


class LazyValueGenerator(LazyString):

    __class__ = raw

    def __init__(self, *args, **kwargs):
        super(LazyValueGenerator, self).__init__(
            lambda: self.function(*args, **kwargs)
        )


class Avg(LazyValueGenerator):
    function = staticmethod(_.avg)


class Count(LazyValueGenerator):
    function = staticmethod(_.count)


class Min(LazyValueGenerator):
    function = staticmethod(_.min)


class Max(LazyValueGenerator):
    function = staticmethod(_.max)


class Stddev(LazyValueGenerator):
    function = staticmethod(_.stddev)


class Sum(LazyValueGenerator):
    function = staticmethod(_.sum)


class Variance(LazyValueGenerator):
    function = staticmethod(_.variance)
