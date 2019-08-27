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

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.db import connections
from opentaps_seas.core.models import Entity
from opentaps_seas.core.models import Tag
from opentaps_seas.core.models import Topic


class TopicAPITests(TestCase):

    topic_list_get_url = reverse('core:topic_list')
    topic_list_post_url = reverse('core:topic_table')

    @classmethod
    def setUpTestData(cls):
        # create site
        Entity.objects.get_or_create(entity_id='_test_filters_site', defaults={'m_tags': ['site'], 'kv_tags': {}})

        # ensure topic exists
        Topic.ensure_topic_exists('_test_filters/foo/some_topic')
        Topic.ensure_topic_exists('_test_filters/bar/another_topic')
        Topic.ensure_topic_exists('_test_filters/foo/an_ac')
        Topic.ensure_topic_exists('_test_filters/bar/ahu')
        Topic.ensure_topic_exists('_test_filters/bar/zone_temp')

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

    def setUp(self):
        get_user_model().objects.create_user('temporary', 'temporary@gmail.com', 'temporary')

    def tearDown(self):
        self._cleanup_data()

    @staticmethod
    def _cleanup_data():
        # delete test data from postgres
        Entity.objects.filter(entity_id__startswith='_test').delete()

        # delete test data for CrateDB
        with connections['crate'].cursor() as c:
            sql = """DELETE FROM {0} WHERE topic like %s""".format("volttron.topic")
            c.execute(sql, ['_test%'])
            sql = """DELETE FROM {0} WHERE topic like %s""".format("volttron.data")
            c.execute(sql, ['_test%'])
            sql = """DELETE FROM {0} WHERE topic like %s""".format("volttron.entity")
            c.execute(sql, ['_test%'])

    def _get_response(self, params, method):
        if method == 'get':
            return self.client.get('?'.join((self.topic_list_get_url, params)))
        else:
            return self.client.post(self.topic_list_post_url, params)

    def _check_topic_list(self, response, c_list, nc_list):
        for entity in c_list:
            self.assertContains(response, entity)
        for entity in nc_list:
            self.assertNotContains(response, entity)

    def _login(self):
        self.client.login(username='temporary', password='temporary')

    def test_topics_filter(self):
        self._login()

        # create entities
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

        # ----------- start test n0="Topic" t0="c" f0="test" ----------- #
        c_list = [
            '_test_filters/foo/some_topic',
            '_test_filters/foo/an_ac',
            '_test_filters/bar/another_topic',
            '_test_filters/bar/ahu',
            '_test_filters/bar/zone_temp'
        ]
        nc_list = []

        # get method
        query_params = '&'.join(
            [param for param in ['n0=Topic', 't0=c', 'f0=test', 'filters_count=1']]
        )
        response = self._get_response(query_params, 'get')
        self._check_topic_list(response, c_list, nc_list)

        # post method
        data = {
            'n0': 'Topic',
            't0': 'c',
            'f0': 'test',
            'filters_count': 1
        }
        response = self._get_response(data, 'post')
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

        # get method
        query_params = '&'.join(
            [param for param in ['n0=Topic', 't0=c', 'f0=bar', 'filters_count=1']]
        )
        response = self._get_response(query_params, 'get')
        self._check_topic_list(response, c_list, nc_list)

        # post method
        data = {
            'n0': 'Topic',
            't0': 'c',
            'f0': 'bar',
            'filters_count': 1
        }
        response = self._get_response(data, 'post')
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

        # get method
        query_params = '&'.join(
            [param for param in ['n0=Topic', 't0=c', 'f0=foo', 'filters_count=1']]
        )
        response = self._get_response(query_params, 'get')
        self._check_topic_list(response, c_list, nc_list)

        # post method
        data = {
            'n0': 'Topic',
            't0': 'c',
            'f0': 'foo',
            'filters_count': 1
        }
        response = self._get_response(data, 'post')
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

        # get method
        query_params = '&'.join(
            [param for param in ['n0=Topic', 't0=c', 'f0=bar', 'n1=zone', 't1=present', 'filters_count=2']]
        )
        response = self._get_response(query_params, 'get')
        self._check_topic_list(response, c_list, nc_list)

        # post method
        data = {
            'n0': 'Topic',
            't0': 'c',
            'f0': 'bar',
            'n1': 'zone',
            't1': 'present',
            'filters_count': 2
        }
        response = self._get_response(data, 'post')
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

        # get method
        query_params = '&'.join(
            [param for param in ['n0=Topic', 't0=c', 'f0=foo', 'n1=ac', 't1=absent', 'filters_count=2']]
        )
        response = self._get_response(query_params, 'get')
        self._check_topic_list(response, c_list, nc_list)

        # post method
        data = {
            'n0': 'Topic',
            't0': 'c',
            'f0': 'foo',
            'n1': 'ac',
            't1': 'absent',
            'filters_count': 2
        }
        response = self._get_response(data, 'post')
        self._check_topic_list(response, c_list, nc_list)

        # ----------- start test n0="Topic" t0="c" f0="FOO" n1="ac" t1="absent" (Case Sensitive)----------- #
        c_list = []
        nc_list = [
            '_test_filters/foo/some_topic',
            '_test_filters/foo/an_ac',
            '_test_filters/bar/another_topic',
            '_test_filters/bar/ahu',
            '_test_filters/bar/zone_temp'
        ]

        # get method
        query_params = '&'.join(
            [param for param in ['n0=Topic', 't0=c', 'f0=FOO', 'n1=ac', 't1=absent', 'filters_count=2']]
        )
        response = self._get_response(query_params, 'get')
        self._check_topic_list(response, c_list, nc_list)

        # post method
        data = {
            'n0': 'Topic',
            't0': 'c',
            'f0': 'FOO',
            'n1': 'ac',
            't1': 'absent',
            'filters_count': 2
        }
        response = self._get_response(data, 'post')
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

        # get method
        query_params = '&'.join(
            [param for param in ['n0=Topic', 't0=c', 'f0=test_filters', 'filters_count=1']]
        )
        response = self._get_response(query_params, 'get')
        self._check_topic_list(response, c_list, nc_list)

        # post method
        data = {
            'n0': 'Topic',
            't0': 'c',
            'f0': 'test_filters',
            'filters_count': 1
        }
        response = self._get_response(data, 'post')
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

        # get method
        query_params = '&'.join(
            [
                param for param in [
                    'n0=Topic', 't0=c', 'f0=test_filters', 'n1=appName', 't1=eq', 'f1=test_foo', 'filters_count=2'
                ]
            ]
        )
        response = self._get_response(query_params, 'get')
        self._check_topic_list(response, c_list, nc_list)

        # post method
        data = {
            'n0': 'Topic',
            't0': 'c',
            'f0': 'test_filters',
            'n1': 'appName',
            't1': 'eq',
            'f1': 'test_foo',
            'filters_count': 2
        }
        response = self._get_response(data, 'post')
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

        # get method
        query_params = '&'.join(
            [
                param for param in [
                    'n0=Topic', 't0=c', 'f0=test_filters', 'n1=appName', 't1=neq', 'f1=test_foo', 'filters_count=2'
                ]
            ]
        )
        response = self._get_response(query_params, 'get')
        self._check_topic_list(response, c_list, nc_list)

        # post method
        data = {
            'n0': 'Topic',
            't0': 'c',
            'f0': 'test_filters',
            'n1': 'appName',
            't1': 'neq',
            'f1': 'test_foo',
            'filters_count': 2
        }
        response = self._get_response(data, 'post')
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

        # get method
        query_params = '&'.join(
            [
                param for param in [
                    'n0=Topic', 't0=c', 'f0=test_filters', 'n1=appName', 't1=neq', 'f1=test_foo',
                    'n2=zone', 't2=present', 'n3=ac', 't3=absent', 'n4=unit', 't4=eq', 'f4=celsius', 'filters_count=5'
                ]
            ]
        )
        response = self._get_response(query_params, 'get')
        self._check_topic_list(response, c_list, nc_list)

        # post method
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
        response = self._get_response(data, 'post')
        self._check_topic_list(response, c_list, nc_list)
