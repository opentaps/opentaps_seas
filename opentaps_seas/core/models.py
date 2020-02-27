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

import csv
import logging
import re
from datetime import datetime
from datetime import time
from datetime import timedelta
from functools import lru_cache

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.fields import HStoreField
from django.core.exceptions import ValidationError
from django.db import connections
from django.db import models
from django.db import OperationalError
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
from django.db.models.signals import pre_save
from django.db.models import Q
from django.db.utils import DatabaseError
from django.dispatch import receiver
from django.urls import reverse
from django.utils.timezone import now
from django.utils.timezone import get_current_timezone
from django.utils.translation import ugettext_lazy as _
from enum import Enum
from filer.fields.file import FilerFileField
from filer.models import Image as FilerFile
from cratedb.fields import HStoreField as CrateHStoreField
from cratedb.fields import ArrayField as CrateArrayField
from ..party.models import Party

logger = logging.getLogger(__name__)


DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def date_to_string(datetime, tz=None):
    if not datetime:
        return None
    if tz:
        datetime = datetime.astimezone(tz)
    return datetime.strftime(DATE_FORMAT)


def datetime_to_string(datetime, tz=None):
    if not datetime:
        return None
    if tz:
        datetime = datetime.astimezone(tz)
    return datetime.strftime(DATETIME_FORMAT)


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
            try:
                sv = SiteView.objects.get(object_id=value)
            except SiteView.DoesNotExist:
                sv = None
            return sv
        elif tag == 'equipRef':
            try:
                ev = EquipmentView.objects.get(object_id=value)
            except EquipmentView.DoesNotExist:
                ev = None
            return ev
        elif tag == 'modelRef':
            try:
                mv = ModelView.objects.get(object_id=value)
            except ModelView.DoesNotExist:
                mv = None
            return mv


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

    def meters(self):
        return Meter.objects.filter(site_id=self.entity_id, thru_datetime__isnull=True).order_by('meter_id')

    def transactions(self):
        qs = FinancialTransaction.objects.filter(meter__site__entity_id=self.entity_id)
        return qs.order_by('-transaction_datetime')

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

    try:
        with connections['crate'].cursor() as c:
            # make sure the topic is in CrateDB
            sql = """DELETE {0} WHERE topic = %s;""".format("topic")
            try:
                c.execute(sql, [row.topic])
            except Exception:
                # ignore if the entity did not exist
                pass
    except OperationalError:
        logging.warning('Crate database unavailable')


def sync_tags_to_crate_entity(row, retried=False):
    # we sync points, sites and equipment
    topic = row.topic
    if not topic:
        if row.m_tags and ('site' in row.m_tags or 'equip' in row.m_tags):
            if row.kv_tags:
                topic = row.kv_tags['id']
    if not topic:
        logger.info('sync_tags_to_crate_entity topic or id is empty: %s', row)
        return

    try:
        with connections['crate'].cursor() as c:
            # make sure the topic is in CrateDB
            sql = """INSERT INTO {0} (topic)
            VALUES (%s)""".format("topic")
            try:
                c.execute(sql, [topic])
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
                params_list.append(topic)
                logger.info('sync_tags_to_crate_entity SQL: %s', sql)
                logger.info('sync_tags_to_crate_entity Params: %s', params_list)
                c.execute(sql, params_list)
    except OperationalError:
        logging.warning('Crate database unavailable')


class Status(models.Model):
    status_id = CharField(_("Status ID"), max_length=255, primary_key=True)
    name = CharField(_("Name"), max_length=255)
    type = CharField(_("Type"), max_length=255)
    description = CharField(_("Description"), max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'core_status'

    def __str__(self):
        return self.name


class UnitOfMeasure(models.Model):
    uom_id = CharField(max_length=255, primary_key=True)
    code = CharField(max_length=255)
    symbol = CharField(max_length=255, blank=True, null=True)
    type = CharField(max_length=255)
    description = CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'core_unit_of_measure'

    def __str__(self):
        t = self.description or self.code or self.uom_id
        return t

    @classmethod
    @lru_cache(maxsize=64)
    def get(cls, uom_id):
        return UnitOfMeasure.objects.get(uom_id=uom_id)

    @property
    def unit(self):
        return self.symbol or self.code

    @lru_cache(maxsize=64)
    def conversion_to(self, uom):
        # Lookup the UnitOfMeasureConversion
        n = now()
        cuom = self.conversions_from.filter(from_datetime__lte=n)
        cuom = cuom.exclude(thru_datetime__lte=n)
        cuom = cuom.filter(from_uom_id=self.uom_id)
        cuom = cuom.filter(to_uom_id=uom.uom_id)
        cuom = cuom.first()
        return cuom

    def convert_amount_to(self, amount, uom):
        if (self.uom_id == uom.uom_id):
            return amount
        cuom = self.conversion_to(uom)

        if not cuom:
            raise Exception("Cannot convert UOM {} to {}".format(self, uom))

        return amount * cuom.rate


class UnitOfMeasureConversion(models.Model):
    from_uom = ForeignKey(UnitOfMeasure, related_name='conversions_from', on_delete=models.DO_NOTHING)
    to_uom = ForeignKey(UnitOfMeasure, related_name='conversions_to', on_delete=models.DO_NOTHING)
    from_datetime = DateTimeField(_("From Date"), default=now)
    thru_datetime = DateTimeField(_("Thru Date"), blank=True, null=True)
    rate = FloatField(_("Rate"), null=False)

    class Meta:
        db_table = 'core_unit_of_measure_conversion'


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
        if self.weather_station_code:
            return self.weather_station_code + (" ({name})".format(name=self.station_name) if self.station_name else '')
        else:
            return self.weather_station_id

    def get_absolute_url(self):
        return reverse("core:weather_station_detail", kwargs={"weather_station_id": self.weather_station_id})

    @property
    def latest_reading(self):
        return self.weatherhistory_set.order_by('-as_of_datetime').first()


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


def write_csv_data(qs, output, columns, with_header=True, convert_field=None, convert_uom='uom_id', convert_to=None):
    writer = csv.writer(output)
    header = []
    fields = []
    # check if we want to convert some value field
    convert = False
    if convert_field and convert_uom and convert_to:
        convert = True
    for c in columns:
        header.append(list(c.values())[0])
        fields.append(list(c.keys())[0])
    if with_header:
        writer.writerow(header)
    for d in qs:
        row = []
        for f in fields:
            val = d.__dict__.get(f)
            if convert and convert_field == f:
                # check what uom that field is in
                f_uom_id = d.__dict__.get(convert_uom)
                f_uom = UnitOfMeasure.get(f_uom_id)
                val = f_uom.convert_amount_to(val, convert_to)
            row.append(val)
        writer.writerow(row)


def query_timeseries(qs, start=None, end=None):
    if start:
        qs = qs.filter(as_of_datetime__gte=start)
    if end:
        qs = qs.filter(as_of_datetime__lt=end)
    return qs.order_by('as_of_datetime')


class Meter(models.Model):
    meter_id = CharField(_("Meter ID"), max_length=255, primary_key=True)
    description = CharField(_("Description"), max_length=255, blank=True, null=True)
    weather_station = ForeignKey(WeatherStation, null=True, blank=True, on_delete=models.SET_NULL)
    site = ForeignKey(Entity, on_delete=models.CASCADE)
    from_datetime = DateTimeField(_("From Date"), default=now)
    thru_datetime = DateTimeField(_("Thru Date"), blank=True, null=True)
    rate_plan = ForeignKey('MeterRatePlan', blank=True, null=True, on_delete=models.DO_NOTHING)

    def __str__(self):
        if self.description:
            return "{} ({})".format(self.description, self.meter_id)
        return self.meter_id

    def get_absolute_url(self):
        return reverse("core:meter_detail", kwargs={"meter_id": self.meter_id})

    def get_meter_data(self, start=None, end=None):
        return query_timeseries(self.meterhistory_set, start=start, end=end)

    def get_meter_production_data(self, model_id, start=None, end=None):
        qs = self.meterproduction_set
        qs = qs.filter(Q(**{'meter_production_reference__{}'.format('BaselineModel.id'): model_id}))
        if start:
            qs = qs.filter(from_datetime__gte=start)
        if end:
            qs = qs.filter(from_datetime__lt=end)
        return qs.order_by('from_datetime')

    def get_weather_data(self, start=None, end=None):
        if not self.weather_station:
            return WeatherHistory.objects.none()
        return query_timeseries(self.weather_station.weatherhistory_set, start=start, end=end)

    def write_meter_data_csv(self, output, columns, with_header=True, start=None, end=None, uom=None):
        data = self.get_meter_data(start=start, end=end)
        if not uom:
            first = data.first()
            if first:
                uom = first.uom
        write_csv_data(
            data,
            output,
            columns,
            with_header,
            convert_field='value',
            convert_to=uom)
        # return the uom of the data
        return uom

    def write_weather_data_csv(self, output, columns, with_header=True, start=None, end=None):
        write_csv_data(self.get_weather_data(start=start, end=end), output, columns, with_header)

    def get_data_panda(self):
        # return a pandas.core.frame.DataFrame of the meter data as date .. value
        pass

    def transactions(self):
        qs = FinancialTransaction.objects.filter(meter_id=self.meter_id)
        return qs.order_by('-transaction_datetime')

    @property
    def latest_reading(self):
        return self.meterhistory_set.order_by('-as_of_datetime').first()

    @property
    def latest_value_kwh(self):
        lr = self.latest_reading
        if not lr:
            return None
        kwh_uom = UnitOfMeasure.objects.get(uom_id='energy_kWh')
        return lr.uom.convert_amount_to(lr.value, kwh_uom)


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


class MeterProduction(models.Model):
    meter_production_id = AutoField(_("Meter Production ID"), primary_key=True, auto_created=True)
    meter = ForeignKey(Meter, on_delete=models.CASCADE)
    from_datetime = DateTimeField(_("From Date"), default=now)
    thru_datetime = DateTimeField(_("Thru Date"), blank=True, null=True)
    meter_production_type = CharField(_("Meter Production Type"), max_length=255)
    meter_production_reference = HStoreField(_("Meter Production Reference"), blank=True, null=True)
    error_bands = HStoreField(_("Error Bands"), blank=True, null=True)
    net_value = FloatField(_("Net Value"), null=True)
    model_baseline_value = FloatField(_("Model Baseline Value"), null=True)
    actual_value = FloatField(_("Actual Value"), null=True)
    uom = ForeignKey(UnitOfMeasure, on_delete=models.DO_NOTHING)
    source = CharField(_("Source"), max_length=255)
    created_datetime = DateTimeField(_("Created Date"), default=now)
    created_by_user = ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        db_table = 'core_meter_production'


def day_start_time():
    return time.min


def day_end_time():
    return time.max


class MeterRatePlan(models.Model):
    rate_plan_id = AutoField(_("Rate Plan ID"), primary_key=True, auto_created=True)
    description = CharField(_("Description"), max_length=255)
    params = HStoreField(_("Parameters"), blank=True, null=True)
    from_datetime = DateTimeField(_("From Date"), default=now)
    thru_datetime = DateTimeField(_("Thru Date"), blank=True, null=True)
    billing_frequency_uom = ForeignKey(UnitOfMeasure, on_delete=models.DO_NOTHING, related_name='+', limit_choices_to={'type': 'time_interval'})
    billing_day = IntegerField(_("Billing Day"), default=0)
    source = CharField(_("Source"), max_length=255)
    created_datetime = DateTimeField(_("Created Date"), default=now)
    created_by_user = ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        db_table = 'core_meter_rate_plan'

    def __str__(self):
        if self.description:
            return "{} ({})".format(self.description, self.rate_plan_id)
        return self.rate_plan_id

    def get_absolute_url(self):
        return reverse("core:meter_rate_plan_detail", kwargs={"rate_plan_id": self.rate_plan_id})

    @property
    def currency_uom(self):
        return UnitOfMeasure.objects.get(uom_id=self.params.get('currency_uom_id', 'currency_USD'))

    @property
    def energy_uom(self):
        return UnitOfMeasure.objects.get(uom_id=self.params.get('energy_uom_id', 'energy_kWh'))

    @property
    def flat_rate(self):
        r = self.params.get('flat_rate')
        logging.info("flat_rate = %s", r)
        return float(r)

    def valuate_meter_production(self, meter_production):
        if not self.flat_rate:
            raise Exception("No Flat Rate defined for Meter Rate Plan: {}".format(self))

        r = meter_production.uom.convert_amount_to(meter_production.net_value, self.energy_uom)
        logging.info("valuate_meter_production: flat_rate = %s", self.flat_rate)
        logging.info("valuate_meter_production: meter value = %s", r)
        return r * self.flat_rate

    @classmethod
    def to_day_start(cls, date_time):
        return date_time.replace(hour=0, minute=0, second=0, microsecond=0)

    @classmethod
    def to_day_end(cls, date_time):
        return date_time.replace(hour=23, minute=59, second=59, microsecond=999999)

    def get_billing_period(self, date_time):
        # note billing period can be any valid time_interval: daily,weekly,monthly,quarterly,annually
        # and depends on the billing_day
        # so far a given date_time return the start, end of the corresponding period
        # note: end is given as the start of the next period so the period is the interval [start, end[
        bp = self.billing_frequency_uom.uom_id
        if bp == 'time_interval_daily':
            # daily period is easiest, simply return day start / day end
            start = self.to_day_start(date_time)
            end = start + timedelta(days=1)
            return start, end
        if bp == 'time_interval_weekly':
            # consider billing_day as weekday (0 is Monday)
            start = self.to_day_start(date_time)
            # sanity check
            if self.billing_day < 0 or self.billing_day > 6:
                raise Exception("Invalid billing weekday {} for Meter Rate Plan: {}".format(self.billing_day, self))

            while start.weekday() != self.billing_day:
                start -= timedelta(days=1)
            end = start + timedelta(days=7)
            return start, end
        if bp == 'time_interval_monthly':
            # consider billing_day as day of the month (starting at 1)
            start = self.to_day_start(date_time)
            # sanity check, for now don't handle tricky days of month ..
            if self.billing_day < 0 or self.billing_day > 28:
                raise Exception("Invalid billing day {} for Meter Rate Plan: {}".format(self.billing_day, self))

            if start.day != self.billing_day:
                start = start.replace(day=self.billing_day)
            next_month = start.month + 1
            if next_month > 12:
                next_month = 1
            end = start.replace(month=next_month)
            return start, end
        if bp == 'time_interval_quarterly':
            # consider billing_day as day of the quarter (starting at 1)
            start = self.to_day_start(date_time)
            y = start.year
            # define the quarters, padded by 1 on each end since the
            # billing day can be != 1
            if self.billing_day < 0 or self.billing_day > 92:
                raise Exception("Invalid quarter billing day {} for Meter Rate Plan: {}".format(self.billing_day, self))
            td = timedelta(days=self.billing_day-1)
            quarters = [
                datetime(y-1, 10, 1) + td,
                datetime(y, 1, 1) + td,
                datetime(y, 4, 1) + td,
                datetime(y, 7, 1) + td,
                datetime(y, 10, 1) + td,
                datetime(y+1, 1, 1) + td
                ]

            for i, q in reversed(list(enumerate(quarters))):
                if start > q:
                    return q, quarters[i+1]
            raise Exception("Cannot determine quarter for Meter Rate Plan: {} and date {}".format(self, date_time))
        if bp == 'time_interval_annually':
            # consider billing_day as day of the year (starting at 1)
            start = self.to_day_start(date_time)
            if self.billing_day < 0 or self.billing_day > 365:
                raise Exception("Invalid billing day of year {} for Meter Rate Plan: {}".format(self.billing_day, self))
            doy = start.timetuple().tm_yday
            if doy != self.billing_day:
                start -= timedelta(doy - self.billing_day)
            # need to start at the previous year
            if doy < self.billing_day:
                start = start.replace(year=start.year-1)
            return start, start.replace(year=start.year+1)

        raise Exception("Unsupported billing period {} for Meter Rate Plan: {}".format(bp, self))


class MeterFinancialValue(models.Model):
    meter_value_id = AutoField(_("Meter Value ID"), primary_key=True, auto_created=True)
    meter = ForeignKey(Meter, on_delete=models.DO_NOTHING)
    from_datetime = DateTimeField(_("From Date"), default=now)
    thru_datetime = DateTimeField(_("Thru Date"), blank=True, null=True)
    meter_production_type = CharField(_("Meter Production Type"), max_length=255)
    meter_production_reference = HStoreField(_("Meter Production Reference"), blank=True, null=True)
    amount = FloatField(_("Amount"), null=True)
    # status = ForeignKey(??, on_delete=models.DO_NOTHING)
    uom = ForeignKey(UnitOfMeasure, related_name='+', on_delete=models.DO_NOTHING)
    source = CharField(_("Source"), max_length=255)
    created_datetime = DateTimeField(_("Created Date"), default=now)
    created_by_user = ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        db_table = 'core_meter_financial_value'


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


class FinancialTransaction(models.Model):
    financial_transaction_id = AutoField(_("Financial Transaction ID"), primary_key=True, auto_created=True)
    uom = ForeignKey(UnitOfMeasure, related_name='+', on_delete=models.DO_NOTHING, verbose_name='Currency',
                     limit_choices_to={'type': 'currency'})
    amount = FloatField(_("Amount"))
    meter = ForeignKey(Meter, null=True, blank=True, on_delete=models.DO_NOTHING)
    from_party = ForeignKey(Party, null=True, blank=True, on_delete=models.DO_NOTHING,
                            related_name='financial_transactions_from')
    to_party = ForeignKey(Party, null=True, blank=True, on_delete=models.DO_NOTHING,
                          related_name='financial_transactions_to')
    transaction_datetime = DateTimeField(_("Transaction Date"), default=now)
    from_datetime = DateTimeField(_("Transaction Billing From Date"), default=now)
    thru_datetime = DateTimeField(_("Transaction Billing Thru Date"), null=True, blank=True)
    transaction_type = CharField(_("Transaction Type"), max_length=255)
    status = ForeignKey(Status, related_name='+', on_delete=models.DO_NOTHING,
                        limit_choices_to={'type': 'transaction'})
    source = CharField(_("Source"), max_length=255)
    created_datetime = DateTimeField(_("Created Date"), default=now)
    created_by_user = ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)

    def get_absolute_url(self):
        return reverse("core:transaction_detail", kwargs={"financial_transaction_id": self.financial_transaction_id})

    def can_edit(self):
        # only allow Created transactions to be edited
        return 'transaction_created' == self.status_id

    def can_delete(self):
        return True

    class Meta:
        db_table = 'core_financial_transaction'


class FinancialTransactionNote(models.Model):
    financial_transaction = ForeignKey(FinancialTransaction, on_delete=models.DO_NOTHING)
    content = TextField(_("Comments"), blank=True)
    created = DateTimeField(_("Created Date"), default=now)
    owner = ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)


class FinancialTransactionFile(models.Model):
    financial_transaction = ForeignKey(FinancialTransaction, on_delete=models.DO_NOTHING)
    comments = TextField(_("Comments"), blank=True)
    created = DateTimeField(_("Created Date"), default=now)
    owner = ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    uploaded_file = FilerFileField(null=True, blank=True, related_name="transaction_file", on_delete=models.CASCADE)
    can_thumbnail = BooleanField(default=False)
    link = TextField(blank=True)
    link_name = TextField(blank=True)


class FinancialTransactionHistory(models.Model):
    financial_transaction_history_id = AutoField(_("Financial Transaction History ID"),
                                                 primary_key=True, auto_created=True)
    financial_transaction = ForeignKey(FinancialTransaction, on_delete=models.DO_NOTHING)
    as_of_datetime = DateTimeField(_("History Date"), default=now)
    history = CharField(_("History"), max_length=255, blank=True, null=True)
    created_datetime = DateTimeField(_("Created Date"), default=now)
    created_by_user = ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        db_table = 'core_financial_transaction_history'


# below we want to get the current user from the request in the signal handlers
# so this allows to fetch it from the stack:
def get_current_user_from_stack():
    import inspect
    for frame_record in inspect.stack():
        if frame_record[3] == 'get_response':
            request = frame_record[0].f_locals['request']
            return request.user
    else:
        return None


@receiver(pre_save, sender=FinancialTransaction)
def on_change(sender, instance, raw, using, **kwargs):
    if instance.financial_transaction_id is None:
        # new object will be created
        pass
    else:
        change = ''
        previous = FinancialTransaction.objects.get(financial_transaction_id=instance.financial_transaction_id)
        if previous.status != instance.status:
            change += 'Status changed from {} to {}\n'.format(previous.status, instance.status)
        if previous.amount != instance.amount:
            change += 'Amount changed from {} to {}\n'.format(previous.amount, instance.amount)
        if previous.uom != instance.uom:
            change += 'Currency changed from {} to {}\n'.format(previous.uom, instance.uom)
        if previous.transaction_type != instance.transaction_type:
            change += 'Type changed from {} to {}\n'.format(previous.transaction_type, instance.transaction_type)
        if previous.from_party != instance.from_party:
            change += 'From Party changed from {} to {}\n'.format(previous.from_party, instance.from_party)
        if previous.to_party != instance.to_party:
            change += 'To Party changed from {} to {}\n'.format(previous.to_party, instance.to_party)
        if previous.transaction_type != instance.transaction_type:
            change += 'Type changed from {} to {}\n'.format(previous.transaction_type, instance.transaction_type)
        if previous.source != instance.source:
            change += 'Source changed from {} to {}\n'.format(previous.source, instance.source)
        if previous.meter != instance.meter:
            change += 'Meter changed from {} to {}\n'.format(previous.meter, instance.meter)
        if previous.from_datetime != instance.from_datetime:
            logger.info('on_change : from_datetime from=%s to=%s', previous.from_datetime, instance.from_datetime)
            a = datetime_to_string(previous.from_datetime, tz=get_current_timezone())
            b = datetime_to_string(instance.from_datetime, tz=get_current_timezone())
            if a != b:
                change += 'Billing From Date changed from {} to {}\n'.format(a, b)
        if previous.thru_datetime != instance.thru_datetime:
            a = datetime_to_string(previous.thru_datetime, tz=get_current_timezone())
            b = datetime_to_string(instance.thru_datetime, tz=get_current_timezone())
            if a != b:
                change += 'Billing Thru Date changed from {} to {}\n'.format(a, b)

        if change:
            FinancialTransactionHistory.objects.create(
                financial_transaction_id=instance.financial_transaction_id,
                history=change,
                created_by_user=get_current_user_from_stack())


@receiver(post_delete, sender=FinancialTransactionFile, dispatch_uid='financialtransactionfile_delete_signal')
def financial_transaction_file_deleted(sender, instance, using, **kwargs):
    logger.info('financial_transaction_file_deleted: id=%s uploaded_file=%s', instance.id, instance.uploaded_file_id)
    change = "Removed FinancialTransactionFile {}".format(instance.id)
    if instance.uploaded_file_id:
        c = FinancialTransactionFile.objects.filter(uploaded_file_id=instance.uploaded_file_id).count()
        if c == 0:
            logger.info('entity_file_deleted: file no longer referenced, deleting id=%s', instance.uploaded_file_id)
            FilerFile.objects.get(id=instance.uploaded_file_id).delete()
        change = "Removed file {}".format(instance.uploaded_file.original_filename)
    elif instance.link:
        change = "Removed link {}".format(instance.link)

    FinancialTransactionHistory.objects.create(
        financial_transaction_id=instance.financial_transaction_id,
        history=change,
        created_by_user=get_current_user_from_stack())


@receiver(post_save, sender=FinancialTransactionFile, dispatch_uid='financialtransactionfile_save_signal')
def financial_transaction_file_saved(sender, instance, created, raw, using, **kwargs):
    logger.info('financial_transaction_file_saved: id=%s created=%s', instance.id, created)
    if created:
        change = "Added file"
    else:
        change = "Modified file"

    FinancialTransactionHistory.objects.create(
        financial_transaction_id=instance.financial_transaction_id,
        history=change,
        created_by_user=get_current_user_from_stack())


@receiver(post_delete, sender=FinancialTransactionNote, dispatch_uid='financialtransactionnote_delete_signal')
def financial_transaction_note_deleted(sender, instance, using, **kwargs):
    logger.info('financial_transaction_note_deleted: id=%s', instance.id)
    change = "Removed note"

    FinancialTransactionHistory.objects.create(
        financial_transaction_id=instance.financial_transaction_id,
        history=change,
        created_by_user=get_current_user_from_stack())


@receiver(post_save, sender=FinancialTransactionNote, dispatch_uid='financialtransactionnote_save_signal')
def financial_transaction_note_saved(sender, instance, created, raw, using, **kwargs):
    logger.info('financial_transaction_note_saved: id=%s created=%s', instance.id, created)
    if created:
        change = "Added note"
    else:
        change = "Modified note"

    FinancialTransactionHistory.objects.create(
        financial_transaction_id=instance.financial_transaction_id,
        history=change,
        created_by_user=get_current_user_from_stack())
