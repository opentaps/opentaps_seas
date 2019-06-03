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
from opentaps_seas.core.models import Entity


class HaystackTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        Entity.objects.get_or_create(entity_id='@A', defaults={'m_tags': ['site'], 'kv_tags': {
            'geoState': 'VA',
            'area': '1000ft²',
            'geoAddr': 'Richmond,VA',
            'tz': 'New_York',
            'id': 'site/A',
            'geoCity': 'Richmond',
            'dis': 'A'
            }})
        Entity.objects.get_or_create(entity_id='@B', defaults={'m_tags': ['site'], 'kv_tags': {
            'geoState': 'VA',
            'area': '2000ft²',
            'geoAddr': 'Richmond,VA',
            'tz': 'New_York',
            'id': 'site/B',
            'geoCity': 'Richmond',
            'dis': 'B'
            }})
        Entity.objects.get_or_create(entity_id='@C', defaults={'m_tags': ['site'], 'kv_tags': {
            'geoState': 'DC',
            'area': '3000ft²',
            'geoAddr': 'Washington,DC',
            'tz': 'New_York',
            'id': 'site/C',
            'geoCity': 'Washington',
            'dis': 'C'
            }})

        Entity.objects.get_or_create(entity_id='@A-E1', defaults={
            'm_tags': ['equip', 'siteMeter'],
            'kv_tags': {
                'id': 'equip/A/E1',
                'dis': 'Equipment AE1',
                'siteRef': 'site/A',
            }})
        Entity.objects.get_or_create(entity_id='@A-E2', defaults={
            'm_tags': ['equip', 'siteMeter', 'elecMeter'],
            'kv_tags': {
                'id': 'equip/A/E2',
                'dis': 'Equipment AE2',
                'siteRef': 'site/A',
            }})
        Entity.objects.get_or_create(entity_id='@B-E1', defaults={
            'm_tags': ['equip', 'siteMeter'],
            'kv_tags': {
                'id': 'equip/B/E1',
                'dis': 'Equipment BE1',
                'siteRef': 'site/B',
            }})
        Entity.objects.get_or_create(entity_id='@B-E2', defaults={
            'm_tags': ['equip', 'siteMeter', 'elecMeter'],
            'kv_tags': {
                'id': 'equip/B/E2',
                'dis': 'Equipment BE2',
                'siteRef': 'site/B',
            }})
        Entity.objects.get_or_create(entity_id='@C-E1', defaults={
            'm_tags': ['equip', 'siteMeter'],
            'kv_tags': {
                'id': 'equip/C/E1',
                'dis': 'Equipment CE1',
                'siteRef': 'site/C',
            }})

        Entity.objects.get_or_create(entity_id='@A-E1-KWH', defaults={
            'm_tags': ['point', 'his', 'elecKwh'],
            'kv_tags': {
                'id': 'point/A/E1/KWH',
                'dis': 'Point AE1KWH Meter',
                'siteRef': 'site/A',
                'equipRef': 'equip/A/E1',
                'kind': 'Number',
                'unit': 'kWh',
            }})
        Entity.objects.get_or_create(entity_id='@A-E1-KW', defaults={
            'm_tags': ['point', 'his', 'elecKw'],
            'kv_tags': {
                'id': 'point/A/E1/KW',
                'dis': 'Point AE1KW Meter',
                'siteRef': 'site/A',
                'equipRef': 'equip/A/E1',
                'kind': 'Number',
                'unit': 'kW',
            }})

        Entity.objects.get_or_create(entity_id='@B-E2-Fan', defaults={
            'm_tags': ['point', 'his', 'fan', 'cool'],
            'kv_tags': {
                'id': 'point/B/E2/Fan',
                'dis': 'Point BE2 Fan',
                'siteRef': 'site/B',
                'equipRef': 'equip/B/E2',
                'kind': 'Bool',
            }})

    def setUp(self):
        self._cleanup_data()

    def tearDown(self):
        self._cleanup_data()

    def _cleanup_data(self):
        Entity.objects.filter(entity_id__startswith='_test').delete()

    def test_about(self):
        url = reverse('haystack:about')
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response['Content-Type'], 'text/zinc;charset=utf-8')
        self.assertContains(response, 'vendorUri')
        self.assertContains(response, 'haystackVersion')
        self.assertContains(response, '"Opentaps-SEAS Haystack"')
        self.assertContains(response, '"opensourcestrategies.com"')

    def test_ops(self):
        url = reverse('haystack:ops')
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response['Content-Type'], 'text/zinc;charset=utf-8')
        self.assertContains(response, '"about"')
        self.assertContains(response, '"Summary information for server"')
        self.assertContains(response, '"ops"')
        self.assertContains(response, '"Operations supported by this server"')
        self.assertContains(response, '"formats"')
        self.assertContains(response, '"Grid data formats supported by this server"')
        self.assertContains(response, '"read"')
        self.assertContains(response, '"Read entity records in database"')
        self.assertContains(response, '"hisRead"')
        self.assertContains(response, '"Read time series from historian"')
        self.assertContains(response, '"nav"')
        self.assertContains(response, '"Navigate record tree"')

    def test_formats(self):
        url = reverse('haystack:formats')
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response['Content-Type'], 'text/zinc;charset=utf-8')
        self.assertContains(response, '"text/zinc",M,M')

    def test_nav(self):
        url = reverse('haystack:nav')
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response['Content-Type'], 'text/zinc;charset=utf-8')
        self.assertContains(response, '"Richmond,VA"')
        self.assertContains(response, '"Washington,DC"')
        self.assertContains(response, '"@A"')
        self.assertContains(response, '"@B"')
        self.assertContains(response, '"@C"')
        self.assertContains(response, 'navId')
        self.assertContains(response, 'geoAddr')
        self.assertContains(response, ',site')
        self.assertContains(response, '"New_York"')
        self.assertContains(response, '"site/A"')
        self.assertContains(response, '"site/B"')
        self.assertContains(response, '"site/C"')
        self.assertNotContains(response, 'point')
        self.assertNotContains(response, 'siteMeter')
        self.assertNotContains(response, '@A-E1')

        response = self.client.get(url, {'navId': '@A'})
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response['Content-Type'], 'text/zinc;charset=utf-8')
        self.assertNotContains(response, 'Richmond,VA')
        self.assertContains(response, ',siteRef')
        self.assertContains(response, ',siteMeter')
        self.assertContains(response, ',elecMeter')
        self.assertContains(response, '"site/A"')
        self.assertContains(response, '"@A-E1"')
        self.assertContains(response, '"@A-E2"')
        self.assertNotContains(response, 'point')
        self.assertNotContains(response, '@B')
        self.assertNotContains(response, '@C')

        response = self.client.get(url, {'navId': '@C'})
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response['Content-Type'], 'text/zinc;charset=utf-8')
        self.assertNotContains(response, 'Richmond,VA')
        self.assertNotContains(response, 'Washington')
        self.assertContains(response, ',siteRef')
        self.assertContains(response, ',siteMeter')
        self.assertNotContains(response, 'elecMeter')
        self.assertNotContains(response, 'point')
        self.assertContains(response, '"site/C"')
        self.assertContains(response, '"@C-E1"')
        self.assertNotContains(response, '@A')
        self.assertNotContains(response, '@B')

        response = self.client.get(url, {'navId': '@A-E1'})
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response['Content-Type'], 'text/zinc;charset=utf-8')
        self.assertNotContains(response, 'Richmond,VA')
        self.assertContains(response, ',point')
        self.assertContains(response, ',his')
        self.assertContains(response, ',equipRef')
        self.assertContains(response, ',siteRef')
        self.assertContains(response, ',elecKw')
        self.assertContains(response, ',elecKwh')
        self.assertNotContains(response, ',siteMeter')
        self.assertNotContains(response, ',elecMeter')
        self.assertContains(response, '"equip/A/E1"')
        self.assertContains(response, '"@A-E1-KW"')
        self.assertContains(response, '"@A-E1-KWH"')
        self.assertContains(response, '"Point AE1KW Meter"')
        self.assertContains(response, '"Point AE1KWH Meter"')
        self.assertNotContains(response, 'Fan')
        self.assertNotContains(response, 'fan')
        self.assertNotContains(response, 'cool')
        self.assertNotContains(response, '"@A-E2"')
        self.assertNotContains(response, '@B')
        self.assertNotContains(response, '@C')

        response = self.client.get(url, {'navId': '@B-E2'})
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response['Content-Type'], 'text/zinc;charset=utf-8')
        self.assertNotContains(response, 'Richmond,VA')
        self.assertContains(response, ',point')
        self.assertContains(response, ',his')
        self.assertContains(response, ',equipRef')
        self.assertContains(response, ',siteRef')
        self.assertNotContains(response, ',elecKw')
        self.assertNotContains(response, ',elecKwh')
        self.assertNotContains(response, ',siteMeter')
        self.assertNotContains(response, ',elecMeter')
        self.assertContains(response, '"equip/B/E2"')
        self.assertContains(response, '"@B-E2-Fan"')
        self.assertNotContains(response, '"@A-E1"')
        self.assertNotContains(response, '"@A-E1-KW"')
        self.assertNotContains(response, '"@A-E1-KWH"')
        self.assertNotContains(response, '"Point AE1KW Meter"')
        self.assertNotContains(response, '"Point AE1KWH Meter"')
        self.assertContains(response, 'Fan')
        self.assertContains(response, 'fan')
        self.assertContains(response, 'cool')
        self.assertNotContains(response, '"@B-Eq"')
        self.assertNotContains(response, '@A')
        self.assertNotContains(response, '@C')

    def test_read_by_id(self):
        url = reverse('haystack:read')
        response = self.client.get(url)
        # this needs a filter or id parameter
        self.assertEquals(response.status_code, 404)
        self.assertEquals(response['Content-Type'], 'text/zinc;charset=utf-8')

        response = self.client.get(url, {'id': '@A'})
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response['Content-Type'], 'text/zinc;charset=utf-8')
        self.assertContains(response, '"Richmond,VA"')
        self.assertContains(response, '"site/A"')
        self.assertNotContains(response, '"site/B"')
        self.assertNotContains(response, '"@C"')
        self.assertNotContains(response, 'navId')
        self.assertContains(response, 'geoAddr')
        self.assertContains(response, ',site')
        self.assertContains(response, '"New_York"')
        self.assertNotContains(response, 'point')
        self.assertNotContains(response, 'siteMeter')
        self.assertNotContains(response, '@A-E1')
        self.assertNotContains(response, '@B-E1')
        self.assertNotContains(response, '@C-E1')

        response = self.client.get(url, {'id': '@C'})
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response['Content-Type'], 'text/zinc;charset=utf-8')
        self.assertNotContains(response, '"Richmond,VA"')
        self.assertContains(response, '"Washington,DC"')
        self.assertNotContains(response, '"site/A"')
        self.assertNotContains(response, '"@B"')
        self.assertContains(response, '"site/C"')
        self.assertNotContains(response, 'navId')
        self.assertContains(response, 'geoAddr')
        self.assertContains(response, ',site')
        self.assertContains(response, '"New_York"')
        self.assertNotContains(response, 'point')
        self.assertNotContains(response, 'siteMeter')
        self.assertNotContains(response, '@A-E1')
        self.assertNotContains(response, '@B-E1')
        self.assertNotContains(response, '@C-E1')

        response = self.client.get(url, {'id': '@A-E1'})
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response['Content-Type'], 'text/zinc;charset=utf-8')
        self.assertNotContains(response, '"Richmond,VA"')
        self.assertNotContains(response, '"Washington,DC"')
        self.assertContains(response, '"site/A"')
        self.assertNotContains(response, '"site/B"')
        self.assertNotContains(response, '"@C"')
        self.assertNotContains(response, 'navId')
        self.assertNotContains(response, 'geoAddr')
        self.assertContains(response, ',siteRef')
        self.assertContains(response, ',equip')
        self.assertContains(response, ',siteMeter')
        self.assertNotContains(response, 'point')
        self.assertNotContains(response, 'elecMeter')
        self.assertContains(response, 'equip/A/E1')
        self.assertNotContains(response, '@A-E1')
        self.assertNotContains(response, 'equip/B/E1')
        self.assertNotContains(response, '@C-E1')

    def test_read_by_filter(self):
        url = reverse('haystack:read')
        response = self.client.get(url)
        # this needs a filter or id parameter
        self.assertEquals(response.status_code, 404)
        self.assertEquals(response['Content-Type'], 'text/zinc;charset=utf-8')

        response = self.client.get(url, {'filter': 'site'})
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response['Content-Type'], 'text/zinc;charset=utf-8')
        self.assertContains(response, '"Richmond,VA"')
        self.assertContains(response, '"Washington,DC"')
        self.assertContains(response, '"site/A"')
        self.assertContains(response, '"site/B"')
        self.assertContains(response, '"site/C"')
        self.assertNotContains(response, 'navId')
        self.assertContains(response, 'geoAddr')
        self.assertContains(response, ',site')
        self.assertContains(response, '"New_York"')
        self.assertNotContains(response, 'point')
        self.assertNotContains(response, 'fan')
        self.assertNotContains(response, 'his')
        self.assertNotContains(response, 'siteMeter')
        self.assertNotContains(response, 'elecMeter')
        self.assertNotContains(response, '@A-E1')
        self.assertNotContains(response, 'equip/A/E1')
        self.assertNotContains(response, 'equip/B/E1')
        self.assertNotContains(response, 'equip/C/E1')
        self.assertNotContains(response, '@B-E1')
        self.assertNotContains(response, '@C-E1')

        response = self.client.get(url, {'filter': 'site and geoState=="DC"'})
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response['Content-Type'], 'text/zinc;charset=utf-8')
        self.assertNotContains(response, '"Richmond,VA"')
        self.assertContains(response, '"Washington,DC"')
        self.assertNotContains(response, '"@A"')
        self.assertNotContains(response, '"@B"')
        self.assertNotContains(response, '"@C"')
        self.assertNotContains(response, '"site/A"')
        self.assertNotContains(response, '"site/B"')
        self.assertContains(response, '"site/C"')
        self.assertNotContains(response, 'navId')
        self.assertContains(response, 'geoAddr')
        self.assertContains(response, ',site')
        self.assertContains(response, '"New_York"')
        self.assertNotContains(response, 'point')
        self.assertNotContains(response, 'fan')
        self.assertNotContains(response, 'his')
        self.assertNotContains(response, 'siteMeter')
        self.assertNotContains(response, 'elecMeter')
        self.assertNotContains(response, 'equip/A/E1')
        self.assertNotContains(response, 'equip/B/E1')
        self.assertNotContains(response, 'equip/C/E1')
        self.assertNotContains(response, '@A-E1')
        self.assertNotContains(response, '@B-E1')
        self.assertNotContains(response, '@C-E1')

        response = self.client.get(url, {'filter': 'site and geoState=="DC"'})
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response['Content-Type'], 'text/zinc;charset=utf-8')
        self.assertNotContains(response, '"Richmond,VA"')
        self.assertContains(response, '"Washington,DC"')
        self.assertNotContains(response, '"@A"')
        self.assertNotContains(response, '"site/A"')
        self.assertNotContains(response, '"@B"')
        self.assertNotContains(response, '"site/B"')
        self.assertContains(response, '"site/C"')
        self.assertNotContains(response, 'navId')
        self.assertContains(response, 'geoAddr')
        self.assertContains(response, ',site')
        self.assertContains(response, '"New_York"')
        self.assertNotContains(response, 'point')
        self.assertNotContains(response, 'fan')
        self.assertNotContains(response, 'his')
        self.assertNotContains(response, 'siteMeter')
        self.assertNotContains(response, 'elecMeter')
        self.assertNotContains(response, 'equip/A/E1')
        self.assertNotContains(response, 'equip/B/E1')
        self.assertNotContains(response, 'equip/C/E1')
        self.assertNotContains(response, '@A-E1')
        self.assertNotContains(response, '@B-E1')
        self.assertNotContains(response, '@C-E1')

    def test_read_by_filter_num_compare(self):
        url = reverse('haystack:read')

        response = self.client.get(url, {'filter': 'site and area>=2000'})
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response['Content-Type'], 'text/zinc;charset=utf-8')
        self.assertNotContains(response, '"@A"')
        self.assertNotContains(response, '"site/A"')
        self.assertContains(response, '"site/B"')
        self.assertContains(response, '"site/C"')

        response = self.client.get(url, {'filter': 'site and area<=4000'})
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response['Content-Type'], 'text/zinc;charset=utf-8')
        self.assertContains(response, '"site/A"')
        self.assertContains(response, '"site/B"')
        self.assertContains(response, '"site/C"')

        response = self.client.get(url, {'filter': 'site and area<3000'})
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response['Content-Type'], 'text/zinc;charset=utf-8')
        self.assertContains(response, '"site/A"')
        self.assertContains(response, '"site/B"')
        self.assertNotContains(response, '"site/C"')
        self.assertNotContains(response, '"@C"')

        response = self.client.get(url, {'filter': 'site and area==1000'})
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response['Content-Type'], 'text/zinc;charset=utf-8')
        self.assertContains(response, '"site/A"')
        self.assertNotContains(response, '"@B"')
        self.assertNotContains(response, '"site/B"')
        self.assertNotContains(response, '"@C"')
