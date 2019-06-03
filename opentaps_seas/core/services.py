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

import environ
import os
import json
import logging
from pydoc import locate
from django import forms
from .models import Entity
from . import utils

logger = logging.getLogger(__name__)
ROOT_DIR = environ.Path(__file__) - 2
SERVICEDEF_DIR = os.path.join(ROOT_DIR, 'servicedef')

_SERVICES = {}


class ServiceForm(forms.Form):
    def __init__(self, *args, **kwargs):
        # definition is the paramaters map of the service definition
        # field_name -> {type / default}
        self.service = kwargs.pop('service')
        inputs = self.service.get('input') or {}
        self.inputs = inputs.copy()
        outputs = self.service.get('output') or {}
        self.outputs = outputs.copy()
        super(ServiceForm, self).__init__(*args, **kwargs)

        self.equipment_fields = []
        self.matching_entities = {}
        self.datapoint_fields = []

        for field_name, field in self.inputs.items():
            # field that have a default value, even empty, are optional
            field['required'] = 'default' not in field
            field['name'] = field_name
            if field.get('type') == 'equipment':
                self.equipment_fields.append(field)
            if field.get('type') == 'datapoint':
                self.datapoint_fields.append(field)
            logger.info('ServiceForm preparing field %s : %s', field_name, field)
            self.fields[field_name] = forms.CharField(max_length=255, required=field['required'])

    def apply_entity_rule(self, rule, qs):
        # the rule can be all / id:xxx / site:xxx / tags:xxx / kv_tags:xxx etc ...
        if rule == 'all':
            return qs
        if ':' not in rule:
            return qs.filter(entity_id=rule)
        r, v = rule.split(':', 1)
        if r == 'id' or r == 'entity_id':
            return qs.filter(entity_id=v)
        if r == 'site' or r == 'siteRef':
            return qs.filter(kv_tags__siteRef=v)
        if r == 'equipment' or r == 'equipRef':
            return qs.filter(kv_tags__equipRef=v)
        if r == 'tags':
            tags = [x.strip() for x in v.split(',')]
            return qs.filter(m_tags__contains=tags)
        # else assume a generic kv_tags rule
        k = {'kv_tags__{}'.format(r): v}
        return qs.filter(**k)

    def get_matching_entities(self, field_name):
        if field_name in self.matching_entities:
            return self.matching_entities[field_name]

        # add a basic filter by "type" of the defined field
        d = self.inputs.get(field_name)
        if not d:
            return Entity.objects.none()
        dt = d.get('type')
        qs = Entity.objects.all()
        if 'equipment' == dt:
            qs = qs.filter(m_tags__contains=['equip'])
        elif 'datapoint' == dt:
            qs = qs.filter(m_tags__contains=['point'])
        elif 'site' == dt:
            qs = qs.filter(m_tags__contains=['site'])
        elif 'entity' != dt:
            return Entity.objects.none()

        return self.apply_entity_rule(self.cleaned_data[field_name], qs)

    def get_matching_equipments(self, field_name='equipment'):
        return self.get_matching_entities(field_name)

    def create_outputs(self, context):
        logger.info('ServiceForm create_outputs with context: %s', context)
        for field_name, field in self.outputs.items():
            if field.get('type') == 'datapoint':
                p_name = field_name
                if field.get('name'):
                    p_name = field.get('name')
                topic = field.get('topic')
                tags = field.get('tags')
                # do context substitution
                if topic:
                    logger.info('ServiceForm format topic: %s', topic)
                    topic = topic.format(**context)
                if p_name:
                    logger.info('ServiceForm format name: %s', p_name)
                    p_name = p_name.format(**context)
                if tags:
                    logger.info('ServiceForm format tags: %s', tags)
                    tags = tags.format(**context)
                # check if the datapoint exists
                point = Entity.objects.filter(m_tags__contains=['point']).filter(topic=topic)
                if point:
                    point = point[0]
                else:
                    entity_id = utils.make_random_id(topic)
                    point = Entity(entity_id=entity_id, topic=topic)
                    point.add_tag('point', commit=False)
                # setup
                point.add_tag('dis', p_name, commit=False)
                for tag in [x.strip() for x in tags.split(',')]:
                    k_v = [x.strip() for x in tag.split(':', 1)]
                    if len(k_v) > 1:
                        point.add_tag(k_v[0], k_v[1], commit=False)
                    else:
                        point.add_tag(k_v[0], commit=False)
                logger.info('ServiceForm create_outputs saving datapoint %s : %s', field_name, point)
                point.save()

            else:
                raise Exception('create_outputs: Unsupported output {}'.format(field))


def load_services():
    logger.info('load_services from %s ...', SERVICEDEF_DIR)
    _SERVICES.clear()
    for root, dirs, files in os.walk(SERVICEDEF_DIR):
        logger.info('load_services in %s, %s, %s', root, dirs, files)
        for file in files:
            if file.endswith(".json"):
                logger.info('will load file %s', os.path.join(SERVICEDEF_DIR, file))
                with open(os.path.join(SERVICEDEF_DIR, file)) as f:
                    content = json.loads(f.read())
                    logger.info('loading services %s', content)
                    _SERVICES.update(content)
    return _SERVICES


def get_service(service_name):
    logger.info('get_service %s ...', service_name)
    service = _SERVICES.get(service_name)
    if not service:
        logger.info('try loading services again ...')
        load_services()
        service = _SERVICES.get(service_name)
    logger.info('get_service returning %s', service)
    return service


def run_service(service_name, params):
    logger.info('run_service %s with %s', service_name, params)
    service = get_service(service_name)
    if not service:
        raise Exception('Service not found {}'.format(service_name))
    # locate the service implementation
    Service = locate(service.get('engine'))
    # load the default parameter values from the service definition
    parameters = {}
    definition = service.get('input', {})
    for k, v in definition.items():
        if 'default' in v:
            parameters[k] = v.get('default')
    # merge with the given parameters
    if params:
        parameters.update(params)
    service = Service(parameters, service=service)
    if not service.execute:
        raise Exception('Service {} does not have an "execute" method at {}'.format(service_name, service.engine))
    return service.execute()
