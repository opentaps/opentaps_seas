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
import os
import eeweather

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from opentaps_seas.core.models import WeatherStation
from opentaps_seas.core.utils import get_weather_station_for_location


class WeatherStationAPITests(TestCase):

    def setUp(self):
        self._cleanup_data()
        self.model_id = '_test/myweatherstation'

    def tearDown(self):
        self._cleanup_data()

    def _cleanup_data(self):
        return

    def test_get_station(self):
        ''' Test API result with this demo
        http://eemeter.openee.io/tutorial.html#using-eeweather
        '''

        latitude = 38.1
        longitude = -118.3
        usaf_id = '724856'

        station_id = get_weather_station_for_location(latitude, longitude, False)
        if not station_id:
            self.assertFalse("Cannot get weather station for location ({lat}, {lon})".format(lat=latitude, lon=longitude))
        else:
            self.assertEqual(station_id, usaf_id)
