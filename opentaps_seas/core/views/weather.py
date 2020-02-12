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

from .common import GoogleApiMixin
from .common import WithBreadcrumbsMixin
from .. import utils
from ..models import datetime_to_string
from ..models import WeatherStation
from ..models import SiteView

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views.generic import DetailView

logger = logging.getLogger(__name__)


def weather_data_json(request, weather_station_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)

    m = WeatherStation.objects.get(weather_station_id=weather_station_id)
    if not m:
        logger.warning('No Weather Station found with weather_station_id = %s', weather_station_id)
        return JsonResponse({'error': 'Weather data not found : {}'.format(weather_station_id)}, status=404)

    trange = 24
    srange = request.GET.get('range')
    if srange:
        try:
            trange = int(srange)
            if trange < 0:
                trange = -trange
        except Exception:
            trange = 24

    # Select last <trange> records
    weater_data = []
    qs = m.weatherhistory_set

    # set timezones, default to UTC
    tz = None
    if request.GET.get('site'):
        try:
            site = SiteView.objects.get(entity_id=request.GET.get('site'))
            tz = utils.parse_timezone(site.kv_tags.get('tz'))
        except Exception:
            tz = None

    if not tz:
        tz = utils.parse_timezone(request.GET.get('tz'), 'UTC')

    for data in qs.order_by("-as_of_datetime")[:trange]:
        # Prevent adding duplicates
        dt = datetime_to_string(data.as_of_datetime, tz=tz)
        if weater_data and dt == weater_data[-1]['datetime']:
            continue
        weater_data.append({
            'datetime': dt,
            'temp_c': data.temp_c,
            'temp_f': data.temp_f
        })

    return JsonResponse({'tz': tz.tzname(None), 'values': list(reversed(weater_data))})


@login_required()
def weather_stations_json(request):
    data = []
    for weather_station in WeatherStation.objects.all():
        data.append({
            'id': weather_station.weather_station_id,
            'value': '{code} ({name})'.format(code=weather_station.weather_station_code,
                                              name=weather_station.station_name)
        })

    return JsonResponse({'items': data})


class WeatherStationDetail(LoginRequiredMixin, GoogleApiMixin, WithBreadcrumbsMixin, DetailView):
    model = WeatherStation
    slug_field = "weather_station_id"
    slug_url_kwarg = "weather_station_id"
    template_name = 'core/weather_station_detail.html'


weather_station_detail = WeatherStationDetail.as_view()
