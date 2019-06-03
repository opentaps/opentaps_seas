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
from opentaps_seas.core.models import Entity


class SitesAPITests(TestCase):

    @classmethod
    def setUpTestData(cls):
        Entity.objects.get_or_create(entity_id='@A', defaults={'m_tags': ['site'], 'kv_tags': {
            'geoState': 'VA',
            'area': '1000ft²',
            'geoAddr': 'Richmond,VA',
            'tz': 'New_York',
            'id': '@A',
            'geoCity': 'Richmond',
            'dis': 'A'
            }})
        Entity.objects.get_or_create(entity_id='@B', defaults={'m_tags': ['site'], 'kv_tags': {
            'geoState': 'VA',
            'area': '2000ft²',
            'geoAddr': 'Richmond,VA',
            'tz': 'New_York',
            'id': '@B',
            'geoCity': 'Richmond',
            'dis': 'B'
            }})
        Entity.objects.get_or_create(entity_id='@C', defaults={'m_tags': ['site'], 'kv_tags': {
            'geoState': 'DC',
            'area': '3000ft²',
            'geoAddr': 'Washington,DC',
            'tz': 'New_York',
            'id': '@C',
            'geoCity': 'Washington',
            'dis': 'C'
            }})
        Entity.objects.get_or_create(entity_id='@D', defaults={'m_tags': ['site'], 'kv_tags': {
            'geoState': 'MA',
            'area': '4000ft²',
            'geoAddr': 'Boston,MA',
            'tz': 'New_York',
            'id': '@D',
            'geoCity': 'Boston',
            'dis': 'D'
            }})

    def setUp(self):
        self._cleanup_data()
        get_user_model().objects.create_user('temporary', 'temporary@gmail.com', 'temporary')

    def tearDown(self):
        self._cleanup_data()

    def _cleanup_data(self):
        Entity.objects.filter(entity_id__startswith='_test').delete()

    def _login(self):
        self.client.login(username='temporary', password='temporary')

    def test_list_requires_login(self):
        url = reverse('core:site_list')
        response = self.client.get(url)
        self.assertEquals(response.status_code, 302)

    def test_list_search(self):

        self._login()
        url = reverse('core:site_list')
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)

        response = self.client.get(url + '?query=Boston')
        self.assertContains(response, '@D')
        self.assertNotContains(response, '@A')

        response = self.client.get(url + '?query=@C')
        self.assertContains(response, '@C')
        self.assertContains(response, 'Washington')
        self.assertNotContains(response, '@A')

    def test_list_json_requires_login(self):
        url = reverse('core:site_list_json')
        response = self.client.get(url)
        self.assertEquals(response.status_code, 302)

    def test_list_json(self):
        url = reverse('core:site_list_json')
        self._login()
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue('items' in data, msg='Expected the JSON response to include data.items')
        self.assertTrue(len(data['items']) >= 4,
                        msg='Expected at least 4 tags to be listed, got {0}'.format(len(data['items'])))
