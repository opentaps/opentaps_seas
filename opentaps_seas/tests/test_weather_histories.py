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
from opentaps_seas.core.models import WeatherHistory
from opentaps_seas.core.utils import get_weather_history_for_station


class WeatherHistoryAPITests(TestCase):

    def setUp(self):
        self.model_id = '_test/myweatherhistory'

    def test_get_station(self):
        # Not all of the weather station doesn't supported by eeweather
        # So we use sample id here
        usaf_id = '724010'

        # Get weather station
        weather_station = WeatherStation.objects.filter(weather_station_code=usaf_id).first()
        self.assertIsNotNone(weather_station, "Cannot get weather station with USAF ID {id}".format(id=usaf_id))

        # Get historical data and see 
        historical_data = get_weather_history_for_station(weather_station)
        self.assertIsNotNone(historical_data, "Cannot retrieve historical data with eeweather API")

        # Check values within a wide but realistic range
        for dt, deg_c in historical_data.iteritems():
            self.assertTrue(-20 < deg_c and deg_c < 50, "Temperature is out of range (-20, 50), {temperature}".format(temperature=deg_c))
