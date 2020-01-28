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
import json
import time

from .base import OpentapsSeasTestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.db import connections
from opentaps_seas.core.models import (
    Entity, Tag, Topic, TopicTagRuleSet, TopicTagRule
)

logger = logging.getLogger(__name__)


class TopicAPITests(OpentapsSeasTestCase):

    topic_list_url = reverse('core:topic_json')

    def setUp(self):
        # create site
        Entity.objects.get_or_create(entity_id='_test_filters_site', defaults={'m_tags': ['site'], 'kv_tags': {}})

        # create unmapped topics (without a related Entity)
        Topic.ensure_topic_exists('_test_unmapped/um1/some_topic')
        Topic.ensure_topic_exists('_test_unmapped/um1/another_topic')
        Topic.ensure_topic_exists('_test_unmapped/um2/ahu')
        Topic.ensure_topic_exists('_test_unmapped/um2/zone_temp')
        # add a couple of mapped ones that will match the same filters
        Topic.ensure_topic_exists('_test_mapped/um1/some_topic')
        Topic.ensure_topic_exists('_test_mapped/um1/another_topic')

        # ensure topic exists
        Topic.ensure_topic_exists('_test_filters/foo/some_topic')
        Topic.ensure_topic_exists('_test_filters/bar/another_topic')
        Topic.ensure_topic_exists('_test_filters/foo/an_ac')
        Topic.ensure_topic_exists('_test_filters/bar/ahu')
        Topic.ensure_topic_exists('_test_filters/bar/zone_temp')

        Topic.ensure_topic_exists('_test_Position_Command|vav-100')
        Topic.ensure_topic_exists('_test_Position_Size|vav-100')
        Topic.ensure_topic_exists('_test_Position_Command|vav-101')
        Topic.ensure_topic_exists('_test_Position_Size|vav-101')

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

        # create entities
        Entity.objects.get_or_create(
            entity_id="_test_mapped/um1/some_topic",
            topic="_test_mapped/um1/some_topic",
            m_tags=["his", "point"],
            kv_tags={
                'siteRef': 'test_filters_site',
                'appName': 'test_mapped'
            }
        )
        Entity.objects.get_or_create(
            entity_id="_test_mapped/um1/another_topic",
            topic="_test_mapped/um1/another_topic",
            m_tags=["his", "point"],
            kv_tags={
                'siteRef': 'test_filters_site',
                'appName': 'test_mapped'
            }
        )
        Entity.objects.get_or_create(
            entity_id="_test_filters/foo/some_topic",
            topic="_test_filters/foo/some_topic",
            m_tags=["his", "point"],
            kv_tags={
                'siteRef': 'test_filters_site',
                'appName': 'test_foo_1'
            }
        )
        Entity.objects.get_or_create(
            entity_id="_test_filters/bar/another_topic",
            topic="_test_filters/bar/another_topic",
            m_tags=["his", "point", "ac"],
            kv_tags={
                'siteRef': 'test_filters_site',
                'appName': 'test_bar_1'
            }
        )
        Entity.objects.get_or_create(
            entity_id="_test_filters/foo/an_ac",
            topic="_test_filters/foo/an_ac",
            m_tags=["his", "point", "ac"],
            kv_tags={
                'siteRef': 'test_filters_site',
                'appName': 'test_foo'
            }
        )
        Entity.objects.get_or_create(
            entity_id="_test_filters/bar/ahu",
            topic="_test_filters/bar/ahu",
            m_tags=["his", "point", "ahu", "rooftop"],
            kv_tags={
                'siteRef': 'test_filters_site',
                'appName': 'test_bar'
            }
        )
        Entity.objects.get_or_create(
            entity_id="_test_filters/bar/zone_temp",
            topic="_test_filters/bar/zone_temp",
            m_tags=["his", "point", "zone", "temp"],
            kv_tags={
                'siteRef': 'test_filters_site',
                'appName': 'test_bar',
                'unit': 'celsius'
            }
        )

        Entity.objects.get_or_create(
            entity_id="_test_Position_Command|vav-100",
            topic="_test_Position_Command|vav-100",
            m_tags=["his", "point", "zone", "temp"],
            kv_tags={
                'siteRef': 'test_filters_site',
                'appName': 'test_bar',
                'unit': 'celsius'
            }
        )
        Entity.objects.get_or_create(
            entity_id="_test_Position_Size|vav-100",
            topic="_test_Position_Size|vav-100",
            m_tags=["his", "point", "zone", "temp"],
            kv_tags={
                'siteRef': 'test_filters_site',
                'appName': 'test_bar',
                'unit': 'celsius'
            }
        )
        Entity.objects.get_or_create(
            entity_id="_test_Position_Command|vav-101",
            topic="_test_Position_Command|vav-101",
            m_tags=["his", "point", "zone", "temp"],
            kv_tags={
                'siteRef': 'test_filters_site',
                'appName': 'test_bar',
                'unit': 'celsius'
            }
        )
        Entity.objects.get_or_create(
            entity_id="_test_Position_Size|vav-101",
            topic="_test_Position_Size|vav-101",
            m_tags=["his", "point", "zone", "temp"],
            kv_tags={
                'siteRef': 'test_filters_site',
                'appName': 'test_bar',
                'unit': 'celsius'
            }
        )

        # create model
        Entity.objects.create(
            entity_id='_test_model',
            m_tags=['model'],
            kv_tags={
                'id': '_test_model',
                'dis': 'description'
            }
        )

        get_user_model().objects.create_user('temporary', 'temporary@gmail.com', 'temporary')

        time.sleep(1)

    def tearDown(self):
        self._cleanup_data()

    @staticmethod
    def _cleanup_data():
        # delete test data from postgres
        Entity.objects.filter(entity_id__startswith='_test').delete()
        TopicTagRule.objects.filter(name__contains='test').delete()
        TopicTagRuleSet.objects.filter(name__contains='test').delete()

        # delete test data for CrateDB
        with connections['crate'].cursor() as c:
            sql = """DELETE FROM {0} WHERE topic like %s""".format("topic")
            c.execute(sql, ['_test%'])
            sql = """DELETE FROM {0} WHERE topic like %s""".format("data")
            c.execute(sql, ['_test%'])

    def _get_response(self, params):
        return self.client.post(self.topic_list_url + '?page=1&per_page=10', params)

    def _check_topic_list(self, response, c_list, nc_list):
        json_resp = json.loads(response.content)
        self.assertNotEqual(json_resp, {})
        data_topics = []
        for item in json_resp['data']:
            data_topics.append(item['topic'])
        try:
            for entity in c_list:
                self.assertIn(entity, data_topics)
            for entity in nc_list:
                self.assertNotIn(entity, data_topics)
        except Exception:
            logging.error('_check_topic_list ERROR: c_list %s', c_list)
            logging.error('_check_topic_list ERROR: nc_list %s', nc_list)
            logging.error('_check_topic_list ERROR: check response %s', json_resp['data'])
            logging.error('_check_topic_list ERROR: check response topics %s', data_topics)
            logger.exception('_check_topic_list error')
            raise

    def _login(self):
        self.client.login(username='temporary', password='temporary')

    def test_topics_filter_unmapped(self):
        self._login()

        # ----------- start test n0="Topic" t0="c" f0="mapped" ----------- #
        c_list = [
            '_test_unmapped/um1/some_topic',
            '_test_unmapped/um1/another_topic',
            '_test_unmapped/um2/ahu',
            '_test_unmapped/um2/zone_temp',
            '_test_mapped/um1/some_topic',
            '_test_mapped/um1/another_topic'
        ]
        nc_list = [
            '_test_filters/foo/some_topic',
            '_test_filters/foo/an_ac',
            '_test_filters/bar/another_topic',
            '_test_filters/bar/ahu',
            '_test_filters/bar/zone_temp'
        ]

        # filter data
        data = {
            'n0': 'Topic',
            't0': 'c',
            'f0': 'mapped',
            'filters_count': 1
        }

        response = self._get_response(data)
        self._check_topic_list(response, c_list, nc_list)

        c_list = [
            '_test_unmapped/um1/some_topic',
            '_test_unmapped/um1/another_topic',
            '_test_unmapped/um2/ahu',
            '_test_unmapped/um2/zone_temp'
        ]
        nc_list = [
            '_test_mapped/um1/some_topic',
            '_test_mapped/um1/another_topic'
            '_test_filters/foo/some_topic',
            '_test_filters/foo/an_ac',
            '_test_filters/bar/another_topic',
            '_test_filters/bar/ahu',
            '_test_filters/bar/zone_temp'
        ]

        # filter data
        data = {
            'n0': 'Topic',
            't0': 'c',
            'f0': 'mapped',
            'filters_count': 1,
            'select_not_mapped_topics': 1
        }

        response = self._get_response(data)
        self._check_topic_list(response, c_list, nc_list)

    def test_topics_filter(self):
        self._login()

        # ----------- start test n0="Topic" t0="c" f0="test" ----------- #
        c_list = [
            '_test_filters/foo/some_topic',
            '_test_filters/foo/an_ac',
            '_test_filters/bar/another_topic',
            '_test_filters/bar/ahu',
            '_test_filters/bar/zone_temp'
        ]
        nc_list = []

        # filter data
        data = {
            'n0': 'Topic',
            't0': 'c',
            'f0': 'test',
            'filters_count': 1
        }
        response = self._get_response(data)
        self._check_topic_list(response, c_list, nc_list)

        # ----------- start test n0="Topic" t0="c" f0="bar" ----------- #
        c_list = [
            '_test_filters/bar/another_topic',
            '_test_filters/bar/ahu',
            '_test_filters/bar/zone_temp'
        ]
        nc_list = [
            '_test_filters/foo/some_topic',
            '_test_filters/foo/an_ac'
        ]

        # filter data
        data = {
            'n0': 'Topic',
            't0': 'c',
            'f0': 'bar',
            'filters_count': 1
        }
        response = self._get_response(data)
        self._check_topic_list(response, c_list, nc_list)

        # ----------- start test n0="Topic" t0="c" f0="foo" ----------- #
        c_list = [
            '_test_filters/foo/some_topic',
            '_test_filters/foo/an_ac'
        ]
        nc_list = [
            '_test_filters/bar/another_topic',
            '_test_filters/bar/ahu',
            '_test_filters/bar/zone_temp'
        ]

        # filter data
        data = {
            'n0': 'Topic',
            't0': 'c',
            'f0': 'foo',
            'filters_count': 1
        }
        response = self._get_response(data)
        self._check_topic_list(response, c_list, nc_list)

        # ----------- start test n0="Topic" t0="c" f0="bar" n1="zone" t1="present" ----------- #
        c_list = [
            '_test_filters/bar/zone_temp'
        ]
        nc_list = [
            '_test_filters/foo/some_topic',
            '_test_filters/foo/an_ac',
            '_test_filters/bar/another_topic',
            '_test_filters/bar/ahu',
        ]

        # filter data
        data = {
            'n0': 'Topic',
            't0': 'c',
            'f0': 'bar',
            'n1': 'zone',
            't1': 'present',
            'filters_count': 2
        }
        response = self._get_response(data)
        self._check_topic_list(response, c_list, nc_list)

        # ----------- start test n0="Topic" t0="c" f0="foo" n1="ac" t1="absent" ----------- #
        c_list = [
            '_test_filters/foo/some_topic'
        ]
        nc_list = [
            '_test_filters/foo/an_ac',
            '_test_filters/bar/another_topic',
            '_test_filters/bar/ahu',
            '_test_filters/bar/zone_temp'
        ]

        # filter data
        data = {
            'n0': 'Topic',
            't0': 'c',
            'f0': 'foo',
            'n1': 'ac',
            't1': 'absent',
            'filters_count': 2
        }
        response = self._get_response(data)
        self._check_topic_list(response, c_list, nc_list)

        # ----------- start test n0="Topic" t0="c" f0="FOO" n1="ac" t1="absent" (Case Insensitive)----------- #
        c_list = [
            '_test_filters/foo/some_topic',
        ]
        nc_list = [
            '_test_filters/foo/an_ac'
            '_test_filters/bar/another_topic',
            '_test_filters/bar/ahu',
            '_test_filters/bar/zone_temp'
        ]

        # filter data
        data = {
            'n0': 'Topic',
            't0': 'c',
            'f0': 'FOO',
            'n1': 'ac',
            't1': 'absent',
            'filters_count': 2
        }
        response = self._get_response(data)
        self._check_topic_list(response, c_list, nc_list)

        # ----------- start test n0="Topic" t0="c" f0="test_filters" ----------- #
        c_list = [
            '_test_filters/foo/some_topic',
            '_test_filters/foo/an_ac',
            '_test_filters/bar/another_topic',
            '_test_filters/bar/ahu',
            '_test_filters/bar/zone_temp'
        ]
        nc_list = []

        # filter data
        data = {
            'n0': 'Topic',
            't0': 'c',
            'f0': 'test_filters',
            'filters_count': 1
        }
        response = self._get_response(data)
        self._check_topic_list(response, c_list, nc_list)

        # ----------- start test n0="Topic" t0="c" f0="test_filters" n1="appName" t1="eq" f1="test_foo" ----------- #
        c_list = [
            '_test_filters/foo/an_ac'
        ]
        nc_list = [
            '_test_filters/foo/some_topic',
            '_test_filters/bar/another_topic',
            '_test_filters/bar/ahu',
            '_test_filters/bar/zone_temp'
        ]

        # filter data
        data = {
            'n0': 'Topic',
            't0': 'c',
            'f0': 'test_filters',
            'n1': 'appName',
            't1': 'eq',
            'f1': 'test_foo',
            'filters_count': 2
        }
        response = self._get_response(data)
        self._check_topic_list(response, c_list, nc_list)

        # ----------- start test n0="Topic" t0="c" f0="test_filters" n1="appName" t1="neq" f1="test_foo" ----------- #
        c_list = [
            '_test_filters/foo/some_topic',
            '_test_filters/bar/another_topic',
            '_test_filters/bar/ahu',
            '_test_filters/bar/zone_temp'
        ]
        nc_list = [
            '_test_filters/foo/an_ac'
        ]

        # filter data
        data = {
            'n0': 'Topic',
            't0': 'c',
            'f0': 'test_filters',
            'n1': 'appName',
            't1': 'neq',
            'f1': 'test_foo',
            'filters_count': 2
        }
        response = self._get_response(data)
        self._check_topic_list(response, c_list, nc_list)

        # ----------- start test n0="Topic" t0="c" f0="test_filters" n1="appName" t1="neq" f1="test_foo"; n2="zone"
        # t2="present" n3="ac" t3="absent" n4="unit" t4="eq" f4="celsius" ----------- #
        c_list = [
            '_test_filters/bar/zone_temp'
        ]
        nc_list = [
            '_test_filters/foo/some_topic',
            '_test_filters/foo/an_ac',
            '_test_filters/bar/another_topic',
            '_test_filters/bar/ahu'
        ]

        # filter data
        data = {
            'n0': 'Topic',
            't0': 'c',
            'f0': 'test_filters',
            'n1': 'appName',
            't1': 'neq',
            'f1': 'test_foo',
            'n2': 'zone',
            't2': 'present',
            'n3': 'ac',
            't3': 'absent',
            'n4': 'unit',
            't4': 'eq',
            'f4': 'celsius',
            'filters_count': 5
        }
        response = self._get_response(data)
        self._check_topic_list(response, c_list, nc_list)

        # ----------- start test for OR queries ----------- #
        c_list = []
        nc_list = [
            '_test_filters/foo/some_topic',
            '_test_filters/bar/another_topic',
            '_test_filters/foo/an_ac',
            '_test_filters/bar/zone_temp'
            '_test_filters/bar/ahu'
        ]

        # filter data, first using ANDs which returns nothing
        data = {
            'n0': 'Topic',
            't0': 'c',
            'f0': 'test_filters',
            'n1': 'Topic',
            't1': 'c',
            'f1': 'topic',
            'n2': 'Topic',
            't2': 'c',
            'f2': 'foo',
            'n3': 'Topic',
            't3': 'c',
            'f3': 'bar',
            'filters_count': 4
        }
        response = self._get_response(data)
        self._check_topic_list(response, c_list, nc_list)

        c_list = [
            '_test_filters/foo/some_topic',
            '_test_filters/bar/another_topic',
        ]
        nc_list = [
            '_test_filters/foo/an_ac',
            '_test_filters/bar/zone_temp'
            '_test_filters/bar/ahu'
        ]

        # filter data, now using foo OR bar which returns 2 (A and B and (C or D))
        data = {
            'n0': 'Topic',
            't0': 'c',
            'f0': 'test_filters',
            'n1': 'Topic',
            't1': 'c',
            'f1': 'topic',
            'n2': 'Topic',
            't2': 'c',
            'f2': 'foo',
            'n3': 'Topic',
            't3': 'c',
            'f3': 'bar',
            'filters_count': 4,
            'o3': 'OR'
        }
        response = self._get_response(data)
        self._check_topic_list(response, c_list, nc_list)

        # filter data, change the order (A and (B or C) and D)
        data = {
            'n0': 'Topic',
            't0': 'c',
            'f0': 'test_filters',
            'o0': 'AND',
            'n1': 'Topic',
            't1': 'c',
            'f1': 'foo',
            'o1': 'OR',
            'n2': 'Topic',
            't2': 'c',
            'f2': 'bar',
            'o2': 'OR',
            'n3': 'Topic',
            't3': 'c',
            'f3': 'topic',
            'o3': 'AND',
            'filters_count': 4
        }
        response = self._get_response(data)
        self._check_topic_list(response, c_list, nc_list)

        # filter data, change the order (A or B and C and D)
        data = {
            'n0': 'Topic',
            't0': 'c',
            'f0': 'foo',
            'n1': 'Topic',
            't1': 'c',
            'f1': 'bar',
            'o1': 'OR',
            'n2': 'Topic',
            't2': 'c',
            'f2': 'test_filters',
            'o2': 'AND',
            'n3': 'Topic',
            't3': 'c',
            'f3': 'topic',
            'o3': 'AND',
            'filters_count': 4
        }
        response = self._get_response(data)
        self._check_topic_list(response, c_list, nc_list)

        # mix up 2 ORs (A or B and C or D)
        # ("foo" or "vav") AND ("test_filters" or "test_position_command")
        c_list = [
            '_test_filters/foo/an_ac',
            '_test_filters/foo/some_topic',
            '_test_Position_Command|vav-100',
            '_test_Position_Command|vav-101',
        ]
        nc_list = [
            '_test_filters/bar/another_topic',
            '_test_filters/bar/zone_temp',
            '_test_filters/bar/ahu',
            '_test_Position_Size|vav-100',
            '_test_Position_Size|vav-101',
        ]

        # filter data
        data = {
            'n0': 'Topic',
            't0': 'c',
            'f0': 'foo',
            'n1': 'Topic',
            't1': 'c',
            'f1': 'vav',
            'o1': 'OR',
            'n2': 'Topic',
            't2': 'c',
            'f2': 'test_filters',
            'o2': 'AND',
            'n3': 'Topic',
            't3': 'c',
            'f3': 'test_position_command',
            'o3': 'OR',
            'filters_count': 4
        }
        response = self._get_response(data)
        self._check_topic_list(response, c_list, nc_list)

        # mix up 3 ORs (A or B or C and D)
        # ("ahu" or "zone" or "vav") AND ("test_filters")
        c_list = [
            '_test_filters/bar/ahu',
            '_test_filters/bar/zone_temp',
        ]
        nc_list = [
            '_test_filters/foo/an_ac',
            '_test_filters/foo/some_topic',
            '_test_filters/bar/another_topic',
            '_test_Position_Size|vav-100',
            '_test_Position_Size|vav-101',
            '_test_Position_Command|vav-100',
            '_test_Position_Command|vav-101',
        ]

        # filter data
        data = {
            'n0': 'Topic',
            't0': 'c',
            'f0': 'ahu',
            'n1': 'Topic',
            't1': 'c',
            'f1': 'zone',
            'o1': 'OR',
            'n2': 'Topic',
            't2': 'c',
            'f2': 'vav',
            'o2': 'OR',
            'n3': 'Topic',
            't3': 'c',
            'f3': 'test_filters',
            'o3': 'AND',
            'filters_count': 4
        }
        response = self._get_response(data)
        self._check_topic_list(response, c_list, nc_list)

    def test_topic_rules(self):
        self._login()

        # create rule set 1 with rule 1
        data = {
            "name": "test rule 1",
            "tags": [
                {
                    "tag": "appName",
                    "value": "set_foo"
                }
            ],
            "filters": [
                {
                    "field": "Topic",
                    "type": "c",
                    "value": "foo"
                }
            ],
            "rule_set_id": "new",
            "rule_set_name": "test rule set 1"
        }
        create_topic_rule_url = reverse('core:topic_rules')
        response = self.client.post(create_topic_rule_url, json.dumps(data), content_type='application/json')
        # note we can't assert the rule or rule set ids
        json_resp = json.loads(response.content)
        self.assertIsNotNone(json_resp.get('rule'))
        self.assertIsNotNone(json_resp.get('rule').get('id'))
        rule_id = json_resp.get('rule').get('id')
        self.assertIsNotNone(json_resp.get('rule_set'))
        self.assertIsNotNone(json_resp.get('rule_set').get('id'))
        rule_set_id = json_resp.get('rule_set').get('id')
        self.assertEqual(
            json_resp,
            {
                'success': 'created',
                'rule': {
                    'name': 'test rule 1',
                    'id': rule_id,
                    'filters': [
                        {
                            'field': 'Topic',
                            'type': 'c',
                            'value': 'foo'
                        }
                    ],
                    'tags': [
                        {
                            'tag': 'appName',
                            'value': 'set_foo'
                        }
                    ]
                },
                'rule_set': {
                    'id': rule_set_id,
                    'name': 'test rule set 1'
                }
            }
        )

        # check the rule set exists in the DB and has the rule as defined
        rule_set = TopicTagRuleSet.objects.get(name='test rule set 1')
        self.assertIsNotNone(rule_set)

        rule = TopicTagRule.objects.get(rule_set=rule_set)
        self.assertIsNotNone(rule)
        self.assertEqual(
            rule.tags,
            [
                {
                    "tag": "appName",
                    "value": "set_foo"
                }
            ]
        )
        self.assertEqual(
            rule.filters,
            [
                {
                    "field": "Topic",
                    "type": "c",
                    "value": "foo"
                }
            ]
        )

        # update rule set 1 with rule 2
        data = {
            "name": "test rule 2",
            "tags": [
                {
                    "tag": "ac",
                    "value": None,
                    "remove": True
                }
            ],
            "filters": [
                {
                    "field": "Topic",
                    "type": "c",
                    "value": "foo"
                }
            ],
            "rule_set_name": "test rule set 1"
        }
        response = self.client.post(create_topic_rule_url, json.dumps(data), content_type='application/json')
        # note we can't assert the rule or rule set ids
        json_resp = json.loads(response.content)
        self.assertIsNotNone(json_resp.get('rule'))
        self.assertIsNotNone(json_resp.get('rule').get('id'))
        rule2_id = json_resp.get('rule').get('id')
        # it's a new rule
        self.assertNotEqual(rule2_id, rule_id)
        self.assertIsNotNone(json_resp.get('rule_set'))
        self.assertIsNotNone(json_resp.get('rule_set').get('id'))
        # it's in the same rule set
        self.assertEqual(rule_set_id, json_resp.get('rule_set').get('id'))
        self.assertEqual(
            json_resp,
            {
                'success': 'created',
                'rule': {
                    'name': 'test rule 2',
                    'id': rule2_id,
                    'filters': [
                        {
                            'field': 'Topic',
                            'type': 'c',
                            'value': 'foo'
                        }
                    ],
                    'tags': [
                        {
                            'tag': 'ac',
                            'value': None,
                            'remove': True
                        }
                    ]
                },
                'rule_set': {
                    'id': rule_set_id,
                    'name': 'test rule set 1'
                }
            }
        )

        # check the rule set exists in the DB and has the rule as defined
        rule_set = TopicTagRuleSet.objects.get(name='test rule set 1')
        self.assertIsNotNone(rule_set)

        rules = TopicTagRule.objects.filter(rule_set=rule_set)
        self.assertIsNotNone(rules)
        self.assertEqual(2, len(rules))
        for rule in rules:
            if rule.name == 'test rule 1':
                self.assertEqual(
                    rule.tags,
                    [
                        {
                            "tag": "appName",
                            "value": "set_foo"
                        }
                    ]
                )
                self.assertEqual(
                    rule.filters,
                    [
                        {
                            "field": "Topic",
                            "type": "c",
                            "value": "foo"
                        }
                    ]
                )
            elif rule.name == 'test rule 2':
                self.assertEqual(
                    rule.tags,
                    [
                        {
                            'remove': 'True',
                            "tag": "ac",
                            "value": None
                        }
                    ]
                )
                self.assertEqual(
                    rule.filters,
                    [
                        {
                            "field": "Topic",
                            "type": "c",
                            "value": "foo"
                        }
                    ]
                )
            else:
                pass

        # run rule set 1
        rule_set_run_url = reverse('core:topictagruleset_run', kwargs={'id': rule_set_id})
        response = self.client.post(rule_set_run_url)
        self.assertEqual({'success': 1, 'updated': 2, 'new_equipments': 0}, json.loads(response.content))

        # check both updated topics
        topics = Entity.objects.filter(topic__contains='foo')
        for topic in topics:
            self.assertNotIn('ac', topic.m_tags)
            self.assertEqual(topic.kv_tags['appName'], 'set_foo')

        # create rule set 2 with rule 3
        data = {
            "name": "test rule 3",
            "tags": [
                {
                    "tag": "ac",
                    "value": None,
                    "remove": False,
                    "kind": "Marker",
                    "description": "AC"
                },
                {
                    "tag": "appName",
                    "value": None,
                    "remove": True,
                    "kind": "Str",
                    "description": "Application Name"
                }
            ],
            "filters": [
                {
                    "field": "Topic",
                    "type": "c",
                    "value": "foo"
                },
                {
                    "field": "Topic",
                    "type": "c",
                    "value": "ac"
                }
            ],
            "rule_set_id": "new",
            "rule_set_name": "test rule set 2"
        }
        response = self.client.post(create_topic_rule_url, json.dumps(data), content_type='application/json')
        # note we can't assert the rule or rule set ids
        json_resp = json.loads(response.content)
        self.assertIsNotNone(json_resp.get('rule'))
        self.assertIsNotNone(json_resp.get('rule').get('id'))
        rule3_id = json_resp.get('rule').get('id')
        # it's a new rule
        self.assertNotEqual(rule3_id, rule_id)
        self.assertNotEqual(rule3_id, rule2_id)
        self.assertIsNotNone(json_resp.get('rule_set'))
        self.assertIsNotNone(json_resp.get('rule_set').get('id'))
        # it's a new rule set
        rule_set2_id = json_resp.get('rule_set').get('id')
        self.assertNotEqual(rule_set2_id, rule_set_id)

        # run rule set 2
        rule_set_run_url = reverse('core:topictagruleset_run', kwargs={'id': rule_set2_id})
        response = self.client.post(rule_set_run_url)
        self.assertEqual({'success': 1, 'updated': 1, 'new_equipments': 0}, json.loads(response.content))

        # check topic updated correctly
        topic = Entity.objects.filter(topic__contains='foo').filter(topic__contains='ac')
        self.assertIn('ac', topic[0].m_tags)
        self.assertNotIn(str(topic[0].kv_tags), 'appName')

    def test_topic_regex_rules(self):
        self._login()

        # create rule set 1 with rule 1
        data = {
            "name": "test rule 1",
            "tags": [],
            "filters": [
                {
                    "field": "Topic",
                    "type": "matches",
                    "value": ".*vav-(.*)"
                }
            ],
            "rule_action": "create equipment",
            "rule_action_fields": {
                "equipment_name": "{group[1]} test equip name",
                "site_object_id": "test_filters_site",
                "model_object_id": "_test_model"
            },
            "rule_set_id": "new",
            "rule_set_name": "test regex rule set"
        }
        create_topic_rule_url = reverse('core:topic_rules')
        response = self.client.post(create_topic_rule_url, json.dumps(data), content_type='application/json')
        # note we can't assert the rule or rule set ids
        json_resp = json.loads(response.content)
        self.assertIsNotNone(json_resp.get('rule'))
        self.assertIsNotNone(json_resp.get('rule').get('id'))
        self.assertIsNotNone(json_resp.get('rule_set'))
        self.assertIsNotNone(json_resp.get('rule_set').get('id'))

        # run rule set
        rule_set = TopicTagRuleSet.objects.get(name='test regex rule set')
        logging.warning('test_topic_regex_rules rule_set: %s', rule_set)
        rule_set_run_url = reverse('core:topictagruleset_run', kwargs={'id': rule_set.id})
        response = self.client.post(rule_set_run_url)
        self.assertEqual({'success': 1, 'updated': 0, 'new_equipments': 2}, json.loads(response.content))

        # check 2 equipments are created
        self.assertEqual(1, Entity.objects.filter(entity_id__contains='100-test-equip-name').count())
        self.assertEqual(1, Entity.objects.filter(entity_id__contains='101-test-equip-name').count())

        # check equipment tags
        equipments = Entity.objects.filter(entity_id__contains='100-test-equip-name')
        for equipment in equipments:
            self.assertEqual(equipment.kv_tags['siteRef'], 'test_filters_site')
            self.assertEqual(equipment.kv_tags['modelRef'], '_test_model')
