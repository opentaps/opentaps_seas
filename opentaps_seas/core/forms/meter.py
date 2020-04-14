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
import json
import csv
import solaredge
from io import TextIOWrapper
from .. import utils
from ..models import Meter
from ..models import MeterHistory
from ..models import MeterRatePlanHistory
from ..models import UnitOfMeasure
from ..models import WeatherStation
from .widgets import make_custom_datefields
from .widgets import DateTimeField
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from django import forms
from django.utils.timezone import now
from greenbutton import parse

logger = logging.getLogger(__name__)


class MeterDataSolarEdgeForm(forms.Form):
    meter = forms.CharField(max_length=255)
    time_unit = forms.CharField(label='Time Interval', max_length=255, initial='HOUR')
    from_date = DateTimeField(label='From Date', required=False)
    to_date = DateTimeField(label='To Date', initial=now, required=False)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def is_valid(self):
        if not super().is_valid():
            return False
        # note the SolarEdge API is limited:
        #  limited to one year when using timeUnit=DAY (i.e., daily resolution)
        #  limited to one month when using timeUnit=QUARTER_OF_AN_HOUR or timeUnit=HOUR
        time_unit = self.cleaned_data['time_unit']
        from_date = self.cleaned_data['from_date']
        to_date = self.cleaned_data['to_date']
        if from_date:
            date_range = to_date - from_date
            if time_unit == 'DAY':
                if abs(date_range.days) > 365:
                    self.add_error('from_date', 'The range should not exceed one year.')
                    return False
            else:
                if abs(date_range.days) > 31:
                    self.add_error('from_date', 'The range should not exceed one month.')
                    return False
        return True

    def save(self, commit=True):
        meter = self.cleaned_data['meter']
        time_unit = self.cleaned_data['time_unit']
        from_date = self.cleaned_data['from_date']
        to_date = self.cleaned_data['to_date']

        import_errors = False
        count = 0

        m = Meter.objects.get(meter_id=meter)
        se_setting = m.solaredgesetting_set.first()

        logger.info('Getting SolarEdge power details for site: %s', se_setting.site_id)
        se = solaredge.Solaredge(se_setting.api_key)
        start = from_date.strftime("%Y-%m-%d %H:%M:%S")
        end = to_date.strftime("%Y-%m-%d %H:%M:%S")
        logger.info('Getting SolarEdge power details for site: %s from %s to %s with time interval %s',
                    se_setting.site_id, start, end, time_unit)
        # get the site timezone
        tz_str = None
        site_location = se_setting.site_details.get('location')
        if site_location and 'timeZone' in site_location:
            tz_str = site_location['timeZone']
        tz = utils.parse_timezone(tz_str, 'UTC')
        from_date = from_date.replace(tzinfo=tz)
        to_date = to_date.replace(tzinfo=tz)
        res = se.get_energy_details(se_setting.site_id, start, end, time_unit=time_unit)
        logger.info('Got SolarEdge power details: %s', res)
        se_meters = res['energyDetails']['meters']
        unit = res['energyDetails']['unit']
        # find the proper UOM, this contains the code
        uom = UnitOfMeasure.objects.get(code=unit, type='energy')
        # duration is from the time
        time_unit = res['energyDetails']['timeUnit']
        if time_unit == 'HOUR':
            duration = 3600
        elif time_unit == 'QUARTER_OF_AN_HOUR':
            duration = 900
        elif time_unit == 'DAY':
            duration = 86400
        else:
            import_errors = 'Returned timeUnit not recognized: {}.'.format(time_unit)

        if not import_errors and len(se_meters) > 1:
            import_errors = 'Returned data has more than one SolarEdge meter, not sure what to do.'

        if not import_errors:
            # clear old values for the same period
            MeterHistory.objects.filter(meter=m, as_of_datetime__gte=from_date, as_of_datetime__lte=to_date).delete()
            se_values = se_meters[0]['values']
            for item in se_values:
                value = item.get('value')
                if not value:
                    value = 0
                date_str = item.get('date')
                item_date = datetime.fromisoformat(date_str).replace(tzinfo=tz)
                MeterHistory.objects.create(
                    meter=m,
                    uom=uom,
                    source='SolarEdge: {}'.format(se_setting.site_id),
                    value=value,
                    duration=duration,
                    as_of_datetime=item_date,
                    created_by_user=self.user
                    )
                count = count + 1

            if count == 0:
                import_errors = 'Nothing to Import'

        if import_errors:
            return {'import_errors': import_errors}
        else:
            return {'imported': count}


class MeterDataUploadForm(forms.Form):
    meter = forms.CharField(max_length=255)
    meter_data = forms.FileField(widget=forms.FileInput(attrs={'accept': '.csv,.xml'}))

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        meter = self.cleaned_data['meter']
        meter_data = self.cleaned_data['meter_data']
        file_name = str(meter_data)

        import_errors = False
        count = 0

        if file_name.endswith('.csv'):
            import_errors, count = self.import_csv(meter, meter_data)
        elif file_name.endswith('.xml'):
            import_errors, count = self.import_xml(meter, meter_data)
        else:
            import_errors = "Wrong file format."

        if import_errors:
            return {'import_errors': import_errors}
        else:
            return {'imported': count}

    def import_xml(self, meter, meter_data):
        fxml = TextIOWrapper(meter_data.file, encoding=meter_data.charset if meter_data.charset else 'utf-8')

        import_errors = False
        count = 0
        m = Meter.objects.get(meter_id=meter)
        if not m:
            import_errors = "Meter not found: {}".format(meter)
        else:
            try:
                ups = parse.parse_feed(fxml)
            except Exception:
                import_errors = "Cannot parse XML file."
            else:
                if ups and len(ups) > 0:
                    for up in ups:
                        for mr in up.meterReadings:
                            for ir in mr.intervalReadings:
                                count += 1
                                v = MeterHistory(meter_id=meter, uom_id=ir.value_uom_id)
                                v.source = 'XML Upload'
                                v.value = ir.value
                                v.duration = int(ir.timePeriod.duration.total_seconds())
                                v.as_of_datetime = ir.timePeriod.start
                                v.created_by_user = self.user

                                if up.localTimeParameters.tzOffset is not None:
                                    tz = timezone(timedelta(seconds=up.localTimeParameters.tzOffset))
                                    v.as_of_datetime = v.as_of_datetime.replace(tzinfo=tz)

                                if ir.cost is not None:
                                    v.cost = ir.cost
                                    v.cost_uom_id = ir.cost_uom_id

                                v.save()
                else:
                    import_errors = "Nothing to parse."

        return import_errors, count

    def import_csv(self, meter, meter_data):
        fcsv = TextIOWrapper(meter_data.file, encoding=meter_data.charset if meter_data.charset else 'utf-8')

        import_errors = False
        count = 0
        m = Meter.objects.get(meter_id=meter)
        if not m:
            import_errors = "Meter not found: {}".format(meter)
        else:
            try:
                records = csv.DictReader(fcsv, fieldnames=['dt', 'value'])
            except json.decoder.JSONDecodeError:
                import_errors = "Cannot parse CSV file."
            else:
                logger.info('MeterDataUploadForm: importing Meter CSV Data ...')
                # assume all data is in kwh for now
                uom_id = 'energy_kWh'
                # assume all data duration 1 hour for now
                duration = 3600
                if records:
                    for row in records:
                        # logger.info('MeterDataUploadForm: importing row {}'.format(row))
                        v = MeterHistory(meter_id=meter, uom_id=uom_id, duration=duration)
                        v.source = 'CSV Upload'
                        v.value = row['value']
                        v.as_of_datetime = row['dt']
                        v.created_by_user = self.user
                        v.save()
                else:
                    import_errors = "CSV file is empty."

        return import_errors, count


class MeterCreateForm(forms.ModelForm):
    formfield_callback = make_custom_datefields

    def __init__(self, *args, **kwargs):
        super(MeterCreateForm, self).__init__(*args, **kwargs)
        self.fields['meter_id'].required = False
        self.fields['site'].widget = forms.HiddenInput()

        # Dynamic load weather station list
        if 'weather_station' not in self.data:
            self.fields['weather_station'].queryset = WeatherStation.objects.none()
        # Show error message if failed to get default weather station
        if not self.data and not self.initial.get('weather_station'):
            if not hasattr(self, 'cleaned_data'):
                self.cleaned_data = {}
            error_msg = u"No weather station found for this Site. Please check that your site is set up correctly."
            self.add_error('weather_station', error_msg)

    def save(self, commit=True):
        description = self.cleaned_data['description']
        meter_id = self.cleaned_data['meter_id']
        site = self.cleaned_data['site']

        if not meter_id or meter_id == '':
            id_base = site.entity_id
            if description:
                id_base += "-" + description
            meter_id = utils.make_random_id(id_base)

        weather_station = self.cleaned_data['weather_station']
        from_datetime = self.cleaned_data['from_datetime']
        thru_datetime = self.cleaned_data['thru_datetime']

        meter = Meter(meter_id=meter_id)
        meter.site_id = site.entity_id
        meter.description = description
        if weather_station:
            meter.weather_station_id = weather_station.weather_station_id
        meter.from_datetime = from_datetime
        meter.thru_datetime = thru_datetime

        meter.save()
        self.instance = Meter.objects.get(meter_id=meter_id)
        self.cleaned_data['meter_id'] = meter_id
        self._post_clean()  # reset the form as updating the just created instance
        return self.instance

    class Meta:
        model = Meter
        fields = ["site", "meter_id", "description", "weather_station", "from_datetime", "thru_datetime"]


class MeterUpdateForm(forms.ModelForm):
    formfield_callback = make_custom_datefields

    def __init__(self, *args, **kwargs):
        super(MeterUpdateForm, self).__init__(*args, **kwargs)
        self.fields['meter_id'].widget = forms.HiddenInput()

        # Dynamic load weather station list
        if 'weather_station' not in self.data:
            self.fields['weather_station'].queryset = WeatherStation.objects.none()

    class Meta:
        model = Meter
        fields = ["meter_id", "description", "weather_station", "from_datetime", "thru_datetime"]


class MeterRatePlanHistoryUpdateForm(forms.ModelForm):
    formfield_callback = make_custom_datefields

    def __init__(self, *args, **kwargs):
        super(MeterRatePlanHistoryUpdateForm, self).__init__(*args, **kwargs)

    class Meta:
        model = MeterRatePlanHistory
        fields = ["rate_plan_history_id", "thru_datetime"]
