# This file is part of opentaps Smart Energy Applications Suite (SEAS).

# opentaps Smart Energy Applications Suite (SEAS) is free software:
# you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# opentaps Smart Energy Applications Suite (SEAS) is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public License
# along with opentaps Smart Energy Applications Suite (SEAS).
# If not, see <https://www.gnu.org/licenses/>.

import logging
import re

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.fields import HStoreField
from django.core.exceptions import ValidationError
from django.db import connections
from django.db import models
from django.db.models import AutoField
from django.db.models import BooleanField
from django.db.models import CharField
from django.db.models import DateTimeField
from django.db.models import FloatField
from django.db.models import ForeignKey
from django.db.models import IntegerField
from django.db.models import ProtectedError
from django.db.models import TextField
from django.db.models.signals import post_delete
from django.db.models.signals import post_save
from django.db.models.signals import pre_delete
from django.db.utils import DatabaseError
from django.dispatch import receiver
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _
from enum import Enum
from filer.fields.file import FilerFileField
from filer.models import Image as FilerFile
from cratedb.fields import HStoreField as CrateHStoreField
from cratedb.fields import ArrayField as CrateArrayField

logger = logging.getLogger(__name__)


class Tag(models.Model):
    class KINDS(Enum):
        string = ('Str', 'String')
        coord = ('Coord', 'Coordinate')
        reference = ('Ref', 'Reference')
        number = ('Number', 'Number')
        object = ('Obj', 'Object')
        marker = ('Marker', 'Marker')

        @classmethod
        def get_value(cls, member):
            return cls[member].value[0]

    tag = CharField(_("Tag Name"), max_length=255, primary_key=True)
    kind = CharField(_("Kind"), blank=True, max_length=255, choices=[x.value for x in KINDS])
    description = CharField(_("Tag Description"), blank=True, null=True, max_length=512)
    details = CharField(_("Tag Details"), blank=True, null=True, max_length=512)

    bacnet_tag_prefix = 'bacnet_'

    def __str__(self):
        return self.tag

    def get_absolute_url(self):
        return reverse("core:tag_detail", kwargs={"tag": self.tag})

    def get_use_count(self):
        if self.kind == Tag.KINDS.marker.value[0]:
            return Entity.objects.filter(m_tags__contains=[self.tag]).count()
        else:
            return Entity.objects.filter(kv_tags__has_key=self.tag).count()

    def can_delete(self):
        return self.get_use_count() == 0

    def valid_value(self, value):
        if self.kind == Tag.KINDS.number.value[0]:
            # allow multiple format of number and ending with non numbers (eg: 100ft is considered a Number)
            reg = re.compile(r'^[\d ]+')
            if reg.match(value):
                return True
            raise ValidationError('The value must be a Number')
        if self.kind == Tag.KINDS.reference.value[0]:
            c = 0
            if self.tag in ['siteRef', 'equipRef', 'modelRef']:
                if self.tag == 'siteRef':
                    c = Entity.objects.filter(kv_tags__id=value).filter(m_tags__contains=['site']).count()
                elif self.tag == 'equipRef':
                    c = Entity.objects.filter(kv_tags__id=value).filter(m_tags__contains=['equip']).count()
                elif self.tag == 'modelRef':
                    c = Entity.objects.filter(kv_tags__id=value).filter(m_tags__contains=['model']).count()
                if c > 0:
                    return True
                else:
                    raise ValidationError('The {0}: {1} does not exist'.format(self.tag, value))
        if self.kind != Tag.KINDS.marker.value[0]:
            # any non Marker requires a value
            if not value:
                raise ValidationError('This Tag requires a value')

        return True

    def get_ref_entity(self):
        if not hasattr(self, 'value') or not self.value:
            return None
        if self.tag == 'siteRef':
            return SiteView.objects.get(object_id=self.value)
        elif self.tag == 'equipRef':
            return EquipmentView.objects.get(object_id=self.value)
        elif self.tag == 'modelRef':
            return ModelView.objects.get(object_id=self.value)

    @classmethod
    def get_ref_entity_for(cls, tag, value):
        if not value:
            return None
        if tag == 'siteRef':
            return SiteView.objects.get(object_id=value)
        elif tag == 'equipRef':
            return EquipmentView.objects.get(object_id=value)
        elif tag == 'modelRef':
            return ModelView.objects.get(object_id=value)


@receiver(pre_delete, sender=Tag, dispatch_uid='tag_delete_signal')
def check_tag_can_delete(sender, instance, using, **kwargs):
    if not instance.can_delete():
        raise ProtectedError('This Tag is being used', instance)


class ListableEntity(models.Model):
    entity_id = CharField(_("Entity ID"), max_length=255, primary_key=True)
    object_id = CharField(_("Object ID"), max_length=255, blank=True)
    description = CharField(_("Description"), max_length=255, blank=True)

    def __str__(self):
        return self.entity_id

    def get_absolute_url(self):
        return reverse("core:entity_detail", kwargs={"entity_id": self.entity_id})

    class Meta:
        managed = False
        db_table = 'core_entity_view'


class Entity(models.Model):
    entity_id = CharField(_("Entity ID"), max_length=255, primary_key=True)
    topic = CharField(_("Topic"), max_length=255, blank=True, null=True)
    kv_tags = HStoreField(blank=True, null=True)
    m_tags = ArrayField(CharField(max_length=255, blank=True, null=True))
    dashboard_uid = CharField(_("Dashboard UID"), max_length=255, blank=True)
    dashboard_snapshot_uid = CharField(_("Dashboard Snapshot UID"), max_length=255, blank=True, null=True)

    def __str__(self):
        return self.entity_id

    def get_absolute_url(self):
        return reverse("core:entity_detail", kwargs={"entity_id": self.entity_id})

    def add_tag(self, tag, value=None, commit=True):
        logger.info('Add_tag %s to %s value = %s', tag, self, value)
        if value:
            if not self.kv_tags:
                self.kv_tags = {}
            self.kv_tags[tag] = value
        else:
            if not self.m_tags:
                self.m_tags = []
            if tag not in self.m_tags:
                self.m_tags.append(tag)
        if commit:
            self.save()

    def add_tags_from_model(self, model, commit=True):
        exclude_tags = ['id', 'dis', 'model']
        if model:
            if model['kv_tags']:
                for tag in model['kv_tags'].keys():
                    if model['kv_tags'][tag]:
                        if tag not in exclude_tags:
                            self.add_tag(tag, model['kv_tags'][tag], commit=commit)
            if model['m_tags']:
                for tag in model['m_tags']:
                    if tag not in exclude_tags:
                        self.add_tag(tag, commit=commit)

    def remove_tag(self, tag, commit=True):
        # handle both kv_tags and m_tags
        self.kv_tags.pop(tag, None)
        if tag in self.m_tags:
            self.m_tags.remove(tag)
        if commit:
            self.save()

    def remove_all_tags(self, commit=True):
        self.kv_tags = {}
        self.m_tags = []
        if commit:
            self.save()


class ModelView(models.Model):
    entity_id = CharField(_("Model ID"), max_length=255, primary_key=True)
    object_id = CharField(_("Object ID"), max_length=255, blank=True)
    description = CharField(_("Description"), max_length=255, blank=True)
    kv_tags = HStoreField(blank=True, null=True)
    m_tags = ArrayField(CharField(max_length=255, blank=True, null=True))

    tried_parent_model = False
    parent_model = None
    child_models = None

    def __str__(self):
        return self.entity_id

    def as_dict(self):
        return dict(
            entity_id=self.entity_id,
            description=self.description)

    def get_parent_model(self):
        if not self.parent_model and not self.tried_parent_model and 'modelRef' in self.kv_tags:
            try:
                self.parent_model = ModelView.objects.filter(object_id=self.kv_tags['modelRef'])[0]
            except IndexError:
                self.tried_parent_model = True

        return self.parent_model

    def get_child_models(self):
        if not self.child_models:
            self.child_models = ModelView.objects.filter(kv_tags__contains={'modelRef': self.object_id})
        return self.child_models

    def get_absolute_url(self):
        return reverse("core:model_detail", kwargs={"entity_id": self.entity_id})

    def get_use_count(self):
        return Entity.objects.filter(kv_tags__contains={'modelRef': self.entity_id}).count()

    def can_delete(self):
        return self.get_use_count() == 0

    def get_choices():
        model_choices = [(c.object_id, '{}: {}'.format(c.object_id, c.description)) for c in ModelView.objects.all()]
        model_choices.insert(0, ('', ''))

        return model_choices

    class Meta:
        verbose_name = 'model'
        managed = False
        db_table = 'core_model_view'


@receiver(pre_delete, sender=ModelView, dispatch_uid='model_delete_signal')
def check_model_can_delete(sender, instance, using, **kwargs):
    if not instance.can_delete():
        raise ProtectedError('This Model is being used', instance)


class SiteView(models.Model):
    entity_id = CharField(_("Site ID"), max_length=255, primary_key=True)
    object_id = CharField(_("Object ID"), max_length=255, blank=True)
    description = CharField(_("Description"), max_length=255, blank=True)
    state = CharField(_("State"), max_length=255, blank=True)
    city = CharField(_("City"), max_length=255, blank=True)
    area = CharField(_("Area"), max_length=255, blank=True)
    kv_tags = HStoreField(blank=True, null=True)
    m_tags = ArrayField(CharField(max_length=255, blank=True, null=True))

    def __str__(self):
        return self.entity_id

    def as_dict(self):
        return dict(
            entity_id=self.entity_id,
            description=self.description,
            state=self.state,
            city=self.city,
            area=self.area)

    def get_absolute_url(self):
        return reverse("core:site_detail", kwargs={"site": self.entity_id})

    def get_choices():
        site_choices = [(c.entity_id, '{}'.format(c.description))
                        for c in SiteView.objects.all().order_by('description')]

        return site_choices

    def get_site_choices():
        site_choices = [{'id': c.entity_id, 'description': c.description}
                        for c in SiteView.objects.all().order_by('description')]

        return site_choices

    def get_site_obj_choices():
        site_choices = [{'id': c.object_id, 'description': c.description}
                        for c in SiteView.objects.all().order_by('description')]

        return site_choices

    def count():
        return SiteView.objects.all().count()

    class Meta:
        verbose_name = 'site'
        managed = False
        db_table = 'core_site_view'


class EquipmentView(models.Model):
    entity_id = CharField(_("Equipment ID"), max_length=255, primary_key=True)
    object_id = CharField(_("Object ID"), max_length=255, blank=True)
    description = CharField(_("Description"), max_length=255, blank=True)
    site_id = CharField(_("Site"), max_length=255, blank=True)
    dashboard_uid = CharField(_("Dashboard"), max_length=255, blank=True)
    dashboard_snapshot_uid = CharField(_("Dashboard Snapshot"), max_length=255, blank=True)
    kv_tags = HStoreField(blank=True, null=True)
    m_tags = ArrayField(CharField(max_length=255, blank=True, null=True))

    def __str__(self):
        return self.entity_id

    def as_dict(self):
        return dict(
            entity_id=self.entity_id,
            description=self.description,
            site_id=self.site_id)

    def get_absolute_url(self):
        return reverse("core:equipment_detail", kwargs={"equip": self.entity_id})

    class Meta:
        verbose_name = 'equipment'
        managed = False
        db_table = 'core_equipment_view'


class PointView(models.Model):
    entity_id = CharField(_("Point ID"), max_length=255, primary_key=True)
    object_id = CharField(_("Object ID"), max_length=255, blank=True)
    topic = CharField(_("Topic"), max_length=255, blank=True)
    description = CharField(_("Description"), max_length=255, blank=True)
    kind = CharField(_("Kind"), max_length=255, blank=True)
    unit = CharField(_("Unit"), max_length=255, blank=True)
    site_id = CharField(_("Site"), max_length=255, blank=True)
    equipment_id = CharField(_("Equipment"), max_length=255, blank=True)
    dashboard_uid = CharField(_("Dashboard"), max_length=255, blank=True)
    current_value = CharField(_("Current Value"), max_length=255, blank=True)
    kv_tags = HStoreField(blank=True, null=True)
    m_tags = ArrayField(CharField(max_length=255, blank=True, null=True))

    def __str__(self):
        return self.entity_id

    def get_absolute_url(self):
        return reverse("core:point_detail", kwargs={"entity_id": self.entity_id})

    class Meta:
        verbose_name = 'point'
        managed = False
        db_table = 'core_point_view'


class EntityFile(models.Model):
    entity_id = CharField(_("Entity ID"), max_length=255)
    comments = TextField(_("Comments"), blank=True)
    created = DateTimeField(_("Created Date"), default=now)
    owner = ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    uploaded_file = FilerFileField(null=True, blank=True, related_name="entity_file", on_delete=models.CASCADE)
    can_thumbnail = BooleanField(default=False)
    link = TextField(blank=True)
    link_name = TextField(blank=True)


@receiver(post_delete, sender=EntityFile, dispatch_uid='entityfile_delete_signal')
def entity_file_deleted(sender, instance, using, **kwargs):
    logger.info('entity_file_deleted: id=%s uploaded_file=%s', instance.id, instance.uploaded_file_id)
    if instance.uploaded_file_id:
        c = EntityFile.objects.filter(uploaded_file_id=instance.uploaded_file_id).count()
        if c == 0:
            logger.info('entity_file_deleted: file no longer referenced, deleting id=%s', instance.uploaded_file_id)
            FilerFile.objects.get(id=instance.uploaded_file_id).delete()


class EntityNote(models.Model):
    entity_id = CharField(_("entity_id"), max_length=255)
    content = TextField(_("Comments"), blank=True)
    created = DateTimeField(_("Created Date"), default=now)
    owner = ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)


@receiver(post_delete, sender=ModelView, dispatch_uid='model_post_delete_signal')
def model_deleted(sender, instance, using, **kwargs):
    # remove all associated resourcese: notes, files, links ...
    logger.info('model_deleted: %s', instance.entity_id)
    EntityNote.objects.filter(entity_id=instance.entity_id).delete()
    EntityFile.objects.filter(entity_id=instance.entity_id).delete()


@receiver(post_delete, sender=Entity, dispatch_uid='entity_post_delete_signal')
def entity_deleted(sender, instance, using, **kwargs):
    # remove all associated resourcese: notes, files, links ...
    logger.info('entity_deleted: %s', instance.entity_id)
    EntityNote.objects.filter(entity_id=instance.entity_id).delete()
    EntityFile.objects.filter(entity_id=instance.entity_id).delete()
    if settings.CRATE_TAG_AUTOSYNC:
        delete_tags_from_crate_entity(instance)


@receiver(post_save, sender=Entity, dispatch_uid='entity_post_save_signal')
def entity_saved(sender, instance, using, **kwargs):
    # remove all associated resourcese: notes, files, links ...
    logger.info('entity_saved: %s', instance.entity_id)
    if settings.CRATE_TAG_AUTOSYNC:
        sync_tags_to_crate_entity(instance)


class Topic(models.Model):
    topic = CharField(_("Topic"), max_length=255, primary_key=True)
    kv_tags = CrateHStoreField(blank=True, null=True)
    m_tags = CrateArrayField(CharField(max_length=255, blank=True, null=True))

    tried_related_point = False
    related_point = None

    def __str__(self):
        return self.topic or '?? no topic ??'

    @property
    def point_description(self):
        p = self.get_related_point()
        if p:
            return p.description
        return None

    @property
    def equipment_id(self):
        p = self.get_related_point()
        if p:
            return p.equipment_id
        return None

    @property
    def entity_id(self):
        p = self.get_related_point()
        if p:
            return p.entity_id
        return None

    @property
    def site_id(self):
        p = self.get_related_point()
        if p:
            return p.site_id
        return None

    @classmethod
    def ensure_topic_exists(cls, topic):
        with connections['crate'].cursor() as c:
            sql = """INSERT INTO {0} (topic)
            VALUES (%s)""".format("topic")
            try:
                c.execute(sql, [topic])
            except Exception:
                # just make sure the topic exists
                pass

    def get_related_point(self):
        if not self.related_point and not self.tried_related_point:
            try:
                self.related_point = PointView.objects.filter(topic=self.topic)[0]
            except IndexError:
                self.tried_related_point = True

        return self.related_point

    def get_absolute_url(self):
        if self.entity_id:
            return reverse("core:point_detail", kwargs={"entity_id": self.entity_id})
        return reverse("core:entity_detail", kwargs={"entity_id": self.topic})

    class Meta:
        managed = False
        db_table = 'topic'

    class Db:
        cratedb = True


class TimeZone(models.Model):
    time_zone = CharField(_("Time Zone"), max_length=255)
    tzoffset = IntegerField(default=0)
    tzoffset_dst = IntegerField(default=0)
    geo_ids = ArrayField(CharField(max_length=255, blank=True, null=True), null=True)

    def get_choices(geo_id=None):
        timezones = TimeZone.objects.all().order_by('tzoffset', 'time_zone')
        if geo_id:
            timezones = timezones.filter(geo_ids__contains=[geo_id])
        timezone_choices = []
        for c in timezones:
            title = c.time_zone + " (GMT "
            if c.tzoffset >= 0:
                title = title + "+"

            total_minutes = c.tzoffset / 60
            hours = int(total_minutes // 60)
            minutes = int(total_minutes % 60)

            title = title + '{:02d}:{:02d}'.format(hours, minutes) + ")"
            timezone_choices.append((c.time_zone, title))

        return timezone_choices


class Geo(models.Model):
    geo_code_id = CharField(_("Geo Code ID"), max_length=255, primary_key=True)
    geo_code_type_id = CharField(_("Geo Code Type ID"), max_length=255, blank=False, null=False)
    geo_code_name = CharField(_("Geo Code Name"), max_length=255, blank=False, null=False)
    parent_geo_code_id = CharField(max_length=255, blank=True, null=True)
    geo_name = CharField(_("Name"), max_length=255, blank=True, null=True)

    def get_country_choices():
        country_choices = [{'id': c.geo_code_name, 'name': c.geo_code_name + ' - ' + c.geo_name}
                           for c in Geo.objects.filter(geo_code_type_id='COUNTRY')]

        return country_choices

    def get_states_list(geo_code_name):
        states_list = []
        country = Geo.objects.filter(geo_code_type_id='COUNTRY', geo_code_name=geo_code_name).first()
        if country:
            states = Geo.objects.filter(geo_code_type_id='STATE', parent_geo_code_id=country.geo_code_id)
            if states:
                states_list = [{'id': c.geo_code_name, 'name': c.geo_code_name + ' - ' + c.geo_name} for c in states]

        return states_list

    def get_state_choices():
        state_choices = [(c.geo_code_name, c.geo_code_name)
                         for c in Geo.objects.filter(geo_code_type_id='STATE')]

        return state_choices


class TopicTagRuleSet(models.Model):
    name = CharField(_("Name"), max_length=255)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("core:topictagruleset_detail", kwargs={"id": self.id})


class TopicTagRule(models.Model):
    name = CharField(_("Name"), max_length=255)
    rule_set = ForeignKey(TopicTagRuleSet, on_delete=models.CASCADE)
    filters = ArrayField(HStoreField(blank=True, null=True), default=list)
    tags = ArrayField(HStoreField(blank=True, null=True), default=list)
    action = CharField(max_length=255, blank=True, null=True)
    action_fields = HStoreField(blank=True, null=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("core:topictagrule_detail", kwargs={"id": self.id})


def ensure_crate_entity_table():
    with connections['crate'].cursor() as c:
        sql = """
        CREATE TABLE IF NOT EXISTS "topic" (
           "topic" STRING,
           "m_tags" ARRAY(STRING),
           "kv_tags" OBJECT (DYNAMIC) AS (
              "id" STRING,
              "dis" STRING
           ),
           PRIMARY KEY ("topic")
        );"""
        c.execute(sql)


def kv_tags_update_crate_entity_string(kv_tags, params_list):
    res = '{'
    first = True
    for k in kv_tags.keys():
        if not first:
            res += ', '
        res += '"{}" = CAST(%s AS STRING)'.format(k, kv_tags[k])
        params_list.append(kv_tags[k])
        first = False
    res += '}'
    return res


def delete_tags_from_crate_entity(row):
    # we only sync for entity linked to a topic
    if not row.topic:
        return
    with connections['crate'].cursor() as c:
        # make sure the topic is in CrateDB
        sql = """DELETE {0} WHERE topic = %s;""".format("topic")
        try:
            c.execute(sql, [row.topic])
        except Exception:
            # ignore if the entity did not exist
            pass


def sync_tags_to_crate_entity(row, retried=False):
    # we only sync for entity linked to a topic
    if not row.topic:
        return
    with connections['crate'].cursor() as c:
        # make sure the topic is in CrateDB
        sql = """INSERT INTO {0} (topic)
        VALUES (%s)""".format("topic")
        try:
            c.execute(sql, [row.topic])
        except DatabaseError as e:
            # could be the table is missing
            if 'RelationUnknown' in str(e):
                if not retried:
                    ensure_crate_entity_table()
                    # try again
                    return sync_tags_to_crate_entity(row, retried=True)
        except Exception:
            # just make sure the topic exists
            pass

        if row.m_tags or row.kv_tags:
            params_list = []
            sql = """ UPDATE "topic" SET """
            if row.kv_tags:
                sql += " kv_tags = {} ".format(kv_tags_update_crate_entity_string(row.kv_tags, params_list))
            if row.m_tags:
                if row.kv_tags:
                    sql += ", "
                sql += " m_tags = %s "
                params_list.append(row.m_tags)
            sql += """ WHERE topic = %s;"""
            params_list.append(row.topic)
            logger.info('sync_tags_to_crate_entity SQL: %s', sql)
            logger.info('sync_tags_to_crate_entity Params: %s', params_list)
            c.execute(sql, params_list)


class UnitOfMeasure(models.Model):
    uom_id = CharField(max_length=255, primary_key=True)
    code = CharField(max_length=255)
    type = CharField(max_length=255)
    description = CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'core_unit_of_measure'


class WeatherStation(models.Model):
    weather_station_id = CharField(max_length=12, primary_key=True)
    weather_station_code = CharField(max_length=12)
    station_name = CharField(max_length=255, blank=True, null=True)
    country = CharField(max_length=2, blank=True, null=True)
    state = CharField(max_length=2, blank=True, null=True)
    call = CharField(max_length=6, blank=True, null=True)
    latitude = FloatField(null=True)
    longitude = FloatField(null=True)
    elevation = FloatField(null=True)
    elevation_uom = ForeignKey(UnitOfMeasure, on_delete=models.DO_NOTHING)
    meta_data = HStoreField(null=True, blank=True)
    source = CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'core_weather_station'

    def __str__(self):
        return self.weather_station_code + (" ({name})".format(name=self.station_name) if self.station_name else '')


class WeatherHistory(models.Model):
    weather_history_id = AutoField(_("Weather History ID"), primary_key=True, auto_created=True)
    weather_station = ForeignKey(WeatherStation, on_delete=models.CASCADE)
    as_of_datetime = DateTimeField(_("History Date"), default=now)
    temp_c = FloatField(null=True)
    temp_f = FloatField(null=True)
    source = CharField(max_length=255, blank=True, null=True)
    created_by_user = ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_datetime = DateTimeField(_("Created Date"), default=now)

    class Meta:
        db_table = 'core_weather_history'


class Meter(models.Model):
    meter_id = CharField(_("Meter ID"), max_length=255, primary_key=True)
    description = CharField(_("Description"), max_length=255, blank=True, null=True)
    weather_station = ForeignKey(WeatherStation, null=True, blank=True, on_delete=models.SET_NULL)
    site = ForeignKey(Entity, on_delete=models.CASCADE)
    from_datetime = DateTimeField(_("From Date"), default=now)
    thru_datetime = DateTimeField(_("Thru Date"), blank=True, null=True)

    def get_absolute_url(self):
        return reverse("core:meter_detail", kwargs={"meter_id": self.meter_id})


class MeterHistory(models.Model):
    meter_history_id = AutoField(_("Meter History ID"), primary_key=True, auto_created=True)
    meter = ForeignKey(Meter, on_delete=models.CASCADE)
    as_of_datetime = DateTimeField(_("As Of Datetime"), default=now)
    value = FloatField(null=True)
    uom = ForeignKey(UnitOfMeasure, on_delete=models.DO_NOTHING)
    source = CharField(max_length=255)
    duration = IntegerField(default=0)
    cost = FloatField(null=True)
    cost_uom = ForeignKey(UnitOfMeasure, related_name="cost_uom", null=True, blank=True, on_delete=models.DO_NOTHING)
    created_datetime = DateTimeField(_("Created Date"), default=now)
    created_by_user = ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        db_table = 'core_meter_history'


class SiteWeatherStations(models.Model):
    site = ForeignKey(Entity, on_delete=models.CASCADE)
    weather_station = ForeignKey(WeatherStation, on_delete=models.CASCADE)
    from_datetime = DateTimeField(_("From Date"), default=now)
    thru_datetime = DateTimeField(_("Thru Date"), null=True)
    source = CharField(max_length=255, blank=True, null=True)
    created_by_user = ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_datetime = DateTimeField(_("Created Date"), default=now)

    class Meta:
        db_table = 'core_site_weather_stations'
