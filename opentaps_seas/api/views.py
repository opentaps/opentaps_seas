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

import json

from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from opentaps_seas.core.models import (
    Entity, Topic, SiteView, Tag
)

import logging
import traceback

# Get an instance of a logger
logger = logging.getLogger(__name__)


class TagImportView(APIView):
    permission_classes = (IsAuthenticated,)
    interval = 300

    def post(self, request, site_entity_id):
        # get site id from request
        try:
            site = SiteView.objects.get(entity_id=site_entity_id)
        except SiteView.DoesNotExist:
            err = 'Site does not exist: {}'.format(site_entity_id)
            logger.error(err)
            return Response({'error': err}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # check json file attached or not
        file = request.FILES.get('data', None)
        if file:
            if not file.name.endswith('.json'):
                logger.error('File should be json')
                return Response(
                    {'error': 'File should be json'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            else:
                try:
                    data = json.loads(file.read())
                except json.JSONDecodeError:
                    logger.error('Invalid json format')
                    return Response(
                        {'error': traceback.format_exc()},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
        else:
            # get topic data from request
            data = request.data

        logger.info('Read Json successfully! Start parse...')

        for d_address, d_value in data.items():
            device_name = None
            device_id = None
            device = d_value.get('device', {})
            if device:
                for key, value in device.items():
                    device_id = key
                    if value and value.get('objectName', None):
                        device_name = value.get('objectName', None)
                        if device_name:
                            device_name = device_name.strip()

            # get device_name and device_id
            if not device_name:
                device_name = d_value.get('device_name', None)
            if not device_id:
                device_id = str(d_value.get('device_id', None))

            if not device_id:
                logger.error('Device id not defined. Device Address is {}'.format(d_address))
                return Response(
                    {'error': 'Device id not defined. Invalid json structure'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            device_description = device.get(device_id, {}).get('description', None)
            if device_description:
                device_description = device_description.strip()

            object_name = device.get(device_id, {}).get('objectName', None)
            if object_name:
                object_name = object_name.strip()

            if not device_description and object_name:
                device_description = object_name

            for o_type, o_value in d_value.items():
                if o_type not in ['device', 'device_id', 'device_name']:  # detect meta data
                    for o_id, tags in o_value.items():
                        topic_name = '{site_id}/{device_id}/{o_type}/{o_id}'.format(
                            site_id=site_entity_id,
                            device_id=device_id,
                            o_type=o_type,
                            o_id=o_id
                        )

                        entity_id = topic_name.replace('/', '-')

                        logger.info('Start: Create topic - {}'.format(topic_name))

                        # check topic exists
                        Topic.ensure_topic_exists(topic_name)

                        # get all available tags
                        kv_tags = dict()
                        kv_tags['id'] = topic_name
                        kv_tags['siteRef'] = site.object_id
                        kv_tags['bacnet_volttron_point_name'] = topic_name
                        kv_tags['bacnet_device_address'] = d_address
                        kv_tags['bacnet_device_id'] = device_id
                        kv_tags['bacnet_device_name'] = device_name
                        kv_tags['bacnet_device_description'] = device_description
                        kv_tags['bacnet_bacnet_object_type'] = o_type
                        kv_tags['bacnet_object_index'] = o_id
                        kv_tags['bacnet_prefix'] = device_id
                        kv_tags['interval'] = self.interval  # default 300 for now
                        kv_tags['dis'] = topic_name

                        for t_id, t_v in tags.items():
                            if t_v:
                                t_v = t_v.replace(u"\u0000", "")
                                tag_name = 'bacnet_{}'.format(t_id)
                                kv_tags[tag_name] = t_v.encode('ascii', 'ignore').decode('utf-8')
                                self.ensure_tag_exists(tag_name)

                        try:
                            topic = Entity.objects.get(topic=topic_name)
                            for tag, value in topic.kv_tags.items():
                                topic.add_tag(tag, value)

                            logger.info('End: Update topic - {}'.format(topic_name))
                        except Entity.DoesNotExist:
                            topic = Entity(
                                entity_id=entity_id,
                                topic=topic_name,
                                m_tags=['point'],
                                kv_tags=kv_tags
                            )
                            logger.info('End: Create topic - {}'.format(topic_name))

                        topic.save()

        return Response({'success': 'success'})

    def ensure_tag_exists(self, tag_name):
        try:
            tag = Tag.objects.get(tag=tag_name)
        except Tag.DoesNotExist:
            tag = Tag(tag=tag_name, kind='Str')
            tag.save()


class TagExportView(APIView):
    permission_classes = (IsAuthenticated,)

    @staticmethod
    def get(request, site_entity_id):
        try:
            site = SiteView.objects.get(entity_id=site_entity_id)
        except SiteView.DoesNotExist:
            err = 'Site does not exist: {}'.format(site_entity_id)
            logger.error(err)
            return Response({'error': err}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        logger.info('TagExportView: for Site {}'.format(site.object_id))

        data = dict()
        topics = Entity.objects.filter(
            kv_tags__siteRef=site.object_id,
            m_tags__contains=['point', 'his'],
            kv_tags__bacnet_prefix__isnull=False
        )

        for topic in topics:
            tag_object = dict()
            tag_object['topic'] = topic.topic
            tag_object['point_name'] = topic.entity_id
            tag_object['writable'] = False
            tag_object['write_priority'] = ''

            for tag, value in topic.kv_tags.items():
                if tag not in [
                    'bacnet_device_id',
                    'bacnet_device_address',
                    'bacnet_device_name',
                    'bacnet_device_description',
                    'bacnet_prefix',
                    'interval',
                    'id'
                ]:
                    tag_object[tag.replace('bacnet_', '')] = value

            device_id = topic.kv_tags['bacnet_device_id']
            interval = topic.kv_tags['interval']
            if device_id not in data:
                d_addr = topic.kv_tags['bacnet_device_address']
                d_name = topic.kv_tags['bacnet_device_name']
                data[device_id] = {'intervals': {}, 'metadata': {'device_addr': d_addr, 'device_name': d_name}}

            if interval not in data[device_id]['intervals']:
                data[device_id]['intervals'][interval] = []

            data[device_id]['intervals'][interval].append(
                tag_object
            )
        return Response(data, status=status.HTTP_200_OK)
