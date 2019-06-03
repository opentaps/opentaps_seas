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

import time

from datetime import datetime
from django.db import connections
from django.test import TestCase
from opentaps_seas.core.models import Entity
from opentaps_seas.core import utils


class UtilsTests(TestCase):

    entity_id = '_test_myentity'
    topic = '_test/topic'
    topic1 = '_test/topicbool'

    @classmethod
    def setUpClass(cls):
        super(UtilsTests, cls).setUpClass()
        cls._cleanup_data()
        with connections['crate'].cursor() as c:
            sql = """INSERT INTO {0} (topic)
            VALUES (%s)""".format("volttron.topic")
            try:
                c.execute(sql, [cls.topic])
            except Exception:
                # just make sure the topic exists
                pass
            try:
                c.execute(sql, [cls.topic1])
            except Exception:
                # just make sure the topic exists
                pass

            sql = """INSERT INTO {0} (double_value, source, string_value, topic, ts)
            VALUES (%s, %s, %s, %s, %s)""".format("volttron.data")
            c.execute(sql, [34.74, 'scrape', '34.74', cls.topic, datetime.utcnow()])
            c.execute(sql, [1, 'scrape', '1', cls.topic1, datetime.utcnow()])
        time.sleep(2)

    @classmethod
    def tearDownClass(cls):
        super(UtilsTests, cls).tearDownClass()
        cls._cleanup_data()

    @classmethod
    def _cleanup_data(cls):
        with connections['crate'].cursor() as c:
            sql = """DELETE FROM {0} WHERE topic like %s""".format("volttron.topic")
            c.execute(sql, ['_test%'])
            sql = """DELETE FROM {0} WHERE topic like %s""".format("volttron.data")
            c.execute(sql, ['_test%'])

    def test_get_current_value(self):
        point = Entity()
        point.entity_id = self.entity_id
        point.topic = 'empty'
        point.kind = 'Number'
        point.unit = '°C'
        current_value = utils.get_current_value(point)
        self.assertIsNone(current_value)

        point = Entity()
        point.entity_id = self.entity_id
        point.topic = self.topic
        point.kind = 'Number'
        point.unit = '°C'
        current_value = utils.get_current_value(point)
        self.assertTrue('<b>34.7</b> °C' in current_value)

        point = Entity()
        point.entity_id = self.entity_id
        point.topic = self.topic1
        point.kind = 'Bool'
        current_value = utils.get_current_value(point)
        self.assertTrue('<b>True</b>' in current_value)

        point = Entity()
        point.entity_id = self.entity_id
        point.topic = self.topic
        point.kind = 'Number'
        point.unit = ''
        current_value = utils.get_current_value(point)
        self.assertTrue('<b>34.74</b>' in current_value)

    def test_get_point_values(self):
        point = Entity()
        point.entity_id = self.entity_id
        point.topic = self.topic
        point.kind = 'Number'
        point.unit = '°C'

        point_values = utils.get_point_values(point, '', 'avg', None)
        self.assertIsNotNone(point_values)
        self.assertEqual(len(point_values), 1)
        point_value = point_values[0]
        self.assertIsNotNone(point_value)
        self.assertIn(34.74, point_value)

        point = Entity()
        point.entity_id = self.entity_id
        point.topic = self.topic1
        point.kind = 'Bool'

        point_values = utils.get_point_values(point)
        self.assertIsNotNone(point_values)
        self.assertEqual(len(point_values), 1)
        point_value = point_values[0]
        self.assertIsNotNone(point_value)
        self.assertIn(1, point_value)

        point = Entity()
        point.entity_id = self.entity_id
        point.topic = self.topic
        point.kind = 'String'
        point.unit = ''
        point_values = utils.get_point_values(point)
        self.assertIsNotNone(point_values)
        self.assertEqual(len(point_values), 1)
        point_value = point_values[0]
        self.assertIsNotNone(point_value)
        self.assertIn('34.74', point_value)

    def test_charts_for_points(self):
        point = Entity()
        point.entity_id = self.entity_id
        point.topic = self.topic
        point.kind = 'Number'
        point.unit = '°C'
        point.description = 'Point description'
        point.site_id = '@D'
        point.equipment_id = '@D-AHU1'

        point1 = Entity()
        point1.entity_id = self.entity_id
        point1.topic = self.topic1
        point1.kind = 'Bool'
        point1.unit = ''
        point1.description = 'Point1 description'
        point1.site_id = '@D'
        point1.equipment_id = '@D-AHU2'
        points = []
        points.append(point)
        points.append(point1)
        charts = utils.charts_for_points(points)
        self.assertIsNotNone(charts)
        self.assertEqual(len(charts), 2)

    def test_add_current_values(self):
        point = Entity()
        point.entity_id = self.entity_id
        point.topic = self.topic
        point.kind = 'Number'
        point.unit = '°C'
        point.description = 'Point description'
        point.site_id = '@D'
        point.equipment_id = '@D-AHU1'

        point1 = Entity()
        point1.entity_id = self.entity_id
        point1.topic = self.topic1
        point1.kind = 'Bool'
        point1.unit = ''
        point1.description = 'Point1 description'
        point1.site_id = '@D'
        point1.equipment_id = '@D-AHU2'
        points = []
        points.append(point)
        points.append(point1)
        data = utils.add_current_values(points)
        self.assertIsNotNone(data)
        self.assertTrue('<b>34.7</b> °C' in data[0].current_value)
        self.assertTrue('<b>True</b>' in data[1].current_value)
