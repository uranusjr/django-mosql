#!/usr/bin/env python
# -*- coding: utf-8 -*-

from django.utils import six


class LazyString(object):

    __class__ = six.text_type

    def __init__(self, func):
        super(LazyString, self).__init__()
        self._func = func

    def __unicode__(self):
        return self._func()

    def __str__(self):
        return self._func()

    def __iter__(self):
        return iter(self.__class__(self))

    def __len__(self):
        return len(self.__class__(self))

    def __getitem__(self, k):
        return self.__class__(self)[k]

    def __getattr__(self, key):
        return getattr(self.__class__(self), key)

    def __add__(self, other):
        return self.__class__(self) + other
