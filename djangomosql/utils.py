#!/usr/bin/env python
# -*- coding: utf-8 -*-


class LazyString(object):
    def __init__(self, func):
        super(LazyString, self).__init__()
        self._func = func

    def __str__(self):
        value = self._func()
        return value

    def __getattr__(self, key):
        return getattr(str(self), key)
