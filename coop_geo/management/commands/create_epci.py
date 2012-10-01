#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import coop_geo
from optparse import make_option
from django.core.management.base import BaseCommand, CommandError
from coop_geo import models
import csv
import re


COOP_GEO_PATH = os.path.dirname(os.path.abspath(coop_geo.__file__))


class Command(BaseCommand):
    args = '<numero_departements>'
    help = u'Création des intercommunalité à partir des données de l\'INSEE'
    option_list = BaseCommand.option_list

    def handle(self, *args, **options):
        epci = models.AreaType.objects.get(txt_idx='EPCI')

        if not args:
            raise CommandError("Veuillez entrer au moins un numero de "\
                               "departement")
        for dpt in args:

            try:
                assert len(dpt) < 3
            except AssertionError:
                raise CommandError("Le numero de departement %s n'est pas "\
                                   "valide." % dpt)
            dpt = len(dpt) == 1 and "0" + dpt or dpt
            self.stdout.write('\nDepartement %s\n' % dpt)
            rows = csv.reader(open( os.path.abspath(COOP_GEO_PATH + '/epci/epci.csv'), 'rb'),
                                delimiter=';')
            p = re.compile('\d{2}' + str(dpt) + '\d{5}')
            for row in rows:
                if p.match(row[0]):
                    cc, created = models.Area.objects.get_or_create(
                            reference=row[0],
                            defaults={  'label': row[1].decode('utf-8'),
                                        'update_auto': True,
                                        'area_type': epci})
                    if created:
                        self.stdout.write(u'Zone créée : %s\n' % row[1].decode('utf-8'))
                    communes = csv.reader(open(os.path.abspath(COOP_GEO_PATH + '/epci/communes.csv'), 'rb'), delimiter=';')
                    for comm in communes:
                        if cc.reference == comm[1]:
                            try:
                                commune = models.Area.objects.get(reference=comm[0])
                            except:
                                self.stdout.write(u'ERREUR : la commune avec le code INSEE %s n\'a pas été trouvée\n' % comm[0])
                            rel, created = models.AreaRelations.objects.get_or_create(parent=cc, child=commune)
                            if created:
                                self.stdout.write(u'Relation %s <--> %s créée' % (cc, commune))

                #self.stdout.write('\n')
        self.stdout.write(u'\n*** Import terminé ***\n\n')
