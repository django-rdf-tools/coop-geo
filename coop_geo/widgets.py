#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re

from django.conf import settings
from django.contrib.gis.geos import GEOSGeometry
from django.utils import translation
from django.utils.safestring import mark_safe
from django.core.exceptions import ObjectDoesNotExist

from coop.utils.autocomplete_admin import FkSearchInput

import floppyforms.gis as ff_gis

from models import Area, AreaType, AreaLink, Location


class LocationPointWidget(ff_gis.PointWidget, ff_gis.BaseOsmWidget):
    template_name = 'gis/osm_location.html'
    map_width = 400
    point_zoom = 18
    geocode_region = settings.COOP_GEO_REGION
    geocode_bounding = settings.COOP_GEO_BOUNDING_BOX


    class Media:
        extend = False
        js = ('http://maps.google.com/maps/api/js?sensor=false',
              'js/OpenLayers.js',
              'js/OpenStreetMap.js',
              'js/MapWidget.js',)
        css = {'all': ['css/smoothness/jquery-ui-1.8.14.custom.css', # on l'a déjà aussi dans Bootstrap --> if...
                       'css/openlayers.css']}

    map_attrs = list(ff_gis.BaseOsmWidget.map_attrs) + \
                ['geocode_region', 'geocode_bounding', 'point_zoom']

    # def get_context_data(self):
    #     context = super(LocationPointWidget, self).get_context_data()
    #     context['areas'] = Area.get_all()
    #     return context


class ChooseLocationWidget(ff_gis.PointWidget, ff_gis.BaseOsmWidget):
    template_name = 'gis/osm_choose_location.html'
    map_width = 400
    point_zoom = 18
    geocode_region = settings.COOP_GEO_REGION
    geocode_bounding = settings.COOP_GEO_BOUNDING_BOX

    class Media:
        extend = False
        js = (#'js/jquery-1.6.2.min.js',
              #'js/jquery-ui-1.8.14.custom.min.js',
              'http://maps.google.com/maps/api/js?sensor=false',
              #'http://openlayers.org/api/2.10/OpenLayers.js',
              'js/OpenLayers.js',
              'js/OpenStreetMap.js',
              'js/MapWidget.js',)
        css = {'all': ['css/smoothness/jquery-ui-1.8.14.custom.css',
                       'css/openlayers.css']}

    map_attrs = list(ff_gis.BaseOsmWidget.map_attrs) + \
                ['geocode_region', 'geocode_bounding', 'point_zoom']

    def __init__(self, user, *args, **kwargs):
        self.user = user
        return super(ChooseLocationWidget, self).__init__(*args, **kwargs)

    def get_context(self, name, value, attrs=None, extra_context={}):
        # Defaulting the WKT value to a blank string
        wkt, location = '', None
        if value:
            try:
                location = Location.objects.get(pk=int(value))
                wkt = location.point.wkt
            except ObjectDoesNotExist:
                pass
        context = super(ChooseLocationWidget, self).get_context(name, wkt,
                                                                attrs)
        context['location'] = ""
        if location:
            context['location'] = unicode(location)
        context['attrs']['value'] = wkt
        context['module'] = 'map_%s' % name.replace('-', '_')
        context['name'] = name
        context['ADMIN_MEDIA_PREFIX'] = settings.ADMIN_MEDIA_PREFIX
        context['LANGUAGE_BIDI'] = translation.get_language_bidi()
        return context

    def get_context_data(self):
        context = super(ChooseLocationWidget, self).get_context_data()
        #context['locations'] = Location.get_all(self.user)
        return context


class PolygonWidget(ff_gis.MultiPolygonWidget, ff_gis.BaseOsmWidget):
    template_name = 'gis/osm.html'
    map_width = 400
    areas = Area.get_all()


class ChooseAreaWidget(ff_gis.MultiPolygonWidget, ff_gis.BaseOsmWidget):
    template_name = 'gis/osm_choose_inline_area.html'
    map_width = 400
    point_zoom = 18

    class Media:
        extend = False
        js = (
            'js/OpenLayers.js',
            'http://www.openstreetmap.org/openlayers/OpenStreetMap.js',
            'floppyforms/js/MapWidget.js',
        )
        css = {'all': ['css/coop_geo.css',
                       'css/openlayers.css']}

    def __init__(self, available_locations=None):
        self.available_locations = available_locations
        super(ChooseAreaWidget, self).__init__()

    def get_context(self, name, value, attrs=None, extra_context={}):
        # Defaulting the WKT value
        wkt, location = '', None
        if value:
            try:
                location = Area.objects.get(pk=int(value))
                wkt = location.polygon.wkt
            except ObjectDoesNotExist:
                pass
        context = super(ChooseAreaWidget, self).get_context(name, wkt,
                                                            attrs)
        context['location'] = ""
        context['value_pk'] = ""
        if location:
            context['location'] = unicode(location)
            context['value_pk'] = location.pk
        context['wkt'] = wkt
        context['parent_table_name'] = '-'.join(name.split('-')[:-2] + ['group'])
        context['module'] = 'map_%s' % name.replace('-', '_')
        context['name'] = name
        context['ADMIN_MEDIA_PREFIX'] = settings.ADMIN_MEDIA_PREFIX
        context['LANGUAGE_BIDI'] = translation.get_language_bidi()
        context['area_types'] = AreaType.objects.exclude(txt_idx='circle').all()
        context['available_locations'] = self.available_locations
        return context

    def value_from_datadict(self, data, files, name):
        area_pk = data.get('id_' + name + '_area_pk')
        area_wkt = data.get('id_' + name + '_area_wkt')
        area_location = data.get('id_' + name + '_location')
        # not clean but no other simple way to implement it
        if area_wkt and area_location:
            # treatment of a circle
            # it is a multi-polygon not a simple polygon: manualy fix it
            r = re.compile('POLYGON')
            area_wkt = r.sub('MULTIPOLYGON(', area_wkt) + ')'

            area_type, created = AreaType.objects.get_or_create(
                                        txt_idx='circle',
                                        defaults={'label': "Circle"})
            default_location = None
            if area_location:
                try:
                    default_location = Location.objects.get(pk=area_location)
                except:
                    return
            lbl = u"Rayon d'action - " + default_location.label
            values = {'label': lbl[:150], 'default_location': default_location,
                      'area_type': area_type, 'polygon': GEOSGeometry(area_wkt)}
            area = None
            if area_pk:
                try:
                    area = Area.objects.get(pk=area_pk)
                except:
                    return
                for attr in values:
                    setattr(area, attr, values[attr])
                area.save()
            else:
                area, created = Area.objects.get_or_create(**values)
            return area.pk
        elif area_pk:
            return area_pk
        return None

