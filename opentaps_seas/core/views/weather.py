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
from timezonefinder import TimezoneFinder

from .common import GoogleApiMixin
from .common import WithBreadcrumbsMixin
from .. import utils
from ..forms.weather import WeatherStationFetchDataForm
from ..models import datetime_to_string
from ..models import WeatherStation
from ..models import SiteView

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views.generic import DetailView
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.edit import FormView

logger = logging.getLogger(__name__)


def weather_data_json(request, weather_station_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)

    m = WeatherStation.objects.get(weather_station_id=weather_station_id)
    if not m:
        logger.warning('No Weather Station found with weather_station_id = %s', weather_station_id)
        return JsonResponse({'error': 'Weather data not found : {}'.format(weather_station_id)}, status=404)

    get_all = False
    unit_f = True
    trange = 24
    srange = request.GET.get('range')
    if srange:
        if srange != 'all':
            try:
                trange = int(srange)
                if trange < 0:
                    trange = -trange
            except Exception:
                trange = 24
        else:
            get_all = True

    unit = request.GET.get('unit')
    if unit == 'c':
        unit_f = False

    # Select last <trange> records
    weater_data = []
    qs = m.weatherhistory_set

    # set timezones
    tz = None
    if request.GET.get('site'):
        try:
            site = SiteView.objects.get(entity_id=request.GET.get('site'))
            tz = utils.parse_timezone(site.kv_tags.get('tz'))
        except Exception:
            tz = None

    if not tz:
        tz = utils.parse_timezone(request.GET.get('tz'))

    if not tz:
        # find from the station position
        tf = TimezoneFinder()
        tz = utils.parse_timezone(tf.timezone_at(lng=m.longitude, lat=m.latitude))

    data_list = []
    if get_all:
        data_list = qs.order_by("as_of_datetime")
        for data in data_list:
            dt = datetime_to_string(data.as_of_datetime, tz=tz)
            item = {'datetime': dt}
            if unit_f:
                item['temp'] = data.temp_f
            else:
                item['temp'] = data.temp_c
            weater_data.append(item)

        return JsonResponse({'tz': tz.tzname(None), 'values': weater_data})
    else:
        data_list = qs.order_by("-as_of_datetime")[:trange]
        for data in data_list:
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


class WeatherStationFetchData(LoginRequiredMixin, WithBreadcrumbsMixin, SingleObjectMixin, FormView):
    model = WeatherStation
    slug_field = "weather_station_id"
    slug_url_kwarg = "weather_station_id"
    template_name = 'core/weather_station_fetch_data.html'
    form_class = WeatherStationFetchDataForm

    def get_success_url(self):
        obj = self.get_object()
        return obj.get_absolute_url()

    def get_form_kwargs(self, *args, **kwargs):
        form_data = super().get_form_kwargs(*args, **kwargs)

        try:
            if not self.request.POST:
                ws = self.get_object()
                initial_values = {}
                if ws:
                    initial_values['weather_station_id'] = ws.weather_station_id
                    if ws.latest_reading:
                        initial_values['from_date'] = ws.latest_reading.as_of_datetime
                form_data['initial'] = initial_values
        except Exception as e:
            logging.error(e)

        return form_data

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            try:
                form_results = form.save()
                if form_results is not None and len(form_results):
                    messages.success(self.request, 'Imported {} temperature records.'.format(len(form_results)))
            except Exception as e:
                logging.exception(e)
                if e.__class__.__name__ == 'UnrecognizedUSAFIDError':
                    messages.error(self.request, 'Unrecognized Weather Station USAF ID, cannot fetch data.')
                else:
                    messages.error(self.request, 'Unexpected Error {}: {}'.format(e.__class__.__name__, e))

            return self.form_valid(form)
        else:
            messages.error(self.request, 'Invalid request')
            return self.form_invalid(form)


weather_station_fetch_data = WeatherStationFetchData.as_view()
