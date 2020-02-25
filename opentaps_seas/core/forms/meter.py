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
from io import TextIOWrapper
from .. import utils
from ..models import Meter
from ..models import MeterHistory
from ..models import WeatherStation
from flatpickr import DateTimePickerInput
from django import forms
from greenbutton import parse

logger = logging.getLogger(__name__)


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
        rate_plan = self.cleaned_data['rate_plan']
        from_datetime = self.cleaned_data['from_datetime']
        thru_datetime = self.cleaned_data['thru_datetime']

        meter = Meter(meter_id=meter_id)
        meter.site_id = site.entity_id
        meter.description = description
        if weather_station:
            meter.weather_station_id = weather_station.weather_station_id
        if rate_plan:
            meter.rate_plan_id = rate_plan.rate_plan_id
        meter.from_datetime = from_datetime
        meter.thru_datetime = thru_datetime

        meter.save()
        self.instance = Meter.objects.get(meter_id=meter_id)
        self.cleaned_data['meter_id'] = meter_id
        self._post_clean()  # reset the form as updating the just created instance
        return self.instance

    class Meta:
        date_time_options = {"dateFormat": "Y-m-d H:i:S", "time_24hr": "true", "allowInput": "true",
                             "enableSeconds": "true", "minuteIncrement": 1}
        model = Meter
        fields = ["site", "meter_id", "description", "weather_station", "rate_plan", "from_datetime", "thru_datetime"]
        widgets = {'from_datetime': DateTimePickerInput(options=date_time_options),
                   'thru_datetime': DateTimePickerInput(options=date_time_options)}


class MeterUpdateForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(MeterUpdateForm, self).__init__(*args, **kwargs)
        self.fields['meter_id'].widget = forms.HiddenInput()

        # Dynamic load weather station list
        if 'weather_station' not in self.data:
            self.fields['weather_station'].queryset = WeatherStation.objects.none()

    class Meta:
        date_time_options = {"dateFormat": "Y-m-d H:i:S", "time_24hr": "true", "allowInput": "true",
                             "enableSeconds": "true", "minuteIncrement": 1}
        model = Meter
        fields = ["meter_id", "description", "weather_station", "rate_plan", "from_datetime", "thru_datetime"]
        widgets = {'from_datetime': DateTimePickerInput(options=date_time_options),
                   'thru_datetime': DateTimePickerInput(options=date_time_options)}
