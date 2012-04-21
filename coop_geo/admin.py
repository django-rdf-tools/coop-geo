#!/usr/bin/env python
# -*- coding: utf-8 -*-

from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from coop.utils.autocomplete_admin import InlineAutocompleteAdmin


import models
import forms


class LocationAdmin(admin.ModelAdmin):
    list_display = ['label', 'adr1', 'adr2', 'zipcode', 'city', 'has_point']
    search_fields = ['label', 'adr1', 'adr2', 'zipcode', 'city']
    form = forms.LocationForm
admin.site.register(models.Location, LocationAdmin)


class AreaTypeAdmin(admin.ModelAdmin):
    list_display = ['label', ]
admin.site.register(models.AreaType, AreaTypeAdmin)


class AreaParentRelInline(admin.TabularInline):
    model = models.AreaRelations
    verbose_name = _(u"Included area")
    verbose_name_plural = _(u"Included areas")
    extra = 1
    fk_name = 'child'


class AreaChildRelInline(InlineAutocompleteAdmin):
    model = models.AreaRelations
    verbose_name = _(u"Inside area")
    verbose_name_plural = _(u"Inside areas")
    #related_search_fields = {'child': ('label', 'reference'), }
    extra = 1
    fk_name = 'parent'


class AreaAdmin(admin.ModelAdmin):
    list_display = ['label', 'reference', 'area_type', ]
    list_filter = ['area_type',]
    search_fields = ['label', 'reference']
    model = models.Area
    form = forms.AreaForm
    inlines = [AreaChildRelInline]
admin.site.register(models.Area, AreaAdmin)

