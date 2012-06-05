#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from optparse import make_option
from django.core.management.base import BaseCommand, CommandError
from geodjangofla.models import Commune, Departement, Region
from coop_geo import models

class Command(BaseCommand):
    args = '<numero_departements>'
    help = 'Import des départements depuis l\'application geodjangofla en base de '\
           'donnees'
    option_list = BaseCommand.option_list + (
        make_option('-u', '--update',
            action="store_true",
            dest="update", default=False,
            help="force la mise a jour"),
        )

    def _get_area_type(self, mnemonic):
        if not hasattr(self, 'area_type'):
            self.area_type = {}
            for k, lbl in (('DEP', u'Départment'),
                           ('CAN', u'Canton'),
                           ('COM', u'Ville'),
                           ('REG', u'Région')):
                self.area_type[k], created = models.AreaType.objects.get_or_create(
                                     txt_idx=k, defaults={'label': lbl})
        return self.area_type[mnemonic]


    def handle(self, *args, **options):
        update = 'update' in options and options['update']

        for reg in Region.objects.all():

            self.stdout.write(u'- Région : %s\n' % reg.nom_region)

            region,cr = models.Area.objects.get_or_create(
                    reference=reg.code_reg,
                    area_type=self._get_area_type('REG'),
                    defaults={  'label': reg.nom_region,
                                'reference': reg.code_reg,
                                'update_auto': True,
                                'area_type': self._get_area_type('REG')})

            for geodept in Departement.objects.filter(region_id=reg.code_reg):

                dept,cd = models.Area.objects.get_or_create(
                    area_type=self._get_area_type('DEP'),
                    reference=geodept.code_dept,
                    defaults={  'label': geodept.nom_dept,
                                'reference': geodept.code_dept,
                                'polygon': geodept.limite,
                                'area_type': self._get_area_type('DEP')})

                region.add_child(dept)
                self.stdout.write(u'\t- Département : %s\n' % dept.label)


            self.stdout.write(u'\n\n')
        self.stdout.write(u'Import fini\n')
