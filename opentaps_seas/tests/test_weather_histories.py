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

import numpy as np

from .base import OpentapsSeasTestCase
from opentaps_seas.core.models import WeatherStation
from opentaps_seas.core.utils import get_weather_history_for_station


class WeatherHistoryAPITests(OpentapsSeasTestCase):

    def setUp(self):
        self.model_id = '_test/myweatherhistory'
        self.weather_station_id="NYC_STATION"

        # Create weather station temporary with usaf id for Central Park, NYC
        weather_station = WeatherStation(weather_station_id=self.weather_station_id,
                                         weather_station_code='725053',
                                         station_name='CENTRAL PARK',
                                         country='US',
                                         state='NY',
                                         latitude=40.799,
                                         longitude=-73.969,
                                         elevation=42.7,
                                         elevation_uom_id='length_m',
                                         source='TestCase'
                                         )
        weather_station.save()

    def tearDown(self):
        self._cleanup_data()

    def _cleanup_data(self):
        WeatherStation.objects.filter(weather_station_id=self.weather_station_id).delete()

    def test_get_station(self):
        # Get weather station
        weather_station = WeatherStation.objects.filter(weather_station_id=self.weather_station_id).first()
        self.assertIsNotNone(weather_station, "Cannot get weather station")

        # Get historical data and see 
        historical_data = get_weather_history_for_station(weather_station)
        self.assertIsNotNone(historical_data, "Cannot retrieve historical data with eeweather API")

        # Check values within a wide but realistic range
        for dt, deg_c in historical_data.iteritems():
            if not np.isnan(deg_c):
                self.assertTrue(-20 < deg_c and deg_c < 50, "Temperature is out of range (-20, 50), {temperature}".format(temperature=deg_c))
