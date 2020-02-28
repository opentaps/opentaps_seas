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
from ..utils import get_weather_history_for_station
from ..models import WeatherStation
from .widgets import DateTimeField
from django import forms
from django.utils.timezone import now

logger = logging.getLogger(__name__)


class WeatherStationFetchDataForm(forms.Form):

    weather_station_id = forms.CharField(label='Station')
    from_date = DateTimeField(label='From Date', required=False)
    thru_date = DateTimeField(label='Thru Date', initial=now, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        weather_station_id = self.initial.get('weather_station_id')
        if not weather_station_id and self.data:
            weather_station_id = self.data.get('weather_station_id')
        if weather_station_id:
            try:
                WeatherStation.objects.get(weather_station_id=weather_station_id)
                self.fields['weather_station_id'].widget = forms.HiddenInput()
            except WeatherStation.DoesNotExist:
                logger.error('WeatherStationFetchDataForm: Weather Station not found with id = %s', weather_station_id)
                self.initial.pop('weather_station_id')

    def is_valid(self):
        if not super().is_valid():
            logger.error('WeatherStationFetchDataForm: super not valid')
            return False
        logger.info('WeatherStationFetchDataForm: check is_valid')

        weather_station_id = self.cleaned_data['weather_station_id']
        # check meter exists, note weather_station_id is already required
        if weather_station_id:
            try:
                WeatherStation.objects.get(weather_station_id=weather_station_id)
            except WeatherStation.DoesNotExist:
                logger.error('WeatherStationFetchDataForm: WeatherStation not found with id = %s', weather_station_id)
                self.add_error('weather_station_id', 'Meter {} does not exist.'.format(weather_station_id))
                return False

        return True

    def save(self, commit=True):
        weather_station_id = self.cleaned_data['weather_station_id']
        from_date = self.cleaned_data['from_date']
        thru_date = self.cleaned_data['thru_date']
        logger.info('WeatherStationFetchDataForm: for WeatherStation %s, from %s to %s',
                    weather_station_id, from_date, thru_date)
        ws = WeatherStation.objects.get(weather_station_id=weather_station_id)
        results = get_weather_history_for_station(ws, start_date=from_date, end_date=thru_date)
        logger.info('WeatherStationFetchDataForm: for WeatherStation %s, from %s to %s got %s',
                    weather_station_id, from_date, thru_date, results)

        return results
