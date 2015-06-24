#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Polyfills for get_model migration during Django 1.8.
try:
    from django.apps import apps
    get_model = apps.get_model
except ImportError:
    from django.db.models.loading import get_model  # noqa
