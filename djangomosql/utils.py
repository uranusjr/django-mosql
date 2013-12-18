#!/usr/bin/env python
# -*- coding: utf-8 -*-


class LazyString(object):

    __class__ = str

    def __init__(self, func):
        super(LazyString, self).__init__()
        self._func = func

    def __str__(self):
        return self._func()

    def __iter__(self):
        return iter(str(self))

    def __len__(self):
        return len(str(self))

    def __getitem__(self, k):
        return str(self)[k]

    def __getattr__(self, key):
        return getattr(str(self), key)
