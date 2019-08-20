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
from opentaps_seas.core.models import Entity
from opentaps_seas.core.models import Tag


class SyncAPITests(TestCase):

    entity_id = '_testTopic'
    topic_id = '_testTopic'

    @classmethod
    def setUpTestData(cls):
        Tag.objects.get_or_create(tag='_testkind', defaults={
            'kind': 'String',
            'description': 'This is a test Tag'
        })
        Tag.objects.get_or_create(tag='_testdis', defaults={
            'kind': 'String',
            'description': 'This is a test Tag'
        })

        Tag.objects.get_or_create(tag='_testtag1', defaults={
            'kind': 'Marker',
            'description': 'This is a test Tag'
        })

        Tag.objects.get_or_create(tag='_testtag2', defaults={
            'kind': 'Marker',
            'description': 'This is a test Tag'
        })

        Entity.objects.get_or_create(
            entity_id="_testTopic",
            topic="_testTopic",
            m_tags=["_testtag1"],
            kv_tags={'_testkind': 'test'}
        )

    def setUp(self):
        get_user_model().objects.create_user('temporary', 'temporary@gmail.com', 'temporary')

    def tearDown(self):
        self._cleanup_data()

    @staticmethod
    def _cleanup_data():
        Entity.objects.filter(entity_id__startswith='_test').delete()
        Tag.objects.filter(tag__startswith='_test').delete()

        # delete test data for CrateDB
        with connections['crate'].cursor() as c:
            sql = """DELETE FROM {0} WHERE topic like %s""".format("volttron.topic")
            c.execute(sql, ['_test%'])
            sql = """DELETE FROM {0} WHERE topic like %s""".format("volttron.data")
            c.execute(sql, ['_test%'])
            sql = """DELETE FROM {0} WHERE topic like %s""".format("volttron.entity")
            c.execute(sql, ['_test%'])

    def _login(self):
        self.client.login(username='temporary', password='temporary')

    def test_sync_m_tags(self):
        self._login()

        # Add new m_tag to Topic
        entity_tag_add_url = reverse('core:entity_tag', kwargs={'entity_id': self.entity_id})
        self.client.post(entity_tag_add_url, {'tag': '_testtag2'})

        postgres_tags = Entity.objects.get(entity_id=self.entity_id).m_tags

        self.assertIn('_testtag1', postgres_tags)
        self.assertIn('_testtag2', postgres_tags)

        with connections['crate'].cursor() as c:
            sql = """SELECT "m_tags" FROM {0} WHERE topic = %s""".format("volttron.entity")
            c.execute(sql, ['_testTopic'])
            for record in c:
                m_tags = record[0]
                self.assertIn('_testtag1', m_tags)
                self.assertIn('_testtag2', m_tags)

        # delete m_tag from Entity
        entity_tag_delete_url = reverse('core:entity_tag', kwargs={'entity_id': self.entity_id})
        self.client.post(entity_tag_delete_url, {'tag': '_testtag1', 'delete': 1})

        postgres_tags = Entity.objects.get(entity_id=self.entity_id).m_tags
        self.assertEqual(['_testtag2'], postgres_tags)

        with connections['crate'].cursor() as c:
            sql = """SELECT "m_tags" FROM {0} WHERE topic = %s""".format("volttron.entity")
            c.execute(sql, ['_testTopic'])
            for record in c:
                m_tags = record[0]
                self.assertEqual(['_testtag2'], m_tags)

    def test_sync_kv_tags(self):
        self._login()

        # Add new kv_tag to Topic
        entity_tag_add_url = reverse('core:entity_tag', kwargs={'entity_id': self.entity_id})
        self.client.post(entity_tag_add_url, {'tag': '_testdis', 'value': 'test'})

        postgres_tags = Entity.objects.get(entity_id=self.entity_id).kv_tags

        self.assertEqual(2, len(postgres_tags))
        self.assertEqual({'_testdis': 'test', '_testkind': 'test'}, postgres_tags)

        with connections['crate'].cursor() as c:
            sql = """SELECT "kv_tags" FROM {0} WHERE topic = %s""".format("volttron.entity")
            c.execute(sql, ['_testTopic'])
            for record in c:
                kv_tags = record[0]
                self.assertEqual(2, len(kv_tags))
                self.assertEqual({'_testdis': 'test', '_testkind': 'test'}, kv_tags)

        # update kv_tag from Entity
        entity_tag_update_url = reverse('core:entity_tag', kwargs={'entity_id': self.entity_id})
        self.client.post(entity_tag_update_url, {'tag': '_testdis', 'value': 'test update', 'update': 1})

        postgres_tags = Entity.objects.get(entity_id=self.entity_id).kv_tags
        self.assertEqual(2, len(postgres_tags))
        self.assertEqual({'_testdis': 'test update', '_testkind': 'test'}, postgres_tags)

        with connections['crate'].cursor() as c:
            sql = """SELECT "kv_tags" FROM {0} WHERE topic = %s""".format("volttron.entity")
            c.execute(sql, ['_testTopic'])
            for record in c:
                kv_tags = record[0]
                self.assertEqual(2, len(kv_tags))
                self.assertEqual({'_testdis': 'test update', '_testkind': 'test'}, kv_tags)

        # delete kv_tag from Entity
        entity_tag_delete_url = reverse('core:entity_tag', kwargs={'entity_id': self.entity_id})
        self.client.post(entity_tag_delete_url, {'tag': '_testdis', 'value': 1, 'delete': 1})

        postgres_tags = Entity.objects.get(entity_id=self.entity_id).kv_tags
        self.assertEqual({'_testkind': 'test'}, postgres_tags)

        with connections['crate'].cursor() as c:
            sql = """SELECT "kv_tags" FROM {0} WHERE topic = %s""".format("volttron.entity")
            c.execute(sql, ['_testTopic'])
            for record in c:
                kv_tags = record[0]
                self.assertEqual({'_testkind': 'test'}, kv_tags)
