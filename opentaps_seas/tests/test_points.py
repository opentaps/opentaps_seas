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

import tempfile
import os
import csv
import json
import io
import zipfile
from io import StringIO

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
        self.assertNotIn(['_testtag1'], postgres_tags)

        with connections['crate'].cursor() as c:
            sql = """SELECT "m_tags" FROM {0} WHERE topic = %s""".format("volttron.entity")
            c.execute(sql, ['_testTopic'])
            for record in c:
                m_tags = record[0]
                self.assertNotIn(['_testtag1'], m_tags)

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
        self.assertNotIn(str(postgres_tags), '_testdis')

        with connections['crate'].cursor() as c:
            sql = """SELECT "kv_tags" FROM {0} WHERE topic = %s""".format("volttron.entity")
            c.execute(sql, ['_testTopic'])
            for record in c:
                kv_tags = record[0]
                self.assertNotIn(str(kv_tags), '_testdis')

    def test_import_tags_csv_clear(self):
        self._login()

        # create test topic
        Entity.objects.get_or_create(
            entity_id="_test_topic",
            topic="_test_topic",
            m_tags=["_testtag1"],
            kv_tags={'_testkind': 'test'}
        )

        # import csv tags with clear option
        csv_import_url = reverse('core:tag_import')

        temp_csv = os.path.join(tempfile.gettempdir(), 'temp_tag_csv.csv')
        with open(temp_csv, 'w') as f:
            file_writer = csv.writer(f, quotechar='"', quoting=csv.QUOTE_MINIMAL)
            file_header = ['__topic', '_testtag2', '_testdis']
            file_writer.writerow(file_header)
            file_writer.writerow(['_test_topic', 'X', 'test'])

        with open(temp_csv, 'r') as f:
            data = {
                'clear_existing_tags': True,
                'csv_file': f
            }
            self.client.post(csv_import_url, data)

        # check prev tags removed and new tags added
        entity = Entity.objects.get(entity_id='_test_topic')

        self.assertNotIn('_testtag1', entity.m_tags)
        self.assertNotIn('_testkind', str(entity.kv_tags))

        self.assertEqual(['_testtag2'], entity.m_tags)
        self.assertEqual({'_testdis': 'test'}, entity.kv_tags)

    def test_import_tags_csv_not_clear(self):
        self._login()

        # create test topic
        Entity.objects.get_or_create(
            entity_id="_test_topic_not_clear",
            topic="_test_topic_not_clear",
            m_tags=["_testtag1"],
            kv_tags={'_testkind': 'test'}
        )

        # import csv tags without clear option
        csv_import_url = reverse('core:tag_import')

        temp_csv = os.path.join(tempfile.gettempdir(), 'temp_tag_csv.csv')
        with open(temp_csv, 'w') as f:
            file_writer = csv.writer(f, quotechar='"', quoting=csv.QUOTE_MINIMAL)
            file_header = ['__topic', '_testtag2', '_testdis']
            file_writer.writerow(file_header)
            file_writer.writerow(['_test_topic_not_clear', 'X', 'test'])

        with open(temp_csv, 'r') as f:
            data = {
                'clear_existing_tags': False,
                'csv_file': f
            }
            self.client.post(csv_import_url, data)

        # check prev tags removed and new tags added
        entity = Entity.objects.get(entity_id='_test_topic_not_clear')

        self.assertIn('_testtag1', entity.m_tags)
        self.assertIn('_testkind', str(entity.kv_tags))

        self.assertIn('_testtag2', entity.m_tags)
        self.assertIn('_testdis', str(entity.kv_tags))

    def test_tag_imports_bacnet_config(self):
        self._login()

        # create site
        Entity.objects.get_or_create(entity_id='_test_site', defaults={'m_tags': ['site'], 'kv_tags': {}})

        # create temp file for bacnet csv and config file
        bacnet_csv = os.path.join(tempfile.gettempdir(), 'bacnet.csv')
        with open(bacnet_csv, 'w') as f:
            file_writer = csv.writer(f, quotechar='"', quoting=csv.QUOTE_MINIMAL)
            file_header = [
                'Point Name', 'Volttron Point Name', 'Units', 'Unit Details', 'Object Type', 'Property',
                'Writable', 'Index', 'Notes'
            ]
            file_writer.writerow(file_header)
            file_writer.writerow(
                [
                    '_test_topic_bacnet1', '_test_topic_bacnet1', 'test_units', 'test_unit_details', 'test_object_type',
                    'test_property', 'test_writeable', 'test_index', 'test_notes'
                ]
            )

        bacnet_config = os.path.join(tempfile.gettempdir(), 'bacnet.config')
        with open(bacnet_config, 'w') as b:
            config_json = {
                "driver_config": {
                    "device_address": "10.0.0.1",
                    "device_id": "100"
                },
                "driver_type": "test",
                "registry_config": "config://bacnet.csv",
                "interval": 10
            }
            json.dump(config_json, b)

        f = open(bacnet_csv, 'r')
        b = open(bacnet_config, 'r')

        data = {
            'site': '_test_site',
            'device_prefix': '_test',
            'csv_file': f,
            'config_file': b
        }

        # import tags from bacnet scans
        bacnet_scans_import_url = reverse('core:topic_import')
        self.client.post(bacnet_scans_import_url, data)

        # check all tags are imported correctly
        entity = Entity.objects.get(entity_id__contains='_test_topic_bacnet1')

        # tags from csv
        self.assertIn('bacnet_units', str(entity.kv_tags))
        self.assertIn('bacnet_prefix', str(entity.kv_tags))
        self.assertIn('bacnet_unit_details', str(entity.kv_tags))
        self.assertIn('bacnet_object_type', str(entity.kv_tags))
        self.assertIn('bacnet_volttron_point_name', str(entity.kv_tags))
        self.assertIn('bacnet_reference_point_name', str(entity.kv_tags))
        self.assertIn('bacnet_property', str(entity.kv_tags))
        self.assertIn('bacnet_index', str(entity.kv_tags))
        self.assertIn('bacnet_writable', str(entity.kv_tags))
        self.assertIn('bacnet_notes', str(entity.kv_tags))

        # tags from config file
        self.assertIn('bacnet_device_address', str(entity.kv_tags))
        self.assertIn('bacnet_driver_type', str(entity.kv_tags))
        self.assertIn('bacnet_device_id', str(entity.kv_tags))
        self.assertIn('bacnet_registry_config', str(entity.kv_tags))
        self.assertIn('interval', str(entity.kv_tags))

        # check topic name includes prefix + /
        self.assertEqual('_test/_test_topic_bacnet1', entity.topic)

    def test_exporting_imported_tags(self):
        self._login()

        # create site
        Entity.objects.get_or_create(entity_id='_test_site', defaults={'m_tags': ['site'], 'kv_tags': {}})

        # create temp file for bacnet csv and config file
        bacnet_csv = os.path.join(tempfile.gettempdir(), 'bacnet.csv')
        with open(bacnet_csv, 'w') as f:
            file_writer = csv.writer(f, quotechar='"', quoting=csv.QUOTE_MINIMAL)
            file_header = [
                'Point Name', 'Volttron Point Name', 'Units', 'Unit Details', 'Object Type', 'Property',
                'Writable', 'Index', 'Notes'
            ]
            file_writer.writerow(file_header)
            for i in range(3):
                file_writer.writerow(
                    [
                        '_test_topic_bacnet{}'.format(i + 1), '_test_topic_bacnet{}'.format(i + 1), 'test_units',
                        'test_unit_details', 'test_object_type', 'test_property', 'test_writable', 'test_index',
                        'test_notes'
                    ]
                )

        bacnet_config = os.path.join(tempfile.gettempdir(), 'bacnet.config')
        with open(bacnet_config, 'w') as b:
            config_json = {
                "driver_config": {
                    "device_address": "10.0.0.1",
                    "device_id": "100"
                },
                "driver_type": "test",
                "registry_config": "config://bacnet.csv",
                "interval": 10
            }
            json.dump(config_json, b)

        f = open(bacnet_csv, 'r')
        b = open(bacnet_config, 'r')

        data = {
            'site': '_test_site',
            'device_prefix': '_test',
            'csv_file': f,
            'config_file': b
        }

        # import tags from bacnet scans
        bacnet_scans_import_url = reverse('core:topic_import')
        self.client.post(bacnet_scans_import_url, data)

        # modify interval values
        topic2 = Entity.objects.get(entity_id__contains='_test_topic_bacnet2')
        topic2.kv_tags['interval'] = 5
        topic2.save()

        topic3 = Entity.objects.get(entity_id__contains='_test_topic_bacnet3')
        topic3.kv_tags['interval'] = None
        topic3.save()

        # Export imported tags by interval
        export_config_url = reverse('core:topic_export0')
        data = {
            'site': '_test_site',
            'device_prefix': '_test'
        }
        response = self.client.post(export_config_url, data)

        try:
            exported_file = io.BytesIO(response.content)
            zipped_file = zipfile.ZipFile(exported_file, 'r')

            # check exported file includes all config files by interval
            self.assertIn('_Interval_10.csv', zipped_file.namelist())
            self.assertIn('_Interval_10.config', zipped_file.namelist())
            self.assertIn('_Interval_5.csv', zipped_file.namelist())
            self.assertIn('_Interval_5.config', zipped_file.namelist())
            self.assertIn('_Interval_Not_Set.csv', zipped_file.namelist())
            self.assertIn('_Interval_Not_Set.csv', zipped_file.namelist())

            # check config files and csv files include all values
            topic_count = 0

            for finfo in zipped_file.infolist():
                # check config files
                if finfo.filename.endswith('.config'):
                    interval = finfo.filename.replace('_Interval_', '').replace('.config', '')
                    try:
                        interval = int(interval)
                    except ValueError:
                        interval = None

                    ifile = zipped_file.open(finfo)
                    config_content = ifile.read()
                    config_json_str = config_content.decode('utf8').replace("'", "")
                    config_interval = json.loads(config_json_str)

                    self.assertIn('driver_config', config_json_str)
                    self.assertIn('device_address', config_json_str)
                    self.assertIn('driver_type', config_json_str)
                    self.assertEqual('10.0.0.1', config_interval['driver_config']['device_address'])
                    self.assertEqual('100', config_interval['driver_config']['device_id'])
                    self.assertEqual('test', config_interval['driver_type'])
                    if interval:
                        self.assertIn('interval', config_json_str)
                        self.assertEqual(str(interval), config_interval['interval'])

                # check csv files
                if finfo.filename.endswith('.csv'):
                    ifile = zipped_file.read(finfo).decode('utf8')
                    csv_content = StringIO(ifile)
                    reader = csv.reader(csv_content)
                    for index, row in enumerate(reader):
                        if index == 0:
                            self.assertIn('reference_point_name', row)
                            self.assertIn('volttron_point_name', row)
                            self.assertIn('units', row)
                            self.assertIn('unit_details', row)
                            self.assertIn('object_type', row)
                            self.assertIn('property', row)
                            self.assertIn('writable', row)
                            self.assertIn('index', row)
                            self.assertIn('notes', row)
                        else:
                            topic_count += 1

            # check total topics are same with sum of separated topics
            self.assertEqual(topic_count, 3)

        finally:
            zipped_file.close()
            exported_file.close()
