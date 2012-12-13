#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Command to import areas from a shapefile.
'''

import os
from optparse import make_option
import sys
import tempfile
import zipfile
from django.core.management.base import BaseCommand, CommandError
from django.contrib.gis.gdal import DataSource
from django.contrib.gis.geos import MultiPolygon

from coop_geo import models

class Command(BaseCommand):
    '''
    Command to import areas from a shapefile.
    '''
    args = '<zipped_shapefile> <areatype_idx> [<name_col> <reference_col>]'
    help = 'Import areas from a shapefile.\n\n"areatype_idx" is the textual '\
           'index of the area type. If this area type doesn\'t exist it is '\
           'created.\n"name_col" and "reference_col" are the columns to use '\
           'in the shapefile data respectively for the name and the '\
           'reference.\n\nCreation and update are managed. '\
           'Update is managed according to the reference_col and the area type.'
    option_list = BaseCommand.option_list + (
        make_option('-q', '--quiet',
            action="store_true",
            dest="quiet", default=False,
            help="no output"),
        make_option('-l', '--list',
            action="store_true",
            dest="list", default=False,
            help="list available columns in the shapefile"),
        )

    def handle(self, *args, **options):
        quiet = 'quiet' in options and options['quiet']
        list_columns = 'list' in options and options['list']
        if not args or len(args) < 1 or (not list_columns and len(args) < 2):
            raise CommandError(u"Args missing")
        zipped_shapefile = args[0]
        areatype_idx = args[1] if len(args) > 1 else ''
        name_col = args[2] if len(args) > 2 else ''
        reference_col = args[3] if len(args) > 3 else ''

        areatype = None
        if areatype_idx:
            areatype, created = models.AreaType.objects.get_or_create(
                                    txt_idx=areatype_idx,
                                    defaults={
                                        'label': areatype_idx.replace('-', ' '
                                                            ).replace('_', ' '
                                                            ).capitalize()
                                    })

        # open zipfile
        try:
            flz = zipfile.ZipFile(zipped_shapefile)
        except zipfile.BadZipfile:
            raise CommandError(u"Bad zip file")
        tmpdir = tempfile.mkdtemp()
        prjfilename = None
        shpfilename = None
        for filename in flz.namelist():
            flz.extract(filename, tmpdir)
            full_name = os.sep.join([tmpdir, filename])
            if filename.endswith('.prj'):
                prjfilename = full_name
            elif filename.endswith('.shp'):
                shpfilename = full_name
        srid = None
        if prjfilename:
            try:
                from osgeo import osr
                with open(prjfilename, 'r') as prj_file:
                    prj_txt = prj_file.read()
                    srs = osr.SpatialReference()
                    srs.ImportFromESRI([prj_txt])
                    srs.AutoIdentifyEPSG()
                    srid = srs.GetAuthorityCode(None)
            except ImportError:
                srid = 4326
                if not quiet and not list_columns:
                    self.stdout.write('WARN: module gdal is not installed. SRID'
                        ' cannot be read from proj\n      file. Default to '
                        'WGS84 projection (latitude/longitude).\n')
        datasource = DataSource(shpfilename)
        lyr = datasource[0]
        if list_columns:
            self.stdout.write('Available columns in this shapefile are: %s\n' %
                              ", ".join(lyr.fields))
            sys.exit(0)
        name_idx, reference_idx = None, None
        if name_col or reference_col:
            for idx, name in enumerate(lyr.fields):
                if name == name_col:
                    name_idx = idx
                if name == reference_col:
                    reference_idx = idx
        if name_col and name_idx == None:
            raise CommandError(u'"%s" is not a valid column name. Available '
                     u'column are: %s.' % (name_col, ", ".join(lyr.fields)))
        if reference_col and reference_idx == None:
            raise CommandError(u'"%s" is not a valid column name. Available '
                    u'column are: %s.' % (reference_col, ", ".join(lyr.fields)))
        if reference_idx == None:
            reference_col = lyr.fields[0]
        if name_idx == None:
            name_col = lyr.fields[1]
        created_nb, updated_nb = 0, 0
        for feat in lyr:
            geom = None
            if feat.geom.geom_type == 'MultiPolygon':
                geom = feat.geom
            elif feat.geom.geom_type == 'Polygon':
                geom = MultiPolygon(feat.geom.geos)
            else:
                continue
            values = {'polygon':'SRID=%s;%s' % (srid, geom.wkt),
                      'label':feat.get(name_col).decode('iso-8859-15')}
            area, created = models.Area.objects.get_or_create(
                    area_type=areatype,
                    reference=feat.get(reference_col).decode('iso-8859-15'),
                    defaults=values)
            if not created:
                area.polygon = values['polygon']
                area.save()
                updated_nb += 1
            else:
                created_nb += 1
        if not quiet:
            self.stdout.write('Import done:\n * %d items created\n '
                          '* %d items updated\n' % (created_nb, updated_nb))


"""

http://www.fao.org/countryprofiles/geoinfo/ws/allCountries/FR/

import elementtree.ElementTree as ET
tree = ET.parse("country_names.xml")

for el in tree.findall('self_governing'):
    name_fr = el.find('nameListFR').text
    iso = el.find('codeISO3').text
    if Area.objects.filter(reference=iso).exists():
        a = Area.objects.get(reference=iso)
        a.label = name_fr
        a.save()


"""