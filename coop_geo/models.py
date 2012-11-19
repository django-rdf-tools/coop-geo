#!/usr/bin/env python
# -*- coding: utf-8 -*-

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.gis.db import models
from django.contrib.gis.geos.collections import MultiPolygon
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save
from django.utils.translation import ugettext_lazy as _
from django_extensions.db import fields as exfields
#from genericm2m.models import RelatedObjectsDescriptor
from coop.models import URIModel, URI_MODE
import Geohash
import rdflib


class LocationCategory(models.Model):
    label = models.CharField(max_length=60, verbose_name=_(u"label"))
    slug = exfields.AutoSlugField(populate_from=('label'))

    class Meta:
        ordering = ['label']
        verbose_name = _(u'Location category')
        verbose_name_plural = _(u'Location categories')

    def __unicode__(self):
        return unicode(self.label)

    # def get_absolute_url(self):
    #     return reverse('location_category', args=[self.slug])


class Location(URIModel):
    """Location: a named point or/and polygon entered by an administrator"""
    label = models.CharField(max_length=150, verbose_name=_(u"label"),
                             blank=True, null=True)
    point = models.PointField(verbose_name=_(u"point"), blank=True, null=True,
                              srid=settings.COOP_GEO_EPSG_PROJECTION)
    adr1 = models.CharField(verbose_name=_(u"address"),
                            max_length=100)
    adr2 = models.CharField(verbose_name=_(u"address (extra)"), null=True,
                            blank=True, max_length=100)
    zipcode = models.CharField(verbose_name=_(u"zipcode"), null=True,
                               blank=True, max_length=5)
    city = models.CharField(verbose_name=_(u"city"), null=True, blank=True,
                            max_length=100)
    x_code = models.CharField(verbose_name=_(u"x_code"), null=True, blank=True,
                            max_length=20)
    country = models.CharField(verbose_name=_(u"country"), null=True, blank=True,
                            max_length=100)
    area = models.ForeignKey('Area', verbose_name=_(u'area'), blank=True,
                              null=True)
    owner = models.ForeignKey(User, verbose_name=_(u'owner'), blank=True,
                              null=True, editable=False)
    geohash = models.CharField(verbose_name=_(u'geohash'), null=True, blank=True,
                               max_length=20, editable=False)

    objects = models.GeoManager()

    is_ref_center = models.BooleanField(default=False)

    #related = RelatedObjectsDescriptor()


    class Meta:
        verbose_name = _(u'Location')
        verbose_name_plural = _(u'Locations')

    def __unicode__(self):
        lbl = self.label
        extra = []
        if self.adr1 != self.label:
            extra = [self.adr1]
        extra += [getattr(self, attr) for attr in ['adr2', 'zipcode', 'city']
                                                       if getattr(self, attr)]
        if extra:
            lbl = u"%s (%s)" % (lbl, u", ".join(extra))
        return lbl

    def has_point(self):
        return self.point != None
    has_point.boolean = True
    has_point.short_description = _(u'GPS')

    def save(self, *args, **kwargs):
        # if not self.point and not self.area:
        #     raise ValidationError(_(u"You must at least set a point or choose "
        #                             u"an area."))
        if not self.label:
            self.label = self.adr1
        if self.point:
            self.geohash = Geohash.encode(self.point.y, self.point.x)
        return super(Location, self).save(*args, **kwargs)

    @classmethod
    def get_all(cls, user=None):
        """
        Get all location (by owner)
        """
        locations = cls.objects
        user = None
        if user:
            locations = locations.filter(owner=user)
        return locations.order_by('label')

    # RDF stuff
    @property
    def location_uri(self):
        return 'http://data.economie-solidaire.fr/id/location/%s' % self.geohash

    def toRdfGraph(self):
        g = rdflib.Graph()
        g.add((rdflib.term.URIRef(self.location_uri), settings.NS.rdf.type, settings.NS.dct.Location))
        for method, arguments, reverse in self.location_base_mapping:
            for triple in getattr(self, method)(*arguments):
                g.add(triple)
        if not self.adr1 == u'': 
            g = g + super(Location, self).toRdfGraph()

        return g

    # 
    def to_django(self, g):
        for method, arguments, reverse in self.location_base_mapping:
            getattr(self, reverse)(g, *arguments)
        super(Location, self).to_django(g)


    def location_single_mapping(self, rdfPredicate, djangoField, lang=None):
        uri = lambda x: x.location_uri
        return self.base_single_mapping(uri, rdfPredicate, djangoField, lang=None)

    def location_single_reverse(self, g, rdfPred, djField, lang=None):
        uri = lambda x: x.location_uri
        self.base_single_reverse(uri, g, rdfPred, djField, lang)


    rdf_type = settings.NS.locn.Address

    # Avec la methode normale on traite la adresse car c'est elle qui utilise self.uri
    # la version dct:Location est traité elle par la surcharge
    base_mapping = [
        ('single_mapping', (settings.NS.dct.created, 'created'), 'single_reverse'),
        ('single_mapping', (settings.NS.dct.modified, 'modified'), 'single_reverse'),
        ('single_mapping', (settings.NS.rdfs.label, 'label', 'fr'), 'single_reverse'),
        ('single_mapping', (settings.NS.locn.thoroughfare, 'adr1'), 'single_reverse'),
        ('single_mapping', (settings.NS.locn.locatorName, 'adr2'), 'single_reverse'),
        ('single_mapping', (settings.NS.locn.postCode, 'zipcode'), 'single_reverse'),
        ('single_mapping', (settings.NS.locn.postName, 'city'), 'single_reverse'),

        ('fulladdr_mapping', (settings.NS.locn.fullAddress, ''), 'fulladdr_mapping_reverse'),
   ]

    def fulladdr_mapping(self, rdfPred, djF, lang=None):
        return [(rdflib.term.URIRef(self.uri), rdfPred, rdflib.term.Literal(self.__unicode__()))]

    def fulladdr_mapping_reverse(self, rdfPred, djF, lang=None):
        pass


    location_base_mapping = [
        ('location_single_mapping', (settings.NS.dct.created, 'created'), 'location_single_reverse'),
        ('location_single_mapping', (settings.NS.dct.modified, 'modified'), 'location_single_reverse'),
        ('location_single_mapping', (settings.NS.rdfs.label, 'label', 'fr'), 'location_single_reverse'),
        ('location_single_mapping', (settings.NS.locn.geographicName, 'label', 'fr'), 'location_single_reverse'),

        ('wkt_mapping', (settings.NS.locn.geometry, 'point'), 'wkt_mapping_reverse'),
        ('addr_mapping', (settings.NS.locn.address, 'uri'), 'addr_mapping_reverse'),
    ]

    def wkt_mapping(self, rdfPred, djF, lang=None):
        if getattr(self, djF):
            return [(rdflib.term.URIRef(self.location_uri), rdfPred, \
                     rdflib.term.Literal(getattr(self, djF).wkt, datatype=settings.NS.opens.wkt))]
        else:
            return []

    def wkt_mapping_reverse(self, g, rdfPred, djF, lang=None):
        values = list(g.objects(rdflib.term.URIRef(self.location_uri), rdfPred))
        if len(values) == 1:
            value = str(values[0])
            setattr(self, djF, value)

    def addr_mapping(self, rdfPred, djF, lang=None):
        if not self.adr1 == u'':    
            return [(rdflib.term.URIRef(self.location_uri), rdfPred, rdflib.term.URIRef(self.uri))]
        else:
            return []

    def addr_mapping_reverse(self, g, rdfPred, djF, lang=None):
        pass



#  si nécessaire
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic


class Located(models.Model):
    # things which are located
    location = models.ForeignKey(Location, null=True, blank=True,
                                 verbose_name=_(u"location"))
    main_location = models.BooleanField(default=False,
                                 verbose_name=_(u"main venue"))
    category = models.ForeignKey(LocationCategory, null=True, blank=True,
                                verbose_name=_(u"type of location"))
    content_type = models.ForeignKey(ContentType, blank=True, null=True)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey('content_type', 'object_id')

    def __unicode__(self):
        return unicode(self.content_object) + u" @ " + unicode(self.location)

    class Meta:
        verbose_name = _(u'Located item')
        verbose_name_plural = _(u'Located items')

AREA_DEFAULT_LOCATION_LBL = _(u"%s (center)")


class AreaType(models.Model):
    """Area type"""
    label = models.CharField(max_length=150, verbose_name=_(u"label"))
    txt_idx = models.CharField(verbose_name=_(u"mnemonic"), max_length='50')

    def __unicode__(self):
        return self.label

    class Meta:
        verbose_name = _(u'Area type')
        verbose_name_plural = _(u'Area types')


class Area(URIModel):
    """Areas: towns, regions, ... mainly set by import"""
    label = models.CharField(max_length=150, verbose_name=_(u"label"))
    reference = models.CharField(max_length=150, verbose_name=_(u"reference"),
                                 blank=True, null=True,
                                 help_text=_(u"SI ce n'est pas une référence INSEE, ne mettez rien ici."))
    default_location = models.ForeignKey(Location, blank=True, null=True,
            verbose_name=_(u"default location"), related_name='associated_area')
    related_areas = models.ManyToManyField('Area',
            verbose_name=_(u"related area"), through='AreaRelations')
    area_type = models.ForeignKey(AreaType, verbose_name=_(u"type"))
    polygon = models.MultiPolygonField(_(u"polygon"), blank=True, null=True,
                                  srid=settings.COOP_GEO_EPSG_PROJECTION)

    # when set to true a "parent" area is automaticaly updated with the add
    # of new childs
    update_auto = models.BooleanField(verbose_name=_(u"update automatically?"),
                                      default=False)
    objects = models.GeoManager()

    #  overwrite to deal with INSEE reference
    def init_uri(self):
        if self.reference:
            self.uri_mode = URI_MODE.COMMON
            self.uri = settings.RDF_NAMESPACES['geofr'] +  \
                AreaType.objects.get(id=self.area_type_id).txt_idx + \
                '_' + self.reference
            return self.uri
        else:
            return super(Area, self).init_uri()

    class Meta:
        verbose_name = _(u'Area')
        verbose_name_plural = _(u'Areas')

    def __unicode__(self):
        return self.label

    def add_parent(self, parent):
        if parent == self:
            raise ValidationError(u"You can't set a parent relative to itself.")
        self.related_areas.through.objects.get_or_create(child=self,
                                                         parent=parent)

    def add_child(self, child):
        if child == self:
            raise ValidationError(u"You can't set a parent relative to itself.")
        self.related_areas.through.objects.get_or_create(child=child,
                                                         parent=self)

    def add_childs(self, childs):
        for child in childs:
            self.add_child(child)

    def update_from_childs(self):
        if not self.update_auto or not self.child_rels.count():
            return

        geocollection = [childrel.child.polygon
                         for childrel in self.child_rels.all()]
        n_polygon = geocollection[0]
        for polygon in geocollection[1:]:
            n_polygon = n_polygon.union(polygon)
        #TODO: simplify with unions
        if type(n_polygon) != MultiPolygon:
            n_polygon = MultiPolygon([n_polygon])
        if n_polygon != self.polygon:
            self.polygon = n_polygon
            self.save()
        return

    @property
    def parent(self):
        if not self.parent_rels.count():
            return
        # only return the first defined parent
        return self.parent_rels.order_by('id').all()[0].parent

    @property
    def level(self):
        if hasattr(self, '_level') and isinstance(self._level, int):
            return self._level
        level = 0
        if not self.parent_rels.count():
            self._level = 0
        else:
            # first relation define the level
            self._level = self.parent_rels.all()[0].parent.level + 1
        return self._level

    @property
    def leaf(self):
        if not hasattr(self, '_leaf'):
            self._leaf = False
        return self._leaf

    @property
    def end_leaf(self):
        if not hasattr(self, '_end_leaf'):
            self._end_leaf = 0
        return self._end_leaf

    @classmethod
    def get_all(cls):
        """
        Get areas sorted in a tree style
        """
        areas = cls.objects.order_by('label').all()
        sorted_areas = []

        area_childs_dct = {}
        for area in areas:
            if not area.parent:
                continue
            parent_pk = area.parent.pk
            if area.parent.pk not in area_childs_dct:
                area_childs_dct[parent_pk] = []
            area_childs_dct[parent_pk].append(area)

        def _get_childs(area, level):
            level += 1
            if area.pk not in area_childs_dct:
                return
            childs = []
            for child in area_childs_dct[area.pk]:
                child._level = level
                childs.append(child)
                childs_of_child = _get_childs(child, level)
                if childs_of_child:
                    childs[-1]._leaf = True
                    if not hasattr(childs_of_child[-1], '_end_leaf'):
                        childs_of_child[-1]._end_leaf = 0
                    childs_of_child[-1]._end_leaf += 1
                    childs += childs_of_child
            return childs

        for area in areas:
            if area.parent:
                break
            area._level = 0
            sorted_areas.append(area)
            childs = _get_childs(area, 0)
            if childs:
                sorted_areas[-1]._leaf = True
                if not hasattr(childs[-1], '_end_leaf'):
                    childs[-1]._end_leaf = 0
                childs[-1]._end_leaf += 1
                sorted_areas += childs
        return sorted_areas


    # http://rdf.insee.fr/geo/COM_03273

    # RDF stuff
    rdf_type = settings.NS.schema.AdministrativeArea
    # et aussi dct.Location??
    base_mapping = [
        ('single_mapping', (settings.NS.dct.created, 'created'), 'single_reverse'),
        ('single_mapping', (settings.NS.dct.modified, 'modified'), 'single_reverse'),
        ('single_mapping', (settings.NS.rdfs.label, 'label', 'fr'), 'single_reverse'),
        ('single_mapping', (settings.NS.skos.notation, 'reference', 'fr'), 'single_reverse'),

        ('type_mapping', (settings.NS.rdf.type, 'area_type'), 'type_mapping_reverse'),
        ('wkt_mapping', (settings.NS.locn.geometry, 'polygon'), 'wkt_mapping_reverse'),
     ]

    def type_mapping(self, rdfPred, djF, lang=None):
        aType = getattr(self, djF)
        res = [(rdflib.term.URIRef(self.uri), rdfPred, settings.NS.dct.Location)]
        if aType.txt_idx == 'DEP':
            res.append((rdflib.term.URIRef(self.uri), rdfPred, settings.NS.geofr.Departement))
        elif aType.txt_idx == 'COM':
            res.append((rdflib.term.URIRef(self.uri), rdfPred, settings.NS.geofr.Commune))
        elif aType.txt_idx == 'REG':
            res.append((rdflib.term.URIRef(self.uri), rdfPred, settings.NS.geofr.Region))
        elif aType.txt_idx == 'EPCI':
            res.append((rdflib.term.URIRef(self.uri), rdfPred, settings.NS.geofr.EPCI))
        else:
            pass
        return res

    def type_mapping_reverse(self, g, rdfPred, djF, lang=None):
        values = set(g.objects(rdflib.term.URIRef(self.uri), rdfPred))
        values.remove(self.rdf_type)
        values.removes(settings.NS.dct.Location)
        if len(values) == 1:
            value = values[0]
            if value == settings.NS.geofr.Departement:
                setattr(self, djF, AreaType.objects.get(txt_idx='DEP'))
            elif value == settings.NS.geofr.Commune:
                setattr(self, djF, AreaType.objects.get(txt_idx='COM'))
            elif value == settings.NS.geofr.Region:
                setattr(self, djF, AreaType.objects.get(txt_idx='REG'))
            elif value == settings.NS.geofr.EPCI:
                setattr(self, djF, AreaType.objects.get(txt_idx='EPCI'))
            else:
                pass


    def wkt_mapping(self, rdfPred, djF, lang=None):
        return [(rdflib.term.URIRef(self.uri), rdfPred, \
                 rdflib.term.Literal(getattr(self, djF).wkt, datatype=settings.NS.opens.wkt))]

    def wkt_mapping_reverse(self, g, rdfPred, djF, lang=None):
        values = list(g.objects(rdflib.ter.URIRef(self.uri), rdfPred))
        if len(values) == 1:
            value = str(values[0])
            setattr(self, djF, value)





def area_post_save(sender, **kwargs):
    if not kwargs['instance']:
        return
    area = kwargs['instance']
    if not area.default_location and area.polygon:
        datas = {'point': area.polygon.centroid,
                 'label': AREA_DEFAULT_LOCATION_LBL % area.label}
        area.default_location = Location.objects.create(**datas)
        area.save()
    area.update_from_childs()
    if area.parent_rels.count():
        for parentrel in area.parent_rels.all():
            parentrel.parent.update_from_childs()
post_save.connect(area_post_save, sender=Area)


class AreaLink(models.Model):
    location = models.ForeignKey(Area, null=True, blank=True,  # TODO devrait s'appeler area
                      verbose_name=_(u'area'))
    # things which are in an area
    content_type = models.ForeignKey(ContentType, blank=True, null=True)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey('content_type', 'object_id')

    def __unicode__(self):
        return unicode(self.content_object) + unicode(_(u" has area : ")) + \
               unicode(self.location)

    class Meta:
        verbose_name = _(u'Linked area')
        verbose_name_plural = _(u'Linked areas')


class AreaRelations(models.Model):
    """
    Relations between areas.
    """
    parent = models.ForeignKey(Area, verbose_name=_(u"inside"),
                               related_name='child_rels')
    child = models.ForeignKey(Area, verbose_name=_(u"included"),
                              related_name='parent_rels')

    class Meta:
        verbose_name = _(u"Area relation")
        verbose_name_plural = _(u"Area relations")

    def __unicode__(self):
        return u" - ".join((unicode(self.parent), unicode(self.child)))

    def save(self, *args, **kwargs):
        if self.child == self.parent:
            raise ValidationError(_(u"Child and Parent have to be different."))
        return super(AreaRelations, self).save(*args, **kwargs)


def arearel_post_save(sender, **kwargs):
    if not kwargs['instance']:
        return
    arearel = kwargs['instance']
    arearel.parent.update_from_childs()
post_save.connect(arearel_post_save, sender=AreaRelations)

