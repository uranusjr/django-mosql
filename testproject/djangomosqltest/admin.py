#!/usr/bin/env python
# -*- coding: utf-8 -*-

from django.contrib import admin
from .models import Department, Employee


admin.site.register(Department)
admin.site.register(Employee)
