#!/usr/bin/env python
# -*- coding: utf-8

__all__ = ['Avg', 'Count', 'Min', 'Max', 'Stddev', 'Sum', 'Variance']

from mosql import func as _
from mosql.util import raw


class LazyStringGenerator(object):

    __class__ = raw

    def __init__(self, *args, **kwargs):
        super(LazyStringGenerator, self).__init__()
        self._args = args
        self._kwargs = kwargs

    def __str__(self):
        return self.function(*self._args, **self._kwargs)

    def __getattr__(self, key):
        return getattr(str(self), key)


class Avg(LazyStringGenerator):
    function = staticmethod(_.avg)


class Count(LazyStringGenerator):
    function = staticmethod(_.count)


class Min(LazyStringGenerator):
    function = staticmethod(_.min)


class Max(LazyStringGenerator):
    function = staticmethod(_.max)


class Stddev(LazyStringGenerator):
    function = staticmethod(_.stddev)


class Sum(LazyStringGenerator):
    function = staticmethod(_.sum)


class Variance(LazyStringGenerator):
    function = staticmethod(_.variance)
