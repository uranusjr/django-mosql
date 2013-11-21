#!/usr/bin/env python
# -*- coding: utf-8 -*-

from django.contrib import admin
from .models import Department, Employee, FruitProduct


admin.site.register(Department)
admin.site.register(Employee)
admin.site.register(FruitProduct)
