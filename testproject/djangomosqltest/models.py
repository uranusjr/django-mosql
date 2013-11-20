#!/usr/bin/env python
# -*- coding: utf-8 -*-

from django.db import models
from django.utils.translation import ugettext_lazy as _
from djangomosql.models import MoManager


class Department(models.Model):
    name = models.CharField(max_length=50)

    objects = MoManager()

    class Meta(object):
        verbose_name = _('Department')
        verbose_name_plural = _('Departments')

    def __unicode__(self):
        return _('Department %s') % (self.name,)


class Employee(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    department = models.ForeignKey(Department, blank=True, null=True)

    objects = MoManager()

    class Meta(object):
        verbose_name = _('Employee')
        verbose_name_plural = _('Employees')

    def __unicode__(self):
        return _('Employee %s %s') % (self.first_name, self.last_name)
