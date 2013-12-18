#!/usr/bin/env python
# -*- coding: utf-8

from mosql import util

# Backup things in util
backup = {k: getattr(util, k) for k in dir(util)}

# Load patches
import mosql.mysql
import mosql.sqlite

# Restore backup
for k in backup:
    setattr(util, k, backup[k])


class EnginePatcher(object):
    """This class implements the context manager interface for syntax patching.
    """
    def __init__(self, patches):
        """Initialize a :class:`EnginePatcher` object.

        :param patches: a mapping of members to be patched
        :type patches: `dict`
        """
        self._backup = {}
        self._patches = patches

    def __enter__(self):
        for k in backup:
            self._backup[k] = getattr(mosql.util, k)
            setattr(mosql.util, k, self._patches.get(k, backup[k]))
        return self._backup

    def __exit__(self, exc_type, exc_val, exc_tb):
        while self._backup:
            k, v = self._backup.popitem()
            setattr(mosql.util, k, v)


def mysql():
    patches = {
        'escape': mosql.mysql.fast_escape,
        'format_param': mosql.mysql.format_param,
        'delimit_identifier': mosql.mysql.delimit_identifier,
        'escape_identifier': mosql.mysql.escape_identifier
    }
    return EnginePatcher(patches)


def sqlite():
    return EnginePatcher({'format_param': mosql.sqlite.format_param})
