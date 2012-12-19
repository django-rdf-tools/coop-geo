#!/usr/bin/env python
# -*- coding: utf-8 -*-

from django.core.exceptions import ValidationError
from django.utils.translation import ugettext as _
from django.db.models.loading import get_model

from chosen import widgets as chosenwidgets

import floppyforms as forms
import models
import widgets


class LocationForm(forms.ModelForm):
    class Meta:
        # model = models.Location
        model = get_model('coop_local', 'Location')

        fields = ('label', 'adr1', 'adr2', 'zipcode', 'city', 'x_code', 'point', 'area')
        widgets = {
            'label': forms.TextInput(),
            'point': widgets.LocationPointWidget(),
            'area': forms.HiddenInput(),
        }

    def clean(self):
        cleaned_data = self.cleaned_data
        if not cleaned_data.get('point') and not cleaned_data.get('area'):
            raise ValidationError(_(u"You must at least set a point or choose an area."))
        return cleaned_data


class AreaForm(forms.ModelForm):
    class Meta:
        # model = models.Area
        model = get_model('coop_local', 'Area')
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
        fields = ('location',)  # TODO ça fout le oaï que ça s'appelle location on comprend plus rien
        widgets = {
            'location': widgets.ChooseAreaWidget(),
        }

    def __init__(self, *args, **kwargs):
        super(AreaFormForInline, self).__init__(*args, **kwargs)
        if 'location' in self.fields:
            associated_obj = self.fields['location']._associated_obj
            if associated_obj and hasattr(associated_obj, 'located'):
                self.fields['location'].widget = widgets.ChooseAreaWidget(
                            available_locations=[loc.location
                                        for loc in associated_obj.located.all()])
