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
from eemeter import NoBaselineDataError
from . import utils
from . import tasks
from ..core.models import Meter
from .models import BaselineModel
from django import forms
from django.forms.widgets import HiddenInput
from django.utils.timezone import now

logger = logging.getLogger(__name__)


class MeterInput(forms.TextInput):
    template_name = 'eemeter/forms/meterinput.html'


class MeterField(forms.CharField):
    widget = MeterInput


class MeterModelCreateForm(forms.ModelForm):
    meter_id = MeterField(label='Meter', max_length=255, required=False)
    thru_date = forms.DateTimeField(label='Ending Date', initial=now, required=False)
    use_async = forms.BooleanField(label='Run Async', required=False)

    def __init__(self, *args, **kwargs):
        super(MeterModelCreateForm, self).__init__(*args, **kwargs)
        meter_id = self.initial.get('meter_id')
        if meter_id:
            try:
                Meter.objects.get(meter_id=meter_id)
                self.fields['meter_id'].widget = HiddenInput()
            except Meter.DoesNotExist:
                logger.error('CalcMeterSavingsForm: Meter not found with id = %s', meter_id)
                self.initial.pop('meter_id')

    def is_valid(self):
        if not super().is_valid():
            logger.error('MeterModelCreateForm: super not valid')
            return False
        logger.info('MeterModelCreateForm: check is_valid')

        meter_id = self.cleaned_data['meter_id']
        frequency = self.cleaned_data['frequency']
        # check meter exists, note meter_id is already required
        if meter_id:
            try:
                self.meter = Meter.objects.get(meter_id=meter_id)
                thru_date = self.cleaned_data['thru_date']
                logger.info('MeterModelCreateForm: checking read_meter_data ending in %s', thru_date)
                self.read_meter_data = utils.read_meter_data(self.meter, freq=frequency, blackout_start_date=thru_date)
            except Meter.DoesNotExist:
                logger.error('MeterModelCreateForm: Meter not found with id = %s', meter_id)
                self.add_error('meter_id', 'Meter {} does not exist.'.format(meter_id))
                return False
            except NoBaselineDataError:
                logger.error('MeterModelCreateForm: Cannot get baseline data from = %s', thru_date)
                if thru_date:
                    self.add_error('thru_date', '''Meter does not have enough baseline data ending in {},
                        try leaving blank.'''.format(thru_date))
                else:
                    self.add_error('thru_date', 'Meter does not have enough baseline data.')
                return False

        return True

    def save(self, commit=True):
        if commit:
            if self.cleaned_data['use_async']:
                logger.info('MeterModelCreateForm: running Async ...')
                return self.run_async()
            else:
                return self.run()
        return self.instance

    def get_task_params(self):
        d = self.cleaned_data.copy()
        d.update({'meter': self.meter, 'read_meter_data': self.read_meter_data})
        return d

    def run_async(self):
        return tasks.create_meter_model_task.delay(self.cleaned_data.copy())

    def run(self):
        self.instance = tasks.create_meter_model(self.get_task_params())
        self._post_clean()  # reset the form as updating the just created instance
        return self.instance

    class Meta:
        model = BaselineModel
        fields = ["meter_id", "frequency", "description"]


class CalcMeterSavingsForm(forms.Form):
    meter_id = MeterField(label='Meter', max_length=255, required=True)
    model_id = forms.CharField(label='Model', max_length=255, required=True)
    from_datetime = forms.DateTimeField(label='From', required=True)
    to_datetime = forms.DateTimeField(label='To', required=True)
    use_async = forms.BooleanField(label='Run Async', required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        meter = None
        model = None
        meter_id = self.initial.get('meter_id')
        if meter_id:
            try:
                meter = Meter.objects.get(meter_id=meter_id)
                self.fields['meter_id'].widget = HiddenInput()
            except Meter.DoesNotExist:
                logger.error('CalcMeterSavingsForm: Meter not found with id = %s', meter_id)
                self.initial.pop('meter_id')
        model_id = self.initial.get('model_id')
        if model_id:
            try:
                model = BaselineModel.objects.get(id=model_id)
                self.fields['model_id'].widget = HiddenInput()
            except BaselineModel.DoesNotExist:
                logger.error('CalcMeterSavingsForm: BaselineModel not found with id = %s', model_id)
                self.initial.pop('model_id')

        if meter and model:
            # set the initial from date to the model last calculated date
            # else use the model first data date
            if model.last_calc_saving_datetime:
                self.initial['from_datetime'] = model.last_calc_saving_datetime
            else:
                self.initial['from_datetime'] = meter.get_meter_data().first().as_of_datetime

        if meter:
            # set the end date to the last meter data
            self.initial['to_datetime'] = meter.get_meter_data().last().as_of_datetime

    def is_valid(self):
        if not super().is_valid():
            logger.error('CalcMeterSavingsForm: super not valid')
            return False
        logger.info('CalcMeterSavingsForm: check is_valid')

        meter_id = self.cleaned_data['meter_id']
        meter = None
        if meter_id:
            # check meter exists
            try:
                meter = Meter.objects.get(meter_id=meter_id)
            except Meter.DoesNotExist:
                logger.error('CalcMeterSavingsForm: Meter not found with id = %s', meter_id)
                self.add_error('meter_id', 'Meter {} does not exist.'.format(meter_id))
                return False

        model_id = self.cleaned_data['model_id']
        if model_id:
            # check meter exists
            try:
                BaselineModel.objects.get(id=model_id)
            except BaselineModel.DoesNotExist:
                logger.error('CalcMeterSavingsForm: BaselineModel not found with id = %s', model_id)
                self.add_error('model_id', 'BaselineModel {} does not exist.'.format(model_id))
                return False

        if meter:
            start = self.cleaned_data['from_datetime']
            end = self.cleaned_data['to_datetime']
            # check there is actually data for the range
            if not meter.get_meter_data(start=start, end=end).count():
                logger.error('CalcMeterSavingsForm: No Meter data found for %s from %s to %s', model_id, start, end)
                self.add_error('from_datetime', 'No Meter data found between {} and {}'.format(start, end))
                self.add_error('to_datetime', 'No Meter data found between {} and {}'.format(start, end))
                return False

        return True

    def save(self, commit=True):
        meter_id = self.cleaned_data['meter_id']
        model_id = self.cleaned_data['model_id']
        start = self.cleaned_data['from_datetime']
        end = self.cleaned_data['to_datetime']
        use_async = self.cleaned_data['use_async']
        logger.info('CalcMeterSavingsForm: for Meter %s, from %s to %s, model id %s', meter_id, start, end, model_id)

        if use_async:
            logger.info('CalcMeterSavingsForm: running Async ...')
            return self.run_async()
        else:
            model, savings = utils.calc_meter_savings(meter_id, model_id, start, end)
            self.model = model
            return savings

    def run_async(self):
        return tasks.calc_meter_savings_task.delay(self.cleaned_data.copy())
