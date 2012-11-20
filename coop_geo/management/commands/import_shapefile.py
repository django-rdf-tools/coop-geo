#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import tempfile
import sys
import zipfile
from django.core.management.base import BaseCommand, CommandError
from django.contrib.gis.gdal import DataSource
from django.contrib.gis.geos import MultiPolygon, Polygon

from coop_geo import models

class Command(BaseCommand):
    args = '<zipped_shapefile> <areatype_idx> [<name_col> <reference_col>]'
    help = 'Import area from a shapefile'

    def handle(self, *args, **options):
        if not args or len(args) < 2:
            raise CommandError(u"Args missing")
        zipped_shapefile = args[0]
        areatype_idx = args[1]
        name_col = args[2] if len(args) > 2 else ''
        reference_col = args[3] if len(args) > 3 else ''

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
        prjfilename, dbffilename = None, None
        shpfilename, shxfilename = None, None
        for filename in flz.namelist():
            flz.extract(filename, tmpdir)
            full_name = os.sep.join([tmpdir, filename])
            if filename.endswith('.prj'):
                prjfilename = full_name
            elif filename.endswith('.dbf'):
                dbffilename = full_name
            elif filename.endswith('.shp'):
                shpfilename = full_name
            elif filename.endswith('.shx'):
                shxfilename = full_name
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
                sys.stdout.write('WARN: module gdal is not installed. SRID '
                        'cannot be read from proj\n      file. Default to '
                        'WGS84 projection (latitude/longitude).\n')
        ds = DataSource(shpfilename)
        lyr = ds[0]
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
        self.stdout.write('Import done:\n * %d items created\n '
                          '* %d items updated\n' % (created_nb, updated_nb))
