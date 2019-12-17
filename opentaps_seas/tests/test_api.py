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

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.db import connections
from opentaps_seas.core.models import (
    Entity, Tag,
)


class TopicRestAPITests(TestCase):

    topic_import_url = reverse('api:topic_import', kwargs={'site_entity_id': '_test_site'})
    topic_export_url = reverse('api:topic_export', kwargs={'site_entity_id': '_test_site'})

    def setUp(self):
        # create site
        Entity.objects.get_or_create(entity_id='_test_site', defaults={'m_tags': ['site'],
                                                                       'kv_tags': {'id': '_test_site'}})

        # create tags
        m_tags = ['his', 'point', 'rooftop', 'ac', 'ahu', 'zone', 'temp']
        kv_tags = ['siteRef', 'appName', 'unit']
        for tag in m_tags:
            Tag.objects.get_or_create(tag=tag, defaults={
                'kind': 'Marker',
                'description': 'This is a test Tag'
            })
        for tag in kv_tags:
            Tag.objects.get_or_create(tag=tag, defaults={
                'kind': 'String',
                'description': 'This is a test Tag'
            })

        get_user_model().objects.create_user('temporary', 'temporary@gmail.com', 'temporary')

    def tearDown(self):
        self._cleanup_data()

    @staticmethod
    def _cleanup_data():
        # delete test data from postgres
        Entity.objects.filter(entity_id__startswith='_test').delete()

        # delete test data for CrateDB
        with connections['crate'].cursor() as c:
            sql = """DELETE FROM {0} WHERE topic like %s""".format("topic")
            c.execute(sql, ['_test%'])
            sql = """DELETE FROM {0} WHERE topic like %s""".format("data")
            c.execute(sql, ['_test%'])

            c.close()

    def _login(self):
        credentials = {
            'username': 'temporary',
            'password': 'temporary'
        }
        response = self.client.post(reverse('token_obtain_pair'), credentials)
        token_json = json.loads(response.content)
        return token_json['access']

    def test_topic_import_export_require_security(self):
        unauthorized_response = {
            'detail': 'Authentication credentials were not provided.'
        }
        # topic import api without security params
        response = self.client.post(self.topic_import_url)

        self.assertNotEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), unauthorized_response)

        # topic import api without security params
        response = self.client.get(self.topic_export_url)

        self.assertNotEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), unauthorized_response)

    def test_topic_import_export(self):
        token = self._login()
        header = {
            'HTTP_AUTHORIZATION': 'Bearer {}'.format(token)
        }

        # prepare import topics json
        topics = {
            "10.0.0.1": {
                "binaryOutput": {
                    "8": {
                        "presentValue": "test present",
                        "description": "test description",
                        "objectName": "test object name"
                    }
                },
                "multiStateInput": {
                    "135998": {
                        "stateText": "test state text",
                        "presentValue": "11",
                        "description": "test description",
                        "objectName": "test object name"
                    }
                },
                "device": {
                    "922001": {
                        "description": "BACnet EnOcean Gateway",
                        "objectName": "MES eBox 2.0"
                    }
                },
                "device_name": "MES eBox 2.0",
                "device_id": "922001"
            },
            "10.0.0.2": {
                "binaryOutput": {
                    "8": {
                        "presentValue": "test present",
                        "description": "test description",
                        "objectName": "test object name"
                    }
                },
                "multiStateInput": {
                    "135998": {
                        "stateText": "test state text",
                        "presentValue": "11",
                        "description": "test description",
                        "objectName": "test object name"
                    }
                },
                "device": {
                    "922002": {
                        "description": "BACnet EnOcean Gateway",
                        "objectName": "MES eBox 2.0"
                    }
                },
                "device_name": "MES eBox 2.0",
                "device_id": "922002"
            }
        }

        response = self.client.post(
            self.topic_import_url, json.dumps(topics), content_type='application/json', **header
        )

        self.assertEqual(json.loads(response.content), {'success': 'success'})

        response = self.client.get(self.topic_export_url, **header)
        self.assertEqual(response.status_code, 200)

        json_resp = json.loads(response.content)
        self.assertEqual(json_resp, {})

        # add 'his' tag
        point = Entity.objects.get(
            topic="_test_site/922001/binaryOutput/8",
            m_tags=["point"]
        )
        self.assertIsNotNone(point)
        point.add_tag('his', commit=True)

        point = Entity.objects.get(
            topic="_test_site/922001/multiStateInput/135998",
            m_tags=["point"]
        )
        self.assertIsNotNone(point)
        point.add_tag('his', commit=True)

        point = Entity.objects.get(
            topic="_test_site/922002/binaryOutput/8",
            m_tags=["point"]
        )
        self.assertIsNotNone(point)
        point.add_tag('his', commit=True)

        point = Entity.objects.get(
            topic="_test_site/922002/multiStateInput/135998",
            m_tags=["point"]
        )
        self.assertIsNotNone(point)
        point.add_tag('his', commit=True)

        response = self.client.get(self.topic_export_url, **header)
        self.assertEqual(response.status_code, 200)

        json_resp = json.loads(response.content)

        self.assertIsNotNone(json_resp.get('922001'))
        self.assertIsNotNone(json_resp.get('922001').get('intervals'))
        self.assertIsNotNone(json_resp.get('922001').get('intervals').get('300'))
        arr = json_resp.get('922001').get('intervals').get('300')
        self.assertEqual(len(arr), 2)

        self.assertEqual(arr[0].get('topic', None), '_test_site/922001/binaryOutput/8')
        self.assertEqual(arr[0].get('point_name', None), '_test_site/922001/binaryOutput/8')
        self.assertEqual(arr[0].get('writable', None), False)
        self.assertEqual(arr[0].get('write_priority', None), '')
        self.assertEqual(arr[0].get('objectName', None), 'test object name')
        self.assertEqual(arr[0].get('description', None), 'test description')
        self.assertEqual(arr[0].get('object_type', None), 'binaryOutput')
        self.assertEqual(arr[0].get('presentValue', None), 'test present')
        self.assertEqual(arr[0].get('siteRef', None), '_test_site')

        self.assertEqual(arr[1].get('topic', None), '_test_site/922001/multiStateInput/135998')
        self.assertEqual(arr[1].get('point_name', None), '_test_site/922001/multiStateInput/135998')
        self.assertEqual(arr[1].get('writable', None), False)
        self.assertEqual(arr[1].get('write_priority', None), '')
        self.assertEqual(arr[1].get('stateText', None), 'test state text')
        self.assertEqual(arr[1].get('objectName', None), 'test object name')
        self.assertEqual(arr[1].get('description', None), 'test description')
        self.assertEqual(arr[1].get('object_type', None), 'multiStateInput')
        self.assertEqual(arr[1].get('presentValue', None), '11')
        self.assertEqual(arr[1].get('siteRef', None), '_test_site')

        self.assertIsNotNone(json_resp.get('922002'))
        self.assertIsNotNone(json_resp.get('922002').get('intervals'))
        self.assertIsNotNone(json_resp.get('922002').get('intervals').get('300'))
        arr = json_resp.get('922002').get('intervals').get('300')
        self.assertEqual(len(arr), 2)

        self.assertEqual(arr[0].get('topic', None), '_test_site/922002/binaryOutput/8')
        self.assertEqual(arr[0].get('point_name', None), '_test_site/922002/binaryOutput/8')
        self.assertEqual(arr[0].get('writable', None), False)
        self.assertEqual(arr[0].get('write_priority', None), '')
        self.assertEqual(arr[0].get('objectName', None), 'test object name')
        self.assertEqual(arr[0].get('description', None), 'test description')
        self.assertEqual(arr[0].get('object_type', None), 'binaryOutput')
        self.assertEqual(arr[0].get('presentValue', None), 'test present')
        self.assertEqual(arr[0].get('siteRef', None), '_test_site')

        self.assertEqual(arr[1].get('topic', None), '_test_site/922002/multiStateInput/135998')
        self.assertEqual(arr[1].get('point_name', None), '_test_site/922002/multiStateInput/135998')
        self.assertEqual(arr[1].get('writable', None), False)
        self.assertEqual(arr[1].get('write_priority', None), '')
        self.assertEqual(arr[1].get('stateText', None), 'test state text')
        self.assertEqual(arr[1].get('objectName', None), 'test object name')
        self.assertEqual(arr[1].get('description', None), 'test description')
        self.assertEqual(arr[1].get('object_type', None), 'multiStateInput')
        self.assertEqual(arr[1].get('presentValue', None), '11')
        self.assertEqual(arr[1].get('siteRef', None), '_test_site')
