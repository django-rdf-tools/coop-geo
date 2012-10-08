#!/usr/bin/env python
# -*- coding: utf-8 -*-

from django.core.exceptions import ValidationError
from django.utils.translation import ugettext as _

from chosen import widgets as chosenwidgets

import floppyforms as forms
import models
import widgets


class LocationForm(forms.ModelForm):
    class Meta:
        model = models.Location
        fields = ('label', 'adr1', 'adr2', 'zipcode', 'city', 'x_code', 'point', 'area')
        widgets = {
            'label': forms.TextInput(),
            'point': widgets.LocationPointWidget(),
            'area': forms.HiddenInput(),
        }

    def clean(self):
        cleaned_data = self.cleaned_data
        if not cleaned_data.get('point') and not cleaned_data.get('area'):
            raise ValidationError(u"You must at least set a point or choose "
                                  u"an area.")
        return cleaned_data


class AreaForm(forms.ModelForm):
    class Meta:
        model = models.Area
        fields = ('label', 'area_type', 'reference', 'polygon', 'update_auto',
                  'default_location',)
        widgets = {
            'label': forms.TextInput(),
            'polygon': widgets.PolygonWidget(),
            #'default_location': chosenwidgets.ChosenSelect()
        }


class AreaFormForInline(forms.ModelForm):
    class Meta:
        model = models.Located
        fields = ('location',)
        widgets = {
            'location': widgets.ChooseAreaWidget(),
        }

    def __init__(self, *args, **kwargs):
        super(AreaFormForInline, self).__init__(*args, **kwargs)
        associated_obj = self.fields['location']._associated_obj
        if associated_obj:
            self.fields['location'].widget = widgets.ChooseAreaWidget(
                        available_locations=[loc.location
                                    for loc in associated_obj.located.all()])
