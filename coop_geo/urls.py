#!/usr/bin/env python
# -*- coding:utf-8 -*-
from django.conf.urls.defaults import *
#from django.conf.urls.defaults import patterns, url
from django.contrib.auth.decorators import permission_required

from views import JSONLocationView, JSONAreaView, SimpleAreaView

urlpatterns = patterns('',
    url(r'^location/json/(?P<city>\w+)/(?P<address>\w.*)?$',
     permission_required('coop_geo.add_location')(JSONLocationView.as_view()),
     name='json_location'),
    url(r'^area/simple/?$',
     permission_required('coop_geo.add_arealink')(SimpleAreaView.as_view()),
     name='simple_area'),
    url(r'^area/json/?$',
     permission_required('coop_geo.add_arealink')(JSONAreaView.as_view()),
     name='json_area_pk'),
)
